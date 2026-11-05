#!/bin/bash
# ================================================================
#  SINAGERSAT - DESPLIEGUE COMPLETO (desde cero)
#  Orquesta todos los pasos: requisitos → postgres → BD → API →
#  entorno → servicios → verificación.
#
#  Uso:
#    sudo bash despliegue/scripts/desplegar_todo.sh              # todo
#    sudo bash despliegue/scripts/desplegar_todo.sh --db-only    # solo BD
#    sudo bash despliegue/scripts/desplegar_todo.sh --api-only   # solo API
#    sudo bash despliegue/scripts/desplegar_todo.sh --no-verify  # sin verificación final
#
#  Requiere: Ubuntu/Debian 22.04+, internet, carpeta completa
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
AZUL="\033[0;34m"
CYAN="\033[0;36m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }
step() { echo -e "\n${AZUL}[$1/$TOTAL]${SIN_COLOR} ${CYAN}$2${SIN_COLOR}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"

# ================================================================
#  PARAMETROS
# ================================================================
MODE="full"
SKIP_VERIFY=false
for arg in "$@"; do
    case $arg in
        --db-only)   MODE="db" ;;
        --api-only)  MODE="api" ;;
        --no-verify) SKIP_VERIFY=true ;;
        --help|-h)
            echo "Uso: sudo bash despliegue/scripts/desplegar_todo.sh [opciones]"
            echo ""
            echo "Opciones:"
            echo "  (sin args)     Despliegue completo (postgres + BD + API + servicios)"
            echo "  --db-only      Solo PostgreSQL + restaurar BD"
            echo "  --api-only     Solo instalar API (si PG ya está)"
            echo "  --no-verify    Omitir verificación final"
            echo "  --help         Esta ayuda"
            exit 0
            ;;
    esac
done

case $MODE in
    full) TOTAL=7 ;;
    db)   TOTAL=4 ;;
    api)  TOTAL=3 ;;
esac

echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  SINAGERSAT - DESPLIEGUE COMPLETO${SIN_COLOR}"
echo -e "${CYAN}  Modo: $MODE${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""

if [ "$EUID" -ne 0 ] && [ "$MODE" != "api" ]; then
    fail "Ejecuta como root: sudo bash despliegue/scripts/desplegar_todo.sh"
    exit 1
fi

# ================================================================
#  1. REQUISITOS
# ================================================================
step 1 "Verificando requisitos del sistema..."
if bash "$SCRIPT_DIR/00_requisitos.sh"; then
    ok "Requisitos verificados"
else
    warn "Algunos requisitos fallaron — se intentará continuar"
fi

# ================================================================
#  2. POSTGRESQL
# ================================================================
if [ "$MODE" != "api" ]; then
    step 2 "Instalando/configurando PostgreSQL..."
    if [ "$EUID" -eq 0 ]; then
        bash "$SCRIPT_DIR/01_instalar_postgres.sh"
    else
        fail "Se requiere root para instalar PostgreSQL"
        exit 1
    fi
else
    step 2 "Saltando PostgreSQL (modo --api-only)..."
    ok "Omitido"
fi

# ================================================================
#  3. BASE DE DATOS
# ================================================================
if [ "$MODE" != "api" ]; then
    step 3 "Restaurando base de datos..."
    if [ "$EUID" -eq 0 ]; then
        bash "$SCRIPT_DIR/02_restaurar_bd.sh"
    else
        fail "Se requiere root para restaurar la BD"
        exit 1
    fi
else
    step 3 "Saltando BD (modo --api-only)..."
    ok "Omitido"
fi

# ================================================================
#  4. API (venv + dependencias)
# ================================================================
step 4 "Instalando entorno Python de la API..."
bash "$SCRIPT_DIR/03_instalar_api.sh"

# ================================================================
#  5. ARCHIVO .env
# ================================================================
step 5 "Configurando variables de entorno (.env)..."
bash "$SCRIPT_DIR/04_configurar_env.sh"

# ================================================================
#  6. SERVICIOS SYSTEMD
# ================================================================
if command -v systemctl &>/dev/null && [ "$EUID" -eq 0 ]; then
    step 6 "Instalando servicios systemd..."
    bash "$SCRIPT_DIR/05_instalar_servicios.sh"
else
    step 6 "Saltando systemd (no root o sin systemctl)..."
    warn "Arranca manualmente: bash start_api.sh"
fi

# ================================================================
#  7. VERIFICACION
# ================================================================
if [ "$SKIP_VERIFY" = true ]; then
    step 7 "Verificación omitida (--no-verify)..."
else
    step 7 "Verificando despliegue..."
    if bash "$SCRIPT_DIR/06_verificar.sh"; then
        ok "Verificación completada"
    else
        warn "La verificación reportó fallos — revisar salida arriba"
    fi
fi

# ================================================================
#  RESUMEN
# ================================================================
echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  DESPLIEGUE COMPLETADO${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""
echo "  Servicios:"
echo "    systemctl status sinagersat-api"
echo "    systemctl status motoria-embeddings"
echo ""
echo "  URLs:"
echo "    API:        http://localhost:8000"
echo "    Swagger:    http://localhost:8000/docs"
echo "    Embeddings: http://localhost:8001/docs"
echo ""
echo "  Base de datos:"
echo "    PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1"
echo ""
echo "  Documentación:"
echo "    despliegue/docs/"
echo ""
