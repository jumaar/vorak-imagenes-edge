#!/bin/bash

# Este script se ejecuta como root al iniciar el contenedor.

# 1. Corregir permisos de todos los volúmenes montados.
#    Esto asegura que el usuario 'nevera' pueda escribir en los directorios que necesita.
echo "Ajustando permisos de los volúmenes de la nevera..."
chown -R nevera:nevera /app/status /app/offline_queue /app/review_queue /app/logs /app/db

# 2. Lanzar la aplicación principal.
#    'exec' reemplaza este script con el comando de python, que se convierte en el proceso principal.
#    Se ejecuta como el usuario 'nevera' para mayor seguridad.
#    El flag -E (--preserve-env) es crucial para que app.py herede las variables de entorno.
exec sudo -E -u nevera /opt/venv/bin/python app.py