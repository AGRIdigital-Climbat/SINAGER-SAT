-- ============================================================================
-- SINAGERSAT - Migración v1.4.2 (idempotente)
-- 1. Restringe permisos del módulo EDAN: solo el rol 6 (UGR Municipio), junto a
--    admin (2) y superadmin (1), pueden crear/editar/eliminar. Los roles 3,4,5,7,8,9
--    quedan SOLO con READ (ver).
-- 2. Elimina las acciones de prueba TEST y VERIFY de usuarios.accion.
-- 3. Elimina las aplicaciones de prueba TEST y VERIFY de usuarios.aplicacion.
-- Aplica sobre migration_v1.4.1.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Permisos EDAN
-- ----------------------------------------------------------------------------

-- Roles 3,4,5 pierden CREATE/UPDATE/DELETE (conservan READ)
DELETE FROM usuarios.permiso p
WHERE p.id_aplicacion = (SELECT id_aplicacion FROM usuarios.aplicacion WHERE codigo = 'EDAN')
  AND p.id_accion IN (SELECT id_accion FROM usuarios.accion WHERE codigo IN ('CREATE', 'UPDATE', 'DELETE'))
  AND p.id_rol IN (3, 4, 5);

-- Asegurar READ para los roles que solo ven (3,4,5,7,8,9)
INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT r.id_rol, a.id_aplicacion, ac.id_accion
FROM (VALUES (3), (4), (5), (7), (8), (9)) AS r(id_rol)
CROSS JOIN (SELECT id_aplicacion FROM usuarios.aplicacion WHERE codigo = 'EDAN') a
CROSS JOIN (SELECT id_accion FROM usuarios.accion WHERE codigo = 'READ') ac
ON CONFLICT (id_rol, id_aplicacion, id_accion) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Acciones de prueba
-- ----------------------------------------------------------------------------

DELETE FROM usuarios.accion WHERE codigo IN ('TEST', 'VERIFY');

-- ----------------------------------------------------------------------------
-- 3. Aplicaciones de prueba
-- ----------------------------------------------------------------------------

DELETE FROM usuarios.aplicacion WHERE codigo IN ('TEST', 'VERIFY');

COMMIT;

SELECT 'IDEMPOTENT OK v1.4.2' AS resultado;
