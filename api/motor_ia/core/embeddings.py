import gc
import os
import re
import sys
import threading
import time
import unicodedata

import numpy as np
from dotenv import load_dotenv

from ..config import ENV_FILE

load_dotenv(ENV_FILE)

MODE = os.getenv("EMBEDDINGS_MODE", "local").strip().lower() or "local"
MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DIMENSION = int(os.getenv("EMBEDDINGS_DIM", "384") or 384)
IDLE_SEC = int(os.getenv("EMBEDDINGS_IDLE_UNLOAD_SEC", "120") or 0)
TORCH_THREADS = int(os.getenv("EMBEDDINGS_TORCH_THREADS", "1") or 1)

EXTERNAL_BASE = (
    os.getenv("EMBEDDINGS_API_BASE")
    or os.getenv("LLM_API_BASE")
    or ""
).strip()
EXTERNAL_KEY = (
    os.getenv("EMBEDDINGS_API_KEY")
    or os.getenv("LLM_API_KEY")
    or ""
).strip()
EXTERNAL_MODEL = (
    os.getenv("EMBEDDINGS_API_MODEL")
    or os.getenv("EMBEDDINGS_MODEL")
    or "text-embedding-3-small"
)
EXTERNAL_BATCH_SIZE = max(1, int(os.getenv("EMBEDDINGS_EXTERNAL_BATCH_SIZE", "8") or 8))
METRICS_ENABLED = os.getenv("EMBEDDINGS_METRICS_ENABLED", "true").strip().lower() not in ("false", "0", "no")
METRICS_PROVIDER = (
    os.getenv("EMBEDDINGS_METRICS_PROVIDER")
    or os.getenv("EMBEDDINGS_PROVIDER_NAME")
    or ("google" if "gemini" in EXTERNAL_MODEL.lower() else "external")
).strip()

_model = None
_model_lock = threading.Lock()
_idle_timer = None
_last_used = 0.0


def _normalizar_texto(texto):
    """Normaliza texto para embeddings: quita tildes, minusculas, espacios extra."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.lower()
    return re.sub(r"\s+", " ", texto).strip()


def _preparar_texto(texto):
    if not texto:
        return ""
    if MODE == "external":
        return re.sub(r"\s+", " ", texto).strip()
    return _normalizar_texto(texto)


def _normalizar_vector(vector):
    arr = np.asarray(vector, dtype=np.float32)
    if arr.shape[0] != DIMENSION:
        raise ValueError(
            f"El embedding devolvio {arr.shape[0]} dimensiones, "
            f"pero EMBEDDINGS_DIM={DIMENSION}. Ajusta EMBEDDINGS_DIM y la "
            "columna vectorial del esquema motor_ia."
        )
    norma = float(np.linalg.norm(arr))
    if norma > 0:
        arr = arr / norma
    return arr.tolist()


def _cargar_modelo_local_unlocked():
    global _model
    if _model is None:
        try:
            import torch

            torch.set_num_threads(max(1, TORCH_THREADS))
        except Exception:
            pass
        from sentence_transformers import SentenceTransformer

        print(f"Cargando modelo de embeddings {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        print("Modelo de embeddings cargado.")
    return _model


def _liberar_modelo_unlocked():
    global _model, _idle_timer
    if _idle_timer is not None:
        _idle_timer.cancel()
        _idle_timer = None
    if _model is None:
        return
    del _model
    _model = None
    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    print("Modelo de embeddings liberado de memoria.")


def _liberar_si_inactivo():
    with _model_lock:
        if _model is None:
            return
        if (time.time() - _last_used) < IDLE_SEC:
            return
        _liberar_modelo_unlocked()


def _programar_liberacion_unlocked():
    global _idle_timer
    if IDLE_SEC <= 0:
        return
    if _idle_timer is not None:
        _idle_timer.cancel()
    timer = threading.Timer(IDLE_SEC, _liberar_si_inactivo)
    timer.daemon = True
    _idle_timer = timer
    timer.start()


def cargar_modelo():
    if MODE == "external":
        raise RuntimeError("EMBEDDINGS_MODE=external: no hay modelo local que cargar.")
    with _model_lock:
        model = _cargar_modelo_local_unlocked()
        _programar_liberacion_unlocked()
        return model


def liberar_modelo():
    with _model_lock:
        _liberar_modelo_unlocked()


def _estimar_tokens(textos):
    total = sum(max(0, len(t or "")) for t in textos)
    return max(len(textos), int(total / 4)) if total else 0


def _registrar_uso_embeddings(textos, tokens_prompt=0, tokens_total=None, tipo="query",
                              exitoso=True, estimados=False, error=None):
    if not METRICS_ENABLED:
        return
    try:
        from ..db.queries import registrar_uso_embeddings

        registrar_uso_embeddings(
            proveedor=METRICS_PROVIDER,
            modelo=EXTERNAL_MODEL,
            tipo=tipo,
            textos=len(textos),
            tokens_prompt=tokens_prompt,
            tokens_total=tokens_total,
            dimension=DIMENSION,
            exitoso=exitoso,
            tokens_estimados=estimados,
            error=error,
        )
    except Exception:
        pass


def _cliente_externo():
    if not EXTERNAL_KEY:
        raise RuntimeError(
            "EMBEDDINGS_MODE=external requiere EMBEDDINGS_API_KEY "
            "(o LLM_API_KEY) en .env."
        )
    from openai import OpenAI

    return OpenAI(api_key=EXTERNAL_KEY, base_url=EXTERNAL_BASE or None)


def _es_rate_limit(exc):
    return type(exc).__name__ == "RateLimitError" or getattr(exc, "status_code", None) in (429, 503)


def _crear_embeddings(client, kwargs):
    ultima_exc = None
    for intento in range(3):
        try:
            return client.embeddings.create(**kwargs)
        except Exception as exc:
            ultima_exc = exc
            if _es_rate_limit(exc):
                time.sleep(1.2 * (2**intento))
                continue
            raise
    raise ultima_exc


def _generar_embeddings_externos(textos, purpose="query"):
    client = _cliente_externo()
    resultados = []

    for inicio in range(0, len(textos), EXTERNAL_BATCH_SIZE):
        batch = textos[inicio:inicio + EXTERNAL_BATCH_SIZE]
        kwargs = {"model": EXTERNAL_MODEL, "input": batch, "dimensions": DIMENSION}
        try:
            try:
                respuesta = _crear_embeddings(client, kwargs)
            except Exception as exc:
                if _es_rate_limit(exc) or "dimensions" not in kwargs:
                    raise
                kwargs.pop("dimensions", None)
                respuesta = _crear_embeddings(client, kwargs)
        except Exception as exc:
            _registrar_uso_embeddings(
                batch,
                tokens_prompt=_estimar_tokens(batch),
                tokens_total=_estimar_tokens(batch),
                tipo=purpose,
                exitoso=False,
                estimados=True,
                error=str(exc),
            )
            raise

        datos = sorted(
            enumerate(respuesta.data),
            key=lambda par: getattr(par[1], "index", None) if getattr(par[1], "index", None) is not None else par[0],
        )
        if len(datos) != len(batch):
            error_msg = (
                f"El proveedor externo devolvio {len(datos)} embeddings "
                f"para un lote de {len(batch)} textos."
            )
            _registrar_uso_embeddings(
                batch,
                tokens_prompt=_estimar_tokens(batch),
                tokens_total=_estimar_tokens(batch),
                tipo=purpose,
                exitoso=False,
                estimados=True,
                error=error_msg,
            )
            raise ValueError(error_msg)

        try:
            lote = [_normalizar_vector(par[1].embedding) for par in datos]
        except Exception as exc:
            _registrar_uso_embeddings(
                batch,
                tokens_prompt=_estimar_tokens(batch),
                tokens_total=_estimar_tokens(batch),
                tipo=purpose,
                exitoso=False,
                estimados=True,
                error=str(exc),
            )
            raise

        usage = getattr(respuesta, "usage", None)
        tokens_prompt = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_total = getattr(usage, "total_tokens", None) if usage else None
        if tokens_total is None:
            tokens_total = tokens_prompt if tokens_prompt is not None else _estimar_tokens(batch)
        if tokens_prompt is None:
            tokens_prompt = int(tokens_total)

        _registrar_uso_embeddings(
            batch,
            tokens_prompt=int(tokens_prompt or 0),
            tokens_total=int(tokens_total or 0),
            tipo=purpose,
            exitoso=True,
            estimados=not (usage and getattr(usage, "prompt_tokens", None) is not None),
        )
        resultados.extend(lote)

    return resultados


def generar_embedding(texto):
    global _last_used

    texto_norm = _preparar_texto(texto)
    if MODE == "external":
        return _generar_embeddings_externos([texto_norm], purpose="query")[0]

    with _model_lock:
        model = _cargar_modelo_local_unlocked()
        _last_used = time.time()
        embedding = model.encode(texto_norm, normalize_embeddings=True)
        _programar_liberacion_unlocked()
    return _normalizar_vector(embedding.tolist())


def generar_embeddings_lote(textos):
    global _last_used

    if not textos:
        return []
    textos_norm = [_preparar_texto(t) for t in textos]
    if MODE == "external":
        return _generar_embeddings_externos(textos_norm, purpose="index")

    with _model_lock:
        model = _cargar_modelo_local_unlocked()
        _last_used = time.time()
        embeddings = model.encode(
            textos_norm,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        _programar_liberacion_unlocked()
    return [_normalizar_vector(e.tolist()) for e in embeddings]
