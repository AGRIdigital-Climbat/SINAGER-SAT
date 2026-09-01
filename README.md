# SINAGERSAT — API REST v1.4.0

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. API con módulos EDAN (jerárquico por localidades con geolocalización), REA, Repositorio de documentos PDF, geografía, usuarios, y sistema completo de permisos RBAC. Dos versiones de API: v1 (legacy) y v2 (sync incremental por secciones).

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

| Esquema | Descripción |
|---------|-------------|
| `shared` | Geografía INE 2024 (9 deptos, 112 provs, 340 munis con PostGIS, catálogos cultivo/pecuario) |
| `usuarios` | Cuentas, roles, sesiones, permisos RBAC, auditoría |
| `edan` | Formularios EDAN (23 tablas: cabecera + 14 sub-tablas + catálogos) |
| `rea` | Reportes de Eventos Adversos (4 tablas) |
| `repositorio` | Repositorio de documentos PDF vinculados a EDAN (2 tablas) |
| `rida`, `sinb`, `recursos` | Vacíos — futuros módulos |

**Total:** ~50 tablas, 50+ FK, 60+ índices, PostGIS habilitado.

### Grupos Swagger (v1.4.0)

Los endpoints se agrupan en **20+ categorías colapsables** en `/docs`:

- **API v1** (`/docs/v1`) — 163 endpoints legacy
- **API v2** (`/docs/v2`) — sync incremental por secciones con UPSERT por `id_seccion`
- `EDAN` — cabecera, reportes, catálogos, consolidar, sincronización (36 endpoints)
- `EDAN_LOCALIDADES` — localidades, mis-*, sync, items con foto (28+ endpoints)
- `Repositorio > Catálogo` — tipos de documento PDF (5 endpoints)
- `Repositorio > Documentos` — subir, listar, filtrar, buscar, descargar (9 endpoints)
- `Auth`, `Geografía > *`, `REA > *`, `Usuarios > *`, `Upload`

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

| Archivo | Contenido |
|---------|-----------|
| `docs/DESPLIEGUE_API.md` | Guía completa de despliegue, endpoints, auth, ejemplos (v1) |
| `docs/DESPLIEGUE_API_V2.md` | Guía completa de la API v2 (sync por secciones) |
| `docs/EDAN_LOCALIDADES_V2.md` | Documentación técnica de localidades V2 |
| `docs/PERMISOS_API.md` | Sistema RBAC: roles, apps, acciones, matriz visual |
| `docs/EDAN_BD.md` | Documentación completa de la BD (esquemas, tablas, SQL) |
| `docs/GEOESPACIALES.md` | Endpoints GeoJSON/WKT/Ubicación + herramientas de mapas |
| `docs/SERVICIOS.md` | Gestión de servicios systemd de la API |
| `docs/CONECTAR.md` | Credenciales y formas de conexión a la BD |
| `docs/CLOUDFLARE_TUNNEL.md` | Cloudflare Named Tunnel con dominio fijo |
| `docs/DOMINIO_API.md` | Despliegue con dominio api.climbat.net (Apache + SSL) |

---

## API REST

```bash
# Iniciar local
bash start_api.sh
# → http://localhost:8000/docs        (selección v1/v2)
# → http://localhost:8000/docs/v1     (Swagger v1)
# → http://localhost:8000/docs/v2     (Swagger v2 - recomendada)

# Con Apache proxy (producción)
# Ver docs/APACHE_PROXY.md

# Con dominio api.climbat.net
# Ver docs/DOMINIO_API.md
```

### Endpoints (170+ totales en v1 + v2)

| Grupo | Prefijo v1 | Prefijo v2 | Acceso |
|-------|-----------|-----------|--------|
| Auth | `/api/v1/auth/` | `/api/v2/auth/` | Público |
| Geografía | `/api/v1/shared/` | `/api/v2/shared/` | Público |
| EDAN | `/api/v1/edan/` | `/api/v2/edan/` | Token |
| EDAN_LOCALIDADES | `/api/v1/edan/localidades/*` | `/api/v2/edan/localidades/*` | Token |
| REA | `/api/v1/rea/` | — | Token |
| Repositorio | `/api/v1/repositorio/` | `/api/v2/repositorio/` | Token |
| Usuarios | `/api/v1/usuarios/` | `/api/v2/usuarios/` | Token |
| Upload | `/api/v1/upload/` | `/api/v2/upload/` | Token |

### Roles y permisos (v1.4.0)

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

El login devuelve `permisos`: `"full_access"` para rol 1, o `{app: [acciones]}` para los demás.

Ver `docs/PERMISOS_API.md` para más detalles.
