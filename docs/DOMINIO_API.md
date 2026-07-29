# SINAGERSAT API — Despliegue con dominio api.climbat.net

**Versión:** 1.2.7
**Dominio:** `https://api.climbat.net`
**IP del servidor:** `10.10.0.24`

---

## 1. Arquitectura

```
Usuario (HTTPS)
    ↓
api.climbat.net:443
    ↓
Apache (proxy inverso)
    ↓
Uvicorn (FastAPI) → 127.0.0.1:8000
    ↓
PostgreSQL → 127.0.0.1:5432
```

- **Apache** recibe peticiones HTTPS en `api.climbat.net` y las redirige a la API interna.
- **Uvicorn** (FastAPI/Python) corre en el puerto `8000`.
- **PostgreSQL** corre en el puerto `5432` (solo local, no expuesto).

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
| `127.0.0.1` | Solo localhost | Desarrollo local o cuando Apache hace de proxy (recomendado) |
| `0.0.0.0` | Todas las interfaces de red | Cuando no hay firewall selectivo o pruebas rápidas |
| `10.10.0.24` | Solo la interfaz con esa IP | Producción con IP fija conocida |

### Opción A: `127.0.0.1` — solo localhost (por defecto)

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4
```

La API solo responde en `localhost`. Apache (o cualquier proxy) en el mismo servidor puede redirigir tráfico externo hacia ella.

### Opción B: `0.0.0.0` — todas las interfaces

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

La API responde en cualquier interfaz de red: `localhost`, `10.10.0.24`, y cualquier otra IP del servidor.

### Opción C: `10.10.0.24` — IP fija

```bash
uvicorn api.main:app --host 10.10.0.24 --port 8000 --workers 4
```

La API solo responde en la interfaz con IP `10.10.0.24`. No responde en `localhost` ni en otras interfaces.

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

## 4. Configurar Apache para api.climbat.net

### 4.1 Requisitos

```bash
sudo apt-get install -y apache2 certbot python3-certbot-apache
sudo a2enmod proxy proxy_http proxy_wstunnel ssl rewrite headers
sudo systemctl restart apache2
```

### 4.2 VirtualHost

**Archivo:** `/etc/apache2/sites-available/api.climbat.net.conf`

```apache
<VirtualHost *:80>
    ServerName api.climbat.net
    Redirect permanent / https://api.climbat.net/
</VirtualHost>

<VirtualHost *:443>
    ServerName api.climbat.net
    ServerAdmin admin@climbat.net

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.climbat.net/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.climbat.net/privkey.pem

    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"

    ProxyPreserveHost On
    ProxyRequests Off

    <Location />
        ProxyPass http://127.0.0.1:8000/
        ProxyPassReverse http://127.0.0.1:8000/
    </Location>

    ErrorLog ${APACHE_LOG_DIR}/api.climbat.net-error.log
    CustomLog ${APACHE_LOG_DIR}/api.climbat.net-access.log combined

    ProxyTimeout 300
    Timeout 300
</VirtualHost>
```

### 4.3 Activar sitio y SSL

```bash
sudo a2ensite api.climbat.net.conf
sudo systemctl reload apache2

# SSL con Let's Encrypt
sudo certbot --apache -d api.climbat.net

# Verificar renovación automática
sudo certbot renew --dry-run
```

---

## 5. Servicio systemd

La API debe correr como servicio permanente para que inicie automáticamente al reiniciar el servidor.

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
ExecStart=/home/prosuco/SINAGERSAT/BaseData/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/home/prosuco/SINAGERSAT/BaseData/venv/bin:/usr/bin:/bin
EnvironmentFile=/home/prosuco/SINAGERSAT/BaseData/.env

[Install]
WantedBy=multi-user.target
```

**Nota:** El `ExecStart` usa `--host 127.0.0.1` porque Apache está enfrente. Si se quiere exponer directo sin Apache, cambiar a `--host 0.0.0.0` o `--host 10.10.0.24`.

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

# Recargar Apache
sudo systemctl reload apache2

# Verificar SSL
sudo certbot renew --dry-run
```

---

## 8. Solución de problemas

| Problema | Causa posible | Solución |
|----------|---------------|----------|
| `Connection refused` al acceder por dominio | Apache no está corriendo | `sudo systemctl start apache2` |
| `502 Bad Gateway` | Uvicorn no está corriendo | `sudo systemctl restart sinagersat-api` |
| El dominio no resuelve | DNS no configurado | Agregar registro A: `api.climbat.net → 10.10.0.24` |
| SSL no funciona | Certificado vencido | `sudo certbot renew` |
| No se puede conectar a la BD | PostgreSQL caído | `sudo systemctl restart postgresql` |
| La API responde lento | Pocos workers | Aumentar `--workers` en el servicio systemd |
