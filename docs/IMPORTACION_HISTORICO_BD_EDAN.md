# Importación del histórico legacy "BD EDAN 2002-2025Limpia.xlsx"

Fecha: 2026-09-21 · FASE 2

## Resumen

La base histórica que se mantenía en Excel (17.070 filas de eventos) se importa
al sistema EDAN. **Cada fila incluible se convierte en UN EDAN consolidado**:

- **Cabecera** (`edan.edan`): estado `5 = Aprobado ajuste`, `id_usuario_ugr = NULL`,
  `procedencia = 'excel_legacy'`, `codigo_edan = {codigo_ine}/{año}/{nnn}`.
- **Una localidad vinculada** (`edan_localidades`): nombre = **texto literal de
  `LUGAR` del Excel** (puede ser `''` si está vacío, o genérico como
  `VARIAS COMUNIDADES`), estado `3 = Aprobado UGR`, `id_edan` = cabecera.
- **Secciones** de daños solo si hay dato (ver «Reglas» abajo).
- **Identificador de origen** (`origen_id`): `BD_EDAN-{ID}` si la fila tiene ID
  numérico; `BD_EDAN-SN-{nº fila}` si no tiene ID → la importación es
  **idempotente** (si el `origen_id` ya existe se omite).

## Criterio de inclusión

Solo se importan filas que cumplen **ambas** condiciones esenciales:

1. **Tienen código INE válido** (georreferenciable en `shared.municipio`).
2. **Tienen tipo de evento** (mapeado en la hoja `homologacion` a un
   `tipo_evento` del catálogo).

Adicionalmente la fila debe tener fecha/año (para `codigo_edan`) y un ID
utilizable (la fila `TOTAL` de resumen del Excel se excluye).

## Resultados de la importación (BD real, 2026-09-21)

| Métrica | Cantidad |
|---|---|
| Filas procesadas | 17.070 |
| **Filas importadas** | **16.883** |
| Filas omitidas | 187 |
| Errores de transformación | 0 |
| Secciones totales insertadas | 22.500 |
| EDANs reales existentes (intactos, `procedencia='sistema'`) | 2 |

### Secciones insertadas por tabla

| Tabla | Filas |
|---|---|
| `edan_localidades_danos_viales` | 4.813 |
| `edan_localidades_danos_infra_publica` | 4.756 |
| `edan_localidades_servicios_basicos` | 4.181 |
| `edan_localidades_danos_agricultura` | 5.342 |
| `edan_localidades_danos_vivienda` | 1.547 |
| `edan_localidades_danos_pecuario` | 1.228 |
| `edan_localidades_impacto_poblacion` | 445 |
| `edan_localidades_unidades_educativas` | 161 |
| `edan_localidades_primera_respuesta` (evacuación) | 27 |

## Filas NO importadas y por qué (187)

| Motivo | Filas | Criterio | Ejemplo (ID) |
|---|---|---|---|
| **Sin geografía** | 185 | El `COD. INE` es código de texto no georreferenciable (no está en `shared.municipio`), impide ubicar dep/prov/municipio. | 12719, 13541, 14126, 14655, 14656 |
| **Sin evento homologado** | 1 | El `TIPO DE EVENTO` está vacío y no se puede mapear a `tipo_evento`. | 11459 |
| **Sin ID válido** | 1 | Fila de totales/resumen del Excel (ID = `TOTAL`, celdas con fórmulas). | fila 17070 |

Las 4.177 filas con `LUGAR` vacío, las 500 con `LUGAR` genérico
(`VARIAS COMUNIDADES`, `VARIAS`) y las 1.278 sin ID **tienen código INE y tipo
de evento**, por lo que **sí se importan** (localidad con el texto literal del
Excel; `''` cuando LUGAR viene vacío).

## Reglas de transformación

- **`codigo_edan`**: `{codigo_ine de 6 dígitos}/{año}/{secuencia}`. La secuencia
  continúa el máximo existente por `(ine, año)` en la BD (`{ine}/{año}/{nnn}`);
  el año se toma de la columna `AÑO` (si es numérico 1900–2100) o del año de
  `FECHA EVENTO`.
- **`fecha_evento`**: de la columna `FECHA EVENTO` (puede quedar `NULL`).
- **`origen_id`**: `BD_EDAN-{ID}` (IDs numéricos) o `BD_EDAN-SN-{nº}` (filas sin
  ID, numeradas por su posición en la hoja). Único por fila.
- **Familia afectadas/damnificadas**: de `FAM. AFECTADAS` y `FAM. DAMNIFICADAS`
  (valores no numéricos → primer entero; `HERIDOS` tiene 1.145 alfanuméricos).
- **Secciones**: se inserta fila **solo si hay dato**:
  - `vial` / `infra pública`: código en `{A, D, SI}` → `A`/`SI` = `dano_parcial`,
    `D` = `dano_total`.
  - `servicios básicos`: `tipo` = `energia_electrica | agua_potable |
    alcantarillado | telecomunicaciones` (enum de la tabla).
  - `unidades educativas`: por conteo > 0 en `Centros Educativos`.
  - `vivienda`: `VIV. AFEC.`/`VIV. DES.` (enteros).
  - `agricultura`: `HAS. AFEC.`/`HAS. PERD.` (`id_cultivo = NULL`).
  - `pecuario`: `GAN. AFEC.`/`GAN. PERD` (`id_especie = NULL`).
  - `impacto_poblacion`: si `FALLECIDOS + DESAPARECIDOS + HERIDOS > 0` →
    `id_grupo_etario = 3` (Adulto 19–60), obligatorio.
  - `primera_respuesta`: si `EVACUADOS > 0` → `evacuacion = true` (flag
    `imp_primera_respuesta`, no `imp_proteccion`).
- **Flags `imp_*`** (solo import; `IMP_FLAG_POR_TABLA` de la API real intacta):
  flag de detalle = 1 si existe su sección; flags de **dominio** = OR:
  - `imp_infraestructura` = `imp_danos_viales OR imp_danos_infra_publica`
  - `imp_agropecuario` = `imp_danos_agricultura OR imp_danos_pecuarios
    OR imp_infra_productiva`
  - `imp_servicios` = `imp_servicios_basicos`; `imp_educacion` =
    `imp_unidades_educativas`; `imp_vivienda` = `imp_danos_vivienda`;
    `imp_poblacion` = `imp_impacto_poblacion`.
- Restricciones respetadas: `servicios_basicos.tipo` y
  `impacto_poblacion.id_grupo_etario` NOT NULL; `localidad` ampliada a `TEXT`
  (máx. en origen 1.096 caracteres); `localidad` admite `''` (NOT NULL pero sin CHECK).

## Cómo replicar

Simular (no escribe nada):
```bash
python3 scripts/importar_bdlimpia.py --simular
```

Importar:
```bash
python3 scripts/importar_bdlimpia.py                 # en la BD por defecto
DATABASE_URL=posgresql://... python3 scripts/importar_bdlimpia.py  # otra BD
```

Vía API (autorización JWT): `POST /api/v2/edan/importar-excel`
`multipart/form-data` con el archivo y `modo=simular|importar`,
`solo_compatibles=true|false`.