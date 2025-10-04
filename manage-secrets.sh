#!/bin/bash
# manage-secrets.sh - Lee el .env y crea/actualiza los secretos en Docker Swarm.

set -e # Termina el script si un comando falla

# Función para cargar variables desde .env
load_env() {
  if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
  else
    echo "Error: No se encontró el archivo .env. Por favor, créalo a partir de .env.template."
    exit 1
  fi
}

# Función para crear o actualizar un secreto
# Uso: upsert_secret <nombre_del_secreto> <valor_del_secreto>
upsert_secret() {
  local secret_name=$1
  local secret_value=$2

  if [ -z "$secret_value" ]; then
    echo "⚠️  Advertencia: El valor para el secreto '$secret_name' está vacío en .env. Omitiendo."
    return
  fi

  # Intenta eliminar el secreto existente (ignora el error si no existe)
  sudo docker secret rm "$secret_name" >/dev/null 2>&1 || true
  
  # Crea el nuevo secreto
  printf "%s" "$secret_value" | sudo docker secret create "$secret_name" -
  echo "✅ Secreto '$secret_name' creado/actualizado en Swarm."
}

# --- Lógica Principal ---
echo "🔄 Sincronizando secretos desde .env a Docker Swarm..."
load_env

# Lista de secretos que queremos gestionar. Añade más si es necesario.
upsert_secret "fridge_secret" "$FRIDGE_SECRET"
upsert_secret "grafana_cloud_prometheus_api_key" "$GRAFANA_CLOUD_PROMETHEUS_API_KEY"
upsert_secret "grafana_cloud_loki_api_key" "$GRAFANA_CLOUD_LOKI_API_KEY"

echo "✨ Sincronización de secretos completada."
