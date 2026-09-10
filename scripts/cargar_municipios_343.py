#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vacia y recarga la jerarquia geografica compartida (shared) a partir del
shapefile MUNICIPIOS_343 (343 municipios de Bolivia).

Fuente unica de datos: MUNICIPIOS_343.shp
  - Atributos (dbf, UTF-8): codigo_ine, idep, nombre_dep, iprov, nombre_pro,
    imun, nombre_mun, capital, superficie
  - Geometria: MultiPolygon, WGS84 (EPSG:4326) -- igual al SRID de la BD.

Solo se usan las columnas ya habilitadas en la base de datos:
  shared.departamento (id, codigo_ine, nombre)
  shared.provincia    (id, codigo_ine, id_departamento, nombre)
  shared.municipio    (id, codigo_ine, id_departamento, id_provincia, nombre, geom)

Esquema de ids (derivado de la BD actual):
  departamento.id = int(idep)
  provincia.id    = int(idep + iprov)
  municipio.id    = int(codigo_ine)

Las tablas dependientes (usuarios, edan_localidades, rea.reporte_evento,
repositorio.documentos) se PRESERVAN: se vacian solo los catalogos
desactivando temporalmente las restricciones de claves ajenas con
session_replication_role = replica.

Uso:
  python3 cargar_municipios_343.py [ruta_shapefile_o_zip]
"""
import io
import os
import sys
import zipfile

ZIP_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "MUNICIPIOS_343.zip")
SHP_IN_ZIP = "MUNICIPIOS_343/MUNICIPIOS_343.shp"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
)


def load_shapefile(source):
    """Devuelve un Reader de pyshp desde .shp, .zip o dir."""
    import shapefile

    if source is None:
        source = ZIP_DEFAULT

    if os.path.isdir(source):
        for f in os.listdir(source):
            if f.lower().endswith(".shp"):
                return shapefile.Reader(os.path.join(source, f))
        raise FileNotFoundError("No se encontro .shp en el directorio %s" % source)

    if source.lower().endswith(".zip"):
        with zipfile.ZipFile(source) as z:
            names = z.namelist()
            shp_name = next((n for n in names if n.lower().endswith(".shp")),
                            None)
            if shp_name is None:
                raise ValueError("El ZIP no contiene un .shp")

            data = {n: z.read(n) for n in names}
            shp = data[shp_name]
            base = os.path.splitext(shp_name)[0]
            shx = data.get(base + ".shx")
            dbf = data.get(base + ".dbf")
            prj = data.get(base + ".prj")
            cpg = data.get(base + ".cpg")
            if shx is None or dbf is None:
                raise ValueError("El ZIP no contiene .shx/.dbf junto al .shp")
            encoding = None
            if cpg is not None:
                raw = data.get(cpg) or data.get(b"UTF-8") or data.get("UTF-8")
                if isinstance(raw, (bytes, bytearray)):
                    encoding = bytes(raw).decode("utf-8").strip() or None
                elif isinstance(raw, str):
                    encoding = raw.strip() or None
            return shapefile.Reader(
                shp=io.BytesIO(shp),
                shx=io.BytesIO(shx),
                dbf=io.BytesIO(dbf),
                prj=io.BytesIO(prj) if prj is not None else None,
                encoding=encoding,
            )

    if source.lower().endswith(".shp"):
        return shapefile.Reader(source)

    raise ValueError("Formato no soportado: %s" % source)


def ring_is_ccw(ring):
    """Sentido del anillo por el area con signo (formula de shoelace)."""
    a = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a > 0


def point_in_ring(pt, ring):
    """Ray casting: True si pt esta dentro del anillo."""
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def ring_in_ring(inner, outer):
    """True si un punto representativo de inner esta dentro de outer."""
    if not inner:
        return False
    return point_in_ring(inner[0], outer)


def rings_to_multipolygon_wkt(rings):
    """
    Agrupa los anillos de un shape MultiPolygon en (poligono exterior, huecos)
    usando la contencion geometrica, y devuelve el WKT MULTIPOLYGON.
    Se fuerza orientacion CW para los exteriores y CCW para los huecos,
    requerida por PostGIS (ST_IsValid).
    """
    # Normalizar a lista de listas de tuplas
    rings = [[(float(p[0]), float(p[1])) for p in r] for r in rings]

    if not rings:
        return None

    # Indices de los anillos que son exteriores (no contenidos en ningun otro)
    n = len(rings)
    is_outer = [True] * n
    for i in range(n):
        for j in range(n):
            if i != j and ring_in_ring(rings[i], rings[j]):
                is_outer[i] = False
                break

    # Ordenar exteriores por area (mayor primero) para estabilidad
    outer_idx = [i for i in range(n) if is_outer[i]]
    outer_idx.sort(key=lambda i: -abs(ring_signed_area(rings[i])))

    polygons = []
    for oi in outer_idx:
        outer = normalize_ring(rings[oi], want_cw=True)
        holes = []
        for k in range(n):
            if not is_outer[k] and ring_in_ring(rings[k], rings[oi]):
                # el hueco pertenece al exterior mas pequeno que lo contiene
                containers = [
                    j for j in outer_idx
                    if j != oi and ring_in_ring(rings[k], rings[j])
                ]
                if not containers:
                    holes.append(normalize_ring(rings[k], want_cw=False))
                else:
                    smallest = min(containers,
                                   key=lambda j: abs(ring_signed_area(rings[j])))
                    if smallest == oi:
                        holes.append(normalize_ring(rings[k], want_cw=False))
        poly = "( " + outer
        for h in holes:
            poly += ", " + h
        poly += " )"
        polygons.append(poly)

    if len(polygons) == 1:
        return "POLYGON" + polygons[0]
    return "MULTIPOLYGON (" + ", ".join(polygons) + ")"


def ring_signed_area(ring):
    a = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def normalize_ring(ring, want_cw=True):
    """Devuelve WKT de anillo con la orientacion deseada."""
    pts = ring
    if ring_is_ccw(pts) == want_cw:
        pts = list(reversed(pts))
    coords = ", ".join("%.6f %.6f" % (x, y) for x, y in pts)
    return "(" + coords + ")"


def iter_rows(sf):
    """Genera dict por fila con atributos y geometria WKT."""
    fields = [f[0] for f in sf.fields[1:]]
    for i in range(len(sf)):
        record = dict(zip(fields, sf.record(i)))
        shape = sf.shape(i)
        rings = []
        for p in range(len(shape.parts)):
            end = shape.parts[p + 1] if p + 1 < len(shape.parts) else len(shape.points)
            rings.append(shape.points[shape.parts[p]:end])
        wkt = rings_to_multipolygon_wkt(rings)
        yield record, wkt


def run(database_url, source):
    import psycopg2

    sf = load_shapefile(source)
    num_rows = len(sf)
    print("Shapefile cargado: %d registros" % num_rows)

    # 1) Acumular datos deduplicados
    departamentos = {}
    provincias = {}
    municipios = []

    rows = list(iter_rows(sf))
    for rec, wkt in rows:
        idep = rec["idep"].strip()
        iprov = rec["iprov"].strip()
        codice = rec["codigo_ine"].strip()
        departamentos[idep] = rec["nombre_dep"].strip()
        provincias.setdefault((idep, iprov), rec["nombre_pro"].strip())
        municipios.append({
            "id": int(codice),
            "codigo_ine": codice,
            "id_departamento": int(idep),
            "id_provincia": int(idep + iprov),
            "nombre": rec["nombre_mun"].strip(),
            "wkt": wkt,
        })

    dep_items = sorted(departamentos.items())
    prov_items = sorted(provincias.items())

    print("  departamentos : %d" % len(dep_items))
    print("  provincias    : %d" % len(prov_items))
    print("  municipios    : %d" % len(municipios))

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 2) Vaciar catalogos preservando tablas dependientes.
        #    Se usa DELETE (no TRUNCATE) porque las tablas dependientes
        #    referencian a estos catalogos y TRUNCATE no respeta
        #    session_replication_role. Con las FKs desactivadas via
        #    session_replication_role=replica, los registros de usuarios,
        #    edan_localidades, rea.reporte_evento, etc. se preservan intactos.
        cur.execute("SET session_replication_role = replica")
        cur.execute("DELETE FROM shared.municipio")
        cur.execute("DELETE FROM shared.provincia")
        cur.execute("DELETE FROM shared.departamento")
        cur.execute("SET session_replication_role = DEFAULT")
        print("Catalogos vaciados (FKs desactivadas temporalmente).")

        # 3) Departamentos
        for idep, nombre in dep_items:
            cur.execute(
                "INSERT INTO shared.departamento (id, codigo_ine, nombre) VALUES (%s, %s, %s)",
                (int(idep), idep.zfill(2), nombre),
            )
        print("  + %d departamentos" % len(dep_items))

        # 4) Provincias
        for (idep, iprov), nombre in prov_items:
            cur.execute(
                "INSERT INTO shared.provincia (id, codigo_ine, id_departamento, nombre)"
                " VALUES (%s, %s, %s, %s)",
                (int(idep + iprov), (idep + iprov), int(idep), nombre),
            )
        print("  + %d provincias" % len(prov_items))

        # 5) Municipios (con geometria)
        for m in municipios:
            if m["wkt"] is None:
                cur.execute(
                    "INSERT INTO shared.municipio (id, codigo_ine, id_departamento,"
                    " id_provincia, nombre) VALUES (%s,%s,%s,%s,%s)",
                    (m["id"], m["codigo_ine"], m["id_departamento"],
                     m["id_provincia"], m["nombre"]),
                )
            else:
                cur.execute(
                    "INSERT INTO shared.municipio (id, codigo_ine, id_departamento,"
                    " id_provincia, nombre, geom) VALUES (%s,%s,%s,%s,%s,"
                    " ST_Multi(ST_GeomFromText(%s, 4326)))",
                    (m["id"], m["codigo_ine"], m["id_departamento"],
                     m["id_provincia"], m["nombre"], m["wkt"]),
                )
        print("  + %d municipios" % len(municipios))

        conn.commit()
        print("COMMIT realizado.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


_REMAPEO_MUNICIPIO = {
    # La base antigua tenia Santa Cruz mal codificada. Estos ids de municipio
    # (que ya no existen) corresponden, por nombre, al municipio oficial del
    # shapefile indicado. Se respeta el codigo INE del shapefile.
    71203: 70803,  # Moro Moro   -> Moromoro (Vallegrande)
    71303: 71503,  # El Puente   -> El Puente (Guarayos)
    71702: 70702,  # Charagua    -> Charagua (Autonomia Guarani Charagua)
    71706: 70706,  # Camiri      -> Camiri
    71707: 70707,  # Boyuibe     -> Boyuibe
}

# Provincias antiguas (mal codificadas en Santa Cruz) -> nueva provincia oficial.
# Usado para filas que solo tienen id_provincia (sin municipio) o cuyo municipio
# no pudo resolverse:
#   717 Cordillera -> 707 Cordillera
#   712 Vallegrande(mal) -> 708 Vallegrande
#   713 Guarayos(mal, municipios 0715xx) -> 715 Guarayos
_REMAPEO_PROVINCIA = {
    717: 707,
    712: 708,
    713: 715,
}


def _normalizar(s):
    import unicodedata
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _mapa_nuevo(database_url):
    """id_municipio_nuevo -> (municipio, provincia, departamento) existentes."""
    import psycopg2

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.nombre, m.id_provincia, m.id_departamento
        FROM shared.municipio m
    """)
    mapa = {}
    for mid, nombre, prov, dep in cur.fetchall():
        mapa[mid] = (mid, prov, dep, nombre)
    cur.close()
    conn.close()
    return mapa


def reparar_referencias(database_url):
    """
    Actualiza las filas de las tablas dependientes (usuarios, edan_localidades,
    rea.reporte_evento, repositorio.documentos) que referencian municipios o
    provincias inexistentes, remapeandolas al municipio/provincia correcto
    segun el codigo INE oficial (REMAPEO_MUNICIPIO / REMAPEO_PROVINCIA).
    Actualiza tambien id_provincia e id_departamento a los del municipio nuevo.
    Cada tabla se procesa en una transaccion aislada (para que un error de
    esquema en una tabla no invalide el commit de las demas).
    """
    import psycopg2

    mapa = _mapa_nuevo(database_url)
    if not mapa:
        print("AVISO: no hay municipios cargados para reparar referencias.")
        return

    # (tabla, pk) - pk segun esquema real de cada tabla
    tablas = [
        ("usuarios.usuario", "id_usuario"),
        ("edan.edan_localidades", "id_edan_localidad"),
        ("rea.reporte_evento", "id_reporte"),
        ("repositorio.documentos", "id_documento"),
    ]

    total = 0
    for tabla, pk in tablas:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            # 1) remap por municipio inexistente
            try:
                cur.execute(
                    "SELECT %s, id_municipio, id_provincia, id_departamento"
                    " FROM %s WHERE id_municipio IS NOT NULL"
                    " AND id_municipio NOT IN (SELECT id FROM shared.municipio)"
                    % (pk, tabla)
                )
            except psycopg2.Error as e:
                print("  [skip] %s (sin col id_municipio): %s" % (tabla, e))
                conn.rollback()
                cur.close()
                conn.close()
                continue
            for pk_val, id_mun, id_prov, id_dep in cur.fetchall():
                if id_mun not in _REMAPEO_MUNICIPIO:
                    continue
                nuevo = _REMAPEO_MUNICIPIO[id_mun]
                if nuevo not in mapa:
                    continue
                nuevo_id, nuevo_prov, nuevo_dep, nuevo_nombre = mapa[nuevo]
                cur.execute(
                    "UPDATE %s SET id_municipio=%%s, id_provincia=%%s,"
                    " id_departamento=%%s WHERE %s=%%s" % (tabla, pk),
                    (nuevo_id, nuevo_prov, nuevo_dep, pk_val),
                )
                total += 1
                print("  [reparado] %s %s=%s: municipio %s -> %s (%s)"
                      % (tabla, pk, pk_val, id_mun, nuevo_id, nuevo_nombre))

            # 2) remap por provincia inexistente (filas sin municipio)
            try:
                cur.execute(
                    "SELECT %s, id_municipio, id_provincia, id_departamento"
                    " FROM %s WHERE id_provincia IS NOT NULL"
                    " AND id_provincia NOT IN (SELECT id FROM shared.provincia)"
                    % (pk, tabla)
                )
            except psycopg2.Error as e:
                print("  [skip] %s (sin col id_provincia): %s" % (tabla, e))
                conn.rollback()
                cur.close()
                conn.close()
                continue
            for pk_val, id_mun, id_prov, id_dep in cur.fetchall():
                if id_prov not in _REMAPEO_PROVINCIA:
                    continue
                nuevo_prov = _REMAPEO_PROVINCIA[id_prov]
                nuevo_dep = id_dep
                cur.execute(
                    "SELECT id_departamento FROM shared.provincia WHERE id=%s",
                    (nuevo_prov,),
                )
                r = cur.fetchone()
                if r:
                    nuevo_dep = r[0]
                cur.execute(
                    "UPDATE %s SET id_provincia=%%s, id_departamento=%%s"
                    " WHERE %s=%%s" % (tabla, pk),
                    (nuevo_prov, nuevo_dep, pk_val),
                )
                total += 1
                print("  [reparado-prov] %s %s=%s: provincia %s -> %s"
                      % (tabla, pk, pk_val, id_prov, nuevo_prov))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    print("Referencias reparadas (total): %d" % total)


def verify(database_url):
    """Control de calidad posterior: conteos e integridad."""
    import psycopg2

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    checks = [
        ("shared.departamento", 9),
        ("shared.provincia", 113),
        ("shared.municipio", 343),
    ]
    ok = True
    for table, esperado in checks:
        cur.execute("SELECT count(*) FROM %s" % table)
        got = cur.fetchone()[0]
        estado = "OK" if got == esperado else "!!"
        if got != esperado:
            ok = False
        print("[%s] %-24s esperado=%d  actual=%d" % (estado, table, esperado, got))

    # integridad: municipios sin provincia/departamento valido
    cur.execute("""
        SELECT count(*) FROM shared.municipio m
        LEFT JOIN shared.provincia p ON p.id = m.id_provincia
        LEFT JOIN shared.departamento d ON d.id = m.id_departamento
        WHERE p.id IS NULL OR d.id IS NULL
    """)
    huerfanos = cur.fetchone()[0]
    print("[%s] municipios huerfanos (sin dep/prov) = %d" %
          ("OK" if huerfanos == 0 else "!!", huerfanos))
    if huerfanos != 0:
        ok = False

    # provincias sin departamento valido
    cur.execute("""
        SELECT count(*) FROM shared.provincia p
        LEFT JOIN shared.departamento d ON d.id = p.id_departamento
        WHERE d.id IS NULL
    """)
    hp = cur.fetchone()[0]
    print("[%s] provincias huerfanas = %d" % ("OK" if hp == 0 else "!!", hp))
    if hp != 0:
        ok = False

    # geometrias invalidas
    cur.execute("""
        SELECT count(*) FROM shared.municipio
        WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)
    """)
    ninv = cur.fetchone()[0]
    print("[%s] municipios con geometria invalida = %d" %
          ("OK" if ninv == 0 else "!!", ninv))
    if ninv != 0:
        ok = False

    # municipios sin geometria
    cur.execute("SELECT count(*) FROM shared.municipio WHERE geom IS NULL")
    nsin = cur.fetchone()[0]
    print("[%s] municipios sin geometria = %d" %
          ("OK" if nsin == 0 else "!!", nsin))
    if nsin != 0:
        ok = False

    cur.close()
    conn.close()
    return ok


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else None
    run(DATABASE_URL, source)
    print("\nReparacion de referencias (tablas dependientes preservadas):")
    reparar_referencias(DATABASE_URL)
    print("\nVerificacion:")
    ok = verify(DATABASE_URL)
    print("\nRESULTADO: %s" % ("OK" if ok else "FALLO - revise los valores [!!]"))
    sys.exit(0 if ok else 1)
