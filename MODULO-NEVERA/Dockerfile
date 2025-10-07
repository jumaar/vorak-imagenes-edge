# Usamos una imagen base de Python delgada
FROM python:3.11-slim

# Instalar dependencias del sistema operativo necesarias para OpenCV y otras librerías
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar el archivo de requerimientos e instalar las dependencias de Python
# Hacemos esto ANTES de copiar el resto del código para aprovechar la caché de Docker.
COPY MODULO-NEVERA/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY MODULO-NEVERA/app.py .
COPY MODULO-NEVERA/products.json .
COPY MODULO-NEVERA/test_cameras.py .

# Crear un usuario no-root y asegurar permisos en los directorios de volúmenes
RUN adduser --system --no-create-home appuser && \
    mkdir -p /app/logs /app/db /app/status && \
    chown -R appuser:nogroup /app/logs /app/db /app/status
USER appuser

# Comando para ejecutar la aplicación cuando el contenedor inicie
CMD ["python", "app.py"]