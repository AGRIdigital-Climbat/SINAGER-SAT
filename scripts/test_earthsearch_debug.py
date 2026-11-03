#!/usr/bin/env python3
import sys, os, json
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.sinb import service_ndvi
from sqlalchemy import text

db = SessionLocal()

try:
    # Obtener comunidad
    result = db.execute(text("""
        SELECT lat, lon FROM shared.comunidades 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        LIMIT 1
    """))
    com = result.mappings().first()
    
    bbox = (float(com['lon']) - 0.05, float(com['lat']) - 0.05, float(com['lon']) + 0.05, float(com['lat']) + 0.05)
    
    # Consultar
    escenas = service_ndvi.consultar_earthsearch(bbox=bbox, fecha_desde=date.today()-timedelta(days=30), fecha_hasta=date.today(), max_nubes=20.0)
    
    print("=== ESTRUCTURA DE RESPUESTA EARTHSEARCH ===")
    if escenas:
        escena = escenas[0]
        print(f"\nKeys nivel superior: {list(escena.keys())}")
        print(f"\nID directo: {escena.get('id')}")
        print(f"ID desde properties: {escena.get('properties', {}).get('id')}")
        
        # Buscar UUID
        for key in ['id', 'guid', 'uuid', 'name', 'title', 'sci:doi']:
            val = escena.get(key)
            if val:
                print(f"\n✅ {key}: {val}")
        
        # Ver properties
        props = escena.get('properties', {})
        print(f"\nProperties keys: {list(props.keys())[:10]}...")
        
        # El ID real suele estar en el properties
        print(f"\n=== CAMPOS QUE PODRÍAN SER ID ===")
        for k, v in props.items():
            if 'id' in k.lower() or k in ['title', 'name', 'guid', 'uid']:
                print(f"  {k}: {str(v)[:60]}")
        
        # Ver assets
        print(f"\nAssets: {list(escena.get('assets', {}).keys())}")
        
        # Guardar enlace
        print(f"\n=== ENLACES ===")
        for link in escena.get('links', [])[:3]:
            print(f"  {link.get('rel')}: {link.get('href', '')[:80]}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
