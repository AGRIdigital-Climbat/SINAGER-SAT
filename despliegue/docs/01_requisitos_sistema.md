# Requisitos del sistema — SINAGERSAT

Guía de requisitos para desplegar SINAGERSAT en un servidor nuevo (producción o desarrollo).

## Sistema operativo

| | Recomendado | Mínimo soportado |
|---|---|---|
| **SO** | **Ubuntu 24.04 LTS (Noble)** | Ubuntu 22.04 LTS, Debian 12 |
| Arquitectura | x86_64 | x86_64 |

> Ubuntu 24.04 LTS es el entorno de desarrollo y prueba actual del sistema. Es la opción recomendada por ser la versión en la que todo está verificado.

También funciona en derivados Ubuntu (Linux Mint 21+, Zorin OS 17+) y Debian 11+.

## Recursos del servidor

| Recurso | Mínimo | Recomendado | Entorno actual (dev) |
|---|---|---|---|
| **CPU** | 4 vCPU | 6+ vCPU | 6 vCPU (QEMU @ 2.0GHz) |
| **RAM** | 4 GB | 8 GB | 5.8 GB + 4 GB swap |
| **Disco** | 40 GB SSD | 80 GB SSD | 136 GB (33 GB en uso) |
| **Red** | Puerto 8000/8001/5432 accesibles | + 443 si hay HTTPS | — |

Desglose de disco estimado:

| Componente | Tamaño aprox. |
|---|---|
| Dump de BD (SQL) | ~400 MB |
| BD restaurada en PostgreSQL | ~500 MB – 1 GB |
| venv + dependencias Python (torch CPU, whisper, sentence-transformers) | ~2.5 – 3 GB |
| Código fuente + docs | ~15 MB |
| uploads/ (imágenes de reportes) | crece con el uso |

## Software requerido

El script `01_instalar_postgres.sh` instala todo esto automáticamente:

| Componente | Versión probada | Notas |
|---|---|---|
| **PostgreSQL** | **16.15** | Mínimo 14; 16 recomendado |
| **PostGIS** | **3.4.2** | **Obligatorio** — geometrías de municipios, GeoJSON |
| **pgvector** | **0.6.0** | Requerido por MotorIA (embeddings) |
| **Python** | **3.12.3** | Mínimo 3.10; 3.12 recomendado |
| **ffmpeg** | (distro) | Requerido por Whisper (`/voz`) |
| build-essential, libpq-dev | (distro) | Compilación de psycopg2/bcrypt |
| curl | (distro) | Health-checks |

## Servicios que corren en el servidor

| Servicio | Puerto | Proceso | systemd |
|---|---|---|---|
| API principal | `0.0.0.0:8000` | uvicorn (3 workers) | `sinagersat-api.service` |
| MotorIA embeddings | `127.0.0.1:8001` | uvicorn (2 workers) | `motoria-embeddings.service` |
| PostgreSQL | `5432` | postgres | `postgresql.service` |

### Fórmula de workers

```bash
# Fórmula teórica uvicorn:
workers = (2 × núcleos) + 1     # para 6 núcleos = 13 (máximo teórico)

# Configuración recomendada para 4–6 núcleos / 6–8 GB RAM:
#   API principal:   3 workers  (~150–250 MB c/u)
#   Embeddings:      2 workers
```

Ver `04_workers.md` para detalles de rendimiento y cuándo ajustar.

## Conexiones externas (saliente)

La API consume estos servicios externos; el servidor debe tener salida a internet:

| Servicio | URL | Uso |
|---|---|---|
| Groq LLM | `https://api.groq.com/openai/v1` | MotorIA chat (LLM_MODE=external) |
| EarthSearch STAC | `https://earthsearch.dataspace.copernicus.eu` | NDVI Sentinel-2 (sin API key) |
| Open-Meteo | `https://api.open-meteo.com` | Pronósticos digitales |
| AGETIC (opcional) | `https://validar.firmadigital.bo/backend` | Firma digital |

## Puerto de red

Si hay firewall, abrir:

```bash
sudo ufw allow 8000/tcp    # API (o solo desde IP interna)
# 8001 es solo 127.0.0.1 (no exponer)
# 5432 solo 127.0.0.1 o red interna (no exponer a internet)
```

## Checklist previo al despliegue

- [ ] Ubuntu 22.04+ / Debian 12
- [ ] 4+ vCPU, 4+ GB RAM, 40+ GB disco
- [ ] Acceso root (sudo)
- [ ] Conexión a internet (apt + pip + APIs externas)
- [ ] Carpeta `despliegue/` + código del proyecto completos
- [ ] Puerto 8000 libre
