import os
import time
import threading
import requests
import json
import logging
import hashlib
from flask import Flask, render_template, jsonify, send_from_directory, abort, request

# ==============================================================================
# --- CONFIGURACIÓN DEL KIOSKO ---
# ==============================================================================
# Leer la configuración desde las variables de entorno
FRIDGE_ID = os.getenv("FRIDGE_ID", "NEVERA-001-SANTAROSA")
BASE_BACKEND_URL = os.getenv("BASE_BACKEND_URL")
FRIDGE_SECRET = os.getenv("FRIDGE_SECRET")

# ### ¡MEJORA! ### Validar configuración crítica al inicio
if not BASE_BACKEND_URL or not FRIDGE_SECRET:
    logging.critical("❌ FALTAN VARIABLES DE ENTORNO CRÍTICAS (BASE_BACKEND_URL o FRIDGE_SECRET). El servicio no puede funcionar.")
    # En un escenario real, podríamos querer que el contenedor se detenga si falta la configuración.
    # Para este ejemplo, solo lo logueamos como crítico.

# Construir URLs
KIOSK_BACKEND_URL = f"{BASE_BACKEND_URL}/api/playlist/{FRIDGE_ID}" if BASE_BACKEND_URL else None
AUTH_URL = f"{BASE_BACKEND_URL}/api/auth/login" if BASE_BACKEND_URL else None

# Directorios y archivos locales
DATA_DIR = "/app/data"
CACHE_DIR = os.path.join(DATA_DIR, "media_cache")
PLAYLIST_FILE = os.path.join(DATA_DIR, "playlist.json")
STATUS_FILE = "/app/status/fridge_status.json"

# Intervalo de sincronización
SYNC_INTERVAL_SECONDS = 1200  # 20 minutos

# Configuración de logging estándar (para módulos fuera de Flask)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [Kiosk] %(message)s')

# ==============================================================================
# --- GESTOR DE AUTENTICACIÓN JWT ---
# ==============================================================================

class AuthManager:
    """Gestiona la obtención y el refresco de tokens JWT de forma segura para hilos."""
    def __init__(self, auth_url, fridge_id, fridge_secret):
        self._auth_url = auth_url
        self._fridge_id = fridge_id
        self._fridge_secret = fridge_secret
        self._token = None
        self._token_expires_at = 0
        self._lock = threading.Lock()

    def _login(self):
        """Método privado para solicitar un nuevo token al backend."""
        if not self._auth_url:
            logging.error("❌ [Auth] No se puede solicitar token: AUTH_URL no está configurado.")
            return

        logging.info("🔑 [Auth] Solicitando nuevo token de autenticación JWT...")
        try:
            credentials = {"fridgeId": self._fridge_id, "secret": self._fridge_secret}
            response = requests.post(self._auth_url, json=credentials, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._token = data.get("access_token")
            # Usar un default de 3600s (1 hora) si 'expires_in' no viene
            expires_in = data.get("expires_in", 3600) 
            # Guardar con un margen de seguridad de 60 segundos para evitar usar un token a punto de expirar
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
            is_expired = time.time() >= self._token_expires_at
            if not self._token or is_expired:
                self._login()
            return self._token

# ==============================================================================
# --- HILO 3: SINCRONIZADOR Y CACHE ---
# ==============================================================================

def sync_with_admin_backend(stop_event, auth_manager):
    """
    Hilo periódico que descarga la playlist, los medios y limpia la caché de archivos obsoletos.
    """
    while not stop_event.is_set():
        if not KIOSK_BACKEND_URL:
            logging.warning("La variable BASE_BACKEND_URL no está definida. Saltando ciclo de sincronización.")
            if stop_event.wait(SYNC_INTERVAL_SECONDS): break
            continue

        logging.info(f"Iniciando sincronización. Conectando a: {KIOSK_BACKEND_URL}")

        try:
            # 1. Obtener token de autenticación
            token = auth_manager.get_token()
            if not token:
                logging.error("No se pudo obtener el token de autenticación. Reintentando en 60 segundos.")
                if stop_event.wait(60): break
                continue

            # 2. Obtener la playlist desde el backend
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(KIOSK_BACKEND_URL, headers=headers, timeout=15)
            response.raise_for_status()
            playlist_data = response.json()
            logging.info(f"✅ Playlist recibida con {len(playlist_data.get('media', []))} elemento(s).")
            
            os.makedirs(CACHE_DIR, exist_ok=True)
            
            # 3. Procesar medios, descargar nuevos y preparar la limpieza
            required_media_files = set()
            processed_media_list = []

            for item in playlist_data.get("media", []):
                media_url = item.get("url")
                if not media_url:
                    continue
                
                try:
                    # ### ¡MEJORA! ### Usar un hash de la URL como nombre de archivo para evitar colisiones.
                    # Se mantiene la extensión original para compatibilidad con el navegador.
                    file_ext = os.path.splitext(media_url.split("?")[0])[-1] # Obtener extensión antes de query params
                    hashed_name = hashlib.sha256(media_url.encode('utf-8')).hexdigest()
                    local_filename = f"{hashed_name}{file_ext}"
                    required_media_files.add(local_filename)
                    
                    local_filepath = os.path.join(CACHE_DIR, local_filename)

                    # Descargar solo si no existe
                    if not os.path.exists(local_filepath):
                        logging.info(f"  -> 📥 [Cache] Descargando: {media_url}")
                        media_response = requests.get(media_url, stream=True, timeout=60) # Timeout más largo para archivos grandes
                        media_response.raise_for_status()
                        with open(local_filepath, 'wb') as f:
                            for chunk in media_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        logging.info(f"     ✅ [Cache] Guardado como: {local_filename}")
                    
                    # Añadir la ruta local al item de la playlist para el frontend
                    item["local_path"] = f"/media/{local_filename}"
                    processed_media_list.append(item)

                except requests.exceptions.RequestException as e:
                    logging.error(f"  -> ❌ [Cache] Fallo al descargar {media_url}: {e}. Se omitirá este medio.")
                except IOError as e:
                    logging.error(f"  -> ❌ [Cache] Fallo al guardar en disco {local_filename}: {e}. Se omitirá este medio.")

            # 4. Actualizar la lista de medios en la playlist con solo los que se procesaron bien
            playlist_data["media"] = processed_media_list

            # 5. Guardar la nueva playlist localmente
            with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=2)
            logging.info(f"✅ Playlist local actualizada en {PLAYLIST_FILE}")

            # ### ¡MEJORA! ### Limpieza de caché
            logging.info("🧹 [Cache] Iniciando limpieza de archivos obsoletos...")
            for filename in os.listdir(CACHE_DIR):
                if filename not in required_media_files:
                    try:
                        file_to_delete = os.path.join(CACHE_DIR, filename)
                        os.remove(file_to_delete)
                        logging.info(f"  -> 🗑️ [Cache] Eliminado archivo obsoleto: {filename}")
                    except OSError as e:
                        logging.error(f"  -> ❌ [Cache] Error al eliminar {filename}: {e}")

        except requests.exceptions.RequestException as e:
            logging.error(f"No se pudo conectar con el backend de administración: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error al procesar la playlist recibida del backend: {e}")

        # Esperar para la siguiente sincronización
        if stop_event.wait(SYNC_INTERVAL_SECONDS): break

# ==============================================================================
# --- SERVIDOR WEB FLASK ---
# ==============================================================================

app = Flask(__name__)

# ### ¡MEJORA! ### Configurar el logger de Flask para integrarse con Gunicorn
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Desactivar logs de acceso de Werkzeug para no saturar la consola
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route('/')
def index():
    """Sirve la página principal del kiosko."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """API para que el frontend obtenga el estado de la nevera."""
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        app.logger.warning(f"Solicitud de estado, pero '{STATUS_FILE}' no encontrado.")
        return jsonify({"error": "Archivo de estado no encontrado."}), 404
    except (json.JSONDecodeError, IOError) as e:
        app.logger.error(f"Error al leer el archivo de estado '{STATUS_FILE}': {e}")
        return jsonify({"error": "No se pudo leer el archivo de estado."}), 500

@app.route('/api/playlist')
def get_playlist():
    """API para que el frontend obtenga la lista de reproducción."""
    try:
        with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"media": [], "error": "Playlist no encontrada. Esperando sincronización."}), 404
    except (json.JSONDecodeError, IOError) as e:
        app.logger.error(f"Error al leer el archivo de playlist '{PLAYLIST_FILE}': {e}")
        return jsonify({"error": "No se pudo leer el archivo de playlist."}), 500

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Sirve los archivos de medios cacheados."""
    return send_from_directory(CACHE_DIR, filename)


# ==============================================================================
# --- INICIALIZACIÓN ---
# ==============================================================================

# Crear directorios necesarios al inicio
os.makedirs(CACHE_DIR, exist_ok=True)

# Crear una única instancia del gestor de autenticación
auth_manager = AuthManager(AUTH_URL, FRIDGE_ID, FRIDGE_SECRET)

# Iniciar el hilo de sincronización en segundo plano
stop_sync_event = threading.Event()
sync_thread = threading.Thread(target=sync_with_admin_backend, args=(stop_sync_event, auth_manager), daemon=True)
sync_thread.start()

# ### ¡MEJORA! ### Bloque para permitir la ejecución local para pruebas
if __name__ == '__main__':
    logging.info(f"🚀 Iniciando servidor Flask en modo de desarrollo en el puerto 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)