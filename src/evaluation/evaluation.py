import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import requests as rq
import json
import nltk
from rouge_score import rouge_scorer
import numpy as np
from typing import Literal
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
import time

from react import react_process, TravelScene
from hotel_scene.prompt_hotel import load_prompt as load_hotel_prompt
from restaurant_scene.prompt_restaurant import load_prompt as load_restaurant_prompt
from all_in_context_main import clean_hotels, clean_restaurants

load_dotenv()
client = OpenAI(
    api_key=os.getenv("FIREWORKS_API_KEY"),
    base_url="https://api.fireworks.ai/inference/v1"
)
MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct"
API_URL = os.getenv("API_URL")

def run_blind(history, domain):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a travel assistant helping users find {domain}s in Cambridge. Answer helpfully and naturally."},
            {"role": "user", "content": history}
        ],
        max_tokens=200,
        temperature=0
    )
    return response.choices[0].message.content

def run_all_in_context(history, domain):
    db = clean_hotels if domain == "hotel" else clean_restaurants
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": f"You are a travel assistant. Answer based strictly on this data:\n{db}"},
            {"role": "user", "content": history}
        ],
        max_tokens=200,
        temperature=0
    )
    return response.choices[0].message.content

def calculate_bleu_score(response:str, gold:str) -> float:
    chencherry = nltk.translate.bleu_score.SmoothingFunction()
    bleu_score = nltk.translate.bleu_score.sentence_bleu(
        nltk.tokenize.word_tokenize(gold.lower()),
        nltk.tokenize.word_tokenize(response.lower()),
        smoothing_function=chencherry.method7,
    )
    return bleu_score

def calculate_rouge_score(response: str, gold:str) -> float:
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(gold, response)
    return scores['rougeL'].fmeasure

def calculate_inform_rate(response: str, gold_entities: str) -> float:
    response = response.lower()
    if not gold_entities:
        return 1.0
    hits = sum(1 for v in gold_entities.values() if str(v).lower() in response)
    return hits / len(gold_entities)

def combined_score(inform_score, bleu_score):
    combined_score = inform_score *0.5 + bleu_score
    return combined_score

def evaluate_response(response: str, gold_finish: str, gold_entities:dict) -> dict[Literal["BLEU4"], float]:
    return {'BLEU4': calculate_bleu_score(response, gold_finish),
            'ROUGE': calculate_rouge_score(response, gold_finish),
            'Inform-rate': calculate_inform_rate(response, gold_entities),
            'Combined score': combined_score(calculate_inform_rate(response, gold_entities),
                                             calculate_bleu_score(response, gold_finish))}

def evaluate_set(results: list[dict[Literal["BLEU4"], float]]) -> dict[Literal["BLEU4_mean", "BLEU4_err"], float]:
    # BLEU4
    bleu_scores = [result['BLEU4'] for result in results]
    bleu_str_mean = np.mean(bleu_scores)
    bleu_str_err = np.std(bleu_scores) / np.sqrt(len(bleu_scores))

    # ROUGE
    rouge_scores = [result['ROUGE'] for result in results]
    rouge_str_mean = np.mean(rouge_scores)
    rouge_str_err = np.std(rouge_scores) / np.sqrt(len(rouge_scores))

    # Inform rate
    inform_scores = [result['Inform-rate'] for result in results]
    inform_str_mean = np.mean(inform_scores)
    inform_str_err = np.std(inform_scores) / np.sqrt(len(inform_scores))

    #Combined
    combined_scores = [result['Combined score'] for result in results]
    combined_str_mean = np.mean(combined_scores)
    combined_str_err = np.std(combined_scores) / np.sqrt(len(combined_scores))

    return {'BLEU4_mean': bleu_str_mean, 'BLEU4_err': bleu_str_err,
            'ROUGE_mean': rouge_str_mean, 'ROUGE_err': rouge_str_err,
            'Inform_rate_mean': inform_str_mean, 'Inform_rate_err': inform_str_err,
            'Combined_score_mean': combined_str_mean, 'Combined_score_err': combined_str_err}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gold_standard", type=str, help="Path to gold standard JSON")
    parser.add_argument("--output", type=str, default="evaluation/results.json")
    parser.add_argument("--domain", type=str, choices=["hotel", "restaurant"], default="restaurant")
    parser.add_argument("--system", type=str, choices=["react", "blind", "all_in_context"], default="react")
    args = parser.parse_args()

    with open(args.gold_standard, "r") as f:
        examples_gold = json.load(f)

    if args.domain:
        examples_gold = [e for e in examples_gold if e["domain"] == args.domain] 

    prompt = load_hotel_prompt() if args.domain == "hotel" else load_restaurant_prompt()

    all_results = []
    for example in examples_gold:
        print(f"Evaluating {example['id']}...")
        for attempt in range(3):
            try:
                if args.system == "react":
                    scene = TravelScene(domain=args.domain, api_url=API_URL)
                    result = react_process(prompt, example["history"], scene, client=client, model=MODEL, verbose=False)
                    predicted_finish = result["final_answer"]
                elif args.system == "blind":
                    predicted_finish = run_blind(example["history"], args.domain)
                else:
                    predicted_finish = run_all_in_context(example["history"], args.domain)
                time.sleep(15)
                break 
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}")
                time.sleep(20)  
        else:
            print(f"  Skipping {example['id']} after 3 attempts")
            continue

        metrics = evaluate_response(predicted_finish, example["expected_finish"], example.get("gold_entities", {}))
        
        instance = {
            "id": example["id"],
            "intent": example.get("intent"),
            "history": example["history"],
            "predicted_finish": predicted_finish,
            "expected_finish": example["expected_finish"],
            **metrics
        }
        all_results.append(instance)
        print(f"  BLEU: {metrics['BLEU4']:.3f} | Inform: {metrics['Inform-rate']:.3f} | Combined: {metrics['Combined score']:.3f}")
    
    global_metrics = evaluate_set(all_results)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"global": global_metrics, "instances": all_results}, f, indent=4)

    print("\n── Global Results ──")
    for k, v in global_metrics.items():
        print(f"  {k}: {v:.3f}")

