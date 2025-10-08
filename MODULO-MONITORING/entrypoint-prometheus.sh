#!/bin/sh
# /home/jumaar/Escritorio/GITHUB jumaar/vorak-imagenes-edge/MODULO-MONITORING/entrypoint-prometheus.sh

# Salir inmediatamente si un comando falla
set -e

echo "Prometheus Entrypoint: Procesando archivo de configuración..."

# Sustituye las variables de entorno en el archivo de configuración
# --- ¡CORRECCIÓN! ---
# No podemos sobreescribir un archivo montado. Guardamos el resultado en un nuevo archivo.
# Leemos desde la plantilla montada y escribimos en la ruta final que Prometheus espera.
envsubst < /etc/prometheus/prometheus.yml.template > /etc/prometheus/prometheus.yml

echo "Prometheus Entrypoint: Configuración procesada. Iniciando Prometheus..."
# Pasa el control al comando original de Prometheus.
# Le indicamos explícitamente que use el archivo de configuración que acabamos de generar para mayor claridad.
exec /bin/prometheus --config.file=/etc/prometheus/prometheus.yml "$@"