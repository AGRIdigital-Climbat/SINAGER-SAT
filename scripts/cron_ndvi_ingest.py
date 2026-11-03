#!/usr/bin/env python3
"""
Script CRON para ingesta diaria de NDVI desde EarthSearch.
PARA TODA BOLIVIA - todas las comunidades
SIN AUTENTICACIÓN - llama directamente al service
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import get_db
from api.sinb import service_ndvi
from sqlalchemy import text

def main():
    print(f"=== NDVI SATELITAL - TODA BOLIVIA ===")
    print(f"Fecha: {date.today()}\n")
    
    db = next(get_db())
    
    try:
        # Obtener TODAS las comunidades con coordenadas
        print("Obteniendo comunidades de Bolivia...")
        result = db.execute(text("""
            SELECT codigo_ine, nombre, lat, lon
            FROM shared.comunidades
            WHERE lat IS NOT NULL AND lon IS NOT NULL
            ORDER BY codigo_ine
        """))
        
        comunidades = list(result.mappings().all())
        print(f"Comunidades encontradas: {len(comunidades)}\n")
        
        # Ingestar NDVI para TODAS
        print("Ejecutando ingesta NDVI (puede tardar 30-60 min)...")
        resultado = service_ndvi.ingestar_ndvi_comunidades(
            db,
            codigos_comunidades=[c['codigo_ine'] for c in comunidades],
            max_nubes=25.0
        )
        
        # Resumen
        print(f"\n=== RESUMEN ===")
        print(f"Escenas consultadas: {resultado['escenas_consultadas']}")
        print(f"Escenas procesadas: {resultado['escenas_procesadas']}")
        print(f"Comunidades procesadas: {resultado['comunidades_procesadas']}")
        
        if resultado.get('errores'):
            print(f"\nErrores ({len(resultado['errores'])}):")
            for err in resultado['errores'][:5]:
                print(f"  - {str(err)[:100]}")
        
        print(f"\n=== INGESTA COMPLETADA - {date.today()} ===")
        
    except Exception as e:
        print(f"ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
