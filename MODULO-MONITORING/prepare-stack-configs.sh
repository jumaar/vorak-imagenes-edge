#!/bin/sh
# Este script prepara los archivos de configuración para el despliegue con Docker Stack.
# Lee las variables del archivo .env en la raíz del proyecto y las sustituye
# en los archivos de configuración de monitoreo.

set -e

# Navega a la raíz del proyecto (asumiendo que el script se ejecuta desde MODULO-MONITORING)
cd "$(dirname "$0")/.."

# Verifica que el archivo .env exista
if [ ! -f .env ]; then
    echo "Error: El archivo .env no se encuentra en la raíz del proyecto."
    echo "Por favor, copia .env.template a .env y configura tus variables."
    exit 1
fi

# Exporta las variables de entorno desde el archivo .env para que envsubst las pueda usar
export $(grep -v '^#' .env | xargs)

echo "Generando configuraciones para Docker Stack..."

# Procesa el archivo de configuración de Prometheus
envsubst < ./MODULO-MONITORING/prometheus.yml > ./MODULO-MONITORING/prometheus-stack.yml

# Procesa el archivo de configuración de Promtail
envsubst < ./MODULO-MONITORING/promtail-config.yml > ./MODULO-MONITORING/promtail-config-stack.yml

echo "✓ Archivos 'prometheus-stack.yml' y 'promtail-config-stack.yml' generados correctamente."
echo "Ahora puedes desplegar el stack de monitoreo."
