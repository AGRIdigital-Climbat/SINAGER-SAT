# 🔧 Solución de Bloqueos en APIs - SINAGERSAT

## ⚠️ PROBLEMA IDENTIFICADO

### Síntomas
- APIs devuelven error 500 sin logs
- Servidor se "congela" temporalmente
- Conexiones se quedan en timeout
- Procesos uvicorn mueren inesperadamente

### Causa Raíz
**UVICORN SIN WORKERS** - Cuando se inicia sin `--workers`, uvicorn corre en modo single-threaded:
```bash
# ❌ MAL - Un solo hilo, se bloquea con cada request
uvicorn api.main:app --host 0.0.0.0 --port 8000

# ✅ BIEN - 4 workers, maneja múltiples requests simultáneos
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Por qué ocurre el bloqueo
1. **Request 1**: Consulta SQL lenta (ej: buscar comunidad en 21,175 registros con `ST_Distance`)
2. **Worker**: Se queda bloqueado esperando la respuesta de PostgreSQL
3. **Request 2, 3, 4...**: No pueden ser atendidos porque el único worker está ocupado
4. **Resultado**: Error 500 o timeout

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Iniciar con Múltiples Workers

**Comando correcto:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Beneficios:**
- 4 requests simultáneos pueden ser procesados
- Si 1 worker se bloquea, los otros 3 siguen funcionando
- Mejor uso de CPU multi-core

### 2. Optimizar Consultas SQL

**Query de comunidad más cercana (LENTA):**
```sql
-- ❌ MAL - Calcula distancia para TODAS las 21,175 comunidades
SELECT codigo_ine, nombre, lat, lon, id_municipio,
       ST_Distance(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), geom) as distancia
FROM shared.comunidades
ORDER BY distancia
LIMIT 1;
```

**Query optimizado (RÁPIDO):**
```sql
-- ✅ BIEN - Usa índice espacial y acota la búsqueda
SELECT codigo_ine, nombre, lat, lon, id_municipio
FROM shared.comunidades
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
    0.1  -- Búsqueda en radio de ~11km
)
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
LIMIT 1;
```

**Índices requeridos:**
```sql
-- Índice espacial en geom
CREATE INDEX IF NOT EXISTS idx_comunidades_geom 
ON shared.comunidades USING GIST (geom);

-- Índice en codigo_ine para búsquedas exactas
CREATE INDEX IF NOT EXISTS idx_comunidades_codigo_ine 
ON shared.comunidades (codigo_ine);

-- Índice compuesto para queries comunes
CREATE INDEX IF NOT EXISTS idx_comunidades_municipio 
ON shared.comunidades (id_municipio, codigo_ine);
```

### 3. Agregar Timeouts a Consultas

**En service.py:**
```python
# Configurar timeout para consultas lentas
from sqlalchemy import text

# Timeout de 30 segundos para consultas de comunidades
result = _row(db, text("SET statement_timeout = '30s'"))

# Query de comunidad
comunidad = _row(db, """
    SELECT codigo_ine, nombre, lat, lon, id_municipio
    FROM shared.comunidades
    WHERE codigo_ine = :codigo_ine
""", {"codigo_ine": codigo_ine})

# Resetear timeout
result = _row(db, text("SET statement_timeout = DEFAULT"))
```

### 4. Usar Caché para Datos Estáticos

**Para comunidades y municipios:**
```python
# Caché en memoria (se reinicia con la API)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_comunidad_by_codigo(codigo_ine: str):
    # Consulta a BD solo la primera vez
    return _row(db, """
        SELECT codigo_ine, nombre, lat, lon, id_municipio
        FROM shared.comunidades
        WHERE codigo_ine = :codigo_ine
    """, {"codigo_ine": codigo_ine})
```

## 📋 SCRIPT DE INICIO ROBUSTO

**Archivo:** `/home/prosuco/SINAGERSAT/BaseData/start_api_safe.sh`

```bash
#!/bin/bash

# Script de inicio robusto para SINAGERSAT API
# Evita bloqueos usando múltiples workers y validaciones

set -e  # Salir en caso de error

echo "=========================================="
echo "INICIANDO API SINAGERSAT - MODO SEGURO"
echo "=========================================="

# 1. Matar procesos anteriores
echo "[1/5] Deteniendo procesos anteriores..."
pkill -f "uvicorn api.main" 2>/dev/null || true
sleep 2

# 2. Liberar puerto 8000
echo "[2/5] Liberando puerto 8000..."
fuser -k 8000/tcp 2>/dev/null || true
sleep 2

# 3. Validar configuración
echo "[3/5] Validando configuración..."
cd /home/prosuco/SINAGERSAT/BaseData
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ ERROR: Virtual environment no encontrado"
    exit 1
fi

# 4. Iniciar con workers
echo "[4/5] Iniciando API con 4 workers..."
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
echo "[5/5] Validando inicio..."
sleep 5

if ps -p $API_PID > /dev/null 2>&1; then
    echo "✅ API INICIADA CORRECTAMENTE"
    echo ""
    echo "Configuración:"
    echo "  - Workers: 4"
    echo "  - Timeout keep-alive: 30s"
    echo "  - Max conexiones: 100"
    echo "  - Backlog: 200"
    echo ""
    echo "Logs: /var/log/sinagersat/api.log"
    echo "PID: $API_PID"
else
    echo "❌ ERROR: API no pudo iniciar"
    echo "Ver logs: tail -100 /var/log/sinagersat/api.log"
    exit 1
fi

echo "=========================================="
```

## 🔍 MONITOREO Y DEBUGGING

### Verificar Workers Activos
```bash
# Ver procesos uvicorn
ps aux | grep "uvicorn api.main" | grep -v grep

# Deberías ver 4 procesos:
# - 1 master process
# - 3 worker processes
```

### Logs en Tiempo Real
```bash
tail -f /var/log/sinagersat/api.log | grep -E "ERROR|WARNING|timeout"
```

### Conexiones Activas a BD
```bash
# Ver consultas activas
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat -c "
SELECT 
    pid,
    state,
    now() - query_start as duration,
    left(query, 100) as query
FROM pg_stat_activity 
WHERE state = 'active' 
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC
LIMIT 10;
"
```

### Test de Carga Básica
```bash
# Test con 10 requests simultáneos
for i in {1..10}; do
    curl -s "http://localhost:8000/api/v2/sinb/pronostico-comunidad/02417371843-M" &
done
wait

# Verificar que todos respondieron
# Si hay errores 500, revisar logs
```

## 📊 BENCHMARK ESPERADO

| Configuración | Requests/seg | Error Rate | Latencia p95 |
|---------------|--------------|------------|--------------|
| 1 worker (sin --workers) | ~10 | 5-10% | 2-5s |
| 4 workers | ~40 | <1% | <500ms |
| 4 workers + caché | ~100 | <1% | <200ms |
| 4 workers + índices + caché | ~200 | <0.1% | <100ms |

## ✅ CHECKLIST DE PREVENCIÓN

- [ ] API siempre inicia con `--workers 4` mínimo
- [ ] Índices espaciales creados en tablas grandes
- [ ] Timeouts configurados en queries lentos
- [ ] Caché implementado para datos estáticos
- [ ] Monitoreo de logs activo
- [ ] Alertas configuradas para error rate > 1%

---

**Última actualización:** 2026-10-05  
**Autor:** SINAGERSAT Team  
**Referencias:**
- [Uvicorn Performance](https://www.uvicorn.org/deploy/#number-of-workers)
- [PostgreSQL Spatial Indexes](https://postgis.net/workshops/postgis-intro/indexing.html)
