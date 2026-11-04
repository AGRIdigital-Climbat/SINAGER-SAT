import random
import re
import time
from collections import defaultdict

from .embeddings import generar_embedding, liberar_modelo
from .rag import buscar_cascada, buscar_hibrido_inteligente, deduplicar_fuentes
from .llm import generar_respuesta, seleccionar_chunks_contexto, _guia_para
from ..db.queries import obtener_documento, listar_chunks_documento, listar_contenidos_documentos


def _dividir_oraciones(texto):
    """Divide texto en oraciones para generar preguntas de prueba."""
    oraciones = re.split(r'(?<=[.;])\s+', texto)
    return [o.strip() for o in oraciones if len(o.strip()) >= 30]


def verificar_documento(documento_id, num_preguntas=10):
    """
    Ejecuta pruebas de calidad de búsqueda para un documento.

    Selecciona oraciones aleatorias del documento como queries,
    busca en la BD y verifica si el chunk correcto aparece en top-5.
    """
    doc = obtener_documento(documento_id)
    if not doc:
        return {"error": "Documento no encontrado"}

    contenido = doc["contenido_completo"]
    chunks_doc = listar_chunks_documento(documento_id)
    total_chunks = len(chunks_doc)

    if total_chunks == 0:
        return {
            "documento_id": documento_id,
            "total_chunks": 0,
            "total_queries": 0,
            "precision_at_1": 0,
            "precision_at_3": 0,
            "precision_at_5": 0,
            "average_similarity": 0,
            "queries": [],
        }

    oraciones = _dividir_oraciones(contenido)
    if not oraciones:
        return {
            "documento_id": documento_id,
            "total_chunks": total_chunks,
            "total_queries": 0,
            "precision_at_1": 0,
            "precision_at_3": 0,
            "precision_at_5": 0,
            "average_similarity": 0,
            "queries": [],
        }

    num_preguntas = min(num_preguntas, len(oraciones))
    preguntas = random.sample(oraciones, num_preguntas)

    resultados = []
    aciertos_1 = 0
    aciertos_3 = 0
    aciertos_5 = 0
    suma_similitud = 0
    chunks_encontrados = set()

    for pregunta in preguntas:
        embedding = generar_embedding(pregunta)
        chunks = buscar_cascada(embedding, umbral=0.0, limite=5)

        found_position = 0
        found_similarity = 0.0
        found_numeral = ""
        found_contenido = ""

        for i, chunk in enumerate(chunks):
            if chunk["documento_id"] == documento_id:
                found_position = i + 1
                found_similarity = float(chunk.get("similitud", 0))
                found_numeral = chunk.get("numeral", "")
                found_contenido = str(chunk.get("contenido", ""))[:300]
                chunks_encontrados.add(chunk["id"])
                break

        passed = found_position > 0
        if found_position == 1:
            aciertos_1 += 1
        if 0 < found_position <= 3:
            aciertos_3 += 1
        if 0 < found_position <= 5:
            aciertos_5 += 1
        suma_similitud += found_similarity

        resultados.append({
            "query": pregunta[:120],
            "expected_numeral": "",
            "found_numeral": found_numeral,
            "found_position": found_position,
            "similitud": round(found_similarity, 4),
            "respuesta": found_contenido,
            "passed": passed,
        })

    n = num_preguntas
    liberar_modelo()

    return {
        "documento_id": documento_id,
        "titulo": doc.get("titulo", ""),
        "total_chunks": total_chunks,
        "total_queries": n,
        "precision_at_1": round(aciertos_1 / n, 4) if n else 0,
        "precision_at_3": round(aciertos_3 / n, 4) if n else 0,
        "precision_at_5": round(aciertos_5 / n, 4) if n else 0,
        "average_similarity": round(suma_similitud / n, 4) if n else 0,
        "queries": resultados,
    }


def _metricas_grupo(acc):
    total = acc["total"]
    if total == 0:
        return None
    return {
        "total": total,
        "precision_at_1": round(acc["top1"] / total, 4),
        "precision_at_3": round(acc["top3"] / total, 4),
        "precision_at_5": round(acc["top5"] / total, 4),
        "average_similarity": round(acc["sum_sim"] / total, 4),
    }


def _registrar_acierto(acc, pos, similitud):
    acc["total"] += 1
    if pos == 1:
        acc["top1"] += 1
    if 0 < pos <= 3:
        acc["top3"] += 1
    if 0 < pos <= 5:
        acc["top5"] += 1
    acc["sum_sim"] += similitud


def verificar_sistema(num_preguntas=20, num_respuestas_llm=4, umbral=0.0):
    """
    Evalúa la calidad de todo el sistema de búsqueda y respuestas.

    Toma oraciones reales al azar de todos los documentos indexados y las usa
    como consultas contra el mismo buscador híbrido que usa el chat. Mide en qué
    posición aparece el fragmento fuente de cada consulta, desglosa los
    resultados por intención de búsqueda y por tipo de norma, y opcionalmente
    prueba las respuestas generadas por el modelo de lenguaje.
    """
    docs = listar_contenidos_documentos()
    if not docs:
        return {"error": "No hay documentos indexados para evaluar"}

    pool = []
    for doc in docs:
        contenido = doc.get("contenido_completo") or ""
        for oracion in _dividir_oraciones(contenido):
            pool.append((oracion, doc))

    num_preguntas = min(num_preguntas, len(pool))
    if num_preguntas == 0:
        return {
            "error": "No se pudo extraer oraciones suficientes para evaluar",
        }

    muestras = random.sample(pool, num_preguntas)

    por_intencion = defaultdict(lambda: {"total": 0, "top1": 0, "top3": 0, "top5": 0, "sum_sim": 0.0})
    por_tipo = defaultdict(lambda: {
        "tipo_id": None, "tipo_nombre": "", "prioridad": 0,
        "total": 0, "top1": 0, "top3": 0, "top5": 0, "sum_sim": 0.0,
    })

    global_acc = {"total": 0, "top1": 0, "top3": 0, "top5": 0, "sum_sim": 0.0}
    resultados = []

    for oracion, doc in muestras:
        doc_id = doc["id"]
        pregunta = oracion[:120]

        chunks, intencion = buscar_hibrido_inteligente(pregunta, umbral=umbral, limite=5)

        pos = 0
        similitud = 0.0
        contenido_encontrado = ""
        for i, chunk in enumerate(chunks):
            if chunk["documento_id"] == doc_id:
                pos = i + 1
                similitud = float(chunk.get("similitud", 0))
                contenido_encontrado = str(chunk.get("contenido", ""))[:300]
                break

        _registrar_acierto(global_acc, pos, similitud)
        _registrar_acierto(por_intencion[intencion], pos, similitud)

        tipo_acc = por_tipo[doc["tipo_id"]]
        tipo_acc["tipo_id"] = doc["tipo_id"]
        tipo_acc["tipo_nombre"] = doc["tipo_nombre"]
        tipo_acc["prioridad"] = doc["prioridad"]
        _registrar_acierto(tipo_acc, pos, similitud)

        resultados.append({
            "query": pregunta,
            "documento": doc["titulo"],
            "tipo": doc["tipo_nombre"],
            "intencion": intencion,
            "found_position": pos,
            "passed": pos > 0,
            "similitud": round(similitud, 4),
            "respuesta": contenido_encontrado,
        })

    n = global_acc["total"]
    prec1 = global_acc["top1"] / n
    prec3 = global_acc["top3"] / n
    prec5 = global_acc["top5"] / n
    sim_promedio = global_acc["sum_sim"] / n

    indice_general = round(0.45 * prec5 + 0.25 * prec3 + 0.15 * prec1 + 0.15 * sim_promedio, 4)

    lista_intencion = []
    for intencion, acc in sorted(por_intencion.items(), key=lambda x: -x[1]["total"]):
        m = _metricas_grupo(acc)
        if m:
            m["intencion"] = intencion
            lista_intencion.append(m)

    lista_tipo = []
    for acc in por_tipo.values():
        m = _metricas_grupo(acc)
        if m:
            m["tipo_id"] = acc["tipo_id"]
            m["tipo_nombre"] = acc["tipo_nombre"]
            m["prioridad"] = acc["prioridad"]
            lista_tipo.append(m)
    lista_tipo.sort(key=lambda x: x["prioridad"])

    llm = _evaluar_respuestas_llm(muestras[:num_respuestas_llm] if num_respuestas_llm else [], umbral)

    liberar_modelo()

    return {
        "indice_general": indice_general,
        "total_queries": n,
        "total_documentos": len(docs),
        "precision_at_1": round(prec1, 4),
        "precision_at_3": round(prec3, 4),
        "precision_at_5": round(prec5, 4),
        "average_similarity": round(sim_promedio, 4),
        "por_intencion": lista_intencion,
        "por_tipo": lista_tipo,
        "queries": resultados,
        "llm": llm,
    }


def _evaluar_respuestas_llm(muestras, umbral):
    vacio = {
        "total_respuestas": 0,
        "tiempo_promedio_seg": 0,
        "tasa_citacion": 0,
        "tokens_promedio": 0,
        "resultados": [],
    }
    if not muestras:
        return vacio

    tiempos = []
    tokens = []
    citaciones = 0
    detalles = []

    for oracion, doc in muestras:
        pregunta = oracion[:120]
        chunks, intencion = buscar_hibrido_inteligente(pregunta, umbral=umbral, limite=10)
        if not chunks:
            continue

        fuentes = deduplicar_fuentes(chunks)
        doc_ids = {f["documento_id"] for f in fuentes}
        chunks_filtrados = [c for c in chunks if c.get("documento_id") in doc_ids]
        guia = _guia_para(intencion)
        seleccion = seleccionar_chunks_contexto(chunks_filtrados, pregunta, guia=guia)

        t0 = time.time()
        res = generar_respuesta(pregunta, seleccion, guia=guia)
        dt = time.time() - t0

        respuesta = res["respuesta"]
        cito = bool(re.search(r"\[\d+\]", respuesta))

        tiempos.append(dt)
        tokens.append(res["tokens"])
        if cito:
            citaciones += 1

        detalles.append({
            "query": pregunta,
            "documento": doc["titulo"],
            "intencion": intencion,
            "tiempo_seg": round(dt, 2),
            "tokens": res["tokens"],
            "cito_fuentes": cito,
            "respuesta": respuesta[:220],
        })

    total = len(detalles)
    if total == 0:
        return vacio

    return {
        "total_respuestas": total,
        "tiempo_promedio_seg": round(sum(tiempos) / total, 2),
        "tasa_citacion": round(citaciones / total, 4),
        "tokens_promedio": round(sum(tokens) / total, 1),
        "resultados": detalles,
    }
