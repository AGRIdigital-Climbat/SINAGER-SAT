"""Metricas publicas del dashboard (GET /api/v2/publico).

Lee EXCLUSIVAMENTE las vistas del esquema `publico` (migracion v2.66.0):
solo agregados, sin datos personales ni rutas de archivos. Caché en memoria
con TTL (env PUBLICO_CACHE_TTL, default 60 s; 0 la desactiva).
"""
import os
import threading
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

CACHE_TTL = int(os.getenv("PUBLICO_CACHE_TTL", "60") or 0)

_cache: dict = {}
_lock = threading.Lock()


def _cached(key: str, loader):
    """Valor cacheado por `key` (loader() se ejecuta dentro de la session)."""
    now = time.monotonic()
    if CACHE_TTL > 0:
        with _lock:
            hit = _cache.get(key)
            if hit and hit[0] > now:
                return hit[1]
    data = loader()
    if CACHE_TTL > 0:
        with _lock:
            _cache[key] = (now + CACHE_TTL, data)
    return data


def _rows(db: Session, sql: str) -> list[dict]:
    return [dict(r) for r in db.execute(text(sql)).mappings().all()]


# ---------------------------------------------------------------- EDAN

def edan_resumen(db: Session):
    return _cached("edan_resumen",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_resumen ORDER BY ambito"))


def edan_serie_anios(db: Session):
    return _cached("edan_serie_anios",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_serie_anios"))


def edan_serie_anios_tipo(db: Session):
    return _cached("edan_serie_anios_tipo",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_serie_anios_tipo"))


def edan_serie_meses(db: Session):
    return _cached("edan_serie_meses",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_serie_meses"))


def edan_tipos_evento(db: Session):
    return _cached("edan_tipos_evento",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_tipos_evento"))


def edan_estados(db: Session):
    return _cached("edan_estados",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_estados"))


def edan_departamentos(db: Session):
    return _cached("edan_departamentos",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_departamentos"))


def edan_sectores(db: Session):
    return _cached("edan_sectores",
                   lambda: _rows(db, "SELECT * FROM publico.v_edan_sectores"))


# ---------------------------------------------------------- REPOSITORIO

def repo_serie_anios(db: Session):
    return _cached("repo_serie_anios",
                   lambda: _rows(db, "SELECT * FROM publico.v_repo_serie_anios"))


def repo_serie_anios_tipo(db: Session):
    return _cached("repo_serie_anios_tipo",
                   lambda: _rows(db, "SELECT * FROM publico.v_repo_serie_anios_tipo"))


def repo_resumen(db: Session):
    return _cached("repo_resumen",
                   lambda: _rows(db, "SELECT * FROM publico.v_repo_resumen"))


# --------------------------------------------------------------- USUARIOS

def usuarios_resumen(db: Session):
    def load():
        return {
            "totales": _rows(db, "SELECT * FROM publico.v_usuarios_resumen"),
            "por_rol": _rows(db, "SELECT * FROM publico.v_usuarios_rol"),
            "por_cargo": _rows(db, "SELECT * FROM publico.v_usuarios_cargo"),
            "por_geografia": _rows(db, "SELECT * FROM publico.v_usuarios_geografia"),
        }
    return _cached("usuarios_resumen", load)


# --------------------------------------------------------------- MOTORIA

def motoria_resumen(db: Session):
    return _cached("motoria_resumen",
                   lambda: _rows(db, "SELECT * FROM publico.v_motoria_resumen"))


# ------------------------------------------------------------------- GEO

def geo_resumen(db: Session):
    return _cached("geo_resumen",
                   lambda: _rows(db, "SELECT * FROM publico.v_geo_resumen"))


# ------------------------------------------------------------------ CENSO

def censo_nacional(db: Session):
    return _cached("censo_nacional",
                   lambda: _rows(db, "SELECT * FROM publico.v_censo_nacional"))


def censo_departamentos(db: Session):
    return _cached("censo_departamentos",
                   lambda: _rows(db, "SELECT * FROM publico.v_censo_departamentos"))


def censo_provincias(db: Session):
    return _cached("censo_provincias",
                   lambda: _rows(db, "SELECT * FROM publico.v_censo_provincias"))


def censo_municipios(db: Session):
    return _cached("censo_municipios",
                   lambda: _rows(db, "SELECT * FROM publico.v_censo_municipios"))


# ------------------------------------------------------------------ KPIs

def kpis_globales(db: Session):
    def load():
        rows = _rows(db, "SELECT * FROM publico.v_kpis_globales")
        return rows[0] if rows else {}
    return _cached("kpis_globales", load)
