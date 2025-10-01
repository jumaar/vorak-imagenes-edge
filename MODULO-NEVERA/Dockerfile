# ==============================================================================
# Dockerfile para el Módulo Nevera
# ==============================================================================

# --- Fase 1: Build ---
# Usamos una imagen de Debian Trixie Slim como base, tal como se solicitó.
FROM python:3.11-slim-trixie as builder

LABEL maintainer="jumaar"
LABEL description="Entorno de construcción para el Módulo Nevera de Vorak."

# Variables de entorno para la construcción
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Instalar dependencias del sistema operativo necesarias para compilar librerías de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear y activar un entorno virtual
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar el archivo de requerimientos e instalar las dependencias de Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# --- Fase 2: Producción ---
# Usamos la misma imagen base de python para asegurar la compatibilidad del venv.
FROM python:3.11-slim-trixie

LABEL maintainer="jumaar"
LABEL description="Imagen de producción para el Módulo Nevera de Vorak."

# Instalar dependencias del sistema operativo para la ejecución
# - ffmpeg: Backend de video para OpenCV
# - libgl1: Dependencia de OpenCV para operaciones de GUI (aunque no se muestre video, es necesaria)
# - sudo: Para permitir la gestión de permisos si fuera necesario.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# --- CREACIÓN DE USUARIO NO-ROOT PARA MAYOR SEGURIDAD ---
RUN useradd --create-home --shell /bin/bash nevera && \
    usermod -aG video,dialout,tty,sudo nevera && \
    # Permitir al usuario 'nevera' ejecutar sudo sin contraseña.
    echo "nevera ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/nevera-nopasswd

# Copiar el entorno virtual y el código de la aplicación desde la fase de construcción
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY . .

# Copiar el script de entrada y darle permisos de ejecución
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Asignar la propiedad del directorio de la aplicación al nuevo usuario
RUN chown -R nevera:nevera /app /opt/venv

# Activar el entorno virtual para el entorno de ejecución
ENV PATH="/opt/venv/bin:$PATH"
ENTRYPOINT ["/app/entrypoint.sh"]