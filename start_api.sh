#!/bin/bash
# SINAGERSAT - Iniciar API
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
echo ""
echo "  SINAGERSAT API - http://0.0.0.0:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  VPN/Red: http://10.10.0.24:8000/docs"
echo ""
echo "  Opciones de host:"
echo "    0.0.0.0    → todas las interfaces de red (por defecto, recomendado)"
echo "    127.0.0.1  → solo localhost"
echo "    10.10.0.24 → IP fija del servidor"
echo ""
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
# Para solo localhost:
#   uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
# Para IP fija:
#   uvicorn api.main:app --host 10.10.0.24 --port 8000 --workers 4
