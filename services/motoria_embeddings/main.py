import os

for _var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_var, "1")

from typing import List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MODEL_NAME = (
    os.getenv("EMBEDDINGS_LOCAL_MODEL")
    or os.getenv("EMBEDDINGS_API_MODEL")
    or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
).strip()
DIMENSION = int(os.getenv("EMBEDDINGS_DIM", "384") or 384)
SERVICE_TOKEN = (
    os.getenv("EMBEDDINGS_LOCAL_TOKEN")
    or os.getenv("EMBEDDINGS_SERVICE_TOKEN")
    or ""
).strip()
MAX_BATCH = max(1, int(os.getenv("EMBEDDINGS_LOCAL_MAX_BATCH", "128") or 128))
# Cache persistente del modelo ONNX. Por defecto fastembed usa <tmp>/fastembed_cache,
# que se pierde al limpiar /tmp y deja el servicio sin modelo (arranque con
# HF_HUB_OFFLINE=1). Se fuerza una ruta estable dentro del HOME del usuario
# de servicio para que el modelo quede versionado en el servidor.
CACHE_DIR = (
    os.getenv("EMBEDDINGS_LOCAL_CACHE_DIR")
    or os.path.join(os.path.expanduser("~"), ".cache", "motoria-embeddings")
).strip()

_model = None

app = FastAPI(title="MotorIA Embeddings Local", version="1.0.0")


class EmbeddingsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = Field(..., description="Identificador del modelo esperado.")
    input: Union[str, List[str]] = Field(..., description="Texto o lista de textos.")
    dimensions: Optional[int] = Field(None, description="Dimensiones esperadas.")
    encoding_format: Optional[str] = Field("float", description="Formato de salida.")


def _validar_autorizacion(request: Request):
    if not SERVICE_TOKEN:
        return
    auth = request.headers.get("authorization", "")
    esperado = f"Bearer {SERVICE_TOKEN}"
    if auth != esperado:
        raise HTTPException(status_code=401, detail="Token de embeddings inválido.")


@app.on_event("startup")
def cargar_modelo():
    """Carga el modelo ONNX desde CACHE_DIR.

    Con HF_HUB_OFFLINE=1 (modo servidor sin internet) exige tener el modelo
    precargado; si falla se reintenta una vez permitiendo la descarga, para
    que el primer arranque en un servidor nuevo funcione.
    """
    global _model
    if _model is not None:
        return

    os.makedirs(CACHE_DIR, exist_ok=True)

    from fastembed import TextEmbedding

    print(
        f"Cargando modelo de embeddings local: {MODEL_NAME} (cache: {CACHE_DIR})",
        flush=True,
    )
    try:
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
    except Exception as exc:
        if os.getenv("HF_HUB_OFFLINE", "").strip().lower() not in ("1", "true", "yes"):
            raise
        print(
            f"Modelo no disponible en modo offline ({exc}); "
            "reintentando con descarga habilitada.",
            flush=True,
        )
        os.environ["HF_HUB_OFFLINE"] = "0"
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
    print("Modelo de embeddings local cargado.", flush=True)


@app.get("/health")
def health():
    return {
        "status": "ok" if _model is not None else "cargando",
        "modelo": MODEL_NAME,
        "dimension": DIMENSION,
        "cache_dir": CACHE_DIR,
    }


@app.post("/v1/embeddings")
def crear_embeddings(req: EmbeddingsRequest, request: Request):
    _validar_autorizacion(request)

    if _model is None:
        raise HTTPException(status_code=503, detail="El modelo de embeddings aún no ha terminado de cargar.")

    if req.model != MODEL_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"Este servicio embeddings solo sirve {MODEL_NAME}.",
        )

    if req.dimensions is not None and int(req.dimensions) != DIMENSION:
        raise HTTPException(
            status_code=400,
            detail=f"Dimensiones no soportadas: {req.dimensions}. Este servicio entrega {DIMENSION}D.",
        )

    textos = [req.input] if isinstance(req.input, str) else req.input
    if not textos:
        raise HTTPException(status_code=400, detail="El campo input no puede estar vacío.")

    if len(textos) > MAX_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Demasiados textos en un lote: {len(textos)}. Máximo {MAX_BATCH}.",
        )

    for i, texto in enumerate(textos):
        if not isinstance(texto, str) or not texto.strip():
            raise HTTPException(status_code=400, detail=f"El texto en la posición {i} está vacío.")

    try:
        vectors = list(_model.embed(textos))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el embedding: {str(exc)[:500]}") from exc

    if len(vectors) != len(textos):
        raise HTTPException(
            status_code=500,
            detail=f"El modelo devolvió {len(vectors)} embeddings para {len(textos)} textos.",
        )

    data = []
    for i, vector in enumerate(vectors):
        vector_list = [float(x) for x in vector]
        if len(vector_list) != DIMENSION:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"El modelo devolvió {len(vector_list)} dimensiones, "
                    f"pero EMBEDDINGS_DIM={DIMENSION}."
                ),
            )
        data.append({
            "object": "embedding",
            "index": i,
            "embedding": vector_list,
        })

    prompt_chars = sum(len(t) for t in textos)
    prompt_tokens = max(len(textos), int(prompt_chars / 4))

    return {
        "object": "list",
        "data": data,
        "model": req.model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "total_tokens": prompt_tokens,
        },
    }
