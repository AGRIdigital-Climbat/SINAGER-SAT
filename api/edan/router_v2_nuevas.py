"""APIs nuevas EDAN (Fase 2) — grupo Swagger "EDAN > APIs nuevas".

Contrato uuid-first (PLAN_APIS_V2_EDAN.md §3/§5/§12-§18):
- POST/PUT solo uuid; GET por uuid o id; respuestas con uuid e id.
- Upsert idempotente; LWW total: gana el último que llega (sin `version`, sin 409).
- Acceso igual que la API vieja: lectura por scope (6/7 propias, 8 municipio,
  5/9 departamento, 1-4 nacional); escritura solo roles 6/7 (require_rol).
"""
import hashlib

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth.permisos import module_permiso
from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse
from ..upload import _resolve_upload_path, save_upload_file
from . import service as service_viejo
from . import service_v2_edan_nuevas as svc_edan
from . import service_v2_nuevas as svc
from .schemas_v2_nuevas import (
    ConsolidarNuevoIn, FormularioCompletoUpsert, FormularioUpsert,
    SeccionUpsert, SyncAckRequest, SyncPushRequest, ViviendaUpsert,
)
from .utils import db_error, require_rol

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_BASE = "EDAN > APIs nuevas"
TAG_FORM = "EDAN > APIs nuevas > Formularios"
TAG_VIV = "EDAN > APIs nuevas > Viviendas"
TAG_FOTO = "EDAN > APIs nuevas > Fotografías"
TAG_SYNC = "EDAN > APIs nuevas > Sync"
TAG_EDAN = "EDAN > APIs nuevas > EDAN (cabecera)"

# Escritura solo roles locales (6/7), como require_rol(*ROLES_LOCALES) en la API vieja
_SOLO_67 = [Depends(require_rol(*svc.ROLES_LOCALES))]


# ===========================================================================
# Formularios (cabecera)
# ===========================================================================
@router.post("/formularios", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
             summary="Crear/actualizar formulario (upsert idempotente por uuid)")
def crear_formulario(payload: FormularioUpsert, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    data = svc.upsert_formulario(db, user, payload.model_dump(mode="json"))
    return SuccessResponse(message="Formulario guardado", data=data)


# OJO: registrar ANTES de PUT /formularios/{uuid_ref}: si no, "completo" lo
# captura la ruta parametrizada y exige coincidencia uuid de ruta/payload.
@router.put("/formularios/completo", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
            summary="Editar documento completo con detección de cambios (hubo_cambios; no-op = cero escrituras)")
def actualizar_formulario_completo(payload: FormularioCompletoUpsert,
                                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Mismo JSON que POST /formularios/completo (uuid en el cuerpo).

    El servidor compara con lo almacenado y solo escribe lo que difiere:
    - sin cambios reales -> `hubo_cambios=false`, `cambios=[]` y CERO
      escrituras (fecha_modificacion intacta: sin falsos tiene_cambios);
    - con cambios -> aplica el documento exacto (LWW) y devuelve
      `hubo_cambios=true` + `cambios` (secciones afectadas / "cabecera");
    - si el uuid no existe -> 404 (para crear use POST /formularios/completo).
    """
    data = svc.put_formulario_completo(db, user, payload.model_dump(mode="json"))
    msg = "Documento actualizado" if data.get("hubo_cambios") else "Documento sin cambios"
    return SuccessResponse(message=msg, data=data)



@router.put("/formularios/{uuid_ref}", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
            summary="Actualizar formulario (LWW: gana el último que llega)")
def actualizar_formulario(uuid_ref: str, payload: FormularioUpsert,
                          db: Session = Depends(get_db), user=Depends(get_current_user)):
    if str(payload.uuid_edan_localidad) != uuid_ref:
        raise HTTPException(status_code=400, detail="El uuid de la ruta y el del payload no coinciden")
    data = svc.upsert_formulario(db, user, payload.model_dump(mode="json"))
    return SuccessResponse(message="Formulario actualizado", data=data)



@router.get("/formularios", tags=[TAG_BASE, TAG_FORM],
            summary="Listar formularios COMPLETOS (documento por localidad: cabecera + secciones + fotos; scope por rol + filtros)")
def listar_formularios(
    limit: int = Query(50, ge=1, le=1000, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    modo: Literal["completo", "comprimido"] = Query(
        "comprimido",
        description="completo = SIEMPRE las 14 secciones (vacías si no hay filas); "
                    "comprimido = SOLO las secciones activas (flag imp_* true o con filas)"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio (trae TODO el municipio con todos=true)"),
    localidad: str | None = Query(None, description="Filtrar por nombre de localidad (ILIKE)"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601, filtra)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601, filtra)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601, filtra)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601, filtra)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601, filtra)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601, filtra)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Lista de **documentos completos** de localidad (NO sólo cabeceras): cada
    item es el mismo contrato que `GET /formularios/{uuid}/completo`:

    - `cabecera`: fila pública (`uuid_edan_localidad` + `id_edan_localidad`
      y demás ids; sin `version`/`id_local`/`id_seccion`) + **todo `id_*` con
      su objeto JSON recursivo** (§20.16 — `id_usuario -> usuario {…, rol}`,
      `id_importacion -> importacion`; dentro de los objetos: `usuario -> rol`,
      `municipio -> departamento/provincia`, `edan -> estado_edan/…`). Si
      `id_edan`/`id_importacion` es NULL, la clave viene en null. Identidad
      propia y la cadena `uuid_*` no llevan JSON (no tienen catálogo).
    - secciones con sus **filas reales** (claves legacy: `impacto_poblacion`,
      `danos_vivienda` con `viviendas[]` anidadas, …) + `fotos[]`.
    - `imp_*` (14) y los 9 `grup_*` sincronizados con verdad por datos; SIN
      nodo `grupos`.

    `modo` (default `comprimido`) = sólo secciones **activas**; `completo`
    entrega siempre las 14 claves de sección.

    Cantidad/paginación: `limit` (los más recientes primero), `skip`, o
    `todos=true` para el conjunto completo SIN paginar — p.ej.
    `?id_municipio=70101&todos=true` trae TODAS las localidades de ese
    municipio. Filtros geográficos combinables (AND) y **rangos de fecha**
    (`fecha_llenado_*`, `fecha_evento_*`, `fecha_modificacion_*` desde/hasta,
    también combinables). Scope por rol:
    **6 (UGR Municipio) = TODO su municipio** (API general con filtros, para
    poblar el mapa UGR), 7 = propias, 8 = municipio, 5/9 = departamento,
    1-4 = nacional. (`sync/pull` y `/formularios/estados` siguen siendo la
    vista del propio usuario.)"""
    data, total = svc.list_formularios(
        db, user, skip, limit, todos,
        id_departamento, id_provincia, id_municipio, localidad, modo=modo,
        fecha_llenado_desde=fecha_llenado_desde,
        fecha_llenado_hasta=fecha_llenado_hasta,
        fecha_evento_desde=fecha_evento_desde,
        fecha_evento_hasta=fecha_evento_hasta,
        fecha_modificacion_desde=fecha_modificacion_desde,
        fecha_modificacion_hasta=fecha_modificacion_hasta)
    return SuccessResponse(message="Formularios listados", data=data, total=total)


# OJO: registrar ANTES de GET /formularios/{uuid_ref}, si no "estados" lo
# captura la ruta parametrizada -> 400 "uuid no válido".
@router.get("/formularios/estados", tags=[TAG_BASE, TAG_FORM],
            summary="Listado ligero de estados de formularios (sync: id + uuid + estado)")
def listar_formularios_estados(
    limit: int = Query(200, ge=1, le=1000, description="Cantidad a devolver (los más recientes primero)"),
    skip: int = Query(0, ge=0, description="Saltar registros (paginación, sólo con limit)"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    localidad: str | None = Query(None, description="Filtrar por nombre de localidad (ILIKE)"),
    id_edan_localidad_estado: int | None = Query(None, description="Filtrar por estado de la localidad (id)"),
    estado: str | None = Query(None, description="Estado de la localidad por nombre (ILIKE, ej: 'aprobado')"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601, filtra)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601, filtra)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601, filtra)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601, filtra)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Watermark del cliente para el flag tiene_cambios (ISO 8601); NO filtra: el listado siempre devuelve todo el scope"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Listado LIGERO para refrescar badges de estado / sync (sin secciones).

    - `limit`: cantidad; siempre entrega los más recientes primero (por
      `fecha_modificacion` DESC).
    - `todos=true`: ignora `limit`/`skip` y devuelve el conjunto completo.
    - `skip`: offset, sólo tiene sentido junto a `limit`.
    - Filtros geográficos combinables con **AND** (`id_departamento`,
      `id_provincia`, `id_municipio`), igual que el resto de la familia.
    - `id_edan_localidad_estado` filtra por id; `estado` por nombre (ILIKE).
    - Rangos de fecha `fecha_llenado_*` y `fecha_evento_*` desde/hasta (AND).
      `fecha_modificacion_desde` es SOLO el watermark que computa
      `tiene_cambios` por fila (NO filtra).
    - Scope por rol (6/7 propias, 8 municipio, 5/9 departamento, 1-4 nacional).
    - `data` = `{items, resumen, total}`:
      - `items[]`: fila-cabecera ligera: `id_edan_localidad` +
        `uuid_edan_localidad` + `localidad` + `estado_localidad`
        {id, nombre, orden} + `pendiente_*` + `id_usuario` +
        los 9 `grup_*` planos (SIEMPRE = OR(miembros imp_*); las 14 `imp_*`
        se omiten para mantener el payload mínimo) + `es_huerfana` +
        **`tiene_cambios`**.
      - `resumen`: `{por_estado: [{id_edan_localidad_estado, estado, orden,
        cantidad}], por_grupo: [{grupo, cantidad}]}` — `por_estado` cuenta
        localidades por estado (espejo del resumen legacy); `por_grupo` cuenta
        localidades con `imp_*` de ese grupo en true (9 grupos, sin nodo).
      - `total` = número de `items`.

    **FLUJO DE LA APP (§20.15 — IMPORTANTE):** `tiene_cambios` es SIEMPRE
    booleano. La app, al ABRIR, consulta este listado con su watermark (la
    última `fecha_modificacion` que conoce): `true` = ese registro cambió en el
    servidor -> baja `GET /formularios/{uuid}/completo` (siempre queda
    actualizado de forma segura); `false` = nada que bajar. Sin
    `fecha_modificacion_desde`, todos los `tiene_cambios` son `false`.
    """
    out = svc.list_formularios_estados(
        db, user, skip, limit, todos,
        id_departamento=id_departamento, id_provincia=id_provincia,
        id_municipio=id_municipio, localidad=localidad,
        id_edan_localidad_estado=id_edan_localidad_estado,
        estado=estado,
        fecha_llenado_desde=fecha_llenado_desde,
        fecha_llenado_hasta=fecha_llenado_hasta,
        fecha_evento_desde=fecha_evento_desde,
        fecha_evento_hasta=fecha_evento_hasta,
        fecha_modificacion_desde=fecha_modificacion_desde)
    return SuccessResponse(message="Estados de formularios listados correctamente",
                           data=out, total=out["total"])


@router.get("/formularios/{uuid_ref}", tags=[TAG_BASE, TAG_FORM],
            summary="Obtener formulario por uuid o id: documento COMPLETO {cabecera (imp_* + grup_* planos), secciones, fotos, secciones_resumen}")
def obtener_formulario(
    uuid_ref: str,
    modo: Literal["completo", "comprimido"] = Query(
        "comprimido",
        description="completo = SIEMPRE las 14 secciones (vacías si no hay filas); "
                    "comprimido = SOLO las secciones activas (flag imp_* true o con filas)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """MISMO documento que `GET /formularios/{uuid_ref}/completo`
    (`{cabecera, secciones, fotos}`), más `secciones_resumen` (conteos,
    compatibilidad con los consumidores previos):

    - `cabecera`: **todo `id_*` con su objeto JSON anidado** (§20.16):
      `id_departamento/id_provincia/id_municipio/id_tipo_evento/
      id_tipo_localidad/id_edan_localidad_estado/id_usuario/id_edan/
      id_importacion` -> su objeto (si el id es NULL —ej. `id_edan` en las
      primeras creaciones— la clave viene en null), y los ids DENTRO de esos
      objetos también (`usuario -> rol`, `municipio -> departamento/provincia`,
      `edan -> estado_edan/municipio/tipo_evento`, `importacion -> usuario`).
      Sin nodo `grupos`: los 9 `grup_*` van planos en la cabecera
      (= OR de los `imp_*`, verdad por datos) junto a las 14 `imp_*`.
    - secciones con sus filas reales (claves legacy; `danos_vivienda` trae
      `viviendas[]` anidadas) + `fotos[]` — NO sólo cabecera. `modo` default
      `comprimido` = sólo secciones activas; `completo` = las 14.
    - `id_local` y `id_seccion` NO se exponen: las APIs nuevas van SOLO con
    uuid (`uuid_edan_localidad`, `uuid_registro`).

    Alcance: **rol 6 (UGR Municipio) LEE todo su municipio** (un marcador
    ajeno del mapa entra; fuera de su municipio -> 403); la escritura de rol 6
    sigue siendo solo sobre lo propio. Rol 7 = lo propio; 8/5/9 = su
    jurisdicción; 1-4 = nacional."""
    data = svc.get_formulario(db, uuid_ref, user, modo=modo)
    return SuccessResponse(message="Formulario obtenido", data=data)


@router.post("/formularios/completo", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
             summary="Crear formulario completo (SOLO creación:409 si ya existe; editar = PUT /formularios/completo)")
def crear_formulario_completo(payload: FormularioCompletoUpsert, db: Session = Depends(get_db),
                              user=Depends(get_current_user)):
    data = svc.upsert_formulario_completo(db, user, payload.model_dump(mode="json"))
    return SuccessResponse(message="Formulario completo creado", data=data)


# OJO: registrar DESPUÉS de POST /formularios/completo: si no, "completo" lo
# captura la ruta parametrizada (uuid_ref="completo" -> 400).
@router.post("/formularios/{uuid_ref}", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
             summary="Crear/actualizar formulario con uuid en la ruta (mismo upsert que POST /formularios)")
def crear_formulario_por_ruta(uuid_ref: str, payload: FormularioUpsert,
                              db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Alias de `POST /formularios` con la identidad en la RUTA (contrato
    marcado: `POST /formularios/{uuid}`). Mismo upsert idempotente LWW.

    **400** si el uuid de la ruta y el del payload no coinciden."""
    if str(payload.uuid_edan_localidad) != uuid_ref:
        raise HTTPException(status_code=400, detail="El uuid de la ruta y el del payload no coinciden")
    data = svc.upsert_formulario(db, user, payload.model_dump(mode="json"))
    return SuccessResponse(message="Formulario guardado", data=data)


@router.get("/formularios/{uuid_ref}/completo", tags=[TAG_BASE, TAG_FORM],
            summary="Obtener formulario completo por uuid o id: {cabecera, 14 secciones, fotos} — sin nodo grupos (grup_* planos en cabecera)")
def obtener_formulario_completo(
    uuid_ref: str,
    comprimido: bool = Query(False, description="true = sólo secciones ACTIVAS (imp_* true o con filas); false = las 14"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """`cabecera` con **todo `id_*` + su JSON anidado recursivo** (§20.16,
    igual que GET /formularios y /formularios/{uuid}: `id_usuario -> usuario`
    con `id_rol -> rol`, `importacion`, `estado_edan`, etc.; claves con id
    NULL —`edan` en primeras creaciones— vienen en null). `fotos[]` = fotos
    activas; las secciones traen la
    cadena `uuid_edan_localidad` (sin `id_local`/`id_seccion`: APIs nuevas
    solo uuid). El documento completo se reenvía tal cual
    por `PUT /formularios/completo` (round-trip: los objetos FK se descartan)."""
    data = svc.get_formulario_completo(db, uuid_ref, user, comprimido=comprimido)
    return SuccessResponse(message="Formulario completo obtenido", data=data)


@router.delete("/formularios/{uuid_ref}", tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
               summary="Borrar formulario (cascada: secciones, viviendas, fotos)")
def borrar_formulario(uuid_ref: str, db: Session = Depends(get_db),
                      user=Depends(get_current_user)):
    data = svc.delete_formulario(db, user, uuid_ref)
    return SuccessResponse(message="Formulario borrado", data=data)


# ===========================================================================
# Secciones (14 tipos) — se acepta guion o guion bajo: danos(-_)vivienda
# ===========================================================================
@router.post("/formularios/{uuid_loc}/secciones/{tipo}", tags=[TAG_BASE, TAG_FORM],
             dependencies=_SOLO_67,
             summary="Crear/actualizar fila de sección (upsert por uuid_registro)")
def crear_seccion(uuid_loc: str, tipo: str, payload: SeccionUpsert,
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.upsert_seccion(db, user, uuid_loc, tipo, payload.model_dump(mode="json"))
    return SuccessResponse(message=f"Sección {tipo} guardada", data=data)


@router.put("/formularios/{uuid_loc}/secciones/{tipo}/{uuid_fila}",
            tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
            summary="Actualizar fila de sección (LWW: gana el último que llega)")
def actualizar_seccion(uuid_loc: str, tipo: str, uuid_fila: str,
                       payload: SeccionUpsert, db: Session = Depends(get_db),
                       user=Depends(get_current_user)):
    data = svc.upsert_seccion(db, user, uuid_loc, tipo, payload.model_dump(mode="json"),
                              uuid_fila=uuid_fila)
    return SuccessResponse(message=f"Sección {tipo} actualizada", data=data)


@router.get("/formularios/{uuid_loc}/secciones/{tipo}", tags=[TAG_BASE, TAG_FORM],
            summary="Listar filas de una sección (danos-vivienda incluye viviendas[])")
def listar_seccion(uuid_loc: str, tipo: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    data = svc.get_seccion_filas(db, user, uuid_loc, tipo)
    return SuccessResponse(message=f"Sección {tipo} listada", data=data, total=len(data))


@router.get("/formularios/{uuid_loc}/secciones/{tipo}/{uuid_fila}",
            tags=[TAG_BASE, TAG_FORM],
            summary="Obtener una fila de sección por uuid")
def obtener_seccion(uuid_loc: str, tipo: str, uuid_fila: str,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.get_seccion_fila(db, user, uuid_loc, tipo, uuid_fila)
    return SuccessResponse(message=f"Sección {tipo} obtenida", data=data)


@router.delete("/formularios/{uuid_loc}/secciones/{tipo}/{uuid_fila}",
               tags=[TAG_BASE, TAG_FORM], dependencies=_SOLO_67,
               summary="Borrar fila de sección 1:N por uuid (1:1 responde 400)")
def borrar_seccion(uuid_loc: str, tipo: str, uuid_fila: str,
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.delete_seccion(db, user, uuid_loc, tipo, uuid_fila)
    return SuccessResponse(message=f"Fila de {tipo} borrada", data=data)


# ===========================================================================
# Viviendas (detalle 1:N de danos-vivienda)
# ===========================================================================
@router.post("/formularios/{uuid_loc}/secciones/danos-vivienda/{uuid_dano}/viviendas",
             tags=[TAG_BASE, TAG_VIV], dependencies=_SOLO_67,
             summary="Crear/actualizar vivienda (upsert por uuid_vivienda)")
def crear_vivienda(uuid_loc: str, uuid_dano: str, payload: ViviendaUpsert,
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.upsert_vivienda(db, user, uuid_dano, payload.model_dump(mode="json"))
    return SuccessResponse(message="Vivienda guardada", data=data)


@router.put("/formularios/{uuid_loc}/secciones/danos-vivienda/{uuid_dano}/viviendas/{uuid_v}",
            tags=[TAG_BASE, TAG_VIV], dependencies=_SOLO_67,
            summary="Actualizar vivienda (LWW: gana el último que llega)")
def actualizar_vivienda(uuid_loc: str, uuid_dano: str, uuid_v: str,
                        payload: ViviendaUpsert, db: Session = Depends(get_db),
                        user=Depends(get_current_user)):
    if str(payload.uuid_registro) != uuid_v:
        raise HTTPException(status_code=400, detail="El uuid de la ruta y el del payload no coinciden")
    data = svc.upsert_vivienda(db, user, uuid_dano, payload.model_dump(mode="json"))
    return SuccessResponse(message="Vivienda actualizada", data=data)


@router.get("/formularios/{uuid_loc}/secciones/danos-vivienda/{uuid_dano}/viviendas",
            tags=[TAG_BASE, TAG_VIV], summary="Listar viviendas de una fila de daños")
def listar_viviendas(uuid_loc: str, uuid_dano: str, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    data = svc.get_viviendas(db, user, uuid_dano)
    return SuccessResponse(message="Viviendas listadas", data=data, total=len(data))


@router.get("/formularios/{uuid_loc}/secciones/danos-vivienda/{uuid_dano}/viviendas/{uuid_v}",
            tags=[TAG_BASE, TAG_VIV], summary="Obtener una vivienda por uuid")
def obtener_vivienda(uuid_loc: str, uuid_dano: str, uuid_v: str,
                     db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.get_vivienda(db, user, uuid_dano, uuid_v)
    return SuccessResponse(message="Vivienda obtenida", data=data)


@router.delete("/formularios/{uuid_loc}/secciones/danos-vivienda/{uuid_dano}/viviendas/{uuid_v}",
               tags=[TAG_BASE, TAG_VIV], dependencies=_SOLO_67,
               summary="Borrar vivienda (cascada BD; el padre recalcula conteos)")
def borrar_vivienda(uuid_loc: str, uuid_dano: str, uuid_v: str,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = svc.delete_vivienda(db, user, uuid_dano, uuid_v)
    return SuccessResponse(message="Vivienda borrada", data=data)


# ===========================================================================
# Fotografías
# ===========================================================================
@router.post("/fotografias", tags=[TAG_BASE, TAG_FOTO], dependencies=_SOLO_67,
             summary="Subir foto (multipart): uuid_fotografia + tipo_entidad + uuid_registro + archivo")
async def subir_foto(
    uuid_fotografia: UUID = Form(..., description="Identidad permanente (cliente); reintento = mismo uuid"),
    tipo_entidad: str = Form(..., description="Tabla dueña: 14 secciones o 'vivienda'"),
    uuid_registro: str = Form(..., description="uuid de la fila dueña"),
    archivo: UploadFile = File(...),
    sha256: str | None = Form(None, description="Huella opcional del archivo (anti-duplicado)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    contents = await archivo.read()
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    digest = hashlib.sha256(contents).hexdigest()
    await archivo.seek(0)
    # municipio de la localidad dueña → el archivo se guarda en reports/{codigo_ine}
    dueño = svc._dueño_foto(db, svc._norm_tipo(tipo_entidad), UUID(str(uuid_registro)))
    ruta = await save_upload_file(archivo, db, id_municipio=dueño.get("id_municipio"),
                                  id_usuario=user.get("id_usuario"))
    data = svc.upsert_foto(db, user, str(uuid_fotografia), tipo_entidad, uuid_registro,
                           ruta, sha256 or digest, archivo.content_type, len(contents))
    return SuccessResponse(message="Foto guardada (upsert idempotente por uuid_fotografia)", data=data)


@router.get("/fotografias", tags=[TAG_BASE, TAG_FOTO],
            summary="Listar fotografías (paginado, con metadata + url_descarga)",
            description="Listado paginado de fotos **activas** (`borrado_logico=false`) para la "
                        "galería sin N+1: devuelve la metadata y `url_descarga` de cada foto en una "
                        "sola llamada.\n\n"
                        "Filtros AND: `id_edan_localidad` (id o uuid), `id_municipio`, `id_usuario`, "
                        "`tipo_entidad`, `fecha_creacion_*`, `fecha_modificacion_*`.\n\n"
                        "**Alcance**: las fotos son evidencia informativa → **no** tienen recorte "
                        "geográfico ni por dueño; cualquier usuario autenticado lista **todas** "
                        "(solo se exige token). `total` es el conteo real; usa `limit`/`skip` o "
                        "`todos=true`.")
def listar_fotografias(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    todos: bool = Query(False, description="true = devolver todas sin LIMIT/OFFSET"),
    id_edan_localidad: str | None = Query(None, description="Filtrar por localidad (id numérico o uuid_edan_localidad)"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio de la localidad dueña (FK shared.municipio)"),
    id_usuario: int | None = Query(None, description="Filtrar por usuario dueño de la localidad (id numérico)"),
    tipo_entidad: str | None = Query(None, description="Filtrar por tipo de entidad (p.ej. `danos_vivienda`)"),
    fecha_creacion_desde: datetime | None = Query(None, description="Filtrar por rango: fecha de creación (inclusive)"),
    fecha_creacion_hasta: datetime | None = Query(None, description="Filtrar por rango: fecha de creación (inclusive)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Filtrar por rango: fecha de modificación (inclusive)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Filtrar por rango: fecha de modificación (inclusive)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    data, total = svc.listar_fotografias(
        db, user, skip=skip, limit=limit, todos=todos,
        id_edan_localidad=id_edan_localidad, id_municipio=id_municipio,
        id_usuario=id_usuario,
        tipo_entidad=tipo_entidad,
        fecha_creacion_desde=fecha_creacion_desde, fecha_creacion_hasta=fecha_creacion_hasta,
        fecha_modificacion_desde=fecha_modificacion_desde, fecha_modificacion_hasta=fecha_modificacion_hasta)
    return SuccessResponse(message="Fotografías listadas correctamente", data=data, total=total)


@router.get("/fotografias/{uuid_foto}", tags=[TAG_BASE, TAG_FOTO],
            summary="Obtener foto por uuid (metadata + url_descarga)",
            description="Metadata de una foto activa por `uuid_fotografia` e incluye "
                        "`url_descarga`. Las fotos son evidencia informativa: solo se exige "
                        "token (sin scope de municipio/dueño).")
def obtener_foto(uuid_foto: str, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    data = svc.get_foto(db, user, uuid_foto)
    return SuccessResponse(message="Foto obtenida", data=data)


@router.get("/fotografias/{uuid_foto}/descargar", tags=[TAG_BASE, TAG_FOTO],
            summary="Descargar el binario de una foto por uuid",
            description="Sirve el archivo físico (binario) de la foto activa. Cualquier usuario "
                        "autenticado puede descargar cualquier foto (evidencia informativa, sin "
                        "scope geográfico). Usa la `url_descarga` que devuelve el listado. "
                        "Bloquea path-traversal dentro de `UPLOAD_DIR`.")
def descargar_foto(uuid_foto: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    info = svc.resolver_foto_descarga(db, user, uuid_foto)
    filepath = _resolve_upload_path(info["ruta_archivo"])
    if filepath is None or not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Archivo de la foto no encontrado")
    return FileResponse(path=str(filepath), media_type=info["mime_type"],
                        filename=info["nombre"])


@router.delete("/fotografias/{uuid_foto}", tags=[TAG_BASE, TAG_FOTO], dependencies=_SOLO_67,
               summary="Borrar foto (lógico; se propaga por pull)")
def borrar_foto(uuid_foto: str, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    data = svc.delete_foto(db, user, uuid_foto)
    return SuccessResponse(message="Foto borrada (lógico)", data=data)


# ===========================================================================
# Sync: pull / push / ack
# ===========================================================================
@router.get("/sync/pull", tags=[TAG_BASE, TAG_SYNC],
            summary="Pull incremental (filtrado por el alcance del rol): cambios + tombstones")
def sync_pull(
    desde: str | None = Query(None, description="ISO 8601; vacío o ausente = desde el inicio (restauración)"),
    limit: int = Query(500, ge=1, le=2000, description="Máx. por colección (exento de paginación)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """`formularios[]` trae la MISMA cabecera de los GET de la familia:
    **todo `id_*` con su objeto JSON anidado recursivo** (§20.16 —
    `id_usuario -> usuario` con `id_rol -> rol`, `importacion`,
    `estado_edan` incluidos; claves con id NULL —`edan` en primeras
    creaciones— vienen en null; sin `id_local`/`id_seccion`: APIs nuevas
    solo uuid). `secciones[]` con
    `tipo_seccion` + cadena `uuid_edan_localidad`; `viviendas[]`/`fotos[]`
    con su cadena de uuids; `tombstones[]` de lo borrado. Sin `version`."""
    dt = None
    if desde:
        try:
            dt = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"`desde` no es ISO 8601 válido: {desde!r}")
    data = svc.sync_pull(db, user, dt, limit)
    return SuccessResponse(message="Pull generado", data=data)


@router.post("/sync/push", tags=[TAG_BASE, TAG_SYNC], dependencies=_SOLO_67,
             summary="Push por lote (6/7): resultado por ítem (aplicado|error; LWW sin conflicto por version)")
def sync_push(payload: SyncPushRequest, db: Session = Depends(get_db),
              user=Depends(get_current_user)):
    data = svc.sync_push(db, user, [i.model_dump() for i in payload.items])
    return SuccessResponse(message="Lote procesado", data=data)


@router.post("/sync/ack", tags=[TAG_BASE, TAG_SYNC],
             summary="Confirmar recepción de un pull (watermark aplicado; cualquier rol EDAN)")
def sync_ack(payload: SyncAckRequest, db: Session = Depends(get_db),
             user=Depends(get_current_user)):
    data = svc.sync_ack(db, user, payload.id_dispositivo, payload.watermark)
    return SuccessResponse(message="Ack registrado", data=data)


# ===========================================================================
# EDAN padre (cabecera) — familia nueva (§20.17)
#
# OJO de enrutado: este bloque va AL FINAL del router.
#  - `GET /` y `GET /{ref}` (1 segmento) sólo pueden ir después de
#    `GET /formularios` (también 1 segmento) para no capturarlo.
#  - Con `("edan_cabecera", ...)` montado ANTES que `("edan_nuevas", ...)`
#    en main.V2_ROUTERS, los literals de la API vieja (`/mis-*`,
#    `/reportes/*`) siguen ganando y éstas ganan en los paths compartidos
#    (`/consolidar/pendientes`, `/{ref}/deshacer`, `POST /consolidar`,
#    `GET /{ref}`, `GET /`) — las rutas viejas ya no existen allí.
# ===========================================================================
@router.post("/consolidar", tags=[TAG_BASE, TAG_EDAN], dependencies=_SOLO_67,
             summary="Consolidar localidades en un EDAN nuevo (uuid: uuid_edan + localidades[]; legado DEPRECATED: localidad_ids[])")
def consolidar(payload: ConsolidarNuevoIn, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    """Crea la cabecera del EDAN consolidando localidades. **Dos formas
    exactamente (XOR):**

    **Canónica (uuid):** `uuid_edan` (identidad del EDAN, generada por el
    cliente; si no llega, la genera el servidor) + `localidades[]` con sus
    `uuid_edan_localidad` (sin `id_local`/`id_seccion` ni ids numéricos en
    la escritura). uuid de localidad desconocido → 404. **Idempotente**:
    reenviar el mismo `uuid_edan` con las mismas localidades devuelve el
    EDAN (200); si el uuid ya existe con otras localidades → 409.

    **Legada (DEPRECATED, body viejo POST /edan/consolidar):** `id_municipio`
    + `id_tipo_evento` + `localidad_ids[]` (ids numéricos). Vacío → 400
    "Debe incluir al menos una localidad"; id desconocido o mun+tipo
    incoherentes → 400 con el mensaje clásico (paridad exacta con la API
    vieja). Sin `uuid_edan` no hay idempotencia (el servidor genera la
    identidad, como antes). Migrar a la canónica: `GET /consolidar/pendientes`
    ya devuelve `localidades[]` con `uuid_edan_localidad`.

    Validaciones comunes (mismas que la API vieja): localidades aprobadas
    (estado 3), sin EDAN y del mismo municipio/tipo_evento — 400 con el
    mensaje clásico.

    Respuesta = EDAN completo estilo nuevo (misma forma que
    `GET /{ref}`): cabecera con **todo `id_*` + su JSON recursivo** (§20.16:
    `usuario_ugr`/`usuario_alcalde` con `rol`, `municipio`→`departamento`,
    `estado_edan`, `importacion`), `id_edan` + `uuid_edan`, localidades como
    documento `{cabecera, 14 secciones, fotos}` con id+uuid en todos los
    niveles, **sin `version` ni `id_local`** (LWW total)."""
    try:
        data = svc_edan.consolidar_nuevo(db, user, payload.model_dump(mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN consolidado correctamente", data=data)


@router.get("/consolidar/pendientes", tags=[TAG_BASE, TAG_EDAN],
            summary="Localidades huérfanas listas para consolidar (grupos con localidades id + uuid)")
def consolidar_pendientes(
    id_municipio: int | None = Query(None, description="Municipio del UGR (opcional; lo fuerza el scope)"),
    estado: str | None = Query(None, description="Estado de localidad (ILIKE, ej: 'aprobado')"),
    id_estado: int | None = Query(None, description="ID de estado específico"),
    limit: int | None = Query(None, ge=1, description="Grupos por página. Sin valor: sin límite"),
    skip: int = Query(0, ge=0, description="Grupos a saltar (paginación, sólo con limit)"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    fecha_llenado_desde: datetime | None = Query(None, description="Fecha de llenado desde (ISO 8601, filtra)"),
    fecha_llenado_hasta: datetime | None = Query(None, description="Fecha de llenado hasta (ISO 8601, filtra)"),
    fecha_evento_desde: datetime | None = Query(None, description="Fecha de evento desde (ISO 8601, filtra)"),
    fecha_evento_hasta: datetime | None = Query(None, description="Fecha de evento hasta (ISO 8601, filtra)"),
    fecha_modificacion_desde: datetime | None = Query(None, description="Última modificación desde (ISO 8601, filtra)"),
    fecha_modificacion_hasta: datetime | None = Query(None, description="Última modificación hasta (ISO 8601, filtra)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Mismo comportamiento que la API vieja (huérfanas `id_edan IS NULL`
    agrupadas por municipio+tipo_evento con conteos y totales; filtros
    `estado`/`id_estado` + **rangos de fecha** `fecha_llenado_*`,
    `fecha_evento_*` y `fecha_modificacion_*` desde/hasta (AND); scope
    5/8/9) con el cambio radical de los GET
    nuevos: **cada grupo trae `localidades[]` con `id_edan_localidad` +
    `uuid_edan_localidad`** (además de `localidad_ids` de siempre) y sus FK
    geográficas anidadas (§20.16: `municipio`/`provincia`/`departamento`/
    `tipo_evento`). `total` = total de grupos (sin paginar)."""
    data, total = svc_edan.pendientes_nuevo(
        db, user, id_municipio, estado, id_estado, limit, skip, todos,
        fecha_llenado_desde=fecha_llenado_desde,
        fecha_llenado_hasta=fecha_llenado_hasta,
        fecha_evento_desde=fecha_evento_desde,
        fecha_evento_hasta=fecha_evento_hasta,
        fecha_modificacion_desde=fecha_modificacion_desde,
        fecha_modificacion_hasta=fecha_modificacion_hasta)
    return SuccessResponse(message="EDAN localidades consolidadas listadas correctamente",
                           data=data, total=total)


@router.put("/{ref}/deshacer", tags=[TAG_BASE, TAG_EDAN], dependencies=_SOLO_67,
            summary="Deshacer consolidación de un EDAN (por uuid_edan o id; aplica y responde)")
def deshacer_edan(ref: str, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    """Disuelve un EDAN consolidado y lo elimina; sus localidades quedan
    huérfanas otra vez (`pendiente_actualizacion=true`, visibles por pull).

    Mismas validaciones que la API vieja: sólo rol 6/7, sólo EDAN en estado
    **Borrador**, sólo el UGR que lo consolidó, sin documentos en el
    repositorio. **Aplica directo** (sin modo preview).

    Respuesta nueva: `{edan: {id_edan, uuid_edan, codigo_edan},
    localidades_liberadas, localidades: [{id_edan_localidad,
    uuid_edan_localidad, localidad, id_edan: null}]}` — id + uuid en todos
    los niveles, sin `version`."""
    try:
        data = svc_edan.deshacer_nuevo(db, user, ref)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN deshecho correctamente", data=data)


@router.get("/", tags=[TAG_BASE, TAG_EDAN],
            summary="Listar EDANs con filtros (cabecera con id + uuid, FKs anidadas §20.16)")
def listar_edans(
    q: str | None = Query(None, description="Búsqueda por código/nombre (ILIKE)"),
    id_departamento: int | None = Query(None, description="Filtrar por departamento"),
    id_provincia: int | None = Query(None, description="Filtrar por provincia"),
    id_municipio: int | None = Query(None, description="Filtrar por municipio"),
    id_tipo_evento: int | None = Query(None, description="Filtrar por tipo de evento"),
    id_estado: int | None = Query(None, description="Filtrar por estado del EDAN"),
    estado: str | None = Query(None, description="Estado por nombre (ILIKE)"),
    id_usuario_ugr: int | None = Query(None, description="Filtrar por UGR responsable"),
    fecha_evento_desde: str | None = Query(None, description="Fecha de evento desde (ISO)"),
    fecha_evento_hasta: str | None = Query(None, description="Fecha de evento hasta (ISO)"),
    fecha_creacion_desde: str | None = Query(None, description="Fecha de creación desde (ISO)"),
    fecha_creacion_hasta: str | None = Query(None, description="Fecha de creación hasta (ISO)"),
    fecha_llenado_desde: str | None = Query(None, description="Fecha de llenado desde (ISO)"),
    fecha_llenado_hasta: str | None = Query(None, description="Fecha de llenado hasta (ISO)"),
    fecha_modificacion_desde: str | None = Query(None, description="Última modificación desde (ISO)"),
    fecha_modificacion_hasta: str | None = Query(None, description="Última modificación hasta (ISO)"),
    id_usuario_alcalde: int | None = Query(None, description="Alcalde responsable (id)"),
    id_importacion: int | None = Query(None, description="Importación que creó el EDAN (id)"),
    pendiente_eliminacion: bool | None = Query(None, description="Filtrar por pendiente_eliminacion"),
    pendiente_actualizacion: bool | None = Query(None, description="Filtrar por pendiente_actualizacion"),
    con_foto: bool | None = Query(None, description="Sólo con foto en alguna sección de alguna localidad"),
    sin_foto: bool | None = Query(None, description="Sólo sin foto en ninguna localidad"),
    imp_poblacion: bool | None = Query(None, description="Alguna localidad con impacto de población"),
    imp_salud: bool | None = Query(None, description="Alguna localidad con daños en salud"),
    imp_infraestructura: bool | None = Query(None, description="Alguna localidad con daños en infraestructura"),
    imp_servicios: bool | None = Query(None, description="Alguna localidad con daños en servicios básicos"),
    imp_educacion: bool | None = Query(None, description="Alguna localidad con daños en educación"),
    imp_vivienda: bool | None = Query(None, description="Alguna localidad con daños en vivienda"),
    imp_agropecuario: bool | None = Query(None, description="Alguna localidad con daños agropecuarios"),
    imp_proteccion: bool | None = Query(None, description="Alguna localidad con necesidades de protección"),
    imp_necesidades: bool | None = Query(None, description="Alguna localidad con necesidades humanitarias"),
    tiene_agricultura: bool | None = Query(None, description="Alguna localidad con daños a agricultura"),
    tiene_pecuario: bool | None = Query(None, description="Alguna localidad con daños pecuarios"),
    skip: int = Query(0, ge=0, description="EDAN a saltar (paginación, sólo con limit)"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad a devolver (los más recientes primero)"),
    todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Mismos filtros/scope que el `GET /` viejo (scope geográfico forzado;
    roles 6/7 ven sólo sus EDAN; `limit`+`skip`+`todos` convención de
    listados, orden `id_edan DESC` = recientes primero) con **rangos de
    fecha desde/hasta** (`fecha_evento_*`, `fecha_creacion_*`,
    `fecha_llenado_*`, `fecha_modificacion_*` — todos AND) y filtros
    `id_usuario_alcalde`/`id_importacion`, con items estilo
    nuevo: cabecera sin `version`/`id_local` + **todo `id_*` con su JSON
    recursivo** (§20.16: `usuario_ugr`→`usuario`→`rol`, `municipio`→
    `departamento`, `estado_edan`, `importacion`) + `uuid_edan` junto a
    `id_edan` + `num_localidades` + `localidades[]` como documentos completos
    `{cabecera, 14 secciones, fotos}` con id+uuid en todos los niveles (la
    API vieja también devolvía sus localidades inline)."""
    f = {
        "q": q, "id_departamento": id_departamento, "id_provincia": id_provincia,
        "id_municipio": id_municipio, "id_tipo_evento": id_tipo_evento,
        "id_estado": id_estado, "estado": estado, "id_usuario_ugr": id_usuario_ugr,
        "fecha_evento_desde": fecha_evento_desde, "fecha_evento_hasta": fecha_evento_hasta,
        "fecha_creacion_desde": fecha_creacion_desde,
        "fecha_creacion_hasta": fecha_creacion_hasta,
        "fecha_llenado_desde": fecha_llenado_desde,
        "fecha_llenado_hasta": fecha_llenado_hasta,
        "fecha_modificacion_desde": fecha_modificacion_desde,
        "fecha_modificacion_hasta": fecha_modificacion_hasta,
        "id_usuario_alcalde": id_usuario_alcalde,
        "id_importacion": id_importacion,
        "pendiente_eliminacion": pendiente_eliminacion,
        "pendiente_actualizacion": pendiente_actualizacion,
        "con_foto": con_foto, "sin_foto": sin_foto,
        "imp_poblacion": imp_poblacion, "imp_salud": imp_salud,
        "imp_infraestructura": imp_infraestructura, "imp_servicios": imp_servicios,
        "imp_educacion": imp_educacion, "imp_vivienda": imp_vivienda,
        "imp_agropecuario": imp_agropecuario, "imp_proteccion": imp_proteccion,
        "imp_necesidades": imp_necesidades,
        "tiene_agricultura": tiene_agricultura, "tiene_pecuario": tiene_pecuario,
    }
    f.update(service_viejo.scope_geografico(user))
    if user["id_rol"] in (6, 7) and f.get("id_usuario_ugr") is None:
        f["id_usuario_ugr"] = user["id_usuario"]
    data, total = svc_edan.listar_edans_nuevo(db, user, f, skip, limit, todos)
    return SuccessResponse(message="EDANs listados correctamente", data=data, total=total)


@router.get("/{ref}", tags=[TAG_BASE, TAG_EDAN],
            summary="Obtener EDAN completo por uuid_edan o id (detallado o compacto)")
def obtener_edan(
    ref: str,
    modo: Literal["detallado", "compacto"] = Query(
        "detallado", description="detallado = localidades con las 14 secciones; "
                                 "compacto = sólo secciones con datos + sumatorias"),
    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """**GET por uuid o id** (`uuid_edan` o `id_edan` numérico) — cambio
    radical vs. la API vieja: sin `id_local` y con **id + uuid en todos los
    niveles**.

    - Cabecera: columnas públicas de `edan.edan` (sin `version`, sin
      `id_local` — LWW total) + `uuid_edan` + **todo `id_*` con su JSON
      recursivo** (§20.16: `usuario_ugr`/`usuario_alcalde` → `usuario` →
      `rol`, `municipio` → `departamento`/`provincia`, `id_tipo_evento`,
      `id_estado` → `estado_edan`, `id_importacion` → `importacion`).
    - `localidades[]`: cada localidad como documento `{cabecera, 14 secciones,
      fotos}` (mismo formato que `GET /formularios/{uuid}/completo`, con
      `uuid_edan_localidad` + `id_edan_localidad` en cabecera y filas).
    - `resumen_secciones` + `reportes_rea` (como siempre); `modo=compacto`
      agrega `sumatorias` y comprime las secciones de cada localidad.
    - Fuera del alcance geográfico del rol (5/8/9) → 403."""
    try:
        data = svc_edan.get_edan_nuevo(db, user, ref, modo=modo)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)
    return SuccessResponse(message="EDAN obtenido correctamente", data=data)
