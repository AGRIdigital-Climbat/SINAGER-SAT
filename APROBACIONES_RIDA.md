# SINAGERSAT — Máquina de Aprobaciones de Solicitudes de ayuda (RIDA)

Documento de referencia de la **máquina de estados de aprobaciones** de las
solicitudes de ayuda del RIDA: qué tablas la soportan, qué significa cada estado,
qué reglas aplica el servidor automáticamente y qué contrato expone la API.

> **ESTADO: IMPLEMENTADA en backend.** Este documento es la referencia de lo que
> hace la API. Si algo aquí discrepa del código, el código manda: mira
> `api/rida/solicitudes/service.py` (sección *MÁQUINA DE APROBACIONES*) y
> `api/rida/solicitudes/router.py`.
>
> **v2.60.0 (2026-10-29) — MOTOR DE 7 NIVELES DESDE `ENVIADA`.** Reemplaza la
> cadena de 5 niveles de la v2.59.0 (`enviado → validacion → aprobado →
> despacho → entregado`) por `validacion → viceministro → dgea →
> revision_articulos → suministro → despacho → entrega`. Cambios de fondo:
>
> - Se elimina `BORRADOR` y las acciones `enviar/revisar/observar/corregir/
>   validar/iniciar-aprobacion/autorizar/cerrar`: la solicitud **nace en
>   `ENVIADA`** y el motor se materializa en el mismo `POST` de creación.
> - Nivel 1 (`validacion`) corre sobre `ENVIADA`; al aprobarlo la solicitud pasa
>   a `EN_APROBACION`. `revision_articulos` la lleva a `APROBADA`, `suministro`
>   a `AUTORIZADA`, `despacho` a `DESPACHADA` y `entrega` a `ENTREGADA` con
>   **cierre automático a `CERRADA`** en el mismo `PUT`.
> - 3 roles nuevos: **15 Viceministro**, **16 DGEA**, **17 Gestión de
>   Suministro**.
> - El nivel 1 exige **checklist de instancia 1 completo** y adjunta el
>   **Informe de validación** (PDF) en el mismo `PUT` multipart.
> - El nivel 4 (`revision_articulos`) exige un **cálculo persistido**
>   (`rida.ejecucion_calculo.modo = 'operativo'`) **solo si la modalidad tiene
>   motor** (`rida.cat_modalidad.tiene_motor_calculo = TRUE`); si no, el visado
>   es manual.
> - **Ayuda Humanitaria** queda excluida de este motor (conserva su cadena de 7
>   niveles en `api/ayuda_humanitaria`), pero su etapa de entrada también pasa a
>   `ENVIADA` y exige checklist de instancia 1 para iniciar su motor.
>
> Migración: `database/migrations/v2.60.0_motor_siete_niveles.sql` (idempotente,
> aplicada 2×).

---

## 1. Concepto general

La aprobación de una solicitud de ayuda es una **cadena de niveles con secuencia
ESTRICTA**. La cadena **canónica por defecto tiene 7 niveles**, en este orden:

```
validacion → viceministro → dgea → revision_articulos → suministro → despacho → entrega
    1             2           3            4                5           6         7
```

| Nivel | Lo realiza | Roles | Alcance | Etapa exigida | Etapa tras aprobar | Badge (`estado_global`) |
|---|---|---|---|---|---|---|
| `validacion` | VIDECI Departamental valida | 9 | departamento | `ENVIADA` | `EN_APROBACION` | `EN_VALIDACION` |
| `viceministro` | Viceministro | 15 | nacional | `EN_APROBACION` | `EN_APROBACION` | `VICEMINISTRO` |
| `dgea` | DGEA | 16 | nacional | `EN_APROBACION` | `EN_APROBACION` | `DGEA` |
| `revision_articulos` | Viceministro revisa artículos | 15 | nacional | `EN_APROBACION` | `APROBADA` | `REVISION_ARTICULOS` |
| `suministro` | Gestión de Suministro autoriza | 17 | nacional | `APROBADA` | `AUTORIZADA` | `SUMINISTRO` |
| `despacho` | VIDECI Departamental despacha | 9 | departamento | `AUTORIZADA` | `DESPACHADA` | `DESPACHO` |
| `entrega` | UGR Municipio confirma entrega | 6 | municipio | `DESPACHADA` | `ENTREGADA` → `CERRADA` | `EN_ENTREGA` (completo: `ENTREGADO`) |

> **Regla de negocio: secuencia estricta.** Solo se puede aprobar el **primer
> nivel no aprobado** de la cadena. El rol además solo actúa cuando la solicitud
> está en la **etapa que su nivel exige** (columna "Etapa exigida"). Los roles 1
> (superadmin) y 2 (admin) **bypasean rol y alcance** en cualquier nivel.
>
> **Devolver** (regla 2): sólo puede devolver quien tiene el turno, y sólo se
> devuelve un nivel cuyo anterior esté ya `aprobado`. El primer nivel de la
> cadena no se puede devolver.

La cadena es **configurable por modalidad** (§2.1): puede omitir niveles
intermedios (p. ej. `validacion → revision_articulos → suministro → despacho →
entrega`). **Restricción v2.60.0:** la cadena debe incluir `validacion`,
`revision_articulos`, `suministro`, `despacho` y `entrega` (son los niveles con
trigger de etapa; sin ellos la solicitud no puede avanzar).

> **Regla de diseño.** La cadena activa siempre es un **subconjunto ordenado de
> los 7 niveles canónicos** que incluye los 5 obligatorios: no se inventan
> niveles nuevos ni se reordena fuera de ese orden semántico.

Cada eslabón activo es una fila en `rida.aprobaciones_solicitud`. El servidor
aplica las reglas (quién puede aprobar/devolver, qué estado sigue, cuál es el
estado global) **automáticamente** en cada `PUT`; el frontend solo envía
"apruebo" o "devuelvo" (+ informe PDF en el nivel 1).

### Dos cosas distintas que no se confunden

| | `rida.solicitud.etapa` | esta máquina |
|---|---|---|
| Qué es | Ciclo de vida del expediente (13 etapas activas de `cat-etapas`) | Cadena de visaciones (7 niveles) |
| Quién la mueve | `PUT …/aprobacion/{nivel}` (acople motor ↔ etapa) y `POST …/rechazar` | `PUT /rida/solicitudes/{id}/aprobacion/{nivel}` |
| Estados | `ENVIADA` … `CERRADA` | `pendiente`…`espera_correccion` |

**Acople motor ↔ etapa (v2.60.0).** El motor arranca al crear la solicitud:

```
crear solicitud ──────────────────────► ENVIADA        (badge EN_VALIDACION)
ENVIADA        ── aprobar 'validacion' ► EN_APROBACION  (badge VICEMINISTRO)
EN_APROBACION  ── aprobar 'viceministro' ► EN_APROBACION (badge DGEA)
EN_APROBACION  ── aprobar 'dgea' ──────► EN_APROBACION  (badge REVISION_ARTICULOS)
EN_APROBACION  ── aprobar 'revision_articulos' ► APROBADA (badge SUMINISTRO)
APROBADA       ── aprobar 'suministro' ► AUTORIZADA     (badge DESPACHO)
AUTORIZADA     ── aprobar 'despacho' ──► DESPACHADA     (badge EN_ENTREGA)
DESPACHADA     ── aprobar 'entrega' ───► ENTREGADA ────► CERRADA (automático)
```

Las etapas `BORRADOR`, `EN_REVISION`, `OBSERVADA` y `VALIDADA` quedan
**inactivas** (`cat_etapa_solicitud.activo = FALSE`) y fuera de `TRANSICIONES`.
Las etapas intermedias `EN_SUMINISTROS`, `DESPACHO_AUTORIZADO`, `EN_TRANSPORTE`,
`RECIBIDA` y `EN_DISTRIBUCION` siguen en el catálogo pero tampoco son
alcanzables.

> **Exclusión Ayuda Humanitaria.** La modalidad 1 (`AYUDA_HUMANITARIA`) no usa
> este motor: gestiona su propia cadena de 7 niveles
> (`rida.aprobacion_cadena_ayuda`, `api/ayuda_humanitaria`). `resolver_cadena()`
> le devuelve cadena vacía, `GET …/aprobacion` responde cadena vacía y
> `estado_global` null, el `PUT` general responde **409** y
> `PUT cat-cadena-aprobacion/1` también. Su motor se inicia con
> `POST /ayuda-humanitaria/expedientes/{id}/iniciar` **desde `ENVIADA`** (v2.60.0;
> antes exigía `VALIDADA`) y también exige checklist de instancia 1 completo.

> Analogía: `etapa` ≡ `edan.estado_edan`; esta máquina ≡ `edan.aprobaciones_edan`.

---

## 2. Tabla `rida.aprobaciones_solicitud`

```sql
CREATE TABLE rida.aprobaciones_solicitud (
    id_aprobacion  BIGSERIAL PRIMARY KEY,
    id_solicitud   BIGINT      NOT NULL REFERENCES rida.solicitud (id_solicitud) ON DELETE CASCADE,
    nivel          VARCHAR(20) NOT NULL
                   CHECK (nivel IN ('validacion','viceministro','dgea',
                                    'revision_articulos','suministro',
                                    'despacho','entrega')),
    estado         VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','aprobado','observado','espera_correccion')),
    observacion    TEXT,
    por            INTEGER     REFERENCES usuarios.usuario (id_usuario),
    fecha          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_solicitud, nivel)
);
```

| Campo | Tipo | ¿Cómo se llena? | Descripción |
|---|---|---|---|
| `id_aprobacion` | `BIGSERIAL` | Automático | ID del registro (1 por nivel por solicitud). |
| `id_solicitud` | `BIGINT` FK | Automático | Solicitud a la que pertenece la cadena. `ON DELETE CASCADE`. |
| `nivel` | `VARCHAR(20)` | Automático (al crear la solicitud) | El eslabón: uno de los 7 códigos canónicos. Es el **identificador** que ve la API. |
| `estado` | `VARCHAR(20)` | **Solo el servidor** | Uno de los 4 estados (§3). |
| `observacion` | `TEXT` | Servidor al **devolver** | Motivo de la devolución. **Solo vive en la fila del nivel `observado`**. Se limpia cuando ese nivel vuelve a aprobar. |
| `por` | `INTEGER` FK usuario | Servidor (token JWT) | `id_usuario` que hizo la **última acción** en ese nivel. |
| `fecha` | `TIMESTAMP` | Servidor | Cuándo se hizo la última acción. |

> **Sin columna `ordinal`.** El orden de la cadena lo define
> `rida.aprobacion_cadena` y, si no hay configuración, la constante
> `NIVELES_APROB` del código.

### 2.1 Cadena configurable — tabla `rida.aprobacion_cadena`

```sql
CREATE TABLE rida.aprobacion_cadena (
    id_cadena       BIGSERIAL PRIMARY KEY,
    id_modalidad    INTEGER NULL REFERENCES rida.cat_modalidad (id_modalidad) ON DELETE CASCADE,
    nivel           VARCHAR(20) NOT NULL
                    CHECK (nivel IN ('validacion','viceministro','dgea',
                                     'revision_articulos','suministro',
                                     'despacho','entrega')),
    orden           SMALLINT NOT NULL CHECK (orden >= 1 AND orden <= 7),
    activo          BOOLEAN   NOT NULL DEFAULT TRUE,
    UNIQUE (id_modalidad, nivel)
);
```

| Campo | Descripción |
|---|---|
| `id_modalidad` | Modalidad de ayuda a la que aplica. **`NULL` = cadena por defecto**. |
| `nivel` | Uno de los 7 códigos canónicos. |
| `orden` | Posición dentro de la cadena (1 = primer nivel). Debe respetar el orden semántico. |
| `activo` | Permite **desactivar sin borrar**; las inactivas se ignoran al resolver. |

**Semilla (lo que va a producción):**

| `id_modalidad` | `nivel` | `orden` | `activo` |
|---|---|---|---|
| NULL | `validacion` | 1 | TRUE |
| NULL | `viceministro` | 2 | TRUE |
| NULL | `dgea` | 3 | TRUE |
| NULL | `revision_articulos` | 4 | TRUE |
| NULL | `suministro` | 5 | TRUE |
| NULL | `despacho` | 6 | TRUE |
| NULL | `entrega` | 7 | TRUE |

Ejemplo de una modalidad con **5 niveles** (omite `viceministro` y `dgea`; debe
incluir los 5 obligatorios):

| `id_modalidad` | `nivel` | `orden` | `activo` |
|---|---|---|---|
| 4 | `validacion` | 1 | TRUE |
| 4 | `revision_articulos` | 2 | TRUE |
| 4 | `suministro` | 3 | TRUE |
| 4 | `despacho` | 4 | TRUE |
| 4 | `entrega` | 5 | TRUE |

**Algoritmo de resolución** (`resolver_cadena(id_modalidad)`):

1. Traer las filas `activo = TRUE` de `id_modalidad = <la de la solicitud>`.
2. Si la modalidad no tiene ninguna, traer las de `id_modalidad IS NULL`.
3. Ordenar por `orden`. La precedencia es **"cadena propia o default"** a nivel
   de cadena, NO nivel a nivel.

**Edición:** `PUT /rida/solicitudes/cat-cadena-aprobacion/{id_modalidad}` (roles
1 y 2). Rechaza con **409** la modalidad Ayuda Humanitaria y con **400** una
cadena desordenada o sin los 5 niveles obligatorios.

> **Guard de configuración caliente:** el `PUT` responde **409** si hay
> solicitudes de esa modalidad con el motor activo
> (`ENVIADA`..`ENTREGADA`). Cambiar la cadena en vivo dejaría esas solicitudes
> con filas de niveles que ya no pertenecen a su cadena.

### Ejemplo de filas (Viceministro devolvió al nivel 1)

| `id_aprobacion` | `id_solicitud` | `nivel` | `estado` | `observacion` | `por` | `fecha` |
|---|---|---|---|---|---|---|
| 1 | 142 | `validacion` | `observado` | *"Falta la carta de solicitud firmada"* | 15 | 2026-10-29 11:40:00 |
| 2 | 142 | `viceministro` | `espera_correccion` | NULL | 15 | 2026-10-29 11:40:00 |
| 3 | 142 | `dgea` | `pendiente` | NULL | NULL | NULL |
| 4 | 142 | `revision_articulos` | `pendiente` | NULL | NULL | NULL |
| 5 | 142 | `suministro` | `pendiente` | NULL | NULL | NULL |
| 6 | 142 | `despacho` | `pendiente` | NULL | NULL | NULL |
| 7 | 142 | `entrega` | `pendiente` | NULL | NULL | NULL |

---

## 3. Estados posibles de cada nivel

| Estado | Significado |
|---|---|
| `pendiente` | No ha decidido todavía. Con la secuencia estricta solo el **primer** nivel `pendiente` de la cadena tiene el turno. |
| `aprobado` | El nivel aprobó (con quién/cuándo en `por`/`fecha`). |
| `observado` | Le devolvieron; **debe corregir**. El motivo está en `observacion`. |
| `espera_correccion` | Devolvió al anterior y **espera** que corrija su documento. |

> No existe estado "bloqueado": un nivel fuera de turno simplemente no es el
> primero no aprobado. Lo que restringe quién decide es el turno estricto +
> rol + alcance + etapa (regla 4).

---

## 4. Cómo trabaja el servidor automáticamente

Antes de aplicar cualquier regla, el servidor resuelve la cadena de la solicitud
con `resolver_cadena(id_modalidad)` (§2.1). Todo lo que sigue se lee sobre
**esa cadena**, no sobre la constante de 7 niveles:

```python
NIVELES_APROB = ["validacion", "viceministro", "dgea", "revision_articulos",
                 "suministro", "despacho", "entrega"]          # orden semántico
cadena        = resolver_cadena(id_modalidad)                   # subconjunto ordenado
```

"El nivel anterior" significa **el anterior dentro de `cadena`**.

### Regla 1 — `aprobar(nivel)`

1. Verifica que la solicitud existe (si no → **404**).
2. Verifica que la modalidad no sea Ayuda Humanitaria (si lo es → **409**).
3. Materializa la cadena si faltan filas (`asegurar_aprobaciones`).
4. Verifica rol y alcance del token para ese nivel (→ **403**).
5. Verifica que `nivel` pertenezca a la cadena de su modalidad (→ **400**).
6. **Turno (secuencia estricta):** `nivel` debe ser el **primer nivel no
   aprobado** (si no → **409**; con la cadena completa también → **409**).
7. Verifica que la solicitud esté en la **etapa que exige el nivel** (§1; si no
   → **409**).
8. **Gate de negocio del nivel:**
   - `validacion`: el **checklist de instancia 1** debe estar completo (todos
     los requisitos `es_documento = TRUE` de `instancia = 1` con documento
     válido) → si no, **409**. Además el **Informe de validación** (PDF) es
     **obligatorio** en el mismo `PUT` (campo multipart `archivo`) → si no,
     **409**. El archivo se registra contra el requisito cuyo `nombre_paso`
     empieza con "Informe de validación" (`instancia = 2`) de la modalidad.
   - `revision_articulos`: si `rida.cat_modalidad.tiene_motor_calculo = TRUE`,
     exige al menos una ejecución `modo = 'operativo'` en
     `rida.ejecucion_calculo` → si no, **409**. Si es `FALSE`, el visado es
     manual.
   - Otros niveles: sin gates adicionales (el `archivo` es opcional y, si se
     envía, se registra igual contra el requisito de informe).
9. Marca el nivel como `aprobado`, limpia `observacion`, guarda `por` y `fecha`.
10. **Autocorrección del flujo:** si este nivel venía de `observado`, el nivel
    **siguiente que lo había devuelto** pasa de `espera_correccion` →
    `pendiente`.
11. **Trigger de etapa:** si la etapa resultante difiere de la actual, la
    solicitud avanza en el mismo `PUT`, con su paso de bitácora. Aprobar
    `entrega` deja la solicitud en `ENTREGADA` y, en la misma transacción, la
    pasa a **`CERRADA`** con un segundo paso de bitácora (`CERRAR`).

### Regla 2 — `devolver(nivel)`

1. No se puede devolver desde el **primer nivel de la cadena** → **400**.
2. Verifica que la modalidad no sea Ayuda Humanitaria (**409**) y que la etapa
   esté dentro de la vida del motor (`ENVIADA`..`ENTREGADA`; si no → **409**).
3. Verifica que `nivel` pertenezca a la cadena y que su **anterior** esté
   `aprobado` (si no → **400**).
4. **Turno estricto:** solo puede devolver quien tiene el turno (si no → **409**).
5. `observacion` es **obligatoria** (vacía o < 10 caracteres → **422**).
6. El **nivel anterior** pasa a `observado` (con el motivo en su fila).
7. El **nivel actual** pasa a `espera_correccion`.
8. **Reversa de etapa:** la solicitud vuelve a la etapa que exige el nivel
   observado (`ETAPA_EXIGIDA_POR_NIVEL[anterior]`).

### Regla 3 — `estado_global` (derivado, sin tabla)

```
1. El primer nivel NO-aprobado → badge de ese nivel (§1)
2. Toda la cadena aprobada     → ENTREGADO
3. Sin cadena (Ayuda Humanitaria) → null
```

Valores posibles: `EN_VALIDACION`, `VICEMINISTRO`, `DGEA`,
`REVISION_ARTICULOS`, `SUMINISTRO`, `DESPACHO`, `EN_ENTREGA` y `ENTREGADO`
(cadena completa). Un nivel `observado` muestra el badge de su posición mientras
no se re-apruebe.

> **`estado_global` es un resumen, no un turno.** El frontend debe usar
> `puede_aprobar` de `GET …/aprobacion`, que ya combina turno + etapa + rol +
> alcance (§8).

### Regla 4 — autorización (rol + alcance + etapa)

| Nivel | Roles que pueden visarlo | Alcance exigido | Etapa exigida |
|---|---|---|---|
| `validacion` | 9 (VIDECI Departamental) | mismo `id_departamento` | `ENVIADA` |
| `viceministro` | 15 (Viceministro) | nacional | `EN_APROBACION` |
| `dgea` | 16 (DGEA) | nacional | `EN_APROBACION` |
| `revision_articulos` | 15 (Viceministro) | nacional | `EN_APROBACION` |
| `suministro` | 17 (Gestión de Suministro) | nacional | `APROBADA` |
| `despacho` | 9 (VIDECI Departamental) | mismo `id_departamento` | `AUTORIZADA` |
| `entrega` | 6 (UGR Municipio) | mismo `id_municipio` | `DESPACHADA` |

> **Cambio de permisos (v2.60.0).** Los roles **3 (VIDECI Regional)**, **4 (UGR
> Sectores)**, **5 (DGR Gobernación)**, **8 (Alcalde)** y **14 (Almacén)** quedan
> **sin niveles**. Entran los roles **15, 16 y 17** con permisos RIDA
> CREATE/READ/UPDATE. Los roles 1 y 2 conservan el bypass total.
>
> **Límite conocido:** `validar_scope_solicitud` sólo acota geográficamente a los
> roles 5, 8 y 9; en esta máquina el alcance por nivel sí se aplica
> (`validacion`/`despacho` → departamento, `entrega` → municipio).

---

## 5. Flujo de ejemplo

### Cadena completa de 7 niveles

| Paso | Acción | Resultado en BD |
|---|---|---|
| 0 | `POST /rida/solicitudes` (rol 6) | 7 filas `pendiente`, etapa `ENVIADA`, global `EN_VALIDACION` |
| 1 | subir los 2 documentos de instancia 1 (rol 6) | checklist completo |
| 2 | `PUT validacion` multipart con `archivo` (rol 9) | `validacion=aprobado`, **etapa `EN_APROBACION`**, global `VICEMINISTRO` |
| 3 | `PUT viceministro` (rol 15) | global `DGEA` |
| 4 | `PUT dgea` (rol 16) | global `REVISION_ARTICULOS` |
| 5 | `PUT revision_articulos` (rol 15; con cálculo operativo si la modalidad tiene motor) | **etapa `APROBADA`**, global `SUMINISTRO` |
| 6 | `PUT suministro` (rol 17) | **etapa `AUTORIZADA`**, global `DESPACHO` |
| 7 | `PUT despacho` (rol 9 de su depto.) | **etapa `DESPACHADA`**, global `EN_ENTREGA` |
| 8 | `PUT entrega` (rol 6) | **etapa `ENTREGADA` → `CERRADA`**, global `ENTREGADO` |

Los intentos fuera de turno devuelven **409**. `POST /{id}/rechazar` funciona
desde `ENVIADA` o `EN_APROBACION` (→ `RECHAZADA`) y congela las filas.

### Ejemplo con devolución

| Paso | Acción | Resultado en BD |
|---|---|---|
| 0 | tras aprobar `validacion` y `viceministro` | etapa `EN_APROBACION`, global `DGEA` |
| 1 | `PUT dgea {"aprobado":false,"observacion":"Falta revisar el artículo 12"}` (rol 16) | `viceministro=observado`, `dgea=espera_correccion`, global `VICEMINISTRO` |
| 2 | `PUT viceministro {"aprobado":true}` (rol 15) | `viceministro=aprobado`, `dgea=pendiente`, global `DGEA` |
| 3 | `PUT dgea {"aprobado":true}` | sigue el flujo |

La **reversa de etapa** aplica cuando se devuelve un nivel con trigger: con la
solicitud en `APROBADA`, `PUT suministro {"aprobado":false,…}` observa a
`revision_articulos` y retrocede a `EN_APROBACION`.

### Cadena configurada de 5 niveles

Modalidad 4 con `[validacion, revision_articulos, suministro, despacho,
entrega]`: el `PUT …/aprobacion/viceministro` responde **400** (nivel fuera de
su cadena). Una cadena sin `suministro` se rechaza con **400** en
`PUT cat-cadena-aprobacion` (no habría forma de llegar a `AUTORIZADA`).

---

## 6. API (v2)

Prefijo real: `https://api.climbat.net/api/v2/rida/solicitudes`.

### `GET /{id_solicitud}/aprobacion`

Devuelve SOLO la máquina de aprobaciones. Incluye la **cadena resuelta**, para
que el detalle sea auto-suficiente.

```json
{
  "success": true,
  "message": "Aprobaciones de la solicitud obtenidas correctamente",
  "data": {
    "id_solicitud": 142,
    "id_modalidad": 3,
    "etapa": "EN_APROBACION",
    "cadena": ["validacion", "viceministro", "dgea", "revision_articulos",
               "suministro", "despacho", "entrega"],
    "estado_global": "DGEA",
    "mi_nivel": "viceministro",
    "aprobaciones": {
      "validacion": { "nivel": "validacion", "orden": 1, "estado": "aprobado",
                      "observacion": null, "por": 9, "fecha": "2026-10-29T13:15:00",
                      "roles": [9], "alcance": "departamento",
                      "puede_aprobar": false, "puede_devolver": false, "es_mio": false },
      "viceministro": { "nivel": "viceministro", "orden": 2, "estado": "pendiente",
                        "observacion": null, "por": null, "fecha": null,
                        "roles": [15], "alcance": "nacional",
                        "puede_aprobar": false, "puede_devolver": false, "es_mio": false }
    }
  },
  "total": null
}
```

`aprobaciones` contiene **solo los niveles de `cadena`**. Para Ayuda
Humanitaria: `cadena: []`, `estado_global: null`, `aprobaciones: {}`.

### `GET /cat-cadena-aprobacion`

```json
{
  "success": true,
  "data": {
    "niveles": [
      { "codigo": "validacion",        "label": "Validación VIDECI Departamental",
        "roles": [9],  "alcance": "departamento", "orden": 1,
        "nom_roles": ["VIDECI Departamental"] },
      { "codigo": "viceministro",      "label": "Viceministro",
        "roles": [15], "alcance": "nacional", "orden": 2, "nom_roles": ["Viceministro"] },
      { "codigo": "dgea",              "label": "Dirección General de Emergencia y Auxilio",
        "roles": [16], "alcance": "nacional", "orden": 3, "nom_roles": ["DGEA"] },
      { "codigo": "revision_articulos","label": "Revisión de artículos",
        "roles": [15], "alcance": "nacional", "orden": 4, "nom_roles": ["Viceministro"] },
      { "codigo": "suministro",        "label": "Gestión de suministro",
        "roles": [17], "alcance": "nacional", "orden": 5,
        "nom_roles": ["Gestion de Suministro"] },
      { "codigo": "despacho",          "label": "Despacho",
        "roles": [9],  "alcance": "departamento", "orden": 6,
        "nom_roles": ["VIDECI Departamental"] },
      { "codigo": "entrega",           "label": "Entrega",
        "roles": [6],  "alcance": "municipio", "orden": 7, "nom_roles": ["UGR Municipio"] }
    ],
    "default": ["validacion", "viceministro", "dgea", "revision_articulos",
                "suministro", "despacho", "entrega"],
    "por_modalidad": { "4": ["validacion", "revision_articulos", "suministro",
                             "despacho", "entrega"] }
  }
}
```

- `niveles`: catálogo semilla (label, roles y alcance **vienen del backend**).
  `nom_roles` trae los nombres de `usuarios.rol` resueltos.
- `default`: cadena usada cuando la modalidad no tiene entrada en
  `por_modalidad`.
- `por_modalidad`: solo las modalidades con cadena **distinta** del default.

### `PUT /{id_solicitud}/aprobacion/{nivel}` — **multipart/form-data**

`nivel` = uno de los 7 códigos. Si no pertenece a la cadena de la solicitud →
**400**.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `aprobado` | bool | sí (o legado `aprobar`) | `true` aprueba, `false` devuelve. |
| `observacion` | texto | al devolver (≥10) | Motivo de la devolución. |
| `archivo` | PDF | **sí en `validacion`** | Informe de validación. Opcional en otros niveles. |
| `nombre_documento` | texto | no | Nombre visible del documento. |
| `fecha_documento` | `YYYY-MM-DD` | no | Fecha del documento (default: hoy). |

```bash
# Aprobar validacion adjuntando el informe
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -F "aprobado=true" \
  -F "archivo=@informe.pdf;type=application/pdf" \
  -F "nombre_documento=Informe de validación" \
  -F "fecha_documento=2026-10-29" \
  .../solicitudes/142/aprobacion/validacion

# Devolver
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -F "aprobado=false" \
  -F "observacion=Falta revisar el artículo 12 del cálculo" \
  .../solicitudes/142/aprobacion/dgea
```

El cuerpo legado (`aprobar` + `observaciones`) se sigue aceptando; el canónico
gana si llegan ambos. La respuesta reutiliza el `data` del GET.

| Código | ¿Cuándo? |
|---|---|
| **400** | `nivel` inválido o fuera de la cadena; devolver desde el primer nivel; devolver cuando el anterior no está `aprobado`; `fecha_documento` mal formada. |
| **401** | Sin token (auth `Bearer`). |
| **403** | Rol sin permiso para ese nivel, o alcance (municipio/departamento) fuera del usuario. |
| **404** | `id_solicitud` no existe. |
| **409** | Etapa incorrecta; fuera de turno o cadena completa; modalidad Ayuda Humanitaria; checklist de instancia 1 incompleto; informe de validación ausente; cálculo operativo ausente en `revision_articulos` cuando la modalidad tiene motor. |
| **422** | `aprobado`/`aprobar` ausente; `observado:false` con observación vacía o < 10 caracteres. |

> **Rompe compatibilidad:** el `PUT` pasó de JSON a **multipart/form-data** y el
> `archivo` es obligatorio en `validacion`.

### Endpoints de etapa (v2.60.0)

| Endpoint | Efecto |
|---|---|
| `POST /{id}/rechazar` | `ENVIADA`/`EN_APROBACION` → `RECHAZADA`; congela las filas. |
| `POST /{id}/enviar`, `/revisar`, `/observar`, `/corregir`, `/validar`, `/iniciar-aprobacion`, `/autorizar`, `/cerrar` | **ELIMINADOS (404).** El motor arranca al crear; `autorizar`/`cerrar` son reemplazados por los niveles `suministro`/`entrega` + cierre automático. |
| `PUT /{id}` (actualizar) | Solo en `ENVIADA`. |
| `DELETE /{id}` | Solo en `ENVIADA` y sin niveles aprobados. |
| `POST /{id}/documentos` | Solo en `ENVIADA`. |

### `GET /{id}/bitacora` — auditoría, no es la máquina

Devuelve el historial de pasos (`pasoOrden`, `pasoNombre`, `accion`,
`estadoResultante`, `observaciones`, `fecha`). Es **complementaria**: la fuente
de verdad de los estados es `rida.aprobaciones_solicitud`.

---

## 7. Migraciones

SQL plano idempotente bajo `database/migrations/`, aplicado a mano con
`psql -f` (ver `README.md`).

| Fase | Migración | Estado |
|---|---|---|
| 1 | `v2.36.0_aprobaciones_rida.sql` | **Aplicada** 2026-10-06. Crea `rida.aprobacion_cadena`, `rida.aprobaciones_solicitud` y hace el backfill. |
| 2 | `v2.45.0_drop_aprob_solicitud.sql` | **Aplicada** 2026-10-08. Retira las 15 columnas `aprob_*` y sus 5 FKs de `rida.solicitud`. |
| 3 | `v2.59.0_cadena_visaciones_nueva.sql` | **Aplicada** 2026-10-19. Cadena de 5 niveles. |
| 4 | `v2.60.0_motor_siete_niveles.sql` | **Aplicada** 2026-10-29 (2×). Roles 15/16/17 + permisos RIDA; columna `tiene_motor_calculo`; requisitos de informe para modalidades 2 y 3; cadena default de 7 niveles; CHECKs de `nivel`/`orden`; etapas `BORRADOR`/`EN_REVISION`/`OBSERVADA`/`VALIDADA` inactivas; remapeo de solicitudes existentes a `ENVIADA`. |

### Red de seguridad en vez de trigger

**RIDA no lleva trigger a propósito:** las filas se crean al crear la solicitud
(`crear_solicitud` → `asegurar_aprobaciones`) y, si faltan (restauración de
backup o cadena configurada después), se rellenan con `ON CONFLICT DO NOTHING`
en cada lectura de la máquina y antes de cada visado. Un `GET` de una solicitud
`RECHAZADA`/`CERRADA` **no** materializa filas.

---

## 8. Notas para el frontend

- **No calcular nada cuando exista el GET.** Usar `estado_global` como badge de
  resumen y `puede_aprobar`/`puede_devolver` del nivel.
- **La cadena no es una constante del frontend.** `cat-cadena-aprobacion`
  cacheado es la semilla; `data.cadena` del GET es la cadena real de la
  solicitud.
- **v2.60.0 — rompe compatibilidad:**
  - Códigos de nivel: `enviado/validacion/aprobado/despacho/entregado` →
    `validacion/viceministro/dgea/revision_articulos/suministro/despacho/entrega`.
  - Badges: `ENVIADO`/`APROBADO_EN_ATENCION` desaparecen; aparecen
    `VICEMINISTRO`, `DGEA`, `REVISION_ARTICULOS`, `SUMINISTRO`, `EN_ENTREGA`.
  - El `PUT` de aprobación es **multipart** y el informe es obligatorio en
    `validacion`.
  - Desaparecen los endpoints de etapa `enviar/revisar/observar/corregir/
    validar/iniciar-aprobacion/autorizar/cerrar`.
  - La solicitud nace en `ENVIADA`; no hay `BORRADOR`.
- **`observaciones` (cabecera) ≠ `observacion` (por nivel).**

---

## 9. Efectos visibles de v2.60.0

- **Roles.** Salen de la cadena los roles 3, 4, 5, 8 y 14. Entran 15
  (Viceministro: `viceministro` y `revision_articulos`), 16 (DGEA) y 17
  (Suministro). `validacion` y `despacho` quedan en el rol 9; `entrega` en el 6.
- **Nuevas dependencias de datos.** Requisito "Informe de validación
  departamental" en modalidades 2 y 3 (tipo de documento 24). Las modalidades 2
  y 3 no tenían documentos de instancia 1 cargables en todos los casos: el gate
  de checklist puede impedir avanzar hasta completar el catálogo de requisitos
  (`es_documento = TRUE`).
- **El cierre es automático** al aprobar `entrega`; ya no existe
  `POST /cerrar`.
- **Ayuda Humanitaria**: su motor se inicia desde `ENVIADA` y exige checklist de
  instancia 1; sus 7 niveles y tablas no cambian.
