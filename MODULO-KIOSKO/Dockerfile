# ==============================================================================
# --- ETAPA 1: BUILDER ---
# Esta etapa crea un entorno virtual aislado con todas las dependencias de Python.
# El resultado es una carpeta /opt/venv que se copiará a la etapa final.
# ==============================================================================
FROM python:3.11-alpine AS builder

# Establecemos el directorio de trabajo
WORKDIR /app

# Creamos el entorno virtual dentro del directorio de trabajo
RUN python -m venv /opt/venv

# Activamos el entorno virtual para los comandos siguientes
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos solo el archivo de requisitos para aprovechar la caché de Docker
COPY ./MODULO-KIOSKO/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# --- ETAPA 2: FINAL ---
# Esta es la imagen final, optimizada para ser ligera y segura.
# No contiene herramientas de compilación, solo lo necesario para ejecutar la aplicación.
# ==============================================================================
FROM python:3.11-alpine

WORKDIR /app/MODULO-KIOSKO

# --- ¡MEJORA! ---
# Instalamos tanto 'docker' (el cliente) como 'docker-compose' (el plugin, necesario para run_deployer.sh).
# Usamos --no-cache para no guardar el índice de paquetes y limpiamos la caché al final.
RUN apk update && \
    apk add --no-cache docker docker-compose && \
    rm -rf /var/cache/apk/*

# Copiamos el entorno virtual con las dependencias ya instaladas desde la etapa 'builder'.
COPY --from=builder /opt/venv /opt/venv

# Copiamos el código de la aplicación y damos permisos de ejecución al script de despliegue en una sola capa.
COPY ./MODULO-KIOSKO/ .
RUN chmod +x ./run_deployer.sh

# Activamos el entorno virtual para los comandos siguientes
ENV PATH="/opt/venv/bin:$PATH"

# Creamos un enlace simbólico para que 'python3' apunte a 'python' dentro del entorno virtual.
RUN ln -sf /opt/venv/bin/python /opt/venv/bin/python3
 
# Exponer el puerto en el que Gunicorn escuchará
EXPOSE 5000 9091

# Comando para iniciar Gunicorn
# Gunicorn buscará la aplicación 'app' dentro del módulo 'kiosk.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "kiosk:app"]