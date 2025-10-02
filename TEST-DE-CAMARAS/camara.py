import cv2
import os
import threading
import time
from collections import deque

# Lee las cámaras desde la variable de entorno, igual que app.py
CAMERA_DEVICES = [cam.strip() for cam in os.getenv("CAMERA_DEVICES", "").split(',') if cam.strip()]
FRAME_CACHE = {}
STOP_EVENT = threading.Event()

def camera_reader_thread(camera_device):
    """
    Hilo dedicado a leer fotogramas de una cámara y ponerlos en una caché.
    Incluye la lógica de reconexión de app.py.
    """
    print(f"[INFO] Iniciando hilo para la cámara: {camera_device}")
    cap = None
    
    while not STOP_EVENT.is_set():
        if cap is None or not cap.isOpened():
            print(f"[WARN] {camera_device}: Intentando abrir/reabrir cámara...")
            cap = cv2.VideoCapture(camera_device, cv2.CAP_V4L2)
            if not cap.isOpened():
                print(f"[ERROR] {camera_device}: No se pudo abrir. Reintentando en 5 segundos.")
                time.sleep(5)
                continue
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                print(f"[INFO] {camera_device}: Cámara abierta con resolución 1280x720.")

        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] {camera_device}: Falló la lectura del fotograma. Intentando reabrir.")
            if cap.isOpened():
                cap.release()
            cap = None
            time.sleep(1)
            continue

        # Almacena el último fotograma en la caché global
        FRAME_CACHE[camera_device] = frame
        
        # Pequeña pausa para no consumir 100% de CPU
        time.sleep(0.01)

    if cap is not None and cap.isOpened():
        cap.release()
    print(f"[INFO] Hilo para {camera_device} detenido.")

if __name__ == "__main__":
    if not CAMERA_DEVICES:
        print("\n[ERROR] No se especificaron cámaras en la variable de entorno CAMERA_DEVICES.")
        print("Asegúrate de lanzar el contenedor con el flag --env, por ejemplo:")
        print('  --env CAMERA_DEVICES="/dev/video0,/dev/video1"\n')
        exit(1)

    print("Iniciando hilos de lectura de cámaras...")
    for device in CAMERA_DEVICES:
        # Inicializa la caché para esta cámara con un valor nulo
        FRAME_CACHE[device] = None
        thread = threading.Thread(target=camera_reader_thread, args=(device,), daemon=True)
        thread.start()

    print("\n======================================================")
    print(" VISOR DE CÁMARAS EN VIVO")
    print(" - Se abrirá una ventana por cada cámara configurada.")
    print(" - Presiona la tecla 'q' en cualquiera de las ventanas para salir.")
    print("======================================================\n")

    try:
        while True:
            # Itera sobre las cámaras para mostrar su último fotograma
            for device, frame in FRAME_CACHE.items():
                if frame is not None:
                    # Redimensionar para visualización si es necesario
                    display_frame = cv2.resize(frame, (640, 360))
                    cv2.imshow(f"Camara Test - {device}", display_frame)

            # Espera 1ms por una tecla. Si es 'q', rompe el bucle.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Tecla 'q' presionada. Cerrando...")
                break
    
    finally:
        # Señal para que los hilos se detengan y cierre de ventanas
        STOP_EVENT.set()
        time.sleep(1) # Dar tiempo a los hilos para que terminen
        cv2.destroyAllWindows()
        print("Aplicación de test finalizada.")
