# SINAGERSAT - Cloudflare Tunnel con Dominio Fijo

## Problema Actual

El servidor usa **Cloudflare Quick Tunnel** (`trycloudflare.com`), que genera URLs aleatorias
como `showed-hockey-tag-klein.trycloudflare.com` que cambian cada reinicio.

**Solución**: Cloudflare **Named Tunnel** con dominio fijo (ej: `api.sinagersat.com`).

---

## ¿Cómo funciona?

```
[Servidor SINAGERSAT :8000] ──tunnel saliente──▶ [Cloudflare Edge] ──dominio──▶ [Usuario final]
     (sin IP pública)                              (sin IP pública)
```

- El servidor **inicia una conexión saliente** hacia Cloudflare (no necesita IP pública)
- Cloudflare recibe el tráfico y lo enruta por el tunnel hacia `localhost:8000`
- El usuario accede mediante el dominio estable

---

## Requisitos

1. **Dominio registrado** (ej: `sinagersat.com`)
2. **Cuenta de Cloudflare** con el dominio agregado (nameservers apuntando a CF)
3. **cloudflared** instalado en el servidor (ya está: v2026.7.2)

---

## Guía de Configuración

### Paso 1: Login a Cloudflare (desde el servidor)

```bash
cloudflared tunnel login
```

Esto abre un navegador. Inicia sesión en Cloudflare y selecciona el dominio.
Se genera el archivo `~/.cloudflared/cert.pem`.

### Paso 2: Crear el Named Tunnel

```bash
cloudflared tunnel create sinagersat
```

Esto genera:
- `~/.cloudflared/<TUNNEL_ID>.json` (credenciales)
- El TUNNEL_ID (anotar, Ej: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

### Paso 3: Configurar DNS

```bash
# Crear registro DNS que apunte al tunnel
cloudflared tunnel route dns sinagersat api.sinagersat.com
```

Esto crea automáticamente en Cloudflare:
```
api.sinagersat.com  →  CNAME  →  <TUNNEL_ID>.cfargotunnel.com
```

### Paso 4: Crear archivo de configuración

```bash
mkdir -p ~/.cloudflared
```

Crear `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/climbat/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.sinagersat.com
    service: http://localhost:8000
    originRequest:
      noTLSVerify: true
  - service: http_status:404
```

**Nota**: Reemplazar `<TUNNEL_ID>` con el ID real del tunnel.

### Paso 5: Probar el tunnel manualmente

```bash
cloudflared tunnel run sinagersat
```

Verificar:
```bash
curl https://api.sinagersat.com/health
curl https://api.sinagersat.com/docs
```

### Paso 6: Configurar como servicio systemd

```bash
sudo cp /etc/systemd/system/sinagersat-tunnel.service /etc/systemd/system/sinagersat-tunnel.service.bak
```

Editar `/etc/systemd/system/sinagersat-tunnel.service`:

```ini
[Unit]
Description=SINAGERSAT Cloudflare Tunnel (Named)
After=network-online.target sinagersat-api.service
Wants=network-online.target sinagersat-api.service

[Service]
Type=simple
User=climbat
Group=climbat
ExecStartPre=/bin/bash -c 'until curl -sf http://localhost:8000/ > /dev/null; do sleep 2; done'
ExecStart=/usr/local/bin/cloudflared tunnel run sinagersat
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart sinagersat-tunnel
sudo systemctl status sinagersat-tunnel
```

### Paso 7: Verificar

```bash
# Verificar que el servicio está activo
sudo systemctl status sinagersat-tunnel

# Verificar que la API responde por el dominio
curl https://api.sinagersat.com/
curl https://api.sinagersat.com/health
curl https://api.sinagersat.com/docs

# Verificar logs
sudo journalctl -u sinagersat-tunnel -f
```

---

## Comandos Útiles

```bash
# Ver tunnels existentes
cloudflared tunnel list

# Ver info de un tunnel
cloudflared tunnel info sinagersat

# Eliminar un tunnel
cloudflared tunnel delete sinagersat

# Verificar DNS
dig api.sinagersat.com

# Logs del servicio
sudo journalctl -u sinagersat-tunnel -f
sudo tail -f /tmp/cloudflared.log
```

---

## Estructura de archivos

```
~/.cloudflared/
├── cert.pem                    # Certificado de login
├── <TUNNEL_ID>.json            # Credenciales del tunnel
└── config.yml                  # Configuración del tunnel
```

---

## Notas Importantes

1. **No se necesita IP pública** - El tunnel funciona con conexión saliente
2. **SSL/TLS es automático** - Cloudflare maneja los certificados
3. **El dominio puede tener subdominios** - `api.sinagersat.com`, `app.sinagersat.com`, etc.
4. **Los Quick Tunnel siguen funcionando** - Para pruebas rápidas sin configuración
5. **El Named Tunnel es para producción** - URLs estables, sin cambios

---

## Respuesta para proveedor (Wilsol)

```
Buenas tardes Wilson,

Para configurar el dominio con Cloudflare, necesitamos:

1. El dominio debe estar agregado en Cloudflare (cambiar nameservers del registrador)
   - Cloudflare provee 2 nameservers (ej: ns1.cloudflare.com, ns2.cloudflare.com)
   - Se configuran donde se compró el dominio

2. Desde nuestro servidor ejecutaremos:
   cloudflared tunnel login (seleccionar el dominio)
   cloudflared tunnel create sinagersat
   cloudflared tunnel route dns sinagersat api.{dominio}

3. Nosotros configuramos el tunnel en el servidor

No necesitamos IP pública. Cloudflare Tunnel funciona con una conexión
saliente desde nuestro servidor hacia Cloudflare. El tráfico ingresa
por el tunnel y se enruta a nuestra API.

¿Qué dominio van a usar? (ej: sinagersat.com, climbat.com)
¿Quién administra la cuenta de Cloudflare?
```

---

## Checklist

- [ ] Dominio comprado
- [ ] Dominio agregado a Cloudflare
- [ ] Nameservers actualizados en el registrador
- [ ] `cloudflared tunnel login` ejecutado
- [ ] Named tunnel creado
- [ ] DNS configurado
- [ ] `config.yml` creado
- [ ] Tunnel probado manualmente
- [ ] Servicio systemd configurado
- [ ] Verificado con curl https://api.{dominio}/
