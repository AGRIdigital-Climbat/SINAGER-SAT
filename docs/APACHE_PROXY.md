# SINAGERSAT API — Despliegue con Apache Proxy + Dominio HTTPS

**Versión:** 1.3.0  
**Propósito:** Documento para entregar al proveedor de hosting. Describe cómo vincular la API de SINAGERSAT con Apache y un dominio con SSL.

---

## 1. Arquitectura

```
Usuario → Dominio (HTTPS) → Apache (puerto 443) → ProxyPass → Uvicorn (puerto 8000)
                                                                  → PostgreSQL (puerto 5432)
```

- **Apache** recibe peticiones HTTPS y las redirige a la API interna.
- **Uvicorn** (FastAPI/Python) corre en `localhost:8000`.
- **PostgreSQL** corre en `localhost:5432`.

---

## 2. Datos del Servidor

| Ítem | Valor |
|------|-------|
| IP del servidor | `10.10.0.24` |
| Sistema operativo | Ubuntu 24.04.4 LTS |
| Usuario del sistema | `prosuco` |
| Ruta del proyecto | `/home/prosuco/SINAGERSAT/BaseData` |
| Puerto API interna | `8000` |
| Puerto PostgreSQL | `5432` |

---

## 3. Credenciales de la Base de Datos

| Parámetro | Valor |
|-----------|-------|
| Host | `127.0.0.1` (solo conexiones locales) |
| Puerto | `5432` |
| Base de datos | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

**Verificar conexión:**
```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "SELECT 'OK' as conexion;"
```

**Herramientas externas (DBeaver, pgAdmin4):**  
Conectar a `10.10.0.24:5432` con usuario `sinagersat` y contraseña `12345678`. Usar autenticación `scram-sha-256`.

---

## 4. Archivo de Variables de Entorno

**Ruta:** `/home/prosuco/SINAGERSAT/BaseData/.env`

```
DATABASE_URL=postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat
JWT_SECRET=sinagersat-secret-key-change-in-production-2026
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

---

## 5. Configuración de Apache

### 5.1 Requisitos

```bash
sudo apt-get install -y apache2 certbot python3-certbot-apache
sudo a2enmod proxy proxy_http proxy_wstunnel ssl rewrite headers
sudo systemctl restart apache2
```

### 5.2 VirtualHost con SSL

Reemplazar `midominio.com` por el dominio real.

**Archivo:** `/etc/apache2/sites-available/sinagersat.conf`

```apache
<VirtualHost *:80>
    ServerName midominio.com
    Redirect permanent / https://midominio.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName midominio.com
    ServerAdmin admin@midominio.com

    # --- SSL (Let's Encrypt) ---
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/midominio.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/midominio.com/privkey.pem

    # --- Seguridad ---
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"

    # --- Proxy a la API interna (uvicorn en puerto 8000) ---
    ProxyPreserveHost On
    ProxyRequests Off

    <Location />
        ProxyPass http://127.0.0.1:8000/
        ProxyPassReverse http://127.0.0.1:8000/
    </Location>

    # --- WebSocket (opcional, si se usa en el futuro) ---
    <Location /ws>
        ProxyPass ws://127.0.0.1:8000/ws
        ProxyPassReverse ws://127.0.0.1:8000/ws
    </Location>

    # --- Logs ---
    ErrorLog ${APACHE_LOG_DIR}/sinagersat-error.log
    CustomLog ${APACHE_LOG_DIR}/sinagersat-access.log combined

    # --- Timeouts ---
    ProxyTimeout 300
    Timeout 300
</VirtualHost>
```

**Activar sitio:**
```bash
sudo a2ensite sinagersat.conf
sudo systemctl reload apache2
```

### 5.3 SSL con Let's Encrypt

```bash
sudo certbot --apache -d midominio.com
```

La renovación automática viene configurada por defecto:
```bash
sudo certbot renew --dry-run
```

---

## 6. Servicio systemd de la API

La API debe correr como servicio permanente. El archivo de unidad ya existe.

**Archivo:** `/home/prosuco/SINAGERSAT/BaseData/deploy/systemd/sinagersat-api.service`

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

**Instalar y activar:**
```bash
sudo cp /home/prosuco/SINAGERSAT/BaseData/deploy/systemd/sinagersat-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sinagersat-api
sudo systemctl start sinagersat-api
```

**Comandos útiles:**
```bash
sudo systemctl status sinagersat-api          # Estado
sudo systemctl restart sinagersat-api         # Reiniciar
journalctl -u sinagersat-api -f               # Logs en tiempo real
```

---

## 7. Verificar que todo funciona

```bash
# Interno (en el servidor)
curl -s http://127.0.0.1:8000/          # → {"name":"SINAGERSAT API","version":"1.3.0",...}
curl -s http://127.0.0.1:8000/health   # → {"status":"ok"}

# Externo (vía dominio)
curl -s https://midominio.com/          # → {"name":"SINAGERSAT API","version":"1.3.0",...}
curl -s https://midominio.com/health    # → {"status":"ok"}
curl -s https://midominio.com/docs      # → Swagger UI
```

---

## 8. Endpoints públicos

| Ruta | Descripción |
|------|-------------|
| `/` | Información de la API |
| `/health` | Health check |
| `/docs` | Swagger UI (documentación interactiva) |
| `/redoc` | ReDoc (documentación alternativa) |
| `/openapi.json` | Esquema OpenAPI |
| `/api/v1/auth/*` | Autenticación (público) |
| `/api/v1/shared/*` | Geografía (público) |
| `/api/v1/edan/*` | Formularios EDAN (requiere token) |
| `/api/v1/rea/*` | Reportes de Eventos (requiere token) |
| `/api/v1/usuarios/*` | Gestión de usuarios (requiere token) |
| `/api/v1/upload/*` | Subida de archivos (requiere token) |
| `/uploads/*` | Archivos estáticos (imágenes) |

---

## 9. Notas para el proveedor de hosting

- La API **no necesita PHP ni Node.js**. Solo Python 3.12 + PostgreSQL 16.
- Apache solo actúa como **proxy inverso** — no se ejecuta código en Apache.
- La API ya incluye **CORS abierto** (`Access-Control-Allow-Origin: *`) para cualquier frontend.
- El servidor ya tiene la base de datos restaurada con **40 tablas**, **8 departamentos**, **112 provincias** y **340 municipios**.
- Para cambiar el `JWT_SECRET` en producción, editar `/home/prosuco/SINAGERSAT/BaseData/.env` y reiniciar el servicio.

---

## 10. Resumen de comandos

```bash
# Iniciar API manual
cd /home/prosuco/SINAGERSAT/BaseData && bash start_api.sh

# Verificar base de datos
cd /home/prosuco/SINAGERSAT/BaseData && bash deploy/verificar.sh

# Servicio systemd
sudo systemctl start|stop|restart|status sinagersat-api

# Logs
journalctl -u sinagersat-api -f

# Recargar Apache
sudo systemctl reload apache2
```
