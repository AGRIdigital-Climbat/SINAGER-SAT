"""Motor de calculo de NECESIDADES (RIDA).

A diferencia del motor de articulos (motor.py), que evalua KITS con una lista
de detalles, cada regla de necesidad apunta a UN articulo de UNA categoria
(rida.regla_necesidad) y produce una fila de necesidad por familia:

    poblacion_familia = filas del pool (familia o integrante) de esa familia
                        que cumplen TODAS las condiciones de la regla
    cantidad          = ceil(cantidad_base * dias_duracion * poblacion_familia)

Reglas:
  * POR_FAMILIA: cada familia cuenta 1 (las condiciones deben estar vacias).
  * POR_INTEGRANTE: cuentan los integrantes (con filtros opcionales).
  * POR_CONDICION_ESPECIAL: igual que integrantes, pero exige al menos un
    filtro (gestante, discapacidad, rango de edad o sexo).
  * El redondeo SIEMPRE es hacia arriba; no se aplican cantidad_min/max.
  * Solo corren reglas activas.

Este modulo NO persiste: devuelve las filas calculadas y el resumen. La
persistencia (con reemplazo de manuales por categoria) vive en service.py.
"""

import math
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import motor

CRITERIOS = ("POR_FAMILIA", "POR_INTEGRANTE", "POR_CONDICION_ESPECIAL")
CLAVES_CONDICION = ("gestante", "discapacidad", "edad_min_dias",
                    "edad_max_dias", "sexo")

SQL_REGLAS = """
    SELECT r.id_regla_necesidad, r.nombre, r.criterio_aplicacion,
           r.id_categoria_ayuda, c.nombre AS categoria,
           r.id_articulo, a.nombre AS articulo, a.unidad_de_medida AS unidad,
           r.cantidad_base, r.dias_duracion, r.condiciones,
           r.prioridad, r.orden
    FROM rida.regla_necesidad r
    JOIN rida.cat_articulo a ON a.id_articulo = r.id_articulo
    JOIN rida.cat_categoria_ayuda c
      ON c.id_categoria_ayuda = r.id_categoria_ayuda
    WHERE r.activo
    ORDER BY r.orden, r.prioridad, r.id_regla_necesidad
"""


def cargar_reglas(db: Session, ids: list[int] | None = None) -> list[dict]:
    """Reglas activas (opcionalmente un subconjunto por id)."""
    sql, params = SQL_REGLAS, {}
    if ids:
        sql = SQL_REGLAS.replace("WHERE r.activo", "WHERE r.activo AND r.id_regla_necesidad = ANY(:ids)")
        params["ids"] = list(ids)
    return [dict(r._mapping) for r in db.execute(text(sql), params).fetchall()]


def validar_condiciones(criterio: str, condiciones: dict | None) -> list[str]:
    """Valida el JSONB de condiciones de una regla de necesidad."""
    errores: list[str] = []
    cond = condiciones or {}
    if not isinstance(cond, dict):
        return ["condiciones debe ser un objeto JSON"]
    desconocidas = set(cond) - set(CLAVES_CONDICION)
    if desconocidas:
        errores.append(f"condiciones tiene claves no permitidas: {sorted(desconocidas)}")

    if criterio == "POR_FAMILIA":
        activas = [k for k in CLAVES_CONDICION if cond.get(k) not in (None, False)]
        if activas:
            errores.append(
                "criterio_aplicacion POR_FAMILIA no admite condiciones "
                f"({', '.join(activas)}); aplica a toda la familia")
        return errores

    emin, emax = cond.get("edad_min_dias"), cond.get("edad_max_dias")
    for clave, valor in (("edad_min_dias", emin), ("edad_max_dias", emax)):
        if valor is not None and (not isinstance(valor, int) or valor < 0):
            errores.append(f"{clave} debe ser un entero >= 0")
    if isinstance(emin, int) and isinstance(emax, int) and emin > emax:
        errores.append("edad_min_dias no puede ser mayor que edad_max_dias")
    sexo = cond.get("sexo")
    if sexo is not None and sexo not in ("M", "F"):
        errores.append("sexo debe ser 'M' o 'F'")
    for clave in ("gestante", "discapacidad"):
        valor = cond.get(clave)
        if valor is not None and not isinstance(valor, bool):
            errores.append(f"{clave} debe ser booleano")

    if criterio == "POR_CONDICION_ESPECIAL":
        hay_filtro = any(cond.get(k) not in (None, False)
                         for k in CLAVES_CONDICION)
        if not hay_filtro:
            errores.append(
                "criterio_aplicacion POR_CONDICION_ESPECIAL exige al menos una "
                "condicion activa (gestante, discapacidad, edad_min_dias, "
                "edad_max_dias o sexo)")
    return errores


def _cumple(fila: dict, cond: dict) -> bool:
    if cond.get("gestante") and not fila.get("es_gestante"):
        return False
    if cond.get("discapacidad") and not fila.get("es_discapacitado"):
        return False
    if cond.get("edad_min_dias") is not None:
        if fila.get("edad_dias") is None or fila["edad_dias"] < cond["edad_min_dias"]:
            return False
    if cond.get("edad_max_dias") is not None:
        if fila.get("edad_dias") is None or fila["edad_dias"] > cond["edad_max_dias"]:
            return False
    if cond.get("sexo") and fila.get("sexo") != cond["sexo"]:
        return False
    return True


def _ceil(valor: Decimal) -> int:
    return int(math.ceil(float(valor)))


def evaluar(db: Session, id_evento_rida: int, *,
            reglas: list[dict] | None = None,
            id_familias: list[int] | None = None) -> tuple[list[dict], dict]:
    """Evalua las reglas contra el evento. NO persiste.

    Devuelve (necesidades, resumen). `necesidades` viene agregada por
    (id_familia, id_articulo): si dos reglas generan el mismo articulo para
    una familia, las cantidades se SUMAN.
    """
    if reglas is None:
        reglas = cargar_reglas(db)
    pool = motor._pools(db, id_evento_rida, id_familias)

    agregado: dict[tuple[int, int], dict] = {}
    for regla in reglas:
        cond = regla.get("condiciones") or {}
        filas = pool(regla["criterio_aplicacion"])
        por_familia: dict[int, dict] = {}
        for fila in filas:
            if not _cumple(fila, cond):
                continue
            fam = por_familia.setdefault(fila["id_familia"], {
                "id_localidad": fila.get("id_edan_localidad"),
                "localidad": fila.get("localidad"),
                "poblacion": 0,
            })
            fam["poblacion"] += 1

        dias = Decimal(regla["dias_duracion"] or 1)
        base = Decimal(str(regla["cantidad_base"]))
        for id_familia, fam in por_familia.items():
            cantidad = _ceil(base * dias * fam["poblacion"])
            if cantidad <= 0:
                continue
            key = (id_familia, regla["id_articulo"])
            previa = agregado.get(key)
            if previa is None:
                agregado[key] = {
                    "id_familia": id_familia,
                    "id_localidad": fam["id_localidad"],
                    "localidad": fam["localidad"],
                    "id_articulo": regla["id_articulo"],
                    "articulo": regla["articulo"],
                    "categoria": regla["categoria"],
                    "id_categoria_ayuda": regla["id_categoria_ayuda"],
                    "cantidad": cantidad,
                    "unidad": regla["unidad"],
                    "fuente": "motor",
                    "id_regla": regla["id_regla_necesidad"],
                    "_pri": (regla["prioridad"], regla["orden"],
                             regla["id_regla_necesidad"]),
                }
            else:
                previa["cantidad"] += cantidad
                # Trazabilidad: se queda la regla de mayor prioridad.
                if (regla["prioridad"], regla["orden"], regla["id_regla_necesidad"]) \
                        < previa["_pri"]:
                    previa["id_regla"] = regla["id_regla_necesidad"]
                    previa["_pri"] = (regla["prioridad"], regla["orden"],
                                      regla["id_regla_necesidad"])

    necesidades = sorted(agregado.values(),
                         key=lambda x: (x["id_familia"], x["categoria"],
                                        x["articulo"], x["id_articulo"]))
    for fila in necesidades:
        fila.pop("_pri", None)

    resumen = {
        "familias": len({f["id_familia"] for f in necesidades}),
        "articulos_distintos": len({f["id_articulo"] for f in necesidades}),
        "unidades": sum(f["cantidad"] for f in necesidades),
    }
    return necesidades, resumen
