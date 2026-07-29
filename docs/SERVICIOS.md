# SINAGERSAT — Gestión de Servicios

Guía rápida para administrar la API. v1.2.7.

---

## Servicios

| Servicio | Descripción |
|----------|-------------|
| `sinagersat-api` | FastAPI en puerto 8000 |

---

## Comandos

### Inicio manual

```bash
cd /home/prosuco/SINAGERSAT/BaseData
bash start_api.sh
```

### Servicio systemd (opcional)

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
journalctl -u sinagersat-api -f        # API en tiempo real (si hay servicio systemd)
tail -f /tmp/uvicorn.log               # Log de uvicorn (inicio manual)
```

---

## Verificar que Todo Funciona

```bash
# 1. API responde localmente
curl http://127.0.0.1:8000/

# 2. Swagger
curl http://127.0.0.1:8000/docs

# 3. Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'

# 4. Por dominio
curl https://api.climbat.net/
```

---

## Troubleshooting

```bash
# API no arranca
journalctl -u sinagersat-api -n 20
pg_isready

# Puerto 8000 ocupado
ss -tlnp | grep 8000
sudo fuser -k 8000/tcp

# Error 500
journalctl -u sinagersat-api -f
sudo systemctl restart sinagersat-api

# Verificar que el proxy upstream responde
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
```
