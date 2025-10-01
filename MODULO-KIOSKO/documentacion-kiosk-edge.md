
# Guía Maestra: Configuración de Kiosko Minimalista en el servidor Debian

## Filosofía
Crear un sistema seguro con dos usuarios:
1.  **`nevera1` (Administrador):** Un usuario con contraseña y privilegios `sudo` que gestiona toda la lógica del negocio de forma segura en segundo plano.
2.  **`kiosk` (Kiosko):** Un usuario sin privilegios y sin contraseña que se encarga únicamente de mostrar la pantalla de publicidad.

  



  

## TAREAS   --> V. 0.1

nota: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elimina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- En que version de este modulo estamos para git?  -> 0.3






---
### Gestionar el Servicio -USO DIARIO

Una vez guardado el archivo, ejecute los siguientes comandos para gestionar el servicio:

```bash
# Recargar systemd para que reconozca el nuevo servicio
sudo systemctl daemon-reload

# Habilitar el servicio para que arranque automáticamente
sudo systemctl enable kiosk-app.service

# Iniciar el servicio manualmente por primera vez
sudo systemctl start kiosk-app.service

# Verificar el estado para asegurarse de que está corriendo sin errores
sudo systemctl status kiosk-app.service

# Pasar  la carpeta completa del kisko al servidor
``scp -r "D:\Desktop\GITHUB jumaar\vorak\MODULO-NEVERA\modulo-kiosk-edge" nevera1@ssh-nevera1.lenstextil.com:~/MODULO-NEVERA`` 

```








## Fase 1: Preparación de Usuarios y Permisos

### 1.1. Crear Usuario Administrador (`nevera1`)
Este usuario será el dueño de la aplicación principal (`app.py`, `kiosk.py`,`cloudflared`, etc.).

```bash
# Crear el usuario
sudo adduser nevera1

# Otorgarle los permisos necesarios:
# - sudo: para administrar el sistema
# - dialout/tty: para acceder al puerto serie del ESP32
# - video/input: para acceder a las cámaras y otros dispositivos
sudo usermod -aG sudo,dialout,tty,video,input nevera1
```

### 1.2. Crear Usuario del Kiosko (`kiosk`)
Este usuario no tendrá contraseña y solo podrá ejecutar el navegador.

```bash
# Crear el usuario sin pedir contraseña
sudo adduser --disabled-password --gecos "" kiosk

# Darle los permisos mínimos para controlar la pantalla y dispositivos de entrada
sudo usermod -aG tty,video,input kiosk
```

### 1.3. Asegurar el Directorio del Administrador
Para que el usuario `kiosk` no pueda ver ni modificar los archivos de la aplicación.

```bash
sudo chmod 750 /home/nevera1
```

---

## Fase 2: Configuración del Contenido del Kiosko

### 2.1. Crear Script de Sesión (`.xsession`)
Este archivo le dice al sistema gráfico qué programas lanzar cuando el usuario `kiosk` inicia sesión.

1.  Cree el archivo:
    ```bash
    sudo nano /home/kiosk/.xsession
    ```

2.  Añada el siguiente contenido:
    ```bash
    #!/bin/bash

    # 1. Desactivar el salvapantallas y el modo de ahorro de energía del monitor.
    #    Esto es crucial para que la pantalla del kiosko nunca se apague.
    xset s off -dpms

    # 2. Iniciar el gestor de ventanas Openbox en segundo plano.
    #    El '&' al final es vital para que el script no se detenga aquí.
    openbox &

    # 3. Bucle infinito para mantener Chromium siempre abierto.
    #    Si el navegador falla o se cierra, este bucle lo volverá a lanzar.
    while true; do
  # Lanzamos Chromium en modo kiosko apuntando a una de las cámaras de Motion.
  # Las opciones adicionales ocultan barras de información y mensajes de error.
  chromium --kiosk --no-first-run --disable-infobars --disable-dev-tools --disable-features=Translate  "http://localhost:5000"
  # Esperamos 5 segundos antes de reintentar si se cierra.
  sleep 5
done
    ```

### 2.2. Crear Script de Perfil (`.bash_profile`)
Este script se ejecuta cuando `kiosk` inicia sesión y es el que arranca la parte gráfica.

1.  Cree el archivo:
    ```bash
    sudo nano /home/kiosk/.bash_profile
    ```

2.  Añada el siguiente contenido:
    ```bash
    # Si estamos en la consola física (tty1), iniciar la sesión gráfica sin cursor
    if [ "$(tty)" = "/dev/tty1" ]; then
      startx -- -nocursor
    fi
    ```

### 2.3. Asignar Permisos Correctos
Los scripts deben pertenecer al usuario `kiosk` y ser ejecutables.

```bash
# Dar propiedad de los archivos al usuario kiosk
sudo chown kiosk:kiosk /home/kiosk/.xsession /home/kiosk/.bash_profile

# Darles permiso de ejecución
sudo chmod +x /home/kiosk/.xsession /home/kiosk/.bash_profile
```

---

## Fase 3: Configuración del Arranque Automático

### 3.1. Crear Servicio de Autologin
Modificaremos el servicio de la terminal `autologin` para que inicie sesión automáticamente con el usuario `kiosk`.

1.  Ejecute el comando para crear el servicio. Esto crea un archivo de de un servicio completamente nuevo.
    ```bash
    `sudo nano /etc/systemd/system/autologin@.service
    ```

2.  Añada el siguiente contenido en el editor que se abrirá:

[Unit]
Description=Automatic login service for console %I
After=systemd-user-sessions.service

[Service]
ExecStart=-/sbin/agetty --autologin kiosk --noclear %I $TERM
Type=idle
Restart=always
RestartSec=0
UtmpIdentifier=%I
TTYPath=/dev/%I
TTYReset=yes
TTYVHangup=yes
KillMode=process
IgnoreSIGPIPE=no
SendSIGHUP=yes

[Install]
WantedBy=getty.target

    Guarde y cierre el archivo.

3. habilitemos el servicio 

` sudo systemctl enable autologin@tty1.service`

### 3.2. Establecer Modo de Arranque por Defecto
Aseguramos que el sistema arranque en modo multi-usuario (línea de comandos), que es lo que necesita nuestro script para lanzar la sesión gráfica.

```bash
sudo systemctl set-default multi-user.target
```

### 3.3. Reiniciar y Verificar
Reinicie el servidor para aplicar todos los cambios.

```bash
sudo reboot
```

Al reiniciar, el sistema debería iniciar sesión automáticamente como `kiosk` y, tras unos segundos, mostrar el navegador Chromium en pantalla completa apuntando a `http://localhost:5000`.


---

## Fase 4: El Servidor del Kiosko (`kiosk.py`)

El navegador del usuario `kiosk` apunta a `http://localhost:5000`. Esta dirección es servida por el script `kiosk.py`, que debe estar ejecutándose en segundo plano bajo el usuario `nevera1`.

Este script es un servidor web autocontenido que cumple dos funciones principales:
- **Proyector:** Sirve la página web (`index.html`) que se muestra en la pantalla.
- **Mensajero:** Se comunica con el `MODULO-ADMIN` para descargar la publicidad.

### 4.1. Estructura del Servidor
El script `kiosk.py` se compone de tres partes lógicas:

1.  **Hilo Sincronizador (`sync_with_admin_backend`):**
    - Se ejecuta en segundo plano de forma continua.
    - Cada `SYNC_INTERVAL_SECONDS` (20 minutos, configurable), se conecta a la `KIOSK_BACKEND_URL` para buscar nuevo contenido.
    - **Se autentica de forma segura** usando una `ADMIN_API_KEY` secreta que se envía en las cabeceras de la petición.
    - Descarga la playlist (un archivo JSON con la lista de medios y su duración) desde el backend.
    - Verifica los medios (imágenes/videos) de la playlist y descarga aquellos que no existan en la caché local (`media_cache`).
    - Guarda la playlist actualizada en el archivo `playlist.json`.

2.  **Servidor Web Flask (`app`):**
    - `@app.route('/')`: Sirve la página principal `templates/index.html`.
    - `@app.route('/api/status')`: Es una API interna que el JavaScript de la página consulta cada pocos segundos. Lee el archivo `fridge_status.json` (que es actualizado constantemente por `app.py`) y devuelve el estado de la nevera (temperatura, puerta, etc.).
    - `@app.route('/api/playlist')`: Otra API interna que el JavaScript consulta para obtener la lista de reproducción desde el archivo `playlist.json`.
    - `@app.route('/media/<filename>')`: Sirve los archivos de medios (imágenes, videos) que han sido descargados y cacheados en la carpeta `media_cache`.

### 4.2. Punto de Entrada y Ejecución
La ejecución del servidor se orquesta en el bloque `if __name__ == '__main__':`. Esto es lo que sucede cuando se ejecuta `python kiosk.py`:

1.  Se asegura de que el directorio de caché `media_cache` exista.
2.  Crea un `threading.Event()` que servirá como señal para detener el hilo de sincronización de forma limpia.
3.  Crea e inicia el hilo `sync_with_admin_backend` para que comience a buscar playlists en segundo plano.
4.  Inicia el servidor web Flask (`app.run(...)`), que se queda escuchando peticiones en el puerto 5000. Esta es la parte principal y bloqueante del script.
5.  Si el servidor se detiene (ej. con `Ctrl+C`), el bloque `finally` se asegura de enviar la señal de parada al hilo de sincronización para que termine su ejecución de forma ordenada.

---

## Fase 5: Ejecutar `kiosk.py` como un Servicio en DEBIAN

Para asegurar que el servidor del kiosko se inicie automáticamente con el sistema y se mantenga siempre activo, lo configuraremos como un servicio de `systemd`.

### 5.1. Crear el Archivo de Servicio

1.  Cree un nuevo archivo de servicio:
    ```bash
    sudo nano /etc/systemd/system/kiosk-app.service
    ```

2.  Añada la siguiente configuración. **¡Ajuste las rutas si es necesario!**
    ```ini
[Unit]
    Description=Servicio de la App Kiosko (Servidor Web Flask)
    # Le decimos que espere a que la red esté lista para arrancar.
    After=network.target
    
[Service]
    # Se ejecuta como nuestro usuario seguro que maneja la lógica.
    User=nevera1
    Group=nevera1
    
    # El directorio de trabajo donde se encuentra kiosk.py
    WorkingDirectory=/home/nevera1/MODULO-NEVERA/modulo-kiosk-edge
    
    # El comando de ejecución. Usa el mismo entorno virtual que app.py.
    ExecStart=/home/nevera1/MODULO-NEVERA/venv/bin/python3 /home/nevera1/MODULO-NEVERA/modulo-kiosk-edge/kiosk.py
    
    # Política de reinicio para que siempre esté activo.
    Restart=always
    RestartSec=5
    
[Install]
    WantedBy=multi-user.target
    ```

