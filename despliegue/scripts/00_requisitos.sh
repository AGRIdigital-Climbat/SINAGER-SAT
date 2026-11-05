#!/bin/bash
# ================================================================
#  SINAGERSAT - 00 REQUISITOS DEL SISTEMA
#  Verifica que el servidor cumple los requisitos mínimos.
#  Uso: bash despliegue/scripts/00_requisitos.sh
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

ERRORES=0

echo ""
echo "================================================"
echo "  SINAGERSAT - VERIFICACION DE REQUISITOS"
echo "================================================"
echo ""

# [1] Sistema operativo
echo "[1] Sistema operativo..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "ubuntu" ]; then
        if [ "$(echo "$VERSION_ID >= 22.04" | bc -l 2>/dev/null)" = "1" ] || [ "$VERSION_ID" = "24.04" ] || [ "$VERSION_ID" = "22.04" ]; then
            ok "$PRETTY_NAME (recomendado: Ubuntu 24.04 LTS)"
        else
            warn "$PRETTY_NAME — Ubuntu 22.04+ recomendado (mínimo 20.04)"
        fi
    elif [ "$ID" = "debian" ]; then
        ok "$PRETTY_NAME (compatible)"
    else
        warn "$PRETTY_NAME — no oficialmente soportado (se intentará igualmente)"
    fi
else
    fail "No se pudo detectar el sistema operativo"
    ERRORES=$((ERRORES+1))
fi

# [2] CPU y RAM
echo ""
echo "[2] Recursos del servidor..."
CPU_CORES=$(nproc 2>/dev/null || echo 0)
RAM_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo 0)
DISK_AVAIL=$(df -BG / 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' | tr -d ' ' || echo 0)

if [ "$CPU_CORES" -ge 4 ]; then
    ok "CPU: $CPU_CORES núcleos (mínimo 4, recomendado 6)"
else
    warn "CPU: $CPU_CORES núcleos — mínimo recomendado 4"
fi

if [ "$RAM_MB" -ge 7500 ]; then
    ok "RAM: ${RAM_MB}MB (recomendado 8GB+)"
elif [ "$RAM_MB" -ge 3800 ]; then
    ok "RAM: ${RAM_MB}MB (mínimo 4GB, aceptable con 4 workers)"
else
    warn "RAM: ${RAM_MB}MB — mínimo 4GB recomendado"
fi

if [ "${DISK_AVAIL:-0}" -ge 30 ]; then
    ok "Disco disponible: ${DISK_AVAIL}GB (mínimo 40GB total, dump ~400MB)"
else
    warn "Disco disponible: ${DISK_AVAIL}GB — verificar espacio (dump ~400MB + venv ~3GB)"
fi

# [3] Python
echo ""
echo "[3] Python..."
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        ok "Python $PY_VER (recomendado 3.12)"
    else
        warn "Python $PY_VER — se requiere 3.10+ (recomendado 3.12)"
    fi
else
    fail "python3 no está instalado"
    ERRORES=$((ERRORES+1))
fi

if python3 -m venv --help &>/dev/null 2>&1; then
    ok "python3-venv disponible"
else
    warn "python3-venv no disponible (lo instalará 01_instalar_postgres.sh)"
fi

# [4] PostgreSQL
echo ""
echo "[4] PostgreSQL..."
if command -v psql &>/dev/null; then
    PG_VER=$(psql --version | grep -oP '\d+' | head -1)
    if [ "$PG_VER" -ge 14 ]; then
        ok "PostgreSQL $PG_VER (recomendado 16)"
    else
        warn "PostgreSQL $PG_VER — se recomienda 14+ (probado con 16)"
    fi
else
    warn "PostgreSQL no instalado (lo instalará 01_instalar_postgres.sh)"
fi

if command -v pg_isready &>/dev/null && pg_isready -q 2>/dev/null; then
    ok "PostgreSQL corriendo"
else
    warn "PostgreSQL no está corriendo aún"
fi

# [5] PostGIS
echo ""
echo "[5] PostGIS / pgvector..."
if dpkg -l 2>/dev/null | grep -q "postgresql-.*-postgis"; then
    ok "PostGIS instalado"
else
    warn "PostGIS no instalado (lo instalará 01_instalar_postgres.sh)"
fi

PG_VER_NUM=$(psql --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "16")
if dpkg -l 2>/dev/null | grep -q "postgresql-$PG_VER_NUM-pgvector"; then
    ok "pgvector instalado"
else
    warn "pgvector no instalado (requerido para MotorIA)"
fi

# [6] ffmpeg (Whisper / voz)
echo ""
echo "[6] ffmpeg (para MotorIA /voz)..."
if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg disponible"
else
    warn "ffmpeg no instalado (lo instalará 01_instalar_postgres.sh)"
fi

# [7] Archivos del paquete
echo ""
echo "[7] Archivos del paquete..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$DESPL_DIR")"

if [ -f "$DESPL_DIR/dump/"*.sql ] 2>/dev/null || ls "$DESPL_DIR/dump/"*.sql &>/dev/null; then
    DUMP_FILE=$(ls -1t "$DESPL_DIR/dump/"*.sql 2>/dev/null | head -1)
    DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    ok "Dump de BD encontrado: $(basename "$DUMP_FILE") ($DUMP_SIZE)"
else
    fail "No se encontró dump en $DESPL_DIR/dump/"
    ERRORES=$((ERRORES+1))
fi

if [ -d "$DESPL_DIR/migraciones" ] && [ -n "$(ls -A "$DESPL_DIR/migraciones/"*.sql 2>/dev/null)" ]; then
    MIG_COUNT=$(ls "$DESPL_DIR/migraciones/"*.sql 2>/dev/null | wc -l)
    ok "Migraciones disponibles: $MIG_COUNT"
else
    warn "No se encontraron migraciones en $DESPL_DIR/migraciones/"
fi

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    ok "requirements.txt encontrado"
else
    fail "requirements.txt no encontrado en $PROJECT_DIR"
    ERRORES=$((ERRORES+1))
fi

if [ -d "$PROJECT_DIR/api" ]; then
    ok "Código de la API encontrado (api/)"
else
    fail "Directorio api/ no encontrado en $PROJECT_DIR"
    ERRORES=$((ERRORES+1))
fi

# [8] Puertos
echo ""
echo "[8] Puertos (8000 API, 8001 embeddings, 5432 PostgreSQL)..."
for PUERTO in 8000 8001 5432; do
    if ss -tlnp 2>/dev/null | grep -q ":$PUERTO "; then
        warn "Puerto $PUERTO ya está en uso"
    else
        ok "Puerto $PUERTO libre"
    fi
done

# RESUMEN
echo ""
echo "================================================"
if [ "$ERRORES" -eq 0 ]; then
    echo -e "  ${VERDE}REQUISITOS CUMPLIDOS${SIN_COLOR}"
    echo "  Siguiente paso: sudo bash despliegue/scripts/desplegar_todo.sh"
else
    echo -e "  ${ROJO}$ERRORES ERROR(ES) — corregir antes de continuar${SIN_COLOR}"
fi
echo "================================================"
echo ""

exit $ERRORES
