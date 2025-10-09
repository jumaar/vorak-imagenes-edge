# ==============================================================================
# --- ETAPA 1: BUILDER ---
# Esta etapa instala las dependencias de Python en un entorno virtual aislado.
# ==============================================================================
FROM python:3.11-slim AS builder

# Instalar dependencias del sistema operativo que puedan ser necesarias para
# COMPILAR las librerías de Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Creamos un directorio para el entorno virtual
RUN python -m venv /opt/venv

# Hacemos que los comandos 'pip' y 'python' usen el entorno virtual
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos solo el archivo de requisitos e instalamos las dependencias DENTRO del venv
COPY MODULO-NEVERA/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# --- ETAPA 2: FINAL ---
# Esta es la imagen final, optimizada para producción.
# ==============================================================================
FROM python:3.11-slim

# Instalar solo las dependencias de sistema operativo necesarias para EJECUTAR OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos el entorno virtual con las dependencias ya instaladas desde la etapa 'builder'
COPY --from=builder /opt/venv /opt/venv

# Copiamos el código de la aplicación
COPY MODULO-NEVERA/ .

# Crear un usuario no-root y asegurar permisos en los directorios de volúmenes
RUN adduser --system --no-create-home appuser && \
    mkdir -p /app/logs /app/db /app/status /app/offline_queue /app/review_queue && \
    chown -R appuser:nogroup /app
USER appuser

# Activamos el entorno virtual para los comandos siguientes
ENV PATH="/opt/venv/bin:$PATH"

# Comando para ejecutar la aplicación cuando el contenedor inicie
CMD ["python", "app.py"]