#!/bin/bash
# ================================================================
#  SINAGERSAT - Iniciar API + Cloudflare Quick Tunnel
#  Acceso externo desde internet sin configurar router
#
#  Uso: bash start_tunnel.sh
# ================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CYAN="\033[0;36m"
VERDE="\033[0;32m"
ROJO="\033[0;31m"
AMARILLO="\033[1;33m"
BOLD="\033[1m"
SIN_COLOR="\033[0m"

echo ""
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  SINAGERSAT API + Cloudflare Tunnel${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  Acceso externo desde internet${SIN_COLOR}"
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo ""

# ── Verificar entorno virtual ──
if [ ! -d "venv" ]; then
    echo -e "${AMARILLO}[!]${SIN_COLOR} Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# ── Verificar cloudflared ──
if ! command -v cloudflared &>/dev/null; then
    echo -e "${AMARILLO}[!]${SIN_COLOR} Instalando cloudflared..."
    curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb 2>/dev/null
    sudo dpkg -i /tmp/cloudflared.deb 2>/dev/null
    rm -f /tmp/cloudflared.deb
fi

# ── Matar procesos anteriores ──
pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

# ── Iniciar API ──
echo -e "${BOLD}[1/3]${SIN_COLOR} Iniciando API SINAGERSAT..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
API_PID=$!
sleep 3

if ! curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo -e "${ROJO}[ERROR]${SIN_COLOR} La API no pudo iniciarse"
    cat /tmp/uvicorn.log | tail -5
    exit 1
fi
echo -e "  ${VERDE}[OK]${SIN_COLOR} API corriendo en puerto 8000 (PID: $API_PID)"

# ── Iniciar Cloudflare Tunnel ──
echo -e "${BOLD}[2/3]${SIN_COLOR} Iniciando Cloudflare Quick Tunnel..."
cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!

# Esperar a que el tunnel esté listo (hasta 15 segundos)
TUNNEL_URL=""
for i in $(seq 1 15); do
    TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${ROJO}[ERROR]${SIN_COLOR} No se pudo obtener la URL del tunnel"
    cat /tmp/cloudflared.log | tail -10
    kill $API_PID 2>/dev/null
    exit 1
fi

echo -e "  ${VERDE}[OK]${SIN_COLOR} Tunnel activo (PID: $TUNNEL_PID)"

# ── Verificar acceso externo ──
echo -e "${BOLD}[3/3]${SIN_COLOR} Verificando acceso externo..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$TUNNEL_URL/" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${VERDE}[OK]${SIN_COLOR} Acceso externo verificado"
else
    echo -e "  ${AMARILLO}[!]${SIN_COLOR} Código HTTP: $HTTP_CODE (puede estar propagándose)"
fi

# ── Guardar URL en archivo ──
echo "$TUNNEL_URL" > /tmp/sinagersat_url.txt

# ── Mostrar resultado ──
echo ""
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  SERVIDOR SINAGERSAT ACTIVO${SIN_COLOR}"
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo ""
echo -e "  ${BOLD}LOCAL:${SIN_COLOR}"
echo "    API:       http://localhost:8000"
echo "    Swagger:   http://localhost:8000/docs"
echo "    ReDoc:     http://localhost:8000/redoc"
echo ""
echo -e "  ${BOLD}ACCESO EXTERNO (desde internet):${SIN_COLOR}"
echo -e "    ${VERDE}$TUNNEL_URL${SIN_COLOR}"
echo ""
echo -e "    ${BOLD}Swagger:${SIN_COLOR}  $TUNNEL_URL/docs"
echo -e "    ${BOLD}ReDoc:${SIN_COLOR}    $TUNNEL_URL/redoc"
echo -e "    ${BOLD}Health:${SIN_COLOR}   $TUNNEL_URL/health"
echo ""
echo -e "  ${BOLD}Comparte esta URL:${SIN_COLOR}"
echo -e "    ${VERDE}$TUNNEL_URL${SIN_COLOR}"
echo ""
echo -e "  ${BOLD}PROCESOS:${SIN_COLOR}"
echo "    API PID:     $API_PID"
echo -e "    Tunnel PID:  $TUNNEL_PID"
echo ""
echo -e "  ${BOLD}DETENER:${SIN_COLOR}"
echo "    kill $API_PID $TUNNEL_PID"
echo ""
echo -e "  ${BOLD}LOGS:${SIN_COLOR}"
echo "    API:     tail -f /tmp/uvicorn.log"
echo "    Tunnel:  tail -f /tmp/cloudflared.log"
echo ""

# Guardar PIDs
echo "$API_PID $TUNNEL_PID" > /tmp/sinagersat_pids.txt
echo -e "  ${BOLD}URL guardada en:${SIN_COLOR} /tmp/sinagersat_url.txt"
echo ""
