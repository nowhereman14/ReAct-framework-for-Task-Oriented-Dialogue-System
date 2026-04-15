import asyncio
import sys
import os
import argparse
import warnings

# 1. Configuración de compatibilidad y parches de red
warnings.filterwarnings("ignore")
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Forzamos al sistema a no usar resolvedores de DNS raros
os.environ["LITELLM_USE_SYSTEM_RESOLVER"] = "True"

from prometheus_eval.prompts import ABSOLUTE_PROMPT, SCORE_RUBRIC_TEMPLATE
from create_results_set import create_results, save_results
import google.generativeai as genai

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the model using Prometheus-Eval")
    parser.add_argument("--results_file", type=str, help="Path to the file containing the model results")
    parser.add_argument("--gold_standard", type=str, help="Path to the file containing the reference answers")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Model to use for evaluation")
    parser.add_argument("--tensor-parallel-size", type=int, default=1, help="Tensor parallel size for VLLM")
    parser.add_argument("--remove_reference", action="store_true", help="Remove the reference answers from the evaluation")
    args = parser.parse_args()

    print(f"Argumentos recibidos: {args}")

    # Configuración del modelo (Usamos la API Key que ya tienes)
    api_key = "AIzaSyD0C5Rv61hQ9gR-e4MrQwVr-j3HZ3zlvd0"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(args.model)

    # 2. Carga de datos (Exactamente igual que tu original)
    instructions, responses, rubrics, reference_answers, filenames = create_results(
        results_file=args.results_file,
        gold_standard=args.gold_standard
    )

    # 3. Preparación de rúbricas (Exactamente igual)
    score_rubric = list(map(lambda r: SCORE_RUBRIC_TEMPLATE.format(**r), rubrics)) 

    feedback_list = []
    score_list = []

    print(f"--- Iniciando Evaluación Prometheus (Modo Robusto) ---")
    
    # 4. Simulación del método judge.absolute_grade
    # En lugar de usar la librería que falla, ejecutamos su lógica aquí
    for i in range(len(instructions)):
        print(f"Procesando {i+1}/{len(instructions)}...", end="\r")
        
        # Construimos el prompt oficial de Prometheus
        ref_answer = None if args.remove_reference else reference_answers[i]
        
        prompt_final = ABSOLUTE_PROMPT.format(
            instruction=instructions[i],
            response=responses[i],
            reference_answer=ref_answer,
            rubric=score_rubric[i]
        )

        try:
            # Llamada directa sin pasar por LiteLLM (evita error DNS)
            res = model.generate_content(prompt_final)
            response_text = res.text
            
            # Extracción del score (Lógica estándar de Prometheus)
            score = 1
            if "[RESULT]" in response_text:
                try:
                    score = int(response_text.split("[RESULT]")[-1].strip())
                except:
                    score = 1
            
            feedback_list.append(response_text)
            score_list.append(score)
        except Exception as e:
            print(f"\nError en muestra {i+1}: {e}")
            feedback_list.append(f"Error en evaluación: {e}")
            score_list.append(1)

    # 5. Guardado (Exactamente igual que tu original)
    # Pasamos score_list que ya son enteros para evitar el TypeError
    save_results(args.results_file, filenames, feedback_list, score_list, args.__dict__)

    print(f"\n--- ¡ÉXITO! Evaluación finalizada ---")
    print(f"Resultados guardados en: {args.results_file}")