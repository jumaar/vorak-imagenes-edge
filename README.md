## Sección 2: Despliegue de la Aplicación con Docker Compose

### 2.1. Creación de Secretos
2.  **Clonar el Repositorio**:
    ```bash
    git clone <URL_DEL_REPOSITORIO> /home/nevera1/vorak-edge
    cd /home/nevera1/vorak-edge
    ```
3.  **Autenticarse en el Registro de Contenedores (GHCR)**: Las imágenes de la aplicación son privadas. Debes iniciar sesión en el registro de contenedores de GitHub para poder descargarlas.
    *   Primero, crea un **Personal Access Token (PAT)** en GitHub con el único permiso (`scope`) **`read:packages`**.
    *   Luego, ejecuta el siguiente comando en tu terminal:
        ```bash
        docker login ghcr.io
        ```
    *   **Username**: Tu usuario de GitHub.
    *   **Password**: El Personal Access Token que acabas de crear.

4.  **Crear Secretos**: Los secretos se usan para gestionar información sensible como claves de API y contraseñas.
    *   **Secreto de la Nevera**: Clave para autenticación JWT con el backend.
        ```bash
        docker secret create fridge_secret -
        # Pega la clave secreta y presiona Ctrl+D.
        ```
    *   **Secretos de Grafana Cloud**: Claves de API para enviar métricas y logs.
        ```bash
        # Clave para Prometheus (métricas)
        printf "TU_API_KEY_DE_PROMETHEUS" | docker secret create grafana_cloud_prometheus_api_key -
        # Clave para Loki (logs)
        printf "TU_API_KEY_DE_LOKI" | docker secret create grafana_cloud_loki_api_key -
        ```

5.  **Crear la Red**: Todos los servicios se comunican a través de una red compartida. `docker-compose` la creará automáticamente, pero si se necesita crearla manualmente:
    ```bash
    docker network create vorak-net
    ```


6.  **Crear Archivo de Entorno (`.env`)**: Este archivo configura variables no sensibles. Crea `nano .env` en la raíz del proyecto:
    ```env
    # --- Configuración General de la Aplicación ---
    FRIDGE_ID="NEVERA-001-SANTAROSA"
    BASE_BACKEND_URL="https://api.lenstextil.com"
    
    # --- Configuración de Monitoreo (Grafana Cloud) ---
    GRAFANA_CLOUD_PROMETHEUS_URL="<Pega aquí la URL de Remote Write de Prometheus>"
    GRAFANA_CLOUD_PROMETHEUS_USER="<Pega aquí el Username/Instance ID de Prometheus>"
    GRAFANA_CLOUD_LOKI_URL="<Pega aquí la URL de Loki>"
    GRAFANA_CLOUD_LOKI_USER="<Pega aquí el User de Loki>"
    
    # --- Configuración del Host para Docker ---
    UID=1000
    GID=1000
    DISPLAY=:0
    ```

7.  **Variables de Entorno**: `docker-compose` lee el archivo `.env` automáticamente. Asegúrate de que esté creado en la raíz del proyecto.
    ```bash
    # Exportar variables desde el archivo .env
    export $(cat .env | xargs)

    # Exportar los GIDs para los permisos de hardware
    export VIDEO_GID=$(getent group video | cut -d: -f3)
    export DIALOUT_GID=$(getent group dialout | cut -d: -f3)
    ```
    **Nota**: Si necesitas exportar variables adicionales que no están en el `.env`, puedes hacerlo en tu terminal.


### 2.2. Despliegue de los Servicios con Docker Compose

1.  **Desplegar todos los servicios**:
    Este comando lee el archivo `docker-compose.yml` y levanta todos los servicios definidos en él.
    ```bash
    docker-compose up -d
    ```
    Esto incluye:
    *   **Aplicación**: Servicios `nevera` y `kiosko`.
    *   **Monitoreo**: Servicios como `Portainer`, `Prometheus`, etc.
    *   **Portainer**: Interfaz web para gestionar Docker. Accesible en `https://<IP_DEL_PC>:9443`.
    *   **Prometheus**: Recolecta métricas de los servicios y del hardware.
    *   **Promtail**: Recolecta logs de todos los contenedores y los envía a Grafana Loki.
    *   **cAdvisor & Node Exporter**: Exponen métricas detalladas de los contenedores y del hardware del nodo.

3.  **El servicio backup** 
    es un contenedor muy simple basado en alpine:latest (una imagen de Linux muy ligera). Su única  tarea es ejecutar un script (backup.sh) cada 24 horas. 
            El backup está diseñado para copiar los datos más críticos que genera el servicio nevera y que no se pueden recuperar si se pierden:

        nevera_offline_queue: Es la cola de transacciones que no se pudieron enviar al backend por falta de conexión. ¡Es vital respaldar esto para no perder ventas!
        nevera_review_queue: Son las imágenes de las sesiones de compra que el sistema marcó como "baja confianza". Son importantes para auditoría y para mejorar el sistema.

        En resumen: El backup toma los datos de las colas, los comprime y guarda el archivo resultante en el volumen backup_data, todo dentro del mismo PC.


### 2.3. Configuración de Actualizaciones Automáticas (Webhook)
### 2.3. Gestión y Eliminación de Servicios

Para gestionar los servicios desplegados, puedes usar los siguientes comandos:

```bash
# Listar los contenedores activos del proyecto
docker-compose ps

# Ver los logs de un servicio en tiempo real
docker-compose logs -f nevera

# Para detener y eliminar los contenedores (esto no borra los volúmenes de datos)
docker-compose down
```

### 2.4. Configuración de Actualizaciones Automáticas (Webhook)

Se utiliza un webhook de Portainer para que GitHub Actions pueda redesplegar automáticamente la pila de aplicación tras un `push` a la rama principal.

1.  **En Portainer**:
    *   Ve a `Containers` -> `vorak-nevera-1` (o el nombre del contenedor que desees).
    *   **Importante**: Antes de crear el webhook, asegúrate de haber configurado el acceso a tu registro privado (`ghcr.io`) en la sección `Registries` de Portainer, usando tu usuario y un Personal Access Token (PAT) con permisos `read:packages`.
    *   En la sección "Service details", busca "Service webhook" y crea uno.
    *   Al crear el webhook, asegúrate de que la opción **"Re-pull image"** esté activada. Esto fuerza a Portainer a descargar la última versión de la imagen desde el registro, incluso si la etiqueta (como `:latest`) no ha cambiado.
    *   Copia la URL del webhook.
2.  **En GitHub**:
    *   Ve a `Settings` -> `Secrets and variables` -> `Actions` en tu repositorio.
    *   Crea un nuevo "Repository secret" llamado `PORTAINER_WEBHOOK_URL` y pega la URL que copiaste.

El workflow de GitHub Actions (`.github/workflows/deploy.yml`) usará este secreto para notificar a Portainer que debe actualizar el servicio con la nueva imagen de Docker Hub.

---