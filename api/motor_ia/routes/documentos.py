from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from ...response import SuccessResponse
import os
import re
import pymupdf as fitz
from ..db.queries import (
    listar_documentos_filtrados,
    obtener_documento,
    eliminar_documento,
    contar_chunks_documento,
    listar_chunks_documento_paginado,
    actualizar_documento,
    obtener_tipo_documento,
)
from ..config import BASE_DIR, UPLOAD_DIR
from ..core.rag import procesar_documento
from ..core.verificacion import verificar_documento
from ..security import _validar_token_api

router = APIRouter(prefix="/documentos", tags=["MotorIA > Documentos"])


def _extraer_metadatos(md):
    claves = {
        "title": "titulo_pdf",
        "author": "autor",
        "subject": "asunto",
        "keywords": "keywords",
        "creator": "creador",
        "producer": "productor",
        "creationDate": "fecha_creacion",
        "modDate": "fecha_modificacion",
    }
    return {claves.get(k, k): v for k, v in md.items() if k in claves and v}


def _normalizar_tipo_id(tipo_id):
    if tipo_id in (None, 0):
        return None
    return tipo_id


def _sanitizar_nombre_archivo(nombre):
    limpio = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in nombre)
    limpio = re.sub(r"_+", "_", limpio).strip("_")
    if not limpio:
        limpio = "documento"
    return limpio[:120]


def _nombre_descarga(doc):
    base = doc.get("titulo") or f"documento_{doc['id']}"
    limpio = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base).strip("_")
    if not limpio:
        limpio = f"documento_{doc['id']}"
    return limpio + ".pdf"


def _resolver_archivo_path(archivo_path):
    if not archivo_path:
        return None
    if os.path.isabs(archivo_path):
        return archivo_path
    return os.path.join(BASE_DIR, archivo_path)


def _respuesta_descarga(documento_id, inline=False):
    doc = obtener_documento(documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    archivo_path = _resolver_archivo_path(doc.get("archivo_path"))
    if not archivo_path or not os.path.isfile(archivo_path):
        raise HTTPException(status_code=404, detail="Archivo del documento no encontrado en disco")

    return FileResponse(
        path=archivo_path,
        media_type="application/pdf",
        filename=_nombre_descarga(doc),
        content_disposition_type="inline" if inline else "attachment",
    )


@router.post("", dependencies=[Depends(_validar_token_api)])
def subir_documento(
    archivo: UploadFile = File(..., description="Archivo PDF a subir e indexar."),
    titulo: str = Form(..., description="Titulo del documento para la biblioteca."),
    tipo_id: int = Form(..., description="Id del tipo de norma (GET /tipos-documento)."),
    fecha_publicacion: Optional[str] = Form(None, description="Fecha de publicacion en formato YYYY-MM-DD (opcional)."),
):
    """Sube un PDF, lo indexa con embeddings y lo verifica.

    Multipart/form-data. Extrae el texto con PyMuPDF, genera chunks y embeddings,
    luego ejecuta una verificacion de calidad inicial. El nombre fisico del
    archivo se limpia (quita caracteres invalidos de ruta conservando `.pdf`).
    """
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    fecha = None
    if fecha_publicacion:
        try:
            fecha = date.fromisoformat(fecha_publicacion)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha invalido. Use YYYY-MM-DD")

    nombre_base = _sanitizar_nombre_archivo(titulo)
    base_pdf, ext_pdf = os.path.splitext(archivo.filename)
    nombre_pdf = _sanitizar_nombre_archivo(base_pdf)
    nombre_pdf += (ext_pdf.lower() if ext_pdf else ".pdf")
    archivo_path = os.path.join(UPLOAD_DIR, f"{nombre_base}_{nombre_pdf}")
    with open(archivo_path, "wb") as f:
        content = archivo.file.read()
        f.write(content)

    try:
        doc = fitz.open(archivo_path)
        num_paginas = doc.page_count
        texto_completo = ""
        for pagina in doc:
            texto_completo += pagina.get_text()
        metadatos = _extraer_metadatos(doc.metadata)
        doc.close()

        if not texto_completo.strip():
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")

        resultado = procesar_documento(
            titulo=titulo,
            tipo_id=tipo_id,
            fecha_publicacion=fecha,
            archivo_path=os.path.relpath(archivo_path, BASE_DIR),
            contenido=texto_completo,
            num_paginas=num_paginas,
            metadatos=metadatos,
        )
    except Exception as exc:
        try:
            os.remove(archivo_path)
        except OSError:
            pass
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"No se pudo procesar el PDF: {str(exc)[:500]}") from exc

    try:
        verificacion = verificar_documento(resultado["documento_id"], num_preguntas=10)
    except Exception as exc:
        verificacion = {"error": f"Verificacion no completada: {str(exc)[:500]}"}

    return {
        "mensaje": "Documento procesado correctamente",
        "documento_id": resultado["documento_id"],
        "total_chunks": resultado["total_chunks"],
        "num_paginas": resultado["num_paginas"],
        "titulo": resultado["titulo"],
        "verificacion": verificacion,
    }


@router.get("")
def listado_documentos(
    limit: int = Query(100, ge=1, le=500, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todos los documentos sin paginar"),
    tipo_id: Optional[int] = Query(None, description="Filtrar por tipo de norma."),
    q: Optional[str] = Query(None, description="Filtro de texto por titulo."),
    creado_desde: Optional[date] = Query(None, description="Creado desde (YYYY-MM-DD)."),
    creado_hasta: Optional[date] = Query(None, description="Creado hasta (YYYY-MM-DD)."),
    orden: str = Query("creado_en", pattern="^(titulo|fecha|creado_en|chunks|prioridad)$", description="Campo de ordenamiento."),
    dir: str = Query("desc", pattern="^(asc|desc)$", description="Direccion del ordenamiento."),
):
    """Lista documentos indexados, con cantidad, paginación y filtros."""
    tipo_id = _normalizar_tipo_id(tipo_id)
    documentos, total = listar_documentos_filtrados(
        tipo_id=tipo_id,
        q=q,
        orden=orden,
        direccion=dir,
        limit=limit,
        skip=skip,
        todos=todos,
        creado_desde=creado_desde,
        creado_hasta=creado_hasta,
    )
    return SuccessResponse(message="Documentos listados", data=documentos, total=total)


@router.get("/{documento_id}")
def detalle_documento(documento_id: int):
    """Detalle de un documento: datos, metadatos PDF y total de chunks."""
    doc = obtener_documento(documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    chunks_total = contar_chunks_documento(documento_id)
    doc["total_chunks"] = chunks_total
    return doc


@router.get("/{documento_id}/descargar")
def descargar_documento(documento_id: int, inline: bool = Query(False, description="true = previsualizar en el navegador.")):
    """Descarga el PDF original del documento."""
    return _respuesta_descarga(documento_id, inline=inline)


@router.head("/{documento_id}/descargar")
def descargar_documento_head(documento_id: int, inline: bool = Query(False, description="true = previsualizar en el navegador.")):
    """Cabecera de la descarga (HEAD), util para enlaces."""
    return _respuesta_descarga(documento_id, inline=inline)


class DocumentoUpdate(BaseModel):
    titulo: str = Field(..., description="Nuevo titulo del documento.")
    tipo_id: int = Field(..., description="Nuevo tipo de norma (id).")
    fecha_publicacion: Optional[str] = Field(None, description="Fecha YYYY-MM-DD (opcional).")


@router.put("/{documento_id}", dependencies=[Depends(_validar_token_api)])
def editar_documento(documento_id: int, req: DocumentoUpdate):
    """Edita titulo, tipo y fecha de publicacion de un documento."""
    if not req.titulo.strip():
        raise HTTPException(status_code=400, detail="El titulo no puede estar vacio")

    if not obtener_documento(documento_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not obtener_tipo_documento(req.tipo_id):
        raise HTTPException(status_code=400, detail="Tipo de documento no valido")

    fecha = None
    if req.fecha_publicacion:
        try:
            fecha = date.fromisoformat(req.fecha_publicacion)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha invalido. Use YYYY-MM-DD")

    actualizar_documento(documento_id, req.titulo.strip(), req.tipo_id, fecha)
    return {"mensaje": "Documento actualizado correctamente"}


@router.get("/{documento_id}/chunks")
def chunks_documento(
    documento_id: int,
    limit: int = Query(100, ge=1, le=500, description="Cantidad a devolver (por orden del chunk)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="Devolver todos los chunks sin paginar"),
    q: Optional[str] = Query(None, description="Filtro de texto por contenido del chunk."),
):
    """Lista los chunks (fragmentos indexados) de un documento."""
    if not obtener_documento(documento_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    chunks, total = listar_chunks_documento_paginado(documento_id, q=q, limit=limit, skip=skip, todos=todos)
    return SuccessResponse(message="Chunks listados", data=chunks, total=total)


@router.delete("/{documento_id}", dependencies=[Depends(_validar_token_api)])
def borrar_documento(documento_id: int):
    """Elimina un documento y su archivo de disco."""
    doc = obtener_documento(documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    archivo_path = _resolver_archivo_path(doc.get("archivo_path"))
    eliminar_documento(documento_id)
    if archivo_path and os.path.isfile(archivo_path):
        try:
            os.remove(archivo_path)
        except OSError:
            pass
    return {"mensaje": "Documento eliminado correctamente"}


@router.post("/{documento_id}/verificar", dependencies=[Depends(_validar_token_api)])
def verificar(documento_id: int):
    """Evaluacion de calidad por documento: precision@1/3/5 y similitud."""
    if not obtener_documento(documento_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return verificar_documento(documento_id, num_preguntas=10)
