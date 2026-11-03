# Arquitectura: Gestión de Ayuda Humanitaria (Work Queue VIDECI)

**Versión:** 1.3 — 29-oct-2026
**Estado:** ✅ IMPLEMENTADO y verificado E2E (migraciones v2.55.0 / v2.56.0 / v2.57.0 / v2.58.0 / v2.60.0 / v2.61.0)
**Contrato funcional:** [`AYUDA_HUMANITARIA_BACKEND.md`](./AYUDA_HUMANITARIA_BACKEND.md) v1.6
**Base URL:** `/api/v2/ayuda-humanitaria` (todas las rutas requieren JWT `Bearer`)

---

## 1. Objetivo

Centro de trabajo (Work Queue) para VIDECI que lista los expedientes de ayuda
humanitaria (solicitudes desde `ENVIADA`, v2.60.0) y gestiona los **pasos 4 al 9** de la
infografía VIDECI con patrón Maestro-Detalle.

**Decisiones de diseño cerradas:**

| # | Decisión |
|---|---|
| 1 | El expediente **ES** la `rida.solicitud` (sin columnas nuevas). El evento se resuelve por `solicitud.id_evento_rida → evento_rida → edan`. |
| 2 | El estado de los pasos 4-9 **no se almacena**: se **deriva** del motor en cada lectura (badge, `dias_en_estado`, asignado). `solicitud.etapa` solo se toca en 3 anclas: `EN_APROBACION` / `RECHAZADA` / `CERRADA`. |
| 3 | Motor de aprobaciones **secuencial de 7 niveles**, tablas propias (aisladas del motor de visaciones de `/rida/solicitudes`, que queda intacto — **conviven**). |
| 4 | Orden de despacho (paso 7) y acta (paso 8) **reutilizan `rida.entrega`** + `entrega_detalle` (sin tablas nuevas). |
| 5 | Motor de cálculo **por KITS**: las fórmulas son datos (`rida.regla_calculo_kit` + `rida.detalle_parametro_kit` desde v2.57.0, reemplaza a `cat_regla_calculo`), CRUD por API, con vista previa sin persistir y suma de cantidades si un artículo se repite en 2 kits. |
| 6 | Rol nuevo **14 "Almacén"** + permiso `CREATE` en módulo RIDA para roles 3, 9 y 14. |
| 7 | `dias_duracion` libre por regla (lo define el frontend; NULL = por día); `sexo` (M/F) opcional; **sin** `condiciones` JSONB en el motor de kits. |
| 8 | **Motor de necesidades (v2.61.0)**: reglas en `rida.regla_necesidad` (condiciones JSONB), cálculo por familia con **techo** y persistencia en `rida.necesidad` (`fuente='motor'`). El motor **manda**: reemplaza las manuales de las categorías que cubre por familia. |

---

## 2. Componentes

### 2.1 Backend (implementado)

| Pieza | Archivo |
|---|---|
| Migración BD (6 tablas + ALTER entrega + rol/permisos) | `database/migrations/v2.55.0_ayuda_humanitaria.sql` |
| Migración BD (unidad de medida) | `database/migrations/v2.56.0_cat_unidad_medida.sql` |
| Migración BD (motor por kits: 2 tablas + DROP `cat_regla_calculo`) | `database/migrations/v2.57.0_regla_calculo_kit.sql` |
| Migración BD (motor de necesidades: `regla_necesidad` + `necesidad.fuente/id_regla_necesidad`) | `database/migrations/v2.61.0_motor_necesidades.sql` |
| Módulo API (router, service, schemas) | `api/ayuda_humanitaria/` (`router.py`, `service.py`, `schemas.py`, `motor.py`, `motor_necesidades.py`) |
| Registro en v2 | `api/main.py` → `V2_ROUTERS` (`("ayuda_humanitaria", ...)`) |

### 2.2 Frontend (consumidor del contrato, §6)

- Work Queue: listado → `GET /expedientes`; gestión → detalle `GET /expedientes/{id}`.
- Catálogos para pintar combos/badges: `/estados`, `/aprobacion/cadena`, `/reglas-calculo`.
- Documentos del expediente: **solo lectura**, ya servidos por
  `GET /api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` (el detalle
  del expediente los incluye en `documentos`).
- Catálogos reutilizados: modalidades (`/rida/solicitudes/cat-modalidades`),
  artículos (`/rida/necesidades/cat-articulos`), técnicos (`/usuarios?id_rol=9`).

---

## 3. Flujo end-to-end (pasos 1-9)

```
PASOS 1-3 (existente, /api/v2/rida/solicitudes — v2.60.0)
  POST → ENVIADA (sin BORRADOR; checklist de instancia 1)
                                                     │
  POST /ayuda-humanitaria/expedientes/{id}/iniciar   ▼  (regla 0: ENVIADA → EN_APROBACION)
  ┌──────────────────────── MOTOR SECUENCIAL (7 niveles) ────────────────────────┐
  │ evaluacion → determinacion → autorizacion → almacen → despacho → entrega → cierre │
  └──────────────────────────────────────────────────────────────────────────────┘
  POST /evaluacion          (paso 4: guarda + aprueba 'evaluacion')
  POST /motor-calculo       (paso 5: kits dinámicos → suma por artículo → solicitud_articulo)
  PUT  /aprobacion/determinacion (paso 5: cierra la determinación)
  PUT  /aprobacion/autorizacion  (paso 6: aprueba o DEVUELVE)
  POST /orden-despacho      (paso 7: rida.entrega + entrega_detalle + aprueba 'almacen')
  POST /preparar → /despachar (paso 7: estado_despacho + aprueba 'despacho')
  POST /acta-recepcion      (paso 8: firmas + PDF + aprueba 'entrega')
  POST /cerrar              (paso 9: aprueba 'cierre' → etapa CERRADA)
```

Devolución (regla 2): `PUT /aprobacion/{nivel} {"aprobado":false,"observacion":"…"}`
→ nivel anterior = `observado` (con el motivo), nivel actual = `espera_correccion`,
badge `OBSERVADA`. Al corregir (re-aprobar el observado), el que devolvió vuelve
a `pendiente`.

---

## 4. Modelo de datos (v2.55.0; motor por kits desde v2.57.0)

### 4.1 Tablas nuevas (esquema `rida`)

| Tabla | Rol |
|---|---|
| `cat_estado_rida` | Catálogo de **badges derivados** (9: EN_APROBACION…RECHAZADA, con `tono` para la UI) |
| `aprobacion_cadena_ayuda` | Config de la cadena: 7 niveles, por `id_modalidad` (NULL = default) |
| `aprobaciones_ayuda_humanitaria` | Instancia del motor: 1 fila por nivel por expediente (`pendiente/aprobado/observado/espera_correccion`, `por`, `fecha`) |
| `solicitud_evaluacion` | Paso 4: evaluación nacional (técnico + observaciones, histórico) |
| `regla_calculo_kit` (v2.57.0) | **Reglas (kits)** del motor de cálculo (§5): criterio, rangos de edad en días, sexo, gestante/discapacidad, `dias_duracion` libre; `estado` = `borrador\|publicada` (v2.58.0: el motor SOLO corre publicadas). Reemplaza a `cat_regla_calculo` (ELIMINADO) |
| `detalle_parametro_kit` (v2.57.0) | **Artículos de cada kit** con `cantidad_base_diaria` (por persona/día) y mín/máx; UNIQUE(id_regla, id_articulo) |
| `regla_calculo_version` (v2.58.0) | **Versiones inmutables** de cada regla publicada: snapshot JSONB (`configuracion_json` = columnas + detalles), `numero_version`, auditoría. UNIQUE(id_regla, numero_version) |
| `ejecucion_calculo` (v2.58.0) | **Historial** de ejecuciones operativas del motor: `id_calculo` UUID, `modo` (`previsualizacion\|operativo`), estado, fecha, usuario |
| `ejecucion_calculo_detalle` (v2.58.0) | Detalle de cada ejecución **por familia y artículo** (`id_version` exacta usada); UNIQUE(id_calculo, id_familia, id_regla, id_articulo) |
| `solicitud_articulo` | Paso 5: artículos determinados (`fuente='motor'|'manual'`, `id_regla` FK → `regla_calculo_kit` para trazabilidad, UNIQUE(id_solicitud,id_articulo)) |

### 4.2 `rida.entrega` reutilizada (ALTER)

| Columna nueva | Uso |
|---|---|
| `nro_orden` | `OD-<año>-<NNNN>` (UNIQUE parcial) — la orden de despacho |
| `estado_despacho` | `GENERADA → EN_PREPARACION → PREPARADA → DESPACHADA` |
| `firmas` (JSONB) | Acta: `[{nombre, ci, cargo, fecha}]` |
| `id_documento` | PDF del acta en `repositorio.documentos` |
| `observaciones_acta` | Texto del acta |

Detalle de artículos despachados: `entrega_detalle` (existente). Recepción por
familia: `entrega_beneficiario` (existente).

### 4.3 Jerarquía del expediente

```
solicitud.id_evento_rida → evento_rida (codigo = codigo_rida)
                         → edan (id_municipio, id_departamento, id_tipo_evento)
                         → formulario_rida → familia → integrante / necesidad   (población del motor)
```

---

## 5. Motor de cálculo por KITS (`rida.regla_calculo_kit` + `detalle_parametro_kit`, v2.57.0)

Cantidad por detalle (artículo del kit):

```
poblacion = nº de filas del pool (familia o integrante) que cumplen TODOS los filtros
cantidad  = clamp(redondeo(cantidad_base_diaria × dias_duracion × poblacion),
                  cantidad_min, cantidad_max)     # dias_duracion NULL = 1
```

| Campo (`regla_calculo_kit`) | Valores |
|---|---|
| `criterio_aplicacion` | `POR_FAMILIA` \| `POR_INTEGRANTE` \| `POR_CONDICION_ESPECIAL` |
| `rango_edad_min_dias` / `max_dias` | Edad del integrante en días (0-24 meses = 730). NULL = sin límite |
| `requiere_gestante` / `requiere_discapacidad` | filtros booleanos |
| `sexo` | `M` \| `F` (opcional) |
| `dias_duracion` | horizonte del kit en días (lo define el frontend); NULL = por día |
| `redondeo` | `ninguno` \| `techo` \| `piso` (default `piso`) |
| `prioridad` / `orden` | desempate del `id_regla` guía al sumar por artículo |

| Campo (`detalle_parametro_kit`) | Valores |
|---|---|
| `id_articulo` | FK `cat_articulo` (RESTRICT); UNIQUE por kit |
| `cantidad_base_diaria` | ración **por persona al día** |
| `cantidad_min` / `cantidad_max` | acotación del detalle |

`POR_FAMILIA` evalúa familias; `POR_INTEGRANTE` y `POR_CONDICION_ESPECIAL`
evalúan integrantes (`POR_CONDICION_ESPECIAL` exige ≥1 filtro activo).

**Al persistir, las cantidades SE SUMAN por artículo** (un artículo en 2 kits se
suma); `solicitud_articulo.id_regla` guarda el kit de mayor prioridad.

**Semillas** (`v2.57.0`): `Ración Alimentaria Familiar Estándar`
(POR_FAMILIA, 30 días → Arroz 0.5/día, Azúcar 0.25/día, Kit de cocina 0.05/día)
y `Kit de Higiene Infantil (0-2 años)` (POR_INTEGRANTE, `max_dias=730`,
Kit de higiene 1/día).

**Reglas de persistencia:** filas `fuente='manual'` nunca se pisan salvo
`{"forzar":true}`; el ajuste manual (`PUT /articulos/{id}`) marca `fuente='manual'`.

---

## 6. Contrato API (32 operaciones en 27 paths, verificadas en `/openapi.v2.json`)

### 6.1 Catálogos

| Método y ruta | Devuelve |
|---|---|
| `GET /estados` | Badges: `[{id_estado_rida, codigo, nombre, tono, orden}]` |
| `GET /aprobacion/cadena` | `{niveles:[{codigo,label,roles,alcance,orden,nom_roles}], default, por_modalidad}` |
| `GET /reglas-calculo` | Kits completos (filtros `id_articulo`, `criterio_aplicacion`, `estado`; ver §6.6) |

### 6.2 Work Queue

`GET /expedientes` — filtros: `estado` (código de badge), `id_municipio`,
`id_departamento`, `id_modalidad`, `tipo_evento`, `fecha_desde/hasta`, `q`
(código RIDA o municipio), `skip/limit` (default 20, máx 100), `todos`.
Orden: más recientes primero. Incluye solicitudes desde `ENVIADA`
(en adelante, v2.60.0) y `RECHAZADA`.

```json
{
  "id_solicitud": 1, "id_evento_rida": 15, "codigo_rida": "070101/2026/003-R",
  "id_modalidad": 1, "nombre_modalidad": "Ayuda Humanitaria",
  "id_municipio": 70101, "nombre_municipio": "Santa Cruz de la Sierra",
  "id_departamento": 7, "nombre_departamento": "Santa Cruz",
  "tipo_evento": "Granizadas", "fecha_solicitud": "2026-10-08T…",
  "etapa": "EN_APROBACION",
  "estado": {"id_estado_rida": 1, "codigo": "EN_APROBACION", "nombre": "En aprobación", "tono": "warning"},
  "badge": "EN_APROBACION", "dias_en_estado": 0,
  "id_usuario_asignado": null, "nombre_tecnico": null,
  "tiene_motor": false, "motor_iniciado": false
}
```

### 6.3 Detalle

`GET /expedientes/{id_solicitud}` → campos del listado + `aprobacion` (máquina
completa) + `evaluacion` + `articulos` + `orden_despacho` (+`detalle`) +
`acta_recepcion` + `documentos` (repositorio del evento, **solo lectura**).

### 6.4 Motor de aprobaciones

| Método y ruta | Cuerpo / respuesta |
|---|---|
| `POST /expedientes/{id}/iniciar` | Regla 0: requiere `ENVIADA` (409 si no) y checklist de instancia 1 completo; idempotente |
| `GET /expedientes/{id}/aprobacion` | `{cadena, estado_global, badge, mi_nivel, niveles:{nivel:{estado,observacion,por,fecha,roles,alcance,puede_aprobar,puede_devolver,es_mio}}}` |
| `PUT /expedientes/{id}/aprobacion/{nivel}` | `{"aprobado":true}` o `{"aprobado":false,"observacion":"≥10 caracteres"}` |

**Errores:** 400 nivel fuera de cadena / devolver desde el primero · 403
rol/alcance · 404 solicitud inexistente · 409 motor no iniciado o nivel
anterior no aprobado (secuencial) · 422 observación <10 caracteres.

**Matriz de roles (regla 4, v1.4):** los 7 niveles → **3, 9** (mismas
funciones; antes `autorizacion/cierre` eran solo del 3 y
`almacen/despacho/entrega` del 9/14 — el rol 14 salió del motor). Admin (1, 2):
bypass total. Alcance por nivel sin cambios: `nacional` en
evaluacion/determinacion/autorizacion/cierre y `departamento` en
almacen/despacho/entrega (compara `usuario.id_departamento` con el expediente).

### 6.5 Acciones de paso

| Ruta | Efecto |
|---|---|
| `POST /{id}/evaluacion` | Guarda evaluación + aprueba `evaluacion` |
| `POST /{id}/motor-calculo/preview` | Ejecuta los kits y **devuelve sin persistir** (`calculados` por detalle + `articulos` por artículo) |
| `POST /{id}/motor-calculo` | Ejecuta los kits, **suma por artículo** + upsert en `solicitud_articulo` (`{"forzar":bool}`) |
| `PUT /{id}/articulos/{id_articulo}` | Ajuste manual (`cantidad`, `aprobado`, `observaciones`) |
| `POST /{id}/autorizar` | Aprueba `autorizacion` |
| `POST /{id}/rechazar` | Terminal → etapa `RECHAZADA` (badge RECHAZADA) |
| `POST /{id}/orden-despacho` | `{id_almacen?, serie:[{id_articulo,cantidad}], observaciones?}` → `rida.entrega` + aprueba `almacen` (409 duplicada) |
| `GET /{id}/orden-despacho` | Orden + detalle de artículos |
| `POST /{id}/preparar` | `{"estado":"EN_PREPARACION"\|"PREPARADA"}` |
| `POST /{id}/despachar` | `{transporte?, placa?}` → DESPACHADA + aprueba `despacho` |
| `POST /{id}/acta-recepcion` | `{id_documento?, firmas:[{nombre,ci,cargo,fecha}], observaciones?}` + aprueba `entrega` |
| `POST /{id}/cerrar` | Aprueba `cierre` → etapa `CERRADA` |

### 6.6 Ciclo de vida de reglas del motor (v2.58.0)

| Método y ruta | Efecto / respuesta |
|---|---|
| `GET /reglas-calculo` | Lista completa (sin paginar). Filtros: `id_articulo`, `criterio_aplicacion`, `estado` (`borrador` \| `publicada`) |
| `POST /reglas-calculo` (roles 1,2) | Crea en **borrador** (`detalles` ≥1 con `id_articulo` + `cantidad_base_diaria`) |
| `GET /reglas-calculo/{id}` | Una regla con `estado`, `version_actual`, `detalles[]` |
| `PUT /reglas-calculo/{id}` (roles 1,2) | Edita. **Editar una regla `publicada` la devuelve a `borrador`** (configuración inmutable: hay que volver a publicar). 400 si no hay cambios; 422 criterio inválido |
| `DELETE /reglas-calculo/{id}` (roles 1,2) | 404 inexistente · **409 si ya generó artículos (`solicitud_articulo`) o aparece en historial de ejecuciones** → desactivar (`activo=false`) en su lugar · 200 si no tiene uso (borra en cascade versiones y detalles) |
| `POST /reglas-calculo/{id}/validar` | Validación completa **sin modificar nada**: `200 {valida:true, errores[], advertencias[], resumen{}}`; `422` si no valida (el `detail` lleva el objeto completo) |
| `POST /reglas-calculo/{id}/simular` | Fórmula con población sintética (`{"poblacion":int, "dias_duracion"?, "detalles"?}`); **no persiste** (`persistido_como_necesidad:false`) |
| `POST /reglas-calculo/{id}/publicar` (roles 1,2) | Exige `{"confirmar":true}` (400 si false) y que la regla valide (422 si no). Crea versión inmutable (snapshot JSONB) → `{publicada:true, regla_id, version}` y habilita la regla para el motor |
| `GET /reglas-calculo/{id}/versiones` | Versiones publicadas, **más reciente primero**: `[{id_version, numero_version, configuracion_json, fecha_publicacion, publicado_por}]` |

### 6.7 Ejecuciones del motor — `/calculos` (v2.58.0)

| Método y ruta | Contrato |
|---|---|
| `POST /calculos` | Ejecuta los kits publicados. Cuerpo `{id_solicitud, modo?, familias?[], reglas?[], forzar?}`: `modo:"previsualizacion"` (default) → `resultados` por familia + `articulos` agregados, **no persiste** (`calculo_id:null`, `necesidades_registradas:false`); `modo:"operativo"` → **exige etapa `EN_APROBACION` (409 si no)**, upsert en `solicitud_articulo` (no pisa `fuente='manual'` salvo `forzar:true`) y registra la ejecución (`calculo_id` UUID). `familias[]` sólo en previsualización (**400** en operativo; **404** si alguna no pertenece al evento). `reglas[]: [{id_regla, numero_version?}]` → versión exacta desde su snapshot (**404** versión inexistente, **409** regla en borrador o sin versiones); omitir = todas las publicadas y activas. `inventario_consultado` siempre `false` (el inventario se consulta después de la aprobación) |
| `GET /calculos?id_solicitud=` | Historial del expediente (más recientes primero). `limit` (default 100, máx 500), `skip`, `todos=true` |
| `GET /calculos/{id_calculo}` | Cabecera: `{id_calculo, id_solicitud, modo, estado, fecha_ejecucion, id_usuario, total_detalles, total_familias}` |
| `GET /calculos/{id_calculo}/detalle` | Filas por familia: `[{id_familia, id_regla, id_version, id_articulo, articulo, cantidad_calculada, unidad_medida}]` |

**Scope:** todas las rutas de `/calculos` validan el ámbito del usuario
(`validar_scope`: roles **5, 8, 9, 14** contra el departamento/municipio del
expediente; el resto con token nacional) → **403** fuera de jurisdicción.

---

## 7. Campos derivados (nunca almacenados)

| Campo | Derivación |
|---|---|
| `estado` / `badge` | Regla 3: algún `observado` → OBSERVADA · etapa RECHAZADA → RECHAZADA · cadena completa → CERRADA · si no, badge del primer nivel no aprobado (`cierre` pendiente ⇒ ENTREGADA) |
| `dias_en_estado` | Días desde `fecha` del nivel accionable (primer no aprobado); `MAX(fecha)` si ya cerró |
| `id_usuario_asignado` / `nombre_tecnico` | `por` del nivel accionable |
| `tiene_motor` | `EXISTS` fila en `solicitud_articulo` |
| `motor_iniciado` | `EXISTS` filas del motor para el expediente |

---

## 8. Matriz de alineación (verificada E2E el 12-oct-2026, v2.57.0)

| # | Contrato | Estado |
|---|---|---|
| 1 | Work Queue `GET /expedientes` con derivados + filtros + `todos` | ✅ E2E (total, `q`, `estado=RECHAZADA/CERRADA`, `tipo_evento`) |
| 2 | Detalle Maestro-Detalle con `documentos` read-only | ✅ E2E (2 docs del evento incluidos) |
| 3 | Motor secuencial: iniciar → 7 pendientes, aprobar fuera de orden → **409** | ✅ E2E |
| 4 | Ciclo de devolución (422 corta → observado/espera_correccion → re-aprobar → pendiente) | ✅ E2E (badge OBSERVADA → AUTORIZADA) |
| 5 | Motor de cálculo por kits (preview no persiste; suma por artículo; manual no se pisa; `forzar` sí) | ✅ E2E (raciones por familia + kit por edad en días, suma al repetir artículo) |
| 6 | Orden `OD-2026-0001` + serie + duplicada 409 + preparar + despachar | ✅ E2E |
| 7 | Acta JSONB + cierre → etapa CERRADA, badge CERRADA | ✅ E2E |
| 8 | Rechazo → RECHAZADA con badge derivado | ✅ E2E |
| 9 | CRUD kits: 422 criterio inválido, 409 artículo inexistente/repetido, PUT (detalles), DELETE | ✅ E2E |
| 10 | Permisos: rol 14 + CREATE para 3/9/14 en RIDA | ✅ Migración (E2E con admin) |
| 11 | Convivencia con `/rida/solicitudes` (sin cambios) | ✅ Intacto |

## 9. Notas y límites conocidos

- El filtro `estado` del listado se aplica **en Python** (el badge es derivado);
  volúmenes de la cola son pequeños y `todos=true` cubre lotes/KPIs.
- `GET /usuarios` solo filtra por UN rol (`id_rol`); multi-rol (`roles=3,9`)
  pendiente.
- Al re-ejecutar el motor con `forzar=true` sobre una fila manual, la cantidad
  se recalcula pero la fila conserva `fuente='manual'` (trazabilidad del ajuste).
- El listado excluye etapas pre-paso-4 (BORRADOR…CORREGIDA): esas son del flujo
  de visaciones de `/rida/solicitudes`.
