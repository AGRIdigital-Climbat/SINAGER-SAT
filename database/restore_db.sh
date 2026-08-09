#!/bin/bash
# ================================================================
#  EDAN - RESTAURAR BASE DE DATOS DESDE BACKUP
#  Elimina la BD actual y restaura desde edan_db_backup.sql
#
#  Uso:  bash restore_db.sh
#  Nota: Todos los datos NO guardados se perderan
# ================================================================
set -e

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

# Buscar el backup MÁS RECIENTE (backup_*.sql de tamaño completo)
# Los dumps parciales (crear_edan_db.sql, edan_db_backup.sql, backup_pre_*.sql)
# se ignoran para no perder datos.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKUP=""
for CANDIDATO in $(ls -1t "$SCRIPT_DIR"/backup_*.sql 2>/dev/null); do
    case "$(basename "$CANDIDATO")" in
        backup_pre_*.sql) continue ;;  # dump parcial, no usar como base
    esac
    if [ -s "$CANDIDATO" ]; then
        BACKUP="$CANDIDATO"
        break
    fi
done

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

echo ""
echo "================================================"
echo "  EDAN - RESTAURAR BASE DE DATOS"
echo "================================================"
echo ""

# Verificar backup
if [ ! -f "$BACKUP" ]; then
    fail "No se encuentra: $BACKUP"
    exit 1
fi
ok "Backup encontrado: $(du -h "$BACKUP" | cut -f1)"

# Validar que el backup sea COMPLETO (contenga PostGIS/geom si aplica)
if ! grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$BACKUP"; then
    warn "El backup NO contiene PostGIS. Si es un dump parcial (ej. backup_pre_*.sql)"
    warn "o muy antiguo, la geometría (geom) de shared.municipio no se restaurará."
    warn "Usa database/restaurar_geom.sh con un backup que sí lo incluya."
fi

# Copiar a /tmp para evitar problemas de permisos en medios externos
BACKUP_TMP="/tmp/edan_db_backup.sql"
cp "$BACKUP" "$BACKUP_TMP" 2>/dev/null
BACKUP="$BACKUP_TMP"
ok "Backup preparado en $BACKUP"

# Verificar PostgreSQL
if ! pg_isready -q 2>/dev/null; then
    fail "PostgreSQL no esta corriendo"
    echo "  Ejecuta: sudo service postgresql start"
    exit 1
fi
ok "PostgreSQL corriendo"

# Terminar conexiones
echo ""
echo "[1/5] Terminando conexiones activas..."
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" 2>/dev/null || true
ok "Conexiones terminadas"

# Eliminar BD
echo ""
echo "[2/5] Eliminando base de datos '$DB'..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null
ok "Base de datos eliminada"

# Crear BD
echo ""
echo "[3/5] Creando base de datos '$DB'..."
sudo -u postgres psql -c "CREATE DATABASE $DB OWNER $USER;" 2>/dev/null
ok "Base de datos creada"

# Restaurar
echo ""
echo "[4/5] Restaurando desde backup..."
sudo -u postgres psql -d $DB -f "$BACKUP" 2>/dev/null
ok "Backup restaurado ($(wc -l < "$BACKUP") lineas)"

# Permisos
echo ""
echo "[5/5] Concediendo permisos..."
SCHEMAS=$(sudo -u postgres psql -d $DB -t -A -c "
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema')
" 2>/dev/null)

for SCHEMA in $SCHEMAS; do
    sudo -u postgres psql -d $DB -c "GRANT ALL ON SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL TABLES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
done
ok "Permisos concedidos"

# Verificar
echo ""
echo "================================================"
echo "  RESTAURACION COMPLETADA"
echo "================================================"
echo ""
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT table_schema, COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
GROUP BY table_schema ORDER BY table_schema;
" 2>/dev/null
echo ""
echo "  Conexion:"
echo "    PGPASSWORD=$PW psql -U $USER -d $DB -h 10.10.10.220"
echo ""
