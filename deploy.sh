#!/bin/bash
# --- Script de Despliegue para Dispositivos IoT ---
# Este script es ejecutado por el workflow de GitHub Actions.

set -e # Salir inmediatamente si un comando falla

echo "Iniciando proceso de DESPLIEGUE..."
echo "Fecha: $(date)"
echo "Versión a desplegar (IMAGE_TAG): ${IMAGE_TAG}"
echo "----------------------------------------------------"

# 1. Verificar que la variable IMAGE_TAG esté definida.
if [ -z "${IMAGE_TAG}" ]; then
  echo "Error: La variable de entorno IMAGE_TAG no está definida."
  echo "Este script debe ser ejecutado por el workflow de GitHub Actions."
  exit 1
fi

# 2. Verificar que el archivo .env exista.
echo "Verificando la existencia del archivo .env..."
if [ ! -f ".env" ]; then
    echo "Error: No se encontró el archivo .env. Asegúrate de que exista en el dispositivo."
    exit 1
fi

# 3. Descargar las imágenes específicas de la nueva versión.
echo "Descargando las imágenes de la versión ${IMAGE_TAG}..."
# La variable IMAGE_TAG es exportada por el workflow y usada por docker-compose.yml
docker compose -p vorak-edge --env-file ./.env pull

# 4. Redesplegar la pila de servicios.
echo "Redesplegando la pila de servicios con la nueva versión..."
# Usamos --force-recreate para asegurar que los contenedores se reinicien con la nueva imagen.
docker compose -p vorak-edge --env-file ./.env up -d --no-build --remove-orphans --force-recreate

# 5. Limpiar imágenes de Docker antiguas.
echo "Limpiando imágenes de Docker antiguas (dangling)..."
docker image prune -f

echo "✅ Proceso de despliegue finalizado. Servicios actualizados a la versión ${IMAGE_TAG}."