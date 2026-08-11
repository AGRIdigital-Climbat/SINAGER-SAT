# SINAGERSAT — Base de Datos PostgreSQL (v1.3.0)

Arquitectura **Multi-Esquema** para el Sistema Nacional de Alerta Temprana y
Gestión de Riesgos (SINAGERSAT).

## Conexión

| Parámetro | Valor |
|---|---|
| **Host** | `localhost` (o `/var/run/postgresql` para socket Unix) |
| **Puerto** | `5432` |
| **Base de datos** | `db_sinagersat` |
| **Usuario** | `sinagersat` |
| **Contraseña** | `12345678` |

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost -p 5432
```

---

## Arquitectura Multi-Esquema

Una sola base de datos `db_sinagersat` con **8 esquemas** que separan responsabilidades:

```
PostgreSQL: db_sinagersat
├── shared      → Geografía (INE: 9 deptos, 112 provincias, 340 municipios, cultivos, pecuario)
├── usuarios    → Cuentas, roles, sesiones, permisos, auditoría
├── edan        → Formularios EDAN jerárquicos (cabecera + 14 sub-tablas por localidad)
├── rea         → Reportes de Eventos Adversos (captura rápida móvil)
├── repositorio → Repositorio de documentos PDF vinculados a EDAN (2 tablas)
├── rida        → (vacío - futuro)
├── sinb        → (vacío - futuro)
└── recursos    → (vacío - futuro)
```

**Total de tablas:** ~50  
**Foreign Keys:** ~50  
**Índices:** ~60  

Las consultas entre esquemas son igual de rápidas que entre tablas del mismo schema
(una sola conexión PostgreSQL, sin overhead de BDs separadas).

---

## Esquema `shared` — Geografía (INE Bolivia)

| Tabla | Registros | Descripción |
|---|---|---|
| `departamento` | 9 | Departamentos de Bolivia |
| `provincia` | 112 | Provincias |
| `municipio` | 340 | Municipios |
| `cultivo` | ~80 | Catálogo de cultivos agrícolas (SIIP) |
| `pecuario` | ~40 | Catálogo de especies pecuarias |

### Codificación INE

| Nivel | Formato | Ejemplo |
|---|---|---|
| Departamento | `DD` (2 dígitos) | `02` (La Paz) |
| Provincia | `DDPP` (4 dígitos) | `0204` (Aroma) |
| Municipio | `DDPPMM` (6 dígitos) | `020401` (Patacamaya) |

Los `id` son el valor numérico del `codigo_ine` (sin ceros a la izquierda).

### `shared.departamento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | (= valor numérico de codigo_ine) |
| `codigo_ine` | VARCHAR(2) UNIQUE | Código INE de 2 dígitos |
| `nombre` | VARCHAR(100) | Nombre del departamento |

### `shared.provincia`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | (= valor numérico de codigo_ine) |
| `codigo_ine` | VARCHAR(4) UNIQUE | Código INE de 4 dígitos |
| `id_departamento` | INTEGER FK | → shared.departamento.id |
| `nombre` | VARCHAR(100) | Nombre de la provincia |

### `shared.municipio`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | (= valor numérico de codigo_ine) |
| `codigo_ine` | VARCHAR(6) UNIQUE | Código INE de 6 dígitos |
| `id_departamento` | INTEGER FK | → shared.departamento.id |
| `id_provincia` | INTEGER FK | → shared.provincia.id |
| `nombre` | VARCHAR(100) | Nombre del municipio |
| `geom` | GEOMETRY(MultiPolygon, 4326) | Polígono (GeoJSON compatible) |

---

## Esquema `usuarios` — Gestión de Usuarios y Permisos

| Tabla | Descripción |
|---|---|
| `usuario` | Cuentas (credenciales, estado, contacto, ubicación) |
| `rol` | Catálogo de roles con jerarquía |
| `usuario_rol` | Asignación N:M usuarios ↔ roles |
| `aplicacion` | Catálogo de sistemas (EDAN, REA, REPOSITORIO) |
| `permiso_aplicacion` | Permisos por rol+aplicación+acción |
| `sesion` | Tokens JWT activos |
| `reset_contrasena` | Solicitudes de recuperación |
| `auditoria` | Log de acciones |

### `usuarios.usuario`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_usuario` | SERIAL PK | |
| `usuario` | VARCHAR(100) UNIQUE | Login |
| `contrasena` | VARCHAR(255) | Hash bcrypt |
| `nombre` | VARCHAR(200) | Nombre completo |
| `celular`, `carnet`, `comunidad` | VARCHAR | Datos de contacto |
| `id_departamento`, `id_provincia`, `id_municipio` | INTEGER FK | Ubicación |
| `activo` | BOOLEAN | Cuenta habilitada |

### Roles por defecto (jerarquía 1-5)

| id_rol | Nombre | Jerarquía |
|---|---|---|
| 1 | superadmin | 5 |
| 2 | admin | 4 |
| 3 | VIDECI Regional | 3 |
| 4 | UGR Sectores | 3 |
| 5 | DGR Gobernación | 3 |
| 6 | UGR Municipio | 2 |
| 7 | Responsable Local | 2 |
| 8 | Alcalde | 2 |
| 9 | VIDECI Departamental | 3 |

---

## Esquema `edan` — Formulario EDAN

Arquitectura **jerárquica por localidades**: un EDAN tiene una cabecera única y
una o varias **localidades** afectadas, cada una con sus **14 secciones** de
daños y necesidades como sub-tablas.

```
edan.edan  (cabecera 1)
   └── edan.edan_localidades  (1:N)
          ├── edan_localidades_impacto_poblacion     (1:N por rango etario)
          ├── edan_localidades_primera_respuesta     (1:1)
          ├── edan_localidades_salud_establecimientos(1:N)
          ├── edan_localidades_salud_necesidades     (1:1)
          ├── edan_localidades_danos_viales          (1:N)
          ├── edan_localidades_danos_infra_publica   (1:N)
          ├── edan_localidades_servicios_basicos     (1:N)
          ├── edan_localidades_unidades_educativas   (1:N)
          ├── edan_localidades_danos_vivienda        (1:N)
          ├── edan_localidades_danos_agricultura     (1:N)
          ├── edan_localidades_danos_pecuario        (1:N)
          ├── edan_localidades_infra_productiva      (1:N)
          ├── edan_localidades_proteccion            (1:N)
          └── edan_localidades_necesidades_humanitarias (1:1)
```

### `edan.edan` (cabecera)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan` | BIGSERIAL PK | ID único |
| `codigo_edan` | VARCHAR(30) UNIQUE | Código interno auto-generado |
| `id_departamento` | INTEGER FK | (deriva de id_municipio) |
| `id_provincia` | INTEGER FK | (deriva de id_municipio) |
| `id_municipio` | INTEGER FK NOT NULL | → shared.municipio.id |
| `id_tipo_evento` | INTEGER FK | → edan.tipo_evento |
| `id_estado` | INTEGER FK | → edan.estado_edan |
| `id_usuario_ugr` | INTEGER FK | UGR que creó (→ usuarios.usuario) |
| `id_usuario_alcalde` | INTEGER FK | Alcalde que validó (nullable) |
| `id_local` | VARCHAR(64) UNIQUE | UUID generado en móvil (offline-first) |
| `id_reporte_rea` | BIGINT FK | REA de origen (nullable) |
| `fecha_evento` | DATE | Fecha del evento |
| `hora_evento` | TIME | Hora del evento |
| `fecha_llenado` | DATE | Fecha de llenado |
| `total_poblacion_afectada` | INTEGER | |
| `total_familias_afectadas` | INTEGER | |
| `total_familias_damnificadas` | INTEGER | |
| `pendiente_eliminacion` | BOOLEAN | Soft-delete |
| `pendiente_actualizacion` | BOOLEAN | Bump desde localidades |
| `fecha_creacion`, `fecha_modificacion` | TIMESTAMP | Auditoría |

> Las columnas legacy `sincronizado`, `es_borrador`, `id_server` fueron
> **removidas** en la migración v1.7.0. La columna `estado` (VARCHAR) también
> fue removida (solo se conserva `id_estado` FK).

### `edan.edan_localidades` (tabla intermedia)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan_localidad` | SERIAL PK | |
| `id_edan` | BIGINT FK NULL | EDAN consolidado (NULL = huérfana) |
| `id_local` | VARCHAR(64) UNIQUE | UUID móvil |
| `id_tipo_localidad` | INTEGER FK | → edan.tipo_localidad |
| `id_edan_localidad_estado` | INTEGER FK | → edan.edan_localidades_estado |
| `id_tipo_evento` | INTEGER FK | → edan.tipo_evento |
| `id_departamento`, `id_provincia`, `id_municipio` | INTEGER FK | Ubicación |
| `id_usuario` | INTEGER FK | Usuario que creó |
| `localidad` | VARCHAR(200) | Nombre de la comunidad |
| `imp_poblacion`, `imp_salud`, `imp_infraestructura`, `imp_servicios`, `imp_educacion`, `imp_vivienda`, `imp_agropecuario`, `imp_proteccion`, `imp_necesidades` | BOOLEAN | Flags de secciones informadas |
| `total_poblacion_afectada`, `total_familias_afectadas`, `total_familias_damnificadas` | INTEGER | |
| `fecha_evento`, `fecha_llenado`, `fecha_modificacion` | DATE/TIMESTAMP | |
| `pendiente_actualizacion`, `pendiente_eliminacion` | BOOLEAN | Sync |

> Las columnas legacy `botiquines`, `afectado`, `via_puente` (en sub-tablas) y
> la columna denormalizada `nombre` (ahora `localidad`) fueron removidas en
> v1.7.0 / v2.0.0.

### Sub-tablas con geolocalización (v2.6.0)

A partir de la migración v2.6.0, las 8 sub-tablas de daños/servicios tienen
3 columnas adicionales:

| Columna | Tipo | Descripción |
|---|---|---|
| `fotografia` | VARCHAR(500) | Ruta del archivo subido (uploads/reports/{cod}/{cod}_{uid}_{ts}.jpg) |
| `coordenada_lat` | DECIMAL(10,8) | Latitud GPS |
| `coordenada_lon` | DECIMAL(11,8) | Longitud GPS |

Las 8 tablas son: `danos_viales`, `danos_infra_publica`, `danos_vivienda`,
`danos_agricultura`, `danos_pecuario`, `salud_establecimientos`,
`servicios_basicos`, `unidades_educativas`.

### Catálogos propios de EDAN

| Tabla | Registros | Descripción |
|---|---|---|
| `tipo_evento` | 8 | Tipos de evento adverso |
| `estado_edan` | 5 | Borrador / Enviado / Aprobado / Rechazado / Cerrado |
| `tipo_localidad` | 21 | Localidad / Comunidad / Ayllu / Marka / TIOC / OTB / etc. |
| `edan_localidades_estado` | 5 | Estados de la localidad (mismo ciclo) |

---

## Esquema `rea` — Reportes de Eventos Adversos

Captura rápida desde el móvil (líderes comunitarios) antes de la evaluación EDAN completa.

### `rea.estado_reporte`

5 estados: Pendiente, Revisado, Atendido, Cerrado, Rechazado.

### `rea.afectacion_categoria`

7 categorías: Población, Salud, Infraestructura, Servicios, Educación,
Vivienda, Agropecuario.

### `rea.reporte_evento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_reporte` | SERIAL PK | |
| `id_usuario` | INTEGER FK | Líder que reporta |
| `id_departamento`, `id_provincia`, `id_municipio` | INTEGER FK | Ubicación |
| `id_tipo_evento` | INTEGER FK | → edan.tipo_evento |
| `id_estado` | INTEGER FK | → rea.estado_reporte |
| `id_edan` | BIGINT FK | EDAN generado (nullable, ON DELETE SET NULL) |
| `comunidad` | VARCHAR(200) | |
| `fecha_evento` | DATE | |
| `coordenada_lat` | NUMERIC(10,8) | |
| `coordenada_lon` | NUMERIC(11,8) | |
| `fotografia` | VARCHAR(500) | Ruta de la foto (uploads/reports/...) |
| `descripcion` | TEXT | |

### `rea.reporte_afectacion` (tabla puente N:M)

PK compuesta: `(id_reporte, id_categoria)`.

### Relación bidireccional REA ↔ EDAN

- `edan.edan.id_reporte_rea` → REA origen (nullable, SET NULL al borrar REA)
- `rea.reporte_evento.id_edan` → EDAN generado (nullable, SET NULL al borrar EDAN)

Reglas:
- Un REA puede generar **un** EDAN; un EDAN puede agrupar **varios** REAs.
- Las FKs usan `ON DELETE SET NULL` para no eliminar el registro que sobrevive.
- API mantiene ambos vínculos sincronizados (POST/PUT de EDAN actualizan
  `id_edan` del REA correspondiente).

---

## Esquema `repositorio` — Documentos PDF vinculados a EDAN

Repositorio centralizado de PDFs (informes legales, técnicos, financieros,
leyes municipales, resoluciones, certificados de daño, etc.).

### `repositorio.tipo_documento` (catálogo)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_tipo_documento` | SERIAL PK | |
| `codigo` | VARCHAR(50) UNIQUE | Código interno (informe_legal, ley_municipal, ...) |
| `nombre` | VARCHAR(100) | Nombre legible |
| `descripcion` | TEXT | |
| `orden` | INTEGER | Orden de visualización |
| `activo` | BOOLEAN | Soft-delete |

**Tipos seed (v2.7.0):** `informe_legal`, `informe_tecnico`, `informe_financiero`,
`ley_municipal`, `resolucion_alcaldicia`, `certificado_dano`, `otro`.

### `repositorio.documentos` (tabla simplificada v2.7.3)

**16 columnas** (sin versionado, sin metadata JSONB, sin full-text).

| Campo | Tipo | Descripción |
|---|---|---|
| `id_documento` | BIGSERIAL PK | |
| `id_edan` | BIGINT FK NOT NULL | → edan.edan (CASCADE) |
| `id_tipo_documento` | INTEGER FK NOT NULL | → repositorio.tipo_documento |
| `id_departamento` | INTEGER FK | → shared.departamento (denormalizado) |
| `id_provincia` | INTEGER FK | → shared.provincia (denormalizado) |
| `id_municipio` | INTEGER FK | → shared.municipio (denormalizado) |
| `fecha_documento` | DATE | Fecha del documento (no de subida) |
| `nombre_documento` | VARCHAR(255) | Nombre normalizado (para búsqueda/filtrado) |
| `nombre_original` | VARCHAR(255) NOT NULL | Filename original subido |
| `path_archivo` | VARCHAR(500) NOT NULL | uploads/edan/documentos/{id_edan}/doc_{cod}_{uid}_{ts}.pdf |
| `tamano_bytes` | INTEGER NOT NULL | Tamaño (máx 50 MB) |
| `hash_sha256` | CHAR(64) | SHA256 del archivo (integridad/duplicados) |
| `id_usuario_subio` | INTEGER FK | → usuarios.usuario |
| `fecha_subida` | TIMESTAMP DEFAULT NOW() | |
| `activo` | BOOLEAN DEFAULT TRUE | Soft-delete |
| `observaciones` | TEXT | |

**Campos removidos en v2.7.3** (simplificación): `mime_type`, `version`,
`id_documento_padre`, `metadata` (JSONB), `ip_origen`, `texto_busqueda`,
vista `vw_documentos_activos`, índices `idx_documentos_version`,
`idx_documentos_consulta`, trigger `trg_update_texto_busqueda`,
función `fn_update_texto_busqueda`.

### Almacenamiento físico

Los PDFs se guardan en disco:
```
uploads/edan/documentos/{id_edan}/doc_{codigo_ine}_{id_usuario}_{timestamp}.pdf
```

Validaciones al subir (`api/upload.py:save_documento_pdf`):
- MIME type = `application/pdf`
- Extensión `.pdf`
- Tamaño máximo 50 MB
- Calcula SHA256 automáticamente

---

## Migraciones aplicadas (orden cronológico)

| Versión | Cambios principales |
|---|---|
| v1.2.0 – v1.3.x | Setup inicial: shared, usuarios, edan, rea |
| v1.4.0 | Modelo jerárquico por localidades (cabecera + sub-tablas) |
| v1.4.1 | `descripcion` en `edan.tipo_evento` |
| v1.4.2 | Permisos EDAN: solo rol 6 escribe |
| v1.4.3 | Sync offline-first (`id_local` + `idx_edan_sync_pull`) |
| v1.5.0 – v1.6.0 | Catálogos `tipo_localidad`, `estado_edan` |
| **v1.7.0** | Limpieza `edan.edan`: removidos `sincronizado`, `es_borrador`, `id_server`, `estado` (VARCHAR) |
| v1.8.0 – v2.4.0 | Refinamientos: FK `id_reporte_rea`, ajustes de constraints |
| **v2.5.0** | API EDAN alineada al esquema final (schemas Pydantic actualizados) |
| **v2.6.0** | Geolocalización: `fotografia` + `coordenada_lat`/`coordenada_lon` en 8 sub-tablas |
| **v2.7.0** | Esquema `repositorio` + tabla `tipo_documento` (catálogo con 7 tipos seed) |
| **v2.7.1** | Tabla `repositorio.documentos` (con full-text TSVECTOR+GIN, versionado, metadata JSONB) |
| **v2.7.2** | Metadata estructurada: `id_departamento`, `id_provincia`, `fecha_documento`, `nombre_documento` + remoción de full-text |
| **v2.7.3** | Simplificación: removidos `mime_type`, `version`, `id_documento_padre`, `metadata`, `ip_origen`, `vw_documentos_activos` |

---

## API REST — Endpoints consolidados (v1.3.0)

**Total: 163 endpoints** distribuidos en **20 grupos Swagger**.

### Tag `EDAN` (36 endpoints — colapsable)

Cabecera EDAN, reportes agregados, catálogos, sincronización, consolidar, fotos por municipio, cambio de estado.

| Método | Ruta | Descripción |
|---|---|---|
| GET / POST | `/api/v1/edan/` | Listar / crear EDAN |
| GET / PUT / DELETE | `/api/v1/edan/{id}` | Obtener / actualizar / eliminar |
| **PUT** | **`/api/v1/edan/{id}/estado`** | **Cambiar `id_estado` (roles 1-5, 9)** |
| POST / GET | `/api/v1/edan/sync`, `/edan/sync/pull` | Sync offline-first |
| GET | `/api/v1/edan/reportes/{mis-resumen,mis-reportes,resumen,geografico,agricultura,pecuario,localidades}` | Reportes agregados |
| GET / POST / PUT / DELETE | `/api/v1/edan/{tipo-evento,estados,tipo-localidad,localidades-estado}/{,/{id}}` | CRUD catálogos |
| POST | `/api/v1/edan/consolidar` | Consolidar localidades aprobadas en EDAN |
| GET | `/api/v1/edan/consolidar/pendientes` | Listar localidades listas para consolidar |
| GET | `/api/v1/edan/municipios/{id}/fotos` | Galería de evidencias fotográficas |
| GET | `/api/v1/rea/reportes/{id}/edan` | EDAN generado desde REA |

### Tag `EDAN_LOCALIDADES` (28 endpoints — colapsable)

Localidades del EDAN (CRUD anidado), sync móvil, mis-*, items con foto y coordenadas.

| Método | Ruta | Descripción |
|---|---|---|
| GET / POST / PUT / DELETE | `/api/v1/edan/{id}/localidades/{,/{id_localidad}}` | CRUD localidades |
| POST / GET | `/api/v1/edan/localidades/sync`, `/localidades/sync/pull` | Sync offline |
| PUT | `/api/v1/edan/localidades/{id_localidad}/estado` | Cambiar estado de localidad (roles 6, 7, 8) |
| **GET** | **`/api/v1/edan/localidades/mis-resumen`** | **Resumen de localidades huérfanas del usuario** |
| **GET** | **`/api/v1/edan/localidades/mis-reportes`** | **Lista de localidades huérfanas del usuario** |
| POST | `/api/v1/edan/localidades/{id_localidad}/{tipo}/con-foto` | Crear daño/servicio con foto+GPS (8 endpoints) |
| GET | `/api/v1/edan/localidades/{id_localidad}/{tipo}` | Listar items (8 endpoints) |

Los 8 tipos de daño/servicio con foto son: `danos-viales`, `danos-infra-publica`,
`danos-vivienda`, `danos-agricultura`, `danos-pecuarios`,
`salud-establecimientos`, `servicios-basicos`, `unidades-educativas`.

### Tag `Repositorio > Catálogo` (5 endpoints)

| Método | Ruta | Descripción |
|---|---|---|
| GET / POST | `/api/v1/repositorio/tipos` | Listar / crear tipo de documento |
| GET / PUT / DELETE | `/api/v1/repositorio/tipos/{id_tipo}` | Obtener / actualizar / eliminar |

### Tag `Repositorio > Documentos` (9 endpoints)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/repositorio/edan/{id_edan}/documentos` | Subir PDF (multipart: file + metadata) |
| GET | `/api/v1/repositorio/edan/{id_edan}/documentos` | Listar PDFs de un EDAN |
| GET | `/api/v1/repositorio/documentos/{id_documento}` | Obtener metadata |
| PUT | `/api/v1/repositorio/documentos/{id_documento}` | Actualizar observaciones/activo |
| DELETE | `/api/v1/repositorio/documentos/{id_documento}` | Soft delete |
| DELETE | `/api/v1/repositorio/documentos/{id_documento}/hard` | Hard delete (archivo incluido) |
| GET | `/api/v1/repositorio/documentos/{id_documento}/descargar` | Descargar PDF |
| GET | `/api/v1/repositorio/documentos/filtrar` | Filtros: departamento, provincia, municipio, tipo, fecha_desde, fecha_hasta, nombre |
| GET | `/api/v1/repositorio/documentos/buscar` | Búsqueda por nombre (ILIKE, sin full-text) |

### Permisos por rol (EDAN — v1.3.0)

| Rol | EDAN (CRUD) | Localidades | Estado EDAN | Ver |
|---|---|---|---|---|
| 1 superadmin | ✅ | ✅ | ✅ | ✅ |
| 2 admin | ❌ (no crea) | ❌ | ✅ | ✅ |
| 3 VIDECI Regional | ❌ | ❌ | ✅ | ✅ |
| 4 UGR Sectores | ❌ | ❌ | ✅ | ✅ |
| 5 DGR Gobernación | ❌ | ❌ | ✅ | ✅ |
| **6 UGR Municipio** | **✅** | **✅** | **❌** | **✅** |
| **7 Responsable Local** | **❌** | **✅** | **❌** | **✅** |
| 8 Alcalde | ❌ | ❌ | ❌ | ✅ |
| 9 VIDECI Departamental | ❌ | ❌ | ✅ | ✅ |

Constantes en `api/edan/router.py`:
- `ROLES_LOCALES = (6, 7)` — CRUD de localidades
- `ROLES_EDAN_CREA = (6,)` — Crear/actualizar EDAN consolidado
- `ROLES_ESTADO_EDAN = (1, 2, 3, 4, 5, 9)` — Cambiar `id_estado` del EDAN
- `ROLES_LECTURA = (6, 7, 8)` — Lectura (incluye alcalde)

Helper: `_require_rol(*roles)` lanza 403 si el rol no está en la lista.

---

## Archivos de referencia

| Archivo | Ubicación |
|---|---|
| Script SQL completo | `database/crear_edan_db.sql` |
| Script geografía INE | `database/insert_provincias_municipios.sql` |
| Migraciones | `database/migration_v*.sql` (v1.2.0 → v2.7.3) |
| Backups | `database/backup_*.sql` |
| Iniciar BD | `database/hacer_backup.sh`, `restore_db.sh` |
| Documentación | `docs/EDAN_BD.md` (este archivo) |
| API | `api/main.py`, `api/edan/`, `api/repositorio/`, `api/rea/` |
