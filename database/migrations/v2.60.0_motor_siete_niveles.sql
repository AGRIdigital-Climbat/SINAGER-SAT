-- =============================================================================
-- v2.60.0 — Motor de aprobaciones RIDA: cadena de 7 niveles desde ENVIADA
--
-- Reemplaza la cadena de 5 niveles de la v2.59.0 (enviado → validacion →
-- aprobado → despacho → entregado) por:
--   validacion → viceministro → dgea → revision_articulos → suministro →
--   despacho → entrega
--
-- Decisiones de diseño (acordadas con el cliente):
--   * El motor arranca al crear la solicitud (etapa ENVIADA); se elimina
--     BORRADOR y las acciones enviar/revisar/observar/corregir/validar/
--     iniciar-aprobacion/autorizar/cerrar.
--   * Nivel 1 (VIDECI Departamental) corre sobre ENVIADA y al aprobar pasa a
--     EN_APROBACION; niveles 2-4 en EN_APROBACION; el nivel 4 (revision de
--     articulos) pasa a APROBADA; suministro → AUTORIZADA; despacho →
--     DESPACHADA; entrega → ENTREGADA y cierre automatico a CERRADA.
--   * 3 roles nuevos: 15 Viceministro, 16 DGEA, 17 Gestion de Suministro.
--   * Nivel 4 exige calculo persistido SOLO si la modalidad tiene motor
--     (nueva columna rida.cat_modalidad.tiene_motor_calculo).
--   * Modalidad Ayuda Humanitaria excluida de este motor: conserva su cadena
--     de 7 niveles en rida.aprobacion_cadena_ayuda (api/ayuda_humanitaria),
--     pero su etapa de entrada tambien pasa a ENVIADA.
--
-- Idempotente: puede aplicarse 2 veces sin efecto adverso.
-- =============================================================================

-- 1. Roles nuevos --------------------------------------------------------------
INSERT INTO usuarios.rol (id_rol, nombre, descripcion) VALUES
    (15, 'Viceministro', 'Viceministro: visado nacional (niveles viceministro y revision de articulos)'),
    (16, 'DGEA', 'Direccion General de Emergencia y Auxilio: aprobacion nacional'),
    (17, 'Gestion de Suministro', 'Gestion de Suministro: autorizacion y disposicion de articulos')
ON CONFLICT (id_rol) DO NOTHING;

SELECT setval('usuarios.rol_id_rol_seq',
              GREATEST((SELECT MAX(id_rol) FROM usuarios.rol), 17));

-- 2. Permisos RIDA para los roles nuevos ---------------------------------------
-- Misma matriz que el rol 9 (VIDECI Departamental): CREATE, READ, UPDATE.
INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT v.id_rol, a.id_aplicacion, ac.id_accion
FROM (VALUES (15), (16), (17)) AS v(id_rol)
CROSS JOIN usuarios.aplicacion a
CROSS JOIN usuarios.accion ac
WHERE a.codigo = 'RIDA' AND ac.codigo IN ('CREATE', 'READ', 'UPDATE')
ON CONFLICT (id_rol, id_aplicacion, id_accion) DO NOTHING;

-- 3. Flag de motor de calculo por modalidad ------------------------------------
ALTER TABLE rida.cat_modalidad
  ADD COLUMN IF NOT EXISTS tiene_motor_calculo BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE rida.cat_modalidad SET tiene_motor_calculo = TRUE WHERE id_modalidad = 1;

COMMENT ON COLUMN rida.cat_modalidad.tiene_motor_calculo IS
    'Si TRUE, el nivel revision_articulos del motor de visaciones exige un '
    'calculo persistido en rida.ejecucion_calculo (POST /ayuda-humanitaria/'
    'calculos en modo operativo). Si FALSE el visado es manual. Inicialmente '
    'solo Ayuda Humanitaria (id 1) lo tiene; esa modalidad usa su propio motor.';

-- 4. Requisito "Informe de validacion" para las modalidades que no lo tienen ---
-- El nivel 1 (VIDECI Departamental) adjunta el informe en el PUT del visado;
-- se guarda contra este requisito (instancia 2). La modalidad 4 ya tiene el
-- requisito 69 ("Informe de validacion departamental → despacho") y la 1
-- (Ayuda Humanitaria) el 11, pero esa modalidad no usa este motor.
INSERT INTO rida.cat_requisito
    (id_modalidad, orden, nombre_paso, id_tipo_documento, instancia,
     es_documento, es_hito_aprobacion, activo)
SELECT m.id_modalidad,
       (SELECT COALESCE(MAX(r.orden), 0) + 1
        FROM rida.cat_requisito r WHERE r.id_modalidad = m.id_modalidad),
       'Informe de validación departamental', 24, 2, TRUE, FALSE, TRUE
FROM rida.cat_modalidad m
WHERE m.id_modalidad IN (2, 3)
  AND NOT EXISTS (
      SELECT 1 FROM rida.cat_requisito r2
      WHERE r2.id_modalidad = m.id_modalidad
        AND r2.nombre_paso ILIKE 'Informe de validación%');

-- repositorio.documentos.id_tipo_documento es NOT NULL: repara los requisitos
-- de informe creados sin tipo por una version previa de esta migracion.
UPDATE rida.cat_requisito SET id_tipo_documento = 24
WHERE nombre_paso ILIKE 'Informe de validación%'
  AND instancia = 2 AND id_tipo_documento IS NULL;

-- 5. Soltar los CHECK de nivel y orden ANTES de sembrar la cadena nueva --------
ALTER TABLE rida.aprobacion_cadena
  DROP CONSTRAINT IF EXISTS aprobacion_cadena_nivel_check;
ALTER TABLE rida.aprobacion_cadena
  DROP CONSTRAINT IF EXISTS aprobacion_cadena_orden_check;
ALTER TABLE rida.aprobaciones_solicitud
  DROP CONSTRAINT IF EXISTS aprobaciones_solicitud_nivel_check;

-- 6. Cadena por defecto de 7 niveles -------------------------------------------
-- A fecha de esta migracion: 0 filas en aprobaciones_solicitud y la cadena por
-- defecto es la de 5 niveles de la v2.59.0; se reemplaza completa.
DELETE FROM rida.aprobacion_cadena WHERE id_modalidad IS NULL;

INSERT INTO rida.aprobacion_cadena (id_modalidad, nivel, orden, activo)
SELECT NULL, v.nivel, v.orden, TRUE
FROM (VALUES ('validacion', 1), ('viceministro', 2), ('dgea', 3),
             ('revision_articulos', 4), ('suministro', 5), ('despacho', 6),
             ('entrega', 7))
     AS v(nivel, orden)
WHERE NOT EXISTS (SELECT 1 FROM rida.aprobacion_cadena WHERE id_modalidad IS NULL);

-- 7. CHECKs nuevos --------------------------------------------------------------
ALTER TABLE rida.aprobacion_cadena
  ADD CONSTRAINT aprobacion_cadena_nivel_check
  CHECK (nivel IN ('validacion', 'viceministro', 'dgea', 'revision_articulos',
                   'suministro', 'despacho', 'entrega'));
ALTER TABLE rida.aprobacion_cadena
  ADD CONSTRAINT aprobacion_cadena_orden_check
  CHECK (orden >= 1 AND orden <= 7);
ALTER TABLE rida.aprobaciones_solicitud
  ADD CONSTRAINT aprobaciones_solicitud_nivel_check
  CHECK (nivel IN ('validacion', 'viceministro', 'dgea', 'revision_articulos',
                   'suministro', 'despacho', 'entrega'));

-- 8. Etapas retiradas del grafo ------------------------------------------------
-- Se conservan las filas (historial/bitacora) pero dejan de listarse.
UPDATE rida.cat_etapa_solicitud
SET activo = FALSE
WHERE codigo IN ('BORRADOR', 'EN_REVISION', 'OBSERVADA', 'VALIDADA');

-- 9. Remapeo de solicitudes existentes -----------------------------------------
-- BORRADOR/EN_REVISION/OBSERVADA/VALIDADA desaparecen del grafo: todas vuelven
-- a la etapa de entrada (ENVIADA). El motor de Ayuda Humanitaria aun no estaba
-- iniciado en ninguna (0 filas en aprobaciones_ayuda_humanitaria), asi que
-- ENVIADA es la etapa correcta tambien para esa modalidad.
UPDATE rida.solicitud
SET etapa = 'ENVIADA'
WHERE etapa IN ('BORRADOR', 'EN_REVISION', 'OBSERVADA', 'VALIDADA');

-- 10. Comentarios ---------------------------------------------------------------
COMMENT ON TABLE rida.aprobacion_cadena IS
    'Niveles de la cadena de visaciones por modalidad de solicitud. '
    'id_modalidad NULL = cadena por defecto (los 7 niveles de la v2.60.0: '
    'validacion → viceministro → dgea → revision_articulos → suministro → '
    'despacho → entrega). La modalidad Ayuda Humanitaria (AYUDA_HUMANITARIA) '
    'no usa esta cadena: gestiona su propio motor de 7 niveles en '
    'aprobacion_cadena_ayuda.';
COMMENT ON COLUMN rida.aprobacion_cadena.orden IS
    'Posicion dentro de la cadena (1 = primer nivel). Debe respetar el orden '
    'semantico validacion < viceministro < dgea < revision_articulos < '
    'suministro < despacho < entrega.';
COMMENT ON TABLE rida.aprobaciones_solicitud IS
    'Maquina de visaciones del RIDA: una fila por nivel de la cadena activa de '
    'la modalidad. Secuencia estricta: solo se aprueba el primer nivel no '
    'aprobado. estado_global NO se almacena: se deriva en cada lectura como el '
    'badge del primer nivel no aprobado (EN_VALIDACION / VICEMINISTRO / DGEA / '
    'REVISION_ARTICULOS / SUMINISTRO / DESPACHO / EN_ENTREGA; cadena completa '
    '= ENTREGADO).';
