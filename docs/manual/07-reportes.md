# 07 · Reportes

> Qué reportes ofrece hoy el sistema, cómo obtenerlos y qué está pendiente.

## 1. Estado actual (importante)

| Tipo de reporte | Estado |
|---|---|
| **Reportes agregados en JSON** (resúmenes, totales, desgloses) | ✅ Disponibles |
| **Reportes geográficos GeoJSON** (para mapas) | ✅ Disponibles |
| **Reportes descargables (.xlsx / .pdf)** | ❌ **No implementados** |
| **Generación automática por programación (cron)** | ❌ **No implementada** |

> El requisito de "generación automática de al menos 3 reportes" **queda pendiente** y está documentado en [../../docs/INFORME_ENTREGA.md](../INFORME_ENTREGA.md). Este capítulo describe lo que puede hacerse **hoy**.

## 2. Reportes disponibles

### 2.1 EDAN (daños)

| Reporte | Endpoint |
|---|---|
| Resumen general de daños | `GET /api/v2/edan/reportes/resumen` |
| Daños por geografía | `GET /api/v2/edan/reportes/geografico` |
| Daños agrícolas | `GET /api/v2/edan/reportes/agricultura` |
| Daños pecuarios | `GET /api/v2/edan/reportes/pecuario` |
| Resumen por municipio | `GET /api/v2/edan/localidades/municipio/{id}/resumen` |
| Mis reportes | `GET /api/v2/edan/reportes/mis-reportes` |

### 2.2 RIDA

| Reporte | Endpoint |
|---|---|
| Formularios con familias e integrantes | `GET /api/v2/rida/empadronamiento/formularios/{id}` |
| Listado de formularios por geografía/estado | `GET /api/v2/rida/empadronamiento/formularios` |
| Solicitudes por etapa/modalidad | `GET /api/v2/rida/solicitudes` |
| Eventos con sus localidades | `GET /api/v2/rida/eventos`, `GET /api/v2/rida/evento/{id}/localidades` |
| Necesidades por familia/localidad | `GET /api/v2/rida/necesidades/...` |
| Búsqueda de personas | `GET /api/v2/rida/empadronamiento/personas/buscar` |

### 2.3 Población y ambiente

| Reporte | Endpoint |
|---|---|
| Población censo 2024 (nacional → municipio) | `GET /api/v2/shared/censo/poblacion/...` |
| Pronósticos y su verificación | `GET /api/v2/sinb/reporte/pronosticos` |
| Estadísticas NDVI | `GET /api/v2/ndvi/estadisticas/resumen` |
| Auditoría de uso del sistema | `GET /api/v2/usuarios/auditoria` |

## 3. Cómo obtener un reporte

**Paso 1 — Autenticar**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"USER","contrasena":"PASS"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])")
```

**Paso 2 — Consultar**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/edan/reportes/resumen?id_departamento=7" > reporte.json
```

**Paso 3 — Exportar localmente (opcional)**

Mientras no exista export en el servidor, puede convertirse el JSON en CSV/Excel en el equipo del usuario:

```bash
python3 - <<'EOF'
import json, csv
d = json.load(open('reporte.json'))
data = d['data']
if isinstance(data, dict): data = [data]
cols = list(data[0].keys())
with open('reporte.csv','w',newline='',encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(data)
print('reporte.csv generado con', len(data), 'filas')
EOF
```

> Para Excel: abrir el CSV con Excel/LibreOffice o usar `pandas`/`openpyxl` si están disponibles en el equipo.

## 4. Filtrar para que el reporte sea útil

Casi todos los reportes admiten filtros geográficos jerárquicos:

| Parámetro | Ejemplo |
|---|---|
| `id_departamento` | `7` (Santa Cruz) |
| `id_provincia` | `701` |
| `id_municipio` | `70101` |
| `fecha_desde` / fechas | según endpoint |
| `skip`, `limit` | paginación (máx. 1000) |

La combinación debe ser jerárquica: un municipio con su provincia y departamento correctos; si no, la API responde `400 Inconsistencia geográfica`.

## 5. Reporte para impresión (vía navegador)

La documentación interactiva de la API permite generar un "informe" legible sin código:

1. Abre `http://<servidor>:8000/docs/v2`.
2. Ejecuta el endpoint de reporte con tus filtros (`Authorize` con tu token).
3. Copia la respuesta JSON o usa la impresión del navegador (`Ctrl+P`) sobre la página de resultados.

## 6. Trabajo pendiente

| Pendiente | Descripción |
|---|---|
| `GET .../reportes/empadronamiento?format=xlsx\|pdf` | Reporte de población empadronada |
| `GET .../reportes/necesidades?format=xlsx\|pdf` | Necesidades por categoría/artículo |
| `GET .../reportes/eventos?format=xlsx\|pdf` | Avance por evento RIDA |
| Publicación automática por cron | Generación periódica en `uploads/reports/` |
| `GET /api/v2/rida/indicadores` | KPIs agregados de RIDA |

Estos ítems forman parte del alcance comprometido y se detallan en [../INFORME_ENTREGA.md](../INFORME_ENTREGA.md).

## 7. Autoevaluación

- [ ] Puedo obtener el resumen de daños de mi departamento.
- [ ] Sé convertir un reporte JSON a CSV en mi equipo.
- [ ] Sé exactamente qué reportes de archivo aún no existen.

---

**Anterior:** [06 · Indicadores](06-indicadores.md) · **Siguiente:** [08 · Offline y sincronización](08-offline-y-sincronizacion.md)
