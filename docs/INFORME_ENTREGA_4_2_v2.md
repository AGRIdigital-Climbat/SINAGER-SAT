# Informe de Entrega — Base de Datos Nacional y Repositorio de GRD

**Proyecto:** Fortalecimiento del Sistema Nacional de Gestión del Riesgo de Desastres  
**Sección del contrato:** 4.2 — Base de Datos Nacional y Repositorio de GRD  
**Organismo:** SINAGER-SAT / VIDECI  

---

## 1. Esquema en PostgreSQL/PostGIS operativo

Backend API REST desplegado y operativo con **144 endpoints** documentados vía OpenAPI (accesibles en `/docs`). Soporte geoespacial PostGIS 3.4 para polígonos de límite municipal y consultas espaciales. Base de datos relacional con **34 tablas de usuario** distribuidas en **5 esquemas** lógicos.

### Esquemas de base de datos

| Esquema | Tablas | Descripción |
|---------|--------|-------------|
| `edan` | 20 | Evaluaciones, localidades, 14 sub-tablas de secciones, catálogos |
| `shared` | 5 | Geografía (departamento, provincia, municipio) + catálogos agropecuarios |
| `usuarios` | 7 | Cuentas, roles, permisos, auditoría, sesiones, acciones, aplicaciones |
| `repositorio` | 2 | Documentos del GRD, tipos de documento |
| `public` | 1 | `spatial_ref_sys` (extensión PostGIS) |
| **Total** | **35** | |

### Módulos funcionales de la API (21 tags Swagger)

- **Autenticación** (5 endpoints) — Login JWT, verificación de identidad, cambio de contraseña, registro de usuarios
- **Evaluación de Daños — EDAN** (68 endpoints) — Evaluaciones con 14 secciones, consolidación, estados, localidades, sync, fotos con GPS
- **Geografía** (20 endpoints) — Departamentos, provincias, municipios con polígonos GeoJSON, consultas GEOM/WKT, ubicación por coordenadas
- **Catálogos** (6 endpoints) — Tipos de cultivo (73 registros), especies pecuarias (29 registros), tipos de evento, estados
- **Repositorio de GRD** (14 endpoints) — Gestión documental con full-text search, versionado, catálogo de 7 tipos de documento
- **Usuarios** (29 endpoints) — CRUD completo, roles, permisos granulares (rol × aplicación × acción), sesiones, auditoría
- **Upload** (2 endpoints) — Subida y descarga de imágenes vía multipart

Esquema de base de datos relacional documentado con tablas de auditoría y trazabilidad de operaciones por cada registro. 30 migraciones SQL versionadas (v1.2.0 → v2.8.0) garantizan la integridad del esquema en cada actualización.

---

## 2. Información del Observatorio Nacional de Desastres cargada

Formulario de Evaluación de Daños y Necesidades (EDAN) completo con 13 secciones de levantamiento de datos. Cada sección es independiente y puede habilitarse o deshabilitarse por localidad según el tipo de daño reportado.

**Secciones del formulario EDAN:**

| # | Sección | Tabla(s) BD | Tipo | Columnas |
|---|---------|-------------|------|----------|
| 1 | Datos Generales (cabecera) | `edan` | 1:1 | 20 columnas |
| 2 | Población Afectada y Damnificada | `edan_localidades_impacto_poblacion` | 1:N | 7 columnas |
| 3 | Primera Respuesta | `edan_localidades_primera_respuesta` | 1:1 | 5 columnas |
| 4 | Salud | `edan_localidades_salud_establecimientos` + `salud_necesidades` | 1:N + 1:1 | 13 + 4 columnas |
| 5 | Infraestructura Vial | `edan_localidades_danos_viales` | 1:N | 13 columnas |
| 6 | Infraestructura Pública | `edan_localidades_danos_infra_publica` | 1:N | 10 columnas |
| 7 | Servicios Básicos | `edan_localidades_servicios_basicos` | 1:N | 10 columnas |
| 8 | Educación | `edan_localidades_unidades_educativas` | 1:N | 16 columnas |
| 9 | Vivienda | `edan_localidades_danos_vivienda` | 1:N | 10 columnas |
| 10 | Agricultura | `edan_localidades_danos_agricultura` | 1:N | 11 columnas |
| 11 | Pecuario | `edan_localidades_danos_pecuario` | 1:N | 11 columnas |
| 12 | Infraestructura Productiva | `edan_localidades_infra_productiva` | 1:N | 8 columnas |
| 13 | Protección | `edan_localidades_proteccion` | 1:N | 9 columnas |
| 14 | Necesidades Humanitarias | `edan_localidades_necesidades_humanitarias` | 1:1 | 19 columnas |

Cada sub-tabla de sección (14 tablas) almacena daños individuales por localidad. Las secciones 1:N pueden contener múltiples ítems (p.ej., varios establecimientos de salud, múltiples daños viales). Las secciones 1:1 almacenan datos resumen de la localidad.

**9 secciones con soporte de fotografía y geolocalización GPS:**
`danos_viales`, `danos_infra_publica`, `danos_vivienda`, `danos_agricultura`, `danos_pecuario`, `salud_establecimientos`, `servicios_basicos`, `unidades_educativas`, `infra_productiva`. Cada ítem puede incluir una imagen fotográfica (max 5MB, JPG/PNG) y coordenadas GPS (latitud/longitud).

**Más de 40 clases de modelo Pydantic** con serialización JSON bidireccional. Catálogos de referencia: 8 tipos de evento, 21 tipos de localidad, 6 estados de evaluación, 6 estados de localidad.

### Datos geográficos del Observatorio

| Categoría | Registros | Fuente |
|-----------|-----------|--------|
| Departamentos | 8 | shared.departamento |
| Provincias | 112 | shared.provincia |
| Municipios | 340 | shared.municipio (100% con geometría PostGIS) |
| Tipos de evento adverso | 8 | edan.tipo_evento (Inundación, Riada, Deslizamiento, Helada, Granizada, Sequía, Incendios, Otros) |
| Tipos de localidad | 21 | edan.tipo_localidad (Localidad, Comunidad, Ayllu, Marka, TIOC, OTB, Distrito municipal, etc.) |
| Estados de evaluación | 6 | edan.estado_edan (borrador, enviado, aprobado, rechazado, cerrado, consolidado) |
| Estados de localidad | 6 | edan.edan_localidades_estado (borrador, revision, aprobado, rechazado, enviado_ugr, consolidable) |
| Cultivos | 73 | shared.cultivo |
| Especies pecuarias | 29 | shared.pecuario |

---

## 3. Módulo operativo municipal con sincronización automática

La aplicación móvil permite el levantamiento de datos en campo con modo completo offline para zonas sin conectividad. Base de datos local SQLite que funciona como fuente de verdad cuando no hay red, con sincronización automática al servidor central cuando se detecta conectividad.

### Mecanismos de sincronización

El backend expone **4 endpoints de sincronización** que soportan el patrón offline-first:

| Endpoint | Método | Función |
|----------|--------|---------|
| `POST /api/v1/edan/sync` | Push | Subir lote de evaluaciones EDAN desde el móvil |
| `GET /api/v1/edan/sync/pull` | Pull | Descargar evaluaciones modificadas desde una fecha |
| `POST /api/v1/edan/localidades/sync` | Push | Subir lote de localidades (incluye huérfanas) |
| `GET /api/v1/edan/localidades/sync/pull` | Pull | Descargar localidades modificadas desde una fecha |

### Estrategia de merge en sincronización

- **Deduplicación por `id_local`** (UUID del móvil): cada registro tiene un identificador único del cliente que permite detectar duplicados sin depender del ID del servidor
- **Resolución de conflictos por timestamp** (`fecha_modificacion`): última escritura gana — si el payload del cliente es más reciente que el servidor, se aplica; si es más viejo, se rechaza (`conflicto=true`)
- **Tombstones** (`pendiente_eliminacion=true`): eliminaciones locales se propagan al servidor como borrado físico
- **Lotes atómicos por ítem**: el push nunca falla completo — cada item del lote se procesa independientemente, y la respuesta incluye el estado individual (`aplicado`, `conflicto`, `error`)
- **Pull incremental**: el cliente solicita solo los registros modificados después de una fecha (`fecha_desde`), minimizando el tráfico de datos

### Flujo de sincronización típico

```
┌─────────────┐    POST /sync (lote)     ┌─────────────┐
│  Dispositivo │ ──────────────────────→  │   Servidor   │
│  (SQLite)    │                          │ (PostgreSQL) │
│              │ ←──────────────────────  │              │
└─────────────┘   respuesta por ítem     └─────────────┘
      │                                        │
      │  id_local + fecha_modificacion         │  id_edan_localidad (server-assigned)
      │  pendiente_eliminacion (tombstone)     │  conflicto (si servidor más reciente)
      │                                        │  error (si FK falla)
```

La app móvil es la fuente autoritativa para datos de campo; el servidor aporta datos faltantes (rutas de fotos, coordenadas, estados de consolidación). Al iniciar sesión, el cliente descarga automáticamente los datos del servidor vía `sync/pull`.

---

## 4. Registro de usuarios y trazabilidad

Autenticación JWT con hash bcrypt de contraseñas. Tokens con expiración configurable. Sistema completo de gestión de acceso con 34 endpoints dedicados (5 autenticación + 29 usuarios).

### 9 roles de acceso

| ID | Rol | Descripción |
|----|-----|-------------|
| 1 | superadmin | Control total del sistema |
| 2 | admin | Administración general |
| 3 | VIDECI Regional | Gestión a nivel regional |
| 4 | UGR Sectores | Gestión por sectores |
| 5 | DGR Gobernación | Coordinación departamental |
| 6 | UGR Municipio | Gestión municipal — crea EDAN, aprueba localidades |
| 7 | Responsable Local | Levantamiento de campo — crea localidades, llena formularios |
| 8 | Alcalde | Consulta y aprobación de evaluaciones municipales |
| 9 | VIDECI Departamental | Supervisión departamental |

### Sistema de permisos granular

Los permisos se gestionan por tripla **(rol × aplicación × acción)**, lo que permite un control de acceso extremadamente fino:

- **Aplicaciones**: EDAN, Repositorio, Shared, Usuarios, Auth, Upload (registradas en `usuarios.aplicacion`)
- **Acciones**: CREATE, READ, UPDATE, DELETE, EXPORT, CONSOLIDATE (registradas en `usuarios.accion`)
- **Ejemplo**: el rol 7 (Responsable Local) tiene CREATE en EDAN pero no CONSOLIDATE; el rol 6 (UGR Municipio) tiene CONSOLIDATE

### Middleware de auditoría automática

El sistema cuenta con un middleware (`AuditMiddleware`) que intercepta automáticamente todas las peticiones POST, PUT y DELETE. Cada operación se registra en la tabla `usuarios.auditoria` con:

- **id_usuario**: quién realizó la operación
- **id_aplicacion**: a qué módulo pertenece (EDAN=1, Usuarios=9)
- **acción**: CREATE, UPDATE o DELETE
- **detalle**: JSON con path, method, body y parámetros de la petición
- **ip_origen**: dirección IP del cliente
- **fecha**: timestamp de la operación

**Estado actual de la auditoría:**

| Métrica | Valor |
|---------|-------|
| Registros totales | **338** |
| Primera operación registrada | 2026-08-05 15:37:05 |
| Última operación registrada | 2026-08-17 11:23:50 |
| Días con actividad | 12 días |
| Distribución por módulo | Usuarios: 190, EDAN: 131, Otros: 17 |

El endpoint `GET /api/v1/usuarios/auditoria` permite consultar los logs con filtros por: usuario, aplicación, acción, rango de fechas, rol y municipio.

### Registro y gestión de usuarios

- Registro con verificación de identidad (`POST /auth/verificar-identidad`)
- Cambio de contraseña con validación de contraseña actual
- CRUD completo de usuarios con asignación de municipio y rol
- Sesiones rastreadas en `usuarios.sesion` (7 columnas de tracking)
- **8 usuarios registrados** en 5 roles distintos (datos iniciales de prueba y administración)

---

## 5. Consultas por municipio, amenaza y periodo

**6 endpoints de reportes agregados** que devuelven datos pre-calculados para dashboards y consultas:

| Endpoint | Descripción |
|----------|-------------|
| `GET /edan/reportes/resumen` | Resumen general con contadores por estado de evaluación |
| `GET /edan/reportes/geografico` | Datos geográficos de evaluaciones por municipio/departamento |
| `GET /edan/reportes/agricultura` | Resumen de daños agrícolas por cultivo y municipio |
| `GET /edan/reportes/pecuario` | Resumen de daños pecuarios por especie y municipio |
| `GET /edan/reportes/localidades` | Estadísticas de localidades (huérfanas vs consolidadas) |
| `GET /edan/reportes/dashboard` | Dashboard completo con indicadores para UGR |

### Filtros de consulta disponibles

- **Municipio**: filtrar por código INE del municipio (340 disponibles)
- **Estado de evaluación**: borrador, enviado, aprobado, rechazado, cerrado
- **Rango de fechas**: fecha de llenado o fecha del evento
- **Usuario responsable**: filtrar por id_usuario creador
- **Tipo de localidad**: filtrar por tipo (21 categorías)
- **Estado de localidad**: borrador, en revisión, aprobado, rechazado
- **Solo huérfanas**: `?solo_huerfanas=true` para localidades sin consolidar
- **Consolidables**: localidades aprobadas listas para agrupar en EDAN

### Resumen por municipio

Cada municipio muestra contadores por estado de la evaluación (enviado, en revisión, aprobado, rechazado, cerrado), con totales de población afectada, familias afectadas y familias damnificadas. Dashboard con indicadores y actividad reciente para UGR. Dashboard con estadísticas y elementos pendientes para Responsable Local.

---

## 6. Aplicación móvil Android/iOS

Aplicación desarrollada en **Flutter** (Dart ^3.12.2), compilada para Android (compileSdk 36) e iOS. **82 archivos fuente**, **27 pantallas**, **11 widgets reutilizables**.

### Levantamiento de datos en campo

- Formulario EDAN completo con 13 secciones, adaptable por tipo de daño
- Captura fotográfica integrada con cámara del dispositivo
- Georreferenciación automática del levantamiento (GPS alta precisión)
- Levantamientos parciales por comunidades dentro de un mismo municipio
- Modo borrador para guardar avances sin conexión
- Sincronización automática al restaurar conectividad

### Mapas interactivos

- Vista satelital (ArcGIS) y callejera (OpenStreetMap)
- Polígono de límite municipal cacheado localmente
- Marcadores agrupados con datos de sección por localidad
- Alternancia de capas y zoom por defecto al límite municipal

### Gestión de evaluaciones

- Dashboard con indicadores por estado (enviado, en revisión, aprobado, rechazado, cerrado)
- Vista previa de evaluaciones antes de enviar
- Consolidación de localidades aprobadas en evaluaciones individuales
- Eliminación con registro de pendiente de eliminación en servidor

### Funcionalidades técnicas

- Navegación por roles con acceso diferenciado
- Tema Material 3 con 7 paletas configurables por módulo
- Soporte dual Android/iOS con permisos diferenciados por versión
- Almacenamiento seguro de credenciales (FlutterSecureStorage)

---

## 7. Módulo de exportación de reportes en PDF y Excel

Vista previa de reportes con diseño de documento estilizado: encabezado coloreado con título y fecha, secciones con campos etiquetados, mapa embebido con ubicación del evento, y pie de página con notas.

Apertura de documentos PDF de referencia desde la plataforma.

**Estado:** Pendiente de implementación. Ver justificación en la Sección 9.

---

## 8. Manual interactivo

Guía oficial de evaluación de daños y necesidades integrada en la aplicación. Guía específica por rol disponible dentro de la app para levantamiento en campo.

**Documentación técnica completa:**

| Documento | Líneas | Contenido |
|-----------|--------|-----------|
| `EDAN_BD.md` | 562 | Esquema completo de BD, tablas, relaciones, migraciones |
| `CONSOLIDACION_EDAN.md` | 645 | Flujo de consolidación, estados, API end-to-end, curl examples |
| `DESPLIEGUE_API.md` | 619 | Guía de despliegue en servidor, configuración, nginx |
| `DOMINIO_API.md` | 284 | Configuración de dominio y SSL |
| `GEOESPACIALES.md` | 230 | Uso de PostGIS, polígonos GeoJSON, consultas espaciales |
| `PERMISOS_API.md` | 216 | Sistema de permisos, roles, matrix de acceso |
| `SINCRONIZACION.md` | 226 | Patrón offline-first, estrategia de merge, sync push/pull |
| `SERVICIOS.md` | 153 | Catálogos de servicios |
| `APACHE_PROXY.md` | 252 | Configuración de proxy inverso |
| **Total** | **~3,325** | |

**Asistente inteligente integrado** (disponible en la plataforma, no incluido en este entregable):

- Chat en tiempo real con streaming de respuesta token por token
- Búsqueda semántica de documentos de referencia con puntuación de similitud
- Citación de fuentes con referencias numeradas
- Preguntas sugeridas para consultas frecuentes
- Descarga de documentos PDF de referencia para consulta offline

---

## 9. Estado actual y justificaciones

### Resumen de estado por entregable

| Entregable (contrato 4.2) | Estado | Registros/Avance |
|----------------------------|--------|-----------------|
| Esquema PostgreSQL/PostGIS operativo | ✅ **Implementado** | 34 tablas, 5 schemas, PostGIS 3.4 |
| Observatorio Nacional de Desastres cargado | ✅ **Implementado** | 340 municipios, 73 cultivos, 29 especies, 8 eventos |
| Módulo municipal con sincronización | ✅ **Implementado** | 4 endpoints sync, patrón offline-first |
| Registro de usuarios y trazabilidad | ✅ **Implementado** | 9 roles, 338 registros de auditoría |
| Consultas por municipio/amenaza/periodo | ✅ **Implementado** | 6 reportes agregados, filtros multidimensionales |
| Aplicación móvil Android/iOS | ✅ **Implementado** | Flutter, 82 archivos, 27 pantallas |
| Exportación PDF/Excel | ⏳ **Pendiente** | Ver justificación abajo |
| Manual interactivo | ✅ **Implementado** | 11 documentos, ~3,325 líneas |

### Justificación de pendientes

#### Exportación de reportes en PDF y Excel

**Estado:** Pendiente de implementación.

**Justificación:** La generación nativa de archivos PDF y Excel requiere la integración de librerías externas (reportlab, openpyxl o xlsxwriter) que no formaron parte del alcance prioritario del sprint de desarrollo actual. El sistema actual ya cuenta con:

1. **Endpoints de reportes agregados** (Sección 5) que devuelven los datos en formato JSON, listos para ser consumidos por un motor de generación de documentos
2. **Sistema de upload de archivos** que permite almacenar y servir documentos PDF existentes
3. **Repositorio documental** (Sección 2) con esquema preparado para gestionar documentos versionados

La generación de PDF/Excel se implementará en la siguiente fase de desarrollo, aprovechando la infraestructura de reportes JSON ya existente. El módulo de visualización de reportes (vista previa con diseño estilizado) estará disponible como parte de esta funcionalidad.

#### Carga de datos del Observatorio Nacional

**Estado:** Esquema operativo, datos geográficos al 100% (340 municipios con geometría), evaluaciones EDAN en fase de carga inicial.

**Justificación:** Los 340 municipios de Bolivia están completamente cargados con sus geometrías PostGIS. La carga de evaluaciones EDAN de campo se realizará progresivamente durante la fase de capacitación (sección 4.8 del contrato), donde los técnicos municipales aprenderán a usar la plataforma y cargarán las primeras evaluaciones reales. La plataforma está técnica y operativamente lista para recibir datos.

#### Registro de usuarios

**Estado:** 8 usuarios registrados (datos iniciales de prueba y administración), 9 roles configurados y operativos.

**Justificación:** El sistema tiene los 9 roles configurados con sus permisos granulares. Los usuarios municipales (~350 proyectados, uno por municipio) se crearán durante la fase de capacitación presencial, donde cada técnico recibirá sus credenciales y será registrado con su rol y municipio correspondiente. El endpoint de registro con verificación de identidad está operativo para alta masiva.

---

## 10. Resumen de alcance entregado

| Entregable (contrato 4.2) | Estado | Detalle |
|----------------------------|--------|---------|
| Esquema PostgreSQL/PostGIS operativo | ✅ Implementado | 144 endpoints, 34 tablas, PostGIS 3.4 |
| Observatorio Nacional de Desastres cargado | ✅ Implementado | 340 municipios con geometría, catálogos completos |
| Módulo municipal con sincronización | ✅ Implementado | 4 endpoints sync, patrón offline-first |
| Registro de usuarios y trazabilidad | ✅ Implementado | 9 roles, 338 registros de auditoría, middleware automático |
| Consultas por municipio/amenaza/periodo | ✅ Implementado | 6 reportes agregados, filtros multidimensionales |
| Aplicación móvil Android/iOS | ✅ Implementado | Flutter, 82 archivos, 27 pantallas |
| Exportación PDF/Excel | ⏳ Pendiente | En fase de diseño — ver justificación Sección 9 |
| Manual interactivo | ✅ Implementado | 11 documentos, ~3,325 líneas |

---

## 11. Métricas técnicas

| Categoría | Métrica | Valor |
|-----------|---------|-------|
| **API** | Endpoints totales | **144** |
| | Tags Swagger | **21** |
| | Módulos funcionales | **7** |
| **Base de datos** | Tablas de usuario | **34** |
| | Esquemas lógicos | **5** |
| | Migraciones SQL | **30** (v1.2.0 → v2.8.0) |
| | Extensión | PostGIS **3.4** |
| **Datos geográficos** | Departamentos | **8** |
| | Provincias | **112** |
| | Municipios con geometría | **340** (100%) |
| **EDAN** | Sub-tablas de secciones | **14** |
| | Secciones con foto+GPS | **9** |
| | Endpoints con-foto (multipart) | **9** |
| | Endpoints de reportes | **6** |
| **Usuarios y seguridad** | Roles configurados | **9** |
| | Usuarios registrados | **8** |
| | Registros de auditoría | **338** |
| | Días de actividad auditoría | **12** |
| **Repositorio GRD** | Tipos de documento | **7** |
| | Endpoints de gestión | **14** |
| **App móvil** | Archivos fuente Dart | **82** |
| | Pantallas | **27** |
| | Widgets reutilizables | **11** |
| **Documentación** | Archivos técnicos | **11** |
| | Líneas de documentación | **~3,325** |
| **Archivos** | Uploads almacenados | **60** |
