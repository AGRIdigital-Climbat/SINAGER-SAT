#!/usr/bin/env bash
#
# cerrar_opencode.sh — Limpieza automática de sesiones opencode huérfanas
#
# El problema: cada sesión de opencode mantiene procesos en memoria
# (~400-800 MB por instancia). Las sesiones abandonadas (sin terminal)
# se acumulan y pueden llenar la RAM/swap, volviendo lento todo el servidor.
#
# Regla conservadora (segura):
#   - Solo se cierran procesos `opencode` SIN terminal (tty = ?) y con
#     antigüedad > 24 horas. Las sesiones interactivas SIEMPRE tienen
#     tty pts/X, por lo que NUNCA se tocan.
#   - Salvaguarda: si la RAM disponible es baja (< 512 MB) se aborta
#     para no interferir con trabajo en curso.
#
# Uso:
#   sudo bash scripts/cerrar_opencode.sh          # limpieza manual
#   sudo bash scripts/cerrar_opencode.sh --force  # ignora la salvaguarda de RAM
#
# Cron sugerido (05:05 diario):
#   5 3 * * * root /home/prosuco/SINAGERSAT/BaseData/scripts/cerrar_opencode.sh

LOG="/var/log/opencode_limpieza.log"
MIN_AGE_HORAS=24
MIN_EDAD_SEC=$((MIN_AGE_HORAS * 3600))
RAM_MIN_MB=512

msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

# ---------- Salvaguarda de RAM (salvo con --force) ----------
if [ "$1" != "--force" ]; then
    AVAIL_MB=$(free -m | awk '/^Mem:/ {print $7}')
    if [ -n "$AVAIL_MB" ] && [ "$AVAIL_MB" -lt "$RAM_MIN_MB" ]; then
        msg "RAM disponible baja (${AVAIL_MB} MB < ${RAM_MIN_MB} MB). Limpieza omitida."
        exit 0
    fi
fi

# ---------- Buscar procesos opencode ----------
# ps: tty=?  -> sin terminal (huérfano/daemon)
# etime -> 1-02:03:45 (días-hh:mm:ss) o 03:45 (mm:ss) o 45 (segundos)
MATADOS=0
while IFS= read -r line; do
    PID=$(echo "$line" | awk '{print $1}')
    TTY=$(echo "$line" | awk '{print $2}')
    ETIME=$(echo "$line" | awk '{print $3}')

    # Solo huérfanos (sin terminal)
    [ "$TTY" = "?" ] || continue

    # Calcular edad en segundos desde etime
    EDAD=0
    if [[ "$ETIME" == *-* ]]; then
        DIAS=${ETIME%%-*}
        HHM=${ETIME#*-}
        H=${HHM%%:*}; M=${HHM#*:}; M=${M%%:*}; S=${HHM##*:}
        EDAD=$(( (DIAS*24*3600) + (10#$H*3600) + (10#$M*60) + 10#$S ))
    elif [[ "$ETIME" == *:*:* ]]; then
        H=${ETIME%%:*}; M=${ETIME%%:*:*}; M=${M#*:}; S=${ETIME##*:}
        EDAD=$(( (10#$H*3600) + (10#$M*60) + 10#$S ))
    elif [[ "$ETIME" == *:* ]]; then
        M=${ETIME%%:*}; S=${ETIME##*:}
        EDAD=$(( (10#$M*60) + 10#$S ))
    else
        EDAD=$((10#$ETIME))
    fi

    if [ "$EDAD" -gt "$MIN_EDAD_SEC" ]; then
        if kill -TERM "$PID" 2>/dev/null; then
            msg "Cerrada instancia opencode huérfana PID $PID (edad ${ETIME})"
            MATADOS=$((MATADOS+1))
        else
            msg "No se pudo cerrar PID $PID (¿ya terminó?)"
        fi
    fi
done < <(ps -eo pid,tty,etime,args | awk '$4 ~ /opencode/ && $4 !~ /grep/ {print $1, $2, $3}')

# ---------- Resumen ----------
if [ "$MATADOS" -gt 0 ]; then
    msg "Limpieza completada: $MATADOS proceso(s) cerrado(s)."
else
    msg "Limpieza completada: ninguna instancia huérfana que cerrar."
fi

exit 0
