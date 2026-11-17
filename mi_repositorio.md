# Mi Repositorio — APIs de subida y consulta de documentos

Repositorio compartido de documentos PDF (`repositorio.documentos`). Soporta tres orígenes; el **origen se asigna automáticamente según la URL** de subida (el cliente no lo envía).

- **Subida municipal**: los documentos quedan vinculados a un municipio (`id_departamento/provincia/municipio`).
- **Consulta vista nacional**: el listado general mezcla todos los orígenes y se filtra por geografía, tipo, fechas, etc.

| Ruta de subida (POST) | Origen | Vínculo |
|---|---|---|
| `/api/v2/repositorio/edan/{id_edan}/documentos` (existente, sin cambios) | `EDAN` | `id_edan` |
| `/api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` (existente, sin cambios) | `RIDA` | `id_evento_rida` + `id_edan` heredado |
| `/api/v2/repositorio/documentos` (**nueva**) | `DOC_PRECEDENTE` | sin `id_edan`/`id_evento_rida` (respaldo municipal) |

> Todos los endpoints requieren autenticación (`Authorization: Bearer <token>`) y el módulo REPOSITORIO según corresponda. `id_usuario_subio` se registra automáticamente desde el usuario autenticado.

---

## 1. APIs de subida (PDF)

- **Content-Type:** `multipart/form-data`
- **Archivo:** solo PDF (MIME `application/pdf`, `.pdf`, máx. 50 MB). Si el PDF ≤ 20 MB se valida la firma digital (AGETIC) y se guarda en `tiene_firma_digital`/`resultado_firma`.
- **Campos comunes (misma estructura en las 3 APIs):**

| Campo | Tipo | Req. | Descripción |
|---|---|---|---|
| `file` | archivo (PDF) | sí | Documento PDF |
| `id_tipo_documento` | int | sí | Tipo del catálogo (`repositorio.tipo_documento`, activo) |
| `id_departamento` | int | sí | Departamento (geografía) |
| `id_provincia` | int | sí | Provincia (geografía) |
| `id_municipio` | int | sí | Municipio (geografía) |
| `fecha_documento` | string | sí | Fecha del documento (`YYYY-MM-DD`) |
| `nombre_documento` | string | sí | Nombre/título del documento |
| `observaciones` | string | no | **Texto libre** (opcional) |

### 1.1 EDAN (existente, sin cambios de contrato)
`POST /api/v2/repositorio/edan/{id_edan}/documentos` → `origen=EDAN`

```bash
curl -X POST "$API/api/v2/repositorio/edan/123/documentos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@informe_edan.pdf" \
  -F "id_tipo_documento=1" \
  -F "id_departamento=2" -F "id_provincia=201" -F "id_municipio=20101" \
  -F "fecha_documento=2026-11-10" \
  -F "nombre_documento=Informe EDAN zona norte" \
  -F "observaciones=Texto libre opcional"
```

### 1.2 RIDA (existente, sin cambios de contrato)
`POST /api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` → `origen=RIDA` (`id_edan` heredado del evento)

```bash
curl -X POST "$API/api/v2/repositorio/rida/eventos/45/documentos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@respaldo_rida.pdf" \
  -F "id_tipo_documento=3" \
  -F "id_departamento=2" -F "id_provincia=201" -F "id_municipio=20101" \
  -F "fecha_documento=2026-11-12" \
  -F "nombre_documento=Acta RIDA evento 45" \
  -F "observaciones=Texto libre opcional"
```

### 1.3 DOC_PRECEDENTE — respaldo municipal (nueva)
`POST /api/v2/repositorio/documentos` → `origen=DOC_PRECEDENTE` (sin `id_edan`/`id_evento_rida`)

Subida municipal para documentos fuera de EDAN/RIDA. Mismos campos que las anteriores.

```bash
curl -X POST "$API/api/v2/repositorio/documentos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@convenio_municipal.pdf" \
  -F "id_tipo_documento=5" \
  -F "id_departamento=2" -F "id_provincia=201" -F "id_municipio=20101" \
  -F "fecha_documento=2026-11-15" \
  -F "nombre_documento=Convenio interinstitucional" \
  -F "observaciones=Respaldo municipal, texto libre"
```

### Respuesta de subida (ejemplo, `201`)
```json
{
  "success": true,
  "message": "Documento subido correctamente",
  "data": {
    "id_documento": 987,
    "origen": "DOC_PRECEDENTE",
    "id_edan": null,
    "id_evento_rida": null,
    "id_departamento": 2,
    "id_provincia": 201,
    "id_municipio": 20101,
    "id_usuario_subio": 29,
    "id_tipo_documento": 5,
    "nombre_documento": "Convenio interinstitucional",
    "fecha_documento": "2026-11-15",
    "observaciones": "Respaldo municipal, texto libre",
    "tiene_firma_digital": false,
    "cantidad_firmas": 0,
    "firma_validada": false
  }
}
```

---

## 2. Consulta general — vista nacional (nueva)

`GET /api/v2/repositorio/documentos`

Lista **EDAN + RIDA + DOC_PRECEDENTE** (vista nacional) con filtros geográficos.
- **Orden:** más recientes primero (`fecha_documento DESC NULLS LAST, fecha_subida DESC`).
- **Paginación (skill cantidad → paginación → todos → filtros):**
  - `limit` (def. `50`, máx. `200`): cantidad de resultados (los más recientes).
  - `skip` (def. `0`): offset, para paginar junto a `limit`.
  - `todos=true`: devuelve el conjunto completo sin paginar (ignora `limit`/`skip`).
- **Respuesta:** `{"success": true, "message": "Documentos listados", "data": [...], "total": N}` donde `total` es el total **sin paginar** con los mismos filtros.

### Filtros opcionales

| Filtro | Tipo | Descripción |
|---|---|---|
| `origen` | `EDAN` \| `RIDA` \| `DOC_PRECEDENTE` | Origen del documento |
| `id_departamento` | int | Filtro geográfico: departamento |
| `id_provincia` | int | Filtro geográfico: provincia |
| `id_municipio` | int | Filtro geográfico: municipio |
| `id_edan` | int | EDAN asociado |
| `id_evento_rida` | int | Evento RIDA asociado |
| `id_tipo_documento` | int | Tipo de documento (catálogo) |
| `id_usuario_subio` | int | Usuario que subió |
| `fecha_desde` | `YYYY-MM-DD` | `fecha_documento` desde |
| `fecha_hasta` | `YYYY-MM-DD` | `fecha_documento` hasta |
| `q` | string | Búsqueda por nombre (`ILIKE` en `nombre_documento`/`nombre_original`) |
| `tiene_firma_digital` | bool | Con/sin firma digital |
| `include_inactive` | bool | Incluir inactivos (`false` por defecto) |

### Ejemplos

```bash
# 1) Últimos 20 de todos los orígenes (vista nacional)
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?limit=20&skip=0"

# 2) Solo DOC_PRECEDENTE de un municipio
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?origen=DOC_PRECEDENTE&id_municipio=20101&limit=50"

# 3) Todo un departamento (mezcla EDAN + RIDA + DOC_PRECEDENTE)
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?id_departamento=2&limit=50&skip=0"

# 4) RIDA de una provincia, por tipo y rango de fechas
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?origen=RIDA&id_provincia=201&id_tipo_documento=3&fecha_desde=2026-01-01&fecha_hasta=2026-12-31"

# 5) Búsqueda por nombre en un municipio + paginación
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?q=convenio&id_municipio=20101&limit=20&skip=20"

# 6) TODOS (sin paginar) los de un municipio
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?id_municipio=20101&todos=true"
```

Ejemplo de respuesta:
```json
{
  "success": true,
  "message": "Documentos listados",
  "data": [
    {
      "id_documento": 987,
      "origen": "DOC_PRECEDENTE",
      "id_edan": null,
      "id_evento_rida": null,
      "id_departamento": 2,
      "id_provincia": 201,
      "id_municipio": 20101,
      "id_tipo_documento": 5,
      "nombre_documento": "Convenio interinstitucional",
      "fecha_documento": "2026-11-15",
      "id_usuario_subio": 29,
      "tiene_firma_digital": false,
      "cantidad_firmas": 0,
      "firma_validada": false
    }
  ],
  "total": 134
}
```

---

## 3. Otros endpoints de consulta/gestión (compatibilidad)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v2/repositorio/documentos/filtrar` | Filtros por metadata (incluye `DOC_PRECEDENTE`, `total` correcto). Compatible con clientes existentes. |
| `GET` | `/api/v2/repositorio/documentos/buscar?q=...` | Búsqueda por nombre (`ILIKE`), con `id_municipio`, `origen`, `limit/skip/todos`. |
| `GET` | `/api/v2/repositorio/edan/{id_edan}/documentos` | Documentos de un EDAN (filtros `id_tipo_documento`, `origen` EDAN/RIDA, paginación). |
| `GET` | `/api/v2/repositorio/rida/eventos/{id_evento_rida}/documentos` | Documentos de un evento RIDA. |
| `GET` | `/api/v2/repositorio/documentos/{id_documento}` | Metadata de un documento. |
| `GET` | `/api/v2/repositorio/documentos/{id_documento}/descargar` | Descarga el PDF (`application/pdf`). |
| `PUT` | `/api/v2/repositorio/documentos/{id_documento}` | Actualiza `observaciones` (texto libre) y/o `activo`. |
| `DELETE` | `/api/v2/repositorio/documentos/{id_documento}` | Soft delete (`activo=false`). |
| `DELETE` | `/api/v2/repositorio/documentos/{id_documento}/hard` | Eliminación física (BD + archivo). |

**Restricción (solo `DOC_PRECEDENTE`, tercera API):** editar (`PUT`) y eliminar (`DELETE`/`/hard`) solo lo puede hacer el **usuario que subió** el documento y únicamente dentro de las **72 horas** desde la subida; fuera de esas condiciones responde **403**. **No aplica** a documentos `EDAN` ni `RIDA`.

> Los catálogos de tipos (`GET/POST/PUT/DELETE /api/v2/repositorio/tipos`) se mantienen y se devuelven completos.

## 4. Notas
- `observaciones` es **texto libre** (opcional) en subida y en actualización.
- `DOC_PRECEDENTE`: solo el usuario que subió puede editar/eliminar (soft y hard) y dentro de 72 h desde la subida (403 si no). No aplica a `EDAN`/`RIDA`.
- La subida `DOC_PRECEDENTE` es **municipal** (vinculada al municipio enviado) y la consulta es de **vista nacional** con filtros geográficos.
- Requiere migración `v2.65.0_repositorio_origen_doc_precedente.sql` (y su espejo en `despliegue/migraciones/`) aplicada en la BD.
- Handoff técnico de replicación: `cambios_replicacion/REPOSITORIO_doc_precedente_v265.md`.
