# SINAGERSAT - Gestión de Servicios

Guía rápida para administrar la API y el tunnel de acceso externo. v1.2.3.

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

## Obtener URL Pública (Cloudflare Tunnel)

La URL pública es **dinámica**: cambia cada vez que se reinicia el servicio `sinagersat-tunnel`.

### Obtener URL actual

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

Ejemplo de salida:
```
https://abc-def-ghi.trycloudflare.com
```

### Script rápido (alias)

```bash
# Agregar a ~/.bashrc
alias sinagersat-url="grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1"
```

Uso:
```bash
sinagersat-url           # Imprime la URL actual
sinagersat-url | xclip   # Copia al portapapeles (Linux)
sinagersat-url | pbcopy  # Copia al portapapeles (macOS)
```

### Verificar desde internet

```bash
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
echo "URL pública: $URL"
curl "$URL/"        # Info de la API
curl "$URL/docs"    # Swagger UI
```

### Desde otra máquina en la red local

```bash
curl http://192.168.0.34:8000/docs
```

### URL fija (con dominio propio)

Si necesitas una URL permanente, ver `docs/DESPLIEGUE_API.md` sección "Opción B: URL Fija con Cloudflare".

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

# 3. URL externa funciona
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1)
curl "$URL/"
curl "$URL/docs"

# 4. Login funciona
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}'

# 5. Endpoint protegido funciona
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"sinagersat","contrasena":"12345678"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/usuarios/roles
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

### URL del tunnel cambió

La URL cambia al reiniciar `sinagersat-tunnel`. Obtener la nueva:

```bash
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -1
```

### API retorna error 500

```bash
# Ver logs detallados
journalctl -u sinagersat-api -f

# Reiniciar
sudo systemctl restart sinagersat-api
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
