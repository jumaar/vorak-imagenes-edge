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

# Ejecuta el script de despliegue dentro de un contenedor 'deployer' temporal.
# --rm asegura que el contenedor se elimine después de la ejecución.
# -T deshabilita la asignación de un pseudo-TTY, crucial para evitar que el
# script se "cuelgue" al redirigir la salida a un log.
docker compose -p vorak-edge run --rm deployer ./deploy.sh