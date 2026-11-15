# Análisis de los datos `NULL` en hogares (Censo 2024)

> **Pregunta que responde este documento:** *¿por qué hay unidades con `hogares = NULL`,
> dónde están exactamente, se puede sacar ese dato de otra fuente y qué se decidió?*
>
> Fecha: **2026-11-14** · Base: `db_sinagersat` · Todas las cifras verificadas con SQL en vivo.
> Contexto completo del cambio: [`INSTRUCCIONES.md`](INSTRUCCIONES.md) (§6 notas, §7.2 D1/D5/D6).

---

## 1. Resumen ejecutivo

- **117.860 de 268.604 unidades (43,9 %)** tienen `hogares = NULL`: **115.628 manzanos**
  (46,7 %) y **2.232 comunidades** (10,5 %).
- La causa **no es una falla de carga**: el **INE deliberadamente no publica** la ficha de las
  unidades con poca población (**reserva estadística**). No existe otra fuente oficial con
  hogares por debajo del municipio (§5).
- **0 municipios están totalmente sin dato**: los 343 tienen su cifra **exacta** en
  `shared.censo2024_hogares_municipio` (`hogares_ine`). Solo el desglose fino por unidad queda
  parcial.
- Las unidades sin ficha son **pequeñas** (promedio **8,1 personas**): por eso la cobertura de
  *personas* (91,7 %) y de *hogares* (91,7 %) es mucho mayor que la cobertura de *unidades*
  (56,1 %).
- **Decisión del equipo (§1 de INSTRUCCIONES, punto 3): mantener `NULL`** — dato 100 % oficial,
  **nunca se estimó ni se derivó** de población/viviendas. El 15 de noviembre se re-confirmó:
  *"Mantener NULL"*.
- `NULL ≠ 0`: hay **14 unidades con `hogares = 0` real** (ficha publicada sin personas
  presentes: 4 manzanos + 10 comunidades) — el `0` es dato, el `NULL` es "sin dato".

---

## 2. Por qué son NULL (fuente oficial)

Del **release `data-fichas-v1.0.0`** de `lab-tecnosocial/censosbo` (la digitalización oficial
de las fichas del geoportal `geoportal.ine.gob.bo`):

> "*El INE **no publica** la ficha de las unidades con poca población, **por reserva
> estadística**: queda fuera el 47 % de los manzanos, pero las que sí la tienen cubren el
> **92 % de la población y el 90 % de las viviendas** del país.*"

Es una **no-publicación deliberada** (proteger unidades pequeñas de identificación), no un
hueco de procesamiento: ninguna fuente — incluida la microdata oficial — puede tener ese dato
mientras el INE no lo publique.

---

## 3. Cifras exactas (verificadas en BD)

### 3.1 Cobertura global

| Concepto | Manzanos | Comunidades | Total |
|---|---:|---:|---:|
| Unidades totales | 247.429 | 21.175 | **268.604** |
| Con `hogares` (ficha INE) | 131.801 (53,3 %) | 18.943 (89,5 %) | **150.744 (56,1 %)** |
| `hogares = NULL` (sin ficha) | **115.628** (46,7 %) | **2.232** (10,5 %) | **117.860 (43,9 %)** |
| Población en unidades `NULL` | 927.866 | 20.845 | **948.711** (8,3 % nacional) |
| Viviendas en unidades `NULL` | 430.016 | 17.929 | **447.945** (10,0 % nacional) |
| `hogares = 0` (dato real, ≠ NULL) | 4 | 10 | 14 |

Cobertura resultante (nacional):

| Indicador | Con dato oficial | Total INE | Cobertura |
|---|---:|---:|---:|
| Unidades | 150.744 | 268.604 | 56,1 % |
| Población | 10.416.622 | 11.365.333 | 91,7 % |
| Viviendas | 4.032.256 | 4.480.201 | 90,0 % |
| Hogares (suma de unidades) | 3.322.402 | 3.623.711 (`hogares_ine`) | 91,7 % |

### 3.2 Ceros reales (control `NULL ≠ 0`)

`SELECT count(*) FROM shared.manzanos WHERE hogares = 0;` → **4** ·
`… FROM shared.comunidades …` → **10**. Coincide con D6 de `INSTRUCCIONES.md` §7.2:
`viv_tipo_presentes = 0` en la fuente (vivienda registrada sin personas presentes).

---

## 4. Dónde están los `NULL`

### 4.1 Comunidades sin ficha, por departamento (2.232)

| Departamento | Comunidades `NULL` |
|---|---:|
| Santa Cruz | 679 |
| La Paz | 386 |
| Beni | 318 |
| Oruro | 256 |
| Cochabamba | 247 |
| Potosí | 165 |
| Chuquisaca | 77 |
| Tarija | 55 |
| Pando | 49 |
| **Total** | **2.232** |

### 4.2 Grupos de manzanos por nombre (`/censo/manzanos/por-nombre`) sin ningún dato (416 de 2.942)

Cada grupo = `(id_municipio, nombre)`; un grupo está "sin hogares" si **ninguno** de sus
manzanos tiene ficha (`unidades_con_hogares = 0`). Cobertura de grupos: **2.526/2.942 (85,9 %)**.

| Departamento | Grupos sin datos |
|---|---:|
| Potosí | 103 |
| Oruro | 91 |
| Santa Cruz | 68 |
| La Paz | 58 |
| Chuquisaca | 40 |
| Cochabamba | 33 |
| Tarija | 22 |
| Beni | 1 |
| Pando | 0 |
| **Total** | **416** |

### 4.3 Municipios con menor cobertura **por unidades** (≥ 50 unidades)

| Municipio | Depto | Unidades con ficha / total | % unidades |
|---|---|---|---:|
| San Pablo | Potosí | 29 / 275 | 10,5 % |
| Llica | Potosí | 65 / 549 | 11,8 % |
| Colcha "K" | Potosí | 154 / 1.242 | 12,4 % |
| Uru Chipaya | Oruro | 30 / 222 | 13,5 % |
| Turco | Oruro | 42 / 301 | 14,0 % |
| San Antonio de Lomerio | Santa Cruz | 55 / 390 | 14,1 % |
| Tahua | Potosí | 20 / 137 | 14,6 % |
| Salinas de Garci Mendoza | Oruro | 185 / 1.244 | 14,9 % |
| Yunguyo del Litoral | Oruro | 8 / 53 | 15,1 % |
| Coipasa | Oruro | 15 / 99 | 15,2 % |

### 4.4 Municipios con menor cobertura **de hogares** (distinta métrica)

`SUM(hogares de unidades) / hogares_ine` — es la métrica de `INSTRUCCIONES.md` §7.2; al ser las
unidades sin ficha **pequeñas**, esta cobertura es mayor que la de unidades:

| Municipio | Hogares de unidades / `hogares_ine` | % hogares |
|---|---|---:|
| San Agustín (Potosí) | 175 / 667 | 26 % |
| Coipasa (Oruro) | 125 / 357 | 35 % |
| San Antonio de Lomerio (SC) | 612 / 1.475 | 41 % |
| Yunguyo del Litoral (Oruro) | 72 / 173 | 42 % |
| Llica (Potosí) | 819 / 1.856 | 44 % |

**Los 343 municipios tienen al menos una unidad con ficha** (`municipios_con_todo_null = 0`).

---

## 5. ¿Se puede sacar de otro lado? Fuentes verificadas: NO

| # | Fuente | Nivel que alcanza | Por qué no sirve |
|---|---|---|---|
| 1 | **Microdata oficial INE** (CSV 413 MB, `cpv2024.ine.gob.bo`; ya descargada y verificada 343/343) | **Municipio** | Registros traen solo `idep`, `iprov`, `imun` (+ `i00` de vivienda): **no hay código de manzano/localidad** en encabezados ni diccionario |
| 2 | **REDATAM** (`redatam.ine.gob.bo`) | **Municipio** | El propio INE lo declara: "*bases de datos en Redatam, **hasta el nivel de municipios***" |
| 3 | **Tabulados INE** (cuadros de `cpv2024.ine.gob.bo`) | Municipio / TIOC | Nada por manzano; para TIOC falta una tabla puente TIOC↔municipio (documentado en `README_censo2024.md` §10) |
| 4 | **Geoportal INE vía censosbo** (`fuentes/unidad.parquet`, geometrías) | Unidades con `personas`, `viviendas` y geometría | **Sin hogares**; solo trae el flag booleano `ficha` (oficial: 150.744 `True`). Archivos geo: `codigo, nombre, idep, iprov, imun, geometria` |
| 5 | **Releases de censosbo** (API de GitHub, `lab-tecnosocial/censosbo`) | — | Única versión de fichas: `data-fichas-v1.0.0` (2026-07-27, 150.744 unidades). **No existe release más completa** |
| 6 | Niveles alternativos (barrios, zonas, localidades) | — | El nivel urbano más fino **oficial** es el manzano; barrios/zonas "no son un nivel oficial" (`README_censo2024.md` §10) |

Conclusión: mientras el INE no publique más fichas, **`NULL` es la única representación fiel**
del dato a nivel unidad. A nivel municipio **sí está el dato exacto** para los 343
(`hogares_ine`, verificado contra microdata 343/343).

---

## 6. Estimación evaluada y descartada (no se usó)

Se validó una asignación proporcional — `hogares_estimado = viviendas_unidad ×
(hogares_ine_municipio / viviendas_municipio)` — **solo como estudio**, comparándola contra las
**150.744 unidades que sí tienen dato real**:

| Peso | Error absoluto medio | Error % mediano | Dentro de ±1 hogar | Dentro de ±2 | Sesgo medio |
|---|---:|---:|---:|---:|---:|
| **viviendas** (mejor) | 2,92 hogares | 11,9 % | 27,8 % | 55,3 % | −0,34 |
| personas | 3,71 hogares | 13,6 % | 26,4 % | 48,3 % | — |

Resultado: **no se implementa**. Violaba la decisión #3 del equipo (*"cobertura solo oficial;
no se estimó ningún dato"*) y el error por unidad es alto (error típico ≈ 12 %, solo 28 % de
las unidades caería en ±1 hogar). Además **no aporta nada a nivel municipio**, donde ya está la
cifra exacta. Re-confirmado con el equipo el **2026-11-15**: *"Mantener NULL"*.

---

## 7. Cómo se comporta la API con los `NULL`

| Superficie | Comportamiento |
|---|---|
| `GET /manzanos`, `/comunidades` (listado) | `hogares: null`, `personas_por_hogar: null` en unidades sin ficha |
| `GET /{codigo_ine}/poblacion` | ídem |
| GeoJSON (`properties`) | ídem (`hogares` ausente en `properties` cuando es NULL) |
| Resúmenes `/censo/poblacion/*` | `hogares` = suma de unidades (NULL si **ninguna** tiene ficha), **`unidades_con_hogares`** = cobertura, `hogares_ine` = cifra exacta (343/343), `personas_por_hogar` = `ROUND(poblacion / hogares_ine)` |
| `GET /censo/manzanos/por-nombre` | por grupo: `unidades_con_hogares` (0 = grupo sin datos) y `personas_por_hogar: null` si `hogares = 0` |
| Ejemplo real (resumen Santa Cruz) | `hogares: 441.420` (unidades), `unidades_con_hogares: 16.810`, `hogares_ine: 453.158`, `personas_por_hogar: 4` |

**Regla de oro:** `hogares = NULL` significa *"sin ficha del INE"*; **no se trata como 0** ni se
rellena con estimaciones. La cobertura se publica siempre con `unidades_con_hogares`.

---

## 8. Cómo reproducir estas cifras (SQL)

```sql
-- Cobertura global por tipo de unidad
SELECT 'manzanos' AS tipo, COUNT(*) total,
       COUNT(hogares) con_hogares, COUNT(*) - COUNT(hogares) sin_hogares
FROM shared.manzanos
UNION ALL
SELECT 'comunidades', COUNT(*), COUNT(hogares), COUNT(*) - COUNT(hogares)
FROM shared.comunidades;
-- manzanos 247429 | 131801 | 115628 · comunidades 21175 | 18943 | 2232

-- Población y viviendas de las unidades sin ficha
SELECT SUM(personas), SUM(viviendas) FROM (
  SELECT personas, viviendas FROM shared.manzanos   WHERE hogares IS NULL
  UNION ALL
  SELECT personas, viviendas FROM shared.comunidades WHERE hogares IS NULL) t;
-- 948711 | 447945

-- ¿Hay algún municipio totalmente sin dato? (esperado: 0)
SELECT COUNT(*) FROM (
  SELECT id_municipio FROM (
    SELECT id_municipio, hogares FROM shared.manzanos
    UNION ALL SELECT id_municipio, hogares FROM shared.comunidades) t
  GROUP BY id_municipio
  HAVING COUNT(*) FILTER (WHERE hogares IS NULL) = COUNT(*)) x;

-- Comunidades NULL por departamento
SELECT d.nombre, COUNT(*) FROM shared.comunidades c
JOIN shared.departamento d ON d.id = c.id_departamento
WHERE c.hogares IS NULL GROUP BY d.nombre ORDER BY 2 DESC;

-- Grupos por-nombre (manzanos) sin ningún dato: 416 de 2.942
WITH g AS (SELECT id_municipio, nombre, COUNT(*) u, COUNT(hogares) c
           FROM shared.manzanos GROUP BY id_municipio, nombre)
SELECT COUNT(*) FILTER (WHERE c = 0) sin_datos, COUNT(*) total FROM g;

-- Cobertura por municipio (unidades con ficha)
WITH u AS (SELECT id_municipio, hogares FROM shared.manzanos
           UNION ALL SELECT id_municipio, hogares FROM shared.comunidades),
     g AS (SELECT id_municipio, COUNT(*) tot, COUNT(hogares) con FROM u GROUP BY id_municipio)
SELECT mu.nombre, g.con || '/' || g.tot,
       ROUND(100.0 * g.con / g.tot, 1) || '%'
FROM g JOIN shared.municipio mu ON mu.id = g.id_municipio
ORDER BY 3::float8 ASC LIMIT 10;
```

---

## 9. Si en el futuro el INE publica más fichas

1. Descargar la `ficha.parquet` nueva desde el release de censosbo (URL y SHA-256 en
   `INSTRUCCIONES.md` §2) y reemplazar `datos/ficha.parquet`.
2. Re-ejecutar `venv/bin/python scripts/cargar_hogares_censo2024.py --simular` y luego
   `--importar` (**idempotente**: rellena los `NULL` que aparezcan y revalida todo).
3. Actualizar los conteos de este documento y de `INSTRUCCIONES.md` §7.2 (D1).

Mientras tanto: **no estimar, no derivar** `hogares` de `personas/viviendas` (decisión #3).
