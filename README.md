## Sección 2: Despliegue de la Aplicación con Docker Swarm

### 2.1. Inicialización de Swarm y Creación de Secretos

1.  **Inicializar Docker Swarm**: Convierte el nodo en un manager de Swarm.
    ```bash

    docker swarm init

    `sudo docker swarm init --advertise-addr 192.168.0.102 `----> esta es la forma correcta asi sea un solo nodo, modificar ip por la del equipo

    
    ```
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

5.  **Crear la Red Overlay**: Todos los servicios se comunican a través de una red compartida. Debes crearla antes de desplegar cualquier stack.
    ```bash
    docker network create --driver=overlay --attachable vorak-net
    ```
    *   `--driver=overlay`: Crea una red compatible con Swarm.
    *   `--attachable`: Permite conectar contenedores manualmente para depuración.


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

7.  **Exportar Variables de Entorno**: A diferencia de `docker-compose`, `docker stack deploy` no lee el archivo `.env` automáticamente. Debes exportar las variables a tu sesión de terminal antes de desplegar. Esto incluye las variables del archivo `.env` y los GIDs para los permisos de hardware.
    ```bash
    # Exportar variables desde el archivo .env
    export $(cat .env | xargs)

    # Exportar los GIDs para los permisos de hardware
    export VIDEO_GID=$(getent group video | cut -d: -f3)
    export DIALOUT_GID=$(getent group dialout | cut -d: -f3)
    ```
    **Nota**: Este comando debe ejecutarse cada vez que abras una nueva terminal para desplegar o actualizar los stacks.


### 2.2. Despliegue de las Pilas de Servicios (Stacks)

El sistema se divide en dos pilas: la aplicación principal y el monitoreo.

1.  **Desplegar la Pila de Aplicación (`vorak-app`)**:
    Este comando lee `docker-stack.app.yml` y despliega los servicios `nevera` y `kiosko`.
    ```bash
    docker stack deploy --with-registry-auth -c docker-stack.app.yml vorak-app
    ```

2.  **Desplegar la Pila de Monitoreo (`vorak-monitoring`)**:
    Este comando lee `MODULO-MONITORING/docker-stack.monitoring.yml` y despliega los servicios de monitoreo en la misma red.
    ```bash
    docker stack deploy --with-registry-auth -c MODULO-MONITORING/docker-stack.monitoring.yml vorak-monitoring
    ```
    Esta pila incluye:
    *   **Portainer**: Interfaz web para gestionar Docker Swarm. Accesible en `https://<IP_DEL_PC>:9443`.
    *   **Prometheus**: Recolecta métricas de los servicios y del hardware.
    *   **Promtail**: Recolecta logs de todos los contenedores y los envía a Grafana Loki.
    *   **cAdvisor & Node Exporter**: Exponen métricas detalladas de los contenedores y del hardware del nodo.

### 2.3. Configuración de Actualizaciones Automáticas (Webhook)
### 2.3. Gestión y Eliminación de Stacks

Para gestionar los servicios desplegados, puedes usar los siguientes comandos:

```bash
# Listar todos los stacks activos
docker stack ls

# Ver los servicios de un stack específico y su estado
docker stack services vorak-app

# Para detener y eliminar un stack (esto no borra los volúmenes de datos)
docker stack rm vorak-app
docker stack rm vorak-monitoring
```

### 2.4. Configuración de Actualizaciones Automáticas (Webhook)

Se utiliza un webhook de Portainer para que GitHub Actions pueda redesplegar automáticamente la pila de aplicación tras un `push` a la rama principal.

1.  **En Portainer**:
    *   Ve a `Services` -> `vorak_stack_nevera` (o `kiosko`).
    *   **Importante**: Antes de crear el webhook, asegúrate de haber configurado el acceso a tu registro privado (`ghcr.io`) en la sección `Registries` de Portainer, usando tu usuario y un Personal Access Token (PAT) con permisos `read:packages`.
    *   En la sección "Service details", busca "Service webhook" y crea uno.
    *   Al crear el webhook, asegúrate de que la opción **"Re-pull image"** esté activada. Esto fuerza a Portainer a descargar la última versión de la imagen desde el registro, incluso si la etiqueta (como `:latest`) no ha cambiado.
    *   Copia la URL del webhook.
2.  **En GitHub**:
    *   Ve a `Settings` -> `Secrets and variables` -> `Actions` en tu repositorio.
    *   Crea un nuevo "Repository secret" llamado `PORTAINER_WEBHOOK_URL` y pega la URL que copiaste.

El workflow de GitHub Actions (`.github/workflows/deploy.yml`) usará este secreto para notificar a Portainer que debe actualizar el servicio con la nueva imagen de Docker Hub.

---