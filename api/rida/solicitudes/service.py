from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from datetime import date

from ...pagination import pagina_limit_offset


def _row(db: Session, query: str, params: dict) -> dict | None:
    result = db.execute(text(query), params).fetchone()
    return dict(result._mapping) if result else None


def _rows(db: Session, query: str, params: dict) -> list:
    result = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in result]


def listar_modalidades(db: Session) -> list:
    return _rows(db, "SELECT id_modalidad, nombre, descripcion, activo FROM rida.cat_modalidad WHERE activo = TRUE ORDER BY id_modalidad", {})


def listar_requisitos(db: Session, id_modalidad: int | None = None) -> list:
    params = {}
    filtro = ""
    if id_modalidad:
        filtro = " WHERE id_modalidad = :id_modalidad"
        params = {"id_modalidad": id_modalidad}
    query = f"""
        SELECT id_requisito, id_modalidad, orden, nombre_paso, 
               id_tipo_documento, instancia, es_documento, es_hito_aprobacion, activo
        FROM rida.cat_requisito
        {filtro}
        ORDER BY id_modalidad, orden
    """
    return _rows(db, query, params)


def get_evento_geo(db: Session, id_evento_rida: int) -> dict | None:
    """Geografía y estado del EVENTO RIDA (evento -> EDAN: un solo municipio
    por evento). Reemplaza a get_formulario_geo desde v2.41.0."""
    query = """
        SELECT e.id_municipio, e.id_departamento,
               m.nombre AS municipio_nombre, d.nombre AS departamento_nombre,
               e.codigo_edan, ce.codigo AS evento_codigo
        FROM rida.evento_rida ev
        JOIN edan.edan e ON e.id_edan = ev.id_edan
        LEFT JOIN shared.municipio m ON m.id = e.id_municipio
        LEFT JOIN shared.departamento d ON d.id = e.id_departamento
        LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
        WHERE ev.id_evento_rida = :id_evento_rida
    """
    return _row(db, query, {"id_evento_rida": id_evento_rida})


def crear_solicitud(db: Session, id_evento_rida: int, id_modalidad: int, id_usuario: int, observaciones: str | None = None) -> int:
    geo = get_evento_geo(db, id_evento_rida)
    if not geo:
        raise HTTPException(status_code=404, detail=f"Evento RIDA {id_evento_rida} no encontrado")
    if geo["evento_codigo"] == "CERRADO":
        raise HTTPException(status_code=400, detail="El evento RIDA está cerrado; no admite nuevas solicitudes")
    
    query = """
        INSERT INTO rida.solicitud (id_evento_rida, id_modalidad, id_municipio, id_departamento, id_usuario_crea, observaciones, etapa, fecha_inicio)
        VALUES (:id_evento_rida, :id_modalidad, :id_municipio, :id_departamento, :id_usuario_crea, :observaciones, :etapa, (NOW() AT TIME ZONE 'America/La_Paz'))
        RETURNING id_solicitud
    """
    params = {
        "id_evento_rida": id_evento_rida,
        "id_modalidad": id_modalidad,
        "id_municipio": geo["id_municipio"],
        "id_departamento": geo["id_departamento"],
        "id_usuario_crea": id_usuario,
        "observaciones": observaciones,
        "etapa": "ENVIADA"
    }
    result = db.execute(text(query), params).fetchone()
    db.commit()
    id_solicitud = result[0]
    # v2.60.0: el motor arranca al crear (no hay BORRADOR ni accion enviar).
    # Ayuda Humanitaria devuelve cadena vacia: su motor se inicia aparte con
    # POST /ayuda-humanitaria/expedientes/{id}/iniciar.
    cadena = asegurar_aprobaciones(db, id_solicitud, id_modalidad)
    if cadena:
        _registrar_paso(db, id_solicitud, 1,
                        f"Motor de aprobaciones iniciado ({ETIQUETA_NIVEL[cadena[0]]} pendiente)",
                        "INICIAR_APROBACION", "ENVIADA", None, id_usuario)
        db.commit()
    return id_solicitud


def listar_solicitudes(db: Session, filtros: dict, skip: int, limit: int, user_scope: dict | None = None) -> tuple[list, int]:
    conds = ["1=1"]
    params = {}
    
    if filtros.get("id_modalidad"):
        ids = filtros["id_modalidad"]
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        conds.append("s.id_modalidad = ANY(:ids_modalidad)")
        params["ids_modalidad"] = list(ids)
    if filtros.get("modalidad"):
        conds.append("EXISTS (SELECT 1 FROM rida.cat_modalidad cmf "
                     "WHERE cmf.id_modalidad = s.id_modalidad "
                     "AND (cmf.codigo ILIKE :modalidad OR cmf.nombre ILIKE :modalidad))")
        params["modalidad"] = f"%{filtros['modalidad']}%"
    if filtros.get("etapa"):
        conds.append("s.etapa = :etapa")
        params["etapa"] = filtros["etapa"]
    if filtros.get("id_departamento"):
        conds.append("s.id_departamento = :id_departamento")
        params["id_departamento"] = filtros["id_departamento"]
    if filtros.get("id_municipio"):
        conds.append("s.id_municipio = :id_municipio")
        params["id_municipio"] = filtros["id_municipio"]
    if filtros.get("id_evento_rida"):
        conds.append("s.id_evento_rida = :id_evento_rida")
        params["id_evento_rida"] = filtros["id_evento_rida"]
    if filtros.get("q"):
        conds.append("s.observaciones ILIKE :q")
        params["q"] = f"%{filtros['q']}%"
    
    if user_scope:
        if user_scope.get("id_municipio"):
            conds.append("s.id_municipio = :id_municipio_scope")
            params["id_municipio_scope"] = user_scope["id_municipio"]
        elif user_scope.get("id_departamento"):
            conds.append("s.id_departamento = :id_departamento_scope")
            params["id_departamento_scope"] = user_scope["id_departamento"]
    
    where = " AND ".join(conds)
    
    query_count = f"SELECT COUNT(*) FROM rida.solicitud s WHERE {where}"
    total = _row(db, query_count, params)["count"]
    
    query = f"""
        SELECT s.id_solicitud, s.id_evento_rida, s.id_modalidad, cm.nombre AS nombre_modalidad,
               s.etapa, s.id_municipio, m.nombre AS nombre_municipio,
               s.id_departamento, d.nombre AS nombre_departamento,
               e.codigo_edan, ce.codigo AS evento_codigo,
               s.fecha_inicio, s.observaciones, s.fecha_cierre, s.id_usuario_crea,
               (SELECT COALESCE(json_agg(json_build_object(
                           'nivel', a.nivel, 'estado', a.estado,
                           'observacion', a.observacion,
                           'por', a.por, 'fecha', a.fecha)), '[]'::json)
                FROM rida.aprobaciones_solicitud a
                WHERE a.id_solicitud = s.id_solicitud) AS aprobaciones
        FROM rida.solicitud s
        JOIN rida.cat_modalidad cm ON cm.id_modalidad = s.id_modalidad
        LEFT JOIN rida.evento_rida ev ON ev.id_evento_rida = s.id_evento_rida
        LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
        LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
        LEFT JOIN shared.municipio m ON m.id = s.id_municipio
        LEFT JOIN shared.departamento d ON d.id = s.id_departamento
        WHERE {where}
        ORDER BY s.id_solicitud DESC
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = skip
    filas = _rows(db, query, params)
    for fila in filas:
        _enriquecer_aprobaciones(fila)
    return filas, total


def obtener_solicitud(db: Session, id_solicitud: int) -> dict | None:
    query = """
        SELECT s.id_solicitud, s.id_evento_rida, s.id_modalidad, cm.nombre AS nombre_modalidad,
               s.etapa, s.id_municipio, m.nombre AS nombre_municipio,
               s.id_departamento, d.nombre AS nombre_departamento,
               e.codigo_edan, ce.codigo AS evento_codigo,
               s.fecha_inicio, s.observaciones, s.fecha_cierre, s.id_usuario_crea,
               (SELECT COALESCE(json_agg(json_build_object(
                           'nivel', a.nivel, 'estado', a.estado,
                           'observacion', a.observacion,
                           'por', a.por, 'fecha', a.fecha)), '[]'::json)
                FROM rida.aprobaciones_solicitud a
                WHERE a.id_solicitud = s.id_solicitud) AS aprobaciones
        FROM rida.solicitud s
        JOIN rida.cat_modalidad cm ON cm.id_modalidad = s.id_modalidad
        LEFT JOIN rida.evento_rida ev ON ev.id_evento_rida = s.id_evento_rida
        LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
        LEFT JOIN rida.cat_estado_evento ce ON ce.id_estado_evento = ev.id_estado
        LEFT JOIN shared.municipio m ON m.id = s.id_municipio
        LEFT JOIN shared.departamento d ON d.id = s.id_departamento
        WHERE s.id_solicitud = :id_solicitud
    """
    return _enriquecer_aprobaciones(_row(db, query, {"id_solicitud": id_solicitud}))


def actualizar_solicitud(db: Session, id_solicitud: int, data: dict) -> bool:
    set_parts = []
    params = {"id": id_solicitud}
    for k, v in data.items():
        set_parts.append(f"{k} = :{k}")
        params[k] = v
    if not set_parts:
        return False
    set_clause = ", ".join(set_parts)
    # Sin fecha_modificacion: esa columna no existe en rida.solicitud (solo en
    # rida.formulario_rida) y su presence hacia que este PUT terminara en 500.
    query = f"UPDATE rida.solicitud SET {set_clause} WHERE id_solicitud = :id"
    db.execute(text(query), params)
    db.commit()
    return True


def eliminar_solicitud(db: Session, id_solicitud: int) -> bool:
    result = _row(db, "SELECT etapa FROM rida.solicitud WHERE id_solicitud = :id", {"id": id_solicitud})
    if not result or result["etapa"] != "ENVIADA":
        return False
    # v2.60.0: la solicitud nace en ENVIADA con el motor iniciado; solo se puede
    # borrar mientras ningun nivel haya sido aprobado.
    aprobadas = _row(db, """
        SELECT COUNT(*) AS c FROM rida.aprobaciones_solicitud
        WHERE id_solicitud = :id AND estado = 'aprobado'
    """, {"id": id_solicitud})
    if aprobadas and aprobadas["c"] > 0:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: la solicitud ya tiene niveles aprobados en el motor")
    
    hijos = ["comando_incidente", "contratacion", "entrega", "proforma", "proyecto", "requerimiento_umee"]
    for tabla in hijos:
        count = _row(db, f"SELECT COUNT(*) as c FROM rida.{tabla} WHERE id_solicitud = :id", {"id": id_solicitud})
        if count and count["c"] > 0:
            raise HTTPException(status_code=400, detail=f"No se puede eliminar: la solicitud tiene {tabla} asociados")
    
    db.execute(text("DELETE FROM rida.solicitud_documento WHERE id_solicitud = :id"), {"id": id_solicitud})
    db.execute(text("DELETE FROM rida.bitacora WHERE id_solicitud = :id"), {"id": id_solicitud})
    db.execute(text("DELETE FROM rida.solicitud WHERE id_solicitud = :id"), {"id": id_solicitud})
    db.commit()
    return True


def get_checklist(db: Session, id_solicitud: int) -> list:
    query = """
        SELECT r.id_requisito, r.id_modalidad, r.orden, r.nombre_paso, 
               r.id_tipo_documento, r.instancia, r.es_documento, r.es_hito_aprobacion, r.activo,
               sd.id_solicitud_documento, sd.id_documento, sd.fecha_subida, sd.valido, sd.observaciones AS observaciones_doc
        FROM rida.cat_requisito r
        LEFT JOIN rida.solicitud_documento sd ON sd.id_requisito = r.id_requisito 
            AND sd.id_solicitud = :id_solicitud AND sd.valido = TRUE
        WHERE r.id_modalidad = (SELECT id_modalidad FROM rida.solicitud WHERE id_solicitud = :id_solicitud)
        ORDER BY r.orden
    """
    return _rows(db, query, {"id_solicitud": id_solicitud})


def subir_documento(db: Session, id_solicitud: int, id_requisito: int, id_usuario: int, 
                    path_archivo: str, tamano: int, hash_sha: str, nombre_original: str,
                    id_tipo_documento: int | None, id_municipio: int | None, id_departamento: int | None,
                    fecha_documento: date, nombre_documento: str, observaciones: str | None = None) -> int:
    solicitud = _row(db, "SELECT id_evento_rida, id_modalidad, etapa FROM rida.solicitud WHERE id_solicitud = :id", {"id": id_solicitud})
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud["etapa"] != "ENVIADA":
        raise HTTPException(status_code=400, detail="Solo se pueden subir documentos en etapa ENVIADA")
    
    evento = _row(db, "SELECT id_edan FROM rida.evento_rida WHERE id_evento_rida = :id", {"id": solicitud["id_evento_rida"]})
    id_edan = evento["id_edan"] if evento else None
    
    requisito = _row(db, "SELECT id_tipo_documento, es_documento FROM rida.cat_requisito WHERE id_requisito = :id AND id_modalidad = :id_modalidad", 
                     {"id": id_requisito, "id_modalidad": solicitud["id_modalidad"]})
    if not requisito:
        raise HTTPException(status_code=400, detail="El requisito no pertenece a la modalidad de esta solicitud")
    if not requisito.get("es_documento", False):
        raise HTTPException(status_code=400, detail="El requisito no es de tipo documento")
    
    db.execute(text("UPDATE rida.solicitud_documento SET valido = FALSE WHERE id_solicitud = :id_solicitud AND id_requisito = :id_requisito"), 
               {"id_solicitud": id_solicitud, "id_requisito": id_requisito})
    
    doc_query = """
        INSERT INTO repositorio.documentos (id_edan, id_tipo_documento, nombre_original, path_archivo, tamano_bytes, hash_sha256, 
                                           id_usuario_subio, id_municipio, fecha_documento, nombre_documento, observaciones,
                                           id_evento_rida, id_departamento, id_provincia)
        VALUES (:id_edan, :id_tipo_documento, :nombre_original, :path_archivo, :tamano_bytes, :hash_sha256, 
                :id_usuario_subio, :id_municipio, :fecha_documento, :nombre_documento, :observaciones,
                :id_evento_rida, :id_departamento, NULL)
        RETURNING id_documento
    """
    doc_params = {
        "id_edan": id_edan, "id_tipo_documento": id_tipo_documento, "nombre_original": nombre_original,
        "path_archivo": path_archivo, "tamano_bytes": tamano, "hash_sha256": hash_sha,
        "id_usuario_subio": id_usuario, "id_municipio": id_municipio, "fecha_documento": fecha_documento,
        "nombre_documento": nombre_documento, "observaciones": observaciones,
        "id_evento_rida": solicitud["id_evento_rida"], "id_departamento": id_departamento
    }
    id_documento = db.execute(text(doc_query), doc_params).fetchone()[0]
    
    sd_query = """
        INSERT INTO rida.solicitud_documento (id_solicitud, id_requisito, id_documento, id_usuario_subio, observaciones, valido, fecha_subida)
        VALUES (:id_solicitud, :id_requisito, :id_documento, :id_usuario_subio, :observaciones, TRUE, NOW())
        RETURNING id_solicitud_documento
    """
    sd_params = {"id_solicitud": id_solicitud, "id_requisito": id_requisito, "id_documento": id_documento, 
                 "id_usuario_subio": id_usuario, "observaciones": observaciones}
    id_sd = db.execute(text(sd_query), sd_params).fetchone()[0]
    db.commit()
    return id_sd


def listar_documentos(db: Session, id_solicitud: int,
                      limit: int | None = None, skip: int = 0, todos: bool = False) -> tuple[list, int]:
    """Documentos de la solicitud. Devuelve (filas, total sin paginar)."""
    total = _row(db, """
        SELECT COUNT(*) AS total
        FROM rida.solicitud_documento sd
        JOIN rida.cat_requisito r ON r.id_requisito = sd.id_requisito
        JOIN repositorio.documentos d ON d.id_documento = sd.id_documento
        WHERE sd.id_solicitud = :id_solicitud
    """, {"id_solicitud": id_solicitud})["total"]

    page, page_params = pagina_limit_offset(limit, skip, todos)
    query = f"""
        SELECT sd.id_solicitud_documento, sd.id_solicitud, sd.id_requisito, sd.id_documento,
               sd.id_usuario_subio, sd.fecha_subida, sd.valido, sd.observaciones,
               r.nombre_paso, r.instancia, r.es_documento, r.es_hito_aprobacion,
               d.nombre_original, d.path_archivo, d.tamano_bytes, d.fecha_documento, d.nombre_documento
        FROM rida.solicitud_documento sd
        JOIN rida.cat_requisito r ON r.id_requisito = sd.id_requisito
        JOIN repositorio.documentos d ON d.id_documento = sd.id_documento
        WHERE sd.id_solicitud = :id_solicitud
        ORDER BY r.orden, sd.fecha_subida DESC
        {page}
    """
    return _rows(db, query, {"id_solicitud": id_solicitud, **page_params}), total


def eliminar_documento(db: Session, id_solicitud_documento: int, path_archivo: str | None) -> bool:
    db.execute(text("DELETE FROM rida.solicitud_documento WHERE id_solicitud_documento = :id"), {"id": id_solicitud_documento})
    db.commit()
    return True


ETAPAS = [
    "ENVIADA", "EN_APROBACION", "APROBADA", "RECHAZADA", "AUTORIZADA",
    "DESPACHADA", "ENTREGADA", "CERRADA"
]

# v2.60.0: el grafo arranca en ENVIADA (no hay BORRADOR ni acciones
# enviar/revisar/observar/validar). Los niveles del motor mueven la etapa via
# ETAPA_RESULTANTE_POR_NIVEL: 'validacion' -> EN_APROBACION, 'revision_articulos'
# -> APROBADA, 'suministro' -> AUTORIZADA, 'despacho' -> DESPACHADA, 'entrega'
# -> ENTREGADA y cierre automatico a CERRADA. Las etapas retiradas
# (BORRADOR, EN_REVISION, OBSERVADA, VALIDADA) y las intermedias sin endpoint
# (EN_SUMINISTROS, DESPACHO_AUTORIZADO, EN_TRANSPORTE, RECIBIDA,
# EN_DISTRIBUCION) quedan en el catalogo (rida.cat_etapa_solicitud) como
# historicas pero fuera del grafo: ya no son alcanzables.
TRANSICIONES = {
    "ENVIADA": ["EN_APROBACION", "RECHAZADA"],
    "EN_APROBACION": ["APROBADA", "RECHAZADA"],
    "APROBADA": ["AUTORIZADA"],
    "AUTORIZADA": ["DESPACHADA"],
    "DESPACHADA": ["ENTREGADA"],
    "ENTREGADA": ["CERRADA"],
    "CERRADA": [],
    "RECHAZADA": [],
}

# Orden SEMANTICO de los 7 niveles canonicos (v2.60.0). No es la cadena de una
# solicitud: la cadena activa la resuelve resolver_cadena() desde
# rida.aprobacion_cadena y siempre es un subconjunto ordenado de esta lista
# (que debe incluir 'validacion', 'revision_articulos', 'suministro',
# 'despacho' y 'entrega': sin ellos la etapa de la solicitud no puede
# avanzar). Si no hay cadena configurada se usa esta como fallback. Secuencia
# ESTRICTA: solo se aprueba el primer nivel no aprobado.
NIVELES_APROB = ["validacion", "viceministro", "dgea", "revision_articulos",
                 "suministro", "despacho", "entrega"]

ETIQUETA_NIVEL = {
    "validacion": "Validación VIDECI Departamental",
    "viceministro": "Viceministro",
    "dgea": "Dirección General de Emergencia y Auxilio",
    "revision_articulos": "Revisión de artículos",
    "suministro": "Gestión de suministro",
    "despacho": "Despacho",
    "entrega": "Entrega",
}

# Regla 4 de APROBACIONES_RIDA.md: quien puede visar cada nivel.
# Decidido con el cliente (v2.60.0): validacion y despacho = VIDECI
# Departamental (9); viceministro y revision_articulos = Viceministro (15);
# dgea = Direccion General de Emergencia y Auxilio (16); suministro = Gestion
# de Suministro (17); entrega = UGR Municipio (6). Los roles 4 (UGR Sectores)
# y 14 (Almacen) quedan sin niveles propios. Admin (1, 2) ademas conserva
# bypass total en cualquier nivel.
ROLES_NIVEL = {
    "validacion": (9,),
    "viceministro": (15,),
    "dgea": (16,),
    "revision_articulos": (15,),
    "suministro": (17,),
    "despacho": (9,),
    "entrega": (6,),
}
ROLES_ADMIN_APROBACION = (1, 2)

# Modalidad excluida del motor de visaciones (v2.59.0): Ayuda Humanitaria
# (rida.cat_modalidad.codigo = 'AYUDA_HUMANITARIA') gestiona su propia cadena
# de 7 niveles en rida.aprobacion_cadena_ayuda (api/ayuda_humanitaria).
MODALIDAD_AYUDA_HUMANITARIA = 1

# Alcance geografico exigido por nivel. 'nacional' no restringe.
ALCANCE_NIVEL = {
    "validacion": "departamento",
    "viceministro": "nacional",
    "dgea": "nacional",
    "revision_articulos": "nacional",
    "suministro": "nacional",
    "despacho": "departamento",
    "entrega": "municipio",
}

# Badge derivado (regla 3): estado_global = badge del PRIMER nivel no aprobado
# de la cadena; con la cadena completa queda BADGE_COMPLETO.
BADGE_POR_NIVEL = {
    "validacion": "EN_VALIDACION",
    "viceministro": "VICEMINISTRO",
    "dgea": "DGEA",
    "revision_articulos": "REVISION_ARTICULOS",
    "suministro": "SUMINISTRO",
    "despacho": "DESPACHO",
    "entrega": "EN_ENTREGA",
}
BADGE_COMPLETO = "ENTREGADO"

# Acople motor <-> etapa de la solicitud (v2.60.0). ETAPA_EXIGIDA: etapa que
# debe tener la solicitud para poder actuar sobre el nivel. ETAPA_RESULTANTE:
# etapa que queda tras aprobar el nivel. El motor arranca al crear la
# solicitud: 'validacion' corre sobre ENVIADA y la pasa a EN_APROBACION;
# 'viceministro' y 'dgea' no mueven la etapa; 'revision_articulos' la lleva a
# APROBADA, 'suministro' a AUTORIZADA, 'despacho' a DESPACHADA y 'entrega' a
# ENTREGADA (y de ahi el cierre automatico a CERRADA).
ETAPA_EXIGIDA_POR_NIVEL = {
    "validacion": "ENVIADA",
    "viceministro": "EN_APROBACION",
    "dgea": "EN_APROBACION",
    "revision_articulos": "EN_APROBACION",
    "suministro": "APROBADA",
    "despacho": "AUTORIZADA",
    "entrega": "DESPACHADA",
}
ETAPA_RESULTANTE_POR_NIVEL = {
    "validacion": "EN_APROBACION",
    "viceministro": "EN_APROBACION",
    "dgea": "EN_APROBACION",
    "revision_articulos": "APROBADA",
    "suministro": "AUTORIZADA",
    "despacho": "DESPACHADA",
    "entrega": "ENTREGADA",
}
ETAPAS_MOTOR = ("ENVIADA", "EN_APROBACION", "APROBADA", "AUTORIZADA",
                "DESPACHADA", "ENTREGADA")

ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_OBSERVADO = "observado"
ESTADO_ESPERA_CORRECCION = "espera_correccion"

# Minimo de caracteres de la observacion al devolver. El frontend lo exige
# tambien (su OBS_MIN); aqui se valida en el servidor para no depender de que el
# cliente lo haga.
OBS_MIN_APROBACION = 10


def listar_etapas(db: Session) -> list:
    return _rows(db, "SELECT id_etapa, codigo, nombre, orden, activo FROM rida.cat_etapa_solicitud WHERE activo = TRUE ORDER BY orden", {})


def listar_bitacora(db: Session, id_solicitud: int,
                    limit: int | None = None, skip: int = 0, todos: bool = False) -> tuple[list, int]:
    """Bitácora de la solicitud. Devuelve (filas, total sin paginar)."""
    total = _row(db, """
        SELECT COUNT(*) AS total FROM rida.bitacora WHERE id_solicitud = :id_solicitud
    """, {"id_solicitud": id_solicitud})["total"]

    page, page_params = pagina_limit_offset(limit, skip, todos)
    query = f"""
        SELECT id_bitacora, id_solicitud, paso_orden, paso_nombre, accion, estado_resultante,
               observaciones, id_usuario, fecha
        FROM rida.bitacora
        WHERE id_solicitud = :id_solicitud
        ORDER BY paso_orden, fecha
        {page}
    """
    return _rows(db, query, {"id_solicitud": id_solicitud, **page_params}), total


def _registrar_paso(db: Session, id_solicitud: int, paso_orden: int, paso_nombre: str,
                    accion: str, estado_resultante: str, observaciones: str | None, id_usuario: int) -> None:
    query = """
        INSERT INTO rida.bitacora (id_solicitud, paso_orden, paso_nombre, accion, estado_resultante,
                                   observaciones, id_usuario, fecha)
        VALUES (:id_solicitud, :paso_orden, :paso_nombre, :accion, :estado_resultante,
                :observaciones, :id_usuario, NOW())
    """
    db.execute(text(query), {
        "id_solicitud": id_solicitud, "paso_orden": paso_orden, "paso_nombre": paso_nombre,
        "accion": accion, "estado_resultante": estado_resultante,
        "observaciones": observaciones, "id_usuario": id_usuario
    })


def _transicionar(db: Session, id_solicitud: int, nueva_etapa: str, accion: str,
                  observaciones: str | None, id_usuario: int, paso_orden: int = 1,
                  user: dict | None = None) -> dict:
    sol = obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Todas las transiciones del workflow quedan acotadas a la jurisdicción del
    # rol: sin esto un alcalde puede revisar, rechazar, autorizar y hasta cerrar
    # una solicitud de otro municipio.
    if user is not None:
        validar_scope_solicitud(db, user, id_solicitud)

    etapa_actual = sol["etapa"]
    if nueva_etapa not in TRANSICIONES.get(etapa_actual, []):
        raise HTTPException(status_code=400, detail=f"Transición inválida: {etapa_actual} → {nueva_etapa}")
    
    db.execute(text("UPDATE rida.solicitud SET etapa = :etapa WHERE id_solicitud = :id"),
               {"etapa": nueva_etapa, "id": id_solicitud})
    
    # paso_orden se pasa desde la maquina para que la bitacora ordene de verdad
    # la cadena; en el resto del workflow sigue siendo 1.
    _registrar_paso(db, id_solicitud, paso_orden, f"Transición {accion}", accion, nueva_etapa, observaciones, id_usuario)
    db.commit()
    
    return obtener_solicitud(db, id_solicitud)


def _checklist_completado(db: Session, id_solicitud: int, instancia: int) -> bool:
    query = """
        SELECT COUNT(*) as total,
               COUNT(sd.id_solicitud_documento) as completados
        FROM rida.cat_requisito r
        LEFT JOIN rida.solicitud_documento sd ON sd.id_requisito = r.id_requisito 
            AND sd.id_solicitud = :id_solicitud AND sd.valido = TRUE
        WHERE r.id_modalidad = (SELECT id_modalidad FROM rida.solicitud WHERE id_solicitud = :id_solicitud)
          AND r.instancia = :instancia AND r.es_documento = TRUE
    """
    result = _row(db, query, {"id_solicitud": id_solicitud, "instancia": instancia})
    return result is not None and result["total"] > 0 and result["completados"] >= result["total"]


def checklist_por_instancia(db: Session, id_solicitud: int) -> dict:
    return {
        1: _checklist_completado(db, id_solicitud, 1),
        2: _checklist_completado(db, id_solicitud, 2),
        3: _checklist_completado(db, id_solicitud, 3),
    }


def _informe_requisito(db: Session, id_modalidad: int) -> dict | None:
    """Requisito 'Informe de validación departamental' de la modalidad.

    v2.60.0: el nivel 1 (VIDECI Departamental) adjunta su informe en el PUT del
    visado y se registra contra este requisito (instancia 2).
    """
    return _row(db, """
        SELECT id_requisito, id_tipo_documento
        FROM rida.cat_requisito
        WHERE id_modalidad = :id_modalidad
          AND nombre_paso ILIKE 'Informe de validación%'
          AND activo
        ORDER BY id_requisito
        LIMIT 1
    """, {"id_modalidad": id_modalidad})


def _informe_presente(db: Session, id_solicitud: int, id_modalidad: int) -> bool:
    req = _informe_requisito(db, id_modalidad)
    if not req:
        return False
    fila = _row(db, """
        SELECT 1 AS ok FROM rida.solicitud_documento
        WHERE id_solicitud = :id_solicitud AND id_requisito = :id_requisito AND valido
        LIMIT 1
    """, {"id_solicitud": id_solicitud, "id_requisito": req["id_requisito"]})
    return fila is not None


def _adjuntar_informe(db: Session, id_solicitud: int, id_modalidad: int, id_usuario: int,
                      informe: dict) -> None:
    """Registra el informe de validación adjunto al visado del nivel 1.

    El archivo físico ya fue escrito por el router (save_documento_pdf); aqui se
    insertan repositorio.documentos y rida.solicitud_documento contra el
    requisito 'Informe de validación departamental' de la modalidad.
    """
    sol = _row(db, """
        SELECT id_evento_rida, id_municipio, id_departamento
        FROM rida.solicitud WHERE id_solicitud = :id
    """, {"id": id_solicitud})
    req = _informe_requisito(db, id_modalidad)
    if not req:
        raise HTTPException(
            status_code=409,
            detail="La modalidad no tiene configurado el requisito "
                   "'Informe de validación departamental'")
    evento = _row(db, "SELECT id_edan FROM rida.evento_rida WHERE id_evento_rida = :id",
                  {"id": sol["id_evento_rida"]})
    id_edan = evento["id_edan"] if evento else None

    db.execute(text("""
        UPDATE rida.solicitud_documento SET valido = FALSE
        WHERE id_solicitud = :id_solicitud AND id_requisito = :id_requisito
    """), {"id_solicitud": id_solicitud, "id_requisito": req["id_requisito"]})

    id_documento = db.execute(text("""
        INSERT INTO repositorio.documentos (id_edan, id_tipo_documento, nombre_original,
                                           path_archivo, tamano_bytes, hash_sha256,
                                           id_usuario_subio, id_municipio, fecha_documento,
                                           nombre_documento, observaciones, id_evento_rida,
                                           id_departamento, id_provincia)
        VALUES (:id_edan, :id_tipo_documento, :nombre_original, :path_archivo,
                :tamano_bytes, :hash_sha256, :id_usuario_subio, :id_municipio,
                :fecha_documento, :nombre_documento, :observaciones, :id_evento_rida,
                :id_departamento, NULL)
        RETURNING id_documento
    """), {
        "id_edan": id_edan, "id_tipo_documento": req.get("id_tipo_documento"),
        "nombre_original": informe["nombre_original"], "path_archivo": informe["path_archivo"],
        "tamano_bytes": informe["tamano"], "hash_sha256": informe["hash_sha"],
        "id_usuario_subio": id_usuario, "id_municipio": sol["id_municipio"],
        "fecha_documento": informe["fecha_documento"],
        "nombre_documento": informe["nombre_documento"],
        "observaciones": informe.get("observaciones"),
        "id_evento_rida": sol["id_evento_rida"], "id_departamento": sol["id_departamento"],
    }).fetchone()[0]

    db.execute(text("""
        INSERT INTO rida.solicitud_documento (id_solicitud, id_requisito, id_documento,
                                              id_usuario_subio, observaciones, valido, fecha_subida)
        VALUES (:id_solicitud, :id_requisito, :id_documento, :id_usuario_subio,
                :observaciones, TRUE, NOW())
    """), {"id_solicitud": id_solicitud, "id_requisito": req["id_requisito"],
           "id_documento": id_documento, "id_usuario_subio": id_usuario,
           "observaciones": informe.get("observaciones")})


def _tiene_calculo_persistido(db: Session, id_solicitud: int) -> bool:
    """TRUE si la solicitud tiene al menos una ejecucion OPERATIVA del motor."""
    fila = _row(db, """
        SELECT 1 AS ok FROM rida.ejecucion_calculo
        WHERE id_solicitud = :id_solicitud AND modo = 'operativo'
        LIMIT 1
    """, {"id_solicitud": id_solicitud})
    return fila is not None


def _modalidad_tiene_motor(db: Session, id_modalidad: int) -> bool:
    fila = _row(db, """
        SELECT tiene_motor_calculo FROM rida.cat_modalidad WHERE id_modalidad = :id
    """, {"id": id_modalidad})
    return bool(fila and fila["tiene_motor_calculo"])


def _instancia_permitida_para_etapa(etapa: str) -> list:
    # v2.60.0: la solicitud nace en ENVIADA (no hay BORRADOR/EN_REVISION/
    # OBSERVADA/VALIDADA); el checklist de instancia 1 se sube ahi.
    if etapa == "ENVIADA":
        return [1]
    if etapa == "EN_APROBACION":
        return [1, 2]
    if etapa in ["APROBADA", "AUTORIZADA"]:
        return [1, 2, 3]
    return [1, 2, 3]


def subir_documento_v2(db: Session, id_solicitud: int, id_requisito: int, id_usuario: int,
                       path_archivo: str, tamano: int, hash_sha: str, nombre_original: str,
                       id_tipo_documento: int | None, id_municipio: int | None, id_departamento: int | None,
                       fecha_documento: date, nombre_documento: str, observaciones: str | None = None) -> int:
    solicitud = _row(db, "SELECT id_evento_rida, id_modalidad, etapa FROM rida.solicitud WHERE id_solicitud = :id", {"id": id_solicitud})
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    instancias_permitidas = _instancia_permitida_para_etapa(solicitud["etapa"])
    requisito = _row(db, "SELECT id_tipo_documento, es_documento, instancia FROM rida.cat_requisito WHERE id_requisito = :id AND id_modalidad = :id_modalidad",
                     {"id": id_requisito, "id_modalidad": solicitud["id_modalidad"]})
    if not requisito:
        raise HTTPException(status_code=400, detail="El requisito no pertenece a la modalidad de esta solicitud")
    if not requisito.get("es_documento", False):
        raise HTTPException(status_code=400, detail="El requisito no es de tipo documento")
    if requisito["instancia"] not in instancias_permitidas:
        raise HTTPException(status_code=400, detail=f"El requisito es de instancia {requisito['instancia']} y no se puede subir en etapa {solicitud['etapa']}")
    
    evento = _row(db, "SELECT id_edan FROM rida.evento_rida WHERE id_evento_rida = :id", {"id": solicitud["id_evento_rida"]})
    id_edan = evento["id_edan"] if evento else None
    
    db.execute(text("UPDATE rida.solicitud_documento SET valido = FALSE WHERE id_solicitud = :id_solicitud AND id_requisito = :id_requisito"),
               {"id_solicitud": id_solicitud, "id_requisito": id_requisito})
    
    doc_query = """
        INSERT INTO repositorio.documentos (id_edan, id_tipo_documento, nombre_original, path_archivo, tamano_bytes, hash_sha256,
                                           id_usuario_subio, id_municipio, fecha_documento, nombre_documento, observaciones,
                                           id_evento_rida, id_departamento, id_provincia)
        VALUES (:id_edan, :id_tipo_documento, :nombre_original, :path_archivo, :tamano_bytes, :hash_sha256,
                :id_usuario_subio, :id_municipio, :fecha_documento, :nombre_documento, :observaciones,
                :id_evento_rida, :id_departamento, NULL)
        RETURNING id_documento
    """
    doc_params = {
        "id_edan": id_edan, "id_tipo_documento": id_tipo_documento, "nombre_original": nombre_original,
        "path_archivo": path_archivo, "tamano_bytes": tamano, "hash_sha256": hash_sha,
        "id_usuario_subio": id_usuario, "id_municipio": id_municipio, "fecha_documento": fecha_documento,
        "nombre_documento": nombre_documento, "observaciones": observaciones,
        "id_evento_rida": solicitud["id_evento_rida"], "id_departamento": id_departamento
    }
    id_documento = db.execute(text(doc_query), doc_params).fetchone()[0]
    
    sd_query = """
        INSERT INTO rida.solicitud_documento (id_solicitud, id_requisito, id_documento, id_usuario_subio, observaciones, valido, fecha_subida)
        VALUES (:id_solicitud, :id_requisito, :id_documento, :id_usuario_subio, :observaciones, TRUE, NOW())
        RETURNING id_solicitud_documento
    """
    sd_params = {"id_solicitud": id_solicitud, "id_requisito": id_requisito, "id_documento": id_documento,
                 "id_usuario_subio": id_usuario, "observaciones": observaciones}
    id_sd = db.execute(text(sd_query), sd_params).fetchone()[0]
    db.commit()
    return id_sd


# ============================================================================
#  MAQUINA DE APROBACIONES (APROBACIONES_RIDA.md, migracion v2.36.0)
#
#  Fuente de verdad: rida.aprobaciones_solicitud (una fila por nivel de la
#  cadena activa). El detalle y la bandeja derivan las aprobaciones por fila
#  con un json_agg sobre esta tabla (fase 2, v2.45.0): no hay copia en
#  rida.solicitud desde que se retiraron sus 15 columnas derivadas.
#
#  La cadena activa NO es una constante: la resuelve resolver_cadena() desde
#  rida.aprobacion_cadena y puede ser un subconjunto ordenado de los 7 niveles
#  canonicos (p.ej. 5 niveles para una modalidad).
#
#  No hay estado 'bloqueado': la cadena NO es estricta, un nivel puede aprobar
#  aunque el anterior no haya aprobado. Lo unico que exige orden es DEVOLVER
#  (regla 2), porque solo se devuelve algo que efectivamente se aprobo.
# ============================================================================

SQL_RESOLVER_CADENA = """
    SELECT c.nivel, c.orden
    FROM rida.aprobacion_cadena c
    WHERE c.activo
      AND (c.id_modalidad = :id_modalidad
           OR (c.id_modalidad IS NULL
               AND NOT EXISTS (SELECT 1 FROM rida.aprobacion_cadena c2
                                WHERE c2.activo AND c2.id_modalidad = :id_modalidad)))
    ORDER BY c.orden
"""


def resolver_cadena(db: Session, id_modalidad: int) -> list[str]:
    """Niveles que participan en la cadena de una modalidad, en orden.

    Precedencia: si la modalidad tiene filas activas, la cadena es esa; si no
    tiene ninguna, es la de id_modalidad IS NULL (la semilla de 5 niveles). El
    default NO se mezcla nivel a nivel con la modalidad: si la modalidad tiene 3
    niveles, no hereda despacho/entregado del default.

    Exclusion (v2.59.0): Ayuda Humanitaria devuelve cadena vacia — esa
    modalidad gestiona sus visaciones con su propio motor de 7 niveles
    (aprobacion_cadena_ayuda, api/ayuda_humanitaria) y este motor no debe
    crearle filas ni autorizarle aprobaciones.
    """
    if id_modalidad == MODALIDAD_AYUDA_HUMANITARIA:
        return []
    filas = _rows(db, SQL_RESOLVER_CADENA, {"id_modalidad": id_modalidad})
    if filas:
        return [f["nivel"] for f in filas]
    return list(NIVELES_APROB)


def asegurar_aprobaciones(db: Session, id_solicitud: int, id_modalidad: int) -> list[str]:
    """Crea las filas de aprobacion que falten para la cadena activa.

    Red de seguridad, no la via principal. La via principal es
    iniciar_aprobacion(), pero una solicitud puede llegar a EN_APROBACION por
    restauracion de backup, carga manual o porque la cadena se configuro despues
    de abrirla. Con ON CONFLICT DO NOTHING rellena solo lo que falta y no toca
    las filas existentes.
    """
    cadena = resolver_cadena(db, id_modalidad)
    db.execute(text("""
        INSERT INTO rida.aprobaciones_solicitud (id_solicitud, nivel, estado)
        SELECT :id_solicitud, v.nivel, 'pendiente'
        FROM unnest(CAST(:cadena AS text[])) AS v(nivel)
        ON CONFLICT (id_solicitud, nivel) DO NOTHING
    """), {"id_solicitud": id_solicitud, "cadena": cadena})
    db.commit()
    return cadena


def _get_aprobaciones(db: Session, id_solicitud: int) -> dict:
    """Filas de la maquina indexadas por nivel. Sin COMMIT: la escribe es el
    llamador, dentro de su propia transaccion."""
    filas = _rows(db, """
        SELECT nivel, estado, observacion, por, fecha
        FROM rida.aprobaciones_solicitud
        WHERE id_solicitud = :id_solicitud
    """, {"id_solicitud": id_solicitud})
    return {f["nivel"]: f for f in filas}


def _estado_nivel(niveles: dict, nivel: str) -> str:
    """Estado de un nivel; si la fila no existe se trata como pendiente."""
    return (niveles.get(nivel) or {}).get("estado") or ESTADO_PENDIENTE


def estado_global_aprobaciones(niveles: dict, cadena: list[str]) -> str | None:
    """Regla 3: estado global DERIVADO, no se almacena.

    Badge del PRIMER nivel no aprobado de la cadena (EN_VALIDACION,
    VICEMINISTRO, DGEA, REVISION_ARTICULOS, SUMINISTRO, DESPACHO, EN_ENTREGA);
    con toda la cadena aprobada, BADGE_COMPLETO (ENTREGADO). Sin cadena (Ayuda
    Humanitaria o sin configurar) devuelve None.

    Es un RESUMEN para pintar una etiqueta corta, no un turno. Con la secuencia
    estricta el primer nivel no aprobado SI determina quien puede actuar, pero
    el frontend debe usar 'puede_aprobar', que ya combina rol + alcance + etapa.
    """
    if not cadena:
        return None
    for nivel in cadena:
        if _estado_nivel(niveles, nivel) != ESTADO_APROBADO:
            return BADGE_POR_NIVEL[nivel]
    return BADGE_COMPLETO


def _primer_nivel_no_aprobado(niveles: dict, cadena: list[str]) -> str | None:
    """Primer nivel de la cadena sin estado 'aprobado' (None si esta completa).
    Con la secuencia estricta es el unico nivel que se puede aprobar."""
    for nivel in cadena:
        if _estado_nivel(niveles, nivel) != ESTADO_APROBADO:
            return nivel
    return None


def _enriquecer_aprobaciones(row: dict | None) -> dict | None:
    """Deriva el listado `aprobaciones` y `estado_global` para bandeja/detalle.

    El json_agg del SELECT trae las filas de la maquina en orden arbitrario: se
    reordena por el orden semantico de la cadena y se calcula el estado_global
    con la MISMA regla 3 que GET /{id_solicitud}/aprobacion. Sin filas (etapas
    previas a EN_APROBACION) queda lista vacia y estado_global NULL.
    """
    if not row:
        return row
    ap = row.get("aprobaciones") or []
    ap.sort(key=lambda x: NIVELES_APROB.index(x["nivel"])
            if x["nivel"] in NIVELES_APROB else len(NIVELES_APROB))
    row["aprobaciones"] = ap
    row["estado_global"] = (
        estado_global_aprobaciones({x["nivel"]: x for x in ap},
                                   [x["nivel"] for x in ap])
        if ap else None
    )
    return row


def validar_scope_solicitud(db: Session, user: dict, id_solicitud: int) -> dict:
    """Alcance geografico de la solicitud para los roles que lo tienen acotado.

    5 (DGR) y 9 (VIDECI Departamental) -> su departamento.
    8 (Alcalde) -> su municipio.
    1, 2, 3, 4 -> nacional.
    6 (UGR Municipio) y 7 (Responsable Local) -> sin filtro: no existe columna de
    propiedad en rida.solicitud (solo id_usuario_crea), asi que no hay forma de
    acotarlos por propietario. Limite conocido, documentado en
    APROBACIONES_RIDA.md.
    """
    rol = user.get("id_rol")
    if rol not in (5, 8, 9):
        return {}
    sol = _row(db, "SELECT id_municipio, id_departamento FROM rida.solicitud WHERE id_solicitud = :id",
               {"id": id_solicitud})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if rol == 8:
        if user.get("id_municipio") is None:
            raise HTTPException(status_code=403, detail="El usuario no tiene municipio asignado")
        if sol["id_municipio"] != user["id_municipio"]:
            raise HTTPException(status_code=403, detail="Solicitud fuera de su municipio")
        return {"id_municipio": sol["id_municipio"]}
    if user.get("id_departamento") is None:
        raise HTTPException(status_code=403, detail="El usuario no tiene departamento asignado")
    if sol["id_departamento"] != user["id_departamento"]:
        raise HTTPException(status_code=403, detail="Solicitud fuera de su departamento")
    return {"id_departamento": sol["id_departamento"]}


def _niveles_del_usuario(user: dict) -> set[str]:
    """Niveles de la cadena que este usuario puede visar por rol.

    Los admin (1, 2) pueden todos: asi una matriz de roles mal cargada no
    bloquea a la administracion del sistema.
    """
    if user.get("id_rol") in ROLES_ADMIN_APROBACION:
        return set(NIVELES_APROB)
    return {nivel for nivel, roles in ROLES_NIVEL.items() if user.get("id_rol") in roles}


def _alcance_cumple(nivel: str, user: dict, sol: dict) -> bool:
    alcance = ALCANCE_NIVEL[nivel]
    if alcance == "nacional":
        return True
    if alcance == "municipio":
        return user.get("id_municipio") is not None and user["id_municipio"] == sol["id_municipio"]
    if alcance == "departamento":
        return (user.get("id_departamento") is not None
                and user["id_departamento"] == sol["id_departamento"])
    return True


def validar_nivel(db: Session, user: dict, sol: dict, nivel: str, cadena: list[str]) -> None:
    """Regla 4: autorizacion = rol del nivel + alcance geografico + pertenencia
    a la cadena. En ese orden, para que el mensaje de error sea util.

    El bypass de admin es TOTAL (rol y alcance): superadmin/admin son
    nacionales y no tienen id_municipio ni id_departamento asignados, asi que
    si se les exigiera el alcance no podrian aprobar nunca. Se acepta como
    decision: una matriz de roles mal cargada no debe dejar al sistema sin
    poder aprobar solicitudes.
    """
    if nivel not in cadena:
        raise HTTPException(
            status_code=400,
            detail=f"El nivel '{nivel}' no pertenece a la cadena de esta solicitud "
                   f"(modalidad {sol['id_modalidad']}): {cadena}")
    if user.get("id_rol") in ROLES_ADMIN_APROBACION:
        return
    if nivel not in _niveles_del_usuario(user):
        roles = ROLES_NIVEL.get(nivel, ())
        raise HTTPException(
            status_code=403,
            detail=f"Rol {user.get('id_rol')} no autorizado para el nivel '{nivel}' "
                   f"(roles permitidos: {roles})")
    if not _alcance_cumple(nivel, user, sol):
        raise HTTPException(
            status_code=403,
            detail=f"El nivel '{nivel}' exige alcance {ALCANCE_NIVEL[nivel]} y la solicitud "
                   f"está fuera de su jurisdicción")


def get_aprobaciones(db: Session, id_solicitud: int, user: dict | None = None) -> dict | None:
    """GET /{id_solicitud}/aprobacion: la maquina completa + estado_global + que
    puede hacer este usuario. Auto-suficiente: incluye la cadena resuelta."""
    sol = _row(db, """
        SELECT id_solicitud, id_modalidad, etapa, id_municipio, id_departamento
        FROM rida.solicitud WHERE id_solicitud = :id
    """, {"id": id_solicitud})
    if not sol:
        return None
    if user is not None:
        validar_scope_solicitud(db, user, id_solicitud)
    # v2.60.0: el motor arranca al crear la solicitud, asi que las filas deben
    # existir desde ENVIADA. Si faltan (restauracion de backup o cadena
    # configurada despues de abrirla) se materializan aqui. Un GET nunca
    # materializa la maquina de una solicitud RECHAZADA/CERRADA.
    if sol["etapa"] in ETAPAS_MOTOR:
        cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    else:
        cadena = resolver_cadena(db, sol["id_modalidad"])
    niveles = _get_aprobaciones(db, id_solicitud)
    mis_niveles = _niveles_del_usuario(user) if user else set()

    aprobaciones = {}
    mi_nivel = None
    for i, nivel in enumerate(cadena, start=1):
        fila = niveles.get(nivel) or {}
        estado = fila.get("estado") or ESTADO_PENDIENTE
        es_mio = nivel in mis_niveles
        # Secuencia estricta (v2.60.0): solo el primer nivel no aprobado es
        # aprobable, y ademas la solicitud debe estar en la etapa que ese nivel
        # exige (ej. 'despacho' solo desde AUTORIZADA).
        puede_aprobar = (es_mio and nivel == _primer_nivel_no_aprobado(niveles, cadena)
                         and sol["etapa"] == ETAPA_EXIGIDA_POR_NIVEL[nivel])
        puede_devolver = (es_mio and i > 1
                          and _estado_nivel(niveles, cadena[i - 2]) == ESTADO_APROBADO)
        if es_mio and mi_nivel is None:
            mi_nivel = nivel
        aprobaciones[nivel] = {
            "nivel": nivel,
            "orden": i,
            "estado": estado,
            "observacion": fila.get("observacion"),
            "por": fila.get("por"),
            "fecha": fila.get("fecha"),
            "roles": list(ROLES_NIVEL.get(nivel, ())),
            "alcance": ALCANCE_NIVEL[nivel],
            "puede_aprobar": puede_aprobar,
            "puede_devolver": puede_devolver,
            "es_mio": es_mio,
        }
    return {
        "id_solicitud": sol["id_solicitud"],
        "id_modalidad": sol["id_modalidad"],
        "etapa": sol["etapa"],
        "cadena": cadena,
        "estado_global": estado_global_aprobaciones(niveles, cadena),
        "mi_nivel": mi_nivel,
        "aprobaciones": aprobaciones,
    }


def aprobar_nivel(db: Session, id_solicitud: int, nivel: str, id_usuario: int,
                  user: dict | None = None, informe: dict | None = None) -> dict:
    """Regla 1: aprobar un nivel.

    v2.60.0 — Secuencia ESTRICTA: solo se puede aprobar el primer nivel no
    aprobado de la cadena. La etapa exigida por nivel (ETAPA_EXIGIDA_POR_NIVEL)
    es ENVIADA para 'validacion' (el motor arranca al crear la solicitud),
    EN_APROBACION para 'viceministro', 'dgea' y 'revision_articulos', APROBADA
    para 'suministro', AUTORIZADA para 'despacho' y DESPACHADA para 'entrega'.

    Gates de negocio:
      * 'validacion' exige el checklist de instancia 1 completo y el informe de
        validación departamental adjunto (en este mismo PUT o ya registrado).
      * 'revision_articulos' exige un calculo OPERATIVO persistido cuando la
        modalidad tiene motor de calculo (cat_modalidad.tiene_motor_calculo).
      * 'entrega' cierra la solicitud automaticamente (ENTREGADA -> CERRADA).
    """
    if nivel not in NIVELES_APROB:
        raise HTTPException(status_code=400, detail=f"Nivel inválido: {nivel}")
    sol = _row(db, """
        SELECT id_solicitud, id_modalidad, etapa, id_municipio, id_departamento
        FROM rida.solicitud WHERE id_solicitud = :id
    """, {"id": id_solicitud})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    cadena = resolver_cadena(db, sol["id_modalidad"])
    if not cadena:
        raise HTTPException(
            status_code=409,
            detail="La modalidad Ayuda Humanitaria gestiona sus visaciones con su "
                   "propio motor de 7 niveles (flujo de Ayuda Humanitaria)")
    if sol["etapa"] != ETAPA_EXIGIDA_POR_NIVEL[nivel]:
        raise HTTPException(
            status_code=409,
            detail=f"Para aprobar '{nivel}' la solicitud debe estar en "
                   f"{ETAPA_EXIGIDA_POR_NIVEL[nivel]} (actual: {sol['etapa']})")
    cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    if user is not None:
        validar_nivel(db, user, sol, nivel, cadena)

    niveles = _get_aprobaciones(db, id_solicitud)
    pendiente = _primer_nivel_no_aprobado(niveles, cadena)
    if pendiente is None:
        raise HTTPException(
            status_code=409,
            detail="Todos los niveles de la cadena ya están aprobados")
    if nivel != pendiente:
        raise HTTPException(
            status_code=409,
            detail=f"Secuencia estricta: corresponde aprobar '{pendiente}' "
                   f"(estado {_estado_nivel(niveles, pendiente)}), no '{nivel}'")

    # Gates de negocio (v2.60.0) ------------------------------------------------
    if nivel == "validacion":
        if not _checklist_completado(db, id_solicitud, 1):
            raise HTTPException(
                status_code=409,
                detail="El nivel de validación exige el checklist de instancia 1 completo "
                       "(documentos del UGR)")
        if informe is None and not _informe_presente(db, id_solicitud, sol["id_modalidad"]):
            raise HTTPException(
                status_code=409,
                detail="El nivel de validación exige adjuntar el informe de validación "
                       "departamental (campo 'archivo' del PUT)")
    if nivel == "revision_articulos" and _modalidad_tiene_motor(db, sol["id_modalidad"]):
        if not _tiene_calculo_persistido(db, id_solicitud):
            raise HTTPException(
                status_code=409,
                detail="La modalidad exige un cálculo operativo persistido antes de "
                       "revisar los artículos (POST /api/v2/ayuda-humanitaria/calculos, "
                       "modo operativo)")

    venia_observado = _estado_nivel(niveles, nivel) == ESTADO_OBSERVADO
    orden = cadena.index(nivel)

    db.execute(text("""
        UPDATE rida.aprobaciones_solicitud
        SET estado = 'aprobado', observacion = NULL,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :nivel
    """), {"id": id_solicitud, "nivel": nivel, "por": id_usuario})

    # Al re-aprobar un nivel devuelto, el ciclo de correccion queda resuelto: el
    # nivel que habia devuelto (el siguiente de la cadena) vuelve a pendiente y
    # puede decidir de nuevo.
    if venia_observado and orden < len(cadena) - 1:
        siguiente = cadena[orden + 1]
        db.execute(text("""
            UPDATE rida.aprobaciones_solicitud
            SET estado = 'pendiente'
            WHERE id_solicitud = :id AND nivel = :siguiente
              AND estado = 'espera_correccion'
        """), {"id": id_solicitud, "siguiente": siguiente})

    # Informe de validación adjunto en este mismo visado (nivel 1).
    if informe is not None and nivel == "validacion":
        _adjuntar_informe(db, id_solicitud, sol["id_modalidad"], id_usuario, informe)

    # La maquina es la unica fuente de verdad para el badge; la etapa, en
    # cambio, avanza cuando el nivel aprobado tiene trigger (v2.60.0).
    nueva_etapa = ETAPA_RESULTANTE_POR_NIVEL[nivel]
    if nueva_etapa != sol["etapa"]:
        db.execute(text("""
            UPDATE rida.solicitud SET etapa = :etapa
            WHERE id_solicitud = :id AND etapa = :etapa_anterior
        """), {"etapa": nueva_etapa, "id": id_solicitud, "etapa_anterior": sol["etapa"]})
        _registrar_paso(db, id_solicitud, orden + 1,
                        f"Aprobación {ETIQUETA_NIVEL[nivel]}", "APROBAR",
                        nueva_etapa, None, id_usuario)
        # v2.60.0: al registrar la entrega la solicitud se cierra sola.
        if nivel == "entrega":
            db.execute(text("""
                UPDATE rida.solicitud SET etapa = 'CERRADA', fecha_cierre = NOW()
                WHERE id_solicitud = :id
            """), {"id": id_solicitud})
            _registrar_paso(db, id_solicitud, orden + 1,
                            "Cierre automático de la solicitud", "CERRAR", "CERRADA",
                            "Cadena de visaciones completa", id_usuario)
        db.commit()
    else:
        _registrar_paso(db, id_solicitud, orden + 1,
                        f"Aprobación {ETIQUETA_NIVEL[nivel]}", "APROBAR",
                        sol["etapa"], None, id_usuario)
        db.commit()
    return get_aprobaciones(db, id_solicitud, user)


def devolver_nivel(db: Session, id_solicitud: int, nivel: str, observacion: str,
                   id_usuario: int, user: dict | None = None) -> dict:
    """Regla 2: devolver al nivel ANTERIOR de la cadena.

    Aqui SI aplica el orden: solo se devuelve algo que efectivamente se aprobo.
    Si el anterior no llego a aprobar (porque se saltaron niveles) no hay nada
    que devolver -> 400.

    v2.60.0: el motor vive en todo el ciclo (ETAPAS_MOTOR, no solo
    EN_APROBACION) y, al devolver, la etapa de la solicitud retrocede a la que
    exige el nivel observado (ETAPA_EXIGIDA_POR_NIVEL[anterior]): devolver
    'viceministro'/'dgea'/'revision_articulos' vuelve a EN_APROBACION,
    'suministro' a APROBADA, 'despacho' a AUTORIZADA y 'entrega' a DESPACHADA;
    asi el nivel observado se puede re-aprobar en su etapa.
    """
    if nivel not in NIVELES_APROB:
        raise HTTPException(status_code=400, detail=f"Nivel inválido: {nivel}")
    sol = _row(db, """
        SELECT id_solicitud, id_modalidad, etapa, id_municipio, id_departamento
        FROM rida.solicitud WHERE id_solicitud = :id
    """, {"id": id_solicitud})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    cadena = resolver_cadena(db, sol["id_modalidad"])
    if not cadena:
        raise HTTPException(
            status_code=409,
            detail="La modalidad Ayuda Humanitaria gestiona sus visaciones con su "
                   "propio motor de 7 niveles (flujo de Ayuda Humanitaria)")
    if sol["etapa"] not in ETAPAS_MOTOR:
        raise HTTPException(
            status_code=409,
            detail=f"El motor de visaciones exige etapa en {list(ETAPAS_MOTOR)} "
                   f"(actual: {sol['etapa']})")
    cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    orden = cadena.index(nivel) if nivel in cadena else -1
    if orden <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede devolver desde el primer nivel de la cadena ('{nivel}'): "
                   f"no existe un nivel anterior")
    if user is not None:
        validar_nivel(db, user, sol, nivel, cadena)
    if len(observacion) < OBS_MIN_APROBACION:
        raise HTTPException(
            status_code=422,
            detail=f"La observación es obligatoria y debe tener al menos "
                   f"{OBS_MIN_APROBACION} caracteres (actual: {len(observacion)})")

    anterior = cadena[orden - 1]
    niveles = _get_aprobaciones(db, id_solicitud)
    if _estado_nivel(niveles, anterior) != ESTADO_APROBADO:
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede devolver a '{anterior}' si está aprobado "
                   f"(estado actual: {_estado_nivel(niveles, anterior)})")
    # Secuencia estricta tambien al devolver: solo puede devolver quien tiene
    # el turno (el primer nivel no aprobado). Con la cadena completa ya no hay
    # turno y la maquina queda cerrada.
    pendiente = _primer_nivel_no_aprobado(niveles, cadena)
    if pendiente is None or nivel != pendiente:
        raise HTTPException(
            status_code=409,
            detail=f"Secuencia estricta: solo puede devolver quien tiene el turno "
                   f"('{pendiente or 'cadena completa'}'), no '{nivel}'")

    # El nivel devuelto guarda el motivo; el que devuelve espera la correccion.
    db.execute(text("""
        UPDATE rida.aprobaciones_solicitud
        SET estado = 'observado', observacion = :obs,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :anterior
    """), {"id": id_solicitud, "anterior": anterior, "obs": observacion, "por": id_usuario})
    db.execute(text("""
        UPDATE rida.aprobaciones_solicitud
        SET estado = 'espera_correccion', observacion = NULL,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :nivel
    """), {"id": id_solicitud, "nivel": nivel, "por": id_usuario})

    # Reversa de etapa: el nivel observado se re-aprueba en la etapa que le
    # corresponde (ver ETAPA_EXIGIDA_POR_NIVEL).
    etapa_revertida = ETAPA_EXIGIDA_POR_NIVEL[anterior]
    if sol["etapa"] != etapa_revertida:
        db.execute(text("UPDATE rida.solicitud SET etapa = :etapa WHERE id_solicitud = :id"),
                   {"etapa": etapa_revertida, "id": id_solicitud})

    _registrar_paso(db, id_solicitud, orden, f"Devolución de {nivel} a {anterior}", "DEVOLVER",
                    etapa_revertida, observacion, id_usuario)
    db.commit()
    return get_aprobaciones(db, id_solicitud, user)


def listar_cadenas_aprobacion(db: Session) -> dict:
    """GET /rida/solicitudes/cat-cadena-aprobacion: el catalogo de configuracion.

    El frontend lo consume UNA vez y lo cachea: el listado de solicitudes no
    hace un GET de la maquina por fila (cada fila tiene su propia cadena segun su
    modalidad), asi que sin esto no podria dibujar la bandeja.
    """
    default = [f["nivel"] for f in _rows(db, """
        SELECT nivel FROM rida.aprobacion_cadena
        WHERE activo AND id_modalidad IS NULL ORDER BY orden
    """, {})]
    if not default:
        # Sin default sembrado la resolucion no es determinista. Se cae al
        # catalogo canonico en vez de devolver una cadena vacia que el frontend
        # interpretaria como "esta solicitud no tiene niveles".
        default = list(NIVELES_APROB)
    por_modalidad = {}
    for f in _rows(db, """
        SELECT id_modalidad, nivel FROM rida.aprobacion_cadena
        WHERE activo AND id_modalidad IS NOT NULL ORDER BY id_modalidad, orden
    """, {}):
        por_modalidad.setdefault(str(f["id_modalidad"]), []).append(f["nivel"])
    # Solo las modalidades cuya cadena difiere del default.
    por_modalidad = {k: v for k, v in por_modalidad.items() if v != default}
    roles_meta = {}
    for f in _rows(db, "SELECT id_rol, nombre FROM usuarios.rol WHERE id_rol = ANY(:ids)",
                   {"ids": list({r for roles in ROLES_NIVEL.values() for r in roles}) or [0]}):
        roles_meta[f["id_rol"]] = f["nombre"]
    return {
        "niveles": [
            {
                "codigo": nivel,
                "label": ETIQUETA_NIVEL[nivel],
                "roles": list(ROLES_NIVEL[nivel]),
                "alcance": ALCANCE_NIVEL[nivel],
                "orden": i,
                "nom_roles": [roles_meta.get(r, f"Rol {r}") for r in ROLES_NIVEL[nivel]],
            }
            for i, nivel in enumerate(NIVELES_APROB, start=1)
        ],
        "default": default,
        "por_modalidad": por_modalidad,
    }


def reemplazar_cadena_modalidad(db: Session, id_modalidad: int, niveles: list[str]) -> dict:
    """PUT /rida/solicitudes/cat-cadena-aprobacion/{id_modalidad}: reemplaza la
    cadena de una modalidad.

    Se rechaza (409) si hay solicitudes con el motor activo en esa modalidad
    (EN_APROBACION..ENTREGADA): cambiarla en caliente dejaria esas solicitudes
    con filas de una cadena que ya no existe.

    v2.60.0: Ayuda Humanitaria no se configura aqui (409). Y la cadena debe
    incluir 'validacion', 'revision_articulos', 'suministro', 'despacho' y
    'entrega': son los niveles con trigger de etapa y sin ellos la solicitud no
    puede avanzar.
    """
    if not _row(db, "SELECT 1 AS ok FROM rida.cat_modalidad WHERE id_modalidad = :id",
                {"id": id_modalidad}):
        raise HTTPException(status_code=404, detail="Modalidad no encontrada")
    if id_modalidad == MODALIDAD_AYUDA_HUMANITARIA:
        raise HTTPException(
            status_code=409,
            detail="La modalidad Ayuda Humanitaria usa su propia cadena de 7 niveles "
                   "(rida.aprobacion_cadena_ayuda) y no se configura aqui")
    if not niveles:
        raise HTTPException(status_code=400, detail="La cadena debe tener al menos un nivel")
    seen = set()
    for nivel in niveles:
        if nivel not in NIVELES_APROB:
            raise HTTPException(
                status_code=400,
                detail=f"Nivel inválido: '{nivel}'. Solo se admiten {NIVELES_APROB}")
        if nivel in seen:
            raise HTTPException(status_code=400, detail=f"Nivel repetido: '{nivel}'")
        seen.add(nivel)
    esperado = [n for n in NIVELES_APROB if n in seen]
    if niveles != esperado:
        raise HTTPException(
            status_code=400,
            detail=f"El orden debe respetar el orden semántico de la cadena. "
                   f"Esperado: {esperado}, recibido: {niveles}")
    for requerido in ("validacion", "revision_articulos", "suministro", "despacho", "entrega"):
        if requerido not in niveles:
            raise HTTPException(
                status_code=400,
                detail=f"La cadena debe incluir el nivel '{requerido}': es un nivel con "
                       f"trigger de etapa y sin él la solicitud no puede avanzar")

    # Literal fijo: ETAPAS_MOTOR es constante del modulo y con text() un
    # tuple no se expande en un IN.
    abiertas = _row(db, """
        SELECT COUNT(*) AS c FROM rida.solicitud
        WHERE id_modalidad = :id AND etapa IN
              ('ENVIADA', 'EN_APROBACION', 'APROBADA', 'AUTORIZADA', 'DESPACHADA', 'ENTREGADA')
    """, {"id": id_modalidad})
    if abiertas and abiertas["c"] > 0:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede cambiar la cadena: hay {abiertas['c']} solicitud(es) de esta "
                   f"modalidad con el motor activo")

    db.execute(text("DELETE FROM rida.aprobacion_cadena WHERE id_modalidad = :id"),
               {"id": id_modalidad})
    db.execute(text("""
        INSERT INTO rida.aprobacion_cadena (id_modalidad, nivel, orden, activo)
        SELECT :id, v.nivel, v.orden, TRUE
        FROM unnest(CAST(:niveles AS text[])) WITH ORDINALITY AS v(nivel, orden)
    """), {"id": id_modalidad, "niveles": niveles})
    db.commit()
    return listar_cadenas_aprobacion(db)


def rechazar_solicitud(db: Session, id_solicitud: int, id_usuario: int, observaciones: str | None = None,
                       user: dict | None = None) -> dict:
    if user is not None:
        validar_scope_solicitud(db, user, id_solicitud)
    sol = obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if sol["etapa"] not in ["ENVIADA", "EN_APROBACION"]:
        raise HTTPException(status_code=400, detail=f"La solicitud debe estar ENVIADA o EN_APROBACION (actual: {sol['etapa']})")
    
    db.execute(text("UPDATE rida.solicitud SET etapa = 'RECHAZADA' WHERE id_solicitud = :id"), {"id": id_solicitud})
    _registrar_paso(db, id_solicitud, 1, "Rechazo de solicitud", "RECHAZAR", "RECHAZADA", observaciones, id_usuario)
    db.commit()
    return obtener_solicitud(db, id_solicitud)
