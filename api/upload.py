import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .dependencies import get_current_user
from .response import SuccessResponse

router = APIRouter(prefix="/upload", tags=["Upload"])

# Extensiones de imagen admitidas. El formato real SIEMPRE se decide por magic
# bytes (ver detect_image_ext), nunca por el content-type que declare el
# cliente: hay navegantes/sistemas que mandan "image/jpg" o
# "application/octet-stream" para archivos que igual son JPEG válidos.
IMAGE_EXTENSIONS = (".jpg", ".png", ".webp", ".gif", ".bmp", ".tif", ".heic", ".heif", ".avif")
MAX_SIZE = 10 * 1024 * 1024  # 10 MB

_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis"}
_HEIF_BRANDS = {b"mif1", b"msf1"}
_AVIF_BRANDS = {b"avif", b"avis"}


def detect_image_ext(contents: bytes) -> str | None:
    """Identifica el formato real de la imagen por magic bytes (None si no es imagen)."""
    if contents[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if contents[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if contents[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if len(contents) >= 12 and contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return ".webp"
    if contents[:2] == b"BM":
        return ".bmp"
    if contents[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif"
    if len(contents) >= 12 and contents[4:8] == b"ftyp":
        brand = contents[8:12]
        if brand in _HEIC_BRANDS:
            return ".heic"
        if brand in _HEIF_BRANDS:
            return ".heif"
        if brand in _AVIF_BRANDS:
            return ".avif"
    return None


def _sanitize_filename(filename: str) -> str:
    """Deja un nombre de archivo 100% seguro (sin rutas ni caracteres raros)."""
    safe = (
        filename.replace(" ", "_")
        .replace("/", "_").replace("\\", "_")
        .replace(":", "_").replace("*", "_")
        .replace("?", "_").replace('"', "_")
        .replace("<", "_").replace(">", "_")
        .replace("|", "_")
        .replace("\x00", "")
    )
    # Quitar cualquier carácter fuera de ASCII imprimible (tildes, ñ, etc.)
    safe = "".join(c if 32 <= ord(c) < 127 else "_" for c in safe)
    return safe[:120] or "archivo"


def _get_municipio_codigo(db: Session, id_municipio: int) -> str:
    from sqlalchemy import text
    row = db.execute(
        text("SELECT codigo_ine FROM shared.municipio WHERE id = :id"),
        {"id": id_municipio},
    ).mappings().first()
    return row["codigo_ine"] if row else "000000"


async def save_upload_file(
    file: UploadFile,
    db: Session,
    id_municipio: int | None = None,
    id_usuario: int | None = None,
) -> str:
    """Guarda una imagen subida y devuelve el path. Lanza HTTPException si falla.

    - El formato se valida con magic bytes, no con el content-type del cliente.
    - El archivo SIEMPRE se renombra con un nombre generado por el servidor
      (ASCII, sin espacios ni caracteres especiales):
      {codigo_ine}_{id_usuario}_{timestamp}{uuid}{ext}
    - Carpeta: uploads/reports/{codigo_ine}/ (o reports/general si no hay municipio)
    """
    original = file.filename or ""
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El archivo excede {MAX_SIZE // (1024 * 1024)} MB "
                f"(recibido {round(len(contents) / (1024 * 1024), 1)} MB)"
            ),
        )

    ext = detect_image_ext(contents)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Formato de imagen no reconocido. "
                f"Recibido: content-type={file.content_type!r}, "
                f"nombre={_sanitize_filename(original)!r}, {len(contents)} bytes. "
                f"Se aceptan: {', '.join(IMAGE_EXTENSIONS)}"
            ),
        )

    timestamp_short = str(int(time.time()))[-8:] + uuid.uuid4().hex[:4]

    if id_municipio:
        codigo_ine = _get_municipio_codigo(db, id_municipio)
        uid_part = str(id_usuario) if id_usuario else "anon"
        filename = f"{codigo_ine}_{uid_part}_{timestamp_short}{ext}"
        subfolder = f"reports/{codigo_ine}"
    else:
        filename = f"upload_{timestamp_short}{ext}"
        subfolder = "reports/general"

    upload_dir = Path(settings.UPLOAD_DIR) / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)

    filepath = upload_dir / filename
    with open(filepath, "wb") as f:
        f.write(contents)

    return f"/uploads/{subfolder}/{filename}"


@router.post("", status_code=201, responses={201: {"model": SuccessResponse}})
async def upload_file(
    file: UploadFile = File(...),
    id_municipio: int | None = None,
    id_usuario: int | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    uid = id_usuario or _user.get("id_usuario")
    path = await save_upload_file(file, db, id_municipio, uid)

    return SuccessResponse(
        message="Archivo subido correctamente",
        data={
            "path": path,
        },
    )


def _resolve_upload_path(path: str) -> Path | None:
    """Resuelve `path` dentro de UPLOAD_DIR y devuelve None si escapa de él.

    Bloquea path traversal (../../, rutas absolutas, symlinks hacia fuera).
    """
    clean_path = path.lstrip("/")
    if clean_path.startswith("uploads/"):
        clean_path = clean_path[len("uploads/"):]
    if not clean_path:
        return None

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    filepath = (upload_root / clean_path).resolve()

    if filepath == upload_root or upload_root not in filepath.parents:
        return None
    return filepath


@router.get("/descargar/{path:path}")
def descargar_archivo(
    path: str,
    _user=Depends(get_current_user),
):
    filepath = _resolve_upload_path(path)
    if filepath is None or not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".avif": "image/avif",
        ".pdf": "application/pdf",
    }.get(filepath.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(filepath), media_type=content_type, filename=filepath.name)


# ============================================================================
#  REPOSITORIO DE DOCUMENTOS PDF (vinculados a EDAN / evento RIDA)
#  Esquema: uploads/edan/documentos/{id_edan}/{id_doc}_{timestamp}.pdf
#           uploads/rida/documentos/{id_evento_rida}/{id_doc}_{timestamp}.pdf
# ============================================================================

PDF_MIME = "application/pdf"
PDF_MAX_SIZE = 50 * 1024 * 1024  # 50 MB


async def save_documento_pdf(
    file: UploadFile,
    db: Session,
    id_usuario: int,
    subfolder: str,
    id_municipio: int | None = None,
) -> tuple[str, int, str, bytes]:
    """Guarda un PDF bajo /uploads/{subfolder}/ y devuelve (path, size, hash_sha256, contents).

    El repositorio es compartido por EDAN y RIDA, asi que la carpeta de destino
    la decide el llamador: 'edan/documentos/{id_edan}' o
    'rida/documentos/{id_evento_rida}'. Esta funcion solo se encarga del
    archivo; validar que la entidad de destino exista es responsabilidad de
    quien llama (api.repositorio.service.resolver_destino_documento).

    Validaciones:
      - MIME type debe ser application/pdf
      - Extensión debe ser .pdf
      - Tamaño máximo 50 MB
    """
    if file.content_type != PDF_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Solo se aceptan archivos PDF. Recibido: {file.content_type}",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener extensión .pdf",
        )

    contents = await file.read()
    if len(contents) > PDF_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo excede el límite de {PDF_MAX_SIZE // (1024 * 1024)} MB",
        )

    import hashlib
    hash_sha256 = hashlib.sha256(contents).hexdigest()

    # El codigo INE solo va en el nombre del archivo; si el municipio no se
    # pudo resolver se usa un marcador y el documento se guarda igual.
    codigo_ine = _get_municipio_codigo(db, id_municipio) if id_municipio else "SINMUNICIPIO"
    timestamp_short = str(int(time.time()))[-8:] + uuid.uuid4().hex[:4]
    filename = f"doc_{codigo_ine}_{id_usuario}_{timestamp_short}.pdf"

    upload_dir = Path(settings.UPLOAD_DIR) / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)

    filepath = upload_dir / filename
    with open(filepath, "wb") as f:
        f.write(contents)

    return f"/uploads/{subfolder}/{filename}", len(contents), hash_sha256, contents


def delete_file_from_server(path_archivo: str) -> bool:
    """Elimina un archivo físico del servidor. Devuelve True si lo eliminó."""
    filepath = _resolve_upload_path(path_archivo)
    if filepath is not None and filepath.exists() and filepath.is_file():
        filepath.unlink()
        return True
    return False
