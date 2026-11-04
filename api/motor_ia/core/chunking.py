import re

# Límite óptimo para all-MiniLM-L6-v2 (256 tokens ≈ 600 chars en español)
MAX_CHUNK_CHARS = 600
OVERLAP_CHARS = 100


def _dividir_texto_largo(texto, numeral_base, orden_inicio):
    """Divide un texto largo en sub-chunks con overlap."""
    chunks = []
    if len(texto) <= MAX_CHUNK_CHARS:
        chunks.append({
            "numeral": numeral_base,
            "contenido": texto,
            "orden": orden_inicio,
        })
        return chunks

    inicio = 0
    orden = orden_inicio
    while inicio < len(texto):
        fin = inicio + MAX_CHUNK_CHARS
        sub = texto[inicio:fin]

        # Si no es el último trozo y hay espacio, cortar en palabra completa
        if fin < len(texto):
            ultimo_espacio = sub.rfind(" ")
            if ultimo_espacio > MAX_CHUNK_CHARS // 2:
                sub = sub[:ultimo_espacio]

        sufijo = f" (parte {len(chunks) + 1})" if len(chunks) > 0 or inicio > 0 else ""
        chunks.append({
            "numeral": f"{numeral_base}{sufijo}",
            "contenido": sub.strip(),
            "orden": orden,
        })
        orden += 1
        inicio += MAX_CHUNK_CHARS - OVERLAP_CHARS

    return chunks


def detectar_secciones(texto):
    # Regex con soporte para "Artículo" (con tilde) y "Articulo" / "Art."
    patron = re.compile(
        r"(?:Art[ií]culo|Art\.)\s+(\d+)[\.\s—–\-]*(.+?)(?=(?:Art[ií]culo|Art\.)\s+\d+|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    matches = patron.findall(texto)

    if not matches:
        return _chunking_parrafos(texto)

    chunks = []
    orden = 0
    for num, contenido in matches:
        contenido_limpio = contenido.strip()
        if len(contenido_limpio) < 20:
            continue
        numeral = f"Artículo {num}"
        sub_chunks = _dividir_texto_largo(contenido_limpio, numeral, orden)
        chunks.extend(sub_chunks)
        orden += len(sub_chunks)

    return chunks


def _chunking_parrafos(texto):
    """Fallback: dividir por párrafos (doble salto de línea)."""
    parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    chunks = []
    orden = 0
    for i, p in enumerate(parrafos):
        if len(p) < 20:
            continue
        numeral = f"Parrafo {i + 1}"
        sub_chunks = _dividir_texto_largo(p, numeral, orden)
        chunks.extend(sub_chunks)
        orden += len(sub_chunks)
    return chunks


def chunk_texto(texto, max_longitud=1000, superposicion=100):
    """División por palabras con overlap. Usado como último fallback."""
    chunks = []
    palabras = texto.split()
    inicio = 0
    orden = 0

    while inicio < len(palabras):
        fin = inicio + max_longitud
        chunk_palabras = palabras[inicio:fin]
        chunk_texto_str = " ".join(chunk_palabras)
        chunks.append({
            "numeral": f"Seccion {orden + 1}",
            "contenido": chunk_texto_str,
            "orden": orden,
        })
        orden += 1
        inicio += max_longitud - superposicion

    return chunks
