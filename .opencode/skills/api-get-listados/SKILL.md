---
name: api-get-listados
description: Use when creating or modifying any GET list endpoint in this repo's FastAPI SINB API (api/sinb/router_v2.py, api/usuarios, api/shared, api/repositorio) — mandates cantidad/limit returning the most recent first, a todos option, filters, and skip/limit pagination with the SuccessResponse envelope. Catalogs (departamentos, municipios, roles, cat-*...) are EXEMPT and must return complete lists. Trigger words: listar, listado, GET, filtros, paginación, cantidad, todos, catálogo.
---

# Convención de endpoints GET de listado (SINAGERSAT)

Todo endpoint **GET que devuelva una lista dinámica** en esta API debe soportar,
en este orden de parámetros: **cantidad → paginación → todos → filtros**.

## Exenciones — no aplica a

1. **Catálogos → SIEMPRE COMPLETOS.** Un catálogo es un listado fijo/pequeño de
   elementos de referencia. **No lleva `limit`, ni `skip`, ni `todos`, ni
   paginación: devuelve la lista entera** (los consumidores los necesitan
   completos para poblar combos, selects y validaciones; truncarlos rompe la UI).

   Catálogos de este repo (exentos):
   - **Geografía**: `/departamentos`, `/provincias`, `/municipios`, `/cultivos`,
     `/cultivos/grupos`, `/pecuario`, `/pecuario/grupos`
   - **Usuarios**: `/roles`, `/aplicaciones`, `/acciones`, `/usuarios/permisos/*`
   - **SINB (catálogos bioculturales)**: `/grupo`, `/indicador-natural`,
     `/caracteristica`, `/comportamiento`, `/significado`, `/zona-geografica`,
     `/categoria-pronostico`, `/escenario`
   - **Repositorio**: `/tipos`
   - **RIDA (prefijo `cat-`)**: `cat-parentesco`, `cat-tipo-albergue`,
     `cat-tipo-discapacidad`, `cat-articulos`, `cat-categorias`,
     `cat-insumos-rehabilitacion`, `cat-tipos-rehabilitacion`,
     `cat-modalidades`, `cat-etapas`, `cat-requisitos`, `cat-cadena-aprobacion`
   - **EDAN**: `/estados`, `/tipo-evento`, `/tipo-localidad`, `/grupo-vulnerable`,
     `/grupo-etario`, `/localidades-estado`

   Regla práctica: si el conjunto es **fijo, pequeño (< ~200 filas) y se usa para
   poblar selects/validaciones** → es catálogo → **viene completo, sin
   paginar**. Los catálogos **sí pueden llevar filtros** (`?q=`, `?id_grupo=`)
   y **sí** deben ordenarse de forma estable (alfabético/código); ahí no manda
   "los más recientes primero".

2. **GET por `{id}`** (devuelve un solo item) — no aplica.

3. **Endpoints de acción/consulta puntual** — no aplica: `/mapa`, `/consultar`,
   `/resumen`, `/geojson`, `/descargar`, `/alertas`, `/hist*`, `/serie*`,
   `/poblacion`, `/export*`, `/sync/pull`, `/buscar`, `/preview`, `/firma*`,
   `/validar*`, `/check*`, `/health`, `/openapi*`, `/docs`.

La convención de abajo aplica **sólo a listados dinámicos** (reportes,
pronósticos, documentos, eventos, solicitudes, auditoría, historiales…): cosas
que crecen indefinidamente.

## Reglas

1. **`limit` (cantidad)** — siempre presente. Devuelve **los más recientes
   primero**: el `ORDER BY` debe ser por fecha de creación/emisión `DESC`
   (`creado_en DESC`, `fecha_emision DESC, creado_en DESC`, etc.). El default
   del repo es `15` (pronósticos), `50` o `100` (auditoría); tope `le=100` o
   `le=500` según volumen.
2. **`skip` (paginación)** — va junto a `limit`. Se activa **sólo cuando se
   pide cantidad**: `Query(0, ge=0)`. Es el offset de la página.
3. **`todos: bool = Query(False)`** — opción "todos": al `true` devuelve el
   conjunto completo **sin `LIMIT`/`OFFSET`** (ignora `skip`/`limit`).
4. **Filtros opcionales** — todos con `Query(None, description="Filtrar por X")`
   y tipo fuerte (`UUID | None`, `date | None`, `Literal[...]` para enums).
   Fechas con sufijo `_desde`/`_hasta`. Filtro geográfico: **uno a la vez**
   (si llegan 2+ → `400`, como en `/usuarios/auditoria`).
5. **Respuesta** — siempre `SuccessResponse`/`DataListResponse[T]` con
   `data` + `total` (total **sin** paginar, calculado con los mismos filtros).
   **Nunca** cambiar la forma de la respuesta existente: la web está
   desplegada en http://10.10.0.24:8000 y consume estos JSON tal cual.
6. Enums en filtro → `Literal[...]` en el router **y** `CAST(:x AS
   schema.enum)` en el SQL (un `str` crudo compara mal contra el tipo enum y
   revienta en 500; ver `service.py` estado de pronósticos).

## Router — plantilla

```python
@router.get("/recurso", tags=[TAG],
            response_model=DataListResponse[RecursoResponse],
            summary="Listar recursos (los más recientes primero)")
def listar_recursos(
    limit: int = Query(100, ge=1, le=500, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    id_grupo: UUID | None = Query(None, description="Filtrar por grupo"),
    fecha_desde: date | None = Query(None, description="Fecha desde (ISO: YYYY-MM-DD)"),
    fecha_hasta: date | None = Query(None, description="Fecha hasta (ISO: YYYY-MM-DD)"),
    estado: Literal["EMITIDO", "ACEPTADO"] | None = Query(None, description="Filtrar por estado"),
    db: Session = Depends(get_db),
):
    """Lista de recursos con cantidad, paginación y filtros.

    - `limit`: cantidad; siempre entrega los más recientes primero.
    - `todos=true`: ignora `limit`/`skip` y devuelve el conjunto completo.
    - `skip`: offset, sólo tiene sentido junto a `limit`.
    """
    data, total = service.get_recursos(
        db, limit=limit, skip=skip, todos=todos,
        id_grupo=id_grupo, fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta, estado=estado,
    )
    return SuccessResponse(message="Recursos listados", data=data, total=total)
```

## Service — plantilla

```python
def get_recursos(db: Session, *, limit: int = 100, skip: int = 0,
                 todos: bool = False, **filtros) -> tuple[list, int]:
    where, params = ["r.estado = 'ACTIVO'"], {}

    if filtros.get("id_grupo"):
        where.append("r.id_grupo = :id_grupo")
        params["id_grupo"] = filtros["id_grupo"]
    if filtros.get("fecha_desde"):
        where.append("r.fecha >= :fecha_desde")
        params["fecha_desde"] = filtros["fecha_desde"]
    if filtros.get("fecha_hasta"):
        where.append("r.fecha <= :fecha_hasta")
        params["fecha_hasta"] = filtros["fecha_hasta"]
    if filtros.get("estado"):
        where.append("r.estado = CAST(:estado AS sinb.estado_validacion)")
        params["estado"] = filtros["estado"]

    where_clause = " AND ".join(where)

    # cantidad → paginación; todos=true → sin LIMIT/OFFSET
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    query_params = {**params, "limit": limit, "skip": skip} if not todos else params

    rows = _rows(db, f"""
        SELECT r.*
        FROM sinb.recurso r
        WHERE {where_clause}
        ORDER BY r.fecha_emision DESC, r.creado_en DESC
        {page}
    """, query_params)

    total = _row(db, f"""
        SELECT COUNT(*) AS total FROM sinb.recurso r WHERE {where_clause}
    """, params)["total"]

    return rows, total
```

Puntos clave del service:

- `page = "" if todos else " LIMIT :limit OFFSET :skip"` — patrón literal de
  `usuarios/service.py:get_auditoria`.
- `query_params` sólo lleva `limit`/`skip` cuando **no** es `todos` (pasarlos
  sin usarlos rompe la query parametrizada).
- `total` se calcula con los **mismos filtros** pero **sin** paginar.
- Orden reciente: `ORDER BY <fecha> DESC` (ver ejemplos reales abajo).

## Ejemplos reales de referencia

| Endpoint | Archivo | Nota |
|---|---|---|
| `GET /pronostico-largo` (default 15, le=100) | `api/sinb/router_v2.py:527` + `service.get_pronosticos_estacionales` | `ORDER BY fecha_emision DESC, creado_en DESC`; total con filtros |
| `GET /usuarios/auditoria` (`todos=true`) | `api/usuarios/router.py` + `service.get_auditoria:452` | patrón `page = "" if todos` y validación de 1 solo filtro geográfico |
| `GET /usuarios/sesiones` | `api/usuarios/router.py:210` | devuelve `total=len(items)` |
| `GET /repositorio/documentos` | `api/repositorio/router.py:392` | `skip=0, limit=50, le=200` |

## Checklist al crear/modificar un GET de listado

- [ ] **¿Es catálogo?** (fijo, pequeño, para poblar selects) → **viene COMPLETO**:
      sin `limit`, sin `skip`, sin `todos`, sin paginación; orden estable
      (alfabético/código). Filtros opcionales sí. **Si no es catálogo → seguir abajo.**
- [ ] `limit` con default, `ge=1`, `le` acotado y description de "los más recientes"
- [ ] `skip` con `ge=0` (paginación)
- [ ] `todos: bool = Query(False, ...)` y rama sin `LIMIT/OFFSET` en el service
- [ ] `ORDER BY` por fecha `DESC` (los más recientes primero)
- [ ] Filtros con `Query(None, description=...)` y tipos fuertes; enums con `Literal` + `CAST`
- [ ] `total` = total sin paginar con los mismos filtros
- [ ] Respuesta `SuccessResponse(message=..., data=..., total=...)` sin alterar estructura existente
- [ ] Docstring en español explicando `limit`/`skip`/`todos` y los filtros
