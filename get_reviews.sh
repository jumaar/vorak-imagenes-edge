#!/bin/bash

# ==============================================================================
# Script para descargar y limpiar la cola de revisión de una nevera remota.
# USO: ./get_reviews.sh
#
# Este script se conecta a la nevera, copia los archivos de la cola de revisión
# a una carpeta temporal, los descarga a tu PC local y, si la descarga es
# exitosa, borra los archivos del dispositivo remoto para liberar espacio.
# ==============================================================================

# --- Configuración ---
REMOTE_USER="nevera1"
REMOTE_HOST="ssh-nevera1.lenstextil.com"
CONTAINER_NAME="vorak-nevera"
# Ruta DENTRO del contenedor donde están los archivos de revisión
CONTAINER_PATH="/app/review_queue"
# Carpeta temporal que se creará en la nevera
REMOTE_TEMP_DIR="~/review_to_download"
# Carpeta local donde se guardarán las revisiones
LOCAL_DEST_DIR="./downloaded_reviews"

echo "### INICIANDO PROCESO DE DESCARGA Y LIMPIEZA DE REVISIONES ###"
echo "Host Remoto: ${REMOTE_USER}@${REMOTE_HOST}"
echo "------------------------------------------------------------"

# --- PASO 1: Preparar archivos en la nevera remota ---
echo "PASO 1: Conectando a la nevera para preparar los archivos..."
ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
  echo "  -> Limpiando carpetas temporales anteriores (si existen)..."
  rm -rf ${REMOTE_TEMP_DIR}

  echo "  -> Usando 'docker cp' para copiar desde el contenedor a una carpeta temporal..."
  # Usamos sudo porque el demonio de Docker requiere privilegios de root
  sudo docker cp ${CONTAINER_NAME}:${CONTAINER_PATH} ${REMOTE_TEMP_DIR}

  echo "  -> Corrigiendo permisos de los archivos copiados..."
  # Cambiamos el propietario de la carpeta temporal a nuestro usuario
  sudo chown -R \$(whoami):\$(whoami) ${REMOTE_TEMP_DIR}

  echo "  -> ¡Archivos listos para la descarga!"
EOF

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Falló la preparación de archivos en la nevera remota. Abortando."
  exit 1
fi

# --- PASO 2: Descargar los archivos a tu PC local ---
echo ""
echo "PASO 2: Descargando la carpeta a tu PC local en '${LOCAL_DEST_DIR}'..."
mkdir -p ${LOCAL_DEST_DIR}
# Copiamos el contenido de la carpeta remota, no la carpeta en sí
scp -r ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TEMP_DIR}/* ${LOCAL_DEST_DIR}/

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Falló la descarga con scp. Los archivos NO se borrarán del dispositivo remoto."
  # Limpiamos solo la carpeta temporal en la nevera
  ssh ${REMOTE_USER}@${REMOTE_HOST} "rm -rf ${REMOTE_TEMP_DIR}"
  exit 1
fi

echo "✅ ¡Éxito! Los archivos de revisión han sido descargados a '${LOCAL_DEST_DIR}'."

# --- PASO 3: Limpiar archivos en la nevera remota ---
echo ""
echo "PASO 3: Limpiando archivos en la nevera remota..."
ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
  echo "  -> Borrando contenido de la cola de revisión original en el contenedor..."
  sudo docker exec ${CONTAINER_NAME} sh -c "rm -rf ${CONTAINER_PATH}/*"

  echo "  -> Borrando carpeta temporal..."
  rm -rf ${REMOTE_TEMP_DIR}
EOF

echo "✅ Limpieza completada. Proceso finalizado."