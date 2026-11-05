BEGIN;

CREATE TABLE usuarios.accion (
    id_accion SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL
);

INSERT INTO usuarios.accion (codigo, nombre) VALUES
    ('CREATE', 'Agregar registro'),
    ('READ',   'Ver/Consultar'),
    ('UPDATE', 'Editar'),
    ('DELETE', 'Eliminar');

INSERT INTO usuarios.aplicacion (codigo, nombre, descripcion) VALUES
    ('REA',    'Reportes de Eventos Adversos', 'Modulo REA - Reportes de Eventos Adversos'),
    ('SISTEMA', 'Administracion del Sistema',  'Gestion de usuarios, roles, configuraciones')
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE usuarios.permiso (
    id_permiso    SERIAL PRIMARY KEY,
    id_rol        INTEGER NOT NULL REFERENCES usuarios.rol(id_rol),
    id_aplicacion INTEGER NOT NULL REFERENCES usuarios.aplicacion(id_aplicacion),
    id_accion     INTEGER NOT NULL REFERENCES usuarios.accion(id_accion),
    UNIQUE (id_rol, id_aplicacion, id_accion)
);

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT pa.id_rol, pa.id_aplicacion, ac.id_accion
FROM usuarios.permiso_aplicacion pa
CROSS JOIN usuarios.accion ac
WHERE ac.codigo IN ('CREATE', 'READ', 'UPDATE');

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT pa.id_rol, pa.id_aplicacion, ac.id_accion
FROM usuarios.permiso_aplicacion pa
CROSS JOIN usuarios.accion ac
WHERE ac.codigo = 'DELETE' AND pa.id_rol IN (1, 2);

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT p.id_rol, a_rea.id_aplicacion, p.id_accion
FROM usuarios.permiso p
JOIN usuarios.aplicacion a_edan ON a_edan.codigo = 'EDAN'
JOIN usuarios.aplicacion a_rea  ON a_rea.codigo  = 'REA'
WHERE p.id_aplicacion = a_edan.id_aplicacion
  AND NOT EXISTS (
      SELECT 1 FROM usuarios.permiso p2
      WHERE p2.id_rol = p.id_rol
        AND p2.id_aplicacion = a_rea.id_aplicacion
        AND p2.id_accion = p.id_accion
  );

INSERT INTO usuarios.permiso (id_rol, id_aplicacion, id_accion)
SELECT r.id_rol, a_sis.id_aplicacion, ac.id_accion
FROM usuarios.rol r
CROSS JOIN usuarios.aplicacion a_sis
CROSS JOIN usuarios.accion ac
WHERE r.id_rol IN (1, 2) AND a_sis.codigo = 'SISTEMA';

COMMIT;
