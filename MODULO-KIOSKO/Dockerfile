# Dockerfile para el servicio kiosko-webapp (solo el servidor Flask)
FROM python:3.11-alpine

# --- ¡NUEVO! Instalar el cliente de Docker ---
# Esto es necesario para que el script de redespliegue pueda ejecutar comandos 'docker'.
RUN apk add --no-cache docker-cli

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requisitos e instalar las dependencias
COPY MODULO-KIOSKO/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# --- ¡NUEVO! Copiar el script de redespliegue y darle permisos de ejecución ---
# Copiar el código de la aplicación y los directorios de plantillas/estáticos
# Copiar todo el código de la aplicación del módulo kiosko al directorio de trabajo
COPY MODULO-KIOSKO/ .

# Exponer el puerto en el que Gunicorn escuchará
EXPOSE 5000 9091

# Comando para iniciar Gunicorn
# Gunicorn buscará la aplicación 'app' dentro del módulo 'kiosk.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "kiosk:app"]