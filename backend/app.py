from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import base64
import threading
import time
import json
from dj_ai2 import analizar_ambiente, generar_voz_dj
from PIL import Image
import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

cap = None
analysis_timer = None
current_analysis = None
current_dj_phrase = None

def capture_and_analyze():
    global cap, analysis_timer, current_analysis, current_dj_phrase
    
    if cap is None or not cap.isOpened():
        return
    
    ret, frame = cap.read()
    if not ret:
        return
    
    # Convertir frame para análisis
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    
    # Realizar análisis
    analisis = analizar_ambiente(pil)
    
    if analisis:
        current_analysis = analisis
        current_dj_phrase = generar_voz_dj(analisis)
        
        # Enviar datos a todos los clientes conectados
        socketio.emit('analysis_update', {
            'analysis': current_analysis,
            'dj_phrase': current_dj_phrase
        })
        
        # Determinar intervalo basado en energía
        nivel = analisis.get("nivel_energia", 5)
        if nivel <= 4:
            intervalo = 2
        elif nivel <= 7:
            intervalo = 4
        else:
            intervalo = 6
    else:
        intervalo = 8
    
    # Programar próximo análisis
    analysis_timer = threading.Timer(intervalo, capture_and_analyze)
    analysis_timer.daemon = True
    analysis_timer.start()

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')
    # Enviar datos actuales si existen
    if current_analysis and current_dj_phrase:
        emit('analysis_update', {
            'analysis': current_analysis,
            'dj_phrase': current_dj_phrase
        })

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

@socketio.on('start_camera')
def handle_start_camera():
    global cap, analysis_timer
    
    if cap is not None:
        cap.release()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        emit('error', {'message': 'No se puede abrir la cámara'})
        return
    
    emit('camera_started', {'message': 'Cámara iniciada correctamente'})
    
    # Iniciar análisis automático
    if analysis_timer:
        analysis_timer.cancel()
    capture_and_analyze()

@socketio.on('stop_camera')
def handle_stop_camera():
    global cap, analysis_timer
    
    if analysis_timer:
        analysis_timer.cancel()
    
    if cap:
        cap.release()
        cap = None
    
    emit('camera_stopped', {'message': 'Cámara detenida'})

@socketio.on('get_frame')
def handle_get_frame():
    global cap
    
    if cap is None or not cap.isOpened():
        return
    
    ret, frame = cap.read()
    if ret:
        # Codificar frame como base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        emit('frame_update', {'frame': frame_base64})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)