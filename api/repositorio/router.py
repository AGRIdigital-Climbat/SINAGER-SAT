from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import base64
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..config import settings
from ..response import SuccessResponse, MessageResponse, DataListResponse, DataItemResponse
from ..upload import save_documento_pdf, delete_file_from_server
from ..firma_digital import service as firma_service
from . import service
from .schemas import (
    TipoDocumentoCreate, TipoDocumentoUpdate,
    TipoDocumentoResponse,
    DocumentoUpdate,
)


def create_repositorio_router(require_module: bool = False) -> APIRouter:
    if require_module:
        router = APIRouter(
            prefix="/repositorio",
            dependencies=[Depends(module_permiso("REPOSITORIO"))],
        )
    else:
        router = APIRouter(prefix="/repositorio")

    TAG_CATALOGO = "Repositorio > Catálogo"
    TAG_DOCS     = "Repositorio > Documentos"

    # ============================================================================
    #  CATÁLOGO: tipos de documento (CRUD completo)
    # ============================================================================

    @router.get("/tipos", tags=[TAG_CATALOGO], response_model=DataListResponse[TipoDocumentoResponse],
            summary="Listar tipos de documento del catálogo",
            description="Retorna los tipos de documento disponibles para subir al repositorio.\n\n"
                        "Por defecto solo retorna tipos activos. Pasar `include_inactive=true` para ver todos.")
    def listar_tipos_documento(
        include_inactive: bool = Query(False, description="Si TRUE, incluye tipos con activo=FALSE"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Lista todos los tipos de documento del catálogo."""
        data = service.list_tipos_documento(db, include_inactive=include_inactive)
        return SuccessResponse(message="Tipos de documento listados", data=data, total=len(data))

    @router.get("/tipos/{id_tipo}", tags=[TAG_CATALOGO], response_model=DataItemResponse[TipoDocumentoResponse],
            summary="Obtener un tipo de documento específico",
            description="Retorna metadata del tipo: codigo, nombre, extensiones permitidas, tamaño máximo.")
    def obtener_tipo_documento(
        id_tipo: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Obtiene un tipo de documento específico."""
        data = service.get_tipo_documento(db, id_tipo)
        if not data:
            raise HTTPException(status_code=404, detail="Tipo de documento no encontrado")
        return SuccessResponse(message="Tipo de documento obtenido", data=dict(data))

    @router.post("/tipos", status_code=201, tags=[TAG_CATALOGO], response_model=DataItemResponse[TipoDocumentoResponse],
            summary="Crear tipo de documento en el catálogo",
            description="Crea una entrada nueva en `repositorio.tipo_documento`.\n\n"
                        "Defaults: `activo=TRUE`, `requiere_versionado=FALSE`, `extensiones_permitidas='pdf'`, "
                        "`tamano_maximo_bytes=52428800` (50MB).")
    def crear_tipo_documento(
        data: TipoDocumentoCreate,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Crea un nuevo tipo de documento en el catálogo."""
        id_tipo = service.create_tipo_documento(db, data.model_dump())
        created = service.get_tipo_documento(db, id_tipo)
        return SuccessResponse(message="Tipo de documento creado", data=dict(created))

    @router.put("/tipos/{id_tipo}", tags=[TAG_CATALOGO], response_model=DataItemResponse[TipoDocumentoResponse],
            summary="Actualizar tipo de documento (PUT parcial)",
            description="Actualiza el subset de campos enviados. Solo los campos no-None se modifican.")
    def actualizar_tipo_documento(
        id_tipo: int,
        data: TipoDocumentoUpdate,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Actualiza un tipo de documento del catálogo."""
        service.update_tipo_documento(db, id_tipo, data.model_dump(exclude_unset=True))
        updated = service.get_tipo_documento(db, id_tipo)
        return SuccessResponse(message="Tipo de documento actualizado", data=dict(updated))

    @router.delete("/tipos/{id_tipo}", tags=[TAG_CATALOGO],
            summary="Eliminar tipo de documento",
            description="Soft delete por defecto (activo=FALSE). Pasar `hard=true` para DELETE físico.")
    def eliminar_tipo_documento(
        id_tipo: int,
        hard: bool = Query(False, description="True = DELETE físico, False = soft delete (activo=FALSE)"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Elimina un tipo de documento (soft delete por defecto)."""
        if not service.delete_tipo_documento(db, id_tipo, hard=hard):
            raise HTTPException(status_code=404, detail="Tipo de documento no encontrado")
        return MessageResponse(
            message=f"Tipo de documento {'eliminado' if hard else 'desactivado'} correctamente"
        )

    # ============================================================================
    #  SUBIR DOCUMENTOS (solo PDF, sin versionado)
    # ============================================================================

    @router.post("/edan/{id_edan}/documentos", status_code=201, tags=[TAG_DOCS],
                 summary="Subir PDF al repositorio de un EDAN",
                 description="Sube un archivo PDF, crea una fila en `repositorio.documentos` y **valida la "
                             "firma digital automáticamente** (si el PDF ≤ 20 MB), guardando los metadatos "
                             "de validación (`tiene_firma_digital`, `resultado_firma`, `fecha_validacion_firma`).\n\n"
                             "Si AGETIC no está disponible o el PDF supera 20 MB la validación se omite, el "
                             "documento se guarda igual y `resultado_firma` registra el motivo.\n\n"
                             "**Multipart**: `file` (PDF, max 50MB) + form fields.\n\n"
                             "Validaciones:\n"
                             "- MIME debe ser `application/pdf`\n"
                             "- Extensión debe ser `.pdf`\n"
                             "- El EDAN debe existir en `edan.edan`\n"
                             "- El tipo de documento debe existir y estar `activo=TRUE`\n\n"
                             "Path de almacenamiento: `/uploads/edan/documentos/{id_edan}/doc_{codigo_ine}_{id_usuario}_{ts}.pdf`")
    async def subir_documento(
        id_edan: int,
        file: UploadFile = File(...),
        id_tipo_documento: int = Form(...),
        id_departamento: int = Form(...),
        id_provincia: int = Form(...),
        id_municipio: int = Form(...),
        fecha_documento: str = Form(..., description="YYYY-MM-DD"),
        nombre_documento: str = Form(...),
        observaciones: str | None = Form(None),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Sube un nuevo PDF al repositorio del EDAN y valida su firma al vuelo."""
        tipo = service.get_tipo_documento(db, id_tipo_documento)
        if not tipo or not tipo["activo"]:
            raise HTTPException(status_code=400, detail="Tipo de documento no válido o inactivo")

        file_path, size, hash_sha256, contents = await save_documento_pdf(
            file, db, id_edan, _user["id_usuario"]
        )

        tiene_firma = False
        resultado_firma: dict | None = None
        fecha_validacion_firma: datetime | None = None

        max_bytes = settings.AGETIC_MAX_SIZE_MB * 1024 * 1024
        if len(contents) <= max_bytes:
            try:
                pdf_b64 = base64.b64encode(contents).decode("ascii")
                resultado = await firma_service.validar_pdf(pdf_b64)
                tiene_firma = bool(resultado.get("cantidad_firmas", 0) > 0)
                resultado_firma = resultado
                fecha_validacion_firma = datetime.now()
            except HTTPException as exc:
                resultado_firma = {
                    "finalizado": False,
                    "tipoRespuesta": "Error",
                    "mensaje": f"No se pudo validar la firma: {exc.detail}",
                    "firmas": [],
                    "cantidad_firmas": 0,
                    "error": exc.detail,
                }
        else:
            resultado_firma = {
                "finalizado": False,
                "tipoRespuesta": "Error",
                "mensaje": (f"Documento excede el límite de "
                            f"{settings.AGETIC_MAX_SIZE_MB} MB para validar firma digital."),
                "firmas": [],
                "cantidad_firmas": 0,
                "error": "archivo_excede_limite_agetica",
            }

        id_doc = service.upload_documento(
            db=db,
            id_edan=id_edan,
            id_tipo_documento=id_tipo_documento,
            file_path=file_path,
            nombre_original=file.filename,
            tamano_bytes=size,
            id_usuario=_user["id_usuario"],
            id_municipio=id_municipio,
            id_departamento=id_departamento,
            id_provincia=id_provincia,
            fecha_documento=fecha_documento,
            nombre_documento=nombre_documento,
            observaciones=observaciones,
            hash_sha256=hash_sha256,
            tiene_firma_digital=tiene_firma,
            resultado_firma=resultado_firma,
            fecha_validacion_firma=fecha_validacion_firma,
        )

        doc = service.get_documento(db, id_doc)
        return SuccessResponse(message="Documento subido correctamente", data=dict(doc))

    # ============================================================================
    #  CONSULTAR DOCUMENTOS
    # ============================================================================

    @router.get("/edan/{id_edan}/documentos", tags=[TAG_DOCS],
                summary="Listar documentos de un EDAN específico",
                description="Retorna todos los PDFs del repositorio vinculados a `id_edan`.\n\n"
                            "Filtros opcionales: `id_tipo_documento` y `include_inactive`.")
    def listar_documentos_edan(
        id_edan: int,
        id_tipo_documento: int | None = Query(None, description="Filtrar por tipo de catálogo"),
        include_inactive: bool = Query(False, description="Incluir documentos con activo=FALSE"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Lista documentos de un EDAN."""
        data = service.list_documentos_by_edan(db, id_edan, id_tipo_documento, include_inactive)
        return SuccessResponse(message="Documentos listados", data=[dict(r) for r in data], total=len(data))

    @router.get("/documentos/filtrar", tags=[TAG_DOCS],
                summary="Filtrar documentos por metadata estructurada",
                description="Filtra documentos del repositorio combinando los parámetros:\n\n"
                            "- **id_edan**: documentos de un EDAN específico\n"
                            "- **id_departamento/id_provincia/id_municipio**: por ubicación\n"
                            "- **id_tipo_documento**: por tipo de catálogo\n"
                            "- **fecha_desde/fecha_hasta**: rango sobre `fecha_documento` (YYYY-MM-DD)\n"
                            "- **nombre_documento_like**: búsqueda parcial en `nombre_documento`\n\n"
                            "Retorna `{data: [...], total: N}` con paginación `skip`/`limit`.")
    def filtrar_documentos(
        id_edan: int | None = Query(None, description="FK a edan.edan.id_edan"),
        id_departamento: int | None = Query(None),
        id_provincia: int | None = Query(None),
        id_municipio: int | None = Query(None),
        id_tipo_documento: int | None = Query(None),
        fecha_desde: str | None = Query(None, description="YYYY-MM-DD"),
        fecha_hasta: str | None = Query(None, description="YYYY-MM-DD"),
        nombre_documento_like: str | None = Query(None, description="ILIKE match"),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Filtra documentos por metadata estructurada (departamento, provincia, municipio, tipo, fecha, nombre)."""
        data, total = service.list_documentos_filtrados(
            db,
            id_edan=id_edan,
            id_departamento=id_departamento,
            id_provincia=id_provincia,
            id_municipio=id_municipio,
            id_tipo_documento=id_tipo_documento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            nombre_documento_like=nombre_documento_like,
            limit=limit,
            skip=skip,
        )
        return SuccessResponse(
            message="Documentos filtrados correctamente",
            data=[dict(r) for r in data],
            total=total,
        )

    @router.get("/documentos/buscar", tags=[TAG_DOCS],
                summary="Buscar documentos por nombre (ILIKE)",
                description="Búsqueda parcial en `nombre_documento` y `nombre_original`.\n\n"
                            "Retorna documentos activos ordenados por `fecha_documento` DESC.")
    def buscar_documentos(
        q: str = Query(..., description="Término a buscar en nombre_documento o nombre_original"),
        id_municipio: int | None = Query(None, description="Limitar búsqueda a un municipio"),
        limit: int = Query(50, le=200, description="Máximo 200 resultados"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Búsqueda por nombre (ILIKE sobre nombre_documento y nombre_original)."""
        data = service.buscar_documentos(db, q, id_municipio, limit)
        return SuccessResponse(
            message=f"Búsqueda: {q}",
            data=[dict(r) for r in data],
            total=len(data),
        )

    @router.get("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Obtener metadata de un documento",
            description="Retorna todos los campos del documento + datos del tipo (codigo, nombre).")
    def obtener_documento(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Obtiene metadata de un documento específico."""
        data = service.get_documento(db, id_documento)
        if not data:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return SuccessResponse(message="Documento obtenido", data=dict(data))

    @router.get("/documentos/{id_documento}/descargar", tags=[TAG_DOCS],
            summary="Descargar el PDF físico",
            description="Retorna el archivo PDF con `Content-Type: application/pdf`.\n\n"
                        "El documento debe existir y estar activo.")
    def descargar_documento(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Descarga el PDF físico del documento."""
        doc = service.get_documento(db, id_documento)
        if not doc or not doc["activo"]:
            raise HTTPException(status_code=404, detail="Documento no encontrado o inactivo")

        clean = doc["path_archivo"].lstrip("/")
        if clean.startswith("uploads/"):
            clean = clean[len("uploads/"):]
        filepath = Path(settings.UPLOAD_DIR) / clean

        if not filepath.exists() or not filepath.is_file():
            raise HTTPException(status_code=404, detail="Archivo no encontrado en servidor")

        return FileResponse(
            path=str(filepath),
            media_type="application/pdf",
            filename=doc["nombre_original"],
        )

    # ============================================================================
    #  ACTUALIZAR / ELIMINAR
    # ============================================================================

    @router.put("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Actualizar metadata del documento",
            description="Solo `observaciones` y `activo` son modificables (PUT parcial).")
    def actualizar_documento(
        id_documento: int,
        data: DocumentoUpdate,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Actualiza observaciones/activo de un documento."""
        if not service.get_documento(db, id_documento):
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        service.update_documento(db, id_documento, data.model_dump(exclude_unset=True))
        updated = service.get_documento(db, id_documento)
        return SuccessResponse(message="Documento actualizado", data=dict(updated))

    @router.delete("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Eliminar documento (soft delete)",
            description="Marca `activo=FALSE`. El archivo físico permanece en disco.")
    def eliminar_documento(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Soft delete (activo=FALSE)."""
        if not service.delete_documento(db, id_documento, hard=False):
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return MessageResponse(message="Documento eliminado correctamente")

    @router.delete("/documentos/{id_documento}/hard", tags=[TAG_DOCS],
            summary="Eliminar documento físicamente (hard delete)",
            description="DELETE irreversible: borra fila en BD **Y** archivo del servidor.")
    def eliminar_documento_hard(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Eliminación física (DELETE irreversible, archivo del servidor incluido)."""
        doc = service.get_documento(db, id_documento)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        delete_file_from_server(doc["path_archivo"])
        service.delete_documento(db, id_documento, hard=True)
        return MessageResponse(message="Documento eliminado permanentemente")

    return router


router = create_repositorio_router(require_module=True)
router_v2 = create_repositorio_router(require_module=False)