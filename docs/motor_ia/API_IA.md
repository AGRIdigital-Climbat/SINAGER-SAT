# Documentación operativa de MotorIA – SINAGERSAT

Fecha: 2026-11-04
Servicio API: `sinagersat-api.service` con `3` workers
Servicio embeddings: `motoria-embeddings.service` con `2` workers en `127.0.0.1:8001`
Prefijo API: `/api/v2/motor-ia`
Esquema PostgreSQL: `motor_ia`
Embeddings: servicio local FastEmbed ONNX con `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `384D`

## Estado actual

El módulo MotorIA ya está integrado en la API de SINAGERSAT.

Estado de datos:

- `motor_ia.tipos_documento`: catálogo inicial con 19 tipos.
- `motor_ia.documentos`: 0.
- `motor_ia.chunks`: 0.
- `motor_ia.grupo_documentos`: 0.
- `motor_ia.proveedores_llm`: 0.
- `motor_ia.uso_llm`: 0.

Estado funcional:

- Búsqueda semántica: habilitada con embeddings locales vía `motoria-embeddings`.
- Subida/indexación de PDF: habilitada.
- Verificación de calidad: habilitada.
- Chat con respuesta generada por LLM: pendiente de registrar/probar un proveedor LLM.
- Voz: requiere LLM para generar respuesta; Whisper está instalado, pero el modelo se descarga en el primer uso.

## Arquitectura actual de embeddings

```text
sinagersat-api.service
  3 workers en 0.0.0.0:8000
  no carga modelos de embeddings
  usa EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1

motoria-embeddings.service
  2 workers en 127.0.0.1:8001
  carga FastEmbed ONNX
  modelo: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  dimension: 384D
```

El servicio interno expone `/v1/embeddings` compatible con OpenAI para que
`api/motor_ia/core/embeddings.py` lo consuma como `EMBEDDINGS_MODE=external`.
No debe exponerse públicamente; solo escucha en `127.0.0.1`.

## Autenticación

Las operaciones de lectura son públicas.

Las operaciones de escritura/administración requieren:

```http
X-API-Key: <API_AUTH_TOKEN>
```

La variable `API_AUTH_TOKEN` está definida en `.env`.

Para cargarla en la shell local sin escribirla en un documento compartido:

```bash
export API_AUTH_TOKEN=$(awk -F= '/^API_AUTH_TOKEN=/{print $2}' .env)
```

Para verla localmente solo cuando haga falta:

```bash
awk -F= '/^API_AUTH_TOKEN=/{print $2}' .env
```

No se recomienda copiar el token literal en documentación, chats, repositorios o logs.

## Endpoints disponibles

Base local:

```bash
BASE=http://127.0.0.1:8000/api/v2/motor-ia
```

### Estado

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | No | Estado del módulo MotorIA. |

### Catálogo

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/tipos-documento` | No | Lista catálogo completo de tipos de norma. |
| POST | `/tipos-documento` | `X-API-Key` | Crea un tipo. |
| PUT | `/tipos-documento/{tipo_id}` | `X-API-Key` | Edita un tipo. |
| DELETE | `/tipos-documento/{tipo_id}` | `X-API-Key` | Elimina un tipo. |

Ejemplo:

```bash
curl "$BASE/tipos-documento" | jq
```

Respuesta tipo catálogo:

```json
{
  "success": true,
  "message": "Tipos listados",
  "data": [
    {"id": 1, "nombre": "Constitución", "prioridad": 1}
  ],
  "total": 19
}
```

### Documentos

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/documentos` | No | Lista documentos con `limit`, `skip`, `todos` y filtros. |
| POST | `/documentos` | `X-API-Key` | Sube un PDF, lo chunkea, lo indexa y lo verifica. |
| GET | `/documentos/{documento_id}` | No | Detalle de documento. |
| PUT | `/documentos/{documento_id}` | `X-API-Key` | Actualiza título, tipo y fecha. |
| DELETE | `/documentos/{documento_id}` | `X-API-Key` | Elimina documento y archivo físico. |
| GET | `/documentos/{documento_id}/descargar` | No | Descarga o previsualiza PDF. |
| GET | `/documentos/{documento_id}/chunks` | No | Lista chunks con paginación. |
| POST | `/documentos/{documento_id}/verificar` | `X-API-Key` | Verificación de calidad por documento. |

Parámetros de listado:

```text
limit: int, 1-500, default 100
skip: int, >=0, default 0
todos: bool, default false
tipo_id: int, optional
q: string, optional
creado_desde: date, optional
creado_hasta: date, optional
orden: titulo|fecha|creado_en|chunks|prioridad, default creado_en
dir: asc|desc, default desc
```

Ejemplo de listado:

```bash
curl "$BASE/documentos?limit=10&skip=0&tipo_id=3&q=riesgos" | jq
```

Ejemplo de subida de PDF:

```bash
curl -X POST "$BASE/documentos" \
  -H "X-API-Key: $API_AUTH_TOKEN" \
  -F "archivo=@/ruta/al/documento.pdf;type=application/pdf" \
  -F "titulo=Ley de Gestión de Riesgos" \
  -F "tipo_id=3" \
  -F "fecha_publicacion=2024-01-15"
```

### Búsqueda

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/busqueda` | No | Búsqueda híbrida sin generar respuesta LLM. |
| POST | `/busqueda` | No | Búsqueda híbrida por JSON. |

Ejemplo GET:

```bash
curl "$BASE/busqueda?q=planes%20de%20emergencia&limite=5&umbral=0.30" | jq
```

Ejemplo POST:

```bash
curl -X POST "$BASE/busqueda" \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"planes de emergencia","limite":5,"umbral":0.30}' | jq
```

Respuesta:

```json
{
  "consulta": "planes de emergencia",
  "intencion": "general",
  "total_resultados": 10,
  "resultados": [
    {
      "id": 1,
      "documento_id": 1,
      "titulo": "...",
      "numeral": "Artículo 3",
      "contenido": "...",
      "similitud": 0.8474
    }
  ]
}
```

### Grupos

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/grupos` | No | Lista grupos con paginación. |
| POST | `/grupos` | `X-API-Key` | Crea grupo. |
| GET | `/grupos/{grupo_id}` | No | Detalle de grupo. |
| PUT | `/grupos/{grupo_id}` | `X-API-Key` | Edita grupo. |
| DELETE | `/grupos/{grupo_id}` | `X-API-Key` | Elimina grupo. |
| GET | `/grupos/{grupo_id}/documentos` | No | IDs de documentos del grupo. |

Ejemplo:

```bash
curl "$BASE/grupos?limit=10&todos=false&q=normas" | jq
```

### LLM

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/llm/modo` | `X-API-Key` | Consulta el modo global del LLM. |
| POST | `/llm/modo` | `X-API-Key` | Cambia modo global: `local` o `external`. |
| GET | `/llm/proveedores` | No | Lista proveedores con claves enmascaradas. |
| POST | `/llm/proveedores` | `X-API-Key` | Crea proveedor; cifra `apikey`. |
| GET | `/llm/proveedores/{proveedor_id}` | No | Detalle de proveedor. |
| PUT | `/llm/proveedores/{proveedor_id}` | `X-API-Key` | Edita proveedor. |
| DELETE | `/llm/proveedores/{proveedor_id}` | `X-API-Key` | Elimina proveedor. |
| POST | `/llm/proveedores/{proveedor_id}/probar` | `X-API-Key` | Prueba proveedor y actualiza `estado_modelo`. |
| GET | `/llm/uso/resumen` | `X-API-Key` | Resumen de consumo: LLM + embeddings. |

Crear un proveedor externo:

```bash
curl -X POST "$BASE/llm/proveedores" \
  -H "X-API-Key: $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Google",
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "modelo_base": "gemini-3.6-flash",
    "apikey": "<LLM_API_KEY>",
    "estado_manual": true
  }'
```

Probar el proveedor creado:

```bash
curl -X POST "$BASE/llm/proveedores/1/probar" \
  -H "X-API-Key: $API_AUTH_TOKEN"
```

Importante:

- Si existe algún proveedor en la tabla `proveedores_llm`, el fallback por `.env` se ignora.
- Para que `/chat` use un proveedor de tabla, el proveedor debe quedar con:
  - `estado_manual = true`
  - `estado_modelo = true`
  - `apikey` configurada
- La `apikey` se guarda cifrada en PostgreSQL con la master key de `.keys/motor_ia_llm_master.key`.
- La API nunca devuelve la `apikey` en texto plano.

### Chat

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/chat` | No | Chat RAG con respuesta en streaming. |

Ejemplo:

```bash
curl -N -X POST "$BASE/chat" \
  -H "Content-Type: application/json" \
  -d '{"pregunta":"¿Qué dice la normativa sobre planes de emergencia?","limite":10}'
```

Respuesta SSE con eventos:

```text
data: {"type":"token","content":"..."}
data: {"type":"done","pregunta":"...","tokens":0,"fuentes":[...]}
```

Sin documentos indexados:

```text
data: {"type":"token","content":"No encontre documentos relevantes para su pregunta."}
```

Con documentos pero sin proveedor LLM habilitado, la generación puede fallar.

### Verificación

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/documentos/{documento_id}/verificar` | `X-API-Key` | Calidad retrieval por documento. |
| POST | `/verificacion/general` | `X-API-Key` | Evaluación global del sistema. |

Ejemplo:

```bash
curl -X POST "$BASE/documentos/1/verificar" \
  -H "X-API-Key: $API_AUTH_TOKEN"
```

### Voz

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/voz` | No | Transcribe audio con Whisper y responde con RAG. |

Ejemplo:

```bash
curl -N -X POST "$BASE/voz" \
  -F "audio=@/ruta/al/pregunta.mp3;type=audio/mpeg"
```

Requiere LLM habilitado para devolver respuesta generada.

## Convención de listados

Los listados dinámicos de MotorIA siguen la convención SINAGERSAT:

```text
limit -> cantidad, por defecto 100
skip -> offset
todos -> true devuelve todo sin paginar
total -> número total filtrado sin paginar
data -> lista de registros
```

Los listados dinámicos usan respuesta:

```json
{
  "success": true,
  "message": "...",
  "data": [],
  "total": 0
}
```

Los catálogos no llevan paginación; devuelven la lista completa con el mismo envelope `data` + `total`.

## Embeddings

Configuración actual en `.env`:

```env
EMBEDDINGS_MODE=external
EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1
EMBEDDINGS_API_KEY=<EMBEDDINGS_LOCAL_TOKEN>
EMBEDDINGS_API_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDINGS_LOCAL_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDINGS_LOCAL_TOKEN=<EMBEDDINGS_LOCAL_TOKEN>
EMBEDDINGS_LOCAL_MAX_BATCH=128
EMBEDDINGS_DIM=384
EMBEDDINGS_EXTERNAL_BATCH_SIZE=8
EMBEDDINGS_PROVIDER_NAME=local-multilingual
EMBEDDINGS_METRICS_PROVIDER=local-multilingual
```

Comportamiento actual:

- La API principal llama al servicio local `motoria-embeddings`.
- El servicio carga FastEmbed ONNX en `2` workers separados.
- La API principal no carga el modelo dentro de sus workers.
- Se mantiene `motor_ia.chunks.embedding vector(384)`.
- El modelo elegido para español es `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- El servicio debe escuchar solo en `127.0.0.1:8001`.

### Volver a Google si fuera necesario

La clave de Google se conservó como `GEMINI_EMBEDDINGS_API_KEY`. Para regresar:

```env
EMBEDDINGS_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/
EMBEDDINGS_API_KEY=<GEMINI_EMBEDDINGS_API_KEY>
EMBEDDINGS_API_MODEL=gemini-embedding-001
EMBEDDINGS_PROVIDER_NAME=google
EMBEDDINGS_METRICS_PROVIDER=google
```

Advertencia: si ya hay chunks generados con el modelo local multilingual y se cambia a Google, se deben reindexar los documentos, porque aunque ambos generen 384D son espacios vectoriales distintos.

### Alternativa in-process

Si un día se quisiera embeddings locales dentro de la misma API, se puede usar:

```env
EMBEDDINGS_MODE=local
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDINGS_DIM=384
EMBEDDINGS_IDLE_UNLOAD_SEC=120
EMBEDDINGS_TORCH_THREADS=1
```

Pero esa opción duplica el modelo por worker y no es recomendable para más de 1 worker en este servidor.

## Métricas de consumo

Endpoint:

```bash
curl -H "X-API-Key: $API_AUTH_TOKEN" \
  "http://127.0.0.1:8000/api/v2/motor-ia/llm/uso/resumen"
```

Filtro opcional:

```bash
curl -H "X-API-Key: $API_AUTH_TOKEN" \
  "http://127.0.0.1:8000/api/v2/motor-ia/llm/uso/resumen?desde=2026-11-01&hasta=2026-11-30"
```

El resumen incluye:

- `uso_total`: sumatoria simple de llamadas LLM + embeddings.
- Bloques clásicos `resumen_total`, `por_proveedor` y `por_modelo` del LLM.
- `embeddings`: métricas de embeddings actuales (servicio local `local-multilingual`), con:
  - `llamadas`
  - `llamadas_exitosas`
  - `llamadas_sin_exito`
  - `textos`
  - `tokens_prompt`
  - `tokens_total`
  - `llamadas_con_tokens_estimados`
  - `por_tipo` (`query` y `index`)

Importante: el servicio local devuelve tokens estimados; la API los toma si el
proveedor no envía `usage`. La tabla de control es `motor_ia.uso_embeddings`.

## Datos sensibles

No documentar ni pegar en el repo:

- `API_AUTH_TOKEN`
- `EMBEDDINGS_API_KEY`
- `LLM_API_KEY`
- Claves de proveedores
- Contraseña de PostgreSQL
- Contenido del `.env`

El `API_AUTH_TOKEN` real se lee localmente desde `.env`.

## Verificación rápida

```bash
BASE=http://127.0.0.1:8000/api/v2/motor-ia
export API_AUTH_TOKEN=$(awk -F= '/^API_AUTH_TOKEN=/{print $2}' .env)

curl -s "$BASE/health" | jq
curl -s "$BASE/tipos-documento" | jq '.total'
curl -s "$BASE/documentos" | jq '.total'
curl -s "$BASE/grupos" | jq '.total'
curl -s "$BASE/llm/proveedores" | jq '.total'
curl -s -o /dev/null -w 'docs %{http_code}\n' "$BASE/documentos?limit=1"
curl -s -o /dev/null -w 'busqueda %{http_code}\n' "$BASE/busqueda?q=prueba"
curl -s -o /dev/null -w 'modo sin token %{http_code}\n' "$BASE/llm/modo"
curl -s -o /dev/null -w 'modo con token %{http_code}\n' -H "X-API-Key: $API_AUTH_TOKEN" "$BASE/llm/modo"
```

Resultado esperado hoy:

- `/health`: 200.
- `/tipos-documento`: 200 con 19 tipos.
- `/documentos`: 200 con `total=0`.
- `/grupos`: 200 con `total=0`.
- `/llm/proveedores`: 200 con `total=0`.
- `/busqueda`: 200.
- `/llm/modo` sin token: 401.
- `/llm/modo` con token: 200.

## Próximos pasos operativos

1. Registrar al menos un proveedor de LLM en `/llm/proveedores`.
2. Ejecutar `POST /llm/proveedores/{id}/probar` para activar `estado_modelo`.
3. Subir PDFs reales con `POST /documentos`.
4. Probar `/busqueda` antes de usar `/chat`.
5. Monitorear `motoria-embeddings.service` y `motor_ia.uso_embeddings`.
