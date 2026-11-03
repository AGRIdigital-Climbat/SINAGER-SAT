-- v2.44.0: usuarios.sesion.token de varchar(255) a text
--
-- Motivo: el JWT firmado incluye jti/usuario/rol; con usuarios largos
-- (columna usuarios.usuario permite 100 caracteres) el token supera los 255
-- caracteres, el INSERT revienta con "value too long for type character
-- varying(255)" y el login responde 500. Ampliar a text elimina el techo.
-- Cambio 100% compatible (ampliación, no relleno).

ALTER TABLE usuarios.sesion
    ALTER COLUMN token TYPE text;

COMMENT ON COLUMN usuarios.sesion.token IS
    'JWT completo emitido en cada login (uno por sesión/dispositivo; nunca se reutiliza)';
