"""APIs PUBLICAS de metricas (sin autenticacion y sin filtros).

Grupo: "Publico > Metricas" — disenhado para graficas/tablas de la pagina
principal. Todas las rutas son GET y devuelven el envelope habitual
SuccessResponse (data + total cuando hay listas). Los datos vienen solo de
vistas del esquema `publico` (agregados; sin datos personales ni rutas de
archivos). Caché en memoria por endpoint (PUBLICO_CACHE_TTL segundos).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..response import SuccessResponse
from . import service

TAG = "Público > Métricas"

router = APIRouter(prefix="/publico", tags=[TAG])


def _ok(msg: str, data, total=None):
    if total is None and isinstance(data, list):
        total = len(data)
    return SuccessResponse(message=msg, data=data, total=total)


# ------------------------------------------------------------------ KPIs

@router.get("/resumen", summary="KPIs globales para tarjetas de portada", tags=[TAG])
def resumen(db: Session = Depends(get_db)):
    """Una sola llamada con los KPIs: EDAN (consolidado/local), repositorio,
    usuarios activos, geografia, censo nacional y MotorIA."""
    return _ok("KPIs globales", service.kpis_globales(db))


# ------------------------------------------------------------------- EDAN

@router.get("/edan/resumen", summary="Totales EDAN por ambito (consolidado y local)", tags=[TAG])
def edan_resumen(db: Session = Depends(get_db)):
    return _ok("Resumen EDAN", service.edan_resumen(db))


@router.get("/edan/serie-anios", summary="Eventos EDAN por ano desde el inicio (huecos en 0)", tags=[TAG])
def edan_serie_anios(db: Session = Depends(get_db)):
    """Serie continua `[{ambito, anio, total}]` con ambito
    'consolidado' (edan.edan) y 'local' (edan.edan_localidades)."""
    return _ok("Serie anual EDAN", service.edan_serie_anios(db))


@router.get("/edan/serie-anios-por-tipo", summary="Eventos EDAN por ano y tipo de evento (apilable)", tags=[TAG])
def edan_serie_anios_tipo(db: Session = Depends(get_db)):
    return _ok("Serie anual EDAN por tipo", service.edan_serie_anios_tipo(db))


@router.get("/edan/serie-meses", summary="Eventos EDAN por mes desde el inicio (YYYY-MM, huecos en 0)", tags=[TAG])
def edan_serie_meses(db: Session = Depends(get_db)):
    return _ok("Serie mensual EDAN", service.edan_serie_meses(db))


@router.get("/edan/tipos-evento", summary="Tipos de evento mas recurrentes (historico)", tags=[TAG])
def edan_tipos_evento(db: Session = Depends(get_db)):
    return _ok("Tipos de evento", service.edan_tipos_evento(db))


@router.get("/edan/estados", summary="Distribucion por estado del workflow EDAN (por ambito)", tags=[TAG])
def edan_estados(db: Session = Depends(get_db)):
    return _ok("Estados EDAN", service.edan_estados(db))


@router.get("/edan/departamentos", summary="Ranking de departamentos por eventos y poblacion afectada", tags=[TAG])
def edan_departamentos(db: Session = Depends(get_db)):
    return _ok("EDAN por departamento", service.edan_departamentos(db))


@router.get("/edan/sectores", summary="Sectores afectados (flags de edan_localidades)", tags=[TAG])
def edan_sectores(db: Session = Depends(get_db)):
    return _ok("Sectores afectados", service.edan_sectores(db))


# ------------------------------------------------------------- REPOSITORIO

@router.get("/repositorio/serie-anios", summary="Documentos del repositorio por ano y origen (huecos en 0)", tags=[TAG])
def repo_serie_anios(db: Session = Depends(get_db)):
    """`[{origen, anio, total}]` con origen EDAN / RIDA / DOC_PRECEDENTE
    (solo documentos activos)."""
    return _ok("Serie anual de documentos", service.repo_serie_anios(db))


@router.get("/repositorio/serie-anios-por-tipo", summary="Documentos por ano y tipo de documento", tags=[TAG])
def repo_serie_anios_tipo(db: Session = Depends(get_db)):
    return _ok("Serie anual por tipo", service.repo_serie_anios_tipo(db))


@router.get("/repositorio/resumen", summary="Conteos del repositorio (total, por origen, por tipo, por firma)", tags=[TAG])
def repo_resumen(db: Session = Depends(get_db)):
    return _ok("Resumen repositorio", service.repo_resumen(db))


# ---------------------------------------------------------------- USUARIOS

@router.get("/usuarios/resumen", summary="Usuarios: solo conteos agregados (totales, rol, cargo, geografia)", tags=[TAG])
def usuarios_resumen(db: Session = Depends(get_db)):
    """Agregados sin datos personales: totales/activos/inactivos, cantidad por
    rol, cantidad por cargo y cantidad por departamento/provincia/municipio."""
    return _ok("Resumen de usuarios", service.usuarios_resumen(db))


# ---------------------------------------------------------------- MOTORIA

@router.get("/motor-ia/resumen", summary="MotorIA: documentos, chunks y uso LLM/embeddings (conteos)", tags=[TAG])
def motoria_resumen(db: Session = Depends(get_db)):
    return _ok("Resumen MotorIA", service.motoria_resumen(db))


# -------------------------------------------------------------------- GEO

@router.get("/geo/resumen", summary="Division territorial: conteos de departamentos, provincias, municipios, manzanos y comunidades", tags=[TAG])
def geo_resumen(db: Session = Depends(get_db)):
    return _ok("Resumen geografico", service.geo_resumen(db))


# ------------------------------------------------------------------ CENSO

@router.get("/censo/nacional", summary="Censo 2024: poblacion, viviendas, hogares y personas por hogar (nacional)", tags=[TAG])
def censo_nacional(db: Session = Depends(get_db)):
    return _ok("Censo nacional", service.censo_nacional(db))


@router.get("/censo/departamentos", summary="Censo 2024 por departamento (poblacion y personas por hogar)", tags=[TAG])
def censo_departamentos(db: Session = Depends(get_db)):
    return _ok("Censo por departamento", service.censo_departamentos(db))


@router.get("/censo/provincias", summary="Censo 2024 por provincia (poblacion y personas por hogar)", tags=[TAG])
def censo_provincias(db: Session = Depends(get_db)):
    return _ok("Censo por provincia", service.censo_provincias(db))


@router.get("/censo/municipios", summary="Censo 2024 por municipio (poblacion y personas por hogar)", tags=[TAG])
def censo_municipios(db: Session = Depends(get_db)):
    return _ok("Censo por municipio", service.censo_municipios(db))
