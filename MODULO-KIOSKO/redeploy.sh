#!/bin/sh

# --- Script para redesplegar el stack de la aplicación ---
# Este script es ejecutado por el servidor del Kiosko al recibir un webhook.

set -e # Salir inmediatamente si un comando falla

echo "----------------------------------------------------"
echo "Webhook recibido. Iniciando proceso de redespliegue..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

# 1. Navegar al directorio del proyecto montado en /app/project_root
# Esto es necesario para que 'docker stack deploy' encuentre el archivo .yml y el .env
cd /app/project_root

# --- ¡NUEVO Y CRÍTICO! Actualizar el repositorio local ---
echo "Actualizando el repositorio local con 'git pull'..."
git pull origin main

# 2. Exportar las variables de entorno necesarias desde el archivo .env
echo "Exportando variables de entorno desde .env..."
export $(grep -v '^#' .env | xargs)

# --- ¡NUEVO! 3. Actualizar los secretos en Docker Swarm ---
echo "Sincronizando secretos desde .env a Docker Swarm..."
/app/manage-secrets.sh

# 3. Exportar los GIDs de hardware
echo "Exportando GIDs de hardware..."
export VIDEO_GID=$(getent group video | cut -d: -f3)
export DIALOUT_GID=$(getent group dialout | cut -d: -f3)

# 4. Iniciar sesión en el registro de contenedores (GHCR)
# Las credenciales se leen desde las variables de entorno del contenedor del kiosko.
echo "Autenticando en ghcr.io..."
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

# 5. Redesplegar el stack de la aplicación
echo "Redesplegando el stack 'vorak-app'..."
docker stack deploy --with-registry-auth -c docker-stack.app.yml vorak-app

echo "----------------------------------------------------"
echo "✅ Proceso de redespliegue completado."
echo "----------------------------------------------------"