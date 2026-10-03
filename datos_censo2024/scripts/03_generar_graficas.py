"""03 - Graficas y muestras de datos (se generan desde procesado/ sin tocar fuentes).

Terminologia usada en las graficas (la misma del documento):
  Manzano = area amanzanada (unidad urbana en cartografia)
  Comunidad = area dispersa (unidad rural en cartografia)
  personas / viviendas  => campos de la fuente INE
  area cartografica = tipo de unidad (Manzano/Comunidad)
  area oficial = variable `area` de los microdatos INE (Urbana/Rural a nivel municipio)
"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESADO, GRAFICAS

PAL = {"Urbana": "#2c7fb8", "Rural": "#d95f0e", "Manzano": "#2c7fb8",
       "Comunidad": "#31a354", "Mixto": "#756bb1", "desv": "#c51b8a"}
DEP_ORDER = ["Chuquisaca", "La Paz", "Cochabamba", "Oruro", "Potosí",
             "Tarija", "Santa Cruz", "Beni", "Pando"]


def fmt(x): return f"{x:,.0f}".replace(",", ".")


def guardar(fig, sub, nombre):
    out = GRAFICAS / sub / nombre
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  grafico:", out)


def estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def nacionales(u):
    print("Graticas nacionales...")
    nm = int((u.tipo_unidad == "Manzano").sum()); nc = int((u.tipo_unidad == "Comunidad").sum())
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie([nm, nc], labels=["Manzano", "Comunidad"], colors=[PAL["Manzano"], PAL["Comunidad"]],
           autopct="%1.1f%%", startangle=90, wedgeprops=dict(width=0.42, edgecolor="w"))
    ax.set_title("Unidades censales 2024 (nacional)\n"
                 f"{fmt(nm)} Manzano · {fmt(nc)} Comunidad · {fmt(nm + nc)} total")
    guardar(fig, "nacional", "01_composicion_unidades_nacional.png")

    pman = int(u[u.tipo_unidad == "Manzano"].personas.sum())
    pcom = int(u[u.tipo_unidad == "Comunidad"].personas.sum())
    # oficial INE (municipios), sumado de area_oficial_municipios
    aom = pd.read_csv(PROCESADO / "area_oficial_municipios.csv")
    uof = int(aom.poblacion_urbana_oficial.sum()); rof = int(aom.poblacion_rural_oficial.sum())
    fig, ax = plt.subplots(figsize=(7, 4.5))
    cats = ["Urbana", "Rural"]; labels = ["Cartográfica\n(Manzano / Comunidad)", "Oficial INE\n(microdatos)"]
    cart = [pman, pcom]; ofc = [uof, rof]
    x = [0, 1]
    a = ax.bar(0, cart[0], width=0.35, label="Urbana", color=PAL["Urbana"])
    b = ax.bar(0, cart[1], bottom=cart[0], width=0.35, label="Rural", color=PAL["Rural"])
    ax.bar(1, ofc[0], width=0.35, color=PAL["Urbana"])
    ax.bar(1, ofc[1], bottom=ofc[0], width=0.35, color=PAL["Rural"])
    for i, (c_, o_) in enumerate([(cart, ofc)]):
        pass
    ax.text(0, pman / 2, fmt(pman), ha="center", va="center", color="white", fontweight="bold")
    ax.text(0, pman + pcom / 2, fmt(pcom), ha="center", va="center", color="white", fontweight="bold")
    ax.text(1, uof / 2, fmt(uof), ha="center", va="center", color="white", fontweight="bold")
    ax.text(1, uof + rof / 2, fmt(rof), ha="center", va="center", color="white", fontweight="bold")
    df_ = fmt(pman - uof)
    ax.annotate(f"Diferencia urbana: {df_} personas\n(personas en Manzano clasificadas Rural por el INE)",
                xy=(1.15, (uof + rof) / 2), ha="left", va="center", fontsize=9, color=PAL["desv"])
    ax.set_xticks([0, 1]); ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel("Personas")
    ax.set_title("Población urbana/rural: cartográfica vs. clasificación oficial del INE")
    ax.set_ylim(0, pman + pcom + (pman - uof))
    estilo(ax); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    ax.legend(loc="upper left")
    guardar(fig, "nacional", "02_poblacion_urbana_rural_cartografica_vs_oficial.png")

    # controles
    fig, ax = plt.subplots(figsize=(7, 4.5), subplot_kw=dict(aspect="equal"))
    tot = int(u.personas.sum()); viv = int(u.viviendas.sum())
    ax.pie([tot - viv, viv], labels=[f"Viviendas\n{fmt(viv)}", f"Personas\n{fmt(tot)}"],
           colors=[PAL["Manzano"], PAL["Comunidad"]], autopct=lambda p: f"{p:.1f}%",
           startangle=90, wedgeprops=dict(edgecolor="w"))
    ax.set_title(f"Controles al total oficial INE (diferencia 0)\nPersonas {fmt(tot)} · Viviendas {fmt(viv)}")
    guardar(fig, "nacional", "03_controles_totales_nacional.png")

    # poblacion por area_oficial
    r = pd.read_csv(PROCESADO / "resumen_municipios.csv")
    pob = r.groupby("area_oficial")["poblacion_total"].sum().reindex(["Mixto", "Rural", "Urbana"]).fillna(0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(pob.index, pob.values, color=[PAL["Mixto"], PAL["Rural"], PAL["Urbana"]])
    for b, v in zip(bars, pob.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 20000, fmt(int(v)), ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("Personas"); ax.set_title("Población según el área oficial del INE (por municipio)")
    ax.set_ylim(0, pob.max() * 1.15)
    estilo(ax); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    guardar(fig, "nacional", "04_poblacion_segun_area_oficial.png")


def departamentales(u, comp):
    print("Graticas por departamento...")
    c = comp.set_index("dep").reindex(range(1, 10))
    c["nombre_dep"] = [DEP_ORDER[i] for i in range(9)]
    g = u.groupby(["nombre_dep", "tipo_unidad"])["personas"].sum().unstack(fill_value=0).reindex(DEP_ORDER)
    gu = u.groupby("nombre_dep").apply(lambda x: int(x[x.tipo_unidad == "Manzano"].personas.sum()), include_groups=False).reindex(DEP_ORDER)
    gv = g.astype(int)
    total = gv.sum(axis=1)

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(gv.index, total.values, color=PAL["Manzano"])
    for b, v in zip(bars, total.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 30000, fmt(int(v)), ha="center", fontsize=9)
    ax.set_ylabel("Personas"); ax.set_title("Población total por departamento (Censo 2024)")
    ax.tick_params(axis="x", rotation=35); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    ax.set_ylim(0, total.max() * 1.12)
    estilo(ax)
    guardar(fig, "departamentos", "05_poblacion_total_por_departamento.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(gv.index, gv["Manzano"], label="Manzano", color=PAL["Manzano"])
    ax.bar(gv.index, gv["Comunidad"], bottom=gv["Manzano"], label="Comunidad", color=PAL["Comunidad"])
    ax.set_ylabel("Personas"); ax.set_title("Población por tipo de unidad censal (cartográfica) y departamento")
    ax.tick_params(axis="x", rotation=35); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    ax.legend(); estilo(ax)
    guardar(fig, "departamentos", "06_poblacion_manzano_comunidad_por_departamento.png")

    x = range(len(DEP_ORDER)); w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - w / 2 for i in x], gu.values, width=w, label="Manzano (cartográfica)", color=PAL["Manzano"])
    ax.bar([i + w / 2 for i in x], c["urbana"].astype(int).values, width=w, label="Urbana oficial (microdatos INE)", color=PAL["Urbana"])
    ax.set_xticks(list(x)); ax.set_xticklabels(DEP_ORDER, rotation=35)
    ax.set_ylabel("Personas"); ax.set_title("Población urbana: cartográfica (Manzano) vs. oficial INE, por departamento")
    ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    ax.legend(); estilo(ax)
    guardar(fig, "departamentos", "07_urbana_cartografica_vs_oficial_por_departamento.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(DEP_ORDER, c["d_urbana"].astype(int).values, color=PAL["desv"])
    for b, v in zip(bars, c["d_urbana"].astype(int).values):
        ax.text(b.get_x() + b.get_width() / 2, v + 9000, fmt(int(v)), ha="center", fontsize=9)
    ax.set_ylabel("Personas en Manzano clasificadas Rural (INE)"); ax.set_title("Discrepancia urbana por departamento")
    ax.tick_params(axis="x", rotation=35); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    estilo(ax)
    guardar(fig, "departamentos", "08_discrepancia_urbana_por_departamento.png")

    vv = u.groupby("nombre_dep")["viviendas"].sum().reindex(DEP_ORDER)
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(vv.index, vv.values, color=PAL["Comunidad"])
    for b, v in zip(bars, vv.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 30000, fmt(int(v)), ha="center", fontsize=9)
    ax.set_ylabel("Viviendas"); ax.set_title("Viviendas por departamento")
    ax.tick_params(axis="x", rotation=35); ax.get_yaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    ax.set_ylim(0, vv.max() * 1.12); estilo(ax)
    guardar(fig, "departamentos", "09_viviendas_por_departamento.png")

    nu = u.groupby("nombre_dep")["tipo_unidad"].value_counts().unstack(fill_value=0).reindex(DEP_ORDER)[["Manzano", "Comunidad"]].astype(int)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(nu.index, nu["Manzano"], label="Manzano", color=PAL["Manzano"])
    ax.bar(nu.index, nu["Comunidad"], bottom=nu["Manzano"], label="Comunidad", color=PAL["Comunidad"])
    ax.set_ylabel("Nº de unidades"); ax.set_title("Unidades censales (Manzano y Comunidad) por departamento")
    ax.tick_params(axis="x", rotation=35); ax.legend(); estilo(ax)
    guardar(fig, "departamentos", "10_unidades_por_departamento.png")


def municipales(r):
    print("Graticas de municipios...")
    r = r.copy(); r["desv"] = r.poblacion_urbana - r.poblacion_urbana_oficial
    top = r.sort_values("desv", ascending=False).head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6.5))
    ax.barh([f"{m} ({d.split()[-1]})" for m, d in zip(top.nombre_mun, top.nombre_dep)],
            top.desv.values, color=PAL["desv"])
    for i, v in enumerate(top.desv.values):
        ax.text(v + 800, i, fmt(int(v)), va="center", fontsize=9)
    ax.set_xlabel("Personas en Manzano que el INE clasifica como Rural")
    ax.set_title("Municipios con mayor desajuste urbano (cartográfica vs. oficial)")
    ax.set_xlim(0, top.desv.max() * 1.12)
    ax.get_xaxis().set_major_formatter(mtick.FuncFormatter(lambda v, p: fmt(v)))
    estilo(ax); ax.grid(axis="x", alpha=0.3)
    guardar(fig, "municipios", "11_top_municipios_desajuste_manzano_oficial_rural.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    counts = r.area_oficial.value_counts().reindex(["Mixto", "Rural", "Urbana"]).fillna(0).astype(int)
    bars = ax.bar(counts.index, counts.values, color=[PAL["Mixto"], PAL["Rural"], PAL["Urbana"]])
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 5, str(int(v)), ha="center", fontweight="bold", fontsize=11)
    ax.set_title("Municipios según su área oficial (INE): Mixto / Rural / Urbana\n(Urbana = Colcapirhua)")
    ax.set_ylabel("Nº de municipios"); ax.set_ylim(0, max(counts.values) * 1.15)
    estilo(ax)
    guardar(fig, "municipios", "12_municipios_por_area_oficial.png")


def muestras(u, r):
    print("Muestras de datos...")
    (GRAFICAS / "ejemplos").mkdir(parents=True, exist_ok=True)
    m1 = u.sort_values(["tipo_unidad", "personas"], ascending=[True, False]).head(6)
    m1 = pd.concat([m1, u.sort_values(["tipo_unidad", "personas"], ascending=[True, False]).tail(3)])
    m1 = m1[["codigo", "nombre", "tipo_unidad", "area", "personas", "viviendas",
             "codigo_municipio", "nombre_dep", "nombre_prov", "nombre_mun", "area_oficial"]]
    m1.to_csv(GRAFICAS / "ejemplos" / "muestra_unidades.csv", index=False)
    m2 = r[["codigo_municipio", "nombre_dep", "nombre_mun", "n_manzanos", "n_comunidades",
            "poblacion_urbana", "poblacion_rural", "poblacion_total",
            "poblacion_urbana_oficial", "poblacion_rural_oficial", "area_oficial"]].head(10)
    m2.to_csv(GRAFICAS / "ejemplos" / "muestra_resumen_municipios.csv", index=False)
    aom = pd.read_csv(PROCESADO / "area_oficial_municipios.csv")
    aom = aom.merge(r[["codigo_municipio", "nombre_dep", "nombre_mun"]], on="codigo_municipio")
    aom[["codigo_municipio", "nombre_dep", "nombre_mun", "poblacion_urbana_oficial",
         "poblacion_rural_oficial", "poblacion_total_oficial"]].to_csv(
        GRAFICAS / "ejemplos" / "muestra_area_oficial_municipios.csv", index=False)
    print("  muestras csv en graficas/ejemplos/")


def main():
    u = pd.read_csv(PROCESADO / "unidades_censo2024.csv")
    comp = pd.read_csv(PROCESADO / "comparacion_departamentos_censo2024.csv")
    r = pd.read_csv(PROCESADO / "resumen_municipios.csv")
    nacionales(u)
    departamentales(u, comp)
    municipales(r)
    muestras(u, r)
    print("Graticas listas en", GRAFICAS)


if __name__ == "__main__":
    main()