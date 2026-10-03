from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_current_user
from ..database import get_db
from ..response import SuccessResponse
from . import service
from ..response import DataItemResponse
from .schemas import AprobacionEdan, AprobacionesEdanResponse

router = APIRouter(prefix="/edan")

TAG_APROB = "EDAN"

DESC_PUT_APROBACION = (
    "Cuerpo: `{\"aprobado\": bool, \"observacion\": str|null}`.\n"
    "- `aprobado: true` aprueba este nivel. Quedan invalidados los niveles siguientes.\n"
    "- `aprobado: false` devuelve el nivel ANTERIOR a `observado` y deja este nivel en\n"
    "  `espera_correccion`. Es obligatorio enviar `observacion` (motivo del rechazo).\n"
    "\n"
    "El usuario que aprueba o devuelve se toma del token JWT, no del cuerpo. La\n"
    "respuesta es el mismo objeto que devuelve el GET, con `usuario_aprobacion` y\n"
    "`usuario_devolucion` ya resueltos."
)


def _ejecutar_aprobacion(db, id, nivel, data, por, _user):
    service.validar_scope_edan(db, _user, id)
    try:
        if data.aprobado:
            return service.aprobar_edan(db, id, nivel, por=por)
        if not (data.observacion and data.observacion.strip()):
            raise HTTPException(status_code=422,
                                detail="Para devolver debe enviar la observacion (motivo del rechazo)")
        return service.devolver_edan(db, id, nivel, data.observacion.strip(), por=por)
    except ValueError as e:
        msg = str(e)
        if msg == "EDAN no encontrado":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.get("/{id}/aprobacion", tags=[TAG_APROB],
            response_model=DataItemResponse[AprobacionesEdanResponse],
            summary="Obtener aprobaciones del EDAN",
            description="Vista informativa del estado actual de la cadena de aprobaciones\n"
                        "(ugr, alcalde, dgr, videcid) + el `estado_global` derivado.\n"
                        "\n"
                        "Cada nivel incluye `estado` y `observacion` (motivo del rechazo),\n"
                        "`rol_aprobador` (a qué rol le corresponde este nivel, dato\n"
                        "informativo: la API NO restringe por rol), y los usuarios anidados\n"
                        "`usuario_aprobacion` / `usuario_devolucion` con sus fechas.\n"
                        "\n"
                        "Los usuarios van embebidos para no pedir llamadas extra al frontend.\n"
                        "API ligera, sin cabecera completa ni localidades. Solo se valida\n"
                        "territorio para 5/8/9.")
def obtener_aprobaciones(id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    service.validar_scope_edan(db, _user, id)
    result = service.get_aprobaciones_edan(db, id)
    if not result:
        raise HTTPException(status_code=404, detail="EDAN no encontrado")
    return SuccessResponse(message="Aprobaciones del EDAN obtenidas correctamente", data=result)


@router.put("/{id}/aprobacion/ugr",
            tags=[TAG_APROB],
            response_model=DataItemResponse[AprobacionesEdanResponse],
            summary="Aprobar o devolver UGR",
            description=DESC_PUT_APROBACION)
def set_aprobacion_ugr(id: int, data: AprobacionEdan, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = _ejecutar_aprobacion(db, id, "ugr", data, _user.get("id_usuario"), _user)
    return SuccessResponse(message="Aprobación UGR actualizada", data=result)


@router.put("/{id}/aprobacion/alcalde",
            tags=[TAG_APROB],
            response_model=DataItemResponse[AprobacionesEdanResponse],
            summary="Aprobar o devolver Alcalde",
            description=DESC_PUT_APROBACION)
def set_aprobacion_alcalde(id: int, data: AprobacionEdan, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = _ejecutar_aprobacion(db, id, "alcalde", data, _user.get("id_usuario"), _user)
    return SuccessResponse(message="Aprobación de alcalde actualizada", data=result)


@router.put("/{id}/aprobacion/dgr",
            tags=[TAG_APROB],
            response_model=DataItemResponse[AprobacionesEdanResponse],
            summary="Aprobar o devolver DGR",
            description=DESC_PUT_APROBACION)
def set_aprobacion_dgr(id: int, data: AprobacionEdan, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = _ejecutar_aprobacion(db, id, "dgr", data, _user.get("id_usuario"), _user)
    return SuccessResponse(message="Aprobación departamental actualizada", data=result)


@router.put("/{id}/aprobacion/videcid",
            tags=[TAG_APROB],
            response_model=DataItemResponse[AprobacionesEdanResponse],
            summary="Aprobar o devolver VIDECID",
            description=DESC_PUT_APROBACION)
def set_aprobacion_videcid(id: int, data: AprobacionEdan, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    result = _ejecutar_aprobacion(db, id, "videcid", data, _user.get("id_usuario"), _user)
    return SuccessResponse(message="Aprobación videcid actualizada", data=result)