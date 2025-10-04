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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- ¡CORRECCIÓN CLAVE DE PERMISOS! ---
# Añadimos el usuario root (que es el que corre la app por defecto en esta imagen)
# a los grupos 'video' y 'dialout'. Los GID (997 y 20) son estándar en Debian/Ubuntu.
RUN usermod -a -G video,dialout root

# Copiar el resto del código de la aplicación
COPY app.py .
COPY products.json .
COPY test_cameras.py .

# Comando para ejecutar la aplicación cuando el contenedor inicie
CMD ["python", "app.py"]