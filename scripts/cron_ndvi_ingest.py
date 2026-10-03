#!/usr/bin/env python3
"""
Script CRON para ingesta diaria de NDVI desde EarthSearch.

Ejecutar diariamente a las 06:00 (hora Bolivia):
0 6 * * * cd /home/prosuco/SINAGERSAT/BaseData && venv/bin/python scripts/cron_ndvi_ingest.py >> /var/log/sinb/ndvi_cron.log 2>&1

"""
import sys
import os
from datetime import date, timedelta

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from api.sinb import service_ndvi
from sqlalchemy.orm import Session


def main():
    """Ejecutar ingesta diaria de NDVI."""
    print(f"=== INICIO INGESTA NDVI - {date.today()} ===")
    
    # Obtener sesión DB
    db = next(get_db())
    
    try:
        print("Iniciando ingestión de NDVI...")
        
        # Obtener todas las comunidades
        print("Obteniendo lista de comunidades...")
        result = db.execute(
            "SELECT codigo_ine, nombre FROM shared.comunidades ORDER BY codigo_ine"
        )
        comunidades = [dict(row)["codigo_ine"] for row in result.mappings().all()]
        
        print(f"Total comunidades: {len(comunidades)}")
        
        # Ejecutar ingesta (limitar a 50 comunidades para demo)
        # En producción: remover el slice [:50]
        print("Ejecutando ingesta (modo demo: 50 comunidades)...")
        resultado = service_ndvi.ingestar_ndvi_comunidades(
            db,
            codigos_comunidades=comunidades[:50],  # Limitar para demo
            max_nubes=20.0
        )
        
        # Imprimir resumen
        print("\n=== RESUMEN ===")
        print(f"Escenas consultadas: {resultado['escenas_consultadas']}")
        print(f"Escenas procesadas: {resultado['escenas_procesadas']}")
        print(f"Comunidades procesadas: {resultado['comunidades_procesadas']}")
        
        if resultado['errores']:
            print(f"\nErrores ({len(resultado['errores'])}):")
            for err in resultado['errores'][:5]:  # Mostrar solo primeros 5
                print(f"  - {err}")
        
        print(f"\n=== FIN INGESTA - {date.today()} ===")
        
    except Exception as e:
        print(f"ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
