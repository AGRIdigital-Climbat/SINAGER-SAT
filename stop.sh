#!/bin/bash
# SINAGERSAT - Detener todos los servicios
echo "Deteniendo SINAGERSAT..."
pkill -f "uvicorn api.main" 2>/dev/null && echo "  API detenida" || echo "  API no estaba corriendo"
echo "Listo."
