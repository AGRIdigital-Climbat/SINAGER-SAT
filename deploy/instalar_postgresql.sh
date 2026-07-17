#!/bin/bash
# ================================================================
#  EDAN - INSTALAR POSTGRESQL
#  Instala y configura PostgreSQL en Ubuntu / Zorin OS
#
#  Uso:  sudo bash instalar_postgresql.sh
#  Nota: Solo instala PostgreSQL, no crea la BD
#        Usa desplegar_bd.sh despues de instalar
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
echo "  EDAN - INSTALACION DE POSTGRESQL"
echo "  Compatible: Ubuntu 20.04+, Zorin OS 16+"
echo "================================================"
echo ""

# --------------------------------------------------
# Verificar root
# --------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    fail "Ejecuta como root: sudo bash instalar_postgresql.sh"
    exit 1
fi

# --------------------------------------------------
# [1/5] Actualizar repositorios
# --------------------------------------------------
echo "[1/5] Actualizando repositorios..."
apt-get update -qq
ok "Repositorios actualizados"

# --------------------------------------------------
# [2/5] Instalar PostgreSQL
# --------------------------------------------------
echo ""
echo "[2/5] Instalando PostgreSQL..."
if command -v psql &>/dev/null; then
    PG_VER_INST=$(psql --version | grep -oP '\d+' | head -1)
    ok "PostgreSQL v$PG_VER_INST ya instalado"
else
    apt-get install -y -qq postgresql postgresql-client
    ok "PostgreSQL instalado"
fi

# --------------------------------------------------
# [3/5] Iniciar servicio
# --------------------------------------------------
echo ""
echo "[3/5] Iniciando servicio..."
systemctl enable postgresql 2>/dev/null || true
systemctl start postgresql 2>/dev/null || true
sleep 2

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL corriendo"
else
    fail "PostgreSQL no pudo iniciarse"
    exit 1
fi

# --------------------------------------------------
# [4/5] Crear usuario
# --------------------------------------------------
echo ""
echo "[4/5] Creando usuario '$USER'..."
sudo -u postgres psql -c "CREATE ROLE $USER WITH SUPERUSER CREATEDB LOGIN PASSWORD '$PW';" 2>/dev/null && ok "Usuario '$USER' creado" || ok "Usuario '$USER' ya existe"

# --------------------------------------------------
# [5/5] Configurar acceso
# --------------------------------------------------
echo ""
echo "[5/5] Configurando acceso a la BD..."

PG_VER=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
PG_DIR="/etc/postgresql/$PG_VER/main"

if [ -n "$PG_DIR" ] && [ -d "$PG_DIR" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    # Buscar configs en deploy/config/ o config/
    CONF_DIR=""
    for CANDIDATO in "$SCRIPT_DIR/config" "$SCRIPT_DIR/../config"; do
        if [ -f "$CANDIDATO/postgresql.conf" ]; then
            CONF_DIR="$CANDIDATO"
            break
        fi
    done

    # Aplicar postgresql.conf
    if [ -n "$CONF_DIR" ] && [ -f "$CONF_DIR/postgresql.conf" ]; then
        cp "$CONF_DIR/postgresql.conf" "$PG_DIR/postgresql.conf"
        ok "postgresql.conf personalizada aplicada"
    else
        if grep -q "^#listen_addresses = 'localhost'" "$PG_DIR/postgresql.conf"; then
            sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_DIR/postgresql.conf"
        fi
        ok "listen_addresses = '*' configurado"
    fi

    # Aplicar pg_hba.conf
    if [ -n "$CONF_DIR" ] && [ -f "$CONF_DIR/pg_hba.conf" ]; then
        cp "$CONF_DIR/pg_hba.conf" "$PG_DIR/pg_hba.conf"
        ok "pg_hba.conf personalizada aplicada"
    else
        if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_DIR/pg_hba.conf" 2>/dev/null; then
            echo "" >> "$PG_DIR/pg_hba.conf"
            echo "# Conexiones remotas EDAN" >> "$PG_DIR/pg_hba.conf"
            echo "host    all    all    0.0.0.0/0    md5" >> "$PG_DIR/pg_hba.conf"
            echo "host    all    all    ::/0         md5" >> "$PG_DIR/pg_hba.conf"
        fi
        ok "Reglas de acceso remoto configuradas"
    fi

    # Reiniciar para aplicar cambios
    systemctl restart postgresql 2>/dev/null || true
    sleep 2
    ok "PostgreSQL reiniciado con nueva configuracion"
else
    warn "Directorio de configuracion no encontrado en /etc/postgresql/"
    warn "Configura listen_addresses manualmente"
fi

# --------------------------------------------------
# RESUMEN
# --------------------------------------------------
echo ""
echo "================================================"
echo "  INSTALACION COMPLETADA"
echo "================================================"
echo ""
echo "  PostgreSQL:  $(psql --version)"
echo "  Usuario:     $USER"
echo "  Password:    $PW"
echo "  Puerto:      5432"
echo ""
echo "  Siguiente paso:"
echo "    bash $(cd "$(dirname "$0")" && pwd)/desplegar_bd.sh"
echo ""
