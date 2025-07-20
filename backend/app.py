# ------------------- imports -------------------
from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2, base64, threading, time, random, os
from PIL import Image
from dj_ai2 import analizar_ambiente, generar_voz_dj

# ---- Spotipy ----------------------------------
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

# ----------------- Flask / Socket.IO ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_super_segura'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------ Spotify setup --------------------
PLAYLIST_ID = "37i9dQZF1DX9C8KzGEUKV4"

PLAYLIST_URI = f"spotify:playlist:{PLAYLIST_ID}"

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),   # p. ej.  http://localhost:8888/callback
    scope=("user-modify-playback-state user-read-playback-state "
           "playlist-read-private playlist-read-collaborative")
))

def cargar_tracks(pid: str, market="PE") -> list[str]:
    """Devuelve todas las canciones de la playlist para el market dado."""
    try:
        res = sp.playlist_items(pid, market=market, limit=100,
                                fields="items.track.uri,next",
                                additional_types=["track"])
        uris = [i["track"]["uri"] for i in res["items"] if i.get("track")]
        while res.get("next"):
            res = sp.next(res)
            uris.extend([i["track"]["uri"] for i in res["items"] if i.get("track")])
        return uris
    except SpotifyException as e:
        print(f"⚠️  Error al cargar la playlist ({e.http_status}): {e.msg or e.reason}")
        return []

tracks = cargar_tracks(PLAYLIST_ID) or [PLAYLIST_URI]
print(f"✅ Se cargaron {len(tracks)} pistas.") if len(tracks) > 1 else \
      print("⚠️  Solo se pudo acceder a la URI de la playlist (no a sus pistas).")

third = max(1, len(tracks)//3)
LOW_ENERGY, MID_ENERGY, HIGH_ENERGY = tracks[:third], tracks[third:2*third], tracks[2*third:] or tracks

# ---------- parámetros ajustables --------------
COOLDOWN          = 15    # segundos mínimos entre saltos normales
FRECUENCIA_CAMBIO = 1     # 1=cada análisis, 2=c/2, 3=c/3…
# -----------------------------------------------

# ------------- estado global -------------------
cap = analysis_timer = None
analysis_lock = threading.Lock()
current_analysis = current_dj_phrase = None
current_voice   = "bad_bunny"
LAST_TRACK_URI  = None
LAST_CHANGE_TS  = 0
ANALYSIS_COUNT  = 0
# ------------------------------------------------

# ============ Spotify helper ===================
def reproducir_cancion(nivel: int, force=False):
    global LAST_TRACK_URI, LAST_CHANGE_TS
    if not tracks: return

    ahora = time.time()
    if not force and (ahora - LAST_CHANGE_TS) < COOLDOWN:
        return

    pool = LOW_ENERGY if nivel <= 4 else MID_ENERGY if nivel <= 7 else HIGH_ENERGY
    if not pool: return

    # Si solo tenemos la playlist, saltamos a posición aleatoria
    if pool == [PLAYLIST_URI]:
        try:
            sp.start_playback(context_uri=PLAYLIST_URI,
                              offset={"position": random.randint(0, 99)})
            LAST_TRACK_URI, LAST_CHANGE_TS = PLAYLIST_URI, ahora
            print("🎵 Spotify → salto aleatorio dentro de la playlist")
        except SpotifyException as e:
            print("Spotify error:", e); return
        return

    track = random.choice(pool)
    if len(pool) > 1:
        while track == LAST_TRACK_URI:
            track = random.choice(pool)

    try:
        sp.start_playback(uris=[track])
        LAST_TRACK_URI, LAST_CHANGE_TS = track, ahora
        print("🎵 Spotify →", track)
    except SpotifyException as e:
        print("Spotify error:", e)
# ------------------------------------------------

# ============ Visión + IA =======================
def capture_and_analyze():
    global cap, analysis_timer, current_analysis, current_dj_phrase, ANALYSIS_COUNT
    if cap is None or not cap.isOpened(): return
    ret, frame = cap.read()
    if not ret: return

    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    analisis = analizar_ambiente(pil)

    if analisis:
        frase, audio_bytes = generar_voz_dj(analisis, current_voice)
        nivel = analisis.get("nivel_energia", 5)

        ANALYSIS_COUNT += 1
        force = (ANALYSIS_COUNT % FRECUENCIA_CAMBIO) == 0
        reproducir_cancion(nivel, force=force)

        with analysis_lock:
            current_analysis, current_dj_phrase = analisis, frase

        socketio.emit("analysis_update", {
            "analysis": analisis,
            "dj_phrase": frase,
            "audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else None
        })

        intervalo = 20 if nivel <= 4 else 40 if nivel <= 7 else 60
    else:
        intervalo = 40

    analysis_timer = threading.Timer(intervalo, capture_and_analyze)
    analysis_timer.daemon = True
    analysis_timer.start()
# ================================================

# ------------------ Socket.IO -------------------
@socketio.on("start_camera")
def start_camera():
    global cap, analysis_timer, ANALYSIS_COUNT
    ANALYSIS_COUNT = 0
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        emit("error", {"message": "No se puede abrir la cámara"}); return
    emit("camera_started")
    if analysis_timer: analysis_timer.cancel()
    capture_and_analyze()

@socketio.on("stop_camera")
def stop_camera():
    global cap, analysis_timer
    if analysis_timer: analysis_timer.cancel()
    if cap: cap.release(); cap = None
    emit("camera_stopped")

@socketio.on("get_frame")
def get_frame():
    if cap and cap.isOpened():
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode(".jpg", frame)
            emit("frame_update", {"frame": base64.b64encode(buf).decode()})

@socketio.on("change_voice_model")
def change_voice(data):
    global current_voice
    if data.get("voice_model"):
        current_voice = data["voice_model"]
        print("→ voz DJ cambiada a:", current_voice)

@socketio.on("connect")
def on_connect():
    print("✅ Cliente conectado.")
    if current_analysis and current_dj_phrase:
        emit("analysis_update", {
            "analysis": current_analysis,
            "dj_phrase": current_dj_phrase,
            "audio_base64": None
        })

# ---------------- run ----------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
