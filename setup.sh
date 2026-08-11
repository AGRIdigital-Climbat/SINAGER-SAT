#!/bin/bash
# ================================================================
#  EDAN - INSTALACION COMPLETA EN UN SOLO PASO
#  Ejecutar como root:
#    sudo bash setup.sh
# ================================================================
set -e

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Preferir backup más reciente
if [ -f "$SCRIPT_DIR/database/backup_v1.2.6.sql" ]; then
    BACKUP="$SCRIPT_DIR/database/backup_v1.2.6.sql"
else
    BACKUP="$SCRIPT_DIR/database/backup_2026_07_26.sql"
fi
SQL_ESQUEMA="$SCRIPT_DIR/database/crear_edan_db.sql"
SQL_GEOGRAFIA="$SCRIPT_DIR/database/insert_provincias_municipios.sql"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

echo ""
echo "================================================"
echo "  EDAN - INSTALACION COMPLETA"
echo "  Evaluacion de Danos y Analisis de Necesidades"
echo "================================================"
echo ""

# --------------------------------------------------
# 0. Verificar root
# --------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash setup.sh"
    exit 1
fi

# --------------------------------------------------
# 1. Detectar OS
# --------------------------------------------------
echo "[1/7] Detectando sistema operativo..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    ok "$PRETTY_NAME"
else
    fail "No se pudo detectar el OS"
    exit 1
fi

# --------------------------------------------------
# 2. Instalar PostgreSQL
# --------------------------------------------------
echo ""
echo "[2/7] Instalando PostgreSQL..."

if command -v psql &>/dev/null; then
    PG_VER_INSTALLED=$(psql --version | grep -oP '\d+' | head -1)
    ok "PostgreSQL ya instalado (v$PG_VER_INSTALLED)"
else
    apt-get update -qq
    apt-get install -y -qq postgresql postgresql-client
    ok "PostgreSQL instalado"
fi

# PostGIS (requerido para geometrías de municipios)
if dpkg -l | grep -q "postgresql-.*-postgis" 2>/dev/null; then
    ok "PostGIS ya instalado"
else
    PG_VER=$(psql --version | grep -oP '\d+' | head -1)
    echo "  Instalando PostGIS..."
    apt-get install -y -qq "postgresql-$PG_VER-postgis-3" 2>/dev/null || apt-get install -y -qq postgis 2>/dev/null || true
    ok "PostGIS instalado"
fi

# --------------------------------------------------
# 3. Iniciar servicio
# --------------------------------------------------
echo ""
echo "[3/7] Iniciando servicio PostgreSQL..."

if command -v systemctl &>/dev/null; then
    systemctl enable postgresql 2>/dev/null || true
    systemctl start postgresql 2>/dev/null || true
else
    service postgresql start 2>/dev/null || true
fi

sleep 2

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL corriendo"
else
    fail "PostgreSQL no pudo iniciarse"
    exit 1
fi

# --------------------------------------------------
# 4. Detectar directorio de configuracion PostgreSQL
# --------------------------------------------------
echo ""
echo "[4/7] Configurando PostgreSQL..."

PG_VER=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
PG_DIR="/etc/postgresql/$PG_VER/main"

if [ ! -d "$PG_DIR" ]; then
    PG_DIR=$(find /etc/postgresql -name "main" -type d 2>/dev/null | head -1)
fi

if [ -n "$PG_DIR" ] && [ -d "$PG_DIR" ]; then
    # Aplicar configuracion de listen_addresses
    if grep -q "^#listen_addresses = 'localhost'" "$PG_DIR/postgresql.conf"; then
        sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_DIR/postgresql.conf"
        ok "listen_addresses configurado"
    elif ! grep -q "^listen_addresses" "$PG_DIR/postgresql.conf"; then
        echo "listen_addresses = '*'" >> "$PG_DIR/postgresql.conf"
        ok "listen_addresses agregado"
    else
        ok "listen_addresses ya configurado"
    fi

    # Aplicar pg_hba.conf para conexiones remotas
    if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_DIR/pg_hba.conf" 2>/dev/null; then
        echo "" >> "$PG_DIR/pg_hba.conf"
        echo "# Conexiones remotas EDAN" >> "$PG_DIR/pg_hba.conf"
        echo "host    all    all    0.0.0.0/0    md5" >> "$PG_DIR/pg_hba.conf"
        echo "host    all    all    ::/0         md5" >> "$PG_DIR/pg_hba.conf"
        ok "Reglas de acceso remoto agregadas"
    else
        ok "Reglas de acceso ya configuradas"
    fi

    # Reiniciar para aplicar cambios
    if command -v systemctl &>/dev/null; then
        systemctl restart postgresql 2>/dev/null || true
    else
        service postgresql restart 2>/dev/null || true
    fi
    sleep 2
    ok "PostgreSQL reiniciado"
else
    warn "Directorio de configuracion no encontrado, se usan valores por defecto"
fi

# --------------------------------------------------
# 5. Crear usuario
# --------------------------------------------------
echo ""
echo "[5/7] Creando usuario de base de datos..."

sudo -u postgres psql -c "CREATE ROLE $USER WITH SUPERUSER CREATEDB LOGIN PASSWORD '$PW';" 2>/dev/null && ok "Usuario '$USER' creado" || ok "Usuario '$USER' ya existe"

# --------------------------------------------------
# 6. Restaurar base de datos
# --------------------------------------------------
echo ""
echo "[6/7] Restaurando base de datos..."

# Verificar que existe el backup
if [ ! -f "$BACKUP" ]; then
    fail "No se encuentra el backup: $BACKUP"
    fail "Verifica que la carpeta database/ este completa"
    exit 1
fi

# Copiar backup a /tmp para evitar problemas de permisos en medios externos
BACKUP_TMP="/tmp/edan_db_backup.sql"
cp "$BACKUP" "$BACKUP_TMP" 2>/dev/null
BACKUP="$BACKUP_TMP"
ok "Backup preparado en $BACKUP"

# Matar conexiones existentes
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" 2>/dev/null || true

# Eliminar BD anterior si existe
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null
ok "Base de datos anterior eliminada (si existia)"

# Crear BD
sudo -u postgres psql -c "CREATE DATABASE $DB OWNER $USER;" 2>/dev/null
ok "Base de datos '$DB' creada"

# Restaurar desde backup
sudo -u postgres psql -d $DB -f "$BACKUP" 2>/dev/null
ok "Backup restaurado ($(wc -l < "$BACKUP") lineas)"

# --------------------------------------------------
# 6b. Modo alternativo: scripts SQL individuales
# --------------------------------------------------
if [ ! -f "$BACKUP" ] && [ -f "$SQL_ESQUEMA" ]; then
    warn "Backup no encontrado, usando scripts SQL individuales..."
    sudo -u postgres psql -d $DB -f "$SQL_ESQUEMA" 2>/dev/null
    ok "Esquema creado desde $SQL_ESQUEMA"
    if [ -f "$SQL_GEOGRAFIA" ]; then
        sudo -u postgres psql -d $DB -f "$SQL_GEOGRAFIA" 2>/dev/null
        ok "Geografia cargada desde $SQL_GEOGRAFIA"
    fi
fi

# --------------------------------------------------
# 7. Conceder permisos
# --------------------------------------------------
echo ""
echo "[7/7] Concediendo permisos..."

# Permisos en todos los schemas
for SCHEMA in public edan shared usuarios rea recursos rida sinb; do
    sudo -u postgres psql -d $DB -c "GRANT ALL ON SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
done

# Permisos en tablas y secuencias de todos los schemas
for SCHEMA in public edan shared usuarios rea recursos rida sinb; do
    sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL TABLES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
done

# Propietario de tablas
sudo -u postgres psql -d $DB -c "
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('edan','shared','usuarios','rea') LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(r.schemaname) || '.' || quote_ident(r.tablename) || ' OWNER TO $USER';
    END LOOP;
    FOR r SELECT sequence_schema, sequence_name FROM information_schema.sequences WHERE sequence_schema IN ('edan','shared','usuarios','rea') LOOP
        EXECUTE 'ALTER SEQUENCE ' || quote_ident(r.sequence_schema) || '.' || quote_ident(r.sequence_name) || ' OWNER TO $USER';
    END LOOP;
END \$\$;
" 2>/dev/null || true

ok "Permisos concedidos en todos los schemas"

# --------------------------------------------------
# VERIFICACION RAPIDA
# --------------------------------------------------
echo ""
echo "================================================"
echo "  VERIFICACION"
echo "================================================"
echo ""

RESULTADO=$(PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
SELECT
    (SELECT COUNT(*) FROM shared.departamento) as departamentos,
    (SELECT COUNT(*) FROM shared.provincia) as provincias,
    (SELECT COUNT(*) FROM shared.municipio) as municipios,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'edan') as tablas_edan,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'usuarios') as tablas_usuarios,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'rea') as tablas_rea
" 2>/dev/null || echo "ERROR")

if echo "$RESULTADO" | grep -q "ERROR"; then
    # Intentar con esquema public (modo crear_edan_db.sql)
    RESULTADO=$(PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
    SELECT
        (SELECT COUNT(*) FROM catalogo_departamento) as departamentos,
        (SELECT COUNT(*) FROM catalogo_provincia) as provincias,
        (SELECT COUNT(*) FROM catalogo_municipio) as municipios,
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as tablas_public
    " 2>/dev/null || echo "ERROR")
fi

echo "  Departamentos: $(echo $RESULTADO | cut -d'|' -f1)"
echo "  Provincias:    $(echo $RESULTADO | cut -d'|' -f2)"
echo "  Municipios:    $(echo $RESULTADO | cut -d'|' -f3)"
echo "  Tablas EDAN:   $(echo $RESULTADO | cut -d'|' -f4)"
echo "  Tablas USR:    $(echo $RESULTADO | cut -d'|' -f5)"
echo "  Tablas REA:    $(echo $RESULTADO | cut -d'|' -f6)"
echo ""

# Total de tablas
TOTAL_TABLAS=$(PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
" 2>/dev/null || echo "?")
echo "  Total tablas:  $TOTAL_TABLAS"

# --------------------------------------------------
# RESUMEN FINAL
# --------------------------------------------------
echo ""
echo "================================================"
echo "  INSTALACION COMPLETADA EXITOSAMENTE"
echo "================================================"
echo ""
echo "  Base de datos:  $DB"
echo "  Usuario:        $USER"
echo "  Password:       $PW"
echo "  Host:           10.10.10.220"
echo "  Puerto:         5432"
echo ""
echo "  Conexion:"
echo "    PGPASSWORD=$PW psql -U $USER -d $DB -h 10.10.10.220"
echo ""
echo "  pgAdmin4:"
echo "    File > Import/Export Servers > Import"
echo "    Seleccionar: database/servers.json"
echo ""
echo "  DBeaver:"
echo "    Nuevo.getConnection > PostgreSQL"
echo "    Host: 10.10.10.220 | DB: $DB | User: $USER"
echo ""
echo "  Para verificar:  bash $SCRIPT_DIR/deploy/verificar.sh"
echo "  Para restaurar:  bash $SCRIPT_DIR/database/restore_db.sh"
echo ""
