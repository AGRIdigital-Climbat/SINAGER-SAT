# Documentación: Módulo de Almacenes (SINAGERSAT/RIDA)

**Versión:** 1.0  
**Fecha:** 2025-10-29  
**Base URL:** `/api/v2/almacenes`  
**Esquema:** `rida`  
**Estado:** Implementado (Tablas + APIs)

## 1. Principio Fundamental
- **Descuento de stock/kardex ÚNICAMENTE al despachar.** Al registrar/despachar una **PECOSA** (`rida.entrega`) se generan movimientos `almacen_movimiento(SALIDA -)` y se actualiza `almacen_stock` vía trigger.
- **Entrega a beneficiarios posterior.** `rida.entrega_beneficiario` registra a quién se entregó lo que ya salió del almacén. **NO genera movimientos de kardex/stock**.
- **Cruce con RIDA.** Las necesidades se toman de `rida.necesidad` y/o `rida.solicitud_articulo`. Cobertura calculada desde `almacen_stock`.

## 2. Estructura de Tablas

### 2.1 Núcleo
| Tabla | Descripción |
|---|---|
| `rida.almacen` | Almacenes territoriales (municipal/departamental/nacional). Reemplazo operativo de `rida.cat_almacen`. |
| `rida.almacen_entrada` / `rida.almacen_entrada_detalle` | **NEA** - Notas de Entrada a Almacén. Generan movimientos `ENTRADA (+)`. |
| `rida.almacen_movimiento` | **Kardex inmutable**. Solo INSERT. Campos: `cantidad_signed (+/-)`, `cantidad_abs`, `referencia_tipo` (NEA/PECOSA/CONTEO/ANULACION/OTRO), `nro_documento`. |
| `rida.almacen_stock` | Proyección mantenida por trigger `trg_almacen_stock_update`. `CHECK(cantidad_disponible >= 0)`. Clave única por (almacén, artículo, lote, fecha_vencimiento). |

### 2.2 Solicitudes y Despacho
| Tabla | Descripción |
|---|---|
| `rida.almacen_solicitud` / `rida.almacen_solicitud_detalle` | Solicitud interna de salida. Vinculable a `rida.solicitud`. Estados: SOLICITADA/APROBADA/RECHAZADA/ATENDIDA_PARCIAL/ATENDIDA_TOTAL/CANCELADA. |
| `rida.entrega` (extendida) | **Usada como PECOSA/Despacho**. Campos añadidos: `id_solicitud_salida`, `fecha_despacho`, `id_usuario_despacha`, `id_documento_lista_firmada`, `estado_despacho`. |
| `rida.entrega_detalle` (extendida) | Campos añadidos: `lote`, `fecha_vencimiento`, `cantidad_despachada`, `cantidad_entregada_acumulada`. |

### 2.3 Entregas a Beneficiarios y Evidencias
| Tabla | Descripción |
|---|---|
| `rida.entrega_beneficiario` (extendida) | Entrega por familia vinculada a `rida.entrega`. Añadidos: `codigo_familia`, `ci_jefe_familia`, `nombre_jefe_familia`, `metodo_verificacion`, `id_usuario_entrega`, `fecha_hora_entrega`, `id_documento_lista_firmada`. **Sin movimientos**. |
| `rida.almacen_entrega_evidencia_offline` | Staging para modo offline. `local_uuid`, `local_uuid_evidencia`, `archivo_hash_sha256`, `tipo_evidencia`, `sync_status`, `dispositivo_id`. |
| `rida.solicitud_articulo` (extendida) | Añadido `cantidad_atendida_acumulada` para seguimiento de avance desde RIDA. |
| `rida.cat_articulo` (extendida) | Añadidos `controla_lote`, `controla_vencimiento`, `volumen_unitario_m3`. |

## 3. APIs

### 3.1 Almacenes
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v2/almacenes` | Listado con filtros por scope (rol + municipio/departamento). Filtros: `nivel`, `estado`, `q`. |
| `POST` | `/api/v2/almacenes` | Crear almacén. Genera código automático si no se provee. |
| `GET` | `/api/v2/almacenes/{id}/stock` | Stock por artículo/lote/vencimiento desde `almacen_stock`. |
| `GET` | `/api/v2/almacenes/{id}/kardex` | Últimos movimientos desde `almacen_movimiento` (inmutable). |

### 3.2 Cruce RIDA - Cobertura
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v2/almacenes/cobertura/necesidades-rida` | Cruce entre `rida.necesidad` + `rida.familia`/`formulario_rida` con `almacen_stock`. Calcula necesidad_total, disponible_total, faltante, cobertura_pct. Filtros: `id_municipio`, `id_departamento`, `id_solicitud`. |

### 3.3 Entradas (NEA)
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v2/almacenes/{id_almacen}/entradas` | Crear NEA. Genera `nro_nea`. Inserta detalle y genera movimientos `ENTRADA (+)` en `almacen_movimiento`. Actualiza stock vía trigger. |

**Body ejemplo:**
```json
{
  "tipo": "DONACION",
  "proveedor_donante": "Fundación XYZ",
  "id_documento_soporte": 152,
  "fecha_entrada": "2025-10-29",
  "observaciones": "Donación recibida",
  "detalle": [
    {"id_articulo": 12, "cantidad": 150, "lote": "ARR-DON-01", "fecha_vencimiento": "2027-12-31", "valor_unitario_bs": 5.5}
  ]
}
```

### 3.4 Salidas (PECOSA) - Descuento al despachar
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v2/almacenes/{id_almacen}/salidas` | Crear/Despachar PECOSA en `rida.entrega`. **Al despachar genera movimientos SALIDA (-) en `almacen_movimiento` y actualiza `almacen_stock`. Transaccional.** |

**Body ejemplo:**
```json
{
  "tipo": "DESPACHO",
  "id_solicitud": 123,
  "fecha_salida": "2025-10-29",
  "nombre_quien_recibe": "Comité Comunitario",
  "detalle": [
    {"id_articulo": 12, "cantidad": 50, "lote": "ARR-DON-01", "fecha_vencimiento": "2027-12-31"}
  ]
}
```

### 3.5 Entregas a Beneficiarios (sin movimientos)
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v2/almacenes/salidas/{id_entrega}/entregar-beneficiario` | Registrar entrega por familia en `rida.entrega_beneficiario`. **NO genera movimientos de kardex/stock.** Actualiza `entrega_detalle.cantidad_entregada_acumulada`. |

**Body ejemplo:**
```json
{
  "id_familia": 456,
  "codigo_familia": "FAM-001",
  "ci_jefe_familia": "1234567",
  "nombre_jefe_familia": "Juan Pérez",
  "metodo_verificacion": "CI_PADRON",
  "id_documento_lista_firmada": 789,
  "detalle": [
    {"id_articulo": 12, "cantidad": 25, "lote": "ARR-DON-01"}
  ]
}
```

## 4. Reglas de Negocio
| Regla | Descripción |
|---|---|
| **RO-ALM-01** | **Descuento al despachar.** Solo `POST /salidas` genera movimientos `SALIDA (-)`. |
| **RO-ALM-02** | **Kardex inmutable.** `almacen_movimiento` solo INSERT. Anulaciones con movimiento inverso. |
| **RO-ALM-03** | **Stock >= 0.** Validado por lógica y reforzado por trigger. |
| **RO-ALM-04** | **Entrega sin descuento.** `entregar-beneficiario` no genera movimientos, solo trazabilidad. |
| **RO-ALM-05** | **Cruce con RIDA.** Cobertura calculada desde necesidades/familias sin reserva previa. |
| **RO-ALM-06** | **FEFO.** Priorizar lotes con menor fecha de vencimiento al despachar. |
| **RO-ALM-07** | **Evidencia.** Soporta vinculación de planilla PDF firmada vía `id_documento_lista_firmada`. |

## 5. Archivos Modificados/Creados
- **Migración:** `database/migrations/v2.62.0_almacenes.sql`
- **Módulo API:** `api/almacenes/{__init__,schemas,service,router}.py`
- **Registro:** `api/main.py` (añadido router almacenes en V2_ROUTERS)
- **Seguimiento:** `SEGUIMIENTO_ALMACENES_RIDA.md`
- **Arquitectura:** `ARQUITECTURA_ALMACENES.md` (actualizado previamente)
