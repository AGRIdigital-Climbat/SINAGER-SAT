# 04 · Necesidades humanitarias y rehabilitación

> Registrar **qué necesita** cada familia o localidad, y administrar los catálogos de ayuda.
> Prefijo: `/api/v2/rida/necesidades`

## 1. Estructura

```
cat_categoria_ayuda  (7 categorías de Ayuda Humanitaria)
        │ 1:N
        ▼
cat_articulo  ←── necesidad (cantidad, prioridad, estado)
                        │
                        ├── id_familia    → necesidad de una familia
                        └── id_formulario → necesidad de la localidad

cat_tipo_rehabilitacion (5 tipos) ── 1:N ── cat_insumo_rehabilitacion (25 insumos)
```

**Categorías activas (v2.35.0):**

| Código | Nombre |
|---|---|
| `ALIMENTOS` | Alimentos |
| `HERRAMIENTAS_MENORES` | Herramientas menores |
| `REF_VIVIENDA` | Refugio y vivienda |
| `ROPA_CAMA` | Ropa de cama |
| `ROPA_AGUA` | Ropa de agua |
| `ARTICULOS_HIGIENE` | Artículos de higiene |
| `ARTICULOS_COCINA` | Artículos de cocina |

> Las categorías antiguas (`TECHO_ABRIGO`, `ALIMENTACION_AGUA`, `SALUD_HIGIENE`, `MEDIOS_VIDA`, `EQUIPAMIENTO_UMEE`) quedaron **inactivas** en v2.35.0: siguen visibles para leer datos históricos, pero no deben usarse en registros nuevos.

## 2. Checklist

- [ ] 1. Revisar catálogos (`GET /cat-categorias`, `GET /cat-unidades-medida`, `GET /cat-articulos`).
- [ ] 2. Crear la necesidad en el formulario o en la familia.
- [ ] 3. Asignar prioridad (1 = alta).
- [ ] 4. Al completar la entrega, marcar `estado: true`.
- [ ] 5. (Opcional) Configurar reglas del motor de necesidades y previsualizar
      el cálculo en la solicitud de Ayuda Humanitaria (§7).

## 3. Catálogos

| Endpoint | Método | Contenido |
|---|---|---|
| `/cat-categorias` | GET / POST | Categorías de ayuda humanitaria |
| `/cat-categorias/{id}` | GET / PUT / DELETE | Detalle con sus artículos; el DELETE requiere que no tenga artículos |
| `/cat-unidades-medida` | GET / POST | Unidades de medida (v2.56.0): `kit`, `caja`, `kg`, `litro`, `unidad` |
| `/cat-unidades-medida/{id}` | GET / PUT / DELETE | El DELETE devuelve 409 si hay artículos que la usan |
| `/cat-articulos` | GET / POST | Artículos (`codigo` autogenerado `ART-000001`); `unidad_de_medida` opcional (default `unidad`) |
| `/cat-articulos/{id}` | GET / PUT / DELETE | |
| `/cat-tipos-rehabilitacion` | GET / POST | 5 tipos de rehabilitación |
| `/cat-tipos-rehabilitacion/{id}` | GET / PUT / DELETE | Borrado lógico (`activo=false`) |
| `/cat-insumos-rehabilitacion` | GET / POST | 25 insumos/servicios |
| `/cat-insumos-rehabilitacion/{id}` | GET / PUT / DELETE | Borrado lógico |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v2/rida/necesidades/cat-categorias
```

> La escritura de catálogos exige los permisos `RIDA.CREATE` / `RIDA.UPDATE` (roles 1, 2, 6, 7).

## 4. Registrar una necesidad

**Necesidad de una familia:**

`POST /api/v2/rida/necesidades/familias/{id_familia}/necesidades`

```json
{
  "id_categoria_ayuda": 7,
  "id_articulo": 31,
  "cantidad": 10,
  "prioridad": 1,
  "estado": false,
  "id_necesidad_off": "nec-20261005-01"
}
```

**Necesidad de una localidad (formulario):**

`POST /api/v2/rida/necesidades/formularios/{id_formulario}/necesidades`

```json
{
  "id_categoria_ayuda": 8,
  "id_articulo": 44,
  "cantidad": 50,
  "prioridad": 2
}
```

| Campo | Regla |
|---|---|
| `id_articulo` | **Obligatorio** |
| `id_categoria_ayuda` | **Obligatorio** y debe coincidir con la categoría del artículo |
| `cantidad` | Obligatoria, **> 0** |
| `prioridad` | `1` Alta · `2` Media · `3` Baja (default 3) |
| `estado` | `false` = pendiente · `true` = completada (default `false`) |
| `id_necesidad_off` | Clave offline para sincronización |

> `unidad_de_medida` **no se envía** en las necesidades: se toma del artículo (`cat_articulo`), que a su vez se valida contra el catálogo `cat_unidad_medida` (campo de solo lectura en la respuesta).

## 5. Consultar y modificar

| Endpoint | Uso |
|---|---|
| `GET /formularios/{id}/necesidades` | Todas las necesidades de una localidad |
| `GET /familias/{id}/necesidades` | Las de una familia |
| `GET /necesidades/{id}` | Detalle |
| `PUT /necesidades/{id}` | Modificar cantidad, prioridad o `estado` |
| `DELETE /necesidades/{id}` | Eliminar |

```bash
# Marcar como completada
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"estado": true}' \
  http://localhost:8000/api/v2/rida/necesidades/necesidades/2
```

## 6. Lote offline

`POST /api/v2/rida/necesidades/sync`

```json
{
  "necesidades": [
    {"id_necesidad_off": "nec-1", "id_familia_off": "fam-1",
     "id_categoria_ayuda": 7, "id_articulo": 31, "cantidad": 10, "prioridad": 1},
    {"id_necesidad_off": "nec-2", "id_familia_off": "fam-2",
     "id_categoria_ayuda": 8, "id_articulo": 44, "cantidad": 5, "prioridad": 3}
  ]
}
```

Respuesta: `{"necesidades": [...], "errores": [...]}` — el lote **nunca falla completo**. Detalle: [Cap. 08](08-offline-y-sincronizacion.md).

## 7. Motor de necesidades (v2.61.0)

Genera las necesidades de una familia a partir de **reglas** configurables, en
lugar de cargarlas manualmente. Se ejecuta desde el expediente de Ayuda
Humanitaria.

| Endpoint | Método | Uso |
|---|---|---|
| `/api/v2/ayuda-humanitaria/reglas-necesidad` | GET / POST | Listado (filtros `activo`, `criterio_aplicacion`, `id_categoria_ayuda`) y alta |
| `/api/v2/ayuda-humanitaria/reglas-necesidad/{id}` | GET / PUT / DELETE | Detalle/edición; DELETE → 409 si ya generó necesidades |
| `/api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades/preview` | POST | Evalúa y devuelve sin persistir (cualquier etapa) |
| `/api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades` | POST | Calcula y persiste; solo `ENVIADA`/`EN_APROBACION` |

**Regla:**

```json
{
  "nombre": "Kit gestante",
  "id_categoria_ayuda": 7,
  "id_articulo": 31,
  "criterio_aplicacion": "POR_CONDICION_ESPECIAL",
  "cantidad_base": 2,
  "dias_duracion": 30,
  "prioridad": 10,
  "condiciones": {"gestante": true, "edad_max_dias": 3650},
  "activo": true
}
```

- `POR_FAMILIA`: aplica a todas las familias, sin condiciones.
- `POR_INTEGRANTE`: cuenta los integrantes (con filtros opcionales).
- `POR_CONDICION_ESPECIAL`: exige al menos una condición (`gestante`,
  `discapacidad`, `edad_min_dias`, `edad_max_dias`, `sexo` `M`/`F`).
- Fórmula: `ceil(cantidad_base × (dias_duracion or 1) × poblacion_familia)`,
  sin mínimos ni máximos; la unidad se toma de `cat_articulo`.
- Al persistir, **reemplaza** las necesidades manuales de las categorías
  cubiertas por familia; las categorías sin regla se conservan.
- La respuesta incluye `familias`, `articulos_distintos`, `unidades`,
  `manuales_reemplazadas` y `motoras_eliminadas`.

## 8. Relación con la modalidad de Rehabilitación

Las necesidades registradas aquí alimentan las modalidades **3 · Rehabilitación-Insumos** y **4 · Rehabilitación-Reconstrucción** de las solicitudes ([Cap. 05](05-solicitudes-workflow.md)). Los catálogos de rehabilitación (`cat_tipos_rehabilitacion`, `cat_insumo_rehabilitacion`) describen los servicios e insumos disponibles:

| Tipo | Ejemplos de insumo |
|---|---|
| `DEFENSIVOS` | Colchonetas de gavión, mallas de gavión |
| `SECTOR_PECUARIO` | Reconstituyente, alimento balanceado, forraje |
| `SISTEMAS_AGUA` | Bebederos, politubo 3"/2" |
| `VIAS_TALUDES` | *(según catálogo cargado)* |
| `CUBIERTAS` | *(según catálogo cargado)* |

## 9. Errores frecuentes

| Error | Causa | Solución |
|---|---|---|
| `422 cantidad debe ser > 0` | Cantidad en cero o negativa | Usa valores positivos |
| `400 La categoría no coincide con el artículo` | `id_categoria_ayuda` ≠ categoría real del artículo | Consulta `GET /cat-articulos/{id}` |
| `403 Sin permiso: CREATE en RIDA` | Rol sin escritura | [Cap. 01 §3](01-acceso-y-roles.md) |
| `422` en reglas de necesidad | Clave de `condiciones` desconocida o `POR_CONDICION_ESPECIAL` sin filtros | Revisa §7 |
| `409` al persistir el motor | La solicitud no está en `ENVIADA`/`EN_APROBACION` | Usa `preview` o espera la etapa válida |

---

**Anterior:** [03 · Eventos](03-eventos.md) · **Siguiente:** [05 · Solicitudes y workflow](05-solicitudes-workflow.md)
