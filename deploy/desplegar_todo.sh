#!/bin/bash
# ================================================================
#  SINAGERSAT - DESPLIEGUE COMPLETO EN ENTORNO VACÍO
#  Instala todo desde cero: PostgreSQL + BD completa + API
#
#  Uso:
#    sudo bash deploy/desplegar_todo.sh              # despliegue completo
#    sudo bash deploy/desplegar_todo.sh --db-only    # solo base de datos
#    sudo bash deploy/desplegar_todo.sh --api-only   # solo API (si PG ya está)
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
        --update)   MODE="update" ;;
        --help|-h)
            echo "Uso: sudo bash deploy/desplegar_todo.sh [opciones]"
            echo ""
            echo "Opciones:"
            echo "  (sin args)    Despliegue completo (BD + API)"
            echo "  --db-only     Solo base de datos"
            echo "  --api-only    Solo API (PostgreSQL debe estar corriendo)"
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
if [ "$EUID" -ne 0 ] && [ "$MODE" = "db" -o "$MODE" = "full" ]; then
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

    # pgvector (requerido por MotorIA para embeddings)
    PG_VER=$(psql --version | grep -oP '\d+' | head -1)
    if dpkg -l | grep -q "postgresql-$PG_VER-pgvector" 2>/dev/null; then
        ok "pgvector ya instalado"
    else
        echo "  Instalando pgvector..."
        apt-get install -y -qq "postgresql-$PG_VER-pgvector" 2>/dev/null || true
        if dpkg -l | grep -q "postgresql-$PG_VER-pgvector" 2>/dev/null; then
            ok "pgvector instalado"
        else
            warn "No se pudo instalar pgvector; la migración de MotorIA fallará"
        fi
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

    # curl
    if ! command -v curl &>/dev/null; then
        apt-get install -y -qq curl
        ok "curl instalado"
    fi

    # ffmpeg (requerido por Whisper para /voz)
    if ! command -v ffmpeg &>/dev/null; then
        echo "  Instalando ffmpeg..."
        apt-get install -y -qq ffmpeg
        ok "ffmpeg instalado"
    else
        ok "ffmpeg disponible"
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
# Torch CPU primero: evita que sentence-transformers descargue la variante CUDA
# (más pesada) y mantiene el consumo de RAM/disco bajo en el servidor.
if ! sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && python -c 'import torch'" 2>/dev/null; then
    sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && pip install -q torch --index-url https://download.pytorch.org/whl/cpu" \
        || warn "No se pudo instalar torch CPU; se intentará con las dependencias normales"
fi
sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && pip install -q -r '$PROJECT_DIR/requirements.txt'"
ok "Dependencias Python instaladas"

# Verificar que uvicorn y las dependencias de MotorIA funcionan
if sudo -u "$REAL_USER" bash -c "source '$VENV_DIR/bin/activate' && python -c 'import uvicorn; import fastapi; import sqlalchemy; import pymupdf; import openai; import sentence_transformers; import whisper; print(\"OK\")'" 2>/dev/null; then
    ok "Módulos Python verificados"
else
    fail "Error al verificar módulos Python"
    exit 1
fi

# ================================================================
#  5.1 EJECUTAR MIGRACIONES (modo update o full)
# ================================================================
if [ "$MODE" = "update" ] || [ "$MODE" = "full" ]; then
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
    
    # Ejecutar migración v1.2.7
    MIGRATION_127="$PROJECT_DIR/database/migration_v1.2.7.sql"
    if [ -f "$MIGRATION_127" ]; then
        echo "  Ejecutando migración v1.2.7..."
        PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -f "$MIGRATION_127" 2>/dev/null || true
        ok "Migración v1.2.7 ejecutada"
    else
        warn "Archivo migration_v1.2.7.sql no encontrado"
    fi

    # Ejecutar migración de MotorIA (requiere superusuario por CREATE EXTENSION)
    MIGRATION_MOTOR_IA="$PROJECT_DIR/database/migrations/v2.63.0_motor_ia.sql"
    if [ -f "$MIGRATION_MOTOR_IA" ]; then
        echo "  Ejecutando migración MotorIA..."
        sudo -u postgres psql -d $DB -f "$MIGRATION_MOTOR_IA" >/dev/null 2>&1 \
            && ok "Migración MotorIA ejecutada" \
            || warn "Migración MotorIA falló; revisar pgvector y permisos"
    else
        warn "Archivo migrations/v2.63.0_motor_ia.sql no encontrado"
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

# Conservar el token de MotorIA si ya existía (evita invalidar clientes)
EXISTING_API_TOKEN=$(grep '^API_AUTH_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
API_AUTH_TOKEN="${EXISTING_API_TOKEN:-$(openssl rand -hex 32)}"
EXISTING_LOCAL_TOKEN=$(grep '^EMBEDDINGS_LOCAL_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
EMBEDDINGS_LOCAL_TOKEN="${EMBEDDINGS_LOCAL_TOKEN:-${EXISTING_LOCAL_TOKEN:-$(openssl rand -hex 32)}}"
EXISTING_GEMINI_EMBEDDINGS_KEY=$(grep '^GEMINI_EMBEDDINGS_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
GEMINI_EMBEDDINGS_API_KEY="${GEMINI_EMBEDDINGS_API_KEY:-$EXISTING_GEMINI_EMBEDDINGS_KEY}"

cat > "$ENV_FILE" << ENVEOF
# SINAGERSAT API - Configuración de entorno
# Generado por desplegar_todo.sh el $(date '+%Y-%m-%d %H:%M:%S')

# Base de datos (ajustar host según entorno)
DATABASE_URL=postgresql://${USER}:${PW}@127.0.0.1:5432/${DB}

# JWT (cambiar JWT_SECRET en producción)
JWT_SECRET=sinagersat-secret-key-change-in-production-2026
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# MotorIA (RAG)
MOTOR_IA_SCHEMA=motor_ia
MOTOR_IA_UPLOAD_DIR=uploads/motor_ia
API_AUTH_TOKEN=${API_AUTH_TOKEN}
LLM_MODE=external
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
LLM_MAX_TOKENS=512
LLM_RAZONAMIENTO_TOKENS=2048
LLM_MASTER_KEY_FILE=.keys/motor_ia_llm_master.key
# Cargar la clave del proveedor externo (Groq/OpenAI-compatible) o registrar
# un proveedor desde POST /api/v2/motor-ia/llm/proveedores
LLM_API_KEY=${LLM_API_KEY:-}
EMBEDDINGS_MODE=${EMBEDDINGS_MODE:-external}
EMBEDDINGS_API_BASE=${EMBEDDINGS_API_BASE:-http://127.0.0.1:8001/v1}
EMBEDDINGS_API_KEY=${EMBEDDINGS_LOCAL_TOKEN}
EMBEDDINGS_API_MODEL=${EMBEDDINGS_API_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}
EMBEDDINGS_LOCAL_MODEL=${EMBEDDINGS_LOCAL_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}
EMBEDDINGS_LOCAL_TOKEN=${EMBEDDINGS_LOCAL_TOKEN}
EMBEDDINGS_LOCAL_MAX_BATCH=${EMBEDDINGS_LOCAL_MAX_BATCH:-128}
EMBEDDINGS_EXTERNAL_BATCH_SIZE=${EMBEDDINGS_EXTERNAL_BATCH_SIZE:-8}
GEMINI_EMBEDDINGS_API_KEY=${GEMINI_EMBEDDINGS_API_KEY:-}
EMBEDDINGS_MODEL=${EMBEDDINGS_MODEL:-sentence-transformers/all-MiniLM-L6-v2}
EMBEDDINGS_DIM=${EMBEDDINGS_DIM:-384}
EMBEDDINGS_IDLE_UNLOAD_SEC=${EMBEDDINGS_IDLE_UNLOAD_SEC:-120}
EMBEDDINGS_TORCH_THREADS=${EMBEDDINGS_TORCH_THREADS:-1}
EMBEDDINGS_PROVIDER_NAME=${EMBEDDINGS_PROVIDER_NAME:-local-multilingual}
EMBEDDINGS_METRICS_ENABLED=${EMBEDDINGS_METRICS_ENABLED:-true}
EMBEDDINGS_METRICS_PROVIDER=${EMBEDDINGS_METRICS_PROVIDER:-local-multilingual}
WHISPER_MODEL=tiny
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

# MotorIA: documentos PDF y clave maestra de cifrado
mkdir -p "$PROJECT_DIR/uploads/motor_ia" "$PROJECT_DIR/.keys"
chown -R "$REAL_USER":"$(id -gn "$REAL_USER")" "$PROJECT_DIR/uploads/motor_ia" "$PROJECT_DIR/.keys" 2>/dev/null || true
chmod 755 "$PROJECT_DIR/uploads/motor_ia" 2>/dev/null || true
chmod 700 "$PROJECT_DIR/.keys" 2>/dev/null || true
ok "Directorios de MotorIA listos (uploads/motor_ia y .keys)"

# ================================================================
#  7.2 INSTALAR UNIDADES SYSTEMD DE MOTORIA
# ================================================================
if command -v systemctl >/dev/null 2>&1 && [ "${EUID:-$(id -u)}" -eq 0 ]; then
    step 8 "Instalando unidades systemd de SINAGERSAT y MotorIA..."
    cp "$PROJECT_DIR/deploy/systemd/sinagersat-api.service" /etc/systemd/system/sinagersat-api.service 2>/dev/null || true
    cp "$PROJECT_DIR/deploy/systemd/motoria-embeddings.service" /etc/systemd/system/motoria-embeddings.service 2>/dev/null || true
    systemctl daemon-reload
    systemctl enable motoria-embeddings.service 2>/dev/null || true
    ok "Unidades systemd instaladas"
else
    ok "Saltando instalacion de systemd (no es root o no hay systemctl)"
fi

# ================================================================
#  7.3 CREAR SCRIPTS DE INICIO
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

# --- stop.sh ---
cat > "$PROJECT_DIR/stop.sh" << 'STOPEOF'
#!/bin/bash
# SINAGERSAT - Detener todos los servicios
echo "Deteniendo SINAGERSAT..."
pkill -f "uvicorn api.main" 2>/dev/null && echo "  API detenida" || echo "  API no estaba corriendo"
echo "Listo."
STOPEOF
chmod +x "$PROJECT_DIR/stop.sh"
ok "stop.sh creado"

# ================================================================
#  9. INICIAR API
# ================================================================
if [ "$MODE" = "full" ] || [ "$MODE" = "api" ]; then
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

if [ "$MODE" = "full" ] || [ "$MODE" = "api" ]; then
    echo -e "  ${VERDE}API REST:${SIN_COLOR}"
    echo "    Local:    http://localhost:$API_PORT"
    echo "    Docs:     http://localhost:$API_PORT/docs"
    echo "    ReDoc:    http://localhost:$API_PORT/redoc"
    echo ""
    echo "    Endpoints: 166 (auth, shared, edan, rea, usuarios, geojson, geom, ubicacion)"
    echo ""
fi

echo -e "  ${VERDE}COMANDOS ÚTILES:${SIN_COLOR}"
echo "    bash start_api.sh          # Iniciar API local"
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
