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

# --- ¡SOLUCIÓN DEFINITIVA! ---
# 5. Usar un contenedor "desechable" para ejecutar el redespliegue.
# Esto evita la paradoja de que el kiosko intente reiniciarse a sí mismo.
echo "Lanzando un contenedor temporal para gestionar el redespliegue de toda la pila..."

# Usamos la imagen oficial de Docker Compose para ejecutar el comando 'up'.
# Esto asegura que el contenedor que ejecuta el despliegue es independiente
# de la pila que se está actualizando.
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)":"$(pwd)" \
  -w "$(pwd)" \
  docker/compose:v2.24.6 \
  --env-file ./.env up -d --no-build --remove-orphans

# El script original se detendrá aquí cuando el contenedor kiosko sea reemplazado.
# Los logs posteriores a este punto no se verán en la llamada del webhook,
# lo cual es un comportamiento esperado y correcto.
echo "El contenedor de despliegue ha sido lanzado. El kiosko será reiniciado como parte del proceso."
echo "El proceso de actualización se está ejecutando en segundo plano."