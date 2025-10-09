# --- Script UNIFICADO para actualizar y redesplegar la aplicación ---
# Este script se ejecuta dentro del contenedor 'deployer' y lo hace TODO.

set -e # Salir inmediatamente si un comando falla


> deploy.log

(
  echo "----------------------------------------------------"
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

  docker compose -p vorak-edge up -d --no-build --remove-orphans --force-recreate

  echo "Limpiando imágenes de Docker antiguas (dangling)..."

  docker image prune -f

  echo "✅ Proceso de despliegue finalizado. Los servicios han sido actualizados."
) >> deploy.log 2>&1