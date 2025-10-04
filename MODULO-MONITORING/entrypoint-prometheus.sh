#!/bin/sh
# /home/jumaar/Escritorio/GITHUB jumaar/vorak-imagenes-edge/MODULO-MONITORING/entrypoint-prometheus.sh

# Salir inmediatamente si un comando falla
set -e

echo "Prometheus Entrypoint: Procesando archivo de configuración..."

# Sustituye las variables de entorno en el archivo de configuración
# --- ¡CORRECCIÓN! ---
# No podemos sobreescribir un archivo montado. Guardamos el resultado en un nuevo archivo.
envsubst < /etc/prometheus/prometheus.yml > /etc/prometheus/prometheus-processed.yml

echo "Prometheus Entrypoint: Configuración procesada. Iniciando Prometheus..."
# Pasa el control al comando original de Prometheus, usando los argumentos que se le pasen a este script.
exec /bin/prometheus --config.file=/etc/prometheus/prometheus-processed.yml "$@"