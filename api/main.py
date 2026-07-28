from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .auth.router import router as auth_router
from .shared.router import router as shared_router
from .edan.router import router as edan_router
from .rea.router import router as rea_router
from .usuarios.router import router as usuarios_router
from .upload import router as upload_router

TAGS_METADATA = [
    {"name": "Auth",                    "description": "Login y registro de usuarios (JWT)"},
    {"name": "Geografía",               "description": "Departamentos, provincias y municipios de Bolivia (INE 2024)"},
    {"name": "Geografía > Departamentos", "description": "CRUD de los 9 departamentos"},
    {"name": "Geografía > Provincias",    "description": "CRUD de las 112 provincias"},
    {"name": "Geografía > Municipios",    "description": "CRUD de los 340 municipios"},
    {"name": "Geografía > GeoJSON",       "description": "Municipios en formato GeoJSON (RFC 7946) para mapas web"},
    {"name": "Geografía > GEOM/WKT",      "description": "Municipios con geometría en formato WKT (Well-Known Text)"},
    {"name": "Geografía > Ubicación",     "description": "Identificar municipio por coordenadas (punto-dentro-de-polígono)"},
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
    {"name": "Upload",                  "description": "Subida de archivos (imágenes)"},
]

app = FastAPI(
    title="SINAGERSAT API",
    description=(
        "API del Sistema Nacional de Alerta Temprana y Gestión de Riesgos.\n\n"
        "## Formato de respuestas\n"
        "Todas las respuestas exitosas usan el formato:\n"
        "```json\n"
        '{"success": true, "message": "...", "data": ..., "total": ...}\n'
        "```\n\n"
        "## Autenticación\n"
        "1. **Público** (no requiere token): Auth, Geografía\n"
        "2. **Protegido** (requiere token): EDAN, REA, Usuarios\n\n"
        "### Obtener token\n"
        "1. Registrar usuario: `POST /api/v1/auth/register`\n"
        "2. Login: `POST /api/v1/auth/login` → obtiene token JWT\n"
        "3. Click **Authorize** arriba a la derecha → pegar el token\n"
        "4. Ahora puedes usar todos los endpoints protegidos\n\n"
        "## Módulos\n"
        "- **Auth**: Login y registro (público)\n"
        "- **Geografía**: Departamentos, provincias, municipios (público)\n"
        "- **EDAN**: Evaluación de Daños y Análisis de Necesidades (requiere token)\n"
        "- **REA**: Reportes de Eventos Adversos (requiere token)\n"
        "- **Usuarios**: Gestión de cuentas, roles y permisos (requiere token)\n"
    ),
    version="1.2.5",
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
app.include_router(upload_router, prefix="/api/v1")

uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Error interno del servidor",
            "error_code": 500,
        },
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Error de validación en los datos enviados",
            "error_code": 422,
        },
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAGS_METADATA,
    )
    schema["components"] = schema.get("components", {})
    schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Pega tu token JWT aquí. Obtén uno con POST /api/v1/auth/login",
        }
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def root():
    return {
        "name": "SINAGERSAT API",
        "version": "1.2.5",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
