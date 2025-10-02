## Guia completa MODULO-NEVERA
- MODULO-SENSORES : este modulo es una configuracion hecha en esp32 (leer documentacion.md MODULO-SENSORES ), este nos envia un reporte cada 30 segundos con el estado de la nevera, y 2 tipos de eventos a.cuando abre  cierra la puerta b. cuando hay un cambio de peso.

- HARDWARE : se acondiciona un pc portatil de buena pantalla 15.5 " para el sistema de kiosco , minimo core i3 con 4gb de ram , se instala SO linux Debian 13, se procesa toda la informacion recibida de los sensores y de las camaras web con opturador global shutter monocromaticas de alta captura, pueden ser 2  mas camaras es solo modificar en app.py el CAMERA_INDICES = [0,1,2,3]

- ADMINISTRACION : Se utiliza un tunnel ssh desde un pc cliente. por medio de cloudflared se realiza la configuracion del sudominio de cada nueva nevera que se añada a red , clouflared se encarga de hacernos la conexion segura a cada dispositivo para la administracion, el archivo ``config-tunnel-client-ser.md`` es la guia completa para dejar la conexion lista con el servidor. siempre que recibamos una calificacion baja de captura de producto se debe ingresar a la nevera para a revision manual de las capturas tomadas de a secion fallida , cada  secion se guarda con un id unico. la nevera tiene un boton de tara , el cual lleva a cero la bascula (esta se debe tener vacia a momneto de la tara) 

- LOGICA : app.py es el cerebro que se encarga de procesar todos los eventos y enviar al backend las respuestas de cada evento , tenemos implementado un sistema de falla de comunicacion persistente, tenemos sistema de logs, tenemos sistema de captura de secion de identificacion de productos con dudosa evaluacion el cual guarda en el servidor las imagenes para una revision posterior por un humano o una ia para verificar cual fue el fallo en la captura y la decision de que producto fue el que salio o entro de la nevera,

- KIOSK: ``modulo-kiosk-edge`` tenemos un pantalla adactada que muestra en modo kiosko informacion de la nevera y publicidad este modulo se conecta con ``modulo-kiosk-admin``que es el encargado de poner de manera inteligente la publicidad ( si en una nevera hay mucho chorizo esta por vencer --> el sistema coloca en descuento el producto y pone la imagen de promocion de chorizo en la nevera )
documentacion ``documentacion-kiosk-admin.md``

- .env:  ``FRIDGE_ID="NEVERA-001-SANTAROSA"`` simpre modificar este id para cada nevera
``BASE_BACKEND_URL="https://9dfd069ea59e.ngrok-free.app"`` se coloca solo la url de la api , el resto ya lo manejca cada script.
``FRIDGE_SECRET="una-clave-secreta-muy-larga-y-unica"`` Clave secreta para la autenticación JWT.

-JWT: Integrado. El sistema ahora usa autenticación JWT para todas las peticiones al backend.
 
   




## TAREAS  --> V 0.3 

nota: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

- En que version de este modulo estamos para git?  -> 0.3

- crear un servidor para el manejo .env y que cada nevera se conecte a el para cargar las claves  y las variables de entorno y asi Eliminar la librería python-dotenv usamos swarm





## USO DIARIO. 

# Conéctate usando el subdominio único de la nevera.
``ssh nevera1@ssh-nevera1.lenstextil.com``

# Verificar el estado de tu aplicación. 
``sudo systemctl status nevera.service``

# parar el servicio de la app.py
``sudo systemctl stop nevera.service``

# VERFICAR los LOGS de tu aplicación. 
``El '-n 100' muestra las últimas 100 líneas, y '--no-pager' lo imprime directo.
``journalctl -u nevera.service -n 100 --no-pager``

este comando muestra los logs desde el ultimo reinicio
`journalctl -b -u nevera.service`

ver losg en tiempo real 
``journalctl -f -u nevera.service``

``# El '-n 20' muestra las últimas 20 líneas.
``tail -n 20 ~/MODULO-NEVERA/fridge_service.log``

# gestion de archivos en el servidor app
``cd ~/MODULO-NEVERA/``  modificar archivo de configuracion  ``nano app.py`` 
reiniciar despues ``sudo systemctl restart nevera.service``

# Entorno virtual para actualizar librerias

1. `` cd ~/MODULO-NEVERA/``  
2. Activa el entorno para "abrir la caja de herramientas".``source venv/bin/activate``

3. Instala la nueva herramienta. Notarás el prefijo (venv). 
(venv) nevera1@...:~$ pip install opencv-python requests pyserial python-dotenv Flask PyJWT

4. desactivar el entorno.
(venv) nevera1@...:~$ deactivate

5. reiniciar de nuevo 
 ``sudo systemctl restart nevera.service``

# copiar carpetas o archivos desde el servidor cambiar el --> nevera1@ssh-nevera1.lenstextil.com

Con este comando se pueden copiar carpetas o archivos desde el servidor desde linux a wimdows o al pc de administracion. 
`` scp -r nevera1@ssh-nevera1.lenstextil.com:/home/nevera1/MODULO-NEVERA/review_queue/ .``
nota : estar ubicados en en la terminal donde se quiere guardar la carpeta

 Pasar el app.py al servidor
``scp "D:\Desktop\GITHUB jumaar\vorak\MODULO-NEVERA\app.py" nevera1@ssh-nevera1.lenstextil.com:/home/nevera1/MODULO-NEVERA/``

Pasar  la carpeta completa del kisko al servidor
``scp -r "D:\Desktop\GITHUB jumaar\vorak\MODULO-NEVERA\modulo-kiosk-edge" nevera1@ssh-nevera1.lenstextil.com:~/MODULO-NEVERA`` 











## Módulo de Procesamiento para Nevera Inteligente app.py

### 1. Descripción General / modulos importantes 3. y 8.

Este programa en Python actúa como el "cerebro" del sistema de la nevera inteligente. Se ejecuta en un PC (o similar) conectado a la nevera y es responsable de:  

-   **Comunicarse** con el microcontrolador ESP32 para recibir eventos de sensores (puerta, peso, temperatuta). COM1 COM2 COM3 para windows y SERIAL_PORT = '/dev/ttyUSB0' para linux.
-   **Controlar** las cámaras USB global shutter monocromaticas para capturar imágenes durante una interacción.
-   **Procesar** los datos de la sesión de apertura de puerta para correlacionar cambios de peso con productos (identificados por marcadores ArUco).
-   **Enviar de forma robusta** las transacciones y reportes de estado a un servidor backend, con un sistema de reintentos y persistencia offline para no perder ninguna transacción.
-   **Registrar** toda la actividad y los errores en archivos de log para facilitar la monitorización y el diagnóstico se puede usar un servicio de monitoreo como dataDog o New Relic.
-   **Auditar** sesiones de baja confianza guardando las imágenes capturadas para una revisión posterior (carpeta review_queue) , ya sea manual o por otra IA.

El sistema está diseñado para ser robusto y manejar múltiples interacciones rápidas sin perder datos.

### 2. Arquitectura: El Mesero, los Cocineros y el Equipo de Logística

Para garantizar que el sistema siempre esté listo para una nueva apertura de puerta, incluso si el procesamiento anterior no ha terminado, se utiliza un modelo de dos tipos de hilos (threads):

a.  **El Mesero (Hilo Principal)**: Es el hilo principal de la aplicación. Su única tarea es esperar eventos. Cuando la puerta se abre, inicia una sesión de captura. Cuando la sesión termina, empaqueta todos los datos y se los entrega a un "Cocinero". Vuelve inmediatamente a esperar la siguiente apertura de puerta.

b.  **Los Cocineros (Hilos de Procesamiento)**: Por cada sesión terminada, el "Mesero" crea un nuevo hilo "Cocinero" (`session_processing_thread`). Este hilo realiza el trabajo pesado: analiza las imágenes, correlaciona los datos y, si deduce una transacción, la entrega al "Cartero".

c.  **El Cartero (Hilo de Carga a la API)**: El `api_uploader_thread` es responsable de enviar los datos al backend.
    -   Toma los "trabajos" de una cola.
    -   Para transacciones críticas, si el envío falla, lo reintenta varias veces.
    -   Si los reintentos fallan, guarda el paquete en un archivo local y se lo pasa al "Almacenista".

d.  **El Almacenista Offline (Hilo de Envío Offline)**: El `offline_sender_thread` es un trabajador paciente. Periódicamente revisa la carpeta `offline_queue`. Si encuentra paquetes pendientes y hay conexión a internet, los envía al backend, asegurando que ninguna transacción se pierda, incluso si la aplicación se reinicia.

Esta arquitectura asegura que **abrir la puerta rápidamente varias veces no causará errores** y que **ninguna transacción de inventario se perderá** por fallos de red.

### 3. Módulos de Código

El código se organiza en las siguientes funciones y hilos principales dentro de `app.py`:

-  **Hilos de Infraestructura (Trabajadores de Fondo)**

-   `serial_reader_thread()`: El "Recepcionista del ESP32". Lee continuamente los datos de los sensores desde el puerto serie y los pone en una cola.
-   `camera_worker_thread()`: El "Vigilante". Gestiona una cámara, manteniéndola lista y guardando fotogramas cuando se le ordena.
-   `api_uploader_thread()`: El "Cartero". Envía los datos al backend, gestionando reintentos para transacciones críticas.
-   `offline_sender_thread()`: El "Almacenista". Procesa la cola de envíos guardados en disco cuando la conexión se restablece.
-   `product_database_updater_thread()`: El "Gerente de Inventario". Actualiza periódicamente la base de datos de productos desde el backend.

-  **Hilos de Procesamiento de Sesión (Los "Cocineros")** 

-   `session_processing_thread()`: El "Cocinero Jefe". Orquesta el análisis completo de una sesión en un hilo dedicado para no bloquear el sistema.
-   `process_images_for_arucos()`: El "Cocinero Especialista en Visión". Procesa todas las imágenes de una sesión para detectar los marcadores ArUco.

-  **Hilos de Funciones Principales de Lógica y Orquestación**

-   `correlate_and_prepare_upload()`: **LA FUNCIÓN MÁS IMPORTANTE**. Actúa como el "Cocinero de Lógica de Negocio" que orquesta la secuencia de análisis para deducir las transacciones. Llama a las siguientes sub-funciones:
    -   `_synchronize_timestamps()`: Alinea los timestamps de los sensores con el reloj del PC.
    -   `_analyze_aruco_frequency()`: Asigna un rating de confianza global a cada ArUco visto en la sesión.
    -   `_build_state_intervals()`: Divide la sesión en intervalos de tiempo basados en los cambios de peso y crea un inventario de ArUcos para cada uno.
    -   `find_best_candidates()`: Selecciona los candidatos visuales más probables para un cambio de peso.
    -   `_deduce_initial_transactions()`: Genera la primera lista de transacciones candidatas comparando los inventarios entre intervalos.
    -   `_validate_and_resolve_transactions()`: Valida las transacciones por peso y resuelve ambigüedades, incluyendo la lógica de "swap temporal".
    -   `_consolidate_transactions()`: Limpia el resultado final eliminando transacciones de "ruido" (movimientos netos de cero).
    -   `_finalize_session()`: Prepara el lote final para su envío a la cola del "Cartero".

-  **Hilos de Funciones de Soporte y Utilidades**

-   `setup_logging()`: Configura un sistema de registro profesional que escribe en consola y en archivos rotativos.
-   `load_initial_product_database()`: Carga la lista de productos al iniciar el sistema, ya sea desde el backend o desde una caché local.
-   `_save_images_for_review()`: Guarda las imágenes de una sesión cuando se detectan transacciones de baja confianza para auditoría `low_weight_mismatch` o `low_no_match`.
-   `_send_payload()` y `_save_payload_for_offline_sending()`: Funciones auxiliares para el "Cartero" que realizan el envío HTTP y el guardado en disco.
-   **Bucle Principal (`if __name__ == "__main__"`)**: Actúa como el "Mesero". Gestiona la máquina de estados principal (`IDLE`/`CAPTURING`) y delega el trabajo pesado a los hilos "Cocinero".

### 4. Configuración

Todas las configuraciones principales se encuentran al inicio del archivo `app.py`:

-   `SERIAL_PORT`: Puerto COM o tty donde está conectado el ESP32.
-   `CAMERA_INDICES`: Lista de los índices de las cámaras a utilizar (ej. `[0, 1]` para dos cámaras).
-   `CAPTURE_TIMEOUT_SECONDS`: Segundos de inactividad de peso para terminar una sesión de captura.
-   `BACKEND_URL`: La URL del servidor donde se enviarán los resultados.
-   `MAX_UPLOAD_RETRIES`: Número de reintentos inmediatos antes de guardar un envío para más tarde.
-   `OFFLINE_CHECK_INTERVAL_SECONDS`: Cada cuántos segundos el "Almacenista" revisa si hay envíos pendientes.
-   `REVIEW_QUEUE_PATH`: Carpeta donde se guardan las imágenes de las sesiones que requieren revisión.

### 5. Flujo de Operación

1.  **IDLE**: El sistema espera eventos del ESP32.
    -   Si recibe un `door_change` con estado `open`, pasa al estado **CAPTURING**.
    -   Si recibe un `status_report` o `tare_button`, lo pone en la cola de subida para un envío no crítico.
2.  **CAPTURING**: Al abrirse la puerta:
    -   Se activan las cámaras para que empiecen a guardar fotogramas.
    -   Se registran todos los eventos de `weight_change`.
    -   La captura termina si llega un evento `door_change` con estado `closed` o si transcurre el `CAPTURE_TIMEOUT_SECONDS` sin cambios de peso.
3.  **PROCESSING**:
    -   El "Mesero" (bucle principal) empaqueta los datos de la sesión e inicia un nuevo hilo "Cocinero" (`session_processing_thread`).
    -   El "Mesero" vuelve inmediatamente al estado **IDLE**.
    -   El "Cocinero" (`session_processing_thread`) realiza el análisis de correlación (llamando a `correlate_and_prepare_upload`) y pone las transacciones resultantes en la cola de subida.
4.  **UPLOADING (Gestión de Envío)**:
    -   El hilo "Cartero" (`api_uploader_thread`) toma los trabajos de la cola.
    -   Si un trabajo es crítico (`type: "transaction"`), intenta enviarlo. Si falla, reintenta `MAX_UPLOAD_RETRIES` veces.
    -   Si los reintentos fallan, guarda el trabajo en la carpeta `offline_queue`.
    -   El hilo "Almacenista" (`offline_sender_thread`) revisa esa carpeta cada `OFFLINE_CHECK_INTERVAL_SECONDS`. Cuando hay conexión, envía los trabajos pendientes y los elimina.

### 6. Lógica de Correlación (`correlate_and_prepare_upload`)

Esta función orquesta el flujo de análisis para tomar los datos brutos de una sesión y deducir qué productos entraron o salieron. El proceso se divide en pasos claros, cada uno manejado por una sub-función:

1.  **Sincronización y Análisis Previo**: Se sincronizan los timestamps y se analiza la frecuencia global de los ArUcos para obtener un rating de confianza.
1.  **Sincronización y Análisis Previo**: Se sincronizan los timestamps (`_synchronize_timestamps`) y se analiza la frecuencia global de los ArUcos para obtener un rating de confianza (`_analyze_aruco_frequency`).
2.  **Construcción de Intervalos de Estado (`_build_state_intervals`)**: La sesión se divide en segmentos de tiempo, usando cada cambio de peso como un punto de corte. Para cada segmento, se crea un "inventario" de los ArUcos vistos.
3.  **Deducción de Transacciones Iniciales (`_deduce_initial_transactions`)**: Por cada cambio de peso, se comparan los inventarios de ArUcos del intervalo ANTERIOR con el POSTERIOR para generar una lista de transacciones candidatas.
    -   **Si el peso AUMENTA (Producto Añadido)**: Los candidatos son los ArUcos vistos **ANTES** del cambio de peso. (Razón: El usuario muestra el producto a la cámara y *luego* lo pone en la báscula).
    -   **Si el peso DISMINUYE (Producto Retirado)**: Los candidatos son los ArUcos vistos **DESPUÉS** del cambio de peso. (Razón: El usuario saca el producto de la báscula y *luego* lo pasa por la cámara al salir).
4.  **Validación y Resolución de Transacciones (`_validate_and_resolve_transactions`)**: Este es un paso crucial con dos lógicas principales:
    -   **Desambiguación Temporal para Intercambios Rápidos (Nueva Lógica Robusta)**:
        -   **Problema**: Se detecta un patrón de `OUT` ambiguo seguido de un `IN` ambiguo con pesos opuestos (ej. -500g y +505g). Esto suele ocurrir cuando un usuario saca un producto y mete otro rápidamente.
        -   **Solución**: El sistema analiza el intervalo de tiempo entre las dos transacciones. En lugar de confiar en un solo fotograma, toma una muestra de las **primeras detecciones de ArUco** y las **últimas**.
        -   El ArUco más frecuente en la primera muestra se asigna a la transacción de **salida (OUT)**.
        -   El ArUco más frecuente en la última muestra se asigna a la transacción de **entrada (IN)**.
        -   Ambas transacciones se marcan con la confianza `high_temporal_swap_confirmed`.
    -   **Validación por Peso (Flujo Normal)**: Si el patrón de intercambio no se detecta, se aplica la validación estándar. Se compara el `change_g` con el peso nominal de los candidatos de `products.json` para ajustar la confianza (`high_weight_confirmed` o `low_weight_mismatch`).
5.  **Consolidación Final (`_consolidate_transactions`)**:
    -   Calcula el movimiento neto de cada producto (ej. +1 si entró, -1 si salió).
    -   Si un producto tiene un movimiento neto de 0 (ej. el cliente lo sacó y lo volvió a meter), sus transacciones se descartan para no enviar "ruido" al backend.
6.  **Finalización y Envío (`_finalize_session`)**: Se empaquetan las transacciones finales y se determina si la sesión necesita revisión.

### 7. Niveles de Confianza
A cada transacción se le asigna un nivel de confianza para que el backend sepa qué tan fiable es la información:

-   `high_temporal_swap_confirmed`: Máxima confianza. La transacción fue resuelta usando la lógica de desambiguación temporal para un intercambio rápido.
-   `high_swap_confirmed`: Máxima confianza. Se detectó un intercambio de dos productos con peso casi idéntico.
-   `high_weight_confirmed`: Máxima confianza. Evidencia visual y física (peso) coinciden.
-   `high`: Alta confianza. Candidato visual claro, pero sin validación por peso (ej. el producto no estaba en la DB).
-   `medium_global_tiebreak`: Confianza media. Se asigna cuando hay varios candidatos visuales poco frecuentes y se usa la frecuencia global para desempatar.
-   `low_weight_mismatch`: Baja confianza. La evidencia visual y física se contradicen.
-   `low_no_match`: Confianza nula. No se vio ningún ArUco relevante durante el cambio de peso.

### 8. Formato de Datos Enviados al Backend (JSON)

Todos los envíos al backend se realizan mediante una petición `POST` a la `BACKEND_URL`. **Desde la implementación de JWT, todas estas peticiones deben incluir una cabecera de autenticación `Authorization: Bearer <token>` para ser aceptadas por el backend.** El cuerpo de la petición, que se muestra en los siguientes ejemplos, es un JSON con la siguiente estructura general:

✅ Caso 1: Transacción Ideal (Confirmada por Peso)->products.json que se actualiza cada hora desde el backend
Este es el mejor escenario. Se detectó un cambio de peso y solo un producto candidato coincidió visualmente y por peso.

Escenario: Un cliente saca una libra de un producto (-497g). El sistema la ve claramente y el peso coincide.
```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "events": [
    {
      "event": "product_transaction",
      "timestamp": 1757517001234567000,
      "change_g": -497,
      "candidates": [
        {
          "aruco_id": "101",
          "reason": "local_high",
          "nominal_weight_g": 500
        }
      ],
      "confidence": "high_weight_confirmed"
    }
  ]
 }
```


🔄 Caso 2: Intercambio Resuelto por Lógica Temporal
Lógica optimizada para flujo OUT -> IN y no al revez (no se necesita)
Este es el caso especial donde un producto es retirado y otro es ingresado con pesos SIMILARES. La lógica de timestamps resuelve la ambigüedad.

Escenario: Un cliente saca un producto "A" (-1000g) e inmediatamente después, coloca un producto "B" (+1000g). El sistema vio primero el ArUco de "A" y al final el de "B". esto se resuelve tomando todos los arucos del intervalo de tiempo posterior al primer evento y asignando los primeros a "A" y los últimos a "B".   
```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "b2c3d4e5-f6a7-8901-2345-67890abcdef1",
  "events": [
    {
      "event": "product_transaction",
      "timestamp": 1757517105123456000,
      "change_g": -1005,
      "candidates": [
        {
          "aruco_id": "205",
          "reason": "temporal_swap_out_robust",
          "nominal_weight_g": 1000
        }
      ],
      "confidence": "high_temporal_swap_confirmed"
    },
    {
      "event": "product_transaction",
      "timestamp": 1757517109876543000,
      "change_g": 998,
      "candidates": [
        {
          "aruco_id": "310",
          "reason": "temporal_swap_in_robust",
          "nominal_weight_g": 1000
        }
      ],
      "confidence": "high_temporal_swap_confirmed"--> posible mejora en el futuro (esto solo funciona para los valores de peso igual se puede mejorar la logica para que trabaje tambien con valores de peso distintos NOTA: para los pesos distintos lo resuelve products.json, pero AÑADIR mas robustes a esta logica temporal soluciona el problema de que la tabla de products.json no esté actualizada)
    }
  ]
}
```
> **Nota**: La lógica de `high_temporal_swap_confirmed` es más robusta cuando los pesos son distintos, ya que la validación por peso (`products.json`) ayuda a confirmar. Sin embargo, la lógica temporal por sí sola es una mejora significativa para resolver intercambios de productos de peso idéntico que no están actualizados en la base de datos.



❓ Caso 3: Ambigüedad por Peso
Ocurre cuando un cambio de peso podría corresponder a varios productos distintos que tienen un peso similar.

Escenario: La báscula detecta un cambio de -505g. Tanto el "Jugo de Naranja" (Aruco 45) como el "Yogur de Fresa" (Aruco 48) pesan 500g y ambos fueron vistos.y no esta en el base de datos products.json. El sistema no puede decidir y envía ambos como candidatos.

```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "c3d4e5f6-a7b8-9012-3456-7890abcdef12",
  "events": [
    {
      "event": "product_transaction",
      "timestamp": 1757517220987654000,
      "change_g": -505,
      "candidates": [
        {
          "aruco_id": "45",
          "reason": "local_high",
          "nominal_weight_g": 500
        },
        {
          "aruco_id": "48",
          "reason": "local_medium",
          "nominal_weight_g": 500
        }
      ],
      "confidence": "high"
    }
  ]
}
```


⚠️ Caso 4: Baja Confianza (Discrepancia de Peso)
El sistema ve claramente un producto, pero el cambio de peso medido por la báscula no coincide con el peso nominal de ese producto.

Escenario: El sistema ve salir un "Sandwich" (Aruco 77, 200g), pero la báscula solo registró un cambio de -80g.

```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "d4e5f6a7-b8c9-0123-4567-890abcdef123",
  "events": [
    {
      "event": "product_transaction",
      "timestamp": 1757517330123456000,
      "change_g": -80,
      "candidates": [
        {
          "aruco_id": "77",
          "reason": "local_high",
          "nominal_weight_g": 200
        }
      ],
      "confidence": "low_weight_mismatch"  --> **Acción**: Se ejecuta la función `_save_images_for_review` y se guardan las imágenes en la carpeta `review_queue` para una revisión manual.

    }
  ]
}
```


👻 Caso 5: Baja Confianza (Sin Evidencia Visual Directa)
La báscula detecta un cambio de peso, pero en el intervalo de tiempo relevante no se vio ningún ArUco. El sistema envía una lista de los ArUcos más comunes en la sesión como posibles "sospechosos".

Escenario: El peso baja -150g, pero el cliente tapó el producto con la mano. El sistema envía los ArUcos más vistos en general durante la sesión como contexto.

```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "e5f6a7b8-c9d0-1234-5678-90abcdef1234",
  "events": [
    {
      "event": "product_transaction",
      "timestamp": 1757517440987654000,
      "change_g": -150,
      "candidates": [
        {
          "aruco_id": "5",
          "reason": "context_global_high",
          "nominal_weight_g": 330
        },
        {
          "aruco_id": "22",
          "reason": "context_global_medium",
          "nominal_weight_g": 150
        }
      ],
      "confidence": "low_no_match"  --> **Acción**: Se ejecuta la función `_save_images_for_review` y se guardan las imágenes en la carpeta `review_queue` para una revisión manual.
    }
  ]
}
```




⚙️ Eventos de Estado y Sistema
Estos eventos no están relacionados con una transacción de productos y se envían de forma individual, fuera de una sesión de puerta.

ℹ️ Caso 6: Reporte de Estado (type: "status_report")
El ESP32 envía periódicamente un reporte de su estado actual (peso total, estado de la puerta).

Escenario: Reporte periódico (30s) mientras la nevera está inactiva.

```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "f6a7b8c9-d0e1-2345-6789-0abcdef12345",
  "events": [
    {
      "event": "status_report",
      "timestamp": 1757517550123456000,
      "total_weight_g": 8540,
      "door_status": "closed"
    }
  ]
}
```
⚖️ Caso 7: Botón de Tara Presionado (type: "tare_button")
Un operario presiona el botón físico para tarar (poner a cero) la báscula.

Escenario: El operario vacía la nevera y presiona el botón para recalibrar el cero.

```json
{
  "fridge_id": "NEVERA-001-SANTAROSA",
  "batch_id": "a7b8c9d0-e1f2-3456-7890-bcdef1234567",
  "events": [
    {
      "event": "tare_button",
      "timestamp": 1757517660987654000,
      "message": "Tare function executed successfully"
    }
  ]
}
```


###  9. Gestión de la Base de Datos de Productos

El archivo `products.json` es vital para la validación por peso. El sistema lo gestiona de forma automática y resiliente: NOTA:  BACKEND ES RESPONSABLE DE ACTUALIZARLO.

1.  **Al arrancar**, la aplicación siempre intenta descargar la base de datos con ``load_initial_product_database`` desde la `PRODUCT_DATABASE_URL` del backend.
2.  **Si la descarga es exitosa**, crea o sobrescribe el archivo `products.json` local. Este archivo sirve como una caché para operaciones futuras.
3.  **Si la descarga falla** (ej. no hay internet), la aplicación intenta cargar la última versión guardada en el `products.json` local.
4.  **Si ambos pasos fallan**, la aplicación registrará un error crítico pero continuará funcionando en un modo degradado, sin la capacidad de validar pesos, asegurando que el resto de las operaciones no se interrumpan.

### 10. Auditoría y Revisión de Baja Confianza

Para mejorar la fiabilidad del sistema y permitir la corrección de errores, se ha implementado un mecanismo de auditoría para las transacciones que el sistema no puede resolver con alta certeza.

**¿Cuándo se activa?**

-   Cuando una sesión de compra resulta en una o más transacciones con confianza `low_weight_mismatch` o `low_no_match`.

**¿Qué sucede?**

1.  El sistema marca la sesión completa para revisión.
2.  Se crea una carpeta única dentro de `review_queue`. El nombre de esta carpeta es el mismo `batch_id` que se envía al backend.
3.  **Todas las imágenes** capturadas durante esa sesión se guardan en formato `.jpg` dentro de esa carpeta.
4.  El log del sistema registrará una advertencia (`❗`) indicando que la sesión ha sido guardada para revisión.

Esto permite que un operador humano o un sistema de IA secundario pueda analizar las imágenes correspondientes a un `batch_id` específico para verificar qué ocurrió realmente y corregir el inventario si es necesario.




### manjeo de instalacion de camaras

Claro que sí! Aquí tienes un resumen de todo el proceso de depuración que hicimos, partiendo del problema que tenías con las rutas de ls -l /dev/v4l/by-path/.

Resumen del Proceso de Depuración
El Problema Original:

Identificaste correctamente que para usar dos cámaras idénticas, necesitabas sus rutas por puerto físico, que obtuviste con ls -l /dev/v4l/by-path/.
El problema fue que estas rutas (ej. pci-0000:00:14.0-usbv2-0:4:1.0-video-index0) contienen dos puntos (:).
Docker Compose usa los dos puntos para separar la ruta del host de la ruta del contenedor (ej. HOST:CONTENEDOR), lo que causaba errores como too many colons o confusing device mapping.
Intentos Fallidos (y por qué):

Intentamos usar la "sintaxis larga" en la sección volumes, pero Docker Compose seguía teniendo problemas para interpretar esas rutas complejas.
Sugerimos usar /dev/v4l/by-id/, pero tú acertadamente nos corregiste, explicando que al ser cámaras idénticas, no tenían IDs únicos, por lo que by-path era la única opción.
La Solución Definitiva: Reglas udev Como no podíamos cambiar las rutas de las cámaras ni la sintaxis de Docker, decidimos "engañar" al sistema creando nuestros propios nombres de dispositivo, limpios y predecibles.

¿Qué hicimos? Creamos un archivo de reglas en el sistema anfitrión (la nevera) en /etc/udev/rules.d/99-vorak-cameras.rules.
¿Qué hace esa regla? Le dice al sistema operativo Linux:
"Cada vez que detectes una cámara conectada en el puerto físico ...usbv2-0:1:1.0..., en lugar de solo llamarla video0, créale también un alias (un acceso directo) llamado /dev/cam_nevera_0".

Hicimos lo mismo para la segunda cámara, creando el alias /dev/cam_nevera_1.
El Resultado Final:

Ahora, en tu docker-compose.yml, en lugar de usar las rutas largas y problemáticas, usamos nuestros nuevos alias, que son limpios y no tienen dos puntos:
yaml
devices:
  - "/dev/ttyUSB0:/dev/ttyUSB0"
  - "/dev/cam_nevera_0:/dev/video0" # <- Alias limpio y estable
  - "/dev/cam_nevera_1:/dev/video1" # <- Alias limpio y estable
Docker Compose ahora entiende perfectamente estas rutas, y las reglas udev se encargan de que /dev/cam_nevera_0 siempre apunte a la cámara correcta, sin importar si reinicias el equipo o desconectas y vuelves a conectar las cámaras.
En resumen: Creamos alias personalizados y estables en el sistema operativo para evitar los caracteres que confundían a Docker Compose, logrando una configuración robusta y funcional. ¡Fue un gran trabajo en equipo!







-------------------------------------------------------------------------------------------------------


Guía Definitiva: Configuración de Múltiples Cámaras USB Idénticas en Linux con Nombres Personalizados
Este documento detalla el proceso validado para instalar dos o más cámaras USB idénticas en un sistema Linux (como Linux Mint), asignándoles nombres de dispositivo permanentes y personalizados para un uso fiable en cualquier aplicación, incluyendo Docker.

Paso 1: Verificación Inicial del Hardware
El primer paso es confirmar que el sistema operativo reconoce correctamente las cámaras a nivel de hardware y del subsistema de video.

Instalar Herramientas de Video: Abre una terminal e instala el paquete v4l-utils, que contiene herramientas esenciales para interactuar con dispositivos de video.

Bash

sudo apt update
sudo apt install v4l-utils
Listar Dispositivos de Video: Con ambas cámaras conectadas, ejecuta el siguiente comando para listar todos los dispositivos de video que el sistema detecta.   

Bash

v4l2-ctl --list-devices
La salida confirmará que ambas cámaras son reconocidas y mostrará los nodos de dispositivo que se les asignan temporalmente (ej. /dev/video0, /dev/video2, etc.). Es normal que cada cámara física cree dos nodos de video (index0 para captura y index1 para metadatos).   

Paso 2: Configuración de Permisos de Usuario
Para que las aplicaciones puedan acceder a las cámaras sin privilegios de administrador, el usuario debe pertenecer al grupo video.

Añadir Usuario al Grupo video: Ejecuta el siguiente comando para añadir tu usuario actual al grupo video. La opción -aG es crucial para añadir al grupo sin eliminar al usuario de otros grupos.   

Bash

sudo usermod -aG video $USER
Aplicar los Cambios: Para que la nueva membresía de grupo tenga efecto, debes cerrar la sesión por completo y volver a iniciarla. Este paso es obligatorio.

Paso 3: Identificar la Ruta Física Única de cada Cámara
El núcleo del problema con cámaras idénticas es que sus nombres (/dev/videoX) pueden cambiar en cada reinicio. La solución es identificarlas por el puerto USB físico al que están conectadas, que es un identificador estable.

Conecta una cámara a la vez: Para evitar confusiones, conecta solo una cámara en el puerto deseado.

Obtén la información del dispositivo: Usa udevadm para inspeccionar los atributos del dispositivo. Asume que la cámara conectada es /dev/video0 (ajústalo si es necesario según la salida de v4l2-ctl --list-devices).

Bash

udevadm info -a -n /dev/video0
Encuentra el devpath: En la larga salida del comando, busca en los bloques de "parent device" una línea que diga ATTRS{devpath}. Este será un número corto que identifica la ruta en el bus USB (por ejemplo, 1 o 4). Anota este número.

Repite para la otra cámara: Desconecta la primera cámara, conecta la segunda en su puerto designado y repite los pasos 2 y 3 para encontrar su devpath único.

Paso 4: Crear una Regla udev para Nombres Personalizados y Permanentes
Con los devpath únicos identificados, creamos una regla udev para que el sistema genere automáticamente enlaces simbólicos cortos y significativos cada vez que las cámaras se conecten.

Crear el Archivo de Reglas: Abre un editor de texto con privilegios de administrador para crear un nuevo archivo de reglas. El número 99 asegura que se ejecute después de las reglas del sistema.   

Bash

sudo nano /etc/udev/rules.d/99-webcams.rules
Escribir la Regla: Pega el siguiente contenido en el editor, sustituyendo 1 y 4 con los valores de devpath que encontraste en el paso anterior y cam_nevera_0/cam_nevera_1 con los nombres que desees.

Fragmento de código

# Cámara asignada al nombre 'cam_nevera_0' (identificada por el puerto físico con devpath "4")
SUBSYSTEM=="video4linux", ATTRS{devpath}=="4", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_0", GROUP="video", MODE="0666"

# Cámara asignada al nombre 'cam_nevera_1' (identificada por el puerto físico con devpath "1")
SUBSYSTEM=="video4linux", ATTRS{devpath}=="1", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_1", GROUP="video", MODE="0666"
ATTRS{devpath}: Identifica el puerto físico de forma fiable.   

ATTR{index}=="0": Filtra para aplicar la regla solo al dispositivo de captura de video real, ignorando el de metadatos.   

SYMLINK+="cam_nevera_0": La acción principal. Crea el enlace simbólico deseado en el directorio /dev/.   

Guardar y Cerrar: En nano, presiona Ctrl + X, luego Y para guardar, y finalmente Enter.

Aplicar las Nuevas Reglas: Recarga las reglas de udev y activa los cambios sin necesidad de reiniciar.

Bash

sudo udevadm control --reload-rules
sudo udevadm trigger
Paso 5: Verificación Final y Uso
Comprueba que tus nombres personalizados se hayan creado correctamente.

Verificar los Enlaces: Con ambas cámaras conectadas, lista tus nuevos dispositivos:

Bash

ls -l /dev/cam*
La salida debería mostrar tus nuevos nombres apuntando a los dispositivos /dev/videoX correspondientes.

Uso en Aplicaciones: ¡Listo! Ahora puedes usar /dev/cam_nevera_0 y /dev/cam_nevera_1 en todas tus aplicaciones (OBS, scripts, Docker Compose, etc.). Estos nombres son permanentes, predecibles y significativos, resolviendo completamente el problema de la asignación aleatoria.


comando
udevadm info -a -n /dev/video0



jumaar@le-id500:~$ v4l2-ctl --list-devices
USB 2.0 Camera: USB Camera (usb-0000:00:14.0-1):
	/dev/video0
	/dev/video1
	/dev/media0

USB 2.0 Camera: USB Camera (usb-0000:00:14.0-4):
	/dev/video2
	/dev/video3
	/dev/media1

jumaar@le-id500:~$ ls -l /dev/cam*
lrwxrwxrwx 1 root root 6 oct  2  2025 /dev/cam_nevera_0 -> video0
lrwxrwxrwx 1 root root 6 oct  2  2025 /dev/cam_nevera_1 -> video2
jumaar@le-id500:~$ ls -l /dev/v4l/by-path/.
total 0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:1:1.0-video-index0 -> ../../video0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:1:1.0-video-index1 -> ../../video1
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:4:1.0-video-index0 -> ../../video2
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usb-0:4:1.0-video-index1 -> ../../video3
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:1:1.0-video-index0 -> ../../video0
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:1:1.0-video-index1 -> ../../video1
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:4:1.0-video-index0 -> ../../video2
lrwxrwxrwx 1 root root 12 oct  2  2025 pci-0000:00:14.0-usbv2-0:4:1.0-video-index1 -> ../../video3
jumaar@le-id500:~$ sudo nano /etc/udev/rules.d/99-webcams.rules
[sudo] contraseña para jumaar:           
jumaar@le-id500:~$ cat /etc/udev/rules.d/99-webcams.rules
# Cámara 1 (puerto físico...-1, que actualmente es video2)
SUBSYSTEM=="video4linux", ATTRS{devpath}=="4", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_1", GROUP="video", MODE="0666"

# Cámara 2 (puerto físico...-4, que actualmente es video0)
SUBSYSTEM=="video4linux", ATTRS{devpath}=="1", KERNEL=="video*", ATTR{index}=="0", SYMLINK+="cam_nevera_0", GROUP="video", MODE="0666"
