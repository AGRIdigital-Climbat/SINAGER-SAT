# SINAGERSAT API - Despliegue y Acceso Externo

Guía completa para desplegar la API REST y acceder desde internet.

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

Con el Cloudflare Quick Tunnel, la URL es dinámica (cambia al reiniciar).

```bash
# Iniciar API + tunnel
bash start_tunnel.sh
```

La URL pública aparece en pantalla al iniciar, y se guarda en:
```bash
cat /tmp/cloudflared.log | grep trycloudflare | head -1
```

### Desde otra máquina en la red local

```bash
# Reemplazar IP del servidor
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

**Para hacerlo permanente (mismo URL siempre):**

1. Crear cuenta gratuita en [Cloudflare](https://dash.cloudflare.com)
2. Registrar un dominio (o usar uno existente)
3. Crear un tunnel nombrado:

```bash
# Login a Cloudflare
cloudflared tunnel login

# Crear tunnel permanente
cloudflared tunnel create sinagersat

# Configurar (reemplaza TU_DOMINIO.com)
cat > ~/.cloudflared/config.yml << EOF
tunnel: sinagersat
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.TU_DOMINIO.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Asociar dominio al tunnel
cloudflared tunnel route dns sinagersat api.TU_DOMINIO.com

# Iniciar
cloudflared tunnel run sinagersat
```

Resultado: `https://api.TU_DOMINIO.com` siempre apunta a tu API.

### Opción B: Port Forwarding en el Router

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
# Desde el servidor
curl http://181.188.161.73:8000/
```

### Opción C: ngrok

Similar a Cloudflare tunnel, pero con ngrok.

```bash
# Instalar
curl -s https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip | sudo unzip -d /usr/local/bin

# Ejecutar (requiere cuenta gratuita en ngrok.com)
ngrok http 8000
```

---

## 4. Estructura de Endpoints

La API tiene **157 endpoints** v1.1.0 organizados en 5 módulos.

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
│   ├── GET/POST /estados           # Estados del reporte
│   └── GET/POST /categorias        # Categorías de afectación
│
└── usuarios/          # Gestión de usuarios (🔒 requiere token)
    ├── GET/POST /              # Listar/Crear
    ├── GET/PUT/DELETE /{id}
    ├── GET/roles
    ├── GET/permisos
    ├── GET/sesiones
    └── GET/auditoria
```

---

## 5. Autenticación

La API usa JWT (JSON Web Tokens) v1.1.0.

### Endpoints sin token (públicos)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Login → token JWT |
| `/api/v1/auth/register` | POST | Crear usuario |
| `/api/v1/shared/*` | GET/POST/PUT/DELETE | Geografía (CRUD completo) |

### Endpoints con token (protegidos)

Todos los endpoints de **EDAN**, **REA** y **Usuarios** requieren token.

### Obtener token

```bash
# 1. Registrar usuario (sin token)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123","nombre":"Admin"}'

# 2. Login → obtiene token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123"}'
```

Respuesta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "usuario": "admin",
  "nombre": "Admin"
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

## 6. Ejemplos de Uso

### Crear un reporte EDAN

```bash
curl -X POST http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_edan": "EDAN-2026-001",
    "id_departamento": 1,
    "id_municipio": 101,
    "nombre_alcalde": "Juan Perez",
    "telefono_alcalde": "70000000",
    "fecha_llenado": "2026-07-17",
    "fecha_evento": "2026-07-15",
    "hora_evento": "14:30:00",
    "localidades_afectadas": "Localidad A, Localidad B",
    "total_poblacion_afectada": 500,
    "total_familias_afectadas": 100,
    "total_familias_damnificadas": 30,
    "nombre_responsable": "Maria Garcia",
    "cargo_responsable": "Directora DEDECA",
    "telefono_responsable": "71111111",
    "email_responsable": "maria@gov.bo",
    "usuario_registro": "admin"
  }'
```

### Crear un reporte REA

```bash
curl -X POST http://localhost:8000/api/v1/rea/reportes/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Inundación en Oruro",
    "descripcion": "Lluvias intensas causaron inundaciones",
    "id_estado": 1,
    "usuario_registro": "admin"
  }'
```

### Obtener EDAN completa (con sub-tablas)

```bash
curl http://localhost:8000/api/v1/edan/1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 7. Configuración

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

## 8. Troubleshooting

### API no inicia

```bash
# Ver logs
tail -20 /tmp/uvicorn.log

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

### Token expirado

```bash
# Hacer login de nuevo para obtener nuevo token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "contrasena": "admin123"}'
```

### Error 422 en endpoints

Verificar que el body del request tiene el formato correcto.
Usar Swagger UI (`/docs`) para probar interactivamente.

---

## 9. Archivos

```
SINAGER-SAT/
├── api/                    # Código fuente de la API
│   ├── main.py             # Punto de entrada FastAPI
│   ├── config.py           # Configuración (.env)
│   ├── database.py         # Conexión SQLAlchemy
│   ├── dependencies.py     # JWT auth dependency
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
└── database/
    └── edan_db_backup.sql  # Backup completo de BD
```
