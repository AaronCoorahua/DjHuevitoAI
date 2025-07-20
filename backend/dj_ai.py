# dj_ai.py

import os
import json
import base64
import google.generativeai as genai
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# --- Carga de Claves ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GEMINI_API_KEY or not ELEVENLABS_API_KEY:
    raise ValueError("Asegúrate de que GEMINI_API_KEY y ELEVENLABS_API_KEY están en tu .env")

# --- Inicialización de Clientes ---
genai.configure(api_key=GEMINI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
text_model = genai.GenerativeModel('gemini-1.5-flash-latest')

VOICE_IDS = {
    "bad_bunny": "6DsgX00trsI64jl83WWS", 
    "bob_sponge": "G4IAP30yc6c1gK0csDfu"
}

# --- PROMPTS FUSIONADOS ---

PROMPT_ANALISIS = """
Eres un analista de multitudes experto y DJ. Tu trabajo es observar una imagen de una fiesta y evaluar la energía. Proporciona tu análisis únicamente en formato JSON con la siguiente estructura:
{
  "hay_personas": boolean,
  "numero_personas": integer,
  "descripcion_general": "string",
  "nivel_energia": integer (1-10),
  "personas_bailando": boolean,
  "personas_aburridas": boolean,
  "genero_recomendado": "string"
}
Para "genero_recomendado", elige uno de esta lista: [reggaeton, edm, chill, salsa, rock, kpop, lofi, disco, techno, meditacion]. Evalúa el estilo del lugar, número de personas, sus gestos y ropa. Sé creativo pero preciso.
"""

PROMPT_VOZ_DJ = """
Eres un DJ animador. Tu personalidad cambiará según el personaje que se te asigne.
Tu objetivo es que NADIE se aburra. Has recibido un análisis JSON del ambiente. Tu tarea es generar UNA SOLA LÍNEA de diálogo corta y enérgica.

PERSONAJES DISPONIBLES:
- "bad_bunny": Eres Bad Bunny. Usa jerga boricua, habla con un estilo urbano, relajado pero con energía. 'Mera, mano, ¿qué fue?', '¡Fuego, fuego!'.
- "bob_sponge": Eres Bob Esponja. Eres extremadamente optimista, inocente y enérgico. Usa frases como '¡Estoy listo!', ríete de forma escandalosa.

PERSONAJE ACTUAL: {personaje}

REGLAS:
- Si no hay gente, haz un chiste sobre una fiesta fantasma.
- Si la gente está aburrida, anímalos directamente.
- Si la energía es baja (1-4), motívalos a moverse.
- Si la energía es media (5-7), anímalos a que suban el nivel.
- Si la energía es alta (8-10), celébralo con ellos.

Aquí está el reporte del ambiente:
{reporte_json}

Actuando como {personaje}, dame solo la frase que dirías. Sin introducciones, ni explicaciones, SOLO LA FRASE.
"""

def analizar_ambiente(frame_image):
    try:
        print("🤖 Analizando ambiente con Gemini Vision...")
        response = vision_model.generate_content([PROMPT_ANALISIS, frame_image])
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_text)
    except Exception as e:
        print(f"Error en el análisis de ambiente: {e}")
        return None

def generar_voz_dj(analisis_dict, personaje="bad_bunny"):
    try:
        # 1. Generar la frase con Gemini
        print(f"🗣️  Generando frase como: {personaje}...")
        reporte_str = json.dumps(analisis_dict, indent=2)
        prompt_final = PROMPT_VOZ_DJ.format(reporte_json=reporte_str, personaje=personaje)
        response = text_model.generate_content(prompt_final)
        frase_dj = response.text.strip().replace('"', '') # Limpiar comillas
        
        # 2. Generar el audio con ElevenLabs
        print(f"🔊 Generando audio para: '{frase_dj}'")
        voice_id = VOICE_IDS.get(personaje, VOICE_IDS["bad_bunny"])
        
        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=frase_dj,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2"
        )
        
        audio_bytes = b"".join(audio_stream)
        
        return frase_dj, audio_bytes

    except Exception as e:
        print(f"Error al generar la voz o el audio del DJ: {e}")
        fallback_phrase = "¡Se me cruzaron los cables! ¡Pero la fiesta sigue!"
        return fallback_phrase, None