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
Eres un DJ animador de fiestas. Tu personalidad cambiará según el personaje que se te asigne.
Tu objetivo es que NADIE se aburra. Has recibido un análisis JSON del ambiente actual. Tu tarea es generar UNA SOLA LÍNEA de diálogo corta y enérgica para animar a la gente.

PERSONAJES DISPONIBLES:
- "bad_bunny": Eres Bad Bunny. Usa jerga boricua, habla con un estilo urbano, relajado pero con energía. 'Mera, mano, ¿qué fue?', '¡Fuego, fuego!'.
- "bob_sponge": Eres Bob Esponja. Eres extremadamente optimista, inocente y enérgico. Usa frases como '¡Estoy listo!', '¡Krabby Patty!', ríete de forma escandalosa.

PERSONAJE ACTUAL: {personaje}

REGLAS:
- Si el nivel de energía es bajo (1-4), ¡motívalos a moverse!
- Si la energía es media (5-7), anímalos a que suban el nivel.
- Si la energía es alta (8-10) y están bailando, ¡celébralo con ellos!
- Si no ves a nadie, haz un comentario gracioso sobre una fiesta fantasma.
- Si ves gente aburrida, dirígete a ellos directamente de forma divertida.

Aquí está el reporte del ambiente:
{reporte_json}

Basado en el reporte y actuando como {personaje}, dame solo la frase que dirías. Sin introducciones, ni explicaciones, SOLO LA FRASE.
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

# --- FUNCIÓN GENERAR VOZ ACTUALIZADA ---
def generar_voz_dj(analisis_dict, personaje="bad_bunny"): # Añadimos el parámetro 'personaje'
    try:
        print(f"Generando frase del DJ como: {personaje}...")
        reporte_str = json.dumps(analisis_dict, indent=2)
        
        # Rellenamos el prompt con el reporte y el personaje
        prompt_final = PROMPT_VOZ_DJ.format(reporte_json=reporte_str, personaje=personaje)
        
        response = text_model.generate_content(prompt_final)
        
        frase_dj = response.text.strip()
        return frase_dj
        
    except Exception as e:
        print(f"Error al generar la voz del DJ: {e}")
        return "¡Se me cruzaron los cables! ¡Pero la fiesta sigue!"
