from fastapi import APIRouter

from .routes import busqueda, chat, documentos, grupos, llm, tipos, verificacion, voz

router = APIRouter(prefix="/motor-ia")

router.include_router(chat.router)
router.include_router(busqueda.router)
router.include_router(documentos.router)
router.include_router(tipos.router)
router.include_router(grupos.router)
router.include_router(llm.router)
router.include_router(verificacion.router)
router.include_router(voz.router)


@router.get("/health", tags=["MotorIA > Estado"])
def health():
    return {"status": "ok", "module": "motor-ia"}
