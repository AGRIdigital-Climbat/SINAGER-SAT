# Seguimiento: Módulo de Almacenes (Tablas -> APIs)

**Objetivo:** Diseñar y crear las tablas para el módulo de almacenes autónomo por territorio, cruzando necesidades de **familias en RIDA** con stock de almacenes. Luego implementar APIs hasta ahí.

**Principio clave:** El descuento de stock y la actualización del kardex ocurre **únicamente al despachar la PECOSA**. La entrega a beneficiarios por familia es posterior, vinculada a esa PECOSA, sin generar movimientos.

**Alcance acordado:** Solo Tablas -> APIs. Sin frontend, sin app móvil completa, sin sincronización masiva forzada.

---

## Estado General
- [x] Diseño arquitectónico documentado (`ARQUITECTURA_ALMACENES.md`)
- [x] Plan de ejecución definido
- [x] Fase 0: Lectura e identificación de entidades RIDA (completada)
- [ ] Fase 1: Diseño y creación de tablas
- [ ] Fase 2: Implementación de APIs (hasta ahí)
- [ ] Validación final

---

## Hallazgos Fase 0 (Entidades RIDA)
**Reutilizables directamente:**
- `rida.familia` (id_familia, id_formulario, codigo_ficha, id_jefe, n_integrantes, estado) + `rida.integrante` (ci, nombres/apellidos, es_jefe, parentesco)
- `rida.formulario_rida` (id_municipio, id_departamento, id_evento_rida)
- `rida.necesidad` (id_necesidad, id_familia, id_categoria, id_articulo, cantidad, estado, fuente/id_regla_necesidad desde v2.61.0)
- `rida.solicitud` (id_solicitud, id_formulario, id_modalidad, codigo_expediente, etapa, id_municipio/id_departamento)
- `rida.solicitud_articulo` (id_solicitud_articulo, id_solicitud, id_articulo, cantidad, aprobado, fuente, id_regla)
- `rida.entrega` / `rida.entrega_detalle` / `rida.entrega_beneficiario` (ya existen, se reutilizarán con cuidado)

**Catálogos/base:**
- `rida.cat_articulo` (unidad_de_medida, peso_unitario_kg, costo_referencia_bs)
- `rida.cat_almacen` (actual, será migrado a `rida.almacen` como reemplazo operativo)
- `usuarios.usuario` (roles + id_municipio/id_departamento)
- `repositorio.documentos` (para planilla/lista firmada PDF)

**Cruce propuesto:** partir de `rida.necesidad` (y/o `rida.solicitud_articulo`) validadas → consolidar por artículo/territorio → consultar `almacen_stock` por almacenes del municipio/departamento/nacional → generar `almacen_solicitud` vinculada a `rida.solicitud`/necesidad → aprobar → PECOSA (descuento al despachar) → entrega por familia vinculada a PECOSA sin movimientos → actualizar atendido.

---

## Fase 1: Diseño y creación de tablas
| Tarea | Estado | Responsable | Notas |
| :-- | :-- | :-- | :-- |
| Crear `rida.almacen` (migrar desde `rida.cat_almacen`) | Pendiente | Agente | Reemplazo operativo. Marcar `cat_almacen` como legacy. Reapuntar `rida.entrega.id_almacen`. |
| Crear `rida.almacen_entrada` / `almacen_entrada_detalle` | Pendiente | Agente | NEA. |
| Crear `rida.almacen_salida` / `almacen_salida_detalle` | Pendiente | Agente | PECOSA. Ampliar con `id_solicitud` (FK rida.solicitud), `id_solicitud_salida`, `fecha_despacho`, `id_usuario_despacha`, `id_documento_lista_firmada`, `cantidad_despachada`, `cantidad_entregada_acumulada`. |
| Crear `rida.almacen_movimiento` (inmutable) | Pendiente | Agente | Fuente de verdad. Solo INSERT. |
| Crear `rida.almacen_stock` + trigger UPSERT | Pendiente | Agente | Proyección. CHECK (cantidad_disponible >= 0). |
| Crear `rida.almacen_solicitud` / `almacen_solicitud_detalle` | Pendiente | Agente | Solicitud interna. Vincular a `rida.solicitud`. |
| Crear `rida.almacen_entrega_beneficiario` / `almacen_entrega_beneficiario_detalle` | Pendiente | Agente | Entrega por familia vinculada a PECOSA despachada. Sin movimientos. Vincular a `rida.familia` cuando aplique. |
| Crear `rida.almacen_entrega_evidencia_offline` | Pendiente | Agente | Soporte `local_uuid`, `local_uuid_evidencia`, `archivo_hash_sha256`, `sync_status`, `dispositivo_id`. |
| Ampliar `rida.cat_articulo` (controla_lote/controla_vencimiento) | Pendiente | Agente | Para validar lote/vencimiento. |
| Reapuntar `rida.entrega.id_almacen` -> `rida.almacen` | Pendiente | Agente | Mantener compatibilidad. |
| Índices, checks, correlativos | Pendiente | Agente | NEA-AAAA-NNNN, PECOSA-AAAA-NNNN. |
| Migración SQL unificada | Pendiente | Agente | Ordenado, idempotente según estilo repo. |
| Validación de esquema & conciliación kardex/stock | Pendiente | Agente | Prueba trigger + suma movimientos vs stock. |

---

## Fase 2: APIs (hasta ahí)
| Tarea | Estado | Responsable | Notas |
| :-- | :-- | :-- | :-- |
| Router `/api/v2/almacenes`, permisos/scope | Pendiente | Agente | Reutilizar `validar_scope`. |
| Almacenes CRUD | Pendiente | Agente | Por nivel/territorio. |
| Entradas (NEA) | Pendiente | Agente | `ENTRADA (+)`, validación lote/vencimiento. |
| Solicitudes de salida | Pendiente | Agente | CRUD + aprobar/rechazar. |
| Cruce RIDA + Cobertura | Pendiente | Agente | `GET /cobertura/necesidades-rida`, `POST /solicitudes-salida/desde-necesidades-rida`. Consultar `almacen_stock`. |
| Salidas (PECOSA) con descuento | Pendiente | Agente | **ÚNICAMENTE al despachar**. FEFO, transaccional, valida stock >=0. |
| Entregas por familia | Pendiente | Agente | Vinculada a PECOSA despachada. Validar pendiente. Sin movimientos. Vincular planilla PDF. |
| Stock, Kardex, Alertas | Pendiente | Agente | Kardex inmutable. Alertas bajo/crítico/por vencer/vencido. |
| Conteos físicos (mínimo) | Pendiente | Agente | Con ajustes trazables. |
| Pruebas integradas ciclo completo | Pendiente | Agente | Conciliación stock/kardex. |

---

## Bitácora
| Fecha | Acción | Resultado | Notas |
| :-- | :-- | :-- | :-- |
| 2025-10-29 | Inicio seguimiento | Completado | Documento creado. |
| 2025-10-29 | Lectura entidades RIDA | Completado | Identificadas `familia`, `integrante`, `formulario_rida`, `necesidad`, `solicitud`, `solicitud_articulo`, `entrega*`, catálogos. |

## Listado propuesto para aprobación (Fase 1)
### Reutilizar (sin crear)
- `rida.familia`, `rida.integrante`, `rida.formulario_rida`, `rida.necesidad`, `rida.solicitud`, `rida.solicitud_articulo`
- `rida.entrega`, `rida.entrega_detalle`, `rida.entrega_beneficiario` (solo vincular donde aplique)
- `rida.cat_articulo`, `usuarios.usuario`, `repositorio.documentos`, `shared.*`

### Crear/Ampliar
- `rida.almacen` (migrar desde `rida.cat_almacen`, marcar legacy, reapuntar `rida.entrega.id_almacen`)
- `rida.almacen_entrada` / `almacen_entrada_detalle` (NEA)
- `rida.almacen_salida` / `almacen_salida_detalle` (PECOSA: añadir `id_solicitud`, `id_solicitud_salida`, `fecha_despacho`, `id_usuario_despacha`, `id_documento_lista_firmada`, `cantidad_despachada`, `cantidad_entregada_acumulada`)
- `rida.almacen_movimiento` (inmutable, solo INSERT)
- `rida.almacen_stock` + trigger UPSERT (CHECK >= 0)
- `rida.almacen_solicitud` / `almacen_solicitud_detalle` (vincular a `rida.solicitud`)
- `rida.almacen_entrega_beneficiario` / `almacen_entrega_beneficiario_detalle` (vinculada a PECOSA despachada, sin movimientos; vincular a `rida.familia`)
- `rida.almacen_entrega_evidencia_offline` (`local_uuid`, `local_uuid_evidencia`, `archivo_hash_sha256`, `sync_status`, `dispositivo_id`)
- Ampliar `rida.cat_articulo`: `controla_lote` BOOLEAN DEFAULT FALSE, `controla_vencimiento` BOOLEAN DEFAULT FALSE

**Acción:** Esperando aprobación para generar migración SQL unificada y pasar a APIs.

## Actualización: Extender tablas existentes (evitar duplicados)
Tras revisar `api/ayuda_humanitaria`, se decide **extender** en lugar de duplicar:

| Tabla | Acción | Detalle |
| :-- | :-- | :-- |
| `rida.entrega` | **EXTENDER** | Servirá como **PECOSA/Despacho** del módulo almacén. Añadir: `id_solicitud_salida` (FK `almacen_solicitud`), `fecha_despacho`, `id_usuario_despacha`, `id_documento_lista_firmada`. Mantener compatibilidad con flujo actual de `ayuda_humanitaria`. |
| `rida.entrega_detalle` | **EXTENDER** | Añadir: `lote`, `fecha_vencimiento`, `cantidad_despachada`, `cantidad_entregada_acumulada` DEFAULT 0. Usado por FEFO y control de entregas parciales. |
| `rida.entrega_beneficiario` | **EXTENDER** | Añadir: `codigo_familia`, `ci_jefe_familia`, `nombre_jefe_familia`, `metodo_verificacion`, `id_usuario_entrega`, `fecha_hora_entrega`, `id_documento_lista_firmada`. Vinculado a `rida.entrega` despachada. **Sin movimientos de kardex**. |
| `rida.solicitud_articulo` | **EXTENDER** | Añadir: `cantidad_atendida_acumulada` NUMERIC(12,2) DEFAULT 0. Controla avance sobre lo solicitado desde RIDA. |
| `rida.cat_almacen` | **MIGRAR A `rida.almacen`** | Crear `rida.almacen`, migrar datos, marcar `cat_almacen` como legacy, reapuntar `rida.entrega.id_almacen`. |

**Nuevas (únicas para kardex/stock/solicitud interna):**
- `rida.almacen`, `rida.almacen_movimiento` (inmutable), `rida.almacen_stock` + trigger, `rida.almacen_entrada`/`almacen_entrada_detalle`, `rida.almacen_solicitud`/`almacen_solicitud_detalle`, `rida.almacen_entrega_evidencia_offline`, ampliación `rida.cat_articulo`.

**Regla estricta:** El descuento (`almacen_movimiento` SALIDA -) y actualización de `almacen_stock` ocurre **ÚNICAMENTE** al pasar `rida.entrega` a `DESPACHADA/REGISTRADA`. Las entregas por `rida.entrega_beneficiario` **NO** generan movimientos.

## Acción Actual
- [x] Revisado uso de `rida.entrega` en ayuda_humanitaria - se reutilizará/extenderá
- [ ] Crear migración SQL con tablas necesarias (crear desde cero donde falten, extender donde aplique)
- [ ] Crear módulo API `api/almacenes/` 
- [ ] Implementar flujo completo hasta APIs

## Estado Actual
- [x] Fase 0 completada
- [x] Migración v2.62.0_almacenes.sql creada (extiende rida.entrega/entrega_detalle/entrega_beneficiario/solicitud_articulo, crea rida.almacen, kardex/stock, NEA, solicitudes, evidencias offline)
- [x] Módulo API api/almacenes/ creado (schemas, service, router)
- [x] Registrado en api/main.py como /api/v2/almacenes
- [ ] Ejecutar migración / probar endpoints

## Actualización
- [x] API almacenes con CRUD completo + paginación (limit/skip/todos), filtros y scope geográfico
- [x] Stock/Kardex paginados con filtros
- [x] Regla aplicada: descuento SOLO al despachar PECOSA; entrega a beneficiarios SIN movimientos
- [x] Auditoría (fecha_creacion/modificacion, id_usuario_crea/modifica) en tablas clave
