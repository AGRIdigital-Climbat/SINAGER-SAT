# MOTORIA — Worker de embeddings local (:8001): cache persistente y arranque robusto

> **Contexto (esquema/módulo):** módulo `motor_ia` (MotorIA/RAG) + servicio externo
> `services/motoria_embeddings` (worker FastAPI en `127.0.0.1:8001`). **Sin esquema BD
> nuevo** y **sin migración**: usa `motor_ia.uso_embeddings` (métricas) y
> `motor_ia.documentos/chunks` ya existentes.
>
> **Rama/commit:** `migraciones` (código + script de despliegue + este handoff).

## 1. Objetivo y decisiones

- Confirmado el diseño: **LLM externo** (`LLM_MODE=external`, Groq/OpenAI-compatible) y
  **embeddings en un worker propio** (`EMBEDDINGS_MODE=external` →
  `EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1`). El worker carga el modelo ONNX
  (`fastembed`, `paraphrase-multilingual-MiniLM-L12-v2`, 384 dims) y la API (`:8000`,
  4 workers) **no** carga modelos.
- **Problema detectado:** el servicio estaba `inactive (dead)`. El modelo se guardaba en
  `<tempdir>/fastembed_cache`; al limpiar `/tmp` (y con `HF_HUB_OFFLINE=1` en la unidad
  systemd) el arranque fallaba:
  `ValueError: Could not load model ... from any source` → la API no tenía embeddings
  (RAG/búsqueda rotos).
- **Decisiones:**
  1. **Cache persistente y explícita** del modelo: nueva variable
     `EMBEDDINGS_LOCAL_CACHE_DIR` (default `~/.cache/motoria-embeddings`), usada por el
     worker vía `TextEmbedding(cache_dir=...)`.
  2. **Arranque tolerante:** si la carga offline falla, reintenta una vez con descarga
     habilitada (`HF_HUB_OFFLINE=0` en proceso). Así el primer arranque en servidor nuevo
     funciona y luego queda cacheado.
  3. **Precarga en la instalación:** `05_instalar_servicios.sh` descarga el modelo (como el
     usuario de servicio) antes de habilitar la unidad y escribe
     `EMBEDDINGS_LOCAL_CACHE_DIR` + `HF_HUB_OFFLINE=1` + límites de hilos en la unidad.
  4. **`/health` del worker** ahora reporta `cache_dir` (diagnóstico de replicación).
- No se cambia el contrato del worker (`POST /v1/embeddings`, token `EMBEDDINGS_LOCAL_TOKEN`
  / `EMBEDDINGS_SERVICE_TOKEN`, batch `EMBEDDINGS_LOCAL_MAX_BATCH`) ni el del API.

## 2. Archivos

**Modificados**
| Archivo | Qué cambió |
|---|---|
| `services/motoria_embeddings/main.py` | `CACHE_DIR` (`EMBEDDINGS_LOCAL_CACHE_DIR`, default `~/.cache/motoria-embeddings`) + `mkdir`; carga del modelo con `cache_dir`, reintento online si falla en modo offline; `/health` incluye `cache_dir`. |
| `despliegue/scripts/05_instalar_servicios.sh` | Bloque `motoria-embeddings.service`: calcula/crea la cache del usuario de servicio, **precarga el modelo ONNX** (descarga única, `HF_HUB_OFFLINE=0`), y escribe `Environment=EMBEDDINGS_LOCAL_CACHE_DIR=…`, `Environment=HF_HUB_OFFLINE=1` y `OMP/OPENBLAS/MKL/NUMEXPR/VECLIB_*_THREADS=1`. |

**Fuera del repo (estado del servidor, se documenta para replicar)**
| Elemento | Detalle |
|---|---|
| `/etc/systemd/system/motoria-embeddings.service` | Añadido `Environment=EMBEDDINGS_LOCAL_CACHE_DIR=/home/prosuco/.cache/motoria-embeddings` (ya tenía `HF_HUB_OFFLINE=1` + hilos). `systemctl daemon-reload && systemctl restart motoria-embeddings`. |
| `~prosuco/.cache/motoria-embeddings/` | Modelo ONNX precargado (`models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q`, ~241 MB, `chown prosuco:prosuco`). |
| `.env` (sin cambios) | `EMBEDDINGS_MODE=external`, `EMBEDDINGS_API_BASE=http://127.0.0.1:8001/v1`, `EMBEDDINGS_API_MODEL=EMBEDDINGS_LOCAL_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `EMBEDDINGS_DIM=384`, `EMBEDDINGS_LOCAL_TOKEN` = `EMBEDDINGS_API_KEY` (64 chars), `LLM_MODE=external`, `LLM_API_BASE=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-20b`. |

## 3. Migraciones
**Ninguna.** No hay cambios de esquema. (La BD `motor_ia` ya existe; este cambio es de
servicio/config.) No requiere espejo en `despliegue/migraciones/`.

## 4. BD
Sin afectación directa. Efecto observable: `motor_ia.uso_embeddings` vuelve a registrar
filas `exitoso = TRUE` (proveedor `local-multilingual`, `dimension 384`) cuando hay
búsquedas/ingesta, en lugar de acumular errores.

## 5. APIs

| Componente | Detalle |
|---|---|
| Worker (`:8001`) | `GET /health` → `{status, modelo, dimension, cache_dir}`; `POST /v1/embeddings` (OpenAI-compatible: `model`, `input`, `dimensions`), exige `Authorization: Bearer $EMBEDDINGS_LOCAL_TOKEN` (401 si falta/mal); `503` si el modelo aún no cargó; rechaza modelo distinto al servido (400). 2 workers uvicorn. |
| API (`:8000`) | Sin cambios de contrato. Usa el worker vía `api/motor_ia/core/embeddings.py` (`EMBEDDINGS_MODE=external`). Rutas afectadas funcionalmente: `GET/POST /api/v2/motor-ia/busqueda`, `POST /api/v2/motor-ia/documentos` (indexa chunks con embeddings), `POST /api/v2/motor-ia/chat` (RAG), `GET /api/v2/motor-ia/health`. |

## 6. Replicación (servidor limpio o servidor con worker caído)

```bash
cd /home/prosuco/SINAGERSAT/BaseData
git pull

# 1) (una vez) Precargar el modelo ONNX para el usuario de servicio
venv/bin/python - <<'PY'
import os
from dotenv import dotenv_values
cfg = dotenv_values(".env")
model = cfg["EMBEDDINGS_LOCAL_MODEL"]
cache = os.path.expanduser("~/.cache/motoria-embeddings")
os.makedirs(cache, exist_ok=True)
os.environ["HF_HUB_OFFLINE"] = "0"          # permite la descarga única
from fastembed import TextEmbedding
TextEmbedding(model_name=model, cache_dir=cache)
print("modelo precargado en", cache)
PY

# 2) Instalar/actualizar la unidad systemd (escribe la unidad con la cache + offline)
bash despliegue/scripts/05_instalar_servicios.sh
#    (o editar /etc/systemd/system/motoria-embeddings.service añadiendo
#     Environment=EMBEDDINGS_LOCAL_CACHE_DIR=/home/<user>/.cache/motoria-embeddings
#     Environment=HF_HUB_OFFLINE=1)

systemctl daemon-reload
systemctl enable --now motoria-embeddings.service
```

> Alternativa sin systemd (dev): correr el worker a mano —
> `EMBEDDINGS_LOCAL_CACHE_DIR=$HOME/.cache/motoria-embeddings HF_HUB_OFFLINE=1 \
>  venv/bin/uvicorn services.motoria_embeddings.main:app --host 127.0.0.1 --port 8001 --workers 2`

## 7. Verificación

```bash
# Worker arriba y modelo cargado desde la cache persistente
systemctl is-active motoria-embeddings                                  # active
ss -ltn | grep 8001                                                     # 127.0.0.1:8001 LISTEN
curl -s http://127.0.0.1:8001/health
# -> {"status":"ok","modelo":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
#     "dimension":384,"cache_dir":"/home/prosuco/.cache/motoria-embeddings"}

# Embeddings con token del .env (EMBEDDINGS_LOCAL_TOKEN)
curl -s -X POST http://127.0.0.1:8001/v1/embeddings \
  -H "Authorization: Bearer $(venv/bin/python -c "from dotenv import dotenv_values;print(dotenv_values('.env')['EMBEDDINGS_LOCAL_TOKEN'])")" \
  -H "Content-Type: application/json" \
  -d '{"model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2","input":["carretera dañada por inundación"],"dimensions":384}'
# -> data[0].embedding con 384 floats

# Sin token -> 401 (auth del worker intacta)
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8001/v1/embeddings \
  -H "Content-Type: application/json" -d '{"model":"x","input":["a"]}'    # 401
```

```bash
# De punta a punta por la API (JWT admin + X-API-Key para ingesta)
venv/bin/python -c "from api.motor_ia.core.embeddings import generar_embedding, generar_embeddings_lote; \
print(len(generar_embedding('carretera dañada')), len(generar_embeddings_lote(['inundación','sequía'])))"
# -> 384 2

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/motor-ia/busqueda?q=ayuda+humanitaria+para+familias+afectadas&limite=3"
# -> 200, intencion/total_resultados con similitudes (0.53-0.57 en la prueba con 1 documento indexado)
```

```sql
-- El worker dejó de fallar: métricas de embeddings exitosas
SELECT proveedor, modelo, tipo, textos, exitoso, dimension
FROM motor_ia.uso_embeddings ORDER BY id DESC LIMIT 5;
-- proveedor = 'local-multilingual', exitoso = t, dimension = 384
```

### Resultados reales en dev (2026-11-17)
| Prueba | Resultado |
|---|---|
| `systemctl status motoria-embeddings` antes de fixes | `inactive (dead)`; log: `ValueError: Could not load model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 from any source` |
| Cache precargada + unidad con `EMBEDDINGS_LOCAL_CACHE_DIR` + restart | `active`; `ss` LISTEN `127.0.0.1:8001`; `/health` `status ok`, `cache_dir` correcto |
| `POST /v1/embeddings` con token | vector de **384** dims, `modelo` = paraphrase-multilingual-MiniLM-L12-v2 |
| `POST /v1/embeddings` sin token | **401** |
| `generar_embedding` / `generar_embeddings_lote` (core de la API) | 384 dims y lote 3×384, norma unitaria |
| Ingesta `POST /api/v2/motor-ia/documentos` (PDF 1 pág.) | 200, 5 chunks indexados |
| `GET /api/v2/motor-ia/busqueda?q=...` | 200 con resultados semánticos (similitud 0.53–0.57) |
| `motor_ia.uso_embeddings` | 3 filas nuevas, `proveedor=local-multilingual`, `exitoso=t`, `dimension=384` |
| Limpieza | documento de prueba eliminado (`motor_ia.documentos/chunks` otra vez en 0); PDFs temporales borrados |

## 8. Notas / pendientes
- **`sinagersat-api.service` está `inactive`**: en dev el API atiende `:8000` porque se
  levantó a mano con `./start_api.sh` (4 workers uvicorn, proceso root). Al reiniciar de
  forma canónica usar `systemctl restart sinagersat-api` (unidad: 3 workers, usuario
  `prosuco`) **o** `./start_api.sh`, pero no ambos a la vez (puerto en uso).
- El **LLM externo sigue sin proveedor dado de alta**: `motor_ia.proveedores_llm` está
  vacío y `POST /api/v2/motor-ia/chat` responde `No hay proveedores externos en la BD`.
  Queda pendiente cargar el proveedor Groq (API key del usuario) — se hará aparte.
- El worker sirve **solo** el modelo de `EMBEDDINGS_LOCAL_MODEL` (400 si se pide otro).
  `EMBEDDINGS_DIM=384` debe coincidir con la columna vectorial de `motor_ia.chunks`.
- Con `HF_HUB_OFFLINE=1`, borrar `~/.cache/motoria-embeddings` sin red deja el servicio
  caído; la precarga (§6 paso 1) o el reintento online (§1.2) lo recuperan.
- Rollback: revertir `services/motoria_embeddings/main.py` y `05_instalar_servicios.sh`;
  la unidad puede quedarse con la cache explícita (es compatible con el código antiguo).
