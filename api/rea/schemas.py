from pydantic import BaseModel


# ── REA Reporte Evento ──

class ReporteDepartamento(BaseModel):
    id: int | None = None
    codigo_ine: str | None = None
    nombre: str | None = None

class ReporteProvincia(BaseModel):
    id: int | None = None
    codigo_ine: str | None = None
    nombre: str | None = None
    departamento: ReporteDepartamento | None = None

class ReporteMunicipio(BaseModel):
    id: int | None = None
    codigo_ine: str | None = None
    nombre: str | None = None
    departamento: ReporteDepartamento | None = None
    provincia: ReporteProvincia | None = None

class ReporteTipoEvento(BaseModel):
    id_tipo_evento: int | None = None
    nombre: str | None = None
    descripcion: str | None = None

class ReporteEstado(BaseModel):
    id_estado: int | None = None
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None

class ReporteCategoria(BaseModel):
    id_categoria: int | None = None
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None


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
    departamento: ReporteDepartamento | None = None
    provincia: ReporteProvincia | None = None
    municipio: ReporteMunicipio | None = None
    tipo_evento: ReporteTipoEvento | None = None
    estado: ReporteEstado | None = None
    categorias: list[ReporteCategoria] | None = None

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
