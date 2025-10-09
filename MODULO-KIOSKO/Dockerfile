# ==============================================================================
# --- ETAPA 1: BUILDER ---
# Esta etapa crea un entorno virtual con todas las dependencias de Python.
# ==============================================================================
FROM python:3.11-alpine AS builder

# Creamos un directorio para el entorno virtual
RUN python -m venv /opt/venv

# Hacemos que los comandos 'pip' y 'python' usen el entorno virtual
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos solo el archivo de requisitos e instalamos las dependencias DENTRO del venv
COPY MODULO-KIOSKO/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# --- ETAPA 2: FINAL ---
# Esta es la imagen final, súper ligera. Solo copia el entorno virtual
# y el código de la aplicación. No contiene herramientas de build.
# ==============================================================================
FROM python:3.11-alpine

WORKDIR /app

# Esto es necesario porque kiosk.py ahora usa 'subprocess' para llamar a 'docker compose'.
RUN apk add --no-cache docker-cli docker-compose-v2
# Nota: 'docker-compose-v2' instala el plugin 'compose' para el comando 'docker compose ...'
#
# Limpiar la caché de apk para mantener la imagen ligera.
RUN rm -rf /var/cache/apk/*


# Copiamos el entorno virtual con las dependencias ya instaladas desde la etapa 'builder'
COPY --from=builder /opt/venv /opt/venv

# Copiamos el código de la aplicación.
# Nota: Esto es opcional si siempre usas un volumen, pero es buena práctica tenerlo.
COPY MODULO-KIOSKO/ .

# Activamos el entorno virtual para los comandos siguientes
ENV PATH="/opt/venv/bin:$PATH"

# Exponer el puerto en el que Gunicorn escuchará
EXPOSE 5000 9091

# Comando para iniciar Gunicorn
# Gunicorn buscará la aplicación 'app' dentro del módulo 'kiosk.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "kiosk:app"]