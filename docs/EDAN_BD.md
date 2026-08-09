# EDAN - Base de Datos PostgreSQL

Arquitectura **Multi-Esquema** para el Sistema de Gestión de Desastres Naturales
SINAGERSAT (Sistema Nacional de Alerta Temprana y Gestión de Riesgos).

## Conexión

| Parámetro | Valor |
|---|---|
| **Host** | `localhost` o `/var/run/postgresql` |
| **Puerto** | `5432` |
| **Base de datos** | `db_sinagersat` |
| **Usuario** | `sinagersat` |
| **Contraseña** | `12345678` |

### Comando de conexión

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost -p 5432
```

### Conexión via socket Unix

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h /var/run/postgresql
```

---

## Arquitectura Multi-Esquema

Una sola base de datos `db_sinagersat` con 6 esquemas que separan responsabilidades:

```
PostgreSQL: db_sinagersat
├── shared   → Geografía (catálogos INE: departamento, provincia, municipio)
├── usuarios → Gestión de usuarios (cuentas, roles, sesiones, permisos, auditoría)
├── edan     → Formularios EDAN (20 tablas: cabecera + localidades anidadas)
├── rea      → Reportes de Eventos Adversos (4 tablas)
├── rida     → (vacío - futuro sistema RIDA)
├── sinb     → (vacío - futuro sistema SINB)
└── recursos → (vacío - futura gestión de recursos)
```

**Total de tablas:** 40  
**Foreign Keys:** 35+  
**Índices:** 45+

Las consultas entre esquemas son igual de rápidas que entre tablas del mismo schema
(una sola conexión PostgreSQL, sin overhead de BDs separadas).

---

## Schema `shared` — Geografía (códigos INE)

Catálogos geográficos del Instituto Nacional de Estadística (INE) de Bolivia,
compartidos por todos los sistemas del SINAGERSAT.

| Tabla | Registros | Descripción |
|---|---|---|
| `departamento` | 9 | Departamentos de Bolivia |
| `provincia` | 112 | Provincias por departamento |
| `municipio` | 340 | Municipios por provincia |

### Codificación INE

| Nivel | Formato | Ejemplo | Descripción |
|---|---|---|---|
| **Departamento** | `DD` (2 dígitos) | `02` | La Paz |
| **Provincia** | `DDPP` (4 dígitos) | `0204` | Provincia Aroma (La Paz) |
| **Municipio** | `DDPPMM` (6 dígitos) | `020401` | Municipio Patacamaya (Aroma, La Paz) |

Los `id` son el valor numérico del `codigo_ine` (sin ceros a la izquierda).

### Estructura de `shared.departamento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | ID numérico (= valor de codigo_ine) |
| `codigo_ine` | VARCHAR(2) NOT NULL UNIQUE | Código INE de 2 dígitos (DD) |
| `nombre` | VARCHAR(100) NOT NULL UNIQUE | Nombre del departamento |

### Estructura de `shared.provincia`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | ID numérico (= valor de codigo_ine) |
| `codigo_ine` | VARCHAR(4) NOT NULL UNIQUE | Código INE de 4 dígitos (DDPP) |
| `id_departamento` | INTEGER NOT NULL FK | Departamento (FK → shared.departamento.id) |
| `nombre` | VARCHAR(100) NOT NULL | Nombre de la provincia |

### Estructura de `shared.municipio`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | ID numérico (= valor de codigo_ine) |
| `codigo_ine` | VARCHAR(6) NOT NULL UNIQUE | Código INE de 6 dígitos (DDPPMM) |
| `id_departamento` | INTEGER NOT NULL FK | Departamento (FK → shared.departamento.id) |
| `id_provincia` | INTEGER NOT NULL FK | Provincia (FK → shared.provincia.id) |
| `nombre` | VARCHAR(100) NOT NULL | Nombre del municipio |

### Datos geográficos

| Código | Departamento | Provincias | Municipios |
|---|---|---|---|
| 01 | Chuquisaca | 10 | 29 |
| 02 | La Paz | 20 | 87 |
| 03 | Cochabamba | 16 | 47 |
| 04 | Oruro | 16 | 35 |
| 05 | Potosí | 16 | 41 |
| 06 | Tarija | 6 | 11 |
| 07 | Santa Cruz | 15 | 56 |
| 08 | Beni | 8 | 19 |
| 09 | Pando | 5 | 15 |

> **Nota:** Los datos corresponden al Censo INE 2024 (112 provincias, 340 municipios).

---

## Schema `usuarios` — Gestión de Usuarios

Sistema global de autenticación y autorización para todas las aplicaciones del SINAGERSAT.

| Tabla | Descripción |
|---|---|
| `usuario` | Cuentas de usuario (credenciales, estado, control de acceso) |
| `rol` | Catálogo de roles (gestionable desde la aplicación) |
| `usuario_rol` | Asignación N:M de usuarios a roles |
| `aplicacion` | Catálogo de sistemas (EDAN, RIDA, SINB) |
| `permiso_aplicacion` | Qué rol tiene acceso a qué aplicación |
| `sesion` | Tokens de sesión activos |
| `reset_contrasena` | Solicitudes de restablecimiento de contraseña |
| `auditoria` | Log de acciones (login, creación de formularios, etc.) |

### Estructura de `usuarios.usuario`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_usuario` | SERIAL PK | ID único |
| `usuario` | VARCHAR(100) NOT NULL UNIQUE | Nombre de usuario (login) |
| `contrasena` | VARCHAR(255) NOT NULL | Hash de la contraseña |
| `nombre` | VARCHAR(200) NOT NULL | Nombre real del usuario |
| `celular` | VARCHAR(30) | Teléfono/celular |
| `carnet` | VARCHAR(30) | N° de carnet de identidad |
| `comunidad` | VARCHAR(200) | Comunidad a la que pertenece |
| `id_departamento` | INTEGER FK | Departamento (FK → shared.departamento.id) |
| `id_provincia` | INTEGER FK | Provincia (FK → shared.provincia.id) |
| `id_municipio` | INTEGER FK | Municipio (FK → shared.municipio.id) |
| `activo` | BOOLEAN DEFAULT TRUE | Cuenta activa/inactiva |

### Estructura de `usuarios.rol`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_rol` | SERIAL PK | ID único |
| `nombre` | VARCHAR(50) NOT NULL UNIQUE | Nombre del rol (superadmin, admin, encuestador, visor) |
| `descripcion` | VARCHAR(255) | Descripción del rol |
| `jerarquia` | INTEGER NOT NULL | Nivel de permisos (1=menor, 5=mayor) |

### Roles por defecto

| Rol | Jerarquía | Acceso a aplicaciones | Descripción |
|---|---|---|---|
| `superadmin` | 5 | Todas (EDAN, RIDA, SINB) | Acceso total a todos los sistemas + gestión de usuarios |
| `admin` | 4 | Todas (EDAN, RIDA, SINB) | Gestiona usuarios y datos de su sistema |
| `encuestador` | 2 | EDAN | Carga y edita formularios propios |
| `visor` | 1 | EDAN | Solo lectura en todos los módulos |

> Los roles y permisos son gestionables desde la aplicación (CRUD completo).

### Estructura de `usuarios.aplicacion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_aplicacion` | SERIAL PK | ID único |
| `codigo` | VARCHAR(20) NOT NULL UNIQUE | Código (EDAN, RIDA, SINB) |
| `nombre` | VARCHAR(100) NOT NULL | Nombre completo |
| `descripcion` | VARCHAR(255) | Descripción |
| `activo` | BOOLEAN DEFAULT TRUE | Disponible para asignar permisos |

### Estructura de `usuarios.usuario_rol`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_usuario` | INTEGER FK | Usuario (FK → usuarios.usuario.id_usuario) |
| `id_rol` | INTEGER FK | Rol (FK → usuarios.rol.id_rol) |
| PK compuesta | (id_usuario, id_rol) | Un usuario puede tener varios roles |

### Estructura de `usuarios.permiso_aplicacion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_permiso` | SERIAL PK | ID único |
| `id_rol` | INTEGER FK | Rol (FK → usuarios.rol.id_rol) |
| `id_aplicacion` | INTEGER FK | Aplicación (FK → usuarios.aplicacion.id_aplicacion) |
| UNIQUE | (id_rol, id_aplicacion) | Un permiso por rol+aplicación |

### Estructura de `usuarios.sesion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_sesion` | SERIAL PK | ID único |
| `id_usuario` | INTEGER FK | Usuario (FK → usuarios.usuario.id_usuario) |
| `token` | VARCHAR(255) NOT NULL UNIQUE | Token de autenticación (JWT o UUID) |
| `fecha_inicio` | TIMESTAMP DEFAULT NOW | Inicio de sesión |
| `fecha_expiracion` | TIMESTAMP NOT NULL | Expiración del token |
| `ip_origen` | VARCHAR(50) | Dirección IP de origen |
| `activo` | BOOLEAN DEFAULT TRUE | Sesión vigente |

### Estructura de `usuarios.reset_contrasena`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_reset` | SERIAL PK | ID único |
| `id_usuario` | INTEGER FK | Usuario (FK → usuarios.usuario.id_usuario) |
| `token` | VARCHAR(255) NOT NULL UNIQUE | Token de restablecimiento |
| `usado` | BOOLEAN DEFAULT FALSE | Ya fue utilizado |
| `fecha_solicitud` | TIMESTAMP DEFAULT NOW | Fecha de solicitud |
| `fecha_expiracion` | TIMESTAMP NOT NULL | Expiración del token |
| `ip_origen` | VARCHAR(50) | IP desde donde se solicitó |

### Estructura de `usuarios.auditoria`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_auditoria` | BIGSERIAL PK | ID único |
| `id_usuario` | INTEGER FK | Usuario que realizó la acción |
| `id_aplicacion` | INTEGER FK | Aplicación donde ocurrió |
| `accion` | VARCHAR(100) NOT NULL | Tipo de acción (login, logout, crear_edan, etc.) |
| `detalle` | JSONB | Datos adicionales de la acción |
| `ip_origen` | VARCHAR(50) | IP de origen |
| `fecha` | TIMESTAMP DEFAULT NOW | Fecha y hora |

---

## Schema `edan` — Formulario EDAN

Arquitectura **jerárquica por localidades**: un EDAN tiene una cabecera única y
una o varias **localidades**, cada una con sus 16 secciones de daños y necesidades
como sub-tablas. Es el modelo que usa la app móvil `AppREA`
(`lib/models/edan.dart`) y la API los devuelve anidados.

```
edan.edan  (cabecera 1)
   └── edan.edan_localidades  (1:N)
         ├── edan_grupo_etario_detalle              (1:N)
         ├── edan_localidades_impacto_poblacion     (1:1)
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
         ├── edan_localidades_proteccion            (1:1)
         ├── edan_localidades_proteccion_grupos     (1:N)
         └── edan_localidades_necesidades_humanitarias (1:1)
```

### Tabla Padre: `edan.edan`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan` | BIGSERIAL PK | Identificador único |
| `codigo_edan` | VARCHAR(30) | Código interno EDAN |
| `id_departamento` | INTEGER FK | Departamento (FK → shared.departamento.id) |
| `id_provincia` | INTEGER FK | Provincia (FK → shared.provincia.id) |
| `id_municipio` | INTEGER FK | Municipio (FK → shared.municipio.id) |
| `nombre_alcalde` | VARCHAR(200) | Nombre del alcalde |
| `fono_alcalde` | VARCHAR(30) | Teléfono del alcalde |
| `fecha_llenado` | DATE | Fecha de llenado |
| `fecha_evento` | DATE | Fecha del evento |
| `hora_evento` | TIME | Hora del evento |
| `total_poblacion_afectada` | INTEGER | Total población afectada |
| `total_familias_afectadas` | INTEGER | Total familias afectadas |
| `total_familias_damnificadas` | INTEGER | Total familias damnificadas |
| `responsable_nombre` | VARCHAR(200) | Responsable del llenado |
| `responsable_cargo` | VARCHAR(100) | Cargo |
| `responsable_fono` | VARCHAR(30) | Teléfono/celular |
| `responsable_correo` | VARCHAR(150) | Correo electrónico |
| `fecha_creacion` | TIMESTAMP | Auditoría |
| `fecha_modificacion` | TIMESTAMP | Auditoría |
| `id_reporte_rea` | INTEGER FK | Reporte REA origen (FK → rea.reporte_evento.id_reporte, ON DELETE SET NULL, nullable) |
| `fotografia` | TEXT | Ruta/imagen del formulario |
| `id_server` | INTEGER | ID del servidor de origen (sincronización) |
| `id_usuario` | INTEGER FK | Usuario que registró (FK → usuarios.usuario.id_usuario) |
| `id_tipo_evento` | INTEGER FK | Tipo de evento (FK → edan.tipo_evento) |
| `id_estado` | INTEGER FK | Estado del ciclo de vida (FK → edan.estado_edan) |
| `estado` | VARCHAR(50) | Nombre del estado (borrador, enviado, ...) |
| `sincronizado` | BOOLEAN | Banderas de sincronización |
| `pendiente_eliminacion` | BOOLEAN | Marca de eliminación suave |
| `pendiente_actualizacion` | BOOLEAN | Actualización pendiente de sincronizar |
| `es_borrador` | BOOLEAN | Formulario en borrador |
| `intentos_sync` | INTEGER | Contador de reintentos |
| `ultimo_error` | TEXT | Último error de sincronización |
| `departamento_nombre` | VARCHAR(200) | Nombre denormalizado (reportes) |
| `provincia_nombre` | VARCHAR(200) | Nombre denormalizado (reportes) |
| `municipio_nombre` | VARCHAR(200) | Nombre denormalizado (reportes) |
| `tipo_evento_nombre` | VARCHAR(100) | Nombre denormalizado (reportes) |

> **Nota:** `id_provincia` y `id_departamento` se derivan automáticamente del
> `id_municipio` en el backend cuando no se envían explícitamente.

### Catálogos propios del formulario

| Tabla | Registros | Descripción |
|---|---|---|
| `tipo_evento` | 8 | Tipos de evento adverso (Inundación, Riada, etc.) |
| `estado_edan` | 5 | Estados del ciclo de vida (borrador, enviado, aprobado, rechazado, cerrado) |

> `grupo_etario`, `servicio_basico`, `categoria_proteccion` y `ayuda_humanitaria`
> se eliminaron: hoy son CHECKs / columnas booleanas directas en las sub-tablas.

---

## Tabla intermedia: `edan.edan_localidades`

Cada localidad afectada. Tiene 9 flags `imp_*` que indican qué secciones están
informadas (permiten filtros rápidos tipo "EDAN con daños en educación").

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan_localidad` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia al EDAN (CASCADE) |
| `tipo_localidad` | VARCHAR(50) | Tipo (Comunidad, Barrio, ...) |
| `nombre` | VARCHAR(200) | Nombre de la localidad |
| `imp_poblacion` | BOOLEAN | Tiene impacto en población |
| `imp_salud` | BOOLEAN | Tiene impacto en salud |
| `imp_infraestructura` | BOOLEAN | Tiene impacto en infraestructura |
| `imp_servicios` | BOOLEAN | Tiene impacto en servicios |
| `imp_educacion` | BOOLEAN | Tiene impacto en educación |
| `imp_vivienda` | BOOLEAN | Tiene impacto en vivienda |
| `imp_agropecuario` | BOOLEAN | Tiene impacto agropecuario |
| `imp_proteccion` | BOOLEAN | Tiene impacto en protección |
| `imp_necesidades` | BOOLEAN | Tiene necesidades humanitarias |

## Tablas Hijas (16)

Todas referencian a `edan.edan_localidades(id_edan_localidad)` con `ON DELETE CASCADE`.
Las relaciones 1:1 usan la PK de la localidad como PK propia.

### `edan.edan_grupo_etario_detalle` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_grupo_etario_detalle` | SERIAL PK | ID |
| `rango` | VARCHAR(100) | Rango etario (00-05, 06-18, ...) |
| `fallecidos` | INTEGER | N° fallecidos |
| `heridos` | INTEGER | N° heridos |
| `desaparecidos` | INTEGER | N° desaparecidos |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_impacto_poblacion` (1:1)

| Campo | Tipo | Descripción |
|---|---|---|
| `grupo_etario` | VARCHAR(100) | Grupo etario general |
| `fallecidos` / `heridos` / `desaparecidos` | INTEGER | Totales |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_primera_respuesta` (1:1)

| Campo | Tipo | Descripción |
|---|---|---|
| `busqueda` / `salvamento` / `evacuacion` | BOOLEAN | Requerimientos |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_salud_establecimientos` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_establecimiento_salud` | SERIAL PK | ID |
| `nombre_establecimiento` | VARCHAR(200) | Nombre |
| `comunidad` | VARCHAR(200) | Localidad/Comunidad |
| `nivel_atencion` | VARCHAR(50) | Nivel de atención |
| `dano_parcial` / `dano_total` | BOOLEAN | Daños |
| `medicos_afectados` / `enfermeras_afectadas` / `otros_afectados` | INTEGER | Personal afectado |

### `edan.edan_localidades_salud_necesidades` (1:1)

| Campo | Tipo | Descripción |
|---|---|---|
| `botiquines` | BOOLEAN | Requiere botiquines |
| `numero_personas` | INTEGER | Personas que requieren atención |
| `otras_necesidades` | TEXT | Otras necesidades |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_danos_viales` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_dano_vial` | SERIAL PK | ID |
| `via_puente` | VARCHAR(200) | Vía/puente afectado |
| `tramo` | VARCHAR(200) | Tramo |
| `dano_parcial` / `dano_total` | BOOLEAN | Daños |
| `km_danio` | NUMERIC(10,2) | Km de daño |
| `necesidades_inmediatas` / `observaciones` | TEXT | Detalle |

### `edan.edan_localidades_danos_infra_publica` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_dano_infra` | SERIAL PK | ID |
| `comunidad` | VARCHAR(200) | Localidad |
| `tipo_estructura` | VARCHAR(200) | Tipo de estructura |
| `dano_parcial` / `dano_total` | BOOLEAN | Daños |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_servicios_basicos` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_servicio_basico` | SERIAL PK | ID |
| `tipo` | VARCHAR(50) | CHECK: energia_electrica, agua_potable, alcantarillado, gas_domiciliario, telecomunicaciones |
| `afectado` | BOOLEAN | Afectado |
| `dano_parcial` / `dano_total` | BOOLEAN | Daños |
| `necesidades_inmediatas` / `observaciones` | TEXT | Detalle |
| — | — | UNIQUE (id_edan_localidad, tipo) |

### `edan.edan_localidades_unidades_educativas` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_unidad_educativa` | SERIAL PK | ID |
| `nombre_establecimiento` | VARCHAR(200) | Nombre |
| `comunidad` | VARCHAR(200) | Localidad |
| `dano_parcial` / `dano_total` | BOOLEAN | Daños |
| `suspension_clases` / `perdida_material` / `funciona_albergue` | BOOLEAN | Estado |
| `estudiantes` / `profesores` / `administrativos` | INTEGER | Afectados |
| `observaciones` | TEXT | Observaciones |

### `edan.edan_localidades_danos_vivienda` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_dano_vivienda` | SERIAL PK | ID |
| `comunidad` | VARCHAR(200) | Localidad |
| `dano_parcial` | INTEGER | Viviendas con daño parcial |
| `dano_total` | INTEGER | Viviendas con daño total |
| `necesidades_inmediatas` / `observaciones` | TEXT | Detalle |

### `edan.edan_localidades_danos_agricultura` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_dano_agricultura` | SERIAL PK | ID |
| `tipo_cultivo` | VARCHAR(200) | Texto libre |
| `id_cultivo` | INTEGER FK | FK opcional → shared.cultivo(id) |
| `hectareas_afectadas` / `hectareas_perdidas` | INTEGER | Hectáreas |
| `necesidades_inmediatas` / `observaciones` | TEXT | Detalle |

### `edan.edan_localidades_danos_pecuario` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_dano_pecuario` | SERIAL PK | ID |
| `especie` | VARCHAR(100) | Texto libre |
| `id_especie` | INTEGER FK | FK opcional → shared.pecuario(id) |
| `raza` | VARCHAR(100) | Raza |
| `animales_afectados` / `animales_muertos` | INTEGER | Cabezas |
| `necesidades_inmediatas` | TEXT | Detalle |

### `edan.edan_localidades_infra_productiva` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_infra_productiva` | SERIAL PK | ID |
| `tipo` | VARCHAR(200) | Tipo de infraestructura |
| `dano_parcial` / `dano_total` | INTEGER | Unidades dañadas |

### `edan.edan_localidades_proteccion` (1:1)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan_localidad` | BIGINT PK | Solo existencia (marcador) |

### `edan.edan_localidades_proteccion_grupos` (1:N)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_grupo_vulnerable` | SERIAL PK | ID |
| `grupo` | VARCHAR(50) | CHECK: ninos, adolescentes, mujeres_lactantes, mujeres_embarazadas, adultos_mayores, personas_discapacidad, personas_enfermedad |
| `mujeres` / `hombres` | INTEGER | Cantidad |
| `apoyo_psicologico` / `reposicion_documentos` | BOOLEAN | Apoyos |
| `observaciones` | TEXT | Observaciones |
| — | — | UNIQUE (id_edan_localidad, grupo) |

### `edan.edan_localidades_necesidades_humanitarias` (1:1)

| Campo | Tipo | Descripción |
|---|---|---|
| `alimentos`, `refugio_vivienda`, `ropa_cama`, `articulos_higiene`, `articulos_cocina`, `prendas_vestir`, `herramientas`, `almacenamiento_agua`, `banos` | BOOLEAN | Necesidades (9) |
| `obs_<nombre>` (9) | TEXT | Observaciones por necesidad |

---

## Schema `rea` — Reportes de Eventos Adversos

Sistema para que líderes comunitarios reporten eventos adversos antes de la evaluación EDAN completa.
Permite registrar eventos desde el campo con información básica, que luego puede generar una EDAN.

### Estructura de `rea.estado_reporte`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_estado` | SERIAL PK | ID único |
| `nombre` | VARCHAR(50) NOT NULL UNIQUE | Nombre del estado |
| `descripcion` | VARCHAR(200) | Descripción del estado |
| `orden` | INTEGER NOT NULL | Orden de visualización |

**Estados por defecto:** Pendiente (1), Revisado (2), Atendido (3), Cerrado (4), Rechazado (5)

### Estructura de `rea.afectacion_categoria`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_categoria` | SERIAL PK | ID único |
| `nombre` | VARCHAR(100) NOT NULL UNIQUE | Nombre de la categoría |
| `descripcion` | VARCHAR(200) | Descripción de la categoría |
| `orden` | INTEGER NOT NULL | Orden de visualización |

**Categorías por defecto:** Población (1), Salud (2), Infraestructura (3), Servicios básicos (4), Educación (5), Vivienda (6), Agropecuario (7)

### Estructura de `rea.reporte_evento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_reporte` | SERIAL PK | ID único del reporte |
| `id_usuario` | INTEGER FK | Líder que reporta (FK → usuarios.usuario.id_usuario) |
| `id_departamento` | INTEGER FK | Departamento (FK → shared.departamento.id) |
| `id_provincia` | INTEGER FK | Provincia (FK → shared.provincia.id) |
| `id_municipio` | INTEGER FK | Municipio (FK → shared.municipio.id) |
| `comunidad` | VARCHAR(200) NOT NULL | Nombre de la comunidad |
| `fecha_evento` | DATE NOT NULL | Fecha en que ocurrió el evento |
| `hora_evento` | TIME | Hora aproximada del evento |
| `fecha_reporte` | TIMESTAMP DEFAULT NOW | Fecha y hora del reporte |
| `id_tipo_evento` | INTEGER FK | Tipo de evento (FK → edan.tipo_evento.id_tipo_evento) |
| `coordenada_lat` | NUMERIC(10,8) | Latitud GPS |
| `coordenada_lon` | NUMERIC(11,8) | Longitud GPS |
| `fotografia` | VARCHAR(500) | Ruta/nombre del archivo de foto |
| `descripcion` | TEXT | Descripción del evento |
| `id_estado` | INTEGER FK | Estado del reporte (FK → rea.estado_reporte.id_estado) |

### Estructura de `rea.reporte_afectacion` (tabla puente)

| Campo | Tipo | Descripción |
|---|---|---|
| `id_reporte` | INTEGER FK PK | Reporte (FK → rea.reporte_evento.id_reporte, ON DELETE CASCADE) |
| `id_categoria` | INTEGER FK PK | Categoría de afectación (FK → rea.afectacion_categoria.id_categoria) |

### Relación REA → EDAN

Un reporte REA puede generar un formulario EDAN completo. La relación es **bidireccional** (migración v1.5.1):

- `edan.edan.id_reporte_rea` (`INTEGER FK`) → **REA de origen** (el que generó el EDAN). FK hacia `rea.reporte_evento.id_reporte` con `ON DELETE SET NULL`.
- `rea.reporte_evento.id_edan` (`BIGINT FK`) → **vínculo inverso** (a qué EDAN pertenece el REA). FK hacia `edan.edan.id_edan` con `ON DELETE SET NULL`.

Reglas de negocio:
- **NULL**: el EDAN fue creado directamente, sin reporte REA previo (el campo puede ir vacío).
- **Con valor**: el EDAN fue creado a partir del reporte REA indicado.
- **Cardinalidad**: un REA solo puede generar **un** EDAN; un EDAN puede **agrupar varios** REAs (por lo general solo uno). La API mantiene ambos vínculos sincronizados automáticamente (crear/actualizar/desvincular).
- Si se borra un REA o un EDAN, el vínculo se pone en NULL (nunca se elimina el registro que sobrevive).
- Si el REA de origen cambia, el `id_edan` del REA anterior se limpia.

No se copia información del REA al EDAN; solo se establece la trazabilidad para saber de qué reporte surgió cada evaluación. En la respuesta GET del EDAN, el objeto anidado `reporte_rea` (detalle del REA de origen) solo aparece cuando `id_reporte_rea` está lleno; si está vacío, no se incluye.

### Árbol de relaciones REA

```
usuarios.usuario ←─ (FK: id_usuario en rea.reporte_evento)
    │
rea.reporte_evento
    ├── FK → shared.departamento
    ├── FK → shared.provincia
    ├── FK → shared.municipio
    ├── FK → edan.tipo_evento
    ├── FK → rea.estado_reporte
    │
    └── rea.reporte_afectacion (puente N:M)
         └── FK → rea.afectacion_categoria

edan.edan
    └── FK → rea.reporte_evento (nullable, id_reporte_rea)
```

---

## Consultas entre esquemas

Las tablas de diferentes esquemas se consultan igual que si estuvieran en el mismo,
sin penalidad de rendimiento (una sola BD, un pool de conexiones):

```sql
-- Obtener formularios EDAN con ubicación y responsable
SELECT e.id_edan,
       d.nombre AS departamento,
       m.nombre AS municipio,
       u.nombre AS encuestador,
       e.fecha_evento
FROM edan.edan e
JOIN shared.departamento d ON d.id = e.id_departamento
JOIN shared.municipio m ON m.id = e.id_municipio
JOIN usuarios.usuario u ON u.id_usuario = e.id_usuario;

-- Obtener reportes REA con ubicación y estado
SELECT r.id_reporte,
       r.comunidad,
       d.nombre AS departamento,
       m.nombre AS municipio,
       t.nombre AS tipo_evento,
       er.nombre AS estado,
       r.fecha_evento,
       r.descripcion
FROM rea.reporte_evento r
JOIN shared.departamento d ON d.id = r.id_departamento
JOIN shared.municipio m ON m.id = r.id_municipio
JOIN edan.tipo_evento t ON t.id_tipo_evento = r.id_tipo_evento
JOIN rea.estado_reporte er ON er.id_estado = r.id_estado;

-- EDANs que provienen de un reporte REA
SELECT e.id_edan, e.codigo_edan, r.comunidad, r.fecha_evento
FROM edan.edan e
JOIN rea.reporte_evento r ON r.id_reporte = e.id_reporte_rea;
```

---

## Vinculación `usuarios` ↔ `edan`

### FK de integridad

`edan.edan.id_usuario` referencia `usuarios.usuario(id_usuario)` mediante la
restricción `edan_id_usuario_fkey`. La base de datos rechaza formularios cuyo
`id_usuario` no exista (error `23503`), garantizando que todo EDAN tenga un
registrador válido.

### Autopoblado desde el token JWT

Si el payload de creación no incluye `id_usuario`, la API lo asigna
automáticamente desde el usuario autenticado (`router.py → crear_edan`):

```
POST /api/v1/edan/  { "codigo_edan": "...", "id_municipio": 20101 }
→ id_usuario = usuario del token (ej. admin = 2)
```

En el PUT (actualización) el `id_usuario` solo se modifica si el payload lo
envía explícitamente.

### Lectura anidada

El GET de un EDAN devuelve el objeto usuario completo anidado:

```json
{
  "id_edan": 1,
  "usuario": { "id_usuario": 2, "usuario": "admin", "nombre": "Administrador" },
  "responsable": { "nombre": "...", "cargo": "...", "fono": "...", "correo": "..." }
}
```

### Filtro por usuario en reportes

`listar_edans` y los reportes soportan `?id_usuario=N` para acotar por
registrador.

### Permisos por módulo

El acceso a todas las rutas `/api/v1/edan/*` está protegido por
`module_permiso("EDAN")`. El rol del usuario debe tener las acciones
CREATE/READ/UPDATE/DELETE para el módulo EDAN (ver `usuarios.permiso_aplicacion`
y `usuarios.aplicacion`).

---

## Árbol de Relaciones

```
shared.departamento
│
└── shared.provincia (FK: id_departamento)
    │
    └── shared.municipio (FK: id_provincia)
        │
        ├── edan.edan (FK: id_municipio, id_provincia, id_departamento)
        │    │
        │    ├── edan.edan_localidades (1:N, CASCADE)
        │    │    ├── edan_grupo_etario_detalle (1:N)
        │    │    ├── edan_localidades_impacto_poblacion (1:1)
        │    │    ├── edan_localidades_primera_respuesta (1:1)
        │    │    ├── edan_localidades_salud_establecimientos (1:N)
        │    │    ├── edan_localidades_salud_necesidades (1:1)
        │    │    ├── edan_localidades_danos_viales (1:N)
        │    │    ├── edan_localidades_danos_infra_publica (1:N)
        │    │    ├── edan_localidades_servicios_basicos (1:N)
        │    │    ├── edan_localidades_unidades_educativas (1:N)
        │    │    ├── edan_localidades_danos_vivienda (1:N)
        │    │    ├── edan_localidades_danos_agricultura (1:N, FK → shared.cultivo)
        │    │    ├── edan_localidades_danos_pecuario (1:N, FK → shared.pecuario)
        │    │    ├── edan_localidades_infra_productiva (1:N)
        │    │    ├── edan_localidades_proteccion (1:1)
        │    │    ├── edan_localidades_proteccion_grupos (1:N)
        │    │    └── edan_localidades_necesidades_humanitarias (1:1)
        │    │
        │    ├── FK → edan.tipo_evento (id_tipo_evento)
        │    ├── FK → edan.estado_edan (id_estado)
        │    ├── FK → usuarios.usuario (id_usuario)
        │    └── FK → rea.reporte_evento (nullable: id_reporte_rea)
        │
        └── rea.reporte_evento (FK: id_municipio, id_departamento)
             │
             ├── FK → edan.tipo_evento
             ├── FK → rea.estado_reporte
             ├── FK → usuarios.usuario (id_usuario)
             │
             └── rea.reporte_afectacion (puente N:M)
                  └── FK → rea.afectacion_categoria

usuarios.usuario ←── (FK: id_usuario en edan.edan, id_usuario en rea.reporte_evento)
    │
    └── usuarios.usuario_rol → usuarios.rol
```

---

## Archivos de referencia

| Archivo | Ubicación |
|---|---|
| Script SQL completo | `database/crear_db_sinagersat.sql` |
| Script geografía | `database/insert_provincias_municipios.sql` |
| Migración v1.4.0 | `database/migration_v1.4.0.sql` (modelo jerárquico por localidades) |
| Migración v1.4.1 | `database/migration_v1.4.1.sql` (`descripcion` en `edan.tipo_evento`) |
| Migración v1.4.2 | `database/migration_v1.4.2.sql` (permisos EDAN: solo rol 6 escribe; elimina acciones/aplicaciones TEST y VERIFY) |
| Migración v1.4.3 | `database/migration_v1.4.3.sql` (sync offline-first: `id_local` UNIQUE + índice `idx_edan_sync_pull`) |
| Backup pre-migración | `database/backup_pre_v1.4.0.sql` |
| Backup completo | `database/backup_2026_07_26.sql` |
| Config pgAdmin4 | `database/servers.json` |
| Iniciar BD | `database/iniciar_edan.sh` |
| Restaurar BD | `database/restore_db.sh` |
| Documentación | `docs/EDAN_BD.md` |
| Formulario original | `Formulario.pdf` |

---

## API — Formulario EDAN (`/api/v1/edan`)

Endpoints bajo `api/edan/` (router, service y schemas Pydantic anidados).
Todos requieren token JWT (`Authorization: Bearer`) y el permiso de módulo `EDAN`.

### Formulario principal

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/edan/` | Listar EDANs con filtros potentes |
| GET | `/api/v1/edan/{id}` | Obtener EDAN completo (cabecera + localidades anidadas + `reporte_rea`/`reportes_rea`) |
| POST | `/api/v1/edan/` | Crear EDAN con `localidades[]` anidadas (opcional `id_reporte_rea`) |
| PUT | `/api/v1/edan/{id}` | Actualizar cabecera (`id_reporte_rea: null` desvincula el REA) |
| DELETE | `/api/v1/edan/{id}` | Eliminar (soft por defecto; `?permanente=true` = físico con cascada) |

**Campo `id_reporte_rea`**: opcional en POST/PUT (puede ir vacío). Si se envía un valor, debe existir en `rea.reporte_evento` (404 si no); al crear/actualizar la API sincroniza el vínculo inverso `rea.reporte_evento.id_edan`. Respuesta GET: `reporte_rea` (detalle anidado del REA de origen, solo si está lleno) y `reportes_rea` (lista de REAs agrupados bajo el EDAN).

### Vinculación REA → EDAN

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/rea/reportes/{id}/edan` | Obtener el EDAN generado desde un reporte REA (404 si aún no tiene) |

### Localidades

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/edan/{id}/localidades` | Listar localidades de un EDAN |
| POST | `/api/v1/edan/{id}/localidades` | Crear localidad con sus 16 secciones |
| PUT | `/api/v1/edan/{id}/localidades/{id_localidad}` | Reemplazar localidad (borra y reinserta secciones) |
| DELETE | `/api/v1/edan/{id}/localidades/{id_localidad}` | Eliminar localidad |

### Reportes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/edan/reportes/mis-resumen` | Resumen agregado de EDANs de un usuario (totales + por estado/tipo de evento) |
| GET | `/api/v1/edan/reportes/mis-reportes` | EDANs completos (con localidades) de un usuario, paginados |
| GET | `/api/v1/edan/reportes/resumen` | Totales (EDANs, localidades, población) por estado y tipo de evento |
| GET | `/api/v1/edan/reportes/geografico` | Conteos por departamento/provincia/municipio |
| GET | `/api/v1/edan/reportes/agricultura` | Agregados de cultivos afectados |
| GET | `/api/v1/edan/reportes/pecuario` | Agregados de especies afectadas |
| GET | `/api/v1/edan/reportes/localidades` | Detalle paginado de localidades |

`mis-resumen` y `mis-reportes` usan el patrón de REA (`ROLES_BAJOS = (6,)`):
el rol 6 (UGR Municipio) siempre ve **sus propios** registros (ignora `id_usuario`);
los demás roles pueden pasar `id_usuario` para consultar el de cualquier usuario
(si no lo pasan, ven los suyos).

### Permisos por rol (migración v1.4.2)

| Rol | EDAN |
|---|---|
| 1 superadmin | CRUD completo |
| 2 admin | CRUD completo |
| 3 VIDECI Regional | Solo READ |
| 4 UGR Sectores | Solo READ |
| 5 DGR Gobernación | Solo READ |
| 6 UGR Municipio | CRUD completo (crea/edita/elimina) |
| 7 Responsable Local | Solo READ |
| 8 Alcalde | Solo READ |
| 9 VIDECI Departamental | Solo READ |

### Sincronización offline-first (migración v1.4.3)

Protocolo de sync **exclusivo del módulo EDAN** para flujo
móvil → servidor → PC → móvil (el móvil captura en campo sin conexión).

**Estructura:**

- `edan.edan.id_local` (`VARCHAR(64)`): identificador UUID generado en el
  dispositivo móvil, único (`edan_id_local_key`). Identifica al documento en
  todos los dispositivos mientras el servidor solo conoce `id_server`/`id_edan`.
- Índice `idx_edan_sync_pull (id_usuario, fecha_modificacion)`: soporta el pull
  incremental por usuario.
- `fecha_modificacion`: **autoridad de tiempo = servidor** (siempre `NOW()`).
  La fecha que envía el cliente solo sirve para detectar versiones atrasadas.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/edan/sync` | Push de EDANs (`EdanSyncIn {edans: [EdanCreate]}`). Crea si `id_local` no existe; actualiza si existe; responde convergido |
| GET | `/api/v1/edan/sync/pull` | Pull incremental: `id_usuario`, `fecha_desde`, `skip`, `limit` |

**Reglas de convergencia:**

- *Match*: primero por `id_local`; si no, por `id_server` (móvil que aún no
  persiste el id asignado).
- *Idempotencia*: re-push del mismo documento no duplica.
- *Conflicto*: last-write-wins. El cliente envía en `fecha_modificacion` la fecha
  de la última versión que conoce; si es anterior a la del servidor, su push se
  rechaza con `aplicado: False, conflicto: True` y recibe la versión vigente.
- *Borrado*: tombstones. El móvil envía `pendiente_eliminacion: true` →
  `soft_delete_edan` marca el registro y el otro dispositivo lo ve en el pull
  (con `GREATEST` para no retroceder la fecha).
- *Pull*: filtro `fecha_modificacion >= :fecha_desde` (el cliente guarda la mayor
  fecha recibida como marca de último sync).
- Crear/editar/eliminar localidades "bump" la cabecera (`_bump_edan_fecha` →
  `NOW()`, `sincronizado = FALSE`, `pendiente_actualizacion = TRUE`) para que el
  pull la vea como modificada.

**Respuestas de sync:**

| Campo | Significado |
|---|---|
| `id_local`, `id_edan` | Identidad del documento |
| `aplicado`, `conflicto` | Si el push se aplicó o se rechazó por versión atrasada |
| `tombstone` | `true` cuando el push era un borrado |
| `sincronizado` | `true` tras aplicar |
| `data` | Documento convergido (cabecera + localidades), el que el cliente debe guardar |

**Flujo típico:**

1. Móvil crea EDAN offline con `id_local = uuid4()`.
2. Con conexión: `POST /edan/sync` → servidor crea y devuelve `id_edan`.
3. PC hace `GET /edan/sync/pull` y completa el formulario (`PUT /edan/{id}`).
4. Móvil hace pull → recibe la versión del PC (cabecera + localidades).
5. Si el móvil intenta sobreescribir con una versión vieja → conflicto, gana el PC.
6. Móvil borra el EDAN → `pendiente_eliminacion: true` → el PC lo ve en el pull.

### Catálogos

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/v1/edan/tipo-evento`, `/api/v1/edan/tipo-evento/{id}` | CRUD tipo de evento |
| GET/POST | `/api/v1/edan/estados`, `/api/v1/edan/estados/{id}` | CRUD estados del EDAN |

### Filtros del listado y reportes (query params)

`q`, `id_departamento`, `id_provincia`, `id_municipio`, `id_tipo_evento`,
`id_estado`, `estado`, `id_usuario`, `fecha_evento_desde`, `fecha_evento_hasta`,
`fecha_creacion_desde`, `fecha_creacion_hasta`, `sincronizado`, `es_borrador`,
`pendiente_eliminacion`, `pendiente_actualizacion`, `con_foto`, `sin_foto`,
`imp_poblacion`, `imp_salud`, `imp_infraestructura`, `imp_servicios`,
`imp_educacion`, `imp_vivienda`, `imp_agropecuario`, `imp_proteccion`,
`imp_necesidades`, `tiene_agricultura`, `tiene_pecuario`.

Listado añade: `order_by` (whitelist: id_edan, codigo_edan, fecha_evento,
fecha_creacion, fecha_modificacion, total_poblacion_afectada, id_departamento,
id_municipio, estado, nombre_alcalde), `order` (asc/desc), `skip`, `limit`.

### Contenido anidado

Las respuestas devuelven **contenido** en lugar de ids cuando el id existe:

- `departamento` / `provincia` / `municipio` → objeto geográfico completo.
- `tipo_evento` / `estado` → objeto del catálogo.
- `usuario` → objeto del usuario responsable.
- En localidades: `danos_agricultura[].cultivo` (→ shared.cultivo) y
  `danos_pecuarios[].especie_obj` (→ shared.pecuario).

---

## Acceso desde aplicaciones

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="db_sinagersat",
    user="sinagersat",
    password="12345678"
)

cur = conn.cursor()
# Consultar con esquema
cur.execute("SELECT * FROM usuarios.usuario")
cur.execute("""
    SELECT e.* FROM edan.edan e
    JOIN shared.municipio m ON m.id = e.id_municipio
""")
# Consultar reportes REA
cur.execute("""
    SELECT r.*, t.nombre AS tipo_evento
    FROM rea.reporte_evento r
    JOIN edan.tipo_evento t ON t.id_tipo_evento = r.id_tipo_evento
""")
```

### Node.js (pg)
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'db_sinagersat',
  user: 'sinagersat',
  password: '12345678'
});

// Consulta multiesquema
const result = await pool.query(`
  SELECT d.nombre AS depto, m.nombre AS municipio, e.id_edan
  FROM edan.edan e
  JOIN shared.departamento d ON d.id = e.id_departamento
  JOIN shared.municipio m ON m.id = e.id_municipio
`);

// Consultar reportes REA
const reaResult = await pool.query(`
  SELECT r.comunidad, t.nombre AS tipo_evento, er.nombre AS estado
  FROM rea.reporte_evento r
  JOIN edan.tipo_evento t ON t.id_tipo_evento = r.id_tipo_evento
  JOIN rea.estado_reporte er ON er.id_estado = r.id_estado
`);
```

### JDBC (Java)
```
jdbc:postgresql://localhost:5432/db_sinagersat?user=sinagersat&password=12345678
```
