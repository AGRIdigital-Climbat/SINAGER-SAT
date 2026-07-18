from pydantic import BaseModel


class ReporteEventoCreate(BaseModel):
    id_usuario: int
    id_departamento: int
    id_provincia: int
    id_municipio: int
    comunidad: str
    fecha_evento: str
    hora_evento: str | None = None
    id_tipo_evento: int
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None
    fotografia: str | None = None
    descripcion: str | None = None
    id_estado: int = 1
    categorias: list[int] | None = None


class ReporteEventoUpdate(BaseModel):
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    comunidad: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    id_tipo_evento: int | None = None
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None
    fotografia: str | None = None
    descripcion: str | None = None
    categorias: list[int] | None = None


class ReporteEventoResponse(BaseModel):
    id_reporte: int
    id_usuario: int
    id_departamento: int
    id_provincia: int
    id_municipio: int
    comunidad: str
    fecha_evento: str
    hora_evento: str | None = None
    fecha_reporte: str | None = None
    id_tipo_evento: int
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None
    fotografia: str | None = None
    descripcion: str | None = None
    id_estado: int

    class Config:
        from_attributes = True


class EstadoReporteCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int


class EstadoReporteUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class EstadoReporteResponse(BaseModel):
    id_estado: int
    nombre: str
    descripcion: str | None = None
    orden: int
    class Config:
        from_attributes = True


class AfectacionCategoriaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int


class AfectacionCategoriaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


class AfectacionCategoriaResponse(BaseModel):
    id_categoria: int
    nombre: str
    descripcion: str | None = None
    orden: int
    class Config:
        from_attributes = True


class ReporteAfectacionCreate(BaseModel):
    id_reporte: int
    id_categoria: int


class ReporteAfectacionResponse(BaseModel):
    id_reporte: int
    id_categoria: int
    class Config:
        from_attributes = True


class CambiarEstadoRequest(BaseModel):
    id_estado: int


class MessageResponse(BaseModel):
    message: str
    id: int | None = None
