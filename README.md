# Proyecto Vorak Edge: Sistema de Nevera Inteligente

Este repositorio contiene la infraestructura y el código para el sistema de neveras inteligentes "Vorak Edge", gestionado completamente a través de Docker.

## Arquitectura Modular

El sistema se compone de los siguientes servicios Docker: `nevera`, `kiosko`, `backup`, `monitoring` (Prometheus, Promtail, node-exporter) y `backup`.

---

## 1. Instalación Inicial

1.  **Requisitos**: `git`, `docker` y `docker-compose`.

2.  **Clonar el repositorio**:
    ```bash
    `git clone https://github.com/jumaar/vorak-imagenes-edge.git
    `cd vorak-imagenes-edge`
    ```

3.  **Autenticarse en el registro de Docker**:
    ```bash
    # Usa tu usuario de GitHub y un Personal Access Token (PAT) con permisos `read:packages`.
    docker login ghcr.io
    ```

4.  **Crear y configurar el archivo de entorno**:
    ```bash
    cp .env.template .env
    nano .env
    ```
    Rellena todas las variables, especialmente `FRIDGE_ID`, las credenciales de Grafana y `GHCR_USER`/`GHCR_TOKEN`.

5.  **Desplegar la aplicación**:
    ```bash
    # El flag -p define un nombre de proyecto para evitar conflictos.
    `docker compose -p vorak-edge up -d`
    ```

---
---

---

## Apéndice A: Solución de Problemas de Conexión SSH

Esta sección sirve como referencia rápida si los despliegues automáticos fallan por problemas de autenticación SSH. Dado que los dispositivos se clonarán, esta configuración solo debería necesitarse una vez.

### Puntos Clave de la Configuración

1.  **Clave Pública vs. Privada**:
    -   La **Clave Pública** (`~/.ssh/id_ed25519.pub`) es la "cerradura". Se instala en el dispositivo IoT, dentro del archivo `~/.ssh/authorized_keys` del usuario de despliegue (ej: `nevera1`).
    -   La **Clave Privada** (`~/.ssh/id_ed25519`) es la "llave". Debe ser secreta y su contenido se copia en el secreto `IOT_PRIVATE_KEY` de GitHub.

2.  **Secretos de GitHub (`Settings > Secrets and variables > Actions`)**:
    -   `IOT_USERNAME`: Usuario para el despliegue (ej: `nevera1`).
    -   `IOT_PRIVATE_KEY`: Contenido completo de la clave **privada**, incluyendo `-----BEGIN...` y `-----END...`.
    -   `IOT_PASSPHRASE`: La contraseña de la clave privada, si tiene una.

3.  **Permisos en el Dispositivo IoT**:
    Los permisos incorrectos son una causa común de fallos. El directorio `.ssh` y su contenido deben ser privados para el usuario.
    ```bash
    # Ejecutar como el usuario de despliegue (ej: nevera1) en el dispositivo
    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/authorized_keys
    ```

### Diagnóstico Rápido de Errores Comunes

-   **`ssh: no key found`**: El contenido del secreto `IOT_PRIVATE_KEY` es incorrecto. Asegúrate de que sea la clave **privada** completa.
-   **`ssh: this private key is passphrase protected`**: La clave privada tiene contraseña. Asegúrate de que el secreto `IOT_PASSPHRASE` exista y contenga la contraseña correcta.
-   **`i/o timeout`**: Problema de red. En nuestro caso, se solucionó configurando el workflow para usar el túnel de Cloudflare (`cloudflared`).
-   **`Permission denied (publickey)`**: La clave pública no está correctamente añadida en `authorized_keys` en el dispositivo, o los permisos de los archivos/directorios `.ssh` son incorrectos.

---

## 2. Gestión y Operaciones

### Descargar y Limpiar Sesiones para Revisión

Cuando una sesión de compra tiene baja confianza, los videos se guardan en la `review_queue` en el dispositivo. Para descargarlos a tu PC y borrarlos del dispositivo para liberar espacio, usa el script `get_reviews.sh`.

**Este proceso se debe ejecutar desde el PC de desarrollo, no en la nevera.**

1.  **Dar permisos de ejecución al script (solo la primera vez)**:
    ```bash
    chmod +x get_reviews.sh
    ```

2.  **Ejecutar el script desde la raíz del proyecto**:
    ```bash
    ./get_reviews.sh
    ```

El script se conectará a la nevera, descargará los archivos y los guardará en una nueva carpeta llamada `downloaded_reviews` en el directorio actual de tu PC. Si la descarga es exitosa, borrará los archivos del dispositivo remoto para liberar espacio.

---

## 3. Comandos de Gestión


# Ver logs del servicio 'nevera' (el cerebro)
docker compose -p vorak-edge logs -f nevera

# Ver logs del servicio 'kiosko' (la interfaz web)
docker compose -p vorak-edge logs -f kiosko
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

# revisar los eventos entiempo real de la red de docker que se quiera ver
docker events --filter 'network=vorak-edge_vorak-net'
---


### Comandos de Depuración
```
Para acceder a una terminal (shell) dentro de un contenedor en ejecución, puedes usar los siguientes comandos. Esto es útil para revisar logs, verificar archivos o ejecutar comandos manualmente.

**Acceder al contenedor del Kiosko:**
```bash
docker compose -p vorak-edge exec kiosko sh```

**Acceder al contenedor de la Nevera:**
```bash
docker compose -p vorak-edge exec nevera sh```
**parar el servicio `
ps aux | grep 'app.py'
``` 


## Próximos Pasos (Flujo de Trabajo)

1.  **Desarrollo de Nuevas Funcionalidades**:
    - Crea nuevas ramas a partir de `develop` para cada nueva funcionalidad:
      ```bash
      git checkout develop
      git pull origin develop
      git checkout -b feature/nombre-de-la-funcionalidad
      ```
    - Una vez completado el desarrollo, fusiona la rama de funcionalidad de nuevo en `develop`.

2.  **Lanzamiento a Producción**:
    - Fusiona la rama `develop` en `main`.
    - Crea un nuevo tag de Git para versionar el lanzamiento:
      ```bash
      git tag v1.0.1
      git push origin v1.0.1
      ```
