from fastapi import APIRouter, Depends, HTTPException, Query, Form, UploadFile, File
from sqlalchemy.orm import Session
from datetime import date
from pathlib import Path

from ...database import get_db
from ...dependencies import get_current_user
from ...response import SuccessResponse, DataListResponse, DataItemResponse, MessageResponse
from ...auth.permisos import module_permiso
from ...edan.utils import require_rol
from ...upload import save_documento_pdf
from . import service
from .schemas import (
    CatModalidadResponse, CatRequisitoResponse, RequisitoConEstado,
    SolicitudCreate, SolicitudUpdate, SolicitudDocumentoCreate, SolicitudResponse,
    CatEtapaSolicitudResponse, BitacoraItemResponse, TransicionRequest,
    AprobacionesSolicitudResponse, CadenaAprobacionResponse, CadenaAprobacionUpdateRequest,
)

router = APIRouter(
    prefix="/rida/solicitudes",
    dependencies=[Depends(module_permiso("RIDA"))],
)

TAG_SOLICITUDES = "RIDA > Solicitudes"
ROLES_ESCRITURA = (1, 2, 6, 7)
ROLES_CONFIG_APROBACION = (1, 2)


@router.get("/cat-modalidades", tags=[TAG_SOLICITUDES], response_model=DataListResponse[CatModalidadResponse],
            summary="Listar modalidades de solicitud",
            description="Retorna las 4 modalidades activas: Ayuda Humanitaria, Respuesta Rápida UMEE, Rehabilitación-Insumos, Rehabilitación-Reconstrucción.")
def listar_cat_modalidades(db: Session = Depends(get_db)):
    data = service.listar_modalidades(db)
    return SuccessResponse(message="Modalidades listadas correctamente", data=data, total=len(data))


@router.get("/cat-requisitos", tags=[TAG_SOLICITUDES], response_model=DataListResponse[CatRequisitoResponse],
            summary="Listar requisitos por modalidad",
            description="Retorna el checklist de requisitos para una modalidad (o todas). Cada requisito indica si es documento y si es hito de aprobación.")
def listar_cat_requisitos(id_modalidad: int | None = Query(None), db: Session = Depends(get_db)):
    data = service.listar_requisitos(db, id_modalidad)
    return SuccessResponse(message="Requisitos listados correctamente", data=data, total=len(data))


@router.get("/cat-etapas", tags=[TAG_SOLICITUDES], response_model=DataListResponse[CatEtapaSolicitudResponse],
            summary="Catálogo de etapas de solicitud",
            description="Retorna las 17 etapas válidas del flujo de solicitud.")
def listar_cat_etapas(db: Session = Depends(get_db)):
    data = service.listar_etapas(db)
    return SuccessResponse(message="Etapas listadas correctamente", data=data, total=len(data))


# Catálogo de la máquina de aprobaciones. Va ANTES de /{id_solicitud} por el
# mismo motivo que los cat-* anteriores: FastAPI resuelve las rutas en orden de
# declaración y "/{id_solicitud}" (que tipa id_solicitud como int) se
# llevaría este path y devolvería 422.
DESC_CADENA_APROBACION = (
    "Niveles de la cadena de visaciones con su rol y su alcance, la cadena por "
    "defecto y las cadenas específicas por modalidad.\n\n"
    "- `niveles`: catálogo de los 7 niveles canónicos en orden semántico\n"
    "  (validacion → viceministro → dgea → revision_articulos → suministro →\n"
    "  despacho → entrega; v2.60.0). Los "
    "`roles` y el `alcance` los publica el backend para que el frontend no los "
    "replica.\n"
    "- `default`: cadena usada cuando la modalidad no tiene entrada propia.\n"
    "- `por_modalidad`: solo las modalidades cuya cadena **difiere** del default, "
    "indexadas por `id_modalidad`. La modalidad Ayuda Humanitaria NO se "
    "configura aquí: usa su propio motor de 7 niveles.\n\n"
    "Se consume una vez y se cachea: el listado de solicitudes no hace un GET de "
    "la máquina por fila."
)


@router.get("/cat-cadena-aprobacion", tags=[TAG_SOLICITUDES],
            response_model=DataItemResponse[CadenaAprobacionResponse],
            summary="Cadenas de aprobación institucional",
            description=DESC_CADENA_APROBACION)
def listar_cadena_aprobacion(db: Session = Depends(get_db)):
    return SuccessResponse(message="Cadenas de aprobación obtenidas correctamente",
                           data=service.listar_cadenas_aprobacion(db))


@router.put("/cat-cadena-aprobacion/{id_modalidad}", tags=[TAG_SOLICITUDES],
            dependencies=[Depends(require_rol(*ROLES_CONFIG_APROBACION))],
            response_model=DataItemResponse[CadenaAprobacionResponse],
            summary="Configurar la cadena de una modalidad",
            description="Reemplaza la cadena de la modalidad por la lista de niveles enviada.\n\n"
                        "La cadena debe ser un subconjunto **ordenado** de los 7 niveles "
                        "canónicos (ej. `[\"validacion\",\"viceministro\",\"dgea\","
                        "\"revision_articulos\",\"suministro\",\"despacho\",\"entrega\"]`); no se "
                        "admiten niveles nuevos ni reordenes fuera del orden semántico, y debe "
                        "incluir `validacion`, `revision_articulos`, `suministro`, `despacho` y "
                        "`entrega` (son los niveles con trigger de etapa: sin ellos la "
                        "solicitud no puede avanzar).\n\n"
                        "Responde **409** si la modalidad es Ayuda Humanitaria (usa su propia "
                        "cadena de 7 niveles) o si hay solicitudes de esa modalidad con el "
                        "motor activo (`ENVIADA`..`ENTREGADA`): cambiarla en caliente "
                        "dejaría esas solicitudes con filas de una cadena que ya no existe.")
def actualizar_cadena_aprobacion(
    id_modalidad: int,
    body: CadenaAprobacionUpdateRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.reemplazar_cadena_modalidad(db, id_modalidad, body.niveles)
    return SuccessResponse(message="Cadena de aprobación actualizada correctamente", data=data)


@router.post("", tags=[TAG_SOLICITUDES], status_code=201, response_model=DataItemResponse[SolicitudResponse],
             summary="Crear solicitud desde evento RIDA",
             description="Crea una nueva solicitud vinculada al **evento RIDA** (padre, `id_evento_rida`). "
                         "Auto-completa: id_municipio/id_departamento (del EDAN del evento; un evento abarca "
                         "un solo municipio), id_usuario_crea, etapa=ENVIADA, fecha_inicio=hora de Bolivia. "
                         "El motor de aprobaciones arranca de inmediato (v2.60.0; no hay etapa BORRADOR). "
                         "Error 404 si el evento no existe; 400 si el evento está CERRADO.")
def crear_solicitud(
    body: SolicitudCreate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    id_solicitud = service.crear_solicitud(db, body.id_evento_rida, body.id_modalidad, _user["id_usuario"], body.observaciones)
    data = service.obtener_solicitud(db, id_solicitud)
    return SuccessResponse(message="Solicitud creada correctamente", data=data)


@router.get("", tags=[TAG_SOLICITUDES], response_model=DataListResponse[SolicitudResponse],
            summary="Listar solicitudes con filtros",
            description="Lista **paginada, por defecto los últimos 50** (ORDER BY id DESC). "
                        "`limit` = tamaño de página (los últimos N, 1..500), `skip` = desplazamiento para "
                        "hojear páginas, `todos=true` devuelve todo sin paginar. "
                        "Filtros: id_modalidad (id único o lista separada por comas, ej. `1` o `1,3`), "
                        "modalidad (nombre o código, parcial e insensible a mayúsculas), etapa, "
                        "id_departamento, id_municipio, id_evento_rida, q (observaciones). "
                        "Aplica scope del usuario (municipio/departamento).")
def listar_solicitudes(
    id_modalidad: str | None = Query(
        None, description="Filtrar por modalidad(es): id único o lista separada por comas (ej. 1 o 1,3)"),
    modalidad: str | None = Query(
        None, description="Filtrar por nombre o código de modalidad (parcial, insensible a mayúsculas)"),
    etapa: str | None = Query(None),
    id_departamento: int | None = Query(None),
    id_municipio: int | None = Query(None),
    id_evento_rida: int | None = Query(None, description="Filtrar por evento RIDA (padre)"),
    q: str | None = Query(None),
    skip: int = Query(0, ge=0, description="Desplazamiento (página = skip/limit)"),
    limit: int = Query(50, ge=1, le=500, description="Tamaño de página: los últimos N"),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    ids_modalidad = None
    if id_modalidad and id_modalidad.strip():
        try:
            ids_modalidad = [int(t) for t in id_modalidad.split(",") if t.strip()]
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"id_modalidad inválido: '{id_modalidad}' "
                       "(use ids separados por comas, ej. 1 o 1,3)")
        if not ids_modalidad:
            ids_modalidad = None
    filtros = {k: v for k, v in {
        "id_modalidad": ids_modalidad, "modalidad": modalidad, "etapa": etapa,
        "id_departamento": id_departamento,
        "id_municipio": id_municipio, "id_evento_rida": id_evento_rida, "q": q
    }.items() if v is not None}
    
    user_scope = {}
    if _user.get("id_rol") not in ROLES_ESCRITURA:
        if _user.get("id_municipio"):
            user_scope["id_municipio"] = _user["id_municipio"]
        elif _user.get("id_departamento"):
            user_scope["id_departamento"] = _user["id_departamento"]
    
    if todos:
        skip = 0
        limit = 10000
    data, total = service.listar_solicitudes(db, filtros, skip, limit, user_scope)
    return SuccessResponse(message="Solicitudes listadas correctamente", data=data, total=total)


@router.get("/{id_solicitud}", tags=[TAG_SOLICITUDES], response_model=DataItemResponse[SolicitudResponse],
            summary="Obtener detalle de solicitud",
            description="Retorna cabecera de la solicitud con datos de modalidad, municipio, departamento y estado de aprobaciones.")
def obtener_solicitud(id_solicitud: int, db: Session = Depends(get_db),
                      _user=Depends(get_current_user)):
    data = service.obtener_solicitud(db, id_solicitud)
    if not data:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    return SuccessResponse(message="Solicitud obtenida correctamente", data=data)


@router.put("/{id_solicitud}", tags=[TAG_SOLICITUDES], response_model=DataItemResponse[SolicitudResponse],
            summary="Actualizar solicitud",
            description="Solo permite actualizar en etapa ENVIADA (antes de que se apruebe el primer nivel). Campos actualizables: id_modalidad, observaciones.")
def actualizar_solicitud(
    id_solicitud: int,
    body: SolicitudUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    if sol["etapa"] != "ENVIADA":
        raise HTTPException(status_code=400, detail="Solo se puede actualizar en etapa ENVIADA")
    
    update_data = {}
    if body.id_modalidad is not None:
        update_data["id_modalidad"] = body.id_modalidad
    if body.observaciones is not None:
        update_data["observaciones"] = body.observaciones
    
    if update_data:
        service.actualizar_solicitud(db, id_solicitud, update_data)
    data = service.obtener_solicitud(db, id_solicitud)
    return SuccessResponse(message="Solicitud actualizada correctamente", data=data)


@router.delete("/{id_solicitud}", tags=[TAG_SOLICITUDES], response_model=MessageResponse,
               summary="Eliminar solicitud",
               description="Solo elimina solicitudes en etapa ENVIADA, sin niveles aprobados y sin entidades hijas (proyecto, contratacion, entrega, etc.).")
def eliminar_solicitud(id_solicitud: int, db: Session = Depends(get_db),
                       _user=Depends(get_current_user)):
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    if sol["etapa"] != "ENVIADA":
        raise HTTPException(status_code=400, detail="Solo se puede eliminar en etapa ENVIADA")
    service.eliminar_solicitud(db, id_solicitud)
    return {"message": "Solicitud eliminada correctamente", "id": id_solicitud}


@router.get("/{id_solicitud}/checklist", tags=[TAG_SOLICITUDES], response_model=DataListResponse[RequisitoConEstado],
            summary="Checklist de requisitos de la solicitud",
            description="Retorna todos los requisitos de la modalidad de la solicitud, indicando si cada uno está completado (documento subido y valido=TRUE).")
def get_checklist(id_solicitud: int, db: Session = Depends(get_db),
                  _user=Depends(get_current_user)):
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    data = service.get_checklist(db, id_solicitud)
    for r in data:
        r["completado"] = r["id_solicitud_documento"] is not None
    return SuccessResponse(message="Checklist obtenido correctamente", data=data, total=len(data))


@router.post("/{id_solicitud}/documentos", tags=[TAG_SOLICITUDES], status_code=201,
             summary="Subir documento de requisito",
             description="Sube un PDF como documento de un requisito específico. "
                        "Valida: solicitud en ENVIADA (v2.60.0), requisito pertenece a la modalidad y es_documento=true. "
                        "Si ya existe un documento válido para el requisito, lo marca como valido=false (historial).")
async def subir_documento(
    id_solicitud: int,
    file: UploadFile = File(..., description="Archivo PDF (max 50MB)"),
    id_requisito: int = Form(...),
    fecha_documento: str = Form(..., description="YYYY-MM-DD"),
    nombre_documento: str = Form(...),
    observaciones: str | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    from datetime import datetime
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    reqs = service.listar_requisitos(db, sol["id_modalidad"])
    req = next((r for r in reqs if r["id_requisito"] == id_requisito), None)
    if not req:
        raise HTTPException(status_code=400, detail="Requisito no pertenece a la modalidad")
    if not req.get("es_documento", False):
        raise HTTPException(status_code=400, detail="El requisito no es de tipo documento")
    
    subfolder = f"rida/solicitudes/{id_solicitud}"
    path, tamano, hash_sha, _ = await save_documento_pdf(file, db, _user["id_usuario"], subfolder, sol["id_municipio"])
    
    try:
        fecha_dt = datetime.strptime(fecha_documento, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="fecha_documento debe ser YYYY-MM-DD")
    
    id_sd = service.subir_documento_v2(
        db=db, id_solicitud=id_solicitud, id_requisito=id_requisito, id_usuario=_user["id_usuario"],
        path_archivo=path, tamano=tamano, hash_sha=hash_sha, nombre_original=file.filename or "documento.pdf",
        id_tipo_documento=req.get("id_tipo_documento"), id_municipio=sol["id_municipio"],
        id_departamento=sol["id_departamento"], fecha_documento=fecha_dt,
        nombre_documento=nombre_documento, observaciones=observaciones
    )
    data = {"id_solicitud_documento": id_sd, "id_solicitud": id_solicitud, "id_requisito": id_requisito}
    return {"success": True, "message": "Documento subido correctamente", "data": data, "id": id_sd}


@router.get("/{id_solicitud}/documentos", tags=[TAG_SOLICITUDES],
            summary="Listar documentos de la solicitud",
            description="Retorna todos los documentos subidos a la solicitud, con datos del requisito y del archivo físico.")
def listar_documentos(id_solicitud: int,
                      limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
                      skip: int = Query(0, ge=0, description="Registros a saltar"),
                      todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
                      db: Session = Depends(get_db),
                      _user=Depends(get_current_user)):
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    data, total = service.listar_documentos(db, id_solicitud, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Documentos listados correctamente", data=data, total=total)


@router.delete("/{id_solicitud}/documentos/{id_solicitud_documento}", tags=[TAG_SOLICITUDES], response_model=MessageResponse,
               summary="Eliminar documento de solicitud",
               description="Elimina el vínculo solicitud_documento. El archivo físico se elimina opcionalmente (hard delete).")
def eliminar_documento(id_solicitud: int, id_solicitud_documento: int,
                       db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.validar_scope_solicitud(db, _user, id_solicitud)
    docs = service.listar_documentos(db, id_solicitud)[0]
    doc = next((d for d in docs if d["id_solicitud_documento"] == id_solicitud_documento), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    path_archivo = doc.get("path_archivo")
    service.eliminar_documento(db, id_solicitud_documento, path_archivo)
    
    if path_archivo:
        try:
            from ...upload import delete_file_from_server
            delete_file_from_server(path_archivo)
        except Exception:
            pass
    
    return {"message": "Documento eliminado correctamente", "id": id_solicitud_documento}


# ============================================================================
#  MOTOR DE ESTADOS (FASE 1)
# ============================================================================


@router.get("/{id_solicitud}/bitacora", tags=[TAG_SOLICITUDES], response_model=DataListResponse[BitacoraItemResponse],
            summary="Bitácora de la solicitud",
            description="Historial completo de transiciones y acciones sobre la solicitud.")
def get_bitacora(id_solicitud: int,
                 limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
                 skip: int = Query(0, ge=0, description="Registros a saltar"),
                 todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
                 db: Session = Depends(get_db), _user=Depends(get_current_user)):
    sol = service.obtener_solicitud(db, id_solicitud)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    service.validar_scope_solicitud(db, _user, id_solicitud)
    data, total = service.listar_bitacora(db, id_solicitud, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Bitácora obtenida correctamente", data=data, total=total)


DESC_PUT_APROBACION = (
    "Aprueba o devuelve un nivel de la cadena (`validacion` | `viceministro` | `dgea` | "
    "`revision_articulos` | `suministro` | `despacho` | `entrega`). El usuario que aprueba "
    "o devuelve se toma del token JWT, nunca del cuerpo.\n\n"
    "**Content-Type: `multipart/form-data`** (v2.60.0). Campos:\n"
    "- `aprobado` (bool, obligatorio; se acepta el nombre legado `aprobar`).\n"
    "- `observacion` (str; obligatoria al devolver y debe tener al menos "
    f"{service.OBS_MIN_APROBACION} caracteres; se acepta el nombre legado `observaciones`).\n"
    "- `archivo` (PDF, opcional): se registra como documento del requisito "
    "'Informe de validación departamental' de la modalidad. **Obligatorio al aprobar "
    "`validacion`** (el VIDECI Departamental adjunta su informe en el mismo visado).\n"
    "- `nombre_documento` / `fecha_documento` (opcionales, para el registro del informe).\n\n"
    "- `aprobado: true` — secuencia **estricta** (v2.60.0): solo se puede aprobar el "
    "PRIMER nivel no aprobado de la cadena, y la solicitud debe estar en la etapa que ese "
    "nivel exige (`validacion` en `ENVIADA`; `viceministro`/`dgea`/`revision_articulos` en "
    "`EN_APROBACION`; `suministro` en `APROBADA`; `despacho` en `AUTORIZADA`; `entrega` en "
    "`DESPACHADA`).\n"
    "- `aprobado: false` devuelve el nivel ANTERIOR de la cadena a `observado` (guardando "
    "el motivo en su fila) y deja este nivel en `espera_correccion`. Solo puede devolver "
    "quien tiene el turno, y aquí **sí** aplica el orden: solo se devuelve algo que se "
    "aprobó.\n\n"
    "**Gates de negocio** (v2.60.0): aprobar `validacion` exige el checklist de instancia 1 "
    "completo (documentos del UGR) y el informe de validación adjunto; aprobar "
    "`revision_articulos` exige un cálculo operativo persistido cuando la modalidad tiene "
    "motor de cálculo (`tiene_motor_calculo`); aprobar `entrega` cierra la solicitud "
    "automáticamente (`ENTREGADA` → `CERRADA`).\n\n"
    "**Acople motor ↔ etapa**: aprobar `validacion` pasa la solicitud a `EN_APROBACION`; "
    "`revision_articulos` a `APROBADA`; `suministro` a `AUTORIZADA`; `despacho` a "
    "`DESPACHADA`; `entrega` a `ENTREGADA` y luego `CERRADA`. Devolver revierte la etapa a "
    "la que exige el nivel observado.\n\n"
    "| Código | Cuándo |\n"
    "|---|---|\n"
    "| **400** | Nivel fuera de la cadena de la modalidad; devolver desde el primer nivel; "
    "devolver cuando el anterior no está `aprobado`. |\n"
    "| **403** | Rol sin permiso para ese nivel, o alcance (municipio/departamento) fuera "
    "del del usuario. |\n"
    "| **404** | La solicitud no existe. |\n"
    "| **409** | La solicitud no está en la etapa que exige el nivel; la secuencia estricta "
    "no permite aprobar/devolver ese nivel; falta el checklist de instancia 1 o el informe "
    "de validación; la modalidad exige cálculo operativo persistido; la modalidad es Ayuda "
    "Humanitaria (motor propio de 7 niveles). |\n"
    "| **422** | `aprobado` ausente, o `observacion` vacía / con menos de "
    f"{service.OBS_MIN_APROBACION} caracteres. |"
)


@router.get("/{id_solicitud}/aprobacion", tags=[TAG_SOLICITUDES],
            response_model=DataItemResponse[AprobacionesSolicitudResponse],
            summary="Obtener la máquina de aprobaciones de la solicitud",
            description="Vista de la cadena **activa** de esta solicitud: `cadena` resuelta, "
                        "`estado_global` derivado y, por nivel, su estado, la `observacion` de "
                        "devolución, quién y cuándo.\n\n"
                        "Es auto-suficiente: incluye la cadena, así que el frontend no necesita "
                        "el catálogo para pintar el detalle.\n\n"
                        "Cada nivel trae `puede_aprobar` / `puede_devolver` / `es_mio`, ya "
                        "calculados con el rol, el alcance y la etapa del token. **No hay que derivar "
                        "\"quién puede actuar\" de `estado_global`**: es el badge del primer nivel "
                        "no aprobado (EN_VALIDACION → VICEMINISTRO → DGEA → REVISION_ARTICULOS "
                        "→ SUMINISTRO → DESPACHO → EN_ENTREGA; completo = ENTREGADO) y una "
                        "etiqueta de resumen; use `puede_aprobar`.\n\n"
                        "Para la modalidad Ayuda Humanitaria devuelve cadena vacía y "
                        "`estado_global` null (motor propio de 7 niveles).\n\n"
                        "La cabecera completa sigue viniendo de `GET /{id_solicitud}`; este "
                        "endpoint devuelve SOLO la máquina.")
def obtener_aprobacion(id_solicitud: int, db: Session = Depends(get_db),
                       _user=Depends(get_current_user)):
    data = service.get_aprobaciones(db, id_solicitud, user=_user)
    if not data:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return SuccessResponse(message="Aprobaciones de la solicitud obtenidas correctamente", data=data)


@router.put("/{id_solicitud}/aprobacion/{nivel}", tags=[TAG_SOLICITUDES],
            response_model=DataItemResponse[AprobacionesSolicitudResponse],
            summary="Aprobar o devolver un nivel de la cadena",
            description=DESC_PUT_APROBACION)
async def set_aprobacion_nivel(
    id_solicitud: int,
    nivel: str,
    aprobado: bool | None = Form(None),
    observacion: str | None = Form(None),
    aprobar: bool | None = Form(None),
    observaciones: str | None = Form(None),
    archivo: UploadFile | None = File(None),
    nombre_documento: str | None = Form(None),
    fecha_documento: str | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    if nivel not in service.NIVELES_APROB:
        raise HTTPException(status_code=400,
                            detail=f"Nivel inválido. Válidos: {service.NIVELES_APROB}")
    aprobado_final = aprobado if aprobado is not None else aprobar
    if aprobado_final is None:
        raise HTTPException(status_code=422, detail="Debe enviar 'aprobado' (o 'aprobar')")
    obs = observacion if observacion is not None else observaciones
    if aprobado_final:
        informe = None
        if archivo is not None:
            from datetime import datetime
            sol = service.obtener_solicitud(db, id_solicitud)
            if not sol:
                raise HTTPException(status_code=404, detail="Solicitud no encontrada")
            fecha_dt = date.today()
            if fecha_documento:
                try:
                    fecha_dt = datetime.strptime(fecha_documento, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(status_code=400,
                                        detail="fecha_documento debe ser YYYY-MM-DD")
            subfolder = f"rida/solicitudes/{id_solicitud}"
            path, tamano, hash_sha, _ = await save_documento_pdf(
                archivo, db, _user["id_usuario"], subfolder, sol["id_municipio"])
            informe = {
                "path_archivo": path, "tamano": tamano, "hash_sha": hash_sha,
                "nombre_original": archivo.filename or "informe.pdf",
                "fecha_documento": fecha_dt,
                "nombre_documento": nombre_documento or "Informe de validación departamental",
                "observaciones": None,
            }
        data = service.aprobar_nivel(db, id_solicitud, nivel, _user["id_usuario"],
                                     user=_user, informe=informe)
        msg = f"Aprobación {nivel} registrada"
    else:
        data = service.devolver_nivel(db, id_solicitud, nivel, (obs or "").strip(),
                                      _user["id_usuario"], user=_user)
        msg = f"Devolución de {nivel} registrada"
    return SuccessResponse(message=msg, data=data)


@router.post("/{id_solicitud}/rechazar", tags=[TAG_SOLICITUDES], response_model=DataItemResponse[SolicitudResponse],
             summary="Rechazar solicitud (ENVIADA/EN_APROBACION → RECHAZADA)",
             description="Rechaza la solicitud de forma terminal.")
def rechazar(id_solicitud: int, body: TransicionRequest,
             db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.rechazar_solicitud(db, id_solicitud, _user["id_usuario"], body.observaciones, user=_user)
    return SuccessResponse(message="Solicitud rechazada", data=data)
