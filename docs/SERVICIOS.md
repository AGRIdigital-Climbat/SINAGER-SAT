# SINAGERSAT — Gestión de Servicios

Guía rápida para administrar la API y el tunnel de acceso externo. v1.2.7.

---

## Servicios

| Servicio | Descripción |
|----------|-------------|
| `sinagersat-api` | FastAPI en puerto 8000 |
| `sinagersat-tunnel` | Cloudflare Quick Tunnel (acceso externo) |

---

## Comandos

```bash
# Estado
sudo systemctl status sinagersat-api sinagersat-tunnel

# Iniciar
sudo systemctl start sinagersat-api sinagersat-tunnel

# Detener
sudo systemctl stop sinagersat-tunnel sinagersat-api

# Reiniciar
sudo systemctl restart sinagersat-api sinagersat-tunnel

# Habilitar al inicio
sudo systemctl enable sinagersat-api sinagersat-tunnel

# Deshabilitar
sudo systemctl disable sinagersat-api sinagersat-tunnel
```

---

## Obtener URL Pública

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### Alias rápido (~/.bashrc)

```bash
alias sinagersat-url="grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1"
```

---

## Ver Logs

```bash
journalctl -u sinagersat-api -f     # API en tiempo real
journalctl -u sinagersat-tunnel -f  # Tunnel en tiempo real
tail -f /tmp/uvicorn.log            # Log de uvicorn
tail -f /tmp/cloudflared.log        # Log de cloudflare
```

---

## Verificar que Todo Funciona

```bash
# 1. API responde
curl http://localhost:8000/

# 2. Swagger
curl http://localhost:8000/docs

# 3. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'

# 4. URL externa
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
curl "$URL/"
```

---

## Troubleshooting

```bash
# API no arranca
journalctl -u sinagersat-api -n 20
pg_isready

# Tunnel no arranca
cloudflared --version
curl http://localhost:8000/

# Puerto 8000 ocupado
ss -tlnp | grep 8000
sudo fuser -k 8000/tcp

# URL del tunnel cambió
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1

# Error 500
journalctl -u sinagersat-api -f
sudo systemctl restart sinagersat-api
```
