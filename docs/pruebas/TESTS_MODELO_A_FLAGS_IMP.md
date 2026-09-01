# Pruebas - Modelo A (por secciones) + Flags `imp_*` automáticos

Documenta las pruebas funcionales realizadas sobre el **Modelo A** (guardado por
secciones, UPSERT por `id_seccion`) y el **auto-cálculo de los 14 flags `imp_*`**
del v2 en el servidor.

> **NO subir a GitHub.** Estas pruebas y sus datos se crean y se limpian
> localmente contra la BD de desarrollo.

## Contexto

- Endpoint base: `http://localhost:8000/api/v2/edan/localidades`
- Auth: token JWT rol 7 (usuario 30).
- Flujo Modelo A: `POST` cabecera → `POST` sección (objeto o array) →
  `GET /localidades/{id}` devuelve todas las secciones anidadas.
- El Modelo B (`/sync` y `/sync/pull`) fue **eliminado del v2** (quedan solo
  en v1). El cliente del rol 7 debe usar el Modelo A (por secciones).
- Cada flag `imp_*` nuevo se calcula **automáticamente** en el servidor al
  guardar (INSERT/UPDATE) o eliminar una sección.

## Flags `imp_*` (14 nuevos, uno por sección)

| Columna (nueva) | Sección que la activa | Legacy asociado |
|---|---|---|
| `imp_impacto_poblacion` | impacto_poblacion | imp_poblacion |
| `imp_salud_establecimientos` | salud_establecimientos | imp_salud |
| `imp_danos_viales` | danos_viales | — |
| `imp_danos_infra_publica` | danos_infra_publica | imp_infraestructura |
| `imp_servicios_basicos` | servicios_basicos | imp_servicios |
| `imp_unidades_educativas` | unidades_educativas | imp_educacion |
| `imp_danos_vivienda` | danos_vivienda | imp_vivienda |
| `imp_danos_agricultura` | danos_agricultura | imp_agropecuario |
| `imp_danos_pecuarios` | danos_pecuario | imp_agropecuario |
| `imp_infra_productiva` | infra_productiva | — |
| `imp_primera_respuesta` | primera_respuesta | — |
| `imp_necesidad_salud` | salud_necesidades | imp_salud + imp_necesidades |
| `imp_necesidad_humanitaria` | necesidades_humanitarias | imp_necesidades |
| `imp_proteccion` | proteccion | imp_proteccion (misma columna) |

Nota: la tabla `proteccion` activa **la misma columna** `imp_proteccion` tanto
para el flag nuevo como para el legado (evita el error de UPDATE en columna
duplicada mediante deduplicación de columnas).

---

## Preparación: datos de prueba

Se creó una **localidad huérfana** para las pruebas (no tocar datos reales).

```bash
TOKEN=$(cat /tmp/opencode/token.txt)
BASE=http://localhost:8000/api/v2/edan/localidades

# 1. Crear cabecera (POST devuelve una EDAN huérfana es_huerfana=true)
curl -s -X POST "$BASE/cabecera" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "id_tipo_localidad": 7,
    "id_tipo_evento": 4,
    "id_departamento": 7,
    "id_provincia": 701,
    "id_municipio": 70101,
    "fecha_llenado": "2026-09-01",
    "fecha_evento": "2026-09-01",
    "hora_evento": "09:00",
    "localidad": "Zona Prueba Modelo A"
  }'
```

Resultado: `id_edan_localidad = 337` (localidad de prueba).

---

## Test 1: UPSERT por id_seccion (1:N)

**Request:**
```bash
curl -s -X POST "$BASE/337/impacto-poblacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id_seccion": "imp-01", "rango": "0 a 5 anos", "fallecidos": 2, "heridos": 10},
      {"id_seccion": "imp-02", "rango": "6 a 12 anos", "fallecidos": 0, "heridos": 5}
    ]
  }'
```
**Respuesta:** 201, dos items creados (ids 247-248).

**Re-POST con el MISMO id_seccion (update, sin duplicar):**
```bash
curl -s -X POST "$BASE/337/impacto-poblacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"items": [{"id_seccion": "imp-01", "rango": "0 a 5 anos", "fallecidos": 9, "heridos": 10}]}'
```
**Resultado:** el item `imp-01` (id 247) se **actualizó** (fallecidos 2→9),
NO se creó otro registro. ✓ UPSERT por `id_seccion`.

**Verificación:**
```sql
SELECT id_impacto_poblacion, id_seccion, rango, fallecidos
FROM edan.edan_localidades_impacto_poblacion WHERE id_edan_localidad=337;
```

---

## Test 2: Guardado con foto + regla GPS

**Request (unidades-educativas con foto y GPS):**
```bash
curl -s -X POST "$BASE/337/unidades-educativas/con-foto" \
  -H "Authorization: Bearer $TOKEN" \
  -F 'item={"id_seccion":"edu-01","nombre_establecimiento":"Escuela A","dano_parcial":false}' \
  -F 'coordenada_lat=-17.0' \
  -F 'coordenada_lon=-65.0' \
  -F 'file=@/ruta/foto.png'
```
**Resultado:** 201. Foto guardada en
`/uploads/reports/070101/070101_30_88226595b6c2.png`.

**Caso límite (sin GPS con foto) → 422:**
```bash
curl -s -X POST "$BASE/337/unidades-educativas/con-foto" \
  -H "Authorization: Bearer $TOKEN" \
  -F 'item={"id_seccion":"edu-02","nombre_establecimiento":"Escuela B"}' \
  -F 'file=@/ruta/foto.png'
```
**Resultado:** HTTP 422 — regla: si viene `file`, son obligatorias
`coordenada_lat` + `coordenada_lon`.

**Sección sin foto (sin GPS ok):**
```bash
curl -s -X POST "$BASE/337/servicios-basicos" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"items": [{"id_seccion":"serv-01","tipo":"energia_electrica","dano_parcial":true}]}'
```
**Resultado:** 201 (fotografia=null, GPS null, válido). ✓

---

## Test 3: Secciones 1:1 (ídem y caso límite de unicidad)

Secciones 1:1 = primera-respuesta, necesidad-salud, necesidad-humanitaria:
**un solo registro por localidad** (PK `id_edan_localidad`).

```bash
# primera vez → 201
curl -s -X POST "$BASE/337/necesidad-salud" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id_seccion":"ns-01","numero_personas":100,"otras_necesidades":"Medicamentos"}'

# re-POST con NUEVO id_seccion → 400 "violación de unicidad"
curl -s -X POST "$BASE/337/necesidad-salud" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id_seccion":"ns-02","numero_personas":50}'
```
**Resultado:** primera → 201; la segunda → **HTTP 400** "violación de unicidad".
Para actualizar, el cliente debe **re-enviar el MISMO `id_seccion`**.

---

## Test 4: Auto-cálculo de flags en vivo

Se verificó el cambio del flag `imp_danos_viales` contra POST y DELETE:

```bash
# POST danos-viales → flag se activa
curl -s -X POST "$BASE/337/danos-viales" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"items": [{"id_seccion":"dv-01","via":true,"tramo":"Camino 1","dano_parcial":false}]}'

# GET → imp_danos_viales == true
curl -s "$BASE/337" -H "Authorization: Bearer $TOKEN"

# DELETE la sección por id_seccion → flag se desactiva
curl -s -X DELETE "$BASE/337/danos-viales/seccion/dv-01" -H "Authorization: Bearer $TOKEN"

# GET → imp_danos_viales == false
curl -s "$BASE/337" -H "Authorization: Bearer $TOKEN"
```
**Resultado:** `imp_danos_viales` pasó `false→true` (POST) y `true→false`
(DELETE). ✓ Auto-cálculo tanto al insertar como al eliminar.

---

## Test 5: proteccion (dedup de imp_proteccion)

```bash
curl -s -X POST "$BASE/337/proteccion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id_seccion":"pr-01","id_grupo_vulnerable_catalogo":2,"mujeres":10,"hombres":8}'
```
**Resultado:** 201, sin error de UPDATE en columna duplicada. `imp_proteccion=true`.
✓ El caso especial `_marcar_impacto` deduplica columnas
(`list(dict.fromkeys([nuevo] + legacies))`), por eso `proteccion` contribuye
solo una vez a `imp_proteccion`.

---

## Test 6: GET /localidades/{id} agrupa las secciones

```bash
curl -s "$BASE/337" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
**Resultado:** el GET devuelve todas las secciones anidadas bajo la localidad, con
los 14 flags `imp_*` en el nodo raíz (copiados por `SELECT *`).

---

## Resumen de resultados

| Test | Descripción | Resultado |
|------|-------------|-----------|
| 1 | UPSERT por id_seccion (1:N) | ✓ PASS (sin duplicados) |
| 2 | Foto + regla GPS (422 sin GPS) + sección sin foto | ✓ PASS |
| 3 | Secciones 1:1 (re-POST con nuevo id_seccion → 400) | ✓ PASS |
| 4 | Auto-cálculo de flags en vivo (POST/DELETE) | ✓ PASS |
| 5 | proteccion (dedup imp_proteccion) | ✓ PASS |
| 6 | GET /localidades/{id} con secciones y flags | ✓ PASS |

## Verificación de flags tras las pruebas (backfill en datos reales)

El backfill sobre las 30 localidades existentes se ejecutó y se verificó la
localidad real 336 (Surumaya): `imp_impacto_poblacion`, `imp_primera_respuesta`,
`imp_necesidad_salud`, `imp_salud_establecimientos = true`, y sus legacy
(`imp_poblacion`, `imp_salud`) consistentes. Los flags nuevos reflejan las
secciones con datos.

## Script de limpieza (post-tests)

La localidad de prueba (337) y sus secciones/fotos fueron **eliminadas** tras las
pruebas. Script de referencia por si se reutiliza:

```sql
DELETE FROM edan.edan_localidades_impacto_poblacion WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_salud_establecimientos WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_danos_agricultura WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_danos_pecuario WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_servicios_basicos WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_unidades_educativas WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_danos_vivienda WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_proteccion WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_salud_necesidades WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_necesidades_humanitarias WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_danos_viales WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_infra_productiva WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades_primera_respuesta WHERE id_edan_localidad=337;
DELETE FROM edan.edan_localidades WHERE id_edan_localidad=337;
-- borrar fotos de prueba del disco (nunca datos reales)
# rm -f "uploads/reports/070101/070101_30_88226595b6c2.png" \
#      "uploads/reports/070101/070101_30_88226676ab4f.png"
```
