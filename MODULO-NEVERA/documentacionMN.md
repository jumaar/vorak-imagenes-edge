## Guía Completa MODULO-NEVERA

-   **MODULO-SENSORES**: Este módulo es una configuración hecha en ESP32 (leer `documentacion.md` en `MODULO-SENSORES`), que nos envía un reporte de estado cada 30 segundos y eventos cuando la puerta se abre/cierra o cuando hay un cambio de peso.

-   **HARDWARE Y ENTORNO DE EJECUCIÓN**: El sistema está diseñado para ejecutarse en un PC con un sistema operativo Linux que soporte Docker. La aplicación no se instala directamente en el anfitrión, sino que se ejecuta dentro de un **contenedor Docker**, lo que garantiza un entorno consistente y aislado.
    -   **Imagen Docker**: Se utiliza una imagen base `python:3.11-slim-trixie` con las dependencias necesarias (`ffmpeg`, `libgl1`) instaladas.
    -   **Cámaras**: El sistema está diseñado para cámaras web con obturador global. La configuración de qué cámaras usar se gestiona a través del archivo `docker-compose.yml` y una variable de entorno, no modificando el código directamente.

-   **ADMINISTRACIÓN**: (leer `documentacion-IOT.md`) Se mantiene el uso de un túnel SSH a través de Cloudflared para la administración remota segura de cada dispositivo. La revisión de sesiones de baja confianza sigue siendo una tarea clave, accediendo a las imágenes guardadas dentro de los volúmenes del contenedor.

-   **LÓGICA**: `app.py` sigue siendo el cerebro que procesa todos los eventos. Ahora, se ejecuta de forma aislada dentro de su contenedor Docker. La comunicación con el módulo de Kiosko se realiza a través de un **volumen Docker compartido** (`fridge_status`), donde `app.py` escribe el archivo `fridge_status.json` para que el kiosko lo lea.

-   **.env (Archivo de Entorno)**: Este archivo es ahora la fuente principal de configuración.
    -   `FRIDGE_ID="NEVERA-001-SANTAROSA"`: ID único para cada nevera.
    -   `BASE_BACKEND_URL="https://api.lenstextil.com/"`: URL base de la API. Los scripts construyen las URLs completas a partir de esta base.
    -   `FRIDGE_SECRET="una-clave-secreta-muy-larga-y-unica"`: Clave secreta para la autenticación JWT.
    -   `CAMERA_DEVICES="/dev/video0,/dev/video2"`: Lista de rutas de dispositivos de cámara **dentro del contenedor**, separadas por comas. Estas se mapean desde los dispositivos del host en `docker-compose.yml`.

-   **JWT**: Integrado. El sistema utiliza un `AuthManager` para obtener y refrescar automáticamente tokens de autenticación JWT para todas las peticiones al backend.

---













## TAREAS --> V 0.4

nota: en este apartado se colocan ideas y posibles mejoras a futuro , cuando se coloca una queda pendiente, si la tarea se realiza esta se elinina de aca y se implementa inmediatamente en la docuentacion si la mejora fuera positiva.( si esta vacio no hay nada pendiente)

-   Tarea fija: En que version de este modulo estamos para git? -> 0.4





   











## Módulo de Procesamiento para Nevera Inteligente app.py

### 1. Descripción General / módulos importantes 3. y 8.

Este programa en Python actúa como el "cerebro" del sistema de la nevera inteligente. Se ejecuta dentro de un contenedor Docker y es responsable de:

-   **Comunicarse** con el ESP32, detectando automáticamente el puerto serie (`/dev/ttyUSB*` o `/dev/ttyACM*`) mapeado al contenedor.
-   **Controlar** las cámaras USB para capturar imágenes durante una interacción.
-   **Procesar** los datos para correlacionar cambios de peso con productos (identificados por marcadores ArUco).
-   **Enviar de forma robusta** las transacciones al backend, con un sistema de reintentos y persistencia offline en un volumen Docker.
-   **Registrar** la actividad en archivos de log persistentes.
-   **Auditar** sesiones de baja confianza guardando las imágenes en un volumen para revisión posterior.


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

### 4. Configuración (vía Variables de Entorno)

La configuración ya no se realiza modificando el código, sino a través de **variables de entorno** definidas en el archivo `.env` y pasadas al contenedor por `docker-compose`.

-   `FRIDGE_ID`: ID único de la nevera.
-   `BASE_BACKEND_URL`: URL base del servidor backend.
-   `FRIDGE_SECRET`: Clave secreta para la autenticación. Se puede proporcionar como secreto de Docker Swarm.
-   `CAMERA_DEVICES`: Rutas de las cámaras dentro del contenedor, separadas por comas (ej. `/dev/video0,/dev/video2`).
-   `BAUD_RATE`: Velocidad de comunicación con el ESP32 (por defecto `115200`).

El script `app.py` detecta automáticamente el puerto serie (`/dev/ttyUSB*`, `/dev/ttyACM*`) disponible dentro del contenedor.

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
```> **Nota**: La lógica de `high_temporal_swap_confirmed` es más robusta cuando los pesos son distintos, ya que la validación por peso (`products.json`) ayuda a confirmar. Sin embargo, la lógica temporal por sí sola es una mejora significativa para resolver intercambios de productos de peso idéntico que no están actualizados en la base de datos.



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


