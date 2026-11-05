#!/bin/bash
# ================================================================
#  SINAGERSAT - 04 CONFIGURAR ARCHIVO .env
#  Genera .env con tokens aleatorios (conserva valores si ya existe).
#  Uso: bash despliegue/scripts/04_configurar_env.sh
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DESPL_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

echo ""
echo "================================================"
echo "  SINAGERSAT - CONFIGURACION .env"
echo "================================================"
echo ""

if [ -f "$ENV_FILE" ]; then
    ok ".env existente — se conservarán tokens"
else
    ok ".env no existe — se generará uno nuevo"
fi

# Conservar tokens existentes si los hay
EXISTING_API_TOKEN=$(grep '^API_AUTH_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
API_AUTH_TOKEN="${EXISTING_API_TOKEN:-$(openssl rand -hex 32)}"

EXISTING_LOCAL_TOKEN=$(grep '^EMBEDDINGS_LOCAL_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
EMBEDDINGS_LOCAL_TOKEN="${EXISTING_LOCAL_TOKEN:-$(openssl rand -hex 32)}"

EXISTING_JWT=$(grep '^JWT_SECRET=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
JWT_SECRET="${EXISTING_JWT:-$(openssl rand -hex 32)}"

EXISTING_LLM_KEY=$(grep '^LLM_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
LLM_API_KEY="${EXISTING_LLM_KEY:-}"

EXISTING_GEMINI=$(grep '^GEMINI_EMBEDDINGS_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
GEMINI_EMBEDDINGS_API_KEY="${EXISTING_GEMINI:-}"

cat > "$ENV_FILE" << ENVEOF
# SINAGERSAT API - Variables de entorno
# Generado por despliegue/scripts/04_configurar_env.sh el $(date '+%Y-%m-%d %H:%M:%S')
# No subir este archivo a git.

# Base de datos
DATABASE_URL=postgresql://${USER}:${PW}@127.0.0.1:5432/${DB}

# JWT
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# MotorIA (RAG)
MOTOR_IA_SCHEMA=motor_ia
MOTOR_IA_UPLOAD_DIR=uploads/motor_ia
API_AUTH_TOKEN=${API_AUTH_TOKEN}

# LLM externo (Groq u otro proveedor OpenAI-compatible)
LLM_MODE=external
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
LLM_API_KEY=${LLM_API_KEY}
LLM_MAX_TOKENS=512
LLM_RAZONAMIENTO_TOKENS=2048
LLM_MASTER_KEY_FILE=.keys/motor_ia_llm_master.key

# Embeddings locales (servicio motoria-embeddings en :8001)
EMBEDDINGS_MODE=external
EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1
EMBEDDINGS_API_KEY=${EMBEDDINGS_LOCAL_TOKEN}
EMBEDDINGS_API_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDINGS_LOCAL_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDINGS_LOCAL_TOKEN=${EMBEDDINGS_LOCAL_TOKEN}
EMBEDDINGS_LOCAL_MAX_BATCH=128
EMBEDDINGS_DIM=384
EMBEDDINGS_EXTERNAL_BATCH_SIZE=8

# Respaldo embeddings (opcional)
GEMINI_EMBEDDINGS_API_KEY=${GEMINI_EMBEDDINGS_API_KEY}
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDINGS_IDLE_UNLOAD_SEC=120
EMBEDDINGS_TORCH_THREADS=1
EMBEDDINGS_PROVIDER_NAME=local-multilingual
EMBEDDINGS_METRICS_ENABLED=true
EMBEDDINGS_METRICS_PROVIDER=local-multilingual

# Whisper (voz)
WHISPER_MODEL=tiny
ENVEOF

chmod 600 "$ENV_FILE" 2>/dev/null || true
ok "Archivo .env generado en $ENV_FILE"

echo ""
echo "  NOTA: para producción, edita .env y cambia:"
echo "    - JWT_SECRET (ya es aleatorio si se generó nuevo)"
echo "    - LLM_API_KEY (clave de Groq u otro proveedor)"
echo "    - AGETIC_* si usas firma digital"
echo ""
echo "================================================"
echo -e "  ${VERDE}ENTORNO CONFIGURADO${SIN_COLOR}"
echo "================================================"
echo "  Siguiente: sudo bash despliegue/scripts/05_instalar_servicios.sh"
echo ""
