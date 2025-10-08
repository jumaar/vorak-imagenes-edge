# Dockerfile para el servicio kiosko-webapp (solo el servidor Flask)
FROM python:3.11-alpine

# --- ¡NUEVO! Instalar el cliente de Docker ---
# Esto es necesario para que el script de redespliegue pueda ejecutar comandos 'docker', 'git' y 'docker compose'.
# --- ¡SOLUCIÓN! Añadimos 'docker-compose' para instalar el plugin 'compose' v2. ---
RUN apk add --no-cache git docker-cli docker-compose

# --- ¡SOLUCIÓN! Marcar el directorio del proyecto como seguro para Git ---
# Esto evita el error "dubious ownership" cuando el contenedor (como root) opera en un volumen montado desde el host (propiedad de otro usuario).
RUN git config --global --add safe.directory /project

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requisitos e instalar las dependencias
COPY MODULO-KIOSKO/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copiar el código de la aplicación del módulo kiosko
COPY MODULO-KIOSKO/ .


# Estos son necesarios para que el webhook de actualización pueda ejecutarlos.
COPY gitpull.sh .
COPY deploy.sh .

# Exponer el puerto en el que Gunicorn escuchará
EXPOSE 5000 9091

# Comando para iniciar Gunicorn
# Gunicorn buscará la aplicación 'app' dentro del módulo 'kiosk.py'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "kiosk:app"]