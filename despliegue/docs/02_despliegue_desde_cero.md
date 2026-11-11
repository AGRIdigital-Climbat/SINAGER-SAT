# Despliegue desde cero — SINAGERSAT

Guía paso a paso para instalar SINAGERSAT completo en un servidor nuevo: PostgreSQL con todos los esquemas, API principal y MotorIA embeddings.

## Prerrequisitos

- Servidor Ubuntu 24.04 LTS (ver `01_requisitos_sistema.md`)
- Carpeta `despliegue/` + código del proyecto (`api/`, `services/`, `requirements.txt`)
- Acceso root (sudo)
- Conexión a internet

## Estructura esperada en el servidor

```
/home/<usuario>/SINAGERSAT/BaseData/
├── api/                    ← código de la API
├── services/               ← MotorIA embeddings
├── requirements.txt
├── despliegue/             ← ESTA CARPETA
│   ├── dump/               ← dump de BD (3 partes .sql.gz.?? si viene de GitHub)
│   ├── migraciones/        ← migraciones SQL
│   ├── scripts/            ← comandos de instalación
│   └── docs/               ← esta documentación
└── ...
```

## Opción A: despliegue completo automatizado (recomendado)

```bash
cd /home/<usuario>/SINAGERSAT/BaseData

# 1. Verificar requisitos (opcional pero recomendado)
bash despliegue/scripts/00_requisitos.sh

# 2. Desplegar todo (postgres + BD + API + servicios)
sudo bash despliegue/scripts/desplegar_todo.sh
```

El orquestador ejecuta en orden:

| Paso | Script | Qué hace |
|---|---|---|
| 1 | `00_requisitos.sh` | Verifica SO, recursos, Python, puertos |
| 2 | `01_instalar_postgres.sh` | Instala PostgreSQL 16 + PostGIS + pgvector + ffmpeg |
| 3 | `02_restaurar_bd.sh` | Crea usuario/BD y restaura el dump (8 esquemas) |
| 4 | `03_instalar_api.sh` | Crea venv e instala requirements.txt (torch CPU) |
| 5 | `04_configurar_env.sh` | Genera `.env` con tokens aleatorios |
| 6 | `05_instalar_servicios.sh` | Instala unidades systemd (API :8000, embeddings :8001) |
| 7 | `06_verificar.sh` | Comprueba BD, esquemas, extensiones y servicios |

### Modos parciales

```bash
sudo bash despliegue/scripts/desplegar_todo.sh --db-only    # solo PostgreSQL + BD
sudo bash despliegue/scripts/desplegar_todo.sh --api-only   # solo API (si PG ya está)
sudo bash despliegue/scripts/desplegar_todo.sh --no-verify  # sin verificación final
```

## Opción B: paso a paso manual

Si prefieres ejecutar cada comando por separado:

```bash
cd /home/<usuario>/SINAGERSAT/BaseData

# 1. Requisitos
bash despliegue/scripts/00_requisitos.sh

# 2. PostgreSQL + PostGIS + pgvector + ffmpeg
sudo bash despliegue/scripts/01_instalar_postgres.sh

# 3. Restaurar BD (dump con todos los esquemas)
#    Si el dump está en partes (desde GitHub), ensamblar primero:
#      bash despliegue/scripts/ensamblar_dump.sh
#    (o directamente: 02_restaurar_bd.sh auto-detecta las partes)
sudo bash despliegue/scripts/02_restaurar_bd.sh

# 4. Entorno Python + dependencias
bash despliegue/scripts/03_instalar_api.sh

# 5. Archivo .env
bash despliegue/scripts/04_configurar_env.sh

# 6. Servicios systemd
sudo bash despliegue/scripts/05_instalar_servicios.sh

# 7. Verificación
bash despliegue/scripts/06_verificar.sh
```

## Verificación final

La verificación debe mostrar todo en `[OK]`:

```bash
bash despliegue/scripts/06_verificar.sh
```

Comprueba:

- [ ] PostgreSQL corriendo
- [ ] Conexión a `db_sinagersat`
- [ ] 8 esquemas: `edan`, `motor_ia`, `rea`, `repositorio`, `rida`, `shared`, `sinb`, `usuarios`
- [ ] Extensiones `postgis` y `vector`
- [ ] Conteos de geografía (deptos/provs/munis)
- [ ] Servicios systemd activos
- [ ] API respondiendo en `:8000`
- [ ] Swagger en `http://localhost:8000/docs`
- [ ] Embeddings en `:8001`

## URLs de acceso

| Servicio | URL |
|---|---|
| API | `http://<IP-SERVIDOR>:8000` |
| Swagger UI (selector) | `http://<IP-SERVIDOR>:8000/docs` |
| Docs API v1 | `http://<IP-SERVIDOR>:8000/docs/v1` |
| Docs API v2 | `http://<IP-SERVIDOR>:8000/docs/v2` |
| Health check | `http://<IP-SERVIDOR>:8000/health` |
| MotorIA embeddings | `http://127.0.0.1:8001/docs` (solo local) |

## Gestión de servicios

```bash
# Estado
systemctl status sinagersat-api
systemctl status motoria-embeddings

# Reiniciar
sudo systemctl restart sinagersat-api
sudo systemctl restart motoria-embeddings

# Logs en vivo
journalctl -u sinagersat-api -f
journalctl -u motoria-embeddings -f

# Detener
sudo systemctl stop sinagersat-api
sudo systemctl stop motoria-embeddings

# Deshabilitar arranque automático
sudo systemctl disable sinagersat-api
```

## Conexión a la base de datos

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1
```

| Parámetro | Valor |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `5432` |
| Base | `db_sinagersat` |
| Usuario | `sinagersat` |
| Contraseña | `12345678` |

> **Producción:** cambia la contraseña de BD y `JWT_SECRET` en `.env` tras el primer despliegue.

## Configuración post-instalación

1. **Editar `.env`:**
   ```bash
   nano .env
   # - LLM_API_KEY: clave de Groq u otro proveedor (MotorIA)
   # - JWT_SECRET: ya es aleatorio si se generó nuevo
   # - AGETIC_*: si usas firma digital
   ```

2. **Reiniciar tras cambios:**
   ```bash
   sudo systemctl restart sinagersat-api
   ```

## Solución de problemas

| Problema | Solución |
|---|---|
| `psql: command not found` | `sudo bash despliegue/scripts/01_instalar_postgres.sh` |
| Error PostGIS al restaurar | Verificar `postgresql-16-postgis-3` instalado |
| Error `vector` extension | Instalar `postgresql-16-pgvector` |
| API no arranca en :8000 | `journalctl -u sinagersat-api -n 50` |
| 500 en endpoints geo | Falta PostGIS o restauración incompleta |
| MotorIA falla | Verificar `motoria-embeddings` activo y `pgvector` |
| Puerto ocupado | `sudo lsof -i :8000` y detener proceso |

## Siguientes pasos

- Actualizaciones: ver `03_actualizacion.md`
- Workers y rendimiento: ver `04_workers.md`
- Rollback: ver `06_rollback.md`
