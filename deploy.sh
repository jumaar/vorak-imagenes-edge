set -e 

if [ -z "${IMAGE_TAG}" ]; then
  echo "Error: La variable de entorno IMAGE_TAG no está definida."
  echo "Este script debe ser ejecutado por el workflow de GitHub Actions."
  exit 1
fi

echo "Verificando la existencia del archivo .env..."
if [ ! -f ".env" ]; then
    echo "Error: No se encontró el archivo .env. Asegúrate de que exista en el dispositivo."
    exit 1
fi

echo "Descargando las imágenes de la versión ${IMAGE_TAG}..."
docker compose -p vorak-edge --env-file ./.env pull

echo "Redesplegando la pila de servicios con la nueva versión..."
docker compose -p vorak-edge --env-file ./.env up -d --no-build --remove-orphans --force-recreate

echo "Limpiando imágenes de Docker antiguas (dangling)..."
docker image prune -f

echo "✅ Proceso de despliegue finalizado. Servicios actualizados a la versión ${IMAGE_TAG}."