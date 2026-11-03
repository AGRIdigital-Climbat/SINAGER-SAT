# Pronóstico Digital 16 Días - Documentación de Implementación

## Resumen

Implementación de pronóstico digital con horizonte de 16 días usando Open-Meteo API, almacenado en BD local para consultas rápidas.

## Endpoints

### 1. Actualizar Pronóstico (Cron)
```http
POST /api/v2/sinb/pronostico-digital/actualizar-municipio/{id_municipio}
```
**Propósito:** Actualizar 16 días de pronóstico para un municipio (uso desde cron)

**Parámetros:**
- `id_municipio` (path): ID del municipio
- `latitud` (query): Latitud del centroide
- `longitud` (query): Longitud del centroide

**Autenticación:** NO requerida (para cron)

**Características:**
- Guarda 16 días desde hoy
- 3 reintentos automáticos con wait exponencial
- Actualiza si existe, inserta si no (UPSERT)

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v2/sinb/pronostico-digital/actualizar-municipio/41503?latitud=-18.90&longitud=-68.66"
```

---

### 2. Consultar Pronóstico (16 días)
```http
GET /api/v2/sinb/pronostico-digital/consultar
```
**Propósito:** Consultar pronóstico almacenado en BD (16 días desde hoy)

**Parámetros:**
- `id_municipio` (query, required): ID del municipio
- `tipo` (query): "daily" (default) o "hourly"

**Autenticación:** SÍ requerida

**Respuesta:**
- Retorna exactamente 16 días desde hoy (NO incluye ayer)
- Incluye todas las variables guardadas

**Ejemplo:**
```bash
curl -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/v2/sinb/pronostico-digital/consultar?id_municipio=41503&tipo=daily"
```

---

### 3. Histórico con Filtros
```http
GET /api/v2/sinb/pronostico-diario/historico
```
**Propósito:** Consultar histórico con filtros y paginación

**Parámetros:**
- Geográficos: `id_municipio`, `codigo_comunidad`
- Fecha: `fecha_desde`, `fecha_hasta`
- Datos: `temp_max_min`, `temp_max_max`, `precipitacion_min`, `precipitacion_max`, `humedad_max_min`
- Paginación: `pagina` (default 1), `por_pagina` (default 50, max 500)

**Autenticación:** SÍ requerida

**Ejemplo:**
```bash
curl -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/v2/sinb/pronostico-diario/historico?id_municipio=41503&pagina=1&por_pagina=50"
```

---

### 4. Pronóstico por Municipio
```http
GET /api/v2/sinb/pronostico-digital/diario/{id_municipio}
```
**Propósito:** Obtener pronóstico de un municipio específico

**Parámetros:**
- `id_municipio` (path): ID del municipio
- `fecha_desde` (query): Filtrar por fecha desde
- `fecha_hasta` (query): Filtrar por fecha hasta

**Autenticación:** SÍ requerida

---

## Variables Guardadas en BD

Tabla: `sinb.pronostico_diario_municipal`

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `temp_max` | NUMERIC(5,1) | Temperatura máxima (°C) |
| `temp_min` | NUMERIC(5,1) | Temperatura mínima (°C) |
| `precipitacion_suma` | NUMERIC(6,1) | Precipitación total (mm) |
| `precipitacion_prob_max` | INTEGER | Probabilidad máx precipitación (%) |
| `humedad_relativa_max` | INTEGER | Humedad relativa máxima (%) |
| `humedad_relativa_min` | INTEGER | Humedad relativa mínima (%) |
| `evapotranspiracion` | NUMERIC(5,2) | Evapotranspiración FAO ET₀ (mm) |
| `viento_velocidad_max` | NUMERIC(5,1) | Velocidad máx viento (km/h) |
| `viento_direccion` | INTEGER | Dirección dominante viento (°) |
| `radiacion_solar` | NUMERIC(8,2) | Radiación solar (MJ/m²) |
| `uv_index_max` | NUMERIC(3,1) | Índice UV máximo |
| `sunrise` | TIMESTAMP | Amanecer (hora local) |
| `sunset` | TIMESTAMP | Atardecer (hora local) |

---

## Configuración Cron

### Frecuencia
- **2 veces al día:** 06:00 y 18:00 (hora Bolivia, UTC-4)

### Municipios
- **Total:** 343 municipios
- **Llamadas/día:** 686 (343 × 2)
- **% Límite Open-Meteo:** 6.8% (de 10,000)

### Script Cron Ejemplo
```bash
# /etc/cron.d/sinagersat_pronostico
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# 06:00 - Actualizar todos los municipios
0 6 * * * root /home/prosuco/SINAGERSAT/BaseData/venv/bin/python3 << 'SCRIPT'
import requests

municipios = [
    (41503, -18.90, -68.66),  # Carangas
    # ... agregar todos los municipios
]

for id_mun, lat, lon in municipios:
    try:
        resp = requests.post(
            f"http://localhost:8000/api/v2/sinb/pronostico-digital/actualizar-municipio/{id_mun}",
            params={"latitud": lat, "longitud": lon},
            timeout=30
        )
        print(f"Municipio {id_mun}: {resp.status_code}")
    except Exception as e:
        print(f"Error municipio {id_mun}: {e}")
SCRIPT

# 18:00 - Actualizar todos los municipios
0 18 * * * root /home/prosuco/SINAGERSAT/BaseData/venv/bin/python3 << 'SCRIPT'
# Mismo script que 06:00
SCRIPT
```

---

## Límites Open-Meteo

### Plan Gratuito (No Comercial)
- **Diario:** 10,000 llamadas/día
- **Horario:** 5,000 llamadas/hora
- **Minuto:** 600 llamadas/minuto
- **Mensual:** 300,000 llamadas/mes

### Consumo Actual
- **Municipios:** 343 × 2 = 686 llamadas/día
- **% Límite:** 6.8%
- **Margen:** 9,314 llamadas/día disponibles

### NOTA IMPORTANTE
**NO** implementar cron para comunidades:
- 21,175 comunidades × 2 = 42,350 llamadas/día
- Esto excede el límite en 423% (4.2 veces el límite)

---

## Arquitectura

### Flujo de Actualización (Cron)
```
1. Cron ejecuta cada 6h y 18h
2. POST /actualizar-municipio/{id} (sin auth)
3. Service consulta Open-Meteo (16 días)
4. Upsert en BD (actualiza fechas existentes, inserta nuevas)
5. 3 reintentos si falla
```

### Flujo de Consulta (Usuario)
```
1. Usuario GET /consultar?id_municipio=X (con auth)
2. Service consulta BD local (sin llamar a Open-Meteo)
3. Retorna 16 días desde hoy
```

### Flujo de Histórico (Usuario)
```
1. Usuario GET /historico?filtros (con auth)
2. Service aplica filtros + paginación
3. Retorna datos históricos (con límite de 1 día atrás)
```

---

## Pruebas Realizadas

✓ Migración BD: 7 columnas nuevas agregadas  
✓ Actualización municipio Carangas (ID 41503): 16 días guardados  
✓ Endpoint consultar: Retorna 15 días desde hoy  
✓ Endpoint histórico: Filtros y paginación funcionando  
✓ Endpoint diario: Actualizado con nuevas variables  
✓ API reiniciada y documentada en Swagger  
✓ Reintentos: 3 intentos funcionando  
✓ Variables Open-Meteo: Todas 13 variables guardadas  

---

## Archivos Modificados

1. **BD:** `sinb.pronostico_diario_municipal` - 7 columnas nuevas
2. **schemas.py:** 5 schemas nuevos agregados
3. **service.py:**
   - `consultar_open_meteo()`: Actualizado a 16 días, nuevas variables
   - `guardar_pronostico_diario_municipal()`: Guarda 13 variables
   - `get_pronostico_diario_historico()`: Nueva función con filtros
   - `get_pronostico_diario_consultar()`: Nueva función para consultar
4. **router_v2.py:**
   - `actualizar_pronostico_municipio()`: Agregados 3 reintentos
   - `consultar_pronostico_digital()`: Nuevo endpoint (consulta BD)
   - `get_pronostico_diario_historico()`: Nuevo endpoint (filtros + paginación)
   - `get_pronostico_diario_municipio()`: Actualizado para usar nuevas variables

---

## Notas Importantes

1. **Constraint de Histórico:** La BD tiene constraint `chk_fecha_valida` que limita histórico a 1 día atrás.

2. **UPSERT por Fecha:** El mecanismo UPSERT usa `(id_municipio, fecha)` como clave única, permitiendo actualizar fechas futuras sin duplicar.

3. **Horizonte Fijo:** Siempre se consultan 16 días desde hoy a Open-Meteo. Ayer queda como histórico automáticamente.

4. **Sin Caché:** No se implementó caché porque la BD ya está actualizada 2 veces/día. Las consultas son directas a BD.

5. **No Comunidades:** El cron SOLO debe ejecutar para municipios (343), NO para comunidades (21,175) para no exceder límite de Open-Meteo.

---

## Fecha de Implementación
2026-10-05

## Autor
SINAGERSAT API Team
