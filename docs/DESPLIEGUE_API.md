# SINAGERSAT API — Despliegue y Documentación

Guía completa de la API REST v1.2.7. Incluye despliegue, endpoints, autenticación, roles, permisos y ejemplos.

---

## 1. Despliegue Rápido

### Desde cero (entorno vacío)

```bash
cd SINAGER-SAT
sudo bash deploy/desplegar_todo.sh
```

Instala PostgreSQL + Python + BD completa + API.

### Solo API (si PostgreSQL ya está corriendo)

```bash
sudo bash deploy/desplegar_todo.sh --api-only
```

### Con acceso externo (Cloudflare Tunnel)

```bash
sudo bash deploy/desplegar_todo.sh --tunnel
```

### Actualizar desde versión anterior (preservar datos)

```bash
sudo bash deploy/desplegar_todo.sh --update
```

---

## 2. URLs de la API

### Local

| Servicio | URL |
|----------|-----|
| API Base | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Health Check | `http://localhost:8000/health` |

### Externa (desde internet)

Con Cloudflare Quick Tunnel (URL dinámica):

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Desde otra máquina en la red local

```bash
curl http://192.168.0.34:8000
```

---

## 3. Formato de Respuestas

### Respuesta exitosa (lista)

```json
{
  "success": true,
  "message": "Departamentos listados correctamente",
  "data": [ ... ],
  "total": 9
}
```

### Respuesta exitosa (objeto)

```json
{
  "success": true,
  "message": "Usuario obtenido correctamente",
  "data": { ... },
  "total": null
}
```

### Eliminación

```json
{
  "message": "Recurso eliminado correctamente"
}
```

### Error

```json
{
  "success": false,
  "message": "Error interno del servidor",
  "error_code": 500
}
```

### Objetos anidados

Todas las foreign keys incluyen el `id_*` original **y** un objeto anidado:

```json
{
  "id_departamento": 2,
  "departamento": { "id": 2, "codigo_ine": "02", "nombre": "La Paz" }
}
```

---

## 4. Estructura de Endpoints

La API tiene ~170 endpoints organizados en 6 módulos.

```
/api/v1/
├── auth/                      # Autenticación (PÚBLICO)
│   ├── POST /login                  # Login → token JWT + permisos
│   ├── POST /register               # Registrar usuario
│   ├── POST /verificar-identidad    # Verificar identidad por carnet
│   ├── POST /cambiar-contrasena     # Cambiar contraseña
│   └── GET  /mis-permisos           # 🔒 Permisos del usuario actual
│
├── shared/                    # Geografía (PÚBLICO)
│   ├── GET/POST /departamentos
│   ├── GET/PUT/DELETE /departamentos/{id}
│   ├── GET/POST /provincias
│   ├── GET/PUT/DELETE /provincias/{id}
│   ├── GET/POST /municipios
│   ├── GET/PUT/DELETE /municipios/{id}
│   ├── GET /municipios/geojson       # GeoJSON (RFC 7946)
│   ├── GET /municipios/{id}/geojson
│   ├── GET /municipios/geom          # WKT
│   ├── GET /municipios/{id}/geom
│   └── GET /municipios/ubicacion     # Punto-dentro-de-polígono
│
├── edan/                      # Formularios EDAN (🔒 token)
│   ├── GET/POST /
│   ├── POST /con-foto
│   ├── GET/PUT/DELETE /{id}
│   ├── GET /{id}/...                # 17 sub-tablas anidadas
│   ├── GET /tipo-evento             # Catálogos
│   ├── GET /grupo-etario
│   ├── GET /servicio-basico
│   ├── GET /categoria-proteccion
│   └── GET /ayuda-humanitaria
│
├── rea/                       # Reportes de Eventos (🔒 token)
│   ├── GET/POST /reportes
│   ├── POST /reportes/con-foto
│   ├── GET/PUT/DELETE /reportes/{id}
│   ├── PUT /reportes/{id}/estado    # Cambiar estado (con reglas por rol)
│   ├── GET /reportes/mis-resumen
│   ├── GET /reportes/mis-reportes
│   ├── GET/POST /estados
│   ├── GET/PUT/DELETE /estados/{id}
│   ├── GET/POST /categorias
│   └── GET/PUT/DELETE /categorias/{id}
│
├── usuarios/                  # Gestión de usuarios (🔒 token)
│   ├── GET/POST /
│   ├── GET/PUT/DELETE /{id}
│   ├── GET/POST /roles
│   ├── GET/PUT/DELETE /roles/{id}
│   ├── PUT /roles/{id}/permisos     # Batch: reemplaza todos los permisos
│   ├── GET/POST /aplicaciones
│   ├── GET/PUT/DELETE /aplicaciones/{id}
│   ├── GET /permisos                # Lista plana de permisos
│   ├── GET /permisos/estructura     # Matriz completa (roles×apps×acciones)
│   ├── GET /permisos/rol/{id}       # Permisos agrupados de un rol
│   ├── POST/DELETE /permisos/{rol}/{app}/{accion}
│   ├── GET /acciones
│   ├── GET /sesiones
│   └── GET /auditoria
│
└── upload/                    # Archivos (🔒 token)
    ├── POST /                       # Subir imagen
    └── GET /descargar/{path}        # Descargar imagen
```

---

## 5. Autenticación y Roles

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'
```

Respuesta incluye `permisos`:

```json
{
  "success": true,
  "message": "Login exitoso",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user_id": 1,
    "usuario": "sinagersat",
    "nombre": "sinagersat",
    "id_rol": 1,
    "rol": "superadmin",
    "celular": "...",
    "departamento": { ... },
    "provincia": { ... },
    "municipio": { ... },
    "activo": true,
    "permisos": "full_access"
  }
}
```

Para rol 1 → `"full_access"` (string).  
Para otros roles → `{"EDAN": ["CREATE","READ","UPDATE"], "REA": [...]}`

### Obtener permisos del usuario actual

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/auth/mis-permisos
```

### Roles del Sistema

| id | Rol | Token expira | Ownership forzado |
|----|-----|-------------|-------------------|
| 1 | superadmin | 72h | ❌ |
| 2 | admin | 72h | ❌ |
| 3 | VIDECI Regional | 72h | ❌ |
| 4 | UGR Sectores | 72h | ❌ |
| 5 | DGR Gobernacion | 72h | ❌ |
| 6 | UGR Municipio | **Nunca** (2099) | ✅ Solo EDAN/REA propios |
| 7 | Responsable Local | **Nunca** (2099) | ✅ Solo EDAN/REA propios |

### Regla especial: PUT /rea/reportes/{id}/estado

- **Roles 1-5**: sin restricción — pueden cambiar estado de cualquier reporte.
- **Rol 7**: solo puede cambiar estado de sus propios reportes.
- **Rol 6**: puede cambiar estado de reportes **de rol 7** exclusivamente, **solo si pertenecen al mismo municipio** del UGR.

### Usar el token

```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer $TOKEN"
```

Desde Swagger UI: click **Authorize** → pegar token.

---

## 6. Migraciones de Base de Datos

### Migración v1.2.7

No requiere cambios en esquema de BD. Solo cambios en lógica de API:

- `PUT /rea/reportes/{id}/estado`: rol 6 puede cambiar estado de reportes de rol 7 en su mismo municipio
- `GET /auth/mis-permisos`: bugfix (500 error corregido)
- `get_current_user` ahora incluye `id_municipio`

### Historial de migraciones

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 \
  -f database/migration_v1.2.0.sql \
  -f database/migration_v1.2.1.sql \
  -f database/migration_v1.2.3.sql \
  -f database/migration_v1.2.5_permisos.sql
```

---

## 7. Ejemplos de Uso

### Login y obtener token

```bash
RESP=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}')
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
```

### Crear reporte REA

```bash
curl -X POST http://localhost:8000/api/v1/rea/reportes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_usuario": 1,
    "id_departamento": 2,
    "id_provincia": 201,
    "id_municipio": 20101,
    "comunidad": "Villa Fátima",
    "fecha_evento": "2026-07-15",
    "id_tipo_evento": 1,
    "id_estado": 1
  }'
```

### Crear reporte REA con foto

```bash
curl -X POST http://localhost:8000/api/v1/rea/reportes/con-foto \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@foto.jpg" \
  -F "id_usuario=1" \
  -F "id_departamento=2" \
  -F "id_provincia=201" \
  -F "id_municipio=20101" \
  -F "comunidad=Villa Fátima" \
  -F "fecha_evento=2026-07-15" \
  -F "id_tipo_evento=1"
```

### Cambiar estado de un reporte (rol 6 a reporte de rol 7 en mismo municipio)

```bash
curl -X PUT http://localhost:8000/api/v1/rea/reportes/5/estado \
  -H "Authorization: Bearer $TOKEN6" \
  -H "Content-Type: application/json" \
  -d '{"id_estado": 2}'
```

### Crear formulario EDAN

```bash
curl -X POST http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_edan": "EDAN-2026-001",
    "id_departamento": 2,
    "id_municipio": 20101,
    "nombre_alcalde": "Juan Perez",
    "telefono_alcalde": "70000000",
    "fecha_llenado": "2026-07-18",
    "fecha_evento": "2026-07-15"
  }'
```

### Consultar geografía

```bash
# Departamentos
curl http://localhost:8000/api/v1/shared/departamentos

# Municipios como GeoJSON (para mapas)
curl http://localhost:8000/api/v1/shared/municipios/geojson

# ¿En qué municipio está una coordenada GPS?
curl "http://localhost:8000/api/v1/shared/municipios/ubicacion?lat=-16.4897&lon=-68.1193"
```

---

## 8. Configuración

### Variables de entorno (.env)

```bash
DATABASE_URL=postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat
JWT_SECRET=tu-secreto-seguro-aqui
JWT_ALGORITHM=HS256
```

### Cambiar puerto

```bash
# Editar start_api.sh
uvicorn api.main:app --host 0.0.0.0 --port 9000 --reload
```

---

## 9. Acceso Externo (desde internet)

Tres opciones:

### A) Cloudflare Quick Tunnel (recomendado, sin configuración)

```bash
bash start_tunnel.sh
# URL: grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### B) URL Fija con Cloudflare (producción)

Requiere dominio. Ver `docs/CLOUDFLARE_TUNNEL.md`.

### C) Port Forwarding

```bash
# Router → Puerto 8000 → IP local 192.168.0.34
curl http://181.188.161.73:8000/
```

---

## 10. Troubleshooting

```bash
# Logs de la API
journalctl -u sinagersat-api -f

# Verificar BD
pg_isready

# Probar conexión
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1

# Obtener URL del tunnel
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1

# Verificar uploads
ls -la uploads/reports/
```

---

## 11. Archivos

```
SINAGER-SAT/
├── api/                     # Código fuente FastAPI
│   ├── main.py              # v1.2.7 — Entry point + Swagger custom
│   ├── config.py            # Config (.env)
│   ├── database.py          # SQLAlchemy connection
│   ├── dependencies.py      # JWT auth (incluye id_municipio)
│   ├── response.py          # SuccessResponse / ErrorResponse
│   ├── upload.py            # Subir/descargar archivos
│   ├── audit.py             # Middleware de auditoría
│   ├── auth/                # Login, register, permisos
│   ├── shared/              # Geografía + geoespaciales
│   ├── edan/                # Formularios EDAN
│   ├── rea/                 # Reportes REA (con reglas por rol)
│   └── usuarios/            # Cuentas, roles, permisos RBAC, sesiones
├── .env                     # Variables de entorno
├── requirements.txt         # Dependencias Python
├── start_api.sh             # Iniciar API local
├── start_tunnel.sh          # Iniciar API + tunnel
├── stop.sh                  # Detener todo
├── database/
│   ├── backup_v1.2.7.sql    # Backup completo (Jul 2026)
│   ├── migration_v1.2.0.sql
│   ├── migration_v1.2.1.sql
│   ├── migration_v1.2.3.sql
│   ├── migration_v1.2.5_permisos.sql
│   └── servers.json         # Config pgAdmin4
├── deploy/
│   ├── desplegar_todo.sh    # Despliegue completo
│   ├── desplegar_bd.sh      # Solo BD
│   ├── instalar_postgresql.sh
│   ├── verificar.sh
│   └── systemd/             # Servicios systemd
├── uploads/                 # Imágenes (fotos de reportes)
└── docs/
    ├── DESPLIEGUE_API.md    # Este documento
    ├── PERMISOS_API.md      # Sistema RBAC completo
    ├── EDAN_BD.md           # Documentación BD
    ├── GEOESPACIALES.md     # GeoJSON/WKT/Ubicación
    ├── SERVICIOS.md         # Gestión systemd
    ├── CONECTAR.md          # Credenciales BD
    └── CLOUDFLARE_TUNNEL.md # Tunnel con dominio fijo
```
