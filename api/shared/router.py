from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..auth.permisos import permiso_required
from ..response import SuccessResponse, DataListResponse, DataItemResponse
from .schemas import (
    DepartamentoCreate, DepartamentoUpdate, DepartamentoResponse,
    ProvinciaCreate, ProvinciaUpdate, ProvinciaResponse,
    MunicipioCreate, MunicipioUpdate, MunicipioResponse,
    CultivoCreate, CultivoUpdate, CultivoResponse,
    PecuarioCreate, PecuarioUpdate, PecuarioResponse,
    ManzanoCreate, ManzanoUpdate, ManzanoResponse,
    ComunidadCreate, ComunidadUpdate, ComunidadResponse,
    ResumenPoblacion, ResumenPoblacionUnidad,
)
from . import service


def create_shared_router(open_writes: bool = False) -> APIRouter:
    router = APIRouter(prefix="/shared")

    def _write_dep(action: str):
        if open_writes:
            return get_current_user
        return permiso_required("SISTEMA", action)

    TAG = "Geografía > Departamentos"

    @router.get("/departamentos", response_model=DataListResponse[DepartamentoResponse], tags=[TAG])
    def listar_departamentos(db: Session = Depends(get_db)):
        items = service.get_departamentos(db)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/departamentos/{id}", response_model=DataItemResponse[DepartamentoResponse], tags=[TAG])
    def obtener_departamento(id: int, db: Session = Depends(get_db)):
        result = service.get_departamento(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Departamento no encontrado")
        return SuccessResponse(message="Operación exitosa", data=result)

    @router.post("/departamentos", response_model=DataItemResponse[DepartamentoResponse], status_code=201, tags=[TAG])
    def crear_departamento(data: DepartamentoCreate, db: Session = Depends(get_db), _ua=Depends(_write_dep("CREATE"))):
        try:
            id = service.create_departamento(db, data)
            result = service.get_departamento(db, id)
            return SuccessResponse(message="Departamento creado exitosamente", data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/departamentos/{id}", response_model=DataItemResponse[DepartamentoResponse], tags=[TAG])
    def actualizar_departamento(id: int, data: DepartamentoUpdate, db: Session = Depends(get_db), _ua=Depends(_write_dep("UPDATE"))):
        result = service.update_departamento(db, id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Departamento no encontrado")
        return SuccessResponse(message="Departamento actualizado exitosamente", data=result)

    @router.delete("/departamentos/{id}", response_model=SuccessResponse, tags=[TAG])
    def eliminar_departamento(id: int, db: Session = Depends(get_db), _ua=Depends(_write_dep("DELETE"))):
        if not service.delete_departamento(db, id):
            raise HTTPException(status_code=404, detail="Departamento no encontrado")
        return SuccessResponse(message="Departamento eliminado")

    TAG = "Geografía > Provincias"

    @router.get("/provincias", response_model=DataListResponse[ProvinciaResponse], tags=[TAG])
    def listar_provincias(
        id_departamento: int | None = Query(None),
        db: Session = Depends(get_db),
    ):
        items = service.get_provincias(db, id_departamento)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/provincias/{id}", response_model=DataItemResponse[ProvinciaResponse], tags=[TAG])
    def obtener_provincia(id: int, db: Session = Depends(get_db)):
        result = service.get_provincia(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Provincia no encontrada")
        return SuccessResponse(message="Operación exitosa", data=result)

    @router.post("/provincias", response_model=DataItemResponse[ProvinciaResponse], status_code=201, tags=[TAG])
    def crear_provincia(data: ProvinciaCreate, db: Session = Depends(get_db), _ua=Depends(_write_dep("CREATE"))):
        try:
            id = service.create_provincia(db, data)
            result = service.get_provincia(db, id)
            return SuccessResponse(message="Provincia creada exitosamente", data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/provincias/{id}", response_model=DataItemResponse[ProvinciaResponse], tags=[TAG])
    def actualizar_provincia(id: int, data: ProvinciaUpdate, db: Session = Depends(get_db), _ua=Depends(_write_dep("UPDATE"))):
        result = service.update_provincia(db, id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Provincia no encontrada")
        return SuccessResponse(message="Provincia actualizada exitosamente", data=result)

    @router.delete("/provincias/{id}", response_model=SuccessResponse, tags=[TAG])
    def eliminar_provincia(id: int, db: Session = Depends(get_db), _ua=Depends(_write_dep("DELETE"))):
        if not service.delete_provincia(db, id):
            raise HTTPException(status_code=404, detail="Provincia no encontrada")
        return SuccessResponse(message="Provincia eliminada")

    TAG = "Geografía > Municipios"

    # ── IMPORTANTE: Rutas estáticas ANTES de /{id} para evitar conflicto de routing ──

    TAG_GEOJSON = "Geografía > GeoJSON"
    TAG_GEOM = "Geografía > GEOM/WKT"
    TAG_UBICACION = "Geografía > Ubicación"

    # ── GEOJSON (RFC 7946) ── compatible con Leaflet, OpenLayers, Google Maps, QGIS, Mapbox, kepler.gl

    @router.get("/municipios/geojson", tags=[TAG_GEOJSON],
                summary="Municipios en formato GeoJSON (FeatureCollection)",
                response_class=JSONResponse)
    def listar_municipios_geojson(
        id_provincia: int | None = Query(None, description="Filtrar por provincia"),
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        db: Session = Depends(get_db),
    ):
        """
        Retorna todos los municipios en formato **GeoJSON FeatureCollection** (RFC 7946).

        Compatible con: **Leaflet**, **OpenLayers**, **Google Maps**, **Mapbox GL JS**,
        **QGIS**, **ArcGIS**, **kepler.gl**, **deck.gl**, **GeoServer**, **MapProxy**.

        Ejemplos de uso:
        - Leaflet: `L.geoJSON(data).addTo(map)`
        - OpenLayers: `new ol.layer.Vector({source: new ol.source.Vector({format: new ol.format.GeoJSON(), url: '...'})})`
        - QGIS: Capa > Añadir capa > Vector > Protocolo: GeoJSON > URL del endpoint
        - Google Maps: `data.features.forEach(f => new google.maps.Data().addGeoJson(f))`
        - Mapbox: `map.addSource('municipios', {type: 'geojson', data: url})`
        """
        data = service.get_municipios_geojson(db, id_provincia, id_departamento)
        return JSONResponse(content=data)

    @router.get("/municipios/geom", tags=[TAG_GEOM],
                summary="Municipios con geometría en formato WKT (Well-Known Text)",
                response_class=JSONResponse)
    def listar_municipios_geom(
        id_provincia: int | None = Query(None, description="Filtrar por provincia"),
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        db: Session = Depends(get_db),
    ):
        """
        Retorna municipios con geometría en formato **WKT (Well-Known Text)**.

        Útil para: debug, consultas SQL directas, sistemas internos,
        herramientas que parsean WKT (PostGIS, Shapely, GEOS).

        Ejemplo WKT: `MULTIPOLYGON(((-68.12 -16.49, -68.11 -16.48, ...)))`
        """
        items = service.get_municipios_geom(db, id_provincia, id_departamento)
        return JSONResponse(content={
            "type": "GeometryCollection",
            "geometries": items,
            "total": len(items),
        })

    @router.get("/municipios/ubicacion", tags=[TAG_UBICACION],
                summary="Identificar municipio para un punto (lat, lon)",
                response_class=JSONResponse)
    def obtener_ubicacion(
        lat: float = Query(..., description="Latitud (ej: -16.4897)"),
        lon: float = Query(..., description="Longitud (ej: -68.1193)"),
        db: Session = Depends(get_db),
    ):
        """
        Dada una coordenada **(lat, lon)**, retorna el municipio, provincia y departamento
        que contienen ese punto usando `ST_Contains`.

        Compatible con GPS, formularios REA/EDAN, geolocalización de reportes.

        Ejemplo: `GET /api/v1/shared/municipios/ubicacion?lat=-16.4897&lon=-68.1193`
        """
        result = service.obtener_ubicacion(db, lat, lon)
        if not result:
            return JSONResponse(
                status_code=404,
                content={
                    "lat": lat,
                    "lon": lon,
                    "municipio": None,
                    "provincia": None,
                    "departamento": None,
                    "message": "No se encontró municipio para estas coordenadas",
                },
            )
        return JSONResponse(content=result)

    # ── CRUD Municipios (rutas con /{id} DEBEN ir DESPUÉS de las rutas estáticas) ──

    @router.get("/municipios", response_model=DataListResponse[MunicipioResponse], tags=[TAG])
    def listar_municipios(
        id_provincia: int | None = Query(None),
        id_departamento: int | None = Query(None),
        db: Session = Depends(get_db),
    ):
        items = service.get_municipios(db, id_provincia, id_departamento)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/municipios/{id}", response_model=DataItemResponse[MunicipioResponse], tags=[TAG])
    def obtener_municipio(id: int, db: Session = Depends(get_db)):
        result = service.get_municipio(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Municipio no encontrado")
        return SuccessResponse(message="Operación exitosa", data=result)

    @router.post("/municipios", response_model=DataItemResponse[MunicipioResponse], status_code=201, tags=[TAG])
    def crear_municipio(data: MunicipioCreate, db: Session = Depends(get_db), _ua=Depends(_write_dep("CREATE"))):
        try:
            id = service.create_municipio(db, data)
            result = service.get_municipio(db, id)
            return SuccessResponse(message="Municipio creado exitosamente", data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/municipios/{id}", response_model=DataItemResponse[MunicipioResponse], tags=[TAG])
    def actualizar_municipio(id: int, data: MunicipioUpdate, db: Session = Depends(get_db), _ua=Depends(_write_dep("UPDATE"))):
        result = service.update_municipio(db, id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Municipio no encontrado")
        return SuccessResponse(message="Municipio actualizado exitosamente", data=result)

    @router.delete("/municipios/{id}", response_model=SuccessResponse, tags=[TAG])
    def eliminar_municipio(id: int, db: Session = Depends(get_db), _ua=Depends(_write_dep("DELETE"))):
        if not service.delete_municipio(db, id):
            raise HTTPException(status_code=404, detail="Municipio no encontrado")
        return SuccessResponse(message="Municipio eliminado")

    # ── GEOJSON por ID (después de /{id} porque incluye geojson en el path) ──

    @router.get("/municipios/{id}/geojson", tags=[TAG_GEOJSON],
                summary="Un municipio en formato GeoJSON (Feature)",
                response_class=JSONResponse)
    def obtener_municipio_geojson(id: int, db: Session = Depends(get_db)):
        """
        Retorna un municipio individual en formato **GeoJSON Feature** (RFC 7946).
        Incluye bounding box para facilitar el zoom en el mapa.
        """
        result = service.get_municipio_geojson(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Municipio no encontrado")
        return JSONResponse(content=result)

    @router.get("/municipios/{id}/geom", tags=[TAG_GEOM],
                summary="Un municipio con geometría en formato WKT",
                response_class=JSONResponse)
    def obtener_municipio_geom(id: int, db: Session = Depends(get_db)):
        """
        Retorna un municipio individual con geometría en formato **WKT**.
        """
        result = service.get_municipio_geom(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Municipio no encontrado")
        return JSONResponse(content=result)

    TAG_CULTIVOS = "Catálogos > Cultivos"

    @router.get("/cultivos/grupos", response_model=DataListResponse[dict], tags=[TAG_CULTIVOS])
    def listar_grupos_cultivo(db: Session = Depends(get_db)):
        items = service.get_grupos_cultivo(db)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/cultivos", response_model=DataListResponse[CultivoResponse], tags=[TAG_CULTIVOS])
    def listar_cultivos(
        grupo: str | None = Query(None, description="Filtrar por grupo exacto (ej: Frutales)"),
        q: str | None = Query(None, description="Buscar por nombre parcial (ej: maiz)"),
        db: Session = Depends(get_db),
    ):
        items = service.get_cultivos(db, grupo, q)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/cultivos/{id}", response_model=DataItemResponse[CultivoResponse], tags=[TAG_CULTIVOS])
    def obtener_cultivo(id: int, db: Session = Depends(get_db)):
        result = service.get_cultivo(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Cultivo no encontrado")
        return SuccessResponse(message="Operación exitosa", data=result)

    @router.post("/cultivos", response_model=DataItemResponse[CultivoResponse], status_code=201, tags=[TAG_CULTIVOS])
    def crear_cultivo(data: CultivoCreate, db: Session = Depends(get_db), _ua=Depends(_write_dep("CREATE"))):
        result = service.create_cultivo(db, data)
        return SuccessResponse(message="Cultivo creado exitosamente", data=result)

    @router.put("/cultivos/{id}", response_model=DataItemResponse[CultivoResponse], tags=[TAG_CULTIVOS])
    def actualizar_cultivo(id: int, data: CultivoUpdate, db: Session = Depends(get_db), _ua=Depends(_write_dep("UPDATE"))):
        result = service.update_cultivo(db, id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Cultivo no encontrado")
        return SuccessResponse(message="Cultivo actualizado exitosamente", data=result)

    @router.delete("/cultivos/{id}", response_model=SuccessResponse, tags=[TAG_CULTIVOS])
    def eliminar_cultivo(id: int, db: Session = Depends(get_db), _ua=Depends(_write_dep("DELETE"))):
        result = service.delete_cultivo(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Cultivo no encontrado")
        return SuccessResponse(message="Cultivo eliminado exitosamente")

    TAG_PECUARIO = "Catálogos > Pecuaria"

    @router.get("/pecuario/grupos", response_model=DataListResponse[dict], tags=[TAG_PECUARIO])
    def listar_grupos_pecuario(db: Session = Depends(get_db)):
        items = service.get_grupos_pecuario(db)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/pecuario", response_model=DataListResponse[PecuarioResponse], tags=[TAG_PECUARIO])
    def listar_pecuario(
        grupo: str | None = Query(None, description="Filtrar por grupo exacto (ej: Camélidos)"),
        q: str | None = Query(None, description="Buscar por nombre parcial (ej: trucha)"),
        db: Session = Depends(get_db),
    ):
        items = service.get_pecuario(db, grupo, q)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/pecuario/{id}", response_model=DataItemResponse[PecuarioResponse], tags=[TAG_PECUARIO])
    def obtener_pecuario(id: int, db: Session = Depends(get_db)):
        result = service.get_pecuario_by_id(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Especie no encontrada")
        return SuccessResponse(message="Operación exitosa", data=result)

    @router.post("/pecuario", response_model=DataItemResponse[PecuarioResponse], status_code=201, tags=[TAG_PECUARIO])
    def crear_pecuario(data: PecuarioCreate, db: Session = Depends(get_db), _ua=Depends(_write_dep("CREATE"))):
        result = service.create_pecuario(db, data)
        return SuccessResponse(message="Especie creada exitosamente", data=result)

    @router.put("/pecuario/{id}", response_model=DataItemResponse[PecuarioResponse], tags=[TAG_PECUARIO])
    def actualizar_pecuario(id: int, data: PecuarioUpdate, db: Session = Depends(get_db), _ua=Depends(_write_dep("UPDATE"))):
        result = service.update_pecuario(db, id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Especie no encontrada")
        return SuccessResponse(message="Especie actualizada exitosamente", data=result)

    @router.delete("/pecuario/{id}", response_model=SuccessResponse, tags=[TAG_PECUARIO])
    def eliminar_pecuario(id: int, db: Session = Depends(get_db), _ua=Depends(_write_dep("DELETE"))):
        result = service.delete_pecuario(db, id)
        if not result:
            raise HTTPException(status_code=404, detail="Especie no encontrada")
        return SuccessResponse(message="Especie eliminada exitosamente")

    # ── CENSO 2024 (shared.manzanos / shared.comunidades) ──
    # Las rutas estáticas (*/geojson, /{tabla}/geojson) van ANTES de
    # /{codigo_ine} para evitar conflictos de routing (igual que en municipios).

    def _definir_rutas_censo(tabla: str, nombre_singular: str,
                             tag_crud: str, tag_geojson: str,
                             schema_create, schema_update, schema_response):
        nombre_recurso = f"{nombre_singular} censal (Censo 2024)"

        @router.get(f"/{tabla}", response_model=DataListResponse[schema_response], tags=[tag_crud])
        def listar_unidades_censo(
            id_municipio: int | None = Query(None, description="Filtrar por municipio"),
            codigo_ine: str | None = Query(None, description="Código INE exacto de la unidad"),
            q: str | None = Query(None, description="Buscar por nombre parcial"),
            area_oficial: str | None = Query(None, description="Urbana | Rural | Mixto"),
            limit: int | None = Query(None, ge=1, le=100000, description="Máx. de filas"),
            offset: int | None = Query(None, ge=0, description="Desplazamiento"),
            skip: int | None = Query(None, ge=0, description="Saltar registros (alias de offset)"),
            todos: bool = Query(False, description="true = devolver todos sin LIMIT/OFFSET"),
            db: Session = Depends(get_db),
        ):
            """Listado completo por defecto (`limit` vacío); `limit`/`skip`/`offset` paginan."""
            if skip is not None:
                offset = skip
            if todos:
                limit = None
                offset = None
            items = service.get_unidades_censo(db, tabla, id_municipio, codigo_ine, q,
                                               area_oficial, limit, offset)
            return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

        @router.get(f"/{tabla}/geojson", tags=[tag_geojson],
                    summary=f"{nombre_recurso}: FeatureCollection GeoJSON",
                    response_class=JSONResponse)
        def listar_unidades_censo_geojson(
            id_municipio: int | None = Query(None, description="Filtrar por municipio"),
            codigo_ine: str | None = Query(None, description="Código INE exacto de la unidad"),
            q: str | None = Query(None, description="Buscar por nombre parcial"),
            area_oficial: str | None = Query(None, description="Urbana | Rural | Mixto"),
            bbox: str | None = Query(None, description="Filtro espacial: 'minx,miny,maxx,maxy' (usa índice GIST)"),
            limit: int = Query(5000, ge=1, le=50000, description="Máx. de features"),
            db: Session = Depends(get_db),
        ):
            """
            Retorna unidades del Censo 2024 en **GeoJSON FeatureCollection** (RFC 7946)
            para mapas (Leaflet, OpenLayers, Mapbox, QGIS, Google Maps).

            Recomendado para consultas por mapa: usar `bbox` (recorte visible) y/o
            `id_municipio`; ambos aprovechan el índice espacial GIST.
            """
            try:
                return JSONResponse(content=service.get_unidades_censo_geojson(
                    db, tabla, id_municipio, codigo_ine, q, area_oficial, bbox, limit))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.get(f"/{tabla}/{{codigo_ine}}", response_model=DataItemResponse[schema_response], tags=[tag_crud])
        def obtener_unidad_censo(codigo_ine: str, db: Session = Depends(get_db)):
            result = service.get_unidad_censo(db, tabla, codigo_ine)
            if not result:
                raise HTTPException(status_code=404, detail=f"{nombre_recurso.title()} no encontrada")
            return SuccessResponse(message="Operación exitosa", data=result)

        @router.get(f"/{tabla}/{{codigo_ine}}/geojson", tags=[tag_geojson],
                    summary=f"{nombre_recurso}: GeoJSON Feature individual",
                    response_class=JSONResponse)
        def obtener_unidad_censo_geojson(codigo_ine: str, db: Session = Depends(get_db)):
            result = service.get_unidad_censo_geojson(db, tabla, codigo_ine)
            if not result:
                raise HTTPException(status_code=404, detail=f"{nombre_recurso.title()} no encontrada")
            return JSONResponse(content=result)

        @router.get(f"/{tabla}/{{codigo_ine}}/poblacion",
                    response_model=DataItemResponse[ResumenPoblacionUnidad],
                    tags=[tag_crud],
                    summary=f"{nombre_recurso}: personas y viviendas")
        def poblacion_unidad_censo(codigo_ine: str, db: Session = Depends(get_db)):
            result = service.get_poblacion_unidad(db, tabla, codigo_ine)
            if not result:
                raise HTTPException(status_code=404, detail=f"{nombre_recurso.title()} no encontrada")
            return SuccessResponse(message="Operación exitosa", data=result)

        @router.post(f"/{tabla}", response_model=DataItemResponse[schema_response],
                     status_code=201, tags=[tag_crud])
        def crear_unidad_censo(data: schema_create, db: Session = Depends(get_db),
                               _ua=Depends(_write_dep("CREATE"))):
            try:
                codigo_ine = service.create_unidad_censo(db, tabla, data)
                return SuccessResponse(message=f"{nombre_recurso.title()} creada exitosamente",
                                       data=service.get_unidad_censo(db, tabla, codigo_ine))
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @router.put(f"/{tabla}/{{codigo_ine}}", response_model=DataItemResponse[schema_response], tags=[tag_crud])
        def actualizar_unidad_censo(codigo_ine: str, data: schema_update,
                                    db: Session = Depends(get_db),
                                    _ua=Depends(_write_dep("UPDATE"))):
            result = service.update_unidad_censo(db, tabla, codigo_ine, data)
            if not result:
                raise HTTPException(status_code=404, detail=f"{nombre_recurso.title()} no encontrada")
            return SuccessResponse(message=f"{nombre_recurso.title()} actualizada exitosamente", data=result)

        @router.delete(f"/{tabla}/{{codigo_ine}}", response_model=SuccessResponse, tags=[tag_crud])
        def eliminar_unidad_censo(codigo_ine: str, db: Session = Depends(get_db),
                                  _ua=Depends(_write_dep("DELETE"))):
            if not service.delete_unidad_censo(db, tabla, codigo_ine):
                raise HTTPException(status_code=404, detail=f"{nombre_recurso.title()} no encontrada")
            return SuccessResponse(message=f"{nombre_recurso.title()} eliminada")

    TAG_CENSO_MANZ = "Censo 2024 > Manzanos"
    TAG_CENSO_COM = "Censo 2024 > Comunidades"
    TAG_CENSO_GEOJSON = "Censo 2024 > GeoJSON"

    _definir_rutas_censo(
        tabla="manzanos", nombre_singular="manzano",
        tag_crud=TAG_CENSO_MANZ, tag_geojson=TAG_CENSO_GEOJSON,
        schema_create=ManzanoCreate, schema_update=ManzanoUpdate,
        schema_response=ManzanoResponse,
    )
    _definir_rutas_censo(
        tabla="comunidades", nombre_singular="comunidad",
        tag_crud=TAG_CENSO_COM, tag_geojson=TAG_CENSO_GEOJSON,
        schema_create=ComunidadCreate, schema_update=ComunidadUpdate,
        schema_response=ComunidadResponse,
    )

    # ── CENSO 2024: Poblacion y viviendas (resumenes agregados) ──

    TAG_CENSO_POB = "Censo 2024 > Población y Viviendas"

    @router.get("/censo/poblacion/nacional",
                response_model=DataItemResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Totales nacionales de población y viviendas")
    def resumen_poblacion_nacional(db: Session = Depends(get_db)):
        return SuccessResponse(message="Operación exitosa",
                               data=service.resumen_censo_nacional(db))

    @router.get("/censo/poblacion/departamentos",
                response_model=DataListResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas por departamento")
    def resumen_poblacion_departamentos(
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        db: Session = Depends(get_db),
    ):
        items = service.resumen_censo_por_nivel(db, "departamento",
                                                id_departamento=id_departamento)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/censo/poblacion/provincias",
                response_model=DataListResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas por provincia")
    def resumen_poblacion_provincias(
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        id_provincia: int | None = Query(None, description="Filtrar por provincia"),
        db: Session = Depends(get_db),
    ):
        items = service.resumen_censo_por_nivel(db, "provincia",
                                                id_departamento=id_departamento,
                                                id_provincia=id_provincia)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/censo/poblacion/municipios",
                response_model=DataListResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas por municipio")
    def resumen_poblacion_municipios(
        id_departamento: int | None = Query(None, description="Filtrar por departamento"),
        id_provincia: int | None = Query(None, description="Filtrar por provincia"),
        id_municipio: int | None = Query(None, description="Filtrar por municipio"),
        db: Session = Depends(get_db),
    ):
        items = service.resumen_censo_por_nivel(db, "municipio",
                                                id_departamento=id_departamento,
                                                id_provincia=id_provincia,
                                                id_municipio=id_municipio)
        return SuccessResponse(message="Operación exitosa", data=items, total=len(items))

    @router.get("/censo/poblacion/departamento/{id}",
                response_model=DataItemResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas de un departamento")
    def resumen_poblacion_departamento(id: int, db: Session = Depends(get_db)):
        items = service.resumen_censo_por_nivel(db, "departamento", id_departamento=id)
        if not items:
            raise HTTPException(status_code=404, detail="Departamento sin datos censales")
        return SuccessResponse(message="Operación exitosa", data=items[0])

    @router.get("/censo/poblacion/provincia/{id}",
                response_model=DataItemResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas de una provincia")
    def resumen_poblacion_provincia(id: int, db: Session = Depends(get_db)):
        items = service.resumen_censo_por_nivel(db, "provincia", id_provincia=id)
        if not items:
            raise HTTPException(status_code=404, detail="Provincia sin datos censales")
        return SuccessResponse(message="Operación exitosa", data=items[0])

    @router.get("/censo/poblacion/municipio/{id}",
                response_model=DataItemResponse[ResumenPoblacion],
                tags=[TAG_CENSO_POB],
                summary="Población y viviendas de un municipio")
    def resumen_poblacion_municipio(id: int, db: Session = Depends(get_db)):
        items = service.resumen_censo_por_nivel(db, "municipio", id_municipio=id)
        if not items:
            raise HTTPException(status_code=404, detail="Municipio sin datos censales")
        return SuccessResponse(message="Operación exitosa", data=items[0])

    return router


router = create_shared_router(open_writes=False)
router_v2 = create_shared_router(open_writes=True)