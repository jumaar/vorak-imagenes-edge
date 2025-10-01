document.addEventListener('DOMContentLoaded', () => {
    const mediaContainer = document.getElementById('media-container');
    
    // Elementos del recuadro de estado
    const tempSpan = document.getElementById('status-temp');
    const doorSpan = document.getElementById('status-door');
    const weightSpan = document.getElementById('status-weight');
    const updateSpan = document.getElementById('status-update');

    // --- CONFIGURACIÓN ---
    const STATUS_UPDATE_INTERVAL = 5000; // 5 segundos
    const PLAYLIST_UPDATE_INTERVAL = 60000; // 1 minuto
    const FALLBACK_IMAGE = 'https://media.istockphoto.com/id/1497211516/es/foto/primer-plano-del-carnicero-cortando-un-bloque-de-por-con-una-sierra-el%C3%A9ctrica.webp?a=1&b=1&s=612x612&w=0&k=20&c=Cdd6paD1Q9qDvErl83WaGmNLAMphLhwz0FNHjZVeEzg='; // Ruta a una imagen por defecto

    let playlist = [];
    let currentMediaIndex = 0;

    // --- LÓGICA DE LA PLAYLIST ---

    /**
     * Muestra el siguiente medio en la playlist.
     */
    function playNextMedia() {
        if (playlist.length === 0) {
            showFallback();
            // Reintentar cargar la playlist después de un tiempo si está vacía
            setTimeout(fetchPlaylist, 10000); 
            return;
        }

        // Asegurarse de que el índice sea válido
        currentMediaIndex = (currentMediaIndex % playlist.length);
        const mediaItem = playlist[currentMediaIndex];

        // Limpiar el contenedor
        mediaContainer.innerHTML = '';

        let mediaElement;
        const mediaType = mediaItem.type || (mediaItem.local_path.endsWith('.mp4') ? 'video' : 'image');

        if (mediaType === 'video') {
            mediaElement = document.createElement('video');
            mediaElement.src = mediaItem.local_path;
            mediaElement.autoplay = true;
            mediaElement.muted = true; // El autoplay en muchos navegadores requiere que el video esté silenciado
            mediaElement.loop = false; // No queremos que se repita, pasamos al siguiente
            // Cuando el video termine, pasa al siguiente medio
            mediaElement.onended = playNextMedia;
        } else { // 'image'
            mediaElement = document.createElement('img');
            mediaElement.src = mediaItem.local_path;
            // Para las imágenes, usamos la duración definida en la playlist
            const duration = (mediaItem.duration_seconds || 10) * 1000;
            setTimeout(playNextMedia, duration);
        }
        
        mediaElement.onerror = () => {
            console.error(`Error al cargar el medio: ${mediaItem.local_path}. Mostrando fallback.`);
            showFallback();
            setTimeout(playNextMedia, 5000); // Intenta el siguiente medio después de 5s
        };

        mediaContainer.appendChild(mediaElement);
        currentMediaIndex++;
    }

    /**
     * Muestra una imagen por defecto si la playlist falla o está vacía.
     */
    function showFallback() {
        mediaContainer.innerHTML = `<img src="${FALLBACK_IMAGE}" alt="Publicidad no disponible">`;
    }

    /**
     * Obtiene la playlist desde la API del backend (kiosk.py).
     */
    async function fetchPlaylist() {
        console.log('Fetching playlist...');
        try {
            const response = await fetch('/api/playlist');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data && data.media && data.media.length > 0) {
                // Si la playlist ha cambiado, reiniciamos la reproducción desde el principio
                if (JSON.stringify(playlist) !== JSON.stringify(data.media)) {
                    console.log('Playlist actualizada. Reiniciando reproducción.');
                    playlist = data.media;
                    currentMediaIndex = 0;
                    playNextMedia(); // Inicia inmediatamente con la nueva playlist
                }
            } else {
                playlist = [];
                showFallback();
            }
        } catch (error) {
            console.error('Error al obtener la playlist:', error);
            playlist = [];
            showFallback();
        }
    }

    // --- LÓGICA DEL ESTADO DE LA NEVERA ---

    /**
     * Obtiene el estado de la nevera desde la API y actualiza la UI.
     */
    async function fetchStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const status = await response.json();

            tempSpan.textContent = status.temperature_c !== null ? status.temperature_c.toFixed(1) : '--.-';
            doorSpan.textContent = status.door_status ? status.door_status.charAt(0).toUpperCase() + status.door_status.slice(1) : '------';
            weightSpan.textContent = status.total_weight_kg !== null ? status.total_weight_kg.toFixed(2) : '--.--';
            
            if (status.last_update_utc) {
                const updateDate = new Date(status.last_update_utc);
                updateSpan.textContent = updateDate.toLocaleTimeString('es-ES');
            }

        } catch (error) {
            console.error('Error al obtener el estado de la nevera:', error);
        }
    }

    // --- INICIALIZACIÓN ---
    fetchPlaylist();
    fetchStatus();
    setInterval(fetchPlaylist, PLAYLIST_UPDATE_INTERVAL);
    setInterval(fetchStatus, STATUS_UPDATE_INTERVAL);
});