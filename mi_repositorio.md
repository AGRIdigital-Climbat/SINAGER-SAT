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

**Campo extra opcional `codigo_documento`** (≤64): clave de rastreo/expediente, el
equivalente municipal de `id_edan`/`id_evento_rida`. No es única: **varios documentos
pueden compartir el mismo código** para anexarse al mismo expediente. Se normaliza a
MAYÚSCULAS. Si **no** la envías, la API la **autogenera** (`RES-{codigo_ine}-{año}-{sec}`,
p. ej. `RES-070101-2026-00002`) y la devuelve en la respuesta: úsala en subidas
posteriores para agrupar.

```bash
curl -X POST "$API/api/v2/repositorio/documentos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@convenio_municipal.pdf" \
  -F "id_tipo_documento=5" \
  -F "id_departamento=2" -F "id_provincia=201" -F "id_municipio=20101" \
  -F "fecha_documento=2026-11-15" \
  -F "nombre_documento=Convenio interinstitucional" \
  -F "observaciones=Respaldo municipal, texto libre" \
  -F "codigo_documento=RES-020101-2026-00001"   # opcional: anexa a ese expediente
```

### Respuesta de subida (ejemplo, `201`)
```json
{
  "success": true,
  "message": "Documento subido correctamente",
  "data": {
    "id_documento": 987,
    "origen": "DOC_PRECEDENTE",
    "codigo_documento": "RES-020101-2026-00001",
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

## 2. Consulta general — vista nacional (agrupada por expediente)

`GET /api/v2/repositorio/documentos`

Lista **EDAN + RIDA + DOC_PRECEDENTE** (vista nacional) con filtros geográficos.
- **Por defecto `modo=agrupado`**: devuelve **un objeto por grupo/expediente**. Regla
  de agrupación (fuente única en el servidor):
  | tipo | agrupador | nota |
  |---|---|---|
  | `RIDA` | `id_evento_rida` | se mantiene RIDA aunque el documento herede `id_edan` (no se mezcla con el grupo EDAN) |
  | `EDAN` | `id_edan` | formulario padre del municipio |
  | `DOC_PRECEDENTE` | `codigo_documento` | expediente municipal; si faltara el código, el doc forma su propio grupo |
- Cada grupo trae: `tipo`, **`clave` = el código REAL del grupo** (`codigo_edan`
  para EDAN → `070101/2026/003`; `rida.evento_rida.codigo` para RIDA →
  `070101/2026/003-R`; `codigo_documento` tal cual para DOC_PRECEDENTE →
  `RES-070101-2026-00002` o el que el municipio haya puesto), `etiqueta`
  (igual que `clave`), `id_edan`, `id_evento_rida`, `codigo_documento`, geografía
  del grupo, **`total_documentos`**, `fecha_documento_max`, `fecha_subida_max`.
  (Los identificadores técnicos `ED-79`/`EV-15` ya NO se devuelven; solo
  quedarían como fallback si un padre no tuviera código.)
- **Copias idénticas entre grupos (hash exacto, sin API extra)**: cada grupo incluye
  `documentos_compartidos` (cuántos de sus documentos tienen el mismo `hash_sha256`
  en OTRO grupo) y `comparte_con`: grupos hermanos con `tipo`, `clave`, `etiqueta`,
  `documentos_comunes` y los `documentos` exactos (`id_documento`,
  `nombre_documento`, `hash_sha256` de 16 caracteres). El mismo PDF subido a un EDAN
  y a un expediente municipal queda identificado en ambos grupos; dos copias dentro
  del MISMO grupo no cuentan. Se calcula contra todos los docs activos, aunque la
  lista esté filtrada/paginada.
- **`total` = nº de GRUPOS** sin paginar con los mismos filtros; `limit/skip` paginan grupos.
- **`modo=plano`**: comportamiento clásico, lista de documentos individuales
  (respuesta `Documentos listados`, `total` = nº de docs).
- **Drill-down de un grupo** (sin endpoint nuevo): `?modo=plano&codigo_grupo=<código visible>`
  (sirve para los 3 tipos, admite minúsculas) o los filtros técnicos
  `id_evento_rida=15` / `id_edan=79` / `codigo_documento=RES-...`.
  También `GET /documentos/codigo/{código}` con el código completo tal cual
  (usa `:path`, los `/` del código como `070101/2026/003-R` van sin escapar).
- **Orden:** más recientes primero (grupos por su documento más nuevo).

Ejemplo (respuesta `modo=agrupado`):
```json
{
  "success": true, "message": "Grupos de documentos listados", "total": 3,
  "data": [
    {"tipo": "DOC_PRECEDENTE", "clave": "PRUEBA-AGRUP-2026-001",
     "etiqueta": "PRUEBA-AGRUP-2026-001",
     "id_edan": null, "id_evento_rida": null,
     "codigo_documento": "PRUEBA-AGRUP-2026-001",
     "id_departamento": 7, "id_provincia": 701, "id_municipio": 70101,
     "total_documentos": 2, "fecha_documento_max": "2026-11-17",
     "fecha_subida_max": "2026-11-17T03:12:44",
     "documentos_compartidos": 1,
     "comparte_con": [
       {"tipo": "EDAN", "clave": "ED-79", "etiqueta": "EDAN 070101/2026/003",
        "documentos_comunes": 1,
        "documentos": [{"id_documento": 373,
                        "nombre_documento": "Declaratoria 034/2026 (copia EDAN)",
                        "hash_sha256": "b4b2f45d041f9d89"}]} ]},
    {"tipo": "RIDA", "clave": "EV-15", "etiqueta": "EVENTO RIDA 15",
     "id_edan": 79, "id_evento_rida": 15, "codigo_documento": null,
     "total_documentos": 2, "fecha_documento_max": "2026-10-09"},
    {"tipo": "EDAN", "clave": "ED-79", "etiqueta": "EDAN 070101/2026/003",
     "id_edan": 79, "id_evento_rida": null, "codigo_documento": null,
     "total_documentos": 2, "fecha_documento_max": "2026-09-10"}
  ]
}
```
> Los 2 RIDA comparten `id_edan=79` con el grupo EDAN y aun así figuran **solo** como
> RIDA: la agrupación prioriza `id_evento_rida`, como se acordó.

### Filtros opcionales

| Filtro | Tipo | Descripción |
|---|---|---|
| `origen` | `EDAN` \| `RIDA` \| `DOC_PRECEDENTE` | Origen del documento |
| `codigo_documento` | string ≤64 | Expediente/rastreo de DOC_PRECEDENTE (exacto, sin distinguir mayúsculas) |
| `codigo_grupo` | string ≤80 | **Código real del grupo en cualquier origen** (codigo_edan, código de evento RIDA o codigo_documento); respeta 'id_edan gana': cada código empareja solo su propio origen |
| `id_departamento` | int | Filtro geográfico: departamento |
| `id_provincia` | int | Filtro geográfico: provincia |
| `id_municipio` | int | Filtro geográfico: municipio |
| `id_edan` | int | **Solo documentos de origen EDAN** de ese EDAN (regla 'id_edan gana'). Los RIDA que heredan ese `id_edan` NO se incluyen; para ver TODO lo del EDAN usa `GET /edan/{id_edan}/documentos` |
| `id_evento_rida` | int | Solo documentos RIDA de ese evento |
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

# 7) Documentos sueltos (comportamiento clásico)
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?modo=plano&limit=20"

# 8) Drill-down de un grupo: anexos del mismo evento RIDA
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v2/repositorio/documentos?modo=plano&id_evento_rida=15"
```

Ejemplo de respuesta (`modo=plano`; ver arriba el ejemplo de `modo=agrupado`):
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
| `GET` | `/api/v2/repositorio/documentos/codigo/{codigo_documento}` | **Todos los documentos de un expediente** (DOC_PRECEDENTE). El código se normaliza (admite minúsculas); `limit`/`skip`/`todos`; solo activos. |
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
- `codigo_documento` (expediente): solo lo usan los `DOC_PRECEDENTE`; la 3ª subida lo
  acepta o lo autogenera (`RES-{codigo_ine}-{año}-{sec}`), y es la clave para **agrupar
  varios PDFs en un mismo expediente** (varios documentos → mismo código). Se consulta
  con `GET /documentos?codigo_documento=...` o `GET /documentos/codigo/{codigo}`.
  EDAN/RIDA lo devuelven `null` (sus padres son `id_edan`/`id_evento_rida`).
- `DOC_PRECEDENTE`: solo el usuario que subió puede editar/eliminar (soft y hard) y dentro de 72 h desde la subida (403 si no). No aplica a `EDAN`/`RIDA`.
- Verificado en dev (2026-11-17): subida municipal → `origen=DOC_PRECEDENTE`, mezcla en la vista nacional (`total` con EDAN/RIDA), filtros por departamento/provincia/municipio/tipo/fecha/`q`/`todos`, y `403` tanto a usuario distinto del dueño como al dueño pasadas las 72 h. Detalle en `cambios_replicacion/REPOSITORIO_doc_precedente_v265.md` §7.1.
- Agrupación probada (2026-11-17): 2 subidas sin código → códigos distintos; 3ª subida con el código de la 1ª en minúsculas → quedó en el mismo expediente; `/codigo/...` y filtro `?codigo_documento` devuelven el grupo; PUT del dueño reasigna el expediente y PUT de otro usuario → 403. Detalle en `cambios_replicacion/REPOSITORIO_codigo_documento_v267.md`.
- La subida `DOC_PRECEDENTE` es **municipal** (vinculada al municipio enviado) y la consulta es de **vista nacional** con filtros geográficos.
- Requiere migraciones `v2.65.0_repositorio_origen_doc_precedente.sql` y `v2.67.0_repositorio_codigo_documento.sql` (con sus espejos en `despliegue/migraciones/`) aplicadas en la BD.
- Handoff técnico de replicación: `cambios_replicacion/REPOSITORIO_doc_precedente_v265.md` y `cambios_replicacion/REPOSITORIO_codigo_documento_v267.md`.
