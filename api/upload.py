import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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


def _sanitize(name: str) -> str:
    return (
        name.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
        .replace("-", "_")
    )


async def save_upload_file(
    file: UploadFile,
    db: Session,
    id_municipio: int | None = None,
    comunidad: str | None = None,
) -> str:
    """Save an uploaded file and return the path. Raises HTTPException on failure."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {file.content_type}. Use: {', '.join(ALLOWED_TYPES.keys())}",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="El archivo excede 5 MB")

    ext = ALLOWED_TYPES[file.content_type]
    timestamp = int(time.time())
    uid = uuid.uuid4().hex[:8]

    if id_municipio and comunidad:
        codigo_ine = _get_municipio_codigo(db, id_municipio)
        folder_name = _sanitize(comunidad)
        filename = f"{folder_name}_{codigo_ine}_{timestamp}{ext}"
        subfolder = f"reports/{codigo_ine}"
    else:
        filename = f"upload_{timestamp}_{uid}{ext}"
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
    comunidad: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    path = await save_upload_file(file, db, id_municipio, comunidad)

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
    }.get(filepath.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(filepath), media_type=content_type, filename=filepath.name)
