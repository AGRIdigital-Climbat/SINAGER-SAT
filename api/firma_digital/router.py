import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..response import SuccessResponse
from ..repositorio import service as repositorio_service
from . import service
from .schemas import ValidarPdfRequest, ValidarPdfUrlRequest


router = APIRouter(
    prefix="/firma-digital",
    dependencies=[Depends(module_permiso("REPOSITORIO"))],
)

TAG = "Repositorio > Documentos"


@router.post("/validar-pdf", tags=[TAG],
             summary="Validar firma digital de un PDF (base64)",
             description="Proxy a AGETIC. Recibe el PDF en base64 puro (sin prefijo data:) "
                         "y devuelve el detalle de las firmas digitales.\n\n"
                         "Requerido: `pdfFirmadoBase64`. Opcional: `contrasenia` para PDFs protegidos.\n\n"
                         "Límite: 20 MB (límite de AGETIC). Requiere permiso REPOSITORIO (CREATE).")
async def validar_pdf(payload: ValidarPdfRequest, _user=Depends(get_current_user)):
    resultado = await service.validar_pdf(
        payload.pdfFirmadoBase64,
        payload.contrasenia,
    )
    return SuccessResponse(
        message=resultado["mensaje"] or "Validación completada.",
        data=resultado,
    )


@router.post("/validar-pdf-url", tags=[TAG],
             summary="Validar firma digital de un PDF accesible por URL",
             description="Proxy a AGETIC. Recibe `urlArchivoFirmado` y valida el PDF "
                         "alojado en esa URL pública.\n\n"
                         "Requiere permiso REPOSITORIO (CREATE).")
async def validar_pdf_url(
    payload: ValidarPdfUrlRequest,
    _user=Depends(get_current_user),
):
    resultado = await service.validar_pdf_url(payload.urlArchivoFirmado)
    return SuccessResponse(
        message=resultado["mensaje"] or "Validación completada.",
        data=resultado,
    )


@router.post("/documento/{id_documento}/validar", tags=[TAG],
             summary="Validar firma digital de un PDF del repositorio (sin guardar)",
             description="Lee el PDF de `repositorio.documentos`, lo envía a AGETIC y devuelve el "
                         "detalle de su firma digital **sin modificar la base de datos**.\n\n"
                         "Sirve para re-validar un documento ya subido y revisar su resultado "
                         "sin sobreescribir los metadatos guardados en la subida.\n\n"
                         "Rechaza documentos > 20 MB. Requiere permiso REPOSITORIO (CREATE).")
async def validar_documento_repositorio(
    id_documento: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    doc = repositorio_service.get_documento(db, id_documento)
    if not doc or not doc["activo"]:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    contenido = service.leer_pdf_repositorio(doc["path_archivo"], doc.get("tamano_bytes"))
    pdf_base64 = base64.b64encode(contenido).decode("ascii")

    resultado = await service.validar_pdf(pdf_base64)

    return SuccessResponse(
        message=resultado["mensaje"] or "Validación completada.",
        data={
            "id_documento": id_documento,
            "tiene_firma_digital": bool(resultado["cantidad_firmas"] > 0),
            "guardado_en_bd": False,
            "validacion": resultado,
        },
    )