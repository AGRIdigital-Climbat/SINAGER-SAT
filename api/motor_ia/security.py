import os
import hmac
from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import ENV_FILE

load_dotenv(ENV_FILE)

_API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")

_token_bytes = b""
if _API_AUTH_TOKEN:
    _token_bytes = _API_AUTH_TOKEN.encode("utf-8")

# Esquema visible en Swagger (botón Authorize)
api_key_scheme = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description=(
        "Token de autenticacion (valor de API_AUTH_TOKEN en .env). Se requiere en: "
        "/llm/modo, /llm/uso/resumen, crear/editar/eliminar/probar proveedores, "
        "/verificacion/general y en las operaciones de escritura de "
        "/documentos, /tipos-documento y /grupos. La mayoria de endpoints de "
        "lectura son publicos."
    ),
)


def _token_es_valido(x_api_key) -> bool:
    if not _token_bytes or not x_api_key:
        return False
    try:
        provided = x_api_key.encode("utf-8")
    except Exception:
        return False
    return hmac.compare_digest(provided, _token_bytes)


def _validar_token_api(x_api_key: str = Security(api_key_scheme)):
    """Dependency estricta: exige X-API-Key valido (tiempo constante)."""
    if not _token_bytes:
        raise HTTPException(
            status_code=500,
            detail="API_AUTH_TOKEN no configurado en el servidor.",
        )
    if not _token_es_valido(x_api_key):
        raise HTTPException(status_code=401, detail="Token invalido.")
