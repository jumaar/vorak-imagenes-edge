#!/bin/sh
set -e # Salir inmediatamente si un comando falla.

# Este script es llamado por kiosk.py para lanzar el contenedor de despliegue.
# Centraliza la lógica del comando para facilitar su mantenimiento y evitar problemas de parsing en Python.

echo "[Deploy Script] Iniciando el contenedor 'deployer'..."

# Definimos el nombre del proyecto para asegurar la consistencia.
# Usamos la variable de entorno si está disponible, si no, un valor por defecto.
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-vorak-edge}

echo "[Deploy Script] Usando el nombre de proyecto: ${PROJECT_NAME}"

# Ejecutamos el comando 'docker-compose run'. Usamos 'docker-compose' con guion para máxima compatibilidad.
# El flag '--rm' asegura que el contenedor se elimine después de ejecutar su tarea.
docker-compose -p "${PROJECT_NAME}" run --rm deployer

echo "[Deploy Script] El comando 'docker-compose run' se ha completado."