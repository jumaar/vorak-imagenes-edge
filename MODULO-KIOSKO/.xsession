#!/bin/bash

# --- CONFIGURACIÓN DE LA SESIÓN GRÁFICA (se ejecuta una sola vez) ---

# 1. Desactivar salvapantallas y ahorro de energía del monitor.
xset s off -dpms

# 2. ¡LA CLAVE! Elimina la variable de entorno de D-Bus para toda la sesión.
#    Esto evita que Chromium intente conectarse y genere los errores en el log.
unset DBUS_SESSION_BUS_ADDRESS

# 3. Iniciar el gestor de ventanas Openbox en segundo plano.
openbox &

# 3. Crear un archivo de preferencias para Chromium para desactivar la traducción.
#    Esto escribe directamente en la configuración del perfil del navegador.
PREFS_FILE="/tmp/chromium_profile/Default/Preferences"
mkdir -p "$(dirname "$PREFS_FILE")"
echo '{ "translate": { "enabled": false } }' > "$PREFS_FILE"


# --- BUCLE DE SUPERVISIÓN DE CHROMIUM ---
# Bucle infinito para mantener Chromium siempre abierto.
#    Si el navegador falla o se cierra, este bucle lo volverá a lanzar.
while true; do
  # Lanzamos Chromium en modo kiosko apuntando al servidor local.
  # Las opciones adicionales ocultan barras de información y mensajes de error.
  chromium \
    --kiosk "http://localhost:5000" \
    --no-sandbox \
    --disable-gpu \
    --disable-dbus \
    --disable-infobars \
    --no-first-run \
    --no-default-browser-check \
    --user-data-dir=/tmp/chromium_profile 2>/dev/null

  # Esperamos 5 segundos antes de reintentar si se cierra.
  sleep 5
done