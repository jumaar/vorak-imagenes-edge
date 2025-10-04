# Usamos una imagen base ligera de Alpine Linux
FROM alpine:latest

# Instalamos rsync (para sincronización eficiente) y cron (para programar tareas)
# openrc es una dependencia de cron en Alpine
RUN apk add --no-cache rsync openrc cron

# Creamos los directorios que el script de backup usará dentro del contenedor
RUN mkdir -p /backups/source /backups/destination /etc/periodic/hourly

# Copiamos el script de backup desde nuestro directorio local al contenedor.
# Lo ponemos en /etc/periodic/hourly para que cron lo ejecute automáticamente cada hora.
COPY backup.sh /etc/periodic/hourly/backup
RUN chmod +x /etc/periodic/hourly/backup

# El comando que se ejecuta cuando el contenedor arranca.
# Inicia el demonio de cron en primer plano para mantener el contenedor vivo y ejecutando las tareas.
CMD ["crond", "-f", "-d", "8"]