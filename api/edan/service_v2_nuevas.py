"""Service de las APIs nuevas EDAN (Fase 2, uuid-first).

Reglas (PLAN_APIS_V2_EDAN.md, §20.14 LWW):
- Upsert idempotente por uuid (nunca DELETE+INSERT).
- **LWW total: gana el último que llega.** `version` NO se envía ni se valida;
  sin optimistic-lock ni 409 en la escritura (los 409 previos eran casi todos
  falsos: bump de foto, colas del mismo dispositivo).
- Filas de sección creadas por aquí escriben `id_seccion = uuid_registro::text`
  (sintético v2.52: la identidad sobrevive al DELETE+INSERT de la app vieja).
- Coexistencia: no se tocan columnas legacy ni índices `idx_seccion_*`.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import service as service_viejo
from .grupos import (
    GRUPO_FLAG,
    GRUPO_SECCIONES,
    GRUPOS_BD,
    GRUPO_WIRE_LEGACY,
    SECCION_FLAG,
    SECCION_FLAG_R,
    SECCION_LEGACY,
    grupos_de,
    grupos_de_activos,
)
from .utils import db_error

# tipo_corto -> (tabla sin prefijo edan., es_1:1, columna PK)
TIPOS_SECCION: dict[str, tuple[str, bool, str]] = {
    "impacto_poblacion":        ("edan_localidades_impacto_poblacion",        False, "id_impacto_poblacion"),
    "salud_establecimientos":   ("edan_localidades_salud_establecimientos",   False, "id_establecimiento_salud"),
    "salud_necesidades":        ("edan_localidades_salud_necesidades",        True,  "id_edan_localidad"),
    "danos_viales":             ("edan_localidades_danos_viales",             False, "id_dano_vial"),
    "danos_infra_publica":      ("edan_localidades_danos_infra_publica",      False, "id_dano_infra"),
    "servicios_basicos":        ("edan_localidades_servicios_basicos",        False, "id_servicio_basico"),
    "unidades_educativas":      ("edan_localidades_unidades_educativas",      False, "id_unidad_educativa"),
    "danos_vivienda":           ("edan_localidades_danos_vivienda",           True,  "id_dano_vivienda"),
    "danos_agricultura":        ("edan_localidades_danos_agricultura",        False, "id_dano_agricultura"),
    "danos_pecuario":           ("edan_localidades_danos_pecuario",           False, "id_dano_pecuario"),
    "infra_productiva":         ("edan_localidades_infra_productiva",         False, "id_infra_productiva"),
    "proteccion":               ("edan_localidades_proteccion",               False, "id_grupo_vulnerable"),
    "primera_respuesta":        ("edan_localidades_primera_respuesta",        True,  "id_edan_localidad"),
    "necesidades_humanitarias": ("edan_localidades_necesidades_humanitarias", True,  "id_edan_localidad"),
}

# tipo_entidad de fotografias -> tabla (además de las 14 secciones, 'vivienda')
TABLA_FOTO_EXTRA = {"vivienda": "edan_localidades_viviendas"}

# Columnas del cliente que NUNCA se escriben desde los payloads
_SISTEMA = {
    "id_edan_localidad", "uuid_registro", "uuid_edan_localidad",
    "version", "fecha_modificacion", "id_seccion",
    "id_dano_vivienda", "uuid_dano_vivienda", "id_vivienda",
    "id_fotografia", "uuid_fotografia", "fecha_creacion", "sha256",
    "mime_type", "tamano_bytes", "borrado_logico", "ruta_archivo",
    "id_local", "id_edan", "id_importacion", "pendiente_actualizacion",
    "pendiente_eliminacion", "id_usuario", "id_seccion",
}

_CABECERA_COLS = {
    "localidad", "id_municipio", "id_departamento", "id_provincia",
    "id_tipo_evento", "id_tipo_localidad", "id_edan_localidad_estado",
    "fecha_llenado", "fecha_evento", "hora_evento",
    "total_poblacion_afectada", "total_familias_afectadas",
    "total_familias_damnificadas",
    "id_usuario", "pendiente_actualizacion", "pendiente_eliminacion",
}

# id crudo -> (tabla, pk, columnas expuestas, clave del objeto anidado en el GET)
_FK_RESOLVER: dict[str, tuple[str, str, list[str], str]] = {
    "id_departamento": ("shared.departamento", "id",
                        ["id", "codigo_ine", "nombre"], "departamento"),
    "id_provincia": ("shared.provincia", "id",
                     ["id", "codigo_ine", "id_departamento", "nombre"], "provincia"),
    "id_municipio": ("shared.municipio", "id",
                     ["id", "codigo_ine", "id_departamento", "id_provincia", "nombre"], "municipio"),
    "id_tipo_evento": ("edan.tipo_evento", "id_tipo_evento",
                       ["id_tipo_evento", "nombre"], "tipo_evento"),
    "id_tipo_localidad": ("edan.tipo_localidad", "id_tipo_localidad",
                          ["id_tipo_localidad", "nombre", "descripcion", "orden"], "tipo_localidad"),
    "id_edan_localidad_estado": ("edan.edan_localidades_estado", "id_edan_localidad_estado",
                                 ["id_edan_localidad_estado", "nombre", "orden"], "estado_localidad"),
    "id_usuario": ("usuarios.usuario", "id_usuario",
                   ["id_usuario", "usuario", "nombre", "id_rol"], "usuario"),
    "id_edan": ("edan.edan", "id_edan",
                ["id_edan", "uuid_edan", "codigo_edan", "id_estado", "id_municipio",
                 "id_tipo_evento", "fecha_evento"], "edan"),
    # FKs de secciones (solo presentes en las filas que las traen)
    "id_cultivo": ("shared.cultivo", "id", ["id", "nombre", "grupo"], "cultivo"),
    "id_especie": ("shared.pecuario", "id", ["id", "nombre", "grupo"], "pecuario"),
    # §20.16: cabecera EDAN — TODO id con su JSON (id_importacion) + los ids
    # que vienen DENTRO de los objetos ya anidados (recursión de _resolver_ids)
    "id_importacion": ("edan.edan_importacion_log", "id_importacion",
                       ["id_importacion", "nombre_archivo", "procedencia", "id_usuario",
                        "fecha_importacion", "filas_procesadas", "filas_insertadas",
                        "filas_actualizadas", "filas_omitidas", "errores"], "importacion"),
    "id_rol": ("usuarios.rol", "id_rol", ["id_rol", "nombre", "descripcion"], "rol"),
    "id_estado": ("edan.estado_edan", "id_estado",
                  ["id_estado", "nombre", "descripcion", "orden"], "estado_edan"),
    # §20.17: cabecera del EDAN padre — sus dos FKs de usuario
    "id_usuario_ugr": ("usuarios.usuario", "id_usuario",
                       ["id_usuario", "usuario", "nombre", "id_rol", "carnet",
                        "celular", "correo", "cargo", "activo"], "usuario_ugr"),
    "id_usuario_alcalde": ("usuarios.usuario", "id_usuario",
                           ["id_usuario", "usuario", "nombre", "id_rol", "carnet",
                            "celular", "correo", "cargo", "activo"], "usuario_alcalde"),
}

# Objetos FK anidados que el GET pone junto al id crudo (municipio: {...}):
# en un PUT de ida y vuelta viajan en las filas y el servidor los DESCARTA.
_FK_OBJETOS = {tup[3] for tup in _FK_RESOLVER.values()}

# Profundidad máxima de la recursión FK (grafo real: cabecera -> edan ->
# municipio -> provincia -> departamento; importacion -> usuario -> rol <= 5)
_MAX_PROF_FK = 6


def _resolver_ids(db: Session, fila: dict, cache: dict | None = None,
                  prof: int = 0, skip_pk: str | None = None) -> dict:
    """GET: además del id crudo, añade el objeto JSON anidado de cada FK
    (id_municipio -> municipio {id, codigo_ine, nombre, ...}).

    §20.16 — RECURSIVO dentro de la cabecera de la localidad EDAN: si el
    objeto anidado trae a su vez ids FK expuestos (usuario.id_rol -> rol,
    municipio.id_departamento -> departamento, municipio.id_provincia ->
    provincia, provincia.id_departamento -> departamento, edan.id_estado ->
    estado_edan, edan.id_municipio -> municipio, edan.id_tipo_evento ->
    tipo_evento, importacion.id_usuario -> usuario), TAMBIÉN se les añade su
    JSON. `skip_pk` evita auto-anidar el PK del propio objeto (id_usuario
    dentro de usuario, id_rol dentro de rol, id_edan dentro de edan, …);
    los catálogos no ciclan y `_MAX_PROF_FK` acota el coste."""
    if prof > _MAX_PROF_FK:
        return fila
    for id_col, (tabla, pk, cols, key) in _FK_RESOLVER.items():
        if id_col not in fila:
            continue
        if skip_pk is not None and id_col == skip_pk:
            continue                      # el id ES la identidad del objeto
        v = fila.get(id_col)
        if v is None:
            fila[key] = None
            continue
        ck = (tabla, v)
        if cache is not None and ck in cache:
            fila[key] = cache[ck]
            continue
        q = db.execute(text(f"SELECT {', '.join(cols)} FROM {tabla} WHERE {pk} = :id"),
                       {"id": v}).mappings().first()
        obj = _row_public(q) if q else None
        if isinstance(obj, dict):          # recursión: el objeto trae sus ids
            _resolver_ids(db, obj, cache, prof + 1, skip_pk=pk)
        if cache is not None:
            cache[ck] = obj
        fila[key] = obj
    return fila

_columns_cache: dict[str, set[str]] = {}


def _cols(db: Session, tabla: str) -> set[str]:
    if tabla not in _columns_cache:
        rows = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'edan' AND table_name = :t
        """), {"t": tabla}).scalars().all()
        _columns_cache[tabla] = set(rows)
    return _columns_cache[tabla]


def _parse_uuid(valor, campo: str) -> UUID:
    try:
        return valor if isinstance(valor, UUID) else UUID(str(valor))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail=f"{campo} no es un UUID válido: {valor!r}")


def _iso(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


def _row_public(row) -> dict:
    """Fila -> dict de respuesta. `version` (columna interna + trigger
    trg_bump_version) NUNCA se expone al cliente (§20.14 LWW).
    `id_local` y `id_seccion` TAMPOCO se exponen: las APIs nuevas mandan y
    devuelven SOLO uuid (`uuid_edan_localidad`, `uuid_registro`, …) + ids
    numéricos, para no confundir al cliente — el servidor los sigue
    escribiendo internamente."""
    d = dict(row)
    d.pop("version", None)
    d.pop("id_local", None)
    d.pop("id_seccion", None)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, date):
            d[k] = v.isoformat()
        elif isinstance(v, time):
            d[k] = v.isoformat()
        elif isinstance(v, UUID):
            d[k] = str(v)
        elif isinstance(v, Decimal):
            # coordenadas SIEMPRE como string (paridad con la API vieja:
            # el parser del mapa las espera como texto, con la escala de BD)
            d[k] = str(v) if k in ("coordenada_lat", "coordenada_lon") else float(v)
    return d


def _cmp_iguales(actual, nuevo) -> bool:
    """Compara un valor de BD con uno del payload (JSON) SIN falsos positivos.

    Idempotencia §20.15: si el payload trae el MISMO dato que ya está en la
    fila, no se escribe ni se bumpa `fecha_modificacion` (evita falsos
    `tiene_cambios` en /estados y falsos cambios en pull). Normaliza
    Decimal/float/int, datetime/date/time (ISO con o sin tz) y str.
    """
    if nuevo is None:
        return actual is None
    if actual is None:
        return False
    if isinstance(nuevo, bool):
        if isinstance(actual, str):
            return (actual.lower() in ("true", "t", "yes", "1")) == nuevo
        return bool(actual) == nuevo
    if isinstance(nuevo, (int, float, Decimal)):
        try:
            return Decimal(str(actual)) == Decimal(str(nuevo))
        except Exception:
            return str(actual) == str(nuevo)
    if isinstance(nuevo, str):
        if isinstance(actual, datetime):
            try:
                p = datetime.fromisoformat(nuevo.replace("Z", "+00:00"))
                return p.replace(tzinfo=None) == actual.replace(tzinfo=None)
            except Exception:
                try:                    # payload solo fecha ("2026-10-11")
                    return date.fromisoformat(nuevo[:10]) == actual.date()
                except Exception:
                    return False
        if isinstance(actual, date):
            try:
                return date.fromisoformat(nuevo[:10]) == actual
            except Exception:
                return False
        if isinstance(actual, time):
            try:
                return time.fromisoformat(nuevo) == actual   # "10:30" == "10:30:00"
            except Exception:
                return False
        if isinstance(actual, (Decimal, int, float)) and not isinstance(actual, bool):
            try:
                return Decimal(str(actual)) == Decimal(nuevo)
            except Exception:
                return str(actual) == nuevo
        if isinstance(actual, UUID):
            return str(actual) == nuevo
        return str(actual) == nuevo
    return str(actual) == str(nuevo)


# ===========================================================================
# Invariante grup_* := OR(sus imp_* miembros) — verdad por construcción
# (PLAN §20.13): los 9 grup_* se derivan SIEMPRE de las 14 columnas imp_*,
# nunca del wire. Red de lectura (inmune al drift legacy) + recálculo en
# toda escritura que cambie imp_* (cabecera y /completo). Sin nodo `grupos`
# en las respuestas: los planos en cabecera son la única cara pública.
# ===========================================================================
def _grupos_planos_desde_flags(flags: dict) -> dict[str, bool]:
    """Los 9 `grup_*` (claves = columnas) derivados de las `imp_*` de una fila."""
    return {colg: any(bool((flags or {}).get(SECCION_FLAG_R[s])) for s in miembros)
            for colg, miembros in GRUPO_SECCIONES.items()}


def _sincronizar_grupos_fila(fila: dict) -> dict:
    """Red de lectura: sobrescribe los 9 `grup_*` planos con OR(imp_*)
    (inmune a columnas crudas legacy desalineadas)."""
    fila.update(_grupos_planos_desde_flags(fila))
    return fila


def _recalcular_grupos(db: Session, id_loc: int) -> dict[str, bool]:
    """Escritura: recalcula los 9 `grup_*` = OR(miembros imp_*) desde las
    columnas y los escribe si difieren (bump de fecha_modificacion incluido)."""
    row = db.execute(text(f"""
        SELECT {", ".join(sorted(SECCION_FLAG))}, {", ".join(sorted(GRUPOS_BD))}
        FROM edan.edan_localidades WHERE id_edan_localidad = :id
    """), {"id": id_loc}).mappings().first()
    if not row:
        return {}
    planos = _grupos_planos_desde_flags(row)
    diff = {c: planos[c] for c in planos if bool(row[c]) != planos[c]}
    if diff:
        sets = ", ".join(f"{c} = :{c}" for c in diff)
        db.execute(text(f"""
            UPDATE edan.edan_localidades SET {sets}, fecha_modificacion = now()
            WHERE id_edan_localidad = :id
        """), {**diff, "id": id_loc})
    return planos


# Estados "enviados" (heredados 3/4/5 incluidos): 2 Enviado, 3 Aprobado,
# 4 Rechazado, 5 Aprobado Ajuste. 1 Borrador y 6 En revisión quedan libres.
_ESTADOS_ENVIADOS = (2, 3, 4, 5)


def _violaciones_enviados(db: Session, id_loc: int) -> list[dict]:
    """Regla de enviados (estados 2/3/4/5): cada grupo true debe tener algún
    miembro imp_*=true CON ≥1 fila. Devuelve [] si cumple (o si es 1/6/None)."""
    row = db.execute(text(f"""
        SELECT id_edan_localidad_estado, {", ".join(sorted(SECCION_FLAG))}
        FROM edan.edan_localidades WHERE id_edan_localidad = :id
    """), {"id": id_loc}).mappings().first()
    if not row or row["id_edan_localidad_estado"] not in _ESTADOS_ENVIADOS:
        return []
    violaciones = []
    for grupok, miembros in GRUPO_SECCIONES.items():
        if not any(bool(row[SECCION_FLAG_R[s]]) for s in miembros):
            continue  # grupo false: libre
        alguno_con_filas = False
        for s in miembros:
            if not row[SECCION_FLAG_R[s]]:
                continue
            tabla = TIPOS_SECCION[s][0]
            n = db.execute(text(
                f"SELECT count(*) FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                {"id": id_loc}).scalar()
            if n:
                alguno_con_filas = True
                break
        if not alguno_con_filas:
            violaciones.append({"grup": grupok,
                                "imp_miembros": [SECCION_FLAG_R[s] for s in miembros]})
    return violaciones


def _exigir_enviados_validos(db: Session, id_loc: int) -> None:
    """400 (y rollback de la transacción en curso) si la mutación dejaría un
    estado enviado/aprobado con algún grupo activo sin filas."""
    v = _violaciones_enviados(db, id_loc)
    if v:
        db.rollback()
        raise HTTPException(status_code=400, detail=(
            "La localidad quedó en estado enviado/aprobado con grupos activos sin "
            "datos: " + "; ".join(
                f"{x['grup']} (imp miembros {x['imp_miembros']} sin ninguna fila)"
                for x in v)
            + ". Corrija los flags o cargue las filas de esas secciones."))


def _marcar_fotos_borradas(db: Session, tipo_entidad: str, uuids) -> None:
    """Fotos de filas eliminadas -> borrado_logico=true (viajan por pull).
    danos_vivienda además marca las fotos de sus viviendas hijas (el DELETE
    las elimina en cascada; las fotos viajan por pull para otros equipos)."""
    us = [u for u in uuids if u]
    if not us:
        return
    db.execute(text("""
        UPDATE edan.fotografias SET borrado_logico = true, fecha_modificacion = now()
        WHERE tipo_entidad = :te AND uuid_registro = ANY(CAST(:us AS uuid[])) AND borrado_logico = false
    """), {"te": tipo_entidad, "us": us})
    if tipo_entidad == "danos_vivienda":
        db.execute(text("""
            UPDATE edan.fotografias SET borrado_logico = true, fecha_modificacion = now()
            WHERE tipo_entidad = 'vivienda' AND borrado_logico = false
              AND uuid_registro IN (
                  SELECT v.uuid_registro FROM edan.edan_localidades_viviendas v
                  JOIN edan.edan_localidades_danos_vivienda d ON d.id_dano_vivienda = v.id_dano_vivienda
                  WHERE d.uuid_registro = ANY(CAST(:us AS uuid[])))
        """), {"us": us})


# `fotografia` en payloads de filas/viviendas: aceptada y DESCARTADA (oculta de
# Swagger); la foto se sube con POST /fotografias (multipart) y el servidor
# espeja el path en la columna de la fila dueña.
_CLAVES_DESCARTADAS = {"fotografia"}


# ===========================================================================
# Alcance (acceso por rol — espejo de las APIs v2 viejas)
# ===========================================================================
ROLES_LOCALES = (6, 7)


def _norm_tipo(tipo: str) -> str:
    """Estandariza guiones: 'danos-vivienda' -> 'danos_vivienda'."""
    return str(tipo).replace("-", "_")


# ===========================================================================
# Formulario completo: mapeos de nombres y flags
# (nombres legacy/canónicos de sección; imp_* = sección, grup_* = grupo)
# ===========================================================================
# clave (legacy o canónica, normalizada sin guiones) -> sección canónica
SECCION_ALIAS = {
    "impacto_poblacion": "impacto_poblacion",
    "establecimientos_salud": "salud_establecimientos",
    "salud_establecimientos": "salud_establecimientos",
    "danos_viales": "danos_viales",
    "danos_infra_publica": "danos_infra_publica",
    "servicios_basicos": "servicios_basicos",
    "unidades_educativas": "unidades_educativas",
    "danos_vivienda": "danos_vivienda",
    "danos_agricultura": "danos_agricultura",
    "danos_pecuarios": "danos_pecuario",
    "danos_pecuario": "danos_pecuario",
    "infra_productiva": "infra_productiva",
    "proteccion": "proteccion",
    "necesidad_primera_respuesta": "primera_respuesta",
    "primera_respuesta": "primera_respuesta",
    "necesidad_salud": "salud_necesidades",
    "salud_necesidades": "salud_necesidades",
    "necesidad_humanitaria": "necesidades_humanitarias",
    "necesidades_humanitarias": "necesidades_humanitarias",
}

# Los mapeos sección<->grupo viven en `grupos.py` (fuente única, importados arriba).


def _scope_lectura(db: Session, user: dict, geo: tuple | None = None) -> dict:
    """Matriz de lectura igual que `scope_mis_localidades_v2` de la API vieja:
    1-4 nacional, 5/9 departamento (403 si no tiene), 8 municipio (403 si no
    tiene), 6/7 solo propias. 403 si el geo query choca con el scope forzado."""
    sc = service_viejo.scope_mis_localidades_v2(user, geo=geo)
    return sc


def _loc_dueno(db: Session, id_localidad: int) -> dict:
    row = db.execute(text("""
        SELECT id_usuario, id_departamento, id_municipio
        FROM edan.edan_localidades WHERE id_edan_localidad = :i
    """), {"i": id_localidad}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return dict(row)


def _check_acceso(db: Session, user: dict, id_localidad: int, escribir: bool = False) -> None:
    """Lectura: aplica la matriz de scope. Escritura: además exige rol 6/7
    (igual que `require_rol(*ROLES_LOCALES)` en las APIs viejas) y propiedad.

    **Rol 6/7 (UGR Municipio / Responsable Local) en LECTURA**: alcance de
    **todo su municipio** (mapa/listado: `id_municipio` forzado del usuario),
    igual que el UGR ve el mapa; la ESCRITURA sigue siendo solo sobre lo propio
    (`id_usuario`)."""
    if escribir and user.get("id_rol") not in ROLES_LOCALES:
        raise HTTPException(status_code=403, detail=(
            "Las APIs nuevas solo permiten escribir a roles locales (6=UGR "
            "Municipio, 7=Responsable Local), igual que las APIs viejas"))
    loc = _loc_dueno(db, id_localidad)
    # Escritura de roles propios (6/7): SOLO sobre lo propio (id_usuario),
    # aunque la LECTURA se abra a todo el municipio vía _scope_lectura.
    if escribir and user.get("id_rol") in service_viejo.ROLES_PROPIOS:
        if loc["id_usuario"] != user.get("id_usuario"):
            raise HTTPException(status_code=403, detail="El formulario pertenece a otro usuario")
    sc = _scope_lectura(db, user)
    if sc["id_usuario"] and loc["id_usuario"] != sc["id_usuario"]:
        raise HTTPException(status_code=403, detail="El formulario pertenece a otro usuario")
    if sc["id_departamento"] and loc["id_departamento"] != sc["id_departamento"]:
        raise HTTPException(status_code=403, detail="Formulario fuera de su departamento")
    if sc["id_municipio"] and loc["id_municipio"] != sc["id_municipio"]:
        raise HTTPException(status_code=403, detail="Formulario fuera de su municipio")


def _scope_where(sc: dict, alias: str = "edan_localidades") -> tuple[str, dict]:
    """Clause WHERE sobre edan_localidades para filtrar por scope de lectura."""
    conds, params = [], {}
    if sc.get("id_usuario"):
        conds.append(f"{alias}.id_usuario = :su"); params["su"] = sc["id_usuario"]
    if sc.get("id_departamento"):
        conds.append(f"{alias}.id_departamento = :sd"); params["sd"] = sc["id_departamento"]
    if sc.get("id_municipio"):
        conds.append(f"{alias}.id_municipio = :sm"); params["sm"] = sc["id_municipio"]
    return (" AND ".join(conds) if conds else "1=1"), params


# ===========================================================================
# Formulario (cabecera)
# ===========================================================================
def _localidad_por_ref(db: Session, ref: str) -> dict:
    """Resuelve por uuid_edan_localidad o id_edan_localidad numérico."""
    u = None
    if ref and not str(ref).isdigit():
        u = _parse_uuid(ref, "uuid_edan_localidad")
    q = ("SELECT id_edan_localidad, uuid_edan_localidad, version, id_departamento, id_municipio "
         "FROM edan.edan_localidades WHERE ")
    row = db.execute(text(q + ("uuid_edan_localidad = :u" if u else "id_edan_localidad = :i")),
                     {"u": u, "i": None if u else int(ref)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Formulario no encontrado: {ref}")
    return dict(row)


def upsert_formulario(db: Session, user: dict, data: dict, validar: bool = True) -> dict:
    """Escritura de cabecera (POST/PUT /formularios y /completo). LWW: gana
    el último que llega; `version` en el payload se ignora (sin 409).

    - `imp_*` (14) opcionales: los explícitos se escriben; en Borrador
      declarar imp=true sin datos es verdad. imp=false con filas existentes
      -> 400 (la purga se hace con POST /formularios/completo o DELETE).
    - `grup_*` nunca del wire: tras escribir, grup := OR(miembros imp_*)
      (`_recalcular_grupos`) — imposible imp=true con grup=false.
    - `validar=False` (sync_push): solo recálculo, sin regla de enviados.
    """
    uuid_loc = _parse_uuid(data.get("uuid_edan_localidad"), "uuid_edan_localidad")

    # "" viene del default de pydantic: no debe sobreescribir en updates
    campos = {k: v for k, v in data.items()
              if k in _CABECERA_COLS and v is not None and v != ""}
    # 14 imp_* opcionales: los explícitos (true/false) se escriben
    flags_in = {k: bool(data[k]) for k in SECCION_FLAG if data.get(k) is not None}

    # geo derivada: si llega id_municipio y no llegan departamento/provincia,
    # se completan desde shared.municipio (los filtros y el scope 5/9 dependen de ellas)
    if campos.get("id_municipio"):
        m = db.execute(text("""
            SELECT id_departamento, id_provincia FROM shared.municipio WHERE id = :m
        """), {"m": campos["id_municipio"]}).mappings().first()
        if m:
            if "id_departamento" not in campos:
                campos["id_departamento"] = m["id_departamento"]
            if "id_provincia" not in campos:
                campos["id_provincia"] = m["id_provincia"]

    existente = db.execute(text("""
        SELECT * FROM edan.edan_localidades
        WHERE uuid_edan_localidad = :u
    """), {"u": uuid_loc}).mappings().first()

    if existente:
        _check_acceso(db, user, existente["id_edan_localidad"], escribir=True)
        # imp=false con filas existentes: la purga NO es desde cabecera
        for flag, val in flags_in.items():
            if val:
                continue
            tabla = TIPOS_SECCION[SECCION_FLAG[flag]][0]
            n = db.execute(text(
                f"SELECT count(*) FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                {"id": existente["id_edan_localidad"]}).scalar()
            if n:
                raise HTTPException(status_code=400, detail=(
                    f"{flag}=false pero la sección {SECCION_FLAG[flag]} tiene {n} "
                    f"fila(s). La purga se hace con POST /formularios/completo "
                    f"(documento exacto) o con DELETE "
                    f"/formularios/{{uuid}}/secciones/{SECCION_FLAG[flag]}/{{uuid_fila}}."))

    a_escribir = {**campos, **flags_in}
    try:
        if existente:
            # LWW + IDEMPOTENCIA (§20.15): solo se escriben los campos que
            # REALMENTE difieren (id_usuario es INMUTABLE: el autor no cambia).
            # Si nada cambió no hay UPDATE => no se bumpa fecha_modificacion
            # (sin falsos tiene_cambios / sin ruido en pull).
            mutables = {k: v for k, v in a_escribir.items()
                        if k != "id_usuario" and not _cmp_iguales(existente.get(k), v)}
            if mutables:
                sets = ", ".join(f"{k} = :{k}" for k in mutables)
                params = {**mutables, "id": existente["id_edan_localidad"]}
                db.execute(text(f"""
                    UPDATE edan.edan_localidades SET {sets}, fecha_modificacion = now()
                    WHERE id_edan_localidad = :id
                """), params)
            id_loc = existente["id_edan_localidad"]
        else:
            # id_usuario: si el payload lo trae se respeta (dentro del alcance
            # del token); si no, se toma del token. Los roles locales (6/7) solo
            # pueden autuar a su nombre; los nacionales/depto/municipio pueden
            # firmar por usuarios de su alcance (sync de un equipo).
            eff_uid = campos.get("id_usuario", user.get("id_usuario"))
            sc = _scope_lectura(db, user)
            if sc.get("id_usuario") and eff_uid != sc["id_usuario"]:
                raise HTTPException(status_code=403, detail=(
                    "No puede registrar a nombre de otro usuario: su rol solo "
                    f"autúa a su nombre (id_usuario={sc['id_usuario']})."))
            cols = ["uuid_edan_localidad", "id_local", "fecha_modificacion",
                    *sorted(c for c in a_escribir if c != "id_usuario")]
            placeholders = ", ".join(f":{c}" for c in cols)
            # id_local = texto del uuid: el sync viejo (pull/ON CONFLICT) lo ve coherente.
            params = {**a_escribir, "uuid_edan_localidad": uuid_loc, "id_local": str(uuid_loc),
                      "fecha_modificacion": datetime.now()}
            params["id_usuario"] = eff_uid
            cols.append("id_usuario")
            db.execute(text(f"""
                INSERT INTO edan.edan_localidades ({", ".join(cols)})
                VALUES ({placeholders}, :id_usuario)
            """), params)
            id_loc = db.execute(text(
                "SELECT id_edan_localidad FROM edan.edan_localidades "
                "WHERE uuid_edan_localidad = :u"), {"u": uuid_loc}).scalar()
        # invariante: grup_* := OR(miembros imp_*) — siempre, sin queries extra
        _recalcular_grupos(db, id_loc)
        if validar:
            _exigir_enviados_validos(db, id_loc)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    return get_formulario(db, str(uuid_loc), user)


def get_formulario(db: Session, ref: str, user: dict | None = None,
                   modo: str = "comprimido") -> dict:
    """Documento de localidad: {cabecera, secciones con datos, fotos,
    secciones_resumen}. La cabecera es
    la fila pública (columnas sin `version`/`id_local`/`id_seccion`: solo
    uuid + ids) + FK anidadas RECURSIVAS §20.16 —
    todo id con su JSON, incl. id_usuario -> usuario, id_importacion ->
    importacion, y dentro de los
    objetos: usuario -> rol, municipio -> departamento/provincia,
    edan -> estado_edan/municipio/tipo_evento) — + 14 imp_* + los 9
    grup_* SINCRONIZADOS con OR(imp) — red de lectura, sin nodo `grupos`.

    Además de `cabecera` y `secciones_resumen` (conteos, compatibilidad), el
    documento trae **las filas reales de las secciones** (claves legacy con
    `viviendas[]` anidadas en `danos_vivienda`) y `fotos[]`: NO es sólo
    cabecera. `modo="comprimido"` (default) = SOLO secciones **activas**
    (flag `imp_*` true o con filas — verdad por datos); `modo="completo"`
    entrega siempre las 14 claves."""
    loc = _localidad_por_ref(db, ref)
    if user is not None:
        _check_acceso(db, user, loc["id_edan_localidad"])
    id_loc = loc["id_edan_localidad"]
    row = db.execute(text("""
        SELECT * FROM edan.edan_localidades WHERE id_edan_localidad = :id
    """), {"id": id_loc}).mappings().first()
    data = _resolver_ids(db, _row_public(row))
    # resumen de secciones (conteos)
    resumen = {}
    for tipo, (tabla, _e11, _pk) in TIPOS_SECCION.items():
        n = db.execute(text(f"SELECT count(*) FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                       {"id": id_loc}).scalar()
        if n:
            resumen[tipo] = n
    nv = db.execute(text("""
        SELECT count(*) FROM edan.edan_localidades_viviendas v
        JOIN edan.edan_localidades_danos_vivienda d ON d.id_dano_vivienda = v.id_dano_vivienda
        WHERE d.id_edan_localidad = :id
    """), {"id": id_loc}).scalar()
    if nv:
        resumen["viviendas"] = nv
    # verdad por datos: sección activa si su flag O tiene filas; los 9 grup_*
    # planos se sobrescriben con OR de esas activas (red de lectura).
    activa = {canon: bool(data.get(flag_col) or resumen.get(canon))
              for flag_col, canon in SECCION_FLAG.items()}
    planos = grupos_de_activos(activa)
    for c, v in planos.items():
        data[c] = v

    # filas reales de las secciones (el scope ya se validó arriba una vez)
    comprimido = modo != "completo"
    secciones: dict[str, list] = {}
    for tipo in TIPOS_SECCION:
        if comprimido and not activa[tipo]:
            continue            # comprimido = SOLO secciones activas
        filas = get_seccion_filas(db, user, str(loc["uuid_edan_localidad"]), tipo,
                                  chequear_acceso=False)
        secciones[SECCION_LEGACY[tipo]] = filas
    fotos = db.execute(text("""
        SELECT * FROM edan.fotografias
        WHERE id_edan_localidad = :id AND borrado_logico = false
        ORDER BY fecha_modificacion DESC, id_fotografia DESC
    """), {"id": id_loc}).mappings().all()
    return {
        "cabecera": data,
        **secciones,
        "fotos": [_row_public(f) for f in fotos],
        "secciones_resumen": resumen,
    }


# rangos de fecha combinables (AND) sobre edan.edan_localidades
_RANGOS_FECHA = (
    ("fecha_llenado", "fecha_llenado_desde", ">=", "fl_d"),
    ("fecha_llenado", "fecha_llenado_hasta", "<=", "fl_h"),
    ("fecha_evento", "fecha_evento_desde", ">=", "ev_d"),
    ("fecha_evento", "fecha_evento_hasta", "<=", "ev_h"),
    ("fecha_modificacion", "fecha_modificacion_desde", ">=", "fm_d"),
    ("fecha_modificacion", "fecha_modificacion_hasta", "<=", "fm_h"),
)


def _vals_fecha(fechas: dict) -> dict:
    """{clave_param: valor} de los rangos, tal como llegan de la query."""
    return {clave: fechas.get(clave) for _, clave, _, _ in _RANGOS_FECHA}


def _cond_rangos(alias: str, fechas: dict, params: dict) -> list[str]:
    """Condiciones AND de los rangos de fecha presentes (alias = '' o 'l.').

    La fecha FINAL (`_hasta`, op `<=`) es **inclusiva del día**: sobre columnas
    `timestamp` un `col <= '2026-09-15'` cortaría los registros de esa jornada
    (compararía contra las 00:00). Se traduce a `col < CAST(:x AS date) +
    interval '1 day'`, que incluye el día completo y sigue usando el índice
    (sargable: la función se aplica al parámetro, no a la columna). En columnas
    `date` (`fecha_llenado`/`fecha_evento`) el resultado es idéntico al de `<=`.
    El límite INICIAL (`_desde`, op `>=`) queda igual: arranca a las 00:00 del
    día indicado, así que ya es inclusivo."""
    out = []
    for col, clave, op, nom in _RANGOS_FECHA:
        val = fechas.get(clave)
        if val is not None:
            if op == "<=":
                out.append(f"{alias}{col} < CAST(:{nom} AS date) + interval '1 day'")
            else:
                out.append(f"{alias}{col} >= :{nom}")
            params[nom] = val
    return out


def list_formularios(db: Session, user: dict, skip: int, limit: int, todos: bool,
                     id_departamento: int | None = None, id_provincia: int | None = None,
                     id_municipio: int | None = None, localidad: str | None = None,
                     modo: str = "comprimido",
                     fecha_llenado_desde: datetime | None = None,
                     fecha_llenado_hasta: datetime | None = None,
                     fecha_evento_desde: datetime | None = None,
                     fecha_evento_hasta: datetime | None = None,
                     fecha_modificacion_desde: datetime | None = None,
                     fecha_modificacion_hasta: datetime | None = None) -> tuple[list, int]:
    """Filtros + alcance por rol. ROL 6 (UGR Municipio) = **todo su
    municipio** (`id_municipio` forzado del usuario — API general con
    filtros, para poblar el mapa UGR); 7 = propias; 8 = municipio forzado;
    5/9 = departamento forzado; 1-4 = nacional. Los filtros query se honran
    además del scope forzado (dentro del alcance).

    OJO: esto NO cambia `sync/pull` ni `GET /formularios/estados`, que siguen
    siendo la vista DEL USUARIO (sus propios registros / su bitácora de sync).

    Cada item es el **documento COMPLETO** de la localidad (mismo contrato que
    `GET /formularios/{uuid}/completo`, uuid-first §20.16): `{cabecera, secciones,
    fotos}` — NO sólo la cabecera:

    - `cabecera`: fila pública (`uuid_edan_localidad` + ids; sin `version`/
      `id_local`/`id_seccion`) + **todo `id_*` con su objeto JSON recursivo**
      (§20.16) + `imp_*` y los 9 `grup_*` sincronizados con verdad por datos.
    - secciones (claves legacy, p.ej. `impacto_poblacion`, `danos_vivienda` con
      `viviendas[]` anidadas) — el scope ya se validó a nivel query, así que
      NO se repite el chequeo por localidad (`chequear_acceso=False`).
    - `fotos`: fotos activas de la localidad.

    `modo="comprimido"` (default) = SOLO secciones **activas** (flag `imp_*`
    true o con filas — verdad por datos); `modo="completo"` devuelve SIEMPRE
    las 14 claves de sección (vacías si no hay filas)."""
    sc = _scope_lectura(db, user, geo=(id_departamento, id_municipio))
    base_w, params = _scope_where(sc)
    where = [base_w]
    if id_provincia is not None:
        where.append("id_provincia = :sp"); params["sp"] = id_provincia
    if localidad:
        where.append("localidad ILIKE :l"); params["l"] = f"%{localidad}%"
    where += _cond_rangos("", _vals_fecha({
        "fecha_llenado_desde": fecha_llenado_desde,
        "fecha_llenado_hasta": fecha_llenado_hasta,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_modificacion_desde": fecha_modificacion_desde,
        "fecha_modificacion_hasta": fecha_modificacion_hasta,
    }), params)
    w = " AND ".join(where)
    total = db.execute(text(f"SELECT count(*) FROM edan.edan_localidades WHERE {w}"), params).scalar()
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    qp = dict(params) if todos else {**params, "limit": limit, "skip": skip}
    rows = db.execute(text(f"""
        SELECT uuid_edan_localidad FROM edan.edan_localidades WHERE {w}
        ORDER BY fecha_modificacion DESC NULLS LAST, id_edan_localidad DESC {page}
    """), qp).mappings().all()
    comprimido = modo != "completo"
    items = [get_formulario_completo(db, str(r["uuid_edan_localidad"]), user,
                                     comprimido=comprimido,
                                     chequear_acceso=False)
             for r in rows]
    return items, total


def list_formularios_estados(db: Session, user: dict, skip: int, limit: int, todos: bool,
                             id_departamento: int | None = None, id_provincia: int | None = None,
                             id_municipio: int | None = None, localidad: str | None = None,
                             id_edan_localidad_estado: int | None = None,
                             fecha_modificacion_desde: datetime | None = None,
                             estado: str | None = None,
                             fecha_llenado_desde: datetime | None = None,
                             fecha_llenado_hasta: datetime | None = None,
                             fecha_evento_desde: datetime | None = None,
                             fecha_evento_hasta: datetime | None = None) -> dict:
    """Listado LIGERO de estados de formularios (sync / badges) + resumen.

    Devuelve `{"items": [...], "resumen": {por_estado[], por_grupo[]}, "total": n}`
    con el MISMO scope y filtros para items y resumen:

    - items: cabecera ligera (subset de columnas + `estado_localidad` anidado +
      los 9 `grup_*` SINCRONIZADOS con OR(imp) — sin nodo `grupos`, sin `imp_*`
      para mantener el payload mínimo) + `es_huerfana` + `tiene_cambios`.
    - resumen.por_estado: [{id_edan_localidad_estado, estado, orden, cantidad}].
    - resumen.por_grupo: [{grupo, cantidad}] computado en SQL desde las
      columnas `imp_*` (OR de miembros) — inmune al drift legacy de grup_*.
    - `tiene_cambios` (por fila, SIEMPRE booleano §20.15): `true` si
      `fecha_modificacion` es posterior al watermark `fecha_modificacion_desde`;
      SIN el parámetro es `false` (nunca `null`). El watermark es SOLO
      referencia del flag: NO filtra items/resumen/total (el listado siempre
      devuelve todo el scope; el cliente decide qué bajar según el flag).
    """
    sc = _scope_lectura(db, user, geo=(id_departamento, id_municipio))
    base_w, params = _scope_where(sc, "l")
    where = [base_w]
    if id_provincia is not None:
        where.append("l.id_provincia = :sp"); params["sp"] = id_provincia
    if localidad:
        where.append("l.localidad ILIKE :l"); params["l"] = f"%{localidad}%"
    if id_edan_localidad_estado is not None:
        where.append("l.id_edan_localidad_estado = :est"); params["est"] = id_edan_localidad_estado
    if estado:
        where.append("""l.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE nombre ILIKE :est_nom
        )""")
        params["est_nom"] = f"%{estado}%"
    # OJO: `fecha_modificacion_desde` es SOLO el watermark del flag
    # `tiene_cambios` (§20.15): NO filtra. Por eso aquí va en None.
    where += _cond_rangos("l.", _vals_fecha({
        "fecha_llenado_desde": fecha_llenado_desde,
        "fecha_llenado_hasta": fecha_llenado_hasta,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_modificacion_desde": None,
        "fecha_modificacion_hasta": None,
    }), params)
    w = " AND ".join(where)
    total = db.execute(text(f"SELECT count(*) FROM edan.edan_localidades l WHERE {w}"), params).scalar()
    # resumen con el MISMO scope/filtros (antes de la paginación)
    por_estado = [dict(r) for r in db.execute(text(f"""
        SELECT l.id_edan_localidad_estado, ele.nombre AS estado,
               ele.orden, COUNT(*) AS cantidad
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE {w}
        GROUP BY l.id_edan_localidad_estado, ele.nombre, ele.orden
        ORDER BY ele.orden NULLS LAST, l.id_edan_localidad_estado
    """), params).mappings().all()]
    # por_grupo desde imp_* (OR de miembros en SQL): inmune a grup_* legacy
    grupo_cols = ", ".join(
        f"COUNT(*) FILTER (WHERE {' OR '.join(f'l.{SECCION_FLAG_R[s]}' for s in miembros)}) AS {colg}"
        for colg, miembros in GRUPO_SECCIONES.items())
    grow = db.execute(text(
        f"SELECT {grupo_cols} FROM edan.edan_localidades l WHERE {w}"), params).mappings().first()
    por_grupo = [{"grupo": g, "cantidad": int((grow or {}).get(g) or 0)} for g in GRUPO_SECCIONES]
    # cantidad → paginación; todos=True → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    qp = dict(params) if todos else {**params, "limit": limit, "skip": skip}
    rows = db.execute(text(f"""
        SELECT l.id_edan_localidad, l.uuid_edan_localidad, l.localidad,
               l.id_edan_localidad_estado, l.id_edan, l.id_usuario,
               l.version, l.pendiente_actualizacion, l.pendiente_eliminacion,
               l.fecha_modificacion,
               {", ".join(f"l.{c}" for c in sorted(SECCION_FLAG))},
               {", ".join(f"l.{c}" for c in sorted(GRUPOS_BD))},
               ele.nombre AS estado_nombre, ele.orden AS estado_orden
        FROM edan.edan_localidades l
        LEFT JOIN edan.edan_localidades_estado ele
            ON ele.id_edan_localidad_estado = l.id_edan_localidad_estado
        WHERE {w}
        ORDER BY l.fecha_modificacion DESC NULLS LAST, l.id_edan_localidad DESC {page}
    """), qp).mappings().all()
    data = []
    for r in rows:
        item = _row_public(r)
        item["es_huerfana"] = item.get("id_edan") is None
        if item.get("id_edan_localidad_estado"):
            item["estado_localidad"] = {
                "id_edan_localidad_estado": item["id_edan_localidad_estado"],
                "nombre": item.pop("estado_nombre"),
                "orden": item.pop("estado_orden"),
            }
        else:
            item.pop("estado_nombre", None)
            item.pop("estado_orden", None)
            item["estado_localidad"] = None
        # los 9 grup_* planos se quedan SINCRONIZADOS (OR de imp_ de la fila)
        _sincronizar_grupos_fila(item)
        for _c in SECCION_FLAG:        # imp_* fuera: payload mínimo por fila
            item.pop(_c, None)
        # tiene_cambios: SIEMPRE booleano (§20.15): true solo si la fila es
        # estrictamente posterior al watermark del cliente (watermark igual a
        # la fecha visto => false: el loop de la app ASIENTA y no re-baja).
        # Sin watermark -> false.
        if fecha_modificacion_desde is not None:
            fm = item.get("fecha_modificacion")
            item["tiene_cambios"] = bool(fm and fm > fecha_modificacion_desde.isoformat())
        else:
            item["tiene_cambios"] = False
        data.append(item)
    return {"items": data, "resumen": {"por_estado": por_estado, "por_grupo": por_grupo},
            "total": total}


def delete_formulario(db: Session, user: dict, ref: str) -> dict:
    loc = _localidad_por_ref(db, ref)
    _check_acceso(db, user, loc["id_edan_localidad"], escribir=True)
    try:
        db.execute(text("DELETE FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
                   {"id": loc["id_edan_localidad"]})
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    return {"id_edan_localidad": loc["id_edan_localidad"],
            "uuid_edan_localidad": str(loc["uuid_edan_localidad"]), "borrado": True}


# ===========================================================================
# Formulario completo (todo-en-uno: cabecera + flags + 14 secciones + viviendas)
# ===========================================================================
def _normalizar_seccion_valor(clave: str, valor) -> list:
    """Coerciona una sección a lista de filas (objeto único -> [objeto]; None -> [])."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return [v for v in valor if v is not None]
    return [valor]


def _aplanar_completo(data: dict) -> dict:
    """Acepta además el formato del GET /completo (§20.15): `cabecera: {...}`
    anidada (con objetos FK, grup_*, id interno) y `fotos: [...]`.

    El flujo de la app es GET -> guardarlo -> editar -> PUT: el documento se
    aplana al formato plano de escritura. Solo sobreviven de la cabecera las
    columnas ESCRIBIBLES (_CABECERA_COLS) + las 14 imp_* + el uuid; los
    `grup_*` se derivan en el servidor y `fotos` va por POST /fotografias."""
    cab = data.get("cabecera")
    if not isinstance(cab, dict):
        return data                       # ya está en formato plano
    doc: dict = {}
    for k, v in cab.items():
        if k in _CABECERA_COLS or k in SECCION_FLAG or k == "uuid_edan_localidad":
            doc[k] = v
    for k, v in data.items():
        if k in ("cabecera", "fotos"):
            continue
        doc[k] = v
    return doc


def _validar_completo_payload(data: dict) -> UUID:
    """Reglas ESTÁTICAS 400 del documento exacto — SIEMPRE ANTES de cualquier
    escritura (§20.15): un payload inválido jamás debe dejar estado a medias.

    Reglas (PLAN §20.13 / §20.14 / §20.15):
    - Identidad SOLO por uuid; las 14 imp_* son OBLIGATORIAS y explícitas;
      grup_* NO se envían (el servidor deriva grup := OR(miembros imp_*)).
    - `version` se ignora si llega (LWW: gana el último que llega; sin 409).
    - flag=true ⇒ la sección debe traer ≥1 fila en el payload (400 si falta);
      flag=false ⇒ NO debe traer filas (la purga la decide el documento).
    - sets completos 4 (impacto_poblacion) / 8 (proteccion) intactos.
    - Secciones 1:N: como máximo el array del tamaño natural; 1:1 = objeto
      único (danos_vivienda con hijos viviendas[] 1:N).
    """
    claves = set(data)
    for k in sorted(claves):
        if k.startswith("grup_"):
            raise HTTPException(status_code=400, detail=(
                f"Los flags de grupo ({k!r}) NO se envían en POST /formularios/completo: "
                f"el servidor los deriva. Envía solo las 14 imp_* de sección."))
    # también se rechazan los nombres legacy de agrupado (imp_poblacion, …)
    for k in sorted(claves & (GRUPOS_BD | (set(GRUPO_WIRE_LEGACY) - {"imp_proteccion"}))):
        raise HTTPException(status_code=400, detail=(
            f"El flag {k!r} es de GRUPO y el servidor lo deriva. Envía solo las 14 "
            f"imp_* de sección: {sorted(SECCION_FLAG)}"))
    conocidas = (set(_CABECERA_COLS) | set(SECCION_FLAG) | set(SECCION_ALIAS)
                 # aceptadas y descartadas (el servidor fija la suya):
                 | {"uuid_edan_localidad", "version", "fecha_modificacion"})
    extra = claves - conocidas
    if extra:
        raise HTTPException(status_code=400, detail=f"Campo no reconocido: {sorted(extra)}")

    faltantes = [f for f in SECCION_FLAG if data.get(f) is None]
    if faltantes:
        raise HTTPException(status_code=400, detail=(
            f"Faltan flags de sección en POST /formularios/completo (se envían las 14 "
            f"con true/false): {faltantes}"))
    for f in SECCION_FLAG:
        if not isinstance(data.get(f), bool):
            raise HTTPException(status_code=400, detail=f"{f} debe ser true o false")

    uuid_loc = _parse_uuid(data.get("uuid_edan_localidad"), "uuid_edan_localidad")

    # ¿el payload trae filas de esa sección?
    def _envia_filas(sec: str) -> bool:
        for k, v in data.items():
            if v is None or SECCION_ALIAS.get(_norm_tipo(k)) != sec:
                continue
            if _normalizar_seccion_valor(k, v):
                return True
        return False

    # flag↔fila (documento exacto): flag true exige filas EN EL PAYLOAD
    for flag, sec in SECCION_FLAG.items():
        if data.get(flag) is True and not _envia_filas(sec):
            raise HTTPException(status_code=400, detail=(
                f"El flag {flag}=true pero la sección {sec} no trae filas en el "
                f"payload. Documento exacto: envíe las filas o declare {flag}=false "
                f"(lo purga)."))

    for clave_api, valor in data.items():
        if valor is None:
            continue
        tipo = SECCION_ALIAS.get(_norm_tipo(clave_api))
        if tipo is None:
            continue
        tabla, es_11, _pk = TIPOS_SECCION[tipo]
        filas = _normalizar_seccion_valor(clave_api, valor)
        flag_col = SECCION_FLAG_R.get(tipo)
        flag_val = data.get(flag_col) if flag_col else None
        # flag=false + filas -> 400 (simétrico a la regla flag↔fila)
        if flag_val is not True:
            if filas:
                raise HTTPException(status_code=400, detail=(
                    f"La sección {clave_api} trae filas pero su flag {flag_col}=false. "
                    f"La sección solo se escribe si {flag_col}=true; si no hay datos, "
                    f"envíe {flag_col}=false y no incluya la sección."))
            continue

        # Set completo por catálogo: impacto_poblacion = 4 filas
        # (id_grupo_etario 1-4); proteccion = 8 filas (catálogo 1-8).
        if tipo == "impacto_poblacion" and filas:
            ids = [f.get("id_grupo_etario") for f in filas]
            if len(filas) != 4 or set(ids) != {1, 2, 3, 4}:
                raise HTTPException(status_code=400, detail=(
                    f"impacto_poblacion con {flag_col}=true debe enviar las 4 filas "
                    f"completas (id_grupo_etario 1,2,3,4); se recibieron {len(filas)} "
                    f"con id_grupo_etario={sorted(x for x in ids if x is not None)}."))
        if tipo == "proteccion" and filas:
            ids = [f.get("id_grupo_vulnerable_catalogo") for f in filas]
            if len(filas) != 8 or set(ids) != {1, 2, 3, 4, 5, 6, 7, 8}:
                raise HTTPException(status_code=400, detail=(
                    f"proteccion con {flag_col}=true debe enviar las 8 filas "
                    f"completas (id_grupo_vulnerable_catalogo 1-8); se recibieron "
                    f"{len(filas)} con catálogo={sorted(x for x in ids if x is not None)}."))

        if es_11 and len(filas) > 1:
            raise HTTPException(status_code=400, detail=(
                f"La sección {clave_api} es 1:1 (con hijos 1:N en el caso de "
                f"danos_vivienda): se recibió un array de {len(filas)} filas; "
                f"envía un solo objeto (o array de 1)."))

    return uuid_loc


def _aplicar_completo(db: Session, user: dict, data: dict, uuid_loc: UUID) -> dict:
    """Escribe el documento exacto (mutación). Asume payload YA validado por
    `_validar_completo_payload` (POST crea / PUT aplica sobre lo existente)."""
    # id_usuario es OPCIONAL: si no llega, upsert_formulario usa el token.
    # Cabecera sin flags (los 23 se reconcilian al final, tras los datos)
    cab = {k: v for k, v in data.items() if k in _CABECERA_COLS and k not in GRUPOS_BD}
    cab["uuid_edan_localidad"] = data["uuid_edan_localidad"]
    form = upsert_formulario(db, user, cab, validar=False)
    cabecera = form["cabecera"]
    id_loc = cabecera["id_edan_localidad"]
    ref_loc = str(cabecera["uuid_edan_localidad"])

    # uuids intentados por sección 1:N (reemplazo exacto) + viviendas por dano
    payload_uuids: dict[str, set[str]] = {sec: set() for sec in TIPOS_SECCION}
    viviendas_payload: dict[int, set[str]] = {}

    resultados: list[dict] = []
    for clave_api, valor in data.items():
        if valor is None:
            continue
        tipo = SECCION_ALIAS.get(_norm_tipo(clave_api))
        if tipo is None:
            continue
        tabla, es_11, _pk = TIPOS_SECCION[tipo]
        filas = _normalizar_seccion_valor(clave_api, valor)

        # Solo se ESCRIBE la sección si su flag imp_* es true (contrato /completo);
        # las reglas flag↔fila / sets / 1:1 ya las validó _validar_completo_payload
        flag_col = SECCION_FLAG_R.get(tipo)
        flag_val = data.get(flag_col) if flag_col else None
        if flag_val is not True:
            continue

        for item in filas:
            try:
                item_datos = dict(item or {})
                viviendas = item_datos.pop("viviendas", None)
                # uuids intentados ANTES del upsert: un conflicto (409) no debe
                # convertir la fila en "no enviada" y provocar su borrado.
                uu_item = item_datos.get("uuid_registro")
                if not es_11 and uu_item:
                    payload_uuids[tipo].add(str(uu_item))
                fila = upsert_seccion(db, user, ref_loc, tipo, item_datos)
                uu_dano = str(fila.get("uuid_registro"))
                resultados.append({"indice": len(resultados), "tipo": tipo,
                                   "seccion": clave_api, "uuid_registro": uu_dano,
                                   "estado": "aplicado", "message": "OK"})
                if tipo == "danos_vivienda":
                    vv_set = set()
                    if viviendas is not None:
                        for vv in _normalizar_seccion_valor("viviendas", viviendas):
                            if (vv or {}).get("uuid_registro"):
                                vv_set.add(str(vv["uuid_registro"]))
                            try:
                                v = upsert_vivienda(db, user, uu_dano, dict(vv))
                                resultados.append({"indice": len(resultados), "tipo": "vivienda",
                                                   "uuid_registro": str(v.get("uuid_registro")),
                                                   "estado": "aplicado", "message": "OK"})
                            except HTTPException as e:
                                db.rollback()
                                est = "conflicto" if e.status_code == 409 else "error"
                                msg = e.detail.get("message") if isinstance(e.detail, dict) else str(e.detail)
                                resultados.append({"indice": len(resultados), "tipo": "vivienda",
                                                   "uuid_registro": str(vv.get("uuid_registro", "")),
                                                   "estado": est, "message": msg})
                                continue
                    id_d = fila.get("id_dano_vivienda")
                    if id_d is not None:
                        viviendas_payload[int(id_d)] = vv_set
            except HTTPException as e:
                db.rollback()
                est = "conflicto" if e.status_code == 409 else "error"
                msg = e.detail.get("message") if isinstance(e.detail, dict) else str(e.detail)
                resultados.append({"indice": len(resultados), "tipo": tipo,
                                   "seccion": clave_api,
                                   "uuid_registro": str((item or {}).get("uuid_registro", "")),
                                   "estado": est, "message": msg})
                continue

    # ---- fase final (una transacción): purga/reemplazo + flags + validación
    for flag, sec in SECCION_FLAG.items():
        tabla, es_11, _pk = TIPOS_SECCION[sec]
        uu_exis = [str(r[0]) for r in db.execute(text(
            f"SELECT uuid_registro FROM edan.{tabla} WHERE id_edan_localidad = :id"),
            {"id": id_loc})]
        if data.get(flag) is not True:
            # imp=false ⇒ purga total (1:1 incluidas) + fotos a borrado_logico
            _marcar_fotos_borradas(db, sec, uu_exis)
            db.execute(text(f"DELETE FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                       {"id": id_loc})
        elif es_11:
            # imp=true 1:1 ⇒ exacto: debe quedar SOLO la fila que upsert escribió
            # (si había filas legacy múltiples, se adopta la primera y el resto se borra)
            keep = db.execute(text(
                f"SELECT uuid_registro FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                {"id": id_loc}).scalar()
            keep = str(keep) if keep else None
            extras = [u for u in uu_exis if u != keep]
            _marcar_fotos_borradas(db, sec, extras)
            if extras:
                db.execute(text(f"""
                    DELETE FROM edan.{tabla}
                    WHERE id_edan_localidad = :id AND uuid_registro = ANY(CAST(:uu AS uuid[]))
                """), {"id": id_loc, "uu": extras})
        else:
            # imp=true 1:N ⇒ reemplazo exacto: borra las no enviadas
            permitidos = payload_uuids.get(sec) or set()
            a_borrar = [u for u in uu_exis if u not in permitidos]
            _marcar_fotos_borradas(db, sec, a_borrar)
            if a_borrar:
                db.execute(text(f"""
                    DELETE FROM edan.{tabla}
                    WHERE id_edan_localidad = :id AND uuid_registro = ANY(CAST(:uu AS uuid[]))
                """), {"id": id_loc, "uu": a_borrar})
    # viviendas (hijas 1:N de danos_vivienda 1:1): reemplazo exacto por dano
    for id_d, permitidos in viviendas_payload.items():
        uu_exis = [str(r[0]) for r in db.execute(text(
            "SELECT uuid_registro FROM edan.edan_localidades_viviendas "
            "WHERE id_dano_vivienda = :d"), {"d": id_d})]
        a_borrar = [u for u in uu_exis if u not in permitidos]
        _marcar_fotos_borradas(db, "vivienda", a_borrar)
        if a_borrar:
            db.execute(text("""
                DELETE FROM edan.edan_localidades_viviendas
                WHERE id_dano_vivienda = :d AND uuid_registro = ANY(CAST(:uu AS uuid[]))
            """), {"d": id_d, "uu": a_borrar})

    # Flags: el documento declara las 14 EXACTAMENTE; grup_* := OR(miembros)
    cambios: dict[str, bool] = {flag: bool(data.get(flag)) for flag in SECCION_FLAG}
    cambios.update(_grupos_planos_desde_flags(cambios))
    actual = db.execute(text(
        "SELECT * FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
        {"id": id_loc}).mappings().first()
    diff = [k for k, v in cambios.items() if actual[k] != v]
    if diff:
        sets = ", ".join(f"{k} = :{k}" for k in diff)
        db.execute(text(f"""
            UPDATE edan.edan_localidades SET {sets}, fecha_modificacion = now()
            WHERE id_edan_localidad = :id
        """), {**{k: cambios[k] for k in diff}, "id": id_loc})
    _exigir_enviados_validos(db, id_loc)
    db.commit()

    return {
        "resultados": resultados,
        "aplicados": sum(1 for r in resultados if r["estado"] == "aplicado"),
        "conflictos": sum(1 for r in resultados if r["estado"] == "conflicto"),
        "errores": sum(1 for r in resultados if r["estado"] == "error"),
        "formulario": get_formulario_completo(db, ref_loc, user),
    }


def upsert_formulario_completo(db: Session, user: dict, data: dict) -> dict:
    """POST /formularios/completo — SOLO CREACIÓN del documento exacto (§20.15).

    - Reglas 400 (estáticas) PRIMERO; después, si el uuid ya existe en el
      servidor -> 409 "ya existe; use PUT /formularios/completo" (nunca edita).
    - Documento exacto: imp_* declaradas EXACTAMENTE; imp=false purga sus filas
      (1:1 incluidas), fotos a borrado_logico=true y viviendas en cascada;
      secciones 1:N = reemplazo exacto por uuid; danos_vivienda 1:1 con
      viviendas[] 1:N (sin `viviendas` = se borran las hijas); `fotografia`
      aceptada y DESCARTADA (la sube POST /fotografias); `version` ignorada.
    - Estados 2/3/4/5: cada grupo activo exige algún imp miembro con ≥1 fila
      (validado post-mutación; 400 + rollback de purga/flags).
    """
    data = _aplanar_completo(data)
    uuid_loc = _validar_completo_payload(data)
    existente = db.execute(text("""
        SELECT id_edan_localidad FROM edan.edan_localidades
        WHERE uuid_edan_localidad = :u
    """), {"u": uuid_loc}).mappings().first()
    if existente:
        raise HTTPException(status_code=409, detail=(
            f"El formulario ya existe (uuid_edan_localidad={uuid_loc}). "
            f"POST /formularios/completo es SOLO creación: para editar el documento "
            f"completo use PUT /formularios/completo con el mismo JSON."))
    return _aplicar_completo(db, user, data, uuid_loc)


def put_formulario_completo(db: Session, user: dict, data: dict) -> dict:
    """PUT /formularios/completo — EDICIÓN con detección de cambios (§20.15).

    Mismo JSON que POST (uuid en el cuerpo). El servidor compara el payload
    con lo almacenado y SOLO escribe lo que difiere:
    - Sin cambios reales -> 200 `hubo_cambios=false`, `cambios=[]`,
      `resultados=[]` y CERO escrituras (fecha_modificacion intacta en TODA la
      cabecera y TODAS las filas: sin falsos tiene_cambios en /estados).
    - Con cambios -> aplica el documento exacto (LWW) y devuelve
      `hubo_cambios=true` + `cambios` (secciones afectadas, "cabecera", …).
    - Sin registro -> 404 (PUT solo edita; para crear use POST /completo).
    - Reglas 400 (estáticas) ANTES de escribir; acceso de escritura verificado
      incluso en el no-op.
    """
    data = _aplanar_completo(data)
    uuid_loc = _validar_completo_payload(data)
    existente = db.execute(text("SELECT * FROM edan.edan_localidades "
                                "WHERE uuid_edan_localidad = :u"),
                           {"u": uuid_loc}).mappings().first()
    if not existente:
        raise HTTPException(status_code=404, detail=(
            f"El formulario no existe (uuid_edan_localidad={uuid_loc}). "
            f"PUT /formularios/completo solo edita: para crearlo use "
            f"POST /formularios/completo."))
    _check_acceso(db, user, existente["id_edan_localidad"], escribir=True)

    cambios = _diff_completo(db, data, existente)
    if not cambios:
        return {"hubo_cambios": False, "cambios": [], "resultados": [],
                "aplicados": 0, "conflictos": 0, "errores": 0,
                "formulario": get_formulario_completo(db, str(uuid_loc), user)}

    res = _aplicar_completo(db, user, data, uuid_loc)
    return {"hubo_cambios": True, "cambios": cambios, **res}


def _diff_completo(db: Session, data: dict, loc: dict) -> list[str]:
    """Qué habría que escribir si se aplicara el documento (PUT /completo).

    Devuelve [] si el payload es EQUIVALENTE a lo almacenado (no-op: cero
    escrituras) o la lista de qué cambiaría: "cabecera" y/o el nombre de cada
    sección con cambios reales de flag, filas o viviendas. Conservador ante la
    duda (compara solo lo que el upsert escribiría)."""
    cambios: list[str] = []
    id_loc = loc["id_edan_localidad"]

    # cabecera: solo campos escribibles enviados (None/"" no se escriben;
    # id_usuario es inmutable -> no cuenta como cambio)
    for k, v in data.items():
        if k in _CABECERA_COLS and k != "id_usuario" and v not in (None, ""):
            if not _cmp_iguales(loc.get(k), v):
                cambios.append("cabecera")
                break

    for flag, sec in SECCION_FLAG.items():
        if data.get(flag) is not True:
            # flag=false: cambia solo si hay filas que purgar
            tabla = TIPOS_SECCION[sec][0]
            n = db.execute(text(
                f"SELECT count(*) FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                {"id": id_loc}).scalar()
            if n:
                cambios.append(sec)
            continue
        if not loc.get(flag):
            cambios.append(sec)      # se activa (además de lo que traigan las filas)
            continue
        if _diff_seccion_filas(db, data, sec, loc):
            cambios.append(sec)
    return cambios


def _diff_seccion_filas(db: Session, data: dict, sec: str, loc: dict) -> bool:
    """¿Las filas del payload difieren de las almacenadas de esa sección?"""
    tabla, es_11, _pk = TIPOS_SECCION[sec]
    filas_payload: list[dict] = []
    for clave_api, valor in data.items():
        if valor is None or SECCION_ALIAS.get(_norm_tipo(clave_api)) != sec:
            continue
        filas_payload.extend(it or {} for it in _normalizar_seccion_valor(clave_api, valor))
    db_rows = [dict(r) for r in db.execute(
        text(f"SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id"),
        {"id": loc["id_edan_localidad"]}).mappings().all()]

    if es_11:
        if not db_rows:
            return bool(filas_payload)     # no hay fila: crear si el payload trae
        if not filas_payload:
            return True                    # (imposible: flag=true exige filas)
        # 1:1: comparar SOLO campos (el uuid no se escribe: converge siempre)
        if _diff_fila(sec, db_rows[0], filas_payload[0]):
            return True
        # danos_vivienda 1:1: además comparan sus HIJAS viviendas[] 1:N
        # (sin nodo viviendas = purga de hijas; una hija distinta = cambio)
        if sec == "danos_vivienda":
            id_d = db_rows[0].get("id_dano_vivienda")
            if id_d is None:
                return True
            return _diff_hijas(db, id_d, filas_payload[0].get("viviendas"))
        return False

    dbmap = {str(r["uuid_registro"]): r for r in db_rows}
    vistos: set[str] = set()
    for item in filas_payload:
        uu = str(item.get("uuid_registro") or "")
        if not uu or uu not in dbmap:
            return True                    # fila nueva (o sin uuid -> se crea)
        vistos.add(uu)
        if _diff_fila(sec, dbmap[uu], item):
            return True
    if set(dbmap) - vistos:
        return True                        # filas no enviadas -> se borran
    return False


def _diff_fila(sec: str, dbrow: dict, item: dict) -> bool:
    """Compara SOLO las claves que el upsert escribiría del payload."""
    for k, v in item.items():
        if k in ("uuid_registro", "version", "uuid_edan_localidad",
                 "viviendas", "fotografia"):
            continue
        if k in _SISTEMA or k in _FK_OBJETOS:
            continue                      # servidor / objetos FK anidados (GET)
        if sec == "danos_vivienda" and k in ("coordenada_lat", "coordenada_lon"):
            continue                      # las coords viven en las hijas viviendas[]
        if not _cmp_iguales(dbrow.get(k), v):
            return True
    return False


def _diff_hijas(db: Session, id_dano, vv_payload) -> bool:
    """¿Las viviendas[] del payload difieren de las hijas almacenadas?"""
    db_hijas = {str(r["uuid_registro"]): dict(r) for r in db.execute(text(
        "SELECT * FROM edan.edan_localidades_viviendas WHERE id_dano_vivienda = :d"),
        {"d": id_dano}).mappings().all()}
    if vv_payload is None:
        return bool(db_hijas)             # sin nodo viviendas = purga de hijas
    plist = [v or {} for v in _normalizar_seccion_valor("viviendas", vv_payload)]
    vistos: set[str] = set()
    for it in plist:
        uu = str(it.get("uuid_registro") or "")
        if not uu or uu not in db_hijas:
            return True
        vistos.add(uu)
        for k in ("tipo_dano", "coordenada_lat", "coordenada_lon"):
            if k in it and not _cmp_iguales(db_hijas[uu].get(k), it[k]):
                return True
    return bool(set(db_hijas) - vistos)    # hijas no enviadas -> se borran


def get_formulario_completo(db: Session, ref: str, user: dict, comprimido: bool = False,
                            chequear_acceso: bool = True) -> dict:
    """GET /formularios/{uuid}/completo — {cabecera, 14 secciones, fotos}.

    - `comprimido=true` = SOLO secciones **activas** (flag `imp_*` true O con
      filas — verdad por datos); las inactivas se omiten. Sin comprimir,
      van SIEMPRE las 14 claves (vacías si no hay filas).
    - SIN nodo `grupos`: los 9 `grup_*` van en la cabecera, SIEMPRE
      sincronizados con OR(imp|filas) (red de lectura) — única cara pública.
    - Las flags `imp_*` de la cabecera reflejan "verdad por datos" (flag o
      sección con filas).
    - `chequear_acceso=False`: para las vistas de EDAN padre (§20.17), donde
      el scope ya se validó a nivel EDAN (`validar_scope_edan`) — un UGR que
      consolida localidades de otros autores las ve dentro de SU EDAN (igual
      que la API vieja, que no chequeaba por localidad)."""
    loc = _localidad_por_ref(db, ref)
    if chequear_acceso:
        _check_acceso(db, user, loc["id_edan_localidad"])
    id_loc = loc["id_edan_localidad"]
    row = db.execute(text("SELECT * FROM edan.edan_localidades WHERE id_edan_localidad = :id"),
                     {"id": id_loc}).mappings().first()
    base = _row_public(row)

    # verdad por datos: seccion activa si su flag o tiene filas
    activa: dict[str, bool] = {}
    for flag, sec in SECCION_FLAG.items():
        tabla, _e, _p = TIPOS_SECCION[sec]
        n = db.execute(text(f"SELECT count(*) FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                       {"id": id_loc}).scalar()
        activa[sec] = bool(base.get(flag) or n)

    # cabecera = columnas públicas de la tabla (sin `version`/`id_local`/
    # `id_seccion`: las APIs nuevas van SOLO con uuid) + objetos JSON
    # anidados de
    # cada FK RECURSIVAMENTE (§20.16: id_usuario -> usuario, id_importacion
    # -> importacion; y dentro
    # de los objetos, usuario -> rol, municipio -> departamento/provincia,
    # edan -> estado_edan/municipio/tipo_evento); flags y grup_* sincronizados
    cabecera = _resolver_ids(db, dict(base))
    for flag, sec in SECCION_FLAG.items():
        cabecera[flag] = activa[sec]
    for c, v in grupos_de_activos(activa).items():
        cabecera[c] = v

    secciones = {}
    for tipo in TIPOS_SECCION:
        if comprimido and not activa[tipo]:
            continue            # comprimido = SOLO secciones activas
        filas = get_seccion_filas(db, user, str(loc["uuid_edan_localidad"]), tipo,
                                  chequear_acceso=chequear_acceso)
        secciones[SECCION_LEGACY[tipo]] = filas

    fotos = db.execute(text("""
        SELECT * FROM edan.fotografias
        WHERE id_edan_localidad = :id AND borrado_logico = false
        ORDER BY fecha_modificacion DESC, id_fotografia DESC
    """), {"id": id_loc}).mappings().all()

    return {
        "cabecera": cabecera,
        **secciones,
        "fotos": [_row_public(f) for f in fotos],
    }


# ===========================================================================
# Secciones (14 tablas) — LWW: gana el último que llega (sin versiones/409)
# ===========================================================================
def upsert_seccion(db: Session, user: dict, uuid_loc_ref: str, tipo: str, data: dict,
                   uuid_fila: str | None = None) -> dict:
    tipo = _norm_tipo(tipo)
    if tipo not in TIPOS_SECCION:
        raise HTTPException(status_code=400, detail=f"Tipo de sección inválido: {tipo}. Válidos: {sorted(TIPOS_SECCION)}")
    tabla, es_11, pk = TIPOS_SECCION[tipo]
    loc = _localidad_por_ref(db, uuid_loc_ref)
    _check_acceso(db, user, loc["id_edan_localidad"], escribir=True)

    uuid_registro = _parse_uuid(data.get("uuid_registro") or uuid_fila, "uuid_registro")

    permitidas = _cols(db, tabla)
    campos = {}
    for k, v in data.items():
        if k in ("uuid_registro", "version", "uuid_edan_localidad"):
            continue
        if k in _CLAVES_DESCARTADAS:
            continue  # fotografia: aceptada y descartada (va en POST /fotografias)
        if k in _SISTEMA or k in _FK_OBJETOS:
            continue  # columnas servidor / objetos FK del GET: descartadas (ida y vuelta)
        if k not in permitidas:
            raise HTTPException(status_code=400, detail=f"Campo desconocido o no escribible para {tipo}: {k!r}")
        campos[k] = v

    # danos_vivienda es 1:1 y sus coordenadas son de los hijos (viviendas[]):
    # la fila padre nunca guarda coordenada_lat/lon (se ignoran al escribir)
    if tipo == "danos_vivienda":
        campos.pop("coordenada_lat", None)
        campos.pop("coordenada_lon", None)

    if es_11:
        existente = db.execute(text(f"""
            SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id
        """), {"id": loc["id_edan_localidad"]}).mappings().first()
    else:
        existente = db.execute(text(f"""
            SELECT * FROM edan.{tabla}
            WHERE uuid_registro = :u AND id_edan_localidad = :id
        """), {"u": uuid_registro, "id": loc["id_edan_localidad"]}).mappings().first()

    try:
        if existente:
            # LWW + IDEMPOTENCIA (§20.15): solo escribir lo que REALMENTE
            # difiere. Payload idéntico => SIN UPDATE => fecha_modificacion
            # intacta (sin falsos tiene_cambios en /estados ni ruido en pull).
            diffs = {k: v for k, v in campos.items()
                     if not _cmp_iguales(existente.get(k), v)}
            if diffs:
                sets = ", ".join(f"{k} = :{k}" for k in diffs)
                db.execute(text(f"""
                    UPDATE edan.{tabla} SET {sets}, fecha_modificacion = now()
                    WHERE {pk} = :_pk
                """), {**diffs, "_pk": existente[pk]})
        else:
            cols = ["id_edan_localidad", "uuid_registro", "id_seccion", "fecha_modificacion", *campos]
            col_names = ", ".join(cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            params = {**campos,
                      "id_edan_localidad": loc["id_edan_localidad"],
                      "uuid_registro": uuid_registro,
                      "id_seccion": str(uuid4()),     # único por fila (idx_seccion_* global)
                      "fecha_modificacion": datetime.now()}
            db.execute(text(f"""
                INSERT INTO edan.{tabla} ({col_names})
                VALUES ({placeholders})
            """), params)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    return get_seccion_fila(db, user, uuid_loc_ref, tipo, str(uuid_registro) if not es_11 else None)


def get_seccion_filas(db: Session, user: dict, uuid_loc_ref: str, tipo: str,
                      chequear_acceso: bool = True) -> list[dict]:
    tipo = _norm_tipo(tipo)
    if tipo not in TIPOS_SECCION:
        raise HTTPException(status_code=400, detail="Tipo de sección inválido: " + tipo)
    tabla, _e, _pk = TIPOS_SECCION[tipo]
    loc = _localidad_por_ref(db, uuid_loc_ref)
    if chequear_acceso:
        _check_acceso(db, user, loc["id_edan_localidad"])
    rows = db.execute(text(f"""
        SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id
        ORDER BY 1
    """), {"id": loc["id_edan_localidad"]}).mappings().all()
    result = []
    for r in rows:
        d = _resolver_ids(db, _row_public(r))
        # modo offline: cadena de uuids sin GET extra (localidad ↔ fila)
        d["uuid_edan_localidad"] = str(loc["uuid_edan_localidad"])
        if tipo == "danos_vivienda":
            d["viviendas"] = get_viviendas(db, user, str(r["uuid_registro"]),
                                           chequear_acceso=chequear_acceso)
            if d["viviendas"]:               # el padre omite coords solo si tiene hijas
                d["coordenada_lat"] = None
                d["coordenada_lon"] = None
        result.append(d)
    return result


def get_seccion_fila(db: Session, user: dict, uuid_loc_ref: str, tipo: str, uuid_fila: str | None) -> dict:
    tipo = _norm_tipo(tipo)
    if tipo not in TIPOS_SECCION:
        raise HTTPException(status_code=400, detail=f"Tipo de sección inválido: {tipo}")
    tabla, es_11, pk = TIPOS_SECCION[tipo]
    loc = _localidad_por_ref(db, uuid_loc_ref)
    _check_acceso(db, user, loc["id_edan_localidad"])
    if es_11:
        row = db.execute(text(f"SELECT * FROM edan.{tabla} WHERE id_edan_localidad = :id"),
                         {"id": loc["id_edan_localidad"]}).mappings().first()
    else:
        u = _parse_uuid(uuid_fila, "uuid_registro")
        row = db.execute(text(f"""
            SELECT * FROM edan.{tabla} WHERE uuid_registro = :u AND id_edan_localidad = :id
        """), {"u": u, "id": loc["id_edan_localidad"]}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Fila de {tipo} no encontrada")
    d = _resolver_ids(db, _row_public(row))
    # modo offline: cadena de uuids sin GET extra (localidad ↔ fila)
    d["uuid_edan_localidad"] = str(loc["uuid_edan_localidad"])
    if tipo == "danos_vivienda":
        d["viviendas"] = get_viviendas(db, user, str(row["uuid_registro"]))
        if d["viviendas"]:                   # el padre omite coords solo si tiene hijas
            d["coordenada_lat"] = None
            d["coordenada_lon"] = None
    return d


def delete_seccion(db: Session, user: dict, uuid_loc_ref: str, tipo: str, uuid_fila: str,
                   validar: bool = True) -> dict:
    """Borrado físico de una fila 1:N por uuid_registro (1:1 → 400; se
    sobrescriben). Borrar la fila de daños_vivienda elimina sus viviendas
    (FK CASCADE) y las fotos de la fila van a borrado_logico (pull).
    Post-mutación aplica la regla de enviados (estados 2/3/4/5): si el borrado
    dejaría un grupo activo sin filas → 400 y rollback (salvo sync_push:
    validar=False)."""
    tipo = _norm_tipo(tipo)
    if tipo not in TIPOS_SECCION:
        raise HTTPException(status_code=400, detail=f"Tipo de sección inválido: {tipo}")
    tabla, es_11, pk = TIPOS_SECCION[tipo]
    if es_11 and tipo != "danos_vivienda":
        raise HTTPException(status_code=400, detail=(
            f"La sección {tipo} es 1:1 con el formulario: no tiene filas que borrar "
            "(sus campos se sobrescriben con POST/PUT)"))
    loc = _localidad_por_ref(db, uuid_loc_ref)
    _check_acceso(db, user, loc["id_edan_localidad"], escribir=True)
    u = _parse_uuid(uuid_fila, "uuid_registro")
    try:
        res = db.execute(text(f"""
            DELETE FROM edan.{tabla}
            WHERE id_edan_localidad = :id AND uuid_registro = :u
        """), {"id": loc["id_edan_localidad"], "u": u})
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Fila de {tipo} no encontrada: {uuid_fila}")
        # fotos de la fila: borrado logico (viajan por pull para otros dispositivos);
        # danos_vivienda además marca las de sus viviendas hijas (cascada)
        _marcar_fotos_borradas(db, tipo, [str(u)])
        if validar:
            _exigir_enviados_validos(db, loc["id_edan_localidad"])
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    nota = ("Las viviendas hijas se eliminaron en cascada y los conteos del "
            "padre se recalculan" if tipo == "danos_vivienda" else None)
    out = {"tabla": tabla, "uuid_registro": str(u), "borrado": True,
           # modo offline: cadena de uuids sin GET extra
           "uuid_edan_localidad": str(loc["uuid_edan_localidad"]),
           "id_edan_localidad": int(loc["id_edan_localidad"])}
    if nota:
        out["nota"] = nota
    return out


# ===========================================================================
# Viviendas (detalle 1:N, v2.53.0)
# ===========================================================================
def _uuid_localidad(db: Session, id_loc: int) -> str | None:
    """uuid_edan_localidad por id (para enriquecer respuestas offline)."""
    u = db.execute(text("SELECT uuid_edan_localidad FROM edan.edan_localidades "
                        "WHERE id_edan_localidad = :i"), {"i": id_loc}).scalar()
    return str(u) if u else None


def _dano_por_ref(db: Session, ref: str) -> dict:
    u = None
    if ref and not str(ref).isdigit():
        u = _parse_uuid(ref, "uuid_dano_vivienda")
    row = db.execute(text("""
        SELECT id_dano_vivienda, uuid_registro, id_edan_localidad, version
        FROM edan.edan_localidades_danos_vivienda WHERE
    """ + (" uuid_registro = :u" if u else " id_dano_vivienda = :i")),
        {"u": u, "i": None if u else int(ref)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Fila de daños de vivienda no encontrada: {ref}")
    return dict(row)


def upsert_vivienda(db: Session, user: dict, ref_dano: str, data: dict,
                    uuid_vivienda: str | None = None) -> dict:
    dano = _dano_por_ref(db, ref_dano)
    _check_acceso(db, user, dano["id_edan_localidad"], escribir=True)
    uuid_v = _parse_uuid(data.get("uuid_registro") or uuid_vivienda, "uuid_registro")
    tipo_dano = data.get("tipo_dano")
    if tipo_dano not in ("TOTAL", "PARCIAL"):
        raise HTTPException(status_code=400, detail="tipo_dano debe ser TOTAL o PARCIAL")

    existente = db.execute(text("""
        SELECT * FROM edan.edan_localidades_viviendas
        WHERE uuid_registro = :u AND id_dano_vivienda = :d
    """), {"u": uuid_v, "d": dano["id_dano_vivienda"]}).mappings().first()

    # fotografia en el payload: aceptada y descartada (la sube POST /fotografias)
    campos = {k: data.get(k) for k in ("coordenada_lat", "coordenada_lon") if data.get(k) is not None}

    try:
        if existente:
            # LWW + IDEMPOTENCIA (§20.15): solo escribir lo que difiere
            diffs = {"tipo_dano": tipo_dano} if not _cmp_iguales(existente.get("tipo_dano"), tipo_dano) else {}
            diffs.update({k: v for k, v in campos.items()
                          if not _cmp_iguales(existente.get(k), v)})
            if diffs:
                sets = ", ".join(f"{k} = :{k}" for k in diffs)
                db.execute(text(f"""
                    UPDATE edan.edan_localidades_viviendas SET {sets}, fecha_modificacion = now()
                    WHERE id_vivienda = :_pk
                """), {**diffs, "_pk": existente["id_vivienda"]})
        else:
            cols = ["id_dano_vivienda", "uuid_registro", "tipo_dano", "fecha_modificacion", *campos]
            col_names = ", ".join(cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            db.execute(text(f"""
                INSERT INTO edan.edan_localidades_viviendas ({col_names})
                VALUES ({placeholders})
            """), {**campos, "id_dano_vivienda": dano["id_dano_vivienda"], "uuid_registro": uuid_v,
                   "tipo_dano": tipo_dano, "fecha_modificacion": datetime.now()})
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    return get_vivienda(db, user, ref_dano, str(uuid_v))


def get_viviendas(db: Session, user: dict, ref_dano: str,
                  chequear_acceso: bool = True) -> list[dict]:
    dano = _dano_por_ref(db, ref_dano)
    if chequear_acceso:
        _check_acceso(db, user, dano["id_edan_localidad"])
    rows = db.execute(text("""
        SELECT * FROM edan.edan_localidades_viviendas WHERE id_dano_vivienda = :d ORDER BY id_vivienda
    """), {"d": dano["id_dano_vivienda"]}).mappings().all()
    u_loc = _uuid_localidad(db, dano["id_edan_localidad"])
    return [{**_row_public(r), "uuid_dano_vivienda": str(dano["uuid_registro"]),
             "uuid_edan_localidad": u_loc} for r in rows]


def get_vivienda(db: Session, user: dict, ref_dano: str, uuid_v: str) -> dict:
    dano = _dano_por_ref(db, ref_dano)
    _check_acceso(db, user, dano["id_edan_localidad"])
    u = _parse_uuid(uuid_v, "uuid_vivienda")
    row = db.execute(text("""
        SELECT * FROM edan.edan_localidades_viviendas
        WHERE uuid_registro = :u AND id_dano_vivienda = :d
    """), {"u": u, "d": dano["id_dano_vivienda"]}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Vivienda no encontrada: {uuid_v}")
    # modo offline: cadena de uuids sin GET extra (localidad ↔ dano ↔ vivienda)
    return {**_row_public(row), "uuid_dano_vivienda": str(dano["uuid_registro"]),
            "uuid_edan_localidad": _uuid_localidad(db, dano["id_edan_localidad"])}


def delete_vivienda(db: Session, user: dict, ref_dano: str, uuid_v: str) -> dict:
    dano = _dano_por_ref(db, ref_dano)
    _check_acceso(db, user, dano["id_edan_localidad"], escribir=True)
    u = _parse_uuid(uuid_v, "uuid_vivienda")
    try:
        res = db.execute(text("""
            DELETE FROM edan.edan_localidades_viviendas
            WHERE uuid_registro = :u AND id_dano_vivienda = :d
        """), {"u": u, "d": dano["id_dano_vivienda"]})
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Vivienda no encontrada: {uuid_v}")
        # las fotos de la vivienda se borran logicamente (viajan por pull y el
        # otro dispositivo las elimina; fotografias no tiene FK a viviendas)
        db.execute(text("""
            UPDATE edan.fotografias SET borrado_logico = true, fecha_modificacion = now()
            WHERE tipo_entidad = 'vivienda' AND uuid_registro = :u AND borrado_logico = false
        """), {"u": u})
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    return {"uuid_registro": str(u), "borrado": True,
            # modo offline: cadena de uuids sin GET extra
            "uuid_dano_vivienda": str(dano["uuid_registro"]),
            "uuid_edan_localidad": _uuid_localidad(db, dano["id_edan_localidad"]),
            "nota": "El padre recalcula dano_total/dano_parcial (trigger); "
                    "sus fotos quedaron borrado_logico=true (viajan por pull)"}


# ===========================================================================
# Fotografías
# ===========================================================================
def _dueño_foto(db: Session, tipo_entidad: str, uuid_registro: UUID) -> dict:
    """Devuelve la fila dueña con id_edan_localidad, id_municipio, tabla, pk y uuid."""
    if tipo_entidad in TIPOS_SECCION:
        tabla, _e, pk = TIPOS_SECCION[tipo_entidad]
        row = db.execute(text(f"""
            SELECT s.id_edan_localidad, s.uuid_registro, l.id_municipio,
                   '{tabla}' AS tabla, '{pk}' AS pk_col
            FROM edan.{tabla} s
            JOIN edan.edan_localidades l ON l.id_edan_localidad = s.id_edan_localidad
            WHERE s.uuid_registro = :u
        """), {"u": uuid_registro}).mappings().first()
    elif tipo_entidad in TABLA_FOTO_EXTRA:
        tabla = TABLA_FOTO_EXTRA[tipo_entidad]
        # edan_localidades_viviendas no tiene id_edan_localidad: se resuelve por el padre
        row = db.execute(text(f"""
            SELECT d.id_edan_localidad, v.uuid_registro, l.id_municipio,
                   '{tabla}' AS tabla, 'id_vivienda' AS pk_col
            FROM edan.{tabla} v
            JOIN edan.edan_localidades_danos_vivienda d ON d.id_dano_vivienda = v.id_dano_vivienda
            JOIN edan.edan_localidades l ON l.id_edan_localidad = d.id_edan_localidad
            WHERE v.uuid_registro = :u
        """), {"u": uuid_registro}).mappings().first()
    else:
        raise HTTPException(status_code=400, detail=f"tipo_entidad inválido: {tipo_entidad}")
    if not row:
        raise HTTPException(status_code=404, detail=(
            f"La fila dueña ({tipo_entidad}={uuid_registro}) no existe: sincronice primero su fila"))
    return dict(row)


def upsert_foto(db: Session, user: dict, uuid_fotografia: str, tipo_entidad: str,
                uuid_registro: str, ruta: str, sha256: str | None,
                mime_type: str | None, tamano: int | None) -> dict:
    """Sube/actualiza la foto de una fila. **1 foto activa por fila**
    (tipo_entidad + uuid_registro): un re-upload REEMPLAZA la activa anterior
    (queda borrado_logico=true y viaja por pull). Sin versiones de foto."""
    u_foto = _parse_uuid(uuid_fotografia, "uuid_fotografia")
    u_reg = _parse_uuid(uuid_registro, "uuid_registro")
    tipo_entidad = _norm_tipo(tipo_entidad)
    dueño = _dueño_foto(db, tipo_entidad, u_reg)
    _check_acceso(db, user, dueño["id_edan_localidad"], escribir=True)
    try:
        # 1:1 — marcar la foto activa anterior (distinta uuid_fotografia) como
        # borrada; el índice parcial uq_fotografias_activa garantiza ≤1 activa
        db.execute(text("""
            UPDATE edan.fotografias SET borrado_logico = true, fecha_modificacion = now()
            WHERE tipo_entidad = :te AND uuid_registro = :ur
              AND uuid_fotografia <> :uf AND borrado_logico = false
        """), {"te": tipo_entidad, "ur": u_reg, "uf": u_foto})
        db.execute(text("""
            INSERT INTO edan.fotografias
                (uuid_fotografia, id_edan_localidad, tipo_entidad, uuid_registro,
                 ruta_archivo, sha256, mime_type, tamano_bytes, fecha_modificacion)
            VALUES (:uf, :id, :te, :ur, :ruta, :sha, :mime, :tam, now())
            ON CONFLICT (uuid_fotografia) DO UPDATE SET
                ruta_archivo = EXCLUDED.ruta_archivo,
                sha256 = EXCLUDED.sha256,
                mime_type = EXCLUDED.mime_type,
                tamano_bytes = EXCLUDED.tamano_bytes,
                borrado_logico = false,
                fecha_modificacion = now()
        """), {"uf": u_foto, "id": dueño["id_edan_localidad"], "te": tipo_entidad,
               "ur": u_reg, "ruta": ruta, "sha": sha256, "mime": mime_type, "tam": tamano})
        # espejo del path en la columna fotografia de la fila dueña (patrón legacy)
        if "fotografia" in _cols(db, dueño["tabla"]):
            db.execute(text(f"""
                UPDATE edan.{dueño['tabla']} SET fotografia = :ruta
                WHERE {dueño['pk_col']} = (
                    SELECT {dueño['pk_col']} FROM edan.{dueño['tabla']}
                    WHERE uuid_registro = :u
                )
            """), {"ruta": ruta, "u": u_reg})
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise db_error(e)
    foto = get_foto(db, user, str(u_foto))
    # fila dueña completa: la app actualiza su copia local sin GET extra
    frow = db.execute(text(f"SELECT * FROM edan.{dueño['tabla']} WHERE uuid_registro = :u"),
                      {"u": u_reg}).mappings().first()
    fila = None
    if frow:
        fila = _resolver_ids(db, _row_public(frow))
        fila["uuid_edan_localidad"] = foto["uuid_edan_localidad"]
    return {**foto, "fila_dueña": fila}


def get_foto(db: Session, user: dict, uuid_foto: str) -> dict:
    u = _parse_uuid(uuid_foto, "uuid_fotografia")
    row = db.execute(text("SELECT * FROM edan.fotografias WHERE uuid_fotografia = :u"),
                     {"u": u}).mappings().first()
    if not row or row["borrado_logico"]:
        raise HTTPException(status_code=404, detail=f"Foto no encontrada: {uuid_foto}")
    # fotos = evidencia informativa: solo se exige token (router); sin scope de
    # municipio/dueño (ver listar_fotografias / PLAN §22.3).
    # modo offline: cadena de uuids sin GET extra (localidad ↔ fila dueña)
    return {**_row_public(row),
            "uuid_edan_localidad": _uuid_localidad(db, row["id_edan_localidad"]),
            "url_descarga": f"/api/v2/edan/fotografias/{str(row['uuid_fotografia'])}/descargar"}


def listar_fotografias(db: Session, user: dict,
                       skip: int = 0, limit: int = 50, todos: bool = False,
                       id_edan_localidad: str | None = None,
                       id_municipio: int | None = None,
                       id_usuario: int | None = None,
                       tipo_entidad: str | None = None,
                       fecha_creacion_desde=None, fecha_creacion_hasta=None,
                       fecha_modificacion_desde=None, fecha_modificacion_hasta=None):
    """Listado paginado de fotos activas (`borrado_logico = false`).

    Las fotos son **evidencia informativa**: NO tienen alcance geográfico ni por
    dueño — cualquier usuario autenticado lista **todas**. El token se exige en
    el router (`module_permiso("EDAN")`).

    Filtros (todos opcionales, combinables con AND):
      - id_edan_localidad: id numérico o uuid_edan_localidad.
      - id_municipio: municipio de la localidad dueña (JOIN edan_localidades).
      - id_usuario: usuario dueño de la localidad (id numérico).
      - tipo_entidad: `varchar` (p.ej. `danos_vivienda`).
      - fecha_creacion_desde/hasta y fecha_modificacion_desde/hasta.
    Orden: fecha_creacion DESC NULLS LAST, id_fotografia DESC (`total` real).
    """
    conds = ["f.borrado_logico = false"]
    params: dict[str, Any] = {}
    joins = "LEFT JOIN edan.edan_localidades l ON l.id_edan_localidad = f.id_edan_localidad"
    if id_edan_localidad is not None:
        if str(id_edan_localidad).isdigit():
            conds.append("f.id_edan_localidad = :id_loc"); params["id_loc"] = int(id_edan_localidad)
        else:
            u = _parse_uuid(id_edan_localidad, "id_edan_localidad")
            conds.append("l.uuid_edan_localidad = :uuid_loc"); params["uuid_loc"] = u
    if id_municipio is not None:
        conds.append("l.id_municipio = :id_mun"); params["id_mun"] = id_municipio
    if id_usuario is not None:
        conds.append("l.id_usuario = :id_usuario"); params["id_usuario"] = id_usuario
    if tipo_entidad is not None:
        conds.append("f.tipo_entidad = :tipo_entidad"); params["tipo_entidad"] = tipo_entidad
    for col, val, op in (
        ("fecha_creacion", fecha_creacion_desde, ">="),
        ("fecha_creacion", fecha_creacion_hasta, "<="),
        ("fecha_modificacion", fecha_modificacion_desde, ">="),
        ("fecha_modificacion", fecha_modificacion_hasta, "<="),
    ):
        if val is not None:
            if op == "<=":
                key = f"{col}_hasta"
                conds.append(f"f.{col} < CAST(:{key} AS date) + interval '1 day'")
            else:
                key = f"{col}_desde"
                conds.append(f"f.{col} >= :{key}")
            params[key] = val
    where = " AND ".join(conds)
    total = db.execute(text(f"SELECT count(*) FROM edan.fotografias f {joins} WHERE {where}"),
                       params).scalar()
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    qp = dict(params) if todos else {**params, "limit": limit, "skip": skip}
    rows = db.execute(text(f"""
        SELECT f.uuid_fotografia, f.tipo_entidad, f.uuid_registro,
               f.id_edan_localidad, f.ruta_archivo, f.sha256, f.mime_type,
               f.tamano_bytes, f.fecha_creacion, f.fecha_modificacion,
               l.uuid_edan_localidad
        FROM edan.fotografias f {joins}
        WHERE {where}
        ORDER BY f.fecha_creacion DESC NULLS LAST, f.id_fotografia DESC {page}
    """), qp).mappings().all()
    items = []
    for r in rows:
        d = _row_public(r)
        d["url_descarga"] = f"/api/v2/edan/fotografias/{d['uuid_fotografia']}/descargar"
        items.append(d)
    return items, total


def resolver_foto_descarga(db: Session, user: dict, uuid_foto: str) -> dict:
    """Devuelve (ruta_archivo, mime_type, nombre) de una foto activa para que el
    router sirva el binario. 404 si no existe o está borrada.

    Las fotos son evidencia informativa: **no** aplican scope de municipio/dueño;
    el token ya se exige en el router (`module_permiso("EDAN")`)."""
    u = _parse_uuid(uuid_foto, "uuid_fotografia")
    row = db.execute(text("""
        SELECT ruta_archivo, mime_type, sha256, id_edan_localidad
        FROM edan.fotografias WHERE uuid_fotografia = :u AND borrado_logico = false
    """), {"u": u}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Foto no encontrada: {uuid_foto}")
    if not row["ruta_archivo"]:
        raise HTTPException(status_code=404, detail="La foto no tiene archivo asociado")
    ruta = str(row["ruta_archivo"])
    nombre = ruta.rstrip("/").rsplit("/", 1)[-1] or f"{u}"
    return {"ruta_archivo": ruta, "mime_type": row["mime_type"] or "application/octet-stream",
            "nombre": nombre}


def delete_foto(db: Session, user: dict, uuid_foto: str) -> dict:
    u = _parse_uuid(uuid_foto, "uuid_fotografia")
    exist = db.execute(text("SELECT id_edan_localidad FROM edan.fotografias WHERE uuid_fotografia = :u"),
                       {"u": u}).mappings().first()
    if not exist:
        raise HTTPException(status_code=404, detail=f"Foto no encontrada: {uuid_foto}")
    _check_acceso(db, user, exist["id_edan_localidad"], escribir=True)
    db.execute(text("""
        UPDATE edan.fotografias SET borrado_logico = true, fecha_modificacion = now()
        WHERE uuid_fotografia = :u AND borrado_logico = false
    """), {"u": u})
    db.commit()
    return {"uuid_fotografia": str(u), "borrado_logico": True,
            "uuid_edan_localidad": _uuid_localidad(db, exist["id_edan_localidad"]),
            "nota": "Borrado lógico: se propaga por pull (borrado_logico=true)"}


# ===========================================================================
# Sync: pull / push / ack
# ===========================================================================
def sync_pull(db: Session, user: dict, desde: datetime | None, limit: int) -> dict:
    """Pull con el MISMO alcance de lectura que la API vieja:
    6/7 propias; 8 municipio; 5/9 departamento; 1-4 nacional.
    El feed de sync sigue trayendo SOLO lo propio para roles 6/7 (no se abre a
    todo el municipio: eso aplica a mapa/listas/GET, no a la descarga por
    dispositivo)."""
    watermark = datetime.now()
    d = desde or datetime.min
    sc = service_viejo.scope_mis_localidades_v2(user, solo_propio=True)
    w, params = _scope_where(sc)
    params = {**params, "d": d, "l": limit}
    loc_subq = f"(SELECT id_edan_localidad FROM edan.edan_localidades WHERE {w})"

    formularios = db.execute(text(f"""
        SELECT * FROM edan.edan_localidades WHERE fecha_modificacion > :d AND {w}
        ORDER BY fecha_modificacion ASC LIMIT :l
    """), params).mappings().all()

    # forma alineada con los GET de la familia: FK anidadas RECURSIVAS en la
    # cabecera (§20.16) + grup_* = OR(imp)
    cache: dict = {}
    form_pub = []
    for r in formularios:
        it = _sincronizar_grupos_fila(_resolver_ids(db, _row_public(r), cache))
        form_pub.append(it)

    secciones: list[dict] = []
    for tipo, (tabla, _e, _pk) in TIPOS_SECCION.items():
        rows = db.execute(text(f"""
            SELECT * FROM edan.{tabla} WHERE fecha_modificacion > :d
              AND id_edan_localidad IN {loc_subq}
            ORDER BY fecha_modificacion ASC LIMIT :l
        """), params).mappings().all()
        for r in rows:
            drow = _resolver_ids(db, _row_public(r), cache)
            drow["tipo_seccion"] = tipo
            secciones.append(drow)

    viviendas = db.execute(text(f"""
        SELECT * FROM edan.edan_localidades_viviendas WHERE fecha_modificacion > :d
          AND id_dano_vivienda IN (SELECT id_dano_vivienda FROM edan.edan_localidades_danos_vivienda
                                   WHERE id_edan_localidad IN {loc_subq})
        ORDER BY fecha_modificacion ASC LIMIT :l
    """), params).mappings().all()

    fotos = db.execute(text(f"""
        SELECT * FROM edan.fotografias WHERE fecha_modificacion > :d
          AND id_edan_localidad IN {loc_subq}
        ORDER BY fecha_modificacion ASC LIMIT :l
    """), params).mappings().all()

    if params.get("su") or params.get("sd") or params.get("sm"):
        # con scope: las localidades borradas ya no tienen geo para filtrar,
        # asi que sus tombstones viajan sin filtro (el uuid no es sensible: solo
        # indica "borren esa fila"); los de otras tablas (secciones/viviendas)
        # llegaran con v2.55.0 cuando exista el dato geo en el tombstone.
        tomb_sql = """
            SELECT rb.* FROM edan.registro_borrado rb
            WHERE rb.borrado_en > :d
              AND rb.tabla = 'edan_localidades'
            ORDER BY rb.borrado_en ASC LIMIT :l
        """
    else:
        tomb_sql = """
            SELECT * FROM edan.registro_borrado WHERE borrado_en > :d
            ORDER BY borrado_en ASC LIMIT :l
        """
    tombstones = db.execute(text(tomb_sql), params).mappings().all()

    # modo offline: cadena de uuids sin GET extra (localidad ↔ dano ↔ vivienda ↔ foto)
    loc_uuid_cache: dict[int, str | None] = {}
    # viviendas NO tiene id_edan_localidad: se resuelve por el padre dano
    _ids_dano = list({r["id_dano_vivienda"] for r in viviendas})
    dano_info: dict[int, tuple[str | None, int | None]] = {}
    if _ids_dano:
        for row in db.execute(text(
                "SELECT id_dano_vivienda, uuid_registro, id_edan_localidad "
                "FROM edan.edan_localidades_danos_vivienda WHERE id_dano_vivienda = ANY(:ids)"),
                {"ids": _ids_dano}).mappings():
            dano_info[row["id_dano_vivienda"]] = (str(row["uuid_registro"]),
                                                   row["id_edan_localidad"])
    _ids_loc_v = [loc for _uu, loc in dano_info.values()] + \
                 [r["id_edan_localidad"] for r in fotos]
    _ids_loc_v = [i for i in set(_ids_loc_v) if i is not None]
    if _ids_loc_v:
        for row in db.execute(text(
                "SELECT id_edan_localidad, uuid_edan_localidad FROM edan.edan_localidades "
                "WHERE id_edan_localidad = ANY(:ids)"), {"ids": _ids_loc_v}).mappings():
            loc_uuid_cache[row["id_edan_localidad"]] = str(row["uuid_edan_localidad"])
    viv_pub = []
    for r in viviendas:
        v = _row_public(r)
        uu_d, id_l = dano_info.get(r["id_dano_vivienda"], (None, None))
        v["uuid_dano_vivienda"] = uu_d
        v["uuid_edan_localidad"] = loc_uuid_cache.get(id_l)
        viv_pub.append(v)
    foto_pub = []
    for r in fotos:
        f = _row_public(r)
        f["uuid_edan_localidad"] = loc_uuid_cache.get(r.get("id_edan_localidad"))
        foto_pub.append(f)

    return {
        "watermark": watermark.isoformat(),
        "formularios": form_pub,
        "secciones": secciones,
        "viviendas": viv_pub,
        "fotos": foto_pub,
        "tombstones": [_row_public(r) for r in tombstones],
        "totals": {
            "formularios": len(form_pub), "secciones": len(secciones),
            "viviendas": len(viv_pub), "fotos": len(foto_pub),
            "tombstones": len(tombstones),
        },
    }


def sync_push(db: Session, user: dict, items: list[dict]) -> dict:
    """Push por lote: aplica los mismos upsert/borrado que los endpoints
    directos pero SOLO con recálculo de grup_* (sin regla de enviados 2/3/4/5,
    documentado): el lote offline puede llevar parcialidad transitoria."""
    resultados = []
    for i, item in enumerate(items):
        accion = item.get("accion", "upsert")
        tipo = item.get("tipo")
        datos = item.get("datos") or {}
        estado, message = "aplicado", ""
        try:
            if accion == "borrar":
                if tipo == "formulario":
                    delete_formulario(db, user, str(datos.get("uuid_edan_localidad")))
                elif tipo == "vivienda":
                    delete_vivienda(db, user, str(datos.get("uuid_dano_vivienda")),
                                    str(datos.get("uuid_registro")))
                elif tipo == "seccion":
                    delete_seccion(db, user, str(datos.get("uuid_edan_localidad")),
                                   item.get("tipo_seccion") or "", str(datos.get("uuid_registro")),
                                   validar=False)
                else:
                    raise HTTPException(status_code=400,
                                        detail="borrar solo soporta tipo formulario|seccion|vivienda")
            elif tipo == "formulario":
                upsert_formulario(db, user, datos, validar=False)
            elif tipo == "seccion":
                loc_ref = str(datos.pop("uuid_edan_localidad", "") or "")
                upsert_seccion(db, user, loc_ref,
                               item.get("tipo_seccion") or "", datos)
            elif tipo == "vivienda":
                upsert_vivienda(db, user, str(datos.get("uuid_dano_vivienda")), datos)
            else:
                raise HTTPException(status_code=400, detail=f"tipo inválido: {tipo}")
        except HTTPException as e:
            db.rollback()
            estado = "conflicto" if e.status_code == 409 else "error"
            message = str(e.detail if not isinstance(e.detail, dict) else e.detail.get("message", e.detail))
            resultados.append({"indice": i, "estado": estado, "tipo": tipo,
                               "message": message})
            continue
        except Exception as e:  # noqa: BLE001
            db.rollback()
            estado, message = "error", f"{type(e).__name__}: {e}"
        resultados.append({"indice": i, "estado": estado, "tipo": tipo,
                           "message": message or "OK"})
    return {
        "resultados": resultados,
        "aplicados": sum(1 for r in resultados if r["estado"] == "aplicado"),
        "conflictos": sum(1 for r in resultados if r["estado"] == "conflicto"),
        "errores": sum(1 for r in resultados if r["estado"] == "error"),
    }


def sync_ack(db: Session, user: dict, id_dispositivo: UUID, watermark: datetime | None) -> dict:
    db.execute(text("""
        INSERT INTO edan.dispositivo_sync
            (id_dispositivo, id_usuario, watermark_aplicado, ack_en, fecha_registro)
        VALUES (:d, :u, :w, now(), now())
        ON CONFLICT (id_dispositivo) DO UPDATE SET
            id_usuario = EXCLUDED.id_usuario,
            watermark_aplicado = EXCLUDED.watermark_aplicado,
            ack_en = now()
    """), {"d": id_dispositivo, "u": user.get("id_usuario"), "w": watermark})
    db.commit()
    return {"id_dispositivo": str(id_dispositivo),
            "watermark_aplicado": watermark.isoformat() if watermark else None,
            "ack_en": datetime.now().isoformat()}


# re-export para el router (scope geográfico del dominio existente)
validar_scope_localidad = service_viejo.validar_scope_localidad
