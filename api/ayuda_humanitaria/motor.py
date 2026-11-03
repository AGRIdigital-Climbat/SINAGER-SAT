"""Motor de calculo por KITS de ayuda humanitaria.

Las formulas son DATOS (rida.regla_calculo_kit + rida.detalle_parametro_kit,
AYUDA_HUMANITARIA_BACKEND.md §2.6): cada KIT es una regla con un criterio de
aplicacion y una lista de articulos (detalhes) con su cantidad base DIARIA.
Este evaluador corre cada kit contra la poblacion del expediente

    evento_rida -> formulario_rida -> familia -> integrante

y devuelve UNA fila por detalle SIN persistir. El que persiste (sumando las
cantidades por articulo en rida.solicitud_articulo) es
service.ejecutar_motor_calculo().

Cantidad de cada detalle:
    poblacion = num. de filas del pool (familia o integrante) que cumplen
                TODOS los criterios del kit
    cantidad  = clamp(redondeo(base_diaria * dias_duracion * poblacion),
                      cantidad_min, cantidad_max)   (dias_duracion NULL = 1)

v2.58.0: solo corren los kits con estado='publicada' (y activo). Opcionalmente
filtra por id_regla (subset) y por id_familia, y produce el DESGLOSE por
familia: cantidad_familia = base_diaria * dias * poblacion_familia en CRUDO
(sin redondeo ni clamp) — la suma de los crudos = base*dias*poblacion_total,
asi el total agregado se sigue calculando igual que siempre. Tambien puede
evaluar KITS inyectados desde el snapshot JSONB de una version publicada
(regla_calculo_version.configuracion_json) para reproducir calculos historicos.
"""

import math

from sqlalchemy import text
from sqlalchemy.orm import Session

# Campos del kit que viven en el snapshot JSONB de una version publicada.
CAMPOS_KIT_JSON = (
    "nombre_regla", "criterio_aplicacion", "rango_edad_min_dias",
    "rango_edad_max_dias", "requiere_gestante", "requiere_discapacidad",
    "sexo", "dias_duracion", "redondeo", "prioridad", "orden", "estado",
)

SQL_FAMILIAS = """
    SELECT f.id_familia,
           f.id_edan_localidad,
           el.localidad,
           ub.id_cat_tipo_albergue,
           (SELECT COUNT(*) FROM rida.integrante i
             WHERE i.id_familia = f.id_familia) AS total_miembros
    FROM rida.familia f
    LEFT JOIN rida.ubicacion_familia ub ON ub.id_familia = f.id_familia
    LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = f.id_edan_localidad
    JOIN rida.formulario_rida fr ON fr.id_formulario = f.id_formulario
    WHERE fr.id_evento_rida = :id_evento
"""

SQL_INTEGRANTES = """
    SELECT i.id_familia, i.sexo, i.es_jefe, i.id_parentesco, i.gestante_semanas,
           i.lactante_meses, i.id_discapacidad, i.id_enfermedad,
           f.id_edan_localidad, el.localidad,
           COALESCE((CURRENT_DATE - i.fecha_nacimiento)::int, NULL) AS edad_dias,
           CASE WHEN i.sexo = 'F' AND i.gestante_semanas IS NOT NULL
                     AND i.gestante_semanas > 0 THEN TRUE ELSE FALSE END AS es_gestante,
           CASE WHEN i.id_discapacidad IS NOT NULL THEN TRUE ELSE FALSE END AS es_discapacitado
    FROM rida.integrante i
    JOIN rida.familia f ON f.id_familia = i.id_familia
    LEFT JOIN edan.edan_localidades el ON el.id_edan_localidad = f.id_edan_localidad
    JOIN rida.formulario_rida fr ON fr.id_formulario = f.id_formulario
    WHERE fr.id_evento_rida = :id_evento
"""

SQL_POOL_POR_CRITERIO = {
    "POR_FAMILIA": SQL_FAMILIAS,
    "POR_INTEGRANTE": SQL_INTEGRANTES,
    "POR_CONDICION_ESPECIAL": SQL_INTEGRANTES,
}


def validar_criterio(kit: dict) -> list[str]:
    """Valida la consistencia de una regla kit (criterio + rangos + sexo)."""
    errores = []
    c = kit.get("criterio_aplicacion")
    if c == "POR_FAMILIA" and any((kit.get("rango_edad_min_dias") is not None,
                                   kit.get("rango_edad_max_dias") is not None,
                                   kit.get("sexo") is not None,
                                   kit.get("requiere_gestante"),
                                   kit.get("requiere_discapacidad"))):
        errores.append(
            "criterio_aplicacion POR_FAMILIA no admite rango_edad_dias, sexo, "
            "requiere_gestante ni requiere_discapacidad (aplica a toda la familia)")
    if (kit.get("rango_edad_min_dias") is not None and kit.get("rango_edad_max_dias") is not None
            and kit["rango_edad_min_dias"] > kit["rango_edad_max_dias"]):
        errores.append("rango_edad_min_dias no puede ser mayor que rango_edad_max_dias")
    if c == "POR_CONDICION_ESPECIAL" and not any((kit.get("rango_edad_min_dias") is not None,
                                                  kit.get("rango_edad_max_dias") is not None,
                                                  kit.get("sexo") is not None,
                                                  kit.get("requiere_gestante"),
                                                  kit.get("requiere_discapacidad"))):
        errores.append("criterio_aplicacion POR_CONDICION_ESPECIAL exige al menos un "
                       "filtro activo (rango_edad_dias, sexo, requiere_gestante o "
                       "requiere_discapacidad)")
    return errores


def _cargar_kits(db: Session, *, solo_publicadas: bool = True,
                 ids_reglas: list[int] | None = None) -> list[dict]:
    """Kits vigentes (activo + publicadas por defecto), con sus detalles."""
    filtros = ""
    params: dict = {}
    if solo_publicadas:
        filtros += " AND k.estado = 'publicada'"
    if ids_reglas:
        filtros += " AND k.id_regla = ANY(:ids_reglas)"
        params["ids_reglas"] = list(ids_reglas)
    return [dict(r._mapping) for r in db.execute(text(f"""
        SELECT k.id_regla, k.nombre_regla, k.criterio_aplicacion,
               k.rango_edad_min_dias, k.rango_edad_max_dias, k.requiere_gestante,
               k.requiere_discapacidad, k.sexo, k.dias_duracion, k.redondeo,
               k.prioridad, k.orden, k.estado,
               d.id_detalle_regla, d.id_articulo, d.cantidad_base_diaria,
               d.cantidad_min, d.cantidad_max,
               a.nombre AS articulo, a.unidad_de_medida
        FROM rida.regla_calculo_kit k
        JOIN rida.detalle_parametro_kit d ON d.id_regla = k.id_regla
        JOIN rida.cat_articulo a ON a.id_articulo = d.id_articulo
        WHERE k.activo{filtros}
        ORDER BY k.orden, k.prioridad, k.id_regla, d.id_detalle_regla
    """), params).fetchall()]


def _kits_desde_snapshot(db: Session, id_regla: int, config: dict) -> list[dict]:
    """Reconstruye los kits de una version publicada desde su snapshot JSONB.

    El snapshot (regla_calculo_version.configuracion_json) trae las columnas del
    kit + la lista `detalles`; aqui se enriquecen con nombre/unidad de
    cat_articulo para que el evaluador reciba la MISMA forma que la BD.
    """
    ids_art = [d["id_articulo"] for d in config.get("detalles", [])]
    catalogo = {}
    if ids_art:
        for r in db.execute(text("""
            SELECT id_articulo, nombre, unidad_de_medida
            FROM rida.cat_articulo WHERE id_articulo = ANY(:ids)
        """), {"ids": ids_art}).fetchall():
            catalogo[r.id_articulo] = (r.nombre, r.unidad_de_medida)
    kits = []
    for d in config.get("detalles", []):
        nombre, unidad = catalogo.get(d["id_articulo"], (None, None))
        kit = {"id_regla": id_regla, "id_detalle_regla": None, "id_articulo": d["id_articulo"],
               "articulo": nombre, "unidad": unidad,
               "cantidad_base_diaria": d["cantidad_base_diaria"],
               "cantidad_min": d.get("cantidad_min"), "cantidad_max": d.get("cantidad_max")}
        for campo in CAMPOS_KIT_JSON:
            kit[campo] = config.get(campo)
        kits.append(kit)
    return kits


def _pools(db: Session, id_evento_rida: int,
           id_familias: list[int] | None = None) -> dict[str, list]:
    """Pool de familias/integrantes del evento (cacheado por criterio)."""
    extra = ""
    params: dict = {"id_evento": id_evento_rida}
    if id_familias:
        extra = " AND f.id_familia = ANY(:familias)"
        params["familias"] = list(id_familias)
    sql_fam = SQL_FAMILIAS + extra
    sql_int = SQL_INTEGRANTES + extra.replace("f.id_familia", "i.id_familia")

    pools: dict[str, list] = {}

    def _pool(criterio: str) -> list:
        if criterio not in pools:
            sql = sql_fam if criterio == "POR_FAMILIA" else sql_int
            pools[criterio] = [dict(r._mapping) for r in db.execute(text(sql), params).fetchall()]
        return pools[criterio]

    return _pool


def _cumple_kit(fila: dict, kit: dict) -> bool:
    if kit["rango_edad_min_dias"] is not None:
        if fila.get("edad_dias") is None or fila["edad_dias"] < kit["rango_edad_min_dias"]:
            return False
    if kit["rango_edad_max_dias"] is not None:
        if fila.get("edad_dias") is None or fila["edad_dias"] > kit["rango_edad_max_dias"]:
            return False
    if kit["requiere_gestante"] and not fila.get("es_gestante"):
        return False
    if kit["requiere_discapacidad"] and not fila.get("es_discapacitado"):
        return False
    if kit["sexo"] and fila.get("sexo") != kit["sexo"]:
        return False
    return True


def _redondear(valor: float, modo: str) -> float:
    if modo == "techo":
        return float(math.ceil(valor))
    if modo == "piso":
        return float(math.floor(valor))
    return valor


def ejecutar_kits_completo(db: Session, id_evento_rida: int, *, kits: list[dict] | None = None,
                           solo_publicadas: bool = True, ids_reglas: list[int] | None = None,
                           id_familias: list[int] | None = None,
                           con_desglose: bool = False) -> tuple[list[dict], list[dict]]:
    """Evalua los kits contra el expediente. NO persiste.

    Devuelve (calculados, por_familia):
      - calculados: una fila por DETALLE con el TOTAL del expediente (formula
        historica: redondeo + clamp sobre base*dias*poblacion).
      - por_familia (si con_desglose): una fila por (familia, detalle) con la
        cantidad en CRUDO (base*dias*poblacion_familia, sin redondeo ni clamp);
        la suma de crudos es exactamente base*dias*poblacion_total.
    """
    if kits is None:
        kits = _cargar_kits(db, solo_publicadas=solo_publicadas, ids_reglas=ids_reglas)
    _pool = _pools(db, id_evento_rida, id_familias)

    calculados: list[dict] = []
    por_familia: dict[tuple, dict] = {}
    for kit in kits:
        filas = _pool(kit["criterio_aplicacion"])
        cumplen = [f for f in filas if _cumple_kit(f, kit)]
        pob = len(cumplen)
        dias = kit["dias_duracion"] or 1
        cantidad = float(kit["cantidad_base_diaria"]) * dias * pob
        cantidad = _redondear(cantidad, kit["redondeo"])
        if kit["cantidad_max"] is not None and cantidad > float(kit["cantidad_max"]):
            cantidad = float(kit["cantidad_max"])
        if kit["cantidad_min"] is not None and cantidad < float(kit["cantidad_min"]):
            cantidad = float(kit["cantidad_min"])
        calculados.append({
            "id_regla": kit["id_regla"],
            "nombre_regla": kit["nombre_regla"],
            "criterio_aplicacion": kit["criterio_aplicacion"],
            "prioridad": kit["prioridad"],
            "orden": kit["orden"],
            "id_detalle_regla": kit["id_detalle_regla"],
            "id_articulo": kit["id_articulo"],
            "articulo": kit["articulo"],
            "unidad": kit["unidad_de_medida"] if kit.get("unidad") is None else kit["unidad"],
            "cantidad_base_diaria": float(kit["cantidad_base_diaria"]),
            "dias_duracion": dias,
            "poblacion": pob,
            "cantidad": cantidad,
        })
        if con_desglose:
            por_familia_fila: dict[int, int] = {}
            for f in cumplen:
                por_familia_fila[f["id_familia"]] = por_familia_fila.get(f["id_familia"], 0) + 1
            for id_familia, pob_fam in por_familia_fila.items():
                crudo = round(float(kit["cantidad_base_diaria"]) * dias * pob_fam, 2)
                key = (id_familia, kit["id_regla"], kit["id_articulo"])
                previa = por_familia.get(key)
                por_familia[key] = {
                    "id_familia": id_familia,
                    "id_regla": kit["id_regla"],
                    "id_articulo": kit["id_articulo"],
                    "articulo": kit["articulo"] or previa["articulo"] if previa else kit["articulo"],
                    "unidad": kit["unidad_de_medida"] if kit.get("unidad") is None else kit["unidad"],
                    "cantidad": (previa["cantidad"] + crudo) if previa else crudo,
                }
    return calculados, list(por_familia.values())


def ejecutar_kits(db: Session, id_evento_rida: int, *, kits: list[dict] | None = None,
                  solo_publicadas: bool = True, ids_reglas: list[int] | None = None,
                  id_familias: list[int] | None = None) -> list[dict]:
    """Compatibilidad: solo la rama de totales (como siempre)."""
    calculados, _ = ejecutar_kits_completo(
        db, id_evento_rida, kits=kits, solo_publicadas=solo_publicadas,
        ids_reglas=ids_reglas, id_familias=id_familias)
    return calculados


def agrupar_calculados(calculados: list[dict]) -> list[dict]:
    """Suma por articulo las cantidades de todos los kits (regla: si un mismo
    articulo aparece en 2 kits, las cantidades SE SUMAN).

    id_regla guia = el del kit con mayor prioridad (menor valor de prioridad,
    luego menor orden, luego menor id_regla).
    """
    por_articulo: dict[int, dict] = {}
    for c in calculados:
        key = c["id_articulo"]
        if key not in por_articulo:
            por_articulo[key] = {
                "id_articulo": key,
                "articulo": c["articulo"],
                "unidad": c["unidad"],
                "cantidad": 0.0,
                "id_regla": c["id_regla"],
                "_pri": c["prioridad"],
                "_ord": c["orden"],
                "detalles": 0,
            }
        ag = por_articulo[key]
        ag["cantidad"] += c["cantidad"]
        ag["detalles"] += 1
        if (c["prioridad"], c["orden"], c["id_regla"]) < \
                (ag["_pri"], ag["_ord"], ag["id_regla"]):
            ag["_pri"] = c["prioridad"]
            ag["_ord"] = c["orden"]
            ag["id_regla"] = c["id_regla"]
    for f in por_articulo.values():
        f.pop("_pri", None)
        f.pop("_ord", None)
    return list(por_articulo.values())
