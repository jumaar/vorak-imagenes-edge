#!/bin/sh
set -e

# Este es el script de entrada para el contenedor 'kiosko'.
# Su propósito es preparar el entorno ANTES de lanzar la aplicación principal.

echo "[Entrypoint] Verificando permisos de los scripts..."

# SOLUCIÓN: Aseguramos que el script de despliegue tenga permisos de ejecución.
# Esto soluciona el problema del bind mount que sobrescribe los permisos del Dockerfile.
chmod +x ./run_deployer.sh
echo "[Entrypoint] Permisos de 'run_deployer.sh' asegurados."

# Finalmente, ejecutamos el comando principal que se pasó al contenedor (en nuestro caso, gunicorn).
exec "$@"