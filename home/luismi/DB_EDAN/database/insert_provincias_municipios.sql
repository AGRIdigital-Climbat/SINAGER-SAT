-- =============================================================================
-- INSERT DEPARTAMENTOS, PROVINCIAS Y MUNICIPIOS DE BOLIVIA
-- Sistema EDAN - Codificacion INE
-- Formato INE: DD (departamento) | DDPP (provincia) | DDPPMM (municipio)
-- =============================================================================

-- Departamentos
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('01', 'Chuquisaca') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('02', 'La Paz') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('03', 'Cochabamba') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('04', 'Oruro') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('05', 'Potosi') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('06', 'Tarija') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('07', 'Santa Cruz') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('08', 'Beni') ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_departamento (codigo_ine, nombre) VALUES ('09', 'Pando') ON CONFLICT (codigo_ine) DO NOTHING;

-- =============================================================================
-- 01 - CHUQUISACA
-- =============================================================================

INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0101', id_departamento, 'Oropeza' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0102', id_departamento, 'Belisario Boeto' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0103', id_departamento, 'Hernando Siles' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0104', id_departamento, 'Jaime Zudanez' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0105', id_departamento, 'Cornelio Saavedra' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0106', id_departamento, 'Valencia' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0107', id_departamento, 'Yamparaez' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0108', id_departamento, 'Azurduy' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_provincia (codigo_ine, id_departamento, nombre) SELECT '0109', id_departamento, 'Luis Calvo' FROM catalogo_departamento WHERE codigo_ine = '01' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Oropeza (0101)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010101', d.id_departamento, p.id_provincia, 'Sucre' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0101' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010102', d.id_departamento, p.id_provincia, 'Yotala' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0101' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010103', d.id_departamento, p.id_provincia, 'Poroma' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0101' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Belisario Boeto (0102)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010201', d.id_departamento, p.id_provincia, 'Villa Serrano' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0102' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Hernando Siles (0103)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010301', d.id_departamento, p.id_provincia, 'Monteagudo' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0103' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010302', d.id_departamento, p.id_provincia, 'El Villar' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0103' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Jaime Zudanez (0104)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010401', d.id_departamento, p.id_provincia, 'Zudanez' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0104' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010402', d.id_departamento, p.id_provincia, 'Presto' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0104' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010403', d.id_departamento, p.id_provincia, 'Villa Mojocoyas' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0104' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Cornelio Saavedra (0105)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010501', d.id_departamento, p.id_provincia, 'Betanzos' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0105' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010502', d.id_departamento, p.id_provincia, 'Ayopaya' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0105' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010503', d.id_departamento, p.id_provincia, 'Chaqui' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0105' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010504', d.id_departamento, p.id_provincia, 'Anzaldo' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0105' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Valencia (0106)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010601', d.id_departamento, p.id_provincia, 'Caranday' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0106' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010602', d.id_departamento, p.id_provincia, 'Sopachuy' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0106' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010603', d.id_departamento, p.id_provincia, 'Ravelo' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0106' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010604', d.id_departamento, p.id_provincia, 'Toroa' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0106' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Yamparaez (0107)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010701', d.id_departamento, p.id_provincia, 'Tarabuco' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0107' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010702', d.id_departamento, p.id_provincia, 'Pampamarca' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0107' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010703', d.id_departamento, p.id_provincia, 'Yamparaez' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0107' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010704', d.id_departamento, p.id_provincia, 'Huacareta' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0107' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Azurduy (0108)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010801', d.id_departamento, p.id_provincia, 'Azurduy' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0108' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010802', d.id_departamento, p.id_provincia, 'Tarvita' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0108' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010803', d.id_departamento, p.id_provincia, 'Villa de Villazon' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0108' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010804', d.id_departamento, p.id_provincia, 'Las Carreras' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0108' ON CONFLICT (codigo_ine) DO NOTHING;

-- Municipios de Luis Calvo (0109)
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010901', d.id_departamento, p.id_provincia, 'Villa Viscarra' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0109' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010902', d.id_departamento, p.id_provincia, 'Culpina' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0109' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010903', d.id_departamento, p.id_provincia, 'San Pablo' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0109' ON CONFLICT (codigo_ine) DO NOTHING;
INSERT INTO catalogo_municipio (codigo_ine, id_departamento, id_provincia, nombre) SELECT '010904', d.id_departamento, p.id_provincia, 'El Pueblito' FROM catalogo_departamento d JOIN catalogo_provincia p ON d.id_departamento = p.id_departamento WHERE d.codigo_ine = '01' AND p.codigo_ine = '0109' ON CONFLICT (codigo_ine) DO NOTHING;
