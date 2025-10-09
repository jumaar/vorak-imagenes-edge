# Usamos la imagen oficial de Docker con la CLI como base.
FROM docker:cli

# Instalar git, que es necesario para que deploy.sh pueda hacer 'git pull'.
# 'apk add --no-cache' mantiene la imagen ligera.
RUN apk add --no-cache git

# Establecer el directorio de trabajo por defecto.
WORKDIR /app