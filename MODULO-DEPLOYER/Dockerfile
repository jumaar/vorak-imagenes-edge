# Usamos la imagen oficial de Docker que incluye el CLI moderno y el plugin Compose v2
FROM docker:latest

# El procedimiento para instalar git sigue siendo el mismo
RUN apk update && apk add --no-cache git

WORKDIR /app

CMD ["./deploy.sh"]