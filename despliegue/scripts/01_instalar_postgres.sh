#!/bin/bash
# ================================================================
#  SINAGERSAT - 01 INSTALAR POSTGRESQL + POSTGIS + PGVECTOR
#  Instala PostgreSQL 16, PostGIS y pgvector en Ubuntu/Debian.
#  Uso: sudo bash despliegue/scripts/01_instalar_postgres.sh
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
AZUL="\033[0;34m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }
step() { echo -e "\n${AZUL}$1${SIN_COLOR}"; }

if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash despliegue/scripts/01_instalar_postgres.sh"
    exit 1
fi

echo ""
echo "================================================"
echo "  SINAGERSAT - INSTALACION DE POSTGRESQL"
echo "================================================"
echo ""

# [1] Actualizar repositorios
step "[1/6] Actualizando repositorios..."
apt-get update -qq
ok "Repositorios actualizados"

# [2] PostgreSQL
step "[2/6] Instalando PostgreSQL..."
if command -v psql &>/dev/null; then
    PG_VER_INSTALLED=$(psql --version | grep -oP '\d+' | head -1)
    ok "PostgreSQL ya instalado (v$PG_VER_INSTALLED)"
else
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-client
    ok "PostgreSQL instalado ($(psql --version))"
fi

# Detectar versión instalada
PG_VER=$(psql --version | grep -oP '\d+' | head -1)

# [3] PostGIS
step "[3/6] Instalando PostGIS..."
if dpkg -l 2>/dev/null | grep -q "postgresql-.*-postgis"; then
    ok "PostGIS ya instalado"
else
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "postgresql-$PG_VER-postgis-3" 2>/dev/null \
        || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgis 2>/dev/null \
        || warn "No se pudo instalar PostGIS desde repositorios"
    if dpkg -l 2>/dev/null | grep -q "postgresql-.*-postgis"; then
        ok "PostGIS instalado"
    else
        fail "PostGIS es OBLIGATORIO (geometrías de municipios)"
        exit 1
    fi
fi

# [4] pgvector
step "[4/6] Instalando pgvector (MotorIA embeddings)..."
if dpkg -l 2>/dev/null | grep -q "postgresql-$PG_VER-pgvector"; then
    ok "pgvector ya instalado"
else
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "postgresql-$PG_VER-pgvector" 2>/dev/null \
        || warn "No se pudo instalar pgvector — MotorIA requerirá instalación manual"
    if dpkg -l 2>/dev/null | grep -q "postgresql-$PG_VER-pgvector"; then
        ok "pgvector instalado"
    else
        warn "pgvector NO disponible — la extensión vector fallará en MotorIA"
    fi
fi

# [5] Python + build tools + ffmpeg
step "[5/6] Instalando Python, build tools y ffmpeg..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    build-essential libpq-dev gcc curl ffmpeg
ok "Python $(python3 --version | grep -oP '\d+\.\d+\.\d+'), build-essential, ffmpeg instalados"

# [6] Arrancar y configurar PostgreSQL
step "[6/6] Configurando PostgreSQL..."

systemctl enable postgresql 2>/dev/null || true
systemctl start postgresql 2>/dev/null || service postgresql start 2>/dev/null || true
sleep 2

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL corriendo"
else
    fail "PostgreSQL no pudo iniciarse"
    exit 1
fi

# Directorio de configuración
PG_CONF_DIR="/etc/postgresql/$PG_VER/main"

if [ -d "$PG_CONF_DIR" ]; then
    # listen_addresses
    if grep -q "^#listen_addresses = 'localhost'" "$PG_CONF_DIR/postgresql.conf" 2>/dev/null; then
        sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF_DIR/postgresql.conf"
        ok "listen_addresses = '*' configurado"
    elif ! grep -q "^listen_addresses" "$PG_CONF_DIR/postgresql.conf" 2>/dev/null; then
        echo "listen_addresses = '*'" >> "$PG_CONF_DIR/postgresql.conf"
        ok "listen_addresses agregado"
    else
        ok "listen_addresses ya configurado"
    fi

    # pg_hba.conf — conexiones remotas (solo si no existen)
    if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_CONF_DIR/pg_hba.conf" 2>/dev/null; then
        echo "" >> "$PG_CONF_DIR/pg_hba.conf"
        echo "# Conexiones remotas SINAGERSAT" >> "$PG_CONF_DIR/pg_hba.conf"
        echo "host    all    all    0.0.0.0/0    md5" >> "$PG_CONF_DIR/pg_hba.conf"
        echo "host    all    all    ::/0         md5" >> "$PG_CONF_DIR/pg_hba.conf"
        ok "Reglas de acceso remoto agregadas"
    else
        ok "Reglas de acceso ya configuradas"
    fi

    # Timezone Bolivia
    if ! grep -q "timezone = 'America/La_Paz'" "$PG_CONF_DIR/postgresql.conf" 2>/dev/null; then
        sed -i "s|^#*timezone = .*|timezone = 'America/La_Paz'|" "$PG_CONF_DIR/postgresql.conf" 2>/dev/null || true
        ok "Timezone America/La_Paz configurado"
    fi

    systemctl restart postgresql 2>/dev/null || service postgresql restart 2>/dev/null || true
    sleep 2
    ok "PostgreSQL reiniciado con nueva configuración"
else
    warn "Directorio de configuración no encontrado ($PG_CONF_DIR)"
fi

echo ""
echo "================================================"
echo -e "  ${VERDE}POSTGRESQL INSTALADO${SIN_COLOR}"
echo "================================================"
echo "  Versión:  $(psql --version)"
echo "  Siguiente: bash despliegue/scripts/02_restaurar_bd.sh"
echo ""
