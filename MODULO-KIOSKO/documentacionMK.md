# Guía de Arquitectura y Operación: Módulo Kiosko v0.2 (Dockerizado)

## Filosofía

Este sistema está diseñado como una aplicación robusta y aislada que utiliza contenedores Docker para separar sus dos componentes principales:

1.  **`nevera` (Contenedor de Lógica):** Un servicio de backend sin interfaz gráfica que gestiona toda la lógica de negocio, la comunicación con el hardware (cámaras, sensores) y la sincronización con el servidor central.
2.  **`kiosko` (Contenedor de Interfaz):** Un servicio que contiene el entorno gráfico mínimo necesario para ejecutar un navegador web (`Chromium`) en modo kiosko a pantalla completa, mostrando la interfaz de usuario y la publicidad.

El uso de Docker proporciona un entorno consistente, seguro y fácil de desplegar, eliminando la necesidad de configurar manualmente el sistema operativo anfitrión.

---






## TAREAS  --> V 0.2 

NOTA: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- Tarea fija: En que version de este modulo estamos para git?  -> 0.3










## Arquitectura Docker

El sistema se orquesta a través de `docker-compose.yml`, que define y conecta los dos servicios principales.

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

Para que el contenedor `kiosko` pueda "dibujar" en la pantalla del sistema anfitrión, se utilizan varias configuraciones clave en `docker-compose.yml`:

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
3.  **Archivo de Entorno:** Cree un archivo `.env` en la raíz del proyecto y configure las variables necesarias, como `BASE_BACKEND_URL`, `FRIDGE_ID` y `FRIDGE_SECRET`.

### Comandos de Gestión

Ejecute estos comandos desde el directorio raíz del proyecto.

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
