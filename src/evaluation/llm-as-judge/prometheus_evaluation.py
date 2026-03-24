"""
python src/llm-as-judge/prometheus-eval.py --reference_folder src/react_prompt_model_playground/to_process/manual_100 --results_folder src/react_prompt_model_playground/results/manual_100/example_marking_dict_default_L3.3-70B-I
"""

# Absolute Grading: Outputs score of 1 to 5

import asyncio
import sys
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
from prometheus_eval import PrometheusEval
from prometheus_eval.litellm import AsyncLiteLLM
from prometheus_eval.prompts import ABSOLUTE_PROMPT, SCORE_RUBRIC_TEMPLATE
from create_results_set import create_results, save_results
import argparse

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Evaluate the model using Prometheus-Eval")
  parser.add_argument("--results_file", type=str, help="Path to the file containing the model results")
  parser.add_argument("--gold_standard", type=str, help="Path to the file containing the reference answers")
  parser.add_argument("--model", type=str, default="prometheus-eval/prometheus-8x7b-v2.0", help="Model to use for evaluation")
  parser.add_argument("--tensor-parallel-size", type=int, default=1, help="Tensor parallel size for VLLM")
  parser.add_argument("--remove_reference", action="store_true", help="Remove the reference answers from the evaluation")
  args = parser.parse_args()

  print(args)
  os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")
  model = AsyncLiteLLM('gemini/gemini-2.5-flash-lite', requests_per_minute=20)
  judge = PrometheusEval(model=model, absolute_grade_template=ABSOLUTE_PROMPT)

  #! export VLLM_CACHE_ROOT="/home/mferro/SCRATCH/simmc-luminous/.cache/vllm"

  instructions, responses, rubrics, reference_answers, filenames = create_results(
    results_file=args.results_file,
    gold_standard=args.gold_standard
  )

  score_rubric = list(map(lambda r: SCORE_RUBRIC_TEMPLATE.format(**r), rubrics)) 

  feedback, score = judge.absolute_grade(
    instructions=instructions,
    responses=responses,
    rubric=score_rubric,
    reference_answers=None if args.remove_reference else reference_answers
  )

  save_results(args.results_file, filenames, feedback, score, args.__dict__)

import warnings
warnings.filterwarnings("ignore")

  # Output
  # Feedback: The response provided shows a high level of empathy and emotional intelligence. It effectively addresses the emotional distress expressed by the user. It acknowledges the user's pain and validates their feelings of loneliness and sadness, which is a crucial aspect of providing empathetic advice. The response also suggests practical steps for coping, such as embracing emotions, practicing self-care, and seeking support from friends, family, or professionals. Furthermore, the response reassures the user that healing is a personal process with no fixed timeline, offering comfort and understanding. It emphasizes the user's worth and potential to overcome the situation, which demonstrates a profound comprehension of the user's emotions and situation. By comparing the score rubric with the provided response, it is clear that the model exhibits an excellent ability to apply empathy and emotional intelligence. The response does not have any deficiencies in emotional depth and successfully meets the criteria for a score of 5.
  # Score: 5