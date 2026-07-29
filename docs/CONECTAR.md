# Conexión a la Base de Datos

## Credenciales

| Parámetro | Valor |
|-----------|-------|
| **Host** | `localhost` o `127.0.0.1` |
| **Puerto** | `5432` |
| **Base de datos** | `db_sinagersat` |
| **Usuario** | `sinagersat` |
| **Contraseña** | `12345678` |

## Conexión por terminal

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost -p 5432
```

## DBeaver

1. Nuevo Connection > PostgreSQL
2. Host: `localhost` | Port: `5432`
3. Database: `db_sinagersat` | User: `sinagersat`
4. Password: `12345678`

## pgAdmin4

1. Abrir pgAdmin4
2. **File > Import/Export Servers > Import**
3. Seleccionar `database/servers.json`

## API REST

| Servicio | URL |
|----------|-----|
| API local | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| API por dominio | `https://api.climbat.net` |

Documentación completa: `docs/DESPLIEGUE_API.md`
