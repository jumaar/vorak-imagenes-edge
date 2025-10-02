# Herramienta de Test de Cámaras en Docker

Este proyecto proporciona una solución simple y autocontenida para verificar el funcionamiento de cámaras conectadas a un servidor remoto, especialmente aquellos que no disponen de una interfaz gráfica (headless).

Utiliza un contenedor Docker con OpenCV para capturar el video y lo retransmite a la pantalla de tu computadora local mediante X11 forwarding a través de una conexión SSH.

## ¿Para qué sirve?

El objetivo principal es poder visualizar en tiempo real la imagen de una o más cámaras conectadas a un servidor para:
- Confirmar que el sistema operativo las detecta correctamente.
- Verificar que el hardware de la cámara funciona.
- Asegurarse de que los permisos de acceso al dispositivo (`/dev/video*`) son correctos.

## Requisitos

### En el Servidor:
- **Docker** instalado.
- Acceso a los dispositivos de las cámaras (ej. `/dev/video0`, `/dev/cam_nevera_0`, etc.).

### En tu PC Local:
- Un cliente **SSH**.
- Un **servidor X11**:
    - **Linux**: Ya viene instalado en la mayoría de las distribuciones de escritorio.
    - **macOS**: Requiere instalar XQuartz.
    - **Windows**: Requiere instalar un servidor X11 como VcXsrv o usar MobaXterm (que lo incluye).

## Guía de Uso Rápido

Sigue estos pasos para poner en marcha el visor de cámaras.

### 1. Construir la Imagen Docker (en el servidor)

Primero, clona o copia los archivos (`Dockerfile`, `camara.py`) en tu servidor. Luego, navega a ese directorio y ejecuta:

```bash
docker build -t test-camara .
```

Este comando crea la imagen Docker con todas las dependencias necesarias. Solo necesitas hacerlo una vez.

### 2. Preparar tu PC Local

Abre una terminal en tu computadora y ejecuta el siguiente comando para permitir que aplicaciones externas muestren ventanas en tu pantalla:

```bash
xhost +
```

### 3. Conectar al Servidor con Reenvío Gráfico

Conéctate a tu servidor usando SSH con la bandera `-X`, que habilita el X11 forwarding.

```bash
ssh -X tu_usuario@ip_del_servidor
```

### 4. Lanzar el Visor de Cámaras

Una vez dentro del servidor, ejecuta el contenedor. **Debes personalizar este comando** para que coincida con los nombres de tus dispositivos de cámara.

**Ejemplo de uso:**

Supongamos que tus cámaras son `/dev/cam_nevera_0` y `/dev/cam_nevera_1` en el servidor.

```bash
docker run --rm -it \
  --network host \
  --env DISPLAY=$DISPLAY \
  --volume /tmp/.X11-unix:/tmp/.X11-unix \
  --device /dev/cam_nevera_0:/dev/video0 \
  --device /dev/cam_nevera_1:/dev/video2 \
  --env CAMERA_DEVICES="/dev/video0,/dev/video2" \
  test-camara
```

- `--device /dev/cam_nevera_0:/dev/video0`: Mapea el dispositivo real del servidor (`/dev/cam_nevera_0`) a un nombre estándar (`/dev/video0`) dentro del contenedor.
- `--env CAMERA_DEVICES="/dev/video0,/dev/video2"`: Le dice al script de Python qué dispositivos buscar *dentro* del contenedor.

Las ventanas de las cámaras aparecerán en tu escritorio local. Para salir, haz clic en una de las ventanas y presiona la tecla `q`.

## Archivos del Proyecto

- **`Dockerfile`**: Define el entorno del contenedor. Instala Debian, Python, OpenCV y crea un usuario no-root (`tester`) para mayor seguridad.
- **`camara.py`**: El script de Python que utiliza OpenCV para leer las cámaras en hilos separados y mostrarlas en ventanas. Incluye una lógica robusta para reintentar la conexión si una cámara se desconecta.