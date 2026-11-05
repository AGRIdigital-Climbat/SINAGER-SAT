# Rollback — SINAGERSAT

Cómo volver a una versión anterior del despliegue (código, BD o ambos).

## Cuándo hacer rollback

- Una actualización rompió la API
- Una migración causó errores
- Se necesita volver al estado anterior documentado

## Opción 1: Rollback solo de código (sin tocar BD)

Útil si el problema está en el código nuevo pero el esquema de BD es compatible.

### Vía git

```bash
cd /home/<usuario>/SINAGERSAT/BaseData

# Ver historial
git log --oneline -10

# Volver al commit anterior
git checkout <commit-anterior>

# O a la rama anterior
git checkout v1.4.0

# Reiniciar servicios
sudo systemctl restart sinagersat-api
sudo systemctl restart motoria-embeddings

# Verificar
bash despliegue/scripts/06_verificar.sh
```

### Vía ZIP

1. Tener el ZIP de la versión anterior (`sinagersat-actualizacion-AAAA-MM-DD.zip`).
2. Descomprimir sobre el proyecto:
   ```bash
   unzip -o /tmp/sinagersat-actualizacion-ANTERIOR.zip
   ```
3. Reiniciar:
   ```bash
   sudo systemctl restart sinagersat-api
   ```

## Opción 2: Rollback de BD + código

**⚠️ PELIGRO:** restaurar un dump antiguo **elimina los datos posteriores** al backup. Crear siempre un backup del estado actual antes.

### Paso 1: Backup del estado actual (si no existe)

```bash
PGPASSWORD=12345678 pg_dump -h 127.0.0.1 -U sinagersat -d db_sinagersat \
  --no-owner --no-privileges \
  -f backups/pre_rollback_$(date +%Y%m%d_%H%M%S).sql
```

### Paso 2: Restaurar el dump anterior

```bash
# Colocar el dump anterior en despliegue/dump/
cp /ruta/al/dump-anterior.sql despliegue/dump/

# Restaurar (ELIMINA la BD actual y la recrea desde el dump)
sudo bash despliegue/scripts/02_restaurar_bd.sh
```

### Paso 3: Código anterior

```bash
git checkout <commit-anterior>
# o unzip del ZIP anterior
```

### Paso 4: Reiniciar y verificar

```bash
sudo systemctl restart sinagersat-api
sudo systemctl restart motoria-embeddings
bash despliegue/scripts/06_verificar.sh
```

## Opción 3: Rollback de una migración puntual

Si solo una migración causó el problema, usar su archivo `*_rollback.sql` si existe:

```bash
# Ver si hay rollback disponible
ls despliegue/migraciones/*rollback*.sql

# Aplicar el rollback específico
PGPASSWORD=12345678 psql -h 127.0.0.1 -U sinagersat -d db_sinagersat \
  -f despliegue/migraciones/vX.Y.Z_nombre_rollback.sql

# Reiniciar
sudo systemctl restart sinagersat-api
```

> No todas las migraciones tienen rollback. Revisar el archivo antes.

## Dónde están los backups

| Tipo | Ubicación | Generado por |
|---|---|---|
| Pre-actualización | `backups/pre_update_YYYYMMDD_HHMMSS.sql` | `actualizar.sh` |
| Pre-rollback | `backups/pre_rollback_YYYYMMDD_HHMMSS.sql` | manual (arriba) |
| Dump del paquete | `despliegue/dump/db_sinagersat_YYYYMMDD_HHMMSS.sql` | `generar_dump.sh` |
| Backups históricos | `backups/*.dump`, `backups/*.sql` | manuales |

## Checklist de rollback

- [ ] Identificar la causa (código vs BD vs migración)
- [ ] Backup del estado actual creado
- [ ] Restaurar solo lo necesario (código o BD o ambos)
- [ ] `sudo systemctl restart` de servicios
- [ ] `bash despliegue/scripts/06_verificar.sh`
- [ ] Probar endpoints críticos (`/health`, login, geografía)
- [ ] Documentar qué falló para la siguiente actualización

## Recuperación de desastres (servidor perdido)

Si el servidor de producción se pierde, reconstruir desde cero:

```bash
# 1. Servidor nuevo Ubuntu 24.04
# 2. Copiar carpeta completa (código + despliegue/)
# 3. Desplegar
sudo bash despliegue/scripts/desplegar_todo.sh
# 4. Restaurar el dump MÁS RECIENTE si no está en el paquete
# 5. Verificar
bash despliegue/scripts/06_verificar.sh
```
