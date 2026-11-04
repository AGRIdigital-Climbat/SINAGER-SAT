import os

from dotenv import load_dotenv

from ..config import ENV_FILE

load_dotenv(ENV_FILE)

_model = None
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")


def _whisper_disponible():
    try:
        import whisper  # noqa: F401

        return True
    except ImportError:
        return False


def cargar_modelo():
    global _model
    if not _whisper_disponible():
        raise RuntimeError(
            "Whisper no esta instalado. Instale con: pip install openai-whisper"
        )
    if _model is None:
        import whisper

        print(f"Cargando modelo Whisper {WHISPER_MODEL}...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("Modelo Whisper cargado.")
    return _model


def transcribir_audio(audio_path):
    model = cargar_modelo()
    resultado = model.transcribe(audio_path, language="es")
    return resultado["text"]
