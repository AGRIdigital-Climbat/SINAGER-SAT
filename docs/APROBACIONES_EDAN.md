# SINAGERSAT — Máquina de Aprobaciones EDAN (v2.17)

Documento de referencia de la **máquina de estados de aprobaciones** del EDAN:
qué campos tiene la tabla, qué significa cada estado, y cómo el servidor la
actualiza **automáticamente** sin que el frontend tenga que calcular nada.

> **Cambio de paradigma (v2.17.1):** antes había 4 booleanos en `edan.edan`
> (`aprob_ugr/aprob_alcalde/aprob_dgr/aprob_videcid`). Ahora existe una tabla
> separada `edan.aprobaciones_edan` (1 fila por nivel) que es la **fuente única
> de verdad** de las aprobaciones. Los booleanos fueron eliminados.

> **v2.17.4 — el GET pasó a ser informativo.** Antes el campo `por` mezclaba dos
> cosas: se escribía tanto al aprobar como al devolver, así que el mismo número
> significaba "quién aprobó" o "quién devolvió" según el estado, y al devolver se
> sobrescribía el aprobador original (que quedaba perdido para siempre). Ahora
> hay columnas separadas para cada cosa y el GET responde las dos preguntas:
> **quién aprobó y cuándo**, y **quién devolvió y cuándo**. Ver §2.

> **v2.17.5 — el motor maneja `edan.estado_edan`.** Agrega el estado 4
> **"Observado"** (faltaba para representar un EDAN devuelto) y hace que
> aprobar/devolver dejen `edan.edan.id_estado` alineado con la cadena. A partir de
> acá **nadie fija el estado a mano**: se quitó el endpoint de cambio de estado en
> V1 y V2, y el `PUT /edan/{id}` normal ya no lo acepta. Ver §9.

---

## 1. Concepto general

La aprobación de un EDAN es una **cadena estricta de 4 niveles**, en este orden:

```
ugr → alcalde → dgr → videcid
1      2         3      4
```

Cada eslabón de la cadena es una fila en `edan.aprobaciones_edan`. El servidor
aplica las reglas (quién puede aprobar/devolver, qué estado sigue, cuál es el
estado global) **automáticamente** en cada `PUT`; el frontend solo envía
"apruebo" (`aprobado:true`) o "devuelvo" (`aprobado:false` + motivo).

`edan.estado_edan` (ciclo de vida del formulario) lo escribe **el propio motor**
al aprobar o devolver — ver §9. Lo que sigue sin automatizarse es la suma de
población y familias afectadas al aprobar.

---

## 2. Tabla `edan.aprobaciones_edan`

```sql
CREATE TABLE edan.aprobaciones_edan (
    id_aprobacion BIGSERIAL PRIMARY KEY,
    id_edan       BIGINT      NOT NULL REFERENCES edan.edan (id_edan) ON DELETE CASCADE,
    nivel         VARCHAR(20) NOT NULL CHECK (nivel IN ('ugr','alcalde','dgr','videcid')),
    estado        VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente','aprobado','observado','espera_correccion')),
    observacion   TEXT,

    -- v2.17.4
    id_usuario_aprobacion INTEGER REFERENCES usuarios.usuario (id_usuario),
    fecha_aprobacion      TIMESTAMP,
    id_usuario_devolucion INTEGER REFERENCES usuarios.usuario (id_usuario),
    fecha_devolucion      TIMESTAMP,
    -- renombradas desde por/fecha (v2.17.4). Auditoría; la API NO las expone.
    id_usuario_ultima_accion INTEGER REFERENCES usuarios.usuario (id_usuario),
    fecha_ultima_accion      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (id_edan, nivel)
);
```

| Campo | Tipo | ¿Cómo se llena? | Descripción |
|---|---|---|---|
| `id_aprobacion` | `BIGSERIAL` | Automático | ID del registro (1 por nivel por EDAN). |
| `id_edan` | `BIGINT` FK | Automático | EDAN al que pertenece la cadena. `ON DELETE CASCADE`: si se borra el EDAN se borran sus 4 aprobaciones. |
| `nivel` | `VARCHAR(20)` | Automático (backfill) | El eslabón: `ugr`, `alcalde`, `dgr` o `videcid`. Es el **identificador** que ve la API. |
| `estado` | `VARCHAR(20)` | **Solo el servidor** | Uno de los 4 estados (ver §3). |
| `observacion` | `TEXT` | Servidor al **devolver** | Motivo de la devolución. **Solo vive en la fila del nivel `observado`** (quien debe corregir lo lee). Se limpia cuando ese nivel vuelve a aprobar. |
| `id_usuario_aprobacion` | `INTEGER` FK usuario | Servidor (del token JWT) | **Quién aprobó este nivel.** Se escribe al aprobar y **se conserva aunque el nivel luego sea devuelto**, para no perder la identidad del aprobador. |
| `fecha_aprobacion` | `TIMESTAMP` | Servidor | **Cuándo se aprobó** ese nivel. |
| `id_usuario_devolucion` | `INTEGER` FK usuario | Servidor (del token JWT) | **Quién devolvió este nivel.** Se escribe en las **dos** filas del ciclo: la devuelta (`observado`) y la que devuelve (`espera_correccion`). Se limpia al aprobar de nuevo o al resolverse la corrección. |
| `fecha_devolucion` | `TIMESTAMP` | Servidor | **Cuándo se devolvió.** |
| `id_usuario_ultima_accion` | `INTEGER` FK usuario | Servidor | *(era `por`)* Último usuario que actuó, apruebe o devuelva. **Auditoría; la API no lo expone** porque es derivable del estado. |
| `fecha_ultima_accion` | `TIMESTAMP` | Automático / Servidor | *(era `fecha`)* Fecha de la última acción. **Auditoría; la API no la expone.** |

> **Por qué las columnas de auditoría no se exponen:** `id_usuario_ultima_accion`
> siempre coincide con el `id_usuario_aprobacion` o el `id_usuario_devolucion`
> según el estado del nivel, así que es dato redundante. Además, la API no expone
> ningún `id_usuario` sin su objeto de usuario anidado (ver §6), y no vale la pena
> duplicar ese bloque de 9 campos para un dato que el frontend no necesita.

> La columna `ordinal` (1–4) existió en v2.17.1 y fue **eliminada en v2.17.2**:
> el orden de la cadena lo define el código (constante `NIVELES_APROBACION`), no
> la BD. Nunca se expuso por la API.

### Ejemplo de filas (DGR devolvió a Alcalde)

Estado real de un EDAN con el DGR devolviendo el croquis del alcalde:

| `nivel` | `estado` | `observacion` | `id_usuario_aprobacion` | `fecha_aprobacion` | `id_usuario_devolucion` | `fecha_devolucion` |
|---|---|---|---|---|---|---|
| `ugr` | `aprobado` | NULL | 28 | 23:09 15:44:33 | NULL | NULL |
| `alcalde` | `observado` | *"El croquis está desactualizado, corrijan"* | **26** | 23:09 16:02:10 | **31** | 23:09 17:20:45 |
| `dgr` | `espera_correccion` | NULL | 31 | 23:09 17:20:45 | **31** | 23:09 17:20:45 |
| `videcid` | `pendiente` | NULL | NULL | NULL | NULL | NULL |

Lo importante de esta tabla: la fila `alcalde` dice **quién aprobó (26), quién lo
devolvió (31), y las dos fechas**, y la fila `dgr` dice que fue el propio DGR
(31) quien hizo la devolución. Antes de v2.17.4 esto era imposible de expresar:
solo existía un `por` que se pisaba.

---

## 3. Estados posibles de cada nivel

| Estado | Significado |
|---|---|
| `pendiente` | Aún no le toca decidir, o le toca y no ha decidido. |
| `aprobado` | El nivel aprobó. Quién y cuándo en `id_usuario_aprobacion` / `fecha_aprobacion`. |
| `observado` | Le devolvieron; **debe corregir**. El motivo está en `observacion`, y quién devolvió en `id_usuario_devolucion` / `fecha_devolucion`. |
| `espera_correccion` | Devolvió al anterior y **espera** que corrija su documento. También registra su propia devolución. |

---

## 4. Cómo trabaja el servidor automáticamente

El código vive en `api/edan/service.py`; la cadena fija es:

```python
NIVELES_APROBACION = ["ugr", "alcalde", "dgr", "videcid"]
ROL_APROBADOR = {"ugr": 6, "alcalde": 8, "dgr": 5, "videcid": 9}
```

> `ROL_APROBADOR` es **informativo**: la API lo publica en el GET para que el
> frontend sepa a quién le toca cada nivel, pero **el servidor NO restringe por
> rol** — cualquier usuario autenticado puede aprobar cualquier nivel (lo único
> que se valida es el territorio para los roles 5/8/9). Es una decisión
> consciente: en una comunidad el UGR o el alcalde pueden cambiar y no hay un
> "dueño" estable del nivel, así que **no** se lee `edan.edan.id_usuario_ugr` /
> `id_usuario_alcalde` para decidir. Ver §8.

Cada `PUT .../aprobacion/{nivel}` ejecuta una de estas dos reglas:

### Regla 1 — `aprobar(nivel)`  (`aprobado: true`)
1. Verifica que el EDAN existe (si no → 404).
2. Verifica que el **nivel anterior** esté `aprobado` (si no → **400**;
   `ugr` no tiene anterior, puede aprobar siempre).
3. Marca el nivel como `aprobado`, **guarda `id_usuario_aprobacion` y
   `fecha_aprobacion`**, y limpia `observacion`, `id_usuario_devolucion` y
   `fecha_devolucion` (si el nivel venía devuelto, el ciclo ya se resolvió y el
   GET debe reflejar el estado actual, no el pasado).
4. **Autocorrección del flujo:** si este nivel venía de `observado` (había sido
   devuelto), el nivel **siguiente que lo había devuelto** pasa de
   `espera_correccion` → `pendiente` (ya puede volver a decidir) y también se le
   limpia su `id_usuario_devolucion`.

### Regla 2 — `devolver(nivel)`  (`aprobado: false`)
1. No se puede devolver desde `ugr` (no hay nivel anterior) → **400**.
2. Verifica que el **nivel anterior** esté `aprobado` (if no → **400**).
3. `observacion` es **obligatoria** (si viene vacía → **422**).
4. El **nivel anterior** pasa a `observado` con el motivo, y se le escribe
   `id_usuario_devolucion` / `fecha_devolucion`. Su `id_usuario_aprobacion`
   **no se toca**: sigue siendo el del nivel anterior, que es justo el dato que
   ahora se quiere conservar.
5. El **nivel actual** pasa a `espera_correccion` y **también** registra la
   devolución (`id_usuario_devolucion` / `fecha_devolucion`), para que su fila
   diga "yo devolví esto y en este momento".

### Regla 3 — `estado_global` (derivado, SIN tabla)
El servidor lo calcula en cada lectura y **no se almacena**:

```
1. Si algún nivel está 'observado'  → observado_{nivel}   (primer observado de la cadena)
2. Si no, el primer nivel NO-aprobado → {estado}_{nivel}   (p. ej. pendiente_dgr)
3. Los 4 aprobados                  → aprobado
```

Ejemplos: `pendiente_ugr`, `pendiente_dgr`, `observado_alcalde`, `aprobado`.

> El turno visible para el usuario está en el `estado_global`: si el frontend
> lee `pendiente_dgr`, quiere decir que "le toca al DGR".

---

## 5. Flujo de ejemplo (el caso típico: DGR devuelve)

| Paso | Acción | Resultado en BD |
|---|---|---|
| 1 | Estado inicial (backfill) | todos `pendiente`, global `pendiente_ugr` |
| 2 | `PUT ugr {"aprobado":true}` | `ugr=aprobado` (aprobador=28), global `pendiente_alcalde` |
| 3 | `PUT alcalde {"aprobado":true}` | `alcalde=aprobado` (aprobador=26), global `pendiente_dgr` |
| 4 | `PUT dgr {"aprobado":false,"observacion":"Falta el plano"}` | `alcalde=observado` (+motivo, +devuelto por 31, **aprobador 26 intacto**), `dgr=espera_correccion` (+devuelto por 31), global `observado_alcalde` |
| 5 | `PUT alcalde {"aprobado":true}` (corrige y vuelve a aprobar) | `alcalde=aprobado`, **devolución limpiada**, `dgr=pendiente` (vuelve a decidir, devolución limpiada), global `pendiente_dgr` |
| 6 | `PUT dgr {"aprobado":true}` | `dgr=aprobado`, global `pendiente_videcid` |
| 7 | `PUT videcid {"aprobado":true}` | `videcid=aprobado`, global `aprobado` |

---

## 6. API (solo V2)

### `GET /api/v2/edan/{id_edan}/aprobacion`

Devuelve SOLO la máquina de aprobaciones (sin cabecera completa ni localidades).
**Abierta a cualquier rol autenticado** (no requiere permiso de edición EDAN);
solo se valida territorio para roles 5/8/9 (depto/municipio).

Es una **vista informativa del estado actual**: por cada nivel dice en qué estado
está, quién lo aprobó y cuándo, y quién lo devolvió y cuándo. Los usuarios van
**embebidos** (no solo el id) para que el frontend no necesite llamadas extra.

Cada nivel trae estos campos:

| Campo | Qué es |
|---|---|
| `nivel` | `ugr` \| `alcalde` \| `dgr` \| `videcid` |
| `estado` | `pendiente` \| `aprobado` \| `observado` \| `espera_correccion` |
| `observacion` | Motivo del rechazo; `null` si no hay. |
| `rol_aprobador` | `{id_rol, nombre, descripcion}` del rol que corresponde a ese nivel. **Informativo** (§4). |
| `id_usuario_aprobacion` / `usuario_aprobacion` / `fecha_aprobacion` | Quién aprobó y cuándo. `null` si nunca se aprobó. |
| `id_usuario_devolucion` / `usuario_devolucion` / `fecha_devolucion` | Quién devolvió y cuándo. `null` si no está devuelto. |

`usuario_aprobacion` y `usuario_devolucion` son el objeto completo del usuario
(9 campos: `id_usuario`, `usuario`, `nombre`, `carnet`, `celular`, `correo`,
`cargo`, `id_rol`, `activo`) o `null`.

Ejemplo real (EDAN 79, el DGR devolvió el croquis del alcalde):

```json
{
  "success": true,
  "message": "Aprobaciones del EDAN obtenidas correctamente",
  "data": {
    "id_edan": 79,
    "estado_global": "observado_alcalde",
    "aprobaciones": {
      "ugr": {
        "estado": "aprobado",
        "observacion": null,
        "rol_aprobador": { "id_rol": 6, "nombre": "UGR Municipio", "descripcion": "Carga y edita formularios propios" },
        "id_usuario_aprobacion": 28,
        "usuario_aprobacion": {
          "id_usuario": 28, "usuario": "UGRSCZ", "nombre": "Andres Calamardo",
          "carnet": "12345678", "celular": "67023648", "correo": null,
          "cargo": "UGR", "id_rol": 6, "activo": true
        },
        "fecha_aprobacion": "2026-09-23T15:44:33.410555",
        "id_usuario_devolucion": null,
        "usuario_devolucion": null,
        "fecha_devolucion": null
      },
      "alcalde": {
        "estado": "observado",
        "observacion": "El croquis esta desactualizado, corrijan",
        "rol_aprobador": { "id_rol": 8, "nombre": "Alcalde", "descripcion": "Revisa formularios EDAN" },
        "id_usuario_aprobacion": 26,
        "usuario_aprobacion": {
          "id_usuario": 26, "usuario": "AlcaldeSCZ", "nombre": "Mamen Saavedra",
          "carnet": "7894561", "celular": "78851166", "correo": null,
          "cargo": null, "id_rol": 8, "activo": true
        },
        "fecha_aprobacion": "2026-09-23T16:02:10",
        "id_usuario_devolucion": 31,
        "usuario_devolucion": {
          "id_usuario": 31, "usuario": "DGRLP", "nombre": "Mario Vargas",
          "carnet": "5566778", "celular": "70112233", "correo": "dgr@lp.gob.bo",
          "cargo": "Director", "id_rol": 5, "activo": true
        },
        "fecha_devolucion": "2026-09-23T17:20:45"
      },
      "dgr": {
        "estado": "espera_correccion",
        "observacion": null,
        "rol_aprobador": { "id_rol": 5, "nombre": "DGR Gobernación", "descripcion": "Carga y edita formularios propios" },
        "id_usuario_aprobacion": 31,
        "usuario_aprobacion": {
          "id_usuario": 31, "usuario": "DGRLP", "nombre": "Mario Vargas",
          "carnet": "5566778", "celular": "70112233", "correo": "dgr@lp.gob.bo",
          "cargo": "Director", "id_rol": 5, "activo": true
        },
        "fecha_aprobacion": "2026-09-23T17:20:45",
        "id_usuario_devolucion": 31,
        "usuario_devolucion": {
          "id_usuario": 31, "usuario": "DGRLP", "nombre": "Mario Vargas",
          "carnet": "5566778", "celular": "70112233", "correo": "dgr@lp.gob.bo",
          "cargo": "Director", "id_rol": 5, "activo": true
        },
        "fecha_devolucion": "2026-09-23T17:20:45"
      },
      "videcid": {
        "estado": "pendiente",
        "observacion": null,
        "rol_aprobador": { "id_rol": 9, "nombre": "VIDECI Departamental", "descripcion": "Gestiona usuario a nivel departamental y visualiza datos del departamento asignado" },
        "id_usuario_aprobacion": null,
        "usuario_aprobacion": null,
        "fecha_aprobacion": null,
        "id_usuario_devolucion": null,
        "usuario_devolucion": null,
        "fecha_devolucion": null
      }
    }
  },
  "total": null
}
```

> Los usuarios 28, 26 y el EDAN 79 son reales. **El usuario 31 / DGRLP es
> ilustrativo**: al momento de escribir esto no hay usuarios con rol 5 (DGR) ni
> rol 9 (VIDECI) cargados en `usuarios.usuario`. Los 4 objetos `rol_aprobador`
> sí salen de `usuarios.rol`.

Con este ejemplo, el frontend puede pintar "lo aprobó Mamen Saavedra el 23/09 a
las 16:02, se lo devolvió Mario Vargas a las 17:20 porque *el croquis está
desactualizado*" sin calcular nada y sin llamadas extra.

> **No existe histórico.** El GET muestra el **estado actual**: cuando un nivel
> se corrige y vuelve a aprobarse, su `usuario_devolucion` se limpia. Si el
> frontend necesita la bitácora de rechazos, eso no existe todavía (ver §8).

### `PUT /api/v2/edan/{id_edan}/aprobacion/{nivel}`  (`nivel` = `ugr` | `alcalde` | `dgr` | `videcid`)

Body (schema `AprobacionEdan`):

```json
// APROBAR
{ "aprobado": true }

// DEVOLVER (observacion obligatoria)
{ "aprobado": false, "observacion": "El croquis está desactualizado, corrijan" }
```

La respuesta reutiliza el `data` del GET (máquina completa + `estado_global`),
con los usuarios ya resueltos, así que el frontend no tiene que hacer una segunda
consulta para pintar "quién aprobó".

El usuario que aprueba o devuelve **se toma del token JWT**, no del cuerpo: el
body solo dice *qué* hacer (`aprobado` + `observacion`), nunca *quién`. Por eso
`aprobado: true` y `aprobado: false` con el mismo body acting token producen
resultados distintos en `usuario_aprobacion` / `usuario_devolucion`.

Errores controlados por el servidor:

| Código | ¿Cuándo? |
|---|---|
| **400** | Devolver desde `ugr`; aprobar/devolver salteando un anterior no aprobado; `nivel` fuera de la cadena. |
| **403** | Solo roles con territorio asignado (5/9 depto, 8 municipio): el EDAN está fuera de su jurisdicción. |
| **404** | `id_edan` no existe. |
| **422** | `aprobado:false` sin `observacion` (vacía o en blanco). |
| **401** | Sin token (auth `Bearer`). |

> **Permisos:** desde v2.17.3 las aprobaciones NO dependen de `usuarios.permiso`
> (módulo EDAN) ni de poder editar la cabecera: **cualquier rol autenticado**
> puede aprobar/devolver, y solo se aplica restricción geográfica a roles
> 5/8/9. La edición del formulario EDAN (`PUT /{id}`) sigue restringida como
> antes.

> No hay `DELETE` ni edición del estado manual: la única forma de cambiar un
> estado es pasar por las reglas anteriores.

---

## 7. Migraciones relacionadas

| Migración | Qué hace |
|---|---|
| `database/migrations/v2.17.1_aprobaciones_edan.sql` | Crea la tabla, backfill desde los 4 booleanos y elimina esos booleanos de `edan.edan`. Idempotente. |
| `database/migrations/v2.17.2_drop_ordinal_aprobaciones.sql` | Elimina la columna `ordinal` (el orden lo define el código). Idempotente. |
| `database/migrations/v2.17.3_asegurar_aprobaciones_edan.sql` | **Trigger `trg_edan_crear_aprobaciones`** (`AFTER INSERT` en `edan.edan`) que crea las 4 filas `pendiente` de todo EDAN nuevo + backfill de los EDANs previos incompletos. Idempotente. |
| `database/migrations/v2.17.4_aproban_devolucion.sql` | Agrega `id_usuario_aprobacion` / `fecha_aprobacion` / `id_usuario_devolucion` / `fecha_devolucion`; hace backfill del aprobador desde el `por` de las filas ya `aprobado`; y renombra `por` → `id_usuario_ultima_accion`, `fecha` → `fecha_ultima_accion` (auditoría, no se expone). Idempotente. |
| `database/migrations/v2.17.5_estado_observado_edan.sql` | Agrega el estado **4 = "Observado"** a `edan.estado_edan` y backfillea `edan.edan.id_estado` de los EDANs que no cuadran con su cadena de aprobaciones. Idempotente (probada 3× seguidas). |

### Limitación del backfill de v2.17.4

Solo recupera el aprobador de las filas que estaban **`aprobado`** (donde el `por`
sí era el aprobador). Una fila que ya estuviera `observada` cuando corrió la
migración tiene el `por` de **quien devolvió**, no del que aprobó antes, y no hay
forma de recuperarlo. Al momento de aplicarla no había ninguna fila en ese
estado, así que no se perdió información.

### Garantía de que todo EDAN tenga sus 4 filas

El backfill de **v2.17.1 corre una sola vez**: dentro de un bloque `DO $$` que
solo inserta si la tabla estaba vacía. Como nadie más insertaba en
`aprobaciones_edan`, **todo EDAN creado después de esa migración** (`create_edan`,
`consolidar`, `importar_excel`) se quedaba con 0 filas, y:

- `GET /aprobacion` → **500** (`KeyError` al derivar `estado_global`)
- `PUT /aprobacion/{nivel}` → **500** (`KeyError` al leer el nivel anterior)

**v2.17.3 cierra el hueco en tres capas** (por si alguna falla, siguen las otras):

1. **Trigger de BD** — `AFTER INSERT ON edan.edan` inserta las 4 filas. Cubre los
   3 caminos de creación y cualquier futuro. Es `AFTER` y no `BEFORE` porque
   `aprobaciones_edan.id_edan` tiene FK a `edan.edan(id_edan)`.
2. **Backfill de la migración** — rellena los EDANs que ya existían, con
   `ON CONFLICT DO NOTHING` (no pisa estados ya decididos).
3. **Red de seguridad en el código** — `_asegurar_aprobaciones()`
   (en `api/edan/service.py`) se llama en `get_aprobaciones_edan`,
   `aprobar_edan` y `devolver_edan`; crea las filas faltantes antes de operar.
   Además `_estado_global_aprobaciones` trata un nivel sin fila como
   `pendiente` en vez de romper.

> Para comprobar la integridad: ningún EDAN debe tener ≠ 4 filas.
> `SELECT id_edan FROM edan.edan LEFT JOIN edan.aprobaciones_edan USING (id_edan)
> GROUP BY id_edan HAVING count(nivel) <> 4;` tiene que devolver 0 filas.


---

## 8. Notas para el frontend (en construcción)

- **No calcular nada**: los estados de transición y el `estado_global` los
  resuelve el servidor; el frontend solo refleja `estado_global` y pinta el
  motivo de `observacion` del nivel que lo tenga.
- **Aprobaciones abiertas**: las rutas `/aprobacion` funcionan para cualquier
  rol autenticado (no hace falta permiso de edición EDAN). Los roles 5/8/9
  solo ven/actúan sobre EDAN de su departamento (5/9) o municipio (8).
- **`PUT /edan/{id}` (v2) ya no acepta `aprob_*`** (fueron eliminados);
  las aprobaciones se manejan SOLO por `/aprobacion/{nivel}`.
- **`PUT /edan/{id}` (v2) ya no acepta `id_estado`** (v2.17.5): aunque lo mandes,
  se ignora. El estado lo pone el motor. No hace falta quitarlo del body.
- El campo `observacion` aparece **vacío salvo en el nivel `observado`**.
- Para "ver qué me toca aprobar": mirar `estado_global` (ej. `pendiente_dgr`)
  → es el nivel cuyo nombre está en el sufijo.
- Los 4 niveles arrancan en `pendiente` para todo EDAN nuevo. Lo garantiza el
  trigger `trg_edan_crear_aprobaciones` (v2.17.3) + el backfill de la migración
  + la red de seguridad `_asegurar_aprobaciones()` en cada lectura/escritura de
  `/aprobacion`. **No existe ningún EDAN con aprobaciones vacías** (ver §7).

### Quién aprobó / quién devolvió (v2.17.4)

- Cada nivel ya trae `usuario_aprobacion` y `usuario_devolucion` **embebidos**
  con nombre, usuario y rol: pintar "aprobó Mamen Saavedra" no requiere llamadas
  extra ni resolver ids contra `usuarios.usuario` a mano.
- Para **restringir por rol en la UI** (el servidor NO lo hace, §4), comparar
  `usuario.id_rol` —o el rol del token— contra `rol_aprobador.id_rol` del nivel.
  Ahí está el mapping: `ugr`=6, `alcalde`=8, `dgr`=5, `videcid`=9.
- Al devolver, el nivel devuelto queda `observado` con `usuario_devolucion`, y
  el nivel que devuelve queda `espera_correccion` **también con
  `usuario_devolucion`**. Los dos dicen "yo lo devolví, en este momento".
- `usuario_aprobacion` **sobrevive a la devolución**: un nivel `observado` sigue
  mostrando quién lo aprobó originalmente.
- **No hay bitácora**: cuando el nivel se corrige y vuelve a aprobarse, su
  `usuario_devolucion` se limpia. Si se necesita el historial de rechazos hay que
  crearlo aparte (hoy no existe).
- **No hay "puede_aprobar" ni "dueño del nivel"**: a propósito. El UGR o el
  alcalde de una comunidad pueden cambiar, así que no se expone un usuario
  esperado por nivel. `rol_aprobador` es la única guía, y es del rol, no de la
  persona.

### Pendiente / fuera de alcance

- `total_poblacion_afectada` y las 3 cantidades de familias **no se suman**
  automáticamente al aprobar; se toma el valor de la cabecera.
- Sin `DELETE` ni edición manual de estados: la única vía son las reglas de §4.
- En RIDA, el gate de `api/rida/service.py` sigue exigiendo `id_estado in (3, 5)`.
  Con v2.17.5 el `5` sigue sin existir, así que en la práctica es `== 3`: un EDAN
  se habilita al llegar a **Aprobado**. No se modificó (fuera de alcance). El `5`
  es un id fantasma heredado, y `service_importar.ESTADO_EDAN_CERRADO = 5` también
  lo referencia; ambos quedan pendientes de unificar.

---

## 9. `edan.estado_edan` (v2.17.5)

Desde v2.17.5 el motor de aprobaciones es el **único dueño** de
`edan.edan.id_estado`. Antes cada quien fijaba el estado a mano por su cuenta y
un EDAN con las 4 aprobaciones seguía figurando "Pendiente".

### Catálogo

| `id_estado` | Nombre | Quién lo pone |
|---|---|---|
| 1 | Pendiente aprobaciones | El motor: mientras falte aprobar |
| 2 | Rechazado | **Nadie** — ver abajo |
| 3 | Aprobado | El motor: los 4 niveles `aprobado` |
| 4 | Observado | El motor: algún nivel `observado` |

**Por qué existe "Observado" y por qué "Rechazado" no.** El motor maneja 3
estados por nivel (`pendiente`, `aprobado`, `observado`) y "Observado" es el que
no tenía dónde verse: un EDAN devuelto por el DGR solo podía quedar en
"Pendiente", indistinguible de uno que nadie revisó. Al revés, "Rechazado" (2) es
**inalcanzable**: devolver exige un nivel *anterior* aprobado, y el primero de la
cadena es `ugr`, que no tiene anterior. Por eso el 2 queda reservado y nadie lo
escribe. La fila 4 se agregó en la migración `v2.17.5_estado_observado_edan.sql`.

### Regla de mapeo

Se aplica en `_sincronizar_estado_edan()` (`api/edan/service.py`), dentro de la
**misma transacción** que la aprobación/devolución, antes del `commit`:

| Las 4 filas | `id_estado` |
|---|---|
| alguna `observado` | **4 Observado** |
| las 4 `aprobado` | **3 Aprobado** |
| cualquier otro caso (`pendiente` / `espera_correccion`) | **1 Pendiente aprobaciones** |
| — | 2 Rechazado: nadie lo escribe |

El ciclo se ve así: `1` → aprobar hasta completar `3` → devolver `4` → corregir y
re-aprobar `1` → …

### Qué se cerró para que el motor sea el único dueño

- **`PUT /edan/{id}/estado` eliminado en V1 y V2** (junto con
  `service.cambiar_estado_edan()`, `ROLES_ESTADO_EDAN` y el schema
  `CambiarEstadoEdanIn`). Ya no hay forma de fijar el estado a mano por API.
- **`PUT /edan/{id}` (el update normal) ignora `id_estado`**: se sacó de la
  whitelist de `update_edan`. Si el frontend lo manda en el body se descarta en
  silencio, sin error, para no romper clientes que todavía lo envían.
- **La creación fuerza `id_estado = 1`**: un EDAN nuevo siempre arranca en
  "Pendiente aprobaciones".
- **La sincronización NO toca `fecha_modificacion`**: esa columna maneja el LWW
  por sección del formulario, y que una aprobación la bumpee haría que la copia
  cacheada del cliente quedara vieja. La máquina es independiente del contenido.
- El `UPDATE` usa `IS DISTINCT FROM`: si el estado no cambia no se escribe nada.

### Los GET no cambiaron

Ningún GET del EDAN tenía estados hardcodeados: todos hacen
`LEFT JOIN estado_edan es` y devuelven `es.nombre`, así que **"Observado" aparece
solo en la respuesta**, sin tocar el código de lectura.

La única excepción era `GET /edan/mis-resumen`, que tenía 3 contadores fijos por
id. `total_aprobado` apuntaba al id 4, que hasta v2.17.5 no existía (daba siempre
0) y con "Observado" habría contado los devueltos como aprobados: ahora resuelve
por nombre (como ya hacía `listar_edan_por_estado`) y se agregó
`total_observado`. `total_borrador` y `total_enviado` conservan su nombre y su id
de siempre: **ya estaban desviados antes de v2.17.5** y se dejan así para no
cambiar el contrato de la respuesta. La fuente de verdad del desglose es
`por_estado[]`, que sale del catálogo y no se puede desalinear.
