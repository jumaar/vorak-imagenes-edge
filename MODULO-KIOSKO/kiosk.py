import os
import time
import threading
import requests
import subprocess
import json
import logging
from flask import Flask, render_template, jsonify, send_from_directory, abort, request

# ==============================================================================
# --- CONFIGURACIÓN DEL KIOSKO ---
# ==============================================================================
# Las variables de entorno son inyectadas por Docker Compose.

# Leer la configuración desde las variables de entorno
# Se usa un valor por defecto por si la variable no está definida.
FRIDGE_ID = os.getenv("FRIDGE_ID", "NEVERA-001-SANTAROSA")
BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL")

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

# Construir la URL final usando la plantilla y el ID de la nevera
KIOSK_BACKEND_URL = f"{BASE_BACKEND_URL}/api/playlist/{FRIDGE_ID}"
AUTH_URL = f"{BASE_BACKEND_URL}/api/auth/login" # Nuevo endpoint para obtener el token JWT

# Archivos y carpetas locales dentro del contenedor
DATA_DIR = "/app/data" # Directorio persistente para la caché y la playlist
CACHE_DIR = os.path.join(DATA_DIR, "media_cache")
PLAYLIST_FILE = os.path.join(DATA_DIR, "playlist.json")
STATUS_FILE = "/app/status/fridge_status.json" # Ruta al volumen compartido con la nevera

# Intervalo para sincronizar con el backend (en segundos)
SYNC_INTERVAL_SECONDS = 1200  # 12 minutos

# Configuración del servidor Flask
FLASK_PORT = 5000

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [Kiosk] %(message)s')

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
        logging.info("🔑 [Auth] Solicitando nuevo token de autenticación JWT...")
        try:
            credentials = {"fridgeId": self._fridge_id, "secret": self._fridge_secret}
            response = requests.post(self._auth_url, json=credentials, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._token = data.get("access_token")
            expires_in = data.get("expires_in", 3600) 
            self._token_expires_at = time.time() + expires_in - 60
            
            if self._token:
                logging.info("✅ [Auth] Nuevo token JWT obtenido con éxito.")
            else:
                logging.error("❌ [Auth] Fallo en la autenticación: El backend no devolvió un token.")

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ [Auth] Error de red al intentar obtener el token JWT: {e}")
            self._token = None

    def get_token(self):
        """Devuelve un token JWT válido, solicitando uno nuevo si es necesario."""
        with self._lock:
            if not self._token or time.time() >= self._token_expires_at:
                self._login()
            return self._token

# ==============================================================================
# --- HILO 3: SINCRONIZADOR Y CACHE (EL "MENSAJERO") ---
# ==============================================================================

def sync_with_admin_backend(stop_event, auth_manager):
    """
    Hilo que se ejecuta periódicamente para descargar la playlist y los medios
    desde el backend de administración.
    """
    while not stop_event.is_set():
        # --- VERIFICACIÓN DE URL BASE ---
        if not BASE_BACKEND_URL:
            logging.warning("La variable BASE_BACKEND_URL no está definida. El kiosko no puede sincronizar la playlist. Verifique el archivo .env.")
            stop_event.wait(SYNC_INTERVAL_SECONDS) # Esperar el intervalo completo antes de volver a verificar.
            continue
        logging.info("Iniciando sincronización de playlist con el backend...")
        os.makedirs(CACHE_DIR, exist_ok=True)

        try:
            token = auth_manager.get_token()
            if not token:
                logging.error("No se pudo obtener el token de autenticación. Se saltará este ciclo de sincronización.")
                stop_event.wait(60) # Reintentar en 60 segundos si falla la autenticación
                continue

            # 1. Obtener la playlist desde el backend
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(KIOSK_BACKEND_URL, headers=headers, timeout=15)
            response.raise_for_status()
            playlist_data = response.json()
            logging.info("Playlist recibida del backend con éxito.")

            # 2. Procesar y descargar los medios
            for item in playlist_data.get("media", []):
                media_url = item.get("url")
                if not media_url:
                    continue
                
                # Generar un nombre de archivo local a partir de la URL
                local_filename = os.path.basename(media_url)
                local_filepath = os.path.join(CACHE_DIR, local_filename)
                item["local_path"] = f"/media/{local_filename}" # Ruta que usará el frontend

                # Descargar el archivo solo si no existe localmente
                if not os.path.exists(local_filepath):
                    logging.info(f"Descargando nuevo medio: {media_url}")
                    media_response = requests.get(media_url, stream=True, timeout=30)
                    media_response.raise_for_status()
                    with open(local_filepath, 'wb') as f:
                        for chunk in media_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    logging.info(f"Medio guardado en: {local_filepath}")

            # 3. Guardar la playlist procesada localmente
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2)
            logging.info(f"Playlist local actualizada en {PLAYLIST_FILE}")

        except requests.exceptions.RequestException as e:
            logging.error(f"No se pudo conectar con el backend de administración: {e}")
            logging.warning("El kiosko continuará usando la última playlist cacheada si existe.")
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error al procesar la playlist recibida del backend: {e}")

        # Esperar para la próxima sincronización
        stop_event.wait(SYNC_INTERVAL_SECONDS)

# ==============================================================================
# --- HILO 1: SERVIDOR WEB FLASK (EL "PROYECTOR") ---
# ==============================================================================

 # Rutas absolutas para las carpetas de Flask para evitar problemas con el directorio de trabajo
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# Desactivar los logs de acceso de Werkzeug (el servidor que usa Flask).
# Esto evita que la consola se llene con cada petición GET que el frontend
# hace a /api/status, manteniendo el log limpio para mensajes importantes.
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

@app.route('/')
def index():
    """Sirve la página principal del kiosko."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """
    API interna para que el frontend obtenga el estado actual de la nevera.
    Lee los datos del archivo que 'app.py' actualiza (nuestra "variable compartida").
    """
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        return jsonify(status_data)
    except FileNotFoundError:
        return jsonify({"error": "Archivo de estado no encontrado. Esperando la primera actualización de app.py."}), 404
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error al leer el archivo de estado: {e}")
        return jsonify({"error": "No se pudo leer el archivo de estado."}), 500

@app.route('/api/playlist')
def get_playlist():
    """
    API interna para que el frontend obtenga la lista de reproducción.
    """
    try:
        with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
            playlist_data = json.load(f)
        return jsonify(playlist_data)
    except FileNotFoundError:
        # Fallback: si no hay playlist, enviar una vacía para que el frontend no falle.
        return jsonify({"media": [], "error": "Playlist no encontrada. Esperando sincronización con el backend."}), 404
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error al leer el archivo de playlist: {e}")
        return jsonify({"error": "No se pudo leer el archivo de playlist."}), 500

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Sirve los archivos de medios cacheados (imágenes, videos)."""
    return send_from_directory(CACHE_DIR, filename)

# --- ¡NUEVO! FUNCIÓN TRABAJADORA PARA EL DESPLIEGUE ---
def _run_deployment_script():
    """
    Ejecuta el script de redespliegue en segundo plano, espera a que termine
    y registra el resultado. Esto se ejecuta en un hilo separado para no
    bloquear la respuesta del webhook.
    """
    logging.info("[Deploy] Iniciando ejecución de redeploy.sh en segundo plano...")
    try:
        # Usamos subprocess.run para esperar a que el script termine y capturar su salida.
        result = subprocess.run(
            ["/app/redeploy.sh"],
            capture_output=True,
            text=True,
            check=False  # No lanzar excepción si falla, lo manejaremos manualmente.
        )

        # Registrar la salida estándar del script para tener el detalle completo.
        if result.stdout:
            logging.info(f"[Deploy] Salida del script:\n{result.stdout.strip()}")

        # Si hubo un error, registrarlo también.
        if result.stderr:
            logging.error(f"[Deploy] Errores del script:\n{result.stderr.strip()}")

        if result.returncode == 0:
            logging.info("✅ [Deploy] El script de redespliegue finalizó con ÉXITO.")
        else:
            logging.error(f"❌ [Deploy] El script de redespliegue FALLÓ con código de salida {result.returncode}.")
    except Exception as e:
        logging.critical(f"CRÍTICO: No se pudo ejecutar el hilo de despliegue: {e}")

# --- ¡NUEVO! ENDPOINT PARA EL WEBHOOK DE REDESPLIEGUE ---
@app.route('/update/<token>', methods=['POST'])
def handle_webhook(token):
    """
    Escucha las llamadas del webhook de GitHub Actions para redesplegar la aplicación.
    """
    # 1. Validar que el token de la URL sea el correcto.
    #    Se reutiliza el secreto de la nevera para mayor simplicidad y seguridad.
    if not FRIDGE_SECRET or token != FRIDGE_SECRET:
        logging.warning(f"Intento de acceso no autorizado al webhook con token: {token}")
        abort(401) # Unauthorized

    # 2. Validar que la petición venga de GitHub (seguridad extra)
    user_agent = request.headers.get('User-Agent', '')
    if not user_agent.startswith('GitHub-Hookshot/'):
        logging.warning(f"Petición de webhook rechazada de User-Agent no válido: {user_agent}")
        abort(403) # Forbidden

    # 3. Ejecutar el script de redespliegue en segundo plano
    logging.info("Webhook autorizado recibido. Ejecutando script de redespliegue...")
    try:
        # Creamos y lanzamos el hilo que hará el trabajo pesado.
        deployment_thread = threading.Thread(target=_run_deployment_script, daemon=True)
        deployment_thread.start()
        return "Proceso de redespliegue iniciado.", 202 # Accepted
    except Exception as e:
        logging.error(f"Error al ejecutar el script de redespliegue: {e}")
        return "Fallo al iniciar el proceso de redespliegue.", 500


# ==============================================================================
# --- PUNTO DE ENTRADA ---
# ==============================================================================

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Crear una única instancia del gestor de autenticación
    auth_manager = AuthManager(AUTH_URL, FRIDGE_ID, FRIDGE_SECRET)

    stop_sync_event = threading.Event()
    sync_thread = threading.Thread(target=sync_with_admin_backend, args=(stop_sync_event, auth_manager), daemon=True)
    sync_thread.start()
    
    logging.info(f"Iniciando servidor del kiosko en http://localhost:{FLASK_PORT}")
    
    try:
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    except KeyboardInterrupt:
        logging.info("Deteniendo el servidor del kiosko...")
    finally:
        stop_sync_event.set()
        logging.info("Servidor del kiosko detenido.")