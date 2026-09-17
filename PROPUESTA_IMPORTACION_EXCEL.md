# Propuesta: Carga de datos legacy (BDLimpia.xlsx) al sistema EDAN

> **Documento de decisión para revisión con el personal.**
> Nada ha sido subido a GitHub. El manejo del archivo Excel y su carga solo son cambios **locales** hasta que se apruebe.

---

## 1. Estado actual (qué se hizo hasta ahora)

- Rama `v1.3.6` **sincronizada** con `origin` (0 commits sin subir). No se tocó nada en GitHub.
- Local, sin impacto en datos:
  - Backup de BD: `database/backup_2026_09_11_162407.sql`
  - Migración `v2.12.0_importacion_excel.sql` **aplicada solo local**: agrega columnas `procedencia`, `origen_id`, `id_importacion` a `edan.edan_localidades` y crea la tabla `edan.edan_importacion_log`. **No inserta ningún registro.**
- `BDLimpia.xlsx` **NO está y NO estará** en git (contiene datos personales de víctimas). Solo queda como archivo local sin trackear.
- Pendiente de decisión: subir **todo** el histórico (2002–2026) o un subconjunto.

Revertir la migración local, si el personal decide no cargar nada:
```sql
ALTER TABLE edan.edan_localidades DROP CONSTRAINT IF EXISTS edan_localidades_id_importacion_fk;
ALTER TABLE edan.edan_localidades DROP CONSTRAINT IF EXISTS edan_localidades_procedencia_check;
ALTER TABLE edan.edan_localidades DROP COLUMN IF EXISTS procedencia, DROP COLUMN IF EXISTS origen_id, DROP COLUMN IF EXISTS id_importacion;
DROP TABLE IF EXISTS edan.edan_importacion_log;
```

---

## 2. Objetivo

Convertir el archivo legacy (1 hoja "Hoja1", 40 columnas, **17,070 filas**, años 2002–2026) al modelo actual de la BD: **1 fila de Excel = 1 localidad** en `edan.edan_localidades`, con sus daños en las tablas de sección.

- Los datos se marcan con `procedencia = 'excel_legacy'` para distinguirlos de los cargados por el sistema (`'sistema'`).
- Se usa un endpoint nuevo `POST /edan/importar-excel` (autenticado, **sin** restricción por rol) y un script cliente aparte.
- Las APIs GET del EDAN (consolidado, reportes, localidades) **no cambian** y devuelven la data importada tal cual.

---

## 3. Compatibilidad del archivo con la BD (resumen ejecutivo)

| Indicador | Valor | Estado |
|---|---|---|
| Filas (eventos de localidad) | 17,070 | OK |
| Municípios cubiertos | **343/343** (todo Bolivia) | OK |
| Geo resuelve por Código INE | 17,041 (99.8%) | OK |
| Geo no resoluble | 29 (16 vacíos + 13 `#N/A`, y el nombre tampoco matchea) | ⚠️ 0.17% |
| Tipo de evento resuelve al catálogo | 16,667 (16,267 directo + 400 compuesto) | OK* |
| Epidemia (sin categoría en catálogo) | 403 (`CUARENTENA EPIDEMIA` 312, `EPIDEMIA` 84, `BIOLÓGICO` 7) | ⚠️ requiere crear catálogo |
| Tipo de evento sin ningún match | 7 (`OTROS`, `ESCASEZ DE COMBUSTIBLE` x2, `ASISTENCIA HUMANITARIA TRANSPORTE`, `'0'`, `None` x2) | ⚠️ |
| Fecha de evento válida | 16,733 (datetime real) | OK |
| Fecha como texto/rango | 310 (`"ENERO - MARZO"`, `"POR CONFIRMAR"`, `"MARZO"`, …) | ⚠️ → NULL |
| Filas sin ID (col A) | 1,278 (7.5%) | se genera ID sintético |
| Duplicados probables (mismo lugar+familias+evento) | 528 grupos / 1,706 filas | ⚠️ revisar criterio |
| Filas "vacías" (sin daños) | 2 | ok |

\* 402 compuestos del tipo `INUNDACIÓN Y RIADA` → se toma el **primer** evento de la cadena.

### Alcance por tabla de daños (cuántas filas generarían cada sección)

| Sección | Filas |
|---|---|
| danos_agricultura | 5,464 |
| danos_viales (Infra. Vial) | 4,814 |
| danos_infra_publica (Infra. Pública) | 4,755 |
| servicios_basicos – Agua potable | 2,318 |
| danos_vivienda | 1,569 |
| danos_pecuario | 1,262 |
| servicios_basicos – Energía | 833 |
| servicios_basicos – Alcantarillado | 794 |
| impacto_poblacion (fallecidos/heridos/desaparecidos) | 455 |
| servicios_basicos – Telecomunicaciones | 236 |
| unidades_educativas | 164 |
| primera_respuesta (evacuados) | 29 |

---

## 4. Mapeo columna por columna (Excel → BD)

| Col | Encabezado (Hoja1) | Destino en BD | Cobertura | Conflicto |
|---|---|---|---|---|
| A | ID | `localidad.origen_id` (dedupe) — sintético `orig-{fila}` si falta | 93% tiene | Bajo |
| B | FECHA EVENTO | `localidad.fecha_evento` | 16,733 ok | Bajo |
| C | MES | — (deriva de fecha) | — | Nulo |
| D | AÑO | — (deriva de fecha) | — | Nulo |
| E | COD. INE | depto/prov/mun por código (zfill 6) | 99.8% | Bajo |
| F | DEPARTAMENTO | `shared.departamento` (fallback nombre) | 100% | Bajo |
| G | PROVINCIA | `shared.provincia` (fallback nombre) | 100% | Bajo |
| H | MUNICIPIO | `shared.municipio` (fallback nombre) | 100% | Bajo |
| I | LUGAR | `localidad.localidad` | ~9,689 únicos; vacío en boletines COVID | **Medio** |
| J | N COMUNIDADES | — **sin destino en BD** | — | Nulo (se descarta) |
| K | TIPO DE EVENTO | `localidad.id_tipo_evento` | 99.96% (7 sin match) | **Alto** |
| L | FAM. AFECTADAS | `total_familias_afectadas` | OK | Bajo |
| M | FAM. DAMNIFICADAS | `total_familias_damnificadas` | OK | Bajo |
| N | Infraestructura Vial | `danos_viales` (via, km) | 4,814 | **Medio** |
| O | Infraestructura Pública | `danos_infra_publica` | 4,755 | **Medio** |
| P | Energía Eléctrica | `servicios_basicos` (tipo=Energía) | 833 | **Medio** |
| Q | Agua potable | `servicios_basicos` (tipo=Agua potable) | 2,318 | **Medio** |
| R | Alcantarillado | `servicios_basicos` (tipo=Alcantarillado) | 794 | **Medio** |
| S | Gas. Dom. | `servicios_basicos` | 0 reales (todo 0) | Bajo (no genera) |
| T | Telecom. | `servicios_basicos` (tipo=Telecomunicaciones) | 236 | **Medio** |
| U | Centros Educativos | `unidades_educativas` (dano_parcial) | 164 | Bajo |
| V | VIV. AFEC. | `danos_vivienda.dano_parcial` (nº) | 741 | Bajo |
| W | VIV. DES. | `danos_vivienda.dano_total` (nº) | 1,104 | Bajo |
| X | HAS. AFEC. | `danos_agricultura.hectareas_afectadas` | 5,196 | Bajo |
| Y | HAS. PERD. | `danos_agricultura.hectareas_perdidas` | 1,238 | Bajo |
| Z | GAN. AFEC. | `danos_pecuario.animales_afectados` | 1,214 | Bajo |
| AA | GAN. PERD | `danos_pecuario.animales_muertos` | 467 | Bajo |
| AB | OBS. | `impacto_poblacion.observaciones` (si hay víctimas) | — | Bajo |
| AC | Fuente | — **sin destino en BD** | DC/O-I/… | **Medio** (se descarta) |
| AD | FORM. EDAN | — **sin destino en BD** (contaminado con texto) | solo C/E 8,148 y S/E 2,352 útiles | **Alto** (se descarta) |
| AE | FALLECIDOS | `impacto_poblacion.fallecidos` | 409 | Bajo |
| AF | DESAPARECIDOS | `impacto_poblacion.desaparecidos` | 48 | Bajo |
| AG | HERIDOS | `impacto_poblacion.heridos` | 59 | Bajo |
| AH | EVACUADOS | `primera_respuesta.evacuacion` (bool si >0) | 29 | Bajo |
| AI–AN | DESASTRE/EMERGENCIA/… | — casi todo vacío | — | Nulo (se descarta) |

**Campos del sistema sin equivalente en el Excel** (se fijan con default): `id_edan_localidad_estado = 1 (Borrador)`, `id_tipo_localidad = 2 (Comunidad)`, `id_grupo_etario = 3 (adulto 19–60)` para impacto, `total_poblacion_afectada = 0`.

---

## 5. Columnas que generan conflicto (de mayor a menor)

1. **K TIPO DE EVENTO — el mayor conflicto.**
   - 64 valores distintos. Muchos son **eventos compuestos** (`INUNDACIÓN Y RIADA`, `DESLIZAMIENTO Y GRANIZADA`, `INUNDACIÓN, RIADA Y DESLIZAMIENTO`, `SEQUIA E INCENDIO`…). No existe en la BD una noción de multi-evento.
   - 403 filas son **epidemias** y el catálogo `tipo_evento` no tiene esa categoría → se propone **crear el catálogo `Epidemias`** (insert nuevo).
   - 7 filas sin match (`OTROS`, `ESCASEZ DE COMBUSTIBLE`, `ASISTENCIA HUMANITARIA TRANSPORTE`, `'0'`, `None`): no son eventos propiamente.
   - **Regla propuesta:** tokenizar `Y / E / , / /`; tomar el primer token que matchee el catálogo. Si nada matchea, importar igual con `id_tipo_evento = NULL` y registrar aviso (nunca descartar la fila).

2. **AD FORM. EDAN — engañoso y contaminado.**
   - Solo `C/E` (8,148) y `S/E` (2,352) son valores formales. El resto (~400+) es **texto libre descriptivo** (ej: "Pérdida de cultivos de maíz, papá, oca...", boletines COVID "Ayuda Humanitaria COVID 19"). Es información valiosa pero **no tiene columna destino** en el modelo actual.
   - Se descarta. (Add: el texto del boletín queda perdido salvo que se archive en el lote de importación.)

3. **AC FUENTE.** 100+ valores. Formales: `DC` (10,027), `O-I` (115), `O-DC` (293), `O` (65). Resto: `WhatsApp …`, `PTDDC 012/20`, `MEDIOS DE COMUNICACIÓN…`. Sin columna destino → se descarta.

4. **N–T Servicios e Infraestructura.** Valores `S/D` (sin dato), `A` (afectado), `D` (dañado), `N/T`, `S/N`, `S/A`, `0` y basura ("seleccionable daño total/ daño parcial", "numero", "140KM.").
   - **Regla propuesta:** `A`, `D`, `SI` o número >0 → daño (`dano_parcial = true`); `S/D`, `N/T`, `S/N`, `S/A`, `0`, vacío → sin dato. `S` (Gas. Dom.) = 100% 0 → no generará registros.

5. **E COD. INE.** 16 vacíos + 13 `#N/A` = **29 filas (0.17%)** que no se geocodifican ni por código ni por nombre → candidatas a **omitir** (o revisarse a mano). El resto resuelve perfecto (los 343 municipios).

6. **B FECHA EVENTO.** 310 textos (`"ENERO - MARZO"`, `"POR CONFIRMAR"`, `"MARZO"`) → `fecha_evento = NULL` (se pierde precisión pero no la fila). 27 vacíos.

7. **A ID.** 1,278 sin ID → se genera `orig-{nro_fila}` (los datos sí importan, el ID solo sirve de dedupe).

8. **I LUGAR.** La localidad queda vacía en los boletines COVID (se reportó solo a nivel municipio). Aceptable, pero queda `localidad = ""`.

9. **Duplicados.** 528 grupos (1,706 filas) con el mismo lugar+familias+evento (los tope son boletines COVID diarios). No se detecta ni corrige automáticamente; queda para criterio del personal (ver Pregunta F).

---

## 6. Lógica de importación propuesta (paso a paso)

1. `POST /edan/importar-excel` recibe el `.xlsx` (multipart), `modo` ∈ {`upsert`, `solo-nuevos`} y opcional `simular=true` (previsualisa resumen sin tocar BD). **Auth JWT requerida, sin rol.**
2. Se lee Hoja1 con `openpyxl` (nueva dependencia). Los encabezados se normalizan (sin acentos/minúsculas) y se mapean a campos internos.
3. Por cada fila (2..N):
   a. **Geo**: `COD.INE → zfill(6)` (depto=2, prov=4, munic=6) con catálogo en memoria; fallback por nombre (depto/prov/mun). Si no resuelve → fila omitida (contada).
   b. **Evento**: tokenizar y mapear al catálogo; fallback `id_tipo_evento=NULL` con aviso.
   c. **Fecha**: datetime real o `NULL`.
   d. **Cabecera localidad**: se crea huérfana (`id_edan=NULL`, Borrador) con `procedencia='excel_legacy'`, `origen_id`, `id_importacion`.
   e. **Secciones**: se insertan con `id_seccion = 'legacy-{origen}-{seccion}'` → **re-import es idempotente** (mismo ID se actualiza, no se duplica). Los flags `imp_*` se mantienen solos (`_marcar_impacto`).
4. Cada lote se registra en `edan_importacion_log` (`insertadas`, `actualizadas`, `omitidas`, `errores`, `detalle` JSONB con fila+motivo).
5. Respuesta: resumen + avisos por fila.

**Inmutabilidad:** las localidades importadas viven en las mismas tablas → `GET /edan/reportes/resumen`, consolidado, etc., las ven sin cambios. La columna `procedencia` se expone en las respuestas GET para que la app/histórico pueda distinguir.

---

## 7. Cambios al sistema requeridos (migración v2.12.0, ya escrita y aplicada local)

1. `edan_localidades`: `+procedencia` (CHECK `sistema|excel_legacy|api_import`), `+origen_id`, `+id_importacion`; índices por `procedencia` y `origen_id`.
2. Tabla nueva `edan_importacion_log` (lote completo + `detalle` JSONB).
3. Catálogo: insert `Epidemias` en `tipo_evento` (requiere decisión B).
4. `requirements.txt`: `+openpyxl` (solo servidor).
5. Endpoint + service `service_importar.py` + script cliente `importar_bdlimpia.py`.
6. `_build_localidad()`: exponer `procedencia`/`origen_id` en GET.

---

## 8. Decisiones para el personal (bloquantes)

- **A. ¿Cargar todo el histórico (17,070 filas, 2002–2026) o un subconjunto?**
  Muy pocas filas están "vacías" (2). Incluye boletines COVID 2020 (`CUARENTENA EPIDEMIA`, "Ayuda humanitaria") y menciones de emergencias que no son daños por evento (Incendios/Sequías "Atención COVID"). ¿Se cargan como histórico también?
- **B. EPIDEMIA**: ¿crear la categoría `Epidemias` en el catálogo `tipo_evento`? (recomendado)
- **C. 29 filas sin geo**: ¿omitirlas o revisar a mano?
- **D. Interpretación de N–T**: `A/D/SI = daño` (recomendado).
- **E. EVACUADOS → `primera_respuesta.evacuacion`** (recomendado).
- **F. Duplicados (1,706 filas)**: ¿cargar igualmente como histórico o filtrar los obvios de boletines COVID?
- **G. Filas sin evento (7)**: importar con `id_tipo_evento=NULL` (recomendado) o descartar.
- **H. Subir la migración/SQL a GitHub cuando se apruebe**: actualmente los cambios son **solo locales**.

---

## 9. Pendiente (no ejecutado aún)

- [ ] Decisión del personal sobre el alcance y las preguntas de la sección 8
- [ ] Endpoint `POST /edan/importar-excel` (router)
- [ ] Service de importación (`service_importar.py`)
- [ ] Exponer `procedencia`/`origen_id` en GET (`service.py`)
- [ ] Script cliente `importar_bdlimpia.py` (fuera del repo)
- [ ] Pruebas de carga local + verificación en reportes
- [ ] Push a GitHub **solo si** se aprueba la carga