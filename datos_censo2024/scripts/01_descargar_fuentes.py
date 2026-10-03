"""01 - Descarga de fuentes (los originales se respaldan en fuentes/).

Replica exactamente lo hecho en la sesion: universo y geometrias del geoportal INE
via censosbo, microdatos de personas, diccionario de municipios y los limites
municipales de SDSN Bolivia (descargados desde la carpeta de Google Drive que el QR
de la ficha apunta).
"""
import sys, zipfile, io, re
from pathlib import Path
import requests
import gdown
import fitz  # PyMuPDF (solo para extraer el QR/URI de la ficha SDSN)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FUENTES, RELEASE_FICHAS, RELEASE_MICRO, SDSN_DRIVE_FOLDER, SDSN_ZIP_NAME

URLS_UNIVERSO = {
    "unidad.parquet": f"{RELEASE_FICHAS}/unidad.parquet",
    "geo_comunidad.parquet": f"{RELEASE_FICHAS}/geo_comunidad.parquet",
    "ficha.parquet": f"{RELEASE_FICHAS}/ficha.parquet",
    "diccionario_fichas_v1.parquet": f"{RELEASE_FICHAS}/diccionario_fichas_v1.parquet",
    "municipios.csv": f"{RELEASE_FICHAS}/municipios.csv",
}
for dep in (f"0{i}" for i in range(1, 10)):
    URLS_UNIVERSO[f"geo_manzano_dep{dep}.parquet"] = f"{RELEASE_FICHAS}/geo_manzano_dep{dep}.parquet"
URLS_MICRO = {f"persona_dep{dep:02d}.parquet": f"{RELEASE_MICRO}/persona_dep{dep:02d}.parquet"
              for dep in range(1, 10)}


def descargar_si_falta(url: str, destino: Path) -> None:
    if destino.exists():
        print(f"  [ya existe] {destino.name}")
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [descarga] {url}")
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)


def tipo_unidad_por_sufijo(codigo: str) -> str:
    """-A => manzano; -D/-M => comunidad (denominacion que usamos)."""
    return "Manzano" if codigo.endswith("-A") else "Comunidad"


def extraer_uri_del_qr_de_la_ficha(ficha_pdf: Path) -> str:
    """La ficha SDSN embebe un QR con la URI de la carpeta de datos; se extrae del PDF."""
    doc = fitz.open(ficha_pdf)
    for page in doc:
        for link in page.get_links():
            uri = (link.get("uri") or "")
            if "drive.google.com/drive/folders" in uri:
                print(f"  URI del QR encontrada: {uri}")
                return uri
    raise RuntimeError("No se encontro la URI de Google Drive en la ficha")


def descargar_limites_sdsn() -> Path:
    destino = FUENTES / "limites_municipales_sdsn2025"
    destino.mkdir(parents=True, exist_ok=True)
    zip_out = destino / f"{SDSN_ZIP_NAME}.zip"
    # se guarda la ficha como evidencia
    return destino, zip_out


if __name__ == "__main__":
    print("== Universo y geometrias (geoportal INE via censosbo) ==")
    for name, url in URLS_UNIVERSO.items():
        sub = "geometria_manzanos" if name.startswith("geo_manzano") else "."
        descargar_si_falta(url, FUENTES / sub / name)

    print("== Microdatos de personas (INE) ==")
    for name, url in URLS_MICRO.items():
        descargar_si_falta(url, FUENTES / "personas" / name)

    print("== Limites municipales SDSN Bolivia (via QR de la ficha) ==")
    ficha = FUENTES / "limites_municipales_sdsn2025" / "Ficha-Limites-municipales_SDSN.pdf"
    # (La ficha ya descargada se respalda en la carpeta; aqui se demuestra la evidencia del QR.)
    if ficha.exists():
        uri = extraer_uri_del_qr_de_la_ficha(ficha)
    else:
        uri = f"https://drive.google.com/drive/folders/{SDSN_DRIVE_FOLDER}"
    print(f"  Descargando carpeta de Drive: {uri}")
    gdown.download_folder(uri, output=str(FUENTES / "limites_municipales_sdsn2025"), quiet=False)

    print("Fuentes listas.")