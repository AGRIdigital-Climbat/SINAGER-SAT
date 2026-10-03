# ============================================================================
# CRON JOBS SINB - NDVI SATELITAL
# ============================================================================
# Instalar en crontab del usuario prosuco:
# 
# crontab -e
# 
# Y agregar las líneas siguientes:
# ============================================================================

# Ingesta diaria de NDVI (06:00 hora Bolivia)
# Descarga escenas Sentinel-2 y calcula NDVI para todas las comunidades
0 6 * * * cd /home/prosuco/SINAGERSAT/BaseData && venv/bin/python scripts/cron_ndvi_ingest.py >> /var/log/sinb/ndvi_cron.log 2>&1

# Verificación de salud del servidor NDVI (opcional)
# Revisa que el endpoint de estadísticas responda correctamente
*/30 * * * * curl -s http://localhost:8000/api/v2/ndvi/estadisticas/resumen > /dev/null || echo "ALERTA: Endpoint NDVI no responde" >> /var/log/sinb/ndvi_health.log

# ============================================================================
# NOTAS:
# ============================================================================
# - La ingesta toma ~1-2 horas para 343 municipios (depende de EarthSearch)
# - Los datos se guardan en:
#   * sinb.escena_satelital (escenas descargadas)
#   * sinb.agregado_satelital (NDVI por comunidad)
#   * sinb.serie_ndvi_comunidad (serie temporal)
# - No hay limpieza automática: los datos se guardan indefinidamente
# - Ver logs en: /var/log/sinb/ndvi_cron.log
# ============================================================================
