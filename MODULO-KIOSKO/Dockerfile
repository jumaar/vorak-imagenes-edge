
FROM python:3.10-slim as builder

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos e instalar las dependencias
# Esto aprovecha el cache de capas de Docker: solo se reinstalará si requirements.txt cambia.
COPY MODULO-KIOSKO/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Fase 2: Final ---
# Usamos una imagen "slim" que es más ligera para la ejecución final.
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Crear un usuario no-root para mejorar la seguridad
RUN useradd --create-home appuser && \
    mkdir -p /app/status && \
    chown -R appuser:appuser /app
USER appuser

# Copiar las dependencias instaladas desde la fase de 'builder'
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=appuser:appuser MODULO-KIOSKO/ .

# Exponer el puerto que usará Gunicorn
EXPOSE 5000

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "kiosk:app"]
