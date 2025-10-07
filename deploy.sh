#!/bin/sh

# --- Script para redesplegar la aplicación con Docker Compose ---
# Este script asume que 'git pull' ya se ha ejecutado.

set -e # Salir inmediatamente si un comando falla

echo "----------------------------------------------------"
echo "Iniciando proceso de despliegue con Docker Compose..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

# 1. Navegar a la raíz del proyecto.
cd "$(dirname "$0")"

# 2. Verificar que el archivo .env exista.
echo "Verificando la existencia del archivo .env..."
if [ ! -f ".env" ]; then
    echo "Error: No se encontró el archivo .env. Por favor, créalo a partir de .env.template."
    exit 1
fi

# 3. Cargar variables de entorno para el login de Docker.
export $(grep -v '^#' .env | xargs)

echo "Autenticando en el registro de contenedores (ghcr.io)..."
if [ -n "$GHCR_USER" ] && [ -n "$GHCR_TOKEN" ]; then
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
else
  echo "Error: Las variables GHCR_USER o GHCR_TOKEN no están definidas en .env."
  exit 1
fi

# 4. Descargar las últimas versiones de las imágenes.
echo "Descargando las últimas versiones de las imágenes con 'docker compose pull'..."
docker compose --env-file ./.env pull

# 5. Redesplegar los servicios usando las imágenes ya descargadas.
echo "Redesplegando todos los servicios con 'docker compose up'..."
docker compose --env-file ./.env up -d --build --remove-orphans

echo "----------------------------------------------------"
echo "✅ Proceso de despliegue completado."
echo "----------------------------------------------------"