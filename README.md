# SINAGERSAT — API REST v1.2.7

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. API con módulos EDAN, REA, geografía, usuarios, y sistema completo de permisos RBAC.

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
sudo bash deploy/desplegar_todo.sh --tunnel         # Todo + Cloudflare tunnel público
```

---

## Arquitectura

| Esquema | Descripción |
|---------|-------------|
| `shared` | Geografía INE 2024 (9 deptos, 112 provs, 340 munis con PostGIS) |
| `usuarios` | Cuentas, roles, sesiones, permisos RBAC, auditoría |
| `edan` | Formularios EDAN (23 tablas) |
| `rea` | Reportes de Eventos Adversos (4 tablas) |
| `rida`, `sinb`, `recursos` | Vacíos — futuros módulos |

**Total:** ~38 tablas, 35+ FK, 29+ índices, PostGIS habilitado.

---

## Conexión BD

| Parámetro | Valor |
|-----------|-------|
| Host | `localhost` o `127.0.0.1` |
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
| `docs/DESPLIEGUE_API.md` | Guía completa de despliegue, endpoints, auth, ejemplos |
| `docs/PERMISOS_API.md` | Sistema RBAC: roles, apps, acciones, matriz visual |
| `docs/EDAN_BD.md` | Documentación completa de la BD (esquemas, tablas, SQL) |
| `docs/GEOESPACIALES.md` | Endpoints GeoJSON/WKT/Ubicación + herramientas de mapas |
| `docs/SERVICIOS.md` | Gestión de servicios systemd (API + tunnel) |
| `docs/CONECTAR.md` | Credenciales y formas de conexión a la BD |
| `docs/CLOUDFLARE_TUNNEL.md` | Cloudflare Named Tunnel con dominio fijo |

---

## API REST

```bash
# Iniciar local
bash start_api.sh
# → http://localhost:8000/docs

# Con tunnel público
bash start_tunnel.sh
# → URL: grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Endpoints (~170 totales)

| Grupo | Prefijo | Acceso |
|-------|---------|--------|
| Auth | `/api/v1/auth/` | Público |
| Geografía | `/api/v1/shared/` | Público |
| EDAN | `/api/v1/edan/` | Token |
| REA | `/api/v1/rea/` | Token |
| Usuarios | `/api/v1/usuarios/` | Token |
| Upload | `/api/v1/upload/` | Token |

### Roles

| id | Rol | Token |
|----|-----|-------|
| 1 | superadmin | 72h con `exp` |
| 2 | admin | 72h con `exp` |
| 3 | VIDECI Regional | 72h con `exp` |
| 4 | UGR Sectores | 72h con `exp` |
| 5 | DGR Gobernacion | 72h con `exp` |
| 6 | UGR Municipio | **Eterno** (año 2099) |
| 7 | Responsable Local | **Eterno** (año 2099) |

El login devuelve `permisos`: `"full_access"` para rol 1, o `{app: [acciones]}` para los demás.

Ver `docs/PERMISOS_API.md` para más detalles.
