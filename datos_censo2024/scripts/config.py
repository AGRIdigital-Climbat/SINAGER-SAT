"""Configuracion compartida del pipeline Censo 2024 (carpeta datos_censo2024)."""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent            # datos_censo2024/
FUENTES = BASE / "fuentes"
PROCESADO = BASE / "procesado"
GEO = BASE / "geo"
GRAFICAS = BASE / "graficas"
SCRIPT_DIR = Path(__file__).resolve().parent

DEPARTAMENTOS = {
    "01": "Chuquisaca", "02": "La Paz", "03": "Cochabamba", "04": "Oruro",
    "05": "Potosí", "06": "Tarija", "07": "Santa Cruz", "08": "Beni", "09": "Pando",
}

# Releases de censosbo (Lab TecnoSocial) que replican el geoportal del INE.
RELEASE_FICHAS = "https://github.com/lab-tecnosocial/censosbo/releases/download/data-fichas-v1.0.0"
RELEASE_MICRO  = "https://github.com/lab-tecnosocial/censosbo/releases/download/data-v1.0.0"

# Si la base REDATAM usa 'area' con el mismo codigo que el geoportal (1=urbana, 2=rural).
AREA_1_URBANA = True

# Carpeta de Google Drive extraida del QR de la ficha de limites municipales de SDSN.
SDSN_DRIVE_FOLDER = "1_S6VTI6uUrGgGXVbSCSXY_41VxNn-5cq"
SDSN_ZIP_NAME = "SDSN_Limites_Municipales_Bolivia_2026.zip"