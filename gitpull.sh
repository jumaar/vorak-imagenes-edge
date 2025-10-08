#!/bin/sh

# --- Script para actualizar el código fuente desde Git ---
# Este script es el punto de entrada para el webhook. Su única
# responsabilidad es descargar los últimos cambios del repositorio.

set -e

echo "----------------------------------------------------"
echo "Iniciando actualización de código fuente..."
echo "Fecha: $(date)"
echo "----------------------------------------------------"

echo "Navegando al directorio del proyecto..."
cd "$(dirname "$0")"

echo "Forzando actualización desde github (origin/main)..."
git fetch origin main
git reset --hard origin/main

echo "✅ Código fuente actualizado y sincronizado con origin/main."
echo "Esperando 5 segundos antes de continuar..."
sleep 5

echo "Lanzando el script de despliegue..."
rm -f ./deploy.log

# Ejecuta el script de despliegue dentro de un contenedor 'deployer' temporal.
# --rm asegura que el contenedor se elimine después de la ejecución.
docker compose -p vorak-edge run --rm deployer ./deploy.sh > ./deploy.log 2>&1