import cv2
import time
import requests
import serial
import json
import threading
import queue
import uuid
import logging
from logging.handlers import RotatingFileHandler
import glob
from collections import deque, Counter
import os

# --- Directorio del Script para rutas robustas ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# --- CONFIGURACIÓN PRINCIPAL ---
# ==============================================================================
FRIDGE_ID = os.getenv("FRIDGE_ID", "NEVERA-001-SANTAROSA")
# Lee una variable de entorno 'SERIAL_PORTS' que es una lista de rutas separadas por comas (ej: "/dev/ttyUSB0,/dev/ttyACM0")
# Si no se define, se usa una lista vacía por defecto.
SERIAL_PORTS = [port.strip() for port in os.getenv("SERIAL_PORTS", "").split(',') if port.strip()]
BAUD_RATE = int(os.getenv("BAUD_RATE", 115200))
# --- Configuración de Cámaras ---
# Lee una variable de entorno 'CAMERA_DEVICES' que es una lista de rutas separadas por comas (ej: "/dev/video0,/dev/video2")
# Si no se define, se usa una lista vacía por defecto.
CAMERA_DEVICES = [cam.strip() for cam in os.getenv("CAMERA_DEVICES", "").split(',') if cam.strip()]
CAPTURE_TIMEOUT_SECONDS = 60.0 # Tiempo máximo para capturar imágenes tras el cierre de la puerta.    
BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL") # Se mantiene como variable de entorno

# --- LECTURA DE SECRETOS EN SWARM ---
# En un entorno Swarm, el secreto se monta como un archivo.
# Esta función intenta leerlo desde el archivo, y si no existe,
# vuelve a usar la variable de entorno (para compatibilidad con docker-compose).
def get_fridge_secret():
    secret_path = '/run/secrets/fridge_secret'
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    return os.getenv("FRIDGE_SECRET")

FRIDGE_SECRET = get_fridge_secret()
SHOW_VIDEO = False
TARGET_FPS = 30 # Limita los FPS de las cámaras para optimizar el rendimiento
DEBUG_SAVE_IMAGES = False # <-- Si es True, guarda imágenes con ArUcos detectados

# --- Construcción de URLs dinámicas ---
## Se actualizan las URLs para que coincidan con la nueva estructura unificada de la API,
AUTH_URL = f"{BASE_BACKEND_URL}/api/auth/login" # Nuevo endpoint para obtener el token JWT
## usando como referencia el formato de kiosk.py: /api/<recurso>/<id_nevera>
BACKEND_URL = f"{BASE_BACKEND_URL}/api/transactions/{FRIDGE_ID}"
PRODUCT_DATABASE_URL = f"{BASE_BACKEND_URL}/api/products/{FRIDGE_ID}"

# --- Configuración de Lógica de Negocio y Base de Datos ---
WEIGHT_TOLERANCE_G = 70 # Margen de error aceptado para la coincidencia de peso (en gramos).
# Ruta corregida para que la DB de productos se guarde en el volumen 'nevera_db' montado en /app/db
LOCAL_PRODUCT_DB_PATH = os.path.join(SCRIPT_DIR, 'db', 'products.json')
DB_UPDATE_INTERVAL_SECONDS = 3600 # 120 segundos para probar .. ponerlo a una hora '3600'normalmente en produccion,actualizaciones de la DB de productos.

# --- Configuración de Envío y Persistencia al backend---
OFFLINE_QUEUE_PATH = os.path.join(SCRIPT_DIR, "offline_queue") # Carpeta para guardar transacciones si no hay conexión.
MAX_UPLOAD_RETRIES = 3 # Número de reintentos inmediatos antes de guardar para más tarde.
RETRY_DELAY_SECONDS = 5 # Segundos de espera entre reintentos.
OFFLINE_CHECK_INTERVAL_SECONDS = 60 # Cada cuánto tiempo se revisa la cola offline.
STATUS_REPORT_SEND_INTERVAL_SECONDS = 900 # 15 minutos. Intervalo para enviar reportes de estado al backend.

# --- Configuración de Logging ---
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "fridge_service.log")
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 5 # Mantiene hasta 5 archivos de log antiguos

# --- Configuración de Revisión ---
REVIEW_QUEUE_PATH = os.path.join(SCRIPT_DIR, "review_queue") # Carpeta para guardar imágenes de sesiones de baja confianza.

# --- Configuración de ArUco y Procesamiento de Imagen (tomado de los tests) ---
ARUCO_DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
ARUCO_PARAMETERS = cv2.aruco.DetectorParameters()
ARUCO_PARAMETERS.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
DEBUG_SAVE_IMAGES_PATH = os.path.join(SCRIPT_DIR, "debug_images") # Ruta para guardar imágenes de depuración.


# --- Variables Globales y Locks de Sincronización ---
PRODUCT_DATABASE = {}
PRODUCT_DB_LOCK = threading.Lock()


# ==============================================================================
# --- GESTOR DE AUTENTICACIÓN JWT ---
# ==============================================================================

class AuthManager:
    """
    Clase para gestionar la obtención y el refresco de tokens JWT.
    Es segura para hilos (thread-safe) gracias al uso de un Lock.
    """
    def __init__(self, auth_url, fridge_id, fridge_secret):
        self._auth_url = auth_url
        self._fridge_id = fridge_id
        self._fridge_secret = fridge_secret
        self._token = None
        self._token_expires_at = 0
        self._lock = threading.Lock()

    def _login(self):
        """Método privado para solicitar un nuevo token al backend."""
        logging.info("🔑 Solicitando nuevo token de autenticación JWT...")
        try:
            credentials = {"fridgeId": self._fridge_id, "secret": self._fridge_secret}
            response = requests.post(self._auth_url, json=credentials, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._token = data.get("access_token")
            # Asumimos que el backend devuelve 'expires_in' en segundos.
            # Restamos 60s para refrescar el token un poco antes de que expire.
            expires_in = data.get("expires_in", 3600) 
            self._token_expires_at = time.time() + expires_in - 60
            
            if self._token:
                logging.info("✅ Nuevo token JWT obtenido con éxito.")
            else:
                logging.error("❌ Fallo en la autenticación: El backend no devolvió un token.")

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error de red al intentar obtener el token JWT: {e}")
            self._token = None # Reseteamos el token en caso de fallo

    def get_token(self):
        """Devuelve un token JWT válido, solicitando uno nuevo si es necesario."""
        with self._lock:
            # Si no hay token o si el token ha expirado (o está a punto de expirar)
            if not self._token or time.time() >= self._token_expires_at:
                self._login()
            return self._token



# ==============================================================================
# --- HILOS TRABAJADORES (SENSORES, CÁMARAS, API) ---
# ==============================================================================

def setup_logging():
    """Configura el sistema de logging para que escriba en consola y en un archivo rotativo."""
    # Crear el logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Nivel mínimo de severidad a registrar

    # Crear un formateador para definir el estilo de los logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Configurar el handler para la consola (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Configurar el handler para el archivo rotativo (RotatingFileHandler)
    # Esto previene que el archivo de log crezca indefinidamente.
    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ==============================================================================
# --- HILOS TRABAJADORES (SENSORES, CÁMARAS, API) ---
# ==============================================================================

def serial_reader_thread(ports_to_try, baud, sensor_queue, stop_app_event):
    """
    Hilo dedicado a la comunicación con el ESP32 a través del puerto serie.

    - Intenta conectarse automáticamente a uno de los puertos de la lista `ports_to_try`.
    - Una vez conectado, lee línea por línea los datos enviados por el ESP32.
    - Responde a las solicitudes de sincronización de tiempo ("GET_TIME").
    - Decodifica los mensajes JSON y los coloca en la `sensor_queue` para ser
      procesados por el hilo principal.

    Args:
        ports_to_try (list): Una lista de puertos a intentar (ej. ['/dev/ttyUSB0', 'COM3']).
        baud (int): La velocidad de comunicación (baud rate).
        sensor_queue (queue.Queue): La cola donde se depositan los eventos de los sensores.
        stop_app_event (threading.Event): Evento para señalar la detención del hilo.
    """
    while not stop_app_event.is_set():
        esp32 = None
        for port in ports_to_try:
            try:
                logging.info(f"Intentando conectar al ESP32 en {port}...")
                esp32 = serial.Serial(port, baud, timeout=1)
                logging.info(f"✅ Conexión con ESP32 exitosa en {port}.")
                break  # Salir del bucle for si la conexión es exitosa
            except serial.SerialException:
                continue # Probar el siguiente puerto

        if not esp32:
            logging.error(f"No se pudo conectar a ninguno de los puertos: {ports_to_try}. Reintentando en 10 segundos...")
            time.sleep(10)
            continue # Volver al inicio del bucle while para reintentar

        try:
            while not stop_app_event.is_set():
                if esp32.in_waiting > 0:
                    line = esp32.readline().decode('utf-8').strip()
                    if line == "GET_TIME":
                        current_time_ns = time.time_ns() // 1000
                        esp32.write(f"{current_time_ns}\n".encode())
                    # Solo intentar decodificar si la línea parece ser un objeto JSON
                    elif line.startswith('{') and line.endswith('}'):
                        try:
                            data = json.loads(line)
                            sensor_queue.put(data)
                        except json.JSONDecodeError:
                            logging.warning(f"Error al decodificar JSON desde ESP32: {line}")
        except serial.SerialException as e:
            logging.error(f"Conexión perdida en {esp32.port}: {e}. Buscando de nuevo...")
            if esp32 and esp32.is_open:
                esp32.close()
            time.sleep(5) # Esperar un poco antes de re-escanear

def camera_worker_thread(camera_device, image_cache, capture_event, stop_app_event, auth_manager):
    """
    Hilo que gestiona una única cámara.
    
    - Mantiene la cámara "caliente" (abierta y leyendo frames continuamente) para
      minimizar la latencia al iniciar la captura.
    - Cuando el `capture_event` está activado, guarda los fotogramas capturados
      junto con su timestamp en la `image_cache`.
    - Controla la tasa de captura para no exceder `TARGET_FPS`, optimizando el uso de CPU.

    Args:
        camera_device (str): La ruta del dispositivo de la cámara (ej. '/dev/video0').
        image_cache (collections.deque): Una cola (deque) compartida donde se guardan los fotogramas.
        capture_event (threading.Event): Evento que indica si se debe o no guardar fotogramas.
        stop_app_event (threading.Event): Evento para señalar la detención del hilo.
        auth_manager (AuthManager): El gestor de autenticación para obtener el token.
    """
    cap = cv2.VideoCapture(camera_device, cv2.CAP_V4L2)
    if not cap.isOpened():
        logging.error(f"[Cámara {camera_device}] No se pudo abrir la cámara. Este hilo no se ejecutará.")
        return

    # --- CONFIGURACIÓN DE RESOLUCIÓN (AÑADIDO) ---
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    logging.info(f"[Cámara {camera_device}] Cámara abierta y lista con resolución 1280x720.")

    # Calculamos el tiempo de espera necesario entre fotogramas para alcanzar el FPS objetivo
    frame_delay = 1.0 / TARGET_FPS

    while not stop_app_event.is_set():
        loop_start_time = time.monotonic()

        ret, frame = cap.read()
        if ret and capture_event.is_set():
            ts = time.time_ns()
            image_cache.append({'timestamp': ts, 'frame': frame, 'cam_index': camera_device})

        # --- Control de FPS ---
        elapsed_time = time.monotonic() - loop_start_time
        time_to_wait = frame_delay - elapsed_time
        if time_to_wait > 0:
            time.sleep(time_to_wait)
    cap.release()

def _send_payload(job, auth_manager):
    """
    Intenta enviar un lote de datos al backend.

    Args:
        job (dict): El diccionario del trabajo, que contiene id, datos, etc.

    Returns:
        auth_manager (AuthManager): El gestor de autenticación para obtener el token.
        bool: True si el envío fue exitoso o si es un error que no debe reintentarse (ej. 4xx).
              False si ocurrió un error de red o de servidor (5xx) que justifica un reintento.
    """
    job_id = job['id']
    job_data = job['data']
    
    # El payload final enviado al backend incluye un ID de lote para la deduplicación.
    final_payload = {
        "fridge_id": FRIDGE_ID,
        "batch_id": job_id,
        "events": job_data
    }

    token = auth_manager.get_token()
    if not token:
        logging.error(f"❌ No se pudo enviar el lote {job_id} porque no hay token de autenticación.")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        logging.info(f"📤 Enviando lote {job_id} ({len(job_data)} evento(s)) al backend...")
        response = requests.post(BACKEND_URL, json=final_payload, headers=headers, timeout=15)
        
        if 200 <= response.status_code < 300:
            logging.info(f"✅ Envío exitoso. Lote {job_id}. Respuesta del servidor: {response.status_code}")
            return True
        elif 400 <= response.status_code < 500:           
            # errores de conectividad temporales (ej. 400/404 si el túnel no alcanza el backend).
            # Por seguridad, los tratamos como reintentables.
            logging.warning(f"⚠️ ERROR DE CLIENTE ({response.status_code}) al enviar lote {job_id}. Se reintentará, asumiendo que es un problema temporal del túnel/backend.")
            logging.warning(f"   Respuesta del servidor (primeros 200 chars): {response.text[:200]}")
            return False # Devuelve False para que se reintente.
        else: # Error del servidor 5xx u otros códigos inesperados.
            logging.error(f"❌ ERROR DE SERVIDOR ({response.status_code}) al enviar lote {job_id}. Respuesta: {response.text}")
            return False # Devuelve False para señalar que se necesita un reintento.

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ ERROR DE RED al enviar lote {job_id}: {e}")
        return False # Devuelve False para señalar que se necesita un reintento.

def _save_payload_for_offline_sending(job):
    """Guarda un trabajo fallido en un archivo en el directorio de la cola offline."""
    os.makedirs(OFFLINE_QUEUE_PATH, exist_ok=True)
    file_path = os.path.join(OFFLINE_QUEUE_PATH, f"{job['id']}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(job, f, indent=4)
        logging.info(f"   Lote {job['id']} guardado en {file_path}")
    except IOError as e:
        logging.critical(f"No se pudo guardar el lote {job['id']} para envío offline: {e}")

def api_uploader_thread(upload_queue, stop_app_event, auth_manager):
    """
    Hilo que consume la `upload_queue` y gestiona el envío de datos al backend.

    - Para trabajos críticos ('transaction'), reintenta el envío en caso de fallo.
    - Si los reintentos fallan, guarda el trabajo en disco para el `offline_sender_thread`.
    - Para trabajos no críticos, intenta enviarlos una vez y los descarta si fallan.

    Args:
        upload_queue (queue.Queue): Cola de la que se extraen los trabajos a enviar.
        stop_app_event (threading.Event): Evento para señalar la detención del hilo.
        auth_manager (AuthManager): El gestor de autenticación para obtener el token.
    """
    while not stop_app_event.is_set():
        try:
            job = upload_queue.get(timeout=1)
            
            success = _send_payload(job, auth_manager)

            if not success and job['type'] == 'transaction':
                job['attempts'] += 1
                if job['attempts'] < MAX_UPLOAD_RETRIES:
                    logging.warning(f"   Reintentando envío en {RETRY_DELAY_SECONDS}s... (Intento {job['attempts']}/{MAX_UPLOAD_RETRIES})")
                    time.sleep(RETRY_DELAY_SECONDS)
                    upload_queue.put(job) # Poner de nuevo en la cola para otro intento.
                else:
                    logging.error(f"   Máximo de reintentos alcanzado. Guardando para envío offline.")
                    _save_payload_for_offline_sending(job)
            
            # Para envíos exitosos, errores 4xx, o fallos de trabajos no críticos,
            # el trabajo se considera finalizado y se saca de la cola.
            upload_queue.task_done()

        except queue.Empty:
            continue

def offline_sender_thread(stop_event, auth_manager):
    """Revisa periódicamente el directorio offline y reintenta enviar los trabajos guardados."""
    logging.info("🛰️  Hilo de envío offline iniciado.")
    while not stop_event.wait(OFFLINE_CHECK_INTERVAL_SECONDS):
        if not os.path.isdir(OFFLINE_QUEUE_PATH):
            continue

        for file_path in glob.glob(os.path.join(OFFLINE_QUEUE_PATH, "*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    job = json.load(f)
                
                if _send_payload(job, auth_manager):
                    logging.info(f"🛰️  [Offline] Lote {job['id']} enviado con éxito. Eliminando archivo.")
                    os.remove(file_path)
            except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
                logging.warning(f"🛰️  [Offline] Error procesando archivo {file_path}: {e}. Se reintentará más tarde.")

def product_database_updater_thread(url, local_path, interval_seconds, stop_event, auth_manager):
    """
    Hilo que actualiza periódicamente la base de datos de productos desde el backend.

    - Al iniciar, intenta cargar una versión desde la caché local para operar de inmediato.
    - Luego, entra en un bucle para sincronizar con el backend.
    - Si no hay conexión o no hay caché, entra en un modo de reintento rápido.
    - Una vez que la base de datos se descarga con éxito, cambia al intervalo de actualización normal.
    - Este proceso se ejecuta en segundo plano y no bloquea el arranque de la aplicación.
    - Usa el AuthManager para autenticar la petición.
    """
    global PRODUCT_DATABASE
    FAST_RETRY_INTERVAL_SECONDS = 60
    
    logging.info("🔄 [Updater] Hilo de actualización de base de datos iniciado.")
    
    # --- PASO 1: Carga inicial desde caché local (no bloqueante) ---
    has_initial_cache = False
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            with PRODUCT_DB_LOCK:
                PRODUCT_DATABASE = json.load(f)
            logging.info(f"✅ [Updater] Base de datos cargada desde caché local '{local_path}' con {len(PRODUCT_DATABASE)} entradas.")
            has_initial_cache = True
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"⚠️ [Updater] No se encontró o no se pudo leer la caché local. Se intentará la descarga desde el backend de inmediato.")
        # PRODUCT_DATABASE ya es {} por defecto.

    # --- PASO 2: Bucle de sincronización continua con el backend ---
    is_in_fast_retry_mode = not has_initial_cache
    is_first_run = True
    
    while not stop_event.is_set():
        # En la primera ejecución, no esperamos. En las siguientes, sí.
        if not is_first_run:
            current_interval = FAST_RETRY_INTERVAL_SECONDS if is_in_fast_retry_mode else interval_seconds
            if stop_event.wait(current_interval):
                break # Salir del bucle si la aplicación se está deteniendo.
        is_first_run = False

        if is_in_fast_retry_mode:
            logging.info(f"🔄 [Updater] Intentando descargar base de datos (reintento rápido)...")
        else:
            logging.info("🔄 [Updater] Verificando actualizaciones de la base de datos de productos...")

        try:
            token = auth_manager.get_token()
            if not token:
                logging.warning("⚠️ [Updater] No se puede actualizar la DB de productos, no hay token de autenticación. Reintentando...")
                is_in_fast_retry_mode = True
                continue

            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            new_db_content = response.json()

            # Si estábamos en modo de reintento rápido y tuvimos éxito, volvemos al modo normal.
            if is_in_fast_retry_mode:
                logging.info(f"✅ [Updater] ¡Éxito en reintento! Base de datos descargada. Cambiando a intervalo normal de {interval_seconds}s.")
                is_in_fast_retry_mode = False

            with PRODUCT_DB_LOCK:
                if new_db_content != PRODUCT_DATABASE:
                    logging.info("✨ [Updater] Nueva versión de la base de datos encontrada. Actualizando...")
                    PRODUCT_DATABASE = new_db_content
                    with open(local_path, 'w', encoding='utf-8') as f:
                        json.dump(new_db_content, f, indent=2, ensure_ascii=False) 
                    logging.info("✅ [Updater] Base de datos en memoria y caché local actualizadas.")
                else:
                    logging.info("👍 [Updater] La base de datos de productos ya está actualizada.")

        except requests.exceptions.RequestException as e:
            # Si falla la conexión, y no estábamos ya en modo de reintento rápido, entramos en él.
            if not is_in_fast_retry_mode:
                logging.error(f"⚠️ [Updater] Fallo en la conexión durante actualización normal ({e}). Entrando en modo de reintento rápido.")
                is_in_fast_retry_mode = True
            else:
                logging.warning(f"⚠️ [Updater] No se pudo conectar al backend para la base de datos ({e}). Se reintentará en modo rápido.")
        except json.JSONDecodeError:
             logging.error("❌ [Updater] Error al decodificar el JSON recibido del backend. Se reintentará.")


def _save_images_for_review(batch_id, image_cache):
    """Guarda las imágenes de una sesión de baja confianza para revisión manual o por IA."""
    review_folder = os.path.join(REVIEW_QUEUE_PATH, batch_id)
    try:
        os.makedirs(review_folder, exist_ok=True)
        logging.info(f"💾 Guardando {len(image_cache)} imágenes para revisión en: {review_folder}")
        for image_data in image_cache:
            filename = f"review_{image_data['timestamp']}_cam{str(image_data['cam_index']).replace('/','_')}.jpg"
            filepath = os.path.join(review_folder, filename)
            # Guardar la imagen. El 'quality' es para JPG, 95 es un buen valor por defecto.
            cv2.imwrite(filepath, image_data['frame'], [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        logging.info("✅ Imágenes para revisión guardadas con éxito.")
    except Exception as e:
        logging.error(f"❌ No se pudieron guardar las imágenes para revisión para el lote {batch_id}: {e}")


# ==============================================================================
# --- HILOS Y FUNCIONES DE PROCESAMIENTO DE SESIÓN ("LOS COCINEROS") ---
# ==============================================================================

def process_images_for_arucos(image_cache):
    """
    Función "Cocinero Especialista" para el análisis de imágenes.

    Recibe un lote de imágenes y aplica un pipeline de procesamiento para detectar marcadores ArUco.
    El pipeline es: `Color -> Escala de Grises -> CLAHE -> Detección de ArUco`.
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) es crucial para mejorar el
      contraste en condiciones de iluminación difíciles.

    Retorna una lista de todas las detecciones encontradas, cada una con su `timestamp` y `aruco_id`.
    """
    if not image_cache:
        logging.warning("No se capturaron imágenes en esta sesión.")
        return []

    # --- Detección de ArUcos con pipeline mejorado (Gris -> CLAHE -> Detect) ---
    all_detections = []
    # Solo procedemos si hay imágenes que analizar.
    if image_cache:
        # Creamos una instancia del detector y del filtro CLAHE una sola vez para reutilizarlos en el bucle.
        detector = cv2.aruco.ArucoDetector(ARUCO_DICTIONARY, ARUCO_PARAMETERS)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Si la depuración está activa, nos aseguramos de que la carpeta de salida exista.
        if DEBUG_SAVE_IMAGES:
            os.makedirs(DEBUG_SAVE_IMAGES_PATH, exist_ok=True)

        # Iteramos sobre cada imagen capturada durante la sesión.
        for image_data in image_cache:
            # --- INICIO DEL PIPELINE DE PROCESAMIENTO ---
            # Paso 1: Convertir la imagen original (BGR) a escala de grises (1 canal).
            # Esto es un requisito para CLAHE y reduce la complejidad para el detector.
            gray_frame = cv2.cvtColor(image_data['frame'], cv2.COLOR_BGR2GRAY)

            # Paso 2: Aplicar CLAHE (Contrast Limited Adaptive Histogram Equalization).
            # Este filtro mejora drásticamente el contraste en la imagen, especialmente en condiciones
            # de iluminación desigual (sombras, reflejos), haciendo los bordes de los ArUcos más nítidos.
            clahe_frame = clahe.apply(gray_frame)

            # Paso 3: Detectar los marcadores ArUco en la imagen ya procesada con CLAHE.
            corners, markerIds, _ = detector.detectMarkers(clahe_frame)
            # --- FIN DEL PIPELINE DE PROCESAMIENTO ---

            # Si se encontraron marcadores, los registramos para el reporte final.
            if markerIds is not None:
                for marker_id in markerIds.flatten():
                    all_detections.append({
                        'timestamp': image_data['timestamp'],
                        'aruco_id': str(marker_id)
                    })

            # Si la depuración está activa, guardamos TODAS las imágenes procesadas de la sesión.
            if DEBUG_SAVE_IMAGES:
                # Convertimos la imagen CLAHE (monocromática) a BGR (color) para poder dibujar sobre ella.
                debug_frame = cv2.cvtColor(clahe_frame, cv2.COLOR_GRAY2BGR)
                # Si se encontraron marcadores en ESTA imagen, los dibujamos.
                if markerIds is not None:
                    cv2.aruco.drawDetectedMarkers(debug_frame, corners, markerIds)
                # Guardamos la imagen, contenga o no marcadores dibujados.
                debug_filename = f"session_img_{image_data['timestamp']}.jpg"
                cv2.imwrite(os.path.join(DEBUG_SAVE_IMAGES_PATH, debug_filename), debug_frame)

    return all_detections

def _synchronize_timestamps(sensor_events, time_offset_ns):
    """Alinea los timestamps de los eventos del sensor (ESP32) al reloj del PC."""
    corrected_events = []
    for event in sensor_events:
        corrected_event = event.copy()
        esp_time_ns = corrected_event['timestamp'] * 1000
        pc_equivalent_time_ns = esp_time_ns + time_offset_ns
        corrected_event['timestamp'] = pc_equivalent_time_ns
        corrected_events.append(corrected_event)
    return corrected_events

def _analyze_aruco_frequency(aruco_detections):
    """Calcula la frecuencia de cada ArUco y les asigna un rating de confianza global."""
    if not aruco_detections:
        return Counter(), {}

    aruco_id_counts = Counter(d['aruco_id'] for d in aruco_detections)
    aruco_confidence_rating = {}
    
    sorted_arucos = aruco_id_counts.most_common()
    if not sorted_arucos:
        return aruco_id_counts, {}

    # El más frecuente es 'high' (probablemente un marcador estático)
    high_confidence_id, _ = sorted_arucos[0]
    aruco_confidence_rating[high_confidence_id] = 'high'
    
    # Clasificar el resto
    for aruco_id, count in sorted_arucos[1:]:
        aruco_confidence_rating[aruco_id] = 'low' if count <= 3 else 'medium'
        
    return aruco_id_counts, aruco_confidence_rating

def _build_state_intervals(corrected_sensor_events, all_aruco_detections):
    """
    Divide la sesión en intervalos de tiempo basados en eventos clave y crea un
    inventario de ArUcos para cada uno.
    """
    SESSION_END_BUFFER_NS = 100_000_000  # 100ms

    weight_events = sorted([e for e in corrected_sensor_events if e['event'] == 'weight_change'], key=lambda x: x['timestamp'])
    door_open_event = next((e for e in corrected_sensor_events if e.get('status') == 'open'), None)
    door_close_event = next((e for e in corrected_sensor_events if e.get('status') == 'closed'), None)

    if not door_open_event or not door_close_event:
        logging.error("Error de sesión: No se encontraron eventos de apertura y/o cierre. No se puede procesar.")
        return None, None, None

    session_start_ts = door_open_event['timestamp']
    session_end_ts = door_close_event['timestamp'] + SESSION_END_BUFFER_NS

    # Filtrar ArUcos para que pertenezcan solo a esta sesión
    session_aruco_detections = [d for d in all_aruco_detections if session_start_ts <= d['timestamp'] < session_end_ts]

    # Crear los límites de tiempo para cada intervalo
    time_boundaries = [door_open_event['timestamp']]
    time_boundaries.extend([e['timestamp'] for e in weight_events])
    time_boundaries.append(door_close_event['timestamp'])

    # Crear un inventario de ArUcos para cada intervalo
    arucos_per_interval = []
    for i in range(len(time_boundaries) - 1):
        start_t, end_t = time_boundaries[i], time_boundaries[i+1]
        
        detections_in_slice = [d['aruco_id'] for d in session_aruco_detections if start_t <= d['timestamp'] < end_t]
        interval_counts = Counter(detections_in_slice)
        
        inventory_in_slice = {}
        if interval_counts:
            sorted_arucos_interval = interval_counts.most_common()
            inventory_in_slice[sorted_arucos_interval[0][0]] = 'high'
            for aruco_id, count in sorted_arucos_interval[1:]:
                inventory_in_slice[aruco_id] = 'low' if count <= 3 else 'medium'
        arucos_per_interval.append(inventory_in_slice)
        
    return weight_events, arucos_per_interval, session_aruco_detections

def _deduce_initial_transactions(weight_events, arucos_per_interval, aruco_confidence_rating, find_best_candidates_func):
    """Genera una lista de transacciones candidatas basadas en la comparación de inventarios entre intervalos."""
    final_transactions = []
    for i, weight_event in enumerate(weight_events):
        arucos_before = arucos_per_interval[i]
        arucos_after = arucos_per_interval[i+1]
        change_g = weight_event['change_g']

        transaction = {
            "event": "product_transaction",
            "timestamp": weight_event['timestamp'],
            "change_g": change_g,
            "candidates": [],
            "confidence": "low"
        }

        if change_g > 0:  # Producto AÑADIDO (IN)
            candidate_ids = set(arucos_before.keys())
            candidates, confidence = find_best_candidates_func(candidate_ids, arucos_before, aruco_confidence_rating)
            transaction.update({"candidates": candidates, "confidence": confidence})
            final_transactions.append(transaction)

        elif change_g < 0:  # Producto RETIRADO (OUT)
            candidate_ids = set(arucos_after.keys())
            candidates, confidence = find_best_candidates_func(candidate_ids, arucos_after, aruco_confidence_rating)
            transaction.update({"candidates": candidates, "confidence": confidence})
            final_transactions.append(transaction)

        elif change_g == 0: # Posible SWAP de productos de igual peso
            in_candidate_ids = set(arucos_before.keys())
            out_candidate_ids = set(arucos_after.keys())

            if not in_candidate_ids or not out_candidate_ids:
                continue

            in_candidates, _ = find_best_candidates_func(in_candidate_ids, arucos_before, aruco_confidence_rating)
            out_candidates, _ = find_best_candidates_func(out_candidate_ids, arucos_after, aruco_confidence_rating)

            best_pair = None
            min_weight_diff = float('inf')
            for in_cand in in_candidates:
                if 'nominal_weight_g' not in in_cand: continue
                for out_cand in out_candidates:
                    if 'nominal_weight_g' not in out_cand or in_cand['aruco_id'] == out_cand['aruco_id']: continue
                    
                    weight_diff = abs(in_cand['nominal_weight_g'] - out_cand['nominal_weight_g'])
                    if weight_diff <= WEIGHT_TOLERANCE_G and weight_diff < min_weight_diff:
                        min_weight_diff = weight_diff
                        best_pair = (in_cand, out_cand)

            if best_pair:
                in_product, out_product = best_pair
                final_transactions.append({"event": "product_transaction", "timestamp": weight_event['timestamp'] - 1, "change_g": in_product['nominal_weight_g'], "candidates": [in_product], "confidence": "high_swap_confirmed"})
                final_transactions.append({"event": "product_transaction", "timestamp": weight_event['timestamp'], "change_g": -out_product['nominal_weight_g'], "candidates": [out_product], "confidence": "high_swap_confirmed"})

    return final_transactions

def _validate_and_resolve_transactions(initial_transactions, session_aruco_detections, create_candidate_func):
    """Valida transacciones por peso y resuelve ambigüedades, incluyendo el 'temporal swap'."""
    validated_transactions = []
    i = 0
    while i < len(initial_transactions):
        t_actual = initial_transactions[i]
        pair_resolved = False

        # Lógica de Desambiguación Temporal para Pares Opuestos
        is_potential_pair_start = (
            t_actual['change_g'] < 0 and len(t_actual.get('candidates', [])) > 1 and i + 1 < len(initial_transactions)
        )

        if is_potential_pair_start:
            t_siguiente = initial_transactions[i + 1]
            is_pair_complete = (
                t_siguiente['change_g'] > 0 and
                abs(t_actual['change_g'] + t_siguiente['change_g']) <= WEIGHT_TOLERANCE_G and
                len(t_siguiente.get('candidates', [])) > 1
            )

            if is_pair_complete:
                start_time, end_time = t_actual['timestamp'], t_siguiente['timestamp']
                interval_detections = sorted([d for d in session_aruco_detections if start_time <= d['timestamp'] <= end_time], key=lambda d: d['timestamp'])
                
                if interval_detections:
                    sample_size = 6
                    first_sample_ids = [d['aruco_id'] for d in interval_detections[:sample_size]]
                    last_sample_ids = [d['aruco_id'] for d in interval_detections[-sample_size:]]
                    
                    if first_sample_ids and last_sample_ids:
                        first_aruco_id = Counter(first_sample_ids).most_common(1)[0][0]
                        last_aruco_id = Counter(last_sample_ids).most_common(1)[0][0]
                        
                        t_actual['candidates'] = [create_candidate_func(first_aruco_id, "temporal_swap_out_robust")]
                        t_actual['confidence'] = "high_temporal_swap_confirmed"
                        validated_transactions.append(t_actual)
                        
                        t_siguiente['candidates'] = [create_candidate_func(last_aruco_id, "temporal_swap_in_robust")]
                        t_siguiente['confidence'] = "high_temporal_swap_confirmed"
                        validated_transactions.append(t_siguiente)
                        
                        i += 2
                        pair_resolved = True

        # Flujo Normal de Validación por Peso
        if not pair_resolved:
            if not t_actual.get('candidates'):
                validated_transactions.append(t_actual)
            else:
                weight_matches = []
                for candidate in t_actual['candidates']:
                    with PRODUCT_DB_LOCK:
                        product_info = PRODUCT_DATABASE.get(candidate['aruco_id'])
                    if product_info and abs(abs(t_actual['change_g']) - product_info['nominal_weight_g']) <= WEIGHT_TOLERANCE_G:
                        weight_matches.append(candidate)
                
                if len(weight_matches) == 1:
                    t_actual['candidates'] = weight_matches
                    if t_actual['confidence'] != 'high_swap_confirmed':
                        t_actual['confidence'] = 'high_weight_confirmed'
                elif len(weight_matches) > 1:
                    t_actual['candidates'] = weight_matches
                else:
                    t_actual['confidence'] = 'low_weight_mismatch'
                validated_transactions.append(t_actual)
            i += 1
            
    return validated_transactions

def _consolidate_transactions(validated_transactions):
    """Elimina ruido cancelando pares de IN/OUT (por peso sin evidencia y por ArUco)."""
    # 1. Consolidación por peso para eventos sin evidencia visual
    in_events_no_evidence = [t for t in validated_transactions if t['change_g'] > 0 and (t['confidence'] == 'low_no_match' or not t['candidates'])]
    out_events_no_evidence = [t for t in validated_transactions if t['change_g'] < 0 and (t['confidence'] == 'low_no_match' or not t['candidates'])]
    remaining = [t for t in validated_transactions if t not in in_events_no_evidence and t not in out_events_no_evidence]
    
    for out_event in list(out_events_no_evidence):
        best_match = next((in_event for in_event in in_events_no_evidence if abs(out_event['change_g'] + in_event['change_g']) <= WEIGHT_TOLERANCE_G), None)
        if best_match:
            out_events_no_evidence.remove(out_event)
            in_events_no_evidence.remove(best_match)

    # 2. Consolidación por ArUco para movimientos netos de cero
    pre_consolidated = remaining + in_events_no_evidence + out_events_no_evidence
    aruco_net_change = Counter()
    for t in pre_consolidated:
        if len(t.get('candidates', [])) == 1:
            aruco_id = t['candidates'][0]['aruco_id']
            aruco_net_change[aruco_id] += 1 if t['change_g'] > 0 else -1

    consolidated = [t for t in pre_consolidated if len(t.get('candidates', [])) != 1]
    net_change_tracker = aruco_net_change.copy()

    for t in sorted([t for t in pre_consolidated if len(t.get('candidates', [])) == 1], key=lambda x: x['timestamp']):
        aruco_id = t['candidates'][0]['aruco_id']
        if net_change_tracker[aruco_id] > 0 and t['change_g'] > 0:
            consolidated.append(t)
            net_change_tracker[aruco_id] -= 1
        elif net_change_tracker[aruco_id] < 0 and t['change_g'] < 0:
            consolidated.append(t)
            net_change_tracker[aruco_id] += 1

    return sorted(consolidated, key=lambda x: x['timestamp'])

def _finalize_session(consolidated_transactions, upload_queue):
    """Prepara el lote final para envío, determina si necesita revisión y lo encola."""
    if not consolidated_transactions:
        logging.info("  - Resultado: No se generaron transacciones netas en esta sesión.")
        return None, False

    needs_review = any(t['confidence'] in ['low_weight_mismatch', 'low_no_match'] for t in consolidated_transactions)
    
    logging.info(f"  - Resultado: {len(consolidated_transactions)} transacciones netas para enviar.")
    if needs_review:
        logging.warning("  - ❗ Esta sesión contiene transacciones de baja confianza. Las imágenes se guardarán para revisión.")
    
    batch_id = str(uuid.uuid4())
    job = {
        "id": batch_id,
        "type": "transaction",
        "data": consolidated_transactions,
        "attempts": 0
    }
    upload_queue.put(job)
    
    return batch_id, needs_review

def correlate_and_prepare_upload(aruco_detections, sensor_events, time_offset_ns, upload_queue):
    """
    La función más inteligente del sistema ("Cocinero de Lógica de Negocio").
    Recibe los datos brutos de una sesión (detecciones de ArUcos y eventos de sensores)
    y deduce qué productos entraron o salieron de la nevera.

    El proceso se divide en los siguientes pasos:
    1.  Sincronizar timestamps de sensores.
    2.  Analizar frecuencia de ArUcos para obtener un rating de confianza global.
    3.  Construir intervalos de estado basados en eventos de peso y puerta.
    4.  Deducir transacciones iniciales comparando los inventarios de ArUco entre intervalos.
    5.  Validar y resolver transacciones usando el peso y la lógica de "swap temporal".
    6.  Consolidar transacciones para eliminar ruido (movimientos de entrada/salida netos cero).
    7.  Finalizar la sesión, empaquetar el lote y ponerlo en la cola de envío.
    """
    # --- DATOS DE ENTRADA ---
    logging.info(f"  - Datos de entrada: {len(aruco_detections)} detecciones de ArUco, {len(sensor_events)} eventos de sensor.")

    def _create_candidate_with_weight(aruco_id, reason):
        """Crea un diccionario de candidato y le añade el peso nominal si lo encuentra en la DB."""
        candidate_info = {"aruco_id": aruco_id, "reason": reason}
        with PRODUCT_DB_LOCK:
            product_data = PRODUCT_DATABASE.get(aruco_id)
            if product_data and 'nominal_weight_g' in product_data:
                candidate_info['nominal_weight_g'] = product_data['nominal_weight_g']
        return candidate_info

    def find_best_candidates(candidate_ids, source_inventory, global_ratings):
        """Aplica una lógica de "embudo" para encontrar los mejores candidatos de una lista."""
        # CASO 3: No hay candidatos en el intervalo.
        if not candidate_ids:
            confidence = "low_no_match"
            final_candidates = []
            
            # Ordenar los ArUcos globales por su rating para que el backend los reciba en orden de importancia.
            rating_priority = ['high', 'medium', 'low']
            sorted_global_arucos = sorted(global_ratings.items(), key=lambda item: rating_priority.index(item[1]))

            for aruco_id, rating in sorted_global_arucos:
                final_candidates.append(_create_candidate_with_weight(aruco_id, f"context_global_{rating}"))
            
            return final_candidates, confidence

        # Separar candidatos por su calificación LOCAL en el inventario de origen
        local_high = {cid for cid in candidate_ids if source_inventory.get(cid) == 'high'}
        local_medium = {cid for cid in candidate_ids if source_inventory.get(cid) == 'medium'}
        local_low = {cid for cid in candidate_ids if source_inventory.get(cid) == 'low'}

        final_candidates = []
        confidence = "low"

        # Prioridad #1: Usar los mejores candidatos locales si existen
        if local_high or local_medium:
            confidence = "high"
            for cid in local_high:
                final_candidates.append(_create_candidate_with_weight(cid, "local_high"))
            for cid in local_medium:
                final_candidates.append(_create_candidate_with_weight(cid, "local_medium"))

        # Prioridad #2: Si solo hay 'low' locales, usar el global para desempatar
        elif local_low:
            confidence = "medium_global_tiebreak"
            
            # Encontrar el mejor candidato de los 'low' locales basándose en su rating global
            # El orden de la lista define la prioridad: 'high' > 'medium' > 'low'
            rating_priority = ['high', 'medium', 'low']
            best_candidate_by_global = min(local_low, key=lambda cid: rating_priority.index(global_ratings.get(cid, 'low')))
            global_rating_of_best = global_ratings.get(best_candidate_by_global, 'low')
            
            # 1. Añadir el candidato principal encontrado por desempate
            final_candidates.append(_create_candidate_with_weight(best_candidate_by_global, f"global_tiebreak_{global_rating_of_best}"))

            # 2. Añadir los ArUcos HIGH y MEDIUM globales como contexto adicional para el backend.
            # Esto le da al backend más opciones si el peso del candidato principal no coincide.
            global_context_candidates = []
            for aruco_id, rating in global_ratings.items():
                # Nos aseguramos de no añadir duplicados si el candidato principal ya era un high/medium global
                if aruco_id != best_candidate_by_global:
                    if rating == 'high':
                        final_candidates.append(_create_candidate_with_weight(aruco_id, "context_global_high"))
                        global_context_candidates.append(f"{aruco_id} (high)")
                    elif rating == 'medium':
                        final_candidates.append(_create_candidate_with_weight(aruco_id, "context_global_medium"))
                        global_context_candidates.append(f"{aruco_id} (medium)")

        # Prioridad #3: Si algo falla o no hay candidatos claros
        else:
            confidence = "low_no_match"

        return final_candidates, confidence

    # --- PASO 1: Sincronizar y preparar datos básicos ---
    corrected_sensor_events = _synchronize_timestamps(sensor_events, time_offset_ns)
    _, aruco_confidence_rating = _analyze_aruco_frequency(aruco_detections)

    # --- ANÁLISIS PRELIMINAR DE FALLOS ---
    weight_events_check = [e for e in corrected_sensor_events if e['event'] == 'weight_change']
    if weight_events_check and not aruco_detections:
        logging.error("❗ FALLO DE VISIÓN CRÍTICO: Se detectaron cambios de peso pero CERO ArUcos en toda la sesión.")
        logging.error("   Posibles causas: Lente de cámara sucia/obstruida, mala iluminación, fallo de cámara, o no se mostraron productos.")

    # --- PASO 2: Dividir la sesión en intervalos de estado ---
    result = _build_state_intervals(corrected_sensor_events, aruco_detections)
    weight_events, arucos_per_interval, session_aruco_detections = result

    # Si _build_state_intervals falla (ej. por falta de evento de cierre), devuelve None.
    # Debemos verificar esto antes de continuar para evitar el TypeError.
    if weight_events is None:
        logging.warning("  - Análisis abortado: no se pudieron construir los intervalos de estado (probablemente por timeout sin cierre de puerta).")
        return None, False

    # --- PASO 3: Deducir transacciones iniciales ---
    initial_transactions = _deduce_initial_transactions(weight_events, arucos_per_interval, aruco_confidence_rating, find_best_candidates)

    # --- PASO 4: Validar y resolver transacciones ---
    validated_transactions = _validate_and_resolve_transactions(initial_transactions, session_aruco_detections, _create_candidate_with_weight)

    # --- PASO 5: Consolidar transacciones para eliminar ruido ---
    consolidated_transactions = _consolidate_transactions(validated_transactions)

    # --- PASO 6: Finalizar y encolar el reporte ---
    batch_id, needs_review = _finalize_session(consolidated_transactions, upload_queue)

    return batch_id, needs_review

def session_processing_thread(session_data, upload_queue):
    """
    Hilo "Cocinero Jefe": Orquesta el procesamiento de una sesión finalizada.

    Este hilo se crea cada vez que una sesión de captura termina. Su trabajo es:
    1. Llamar al "Cocinero Especialista" de imágenes (`process_images_for_arucos`).
    2. Llamar al "Cocinero de Lógica de Negocio" (`correlate_and_prepare_upload`).

    Al ejecutarse en un hilo separado, el procesamiento pesado no bloquea al hilo
    principal ("Mesero"), que puede volver inmediatamente a esperar la siguiente apertura de puerta.
    """
    logging.info("="*20 + " ⚙️ INICIO ANÁLISIS DE SESIÓN " + "="*20)
    # 1. Procesar imágenes para obtener las detecciones de ArUco.
    aruco_detections = process_images_for_arucos(session_data['images'])
    # 2. Correlacionar ArUcos con eventos de sensores y preparar el envío.
    batch_id, needs_review = correlate_and_prepare_upload(aruco_detections, session_data['sensors'], session_data['time_offset_ns'], upload_queue)
    
    # 3. Si la sesión fue marcada para revisión, guardar las imágenes.
    if needs_review and batch_id:
        _save_images_for_review(batch_id, session_data['images'])

    logging.info("="*62)

# ==============================================================================
# --- LÓGICA PRINCIPAL (EL "MESERO") ---
# ==============================================================================
if __name__ == "__main__":
    # --- El "Mesero": Hilo principal de la aplicación ---
    # Su única tarea es esperar eventos, gestionar la máquina de estados (IDLE/CAPTURING)
    # y delegar el trabajo pesado a los hilos "Cocinero".
    # --- Colas de comunicación entre hilos ---
    sensor_events_queue = queue.Queue()
    upload_queue = queue.Queue()
    
    stop_app_event = threading.Event()
    capture_event = threading.Event()

    # Crear una única instancia del gestor de autenticación para toda la aplicación
    auth_manager = AuthManager(AUTH_URL, FRIDGE_ID, FRIDGE_SECRET)

    # Configurar el sistema de logging
    setup_logging()

    # Iniciar hilos de infraestructura (comunicación, subida a API, actualización de DB)    
    serial_thread = threading.Thread(target=serial_reader_thread, args=(SERIAL_PORTS, BAUD_RATE, sensor_events_queue, stop_app_event), daemon=True)
    api_thread = threading.Thread(target=api_uploader_thread, args=(upload_queue, stop_app_event, auth_manager), daemon=True)
    offline_thread = threading.Thread(target=offline_sender_thread, args=(stop_app_event, auth_manager), daemon=True)
    db_updater_thread = threading.Thread(target=product_database_updater_thread, args=(PRODUCT_DATABASE_URL, LOCAL_PRODUCT_DB_PATH, DB_UPDATE_INTERVAL_SECONDS, stop_app_event, auth_manager), daemon=True)
    
    serial_thread.start()
    api_thread.start()
    offline_thread.start()
    db_updater_thread.start()

    os.makedirs(OFFLINE_QUEUE_PATH, exist_ok=True)

    # Iniciar hilos de cámaras (se quedan en standby, listos para capturar)
    image_cache = deque()
    for device in CAMERA_DEVICES:
        threading.Thread(target=camera_worker_thread, args=(device, image_cache, capture_event, stop_app_event, auth_manager), daemon=True).start()

    # Máquina de estados principal
    estado_captura = "IDLE"
    sensor_events_session = []
    session_time_offset_ns = 0
    global_time_offset_ns = None # Offset para eventos fuera de una sesión (status_report, etc.)
    last_weight_event_time = 0
    last_status_report_sent_time = 0

    logging.info("🧠 Cerebro Principal iniciado. Esperando eventos...")
    try:
        while True:
            # --- ESTADO: IDLE (Esperando apertura de puerta) ---
            if estado_captura == "IDLE":
                sensor_data = sensor_events_queue.get()
                
                is_door_open_event = sensor_data.get("event") == "door_change" and sensor_data.get("status") == "open"

                # --- SINCRONIZACIÓN DE TIEMPO ---
                # Al recibir el primer evento de todos, o en cada nueva apertura de puerta,
                # calculamos/refrescamos el offset de tiempo entre el PC y el ESP32.
                if (global_time_offset_ns is None or is_door_open_event) and 'timestamp' in sensor_data:
                    pc_time_now_ns = time.time_ns()
                    esp_time_us = sensor_data['timestamp']
                    calculated_offset = pc_time_now_ns - (esp_time_us * 1000)
                    
                    if global_time_offset_ns is None:
                        logging.info("✅ Offset de tiempo global inicial calculado.")
                    
                    global_time_offset_ns = calculated_offset
                    
                    # Si es una apertura de puerta, guardamos este offset de alta precisión para usarlo en toda la sesión.
                    if is_door_open_event:
                        session_time_offset_ns = calculated_offset

                # --- MANEJO DE EVENTOS EN MODO IDLE ---
                event_type = sensor_data.get("event")

                if is_door_open_event:
                    logging.info("🚪 Puerta Abierta! Iniciando sesión de captura...")
                    estado_captura = "CAPTURING"
                    sensor_events_session.append(sensor_data) # Guardamos el evento original para el procesador de sesión
                    last_weight_event_time = time.time()
                    capture_event.set() # <-- ORDENA A LAS CÁMARAS EMPEZAR A GUARDAR FOTOS
                
                elif event_type in ["status_report", "tare_button"]:
                    # --- Actualización para Kiosko (siempre que sea un reporte de estado) ---
                    if event_type == "status_report":                        
                        try:
                            status_for_kiosk = {
                                "temperature_c": sensor_data.get("temperature_c"),
                                "door_status": "open" if sensor_data.get("door_open") else "closed",
                                "total_weight_kg": sensor_data.get("weight_kg"),
                                "last_update_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            }
                            # Ruta corregida para escribir dentro del volumen compartido 'status'
                            status_dir = os.path.join(SCRIPT_DIR, "status")
                            status_file_path = os.path.join(status_dir, "fridge_status.json")
                            with open(status_file_path, 'w', encoding='utf-8') as f:
                                json.dump(status_for_kiosk, f)
                        except Exception as e:
                            logging.error(f"Error al actualizar el archivo de estado del kiosko: {e}")

                    # --- Lógica de envío al Backend (solo si es necesario) ---
                    should_send_to_backend = False
                    if event_type == "tare_button":
                        logging.info(f"⚖️ {sensor_data.get('message', 'Evento de Tara recibido')}. Poniendo en cola para envío.")
                        should_send_to_backend = True
                    elif event_type == "status_report":
                        current_time = time.time()
                        
                        if (current_time - last_status_report_sent_time) > STATUS_REPORT_SEND_INTERVAL_SECONDS:
                            logging.info(f"   -> Intervalo de {STATUS_REPORT_SEND_INTERVAL_SECONDS}s cumplido. Poniendo reporte en cola para envío al backend.")
                            should_send_to_backend = True
                            last_status_report_sent_time = current_time

                    if should_send_to_backend:
                        event_to_upload = sensor_data.copy()
                        if global_time_offset_ns is not None and 'timestamp' in event_to_upload:
                            esp_time_ns = event_to_upload['timestamp'] * 1000
                            pc_equivalent_time_ns = esp_time_ns + global_time_offset_ns
                            event_to_upload['timestamp'] = pc_equivalent_time_ns
                        
                        job = {
                            "id": str(uuid.uuid4()),
                            "type": event_type,
                            "data": [event_to_upload],
                            "attempts": 0
                        }
                        upload_queue.put(job)
            
            # --- ESTADO: CAPTURING (Sesión en progreso) ---
            elif estado_captura == "CAPTURING":
                door_closed = False
                timeout_reached = time.time() - last_weight_event_time > CAPTURE_TIMEOUT_SECONDS

                while not sensor_events_queue.empty():
                    sensor_data = sensor_events_queue.get()
                    sensor_events_session.append(sensor_data) # Guardamos CUALQUIER evento de la sesión
                    if sensor_data.get("event") == "weight_change":
                        last_weight_event_time = time.time()
                    elif sensor_data.get("event") == "door_change" and sensor_data.get("status") == "closed":
                        door_closed = True
                
                # La sesión termina si se cierra la puerta o si hay un timeout de inactividad.
                if door_closed or timeout_reached:
                    logging.info("🚪 Puerta Cerrada o Timeout. Finalizando captura y delegando al procesador...")
                    capture_event.clear() # <-- ORDENA A LAS CÁMARAS DEJAR DE GUARDAR FOTOS

                    # Prepara una copia de los datos de la sesión para el "cocinero".
                    session_data_copy = {
                        "images": list(image_cache),
                        "sensors": list(sensor_events_session),
                        "time_offset_ns": session_time_offset_ns # Pasamos el offset al procesador
                    }

                    # --- INICIA EL PROCESADOR EN UN NUEVO HILO ---
                    proc_thread = threading.Thread(target=session_processing_thread, args=(session_data_copy, upload_queue), daemon=True)
                    proc_thread.start()
                    
                    # El "mesero" vuelve a su trabajo inmediatamente
                    # Limpiamos las cachés para la siguiente sesión.
                    image_cache.clear()
                    sensor_events_session.clear()
                    estado_captura = "IDLE"
                    logging.info("🧠 Sistema en modo IDLE, listo para la siguiente apertura.")

            time.sleep(0.05)

    except KeyboardInterrupt:
        logging.info("Deteniendo todos los hilos...")
        stop_app_event.set()
