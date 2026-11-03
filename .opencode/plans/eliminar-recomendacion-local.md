# Eliminar `recomendacion_local` completamente

## Objetivo
Borrar la tabla `sinb.recomendacion_local` y todo lo relacionado (endpoints, schemas, catálogo `categoria_recomendacion`, consultas de estadísticas, docs). La recomendación **solo** entra por `POST /api/v2/sinb/pronostico-largo` (ya implementado y funcional).

## Verificación previa (hecha)
- Ninguna vista ni FK externa referencia `sinb.recomendacion_local`.
- Única FK saliente: `recomendacion_local_id_categoria_fkey` → `sinb.categoria_recomendacion`.
- `sinb.categoria_recomendacion` (8 filas) solo es referenciada por `recomendacion_local` → se borra también.
- **NO se toca**: `sinb.recomendacion` (2), `sinb.comportamiento_recomendacion` (10), `sinb.pronostico_largo_recomendacion` (91) y su puente. Son el camino del POST.
- `scripts/migrate_pronostico_largo_relacional.py` escribe en `sinb.recomendacion`, no en `recomendacion_local` → no se modifica.

## Pasos

### 1. Migración SQL nueva
Crear `database/migrations/v2.33.0_eliminar_recomendacion_local.sql`:
```sql
ALTER TABLE sinb.recomendacion_local DROP CONSTRAINT IF EXISTS recomendacion_local_id_categoria_fkey;
DROP TABLE IF EXISTS sinb.recomendacion_local;
DROP TABLE IF EXISTS sinb.categoria_recomendacion;
```
No editar migraciones ya aplicadas (v2.26.0, v2.30.0, v2.32.0).

### 2. `api/sinb/router_v2.py`
- Eliminar los **12 endpoints** (líneas ≈702–969, bloque completo "RECOMENDACIONES LOCALES" + "CATEGORÍAS DE RECOMENDACIÓN"):
  - `GET/POST /recomendacion-local`, `GET/PUT/DELETE /recomendacion-local/{id}` (5)
  - `GET/POST /recomendacion-local/{id}/comentarios` (2)
  - `GET /indicador-natural/{id}/recomendaciones` (1)
  - `GET/POST /PUT/DELETE /categoria-recomendacion[/{id}]` (4)
- Quitar imports (líneas 25–26): `RecomendacionLocalCreate/Update/Response`, `CategoriaRecomendacionCreate/Response`.
- Quitar `TAGS_RECOMENDACIONES` (línea 52) — queda sin uso.
- Ranking `GET /observadores/ranking`: eliminar la rama
  `UNION ALL SELECT id_usuario_subio, 'recomendaciones', COUNT(*) FROM sinb.recomendacion_local WHERE estado='ACTIVO'` (≈1021), la columna `COALESCE(...tipo='recomendaciones'...)` (≈1053) y la línea `Recomendaciones` del docstring.
- Borrar el bloque **muerto** alcanzable tras `return` en `ranking_observadores` (líneas ≈1057–1094, "resumen estadístico de actividad") que también consulta `recomendacion_local`.

### 3. `api/sinb/schemas.py`
Eliminar (líneas ≈442–496): `RecomendacionLocalCreate`, `RecomendacionLocalUpdate`, `RecomendacionLocalResponse`, `CategoriaRecomendacionCreate`, `CategoriaRecomendacionResponse`.

### 4. Documentación `DOCUMENTACION_SINB.md`
- Tablas: línea 309 (`recomendacion_local`), 382 (mención v2.30.0), 396–397 (mermaid), 875 (offline).
- Endpoints: filas 655–659 ("Recomendaciones (12)"), sección 7.7 (776–786), 906 (conteo 85 → 73).
- Aclarar en 7.7 que la recomendación vive en `POST/GET /pronostico-largo` → `recomendaciones[]`.

### 5. Reinicio y pruebas
```bash
sudo systemctl daemon-reload && sudo systemctl restart sinagersat-api
sleep 8; ps aux | grep -c spawn_main   # debe ser 5 (1 master + 4 workers)
```
Pruebas:
- `GET /api/v2/sinb/recomendacion-local` → **404**
- `GET /api/v2/sinb/categoria-recomendacion` → **404**
- `GET /api/v2/sinb/indicador-natural/{id}/recomendaciones` → **404**
- `GET /api/v2/sinb/observadores/ranking` → 200, sin campo `recomendaciones`
- `GET /api/v2/sinb/pronostico-largo` → 200, 91 recomendaciones intactas
- Swagger `http://10.10.0.24:8000/docs` → sin la sección "SINB > Recomendaciones"

## Riesgos
- Ningún cliente consume hoy `/recomendacion-local` (confirmado: sin referencias en el repo).
- Las 104 filas se pierden de forma irreversible → respaldar antes:
  `pg_dump -t sinb.recomendacion_local -t sinb.categoria_recomendacion db_sinagersat > backups/...`
