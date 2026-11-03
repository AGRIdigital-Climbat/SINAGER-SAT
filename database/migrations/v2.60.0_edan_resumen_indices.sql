-- =============================================================================
-- v2.60.0 — Indices para las APIs de resumen/graficas EDAN (familia nueva)
-- GET /edan/resumen/formularios/... y /edan/resumen/edan/... filtran por
-- rango de fechas (desde/hasta) y agrupan por fecha; hoy no existe ningun
-- indice sobre esas columnas (solo los compuestos de sync).
-- Idempotente: puede aplicarse 2 veces sin efecto adverso.
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_edan_localidades_fecha_llenado
    ON edan.edan_localidades (fecha_llenado);

CREATE INDEX IF NOT EXISTS idx_edan_localidades_fecha_evento
    ON edan.edan_localidades (fecha_evento);

CREATE INDEX IF NOT EXISTS idx_edan_localidades_fecha_mod
    ON edan.edan_localidades (fecha_modificacion);

CREATE INDEX IF NOT EXISTS idx_edan_fecha_mod
    ON edan.edan (fecha_modificacion);

-- Series temporales de secciones (solo si se agregan por fecha de fila)
CREATE INDEX IF NOT EXISTS idx_fotografias_fecha_creacion
    ON edan.fotografias (fecha_creacion);

CREATE INDEX IF NOT EXISTS idx_aprobaciones_fecha_accion
    ON edan.aprobaciones_edan (fecha_ultima_accion);
