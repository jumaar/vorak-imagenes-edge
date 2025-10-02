## USO DIARIO. 

# Conéctate usando el subdominio único de la nevera.
``ssh nevera1@ssh-nevera1.lenstextil.com``

# Verificar el estado de tu aplicación. 
``sudo systemctl status nevera.service``

# parar el servicio de la app.py
``sudo systemctl stop nevera.service``

# VERFICAR los LOGS de tu aplicación. 
``El '-n 100' muestra las últimas 100 líneas, y '--no-pager' lo imprime directo.
``journalctl -u nevera.service -n 100 --no-pager``

este comando muestra los logs desde el ultimo reinicio
`journalctl -b -u nevera.service`

ver losg en tiempo real 
``journalctl -f -u nevera.service``

``# El '-n 20' muestra las últimas 20 líneas.
``tail -n 20 ~/MODULO-NEVERA/fridge_service.log``

# gestion de archivos en el servidor app
``cd ~/MODULO-NEVERA/``  modificar archivo de configuracion  ``nano app.py`` 
reiniciar despues ``sudo systemctl restart nevera.service``

# Entorno virtual para actualizar librerias

1. `` cd ~/MODULO-NEVERA/``  
2. Activa el entorno para "abrir la caja de herramientas".``source venv/bin/activate``

3. Instala la nueva herramienta. Notarás el prefijo (venv). 
(venv) nevera1@...:~$ pip install opencv-python requests pyserial python-dotenv Flask PyJWT

4. desactivar el entorno.
(venv) nevera1@...:~$ deactivate

5. reiniciar de nuevo 
 ``sudo systemctl restart nevera.service``

# copiar carpetas o archivos desde el servidor cambiar el --> nevera1@ssh-nevera1.lenstextil.com

Con este comando se pueden copiar carpetas o archivos desde el servidor desde linux a wimdows o al pc de administracion. 
`` scp -r nevera1@ssh-nevera1.lenstextil.com:/home/nevera1/MODULO-NEVERA/review_queue/ .``
nota : estar ubicados en en la terminal donde se quiere guardar la carpeta

 Pasar el app.py al servidor
``scp "D:\Desktop\GITHUB jumaar\vorak\MODULO-NEVERA\app.py" nevera1@ssh-nevera1.lenstextil.com:/home/nevera1/MODULO-NEVERA/``

Pasar  la carpeta completa del kisko al servidor
``scp -r "D:\Desktop\GITHUB jumaar\vorak\MODULO-NEVERA\modulo-kiosk-edge" nevera1@ssh-nevera1.lenstextil.com:~/MODULO-NEVERA`` 






### manjeo de instalacion de camaras

Claro que sí! Aquí tienes un resumen de todo el proceso de depuración que hicimos, partiendo del problema que tenías con las rutas de ls -l /dev/v4l/by-path/.

Resumen del Proceso de Depuración
El Problema Original:

Identificaste correctamente que para usar dos cámaras idénticas, necesitabas sus rutas por puerto físico, que obtuviste con ls -l /dev/v4l/by-path/.
El problema fue que estas rutas (ej. pci-0000:00:14.0-usbv2-0:4:1.0-video-index0) contienen dos puntos (:).
Docker Compose usa los dos puntos para separar la ruta del host de la ruta del contenedor (ej. HOST:CONTENEDOR), lo que causaba errores como too many colons o confusing device mapping.
Intentos Fallidos (y por qué):

Intentamos usar la "sintaxis larga" en la sección volumes, pero Docker Compose seguía teniendo problemas para interpretar esas rutas complejas.
Sugerimos usar /dev/v4l/by-id/, pero tú acertadamente nos corregiste, explicando que al ser cámaras idénticas, no tenían IDs únicos, por lo que by-path era la única opción.
La Solución Definitiva: Reglas udev Como no podíamos cambiar las rutas de las cámaras ni la sintaxis de Docker, decidimos "engañar" al sistema creando nuestros propios nombres de dispositivo, limpios y predecibles.

¿Qué hicimos? Creamos un archivo de reglas en el sistema anfitrión (la nevera) en /etc/udev/rules.d/99-vorak-cameras.rules.
¿Qué hace esa regla? Le dice al sistema operativo Linux:
"Cada vez que detectes una cámara conectada en el puerto físico ...usbv2-0:1:1.0..., en lugar de solo llamarla video0, créale también un alias (un acceso directo) llamado /dev/cam_nevera_0".

Hicimos lo mismo para la segunda cámara, creando el alias /dev/cam_nevera_1.
El Resultado Final:

Ahora, en tu docker-compose.yml, en lugar de usar las rutas largas y problemáticas, usamos nuestros nuevos alias, que son limpios y no tienen dos puntos:
yaml
devices:
  - "/dev/ttyUSB0:/dev/ttyUSB0"
  - "/dev/cam_nevera_0:/dev/video0" # <- Alias limpio y estable
  - "/dev/cam_nevera_1:/dev/video1" # <- Alias limpio y estable
Docker Compose ahora entiende perfectamente estas rutas, y las reglas udev se encargan de que /dev/cam_nevera_0 siempre apunte a la cámara correcta, sin importar si reinicias el equipo o desconectas y vuelves a conectar las cámaras.
En resumen: Creamos alias personalizados y estables en el sistema operativo para evitar los caracteres que confundían a Docker Compose, logrando una configuración robusta y funcional. ¡Fue un gran trabajo en equipo!







-------------------------------------------------------------------------------------------------------


Guía Definitiva: Configuración de Múltiples Cámaras USB Idénticas en Linux con Nombres Personalizados
Este documento detalla el proceso validado para instalar dos o más cámaras USB idénticas en un sistema Linux (como Linux Mint), asignándoles nombres de dispositivo permanentes y personalizados para un uso fiable en cualquier aplicación, incluyendo Docker.

Paso 1: Verificación Inicial del Hardware
El primer paso es confirmar que el sistema operativo reconoce correctamente las cámaras a nivel de hardware y del subsistema de video.

Instalar Herramientas de Video: Abre una terminal e instala el paquete v4l-utils, que contiene herramientas esenciales para interactuar con dispositivos de video.

Bash

sudo apt update
sudo apt install v4l-utils
Listar Dispositivos de Video: Con ambas cámaras conectadas, ejecuta el siguiente comando para listar todos los dispositivos de video que el sistema detecta.   

Bash

v4l2-ctl --list-devices
La salida confirmará que ambas cámaras son reconocidas y mostrará los nodos de dispositivo que se les asignan temporalmente (ej. /dev/video0, /dev/video2, etc.). Es normal que cada cámara física cree dos nodos de video (index0 para captura y index1 para metadatos).   

Paso 2: Configuración de Permisos de Usuario
Para que las aplicaciones puedan acceder a las cámaras sin privilegios de administrador, el usuario debe pertenecer al grupo video.

Añadir Usuario al Grupo video: Ejecuta el siguiente comando para añadir tu usuario actual al grupo video. La opción -aG es crucial para añadir al grupo sin eliminar al usuario de otros grupos.   

Bash

sudo usermod -aG video $USER
Aplicar los Cambios: Para que la nueva membresía de grupo tenga efecto, debes cerrar la sesión por completo y volver a iniciarla. Este paso es obligatorio.

Paso 3: Identificar la Ruta Física Única de cada Cámara
El núcleo del problema con cámaras idénticas es que sus nombres (/dev/videoX) pueden cambiar en cada reinicio. La solución es identificarlas por el puerto USB físico al que están conectadas, que es un identificador estable.

Conecta una cámara a la vez: Para evitar confusiones, conecta solo una cámara en el puerto deseado.

Obtén la información del dispositivo: Usa udevadm para inspeccionar los atributos del dispositivo. Asume que la cámara conectada es /dev/video0 (ajústalo si es necesario según la salida de v4l2-ctl --list-devices).

Bash

udevadm info -a -n /dev/video0
Encuentra el devpath: En la larga salida del comando, busca en los bloques de "parent device" una línea que diga ATTRS{devpath}. Este será un número corto que identifica la ruta en el bus USB (por ejemplo, 1 o 4). Anota este número.

Repite para la otra cámara: Desconecta la primera cámara, conecta la segunda en su puerto designado y repite los pasos 2 y 3 para encontrar su devpath único.

Paso 4: Crear una Regla udev para Nombres Personalizados y Permanentes
Con los devpath únicos identificados, creamos una regla udev para que el sistema genere automáticamente enlaces simbólicos cortos y significativos cada vez que las cámaras se conecten.

Crear el Archivo de Reglas: Abre un editor de texto con privilegios de administrador para crear un nuevo archivo de reglas. El número 99 asegura que se ejecute después de las reglas del sistema.   

Bash

sudo nano /etc/udev/rules.d/99-webcams.rules
Escribir la Regla: Pega el siguiente contenido en el editor, sustituyendo 1 y 4 con los valores de devpath que encontraste en el paso anterior y cam_nevera_0/cam_nevera_1 con los nombres que desees.

Fragmento de código

# Cámara asignada al nombre 'cam_nevera_0' (identificada por el puerto físico con devpath "4")
SUBSYSTEM=="video4linux", ATTRS{devpath}=="4", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_0", GROUP="video", MODE="0666"

# Cámara asignada al nombre 'cam_nevera_1' (identificada por el puerto físico con devpath "1")
SUBSYSTEM=="video4linux", ATTRS{devpath}=="1", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_1", GROUP="video", MODE="0666"
ATTRS{devpath}: Identifica el puerto físico de forma fiable.   

ATTR{index}=="0": Filtra para aplicar la regla solo al dispositivo de captura de video real, ignorando el de metadatos.   

SYMLINK+="cam_nevera_0": La acción principal. Crea el enlace simbólico deseado en el directorio /dev/.   

Guardar y Cerrar: En nano, presiona Ctrl + X, luego Y para guardar, y finalmente Enter.

Aplicar las Nuevas Reglas: Recarga las reglas de udev y activa los cambios sin necesidad de reiniciar.

Bash

sudo udevadm control --reload-rules
sudo udevadm trigger
Paso 5: Verificación Final y Uso
Comprueba que tus nombres personalizados se hayan creado correctamente.

Verificar los Enlaces: Con ambas cámaras conectadas, lista tus nuevos dispositivos:

Bash

ls -l /dev/cam*
La salida debería mostrar tus nuevos nombres apuntando a los dispositivos /dev/videoX correspondientes.

Uso en Aplicaciones: ¡Listo! Ahora puedes usar /dev/cam_nevera_0 y /dev/cam_nevera_1 en todas tus aplicaciones (OBS, scripts, Docker Compose, etc.). Estos nombres son permanentes, predecibles y significativos, resolviendo completamente el problema de la asignación aleatoria.


comando
udevadm info -a -n /dev/video0



jumaar@le-id500:~$ v4l2-ctl --list-devices
USB 2.0 Camera: USB Camera (usb-0000:00:14.0-1):
	/dev/video0
	/dev/video1
	/dev/media0

USB 2.0 Camera: USB Camera (usb-0000:00:14.0-4):
	/dev/video2
	/dev/video3
	/dev/media1

jumaar@le-id500:~$ ls -l /dev/cam*
lrwxrwxrwx 1 root root 6 oct  2  2025 /dev/cam_nevera_0 -> video0
lrwxrwxrwx 1 root root 6 oct  2  2025 /dev/cam_nevera_1 -> video2
jumaar@le-id500:~$ ls -l /dev/v4l/by-path/.
total 0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:1:1.0-video-index0 -> ../../video0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:1:1.0-video-index1 -> ../../video1
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:4:1.0-video-index0 -> ../../video2
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:4:1.0-video-index1 -> ../../video3
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:1:1.0-video-index0 -> ../../video0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:1:1.0-video-index1 -> ../../video1
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:4:1.0-video-index0 -> ../../video2
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:4:1.0-video-index1 -> ../../video3
jumaar@le-id500:~$ sudo nano /etc/udev/rules.d/99-webcams.rules
[sudo] contraseña para jumaar:           
jumaar@le-id500:~$ cat /etc/udev/rules.d/99-webcams.rules
# Cámara 1 (puerto físico...-1, que actualmente es video2)
SUBSYSTEM=="video4linux", ATTRS{devpath}=="4", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_1", GROUP="video", MODE="0666"

# Cámara 2 (puerto físico...-4, que actualmente es video0)
SUBSYSTEM=="video4linux", ATTRS{devpath}=="1", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_0", GROUP="video", MODE="0666"




# Guía Maestra: Configuración de Túnel SSH Cliente-Servidor con Cloudflare

Esta guía detalla el proceso completo para conectar de forma segura un servidor Linux (Debian) a internet, ocultando su IP y sin necesidad de abrir puertos, utilizando el servicio **Cloudflare Tunnel**.

---

## Fase 1: Preparación del Servidor Debian

El objetivo es tener un servidor base seguro y listo para la red.

### 1.1. Crear un Usuario Administrador (No-Root)
Para mejorar la seguridad, se crea un usuario personal con privilegios de administrador, evitando el uso directo de `root` en las operaciones diarias.

```bash
# Crear el usuario (ej. 'nevera1')
sudo adduser nevera1

# Otorgarle permisos de administrador (añadirlo al grupo sudo)
sudo usermod -aG sudo nevera1
```

### 1.2. Asegurar el Servicio SSH
Se configura el servicio SSH para máxima seguridad, permitiendo el acceso solo al nuevo usuario administrador.

1.  Edita el archivo de configuración de SSH:
    ```bash
    sudo nano /etc/ssh/sshd_config
    ```

2.  Asegúrate de que las siguientes líneas estén configuradas así. Si no existen, añádelas:
    ```ini
    # Deshabilita el inicio de sesión para el usuario root. ¡Muy importante!
    PermitRootLogin no
    
    # Permite la autenticación por contraseña (puedes cambiarlo a 'no' si usas llaves SSH).
    PasswordAuthentication yes
    
    # Especifica qué usuarios tienen permitido conectarse por SSH.
    AllowUsers nevera1
    ```

3.  Aplica los cambios reiniciando el servicio SSH:
    ```bash
    sudo systemctl restart sshd
    ```

---

## Fase 2: Configuración de la Cuenta de Cloudflare

El objetivo es delegar la gestión de nuestro dominio a Cloudflare para que pueda actuar como intermediario seguro.

### 2.1. Registrarse y Añadir un Dominio
1.  Crea una cuenta gratuita en **Cloudflare.com**.
2.  Compra un nombre de dominio en cualquier registrador (ej. `lenstextil.com`).
3.  Desde el panel principal de Cloudflare, añade tu dominio a la cuenta.

### 2.2. Cambiar los Servidores de Nombres (Nameservers)
1.  Cloudflare te proporcionará dos o más direcciones de servidores de nombres (Nameservers).
2.  En el panel de administración de tu registrador de dominio, reemplaza los nameservers existentes por los que te dio Cloudflare.
    > **Nota:** Este cambio puede tardar desde unos minutos hasta varias horas en propagarse por internet.

---

## Fase 3: Creación del Túnel en el Servidor Debian

El objetivo es instalar el agente de Cloudflare (`cloudflared`), crear el túnel y configurarlo para que se ejecute como un servicio permanente.

### 3.1. Instalar el Agente `cloudflared`
Se añade el repositorio oficial de Cloudflare y se instala el software.

```bash
# Instalar pre-requisitos
sudo apt update
sudo apt install curl

# Añadir la clave GPG del repositorio de Cloudflare
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Añadir el repositorio de Cloudflare a las fuentes de apt
# (usar 'bookworm' es compatible con Debian 12 y versiones recientes de Ubuntu)
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared bookworm main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# Actualizar la lista de paquetes e instalar cloudflared
sudo apt update
sudo apt install cloudflared
```

### 3.2. Autenticar el Agente
Conecta el agente `cloudflared` a tu cuenta de Cloudflare.

1.  Ejecuta el siguiente comando:
    ```bash
    cloudflared tunnel login
    ```
2.  Copia la URL que aparece en la terminal.
3.  Pega la URL en un navegador, inicia sesión en Cloudflare y autoriza el dominio que configuraste.

### 3.3. Crear y Configurar el Túnel
Se crea una entrada para el túnel y se define su archivo de configuración.

1.  Crea el túnel. Dale un nombre descriptivo (ej. `nevera1-tunnel`).
    ```bash
    cloudflared tunnel create nevera1-tunnel
    ```
    > **¡Importante!** Anota el **UUID** del túnel que se mostrará en la salida.

2.  Crea y edita el archivo de configuración del túnel.
    ```bash
    sudo nano /etc/cloudflared/config.yml
    ```

3.  Añade el siguiente contenido, **reemplazando `<UUID-DEL-TÚNEL>` y el `hostname`** con tus propios valores.
    ```yaml
    # UUID del túnel que creaste en el paso anterior.
    tunnel: <UUID-DEL-TÚNEL>
    # Ruta al archivo de credenciales que se generó.
    credentials-file: /etc/cloudflared/<UUID-DEL-TÚNEL>.json
    
    # Reglas de enrutamiento (Ingress Rules).
    ingress:
      # Enruta el tráfico del subdominio al servicio SSH local (puerto 22).
      - hostname: ssh-nevera1.lenstextil.com
        service: ssh://localhost:22
      # Regla final: si no coincide ninguna regla anterior, devuelve un error 404.
      - service: http_status:404
    ```

4.  Mueve el archivo de credenciales (generado durante la autenticación) a su ubicación permanente.
    ```bash
    # Reemplaza <UUID-DEL-TÚNEL> y, si es necesario, el nombre de tu usuario ('nevera1').
    sudo mv /home/nevera1/.cloudflared/<UUID-DEL-TÚNEL>.json /etc/cloudflared/
    ```

### 3.4. Crear la Ruta DNS Pública
Registra el `hostname` en el DNS de Cloudflare para que apunte al túnel.

```bash
cloudflared tunnel route dns nevera1-tunnel ssh-nevera1.lenstextil.com
```

### 3.5. Activar y Verificar el Servicio
Configura el túnel para que se inicie automáticamente con el servidor y comprueba su estado.

```bash
# Instalar cloudflared como un servicio del sistema
sudo cloudflared service install

# Iniciar el servicio
sudo systemctl start cloudflared

# Habilitar el servicio para que se inicie en cada arranque
sudo systemctl enable cloudflared

# Verificar que el servicio está corriendo correctamente
sudo systemctl status cloudflared
```
Deberías ver un estado `active (running)`.

---

## Fase 4: Configuración del Cliente (PC con Windows)

El objetivo es configurar el cliente SSH de Windows para que sepa cómo usar el túnel de Cloudflare para conectarse.

### 4.1. Preparar el Agente `cloudflared.exe`
1.  Crea una carpeta para las herramientas de Cloudflare.
    ```powershell
    mkdir C:\Cloudflare\bin
    ```
2.  Descarga la versión de 64-bit de `cloudflared` para Windows desde la página oficial de Cloudflare.
3.  Mueve el archivo descargado a `C:\Cloudflare\bin` y renómbralo a `cloudflared.exe`.

### 4.2. Configurar el Cliente SSH
1.  Crea o edita el archivo de configuración de SSH de tu usuario. Puedes usar `notepad` o cualquier editor de texto.
    > **Nota:** Si la carpeta `.ssh` o el archivo `config` no existen en tu perfil de usuario (`%USERPROFILE%`), créalos.
    ```powershell
    notepad %USERPROFILE%\.ssh\config
    ```

2.  Añade el siguiente bloque. Asegúrate de que la ruta a `cloudflared.exe` y el `HostName` sean correctos.
    ```properties
    Host ssh-nevera1.lenstextil.com
        HostName ssh-nevera1.lenstextil.com
        User nevera1
        ProxyCommand C:\Cloudflare\bin\cloudflared.exe access ssh --hostname %h
    ```
3.  Guarda y cierra el archivo.

### 4.3. La Conexión Final
¡Listo! Ahora la conexión remota y segura se realiza con un único y simple comando desde PowerShell o CMD.
 
Gracias a la línea `User nevera1` que añadimos en la configuración, no es necesario escribir el usuario cada vez. El cliente SSH lo hará por ti, por eso el comando se simplifica a:

```bash
ssh ssh-nevera1.lenstextil.com
```

Como bien apuntas, el comando que incluye el usuario también es **100% correcto y válido**:

```bash
ssh nevera1@ssh-nevera1.lenstextil.com
```

Ambos comandos logran el mismo resultado y utilizan automáticamente el túnel de Cloudflare (`ProxyCommand`) para establecer una conexión segura sin exponer tu servidor directamente a internet.


### ¿Qué Viene Después? ###
El siguiente paso en un proyecto real, sera la escalabilidad y la gestión a nivel de flota:

Automatización: Ahora que sabes configurar una nevera, ¿cómo configurarías 100 sin volverte loco? Ahí entran herramientas como Ansible.

Monitorización: ¿Cómo sabes si una nevera se desconectó? Ahí entran los sistemas de monitoreo y alertas.

Seguridad de Acceso (Zero Trust): ¿Cómo le das acceso a otros técnicos de forma segura? Ahí entran herramientas como Cloudflare Access, que añaden una capa de autenticación (como iniciar sesión con Google) incluso antes de poder intentar la conexión SSH.