# ==============================================================================
# Dockerfile para la Herramienta de Test de Cámaras
# ==============================================================================

# Usamos una imagen base de Debian completa para tener las dependencias gráficas.
FROM debian:trixie

LABEL maintainer="jumaar"
LABEL description="Imagen para la herramienta de test de cámaras."

# Instalar dependencias del sistema:
# - python3 y pip: Para nuestra aplicación.
# - python3-opencv: La forma más fácil de tener OpenCV y sus dependencias gráficas.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Crear un usuario no-root para ejecutar la aplicación
RUN useradd --create-home --shell /bin/bash tester && \
    usermod -aG video tester

WORKDIR /app

# Copiar solo el script de test
COPY camara.py .

# Asignar permisos
RUN chown -R tester:tester /app

# Cambiar al usuario no-root
USER tester

# El comando que se ejecutará al iniciar el contenedor
CMD ["python3", "camara.py"]