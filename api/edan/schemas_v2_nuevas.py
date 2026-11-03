"""Schemas Pydantic de las APIs nuevas EDAN (Fase 2, uuid-first).

Contrato (PLAN_APIS_V2_EDAN.md §3/§20.14): POST/PUT solo uuid; GET por uuid
o id; respuestas con uuid e id; **LWW total** — `version` no se envía ni se
valida (se acepta y descarta si llega; sin 409 por edición simultánea).
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SeccionTipo = Literal[
    "impacto_poblacion",
    "salud_establecimientos",
    "salud_necesidades",
    "danos_viales",
    "danos_infra_publica",
    "servicios_basicos",
    "unidades_educativas",
    "danos_vivienda",
    "danos_agricultura",
    "danos_pecuario",
    "infra_productiva",
    "proteccion",
    "primera_respuesta",
    "necesidades_humanitarias",
]


# ---------------------------------------------------------------------------
# Formulario (cabecera edan_localidades)
# ---------------------------------------------------------------------------
class FormularioUpsert(BaseModel):
    """Escritura de cabecera (LWW: gana el último que llega; sin 409).

    `version` NO se envía; si llega se acepta y se descarta (compatibilidad).
    - Acepta las 14 `imp_*` opcionales (sin `grup_*`: el servidor deriva
      grup := OR(miembros imp_*)). `imp=false` con filas existentes -> 400
      (borre la sección o use POST /formularios/completo)."""
    model_config = ConfigDict(extra="forbid")

    uuid_edan_localidad: UUID = Field(..., description="Identidad permanente generada por el cliente")
    version: int | None = Field(
        None, ge=1, description="DEPRECATED (LWW): aceptado y descartado; no se valida")
    localidad: str = Field("", max_length=200)
    id_municipio: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_tipo_evento: int | None = None
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    fecha_llenado: str | None = Field(None, description="ISO 8601")
    fecha_evento: str | None = Field(None, description="ISO 8601")
    hora_evento: str | None = None
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    id_usuario: int | None = Field(None, ge=1, description=(
        "Autor de la localidad. Si se omite, se usa el usuario del token. "
        "En UPDATE es INMUTABLE (no cambia el autor ya registrado)."))
    # 14 flags de sección opcionales (true/false); sin grup_*:
    # el servidor recalcula grup_* := OR(miembros imp_*) en toda escritura.
    imp_impacto_poblacion: bool | None = None
    imp_primera_respuesta: bool | None = None
    imp_salud_establecimientos: bool | None = None
    imp_necesidad_salud: bool | None = None
    imp_danos_viales: bool | None = None
    imp_danos_infra_publica: bool | None = None
    imp_servicios_basicos: bool | None = None
    imp_unidades_educativas: bool | None = None
    imp_danos_vivienda: bool | None = None
    imp_danos_agricultura: bool | None = None
    imp_danos_pecuarios: bool | None = None
    imp_infra_productiva: bool | None = None
    imp_proteccion: bool | None = None
    imp_necesidad_humanitaria: bool | None = None
    # los 9 flags de grupo (grup_*) y sus nombres legacy (imp_poblacion, …)
    # NO se envían: el servidor los deriva de las secciones (400 si llegan)


class FormularioResponse(BaseModel):
    uuid_edan_localidad: UUID
    id_edan_localidad: int
    localidad: str | None = None
    id_municipio: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_tipo_evento: int | None = None
    # id_local NO se expone (las APIs nuevas van SOLO con uuid)
    id_usuario: int | None = None
    fecha_llenado: str | None = None
    fecha_evento: str | None = None
    total_poblacion_afectada: int | None = None
    total_familias_afectadas: int | None = None
    total_familias_damnificadas: int | None = None
    fecha_modificacion: str | None = None


# ---------------------------------------------------------------------------
# Secciones (las 14 tablas; campos libres validados contra columnas reales)
# ---------------------------------------------------------------------------
class SeccionUpsert(BaseModel):
    """Campos de sección: `uuid_registro` (identidad) + los campos REALES de
    la tabla (validados en el service contra information_schema). `fotografia`
    se acepta pero se descarta (la sube POST /fotografias; 1 foto activa por
    fila). `version` no se envía (LWW); si llega se descarta."""
    model_config = ConfigDict(extra="allow")

    uuid_registro: UUID = Field(..., description="Identidad permanente de la fila (cliente)")


class ViviendaUpsert(BaseModel):
    # extra="ignore": acepta `fotografia` y la DESCARTA (va en POST /fotografias);
    # así no aparece en el esquema Swagger ni se envía a BD.
    model_config = ConfigDict(extra="ignore")

    uuid_registro: UUID = Field(..., description="Identidad de la vivienda (cliente)")
    tipo_dano: Literal["TOTAL", "PARCIAL"]
    coordenada_lat: float | None = None
    coordenada_lon: float | None = None


# ---------------------------------------------------------------------------
# Consolidar (EDAN padre) — identidad SOLO por uuid (§20.17)
# ---------------------------------------------------------------------------
class ConsolidarNuevoIn(BaseModel):
    """POST /consolidar — crea un EDAN consolidando localidades aprobadas.

    Dos formas exactamente (XOR), ambas con `extra="forbid"`:

    **Canónica (uuid, recomendada):**

    - `uuid_edan`: identidad del EDAN generada por el CLIENTE; si se omite,
      el servidor la genera (trigger `trg_uuid_edan`).
    - `localidades[]`: `uuid_edan_localidad` de cada localidad (sin
      `id_local`/`id_seccion` ni ids numéricos en la escritura).

    Reintento idempotente: si `uuid_edan` ya existe y las mismas localidades
    ya están consolidadas en él, devuelve el EDAN (200); si no coincide → 409.

    **Legada (DEPRECATED, compatibilidad con la app actual):**

    - `id_municipio` + `id_tipo_evento` + `localidad_ids[]` (ids numéricos
      `id_edan_localidad`), idéntica al body viejo `POST /edan/consolidar`.
    - `id_municipio`/`id_tipo_evento` deben coincidir con las localidades
      (400 clásico si no); `localidad_ids` vacío → 400 clásico; ids
      desconocidos → 400 clásico (mismo texto que la API vieja).
    - Si no llega `uuid_edan`, el servidor genera la identidad (sin
      idempotencia), igual que antes.
    - **Migrar** a la forma uuid: `GET /consolidar/pendientes` ya devuelve
      `localidades[]` con `uuid_edan_localidad`.

    Ejemplo canónico::

        {"uuid_edan": "0d1e2f3a-4b5c-4d6e-8f90-112233445566",
         "localidades": ["3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d80",
                         "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d81"]}

    Ejemplo legado (deprecated)::

        {"id_municipio": 70101, "id_tipo_evento": 5,
         "localidad_ids": [278, 325668]}
    """
    model_config = ConfigDict(extra="forbid")

    uuid_edan: UUID | None = Field(
        None, description="Identidad del EDAN generada por el cliente "
                          "(si no llega, el servidor la genera)")
    localidades: list[UUID] | None = Field(
        None, min_length=1,
        description="CANÓNICA: uuid_edan_localidad de las localidades a consolidar "
                    "(aprobadas, sin EDAN, mismo municipio/tipo de evento). "
                    "Exactamente una de 'localidades' o 'localidad_ids'.")
    id_municipio: int | None = Field(
        None, description="LEGADA (DEPRECATED): id_municipio; solo con 'localidad_ids'")
    id_tipo_evento: int | None = Field(
        None, description="LEGADA (DEPRECATED): id_tipo_evento; solo con 'localidad_ids'")
    localidad_ids: list[int] | None = Field(
        None, description="LEGADA (DEPRECATED): ids numéricos id_edan_localidad; "
                          "solo con id_municipio+id_tipo_evento. Migrar a 'localidades'.")

    @model_validator(mode="after")
    def _exactamente_una_forma(self):
        nuevo = self.localidades is not None
        legado = self.localidad_ids is not None
        if nuevo and legado:
            raise ValueError(
                "envíe exactamente una forma: 'localidades' (uuid, canónica) "
                "o 'localidad_ids' (legada, deprecated), no ambas")
        if not nuevo and not legado:
            raise ValueError(
                "falta 'localidades' (uuid, canónica) o 'localidad_ids' "
                "(legada, deprecated); envíe exactamente una")
        if legado and (self.id_municipio is None or self.id_tipo_evento is None):
            raise ValueError(
                "la forma legada 'localidad_ids' requiere 'id_municipio' "
                "e 'id_tipo_evento' (como el body viejo POST /edan/consolidar)")
        return self


# ---------------------------------------------------------------------------
# Formulario completo (todo-en-uno, estilo legacy /localidades/{id}/documento)
# ---------------------------------------------------------------------------# Ejemplo COMPLETO mostrado en Swagger al dar "Try it out" en
# POST /api/v2/edan/formularios/completo. Orden del documento:
#   1) identidad (uuid)  2) cabecera  3) 14 flags imp_*  4) 14 secciones.
# NO incluye `fotografia` en las filas: se acepta y descarta si llega; la foto
# se sube DESPUÉS con POST /fotografias (multipart) y el servidor espeja el
# path en la fila (ver §20.7 del PLAN).
FORMULARIO_COMPLETO_EJEMPLO: dict = {
    # --- 1) identidad (obligatoria; upsert idempotente por uuid) ---
    "uuid_edan_localidad": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d80",
    # --- 2) cabecera ---
    "localidad": "Comunidad El Carmen - Sector Norte",
    "id_municipio": 70101,       # Santa Cruz de la Sierra (070101)
    "id_departamento": 7,        # lo deriva el servidor si se omite
    "id_provincia": 701,         # lo deriva el servidor si se omite
    "id_tipo_evento": 1,         # 1 = Inundaciones ocasionales
    "id_tipo_localidad": 1,      # 1 = Localidad
    "id_edan_localidad_estado": 1,  # 1 = Borrador
    "fecha_llenado": "2026-10-11T14:30:00+00:00",
    "fecha_evento": "2026-10-10",
    "hora_evento": "08:15:00",
    "total_poblacion_afectada": 1250,
    "total_familias_afectadas": 312,
    "total_familias_damnificadas": 98,
    "id_usuario": 1207,  # OPCIONAL (autor de la localidad; si falta, token)
    "pendiente_actualizacion": False,  # dirty flag offline del cliente
    "pendiente_eliminacion": False,
    # --- 3) 14 flags de sección (OBLIGATORIAS; true = la sección trae filas) ---
    "imp_impacto_poblacion": True,
    "imp_primera_respuesta": True,
    "imp_salud_establecimientos": True,
    "imp_necesidad_salud": True,
    "imp_danos_viales": True,
    "imp_danos_infra_publica": True,
    "imp_servicios_basicos": True,
    "imp_unidades_educativas": True,
    "imp_danos_vivienda": True,
    "imp_danos_agricultura": True,
    "imp_danos_pecuarios": True,
    "imp_infra_productiva": True,
    "imp_proteccion": True,
    "imp_necesidad_humanitaria": True,
    # --- 4) 14 secciones (1:1 = objeto único, 1:N = array; SOLO si su flag es true) ---
    # 1:N — SIEMPRE se envían las 4 filas (una por cada id_grupo_etario del catálogo
    # edan.grupo_etario), aunque los conteos sean 0. Tope = 4.
    "impacto_poblacion": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d81",  # 1 = Niño (a) 0-5 años
         "id_grupo_etario": 1, "fallecidos": 0, "heridos": 2, "desaparecidos": 0,
         "observaciones": ""},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da5",  # 2 = Escolar de 6-18 años
         "id_grupo_etario": 2, "fallecidos": 1, "heridos": 8, "desaparecidos": 1,
         "observaciones": "2 escolares de la U.E. Copa Kollu"},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da6",  # 3 = Adulto de 19-60 años
         "id_grupo_etario": 3, "fallecidos": 2, "heridos": 15, "desaparecidos": 1,
         "observaciones": "Censo preliminar de juntas vecinales"},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da7",  # 4 = Adulto mayor de 60 años
         "id_grupo_etario": 4, "fallecidos": 0, "heridos": 2, "desaparecidos": 0,
         "observaciones": ""},
    ],
    # 1:1
    "necesidad_primera_respuesta": {
        "uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d82",
        "busqueda": True, "salvamento": True, "evacuacion": True,
        "observaciones": "Equipos de rescate municipal en la cuenca sur",
    },
    # 1:N
    "establecimientos_salud": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d83",
         "nombre_establecimiento": "C.S. El Carmen", "comunidad": "El Carmen",
         "nivel_atencion": "2do Nivel",  # varchar: '1er Nivel' | '2do Nivel' | '3er Nivel'
         "dano_parcial": True, "dano_total": False,
         "medicos_afectados": 1, "enfermeras_afectadas": 2, "otros_afectados": 3},
    ],
    # 1:1
    "necesidad_salud": {
        "uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d84",
        "numero_personas": 89, "otras_necesidades": "Medicamentos anticonceptivos",
        "observaciones": "Un médico por cada 300 afectados",
    },
    # 1:N
    "danos_viales": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d85",
         "tramo": "El Carmen - Puente Verde", "via": True, "puente": False,
         "dano_parcial": True, "dano_total": False, "km_danio": 3.5,
         "necesidades_inmediatas": "Maquinaria para reposicion de calzada"},
    ],
    # 1:N
    "danos_infra_publica": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d86",
         "comunidad": "El Carmen", "tipo_estructura": "Puente de concreto",  # varchar libre
         "dano_parcial": True, "dano_total": False},
    ],
    # 1:N
    "servicios_basicos": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d87",
         "tipo": "agua_potable", "dano_parcial": True, "dano_total": True,
         "necesidades_inmediatas": "Reposicion de tuberia en red principal"},
    ],
    # 1:N
    "unidades_educativas": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d88",
         "nombre_establecimiento": "U.E. Copa Kollu", "comunidad": "El Carmen",
         "dano_parcial": True, "dano_total": False, "suspension_clases": True,
         "perdida_material": True, "funciona_albergue": False,
         "estudiantes": 520, "profesores": 24, "administrativos": 4},
    ],
    # 1:1 con hijas 1:N (viviendas[]). El padre NO guarda coords (van en cada hija).
    "danos_vivienda": {
        "uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d89",
        "comunidad": "El Carmen", "dano_parcial": 42, "dano_total": 17,
        "necesidades_inmediatas": "Carpas y kits de cocina para viviendas destechadas",
        "viviendas": [
            {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da1",
             "tipo_dano": "TOTAL", "coordenada_lat": -17.3987, "coordenada_lon": -66.1601},
            {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da2",
             "tipo_dano": "PARCIAL", "coordenada_lat": -17.3992, "coordenada_lon": -66.1608},
        ],
    },
    # 1:N
    "danos_agricultura": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d90",
         "tipo_cultivo": "Maiz blanco", "hectareas_afectadas": 23,  # integer
         "hectareas_perdidas": 8, "necesidades_inmediatas": "Semilla certificada para resiembra"},
    ],
    # 1:N
    "danos_pecuarios": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d91",
         "especie": "Bovino", "animales_afectados": 145, "animales_muertos": 12,
         "necesidades_inmediatas": "Suero y forraje"},
    ],
    # 1:N
    "infra_productiva": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d92",
         "tipo": "silos_comunitarios",
         "dano_parcial": 2, "dano_total": 1},  # integer (cantidades), no boolean
    ],
    # 1:N — SIEMPRE se envían las 8 filas (una por cada id_grupo_vulnerable del
    # catálogo edan.grupo_vulnerable), aunque los conteos sean 0. Tope = 8.
    # Vinculación por id_grupo_vulnerable_catalogo (FK); NO se envía `grupo` (lectura).
    "proteccion": [
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d93",  # 1 = Niñas y niños 0-5
         "id_grupo_vulnerable_catalogo": 1, "mujeres": 14, "hombres": 12,
         "apoyo_psicologico": False, "reposicion_documentos": False, "total": 26},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da8",  # 2 = Niñas y niños 6-12
         "id_grupo_vulnerable_catalogo": 2, "mujeres": 30, "hombres": 28,
         "apoyo_psicologico": True, "reposicion_documentos": False, "total": 58},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6da9",  # 3 = Adolescentes
         "id_grupo_vulnerable_catalogo": 3, "mujeres": 18, "hombres": 15,
         "apoyo_psicologico": True, "reposicion_documentos": True, "total": 33},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6daa",  # 4 = Mujeres lactantes
         "id_grupo_vulnerable_catalogo": 4, "mujeres": 7, "hombres": 0,
         "apoyo_psicologico": False, "reposicion_documentos": False, "total": 7},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6dab",  # 5 = Mujeres embarazadas
         "id_grupo_vulnerable_catalogo": 5, "mujeres": 9, "hombres": 0,
         "apoyo_psicologico": True, "reposicion_documentos": True, "total": 9},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6dac",  # 6 = Adultos mayores
         "id_grupo_vulnerable_catalogo": 6, "mujeres": 11, "hombres": 8,
         "apoyo_psicologico": False, "reposicion_documentos": True, "total": 19},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6dad",  # 7 = Personas con discapacidad
         "id_grupo_vulnerable_catalogo": 7, "mujeres": 4, "hombres": 3,
         "apoyo_psicologico": False, "reposicion_documentos": False, "total": 7},
        {"uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6dae",  # 8 = Enfermedad inhabilitante
         "id_grupo_vulnerable_catalogo": 8, "mujeres": 2, "hombres": 1,
         "apoyo_psicologico": False, "reposicion_documentos": False, "total": 3},
    ],
    # 1:1 — los 9 campos son boolean ("¿se requiere esa ayuda?"); el obs_* de cada
    # ayuda se envía SOLO cuando esa ayuda es true.
    "necesidad_humanitaria": {
        "uuid_registro": "3f9e6b18-2b2f-4a5e-9c1d-0e5a2b4c6d94",
        "alimentos": True, "obs_alimentos": "Cajas de alimentos para 96 familias por 15 dias",
        "refugio_vivienda": True, "obs_refugio_vivienda": "98 carpas y kits de cocina",
        "ropa_cama": True, "obs_ropa_cama": "210 cobijas y juegos de sábanas",
        "articulos_higiene": True, "obs_articulos_higiene": "120 kits de higiene familiar",
        "articulos_cocina": True, "obs_articulos_cocina": "40 kits de utensilios",
        "prendas_vestir": True, "obs_prendas_vestir": "200 prendas de vestir para niño/as",
        "herramientas": False,   # false -> NO se envía obs_herramientas
        "almacenamiento_agua": True, "obs_almacenamiento_agua": "60 bidones de 200L",
        "banos": False,          # false -> NO se envía obs_banos
    },
}


class FormularioCompletoUpsert(BaseModel):
    """POST /formularios/completo y PUT /formularios/completo — documento
    plano (cabecera + 14 imp_* + 14 secciones).

    - Identidad SOLO por uuid (uuid_edan_localidad + uuid_registro por fila).
    - `id_usuario` es OPCIONAL: si no llega, se usa el usuario del token; si
      llega, se respeta (autor de la localidad). En UPDATE es INMUTABLE.
    - Las 14 flags de sección (imp_*) son OBLIGATORIAS y explícitas (true/false).
      Los grupos (grup_*) NO se envían: el servidor los deriva.
    - Nombres de sección: legacy o canónicos; 4 son 1:1 (objeto único):
      necesidad_primera_respuesta, necesidad_salud, necesidad_humanitaria y
      danos_vivienda (ésta puede arrastrar `viviendas[]` anidadas). Resto 1:N.
    - NO se envía `fotografia` en las filas: se acepta y descarta si llega;
      la foto se sube DESPUÉS con POST /fotografias (multipart) y el
      servidor espeja el path en la fila.
    - Se ESCRIBE cada sección SOLO si su flag `imp_*=true`:
      - `imp_*=false` y la sección trae filas -> 400 (simétrico a la regla
        flag↔fila: `true` sin filas ya era 400 atómico).
      - `impacto_poblacion` con `true`: enviar las 4 filas completas
        (id_grupo_etario 1,2,3,4 del catálogo), aunque los conteos sean 0;
        si llegan ≠4 o con ids fuera de {1..4} -> 400 (tope 4 enforced).
      - `proteccion` con `true`: enviar las 8 filas completas
        (id_grupo_vulnerable_catalogo 1-8), aunque los conteos sean 0;
        si llegan ≠8 o con catálogo fuera de {1..8} -> 400 (tope 8 enforced).
    - §20.15 (flujo de la app): también se ACEPTA el formato del
      GET /formularios/{uuid}/completo (`cabecera: {...}` + `fotos: [...]`):
      se aplana automáticamente (round-trip GET -> editar -> PUT).
    - Pulsa "Try it out" y edita el JSON de ejemplo completo.
    """
    model_config = ConfigDict(extra="allow",   # extras (p.ej. flags de grupo) se
                                                # rechazan con 400 explícito en el service
                               json_schema_extra={"example": FORMULARIO_COMPLETO_EJEMPLO})

    @model_validator(mode="before")
    @classmethod
    def _aplana_formato_get(cls, data: Any) -> Any:
        # Round-trip del flujo de la app: el documento del GET (cabecera
        # anidada con objetos FK/grup_*/id interno + fotos) se aplana aquí,
        # ANTES de validar, a la forma plana de escritura (§20.15).
        if isinstance(data, dict) and isinstance(data.get("cabecera"), dict):
            from .service_v2_nuevas import _aplanar_completo
            return _aplanar_completo(data)
        return data


    uuid_edan_localidad: UUID = Field(..., description="Identidad permanente (cliente)")
    localidad: str = Field("", max_length=200)
    id_municipio: int | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_tipo_evento: int | None = None
    id_tipo_localidad: int | None = None
    id_edan_localidad_estado: int | None = None
    fecha_llenado: str | None = Field(None, description="ISO 8601")
    fecha_evento: str | None = Field(None, description="ISO 8601")
    hora_evento: str | None = None
    total_poblacion_afectada: int = 0
    total_familias_afectadas: int = 0
    total_familias_damnificadas: int = 0
    id_usuario: int | None = Field(None, ge=1, description=(
        "Autor de la localidad. OPCIONAL: si se omite, se usa el usuario del token. "
        "En UPDATE es INMUTABLE (no cambia el autor ya registrado)."))
    pendiente_actualizacion: bool = Field(False, description="Dirty flag offline del cliente")
    pendiente_eliminacion: bool = Field(False, description="Borrado pendiente offline del cliente")
    fecha_modificacion: str | None = Field(
        None, description="ISO 8601; se acepta pero el servidor SIEMPRE fija now() (no se escribe)")

    # 14 flags de sección (todas obligatorias; true/false)
    imp_impacto_poblacion: bool | None = None
    imp_primera_respuesta: bool | None = None
    imp_salud_establecimientos: bool | None = None
    imp_necesidad_salud: bool | None = None
    imp_danos_viales: bool | None = None
    imp_danos_infra_publica: bool | None = None
    imp_servicios_basicos: bool | None = None
    imp_unidades_educativas: bool | None = None
    imp_danos_vivienda: bool | None = None
    imp_danos_agricultura: bool | None = None
    imp_danos_pecuarios: bool | None = None
    imp_infra_productiva: bool | None = None
    imp_proteccion: bool | None = None
    imp_necesidad_humanitaria: bool | None = None

    # 14 secciones (nombres legacy); 1:N = list|dict, 1:1 = dict
    impacto_poblacion: list[dict[str, Any]] | dict[str, Any] | None = None
    establecimientos_salud: list[dict[str, Any]] | dict[str, Any] | None = None
    danos_viales: list[dict[str, Any]] | dict[str, Any] | None = None
    danos_infra_publica: list[dict[str, Any]] | dict[str, Any] | None = None
    servicios_basicos: list[dict[str, Any]] | dict[str, Any] | None = None
    unidades_educativas: list[dict[str, Any]] | dict[str, Any] | None = None
    danos_vivienda: list[dict[str, Any]] | dict[str, Any] | None = None
    danos_agricultura: list[dict[str, Any]] | dict[str, Any] | None = None
    danos_pecuarios: list[dict[str, Any]] | dict[str, Any] | None = None
    infra_productiva: list[dict[str, Any]] | dict[str, Any] | None = None
    proteccion: list[dict[str, Any]] | dict[str, Any] | None = None
    necesidad_primera_respuesta: dict[str, Any] | list[dict[str, Any]] | None = None
    necesidad_salud: dict[str, Any] | list[dict[str, Any]] | None = None
    necesidad_humanitaria: dict[str, Any] | list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Fotos
# ---------------------------------------------------------------------------
class FotoResponse(BaseModel):
    uuid_fotografia: UUID
    id_fotografia: int
    id_edan_localidad: int | None = None
    tipo_entidad: str | None = None
    uuid_registro: UUID | None = None
    ruta_archivo: str | None = None
    sha256: str | None = None
    mime_type: str | None = None
    tamano_bytes: int | None = None
    borrado_logico: bool | None = None
    fecha_modificacion: str | None = None


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------
class SyncPushItem(BaseModel):
    accion: Literal["upsert", "borrar"] = "upsert"
    tipo: Literal["formulario", "seccion", "vivienda"]
    tipo_seccion: SeccionTipo | None = Field(None, description="Obligatorio cuando tipo='seccion'")
    datos: dict[str, Any] | None = Field(None, description="Payload del upsert (mismos campos que los endpoints directos)")


class SyncPushRequest(BaseModel):
    items: list[SyncPushItem] = Field(..., max_length=200, description="Lote; cada ítem se aplica y confirma por separado")


class SyncAckRequest(BaseModel):
    id_dispositivo: UUID = Field(..., description="uuid estable de la instalación del cliente")
    watermark: datetime | None = Field(None, description="Marca (fecha_modificacion del servidor) ya aplicada localmente")


class SyncPullResponse(BaseModel):
    watermark: str = Field(..., description="Guardar como 'desde' en el siguiente pull (y ackear)")
    formularios: list[dict[str, Any]] = []
    secciones: list[dict[str, Any]] = []
    viviendas: list[dict[str, Any]] = []
    fotos: list[dict[str, Any]] = []
    tombstones: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
