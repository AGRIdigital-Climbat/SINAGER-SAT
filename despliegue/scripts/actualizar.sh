#!/bin/bash
# ================================================================
#  SINAGERSAT - ACTUALIZAR DESPLIEGUE EXISTENTE
#  Actualización segura: backup BD → aplicar código → migraciones →
#  reiniciar servicios. NO elimina datos.
#
#  Uso:
#    sudo bash despliegue/scripts/actualizar.sh              # completo
#    sudo bash despliegue/scripts/actualizar.sh --sin-bd     # sin backup BD
#    sudo bash despliegue/scripts/actualizar.sh --help
#
#  Requiere: despliegue ya instalado (ver desplegar_todo.sh)
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

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DESPL_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

# Parametros
SKIP_BACKUP=false
for arg in "$@"; do
    case $arg in
        --sin-bd) SKIP_BACKUP=true ;;
        --help|-h)
            echo "Uso: sudo bash despliegue/scripts/actualizar.sh [opciones]"
            echo ""
            echo "  (sin args)  Backup BD + migraciones + reiniciar servicios"
            echo "  --sin-bd    Omitir backup de BD (más rápido)"
            echo "  --help      Esta ayuda"
            exit 0
            ;;
    esac
done

TOTAL=5

echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  SINAGERSAT - ACTUALIZACION DE DESPLIEGUE${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""

if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash despliegue/scripts/actualizar.sh"
    exit 1
fi

# ================================================================
#  1. BACKUP DE BD (antes de tocar nada)
# ================================================================
if [ "$SKIP_BACKUP" = true ]; then
    step 1 "Backup de BD omitido (--sin-bd)..."
    ok "Omitido"
else
    step 1 "Creando backup de seguridad de la BD..."
    mkdir -p "$BACKUP_DIR"
    TS=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/pre_update_${TS}.sql"
    if PGPASSWORD=$PW pg_dump -h 127.0.0.1 -U "$USER" -d "$DB" --no-owner --no-privileges -f "$BACKUP_FILE" 2>/dev/null; then
        ok "Backup creado: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    else
        fail "No se pudo crear el backup — abortando actualización"
        exit 1
    fi
fi

# ================================================================
#  2. VERIFICAR INTEGRIDAD PREVIA
# ================================================================
step 2 "Verificando estado previo..."
if ! PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -c "SELECT 1;" >/dev/null 2>&1; then
    fail "La BD no responde — ¿está desplegado?"
    exit 1
fi
ok "BD accesible"

if [ ! -d "$PROJECT_DIR/api" ]; then
    fail "Directorio api/ no encontrado en $PROJECT_DIR"
    exit 1
fi
ok "Código de la API presente"

# ================================================================
#  3. ACTUALIZAR DEPENDENCIAS PYTHON
# ================================================================
step 3 "Actualizando dependencias Python..."
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    bash -c "source '$VENV_DIR/bin/activate' && pip install -q -r '$PROJECT_DIR/requirements.txt'" \
        && ok "Dependencias actualizadas" \
        || warn "Algunas dependencias fallaron — revisar pip"
else
    warn "venv no existe — ejecutar 03_instalar_api.sh"
fi

# ================================================================
#  4. EJECUTAR MIGRACIONES PENDIENTES
# ================================================================
step 4 "Ejecutando migraciones de BD..."
MIG_DIR="$DESPL_DIR/migraciones"
MIG_OK=0
MIG_FAIL=0
MIG_SKIP=0

if [ -d "$MIG_DIR" ]; then
    # Registrar migraciones ya aplicadas (si existe tabla de control)
    for MIG in $(ls -1v "$MIG_DIR"/*.sql 2>/dev/null); do
        NAME=$(basename "$MIG")
        # Saltar rollbacks en ejecución normal
        case "$NAME" in
            *_rollback.sql) MIG_SKIP=$((MIG_SKIP+1)); continue ;;
        esac
        # Ejecutar (algunas migraciones son idempotentes / IF NOT EXISTS)
        if PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -f "$MIG" >/dev/null 2>&1; then
            echo "    OK: $NAME"
            MIG_OK=$((MIG_OK+1))
        else
            # Puede fallar por "ya existe" — no es fatal
            echo "    SKIP/ERROR: $NAME (puede ya estar aplicada)"
            MIG_FAIL=$((MIG_FAIL+1))
        fi
    done
    ok "Migraciones: $MIG_OK aplicadas, $MIG_FAIL con avisos, $MIG_SKIP rollbacks omitidos"
else
    warn "Directorio de migraciones no encontrado: $MIG_DIR"
fi

# MotorIA requiere superusuario para CREATE EXTENSION vector
MOTOR_MIG="$MIG_DIR/v2.63.0_motor_ia.sql"
if [ -f "$MOTOR_MIG" ]; then
    echo "  Aplicando migración MotorIA (superusuario)..."
    sudo -u postgres psql -d "$DB" -f "$MOTOR_MIG" >/dev/null 2>&1 \
        && ok "MotorIA migración aplicada" \
        || warn "MotorIA migración con avisos (¿pgvector o ya aplicada?)"
fi

# ================================================================
#  5. REINICIAR SERVICIOS
# ================================================================
step 5 "Reiniciando servicios..."
if command -v systemctl &>/dev/null; then
    systemctl restart motoria-embeddings.service 2>/dev/null && ok "motoria-embeddings reiniciado" || warn "motoria-embeddings no reiniciado"
    sleep 2
    systemctl restart sinagersat-api.service 2>/dev/null && ok "sinagersat-api reiniciado" || warn "sinagersat-api no reiniciado"
    sleep 3
else
    pkill -f "uvicorn api.main" 2>/dev/null || true
    sleep 1
    warn "Sin systemctl — reinicia manualmente"
fi

# Health-check
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/" 2>/dev/null | grep -q "200\|30[0-9]"; then
    ok "API respondiendo en :8000"
else
    warn "API aún no responde en :8000 (puede estar arrancando)"
fi

# ================================================================
#  RESUMEN
# ================================================================
echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  ACTUALIZACION COMPLETADA${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""
if [ "$SKIP_BACKUP" = false ]; then
    echo "  Backup previo: $BACKUP_FILE"
fi
echo "  Migraciones:   $MIG_OK aplicadas / $MIG_FAIL avisos"
echo ""
echo "  Verificar:     bash despliegue/scripts/06_verificar.sh"
echo "  Rollback:      ver despliegue/docs/06_rollback.md"
echo ""
