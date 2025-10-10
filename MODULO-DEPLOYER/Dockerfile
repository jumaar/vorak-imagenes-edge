# --- ¡SOLUCIÓN! ---
# Usamos la imagen oficial 'docker/compose' que incluye tanto el cliente de Docker
# como el plugin 'compose'. Esto resuelve el error "command not found" (exit 127).
FROM docker/compose:latest

# Instalar git, que es necesario para que deploy.sh pueda hacer 'git pull'.
# La imagen docker/compose está basada en Alpine, por lo que usamos 'apk'.
RUN apk add --no-cache git

# Establecer el directorio de trabajo por defecto.
WORKDIR /app

# Copiamos el script de despliegue a la imagen.
COPY ./deploy.sh .
# Nos aseguramos de que tenga permisos de ejecución.
RUN chmod +x ./deploy.sh

# Comando por defecto que se ejecutará al iniciar el contenedor.
CMD ["./deploy.sh"]
