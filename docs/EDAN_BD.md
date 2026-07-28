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
├── edan     → Formularios EDAN (23 tablas)
├── rea      → Reportes de Eventos Adversos (4 tablas)
├── rida     → (vacío - futuro sistema RIDA)
├── sinb     → (vacío - futuro sistema SINB)
└── recursos → (vacío - futura gestión de recursos)
```

**Total de tablas:** 38  
**Foreign Keys:** 35+  
**Índices:** 29+

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

23 tablas que componen el formulario de Evaluación de Daños y Análisis de Necesidades.
Incluye la tabla padre `edan`, 17 tablas hijas por sección y 5 catálogos propios.

### Tabla Padre: `edan.edan`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_edan` | BIGSERIAL PK | Identificador único |
| `codigo_edan` | VARCHAR(30) | Código interno EDAN |
| `id_departamento` | INTEGER FK | Departamento (FK → shared.departamento.id) |
| `id_municipio` | INTEGER FK | Municipio (FK → shared.municipio.id) |
| `nombre_alcalde` | VARCHAR(200) | Nombre del alcalde |
| `telefono_alcalde` | VARCHAR(30) | Teléfono del alcalde |
| `fecha_llenado` | DATE | Fecha de llenado |
| `fecha_evento` | DATE | Fecha del evento |
| `hora_evento` | TIME | Hora del evento |
| `localidades_afectadas` | INTEGER | Cantidad de localidades |
| `total_poblacion_afectada` | INTEGER | Total población afectada |
| `total_familias_afectadas` | INTEGER | Total familias afectadas |
| `total_familias_damnificadas` | INTEGER | Total familias damnificadas |
| `nombre_responsable` | VARCHAR(200) | Responsable del llenado |
| `cargo_responsable` | VARCHAR(100) | Cargo |
| `telefono_responsable` | VARCHAR(30) | Teléfono/celular |
| `email_responsable` | VARCHAR(150) | Correo electrónico |
| `usuario_registro` | INTEGER FK | Usuario que registró (FK → usuarios.usuario.id_usuario) |
| `fecha_registro` | TIMESTAMP | Auditoría |
| `fecha_actualizacion` | TIMESTAMP | Auditoría |
| `id_reporte_rea` | BIGINT FK | Reporte REA origen (FK → rea.reporte_evento.id_reporte, nullable) |

### Catálogos propios del formulario

| Tabla | Registros | Descripción |
|---|---|---|
| `tipo_evento` | 8 | Tipos de evento adverso (Inundación, Riada, etc.) |
| `grupo_etario` | 4 | Grupos de edad (0-5, 6-18, 19-60, 60+) |
| `servicio_basico` | 5 | Servicios básicos (Luz, Agua, Gas, etc.) |
| `categoria_proteccion` | 7 | Categorías de vulnerabilidad (Niños, Embarazadas, etc.) |
| `ayuda_humanitaria` | 9 | Tipos de ayuda (Alimentos, Refugio, etc.) |

### Tablas hijas (17)

| Tabla | Sección | Relación con edan.edan |
|---|---|---|
| `edan_poblacion_grupo` | 2 - Población | 1:N |
| `edan_tipo_evento` | 3.1 - Tipo de evento | 1:N (puente) |
| `edan_primera_respuesta` | 3.3 - Primera respuesta | 1:1 |
| `edan_salud_establecimiento` | 4.1 - Salud: establecimientos | 1:N |
| `edan_salud_necesidades` | 4.2 - Salud: necesidades | 1:1 |
| `edan_infraestructura_vial` | 5.1 - Infraestructura vial | 1:N |
| `edan_infraestructura_publica` | 5.2 - Infraestructura pública | 1:N |
| `edan_servicio_basico` | 6 - Servicios básicos | 1:N |
| `edan_educacion_dano` | 7.1 - Educación: daños | 1:N |
| `edan_educacion_afectacion` | 7.2 - Educación: afectación | 1:N |
| `edan_vivienda` | 8 - Vivienda | 1:N |
| `edan_agricultura` | 9.1 - Agricultura | 1:N |
| `edan_pecuaria` | 9.2 - Pecuaria | 1:N |
| `edan_infraestructura_productiva` | 9.3 - Infraestructura productiva | 1:N |
| `edan_proteccion` | 10 - Protección | 1:N |
| `edan_ayuda_humanitaria` | 11 - Ayuda humanitaria | 1:N |
| `edan_comunidad` | 12 - Comunidades | 1:N |

> Ver el detalle de cada tabla hija en la sección "Tablas Hijas" más abajo.

---

## Tablas Hijas

### Sección 2 - `edan.edan_poblacion_grupo`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_poblacion_grupo` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_grupo_etario` | INTEGER FK | Grupo de edad (FK → sinagersat.grupo_etario) |
| `fallecidos` | INTEGER | N° fallecidos |
| `heridos` | INTEGER | N° heridos |
| `desaparecidos` | INTEGER | N° desaparecidos |
| `observaciones` | TEXT | Observaciones |

### Sección 3.1 - `edan.edan_tipo_evento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_tipo_evento_edan` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_tipo_evento` | INTEGER FK | Tipo de evento (FK → edan.tipo_evento) |

### Sección 3.3 - `edan.edan_primera_respuesta`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_primera_respuesta` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `busqueda_requerimiento` | BOOLEAN | Búsqueda (Sí/No) |
| `busqueda_observaciones` | TEXT | Observaciones |
| `salvamento_requerimiento` | BOOLEAN | Salvamento/Rescate |
| `salvamento_observaciones` | TEXT | Observaciones |
| `evacuacion_requerimiento` | BOOLEAN | Evacuación |
| `evacuacion_observaciones` | TEXT | Observaciones |
| `otros_requerimiento` | BOOLEAN | Otros |
| `otros_observaciones` | TEXT | Observaciones |
| `observaciones_generales` | TEXT | Observaciones finales |

### Sección 4.1 - `edan.edan_salud_establecimiento`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_salud_establecimiento` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `nombre_establecimiento` | VARCHAR(200) | Nombre del establecimiento |
| `localidad_comunidad` | VARCHAR(200) | Localidad/Comunidad |
| `nivel_atencion` | SMALLINT (1/2/3) | Nivel de atención |
| `dano_parcial` | BOOLEAN | Daño parcial |
| `dano_total` | BOOLEAN | Daño total |
| `personal_medicos` | INTEGER | Médicos afectados |
| `personal_enfermeras` | INTEGER | Enfermeras afectadas |
| `personal_otros` | INTEGER | Otros personal |
| `observaciones` | TEXT | Observaciones |

### Sección 4.2 - `edan.edan_salud_necesidades`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_salud_necesidad` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `botiquin_personas` | INTEGER | Personas que requieren atención |
| `otras_necesidades` | TEXT | Otras necesidades |
| `observaciones` | TEXT | Observaciones |

### Sección 5.1 - `edan.edan_infraestructura_vial`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_infraestructura_vial` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `via_acceso_puentes` | VARCHAR(200) | Vías de acceso/puentes |
| `tramo` | VARCHAR(200) | Tramo |
| `localidad_origen` | VARCHAR(200) | Localidad origen |
| `localidad_destino` | VARCHAR(200) | Localidad destino |
| `dano_parcial_km` | DECIMAL(10,2) | Daño parcial en Km |
| `dano_total_km` | DECIMAL(10,2) | Daño total en Km |
| `necesidades_inmediatas` | TEXT | Necesidades inmediatas |
| `observaciones` | TEXT | Observaciones |

### Sección 5.2 - `edan.edan_infraestructura_publica`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_infraestructura_publica` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `localidad_comunidad` | VARCHAR(200) | Localidad/Comunidad |
| `tipo_estructura` | VARCHAR(200) | Tipo de estructura |
| `dano_parcial` | INTEGER | Daño parcial |
| `dano_total` | INTEGER | Daño total |
| `observaciones` | TEXT | Observaciones |

### Sección 6 - `edan.edan_servicio_basico`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_servicio_basico_edan` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_servicio_basico` | INTEGER FK | Servicio básico (FK → edan.servicio_basico) |
| `dano_parcial` | BOOLEAN | Daño parcial |
| `dano_total` | BOOLEAN | Daño total |
| `necesidades_inmediatas` | TEXT | Necesidades inmediatas |
| `observaciones` | TEXT | Observaciones |

### Sección 7.1 - `edan.edan_educacion_dano`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_educacion_dano` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `nombre_establecimiento` | VARCHAR(200) | Nombre del establecimiento |
| `comunidad` | VARCHAR(200) | Comunidad |
| `dano_parcial` | BOOLEAN | Daño parcial |
| `dano_total` | BOOLEAN | Daño total |
| `suspension_clases` | BOOLEAN | Suspensión de clases |
| `perdida_material` | BOOLEAN | Pérdida de material |
| `funciona_albergue` | BOOLEAN | Funciona como albergue |
| `observaciones` | TEXT | Observaciones |

### Sección 7.2 - `edan.edan_educacion_afectacion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_educacion_afectacion` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_educacion_dano` | INTEGER FK | Referencia al daño (FK → edan.educacion_dano) |
| `nombre_establecimiento` | VARCHAR(200) | Nombre del establecimiento |
| `estudiantes_afectados` | INTEGER | N° estudiantes |
| `profesores_afectados` | INTEGER | N° profesores |
| `administrativos_afectados` | INTEGER | N° administrativos |
| `total_afectados` | INTEGER | Total |
| `observaciones` | TEXT | Observaciones |

### Sección 8 - `edan.edan_vivienda`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_vivienda` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `comunidad` | VARCHAR(200) | Comunidad |
| `viviendas_dano_parcial` | INTEGER | Viviendas con daño parcial |
| `viviendas_dano_total` | INTEGER | Viviendas con daño total |
| `necesidades_inmediatas` | TEXT | Necesidades inmediatas |
| `observaciones` | TEXT | Observaciones |

### Sección 9.1 - `edan.edan_agricultura`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_agricultura` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `tipo_cultivo` | VARCHAR(200) | Tipo de cultivo |
| `hectareas_afectadas` | DECIMAL(10,2) | Hectáreas afectadas |
| `hectareas_perdidas` | DECIMAL(10,2) | Hectáreas perdidas |
| `necesidades_inmediatas` | TEXT | Necesidades inmediatas |
| `observaciones` | TEXT | Observaciones |

### Sección 9.2 - `edan.edan_pecuaria`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_pecuaria` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `tipo_especie` | VARCHAR(200) | Tipo de especie |
| `raza` | VARCHAR(200) | Raza |
| `animales_afectados` | INTEGER | Animales afectados |
| `animales_muertos` | INTEGER | Animales muertos |
| `necesidades_inmediatas` | TEXT | Necesidades inmediatas |
| `observaciones` | TEXT | Observaciones |

### Sección 9.3 - `edan.edan_infraestructura_productiva`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_infra_productiva` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `tipo` | VARCHAR(200) | Tipo de infraestructura |
| `dano_parcial` | INTEGER | Daño parcial |
| `dano_total` | INTEGER | Daño total |
| `observaciones` | TEXT | Observaciones |

### Sección 10 - `edan.edan_proteccion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_proteccion` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_categoria_proteccion` | INTEGER FK | Categoría (FK → sinagersat.categoria_proteccion) |
| `mujeres` | INTEGER | N° mujeres |
| `hombres` | INTEGER | N° hombres |
| `total` | INTEGER | Total |
| `apoyo_psicosocial` | BOOLEAN | Apoyo psicosocial |
| `reposicion_documentos` | BOOLEAN | Reposición de documentos |
| `observaciones` | TEXT | Observaciones |

### Sección 11 - `edan.edan_ayuda_humanitaria`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_ayuda_edan` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `id_ayuda_humanitaria` | INTEGER FK | Tipo de ayuda (FK → edan.ayuda_humanitaria) |
| `requiere` | BOOLEAN | Requiere (Sí/No) |
| `observaciones` | TEXT | Observaciones |

### Sección 12 - `edan.edan_comunidad`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_comunidad` | SERIAL PK | ID |
| `id_edan` | BIGINT FK | Referencia a EDAN |
| `nombre_comunidad` | VARCHAR(200) | Nombre de la comunidad/localidad/barrio |

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

Un reporte REA puede generar un formulario EDAN completo. La relación se establece mediante el campo `edan.edan.id_reporte_rea`:
- **NULL**: El EDAN fue creado directamente (sin reporte REA previo)
- **Con valor**: El EDAN fue creado a partir del reporte REA indicado

No se copia información del REA al EDAN; solo se establece la trazabilidad para saber de qué reporte surgió cada evaluación.

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
JOIN usuarios.usuario u ON u.id_usuario = e.usuario_registro;

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

## Árbol de Relaciones

```
shared.departamento
│
└── shared.provincia (FK: id_departamento)
    │
    └── shared.municipio (FK: id_provincia)
        │
        ├── edan.edan (FK: id_municipio, id_departamento)
        │    │
        │    ├── edan.poblacion_grupo (FK: id_grupo_etario → edan.grupo_etario)
        │    ├── edan.tipo_evento (FK: → edan.tipo_evento)
        │    ├── edan.primera_respuesta (1:1)
        │    ├── edan.salud_establecimiento (1:N)
        │    ├── edan.salud_necesidades (1:1)
        │    ├── edan.infraestructura_vial (1:N)
        │    ├── edan.infraestructura_publica (1:N)
        │    ├── edan.servicio_basico (FK: → edan.servicio_basico)
        │    ├── edan.educacion_dano (1:N)
        │    ├── edan.educacion_afectacion (1:N, FK → edan.educacion_dano)
        │    ├── edan.vivienda (1:N)
        │    ├── edan.agricultura (1:N)
        │    ├── edan.pecuaria (1:N)
        │    ├── edan.infraestructura_productiva (1:N)
        │    ├── edan.proteccion (FK: → edan.categoria_proteccion)
        │    ├── edan.ayuda_humanitaria (FK: → edan.ayuda_humanitaria)
        │    ├── edan.comunidad (1:N)
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

usuarios.usuario ←── (FK: usuario_registro en edan.edan, id_usuario en rea.reporte_evento)
    │
    └── usuarios.usuario_rol → usuarios.rol
```

---

## Archivos de referencia

| Archivo | Ubicación |
|---|---|
| Script SQL completo | `database/crear_db_sinagersat.sql` |
| Script geografía | `database/insert_provincias_municipios.sql` |
| Backup completo | `database/backup_2026_07_26.sql` (más reciente) |
| Config pgAdmin4 | `database/servers.json` |
| Iniciar BD | `database/iniciar_edan.sh` |
| Restaurar BD | `database/restore_db.sh` |
| Documentación | `docs/EDAN_BD.md` |
| Formulario original | `Formulario.pdf` |

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
