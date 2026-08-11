# Sincronización EDAN — Modelo en PostgreSQL (offline-first)

Documenta la **lógica de sincronización tal como quedó definida en la base de
datos** (migraciones `v1.8.0` y `v1.9.0`), preparada para el flujo
**AppSheet (móvil) ↔ servidor ↔ PC (web)**. No documenta endpoints: la capa
API se ajustará al modelo en una etapa posterior.

## Objetivo

Un formulario EDAN se captura en campo con la app (sin conexión), se sube al
servidor y se completa/visualiza en la PC. El mismo documento debe poder
editarse **desde cualquier extremo** y converger sin duplicados ni pérdidas,
usando la regla simple **last-write-wins (LWW)**.

## Modelo de datos

### Campos de sync en `edan.edan`

| Campo | Tipo | Rol en la sincronización |
|---|---|---|
| `id_edan` | BIGSERIAL PK | Identidad del documento **en el servidor** |
| `id_local` | VARCHAR(64) UNIQUE | UUID generado en el dispositivo (AppSheet). **Identidad estable del documento entre dispositivos**; el servidor lo mapea a `id_edan` |
| `fecha_creacion` | TIMESTAMP | Auditoría, `NOW()` del servidor (no participa en sync) |
| `fecha_modificacion` | TIMESTAMP | **Autoridad de tiempo**. `NOW()` al escribir. Soporta pull incremental y LWW |
| `pendiente_actualizacion` | BOOLEAN (FALSE) | Flag "dirty": cambios locales sin subir |
| `pendiente_eliminacion` | BOOLEAN (FALSE) | Tombstone de borrado |
| `id_usuario_ugr` | INTEGER FK | **Dueño del pull** del EDAN (rol 6, UGR Municipio). Índice `idx_edan_sync_pull` |
| `id_usuario_alcalde` | INTEGER FK | Alcalde (rol 8) que registró/edita desde la app |
| `id_estado` | INTEGER FK (1) | Ciclo de vida (`borrador`, `enviado`, `aprobado`, `rechazado`, `cerrado`). `borrador` = id_estado 1 |

### Campos de sync en `edan.edan_localidades`

| Campo | Tipo | Rol en la sincronización |
|---|---|---|
| `id_edan_localidad` | SERIAL PK | Identidad **en el servidor** |
| `id_local` | VARCHAR(64) UNIQUE | UUID del dispositivo. Identidad estable de la localidad |
| `id_edan` | BIGINT FK (SET NULL) | EDAN padre |
| `id_usuario` | INTEGER FK | **Dueño del pull** de la localidad. Índice `idx_edan_localidades_sync_pull` |
| `fecha_modificacion` | TIMESTAMP | Autoridad de tiempo (mismo uso que en la cabecera) |
| `pendiente_actualizacion` | BOOLEAN (FALSE) | Flag "dirty" |
| `pendiente_eliminacion` | BOOLEAN (FALSE) | Tombstone de borrado |

### Columnas eliminadas (no se usan)

| Columna | Motivo |
|---|---|
| `sincronizado` (ambas tablas) | Redundante: el flag de "no subido" es `pendiente_actualizacion` |
| `es_borrador` (edan) | Derivable: `id_estado = 1` |
| `id_server` (ambas tablas) | El id del servidor es `id_edan` / `id_edan_localidad` |
| `intentos_sync`, `ultimo_error` (edan) | La cola/reintentos se manejan en el cliente |
| `id_usuario` (edan.edan) | Sustituido por `id_usuario_ugr` + `id_usuario_alcalde` |

## Reglas de la sincronización

### 1. Identidad: el `id_local` manda

- El dispositivo genera `id_local = UUID` al crear el documento y nunca lo cambia.
- **Dedupe** por `id_local`: si el servidor ya tiene una fila con ese `id_local`,
  es el mismo documento (aunque el dispositivo aún no conozca su `id_edan`).
- El `id_edan` asignado por el servidor se le devuelve al dispositivo como
  referencia, pero **nunca** se usa como clave de comparación para sync.
- El índice único **parcial** `edan_id_local_key` (`WHERE id_local IS NOT NULL`)
  garantiza que un `id_local` no pueda existir dos veces.

### 2. Autoridad de tiempo: `fecha_modificacion`

- El **servidor es la autoridad de tiempo**: cada escritura fija
  `fecha_modificacion = NOW()`.
- La `fecha_modificacion` que envía el cliente solo sirve para saber **qué
  versión conoce** y detectar versiones atrasadas.
- **LWW**: si dos extremos editan el mismo documento, gana la versión con
  `fecha_modificacion` más reciente.

### 3. Flags de estado

- `pendiente_actualizacion = TRUE` → "tengo cambios que aún no subí" (dirty).
  Se limpia al aplicar el push.
- `pendiente_eliminacion = TRUE` → **tombstone**: borrado local que debe
  propagarse al otro extremo. El pull devuelve el documento con este flag y el
  otro extremo lo marca/oculta.
- Para no retroceder el reloj al marcar un borrado, se usa
  `fecha_modificacion = GREATEST(fecha_modificacion, NOW())`.

### 4. Dueño del pull

| Unidad | Dueño | Criterio |
|---|---|---|
| EDAN (cabecera) | `id_usuario_ugr` (rol 6) | El UGR ve/descarga todos los EDANs de su municipio |
| Localidad | `id_usuario` | La localidad viaja con su dueño |

Índices que soportan el pull incremental por dueño:

- `idx_edan_sync_pull (id_usuario_ugr, fecha_modificacion)`
- `idx_edan_localidades_sync_pull (id_usuario, fecha_modificacion)`

### 5. Push (subida) de un EDAN

1. Buscar por `id_local`.
2. **No existe** → INSERT (la cabecera conserva el `id_local` y la
   `fecha_modificacion` del cliente como referencia). Se limpian los flags.
3. **Existe** → comparar la `fecha_modificacion` que envía el cliente con la
   del servidor:
   - cliente más nuevo → UPDATE (LWW) y se devuelve el documento convergido;
   - cliente más viejo → **no se aplica** (conflicto): se devuelve la versión
     vigente para que el dispositivo la adopte.
4. **Tombstone** (`pendiente_eliminacion`) → marcar el registro en el servidor
   (no eliminación física), manteniendo la fecha con `GREATEST`.
5. El resultado siempre devuelve el documento **convergido** que el dispositivo
   debe guardar como su versión local.

### 6. Localidades dentro del EDAN

- El push de un EDAN reemplaza **el set completo de localidades** de la cabecera
  (delete + reinsert) preservando la identidad de sync de las que ya existían:
  `id_local`, `id_usuario`, `fecha_modificacion`, estado.
- De esta forma re-sincronizar el mismo EDAN **no duplica** localidades y no
  pierde el estado de las existentes.
- Toda escritura sobre una localidad de un EDAN **bump** la cabecera
  (`fecha_modificacion = NOW()`, `pendiente_actualizacion = TRUE`) para que el
  pull la detecte como modificada.

## Vínculo REA ↔ EDAN

- `edan.edan` ya no guarda `id_reporte_rea`: el vínculo vive en
  `rea.reporte_evento.id_edan` (FK inversa → `edan.edan.id_edan`, `ON DELETE
  SET NULL`, índice `idx_reporte_id_edan`).
- Un REA solo puede generar **un** EDAN; un EDAN puede agrupar varios REAs.
- Al crear/actualizar/borrar un EDAN la capa API mantiene ese vínculo en
  sincronía (el REA anterior se desvincula a NULL si el origen cambia).

## Escenarios de sincronización

### A. Solo app (el PC no participa)

```
app crea EDAN offline (id_local = UUID)
  → con conexión: push → servidor INSERT + asigna id_edan
  → app guarda el documento convergido (id_local + id_edan + flags limpios)
```

- El documento vive solo en el móvil y el servidor; el pull posterior de la app
  devuelve el mismo documento sin duplicados.

### B. Solo web (la app no participa)

```
PC crea/edita EDAN en el servidor (web, con conexión)
  → servidor genera id_local (UUID) para el documento
  → pull incremental por id_usuario_ugr devuelve el documento
```

- La web nunca ve flags de sync: `pendiente_actualizacion/eliminacion` quedan
  en FALSE. El `id_local` generado por el servidor asegura que el documento
  pueda adoptarse después desde la app.

### C. App → Web → App (captura en campo, cierre en PC)

```
1. app crea EDAN offline (id_local = X)
2. push → servidor crea id_edan, devuelve convergido (X → id_edan)
3. PC hace pull incremental → recibe el EDAN X y lo completa (PUT)
4. app hace pull → recibe la versión del PC (misma X, ahora actualizada)
5. app intenta re-push con su versión vieja → LWW: gana el PC, la app
   recibe la versión vigente y la adopta
```

### D. Web → App → Web (carga en web, edición en campo)

```
1. PC crea EDAN (servidor genera id_local = Y)
2. app hace pull → recibe el EDAN Y y lo edita offline
3. app push → LWW: si la app es más nueva, gana; si es más vieja, la app
   adopta la versión del servidor
4. PC hace pull → recibe la versión de la app
```

### E. Borrado propagado (tombstone)

```
app borra EDAN offline → pendiente_eliminacion = TRUE
  → push → servidor marca el registro (fecha con GREATEST)
  → PC hace pull → ve el documento con pendiente_eliminacion = TRUE
    y lo oculta/marca como eliminado
```

## Consultas útiles (PostgreSQL)

```sql
-- Documentos sucios (cambios locales sin subir)
SELECT id_edan, id_local, pendiente_actualizacion, fecha_modificacion
FROM edan.edan
WHERE pendiente_actualizacion = TRUE;

-- Tombsones (borrados pendientes de propagar)
SELECT id_edan, id_local, pendiente_eliminacion
FROM edan.edan
WHERE pendiente_eliminacion = TRUE;

-- Pull incremental de un UGR (marca de último sync = fecha_desde)
SELECT e.*
FROM edan.edan e
WHERE e.id_usuario_ugr = :id_ugr
  AND e.fecha_modificacion >= :fecha_desde
ORDER BY e.fecha_modificacion DESC;

-- Detectar duplicados de id_local (no debería haber: índice único parcial)
SELECT id_local, COUNT(*) FROM edan.edan
WHERE id_local IS NOT NULL GROUP BY id_local HAVING COUNT(*) > 1;

-- EDANs que provienen de un reporte REA (vínculo inverso)
SELECT r.id_reporte, r.comunidad, e.id_edan, e.id_local
FROM rea.reporte_evento r
LEFT JOIN edan.edan e ON e.id_edan = r.id_edan;
```

## Resumen de reglas

| Regla | Decisión |
|---|---|
| Dedupe | `id_local` (UUID), nunca `id_edan` |
| Conflictos | **LWW** por `fecha_modificacion`; el servidor es autoridad de tiempo |
| Push atrasado | No aplica; responde el documento vigente para que el cliente lo adopte |
| Borrado | Tombstone (`pendiente_eliminacion`), nunca DELETE físico |
| Dueño del pull | EDAN → `id_usuario_ugr`; Localidad → `id_usuario` |
| Re-sync | Idempotente (no duplica) y preserva identidad/estado de localidades |
| Subir | `pendiente_actualizacion` = TRUE hasta aplicar el push |
