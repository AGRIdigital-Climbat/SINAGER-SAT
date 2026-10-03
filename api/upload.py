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

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


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
    """Save an uploaded file and return the path. Raises HTTPException on failure.

    Naming: {codigo_ine}_{id_usuario}_{timestamp_short}{ext}
    Folder:  uploads/reports/{codigo_ine}/
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {file.content_type}. Use: {', '.join(ALLOWED_TYPES.keys())}",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede 5 MB")

    ext = ALLOWED_TYPES[file.content_type]
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


@router.get("/descargar/{path:path}")
def descargar_archivo(
    path: str,
    _user=Depends(get_current_user),
):
    clean_path = path.lstrip("/")
    if clean_path.startswith("uploads/"):
        clean_path = clean_path[len("uploads/"):]
    filepath = Path(settings.UPLOAD_DIR) / clean_path
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
    }.get(filepath.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(filepath), media_type=content_type, filename=filepath.name)


# ============================================================================
#  REPOSITORIO DE DOCUMENTOS PDF (vinculados a EDAN)
#  Esquema: uploads/edan/documentos/{id_edan}/{id_doc}_{timestamp}.pdf
# ============================================================================

PDF_MIME = "application/pdf"
PDF_MAX_SIZE = 50 * 1024 * 1024  # 50 MB


def _sanitize_filename(filename: str) -> str:
    return (
        filename.replace(" ", "_")
        .replace("/", "_").replace("\\", "_")
        .replace(":", "_").replace("*", "_")
        .replace("?", "_").replace('"', "_")
        .replace("<", "_").replace(">", "_")
        .replace("|", "_")
    )


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
    'rida/documentos/{id_formulario_rida}'. Esta funcion solo se encarga del
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
    clean = path_archivo.lstrip("/")
    if clean.startswith("uploads/"):
        clean = clean[len("uploads/"):]
    filepath = Path(settings.UPLOAD_DIR) / clean
    if filepath.exists() and filepath.is_file():
        filepath.unlink()
        return True
    return False
