#!/bin/sh

# --- Script Disparador del Despliegue ---
# Este script es llamado por el webhook en el contenedor 'kiosko'.
# Su ÚNICA responsabilidad es lanzar el contenedor 'deployer',
# que se encargará de todo el proceso de actualización y despliegue.

set -e

echo "----------------------------------------------------"
echo "Disparando el proceso de despliegue..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

# El working_dir ya está configurado en /app en docker-compose.yml

docker compose -p vorak-edge run --rm deployer ./deploy.sh