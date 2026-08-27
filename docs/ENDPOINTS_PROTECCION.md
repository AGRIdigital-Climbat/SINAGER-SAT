# Endpoints de Protección (Grupos Vulnerables)

## Descripción

Endpoints dedicados para gestionar individualmente los grupos vulnerables asociados a una localidad EDAN.

**Tabla:** `edan.edan_localidades_proteccion`

**Catálogo:** `edan.grupo_vulnerable` (8 grupos predefinidos)

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/edan/localidades/{id}/proteccion` | Lista todos los grupos vulnerables de una localidad |
| `POST` | `/edan/localidades/{id}/proteccion` | Crea o actualiza un grupo vulnerable (UPSERT por `id_seccion`) |
| `PUT` | `/edan/localidades/{id}/proteccion/{id_grupo}` | Actualiza un grupo vulnerable específico |
| `DELETE` | `/edan/localidades/{id}/proteccion/{id_grupo}` | Elimina un grupo vulnerable específico |

**Nota:** Todos los endpoints usan JSON (no multipart/form-data). No hay fotos ni coordenadas en esta sección.

---

## Campos del Schema `ProteccionCreate`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id_seccion` | string | No | ID único offline (generado por cliente). Ej: `po_1693012345_abc12345` |
| `id_grupo_vulnerable_catalogo` | int | **Sí** | FK a `edan.grupo_vulnerable` (1-8) |
| `mujeres` | int | No | Cantidad de mujeres (default: 0) |
| `hombres` | int | No | Cantidad de hombres (default: 0) |
| `total` | int | No | Total personas (default: 0) |
| `apoyo_psicologico` | bool | No | Requiere apoyo psicológico |
| `reposicion_documentos` | bool | No | Requiere reposición de documentos |
| `observaciones` | string | No | Observaciones libres |

---

## Ejemplos de Uso

### 1. Listar grupos vulnerables de una localidad

```bash
curl -X GET "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer TU_TOKEN"
```

**Respuesta:**
```json
{
  "message": "Grupos vulnerables listados",
  "data": [
    {
      "id_grupo_vulnerable": 1,
      "id_grupo_vulnerable_catalogo": 1,
      "id_seccion": "po_1693012345_abc12345",
      "grupo": {
        "id": 1,
        "codigo": "adultos_mayores",
        "nombre": "Adultos mayores",
        "orden": 1,
        "activo": true
      },
      "mujeres": 15,
      "hombres": 12,
      "total": 27,
      "apoyo_psicologico": true,
      "reposicion_documentos": false,
      "observaciones": "Requieren medicamentos"
    }
  ],
  "total": 1
}
```

---

### 2. Crear grupo vulnerable con `id_seccion`

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_1693012345_abc12345",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 15,
    "hombres": 12,
    "total": 27,
    "apoyo_psicologico": true,
    "reposicion_documentos": false,
    "observaciones": "Requieren medicamentos"
  }'
```

**Respuesta (201):**
```json
{
  "message": "Grupo vulnerable creado/actualizado",
  "data": {
    "id_grupo_vulnerable": 1,
    "id_grupo_vulnerable_catalogo": 1,
    "id_seccion": "po_1693012345_abc12345",
    "grupo": {
      "id": 1,
      "codigo": "adultos_mayores",
      "nombre": "Adultos mayores",
      "orden": 1,
      "activo": true
    },
    "mujeres": 15,
    "hombres": 12,
    "total": 27,
    "apoyo_psicologico": true,
    "reposicion_documentos": false,
    "observaciones": "Requieren medicamentos"
  }
}
```

---

### 3. Actualizar grupo vulnerable con el mismo `id_seccion` (UPSERT)

Si envías el mismo `id_seccion`, se actualiza en lugar de duplicar:

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_1693012345_abc12345",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 20,
    "hombres": 15,
    "total": 35,
    "apoyo_psicologico": true,
    "reposicion_documentos": true,
    "observaciones": "Datos actualizados"
  }'
```

**Resultado:** Se actualiza la fila existente (no se crea otra).

---

### 4. Actualizar grupo específico por ID

```bash
curl -X PUT "http://localhost:8000/api/v1/edan/localidades/199/proteccion/1" \
  -H "Authorization: Bearer TU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_1693012345_abc12345",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 25,
    "hombres": 18,
    "total": 43,
    "observaciones": "Actualizado vía PUT"
  }'
```

---

### 5. Eliminar grupo vulnerable

```bash
curl -X DELETE "http://localhost:8000/api/v1/edan/localidades/199/proteccion/1" \
  -H "Authorization: Bearer TU_TOKEN"
```

**Respuesta:**
```json
{
  "message": "Grupo vulnerable eliminado"
}
```

---

## Flujo Completo: Crear → Actualizar → Listar → Eliminar

```bash
# 1. Login
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login \
  -X POST -H "Content-Type: application/json" \
  -d '{"usuario":"7051296","contrasena":"12345678"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 2. Crear grupo Adultos Mayores
curl -s -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_test_001",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 10,
    "hombres": 8,
    "total": 18
  }'

# 3. Crear grupo Mujeres embarazadas
curl -s -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_test_002",
    "id_grupo_vulnerable_catalogo": 2,
    "mujeres": 5,
    "hombres": 0,
    "total": 5,
    "observaciones": "Primer trimestre"
  }'

# 4. Listar todos los grupos
curl -s "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer $TOKEN"

# 5. Actualizar el primer grupo (UPSERT por id_seccion)
curl -s -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_test_001",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 12,
    "hombres": 10,
    "total": 22,
    "observaciones": "Actualizado"
  }'

# 6. Eliminar el segundo grupo
curl -s -X DELETE "http://localhost:8000/api/v1/edan/localidades/199/proteccion/2" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Sync con Protección

Los endpoints dedicados son para CRUD individual. Para sync batch, usa el endpoint existente:

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-sync-001",
      "id_usuario": 30,
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "localidad": "Test Sync Protección",
      "fecha_llenado": "2026-08-27",
      "total_poblacion_afectada": 50,
      "proteccion": [
        {
          "id_seccion": "po_sync_001",
          "id_grupo_vulnerable_catalogo": 1,
          "mujeres": 10,
          "hombres": 8,
          "total": 18
        },
        {
          "id_seccion": "po_sync_002",
          "id_grupo_vulnerable_catalogo": 3,
          "mujeres": 5,
          "hombres": 3,
          "total": 8
        }
      ]
    }]
  }'
```

---

## Catálogo de Grupos Vulnerables

| ID | Código | Nombre | Orden |
|----|--------|--------|-------|
| 1 | adultos_mayores | Adultos mayores | 1 |
| 2 | mujeres_embarazadas | Mujeres embarazadas | 2 |
| 3 | ninos_0_5 | Niños 0-5 años | 3 |
| 4 | ninos_6_12 | Niños 6-12 años | 4 |
| 5 | adolescentes | Adolescentes 13-17 años | 5 |
| 6 | personas_discapacidad | Personas con discapacidad | 6 |
| 7 | personas_enfermas | Personas enfermas crónicas | 7 |
| 8 | otros_grupos | Otros grupos vulnerables | 8 |

---

## Notas Técnicas

- **UPSERT por `id_seccion`:** Si envías un `id_seccion` que ya existe, se actualiza la fila en lugar de crear otra.
- **Sin fotos ni coordenadas:** Esta sección NO tiene campos `fotografia`, `coordenada_lat`, `coordenada_lon`.
- **id_seccion en sync:** El campo `id_seccion` es opcional pero recomendado para offline-first.
- **Cálculo automático de total:** El backend NO calcula `total = mujeres + hombres` automáticamente. El cliente debe enviar el total.
