#!/bin/bash
# ================================================================
#  SINAGERSAT - 05 INSTALAR SERVICIOS SYSTEMD
#  Instala unidades systemd para API y MotorIA con rutas dinámicas.
#  Uso: sudo bash despliegue/scripts/05_instalar_servicios.sh
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash despliegue/scripts/05_instalar_servicios.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DESPL_DIR")"

# Usuario real (no root)
REAL_USER="${SUDO_USER:-prosuco}"
REAL_HOME=$(eval echo "~$REAL_USER")

echo ""
echo "================================================"
echo "  SINAGERSAT - SERVICIOS SYSTEMD"
echo "================================================"
echo ""
echo "  Proyecto:  $PROJECT_DIR"
echo "  Usuario:   $REAL_USER"
echo ""

if ! command -v systemctl &>/dev/null; then
    fail "systemctl no disponible — instalar servicios manualmente"
    exit 1
fi

# Crear directorios necesarios
mkdir -p "$PROJECT_DIR/uploads/reports" "$PROJECT_DIR/uploads/motor_ia" "$PROJECT_DIR/.keys" "$PROJECT_DIR/logs"
chown -R "$REAL_USER":"$(id -gn "$REAL_USER")" "$PROJECT_DIR/uploads" "$PROJECT_DIR/.keys" "$PROJECT_DIR/logs" 2>/dev/null || true
chmod 700 "$PROJECT_DIR/.keys" 2>/dev/null || true
ok "Directorios creados (uploads/, .keys/, logs/)"

# --- Unidad: sinagersat-api.service ---
cat > /etc/systemd/system/sinagersat-api.service << APIEOF
[Unit]
Description=SINAGERSAT API REST (FastAPI)
After=network.target postgresql.service motoria-embeddings.service
Requires=postgresql.service
Wants=motoria-embeddings.service

[Service]
Type=simple
User=${REAL_USER}
Group=$(id -gn "$REAL_USER")
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 3
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitIntervalSec=60
Environment=PATH=${PROJECT_DIR}/venv/bin:/usr/bin:/bin
EnvironmentFile=${PROJECT_DIR}/.env

[Install]
WantedBy=multi-user.target
APIEOF
ok "sinagersat-api.service escrita"

# --- Unidad: motoria-embeddings.service ---
cat > /etc/systemd/system/motoria-embeddings.service << MIAEOF
[Unit]
Description=SINAGERSAT MotorIA Embeddings (FastEmbed ONNX)
After=network.target postgresql.service

[Service]
Type=simple
User=${REAL_USER}
Group=$(id -gn "$REAL_USER")
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/uvicorn services.motoria_embeddings.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=on-failure
RestartSec=10
Environment=PATH=${PROJECT_DIR}/venv/bin:/usr/bin:/bin
EnvironmentFile=${PROJECT_DIR}/.env

[Install]
WantedBy=multi-user.target
MIAEOF
ok "motoria-embeddings.service escrita"

# Recargar y habilitar
systemctl daemon-reload
systemctl enable sinagersat-api.service 2>/dev/null || true
systemctl enable motoria-embeddings.service 2>/dev/null || true
ok "Servicios habilitados al arranque"

# Intentar arrancar
echo ""
echo "  Arrancando servicios..."
systemctl start motoria-embeddings.service 2>/dev/null && ok "motoria-embeddings iniciado" || warn "motoria-embeddings no arrancó (revisar: systemctl status motoria-embeddings)"
systemctl start sinagersat-api.service 2>/dev/null && ok "sinagersat-api iniciado" || warn "sinagersat-api no arrancó (revisar: systemctl status sinagersat-api)"

sleep 3

echo ""
echo "================================================"
echo -e "  ${VERDE}SERVICIOS INSTALADOS${SIN_COLOR}"
echo "================================================"
echo "  Comandos útiles:"
echo "    systemctl status sinagersat-api"
echo "    systemctl status motoria-embeddings"
echo "    systemctl restart sinagersat-api"
echo "    journalctl -u sinagersat-api -f"
echo ""
echo "  Siguiente: bash despliegue/scripts/06_verificar.sh"
echo ""
