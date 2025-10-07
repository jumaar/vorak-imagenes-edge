# Guía de Arquitectura y Operación: Módulo Kiosko v0.3 (Refactorizado para Docker Compose)

## Filosofía

Este sistema está diseñado como una aplicación robusta y desacoplada que utiliza contenedores Docker para separar sus dos componentes principales:

1.  **`nevera` (Contenedor de Lógica):** Un servicio de backend sin interfaz gráfica que gestiona toda la lógica de negocio, la comunicación con el hardware (cámaras, sensores) y la sincronización con el servidor central.

2.  **`kiosko` (Contenedor de Aplicación Web):** Un servicio que contiene un servidor web ligero. Su única función es servir la aplicación web (HTML, CSS, JS) y las APIs necesarias para la interfaz de usuario.

Esta separación simplifica drásticamente el contenedor del kiosko, que ya no necesita gestionar un entorno gráfico. El despliegue se gestiona a través de **Docker Compose** o **Docker Swarm**.
---






## TAREAS  --> V 0.4

NOTA: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- Tarea fija: En que version de este modulo estamos para git?  -> 0.4










## Arquitectura Docker

El sistema se orquesta a través de `docker-compose.yml`, que define y conecta los dos servicios principales.

### 1. Servicio `nevera`

- **Propósito:** Es el cerebro del sistema. Se encarga de la lógica de la máquina expendedora.
- **Comunicación:** Se comunica con el servicio `kiosko` de forma indirecta a través de un **volumen Docker compartido** (`fridge_status`). El servicio `nevera` escribe el estado actual (temperatura, estado de la puerta, etc.) en un archivo `fridge_status.json` dentro de este volumen.

### 2. Servicio `kiosko`

- **Propósito Dual:**
    1.  **Interfaz de Usuario:** Sirve la aplicación web (HTML, CSS, JS) a la que accede el navegador del dispositivo físico.
    2.  **Orquestador de Despliegue:** Actúa como el cerebro del proceso de CI/CD, recibiendo notificaciones (webhooks) para actualizar todo el stack de la aplicación de forma automática.

- **Componentes Clave:**
    - **`Dockerfile`:** Construye una imagen Python ligera (basada en Alpine) que incluye el cliente de Docker (`docker-cli`). Esto es fundamental para que el contenedor pueda interactuar con el Docker socket del host y gestionar otros contenedores.
    - **`kiosk.py`:** Un servidor web Flask que cumple dos funciones críticas:
        1.  **APIs para la UI:** Proporciona endpoints para que el frontend consulte datos dinámicos, como la playlist de medios o el estado actual de la nevera (leyendo `fridge_status.json` del volumen compartido).
        2.  **Webhook de Despliegue (`/update/<secret>`):** Expone un endpoint seguro que, al ser llamado por el pipeline de CI/CD (GitHub Actions), inicia el proceso de actualización. Verifica un secreto compartido para prevenir ejecuciones no autorizadas.
    - **`redeploy.sh` (Internalizado en la imagen):** Este script contiene la lógica para redesplegar los servicios. Es ejecutado por `kiosk.py` al recibir un webhook válido. Sus tareas son:
        1.  Autenticarse en el registro de contenedores (`ghcr.io`) usando credenciales seguras.
        2.  Ejecutar `docker-compose up -d --pull` para descargar las nuevas versiones de las imágenes y actualizar los servicios correspondientes.
    - **`manage-secrets.sh`:** Un script de utilidad, también dentro de la imagen, que podría usarse para gestionar la creación o actualización de secretos de Docker si fuera necesario.

### 3. Conexión con el Entorno Gráfico del Host

El contenedor `kiosko` ya no gestiona el entorno gráfico. En su lugar, el sistema operativo anfitrión (Host OS) debe estar configurado para lanzar un navegador web (como Chromium) en modo kiosko al arrancar. Este navegador apuntará a la dirección del servidor Flask que se ejecuta dentro del contenedor, típicamente `http://localhost:5000`.

- **`network_mode: "host"`:** El contenedor comparte la pila de red del host. Esto es crucial para que pueda conectarse al servidor X11 que se ejecuta en `localhost`.
- **Volúmenes de X11:**
    - `/tmp/.X11-unix:/tmp/.X11-unix`: Se monta el socket del servidor X11 del host dentro del contenedor.
    - `$HOME/.Xauthority:/home/kiosk/.Xauthority`: Se monta el archivo de autorización para permitir que el usuario del contenedor se conecte al servidor X11.
- **`DISPLAY=${DISPLAY}`:** La variable de entorno `DISPLAY` se pasa desde el host al contenedor para que sepa a qué pantalla conectarse.

### 4. Persistencia de Datos

Se utilizan volúmenes nombrados de Docker para asegurar que los datos no se pierdan si los contenedores se recrean:

- **`kiosk_data`:** Persiste la caché de medios (imágenes, videos) y el archivo `playlist.json` descargado por el kiosko.
- **`fridge_status`:** El volumen compartido que actúa como puente de comunicación entre los dos servicios.
- **`nevera_*`:** Varios volúmenes para persistir las bases de datos, colas y logs del servicio `nevera`.

---

## Uso y Mantenimiento

Toda la gestión del ciclo de vida de la aplicación se realiza a través de comandos de Docker Compose.

### Prerrequisitos

1.  **Docker y Docker Compose:** Asegúrese de que ambos estén instalados en el sistema anfitrión.
2.  **Repositorio:** Clone este repositorio en el dispositivo.
3.  **Archivo de Entorno (`.env`):** Cree un archivo `.env` en la raíz del proyecto para configurar las variables específicas del entorno. Por ejemplo:
    ```env
    BASE_BACKEND_URL="https://api.tu-dominio.com"
    FRIDGE_ID="NEVERA-TIENDA-01"
    GRAFANA_CLOUD_PROMETHEUS_URL="https://prometheus-prod-..."
    GRAFANA_CLOUD_PROMETHEUS_USER="123456"
    ```

2.  **Autenticarse en el Registro de Contenedores (GHCR)**: Las imágenes de la aplicación son privadas. Debes iniciar sesión en el registro de contenedores de GitHub para poder descargarlas.
    *   Primero, crea un Personal Access Token (PAT) en GitHub con el permiso (`scope`) **`read:packages`**.
    *   Luego, ejecuta el siguiente comando en tu terminal:
        ```bash
        docker login ghcr.io
        ```
    *   **Username**: Tu usuario de GitHub.
    *   **Password**: El Personal Access Token que acabas de crear.


 
### Comandos de Gestión (Desarrollo Local)
Estos comandos utilizan `docker-compose.yml` para un entorno de desarrollo local. Ejecútelos desde el directorio raíz del proyecto.




```bash
# 1. Construir las imágenes de los contenedores por primera vez
#    (o si se ha modificado un Dockerfile)
sudo docker compose build

# 2. Iniciar todos los servicios en segundo plano (modo detached)
sudo docker compose up -d

# 3. Detener y eliminar los contenedores
sudo docker compose down

# 4. Ver los logs de un servicio en tiempo real (muy útil para depurar)
#    (Use Ctrl+C para salir)
sudo docker compose logs -f kiosko
sudo docker compose logs -f nevera

# 5. Reiniciar los servicios
sudo docker compose restart

# 6. Acceder a un shell dentro de un contenedor en ejecución
#    (para explorar archivos o ejecutar comandos manualmente)
sudo docker exec -it vorak-kiosko /bin/bash
sudo docker exec -it vorak-nevera /bin/bash

---

