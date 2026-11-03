# Backend: Gestión de Ayuda Humanitaria (Work Queue VIDECI)

**Versión:** v1.6 (motor de necesidades, v2.61.0)
**Base URL:** `/api/v2/ayuda-humanitaria`
**Necesidad:** Centro de trabajo (Work Queue) para el personal de VIDECI donde se
listan todos los expedientes de ayuda humanitaria (RIDA habilitados) y se gestionan
los Pasos 4 al 9 de la infografía VIDECI, en patrón Maestro-Detalle.

---

## 0. Cambios respecto a la v1.0 (decisiones tomadas)

Estas dos decisiones cambian el diseño:

1. **NO se modifica la tabla `solicitud`.** No se le agregan columnas
   (`id_evento_rida`, `id_usuario_asignado`, `fecha_ultimo_cambio_estado`,
   `id_estado_rida`). El expediente de ayuda humanitaria es la propia `solicitud`
   + las tablas nuevas que se describen aquí.
2. **El estado rida no es una columna: es el resultado de un Motor de
   Aprobaciones.** Se crea un motor de niveles (mismo modelo que
   [`APROBACIONES_RIDA.md`](./APROBACIONES_RIDA.md)) donde cada paso 4–9 es un
   nivel con estado propio. El `cat_estado_rida` pasa a ser **catálogo de badges
   derivados**, no un valor almacenado en la solicitud.

Consecuencia: `estado_rida`, `dias_en_estado`, `id_usuario_asignado` y
`fecha_ultimo_cambio_estado` **no se almacenan**: se derivan del motor en cada
lectura (igual que `estado_global` en `APROBACIONES_RIDA.md` §4).

### Decisiones v1.2 (implementación cerrada, migración v2.55.0)

3. **La orden de despacho (paso 7) y el acta (paso 8) REUTILIZAN `rida.entrega`.**
   No existen `orden_despacho` ni `acta_recepcion`: una fila de `entrega`
   (`tipo='AYUDA_HUMANITARIA'`) con las columnas nuevas `nro_orden`,
   `estado_despacho`, `firmas` (JSONB), `id_documento` y `observaciones_acta`
   ES la orden **y** su acta (§2.4). El detalle de artículos despachados vive
   en la existente `rida.entrega_detalle`.
4. **El motor de cálculo es DINÁMICO por KITS**: las fórmulas son datos en
   `rida.regla_calculo_kit` + `rida.detalle_parametro_kit`, cargables por API
   (§2.6). No existe ningún `sp_EjecutarMotorCalculo`: el motor corre en el
   backend (Python) y expone `POST /motor-calculo/preview` (no persiste) y
   `POST /motor-calculo` (persiste en `solicitud_articulo`).
5. **Rol de almacén = `id_rol 14`** (nuevo en v2.55.0). Los roles 3 y 9
   recibieron permiso `CREATE` en el módulo RIDA para poder ejecutar las
   acciones de paso.

### Decisiones v1.3 (implementación cerrada, migración v2.57.0)

6. **El motor de cálculo se REEMPLAZA por kits.** Se elimina
   `rida.cat_regla_calculo` (v2.55.0, fórmulas con `base`/`agregacion`/
   `factor`/`condiciones`) y en su lugar hay dos tablas (§2.6):
   `rida.regla_calculo_kit` (la regla: nombre, criterio de aplicación, rangos
   de edad en días, sexo, requiere gestante/discapacidad, `dias_duracion`
   libre) y `rida.detalle_parametro_kit` (los ARTÍCULOS de cada kit con su
   cantidad base DIARIA y mínimos/máximos por artículo).
7. **`dias_duracion` lo define el frontend** (libre por regla; `NULL` = se
   calcula por día). **Un mismo artículo en 2 kits SUMA sus cantidades.** La
   columna `sexo` (M/F) es opcional (p. ej. "Kit de Ropa Femenina"). **No hay**
   `condiciones` JSONB: los filtros son columnas tipadas. La ruta
   `/reglas-calculo` NO cambia.

### Decisiones v1.5 (implementación cerrada, migración v2.58.0)

8. **Ciclo de vida de reglas**: `regla_calculo_kit.estado` = `borrador` |
   `publicada`. **El motor SOLO corre reglas publicadas** (y `activo`). Una
   regla nace en `borrador`; publicar exige validar (422 si no) y crea una
   **versión inmutable** en `rida.regla_calculo_version`
   (`configuracion_json` = snapshot exacto de columnas + detalles). Editar una
   regla publicada la devuelve a `borrador`: hay que publicar de nuevo (se
   genera la versión `n+1`). Las 3 reglas migradas quedaron `publicada` con
   su versión 1 snapshot.
9. **Historial de ejecuciones**: `rida.ejecucion_calculo` (id_calculo UUID,
   modo `previsualizacion`|`operativo`, estado, fecha, usuario) +
   `rida.ejecucion_calculo_detalle` (por FAMILIA y artículo, con
   `id_version`). Solo el **modo operativo** queda en el historial; el
   preview no deja rastro. El total por artículo que va a
   `solicitud_articulo` se calcula EXACTAMENTE como siempre; el detalle por
   familia guarda el valor en crudo (`base × días × pob_familia`, sin
   redondeo ni clamp) — la suma de crudos es el pre-redondeo del total.
10. **`POST /calculos`**: contrato nuevo de ejecución (`modo`,
    `familias[]` subset solo en previsualización, `reglas[]` con versión
    exacta ejecutada desde su snapshot). Los endpoints históricos
    `/{id}/motor-calculo(/preview)` NO cambian; una ejecución persistida por
    cualquiera de las dos vías queda en el historial. El inventario NO
    interviene en la fórmula (`inventario_consultado: false`): la
    disponibilidad se comprueba tras la aprobación.

### Decisiones v1.6 (motor de necesidades, migración v2.61.0)

11. **Motor de necesidades independiente del motor de kits.** El motor de
    kits determina artículos de la solicitud (`solicitud_articulo`); este
    motor calcula las **necesidades de la población** (`rida.necesidad`).
    Las reglas viven en `rida.regla_necesidad` y se evalúan contra
    `evento_rida → formulario_rida → familia → integrante`.
12. **El motor manda al persistir.** Reemplaza las necesidades
    `fuente='manual'` de las categorías que cubre **para cada familia** y
    todas las filas `fuente='motor'` previas del evento; las categorías sin
    regla se conservan. El preview nunca escribe. `forzar` se acepta por
    contrato pero **no cambia** la semántica.
13. **Persistencia acotada al workflow:** solo en `ENVIADA` o
    `EN_APROBACION` (409 en el resto). El preview está permitido en
    cualquier etapa.
14. **Redondeo fijo:** `cantidad = ceil(cantidad_base × (dias_duracion or 1) ×
    poblacion_familia)`, sin `cantidad_min`/`cantidad_max`. Las condiciones
    son JSONB (`gestante`, `discapacidad`, `edad_min_dias`,
    `edad_max_dias`, `sexo`).

---

## 1. Mapeo del flujo de 9 pasos → niveles del motor

Los pasos 1–3 ya existen (validación departamental de la solicitud). El motor de
ayuda humanitaria arranca en el **paso 4** y termina en el **paso 9**. Cada paso
es un **nivel** del motor.

| Paso VIDECI | Nombre                     | Nivel del motor | Etapa(s) de `cat-etapas` | Estado actual |
|-------------|----------------------------|-----------------|--------------------------|---------------|
| 1           | Recepción                  | —               | `ENVIADA`                | Existe (v2.60.0: sin BORRADOR) |
| 2           | Revisión                   | —               | *(retiradas en v2.60.0)* | Ya no existe |
| 3           | Validación EDAN            | —               | *(retirada en v2.60.0)*  | Ya no existe |
| 4           | Evaluación Nacional        | `evaluacion`    | `EN_APROBACION`          | **Nuevo motor** |
| 5           | Determinación de artículos | `determinacion` | `APROBADA`               | **Nuevo motor** |
| 6           | Autorización               | `autorizacion`  | `AUTORIZADA`             | **Nuevo motor** |
| 7           | Almacén / orden de despacho| `almacen` + `despacho` | `EN_PREPARACION`, `PREPARADA`, `DESPACHADA` | **Nuevo motor** |
| 8           | Entrega / acta de recepción| `entrega`       | `RECIBIDA`, `ENTREGADA`  | **Nuevo motor** |
| 9           | Cierre                     | `cierre`        | `CERRADA`                | **Nuevo motor** |

El motor tiene **7 niveles**, en este orden **secuencial**:

```
evaluacion → determinacion → autorizacion → almacen → despacho → entrega → cierre
```

> **A diferencia del motor de visaciones de solicitudes (cadena NO estricta),
> este motor es SECUENCIAL:** no se puede despachar antes de autorizar. La
> única libertad es **devolver el nivel anterior** con observación (regla 2, §4).

---

## 2. Modelo de datos

### 2.1 El expediente (sin tocar `solicitud`)

Un expediente de ayuda humanitaria **es** una `solicitud` de la modalidad
"Ayuda Humanitaria" (`id_modalidad` correspondiente). Como `solicitud` no se
modifica, el **evento RIDA** y el **municipio** se resuelven por la jerarquía ya
existente (desde v2.41.0 la solicitud apunta DIRECTO al evento):

```
solicitud.id_evento_rida → evento_rida → edan (id_municipio, id_departamento, id_tipo_evento) → municipio / departamento / tipo_evento
```

El endpoint de listado hace ese JOIN. `codigo_rida` = `evento_rida.codigo`
(v2.46.0) y `fecha_solicitud` = `solicitud.fecha_inicio`. No hace falta ninguna
columna nueva en `solicitud`.

### 2.2 `cat_estado_rida` — catálogo de badges (derivados)

Catálogo de los estados visibles de la Work Queue. **No se guarda en la
solicitud**: es el conjunto de valores que el motor puede derivar (§4, regla 3).

```sql
CREATE TABLE cat_estado_rida (
  id_estado_rida   INT AUTO_INCREMENT PRIMARY KEY,
  codigo           VARCHAR(40) NOT NULL UNIQUE,   -- code que deriva el motor
  nombre           VARCHAR(80) NOT NULL,
  tono             VARCHAR(20) NOT NULL DEFAULT 'neutral',  -- warning|success|info|danger|neutral
  orden            INT NOT NULL DEFAULT 0,
  activo           TINYINT(1) NOT NULL DEFAULT 1
);
```

Semilla:

| `codigo`        | `nombre`         | `tono`    |
|-----------------|------------------|-----------|
| `EN_APROBACION` | En aprobación    | warning   |
| `APROBADA`      | Aprobada         | info      |
| `AUTORIZADA`    | Autorizada       | success   |
| `EN_PREPARACION`| En preparación   | warning   |
| `DESPACHADA`    | Despachada       | info      |
| `ENTREGADA`     | Entregada        | success   |
| `CERRADA`       | Cerrada          | neutral   |
| `OBSERVADA`     | Observada        | warning   |
| `RECHAZADA`     | Rechazada        | danger    |

### 2.3 El Motor de Aprobaciones

Dos tablas, mismo diseño que `APROBACIONES_RIDA.md` (§2). **La config es por
modalidad**; la instancia es **por solicitud**.

**a) Configuración de la cadena** (qué niveles participan y en qué orden):

```sql
CREATE TABLE rida.aprobacion_cadena_ayuda (
  id_cadena     BIGSERIAL PRIMARY KEY,
  id_modalidad  INTEGER NULL REFERENCES rida.cat_modalidad (id_modalidad) ON DELETE CASCADE,
  nivel         VARCHAR(20) NOT NULL
                CHECK (nivel IN ('evaluacion','determinacion','autorizacion',
                                 'almacen','despacho','entrega','cierre')),
  orden         SMALLINT NOT NULL,
  activo        BOOLEAN  NOT NULL DEFAULT TRUE,
  UNIQUE (id_modalidad, nivel)
);
```

> `id_modalidad = NULL` = cadena por defecto (los 7 niveles). Si una modalidad
> de ayuda necesita menos hitos, se define su propia cadena. El orden debe
> respetar el orden semántico de §1.

**b) Instancia del motor** (una fila por nivel por expediente):

```sql
CREATE TABLE rida.aprobaciones_ayuda_humanitaria (
  id_aprobacion  BIGSERIAL PRIMARY KEY,
  id_solicitud   BIGINT      NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
  nivel          VARCHAR(20) NOT NULL
                 CHECK (nivel IN ('evaluacion','determinacion','autorizacion',
                                  'almacen','despacho','entrega','cierre')),
  estado         VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente','aprobado','observado','espera_correccion')),
  observacion    TEXT,
  por            INTEGER     REFERENCES usuarios.usuario (id_usuario),
  fecha          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (id_solicitud, nivel)
);
```

| Campo | Cómo se llena | Descripción |
|---|---|---|
| `id_solicitud` | Automático | El expediente. `ON DELETE CASCADE`. |
| `nivel` | Al iniciar el motor | Uno de los 7 códigos de §1. |
| `estado` | **Solo el servidor** | `pendiente` / `aprobado` / `observado` / `espera_correccion` (§3). |
| `observacion` | Servidor al **devolver** | Motivo; solo vive en el nivel `observado`. |
| `por` | Servidor (token JWT) | Quién hizo la última acción en ese nivel. |
| `fecha` | Servidor | Cuándo. `CURRENT_TIMESTAMP` en cada UPDATE. |

> **Secciones opcionales por paso:** las tablas de §2.4 (`solicitud_evaluacion`,
> `solicitud_articulo`, `orden_despacho`, `acta_recepcion`) guardan el detalle
> funcional de cada paso; el **estado** del paso vive en el motor, no en ellas.

### 2.4 Tablas de detalle por paso (no tocan `solicitud`)

**Paso 5 — `solicitud_articulo`** (determinación de artículos / motor de cálculo):

```sql
CREATE TABLE solicitud_articulo (
  id_solicitud_articulo INT AUTO_INCREMENT PRIMARY KEY,
  id_solicitud          INT NOT NULL,
  id_articulo           INT NOT NULL,
  id_regla              INT NULL,               -- regla del motor que la generó
  cantidad              DECIMAL(12,2) NOT NULL DEFAULT 0,
  unidad                VARCHAR(30) NULL,
  aprobado              TINYINT(1) NOT NULL DEFAULT 0,
  fuente                VARCHAR(20) NOT NULL DEFAULT 'motor',  -- motor | manual
  observaciones         VARCHAR(500) NULL,
  fecha                 TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sa_solicitud FOREIGN KEY (id_solicitud) REFERENCES rida.solicitud(id_solicitud),
  CONSTRAINT fk_sa_articulo  FOREIGN KEY (id_articulo)  REFERENCES rida.cat_articulo(id_articulo),
  UNIQUE KEY uq_sa_solicitud_articulo (id_solicitud, id_articulo)
);
```

> DDL real en PostgreSQL: `database/migrations/v2.55.0_ayuda_humanitaria.sql`.

**Paso 4 — `solicitud_evaluacion`** (evaluación nacional):

```sql
CREATE TABLE solicitud_evaluacion (
  id_solicitud_evaluacion INT AUTO_INCREMENT PRIMARY KEY,
  id_solicitud            INT NOT NULL,
  id_usuario_tecnico      INT NULL,      -- técnico VIDECI a cargo
  observaciones           TEXT NULL,
  fecha                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_se_solicitud FOREIGN KEY (id_solicitud) REFERENCES solicitud(id_solicitud)
);
```

**Paso 7 — orden de despacho + Paso 8 — acta: REUTILIZAN `rida.entrega`** (v1.2):

No se crean tablas nuevas. Una fila de `rida.entrega` con
`tipo='AYUDA_HUMANITARIA'` es la orden de despacho **y** aloja el acta en la
misma fila. Columnas agregadas en v2.55.0:

| Columna | Uso |
|---|---|
| `nro_orden` | `OD-2026-0001` (UNIQUE parcial) |
| `estado_despacho` | `GENERADA` → `EN_PREPARACION` → `PREPARADA` → `DESPACHADA` |
| `firmas` | JSON `[{nombre, ci, cargo, fecha}]` (acta) |
| `id_documento` | PDF del acta en `repositorio.documentos` |
| `observaciones_acta` | Texto del acta |

- Artículos despachados: existente `rida.entrega_detalle` (id_articulo, cantidad, peso_kg, valor_bs).
- Recepción por familia: existente `rida.entrega_beneficiario` (id_familia, firma_digital, evidencia).

### 2.5 Valores derivados (NO son columnas)

| Campo del contrato | Cómo se deriva |
|---|---|
| `estado` (badge)        | `estado_global` del motor (§4, regla 3). |
| `dias_en_estado`        | Días desde `fecha` del **nivel no aprobado** actual (o `MAX(fecha)` si ya cerró). |
| `fecha_ultimo_cambio_estado` | `MAX(fecha)` de `aprobaciones_ayuda_humanitaria` del expediente. |
| `id_usuario_asignado` / `nombre_tecnico` | `por` del nivel actualmente accionable (primer `pendiente`/`observado`). |
| `tiene_motor`           | `EXISTS` una fila en `solicitud_articulo` del expediente. |

> Reiniciar `dias_en_estado` es automático: al moverse a otro nivel cambia el
> nivel accionable y con él su `fecha`.

### 2.6 `regla_calculo_kit` — motor de cálculo por KITS (v1.3, migración v2.57.0)

Las fórmulas de determinación de artículos **son datos**, no código: un KIT es
una regla con un criterio de aplicación y una lista de artículos (detalhes).
Se cargan y se editan por API (`/reglas-calculo`, §5.5). El motor corre en el
backend leyendo los kits activos contra la población del expediente:

```
evento_rida → formulario_rida → familia → integrante
```

**`rida.regla_calculo_kit`** — la regla:

| Campo | Descripción |
|---|---|
| `nombre_regla` | Nombre del kit. Ej. `Ración Alimentaria Familiar Estándar` |
| `criterio_aplicacion` | `POR_FAMILIA` \| `POR_INTEGRANTE` \| `POR_CONDICION_ESPECIAL` |
| `rango_edad_min_dias` / `max_dias` | Edad del integrante (0-24 meses = 730 días). NULL = sin límite |
| `requiere_gestante` / `requiere_discapacidad` | Filtros booleanos por condición |
| `sexo` | `M` \| `F` (opcional). P. ej. "Kit de Ropa Femenina" |
| `dias_duracion` | **Horizonte en días del kit (lo define el frontend).** `NULL` = cálculo por día |
| `redondeo` | `ninguno` \| `techo` \| `piso` (default `piso`) |
| `prioridad` / `orden` | Desempate del `id_regla` guía cuando un artículo se repite en 2 kits |
| `activo` | Solo los kits activos corren en el motor |

**`rida.detalle_parametro_kit`** — los artículos de cada kit:

| Campo | Descripción |
|---|---|
| `id_articulo` | Artículo que produce este detalle (FK `rida.cat_articulo`, RESTRICT) |
| `cantidad_base_diaria` | Ración del artículo **POR PERSONA al día** |
| `cantidad_min` / `cantidad_max` | Acotación del resultado de este detalle |

> `POR_FAMILIA` se evalúa contra las familias; `POR_INTEGRANTE` y
> `POR_CONDICION_ESPECIAL` contra los integrantes. `POR_CONDICION_ESPECIAL`
> exige al menos un filtro activo (edad, sexo, gestante o discapacidad).

**Fórmula del motor** (por detalle):

```
poblacion  = nº de filas del pool que cumplen TODOS los filtros del kit
cantidad   = clamp(redondeo(cantidad_base_diaria × dias_duracion × poblacion),
                   cantidad_min, cantidad_max)
            (dias_duracion NULL = 1)
```

Al persistir, las cantidades **SE SUMAN por artículo** (regla v1.3, decisión 7);
el `id_regla` guardado en `solicitud_articulo` es el del kit de **mayor
prioridad** (menor `prioridad`, luego menor `orden`, luego menor `id_regla`).

> **Unidad (v2.56.0):** la unidad de cada resultado no vive en la regla: se
> toma de `cat_articulo.unidad_de_medida`, que es **FK → `rida.cat_unidad_medida`**
> (`kit`, `caja`, `kg`, `litro`, `unidad`; CRUD `/rida/necesidades/cat-unidades-medida`).
> El motor sigue leyendo `a.unidad_de_medida` sin cambios.

**Ejecución** (dos endpoints, §5.4):

- `POST /motor-calculo/preview` → calcula y **devuelve sin persistir** (vista
  dinámica: una fila por detalle en `calculados` y el total por artículo en
  `articulos`).
- `POST /motor-calculo` → **suma por artículo** y hace upsert en
  `solicitud_articulo` con `fuente='motor'`; **nunca pisa filas
  `fuente='manual'`** salvo `{"forzar": true}`.

`tiene_motor` (§2.5) = `EXISTS` una fila en `solicitud_articulo`.

### 2.6.1 Ciclo de vida y versiones (v1.5, migración v2.58.0)

**`regla_calculo_kit.estado`** — `borrador` | `publicada` (default `borrador`).
Solo las reglas `publicada` (y `activo`) corren en el motor.

**`rida.regla_calculo_version`** — la configuración exacta publicada:

| Campo | Descripción |
|---|---|
| `id_version` / `id_regla` | Versión y regla (`UNIQUE(id_regla, numero_version)`) |
| `numero_version` | 1, 2, … por regla |
| `configuracion_json` | Snapshot JSONB: columnas del kit + array `detalles` |
| `fecha_publicacion` / `publicado_por` | Auditoría |

Flujo: **crear (borrador) → validar → simular → publicar → ejecutar**.
Publicar exige `{confirmar: true}` y validación OK (422 con
`{valida, errores[], advertencias[], resumen}` si no); ya publicada → 409.
Editar una publicada la devuelve a `borrador` (la versión publicada es
inmutable); para que el motor use los cambios, publicar de nuevo.

**`rida.ejecucion_calculo` + `rida.ejecucion_calculo_detalle`** — historial
(v2.58.0): solo el modo **operativo** registra (UUID `id_calculo`, modo,
estado, fecha, usuario; detalle por FAMILIA + artículo + `id_version`).

### 2.7 `regla_necesidad` — motor de necesidades de la población (v1.6, migración v2.61.0)

Este motor es **distinto** del motor de kits de §2.6: no calcula artículos de
la solicitud, calcula las **necesidades** (`rida.necesidad`) de las familias
del evento. Las reglas se cargan por API (`/reglas-necesidad`, §5.5) y se
evalúan contra la población:

```
evento_rida → formulario_rida → familia → integrante
```

**`rida.regla_necesidad`** — la regla:

| Campo | Descripción |
|---|---|
| `nombre` | Nombre de la regla (máx. 100). |
| `criterio_aplicacion` | `POR_FAMILIA` \| `POR_INTEGRANTE` \| `POR_CONDICION_ESPECIAL`. |
| `id_categoria_ayuda` / `id_articulo` | Deben coincidir; el artículo pertenece a la categoría. |
| `cantidad_base` | `NUMERIC(8,3) >= 0`; se multiplica por días y población. |
| `dias_duracion` | Horizonte en días (`>0`); `NULL` = 1 día. |
| `condiciones` | JSONB; claves permitidas: `gestante`, `discapacidad`, `edad_min_dias`, `edad_max_dias`, `sexo` (`M`/`F`). |
| `prioridad` / `orden` | Desempate del `id_regla` reportado cuando un artículo se repite. |
| `activo` | Solo las reglas activas corren en el motor. |

**Condiciones por criterio:**

- `POR_FAMILIA`: no admite condiciones (422 si se envían).
- `POR_INTEGRANTE`: cuenta integrantes; admite filtros opcionales.
- `POR_CONDICION_ESPECIAL`: exige al menos un filtro activo (422 si no).
- Gestante = `sexo='F' AND gestante_semanas > 0`; discapacidad =
  `id_discapacidad IS NOT NULL`; edad en días se calcula contra la fecha del
  evento/registro; los filtros se combinan con **AND**.

**Fórmula** (por familia y artículo):

```
poblacion_familia = nº de familias o integrantes que cumplen TODOS los filtros
cantidad          = ceil(cantidad_base × (dias_duracion or 1) × poblacion_familia)
```

- **Siempre techo** (`ROUND_CEILING`), sin mínimos ni máximos.
- Si dos reglas producen el mismo artículo para una familia, las cantidades se
  **suman**; `id_regla` reportado es el de menor `prioridad`, luego menor
  `orden`, luego menor `id_regla_necesidad`.

**Persistencia** (`POST /expedientes/{id}/motor-necesidades`):

- Requiere etapa `ENVIADA` o `EN_APROBACION` (409 si no); el preview no.
- Borra las necesidades `fuente='manual'` de las categorías cubiertas **para
  cada familia** (aunque cambie de artículo/cantidad) y todas las filas
  `fuente='motor'` del evento; luego inserta el resultado actual con
  `fuente='motor'`, `estado=false`, `prioridad=3`.
- Las categorías sin regla y sus necesidades manuales se conservan.
- `rida.familia.id_necesidad` (FK legacy) se nulifica defensivamente antes de
  borrar filas.
- `resumen` incluye `manuales_reemplazadas` y `motoras_eliminadas`.

**Respuesta** (`{success,message,data}`, snake_case):

```json
{
  "id_solicitud": 12,
  "persistido": true,
  "necesidades": [
    {"id_familia": 29, "id_localidad": 325643, "localidad": "Comunidad San Miguel",
     "id_articulo": 15, "articulo": "Arroz", "categoria": "Alimentos",
     "cantidad": 15, "unidad": "kg", "fuente": "motor", "id_regla": 1}
  ],
  "resumen": {"familias": 7, "articulos_distintos": 3, "unidades": 157,
              "manuales_reemplazadas": 3, "motoras_eliminadas": 16}
}
```

> El frontend aplica `toCamelCase`; el backend responde **snake_case**.

---

## 3. Estados de cada nivel (idénticos al motor de visaciones)

| Estado | Significado |
|---|---|
| `pendiente` | No ha decidido todavía. |
| `aprobado` | El nivel aprobó (quién/cuándo en `por`/`fecha`). |
| `observado` | Le devolvieron; **debe corregir**. Motivo en `observacion`. |
| `espera_correccion` | Devolvió al anterior y **espera** la corrección. |

---

## 4. Reglas del motor (secuencial)

### Regla 0 — `iniciar(solicitud)`

Se dispara con la solicitud en `ENVIADA` (v2.60.0; antes `VALIDADA`) y exige el
checklist de instancia 1 completo (409 si no). Crea una fila `pendiente` por cada
nivel de `resolver_cadena(id_modalidad)` y avanza la solicitud a
`EN_APROBACION`. El nivel accionable inicial es `evaluacion`.

### Regla 1 — `aprobar(nivel)` (`aprobado: true`)

1. La `solicitud` existe (si no → **404**).
2. El `nivel` pertenece a la cadena de su modalidad (si no → **400**).
3. **Cadena secuencial:** el nivel anterior en la cadena debe estar `aprobado`
   (si no → **409**, salvo que sea el primer nivel).
4. Marca el nivel `aprobado`, limpia `observacion`, guarda `por`/`fecha`.
5. Si este nivel venía de `observado`, el nivel anterior que había devuelto pasa
   de `espera_correccion` → `pendiente`.
6. Si **toda la cadena** queda `aprobado` → la solicitud pasa a `CERRADA`.

Cada acción de paso (§5.4) internamente ejecuta `aprobar(nivel)`; por eso el
backend del paso debe registrar también la fila del motor.

### Regla 2 — `devolver(nivel)` (`aprobado: false`)

1. No se puede devolver desde el **primer nivel** de la cadena → **400**.
2. `observacion` obligatoria (≥10 caracteres; si no → **422**).
3. El **nivel anterior** pasa a `observado` (motivo en su fila).
4. El **nivel actual** pasa a `espera_correccion`.

### Regla 3 — `estado_global` derivado → badge (`cat_estado_rida`)

```
1. Si algún nivel está 'observado'              → OBSERVADA
2. Si la solicitud fue rechazada                → RECHAZADA
3. Si toda la cadena está 'aprobado'            → CERRADA
4. Si no, el primer nivel NO-aprobado define    → badge del nivel:
     evaluacion       → EN_APROBACION
     determinacion    → APROBADA
     autorizacion     → AUTORIZADA
     almacen          → EN_PREPARACION
     despacho         → DESPACHADA
     entrega          → ENTREGADA
```

### Regla 4 — autorización (rol + alcance)

> **Cambio de política v1.4 (15-oct-2026):** en el motor participan SOLO los
> roles **3 y 9**, con las **mismas funciones** en los 7 niveles (1 y 2
> mantienen el bypass total). El rol 14 (Almacén) queda **fuera del motor**
> (conserva sus permisos RIDA y su alcance para el resto del módulo). Los
> roles 5 y 6 no cambian (nunca tuvieron niveles en este motor).

| Nivel | Roles | Alcance |
|---|---|---|
| `evaluacion`   | 3 (VIDECI Regional), 9 (VIDECI Departamental) | nacional |
| `determinacion`| 3, 9 | nacional |
| `autorizacion` | 3, 9 | nacional |
| `almacen`      | 3, 9 | departamento |
| `despacho`     | 3, 9 | departamento |
| `entrega`      | 3, 9 | departamento |
| `cierre`       | 3, 9 | nacional |

Además: el `id_usuario` del token debe tener el rol del nivel; el alcance debe
cubrir el municipio/departamento del expediente.

---

## 5. Endpoints REST

Prefijo completo: `/api/v2/ayuda-humanitaria/expedientes`.

### 5.1 Listado (Work Queue) — `GET /api/v2/ayuda-humanitaria/expedientes`

JOIN: `solicitud ⨝ formulario ⨝ localidad ⨝ evento_rida ⨝ tipo_evento ⨝ municipio ⨝ departamento`,
más el `estado_global` derivado del motor (§2.5).

| Query param       | Tipo    | Descripción |
|-------------------|---------|-------------|
| `estado`          | string  | Código de `cat_estado_rida` (ej. `EN_APROBACION`) |
| `id_municipio`    | int     | Filtro por municipio |
| `id_departamento` | int     | Filtro por departamento |
| `id_modalidad`    | int     | Filtro por tipo de solicitud (modalidad) |
| `tipo_evento`     | string  | Filtro por tipo de evento RIDA (texto) |
| `fecha_desde`     | date    | Rango inicial de `fecha_inicio` |
| `fecha_hasta`     | date    | Rango final de `fecha_inicio` |
| `q`               | string  | Búsqueda por código RIDA o municipio |
| `skip` / `limit`  | int     | Paginación (`limit` default 20, máx 100) |
| `todos`           | bool    | `true` para omitir paginación (lotes/KPIs) |

Respuesta `200`:

```json
{
  "success": true,
  "total": 12,
  "data": [
    {
      "id_solicitud": 101,
      "id_evento_rida": 45,
      "codigo_rida": "RIDA-2026-045",
      "formulario": 32,
      "id_modalidad": 1,
      "nombre_modalidad": "Ayuda Humanitaria",
      "id_municipio": 70101,
      "nombre_municipio": "Santa Cruz de la Sierra",
      "id_departamento": 7,
      "nombre_departamento": "Santa Cruz",
      "tipo_evento": "Granizadas",
      "fecha_solicitud": "2026-09-30T10:00:00",
      "estado": { "id_estado_rida": 1, "codigo": "EN_APROBACION", "nombre": "En aprobación", "tono": "warning" },
      "dias_en_estado": 4,
      "id_usuario_asignado": 14,
      "nombre_tecnico": "Lic. Ana Roca",
      "tiene_motor": false
    }
  ]
}
```

### 5.2 Detalle — `GET /api/v2/ayuda-humanitaria/expedientes/{id_solicitud}`

```json
{
  "success": true,
  "data": {
    "...campos del listado...",
    "aprobacion": {
      "cadena": ["evaluacion","determinacion","autorizacion","almacen","despacho","entrega","cierre"],
      "estado_global": "EN_APROBACION",
      "niveles": {
        "evaluacion":    { "estado": "pendiente", "observacion": null, "por": null, "fecha": null },
        "determinacion": { "estado": "pendiente", "observacion": null, "por": null, "fecha": null }
      }
    },
    "evaluacion": { "id_usuario_tecnico": 14, "observaciones": "...", "fecha": "2026-10-01T09:00:00" },
    "articulos": [
      { "id_articulo": 12, "articulo": "Carpa familiar", "cantidad": 45, "unidad": "unidad", "aprobado": true }
    ],
    "orden_despacho": { "id_orden_despacho": 3, "nro_orden": "OD-2026-0001", "estado": "GENERADA" },
    "acta_recepcion": { "id_acta_recepcion": 1, "id_documento": 900, "firmas": [] },
    "documentos": [ "...repositorio del evento RIDA y del EDAN (solo lectura)" ]
  }
}
```

### 5.3 Motor de aprobaciones

```
GET  /api/v2/ayuda-humanitaria/expedientes/{id_solicitud}/aprobacion
PUT  /api/v2/ayuda-humanitaria/expedientes/{id_solicitud}/aprobacion/{nivel}
GET  /api/v2/ayuda-humanitaria/aprobacion/cadena
```

- El `GET` devuelve la máquina completa (igual forma que el `aprobacion` de §5.2).
- El `PUT` recibe el cuerpo canónico:

```json
// APROBAR
{ "aprobado": true }

// DEVOLVER (observacion obligatoria, ≥10 caracteres)
{ "aprobado": false, "observacion": "Falta la firma del acta de recepción" }
```

- `GET /aprobacion/cadena` es el catálogo de configuración (niveles, labels,
  roles, alcance y la cadena por modalidad), igual que
  `APROBACIONES_RIDA.md` §6.

| Código | ¿Cuándo? |
|---|---|
| **400** | `nivel` fuera de la cadena; devolver desde el primer nivel. |
| **401** | Sin token. |
| **403** | Rol/alcance insuficiente para ese nivel. |
| **404** | `id_solicitud` no existe. |
| **409** | El nivel anterior no está `aprobado` (cadena secuencial). |
| **422** | `aprobado:false` con `observacion` vacía o < 10 caracteres. |

### 5.4 Acciones de paso (cada una marca su nivel en el motor)

Estas acciones ejecutan su lógica de negocio **y** el `aprobar(nivel)`
correspondiente (regla 1). La devolución/observación se hace por el `PUT` de §5.3.

```
POST /{id_solicitud}/evaluacion        → guarda evaluación + aprueba 'evaluacion'
POST /{id_solicitud}/motor-calculo/preview → ejecuta los kits de regla_calculo_kit y DEVUELVE sin persistir (vista dinámica: calculados por detalle + articulos por artículo)
POST /{id_solicitud}/motor-calculo     → ejecuta los kits, SUMA por artículo y hace upsert en solicitud_articulo (fuente='motor'; no aprueba)
POST /{id_solicitud}/motor-necesidades/preview → evalúa regla_necesidad y DEVUELVE necesidades sin persistir (cualquier etapa)
POST /{id_solicitud}/motor-necesidades → calcula y persiste rida.necesidad (fuente='motor'); reemplaza manuales de categorías cubiertas; solo ENVIADA/EN_APROBACION
PUT  /{id_solicitud}/articulos/{id_articulo}  → ajuste manual (cantidad, aprobado); marca fuente='manual'
POST /{id_solicitud}/autorizar         → aprueba 'autorizacion'
POST /{id_solicitud}/rechazar          → solicitud RECHAZADA (congela las filas del motor)
POST /{id_solicitud}/orden-despacho    → genera fila rida.entrega (nro_orden) + aprueba 'almacen'
GET  /{id_solicitud}/orden-despacho    → lee la orden (+ entrega_detalle)
POST /{id_solicitud}/preparar          → mueve estado_despacho a EN_PREPARACION/PREPARADA
POST /{id_solicitud}/despachar         → estado_despacho=DESPACHADA + aprueba 'despacho'
POST /{id_solicitud}/acta-recepcion    → firma/id_documento en entrega + aprueba 'entrega'
POST /{id_solicitud}/cerrar            → aprueba 'cierre' → solicitud CERRADA
```

> El nivel `determinacion` se aprueba con `PUT /{id}/aprobacion/determinacion`
> (§5.3) una vez revisados los artículos del motor. Los pasos sin endpoint
> propio usan siempre el `PUT` genérico del motor.

### 5.5 Catálogos

| Método | Endpoint | Uso |
|--------|----------|-----|
| `GET`  | `/api/v2/ayuda-humanitaria/estados` | Badges del listado (`cat_estado_rida`) |
| `GET`  | `/api/v2/ayuda-humanitaria/aprobacion/cadena` | Niveles/roles/alcance y cadenas |
| `GET/POST/PUT/DELETE` | `/api/v2/ayuda-humanitaria/reglas-calculo` | Kits del motor de cálculo (§2.6); `GET` admite `estado=borrador\|publicada` |
| `GET/POST/PUT/DELETE` | `/api/v2/ayuda-humanitaria/reglas-necesidad` | Reglas del motor de necesidades (§2.7); `GET` completo con filtros `activo`, `criterio_aplicacion`, `id_categoria_ayuda`; escritura roles 1/2 |
| `GET`  | `/api/v2/usuarios?id_rol=9` | Técnicos VIDECI a asignar (hoy solo filtro por UN rol; multi-rol pendiente) |
| `GET`  | `/api/v2/rida/solicitudes/cat-modalidades` | Filtro por tipo de solicitud |
| `GET`  | `/api/v2/rida/necesidades/cat-articulos` | Artículos del motor |

### 5.6 Ciclo de vida de reglas + ejecuciones (v1.5, contrato `/calculos`)

| Método | Endpoint | Uso |
|--------|----------|-----|
| `GET`  | `/reglas-calculo/{id_regla}` | Consulta una regla (estado + `version_actual`) |
| `POST` | `/reglas-calculo/{id_regla}/validar` | Valida estructura/parámetros; **422** con `{valida, errores[], advertencias[], resumen}` si falla |
| `POST` | `/reglas-calculo/{id_regla}/simular` | Fórmula unitaria con población sintética (`{poblacion?, dias_duracion?, detalles?}`); NADA persiste |
| `POST` | `/reglas-calculo/{id_regla}/publicar` | Roles 1,2; `{confirmar:true}`; crea versión inmutable; 409 si ya publicada |
| `GET`  | `/reglas-calculo/{id_regla}/versiones` | Versiones publicadas (reciente primero) |
| `POST` | `/calculos` | Ejecuta el motor: `{id_solicitud, familias?, reglas?, modo, forzar?}` |
| `GET`  | `/calculos?id_solicitud=` | Historial del expediente (limit/skip/todos; recientes primero) |
| `GET`  | `/calculos/{id_calculo}` | Cabecera de una ejecución |
| `GET`  | `/calculos/{id_calculo}/detalle` | Resultados por familia y artículo |

`POST /calculos` — respuesta:

```json
{
  "calculo_id": "e9f31a50-…",          // null en previsualización (no hay historial)
  "estado": "completado",
  "modo": "operativo",
  "id_solicitud": 6,
  "resultados": [
    { "id_familia": 30, "articulos": [
      { "id_regla": 1, "id_articulo": 15, "articulo": "Arroz",
        "cantidad": 15.0, "unidad": "unidad" } ] }
  ],
  "articulos": [ { "id_articulo": 15, "articulo": "Arroz", "cantidad": 105.0 } ],
  "inventario_consultado": false,
  "necesidades_registradas": true
}
```

> `resultados` trae la cantidad **por familia en crudo** (sin redondeo ni
> clamp); `articulos`/`solicitud_articulo` traen el total histórico
> (`redondeo(base×días×población)` + clamp). El detalle por familia sumado
> reproduce el pre-redondeo del total. Errores: 404 regla/familia/ejecución
> inexistente · 409 etapa, regla en borrador o versión no vigente · 422
> validación · 400 `familias[]` en modo operativo o `confirmar` falso.

---

## 6. Flujo de ejemplo

Cadena por defecto (7 niveles). El expediente `#101` avanza normal hasta que
VIDECI devuelve desde `autorizacion`:

| Paso | Acción | Resultado |
|---|---|---|
| 0 | `iniciar(101)` (solicitud `ENVIADA` + checklist inst 1) | 7 filas `pendiente`, badge `EN_APROBACION` |
| 1 | `POST /101/evaluacion` | `evaluacion=aprobado`, badge `APROBADA` |
| 2 | `POST /101/motor-calculo` + ajuste manual | `articulos` poblados (aún `determinacion` pendiente) |
| 3 | `PUT /101/aprobacion/determinacion {"aprobado":true}` | `determinacion=aprobado`, badge `AUTORIZADA` |
| 4 | `PUT /101/aprobacion/autorizacion {"aprobado":false,"observacion":"Falta informe de daños"}` | `determinacion=observado` (+motivo), `autorizacion=espera_correccion`, badge `OBSERVADA` |
| 5 | `PUT /101/aprobacion/determinacion {"aprobado":true}` (corrige y reaprueba) | `determinacion=aprobado`, `autorizacion=pendiente`, badge `AUTORIZADA` |
| 6 | `PUT /101/aprobacion/autorizacion {"aprobado":true}` | `autorizacion=aprobado`, badge `EN_PREPARACION` |
| 7 | `POST /101/orden-despacho` | orden `OD-…` creada, `almacen=aprobado`, badge `DESPACHADA` |
| 8 | `POST /101/despachar` | `despacho=aprobado` |
| 9 | `POST /101/acta-recepcion` | `entrega=aprobado`, badge `ENTREGADA` |
| 10 | `POST /101/cerrar` | `cierre=aprobado`, badge `CERRADA` |

> El **badge** siempre sale de la regla 3, nunca de una columna.

---

## 7. Notas para el frontend

- El listado consume `GET /expedientes`; la vista ya existe:
  `AyudaHumanitariaListView.vue`. Los campos `estado`, `dias_en_estado`,
  `nombre_tecnico`, `tiene_motor` llegan derivados y **no requieren cambios** en
  el frontend.
- El detalle se abre en `/sinagersat/rida/evento/{id_evento_rida}/ayuda-humanitaria`
  (`RidaEventoDetailView` en modo `modoAyuda`).
- El motor se puede exponer al frontend con `GET /{id}/aprobacion` y
  `PUT /{id}/aprobacion/{nivel}`; conviene añadir esos dos métodos a
  `src/api/ayudaHumanitaria.ts` cuando el backend los entregue.
- Los pasos aún sin endpoint se muestran como "pendiente de backend"
  (`GRUPOS_PROCESO`).