# Propuesta de identificación y sincronización para EDAN

## 1. Objetivo

Definir una convención de identificadores para que los registros EDAN
puedan crearse, editarse y sincronizarse desde la aplicación móvil o
desde la plataforma web, incluso cuando un dispositivo trabaje sin
conexión.

La propuesta mantiene los identificadores numéricos actuales para las
relaciones internas de PostgreSQL y añade un UUID estable para
identificar cada registro entre la aplicación, la web y el servidor.

> Este documento describe una propuesta de diseño. Antes de ejecutar
> cambios, hay que contrastarla con el esquema completo y el código
> vigente, preparar una migración compatible y probarla con una copia de
> la base de datos.

## 2. Regla general: `id` y `uuid`

En cada tabla que represente un registro de negocio que pueda crearse,
editarse o sincronizarse, se recomienda disponer de dos identificadores:

-   **`id_*`**: identificador numérico interno, generado por PostgreSQL.
    Se conserva para las claves primarias y las relaciones internas
    existentes.
-   **`uuid_*`**: identificador global y estable del registro, generado
    cuando se crea por primera vez en la aplicación móvil o en la web.
    Debe conservarse durante toda la vida del registro y ser único.

Ejemplo conceptual:

  -----------------------------------------------------------------------
  Campo                   Función                 Regla
  ----------------------- ----------------------- -----------------------
  `id_edan_localidad`     Identificador interno   Numérico, generado por
                          de la localidad EDAN    el servidor

  `uuid_edan_localidad`   Identificador estable   UUID, único y no cambia
                          de esa localidad entre  
                          móvil, web y servidor   
  -----------------------------------------------------------------------

No se debe generar un UUID nuevo cada vez que se sincroniza o modifica
un registro.

## 3. Convención de nombres

Usar el prefijo `uuid_` seguido del nombre de la entidad. Evitar nombres
ambiguos como `id_local` para identificar registros creados sin
conexión.

Ejemplos:

  -----------------------------------------------------------------------------------
  Tabla o entidad         Identificador interno        Identificador estable
  ----------------------- ---------------------------- ------------------------------
  Localidad EDAN          `id_edan_localidad`          `uuid_edan_localidad`

  Daño agrícola           `id_dano_agricultura`        `uuid_dano_agricultura`

  Daño pecuario           `id_dano_pecuario`           `uuid_dano_pecuario`

  Daño vial               `id_dano_vial`               `uuid_dano_vial`

  Daño a vivienda         `id_dano_vivienda`           `uuid_dano_vivienda`

  Establecimiento de      `id_establecimiento_salud`   `uuid_establecimiento_salud`
  salud                                                

  Unidad educativa        `id_unidad_educativa`        `uuid_unidad_educativa`

  Fotografía, si se       `id_fotografia`              `uuid_fotografia`
  gestiona como entidad                                
  independiente                                        
  -----------------------------------------------------------------------------------

Aplicar la misma convención a las demás tablas de secciones que
contengan registros editables o sincronizables, utilizando el nombre
real de cada tabla y su clave primaria correspondiente.

Los nombres de la tabla anterior son ejemplos de convención; deben
verificarse contra el esquema instalado antes de generar el SQL
definitivo.

## 4. Relaciones entre tablas

Las relaciones internas existentes pueden seguir utilizando claves
foráneas numéricas.

Por ejemplo:

-   `edan.edan_localidades.id_edan_localidad`: clave interna de la
    localidad.
-   Una tabla de sección mantiene `id_edan_localidad` como clave foránea
    para indicar a qué localidad pertenece.
-   La fila de la sección tiene su propio UUID estable, por ejemplo
    `uuid_dano_agricultura`.

El UUID de la localidad permite localizar la misma localidad desde el
móvil, la web o la API. Una vez que el servidor conoce el registro,
puede usar los identificadores numéricos para las relaciones internas.

**No es necesario sustituir todas las claves foráneas numéricas por
UUID** para conseguir sincronización multiplataforma.

## 5. Qué tablas deberían tener ambos identificadores

Añadir `id_*` y `uuid_*` a las tablas que representan entidades o
registros que se crean, editan, eliminan o sincronizan entre clientes.

En cambio, los catálogos estáticos y tablas de referencia ---por
ejemplo, listas cerradas que solo administra el servidor--- no necesitan
necesariamente un UUID propio. La decisión debe tomarse según si esos
registros requieren identidad estable entre sistemas.

En tablas de sección con relación uno a uno, se debe conservar la
estructura actual de clave primaria y clave foránea. Si la fila puede
sincronizarse de forma independiente, también necesita una identidad
estable mediante UUID; el diseño exacto dependerá de la estructura real
de esa tabla.

## 6. Creación y sincronización

### 6.1 Registro creado en el móvil sin conexión

1.  La aplicación genera `uuid_edan_localidad` al crear la localidad.
2.  Guarda el registro en SQLite con ese UUID.
3.  Las secciones y fotografías se vinculan al UUID de la localidad y
    cada registro sincronizable tiene su propio UUID.
4.  Cuando vuelve la conexión, la aplicación envía los cambios a la API.
5.  El servidor busca por UUID para identificar si el registro ya
    existe.
6.  Si no existe, crea el registro y asigna su `id_*` numérico.
7.  Si ya existe, actualiza o concilia el registro según las reglas de
    conflicto; no crea un duplicado.

### 6.2 Registro creado desde la web

1.  La web solicita la creación a la API.
2.  El servidor crea o acepta el UUID estable y registra el
    identificador numérico.
3.  La aplicación móvil obtiene el registro en la siguiente
    sincronización.
4.  Si el móvil estaba sin conexión, debe evitar crear otra localidad al
    recibirlo: compara el UUID estable.

### 6.3 Edición desde móvil y web

El UUID identifica el registro, pero **no resuelve por sí solo los
conflictos de edición**. Para evitar sobrescrituras silenciosas, la API
debe validar la versión o la fecha de la última modificación y aplicar
una política explícita de conflictos.

Como mínimo, se recomienda definir:

-   `fecha_creacion`
-   `fecha_modificacion`
-   `modificado_por`, si la autenticación permite identificar al usuario
-   un número de versión, por ejemplo `version_registro`, o un mecanismo
    equivalente de control de concurrencia
-   el estado de sincronización en el cliente móvil

Cuando dos clientes modifican la misma entidad a partir de una versión
anterior, el servidor debe detectar el conflicto y responder de forma
explícita. No se debe asumir que la fecha más reciente siempre
representa la edición correcta sin una regla acordada.

## 7. Secciones EDAN

Las secciones deben mantener la relación con la localidad EDAN y tener
una identidad estable para sus filas sincronizables.

-   Para registros de una sección con varias filas (uno a muchos), cada
    fila necesita su propio UUID.
-   Para secciones de una sola fila por localidad (uno a uno), debe
    respetarse la clave primaria y la restricción de unicidad actuales;
    el UUID puede identificar esa fila de manera estable.
-   La sincronización debe hacer *upsert* por UUID, no depender de que
    los identificadores numéricos del servidor coincidan con los del
    dispositivo.
-   Los identificadores numéricos de las secciones se conservan para las
    relaciones y consultas internas del servidor.

No conviene utilizar un mismo UUID para todas las filas de una sección.
Cada registro independiente debe tener el suyo.

## 8. Fotografías y archivos adjuntos

Las fotografías deben tener una identidad y un estado de sincronización
que permitan reintentar la carga sin duplicarlas.

Si se mantienen como entidad independiente, se recomienda un registro
con campos conceptuales como:

-   `id_fotografia`: identificador numérico interno.
-   `uuid_fotografia`: UUID estable de la fotografía.
-   `uuid_edan_localidad`: identidad estable de la localidad asociada.
-   UUID de la fila de sección asociada, cuando corresponda.
-   `ruta_archivo`: ruta o referencia al archivo almacenado.
-   `hash_archivo`: hash para comprobar integridad y detectar
    duplicados, si se implementa.
-   `fecha_creacion`.
-   `estado_sincronizacion`: pendiente, enviado o error.

El esquema final debe reflejar la relación real entre una fotografía, su
localidad y, cuando corresponda, el registro de sección. Si las
fotografías se guardan actualmente en columnas de las tablas de sección,
la migración debe contemplar esa estructura existente en vez de asumir
que ya existe una tabla independiente.

La subida de la fotografía debe poder reintentarse independientemente de
la sincronización de los datos del formulario. La API debe evitar crear
duplicados cuando se repite una petición de carga.

## 9. Compatibilidad con `id_local`

El esquema actual documentado utiliza `id_local` en
`edan.edan_localidades` como identificador local de tipo texto. La
propuesta es adoptar el nombre explícito `uuid_edan_localidad`.

No se recomienda eliminar o renombrar directamente `id_local` en
producción sin una transición controlada. Para mantener la
compatibilidad con la aplicación instalada y los endpoints actuales:

1.  Revisar todos los usos de `id_local` en la base de datos, la API, la
    aplicación móvil y la web.
2.  Añadir la nueva columna `uuid_edan_localidad`.
3.  Migrar los valores existentes válidos a la nueva columna,
    conservando la correspondencia entre registros.
4.  Generar UUID para los registros antiguos que no tengan un
    identificador válido, asegurando que no se dupliquen.
5.  Añadir una restricción de unicidad y validar que no queden valores
    nulos en los registros que deban sincronizarse.
6.  Adaptar la API para aceptar temporalmente el campo antiguo y el
    nuevo, si hace falta compatibilidad.
7.  Actualizar los clientes y probar sincronización en ambos sentidos.
8.  Retirar el campo antiguo solo cuando se haya comprobado que ningún
    cliente ni proceso lo necesita.

La migración debe ser transaccional cuando sea posible y ejecutarse
primero en una copia de la base de datos.

## 10. Reglas de integridad recomendadas

Para cada tabla sincronizable:

-   El UUID debe ser único.
-   El UUID debe mantenerse estable.
-   La API debe comprobar el UUID antes de insertar para evitar
    duplicados.
-   Los identificadores numéricos continúan siendo administrados por el
    servidor.
-   Las claves foráneas deben seguir garantizando la integridad
    referencial.
-   Las eliminaciones deben tener una política explícita para
    sincronización offline; no se debe borrar físicamente un registro en
    un cliente y esperar que el resto lo detecte automáticamente.
-   Los reintentos de sincronización deben ser idempotentes: repetir la
    misma petición no debe duplicar registros ni fotografías.
-   Los conflictos de edición deben quedar identificados y no
    sobrescribirse silenciosamente.

## 11. Plan de implementación

1.  **Inventariar el esquema:** listar tablas, claves primarias, claves
    foráneas, cardinalidad uno a uno/uno a muchos y endpoints actuales.
2.  **Definir el mapeo:** documentar por tabla el campo `id_*`, el campo
    `uuid_*`, las relaciones y las restricciones.
3.  **Diseñar la migración:** añadir UUID sin romper las claves ni los
    clientes actuales.
4.  **Actualizar la API:** implementar búsquedas y operaciones
    idempotentes por UUID, junto con el control de concurrencia.
5.  **Actualizar móvil y web:** generar o conservar UUID, guardar
    cambios pendientes y gestionar reintentos.
6.  **Sincronizar fotografías:** implementar identificadores estables,
    reintentos y verificación de integridad.
7.  **Probar escenarios:** alta móvil offline, alta web, edición desde
    ambos clientes, reintentos, pérdida de conexión, eliminación y
    conflicto simultáneo.
8.  **Desplegar gradualmente:** respaldar la base de datos, probar en
    entorno de desarrollo y conservar un plan de reversión.

## 12. Criterio final

La regla propuesta es:

> **Cada registro EDAN editable o sincronizable tiene un identificador
> numérico interno `id_*` y un UUID estable `uuid_*`. Las claves
> foráneas numéricas existentes se conservan para las relaciones
> internas; el UUID se utiliza para identificar el mismo registro entre
> móvil, web y API.**

Esta convención permite crear y editar registros desde cualquiera de los
clientes y constituye la base de la sincronización offline. Para que sea
segura, debe complementarse con control de concurrencia, operaciones
idempotentes, una estrategia de eliminación y sincronización
independiente de fotografías.
