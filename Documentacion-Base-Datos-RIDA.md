# 15. Documentación de la Base de Datos RIDA

> **Análisis completo de la estructura de la base de datos PostgreSQL del Sistema RIDA (Registro de Intervención a Damnificados).**
> Base de datos: `rida` | Puerto: `5432` | Motor: PostgreSQL 16

---

## 1. Resumen General

La base de datos RIDA contiene **24 tablas** distribuidas en:

| Categoría | Cantidad | Tablas |
|---|---|---|
| **Catálogos** | 12 | `departamento`, `municipio`, `tipoevento`, `tipoafectacion`, `detalleperdida`, `categoriaarticulo`, `articulo`, `tiporespaldo`, `fuentedonacion`, `tipocontacto`, `contactomunicipio`, `rol` |
| **Operación** | 12 | `evento`, `eventotipoevento`, `formulariorida`, `formularioridadetalle`, `formularioridadetallefamilia`, `necesidadformulariorida`, `atencionevento`, `atencioneventomunicipio`, `tiporespaldoevento`, `usuario`, `usuariorol`, `bitacora` |

---

## 2. Diagrama Entidad-Relación

```
                                    ┌─────────────────┐
                                    │   DEPARTAMENTO   │
                                    │─────────────────│
                                    │ departamento_cod │ PK
                                    │ departamento_desc│
                                    └────────┬────────┘
                                             │ 1
                                             │
                                             │ *
                                    ┌────────┴────────┐
                                    │     MUNICIPIO    │
                                    │─────────────────│
                                    │ municipio_cod    │ PK
                                    │ municipio_desc   │
                                    │ departamento_cod │ FK
                                    │ municipio_poblacion_h │
                                    │ municipio_poblacion_m │
                                    └───┬─────────┬───┘
                                        │ 1       │ 1
                                        │         │
                                        │ *       │ *
                           ┌────────────┴──┐  ┌──┴─────────────────┐
                           │   EVENTO      │  │ CONTACTOMUNICIPIO   │
                           │──────────────│  │────────────────────│
                           │ evento_cod    │  │ municipio_cod       │ FK
                           │ evento_fecha  │  │ tipocontacto_cod    │ FK
                           │ municipio_cod │FK│ contactomunicipio_* │ (campos)
                           │ evento_desc   │  └────────────────────┘
                           │ evento_atendido│              │ *
                           │ ...          │               │ 1
                           └──┬───┬───┬──┘      ┌────────┴────────┐
                              │   │   │         │  TIPOCONTACTO    │
                              │   │   │         │─────────────────│
                              │   │   │         │ tipocontacto_cod │ PK
                              │   │   │         │ tipocontacto_desc│
                              │   │   │         └─────────────────┘
                    ┌─────────┘   │   └──────────────┐
                    │ *           │ *                 │ *
                    │ 1           │ 1                 │ 1
        ┌───────────┴──┐  ┌──────┴───────┐  ┌───────┴──────────────┐
        │EVENTOTIPOEVE │  │FORMULARIORIDA│  │ TIPORESPALDOEVENTO   │
        │──────────────│  │──────────────│  │─────────────────────│
        │evento_cod    │FK│formulariorida│PK│ tiporespaldoevento_* │ (campos)
        │tipoevento_cod│FK│evento_cod    │FK│ evento_cod           │ FK
        └──────┬───────┘  └──────┬───────┘│ tiporespaldo_cod     │ FK
               │ *               │ 1       └─────────────────────┘
               │ 1               │                    │ *
        ┌──────┴───────┐        │ *                  │ 1
        │  TIPOEVENTO   │        │ 1         ┌───────┴─────────────┐
        │──────────────│  ┌─────┴──────────┐ │   TIPORESPALDO      │
        │tipoevento_cod│PK │FORMULARIORIDA-│ │────────────────────│
        │tipoevento_desc│  │   DETALLE     │ │ tiporespaldo_cod    │ PK
        └──────────────┘  │──────────────│ │ tiporespaldo_desc   │
                          │formulariorida-│PK└─────────────────────┘
                          │  detalle_cod  │
                          │formulariorida_│FK
                          │  cod          │
                          └──────┬────────┘
                                 │ 1
                                 │ *
                        ┌────────┴─────────────────┐
                        │FORMULARIORIDADETALLEFAMILIA│
                        │──────────────────────────│
                        │formularioridadetallefamilia_cod│ PK
                        │formularioridadetalle_cod  │ FK
                        │formularioridadetallefamilia_*│ (campos)
                        └──────────────────────────┘

        ┌───────────────────┐         ┌───────────────────┐
        │ NECESIDADFORMULARI│         │  ATENCIONEVENTO    │
        │      ORIDA        │         │───────────────────│
        │──────────────────│         │atencionevento_cod  │ PK
        │necesidadformulari-│PK       │evento_cod          │ FK
        │  orida_cod        │         │articulo_cod        │ FK
        │formulariorida_cod │FK       │fuentedonacion_cod  │ FK
        │articulo_cod       │FK       │atencionevento_*    │ (campos)
        └─────────┬─────────┘         └───────────────────┘
                  │ *                        │ *
                  │ 1                        │ 1
         ┌────────┴────────┐        ┌────────┴────────┐
         │    ARTICULO      │        │ FUENTEDONACION   │
         │─────────────────│        │─────────────────│
         │ articulo_cod     │ PK     │ fuentedonacion_cod│ PK
         │ articulo_desc    │        │ fuentedonacion_desc│
         │categoriaarticulo_│FK      └─────────────────┘
         └────────┬─────────┘
                  │ *
                  │ 1
         ┌────────┴──────────┐
         │ CATEGORIAARTICULO  │
         │──────────────────│
         │categoriaarticulo_ │ PK
         │  cod              │
         │categoriaarticulo_ │
         │  desc             │
         └──────────────────┘

        ┌────────────────────────┐
        │ATENCIONEVENTOMUNICIPIO  │
        │────────────────────────│
        │atencioneventomunicipio_ │ PK
        │  cod                   │
        │evento_cod              │ FK
        │articulo_cod            │ FK
        │atencioneventomunicipio_│ (campos)
        └────────────────────────┘

        ┌───────────────────┐    ┌──────────────┐    ┌──────────┐
        │     USUARIO        │    │ USUARIOROL   │    │   ROL    │
        │──────────────────│    │──────────────│    │──────────│
        │ usuario_cod       │PK  │ usuario_cod  │FK  │ rol_cod  │ PK
        │ usuario_nombre    │    │ rol_cod      │FK  │ rol_desc │
        │ usuario_login     │    └──────────────┘    └──────────┘
        │ usuario_password  │
        │ municipio_cod     │FK
        └────────┬──────────┘
                 │ 1
                 │ *
        ┌────────┴──────────┐
        │     BITACORA       │
        │──────────────────│
        │ bitacora_cod      │ PK
        │ usuario_cod       │ FK
        │ bitacora_accion   │
        │ bitacora_fechahora│
        └──────────────────┘

        ┌────────────────────────┐
        │  DETALLEPERDIDA         │
        │────────────────────────│
        │ detalleperdida_cod      │ PK
        │ detalleperdida_desc     │
        │ tipoafectacion_cod      │ FK
        └────────────────────────┘
                  │ *
                  │ 1
         ┌────────┴──────────┐
         │  TIPOAFECTACION    │
         │──────────────────│
         │ tipoafectacion_cod │ PK
         │ tipoafectacion_desc│
         └──────────────────┘
```

---

## 3. Descripción de Cada Tabla

### 3.1. TABLA `departamento` — Catálogo de Departamentos

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `departamento_cod` | integer | **PK**, NOT NULL, default `nextval('departamento_departamento_cod_seq'::regclass)` | Código único del departamento |
| `departamento_desc` | varchar(100) | NOT NULL | Nombre del departamento |
| `creado_por` | integer | | Usuario que creó el registro |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` (baja lógica) |

**Registros:** 9 (departamentos de Bolivia)

---

### 3.2. TABLA `municipio` — Catálogo de Municipios

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `municipio_cod` | integer | **PK**, NOT NULL, default `nextval('municipio_municipio_cod_seq'::regclass)` | Código único del municipio (códigos INE) |
| `municipio_desc` | varchar(100) | NOT NULL | Nombre del municipio |
| `departamento_cod` | integer | **FK → `departamento.departamento_cod`**, NOT NULL | Departamento al que pertenece |
| `municipio_poblacion_h` | double precision | | Población hombres |
| `municipio_poblacion_m` | double precision | | Población mujeres |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 339 (todos los municipios de Bolivia)
**Relación:** `municipio.departamento_cod` → `departamento.departamento_cod` (N:1)

---

### 3.3. TABLA `tipoevento` — Catálogo de Tipos de Evento Adverso

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `tipoevento_cod` | integer | **PK**, NOT NULL, default `nextval('tipoevento_tipoevento_cod_seq'::regclass)` | Código único |
| `tipoevento_desc` | varchar(100) | NOT NULL | Nombre del tipo de evento |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 12 (Inundación, Sequía, Helada, Granizo, Incendio, etc.)

---

### 3.4. TABLA `tipoafectacion` — Catálogo de Tipos de Afectación

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `tipoafectacion_cod` | integer | **PK**, NOT NULL, default `nextval('tipoafectacion_tipoafectacion_cod_seq'::regclass)` | Código único |
| `tipoafectacion_desc` | varchar(100) | NOT NULL | Nombre del tipo de afectación |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 12 (Vivienda, Cultivos, Ganado, Personas, Vías, Servicios, etc.)

---

### 3.5. TABLA `detalleperdida` — Catálogo de Detalle de Pérdidas

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `detalleperdida_cod` | integer | **PK**, NOT NULL, default `nextval('detalleperdida_detalleperdida_cod_seq'::regclass)` | Código único |
| `detalleperdida_desc` | varchar(100) | NOT NULL | Descripción del detalle de pérdida |
| `tipoafectacion_cod` | integer | **FK → `tipoafectacion.tipoafectacion_cod`**, NOT NULL | Tipo de afectación padre |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 69 (sub-detalles por tipo de afectación)
**Relación:** `detalleperdida.tipoafectacion_cod` → `tipoafectacion.tipoafectacion_cod` (N:1)

---

### 3.6. TABLA `categoriaarticulo` — Catálogo de Categorías de Artículos

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `categoriaarticulo_cod` | integer | **PK**, NOT NULL, default `nextval('categoriaarticulo_categoriaarticulo_cod_seq'::regclass)` | Código único |
| `categoriaarticulo_desc` | varchar(100) | NOT NULL | Nombre de la categoría |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 12 (Alimentos, Alojamiento, Salud, Agua, etc.)

---

### 3.7. TABLA `articulo` — Catálogo de Artículos de Ayuda

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `articulo_cod` | integer | **PK**, NOT NULL, default `nextval('articulo_articulo_cod_seq'::regclass)` | Código único |
| `articulo_desc` | varchar(100) | NOT NULL | Nombre del artículo |
| `categoriaarticulo_cod` | integer | **FK → `categoriaarticulo.categoriaarticulo_cod`**, NOT NULL | Categoría a la que pertenece |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 45 (artículos específicos por categoría)
**Relación:** `articulo.categoriaarticulo_cod` → `categoriaarticulo.categoriaarticulo_cod` (N:1)

---

### 3.8. TABLA `tiporespaldo` — Catálogo de Tipos de Documento de Respaldo

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `tiporespaldo_cod` | integer | **PK**, NOT NULL, default `nextval('tiporespaldo_tiporespaldo_cod_seq'::regclass)` | Código único |
| `tiporespaldo_desc` | varchar(100) | NOT NULL | Nombre del tipo de documento |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 9 (Fotografía, Acta, Certificado, etc.)

---

### 3.9. TABLA `fuentedonacion` — Catálogo de Fuentes de Donación

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `fuentedonacion_cod` | integer | **PK**, NOT NULL, default `nextval('fuentedonacion_fuentedonacion_cod_seq'::regclass)` | Código único |
| `fuentedonacion_desc` | varchar(100) | NOT NULL | Nombre de la fuente |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 5 (Gobierno Nacional, ONG, Privados, etc.)

---

### 3.10. TABLA `tipocontacto` — Catálogo de Tipos de Contacto

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `tipocontacto_cod` | integer | **PK**, NOT NULL, default `nextval('tipocontacto_tipocontacto_cod_seq'::regclass)` | Código único |
| `tipocontacto_desc` | varchar(100) | NOT NULL | Nombre del tipo de contacto |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Registros:** 2 (Responsable, Técnico)

---

### 3.11. TABLA `contactomunicipio` — Contactos Municipales

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `municipio_cod` | integer | **PK compuesta**, **FK → `municipio.municipio_cod`**, NOT NULL | Municipio |
| `tipocontacto_cod` | integer | **PK compuesta**, **FK → `tipocontacto.tipocontacto_cod`**, NOT NULL | Tipo de contacto |
| `contactomunicipio_activo` | varchar(1) | | Estado del contacto |
| `contactomunicipio_nombre` | varchar(200) | NOT NULL | Nombre completo |
| `contactomunicipio_telefono` | varchar(50) | | Teléfono fijo |
| `contactomunicipio_celular` | varchar(50) | | Teléfono celular |
| `contactomunicipio_direccion` | varchar(200) | | Dirección |
| `contactomunicipio_email` | varchar(100) | | Correo electrónico |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**PK compuesta:** `(municipio_cod, tipocontacto_cod)`
**Relaciones:**
- `contactomunicipio.municipio_cod` → `municipio.municipio_cod` (N:1)
- `contactomunicipio.tipocontacto_cod` → `tipocontacto.tipocontacto_cod` (N:1)

---

### 3.12. TABLA `rol` — Catálogo de Roles del Sistema

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `rol_cod` | integer | **PK**, NOT NULL, default `nextval('rol_rol_cod_seq'::regclass)` | Código del rol |
| `rol_desc` | varchar(100) | NOT NULL | Nombre del rol |

**Registros:** 5

| rol_cod | rol_desc | Descripción |
|---|---|---|
| 1 | **Administrador** | VIDECI - acceso y validación total |
| 2 | **Municipio** | Técnicos UGR municipales (crean eventos/RIDA) |
| 3 | **Respuesta** | Unidad de Respuestas (aprueba SINAGER) |
| 4 | **Atencion** | Unidad de Suministros (aprueba/registra atención) |
| 5 | **Gobernacion** | Autoridad departamental (consulta/reportes) |

---

## 4. Tablas de Operación

### 4.1. TABLA `evento` — Eventos Adversos (Tabla Principal)

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `evento_cod` | integer | **PK**, NOT NULL, default `nextval('evento_evento_cod_seq'::regclass)` | Código único del evento |
| `evento_fecha` | date | NOT NULL | Fecha del evento adverso |
| `evento_atendido` | varchar(1) | NOT NULL, default `'N'` | Estado del ciclo: `N`=No atendido, `P`=SINAGER, `V`=Documental, `A`=Atención, `C`=Cerrado |
| `evento_fecha_atencion` | date | | Fecha de atención |
| `evento_desc` | varchar(150) | NOT NULL | Descripción del evento |
| `municipio_cod` | integer | **FK → `municipio.municipio_cod`**, NOT NULL | Municipio afectado |
| `evento_centro_lon` | numeric(14,7) | | Longitud GPS del centro del evento |
| `evento_centro_lat` | numeric(14,7) | | Latitud GPS del centro del evento |
| `evento_localidades_afectadas` | integer | NOT NULL | Número de localidades afectadas |
| `evento_familias_afectadas` | integer | NOT NULL | Número de familias afectadas |
| `evento_familias_damnificadas` | integer | NOT NULL | Número de familias damnificadas |
| `evento_observaciones_ugr` | varchar(500) | NOT NULL | Observaciones de la UGR |
| `evento_municipio_poblacion_h` | double precision | | Población municipio - hombres |
| `evento_municipio_poblacion_m` | double precision | | Población municipio - mujeres |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `evento.municipio_cod` → `municipio.municipio_cod` (N:1)
- Un evento puede tener múltiples formularios RIDA, atenciones, documentos de respaldo y tipos de evento

**Ciclo de estados (`evento_atendido`):**

| Valor | Estado | Transición |
|---|---|---|
| `N` | NO ATENDIDO | Creación del evento |
| `P` | SINAGER | `apruebaSinager` |
| `V` | DOCUMENTAL | `aprueba` |
| `A` | ATENCIÓN | `apruebaAtencion` |
| `C` | CERRADO | `cierre` |

---

### 4.2. TABLA `eventotipoevento` — Relación Evento-Tipo de Evento (N:M)

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `evento_cod` | integer | **PK compuesta**, **FK → `evento.evento_cod`**, NOT NULL | Evento |
| `tipoevento_cod` | integer | **PK compuesta**, **FK → `tipoevento.tipoevento_cod`**, NOT NULL | Tipo de evento |

**PK compuesta:** `(evento_cod, tipoevento_cod)`
**Relaciones:**
- `eventotipoevento.evento_cod` → `evento.evento_cod` (N:1)
- `eventotipoevento.tipoevento_cod` → `tipoevento.tipoevento_cod` (N:1)

**Nota:** Permite que un evento tenga múltiples tipos (ej. inundación + granizo).

---

### 4.3. TABLA `formulariorida` — Formularios RIDA (uno por localidad/campamento)

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `formulariorida_cod` | integer | **PK**, NOT NULL, default `nextval('formulariorida_formulariorida_cod_seq'::regclass)` | Código único del formulario |
| `evento_cod` | integer | **FK → `evento.evento_cod`**, NOT NULL | Evento al que pertenece |
| `formulariorida_localidad` | varchar(100) | NOT NULL | Nombre de la localidad |
| `formulariorida_campamento` | varchar(100) | NOT NULL | Número de carpa/campamento |
| `formulariorida_centro_lon` | numeric(14,7) | | Longitud GPS de la localidad |
| `formulariorida_centro_lat` | numeric(14,7) | | Latitud GPS de la localidad |
| `formulariorida_archivo` | text | | Archivo adjunto (formulario digitalizado, base64) |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `formulariorida.evento_cod` → `evento.evento_cod` (N:1)
- Un formulario RIDA tiene múltiples familias (`formularioridadetalle`) y necesidades (`necesidadformulariorida`)

---

### 4.4. TABLA `formularioridadetalle` — Detalle de Familias por Formulario RIDA

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `formularioridadetalle_cod` | integer | **PK**, NOT NULL, default `nextval('formularioridadetalle_formularioridadetalle_cod_seq'::regclass)` | Código único |
| `formulariorida_cod` | integer | **FK → `formulariorida.formulariorida_cod`**, NOT NULL | Formulario RIDA padre |
| `formularioridadetalle_responsable_familia` | varchar(100) | NOT NULL | Nombre del responsable/jefe de familia |
| `formularioridadetalle_ci` | varchar(100) | NOT NULL | Cédula de identidad del responsable |
| `formularioridadetalle_exp` | varchar(100) | NOT NULL | Expedido en (lugar de expedición CI) |
| `formularioridadetalle_personas_familia` | integer | NOT NULL | Número total de personas en la familia |
| `formularioridadetalle_nino_h` | integer | NOT NULL | Niños hombres |
| `formularioridadetalle_nino_m` | integer | NOT NULL | Niños mujeres |
| `formularioridadetalle_adolecente_h` | integer | NOT NULL | Adolescentes hombres |
| `formularioridadetalle_adolecente_m` | integer | NOT NULL | Adolescentes mujeres |
| `formularioridadetalle_adulto_h` | integer | NOT NULL | Adultos hombres |
| `formularioridadetalle_adulto_m` | integer | NOT NULL | Adultos mujeres |
| `formularioridadetalle_adultomayor_h` | integer | NOT NULL | Adultos mayores hombres |
| `formularioridadetalle_adultomayor_m` | integer | NOT NULL | Adultos mayores mujeres |
| `formularioridadetalle_embarazada_m` | integer | NOT NULL | Mujeres embarazadas |
| `formularioridadetalle_lactancia_m` | integer | NOT NULL | Mujeres en lactancia |
| `formularioridadetalle_discapacidad` | integer | NOT NULL | Personas con discapacidad |
| `tipoafectacion_cod` | integer | **FK → `tipoafectacion.tipoafectacion_cod`** | Tipo de afectación |
| `detalleperdida_cod` | integer | **FK → `detalleperdida.detalleperdida_cod`** | Detalle de la pérdida |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `formularioridadetalle.formulariorida_cod` → `formulariorida.formulariorida_cod` (N:1)
- `formularioridadetalle.tipoafectacion_cod` → `tipoafectacion.tipoafectacion_cod` (N:1)
- `formularioridadetalle.detalleperdida_cod` → `detalleperdida.detalleperdida_cod` (N:1)
- Una familia tiene múltiples integrantes (`formularioridadetallefamilia`)

---

### 4.5. TABLA `formularioridadetallefamilia` — Integrantes de la Familia

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `formularioridadetallefamilia_cod` | integer | **PK**, NOT NULL, default `nextval('formularioridadetallefamilia_formularioridadetallefamilia_cod_seq'::regclass)` | Código único |
| `formularioridadetalle_cod` | integer | **FK → `formularioridadetalle.formularioridadetalle_cod`**, NOT NULL | Familia padre |
| `formularioridadetallefamilia_responsable_familia` | boolean | | `true` = jefe de familia (solo uno por familia) |
| `formularioridadetallefamilia_nombre` | varchar(100) | NOT NULL | Nombre completo del integrante |
| `formularioridadetallefamilia_ci` | varchar(100) | NOT NULL | Cédula de identidad |
| `formularioridadetallefamilia_exp` | varchar(100) | NOT NULL | Expedido en |
| `formularioridadetallefamilia_fecha_nacimiento` | date | NOT NULL | Fecha de nacimiento |
| `formularioridadetallefamilia_sexo` | varchar(1) | NOT NULL | Sexo: `M` (Masculino) / `F` (Femenino) |
| `formularioridadetallefamilia_embarazada` | boolean | | ¿Embarazada? |
| `formularioridadetallefamilia_lactancia` | boolean | | ¿En lactancia? |
| `formularioridadetallefamilia_discapacidad` | boolean | | ¿Discapacidad? |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relación:** `formularioridadetallefamilia.formularioridadetalle_cod` → `formularioridadetalle.formularioridadetalle_cod` (N:1)
**Regla de negocio:** Solo un integrante por familia puede tener `responsable_familia = true`.

---

### 4.6. TABLA `necesidadformulariorida` — Necesidades por Formulario RIDA

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `necesidadformulariorida_cod` | integer | **PK**, NOT NULL, default `nextval('necesidadformulariorida_necesidadformulariorida_cod_seq'::regclass)` | Código único |
| `formulariorida_cod` | integer | **FK → `formulariorida.formulariorida_cod`**, NOT NULL | Formulario RIDA padre |
| `articulo_cod` | integer | **FK → `articulo.articulo_cod`**, NOT NULL | Artículo necesario |
| `necesidadformulariorida_cantidad` | double precision | NOT NULL | Cantidad necesaria |
| `necesidadformulariorida_estado` | varchar(1) | NOT NULL | Estado de la necesidad |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `necesidadformulariorida.formulariorida_cod` → `formulariorida.formulariorida_cod` (N:1)
- `necesidadformulariorida.articulo_cod` → `articulo.articulo_cod` (N:1)

---

### 4.7. TABLA `atencionevento` — Atención Departamental

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `atencionevento_cod` | integer | **PK**, NOT NULL, default `nextval('atencionevento_atencionevento_cod_seq'::regclass)` | Código único |
| `evento_cod` | integer | **FK → `evento.evento_cod`**, NOT NULL | Evento atendido |
| `articulo_cod` | integer | **FK → `articulo.articulo_cod`**, NOT NULL | Artículo entregado |
| `atencionevento_fecha` | date | NOT NULL | Fecha de entrega |
| `atencionevento_cantidad` | double precision | NOT NULL | Cantidad entregada |
| `atencionevento_peso` | double precision | NOT NULL | Peso total |
| `atencionevento_valor_bs` | double precision | NOT NULL | Valor en bolivianos (Bs) |
| `fuentedonacion_cod` | integer | **FK → `fuentedonacion.fuentedonacion_cod`**, NOT NULL | Fuente de donación |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `atencionevento.evento_cod` → `evento.evento_cod` (N:1)
- `atencionevento.articulo_cod` → `articulo.articulo_cod` (N:1)
- `atencionevento.fuentedonacion_cod` → `fuentedonacion.fuentedonacion_cod` (N:1)

**Diferencia vs municipal:** Incluye `fuentedonacion_cod` (recursos externos/donaciones).

---

### 4.8. TABLA `atencioneventomunicipio` — Atención Municipal

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `atencioneventomunicipio_cod` | integer | **PK**, NOT NULL, default `nextval('atencioneventomunicipio_atencioneventomunicipio_cod_seq'::regclass)` | Código único |
| `evento_cod` | integer | **FK → `evento.evento_cod`**, NOT NULL | Evento atendido |
| `articulo_cod` | integer | **FK → `articulo.articulo_cod`**, NOT NULL | Artículo entregado |
| `atencioneventomunicipio_fecha` | date | NOT NULL | Fecha de entrega |
| `atencioneventomunicipio_cantidad` | double precision | NOT NULL | Cantidad entregada |
| `atencioneventomunicipio_peso` | double precision | NOT NULL | Peso total |
| `atencioneventomunicipio_valor_bs` | double precision | NOT NULL | Valor en bolivianos (Bs) |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `atencioneventomunicipio.evento_cod` → `evento.evento_cod` (N:1)
- `atencioneventomunicipio.articulo_cod` → `articulo.articulo_cod` (N:1)

**Diferencia vs departamental:** NO incluye `fuentedonacion_cod` (usa recursos propios del municipio).

---

### 4.9. TABLA `tiporespaldoevento` — Documentos de Respaldo por Evento

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `tiporespaldoevento_cod` | integer | **PK**, NOT NULL, default `nextval('tiporespaldoevento_tiporespaldoevento_cod_seq'::regclass)` | Código único |
| `evento_cod` | integer | **FK → `evento.evento_cod`**, NOT NULL | Evento asociado |
| `tiporespaldo_cod` | integer | **FK → `tiporespaldo.tiporespaldo_cod`**, NOT NULL | Tipo de documento |
| `tiporespaldoevento_archivo` | text | NOT NULL | Archivo digital (base64) |
| `tiporespaldoevento_estado` | varchar(1) | NOT NULL | Estado: `P`=Pendiente, `A`=Aprobado, `R`=Rechazado |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `tiporespaldoevento.evento_cod` → `evento.evento_cod` (N:1)
- `tiporespaldoevento.tiporespaldo_cod` → `tiporespaldo.tiporespaldo_cod` (N:1)

---

### 4.10. TABLA `usuario` — Usuarios del Sistema

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `usuario_cod` | integer | **PK**, NOT NULL, default `nextval('usuario_usuario_cod_seq'::regclass)` | Código único del usuario |
| `usuario_nombre` | varchar(100) | NOT NULL | Nombre completo |
| `usuario_login` | varchar(100) | NOT NULL | Login de acceso |
| `usuario_password` | varchar(100) | NOT NULL | Contraseña (⚠️ en texto plano) |
| `usuario_email` | varchar(100) | NOT NULL | Correo electrónico |
| `usuario_telefono` | varchar(50) | NOT NULL | Teléfono |
| `usuario_celular` | varchar(50) | NOT NULL | Celular |
| `usuario_direccion` | varchar(200) | NOT NULL | Dirección |
| `municipio_cod` | integer | **FK → `municipio.municipio_cod`** | Municipio al que pertenece |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relaciones:**
- `usuario.municipio_cod` → `municipio.municipio_cod` (N:1)
- Un usuario tiene múltiples roles (`usuariorol`) y registros de auditoría (`bitacora`)

---

### 4.11. TABLA `usuariorol` — Relación Usuario-Rol (N:M)

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `usuario_cod` | integer | **PK compuesta**, **FK → `usuario.usuario_cod`**, NOT NULL | Usuario |
| `rol_cod` | integer | **PK compuesta**, **FK → `rol.rol_cod`**, NOT NULL | Rol asignado |

**PK compuesta:** `(usuario_cod, rol_cod)`
**Relaciones:**
- `usuariorol.usuario_cod` → `usuario.usuario_cod` (N:1)
- `usuariorol.rol_cod` → `rol.rol_cod` (N:1)

**Nota:** Un usuario puede tener múltiples roles.

---

### 4.12. TABLA `bitacora` — Registro de Auditoría

| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `bitacora_cod` | integer | **PK**, NOT NULL, default `nextval('bitacora_bitacora_cod_seq'::regclass)` | Código único |
| `usuario_cod` | integer | **FK → `usuario.usuario_cod`**, NOT NULL | Usuario que ejecutó la acción |
| `bitacora_accion` | varchar(100) | NOT NULL | Acción realizada (ej. "LOGIN USUARIO COD: 1") |
| `bitacora_fechahora` | timestamp without time zone | NOT NULL | Fecha y hora de la acción |
| `creado_por` | integer | | Usuario que creó |
| `creado_fecha` | timestamp without time zone | | Fecha de creación |
| `modificado_por` | integer | | Último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp without time zone | | Fecha de última modificación |
| `activo` | varchar(1) | | Estado: `S`/`N` |

**Relación:** `bitacora.usuario_cod` → `usuario.usuario_cod` (N:1)

---

## 5. Resumen de Relaciones entre Tablas

| Tabla Origen | FK | Tabla Destino | Tipo Relación |
|---|---|---|---|
| `municipio` | `departamento_cod` | `departamento` | N:1 |
| `contactomunicipio` | `municipio_cod` | `municipio` | N:1 |
| `contactomunicipio` | `tipocontacto_cod` | `tipocontacto` | N:1 |
| `detalleperdida` | `tipoafectacion_cod` | `tipoafectacion` | N:1 |
| `articulo` | `categoriaarticulo_cod` | `categoriaarticulo` | N:1 |
| `evento` | `municipio_cod` | `municipio` | N:1 |
| `eventotipoevento` | `evento_cod` | `evento` | N:1 |
| `eventotipoevento` | `tipoevento_cod` | `tipoevento` | N:1 |
| `formulariorida` | `evento_cod` | `evento` | N:1 |
| `formularioridadetalle` | `formulariorida_cod` | `formulariorida` | N:1 |
| `formularioridadetalle` | `tipoafectacion_cod` | `tipoafectacion` | N:1 |
| `formularioridadetalle` | `detalleperdida_cod` | `detalleperdida` | N:1 |
| `formularioridadetallefamilia` | `formularioridadetalle_cod` | `formularioridadetalle` | N:1 |
| `necesidadformulariorida` | `formulariorida_cod` | `formulariorida` | N:1 |
| `necesidadformulariorida` | `articulo_cod` | `articulo` | N:1 |
| `atencionevento` | `evento_cod` | `evento` | N:1 |
| `atencionevento` | `articulo_cod` | `articulo` | N:1 |
| `atencionevento` | `fuentedonacion_cod` | `fuentedonacion` | N:1 |
| `atencioneventomunicipio` | `evento_cod` | `evento` | N:1 |
| `atencioneventomunicipio` | `articulo_cod` | `articulo` | N:1 |
| `tiporespaldoevento` | `evento_cod` | `evento` | N:1 |
| `tiporespaldoevento` | `tiporespaldo_cod` | `tiporespaldo` | N:1 |
| `usuario` | `municipio_cod` | `municipio` | N:1 |
| `usuariorol` | `usuario_cod` | `usuario` | N:1 |
| `usuariorol` | `rol_cod` | `rol` | N:1 |
| `bitacora` | `usuario_cod` | `usuario` | N:1 |

---

## 6. Campos Comunes de Auditoría

Toda tabla de negocio incluye estos campos de control:

| Campo | Tipo | Descripción |
|---|---|---|
| `creado_por` | integer | Código del usuario que creó el registro |
| `creado_fecha` | timestamp | Fecha y hora de creación |
| `modificado_por` | integer | Código del último usuario que modificó |
| `ultima_modificacion_fecha` | timestamp | Fecha y hora de última modificación |
| `activo` | varchar(1) | `S` = Activo, `N` = Inactivo (baja lógica) |

---

## 7. Datos Precargados (Seed)

| Tabla | Registros | Contenido |
|---|---|---|
| `departamento` | 9 | 9 departamentos de Bolivia |
| `municipio` | 339 | Todos los municipios (códigos INE) |
| `tipoevento` | 12 | Inundación, Sequía, Helada, Granizo, Incendio, etc. |
| `tipoafectacion` | 12 | Vivienda, Cultivos, Ganado, Personas, Vías, Servicios, etc. |
| `detalleperdida` | 69 | Sub-detalles por tipo de afectación |
| `categoriaarticulo` | 12 | Alimentos, Alojamiento, Salud, Agua, etc. |
| `articulo` | 45 | Items específicos por categoría |
| `tiporespaldo` | 9 | Foto, Acta, Certificado, etc. |
| `fuentedonacion` | 5 | Gobierno Nacional, ONG, Privados, etc. |
| `tipocontacto` | 2 | Responsable, Técnico |
| `contactomunicipio` | 3 | Contactos de ejemplo |
| `rol` | 5 | Administrador, Municipio, Respuesta, Atención, Gobernación |

---

## 8. Usuarios Precargados

| # | Login | Contraseña | Rol | Nombre | Municipio |
|---|---|---|---|---|---|
| 1 | `admin` | `videci` | 1 – Administrador | Administrador | — |
| 2 | `villaabecia` | `villaabecia` | 2 – Municipio | Villa Abecia | CAMATAQUI (VILLA ABECIA) |
| 3 | `respuestas` | `respuestas` | 3 – Respuesta | Unidad de Respuestas | — |
| 4 | `suministros` | `suministros` | 4 – Atención | Unidad de Suministros | — |
| 5 | `batallas` | `batallas` | 2 – Municipio | Batallas | BATALLAS |
| 6 | `huata` | `huata` | 2 – Municipio | Santiago de Huata | SANTIAGO DE HUATA |
| 7 | `ballivian` | `ballivian` | 2 – Municipio | Waldo Ballivian | WALDO BALLIVIÁN |
| 8 | `curahuara` | `curahuara` | 2 – Municipio | Curahuara de Carangas | CURAHUARA DE CARANGAS |
| 9 | `salinas` | `salinas` | 2 – Municipio | Salinas de Garci Mendoza | SALINAS DE G. MENDOZA |
| 10 | `lapaz` | `lapaz` | 5 – Gobernación | Gobernación La Paz | — |

---

## 9. Flujo de Estados del Evento

```
┌──────────┐   /evento/graba   ┌───────────────┐
│  NUEVO   │────────────────▶ │ NO ATENDIDO(N)│
└──────────┘                  └───────┬───────┘
                                      │ apruebaSinager
                                      ▼
                                  ┌───────┐   devuelveInicio
                      ┌──────────▶│SINAGER│◀────────────────┐
                      │           └───┬────┘                 │
                      │ aprueba      │ apruebaDocumental     │
                      │              ▼                       │
                      │           ┌────────┐   devuelve      │
                      │           │DOCUMEN.│◀────────────────┤
                      │           └───┬────┘   Documental    │
                      │ apruebaAtenc  │                      │
                      │               ▼                      │
                      │           ┌────────┐   devuelveAtenc │
                      │           │ATENCIÓN│◀────────────────┘
                      │           └───┬────┘
                      │ cierre        │
                      │               ▼
                      │           ┌────────┐
                      └──────────▶│CERRADO │
                                  └────────┘
```

---

## 10. Diagrama Jerárquico de Datos (Evento → Reporte)

```
EVENTO
├── EVENTOTIPOEVENTO (tipos de evento)
├── FORMULARIORIDA (por localidad/campamento)
│   ├── FORMULARIORIDADETALLE (familias)
│   │   └── FORMULARIORIDADETALLEFAMILIA (integrantes)
│   └── NECESIDADFORMULARIORIDA (artículos necesarios)
├── ATENCIONEVENTO (atención departamental)
├── ATENCIONEVENTOMUNICIPIO (atención municipal)
└── TIPORESPALDOEVENTO (documentos de respaldo)
```

---

## 11. Notas Técnicas

1. **Motor de BD:** PostgreSQL 16, puerto 5432, base de datos `rida`
2. **Esquema:** Todos los nombres de tablas y columnas usan snake_case
3. **Secuencias:** Todas las PKs usan secuencias PostgreSQL (`nextval`)
4. **Baja lógica:** Ninguna tabla usa DELETE físico; todas usan campo `activo` con valores `S`/`N`
5. **Contraseñas:** Almacenadas en texto plano (⚠️ problema de seguridad conocido)
6. **Reportes:** JasperReports usa conexión hardcodeada a BD diferente (`gonzalog_rida`) — requiere corrección
