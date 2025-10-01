#!/bin/bash

# Este script se ejecuta como root al iniciar el contenedor.

# 1. Corregir permisos de los volúmenes montados.
#    El usuario 'kiosk' (UID/GID pasado en el build) necesita poder escribir en su data.
echo "Ajustando permisos de los directorios..."
chown -R kiosk:kiosk /app/data /home/kiosk/venv

# 2. Iniciar el servidor web del kiosko (kiosk.py) en segundo plano.
#    Lo ejecutamos como el usuario 'kiosk' para mayor seguridad.
#    Usamos 'sudo -u' que funciona con la configuración NOPASSWD, a diferencia de 'su'.
#    El flag -E (--preserve-env) es crucial para que kiosk.py herede las variables de entorno.
echo "Iniciando servidor web del kiosko como usuario 'kiosk'..."
sudo -E -u kiosk /home/kiosk/venv/bin/python3 /app/kiosk.py &

# 3. Esperar un poco para que el servidor Flask esté listo.
sleep 5

# 4. Lanzar la sesión gráfica como el usuario 'kiosk'.
#    'exec' reemplaza este script con el comando 'sudo'.
#    'sudo -u kiosk' ejecuta el script .xsession como el usuario correcto.
#    Esto conecta las aplicaciones del .xsession (openbox, chromium) al servidor X11 del host,
#    en lugar de intentar crear uno nuevo con startx.
echo "Lanzando sesión gráfica como usuario 'kiosk'..."
exec sudo -E -u kiosk /home/kiosk/.xsession