# Cerrar procesos de opencode (liberar recursos)

Guía para evitar que las sesiones de **opencode** consuman toda la RAM del servidor
y dejen lenta la base de datos y la API.

## Por qué opencode consume mucha RAM

- Cada sesión de opencode mantiene procesos en memoria de **~400 a 800 MB**.
- Si abres opencode en varias terminales y las **dejas abiertas**, las instancias se
  acumulan día a día. Con 10-12 instancias se llenan 5 GB de los 5.8 GB del servidor.
- Con la RAM llena, el kernel empieza a usar **swap** y a **thrashar** (entrada/salida
  constante de páginas): el `load average` sube, el `wa` (I/O wait) llega al 20-30% y
  **todo se vuelve lento**: las consultas a PostgreSQL, la API y el propio opencode.
- En el peor caso (swap 100% lleno) el servidor se reinicia por presión de memoria,
  cortando sesiones de forma abrupta.

**Regla de oro:** una sesión de opencode abierta = ~0.5 GB de RAM comprometidos.
Cierra las terminales que no uses.

## 1. Diagnosticar el estado

```bash
# ¿Cuántas instancias de opencode hay corriendo?
pgrep -fc opencode

# Detalle: PID, memoria, antigüedad y terminal
ps -eo pid,rss,tty,etime,args --sort=-rss | grep -i opencode | grep -v grep

# RAM disponible y swap (debe haber RAM libre y swap sin usar)
free -h

# Carga del sistema (el load no debe superar el nº de núcleos; ver con nproc)
uptime
```

Interpretación del detalle de `ps`:

| Columna  | Qué significa                                        | Peligro          |
|----------|------------------------------------------------------|------------------|
| `tty=?`  | Proceso **sin terminal** → daemon/sesión abandonada  | Huérfano: cerrar |
| `tty=pts/N` | Proceso **con terminal** → sesión interactiva en uso | **NO cerrar**    |
| `etime`  | Antigüedad (días-hh:mm:ss)                           | +1 día sin tty → huérfano |

## 2. Cerrar manualmente

> **NUNCA** cierres la sesión de opencode que estás usando en ese momento
> (la que tiene `tty=pts/N`). Cerrarla pierde el chat/contexto abierto.

```bash
# Cerrar una instancia concreta (PID del paso 1)
kill <PID>

# Cerrar todas las instancias sin terminal (huérfanas), conservando las activas
pkill -f opencode 2>/dev/null
# └─ ⚠️  ULTIMA OPCION: cierra TODAS, incluida la tuya. Usar solo en emergencia.
```

## 3. Limpieza automática (recomendada)

El script `scripts/cerrar_opencode.sh` cierra **solo huérfanos seguros**:

- Procesos `opencode` con **tty = ?** (sin terminal) y antigüedad **> 24 horas**.
- Nunca toca sesiones interactivas (`tty=pts/*`).
- **Salvaguarda:** si la RAM disponible es < 512 MB, aborta para no interferir
  con trabajo en curso (forzar con `--force`).

```bash
# Ejecución manual (requiere root para leer todos los procesos)
sudo bash scripts/cerrar_opencode.sh
sudo bash scripts/cerrar_opencode.sh --force   # ignora la salvaguarda de RAM
```

Ya está instalado un **cron diario a las 03:05** que ejecuta la limpieza
automáticamente. El log queda en `/var/log/opencode_limpieza.log`.

## 4. Verificar la liberación de recursos

```bash
free -h          # RAM disponible y swap (swap debe quedar en 0)
uptime           # load average debe bajar
pgrep -fc opencode   # solo deben quedar las sesiones que estás usando
```

## Referencia rápida

| Acción | Comando |
|--------|---------|
| Contar instancias | `pgrep -fc opencode` |
| Ver detalle | `ps -eo pid,rss,tty,etime,args \| grep opencode` |
| Cerrar una huérfana | `kill <PID>` |
| Limpieza automática | `sudo bash scripts/cerrar_opencode.sh` |
| Ver log | `tail -f /var/log/opencode_limpieza.log` |
| RAM | `free -h` |
| Carga | `uptime` |
