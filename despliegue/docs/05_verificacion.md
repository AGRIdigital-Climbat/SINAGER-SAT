# Verificación post-despliegue — SINAGERSAT

Comandos para comprobar que el despliegue o actualización funcionó correctamente.

## 1. Verificación automática

```bash
bash despliegue/scripts/06_verificar.sh
```

Debe mostrar todos los checks en `[OK]` y terminar con `DESPLIEGUE VERIFICADO CORRECTAMENTE`.

## 2. Verificación manual paso a paso

### 2.1 PostgreSQL

```bash
pg_isready
# Expected: accepting connections

psql --version
# Expected: psql (PostgreSQL) 16.x
```

### 2.2 Conexión y esquemas

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema')
ORDER BY schema_name;"
```

**Esquemas esperados (8):**

| # | Esquema | Contenido |
|---|---|---|
| 1 | `edan` | Evaluación de daños y necesidades |
| 2 | `motor_ia` | IA RAG (documentos, chunks, embeddings) |
| 3 | `rea` | Reportes de eventos adversos |
| 4 | `repositorio` | Documentos PDF vinculados |
| 5 | `rida` | Registro de damnificados |
| 6 | `shared` | Geografía INE + censo + catálogos |
| 7 | `sinb` | Indicadores bioculturales |
| 8 | `usuarios` | Cuentas, roles, permisos |

### 2.3 Extensiones

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('postgis','vector') ORDER BY extname;"
```

**Esperado:**

| extname | extversion |
|---|---|
| postgis | 3.x |
| vector | 0.x |

### 2.4 Datos de geografía

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "
SELECT
  (SELECT COUNT(*) FROM shared.departamento) AS deptos,
  (SELECT COUNT(*) FROM shared.provincia) AS provs,
  (SELECT COUNT(*) FROM shared.municipio) AS munis;"
```

**Esperado:** ~9 deptos, ~113 provs, ~343 munis.

### 2.5 Conteo total de tablas

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "
SELECT table_schema, COUNT(*) AS tablas
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
GROUP BY table_schema ORDER BY table_schema;"
```

### 2.6 MotorIA

```bash
PGPASSWORD=12345678 psql -U sinagersat -d db_sinagersat -h 127.0.0.1 -c "
SELECT 'documentos' AS tabla, COUNT(*) FROM motor_ia.documentos
UNION ALL SELECT 'chunks', COUNT(*) FROM motor_ia.chunks
UNION ALL SELECT 'tipos_documento', COUNT(*) FROM motor_ia.tipos_documento;"
```

## 3. Servicios systemd

```bash
systemctl status sinagersat-api --no-pager
systemctl status motoria-embeddings --no-pager
```

**Esperado:** `Active: active (running)` en ambos.

Si fallan:

```bash
journalctl -u sinagersat-api -n 50 --no-pager
journalctl -u motoria-embeddings -n 50 --no-pager
```

## 4. API HTTP

```bash
# Health check
curl -s http://localhost:8000/health
# Expected: JSON con status ok

# Página raíz
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
# Expected: 200

# Swagger UI
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs
# Expected: 200

# Spec OpenAPI
curl -s http://localhost:8000/openapi.json | head -c 200
# Expected: {"openapi": ...

# Desde fuera del servidor
curl -s http://<IP-SERVIDOR>:8000/health
```

## 5. MotorIA embeddings

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/docs
# Expected: 200

systemctl status motoria-embeddings --no-pager
```

## 6. Puerto y firewall

```bash
ss -tlnp | grep -E ':(8000|8001|5432)'
# Expected: uvicorn en 8000, 8001, postgres en 5432

# Si hay ufw:
sudo ufw status | grep -E '8000|5432'
```

## 7. Prueba funcional mínima

```bash
# Login (si tienes credenciales de prueba)
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ADMIN","password":"..."}'

# O consultar un catálogo público/geografía
curl -s http://localhost:8000/api/v2/shared/departamentos | head -c 500
```

## Checklist resumido

- [ ] `06_verificar.sh` todo en `[OK]`
- [ ] 8 esquemas presentes
- [ ] postgis + vector instaladas
- [ ] ≥9 deptos, ≥343 munis
- [ ] `sinagersat-api` active (running)
- [ ] `motoria-embeddings` active (running)
- [ ] `GET /health` → 200
- [ ] `GET /docs` → 200
- [ ] Puerto 8000 escuchando
- [ ] Logs sin errores críticos (`journalctl -u sinagersat-api -n 20`)

## Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| `FALLO: Esquema faltante` | Dump no restaurado | `sudo bash despliegue/scripts/02_restaurar_bd.sh` |
| `Extensión vector no instalada` | Falta pgvector | `sudo apt install postgresql-16-pgvector` + reiniciar PG |
| API no responde :8000 | Servicio caído | `sudo systemctl start sinagersat-api` + logs |
| 500 en endpoints geo | PostGIS faltante | Verificar extensión postgis |
| Embeddings no responden | Servicio caído | `sudo systemctl start motoria-embeddings` |
| `FATAL: password authentication failed` | Password BD cambió | Revisar `.env` DATABASE_URL |
| OOM / workers reiniciando | RAM insuficiente | Reducir workers (ver `04_workers.md`) |
