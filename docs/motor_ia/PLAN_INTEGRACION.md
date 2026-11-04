# Plan de integracion de MotorIA en SINAGERSAT

Fecha: 2026-11-03
Rama de respaldo ya subida: `respaldo`
Rama local de trabajo: `integracion-motor-ia` (no se subira a GitHub)

## Objetivo

Integrar el motor RAG de MotorIA dentro de la API FastAPI existente de
SINAGERSAT, usando la misma base PostgreSQL `db_sinagersat` pero con un esquema
nuevo y separado llamado `motor_ia`.

- Sin servicio nuevo en el puerto 8001.
- Sin Cloudflare.
- Sin tocar las tablas de `public`, `edan`, `rida`, `sinb`, `usuarios`,
  `repositorio`, `shared` ni `rea`.
- Documentos fisicos de MotorIA en `uploads/motor_ia/`.
- Metadatos y chunks en el esquema `motor_ia`.
- LLM externo OpenAI-compatible (`LLM_MODE=external`).
- Autenticacion de escritura/administracion con `X-API-Key` (`API_AUTH_TOKEN`),
  separada del JWT de SINAGERSAT.
- Frontend Vue fuera de alcance por ahora.

## Fases

### Fase 0 - Respaldo (completada)

- [x] Revisar estado de git y excluir secretos, dumps y `node_modules`.
- [x] Crear rama `respaldo`.
- [x] Commit y push del estado actual a GitHub.
- [x] Crear rama local `integracion-motor-ia` para no subir cambios posteriores.

Archivos excluidos del respaldo por seguridad:

- `backups/`
- `.env`
- `database/servers.json`
- `database/dbeaver-data-sources.xml`
- `database/*_backup.sql`, `database/*.dump`
- `SINB/sinb_*.sql`
- `.opencode/node_modules/`
- `venv/`, `uploads/`

### Fase 1 - PostgreSQL (completada y verificada)

1. [x] Instalar la extension `postgresql-16-pgvector` (version 0.6.0).
2. [x] Verificar version de PostgreSQL, PostGIS, `pg_trgm` y `vector`.
3. [x] Respaldar `db_sinagersat` antes de migrar
   (`backups/pre_motor_ia_20261103_200321.dump`).
4. [x] Crear `database/migrations/v2.63.0_motor_ia.sql`.
5. [x] Crear rollback `database/migrations/v2.63.0_motor_ia_rollback.sql`.
6. [x] Aplicar la migracion como superusuario de PostgreSQL.
7. [x] Verificar esquema `motor_ia`, 7 tablas, 19 tipos, indices y permisos.
8. [x] Probar `INSERT/SELECT` de un vector de 384 dimensiones con rollback.
9. [x] Reaplicar la migracion: idempotente (19 tipos, 7 tablas).
10. [x] Probar rollback y reaplicacion: correcto.
11. [x] Verificar que las tablas existentes de SINAGERSAT siguen intactas
    (edan 28, public 3, rea 4, repositorio 2, rida 58, shared 7, sinb 32,
    usuarios 7).

### Fase 2 - APIs (completada y verificada)

1. [x] Completar `api/motor_ia/` (rutas, core, db, seguridad y configuracion).
2. [x] Registrar el router en `api/main.py` bajo `/api/v2/motor-ia`.
3. [x] Instalar dependencias adicionales sin cambiar los pines actuales de
   FastAPI/Uvicorn (`torch` CPU, `sentence-transformers`, `PyMuPDF`, `openai`,
   `openai-whisper`) y `ffmpeg` del sistema para `/voz`.
4. [x] Configurar `.env` (LLM externo, embeddings, token, rutas, claves).
5. [x] Crear `uploads/motor_ia/` y `.keys/` con permisos restringidos.
6. [x] Reiniciar la API y probar endpoints nuevos.
7. [x] Verificar que `/api/v1`, `/api/v2` y `/docs/v2` siguen funcionando.

Pruebas realizadas el 2026-11-03:

- `GET /health`, `/api/v2/motor-ia/health`, `/tipos-documento`, `/documentos`,
  `/grupos` responden 200.
- `GET /api/v2/motor-ia/llm/modo` responde 401 sin `X-API-Key` y 200 con el
  token configurado.
- Prueba de embeddings externo Google: vector de 384 dimensiones, norma 1.0.
- Prueba de subida de PDF: 10 chunks, extraccion de texto, embeddings,
  busqueda y verificacion con precision@1/3/5 = 1.0; documento y archivo de
  prueba eliminados despues.
- `GET /api/v2/shared/departamentos`, `/provincias`, `/municipios` y
  `/cultivos/grupos` siguen respondiendo 200.
- `pip check`, `whisper` y `ffmpeg` verificados sin conflictos de dependencias.
- OpenAPI activo con 464 rutas, 20 de ellas bajo `/api/v2/motor-ia`.

Pendiente operativo: cargar `LLM_API_KEY` en `.env` (o registrar un proveedor
desde `POST /api/v2/motor-ia/llm/proveedores`) para habilitar `/chat`.
`/voz` ya tiene `whisper`/`ffmpeg`, pero descarga el modelo en el primer uso y
tambien requiere LLM para responder. Los embeddings ya funcionan con Google
externo gratuito. El resto del modulo (documentos, busqueda y administracion)
esta verificado.

### Fase 2.2 - Embeddings Google externos (completada)

1. [x] Configurar `EMBEDDINGS_MODE=external` con Google AI Studio.
2. [x] Validar modelo `gemini-embedding-001` devolviendo 384 dimensiones.
3. [x] Adaptar `core/embeddings.py` para lotes externos, reintentos por rate
   limit y validacion estricta de dimension.
4. [x] Mantener `--workers 4`; la memoria del servicio bajo de ~1.0 GB con
   modelo local a ~0.6 GB sin carga local.
5. [x] Probar busqueda y subida/eliminacion de PDF de prueba sin dejar datos.

### Fase 2.3 - Convencion de listados API (completada)

1. [x] Normalizar `GET /documentos` con `limit`, `skip`, `todos`, filtros y
   respuesta `SuccessResponse` (`data` + `total`).
2. [x] Normalizar `GET /grupos` con `limit`, `skip`, `todos`, `q` y
   `SuccessResponse`.
3. [x] Normalizar `GET /llm/proveedores` con `limit`, `skip`, `todos`, `q`,
   `estado_manual`, `estado_modelo` y `SuccessResponse`.
4. [x] Normalizar `GET /documentos/{id}/chunks` con `limit`, `skip`, `todos`,
   `q` y `SuccessResponse`.
5. [x] Dejar `tipos-documento` como catalogo completo, sin paginacion, pero con
   `SuccessResponse`.

### Fase 2.4 - Metricas Google embeddings (completada)

1. [x] Se descarto temporalmente NVIDIA como redundante porque Google y NVIDIA
   generan espacios vectoriales incompatibles sin dual-index completo.
2. [x] Se configuró Google `gemini-embedding-001` con `384D` y esquema original
   `motor_ia.chunks.embedding`.
3. [x] Se creó `motor_ia.uso_embeddings` para consumo de embeddings.
4. [x] `core/embeddings.py` registra llamadas de `query` e `index`.
5. [x] `GET /llm/uso/resumen` ahora combina métricas LLM + embeddings.
6. [x] Proteger `GET /llm/uso/resumen` con `X-API-Key`.
7. [x] Prueba con búsqueda, subida de PDF y métricas; datos de prueba limpiados.

### Fase 2.5 - Servicio local de embeddings FastEmbed (completada)

1. [x] Crear `services/motoria_embeddings/main.py` compatible con OpenAI
   `/v1/embeddings`.
2. [x] Usar modelo local multilingue compatible con 384D:
   `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
3. [x] Añadir `fastembed` a `requirements.txt` e instalarlo en el venv.
4. [x] Precargar el modelo ONNX en el usuario `prosuco`.
5. [x] Crear unit systemd `motoria-embeddings.service` escuchando solo
   `127.0.0.1:8001` con `--workers 2`.
6. [x] Cambiar `sinagersat-api.service` de `--workers 4` a `--workers 3` y hacer
   que dependa de `motoria-embeddings.service`.
7. [x] Actualizar `.env`: MotorIA usa
   `EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1`.
8. [x] Conservar la clave anterior de Google como `GEMINI_EMBEDDINGS_API_KEY`.
9. [x] Probar subida de PDF, búsqueda y métricas; luego limpiar datos de prueba.

### Fase 3 - Operacion y documentacion (completada)

1. [x] Actualizar `deploy/desplegar_todo.sh` (pgvector, torch CPU, migracion,
   variables de MotorIA y directorios).
2. [x] Actualizar `deploy/verificar.sh` (schema, tablas y extension vector).
3. [x] Actualizar `deploy/desplegar_bd.sh` (migracion MotorIA como superusuario).
4. [x] Crear `.env.example` sin secretos reales.
5. [x] Documentar uso, migracion y rollback en `docs/motor_ia/README.md`.

## Esquema PostgreSQL `motor_ia`

Tablas:

- `tipos_documento`
- `documentos`
- `chunks` con `embedding vector(384)`
- `proveedores_llm` con `razonamiento_tokens`
- `uso_llm`
- `grupo_documentos`
- `grupo_documentos_items`

Extensiones requeridas:

- `vector` (pgvector)
- `pg_trgm` (ya instalada)

Indices previstos:

- HNSW sobre `chunks.embedding` con `vector_cosine_ops`.
- GIN trigram sobre `chunks.contenido`.
- B-tree sobre claves foraneas y campos de filtro.

Permisos:

- `GRANT ALL` al rol `sinagersat` sobre el esquema y sus objetos.
- `ALTER DEFAULT PRIVILEGES` para futuras tablas/secuencias.

## Embeddings

Configuracion actual: servicio local separado `motoria-embeddings.service`
con FastEmbed ONNX y modelo
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, manteniendo
`EMBEDDINGS_DIM=384` compatible con el esquema creado.

Arquitectura:

- `sinagersat-api.service`: 3 workers, no carga modelos locales.
- `motoria-embeddings.service`: 2 workers, solo `127.0.0.1:8001`.
- MotorIA llama a `http://127.0.0.1:8001/v1` usando `EMBEDDINGS_MODE=external`.

Variables actuales:

- `EMBEDDINGS_MODE=external`
- `EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1`
- `EMBEDDINGS_API_KEY=<EMBEDDINGS_LOCAL_TOKEN>`
- `EMBEDDINGS_API_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `EMBEDDINGS_LOCAL_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `EMBEDDINGS_LOCAL_TOKEN=<EMBEDDINGS_LOCAL_TOKEN>`
- `EMBEDDINGS_LOCAL_MAX_BATCH=128`
- `EMBEDDINGS_DIM=384`
- `EMBEDDINGS_METRICS_PROVIDER=local-multilingual`

Google se conservó como alternativa externa:

- `GEMINI_EMBEDDINGS_API_KEY=<clave anterior preservada en .env>`
- Para volver: cambiar base/modelo/proveedor a Google y reindexar si ya hay
  chunks locales.

Motivo: el modelo local queda aislado en 2 workers separados; los 3 workers de
la API principal siguen respondiendo sin cargar torch/transformers dentro de
cada proceso.

## Seguridad

- No copiar `backups/.env_respaldo` ni `backups/keys/llm_master.key_respaldo`
  de la rama `despliegue` de MotorIA: contienen secretos.
- Generar una clave maestra nueva en `.keys/motor_ia_llm_master.key`.
- Generar un `API_AUTH_TOKEN` nuevo y separado del JWT.
- Mantener `.keys/`, `.env`, `uploads/motor_ia/` y `modelos/` fuera de git.
- No imprimir claves ni secretos en logs.
- No pegar API keys en chats o tickets; si ocurre, rotarlas inmediatamente.

## Rollback

- Base de datos: aplicar `v2.63.0_motor_ia_rollback.sql`
  (`DROP SCHEMA motor_ia CASCADE`).
- API: quitar el registro del router en `api/main.py` y reiniciar el servicio.
- Codigo: volver a la rama `respaldo` o a `v1.4.0`.
- Dependencias: las librerias agregadas no afectan a los modulos existentes;
  si hiciera falta, reinstalar el venv desde un respaldo.

## Verificacion de PostgreSQL

Comandos previstos:

```bash
sudo -u postgres psql -d db_sinagersat -c "SELECT extname, extversion FROM pg_extension ORDER BY 1;"
sudo -u postgres psql -d db_sinagersat -c "SELECT nspname FROM pg_namespace WHERE nspname='motor_ia';"
sudo -u postgres psql -d db_sinagersat -c "SELECT table_name FROM information_schema.tables WHERE table_schema='motor_ia' ORDER BY 1;"
sudo -u postgres psql -d db_sinagersat -c "SELECT count(*) FROM motor_ia.tipos_documento;"
sudo -u postgres psql -d db_sinagersat -c "SELECT indexname FROM pg_indexes WHERE schemaname='motor_ia' ORDER BY 1;"
```

Prueba de vector:

```sql
BEGIN;
INSERT INTO motor_ia.documentos (titulo, tipo_id)
VALUES ('prueba vector', (SELECT id FROM motor_ia.tipos_documento LIMIT 1))
RETURNING id;
-- usar el id devuelto
INSERT INTO motor_ia.chunks (documento_id, contenido, numeral, orden, embedding)
VALUES (<id>, 'texto de prueba', 'Prueba', 0,
        (SELECT array_agg((random())::real)::vector(384) FROM generate_series(1, 384)));
SELECT id, embedding <=> (SELECT embedding FROM motor_ia.chunks ORDER BY id DESC LIMIT 1) AS distancia
FROM motor_ia.chunks ORDER BY id DESC LIMIT 1;
ROLLBACK;
```

## Estado actual

- Respaldo remoto: completado.
- PostgreSQL: completado y verificado (pgvector 0.6.0, migracion aplicada,
  rollback probado).
- APIs: completadas y verificadas; router registrado en `api/main.py` bajo
  `/api/v2/motor-ia`, servicio systemd activo con 3 workers.
- Embeddings: servicio `motoria-embeddings.service` activo con 2 workers,
  FastEmbed ONNX multilingue 384D, solo en localhost.
- Metricas: `motor_ia.uso_embeddings` registra query/index y `GET
  /llm/uso/resumen` combina LLM + embeddings.
- LLM: modo `external` configurado, pendiente de cargar `LLM_API_KEY` o
  registrar un proveedor con clave desde la API.

## Nota importante

El `api/main.py` del respaldo tenia una referencia a `almacenes_router` sin
import. Se elimino esa referencia porque el modulo `api/almacenes/` del
respaldo esta incompleto (importa `api.common.responses` y `api.core.*`, que no
existen en este repositorio) y no formaba parte de la API que estaba en
produccion.
