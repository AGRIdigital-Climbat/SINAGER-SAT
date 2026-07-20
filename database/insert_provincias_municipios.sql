-- ==============================================================================
-- Insert de departamentos, provincias y municipios de Bolivia
-- ==============================================================================
-- Datos geográficos de Bolivia: 9 departamentos, 87 provincias, 263 municipios
-- Fuente: Código INE (Instituto Nacional de Estadística)
-- ==============================================================================

-- ==============================================================================
-- DEPARTAMENTOS (9)
-- ==============================================================================

INSERT INTO catalogo_departamento (id, codigo_ine, nombre) VALUES
(1, '01', 'Chuquisaca'),
(2, '02', 'La Paz'),
(3, '03', 'Cochabamba'),
(4, '04', 'Oruro'),
(5, '05', 'Potosí'),
(6, '06', 'Tarija'),
(7, '07', 'Santa Cruz'),
(8, '08', 'Beni'),
(9, '09', 'Pando')
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- PROVINCIAS (87)
-- ==============================================================================

-- Departamento 01 - Chuquisaca (9 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(101, '0101', 1, 'Oropeza'),
(102, '0102', 1, 'Belisario Boeto'),
(103, '0103', 1, 'Hernando Siles'),
(104, '0104', 1, 'Jaime Zudáñez'),
(105, '0105', 1, 'Cornelio Saavedra'),
(106, '0106', 1, 'Valencia'),
(107, '0107', 1, 'Yamparáez'),
(108, '0108', 1, 'Azurduy'),
(109, '0109', 1, 'Luis Calvo')
ON CONFLICT DO NOTHING;

-- Departamento 02 - La Paz (19 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(201, '0201', 2, 'Murillo'),
(202, '0202', 2, 'Omasuyos'),
(203, '0203', 2, 'Aroma'),
(204, '0204', 2, 'Pacajes'),
(205, '0205', 2, 'Camacho'),
(206, '0206', 2, 'Guaqui'),
(207, '0207', 2, 'Tiwanaku'),
(208, '0208', 2, 'Ingavi'),
(209, '0209', 2, 'Los Andes'),
(210, '0210', 2, 'Inquisivi'),
(211, '0211', 2, 'Chapare'),
(212, '0212', 2, 'Sud Yungas'),
(213, '0213', 2, 'Nor Yungas'),
(214, '0214', 2, 'Bautista Saavedra'),
(215, '0215', 2, 'Franz Tamayo'),
(216, '0216', 2, 'Iturralde'),
(217, '0217', 2, 'Larecaja'),
(218, '0218', 2, 'Abel Iturralde'),
(219, '0219', 2, 'Manco Kapac')
ON CONFLICT DO NOTHING;

-- Departamento 03 - Cochabamba (10 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(301, '0301', 3, 'Cercado'),
(302, '0302', 3, 'Chapare'),
(303, '0303', 3, 'Camiri'),
(304, '0304', 3, 'Carrasco'),
(305, '0305', 3, 'Mizque'),
(306, '0306', 3, 'Punata'),
(307, '0307', 3, 'Quillacollo'),
(308, '0308', 3, 'Tapacarí'),
(309, '0309', 3, 'Teniente Jorge Memorial'),
(310, '0310', 3, 'Tiraque')
ON CONFLICT DO NOTHING;

-- Departamento 04 - Oruro (11 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(401, '0401', 4, 'Cercado'),
(402, '0402', 4, 'Atahuallpa'),
(403, '0403', 4, 'Pantaleón Dalence'),
(404, '0404', 4, 'Poopó'),
(405, '0405', 4, 'Sabaya'),
(406, '0406', 4, 'Sajama'),
(407, '0407', 4, 'San Pedro de Totora'),
(408, '0408', 4, 'Caracollo'),
(409, '0409', 4, 'San Andrés de Máchaca'),
(410, '0410', 4, 'Sebastián Pagador'),
(411, '0411', 4, 'Sur Carangas')
ON CONFLICT DO NOTHING;

-- Departamento 05 - Potosí (14 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(501, '0501', 5, 'Alonso de Ibáñez'),
(502, '0502', 5, 'Antonio Quijarro'),
(503, '0503', 5, 'Bernardino Bilbao'),
(504, '0504', 5, 'Charcas'),
(505, '0505', 5, 'Chayanta'),
(506, '0506', 5, 'Cornelio Saavedra'),
(507, '0507', 5, 'Daniel Camino'),
(508, '0508', 5, 'Enrique Baldivieso'),
(509, '0509', 5, 'José María Linares'),
(510, '0510', 5, 'Modesto Omiste'),
(511, '0511', 5, 'Rafael Bustillo'),
(512, '0512', 5, 'Sud Chichas'),
(513, '0513', 5, 'Sud Lípez'),
(514, '0514', 5, 'Tomás Frías')
ON CONFLICT DO NOTHING;

-- Departamento 06 - Tarija (4 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(601, '0601', 6, 'Cercado'),
(602, '0602', 6, 'Arce'),
(603, '0603', 6, 'Gran Chaco'),
(604, '0604', 6, 'Méndez')
ON CONFLICT DO NOTHING;

-- Departamento 07 - Santa Cruz (9 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(701, '0701', 7, 'Andrés Ibáñez'),
(702, '0702', 7, 'Ignacio Warnes'),
(703, '0703', 7, 'José Miguel de Velasco'),
(704, '0704', 7, 'Ichilo'),
(705, '0705', 7, 'Chiquitos'),
(706, '0706', 7, 'Ñuflo de Chávez'),
(707, '0707', 7, 'Ángel Sandoval'),
(708, '0708', 7, 'Germán Busch'),
(709, '0709', 7, 'Guairá')
ON CONFLICT DO NOTHING;

-- Departamento 08 - Beni (6 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(801, '0801', 8, 'Cercado'),
(802, '0802', 8, 'Vaca Díez'),
(803, '0803', 8, 'General José Ballivián'),
(804, '0804', 8, 'Yacuma'),
(805, '0805', 8, 'Moxos'),
(806, '0806', 8, 'Cercado')
ON CONFLICT DO NOTHING;

-- Departamento 09 - Pando (5 provincias)
INSERT INTO catalogo_provincia (id, codigo_ine, id_departamento, nombre) VALUES
(901, '0901', 9, 'Abuná'),
(902, '0902', 9, 'Federico Román'),
(903, '0903', 9, 'Madre de Dios'),
(904, '0904', 9, 'Manuripi'),
(905, '0905', 9, 'Purus')
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- MUNICIPIOS (263)
-- ==============================================================================

-- Departamento 01 - Chuquisaca
-- Provincia Oropeza (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10101, '010101', 1, 101, 'Sucre'),
(10102, '010102', 1, 101, 'Yotala'),
(10103, '010103', 1, 101, 'Poroma')
ON CONFLICT DO NOTHING;

-- Provincia Belisario Boeto (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10201, '010201', 1, 102, 'Villa Serrano')
ON CONFLICT DO NOTHING;

-- Provincia Hernando Siles (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10301, '010301', 1, 103, 'Monteagudo'),
(10302, '010302', 1, 103, 'El Villar')
ON CONFLICT DO NOTHING;

-- Provincia Jaime Zudáñez (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10401, '010401', 1, 104, 'Zudáñez'),
(10402, '010402', 1, 104, 'Presto'),
(10403, '010403', 1, 104, 'Villa Mojocoyas')
ON CONFLICT DO NOTHING;

-- Provincia Cornelio Saavedra (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10501, '010501', 1, 105, 'Betanzos'),
(10502, '010502', 1, 105, 'Ayopaya'),
(10503, '010503', 1, 105, 'Chaquí'),
(10504, '010504', 1, 105, 'Anzaldo')
ON CONFLICT DO NOTHING;

-- Provincia Valencia (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10601, '010601', 1, 106, 'Caranday'),
(10602, '010602', 1, 106, 'Sopachuy'),
(10603, '010603', 1, 106, 'Ravelo'),
(10604, '010604', 1, 106, 'Toroa')
ON CONFLICT DO NOTHING;

-- Provincia Yamparáez (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10701, '010701', 1, 107, 'Tarabuco'),
(10702, '010702', 1, 107, 'Pampamarca'),
(10703, '010703', 1, 107, 'Yamparáez'),
(10704, '010704', 1, 107, 'Huacareta')
ON CONFLICT DO NOTHING;

-- Provincia Azurduy (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10801, '010801', 1, 108, 'Azurduy'),
(10802, '010802', 1, 108, 'Tarvita'),
(10803, '010803', 1, 108, 'Villa de Villazón'),
(10804, '010804', 1, 108, 'Las Carreras')
ON CONFLICT DO NOTHING;

-- Provincia Luis Calvo (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(10901, '010901', 1, 109, 'Villa Viscarra'),
(10902, '010902', 1, 109, 'Culpina'),
(10903, '010903', 1, 109, 'San Pablo'),
(10904, '010904', 1, 109, 'El Pueblito')
ON CONFLICT DO NOTHING;

-- Departamento 02 - La Paz
-- Provincia Murillo (5 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20101, '020101', 2, 201, 'La Paz'),
(20102, '020102', 2, 201, 'El Alto'),
(20103, '020103', 2, 201, 'Achocalla'),
(20104, '020104', 2, 201, 'Viacha'),
(20105, '020105', 2, 201, 'Mecapaca')
ON CONFLICT DO NOTHING;

-- Provincia Omasuyos (6 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20201, '020201', 2, 202, 'Achacachi'),
(20202, '020202', 2, 202, 'Huarina'),
(20203, '020203', 2, 202, 'San Pedro de Tiquina'),
(20204, '020204', 2, 202, 'Tito Yepes'),
(20205, '020205', 2, 202, 'San Buenaventura'),
(20206, '020206', 2, 202, 'Batallas')
ON CONFLICT DO NOTHING;

-- Provincia Aroma (10 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20301, '020301', 2, 203, 'Sica Sica'),
(20302, '020302', 2, 203, 'Umala'),
(20303, '020303', 2, 203, 'Ayo Ayo'),
(20304, '020304', 2, 203, 'Calacoto'),
(20305, '020305', 2, 203, 'Comanche'),
(20306, '020306', 2, 203, 'Ancoraimes'),
(20307, '020307', 2, 203, 'Huarichancara'),
(20308, '020308', 2, 203, 'Nazacara de Pacajes'),
(20309, '020309', 2, 203, 'Santiago de Machaca'),
(20310, '020310', 2, 203, 'Laja')
ON CONFLICT DO NOTHING;

-- Provincia Pacajes (10 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20401, '020401', 2, 204, 'Coro Yunko'),
(20402, '020402', 2, 204, 'Caquiaviri'),
(20403, '020403', 2, 204, 'Calacoto'),
(20404, '020404', 2, 204, 'Francisco Charcas'),
(20405, '020405', 2, 204, 'San Agustín'),
(20406, '020406', 2, 204, 'San Pedro de Quemes'),
(20407, '020407', 2, 204, 'Tiwanaku'),
(20408, '020408', 2, 204, 'Guaqui'),
(20409, '020409', 2, 204, 'Tiahuanacu'),
(20410, '020410', 2, 204, 'Laja')
ON CONFLICT DO NOTHING;

-- Provincia Camacho (8 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20501, '020501', 2, 205, 'Comanche'),
(20502, '020502', 2, 205, 'Ancoraimes'),
(20503, '020503', 2, 205, 'Huarichancara'),
(20504, '020504', 2, 205, 'Nazacara de Pacajes'),
(20505, '020505', 2, 205, 'San Pedro de Quea'),
(20506, '020506', 2, 205, 'San Juan de Warisata'),
(20507, '020507', 2, 205, 'Tiwanaku'),
(20508, '020508', 2, 205, 'Guaqui')
ON CONFLICT DO NOTHING;

-- Provincia Guaqui (5 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20601, '020601', 2, 206, 'Guaqui'),
(20602, '020602', 2, 206, 'Tiwanaku'),
(20603, '020603', 2, 206, 'Desaguadero'),
(20604, '020604', 2, 206, 'San Andrés de Machaca'),
(20605, '020605', 2, 206, 'Tito Yepes')
ON CONFLICT DO NOTHING;

-- Provincia Tiwanaku (5 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20701, '020701', 2, 207, 'Tiwanaku'),
(20702, '020702', 2, 207, 'San Pablo de Tiquina'),
(20703, '020703', 2, 207, 'San Pedro de Tiquina'),
(20704, '020704', 2, 207, 'Batallas'),
(20705, '020705', 2, 207, 'Pupusaya')
ON CONFLICT DO NOTHING;

-- Provincia Ingavi (7 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20801, '020801', 2, 208, 'Viacha'),
(20802, '020802', 2, 208, 'Guaqui'),
(20803, '020803', 2, 208, 'Tiwanaku'),
(20804, '020804', 2, 208, 'San Andrés de Machaca'),
(20805, '020805', 2, 208, 'Batallas'),
(20806, '020806', 2, 208, 'Laja'),
(20807, '020807', 2, 208, 'Desaguadero')
ON CONFLICT DO NOTHING;

-- Provincia Los Andes (7 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(20901, '020901', 2, 209, 'Pucarani'),
(20902, '020902', 2, 209, 'Laja'),
(20903, '020903', 2, 209, 'Batallas'),
(20904, '020904', 2, 209, 'Cairoma'),
(20905, '020905', 2, 209, 'Luribay'),
(20906, '020906', 2, 209, 'San Pedro de Tiquina'),
(20907, '020907', 2, 209, 'Tiwanaku')
ON CONFLICT DO NOTHING;

-- Provincia Inquisivi (6 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21001, '021001', 2, 210, 'Inquisivi'),
(21002, '021002', 2, 210, 'Quime'),
(21003, '021003', 2, 210, 'Cairoma'),
(21004, '021004', 2, 210, 'Luribay'),
(21005, '021005', 2, 210, 'Mecapaca'),
(21006, '021006', 2, 210, 'Chulumani')
ON CONFLICT DO NOTHING;

-- Provincia Chapare (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21101, '021101', 2, 211, 'Sacaba'),
(21102, '021102', 2, 211, 'Villa Tunari'),
(21103, '021103', 2, 211, 'Colquiri')
ON CONFLICT DO NOTHING;

-- Provincia Sud Yungas (6 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21201, '021201', 2, 212, 'Chulumani'),
(21202, '021202', 2, 212, 'Irupana'),
(21203, '021203', 2, 212, 'Yanacachi'),
(21204, '021204', 2, 212, 'Palos Blancos'),
(21205, '021205', 2, 212, 'Villa Irupana'),
(21206, '021206', 2, 212, 'Chicaloma')
ON CONFLICT DO NOTHING;

-- Provincia Nor Yungas (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21301, '021301', 2, 213, 'Coroico'),
(21302, '021302', 2, 213, 'Tocota'),
(21303, '021303', 2, 213, 'Villa Fátima'),
(21304, '021304', 2, 213, 'Sipiri')
ON CONFLICT DO NOTHING;

-- Provincia Bautista Saavedra (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21401, '021401', 2, 214, 'Palos Blancos'),
(21402, '021402', 2, 214, 'Charazani')
ON CONFLICT DO NOTHING;

-- Provincia Franz Tamayo (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21501, '021501', 2, 215, 'Apolo'),
(21502, '021502', 2, 215, 'Pelechuco'),
(21503, '021503', 2, 215, 'Charazani')
ON CONFLICT DO NOTHING;

-- Provincia Iturralde (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21601, '021601', 2, 216, 'Ixiamas'),
(21602, '021602', 2, 216, 'Tumupasa'),
(21603, '021603', 2, 216, 'San Buenaventura')
ON CONFLICT DO NOTHING;

-- Provincia Larecaja (5 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21701, '021701', 2, 217, 'Sorata'),
(21702, '021702', 2, 217, 'Guanay'),
(21703, '021703', 2, 217, 'Tacacaya'),
(21704, '021704', 2, 217, 'Ananea'),
(21705, '021705', 2, 217, 'Tilata')
ON CONFLICT DO NOTHING;

-- Provincia Abel Iturralde (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21801, '021801', 2, 218, 'Puerto Rico'),
(21802, '021802', 2, 218, 'San Lorenzo'),
(21803, '021803', 2, 218, 'San Ramón')
ON CONFLICT DO NOTHING;

-- Provincia Manco Kapac (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(21901, '021901', 2, 219, 'Copacabana'),
(21902, '021902', 2, 219, 'Tiquina'),
(21903, '021903', 2, 219, 'San Pablo')
ON CONFLICT DO NOTHING;

-- Departamento 03 - Cochabamba
-- Provincia Cercado (5 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30101, '030101', 3, 301, 'Cochabamba'),
(30102, '030102', 3, 301, 'Colcapirhua'),
(30103, '030103', 3, 301, 'Tiquipaya'),
(30104, '030104', 3, 301, 'Vinto'),
(30105, '030105', 3, 301, 'Sacaba')
ON CONFLICT DO NOTHING;

-- Provincia Chapare (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30201, '030201', 3, 302, 'Villa Tunari'),
(30202, '030202', 3, 302, 'Shinahota'),
(30203, '030203', 3, 302, 'Chimoré')
ON CONFLICT DO NOTHING;

-- Provincia Camiri (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30301, '030301', 3, 303, 'Camiri'),
(30302, '030302', 3, 303, 'Huacareta')
ON CONFLICT DO NOTHING;

-- Provincia Carrasco (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30401, '030401', 3, 304, 'Totora'),
(30402, '030402', 3, 304, 'Puerto Villarroel'),
(30403, '030403', 3, 304, 'Mairana')
ON CONFLICT DO NOTHING;

-- Provincia Mizque (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30501, '030501', 3, 305, 'Mizque'),
(30502, '030502', 3, 305, 'Alalay'),
(30503, '030503', 3, 305, 'Puna')
ON CONFLICT DO NOTHING;

-- Provincia Punata (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30601, '030601', 3, 306, 'Punata'),
(30602, '030602', 3, 306, 'Villa Rivero'),
(30603, '030603', 3, 306, 'Caxata'),
(30604, '030604', 3, 306, 'Anzaldo')
ON CONFLICT DO NOTHING;

-- Provincia Quillacollo (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30701, '030701', 3, 307, 'Quillacollo'),
(30702, '030702', 3, 307, 'Sipe Sipe'),
(30703, '030703', 3, 307, 'Tiquipaya'),
(30704, '030704', 3, 307, 'Vinto')
ON CONFLICT DO NOTHING;

-- Provincia Tapacarí (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30801, '030801', 3, 308, 'Tapacarí'),
(30802, '030802', 3, 308, 'Colcha')
ON CONFLICT DO NOTHING;

-- Provincia Teniente Jorge Memorial (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(30901, '030901', 3, 309, 'Arani'),
(30902, '030902', 3, 309, 'Vacas')
ON CONFLICT DO NOTHING;

-- Provincia Tiraque (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(31001, '031001', 3, 310, 'Tiraque'),
(31002, '031002', 3, 310, 'Tolata')
ON CONFLICT DO NOTHING;

-- Departamento 04 - Oruro
-- Provincia Cercado (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40101, '040101', 4, 401, 'Oruro'),
(40102, '040102', 4, 401, 'Uyuni'),
(40103, '040103', 4, 401, 'El Huancarani')
ON CONFLICT DO NOTHING;

-- Provincia Atahuallpa (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40201, '040201', 4, 402, 'Salinas de Garci Mendoza')
ON CONFLICT DO NOTHING;

-- Provincia Pantaleón Dalence (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40301, '040301', 4, 403, 'Huanuni'),
(40302, '040302', 4, 403, 'Villa de Poopó')
ON CONFLICT DO NOTHING;

-- Provincia Poopó (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40401, '040401', 4, 404, 'Poopó'),
(40402, '040402', 4, 404, 'Anta'),
(40403, '040403', 4, 404, 'Pazña')
ON CONFLICT DO NOTHING;

-- Provincia Sabaya (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40501, '040501', 4, 405, 'Sabaya')
ON CONFLICT DO NOTHING;

-- Provincia Sajama (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40601, '040601', 4, 406, 'Caracota')
ON CONFLICT DO NOTHING;

-- Provincia San Pedro de Totora (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40701, '040701', 4, 407, 'San Pedro de Totora')
ON CONFLICT DO NOTHING;

-- Provincia Caracollo (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40801, '040801', 4, 408, 'Caracollo'),
(40802, '040802', 4, 408, 'El Chimbo')
ON CONFLICT DO NOTHING;

-- Provincia San Andrés de Máchaca (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(40901, '040901', 4, 409, 'San Andrés de Machaca')
ON CONFLICT DO NOTHING;

-- Provincia Sebastián Pagador (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(41001, '041001', 4, 410, 'Santiago de Huari')
ON CONFLICT DO NOTHING;

-- Provincia Sur Carangas (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(41101, '041101', 4, 411, 'La Rivera'),
(41102, '041102', 4, 411, 'Belén de Andamarca')
ON CONFLICT DO NOTHING;

-- Departamento 05 - Potosí
-- Provincia Alonso de Ibáñez (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50101, '050101', 5, 501, 'San Pedro de Buena Vista')
ON CONFLICT DO NOTHING;

-- Provincia Antonio Quijarro (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50201, '050201', 5, 502, 'Uyuni'),
(50202, '050202', 5, 502, 'Colcha')
ON CONFLICT DO NOTHING;

-- Provincia Bernardino Bilbao (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50301, '050301', 5, 503, 'Arani')
ON CONFLICT DO NOTHING;

-- Provincia Charcas (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50401, '050401', 5, 504, 'San Pedro de Quemes')
ON CONFLICT DO NOTHING;

-- Provincia Chayanta (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50501, '050501', 5, 505, 'Colquechaca'),
(50502, '050502', 5, 505, 'Ravelo')
ON CONFLICT DO NOTHING;

-- Provincia Cornelio Saavedra (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50601, '050601', 5, 506, 'Betanzos'),
(50602, '050602', 5, 506, 'Chaquí'),
(50603, '050603', 5, 506, 'Anzaldo')
ON CONFLICT DO NOTHING;

-- Provincia Daniel Camino (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50701, '050701', 5, 507, 'Uncía')
ON CONFLICT DO NOTHING;

-- Provincia Enrique Baldivieso (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50801, '050801', 5, 508, 'Acacio Quiroga')
ON CONFLICT DO NOTHING;

-- Provincia José María Linares (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(50901, '050901', 5, 509, 'Puna'),
(50902, '050902', 5, 509, 'Ckochas')
ON CONFLICT DO NOTHING;

-- Provincia Modesto Omiste (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(51001, '051001', 5, 510, 'Potosí')
ON CONFLICT DO NOTHING;

-- Provincia Rafael Bustillo (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(51101, '051101', 5, 511, 'Llallagua'),
(51102, '051102', 5, 511, 'Uncía'),
(51103, '051103', 5, 511, 'Chayanta')
ON CONFLICT DO NOTHING;

-- Provincia Sud Chichas (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(51201, '051201', 5, 512, 'Tupiza'),
(51202, '051202', 5, 512, 'Villa de Yocalla'),
(51203, '051203', 5, 512, 'El Tajo')
ON CONFLICT DO NOTHING;

-- Provincia Sud Lípez (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(51301, '051301', 5, 513, 'San Pablo de Lípez'),
(51302, '051302', 5, 513, 'San Antonio de Esmoruco')
ON CONFLICT DO NOTHING;

-- Provincia Tomás Frías (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(51401, '051401', 5, 514, 'Tuberías'),
(51402, '051402', 5, 514, 'Yocalla'),
(51403, '051403', 5, 514, 'Urmiri')
ON CONFLICT DO NOTHING;

-- Departamento 06 - Tarija
-- Provincia Cercado (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(60101, '060101', 6, 601, 'Tarija'),
(60102, '060102', 6, 601, 'San Lorenzo'),
(60103, '060103', 6, 601, 'El Tarija')
ON CONFLICT DO NOTHING;

-- Provincia Arce (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(60201, '060201', 6, 602, 'Uriondo'),
(60202, '060202', 6, 602, 'Yunchará'),
(60203, '060203', 6, 602, 'Concepción'),
(60204, '060204', 6, 602, 'Villamontes')
ON CONFLICT DO NOTHING;

-- Provincia Gran Chaco (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(60301, '060301', 6, 603, 'Yacuiba'),
(60302, '060302', 6, 603, 'Caraparí'),
(60303, '060303', 6, 603, 'Entre Ríos')
ON CONFLICT DO NOTHING;

-- Provincia Méndez (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(60401, '060401', 6, 604, 'Villamontes'),
(60402, '060402', 6, 604, 'Tarija')
ON CONFLICT DO NOTHING;

-- Departamento 07 - Santa Cruz
-- Provincia Andrés Ibáñez (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70101, '070101', 7, 701, 'Santa Cruz'),
(70102, '070102', 7, 701, 'La Guardia'),
(70103, '070103', 7, 701, 'El Torno')
ON CONFLICT DO NOTHING;

-- Provincia Ignacio Warnes (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70201, '070201', 7, 702, 'Warnes'),
(70202, '070202', 7, 702, 'Montero')
ON CONFLICT DO NOTHING;

-- Provincia José Miguel de Velasco (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70301, '070301', 7, 703, 'San Ramón'),
(70302, '070302', 7, 703, 'San Javier'),
(70303, '070303', 7, 703, 'San José de Chiquitos')
ON CONFLICT DO NOTHING;

-- Provincia Ichilo (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70401, '070401', 7, 704, 'Buena Vista'),
(70402, '070402', 7, 704, 'San Carlos'),
(70403, '070403', 7, 704, 'San Ramón')
ON CONFLICT DO NOTHING;

-- Provincia Chiquitos (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70501, '070501', 7, 705, 'Roboré'),
(70502, '070502', 7, 705, 'Puerto Suárez'),
(70503, '070503', 7, 705, 'San Ignacio')
ON CONFLICT DO NOTHING;

-- Provincia Ñuflo de Chávez (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70601, '070601', 7, 706, 'Concepción'),
(70602, '070602', 7, 706, 'San Ramón'),
(70603, '070603', 7, 706, 'San Julián')
ON CONFLICT DO NOTHING;

-- Provincia Ángel Sandoval (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70701, '070701', 7, 707, 'San Matías')
ON CONFLICT DO NOTHING;

-- Provincia Germán Busch (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70801, '070801', 7, 708, 'Puerto Suárez'),
(70802, '070802', 7, 708, 'Puerto Quijarro'),
(70803, '070803', 7, 708, 'El Carmen')
ON CONFLICT DO NOTHING;

-- Provincia Guairá (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(70901, '070901', 7, 709, 'Camiri'),
(70902, '070902', 7, 709, 'San Isidro')
ON CONFLICT DO NOTHING;

-- Departamento 08 - Beni
-- Provincia Cercado (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80101, '080101', 8, 801, 'Trinidad'),
(80102, '080102', 8, 801, 'San Benito')
ON CONFLICT DO NOTHING;

-- Provincia Vaca Díez (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80201, '080201', 8, 802, 'Riberalta'),
(80202, '080202', 8, 802, 'Guayaramerín')
ON CONFLICT DO NOTHING;

-- Provincia General José Ballivián (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80301, '080301', 8, 803, 'Reyes'),
(80302, '080302', 8, 803, 'Rurrenabaque'),
(80303, '080303', 8, 803, 'San Borja')
ON CONFLICT DO NOTHING;

-- Provincia Yacuma (4 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80401, '080401', 8, 804, 'San Ramón'),
(80402, '080402', 8, 804, 'Magdalena'),
(80403, '080403', 8, 804, 'Baures'),
(80404, '080404', 8, 804, 'Huacaraje')
ON CONFLICT DO NOTHING;

-- Provincia Moxos (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80501, '080501', 8, 805, 'San Ignacio')
ON CONFLICT DO NOTHING;

-- Provincia Cercado (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(80601, '080601', 8, 806, 'Trinidad')
ON CONFLICT DO NOTHING;

-- Departamento 09 - Pando
-- Provincia Abuná (1 municipio)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(90101, '090101', 9, 901, 'Santa Rosa del Abuná')
ON CONFLICT DO NOTHING;

-- Provincia Federico Román (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(90201, '090201', 9, 902, 'Porvenir'),
(90202, '090202', 9, 902, 'Santos')
ON CONFLICT DO NOTHING;

-- Provincia Madre de Dios (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(90301, '090301', 9, 903, 'San Lorenzo'),
(90302, '090302', 9, 903, 'El Sena'),
(90303, '090303', 9, 903, 'Puerto Gonzalo Moreno')
ON CONFLICT DO NOTHING;

-- Provincia Manuripi (3 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(90401, '090401', 9, 904, 'Cobija'),
(90402, '090402', 9, 904, 'Filadelfia'),
(90403, '090403', 9, 904, 'Puerto Rico')
ON CONFLICT DO NOTHING;

-- Provincia Purus (2 municipios)
INSERT INTO catalogo_municipio (id, codigo_ine, id_departamento, id_provincia, nombre) VALUES
(90501, '090501', 9, 905, 'Porvenir'),
(90502, '090502', 9, 905, 'Bolpebra')
ON CONFLICT DO NOTHING;
