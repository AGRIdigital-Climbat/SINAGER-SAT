# Plan: Documentación HTTP de `POST /api/v1/edan/localidades/sync`

## Contexto

El usuario reportó que al editar `id_tipo_evento` en la app Flutter y sincronizar, la BD no se actualiza.
**Investigación completada**: el servidor SÍ actualiza correctamente (testeado con `7051296/12345678`).
El problema real es la **falta de documentación clara** del contrato HTTP.

## Hallazgos

- `SINCRONIZACION.md` línea 5: *"No documenta endpoints: la capa API se ajustará al modelo en una etapa posterior"*
- `CONSOLIDACION_EDAN.md` sección 7: solo ~20 líneas sin ejemplos curl
- El comportamiento del servidor es correcto: UPDATE con `id_tipo_evento` funciona
- `proteccion.grupo` tiene CHECK constraint con valores específicos (documentar)

## Archivos a modificar

### 1. `docs/SINCRONIZACION.md` — Agregar sección completa después de línea 226

**Nueva sección: "Contrato HTTP de los endpoints de sincronización"** que incluya:

#### POST `/api/v1/edan/localidades/sync`

**Request:**
- Tabla completa de campos de `LocalidadCreate` (~40 campos organizados por categoría)
- Campos de sync: `id_local`, `fecha_modificacion`, `pendiente_actualizacion`, `pendiente_eliminacion`
- Secciones opcionales: 11 arrays + 3 objetos 1:1
- CHECK constraints: `proteccion.grupo`, `servicios_basicos.tipo`
- Nota sobre herencia de EDAN padre (`_inherit_localidad_header`)

**Response (5 escenarios con JSON):**
1. INSERT exitoso (`aplicado: true, conflicto: false`)
2. UPDATE exitoso (`aplicado: true, conflicto: false`)
3. Conflicto LWW (`aplicado: false, conflicto: true`)
4. Tombstone (`aplicado: true, tombstone: true`)
5. Error por item (`aplicado: false, error: "..."`)

**Curl examples:**
- Login + crear localidad completa con secciones
- Editar `id_tipo_evento` de 5→3
- Eliminar via tombstone

#### GET `/api/v1/edan/localidades/sync/pull`

**Request:** parámetros query (`fecha_desde`, `skip`, `limit`)

**Response:** estructura completa de `_build_localidad`

**Curl examples:**
- Pull completo
- Pull incremental
- Pull con paginación

#### Tabla de errores comunes

| Situación | Código HTTP | Comportamiento | Solución |
|-----------|-------------|----------------|----------|
| Token inválido | 401 | Rechazo | Re-login |
| Sin rol | 403 | Rechazo | Verificar rol |
| Conflicto LWW | 200 | `aplicado: false, conflicto: true` | Adoptar versión servidor |
| CHECK constraint inválido | 200 | Error en item | Usar valores válidos |

### 2. `docs/CONSOLIDACION_EDAN.md` — Expandir sección 7

Reemplazar las ~20 líneas actuales (líneas 589-612) con:
- Tabla resumen de los 4 sync endpoints
- Referencia a `SINCRONIZACION.md` para detalles completos
- Ejemplo curl paso a paso
- Tabla de errores

## Verificación

1. Ejecutar todos los curl examples con credenciales `7051296/12345678` y verificar que funcionan
2. Confirmar que la documentación refleja exactamente el comportamiento real del API
