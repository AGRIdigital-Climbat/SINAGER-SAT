#!/bin/bash

# Script de inicio robusto para SINAGERSAT API
# Evita bloqueos usando múltiples workers y validaciones

set -e  # Salir en caso de error

echo "=========================================="
echo "INICIANDO API SINAGERSAT - MODO SEGURO"
echo "=========================================="

# 1. Matar procesos anteriores
echo "[1/6] Deteniendo procesos anteriores..."
pkill -f "uvicorn api.main" 2>/dev/null || true
sleep 2

# 2. Liberar puerto 8000
echo "[2/6] Liberando puerto 8000..."
fuser -k 8000/tcp 2>/dev/null || true
sleep 2

# 3. Validar configuración
echo "[3/6] Validando configuración..."
cd /home/prosuco/SINAGERSAT/BaseData
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ ERROR: Virtual environment no encontrado"
    exit 1
fi

# Crear directorio de logs
mkdir -p /var/log/sinagersat

# 4. Iniciar con workers
echo "[4/6] Iniciando API con 4 workers..."
source venv/bin/activate
nohup uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --timeout-keep-alive 30 \
    --limit-concurrency 100 \
    --backlog 200 \
    > /var/log/sinagersat/api.log 2>&1 &

API_PID=$!
echo "PID de API: $API_PID"

# 5. Validar inicio
echo "[5/6] Validando inicio..."
sleep 5

if ps -p $API_PID > /dev/null 2>&1; then
    echo "[6/6] Verificando endpoints..."
    
    # Test rápido a endpoint
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v2/sinb/pronostico-digital/consultar?id_municipio=41503" --max-time 10 || echo "000")
    
    if [ "$RESPONSE" = "200" ]; then
        echo "=========================================="
        echo "✅ API INICIADA CORRECTAMENTE"
        echo "=========================================="
        echo ""
        echo "Configuración:"
        echo "  - Workers: 4"
        echo "  - Timeout keep-alive: 30s"
        echo "  - Max conexiones: 100"
        echo "  - Backlog: 200"
        echo ""
        echo "Endpoints:"
        echo "  - Swagger: http://localhost:8000/docs"
        echo "  - API Base: http://localhost:8000/api/v2"
        echo ""
        echo "Logs: /var/log/sinagersat/api.log"
        echo "PID: $API_PID"
        echo "=========================================="
    else
        echo "⚠️  API inició pero endpoints no responden (HTTP $RESPONSE)"
        echo "Ver logs: tail -100 /var/log/sinagersat/api.log"
        exit 1
    fi
else
    echo "=========================================="
    echo "❌ ERROR: API no pudo iniciar"
    echo "=========================================="
    echo "Ver logs: tail -100 /var/log/sinagersat/api.log"
    exit 1
fi
