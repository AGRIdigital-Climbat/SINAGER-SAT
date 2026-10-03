"""Módulo helper para filtros geográficos con validación jerárquica."""

from fastapi import HTTPException


def validar_geografia_jerarquica(id_departamento: int | None = None,
                                  id_provincia: int | None = None,
                                  id_municipio: int | None = None) -> dict:
    """Valida consistencia jerárquica de filtros geográficos.
    
    Jerarquía: departamento (7) → provincia (701) → municipio (70101)
    
    Retorna dict con filtros válidos para usar en queries.
    """
    if not any([id_departamento, id_provincia, id_municipio]):
        return {}
    
    filtros = {}
    
    # Validar jerarquía: municipio implica provincia y departamento
    if id_municipio is not None:
        municipio_str = str(id_municipio)
        if len(municipio_str) == 6:
            # Extraer departamento y provincia del código de municipio
            depto_from_mun = int(municipio_str[:1])
            prov_from_mun = int(municipio_str[:3])
            
            if id_departamento is not None and id_departamento != depto_from_mun:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inconsistencia geográfica: municipio {id_municipio} pertenece a "
                           f"departamento {depto_from_mun}, no {id_departamento}"
                )
            if id_provincia is not None and id_provincia != prov_from_mun:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inconsistencia geográfica: municipio {id_municipio} pertenece a "
                           f"provincia {prov_from_mun}, no {id_provincia}"
                )
            
            # Usar departamento y provincia derivados del municipio
            filtros["id_departamento"] = depto_from_mun
            filtros["id_provincia"] = prov_from_mun
            filtros["id_municipio"] = id_municipio
        else:
            filtros["id_municipio"] = id_municipio
            if id_departamento:
                filtros["id_departamento"] = id_departamento
            if id_provincia:
                filtros["id_provincia"] = id_provincia
    
    # Validar jerarquía: provincia implica departamento
    elif id_provincia is not None:
        provincia_str = str(id_provincia)
        if len(provincia_str) == 3:
            depto_from_prov = int(provincia_str[:1])
            
            if id_departamento is not None and id_departamento != depto_from_prov:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inconsistencia geográfica: provincia {id_provincia} pertenece a "
                           f"departamento {depto_from_prov}, no {id_departamento}"
                )
            
            filtros["id_departamento"] = depto_from_prov
            filtros["id_provincia"] = id_provincia
        else:
            filtros["id_provincia"] = id_provincia
            if id_departamento:
                filtros["id_departamento"] = id_departamento
    
    # Solo departamento
    elif id_departamento is not None:
        filtros["id_departamento"] = id_departamento
    
    return filtros


def agregar_filtros_geo(conds: list, params: dict, alias_tabla: str = "el",
                        filtros: dict | None = None) -> tuple[list, dict]:
    """Agrega condiciones WHERE para filtros geográficos.
    
    Args:
        conds: Lista de condiciones WHERE existentes
        params: Diccionario de parámetros existente
        alias_tabla: Alias de la tabla de localidades (default: "el")
        filtros: Diccionario con id_departamento, id_provincia, id_municipio
    
    Returns:
        Tupla (conds_actualizados, params_actualizados)
    """
    filtros = filtros or {}
    
    if filtros.get("id_municipio"):
        conds.append(f"{alias_tabla}.id_municipio = :id_municipio")
        params["id_municipio"] = filtros["id_municipio"]
    
    if filtros.get("id_provincia"):
        conds.append(f"{alias_tabla}.id_provincia = :id_provincia")
        params["id_provincia"] = filtros["id_provincia"]
    
    if filtros.get("id_departamento"):
        conds.append(f"{alias_tabla}.id_departamento = :id_departamento")
        params["id_departamento"] = filtros["id_departamento"]
    
    return conds, params
