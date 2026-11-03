# 02 · Empadronamiento

> Registrar la población afectada: **formulario por localidad → familias → integrantes → ubicaciones**.
> Prefijo de la API: `/api/v2/rida/empadronamiento` · Requiere rol con permiso de escritura: **1, 2, 6, 7**.

## 1. El modelo en una imagen

```
evento RIDA (uno por EDAN aprobado)
   └── formulario RIDA  ← uno por localidad  (clave: id_edan_localidad)
         ├── familia    ← una por hogar      (clave offline: id_familia_off)
         │     ├── integrante                (clave offline: id_integrante_off)
         │     └── ubicación                 (clave offline: id_ubicacion_off)
         └── necesidades                     → ver Cap. 04
```

- **Un formulario por localidad**: `id_edan_localidad` es UNIQUE en la base de datos.
- Cada registro lleva su **clave offline** para que la app móvil pueda crear todo sin red y sincronizar después ([Cap. 08](08-offline-y-sincronizacion.md)).

## 2. Checklist del flujo completo

- [ ] 1. Obtener las localidades / el evento (Cap. 03).
- [ ] 2. Crear o localizar el **formulario** de la localidad.
- [ ] 3. Crear las **familias** del formulario.
- [ ] 4. Crear los **integrantes** de cada familia (marcar `es_jefe`).
- [ ] 5. Registrar la **ubicación** (lat/lon, tipo de albergue) de cada familia.
- [ ] 6. Registrar las **necesidades** de cada familia (Cap. 04).
- [ ] 7. Cambiar el estado del formulario a `EN_PROCESO` / `CERRADO`.

## 3. Catálogos de apoyo

| Endpoint | Contenido |
|---|---|
| `GET /cat-tipo-albergue` | Tipos de albergue (`rida.cat_tipo_albergue`) |
| `GET /cat-estado-formulario` | 1 PENDIENTE · 2 EN_PROCESO · 3 CERRADO |
| `GET /cat-parentesco` | Parentescos |
| `GET /cat-tipo-discapacidad` | Tipos de discapacidad |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v2/rida/empadronamiento/cat-parentesco
```

## 4. Paso 2 — Formulario

**Crear** `POST /api/v2/rida/empadronamiento/formularios`

```json
{ "id_edan_localidad": 42, "id_estado": 1 }
```

- `id_edan_localidad` es **obligatorio** y único.
- `id_edan` se infiere del EDAN de la localidad si no se envía.
- Si el formulario ya existe para esa localidad, recibirás error de duplicado: **busca primero**.

**Consultar**

| Endpoint | Uso |
|---|---|
| `GET /formularios` | Listado con filtros geográficos y paginación |
| `GET /formularios/mis` | Solo mis formularios (según mi scope) |
| `GET /formularios/{id}` | Detalle **con familias e integrantes** (árbol completo) |
| `PUT /formularios/{id}` | Cambiar `id_estado` o `id_edan` |
| `DELETE /formularios/{id}` | Eliminar (si no tiene hijos) |

```bash
# Cambiar estado a EN_PROCESO (2)
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"id_estado": 2}' \
  http://localhost:8000/api/v2/rida/empadronamiento/formularios/35
```

## 5. Paso 3 — Familias

**Crear** `POST /api/v2/rida/empadronamiento/formularios/{id_formulario}/familias`

```json
{
  "id_familia_off": "fam-20261005-a1b2",
  "observacion": "Vivienda con daño parcial en techo"
}
```

| Campo | Nota |
|---|---|
| `id_familia_off` | Identificador generado por el dispositivo; **clave en la sincronización** |
| `id_edan_localidad` | Alternativa a `id_formulario` en el flujo de sync |
| `id_necesidad` | Necesidad representativa (opcional) |
| `observacion` | Notas libres |

> ⚠️ `codigo_ficha`, `n_integrantes`, `ubicacion_actual` y `id_jefe` **ya no existen** (eliminados en la migración `v2.19.0`). El jefe de hogar se marca en el integrante con `es_jefe: true`.

**Otros endpoints:** `GET/PUT/DELETE /familias/{id_familia}` · `GET /formularios/{id}/familias`

## 6. Paso 4 — Integrantes

**Crear** `POST /api/v2/rida/empadronamiento/familias/{id_familia}/integrantes`

```json
{
  "id_integrante_off": "int-20261005-x9",
  "nombre": "Juan",
  "apellido": "Perez",
  "sexo": "M",
  "fecha_nacimiento": "1985-04-12",
  "tipo_documento": "CARNET",
  "numero_documento": "6543210",
  "id_parentesco": 1,
  "es_jefe": true,
  "telefono": "76543210"
}
```

| Campo | Regla |
|---|---|
| `sexo` | `"M"` o `"F"` |
| `gestante_semanas` | 0–45, solo si aplica (`NULL` si no) |
| `lactante_meses` | 0–36, solo si aplica |
| `id_discapacidad` / `id_enfermedad` | Claves a los catálogos |
| `tipo_documento` | `CARNET` (default) o `CERTIFICADO` |

**Regla de duplicados:** existe un índice único sobre `(tipo_documento, numero_documento, nombre, apellido, fecha_nacimiento)`. Si intentas registrar dos veces a la misma persona recibirás error `409/400` de duplicado — usa [la búsqueda](#7-buscar-personas) antes de crear.

**Actualizar / eliminar:** `PUT|DELETE /integrantes/{id_integrante}` · `GET /familias/{id}/integrantes`

## 7. Buscar personas

`GET /api/v2/rida/empadronamiento/personas/buscar`

| Parámetro | Ejemplo |
|---|---|
| `busqueda` | texto libre: nombre, apellido o documento |
| `nombre` | nombre exacto |
| + filtros geográficos | `id_municipio`, `id_departamento` |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?busqueda=Perez"
```

## 8. Paso 5 — Ubicaciones

**Crear** `POST /api/v2/rida/empadronamiento/familias/{id_familia}/ubicaciones`

```json
{
  "id_ubicacion_off": "ubi-20261005-z1",
  "coordenada_lat": -14.8333,
  "coordenada_lon": -64.9000,
  "id_cat_tipo_albergue": 1
}
```

`coordenada_lat` (−90…90) y `coordenada_lon` (−180…180). **Otros:** `GET/PUT/DELETE /ubicaciones/{id_ubicacion}` · `GET /familias/{id}/ubicaciones`.

## 9. Consultar resultados

```bash
# Árbol completo de un formulario (familias + integrantes + ubicaciones)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v2/rida/empadronamiento/formularios/35
```

Respuesta (simplificada):

```json
{
  "success": true,
  "data": {
    "id_formulario": 35,
    "id_edan_localidad": 42,
    "id_estado": 1,
    "familias": [
      { "id_familia": 10, "id_familia_off": "fam-...",
        "integrantes": [ {"id_integrante": 12, "nombre": "Juan", "es_jefe": true} ],
        "ubicaciones": [] }
    ]
  }
}
```

## 10. Trabajo por lotes (recomendado en campo)

En lugar de una petición por familia, usa el **sync por lote** — una sola petición con todo lo capturado:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "formularios": [{"id_edan_localidad": 42, "id_estado": 1}],
    "familias":    [{"id_familia_off": "fam-1", "id_edan_localidad": 42}],
    "integrantes": [{"id_integrante_off": "int-1", "id_familia_off": "fam-1",
                     "nombre": "Juan", "apellido": "Perez", "sexo": "M", "es_jefe": true}],
    "ubicaciones": [{"id_ubicacion_off": "ubi-1", "id_familia_off": "fam-1",
                     "coordenada_lat": -14.83, "coordenada_lon": -64.9}]
  }' \
  http://localhost:8000/api/v2/rida/empadronamiento/sync
```

→ Detalle completo en [Cap. 08](08-offline-y-sincronizacion.md).

## 11. Errores frecuentes

| Error | Causa | Solución |
|---|---|---|
| `422 id_edan_localidad es obligatorio` | Falta la clave del formulario | Envía `id_edan_localidad` |
| `409` / duplicado de integrante | Misma persona registrada dos veces | [Busca antes](#7-buscar-personas) |
| `403 Sin permiso: CREATE en RIDA` | Tu rol no es 1, 2, 6 ni 7 | Ver [Cap. 01 §3](01-acceso-y-roles.md) |
| `404` al crear familia | `id_formulario` inexistente o fuera de tu alcance geográfico | Lista con `GET /formularios/mis` |

Más errores: [Cap. 10](10-faq-y-problemas.md).

---

**Anterior:** [01 · Acceso](01-acceso-y-roles.md) · **Siguiente:** [03 · Eventos](03-eventos.md)
