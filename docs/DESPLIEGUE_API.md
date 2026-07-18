# SINAGERSAT API - Despliegue y Acceso Externo

Guía completa para desplegar la API REST y acceder desde internet. v1.2.0.

---

## 1. Despliegue Rápido

### Desde cero (entorno vacío)

```bash
cd SINAGER-SAT
sudo bash deploy/desplegar_todo.sh
```

Esto instala PostgreSQL + Python + BD completa + API.

### Solo API (si PostgreSQL ya está corriendo)

```bash
sudo bash deploy/desplegar_todo.sh --api-only
```

### Con acceso externo (Cloudflare Tunnel)

```bash
sudo bash deploy/desplegar_todo.sh --tunnel
```

---

## 2. URLs de la API

### Local

| Servicio | URL |
|----------|-----|
| API Base | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| Health Check | `http://localhost:8000/health` |

### Externo (desde internet)

Con el Cloudflare Quick Tunnel, la URL es **dinámica** (cambia al reiniciar el servicio `sinagersat-tunnel`).

#### Obtener la URL pública actual

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

Ejemplo de salida:
```
https://abc-def-ghi.trycloudflare.com
```

#### Script rápido (agregar a ~/.bashrc)

```bash
alias sinagersat-url="grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1"
```

Uso:
```bash
sinagersat-url           # Imprime la URL
sinagersat-url | xclip   # Copia al portapapeles (Linux)
sinagersat-url | pbcopy  # Copia al portapapeles (macOS)
```

#### Verificar que funciona desde internet

```bash
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
echo "URL: $URL"
curl "$URL/"        # Debe mostrar info de la API
curl "$URL/docs"    # Debe mostrar Swagger UI
```

#### Desde otra máquina en la red local

```bash
curl http://192.168.0.34:8000/docs
```

---

## 3. Acceso Externo (desde internet)

Hay **3 opciones** para acceder desde fuera de la red:

### Opción A: Cloudflare Quick Tunnel (Recomendado - Sin configuración)

No requiere dominio ni cuenta. Genera una URL temporal.

```bash
bash start_tunnel.sh
```

**Ventajas:**
- No necesita configurar router
- No necesita dominio
- HTTPS automático
- Funciona desde cualquier red

**Desventajas:**
- URL cambia al reiniciar el tunnel
- No apto para producción permanente

**Cómo obtener la URL:**
```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Opción B: URL Fija con Cloudflare (Recomendado para producción)

Requiere una cuenta gratuita en Cloudflare y un dominio.

1. Crear cuenta en [Cloudflare](https://dash.cloudflare.com)
2. Registrar un dominio (o usar uno existente)
3. Login a Cloudflare desde el servidor:

```bash
cloudflared tunnel login
```

4. Crear tunnel permanente:

```bash
cloudflared tunnel create sinagersat
```

5. Configurar `~/.cloudflared/config.yml` (reemplaza `<TUNNEL_ID>` y `TU_DOMINIO.com`):

```yaml
tunnel: sinagersat
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.TU_DOMINIO.com
    service: http://localhost:8000
  - service: http_status:404
```

6. Asociar dominio al tunnel:

```bash
cloudflared tunnel route dns sinagersat api.TU_DOMINIO.com
```

7. Iniciar:

```bash
cloudflared tunnel run sinagersat
```

Resultado: `https://api.TU_DOMINIO.com` siempre apunta a tu API.

### Opción C: Port Forwarding en el Router

Requiere acceso al router (192.168.0.1).

1. Acceder al panel del router: `http://192.168.0.1`
2. Buscar "Port Forwarding" / "Virtual Server"
3. Agregar regla:
   - Puerto externo: `8000`
   - IP interna: `192.168.0.34`
   - Puerto interno: `8000`
   - Protocolo: TCP

Resultado: `http://181.188.161.73:8000`

**Verificar si funciona:**
```bash
curl http://181.188.161.73:8000/
```

### Opción D: ngrok

Similar a Cloudflare tunnel, pero con ngrok.

```bash
# Instalar
curl -s https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip | sudo unzip -d /usr/local/bin

# Ejecutar (requiere cuenta gratuita en ngrok.com)
ngrok http 8000
```

---

## 4. Formato de Respuestas (v1.2.0)

### Respuesta exitosa (lista)

```json
{
  "success": true,
  "message": "Departamentos listados correctamente",
  "data": [
    { "id": 1, "codigo_ine": "01", "nombre": "Chuquisaca" },
    { "id": 2, "codigo_ine": "02", "nombre": "La Paz" }
  ],
  "total": 9
}
```

### Respuesta exitosa (objeto)

```json
{
  "success": true,
  "message": "Usuario obtenido correctamente",
  "data": {
    "id_usuario": 1,
    "usuario": "sinagersat",
    "nombre": "sinagersat",
    "id_departamento": 2,
    "departamento": { "id": 2, "codigo_ine": "02", "nombre": "La Paz" },
    "rol": { "id_rol": 1, "nombre": "superadministrador", "jerarquia": 5 }
  },
  "total": null
}
```

### Respuesta de eliminación

```json
{
  "message": "EDAN eliminado correctamente"
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

### Error de autenticación

```json
{
  "detail": "Not authenticated"
}
```

### Objetos anidados

Para todas las foreign keys, las respuestas incluyen el `id_*` original **y** un objeto anidado con los datos relacionados:

```json
{
  "id_departamento": 2,
  "id_provincia": 201,
  "departamento": { "id": 2, "codigo_ine": "02", "nombre": "La Paz" },
  "provincia": { "id": 201, "codigo_ine": "0201", "nombre": "Murillo" }
}
```

Esto aplica a: departamento, provincia, municipio, rol, tipo_evento, estado, grupo_etario, servicio_basico, categoria_proteccion, ayuda_humanitaria.

---

## 5. Estructura de Endpoints

La API tiene **157 endpoints** v1.2.0 organizados en 5 módulos.

### Endpoints Públicos (sin token)

| Grupo | Prefijo | Descripción |
|-------|---------|-------------|
| Auth | `/api/v1/auth/` | Login y registro |
| Shared | `/api/v1/shared/` | Geografía: deptos, provs, municipios (CRUD completo) |

### Endpoints Protegidos (requieren token JWT)

| Grupo | Prefijo | Descripción |
|-------|---------|-------------|
| EDAN | `/api/v1/edan/` | Formularios + 17 sub-tablas + 5 catálogos |
| REA | `/api/v1/rea/` | Reportes, estados, categorías |
| Usuarios | `/api/v1/usuarios/` | Cuentas, roles, permisos, sesiones, auditoría |

```
/api/v1/
├── auth/              # Autenticación (PÚBLICO)
│   ├── POST /login         # Login → token JWT
│   └── POST /register      # Registrar usuario
│
├── shared/            # Geografía (PÚBLICO, CRUD completo)
│   ├── GET/POST /departamentos       # 9 departamentos
│   ├── GET/PUT/DELETE /departamentos/{id}
│   ├── GET/POST /provincias          # 112 provincias
│   ├── GET/PUT/DELETE /provincias/{id}
│   ├── GET/POST /municipios          # 340 municipios
│   └── GET/PUT/DELETE /municipios/{id}
│
├── edan/              # Formularios EDAN (🔒 requiere token)
│   ├── GET/POST /           # Listar/Crear EDAN
│   ├── GET/PUT/DELETE /{id} # Obtener/Actualizar/Eliminar
│   ├── /{id}/poblacion-grupo
│   ├── /{id}/tipos-evento
│   ├── /{id}/primera-respuesta
│   ├── /{id}/salud-establecimientos
│   ├── /{id}/salud-necesidades
│   ├── /{id}/infraestructura-vial
│   ├── /{id}/infraestructura-publica
│   ├── /{id}/servicios-basicos
│   ├── /{id}/educacion-dano
│   ├── /{id}/educacion-afectacion
│   ├── /{id}/vivienda
│   ├── /{id}/agricultura
│   ├── /{id}/pecuaria
│   ├── /{id}/infraestructura-productiva
│   ├── /{id}/proteccion
│   ├── /{id}/ayuda-humanitaria-edan
│   ├── /{id}/comunidades
│   ├── /tipo-evento         # Catálogo
│   ├── /grupo-etario        # Catálogo
│   ├── /servicio-basico     # Catálogo
│   ├── /categoria-proteccion # Catálogo
│   └── /ayuda-humanitaria   # Catálogo
│
├── rea/               # Reportes de Eventos Adversos (🔒 requiere token)
│   ├── GET/POST /reportes          # Listar/Crear
│   ├── GET/PUT/DELETE /reportes/{id}
│   ├── PUT /reportes/{id}/estado   # Cambiar estado
│   ├── GET/POST /estados           # Estados del reporte
│   └── GET/POST /categorias        # Categorías de afectación
│
└── usuarios/          # Gestión de usuarios (🔒 requiere token)
    ├── GET/POST /              # Listar/Crear
    ├── GET/PUT/DELETE /{id}
    ├── GET/POST /roles
    ├── GET/PUT/DELETE /roles/{id}
    ├── GET/POST /aplicaciones
    ├── GET/PUT/DELETE /aplicaciones/{id}
    ├── GET /permisos
    ├── GET /sesiones
    └── GET /auditoria
```

---

## 6. Autenticación y Roles

La API usa JWT (JSON Web Tokens) v1.2.0 con sistema de roles.

### Roles del Sistema

| id_rol | Rol | Jerarquía | Descripción |
|--------|-----|-----------|-------------|
| 1 | superadministrador | 5 | Acceso total a todos los sistemas |
| 2 | admin | 4 | Gestiona usuarios y datos de su sistema |
| 3 | encuestador | 2 | Carga y edita formularios propios |
| 4 | visor | 1 | Solo lectura en todos los módulos |

### Endpoints sin token (públicos)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Registrar usuario (default: rol visor) |
| `/api/v1/auth/login` | POST | Login → token JWT + info de rol |
| `/api/v1/usuarios/` | POST | Crear usuario (puede asignar id_rol) |
| `/api/v1/shared/*` | GET/POST/PUT/DELETE | Geografía (CRUD completo) |

### Obtener token

```bash
# Login → obtiene token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'
```

Respuesta (v1.2.0):
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
    "rol": "superadministrador"
  },
  "total": null
}
```

### Usar el token

```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."

# Listar EDAN (requiere auth)
curl http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer $TOKEN"
```

### Desde Swagger UI

1. Ir a `http://localhost:8000/docs`
2. Probar endpoints públicos sin token
3. Para endpoints protegidos: click **Authorize** → pegar el token
4. Ahora todos los endpoints protegidos funcionan

---

## 7. Ejemplos de Uso

### Crear un reporte EDAN

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
    "fecha_evento": "2026-07-15",
    "hora_evento": "14:30:00",
    "localidades_afectadas": 3,
    "total_poblacion_afectada": 500,
    "total_familias_afectadas": 100,
    "total_familias_damnificadas": 30,
    "nombre_responsable": "Maria Garcia",
    "cargo_responsable": "Directora DEDECA",
    "telefono_responsable": "71111111",
    "email_responsable": "maria@gov.bo",
    "usuario_registro": "sinagersat",
    "id_reporte_rea": null
  }'
```

### Crear un reporte REA

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
    "hora_evento": "14:30:00",
    "id_tipo_evento": 1,
    "descripcion": "Inundación en zona urbana",
    "id_estado": 1,
    "categorias": [1, 3]
  }'
```

### Obtener EDAN completa (con sub-tablas)

```bash
curl http://localhost:8000/api/v1/edan/1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Obtener URL pública y probar desde internet

```bash
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
echo "URL pública: $URL"
curl "$URL/"
curl "$URL/docs"
```

---

## 8. Configuración

### Variables de entorno (.env)

```bash
DATABASE_URL=postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat
JWT_SECRET=tu-secreto-seguro-aqui
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

**Importante:** Cambiar `JWT_SECRET` en producción.

### Cambiar puerto

```bash
# Editar start_api.sh
uvicorn api.main:app --host 0.0.0.0 --port 9000 --reload
```

### Cambiar host de BD

Si la BD está en otro servidor, editar `.env`:
```
DATABASE_URL=postgresql://sinagersat:12345678@10.10.10.220:5432/db_sinagersat
```

---

## 9. Troubleshooting

### API no inicia

```bash
# Ver logs
journalctl -u sinagersat-api -n 50

# Verificar que la BD está corriendo
pg_isready

# Probar conexión directa
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

### No hay acceso externo

```bash
# Verificar firewall
sudo ufw status
sudo iptables -L INPUT -n

# Verificar que el puerto escucha
ss -tlnp | grep 8000

# Verificar IP pública
curl ifconfig.me

# Verificar Cloudflare tunnel
cat /tmp/cloudflared.log | tail -20
```

### Obtener URL del tunnel (cambia al reiniciar)

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Token expirado

```bash
# Hacer login de nuevo para obtener nuevo token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "sinagersat", "contrasena": "12345678"}'
```

### Error 422 en endpoints

Verificar que el body del request tiene el formato correcto.
Usar Swagger UI (`/docs`) para probar interactivamente.

### API retorna error 500

```bash
# Ver logs detallados
journalctl -u sinagersat-api -f

# Reiniciar
sudo systemctl restart sinagersat-api
```

---

## 10. Archivos

```
SINAGER-SAT/
├── api/                    # Código fuente de la API
│   ├── main.py             # Punto de entrada FastAPI
│   ├── config.py           # Configuración (.env)
│   ├── database.py         # Conexión SQLAlchemy
│   ├── dependencies.py     # JWT auth dependency
│   ├── response.py         # SuccessResponse/ErrorResponse/MessageResponse
│   ├── auth/               # Login/Register
│   ├── shared/             # Geografía
│   ├── edan/               # Formularios EDAN
│   ├── rea/                # Reportes REA
│   └── usuarios/           # Gestión usuarios
├── .env                    # Variables de entorno
├── requirements.txt        # Dependencias Python
├── start_api.sh            # Iniciar API local
├── start_tunnel.sh         # Iniciar API + tunnel
├── stop.sh                 # Detener todo
├── deploy/                 # Scripts de despliegue
│   ├── desplegar_todo.sh   # Despliegue completo
│   ├── desplegar_bd.sh     # Solo BD
│   └── verificar.sh        # Verificar estado
├── database/
│   ├── edan_db_backup.sql  # Backup completo de BD
│   └── servers.json        # Config pgAdmin4
└── docs/
    ├── DESPLIEGUE_API.md   # Esta guía
    ├── EDAN_BD.md          # Documentación de la BD
    ├── SERVICIOS.md        # Gestión de servicios
    └── CONECTAR.md         # Credenciales
```
