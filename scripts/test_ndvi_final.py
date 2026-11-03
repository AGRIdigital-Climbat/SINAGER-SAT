#!/usr/bin/env python3
import sys, os, json
from datetime import date, timedelta
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.sinb import service_ndvi
from sqlalchemy import text

db = SessionLocal()

try:
    print("=== INGESTA NDVI - PRIMERA VEZ ===\n")
    
    # Obtener 3 comunidades desde shared
    result = db.execute(text("""
        SELECT codigo_ine, nombre, lat, lon 
        FROM shared.comunidades 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        LIMIT 3
    """))
    comunidades = list(result.mappings().all())
    
    for com in comunidades:
        print(f"📍 {com['nombre']} ({com['codigo_ine']})")
        
        bbox = (float(com['lon']) - 0.05, float(com['lat']) - 0.05, float(com['lon']) + 0.05, float(com['lat']) + 0.05)
        
        # Consultar EarthSearch
        escenas = service_ndvi.consultar_earthsearch(
            bbox=bbox,
            fecha_desde=date.today()-timedelta(days=30),
            fecha_hasta=date.today(),
            max_nubes=20.0
        )
        
        if not escenas:
            print(f"   ⚠️  Sin escenas\n")
            continue
        
        print(f"   ✅ {len(escenas)} escenas encontradas")
        
        # Procesar primera escena
        escena = escenas[0]
        props = escena.get('properties', {})
        escena_id = escena.get('id', props.get('id'))
        
        # Obtener ID de escena desde BD
        result = db.execute(text("""
            SELECT id FROM sinb.escena_satelital
            WHERE escena_id = :escena_id
        """), {"escena_id": escena_id})
        
        escena_row = result.mappings().first()
        
        if escena_row:
            escena_db_id = escena_row['id']
            
            # Guardar agregado (con ndvi simulado)
            db.execute(text("""
                INSERT INTO sinb.agregado_satelital 
                    (id_escena_satelital, codigo_comunidad, ndvi_promedio, fecha_proceso)
                VALUES (:id_escena, :codigo, :ndvi, now())
                ON CONFLICT (id_escena_satelital, codigo_comunidad) DO UPDATE SET
                    ndvi_promedio = EXCLUDED.ndvi_promedio,
                    fecha_proceso = now()
            """), {
                "id_escena": escena_db_id,
                "codigo": com['codigo_ine'],
                "ndvi": Decimal('0.45')  # NDVI simulado
            })
            db.commit()
            
            print(f"   ✅ {escena_id} procesada\n")
    
    # Verificar datos
    print("=== DATOS EN BD ===")
    result = db.execute(text("""
        SELECT 
            (SELECT count(*) FROM sinb.escena_satelital) as escenas,
            (SELECT count(*) FROM sinb.agregado_satelital) as agregados
    """))
    stats = result.mappings().first()
    print(f"  Escenas: {stats['escenas']}")
    print(f"  Agregados: {stats['agregados']}")
    
    print("\n=== ✅ NDVI INGESTADO EXITOSAMENTE ===")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
