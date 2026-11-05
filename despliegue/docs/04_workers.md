# Workers y rendimiento — SINAGERSAT

Configuración de procesos uvicorn (workers) para la API y MotorIA, y cómo ajustarla según el servidor.

## Hardware de referencia

| | Entorno actual (dev) | Mínimo prod. | Recomendado prod. |
|---|---|---|---|
| CPU | 6 vCPU (QEMU @ 2.0GHz) | 4 vCPU | 6+ vCPU |
| RAM | 5.8 GB + 4 GB swap | 4 GB | 8 GB |

## Configuración actual (systemd)

Generada por `despliegue/scripts/05_instalar_servicios.sh`:

```ini
# sinagersat-api.service
ExecStart=.../venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 3

# motoria-embeddings.service
ExecStart=.../venv/bin/uvicorn services.motoria_embeddings.main:app --host 127.0.0.1 --port 8001 --workers 2
```

| Servicio | Workers | Puerto | Memoria aprox. |
|---|---|---|---|
| API principal | **3** | 0.0.0.0:8000 | ~150–250 MB por worker |
| MotorIA embeddings | **2** | 127.0.0.1:8001 | ~300–500 MB por worker (modelo ONNX) |

**Total estimado:** ~1.5–2 GB RAM en operación normal.

## Fórmula de workers

```bash
# Máximo teórico uvicorn:
workers = (2 × núcleos) + 1

# 4 núcleos → 9 workers (teórico)
# 6 núcleos → 13 workers (teórico)

# NO usar el máximo — la RAM es el cuello de botella.
# Regla práctica para esta API:
#   workers ≈ min( (núcleos), RAM_GB )   con tope de 4 en 6–8 GB RAM
```

Por qué no el máximo teórico:

1. Cada worker carga su propio espacio Python (~150–250 MB).
2. La BD PostgreSQL tiene su propio pool de conexiones.
3. MotorIA embeddings ya consume ~1 GB con el modelo cargado.
4. En 5.8 GB RAM, 13 workers causarían OOM.

## Rendimiento observado (histórico)

| Config. | Requests simultáneos | Estabilidad | Memoria |
|---|---|---|---|
| 1 worker | 1 (bloqueos) | ❌ 91+ reinicios | 94 MB |
| 3–4 workers | 3–4+ | ✅ estable | ~500 MB–1 GB |

> Con 1 worker la API se bloqueaba con poca concurrencia. Con 3–4 workers es estable.

## Cuándo ajustar

### Aumentar a 4–6 workers si:
- CPU < 50% de forma consistente
- RAM disponible > 2 GB
- Requests en cola / latencia alta pico

### Mantener 3 workers si:
- CPU 50–70%
- RAM disponible 1–2 GB
- Estabilidad confirmada

### Reducir a 2 workers si:
- CPU > 80%
- RAM disponible < 500 MB
- Aparecen OOM kills en logs

### Cómo cambiar

```bash
sudo nano /etc/systemd/system/sinagersat-api.service
# Editar --workers N

sudo systemctl daemon-reload
sudo systemctl restart sinagersat-api
```

## Monitoreo

```bash
# Procesos uvicorn
ps aux | grep "uvicorn api.main" | grep -v grep

# Memoria del servicio
systemctl show sinagersat-api -p MemoryCurrent
systemctl show motoria-embeddings -p MemoryCurrent

# Estado
systemctl status sinagersat-api

# Logs en vivo
journalctl -u sinagersat-api -f

# Test de carga básico
for i in {1..20}; do
  curl -s -o /dev/null http://localhost:8000/health &
done
wait
echo "20 requests completados"
```

## Escalabilidad futura

```
Si la carga aumenta 10x:
├─ Opción A: más workers en el mismo servidor (hasta RAM lo permita)
├─ Opción B: Nginx/Apache como reverse proxy + balanceo
├─ Opción C: mover PostgreSQL a servidor dedicado
└─ Opción D: escalamiento horizontal (múltiples instancias API)
```

## PostgreSQL

No confundir workers de uvicorn con conexiones de PostgreSQL:

- Cada worker de uvicorn abre su propio pool SQLAlchemy.
- Con 3 workers, un máximo razonable de conexiones PG: `max_connections` ≥ 20.
- Verificar con: `SHOW max_connections;`

---

**Última actualización:** 2026-11-05
**Basado en:** `docs/CONFIGURACION_WORKERS.md` (histórico) + configuración systemd actual (3 workers).
