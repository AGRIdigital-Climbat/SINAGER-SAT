import os
import random
import re
import time
from pathlib import Path

from dotenv import load_dotenv

from ..config import ENV_FILE

_BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ENV_FILE)

_llm = None
MODEL_PATH = os.getenv("MODEL_PATH", str(_BASE_DIR / "modelos" / "qwen.gguf"))

LLM_MODE = os.getenv("LLM_MODE", "external")  # local | external
_set_modo_global = LLM_MODE
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
LLM_MODEL_FALLBACK = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

CTX_MAX = 2048
MAX_TOKENS_RESPUESTA = int(os.getenv("LLM_MAX_TOKENS", "512"))
RAZONAMIENTO_MAX = int(os.getenv("LLM_RAZONAMIENTO_TOKENS", "2048"))
CHARS_POR_TOKEN = 4
SAFETY_MARGIN = 96
SYSTEM_PROMPT = (
    "Eres un asistente jurídico experto en leyes y normativas de Bolivia. "
    "Responde de forma precisa y clara usando exclusivamente la información "
    "proporcionada en el contexto. Si la información no está en el contexto, "
    "indica que no encontraste datos relevantes. "
    "Cita las fuentes usando el formato [1], [2], etc. "
    "Escribe siempre en español correcto, con tildes, ñ y puntuación adecuados. "
    "Responde exclusivamente en texto plano: sin Markdown, sin negritas ni "
    "asteriscos, sin viñetas, sin listas numeradas ni con guiones, sin "
    "encabezados, sin tablas y sin ningún otro formato. Redacta todo como "
    "prosa, en párrafos completos y bien estructurados. "
    "Responde directamente con la respuesta final, sin mostrar procesos de "
    "razonamiento, sin resumir las instrucciones recibidas y sin incluir ningún "
    "texto de 'pensamiento'. "
    "Corrige siempre fallas ortográficas o de sentido en la pregunta del usuario "
    "o en la extracción de información del contexto."
)
IM_END = "im_end"
IM_START = "im_start"

GUIAS_RESPUESTA = {
    "definicion": (
        "El usuario busca la definición de un término. Si el contexto contiene "
        "una entrada de glosario o definición literal, úsala como base. "
        "Explica el término de forma clara en párrafos de prosa y cita el artículo "
        "o parte de la norma que la define."
    ),
    "procedimiento": (
        "El usuario pregunta por un procedimiento o proceso. Explica los pasos "
        "en orden cronológico en un texto continuo de prosa, indicando quién los "
        "realiza y en qué artículo de la norma se establece cada paso, sin usar "
        "listas ni viñetas."
    ),
    "autoridad": (
        "El usuario pregunta por la autoridad responsable. Identifica qué entidad, "
        "ministerio, comité o instancia tiene la competencia y cita la norma y "
        "el artículo que lo establece, en párrafos de prosa."
    ),
    "requisito": (
        "El usuario pregunta por requisitos o condiciones. Describe cada requisito "
        "de forma clara y ordenada en un texto continuo de prosa, citando el "
        "artículo o parte de la norma correspondiente, sin usar listas ni viñetas."
    ),
    "plazo": (
        "El usuario pregunta por plazos o períodos de vigencia. Indica los plazos, "
        "fechas y la duración exacta de la vigencia en párrafos de prosa, citando "
        "el artículo que lo establece."
    ),
    "general": (
        "Responde de forma precisa y clara usando exclusivamente la información "
        "del contexto y citando las fuentes correspondientes. Usa tildes, ñ y "
        "puntuación correctos. Redacta en párrafos de prosa, sin listas ni viñetas."
    ),
}


def _guia_para(intencion):
    return GUIAS_RESPUESTA.get(intencion, GUIAS_RESPUESTA["general"])


def _estimar_tokens(texto):
    chars = texto if isinstance(texto, int) else len(texto)
    return max(1, chars // CHARS_POR_TOKEN)


def _limpiar_formato(texto, estado):
    """Limpiador best-effort de markdown/viñetas para streaming por tokens.

    Aplica limpieza a cada token recibido, manteniendo en `estado` (un dict)
    una "cola" de caracteres al final que podrían ser el inicio de una marca
    partida entre chunks (negritas, backticks, hashes, o una viñeta/número en
    el arranque de una línea). Quita negritas, asteriscos, backticks,
    marcadores de encabezado, viñetas y listas numeradas al inicio de línea,
    y compacta saltos de línea.
    """
    texto = estado.get("cola", "") + texto
    texto = texto.replace("**", "").replace("`", "")
    texto = texto.replace("*", "")
    texto = re.sub(r"(?m)^\s*#{1,6}\s*", "", texto)
    texto = re.sub(r"(?m)^\s*[-*•·]\s*", "", texto)
    antes_num = texto
    texto = re.sub(r"(?m)^\s*\d+[.)]\s*", "", texto)
    if texto != antes_num:
        estado["espacio_pendiente"] = True
    elif estado.pop("espacio_pendiente", False) and texto.startswith((" ", "\t")):
        texto = texto[1:]
    texto = re.sub(r"\n{2,}", "\n", texto)

    cola = ""
    resto = texto
    if resto.endswith(("*", "`", "#")):
        cola = resto[-1]
        resto = resto[:-1]
    else:
        m = re.search(r"(?m)(?:^|\n)((?:\d+)|(?:[-•·]))$", resto)
        if m:
            cola = m.group(1)
            resto = resto[: m.start(1)]
    estado["cola"] = cola
    return resto


def _instruccion_presupuesto(max_tokens):
    if not max_tokens:
        return ""
    return (
        "\nTu presupuesto de tokens es de máximo "
        f"{int(max_tokens)}, pero ese es un LÍMITE MÁXIMO, no una meta: responde "
        "de forma breve, concisa y directa (idealmente 80-250 tokens), sin divagar "
        "ni repetir el contexto. Concluye la idea completamente y no dejes frases "
        "a medias."
        "\nNo agregues una sección final de 'Referencias' ni vuelvas a enumerar las "
        "fuentes: basta con mencionar el nombre del documento cuando sea necesario. "
        "Corrige siempre la ortografía: tildes, ñ y signos adecuados."
        "\nEscribe en párrafos de prosa, sin viñetas, sin listas y sin formato Markdown."
    )


def _build_contexto_texto(contexto_chunks):
    contexto_texto = ""
    for i, chunk in enumerate(contexto_chunks, 1):
        titulo = chunk.get("titulo", "Sin titulo")
        contenido = chunk.get("contenido", "")
        tipo = chunk.get("tipo_nombre", "")
        fuente = f"[{i}] {tipo} - {titulo}"
        contexto_texto += f"\n{fuente}\n{contenido}\n"
    return contexto_texto


def _build_prompt(pregunta, contexto_chunks, guia=None, max_tokens=None):
    contexto_texto = _build_contexto_texto(contexto_chunks)
    user_prompt = (
        f"CONTEXTO DE LEYES Y NORMATIVAS:\n{contexto_texto}\n\n"
        f"PREGUNTA: {pregunta}\n\n"
    )
    if guia:
        user_prompt += f"GUIA DE RESPUESTA: {guia}\n\n"
    user_prompt += "RESPUESTA (en español, en párrafos, sin viñetas ni markdown):"
    system_prompt = SYSTEM_PROMPT + _instruccion_presupuesto(max_tokens)
    return (
        f"<|{IM_START}|>system\n{system_prompt}<|{IM_END}|>\n\n"
        f"<|{IM_START}|>user\n{user_prompt}<|{IM_END}|>\n\n"
        f"<|{IM_START}|>assistant\n"
    )


def seleccionar_chunks_contexto(chunks, pregunta, guia=None, max_tokens=MAX_TOKENS_RESPUESTA):
    limite_prompt = CTX_MAX - max_tokens - SAFETY_MARGIN
    seleccionados = []

    for chunk in chunks:
        candidato = seleccionados + [chunk]
        if _estimar_tokens(_build_prompt(pregunta, candidato, guia, max_tokens)) > limite_prompt:
            break
        seleccionados = candidato

    return seleccionados or chunks[:1]


def construir_prompt_adaptativo(pregunta, contexto_chunks, intencion):
    return _build_prompt(pregunta, contexto_chunks, _guia_para(intencion))


def cargar_modelo():
    global _llm
    if _llm is None:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeError(
                "LLM_MODE=local requiere llama-cpp-python. Use LLM_MODE=external "
                "o instale llama-cpp-python."
            ) from exc
        print("Cargando modelo Qwen2.5 3B...")
        _llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=8,
            n_batch=512,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
        print("Modelo Qwen2.5 3B cargado.")
    return _llm


def _build_messages(pregunta, contexto_chunks, guia=None, max_tokens=None):
    contexto_texto = _build_contexto_texto(contexto_chunks)
    user_prompt = (
        f"CONTEXTO DE LEYES Y NORMATIVAS:\n{contexto_texto}\n\n"
        f"PREGUNTA: {pregunta}\n\n"
    )
    if guia:
        user_prompt += f"GUIA DE RESPUESTA: {guia}\n\n"
    user_prompt += "RESPUESTA (en español, en párrafos, sin viñetas ni markdown):"
    return [
        {"role": "system", "content": SYSTEM_PROMPT + _instruccion_presupuesto(max_tokens)},
        {"role": "user", "content": user_prompt},
    ]


# --- Selección de proveedor externo (aleatoria + con retry) ---


_COOLDOWN_FALLO_SEG = 15 * 60
_fallos_recientes = {}


def _proveedor_env():
    """Proveedor de arranque leido de .env (sin pasar por la tabla)."""
    apikey = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_API_BASE", "").strip()
    if not apikey or not base_url:
        return None
    return {
        "id": None,
        "nombre": os.getenv("LLM_PROVIDER_NAME", "env").strip() or "env",
        "base_url": base_url,
        "apikey": apikey,
        "modelo_base": os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
        "razonamiento_tokens": int(os.getenv("LLM_RAZONAMIENTO_TOKENS", "2048") or 0),
    }


def _proveedores_habilitados():
    """Proveedores habilitados para el sorteo aleatorio.

    Incluye los que tengan `estado_manual=true` y no esten en cooldown por un
    fallo reciente (15 min): respeta `estado_modelo` de la BD y ademas saca del
    sorteo a los que acaban de fallar, para que un proveedor averiado no se
    siga eligiendo primero en cada peticion (sesgaba la seleccion hacia el
    "superviviente" mas fiable). Vencido el cooldown vuelven a participar
    como sonda; si fallan otra vez se re-marcan.

    Si la tabla esta vacia, usa LLM_API_BASE/LLM_API_KEY/LLM_MODEL del .env
    como proveedor de arranque.
    """
    rows = []
    pool = []
    try:
        from ..db.queries import obtener_proveedores_internos
        from .secrets import decrypt_secret

        rows = obtener_proveedores_internos()
        ahora = time.time()
        for r in rows:
            if not (r.get("estado_manual") and r.get("apikey") and r.get("estado_modelo")):
                continue
            fk = _fallos_recientes.get(r["id"])
            en_cooldown = fk is not None and (ahora - fk) < _COOLDOWN_FALLO_SEG
            if en_cooldown:
                continue
            try:
                apikey = decrypt_secret(r["apikey"])
            except Exception:
                continue
            pool.append({
                "id": r["id"],
                "nombre": r["nombre"],
                "base_url": r["base_url"],
                "apikey": apikey,
                "modelo_base": r["modelo_base"],
                "razonamiento_tokens": int(r.get("razonamiento_tokens") or 0),
            })
    except Exception:
        rows = []

    if not rows:
        env = _proveedor_env()
        if env is not None:
            pool.append(env)
    return pool


def _seleccionar_proveedor():
    """Selecciona un proveedor al azar del pool habilitado.

    Devuelve (OpenAI client, modelo_base, proveedor_id, nombre) o None si no hay pool.
    """
    pool = _proveedores_habilitados()
    if not pool:
        return None
    random.shuffle(pool)
    r = pool[0]
    from openai import OpenAI
    client = OpenAI(api_key=r["apikey"], base_url=r["base_url"])
    return client, r["modelo_base"], r["id"], r["nombre"]


def _marcar_estado(proveedor_id, ok: bool):
    """Actualiza estado_modelo y ultima_verificacion en la BD.

    Ademas lleva el instante del ultimo fallo en memoria para el cooldown:
    un proveedor que falla queda fuera del sorteo 15 minutos; los exitos
    lo reincorporan de inmediato.
    """
    clave = proveedor_id if proveedor_id is not None else "env"
    if ok:
        _fallos_recientes.pop(clave, None)
    else:
        _fallos_recientes[clave] = time.time()
    if proveedor_id is None:
        return
    try:
        from ..db.queries import actualizar_estado_modelo_proveedor
        actualizar_estado_modelo_proveedor(proveedor_id, ok)
    except Exception:
        pass


def _hay_proveedores_registrados() -> bool:
    try:
        from ..db.queries import obtener_proveedores_internos
        if obtener_proveedores_internos():
            return True
    except Exception:
        pass
    return _proveedor_env() is not None


def usar_modelo_externo(llm_externo=None):
    if llm_externo is not None:
        return bool(llm_externo)
    return get_modo_global() == "external"


def get_modo_global():
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for linea in f:
                if linea.strip().startswith("LLM_MODE="):
                    valor = linea.strip().split("=", 1)[1].strip()
                    return "external" if valor == "external" else "local"
    except Exception:
        pass
    return _set_modo_global


def _persistir_modo_env(modo):
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        encontrado = False
        for i, linea in enumerate(lineas):
            if linea.strip().startswith("LLM_MODE="):
                lineas[i] = f"LLM_MODE={modo}\n"
                encontrado = True
                break
        if not encontrado:
            lineas.append(f"LLM_MODE={modo}\n")
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(lineas)
    except Exception:
        pass


def set_modo_global(modo, persistir=True):
    global _set_modo_global
    modo = "external" if str(modo).strip().lower() == "external" else "local"
    _set_modo_global = modo
    if persistir:
        _persistir_modo_env(modo)
    return modo


# --- Generación con modelo externo (selección aleatoria + retry) ---

_soporta_reasoning_effort = {}
_CALIBRAR_PASO = 64


class _RespuestaVaciaError(Exception):
    """El proveedor respondio pero sin texto visible (razonamiento le consumio el presupuesto)."""


def _max_tokens_api(max_tokens, razonamiento_tokens):
    """Tope interno de la API: salida visible + margen de razonamiento calibrado."""
    return max_tokens + min(max(0, int(razonamiento_tokens or 0)), RAZONAMIENTO_MAX)


def _llamar_externo(client, modelo, messages, max_tokens, stream=False, razonamiento_tokens=0, timeout=30):
    """Llama a una API OpenAI-compatible.

    `max_tokens` es el tope de la respuesta de SALIDA (visible). Para modelos que
    razonan, se amplia el tope interno con un margen calibrado por uso real, de
    modo que el razonamiento no recorte la respuesta visible. Se pide
    `reasoning_effort: "low"` a todos los proveedores que lo acepten (el
    resultado se cac de memoria para no reenviar el parametro a los que lo
    rechazan con 400).

    Se añade `timeout` (segundos) para evitar que un proveedor lento/cuélgue
    bloquee la petición completa. Si se excede, se lanza excepción que el
    bucle de proveedores capturará para probar el siguiente.
    """
    api_max = _max_tokens_api(max_tokens, razonamiento_tokens)
    kwargs = dict(
        model=modelo,
        messages=messages,
        max_tokens=api_max,
        temperature=0.1,
        timeout=timeout,  # <--- NUEVO: timeout por proveedor
    )
    if stream:
        kwargs["stream_options"] = {"include_usage": True}
    key = (str(getattr(client, "base_url", "")).rstrip("/"), modelo)
    if _soporta_reasoning_effort.get(key, True):
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    try:
        create = client.chat.completions.create
        return create(stream=True, **kwargs) if stream else create(**kwargs)
    except Exception as e:
        if "extra_body" in kwargs and getattr(e, "status_code", None) == 400:
            _soporta_reasoning_effort[key] = False
            kwargs.pop("extra_body")
            create = client.chat.completions.create
            return create(stream=True, **kwargs) if stream else create(**kwargs)
        raise


def _estimar_uso_fallback(messages, texto_total):
    """Estima tokens cuando el proveedor no devuelve usage (stream)."""
    prompt_chars = sum(len(m.get("content", "") or "") for m in messages)
    return _estimar_tokens(prompt_chars), _estimar_tokens(texto_total)


def _calibrar_razonamiento(proveedor_id, prev, tokens_completados, texto_visible, max_tokens, truncado):
    """Ajusta el margen de razonamiento de un proveedor tras una llamada util.

    Reglas (robusteces ante cortes y respuestas vacias):
    - Respuesta vacia: el razonamiento se comio el presupuesto -> sube un paso
      (excluyendo al maximo `RAZONAMIENTO_MAX`).
    - Recorte por tope (`truncado`) con salida util que NO alcanzo `max_tokens`:
      sube un paso para dar margen a la proxima llamada. Si ya alcanzo el tope
      de salida, no cambia (el modelo solo queria escribir mas).
    - Fin natural: EMA hacia el overhead real (completion - visible), de modo
      que el margen baja cuando el modelo razona menos (gasto minimo).
    """
    texto_visible = (texto_visible or "").strip()
    visible = _estimar_tokens(texto_visible)
    completados = max(0, int(tokens_completados or 0))
    prev = max(0, int(prev or 0))
    if not texto_visible:
        nuevo = min(prev + _CALIBRAR_PASO, RAZONAMIENTO_MAX)
    elif truncado:
        if visible < max(1, int(max_tokens or MAX_TOKENS_RESPUESTA)):
            nuevo = min(prev + _CALIBRAR_PASO, RAZONAMIENTO_MAX)
        else:
            nuevo = prev
    else:
        overhead = min(max(0, completados - visible), RAZONAMIENTO_MAX)
        nuevo = int(round(0.7 * prev + 0.3 * overhead))
    if proveedor_id is None:
        return nuevo
    try:
        from ..db.queries import actualizar_razonamiento_tokens_proveedor
        actualizar_razonamiento_tokens_proveedor(proveedor_id, nuevo)
    except Exception:
        pass
    return nuevo


def generar_respuesta_externo(pregunta, contexto_chunks, guia=None, max_tokens=None):
    max_tokens = max_tokens or MAX_TOKENS_RESPUESTA
    messages = _build_messages(pregunta, contexto_chunks, guia, max_tokens)

    if not _hay_proveedores_registrados():
        raise ValueError(
            "No hay proveedores externos en la BD. "
            "Crea uno en /llm/proveedores."
        )

    pool = _proveedores_habilitados()
    if not pool:
        raise ValueError(
            "Todos los proveedores están deshabilitados o fallaron la verificación. "
            "Activa alguno en /llm/proveedores o ejecuta verificar_proveedores.py."
        )

    import random
    random.shuffle(pool)
    last_error = None

    for prov in pool:
        from openai import OpenAI
        client = OpenAI(api_key=prov["apikey"], base_url=prov["base_url"])
        try:
            resultado = _llamar_externo(
                client, prov["modelo_base"], messages, max_tokens,
                razonamiento_tokens=prov["razonamiento_tokens"],
            )
            _marcar_estado(prov["id"], True)
            respuesta = (resultado.choices[0].message.content or "").strip()
            tokens = getattr(resultado, "usage", None)
            tokens = tokens.completion_tokens if tokens else len(respuesta) // 4
            api_max_uso = _max_tokens_api(max_tokens, prov["razonamiento_tokens"])
            finish = getattr(resultado.choices[0], "finish_reason", None)
            truncado = (finish == "length") or (finish is None and int(tokens or 0) >= api_max_uso)
            _calibrar_razonamiento(prov["id"], prov["razonamiento_tokens"], tokens, respuesta, max_tokens, truncado)
            if not respuesta:
                raise _RespuestaVaciaError("El proveedor devolvió una respuesta vacía")
            return {"respuesta": respuesta, "tokens": tokens}
        except _RespuestaVaciaError:
            last_error = _RespuestaVaciaError("respuesta vacía en todos los proveedores")
            continue
        except Exception as e:
            is_rate_limit = type(e).__name__ in ("RateLimitError",) or getattr(e, "status_code", None) == 429
            if is_rate_limit:
                _marcar_estado(prov["id"], True)  # no es fallo de salud
            else:
                _marcar_estado(prov["id"], False)
            last_error = e
            continue

    raise ValueError(
        f"Ningún proveedor respondió correctamente. "
        f"Último error: {last_error}"
    )


def generar_respuesta_stream_externo(pregunta, contexto_chunks, guia=None, max_tokens=None, contexto_uso=None):
    max_tokens = max_tokens or MAX_TOKENS_RESPUESTA
    messages = _build_messages(pregunta, contexto_chunks, guia, max_tokens)

    if not _hay_proveedores_registrados():
        raise ValueError(
            "No hay proveedores externos en la BD. "
            "Crea uno en /llm/proveedores."
        )

    pool = _proveedores_habilitados()
    if not pool:
        raise ValueError(
            "Todos los proveedores están deshabilitados o fallaron la verificación. "
            "Activa alguno en /llm/proveedores o ejecuta verificar_proveedores.py."
        )

    import random
    random.shuffle(pool)
    max_intentos = 3  # probamos como mucho 3 proveedores por llamada
    intentos = 0
    last_error = None

    for prov in pool:
        intentos += 1
        if intentos > max_intentos:
            raise ValueError(
                f"Ninguno de los primeros {max_intentos} proveedores respondió. "
                "Intenta nuevamente más tarde o contacta soporte."
            )

        from openai import OpenAI
        client = OpenAI(api_key=prov["apikey"], base_url=prov["base_url"])
        try:
            stream = _llamar_externo(
                client, prov["modelo_base"], messages, max_tokens, stream=True,
                razonamiento_tokens=prov["razonamiento_tokens"],
                timeout=30,  # 30 segundos máximo por proveedor
            )
            _marcar_estado(prov["id"], True)
            if contexto_uso is not None:
                contexto_uso.update({
                    "proveedor_id": prov["id"],
                    "proveedor_nombre": prov["nombre"],
                    "modelo": prov["modelo_base"],
                })
            tokens_prompt = tokens_comp = 0
            texto_total = ""
            finish = None
            for chunk in stream:
                usage = getattr(chunk, "usage", None)
                if usage:
                    tokens_prompt = getattr(usage, "prompt_tokens", 0) or tokens_prompt
                    tokens_comp = getattr(usage, "completion_tokens", 0) or tokens_comp
                if chunk.choices:
                    fr = getattr(chunk.choices[0], "finish_reason", None)
                    if fr:
                        finish = fr
                    delta = chunk.choices[0].delta
                    texto = getattr(delta, "content", None)
                    if texto:
                        texto_total += texto
                        yield texto
            if not tokens_prompt and not tokens_comp:
                tokens_prompt, tokens_comp = _estimar_uso_fallback(messages, texto_total)
            api_max_uso = _max_tokens_api(max_tokens, prov["razonamiento_tokens"])
            truncado = (finish == "length") or (finish is None and int(tokens_comp or 0) >= api_max_uso)
            _calibrar_razonamiento(prov["id"], prov["razonamiento_tokens"], tokens_comp, texto_total, max_tokens, truncado)
            if not texto_total.strip():
                raise _RespuestaVaciaError("El proveedor devolvió una respuesta vacía")
            if contexto_uso is not None:
                contexto_uso.update({
                    "proveedor_id": prov["id"],
                    "proveedor_nombre": prov["nombre"],
                    "modelo": prov["modelo_base"],
                    "tokens_prompt": tokens_prompt,
                    "tokens_completados": tokens_comp,
                })
            yield ""
            return
        except _RespuestaVaciaError:
            last_error = _RespuestaVaciaError("respuesta vacía en todos los proveedores")
            continue
        except Exception as e:
            is_rate_limit = type(e).__name__ in ("RateLimitError",) or getattr(e, "status_code", None) == 429
            if is_rate_limit:
                _marcar_estado(prov["id"], True)
            else:
                _marcar_estado(prov["id"], False)
            last_error = e
            continue

    raise ValueError(
        f"Ningún proveedor respondió correctamente. "
        f"Último error: {last_error}"
    )


def generar_respuesta(pregunta, contexto_chunks, guia=None, max_tokens=None, llm_externo=None):
    max_tokens = max_tokens or MAX_TOKENS_RESPUESTA
    if usar_modelo_externo(llm_externo):
        return generar_respuesta_externo(pregunta, contexto_chunks, guia=guia, max_tokens=max_tokens)

    llm = cargar_modelo()
    prompt = _build_prompt(pregunta, contexto_chunks, guia, max_tokens)

    resultado = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.1,
        stop=[f"<|{IM_END}|>"],
    )

    respuesta = resultado["choices"][0]["text"].strip()
    tokens = resultado["usage"]["completion_tokens"]

    return {
        "respuesta": respuesta,
        "tokens": tokens,
    }


def generar_respuesta_stream(pregunta, contexto_chunks, guia=None, max_tokens=None, llm_externo=None, contexto_uso=None):
    max_tokens = max_tokens or MAX_TOKENS_RESPUESTA
    if usar_modelo_externo(llm_externo):
        yield from generar_respuesta_stream_externo(pregunta, contexto_chunks, guia=guia, max_tokens=max_tokens, contexto_uso=contexto_uso)
        return

    llm = cargar_modelo()
    prompt = _build_prompt(pregunta, contexto_chunks, guia, max_tokens)

    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.1,
        stop=[f"<|{IM_END}|>"],
        stream=True,
    )

    if contexto_uso is not None:
        contexto_uso.update({
            "proveedor_id": None,
            "proveedor_nombre": None,
            "modelo": "local/qwen2.5-3b",
        })

    tokens = 0
    for chunk in stream:
        texto = chunk["choices"][0]["text"]
        if texto:
            tokens += 1
            yield texto

    if contexto_uso is not None:
        contexto_uso.update({
            "proveedor_id": None,
            "proveedor_nombre": None,
            "modelo": "local/qwen2.5-3b",
            "tokens_prompt": _estimar_tokens(prompt),
            "tokens_completados": tokens,
        })
    yield ""
