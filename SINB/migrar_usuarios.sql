-- Paso 3B: Migrar usuarios SINB a esquema usuarios
-- Credenciales: celular → usuario, carnet → contraseña
-- Roles: 1→admin(2), 2→UGR Municipio(6), 3→Usuario recolector(12), 4→Observador local(13)

SET statement_timeout = 0;

DROP TABLE IF EXISTS tmp_usuarios_sinb;
CREATE TEMP TABLE tmp_usuarios_sinb AS
WITH usuarios_base AS (
    SELECT 
        u.id_usuario, u.celular::text, u.ci::text, u.nombre, u.paterno, u.materno, u.correo,
        lr.t_rol_id_rol, m.municipio as mun_nombre
    FROM sinb.t_usuario u
    JOIN sinb.t_login l ON l.id_login = u.t_login_id_login
    JOIN sinb.t_login_rol lr ON lr.t_login_id_login = l.id_login
    JOIN sinb.t_usuario_comunidad uc ON uc.fk_t_usuario_id_usuario = u.id_usuario
    JOIN sinb.t_comunidad c ON c.id_comunidad = uc.fk_t_comunidad_id_comunidad
    JOIN sinb.t_municipio_comunidad mc ON mc.fk_t_comunidad_id_comunidad = c.id_comunidad
    JOIN sinb.t_municipio m ON m.id_municipio = mc.fk_t_municipio_id_municipio
    WHERE u.ci IS NOT NULL AND u.celular IS NOT NULL AND u.nombre IS NOT NULL AND u.estado = 1 AND lr.estado = 1
),
usuarios_unificados AS (
    SELECT DISTINCT ON (id_usuario) id_usuario, celular, ci, nombre, paterno, materno, correo, t_rol_id_rol, mun_nombre
    FROM usuarios_base ORDER BY id_usuario, mun_nombre
),
celular_unique AS (
    SELECT DISTINCT ON (celular) id_usuario, celular, ci, nombre, paterno, materno, correo, t_rol_id_rol, mun_nombre
    FROM usuarios_unificados ORDER BY celular, id_usuario
),
ci_con_duplicados AS (
    SELECT ci FROM celular_unique GROUP BY ci HAVING count(*) > 1
),
-- Evitar duplicados en shared.municipio por nombre
municipio_unique AS (
    SELECT DISTINCT ON (lower(nombre)) id, nombre, id_provincia, id_departamento
    FROM shared.municipio
    ORDER BY lower(nombre), id
),
usuarios_mapeados AS (
    SELECT DISTINCT ON (cu.id_usuario)
        cu.id_usuario as id_legacy,
        cu.celular,
        CASE WHEN cd.ci IS NOT NULL THEN cu.celular || '-SINB' ELSE cu.ci || '-SINB' END as carnet,
        trim(concat_ws(' ', cu.nombre, cu.paterno, cu.materno)) as nombre_completo,
        cu.correo,
        CASE cu.t_rol_id_rol WHEN 1 THEN 2 WHEN 2 THEN 6 WHEN 3 THEN 12 WHEN 4 THEN 13 END as id_rol,
        mu.id as id_municipio,
        mu.id_provincia,
        mu.id_departamento
    FROM celular_unique cu
    LEFT JOIN municipio_unique mu ON lower(mu.nombre) = lower(cu.mun_nombre)
    LEFT JOIN ci_con_duplicados cd ON cd.ci = cu.ci
)
SELECT * FROM usuarios_mapeados;

-- Verificar unicidad
SELECT 'Temp rows' as info, count(*) FROM tmp_usuarios_sinb;
SELECT 'Unique celular' as info, count(DISTINCT celular) FROM tmp_usuarios_sinb;
SELECT 'Unique carnet' as info, count(DISTINCT carnet) FROM tmp_usuarios_sinb;

-- Insertar a usuarios.usuario
INSERT INTO usuarios.usuario (usuario, contrasena, nombre, celular, carnet, id_rol, id_municipio, id_provincia, id_departamento, activo, correo)
SELECT celular, carnet, nombre_completo, celular, carnet, id_rol, id_municipio, id_provincia, id_departamento, true, NULLIF(correo, '')
FROM tmp_usuarios_sinb
WHERE id_rol IS NOT NULL
ON CONFLICT (usuario) DO UPDATE SET
    contrasena = EXCLUDED.contrasena,
    nombre = EXCLUDED.nombre,
    id_rol = EXCLUDED.id_rol,
    id_municipio = EXCLUDED.id_municipio,
    id_provincia = EXCLUDED.id_provincia,
    id_departamento = EXCLUDED.id_departamento,
    activo = EXCLUDED.activo,
    correo = EXCLUDED.correo;

SELECT 'Usuarios migrados' as concepto, count(*) FROM usuarios.usuario WHERE id_rol IN (2, 6, 12, 13);
