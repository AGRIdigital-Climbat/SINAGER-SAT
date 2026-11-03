"""Servicio de Ayuda Humanitaria: Work Queue VIDECI (pasos 4-9).

Espeja el motor de visaciones de api/rida/solicitudes/service.py (mismos
estados por nivel, misma regla de devolucion) con DOS diferencias de diseño
(AYUDA_HUMANITARIA_BACKEND.md v1.2):

1. La cadena es SECUENCIAL: no se puede aprobar un nivel sin que el anterior
   este aprobado (en el motor de visaciones se puede saltar niveles).
2. El badge NO se almacena: se deriva en cada lectura (regla 3). La cabecera
   `solicitud.etapa` solo se toca en 3 anclas: EN_APROBACION (iniciar),
   RECHAZADA y CERRADA (cadena completa).

El expediente ES la `solicitud` (sin columnas nuevas): el evento, municipio y
departamento se resuelven por `solicitud.id_evento_rida -> evento_rida -> edan`.
"""

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import motor, motor_necesidades

# ============================================================================
#  Helpers SQL (mismo patron que el resto de la API)
# ============================================================================

def _row(db: Session, query: str, params: dict) -> dict | None:
    result = db.execute(text(query), params).fetchone()
    return dict(result._mapping) if result else None


def _rows(db: Session, query: str, params: dict) -> list:
    result = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in result]


# ============================================================================
#  Constantes del motor (regla 4: roles + alcance por nivel)
# ============================================================================

NIVELES_AYUDA = ["evaluacion", "determinacion", "autorizacion",
                 "almacen", "despacho", "entrega", "cierre"]

ETIQUETA_NIVEL = {
    "evaluacion": "Evaluación Nacional",
    "determinacion": "Determinación de artículos",
    "autorizacion": "Autorización",
    "almacen": "Almacén",
    "despacho": "Despacho",
    "entrega": "Entrega / acta de recepción",
    "cierre": "Cierre",
}

ROLES_NIVEL = {
    "evaluacion": (3, 9),
    "determinacion": (3, 9),
    "autorizacion": (3, 9),
    "almacen": (3, 9),
    "despacho": (3, 9),
    "entrega": (3, 9),
    "cierre": (3, 9),
}

ALCANCE_NIVEL = {
    "evaluacion": "nacional",
    "determinacion": "nacional",
    "autorizacion": "nacional",
    "almacen": "departamento",
    "despacho": "departamento",
    "entrega": "departamento",
    "cierre": "nacional",
}

# Regla 3: badge que deriva el primer nivel NO aprobado de la cadena.
# 'cierre' pendiente (todo lo demas aprobado) sigue mostrando ENTREGADA:
# el badge CERRADA solo aparece con la cadena completa.
BADGE_POR_NIVEL = {
    "evaluacion": "EN_APROBACION",
    "determinacion": "APROBADA",
    "autorizacion": "AUTORIZADA",
    "almacen": "EN_PREPARACION",
    "despacho": "DESPACHADA",
    "entrega": "ENTREGADA",
    "cierre": "ENTREGADA",
}

ROLES_ADMIN = (1, 2)
OBS_MIN = 10

# Etapas visibles en el Work Queue: desde ENVIADA (v2.60.0: la solicitud nace
# ahi, sin BORRADOR ni acciones revisar/validar; candidata al paso 4) hasta
# CERRADA/RECHAZADA.
ETAPAS_COLA = (
    "ENVIADA", "EN_APROBACION", "APROBADA", "AUTORIZADA", "EN_SUMINISTROS",
    "DESPACHO_AUTORIZADO", "DESPACHADA", "EN_TRANSPORTE", "RECIBIDA",
    "EN_DISTRIBUCION", "ENTREGADA", "CERRADA", "RECHAZADA",
)


# ============================================================================
#  Catalogos
# ============================================================================

def listar_estados(db: Session) -> list:
    return _rows(db, """
        SELECT id_estado_rida, codigo, nombre, tono, orden, activo
        FROM rida.cat_estado_rida
        WHERE activo
        ORDER BY orden
    """, {})


def badge_de(db: Session, codigo: str | None) -> dict | None:
    if not codigo:
        return None
    return _row(db, """
        SELECT id_estado_rida, codigo, nombre, tono
        FROM rida.cat_estado_rida
        WHERE codigo = :c AND activo
    """, {"c": codigo})


def listar_cadena(db: Session) -> dict:
    """GET /aprobacion/cadena: niveles, roles, alcance y cadenas por modalidad."""
    default = [f["nivel"] for f in _rows(db, """
        SELECT nivel FROM rida.aprobacion_cadena_ayuda
        WHERE activo AND id_modalidad IS NULL
        ORDER BY orden
    """, {})]
    if not default:
        default = list(NIVELES_AYUDA)
    por_modalidad: dict = {}
    for f in _rows(db, """
        SELECT id_modalidad, nivel FROM rida.aprobacion_cadena_ayuda
        WHERE activo AND id_modalidad IS NOT NULL
        ORDER BY id_modalidad, orden
    """, {}):
        por_modalidad.setdefault(str(f["id_modalidad"]), []).append(f["nivel"])
    por_modalidad = {k: v for k, v in por_modalidad.items() if v != default}
    ids_roles = sorted({r for roles in ROLES_NIVEL.values() for r in roles}) or [0]
    roles_meta = {f["id_rol"]: f["nombre"] for f in _rows(
        db, "SELECT id_rol, nombre FROM usuarios.rol WHERE id_rol = ANY(:ids)",
        {"ids": ids_roles})}
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
            for i, nivel in enumerate(NIVELES_AYUDA, start=1)
        ],
        "default": default,
        "por_modalidad": por_modalidad,
    }


# ============================================================================
#  Motor de aprobaciones: cadena, filas y estado derivado
# ============================================================================

def resolver_cadena(db: Session, id_modalidad: int) -> list[str]:
    filas = _rows(db, """
        SELECT nivel FROM rida.aprobacion_cadena_ayuda
        WHERE activo AND (id_modalidad = :id_modalidad
            OR (id_modalidad IS NULL AND NOT EXISTS (
                SELECT 1 FROM rida.aprobacion_cadena_ayuda c2
                WHERE c2.activo AND c2.id_modalidad = :id_modalidad)))
        ORDER BY orden
    """, {"id_modalidad": id_modalidad})
    return [f["nivel"] for f in filas] or list(NIVELES_AYUDA)


def asegurar_aprobaciones(db: Session, id_solicitud: int, id_modalidad: int) -> list[str]:
    """Crea las filas pendiente que falten (ON CONFLICT DO NOTHING)."""
    cadena = resolver_cadena(db, id_modalidad)
    db.execute(text("""
        INSERT INTO rida.aprobaciones_ayuda_humanitaria (id_solicitud, nivel, estado)
        SELECT :id_solicitud, v.nivel, 'pendiente'
        FROM unnest(CAST(:cadena AS text[])) AS v(nivel)
        ON CONFLICT (id_solicitud, nivel) DO NOTHING
    """), {"id_solicitud": id_solicitud, "cadena": cadena})
    return cadena


def _get_niveles(db: Session, id_solicitud: int) -> dict:
    filas = _rows(db, """
        SELECT nivel, estado, observacion, por, fecha
        FROM rida.aprobaciones_ayuda_humanitaria
        WHERE id_solicitud = :id_solicitud
    """, {"id_solicitud": id_solicitud})
    return {f["nivel"]: f for f in filas}


def _estado_nivel(niveles: dict, nivel: str) -> str:
    return (niveles.get(nivel) or {}).get("estado") or "pendiente"


def estado_global(niveles: dict, cadena: list[str], etapa: str | None = None) -> str:
    """Regla 3: badge DERIVADO, nunca almacenado."""
    for nivel in cadena:
        if _estado_nivel(niveles, nivel) == "observado":
            return "OBSERVADA"
    if etapa == "RECHAZADA":
        return "RECHAZADA"
    for nivel in cadena:
        if _estado_nivel(niveles, nivel) != "aprobado":
            return BADGE_POR_NIVEL[nivel]
    return "CERRADA"


def get_aprobaciones(db: Session, id_solicitud: int, user: dict | None = None) -> dict | None:
    """Maquina completa: cadena + badge derivado + que puede hacer el token."""
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if sol["etapa"] == "EN_APROBACION":
        cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    else:
        cadena = resolver_cadena(db, sol["id_modalidad"])
    niveles = _get_niveles(db, id_solicitud)
    mis_niveles = _niveles_del_usuario(user) if user else set()

    aprobaciones: dict = {}
    mi_nivel = None
    for i, nivel in enumerate(cadena, start=1):
        fila = niveles.get(nivel) or {}
        estado = fila.get("estado") or "pendiente"
        es_mio = nivel in mis_niveles
        # Cadena SECUENCIAL: solo es accionable si todo lo anterior esta aprobado.
        previos_ok = all(_estado_nivel(niveles, n) == "aprobado" for n in cadena[:i - 1])
        puede_aprobar = es_mio and estado != "aprobado" and (i == 1 or previos_ok)
        puede_devolver = (es_mio and i > 1
                          and _estado_nivel(niveles, cadena[i - 2]) == "aprobado")
        if es_mio and mi_nivel is None and estado != "aprobado":
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
    badge = estado_global(niveles, cadena, sol["etapa"])
    return {
        "id_solicitud": sol["id_solicitud"],
        "id_modalidad": sol["id_modalidad"],
        "etapa": sol["etapa"],
        "cadena": cadena,
        "estado_global": badge,
        "badge": badge_de(db, badge),
        "mi_nivel": mi_nivel,
        "niveles": aprobaciones,
        "aprobaciones": [aprobaciones[n] for n in cadena],
    }


# ============================================================================
#  Regla 4: autorizacion (rol + alcance) y scope geografico
# ============================================================================

def _niveles_del_usuario(user: dict) -> set[str]:
    """Los admin (1, 2) pueden todos: bypass total, igual que en visaciones."""
    if user.get("id_rol") in ROLES_ADMIN:
        return set(NIVELES_AYUDA)
    return {n for n, roles in ROLES_NIVEL.items() if user.get("id_rol") in roles}


def _alcance_cumple(nivel: str, user: dict, sol: dict) -> bool:
    if ALCANCE_NIVEL[nivel] == "nacional":
        return True
    return (user.get("id_departamento") is not None
            and user["id_departamento"] == sol["id_departamento"])


def validar_nivel(db: Session, user: dict, sol: dict, nivel: str, cadena: list[str]) -> None:
    if nivel not in cadena:
        raise HTTPException(
            status_code=400,
            detail=f"El nivel '{nivel}' no pertenece a la cadena de esta solicitud "
                   f"(modalidad {sol['id_modalidad']}): {cadena}")
    if user.get("id_rol") in ROLES_ADMIN:
        return
    if nivel not in _niveles_del_usuario(user):
        raise HTTPException(
            status_code=403,
            detail=f"Rol {user.get('id_rol')} no autorizado para el nivel '{nivel}' "
                   f"(roles permitidos: {ROLES_NIVEL.get(nivel, ())})")
    if not _alcance_cumple(nivel, user, sol):
        raise HTTPException(
            status_code=403,
            detail=f"El nivel '{nivel}' exige alcance {ALCANCE_NIVEL[nivel]} y el "
                   f"expediente está fuera de su jurisdicción")


def validar_scope(db: Session, user: dict, id_solicitud: int) -> dict:
    """5 (DGR), 9 (VIDECI Dep.) y 14 (Almacen) -> su departamento.
    8 (Alcalde) -> su municipio. Resto: nacional."""
    rol = user.get("id_rol")
    if rol not in (5, 8, 9, 14):
        return {}
    sol = _row(db, """
        SELECT id_municipio, id_departamento FROM rida.solicitud
        WHERE id_solicitud = :id
    """, {"id": id_solicitud})
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


# ============================================================================
#  Bitacora
# ============================================================================

def _registrar_paso(db: Session, id_solicitud: int, paso_orden: int, paso_nombre: str,
                    accion: str, estado_resultante: str, observaciones: str | None,
                    id_usuario: int) -> None:
    db.execute(text("""
        INSERT INTO rida.bitacora
            (id_solicitud, paso_orden, paso_nombre, accion, estado_resultante, observaciones, id_usuario)
        VALUES (:id, :orden, :nombre, :accion, :estado, :obs, :usr)
    """), {"id": id_solicitud, "orden": paso_orden, "nombre": paso_nombre,
           "accion": accion, "estado": estado_resultante, "obs": observaciones,
           "usr": id_usuario})


# ============================================================================
#  Expedientes: listado (Work Queue) y detalle
# ============================================================================

SQL_EXPEDIENTE_BASE = """
    SELECT s.id_solicitud, s.id_evento_rida, s.etapa,
           ev.codigo AS codigo_rida,
           s.id_modalidad, mo.nombre AS nombre_modalidad,
           COALESCE(s.id_municipio, e.id_municipio) AS id_municipio,
           m.nombre AS nombre_municipio,
           COALESCE(s.id_departamento, e.id_departamento) AS id_departamento,
           d.nombre AS nombre_departamento,
           te.nombre AS tipo_evento,
           s.fecha_inicio AS fecha_solicitud
    FROM rida.solicitud s
    JOIN rida.evento_rida ev ON ev.id_evento_rida = s.id_evento_rida
    JOIN rida.cat_modalidad mo ON mo.id_modalidad = s.id_modalidad
    LEFT JOIN edan.edan e ON e.id_edan = ev.id_edan
    LEFT JOIN shared.municipio m ON m.id = COALESCE(s.id_municipio, e.id_municipio)
    LEFT JOIN shared.departamento d ON d.id = COALESCE(s.id_departamento, e.id_departamento)
    LEFT JOIN edan.tipo_evento te ON te.id_tipo_evento = e.id_tipo_evento
"""


def _sol_or_404(db: Session, id_solicitud: int) -> dict:
    sol = _row(db, """
        SELECT id_solicitud, id_evento_rida, id_modalidad, etapa,
               id_municipio, id_departamento
        FROM rida.solicitud WHERE id_solicitud = :id
    """, {"id": id_solicitud})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return sol


def _derivados(db: Session, sol: dict) -> dict:
    """Badge (regla 3), dias_en_estado, asignado, tiene_motor. TODO derivado."""
    cadena = resolver_cadena(db, sol["id_modalidad"])
    niveles = _get_niveles(db, sol["id_solicitud"])
    badge = estado_global(niveles, cadena, sol.get("etapa"))

    # Nivel accionable = primer nivel no aprobado (cadena secuencial).
    accionable = None
    for n in cadena:
        fila = niveles.get(n) or {}
        if (fila.get("estado") or "pendiente") != "aprobado":
            accionable = fila
            break
    fecha_ref = (accionable or {}).get("fecha")
    if fecha_ref is None and niveles:
        fechas = [f["fecha"] for f in niveles.values() if f.get("fecha")]
        fecha_ref = max(fechas) if fechas else None
    dias = (datetime.now() - fecha_ref).days if fecha_ref else None

    id_asignado = (accionable or {}).get("por")
    nombre = None
    if id_asignado:
        u = _row(db, "SELECT nombre FROM usuarios.usuario WHERE id_usuario = :id",
                 {"id": id_asignado})
        nombre = u["nombre"] if u else None

    tiene = _row(db, """
        SELECT 1 AS ok FROM rida.solicitud_articulo
        WHERE id_solicitud = :id LIMIT 1
    """, {"id": sol["id_solicitud"]})

    return {
        "estado": badge_de(db, badge),
        "badge": badge,
        "dias_en_estado": dias,
        "id_usuario_asignado": id_asignado,
        "nombre_tecnico": nombre,
        "tiene_motor": bool(tiene),
        "motor_iniciado": bool(niveles),
    }


def listar_expedientes(db: Session, filtros: dict, skip: int, limit: int,
                       todos: bool, user_scope: dict) -> tuple[list, int]:
    """Work Queue: los mas recientes primero. El filtro `estado` es derivado
    (regla 3), asi que se aplica en Python tras calcular el badge: los
    volumenes de la cola son pequenos y `todos` cubre lotes/KPIs."""
    conds = ["s.etapa = ANY(CAST(:etapas AS text[]))"]
    params: dict = {"etapas": list(ETAPAS_COLA)}
    if user_scope.get("id_municipio"):
        conds.append("COALESCE(s.id_municipio, e.id_municipio) = :scope_municipio")
        params["scope_municipio"] = user_scope["id_municipio"]
    elif user_scope.get("id_departamento"):
        conds.append("COALESCE(s.id_departamento, e.id_departamento) = :scope_departamento")
        params["scope_departamento"] = user_scope["id_departamento"]
    if filtros.get("id_modalidad"):
        conds.append("s.id_modalidad = :id_modalidad")
        params["id_modalidad"] = filtros["id_modalidad"]
    if filtros.get("id_departamento"):
        conds.append("COALESCE(s.id_departamento, e.id_departamento) = :id_departamento")
        params["id_departamento"] = filtros["id_departamento"]
    if filtros.get("id_municipio"):
        conds.append("COALESCE(s.id_municipio, e.id_municipio) = :id_municipio")
        params["id_municipio"] = filtros["id_municipio"]
    if filtros.get("tipo_evento"):
        conds.append("te.nombre ILIKE :tipo_evento")
        params["tipo_evento"] = f"%{filtros['tipo_evento']}%"
    if filtros.get("fecha_desde"):
        conds.append("s.fecha_inicio >= CAST(:fecha_desde AS timestamp)")
        params["fecha_desde"] = filtros["fecha_desde"]
    if filtros.get("fecha_hasta"):
        conds.append("s.fecha_inicio < CAST(:fecha_hasta AS timestamp) + INTERVAL '1 day'")
        params["fecha_hasta"] = filtros["fecha_hasta"]
    if filtros.get("q"):
        conds.append("(ev.codigo ILIKE :q OR m.nombre ILIKE :q)")
        params["q"] = f"%{filtros['q']}%"

    rows = _rows(db, SQL_EXPEDIENTE_BASE + " WHERE " + " AND ".join(conds) + """
        ORDER BY s.fecha_inicio DESC, s.id_solicitud DESC
    """, params)

    estado_filtro = filtros.get("estado")
    items = []
    for r in rows:
        deriv = _derivados(db, r)
        if estado_filtro and deriv["badge"] != estado_filtro:
            continue
        items.append({**r, **deriv})
    total = len(items)
    if not todos:
        items = items[skip:skip + limit]
    return items, total


def listar_articulos(db: Session, id_solicitud: int) -> list:
    return _rows(db, """
        SELECT sa.id_solicitud_articulo, sa.id_solicitud, sa.id_articulo,
               a.nombre AS articulo, a.codigo AS codigo_articulo,
               sa.id_regla, r.nombre_regla,
               sa.cantidad, sa.unidad, sa.aprobado, sa.fuente, sa.observaciones, sa.fecha
        FROM rida.solicitud_articulo sa
        JOIN rida.cat_articulo a ON a.id_articulo = sa.id_articulo
        LEFT JOIN rida.regla_calculo_kit r ON r.id_regla = sa.id_regla
        WHERE sa.id_solicitud = :id
        ORDER BY a.nombre
    """, {"id": id_solicitud})


def _orden_actual(db: Session, id_solicitud: int) -> dict | None:
    return _row(db, """
        SELECT id_entrega, id_almacen, nro_orden, estado_despacho, responsable,
               transporte, placa, fecha_salida, fecha_entrega, firmas,
               id_documento, observaciones_acta, observaciones
        FROM rida.entrega
        WHERE id_solicitud = :id AND tipo = 'AYUDA_HUMANITARIA'
              AND nro_orden IS NOT NULL
        ORDER BY id_entrega DESC
        LIMIT 1
    """, {"id": id_solicitud})


def get_orden_despacho(db: Session, id_solicitud: int) -> dict | None:
    orden = _orden_actual(db, id_solicitud)
    if not orden:
        return None
    orden["detalle"] = _rows(db, """
        SELECT ed.id_detalle, ed.id_articulo, a.nombre AS articulo,
               a.codigo AS codigo_articulo, ed.cantidad, ed.peso_kg, ed.valor_bs
        FROM rida.entrega_detalle ed
        JOIN rida.cat_articulo a ON a.id_articulo = ed.id_articulo
        WHERE ed.id_entrega = :id
        ORDER BY ed.id_detalle
    """, {"id": orden["id_entrega"]})
    return orden


def get_expediente(db: Session, id_solicitud: int, user: dict | None = None) -> dict | None:
    sol = _row(db, SQL_EXPEDIENTE_BASE + " WHERE s.id_solicitud = :id",
               {"id": id_solicitud})
    if not sol:
        return None
    if user is not None:
        validar_scope(db, user, id_solicitud)
    data = {**sol, **_derivados(db, sol)}
    data["aprobacion"] = get_aprobaciones(db, id_solicitud, user)

    ev = _row(db, """
        SELECT id_solicitud_evaluacion, id_usuario_tecnico, observaciones, fecha
        FROM rida.solicitud_evaluacion
        WHERE id_solicitud = :id
        ORDER BY fecha DESC, id_solicitud_evaluacion DESC
        LIMIT 1
    """, {"id": id_solicitud})
    if ev and ev["id_usuario_tecnico"]:
        u = _row(db, "SELECT nombre FROM usuarios.usuario WHERE id_usuario = :id",
                 {"id": ev["id_usuario_tecnico"]})
        ev["nombre_tecnico"] = u["nombre"] if u else None
    data["evaluacion"] = ev

    data["articulos"] = listar_articulos(db, id_solicitud)
    orden = get_orden_despacho(db, id_solicitud)
    data["orden_despacho"] = orden
    data["acta_recepcion"] = (
        {
            "id_entrega": orden["id_entrega"],
            "nro_orden": orden["nro_orden"],
            "firmas": orden["firmas"],
            "id_documento": orden["id_documento"],
            "observaciones": orden["observaciones_acta"],
        }
        if orden else None
    )

    # Documentos del expediente (repositorio del evento RIDA): SOLO LECTURA.
    from ..repositorio import service as repo_service
    docs, _total = repo_service.list_documentos_by_evento_rida(
        db, sol["id_evento_rida"], todos=True)
    data["documentos"] = docs
    return data


# ============================================================================
#  Regla 0: iniciar el motor
# ============================================================================

def _checklist_instancia1_completo(db: Session, id_solicitud: int) -> bool:
    """Checklist de instancia 1 completo (documentos del UGR).

    v2.60.0: reemplaza el gate que tenia la accion 'validar' (eliminada): el
    motor de Ayuda Humanitaria arranca desde ENVIADA y exige que el UGR haya
    cargado todos sus documentos.
    """
    fila = _row(db, """
        SELECT COUNT(*) AS total,
               COUNT(sd.id_solicitud_documento) AS completados
        FROM rida.cat_requisito r
        LEFT JOIN rida.solicitud_documento sd
          ON sd.id_requisito = r.id_requisito
         AND sd.id_solicitud = :id_solicitud AND sd.valido = TRUE
        WHERE r.id_modalidad = (SELECT id_modalidad FROM rida.solicitud
                                WHERE id_solicitud = :id_solicitud)
          AND r.instancia = 1 AND r.es_documento = TRUE
    """, {"id_solicitud": id_solicitud})
    return bool(fila and fila["total"] > 0 and fila["completados"] >= fila["total"])


def iniciar_motor(db: Session, id_solicitud: int, id_usuario: int,
                  user: dict | None = None, observaciones: str | None = None) -> dict:
    if user is not None:
        validar_scope(db, user, id_solicitud)
    sol = _sol_or_404(db, id_solicitud)
    if sol["etapa"] == "EN_APROBACION":
        # Ya iniciado: idempotente, solo asegura las filas de la cadena activa.
        asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
        db.commit()
        return get_aprobaciones(db, id_solicitud, user)
    if sol["etapa"] != "ENVIADA":
        raise HTTPException(
            status_code=409,
            detail=f"Solo se puede iniciar el motor desde ENVIADA (actual: {sol['etapa']})")
    if not _checklist_instancia1_completo(db, id_solicitud):
        raise HTTPException(
            status_code=409,
            detail="El inicio del motor exige el checklist de instancia 1 completo "
                   "(documentos del UGR)")
    db.execute(text("""
        UPDATE rida.solicitud SET etapa = 'EN_APROBACION' WHERE id_solicitud = :id
    """), {"id": id_solicitud})
    asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    _registrar_paso(db, id_solicitud, 1, "Inicio del motor de ayuda humanitaria (paso 4)",
                    "INICIAR_AYUDA", "EN_APROBACION", observaciones, id_usuario)
    db.commit()
    return get_aprobaciones(db, id_solicitud, user)


# ============================================================================
#  Reglas 1 y 2: aprobar / devolver (cadena SECUENCIAL)
# ============================================================================

def aprobar_nivel(db: Session, id_solicitud: int, nivel: str, id_usuario: int,
                  user: dict | None = None) -> dict:
    if nivel not in NIVELES_AYUDA:
        raise HTTPException(status_code=400, detail=f"Nivel inválido: {nivel}")
    sol = _sol_or_404(db, id_solicitud)
    if sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El motor debe estar iniciado (etapa EN_APROBACION, actual: {sol['etapa']})")
    cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    if user is not None:
        validar_nivel(db, user, sol, nivel, cadena)

    niveles = _get_niveles(db, id_solicitud)
    orden = cadena.index(nivel)
    # Regla 1.3: SECUENCIAL - el nivel anterior debe estar aprobado.
    if orden > 0:
        anterior = cadena[orden - 1]
        if _estado_nivel(niveles, anterior) != "aprobado":
            raise HTTPException(
                status_code=409,
                detail=f"Cadena secuencial: '{anterior}' debe estar aprobado antes "
                       f"de aprobar '{nivel}'")
    venia_observado = _estado_nivel(niveles, nivel) == "observado"

    db.execute(text("""
        UPDATE rida.aprobaciones_ayuda_humanitaria
        SET estado = 'aprobado', observacion = NULL,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :nivel
    """), {"id": id_solicitud, "nivel": nivel, "por": id_usuario})

    # Regla 1.5: al re-aprobar un nivel devuelto, el que habia devuelto
    # (siguiente en la cadena) vuelve a pendiente y puede decidir de nuevo.
    if venia_observado and orden < len(cadena) - 1:
        siguiente = cadena[orden + 1]
        db.execute(text("""
            UPDATE rida.aprobaciones_ayuda_humanitaria
            SET estado = 'pendiente'
            WHERE id_solicitud = :id AND nivel = :siguiente
              AND estado = 'espera_correccion'
        """), {"id": id_solicitud, "siguiente": siguiente})

    db.commit()
    resultado = get_aprobaciones(db, id_solicitud, user)

    # Regla 1.6: cadena completa -> CERRADA (ancla de etapa).
    if resultado["estado_global"] == "CERRADA" and sol["etapa"] != "CERRADA":
        db.execute(text("""
            UPDATE rida.solicitud SET etapa = 'CERRADA', fecha_cierre = NOW()
            WHERE id_solicitud = :id
        """), {"id": id_solicitud})
        _registrar_paso(db, id_solicitud, orden + 1, "Ayuda humanitaria completada",
                        "CERRAR", "CERRADA", "Todos los niveles del motor aprobados",
                        id_usuario)
        db.commit()
        resultado = get_aprobaciones(db, id_solicitud, user)
    else:
        _registrar_paso(db, id_solicitud, orden + 1,
                        f"Aprobación {ETIQUETA_NIVEL[nivel]}", "APROBAR",
                        "EN_APROBACION", None, id_usuario)
        db.commit()
    return resultado


def devolver_nivel(db: Session, id_solicitud: int, nivel: str, observacion: str,
                   id_usuario: int, user: dict | None = None) -> dict:
    if nivel not in NIVELES_AYUDA:
        raise HTTPException(status_code=400, detail=f"Nivel inválido: {nivel}")
    sol = _sol_or_404(db, id_solicitud)
    if sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El motor debe estar iniciado (etapa EN_APROBACION, actual: {sol['etapa']})")
    cadena = asegurar_aprobaciones(db, id_solicitud, sol["id_modalidad"])
    orden = cadena.index(nivel)
    if orden <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede devolver desde el primer nivel de la cadena ('{nivel}')")
    if user is not None:
        validar_nivel(db, user, sol, nivel, cadena)
    if not observacion or len(observacion) < OBS_MIN:
        raise HTTPException(
            status_code=422,
            detail=f"La observación es obligatoria y debe tener al menos "
                   f"{OBS_MIN} caracteres (actual: {len(observacion or '')})")
    anterior = cadena[orden - 1]
    niveles = _get_niveles(db, id_solicitud)
    if _estado_nivel(niveles, anterior) != "aprobado":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede devolver a '{anterior}' si está aprobado "
                   f"(estado actual: {_estado_nivel(niveles, anterior)})")

    # Regla 2: el nivel devuelto guarda el motivo; el que devuelve espera.
    db.execute(text("""
        UPDATE rida.aprobaciones_ayuda_humanitaria
        SET estado = 'observado', observacion = :obs,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :anterior
    """), {"id": id_solicitud, "anterior": anterior, "obs": observacion, "por": id_usuario})
    db.execute(text("""
        UPDATE rida.aprobaciones_ayuda_humanitaria
        SET estado = 'espera_correccion', observacion = NULL,
            por = :por, fecha = CURRENT_TIMESTAMP
        WHERE id_solicitud = :id AND nivel = :nivel
    """), {"id": id_solicitud, "nivel": nivel, "por": id_usuario})

    _registrar_paso(db, id_solicitud, orden, f"Devolución de {ETIQUETA_NIVEL[nivel]} a "
                    f"{ETIQUETA_NIVEL[anterior]}", "DEVOLVER", "EN_APROBACION",
                    observacion, id_usuario)
    db.commit()
    return get_aprobaciones(db, id_solicitud, user)


# ============================================================================
#  Acciones de paso (§5.4): cada una ejecuta su logica Y el aprobar(nivel)
# ============================================================================

def guardar_evaluacion(db: Session, id_solicitud: int, id_usuario: int, body,
                       user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El motor debe estar iniciado (etapa EN_APROBACION, actual: {sol['etapa']})")
    db.execute(text("""
        INSERT INTO rida.solicitud_evaluacion (id_solicitud, id_usuario_tecnico, observaciones)
        VALUES (:id, :tec, :obs)
    """), {"id": id_solicitud, "tec": body.id_usuario_tecnico or id_usuario,
           "obs": body.observaciones})
    db.commit()
    return aprobar_nivel(db, id_solicitud, "evaluacion", id_usuario, user)


def _persistir_agregados(db: Session, id_solicitud: int, agregados: list,
                         forzar: bool) -> int:
    """Upsert de los totales por articulo en solicitud_articulo (fuente='motor').

    Las filas fuente='manual' NO se tocan salvo forzar=True.
    Devuelve cuantas filas se escribieron.
    """
    existentes = {a["id_articulo"]: a for a in listar_articulos(db, id_solicitud)}
    escritas = 0
    for calc in agregados:
        ex = existentes.get(calc["id_articulo"])
        if ex and ex["fuente"] == "manual" and not forzar:
            continue  # el ajuste manual manda sobre el motor
        if ex:
            db.execute(text("""
                UPDATE rida.solicitud_articulo
                SET cantidad = :cant, unidad = :uni, id_regla = :reg,
                    fecha = CURRENT_TIMESTAMP
                WHERE id_solicitud = :id AND id_articulo = :art
            """), {"cant": calc["cantidad"], "uni": calc["unidad"],
                   "reg": calc["id_regla"], "id": id_solicitud,
                   "art": calc["id_articulo"]})
        else:
            db.execute(text("""
                INSERT INTO rida.solicitud_articulo
                    (id_solicitud, id_articulo, id_regla, cantidad, unidad, fuente)
                VALUES (:id, :art, :reg, :cant, :uni, 'motor')
            """), {"id": id_solicitud, "art": calc["id_articulo"],
                   "reg": calc["id_regla"], "cant": calc["cantidad"],
                   "uni": calc["unidad"]})
        escritas += 1
    return escritas


def _ultima_version(db: Session, id_regla: int) -> dict | None:
    return _row(db, """
        SELECT id_version, numero_version, configuracion_json
        FROM rida.regla_calculo_version
        WHERE id_regla = :id ORDER BY numero_version DESC LIMIT 1
    """, {"id": id_regla})


def _registrar_ejecucion(db: Session, id_solicitud: int, id_usuario: int | None,
                         por_familia: list, version_map: dict) -> str:
    """Historial de una ejecucion OPERATIVA: cabecera + detalle por familia."""
    id_calculo = db.execute(text("""
        INSERT INTO rida.ejecucion_calculo (id_solicitud, modo, estado, id_usuario)
        VALUES (:sol, 'operativo', 'completado', :usr)
        RETURNING id_calculo
    """), {"sol": id_solicitud, "usr": id_usuario}).scalar()
    for f in por_familia:
        id_version = version_map.get(f["id_regla"])
        if id_version is None:
            raise HTTPException(
                status_code=409,
                detail=f"La regla {f['id_regla']} está publicada sin versión "
                       f"registrada; publíquela de nuevo")
        db.execute(text("""
            INSERT INTO rida.ejecucion_calculo_detalle
                (id_calculo, id_familia, id_regla, id_version, id_articulo,
                 cantidad_calculada, unidad_medida)
            VALUES (:calc, :fam, :reg, :ver, :art, :cant, :uni)
        """), {"calc": id_calculo, "fam": f["id_familia"], "reg": f["id_regla"],
               "ver": id_version, "art": f["id_articulo"],
               "cant": f["cantidad"], "uni": f["unidad"]})
    return str(id_calculo)


def ejecutar_motor_calculo(db: Session, id_solicitud: int, user: dict | None,
                           forzar: bool = False, persistir: bool = True) -> dict:
    """Motor de calculo por KITS (§2.6). persistir=False = preview.

    Cada kit devuelve UNA fila por detalle (calculados); al persistir las
    cantidades se SUMAN por articulo (un mismo articulo en 2 kits se suma)
    y el id_regla guardado es el del kit con mayor prioridad. v2.58.0: una
    ejecucion persistida queda en el historial (ejecucion_calculo + detalle
    por familia); el preview no deja rastro.
    """
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if persistir and sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El motor debe estar iniciado (etapa EN_APROBACION, actual: {sol['etapa']})")
    calculados, por_familia = motor.ejecutar_kits_completo(
        db, sol["id_evento_rida"], con_desglose=True)
    agregados = motor.agrupar_calculados(calculados)
    if persistir:
        _persistir_agregados(db, id_solicitud, agregados, forzar)
        version_map = {}
        for rid in {c["id_regla"] for c in calculados}:
            v = _ultima_version(db, rid)
            if v:
                version_map[rid] = v["id_version"]
        _registrar_ejecucion(
            db, id_solicitud, user["id_usuario"] if user else None,
            por_familia, version_map)
        db.commit()
    return {
        "id_solicitud": id_solicitud,
        "persistido": persistir,
        "calculados": calculados,
        "articulos": listar_articulos(db, id_solicitud) if persistir else agregados,
    }


def actualizar_articulo(db: Session, id_solicitud: int, id_articulo: int, body,
                        user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    art = _row(db, """
        SELECT id_articulo, unidad_de_medida FROM rida.cat_articulo
        WHERE id_articulo = :id
    """, {"id": id_articulo})
    if not art:
        raise HTTPException(status_code=404, detail=f"Artículo {id_articulo} no encontrado")
    ex = _row(db, """
        SELECT id_solicitud_articulo FROM rida.solicitud_articulo
        WHERE id_solicitud = :id AND id_articulo = :art
    """, {"id": id_solicitud, "art": id_articulo})
    if ex:
        sets, params = ["fuente = 'manual'", "fecha = CURRENT_TIMESTAMP"], \
                       {"id": id_solicitud, "art": id_articulo}
        if body.cantidad is not None:
            sets.append("cantidad = :cant")
            params["cant"] = body.cantidad
        if body.aprobado is not None:
            sets.append("aprobado = :aprob")
            params["aprob"] = body.aprobado
        if body.observaciones is not None:
            sets.append("observaciones = :obs")
            params["obs"] = body.observaciones
        db.execute(text(
            f"UPDATE rida.solicitud_articulo SET {', '.join(sets)} "
            f"WHERE id_solicitud = :id AND id_articulo = :art"), params)
    else:
        db.execute(text("""
            INSERT INTO rida.solicitud_articulo
                (id_solicitud, id_articulo, cantidad, unidad, aprobado, fuente, observaciones)
            VALUES (:id, :art, :cant, :uni, COALESCE(:aprob, FALSE), 'manual', :obs)
        """), {"id": id_solicitud, "art": id_articulo, "cant": body.cantidad or 0,
               "uni": art["unidad_de_medida"], "aprob": body.aprobado,
               "obs": body.observaciones})
    db.commit()
    return next((a for a in listar_articulos(db, id_solicitud)
                 if a["id_articulo"] == id_articulo), None)


def autorizar_ayuda(db: Session, id_solicitud: int, id_usuario: int,
                    user: dict | None = None) -> dict:
    return aprobar_nivel(db, id_solicitud, "autorizacion", id_usuario, user)


def rechazar_ayuda(db: Session, id_solicitud: int, id_usuario: int,
                   user: dict | None = None, observaciones: str | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if sol["etapa"] not in ("ENVIADA", "EN_APROBACION"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede rechazar desde ENVIADA o EN_APROBACION "
                   f"(actual: {sol['etapa']})")
    db.execute(text("""
        UPDATE rida.solicitud SET etapa = 'RECHAZADA' WHERE id_solicitud = :id
    """), {"id": id_solicitud})
    _registrar_paso(db, id_solicitud, 1, "Rechazo del expediente", "RECHAZAR",
                    "RECHAZADA", observaciones, id_usuario)
    db.commit()
    return {
        "id_solicitud": id_solicitud,
        "etapa": "RECHAZADA",
        "badge": badge_de(db, "RECHAZADA"),
        "aprobacion": get_aprobaciones(db, id_solicitud, user),
    }


def generar_orden_despacho(db: Session, id_solicitud: int, id_usuario: int, body,
                           user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El motor debe estar iniciado (etapa EN_APROBACION, actual: {sol['etapa']})")
    if _orden_actual(db, id_solicitud):
        raise HTTPException(status_code=409, detail="El expediente ya tiene una orden de despacho")
    anio = datetime.now().year
    fila = _row(db, """
        SELECT COALESCE(MAX(CAST(RIGHT(nro_orden, 4) AS INT)), 0) + 1 AS siguiente
        FROM rida.entrega WHERE nro_orden LIKE :prefijo
    """, {"prefijo": f"OD-{anio}-%"})
    nro = f"OD-{anio}-{(fila['siguiente'] or 1):04d}"
    if body.id_almacen is not None:
        if not _row(db, "SELECT 1 AS ok FROM rida.cat_almacen WHERE id_almacen = :id",
                    {"id": body.id_almacen}):
            raise HTTPException(status_code=404, detail=f"Almacén {body.id_almacen} no encontrado")
    db.execute(text("""
        INSERT INTO rida.entrega
            (id_solicitud, id_almacen, tipo, nro_orden, estado_despacho, estado, observaciones)
        VALUES (:id, :alm, 'AYUDA_HUMANITARIA', :nro, 'GENERADA', 'AUTORIZADA', :obs)
    """), {"id": id_solicitud, "alm": body.id_almacen, "nro": nro, "obs": body.observaciones})
    if body.serie:
        for item in body.serie:
            db.execute(text("""
                INSERT INTO rida.entrega_detalle (id_entrega, id_articulo, cantidad)
                SELECT e.id_entrega, :art, :cant FROM rida.entrega e
                WHERE e.nro_orden = :nro
            """), {"art": item.id_articulo, "cant": item.cantidad, "nro": nro})
    resultado = aprobar_nivel(db, id_solicitud, "almacen", id_usuario, user)
    return {"orden": get_orden_despacho(db, id_solicitud), "aprobacion": resultado}


def preparar_orden(db: Session, id_solicitud: int, body, user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    orden = _orden_actual(db, id_solicitud)
    if not orden:
        raise HTTPException(status_code=404, detail="El expediente no tiene orden de despacho")
    objetivo = body.estado or "PREPARADA"
    if objetivo not in ("EN_PREPARACION", "PREPARADA"):
        raise HTTPException(status_code=400, detail="estado debe ser EN_PREPARACION o PREPARADA")
    transiciones = {
        "GENERADA": ("EN_PREPARACION", "PREPARADA"),
        "EN_PREPARACION": ("EN_PREPARACION", "PREPARADA"),
        "PREPARADA": ("PREPARADA",),
        "DESPACHADA": (),
    }
    if objetivo not in transiciones.get(orden["estado_despacho"] or "GENERADA", ()):
        raise HTTPException(
            status_code=409,
            detail=f"No se puede pasar de {orden['estado_despacho']} a {objetivo}")
    db.execute(text("""
        UPDATE rida.entrega SET estado_despacho = :e WHERE id_entrega = :id_entrega
    """), {"e": objetivo, "id_entrega": orden["id_entrega"]})
    db.commit()
    return get_orden_despacho(db, id_solicitud)


def despachar_orden(db: Session, id_solicitud: int, id_usuario: int, body,
                    user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    orden = _orden_actual(db, id_solicitud)
    if not orden:
        raise HTTPException(status_code=404, detail="El expediente no tiene orden de despacho")
    db.execute(text("""
        UPDATE rida.entrega
        SET estado_despacho = 'DESPACHADA',
            fecha_salida = COALESCE(fecha_salida, NOW()),
            transporte = COALESCE(:trans, transporte),
            placa = COALESCE(:placa, placa),
            observaciones = COALESCE(:obs, observaciones)
        WHERE id_entrega = :id_entrega
    """), {"trans": body.transporte, "placa": body.placa, "obs": body.observaciones,
           "id_entrega": orden["id_entrega"]})
    db.commit()
    resultado = aprobar_nivel(db, id_solicitud, "despacho", id_usuario, user)
    return {"orden": get_orden_despacho(db, id_solicitud), "aprobacion": resultado}


def registrar_acta(db: Session, id_solicitud: int, id_usuario: int, body,
                   user: dict | None = None) -> dict:
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    orden = _orden_actual(db, id_solicitud)
    if not orden:
        raise HTTPException(status_code=404, detail="El expediente no tiene orden de despacho")
    if body.id_documento is not None:
        if not _row(db, "SELECT 1 AS ok FROM repositorio.documentos WHERE id_documento = :id",
                    {"id": body.id_documento}):
            raise HTTPException(
                status_code=404,
                detail=f"Documento {body.id_documento} no encontrado en el repositorio")
    db.execute(text("""
        UPDATE rida.entrega
        SET firmas = CAST(:firmas AS jsonb),
            id_documento = :doc,
            observaciones_acta = COALESCE(:obs, observaciones_acta),
            fecha_entrega = COALESCE(fecha_entrega, NOW())
        WHERE id_entrega = :id_entrega
    """), {"firmas": json.dumps([f.model_dump() for f in (body.firmas or [])]),
           "doc": body.id_documento, "obs": body.observaciones,
           "id_entrega": orden["id_entrega"]})
    db.commit()
    resultado = aprobar_nivel(db, id_solicitud, "entrega", id_usuario, user)
    return {
        "acta": {
            "id_entrega": orden["id_entrega"],
            "nro_orden": orden["nro_orden"],
            "firmas": body.firmas or [],
            "id_documento": body.id_documento,
            "observaciones": body.observaciones,
        },
        "aprobacion": resultado,
    }


def cerrar_ayuda(db: Session, id_solicitud: int, id_usuario: int,
                 user: dict | None = None, observaciones: str | None = None) -> dict:
    resultado = aprobar_nivel(db, id_solicitud, "cierre", id_usuario, user)
    if observaciones:
        _registrar_paso(db, id_solicitud, 7, "Cierre del expediente", "CERRAR",
                        "CERRADA", observaciones, id_usuario)
        db.commit()
    return resultado


# ============================================================================
#  CRUD de reglas del motor por KITS (§2.6)
# ============================================================================

_SQL_REGLA_BASE = """
    SELECT k.id_regla, k.nombre_regla, k.criterio_aplicacion,
           k.rango_edad_min_dias, k.rango_edad_max_dias, k.requiere_gestante,
           k.requiere_discapacidad, k.sexo, k.dias_duracion, k.redondeo,
           k.prioridad, k.activo, k.orden, k.estado, k.fecha_creacion,
           k.fecha_modificacion,
           COALESCE((SELECT MAX(v.numero_version)
                     FROM rida.regla_calculo_version v
                     WHERE v.id_regla = k.id_regla), 0) AS version_actual
    FROM rida.regla_calculo_kit k
"""

_COLUMNAS_REGLA = (
    "nombre_regla", "criterio_aplicacion", "rango_edad_min_dias",
    "rango_edad_max_dias", "requiere_gestante", "requiere_discapacidad", "sexo",
    "dias_duracion", "redondeo", "prioridad", "activo", "orden",
)


def _detalles_de_regla(db: Session, id_regla: int) -> list:
    return _rows(db, """
        SELECT d.id_detalle_regla, d.id_articulo, d.cantidad_base_diaria,
               d.cantidad_min, d.cantidad_max, a.nombre AS articulo,
               a.unidad_de_medida AS unidad
        FROM rida.detalle_parametro_kit d
        JOIN rida.cat_articulo a ON a.id_articulo = d.id_articulo
        WHERE d.id_regla = :id
        ORDER BY d.id_detalle_regla
    """, {"id": id_regla})


def _regla_response(db: Session, id_regla: int) -> dict | None:
    regla = _row(db, _SQL_REGLA_BASE + " WHERE k.id_regla = :id", {"id": id_regla})
    if not regla:
        return None
    regla["detalles"] = _detalles_de_regla(db, id_regla)
    return regla


def listar_reglas(db: Session, id_articulo: int | None = None,
                  criterio_aplicacion: str | None = None,
                  solo_activas: bool = False,
                  estado: str | None = None) -> list:
    conds, params = ["1 = 1"], {}
    if id_articulo:
        conds.append("EXISTS (SELECT 1 FROM rida.detalle_parametro_kit d "
                     "WHERE d.id_regla = k.id_regla AND d.id_articulo = :art)")
        params["art"] = id_articulo
    if criterio_aplicacion:
        conds.append("k.criterio_aplicacion = :crit")
        params["crit"] = criterio_aplicacion
    if solo_activas:
        conds.append("k.activo")
    if estado:
        conds.append("k.estado = :estado")
        params["estado"] = estado
    filas = _rows(db, f"{_SQL_REGLA_BASE} WHERE {' AND '.join(conds)} "
                      "ORDER BY k.orden, k.prioridad, k.id_regla", params)
    for f in filas:
        f["detalles"] = _detalles_de_regla(db, f["id_regla"])
    return filas


def _validar_detalles(db: Session, detalles) -> None:
    if not detalles:
        raise HTTPException(status_code=422, detail="El kit debe tener al menos un artículo")
    vistos = set()
    for i, d in enumerate(detalles):
        if not _row(db, "SELECT 1 AS ok FROM rida.cat_articulo WHERE id_articulo = :id",
                    {"id": d.id_articulo}):
            raise HTTPException(status_code=409,
                                detail=f"detalles[{i}]: artículo {d.id_articulo} no existe")
        if d.id_articulo in vistos:
            raise HTTPException(status_code=409,
                                detail=f"detalles[{i}]: artículo {d.id_articulo} repetido en el kit")
        vistos.add(d.id_articulo)
        if d.cantidad_max is not None and d.cantidad_min is not None \
                and d.cantidad_max < d.cantidad_min:
            raise HTTPException(
                status_code=400,
                detail=f"detalles[{i}]: cantidad_max no puede ser menor que cantidad_min")


def _validar_regla(db: Session, body) -> None:
    _validar_detalles(db, body.detalles)
    for err in motor.validar_criterio(body.model_dump()):
        raise HTTPException(status_code=422, detail=err)


def crear_regla(db: Session, body) -> dict:
    _validar_regla(db, body)
    try:
        rid = db.execute(text("""
            INSERT INTO rida.regla_calculo_kit
                (nombre_regla, criterio_aplicacion, rango_edad_min_dias,
                 rango_edad_max_dias, requiere_gestante, requiere_discapacidad,
                 sexo, dias_duracion, redondeo, prioridad, activo, orden, estado)
            VALUES (:nombre, :criterio, :emin, :emax, :gestante, :disc, :sexo,
                    :dias, :redondeo, :prioridad, :activo, :orden, 'borrador')
            RETURNING id_regla
        """), {"nombre": body.nombre_regla, "criterio": body.criterio_aplicacion,
               "emin": body.rango_edad_min_dias, "emax": body.rango_edad_max_dias,
               "gestante": body.requiere_gestante, "disc": body.requiere_discapacidad,
               "sexo": body.sexo, "dias": body.dias_duracion,
               "redondeo": body.redondeo, "prioridad": body.prioridad,
               "activo": body.activo, "orden": body.orden}).scalar()
        for d in body.detalles:
            db.execute(text("""
                INSERT INTO rida.detalle_parametro_kit
                    (id_regla, id_articulo, cantidad_base_diaria, cantidad_min, cantidad_max)
                VALUES (:reg, :art, :base, :mini, :maxi)
            """), {"reg": rid, "art": d.id_articulo, "base": d.cantidad_base_diaria,
                   "mini": d.cantidad_min, "maxi": d.cantidad_max})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se pudo crear la regla kit")
    return _regla_response(db, rid)


def actualizar_regla(db: Session, id_regla: int, body) -> dict:
    actual = _regla_response(db, id_regla)
    if not actual:
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    cambios = body.model_dump(exclude_unset=True)
    detalles = body.detalles
    cambios.pop("detalles", None)
    if not cambios and detalles is None:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    fusion = {k: actual[k] for k in ("criterio_aplicacion", "rango_edad_min_dias",
                                     "rango_edad_max_dias", "requiere_gestante",
                                     "requiere_discapacidad", "sexo")}
    fusion.update({k: v for k, v in cambios.items() if k in fusion})
    for err in motor.validar_criterio(fusion):
        raise HTTPException(status_code=422, detail=err)
    if detalles is not None:
        _validar_detalles(db, detalles)
    columnas = {k: v for k, v in cambios.items() if k in _COLUMNAS_REGLA}
    if columnas or detalles is not None:
        # v2.58.0: editar una regla PUBLICADA la devuelve a 'borrador' — la
        # configuración publicada es inmutable (versiones); hay que volver a
        # publicar para que el motor vuelva a usarla.
        if actual["estado"] == "publicada":
            columnas = dict(columnas)
            columnas["estado"] = "borrador"
        if columnas:
            sets, params = [], {"id": id_regla}
            for campo, valor in columnas.items():
                sets.append(f"{campo} = :{campo}")
                params[campo] = valor
            sets.append("fecha_modificacion = CURRENT_TIMESTAMP")
            db.execute(text(
                f"UPDATE rida.regla_calculo_kit SET {', '.join(sets)} WHERE id_regla = :id"),
                params)
        if detalles is not None:
            db.execute(text("DELETE FROM rida.detalle_parametro_kit WHERE id_regla = :id"),
                       {"id": id_regla})
            for d in detalles:
                db.execute(text("""
                    INSERT INTO rida.detalle_parametro_kit
                        (id_regla, id_articulo, cantidad_base_diaria, cantidad_min, cantidad_max)
                    VALUES (:reg, :art, :base, :mini, :maxi)
                """), {"reg": id_regla, "art": d.id_articulo, "base": d.cantidad_base_diaria,
                       "mini": d.cantidad_min, "maxi": d.cantidad_max})
        db.commit()
    return _regla_response(db, id_regla)


def eliminar_regla(db: Session, id_regla: int) -> None:
    if not _regla_response(db, id_regla):
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    ref = _row(db, """
        SELECT COUNT(*) AS c FROM rida.solicitud_articulo WHERE id_regla = :id
    """, {"id": id_regla})
    if ref["c"] > 0:
        raise HTTPException(
            status_code=409,
            detail=f"La regla tiene {ref['c']} artículo(s) generados; "
                   f"desactívela (activo=false) en lugar de eliminarla")
    hist = _row(db, """
        SELECT COUNT(*) AS c FROM rida.ejecucion_calculo_detalle WHERE id_regla = :id
    """, {"id": id_regla})
    if hist["c"] > 0:
        raise HTTPException(
            status_code=409,
            detail=f"La regla aparece en {hist['c']} detalle(s) de ejecuciones "
                   f"del motor; desactívela (activo=false) en lugar de eliminarla")
    db.execute(text("DELETE FROM rida.regla_calculo_kit WHERE id_regla = :id"), {"id": id_regla})
    db.commit()


# ============================================================================
#  Ciclo de vida de reglas (v2.58.0): validar / simular / publicar / versiones
# ============================================================================

def get_regla(db: Session, id_regla: int) -> dict:
    regla = _regla_response(db, id_regla)
    if not regla:
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    return regla


def _validar_estructura_regla(db: Session, regla: dict) -> dict:
    """Estructura + parámetros de una regla (contrato /validar).

    Devuelve {valida, errores, advertencias, resumen}; NO lanza excepciones.
    """
    errores: list[str] = []
    advertencias: list[str] = []

    if not (regla.get("nombre_regla") or "").strip():
        errores.append("nombre_regla es obligatorio")
    if not regla["detalles"]:
        errores.append("El kit debe tener al menos un artículo")

    vistos: set[int] = set()
    for i, d in enumerate(regla["detalles"]):
        art = _row(db, """
            SELECT nombre, activo FROM rida.cat_articulo WHERE id_articulo = :id
        """, {"id": d["id_articulo"]})
        if not art:
            errores.append(f"detalles[{i}]: artículo {d['id_articulo']} no existe en el catálogo")
            continue
        if not art["activo"]:
            errores.append(f"detalles[{i}]: artículo {d['id_articulo']} "
                           f"({art['nombre']}) no está habilitado")
        if d["id_articulo"] in vistos:
            errores.append(f"detalles[{i}]: artículo {d['id_articulo']} repetido en el kit")
        vistos.add(d["id_articulo"])
        if (d.get("cantidad_max") is not None and d.get("cantidad_min") is not None
                and float(d["cantidad_max"]) < float(d["cantidad_min"])):
            errores.append(f"detalles[{i}]: cantidad_max no puede ser menor que cantidad_min")
        if float(d["cantidad_base_diaria"]) <= 0:
            errores.append(f"detalles[{i}]: cantidad_base_diaria debe ser mayor que cero")

    for err in motor.validar_criterio(regla):
        errores.append(err)

    if regla.get("dias_duracion") is None:
        advertencias.append("sin dias_duracion: la cantidad se calcula POR DÍA")
    if all(d.get("cantidad_min") is None and d.get("cantidad_max") is None
           for d in regla["detalles"]):
        advertencias.append("sin acotaciones cantidad_min/cantidad_max en los artículos")
    if regla.get("estado") == "publicada":
        advertencias.append("la regla ya está publicada: editarla la devolverá a borrador")

    resumen = {
        "id_regla": regla.get("id_regla"),
        "nombre_regla": regla.get("nombre_regla"),
        "criterio_aplicacion": regla.get("criterio_aplicacion"),
        "estado": regla.get("estado"),
        "version_actual": regla.get("version_actual"),
        "dias_duracion": regla.get("dias_duracion"),
        "redondeo": regla.get("redondeo"),
        "articulos": [d["articulo"] for d in regla["detalles"]],
    }
    return {"valida": not errores, "errores": errores,
            "advertencias": advertencias, "resumen": resumen}


def validar_regla(db: Session, id_regla: int) -> dict:
    regla = _regla_response(db, id_regla)
    if not regla:
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    resultado = _validar_estructura_regla(db, regla)
    if not resultado["valida"]:
        raise HTTPException(status_code=422, detail=resultado)
    return resultado


def simular_regla(db: Session, id_regla: int, body) -> dict:
    """Fórmula unitaria de la regla SIN persistir (población sintética).

    cantidad = clamp(redondeo(cantidad_base × dias × poblacion), min, max)
    por artículo; nada toca la base de datos.
    """
    regla = _regla_response(db, id_regla)
    if not regla:
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    poblacion = body.poblacion if (body and body.poblacion) else 1
    dias = (body.dias_duracion if (body and body.dias_duracion is not None)
            else regla["dias_duracion"]) or 1
    if body and body.detalles:
        entradas = []
        for d in body.detalles:
            art = _row(db, """
                SELECT nombre, unidad_de_medida FROM rida.cat_articulo
                WHERE id_articulo = :id
            """, {"id": d.id_articulo})
            if not art:
                raise HTTPException(status_code=404,
                                    detail=f"Artículo {d.id_articulo} no existe")
            entradas.append({"id_articulo": d.id_articulo, "articulo": art["nombre"],
                             "unidad": art["unidad_de_medida"],
                             "cantidad_base_diaria": d.cantidad_base_diaria,
                             "cantidad_min": d.cantidad_min, "cantidad_max": d.cantidad_max})
    else:
        entradas = [{"id_articulo": d["id_articulo"], "articulo": d["articulo"],
                     "unidad": d["unidad"], "cantidad_base_diaria": d["cantidad_base_diaria"],
                     "cantidad_min": d["cantidad_min"], "cantidad_max": d["cantidad_max"]}
                    for d in regla["detalles"]]

    resultado = []
    for d in entradas:
        cantidad = float(d["cantidad_base_diaria"]) * dias * poblacion
        cantidad = motor._redondear(cantidad, regla["redondeo"])
        if d["cantidad_max"] is not None and cantidad > float(d["cantidad_max"]):
            cantidad = float(d["cantidad_max"])
        if d["cantidad_min"] is not None and cantidad < float(d["cantidad_min"]):
            cantidad = float(d["cantidad_min"])
        resultado.append({"id_articulo": d["id_articulo"], "articulo": d["articulo"],
                          "cantidad": cantidad, "unidad": d["unidad"]})
    return {
        "simulacion": True,
        "regla": {"id_regla": regla["id_regla"], "nombre_regla": regla["nombre_regla"],
                  "criterio_aplicacion": regla["criterio_aplicacion"],
                  "estado": regla["estado"]},
        "resultado": resultado,
        "poblacion": poblacion,
        "dias_duracion": dias,
        "persistido_como_necesidad": False,
    }


def _snapshot_regla(regla: dict) -> dict:
    """Configuración exacta de la regla (columnas + detalles) para la versión."""
    snap = {c: regla[c] for c in motor.CAMPOS_KIT_JSON}
    snap["estado"] = "publicada"
    snap["detalles"] = [{
        "id_articulo": d["id_articulo"],
        "cantidad_base_diaria": float(d["cantidad_base_diaria"]),
        "cantidad_min": float(d["cantidad_min"]) if d["cantidad_min"] is not None else None,
        "cantidad_max": float(d["cantidad_max"]) if d["cantidad_max"] is not None else None,
    } for d in regla["detalles"]]
    return snap


def publicar_regla(db: Session, id_regla: int, body, id_usuario: int | None = None) -> dict:
    """Publica una regla: crea la versión inmutable y activa para el motor.

    Exige {confirmar: true} y que la regla supere la validación (422 si no).
    Publicar una regla ya publicada es 409: edítela (vuelve a borrador) y
    vuelva a publicar para generar una versión nueva.
    """
    if not (body and body.confirmar is True):
        raise HTTPException(status_code=400,
                            detail='Debe confirmar la publicación con {"confirmar": true}')
    regla = _regla_response(db, id_regla)
    if not regla:
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    validacion = _validar_estructura_regla(db, regla)
    if not validacion["valida"]:
        raise HTTPException(status_code=422, detail=validacion)
    if regla["estado"] == "publicada":
        raise HTTPException(
            status_code=409,
            detail=f"La regla {id_regla} ya está publicada (versión "
                   f"{regla['version_actual']}); edítela —vuelve a borrador— y "
                   f"publique de nuevo para generar otra versión")

    num = db.execute(text("""
        INSERT INTO rida.regla_calculo_version
            (id_regla, numero_version, configuracion_json, publicado_por)
        SELECT :id, COALESCE(MAX(numero_version), 0) + 1,
               CAST(:snap AS jsonb), :usr
        FROM rida.regla_calculo_version WHERE id_regla = :id
        RETURNING numero_version
    """), {"id": id_regla, "snap": json.dumps(_snapshot_regla(regla), default=str),
           "usr": id_usuario}).scalar()
    db.execute(text("""
        UPDATE rida.regla_calculo_kit SET estado = 'publicada',
               fecha_modificacion = CURRENT_TIMESTAMP
        WHERE id_regla = :id
    """), {"id": id_regla})
    db.commit()
    return {"publicada": True, "regla_id": id_regla, "version": num, "estado": "publicada"}


def listar_versiones(db: Session, id_regla: int) -> list:
    if not _row(db, "SELECT 1 AS ok FROM rida.regla_calculo_kit WHERE id_regla = :id",
                {"id": id_regla}):
        raise HTTPException(status_code=404, detail=f"Regla {id_regla} no encontrada")
    return _rows(db, """
        SELECT v.id_version, v.id_regla, v.numero_version, v.configuracion_json,
               v.fecha_publicacion, v.publicado_por
        FROM rida.regla_calculo_version v
        WHERE v.id_regla = :id
        ORDER BY v.numero_version DESC
    """, {"id": id_regla})


# ============================================================================
#  Ejecuciones del motor (v2.58.0): POST /calculos + consultas
# ============================================================================

def crear_calculo(db: Session, body, user: dict | None = None) -> dict:
    """POST /calculos: ejecuta el motor para un expediente.

    - modo 'previsualizacion': calcula (por familia y total) SIN persistir y
      SIN dejar historial (calculo_id = null).
    - modo 'operativo': exige etapa EN_APROBACION, hace el upsert de
      solicitud_articulo (mismas reglas de siempre) y REGISTRA la ejecución
      (cabecera + detalle por familia, con la versión exacta de cada regla).
    - reglas[] permite fijar la versión exacta a ejecutar: una versión antigua
      se ejecuta desde su snapshot JSONB (reproducibilidad histórica).
    """
    sol = _sol_or_404(db, body.id_solicitud)
    if user is not None:
        validar_scope(db, user, body.id_solicitud)
    operativo = body.modo == "operativo"
    if operativo and body.familias:
        raise HTTPException(
            status_code=400,
            detail="familias[] solo se admite en modo previsualizacion: el modo "
                   "operativo calcula TODAS las familias del evento")
    if operativo and sol["etapa"] != "EN_APROBACION":
        raise HTTPException(
            status_code=409,
            detail=f"El modo operativo exige etapa EN_APROBACION (actual: {sol['etapa']})")

    kits_inyectados: list[dict] | None = None
    version_map: dict[int, int] = {}
    if body.reglas:
        kits_inyectados = []
        for r in body.reglas:
            regla = _row(db, _SQL_REGLA_BASE + " WHERE k.id_regla = :id", {"id": r.id_regla})
            if not regla:
                raise HTTPException(status_code=404, detail=f"Regla {r.id_regla} no encontrada")
            if regla["estado"] != "publicada":
                raise HTTPException(
                    status_code=409,
                    detail=f"La regla {r.id_regla} está en borrador; publíquela para ejecutarla")
            if r.numero_version is None:
                v = _ultima_version(db, r.id_regla)
                if not v:
                    raise HTTPException(
                        status_code=409,
                        detail=f"La regla {r.id_regla} no tiene versiones publicadas")
            else:
                v = _row(db, """
                    SELECT id_version, numero_version, configuracion_json
                    FROM rida.regla_calculo_version
                    WHERE id_regla = :id AND numero_version = :nv
                """, {"id": r.id_regla, "nv": r.numero_version})
                if not v:
                    raise HTTPException(
                        status_code=404,
                        detail=f"La regla {r.id_regla} no tiene la versión {r.numero_version}")
            version_map[r.id_regla] = v["id_version"]
            kits_inyectados.extend(
                motor._kits_desde_snapshot(db, r.id_regla, v["configuracion_json"]))

    if body.familias:
        validas = {x["id_familia"] for x in _rows(db, """
            SELECT f.id_familia FROM rida.familia f
            JOIN rida.formulario_rida fr ON fr.id_formulario = f.id_formulario
            WHERE fr.id_evento_rida = :ev AND f.id_familia = ANY(:fams)
        """, {"ev": sol["id_evento_rida"], "fams": body.familias})}
        faltan = [f for f in body.familias if f not in validas]
        if faltan:
            raise HTTPException(
                status_code=404,
                detail=f"Familias inexistentes o fuera del expediente: {faltan}")

    calculados, por_familia = motor.ejecutar_kits_completo(
        db, sol["id_evento_rida"], kits=kits_inyectados,
        id_familias=body.familias, con_desglose=True)
    if not version_map:
        for rid in {c["id_regla"] for c in calculados}:
            v = _ultima_version(db, rid)
            if v:
                version_map[rid] = v["id_version"]
    agregados = motor.agrupar_calculados(calculados)

    res_map: dict[int, list] = {}
    for f in por_familia:
        res_map.setdefault(f["id_familia"], []).append({
            "id_regla": f["id_regla"], "id_articulo": f["id_articulo"],
            "articulo": f["articulo"], "cantidad": f["cantidad"], "unidad": f["unidad"]})
    resultados = [{"id_familia": fid, "articulos": arts} for fid, arts in res_map.items()]

    id_calculo = None
    if operativo:
        _persistir_agregados(db, body.id_solicitud, agregados, body.forzar)
        id_usuario = user["id_usuario"] if user else None
        id_calculo = _registrar_ejecucion(
            db, body.id_solicitud, id_usuario, por_familia, version_map)
        db.commit()

    return {
        "calculo_id": id_calculo,
        "estado": "completado",
        "modo": body.modo,
        "id_solicitud": body.id_solicitud,
        "resultados": resultados,
        "articulos": agregados,
        "inventario_consultado": False,
        "necesidades_registradas": operativo,
    }


def _calculo_cabecera(db: Session, id_calculo, user: dict | None) -> dict:
    """Cabecera de una ejecución + chequeo de scope sobre su solicitud."""
    cab = _row(db, """
        SELECT e.id_calculo, e.id_solicitud, e.modo, e.estado,
               e.fecha_ejecucion, e.id_usuario,
               (SELECT COUNT(*) FROM rida.ejecucion_calculo_detalle d
                 WHERE d.id_calculo = e.id_calculo) AS total_detalles,
               (SELECT COUNT(DISTINCT d.id_familia) FROM rida.ejecucion_calculo_detalle d
                 WHERE d.id_calculo = e.id_calculo) AS total_familias
        FROM rida.ejecucion_calculo e
        WHERE e.id_calculo = :id
    """, {"id": id_calculo})
    if not cab:
        raise HTTPException(status_code=404,
                            detail=f"Ejecución {id_calculo} no encontrada")
    if user is not None:
        validar_scope(db, user, cab["id_solicitud"])
    cab["id_calculo"] = str(cab["id_calculo"])
    return cab


def get_calculo(db: Session, id_calculo, user: dict | None = None) -> dict:
    return _calculo_cabecera(db, id_calculo, user)


def get_calculo_detalle(db: Session, id_calculo, user: dict | None = None) -> list:
    _calculo_cabecera(db, id_calculo, user)
    filas = _rows(db, """
        SELECT d.id_detalle, d.id_calculo, d.id_familia, d.id_regla, d.id_version,
               d.id_articulo, a.nombre AS articulo,
               d.cantidad_calculada, d.unidad_medida
        FROM rida.ejecucion_calculo_detalle d
        JOIN rida.cat_articulo a ON a.id_articulo = d.id_articulo
        WHERE d.id_calculo = :id
        ORDER BY d.id_familia, d.id_regla, d.id_detalle
    """, {"id": id_calculo})
    for f in filas:
        f["id_calculo"] = str(f["id_calculo"])
    return filas


def listar_calculos(db: Session, id_solicitud: int, user: dict | None,
                    limit: int = 100, skip: int = 0, todos: bool = False
                    ) -> tuple[list, int]:
    """Historial de ejecuciones de un expediente (recientes primero)."""
    _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    page = "" if todos else " LIMIT :limit OFFSET :skip"
    params = {"id": id_solicitud}
    if not todos:
        params.update({"limit": limit, "skip": skip})
    filas = _rows(db, f"""
        SELECT e.id_calculo, e.id_solicitud, e.modo, e.estado, e.fecha_ejecucion,
               e.id_usuario,
               (SELECT COUNT(*) FROM rida.ejecucion_calculo_detalle d
                 WHERE d.id_calculo = e.id_calculo) AS total_detalles,
               (SELECT COUNT(DISTINCT d.id_familia)
                  FROM rida.ejecucion_calculo_detalle d
                 WHERE d.id_calculo = e.id_calculo) AS total_familias
        FROM rida.ejecucion_calculo e
        WHERE e.id_solicitud = :id
        ORDER BY e.fecha_ejecucion DESC{page}
    """, params)
    for f in filas:
        f["id_calculo"] = str(f["id_calculo"])
    total = _row(db, """
        SELECT COUNT(*) AS total FROM rida.ejecucion_calculo WHERE id_solicitud = :id
    """, {"id": id_solicitud})["total"]
    return filas, total


# ============================================================================
#  Motor de NECESIDADES (v2.61.0): CRUD de reglas + preview/persistencia
# ============================================================================

_COLUMNAS_REGLA_NECESIDAD = (
    "nombre", "criterio_aplicacion", "id_categoria_ayuda", "id_articulo",
    "cantidad_base", "dias_duracion", "condiciones", "prioridad", "orden",
    "activo",
)

_SQL_REGLA_NECESIDAD = """
    SELECT r.id_regla_necesidad, r.nombre, r.criterio_aplicacion,
           r.id_categoria_ayuda, c.nombre AS categoria,
           r.id_articulo, a.nombre AS articulo, a.unidad_de_medida AS unidad,
           r.cantidad_base, r.dias_duracion, r.condiciones,
           r.prioridad, r.orden, r.activo,
           r.fecha_creacion, r.fecha_modificacion
    FROM rida.regla_necesidad r
    JOIN rida.cat_articulo a ON a.id_articulo = r.id_articulo
    JOIN rida.cat_categoria_ayuda c
      ON c.id_categoria_ayuda = r.id_categoria_ayuda
"""


def _regla_necesidad_response(db: Session, id_regla: int) -> dict | None:
    return _row(db, _SQL_REGLA_NECESIDAD +
                " WHERE r.id_regla_necesidad = :id", {"id": id_regla})


def listar_reglas_necesidad(db: Session, *, activo: bool | None = None,
                            criterio_aplicacion: str | None = None,
                            id_categoria_ayuda: int | None = None) -> list:
    conds, params = ["1 = 1"], {}
    if activo is not None:
        conds.append("r.activo = :activo")
        params["activo"] = activo
    if criterio_aplicacion:
        conds.append("r.criterio_aplicacion = :crit")
        params["crit"] = criterio_aplicacion
    if id_categoria_ayuda:
        conds.append("r.id_categoria_ayuda = :cat")
        params["cat"] = id_categoria_ayuda
    return _rows(db, _SQL_REGLA_NECESIDAD + " WHERE " + " AND ".join(conds) +
                 " ORDER BY r.orden, r.prioridad, r.id_regla_necesidad", params)


def get_regla_necesidad(db: Session, id_regla: int) -> dict:
    regla = _regla_necesidad_response(db, id_regla)
    if not regla:
        raise HTTPException(status_code=404,
                            detail=f"Regla de necesidad {id_regla} no encontrada")
    return regla


def _validar_regla_necesidad(db: Session, data: dict) -> None:
    id_categoria = data["id_categoria_ayuda"]
    id_articulo = data["id_articulo"]
    cat = _row(db, """
        SELECT 1 AS ok FROM rida.cat_categoria_ayuda
        WHERE id_categoria_ayuda = :id
    """, {"id": id_categoria})
    if not cat:
        raise HTTPException(status_code=400,
                            detail=f"La categoría {id_categoria} no existe")
    art = _row(db, """
        SELECT id_categoria_ayuda FROM rida.cat_articulo
        WHERE id_articulo = :id
    """, {"id": id_articulo})
    if not art:
        raise HTTPException(status_code=400,
                            detail=f"El artículo {id_articulo} no existe")
    if art["id_categoria_ayuda"] != id_categoria:
        raise HTTPException(
            status_code=400,
            detail=f"El artículo {id_articulo} no pertenece a la categoría "
                   f"{id_categoria}")
    for err in motor_necesidades.validar_condiciones(
            data["criterio_aplicacion"], data.get("condiciones")):
        raise HTTPException(status_code=422, detail=err)


def _condiciones_json(condiciones) -> str:
    if condiciones is None:
        condiciones = {}
    if hasattr(condiciones, "model_dump"):
        condiciones = condiciones.model_dump(exclude_none=True)
    return json.dumps(condiciones)


def crear_regla_necesidad(db: Session, body) -> dict:
    data = body.model_dump()
    data["condiciones"] = body.condiciones.model_dump(exclude_none=True)
    _validar_regla_necesidad(db, data)
    try:
        rid = db.execute(text("""
            INSERT INTO rida.regla_necesidad
                (nombre, criterio_aplicacion, id_categoria_ayuda, id_articulo,
                 cantidad_base, dias_duracion, condiciones, prioridad, orden,
                 activo)
            VALUES (:nombre, :criterio, :cat, :art, :base, :dias,
                    CAST(:cond AS jsonb), :pri, :orden, :activo)
            RETURNING id_regla_necesidad
        """), {"nombre": data["nombre"],
               "criterio": data["criterio_aplicacion"],
               "cat": data["id_categoria_ayuda"],
               "art": data["id_articulo"],
               "base": data["cantidad_base"],
               "dias": data["dias_duracion"],
               "cond": _condiciones_json(data["condiciones"]),
               "pri": data["prioridad"], "orden": data["orden"],
               "activo": data["activo"]}).scalar()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400,
                            detail="No se pudo crear la regla de necesidad")
    return _regla_necesidad_response(db, rid)


def actualizar_regla_necesidad(db: Session, id_regla: int, body) -> dict:
    actual = get_regla_necesidad(db, id_regla)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    if "condiciones" in cambios and body.condiciones is not None:
        cambios["condiciones"] = body.condiciones.model_dump(exclude_none=True)

    fusion = {k: actual[k] for k in (
        "nombre", "criterio_aplicacion", "id_categoria_ayuda", "id_articulo",
        "cantidad_base", "dias_duracion", "condiciones", "prioridad", "orden",
        "activo")}
    fusion.update(cambios)
    _validar_regla_necesidad(db, fusion)

    sets, params = [], {"id": id_regla}
    for campo in _COLUMNAS_REGLA_NECESIDAD:
        if campo in cambios:
            valor = cambios[campo]
            if campo == "condiciones":
                sets.append("condiciones = CAST(:condiciones AS jsonb)")
                valor = _condiciones_json(valor)
            else:
                sets.append(f"{campo} = :{campo}")
            params[campo] = valor
    sets.append("fecha_modificacion = CURRENT_TIMESTAMP")
    db.execute(text(
        f"UPDATE rida.regla_necesidad SET {', '.join(sets)} "
        f"WHERE id_regla_necesidad = :id"), params)
    db.commit()
    return _regla_necesidad_response(db, id_regla)


def eliminar_regla_necesidad(db: Session, id_regla: int) -> None:
    get_regla_necesidad(db, id_regla)
    ref = _row(db, """
        SELECT COUNT(*) AS c FROM rida.necesidad
        WHERE id_regla_necesidad = :id
    """, {"id": id_regla})
    if ref["c"] > 0:
        raise HTTPException(
            status_code=409,
            detail=f"La regla generó {ref['c']} necesidad(es); desactívela "
                   f"(activo=false) en lugar de eliminarla")
    db.execute(text("DELETE FROM rida.regla_necesidad "
                    "WHERE id_regla_necesidad = :id"), {"id": id_regla})
    db.commit()


def _familias_evento(db: Session, id_evento_rida: int) -> list[int]:
    return [r["id_familia"] for r in _rows(db, """
        SELECT f.id_familia
        FROM rida.familia f
        JOIN rida.formulario_rida fr ON fr.id_formulario = f.id_formulario
        WHERE fr.id_evento_rida = :ev
    """, {"ev": id_evento_rida})]


def preview_motor_necesidades(db: Session, id_solicitud: int,
                              user: dict | None = None) -> dict:
    """Calcula necesidades sin persistir (vista previa del frontend)."""
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    necesidades, resumen = motor_necesidades.evaluar(
        db, sol["id_evento_rida"])
    resumen = {**resumen, "manuales_reemplazadas": 0, "motoras_eliminadas": 0}
    return {"id_solicitud": id_solicitud, "persistido": False,
            "necesidades": necesidades, "resumen": resumen}


def ejecutar_motor_necesidades(db: Session, id_solicitud: int,
                               user: dict | None = None) -> dict:
    """Calcula y persiste necesidades. El motor manda.

    Reemplaza las necesidades MANUALES de las categorías que el motor cubre
    para cada familia y todas las filas `fuente='motor'` previas del evento;
    luego inserta el resultado actual. Requiere etapa ENVIADA o EN_APROBACION.
    """
    sol = _sol_or_404(db, id_solicitud)
    if user is not None:
        validar_scope(db, user, id_solicitud)
    if sol["etapa"] not in ("ENVIADA", "EN_APROBACION"):
        raise HTTPException(
            status_code=409,
            detail="El motor de necesidades solo persiste en ENVIADA o "
                   f"EN_APROBACION (actual: {sol['etapa']})")

    necesidades, resumen = motor_necesidades.evaluar(
        db, sol["id_evento_rida"])
    familias = _familias_evento(db, sol["id_evento_rida"])

    cubiertas: dict[int, set[int]] = {}
    for n in necesidades:
        cubiertas.setdefault(n["id_familia"], set()).add(n["id_categoria_ayuda"])

    try:
        ids_borrar: list[int] = []
        for id_familia, cats in cubiertas.items():
            ids_borrar.extend(r["id_necesidad"] for r in _rows(db, """
                SELECT id_necesidad FROM rida.necesidad
                WHERE fuente = 'manual' AND id_familia = :fam
                  AND id_categoria_ayuda = ANY(:cats)
            """, {"fam": id_familia, "cats": list(cats)}))
        motoras = _rows(db, """
            SELECT id_necesidad FROM rida.necesidad
            WHERE fuente = 'motor' AND id_familia = ANY(:fams)
        """, {"fams": familias})
        ids_borrar.extend(r["id_necesidad"] for r in motoras)

        if ids_borrar:
            # Defensivo: familia.id_necesidad es un FK legacy.
            db.execute(text("""
                UPDATE rida.familia SET id_necesidad = NULL
                WHERE id_necesidad = ANY(:ids)
            """), {"ids": ids_borrar})
            db.execute(text("DELETE FROM rida.necesidad "
                            "WHERE id_necesidad = ANY(:ids)"),
                       {"ids": ids_borrar})

        for n in necesidades:
            db.execute(text("""
                INSERT INTO rida.necesidad
                    (id_familia, id_categoria_ayuda, id_articulo, cantidad,
                     unidad_de_medida, prioridad, estado, fuente,
                     id_regla_necesidad)
                VALUES (:fam, :cat, :art, :cant, :uni, 3, FALSE, 'motor', :reg)
            """), {"fam": n["id_familia"], "cat": n["id_categoria_ayuda"],
                   "art": n["id_articulo"], "cant": n["cantidad"],
                   "uni": n["unidad"], "reg": n["id_regla"]})
        db.commit()
    except Exception:
        db.rollback()
        raise

    resumen = {**resumen,
               "manuales_reemplazadas": len(ids_borrar) - len(motoras),
               "motoras_eliminadas": len(motoras)}
    return {"id_solicitud": id_solicitud, "persistido": True,
            "necesidades": necesidades, "resumen": resumen}
