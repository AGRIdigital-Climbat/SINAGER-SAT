"""Servicio de importación del histórico legacy (Excel BD EDAN).

Cada fila compatible del Excel se importa como:
  - una cabecera EDAN consolidada (edan.edan, estado 5 = Aprobado ajuste,
    id_usuario_ugr NULL, procedencia 'excel_legacy'),
  - una localidad vinculada a esa cabecera (id_edan set, estado localidad 3),
    con sus secciones de daños y los flags imp_* coherentes.

Regla de secciones: SOLO se inserta la fila de sección cuando el Excel tiene
dato (codigo de daño A/D/SI o conteo > 0) y se activa su flag 1:1. Los flags
agregados se fijan según la agrupación del dominio:
  - imp_infraestructura = vial OR infraestructura pública
  - imp_agropecuario     = agricultura OR pecuario OR infra_productiva
No se modifica el mapeo vivo IMP_FLAG_POR_TABLA de service.py.
"""

import os
import re
import unicodedata
from datetime import date, datetime

from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.orm import Session

PROCEDENCIA_LEGACY = "excel_legacy"
ORIGEN_PREFIX = "BD_EDAN"
ESTADO_EDAN_CERRADO = 5          # estado_edan 'Aprobado ajuste' (producto final)
ESTADO_LOCALIDAD_APROBADA = 3    # edan_localidades_estado 'Aprobado UGR'
TIPO_LOCALIDAD_COMUNIDAD = 2     # tipo_localidad 'Comunidad'
GRUPO_ETARIO_ADULTO = 3          # grupo_etario 'Adulto de 19-60 años'

MAX_DETALLES = 200

# --- índices de columnas de la hoja "BDedan" --------------------------------
C_ID = 0
C_FECHA_EVENTO = 1
C_MES = 2
C_ANIO = 3
C_COD_INI = 4
C_DEP = 5
C_PROV = 6
C_MUN = 7
C_LUGAR = 8
C_N_COMUNIDADES = 9
C_TIPO_EVENTO = 10
C_FAM_AFEC = 11
C_FAM_DAM = 12
C_VIAL = 13
C_INFRA_PUB = 14
C_ENERGIA = 15
C_AGUA = 16
C_ALCANT = 17
C_GAS = 18
C_TELECOM = 19
C_EDUC = 20
C_VIV_AFEC = 21
C_VIV_DES = 22
C_HAS_AFEC = 23
C_HAS_PERD = 24
C_GAN_AFEC = 25
C_GAN_PERD = 26
C_OBS = 27
C_FUENTE = 28
C_FORM_EDAN = 29
C_FALLECIDOS = 30
C_DESAPARECIDOS = 31
C_HERIDOS = 32
C_EVACUADOS = 33

LUGAR_NO_NOMINAL = {
    "VARIAS COMUNIDADES", "DIVERSAS COMUNIDADES", "VARIAS", "OTROS",
    "SIN DATOS", "POR CONFIRMAR", "S/D", "NACIONAL",
}

CODIGOS_DANO = {"A", "D", "SI"}


def _norm(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip().upper()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0


def _es_dano(value) -> bool:
    return _norm(value) in CODIGOS_DANO


def _slug(texto: str) -> str:
    return re.sub(r"\W+", "-", _norm(texto)).strip("-")


def _fecha_fila(r) -> tuple[date | None, int | None]:
    """Devuelve (fecha_evento, año). El año se toma de la columna AÑO o de la
    fecha; es el que se usa para generar codigo_edan."""
    fecha = None
    v = r[C_FECHA_EVENTO]
    if isinstance(v, datetime):
        fecha = v.date()
    elif isinstance(v, date):
        fecha = v
    anio = None
    a = r[C_ANIO]
    if isinstance(a, (int, float)) and 1900 <= int(a) <= 2100:
        anio = int(a)
    elif fecha is not None:
        anio = fecha.year
    return fecha, anio


def _cargar_catalogo_eventos(db: Session) -> dict[str, int]:
    rows = db.execute(text("SELECT id_tipo_evento, nombre FROM edan.tipo_evento")).mappings().all()
    return {_norm(r["nombre"]): r["id_tipo_evento"] for r in rows}


def _cargar_municipios(db: Session) -> dict[str, dict]:
    rows = db.execute(text("""
        SELECT codigo_ine, id, id_provincia, id_departamento
        FROM shared.municipio
    """)).mappings().all()
    return {r["codigo_ine"]: dict(r) for r in rows}


def _cargar_homologacion(wb) -> dict[str, str]:
    if "homologacion" not in wb.sheetnames:
        raise HTTPException(status_code=400,
                            detail="El archivo no contiene la hoja 'homologacion'")
    ws = wb["homologacion"]
    rows = ws.iter_rows(values_only=True)
    next(rows, None)  # encabezado
    out = {}
    for r in rows:
        if not r or r[0] is None:
            continue
        raw = _norm(r[0])
        cano = _norm(r[1]) if len(r) > 1 else ""
        if raw:
            out[raw] = cano
    return out


def _secuencias_codigo(db: Session) -> dict[tuple[str, int], int]:
    """Devuelve {(codigo_ine, anio): ultima secuencia} de los EDAN existentes
    con codigo en el formato {ine}/{anio}/{nnn}."""
    seq = {}
    rows = db.execute(text("""
        SELECT codigo_edan FROM edan.edan
        WHERE codigo_edan ~ '^[0-9]{6}/[0-9]{4}/[0-9]{3}$'
    """)).mappings().all()
    for r in rows:
        ine, anio, n = r["codigo_edan"].split("/")
        seq[(ine, int(anio))] = max(seq.get((ine, int(anio)), 0), int(n))
    return seq


class _Resultado:
    def __init__(self):
        self.procesadas = 0
        self.insertadas = 0
        self.omitidas = 0
        self.errores = 0
        self.por_motivo: dict[str, int] = {}
        self.secciones: dict[str, int] = {}
        self.detalles: list[dict] = []

    def motivo(self, clave: str):
        self.por_motivo[clave] = self.por_motivo.get(clave, 0) + 1

    def seccion(self, tabla: str):
        self.secciones[tabla] = self.secciones.get(tabla, 0) + 1

    def error(self, origen: str, msg: str):
        self.errores += 1
        if len(self.detalles) < MAX_DETALLES:
            self.detalles.append({"origen_id": origen, "error": msg[:500]})


def _origen_fila(r, n: int) -> tuple[str, str | None]:
    """Origen + motivo (o None). ID numérico → BD_EDAN-{ID}; sin ID → BD_EDAN-SN-{fila};
    ID no numérico (p.ej. fila TOTAL del Excel) → excluir como 'sin ID válido'."""
    rid = r[C_ID]
    if rid is None or str(rid).strip() == "":
        return f"{ORIGEN_PREFIX}-SN-{n}", None
    s = str(rid).strip()
    if s.isdigit():
        return f"{ORIGEN_PREFIX}-{int(s)}", None
    return f"{ORIGEN_PREFIX}-{s}", "sin ID válido"


def _evaluar_fila(r, ctx: dict, n: int) -> dict | None:
    """Filtra una fila y la transforma en los datos de importación."""
    origen, motivo = _origen_fila(r, n)
    if motivo:
        return {"motivo": motivo}

    # 1. Geografía
    cod = r[C_COD_INI]
    mun = None
    if isinstance(cod, (int, float)):
        mun = ctx["municipios"].get(str(int(cod)).zfill(6))
    elif isinstance(cod, str) and cod.strip().isdigit():
        mun = ctx["municipios"].get(cod.strip().zfill(6))
    if not mun:
        return {"motivo": "sin geografía"}

    # 2. Evento (hoja homologacion)
    raw_ev = _norm(r[C_TIPO_EVENTO])
    cano = ctx["homologacion"].get(raw_ev)
    if not cano:
        return {"motivo": "sin evento homologado"}
    id_tipo_evento = ctx["catalogo"].get(cano)
    if id_tipo_evento is None:
        return {"motivo": f"evento sin catálogo ({cano})"}

    # 3. LUGAR (texto literal del Excel; puede quedar vacío o ser genérico)
    lugar = "" if r[C_LUGAR] is None else str(r[C_LUGAR]).strip()

    # 4. Fecha / año (para codigo_edan)
    fecha_evento, anio = _fecha_fila(r)
    if not anio:
        return {"motivo": "sin fecha ni año"}

    fam_afec, fam_dam = _int(r[C_FAM_AFEC]), _int(r[C_FAM_DAM])

    return {
        "motivo": None,
        "origen": origen,
        "id_tipo_evento": id_tipo_evento,
        "mun": mun,
        "cod_ine": mun["codigo_ine"],
        "fecha_evento": fecha_evento,
        "anio": anio,
        "lugar": lugar,
        "total_familias_afectadas": fam_afec,
        "total_familias_damnificadas": fam_dam,
        "vial": _es_dano(r[C_VIAL]), "tipo_vial": _norm(r[C_VIAL]),
        "infra_pub": _es_dano(r[C_INFRA_PUB]), "tipo_infra_pub": _norm(r[C_INFRA_PUB]),
        "energia": _es_dano(r[C_ENERGIA]),
        "agua": _es_dano(r[C_AGUA]),
        "alcantarillado": _es_dano(r[C_ALCANT]),
        "telecom": _es_dano(r[C_TELECOM]),
        "educ": _int(r[C_EDUC]) > 0,
        "viv_afec": _int(r[C_VIV_AFEC]), "viv_des": _int(r[C_VIV_DES]),
        "has_afec": _int(r[C_HAS_AFEC]), "has_perd": _int(r[C_HAS_PERD]),
        "gan_afec": _int(r[C_GAN_AFEC]), "gan_perd": _int(r[C_GAN_PERD]),
        "fallecidos": _int(r[C_FALLECIDOS]),
        "desaparecidos": _int(r[C_DESAPARECIDOS]),
        "heridos": _int(r[C_HERIDOS]),
        "evacuados": _int(r[C_EVACUADOS]),
    }


def _secciones_de(f: dict) -> list[dict]:
    """Devuelve las secciones a insertar (solo las que tengan dato)."""
    orig = f["origen"]
    secciones = []

    if f["vial"]:
        parcial = f["tipo_vial"] in ("A", "SI")
        total = f["tipo_vial"] == "D"
        secciones.append({
            "tabla": "edan_localidades_danos_viales",
            "flag": "imp_danos_viales",
            "agregados": ["imp_infraestructura"],
            "id_seccion": f"{orig}-vial",
            "data": {"tramo": "", "dano_parcial": parcial or not total,
                     "dano_total": total, "km_danio": 0,
                     "necesidades_inmediatas": "", "observaciones": "",
                     "via": True, "puente": False},
        })

    if f["infra_pub"]:
        parcial = f["tipo_infra_pub"] in ("A", "SI")
        total = f["tipo_infra_pub"] == "D"
        secciones.append({
            "tabla": "edan_localidades_danos_infra_publica",
            "flag": "imp_danos_infra_publica",
            "agregados": ["imp_infraestructura"],
            "id_seccion": f"{orig}-infrapub",
            "data": {"comunidad": "", "tipo_estructura": "",
                     "dano_parcial": parcial or not total, "dano_total": total,
                     "observaciones": ""},
        })

    tipos_servicio = [
        (f["energia"], "energia_electrica", f"{orig}-serv-energia"),
        (f["agua"], "agua_potable", f"{orig}-serv-agua"),
        (f["alcantarillado"], "alcantarillado", f"{orig}-serv-alcantarillado"),
        (f["telecom"], "telecomunicaciones", f"{orig}-serv-telecom"),
    ]
    for presente, tipo, id_seccion in tipos_servicio:
        if presente:
            secciones.append({
                "tabla": "edan_localidades_servicios_basicos",
                "flag": "imp_servicios_basicos",
                "agregados": ["imp_servicios"],
                "id_seccion": id_seccion,
                "data": {"tipo": tipo, "dano_parcial": True, "dano_total": False,
                         "necesidades_inmediatas": "", "observaciones": ""},
            })

    if f["educ"]:
        secciones.append({
            "tabla": "edan_localidades_unidades_educativas",
            "flag": "imp_unidades_educativas",
            "agregados": ["imp_educacion"],
            "id_seccion": f"{orig}-educ",
            "data": {"nombre_establecimiento": "", "comunidad": "",
                     "dano_parcial": True, "dano_total": False,
                     "suspension_clases": None, "perdida_material": None,
                     "funciona_albergue": None, "estudiantes": 0,
                     "profesores": 0, "administrativos": 0, "observaciones": ""},
        })

    if f["viv_afec"] > 0 or f["viv_des"] > 0:
        secciones.append({
            "tabla": "edan_localidades_danos_vivienda",
            "flag": "imp_danos_vivienda",
            "agregados": ["imp_vivienda"],
            "id_seccion": f"{orig}-vivienda",
            "data": {"comunidad": "", "dano_parcial": f["viv_afec"],
                     "dano_total": f["viv_des"], "necesidades_inmediatas": "",
                     "observaciones": ""},
        })

    if f["has_afec"] > 0 or f["has_perd"] > 0:
        secciones.append({
            "tabla": "edan_localidades_danos_agricultura",
            "flag": "imp_danos_agricultura",
            "agregados": ["imp_agropecuario"],
            "id_seccion": f"{orig}-agri",
            "data": {"tipo_cultivo": "", "id_cultivo": None,
                     "hectareas_afectadas": f["has_afec"],
                     "hectareas_perdidas": f["has_perd"],
                     "necesidades_inmediatas": "", "observaciones": ""},
        })

    if f["gan_afec"] > 0 or f["gan_perd"] > 0:
        secciones.append({
            "tabla": "edan_localidades_danos_pecuario",
            "flag": "imp_danos_pecuarios",
            "agregados": ["imp_agropecuario"],
            "id_seccion": f"{orig}-pec",
            "data": {"especie": "", "id_especie": None, "raza": "",
                     "animales_afectados": f["gan_afec"],
                     "animales_muertos": f["gan_perd"],
                     "necesidades_inmediatas": ""},
        })

    if f["fallecidos"] > 0 or f["desaparecidos"] > 0 or f["heridos"] > 0:
        secciones.append({
            "tabla": "edan_localidades_impacto_poblacion",
            "flag": "imp_impacto_poblacion",
            "agregados": ["imp_poblacion"],
            "id_seccion": f"{orig}-impacto",
            "data": {"id_grupo_etario": GRUPO_ETARIO_ADULTO,
                     "fallecidos": f["fallecidos"], "heridos": f["heridos"],
                     "desaparecidos": f["desaparecidos"], "observaciones": ""},
        })

    if f["evacuados"] > 0:
        secciones.append({
            "tabla": "edan_localidades_primera_respuesta",
            "flag": "imp_primera_respuesta",
            "agregados": [],
            "id_seccion": f"{orig}-evac",
            "data": {"busqueda": False, "salvamento": False,
                     "evacuacion": True, "observaciones": ""},
        })

    return secciones


def _flags_de(f: dict, secciones: list[dict]) -> dict:
    """Combina flags 1:1 y agregados (agrupación de dominio)."""
    detalle = {}
    agregado = {}
    for s in secciones:
        detalle[s["flag"]] = True
        for a in s["agregados"]:
            agregado[a] = True
    flags = {
        "imp_poblacion": agregado.get("imp_poblacion", False),
        "imp_salud": False,
        "imp_infraestructura": agregado.get("imp_infraestructura", False),
        "imp_servicios": agregado.get("imp_servicios", False),
        "imp_educacion": agregado.get("imp_educacion", False),
        "imp_vivienda": agregado.get("imp_vivienda", False),
        "imp_agropecuario": agregado.get("imp_agropecuario", False),
        "imp_proteccion": False,
        "imp_necesidades": False,
        "imp_impacto_poblacion": detalle.get("imp_impacto_poblacion", False),
        "imp_salud_establecimientos": False,
        "imp_danos_viales": detalle.get("imp_danos_viales", False),
        "imp_danos_infra_publica": detalle.get("imp_danos_infra_publica", False),
        "imp_servicios_basicos": detalle.get("imp_servicios_basicos", False),
        "imp_unidades_educativas": detalle.get("imp_unidades_educativas", False),
        "imp_danos_vivienda": detalle.get("imp_danos_vivienda", False),
        "imp_danos_agricultura": detalle.get("imp_danos_agricultura", False),
        "imp_danos_pecuarios": detalle.get("imp_danos_pecuarios", False),
        "imp_infra_productiva": False,
        "imp_primera_respuesta": detalle.get("imp_primera_respuesta", False),
        "imp_necesidad_salud": False,
        "imp_necesidad_humanitaria": False,
    }
    return flags


_SECCION_COLS = {
    "edan_localidades_danos_viales": (
        "id_edan_localidad, tramo, dano_parcial, dano_total, km_danio, "
        "necesidades_inmediatas, observaciones, via, puente, id_seccion"),
    "edan_localidades_danos_infra_publica": (
        "id_edan_localidad, comunidad, tipo_estructura, dano_parcial, dano_total, "
        "observaciones, id_seccion"),
    "edan_localidades_servicios_basicos": (
        "id_edan_localidad, tipo, dano_parcial, dano_total, necesidades_inmediatas, "
        "observaciones, id_seccion"),
    "edan_localidades_unidades_educativas": (
        "id_edan_localidad, nombre_establecimiento, comunidad, dano_parcial, dano_total, "
        "suspension_clases, perdida_material, funciona_albergue, estudiantes, "
        "profesores, administrativos, observaciones, id_seccion"),
    "edan_localidades_danos_vivienda": (
        "id_edan_localidad, comunidad, dano_parcial, dano_total, necesidades_inmediatas, "
        "observaciones, id_seccion"),
    "edan_localidades_danos_agricultura": (
        "id_edan_localidad, tipo_cultivo, id_cultivo, hectareas_afectadas, "
        "hectareas_perdidas, necesidades_inmediatas, observaciones, id_seccion"),
    "edan_localidades_danos_pecuario": (
        "id_edan_localidad, especie, id_especie, raza, animales_afectados, "
        "animales_muertos, necesidades_inmediatas, id_seccion"),
    "edan_localidades_impacto_poblacion": (
        "id_edan_localidad, id_grupo_etario, fallecidos, heridos, desaparecidos, "
        "observaciones, id_seccion"),
    "edan_localidades_primera_respuesta": (
        "id_edan_localidad, busqueda, salvamento, evacuacion, observaciones, id_seccion"),
}


def importar_excel(db: Session, ruta: str,
                   solo_compatibles: bool = True,
                   modo: str = "importar",
                   id_usuario: int | None = None) -> dict:
    """Importa (o simula) el Excel legacy. Retorna un resumen con conteos."""
    if not os.path.exists(ruta):
        raise HTTPException(status_code=400, detail=f"Archivo no encontrado: {ruta}")
    if modo not in ("importar", "simular"):
        raise HTTPException(status_code=400, detail="modo debe ser 'importar' o 'simular'")

    wb = load_workbook(ruta, read_only=True, data_only=True)
    if "BDedan" not in wb.sheetnames:
        raise HTTPException(status_code=400, detail="El archivo no contiene la hoja 'BDedan'")
    ws = wb["BDedan"]
    rows = ws.iter_rows(values_only=True)
    next(rows, None)  # encabezado

    ctx = {
        "municipios": _cargar_municipios(db),
        "catalogo": _cargar_catalogo_eventos(db),
        "homologacion": _cargar_homologacion(wb),
        "lugar_no_nominal": LUGAR_NO_NOMINAL,
    }
    if not ctx["homologacion"]:
        raise HTTPException(status_code=400,
                            detail="La hoja 'homologacion' está vacía o no tiene mapeos")

    res = _Resultado()

    if modo == "importar":
        id_importacion = db.execute(text("""
            INSERT INTO edan.edan_importacion_log
                (nombre_archivo, procedencia, id_usuario)
            VALUES (:nombre, :proc, :usr)
            RETURNING id_importacion
        """), {"nombre": os.path.basename(ruta), "proc": PROCEDENCIA_LEGACY,
               "usr": id_usuario}).scalar()
        seqs = _secuencias_codigo(db)
    else:
        id_importacion = None
        seqs = {}

    try:
        for n, r in enumerate(rows, 1):
            res.procesadas += 1
            origen, _ = _origen_fila(r, n)
            try:
                f = _evaluar_fila(r, ctx, n)
            except Exception as e:  # noqa: BLE001
                res.error(origen, f"error de transformación: {e}")
                continue
            if f is None:
                continue
            if f["motivo"]:
                res.omitidas += 1
                res.motivo(f["motivo"])
                continue

            if modo == "simular":
                res.insertadas += 1
                for s in _secciones_de(f):
                    res.seccion(s["tabla"])
                continue

            # ---- modo importar ------------------------------------------
            existe = db.execute(text("SELECT 1 FROM edan.edan WHERE origen_id = :o"),
                                {"o": f["origen"]}).first()
            if existe:
                res.omitidas += 1
                res.motivo("ya importado")
                continue

            clave_seq = (f["cod_ine"], f["anio"])
            seq = seqs.get(clave_seq, 0) + 1
            seqs[clave_seq] = seq
            codigo_edan = f"{f['cod_ine']}/{f['anio']}/{seq:03d}"

            secciones = _secciones_de(f)
            flags = _flags_de(f, secciones)

            cab = db.execute(text("""
                INSERT INTO edan.edan
                    (codigo_edan, id_departamento, id_provincia, id_municipio,
                     fecha_evento, total_poblacion_afectada,
                     total_familias_afectadas, total_familias_damnificadas,
                     id_estado, id_tipo_evento, procedencia, origen_id, id_importacion)
                VALUES (:codigo, :dep, :prov, :mun, :fecha, 0,
                        :fam_afec, :fam_dam, :estado, :ev, :proc, :origen, :lote)
                RETURNING id_edan
            """), {
                "codigo": codigo_edan,
                "dep": f["mun"]["id_departamento"],
                "prov": f["mun"]["id_provincia"],
                "mun": f["mun"]["id"],
                "fecha": f["fecha_evento"],
                "fam_afec": f["total_familias_afectadas"],
                "fam_dam": f["total_familias_damnificadas"],
                "estado": ESTADO_EDAN_CERRADO,
                "ev": f["id_tipo_evento"],
                "proc": PROCEDENCIA_LEGACY,
                "origen": f["origen"],
                "lote": id_importacion,
            }).scalar()

            id_localidad = db.execute(text(f"""
                INSERT INTO edan.edan_localidades
                    (id_edan, localidad, id_tipo_localidad, id_edan_localidad_estado,
                     id_tipo_evento, id_departamento, id_provincia, id_municipio,
                     fecha_evento, total_poblacion_afectada,
                     total_familias_afectadas, total_familias_damnificadas,
                     procedencia, origen_id, id_importacion,
                     imp_poblacion, imp_salud, imp_infraestructura, imp_servicios,
                     imp_educacion, imp_vivienda, imp_agropecuario, imp_proteccion,
                     imp_necesidades, imp_impacto_poblacion,
                     imp_salud_establecimientos, imp_danos_viales,
                     imp_danos_infra_publica, imp_servicios_basicos,
                     imp_unidades_educativas, imp_danos_vivienda,
                     imp_danos_agricultura, imp_danos_pecuarios,
                     imp_infra_productiva, imp_primera_respuesta,
                     imp_necesidad_salud, imp_necesidad_humanitaria)
                VALUES (:edan, :lugar, :tloc, :eloc, :ev, :dep, :prov, :mun,
                        :fecha, 0, :fam_afec, :fam_dam, :proc, :origen, :lote,
                        :f_pob, :f_salud, :f_infra, :f_serv,
                        :f_educ, :f_viv, :f_agro, :f_pro,
                        :f_nec, :f_ip, :f_se, :f_vial, :f_infra_pub, :f_sb,
                        :f_ue, :f_dviv, :f_dagri, :f_dpec, :f_iprod, :f_pr,
                        :f_nsal, :f_nhum)
                RETURNING id_edan_localidad
            """), {
                "edan": cab, "lugar": f["lugar"], "tloc": TIPO_LOCALIDAD_COMUNIDAD,
                "eloc": ESTADO_LOCALIDAD_APROBADA, "ev": f["id_tipo_evento"],
                "dep": f["mun"]["id_departamento"], "prov": f["mun"]["id_provincia"],
                "mun": f["mun"]["id"], "fecha": f["fecha_evento"],
                "fam_afec": f["total_familias_afectadas"],
                "fam_dam": f["total_familias_damnificadas"],
                "proc": PROCEDENCIA_LEGACY, "origen": f["origen"], "lote": id_importacion,
                "f_pob": flags["imp_poblacion"], "f_salud": flags["imp_salud"],
                "f_infra": flags["imp_infraestructura"], "f_serv": flags["imp_servicios"],
                "f_educ": flags["imp_educacion"], "f_viv": flags["imp_vivienda"],
                "f_agro": flags["imp_agropecuario"], "f_pro": flags["imp_proteccion"],
                "f_nec": flags["imp_necesidades"], "f_ip": flags["imp_impacto_poblacion"],
                "f_se": flags["imp_salud_establecimientos"],
                "f_vial": flags["imp_danos_viales"],
                "f_infra_pub": flags["imp_danos_infra_publica"],
                "f_sb": flags["imp_servicios_basicos"],
                "f_ue": flags["imp_unidades_educativas"],
                "f_dviv": flags["imp_danos_vivienda"],
                "f_dagri": flags["imp_danos_agricultura"],
                "f_dpec": flags["imp_danos_pecuarios"],
                "f_iprod": flags["imp_infra_productiva"],
                "f_pr": flags["imp_primera_respuesta"],
                "f_nsal": flags["imp_necesidad_salud"],
                "f_nhum": flags["imp_necesidad_humanitaria"],
            }).scalar()

            for s in secciones:
                cols = _SECCION_COLS[s["tabla"]].split(", ")
                ph = ", ".join(f":{c}" for c in cols)
                params = {c: None for c in cols}
                params["id_edan_localidad"] = id_localidad
                params["id_seccion"] = s["id_seccion"]
                params.update(s["data"])
                db.execute(text(f"""
                    INSERT INTO edan.{s["tabla"]} ({", ".join(cols)})
                    VALUES ({ph})
                    ON CONFLICT (id_seccion) DO UPDATE SET
                        id_edan_localidad = EXCLUDED.id_edan_localidad,
                        id_seccion = EXCLUDED.id_seccion
                """), params)
                res.seccion(s["tabla"])

            res.insertadas += 1

        if modo == "importar":
            db.execute(text("""
                UPDATE edan.edan_importacion_log SET
                    filas_procesadas = :proc, filas_insertadas = :ins,
                    filas_omitidas = :omi, errores = :err,
                    detalle = :det
                WHERE id_importacion = :id
            """), {
                "proc": res.procesadas, "ins": res.insertadas, "omi": res.omitidas,
                "err": res.errores, "det": res.detalles, "id": id_importacion,
            })
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return {
        "modo": modo,
        "solo_compatibles": solo_compatibles,
        "archivo": os.path.basename(ruta),
        "procesadas": res.procesadas,
        "insertadas": res.insertadas,
        "omitidas": res.omitidas,
        "errores": res.errores,
        "id_importacion": id_importacion,
        "por_motivo": res.por_motivo,
        "secciones_insertadas": res.secciones,
        "detalles": res.detalles[:20],
    }