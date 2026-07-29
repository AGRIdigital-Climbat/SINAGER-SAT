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
from .audit import AuditMiddleware

TAGS_METADATA = [
    {"name": "Auth",                      "description": "Login y registro de usuarios (JWT)"},
    {"name": "Geografía > Departamentos", "description": "CRUD de los 9 departamentos"},
    {"name": "Geografía > Provincias",    "description": "CRUD de las 112 provincias"},
    {"name": "Geografía > Municipios",    "description": "CRUD de los 340 municipios"},
    {"name": "Geografía > GeoJSON",       "description": "Municipios en GeoJSON (RFC 7946) para mapas web"},
    {"name": "Geografía > GEOM/WKT",      "description": "Municipios con geometría en WKT"},
    {"name": "Geografía > Ubicación",     "description": "Identificar municipio por coordenadas"},
    {"name": "EDAN > Formulario",         "description": "CRUD principal del formulario EDAN"},
    {"name": "EDAN > Catálogos",          "description": "Tipo evento, grupo etario, servicios, protección, ayuda"},
    {"name": "EDAN > Población",          "description": "Población por grupo etario y tipos de evento"},
    {"name": "EDAN > Salud",              "description": "Primera respuesta, establecimientos y necesidades"},
    {"name": "EDAN > Infraestructura",    "description": "Vial, pública y servicios básicos"},
    {"name": "EDAN > Educación",          "description": "Daño educativo y afectación"},
    {"name": "EDAN > Producción",         "description": "Vivienda, agricultura, pecuaria e infraestructura"},
    {"name": "EDAN > Protección",         "description": "Protección, ayuda humanitaria y comunidades"},
    {"name": "REA > Reportes",            "description": "Crear, consultar y gestionar reportes de eventos"},
    {"name": "REA > Estados",             "description": "Estados del ciclo de vida del reporte"},
    {"name": "REA > Categorías",          "description": "Categorías de afectación del REA"},
    {"name": "Usuarios > Cuentas",        "description": "CRUD de cuentas de usuario"},
    {"name": "Usuarios > Roles",          "description": "Roles y asignación usuario-rol"},
    {"name": "Usuarios > Aplicaciones",   "description": "Aplicaciones registradas en el sistema"},
    {"name": "Usuarios > Permisos",       "description": "Asignación de permisos por rol y aplicación"},
    {"name": "Usuarios > Sesiones",       "description": "Sesiones activas de usuarios"},
    {"name": "Usuarios > Auditoría",      "description": "Log de auditoría"},
    {"name": "Usuarios > Acciones",       "description": "Acciones del sistema"},
    {"name": "Upload",                    "description": "Subida de archivos (imágenes)"},
]

app = FastAPI(
    title="SINAGERSAT API",
    description="API del Sistema Nacional de Alerta Temprana y Gestión de Riesgos.",
    version="1.2.7",
    openapi_tags=TAGS_METADATA,
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

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


import json
from fastapi.responses import HTMLResponse


def _html_safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(req: Request):
    openapi_url = "/openapi.json"
    title = "SINAGERSAT API - Documentación"
    swagger_js_url = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"
    swagger_css_url = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    swagger_favicon_url = "https://fastapi.tiangolo.com/img/favicon.png"

    current_swagger_ui_parameters = {
        "dom_id": "#swagger-ui",
        "layout": "BaseLayout",
        "deepLinking": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "filter": True,
        "syntaxHighlight": {"theme": "monokai"},
        "docExpansion": "none",
        "displayRequestDuration": True,
    }

    params_str = ""
    for key, value in current_swagger_ui_parameters.items():
        params_str += f"{_html_safe_json(key)}: {_html_safe_json(value)},\n"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link type="text/css" rel="stylesheet" href="{swagger_css_url}">
<link rel="shortcut icon" href="{swagger_favicon_url}">
<title>{title}</title>
<style>
  .hierarchical-tag-group > .opblock-tag .nostyle span {{
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
</style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="{swagger_js_url}"></script>
<script src="https://unpkg.com/swagger-ui-plugin-hierarchical-tags"></script>
<script>
const ui = SwaggerUIBundle({{
    url: '{openapi_url}',
{params_str}
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    plugins: [
        HierarchicalTagsPlugin
    ],
    hierarchicalTagSeparator: /\\s*>\\s*/,
}})
</script>
</body>
</html>"""

    return HTMLResponse(html)


@app.get("/")
def root():
    return {
        "name": "SINAGERSAT API",
        "version": "1.2.7",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
