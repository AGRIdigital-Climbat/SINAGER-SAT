# 🔧 Configuración de Workers para SINAGERSAT API

## 📊 Hardware Actual
- **CPU:** 6 núcleos QEMU @ 2.0GHz
- **RAM:** 5.8GB (3.4GB disponible)
- **Workers configurados:** 4

## 🎯 Fórmula de Workers

```bash
# Fórmula recomendada por uvicorn
workers = (2 x núcleos) + 1

# Para 6 núcleos:
workers = (2 x 6) + 1 = 13  # MÁXIMO TEÓRICO

# NUESTRA CONFIGURACIÓN: 4 workers
# Razones:
# 1. Memoria suficiente para 4 procesos (~500MB c/u = 2GB)
# 2. Balance entre rendimiento y consumo
# 3. Testing mostró estabilidad con 4 workers
```

## ⚙️ Configuración Actual (systemd)

```ini
# /etc/systemd/system/sinagersat-api.service

[Service]
ExecStart=/home/prosuco/SINAGERSAT/BaseData/venv/bin/uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4

Restart=on-failure
RestartSec=10s
StartLimitBurst=3
StartLimitIntervalSec=60s
```

## 📈 Rendimiento Observado

| Métrica | 1 Worker | 4 Workers | Mejora |
|---------|----------|-----------|--------|
| Requests simultáneos | 1 | 4+ | 4x |
| Requests en 10s | ~10 | ~40 | 4x |
| Memoria usada | 94MB | 519MB | 5.5x |
| Estabilidad | ❌ 91+ fallos | ✅ 0 fallos | ∞ |

## 🔍 Comandos de Monitoreo

```bash
# Ver workers activos
ps aux | grep "uvicorn api.main" | grep -v grep

# Ver árbol de procesos
pstree -p $(pgrep -f "uvicorn api.main" | head -1)

# Ver consumo de memoria
systemctl show sinagersat-api.service -p MemoryCurrent

# Test de carga
for i in {1..20}; do curl -s "http://localhost:8000/api/v2/sinb/pronostico-comunidad/02417371843-M" > /dev/null & done
wait
echo "20 requests completados"
```

## ⚠️ Cuándo Ajustar Workers

### Aumentar a 6 workers si:
- CPU usage < 50% consistentemente
- RAM disponible > 2GB
- Requests en cola > 10

### Mantener en 4 workers si:
- CPU usage 50-70%
- RAM disponible 1-2GB
- Estabilidad confirmada por 1 semana

### Reducir a 2 workers si:
- CPU usage > 80%
- RAM disponible < 500MB
- OOM kills en logs

## 📝 Historial de Cambios

| Fecha | Workers | Razón |
|-------|---------|-------|
| 2026-10-05 | 1 | Default (causaba bloqueos) |
| 2026-10-06 | 4 | Fix: 91+ reinicios por workers insuficientes |

## 🔮 Escalabilidad Futura

```
Si carga aumenta 10x:
├─ Opción A: Aumentar a 6-8 workers (mismo servidor)
├─ Opción B: Agregar Nginx como load balancer
└─ Opción C: Horizontal scaling (2+ servidores)
```

---
**Última actualización:** 2026-10-06  
**Próxima revisión:** 2026-10-13 (1 semana)
