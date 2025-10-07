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

echo "Guardando cambios locales (stash) y actualizando con 'git pull'..."
git stash
git pull origin main

echo "Estableciendo permisos de ejecución para los scripts de entrypoint..."
chmod +x ./MODULO-MONITORING/entrypoint-prometheus.sh
chmod +x ./MODULO-MONITORING/entrypoint-promtail.sh
echo "✅ Permisos de ejecución establecidos."

echo "✅ Código fuente actualizado. Esperando 10 segundos antes de lanzar el despliegue..."
sleep 10

# Ejecuta el script de despliegue
./deploy.sh