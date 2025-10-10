# Usamos una imagen que SOLO contiene el cliente de Docker, no el motor.
# Esto es más ligero y seguro para nuestro caso de uso.
FROM docker:25-cli

# El resto del archivo no cambia.
RUN apk update && apk add --no-cache git

WORKDIR /app

CMD ["./deploy.sh"]