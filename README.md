# SINAGERSAT — API REST v1.4.0

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. API REST con módulos completos: **EDAN** (evaluación de daños), **RIDA** (registro de damnificados), **SINB** (sistema nacional de indicadores bioculturales), **NDVI** (monitoreo satelital de vegetación), **REA** (reportes de eventos), Repositorio documental, geografía INE 2024, usuarios y permisos RBAC.

---

## Despliegue rápido (entorno vacío)

```bash
sudo bash deploy/desplegar_todo.sh
```

Instala PostgreSQL, Python, crea la BD completa con todos los datos, configura la API y la inicia.

**Opciones:**

```bash
sudo bash deploy/desplegar_todo.sh                  # Todo (BD + API)
sudo bash deploy/desplegar_todo.sh --db-only        # Solo base de datos
sudo bash deploy/desplegar_todo.sh --api-only       # Solo API (si PG ya está)
```

**Con Apache + Dominio HTTPS (producción):**  
Ver [`docs/APACHE_PROXY.md`](docs/APACHE_PROXY.md) — instrucciones para entregar al proveedor de hosting.

---

## Arquitectura

| Esquema | Descripción | Estado |
|---------|-------------|--------|
| `shared` | Geografía INE 2024 (9 deptos, 112 provs, 340 munis, ~18k comunidades con PostGIS), catálogos cultivo/pecuario | ✅ Producción |
| `usuarios` | Cuentas, roles, sesiones, permisos RBAC, auditoría | ✅ Producción |
| `edan` | Formularios EDAN (23 tablas: cabecera + 14 sub-tablas + catálogos + aprobaciones) | ✅ Producción |
| `rea` | Reportes de Eventos Adversos (4 tablas) | ✅ Producción |
| `repositorio` | Repositorio de documentos PDF vinculados a EDAN (2 tablas) | ✅ Producción |
| `rida` | Registro de Damnificados (15 tablas: familia, integrante, ubicación, necesidades, documentos) | ✅ Producción |
| `sinb` | Sistema Nacional de Indicadores Bioculturales (39 tablas + 6 vistas: catálogos, observaciones, predicciones, galería, NDVI) | ✅ Producción |
| `recursos` | Vacío — futuro módulo | ⏳ Pendiente |

**Total:** ~100 tablas, 150+ FK, 200+ índices, PostGIS habilitado.

### Módulos Principales (v1.4.0)

#### 1. **EDAN** - Evaluación de Daños y Análisis de Necesidades
- **Cabecera**: Registro de eventos, consolidación, aprobación
- **Localidades**: Daños en vivienda, infraestructura, servicios, sectores productivos
- **Aprobaciones**: Flujo de trabajo UGR → Gobernación → VIDECI
- **Fotos georreferenciadas**: Evidencias por ítem
- **Offline-first**: Sincronización móvil con IDs offline

#### 2. **RIDA** - Registro de Damnificados
- **Empadronamiento**: Familias damnificadas con ubicación GPS
- **Integrantes**: Datos demográficos, vulnerabilidades
- **Necesidades**: Albergue, alimentación, salud, articulación institucional
- **Documentos**: Fotos, firmas digitales, validación
- **Artículos**: Gestión de ayuda humanitaria

#### 3. **SINB** - Sistema Nacional de Indicadores Bioculturales
- **Catálogos bioculturales**: Grupos, indicadores, características, comportamientos, significados
- **Observaciones de campo**: Registro de bioindicadores (floración, comportamiento animal)
- **Predicciones**: Estacionales (largo plazo), temporales (corto plazo), avisos inmediatos (24-48h)
- **Validación**: Verificación de cumplimiento de predicciones
- **Galería colaborativa**: Fotos/audio de bioindicadores (múltiples usuarios por indicador)
- **Pronósticos digitales**: Open-Meteo API (diario, hourly, minutely)

#### 4. **NDVI Satelital** - Monitoreo de Vegetación
- **Sentinel-2**: EarthSearch STAC API (sin API key)
- **Series temporales**: NDVI por comunidad desde 2021
- **Alertas de sequía**: Detección automática (umbrales y anomalías)
- **GeoJSON**: Mapas de calor para frontend (Leaflet, Mapbox)
- **Histórico permanente**: Datos no se borran, valor científico crece

### Grupos Swagger (v1.4.0)

Los endpoints se agrupan en **30+ categorías colapsables** en `/docs/v2`:

**EDAN:**
- `EDAN` — cabecera, reportes, catálogos, consolidar, sincronización
- `EDAN_LOCALIDADES` — localidades, items con foto, sync
- `EDAN_APROBACIONES` — flujo de aprobaciones, devoluciones

**RIDA:**
- `RIDA > Empadronamiento` — familias, integrantes, ubicación
- `RIDA > Necesidades` — albergue, alimentación, salud
- `RIDA > Artículos` — gestión de ayuda humanitaria
- `RIDA > Documentos` — fotos, firmas digitales

**SINB:**
- `SINB > Catálogos Bioculturales` — grupo, indicador, característica, comportamiento, significado
- `SINB > Observaciones` — CRUD con registros, filtros geográficos
- `SINB > Predicciones > Largo Plazo` — estacionales, escenarios
- `SINB > Predicciones > Corto Plazo` — temporales, categorías
- `SINB > Predicciones > Avisos` — alertas 24-48h
- `SINB > Predicciones > Pronósticos Digitales` — Open-Meteo API
- `SINB > Galería de Evidencias` — fotos/audio colaborativo
- `SINB > NDVI Satelital` — series temporales, alertas, GeoJSON

**Otros:**
- `Auth`, `Geografía > *`, `Censo 2024 > *`, `REA > *`, `Usuarios > *`, `Upload`, `Repositorio > *`

---

## Conexión BD

| Parámetro | Valor |
|-----------|-------|
| Host | `localhost`, `127.0.0.1` o `10.10.0.24` |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

---

## Documentación

### Documentación General
| Archivo | Contenido |
|---------|-----------|
| `docs/DESPLIEGUE_API.md` | Guía completa de despliegue, endpoints, auth, ejemplos |
| `docs/PERMISOS_API.md` | Sistema RBAC: roles, apps, acciones, matriz visual |
| `docs/GEOESPACIALES.md` | Endpoints GeoJSON/WKT/Ubicación + herramientas de mapas |
| `docs/SERVICIOS.md` | Gestión de servicios systemd de la API |
| `docs/CONECTAR.md` | Credenciales y formas de conexión a la BD |

### Documentación EDAN
| Archivo | Contenido |
|---------|-----------|
| `docs/EDAN_BD.md` | Documentación completa de la BD EDAN (esquemas, tablas, SQL) |
| `docs/EDAN_V2.md` | API EDAN v2 por secciones (id_seccion) |
| `docs/EDAN_LOCALIDADES_V2.md` | Localidades EDAN: items con foto, sync |
| `docs/APROBACIONES_EDAN.md` | Flujo de aprobaciones, estados, transiciones |
| `docs/CONSOLIDACION_EDAN.md` | Proceso de consolidación de EDAN |
| `docs/SINCRONIZACION.md` | Sincronización offline-first móvil |
| `docs/SINCRONIZACION_SECCIONES_FOTOS.md` | Sync de secciones y fotos georreferenciadas |
| `docs/FLUJO_EDAN_UGR.md` | Flujo de trabajo UGR Municipio |

### Documentación RIDA
| Archivo | Contenido |
|---------|-----------|
| `docs/RIDA_BD.md` | Base de datos RIDA completa (esquemas, tablas, relaciones) |
| `docs/RIDA_API.md` | API RIDA: empadronamiento, familias, integrantes |
| `docs/RIDA_EMPRADRONAMIENTO_API.md` | Endpoints de empadronamiento |
| `docs/RIDA_FLUJO_GENERAL.md` | Flujo general del módulo RIDA |
| `Estructura_RIDA.md` | Estructura completa de tablas RIDA |
| `Empadronamiento.md` | Proceso de empadronamiento de familias |
| `RehabilitacionReconstruccion.md` | Módulo de rehabilitación y reconstrucción |

### Documentación SINB
| Archivo | Contenido |
|---------|-----------|
| `propuesta/08-SINB-BASE-DE-DATOS.md` | Base de datos SINB: catálogos, observaciones, predicciones |
| `propuesta/09-SINB-NDVI-SATELITAL.md` | **NDVI Satelital**: Sentinel-2, EarthSearch, series temporales, alertas |
| `propuesta/10-SINB-NDVI-CRON.md` | Configuración de tarea CRON para ingesta diaria de NDVI |
| `propuesta/07-FLUJOS-BIOCULTURALES.md` | Flujos bioculturales del SINB |

### Documentación de Infraestructura
| Archivo | Contenido |
|---------|-----------|
| `docs/APACHE_PROXY.md` | Apache reverse proxy para producción |
| `docs/DOMINIO_API.md` | Dominio personalizado (api.climbat.net) |
| `docs/ENDPOINTS_PROTECCION.md` | Protección de endpoints sensibles |
| `docs/IMPORTACION_HISTORICO_BD_EDAN.md` | Importación de histórico EDAN 2002-2025 |

### Propuesta Técnica
| Archivo | Contenido |
|---------|-----------|
| `propuesta/01-ARQUITECTURA.md` | Arquitectura general del sistema |
| `propuesta/02-COMPONENTES-VISUALES.md` | Componentes frontend |
| `propuesta/03-BACKEND.md` | Backend y APIs |
| `propuesta/04-BASE-DE-DATOS.md` | **Base de datos completa** (135KB, 3800+ líneas) |
| `propuesta/05-APIS.md` | **APIs completas** (46KB, 1000+ líneas) |
| `propuesta/06-FRONTEND.md` | Frontend y componentes |
| `propuesta/10-INTEROPERABILIDAD.md` | Interoperabilidad: EarthSearch, Open-Meteo, CHIRPS |

---

## API REST

```bash
# Iniciar local
bash start_api.sh
# → http://localhost:8000/docs

# APIs versionadas
# http://localhost:8000/docs/v1  → Legacy (EDAN monolítico)
# http://localhost:8000/docs/v2  → Actual (EDAN por secciones + RIDA + SINB)

# Con Apache proxy (producción)
# Ver docs/APACHE_PROXY.md

# Con dominio api.climbat.net
# Ver docs/DOMINIO_API.md
```

### Endpoints (500+ totales)

| Módulo | Versión | Prefijo | Acceso | Endpoints |
|--------|---------|---------|--------|-----------|
| Auth | v1, v2 | `/api/v1/auth/`, `/api/v2/auth/` | Público | 6 |
| Geografía | v1, v2 | `/api/v1/shared/`, `/api/v2/shared/` | Público | 30+ |
| Censo 2024 | v2 | `/api/v2/shared/` | Público | 15+ |
| EDAN | v1 | `/api/v1/edan/` | Token | 36 |
| EDAN v2 | v2 | `/api/v2/edan/` | Token | 100+ |
| RIDA | v2 | `/api/v2/rida/` | Token | 50+ |
| SINB | v2 | `/api/v2/sinb/` | Token | 80+ |
| NDVI | v2 | `/api/v2/ndvi/` | Token | 11 |
| REA | v1 | `/api/v1/rea/` | Token | 12 |
| Repositorio | v1, v2 | `/api/v1/repositorio/`, `/api/v2/repositorio/` | Token | 15+ |
| Usuarios | v1, v2 | `/api/v1/usuarios/`, `/api/v2/usuarios/` | Token | 40+ |
| Upload | v1, v2 | `/api/v1/upload/`, `/api/v2/upload/` | Token | 5 |
| Firma Digital | v2 | `/api/v2/firma-digital/` | Token | 4 |

### Roles y permisos (v1.4.0)

#### Roles EDAN
| id | Rol | EDAN | Localidades | Estado EDAN | Token |
|----|-----|-------|-------------|-------------|-------|
| 1 | superadmin | ✅ CRUD | ✅ | ✅ | 72h |
| 2 | admin | ❌ | ❌ | ✅ | 72h |
| 3 | VIDECI Regional | ❌ | ❌ | ✅ | 72h |
| 4 | UGR Sectores | ❌ | ❌ | ✅ | 72h |
| 5 | DGR Gobernación | ❌ | ❌ | ✅ | 72h |
| **6** | **UGR Municipio** | **✅ CRUD** | **✅ CRUD** | **❌** | **Eterno** |
| **7** | **Responsable Local** | **❌** | **✅ CRUD** | **❌** | **Eterno** |
| 8 | Alcalde | ❌ | ❌ | ❌ | Eterno |
| 9 | VIDECI Departamental | ❌ | ❌ | ✅ | 72h |

#### Roles SINB
| id | Rol | Descripcion | Observaciones | Predicciones | Validacion |
|----|-----|-------------|---------------|--------------|------------|
| 2 | admin | Administrador SINB | ✅ CRUD | ✅ CRUD | ✅ |
| 6 | UGR Municipio | Gestor municipal | ✅ Ver/Crear | ✅ Ver/Crear | ❌ |
| 12 | Usuario recolector | Observador de campo | ✅ Ver/Crear | ❌ | ❌ |
| 13 | Observador local | Conocimiento ancestral | ✅ Ver | ❌ | ❌ |

El login devuelve `permisos`: `"full_access"` para rol 1, o `{app: [acciones]}` para los demás.

Ver `docs/PERMISOS_API.md` para más detalles.

---

## Migraciones de Base de Datos

Las migraciones están en `database/migrations/` y se numeran por versión:

```
v2.9.0  → id_seccion en EDAN
v2.13.0 → tipo_evento catálogo
v2.15.0 → Censo 2024 (shared)
v2.17.x → RIDA completo (15 tablas)
v2.26.0 → SINB IDs offline
v2.27.0 → SINB Pronósticos Digitales (Open-Meteo)
v2.28.0 → SINB NDVI Satelital (Sentinel-2)
```

Para ejecutar una migración:
```bash
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat \
  -f database/migrations/v2.28.0_ndvi_satelital.sql
```

---

## Scripts de Utilidad

| Script | Descripción |
|--------|-------------|
| `scripts/importar_bdlimpia.py` | Importar datos desde Excel BD Limpia |
| `scripts/cargar_censo2024_shared.py` | Cargar Censo 2024 al esquema shared |
| `scripts/cron_ndvi_ingest.py` | Ingesta diaria de NDVI (CRON 06:00) |

---

## Estado del Proyecto (v1.4.0)

### ✅ En Producción
- **EDAN completo**: Cabecera + Localidades + Aprobaciones + Sync
- **RIDA completo**: Empadronamiento + Familias + Integrantes + Necesidades + Artículos
- **SINB completo**: Catálogos + Observaciones + Predicciones + Galería + Pronósticos Digitales
- **NDVI Satelital**: EarthSearch + Series temporales + Alertas + GeoJSON
- **Geografía INE 2024**: 9 deptos, 112 provs, 340 munis, ~18k comunidades
- **Usuarios y RBAC**: 15 roles, permisos por app/acción, auditoría
- **Repositorio documental**: PDFs vinculados a EDAN con metadatos

### ⏳ Pendientes
- Módulo `recursos` (vacío)
- Integración con SENAMHI (convenio requerido)
- Frontend web (React/Vue) para mapas de calor NDVI
- Dashboard de alertas tempranas

---

## Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| Base de datos | PostgreSQL 16 + PostGIS |
| Autenticación | JWT (HS256), refresh tokens rotativos |
| Geoespacial | PostGIS, GeoJSON, WKT |
| APIs | REST, OpenAPI 3.1 (Swagger) |
| Offline | IDs offline (UUIDv4), sincronización bidireccional |
| Satelital | EarthSearch STAC, Sentinel-2 L2A |
| Meteorológico | Open-Meteo API (sin API key) |

---

## Versiones

- **v1.3.0**: EDAN + REA + Repositorio + Geografía + Usuarios
- **v1.4.0**: + RIDA completo + SINB completo + NDVI Satelital (actual)
- **v1.5.0** (pendiente): Recursos + Dashboard + Frontend web

---

**Última actualización:** 2026-10-03  
**Repositorio:** https://github.com/AGRIdigital-Climbat/SINAGER-SAT  
**Rama:** `v1.4.0`
