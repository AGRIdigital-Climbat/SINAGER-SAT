#!/bin/bash
# ================================================================
#  SINAGERSAT - GENERAR DUMP FRESCO DE BD
#  Crea un dump nuevo de db_sinagersat en despliegue/dump/
#  (para actualizar el paquete de despliegue cuando hay cambios).
#
#  Uso: bash despliegue/scripts/generar_dump.sh
# ================================================================
set -e

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
DUMP_DIR="$DESPL_DIR/dump"

echo ""
echo "================================================"
echo "  SINAGERSAT - GENERAR DUMP DE BD"
echo "================================================"
echo ""

# Verificar conexión
if ! PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -c "SELECT 1;" >/dev/null 2>&1; then
    fail "No se pudo conectar a $DB"
    echo "  Verifica que PostgreSQL esté corriendo y la BD exista."
    exit 1
fi
ok "Conexión a $DB exitosa"

# Crear directorio
mkdir -p "$DUMP_DIR"

# Generar dump
TS=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="$DUMP_DIR/db_sinagersat_${TS}.sql"

echo "  Generando dump (puede tardar)..."
if PGPASSWORD=$PW pg_dump -h 127.0.0.1 -U "$USER" -d "$DB" \
    --no-owner --no-privileges -f "$DUMP_FILE"; then
    DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    ok "Dump generado: $(basename "$DUMP_FILE") ($DUMP_SIZE)"
else
    fail "Error al generar el dump"
    exit 1
fi

# Validar contenido
echo ""
echo "  Validando contenido..."
if grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$DUMP_FILE"; then
    ok "Incluye PostGIS"
else
    fail "NO incluye PostGIS — dump incompleto"
fi

SCHEMAS=$(grep -oP "CREATE SCHEMA \K\w+" "$DUMP_FILE" | sort -u | tr '\n' ' ')
ok "Esquemas: $SCHEMAS"

# Listar dumps anteriores
echo ""
echo "  Dumps disponibles en despliegue/dump/:"
ls -lht "$DUMP_DIR"/*.sql 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}'

# Limpiar dumps antiguos (conservar solo los últimos 3)
DUMP_COUNT=$(ls -1t "$DUMP_DIR"/*.sql 2>/dev/null | wc -l)
if [ "$DUMP_COUNT" -gt 3 ]; then
    echo ""
    echo "  Limpiando dumps antiguos (conservando últimos 3)..."
    ls -1t "$DUMP_DIR"/*.sql | tail -n +4 | while read -r f; do
        rm -f "$f"
        echo "    eliminado: $(basename "$f")"
    done
fi

echo ""
echo "================================================"
echo -e "  ${VERDE}DUMP GENERADO${SIN_COLOR}"
echo "================================================"
echo "  Archivo: $DUMP_FILE"
echo ""
echo "  Para regenerar migraciones copiadas:"
echo "    ls -1v database/migration_v*.sql database/migrations/*.sql | while read f; do cp \"\$f\" despliegue/migraciones/; done"
echo ""
