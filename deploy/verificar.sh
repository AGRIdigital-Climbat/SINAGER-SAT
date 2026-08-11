#!/bin/bash
# ================================================================
#  EDAN - VERIFICAR BASE DE DATOS
#  Comprueba que todo funciona correctamente
#
#  Uso:  bash verificar.sh
# ================================================================

DB="db_sinagersat"
USER="sinagersat"
PW="12345678"

VERDE="\033[0;32m"
ROJO="\033[0;31m"
SIN_COLOR="\033[0m"

ok()   { echo -e "  ${VERDE}[OK]${SIN_COLOR} $1"; }
fail() { echo -e "  ${ROJO}[FAIL]${SIN_COLOR} $1"; }

echo ""
echo "================================================"
echo "  EDAN - VERIFICACION DE BASE DE DATOS"
echo "================================================"
echo ""

# --------------------------------------------------
# [1] Conexion
# --------------------------------------------------
echo "[1] Conexion..."
if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT 'OK' as conexion;" >/dev/null 2>&1; then
    ok "Conexion exitosa"
else
    fail "No se pudo conectar a la base de datos"
    echo "  Verifica que PostgreSQL este corriendo: pg_isready"
    exit 1
fi

# --------------------------------------------------
# [2] Schemas
# --------------------------------------------------
echo ""
echo "[2] Schemas disponibles:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema')
ORDER BY schema_name;
" 2>/dev/null

# --------------------------------------------------
# [3] Detectar modo de esquema (edan.xxx vs public.xxx)
# --------------------------------------------------
SCHEMA_MODE=$(PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -t -A -c "
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='edan' AND table_name='edan')
    THEN 'edan'
    WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='edan')
    THEN 'public'
    ELSE 'unknown'
END;
" 2>/dev/null)

echo ""
echo "[3] Modo de esquema detectado: $SCHEMA_MODE"

if [ "$SCHEMA_MODE" = "edan" ]; then
    echo ""
    echo "    --- EDAN (schema edan) ---"
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
    SELECT 'Departamentos' as tabla, COUNT(*) as total FROM shared.departamento
    UNION ALL SELECT 'Provincias', COUNT(*) FROM shared.provincia
    UNION ALL SELECT 'Municipios', COUNT(*) FROM shared.municipio
    UNION ALL SELECT 'Tipos Evento', COUNT(*) FROM edan.tipo_evento
    UNION ALL SELECT 'Grupos Etarios', COUNT(*) FROM edan.grupo_etario
    UNION ALL SELECT 'Servicios Basicos', COUNT(*) FROM edan.servicio_basico
    UNION ALL SELECT 'Categorias Proteccion', COUNT(*) FROM edan.categoria_proteccion
    UNION ALL SELECT 'Ayuda Humanitaria', COUNT(*) FROM edan.ayuda_humanitaria
    ORDER BY tabla;
    " 2>/dev/null

    echo ""
    echo "    --- USUARIOS (schema usuarios) ---"
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
    SELECT table_name, 0 as registros
    FROM information_schema.tables
    WHERE table_schema = 'usuarios'
    ORDER BY table_name;
    " 2>/dev/null

    echo ""
    echo "    --- REA (schema rea) ---"
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
    SELECT 'Reportes Eventos' as tabla, COUNT(*) as total FROM rea.reporte_evento
    UNION ALL SELECT 'Estados', COUNT(*) FROM rea.estado_reporte
    UNION ALL SELECT 'Categorias', COUNT(*) FROM rea.afectacion_categoria
    ORDER BY tabla;
    " 2>/dev/null

elif [ "$SCHEMA_MODE" = "public" ]; then
    echo ""
    echo "    --- PUBLIC ---"
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
    SELECT 'Departamentos' as tabla, COUNT(*) as total FROM catalogo_departamento
    UNION ALL SELECT 'Provincias', COUNT(*) FROM catalogo_provincia
    UNION ALL SELECT 'Municipios', COUNT(*) FROM catalogo_municipio
    UNION ALL SELECT 'Tipos Evento', COUNT(*) FROM catalogo_tipo_evento
    UNION ALL SELECT 'Grupos Etarios', COUNT(*) FROM catalogo_grupo_etario
    UNION ALL SELECT 'Servicios Basicos', COUNT(*) FROM catalogo_servicio_basico
    UNION ALL SELECT 'Categorias Proteccion', COUNT(*) FROM catalogo_categoria_proteccion
    UNION ALL SELECT 'Ayuda Humanitaria', COUNT(*) FROM catalogo_ayuda_humanitaria
    ORDER BY tabla;
    " 2>/dev/null
else
    fail "No se detectaron tablas EDAN en ningun schema"
fi

# --------------------------------------------------
# [4] Total de tablas
# --------------------------------------------------
echo ""
echo "[4] Total de tablas:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT table_schema, COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
GROUP BY table_schema
ORDER BY table_schema;
" 2>/dev/null

# --------------------------------------------------
# [5] Foreign Keys
# --------------------------------------------------
echo ""
echo "[5] Foreign Keys:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT COUNT(*) as total_fk
FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY';
" 2>/dev/null

# --------------------------------------------------
# [6] Indices
# --------------------------------------------------
echo ""
echo "[6] Indices:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT COUNT(*) as total_indices
FROM information_schema.statistics
WHERE index_schema NOT IN ('pg_catalog','information_schema');
" 2>/dev/null

# --------------------------------------------------
# [7] Muestra departamentos
# --------------------------------------------------
echo ""
echo "[7] Departamentos:"
if [ "$SCHEMA_MODE" = "edan" ]; then
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT id, codigo_ine, nombre FROM shared.departamento ORDER BY id;" 2>/dev/null
else
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT id, codigo_ine, nombre FROM catalogo_departamento ORDER BY id;" 2>/dev/null
fi

# --------------------------------------------------
# [8] Estructura tabla principal
# --------------------------------------------------
echo ""
echo "[8] Estructura tabla edan:"
if [ "$SCHEMA_MODE" = "edan" ]; then
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "\d edan.edan" 2>/dev/null | head -30
else
    PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "\d edan" 2>/dev/null | head -30
fi

echo ""
echo "================================================"
echo "  VERIFICACION COMPLETADA"
echo "================================================"
echo ""
echo "  Conexion:"
echo "    PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 10.10.10.220"
echo ""
