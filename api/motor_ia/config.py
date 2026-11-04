import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

MOTOR_IA_SCHEMA = os.getenv("MOTOR_IA_SCHEMA", "motor_ia").strip() or "motor_ia"

_upload_dir = Path(os.getenv("MOTOR_IA_UPLOAD_DIR", "uploads/motor_ia"))
if not _upload_dir.is_absolute():
    _upload_dir = BASE_DIR / _upload_dir
UPLOAD_DIR = _upload_dir
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ENV_FILE_PATH = ENV_FILE
