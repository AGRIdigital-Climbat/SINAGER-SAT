# RIDA — Motor de necesidades (v2.61.0, alineación/documentación)

> **Esquema/módulo:** `rida` / ayuda humanitaria (necesidades).  
> **Migración:** **YA EXISTE** (no crear): `database/migrations/v2.61.0_motor_necesidades.sql` y espejo `despliegue/migraciones/v2.61.0_motor_necesidades.sql` (idénticos, idempotentes, `IF NOT EXISTS`/`BEGIN..COMMIT`). Si ya fue aplicada, se ignora sin efecto adverso.  
> **Rama/commit:** `migraciones` (este paquete alinea documentación).

## 1. Objetivo
Calcular necesidades por familia a partir de reglas configurables (en lugar de solo carga manual), evaluadas sobre la población familiar, con trazabilidad (`fuente`, `id_regla_necesidad`).

## 2. Base de datos (v2.61.0, ya versionada)
- **`rida.regla_necesidad`**: `nombre`, `criterio_aplicacion` (`POR_FAMILIA`|`POR_INTEGRANTE`|`POR_CONDICION_ESPECIAL`), `id_categoria_ayuda` (FK RESTRICT), `id_articulo` (FK RESTRICT), `cantidad_base` (≥0), `dias_duracion` (>0, NULL=1), `condiciones` JSONB objeto (`gestante`,`discapacidad`,`edad_min_dias`,`edad_max_dias`,`sexo` M/F), `prioridad`, `orden`, `activo`, timestamps. Índices `idx_regla_necesidad_activo`, `idx_regla_necesidad_categoria`.
- **`rida.necesidad`** (ALTER): `fuente` (`manual`|`motor`, default `manual`), `id_regla_necesidad` FK → `rida.regla_necesidad` `ON DELETE SET NULL`. Índices `idx_necesidad_fuente`, `idx_necesidad_id_regla_necesidad`, y único parcial `uq_necesidad_motor_familia_articulo` `(id_familia,id_articulo)` donde `fuente='motor'` y artículo no nulo.
- No siembra reglas (configuración inicial de operaciones).

## 3. API / lógica (ya en repo)
- Motor/CRUD: `api/ayuda_humanitaria/motor_necesidades.py`, `api/ayuda_humanitaria/router.py`, `schemas.py`, `service.py`.
- Endpoints (prefijo ayuda humanitaria):
  - `GET/POST /api/v2/ayuda-humanitaria/reglas-necesidad` (filtros `activo`, `criterio_aplicacion`, `id_categoria_ayuda`)
  - `GET/PUT/DELETE /api/v2/ayuda-humanitaria/reglas-necesidad/{id}` (DELETE → 409 si ya generó necesidades)
  - `POST /api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades/preview` (sin persistir, cualquier etapa)
  - `POST /api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades` (persiste; solo `ENVIADA`/`EN_APROBACION`)
- Reglas: `POR_FAMILIA` exige `condiciones={}`; `POR_CONDICION_ESPECIAL` exige ≥1 filtro; claves desconocidas → 422. Fórmula `ceil(cantidad_base × (dias_duracion or 1) × poblacion_familia)` (sin mín/máx); unidad desde `cat_articulo`. Colisión de artículo por familia: suma, conserva regla de menor `(prioridad,orden,id)`.
- Persistencia: reemplaza necesidades manuales de las **categorías cubiertas** por familia; categorías sin regla se conservan. Respuesta: `familias`, `articulos_distintos`, `unidades`, `manuales_reemplazadas`, `motoras_eliminadas`.

## 4. Archivos alineados en este cambio (documentación)
| Archivo | Cambio |
|---|---|
| `Documentacion-Base-Datos-RIDA.md` | Tabla `regla_necesidad` (v2.61.0), columnas `fuente`/`id_regla_necesidad` en `necesidad`, migración v2.61.0 en listado, conteo rutas RIDA. |
| `docs/manual/04-necesidades.md` | § Motor de necesidades (v2.61.0): endpoints, reglas/condiciones, fórmula, comportamiento de persistencia y errores. |
| `APROBACIONES_RIDA.md`, `AYUDA_HUMANITARIA_BACKEND.md`, `docs/manual/05-solicitudes-workflow.md` | Notas de compatibilidad/shim y contrato relacionado (alineación documental). |
| `PROPUESTA_MOTOR_CALCULO_NECESIDADES.md` | Propuesta/diseño (histórico del motor), versionada como referencia. |

## 5. Replicación
1. Aplicar migración si falta (idempotente, segura si ya existe):
   ```bash
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/v2.61.0_motor_necesidades.sql
   # o despliegue/scripts/actualizar.sh (usa espejo en despliegue/migraciones/)
   ```
2. Actualizar código/docs y reiniciar API si aplica.

## 6. Verificación
```sql
SELECT to_regclass('rida.regla_necesidad');
SELECT column_name FROM information_schema.columns WHERE table_schema='rida' AND table_name='necesidad' AND column_name IN ('fuente','id_regla_necesidad');
```
```bash
# preview (cualquier etapa, scope válido)
curl -X POST "$API/api/v2/ayuda-humanitaria/expedientes/$ID/motor-necesidades/preview" -H "Authorization: Bearer $T"
# CRUD reglas
curl "$API/api/v2/ayuda-humanitaria/reglas-necesidad" -H "Authorization: Bearer $T"
```
- Escritura de reglas: roles 1/2; scope geográfico habitual del expediente (403 fuera de ámbito). Persistir motor → 409 si no está en `ENVIADA`/`EN_APROBACION`.
