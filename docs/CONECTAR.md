# Conexión a la Base de Datos

## Credenciales

| Parámetro | Valor |
|-----------|-------|
| **Host** | `10.10.10.220` |
| **Puerto** | `5432` |
| **Base de datos** | `db_sinagersat` |
| **Usuario** | `sinagersat` |
| **Contraseña** | `12345678` |

## Conexión por terminal

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 10.10.10.220 -p 5432
```

## DBeaver

1. Nuevo Connection > PostgreSQL
2. Host: `10.10.10.220` | Port: `5432`
3. Database: `db_sinagersat` | User: `sinagersat`
4. Password: `12345678`

## pgAdmin4

1. Abrir pgAdmin4
2. **File > Import/Export Servers > Import**
3. Seleccionar `database/servers.json`
