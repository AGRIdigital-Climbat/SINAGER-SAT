# Actualización del despliegue — SINAGERSAT

Dos vías para actualizar un servidor ya desplegado: **ZIP** (transferencia manual) o **GitHub** (git pull). Ambas usan el mismo script de actualización seguro.

## Flujo seguro de actualización (común a ambas vías)

```bash
cd /home/<usuario>/SINAGERSAT/BaseData
sudo bash despliegue/scripts/actualizar.sh
```

Este script:

1. **Crea backup de la BD** en `backups/pre_update_YYYYMMDD_HHMMSS.sql`
2. **Verifica** que la BD y el código estén accesibles
3. **Actualiza dependencias** Python (`pip install -r requirements.txt`)
4. **Ejecuta migraciones** pendientes de `despliegue/migraciones/`
5. **Reinicia servicios** (`sinagersat-api`, `motoria-embeddings`) con health-check

### Opciones

```bash
sudo bash despliegue/scripts/actualizar.sh --sin-bd   # sin backup de BD (más rápido)
sudo bash despliegue/scripts/actualizar.sh --help     # ayuda
```

---

## Vía A: ZIP (transferencia manual)

Ideal cuando **no hay GitHub** o se actualiza la **base de datos** junto con el código.

### 1. Generar el ZIP de actualización (en este servidor dev)

```bash
cd /home/prosuco/SINAGERSAT/BaseData

# Código + migraciones + docs (sin dump, ~15MB)
zip -r sinagersat-actualizacion-$(date +%Y%m%d).zip \
  api/ services/ requirements.txt \
  despliegue/scripts/ despliegue/migraciones/ despliegue/docs/ \
  despliegue/README.md \
  start_api.sh start_api_safe.sh stop.sh \
  -x "*/__pycache__/*" "*.pyc" "*/venv/*"

# O si la BD también cambió, regenerar dump primero:
bash despliegue/scripts/generar_dump.sh
# (luego incluir despliegue/dump/ en el zip o copiarlo aparte)
```

### 2. Transferir al servidor de producción

```bash
scp sinagersat-actualizacion-YYYYMMDD.zip usuario@SERVIDOR_PROD:/tmp/
# o por USB/medio físico
```

### 3. Aplicar en el servidor de producción

```bash
ssh usuario@SERVIDOR_PROD
cd /home/<usuario>/SINAGERSAT/BaseData

# Descomprimir SOBRE el código existente (sin borrar datos)
unzip -o /tmp/sinagersat-actualizacion-YYYYMMDD.zip

# Actualizar (backup + migraciones + reinicio)
sudo bash despliegue/scripts/actualizar.sh
```

> `-o` sobreescribe archivos modificados pero **no borra** archivos que ya no estén en el ZIP (seguro para uploads/ y .env).

### 4. Si hay dump nuevo (cambios de esquema grandes)

```bash
# Copiar el dump nuevo
cp /tmp/db_sinagersat_YYYYMMDD_HHMMSS.sql despliegue/dump/

# SOLO si es un despliegue nuevo o se acordó regenerar la BD:
# (esto ELIMINA datos actuales — crear backup antes)
# sudo bash despliegue/scripts/02_restaurar_bd.sh
```

**Nota:** en actualizaciones normales **no se restaura el dump**; solo se aplican migraciones. El dump es para despliegue inicial o reconstrucción.

---

## Vía B: GitHub (git pull)

Ideal para **actualizaciones frecuentes de código** sin dump.

### 1. Configurar el servidor de producción (una vez)

```bash
cd /home/<usuario>/SINAGERSAT/BaseData
git remote -v   # debe apuntar a git@github.com:AGRIdigital-Climbat/SINAGER-SAT.git

# Rama de trabajo (la rama viva es estructura-ia)
git fetch origin
git checkout estructura-ia
```

### 2. Actualizar (en cada release)

```bash
cd /home/<usuario>/SINAGERSAT/BaseData

# Guardar cambios locales de .env (no trackeado, pero por seguridad)
cp .env /tmp/env_backup_$(date +%Y%m%d).env

# Traer cambios
git pull origin estructura-ia

# Actualizar migraciones copiadas (si el pull trae nuevas)
# (las migraciones nuevas llegan en database/ — copiarlas al paquete)
ls -1v database/migration_v*.sql database/migrations/*.sql 2>/dev/null \
  | while read f; do cp "$f" despliegue/migraciones/; done

# Aplicar actualización segura
sudo bash despliegue/scripts/actualizar.sh
```

### 3. Restaurar .env si git lo tocara (raro)

```bash
# .env está en .gitignore — git pull no lo modifica normalmente
# Si algo falla:
cp /tmp/env_backup_YYYYMMDD.env .env
sudo systemctl restart sinagersat-api
```

---

## Comparación de vías

| | ZIP | GitHub |
|---|---|---|
| **Ideal para** | Código + BD, actualizaciones puntuales | Código frecuente, sin dump |
| **Requiere** | scp/USB, sin red a GitHub | Acceso a GitHub desde el servidor |
| **Historial** | No | Sí (git log) |
| **Tamaño** | ~15MB (código) / ~400MB (con BD) | Solo delta de commits |
| **Rollback** | ZIP anterior + dump anterior | `git checkout <commit>` |
| **BD** | Incluible en el ZIP | Nunca va en git (usar dump aparte) |

### Recomendación combinada

- **GitHub** para código (actualizaciones frecuentes, historial).
- **ZIP** para la BD (dumps ~400MB no caben en GitHub).
- Siempre ejecutar `actualizar.sh` tras copiar el código nuevo.

---

## Después de cualquier actualización

```bash
# 1. Verificar
bash despliegue/scripts/06_verificar.sh

# 2. Ver logs si algo falló
journalctl -u sinagersat-api -n 50
journalctl -u motoria-embeddings -n 50

# 3. Probar la API
curl -s http://localhost:8000/health
curl -s http://localhost:8000/docs -o /dev/null -w "%{http_code}\n"
```

## Migraciones nuevas (procedimiento)

Cuando se añade una migración en `database/migrations/vX.Y.Z_*.sql`:

1. **En dev:** copiar a `despliegue/migraciones/`:
   ```bash
   cp database/migrations/vX.Y.Z_nuevo.sql despliegue/migraciones/
   ```
2. **Commit** del archivo nuevo (origen + copia en `despliegue/migraciones/`).
3. **En prod:** `git pull` o ZIP + `actualizar.sh` (ejecuta la migración pendiente).

## Rollback

Ver `06_rollback.md`.
