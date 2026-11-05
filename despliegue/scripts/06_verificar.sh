#!/bin/bash
# ================================================================
#  SINAGERSAT - 06 VERIFICAR DESPLIEGUE
#  Comprueba BD, esquemas, extensiones y servicios.
#  Uso: bash despliegue/scripts/06_verificar.sh
# ================================================================

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[FAIL]${SIN_COLOR} $1"; }

FALLOS=0

echo ""
echo "================================================"
echo "  SINAGERSAT - VERIFICACION DE DESPLIEGUE"
echo "================================================"
echo ""

# [1] PostgreSQL
echo "[1] PostgreSQL..."
if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL corriendo ($(psql --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1))"
else
    fail "PostgreSQL no responde"
    FALLOS=$((FALLOS+1))
fi

# [2] Conexion a la BD
echo ""
echo "[2] Conexion a $DB..."
if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT 1;" >/dev/null 2>&1; then
    ok "Conexion exitosa"
else
    fail "No se pudo conectar — ¿restauraste el dump? (02_restaurar_bd.sh)"
    FALLOS=$((FALLOS+1))
fi

# [3] Esquemas
echo ""
echo "[3] Esquemas esperados..."
ESQUEMAS_ESPERADOS="edan motor_ia rea repositorio rida shared sinb usuarios"
for s in $ESQUEMAS_ESPERADOS; do
    if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c \
        "SELECT 1 FROM information_schema.schemata WHERE schema_name='$s';" 2>/dev/null | grep -q 1; then
        ok "Esquema: $s"
    else
        fail "Esquema faltante: $s"
        FALLOS=$((FALLOS+1))
    fi
done

# [4] Extensiones
echo ""
echo "[4] Extensiones (postgis + vector)..."
for ext in postgis vector; do
    VER=$(PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c \
        "SELECT extversion FROM pg_extension WHERE extname='$ext';" 2>/dev/null)
    if [ -n "$VER" ]; then
        ok "Extensión $ext v$VER"
    else
        fail "Extensión $ext no instalada"
        FALLOS=$((FALLOS+1))
    fi
done

# [5] Conteos clave
echo ""
echo "[5] Conteos de datos..."
if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
SELECT
    (SELECT COUNT(*) FROM shared.departamento) || ' deptos, ' ||
    (SELECT COUNT(*) FROM shared.provincia) || ' provs, ' ||
    (SELECT COUNT(*) FROM shared.municipio) || ' munis, ' ||
    (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_schema NOT IN ('pg_catalog','information_schema')) || ' tablas'
" 2>/dev/null; then
    ok "Conteos verificados"
else
    warn "No se pudieron contar tablas"
fi

# [6] Tablas MotorIA
echo ""
echo "[6] MotorIA..."
if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c \
    "SELECT 1 FROM pg_namespace WHERE nspname='motor_ia';" 2>/dev/null | grep -q 1; then
    ok "Esquema motor_ia existe"
else
    fail "Esquema motor_ia no existe"
    FALLOS=$((FALLOS+1))
fi

# [7] Servicios systemd
echo ""
echo "[7] Servicios systemd..."
if command -v systemctl &>/dev/null; then
    for svc in sinagersat-api motoria-embeddings; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            ok "$svc: activo"
        elif systemctl is-enabled --quiet "$svc" 2>/dev/null; then
            warn "$svc: habilitado pero no corriendo"
        else
            warn "$svc: no instalado como servicio"
        fi
    done
else
    warn "systemctl no disponible"
fi

# [8] API HTTP
echo ""
echo "[8] API HTTP (puerto 8000)..."
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/" 2>/dev/null | grep -q "200\|30[0-9]"; then
    ok "API respondiendo en http://127.0.0.1:8000"
else
    warn "API no responde en :8000 (¿arrancada? systemctl start sinagersat-api)"
fi

if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8000/docs" 2>/dev/null | grep -q "200"; then
    ok "Swagger UI en http://127.0.0.1:8000/docs"
fi

# [9] MotorIA embeddings
echo ""
echo "[9] MotorIA embeddings (puerto 8001)..."
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:8001/docs" 2>/dev/null | grep -q "200"; then
    ok "Embeddings respondiendo en :8001"
else
    warn "Embeddings no responden en :8001 (¿arrancado? systemctl start motoria-embeddings)"
fi

# RESUMEN
echo ""
echo "================================================"
if [ "$FALLOS" -eq 0 ]; then
    echo -e "  ${VERDE}DESPLIEGUE VERIFICADO CORRECTAMENTE${SIN_COLOR}"
    echo ""
    echo "  API:       http://localhost:8000"
    echo "  Docs:      http://localhost:8000/docs"
    echo "  Embeddings: http://localhost:8001/docs"
    echo "  BD:        postgresql://sinagersat@127.0.0.1:5432/db_sinagersat"
else
    echo -e "  ${ROJO}$FALLOS FALLO(ES) — revisar arriba${SIN_COLOR}"
fi
echo "================================================"
echo ""

exit $FALLOS
