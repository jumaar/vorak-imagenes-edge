#!/bin/sh

# Este script se ejecuta al iniciar el contenedor para configurar los permisos de hardware.

echo "Iniciando entrypoint para configurar permisos..."

# Lee los GIDs (Group IDs) de las variables de entorno.
# Si no se proporcionan, usa valores por defecto comunes en Debian/Ubuntu.
VIDEO_GID=${VIDEO_GID:-997}
DIALOUT_GID=${DIALOUT_GID:-20}

echo "Usando VIDEO_GID=${VIDEO_GID} y DIALOUT_GID=${DIALOUT_GID}"

# Crea los grupos 'video' y 'dialout' dentro del contenedor con los GIDs correctos.
# El flag '-f' (force) permite que el comando no falle si el grupo ya existe.
groupadd -g "$VIDEO_GID" -f video
groupadd -g "$DIALOUT_GID" -f dialout

# Añade el usuario 'root' (que ejecuta la app) a estos grupos.
usermod -a -G video,dialout root

echo "Permisos configurados. Iniciando la aplicación principal (app.py)..."

# Ejecuta el comando original del Dockerfile (CMD)
exec "$@"