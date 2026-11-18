from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import base64
from datetime import datetime, timedelta
from typing import Literal

from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import module_permiso
from ..config import settings
from ..response import SuccessResponse, MessageResponse, DataListResponse, DataItemResponse
from ..upload import save_documento_pdf, delete_file_from_server
from ..firma_digital import service as firma_service
from . import service
from typing import Union

from .schemas import (
    TipoDocumentoCreate, TipoDocumentoUpdate,
    TipoDocumentoResponse,
    DocumentoUpdate, DocumentoResponse, DocumentoGrupoResponse,
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
    #  El repositorio es compartido por EDAN, RIDA y DOC_PRECEDENTE. Las rutas
    #  de EDAN/RIDA se mantienen (produccion). La etiqueta de origen se asigna
    #  automaticamente segun la ruta de subida.

    _VALIDACIONES_UPLOAD = (
        "Validaciones:\n"
        "- MIME debe ser `application/pdf`\n"
        "- Extensión debe ser `.pdf`\n"
        "- El tipo de documento debe existir y estar `activo=TRUE`\n"
    )

    async def _procesar_subida(
        db: Session,
        _user: dict,
        file: UploadFile,
        destino: dict,
        id_tipo_documento: int,
        id_departamento: int,
        id_provincia: int,
        id_municipio: int,
        fecha_documento: str,
        nombre_documento: str,
        observaciones: str | None,
        codigo_documento: str | None = None,
    ) -> dict:
        """Valida el PDF, valida la firma y persiste. Devuelve el documento.

        'destino' trae ids resueltos y 'origen' (EDAN|RIDA|DOC_PRECEDENTE)
        segun la ruta que atendio la subida.
        """
        tipo = service.get_tipo_documento(db, id_tipo_documento)
        if not tipo or not tipo["activo"]:
            raise HTTPException(status_code=400, detail="Tipo de documento no válido o inactivo")

        id_edan = destino.get("id_edan")
        id_evento_rida = destino.get("id_evento_rida")
        origen = destino.get("origen")

        # Carpeta de destino segun origen (asignado por la ruta)
        if origen == "RIDA" and id_evento_rida is not None:
            subfolder = f"rida/documentos/{id_evento_rida}"
        elif origen == "EDAN" and id_edan is not None:
            subfolder = f"edan/documentos/{id_edan}"
        else:
            subfolder = f"repositorio/municipal/{id_municipio}"

        file_path, size, hash_sha256, contents = await save_documento_pdf(
            file, db, _user["id_usuario"], subfolder, id_municipio
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
            nombre_original=file.filename or "documento.pdf",
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
            id_evento_rida=id_evento_rida,
            origen=origen,
            codigo_documento=codigo_documento,
        )

        return dict(service.get_documento(db, id_doc))

    @router.post("/edan/{id_edan}/documentos", status_code=201, tags=[TAG_DOCS],
                 summary="Subir PDF al repositorio de un EDAN",
                 description="Sube un archivo PDF, crea una fila en `repositorio.documentos` y **valida la "
                             "firma digital automáticamente** (si el PDF ≤ 20 MB), guardando los metadatos "
                             "de validación (`tiene_firma_digital`, `resultado_firma`, `fecha_validacion_firma`).\n\n"
                             "Origen asignado automáticamente por la ruta: **EDAN**. Contrato sin cambios.\n\n"
                             "**Multipart**: `file` (PDF, max 50MB) + form fields.\n\n"
                             + _VALIDACIONES_UPLOAD +
                             "- El EDAN debe existir en `edan.edan`\n\n"
                             "Path de almacenamiento: `/uploads/edan/documentos/{id_edan}/doc_{codigo_ine}_{id_usuario}_{ts}.pdf`")
    async def subir_documento_edan(
        id_edan: int,
        file: UploadFile = File(...),
        id_tipo_documento: int = Form(...),
        id_departamento: int = Form(...),
        id_provincia: int = Form(...),
        id_municipio: int = Form(...),
        fecha_documento: str = Form(..., description="YYYY-MM-DD"),
        nombre_documento: str = Form(...),
        observaciones: str | None = Form(None, description="Texto libre (opcional)"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Sube un nuevo PDF al repositorio del EDAN y valida su firma al vuelo."""
        destino = service.resolver_destino_documento(db, id_edan=id_edan)
        if destino is None:
            raise HTTPException(status_code=404, detail=f"EDAN {id_edan} no encontrado")

        doc = await _procesar_subida(
            db=db, _user=_user, file=file, destino=destino,
            id_tipo_documento=id_tipo_documento, id_departamento=id_departamento,
            id_provincia=id_provincia, id_municipio=id_municipio,
            fecha_documento=fecha_documento, nombre_documento=nombre_documento,
            observaciones=observaciones,
        )
        return SuccessResponse(message="Documento subido correctamente", data=doc)

    @router.post("/rida/eventos/{id_evento_rida}/documentos", status_code=201, tags=[TAG_DOCS],
                 summary="Subir PDF al repositorio de un evento RIDA",
                 description="Sube un archivo PDF a un evento RIDA, crea la fila en "
                             "`repositorio.documentos` y **valida la firma digital automáticamente**.\n\n"
                             "Origen asignado automáticamente por la ruta: **RIDA**. Contrato sin cambios.\n\n"
                             "**Multipart**: `file` (PDF, max 50MB) + form fields.\n\n"
                             + _VALIDACIONES_UPLOAD +
                             "- El evento debe existir en `rida.evento_rida`")
    async def subir_documento_rida(
        id_evento_rida: int,
        file: UploadFile = File(...),
        id_tipo_documento: int = Form(...),
        id_departamento: int = Form(...),
        id_provincia: int = Form(...),
        id_municipio: int = Form(...),
        fecha_documento: str = Form(..., description="YYYY-MM-DD"),
        nombre_documento: str = Form(...),
        observaciones: str | None = Form(None, description="Texto libre (opcional)"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Sube un nuevo PDF al repositorio del evento RIDA y valida su firma al vuelo."""
        destino = service.resolver_destino_documento(db, id_evento_rida=id_evento_rida)
        if destino is None:
            raise HTTPException(status_code=404, detail=f"Evento RIDA {id_evento_rida} no encontrado")

        doc = await _procesar_subida(
            db=db, _user=_user, file=file, destino=destino,
            id_tipo_documento=id_tipo_documento, id_departamento=id_departamento,
            id_provincia=id_provincia, id_municipio=id_municipio,
            fecha_documento=fecha_documento, nombre_documento=nombre_documento,
            observaciones=observaciones,
        )
        return SuccessResponse(message="Documento subido correctamente", data=doc)

    @router.post("/documentos", status_code=201, tags=[TAG_DOCS],
                 summary="Subir PDF de respaldo municipal (DOC_PRECEDENTE)",
                 description="Tercera vía de subida (respaldo municipal). Sube un PDF general fuera de EDAN/RIDA.\n\n"
                             "Origen asignado automáticamente por la ruta: **DOC_PRECEDENTE**. Subida municipal, "
                             "con vista/consulta a nivel nacional mediante filtros geográficos.\n\n"
                             "**Multipart** (mismos campos que EDAN/RIDA): `file` (PDF, max 50MB), "
                             "`id_tipo_documento`, `id_departamento`, `id_provincia`, `id_municipio`, "
                             "`fecha_documento` (YYYY-MM-DD), `nombre_documento`, `observaciones` (texto libre, opcional).\n\n"
                             "**`codigo_documento` (opcional, máx 64)**: clave de rastreo/agrupación tipo "
                             "`id_edan`/`id_evento_rida` para respaldos. Se normaliza a MAYÚSCULAS y NO es única: "
                             "varios documentos pueden compartir el mismo código (expediente). Si no se envía, la "
                             "API genera uno `RES-{codigo_ine}-{YYYY}-{sec}` y lo devuelve en la respuesta; "
                             "reenvíe ese código en subidas futuras para anexar documentos al mismo expediente.\n\n"
                             "No requiere `id_edan` ni `id_evento_rida`. El documento queda vinculado al municipio "
                             "y al usuario autenticado que lo sube (`id_usuario_subio`).\n\n"
                             + _VALIDACIONES_UPLOAD)
    async def subir_documento_municipal(
        file: UploadFile = File(...),
        id_tipo_documento: int = Form(...),
        id_departamento: int = Form(...),
        id_provincia: int = Form(...),
        id_municipio: int = Form(...),
        fecha_documento: str = Form(..., description="YYYY-MM-DD"),
        nombre_documento: str = Form(...),
        observaciones: str | None = Form(None, description="Texto libre (opcional)"),
        codigo_documento: str | None = Form(
            None, max_length=64,
            description="Clave de agrupación/expediente (opcional). Si falta se autogenera RES-{codigo_ine}-{YYYY}-{sec}."),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Sube un PDF de respaldo municipal (DOC_PRECEDENTE).

        `codigo_documento`: si el cliente lo envía, el documento se une a ese
        expediente; si no, se autogenera con la secuencia de la BD.
        """
        cod = service.normalizar_codigo_documento(codigo_documento)
        if cod is not None and len(cod) > 64:
            raise HTTPException(status_code=400,
                                detail="codigo_documento no puede exceder 64 caracteres")
        if cod is None:
            cod = service.generar_codigo_documento(db, id_municipio)

        destino = {
            "id_edan": None,
            "id_evento_rida": None,
            "id_municipio": id_municipio,
            "origen": "DOC_PRECEDENTE",
        }
        doc = await _procesar_subida(
            db=db, _user=_user, file=file, destino=destino,
            id_tipo_documento=id_tipo_documento, id_departamento=id_departamento,
            id_provincia=id_provincia, id_municipio=id_municipio,
            fecha_documento=fecha_documento, nombre_documento=nombre_documento,
            observaciones=observaciones, codigo_documento=cod,
        )
        return SuccessResponse(message="Documento subido correctamente", data=doc)

    # ============================================================================
    #  CONSULTAR DOCUMENTOS
    # ============================================================================

    _CAMPOS_FIRMA = (
        "**Firmas digitales** (derivadas de `resultado_firma`):\n"
        "- `cantidad_firmas`: cuántas firmas tiene el documento\n"
        "- `firma_validada`: `true` si AGETIC respondió, `false` si no se pudo validar\n"
        "- `tiene_firma_digital`: `cantidad_firmas > 0`\n\n"
    )

    _EJEMPLOS_GET_DOCUMENTOS = {
        200: {
            "description": "Grupos (modo=agrupado, default) o documentos (modo=plano). "
                           "Esquema `data`: oneOf de DocumentoGrupoResponse / DocumentoResponse.",
            "content": {"application/json": {"examples": {
                "agrupado": {
                    "summary": "Grupo con copias identicas por hash en OTRO grupo",
                    "value": {"success": True, "message": "Grupos de documentos listados",
                              "total": 3, "data": [
                                  {"tipo": "DOC_PRECEDENTE", "clave": "PRUEBA-CROSS-1",
                                   "id_edan": None, "id_evento_rida": None,
                                   "codigo_documento": "PRUEBA-CROSS-1",
                                   "etiqueta": "PRUEBA-CROSS-1",
                                   "id_departamento": 7, "id_provincia": 701, "id_municipio": 70101,
                                   "total_documentos": 1, "fecha_documento_max": "2026-11-10",
                                   "fecha_subida_max": "2026-11-17T19:57:56",
                                   "documentos_compartidos": 1,
                                   "comparte_con": [{"tipo": "EDAN", "clave": "ED-79",
                                                     "etiqueta": "EDAN 070101/2026/003",
                                                     "documentos_comunes": 1,
                                                     "documentos": [{"id_documento": 373,
                                                                     "nombre_documento": "Declaratoria 034/2026 (copia EDAN)",
                                                                     "hash_sha256": "b4b2f45d041f9d89"}]}]},
                                  {"tipo": "EDAN", "clave": "070101/2026/003", "id_edan": 79,
                                   "id_evento_rida": None, "codigo_documento": None,
                                   "etiqueta": "070101/2026/003",
                                   "id_departamento": 7, "id_provincia": 701, "id_municipio": 70101,
                                   "total_documentos": 3, "fecha_documento_max": "2026-11-10",
                                   "fecha_subida_max": "2026-11-17T19:57:56",
                                   "documentos_compartidos": 1,
                                   "comparte_con": [{"tipo": "DOC_PRECEDENTE",
                                                     "clave": "PRUEBA-CROSS-1",
                                                     "etiqueta": "PRUEBA-CROSS-1",
                                                     "documentos_comunes": 1,
                                                     "documentos": [{"id_documento": 374,
                                                                     "nombre_documento": "Declaratoria 034/2026 (copia expediente)",
                                                                     "hash_sha256": "b4b2f45d041f9d89"}]}]},
                                  {"tipo": "RIDA", "clave": "070101/2026/003-R", "id_edan": 79,
                                   "id_evento_rida": 15, "codigo_documento": None,
                                   "etiqueta": "070101/2026/003-R",
                                   "id_departamento": 7, "id_provincia": 701, "id_municipio": 70101,
                                   "total_documentos": 2, "fecha_documento_max": "2026-10-09",
                                   "fecha_subida_max": "2026-10-09T16:17:52",
                                   "documentos_compartidos": 0, "comparte_con": []}]},
                },
                "plano": {
                    "summary": "Documentos individuales (modo=plano)",
                    "value": {"success": True, "message": "Documentos listados", "total": 1,
                              "data": [{"id_documento": 72, "origen": "RIDA",
                                        "id_edan": 79, "id_evento_rida": 15,
                                        "codigo_documento": None, "id_tipo_documento": 1,
                                        "nombre_original": "RIDA_Municipio_Santa_Cruz.pdf",
                                        "path_archivo": "/uploads/rida/documentos/15/doc_070101_28_x.pdf",
                                        "tamano_bytes": 810065,
                                        "hash_sha256": "88eb878f94ed04ee",
                                        "id_usuario_subio": 28,
                                        "id_departamento": 7, "id_provincia": 701,
                                        "id_municipio": 70101, "fecha_documento": "2026-10-09",
                                        "nombre_documento": "RIDA_Municipio_Santa_Cruz",
                                        "fecha_subida": "2026-10-09T16:17:52",
                                        "activo": True,
                                        "observaciones": "Informe de validacion departamental",
                                        "tiene_firma_digital": False, "cantidad_firmas": 0,
                                        "firma_validada": False,
                                        "tipo_codigo": "informe_legal",
                                        "tipo_nombre": "Informe Legal"}]},
                },
            }}},
        }
    }

    @router.get("/documentos", tags=[TAG_DOCS],
                response_model=DataListResponse[Union[DocumentoGrupoResponse, DocumentoResponse]],
                responses=_EJEMPLOS_GET_DOCUMENTOS,
                summary="Listar documentos (vista nacional, agrupado por expediente)",
                description="Listado general del repositorio (EDAN + RIDA + DOC_PRECEDENTE), vista nacional.\n\n"
                            "**Por defecto devuelve GRUPOS** (`modo=agrupado`): un grupo por entidad "
                            "padre/expediente — RIDA por `id_evento_rida` (se mantiene como RIDA aunque "
                            "herede `id_edan`), EDAN por `id_edan`, DOC_PRECEDENTE por `codigo_documento`— "
                            "con `total_documentos`, geografía, fechas máximas y su **código real** en "
                            "`clave`/`etiqueta` (`codigo_edan` para EDAN, "
                            "`rida.evento_rida.codigo` para RIDA, "
                            "`codigo_documento` para DOC_PRECEDENTE). "
                            "`data` es la lista de grupos y `total` el nº de **grupos** sin paginar.\n\n"
                            "Con `modo=plano` devuelve los documentos individuales (contrato clásico "
                            "reciente primero). Para el detalle de un grupo reenvíe sus claves como "
                            "filtros con `modo=plano`: `?modo=plano&id_evento_rida=15`, "
                            "`?modo=plano&id_edan=79` o `?modo=plano&codigo_documento=RES-...`.\n\n"
                            "Orden: los más recientes primero. Filtros opcionales (aplican a ambos modos): "
                            "`origen` (EDAN|RIDA|DOC_PRECEDENTE), geografía "
                            "(`id_departamento`, `id_provincia`, `id_municipio`), `id_edan` (**solo documentos "
                            "de origen EDAN**: los RIDA que heredan ese `id_edan` no se incluyen; "
                            "para ver todo el EDAN use `GET /edan/{id_edan}/documentos`), "
                            "`id_evento_rida` (solo RIDA de ese evento), "
                            "`codigo_documento` (expediente de respaldos, exacto, sin distinguir mayúsculas) y "
                            "`codigo_grupo` (código real del grupo en cualquier origen), "
                            "`id_tipo_documento`, `id_usuario_subio`, rango `fecha_desde`/`fecha_hasta` (YYYY-MM-DD), "
                            "`q` (búsqueda en nombre), `tiene_firma_digital`, `include_inactive`.\n\n"
                            + _CAMPOS_FIRMA)
    def listar_documentos(
        limit: int = Query(50, ge=1, le=200, description="Cantidad a devolver (los más recientes primero)"),
        skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
        todos: bool = Query(False, description="Devolver todos sin paginar (ignora limit/skip)"),
        modo: Literal["agrupado", "plano"] = Query(
            "agrupado", description="agrupado: un grupo por expediente/padre con total_documentos; plano: lista de documentos"),
        origen: Literal["EDAN", "RIDA", "DOC_PRECEDENTE"] | None = Query(
            None, description="Filtrar por origen: EDAN, RIDA o DOC_PRECEDENTE"),
        codigo_documento: str | None = Query(
            None, max_length=64, description="Filtrar por clave de agrupación/expediente (DOC_PRECEDENTE)"),
        codigo_grupo: str | None = Query(
            None, max_length=80,
            description="Código real del grupo en cualquier origen: codigo_edan "
                        "(070101/2026/003), codigo de evento RIDA (070101/2026/003-R) "
                        "o codigo_documento; sin distinguir mayúsculas"),
        id_edan: int | None = Query(
            None, description="EDAN (solo documentos origen EDAN; los RIDA que heredan este id no se incluyen)"),
        id_evento_rida: int | None = Query(None, description="Filtrar por evento RIDA"),
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        id_provincia: int | None = Query(None, description="Filtrar por provincia"),
        id_municipio: int | None = Query(None, description="Filtrar por municipio"),
        id_tipo_documento: int | None = Query(None, description="Filtrar por tipo de documento"),
        id_usuario_subio: int | None = Query(None, description="Filtrar por usuario que subió"),
        fecha_desde: str | None = Query(None, description="Fecha documento desde (YYYY-MM-DD)"),
        fecha_hasta: str | None = Query(None, description="Fecha documento hasta (YYYY-MM-DD)"),
        q: str | None = Query(None, description="Búsqueda por nombre (ILIKE)"),
        tiene_firma_digital: bool | None = Query(None, description="Filtrar por firma digital"),
        include_inactive: bool = Query(False, description="Incluir documentos inactivos"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Lista documentos (plano) o grupos por expediente (agrupado, default)."""
        if modo == "agrupado":
            data, total = service.list_documentos_grupos(
                db, origen=origen, codigo_documento=codigo_documento, codigo_grupo=codigo_grupo,
                id_edan=id_edan, id_evento_rida=id_evento_rida,
                id_departamento=id_departamento, id_provincia=id_provincia, id_municipio=id_municipio,
                id_tipo_documento=id_tipo_documento, id_usuario_subio=id_usuario_subio,
                fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, nombre_documento_like=q,
                tiene_firma_digital=tiene_firma_digital, include_inactive=include_inactive,
                limit=limit, skip=skip, todos=todos,
            )
            return SuccessResponse(message="Grupos de documentos listados",
                                   data=[dict(r) for r in data], total=total)

        data, total = service.list_documentos_filtrados(
            db, origen=origen, codigo_documento=codigo_documento, codigo_grupo=codigo_grupo,
            id_edan=id_edan, id_evento_rida=id_evento_rida,
            id_departamento=id_departamento, id_provincia=id_provincia, id_municipio=id_municipio,
            id_tipo_documento=id_tipo_documento, id_usuario_subio=id_usuario_subio,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, nombre_documento_like=q,
            tiene_firma_digital=tiene_firma_digital, include_inactive=include_inactive,
            limit=limit, skip=skip, todos=todos,
        )
        return SuccessResponse(message="Documentos listados", data=[dict(r) for r in data], total=total)

    @router.get("/documentos/codigo/{codigo_grupo:path}", tags=[TAG_DOCS],
                response_model=DataListResponse[DocumentoResponse],
                summary="Listar documentos de un grupo por su código real",
                description="Todos los documentos activos del grupo cuyo **código "
                            "real** coincide con el dado: `codigo_edan` de un EDAN "
                            "(p. ej. 070101/2026/003), `rida.evento_rida.codigo` "
                            "(p. ej. 070101/2026/003-R) o `codigo_documento` de un "
                            "expediente DOC_PRECEDENTE (RES-... o el puesto por el "
                            "municipio). Sin distinguir mayúsculas. Orden reciente "
                            "primero con paginación `limit`/`skip`/`todos`.\n\n" + _CAMPOS_FIRMA)
    def listar_documentos_codigo(
        codigo_grupo: str,
        limit: int = Query(50, ge=1, le=200, description="Cantidad a devolver (los más recientes primero)"),
        skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
        todos: bool = Query(False, description="Devolver todos sin paginar (ignora limit/skip)"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Documentos del grupo cuyo codigo real coincide (EDAN/RIDA/PRECEDENTE)."""
        cod = (codigo_grupo or "").strip()
        if not cod:
            raise HTTPException(status_code=400, detail="codigo vacío")
        data, total = service.list_documentos_by_codigo(
            db, cod, limit=limit, skip=skip, todos=todos,
        )
        return SuccessResponse(message="Documentos del expediente listados",
                               data=[dict(r) for r in data], total=total)

    @router.get("/edan/{id_edan}/documentos", tags=[TAG_DOCS],
                summary="Listar documentos de un EDAN específico",
                description="Retorna los PDFs del repositorio vinculados a `id_edan`.\n\n"
                            "Filtros opcionales: `id_tipo_documento`, `include_inactive` y "
                            "`origen` (`EDAN` o `RIDA`).\n\n" + _CAMPOS_FIRMA)
    def listar_documentos_edan(
        id_edan: int,
        id_tipo_documento: int | None = Query(None, description="Filtrar por tipo de catálogo"),
        include_inactive: bool = Query(False, description="Incluir documentos con activo=FALSE"),
        origen: Literal["EDAN", "RIDA"] | None = Query(None, description="Filtrar origen (EDAN o RIDA)"),
        limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
        skip: int = Query(0, ge=0, description="Registros a saltar"),
        todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Lista documentos de un EDAN."""
        data, total = service.list_documentos_by_edan(db, id_edan, id_tipo_documento, include_inactive, origen,
                                                      limit=limit, skip=skip, todos=todos)
        return SuccessResponse(message="Documentos listados", data=[dict(r) for r in data], total=total)

    @router.get("/rida/eventos/{id_evento_rida}/documentos", tags=[TAG_DOCS],
                summary="Listar documentos de un evento RIDA",
                description="Retorna los PDFs del repositorio vinculados a `id_evento_rida` (origen RIDA).\n\n"
                            + _CAMPOS_FIRMA)
    def listar_documentos_rida(
        id_evento_rida: int,
        id_tipo_documento: int | None = Query(None, description="Filtrar por tipo de catálogo"),
        include_inactive: bool = Query(False, description="Incluir documentos con activo=FALSE"),
        limit: int | None = Query(None, ge=1, description="Registros por página. Sin valor: sin límite"),
        skip: int = Query(0, ge=0, description="Registros a saltar"),
        todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Lista documentos de un evento RIDA."""
        data, total = service.list_documentos_by_evento_rida(
            db, id_evento_rida, id_tipo_documento, include_inactive,
            limit=limit, skip=skip, todos=todos
        )
        return SuccessResponse(message="Documentos listados", data=[dict(r) for r in data], total=total)

    @router.get("/documentos/filtrar", tags=[TAG_DOCS],
                response_model=DataListResponse[DocumentoResponse],
                summary="Filtrar documentos por metadata estructurada (compatibilidad)",
                description="Listado con filtros (EDAN + RIDA + DOC_PRECEDENTE). Mantiene compatibilidad con clientes existentes.\n\n"
                            "Se recomienda el endpoint general `GET /repositorio/documentos`.\n\n" + _CAMPOS_FIRMA)
    def filtrar_documentos(
        origen: Literal["EDAN", "RIDA", "DOC_PRECEDENTE"] | None = Query(None, description="Origen"),
        codigo_documento: str | None = Query(None, max_length=64, description="Clave de agrupación/expediente"),
        codigo_grupo: str | None = Query(
            None, max_length=80,
            description="Código real del grupo (codigo_edan, código RIDA o codigo_documento)"),
        id_edan: int | None = Query(
            None, description="FK a edan.edan.id_edan; solo origen EDAN (los RIDA heredados quedan excluidos: use /edan/{id}/documentos)"),
        id_evento_rida: int | None = Query(None, description="FK a rida.evento_rida.id_evento_rida"),
        id_departamento: int | None = Query(None),
        id_provincia: int | None = Query(None),
        id_municipio: int | None = Query(None),
        id_tipo_documento: int | None = Query(None),
        id_usuario_subio: int | None = Query(None),
        fecha_desde: str | None = Query(None, description="YYYY-MM-DD"),
        fecha_hasta: str | None = Query(None, description="YYYY-MM-DD"),
        nombre_documento_like: str | None = Query(None, description="ILIKE match"),
        tiene_firma_digital: bool | None = Query(None),
        include_inactive: bool = Query(False),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Filtra documentos por metadata estructurada."""
        data, total = service.list_documentos_filtrados(
            db, origen=origen, codigo_documento=codigo_documento, codigo_grupo=codigo_grupo,
            id_edan=id_edan, id_evento_rida=id_evento_rida,
            id_departamento=id_departamento, id_provincia=id_provincia, id_municipio=id_municipio,
            id_tipo_documento=id_tipo_documento, id_usuario_subio=id_usuario_subio,
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            nombre_documento_like=nombre_documento_like,
            tiene_firma_digital=tiene_firma_digital, include_inactive=include_inactive,
            limit=limit, skip=skip, todos=todos,
        )
        return SuccessResponse(
            message="Documentos filtrados correctamente",
            data=[dict(r) for r in data],
            total=total,
        )

    @router.get("/documentos/buscar", tags=[TAG_DOCS],
                response_model=DataListResponse[DocumentoResponse],
                summary="Buscar documentos por nombre (ILIKE)",
                description="Búsqueda parcial en `nombre_documento` y `nombre_original` (EDAN, RIDA, DOC_PRECEDENTE).\n\n"
                            "Filtros opcionales: `id_municipio` y `origen`.")
    def buscar_documentos(
        q: str = Query(..., description="Término a buscar en nombre_documento o nombre_original"),
        id_municipio: int | None = Query(None, description="Limitar búsqueda a un municipio"),
        origen: Literal["EDAN", "RIDA", "DOC_PRECEDENTE"] | None = Query(None, description="Limitar a un origen"),
        limit: int = Query(50, ge=1, le=200, description="Máximo 200 resultados"),
        skip: int = Query(0, ge=0, description="Saltar registros (paginación)"),
        todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Búsqueda por nombre (ILIKE)."""
        data, total = service.buscar_documentos(db, q, id_municipio, limit, origen,
                                                skip=skip, todos=todos)
        return SuccessResponse(message=f"Búsqueda: {q}", data=[dict(r) for r in data], total=total)

    @router.get("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Obtener metadata de un documento",
            description="Retorna todos los campos del documento + datos del tipo.\n\n" + _CAMPOS_FIRMA)
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
            description="Retorna el archivo PDF con `Content-Type: application/pdf`.")
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

    DIAS_MAX_DOC_PRECEDENTE = 3  # ventana para editar/eliminar respaldos municipales

    def _validar_permiso_doc_precedente(doc: dict, _user: dict) -> None:
        """Restringe edición/eliminación de DOC_PRECEDENTE (3ª API).

        Aplica SOLO a documentos con origen DOC_PRECEDENTE: los puede editar o
        eliminar únicamente el usuario que los subió y hasta 72 h (3 días)
        después de la subida. Los documentos EDAN y RIDA conservan el
        comportamiento anterior.
        """
        origen = (doc.get("origen") or "").upper()
        if origen != "DOC_PRECEDENTE":
            return

        if int(doc.get("id_usuario_subio") or 0) != int(_user.get("id_usuario") or 0):
            raise HTTPException(
                status_code=403,
                detail="Solo el usuario que subió el documento puede editarlo o eliminarlo",
            )

        fecha_subida = doc.get("fecha_subida")
        if not isinstance(fecha_subida, datetime):
            raise HTTPException(
                status_code=403,
                detail="No se pudo validar la antigüedad del documento",
            )
        ahora = datetime.now(fecha_subida.tzinfo) if fecha_subida.tzinfo else datetime.now()
        if ahora - fecha_subida > timedelta(days=DIAS_MAX_DOC_PRECEDENTE):
            raise HTTPException(
                status_code=403,
                detail="No se puede editar ni eliminar: han pasado más de 3 días desde la subida",
            )

    @router.put("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Actualizar metadata del documento",
            description="Solo `observaciones` (texto libre) y `activo` son modificables (PUT parcial).\n\n"
                        "**DOC_PRECEDENTE** (3ª API): solo el usuario que lo subió y dentro de las 72 h "
                        "(3 días) desde la subida; fuera de eso responde **403**. No aplica a EDAN/RIDA.")
    def actualizar_documento(
        id_documento: int,
        data: DocumentoUpdate,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Actualiza observaciones/activo de un documento."""
        doc = service.get_documento(db, id_documento)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        _validar_permiso_doc_precedente(dict(doc), _user)
        service.update_documento(db, id_documento, data.model_dump(exclude_unset=True))
        updated = service.get_documento(db, id_documento)
        return SuccessResponse(message="Documento actualizado", data=dict(updated))

    @router.delete("/documentos/{id_documento}", tags=[TAG_DOCS],
            summary="Eliminar documento (soft delete)",
            description="Marca `activo=FALSE`. El archivo físico permanece en disco.\n\n"
                        "**DOC_PRECEDENTE** (3ª API): solo el usuario que lo subió y dentro de las 72 h "
                        "(3 días) desde la subida; fuera de eso responde **403**. No aplica a EDAN/RIDA.")
    def eliminar_documento(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Soft delete (activo=FALSE)."""
        doc = service.get_documento(db, id_documento)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        _validar_permiso_doc_precedente(dict(doc), _user)
        service.delete_documento(db, id_documento, hard=False)
        return MessageResponse(message="Documento eliminado correctamente")

    @router.delete("/documentos/{id_documento}/hard", tags=[TAG_DOCS],
            summary="Eliminar documento físicamente (hard delete)",
            description="DELETE irreversible: borra fila en BD **Y** archivo del servidor.\n\n"
                        "**DOC_PRECEDENTE** (3ª API): solo el usuario que lo subió y dentro de las 72 h "
                        "(3 días) desde la subida; fuera de eso responde **403**. No aplica a EDAN/RIDA.")
    def eliminar_documento_hard(
        id_documento: int,
        db: Session = Depends(get_db),
        _user=Depends(get_current_user),
    ):
        """Eliminación física (DELETE irreversible, archivo del servidor incluido)."""
        doc = service.get_documento(db, id_documento)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        _validar_permiso_doc_precedente(dict(doc), _user)

        delete_file_from_server(doc["path_archivo"])
        service.delete_documento(db, id_documento, hard=True)
        return MessageResponse(message="Documento eliminado permanentemente")

    return router


router = create_repositorio_router(require_module=True)
router_v2 = create_repositorio_router(require_module=False)
