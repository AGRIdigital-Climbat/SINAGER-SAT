#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga el dato oficial de HOGARES del Censo 2024 (CPV-2024, INE) en:
  - shared.manzanos.hogares / shared.comunidades.hogares  (por unidad, de la ficha)
  - shared.censo2024_hogares_municipio                     (343 municipios, exacto)

Concepto: "hogares" = viviendas particulares ocupadas con personas presentes
(equivalente censal oficial del concepto "familias"; NO se divide
poblacion/viviendas). Unidades sin ficha del INE quedan con hogares = NULL
(reserva estadistica).

Fuentes (en orden de busqueda):
  1. cambios_replicacion/datos/            (carpeta de cambios, version copiada)
  2. datos_censo2024/fuentes/                    (descarga normal del pipeline)
  3. descarga desde internet (si faltan):
       ficha.parquet         -> release data-fichas-v1.0.0 (lab-tecnosocial/censosbo)
       tabulado_vivienda...  -> INE (nube.ine.gob.bo, cuadro 19 "Vivienda y hogar")

Reglas / validaciones (todo o aborta):
  - por unidad: hogares = suma(hogar_*) = viv_tipo_presentes, 0 <= hogares
  - por unidad: se actualiza solo si hogares <= viviendas (reporta descartes)
  - municipios: exactamente 343 filas del cuadro 19 (fila total por municipio,
    columna del anio 2024) y suma = total Bolivia del propio tabulado
  - cruce: SUM(hogares unidades) <= hogares_ine por municipio (reporte)
  - idempotente: re-ejecutable (UPSERT / UPDATE con los mismos valores)

Uso:
  python3 scripts/cargar_hogares_censo2024.py            # --simular (default)
  python3 scripts/cargar_hogares_censo2024.py --simular
  python3 scripts/cargar_hogares_censo2024.py --importar

  DATABASE_URL=postgresql://... python3 scripts/cargar_hogares_censo2024.py ...
"""
import argparse
import hashlib
import os
import sys
import unicodedata
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CAMBIOS = os.path.join(BASE_DIR, "cambios_replicacion", "datos")
DIR_FUENTES = os.path.join(BASE_DIR, "datos_censo2024", "fuentes")

ARCH_FICHA = "ficha.parquet"
ARCH_TABULADO = "tabulado_vivienda_hogar.xlsx"

URL_FICHA = ("https://github.com/lab-tecnosocial/censosbo/releases/"
             "download/data-fichas-v1.0.0/ficha.parquet")
URL_TABULADO = "https://nube.ine.gob.bo/index.php/s/6H760RRaNemfydX/download"

HOGAR_COLS = [
    "hogar_unipersonal", "hogar_pareja", "hogar_monoparental", "hogar_nuclear",
    "hogar_extendido", "hogar_compuesto", "hogar_otro", "hogar_sinjefe",
]
COL_HOGARES = "viv_tipo_presentes"

SHEET_CUADRO_19 = "19"          # "VIVIENDAS PARTICULARES OCUPADAS CON
                                 # PERSONAS PRESENTES POR TIPO DE HOGAR"
COL_2024_TOTAL = 24              # indice 0-based de la columna "Total" (2024)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
)


def norm(s):
    """Minusculas sin tildes y espacios colapsados (para cruzar nombres INE/BD)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolver_fuente(archivo, url):
    """Busca el archivo en cambios_replicacion/ y luego en fuentes/; si
    falta, lo descarga a fuentes/."""
    p_cambios = os.path.join(DIR_CAMBIOS, archivo)
    p_fuentes = os.path.join(DIR_FUENTES, archivo)
    for p in (p_cambios, p_fuentes):
        if os.path.isfile(p):
            print(f"  [fuente] {p}")
            return p
    print(f"  [descarga] {url}")
    os.makedirs(DIR_FUENTES, exist_ok=True)
    tmp = p_fuentes + ".part"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, p_fuentes)
    print(f"  [guardado] {p_fuentes}")
    return p_fuentes


def leer_fichas(path):
    """(codigo_ine, hogares) por unidad con ficha; valida por fila."""
    import pyarrow.parquet as pq

    cols = ["codigo", COL_HOGARES] + HOGAR_COLS
    table = pq.read_table(path, columns=cols)
    data = table.to_pydict()
    n = table.num_rows
    out = []
    malas = {"suma": 0, "negativo": 0}
    for i in range(n):
        codigo = str(data["codigo"][i])
        hogares = data[COL_HOGARES][i]
        hogares = 0 if hogares is None else int(hogares)
        suma = sum(0 if data[c][i] is None else int(data[c][i]) for c in HOGAR_COLS)
        if suma != hogares:
            malas["suma"] += 1
        if hogares < 0:
            malas["negativo"] += 1
        out.append((codigo, hogares))
    if malas["suma"] or malas["negativo"]:
        sys.exit(f"  ERROR: fichas invalidas (suma hogar_* != {COL_HOGARES}: "
                 f"{malas['suma']}, negativos: {malas['negativo']})")
    print(f"  [fichas] {n} unidades, validacion suma(hogar_*)=={COL_HOGARES}: OK")
    return out


def leer_tabulado(path):
    """dict (dep, prov, muni) normalizados -> hogares (fila total, anio 2024)
    mas el total nacional (fila Pais/Bolivia) del propio cuadro 19."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[SHEET_CUADRO_19]
    munis = {}
    total_pais = None
    for row in ws.iter_rows(min_row=9, values_only=True):
        nivel = row[2]
        if nivel == "País" and row[6] == "Bolivia":
            total_pais = row[COL_2024_TOTAL]
        elif nivel == "Municipio/TIOC" and row[6] == row[5]:
            clave = (norm(row[3]), norm(row[4]), norm(row[5]))
            if clave in munis:
                sys.exit(f"  ERROR: municipio duplicado en el tabulado: {clave}")
            munis[clave] = row[COL_2024_TOTAL]
    wb.close()
    if total_pais is None:
        sys.exit("  ERROR: no se encontro la fila Pais/Bolivia en el cuadro 19")
    if len(munis) != 343:
        sys.exit(f"  ERROR: se esperaban 343 municipios y hay {len(munis)}")
    if any(v is None for v in munis.values()):
        sys.exit("  ERROR: hay municipios sin valor de hogares (fila total vacia)")
    suma = sum(munis.values())
    if suma != total_pais:
        sys.exit(f"  ERROR: suma municipal {suma} != total Bolivia {total_pais}")
    print(f"  [tabulado] 343 municipios, suma {suma} == total Bolivia {total_pais}: OK")
    return munis, total_pais


def cargar_tmp_unidades(conn, unidades):
    """Temp table (codigo_ine, hogares) de las fichas con su validacion en BD."""
    import io

    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_hog_unidad (codigo_ine text, hogares integer) "
                    "ON COMMIT DROP")
        buf = io.StringIO()
        for codigo, hogares in unidades:
            buf.write(f"{codigo}\t{hogares}\n")
        buf.seek(0)
        cur.copy_expert("COPY tmp_hog_unidad (codigo_ine, hogares) FROM STDIN", buf)
        cur.execute("""
            WITH u AS (
                SELECT codigo_ine, personas, viviendas FROM shared.manzanos
                UNION ALL
                SELECT codigo_ine, personas, viviendas FROM shared.comunidades
            )
            SELECT count(*) AS fichas,
                   count(*) FILTER (WHERE u.codigo_ine IS NOT NULL) AS en_bd,
                   count(*) FILTER (WHERE u.codigo_ine IS NULL) AS sin_bd,
                   count(*) FILTER (WHERE u.codigo_ine IS NOT NULL
                                     AND h.hogares > u.viviendas) AS excede_viv,
                   COALESCE(sum(u.personas) FILTER (WHERE u.codigo_ine IS NOT NULL
                     AND h.hogares <= u.viviendas), 0) AS pob_cubierta
            FROM tmp_hog_unidad h
            LEFT JOIN u ON u.codigo_ine = h.codigo_ine
        """)
        return cur.fetchone()


def fase_A(conn, unidades, importar):
    print("── Fase A: hogares por unidad (manzanos/comunidades) ──")
    fichas, en_bd, sin_bd, excede, pob_cubierta = cargar_tmp_unidades(conn, unidades)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), COALESCE(sum(personas), 0) "
                    "FROM shared.manzanos UNION ALL "
                    "SELECT count(*), COALESCE(sum(personas), 0) "
                    "FROM shared.comunidades")
        (m_n, m_pob), (c_n, c_pob) = cur.fetchall()
    unidades_bd = m_n + c_n
    pob_bd = m_pob + c_pob
    print(f"  fichas: {fichas} | en BD: {en_bd} | sin unidad en BD: {sin_bd}")
    print(f"  con hogares > viviendas (se omite): {excede}")
    if sin_bd:
        print("  AVISO: hay fichas cuyo codigo_ine no existe en la BD")
    if not importar:
        pct = (100.0 * pob_cubierta / pob_bd) if pob_bd else 0.0
        print(f"  SIMULACION: se actualizarian {en_bd - excede} unidades "
              f"(cobertura poblacional con hogares: {pct:.1f}%)")
        return
    with conn.cursor() as cur:
        for tabla in ("manzanos", "comunidades"):
            cur.execute(f"""
                UPDATE shared.{tabla} t
                SET hogares = h.hogares
                FROM tmp_hog_unidad h
                WHERE h.codigo_ine = t.codigo_ine
                  AND h.hogares >= 0
                  AND h.hogares <= t.viviendas
            """)
            print(f"  UPDATE shared.{tabla}: {cur.rowcount} filas")
    conn.commit()
    print("  COMMIT fase A")


def fase_B(conn, munis, importar):
    print("── Fase B: hogares exactos por municipio (tabulado INE) ──")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.id, d.nombre, p.nombre, m.nombre
            FROM shared.municipio m
            JOIN shared.provincia p ON p.id = m.id_provincia
            JOIN shared.departamento d ON d.id = m.id_departamento
        """)
        filas = cur.fetchall()
    mapa = {(norm(d), norm(p), norm(m)): mid for mid, d, p, m in filas}
    if len(mapa) != len(filas):
        sys.exit("  ERROR: nombres de municipio duplicados en la BD")
    pareados = {clave: mapa[clave] for clave in munis if clave in mapa}
    faltantes = [clave for clave in munis if clave not in mapa]
    if faltantes or len(pareados) != 343:
        for f in faltantes[:10]:
            print(f"  sin mapear: {f}")
        sys.exit(f"  ERROR: mapeados {len(pareados)}/343 municipios")
    print(f"  mapeados: {len(pareados)}/343 (nombres INE == BD)")
    if not importar:
        print(f"  SIMULACION: se cargarian 343 filas "
              f"(SUM = {sum(munis.values())}) en shared.censo2024_hogares_municipio")
        return
    with conn.cursor() as cur:
        valores = [(pareados[k], int(munis[k])) for k in munis]
        from psycopg2.extras import execute_values
        execute_values(cur, """
            INSERT INTO shared.censo2024_hogares_municipio (id_municipio, hogares)
            VALUES %s
            ON CONFLICT (id_municipio) DO UPDATE
                SET hogares = EXCLUDED.hogares,
                    actualizado_en = now()
        """, valores, page_size=500)
        print(f"  UPSERT: {cur.rowcount} filas")
    conn.commit()
    print("  COMMIT fase B")


def cruce(conn, total_pais):
    print("── Cruce: unidades (fichas) vs tabulado INE (municipio) ──")
    with conn.cursor() as cur:
        cur.execute("""
            WITH u AS (
                SELECT id_municipio, SUM(hogares) hog
                FROM shared.manzanos WHERE hogares IS NOT NULL
                GROUP BY id_municipio
                UNION ALL
                SELECT id_municipio, SUM(hogares) hog
                FROM shared.comunidades WHERE hogares IS NOT NULL
                GROUP BY id_municipio
            ), s AS (
                SELECT id_municipio, SUM(hog) u_hog FROM u GROUP BY id_municipio
            )
            SELECT
                (SELECT COALESCE(sum(hogares), 0) FROM shared.manzanos)
              + (SELECT COALESCE(sum(hogares), 0) FROM shared.comunidades),
                (SELECT count(*) FROM shared.manzanos WHERE hogares IS NOT NULL)
              + (SELECT count(*) FROM shared.comunidades WHERE hogares IS NOT NULL),
                (SELECT COALESCE(sum(hogares), 0)
                   FROM shared.censo2024_hogares_municipio),
                (SELECT count(*) FROM shared.censo2024_hogares_municipio),
                count(*) FILTER (WHERE s.u_hog > h.hogares)
            FROM shared.censo2024_hogares_municipio h
            LEFT JOIN s ON s.id_municipio = h.id_municipio
        """)
        unidades_hog, unidades_n, ine_hog, ine_n, excesos = cur.fetchone()
        cur.execute("SELECT COALESCE(sum(personas), 0) FROM shared.manzanos "
                    "WHERE hogares IS NOT NULL UNION ALL "
                    "SELECT COALESCE(sum(personas), 0) FROM shared.comunidades "
                    "WHERE hogares IS NOT NULL")
        pob = sum(r[0] for r in cur.fetchall())
    cobertura = 100.0 * unidades_hog / ine_hog if ine_hog else 0.0
    print(f"  unidades con hogares: {unidades_n} (SUM unidades = {unidades_hog})")
    print(f"  municipios cargados:  {ine_n} (SUM INE = {ine_hog}, "
          f"Bolivia = {total_pais})")
    if ine_n == 0:
        print("  cruce pendiente: la tabla de hogares INE esta vacia "
              "(corre --importar)")
        return
    if unidades_n == 0:
        print("  cruce pendiente: ninguna unidad tiene hogares aun "
              "(corre --importar)")
        return
    print(f"  cobertura de hogares: {cobertura:.1f}% del total INE")
    if ine_hog != total_pais:
        print(f"  AVISO: SUM hogares_ine ({ine_hog}) != total Bolivia ({total_pais})")
    if excesos:
        print(f"  AVISO: {excesos} municipios con SUM(unidades) > hogares_ine")
    else:
        print("  cruce unidad <= INE en los 343 municipios: OK")
    if unidades_hog > 0:
        print(f"  personas por hogar (nacional, ceil) = "
              f"{-(-pob // unidades_hog):.0f} "
              f"(poblacion de referencia {pob}; ratio real "
              f"{pob / unidades_hog:.2f})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--simular", action="store_true", default=True,
                       help="Solo validar y reportar (default)")
    grupo.add_argument("--importar", action="store_true",
                       help="Escribir en la base de datos")
    args = parser.parse_args()
    importar = bool(args.importar)

    print("Resolviendo fuentes (cambios/ -> fuentes/ -> descarga)...")
    path_ficha = resolver_fuente(ARCH_FICHA, URL_FICHA)
    path_tabulado = resolver_fuente(ARCH_TABULADO, URL_TABULADO)
    print(f"  sha256 {ARCH_FICHA}: {sha256(path_ficha)}")
    print(f"  sha256 {ARCH_TABULADO}: {sha256(path_tabulado)}")

    unidades = leer_fichas(path_ficha)
    munis, total_pais = leer_tabulado(path_tabulado)

    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM shared.manzanos")
            if cur.fetchone()[0] == 0:
                sys.exit("  ERROR: shared.manzanos vacia (corre primero "
                         "cargar_censo2024_shared.py)")
            cur.execute("SELECT to_regclass('shared.censo2024_hogares_municipio')")
            if cur.fetchone()[0] is None:
                sys.exit("  ERROR: falta la migracion v2.17.0 "
                         "(shared.censo2024_hogares_municipio)")
        print(f"Modo: {'IMPORTAR' if importar else 'SIMULAR'}")
        fase_A(conn, unidades, importar)
        fase_B(conn, munis, importar)
        cruce(conn, total_pais)
        if not importar:
            conn.rollback()
            print("\nSIMULACION OK (no se escribio nada). Usa --importar para cargar.")
        else:
            print("\nCarga de hogares completada y confirmada (COMMIT).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
