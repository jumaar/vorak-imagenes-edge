# --- ¡SOLUCIÓN! ---
# Usamos la imagen oficial 'docker/compose' que incluye tanto el cliente de Docker
# como el plugin 'compose'. Esto resuelve el error "command not found" (exit 127).
FROM docker/compose:latest

# Instalar git, que es necesario para que deploy.sh pueda hacer 'git pull'.
# La imagen docker/compose está basada en Alpine, por lo que usamos 'apk'.
RUN apk add --no-cache git

# Establecer el directorio de trabajo por defecto.
WORKDIR /app

# Comando por defecto que se ejecutará al iniciar el contenedor.
# Este script será el que está montado desde el host a través del volumen '.:/app'.
# El propio script 'deploy.sh' se encarga de gestionar los permisos de otros scripts.
CMD ["./deploy.sh"]
