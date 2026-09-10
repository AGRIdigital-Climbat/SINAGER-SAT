from pydantic import BaseModel, Field


# ============================================================================
#  SOLICITUDES
# ============================================================================

class ValidarPdfRequest(BaseModel):
    """Cuerpo para validar un PDF enviado como base64 (proxy AGETIC /validador/pdf)."""
    pdfFirmadoBase64: str = Field(
        ..., description="PDF en base64 PURO (sin prefijo data:). Máx 20 MB.",
    )
    contrasenia: str | None = Field(
        None, description="Contraseña si el PDF está protegido. Opcional.",
    )


class ValidarPdfUrlRequest(BaseModel):
    """Cuerpo para validar un PDF desde una URL pública (proxy AGETIC /validador/pdf/url)."""
    urlArchivoFirmado: str = Field(..., description="URL pública del PDF firmado a validar.")


# ============================================================================
#  RESPUESTAS (modelos documentales; la API devuelve SuccessResponse con data)
# ============================================================================

class CertificadoDto(BaseModel):
    """Certificado digital del firmante (respuesta AGETIC)."""
    ci: str | None = None
    nombreSignatario: str | None = None
    cargoSignatario: str | None = None
    organizacionSignatario: str | None = None
    emailSignatario: str | None = None
    nombreECA: str | None = None
    descripcionECA: str | None = None
    inicioValidez: str | None = None
    finValidez: str | None = None
    revocado: str | None = None


class FirmaDto(BaseModel):
    """Estado de validación de una firma digital (respuesta AGETIC)."""
    noModificado: bool | None = None
    cadenaConfianza: bool | None = None
    firmadoDuranteVigencia: bool | None = None
    firmadoAntesRevocacion: bool | None = None
    timeStamp: bool | None = None
    fechaFirma: str | None = None
    certificado: CertificadoDto | None = None


class ResultadoValidacion(BaseModel):
    """Resultado de validación (AGETIC `datos`) expuesto en SuccessResponse.data."""
    finalizado: bool
    mensaje: str
    tipoRespuesta: str
    firmas: list[FirmaDto] = []
    cantidad_firmas: int = 0