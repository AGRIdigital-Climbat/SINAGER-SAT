#!/bin/bash
# ================================================================
#  SINAGERSAT - BACKUP COMPLETO DE LA BASE DE DATOS
#  Genera un pg_dump completo (esquemas + datos + extensiones como
#  PostGIS). Conserva los últimos N backups (por defecto 14).
#
#  Uso:
#    bash hacer_backup.sh                # backup ahora
#    bash hacer_backup.sh 30             # conservar 30 backups
#
#  Configura el cron diario con:
#    0 3 * * * /home/prosuco/SINAGERSAT/BaseData/database/hacer_backup.sh >> /var/log/sinagersat_backup.log 2>&1
# ================================================================
set -euo pipefail

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"
HOST="127.0.0.1"
KEEP="${1:-14}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR"

STAMP="$(date +%Y_%m_%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/backup_${STAMP}.sql"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
SIN_COLOR="\033[0m"
ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; exit 1; }

echo ""
echo "================================================"
echo "  SINAGERSAT - BACKUP DE BASE DE DATOS"
echo "  Fecha: $(date)"
echo "================================================"

# ── Verificar conexión ──
if ! PGPASSWORD=$PW pg_isready -h $HOST -U $USER -d $DB -q 2>/dev/null; then
    fail "PostgreSQL no está accesible en $HOST"
fi

# ── pg_dump completo ──
echo "  Generando $BACKUP_FILE ..."
PGPASSWORD=$PW pg_dump -h $HOST -U $USER -d $DB \
    --format=plain \
    --no-owner \
    --no-privileges \
    --file="$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    fail "El backup quedó vacío"
fi
ok "Backup generado ($(du -h "$BACKUP_FILE" | cut -f1))"

# ── Verificar que el backup contenga PostGIS ──
if grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$BACKUP_FILE"; then
    ok "PostGIS incluido en el backup"
else
    fail "El backup NO contiene PostGIS. Verifica la extensión en la BD."
fi

# ── Limpiar backups antiguos (solo backup_*.sql completos) ──
PURGE=$(ls -1t "$BACKUP_DIR"/backup_*.sql 2>/dev/null | tail -n +$((KEEP + 1)) || true)
if [ -n "$PURGE" ]; then
    echo "  Limpiando backups antiguos (conservando $KEEP)..."
    for OLD in $PURGE; do
        echo "    - $OLD"
        rm -f "$OLD"
    done
fi

echo ""
echo "================================================"
echo "  BACKUP COMPLETADO: $(basename "$BACKUP_FILE")"
echo "================================================"
