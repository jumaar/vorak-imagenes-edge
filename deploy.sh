# --- Script para redesplegar la aplicación con Docker Compose ---
# Este script asume que 'git pull' ya se ha ejecutado.

set -e # Salir inmediatamente si un comando falla

echo "----------------------------------------------------"
echo "Iniciando proceso de despliegue con Docker Compose..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

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


echo "Descargando las últimas versiones de las imágenes con 'docker compose pull'..."
docker compose -p vorak-edge --env-file ./.env pull

echo "Redesplegando la pila de servicios con 'docker compose up'..."

# EXCLUYENDO al propio 'deployer' para evitar que intente reiniciarse a sí mismo.
docker compose -p vorak-edge up -d --no-build --remove-orphans nevera kiosko backup prometheus promtail cadvisor node-exporter

echo "Limpiando imágenes de Docker antiguas (dangling)..."
# El comando 'docker image prune' elimina las imágenes que no están asociadas a ningún contenedor.
# La bandera -f (force) es necesaria para ejecutarlo de forma no interactiva en un script.
# Esta es una "poda suave" que no afecta a las imágenes base que aún podrían ser útiles.
docker image prune -f

echo "✅ Proceso de despliegue finalizado. Los servicios han sido actualizados."