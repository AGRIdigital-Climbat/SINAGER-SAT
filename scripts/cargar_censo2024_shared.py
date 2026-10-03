#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga el Censo 2024 (CPV-2024, INE) en las tablas `shared.manzanos` y
`shared.comunidades` del esquema geografico compartido.

Fuente de datos:
  - datos_censo2024/procesado/manzanos_censo2024.csv   (247.429 filas)
  - datos_censo2024/procesado/comunidades_censo2024.csv (21.175 filas)
  - datos_censo2024/geo/unidades_censo2024.gpkg          (geometrias,
    manzanos=MULTIPOLYGON, comunidades=POINT, EPSG:4326)

Reglas:
  - Una fila por unidad censal minima; `personas` = poblacion, `viviendas` =
    viviendas particulares (nomenclatura de la fuente INE).
  - Encabezados estandar (como en provincia/municipio): `codigo_ine` (clave
    censal INE) + `id_departamento` / `id_provincia` / `id_municipio`
    (enteros derivados de la jerarquia geografica por id_municipio).
  - `geom` se lee del GeoPackage sin GDAL: se parsea el cabecero
    GeoPackageBinary (magic 'GP', flags, srs_id, envelope) y se extrae el WKB
    estandar, que PostGIS ingiere via ST_GeomFromWKB(..., 4326).
  - Idempotente: usa INSERT ... ON CONFLICT (codigo_ine) DO UPDATE (re-carga
    segura). NO altera ninguna otra tabla del esquema.

Uso:
  python3 scripts/cargar_censo2024_shared.py [--simular|--importar]

  DATABASE_URL=postgresql://... python3 scripts/cargar_censo2024_shared.py ...  # BD alternativa
"""
import argparse
import io
import os
import sqlite3
import struct
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV_MANZANOS = os.path.join(BASE_DIR, "datos_censo2024", "procesado", "manzanos_censo2024.csv")
CSV_COMUNIDADES = os.path.join(BASE_DIR, "datos_censo2024", "procesado", "comunidades_censo2024.csv")
GPKG = os.path.join(BASE_DIR, "datos_censo2024", "geo", "unidades_censo2024.gpkg")

EXPECTED_HEADER = [
    "codigo", "nombre", "tipo_unidad", "area", "personas", "viviendas", "ficha",
    "idep", "iprov", "imun", "codigo_departamento", "codigo_provincia",
    "codigo_municipio", "nombre_dep", "nombre_prov", "nombre_mun", "lat", "lon",
    "area_oficial",
]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
)


def gpkg_wkb(blob: bytes) -> bytes:
    """Extrae el WKB estandar del formato de geometria GeoPackageBinary."""
    if len(blob) < 8 or blob[:2] != b"GP":
        raise ValueError("Blob GeoPackage invalido (sin magic GP)")
    flags = blob[3]
    env_ind = (flags >> 1) & 0x03          # 0=sin envelope, 1=2D, 2=3D, 3=4D
    extended = (flags >> 5) & 0x01          # 0=WKB estandar, 1=EWKB
    if extended:
        raise ValueError("GeoPackage con EWKB no soportado por este cargador")
    header_len = 8 + env_ind * 32           # 4 doubles por dimension
    return blob[header_len:]


def load_geometries(gpkg_path: str, layer: str):
    """Genera (codigo, wkb_hex) para todas las filas de una capa del GPKG."""
    con = sqlite3.connect(gpkg_path)
    try:
        cur = con.execute(f'SELECT codigo, geom FROM "{layer}"')
        for codigo, geom in cur:
            if geom is None:
                continue
            yield codigo, gpkg_wkb(bytes(geom)).hex()
    finally:
        con.close()


def csv_count_rows(path: str):
    n = -1
    with open(path, encoding="utf-8", newline="") as fh:
        for _ in fh:
            n += 1
    return n


def simulate():
    print("SIMULACION (no escribe):")
    for path, label in ((CSV_MANZANOS, "manzanos"), (CSV_COMUNIDADES, "comunidades")):
        rows = csv_count_rows(path)
        print(f"  {label}: {rows} filas | {path}")
    gpkg_layers = {}
    con = sqlite3.connect(GPKG)
    for layer in ("manzanos", "comunidades"):
        gpkg_layers[layer] = con.execute(f'SELECT Count(*) FROM "{layer}"').fetchone()[0]
    con.close()
    print(f"  geometrias GPKG: manzanos={gpkg_layers['manzanos']} "
          f"comunidades={gpkg_layers['comunidades']}")
    return all(os.path.isfile(p) for p in (CSV_MANZANOS, CSV_COMUNIDADES, GPKG))


COPY_COLS = ", ".join(EXPECTED_HEADER)


def copy_csv(conn, path: str, tmp_table: str):
    with open(path, encoding="utf-8", newline="") as fh:
        header = fh.readline().rstrip("\r\n").split(",")
        if [h.strip() for h in header] != EXPECTED_HEADER:
            sys.exit(f"Header inesperado en {path}: {header}")
        with conn.cursor() as cur:
            cur.copy_expert(
                f"COPY {tmp_table} ({COPY_COLS}) FROM STDIN WITH "
                "(FORMAT csv, HEADER false)",
                fh,
            )


def upsert_from_tmp(conn, tmp_table: str, target: str) -> None:
    """Inserta/actualiza target desde la tabla temporal uniendo la jerarquia
    geografica (id_municipio, id_provincia, id_departamento)."""
    sql = f"""
        INSERT INTO shared.{target} (
            codigo_ine, nombre, tipo_unidad, personas, viviendas,
            lat, lon, area_oficial, id_municipio, id_provincia, id_departamento
        )
        SELECT t.codigo AS codigo_ine,
               t.nombre, t.tipo_unidad, t.personas, t.viviendas,
               t.lat, t.lon, t.area_oficial,
               mu.id AS id_municipio, mu.id_provincia, mu.id_departamento
        FROM {tmp_table} t
        JOIN shared.municipio mu
          ON mu.codigo_ine = LPAD(t.codigo_municipio::text, 6, '0')
        ON CONFLICT (codigo_ine) DO UPDATE SET
            nombre        = EXCLUDED.nombre,
            tipo_unidad   = EXCLUDED.tipo_unidad,
            personas      = EXCLUDED.personas,
            viviendas     = EXCLUDED.viviendas,
            lat           = EXCLUDED.lat,
            lon           = EXCLUDED.lon,
            area_oficial  = EXCLUDED.area_oficial
    """
    with conn.cursor() as cur:
        cur.execute(sql)


def load_geometry(conn, tmp_geom: str, target: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE {tmp_geom} (codigo text, wkb_hex text) ON COMMIT DROP")
        buf = io.StringIO()
        for codigo, wkb_hex in load_geometries(GPKG, target):
            buf.write(f"{codigo}\t{wkb_hex}\n")
        buf.seek(0)
        cur.copy_expert(
            f"COPY {tmp_geom} (codigo, wkb_hex) FROM STDIN",
            buf,
        )
        cur.execute(f"""
            UPDATE shared.{target} m
            SET geom = ST_GeomFromWKB(decode(g.wkb_hex, 'hex'), 4326)
            FROM {tmp_geom} g
            WHERE g.codigo = m.codigo_ine
        """)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--simular", action="store_true", help="Solo validar y contar (no escribe)")
    modo.add_argument("--importar", action="store_true", help="Cargar de verdad (default)")
    args = parser.parse_args()

    if not all(os.path.isfile(p) for p in (CSV_MANZANOS, CSV_COMUNIDADES, GPKG)):
        sys.exit("Faltan archivos fuente en datos_censo2024/")

    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    if args.simular:
        simulate()
        conn.close()
        return

    print("Cargando Censo 2024 en shared.manzanos / shared.comunidades ...")
    with conn.cursor() as cur:
        cur.execute("SELECT postgis_version()")
        postgis = cur.fetchone()[0]
        print(f"  PostGIS: {postgis}")

    for target, csv_path, tmp_table, tmp_geom in (
        ("manzanos", CSV_MANZANOS, "tmp_manzanos", "tmp_geom_man"),
        ("comunidades", CSV_COMUNIDADES, "tmp_comunidades", "tmp_geom_com"),
    ):
        csv_rows = csv_count_rows(csv_path)
        print(f"  --- {target}: {csv_rows} filas CSV")
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TEMP TABLE {tmp_table} (
                    codigo text, nombre text, tipo_unidad text, area smallint,
                    personas integer, viviendas integer, ficha boolean,
                    idep smallint, iprov smallint, imun smallint,
                    codigo_departamento smallint, codigo_provincia integer,
                    codigo_municipio integer, nombre_dep text, nombre_prov text,
                    nombre_mun text, lat numeric(10,7), lon numeric(10,7),
                    area_oficial text
                ) ON COMMIT DROP
            """)
        copy_csv(conn, csv_path, tmp_table)
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {tmp_table}")
            loaded = cur.fetchone()[0]
            cur.execute(f"""
                SELECT count(*) FROM {tmp_table} t
                LEFT JOIN shared.municipio mu
                  ON mu.codigo_ine = LPAD(t.codigo_municipio::text, 6, '0')
                WHERE mu.id IS NULL
            """)
            unresolved = cur.fetchone()[0]
        print(f"  COPY: {loaded} filas, sin municipio: {unresolved}")
        if loaded != csv_rows or unresolved:
            conn.rollback()
            sys.exit(f"  ERROR en {target}: abortado sin escribir (loaded={loaded}, "
                     f"sin municipio={unresolved})")
        upsert_from_tmp(conn, tmp_table, target)
        load_geometry(conn, tmp_geom, target)
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*), count(geom), sum(personas), sum(viviendas) "
                        f"FROM shared.{target}")
            n, n_geom, pers, viv = cur.fetchone()
            cur.execute(f"""
                SELECT count(DISTINCT id_municipio) FROM shared.{target}
            """)
            n_mun = cur.fetchone()[0]
        print(f"  RESULTADO {target}: filas={n} con_geom={n_geom} personas={pers} "
              f"viviendas={viv} municipios={n_mun}")

    conn.commit()
    conn.close()
    print("Carga completada y confirmada (COMMIT).")


if __name__ == "__main__":
    main()