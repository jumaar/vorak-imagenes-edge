#!/bin/sh
set -e # Salir inmediatamente si un comando falla.

# Este script es llamado por kiosk.py para lanzar el contenedor de despliegue.
# Centraliza la lógica del comando para facilitar su mantenimiento y evitar problemas de parsing en Python.

echo "[Deploy Script] Iniciando el contenedor 'deployer'..."

# Definimos el nombre del proyecto para asegurar la consistencia.
# Usamos la variable de entorno si está disponible, si no, un valor por defecto.
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-vorak-edge}

echo "[Deploy Script] Usando el nombre de proyecto: ${PROJECT_NAME}"

# --- ¡MEJORA! ---
# Ejecutamos el comando 'docker compose run' en modo 'detached' (-d).
# Esto inicia el contenedor 'deployer' en segundo plano y devuelve el control inmediatamente.
# El kiosko no tiene que esperar a que todo el despliegue termine.
docker compose -p "${PROJECT_NAME}" run -d --rm deployer

echo "[Deploy Script] El contenedor 'deployer' ha sido lanzado en segundo plano para realizar la actualización."