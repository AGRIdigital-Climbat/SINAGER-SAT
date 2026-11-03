#!/usr/bin/env python3
"""
CRON Pronóstico Digital - Ingesta automática PARA TODA BOLIVIA
SIN AUTENTICACIÓN - llama directamente al service

Corrida: 06:10 y 18:10 hora de Bolivia (10:10 y 22:10 UTC).

Dos fases:
  1. TODOS los municipios con geometría, 16 días por municipio, 3 reintentos
     con espera exponencial sobre Open-Meteo (2/4/8 s).
  2. Repaso: los municipios que quedaron con menos de 16 días en la ventana
     hoy..hoy+15 se vuelven a intentar (hasta 2 rondas). Un timeout suelto ya
     no deja al municipio con 15 días esperando a la corrida siguiente.

No se borra nada: los días pasados quedan como evidencia; sólo se reescriben
(ON CONFLICT) las fechas que trae Open-Meteo y se crean las futuras.
"""
import os
import sys
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from api.database import get_db
from api.sinb import service
from api.sinb.service import guardar_pronostico_diario_municipal

REINTENTOS = 3          # intentos sobre Open-Meteo por municipio
RONDAS_REPASO = 2       # rondas extra de repaso para municipios incompletos
HORIZONTE = service.HORIZONTE_DIAS


def _municipios(db):
    """Municipios de Bolivia con centroide desde GEOMETRÍA."""
    result = db.execute(text("""
        SELECT id, nombre,
               ST_Y(ST_Centroid(geom)) as lat,
               ST_X(ST_Centroid(geom)) as lon
        FROM shared.municipio
        WHERE geom IS NOT NULL
        ORDER BY id
    """))
    return list(result.mappings().all())


def _dias_por_municipio(db, hoy):
    """Días guardados en la ventana hoy..hoy+HORIZONTE-1, por municipio."""
    rows = db.execute(text("""
        SELECT id_municipio, COUNT(*) AS dias
        FROM sinb.pronostico_diario_municipal
        WHERE fecha BETWEEN :hoy AND :fin
        GROUP BY id_municipio
    """), {"hoy": hoy, "fin": hoy + timedelta(days=HORIZONTE - 1)}).mappings().all()
    return {r["id_municipio"]: r["dias"] for r in rows}


def _procesar(db, municipios, hoy, etiqueta):
    """Guarda 16 días por municipio. Devuelve (registros, exitos, errores, fallidos)."""
    print(f"--- {etiqueta}: {len(municipios)} municipios ({REINTENTOS} reintentos c/u) ---")
    total_registros = 0
    exitos = 0
    errores = []
    fallidos = []

    for i, muni in enumerate(municipios, 1):
        try:
            registros = guardar_pronostico_diario_municipal(
                db=db,
                id_municipio=muni["id"],
                latitud=float(muni["lat"]),
                longitud=float(muni["lon"]),
                fecha=hoy,
                reintentos=REINTENTOS,
            )
            if isinstance(registros, dict):
                total_registros += registros.get("registros_guardados", 0)
            elif isinstance(registros, int):
                total_registros += registros
            exitos += 1

            if i % 50 == 0:
                print(f"  Progreso: {i}/{len(municipios)} municipios...")

        except Exception as e:
            # Sin esto la transacción queda abortada y TODOS los municipios
            # siguientes fallarían en cadena.
            db.rollback()
            errores.append(f"{muni['nombre']} ({muni['id']}): {str(e)[:80]}")
            print(f"  ERROR {muni['nombre']} ({muni['id']}): {str(e)[:80]}")
            fallidos.append(muni)

    return total_registros, exitos, errores, fallidos


def main():
    inicio = time.time()
    db = next(get_db())
    hoy = service._hoy_bolivia()

    # Opcional: ./cron_pronostico_digital_auto.py 20201 20304  → sólo ésos
    ids_filtro = [int(a) for a in sys.argv[1:] if a.isdigit()]

    print("=== PRONÓSTICO DIGITAL - TODA BOLIVIA ===")
    print(f"Fecha (hora Bolivia): {hoy}")
    if ids_filtro:
        print(f"Filtro manual de municipios: {ids_filtro}")
    print()

    municipios = _municipios(db)
    if ids_filtro:
        municipios = [m for m in municipios if m["id"] in ids_filtro]
    print(f"Municipios a procesar: {len(municipios)}\n")

    # ------------------------------------------------------------ FASE 1
    total_registros, exitos, errores, fallidos = _procesar(db, municipios, hoy, "Fase 1: todos")

    # ------------------------------------------------------------ FASE 2
    # Repite los que quedaron con hueco en la ventana Y los que devolvieron
    # error: un 503 de Open-Meteo puede dejar 16 filas de la corrida anterior
    # (ventana completa) y aun así el municipio necesita su refresco.
    dias = _dias_por_municipio(db, hoy)
    pendientes = {m["id"]: m for m in municipios if dias.get(m["id"], 0) < HORIZONTE}
    for m in fallidos:
        pendientes.setdefault(m["id"], m)
    pendientes = list(pendientes.values())
    rondas = 0

    while pendientes and rondas < RONDAS_REPASO:
        rondas += 1
        resumen = ", ".join(f"{m['nombre']} ({m['id']}): {dias.get(m['id'], 0)} días"
                            for m in pendientes)
        print(f"\n--- Repaso ronda {rondas}: {resumen} ---")
        extra, _, err_repaso, fallidos_repaso = _procesar(
            db, pendientes, hoy, f"Fase 2 ronda {rondas}")
        total_registros += extra
        errores.extend(err_repaso)
        dias = _dias_por_municipio(db, hoy)
        nuevos = {m["id"]: m for m in municipios if dias.get(m["id"], 0) < HORIZONTE}
        for m in fallidos_repaso:
            nuevos.setdefault(m["id"], m)
        pendientes = list(nuevos.values())

    # ------------------------------------------------------------ RESUMEN
    esperados = len(municipios) * HORIZONTE
    filas_ventana = db.execute(text("""
        SELECT COUNT(*) AS n FROM sinb.pronostico_diario_municipal
        WHERE fecha BETWEEN :hoy AND :fin
    """), {"hoy": hoy, "fin": hoy + timedelta(days=HORIZONTE - 1)}).scalar()

    print("\n=== RESUMEN ===")
    print(f"Municipios procesados (fase 1): {exitos}/{len(municipios)}")
    print(f"Rondas de repaso ejecutadas: {rondas}")
    print(f"Registros escritos (acumulados): {total_registros}")
    print(f"Errores registrados: {len(errores)}")
    print(f"Filas en ventana {hoy}..{hoy + timedelta(days=HORIZONTE - 1)}: "
          f"{filas_ventana} (esperadas {esperados} para este filtro)")

    incompletos = list(pendientes)
    if incompletos:
        print(f"\nMUNICIPIOS AÚN INCOMPLETOS ({len(incompletos)}):")
        for m in incompletos:
            print(f"  - {m['nombre']} ({m['id']}): {dias.get(m['id'], 0)}/{HORIZONTE} días")
    else:
        print("Todos los municipios tienen el horizonte completo de 16 días.")

    if errores:
        print("\nPrimeros errores:")
        for err in errores[:5]:
            print(f"  - {err}")

    db.close()
    print(f"\n=== INGESTA COMPLETADA - {hoy} - en {time.time() - inicio:.0f}s ===")
    return 1 if incompletos or exitos < len(municipios) else 0


if __name__ == "__main__":
    sys.exit(main())
