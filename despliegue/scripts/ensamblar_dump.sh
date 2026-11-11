#!/bin/bash
# ================================================================
#  SINAGERSAT - ENSAMBLAR DUMP POR PARTES
#  Concatena las partes db_*.sql.gz.?? y descomprime para obtener
#  el dump .sql listo para 02_restaurar_bd.sh.
#
#  Uso: bash despliegue/scripts/ensamblar_dump.sh
# ================================================================
set -e

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESPL_DIR="$(dirname "$SCRIPT_DIR")"
DUMP_DIR="$DESPL_DIR/dump"

echo ""
echo "================================================"
echo "  SINAGERSAT - ENSAMBLAR DUMP POR PARTES"
echo "================================================"
echo ""

# [1] Buscar dump .sql ya existente
EXISTE_SQL=$(ls -1t "$DUMP_DIR"/db_sinagersat_*.sql 2>/dev/null | head -1)
if [ -n "$EXISTE_SQL" ] && [ -s "$EXISTE_SQL" ]; then
    ok "Ya existe dump SQL: $(basename "$EXISTE_SQL") ($(du -h "$EXISTE_SQL" | cut -f1))"
    echo "  No hace falta ensamblar. Para regenerar desde partes, borra ese .sql antes."
    exit 0
fi

# [2] Buscar partes
echo "[1/4] Buscando partes del dump..."
PARTES=$(ls -1 "$DUMP_DIR"/db_sinagersat_*.sql.gz.[0-9][0-9] 2>/dev/null | sort)
if [ -z "$PARTES" ]; then
    # también aceptar sufijos tipo .aa .ab (split alfabético)
    PARTES=$(ls -1 "$DUMP_DIR"/db_sinagersat_*.sql.gz.[a-z][a-z] 2>/dev/null | sort)
fi

if [ -z "$PARTES" ]; then
    fail "No se encontraron partes en $DUMP_DIR/"
    echo "  Esperado: db_sinagersat_YYYYMMDD_HHMMSS.sql.gz.00 .01 .02 ..."
    exit 1
fi

NUM_PARTES=$(echo "$PARTES" | wc -l)
ok "Partes encontradas: $NUM_PARTES"
for p in $PARTES; do
    echo "    $(basename "$p") ($(du -h "$p" | cut -f1))"
done

# [3] Concatenar
echo ""
echo "[2/4] Concatenando partes..."
BASE=$(echo "$PARTES" | head -1 | sed 's/\.[0-9][0-9]$//; s/\.[a-z][a-z]$//')
TMP_GZ="${BASE}.tmp"
cat $PARTES > "$TMP_GZ"
ok "Concatenado: $(basename "$TMP_GZ") ($(du -h "$TMP_GZ" | cut -f1))"

# Validar que es gzip válido
if ! gzip -t "$TMP_GZ" 2>/dev/null; then
    fail "El archivo concatenado no es un gzip válido — partes incompletas o corruptas"
    rm -f "$TMP_GZ"
    exit 1
fi
ok "gzip válido (integridad verificada)"

# [4] Descomprimir
echo ""
echo "[3/4] Descomprimiendo..."
SQL_OUT="${TMP_GZ%.tmp}"
SQL_OUT="${SQL_OUT%.gz}"
# nombre final coherente: db_sinagersat_*.sql
if [[ "$SQL_OUT" != *.sql ]]; then
    SQL_OUT="${SQL_OUT}.sql"
fi

gunzip -c "$TMP_GZ" > "$SQL_OUT"
rm -f "$TMP_GZ"
ok "Dump generado: $(basename "$SQL_OUT") ($(du -h "$SQL_OUT" | cut -f1))"

# [5] Validar contenido
echo ""
echo "[4/4] Validando contenido..."
if grep -q "CREATE EXTENSION IF NOT EXISTS postgis" "$SQL_OUT" 2>/dev/null; then
    ok "Incluye PostGIS"
else
    warn "NO se encontró CREATE EXTENSION postgis — verificar dump"
fi

if grep -q "CREATE EXTENSION IF NOT EXISTS vector" "$SQL_OUT" 2>/dev/null; then
    ok "Incluye pgvector"
else
    warn "NO se encontró CREATE EXTENSION vector"
fi

ESQUEMAS=$(grep -oP "CREATE SCHEMA \K\w+" "$SQL_OUT" 2>/dev/null | sort -u | tr '\n' ' ')
if [ -n "$ESQUEMAS" ]; then
    ok "Esquemas: $ESQUEMAS"
fi

echo ""
echo "================================================"
echo -e "  ${VERDE}DUMP ENSAMBLADO${SIN_COLOR}"
echo "================================================"
echo "  Archivo: $SQL_OUT"
echo ""
echo "  Siguiente: sudo bash despliegue/scripts/02_restaurar_bd.sh"
echo ""
