from pydantic import BaseModel


# ── EDAN PRINCIPAL ──

class EdanDepartamento(BaseModel):
    id: int
    codigo_ine: str | None = None
    nombre: str | None = None

class EdanMunicipio(BaseModel):
    id: int
    codigo_ine: str | None = None
    nombre: str | None = None

class EdanCreate(BaseModel):
    codigo_edan: str | None = None
    id_departamento: int | None = None
    id_municipio: int | None = None
    nombre_alcalde: str | None = None
    telefono_alcalde: str | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    localidades_afectadas: int = 0
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    nombre_responsable: str | None = None
    cargo_responsable: str | None = None
    telefono_responsable: str | None = None
    email_responsable: str | None = None
    usuario_registro: int | None = None
    id_reporte_rea: int | None = None
    fotografia: str | None = None


class EdanUpdate(BaseModel):
    codigo_edan: str | None = None
    id_departamento: int | None = None
    id_municipio: int | None = None
    nombre_alcalde: str | None = None
    telefono_alcalde: str | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    localidades_afectadas: int | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    nombre_responsable: str | None = None
    cargo_responsable: str | None = None
    telefono_responsable: str | None = None
    email_responsable: str | None = None
    id_reporte_rea: int | None = None
    fotografia: str | None = None


class EdanResponse(BaseModel):
    id_edan: int
    codigo_edan: str | None = None
    id_departamento: int | None = None
    id_municipio: int | None = None
    nombre_alcalde: str | None = None
    telefono_alcalde: str | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    hora_evento: str | None = None
    localidades_afectadas: int | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    nombre_responsable: str | None = None
    cargo_responsable: str | None = None
    telefono_responsable: str | None = None
    email_responsable: str | None = None
    usuario_registro: int | None = None
    id_reporte_rea: int | None = None
    fotografia: str | None = None
    departamento: EdanDepartamento | None = None
    municipio: EdanMunicipio | None = None

    class Config:
        from_attributes = True


# ── CATÁLOGOS ──

class TipoEventoCreate(BaseModel):
    nombre: str
    descripcion: str | None = None

class TipoEventoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None

class TipoEventoResponse(BaseModel):
    id_tipo_evento: int
    nombre: str
    descripcion: str | None = None
    class Config:
        from_attributes = True


class GrupoEtarioCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    orden: int | None = None

class GrupoEtarioUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    orden: int | None = None

class GrupoEtarioResponse(BaseModel):
    id_grupo_etario: int
    nombre: str
    descripcion: str | None = None
    orden: int | None = None
    class Config:
        from_attributes = True


class ServicioBasicoCreate(BaseModel):
    nombre: str
    descripcion: str | None = None

class ServicioBasicoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None

class ServicioBasicoResponse(BaseModel):
    id_servicio_basico: int
    nombre: str
    descripcion: str | None = None
    class Config:
        from_attributes = True


class CategoriaProteccionCreate(BaseModel):
    nombre: str
    descripcion: str | None = None

class CategoriaProteccionUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None

class CategoriaProteccionResponse(BaseModel):
    id_categoria_proteccion: int
    nombre: str
    descripcion: str | None = None
    class Config:
        from_attributes = True


class AyudaHumanitariaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None

class AyudaHumanitariaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None

class AyudaHumanitariaResponse(BaseModel):
    id_ayuda_humanitaria: int
    nombre: str
    descripcion: str | None = None
    class Config:
        from_attributes = True


# ── SUB-TABLAS ──

class PoblacionGrupoGrupoEtario(BaseModel):
    id_grupo_etario: int
    nombre: str | None = None
    descripcion: str | None = None

class PoblacionGrupoCreate(BaseModel):
    id_edan: int
    id_grupo_etario: int
    fallecidos: int = 0
    heridos: int = 0
    desaparecidos: int = 0
    observaciones: str | None = None

class PoblacionGrupoResponse(BaseModel):
    id_poblacion_grupo: int
    id_edan: int
    id_grupo_etario: int
    fallecidos: int | None = None
    heridos: int | None = None
    desaparecidos: int | None = None
    observaciones: str | None = None
    grupo_etario: PoblacionGrupoGrupoEtario | None = None
    class Config:
        from_attributes = True


class EdanTipoEventoTipoEvento(BaseModel):
    id_tipo_evento: int
    nombre: str | None = None
    descripcion: str | None = None

class EdanTipoEventoCreate(BaseModel):
    id_edan: int
    id_tipo_evento: int

class EdanTipoEventoResponse(BaseModel):
    id_tipo_evento_edan: int
    id_edan: int
    id_tipo_evento: int
    tipo_evento: EdanTipoEventoTipoEvento | None = None
    class Config:
        from_attributes = True


class PrimeraRespuestaCreate(BaseModel):
    id_edan: int
    busqueda_requerimiento: bool | None = None
    busqueda_observaciones: str | None = None
    salvamento_requerimiento: bool | None = None
    salvamento_observaciones: str | None = None
    evacuacion_requerimiento: bool | None = None
    evacuacion_observaciones: str | None = None
    otros_requerimiento: bool | None = None
    otros_observaciones: str | None = None
    observaciones_generales: str | None = None

class PrimeraRespuestaResponse(BaseModel):
    id_primera_respuesta: int
    id_edan: int
    busqueda_requerimiento: bool | None = None
    busqueda_observaciones: str | None = None
    salvamento_requerimiento: bool | None = None
    salvamento_observaciones: str | None = None
    evacuacion_requerimiento: bool | None = None
    evacuacion_observaciones: str | None = None
    otros_requerimiento: bool | None = None
    otros_observaciones: str | None = None
    observaciones_generales: str | None = None
    class Config:
        from_attributes = True


class SaludEstablecimientoCreate(BaseModel):
    id_edan: int
    nombre_establecimiento: str
    localidad_comunidad: str | None = None
    nivel_atencion: int | None = None
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    personal_medicos: int | None = None
    personal_enfermeras: int | None = None
    personal_otros: int | None = None
    observaciones: str | None = None

class SaludEstablecimientoResponse(BaseModel):
    id_salud_establecimiento: int
    id_edan: int
    nombre_establecimiento: str
    localidad_comunidad: str | None = None
    nivel_atencion: int | None = None
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    personal_medicos: int | None = None
    personal_enfermeras: int | None = None
    personal_otros: int | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class SaludNecesidadesCreate(BaseModel):
    id_edan: int
    botiquin_personas: int | None = None
    otras_necesidades: str | None = None
    observaciones: str | None = None

class SaludNecesidadesResponse(BaseModel):
    id_salud_necesidad: int
    id_edan: int
    botiquin_personas: int | None = None
    otras_necesidades: str | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class InfraestructuraVialCreate(BaseModel):
    id_edan: int
    via_acceso_puentes: str | None = None
    tramo: str | None = None
    localidad_origen: str | None = None
    localidad_destino: str | None = None
    dano_parcial_km: float | None = None
    dano_total_km: float | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None

class InfraestructuraVialResponse(BaseModel):
    id_infraestructura_vial: int
    id_edan: int
    via_acceso_puentes: str | None = None
    tramo: str | None = None
    localidad_origen: str | None = None
    localidad_destino: str | None = None
    dano_parcial_km: float | None = None
    dano_total_km: float | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class InfraestructuraPublicaCreate(BaseModel):
    id_edan: int
    localidad_comunidad: str | None = None
    tipo_estructura: str | None = None
    dano_parcial: int | None = None
    dano_total: int | None = None
    observaciones: str | None = None

class InfraestructuraPublicaResponse(BaseModel):
    id_infraestructura_publica: int
    id_edan: int
    localidad_comunidad: str | None = None
    tipo_estructura: str | None = None
    dano_parcial: int | None = None
    dano_total: int | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class ServicioBasicoEdanServicioBasico(BaseModel):
    id_servicio_basico: int
    nombre: str | None = None

class ServicioBasicoEdanCreate(BaseModel):
    id_edan: int
    id_servicio_basico: int
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None

class ServicioBasicoEdanResponse(BaseModel):
    id_servicio_basico_edan: int
    id_edan: int
    id_servicio_basico: int
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None
    servicio_basico: ServicioBasicoEdanServicioBasico | None = None
    class Config:
        from_attributes = True


class EducacionDanoCreate(BaseModel):
    id_edan: int
    nombre_establecimiento: str
    comunidad: str | None = None
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    suspension_clases: bool | None = None
    perdida_material: bool | None = None
    funciona_albergue: bool | None = None
    observaciones: str | None = None

class EducacionDanoResponse(BaseModel):
    id_educacion_dano: int
    id_edan: int
    nombre_establecimiento: str
    comunidad: str | None = None
    dano_parcial: bool | None = None
    dano_total: bool | None = None
    suspension_clases: bool | None = None
    perdida_material: bool | None = None
    funciona_albergue: bool | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class EducacionAfectacionCreate(BaseModel):
    id_edan: int
    id_educacion_dano: int | None = None
    nombre_establecimiento: str | None = None
    estudiantes_afectados: int | None = None
    profesores_afectados: int | None = None
    administrativos_afectados: int | None = None
    total_afectados: int | None = None
    observaciones: str | None = None

class EducacionAfectacionResponse(BaseModel):
    id_educacion_afectacion: int
    id_edan: int
    id_educacion_dano: int | None = None
    nombre_establecimiento: str | None = None
    estudiantes_afectados: int | None = None
    profesores_afectados: int | None = None
    administrativos_afectados: int | None = None
    total_afectados: int | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class ViviendaCreate(BaseModel):
    id_edan: int
    comunidad: str | None = None
    viviendas_dano_parcial: int | None = None
    viviendas_dano_total: int | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None

class ViviendaResponse(BaseModel):
    id_vivienda: int
    id_edan: int
    comunidad: str | None = None
    viviendas_dano_parcial: int | None = None
    viviendas_dano_total: int | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class AgriculturaCreate(BaseModel):
    id_edan: int
    tipo_cultivo: str | None = None
    hectareas_afectadas: float | None = None
    hectareas_perdidas: float | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None

class AgriculturaResponse(BaseModel):
    id_agricultura: int
    id_edan: int
    tipo_cultivo: str | None = None
    hectareas_afectadas: float | None = None
    hectareas_perdidas: float | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class PecuariaCreate(BaseModel):
    id_edan: int
    tipo_especie: str | None = None
    raza: str | None = None
    animales_afectados: int | None = None
    animales_muertos: int | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None

class PecuariaResponse(BaseModel):
    id_pecuaria: int
    id_edan: int
    tipo_especie: str | None = None
    raza: str | None = None
    animales_afectados: int | None = None
    animales_muertos: int | None = None
    necesidades_inmediatas: str | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class InfraProductivaCreate(BaseModel):
    id_edan: int
    tipo: str | None = None
    dano_parcial: int | None = None
    dano_total: int | None = None
    observaciones: str | None = None

class InfraProductivaResponse(BaseModel):
    id_infra_productiva: int
    id_edan: int
    tipo: str | None = None
    dano_parcial: int | None = None
    dano_total: int | None = None
    observaciones: str | None = None
    class Config:
        from_attributes = True


class ProteccionCategoriaProteccion(BaseModel):
    id_categoria_proteccion: int
    nombre: str | None = None

class ProteccionCreate(BaseModel):
    id_edan: int
    id_categoria_proteccion: int
    mujeres: int | None = None
    hombres: int | None = None
    total: int | None = None
    apoyo_psicosocial: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str | None = None

class ProteccionResponse(BaseModel):
    id_proteccion: int
    id_edan: int
    id_categoria_proteccion: int
    mujeres: int | None = None
    hombres: int | None = None
    total: int | None = None
    apoyo_psicosocial: bool | None = None
    reposicion_documentos: bool | None = None
    observaciones: str | None = None
    categoria_proteccion: ProteccionCategoriaProteccion | None = None
    class Config:
        from_attributes = True


class AyudaHumanitariaEdanAyudaHumanitaria(BaseModel):
    id_ayuda_humanitaria: int
    nombre: str | None = None

class AyudaHumanitariaEdanCreate(BaseModel):
    id_edan: int
    id_ayuda_humanitaria: int
    requiere: bool | None = None
    observaciones: str | None = None

class AyudaHumanitariaEdanResponse(BaseModel):
    id_ayuda_edan: int
    id_edan: int
    id_ayuda_humanitaria: int
    requiere: bool | None = None
    observaciones: str | None = None
    ayuda_humanitaria: AyudaHumanitariaEdanAyudaHumanitaria | None = None
    class Config:
        from_attributes = True


class ComunidadCreate(BaseModel):
    id_edan: int
    nombre_comunidad: str

class ComunidadResponse(BaseModel):
    id_comunidad: int
    id_edan: int
    nombre_comunidad: str
    class Config:
        from_attributes = True
