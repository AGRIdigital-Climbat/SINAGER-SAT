# Flujo EDAN — Guía del UGR Municipio

**Proyecto:** SINAGER-SAT  
**Sección:** 4.2 — Base de Datos Nacional y Repositorio de GRD  
**Versión:** v2.8.0  
**Fecha:** 2026-08-18

---

## 1. Resumen del modelo de datos

### Tablas principales

```
edan.edan (padre — EDAN consolidado)
    │
    └── edan.edan_localidades (hijas — localidades independientes)
            │   FK: id_edan → edan.edan.id_edan (NULLABLE)
            │   ON DELETE SET NULL
            │
            ├── edan_localidades_impacto_poblacion (1:N)
            ├── edan_localidades_primera_respuesta (1:1)
            ├── edan_localidades_salud_establecimientos (1:N)
            ├── edan_localidades_salud_necesidades (1:1)
            ├── edan_localidades_danos_viales (1:N)
            ├── edan_localidades_danos_infra_publica (1:N)
            ├── edan_localidades_servicios_basicos (1:N)
            ├── edan_localidades_unidades_educativas (1:N)
            ├── edan_localidades_danos_vivienda (1:N)
            ├── edan_localidades_danos_agricultura (1:N)
            ├── edan_localidades_danos_pecuario (1:N)
            ├── edan_localidades_infra_productiva (1:N)
            ├── edan_localidades_proteccion (1:N)
            └── edan_localidades_necesidades_humanitarias (1:1)
```

### Campos que conectan localidades del mismo evento

| Campo | Tabla | Descripción |
|-------|-------|-------------|
| `id_municipio` | `edan_localidades` | Municipio donde ocurrió el daño |
| `id_tipo_evento` | `edan_localidades` | Tipo de evento (inundación, granizada, etc.) |
| `id_departamento` | `edan_localidades` | Departamento |
| `id_provincia` | `edan_localidades` | Provincia |
| `id_edan_localidad_estado` | `edan_localidades` | Estado del ciclo de vida |
| `id_edan` | `edan_localidades` | FK al EDAN padre (NULL = huérfana) |

### Estados de una localidad

| ID | nombre | Descripción |
|----|--------|-------------|
| 1 | Borrador | Creada, aún no enviada |
| 2 | Enviado UGR | Enviada al UGR municipal |
| 3 | Aprobado UGR | Aprobada por UGR, lista para consolidar |
| 4 | Rechazado UGR | Rechazada por UGR |
| 5 | Aprobado Ajuste UGR | Aprobada con correcciones |
| 6 | En revision UGR | En revisión por UGR |

### Identificadores

- **`id_edan_localidad`** (int, PK): asignado por el servidor, usado en todas las operaciones internas
- **`id_local`** (varchar, UUID del móvil): usado para deduplicación en sincronización offline-first
- **`id_edan`** (bigint, FK nullable): vincula la localidad con su EDAN padre. `NULL` = huérfana

---

## 2. Escenario de uso

### Actores

| Rol | ID | Función |
|-----|----|---------|
| Responsable Local | 7 | Líder de comunidad/barrio. Crea localidades independientes con los daños de su zona. |
| UGR Municipio | 6 | Encargado municipal. Revisa, aprueba y consolida localidades en un EDAN. |
| Alcalde | 8 | Consulta y aprobación de evaluaciones. Solo lectura. |

### Caso típico

1. Lluvias fuertes causan inundación en el municipio 70101 (Santa Cruz de la Sierra)
2. 3 líderes locales reportan daños desde sus comunidades:
   - Líder A (Comunidad X): daños viales + agricultura
   - Líder B (Barrio Y): daños en vivienda + salud
   - Líder C (Comunidad Z): solo reporta población afectada
3. 2 de las 3 localidades son del mismo municipio (70101) y mismo tipo de evento (Inundación)
4. El UGR revisa, aprueba las 2 del mismo municipio y las consolida en un EDAN municipal

---

## 3. Flujo paso a paso con APIs

### Paso 1: Líder Local crea su localidad

```
POST /api/v1/edan/localidades
```

**Body mínimo:**
```json
{
  "id_departamento": 7,
  "id_provincia": 701,
  "id_municipio": 70101,
  "id_tipo_evento": 1,
  "localidad": "Comunidad X",
  "fecha_evento": "2026-08-18",
  "total_poblacion_afectada": 45,
  "total_familias_afectadas": 12,
  "total_familias_damnificadas": 8
}
```

**Respuesta:** localidad creada con `id_edan=NULL` (huérfana), estado = Borrador.

**Si tiene daños con foto:**
```
POST /api/v1/edan/localidades/{id_localidad}/danos-viales/con-foto
POST /api/v1/edan/localidades/{id_localidad}/danos-agricultura/con-foto
... (9 endpoints con-foto disponibles)
```

**Alternativa offline-first:**
```
POST /api/v1/edan/localidades/sync
```

---

### Paso 2: UGR ve TODAS las localidades de su municipio

```
GET /api/v1/edan/localidades/municipio/70101
```

**Devuelve:** Todas las localidades del municipio (de TODOS los líderes), huérfanas + consolidadas, con **estructura completa** (14 secciones anidadas).

**Filtros disponibles:**

| Filtro | Tipo | Ejemplo | Descripción |
|--------|------|---------|-------------|
| `id_tipo_evento` | int | `?id_tipo_evento=1` | Filtrar por tipo de evento |
| `id_estado` | int | `?id_estado=1` | ID de estado específico |
| `estado` | str | `?estado=borrador` | Nombre de estado (ILIKE) |
| `solo_huerfanas` | bool | `?solo_huerfanas=true` | True=solo huérfanas, False=solo consolidadas |
| `id_usuario` | int | `?id_usuario=30` | Filtrar por usuario creador |
| `con_foto` | bool | `?con_foto=true` | Solo localidades con al menos una foto |
| `skip` | int | `?skip=0` | Offset de paginación |
| `limit` | int | `?limit=50` | Tamaño de página (max 500) |

**Ejemplo: ver solo huérfanas pendientes:**
```
GET /api/v1/edan/localidades/municipio/70101?solo_huerfanas=true
```

**Ejemplo: ver solo aprobadas por inundación:**
```
GET /api/v1/edan/localidades/municipio/70101?estado=aprobado&id_tipo_evento=1
```

---

### Paso 3: UGR ve resumen ejecutivo

```
GET /api/v1/edan/localidades/municipio/70101/resumen
```

**Respuesta:**
```json
{
  "total": 3,
  "huerfanas": 3,
  "consolidadas": 0,
  "total_poblacion_afectada": 120,
  "total_familias_afectadas": 35,
  "total_familias_damnificadas": 22,
  "por_estado": [
    { "estado": "Borrador", "cantidad": 1 },
    { "estado": "Enviado UGR", "cantidad": 1 },
    { "estado": "Aprobado UGR", "cantidad": 1 }
  ],
  "por_tipo_evento": [
    { "tipo_evento": "Inundación", "cantidad": 3 }
  ]
}
```

---

### Paso 4: UGR cambia estado de una localidad

```
PUT /api/v1/edan/localidades/{id_localidad}/estado
```

**Body:**
```json
{
  "id_edan_localidad_estado": 3
}
```

Estados comunes:
- `2` = Enviado UGR (recibida)
- `3` = Aprobado UGR (lista para consolidar)
- `4` = Rechazado UGR
- `6` = En revisión UGR

---

### Paso 5: UGR ve localidades listas para consolidar

```
GET /api/v1/edan/consolidar/pendientes?id_municipio=70101
```

**Agrupa** por (municipio, tipo_evento) y muestra:
- `cantidad_localidades`: cuántas hay en cada grupo
- `localidad_ids`: array de IDs listos para consolidar
- Totales agregados de población/familias

**Filtros:**

| Filtro | Tipo | Ejemplo | Descripción |
|--------|------|---------|-------------|
| `id_municipio` | int | `?id_municipio=70101` | Filtrar por municipio |
| `estado` | str | `?estado=aprobado` | Nombre de estado (ILIKE) |
| `id_estado` | int | `?id_estado=3` | ID de estado específico |

**Sin filtro:** muestra TODOS los huérfanos de todos los municipios.

---

### Paso 6: UGR consolida localidades en un EDAN

```
POST /api/v1/edan/consolidar
```

**Body:**
```json
{
  "id_municipio": 70101,
  "id_tipo_evento": 1,
  "localidad_ids": [46, 47]
}
```

**Validaciones:**
- Todas las localidades deben ser huérfanas (`id_edan IS NULL`)
- Todas deben estar en estado aprobado
- Todas deben ser del mismo municipio
- Todas deben ser del mismo tipo de evento

**Resultado:**
1. Crea fila en `edan.edan` con `codigo_edan` automático (formato: `70101/2026/001`)
2. Vincula cada localidad seteando `id_edan = <nuevo_id>`
3. Agrega totales de población/familias del EDAN desde las localidades
4. Retorna el EDAN completo con todas las localidades anidadas

---

### Paso 7: UGR ve EDANs consolidados

```
GET /api/v1/edan/?id_municipio=70101
```

**Filtros:** mismos que `_filtros_dep` (municipio, departamento, provincia, tipo evento, estado, fechas, etc.)

```
GET /api/v1/edan/{id_edan}
```

**Devuelve:** EDAN completo con todas las localidades y sus 14 secciones.

---

## 4. APIs del UGR — Resumen rápido

| # | Método | Endpoint | Función |
|---|--------|----------|---------|
| 1 | GET | `/edan/localidades/municipio/{id}` | Ver TODAS las localidades del municipio |
| 2 | GET | `/edan/localidades/municipio/{id}/resumen` | Resumen ejecutivo |
| 3 | PUT | `/edan/localidades/{id}/estado` | Cambiar estado de una localidad |
| 4 | GET | `/edan/consolidar/pendientes?id_municipio={id}` | Ver localidades para consolidar |
| 5 | POST | `/edan/consolidar` | Ejecutar consolidación |
| 6 | GET | `/edan/?id_municipio={id}` | Ver EDANs consolidados |
| 7 | GET | `/edan/{id}` | Ver EDAN completo |

**Total: 7 APIs** para el flujo completo del UGR.

---

## 5. APIs del Líder Local (rol 7)

| # | Método | Endpoint | Función |
|---|--------|----------|---------|
| 1 | POST | `/edan/localidades` | Crear localidad independiente |
| 2 | POST | `/edan/localidades/sync` | Sync offline-first (lote) |
| 3 | PUT | `/edan/localidades/{id}` | Editar localidad huérfana |
| 4 | PUT | `/edan/localidades/{id}/estado` | Cambiar estado |
| 5 | DELETE | `/edan/localidades/{id}` | Eliminar huérfana |
| 6 | GET | `/edan/localidades/mis-reportes` | Ver mis localidades |
| 7 | GET | `/edan/localidades/mis-resumen` | Resumen de mis localidades |
| 8 | POST | `/edan/localidades/{id}/danos-viales/con-foto` | Crear daño vial con foto |
| 9 | POST | `/edan/localidades/{id}/danos-infra-publica/con-foto` | Crear daño infraestructura |
| 10 | POST | `/edan/localidades/{id}/danos-vivienda/con-foto` | Crear daño vivienda |
| 11 | POST | `/edan/localidades/{id}/danos-agricultura/con-foto` | Crear daño agricultura |
| 12 | POST | `/edan/localidades/{id}/danos-pecuarios/con-foto` | Crear daño pecuario |
| 13 | POST | `/edan/localidades/{id}/salud-establecimientos/con-foto` | Crear daño salud |
| 14 | POST | `/edan/localidades/{id}/servicios-basicos/con-foto` | Crear daño servicios |
| 15 | POST | `/edan/localidades/{id}/unidades-educativas/con-foto` | Crear daño educación |
| 16 | POST | `/edan/localidades/{id}/infra-productiva/con-foto` | Crear daño infra productiva |

---

## 6. Descarga de fotos

Las fotos se almacenan en disco y se sirven por 2 mecanismos:

### Opción A: URL estática (sin autenticación)
```
GET /uploads/reports/{codigo_ine}/{filename}
```
Montada vía `StaticFiles` en `api/main.py`.

### Opción B: Descarga autenticada
```
GET /api/v1/upload/descargar/reports/{codigo_ine}/{filename}
```
Requiere JWT. Retorna `FileResponse` con Content-Type correcto.

### Galería de fotos por municipio
```
GET /api/v1/edan/municipios/{id_municipio}/fotos
```
Devuelve todas las fotos de evidencia del municipio, de las 9 tablas con soporte fotográfico.

---

## 7. Diagrama de flujo

```
┌─────────────────┐
│  LÍDER LOCAL     │  (rol 7)
│  Crea localidad  │
│  POST /localidades│
└────────┬────────┘
         │ id_edan = NULL (huérfana)
         │ estado = Borrador
         ▼
┌─────────────────┐
│  LÍDER LOCAL     │  Cambia estado a "Enviado UGR"
│  PUT /estado     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  UGR MUNICIPIO   │  (rol 6)
│  Ve localidades  │  GET /localidades/municipio/{id}
│  Ve resumen      │  GET /localidades/municipio/{id}/resumen
└────────┬────────┘
         │ Revisa cada localidad
         ▼
┌─────────────────┐
│  UGR APRUEBA     │  PUT /localidades/{id}/estado
│  id_estado = 3   │  (Aprobado UGR)
└────────┬────────┘
         ▼
┌─────────────────┐
│  UGR CONSOLIDA   │  Ve pendientes:
│                  │  GET /consolidar/pendientes?id_municipio={id}
│                  │
│                  │  Ejecuta:
│                  │  POST /consolidar
│                  │  { id_municipio, id_tipo_evento, localidad_ids }
└────────┬────────┘
         │ Crea EDAN padre, vincula localidades
         ▼
┌─────────────────┐
│  UGR CONSULTA    │  GET /edan/?id_municipio={id}
│  EDANs consolid. │  GET /edan/{id_edan}
└─────────────────┘
```

---

## 8. Notas técnicas

### Consolidación atómica
La consolidación es una transacción SQL: si alguna validación falla, se revierte todo. Las localidades nunca quedan parcialmente vinculadas.

### Código EDAN automático
Formato: `{id_municipio:06d}/{año}/{secuencial:03d}`  
Ejemplo: `070101/2026/001`, `070101/2026/002`

### Sincronización offline-first
Las localidades soportan patrón offline-first:
- `id_local` (UUID del cliente) para deduplicación
- `fecha_modificacion` para resolución de conflictos (last-write-wins)
- `pendiente_eliminacion` (tombstone) para propagar eliminaciones
- `pendiente_actualizacion` para señalizar cambios del servidor al cliente

### Índice de consolidación
```sql
CREATE INDEX idx_edan_localidades_consolidar
    ON edan.edan_localidades (id_municipio, id_tipo_evento, id_edan_localidad_estado);
```
Optimiza las queries de `consolidar/pendientes` y `localidades/municipio`.
