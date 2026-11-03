"""Router de Ayuda Humanitaria (Work Queue VIDECI).

Prefijo: /ayuda-humanitaria (montado en /api/v2 por main.py).
Contrato: AYUDA_HUMANITARIA_BACKEND.md v1.3.

Orden de rutas: los catalogos (/estados, /aprobacion/cadena, /reglas-calculo)
van ANTES de /expedientes/{id_solicitud}: FastAPI resuelve en orden de
declaracion y un id_solicitud tipado int se llevaria paths genericos.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..response import DataItemResponse, DataListResponse, MessageResponse, SuccessResponse
from ..auth.permisos import module_permiso
from ..edan.utils import require_rol
from . import service
from .schemas import (
    ActaRecepcionCreate, AprobacionAyudaRequest, AprobacionesAyudaResponse,
    ArticuloUpdate, CalculoCabeceraResponse, CalculoDetalleResponse, CalculoRequest,
    CalculoResponse, DespacharRequest, EvaluacionCreate, ExpedienteDetalleResponse,
    ExpedienteResponse, EstadoRidaResponse, MotorCalculoRequest, OrdenDespachoCreate,
    PrepararRequest, PublicarReglaRequest, ReglaCalculoKitCreate,
    ReglaCalculoKitResponse, ReglaCalculoKitUpdate, ReglaValidacionResponse,
    SimulacionReglaRequest, SimulacionReglaResponse, TransicionAyudaRequest,
    ReglaVersionResponse, ReglaNecesidadCreate, ReglaNecesidadUpdate,
    ReglaNecesidadResponse, MotorNecesidadesRequest, MotorNecesidadesResponse,
)

router = APIRouter(
    prefix="/ayuda-humanitaria",
    dependencies=[Depends(module_permiso("RIDA"))],
)

TAG_AYUDA = "RIDA > Ayuda Humanitaria"
ROLES_CONFIG = (1, 2)

# Roles con alcance nacional en el listado; 5/9/14 -> departamento, 8 -> municipio
ROLES_NACIONALES_LISTADO = (1, 2, 3, 4, 6, 7)

DESC_CADENA = (
    "Niveles del motor SECUENCIAL de ayuda humanitaria (pasos 4-9 VIDECI), su "
    "rol, su alcance, la cadena por defecto y las cadenas por modalidad.\n\n"
    "A diferencia del motor de visaciones (cadena no estricta), aqui NO se "
    "puede aprobar un nivel sin que el anterior este aprobado: evaluacion → "
    "determinacion → autorizacion → almacen → despacho → entrega → cierre."
)

DESC_PUT_APROBACION = (
    "Aprueba o devuelve un nivel del motor de ayuda humanitaria. Cuerpo "
    "canonico: `{\"aprobado\": bool, \"observacion\": str}`.\n\n"
    "- **Cadena secuencial**: para aprobar, TODOS los niveles anteriores deben "
    "estar `aprobado` (409 si no).\n"
    "- `aprobado: false` devuelve al nivel ANTERIOR (motivo obligatorio en su "
    "fila, min "
    f"{service.OBS_MIN} caracteres) y deja este nivel en `espera_correccion`.\n"
    "- Al completarse los 7 niveles la solicitud pasa a `CERRADA`.\n\n"
    "| Codigo | Cuando |\n|---|---|\n"
    "| **400** | Nivel fuera de la cadena; devolver desde el primer nivel. |\n"
    "| **403** | Rol/alcance insuficiente para ese nivel. |\n"
    "| **404** | La solicitud no existe. |\n"
    "| **409** | El motor no esta iniciado (etapa EN_APROBACION); el nivel "
    "anterior no esta aprobado. |\n"
    "| **422** | `observacion` vacia o con menos de "
    f"{service.OBS_MIN} caracteres. |"
)


@router.get("/estados", tags=[TAG_AYUDA],
            response_model=DataListResponse[EstadoRidaResponse],
            summary="Badges del Work Queue (cat_estado_rida)")
def listar_estados(db: Session = Depends(get_db)):
    data = service.listar_estados(db)
    return DataListResponse(message="Estados listados correctamente", data=data, total=len(data))


@router.get("/aprobacion/cadena", tags=[TAG_AYUDA],
            summary="Niveles, roles, alcance y cadenas del motor",
            description=DESC_CADENA)
def listar_cadena(db: Session = Depends(get_db)):
    return DataItemResponse(message="Cadena obtenida correctamente", data=service.listar_cadena(db))


# ---------------------------------------------------------------------------
#  Reglas del motor de calculo por KITS (dinamico, §2.6): catalogo -> COMPLETO
# ---------------------------------------------------------------------------

@router.get("/reglas-calculo", tags=[TAG_AYUDA],
            response_model=DataListResponse[ReglaCalculoKitResponse],
            summary="Reglas del motor (kits) — completo, sin paginar")
def listar_reglas(
    id_articulo: int | None = Query(None, description="Filtrar por artículo del kit"),
    criterio_aplicacion: str | None = Query(
        None, description="POR_FAMILIA | POR_INTEGRANTE | POR_CONDICION_ESPECIAL"),
    estado: str | None = Query(
        None, description="Filtrar por estado del ciclo de vida: borrador | publicada"),
    db: Session = Depends(get_db),
):
    data = service.listar_reglas(db, id_articulo, criterio_aplicacion, estado=estado)
    return DataListResponse(message="Reglas listadas correctamente", data=data, total=len(data))


@router.post("/reglas-calculo", tags=[TAG_AYUDA], status_code=201,
             response_model=DataItemResponse[ReglaCalculoKitResponse],
             dependencies=[Depends(require_rol(*ROLES_CONFIG))],
             summary="Crear regla (kit) de cálculo")
def crear_regla(body: ReglaCalculoKitCreate, db: Session = Depends(get_db),
                _user=Depends(get_current_user)):
    return DataItemResponse(message="Regla creada correctamente",
                            data=service.crear_regla(db, body))


@router.put("/reglas-calculo/{id_regla}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[ReglaCalculoKitResponse],
            dependencies=[Depends(require_rol(*ROLES_CONFIG))],
            summary="Actualizar regla (kit) de cálculo")
def actualizar_regla(id_regla: int, body: ReglaCalculoKitUpdate,
                     db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return DataItemResponse(message="Regla actualizada correctamente",
                            data=service.actualizar_regla(db, id_regla, body))


@router.delete("/reglas-calculo/{id_regla}", tags=[TAG_AYUDA],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_CONFIG))],
               summary="Eliminar regla de cálculo",
               description="409 si la regla ya generó artículos: desactivarla (activo=false).")
def eliminar_regla(id_regla: int, db: Session = Depends(get_db),
                   _user=Depends(get_current_user)):
    service.eliminar_regla(db, id_regla)
    return MessageResponse(message="Regla eliminada correctamente", id=id_regla)


@router.get("/reglas-calculo/{id_regla}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[ReglaCalculoKitResponse],
            summary="Consultar una regla (kit) con su estado y versión")
def get_regla(id_regla: int, db: Session = Depends(get_db)):
    return DataItemResponse(message="Regla consultada correctamente",
                            data=service.get_regla(db, id_regla))


@router.post("/reglas-calculo/{id_regla}/validar", tags=[TAG_AYUDA],
             response_model=DataItemResponse[ReglaValidacionResponse],
             summary="Validar estructura y parámetros de la regla (sin publicar)",
             description="Corre las validaciones completas (nombre, artículos "
                         "habilitados, criterios, rangos) SIN modificar nada. "
                         "200 si es válida; **422** con `{valida:false, errores[], "
                         "advertencias[], resumen{}}` si no lo es.")
def validar_regla(id_regla: int, db: Session = Depends(get_db),
                  _user=Depends(get_current_user)):
    return DataItemResponse(message="Regla validada correctamente",
                            data=service.validar_regla(db, id_regla))


@router.post("/reglas-calculo/{id_regla}/simular", tags=[TAG_AYUDA],
             response_model=DataItemResponse[SimulacionReglaResponse],
             summary="Probar la fórmula de la regla sin registrar nada",
             description="Ejecuta la fórmula del kit con una población sintética "
                         "(default 1 familia/integrante) y parámetros opcionales. "
                         "NO persiste: no crea necesidades, no reserva existencias "
                         "ni genera salidas de almacén.")
def simular_regla(id_regla: int, body: SimulacionReglaRequest | None = None,
                  db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return DataItemResponse(message="Simulación ejecutada",
                            data=service.simular_regla(db, id_regla, body))


@router.post("/reglas-calculo/{id_regla}/publicar", tags=[TAG_AYUDA],
             response_model=DataItemResponse[dict],
             dependencies=[Depends(require_rol(*ROLES_CONFIG))],
             summary="Publicar una versión validada de la regla",
             description="Solo roles 1,2. Exige `{\"confirmar\": true}` y que la "
                         "regla valide (422 si no). Crea una versión inmutable "
                         "(snapshot JSONB) y habilita la regla para el motor. "
                         "Editar una regla publicada la devuelve a borrador: hay "
                         "que publicar de nuevo (nueva versión) para que el motor "
                         "use los cambios.")
def publicar_regla(id_regla: int, body: PublicarReglaRequest,
                   db: Session = Depends(get_db), _user=Depends(get_current_user)):
    user = _user
    return DataItemResponse(
        message="Regla publicada correctamente",
        data=service.publicar_regla(db, id_regla, body,
                                    user.get("id_usuario") if user else None))


@router.get("/reglas-calculo/{id_regla}/versiones", tags=[TAG_AYUDA],
            response_model=DataListResponse[ReglaVersionResponse],
            summary="Versiones publicadas de la regla (la más reciente primero)",
            description="Cada publicación guarda la configuración exacta "
                        "(JSONB) para reproducir cálculos históricos.")
def listar_versiones(id_regla: int, db: Session = Depends(get_db)):
    data = service.listar_versiones(db, id_regla)
    return DataListResponse(message="Versiones listadas correctamente",
                            data=data, total=len(data))


# ---------------------------------------------------------------------------
#  Reglas del motor de NECESIDADES (v2.61.0): catalogo -> COMPLETO
# ---------------------------------------------------------------------------

@router.get("/reglas-necesidad", tags=[TAG_AYUDA],
            response_model=DataListResponse[ReglaNecesidadResponse],
            summary="Reglas del motor de necesidades — completo, sin paginar")
def listar_reglas_necesidad(
    activo: bool | None = Query(None, description="Filtrar por activo"),
    criterio_aplicacion: str | None = Query(
        None, description="POR_FAMILIA | POR_INTEGRANTE | POR_CONDICION_ESPECIAL"),
    id_categoria_ayuda: int | None = Query(None, description="Filtrar por categoría"),
    db: Session = Depends(get_db),
):
    data = service.listar_reglas_necesidad(
        db, activo=activo, criterio_aplicacion=criterio_aplicacion,
        id_categoria_ayuda=id_categoria_ayuda)
    return DataListResponse(message="Reglas de necesidad listadas correctamente",
                            data=data, total=len(data))


@router.post("/reglas-necesidad", tags=[TAG_AYUDA], status_code=201,
             response_model=DataItemResponse[ReglaNecesidadResponse],
             dependencies=[Depends(require_rol(*ROLES_CONFIG))],
             summary="Crear regla de necesidad")
def crear_regla_necesidad(body: ReglaNecesidadCreate,
                          db: Session = Depends(get_db),
                          _user=Depends(get_current_user)):
    return DataItemResponse(message="Regla de necesidad creada correctamente",
                            data=service.crear_regla_necesidad(db, body))


@router.get("/reglas-necesidad/{id_regla_necesidad}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[ReglaNecesidadResponse],
            summary="Consultar una regla de necesidad")
def get_regla_necesidad(id_regla_necesidad: int, db: Session = Depends(get_db)):
    return DataItemResponse(
        message="Regla de necesidad consultada correctamente",
        data=service.get_regla_necesidad(db, id_regla_necesidad))


@router.put("/reglas-necesidad/{id_regla_necesidad}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[ReglaNecesidadResponse],
            dependencies=[Depends(require_rol(*ROLES_CONFIG))],
            summary="Actualizar regla de necesidad")
def actualizar_regla_necesidad(id_regla_necesidad: int,
                               body: ReglaNecesidadUpdate,
                               db: Session = Depends(get_db),
                               _user=Depends(get_current_user)):
    return DataItemResponse(
        message="Regla de necesidad actualizada correctamente",
        data=service.actualizar_regla_necesidad(db, id_regla_necesidad, body))


@router.delete("/reglas-necesidad/{id_regla_necesidad}", tags=[TAG_AYUDA],
               response_model=MessageResponse,
               dependencies=[Depends(require_rol(*ROLES_CONFIG))],
               summary="Eliminar regla de necesidad",
               description="409 si la regla ya generó necesidades: desactivarla "
                           "(activo=false).")
def eliminar_regla_necesidad(id_regla_necesidad: int,
                             db: Session = Depends(get_db),
                             _user=Depends(get_current_user)):
    service.eliminar_regla_necesidad(db, id_regla_necesidad)
    return MessageResponse(message="Regla de necesidad eliminada correctamente",
                           id=id_regla_necesidad)


@router.post("/calculos", tags=[TAG_AYUDA],
             response_model=DataItemResponse[CalculoResponse],
             summary="Ejecutar el motor de cálculo (previsualizacion | operativo)",
             description=(
                 "Contrato v2.58.0. Ejecuta los kits publicados sobre las familias "
                 "del expediente.\n\n"
                 "- `modo: previsualizacion` (default): calcula y devuelve "
                 "`resultados` POR FAMILIA + totales en `articulos`; **no persiste** "
                 "ni deja historial (`calculo_id: null`).\n"
                 "- `modo: operativo`: exige etapa EN_APROBACION (409 si no), hace "
                 "el upsert de `solicitud_articulo` (mismas reglas: manual no se "
                 "pisa salvo `forzar`) y registra la ejecución con su `calculo_id`.\n"
                 "- `familias[]`: subset para previsualizacion (404 si alguna no "
                 "pertenece al evento; en operativo no se admite).\n"
                 "- `reglas[]`: subset por `{id_regla, numero_version?}`; la "
                 "versión pedida se ejecuta desde su snapshot (404/409 si no "
                 "existe o está en borrador). Omitir = todas las publicadas y activas.\n\n"
                 "El inventario NO interviene en la fórmula: primero se calculan y "
                 "validan las necesidades; la disponibilidad se comprueba después "
                 "de la aprobación (`inventario_consultado: false`)."))
def crear_calculo(body: CalculoRequest, db: Session = Depends(get_db),
                  _user=Depends(get_current_user)):
    return DataItemResponse(message="Cálculo ejecutado",
                            data=service.crear_calculo(db, body, _user))


@router.get("/calculos", tags=[TAG_AYUDA],
            response_model=DataListResponse[CalculoCabeceraResponse],
            summary="Historial de ejecuciones de un expediente (recientes primero)")
def listar_calculos(
    id_solicitud: int = Query(..., description="Expediente del historial"),
    limit: int = Query(100, ge=1, le=500,
                       description="Cantidad a devolver (las más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todas sin paginar"),
    db: Session = Depends(get_db), _user=Depends(get_current_user),
):
    """Historial de ejecuciones del motor para un expediente.

    - `limit`: cantidad; siempre entrega las más recientes primero.
    - `todos=true`: ignora `limit`/`skip` y devuelve el conjunto completo.
    - `skip`: offset, sólo tiene sentido junto a `limit`.
    """
    data, total = service.listar_calculos(db, id_solicitud, _user,
                                          limit=limit, skip=skip, todos=todos)
    return DataListResponse(message="Ejecuciones listadas correctamente",
                            data=data, total=total)


@router.get("/calculos/{id_calculo}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[CalculoCabeceraResponse],
            summary="Consultar una ejecución del motor")
def get_calculo(id_calculo: UUID, db: Session = Depends(get_db),
                _user=Depends(get_current_user)):
    return DataItemResponse(message="Ejecución consultada correctamente",
                            data=service.get_calculo(db, id_calculo, _user))


@router.get("/calculos/{id_calculo}/detalle", tags=[TAG_AYUDA],
            response_model=DataListResponse[CalculoDetalleResponse],
            summary="Resultados de la ejecución por familia y artículo")
def get_calculo_detalle(id_calculo: UUID, db: Session = Depends(get_db),
                        _user=Depends(get_current_user)):
    data = service.get_calculo_detalle(db, id_calculo, _user)
    return DataListResponse(message="Detalle de la ejecución",
                            data=data, total=len(data))


# ---------------------------------------------------------------------------
#  Work Queue
# ---------------------------------------------------------------------------

@router.get("/expedientes", tags=[TAG_AYUDA],
            response_model=DataListResponse[ExpedienteResponse],
            summary="Work Queue: expedientes de ayuda humanitaria (los más recientes primero)",
            description="Lista solicitudes desde ENVIADA en adelante (etapas de la cola "
                        "VIDECI). Los campos `estado` (badge), `dias_en_estado`, "
                        "`nombre_tecnico` y `tiene_motor` se **derivan del motor** en cada "
                        "lectura (regla 3): no son columnas.\n\n"
                        "- `limit`: cantidad a devolver (los más recientes primero).\n"
                        "- `skip`: desplazamiento.\n"
                        "- `todos=true`: devuelve todo sin paginar (lotes/KPIs).\n"
                        "- `estado`: código de `cat_estado_rida` (derivado).\n"
                        "- `q`: búsqueda por código RIDA o municipio.")
def listar_expedientes(
    estado: str | None = Query(None, description="Código de cat_estado_rida (ej. EN_APROBACION)"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_modalidad: int | None = Query(None, description="Filtrar por modalidad"),
    tipo_evento: str | None = Query(None, description="Filtrar por tipo de evento (texto)"),
    fecha_desde: str | None = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str | None = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    q: str | None = Query(None, description="Código RIDA o nombre de municipio"),
    skip: int = Query(0, ge=0, description="Desplazamiento"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad (los más recientes primero)"),
    todos: bool = Query(False, description="Devolver todos sin paginar"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    filtros = {k: v for k, v in {
        "estado": estado, "id_municipio": id_municipio, "id_departamento": id_departamento,
        "id_modalidad": id_modalidad, "tipo_evento": tipo_evento,
        "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta, "q": q,
    }.items() if v is not None}
    user_scope: dict = {}
    rol = _user.get("id_rol")
    if rol == 8 and _user.get("id_municipio"):
        user_scope["id_municipio"] = _user["id_municipio"]
    elif rol in (5, 9, 14) and _user.get("id_departamento"):
        user_scope["id_departamento"] = _user["id_departamento"]
    data, total = service.listar_expedientes(db, filtros, skip, limit, todos, user_scope)
    return DataListResponse(message="Expedientes listados correctamente", data=data, total=total)


@router.post("/expedientes/{id_solicitud}/iniciar", tags=[TAG_AYUDA],
             response_model=DataItemResponse[AprobacionesAyudaResponse],
             summary="Iniciar el motor (ENVIADA → EN_APROBACION, regla 0)",
             description="Crea una fila `pendiente` por cada nivel de la cadena activa y "
                         "avanza la solicitud a EN_APROBACION. Idempotente si ya está "
                         "iniciado. Requiere etapa ENVIADA (v2.60.0) y el checklist de "
                         "instancia 1 completo (409 si no).")
def iniciar_motor(id_solicitud: int, body: TransicionAyudaRequest | None = None,
                  db: Session = Depends(get_db), _user=Depends(get_current_user)):
    obs = body.observaciones if body else None
    data = service.iniciar_motor(db, id_solicitud, _user["id_usuario"], _user, obs)
    return DataItemResponse(message="Motor de ayuda humanitaria iniciado", data=data)


@router.get("/expedientes/{id_solicitud}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[ExpedienteDetalleResponse],
            summary="Detalle del expediente (Maestro-Detalle)",
            description="Cabecera + derivados + máquina de aprobaciones + evaluación + "
                        "artículos del motor + orden de despacho + acta + documentos del "
                        "evento RIDA (repositorio, **solo lectura**).")
def get_expediente(id_solicitud: int, db: Session = Depends(get_db),
                   _user=Depends(get_current_user)):
    data = service.get_expediente(db, id_solicitud, _user)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return DataItemResponse(message="Expediente obtenido correctamente", data=data)


# ---------------------------------------------------------------------------
#  Motor de aprobaciones
# ---------------------------------------------------------------------------

@router.get("/expedientes/{id_solicitud}/aprobacion", tags=[TAG_AYUDA],
            response_model=DataItemResponse[AprobacionesAyudaResponse],
            summary="Máquina de aprobaciones del expediente",
            description="Cadena resuelta, `estado_global` (badge derivado) y por nivel: "
                        "estado, observacion, por/fecha, `puede_aprobar`, `puede_devolver` "
                        "y `es_mio` ya calculados con el rol y alcance del token.")
def get_aprobacion(id_solicitud: int, db: Session = Depends(get_db),
                   _user=Depends(get_current_user)):
    data = service.get_aprobaciones(db, id_solicitud, _user)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return DataItemResponse(message="Aprobaciones obtenidas correctamente", data=data)


@router.put("/expedientes/{id_solicitud}/aprobacion/{nivel}", tags=[TAG_AYUDA],
            response_model=DataItemResponse[AprobacionesAyudaResponse],
            summary="Aprobar o devolver un nivel",
            description=DESC_PUT_APROBACION)
def set_aprobacion_nivel(id_solicitud: int, nivel: str, body: AprobacionAyudaRequest,
                         db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if body.aprobado:
        data = service.aprobar_nivel(db, id_solicitud, nivel, _user["id_usuario"], _user)
        msg = f"Aprobación {nivel} registrada"
    else:
        data = service.devolver_nivel(db, id_solicitud, nivel, body.observacion or "",
                                      _user["id_usuario"], _user)
        msg = f"Devolución de {nivel} registrada"
    return DataItemResponse(message=msg, data=data)


# ---------------------------------------------------------------------------
#  Acciones de paso (cada una aprueba su nivel, §5.4)
# ---------------------------------------------------------------------------

@router.post("/expedientes/{id_solicitud}/evaluacion", tags=[TAG_AYUDA],
             response_model=DataItemResponse[AprobacionesAyudaResponse],
             summary="Paso 4: guardar evaluación nacional + aprobar 'evaluacion'")
def guardar_evaluacion(id_solicitud: int, body: EvaluacionCreate,
                       db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.guardar_evaluacion(db, id_solicitud, _user["id_usuario"], body, _user)
    return DataItemResponse(message="Evaluación registrada", data=data)


@router.post("/expedientes/{id_solicitud}/motor-calculo/preview", tags=[TAG_AYUDA],
             summary="Paso 5 (vista dinámica): ejecutar kits SIN persistir",
             description="Ejecuta los kits activos de `regla_calculo_kit` contra la "
                         "población del expediente y devuelve el resultado calculado "
                         "(una fila por DETALLE en `calculados` y el total por artículo "
                         "en `articulos`). No escribe nada: es la vista previa del frontend.")
def preview_motor(id_solicitud: int, db: Session = Depends(get_db),
                  _user=Depends(get_current_user)):
    return {"success": True, "message": "Cálculo previsualizado",
            "data": service.ejecutar_motor_calculo(db, id_solicitud, _user, persistir=False)}


@router.post("/expedientes/{id_solicitud}/motor-calculo", tags=[TAG_AYUDA],
             summary="Paso 5: ejecutar motor (kits) + poblar solicitud_articulo",
             description="Ejecuta los kits, SUMA las cantidades por artículo y hace "
                         "upsert en `solicitud_articulo` con `fuente='motor'`. Las "
                         "filas `fuente='manual'` NO se tocan salvo `{\"forzar\": true}`. "
                         "No aprueba nivel.")
def ejecutar_motor(id_solicitud: int, body: MotorCalculoRequest | None = None,
                   db: Session = Depends(get_db), _user=Depends(get_current_user)):
    forzar = body.forzar if body else False
    return {"success": True, "message": "Motor de cálculo ejecutado",
            "data": service.ejecutar_motor_calculo(db, id_solicitud, _user, forzar, True)}


@router.post("/expedientes/{id_solicitud}/motor-necesidades/preview", tags=[TAG_AYUDA],
             response_model=DataItemResponse[MotorNecesidadesResponse],
             summary="Motor de necesidades (vista previa): calcular SIN persistir",
             description="Evalúa las reglas ACTIVAS de `regla_necesidad` contra la "
                         "población del expediente y devuelve una fila por familia y "
                         "artículo (`ceil(cantidad_base × días × población_familia)`). "
                         "No escribe nada.")
def preview_motor_necesidades(id_solicitud: int, db: Session = Depends(get_db),
                              _user=Depends(get_current_user)):
    return DataItemResponse(
        message="Necesidades previsualizadas",
        data=service.preview_motor_necesidades(db, id_solicitud, _user))


@router.post("/expedientes/{id_solicitud}/motor-necesidades", tags=[TAG_AYUDA],
             response_model=DataItemResponse[MotorNecesidadesResponse],
             summary="Motor de necesidades: calcular y persistir",
             description="Calcula y persiste en `rida.necesidad` con `fuente='motor'`. "
                         "El motor manda: reemplaza las necesidades manuales de las "
                         "categorías que cubre para cada familia y las filas de motor "
                         "previas del evento. Requiere etapa ENVIADA o EN_APROBACION "
                         "(409 si no). `forzar` se acepta por contrato y no cambia la "
                         "semántica: el motor siempre sobrescribe.")
def ejecutar_motor_necesidades(id_solicitud: int,
                               body: MotorNecesidadesRequest | None = None,
                               db: Session = Depends(get_db),
                               _user=Depends(get_current_user)):
    return DataItemResponse(
        message="Motor de necesidades ejecutado",
        data=service.ejecutar_motor_necesidades(db, id_solicitud, _user))


@router.put("/expedientes/{id_solicitud}/articulos/{id_articulo}", tags=[TAG_AYUDA],
            summary="Paso 5: ajuste manual de un artículo",
            description="Ajusta cantidad/aprobado/observaciones y marca la fila como "
                        "`fuente='manual'` (el motor ya no la pisa salvo forzar). "
                        "Si la fila no existe, la crea.")
def actualizar_articulo(id_solicitud: int, id_articulo: int, body: ArticuloUpdate,
                        db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.actualizar_articulo(db, id_solicitud, id_articulo, body, _user)
    return {"success": True, "message": "Artículo actualizado", "data": data}


@router.post("/expedientes/{id_solicitud}/autorizar", tags=[TAG_AYUDA],
             response_model=DataItemResponse[AprobacionesAyudaResponse],
             summary="Paso 6: autorizar (aprueba 'autorizacion')")
def autorizar(id_solicitud: int, body: TransicionAyudaRequest | None = None,
              db: Session = Depends(get_db), _user=Depends(get_current_user)):
    data = service.autorizar_ayuda(db, id_solicitud, _user["id_usuario"], _user)
    return DataItemResponse(message="Expediente autorizado", data=data)


@router.post("/expedientes/{id_solicitud}/rechazar", tags=[TAG_AYUDA],
             summary="Rechazar expediente (ENVIADA/EN_APROBACION → RECHAZADA)",
             description="Terminal: congela las filas del motor y la etapa pasa a "
                         "RECHAZADA (badge RECHAZADA derivado).")
def rechazar(id_solicitud: int, body: TransicionAyudaRequest | None = None,
             db: Session = Depends(get_db), _user=Depends(get_current_user)):
    obs = body.observaciones if body else None
    data = service.rechazar_ayuda(db, id_solicitud, _user["id_usuario"], _user, obs)
    return {"success": True, "message": "Expediente rechazado", "data": data}


@router.post("/expedientes/{id_solicitud}/orden-despacho", tags=[TAG_AYUDA], status_code=201,
             summary="Paso 7: generar orden de despacho (rida.entrega) + aprobar 'almacen'",
             description="Crea una fila en `rida.entrega` (tipo AYUDA_HUMANITARIA) con "
                         "`nro_orden` OD-<año>-<NNNN> y `estado_despacho=GENERADA`; la "
                         "`serie` (artículos) va a `rida.entrega_detalle`. Aprueba "
                         "'almacen'. 409 si ya existe una orden.")
def generar_orden(id_solicitud: int, body: OrdenDespachoCreate | None = None,
                  db: Session = Depends(get_db), _user=Depends(get_current_user)):
    from .schemas import OrdenDespachoCreate as _ODC
    data = service.generar_orden_despacho(db, id_solicitud, _user["id_usuario"],
                                          body or _ODC(), _user)
    return {"success": True, "message": "Orden de despacho generada", "data": data}


@router.get("/expedientes/{id_solicitud}/orden-despacho", tags=[TAG_AYUDA],
            summary="Paso 7: leer la orden de despacho (+ detalle de artículos)")
def get_orden(id_solicitud: int, db: Session = Depends(get_db),
              _user=Depends(get_current_user)):
    data = service.get_orden_despacho(db, id_solicitud)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="El expediente no tiene orden de despacho")
    return {"success": True, "message": "Orden obtenida", "data": data}


@router.post("/expedientes/{id_solicitud}/preparar", tags=[TAG_AYUDA],
             summary="Paso 7: preparar (estado_despacho → EN_PREPARACION/PREPARADA)")
def preparar(id_solicitud: int, body: PrepararRequest | None = None,
             db: Session = Depends(get_db), _user=Depends(get_current_user)):
    from .schemas import PrepararRequest as _PR
    data = service.preparar_orden(db, id_solicitud, body or _PR(), _user)
    return {"success": True, "message": "Orden actualizada", "data": data}


@router.post("/expedientes/{id_solicitud}/despachar", tags=[TAG_AYUDA],
             summary="Paso 7: despachar (estado_despacho=DESPACHADA + aprueba 'despacho')")
def despachar(id_solicitud: int, body: DespacharRequest | None = None,
              db: Session = Depends(get_db), _user=Depends(get_current_user)):
    from .schemas import DespacharRequest as _DR
    data = service.despachar_orden(db, id_solicitud, _user["id_usuario"],
                                   body or _DR(), _user)
    return DataItemResponse(message="Despacho registrado", data=data)


@router.post("/expedientes/{id_solicitud}/acta-recepcion", tags=[TAG_AYUDA],
             summary="Paso 8: registrar acta de recepción + aprobar 'entrega'",
             description="Guarda `firmas` (JSONB), `id_documento` (PDF del acta en el "
                         "repositorio) y `observaciones_acta` en la fila de la orden. "
                         "Aprueba 'entrega'.")
def registrar_acta(id_solicitud: int, body: ActaRecepcionCreate | None = None,
                   db: Session = Depends(get_db), _user=Depends(get_current_user)):
    from .schemas import ActaRecepcionCreate as _ARC
    data = service.registrar_acta(db, id_solicitud, _user["id_usuario"],
                                  body or _ARC(), _user)
    return DataItemResponse(message="Acta de recepción registrada", data=data)


@router.post("/expedientes/{id_solicitud}/cerrar", tags=[TAG_AYUDA],
             response_model=DataItemResponse[AprobacionesAyudaResponse],
             summary="Paso 9: cerrar (aprueba 'cierre' → solicitud CERRADA)")
def cerrar(id_solicitud: int, body: TransicionAyudaRequest | None = None,
           db: Session = Depends(get_db), _user=Depends(get_current_user)):
    obs = body.observaciones if body else None
    data = service.cerrar_ayuda(db, id_solicitud, _user["id_usuario"], _user, obs)
    return DataItemResponse(message="Expediente cerrado", data=data)
