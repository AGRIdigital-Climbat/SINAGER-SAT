# Conexión a la Base de Datos

## Credenciales

| Parámetro | Valor |
|-----------|-------|
| **Host** | `localhost` o `192.168.0.34` |
| **Puerto** | `5432` |
| **Base de datos** | `db_sinagersat` |
| **Usuario** | `sinagersat` |
| **Contraseña** | `12345678` |

## Conexión por terminal

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h localhost -p 5432
```

## Conexión desde red local

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 192.168.0.34 -p 5432
```

## DBeaver

1. Nuevo Connection > PostgreSQL
2. Host: `localhost` (o `192.168.0.34` para red local) | Port: `5432`
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
| URL pública | Ver `grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1` |

Documentación completa: `docs/DESPLIEGUE_API.md`
