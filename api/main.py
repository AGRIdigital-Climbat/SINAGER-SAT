import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .auth.router import router as auth_router
from .shared.router import router as shared_router
from .edan.router import router as edan_router
from .edan.router_v2 import router as edan_router_v2
from .edan.router_v2_edan import router as edan_router_v2_edan
from .edan.router_v2_localidades import router as edan_router_v2_localidades
from .edan.router_v2_catalogos import router as edan_router_v2_catalogos
from .rea.router import router as rea_router
from .usuarios.router import router as usuarios_router
from .upload import router as upload_router
from .repositorio.router import router as repositorio_router
from .audit import AuditMiddleware

TAGS_METADATA_V1 = [
    {"name": "Auth",                      "description": "Login y registro de usuarios (JWT)"},
    {"name": "Geografía > Departamentos", "description": "CRUD de los 9 departamentos"},
    {"name": "Geografía > Provincias",    "description": "CRUD de las 112 provincias"},
    {"name": "Geografía > Municipios",    "description": "CRUD de los 340 municipios"},
    {"name": "Geografía > GeoJSON",       "description": "Municipios en GeoJSON (RFC 7946) para mapas web"},
    {"name": "Geografía > GEOM/WKT",      "description": "Municipios con geometría en WKT"},
    {"name": "Geografía > Ubicación",     "description": "Identificar municipio por coordenadas"},
    {"name": "Catálogos > Cultivos",      "description": "Catálogo de cultivos agrícolas (SIIP) con filtros por grupo y nombre"},
    {"name": "Catálogos > Pecuaria",      "description": "Catálogo de especies pecuarias con filtros por grupo y nombre"},
    {"name": "EDAN",                      "description": "Cabecera EDAN: CRUD principal, reportes agregados, catálogos (tipo evento, estado, tipo localidad), sincronización offline-first, consolidar, fotos por municipio, cambio de estado."},
    {"name": "EDAN_LOCALIDADES",          "description": "Localidades del EDAN: CRUD anidado, sync móvil, mis-resumen/mis-reportes de huérfanas, cambio de estado, items de daños/servicios con foto y coordenadas (viales, infra pública, vivienda, agricultura, pecuario, salud, servicios básicos, unidades educativas)."},
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
    {"name": "Repositorio > Catálogo",    "description": "Tipos de documento PDF admitidos por el repositorio"},
    {"name": "Repositorio > Documentos",  "description": "Gestión de documentos PDF vinculados a EDAN: subir, listar, filtrar por metadata estructurada, buscar por nombre, descargar y eliminar."},
]

V1_ROUTERS = [
    ("auth", auth_router),
    ("shared", shared_router),
    ("edan", edan_router),
    ("rea", rea_router),
    ("usuarios", usuarios_router),
    ("upload", upload_router),
    ("repositorio", repositorio_router),
]

V2_ROUTERS = [
    ("auth", auth_router),
    ("shared", shared_router),
    ("usuarios", usuarios_router),
    ("upload", upload_router),
    ("repositorio", repositorio_router),
    ("edan_v2", edan_router_v2),
    ("edan_catalogos", edan_router_v2_catalogos),
    ("edan_cabecera", edan_router_v2_edan),
    ("edan_localidades", edan_router_v2_localidades),
]

app = FastAPI(
    title="SINAGERSAT API",
    description="API del Sistema Nacional de Alerta Temprana y Gestión de Riesgos.",
    version="1.4.0",
    docs_url=None,
    redoc_url=None,
    generate_unique_id=lambda route: f"{next(iter(route.methods))}-{route.path}",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

for _, router in V1_ROUTERS:
    app.include_router(router, prefix="/api/v1")

for _, router in V2_ROUTERS:
    app.include_router(router, prefix="/api/v2")

uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Error interno del servidor", "error_code": 500},
    )


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Error de validación en los datos enviados", "error_code": 422},
    )


@app.get("/debug/routes", include_in_schema=False)
async def debug_routes():
    all_routes = []
    v1 = []
    v2 = []
    for r in app.routes:
        p = getattr(r, "path", "N/A")
        m = getattr(r, "methods", set())
        t = getattr(r, "tags", [])
        all_routes.append({"path": p, "methods": list(m), "tags": t})
        if isinstance(p, str):
            if p.startswith("/api/v1"):
                v1.append(p)
            elif p.startswith("/api/v2"):
                v2.append(p)
    return {
        "total": len(all_routes),
        "v1_count": len(v1),
        "v2_count": len(v2),
        "v2_paths": v2[:15],
        "all_paths_sample": [r["path"] for r in all_routes[:20]]
    }


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_spec():
    from fastapi.openapi.utils import get_openapi
    return get_openapi(
        title="SINAGERSAT API",
        version="1.4.0",
        description="Todas las rutas (v1 + v2)",
        routes=app.routes,
    )


def _collect_tags(paths: dict) -> list[dict]:
    names = sorted({t for p in paths.values() for op in p.values() for t in op.get("tags", [])})
    return [{"name": name} for name in names]


@app.get("/openapi.v1.json", include_in_schema=False)
async def get_openapi_v1():
    full = await get_openapi_spec()
    v1_paths = {k: v for k, v in full.get("paths", {}).items() if "/api/v1/" in k}
    return {
        "openapi": "3.1.0",
        "info": {"title": "SINAGERSAT API v1", "version": "1.4.0", "description": "API v1 (legacy)"},
        "paths": v1_paths,
        "tags": _collect_tags(v1_paths),
        "components": full.get("components", {}),
        "security": full.get("security", []),
    }


@app.get("/openapi.v2.json", include_in_schema=False)
async def get_openapi_v2():
    full = await get_openapi_spec()
    v2_paths = {k: v for k, v in full.get("paths", {}).items() if "/api/v2/" in k}
    return {
        "openapi": "3.1.0",
        "info": {"title": "SINAGERSAT API v2", "version": "1.4.0", "description": "API v2 (EDAN por secciones + EDAN cabecera + auth/shared/upload)"},
        "paths": v2_paths,
        "tags": _collect_tags(v2_paths),
        "components": full.get("components", {}),
        "security": full.get("security", []),
    }


def _html_safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link type="text/css" rel="stylesheet" href="{swagger_css_url}">
<link rel="shortcut icon" href="{swagger_favicon_url}">
<title>{title}</title>
</head>
<body>
<div id="swagger-ui"></div>
<script src="{swagger_js_url}"></script>
<script>
const ui = SwaggerUIBundle({{
    url: '{openapi_url}',
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    filter: true,
    syntaxHighlight: {{theme: "monokai"}},
    docExpansion: "none",
    displayRequestDuration: true,
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
}})
</script>
</body>
</html>"""

SWAGGER_UI_V2_HTML = """<!DOCTYPE html>
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
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    filter: true,
    syntaxHighlight: {{theme: "monokai"}},
    docExpansion: "none",
    displayRequestDuration: true,
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


@app.get("/docs", include_in_schema=False)
async def docs_index():
    return HTMLResponse("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SINAGERSAT API - Documentación</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
h1 { color: #333; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 15px 0; }
.card h2 { margin-top: 0; color: #0066cc; }
.card a { display: inline-block; margin-top: 10px; padding: 8px 16px; background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
.card a:hover { background: #0055aa; }
.version { font-size: 0.9em; color: #666; }
</style>
</head>
<body>
<h1>SINAGERSAT API - Documentación</h1>
<p>Selecciona una versión:</p>
<div class="card">
<h2>API v2 <span class="version">(recomendada)</span></h2>
<p>EDAN Localidades por secciones (id_seccion) + EDAN cabecera (consolidar/desconsolidar) + auth/shared/upload/repositorio.</p>
<a href="/docs/v2">Ver documentación v2</a>
</div>
<div class="card">
<h2>API v1 <span class="version">(legacy)</span></h2>
<p>API original completa (sync monolítico, consolidar, reportes). Se mantiene por compatibilidad.</p>
<a href="/docs/v1">Ver documentación v1</a>
</div>
</body>
</html>""")


@app.get("/docs/v1", include_in_schema=False)
async def docs_v1():
    return HTMLResponse(
        SWAGGER_UI_HTML.format(
            title="SINAGERSAT API v1 - Documentación",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
            openapi_url="/openapi.v1.json",
        )
    )


@app.get("/docs/v2", include_in_schema=False)
async def docs_v2():
    return HTMLResponse(
        SWAGGER_UI_V2_HTML.format(
            title="SINAGERSAT API v2 - Documentación",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
            openapi_url="/openapi.v2.json",
        )
    )


@app.get("/")
def root():
    return {
        "name": "SINAGERSAT API",
        "version": "1.4.0",
        "docs": "/docs",
        "docs_v1": "/docs/v1",
        "docs_v2": "/docs/v2",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

