from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.common.responses import success_response
from api.core.auth import get_current_user
from api.core.db import get_db

from .schemas import *
from .service import AlmacenesService

router = APIRouter(prefix="/almacenes", tags=["almacenes"])


# === ALMACENES CRUD ===
@router.get("")
def listar_almacenes(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    todos: bool = Query(False),
    nivel: Optional[Literal["municipal", "departamental", "nacional"]] = Query(None),
    estado: Optional[Literal["ACTIVO", "INACTIVO", "MANTENIMIENTO"]] = Query(None),
    q: Optional[str] = Query(None),
    id_municipio: Optional[int] = Query(None),
    id_departamento: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = AlmacenesService(db)
    data, total = svc.listar_almacenes(user, limit=limit, skip=skip, todos=todos, nivel=nivel, estado=estado, q=q, id_municipio=id_municipio, id_departamento=id_departamento)
    return success_response(message="Almacenes listados", data=data, total=total)


@router.get("/{id_almacen}")
def obtener_almacen(id_almacen: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data = svc.obtener_almacen(id_almacen)
    return success_response(data)


@router.post("")
def crear_almacen(body: AlmacenCreate, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data = svc.crear_almacen(body.model_dump(), user)
    return success_response(data)


@router.put("/{id_almacen}")
def actualizar_almacen(id_almacen: int, body: AlmacenUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data = svc.actualizar_almacen(id_almacen, body.model_dump(exclude_unset=True), user)
    return success_response(data)


@router.delete("/{id_almacen}")
def eliminar_almacen(id_almacen: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    ok = svc.eliminar_almacen(id_almacen)
    return success_response({"eliminado": ok})


# === SOLICITUDES DE SALIDA ===
@router.post("/{id_almacen}/solicitudes-salida")
def crear_solicitud_salida(id_almacen: int, body: AlmacenSolicitudCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.crear_solicitud_salida(id_almacen, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id_almacen}/solicitudes-salida")
def listar_solicitudes_salida(id_almacen: int, limit: int = Query(100, ge=1, le=500), skip: int = Query(0, ge=0), todos: bool = Query(False), estado: Optional[str] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data, total = svc.listar_solicitudes_salida(id_almacen, limit=limit, skip=skip, todos=todos, estado=estado)
    return success_response(message="Solicitudes listadas", data=data, total=total)


@router.post("/{id_almacen}/solicitudes-salida/{id_solicitud_salida}/aprobar")
def aprobar_solicitud(id_almacen: int, id_solicitud_salida: int, body: AlmacenSolicitudAprobar, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.aprobar_solicitud_salida(id_solicitud_salida, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{id_almacen}/solicitudes-salida/{id_solicitud_salida}/rechazar")
def rechazar_solicitud(id_almacen: int, id_solicitud_salida: int, body: AlmacenSolicitudRechazar, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.rechazar_solicitud_salida(id_solicitud_salida, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# === COBERTURA ===
@router.get("/cobertura/necesidades-rida")
def cobertura_necesidades_rida(id_solicitud: int = Query(None), id_municipio: int = Query(None), id_departamento: int = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data = svc.cobertura_necesidades_rida({"id_solicitud": id_solicitud, "id_municipio": id_municipio, "id_departamento": id_departamento})
    return success_response(data)


# === NEA ===
@router.post("/{id_almacen}/entradas")
def crear_nea(id_almacen: int, body: NEACreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.crear_nea(id_almacen, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# === PECOSA ===
@router.post("/{id_almacen}/salidas")
def crear_pecosa(id_almacen: int, body: PECOSACreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.crear_pecosa(id_almacen, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{id_almacen}/salidas/{id_entrega}/pendiente-entregar")
def pendiente_entregar(id_almacen: int, id_entrega: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data = svc.pendiente_entregar(id_entrega)
    return success_response(data)


@router.post("/{id_almacen}/salidas/{id_entrega}/cerrar")
def cerrar_pecosa(id_almacen: int, id_entrega: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.cerrar_pecosa(id_entrega, user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))


# === ENTREGA A BENEFICIARIOS ===
@router.post("/salidas/{id_entrega}/entregar-beneficiario")
def entregar_beneficiario(id_entrega: int, body: EntregaBeneficiarioCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    try:
        data = svc.entregar_bbeneficiario(id_entrega, body.model_dump(), user) if False else None
    except Exception:
        pass
    try:
        data = svc.entregar_beneficiario(id_entrega, body.model_dump(), user)
        return success_response(data)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


# === STOCK Y KARDEX ===
@router.get("/{id_almacen}/stock")
def stock_almacen(id_almacen: int, limit: int = Query(100, ge=1, le=500), skip: int = Query(0, ge=0), todos: bool = Query(False), q: Optional[str] = Query(None), id_articulo: Optional[int] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data, total = svc.listar_stock(id_almacen, limit=limit, skip=skip, todos=todos, q=q, id_articulo=id_articulo)
    return success_response(message="Stock listado", data=data, total=total)


@router.get("/{id_almacen}/kardex")
def kardex_almacen(id_almacen: int, limit: int = Query(100, ge=1, le=500), skip: int = Query(0, ge=0), todos: bool = Query(False), id_articulo: Optional[int] = Query(None), tipo_movimiento: Optional[Literal["ENTRAGEN", "SALIDA", "AJUSTE"]] = Query(None), referencia_tipo: Optional[Literal["NEA", "PECOSA", "CONTEO", "ANULACION", "OTRO"]] = Query(None), fecha_desde: Optional[date] = Query(None), fecha_hasta: Optional[date] = Query(None), db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = AlmacenesService(db)
    data, total = svc.listar_kardex(id_almacen, limit=limit, skip=skip, todos=todos, id_articulo=id_articulo, tipo_movimiento=tipo_movimiento, referencia_tipo=referencia_tipo, fecha_desde=fecha_desde.isoformat() if fecha_desde else None, fecha_hasta=fecha_hasta.isoformat() if fecha_hasta else None)
    return success_response(message="Kardex listado", data=data, total=total)
