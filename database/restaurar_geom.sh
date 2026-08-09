#!/bin/bash
# ================================================================
#  SINAGERSAT - RESTAURAR GEOMETRÍA DE shared.municipio
#  Recupera la columna geom (PostGIS) de los 340 municipios SIN
#  tocar el resto de tablas ni esquemas.
#
#  Origen: bloque COPY shared.municipio del backup completo
#          database/backup_v1.2.8.sql (contiene la columna geom).
#
#  Uso:  bash restaurar_geom.sh
#  Requiere: PostgreSQL + paquete postgresql-16-postgis-3
# ================================================================
set -euo pipefail

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"
HOST="127.0.0.1"

ROJO="\033[0;31m"
VERDE="\033[0;32m"
AMARILLO="\033[1;33m"
SIN_COLOR="\033[0m"
ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
warn() { echo -e "  ${AMARILLO}[!]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[ERROR]${SIN_COLOR} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORIGEN="${1:-$SCRIPT_DIR/backup_v1.2.8.sql}"

if [ ! -f "$ORIGEN" ]; then
    fail "No se encuentra el backup origen: $ORIGEN"
fi

echo ""
echo "================================================"
echo "  RESTAURAR GEOMETRÍA shared.municipio"
echo "================================================"

# ── 1. PostGIS disponible ──
ok "Verificando extensión PostGIS..."
if ! PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -t -A -c "SELECT extversion FROM pg_extension WHERE extname='postgis';" | grep -q .; then
    fail "PostGIS no está activo en la BD. Ejecuta primero: migration_v1.5.0.sql"
fi
ok "PostGIS activo"

# ── 2. Extraer bloque COPY de municipio ──
echo ""
echo "[1/4] Extrayendo geometrías de $ORIGEN..."
python3 - "$ORIGEN" <<'EOF'
import sys
src = sys.argv[1]
out = "/tmp/municipio_geom_copy.dat"
filas = 0
inb = False
with open(src) as f:
    with open(out, "w") as o:
        for line in f:
            if line.startswith("COPY shared.municipio"):
                inb = True
                continue
            if inb:
                if line.startswith("\\."):
                    break
                o.write(line)
                filas += 1
print(out)
sys.stderr.write("filas=%d\n" % filas)
EOF
BLOQUE="/tmp/municipio_geom_copy.dat"
FILAS=$(grep -c $'\t' "$BLOQUE" || true)
ok "Bloque extraído: $FILAS municipios con geometría"

# ── 3. Cargar en tabla temporal y actualizar geom ──
echo ""
echo "[2/4] Creando tabla temporal y cargando geometrías..."
PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -q -c "
DROP TABLE IF EXISTS shared._municipio_geom_tmp;
CREATE TABLE shared._municipio_geom_tmp (
    id            INTEGER PRIMARY KEY,
    codigo_ine    VARCHAR(6),
    id_departamento INTEGER,
    id_provincia  INTEGER,
    nombre        VARCHAR(100),
    geom          geometry(MultiPolygon, 4326)
);
"
{ cat "$BLOQUE"; printf '\\.\n'; } | PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -q -c "\copy shared._municipio_geom_tmp FROM STDIN"
ok "Geometrías cargadas"

echo ""
echo "[3/4] Actualizando shared.municipio..."
PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -c "
UPDATE shared.municipio m
SET geom = t.geom
FROM shared._municipio_geom_tmp t
WHERE m.id = t.id;
" | tail -2

echo ""
echo "[4/4] Verificando..."
PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -c "
SELECT 'con_geom' AS estado, count(*) FROM shared.municipio WHERE geom IS NOT NULL
UNION ALL
SELECT 'sin_geom', count(*) FROM shared.municipio WHERE geom IS NULL;
"
PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -t -A -c "SELECT 'municipio 70101 SRID: ' || ST_SRID(geom) FROM shared.municipio WHERE id=70101;"

PGPASSWORD=$PW psql -h $HOST -U $USER -d $DB -q -c "DROP TABLE IF EXISTS shared._municipio_geom_tmp;"
rm -f "$BLOQUE"
echo ""
echo "================================================"
echo "  RESTAURACIÓN COMPLETADA"
echo "================================================"
