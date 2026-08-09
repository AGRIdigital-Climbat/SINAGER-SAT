# SINAGERSAT API — Despliegue y Documentación

Guía completa de la API REST v1.2.8. Incluye despliegue, endpoints, autenticación, roles, permisos y ejemplos.

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

### Por dominio (producción)

| Servicio | URL |
|----------|-----|
| API Base | `https://api.climbat.net` |
| Swagger UI | `https://api.climbat.net/docs` |
| ReDoc | `https://api.climbat.net/redoc` |
| Health Check | `https://api.climbat.net/health` |

### Por IP del servidor

```bash
curl http://10.10.0.24:8000
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
│   ├── GET /ayuda-humanitaria
│   ├── POST /sync                   # Push offline (EdanSyncIn) — móvil→servidor
│   ├── GET /sync/pull               # Pull incremental — servidor→dispositivo
│   ├── GET /reportes/mis-resumen    # Resumen de EDANs propios
│   └── GET /reportes/mis-reportes   # EDANs propios completos, paginados
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
│   # Todos los GET de reportes incluyen:
│   #  • "categorias": [ {id_categoria, nombre, descripcion, orden}, ... ]
│   #  • "usuario":    perfil completo del que registró (con rol y geografía anidados)
│
├── usuarios/                  # Gestión de usuarios (🔒 token)
│   ├── GET/POST /
│   │     # GET / soporta filtros (a lo sumo uno de geografía, + opcional id_rol):
│   │     #   ?id_departamento=2 | ?id_provincia=201 | ?id_municipio=20101 | ?id_rol=7
│   │     #   combos válidos: geografía + id_rol (ej. ?id_municipio=20101&id_rol=7)
│   ├── GET/PUT/DELETE /{id}    # ✏️ GET/PUT de tu propio id = "mi perfil" (PUT sin contraseña)
│   ├── PUT /{id}/cuenta        # 🔒 Solo admin: contraseña, rol, estado (SISTEMA UPDATE)
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

## 5. Edición de perfil (auto-edición)

Cualquier usuario autenticado puede ver y editar **su propio perfil** sin permiso del
módulo SISTEMA usando `GET` / `PUT /api/v1/usuarios/{id}` con su propio `id`
(el id se obtiene del token, o de `GET /api/v1/auth/mis-permisos`).

Campos editables en auto-edición (incluye toda la geografía):

```json
{
  "nombre": "Luis Quenta",
  "celular": "76543210",
  "carnet": "7051296",
  "comunidad": "Challapata",
  "correo": "luis@example.com",
  "cargo": "Responsable local",
  "id_departamento": 2,
  "id_provincia": 201,
  "id_municipio": 20101
}
```

- **El `PUT /usuarios/{id}` NO acepta `contrasena` ni `id_rol` ni `activo`**
  (el esquema los rechaza con 422). La contraseña se cambia solo en
  `POST /api/v1/auth/cambiar-contrasena` (el usuario ya está logueado).
- La geografía se valida: la provincia debe pertenecer al departamento y el municipio a
  la provincia/departamento (400 si son inconsistentes). Para limpiar la geografía,
  enviar `null` en los tres campos.
- Para editar el perfil de **otro** usuario se requiere permiso SISTEMA `UPDATE`
  (solo admin/superadmin), con el mismo cuerpo de perfil.

### Administración de cuenta (solo SISTEMA UPDATE)

`PUT /api/v1/usuarios/{id}/cuenta` permite a admin/superadmin modificar credenciales,
rol y estado de cualquier usuario:

```json
{ "contrasena": "NuevaClave", "id_rol": 6, "activo": false }
```

Ejemplo:

```bash
curl -X PUT http://localhost:8000/api/v1/usuarios/7 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id_departamento":2,"id_provincia":201,"id_municipio":20101}'
```

---

## 6. Autenticación y Roles

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

### Migración v1.2.8

Incluye la migración **v1.3.0** de BD (nombrada así por el esquema de versionado de la base) y cambios de API:

- **Geografía en perfil de usuario**: `shared.provincia` y `shared.municipio` ahora tienen claves únicas compuestas; `usuarios.usuario` valida que departamento→provincia→municipio sean coherentes (FKs compuestas en `database/migration_v1.3.0.sql`).
- **Edición de perfil**: `PUT /usuarios/{id}` sin contraseña (autocontrol por token); nuevo `PUT /usuarios/{id}/cuenta` (solo `SISTEMA UPDATE`).
- **REA — categorías**: `GET /reportes`, `GET /reportes/mis-reportes` y `GET /reportes/mis-resumen` ahora devuelven `categorias` (objetos completos desde `rea.reporte_afectacion`), igual que el detalle.
- **REA — nodo `usuario`**: todos los GET de reportes (y las respuestas de POST/PUT) incluyen un nodo anidado `usuario` con el perfil completo del que registró el reporte (id, nombre, carnet, celular, correo, cargo, rol y geografía anidados).
- **Usuarios — filtros en listado**: `GET /usuarios/` acepta `id_departamento`, `id_provincia`, `id_municipio` e `id_rol`. Regla: a lo sumo **un** filtro de geografía a la vez (dos o más → `400`), opcionalmente acompañado de `id_rol`. `total` ahora es el conteo real (`COUNT(*)`), correcto con paginación.
- Versión de API alineada a `1.2.8`.

### Migración v1.2.7

No requiere cambios en esquema de BD. Solo cambios en lógica de API:

- `PUT /rea/reportes/{id}/estado`: rol 6 puede cambiar estado de reportes de rol 7 en su mismo municipio
- `GET /auth/mis-permisos`: bugfix (500 error corregido)
- `get_current_user` ahora incluye `id_municipio`

### Migración v1.4.2

- **Permisos EDAN restringidos**: solo superadmin/admin (roles 1-2) y UGR Municipio (rol 6) escriben (CREATE/UPDATE/DELETE); los demás roles (3, 4, 5, 7, 8, 9) quedan **solo lectura (READ)**.
- **Se eliminan** las acciones/aplicaciones de prueba **TEST** y **VERIFY** (`database/migration_v1.4.2.sql`).

### Migración v1.4.3

- **Sync offline-first EDAN**: columna `edan.edan.id_local` (`VARCHAR(64)` UNIQUE, UUID del móvil) e índice `idx_edan_sync_pull (id_usuario, fecha_modificacion)`.
- **Endpoints**: `POST /api/v1/edan/sync` (push) y `GET /api/v1/edan/sync/pull` (pull incremental). Servidor como autoridad de tiempo; conflictos por versión atrasada; borrados propagados como tombstones (`database/migration_v1.4.3.sql`).

### Migración v1.5.0

- **Restaura la funcionalidad geoespacial**: crea la extensión **PostGIS** (en el schema `public`), agrega `shared.municipio.geom` (`geometry(MultiPolygon, 4326)`) y el índice GiST `idx_municipio_geom`.
- Los datos geométricos (340 polígonos) se restauran aparte con **`database/restaurar_geom.sh`** (extrae el bloque COPY de un backup completo, sin tocar otras tablas).
- **Motivo**: la BD perdió PostGIS/`geom` al restaurarse desde un dump parcial (`backup_pre_*.sql`), rompiendo `/shared/municipios/*/geojson|geom|ubicacion` con `column m.geom does not exist` (`database/migration_v1.5.0.sql`).

### Manejo de backups (regla anti-pérdida)

- **Siempre restaurar desde el backup COMPLETO más reciente** (`database/backup_*.sql`, p. ej. `backup_v1.5.0.sql`).
- **Nunca usar como base**: `backup_pre_*.sql` (dump parcial de schemas sueltos), `crear_edan_db.sql` (solo estructura), `edan_db_backup.sql` (antiguo), `insert_provincias_municipios.sql` (solo catálogo).
- **Backup automático**: `database/hacer_backup.sh` genera un `pg_dump` completo (con PostGIS) y conserva los 14 más recientes. Cron diario configurado: `0 3 * * *`.
- **Verificación de integridad**: el script comprueba que el backup contenga `CREATE EXTENSION ... postgis`; los scripts de restauración (`restore_db.sh`, `deploy/desplegar_bd.sh`) eligen el backup más reciente automáticamente y avisan si falta PostGIS.
- **Antes de aplicar una migración**: ejecutar `bash database/hacer_backup.sh` para tener punto de retorno.

### Historial de migraciones

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 \
  -f database/migration_v1.2.0.sql \
  -f database/migration_v1.2.1.sql \
  -f database/migration_v1.2.3.sql \
  -f database/migration_v1.2.5_permisos.sql \
  -f database/migration_v1.3.0.sql \
  -f database/migration_v1.4.2.sql \
  -f database/migration_v1.4.3.sql \
  -f database/migration_v1.5.0.sql
```

> Nota: las migraciones v1.4.x aplican sobre la estructura EDAN jerárquica. En un
> despliegue desde cero, `deploy/desplegar_bd.sh` ejecuta **todas** las
> `migration_*.sql` en orden automáticamente.

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

### Consultar usuarios con filtros

```bash
# Solo municipio
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/usuarios/?id_municipio=20101"

# Municipio + rol (combo válido)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/usuarios/?id_municipio=20101&id_rol=7"

# Dos geografías a la vez → HTTP 400
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/usuarios/?id_departamento=2&id_provincia=201"
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

## 9. Acceso por dominio (api.climbat.net)

El dominio `api.climbat.net` apunta al servidor mediante un proxy upstream en `10.10.0.6` que:

- Termina SSL/TLS
- Reenvía el tráfico HTTP a `10.10.0.24:8000` (Uvicorn)

```
Usuario → https://api.climbat.net (DNS → 10.10.0.6)
             ↓ (SSL termina en 10.10.0.6)
          [Proxy upstream 10.10.0.6]
             ↓ (HTTP)
          api:8000 en 10.10.0.24 (Uvicorn)
```

Ver `docs/DOMINIO_API.md` para más detalles.

---

## 10. Troubleshooting

```bash
# Logs de la API
tail -f /tmp/uvicorn.log

# Verificar BD
pg_isready

# Probar conexión
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1

# Verificar endpoint público
curl https://api.climbat.net/health

# Verificar uploads
ls -la uploads/reports/
```

---

## 11. Archivos

```
SINAGER-SAT/
├── api/                     # Código fuente FastAPI
│   ├── main.py              # v1.2.8 — Entry point + Swagger custom
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
├── stop.sh                  # Detener todo
├── database/
│   ├── backup_v1.2.8.sql    # Backup completo con PostGIS (fuente de geometría)
│   ├── backup_v1.5.0.sql    # Backup completo de referencia MÁS RECIENTE
│   ├── backup_YYYY_MM_DD_HHMMSS.sql   # Backups automáticos (cron diario 03:00)
│   ├── migration_v1.2.0.sql
│   ├── migration_v1.2.1.sql
│   ├── migration_v1.2.3.sql
│   ├── migration_v1.2.5_permisos.sql
│   ├── migration_v1.2.7.sql
│   ├── migration_v1.3.0.sql    # FKs compuestas geografía en usuarios.usuario
│   ├── migration_v1.4.2.sql    # Permisos EDAN: solo rol 6+admin escriben; quita TEST/VERIFY
│   ├── migration_v1.4.3.sql    # Sync offline: id_local UNIQUE + índice pull
│   ├── migration_v1.5.0.sql    # PostGIS + shared.municipio.geom + índice GiST
│   ├── hacer_backup.sh         # Backup completo (cron diario, conserva 14)
│   ├── restaurar_geom.sh       # Recupera geom de municipios sin tocar otras tablas
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
    ├── DOMINIO_API.md       # Despliegue con dominio api.climbat.net
    └── APACHE_PROXY.md      # Configuración Apache (para proxy upstream)
```
