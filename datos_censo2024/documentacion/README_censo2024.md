# Censo 2024 de Bolivia — Unidades censales mínimas, referencias geoespaciales y controles de calidad

> **Documento**: `documentacion/README_censo2024.md` · **Generado**: 10/09/2026
> **Carpeta de trabajo**: `WebSinagersat/datos_censo2024/`
>
> Este documento resume **qué** contienen los archivos, **de dónde** se obtuvo cada dato (con
> enlaces verificables), **cómo** se vinculan los códigos INE y **qué controles** se hicieron
> contra lo publicado por el INE, incluidas las discrepancias encontradas.
>
> **Estructura de la carpeta** (las rutas se escriben relativas a `datos_censo2024/`):
>
> ```
> datos_censo2024/
> ├── documentacion/   → README_censo2024.md (este documento)
> ├── fuentes/         → datos crudos originales descargados (universo, geometrías, microdatos, SDSN)
> ├── procesado/       → tablas derivadas (universos, municipios, resúmenes, comparaciones)
> ├── geo/             → unidades_censo2024.gpkg (3 capas: manzanos, comunidades, municipios)
> ├── graficas/        → análisis visual (nacional, departamentos, municipios) + muestras de datos
> └── scripts/         → código reproducible (descarga → procesamiento → gráficas)
> ```

---

## 1. Objetivo

Construir la base de la **unidad mínima censal del Censo de Población y Vivienda 2024 (CPV-2024)**
de Bolivia con:

- población y viviendas por unidad,
- **código INE** de cada unidad y de su departamento/provincia/municipio,
- nombres de referencia (dep/prov/mun),
- **geometrías** cargables en cualquier SIG (GeoPackage, EPSG:4326),
- controles de calidad contra los **totales oficiales** del INE.

La **unidad mínima** del censo es la *unidad censal*: **manzano** (área amanzanada) y
**comunidad** (área dispersa). Son **268.604 unidades**: **247.429 manzanos + 21.175
comunidades**. Es la resolución geográfica más fina que publica el INE. Este universo de 2024 es
exacto: la suma de su población cuadra al habitante con los microdatos oficiales (sección 7).

---

## 2. Terminología (estándar del INE)

Para evitar ambigüedades entre fuentes, esta carpeta usa los **términos del INE**. La regla
general: **los nombres de columnas de los archivos crudos se mantienen tal cual salen de la
fuente INE**. Documentamos explícitamente qué viene del INE y qué adecuamos en nuestras tablas
derivadas.

### 2.1 Glosario (término estándar del INE → campo)

| Término del INE | Uso en estos datos | Nota |
|---|---|---|
| **Unidad censal** | la fila de `unidades_censo2024.csv` y de las capas `manzanos`/`comunidades` | menor nivel de desagregación que publica el INE |
| **Manzano** | `tipo_unidad = "Manzano"` (y `area = 1`, cartográfica) | unidad de área amanzanada (urbana en cartografía) |
| **Comunidad** | `tipo_unidad = "Comunidad"` (y `area = 2`, cartográfica) | unidad de área dispersa (rural en cartografía) |
| **Población censada (personas)** | columna **`personas`** | la fuente cruda la llama `personas`; en publicaciones el INE dice "población censada". Se mantiene `personas` **fiel a la fuente** |
| **Viviendas** | columna `viviendas` | el INE publica "viviendas particulares con personas presentes" (4.480.201) |
| **Área urbana/rural oficial** | columna `area_oficial` (valores `Urbana`/`Rural`/`Mixto`) | clasificación **oficial** del INE por municipio, tomada de la variable `area` de los **microdatos** (son los únicos datos que llegan a nivel municipio). **Es la que hay que usar para reportar urbano/rural** (ver §8) |
| **Departamento/Provincia/Municipio** | `idep`/`iprov`/`imun` y `codigo_departamento`/`codigo_provincia`/`codigo_municipio` | códigos jerárquicos del INE (ver §3) |
| **Ficha (indicadores)** | `ficha` (booleano) | el INE publica ficha de 150.744 unidades (ver §10) |
| **TIOC** | (no viene en esta base) | nivel oficial paralelo; solo dep/prov/mun están disponibles |

### 2.2 Qué viene del INE y qué adecuamos

| Campo | Origen | Decisión |
|---|---|---|
| `codigo`, `area`, `idep`, `iprov`, `imun`, `nombre`, `personas`, `viviendas`, `ficha` | **INE tal cual** (geoportal / censosbo) | se conserva el nombre original sin cambios |
| `tipo_unidad` | nuestro (derivado de `area`) | la fuente no trae el tipo como texto; lo etiquetamos **"Manzano"/"Comunidad"** con la denominación estándar del INE (antes decía "Manzano (urbano)"/"Comunidad (rural)"). El matiz urbano/rural lo da `area` |
| `area_oficial` (`Urbana`/`Rural`/`Mixto`) | nuestro (agrega la variable `area` de los **microdatos oficiales** por municipio) | no existe en el geoportal (microdatos no llegan a comunidad/manzano); etiquetas nuestras sobre clasificación del INE |
| `codigo_departamento/provincia/municipio` | nuestro (concatenación `idep\│iprov\│imun`) | alias con nombres más claros de los códigos INE |
| `lat`, `lon` | nuestro (centroide del manzano / punto de comunidad) | calculado desde las geometrías |
| `poblacion_urbana_oficial` / `poblacion_rural_oficial` | agregación de los **microdatos INE** | misma denominación "poblacion" que ya usa `resumen_municipios.csv` |

---

## 3. Estructura jerárquica y códigos INE

Los códigos territoriales **sí son jerárquicos** desde el municipio hacia arriba:

| Nivel | Campo | Longitud | Ejemplo |
|---|---|---|---|
| Departamento | `idep` | 2 | `07` (Santa Cruz) |
| Provincia | `iprov` (dentro del dep.) | 2 | `07` (Cordillera) |
| Municipio | `imun` (dentro de la prov.) | 2 | `05` |
| **Código municipio** | `idep\|iprov\|imun` | 6 | `70705` |
| **Código provincia** | `idep\|iprov` | 4 | `0707` |

Para unir una unidad a su lugar usá siempre la concatenación `idep|iprov|imun` — **nunca** `imun`
solo (se repite entre provincias).

| Nivel | Nº de entidades | Observación |
|---|---|---|
| Departamentos | 9 | códigos 01–09 |
| Provincias | 113 | |
| Municipios | **343** | la lista de 343 incluye 4 TIOC (ver §11) |
| **Unidades mínimas** | **268.604** | 247.429 manzanos + 21.175 comunidades |

**Código de la unidad mínima**: la columna `codigo` (ej. `04121212556-D`) **no es jerárquica**:
el INE la genera matemáticamente desde las coordenadas. El sufijo indica el tipo: `-A` = manzano,
`-D`/`-M` = comunidad. Para ubicar la unidad en su territorio se usan las columnas desnormalizadas
`idep/iprov/imun` y `codigo_departamento/codigo_provincia/codigo_municipio` que ya trae el dato.

Los **microdatos** llegan solo hasta **municipio** (343): `i00` es el identificador de
vivienda/hogar, **no** un código de lugar, y la comunidad/manzano **no aparece** en microdatos
(reserva estadística). La unidad mínima solo existe en el **geoportal**.

---

## 4. Fuentes de los datos (con respaldo)

### 4.1 Universo de unidades y fichas — Geoportal INE vía `censosbo`

El INE publica en su [geoportal](https://geoportal.ine.gob.bo/) las *fichas resumen* de cada
unidad censal y sus geometrías. El paquete [censosbo](https://github.com/lab-tecnosocial/censosbo)
([sitio oficial](https://lab-tecnosocial.github.io/censosbo/)) de Lab TecnoSocial las expone en
arreglos accesibles; los datos se descargaron del *release* **`data-fichas-v1.0.0`**:

- **Página del release**: https://github.com/lab-tecnosocial/censosbo/releases/tag/data-fichas-v1.0.0
- **`unidad.parquet`** (268.604 unidades) — https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/unidad.parquet
- **`geo_manzano_dep01..09.parquet`** (polígonos de manzanos, 247.429) — https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/geo_manzano_depXX.parquet
- **`geo_comunidad.parquet`** (puntos de comunidades, 21.175) — https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/geo_comunidad.parquet
- **`ficha.parquet`** (194 indicadores, 150.744 unidades con ficha) y su diccionario — https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0/ficha.parquet y `.../diccionario_fichas_v1.parquet`

> El release declara como origen el geoportal oficial del INE (`https://geoportal.ine.gob.bo/`) y
> que el INE no publica ficha de unidades con poca población por **reserva estadística** (queda
> fuera el 47% de los manzanos, pero las fichas cubren el 92% de la población / 90% de viviendas).

### 4.2 Microdatos (personas) — INE, base REDATAM/CSV

- Descarga oficial del INE: https://cpv2024.ine.gob.bo/index.php/principal/descargas/ · catálogo ANDA: https://anda.ine.gob.bo/index.php/catalog/132
- Espejo en Parquet del mismo `censosbo`, *release* **`data-v1.0.0`**: https://github.com/lab-tecnosocial/censosbo/releases/tag/data-v1.0.0
- Archivos: `persona_dep01.parquet` … `persona_dep09.parquet` (~283 MB) — https://github.com/lab-tecnosocial/censosbo/releases/download/data-v1.0.0/persona_depXX.parquet

Se usaron para los **controles** (sección 7) y para la columna **`area_oficial`** (sección 8).

### 4.3 Límites municipales (polígonos) — SDSN Bolivia (2026)

La capa de **343 municipios** proviene de **SDSN Bolivia**, «Límites Municipales Bolivia 2025»
(actualizada a 2026):

- Página del dataset: https://sdsnbolivia.org/datos-espaciales/
- Ficha oficial (PDF) con la descripción y metadatos: https://sdsnbolivia.org/wp-content/uploads/2026/04/Ficha-Limites-municipales.pdf
  - **Evidencia del "QR"**: el acceso a los datos en esa ficha está dentro de un **QR** embebido
    en el PDF. Se extrajo su enlace programáticamente (anotación `/URI` del PDF):
    **https://drive.google.com/drive/folders/1_S6VTI6uUrGgGXVbSCSXY_41VxNn-5cq**
  - Dentro de esa carpeta de Google Drive está el archivo **`SDSN_Límites_Municipales_Bolivia_2026.zip`**
    (9,3 MB; shapefile con 343 polígonos), descargado con `gdown`.
- Copia local de respaldo en `fuentes/limites_municipales_sdsn2025/` (shapefile + ficha PDF).

**Respaldo de calidad del shapefile**: 343/343 municipios, proyección original *WGS 1984 Bolivia
Lambert Conformal Conic* (reproyectada a **EPSG:4326**); `Pob_2012` suma **10.059.856**
(= resultado oficial 2012) y `Pob_2024` suma 11.364.933 (ver detalle en §10). Incluye el TIOC de
Raqaypampa. La ficha advierte que persisten conflictos limítrofes a nivel nacional.

### 4.4 Resultados oficiales (para el control) — INE

- Página de resultados de población: https://cpv2024.ine.gob.bo/index.php/resultados/resultados-demografia-demografia/resultados-demografia-poblacion/
- Nota "Bolivia se consolida como país de centros urbanos" (**7.846.708 urbanos / 69 %** y
  **3.518.625 rurales / 31 %**, 02/09/2025): https://cpv2024.ine.gob.bo/index.php/censo-2024-bolivia-se-consolida-como-pais-de-centros-urbanos/
- Nota de presentación de resultados finales (**11.365.333**; 5.682.835 mujeres / 5.682.498 hombres, 28/08/2025): https://cpv2024.ine.gob.bo/index.php/ine-presenta-resultados-del-censo-2024-que-muestran-la-transformacion-demografica-y-avances-sociales-en-bolivia/
- Publicaciones/boletines 2025 (documento nacional, metodología): https://cpv2024.ine.gob.bo/index.php/principal/publicaciones-final-2025/

---

## 5. Archivos descargados (originales, en `fuentes/`)

| Archivo | Contenido | Tamaño |
|---|---|---|
| `fuentes/unidad.parquet` | 268.604 unidades (`codigo, area, idep, iprov, imun, nombre, personas, viviendas, ficha`) | ~2,3 MB |
| `fuentes/geo_comunidad.parquet` | geometrías (puntos) de las 21.175 comunidades | 609 KB |
| `fuentes/geometria_manzanos/geo_manzano_dep01..09.parquet` | polígonos de los 247.429 manzanos por departamento | 24 MB |
| `fuentes/municipios.csv` | 343 municipios (`codigo_ine` + nombres) — diccionario REDATAM vía `censosbo` | — |
| `fuentes/personas/persona_dep01..09.parquet` | microdatos de personas por departamento (control + `area_oficial`) | 283 MB |
| `fuentes/limites_municipales_sdsn2025/` | shapefile de 343 municipios (SDSN 2026) + **ficha PDF con el QR** | 12 MB |

---

## 6. Archivos generados (en `procesado/` y `geo/`)

| Archivo | Filas | Contenido |
|---|---|---|
| `procesado/unidades_censo2024.csv` | 268.604 | universo completo (manzanos + comunidades), 19 columnas |
| `procesado/manzanos_censo2024.csv` | 247.429 | solo manzanos (área 1) |
| `procesado/comunidades_censo2024.csv` | 21.175 | solo comunidades (área 2) |
| `procesado/municipios_censo2024.csv` | 343 | municipios con geometría equivalente en GPKG |
| `procesado/provincias_2024.csv` | 113 | códigos de provincia |
| `procesado/relacion_comunidad_provincia.csv` | 21.175 | cruce comunidad → dep/prov/mun |
| `procesado/resumen_municipios.csv` | 343 | población y nº de unidades por municipio (cartográfico **y** oficial) |
| `procesado/area_oficial_municipios.csv` | 343 | desglose urbano/rural **oficial** (microdatos INE) por municipio |
| `procesado/comparacion_departamentos_censo2024.csv` | 9 | control geoportal vs microdatos por departamento y área (índice 1:1) |
| `geo/unidades_censo2024.gpkg` | **3 capas** | `manzanos` (MultiPolygon) · `comunidades` (Point) · `municipios` (MultiPolygon), EPSG:4326 (~155 MB) |

**Columnas de las tablas de unidades**: `codigo`, `nombre`, `tipo_unidad` (*Manzano* /
*Comunidad*; la fuente no trae el tipo como texto, lo etiquetamos con la denominación del INE, ver §2.2),
`area` (1=urbana, 2=rural; **cartográfica**), **`area_oficial`**
(*Urbana* / *Rural* / *Mixto*; **clasificación oficial del INE**, sección 8), `personas` (la fuente
la llama así; en publicaciones el INE dice "población censada", ver §2.1),
`viviendas`, `ficha`, `idep`, `iprov`, `imun`, `codigo_departamento`, `codigo_provincia`,
`codigo_municipio`, `nombre_dep`, `nombre_prov`, `nombre_mun`, `lat`, `lon` (comunidades = punto;
manzanos = centroide calculado).

---

## 7. Controles de calidad frente a lo publicado por el INE

### 7.1 Total nacional — ✅ cuadra exacto

| Concepto | Nuestros datos (geoportal) | Publicado INE | Diferencia |
|---|---|---|---|
| Población | 11.365.333 | 11.365.333 | **0** |
| Viviendas | 4.480.201 | 4.480.201 | **0** |

### 7.2 Por departamento — ✅ cuadra en los 9 (diferencia 0)

| Dep. | Población (nuestro geoportal) | Población (microdatos INE) | Diferencia |
|---|---|---|---|
| 01 Chuquisaca | 606.027 | 606.027 | 0 |
| 02 La Paz | 3.030.917 | 3.030.917 | 0 |
| 03 Cochabamba | 2.016.357 | 2.016.357 | 0 |
| 04 Oruro | 571.471 | 571.471 | 0 |
| 05 Potosí | 861.292 | 861.292 | 0 |
| 06 Tarija | 534.210 | 534.210 | 0 |
| 07 Santa Cruz | 3.122.605 | 3.122.605 | 0 |
| 08 Beni | 488.260 | 488.260 | 0 |
| 09 Pando | 134.194 | 134.194 | 0 |
| **Total** | **11.365.333** | **11.365.333** | **0** |

### 7.3 Cobertura territorial

- 343/343 municipios con unidades asignadas (0 sin geocodificar).
- Todas las unidades (268.604) se vinculan a un departamento, provincia y municipio.

---

## 8. ⚠️ Discrepancia urbano/rural (y la columna `area_oficial`)

La división **manzano ⇔ comunidad** es **cartográfica** (tipo de unidad). La división
**urbano ⇔ rural oficial** del INE usa la variable `area` de los **microdatos**, y **no son
equivalentes**:

| Área | Geoportal (manzano/comunidad) | Microdatos INE (oficial) | Diferencia |
|---|---|---|---|
| Urbana | 8.830.113 | **7.846.708** | +983.405 |
| Rural | 2.535.220 | **3.518.625** | −983.405 |
| **Total** | 11.365.333 | 11.365.333 | 0 |

El INE reporta oficialmente **7.846.708 urbanos (69 %) y 3.518.625 rurales (31 %)** («7 de cada 10
bolivianos viven en áreas urbanas») — [nota oficial del INE de 02/09/2025](https://cpv2024.ine.gob.bo/index.php/censo-2024-bolivia-se-consolida-como-pais-de-centros-urbanos/).
Es decir, **~983 mil personas viven en manzanos (cartografía) que el INE clasifica como área
rural** en su base final.

**Consecuencia práctica**: los `tipo_unidad`/`area` describen la **cartografía**; para reportar
*área* como el INE hay que usar `area_oficial` (de los microdatos). Por eso se añadió a todas las
tablas y capas la columna **`area_oficial`**, **sin reemplazar** la clasificación cartográfica:

| `area_oficial` | Significado |
|---|---|
| `Urbana` | el municipio figura 100 % urbano en los microdatos |
| `Rural` | el municipio figura 100 % rural en los microdatos |
| `Mixto` | el municipio tiene población oficial urbana **y** rural (no se puede asignar la unidad a un área oficial con seguridad) |

Resultado sobre los 343 municipios (tablas `area_oficial_municipios.csv`,
`resumen_municipios.csv`): **184 municipios mixtos, 158 100 % rurales y 1 100 % urbano
(Colcapirhua)**. Sobre las 268.604 unidades, contando también la cartografía:

| Tipo de unidad (cartográfico) | `area_oficial = Mixto` | `area_oficial = Rural` | `area_oficial = Urbana` |
|---|---|---|---|
| Manzano (`area = 1`) | 218.498 | 28.024 | 907 |
| Comunidad (`area = 2`) | 13.233 | 7.942 | 0 |
| **Total** | **231.731** | **35.966** | **907** |

### ¿Qué usamos y por qué?

**Decisión: todo reporte de *urbano/rural* usa la clasificación oficial INE de los microdatos**
(`area_oficial` y `poblacion_*_oficial`); la cartografía de manzanos/comunidades (`area` /
`tipo_unidad`) se usa **solo** para describir unidades y geometrías. No se confunden ambos sentidos
en este documento ni en las gráficas.

**Por qué usamos la oficial de microdatos** (y no la cartográfica de manzano/comunidad):

1. **Es la fuente que el propio INE usa en sus resultados publicados**: los totales urbanos/rurales
   de la [nota oficial del INE del 02/09/2025](https://cpv2024.ine.gob.bo/index.php/censo-2024-bolivia-se-consolida-como-pais-de-centros-urbanos/)
   (**7.846.708 urbanos / 3.518.625 rurales**) son exactamente los que abre la variable `area` de
   los microdatos. Nuestro cruce (`comparacion_departamentos_censo2024.csv`) da **diferencia 0 en
   los 9 departamentos** contra esa fuente, lo que respalda que reproducimos la clasificación
   oficial con fidelidad.
2. **Manzano/comunidad no es urbano/rural**: la cartografía del geoportal divide por *tipo de
   unidad* (área amanzanada vs dispersa), no por área estadística. Hay ~983 mil personas en
   manzanos que el INE clasifica como rurales (amanzanamiento disperso típico de pueblos rurales),
   y casos extremos que lo demuestran (Colcapirhua, abajo: 100 % manzanos y aun así 100 % urbano
   oficial; o los 158 municipios etiquetados "100 % rural" que sí tienen 28.024 manzanos). Es decir,
   dependiendo del municipio, la clasificación cartográfica puede coincidir o invertir la oficial.
3. **Respaldo documental**: el geoportal del INE no expone la variable `area` a nivel unidad (los
   microdatos llegan solo a municipio, §3). La única vía reproducible de la clasificación oficial
   completa (municipio por municipio) es la variable `area` de los microdatos; por eso `area_oficial`
   es **por municipio** (etiquetas `Urbana`/`Rural`/`Mixto`) y no por unidad.

En resumen: para **reportar** → `area_oficial` (INE, microdatos, fiel a lo publicado); para
**cartografíar/contar unidades** → `area` y `tipo_unidad`. Ambas se conservan en tablas y capas.

### 🔍 Hallazgo destacado: Colcapirhua

**Colcapirhua** (Cochabamba, código **30.905**) es el **único municipio 100 % urbano** del país en
la clasificación oficial: **907 manzanos, 66.505 habitantes, 0 comunidades** (100 % de su
cartografía es amanzanada) y `area_oficial = Urbana` en los microdatos. Este caso demuestra que la
conservación de ambas clasificaciones es necesaria: un resumen hecho solo con *comunidades* daría
342 municipios (Colcapirhua no tiene comunidades), y un reporte hecho solo con cartografía lo
clasificaría rural por sí no tener la etiqueta municipal correcta. Es una **particularidad de la
codificación del INE** que se documenta para no malinterpretar el cruce cartografía × área
oficial.

### Diferencia por departamento (urbana: manzanos − microdatos)

| Dep. | Manzanos − Urbana oficial | Comunidades − Rural oficial |
|---|---|---|
| 01 | +65.872 | −65.872 |
| 02 | +244.828 | −244.828 |
| 03 | +180.514 | −180.514 |
| 04 | +86.650 | −86.650 |
| 05 | +117.696 | −117.696 |
| 06 | +42.491 | −42.491 |
| 07 | +204.034 | −204.034 |
| 08 | +22.592 | −22.592 |
| 09 | +18.728 | −18.728 |

### A nivel municipio: dónde y en qué magnitud difiere

La diferencia es **por municipio** (no por un solo término): 321 municipios clasifican más población
urbana que la oficial (población en manzanos que el INE cuenta rural), 8 clasifican menos (−) y 14
dan exactamente 0. Los 10 municipios con mayor desajuste positivo (población urbana cartográfica −
oficial):

| Municipio | Dep. | Urbana cartográfica − oficial |
|---|---|---|
| Villa Tunari | 03 | +23.345 |
| San Ignacio | 07 | +16.767 |
| Puerto Villarroel | 03 | +14.106 |
| Sipesipe | 03 | +14.103 |
| Warnes | 07 | +12.542 |
| Mecapaca | 02 | +12.350 |
| Cotoca | 07 | +11.264 |
| Yacuiba | 06 | +11.181 |
| San Lorenzo | 06 | +11.045 |
| San Julián | 07 | +10.161 |

Son amanzanamientos (pueblos/colonias) que la cartografía etiqueta "manzano" pero que el INE
clasifica como rurales en su base final. Los municipios con desajuste negativo son Puerto Menor de
Rurrenabaque 08, San Ramón 07, Oruro 04, Villa Abecia 01, Exaltación 08, Colpa Bélgica 07, Pasorapa
03 y Reyes 08 (todos con desajuste ≤ 454 personas). El detalle completo por municipio está en
`area_oficial_municipios.csv` y `resumen_municipios.csv`, y en la gráfica
`graficas/municipios/11_top_municipios_desajuste_manzano_oficial_rural.png`.

---

## 9. Cómo se reprodujo (resumen de los pasos)

1. **Universo y geometrías**: descarga directa de los *assets* del release `data-fichas-v1.0.0`
   (§4.1) → geodataframes de manzanos (Unión de 9 departamentos) y comunidades.
2. **Códigos INE**: se construyeron `codigo_departamento` (idep), `codigo_provincia` (idep|iprov)
   y `codigo_municipio` (idep|iprov|imun) con unión a `fuentes/municipios.csv` (343).
3. **CSV de universos** (`unidades/manzanos/comunidades_censo2024.csv`).
4. **GeoPackage**: capas manzanos y comunidades en EPSG:4326; centroides de manzanos calculados
   reproyectando a ESRI:102033. **Capa de municipios** agregada desde el shapefile de SDSN (§4.3),
   reproyectado a EPSG:4326. Capas: `manzanos`, `comunidades`, `municipios`.
5. **Controles**: suma de `personas`/`viviendas` del universo vs microdatos vía
   `fuentes/personas/persona_dep*.parquet` → `procesado/comparacion_departamentos_censo2024.csv`
   (diferencias 0 en los 9 departamentos).
6. **`area_oficial`**: agregación de la variable `area` de los microdatos a nivel municipio
   → `procesado/area_oficial_municipios.csv` y columnas `area_oficial` en tablas y capas.
7. **Terminología**: se alinearon las etiquetas al estándar del INE (`tipo_unidad` = Manzano /
    Comunidad, columnas `poblacion_*_oficial`); ver §2.
8. **Gráficas y muestras**: `graficas/` con análisis visual (nacional, departamentos, municipios)
   y muestras de datos en `graficas/ejemplos/` (unidades, resumen municipal y área oficial).
9. **Todo reproducible**: el proceso completo está en `scripts/` (`config.py`,
   `01_descargar_fuentes.py`, `02_procesar_universo.py`, `03_generar_graficas.py`). Nota de
   reproducción: los microdatos traen `idep/iprov/imun` como **string** — convertirlos a entero
   antes de concatenar (o concatenar de forma numérica), de lo contrario la operación multiplica
   la cadena y agota la memoria (OOM). Para leer los parquets con geometrías no usar
   `geopandas.read_file` (falla por `libduckdb.so`); leer con `pandas.read_parquet` +
   `GeoSeries.from_wkb`.

---

## 10. Notas, advertencias y limitaciones

- **Viviendas**: el universo oficial son 4.480.201. La tabla REDATAM trae 4.490.488 registros; la
  diferencia (10.287) son personas censadas en la calle / en tránsito (`v01_tipoviv` 15/16), que
  no son viviendas y el geoportal ya excluye.
- **Límites municipales (SDSN)**: `Pob_2024` del shapefile suma **11.364.933**, 400 menos que el
  oficial 11.365.333; se usó **solo la geometría** (y `poblacion_2012` como referencia). La ficha
  advierte de conflictos limítrofes a nivel nacional.
- **TIOC / AIOC**: nivel oficial paralelo de desagregación; no viene en esta base de unidades
  (solo dep/prov/mun). Para agrupar por TIOC hace falta una tabla puente TIOC↔municipio.
- **Barrios / zonas**: no son un nivel oficial; el nivel urbano más fino es el **manzano**.
- **`ficha=True`**: el INE publica ficha de 131.801 manzanos y 18.943 comunidades (150.744;
  cubre 92 % de la población y 90 % de las viviendas; fuera quedan unidades chicas por reserva
  estadística).
- **`resumen_municipios.csv`**: `poblacion_urbana`/`poblacion_rural` son cartográficas;
  `poblacion_urbana_oficial`/`poblacion_rural_oficial` y `area_oficial` son la clasificación
  oficial del INE (según §8, son estas las que se usan para reportar urbano/rural). Colcapirhua
  aparece con `area_oficial = Urbana`, y es el único municipio 100 % urbano del país (ver §8).
- **Página de resultados del INE**: es una SPA (JS); la comparación documental se hizo contra los
  **microdatos oficiales** y las **notas de prensa del INE** (§4.4), no contra tablas que la
  página no expone de forma extractable.

---

## 11. Cómo usar

### 11.1 Archivos finales a usar (los que se consumen en el análisis)

| Archivo | Qué es | Cuándo usarlo |
|---|---|---|
| `geo/unidades_censo2024.gpkg` | **Producto geoespacial final** (3 capas: `manzanos`, `comunidades`, `municipios`, EPSG:4326) | cualquier uso en SIG / mapas |
| `procesado/unidades_censo2024.csv` | **Tabla maestra**: las 268.604 unidades con códigos, nombres, `personas`, `viviendas`, `area`, `area_oficial` | análisis tabular a nivel unidad |
| `procesado/manzanos_censo2024.csv` / `comunidades_censo2024.csv` | subconjuntos de la tabla maestra por tipo de unidad | filtrar por manzanos o comunidades |
| `procesado/municipios_censo2024.csv` | 343 municipios (código + nombres) | listado/relación municipal |
| `procesado/resumen_municipios.csv` | población, nº de unidades y área (cartográfica **y** oficial) por municipio | agrupar/analizar por municipio |
| `procesado/area_oficial_municipios.csv` | desglose **oficial** urbano/rural por municipio (microdatos INE) | reportar área según clasificación del INE |
| `graficas/` (PNG) + `graficas/ejemplos/` (CSV) | análisis visual nacional/departamento/municipio y muestras de datos con los términos usados | divulgación/revisión rápida de los resultados (§8) |

**Nota**: `procesado/comparacion_departamentos_censo2024.csv`, `provincias_2024.csv` y
`relacion_comunidad_provincia.csv` son **auxiliares** (control y soporte), no de uso directo.

- **SIG**: abrir `geo/unidades_censo2024.gpkg` — capas **`manzanos`**, **`comunidades`** y
  **`municipios`**, todas EPSG:4326.
- **Vincular**: unir por `codigo` (unidad) o por `codigo_municipio` (6 dígitos) /
  `codigo_provincia` (4 dígitos), ya presentes en todas las tablas. La capa `municipios` comparte
  la clave `codigo_municipio`.
- **Reportar área**: usar `area_oficial` (según el INE) o `area`/`tipo_unidad` (cartográfico),
  según la necesidad (ver §8).
- **Terminología**: los campos de unidad se nombran como en la fuente del INE (`personas`,
  `viviendas`, `area`, `ficha`); los términos de publicación del INE están mapeados en §2.
- **Control**: `procesado/comparacion_departamentos_censo2024.csv` documenta el cruce oficial.
- **Reproducción**: el pipeline completo está en `scripts/` y se ejecuta en orden
  `01_descargar_fuentes.py` → `02_procesar_universo.py` → `03_generar_graficas.py` (activa el
  entorno de Python y ajusta `config.py` a tu carpeta). Ver notas de OOM/lectura de parquets en §9.

### 11.2 Gráficas generadas (`graficas/`)

| Carpeta | Gráficas |
|---|---|
| `graficas/nacional/` | totales nacionales, distribución Urbana/Rural oficial vs cartográfica, unidades por tipo |
| `graficas/departamentos/` | población y unidades por departamento, distribución de área oficial o cartográfica por dep. |
| `graficas/municipios/` | top municipios urbanos/rurales, desajuste urbano cartográfico − oficial (dónde difiere, §8) |
| `graficas/ejemplos/` | **muestras de datos** en CSV con los términos usados: `muestra_unidades.csv`, `muestra_resumen_municipios.csv`, `muestra_area_oficial_municipios.csv` |

Todas las gráficas nombran las dos clasificaciones con sus términos (`Manzano`/`Comunidad` ·
`Urbana`/`Rural`/`Mixto`) para que la lectura no dependa del contexto.