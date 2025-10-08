#!/bin/sh
# /home/jumaar/Escritorio/GITHUB jumaar/vorak-imagenes-edge/MODULO-MONITORING/entrypoint-promtail.sh

# Salir inmediatamente si un comando falla
set -e

echo "Promtail Entrypoint: Procesando archivo de configuración..."

# Sustituye las variables de entorno en el archivo de configuración
envsubst < /etc/promtail/config.yml > /etc/promtail/processed-config.yml

echo "Promtail Entrypoint: Configuración procesada. Iniciando Promtail..."
# Pasa el control al comando original de Promtail, usando los argumentos que se le pasen a este script.
# --- ¡CORRECCIÓN FINAL! ---
exec /usr/bin/promtail -config.file=/etc/promtail/processed-config.yml "$@"