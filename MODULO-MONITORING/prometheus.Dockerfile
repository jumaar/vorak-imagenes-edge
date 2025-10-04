# --- ETAPA 1: FUENTE ---
# Usamos la imagen oficial solo para poder copiar su contenido.
FROM prom/prometheus:v2.47.2 AS source

# --- ETAPA 2: IMAGEN FINAL ---
# Construimos nuestra imagen final sobre Alpine, que sí tiene un gestor de paquetes.
FROM alpine:latest

# Instalamos 'gettext' (que provee envsubst) y 'ca-certificates' (necesario para conexiones HTTPS).
RUN apk add --no-cache gettext ca-certificates

# Copiamos los binarios y archivos de la UI de Prometheus desde la etapa 'source'.
COPY --from=source /bin/prometheus /bin/prometheus
COPY --from=source /usr/share/prometheus/console_libraries /usr/share/prometheus/console_libraries
COPY --from=source /usr/share/prometheus/consoles /usr/share/prometheus/consoles

# Copiamos nuestro script de entrypoint personalizado y le damos permisos.
COPY entrypoint-prometheus.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint-prometheus.sh

# Establecemos nuestro script como el punto de entrada.
ENTRYPOINT ["/usr/local/bin/entrypoint-prometheus.sh"]