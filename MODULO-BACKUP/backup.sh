#!/bin/sh

# --- Configuración ---
SOURCE_DIR="/backups/source"
DEST_DIR="/backups/destination"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$DEST_DIR/backup_log.txt"

# --- Rotación de Logs ---
# Mantenemos el log con un tamaño máximo de 1MB
if [ -f "$LOG_FILE" ]; then
    log_size=$(stat -c%s "$LOG_FILE")
    if [ "$log_size" -gt 1048576 ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
    fi
fi

# Asegurarse de que el directorio de destino exista
mkdir -p $DEST_DIR

echo "--- Iniciando backup: $TIMESTAMP ---" >> $LOG_FILE

# --- Backup de la cola OFFLINE (Crítico) ---
# Comprimimos todo el contenido del volumen en un archivo tar.gz con fecha.
# El '.' al final es importante, significa "el directorio actual" dentro de -C.
tar -czf $DEST_DIR/offline_queue_backup_$TIMESTAMP.tar.gz -C $SOURCE_DIR/offline_queue .
if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] Backup de 'offline_queue' completado." >> $LOG_FILE
else
    echo "[$TIMESTAMP] ERROR: Falló el backup de 'offline_queue'." >> $LOG_FILE
fi

# --- Backup de la cola de REVISIÓN (Crítico) ---
tar -czf $DEST_DIR/review_queue_backup_$TIMESTAMP.tar.gz -C $SOURCE_DIR/review_queue .
if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] Backup de 'review_queue' completado." >> $LOG_FILE
else
    echo "[$TIMESTAMP] ERROR: Falló el backup de 'review_queue'." >> $LOG_FILE
fi

# --- Limpieza de backups antiguos ---
# Mantenemos los últimos 7 días de backups para no llenar el disco.
find $DEST_DIR -name "offline_queue_backup_*.tar.gz" -mtime +7 -exec rm {} \;
find $DEST_DIR -name "review_queue_backup_*.tar.gz" -mtime +7 -exec rm {} \;
echo "[$TIMESTAMP] Limpieza de backups antiguos completada." >> $LOG_FILE

echo "--- Backup finalizado: $TIMESTAMP ---" >> $LOG_FILE