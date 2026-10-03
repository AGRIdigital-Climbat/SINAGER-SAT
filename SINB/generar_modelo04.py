#!/usr/bin/env python3
"""Extrae los DDL del modelo nuevo de propuesta/04-BASE-DE-DATOS.md.

- Solo DDL: CREATE TYPE/TABLE/INDEX/VIEW, ALTER TABLE ADD CONSTRAINT/COLUMN.
- Orden topologico por REFERENCES.
- Genera SINB/modelo_nuevo_propuesta04.sql (buscador: search_path=sinb).
- NO emite DROP, DELETE, RLS ni indexes trgm (requieren extension pg_trgm).
"""
import re
import sys
from collections import defaultdict

SRC = "/home/prosuco/SINAGERSAT/BaseData/propuesta/04-BASE-DE-DATOS.md"
DST = "/home/prosuco/SINAGERSAT/BaseData/SINB/modelo_nuevo_propuesta04.sql"

# Tablas cuyo DDL no aparece en el documento (verificadas por busqueda).
DDL_FALTANTE = {
    "caracteristica_comportamiento": """CREATE TABLE caracteristica_comportamiento (
    fk_id_comportamiento uuid NOT NULL REFERENCES comportamiento(id) ON DELETE CASCADE,
    fk_id_caracteristica  uuid NOT NULL REFERENCES caracteristica(id)  ON DELETE CASCADE,
    id_legacy             bigint,
    PRIMARY KEY (fk_id_comportamiento, fk_id_caracteristica)
);""",
    "indicador_natural_caracteristica": """CREATE TABLE indicador_natural_caracteristica (
    fk_id_indicador_natural uuid NOT NULL REFERENCES indicador_natural(id) ON DELETE CASCADE,
    fk_id_caracteristica     uuid NOT NULL REFERENCES caracteristica(id)    ON DELETE CASCADE,
    estado                   estado_registro NOT NULL DEFAULT 'ACTIVO',
    id_legacy                bigint,
    PRIMARY KEY (fk_id_indicador_natural, fk_id_caracteristica)
);""",
}



def sanear_particionada(tabla, stmt):
    """PK de tabla particionada debe incluir la columna de particion y hace
    falta una particion DEFAULT para poder insertar."""
    if "PARTITION BY" not in stmt.upper():
        return stmt, []
    col = re.search(r"PARTITION BY RANGE \((\w+)\)", stmt, re.I).group(1)
    mtbl = re.search(r"PRIMARY KEY \(([^)]*)\)", stmt, re.I)
    if mtbl:
        cols = list(dict.fromkeys([c.strip() for c in mtbl.group(1).split(",")] + ["id", col]))
        stmt = (stmt[:mtbl.start()] + "PRIMARY KEY (" + ", ".join(cols) + ")"
                + stmt[mtbl.end():])
    else:
        m2 = re.search(r"\bid\s+([^,\n]+?)\s+PRIMARY KEY", stmt, re.I)
        tipo = m2.group(1).strip()
        stmt = stmt[:m2.start()] + "id " + tipo + stmt[m2.end():]
        m3 = re.search(r"\n(\s*)\)\s*PARTITION BY", stmt, re.I)
        pk = ",\n" + m3.group(1) + "PRIMARY KEY (id, " + col + ")"
        stmt = stmt[:m3.start()] + pk + stmt[m3.start():]
    extra = ["CREATE TABLE IF NOT EXISTS %s_default PARTITION OF %s DEFAULT;"
             % (tabla, tabla)]
    return stmt, extra


def extraer_unique_con_expresion(tabla, stmt):
    # "CONSTRAINT uq_x UNIQUE (col, lower(col))" no es valido: va como CREATE UNIQUE INDEX
    idx = []
    def repl(m):
        nombre, cols = m.group(1), m.group(2)
        idx.append(f"CREATE UNIQUE INDEX IF NOT EXISTS {nombre} ON {tabla} ({cols})")
        return m.group(0).split(",")[0] + m.group(0)[m.group(0).index(","):]
    m = re.search(r",\s*\n\s*CONSTRAINT (\w+) UNIQUE \(([^)]*\([^)]*\)[^)]*)\)", stmt)
    if not m:
        return stmt, idx
    stmt = stmt[:m.start()] + stmt[m.end():]
    idx.append(f"CREATE UNIQUE INDEX IF NOT EXISTS {m.group(1)} ON {tabla} ({m.group(2)})")
    return stmt, idx


def sanear_pk(stmt):
    # doc: "id uuid PRIMARY KEY" + linea suelta ",\n    PRIMARY KEY (id)" -> PK dos veces
    if re.search(r"\bid\s+\w+\s+PRIMARY KEY", stmt, re.I) and re.search(
            r",\s*\n\s*PRIMARY KEY \(id\)", stmt, re.I):
        stmt = re.sub(r",\s*\n\s*PRIMARY KEY \(id\)", "", stmt, count=1, flags=re.I)
    # doc: "id uuid PRIMARY KEY" + "PRIMARY KEY (fk_..., fk_...)" -> una sola PK;
    # se conserva la compuesta como PK y id pasa a UNIQUE
    if re.search(r"\bid\s+\w+\s+PRIMARY KEY", stmt, re.I):
        comp = re.search(r",\s*\n(\s*)PRIMARY KEY \(([^)]*)\)", stmt, re.I)
        if comp and comp.group(2).strip().lower() != "id":
            indent, cols = comp.group(1), comp.group(2)
            stmt = (stmt[:comp.start()] +
                    ",\n" + indent + "CONSTRAINT uq_" + "id_" + cols.split(",")[0].strip() +
                    " UNIQUE (" + cols + ")" + stmt[comp.end():])
            stmt = re.sub(r"\bid\s+(\w+)\s+PRIMARY KEY",
                          lambda m: m.group(1) and "id " + m.group(1) + " NOT NULL",
                          stmt, count=1, flags=re.I)
    return stmt


def extraer_bloques_sql(md: str):
    return re.findall(r"```sql\n(.*?)```", md, re.S)


def partir_sentencias(bloque: str):
    """Divide un bloque en sentencias terminadas en ';' (sin cuerpos $$)."""
    out = []
    buf = []
    for linea in bloque.split("\n"):
        buf.append(linea)
        if linea.rstrip().endswith(";"):
            out.append("\n".join(buf).strip())
            buf = []
    resto = "\n".join(buf).strip()
    if resto:
        out.append(resto)
    return [s for s in out if s]


def normalizar(stmt: str) -> str:
    # quitar comentarios de linea completos al inicio
    lineas = [l for l in stmt.split("\n") if l.strip() and not l.strip().startswith("--")]
    return "\n".join(lineas).strip()


def clasificar(stmt: str):
    """Devuelve (tipo, tabla_destino) o None si se descarta."""
    u = " ".join(stmt.split())
    head = u.upper()
    if head.startswith("CREATE TYPE"):
        return ("type", None)
    if head.startswith("CREATE TABLE"):
        m = re.match(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", u, re.I)
        return ("table", m.group(1))
    if head.startswith("CREATE UNIQUE INDEX") or head.startswith("CREATE INDEX"):
        if "gin_trgm_ops" in u or head.startswith("CREATE TRGM"):
            return ("index_trgm", None)
        m = re.match(r"CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?(\w+) ON (\w+)", u, re.I)
        return ("index", m.group(2) if m else None)
    if head.startswith("CREATE VIEW") or head.startswith("CREATE OR REPLACE VIEW"):
        m = re.match(r"CREATE (?:OR REPLACE )?VIEW (\w+)", u, re.I)
        return ("view", m.group(1) if m else None)
    if head.startswith("ALTER TABLE"):
        if "ENABLE ROW LEVEL SECURITY" in u or "FORCE ROW LEVEL SECURITY" in u:
            return ("rls", None)
        if re.search(r"ADD (CONSTRAINT|COLUMN)", u, re.I):
            m = re.match(r"ALTER TABLE (?:ONLY )?(\w+)", u, re.I)
            return ("alter", m.group(1) if m else None)
        return ("alter_otro", None)
    return ("otro", None)


def referencias(stmt: str):
    return set(re.findall(r"REFERENCES (\w+)", stmt, re.I))


def main():
    md = open(SRC, encoding="utf-8").read()
    sentencias = []
    for b in extraer_bloques_sql(md):
        for s in partir_sentencias(b):
            s = normalizar(s)
            if not s:
                continue
            sentencias.append(s)

    tipos, tablas, alter_cols, alter_ucs, indexs, vistas = [], [], [], [], [], []
    descartadas = defaultdict(list)
    vistas_stmts, trgm = [], []

    vistas_orden = None  # al final

    for s in sentencias:
        t, dest = clasificar(s)
        if t == "type":
            tipos.append(s)
        elif t == "table":
            tablas.append((dest, s))
        elif t == "alter":
            if re.search(r"ADD COLUMN", s, re.I):
                alter_cols.append((dest, s))
            else:
                alter_ucs.append((dest, s))
        elif t == "index":
            indexs.append((dest, s))
        elif t == "index_trgm":
            trgm.append(s)
        elif t == "view":
            vistas_stmts.append(s)
        else:
            descartadas[t].append(s[:70])

    # tablas faltantes en el doc
    existentes = {n for n, _ in tablas}
    for nombre, ddl in DDL_FALTANTE.items():
        if nombre not in existentes:
            tablas.append((nombre, ddl))

    # ---- orden topologico de CREATE TABLE ----
    nombres_tablas = {n for n, _ in tablas}
    stmt_de = {n: s for n, s in tablas}
    deps = defaultdict(set)
    for n, s in tablas:
        for r in referencias(s):
            if r in nombres_tablas and r != n:
                deps[n].add(r)
    # ADD COLUMN con REFERENCES cuentan como dependencia del destino
    for dest, s in alter_cols:
        for r in referencias(s):
            if r in nombres_tablas and r != dest:
                deps[dest].add(r)

    orden, visitados = [], set()

    def visit(n, pila):
        if n in visitados:
            return
        if n in pila:
            sys.stderr.write(f"CICLO: {n}\n")
            return
        for d in sorted(deps.get(n, ())):
            visit(d, pila | {n})
        visitados.add(n)
        orden.append(n)

    for n, _ in tablas:
        visit(n, set())

    # alteraciones ADD COLUMN / ADD CONSTRAINT van tras su tabla
    alter_cols_ord = sorted(alter_cols, key=lambda x: orden.index(x[0]) if x[0] in orden else 999)
    alter_ucs_ord = sorted(alter_ucs, key=lambda x: orden.index(x[0]) if x[0] in orden else 999)
    # ADD CONSTRAINT UNIQUE en caracteristica/comportamiento_significado debe
    # ir antes de observacion_registro (FK compuesta) -> ya va despues de tablas
    indexs_ord = sorted(indexs, key=lambda x: (orden.index(x[0]) if x[0] in orden else 999))

    out = []
    out.append("-- Generado por SINB/generar_modelo04.py desde propuesta/04-BASE-DE-DATOS.md")
    out.append("-- Modelo nuevo del SINB en el esquema sinb. Solo creacion (sin DROP ni DELETE).")
    out.append("-- Previamente:\n--   SET search_path TO sinb, public;\n--   CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA sinb;\n--   CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA sinb;")
    out.append("--")
    out.append("-- Desviaciones aplicadas sobre el DDL del documento (errores del doc):")
    out.append("--   1. categoria_comportamiento: PK declarada dos veces (columna + tabla) -> se deja la de columna.")
    out.append("--   2. escenario_estacional: PK de columna 'id' + PK compuesta -> 'id' pasa a NOT NULL y la compuesta queda UNIQUE.")
    out.append("--   3. sinonimo_indicador: UNIQUE con lower(texto) no es valido -> CREATE UNIQUE INDEX.")
    out.append("--   4. auditoria: PK no incluia la columna de particion -> PRIMARY KEY (id, occurred_at) + particion DEFAULT.")
    out.append("--   5. caracteristica_comportamiento e indicador_natural_caracteristica: el doc no trae DDL -> se autoro (catalogo 1A + FK de observacion_registro).")
    out.append("--   6. gist_observacion_comunidad: observacion no tiene columna geom (el doc lo resuelve con vista materializada) -> omitido.")
    out.append("--   7. v_registro_territorial: gi.fk_id_indicador/fk_id_grupo -> id_indicador/id_grupo; g.nombre -> g.grupo.")
    out.append("--   8. Trgm: 4 indices requieren pg_trgm; se crean los 3 extraibles, el del doc 'CREATE TRGM.idx_comportamiento_texto' esta malformado y se omite.")
    out.append("--   9. RLS/policies (doc linea ~2027) y scripts SET LOCAL: fuera de alcance, fase seguridad/API.")
    out.append("--")
    out.append("-- Re-ejecutable: no usa DROP/DELETE; tipos, tablas e indices son idempotentes.")
    out.append("")
    for t in dict.fromkeys(tipos):
        cuerpo = t.strip().rstrip(";")
        out.append("DO $$ BEGIN")
        out.append(cuerpo + ";")
        out.append("EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
        out.append("")
    # Los ADD COLUMN / ADD CONSTRAINT de cada tabla se emiten justo despues
    # de su CREATE TABLE: las FK compuestas de observacion_registro exigen que
    # la unicidad exista antes de crear la tabla que la referencia.
    out.append("-- ============ TABLAS (+ sus ADD COLUMN / ADD CONSTRAINT) ============")
    out.append("")
    alters_por_tabla = defaultdict(list)
    for _, s in alter_cols_ord + alter_ucs_ord:
        m = re.match(r"ALTER TABLE (?:ONLY )?(\w+)", s, re.I)
        alters_por_tabla[m.group(1)].append(s)
    for n in orden:
        stmt = sanear_pk(stmt_de[n])
        stmt, extra_idx = extraer_unique_con_expresion(n, stmt)
        stmt, extra_part = sanear_particionada(n, stmt)
        extra_idx = extra_idx + extra_part
        stmt = re.sub(r"CREATE TABLE (?!IF NOT EXISTS)", "CREATE TABLE IF NOT EXISTS ",
                      stmt, count=1, flags=re.I)
        out.append(stmt)
        out.append("")
        for e in extra_idx:
            out.append(e.rstrip(";") + ";")
            out.append("")
        for a in alters_por_tabla.get(n, []):
            if re.search(r"ADD COLUMN", a, re.I) and "IF NOT EXISTS" not in a:
                a = re.sub(r"ADD COLUMN", "ADD COLUMN IF NOT EXISTS", a, flags=re.I)
            elif re.search(r"ADD CONSTRAINT", a, re.I):
                a = ("DO $$ BEGIN\n" + a.rstrip(";") + ";\n"
                     "EXCEPTION WHEN OTHERS THEN\n"
                     "  IF SQLSTATE NOT IN ('42710','42P07') THEN RAISE; END IF;\n"
                     "END $$;")
            out.append(a)
            out.append("")
    if indexs_ord:
        out.append("-- ============ INDICES ============")
        out.append("")
        for _, s in indexs_ord:
            # el doc admite que este indice no es viable (usa observacion.geom
            # que no existe) y lo resuelve con vista materializada -> se omite
            if "gist_observacion_comunidad" in s:
                continue
            s = re.sub(r"CREATE (UNIQUE )?INDEX (?!IF NOT EXISTS)",
                       r"CREATE \1INDEX IF NOT EXISTS ", s, flags=re.I)
            out.append(s)
            out.append("")
    if vistas_stmts:
        out.append("-- ============ VISTAS ============")
        out.append("")
        for s in vistas_stmts:
            s = re.sub(r"CREATE VIEW", "CREATE OR REPLACE VIEW", s, count=1, flags=re.I)
            # el doc usa fk_id_indicador en la vista pero la tabla real (y el
            # espejo de t_) se llama id_indicador
            s = re.sub(r"\b(gi)\.fk_id_(\w+)\b", r"\1.id_\2", s)
            # la tabla grupo no tiene columna "nombre": se llama "grupo"
            s = re.sub(r"\bg\.nombre\b", "g.grupo", s)
            out.append(s)
            out.append("")

    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print(f"tipos: {len(dict.fromkeys(tipos))}")
    print(f"tablas: {len(orden)} (incluye {len(DDL_FALTANTE)} DDL autorados por ausencia en el doc)")
    print(f"add column: {len(alter_cols_ord)} | add unique: {len(alter_ucs_ord)}")
    print(f"indices: {len(indexs_ord)} | indices trgm omitidos: {len(trgm)} (requieren pg_trgm)")
    print(f"vistas: {len(vistas_stmts)}")
    print(f"RLS omitido: {len(descartadas['rls'])} sentencias (fase seguridad/API)")
    for k, v in descartadas.items():
        if k in ("rls",):
            continue
        for s in v:
            print(f"  descartada [{k}]: {s}")
    print("orden:", ", ".join(orden))
    print("escrito:", DST)


if __name__ == "__main__":
    main()
