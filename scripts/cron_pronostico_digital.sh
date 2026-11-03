#!/bin/bash
# Pronóstico Digital - Ingesta automática 2x/día
# SIN AUTENTICACIÓN - llama directamente al service Python

echo "Iniciando ingesta de pronósticos digitales: $(date)"

cd /home/prosuco/SINAGERSAT/BaseData
venv/bin/python scripts/cron_pronostico_digital_auto.py >> /var/log/sinb/pronostico_cron.log 2>&1

echo "Completado: $(date)"
