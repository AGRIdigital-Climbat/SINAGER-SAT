-- Generado por SINB/generar_modelo04.py desde propuesta/04-BASE-DE-DATOS.md
-- Modelo nuevo del SINB en el esquema sinb. Solo creacion (sin DROP ni DELETE).
-- Previamente:
--   SET search_path TO sinb, public;
--   CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA sinb;
--   CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA sinb;
--
-- Desviaciones aplicadas sobre el DDL del documento (errores del doc):
--   1. categoria_comportamiento: PK declarada dos veces (columna + tabla) -> se deja la de columna.
--   2. escenario_estacional: PK de columna 'id' + PK compuesta -> 'id' pasa a NOT NULL y la compuesta queda UNIQUE.
--   3. sinonimo_indicador: UNIQUE con lower(texto) no es valido -> CREATE UNIQUE INDEX.
--   4. auditoria: PK no incluia la columna de particion -> PRIMARY KEY (id, occurred_at) + particion DEFAULT.
--   5. caracteristica_comportamiento e indicador_natural_caracteristica: el doc no trae DDL -> se autoro (catalogo 1A + FK de observacion_registro).
--   6. gist_observacion_comunidad: observacion no tiene columna geom (el doc lo resuelve con vista materializada) -> omitido.
--   7. v_registro_territorial: gi.fk_id_indicador/fk_id_grupo -> id_indicador/id_grupo; g.nombre -> g.grupo.
--   8. Trgm: 4 indices requieren pg_trgm; se crean los 3 extraibles, el del doc 'CREATE TRGM.idx_comportamiento_texto' esta malformado y se omite.
--   9. RLS/policies (doc linea ~2027) y scripts SET LOCAL: fuera de alcance, fase seguridad/API.
--
-- Re-ejecutable: no usa DROP/DELETE; tipos, tablas e indices son idempotentes.

DO $$ BEGIN
CREATE TYPE estado_registro AS ENUM ('ACTIVO', 'INACTIVO', 'ELIMINADO');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE presencia_observada AS ENUM ('PRESENTE', 'AUSENTE', 'NO_OBSERVADO');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE origen_registro     AS ENUM ('CAMPO', 'OFICINA', 'IMPORTACION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE ambito_recomendacion AS ENUM ('COMUNIDAD', 'MUNICIPIO', 'DEPARTAMENTO', 'NACIONAL');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE estado_verificacion AS ENUM ('PENDIENTE', 'VERIFICADA', 'NO_VERIFICABLE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE alcance_consentimiento AS ENUM
    ('INTERNO','INVESTIGACION','DOCUMENTACION','PUBLICA','COMERCIAL');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE tipo_ventana AS ENUM
    ('SAN_JUAN','INICIO_ANIO','LLUVIAS_INICIO','COSECHA','FLORACION','HELADA','OTRA');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
CREATE TYPE nivel_calificacion AS ENUM
    ('EN_VERIFICACION', 'USABLE', 'REVISAR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============ TABLAS (+ sus ADD COLUMN / ADD CONSTRAINT) ============

CREATE TABLE IF NOT EXISTS grupo (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo         varchar(80)  NOT NULL,
    slug          varchar(80)  NOT NULL,
    descripcion   text,
    orden         smallint     NOT NULL DEFAULT 0 CHECK (orden >= 0),
    estado        estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy     bigint,
    creado_en     timestamptz  NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_grupo_nombre UNIQUE (grupo),
    CONSTRAINT uq_grupo_slug   UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS indicador_natural (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre             varchar(150) NOT NULL,
    nombre_cientifico  varchar(150),
    taxon_reino        varchar(40),
    taxon_filo         varchar(40),
    taxon_clase        varchar(40),
    taxon_orden        varchar(40),
    taxon_familia      varchar(60),
    rank               varchar(30) CHECK (rank IN
                         ('especie','genero','familia','orden','clase','grupo')),
    fotografia_url     text,
    estado             estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy          bigint,
    version_catalogo   integer NOT NULL DEFAULT 1 CHECK (version_catalogo >= 1),
    creado_en          timestamptz NOT NULL DEFAULT now(),
    actualizado_en     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grupo_indicador_natural (
    id_grupo      uuid NOT NULL REFERENCES grupo(id)             ON DELETE CASCADE,
    id_indicador  uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    estado        estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy     bigint,
    PRIMARY KEY (id_grupo, id_indicador)
);

CREATE TABLE IF NOT EXISTS caracteristica (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_indicador_natural uuid NOT NULL REFERENCES indicador_natural(id)
                                          ON DELETE RESTRICT,
    caracteristica        varchar(300) NOT NULL,
    unidad_medida         varchar(30),
    metodo_observacion    text,
    estado                estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy             bigint,
    version_catalogo      integer NOT NULL DEFAULT 1 CHECK (version_catalogo >= 1),
    creado_en             timestamptz NOT NULL DEFAULT now(),
    actualizado_en        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_caracteristica_indicador_texto
        UNIQUE (fk_id_indicador_natural, caracteristica)
);

DO $$ BEGIN
ALTER TABLE caracteristica
    ADD CONSTRAINT uq_caracteristica_cadena
    UNIQUE (id, fk_id_indicador_natural);
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE NOT IN ('42710','42P07') THEN RAISE; END IF;
END $$;

CREATE TABLE IF NOT EXISTS comportamiento (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    comportamiento varchar(500) NOT NULL,
    grupo_id       uuid REFERENCES grupo(id) ON DELETE SET NULL,
    estado         estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy      bigint,
    version_catalogo integer NOT NULL DEFAULT 1 CHECK (version_catalogo >= 1),
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS significado (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    significado varchar(100) NOT NULL,
    grupo_id   uuid REFERENCES grupo(id) ON DELETE SET NULL,
    severidad  smallint CHECK (severidad BETWEEN 1 AND 5),
    estado     estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy  bigint,
    version_catalogo integer NOT NULL DEFAULT 1 CHECK (version_catalogo >= 1),
    creado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS comportamiento_significado (
    fk_id_comportamiento uuid NOT NULL REFERENCES comportamiento(id) ON DELETE CASCADE,
    fk_id_significado   uuid NOT NULL REFERENCES significado(id)   ON DELETE CASCADE,
    es_principal        boolean NOT NULL DEFAULT false,
    id_legacy           bigint,
    PRIMARY KEY (fk_id_comportamiento, fk_id_significado)
);

DO $$ BEGIN
ALTER TABLE comportamiento_significado
    ADD CONSTRAINT uq_comportamiento_significado_cadena
    UNIQUE (fk_id_significado, fk_id_comportamiento);
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE NOT IN ('42710','42P07') THEN RAISE; END IF;
END $$;

CREATE TABLE IF NOT EXISTS caracteristica_comportamiento (
    fk_id_comportamiento uuid NOT NULL REFERENCES comportamiento(id) ON DELETE CASCADE,
    fk_id_caracteristica  uuid NOT NULL REFERENCES caracteristica(id)  ON DELETE CASCADE,
    id_legacy             bigint,
    PRIMARY KEY (fk_id_comportamiento, fk_id_caracteristica)
);

DO $$ BEGIN
ALTER TABLE caracteristica_comportamiento
    ADD CONSTRAINT uq_caracteristica_comportamiento_cadena
    UNIQUE (fk_id_comportamiento, fk_id_caracteristica);
EXCEPTION WHEN OTHERS THEN
  IF SQLSTATE NOT IN ('42710','42P07') THEN RAISE; END IF;
END $$;

CREATE TABLE IF NOT EXISTS zona_geografica (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      varchar(50) NOT NULL,
    slug        varchar(50) NOT NULL UNIQUE,
    descripcion text NOT NULL,
    rango_alt_min_m smallint,
    rango_alt_max_m smallint,
    estado      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy   bigint,
    creado_en   timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_zona_nombre UNIQUE (nombre),
    CONSTRAINT chk_zona_altura CHECK (
        rango_alt_min_m IS NULL OR rango_alt_max_m IS NULL
        OR rango_alt_min_m < rango_alt_max_m
    )
);

CREATE TABLE IF NOT EXISTS comunidad (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_ine  varchar(20),
    nombre      varchar(150) NOT NULL,
    geom        geometry(Point, 4326),
    elevacion_m smallint CHECK (elevacion_m BETWEEN -500 AND 9000),
    estado      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy   bigint,
    creado_en   timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE comunidad
    ADD COLUMN IF NOT EXISTS latitud double precision
        GENERATED ALWAYS AS (ST_Y(geom)) STORED,
    ADD COLUMN IF NOT EXISTS longitud double precision
        GENERATED ALWAYS AS (ST_X(geom)) STORED;

ALTER TABLE comunidad
    ADD COLUMN IF NOT EXISTS fk_id_zona_geografica uuid REFERENCES zona_geografica(id)
        ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS municipio (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_ine varchar(20),
    nombre     varchar(80) NOT NULL,
    estado     estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy  bigint,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_municipio_nombre UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS login (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario               varchar(30) NOT NULL UNIQUE,
    password_hash         text,             -- argon2id; NULL = solo SSO institucional
    algoritmo             varchar(20) CHECK (algoritmo IN ('argon2id','bcrypt','sha256_legacy')),
    requiere_cambio       boolean NOT NULL DEFAULT false,
    ultimo_acceso_en      timestamptz,
    intentos_fallidos      smallint NOT NULL DEFAULT 0,
    bloqueado_hasta        timestamptz,
    mfa_habilitado        boolean NOT NULL DEFAULT false,
    estado                estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy             bigint,
    creado_en             timestamptz NOT NULL DEFAULT now(),
    actualizado_en        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rol (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        varchar(50) NOT NULL UNIQUE,
    nombre      varchar(50) NOT NULL,
    descripcion varchar(200),
    solo_municipal boolean NOT NULL DEFAULT true,
    estado      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy   bigint,
    creado_en   timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_solo_municipal CHECK (solo_municipal OR slug = 'administrador')
);

CREATE TABLE IF NOT EXISTS usuario (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ci                  varchar(20)  NOT NULL UNIQUE,
    nombre              varchar(30)  NOT NULL,
    paterno             varchar(30),
    materno             varchar(30),
    fecha_nacimiento    date         NOT NULL,
    celular             varchar(20),
    correo              citext,
    fotografia_url      text,
    fk_id_login         uuid UNIQUE REFERENCES login(id) ON DELETE SET NULL,
    fk_id_rol           uuid NOT NULL REFERENCES rol(id) ON DELETE RESTRICT,
    requiere_consentimiento boolean NOT NULL DEFAULT true,
    acepta_consentimiento   boolean NOT NULL DEFAULT false,
    estado              estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy           bigint,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS observacion (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_corto                text NOT NULL UNIQUE,
    fk_id_comunidad             uuid NOT NULL REFERENCES comunidad(id) ON DELETE RESTRICT,
    fk_id_municipio            uuid NOT NULL REFERENCES municipio(id)  ON DELETE RESTRICT,
    fk_id_usuario_responsable  uuid NOT NULL REFERENCES usuario(id)    ON DELETE RESTRICT,
    fecha_inicio                date NOT NULL,
    fecha_fin                   date NOT NULL,
    hora_inicio                 time,
    hora_fin                    time,
    fecha_registro              date NOT NULL,
    clima_observado             text,
    es_validada                 boolean NOT NULL DEFAULT false,
    validada_por                uuid REFERENCES usuario(id) ON DELETE SET NULL,
    validada_en                 timestamptz,
    observacion_rechazada_motivo text,
    estado                      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy                   bigint,
    creado_en                   timestamptz NOT NULL DEFAULT now(),
    actualizado_en              timestamptz NOT NULL DEFAULT now(),
    version_registro            integer NOT NULL DEFAULT 1 CHECK (version_registro >= 1),
    CONSTRAINT chk_fechas     CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT chk_horas      CHECK (hora_fin IS NULL OR hora_inicio IS NULL OR hora_fin >= hora_inicio),
    CONSTRAINT chk_validacion CHECK (
        (es_validada AND validada_por IS NOT NULL AND validada_en IS NOT NULL)
        OR (NOT es_validada)
    )
);

CREATE TABLE IF NOT EXISTS observacion_registro (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_observacion         uuid NOT NULL REFERENCES observacion(id) ON DELETE CASCADE,
    fk_id_indicador_natural   uuid NOT NULL,
    fk_id_caracteristica      uuid,
    fk_id_comportamiento      uuid,
    fk_id_significado         uuid,
    orden                     smallint NOT NULL DEFAULT 0 CHECK (orden >= 0),
    observado_en              timestamptz,
    presencia                 presencia_observada NOT NULL DEFAULT 'PRESENTE',
    valor_texto               text,
    valor_numerico            numeric(12,4),
    unidad                    varchar(30),
    confianza                 smallint CHECK (confianza BETWEEN 1 AND 5),
    notas                     text,
    es_calidad_dudosa         boolean NOT NULL DEFAULT false,
    origen                    origen_registro NOT NULL DEFAULT 'CAMPO',
    creado_por                uuid NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    creado_en                 timestamptz NOT NULL DEFAULT now(),
    actualizado_en            timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fk_registro_caracteristica
        FOREIGN KEY (fk_id_caracteristica, fk_id_indicador_natural)
        REFERENCES caracteristica (id, fk_id_indicador_natural)
        ON DELETE RESTRICT,
    CONSTRAINT fk_registro_comportamiento
        FOREIGN KEY (fk_id_comportamiento, fk_id_caracteristica)
        REFERENCES caracteristica_comportamiento (fk_id_comportamiento, fk_id_caracteristica)
        ON DELETE RESTRICT,
    CONSTRAINT fk_registro_significado
        FOREIGN KEY (fk_id_significado, fk_id_comportamiento)
        REFERENCES comportamiento_significado (fk_id_significado, fk_id_comportamiento)
        ON DELETE RESTRICT,
    CONSTRAINT chk_presencia_valor CHECK (
        (presencia = 'PRESENTE')
        OR (valor_texto IS NULL AND valor_numerico IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS consentimiento_uso (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_comunidad    uuid NOT NULL REFERENCES comunidad(id) ON DELETE CASCADE,
    fk_id_indicador    uuid REFERENCES indicador_natural(id) ON DELETE CASCADE,
    alcance            alcance_consentimiento NOT NULL,
    finalidade         text NOT NULL,
   Otorgante           text NOT NULL,        -- QUIEN OTORGA: nombre o autoridad local
    cargo_otorgante     text,
    fecha_otorgamiento date NOT NULL DEFAULT current_date,
    vigencia_hasta     date,
    documento_respaldo uuid,                -- MinIO: acta de asamblea
    revocable          boolean NOT NULL DEFAULT true,
    estado             estado_registro NOT NULL DEFAULT 'ACTIVO',
    creado_en          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidencia (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo                   varchar(12) NOT NULL
        CHECK (tipo IN ('FOTO','AUDIO','VIDEO')),
    fk_id_indicador_natural    uuid REFERENCES indicador_natural(id) ON DELETE CASCADE,
    fk_id_observacion_registro uuid
        REFERENCES observacion_registro(id) ON DELETE CASCADE,
    descripcion            text,
    orden                  smallint NOT NULL DEFAULT 0,   -- orden en la galería
    clave_almacenamiento   text NOT NULL UNIQUE,          -- clave en MinIO
    sha256                 char(64),
    bytes                  integer,
    fecha_foto             timestamptz,                   -- EXIF si existe
    geom                   geometry(Point, 4326),         -- dónde se sacó
    estado                 varchar(12) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE','CONFIRMADA','CORRUPTA','RETIRADA')),
    subida_por             uuid REFERENCES usuario(id) ON DELETE SET NULL,
    fk_id_consentimiento   uuid REFERENCES consentimiento_uso(id) ON DELETE SET NULL,
    creado_en              timestamptz NOT NULL DEFAULT now(),
    actualizado_en         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_evidencia_sujeto CHECK (
        fk_id_indicador_natural IS NOT NULL
        OR fk_id_observacion_registro IS NOT NULL
    ),
    CONSTRAINT chk_evidencia_descripcion CHECK (
        fk_id_indicador_natural IS NULL
        OR (descripcion IS NOT NULL AND btrim(descripcion) <> '')
    )
);

CREATE TABLE IF NOT EXISTS departamento (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre    varchar(80) NOT NULL UNIQUE,
    slug      varchar(80) NOT NULL UNIQUE,
    estado    estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy bigint,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS provincia (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_ine varchar(20),
    nombre     varchar(80)  NOT NULL,
    estado     estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy  bigint,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_provincia_nombre UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS departamento_provincia (
    fk_id_departamento uuid NOT NULL REFERENCES departamento(id) ON DELETE CASCADE,
    fk_id_provincia    uuid NOT NULL REFERENCES provincia(id)    ON DELETE CASCADE,
    id_legacy bigint,
    PRIMARY KEY (fk_id_departamento, fk_id_provincia)
);

CREATE TABLE IF NOT EXISTS provincia_municipio (
    fk_id_provincia uuid NOT NULL REFERENCES provincia(id) ON DELETE CASCADE,
    fk_id_municipio uuid NOT NULL REFERENCES municipio(id) ON DELETE CASCADE,
    id_legacy bigint,
    PRIMARY KEY (fk_id_provincia, fk_id_municipio)
);

CREATE TABLE IF NOT EXISTS municipio_comunidad (
    fk_id_municipio uuid NOT NULL REFERENCES municipio(id) ON DELETE CASCADE,
    fk_id_comunidad uuid NOT NULL REFERENCES comunidad(id) ON DELETE CASCADE,
    es_principal    boolean NOT NULL DEFAULT true,
    id_legacy bigint,
    PRIMARY KEY (fk_id_municipio, fk_id_comunidad)
);

CREATE TABLE IF NOT EXISTS municipio_indicador_natural (
    fk_id_municipio   uuid NOT NULL REFERENCES municipio(id)         ON DELETE CASCADE,
    fk_id_indicador  uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    vigente_desde    date,
    vigente_hasta    date,
    confirmado_por   uuid REFERENCES usuario(id) ON DELETE SET NULL,
    estado           estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy        bigint,
    PRIMARY KEY (fk_id_municipio, fk_id_indicador),
    CONSTRAINT chk_vigencia CHECK (
        vigente_hasta IS NULL OR vigente_desde IS NULL OR vigente_desde <= vigente_hasta
    )
);

CREATE TABLE IF NOT EXISTS observacion_grupo (
    fk_id_observacion uuid NOT NULL REFERENCES observacion(id) ON DELETE CASCADE,
    fk_id_grupo       uuid NOT NULL REFERENCES grupo(id)       ON DELETE RESTRICT,
    id_legacy bigint,
    PRIMARY KEY (fk_id_observacion, fk_id_grupo)
);

CREATE TABLE IF NOT EXISTS observacion_usuario (
    fk_id_observacion uuid NOT NULL REFERENCES observacion(id) ON DELETE CASCADE,
    fk_id_usuario     uuid NOT NULL REFERENCES usuario(id)     ON DELETE RESTRICT,
    rol_en_sesion     varchar(30) CHECK (rol_en_sesion IN
                          ('RESPONSABLE','ANOTADOR','REVISOR')),
    id_legacy bigint,
    PRIMARY KEY (fk_id_observacion, fk_id_usuario, rol_en_sesion)
);

CREATE TABLE IF NOT EXISTS dimension_recomendacion (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      varchar(50) NOT NULL UNIQUE,
    slug        varchar(50) NOT NULL UNIQUE,
    descripcion text,
    estado      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy   bigint,
    creado_en   timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categoria_comportamiento (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre             varchar(50) NOT NULL,
    fk_id_dimension    uuid NOT NULL REFERENCES dimension_recomendacion(id)
                                                ON DELETE CASCADE,
    orden              smallint NOT NULL DEFAULT 0,
    estado             estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy          bigint,
    CONSTRAINT uq_categoria_dimension UNIQUE (fk_id_dimension, nombre)
);

CREATE TABLE IF NOT EXISTS recomendacion_local (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    texto              varchar(200) NOT NULL,
    fk_id_dimension    uuid REFERENCES dimension_recomendacion(id) ON DELETE SET NULL,
    fk_id_categoria    uuid REFERENCES categoria_comportamiento(id) ON DELETE SET NULL,
    fk_id_comunidad    uuid REFERENCES comunidad(id) ON DELETE SET NULL,
    fk_id_municipio    uuid REFERENCES municipio(id) ON DELETE SET NULL,
    ambito             ambito_recomendacion NOT NULL DEFAULT 'MUNICIPIO',
    autorizado_por     uuid REFERENCES usuario(id) ON DELETE SET NULL,
    estado             estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy          bigint,
    creado_en          timestamptz NOT NULL DEFAULT now(),
    actualizado_en     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS observacion_recomendacion (
    fk_id_observacion       uuid REFERENCES observacion(id)         ON DELETE CASCADE,
    fk_id_recomendacion_local uuid NOT NULL REFERENCES recomendacion_local(id)
                                                           ON DELETE RESTRICT,
    id_legacy bigint,
    PRIMARY KEY (fk_id_observacion, fk_id_recomendacion_local)
);

CREATE TABLE IF NOT EXISTS campo_pronostico (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     varchar(50) NOT NULL UNIQUE,
    slug       varchar(50) NOT NULL UNIQUE,
    es_ordinal boolean NOT NULL DEFAULT true,
    estado     estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy  bigint,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pronostico_estacional (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo            text NOT NULL UNIQUE,
    fk_id_campo       uuid NOT NULL REFERENCES campo_pronostico(id) ON DELETE RESTRICT,
    nombre            varchar(120) NOT NULL,
    pronostico_libre  text,
    tipo_registro     varchar(12) NOT NULL DEFAULT 'COLECTIVO'
        CHECK (tipo_registro IN ('INDIVIDUAL','COLECTIVO')),
    confianza_largo   varchar(6) CHECK (confianza_largo IN ('ALTA','MEDIA','BAJA')),
    confianza_puntaje numeric(4,3) CHECK (confianza_puntaje BETWEEN 0 AND 1),
    zona_objetivo     varchar(80),
    periodo_inicio    date,
    periodo_fin       date,
    emitted_por       uuid REFERENCES usuario(id) ON DELETE SET NULL,
    fecha_emision     date NOT NULL DEFAULT current_date,
    estado            estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy         bigint,
    creado_en         timestamptz NOT NULL DEFAULT now(),
    actualizado_en    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_periodo CHECK (
        periodo_fin IS NULL OR periodo_inicio IS NULL OR periodo_fin >= periodo_inicio
    ),
    CONSTRAINT chk_colectivo CHECK (
        tipo_registro = 'INDIVIDUAL' OR confianza_largo IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS escenario (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre    varchar(50) NOT NULL,
    fk_id_campo_pronostico uuid NOT NULL REFERENCES campo_pronostico(id) ON DELETE CASCADE,
    orden     smallint NOT NULL DEFAULT 0,
    estado    estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy bigint,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_escenario_campo_orden UNIQUE (fk_id_campo_pronostico, orden)
);

CREATE TABLE IF NOT EXISTS escenario_estacional (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    fk_id_pronostico_estacional uuid NOT NULL
        REFERENCES pronostico_estacional(id) ON DELETE CASCADE,
    fk_id_escenario           uuid NOT NULL REFERENCES escenario(id) ON DELETE RESTRICT,
    probabilidad              numeric(5,4) CHECK (probabilidad BETWEEN 0 AND 1),
    es_seleccionado           boolean NOT NULL DEFAULT false,
    estado                    estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy                 bigint,
    CONSTRAINT uq_id_fk_id_pronostico_estacional UNIQUE (fk_id_pronostico_estacional, fk_id_escenario)
);

CREATE TABLE IF NOT EXISTS observacion_pronostico (
    fk_id_observacion          uuid NOT NULL REFERENCES observacion(id)         ON DELETE CASCADE,
    fk_id_pronostico_estacional uuid NOT NULL REFERENCES pronostico_estacional(id)
                                                                           ON DELETE RESTRICT,
    id_legacy bigint,
    PRIMARY KEY (fk_id_observacion, fk_id_pronostico_estacional)
);

CREATE TABLE IF NOT EXISTS pronostico_observador (
    fk_id_pronostico_estacional uuid NOT NULL
        REFERENCES pronostico_estacional(id) ON DELETE CASCADE,
    fk_id_observador            uuid NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    confianza_inicial           varchar(6) NOT NULL
        CHECK (confianza_inicial IN ('ALTA','MEDIA','BAJA')),
    peso                        numeric(3,2) NOT NULL DEFAULT 1.00
        CHECK (peso IN (1.00, 0.70, 0.50)),
    PRIMARY KEY (fk_id_pronostico_estacional, fk_id_observador)
);

CREATE TABLE IF NOT EXISTS observador_indice (
    fk_id_observador uuid NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    tipo             varchar(6) NOT NULL CHECK (tipo IN ('LARGO','CORTO')),
    n_emitidos       integer NOT NULL DEFAULT 0,
    n_cumplidos      integer NOT NULL DEFAULT 0,
    acertividad      numeric(5,4),          -- n_cumplidos / n_emitidos
    indice           numeric(5,2) NOT NULL DEFAULT 0.00
        CHECK (indice BETWEEN 0 AND 100),
    actualizado_en   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (fk_id_observador, tipo)
);

CREATE TABLE IF NOT EXISTS aviso (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo              text NOT NULL UNIQUE,
    fk_id_comunidad     uuid NOT NULL REFERENCES comunidad(id)  ON DELETE RESTRICT,
    fk_id_municipio     uuid NOT NULL REFERENCES municipio(id)  ON DELETE RESTRICT,
    fk_id_campo         uuid NOT NULL REFERENCES campo_pronostico(id) ON DELETE RESTRICT,
    texto_libre         text NOT NULL,        -- «va a granizar», tal como se dice
    geom                geometry(Point, 4326) NOT NULL,  -- punto del que avisa
    tipo_registro       varchar(12) NOT NULL DEFAULT 'INDIVIDUAL'
        CHECK (tipo_registro IN ('INDIVIDUAL','COLECTIVO')),
    confianza_corto     varchar(6) CHECK (confianza_corto IN ('ALTA','MEDIA','BAJA')),
    confianza_puntaje   numeric(4,3) CHECK (confianza_puntaje BETWEEN 0 AND 1),
    emitido_por         uuid REFERENCES usuario(id) ON DELETE SET NULL,
    vigencia_inicio     timestamptz NOT NULL,
    vigencia_fin        timestamptz NOT NULL,
    estado              varchar(12) NOT NULL DEFAULT 'ACTIVO'
        CHECK (estado IN ('ACTIVO','VENCIDO','VERIFICADO','RECHAZADO')),
    resultado_verificacion varchar(12)
        CHECK (resultado_verificacion IN ('CUMPLIO','NO_CUMPLIO','SIN_DATOS')),
    verificado_en       timestamptz,
    verificado_por      uuid REFERENCES usuario(id) ON DELETE SET NULL,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_vigencia CHECK (vigencia_fin > vigencia_inicio)
);

CREATE TABLE IF NOT EXISTS aviso_observador (
    fk_id_aviso       uuid NOT NULL REFERENCES aviso(id) ON DELETE CASCADE,
    fk_id_observador  uuid NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
    confianza_inicial varchar(6) NOT NULL
        CHECK (confianza_inicial IN ('ALTA','MEDIA','BAJA')),
    peso              numeric(3,2) NOT NULL DEFAULT 1.00
        CHECK (peso IN (1.00, 0.70, 0.50)),
    PRIMARY KEY (fk_id_aviso, fk_id_observador)
);

CREATE TABLE IF NOT EXISTS pronostico_digital (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fuente             varchar(40) NOT NULL,
    fk_id_comunidad    uuid NOT NULL REFERENCES comunidad(id) ON DELETE CASCADE,
    variable           varchar(40) NOT NULL,   -- precipitation, temperature_2m, weather_code
    obtenido_en        timestamptz NOT NULL,   -- cuándo lo pidió el sistema
    horizonte_min      integer,                -- minutos futuros (null = observado/análisis)
    valor              numeric(12,4),
    unidad             varchar(20),
    raw                jsonb,                  -- respuesta original para auditoría
    CONSTRAINT uq_digital UNIQUE
        (fuente, fk_id_comunidad, variable, obtenido_en, horizonte_min)
);

CREATE TABLE IF NOT EXISTS categoria_pronostico_temporal (
    id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre   varchar(50) NOT NULL UNIQUE,
    slug     varchar(50) NOT NULL UNIQUE,
    orden    smallint NOT NULL DEFAULT 0,
    estado   estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy bigint,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pronostico_temporal (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo                  text NOT NULL UNIQUE,
    fk_id_categoria         uuid NOT NULL REFERENCES categoria_pronostico_temporal(id)
                                                        ON DELETE RESTRICT,
    texto                   varchar(200) NOT NULL,
    geom                    geometry(Point, 4326) NOT NULL,
    fk_id_comunidad         uuid REFERENCES comunidad(id) ON DELETE SET NULL,
    fecha_registro          date   NOT NULL,
    tiempo_vigencia         smallint NOT NULL CHECK (tiempo_vigencia BETWEEN 1 AND 365),
    descripcion_observacion varchar(500),
    probabilidad            numeric(5,4) CHECK (probabilidad BETWEEN 0 AND 1),
    estado                  estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy               bigint,
    creado_en               timestamptz NOT NULL DEFAULT now(),
    actualizado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_probabilidad CHECK (probabilidad IS NULL OR probabilidad > 0)
);

ALTER TABLE pronostico_temporal
    ADD COLUMN IF NOT EXISTS latitud double precision GENERATED ALWAYS AS (ST_Y(geom)) STORED,
    ADD COLUMN IF NOT EXISTS longitud double precision GENERATED ALWAYS AS (ST_X(geom)) STORED;

CREATE TABLE IF NOT EXISTS usuario_pronostico_temporal (
    fk_id_usuario            uuid NOT NULL REFERENCES usuario(id)            ON DELETE CASCADE,
    fk_id_pronostico_temporal uuid NOT NULL REFERENCES pronostico_temporal(id) ON DELETE CASCADE,
    id_legacy bigint,
    PRIMARY KEY (fk_id_usuario, fk_id_pronostico_temporal)
);

CREATE TABLE IF NOT EXISTS variante_local (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    texto                     varchar(200) NOT NULL,
    fk_id_recomendacion_local uuid NOT NULL REFERENCES recomendacion_local(id)
                                                            ON DELETE CASCADE,
    ambito                    ambito_recomendacion NOT NULL DEFAULT 'MUNICIPIO',
    estado                    estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy                 bigint,
    creado_en                 timestamptz NOT NULL DEFAULT now(),
    actualizado_en            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usuario_comunidad (
    fk_id_usuario   uuid NOT NULL REFERENCES usuario(id)   ON DELETE CASCADE,
    fk_id_comunidad uuid NOT NULL REFERENCES comunidad(id) ON DELETE CASCADE,
    fk_id_municipio uuid NOT NULL REFERENCES municipio(id) ON DELETE RESTRICT,
    vigente_desde   date NOT NULL DEFAULT current_date,
    vigente_hasta   date,
    estado          estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy       bigint,
    PRIMARY KEY (fk_id_usuario, fk_id_comunidad, vigente_desde),
    CONSTRAINT chk_vigencia_uc CHECK (
        vigente_hasta IS NULL OR vigente_hasta >= vigente_desde
    )
);

CREATE TABLE IF NOT EXISTS permiso (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug  varchar(80) NOT NULL UNIQUE,
    nombre varchar(120) NOT NULL,
    modulo varchar(60) NOT NULL
);

CREATE TABLE IF NOT EXISTS rol_permiso (
    fk_id_rol     uuid NOT NULL REFERENCES rol(id)     ON DELETE CASCADE,
    fk_id_permiso uuid NOT NULL REFERENCES permiso(id) ON DELETE CASCADE,
    PRIMARY KEY (fk_id_rol, fk_id_permiso)
);

CREATE TABLE IF NOT EXISTS menu (
    id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id uuid REFERENCES menu(id) ON DELETE CASCADE,
    nombre   varchar(50) NOT NULL,
    url      varchar(150) NOT NULL,
    orden    smallint NOT NULL DEFAULT 0,
    icono    varchar(50),
    fk_id_permiso uuid REFERENCES permiso(id) ON DELETE SET NULL,
    estado   estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy bigint,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS menu_rol (
    fk_id_menu uuid NOT NULL REFERENCES menu(id) ON DELETE CASCADE,
    fk_id_rol  uuid NOT NULL REFERENCES rol(id)  ON DELETE CASCADE,
    PRIMARY KEY (fk_id_menu, fk_id_rol)
);

CREATE TABLE IF NOT EXISTS login_rol (
    fk_id_login uuid NOT NULL REFERENCES login(id) ON DELETE CASCADE,
    fk_id_rol   uuid NOT NULL REFERENCES rol(id)   ON DELETE CASCADE,
    estado      estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy   bigint,
    PRIMARY KEY (fk_id_login, fk_id_rol)
);

CREATE TABLE IF NOT EXISTS token_refresh (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_usuario  uuid NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    familia_id     uuid NOT NULL,
    jti_hash       text NOT NULL UNIQUE,
    emitido_en     timestamptz NOT NULL DEFAULT now(),
    expira_en      timestamptz NOT NULL,
    revocado_en    timestamptz,
    revocado_motivo varchar(60),
    user_agent     text,
    ip_origen      inet,
    CONSTRAINT chk_expiracion CHECK (expira_en > emitido_en)
);

CREATE TABLE IF NOT EXISTS variable_climatica (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      varchar(80) NOT NULL,
    slug        varchar(80) NOT NULL UNIQUE,
    unidad      varchar(30) NOT NULL,
    fuente      varchar(40) NOT NULL CHECK (fuente IN
        ('OPEN_METEO_ARCHIVE','OPEN_METEO_FORECAST','CHIRPS','SENAMHI','ESTACION_LOCAL','SENTINEL2')),
    es_acumulado boolean NOT NULL DEFAULT false,
    requiere_geoide boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS serie_climatica (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_variable    uuid NOT NULL REFERENCES variable_climatica(id) ON DELETE RESTRICT,
    fk_id_comunidad   uuid REFERENCES comunidad(id) ON DELETE CASCADE,
    geom              geometry(Point, 4326) NOT NULL,
    fecha             date NOT NULL,
    valor             numeric(12,4) NOT NULL,
    calidad           smallint NOT NULL DEFAULT 100 CHECK (calidad BETWEEN 0 AND 100),
    ingested_en       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_serie_unica UNIQUE (fk_id_variable, fk_id_comunidad, fecha)
);

CREATE TABLE IF NOT EXISTS escena_satelital (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proveedor     varchar(40) NOT NULL DEFAULT 'ELEMENT84',
    coleccion     varchar(80) NOT NULL,
    escena_id     text NOT NULL,
    datetime      timestamptz NOT NULL,
    plataforma    varchar(30),
    cloud_cover   numeric(6,4) CHECK (cloud_cover BETWEEN 0 AND 1),
    bbox          geometry(Polygon, 4326) NOT NULL,
    href_nir      text NOT NULL,
    href_red      text NOT NULL,
    href_scl      text NOT NULL,
    ingested_en   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_escena UNIQUE (proveedor, coleccion, escena_id)
);

CREATE TABLE IF NOT EXISTS agregado_satelital (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_escena      uuid NOT NULL REFERENCES escena_satelital(id) ON DELETE CASCADE,
    fk_id_comunidad   uuid REFERENCES comunidad(id) ON DELETE CASCADE,
    periodo           date NOT NULL,
    variable          varchar(20) NOT NULL CHECK (variable IN ('NDVI','NDVI_EVI')),
    valor_promedio    numeric(10,6) NOT NULL,
    valor_p10         numeric(10,6),
    valor_p90         numeric(10,6),
    pixeles_validos   integer NOT NULL CHECK (pixeles_validos >= 0),
    fraccion_nube     numeric(6,4) NOT NULL CHECK (fraccion_nube BETWEEN 0 AND 1),
    metodo            varchar(40) NOT NULL DEFAULT 'COG_MEAN',
    calculado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_agregado UNIQUE
        (fk_id_comunidad, periodo, variable)
);

CREATE TABLE IF NOT EXISTS verificacion_pronostico (
    id                            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_pronostico_temporal     uuid REFERENCES pronostico_temporal(id)   ON DELETE CASCADE,
    fk_id_pronostico_estacional   uuid REFERENCES pronostico_estacional(id) ON DELETE CASCADE,
    fk_id_variable                uuid NOT NULL REFERENCES variable_climatica(id) ON DELETE RESTRICT,
    fk_id_comunidad               uuid NOT NULL REFERENCES comunidad(id) ON DELETE CASCADE,
    horizonte_dias                smallint NOT NULL CHECK (horizonte_dias BETWEEN 1 AND 365),
    periodo_inicio                date NOT NULL,
    periodo_fin                   date NOT NULL,
    valor_pronosticado            numeric(12,4),
    valor_observado               numeric(12,4),
    error_absoluto                numeric(12,4) GENERATED ALWAYS AS
                                  (abs(valor_observado - valor_pronosticado)) STORED,
    sesgo                         numeric(12,4) GENERATED ALWAYS AS
                                  (valor_pronosticado - valor_observado) STORED,
    acierto_categoria             boolean,
    brier_score                   numeric(6,4) CHECK (brier_score BETWEEN 0 AND 1),
    skill_vs_climatologia         numeric(8,4),
    estado                        estado_verificacion NOT NULL DEFAULT 'PENDIENTE',
    es_autoevaluada               boolean NOT NULL DEFAULT true,
    verificado_por                uuid REFERENCES usuario(id) ON DELETE SET NULL,
    verificado_en                 timestamptz,
    notas                         text,
    CONSTRAINT chk_un_pronostico CHECK (
        num_nonnulls(fk_id_pronostico_temporal, fk_id_pronostico_estacional) = 1
    ),
    CONSTRAINT chk_periodo_verif CHECK (periodo_fin >= periodo_inicio)
);

CREATE TABLE IF NOT EXISTS traduccion_indicador (
    fk_id_indicador uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    locale          varchar(10) NOT NULL CHECK (locale ~ '^[a-z]{2}(-[A-Z]{2})?$'),
    campo           varchar(30) NOT NULL CHECK (campo IN ('nombre','nombre_cientifico')),
    valor           varchar(200) NOT NULL,
    PRIMARY KEY (fk_id_indicador, locale, campo)
);

CREATE TABLE IF NOT EXISTS sinonimo_indicador (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_indicador     uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    texto               varchar(200) NOT NULL,
    idioma              varchar(40),
    fk_id_comunidad     uuid REFERENCES comunidad(id) ON DELETE SET NULL,
    fk_id_autor         uuid REFERENCES usuario(id) ON DELETE SET NULL,
    fuente              varchar(30) NOT NULL DEFAULT 'CAMPO',
    estado              estado_registro NOT NULL DEFAULT 'ACTIVO'
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sinonimo ON sinonimo_indicador (fk_id_indicador, lower(texto), fk_id_comunidad);

CREATE TABLE IF NOT EXISTS auditoria (
    id bigint GENERATED ALWAYS AS IDENTITY,
    fk_id_usuario  uuid REFERENCES usuario(id) ON DELETE SET NULL,
    fk_id_rol      uuid REFERENCES rol(id) ON DELETE SET NULL,
    accion         varchar(40) NOT NULL CHECK (accion IN
        ('CREAR','LEER','ACTUALIZAR','ELIMINAR','EXPORTAR','INGRESAR','VALIDAR','RECHAZAR')),
    tabla          varchar(60) NOT NULL,
    registro_id    uuid,
    id_legacy      bigint,
    datos_antes    jsonb,
    datos_despues  jsonb,
    campos_cambiados text[],
    ip_origen      inet,
    user_agent     text,
    occurred_at    timestamptz NOT NULL DEFAULT now(),
PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE IF NOT EXISTS auditoria_default PARTITION OF auditoria DEFAULT;

CREATE TABLE IF NOT EXISTS sincronizacion_log (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_usuario  uuid NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    dispositivo_id uuid NOT NULL,
    app_version    varchar(20),
    iniciada_en    timestamptz NOT NULL DEFAULT now(),
    completada_en  timestamptz,
    registros_enviados integer NOT NULL DEFAULT 0,
    registros_aceptados integer NOT NULL DEFAULT 0,
    registros_rechazados integer NOT NULL DEFAULT 0,
    conflictos      integer NOT NULL DEFAULT 0,
    resultado      varchar(20) CHECK (resultado IN ('OK','PARCIAL','ERROR')),
    detalle        jsonb
);

CREATE TABLE IF NOT EXISTS ventana_observacion (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre            varchar(80) NOT NULL,
    slug              varchar(80) NOT NULL UNIQUE,
    tipo              tipo_ventana NOT NULL,
    mes_inicio        smallint NOT NULL CHECK (mes_inicio BETWEEN 1 AND 12),
    dia_inicio        smallint NOT NULL CHECK (dia_inicio BETWEEN 1 AND 31),
    mes_fin           smallint NOT NULL CHECK (mes_fin BETWEEN 1 AND 12),
    dia_fin           smallint NOT NULL CHECK (dia_fin BETWEEN 1 AND 31),
    variable_objetivo varchar(60) NOT NULL,   -- variable climatica que se predice
    ambito           ambito_recomendacion NOT NULL DEFAULT 'NACIONAL',
    descripcion       text,
    fuente_metodologica text,
    vigente           boolean NOT NULL DEFAULT true,
    estado            estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy         bigint,
    creado_en         timestamptz NOT NULL DEFAULT now(),
    actualizado_en    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS serie_indicador (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_indicador       uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    fk_id_comunidad       uuid NOT NULL REFERENCES comunidad(id)         ON DELETE CASCADE,
    fk_id_ventana         uuid REFERENCES ventana_observacion(id)        ON DELETE SET NULL,
    anio                  smallint NOT NULL CHECK (anio BETWEEN 1900 AND 2100),
    n_registros           integer NOT NULL DEFAULT 0,
    n_observaciones       integer NOT NULL DEFAULT 0,
    n_comunidades         integer NOT NULL DEFAULT 1,
    fecha_primera         date,
    fecha_ultima          date,
    valor_medio           numeric(12,4),
    valor_minimo          numeric(12,4),
    valor_maximo          numeric(12,4),
    confianza_media       numeric(3,2),
    comportamiento_dominante uuid REFERENCES comportamiento(id)       ON DELETE SET NULL,
    estado                estado_registro NOT NULL DEFAULT 'ACTIVO',
    calculado_en          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_serie_indicador UNIQUE
        (fk_id_indicador, fk_id_comunidad, fk_id_ventana, anio)
);

CREATE TABLE IF NOT EXISTS norma_climatica (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_variable    uuid NOT NULL REFERENCES variable_climatica(id) ON DELETE CASCADE,
    fk_id_comunidad   uuid NOT NULL REFERENCES comunidad(id)         ON DELETE CASCADE,
    anio_inicio       smallint NOT NULL CHECK (anio_inicio BETWEEN 1900 AND 2100),
    anio_fin          smallint NOT NULL CHECK (anio_fin BETWEEN 1900 AND 2100),
    media             numeric(12,4) NOT NULL,
    desviacion        numeric(12,4) NOT NULL,
    percentil_10      numeric(12,4),
    percentil_90      numeric(12,4),
    n_datos           integer NOT NULL CHECK (n_datos > 0),
    cobertura         numeric(5,2) NOT NULL CHECK (cobertura BETWEEN 0 AND 100),
    calculado_en      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_periodo_norma CHECK (anio_fin > anio_inicio),
    CONSTRAINT uq_norma UNIQUE (fk_id_variable, fk_id_comunidad, anio_inicio, anio_fin)
);

CREATE TABLE IF NOT EXISTS desviacion_indicador (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_indicador        uuid NOT NULL REFERENCES indicador_natural(id)     ON DELETE CASCADE,
    fk_id_comunidad        uuid NOT NULL REFERENCES comunidad(id)             ON DELETE CASCADE,
    fk_id_ventana          uuid REFERENCES ventana_observacion(id)           ON DELETE SET NULL,
    anio                   smallint NOT NULL CHECK (anio BETWEEN 1900 AND 2100),
    fk_id_variable_referencia uuid REFERENCES variable_climatica(id)          ON DELETE SET NULL,
    valor_observado        numeric(12,4) NOT NULL,
    valor_norma            numeric(12,4) NOT NULL,
    desviacion_tipica      numeric(12,4) NOT NULL,
    anomalia               numeric(8,4) NOT NULL,   -- (observado - norma) / desviacion
    correlacion_pearson    numeric(6,4) CHECK (correlacion_pearson BETWEEN -1 AND 1),
    n_observaciones        integer NOT NULL DEFAULT 0,
    es_significativa       boolean NOT NULL DEFAULT false,
    estado                 estado_registro NOT NULL DEFAULT 'ACTIVO',
    calculado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_anomalia_signo CHECK (abs(anomalia) <= 6),
    CONSTRAINT uq_desviacion UNIQUE
        (fk_id_indicador, fk_id_comunidad, fk_id_ventana, anio,
         fk_id_variable_referencia)
);

CREATE TABLE IF NOT EXISTS calificacion_indicador (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_id_indicador   uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    ambito            ambito_recomendacion NOT NULL DEFAULT 'NACIONAL',
    fk_id_municipio   uuid REFERENCES municipio(id) ON DELETE CASCADE,
    nivel             nivel_calificacion NOT NULL DEFAULT 'EN_VERIFICACION',
    n_observaciones   integer NOT NULL DEFAULT 0,
    n_verificaciones  integer NOT NULL DEFAULT 0,
    n_aciertos        integer NOT NULL DEFAULT 0,
    evaluado_por      uuid REFERENCES usuario(id) ON DELETE SET NULL,
    evaluado_en       timestamptz NOT NULL DEFAULT now(),
    notas             text,
    CONSTRAINT chk_municipio_ambito CHECK (
        (ambito = 'MUNICIPIO' AND fk_id_municipio IS NOT NULL) OR ambito <> 'MUNICIPIO'
    ),
    CONSTRAINT uq_calificacion UNIQUE NULLS NOT DISTINCT
        (fk_id_indicador, ambito, fk_id_municipio)
);

CREATE TABLE IF NOT EXISTS indicador_natural_caracteristica (
    fk_id_indicador_natural uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    fk_id_caracteristica     uuid NOT NULL REFERENCES caracteristica(id)    ON DELETE CASCADE,
    estado                   estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy                bigint,
    PRIMARY KEY (fk_id_indicador_natural, fk_id_caracteristica)
);

-- ============ INDICES ============

CREATE UNIQUE INDEX IF NOT EXISTS uq_indicador_nombre_cientifico
    ON indicador_natural (lower(nombre_cientifico))
    WHERE nombre_cientifico IS NOT NULL AND estado <> 'ELIMINADO';

CREATE INDEX IF NOT EXISTS ind_indicador_activo ON indicador_natural (nombre) WHERE estado = 'ACTIVO';

CREATE INDEX IF NOT EXISTS ind_comportamiento_grupo ON comportamiento (grupo_id) WHERE grupo_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ind_significado_grupo   ON significado (grupo_id)   WHERE grupo_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS gist_comunidad_geom ON comunidad USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_comunidad_coordenadas
    ON comunidad (latitud, longitud)
    WHERE estado = 'ACTIVO';

CREATE INDEX IF NOT EXISTS ind_comunidad_zona ON comunidad (fk_id_zona_geografica);

CREATE INDEX IF NOT EXISTS ind_observacion_comunidad ON observacion (fk_id_comunidad, fecha_inicio DESC);

CREATE INDEX IF NOT EXISTS ind_observacion_municipio ON observacion (fk_id_municipio, fecha_inicio DESC);

CREATE INDEX IF NOT EXISTS ind_observacion_pendiente  ON observacion (fk_id_municipio, fecha_inicio)
    WHERE es_validada = false AND estado = 'ACTIVO';

CREATE INDEX IF NOT EXISTS ind_observacion_responsable ON observacion (fk_id_usuario_responsable, fecha_inicio DESC);

CREATE INDEX IF NOT EXISTS ind_registro_observacion ON observacion_registro (fk_id_observacion, orden);

CREATE INDEX IF NOT EXISTS ind_registro_indicador   ON observacion_registro (fk_id_indicador_natural);

CREATE INDEX IF NOT EXISTS ind_registro_fecha
    ON observacion_registro (observado_en)
    WHERE observado_en IS NOT NULL;

CREATE INDEX IF NOT EXISTS ind_registro_calidad
    ON observacion_registro (fk_id_observacion)
    WHERE es_calidad_dudosa;

CREATE INDEX IF NOT EXISTS ind_consentimiento_indicador ON consentimiento_uso (fk_id_indicador, alcance);

CREATE INDEX IF NOT EXISTS ind_evidencia_indicador
    ON evidencia (fk_id_indicador_natural, orden, creado_en)
    WHERE tipo = 'FOTO' AND estado = 'CONFIRMADA';

CREATE INDEX IF NOT EXISTS ind_mc_comunidad ON municipio_comunidad (fk_id_comunidad);

CREATE INDEX IF NOT EXISTS ind_mc_principal ON municipio_comunidad (fk_id_comunidad)
    WHERE es_principal;

CREATE INDEX IF NOT EXISTS ind_aviso_vigencia ON aviso (vigencia_fin)
    WHERE estado = 'ACTIVO';

CREATE INDEX IF NOT EXISTS ind_aviso_municipio ON aviso (fk_id_municipio, vigencia_inicio DESC);

CREATE INDEX IF NOT EXISTS ind_digital_comunidad_fecha
    ON pronostico_digital (fk_id_comunidad, obtenido_en DESC);

CREATE INDEX IF NOT EXISTS ind_usuario_comunidad ON usuario_comunidad (fk_id_usuario);

CREATE INDEX IF NOT EXISTS ind_uc_municipio ON usuario_comunidad (fk_id_municipio)
    WHERE vigente_hasta IS NULL;

CREATE INDEX IF NOT EXISTS ind_refresh_usuario ON token_refresh (fk_id_usuario, familia_id)
    WHERE revocado_en IS NULL;

CREATE INDEX IF NOT EXISTS ind_refresh_expiracion ON token_refresh (expira_en);

CREATE INDEX IF NOT EXISTS ind_serie_fecha ON serie_climatica (fk_id_variable, fecha DESC);

CREATE INDEX IF NOT EXISTS gist_serie_geom ON serie_climatica USING gist (geom);

CREATE INDEX IF NOT EXISTS ind_agregado_periodo ON agregado_satelital (periodo DESC);

CREATE INDEX IF NOT EXISTS ind_verif_variable ON verificacion_pronostico
    (fk_id_variable, periodo_inicio DESC, horizonte_dias);

CREATE INDEX IF NOT EXISTS ind_verif_pendiente ON verificacion_pronostico (periodo_fin)
    WHERE estado = 'PENDIENTE';

CREATE INDEX IF NOT EXISTS ind_auditoria_usuario ON auditoria (fk_id_usuario, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ind_auditoria_tabla   ON auditoria (tabla, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ind_auditoria_cambios ON auditoria USING gin (datos_despues);

CREATE INDEX IF NOT EXISTS ind_sync_usuario ON sincronizacion_log (fk_id_usuario, iniciada_en DESC);

CREATE INDEX IF NOT EXISTS ind_serie_indicador_anio ON serie_indicador
    (fk_id_indicador, anio);

CREATE INDEX IF NOT EXISTS ind_serie_ventana ON serie_indicador (fk_id_ventana, anio);

CREATE INDEX IF NOT EXISTS ind_norma_variable ON norma_climatica (fk_id_variable, anio_inicio);

CREATE INDEX IF NOT EXISTS ind_desviacion_indicador ON desviacion_indicador
    (fk_id_indicador, anio);

CREATE INDEX IF NOT EXISTS ind_calificacion_nivel ON calificacion_indicador (nivel, ambito);

-- ============ VISTAS ============

CREATE OR REPLACE VIEW v_registro_territorial AS
SELECT r.id                    AS registro_id,
       o.id                    AS observacion_id,
       o.codigo_corto,
       o.fecha_inicio,
       co.id                   AS comunidad_id,
       co.nombre               AS comunidad,
       m.id                    AS municipio_id,
       m.nombre                AS municipio,
       p.nombre                AS provincia,
       d.nombre                AS departamento,
       z.nombre                AS zona,
       g.grupo                AS grupo,
       i.nombre                AS indicador,
       i.nombre_cientifico,
       c.caracteristica,
       r.presencia,
       r.valor_texto,
       r.valor_numerico,
       r.unidad,
       s.significado,
       r.confianza,
       r.es_calidad_dudosa,
       r.observado_en
FROM observacion_registro r
JOIN observacion o          ON o.id  = r.fk_id_observacion
JOIN comunidad co           ON co.id = o.fk_id_comunidad
JOIN municipio_comunidad mc ON mc.fk_id_comunidad = co.id AND mc.es_principal
JOIN municipio m            ON m.id  = mc.fk_id_municipio
JOIN provincia_municipio pm ON pm.fk_id_municipio = m.id
JOIN provincia p            ON p.id  = pm.fk_id_provincia
JOIN departamento_provincia dp ON dp.fk_id_provincia = p.id
JOIN departamento d         ON d.id  = dp.fk_id_departamento
LEFT JOIN zona_geografica z  ON z.id  = co.fk_id_zona_geografica
JOIN indicador_natural i     ON i.id  = r.fk_id_indicador_natural
JOIN grupo_indicador_natural gi ON gi.id_indicador = i.id
JOIN grupo g                 ON g.id  = gi.id_grupo
LEFT JOIN caracteristica c   ON c.id  = r.fk_id_caracteristica
LEFT JOIN significado s      ON s.id  = r.fk_id_significado;

CREATE OR REPLACE VIEW v_indicador_confiabilidad AS
SELECT r.fk_id_indicador_natural            AS indicador_id,
       o.fk_id_municipio,
       count(*)                             AS n_observaciones,
       count(*) FILTER (WHERE r.es_calidad_dudosa) AS n_dudosas,
       round(100.0 * count(*) FILTER (WHERE r.es_calidad_dudosa)
             / nullif(count(*), 0), 1)       AS pct_dudosas,
       avg(r.confianza)                      AS confianza_media,
       count(DISTINCT o.fk_id_comunidad)     AS comunidades_cubiertas
FROM observacion_registro r
JOIN observacion o ON o.id = r.fk_id_observacion
WHERE o.es_validada
GROUP BY 1, 2;

CREATE OR REPLACE VIEW v_primera_observacion AS
SELECT r.fk_id_indicador_natural  AS indicador_id,
       o.fk_id_comunidad           AS comunidad_id,
       extract(year FROM o.fecha_inicio)::int AS anio,
       min(o.fecha_inicio)         AS primera_fecha,
       extract(doy FROM min(o.fecha_inicio))::int AS dia_del_anio,
       count(*)                    AS n_registros
FROM observacion_registro r
JOIN observacion o ON o.id = r.fk_id_observacion
WHERE o.es_validada
  AND o.estado = 'ACTIVO'
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW v_tendencia_fenologia AS
SELECT indicador_id,
       comunidad_id,
       dia_del_anio,
       (regr_slope(dia_del_anio, anio))::numeric(8,4) AS dias_por_anio,
       (regr_slope(dia_del_anio, anio) * 10)::numeric(8,2) AS dias_por_decada,
       count(*) AS n_anos,
       CASE WHEN count(*) >= 10 THEN true ELSE false END AS es_concluyente
FROM v_primera_observacion
GROUP BY indicador_id, comunidad_id, dia_del_anio;

CREATE OR REPLACE VIEW v_verificaciones_pendientes AS
SELECT id, fk_id_comunidad, periodo_fin, estado
FROM verificacion_pronostico
WHERE estado = 'PENDIENTE' AND periodo_fin < CURRENT_DATE;

CREATE OR REPLACE VIEW v_calificacion_vigente AS
SELECT ci.ambito,
       ci.nivel,
       i.nombre          AS indicador,
       ci.n_observaciones,
       ci.n_verificaciones,
       ci.n_aciertos
FROM calificacion_indicador ci
JOIN indicador_natural i ON i.id = ci.fk_id_indicador;

