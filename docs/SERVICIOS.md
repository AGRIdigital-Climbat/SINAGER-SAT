# SINAGERSAT — Gestión de Servicios

Guía rápida para administrar la base de datos y la API. v1.3.0.

---

## Servicios

| Servicio | Descripción |
|----------|-------------|
| `postgresql` | PostgreSQL 16 en puerto 5432 |
| `sinagersat-api` | FastAPI (Uvicorn) en puerto 8000 |

---

## Comandos — PostgreSQL

```bash
# Estado
sudo systemctl status postgresql

# Iniciar
sudo systemctl start postgresql

# Detener
sudo systemctl stop postgresql

# Reiniciar
sudo systemctl restart postgresql

# Habilitar al inicio
sudo systemctl enable postgresql
```

### Conexión directa

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

---

## Comandos — API

### Inicio manual

```bash
cd /home/prosuco/SINAGERSAT/BaseData
bash start_api.sh
```

### Servicio systemd (instalado y activo)

```bash
# Estado
sudo systemctl status sinagersat-api

# Iniciar
sudo systemctl start sinagersat-api

# Detener
sudo systemctl stop sinagersat-api

# Reiniciar
sudo systemctl restart sinagersat-api

# Habilitar al inicio
sudo systemctl enable sinagersat-api

# Deshabilitar
sudo systemctl disable sinagersat-api
```

---

## Acceso por dominio

```bash
curl https://api.climbat.net/          # → Información de la API
curl https://api.climbat.net/health    # → {"status":"ok"}
curl https://api.climbat.net/docs      # → Swagger UI
curl https://api.climbat.net/redoc     # → ReDoc
```

---

## Ver Logs

```bash
# PostgreSQL
journalctl -u postgresql -f

# API (systemd)
journalctl -u sinagersat-api -f

# API (inicio manual)
tail -f /tmp/uvicorn.log
```

---

## Verificar que Todo Funciona

```bash
# 1. PostgreSQL responde
pg_isready

# 2. Conexión a la BD
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "SELECT 1;"

# 3. API responde localmente
curl http://127.0.0.1:8000/

# 4. Swagger
curl http://127.0.0.1:8000/docs

# 5. Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'

# 6. Por dominio
curl https://api.climbat.net/
```

---

## Troubleshooting

```bash
# PostgreSQL no arranca
journalctl -u postgresql -n 30
pg_isready
sudo systemctl restart postgresql

# API no arranca
journalctl -u sinagersat-api -n 20
pg_isready  # la BD debe estar corriendo primero

# Puerto 8000 ocupado
ss -tlnp | grep 8000
sudo fuser -k 8000/tcp

# Puerto 5432 ocupado
ss -tlnp | grep 5432

# Error 500 en la API
journalctl -u sinagersat-api -f
sudo systemctl restart sinagersat-api

# Verificar que el proxy upstream responde
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
```
