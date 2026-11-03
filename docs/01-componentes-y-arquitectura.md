# 01 · Componentes y arquitectura

> Verificado contra el repositorio en octubre de 2026. Referencias `archivo:línea` = código real.

## 1. Visión general

SINAGERSAT es una **API REST (FastAPI) + PostgreSQL/PostGIS** que sostiene cuatro dominios funcionales: **EDAN** (evaluación de daños y necesidades), **RIDA** (registro integral de daños/empadronamiento y ayuda), **SINB** (sistema de información biocultural con pronósticos) y **NDVI** (vigilancia satelital de vegetación), más servicios transversales (geografía, usuarios, repositorio documental, firma digital).

```
┌──────────────────────────────────────────────────────────────────────┐
│ CLIENTES (externos a este repositorio)                                │
│  · Web institucional  sat.climbat.net      (fuera del repo)           │
│  · App móvil Flutter  (fuera del repo, consume el sync offline)       │
│  · Navegador → Swagger /docs, /docs/v1, /docs/v2                      │
└───────────────┬──────────────────────────────────────────────────────┘
                │ HTTPS (Bearer JWT)      Apache reverse proxy (api.climbat.net)
┌───────────────▼──────────────────────────────────────────────────────┐
│ API FastAPI  api/main.py                                              │
│  /api/v1  (125 rutas)      /api/v2  (268 rutas)                       │
│  middleware: CORS + AuditMiddleware                                   │
│  módulos: auth · shared · usuarios · upload · repositorio ·           │
│           edan · firma_digital · rida · sinb · ndvi                   │
└───────────────┬──────────────────────────────────────────────────────┘
                │ SQLAlchemy Core (SQL crudo, sin ORM)
┌───────────────▼──────────────────────────────────────────────────────┐
│ PostgreSQL 16 + PostGIS                                               │
│  esquemas: shared · usuarios · edan · rida · sinb · repositorio · rea │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Componentes dentro del repositorio

### 2.1 Backend (`api/`)

| Componente | Fichero(s) | Función |
|---|---|---|
| Aplicación | `api/main.py` (367 l.) | App FastAPI v1.4.0, CORS, auditoría, montaje v1/v2, Swagger propio en `/docs` |
| Configuración | `api/config.py` | `pydantic-settings` + `.env` (`DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `UPLOAD_DIR`, `AGETIC_*`) |
| Conexión BD | `api/database.py` | Engine SQLAlchemy + `get_db()`; **sin modelos ORM** (todo SQL crudo) |
| Autenticación | `api/auth/` (`router.py`, `service.py`, `jwt.py`, `permisos.py`) | Login, registro, JWT HS256, bcrypt, RBAC |
| Dependencias | `api/dependencies.py` | `HTTPBearer` + `get_current_user()` (`:15`), valida token y que el usuario esté `activo` |
| Respuestas | `api/response.py` | Envoltorios `SuccessResponse` / `ErrorResponse` / `DataListResponse` / `DataItemResponse` |
| Auditoría | `api/audit.py` | `AuditMiddleware` (`main.py:113`): registra POST/PUT/DELETE con status <400 en `usuarios.auditoria` |
| Geografía y censo | `api/shared/` | Departamentos, provincias, municipios, GeoJSON/GEOM, censo 2024 (manzanos/comunidades), cultivos y pecuario |
| Usuarios y permisos | `api/usuarios/` | CRUD de usuarios, roles, aplicaciones, acciones, permisos, sesiones, auditoría, importación Excel |
| EDAN | `api/edan/` | Evaluación de daños: 5 routers (v1 + 4 v2), consolidación, aprobaciones, localidades por secciones, sync |
| **RIDA** | `api/rida/` | Empadronamiento, eventos, necesidades, solicitudes (workflow) |
| SINB | `api/sinb/` | Indicadores bioculturales, pronósticos, recomendaciones, NDVI |
| Repositorio | `api/repositorio/` | Documentos PDF: catálogo, subida, filtrado, descarga |
| Firma digital | `api/firma_digital/` | Proxy servidor→servidor contra AGETIC (evita el bloqueo CORS de `validar.firmadigital.bo`) |
| Uploads | `api/upload.py` | Subida de imágenes y helper `save_documento_pdf` |

**Patrón por módulo:** `router.py` (endpoints) + `service.py` (SQL crudo) + `schemas.py` (Pydantic) + `__init__.py`.

**Montaje de routers** (`api/main.py:67-119`): `V1_ROUTERS` y `V2_ROUTERS`, ambos prefijados con `/api/v1` y `/api/v2`. RIDA, SINB, NDVI y firma digital **solo existen en v2**.

### 2.2 Módulos RIDA (`api/rida/`)

| Router | Prefijo final | Fichero | Rutas |
|---|---|---|---|
| Empadronamiento | `/api/v2/rida/empadronamiento` | `rida/router.py` (640 l.) | 15 |
| Eventos | `/api/v2/rida/evento`, `/api/v2/rida/eventos`, `/api/v2/rida/edan-aprobados` | `rida/router_eventos.py` (211 l.) | 8 |
| Necesidades | `/api/v2/rida/necesidades` | `rida/necesidades/router.py` (700 l.) | 17 |
| Solicitudes | `/api/v2/rida/solicitudes` | `rida/solicitudes/router.py` (375 l.) | 19 |
| Ayuda Humanitaria | `/api/v2/ayuda-humanitaria` | `ayuda_humanitaria/router.py` (Work Queue pasos 4-9, motor secuencial + cálculo dinámico) | 20 |
| Documentos RIDA | `/api/v2/repositorio/rida/eventos/{id}/documentos` | `repositorio/router.py:256,343` | 1 |

Servicios: `rida/service.py` (1557 l.), `rida/geo_filters.py` (validación jerárquica de códigos INE), `rida/necesidades/service.py` (775 l.), `rida/solicitudes/service.py` (507 l.).

### 2.3 Base de datos

| Esquema | Tablas | Contenido |
|---|---|---|
| `shared` | 7 | `departamento` (9), `provincia` (113), `municipio` (343), `comunidades`, `manzanos`, cultivos, pecuario |
| `usuarios` | 7 | `usuario`, `rol`, `usuario_rol`, `aplicacion`, `accion`, `permiso`, `sesion`, `auditoria` |
| `edan` | 24 | `edan`, `edan_localidades`, 14 sub-tablas de secciones, catálogos, `aprobaciones_edan` |
| `rida` | **36** | Empadronamiento, eventos, necesidades, solicitudes y logística — ver [Documentacion-Base-Datos-RIDA.md](../Documentacion-Base-Datos-RIDA.md) |
| `sinb` | 36 | Indicadores bioculturales, pronósticos, NDVI, vistas |
| `repositorio` | 2 | `tipo_documento`, `documentos` |
| `rea` | 4 | Esquema residual; **sin router en la API** (solo se menciona en `api/audit.py:9,16`) |
| `public` | 3 | `spatial_ref_sys` (PostGIS) y auxiliares |

Geoespacial: PostGIS, `GEOMETRY(Polygon,4326)` en municipios y `geom` de proyectos.

### 2.4 Despliegue e infraestructura

| Elemento | Ruta | Notas |
|---|---|---|
| Despliegue completo | `deploy/desplegar_todo.sh` (588 l.) | 9 pasos; flags `--db-only`, `--api-only`, `--update` |
| Solo BD / verificación | `deploy/desplegar_bd.sh`, `deploy/verificar.sh` | Restaura backup + migraciones |
| Servicio systemd | `deploy/systemd/sinagersat-api.service` | `uvicorn api.main:app`, `EnvironmentFile=.env` |
| Arranque manual | `start_api.sh` / `stop.sh` | `uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| Configuración PG | `config/`, `deploy/config/` | `pg_hba.conf`, `postgresql.conf` |
| Proxy | Apache como reverse proxy TLS (`api.climbat.net`) | Configuración fuera del repo |
| Dependencias | `requirements.txt` (11 líneas) | fastapi, uvicorn, sqlalchemy, psycopg2, pydantic, python-jose, bcrypt, openpyxl, httpx |
| Crons / scripts | `scripts/` (16 ficheros) | Carga de municipios, censo 2024, importación Excel, ingesta NDVI, pronóstico digital |

## 3. Componentes externos al repositorio

> **Este repositorio no contiene código de interfaz.** No hay ficheros `.html`, `.js`, `.vue`, `.tsx`, `.dart`, `package.json` de producto, `manifest.json` ni service worker (verificado con `glob` y con el historial git completo: nunca existieron).

| Componente | Dónde vive | Relación con este repo |
|---|---|---|
| **Web institucional** | `sat.climbat.net` | Consume la API v2 |
| **App móvil Flutter** | Repositorio externo | Consume los endpoints de sincronización offline (cap. [03](03-offline-y-sincronizacion.md)) |
| **API pública** | `api.climbat.net` (Apache → uvicorn) | Este backend |
| **Firma digital AGETIC** | `validar.firmadigital.bo` | Consumida vía proxy en `api/firma_digital/` |
| **Datos meteorológicos** | Open-Meteo | Pronóstico digital SINB |
| **Imágenes satelitales** | EarthSearch STAC (Sentinel-2) | NDVI |
| **Propuesta de frontend** | `propuesta/06-FRONTEND.md`, `propuesta/02-COMPONENTES-VISUALES.md` | **Diseño, no implementado** (Vue 3 + PWA) |

El contrato que consumen estos clientes es la OpenAPI servida en `/openapi.v2.json`.

## 4. Cadena de solicitudes

1. El cliente envía `Authorization: Bearer <JWT>` (`api/dependencies.py:8`).
2. `get_current_user()` valida el token, consulta `usuarios.usuario` y exige `activo = true` (`api/dependencies.py:15-42`).
3. La dependencia de router `module_permiso("MODULO")` comprueba la acción (GET→READ, POST→CREATE, PUT→UPDATE, DELETE→DELETE) contra `usuarios.permiso` (`api/auth/permisos.py:7-34`).
4. `require_rol(...)` puede restringir además por rol concreto.
5. El handler aplica alcance geográfico (`scope_geografico` o filtros propios del módulo).
6. `AuditMiddleware` persiste la escritura realizada en `usuarios.auditoria`.

**Respuestas** siempre envueltas: `{"success": true/false, "message": "...", "data": ..., "total": n}` (`api/response.py`).

## 5. Versionado y migraciones

Hay **tres carpetas de migraciones** (histórico no reconciliado):

| Carpeta | Rango | Estado |
|---|---|---|
| `database/migration_v*.sql` | v1.2.0 → v2.8.0 (34 ficheros) | Legado, ya aplicados |
| `database/migrations/` | v2.9.0 → **v2.35.0** | **Vigente** |
| `migrations/` (raíz) | v1.3.3, v1.10.0 | Huérfana, sin documentar |

No hay Alembic: las migraciones son SQL plano e idempotente, aplicadas con `psql -f`.

**Últimas migraciones RIDA:**

| Versión | Cambio |
|---|---|
| v2.17.0 | Esquema RIDA completo (35 tablas) |
| v2.18.0 – v2.21.0 | Estructura de formulario, familia, integrante y `ubicacion_familia` |
| v2.22.0 | Documentos RIDA |
| v2.23.0 | Reestructuración de necesidades y artículos |
| v2.24.0 | `evento_rida` (padre) + `cat_estado_evento` |
| v2.33.0 | Se elimina `solicitud.codigo_expediente` |
| v2.34.0 | Motor de etapas: `cat_etapa_solicitud` + CHECK de 17 etapas |
| v2.35.0 | Separación Ayuda Humanitaria / Rehabilitación |
| v2.48.0 | `documentos.id_formulario_rida` → `id_evento_rida` |
| v2.55.0 | Ayuda Humanitaria: Work Queue VIDECI (motor secuencial, motor de cálculo, `entrega` orden/acta, rol 14) |
| v2.56.0 | `cat_unidad_medida` + FK desde `cat_articulo.unidad_de_medida` |
| v2.57.0 | Ayuda Humanitaria: motor de cálculo por **kits** (`regla_calculo_kit` + `detalle_parametro_kit`); se elimina `cat_regla_calculo` |

## 6. Estado de calidad

| Área | Estado |
|---|---|
| Tests automatizados | **No existen** (sin `tests/`, sin `pytest`) |
| Lint / typecheck | Sin configuración (ruff, black, mypy no presentes) |
| CI/CD | Solo `.github/workflows/opencode.yml` (disparador de agente); no ejecuta build ni tests |
| CHANGELOG / LICENSE / CONTRIBUTING | No existen |
| Rate limiting, refresh token, logout | No implementados |

## 7. Cómo explorar el sistema

```bash
bash start_api.sh                      # arranque
open http://localhost:8000/docs        # índice de documentación
curl http://localhost:8000/health      # {"status":"ok"}
curl http://localhost:8000/openapi.v2.json | python3 -m json.tool | less
```

---

**Siguiente:** [02 · Autenticación y roles](02-autenticacion-y-roles.md) · Índice: [README](README.md)
