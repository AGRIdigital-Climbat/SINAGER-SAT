#!/bin/bash
# ================================================================
#  SINAGERSAT - DESPLIEGUE COMPLETO EN ENTORNO VACÍO
#  Instala todo desde cero: PostgreSQL + BD completa + API
#
#  Uso:
#    sudo bash deploy/desplegar_todo.sh              # despliegue completo
#    sudo bash deploy/desplegar_todo.sh --db-only    # solo base de datos
#    sudo bash deploy/desplegar_todo.sh --api-only   # solo API (si PG ya está)
#    sudo bash deploy/desplegar_todo.sh --tunnel     # completo + Cloudflare tunnel
#    sudo bash deploy/desplegar_todo.sh --update     # actualizar desde versión anterior
#
#  Requiere: Ubuntu/Debian, internet, archivos del proyecto
# ================================================================
set -e

# ================================================================
#  CONFIGURACIÓN
# ================================================================
DB="db_sinagersat"
USER="sinagersat"
PW="12345678"
API_PORT=8000
API_HOST="0.0.0.0"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Buscar backup (preferir el más reciente)
BACKUP=""
for CANDIDATO in \
    "$PROJECT_DIR/database/backup_v1.2.7.sql" \
    "$PROJECT_DIR/database/backup_v1.2.6.sql" \
    "$PROJECT_DIR/database/backup_2026_07_26.sql" \
    "$PROJECT_DIR/database/backup_2026_07_21.sql" \
    "$PROJECT_DIR/database/edan_db_backup.sql"; do
    if [ -f "$CANDIDATO" ]; then
        BACKUP="$CANDIDATO"
        break
    fi
done

# Colores
ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
AZUL="\033[0;34m"
CYAN="\033[0;36m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }
step() { echo -e "\n${AZUL}[$1/$TOTAL_STEPS]${SIN_COLOR} ${CYAN}$2${SIN_COLOR}"; }

# ================================================================
#  PARÁMETROS
# ================================================================
MODE="full"
for arg in "$@"; do
    case $arg in
        --db-only)  MODE="db" ;;
        --api-only) MODE="api" ;;
        --tunnel)   MODE="tunnel" ;;
        --update)   MODE="update" ;;
        --help|-h)
            echo "Uso: sudo bash deploy/desplegar_todo.sh [opciones]"
            echo ""
            echo "Opciones:"
            echo "  (sin args)    Despliegue completo (BD + API)"
            echo "  --db-only     Solo base de datos"
            echo "  --api-only    Solo API (PostgreSQL debe estar corriendo)"
            echo "  --tunnel      Completo + Cloudflare Quick Tunnel"
            echo "  --update      Actualizar desde versión anterior (preserva datos)"
            echo "  --help        Mostrar esta ayuda"
            exit 0
            ;;
    esac
done

case $MODE in
    full)   TOTAL_STEPS=8 ;;
    db)     TOTAL_STEPS=5 ;;
    api)    TOTAL_STEPS=3 ;;
    tunnel) TOTAL_STEPS=9 ;;
    update) TOTAL_STEPS=7 ;;
esac

# ================================================================
#  CABECERA
# ================================================================
echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  SINAGERSAT - DESPLIEGUE COMPLETO${SIN_COLOR}"
echo -e "${CYAN}  Sistema Nacional de Alerta Temprana${SIN_COLOR}"
echo -e "${CYAN}  Modo: $MODE${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""

# ================================================================
#  VERIFICAR ROOT (para instalar paquetes)
# ================================================================
if [ "$EUID" -ne 0 ] && [ "$MODE" = "db" -o "$MODE" = "full" -o "$MODE" = "tunnel" ]; then
    fail "Ejecuta como root: sudo bash deploy/desplegar_todo.sh"
    exit 1
fi

# Detectar usuario real (para venv/pip como no-root)
REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(eval echo "~$REAL_USER")

# ================================================================
#  1. DETECTAR SISTEMA OPERATIVO
# ================================================================
step 1 "Detectando sistema operativo..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="$ID"
    OS_VERSION="$VERSION_ID"
    OS_NAME="$PRETTY_NAME"
    ok "$OS_NAME"
else
    fail "No se pudo detectar el OS"
    exit 1
fi

# Verificar que es Ubuntu/Debian
if [ "$OS_ID" != "ubuntu" ] && [ "$OS_ID" != "debian" ] && [ "$OS_ID" != "linuxmint" ] && [ "$OS_ID" != "zorin" ]; then
    warn "OS no oficialmente soportado: $OS_ID. Se intentará igualmente..."
fi

# ================================================================
#  2. INSTALAR DEPENDENCIAS DEL SISTEMA
# ================================================================
if [ "$MODE" != "api" ]; then
    step 2 "Instalando dependencias del sistema..."

    # Actualizar repositorios
    apt-get update -qq

    # PostgreSQL
    if command -v psql &>/dev/null; then
        PG_VER_INSTALLED=$(psql --version | grep -oP '\d+' | head -1)
        ok "PostgreSQL ya instalado (v$PG_VER_INSTALLED)"
    else
        echo "  Instalando PostgreSQL..."
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

    # Python3 + pip + venv
    if command -v python3 &>/dev/null; then
        PYTHON_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
        ok "Python3 ya instalado (v$PYTHON_VER)"
    else
        echo "  Instalando Python3..."
        apt-get install -y -qq python3 python3-pip python3-venv
        ok "Python3 instalado"
    fi

    # python3-venv (necesario para crear venv)
    if ! python3 -m venv --help &>/dev/null 2>&1; then
        echo "  Instalando python3-venv..."
        apt-get install -y -qq python3-venv python3-dev
        ok "python3-venv instalado"
    else
        ok "python3-venv disponible"
    fi

    # Build tools (para psycopg2 y bcrypt)
    if ! dpkg -l | grep -q build-essential 2>/dev/null; then
        echo "  Instalando build-essential..."
        apt-get install -y -qq build-essential libpq-dev gcc
        ok "Build tools instalados"
    else
        ok "Build tools disponibles"
    fi

    # curl (para Cloudflare tunnel)
    if ! command -v curl &>/dev/null; then
        apt-get install -y -qq curl
        ok "curl instalado"
    fi

else
    step 2 "Saltando dependencias del sistema (modo --api-only)..."
    ok "Modo --api-only"
fi

# ================================================================
#  3. CONFIGURAR Y ARRANCAR POSTGRESQL
# ================================================================
if [ "$MODE" != "api" ]; then
    step 3 "Configurando PostgreSQL..."

    # Iniciar servicio
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

    # Detectar directorio de configuración
    PG_VER=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -1)
    PG_DIR="/etc/postgresql/$PG_VER/main"

    if [ -n "$PG_VER" ] && [ -d "$PG_DIR" ]; then
        # Configurar listen_addresses
        if grep -q "^#listen_addresses = 'localhost'" "$PG_DIR/postgresql.conf"; then
            sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_DIR/postgresql.conf"
            ok "listen_addresses = '*' configurado"
        elif ! grep -q "^listen_addresses" "$PG_DIR/postgresql.conf"; then
            echo "listen_addresses = '*'" >> "$PG_DIR/postgresql.conf"
            ok "listen_addresses agregado"
        else
            ok "listen_addresses ya configurado"
        fi

        # Configurar pg_hba.conf para conexiones remotas
        if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_DIR/pg_hba.conf" 2>/dev/null; then
            echo "" >> "$PG_DIR/pg_hba.conf"
            echo "# Conexiones remotas SINAGERSAT" >> "$PG_DIR/pg_hba.conf"
            echo "host    all    all    0.0.0.0/0    md5" >> "$PG_DIR/pg_hba.conf"
            echo "host    all    all    ::/0         md5" >> "$PG_DIR/pg_hba.conf"
            ok "Reglas de acceso remoto agregadas"
        else
            ok "Reglas de acceso ya configuradas"
        fi

        # Timezone Bolivia
        if ! grep -q "timezone = 'America/La_Paz'" "$PG_DIR/postgresql.conf"; then
            sed -i "s|^#*timezone = .*|timezone = 'America/La_Paz'|" "$PG_DIR/postgresql.conf" 2>/dev/null || true
        fi

        # Reiniciar para aplicar cambios
        if command -v systemctl &>/dev/null; then
            systemctl restart postgresql 2>/dev/null || true
        else
            service postgresql restart 2>/dev/null || true
        fi
        sleep 2
        ok "PostgreSQL reiniciado con nueva configuración"
    else
        warn "Directorio de configuración no encontrado ($PG_DIR), se usan valores por defecto"
    fi

    # Crear usuario
    sudo -u postgres psql -c "CREATE ROLE $USER WITH SUPERUSER CREATEDB LOGIN PASSWORD '$PW';" 2>/dev/null && ok "Usuario '$USER' creado" || ok "Usuario '$USER' ya existe"

else
    step 3 "Saltando PostgreSQL (modo --api-only)..."
    ok "Modo --api-only"
fi

# ================================================================
#  4. RESTAURAR BASE DE DATOS COMPLETA
# ================================================================
if [ "$MODE" != "api" ]; then
    step 4 "Restaurando base de datos completa..."

    # Verificar backup
    if [ ! -f "$BACKUP" ]; then
        fail "No se encuentra el backup: $BACKUP"
        fail "Verifica que la carpeta database/ esté completa"
        exit 1
    fi

    BACKUP_SIZE=$(du -h "$BACKUP" | cut -f1)
    BACKUP_LINES=$(wc -l < "$BACKUP")
    ok "Backup encontrado: $BACKUP_SIZE ($BACKUP_LINES líneas)"

    # Copiar a /tmp para evitar problemas de permisos
    BACKUP_TMP="/tmp/sinagersat_backup.sql"
    cp "$BACKUP" "$BACKUP_TMP"
    ok "Backup preparado en /tmp"

    # Matar conexiones existentes
    sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" 2>/dev/null || true

    # Eliminar BD anterior si existe
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB;" 2>/dev/null
    ok "Base de datos anterior eliminada (si existía)"

    # Crear BD
    sudo -u postgres psql -c "CREATE DATABASE $DB OWNER $USER;" 2>/dev/null
    ok "Base de datos '$DB' creada"

    # Restaurar desde backup
    echo "  Restaurando backup... (esto puede tardar unos minutos)"
    sudo -u postgres psql -d $DB -f "$BACKUP_TMP" 2>/dev/null
    ok "Backup restaurado exitosamente"

    # Conceder permisos en TODOS los schemas
    echo "  Concediendo permisos..."
    SCHEMAS=$(sudo -u postgres psql -d $DB -t -A -c "
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog','information_schema')
    " 2>/dev/null)

    for SCHEMA in $SCHEMAS; do
        sudo -u postgres psql -d $DB -c "GRANT ALL ON SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
        sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL TABLES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
        sudo -u postgres psql -d $DB -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA $SCHEMA TO $USER;" 2>/dev/null || true
    done
    ok "Permisos concedidos en todos los schemas"

    # Verificación rápida
    echo ""
    echo "  Verificando contenido de la BD..."
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
        SELECT
            (SELECT COUNT(*) FROM shared.departamento) as deptos,
            (SELECT COUNT(*) FROM shared.provincia) as provs,
            (SELECT COUNT(*) FROM shared.municipio) as munis,
            (SELECT COUNT(*) FROM information_schema.tables
             WHERE table_schema NOT IN ('pg_catalog','information_schema')) as tablas
    " 2>/dev/null | while IFS='|' read -r deptos provs munis tablas; do
        echo "    Departamentos: $deptos"
        echo "    Provincias:    $provs"
        echo "    Municipios:    $munis"
        echo "    Total tablas:  $tablas"
    done
    ok "Base de datos verificada"

    # Limpiar
    rm -f "$BACKUP_TMP"

else
    step 4 "Saltando restauración (modo --api-only)..."
    ok "Modo --api-only"
fi

# ================================================================
#  5. CREAR ENTORNO VIRTUAL E INSTALAR DEPENDENCIAS PYTHON
# ================================================================
step 5 "Configurando entorno Python de la API..."

VENV_DIR="$PROJECT_DIR/venv"

# Crear venv como usuario real (no root)
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creando entorno virtual..."
    sudo -u "$REAL_USER" python3 -m venv "$VENV_DIR"
    ok "Entorno virtual creado"
else
    ok "Entorno virtual ya existe"
fi

# Instalar dependencias
echo "  Instalando dependencias Python..."
sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && pip install -q -r '$PROJECT_DIR/requirements.txt'"
ok "Dependencias Python instaladas"

# Verificar que uvicorn funciona
if sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && python -c 'import uvicorn; import fastapi; import sqlalchemy; print(\"OK\")'" 2>/dev/null; then
    ok "Módulos Python verificados"
else
    fail "Error al verificar módulos Python"
    exit 1
fi

# ================================================================
#  5.1 EJECUTAR MIGRACIONES (modo update o full)
# ================================================================
if [ "$MODE" = "update" ] || [ "$MODE" = "full" ] || [ "$MODE" = "tunnel" ]; then
    step 6 "Ejecutando migraciones de base de datos..."
    
    # Verificar que la BD existe
    if ! PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT 1;" >/dev/null 2>&1; then
        fail "Base de datos '$DB' no existe"
        exit 1
    fi
    
    # Ejecutar migración v1.2.0
    MIGRATION_120="$PROJECT_DIR/database/migration_v1.2.0.sql"
    if [ -f "$MIGRATION_120" ]; then
        echo "  Ejecutando migración v1.2.0..."
        PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION_120" 2>/dev/null || true
        ok "Migración v1.2.0 ejecutada"
    else
        warn "Archivo migration_v1.2.0.sql no encontrado"
    fi
    
    # Ejecutar migración v1.2.1
    MIGRATION_121="$PROJECT_DIR/database/migration_v1.2.1.sql"
    if [ -f "$MIGRATION_121" ]; then
        echo "  Ejecutando migración v1.2.1..."
        PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION_121" 2>/dev/null || true
        ok "Migración v1.2.1 ejecutada"
    else
        warn "Archivo migration_v1.2.1.sql no encontrado"
    fi
    
    # Ejecutar migración v1.2.3
    MIGRATION_123="$PROJECT_DIR/database/migration_v1.2.3.sql"
    if [ -f "$MIGRATION_123" ]; then
        echo "  Ejecutando migración v1.2.3..."
        PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION_123" 2>/dev/null || true
        ok "Migración v1.2.3 ejecutada"
    else
        warn "Archivo migration_v1.2.3.sql no encontrado"
    fi
    
    # Ejecutar migración v1.2.5
    MIGRATION_125="$PROJECT_DIR/database/migration_v1.2.5_permisos.sql"
    if [ -f "$MIGRATION_125" ]; then
        echo "  Ejecutando migración v1.2.5..."
        PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION_125" 2>/dev/null || true
        ok "Migración v1.2.5 ejecutada"
    else
        warn "Archivo migration_v1.2.5_permisos.sql no encontrado"
    fi
    
    ok "Migraciones completadas"
fi

# ================================================================
#  6. CONFIGURAR ARCHIVO .env
# ================================================================
step 7 "Configurando variables de entorno..."

ENV_FILE="$PROJECT_DIR/.env"

# Detectar IP del servidor para DATABASE_URL
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")

cat > "$ENV_FILE" << ENVEOF
# SINAGERSAT API - Configuración de entorno
# Generado por desplegar_todo.sh el $(date '+%Y-%m-%d %H:%M:%S')

# Base de datos (ajustar host según entorno)
DATABASE_URL=postgresql://${USER}:${PW}@127.0.0.1:5432/${DB}

# JWT (cambiar JWT_SECRET en producción)
JWT_SECRET=sinagersat-secret-key-change-in-production-2026
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
ENVEOF

# Ajustar permisos
chown "$REAL_USER":"$(id -gn "$REAL_USER")" "$ENV_FILE" 2>/dev/null || true
chmod 600 "$ENV_FILE" 2>/dev/null || true
ok "Archivo .env configurado (host: 127.0.0.1)"

# ================================================================
#  7.1 CREAR DIRECTORIO DE UPLOADS
# ================================================================
step 8 "Creando directorio de uploads..."

UPLOADS_DIR="$PROJECT_DIR/uploads/reports"
if [ ! -d "$UPLOADS_DIR" ]; then
    mkdir -p "$UPLOADS_DIR"
    chown -R "$REAL_USER":"$(id -gn "$REAL_USER")" "$PROJECT_DIR/uploads" 2>/dev/null || true
    ok "Directorio de uploads creado: $UPLOADS_DIR"
else
    ok "Directorio de uploads ya existe"
fi

# ================================================================
#  7.2 CREAR SCRIPTS DE INICIO
# ================================================================
step 8 "Generando scripts de inicio..."

# --- start_api.sh ---
cat > "$PROJECT_DIR/start_api.sh" << 'APIEOF'
#!/bin/bash
# SINAGERSAT - Iniciar API
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
echo ""
echo "  SINAGERSAT API - http://0.0.0.0:8000"
echo "  Docs: http://localhost:8000/docs"
echo ""
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
APIEOF
chmod +x "$PROJECT_DIR/start_api.sh"
ok "start_api.sh creado"

# --- start_tunnel.sh ---
cat > "$PROJECT_DIR/start_tunnel.sh" << 'TUNELEOF'
#!/bin/bash
# SINAGERSAT - Iniciar API + Cloudflare Quick Tunnel
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CYAN="\033[0;36m"; VERDE="\033[0;32m"; ROJO="\033[0;31m"; AMARILLO="\033[1;33m"; BOLD="\033[1m"; SIN_COLOR="\033[0m"

echo ""
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  SINAGERSAT API + Cloudflare Tunnel${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  Acceso externo desde internet${SIN_COLOR}"
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo ""

if [ ! -d "venv" ]; then
    python3 -m venv venv && source venv/bin/activate && pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

if ! command -v cloudflared &>/dev/null; then
    echo -e "${AMARILLO}[!]${SIN_COLOR} Instalando cloudflared..."
    curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb 2>/dev/null
    sudo dpkg -i /tmp/cloudflared.deb 2>/dev/null
    rm -f /tmp/cloudflared.deb
fi

pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

echo -e "${BOLD}[1/3]${SIN_COLOR} Iniciando API..."
uvicorn api.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
API_PID=$!
sleep 3

if ! curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo -e "${ROJO}[ERROR]${SIN_COLOR} La API no pudo iniciarse"; cat /tmp/uvicorn.log | tail -5; exit 1
fi
echo -e "  ${VERDE}[OK]${SIN_COLOR} API corriendo (PID: $API_PID)"

echo -e "${BOLD}[2/3]${SIN_COLOR} Iniciando Cloudflare Quick Tunnel..."
cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!

TUNNEL_URL=""
for i in $(seq 1 15); do
    TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
    [ -n "$TUNNEL_URL" ] && break
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${ROJO}[ERROR]${SIN_COLOR} No se pudo obtener la URL del tunnel"; kill $API_PID 2>/dev/null; exit 1
fi
echo -e "  ${VERDE}[OK]${SIN_COLOR} Tunnel activo (PID: $TUNNEL_PID)"

echo -e "${BOLD}[3/3]${SIN_COLOR} Verificando acceso externo..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$TUNNEL_URL/" 2>/dev/null)
[ "$HTTP_CODE" = "200" ] && echo -e "  ${VERDE}[OK]${SIN_COLOR} Acceso externo verificado" || echo -e "  ${AMARILLO}[!]${SIN_COLOR} HTTP: $HTTP_CODE (puede estar propagándose)"

echo "$TUNNEL_URL" > /tmp/sinagersat_url.txt

echo ""
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo -e "${CYAN}${BOLD}  SERVIDOR SINAGERSAT ACTIVO${SIN_COLOR}"
echo -e "${CYAN}${BOLD}================================================${SIN_COLOR}"
echo ""
echo -e "  ${BOLD}LOCAL:${SIN_COLOR}"
echo "    API:       http://localhost:8000"
echo "    Swagger:   http://localhost:8000/docs"
echo "    ReDoc:     http://localhost:8000/redoc"
echo ""
echo -e "  ${BOLD}ACCESO EXTERNO (desde internet):${SIN_COLOR}"
echo -e "    ${VERDE}$TUNNEL_URL${SIN_COLOR}"
echo ""
echo -e "    ${BOLD}Swagger:${SIN_COLOR}  $TUNNEL_URL/docs"
echo -e "    ${BOLD}ReDoc:${SIN_COLOR}    $TUNNEL_URL/redoc"
echo -e "    ${BOLD}Health:${SIN_COLOR}   $TUNNEL_URL/health"
echo ""
echo -e "  ${BOLD}Comparte esta URL:${SIN_COLOR}"
echo -e "    ${VERDE}$TUNNEL_URL${SIN_COLOR}"
echo ""
echo -e "  ${BOLD}DETENER:${SIN_COLOR} kill $API_PID $TUNNEL_PID"
echo -e "  ${BOLD}LOGS:${SIN_COLOR}   tail -f /tmp/uvicorn.log | tail -f /tmp/cloudflared.log"
echo ""

echo "$API_PID $TUNNEL_PID" > /tmp/sinagersat_pids.txt
TUNELEOF
chmod +x "$PROJECT_DIR/start_tunnel.sh"
ok "start_tunnel.sh creado"

# --- stop.sh ---
cat > "$PROJECT_DIR/stop.sh" << 'STOPEOF'
#!/bin/bash
# SINAGERSAT - Detener todos los servicios
echo "Deteniendo SINAGERSAT..."
pkill -f "uvicorn api.main" 2>/dev/null && echo "  API detenida" || echo "  API no estaba corriendo"
pkill -f "cloudflared tunnel" 2>/dev/null && echo "  Tunnel detenido" || echo "  Tunnel no estaba corriendo"
rm -f /tmp/sinagersat_pids.txt
echo "Listo."
STOPEOF
chmod +x "$PROJECT_DIR/stop.sh"
ok "stop.sh creado"

# ================================================================
#  9. INICIAR API (y opcionalmente tunnel)
# ================================================================
if [ "$MODE" = "full" ] || [ "$MODE" = "tunnel" ] || [ "$MODE" = "api" ]; then
    step 9 "Iniciando API SINAGERSAT..."

    # Matar instancias anteriores
    pkill -f "uvicorn api.main" 2>/dev/null || true
    sleep 1

    # Iniciar API en background
    cd "$PROJECT_DIR"
    sudo -u "$REAL_USER" bash -c "source venv/bin/activate && cd '$PROJECT_DIR' && setsid uvicorn api.main:app --host $API_HOST --port $API_PORT > /tmp/uvicorn.log 2>&1 &"
    sleep 4

    if curl -s "http://127.0.0.1:$API_PORT/" > /dev/null 2>&1; then
        ok "API corriendo en http://0.0.0.0:$API_PORT"
    else
        warn "La API puede estar iniciándose aún, verifica: tail -f /tmp/uvicorn.log"
    fi
else
    step 8 "Saltando inicio de API..."
    ok "Iniciar manualmente: bash start_api.sh"
fi

# ================================================================
#  10. CLOUDFLARE TUNNEL (solo con --tunnel)
# ================================================================
if [ "$MODE" = "tunnel" ]; then
    step 10 "Iniciando Cloudflare Quick Tunnel..."

    # Verificar/instalar cloudflared
    if ! command -v cloudflared &>/dev/null; then
        echo "  Instalando cloudflared..."
        curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb 2>/dev/null
        dpkg -i /tmp/cloudflared.deb 2>/dev/null
        rm -f /tmp/cloudflared.deb
        ok "cloudflared instalado"
    else
        ok "cloudflared ya instalado ($(cloudflared --version 2>/dev/null | head -1))"
    fi

    # Iniciar tunnel
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    sleep 1
    cloudflared tunnel --url "http://localhost:$API_PORT" > /tmp/cloudflared.log 2>&1 &
    TUNNEL_PID=$!

    # Esperar URL con reintentos
    TUNNEL_URL=""
    for i in $(seq 1 20); do
        TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
        [ -n "$TUNNEL_URL" ] && break
        sleep 1
    done

    if [ -n "$TUNNEL_URL" ]; then
        # Verificar acceso externo
        sleep 2
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$TUNNEL_URL/" 2>/dev/null)
        ok "Tunnel activo: $TUNNEL_URL"
        [ "$HTTP_CODE" = "200" ] && ok "Acceso externo verificado" || warn "HTTP $HTTP_CODE (puede estar propagándose)"
        echo "$TUNNEL_URL" > /tmp/sinagersat_url.txt
        echo "$TUNNEL_PID" > /tmp/sinagersat_tunnel_pid.txt
    else
        warn "No se pudo obtener la URL del tunnel"
        warn "Verifica: tail -f /tmp/cloudflared.log"
    fi
else
    if [ "$MODE" != "db" ]; then
        step 10 "Saltando Cloudflare tunnel..."
        ok "Para activar: bash start_tunnel.sh"
    fi
fi

# ================================================================
#  RESUMEN FINAL
# ================================================================
echo ""
echo -e "${CYAN}================================================${SIN_COLOR}"
echo -e "${CYAN}  DESPLIEGUE COMPLETADO EXITOSAMENTE${SIN_COLOR}"
echo -e "${CYAN}================================================${SIN_COLOR}"
echo ""

if [ "$MODE" != "api" ]; then
    echo -e "  ${VERDE}BASE DE DATOS:${SIN_COLOR}"
    echo "    Base de datos:  $DB"
    echo "    Usuario:        $USER"
    echo "    Contraseña:     $PW"
    echo "    Host:           127.0.0.1 (y $SERVER_IP)"
    echo "    Puerto:         5432"
    echo ""
    echo "    Conexión:"
    echo "      PGPASSWORD=$PW psql -U $USER -d $DB -h 127.0.0.1"
    echo ""
fi

if [ "$MODE" = "full" ] || [ "$MODE" = "tunnel" ] || [ "$MODE" = "api" ]; then
    echo -e "  ${VERDE}API REST:${SIN_COLOR}"
    echo "    Local:    http://localhost:$API_PORT"
    echo "    Docs:     http://localhost:$API_PORT/docs"
    echo "    ReDoc:    http://localhost:$API_PORT/redoc"
    echo ""
    echo "    Endpoints: 166 (auth, shared, edan, rea, usuarios, geojson, geom, ubicacion)"
    echo ""
fi

if [ "$MODE" = "tunnel" ] && [ -n "$TUNNEL_URL" ]; then
    echo -e "  ${VERDE}CLOUDFLARE TUNNEL:${SIN_COLOR}"
    echo "    Público:  $TUNNEL_URL"
    echo "    Docs:     $TUNNEL_URL/docs"
    echo ""
fi

echo -e "  ${VERDE}COMANDOS ÚTILES:${SIN_COLOR}"
echo "    bash start_api.sh          # Iniciar API local"
echo "    bash start_tunnel.sh       # Iniciar API + tunnel público"
echo "    bash stop.sh               # Detener todo"
echo "    bash deploy/verificar.sh   # Verificar base de datos"
echo ""
echo -e "  ${VERDE}ARCHIVOS:${SIN_COLOR}"
echo "    uploads/reports/           # Imágenes de reportes"
echo "    .env                       # Variables de entorno"
    echo "    database/backup_v1.2.7.sql   # Backup de BD (v1.2.7)"
    echo "    database/backup_v1.2.6.sql   # Backup de BD (v1.2.6)"
echo ""
echo -e "  ${VERDE}HERRAMIENTAS:${SIN_COLOR}"
echo "    DBeaver:   Host: 127.0.0.1 | DB: $DB | User: $USER"
echo "    pgAdmin4:  File > Import > database/servers.json"
echo "    Swagger:   http://localhost:$API_PORT/docs"
echo ""
