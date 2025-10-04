# Guía de Arquitectura y Operación: Módulo Kiosko v0.3 (Refactorizado para Swarm)

## Filosofía

Este sistema está diseñado como una aplicación robusta y desacoplada que utiliza contenedores Docker para separar sus dos componentes principales:

1.  **`nevera` (Contenedor de Lógica):** Un servicio de backend sin interfaz gráfica que gestiona toda la lógica de negocio, la comunicación con el hardware (cámaras, sensores) y la sincronización con el servidor central.

2.  **`kiosko` (Contenedor de Aplicación Web):** Un servicio que contiene un servidor web ligero. Su única función es servir la aplicación web (HTML, CSS, JS) y las APIs necesarias para la interfaz de usuario.

Esta separación simplifica drásticamente el contenedor del kiosko, que ya no necesita gestionar un entorno gráfico. El despliegue se gestiona a través de **Docker Compose** o **Docker Swarm**.
---






## TAREAS  --> V 0.3

NOTA: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- Tarea fija: En que version de este modulo estamos para git?  -> 0.3










## Arquitectura Docker

El sistema se orquesta a través de `docker-stack.yml`, que define y conecta los dos servicios principales.

### 1. Servicio `nevera`

- **Propósito:** Es el cerebro del sistema. Se encarga de la lógica de la máquina expendedora.
- **Comunicación:** Se comunica con el servicio `kiosko` de forma indirecta a través de un **volumen Docker compartido** (`fridge_status`). El servicio `nevera` escribe el estado actual (temperatura, estado de la puerta, etc.) en un archivo `fridge_status.json` dentro de este volumen.

### 2. Servicio `kiosko`

- **Propósito:** Es la cara visible del sistema. Su única función es mostrar la interfaz web en la pantalla del dispositivo físico.
- **Componentes Clave:**
    - **`Dockerfile`:** Construye una imagen Debian con `Xorg`, el gestor de ventanas `Openbox` y `Chromium`. Instala la aplicación Python (`kiosk.py`) en un entorno virtual.
    - **`kiosk.py`:** Un servidor web Flask que sirve la página principal y proporciona APIs internas para que el frontend obtenga la playlist de medios y el estado de la nevera (leyendo el `fridge_status.json` del volumen compartido).
    - **`.xsession`:** Un script de sesión gráfica que se encarga de:
        - Desactivar el salvapantallas.
        - Lanzar el gestor de ventanas `Openbox`.
        - Ejecutar `Chromium` en un bucle infinito para asegurar que siempre esté visible, apuntando al servidor local `http://localhost:5000`.
    - **`entrypoint.sh`:** El script que orquesta el arranque del contenedor:
        1.  Ajusta los permisos de los volúmenes.
        2.  Inicia el servidor `kiosk.py` en segundo plano.
        3.  Lanza la sesión gráfica ejecutando el script `.xsession`.

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

Toda la gestión del ciclo de vida de la aplicación se realiza a través de comandos de Docker swarm.

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
4.  **Secretos de Docker (para Docker Swarm):** Si se despliega en un clúster Swarm, es necesario crear los secretos para las claves sensibles. Ejecute los siguientes comandos e ingrese la clave correspondiente cuando se le solicite.
 
    *   **Secreto de la Nevera:**
        ```bash
        docker secret create fridge_secret -
        ```

    *   **Secreto de Grafana Cloud:**
        ```bash
        docker secret create grafana_cloud_api_key -
        ```
 
### Comandos de Gestión

Estos comandos son para gestionar el entorno de **desarrollo local** y utilizan un archivo `docker-compose.yml` (no el `docker-stack.yml` de producción). Ejecútelos desde el directorio raíz del proyecto.


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

## Despliegue en Docker Swarm (Modo Producción)

Esta guía describe el proceso completo para desplegar la aplicación en un entorno de producción utilizando Docker Swarm en un único nodo.

### Paso 1: Inicializar el Clúster de Swarm

Para que los servicios se comuniquen correctamente, es crucial inicializar el clúster de Swarm indicando la dirección IP privada del dispositivo.

1.  **Obtén la dirección IP privada** del dispositivo. Puedes usar uno de los siguientes comandos:
    ```bash
    # Opción A: Muestra todas las interfaces de red
    ip a

    # Opción B: Intenta mostrar directamente la IP (más directo)
    hostname -I | awk '{print $1}'
    ```
    Busca una IP en el rango de `192.168.x.x`, `10.x.x.x`, o `172.16.x.x`.

2.  **Inicializa Swarm** usando esa dirección IP. Esto asegura que el nodo se anuncie a sí mismo correctamente dentro de la red del clúster.
    ```bash
    # Reemplaza <IP_PRIVADA> con la IP que obtuviste
    sudo docker swarm init --advertise-addr <IP_PRIVADA>
    ```
    Si ya habías inicializado Swarm antes, puede que necesites ejecutar `sudo docker swarm leave --force` primero.

### Paso 2: Crear la Red Overlay Compartida

Todos los servicios (aplicación, monitoreo, etc.) se comunican a través de una red "overlay" de Docker. Debemos crearla antes de desplegar los stacks.

```bash
sudo docker network create --driver=overlay --attachable vorak-net
```
*   `--driver=overlay`: Crea una red que puede extenderse a través de múltiples nodos (aunque aquí solo usemos uno).
*   `--attachable`: Permite que tanto los servicios del stack como contenedores individuales puedan conectarse a ella, útil para depuración.

### Paso 3: Crear los Secretos

Los secretos guardan información sensible como claves de API y contraseñas de forma segura.

```bash
# Secreto para la autenticación de la nevera con el backend
sudo docker secret create fridge_secret -

# Secreto para enviar métricas a Grafana Cloud
sudo docker secret create grafana_cloud_api_key -
```
Después de ejecutar cada comando, pega la clave correspondiente y presiona `Enter`.

### Paso 4: Desplegar los Stacks de Servicios

Con todo preparado, despliega las pilas de servicios usando los archivos `docker-stack.yml`. Es recomendable empezar por la aplicación principal.

1.  **Desplegar el Stack de la Aplicación (Nevera y Kiosko):**
    ```bash
    # Navega al directorio del MODULO-NEVERA o donde esté tu stack principal
    sudo docker stack deploy -c docker-stack.yml vorak-app
    ```

2.  **Desplegar el Stack de Monitoreo (Prometheus, cAdvisor, etc.):**
    ```bash
    # Navega al directorio del MODULO-MONITORING
    sudo docker stack deploy -c docker-stack.monitoring.yml vorak-monitoring
    ```

### Paso 5: Verificar el Despliegue

Para asegurarte de que todos los servicios se han levantado correctamente, puedes usar los siguientes comandos:

```bash
# Muestra los stacks activos
sudo docker stack ls

# Muestra los servicios del stack de la aplicación y su estado (debería mostrar 1/1 replicas)
sudo docker stack services vorak-app

# Muestra los servicios del stack de monitoreo
sudo docker stack services vorak-monitoring

# Muestra todos los contenedores en ejecución en el nodo
sudo docker ps
```
