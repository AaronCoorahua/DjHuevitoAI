import cv2, threading, time
import os, json, google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import os
import json
import base64
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
from elevenlabs.client import ElevenLabs

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")


if not GEMINI_API_KEY or not ELEVENLABS_API_KEY:
    raise ValueError("Asegúrate de que GEMINI_API_KEY y ELEVENLABS_API_KEY están en tu .env")


genai.configure(api_key=GEMINI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
text_model = genai.GenerativeModel('gemini-1.5-flash-latest')

VOICE_IDS = {
    "bad_bunny": "JBFqnCBsd6RMkjVDRZzb", # Ejemplo: "SOkoPBb6gm3cm657p2kE"
    "bob_sponge": "G4IAP30yc6c1gK0csDfu"  # Ejemplo: "oVo2c4VvCMvK4dt4vkaI"
}

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

# --- FUNCIÓN DE GENERAR VOZ ACTUALIZADA ---
def generar_voz_dj(analisis_dict, personaje="bad_bunny"):
    """
    Genera la frase del DJ y el audio correspondiente.
    Devuelve una tupla: (frase_del_dj, audio_en_bytes)
    """
    try:
        # 1. Generar la frase con Gemini
        print(f"Generando frase del DJ como: {personaje}...")
        reporte_str = json.dumps(analisis_dict, indent=2)
        prompt_final = PROMPT_VOZ_DJ.format(reporte_json=reporte_str, personaje=personaje)
        response = text_model.generate_content(prompt_final)
        frase_dj = response.text.strip()
        
        # 2. Generar el audio con ElevenLabs
        print(f"Generando audio para la frase: '{frase_dj}'")
        voice_id = VOICE_IDS.get(personaje, VOICE_IDS["bad_bunny"]) # Usa Bad Bunny por defecto si no encuentra el ID
        
        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=frase_dj,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2" # Buen modelo para español
        )
        
        # Concatenamos los chunks de audio en un solo objeto de bytes
        audio_bytes = b"".join(audio_stream)
        
        return frase_dj, audio_bytes

    except Exception as e:
        print(f"Error al generar la voz o el audio del DJ: {e}")
        fallback_phrase = "¡Se me cruzaron los cables! ¡Pero la fiesta sigue!"
        return fallback_phrase, None
