# 06 · Indicadores

> Cómo consultar los indicadores del sistema: totales, población, daños, pronósticos y NDVI.
> Catálogo técnico completo: [../04-indicadores-y-reportes.md](../04-indicadores-y-reportes.md)

## 1. Antes de empezar

- [ ] Tienes tu `TOKEN` ([Cap. 01](01-acceso-y-roles.md)).
- [ ] Sabes que **todos los indicadores se devuelven en JSON** (hoy no hay ficheros descargables — ver [Cap. 07](07-reportes.md)).
- [ ] Recuerda que tu rol limita el alcance geográfico: si faltan datos, revisa §5.

## 2. Indicadores de población (Censo 2024)

| Endpoint | Devuelve |
|---|---|
| `GET /api/v2/shared/censo/poblacion/nacional` | Totales nacionales |
| `GET /api/v2/shared/censo/poblacion/departamentos` | Los 9 departamentos |
| `GET /api/v2/shared/censo/poblacion/provincias` | Las 113 provincias |
| `GET /api/v2/shared/censo/poblacion/municipios` | Los 343 municipios |
| `GET /api/v2/shared/censo/poblacion/departamento/{id}` | Detalle de un departamento |
| `GET /api/v2/shared/censo/poblacion/provincia/{id}` | Detalle de una provincia |
| `GET /api/v2/shared/censo/poblacion/municipio/{id}` | Detalle de un municipio |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/shared/censo/poblacion/departamentos"
```

## 3. Indicadores de daños (EDAN)

| Endpoint | Indicador |
|---|---|
| `GET /api/v2/edan/reportes/resumen` | Totales, localidades huérfanas vs consolidadas, población y familias damnificadas, desglose por estado |
| `GET /api/v2/edan/reportes/geografico` | Agrupado por departamento / provincia / municipio |
| `GET /api/v2/edan/reportes/agricultura` | Daños agrícolas |
| `GET /api/v2/edan/reportes/pecuario` | Daños pecuarios |
| `GET /api/v2/edan/localidades/municipio/{id}/resumen` | Resumen ejecutivo por municipio |

Filtros comunes: `id_departamento`, `id_provincia`, `id_municipio`, fechas.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/edan/reportes/resumen?id_departamento=7"
```

## 4. Indicadores RIDA

**Hoy no existe un endpoint consolidado de KPIs de RIDA** (está registrado como pendiente en [../INFORME_ENTREGA.md](../INFORME_ENTREGA.md)). Los datos se derivan de los listados:

| Pregunta | Endpoint |
|---|---|
| ¿Cuántos formularios hay y en qué estado? | `GET /api/v2/rida/empadronamiento/formularios` |
| ¿Cuántas familias e integrantes tiene una localidad? | `GET /api/v2/rida/empadronamiento/formularios/{id}` |
| ¿Cuántos eventos hay abiertos? | `GET /api/v2/rida/eventos?id_estado=1` |
| ¿Cuántas solicitudes están en revisión? | `GET /api/v2/rida/solicitudes?etapa=EN_REVISION` |
| ¿Qué necesita la población por categoría? | `GET /api/v2/rida/necesidades/formularios/{id}/necesidades` |

**Conteo rápido** (usando el campo `total` de la respuesta):

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/rida/solicitudes?etapa=EN_APROBACION" \
  | python3 -c "import sys,json; print('En aprobación:', json.load(sys.stdin)['total'])"
```

## 5. Indicadores ambientales (SINB y NDVI)

| Endpoint | Indicador |
|---|---|
| `GET /api/v2/sinb/reporte/pronosticos` | Pronósticos por tipo y estado; verificaciones (coinciden / no coinciden / pendientes) |
| `GET /api/v2/sinb/observadores/ranking` | Ranking de aportes de observadores |
| `GET /api/v2/sinb/galeria/indicadores-destacados` | Indicadores con más evidencias |
| `GET /api/v2/sinb/verificacion/pendientes` | Verificaciones pendientes |
| `GET /api/v2/ndvi/estadisticas/resumen` | Escenas, comunidades con datos, promedio NDVI 30 días, alertas activas |
| `GET /api/v2/ndvi/alertas` | Alertas NDVI |
| `GET /api/v2/ndvi/geojson/mapa-calor` | Mapa de calor (GeoJSON para mapas) |

## 6. Mapas (GeoJSON)

Para pintar un mapa sin procesar coordenadas:

- `GET /api/v2/shared/municipios/geojson` (con `bbox`)
- `GET /api/v2/shared/comunidades/geojson`, `GET /api/v2/shared/manzanos/geojson`
- `GET /api/v2/sinb/mapa/{comunidades,municipios,manzanos,pronosticos}/geojson`
- `GET /api/v2/ndvi/geojson/mapa-calor`

## 7. Interpretar la respuesta

Todos los endpoints devuelven el mismo envoltorio:

```json
{
  "success": true,
  "message": "Reporte resumen obtenido correctamente",
  "data": { ... },
  "total": 42
}
```

- `success: false` + `error_code` → hubo un error (ver [Cap. 10](10-faq-y-problemas.md)).
- `total` → número de registros (útil para conteos rápidos).

## 8. Si faltan datos

| Situación | Causa probable |
|---|---|
| Veo menos departamentos/municipios que otros | Tu rol te limita a tu departamento (9) o municipio (6, 7, 8) |
| Un endpoint devuelve lista vacía | No hay datos para ese filtro geográfico/fechas |
| `403` | Ver [Cap. 01 §3](01-acceso-y-roles.md) |

## 9. Autoevaluación

- [ ] Puedo obtener la población de mi municipio.
- [ ] Sé qué endpoint me da los damnificados por municipio.
- [ ] Sé por qué no existe aún un KPI único de RIDA y dónde está registrado ese pendiente.

---

**Anterior:** [05 · Solicitudes](05-solicitudes-workflow.md) · **Siguiente:** [07 · Reportes](07-reportes.md)
