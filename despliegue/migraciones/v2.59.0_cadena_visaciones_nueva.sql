-- =============================================================================
-- v2.59.0 — Nueva cadena de visaciones de la solicitud (5 niveles)
-- (enviado → validacion → aprobado → despacho → entregado; reemplaza
--  ugr/alcalde/dgr/videcid/direccion. Modalidad Ayuda Humanitaria excluida:
--  conserva su propia cadena de 7 niveles en aprobacion_cadena_ayuda)
-- Idempotente: puede aplicarse 2 veces sin efecto adverso.
-- Orden estricto: soltar CHECK viejo -> remapear datos -> crear CHECK nuevo.
-- =============================================================================

-- 1. Soltar los CHECK viejos ---------------------------------------------------
ALTER TABLE rida.aprobacion_cadena
  DROP CONSTRAINT IF EXISTS aprobacion_cadena_nivel_check;
ALTER TABLE rida.aprobaciones_solicitud
  DROP CONSTRAINT IF EXISTS aprobaciones_solicitud_nivel_check;

-- 2. Remapeo de niveles existentes por posicion --------------------------------
-- Decidido con el cliente: reemplazo total. La nueva cadena tiene 5 niveles y
-- la vieja tambien, asi que cada nivel mantiene su ORDEN y cambia de nombre.
-- A fecha de esta migracion: 0 filas en aprobaciones_solicitud y solo la
-- cadena por defecto (id_modalidad NULL); el UPDATE cubre igualmente cadenas
-- por modalidad que pudieran existir.
--   ugr(1) -> enviado      alcalde(2) -> validacion   dgr(3) -> aprobado
--   videcid(4) -> despacho  direccion(5) -> entregado
UPDATE rida.aprobacion_cadena
SET nivel = CASE nivel
              WHEN 'ugr'       THEN 'enviado'
              WHEN 'alcalde'   THEN 'validacion'
              WHEN 'dgr'       THEN 'aprobado'
              WHEN 'videcid'   THEN 'despacho'
              WHEN 'direccion' THEN 'entregado'
            END
WHERE nivel IN ('ugr', 'alcalde', 'dgr', 'videcid', 'direccion');

-- 2b. Red de seguridad: si la cadena por defecto quedara vacia, siembra los
-- 5 niveles nuevos (la guarda del indice parcial la hace idempotente).
INSERT INTO rida.aprobacion_cadena (id_modalidad, nivel, orden, activo)
SELECT NULL, v.nivel, v.orden, TRUE
FROM (VALUES ('enviado', 1), ('validacion', 2), ('aprobado', 3),
             ('despacho', 4), ('entregado', 5))
     AS v(nivel, orden)
WHERE NOT EXISTS (SELECT 1 FROM rida.aprobacion_cadena WHERE id_modalidad IS NULL);

-- 3. CHECK nuevos ---------------------------------------------------------------
ALTER TABLE rida.aprobacion_cadena
  ADD CONSTRAINT aprobacion_cadena_nivel_check
  CHECK (nivel IN ('enviado', 'validacion', 'aprobado', 'despacho', 'entregado'));
ALTER TABLE rida.aprobaciones_solicitud
  ADD CONSTRAINT aprobaciones_solicitud_nivel_check
  CHECK (nivel IN ('enviado', 'validacion', 'aprobado', 'despacho', 'entregado'));

-- 4. Comentarios actualizados --------------------------------------------------
COMMENT ON TABLE rida.aprobacion_cadena IS
    'Niveles de la cadena de visaciones por modalidad de solicitud. '
    'id_modalidad NULL = cadena por defecto (los 5 niveles). '
    'La modalidad Ayuda Humanitaria (AYUDA_HUMANITARIA) no usa esta cadena: '
    'gestiona su propio motor de 7 niveles en aprobacion_cadena_ayuda.';
COMMENT ON COLUMN rida.aprobacion_cadena.orden IS
    'Posicion dentro de la cadena (1 = primer nivel). Debe respetar el orden '
    'semantico enviado < validacion < aprobado < despacho < entregado.';
COMMENT ON TABLE rida.aprobaciones_solicitud IS
    'Maquina de visaciones del RIDA: una fila por nivel de la cadena activa de '
    'la modalidad. Secuencia estricta: solo se aprueba el primer nivel no '
    'aprobado. estado_global NO se almacena: se deriva en cada lectura como el '
    'badge del primer nivel no aprobado (ENVIADO / EN_VALIDACION / '
    'APROBADO_EN_ATENCION / DESPACHO / ENTREGADO).';
