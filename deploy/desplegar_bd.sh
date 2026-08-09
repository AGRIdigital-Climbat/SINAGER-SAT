#!/bin/bash
# ================================================================
#  EDAN - DESPLEGAR BASE DE DATOS
#  Restaura la BD desde el backup completo y ejecuta migraciones
#
#  Uso:  bash desplegar_bd.sh
#  Requiere: PostgreSQL instalado y corriendo
# ================================================================
set -e

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

echo ""
echo "================================================"
echo "  EDAN - DESPLEGUE DE BASE DE DATOS"
echo "================================================"
echo ""

# --------------------------------------------------
# Verificar PostgreSQL
# --------------------------------------------------
if ! pg_isready -q 2>/dev/null; then
    fail "PostgreSQL no esta corriendo"
    echo "  Ejecuta primero: sudo bash instalar_postgresql.sh"
    echo "  O:               sudo bash setup.sh (desde la raiz del proyecto)"
    exit 1
fi
ok "PostgreSQL corriendo"

# --------------------------------------------------
# Buscar el backup MÁS RECIENTE (backup_*.sql de tamaño completo)
# Los dumps parciales (crear_edan_db.sql, edan_db_backup.sql, backup_pre_*.sql)
# se ignoran para no perder datos.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATABASE_DIR="$SCRIPT_DIR/../database"

BACKUP=""
for CANDIDATO in $(ls -1t "$DATABASE_DIR"/backup_*.sql 2>/dev/null); do
    case "$(basename "$CANDIDATO")" in
        backup_pre_*.sql) continue ;;  # dump parcial, no usar como base
    esac
    if [ -s "$CANDIDATO" ]; then
        BACKUP="$CANDIDATO"
        break
    fi
done

if [ -z "$BACKUP" ]; then
    fail "No se encuentra archivo de backup en $DATABASE_DIR"
    echo "  Esperado: database/backup_*.sql (p. ej. backup_v1.5.0.sql)"
    exit 1
fi
ok "Backup encontrado: $BACKUP ($(du -h "$BACKUP" | cut -f1))"

# Validar que el backup sea COMPLETO (contenga PostGIS)
if grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$BACKUP"; then
    ok "Backup completo: incluye PostGIS"
else
    warn "El backup NO incluye PostGIS (puede ser un dump parcial o muy antiguo)."
    warn "La geometría (geom) de shared.municipio se restaurará con database/restaurar_geom.sh."
fi

# Copiar backup a /tmp para evitar problemas de permisos en medios externos
BACKUP_TMP="/tmp/edan_db_backup.sql"
if [ "$BACKUP" != "$BACKUP_TMP" ]; then
    cp "$BACKUP" "$BACKUP_TMP" 2>/dev/null
    ok "Backup copiado a /tmp para evitar problemas de permisos"
fi
BACKUP="$BACKUP_TMP"

# --------------------------------------------------
# [1/5] Crear/verificar usuario
# --------------------------------------------------
echo ""
echo "[1/5] Verificando usuario '$USER'..."
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d postgres -c "SELECT 1;" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "  Creando usuario '$USER'..."
    sudo -u postgres psql -c "CREATE ROLE $USER WITH SUPERUSER CREATEDB LOGIN PASSWORD '$PW';" 2>/dev/null && ok "Usuario creado" || ok "Usuario ya existe"
else
    ok "Usuario verificado"
fi

# --------------------------------------------------
# [2/5] Eliminar BD anterior
# --------------------------------------------------
echo ""
echo "[2/5] Eliminando base de datos anterior (si existe)..."
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" 2>/dev/null || true
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null
ok "Base de datos anterior eliminada"

# --------------------------------------------------
# [3/5] Crear BD
# --------------------------------------------------
echo ""
echo "[3/5] Creando base de datos '$DB'..."
sudo -u postgres psql -c "CREATE DATABASE $DB OWNER $USER;" 2>/dev/null
ok "Base de datos creada"

# --------------------------------------------------
# [4/5] Restaurar backup
# --------------------------------------------------
echo ""
echo "[4/5] Restaurando desde backup..."
sudo -u postgres psql -d $DB -f "$BACKUP" 2>/dev/null
ok "Backup restaurado ($(wc -l < "$BACKUP") lineas)"

# --------------------------------------------------
# [5/5] Conceder permisos en TODOS los schemas
# --------------------------------------------------
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
    ok "Permisos concedidos en schema '$SCHEMA'"
done

# --------------------------------------------------
# [6/6] Ejecutar migraciones (todas en orden)
# --------------------------------------------------
echo ""
echo "[6/6] Ejecutando migraciones..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MIGRATIONS_DIR="$PROJECT_DIR/database"

# Todas las migraciones en orden numérico de versión.
# Los backups (backup_*.sql) y dumps (crear_edan_db.sql, etc.) NO son migraciones.
for MIGRATION in $(ls -1v "$MIGRATIONS_DIR"/migration_*.sql 2>/dev/null); do
    NAME="$(basename "$MIGRATION")"
    echo "  Ejecutando migración $NAME ..."
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION" 2>/dev/null \
        && ok "Migración $NAME ejecutada" \
        || warn "Migración $NAME falló (revisar)."
done

ok "Migraciones completadas"

# --------------------------------------------------
# RESUMEN
# --------------------------------------------------
echo ""
echo "================================================"
echo "  DESPLEGUE COMPLETADO"
echo "================================================"
echo ""
echo "  Base de datos: $DB"
echo "  Usuario:       $USER"
echo "  Password:      $PW"
echo "  Host:          10.10.10.220"
echo "  Puerto:        5432"
echo ""
echo "  Conexion:"
echo "    PGPASSWORD=$PW psql -U $USER -d $DB -h 10.10.10.220"
echo ""
echo "  Verificar:"
echo "    bash $(dirname "$0")/verificar.sh"
echo ""
echo "  pgAdmin4: File > Import > database/servers.json"
echo "  DBeaver:  Host: 10.10.10.220 | DB: $DB | User: $USER"
echo ""
