#!/usr/bin/env python3
"""
Ingesta manual de Pronóstico Digital - Primera ejecución
Sin autenticación - llama directamente al service
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import get_db
from api.sinb.service import guardar_pronostico_diario_municipal
from sqlalchemy import text
import requests

def main():
    db = next(get_db())
    
    print("=== INGESTA PRONÓSTICO DIGITAL (PRIMERA VEZ) ===")
    
    # Obtener municipios con coordenadas desde geometría
    print("Obteniendo municipios con coordenadas...")
    result = db.execute(text("""
        SELECT id, nombre, 
               ST_Y(ST_Centroid(geom)) as lat, 
               ST_X(ST_Centroid(geom)) as lon
        FROM shared.municipio
        WHERE geom IS NOT NULL
        ORDER BY id
        LIMIT 10
    """))
    
    municipios = list(result.mappings().all())
    print(f"Municipios encontrados: {len(municipios)}")
    print("")
    
    # Ingestar para cada municipio
    for muni in municipios:
        print(f"Procesando {muni['nombre']} (ID: {muni['id']})...")
        try:
            # Llamar directamente al service
            registros = guardar_pronostico_diario_municipal(
                db=db,
                id_municipio=muni['id'],
                latitud=float(muni['lat']),
                longitud=float(muni['lon'])
            )
            print(f"  ✅ {registros} días guardados")
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:80]}")
    
    db.commit()
    print("\n=== INGESTA COMPLETADA ===")
    db.close()

if __name__ == "__main__":
    main()
