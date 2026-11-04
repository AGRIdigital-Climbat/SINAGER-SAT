import re
import unicodedata

from .embeddings import generar_embedding, generar_embeddings_lote, liberar_modelo
from .llm import generar_respuesta
from .chunking import detectar_secciones, chunk_texto
from ..db.queries import (
    _normalizar_ids_documento,
    crear_documento,
    eliminar_documento,
    insertar_chunk,
    buscar_por_tipo,
    buscar_por_texto,
    buscar_chunks_por_termino,
    listar_tipos_documento,
    listar_tipos_por_documentos,
)

PESOS_INTENCION = {
    "definicion": (0.7, 0.3),
    "procedimiento": (0.4, 0.6),
    "autoridad": (0.3, 0.7),
    "requisito": (0.5, 0.5),
    "plazo": (0.6, 0.4),
    "general": (0.3, 0.7),
}

PALABRAS_VACIAS = {
    "a", "al", "ante", "bajo", "cabe", "con", "contra", "de", "del", "desde",
    "en", "entre", "hacia", "hasta", "para", "por", "según", "sin", "sobre",
    "tras", "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "u", "ni", "que", "cual", "cuales", "como", "cuando", "donde", "quien",
    "quienes", "es", "son", "era", "eran", "fue", "se", "le", "les", "me",
    "te", "nos", "lo", "cuál", "cuáles", "cómo", "cuándo", "dónde", "quién",
    "cuánto", "cuántos", "cuanta", "cuantas", "que", "cual", "está", "esta",
    "están", "existe", "existen", "hay", "puede", "pueden", "debe", "deben",
    "debería", "deberían", "tiene", "tienen", "ser", "hacer", "sobre", "más",
    "mas", "muy", "bien", "solo", "segun",
}


def procesar_documento(titulo, tipo_id, fecha_publicacion, archivo_path, contenido, num_paginas=None, metadatos=None):
    documento_id = crear_documento(
        titulo=titulo,
        tipo_id=tipo_id,
        fecha_publicacion=fecha_publicacion,
        archivo_path=archivo_path,
        contenido_completo=contenido,
        num_paginas=num_paginas,
        metadatos=metadatos,
    )

    try:
        secciones = detectar_secciones(contenido)
        if not secciones:
            secciones = chunk_texto(contenido)

        textos = [s["contenido"] for s in secciones]
        embeddings = generar_embeddings_lote(textos)

        for i, (seccion, embedding) in enumerate(zip(secciones, embeddings)):
            insertar_chunk(
                documento_id=documento_id,
                contenido=seccion["contenido"],
                numeral=seccion.get("numeral", ""),
                orden=seccion.get("orden", i),
                embedding=embedding,
            )

        liberar_modelo()

        return {
            "documento_id": documento_id,
            "total_chunks": len(secciones),
            "num_paginas": num_paginas,
            "titulo": titulo,
        }
    except Exception:
        try:
            eliminar_documento(documento_id)
        except Exception:
            pass
        raise


def buscar_cascada(embedding, umbral=0.75, limite=15, tipo_id=None, documento_id=None, documento_ids=None, chunk_ids=None):
    embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
    ids = _normalizar_ids_documento(documento_id, documento_ids)

    if ids:
        tipos_ids = listar_tipos_por_documentos(ids)
        if not tipos_ids:
            return []
        lista_temporal = []
        for tipo in tipos_ids:
            resultados = buscar_por_tipo(embedding_str, tipo, umbral, documento_ids=ids, chunk_ids=chunk_ids)
            lista_temporal.extend(resultados)
        lista_temporal.sort(key=lambda x: x["similitud"], reverse=True)
        return lista_temporal[:limite]

    if tipo_id:
        return buscar_por_tipo(embedding_str, tipo_id, umbral, chunk_ids=chunk_ids)[:limite]

    tipos = listar_tipos_documento()
    lista_temporal = []

    for tipo in tipos:
        resultados = buscar_por_tipo(embedding_str, tipo["id"], umbral, chunk_ids=chunk_ids)
        lista_temporal.extend(resultados)

    lista_temporal.sort(key=lambda x: x["similitud"], reverse=True)

    chunks_finales = lista_temporal[:limite]

    return chunks_finales


def responder(pregunta, limite=15, umbral=0.75, tipo_id=None, documento_id=None, documento_ids=None):
    embedding_pregunta = generar_embedding(pregunta)

    chunks = buscar_cascada(embedding_pregunta, umbral=umbral, limite=limite, tipo_id=tipo_id, documento_id=documento_id, documento_ids=documento_ids)

    if not chunks:
        return {
            "respuesta": "No encontre documentos relevantes para su pregunta.",
            "fuentes": [],
        }

    resultado = generar_respuesta(pregunta, chunks)

    fuentes = deduplicar_fuentes(chunks)

    return {
        "respuesta": resultado["respuesta"],
        "tokens": resultado["tokens"],
        "fuentes": fuentes,
    }


def deduplicar_fuentes(chunks):
    seen = {}
    for chunk in chunks:
        doc_id = chunk.get("documento_id")
        similitud = float(chunk.get("similitud", 0))
        numeral = chunk.get("numeral", "")
        prioridad = chunk.get("prioridad")
        if doc_id not in seen:
            seen[doc_id] = {
                "documento_id": doc_id,
                "titulo": chunk.get("titulo", ""),
                "tipo": chunk.get("tipo_nombre", ""),
                "prioridad": prioridad,
                "numerals": [],
                "similitud": round(similitud, 4),
            }
        entry = seen[doc_id]
        if similitud > entry["similitud"]:
            entry["similitud"] = round(similitud, 4)
        if numeral and numeral not in entry["numerals"]:
            entry["numerals"].append(numeral)
    resultado = sorted(seen.values(), key=lambda x: x["similitud"], reverse=True)
    for r in resultado:
        if len(r["numerals"]) > 3:
            r["numerals"] = r["numerals"][:3]
            r["numerals_truncados"] = True
        else:
            r["numerals_truncados"] = False
    return resultado


def busqueda_semantica(pregunta, limite=15, umbral=0.75, tipo_id=None, documento_id=None, documento_ids=None):
    embedding_pregunta = generar_embedding(pregunta)

    chunks = buscar_cascada(embedding_pregunta, umbral=umbral, limite=limite, tipo_id=tipo_id, documento_id=documento_id, documento_ids=documento_ids)

    resultados = []
    for chunk in chunks:
        resultados.append({
            "documento_id": chunk["documento_id"],
            "titulo": chunk.get("titulo", ""),
            "tipo": chunk.get("tipo_nombre", ""),
            "numeral": chunk.get("numeral", ""),
            "contenido": chunk.get("contenido", ""),
            "similitud": round(float(chunk.get("similitud", 0)), 4),
        })

    return resultados


def _quitar_acentos(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def _extraer_keywords(pregunta):
    limpia = _quitar_acentos(pregunta.lower())
    tokens = re.findall(r"[a-zñ]+", limpia)
    keywords = []
    for token in tokens:
        if token in PALABRAS_VACIAS or len(token) < 3:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords


def detectar_intencion(pregunta):
    p = _quitar_acentos(pregunta.lower())

    if any(w in p for w in ["plazo", "vigencia", "cuanto tiempo", "cuando",
                            "fecha", "periodo", "tiempo limite", "en que plazo",
                            "por cuanto", "dura", "duracion"]):
        return "plazo"
    if any(w in p for w in ["definicion", "definir", "significa", "significado",
                            "concepto", "glosario", "termino", "que es",
                            "que son", "cual es", "cuales son", "se entiende",
                            "definido", "concepto de", "significan"]):
        return "definicion"
    if any(w in p for w in ["procedimiento", "como se", "como debe", "pasos",
                            "etapas", "proceso", "paso a paso", "como declarar",
                            "como solicitar", "como atender", "como registrar",
                            "como actuar", "de que manera"]):
        return "procedimiento"
    if any(w in p for w in ["quien", "autoridad", "competencia", "responsable",
                            "encargado", "ministerio", "entidad", "institucion",
                            "comite", "que organo", "que autoridad"]):
        return "autoridad"
    if any(w in p for w in ["requisito", "requisitos", "condiciones",
                            "requiere", "necesita", "se necesita", "debe cumplir",
                            "requisitos para", "que se requiere"]):
        return "requisito"

    return "general"


def _bono_definicion(chunk, keywords):
    contenido = _quitar_acentos(chunk.get("contenido", "")).lower()
    if not contenido:
        return 0.0
    # Bono principal: +0.5 si el keyword appears anywhere in the chunk content
    # (antes solo sumaba +0.3 si tenia formato "keyword:" o "keyword=")
    for k in keywords:
        if k.lower() in contenido:
            return 0.5
    # Bono secundario opcional: +0.3 si aparece con formato "keyword:" o "keyword="
    alternativas = "|".join(re.escape(k) for k in keywords)
    patron = (
        r"(?m)^\s*(?:[a-z0-9]{1,4}\.\s*|[-–•*]\s*)?("
        + alternativas
        + r")\s*[:=]"
    )
    if re.search(patron, contenido):
        return 0.3
    return 0.0


def buscar_hibrido_inteligente(pregunta, limite=15, umbral=0.35, tipo_id=None, documento_id=None, documento_ids=None, termino=None):
    intencion = detectar_intencion(pregunta)
    peso_texto, peso_semantica = PESOS_INTENCION[intencion]
    keywords = _extraer_keywords(pregunta)
    try:
        embedding_pregunta = generar_embedding(pregunta)
    except Exception:
        embedding_pregunta = None

    def _fusionar(chunk_ids=None, umbral_busqueda=None, filtrar_umbral=True):
        u_busqueda = umbral if umbral_busqueda is None else umbral_busqueda
        if embedding_pregunta is None:
            sem_chunks = []
        else:
            sem_chunks = buscar_cascada(
                embedding_pregunta, umbral=u_busqueda, limite=limite * 2,
                tipo_id=tipo_id, documento_id=documento_id, documento_ids=documento_ids,
                chunk_ids=chunk_ids,
            )
        texto_chunks = buscar_por_texto(
            keywords, limite=limite * 2, tipo_id=tipo_id,
            documento_id=documento_id, documento_ids=documento_ids, chunk_ids=chunk_ids,
        )

        fusion = {}
        for chunk in sem_chunks:
            fusion[chunk["id"]] = {"chunk": chunk, "sem": float(chunk["similitud"]), "txt": 0.0}
        for chunk in texto_chunks:
            cid = chunk["id"]
            if cid in fusion:
                fusion[cid]["txt"] = float(chunk["similitud"])
            else:
                fusion[cid] = {"chunk": chunk, "sem": 0.0, "txt": float(chunk["similitud"])}

        resultados = []
        for cid, data in fusion.items():
            puntaje = peso_texto * data["txt"] + peso_semantica * data["sem"]
            if intencion == "definicion":
                puntaje += _bono_definicion(data["chunk"], keywords)
            puntaje = min(1.0, puntaje)
            chunk = dict(data["chunk"])
            chunk["similitud"] = round(puntaje, 4)
            chunk["similitud_semantica"] = round(data["sem"], 4)
            chunk["similitud_textual"] = round(data["txt"], 4)
            resultados.append(chunk)

        resultados.sort(key=lambda x: x["similitud"], reverse=True)

        if filtrar_umbral and umbral:
            resultados = [r for r in resultados if r["similitud"] >= umbral]

        return resultados[:limite]

    # Etapa por termino (seccion/pantalla): solo si llega `termino` junto a
    # `documento_id`/`documento_ids` (p.ej. EDAN con grupo_id). Primero acota al
    # contenido de esa seccion y dentro de el busca/ordena la pregunta. Dentro de
    # la seccion no se exige el umbral global: la restriccion ya aporta la
    # precision. Si la seccion no matchea, cae a la busqueda normal (no falla).
    if termino:
        term_kw = _extraer_keywords(termino)
        ids = _normalizar_ids_documento(documento_id, documento_ids)
        if term_kw and ids:
            term_ids = [
                c["id"] for c in buscar_chunks_por_termino(term_kw, ids, limite=limite * 3, exigir_todos=True)
            ]
            if not term_ids and len(term_kw) > 1:
                term_ids = [
                    c["id"] for c in buscar_chunks_por_termino(term_kw, ids, limite=limite * 3, exigir_todos=False)
                ]
            if term_ids:
                restringido = _fusionar(chunk_ids=term_ids, umbral_busqueda=0.0, filtrar_umbral=False)
                if restringido:
                    return restringido, intencion

    return _fusionar(), intencion


def busqueda_hibrida(pregunta, limite=15, umbral=0.30, tipo_id=None, documento_id=None, documento_ids=None, termino=None):
    chunks, intencion = buscar_hibrido_inteligente(
        pregunta=pregunta, limite=limite, umbral=umbral, tipo_id=tipo_id, documento_id=documento_id, documento_ids=documento_ids, termino=termino
    )

    resultados = []
    for chunk in chunks:
        resultados.append({
            "documento_id": chunk["documento_id"],
            "titulo": chunk.get("titulo", ""),
            "tipo": chunk.get("tipo_nombre", ""),
            "numeral": chunk.get("numeral", ""),
            "contenido": chunk.get("contenido", ""),
            "similitud": round(float(chunk.get("similitud", 0)), 4),
        })

    return resultados, intencion
