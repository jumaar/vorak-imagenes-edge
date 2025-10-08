#!/bin/sh
# /home/jumaar/Escritorio/GITHUB jumaar/vorak-imagenes-edge/MODULO-MONITORING/entrypoint-promtail.sh

# Salir inmediatamente si un comando falla
set -e

echo "Promtail Entrypoint: Procesando archivo de configuración..."

# Sustituye las variables de entorno en el archivo de configuración
# Leemos desde la plantilla montada y escribimos en la ruta final que Promtail espera.
envsubst < /etc/promtail/config.yml.template > /etc/promtail/config.yml

echo "Promtail Entrypoint: Configuración procesada. Iniciando Promtail..."
# Pasa el control al comando original de Promtail.
# Le indicamos explícitamente que use el archivo de configuración que acabamos de generar para mayor claridad.
exec /usr/bin/promtail -config.file=/etc/promtail/config.yml "$@"