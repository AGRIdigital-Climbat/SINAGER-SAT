#!/bin/bash
# ================================================================
#  EDAN - TEST DE CONEXION
#  Verifica conexion basica a la BD
#
#  Uso:  bash test_conn.sh
# ================================================================

PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat -c "
SELECT 'Conexion OK' as estado, current_user as usuario, current_database() as base_datos;
" -c "
SELECT
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')) as total_tablas;
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "  La base de datos EDAN esta funcionando correctamente."
else
    echo ""
    echo "  ERROR: No se pudo conectar a la base de datos."
    echo "  Verifica que PostgreSQL este corriendo: pg_isready"
fi
