# Dockerfile para el servicio kiosko-webapp (solo el servidor Flask)
FROM python:3.11-alpine

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requisitos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación y los directorios de plantillas/estáticos
COPY kiosk.py .
COPY templates/ templates/
COPY static/ static/

# Exponer el puerto en el que Gunicorn escuchará
EXPOSE 5000

# Comando para iniciar Gunicorn
# Gunicorn buscará la aplicación 'app' dentro del módulo 'kiosk.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "kiosk:app"]