# --- ETAPA 1: FUENTE ---
# Usamos la imagen oficial solo para poder copiar su contenido.
FROM grafana/promtail:2.9.2 AS source

# --- ETAPA 2: IMAGEN FINAL ---
# Construimos nuestra imagen final sobre Debian Slim (necesario para glibc).
FROM debian:bookworm-slim

# Instalamos 'gettext-base' (que provee envsubst) y 'ca-certificates' (necesario para conexiones HTTPS).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gettext-base \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copiamos el binario de Promtail desde la etapa 'source'.
# El binario en la imagen oficial está en /usr/bin/promtail
COPY --from=source /usr/bin/promtail /usr/bin/promtail

# Copiamos nuestro script de entrypoint personalizado y le damos permisos.
COPY entrypoint-promtail.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint-promtail.sh

# Establecemos nuestro script como el punto de entrada.
ENTRYPOINT ["/usr/local/bin/entrypoint-promtail.sh"]