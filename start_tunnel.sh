#!/bin/bash
# ================================================================
#  SINAGERSAT - Iniciar API + Cloudflare Quick Tunnel
#  Uso: bash start_tunnel.sh
# ================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "================================================"
echo "  SINAGERSAT API + Cloudflare Tunnel"
echo "================================================"
echo ""

# Verificar que venv existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Matar procesos anteriores
pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

echo "[1/2] Iniciando API en puerto 8000..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
API_PID=$!
sleep 3

# Verificar que la API arrancó
if ! curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo "ERROR: La API no pudo iniciarse"
    cat /tmp/uvicorn.log | tail -5
    exit 1
fi
echo "  API corriendo (PID: $API_PID)"

echo "[2/2] Iniciando Cloudflare Quick Tunnel..."
cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!
sleep 8

# Extraer URL del tunnel
TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo "ERROR: No se pudo obtener la URL del tunnel"
    cat /tmp/cloudflared.log | tail -10
    kill $API_PID 2>/dev/null
    exit 1
fi

echo ""
echo "================================================"
echo "  SERVIDOR ACTIVO"
echo "================================================"
echo ""
echo "  Local:     http://localhost:8000"
echo "  Tunnel:    $TUNNEL_URL"
echo "  Docs:      $TUNNEL_URL/docs"
echo "  API Docs:  $TUNNEL_URL/redoc"
echo ""
echo "  API PID:   $API_PID"
echo "  Tunnel PID: $TUNNEL_PID"
echo ""
echo "  Para detener: kill $API_PID $TUNNEL_PID"
echo ""
echo "  Logs:"
echo "    API:     tail -f /tmp/uvicorn.log"
echo "    Tunnel:  tail -f /tmp/cloudflared.log"
echo ""

# Guardar PIDs para facilitar la limpieza
echo "$API_PID $TUNNEL_PID" > /tmp/sinagersat_pids.txt
echo "PIDs guardados en /tmp/sinagersat_pids.txt"
