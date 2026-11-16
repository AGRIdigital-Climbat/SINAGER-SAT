# Informe: casos extremos de `personas_por_hogar` en unidades Censo 2024

> **Alcance:** unidades (manzanos y comunidades) con `hogares > 0` y razón  
> `(personas / hogares) > 20` (umbral acordado).  
> **Fecha de extracción:** 2026-11-15 (BD de prueba)  
> **Fuente:** `shared.manzanos` / `shared.comunidades` + `cambios_replicacion/datos/ficha.parquet` (INE CPV-2024)

## 1. Resumen

- **Total casos:** 106 (79 manzanos, 27 comunidades)
- **Rango:** 20.33 – 362.73 pers/hogar (redondeado: 20 – 363)
- **Decisión (API):** en acceso directo/listados por unidad se **mantiene el valor real**; en `GET /censo/manzanos/por-nombre`, si el `personas_por_hogar` del grupo > 20 se reemplaza por el **promedio oficial del municipio** (`ROUND(población total municipio / hogares_ine municipio)`).

## 2. Explicación (por qué aparecen)

- `hogares` = viviendas **particulares ocupadas con personas presentes** (`viv_tipo_presentes` = suma `hogar_*`), según ficha INE.
- `personas` = **población total** censada en la unidad (incluye población en **viviendas colectivas**: cuarteles, cárceles, internados, hospitales, residencias, campamentos, etc., y otros residentes).
- Por ello `personas/hogares` puede ser muy alto en unidades con población colectiva relevante (p.ej. 921 pers. / 12 hogares = 77; 5441/15=363). **No representa “77 personas por familia”**; es un artefacto de mezclar población total con hogares particulares.
- El cálculo es aritméticamente correcto respecto a las fuentes cargadas; el problema es la **interpretación** del ratio a nivel de unidad.

## 3. Resumen por departamento

| Departamento | Total | Manzanos | Comunidades |
|---|---:|---:|---:|
| Beni | 6 | 2 | 4 |
| Chuquisaca | 5 | 5 | 0 |
| Cochabamba | 17 | 17 | 0 |
| La Paz | 25 | 21 | 4 |
| Oruro | 3 | 3 | 0 |
| Pando | 4 | 3 | 1 |
| Potosí | 6 | 5 | 1 |
| Santa Cruz | 35 | 18 | 17 |
| Tarija | 5 | 5 | 0 |
| **Total** | **106** | **79** | **27** |

## 4. Detalle completo (106 casos)

Columnas ficha: `v_pres`=viv_tipo_presentes, `v_part`=particular, `v_col`=colectiva, `v_aus`=ausentes, `v_des`=desocupada.

| # | Tipo | Código INE | Nombre | Departamento | Provincia | Municipio | Personas | Viviendas | Hogares | PPH exacto | PPH | v_pres | v_part | v_col | v_aus | v_des |
|---:|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Manzano | `00629371306-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 5441 | 35 | 15 | 362.73 | **363** | 15 | 33 | 2 | 17 | 1 |
| 2 | Comunidad | `05737268628-D` | VILLA PROGRESO | Santa Cruz | Obispo Santisteban | Fernández Alonso | 340 | 11 | 1 | 340.00 | **340** | 1 | 1 | 10 | 0 | 0 |
| 3 | Manzano | `05242945352-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 879 | 7 | 3 | 293.00 | **293** | 3 | 4 | 3 | 1 | 0 |
| 4 | Manzano | `00599163094-A` | VIACHA | La Paz | Ingavi | Viacha | 220 | 12 | 1 | 220.00 | **220** | 1 | 11 | 1 | 5 | 5 |
| 5 | Manzano | `05247631956-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 645 | 11 | 3 | 215.00 | **215** | 3 | 3 | 8 | 0 | 0 |
| 6 | Manzano | `00626774695-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 774 | 8 | 4 | 193.50 | **194** | 4 | 7 | 1 | 2 | 1 |
| 7 | Manzano | `05464609858-A` | RIO BLANCO | Cochabamba | Carrasco | Entre Ríos | 322 | 9 | 2 | 161.00 | **161** | 2 | 2 | 7 | 0 | 0 |
| 8 | Comunidad | `05912206085-M` | HARDEMAN | Santa Cruz | Obispo Santisteban | San Pedro | 222 | 32 | 2 | 111.00 | **111** | 2 | 19 | 13 | 17 | 0 |
| 9 | Manzano | `00630024831-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 416 | 7 | 4 | 104.00 | **104** | 4 | 5 | 2 | 1 | 0 |
| 10 | Comunidad | `06002000519-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Obispo Santisteban | San Pedro | 97 | 11 | 1 | 97.00 | **97** | 1 | 8 | 3 | 7 | 0 |
| 11 | Manzano | `06101624821-A` | EL ALTO | La Paz | Murillo | El Alto | 531 | 10 | 6 | 88.50 | **89** | 6 | 9 | 1 | 2 | 1 |
| 12 | Comunidad | `06080729562-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Obispo Santisteban | San Pedro | 431 | 16 | 5 | 86.20 | **86** | 5 | 5 | 11 | 0 | 0 |
| 13 | Manzano | `05234567439-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 921 | 24 | 12 | 76.75 | **77** | 12 | 19 | 5 | 4 | 3 |
| 14 | Manzano | `02972539837-A` | TARIJA | Tarija | Cercado | Tarija | 1270 | 24 | 17 | 74.71 | **75** | 17 | 22 | 2 | 5 | 0 |
| 15 | Manzano | `05245280258-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 808 | 13 | 11 | 73.45 | **73** | 11 | 12 | 1 | 1 | 0 |
| 16 | Manzano | `00629971536-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 491 | 8 | 7 | 70.14 | **70** | 7 | 7 | 1 | 0 | 0 |
| 17 | Manzano | `00755700432-A` | TRINIDAD | Beni | Cercado | Trinidad | 210 | 7 | 3 | 70.00 | **70** | 3 | 3 | 4 | 0 | 0 |
| 18 | Manzano | `06643977991-A` | CARANAVI | La Paz | Caranavi | Caranavi | 187 | 19 | 3 | 62.33 | **62** | 3 | 12 | 7 | 8 | 1 |
| 19 | Comunidad | `05778394998-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Ñuflo de Chávez | Cuatro Cañadas | 62 | 15 | 1 | 62.00 | **62** | 1 | 12 | 3 | 11 | 0 |
| 20 | Comunidad | `05812114717-M` | SAGRADO CORAZON | Santa Cruz | Obispo Santisteban | San Pedro | 123 | 17 | 2 | 61.50 | **62** | 2 | 2 | 15 | 0 | 0 |
| 21 | Manzano | `03083554410-A` | PALMAR CHICO | Tarija | Gran Chaco | Yacuiba | 611 | 12 | 10 | 61.10 | **61** | 10 | 10 | 2 | 0 | 0 |
| 22 | Manzano | `05716737446-A` | PUERTO VILLARROEL | Cochabamba | Carrasco | Puerto Villarroel | 120 | 9 | 2 | 60.00 | **60** | 2 | 7 | 2 | 5 | 0 |
| 23 | Manzano | `03361104472-A` | VILLA MONTES | Tarija | Gran Chaco | Villa Montes | 222 | 8 | 4 | 55.50 | **56** | 4 | 6 | 2 | 2 | 0 |
| 24 | Manzano | `00309921506-A` | UYUNI | Potosí | Antonio Quijarro | Uyuni | 110 | 7 | 2 | 55.00 | **55** | 2 | 2 | 5 | 0 | 0 |
| 25 | Manzano | `00629930410-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 1232 | 28 | 23 | 53.57 | **54** | 23 | 27 | 1 | 2 | 2 |
| 26 | Manzano | `00379233377-A` | POTOSI | Potosí | Tomás Frías | Potosí | 105 | 15 | 2 | 52.50 | **53** | 2 | 2 | 13 | 0 | 0 |
| 27 | Manzano | `00476432765-A` | ORURO | Oruro | Cercado | Oruro | 259 | 7 | 5 | 51.80 | **52** | 5 | 5 | 2 | 0 | 0 |
| 28 | Manzano | `01212732073-A` | COBIJA | Pando | Nicolás Suárez | Cobija | 254 | 7 | 5 | 50.80 | **51** | 5 | 6 | 1 | 1 | 0 |
| 29 | Manzano | `03718714307-A` | PISIGA BOLIVAR | Oruro | Sabaya | Sabaya | 197 | 10 | 4 | 49.25 | **49** | 4 | 4 | 6 | 0 | 0 |
| 30 | Manzano | `06079040663-A` | EL ALTO | La Paz | Murillo | El Alto | 1150 | 30 | 24 | 47.92 | **48** | 24 | 29 | 1 | 4 | 1 |
| 31 | Manzano | `07988930812-A` | RURRENABAQUE | Beni | General José Ballivián | Puerto Menor de Rurrenabaque | 239 | 8 | 5 | 47.80 | **48** | 5 | 7 | 1 | 2 | 0 |
| 32 | Comunidad | `08788285861-D` | HACIENDA/FINCA/ESTANCIA | Beni | Mamoré | San Joaquín | 47 | 11 | 1 | 47.00 | **47** | 1 | 1 | 10 | 0 | 0 |
| 33 | Manzano | `00280138484-A` | TUPIZA | Potosí | Sur Chichas | Tupiza | 187 | 9 | 4 | 46.75 | **47** | 4 | 6 | 3 | 2 | 0 |
| 34 | Manzano | `04438359419-A` | CHAYANTA | Potosí | Rafael Bustillo | Chayanta | 322 | 10 | 7 | 46.00 | **46** | 7 | 7 | 3 | 0 | 0 |
| 35 | Comunidad | `08479606434-D` | CACHICHIRA | La Paz | Abel Iturralde | San Buenaventura | 45 | 9 | 1 | 45.00 | **45** | 1 | 9 | 0 | 8 | 0 |
| 36 | Comunidad | `11145655791-D` | TRES ISLAS | Pando | Manuripi | San Pedro | 133 | 12 | 3 | 44.33 | **44** | 3 | 3 | 9 | 0 | 0 |
| 37 | Manzano | `06676639987-A` | ACHACACHI | La Paz | Omasuyos | Achacachi | 261 | 57 | 6 | 43.50 | **44** | 6 | 23 | 34 | 14 | 3 |
| 38 | Manzano | `05222074013-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 679 | 26 | 16 | 42.44 | **42** | 16 | 20 | 6 | 1 | 3 |
| 39 | Manzano | `05255005481-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 253 | 9 | 6 | 42.17 | **42** | 6 | 6 | 3 | 0 | 0 |
| 40 | Manzano | `05234478423-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 1055 | 56 | 26 | 40.58 | **41** | 26 | 42 | 14 | 10 | 6 |
| 41 | Manzano | `05239279666-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 1165 | 60 | 29 | 40.17 | **40** | 29 | 59 | 1 | 9 | 21 |
| 42 | Manzano | `07944505126-A` | APOLO | La Paz | Franz Tamayo | Apolo | 40 | 11 | 1 | 40.00 | **40** | 1 | 1 | 10 | 0 | 0 |
| 43 | Manzano | `00523650772-A` | QUILLACOLLO | Cochabamba | Quillacollo | Quillacollo | 427 | 13 | 11 | 38.82 | **39** | 11 | 12 | 1 | 1 | 0 |
| 44 | Manzano | `06036323442-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 115 | 13 | 3 | 38.33 | **38** | 3 | 8 | 5 | 2 | 3 |
| 45 | Manzano | `05186512947-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 299 | 9 | 8 | 37.38 | **37** | 8 | 8 | 1 | 0 | 0 |
| 46 | Manzano | `05088922341-A` | TARATA | Cochabamba | Esteban Arze | Tarata | 522 | 29 | 14 | 37.29 | **37** | 14 | 25 | 4 | 7 | 4 |
| 47 | Manzano | `05537273574-A` | PUERTO SUAREZ | Santa Cruz | Germán Busch | Puerto Suárez | 182 | 7 | 5 | 36.40 | **36** | 5 | 5 | 2 | 0 | 0 |
| 48 | Comunidad | `07885977780-D` | HACIENDA/FINCA/ESTANCIA | Beni | Cercado | San Javier | 36 | 13 | 1 | 36.00 | **36** | 1 | 1 | 12 | 0 | 0 |
| 49 | Manzano | `02606899148-A` | BERMEJO | Tarija | Arce | Bermejo | 179 | 22 | 5 | 35.80 | **36** | 5 | 18 | 4 | 0 | 13 |
| 50 | Manzano | `05218115594-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 988 | 32 | 28 | 35.29 | **35** | 28 | 29 | 3 | 0 | 1 |
| 51 | Comunidad | `02807370412-M` | RIO GRANDE | Potosí | Nor Lípez | Colcha "K" | 408 | 32 | 12 | 34.00 | **34** | 12 | 20 | 12 | 8 | 0 |
| 52 | Manzano | `05501627126-A` | MONTERO | Santa Cruz | Obispo Santisteban | Montero | 711 | 33 | 21 | 33.86 | **34** | 21 | 31 | 2 | 7 | 3 |
| 53 | Manzano | `03059345050-A` | LA GRAMPA | Tarija | Gran Chaco | Yacuiba | 300 | 20 | 9 | 33.33 | **33** | 9 | 19 | 1 | 10 | 0 |
| 54 | Comunidad | `06186829957-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Obispo Santisteban | San Pedro | 161 | 13 | 5 | 32.20 | **32** | 5 | 8 | 5 | 3 | 0 |
| 55 | Comunidad | `05642303337-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Chiquitos | Pailón | 32 | 10 | 1 | 32.00 | **32** | 1 | 6 | 4 | 5 | 0 |
| 56 | Manzano | `00523424529-A` | QUILLACOLLO | Cochabamba | Quillacollo | Quillacollo | 731 | 32 | 23 | 31.78 | **32** | 23 | 31 | 1 | 3 | 5 |
| 57 | Manzano | `00628343981-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 1080 | 47 | 34 | 31.76 | **32** | 34 | 46 | 1 | 4 | 8 |
| 58 | Manzano | `05386049962-A` | BUENA VISTA | Santa Cruz | Ichilo | Buena Vista | 254 | 10 | 8 | 31.75 | **32** | 8 | 8 | 2 | 0 | 0 |
| 59 | Manzano | `03767515793-A` | BOYUIBE | Santa Cruz | Cordillera | Boyuibe | 249 | 12 | 8 | 31.13 | **31** | 8 | 8 | 4 | 0 | 0 |
| 60 | Manzano | `00540528083-A` | PATACAMAYA | La Paz | Aroma | Patacamaya | 373 | 21 | 12 | 31.08 | **31** | 12 | 20 | 1 | 5 | 3 |
| 61 | Manzano | `05582359065-A` | CHIMORE | Cochabamba | Carrasco | Chimoré | 93 | 10 | 3 | 31.00 | **31** | 3 | 3 | 7 | 0 | 0 |
| 62 | Manzano | `05149409993-A` | PUNATA | Cochabamba | Punata | Punata | 216 | 8 | 7 | 30.86 | **31** | 7 | 7 | 1 | 0 | 0 |
| 63 | Manzano | `03952737494-A` | MONTEAGUDO | Chuquisaca | Hernando Siles | Monteagudo | 154 | 10 | 5 | 30.80 | **31** | 5 | 8 | 2 | 3 | 0 |
| 64 | Manzano | `05570404809-A` | IVIRGARZAMA | Cochabamba | Carrasco | Puerto Villarroel | 246 | 9 | 8 | 30.75 | **31** | 8 | 9 | 0 | 1 | 0 |
| 65 | Manzano | `00377193282-A` | POTOSI | Potosí | Tomás Frías | Potosí | 361 | 18 | 12 | 30.08 | **30** | 12 | 17 | 1 | 5 | 0 |
| 66 | Comunidad | `05346234116-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Andrés Ibáñez | Cotoca | 30 | 7 | 1 | 30.00 | **30** | 1 | 5 | 2 | 4 | 0 |
| 67 | Comunidad | `06443742440-D` | INTERCULTURAL AMOR DE DIOS | La Paz | Nor Yungas | Coripata | 389 | 51 | 13 | 29.92 | **30** | 13 | 50 | 1 | 36 | 1 |
| 68 | Manzano | `00627892927-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 209 | 22 | 7 | 29.86 | **30** | 7 | 18 | 4 | 3 | 8 |
| 69 | Comunidad | `06620106382-D` | COMUNIDAD FLOR DE PUSILLANI | La Paz | Murillo | Nuestra Señora de La Paz | 145 | 57 | 5 | 29.00 | **29** | 5 | 57 | 0 | 52 | 0 |
| 70 | Comunidad | `05979333512-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Ñuflo de Chávez | Concepción | 29 | 16 | 1 | 29.00 | **29** | 1 | 10 | 6 | 8 | 1 |
| 71 | Comunidad | `07908214640-D` | ASOCIACION FAMILIA FELIZ | Beni | General José Ballivián | Puerto Menor de Rurrenabaque | 87 | 14 | 3 | 29.00 | **29** | 3 | 4 | 10 | 0 | 1 |
| 72 | Manzano | `05398430281-A` | WARNES | Santa Cruz | Warnes | Warnes | 57 | 7 | 2 | 28.50 | **29** | 2 | 5 | 2 | 2 | 1 |
| 73 | Manzano | `08839323283-A` | IXIAMAS | La Paz | Abel Iturralde | Ixiamas | 142 | 9 | 5 | 28.40 | **28** | 5 | 8 | 1 | 0 | 3 |
| 74 | Manzano | `00626838376-A` | LA PAZ | La Paz | Murillo | Nuestra Señora de La Paz | 4799 | 221 | 170 | 28.23 | **28** | 170 | 219 | 2 | 39 | 10 |
| 75 | Comunidad | `05604105759-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Ñuflo de Chávez | Cuatro Cañadas | 28 | 9 | 1 | 28.00 | **28** | 1 | 6 | 3 | 5 | 0 |
| 76 | Manzano | `06134853580-A` | EL ALTO | La Paz | Murillo | El Alto | 388 | 18 | 14 | 27.71 | **28** | 14 | 16 | 2 | 0 | 2 |
| 77 | Manzano | `04612844047-A` | CABEZAS | Santa Cruz | Cordillera | Cabezas | 192 | 8 | 7 | 27.43 | **27** | 7 | 7 | 1 | 0 | 0 |
| 78 | Comunidad | `05696623733-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Ñuflo de Chávez | San Julián | 54 | 14 | 2 | 27.00 | **27** | 2 | 2 | 12 | 0 | 0 |
| 79 | Manzano | `04917775093-A` | CURAHUARA DE CARANGAS | Oruro | Sajama | Curahuara de Carangas | 242 | 17 | 9 | 26.89 | **27** | 9 | 16 | 1 | 6 | 1 |
| 80 | Manzano | `06390613851-A` | SAN IGNACIO DE VELASCO | Santa Cruz | Velasco | San Ignacio | 53 | 9 | 2 | 26.50 | **27** | 2 | 5 | 4 | 3 | 0 |
| 81 | Comunidad | `05829460272-M` | LAS PARABAS | Santa Cruz | Obispo Santisteban | Fernández Alonso | 26 | 14 | 1 | 26.00 | **26** | 1 | 8 | 6 | 7 | 0 |
| 82 | Manzano | `05580742898-A` | CHIMORE | Cochabamba | Carrasco | Chimoré | 335 | 17 | 13 | 25.77 | **26** | 13 | 16 | 1 | 2 | 1 |
| 83 | Manzano | `00414854717-A` | SUCRE | Chuquisaca | Oropeza | Sucre | 334 | 14 | 13 | 25.69 | **26** | 13 | 13 | 1 | 0 | 0 |
| 84 | Comunidad | `05180789245-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Chiquitos | Pailón | 51 | 7 | 2 | 25.50 | **26** | 2 | 2 | 5 | 0 | 0 |
| 85 | Manzano | `00523626908-A` | SACABA | Cochabamba | Chapare | Sacaba | 431 | 23 | 17 | 25.35 | **25** | 17 | 22 | 1 | 2 | 3 |
| 86 | Manzano | `12151007766-A` | COBIJA | Pando | Nicolás Suárez | Cobija | 324 | 16 | 13 | 24.92 | **25** | 13 | 13 | 3 | 0 | 0 |
| 87 | Comunidad | `08726897875-D` | FLOR DE PATUJU | La Paz | Abel Iturralde | Ixiamas | 197 | 8 | 8 | 24.63 | **25** | 8 | 8 | 0 | 0 | 0 |
| 88 | Manzano | `03768230433-A` | BOYUIBE | Santa Cruz | Cordillera | Boyuibe | 73 | 7 | 3 | 24.33 | **24** | 3 | 3 | 4 | 0 | 0 |
| 89 | Manzano | `03714497430-A` | CUEVO | Santa Cruz | Cordillera | Cuevo | 286 | 15 | 12 | 23.83 | **24** | 12 | 12 | 3 | 0 | 0 |
| 90 | Manzano | `05827186402-A` | RINCON DEL TIGRE | Santa Cruz | Germán Busch | El Carmen Rivero Tórrez | 71 | 13 | 3 | 23.67 | **24** | 3 | 10 | 3 | 7 | 0 |
| 91 | Manzano | `00418400630-A` | SUCRE | Chuquisaca | Oropeza | Sucre | 164 | 8 | 7 | 23.43 | **23** | 7 | 7 | 1 | 0 | 0 |
| 92 | Manzano | `05240636593-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 90 | 7 | 4 | 22.50 | **23** | 4 | 6 | 1 | 2 | 0 |
| 93 | Manzano | `00419070490-A` | SUCRE | Chuquisaca | Oropeza | Sucre | 223 | 13 | 10 | 22.30 | **22** | 10 | 10 | 3 | 0 | 0 |
| 94 | Manzano | `05297795517-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 22 | 8 | 1 | 22.00 | **22** | 1 | 1 | 7 | 0 | 0 |
| 95 | Manzano | `06529029336-A` | SAN PEDRO DE TIQUINA | La Paz | Manco Kapac | San Pedro de Tiquina | 88 | 11 | 4 | 22.00 | **22** | 4 | 4 | 7 | 0 | 0 |
| 96 | Manzano | `05549132443-A` | PUERTO SUAREZ | Santa Cruz | Germán Busch | Puerto Suárez | 264 | 16 | 12 | 22.00 | **22** | 12 | 14 | 2 | 1 | 1 |
| 97 | Comunidad | `05042784951-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Cordillera | Cabezas | 132 | 12 | 6 | 22.00 | **22** | 6 | 11 | 1 | 3 | 2 |
| 98 | Manzano | `05238199724-A` | COCHABAMBA | Cochabamba | Cercado | Cochabamba | 438 | 29 | 20 | 21.90 | **22** | 20 | 28 | 1 | 4 | 4 |
| 99 | Manzano | `03418966645-A` | HUACA CANCHA | Chuquisaca | Nor Cinti | Camargo | 87 | 13 | 4 | 21.75 | **22** | 4 | 6 | 7 | 2 | 0 |
| 100 | Comunidad | `05840128613-D` | LA ISLA | Santa Cruz | Ñuflo de Chávez | San Julián | 43 | 12 | 2 | 21.50 | **22** | 2 | 11 | 1 | 9 | 0 |
| 101 | Manzano | `01212613854-A` | COBIJA | Pando | Nicolás Suárez | Cobija | 708 | 40 | 33 | 21.45 | **21** | 33 | 39 | 1 | 2 | 4 |
| 102 | Manzano | `05231686604-A` | SANTA CRUZ DE LA SIERRA | Santa Cruz | Andrés Ibáñez | Santa Cruz de la Sierra | 63 | 7 | 3 | 21.00 | **21** | 3 | 3 | 4 | 0 | 0 |
| 103 | Comunidad | `07943196273-D` | HACIENDA/FINCA/ESTANCIA | Beni | Mamoré | San Ramón | 41 | 7 | 2 | 20.50 | **21** | 2 | 3 | 4 | 0 | 1 |
| 104 | Manzano | `06093155029-A` | EL ALTO | La Paz | Murillo | El Alto | 366 | 33 | 18 | 20.33 | **20** | 18 | 32 | 1 | 14 | 0 |
| 105 | Manzano | `06540350635-A` | CHUA COCANI | La Paz | Omasuyos | Chua Cocani | 244 | 16 | 12 | 20.33 | **20** | 12 | 15 | 1 | 3 | 0 |
| 106 | Comunidad | `05813598205-D` | HACIENDA/FINCA/ESTANCIA | Santa Cruz | Chiquitos | San José | 61 | 8 | 3 | 20.33 | **20** | 3 | 3 | 5 | 0 | 0 |

## 5. Notas

- A nivel **municipal/departamental/provincial** el ratio se calcula con `hogares_ine` oficial y población total (promedios 2,83–3,85 por depto); no se ven los extremos de unidad, salvo municipios pequeños donde el agregado también puede elevarse.
- Este informe documenta los casos; **no modifica datos fuente**. Los valores en BD/API (acceso directo) permanecen como los entrega la fuente oficial.
- Ver también: `INSTRUCCIONES.md` (D2, base del ratio) y `ANALISIS_NULLS.md`.
