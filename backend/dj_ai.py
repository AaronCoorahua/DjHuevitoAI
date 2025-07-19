import cv2
import os
import google.generativeai as genai
from dotenv import load_dotenv
import time
import json
from PIL import Image

# --- Carga y configuración (sin cambios) ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("No se encontró la GEMINI_API_KEY.")
genai.configure(api_key=GEMINI_API_KEY)
# Usamos un modelo que puede manejar visión y texto
vision_model = genai.GenerativeModel('gemini-1.5-flash-latest')
# --- NUEVO: Usaremos el mismo modelo para texto, es eficiente ---
text_model = genai.GenerativeModel('gemini-1.5-flash-latest')


# --- Prompt para el análisis de la imagen (sin cambios) ---
PROMPT_ANALISIS = """
Eres un analista de multitudes experto. Tu trabajo es observar una imagen de una fiesta y evaluar la energía. Proporciona tu análisis únicamente en formato JSON con la siguiente estructura:
{
  "hay_personas": boolean, "numero_personas": integer, "descripcion_general": "string",
  "nivel_energia": integer (1-10), "personas_bailando": boolean, "personas_aburridas": boolean
}
"""

# --- NUEVO: El prompt para la voz del DJ ---
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


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se puede abrir la cámara.")
        return

    while True:
        ret, frame = cap.read()
        if not ret: break

        cv2.imshow('DJ Huevito AI - Vista de la Camara', frame)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)

        # 1. Obtener el análisis de la escena
        analisis = analizar_ambiente(pil_image)

        if analisis:
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

        print("\nEsperando 10 segundos para el próximo análisis...")
        if cv2.waitKey(10000) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()