from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from sqlalchemy.orm import Session
from ..dependencies import get_current_user
from ..database import get_db
from ..response import SuccessResponse
from . import service
from ..auth.permisos import module_permiso
from ..upload import save_upload_file
from .utils import require_rol, db_error

router = APIRouter(prefix="/edan", dependencies=[Depends(module_permiso("EDAN"))])

TAG_DANOS_VIALES_CON_FOTO = "EDAN_LOCALIDADES > Danos Viales (con foto)"
TAG_DANOS_INFRA_CON_FOTO = "EDAN_LOCALIDADES > Danos Infra Publica (con foto)"
TAG_DANOS_VIVIENDA_CON_FOTO = "EDAN_LOCALIDADES > Danos Vivienda (con foto)"
TAG_DANOS_AGRICULTURA_CON_FOTO = "EDAN_LOCALIDADES > Danos Agricultura (con foto)"
TAG_DANOS_PECUARIOS_CON_FOTO = "EDAN_LOCALIDADES > Danos Pecuario (con foto)"
TAG_SALUD_CON_FOTO = "EDAN_LOCALIDADES > Salud Establecimientos (con foto)"
TAG_SERVICIOS_CON_FOTO = "EDAN_LOCALIDADES > Servicios Basicos (con foto)"
TAG_UNIDADES_CON_FOTO = "EDAN_LOCALIDADES > Unidades Educativas (con foto)"
TAG_INFRA_PROD_CON_FOTO = "EDAN_LOCALIDADES > Infra Productiva (con foto)"

ROLES_LOCALES = (6, 7)


async def _upload_to_localidad(file: UploadFile, db: Session, id_localidad: str, _user: dict) -> str:
    id_edan = service._resolve_localidad_id(db, id_localidad)
    row = service._row(db, "SELECT id_municipio FROM edan.edan_localidades WHERE id_edan_localidad = :id",
                       {"id": id_edan})
    if not row:
        raise HTTPException(status_code=404, detail=f"Localidad {id_edan} no encontrada")
    return await save_upload_file(file, db, row["id_municipio"], _user.get("id_usuario"))


def _validar_foto_gps(file: UploadFile | None, coordenada_lat: float | None, coordenada_lon: float | None) -> None:
    if file is not None and (coordenada_lat is None or coordenada_lon is None):
        raise HTTPException(status_code=422, detail="Foto requiere coordenadas GPS (coordenada_lat y coordenada_lon)")


# ============================================================================
#  ENDPOINTS CON-FOTO (multipart: foto + coordenadas + campos)
#  Lógica v2: id_localidad puede ser UUID (id_local) o int (id_edan_localidad);
#  file es OPCIONAL (regla 6.3: sin foto permite datos y/o GPS; foto exige GPS).
# ============================================================================

@router.post("/localidades/{id_localidad}/danos-viales/con-foto", status_code=201, tags=[TAG_DANOS_VIALES_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear daño vial con foto+GPS (multipart)")
async def crear_danos_viales_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    via: bool = Form(False),
    puente: bool = Form(False),
    tramo: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    km_danio: float | None = Form(None),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None, description="Latitud GPS"),
    coordenada_lon: float | None = Form(None, description="Longitud GPS"),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_dano_vial(db, id_edan, {
            "via": via, "puente": puente, "tramo": tramo,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "km_danio": km_danio,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Daño vial creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/danos-infra-publica/con-foto", status_code=201, tags=[TAG_DANOS_INFRA_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear daño infraestructura pública con foto+GPS")
async def crear_danos_infra_publica_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    comunidad: str = Form(""),
    tipo_estructura: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_dano_infra_publica(db, id_edan, {
            "comunidad": comunidad, "tipo_estructura": tipo_estructura,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Daño infraestructura pública creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/danos-vivienda/con-foto", status_code=201, tags=[TAG_DANOS_VIVIENDA_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear daño vivienda con foto+GPS")
async def crear_danos_vivienda_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    comunidad: str = Form(""),
    dano_parcial: int = Form(0),
    dano_total: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_dano_vivienda(db, id_edan, {
            "comunidad": comunidad,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Daño vivienda creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/danos-agricultura/con-foto", status_code=201, tags=[TAG_DANOS_AGRICULTURA_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear daño agricultura con foto+GPS")
async def crear_danos_agricultura_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    tipo_cultivo: str = Form(""),
    id_cultivo: int | None = Form(None),
    hectareas_afectadas: int = Form(0),
    hectareas_perdidas: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_dano_agricultura(db, id_edan, {
            "tipo_cultivo": tipo_cultivo, "id_cultivo": id_cultivo,
            "hectareas_afectadas": hectareas_afectadas,
            "hectareas_perdidas": hectareas_perdidas,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Daño agricultura creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/danos-pecuarios/con-foto", status_code=201, tags=[TAG_DANOS_PECUARIOS_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear daño pecuario con foto+GPS")
async def crear_danos_pecuarios_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    especie: str = Form(""),
    id_especie: int | None = Form(None),
    raza: str = Form(""),
    animales_afectados: int = Form(0),
    animales_muertos: int = Form(0),
    necesidades_inmediatas: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_dano_pecuario(db, id_edan, {
            "especie": especie, "id_especie": id_especie, "raza": raza,
            "animales_afectados": animales_afectados,
            "animales_muertos": animales_muertos,
            "necesidades_inmediatas": necesidades_inmediatas,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Daño pecuario creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/salud-establecimientos/con-foto", status_code=201, tags=[TAG_SALUD_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear establecimiento salud con foto+GPS")
async def crear_salud_establecimiento_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    nombre_establecimiento: str = Form(""),
    comunidad: str = Form(""),
    nivel_atencion: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    medicos_afectados: int = Form(0),
    enfermeras_afectadas: int = Form(0),
    otros_afectados: int = Form(0),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_establecimiento_salud(db, id_edan, {
            "nombre_establecimiento": nombre_establecimiento, "comunidad": comunidad,
            "nivel_atencion": nivel_atencion,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "medicos_afectados": medicos_afectados,
            "enfermeras_afectadas": enfermeras_afectadas,
            "otros_afectados": otros_afectados,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Establecimiento salud creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/servicios-basicos/con-foto", status_code=201, tags=[TAG_SERVICIOS_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear servicio básico con foto+GPS")
async def crear_servicios_basicos_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    tipo: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    necesidades_inmediatas: str = Form(""),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_servicio_basico(db, id_edan, {
            "tipo": tipo,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "necesidades_inmediatas": necesidades_inmediatas,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Servicio básico creado con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/unidades-educativas/con-foto", status_code=201, tags=[TAG_UNIDADES_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear unidad educativa con foto+GPS")
async def crear_unidades_educativas_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    nombre_establecimiento: str = Form(""),
    comunidad: str = Form(""),
    dano_parcial: bool = Form(False),
    dano_total: bool = Form(False),
    suspension_clases: bool | None = Form(None),
    perdida_material: bool | None = Form(None),
    funciona_albergue: bool | None = Form(None),
    estudiantes: int = Form(0),
    profesores: int = Form(0),
    administrativos: int = Form(0),
    observaciones: str = Form(""),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_unidad_educativa(db, id_edan, {
            "nombre_establecimiento": nombre_establecimiento, "comunidad": comunidad,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "suspension_clases": suspension_clases,
            "perdida_material": perdida_material,
            "funciona_albergue": funciona_albergue,
            "estudiantes": estudiantes, "profesores": profesores,
            "administrativos": administrativos,
            "observaciones": observaciones,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Unidad educativa creada con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


@router.post("/localidades/{id_localidad}/infra-productiva/con-foto", status_code=201, tags=[TAG_INFRA_PROD_CON_FOTO],
             dependencies=[Depends(require_rol(*ROLES_LOCALES))],
             summary="Crear infraestructura productiva con foto+GPS")
async def crear_infra_productiva_con_foto(
    id_localidad: str,
    file: UploadFile | None = File(None, description="Imagen JPG/PNG, max 5MB (opcional)"),
    tipo: str = Form(""),
    dano_parcial: int = Form(0),
    dano_total: int = Form(0),
    coordenada_lat: float | None = Form(None),
    coordenada_lon: float | None = Form(None),
    id_seccion: str | None = Form(None, description="ID único offline (UPSERT por id_seccion)"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        _validar_foto_gps(file, coordenada_lat, coordenada_lon)
        id_edan = service._resolve_localidad_id(db, id_localidad)
        fotografia = await _upload_to_localidad(file, db, str(id_edan), _user) if file else ""
        result = service.create_infra_productiva(db, id_edan, {
            "tipo": tipo,
            "dano_parcial": dano_parcial, "dano_total": dano_total,
            "fotografia": fotografia,
            "coordenada_lat": coordenada_lat,
            "coordenada_lon": coordenada_lon,
            "id_seccion": id_seccion,
        })
        db.commit()
        return SuccessResponse(message="Infraestructura productiva creada con foto correctamente", data=result)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise db_error(e)


# ============================================================================
#  LOCALIDADES POR MUNICIPIO (UGR)
# ============================================================================

@router.get("/localidades/municipio/{id_municipio}",
            tags=[TAG_DANOS_VIALES_CON_FOTO], responses={200: {"model": SuccessResponse}},
            summary="Todas las localidades de un municipio",
            description="Devuelve TODAS las localidades de un municipio (huérfanas + consolidadas),\n"
                        "de TODOS los usuarios, con la estructura completa (14 secciones anidadas).\n\n"
                        "El UGR municipality usa esto para ver todo lo que se está reportando en su zona.\n\n"
                        "Filtros opcionales: tipo de evento, estado, solo huérfanas/consolidadas,\n"
                        "usuario creador, con/sin foto.")
def listar_localidades_municipio(
    id_municipio: int,
    id_tipo_evento: int | None = Query(None, description="Filtrar por tipo de evento"),
    id_estado: int | None = Query(None, description="ID de estado de localidad"),
    estado: str | None = Query(None, description="Nombre de estado (ILIKE, ej: 'aprobado')"),
    solo_huerfanas: bool | None = Query(None, description="True=solo huérfanas, False=solo consolidadas, None=todas"),
    id_usuario: int | None = Query(None, description="Filtrar por usuario creador"),
    con_foto: bool | None = Query(None, description="True=solo con foto, False=solo sin foto, None=todas"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data, total = service.listar_localidades_municipio(
        db, id_municipio=id_municipio, id_tipo_evento=id_tipo_evento,
        id_estado=id_estado, estado_nombre=estado, solo_huerfanas=solo_huerfanas,
        id_usuario=id_usuario, con_foto=con_foto, skip=skip, limit=limit)
    return SuccessResponse(message="Localidades del municipio listadas correctamente",
                           data=data, total=total)


@router.get("/localidades/municipio/{id_municipio}/resumen",
            tags=[TAG_DANOS_VIALES_CON_FOTO], responses={200: {"model": SuccessResponse}},
            summary="Resumen ejecutivo de localidades por municipio",
            description="Conteos agregados de todas las localidades de un municipio:\n"
                        "total, huérfanas vs consolidadas, por estado, por tipo de evento,\n"
                        "totales de población/familias afectadas.")
def resumen_localidades_municipio(
    id_municipio: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    data = service.resumen_localidades_municipio(db, id_municipio)
    return SuccessResponse(message="Resumen de localidades del municipio generado correctamente",
                           data=data)