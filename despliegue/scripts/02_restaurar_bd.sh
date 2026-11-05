#!/bin/bash
# ================================================================
#  SINAGERSAT - 02 RESTAURAR BASE DE DATOS
#  Crea usuario + BD y restaura el dump de despliegue/dump/
#  Uso: sudo bash despliegue/scripts/02_restaurar_bd.sh
# ================================================================
set -e

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
AZUL="\033[0;34m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }
step() { echo -e "\n${AZUL}$1${SIN_COLOR}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
DUMP_DIR="$DESPL_DIR/dump"

if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash despliegue/scripts/02_restaurar_bd.sh"
    exit 1
fi

echo ""
echo "================================================"
echo "  SINAGERSAT - RESTAURACION DE BASE DE DATOS"
echo "================================================"
echo ""

# [1] Verificar PostgreSQL
step "[1/6] Verificando PostgreSQL..."
if ! pg_isready -q 2>/dev/null; then
    fail "PostgreSQL no está corriendo"
    echo "  Ejecuta: sudo bash despliegue/scripts/01_instalar_postgres.sh"
    exit 1
fi
ok "PostgreSQL corriendo"

# [2] Encontrar dump más reciente
step "[2/6] Buscando dump de BD..."
BACKUP=$(ls -1t "$DUMP_DIR"/db_sinagersat_*.sql 2>/dev/null | head -1)
if [ -z "$BACKUP" ] || [ ! -s "$BACKUP" ]; then
    fail "No se encontró dump en $DUMP_DIR/"
    echo "  Esperado: db_sinagersat_YYYYMMDD_HHMMSS.sql"
    exit 1
fi
BACKUP_SIZE=$(du -h "$BACKUP" | cut -f1)
ok "Dump encontrado: $(basename "$BACKUP") ($BACKUP_SIZE)"

# Validar que incluye PostGIS
if grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$BACKUP" 2>/dev/null; then
    ok "Dump completo: incluye PostGIS"
else
    warn "El dump podría no incluir PostGIS — verificar"
fi

# [3] Crear usuario
step "[3/6] Creando usuario '$USER'..."
sudo -u postgres psql -c "CREATE ROLE $USER WITH SUPERUSER CREATEDB LOGIN PASSWORD '$PW';" 2>/dev/null \
    && ok "Usuario '$USER' creado" \
    || ok "Usuario '$USER' ya existe"

# [4] Eliminar y crear BD
step "[4/6] Preparando base de datos '$DB'..."
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" 2>/dev/null || true
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null
ok "Base de datos anterior eliminada (si existía)"

sudo -u postgres psql -c "CREATE DATABASE $DB OWNER $USER;" 2>/dev/null
ok "Base de datos '$DB' creada"

# [5] Restaurar dump
step "[5/6] Restaurando dump (puede tardar varios minutos)..."
BACKUP_TMP="/tmp/sinagersat_restore.sql"
cp "$BACKUP" "$BACKUP_TMP"
chmod 644 "$BACKUP_TMP"

sudo -u postgres psql -d "$DB" -f "$BACKUP_TMP" >/dev/null 2>&1 \
    && ok "Dump restaurado exitosamente" \
    || { fail "Error al restaurar el dump"; exit 1; }

rm -f "$BACKUP_TMP"

# Conceder permisos en todos los esquemas
echo "  Concediendo permisos en todos los esquemas..."
SCHEMAS=$(sudo -u postgres psql -d "$DB" -t -A -c "
    SELECT schema_name FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog','information_schema')
" 2>/dev/null)

for SCHEMA in $SCHEMAS; do
    sudo -u postgres psql -d "$DB" -c "GRANT ALL ON SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB" -c "GRANT ALL ON ALL TABLES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    sudo -u postgres psql -d "$DB" -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
done
ok "Permisos concedidos en todos los esquemas"

# [6] Verificación
step "[6/6] Verificando contenido..."
echo ""
PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -c "
SELECT
    (SELECT COUNT(*) FROM shared.departamento) AS deptos,
    (SELECT COUNT(*) FROM shared.provincia) AS provs,
    (SELECT COUNT(*) FROM shared.municipio) AS munis,
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_schema NOT IN ('pg_catalog','information_schema')) AS tablas
" 2>/dev/null || warn "Verificación de conteos falló"

echo ""
echo "  Esquemas:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -t -A -c "
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_temp','pg_toast')
ORDER BY schema_name;
" 2>/dev/null | while read -r s; do echo "    - $s"; done

echo ""
echo "  Extensiones:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U "$USER" -d "$DB" -t -A -c "
SELECT extname || ' ' || extversion FROM pg_extension
WHERE extname IN ('postgis','vector') ORDER BY extname;
" 2>/dev/null | while read -r e; do echo "    - $e"; done

echo ""
echo "================================================"
echo -e "  ${VERDE}BASE DE DATOS RESTAURADA${SIN_COLOR}"
echo "================================================"
echo "  Base:     $DB"
echo "  Usuario:  $USER"
echo "  Password: $PW"
echo "  Host:     127.0.0.1:5432"
echo ""
echo "  Conexion:"
echo "    PGPASSWORD=$PW psql -U $USER -d $DB -h 127.0.0.1"
echo ""
echo "  Siguiente: bash despliegue/scripts/03_instalar_api.sh"
echo ""
