# MotorIA en SINAGERSAT

MotorIA es un modulo RAG integrado en la API FastAPI existente. Usa la misma
base PostgreSQL (`db_sinagersat`) con un esquema separado `motor_ia`, por lo que
no modifica tablas de `edan`, `public`, `rea`, `repositorio`, `rida`, `shared`,
`sinb` ni `usuarios`.

- Prefijo de API: `/api/v2/motor-ia`
- Documentos PDF: `uploads/motor_ia/`
- Embeddings actuales: servicio local `motoria-embeddings` con FastEmbed ONNX y `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones)
- LLM: proveedor externo OpenAI-compatible (Groq por defecto)
- Autenticacion de escritura/administracion: `X-API-Key: <API_AUTH_TOKEN>`

Documentacion operativa de endpoints disponibles, uso del token y configuracion
de embeddings: `API_IA.md`.

## Endpoints

| Metodo | Ruta | Auth | Descripcion |
|---|---|---|---|
| GET | `/health` | No | Estado del modulo |
| POST | `/chat` | No | Respuesta RAG con streaming |
| GET/POST | `/busqueda` | No | Busqueda hibrida de fragmentos |
| GET | `/documentos` | No | Lista documentos paginada: `limit`, `skip`, `todos`, filtros |
| POST | `/documentos` | `X-API-Key` | Sube e indexa un PDF |
| GET | `/documentos/{id}` | No | Detalle del documento |
| PUT | `/documentos/{id}` | `X-API-Key` | Actualiza metadatos |
| DELETE | `/documentos/{id}` | `X-API-Key` | Elimina documento |
| GET | `/documentos/{id}/descargar` | No | Descarga PDF |
| GET | `/documentos/{id}/chunks` | No | Lista chunks paginada: `limit`, `skip`, `todos`, `q` |
| POST | `/documentos/{id}/verificar` | `X-API-Key` | Precision@1/3/5 |
| GET/POST | `/tipos-documento` | GET publico / POST `X-API-Key` | Catalogo de tipos (completo, sin paginar) |
| PUT/DELETE | `/tipos-documento/{id}` | `X-API-Key` | Edita/elimina tipos |
| GET/POST | `/grupos` | GET publico / POST `X-API-Key` | Lista grupos paginada: `limit`, `skip`, `todos`, `q` |
| PUT/DELETE | `/grupos/{id}` | `X-API-Key` | Edita/elimina grupos |
| GET | `/grupos/{id}/documentos` | No | Documentos del grupo |
| GET/POST | `/llm/modo` | `X-API-Key` | Consulta/cambia modo global |
| GET/POST | `/llm/proveedores` | GET publico / POST `X-API-Key` | Lista/registra proveedores paginados: `limit`, `skip`, `todos`, `q` |
| PUT/DELETE | `/llm/proveedores/{id}` | `X-API-Key` | Edita/elimina proveedor |
| POST | `/llm/proveedores/{id}/probar` | `X-API-Key` | Prueba proveedor |
| GET | `/llm/uso/resumen` | `X-API-Key` | Resumen de consumo: LLM + embeddings. |
| POST | `/verificacion/general` | `X-API-Key` | Evaluacion global |
| POST | `/voz` | No | Transcripcion + busqueda |

## Puesta en marcha

1. Instalar pgvector (ya incluido en `deploy/desplegar_todo.sh`):

   ```bash
   sudo apt-get install -y postgresql-16-pgvector ffmpeg
   ```

2. Aplicar la migracion como superusuario:

   ```bash
   sudo -u postgres psql -d db_sinagersat -f database/migrations/v2.63.0_motor_ia.sql
   ```

3. Instalar dependencias en el venv:

   ```bash
   source venv/bin/activate
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```

4. Configurar `.env` desde `.env.example`. Generar el token con:

   ```bash
   openssl rand -hex 32
   ```

5. Crear directorios y permisos:

   ```bash
   mkdir -p uploads/motor_ia .keys
   chown -R prosuco:prosuco uploads/motor_ia .keys
   chmod 700 .keys
   ```

6. Reiniciar el servicio:

   ```bash
   sudo systemctl restart sinagersat-api
   ```

7. Verificar:

   ```bash
   curl http://127.0.0.1:8000/api/v2/motor-ia/health
   curl -H "X-API-Key: $API_AUTH_TOKEN" http://127.0.0.1:8000/api/v2/motor-ia/llm/modo
   ```

## LLM externo

La API key de Google configurada en `EMBEDDINGS_API_KEY` solo habilita
búsqueda/embeddings. Para `/chat` hace falta una clave de LLM en
`LLM_API_KEY` o un proveedor registrado en `proveedores_llm`. Para `/voz`
hacen falta ademas `whisper` y el binario `ffmpeg`; el primer uso descarga
automaticamente el modelo indicado en `WHISPER_MODEL` (por defecto `tiny`):

- Opcion A: definir `LLM_API_KEY` en `.env` y reiniciar el servicio.
- Opcion B: registrar un proveedor cifrado en la base:

  ```bash
  curl -X POST http://127.0.0.1:8000/api/v2/motor-ia/llm/proveedores \
    -H "X-API-Key: $API_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"nombre":"Groq","base_url":"https://api.groq.com/openai/v1","modelo_base":"openai/gpt-oss-20b","apikey":"..."}'
  ```

La clave maestra de cifrado se guarda en `.keys/motor_ia_llm_master.key`
(permisos `600`, fuera de git).

## Embeddings

La configuracion actual usa un servicio local de embeddings separado, con
FastEmbed ONNX y modelo multilingual:

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
```

Arquitectura:

- `sinagersat-api.service`: 3 workers, no carga modelo local.
- `motoria-embeddings.service`: 2 workers, escucha solo `127.0.0.1:8001`.

Si ya hay chunks generados con un proveedor/modelo distinto, al cambiar de
proveedor hay que reindexar documentos, aunque ambos generen 384 dimensiones,
porque los espacios vectoriales no son compatibles.

## Rollback

- Base de datos:

  ```bash
  sudo -u postgres psql -d db_sinagersat -f database/migrations/v2.63.0_motor_ia_rollback.sql
  ```

  El rollback hace `DROP SCHEMA motor_ia CASCADE`; los documentos fisicos en
  `uploads/motor_ia/` no se borran automaticamente.

- API: quitar el router `motor_ia` de `api/main.py` y reiniciar el servicio.
- Codigo: volver a la rama `respaldo`.

## Pruebas realizadas

- Migracion idempotente y rollback probados.
- Subida de PDF de prueba: 10 chunks, verificacion con precision@1/3/5 = 1.0.
- Embeddings Google externo: vector de 384 dimensiones, norma 1.0, sin carga de
  modelo en los 4 workers.
- Endpoints existentes de `/api/v2/shared/*` siguen respondiendo 200.
- `X-API-Key` devuelve 401 sin token y 200 con token en rutas administrativas.
