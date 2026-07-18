from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth.router import router as auth_router
from .shared.router import router as shared_router
from .edan.router import router as edan_router
from .rea.router import router as rea_router
from .usuarios.router import router as usuarios_router

app = FastAPI(
    title="SINAGERSAT API",
    description="API del Sistema Nacional de Alerta Temprana y Gestión de Riesgos - EDAN y REA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(shared_router, prefix="/api/v1")
app.include_router(edan_router, prefix="/api/v1")
app.include_router(rea_router, prefix="/api/v1")
app.include_router(usuarios_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "SINAGERSAT API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
