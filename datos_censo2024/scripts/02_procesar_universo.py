"""02 - Procesamiento del universo censal: de fuentes/ a procesado/ y geo/.

Reconstruye (idempotente) todos los archivos derivados con la semantica oficial
corregida:
  * `area` del geoportal: 1 = Manzano (area amanzanada), 2 = Comunidad (area dispersa).
  * `area` de los microdatos INE: 1 = urbana, 2 = rural  (convencion que uso el INE).
  * `area_oficial` por municipio = agregado de los microdatos (Urbana/Rural/Mixto).

ADVERTENCIA (bug que se detecto y corrigio): los campos idep/iprov/imun de los
parquets vienen como *string*; NO hay que concatenarlos como texto (Python repite la
cadena y revienta la memoria). Siempre se convierten a entero antes de unir.
"""
import sys, glob
from pathlib import Path
import pandas as pd
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FUENTES, PROCESADO, GEO, DEPARTAMENTOS


def load_unidades_y_geo():
    u = pd.read_parquet(FUENTES / "unidad.parquet")

    def from_wkb(path):
        d = pd.read_parquet(path)
        return gpd.GeoDataFrame(d.drop(columns="geometria"),
                                geometry=gpd.GeoSeries.from_wkb(d.geometria), crs=4326)

    man = pd.concat([from_wkb(FUENTES / "geometria_manzanos" / f"geo_manzano_dep{dep}.parquet")
                     for dep in (f"0{i}" for i in range(1, 10))], ignore_index=True)
    com = from_wkb(FUENTES / "geo_comunidad.parquet")
    return u, man.to_crs(4326), com.to_crs(4326)


def reconstruir_area_oficial():
    """Variable `area` de los microdatos (1=urbana) agregada a nivel municipio."""
    filas = []
    for f in sorted(glob.glob(str(FUENTES / "personas" / "persona_dep*.parquet"))):
        d = pd.read_parquet(f, columns=["idep", "iprov", "imun", "area"])
        for c in ("idep", "iprov", "imun"):
            d[c] = pd.to_numeric(d[c], errors="coerce")          # str -> int
        d["codigo_municipio"] = (d.idep * 10000 + d.iprov * 100 + d.imun).astype("int64")
        g = d.groupby("codigo_municipio").apply(lambda x: pd.Series({
            "poblacion_urbana_oficial": int((x.area == 1).sum()),
            "poblacion_rural_oficial": int((x.area == 2).sum()),
            "poblacion_total_oficial": len(x),
        }), include_groups=False)
        filas.append(g)
    gt = pd.concat(filas).groupby(level=0).sum().reset_index()
    gt["area_oficial"] = gt.apply(
        lambda r: "Urbana" if r.poblacion_rural_oficial == 0
        else "Rural" if r.poblacion_urbana_oficial == 0 else "Mixto", axis=1)
    return gt


def main():
    PROCESADO.mkdir(exist_ok=True); GEO.mkdir(exist_ok=True)
    print("Cargando universo y geometrias...")
    u, man, com = load_unidades_y_geo()
    muni = pd.read_csv(FUENTES / "municipios.csv")

    # ------------------------------------------------------------------ universo
    for c in ("idep", "iprov", "imun"):
        u[c] = pd.to_numeric(u[c], errors="coerce")
    u["codigo_departamento"] = u.idep.astype("int64")
    u["codigo_provincia"] = u.idep * 100 + u.iprov
    u["codigo_municipio"] = (u.idep * 10000 + u.iprov * 100 + u.imun).astype("int64")
    u["tipo_unidad"] = u["codigo"].map(lambda c: "Manzano" if c.endswith("-A") else "Comunidad")

    # lat/lon: manzano = centroide (reproyectando a ESRI:102033, mas exacto); comunidad = punto
    centro = man.geometry.to_crs("ESRI:102033").centroid.to_crs(4326)
    man["lon"], man["lat"] = centro.x, centro.y
    com["lon"], com["lat"] = com.geometry.x, com.geometry.y
    geo = pd.concat([man[["codigo", "lon", "lat"]], com[["codigo", "lon", "lat"]]],
                    ignore_index=True)
    df = u.merge(geo, on="codigo", how="left")
    df = df.merge(muni[["codigo_ine", "nombre_dep", "nombre_prov", "nombre_mun"]],
                  left_on="codigo_municipio", right_on="codigo_ine", how="left").drop(columns="codigo_ine")

    gt = reconstruir_area_oficial()
    df = df.merge(gt[["codigo_municipio", "area_oficial"]], on="codigo_municipio", how="left")

    cols = ["codigo", "nombre", "tipo_unidad", "area", "personas", "viviendas", "ficha",
            "idep", "iprov", "imun", "codigo_departamento", "codigo_provincia", "codigo_municipio",
            "nombre_dep", "nombre_prov", "nombre_mun", "lat", "lon", "area_oficial"]
    df = df[cols]
    df.to_csv(PROCESADO / "unidades_censo2024.csv", index=False)
    df[df.tipo_unidad == "Manzano"].to_csv(PROCESADO / "manzanos_censo2024.csv", index=False)
    df[df.tipo_unidad == "Comunidad"].to_csv(PROCESADO / "comunidades_censo2024.csv", index=False)

    # provincias
    provs = muni[["idep", "iprov", "nombre_dep", "nombre_prov"]].drop_duplicates()
    provs["codigo_provincia"] = provs.idep * 100 + provs.iprov
    provs[["codigo_provincia", "idep", "nombre_dep", "iprov", "nombre_prov"]].sort_values(
        ["codigo_provincia"]).to_csv(PROCESADO / "provincias_2024.csv", index=False)

    # relacion comunidad -> territorio
    df[df.tipo_unidad == "Comunidad"][
        ["codigo", "nombre", "idep", "iprov", "imun", "codigo_municipio",
         "nombre_dep", "nombre_prov", "nombre_mun"]].to_csv(
        PROCESADO / "relacion_comunidad_provincia.csv", index=False)

    # resumen municipal
    res = df.groupby("codigo_municipio").apply(lambda x: pd.Series({
        "nombre_dep": x.nombre_dep.iloc[0], "nombre_prov": x.nombre_prov.iloc[0],
        "nombre_mun": x.nombre_mun.iloc[0],
        "n_manzanos": int((x.tipo_unidad == "Manzano").sum()),
        "n_comunidades": int((x.tipo_unidad == "Comunidad").sum()),
        "n_unidades": len(x),
        "poblacion_urbana": int(x[x.tipo_unidad == "Manzano"].personas.sum()),
        "poblacion_rural": int(x[x.tipo_unidad == "Comunidad"].personas.sum()),
        "poblacion_total": int(x.personas.sum()),
        "viviendas_urbana": int(x[x.tipo_unidad == "Manzano"].viviendas.sum()),
        "viviendas_rural": int(x[x.tipo_unidad == "Comunidad"].viviendas.sum()),
        "viviendas_total": int(x.viviendas.sum()),
    }), include_groups=False)
    res = res.join(gt.set_index("codigo_municipio")[
        ["poblacion_urbana_oficial", "poblacion_rural_oficial", "area_oficial"]])
    res = res.reset_index().rename(columns={"index": "codigo_municipio"})
    res = res[["codigo_municipio", "nombre_dep", "nombre_prov", "nombre_mun",
               "n_manzanos", "n_comunidades", "n_unidades", "poblacion_urbana", "poblacion_rural",
               "poblacion_total", "viviendas_urbana", "viviendas_rural", "viviendas_total",
               "poblacion_urbana_oficial", "poblacion_rural_oficial", "area_oficial"]]
    res.to_csv(PROCESADO / "resumen_municipios.csv", index=False)

    gt.to_csv(PROCESADO / "area_oficial_municipios.csv", index=False)

    # comparacion por departamento (cartografico vs microdatos)
    comp = df.groupby("codigo_departamento").apply(lambda x: pd.Series({
        "n_urbana": int(x[x.tipo_unidad == "Manzano"].personas.sum()),
        "n_rural": int(x[x.tipo_unidad == "Comunidad"].personas.sum()),
        "n_total": int(x.personas.sum()),
    }), include_groups=False)
    gd = gt.copy(); gd["dep"] = gd.codigo_municipio // 10000
    gd = gd.groupby("dep")[["poblacion_urbana_oficial", "poblacion_rural_oficial"]].sum().rename(
        columns={"poblacion_urbana_oficial": "urbana", "poblacion_rural_oficial": "rural"})
    comp = comp.join(gd)
    comp["total"] = comp.urbana + comp.rural
    comp[["d_total", "d_urbana", "d_rural"]] = comp[["n_total", "n_urbana", "n_rural"]].values - \
        comp[["total", "urbana", "rural"]].values
    comp["dep"] = comp.index; comp["nombre_dep"] = comp.dep.map({int(k): v for k, v in DEPARTAMENTOS.items()})
    comp[["dep", "nombre_dep", "n_urbana", "urbana", "n_rural", "rural", "n_total", "total",
          "d_total", "d_urbana", "d_rural"]].to_csv(
        PROCESADO / "comparacion_departamentos_censo2024.csv", index=False)

    # ------------------------------------------------------------------ GeoPackage
    shp = glob.glob(str(FUENTES / "limites_municipales_sdsn2025" / "*.shp"))[0]
    limits = gpd.read_file(shp).to_crs(4326)
    limits = limits.rename(columns={"Codigo_INE": "codigo_municipio", "Depart": "nombre_dep",
                                    "Provincia": "nombre_prov", "Municipio": "nombre_mun",
                                    "Capital": "capital", "Pob_2012": "poblacion_2012",
                                    "Pob_2024": "poblacion_2024", "Sup_Km2": "superficie_km2"})
    limits = limits.merge(gt[["codigo_municipio", "area_oficial"]], on="codigo_municipio", how="left")

    gpk = GEO / "unidades_censo2024.gpkg"
    if gpk.exists(): gpk.unlink()
    man_g = gpd.GeoDataFrame(df[df.tipo_unidad == "Manzano"].merge(
        man.drop(columns=["lon", "lat"]), on="codigo", how="left"), geometry="geometry", crs=4326)
    com_g = gpd.GeoDataFrame(df[df.tipo_unidad == "Comunidad"].merge(
        com.drop(columns=["lon", "lat"]), on="codigo", how="left"), geometry="geometry", crs=4326)
    man_g.to_file(gpk, layer="manzanos", driver="GPKG")
    com_g.to_file(gpk, layer="comunidades", driver="GPKG")
    limits[["codigo_municipio", "nombre_dep", "nombre_prov", "nombre_mun", "capital",
            "poblacion_2012", "poblacion_2024", "superficie_km2", "area_oficial", "geometry"]] \
        .to_file(gpk, layer="municipios", driver="GPKG")

    # municipios_censo2024.csv a partir del shapefile (atributos oficiales SDSN)
    limits.drop(columns="geometry")[["codigo_municipio", "nombre_dep", "nombre_prov", "nombre_mun",
                                     "capital", "poblacion_2012", "poblacion_2024", "superficie_km2"]] \
        .to_csv(PROCESADO / "municipios_censo2024.csv", index=False)

    print("Capa GPKG:", gpd.list_layers(gpk).to_dict("records"))
    print("Invariancias: unidades", len(df), "| personas", int(df.personas.sum()),
          "| viviendas", int(df.viviendas.sum()),
          "| oficial urbana", int(gt.poblacion_urbana_oficial.sum()),
          "| rural", int(gt.poblacion_rural_oficial.sum()))


if __name__ == "__main__":
    main()