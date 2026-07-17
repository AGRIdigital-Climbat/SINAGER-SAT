#!/bin/bash
# ============================================
# EDAN - Iniciar Base de Datos PostgreSQL
# Arquitectura Multi-Esquema
# ============================================

PW="12345678"
USER="sinagersat"
DB="db_sinagersat"

echo "============================================"
echo "  EDAN - Iniciar Base de Datos PostgreSQL"
echo "  Arquitectura Multi-Esquema"
echo "============================================"
echo ""

# 1. Iniciar PostgreSQL
echo "[1/4] Iniciando PostgreSQL..."
sudo service postgresql start 2>/dev/null || sudo systemctl start postgresql 2>/dev/null
sleep 1

if pg_isready -q 2>/dev/null; then
    echo "  PostgreSQL corriendo"
else
    echo "  ERROR: No se pudo iniciar PostgreSQL"
    exit 1
fi

# 2. Verificar conexion
echo "[2/4] Verificando conexion..."
if PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema IN ('shared','edan','usuarios');" 2>/dev/null; then
    echo "  Conexion OK"
else
    echo "  ERROR: No se pudo conectar a la BD"
    exit 1
fi

# 3. Resumen de esquemas
echo "[3/4] Esquemas disponibles:"
PGPASSWORD=$PW psql -h 127.0.0.1 -U $USER -d $DB -c "
SELECT table_schema AS esquema, COUNT(*) AS tablas
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
GROUP BY table_schema
ORDER BY table_schema;
"

echo ""
echo "  shared:   geografia (departamentos, provincias, municipios)"
echo "  edan:     formularios EDAN (23 tablas)"
echo "  usuarios: usuarios, roles, sesiones, auditoria"
echo "  rida:     (futuro)"
echo "  sinb:     (futuro)"
echo "  recursos: (futuro)"

# 4. Mostrar info
echo "[4/4] Info de conexion:"
echo ""
echo "============================================"
echo "  CONFIGURACION COMPLETA"
echo "============================================"
echo ""
echo "  Base de datos: $DB"
echo "  Usuario:       $USER"
echo "  Contrasena:    $PW"
echo "  Host:          127.0.0.1"
echo "  Puerto:        5432"
echo ""
echo "  Conexion rapida:"
echo "  PGPASSWORD=$PW psql -U $USER -d $DB -h 127.0.0.1"
echo ""
echo "  DBeaver / pgAdmin:"
echo "  - Host: 127.0.0.1"
echo "  - Port: 5432"
echo "  - Database: $DB"
echo "  - User: $USER"
echo "  - Password: $PW"
echo ""
echo "Presiona ENTER para cerrar..."
read
