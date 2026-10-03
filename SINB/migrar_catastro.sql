-- Migración Paso 2: Catálogos (simplificado)
SET statement_timeout = 0;
TRUNCATE sinb.migracion_mapa CASCADE;

-- 1. zona_geografica (3)
INSERT INTO sinb.zona_geografica (id, codigo, nombre, descripcion, estado) SELECT gen_random_uuid(), 'ZG-'||id_zona_geografica::text, zona_geografica, regexp_replace(descripcion, E'[\\r\\n]+', ' ', 'g'), 'ACTIVO' FROM sinb_legacy.t_zona_geografica;
INSERT INTO sinb.migracion_mapa SELECT 'zona_geografica', l.id_zona_geografica, z.id FROM sinb_legacy.t_zona_geografica l JOIN sinb.zona_geografica z ON z.codigo = 'ZG-'||l.id_zona_geografica::text;

-- 2. grupo (7)
INSERT INTO sinb.grupo (id, codigo, nombre, estado) SELECT gen_random_uuid(), 'G-'||id_grupo::text, grupo, 'ACTIVO' FROM sinb_legacy.t_grupo;
INSERT INTO sinb.migracion_mapa SELECT 'grupo', l.id_grupo, g.id FROM sinb_legacy.t_grupo l JOIN sinb.grupo g ON g.codigo = 'G-'||l.id_grupo::text;

-- 3. indicador_natural (77)
INSERT INTO sinb.indicador_natural (id, codigo, nombre_cientifico, id_grupo, estado) SELECT gen_random_uuid(), 'I-'||l.id_indicador_natural::text, l.indicador_natural, m.id_nuevo, 'ACTIVO' FROM sinb_legacy.t_indicador_natural l JOIN sinb_legacy.t_grupo_indicador_natural gi ON gi.fk_t_indicador_natural_id_indicador_natural = l.id_indicador_natural JOIN sinb.migracion_mapa m ON m.tabla_origen='grupo' AND m.id_legacy = gi.fk_t_grupo_id_grupo;
INSERT INTO sinb.migracion_mapa SELECT 'indicador_natural', l.id_indicador_natural, i.id FROM sinb_legacy.t_indicador_natural l JOIN sinb.indicador_natural i ON i.nombre_cientifico = l.indicador_natural AND i.codigo = 'I-'||l.id_indicador_natural::text;

-- 4. caracteristica (188)
INSERT INTO sinb.caracteristica (id, id_indicador_natural, caracteristica, estado) SELECT DISTINCT ON (l.id_caracteristica) gen_random_uuid(), m.id_nuevo, l.caracteristica, 'ACTIVO' FROM sinb_legacy.t_caracteristica l JOIN sinb_legacy.t_indicador_natural_caracteristica ic ON ic.fk_t_caracteristica_id_caracteristica = l.id_caracteristica JOIN sinb.migracion_mapa m ON m.tabla_origen='indicador_natural' AND m.id_legacy = ic.fk_t_indicador_natural_id_indicador_natural;
INSERT INTO sinb.migracion_mapa SELECT DISTINCT ON (l.id_caracteristica) 'caracteristica', l.id_caracteristica, c.id FROM sinb_legacy.t_caracteristica l JOIN sinb.caracteristica c ON c.caracteristica = l.caracteristica;

-- 5. comportamiento (523) - solo id_caracteristica, sin id_grupo (legacy no lo tiene)
INSERT INTO sinb.comportamiento (id, id_caracteristica, comportamiento, estado) SELECT DISTINCT ON (l.id_comportamiento) gen_random_uuid(), m_c.id_nuevo, l.comportamiento, 'ACTIVO' FROM sinb_legacy.t_comportamiento l JOIN sinb_legacy.t_caracteristica_comportamiento cc ON cc.fk_t_comportamiento_id_comportamiento = l.id_comportamiento JOIN sinb.migracion_mapa m_c ON m_c.tabla_origen='caracteristica' AND m_c.id_legacy = cc.fk_t_caracteristica_id_caracteristica;
INSERT INTO sinb.migracion_mapa SELECT DISTINCT ON (l.id_comportamiento) 'comportamiento', l.id_comportamiento, c.id FROM sinb_legacy.t_comportamiento l JOIN sinb.comportamiento c ON c.comportamiento = l.comportamiento;

-- 6. significado (293) - solo id_comportamiento
INSERT INTO sinb.significado (id, id_comportamiento, significado, estado) SELECT DISTINCT ON (l.id_significado) gen_random_uuid(), m_c.id_nuevo, l.significado, 'ACTIVO' FROM sinb_legacy.t_significado l JOIN sinb_legacy.t_comportamiento_significado cs ON cs.fk_t_significado_id_significado = l.id_significado JOIN sinb.migracion_mapa m_c ON m_c.tabla_origen='comportamiento' AND m_c.id_legacy = cs.fk_t_comportamiento_id_comportamiento;
INSERT INTO sinb.migracion_mapa SELECT DISTINCT ON (l.id_significado) 'significado', l.id_significado, s.id FROM sinb_legacy.t_significado l JOIN sinb.significado s ON s.significado = l.significado;

-- 7. campo_pronostico (5)
INSERT INTO sinb.campo_pronostico (id, nombre, tipo, estado) SELECT gen_random_uuid(), pronostico, 'CLIMATICO', 'ACTIVO' FROM sinb_legacy.t_campo_pronosticos;
INSERT INTO sinb.migracion_mapa SELECT 'campo_pronostico', l.id_campo_pronostico, c.id FROM sinb_legacy.t_campo_pronosticos l JOIN sinb.campo_pronostico c ON c.nombre = l.pronostico;

-- 8. escenario (23)
INSERT INTO sinb.escenario (id, id_campo_pronostico, nombre, estado) SELECT gen_random_uuid(), m.id_nuevo, l.escenario, 'ACTIVO' FROM sinb_legacy.t_escenarios l JOIN sinb.migracion_mapa m ON m.tabla_origen='campo_pronostico' AND m.id_legacy = l.campo_pronostico_id;
INSERT INTO sinb.migracion_mapa SELECT DISTINCT ON (l.id_escenario) 'escenario', l.id_escenario, e.id FROM sinb_legacy.t_escenarios l JOIN sinb.escenario e ON e.nombre = l.escenario;

-- 9. categoria_pronostico_temporal (12)
INSERT INTO sinb.categoria_pronostico_temporal (id, nombre, estado) SELECT DISTINCT ON (categoria) gen_random_uuid(), categoria, CASE WHEN estado = 1 THEN 'ACTIVO'::sinb.estado_registro ELSE 'INACTIVO'::sinb.estado_registro END FROM sinb_legacy.t_categorias_pronostico_temporal;
INSERT INTO sinb.migracion_mapa SELECT 'categoria_pronostico_temporal', l.id_categoria_temporal, c.id FROM sinb_legacy.t_categorias_pronostico_temporal l JOIN sinb.categoria_pronostico_temporal c ON c.nombre = l.categoria;

-- 10. dimension_recomendacion (2)
INSERT INTO sinb.dimension_recomendacion (id, codigo, nombre, estado) VALUES (gen_random_uuid(),'REC','Recomendaciones','ACTIVO'), (gen_random_uuid(),'COMP','Comportamientos','ACTIVO');
INSERT INTO sinb.migracion_mapa VALUES ('dimension_recomendacion',1,(SELECT id FROM sinb.dimension_recomendacion WHERE codigo='REC')), ('dimension_recomendacion',2,(SELECT id FROM sinb.dimension_recomendacion WHERE codigo='COMP'));

-- 11. categoria_comportamiento (10)
INSERT INTO sinb.categoria_comportamiento (id, id_dimension, nombre, estado) SELECT gen_random_uuid(), m.id_nuevo, l.comportamiento, l.estado::sinb.estado_registro FROM sinb_legacy.t_comportamientos l JOIN sinb.migracion_mapa m ON m.tabla_origen='dimension_recomendacion' AND m.id_legacy = l.recomendacion_id;
INSERT INTO sinb.migracion_mapa SELECT DISTINCT ON (l.id_comportamiento) 'categoria_comportamiento', l.id_comportamiento, c.id FROM sinb_legacy.t_comportamientos l JOIN sinb.categoria_comportamiento c ON c.nombre = l.comportamiento;

SELECT tabla_origen, count(*) as migrados FROM sinb.migracion_mapa GROUP BY tabla_origen ORDER BY 2 DESC;
