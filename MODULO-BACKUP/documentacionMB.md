# Módulo de Backup (MODULO-BACKUP)

## Resumen

Este módulo es un componente de seguridad crítico diseñado para proteger los datos más importantes generados por el servicio `nevera`. Su función principal es crear copias de seguridad periódicas de la información que no se puede recuperar en caso de un fallo o pérdida de datos.

### ¿Qué datos se respaldan?

El servicio de backup se enfoca en dos volúmenes de datos vitales:

1.  **`nevera_offline_queue`**: Contiene todas las transacciones de venta que no pudieron ser enviadas al servidor backend debido a problemas de conexión. Respaldar esta cola es crucial para **evitar la pérdida de ventas**.
2.  **`nevera_review_queue`**: Almacena las imágenes de las sesiones de compra que el sistema marcó como de "baja confianza". Estos datos son esenciales para la **auditoría manual** y para mejorar la precisión del sistema.

### ¿Cómo funciona?

- El servicio ejecuta un script (`backup.sh`) de forma periódica.
- El script comprime el contenido de los dos volúmenes mencionados en archivos `.tar.gz` separados y con marca de tiempo.
- Las copias de seguridad se guardan **localmente** en el volumen `backup_data`.
- El script también gestiona la rotación de backups, eliminando automáticamente las copias de más de 7 días para evitar que el disco se llene.

---













## TAREAS  --> V 0.1

NOTA: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- Tarea fija: En que version de este modulo estamos para git?  -> 0.1

- Configurar el sh para que envie la copia de seguridad a un lugar remoto
