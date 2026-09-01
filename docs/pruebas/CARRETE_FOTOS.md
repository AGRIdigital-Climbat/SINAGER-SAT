# Pruebas - Carrete de fotos por `id_seccion` (una o varias fotos)

Documenta el endpoint **`POST /api/v2/edan/localidades/foto/subir`** que permite
subir **una o varias fotos** y vincularlas a su `id_seccion`, para el flujo
"carrete de fotos" del Modelo A: la app sube primero las fotos y después guarda
las secciones sin foto reenviando el `path` devuelto.

> **NO subir a GitHub.** Pruebas y datos creados solo en la BD de desarrollo
> y se limpian al final.

## Motivo (flujo offline-first correcto)

La app debe poder subir los binarios (fotos) en cuanto tiene conectividad,
**independiente** del guardado de las secciones (que puede llegar después).
Por eso la subida de fotos se separa del guardado de la sección:

1. **Subir fotos** carrete → se devuelve un `path` por cada `id_seccion`.
2. **Guardar secciones sin foto**, reenviando ese `path` en el campo `fotografia`
   (junto con el GPS de la sección).

## Comportamiento del endpoint

- **Una o varias fotos**: repetir el campo `file` (binarios) y paralelo
  `id_seccion`; también sirve una sola foto con un solo `id_seccion`.
- **GPS opcional**: si vienen `coordenada_lat`/`coordenada_lon` se devuelven en
  cada resultado; **no se exigen** (el GPS es dato de la sección, no de la foto).
- **Coherencia de ids**: si se envían `id_local` (UUID) y/o `id_edan_localidad`
  (int) y la cabecera ya existe, el servidor los **valida** (deben apuntar a la
  misma localidad) y resuelve el municipio para la ruta
  `/uploads/reports/{codigo_ine}/...`.
- **Offline (cabecera aún no existe)**: la foto se guarda igual (carpeta
  `reports/general`) y devuelve el `path`; se asocia al guardar la sección.

### Parámetros (multipart/form-data)

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `file` | file (repetible) | sí | Imagen JPG/PNG máx 5MB. Varias = varias fotos |
| `id_seccion` | string (repetible) | sí | ID único de la sección; paralelo a los archivos |
| `id_local` | UUID | no | Localidad (resuelve municipio si la cabecera existe) |
| `id_edan_localidad` | int | no | Localidad (id int) |
| `coordenada_lat` | float | no | Latitud GPS |
| `coordenada_lon` | float | no | Longitud GPS |

## Preparación

Cabecera huérfana de prueba:
```bash
curl -s -X POST "$BASE/cabecera" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id_tipo_localidad":7,"id_tipo_evento":4,"id_departamento":7,"id_provincia":701,
       "id_municipio":70101,"fecha_llenado":"2026-09-01","fecha_evento":"2026-09-01",
       "hora_evento":"09:00","localidad":"Zona Carrete Array"}'
```
> En las pruebas reales dio `id_edan_localidad = 339` (localidad de prueba).

## Test A: Array de 3 fotos, `id_seccion` paralelo, GPS único

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F "id_edan_localidad=$ID" \
  -F 'id_seccion=carrete-a' -F 'id_seccion=carrete-b' -F 'id_seccion=carrete-c' \
  -F 'file=@f1.png' -F 'file=@f2.png' -F 'file=@f3.png' \
  -F 'coordenada_lat=-17.0' -F 'coordenada_lon=-65.0'
```
**Respuesta:** 201, `results` con 3 items, cada uno `{id_seccion, path, coordenada_lat, coordenada_lon}`.
✓ Array de varias fotos con GPS compartido.

## Test B: Foto individual SIN GPS → 201 (ya no 422)

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F "id_edan_localidad=$ID" -F 'id_seccion=carrete-singps' -F 'file=@f4.png'
```
**Respuesta:** 201. ✓ La foto sin GPS ya **no** se rechaza (en los endpoints
`con-foto` antiguos seguía dando 422; en el carrete el GPS es opcional).

## Test C: Foto individual CON GPS → 201 con coordenadas

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F "id_edan_localidad=$ID" -F 'id_seccion=carrete-1' -F 'file=@f1.png' \
  -F 'coordenada_lat=-16.5' -F 'coordenada_lon=-64.5'
```
**Respuesta:** 201, `results[0]` incluye `coordenada_lat`/`coordenada_lon`.
✓ GPS se preserva si viene.

## Test D: Incoherencia id_local inexistente + id_edan_localidad → 400

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F "id_edan_localidad=$ID" -F 'id_local=uuid-inexistente-123' -F 'id_seccion=carrete-bad' -F 'file=@f2.png'
```
**Respuesta:** HTTP 400 `"Incoherencia: id_local no existe en BD y no coincide con id_edan_localidad"`.
✓ Validación de coherencia.

## Test E: Solo id_local real → resuelve municipio

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F 'id_local=2222aaaa-1111-4f81-9999-34366e0f75b5' -F 'id_seccion=carrete-idlocal' -F 'file=@f3.png'
```
**Respuesta:** 201, `path` bajo `070101/` (municipio resuelto) y devuelve
`id_edan_localidad` + `id_local`. ✓ Resolución por UUID.

## Test F: id_local e id_edan_localidad COINCIDENTES → 201

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F 'id_local=2222aaaa-1111-4f81-9999-34366e0f75b5' -F 'id_edan_localidad=339' \
  -F 'id_seccion=carrete-both-ok' -F 'file=@f2.png'
```
**Respuesta:** 201. ✓ Coincidencia correcta.

## Test G: id_local e id_edan_localidad INCOHERENTES → 400

```bash
curl -s -X POST "$BASE/foto/subir" -H "Authorization: Bearer $TOKEN" \
  -F 'id_local=2222aaaa-1111-4f81-9999-34366e0f75b5' -F 'id_edan_localidad=336' \
  -F 'id_seccion=carrete-both-bad' -F 'file=@f1.png'
```
**Respuesta:** HTTP 400
`"Incoherencia: id_local e id_edan_localidad apuntan a localidades distintas"`.
✓ Detecta dos referencias que no son la misma localidad.

## Test H: Asociar el path del carrete a una sección (sin foto)

Después de subir el carrete, se guarda la sección reenviando el `path` + GPS:
```bash
curl -s -X POST "$BASE/$ID/danos-viales" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '[{"id_seccion":"carrete-a","via":true,"tramo":"Camino 1","dano_parcial":false,
       "fotografia":"/uploads/reports/070101/070101_30_8823051087f5.png",
       "coordenada_lat":-17.0,"coordenada_lon":-65.0}]'
```
**Respuesta:** la sección queda con `fotografia`, `id_seccion`, `via`, `tramo`
y GPS correctos. ✓ Se asocia la foto subida en el carrete a su sección.
Además `imp_danos_viales` se activa (True).

> **Nota de formato:** el POST de sección sin-foto recibe **un objeto o un array
> directo** de items (NO envuelto en `{"items": [...]}`). Un payload con `items`
> generaría la fila con campos vacíos.

## Resumen de resultados

| Test | Descripción | Resultado |
|------|-------------|-----------|
| A | Array de 3 fotos + GPS | ✓ PASS |
| B | Foto sin GPS | ✓ PASS (201, ya no 422) |
| C | Foto con GPS | ✓ PASS |
| D | id_local inexistente + id_edan | ✓ PASS (400) |
| E | Solo id_local resuelve municipio | ✓ PASS |
| F | ids coherentes | ✓ PASS |
| G | ids incoherentes | ✓ PASS (400) |
| H | Asociar path a sección + flag | ✓ PASS |

## Script de limpieza

Se eliminó la localidad de prueba (339) y las fotos del carrete tras los tests.
Referencia:
```sql
DELETE FROM edan.edan_localidades_impacto_poblacion WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_salud_establecimientos WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_danos_agricultura WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_danos_pecuario WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_servicios_basicos WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_unidades_educativas WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_danos_vivienda WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_proteccion WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_salud_necesidades WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_necesidades_humanitarias WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_danos_viales WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_infra_productiva WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades_primera_respuesta WHERE id_edan_localidad=339;
DELETE FROM edan.edan_localidades WHERE id_edan_localidad=339;
# borrar fotos de prueba del disco
# rm -f uploads/reports/070101/070101_30_882305*.png
```
