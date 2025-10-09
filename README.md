# Proyecto Vorak Edge: Sistema de Nevera Inteligente

Este repositorio contiene la infraestructura y el código para el sistema de neveras inteligentes "Vorak Edge", gestionado completamente a través de Docker.

## Arquitectura Modular

El sistema se compone de los siguientes servicios Docker: `nevera`, `kiosko`, `backup`, `monitoring` (Prometheus, Promtail, etc.) y `deployer`.

---

## 1. Instalación Inicial

1.  **Requisitos**: `git`, `docker` y `docker-compose`.

2.  **Clonar el repositorio**:
    ```bash
    git clone <URL_DEL_REPOSITORIO> /ruta/de/instalacion
    cd /ruta/de/instalacion
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
    docker compose -p vorak-edge up -d
    ```

---

## 2. Comandos de Gestión

### Ver Logs
```bash
# Log del proceso de despliegue
tail -f deploy.log

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

Para acceder a una terminal (shell) dentro de un contenedor en ejecución, puedes usar los siguientes comandos. Esto es útil para revisar logs, verificar archivos o ejecutar comandos manualmente.

**Acceder al contenedor del Kiosko:**
```bash
docker compose -p vorak-edge exec kiosko sh```

**Acceder al contenedor de la Nevera:**
```bash
docker compose -p vorak-edge exec nevera sh
``` 

** para acceder al contenedor de deployer**
`docker compose -p vorak-edge run deployer sh`

*Acceder a los logs del despliegue:**
```bash
tail -f deploy.log
```
---
