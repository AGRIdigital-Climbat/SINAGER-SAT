# SINAGERSAT API — Despliegue con dominio api.climbat.net

**Versión:** 1.2.7
**Dominio:** `https://api.climbat.net`
**IP del servidor (API):** `10.10.0.24`
**IP del proxy upstream:** `10.10.0.6`

---

## 1. Arquitectura

```
Usuario (HTTPS)
    ↓
api.climbat.net:443 (DNS → 10.10.0.6)
    ↓
Proxy upstream (10.10.0.6)
  - Termina SSL/TLS
  - Reenvía en HTTP
    ↓
Uvicorn (FastAPI) → 0.0.0.0:8000
    ↓
PostgreSQL → 127.0.0.1:5432
```

- **Proxy upstream** en `10.10.0.6` maneja SSL y redirige tráfico HTTP a este servidor.
- **Uvicorn** (FastAPI/Python) corre en `0.0.0.0:8000` aceptando conexiones desde cualquier interfaz.
- **PostgreSQL** corre en `127.0.0.1:5432` (solo local, no expuesto).

No se necesita Apache ni Nginx en este servidor — el proxy upstream hace ese trabajo.

---

## 2. Conexión PostgreSQL → FastAPI

FastAPI se conecta a PostgreSQL a través de la variable `DATABASE_URL` en el archivo `.env`:

**Ruta:** `/home/prosuco/SINAGERSAT/BaseData/.env`

```env
DATABASE_URL=postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat
```

| Parámetro | Valor |
|-----------|-------|
| Host | `127.0.0.1` (solo local) |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

La conexión es siempre a `127.0.0.1` porque PostgreSQL **no se expone a internet** — solo la API tiene acceso.

### Verificar conexión a BD

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "SELECT 'OK' as conexion;"
```

---

## 3. Binding de Uvicorn — las 3 opciones

Al iniciar la API con `uvicorn`, el parámetro `--host` define desde qué direcciones de red se aceptan conexiones:

| Host | Alcance | Cuándo usarlo |
|------|---------|---------------|
| `127.0.0.1` | Solo localhost | Detrás de un proxy en el mismo servidor (Apache, Nginx) |
| `0.0.0.0` | Todas las interfaces de red | Cuando el proxy upstream está en otra máquina |
| `10.10.0.24` | Solo la interfaz con esa IP | Producción con IP fija y firewall selectivo |

### Opción A: `127.0.0.1` — solo localhost

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
```

La API solo responde en `localhost`. Útil cuando Apache/Nginx está en el mismo servidor.

### Opción B: `0.0.0.0` — todas las interfaces (usada actualmente)

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

La API responde en cualquier interfaz de red. **Esta es la configuración actual** porque el proxy upstream está en `10.10.0.6` (otra máquina) y necesita acceder a `10.10.0.24:8000`.

### Opción C: `10.10.0.24` — IP fija

```bash
uvicorn api.main:app --host 10.10.0.24 --port 8000 --workers 4
```

La API solo responde en la interfaz con IP `10.10.0.24`. Requiere que el proxy upstream pueda alcanzar esa IP.

### Script de inicio

El archivo `start_api.sh` incluye las 3 opciones comentadas:

```bash
# host por defecto
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
# Para exponer a la red:
#   uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
# Para IP fija:
#   uvicorn api.main:app --host 10.10.0.24 --port 8000 --workers 4
```

---

## 4. Configuración del proxy upstream

Esta configuración se realiza en el servidor `10.10.0.6`, no en este servidor.

### Opción A: Nginx

```nginx
server {
    listen 80;
    server_name api.climbat.net;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.climbat.net;

    ssl_certificate /etc/letsencrypt/live/api.climbat.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.climbat.net/privkey.pem;

    location / {
        proxy_pass http://10.10.0.24:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

### Opción B: Apache

```apache
<VirtualHost *:80>
    ServerName api.climbat.net
    Redirect permanent / https://api.climbat.net/
</VirtualHost>

<VirtualHost *:443>
    ServerName api.climbat.net

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.climbat.net/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.climbat.net/privkey.pem

    ProxyPreserveHost On
    ProxyRequests Off

    <Location />
        ProxyPass http://10.10.0.24:8000/
        ProxyPassReverse http://10.10.0.24:8000/
    </Location>

    ProxyTimeout 300
    Timeout 300
</VirtualHost>
```

---

## 5. Servicio systemd (en este servidor)

Opcional — para que la API inicie automáticamente al reiniciar.

**Archivo:** `/etc/systemd/system/sinagersat-api.service`

```ini
[Unit]
Description=SINAGERSAT API REST (FastAPI)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=prosuco
Group=prosuco
WorkingDirectory=/home/prosuco/SINAGERSAT/BaseData
ExecStart=/home/prosuco/SINAGERSAT/BaseData/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/home/prosuco/SINAGERSAT/BaseData/venv/bin:/usr/bin:/bin
EnvironmentFile=/home/prosuco/SINAGERSAT/BaseData/.env

[Install]
WantedBy=multi-user.target
```

**Nota:** `ExecStart` usa `--host 0.0.0.0` porque el proxy upstream está en `10.10.0.6` (otra máquina). Si el proxy estuviera en este mismo servidor, se usaría `--host 127.0.0.1`.

### Instalar y activar

```bash
sudo cp deploy/systemd/sinagersat-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sinagersat-api
sudo systemctl start sinagersat-api
```

### Comandos útiles

```bash
sudo systemctl status sinagersat-api          # Estado
sudo systemctl restart sinagersat-api         # Reiniciar
journalctl -u sinagersat-api -f               # Logs en tiempo real
```

---

## 6. Verificación

### 6.1 Probar la API localmente

```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/health
```

### 6.2 Probar por IP del servidor

```bash
curl -s http://10.10.0.24:8000/
curl -s http://10.10.0.24:8000/health
curl -s http://10.10.0.24:8000/docs
```

### 6.3 Probar por dominio

```bash
curl -s https://api.climbat.net/
curl -s https://api.climbat.net/health
curl -s https://api.climbat.net/docs
```

### 6.4 Probar un endpoint público

```bash
curl -s https://api.climbat.net/api/v1/shared/departamentos
```

---

## 7. Resumen de comandos

```bash
# Iniciar API manual
cd /home/prosuco/SINAGERSAT/BaseData && bash start_api.sh

# Verificar base de datos
cd /home/prosuco/SINAGERSAT/BaseData && bash deploy/verificar.sh

# Servicio systemd
sudo systemctl start|stop|restart|status sinagersat-api

# Logs de la API
journalctl -u sinagersat-api -f
tail -f /tmp/uvicorn.log

# Verificar que el proxy upstream funciona
curl -s -o /dev/null -w "%{http_code}" https://api.climbat.net/
```

---

## 8. Solución de problemas

| Problema | Causa posible | Solución |
|----------|---------------|----------|
| `Connection refused` en dominio | API no está corriendo | `bash start_api.sh` o reiniciar systemd |
| `502 Bad Gateway` desde dominio | Proxy upstream no puede alcanzar `10.10.0.24:8000` | Verificar que la API corre en `0.0.0.0:8000` |
| El dominio no resuelve | DNS mal configurado | Verificar registro A: `api.climbat.net → 10.10.0.6` |
| SSL no funciona | Certificado vencido en el upstream | Renovar en el servidor `10.10.0.6` |
| No se puede conectar a la BD | PostgreSQL caído | `sudo systemctl restart postgresql` |
| La API responde lento | Pocos workers | Aumentar `--workers` al iniciar uvicorn |
