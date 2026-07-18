# SINAGERSAT - Base de Datos

Sistema Nacional de Alerta Temprana y Gestión de Riesgos. Base de datos multi-esquema con módulos EDAN y REA.

---

## Desplegar desde cero

```bash
sudo bash setup.sh
```

Esto instala PostgreSQL, crea la BD y verifica todo automáticamente.

---

## Restaurar BD (si ya tienes PostgreSQL instalado)

```bash
bash deploy/desplegar_bd.sh
```

---

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

Ver `docs/EDAN_BD.md` para documentación completa de la BD (esquemas, tablas, relaciones, ejemplos SQL).

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

### Endpoints (157 totales)

| Grupo | Prefijo | Operaciones |
|---|---|---|
| Auth | `/api/v1/auth/` | Login, Register (JWT) |
| Shared | `/api/v1/shared/` | CRUD departamentos, provincias, municipios |
| EDAN | `/api/v1/edan/` | CRUD EDAN + 17 sub-tablas + 5 catálogos |
| REA | `/api/v1/rea/` | CRUD reportes, estados, categorías |
| Usuarios | `/api/v1/usuarios/` | CRUD usuarios, roles, permisos, sesiones, auditoría |

### Autenticación

```bash
# Registrar usuario
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123","nombre":"Admin"}'

# Login → obtiene token JWT
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","contrasena":"pass123"}'

# Usar token en requests
curl http://localhost:8000/api/v1/shared/departamentos \
  -H "Authorization: Bearer <TU_TOKEN>"
```

### Documentación interactiva

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
