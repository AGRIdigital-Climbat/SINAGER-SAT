"""Mapa autoritativo secciones <-> grupos EDAN (fuente única de verdad).

Compartido por la API legacy (`service.py`) y la API nueva
(`service_v2_nuevas.py`) para derivar el nodo `grupos` (9 `grup_*`) de forma
consistente en TODOS los GET que devuelvan una localidad o un EDAN padre.

Módulo NEUTRO: no importa `service` (evita ciclos service <-> service_v2_nuevas).

Nomenclatura:
- sección canónica: nombre corto interno (p.ej. `salud_establecimientos`).
- flag de sección  : columna `imp_*` de `edan_localidades` (14 columnas).
- grupo            : nodo `grup_*` de la API (9); su valor = OR de las secciones
                     miembro (flag true O con filas).
"""

# sección canónica -> clave legacy del documento (la que devuelve el GET legacy)
SECCION_LEGACY = {
    "impacto_poblacion":        "impacto_poblacion",
    "primera_respuesta":        "necesidad_primera_respuesta",
    "salud_establecimientos":   "establecimientos_salud",
    "salud_necesidades":        "necesidad_salud",
    "danos_viales":             "danos_viales",
    "danos_infra_publica":      "danos_infra_publica",
    "servicios_basicos":        "servicios_basicos",
    "unidades_educativas":      "unidades_educativas",
    "danos_vivienda":           "danos_vivienda",
    "danos_agricultura":        "danos_agricultura",
    "danos_pecuario":           "danos_pecuarios",
    "infra_productiva":         "infra_productiva",
    "proteccion":               "proteccion",
    "necesidades_humanitarias": "necesidad_humanitaria",
}

# flag imp_* de sección (columna real en edan_localidades) -> sección canónica
SECCION_FLAG = {
    "imp_impacto_poblacion":       "impacto_poblacion",
    "imp_primera_respuesta":       "primera_respuesta",
    "imp_salud_establecimientos":  "salud_establecimientos",
    "imp_necesidad_salud":         "salud_necesidades",
    "imp_danos_viales":            "danos_viales",
    "imp_danos_infra_publica":     "danos_infra_publica",
    "imp_servicios_basicos":       "servicios_basicos",
    "imp_unidades_educativas":     "unidades_educativas",
    "imp_danos_vivienda":          "danos_vivienda",
    "imp_danos_agricultura":       "danos_agricultura",
    "imp_danos_pecuarios":         "danos_pecuario",
    "imp_infra_productiva":        "infra_productiva",
    "imp_proteccion":              "proteccion",
    "imp_necesidad_humanitaria":   "necesidades_humanitarias",
}
SECCION_FLAG_R = {v: k for k, v in SECCION_FLAG.items()}

# clave grup_* (API/BD) -> columna grup_* de grupo (BD)
GRUPO_FLAG = {
    "grup_poblacion":       "grup_poblacion",
    "grup_salud":           "grup_salud",
    "grup_infraestructura": "grup_infraestructura",
    "grup_servicios":       "grup_servicios",
    "grup_educacion":       "grup_educacion",
    "grup_vivienda":        "grup_vivienda",
    "grup_agropecuario":    "grup_agropecuario",
    "grup_proteccion":      "grup_proteccion",
    "grup_necesidades":     "grup_necesidades",
}

# columna de grupo -> secciones canónicas miembro (mapeo autoritativo del usuario)
GRUPO_SECCIONES = {
    "grup_poblacion":       ["impacto_poblacion", "primera_respuesta"],
    "grup_salud":           ["salud_establecimientos", "salud_necesidades"],
    "grup_infraestructura": ["danos_viales", "danos_infra_publica"],
    "grup_servicios":       ["servicios_basicos"],
    "grup_educacion":       ["unidades_educativas"],
    "grup_vivienda":        ["danos_vivienda"],
    "grup_agropecuario":    ["danos_agricultura", "danos_pecuario", "infra_productiva"],
    "grup_proteccion":      ["proteccion"],
    "grup_necesidades":     ["necesidades_humanitarias"],
}

# nombres legacy de la app móvil (wire imp_* agrupado) -> clave/columna grup_*
GRUPO_WIRE_LEGACY = {
    "imp_poblacion":       "grup_poblacion",
    "imp_salud":           "grup_salud",
    "imp_infraestructura": "grup_infraestructura",
    "imp_servicios":       "grup_servicios",
    "imp_educacion":       "grup_educacion",
    "imp_vivienda":        "grup_vivienda",
    "imp_agropecuario":    "grup_agropecuario",
    "imp_proteccion":      "grup_proteccion",
    "imp_necesidades":     "grup_necesidades",
}
GRUPOS_BD = set(GRUPO_SECCIONES)


def secciones_activas(flags: dict, con_datos_legacy: set[str] | None = None) -> dict[str, bool]:
    """sección canónica -> bool (flag `imp_*` true O tiene filas).

    `flags` es una fila de `edan_localidades` (dict con las columnas imp_*).
    `con_datos_legacy` es el set de claves legacy con al menos una fila
    (el `con_datos` de `_build_localidad`).
    """
    con_datos_legacy = con_datos_legacy or set()
    activa: dict[str, bool] = {}
    for flag_col, canon in SECCION_FLAG.items():
        tiene_datos = SECCION_LEGACY.get(canon) in con_datos_legacy
        activa[canon] = bool((flags or {}).get(flag_col)) or tiene_datos
    return activa


def grupos_de_activos(activa: dict[str, bool]) -> dict[str, bool]:
    """Nodo `grupos` (grup_* -> bool) a partir del dict de secciones activas."""
    return {g: any(activa.get(s, False) for s in GRUPO_SECCIONES[col])
            for g, col in GRUPO_FLAG.items()}


def grupos_de(flags: dict, con_datos_legacy: set[str] | None = None) -> dict[str, bool]:
    """Nodo `grupos` derivado de los flags imp_* (+ secciones con datos)."""
    return grupos_de_activos(secciones_activas(flags, con_datos_legacy))
