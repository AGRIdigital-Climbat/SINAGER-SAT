# SINAGERSAT - Gestión de Servicios

Guía rápida para administrar la API y el tunnel de acceso externo.

---

## Servicios

| Servicio | Descripción |
|----------|-------------|
| `sinagersat-api` | FastAPI en puerto 8000 |
| `sinagersat-tunnel` | Cloudflare Quick Tunnel (acceso externo) |

Ambos están habilitados para iniciar automáticamente al encender la PC.

---

## Comandos

### Ver estado

```bash
sudo systemctl status sinagersat-api sinagersat-tunnel
```

### Iniciar

```bash
# Ambos servicios
sudo systemctl start sinagersat-api sinagersat-tunnel

# Solo API
sudo systemctl start sinagersat-api

# Solo tunnel
sudo systemctl start sinagersat-tunnel
```

### Detener

```bash
# Ambos servicios
sudo systemctl stop sinagersat-tunnel sinagersat-api

# Solo tunnel
sudo systemctl stop sinagersat-tunnel
```

### Reiniciar

```bash
sudo systemctl restart sinagersat-api sinagersat-tunnel
```

### Habilitar / Deshabilitar al inicio

```bash
# Habilitar (ya está habilitado por defecto)
sudo systemctl enable sinagersat-api sinagersat-tunnel

# Deshabilitar (no inician al encender la PC)
sudo systemctl disable sinagersat-api sinagersat-tunnel
```

---

## Obtener URL del Tunnel

La URL pública (para acceder desde internet):

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

**Nota:** La URL cambia cada vez que se reinicia el servicio `sinagersat-tunnel`.

---

## Ver Logs

```bash
# Logs de la API (tiempo real)
journalctl -u sinagersat-api -f

# Logs del tunnel (tiempo real)
journalctl -u sinagersat-tunnel -f

# Últimas 50 líneas de la API
journalctl -u sinagersat-api -n 50

# Logs en archivo
tail -f /tmp/uvicorn.log
tail -f /tmp/cloudflared.log
```

---

## Verificar que Todo Funciona

```bash
# 1. API responde en local
curl http://localhost:8000/

# 2. Swagger funciona
curl http://localhost:8000/docs

# 3. URL externa funciona (reemplazar con la URL actual)
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
curl "$URL/"
curl "$URL/docs"
```

---

## Troubleshooting

### API no arranca

```bash
# Ver error
journalctl -u sinagersat-api -n 20

# Verificar PostgreSQL
pg_isready

# Probar manualmente
cd "/media/luismi/Nuevo vol/SINAGERSAT/BaseData"
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Tunnel no arranca

```bash
# Ver error
journalctl -u sinagersat-tunnel -n 20

# Verificar que cloudflared está instalado
cloudflared --version

# Verificar que la API está corriendo
curl http://localhost:8000/

# Probar manualmente
cloudflared tunnel --url http://localhost:8000
```

### Puerto 8000 ocupado

```bash
# Ver qué lo usa
ss -tlnp | grep 8000

# Matar proceso
sudo fuser -k 8000/tcp
```

### URL del tunnel cambió y necesito la nueva

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

---

## Resumen Rápido

```bash
# Estado
sudo systemctl status sinagersat-api sinagersat-tunnel

# Iniciar
sudo systemctl start sinagersat-api sinagersat-tunnel

# Detener
sudo systemctl stop sinagersat-tunnel sinagersat-api

# URL externa
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1

# Logs
journalctl -u sinagersat-api -f
```
