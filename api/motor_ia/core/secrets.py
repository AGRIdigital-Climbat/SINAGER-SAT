"""
Cifrado AES-256-GCM de secretos (apikey) con clave maestra fuera de la BD.

Producción: migrar a un gestor de secretos real (AWS Secrets Manager,
GCP Secret Manager, HashiCorp Vault). La interfaz (encrypt/decrypt/enmascarar)
se mantiene sin cambios solo cambiando el backend de get_master_key().
"""

import os
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_TOKEN_PREFIX = "AESGCM."
_KEY_ENV_FILE = "LLM_MASTER_KEY_FILE"
_KEY_DEFAULT_PATH = ".keys/motor_ia_llm_master.key"
_BASE_DIR = Path(__file__).resolve().parents[3]


def _key_path() -> Path:
    env = os.getenv(_KEY_ENV_FILE, "").strip()
    if env:
        path = Path(env)
        return path if path.is_absolute() else _BASE_DIR / path
    return _BASE_DIR / _KEY_DEFAULT_PATH


def get_master_key() -> bytes:
    """Devuelve la clave maestra (32 bytes). La crea y persiste si falta."""
    path = _key_path()
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        return base64.b64decode(raw)

    key = AESGCM.generate_key(bit_length=256)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(base64.b64encode(key).decode("utf-8") + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def encrypt_secret(plaintext: str) -> str:
    """Cifra plaintext y devuelve token 'AESGCM.<nonce_b64>.<ct_b64>'."""
    if not plaintext:
        return ""
    key = get_master_key()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return _TOKEN_PREFIX + base64.b64encode(nonce).decode() + "." + base64.b64encode(ct).decode()


def decrypt_secret(token: str) -> str:
    """Descifra un token AESGCM o devuelve el string tal cual (fallback legacy)."""
    if not token or not token.startswith(_TOKEN_PREFIX):
        return token
    _, rest = token.split(".", 1)
    nonce_b64, ct_b64 = rest.split(".", 1)
    key = get_master_key()
    return AESGCM(key).decrypt(
        base64.b64decode(nonce_b64),
        base64.b64decode(ct_b64),
        None,
    ).decode("utf-8")


def enmascarar_clave(token: str) -> str:
    """Devuelve una máscara legible de la apikey (nunca el valor real)."""
    if not token:
        return ""
    try:
        plaintext = decrypt_secret(token)
    except Exception:
        plaintext = token
    if len(plaintext) <= 8:
        return "••••••••"
    return plaintext[:4] + "•••" + plaintext[-4:]


def es_cifrado(token: str) -> bool:
    """True si el valor ya está cifrado (para migración idempotente)."""
    return bool(token) and token.startswith(_TOKEN_PREFIX)
