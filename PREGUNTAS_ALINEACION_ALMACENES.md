# Preguntas para alinear APIs de Almacenes con ARQUITECTURA_ALMACENES.md (Sección 14)

**Fecha:** 2025-10-29  
**Objetivo:** Afinar lo que falta para dejar el backend 100% alineado con la arquitectura propuesta.

> **Instrucción:** Completar el campo `Respuesta:` con la opción elegida o con la respuesta específica solicitada.

## 1) Flujo: Solicitud -> Aprobación -> PECOSA

| # | Pregunta | Opciones sugeridas | Respuesta |
|---|---|---|---|
| 1.1 | ¿Debe ser **obligatorio** pasar por `almacen_solicitud` para generar una PECOSA, o se puede crear una PECOSA directa desde el almacén? | `Obligatorio` / `Opcional (solo en emergencias)` / `Siempre directo` | _______________ |
| 1.2 | ¿Quiénes pueden **crear** la solicitud de salida? ¿Quiénes pueden **aprobar/rechazar**? | Especificar roles (ej. UGR, Coordinador, Jefe de Almacén, DGR, VIDECI, Almacén - Rol 14, etc.) | _______________ |
| 1.3 | ¿Al aprobar la solicitud, se can **modificar las cantidades** (`cantidad_aprobada`) por artículo, or se debe aprobar tal como fue solicitada? | `Solo autorizar lo solicitado` / `Permitir ajustar cantidades` / `Solo with justificación` | _______________ |
| 1.4 | ¿Debe vincularse `almacen_solicitud` with `rida.solicitud` (expediente RIDA) de forma **obligatoria** en esta fase, or lo dejamos **opcional**? | `Obligatorio` / `Opcional` / `Solo cuando venga desde RIDA` | _______________ |

## 2) Despacho, Lotes y FEFO

| # | Pregunta | Opciones sugeridas | Respuesta |
|---|---|---|--- |
| 2.1 | ¿Aplicamos **FEFO estricto** (menor `fecha_vencimiento` primero) sin importar lo que envíe the body, o lo **sugerimos** and permitimos que el usuario elija otro lote? | `Estricto (sistema asigna lotes)` / `Sugerido (permite elegir)` / `Mixto` | _______________ |
| 2.2 | ¿Si un artículo tiene varios lotes y con uno solo no se cubre la cantidad, **se permite consumir varios lotes** en la misma PECOSA? | `Si` / `No` | _______________ |
| 2.3 | ¿Para artículos with `controla_lote = FALSE` permitimos despachar **sin lote ni fecha de vencimiento**? | `Si` / `No` | _______________ |
| 2.4 | ¿Validamos stock **antes** of insertar en `almacen_movimiento` with an error `409/400` entendible, or dejamos que el trigger siga lanzando su excepción? | `Validar pre-insert (recomendado)` / `Solo trigger` / `Ambos` | _______________ |

## 3) Entrega a Beneficiarios (Familias)

| # | Pregunta | Opciones sugeridas | Respuesta |
|---|---|---|---|
| 3.1 | ¿Usamos **obligatoriamente** `rida.almacen_entrega_beneficiario_detalle` for guardar qué artículo/lote entregó cada familia, or basta with actualizar `rida.entrega_detalle.cantidad_entregada_acumulada`? | `Obligatorio detalle por familia` / `Solo actualizar acumulado` / `Ambos` | _______________ |
| 3.2 | ¿El **Acta de Entrega firmada** (`id_documento_lista_firmada` or nuevo `id_acta_entrega`) must be **obligatorio** al registrar la entrega? | `Si` / `No` | _______________ |
| 3.3 | ¿Qué datos are **obligatorios** for `entregar-beneficiario`? | Marcar opciones: `ci_jefe_familia`, `nombre_jefe_familia`, `codigo_familia`, `metodo_verificacion', `id_usuario_entrega`, `fecha_hira_entrega', `id_acta_entrega', 'testigo_nombre', 'testigo_ci' | _______________ |
| 3.4 | ¿Permitimos entregar a **alguien distinto al jefe/a de familia**? If `Si`, ¿qué exigimos? (CI of quien recibe, parentesco, autorización written) | `Solo jefe de familia` / `Permitir with autorización escrita' / `Permitir with CI + parentesco + testigo' / Otro (especificar) | _______________ |
| 3.3b? Or better adjust 3.3 | N/A | N/A | _______________ |
| 3.5 | ¿Validamos against `rida.familia` that esa familia exista y pertenezca al ámbito of esa PECOSA? | `Si` / `No` / `Solo si viene codigo_familia` | _______________ |
| 3.6 | ¿Puede la **misma familia** recibir por the **misma PECOSA** más de una vez? | `No (bloquear)` / `Si (permitir entregas parciales)` | _______________ |

## 4) Estados, Parciales and Cierre

| # | Pregunta | Opciones sugeridas | Respuesta |
|---|------|---|---|
| 4.1 | ¿Pasamos `rida.entrega` a usar estados claros: `BORRADOR / DESPACHADA / ENTREGADA_PARCIAL / ENTREGTAGA_TOTAL / CERRADA / ANULADA`? Or mantenemos `estado` + `estado_despacho' as hoy? | `Unificar a un solo campo` / `Mantener ambos` / `Migrar a nuevos estados' | _______________ |
| 4.2 | ¿Al llegar to `ENTREGADA_TOTAL', **bloqueamos** cualquier nuevo `POST /salidas/{id_entrega}/entregar-beneficiario'? | `Si` / `No` | _______________ |
| 4.3 | ¿Necesitamos el endpoint `GET /api/v2/almacenes/{id_almacen}/salidas/{id_entrega}/pendiente-entregar' exactly as lo pide la arquitectura? | `Si` / `No' / 'With leves ajustes' (especificar) | _______________ |
| 4.4 | ¿Quién can mark/cerrar una PECOSA as `CERRADA'? | Especificar roles (ej. Jefe de Almacén, DGR, VIDECI, Admin, Almacén) | _______________ |

## 5) Habilitación por Municipio / Alcance

| # | Pregunta | Opciones sugeridas | Respuesta |
|---|---|---|---|
| 5.1 | ¿Es correcto el criterio: **for operar a municipio se requiere a `rida.almacen` ACTIVO with `nivel='municipal' and its `id_municipio'**? | `Si' / 'Ajustar' (especificar) | _______________ |
| 5.2 | ¿Los almacenes migrados from `rida.cat_almacen' (v2.62.0) should be **immediatamente operativos** with that same criterio, or there is some extra adjustment? | `Ya operativos' / 'Requieren revisión' / 'Hay que re-apuntar something' (especificar) | _______________ |
| 5.3 | ¿Los usuarios with rol **Almacén (14)** must be able to operate **únicamente** the/los almacenes of their territory though they are not the creators? | `Si' / 'No' | __placeholder]]</script>
