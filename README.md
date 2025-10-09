# Proyecto Vorak Edge: Sistema de Nevera Inteligente

Este repositorio contiene la infraestructura y el código para el sistema de neveras inteligentes "Vorak Edge". La solución está diseñada para funcionar en dispositivos de borde (edge devices) y se gestiona completamente a través de Docker, organizándose en varios módulos interconectados.

## Arquitectura Modular

El sistema se compone de los siguientes módulos principales, cada uno ejecutándose en su propio contenedor Docker:

-   **`nevera`**: El cerebro del sistema. Procesa las imágenes de las cámaras, gestiona el inventario y se comunica con el hardware (ESP32) y el backend en la nube.
-   **`kiosko`**: La interfaz de usuario web. Muestra publicidad, información del producto y gestiona el webhook para las actualizaciones automáticas.
-   **`backup`**: Un servicio liviano que realiza copias de seguridad periódicas de los datos críticos (transacciones offline y sesiones de revisión).
-   **`monitoring`**: Una pila de monitoreo compuesta por `Prometheus`, `Promtail`, `cAdvisor` y `Node-Exporter` para recolectar métricas y logs del sistema y enviarlos a una instancia de Grafana Cloud.
-   **`deployer`**: Un contenedor de utilidad que se usa exclusivamente para orquestar el proceso de redespliegue de la aplicación de forma segura.

---

## 1. Requisitos Previos

Antes de comenzar, asegúrate de tener instalado lo siguiente en tu dispositivo de borde:

-   **Git**: Para clonar el repositorio.
-   **Docker**: Para ejecutar los contenedores.
-   **Docker Compose**: Para orquestar los servicios.
-   **Credenciales de `ghcr.io`**: Un **Personal Access Token (PAT)** de GitHub con permisos de `read:packages` para descargar las imágenes privadas de los contenedores.

---

## 2. Instalación y Configuración Inicial

Sigue estos pasos para poner en marcha el sistema por primera vez.

### 2.1. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO> /ruta/de/instalacion
cd /ruta/de/instalacion
```

### 2.2. Autenticarse en el Registro de Contenedores

Las imágenes de Docker son privadas. Inicia sesión en el registro de contenedores de GitHub (`ghcr.io`) para poder descargarlas.

```bash
docker login ghcr.io
```

-   **Username**: Tu usuario de GitHub.
-   **Password**: El Personal Access Token (PAT) que creaste.

### 2.3. Crear el Archivo de Entorno (`.env`)

Copia el archivo de plantilla `.env.template` a un nuevo archivo llamado `.env` y rellena las variables.

```bash
cp .env.template .env
nano .env
```

Asegúrate de configurar correctamente todas las variables, incluyendo `FRIDGE_ID`, las URLs de Grafana Cloud y las credenciales `GHCR_USER` y `GHCR_TOKEN` para el redespliegue automático.

---

## 3. Despliegue de los Servicios

Una vez configurado el archivo `.env`, puedes levantar toda la pila de servicios con un solo comando.

```bash
# El flag -p define un nombre de proyecto para evitar conflictos.
docker compose -p vorak-edge up -d
```

Este comando leerá el archivo `docker-compose.yml`, descargará las imágenes necesarias y creará e iniciará todos los contenedores en segundo plano (`-d`).

---

## 4. Proceso de Actualización Automatizado

El sistema está diseñado para actualizarse automáticamente cuando se realiza un `push` a la rama `main` del repositorio.

El flujo es el siguiente:

1.  **GitHub Actions** notifica al servicio **`kiosko`** a través de un webhook.
2.  El **`kiosko`** ejecuta el script local `gitpull.sh`.
3.  El script `gitpull.sh` realiza las siguientes acciones clave:
    ```bash
    # 1. Asegura que Git pueda operar en el directorio montado.
    git config --global --add safe.directory /project

    # 2. Descarga los últimos cambios del repositorio.
    git fetch origin main
    git reset --hard origin/main

    # 3. Lanza el contenedor 'deployer' para actualizar la pila.
    docker compose -p vorak-edge run -T --rm deployer ./deploy.sh
    ```
4.  El contenedor `deployer` ejecuta el script `deploy.sh`, que a su vez:
    ```bash
    # 1. Se autentica de nuevo en ghcr.io usando las variables del .env.
    docker login ghcr.io -u "$GHCR_USER" --password-stdin

    # 2. Descarga las versiones más recientes de todas las imágenes.
    docker compose -p vorak-edge pull

    # 3. Redespliega los servicios con las nuevas imágenes.
    docker compose -p vorak-edge up -d --remove-orphans

    # 4. Limpia imágenes de Docker antiguas.
    docker image prune -f
    ```

Este proceso garantiza una actualización segura y atómica de la aplicación sin intervención manual.

---

## 5. Administración y Mantenimiento

A continuación se muestran algunos comandos útiles para gestionar y monitorear el sistema.

### 5.1. Ver Logs de los Contenedores

Para diagnosticar problemas, puedes ver los logs de cada contenedor en tiempo real.

```bash
# Ver logs del servicio 'nevera' (el cerebro)
docker compose -p vorak-edge logs -f nevera

# Ver logs del servicio 'kiosko' (la interfaz web)
docker compose -p vorak-edge logs -f kiosko

# Ver logs del servicio de backups
docker compose -p vorak-edge logs -f backup

# Ver logs de Prometheus
docker compose -p vorak-edge logs -f prometheus

# Ver logs de Promtail (recolector de logs)
docker compose -p vorak-edge logs -f promtail
```


### 5.2. Comandos Generales de Docker Compose

```bash
# Listar todos los contenedores del proyecto y su estado
docker compose -p vorak-edge ps

# Detener y eliminar todos los contenedores del proyecto
# (No borra los volúmenes de datos como la base de datos o las colas)
docker compose -p vorak-edge down

# Forzar una actualización manual (mismo proceso que el deployer)
docker compose -p vorak-edge pull
docker compose -p vorak-edge up -d --remove-orphans

---

### Comandos de Depuración

Para acceder a una terminal (shell) dentro de un contenedor en ejecución, puedes usar los siguientes comandos. Esto es útil para revisar logs, verificar archivos o ejecutar comandos manualmente.

**Acceder al contenedor del Kiosko:**
```bash
docker compose -p vorak-edge exec kiosko sh```

**Acceder al contenedor de la Nevera:**
```bash
docker compose -p vorak-edge exec nevera sh
```