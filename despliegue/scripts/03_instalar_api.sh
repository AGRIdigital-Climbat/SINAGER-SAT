#!/bin/bash
# ================================================================
#  SINAGERSAT - 03 INSTALAR API (entorno Python)
#  Crea venv e instala requirements.txt con torch CPU.
#  Uso: bash despliegue/scripts/03_instalar_api.sh
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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DESPL_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

echo ""
echo "================================================"
echo "  SINAGERSAT - INSTALACION DE LA API"
echo "================================================"
echo ""

# [1] Verificar requirements.txt
step "[1/4] Verificando archivos..."
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    fail "requirements.txt no encontrado en $PROJECT_DIR"
    exit 1
fi
ok "requirements.txt encontrado"

if [ ! -d "$PROJECT_DIR/api" ]; then
    fail "Directorio api/ no encontrado en $PROJECT_DIR"
    exit 1
fi
ok "Código de la API encontrado"

# [2] Crear venv
step "[2/4] Creando entorno virtual..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "venv creado en $VENV_DIR"
else
    ok "venv ya existe"
fi

# [3] Instalar dependencias
step "[3/4] Instalando dependencias Python..."

# Torch CPU primero: evita variante CUDA (más pesada)
if ! bash -c "source '$VENV_DIR/bin/activate' && python -c 'import torch'" 2>/dev/null; then
    echo "  Instalando torch (CPU)..."
    bash -c "source '$VENV_DIR/bin/activate' && pip install -q --upgrade pip && pip install -q torch --index-url https://download.pytorch.org/whl/cpu" \
        || warn "torch CPU falló; se continuará con requirements.txt"
fi

echo "  Instalando requirements.txt..."
bash -c "source '$VENV_DIR/bin/activate' && pip install -q -r '$PROJECT_DIR/requirements.txt'"
ok "Dependencias instaladas"

# [4] Verificar módulos críticos
step "[4/4] Verificando módulos..."
if bash -c "source '$VENV_DIR/bin/activate' && python -c 'import uvicorn, fastapi, sqlalchemy, psycopg2, jose, bcrypt; print(\"core OK\")'" 2>/dev/null; then
    ok "Módulos core (fastapi, uvicorn, sqlalchemy, psycopg2, jose, bcrypt)"
else
    fail "Fallo al importar módulos core"
    exit 1
fi

if bash -c "source '$VENV_DIR/bin/activate' && python -c 'import pymupdf, openai, sentence_transformers, whisper'" 2>/dev/null; then
    ok "Módulos MotorIA (pymupdf, openai, sentence-transformers, whisper)"
else
    warn "Algunos módulos MotorIA fallaron — la API arrancará pero MotorIA podría no funcionar"
fi

echo ""
echo "================================================"
echo -e "  ${VERDE}API INSTALADA${SIN_COLOR}"
echo "================================================"
echo "  venv: $VENV_DIR"
echo "  Python: $(bash -c "source '$VENV_DIR/bin/activate' && python --version" 2>&1)"
echo ""
echo "  Siguiente: bash despliegue/scripts/04_configurar_env.sh"
echo ""
