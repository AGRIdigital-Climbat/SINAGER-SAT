"""Service de la familia EDAN PADRE (cabecera) — APIs nuevas uuid-first (§20.17).

Mismo comportamiento que las APIs viejas de cabecera (consolidar, consolidar
pendientes, deshacer consolidación, obtener/listar EDAN) pero con el CONTRATO
de las APIs nuevas:

- POST: identidad SOLO por uuid (`uuid_edan` del cliente + localidades por
  `uuid_edan_localidad`); sin `id_local` (columna legacy de `edan.edan`).
- GET: por uuid o id (`ref`); respuestas con **id + uuid en todos los
  niveles** (cabecera, localidades, grupos de pendientes).
- **LWW sin `version`**: `version` (columna interna + trigger
  `trg_bump_version`) nunca se expone; si llega en un payload se descarta
  (la cabecera del EDAN no acepta `version` en ningún endpoint nuevo).
- La ESCRITURA reutiliza `service.consolidar` / `service.deshacer_consolidacion`
  (validaciones, triggers `trg_uuid_edan`/`trg_edan_crear_aprobaciones` y
  `db_error` intactos); aquí solo se resuelven uuids y se forma la respuesta.

Ver PLAN_APIS_V2_EDAN.md §20.17.
"""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..pagination import paginar_lista
from . import service as service_viejo
from . import service_v2_nuevas as nuevas

# estado "Aprobado UGR" — el único consolidable (igual que la API vieja)
_ESTADO_APROBADO = 3


def _edan_por_ref(db: Session, ref: str) -> dict:
    """Resuelve `ref` = uuid_edan o id_edan numérico -> {id_edan, uuid_edan}."""
    u = None
    if ref and not str(ref).isdigit():
        u = nuevas._parse_uuid(ref, "uuid_edan")
    row = db.execute(text(
        "SELECT id_edan, uuid_edan FROM edan.edan WHERE "
        + ("uuid_edan = :u" if u else "id_edan = :i")),
        {"u": u, "i": None if u else int(ref)}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"EDAN no encontrado: {ref}")
    return dict(row)


def _edan_public(db: Session, row) -> dict:
    """Fila de `edan.edan` -> respuesta pública: sin `version` ni `id_local`
    (§20.17, igual que `_row_public` de las APIs nuevas) + **todo `id_*` con
    su JSON recursivo** (§20.16: municipio→departamento/provincia,
    tipo_evento, estado_edan, id_usuario_ugr/alcalde→usuario→rol,
    id_importacion→importacion). `skip_pk=id_edan` evita auto-anidar la
    cabecera en sí misma."""
    return nuevas._resolver_ids(db, nuevas._row_public(row), skip_pk="id_edan")


def _localidades_docs(db: Session, user: dict, id_edan: int,
                      comprimido: bool = False) -> list[dict]:
    """Localidades del EDAN como documento nuevo {cabecera, 14 secciones,
    fotos} (contrato de GET /formularios/{uuid}/completo). El scope ya se
    validó a nivel EDAN: sin chequeo por localidad (`chequear_acceso=False`),
    igual que la API vieja que armaba localidades con `_build_localidad`."""
    locs = db.execute(text("""
        SELECT uuid_edan_localidad FROM edan.edan_localidades
        WHERE id_edan = :id ORDER BY id_edan_localidad
    """), {"id": id_edan}).mappings().all()
    return [nuevas.get_formulario_completo(db, str(l["uuid_edan_localidad"]), user,
                                           comprimido=comprimido,
                                           chequear_acceso=False)
            for l in locs]


def _edan_completo(db: Session, user: dict, id_edan: int, modo: str = "detallado") -> dict | None:
    """EDAN completo estilo nuevo: cabecera pública resuelta (§20.16) +
    `localidades[]` (documentos completos con id+uuid en todos los niveles) +
    `resumen_secciones` + `reportes_rea`; `sumatorias` sólo en modo compacto
    (mismo comportamiento que `service.get_edan_completo` viejo)."""
    row = db.execute(text("SELECT * FROM edan.edan WHERE id_edan = :id"),
                     {"id": id_edan}).mappings().first()
    if not row:
        return None
    edan = _edan_public(db, row)
    edan["num_localidades"] = db.execute(text(
        "SELECT COUNT(*) FROM edan.edan_localidades WHERE id_edan = :id"),
        {"id": id_edan}).scalar()
    comprimido = modo == "compacto"
    out = {
        **edan,
        "localidades": _localidades_docs(db, user, id_edan, comprimido=comprimido),
        "resumen_secciones": service_viejo._get_resumen_secciones(db, id_edan),
        "reportes_rea": [dict(r) for r in db.execute(text("""
            SELECT id_reporte, comunidad, fecha_evento, hora_evento,
                   id_municipio, id_tipo_evento, descripcion
            FROM rea.reporte_evento WHERE id_edan = :id_edan ORDER BY id_reporte
        """), {"id_edan": id_edan}).mappings().all()],
    }
    if comprimido:
        out["sumatorias"] = service_viejo._get_sumatorias(db, id_edan)
    return out


# ---------------------------------------------------------------------------
# GET /formularios...: obtener y listar EDAN (uuid o id)
# ---------------------------------------------------------------------------
def get_edan_nuevo(db: Session, user: dict, ref: str, modo: str = "detallado") -> dict:
    info = _edan_por_ref(db, ref)
    # mismo control de alcance que el GET viejo (5/8/9 → depto/municipio)
    service_viejo.validar_scope_edan(db, user, info["id_edan"])
    data = _edan_completo(db, user, info["id_edan"], modo=modo)
    if not data:
        raise HTTPException(status_code=404, detail=f"EDAN no encontrado: {ref}")
    return data


# Secciones con columna `fotografia` (patrón "con foto" de la API vieja)
_FOTO_SECCIONES = (
    "edan_localidades_danos_viales", "edan_localidades_danos_infra_publica",
    "edan_localidades_danos_vivienda", "edan_localidades_danos_agricultura",
    "edan_localidades_danos_pecuario", "edan_localidades_salud_establecimientos",
    "edan_localidades_servicios_basicos", "edan_localidades_unidades_educativas",
    "edan_localidades_infra_productiva",
)


def _cond_alguna_foto() -> str:
    """EXISTS de alguna foto en alguna sección de alguna localidad del EDAN.

    (El filtro `con_foto`/`sin_foto` de la API vieja apuntaba a la columna
    `edan.edan.fotografia`, que NO existe -> 500 preexistente; aquí se
    traduce a la semántica real: EDAN con/sin fotos en sus localidades.)"""
    subs = " OR ".join(
        f"EXISTS (SELECT 1 FROM edan.{t} s WHERE s.id_edan_localidad = lf.id_edan_localidad"
        f" AND s.fotografia IS NOT NULL AND s.fotografia <> '')"
        for t in _FOTO_SECCIONES)
    return (f"EXISTS (SELECT 1 FROM edan.edan_localidades lf"
            f" WHERE lf.id_edan = e.id_edan AND ({subs}))")


def listar_edans_nuevo(db: Session, user: dict, f: dict, skip: int, limit: int,
                       todos: bool) -> tuple[list, int]:
    """Mismos filtros/scope que el GET / viejo (`_filtros_dep`: scope
    geográfico forzado; roles 6/7 → sólo sus EDAN) pero con items estilo
    nuevo (cabecera §20.16 sin `version`/`id_local` + `localidades[]`
    completas con id+uuid, igual que la API vieja incluía sus localidades)."""
    f = dict(f)
    extras: list[str] = []
    if f.pop("con_foto", None):
        extras.append(_cond_alguna_foto())
    if f.pop("sin_foto", None):
        extras.append("NOT " + _cond_alguna_foto())
    conds, params = service_viejo._filters(f)
    conds = conds + extras
    where = " WHERE " + " AND ".join(conds) if conds else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM edan.edan e{where}"), params).scalar()
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    query = """
        SELECT e.*, (SELECT COUNT(*) FROM edan.edan_localidades lc
                     WHERE lc.id_edan = e.id_edan) AS num_localidades
        FROM edan.edan e""" + where + " " + service_viejo._order_clause(f) + page
    params = dict(params)
    if not todos:
        params["limit"] = limit
        params["skip"] = skip
    rows = db.execute(text(query), params).mappings().all()
    items = []
    for r in rows:
        item = _edan_public(db, r)
        item["localidades"] = _localidades_docs(db, user, item["id_edan"])
        items.append(item)
    return items, total


# ---------------------------------------------------------------------------
# POST /consolidar — SOLO uuid (§20.17)
# ---------------------------------------------------------------------------
def consolidar_nuevo(db: Session, user: dict, payload: dict) -> dict:
    """Consolida localidades aprobadas en un EDAN nuevo.

    Dos formas exactamente (XOR, validado en el schema):

    - **Canónica**: `localidades`: SOLO `uuid_edan_localidad` (resueltos a id
      interno); uuid inexistente → 404.
    - **Legada (DEPRECATED)**: `id_municipio` + `id_tipo_evento` +
      `localidad_ids` (ids numéricos), idéntica al body viejo
      POST /edan/consolidar: vacío → 400 "Debe incluir al menos una
      localidad"; id desconocido o municipio/tipo incoherente con los
      declarados → 400 clásico (paridad exacta con la API vieja).
    - `uuid_edan`: identidad del EDAN generada por el cliente; si llega NULL
      el trigger `trg_uuid_edan` la genera (comportamiento previo intacto).
    - **Idempotencia**: si `uuid_edan` ya existe y TODAS las localidades
      pedidas ya están en ese EDAN → devuelve el EDAN (reintento de red);
      si existe y no coincide → 409.
    - Misma validación de consolidabilidad que la API vieja (aprobadas=estado
      3, sin EDAN, mismo municipio+tipo_evento — derivados de las filas):
      400 con el mensaje clásico.
    """
    uuids: list[UUID] = []
    for x in payload.get("localidades") or []:
        uuids.append(nuevas._parse_uuid(str(x), "uuid_edan_localidad"))
    filas: list[dict]

    if uuids:
        uuids = list(dict.fromkeys(uuids))
        ph = ", ".join(f":u{i}" for i in range(len(uuids)))
        rows = db.execute(text(f"""
            SELECT id_edan_localidad, uuid_edan_localidad, id_edan, id_municipio,
                   id_tipo_evento, id_edan_localidad_estado
            FROM edan.edan_localidades WHERE uuid_edan_localidad IN ({ph})
        """), {f"u{i}": str(u) for i, u in enumerate(uuids)}).mappings().all()
        by_uuid = {r["uuid_edan_localidad"]: dict(r) for r in rows}
        faltantes = [str(u) for u in uuids if u not in by_uuid]
        if faltantes:
            raise HTTPException(status_code=404,
                                detail=f"Localidad no encontrada: {', '.join(faltantes)}")
        filas = [by_uuid[u] for u in uuids]
    else:
        # Forma legada (DEPRECATED): ids numéricos — paridad con la API vieja
        localidad_ids = payload.get("localidad_ids") or []
        if not localidad_ids:
            raise HTTPException(status_code=400,
                                detail="Debe incluir al menos una localidad")
        ids = list(dict.fromkeys(int(i) for i in localidad_ids))
        ph = ", ".join(f":i{n}" for n in range(len(ids)))
        rows = db.execute(text(f"""
            SELECT id_edan_localidad, uuid_edan_localidad, id_edan, id_municipio,
                   id_tipo_evento, id_edan_localidad_estado
            FROM edan.edan_localidades WHERE id_edan_localidad IN ({ph})
        """), {f"i{n}": v for n, v in enumerate(ids)}).mappings().all()
        filas = [dict(r) for r in rows]
        # Vacío o incoherente (id desconocido / mun+tipo distintos de los
        # declarados) → 400 con el MISMO texto que service.consolidar
        if (len(filas) != len(ids)
                or {f["id_municipio"] for f in filas} != {payload["id_municipio"]}
                or {f["id_tipo_evento"] for f in filas} != {payload["id_tipo_evento"]}):
            raise HTTPException(status_code=400, detail=(
                "Algunas localidades no son consolidables: deben estar aprobadas, "
                "sin EDAN y del mismo municipio/tipo de evento"))
        # Orden de los ids pedidos (como la rama uuid)
        order = {v: n for n, v in enumerate(ids)}
        filas.sort(key=lambda f: order[f["id_edan_localidad"]])

    # Idempotencia por uuid_edan (reintento de POST tras corte de red)
    uuid_edan = payload.get("uuid_edan")
    if uuid_edan:
        uuid_edan = nuevas._parse_uuid(str(uuid_edan), "uuid_edan")
        ex = db.execute(text("SELECT id_edan FROM edan.edan WHERE uuid_edan = :u"),
                        {"u": str(uuid_edan)}).mappings().first()
        if ex:
            # sólo es reintento si el EDAN existente tiene EXACTAMENTE las
            # mismas localidades pedidas (subconjunto u otras → 409)
            ids_ex = {r[0] for r in db.execute(text(
                "SELECT id_edan_localidad FROM edan.edan_localidades WHERE id_edan = :i"
            ), {"i": ex["id_edan"]}).all()}
            ids_pedidos = {f["id_edan_localidad"] for f in filas}
            if ids_ex == ids_pedidos:
                data = _edan_completo(db, user, ex["id_edan"])
                if data:
                    return data
            raise HTTPException(status_code=409, detail=(
                "uuid_edan ya existe y no corresponde a esta consolidación"))

    pares = {(f["id_municipio"], f["id_tipo_evento"]) for f in filas}
    consolidables = (
        len(pares) == 1
        and all(f["id_edan"] is None
                and f["id_edan_localidad_estado"] == _ESTADO_APROBADO for f in filas)
    )
    if not consolidables:
        raise HTTPException(status_code=400, detail=(
            "Algunas localidades no son consolidables: deben estar aprobadas, "
            "sin EDAN y del mismo municipio/tipo de evento"))
    (id_municipio, id_tipo_evento) = pares.pop()

    result = service_viejo.consolidar(
        db, id_municipio, id_tipo_evento,
        [f["id_edan_localidad"] for f in filas], user["id_usuario"],
        uuid_edan=uuid_edan)
    data = _edan_completo(db, user, result["id_edan"])
    return data if data else result


# ---------------------------------------------------------------------------
# GET /consolidar/pendientes — grupos con localidades id + uuid
# ---------------------------------------------------------------------------
# rangos de fecha combinables (AND): tabla/helper compartidos con las APIs nuevas
_RANGOS_FECHA = nuevas._RANGOS_FECHA
def _consolidables(db: Session, id_municipio: int | None, estado_nombre: str | None,
                   id_estado: int | None,
                   fecha_llenado_desde=None, fecha_llenado_hasta=None,
                   fecha_evento_desde=None, fecha_evento_hasta=None,
                   fecha_modificacion_desde=None,
                   fecha_modificacion_hasta=None) -> list[dict]:
    """Igual que `service.listar_consolidables` (mismos grupos y agregados)
    pero cada grupo trae además `localidades[]` con id + uuid por localidad
    (§20.17) y sus FK geográficas anidadas (§20.16)."""
    conds = ["l.id_edan IS NULL"]
    params: dict = {}
    if id_municipio is not None:
        conds.append("l.id_municipio = :id_municipio")
        params["id_municipio"] = id_municipio
    if id_estado is not None:
        conds.append("l.id_edan_localidad_estado = :id_estado")
        params["id_estado"] = id_estado
    elif estado_nombre:
        conds.append("""l.id_edan_localidad_estado IN (
            SELECT id_edan_localidad_estado FROM edan.edan_localidades_estado
            WHERE LOWER(nombre) LIKE LOWER(:estado_patron)
        )""")
        params["estado_patron"] = f"{estado_nombre}%"
    conds += nuevas._cond_rangos("l.", nuevas._vals_fecha({
        "fecha_llenado_desde": fecha_llenado_desde,
        "fecha_llenado_hasta": fecha_llenado_hasta,
        "fecha_evento_desde": fecha_evento_desde,
        "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_modificacion_desde": fecha_modificacion_desde,
        "fecha_modificacion_hasta": fecha_modificacion_hasta,
    }), params)
    where = " AND ".join(conds)
    rows = db.execute(text(f"""
        SELECT l.id_municipio, m.nombre AS municipio_nombre,
               d.id AS id_departamento, d.nombre AS departamento_nombre,
               p.id AS id_provincia, p.nombre AS provincia_nombre,
               l.id_tipo_evento, te.nombre AS tipo_evento_nombre,
               COUNT(*) AS cantidad_localidades,
               ARRAY_AGG(l.id_edan_localidad ORDER BY l.id_edan_localidad) AS localidad_ids,
               json_agg(json_build_object(
                   'id_edan_localidad', l.id_edan_localidad,
                   'uuid_edan_localidad', l.uuid_edan_localidad,
                   'localidad', l.localidad,
                   'id_edan_localidad_estado', l.id_edan_localidad_estado,
                   'id_usuario', l.id_usuario
               ) ORDER BY l.id_edan_localidad) AS localidades,
               COALESCE(SUM(l.total_poblacion_afectada), 0) AS total_poblacion_afectada,
               COALESCE(SUM(l.total_familias_afectadas), 0) AS total_familias_afectadas,
               COALESCE(SUM(l.total_familias_damnificadas), 0) AS total_familias_damnificadas,
               MIN(l.fecha_evento) AS fecha_evento
        FROM edan.edan_localidades l
        LEFT JOIN shared.municipio m ON m.id = l.id_municipio
        LEFT JOIN shared.departamento d ON d.id = l.id_departamento
        LEFT JOIN shared.provincia p ON p.id = l.id_provincia
        LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = l.id_tipo_evento
        WHERE {where}
        GROUP BY l.id_municipio, m.nombre, d.id, d.nombre, p.id, p.nombre,
                 l.id_tipo_evento, te.nombre
        ORDER BY te.nombre, m.nombre
    """), params).mappings()
    groups = []
    for r in rows:
        g = dict(r)
        for loc in g.get("localidades") or []:
            if loc.get("uuid_edan_localidad") is not None:
                loc["uuid_edan_localidad"] = str(loc["uuid_edan_localidad"])
        # FK anidadas del grupo (§20.16): municipio/provincia/departamento/tipo_evento
        groups.append(nuevas._resolver_ids(db, g))
    return groups


def pendientes_nuevo(db: Session, user: dict, id_municipio: int | None,
                     estado: str | None, id_estado: int | None,
                     limit: int | None, skip: int, todos: bool,
                     fecha_llenado_desde=None, fecha_llenado_hasta=None,
                     fecha_evento_desde=None, fecha_evento_hasta=None,
                     fecha_modificacion_desde=None,
                     fecha_modificacion_hasta=None) -> tuple[list, int]:
    scope = service_viejo.scope_geografico(user)
    if "id_municipio" in scope:
        id_municipio = scope["id_municipio"]
    if "id_departamento" in scope:
        id_municipio = None
    data = _consolidables(db, id_municipio, estado, id_estado,
                          fecha_llenado_desde=fecha_llenado_desde,
                          fecha_llenado_hasta=fecha_llenado_hasta,
                          fecha_evento_desde=fecha_evento_desde,
                          fecha_evento_hasta=fecha_evento_hasta,
                          fecha_modificacion_desde=fecha_modificacion_desde,
                          fecha_modificacion_hasta=fecha_modificacion_hasta)
    if "id_departamento" in scope:
        data = [g for g in data if g.get("id_departamento") == scope["id_departamento"]]
    if "id_municipio" in scope:
        data = [g for g in data if g.get("id_municipio") == scope["id_municipio"]]
    total = len(data)
    return paginar_lista(data, limit, skip, todos), total


# ---------------------------------------------------------------------------
# PUT /{ref}/deshacer — aplica y responde (sin preview)
# ---------------------------------------------------------------------------
def deshacer_nuevo(db: Session, user: dict, ref: str) -> dict:
    """Disuelve la consolidación (mismas validaciones que la API vieja:
    sólo borrador, sólo el UGR que consolidó, sin documentos en repositorio)
    y devuelve el resultado con id + uuid en todos los niveles."""
    info = _edan_por_ref(db, ref)
    id_edan = info["id_edan"]
    cab = db.execute(text("""
        SELECT id_edan, uuid_edan, codigo_edan FROM edan.edan WHERE id_edan = :id
    """), {"id": id_edan}).mappings().first()
    if not cab:
        raise HTTPException(status_code=404, detail=f"EDAN no encontrado: {ref}")
    locs = [dict(r) for r in db.execute(text("""
        SELECT id_edan_localidad, uuid_edan_localidad, localidad
        FROM edan.edan_localidades WHERE id_edan = :id ORDER BY id_edan_localidad
    """), {"id": id_edan}).mappings().all()]

    result = service_viejo.deshacer_consolidacion(db, id_edan, user["id_usuario"])

    return {
        "edan": {"id_edan": cab["id_edan"], "uuid_edan": str(cab["uuid_edan"]),
                 "codigo_edan": cab["codigo_edan"]},
        "localidades_liberadas": result["localidades_liberadas"],
        "localidades": [
            {"id_edan_localidad": l["id_edan_localidad"],
             "uuid_edan_localidad": str(l["uuid_edan_localidad"]),
             "localidad": l["localidad"], "id_edan": None}
            for l in locs
        ],
    }
