# despliegue/ — Paquete de despliegue SINAGERSAT

Carpeta **autónoma** para desplegar y actualizar SINAGERSAT en otro servidor: PostgreSQL con todos los esquemas, API principal y MotorIA embeddings.

> **No modifica los archivos existentes del repo.** Todos los scripts son propios e independientes de `deploy/`.

## Contenido

```
despliegue/
├── README.md                 ← este archivo
├── dump/                     ← dump de la BD en partes comprimidas (8 esquemas + postgis + vector)
│   ├── db_sinagersat_YYYYMMDD_HHMMSS.sql.gz.00   (~40MB)
│   ├── db_sinagersat_YYYYMMDD_HHMMSS.sql.gz.01   (~40MB)
│   ├── db_sinagersat_YYYYMMDD_HHMMSS.sql.gz.02   (~30MB)
│   └── .gitignore            ← el .sql crudo no se sube (reconstruible)
├── migraciones/              ← 109 migraciones SQL (v1.2.0 → v2.63.1) copiadas en orden
├── scripts/                  ← comandos de instalación y actualización
│   ├── 00_requisitos.sh      ← verificar SO, recursos, puertos
│   ├── 01_instalar_postgres.sh ← PostgreSQL 16 + PostGIS + pgvector + ffmpeg
│   ├── 02_restaurar_bd.sh    ← crear usuario/BD y restaurar dump (auto-ensambla partes)
│   ├── 03_instalar_api.sh    ← venv + requirements.txt (torch CPU)
│   ├── 04_configurar_env.sh  ← generar .env con tokens aleatorios
│   ├── 05_instalar_servicios.sh ← unidades systemd (rutas dinámicas)
│   ├── 06_verificar.sh       ← health-check completo
│   ├── desplegar_todo.sh     ← orquestador: 00→06 de una vez
│   ├── actualizar.sh         ← actualización segura (backup + migraciones + reinicio)
│   ├── ensamblar_dump.sh     ← unir partes .gz.?? → dump .sql
│   └── generar_dump.sh       ← regenerar dump cuando la BD cambia
└── docs/                     ← documentación de despliegue
    ├── 01_requisitos_sistema.md   ← SO, hardware, versiones, workers
    ├── 02_despliegue_desde_cero.md ← guía paso a paso
    ├── 03_actualizacion.md        ← vía ZIP y vía GitHub
    ├── 04_workers.md              ← rendimiento y ajuste de workers
    ├── 05_verificacion.md         ← checklist post-despliegue
    └── 06_rollback.md             ← cómo volver atrás
```

## Despliegue rápido (servidor nuevo)

```bash
# 1. Copiar el proyecto completo al servidor (código + despliegue/)
# 2. Desplegar todo (auto-ensambla el dump si está en partes)
sudo bash despliegue/scripts/desplegar_todo.sh

# 3. Verificar
bash despliegue/scripts/06_verificar.sh
```

### Dump por partes (GitHub)

El dump está dividido en 3 partes comprimidas (`*.sql.gz.00/01/02`, <50MB c/u)
por el límite de 100MB por archivo de GitHub. `02_restaurar_bd.sh` las detecta
y ensambla automáticamente; también se puede hacer manualmente:

```bash
bash despliegue/scripts/ensamblar_dump.sh
# Une las partes → valida gzip → descomprime → db_sinagersat_*.sql
```

## Actualización (servidor ya desplegado)

```bash
sudo bash despliegue/scripts/actualizar.sh
```

Ver `docs/03_actualizacion.md` para las dos vías (ZIP / GitHub).

## Requisitos resumidos

| | Mínimo | Recomendado |
|---|---|---|
| SO | Ubuntu 22.04 / Debian 12 | **Ubuntu 24.04 LTS** |
| CPU | 4 vCPU | 6 vCPU |
| RAM | 4 GB | 8 GB |
| Disco | 40 GB | 80 GB |
| Python | 3.10+ | 3.12 |
| PostgreSQL | 14+ | **16 + PostGIS 3 + pgvector** |

Detalles en `docs/01_requisitos_sistema.md`.

## Qué contiene el dump

Dump generado el **2026-11-05** desde el entorno de desarrollo
(406MB SQL → 110MB gzip → 3 partes en git):

- **8 esquemas:** `edan`, `motor_ia`, `rea`, `repositorio`, `rida`, `shared`, `sinb`, `usuarios`
- **Extensiones:** PostGIS 3.4.2, pgvector 0.6.0
- **Datos:** geografía INE completa (9 deptos, ~113 provs, ~343 munis), censo 2024, datos de prueba de todos los módulos
- **MotorIA:** esquema completo (documentos, chunks, proveedores LLM)
- **Catálogos completos:** RBAC (15 roles, 123 permisos), catálogos EDAN/RIDA/SINB, 21k comunidades, 247k manzanos

## Regenerar el dump (cuando la BD cambia)

```bash
# 1. Generar dump nuevo
bash despliegue/scripts/generar_dump.sh

# 2. Comprimir y trocear para GitHub (<50MB por parte)
cd despliegue/dump
gzip -9 -k db_sinagersat_*.sql          # si no existe ya el .gz
split -b 40m -d -a 2 db_sinagersat_*.sql.gz db_sinagersat_*.sql.gz.
rm -f db_sinagersat_*.sql.gz            # limpiar .gz intermedio
cd ../..
```

Conserva los últimos 3 dumps y valida contenido (PostGIS + esquemas).

## Empaquetar en ZIP

```bash
# ZIP completo (con dump en partes, para primer despliegue, ~130MB)
zip -r sinagersat-despliegue-$(date +%Y%m%d).zip \
  api/ services/ requirements.txt despliegue/ \
  start_api.sh stop.sh \
  -x "*/__pycache__/*" "*.pyc" "*/venv/*" "despliegue/dump/*.sql"

# ZIP de actualización (sin dump, ~15MB)
zip -r sinagersat-actualizacion-$(date +%Y%m%d).zip \
  api/ services/ requirements.txt \
  despliegue/scripts/ despliegue/migraciones/ despliegue/docs/ \
  -x "*/__pycache__/*" "*.pyc" "*/venv/*"
```

## Notas importantes

- **Credenciales por defecto:** BD `sinagersat:12345678`, solo para desarrollo. Cambiar en producción.
- **`.env`** se genera con tokens aleatorios; no está incluido en el paquete.
- **Los servicios** se instalan en systemd con rutas dinámicas (detectan la ubicación real del proyecto).
- **Workers:** API 3, embeddings 2 (ver `docs/04_workers.md`).
- **Puertos:** 8000 (API), 8001 (embeddings, solo local), 5432 (PostgreSQL).

## Documentación relacionada

- Requisitos completos: `docs/01_requisitos_sistema.md`
- Guía de despliegue: `docs/02_despliegue_desde_cero.md`
- Actualizaciones: `docs/03_actualizacion.md`
- Verificación: `docs/05_verificacion.md`
- Rollback: `docs/06_rollback.md`
