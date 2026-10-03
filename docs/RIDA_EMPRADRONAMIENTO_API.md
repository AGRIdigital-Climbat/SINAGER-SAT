# RIDA Empadronamiento — API v2

> **Versión:** v1.4.0 · **Base URL:** `https://<host>` · **Prefijo V2:** `/api/v2`
> **Swagger interactivo:** `http://<host>:8000/docs/v2` · **OpenAPI JSON v2:** `GET http://<host>:8000/openapi.v2.json`
> **Audiencia:** app móvil (Flutter/offline) y web — desarrolladores del módulo `rida_empadronamiento`.
> **Relacionado:** [`RIDA_BD.md`](RIDA_BD.md) (esquema `rida`) y [`RIDA_FLUJO_GENERAL.md`](RIDA_FLUJO_GENERAL.md) (aprobaciones y flujo).
> **Aplicación/pérmisos:** `usuarios.aplicacion` RIDA (id 2) — matriz en `usuarios.permiso` (seeds de la migración v2.17.0).

---

## rida_empadronamiento

### 1. Alcance: tablas expuestas (solo las trabajadas)

| Tabla (`rida.*`) | Tipo | Notas |
|---|---|---|
| `formulario_rida` | Datos (CRUD) | Cabecera del empadronamiento. 1 formulario por localidad (UNIQUE `id_edan_localidad`). Requiere EDAN aprobado (estado 3 ó 5). |
| `familia` | Datos (CRUD) | Hijo de `formulario_rida`. UPSERT por `id_familia_off`. |
| `integrante` | Datos (CRUD) | Hijo de `familia`. UPSERT por `id_integrante_off`. |
| `ubicacion_familia` | Datos (CRUD) | Hijo de `familia`. Coordenadas GPS + tipo de albergue. UPSERT por `id_ubicacion_off`. |
| `cat_estado_formulario` | Catálogo (GET) | PENDIENTE(1), EN_PROCESO(2), CERRADO(3). |
| `cat_tipo_albergue` | Catálogo (GET) | Tipos de albergue (lo puebla el usuario). |
| `cat_parentesco` | Catálogo (GET) | FK de `integrante.id_parentesco`. |
| `cat_tipo_discapacidad` | Catálogo (GET) | FK de `integrante.id_discapacidad`. |

> **Fuera de alcance:** `cat_enfermedad_cronica` (FK de `integrante.id_enfermedad` se expone como INTEGER sin catálogo) y el resto de tablas del esquema `rida` (v2.17.0).

### 2. Autenticación y permisos

- Todos los endpoints requieren `Authorization: Bearer <JWT>` (ver `POST /api/v2/auth/login`).
- Nivel router: `module_permiso("RIDA")` — GET libre con token; POST/PUT/DELETE exigen la acción en la matriz RIDA.
- Nivel escritura: `require_rol(1, 2, 6, 7)` (superadmin, admin, UGR Municipio, Responsable Local).
- Scope geográfico forzado en listados:
  - **6/7 (UGR Mun. / Resp. Local):** solo **sus** formularios (`id_usuario` del token).
  - **8 (Alcalde):** todo su **municipio** (`id_municipio` asignado).
  - **5/9 (DGR / VIDECI Deptal.):** todo su **departamento**.
  - **1-4 (nacional):** todo el país; honra filtros de geo/query opcionales.
- El scope se resuelve por **JOIN a `edan.edan_localidades`** (ya no hay `id_municipio`/`id_departamento` en `formulario_rida`).

### 3. Rutas

**Prefijo de grupo:** `/api/v2/rida/empadronamiento` — Swagger: **RIDA > Empadronamiento > \***

#### Catálogos (GET, lectura)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/cat-tipo-albergue` | Tipos de albergue (`id_cat_tipo_albergue`, `nombre`). |
| GET | `/cat-estado-formulario` | Estados de formulario (código/nombre/orden/activo). |
| GET | `/cat-parentesco` | Parentescos activos. |
| GET | `/cat-tipo-discapacidad` | Discapacidades activas (con `requiere_movilidad`). |

#### Formularios

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/formularios` | Lista paginada + filtros (`id_edan`, `id_edan_localidad`, `id_estado`, `id_usuario`, `id_departamento`, `id_municipio`, `skip`, `limit`). |
| GET | `/formularios/mis` | Propios (6/7), municipio forzado (8), departamento forzado (5/9), todo el país (1-4). |
| GET | `/formularios/{id_formulario}` | Árbol completo: familias + integrantes + ubicaciones. |
| POST | `/formularios` | Crea el empadronamiento (1 por localidad). **Valida EDAN aprobado (estado 3/5).** |
| PUT | `/formularios/{id_formulario}` | Actualiza `id_edan` / `id_estado`. |
| DELETE | `/formularios/{id_formulario}` | Elimina con familias/integrantes/ubicaciones. Solo 1-2 o propios (6/7). |

Payload `POST /formularios`:
```json
{
  "id_edan_localidad": 123,
  "id_edan": 5,
  "id_estado": 1
}
```
- `id_edan` opcional: si falta se toma del EDAN de la localidad.
- `id_estado` opcional (default `1` = PENDIENTE).
- Errores 400: localidad inexistente, EDAN no aprobado, localidad ya empadronada.

#### Familias

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/formularios/{id_formulario}/familias` | Familias del formulario (con nidos). |
| GET | `/familias/{id_familia}` | Familia con `integrantes[]` y `ubicaciones[]`. |
| POST | `/formularios/{id_formulario}/familias` | Crea familia (**UPSERT por `id_familia_off`**). |
| PUT | `/familias/{id_familia}` | Actualiza familia. |
| DELETE | `/familias/{id_familia}` | Elimina con integrantes y ubicaciones. |

Payload `POST /familias`:
```json
{
  "id_familia_off": "fam-8f3a-4b21",
  "id_edan_localidad": null,
  "id_necesidad": 2,
  "observacion": "Familia de 5 miembros"
}
```
> El `id_formulario` se toma de la ruta.

#### Integrantes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/familias/{id_familia}/integrantes` | Integrantes de la familia (jefe primero). |
| GET | `/integrantes/{id_integrante}` | Integrante con nombres de catálogos. |
| POST | `/familias/{id_familia}/integrantes` | Crea integrante (**UPSERT por `id_integrante_off`**). |
| PUT | `/integrantes/{id_integrante}` | Actualiza integrante. |
| DELETE | `/integrantes/{id_integrante}` | Elimina integrante. |

Payload `POST /integrantes`:
```json
{
  "id_integrante_off": "int-7c2a-991d",
  "nombre": "María",
  "apellido": "Quispe",
  "sexo": "F",
  "fecha_nacimiento": "1985-03-12",
  "numero_ci": "1234567",
  "id_parentesco": 1,
  "es_jefe": true,
  "gestante_semanas": 0,
  "lactante_meses": 0,
  "id_discapacidad": 1,
  "id_enfermedad": null,
  "telefono": "71234567"
}
```
> Reglas: `sexo` M/F; `gestante_semanas` 0-45; `lactante_meses` 0-36; solo un `es_jefe=true` por familia (el servidor limpia los demás).

#### Ubicaciones (GPS)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/familias/{id_familia}/ubicaciones` | Ubicaciones de la familia. |
| GET | `/ubicaciones/{id_ubicacion}` | Ubicación. |
| POST | `/familias/{id_familia}/ubicaciones` | Crea ubicación (**UPSERT por `id_ubicacion_off`**). |
| PUT | `/ubicaciones/{id_ubicacion}` | Actualiza coordenadas/tipo albergue. |
| DELETE | `/ubicaciones/{id_ubicacion}` | Desvincula de la familia y elimina. |

Payload `POST /ubicaciones`:
```json
{
  "id_ubicacion_off": "ubi-5513-aa20",
  "coordenada_lat": -17.78629,
  "coordenada_lon": -63.18117,
  "id_cat_tipo_albergue": 1
}
```
> Al crear la primera ubicación, el servidor enlaza `familia.id_ubicacion_familia` automáticamente.

#### Sync móvil (offline-first)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/sync` | Push batch; nunca falla completo; devuelve mapeos `off → server`. |

Payload `POST /sync`:
```json
{
  "formularios": [ { "id_edan_localidad": 123, "id_edan": 5, "id_estado": 1 } ],
  "familias":  [ { "id_familia_off": "fam-a", "id_edan_localidad": 123, "observacion": "" } ],
  "integrantes": [ { "id_integrante_off": "int-a", "id_familia_off": "fam-a", "nombre": "María", "apellido": "Quispe", "es_jefe": true } ],
  "ubicaciones": [ { "id_ubicacion_off": "ubi-a", "id_familia_off": "fam-a", "coordenada_lat": -17.78629, "coordenada_lon": -63.18117 } ]
}
```

Reglas:
- **Formulario:** identificado por `id_edan_localidad` (UNIQUE). No tiene `*_off`, el identificador offline natural es la localidad.
- **Familia/Integrante/Ubicación:** UPSERT por `id_*_off`. Si ya existe, actualiza (idempotente).
- **Vínculos offline:** `id_familia_off` en integrantes y ubicaciones resuelve el `id_familia` del servidor (debe llegar en el mismo lote o previo).
- **Resultado:** cada ítem devuelve su mapeo (ej. `id_familia_off → id_familia`) para que el dispositivo reenlace sus tablas locales; los fallos van en `errores[]` con `aplicado: false`.

```json
{
  "success": true,
  "message": "Empadronamiento sincronizado correctamente",
  "data": {
    "formularios": [ { "id_edan_localidad": 123, "id_formulario": 9, "aplicado": true, "data": { ... } } ],
    "familias": [ { "id_familia_off": "fam-a", "id_familia": 4, "aplicado": true, "data": { ... } } ],
    "integrantes": [ { "id_integrante_off": "int-a", "id_integrante": 7, "aplicado": true, "data": { ... } } ],
    "ubicaciones": [ { "id_ubicacion_off": "ubi-a", "id_ubicacion_familia": 3, "aplicado": true, "data": { ... } } ],
    "errores": []
  }
}
```

### 4. Auditoría

El middleware de auditoría mapea `/api/v2/rida/` → **aplicación RIDA (id 2)** (`api/audit.py` → `URL_APP_MAP`). Todo POST/PUT/DELETE exitoso queda registrado en `usuarios.auditoria` con la acción correspondiente.

### 5. Verificación rápida

```bash
bash start_api.sh                    # http://10.10.0.24:8000/docs/v2
# Swagger: grupo "RIDA > Empadronamiento"
curl -H "Authorization: Bearer <token>" \
     "http://10.10.0.24:8000/api/v2/rida/empadronamiento/cat-estado-formulario"
```