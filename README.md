# SINAGERSAT - Base de Datos

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. Base de datos multi-esquema con módulos EDAN y REA. API REST v1.1.0.

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
| Host | `10.10.10.220` o `localhost` |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 10.10.10.220
```

---

## Herramientas gráficas

- **DBeaver**: Host: `10.10.10.220` | Port: `5432` | DB: `db_sinagersat` | User: `sinagersat`
- **pgAdmin4**: File > Import > `database/servers.json`

---

## Documentación

- `docs/EDAN_BD.md` - Documentación completa de la BD (esquemas, tablas, relaciones, SQL)
- `docs/DESPLIEGUE_API.md` - Guía de despliegue de la API y acceso externo desde internet

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

## API REST (FastAPI)

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

### Endpoints (157 totales, v1.1.0)

| Grupo | Prefijo | Acceso | Operaciones |
|---|---|---|---|
| Auth | `/api/v1/auth/` | Público | Login, Register |
| Shared | `/api/v1/shared/` | Público | CRUD deptos, provs, municipios |
| EDAN | `/api/v1/edan/` | 🔒 Token | CRUD EDAN + 17 sub-tablas + 5 catálogos |
| REA | `/api/v1/rea/` | 🔒 Token | CRUD reportes, estados, categorías |
| Usuarios | `/api/v1/usuarios/` | 🔒 Token | CRUD usuarios, roles, permisos, sesiones, auditoría |

### Autenticación

```bash
# Registrar usuario (sin token)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123","nombre":"Admin"}'

# Login → obtiene token JWT
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123"}'

# Usar token en requests protegidos
curl http://localhost:8000/api/v1/edan/ \
  -H "Authorization: Bearer <TU_TOKEN>"
```

### Documentación interactiva

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
