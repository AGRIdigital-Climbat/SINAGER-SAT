from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth.router import router as auth_router
from .shared.router import router as shared_router
from .edan.router import router as edan_router
from .rea.router import router as rea_router
from .usuarios.router import router as usuarios_router

TAGS_METADATA = [
    {"name": "Auth",                    "description": "Login y registro de usuarios (JWT)"},
    {"name": "Geografía",               "description": "Departamentos, provincias y municipios de Bolivia (INE 2024)"},
    {"name": "Geografía > Departamentos", "description": "CRUD de los 9 departamentos"},
    {"name": "Geografía > Provincias",    "description": "CRUD de las 112 provincias"},
    {"name": "Geografía > Municipios",    "description": "CRUD de los 340 municipios"},
    {"name": "EDAN",                    "description": "Formularios de Evaluación de Daños y Análisis de Necesidades"},
    {"name": "EDAN > Formulario",       "description": "CRUD principal del formulario EDAN"},
    {"name": "EDAN > Catálogos",        "description": "Catálogos de referencia: tipo evento, grupo etario, servicios, protección, ayuda"},
    {"name": "EDAN > Población",        "description": "Población por grupo etario y tipos de evento del EDAN"},
    {"name": "EDAN > Salud",            "description": "Primera respuesta, establecimientos y necesidades de salud"},
    {"name": "EDAN > Infraestructura",  "description": "Vial, pública y servicios básicos"},
    {"name": "EDAN > Educación",        "description": "Daño educativo y afectación"},
    {"name": "EDAN > Producción",       "description": "Vivienda, agricultura, pecuaria e infraestructura productiva"},
    {"name": "EDAN > Protección",       "description": "Protección, ayuda humanitaria y comunidades"},
    {"name": "REA",                     "description": "Reportes de Eventos Adversos"},
    {"name": "REA > Reportes",          "description": "Crear, consultar y gestionar reportes de eventos"},
    {"name": "REA > Estados",           "description": "Estados del ciclo de vida del reporte"},
    {"name": "REA > Categorías",        "description": "Categorías de afectación del REA"},
    {"name": "Usuarios",                "description": "Gestión de usuarios del sistema"},
    {"name": "Usuarios > Cuentas",      "description": "CRUD de cuentas de usuario"},
    {"name": "Usuarios > Roles",        "description": "Roles y asignación usuario-rol"},
    {"name": "Usuarios > Aplicaciones", "description": "Aplicaciones registradas en el sistema"},
    {"name": "Usuarios > Permisos",     "description": "Asignación de permisos por rol y aplicación"},
    {"name": "Usuarios > Sesiones",     "description": "Sesiones activas de usuarios"},
    {"name": "Usuarios > Auditoría",    "description": "Log de auditoría y resets de contraseña"},
]

app = FastAPI(
    title="SINAGERSAT API",
    description=(
        "API del Sistema Nacional de Alerta Temprana y Gestión de Riesgos.\n\n"
        "Módulos:\n"
        "- **EDAN**: Evaluación de Daños y Análisis de Necesidades (23 tablas)\n"
        "- **REA**: Reportes de Eventos Adversos (4 tablas)\n"
        "- **Geografía**: División político-administrativa de Bolivia INE 2024\n"
        "- **Usuarios**: Gestión de cuentas, roles y permisos\n"
    ),
    version="1.1.0",
    openapi_tags=TAGS_METADATA,
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
