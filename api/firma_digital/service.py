import base64
import binascii
import logging
import re
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings

logger = logging.getLogger("firma_digital")

# base64 puro estándar (sin data-URI ni saltos de línea estrictos)
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")


def _max_bytes() -> int:
    return settings.AGETIC_MAX_SIZE_MB * 1024 * 1024


def _validar_base64(value: str) -> bytes:
    """Valida que el string sea base64 y no exceda el límite de AGETIC. Devuelve bytes."""
    if not value or not _BASE64_RE.match(value):
        raise HTTPException(status_code=400, detail="El campo base64 no es válido.")
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="El campo base64 no es válido.")
    if len(data) > _max_bytes():
        raise HTTPException(
            status_code=400,
            detail=f"El archivo excede el límite de {settings.AGETIC_MAX_SIZE_MB} MB que acepta el validador.",
        )
    return data


def _transformar(data: dict) -> dict:
    """Convierte la respuesta nativa de AGETIC al formato de SuccessResponse.data v2.

    AGETIC (actual):
      {tipoRespuesta: "Exito"|"Error", exito: bool, mensaje, objeto: {codigoHash, firmas: [...]}}
    Formato anterior/Jacobitus:
      {finalizado: bool, mensaje, datos: {firmas: [...]}}

    Output: {finalizado, tipoRespuesta, mensaje, codigoHash, firmas, cantidad_firmas}
    """
    objeto = data.get("objeto")
    if not isinstance(objeto, dict):
        objeto = data.get("datos")
    if not isinstance(objeto, dict):
        objeto = {}

    exito = data.get("exito")
    if exito is None:
        exito = bool(data.get("finalizado", data.get("tipoRespuesta") == "Exito"))
    finalizado = bool(exito)
    tipo_respuesta = data.get("tipoRespuesta") or ("Exito" if finalizado else "Error")

    firmas = objeto.get("firmas") or []
    return {
        "finalizado": finalizado,
        "tipoRespuesta": tipo_respuesta,
        "mensaje": data.get("mensaje", ""),
        "codigoHash": objeto.get("codigoHash"),
        "firmas": firmas,
        "cantidad_firmas": len(firmas),
    }


async def validar_pdf(pdf_firmado_base64: str, contrasenia: str | None = None) -> dict:
    """Envía un PDF (base64) al validador de AGETIC y retorna el resultado transformado."""
    _validar_base64(pdf_firmado_base64)

    body: dict = {"pdfFirmadoBase64": pdf_firmado_base64}
    if contrasenia:
        body["contrasenia"] = contrasenia

    url = f"{settings.AGETIC_BASE_URL.rstrip('/')}/validador/pdf"
    async with httpx.AsyncClient(timeout=settings.AGETIC_TIMEOUT) as client:
        response = await client.post(url, json=body)

    if response.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail="El servicio de validación de AGETIC no está disponible. Intente más tarde.",
        )
    try:
        data = response.json()
    except ValueError:
        logger.error(f"AGETIC respuesta no JSON ({response.status_code}): {response.text[:200]}")
        raise HTTPException(status_code=502, detail="Respuesta inválida del servicio de AGETIC.")

    return _transformar(data)


async def validar_pdf_url(url_archivo_firmado: str) -> dict:
    """Reenvía a AGETIC la validación de un PDF accesible por URL pública."""
    if not url_archivo_firmado or not url_archivo_firmado.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Debe enviar una URL válida (http/https).")

    url = f"{settings.AGETIC_BASE_URL.rstrip('/')}/validador/pdf/url"
    async with httpx.AsyncClient(timeout=settings.AGETIC_TIMEOUT) as client:
        response = await client.post(url, json={"urlArchivoFirmado": url_archivo_firmado})

    if response.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail="El servicio de validación de AGETIC no está disponible. Intente más tarde.",
        )
    try:
        data = response.json()
    except ValueError:
        logger.error(f"AGETIC respuesta no JSON ({response.status_code}): {response.text[:200]}")
        raise HTTPException(status_code=502, detail="Respuesta inválida del servicio de AGETIC.")

    return _transformar(data)


# ============================================================================
#  ACCESO A ARCHIVOS DEL REPOSITORIO
# ============================================================================

def _resolver_ruta_fisica(path_archivo: str) -> Path:
    """Convierte el path de BD (/uploads/edan/...) a la ruta física en disco."""
    clean = path_archivo.lstrip("/")
    if clean.startswith("uploads/"):
        clean = clean[len("uploads/"):]
    return Path(settings.UPLOAD_DIR) / clean


def leer_pdf_repositorio(path_archivo: str, tamano_bytes: int | None) -> bytes:
    """Lee un PDF almacenado en el repositorio y valida el límite de AGETIC."""
    if tamano_bytes is not None and tamano_bytes > _max_bytes():
        raise HTTPException(
            status_code=400,
            detail=f"El documento excede el límite de {settings.AGETIC_MAX_SIZE_MB} MB que acepta el validador de AGETIC.",
        )
    filepath = _resolver_ruta_fisica(path_archivo)
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="No se encontró el archivo PDF en el servidor.")
    return filepath.read_bytes()