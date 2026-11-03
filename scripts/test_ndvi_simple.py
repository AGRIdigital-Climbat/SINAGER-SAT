#!/usr/bin/env python3
import sys, os, json
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.sinb import service_ndvi
from sqlalchemy import text

db = SessionLocal()

try:
    print("=== 1. OBTENER COMUNIDAD DESDE SHARED ===")
    result = db.execute(text("""
        SELECT codigo_ine, nombre, lat, lon 
        FROM shared.comunidades 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        LIMIT 1
    """))
    com = result.mappings().first()
    
    if not com:
        print("❌ No hay comunidades con coordenadas")
        sys.exit(1)
    
    print(f"  ✅ {com['nombre']} ({com['codigo_ine']})")
    print(f"     lat={com['lat']}, lon={com['lon']}")
    
    # Crear bbox
    bbox = (
        float(com['lon']) - 0.05,
        float(com['lat']) - 0.05,
        float(com['lon']) + 0.05,
        float(com['lat']) + 0.05
    )
    print(f"\n  BBOX: {bbox}")
    
    # Fechas (últimos 30 días)
    fecha_desde = date.today() - timedelta(days=30)
    
    print(f"\n=== 2. CONSULTAR EARTHSEARCH ===")
    print(f"  Fecha: {fecha_desde} hasta {date.today()}")
    
    escenas = service_ndvi.consultar_earthsearch(
        bbox=bbox,
        fecha_desde=fecha_desde,
        fecha_hasta=date.today(),
        max_nubes=20.0
    )
    
    print(f"  ✅ Escenas encontradas: {len(escenas)}")
    
    if escenas:
        print(f"\n=== 3. PROCESAR PRIMERA ESCENA ===")
        escena = escenas[0]
        
        props = escena.get('properties', {})
        print(f"  ID: {props.get('id', 'N/A')}")
        print(f"  Fecha: {props.get('datetime', 'N/A')}")
        print(f"  Nubes: {props.get('eo:cloud_cover', 'N/A')}%")
        print(f"  Plataforma: {props.get('platform', 'N/A')}")
        
        # Serializar metadata
        metadata = json.dumps(props)
        print(f"\n  Metadata size: {len(metadata)} chars")
        
        # Guardar escena
        print(f"\n=== 4. GUARDAR EN BD ===")
        result = db.execute(text("""
            INSERT INTO sinb.escena_satelital (escena_id, fecha_adquisicion, cobertura_nubes, metadata)
            VALUES (:escena_id, :fecha, :nubes, :metadata)
            ON CONFLICT (escena_id) DO UPDATE SET
                cobertura_nubes = EXCLUDED.cobertura_nubes,
                fecha_proceso = now()
            RETURNING id
        """), {
            "escena_id": props.get('id'),
            "fecha": props.get('datetime', '')[:10],
            "nubes": props.get('eo:cloud_cover', 0),
            "metadata": metadata
        })
        
        escena_id = result.mappings().first()['id']
        print(f"  ✅ Escena guardada (ID={escena_id})")
        
        db.commit()
        
        # Guardar agregado
        print(f"\n=== 5. GUARDAR AGREGADO ===")
        db.execute(text("""
            INSERT INTO sinb.agregado_satelital (codigo_comunidad, escena_id, fecha)
            VALUES (:codigo, :escena_id, :fecha)
            ON CONFLICT (codigo_comunidad, escena_id) DO NOTHING
        """), {
            "codigo": com['codigo_ine'],
            "escena_id": escena_id,
            "fecha": props.get('datetime', '')[:10]
        })
        db.commit()
        print(f"  ✅ Agregado guardado")
    
    print(f"\n=== ✅ TEST COMPLETADO EXITOSAMENTE ===")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
