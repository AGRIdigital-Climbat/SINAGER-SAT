# SINAGERSAT - Base de Datos

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. Base de datos multi-esquema con módulos EDAN y REA. API REST v1.2.4.

---

## Desplegar desde cero (entorno vacío)

```bash
sudo bash deploy/desplegar_todo.sh
```

Esto instala PostgreSQL, Python, crea la BD completa con todos los datos, configura la API y la inicia.

**Opciones:**
```bash
sudo bash deploy/desplegar_todo.sh              # Todo (BD + API)
sudo bash deploy/desplegar_todo.sh --db-only    # Solo base de datos
sudo bash deploy/desplegar_todo.sh --api-only   # Solo API (si PG ya está)
sudo bash deploy/desplegar_todo.sh --tunnel     # Todo + Cloudflare tunnel público
```

## Restaurar solo BD (si ya tienes PostgreSQL)

```bash
bash deploy/desplegar_bd.sh
```

## Iniciar API

```bash
bash start_api.sh           # Local: http://localhost:8000/docs
bash start_tunnel.sh        # + Tunnel público Cloudflare
bash stop.sh                # Detener todo
```

## Verificar

```bash
bash deploy/verificar.sh
```

---

## Obtener URL Pública (Cloudflare Tunnel)

La API se expone a internet mediante Cloudflare Quick Tunnel. La URL es **dinámica** (cambia al reiniciar).

### Obtener URL actual

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Obtener URL + copiar al portapapeles

```bash
# Linux
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1 | xclip -selection clipboard

# macOS
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1 | pbcopy
```

### Script rápido

```bash
# Agregar alias a ~/.bashrc
alias sinagersat-url="grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1"

# Uso
sinagersat-url           # Imprime la URL actual
sinagersat-url | xclip   # Copia al portapapeles
```

### Verificar que funciona desde internet

```bash
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
curl "$URL/"
curl "$URL/docs"
```

### URL fija (con dominio propio)

Si necesitas una URL permanente:

1. Crear cuenta gratuita en [Cloudflare](https://dash.cloudflare.com)
2. Registrar un dominio (o usar uno existente)
3. Crear tunnel nombrado:

```bash
cloudflared tunnel login
cloudflared tunnel create sinagersat
```

4. Configurar `~/.cloudflared/config.yml`:

```yaml
tunnel: sinagersat
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.TU_DOMINIO.com
    service: http://localhost:8000
  - service: http_status:404
```

5. Asociar DNS e iniciar:

```bash
cloudflared tunnel route dns sinagersat api.TU_DOMINIO.com
cloudflared tunnel run sinagersat
```

Resultado: `https://api.TU_DOMINIO.com` siempre apunta a tu API.

---

## Arquitectura

| Esquema | Descripción |
|---|---|
| `shared` | Geografía INE 2024 (9 deptos, 112 provs, 340 munis) |
| `usuarios` | Gestión de usuarios (cuentas, roles) |
| `edan` | Formularios EDAN (23 tablas) |
| `rea` | Reportes de Eventos Adversos (4 tablas) |
| `rida`, `sinb`, `recursos` | Vacíos - futuros módulos |

---

## Conexión

| Parámetro | Valor |
|-----------|-------|
| Host | `localhost` o `192.168.0.34` |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost
```

---

## Herramientas gráficas

- **DBeaver**: Host: `localhost` | Port: `5432` | DB: `db_sinagersat` | User: `sinagersat`
- **pgAdmin4**: File > Import > `database/servers.json`

---

## Documentación

- `docs/EDAN_BD.md` - Documentación completa de la BD (esquemas, tablas, relaciones, SQL)
- `docs/DESPLIEGUE_API.md` - Guía de despliegue de la API y acceso externo desde internet
- `docs/SERVICIOS.md` - Gestión de servicios systemd (API + tunnel)
- `docs/CONECTAR.md` - Credenciales y formas de conexión a la BD

---

## Solución de problemas

```bash
# PostgreSQL no está corriendo
sudo service postgresql start

# Restaurar BD
bash deploy/desplegar_bd.sh

# Verificar
bash deploy/verificar.sh
```

---

## API REST (FastAPI) v1.2.4

### Iniciar API local

```bash
bash start_api.sh
# → http://localhost:8000/docs
```

### Iniciar API + Cloudflare Tunnel (acceso externo)

```bash
bash start_tunnel.sh
# → URL temporal: https://xxx.trycloudflare.com/docs
```

### Obtener URL pública

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Formato de Respuestas (v1.2.4)

Todas las respuestas exitosas usan el formato estándar:

```json
{
  "success": true,
  "message": "Operación exitosa",
  "data": { ... },
  "total": 9
}
```

Para errores:

```json
{
  "success": false,
  "message": "Error interno del servidor",
  "error_code": 500
}
```

Para eliminaciones:

```json
{
  "message": "Recurso eliminado correctamente"
}
```

### Objetos Anidados (v1.2.4)

Las respuestas incluyen objetos anidados para todas las foreign keys. Ejemplo de usuario:

```json
{
  "id_usuario": 1,
  "usuario": "sinagersat",
  "nombre": "sinagersat",
  "id_departamento": 2,
  "id_provincia": 201,
  "id_municipio": 20101,
  "id_rol": 1,
  "departamento": { "id": 2, "codigo_ine": "02", "nombre": "La Paz" },
  "provincia": { "id": 201, "codigo_ine": "0201", "nombre": "Murillo" },
  "municipio": { "id": 20101, "codigo_ine": "020101", "nombre": "La Paz" },
  "rol": { "id_rol": 1, "nombre": "superadministrador", "descripcion": "...", "jerarquia": 5 }
}
```

Los campos `id_*` originales se mantienen para compatibilidad; los objetos anidados son información complementaria.

### Endpoints (159 totales)

| Grupo | Prefijo | Acceso | Operaciones |
|---|---|---|---|
| Auth | `/api/v1/auth/` | Público | Login, Register |
| Shared | `/api/v1/shared/` | Público | CRUD deptos, provs, municipios |
| EDAN | `/api/v1/edan/` | Token | CRUD EDAN + 17 sub-tablas + 5 catálogos + con-foto |
| REA | `/api/v1/rea/` | Token | CRUD reportes + con-foto, estados, categorías |
| Usuarios | `/api/v1/usuarios/` | Token | CRUD usuarios, roles, permisos, sesiones, auditoría |
| Upload | `/api/v1/upload/` | Token | Subir/descargar archivos |

### Autenticación

```bash
# Registrar usuario (sin token, default rol visor)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123","nombre":"Admin"}'

# Registrar con rol específico
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"usuario":"enc1","contrasena":"pass123","nombre":"Enc1","id_rol":3}'

# Login → obtiene token JWT + info de rol
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123"}'

# Usar token en requests protegidos
curl http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer <TU_TOKEN>"
```

### Roles

| id | Rol | Jerarquía | Descripción |
|----|-----|-----------|-------------|
| 1 | superadmin | 5 | Acceso total a todos los sistemas |
| 2 | admin | 4 | Gestiona usuarios y datos de su sistema |
| 3 | VIDECI Regional | 3 | Carga y edita formularios propios |
| 4 | UGR Sectores | 2 | Carga y edita formularios propios |
| 5 | UGR Gobernación | 2 | Carga y edita formularios propios |
| 6 | UGR Municipio | 2 | Carga y edita formularios propios |
| 7 | Responsable Local | 1 | Carga y edita formularios propios |

### Documentación interactiva

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
