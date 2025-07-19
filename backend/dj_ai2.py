import cv2, threading, time
import os, json, google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("No se encontró la GEMINI_API_KEY.")
genai.configure(api_key=GEMINI_API_KEY)

vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
text_model = genai.GenerativeModel('gemini-1.5-flash-latest')

PROMPT_ANALISIS = """
Eres un analista de multitudes experto. Tu trabajo es observar una imagen de una fiesta y evaluar la energía. Proporciona tu análisis únicamente en formato JSON con la siguiente estructura:
{
  "hay_personas": boolean, "numero_personas": integer, "descripcion_general": "string",
  "nivel_energia": integer (1-10), "personas_bailando": boolean, "personas_aburridas": boolean
}
"""

PROMPT_VOZ_DJ = """
Eres "DJ Huevito AI", un DJ animador de fiestas. Eres carismático, un poco exagerado y tu objetivo es que NADIE se aburra.
Has recibido un análisis JSON del ambiente actual. Tu tarea es generar UNA SOLA LÍNEA de diálogo corta y enérgica para animar a la gente.

- Si el nivel de energía es bajo (1-4), ¡motívalos a moverse! Lanza un reto o pregunta qué pasa.
- Si la energía es media (5-7), anímalos a que suban el nivel.
- Si la energía es alta (8-10) y están bailando, ¡felicítalos y celebra con ellos!
- Si no ves a nadie, haz un comentario gracioso sobre una fiesta fantasma.
- Si ves gente aburrida, dirígete a ellos directamente de forma divertida.

Aquí está el reporte del ambiente:
{reporte_json}

Basado en este reporte, dame solo la frase que dirías. Sin introducciones, sin explicaciones, solo la frase.
"""

timer = None
cap = None

def analizar_ambiente(frame_image):
    try:
        print("Enviando imagen para análisis de ambiente...")
        response = vision_model.generate_content([PROMPT_ANALISIS, frame_image])
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        analisis = json.loads(json_text)
        return analisis
    except Exception as e:
        print(f"Error en el análisis de ambiente: {e}")
        return None

# --- NUEVO: La función que genera la voz del DJ ---
def generar_voz_dj(analisis_dict):
    try:
        print("Generando frase del DJ...")
        # Convertimos el diccionario de análisis a un string JSON para el prompt
        reporte_str = json.dumps(analisis_dict, indent=2)
        
        # Rellenamos el prompt con el reporte
        prompt_final = PROMPT_VOZ_DJ.format(reporte_json=reporte_str)
        
        response = text_model.generate_content(prompt_final)
        
        # La respuesta debería ser solo la frase, la limpiamos por si acaso
        frase_dj = response.text.strip()
        return frase_dj
        
    except Exception as e:
        print(f"Error al generar la voz del DJ: {e}")
        return "¡Se me cruzaron los cables! ¡Pero la fiesta sigue!"

def programa_analisis():
    global timer
    ret, frame = cap.read()
    if not ret:
        print("No se capturó cuadro.")
        return

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    analisis = analizar_ambiente(pil)

    if analisis:
        # nivel = analisis.get("nivel_energia", 5)
        # frase = generar_voz_dj(analisis)
        # print(f'\nDJ HUEVITO AI (nivel {nivel}): "{frase}"\n')
        nivel = analisis.get("nivel_energia", 5)

        # Imprimir el análisis como antes
        print("\n--- ANÁLISIS DEL AMBIENTE ---")
        print(f"  Descripción: {analisis.get('descripcion_general', 'N/A')}")
        print(f"  Nivel de Energía: {analisis.get('nivel_energia', 'N/A')} / 10")
        print(f"  ¿Gente Bailando?: {'Sí' if analisis.get('personas_bailando') else 'No'}")
        print(f"  ¿Gente Aburrida?: {'Sí' if analisis.get('personas_aburridas') else 'No'}")
        print("-----------------------------")

        # --- NUEVO: 2. Generar y mostrar la voz del DJ ---
        voz_dj = generar_voz_dj(analisis)
        if voz_dj:
            print(f'\nDJ HUEVITO AI: "{voz_dj}"\n')

        if nivel <= 4:
            intervalo = 2
        elif nivel <= 7:
            intervalo = 5
        else:
            intervalo = 7
    else:
        intervalo = 10

    timer = threading.Timer(intervalo, programa_analisis)
    timer.daemon = True
    timer.start()

def main_loop():
    global cap, timer
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: no se puede abrir la cámara.")
        return

    print("Iniciando análisis automático...")
    programa_analisis()  # lanza la primera ejecución

    while True:
        ret, frame = cap.read()
        if not ret: break
        cv2.imshow('DJ Huevito AI', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.1)

    if timer:
        timer.cancel()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main_loop()
