# spotify_controller.py

import os
import time
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# --- Configuración de Spotify ---
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-modify-playback-state user-read-playback-state"
))

# --- Variables de control ---
ultimo_estado = None
ultimo_cambio = 0
COOLDOWN_SEGUNDOS = 45 # Aumentamos un poco para no cambiar tan rápido

GENERO_PLAYLISTS = {
    "reggaeton": "spotify:playlist:37i9dQZF1DX10zKzsJ2jva", # Perreo
    "edm": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",       # Dance
    "chill": "spotify:playlist:37i9dQZF1DX4sWSpwq3LiO",      # Chill
    "salsa": "spotify:playlist:37i9dQZF1DX1tW4VlEfDSS",
    "rock": "spotify:playlist:37i9dQZF1DWXRqgorJj26U",
    "kpop": "spotify:playlist:37i9dQZF1DX9tPFwDMOaN1",
    "lofi": "spotify:playlist:37i9dQZF1DWWQRwui02Gu5", # lofi beats
    "disco": "spotify:playlist:37i9dQZF1DX0BxHamIEkKV", # Disco Fever
    "techno": "spotify:playlist:37i9dQZF1DWVFeEut75IAL",
    "meditacion": "spotify:playlist:37i9dQZF1DWZqd5JICZI0u"
}

def convertir_link_a_uri(link):
    if "track/" in link:
        return "spotify:track:" + link.split("track/")[1].split("?")[0]
    elif "playlist/" in link:
        return "spotify:playlist:" + link.split("playlist/")[1].split("?")[0]
    elif "album/" in link:
        return "spotify:album:" + link.split("album/")[1].split("?")[0]
    return None

# --- FUNCIÓN MODIFICADA ---
def actualizar_musica_spotify(analisis, modo_usuario):
    global ultimo_estado, ultimo_cambio

    if modo_usuario:
        print("🧑‍🎤 Modo usuario activo. Spotify no se controla automáticamente.")
        return

    if not analisis or not analisis.get("hay_personas"):
        if ultimo_estado != "pausa":
            print("🎧 No hay personas, pausando música en Spotify.")
            try:
                sp.pause_playback()
                ultimo_estado = "pausa"
            except Exception as e:
                print(f"Error al pausar Spotify: {e}")
        return

    genero = analisis.get("genero_recomendado", "chill").lower().strip()
    playlist = GENERO_PLAYLISTS.get(genero)

    if not playlist:
        print(f"🎵 Género '{genero}' no reconocido, usando 'chill' por defecto.")
        playlist = GENERO_PLAYLISTS["chill"]
        genero = "chill"

    ahora = time.time()

    if genero == ultimo_estado:
        # Si estamos en el mismo género, nos aseguramos de que la música esté sonando
        try:
            current_playback = sp.current_playback()
            if not current_playback or not current_playback.get('is_playing'):
                 print(f"▶️ Reactivando reproducción para género '{genero}'.")
                 sp.start_playback(context_uri=playlist)
        except Exception as e:
            print(f"Error al verificar reproducción de Spotify: {e}")
        return

    if ahora - ultimo_cambio < COOLDOWN_SEGUNDOS:
        print(f"⏳ Cooldown de Spotify activo. Esperando para cambiar de género.")
        return

    print(f"🎶 Cambiando música en Spotify al género: {genero}")
    try:
        sp.start_playback(context_uri=playlist)
        ultimo_estado = genero
        ultimo_cambio = ahora
    except Exception as e:
        print(f"Error al iniciar reproducción en Spotify: {e}")