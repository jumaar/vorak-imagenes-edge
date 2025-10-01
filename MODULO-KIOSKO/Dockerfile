# ==============================================================================
# Dockerfile para el Módulo Kiosko con Interfaz Gráfica (Chromium)
# ==============================================================================

# Usamos una imagen base de Debian completa para tener las dependencias gráficas.
FROM debian:trixie

LABEL maintainer="jumaar"
LABEL description="Imagen de producción para el Módulo Kiosko con Chromium."

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # --- CONFIGURACIÓN DE IDIOMA PARA TODO EL SISTEMA ---
    LANG=es_CO.UTF-8 \
    LANGUAGE=es_CO:es \
    DISPLAY=:0

# Instalar dependencias del sistema:
# - python3 y venv: Para nuestra aplicación.
# - openbox: Gestor de ventanas ligero.
# - xorg, xinit: Servidor gráfico básico.
# - chromium: El navegador que usaremos en modo kiosko.
# - build-essential: Para instalar algunas librerías de python si es necesario.
# - locales: Herramienta para generar los idiomas del sistema.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    openbox \
    xorg \
    xinit \
    chromium \
    sudo \
    locales \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Generar y configurar el locale 'es_CO.UTF-8'
RUN sed -i -e 's/# es_CO.UTF-8 UTF-8/es_CO.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales


# Deshabilitar completamente el servicio D-Bus para evitar que se inicie.
# Esto es más efectivo que intentar deshabilitarlo en tiempo de ejecución.
# En lugar de 'systemctl mask', que no funciona bien en el build de Docker,
# creamos el enlace simbólico manualmente.
RUN ln -sf /dev/null /etc/systemd/system/dbus.service

# --- CREACIÓN DE USUARIO NO-ROOT ---
# ARG permite pasar variables durante la construcción de la imagen.
# Crearemos un usuario 'kiosk' con el mismo UID/GID que el usuario del host.
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID kiosk && \
    useradd -u $UID -g $GID -m -s /bin/bash kiosk && \
    usermod -aG sudo kiosk && \
    # Permitir al usuario 'kiosk' ejecutar sudo sin contraseña.
    # Esto es crucial para que el entrypoint.sh pueda corregir los permisos del volumen.
    echo "kiosk ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/kiosk-nopasswd

# Establecer el directorio de trabajo principal de la aplicación
WORKDIR /app

# Copiar archivos y establecer permisos como root
COPY --chown=kiosk:kiosk MODULO-KIOSKO/.xsession /home/kiosk/.xsession
COPY --chown=kiosk:kiosk MODULO-KIOSKO/requirements.txt .
COPY --chown=kiosk:kiosk MODULO-KIOSKO/. .
RUN chmod +x /home/kiosk/.xsession && \
    chmod +x /app/entrypoint.sh && \
    mkdir -p /app/data && \
    chown -R kiosk:kiosk /app/data

# Cambiar al usuario kiosk para crear el venv e instalar las dependencias de Python
USER kiosk
RUN python3 -m venv /home/kiosk/venv
# Activar el entorno virtual para los siguientes comandos
ENV PATH="/home/kiosk/venv/bin:$PATH"
RUN /home/kiosk/venv/bin/pip install --upgrade pip && \
    /home/kiosk/venv/bin/pip install -r requirements.txt

# Corregir la ruta para que apunte al venv del usuario 'kiosk'
ENV PATH="/home/kiosk/venv/bin:$PATH"

# El entrypoint se encargará de iniciar todo.
# Se ejecutará como root, pero lanzará los procesos como el usuario 'kiosk'.
ENTRYPOINT ["/app/entrypoint.sh"]