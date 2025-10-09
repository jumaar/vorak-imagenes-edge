# --- Script UNIFICADO para actualizar y redesplegar la aplicación ---
# Este script se ejecuta dentro del contenedor 'deployer' y lo hace TODO.

set -e # Salir inmediatamente si un comando falla
# La redirección de logs ahora se gestiona desde el comando que llama a este script.

echo "Iniciando proceso de ACTUALIZACIÓN Y DESPLIEGUE..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

# 1. ACTUALIZAR CÓDIGO FUENTE DESDE GIT
echo "Forzando actualización desde github (origin/main)..."
# Le decimos a Git que el directorio del proyecto es seguro.
git config --global --add safe.directory /app
git fetch origin main
git reset --hard origin/main
echo "✅ Código fuente actualizado."

# 2. Verificar que el archivo .env exista.
echo "Verificando la existencia del archivo .env..."
if [ ! -f ".env" ]; then
    echo "Error: No se encontró el archivo .env. Por favor, créalo a partir de .env.template."
    exit 1
fi

# 3. Cargar las variables de entorno desde el archivo .env
echo "Cargando variables de entorno desde .env..."
# Usamos 'set -a' para exportar las variables y que estén disponibles
# para los subprocesos (como docker login). 'set +a' revierte el comportamiento.
set -a
. ./.env
set +a
echo "Autenticando en el registro de contenedores (ghcr.io)..."
if [ -n "$GHCR_USER" ] && [ -n "$GHCR_TOKEN" ]; then
  # Ocultar el token del log por seguridad
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
else
  echo "Error: Las variables GHCR_USER o GHCR_TOKEN no están definidas en .env."
  exit 1
fi

echo "Descargando las últimas versiones de las imágenes con 'docker compose pull'..."
docker compose -p vorak-edge --env-file ./.env pull

echo "Redesplegando la pila de servicios con 'docker compose up'..."
docker compose -p vorak-edge --env-file ./.env up -d --no-build --remove-orphans --force-recreate

echo "Limpiando imágenes de Docker antiguas (dangling)..."
docker image prune -f

echo "✅ Proceso de despliegue finalizado. Los servicios han sido actualizados."