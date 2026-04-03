import os

os.environ["HF_HOME"] = "/home/agarcia1124/.cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/home/agarcia1124/.cache/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/home/agarcia1124/.cache/huggingface"

import json
import argparse
import random
from dotenv import load_dotenv
from vllm import LLM, SamplingParams
from react import react_process, TravelScene
from hotel_scene.prompt_hotel import load_prompt as load_hotel_prompt
from restaurant_scene.prompt_restaurant import load_prompt as load_restaurant_prompt

load_dotenv()

llm = LLM(model="casperhansen/llama-3.3-70b-instruct-awq", tensor_parallel_size=2, quantization="awq", gpu_memory_utilization=0.80, max_model_len=8192, enforce_eager=True)
sampling_params = SamplingParams(temperature=0, max_tokens=512, stop=["\nObservation", "\nUser:", "\nSystem:"])
API_URL = os.getenv("API_URL")
RELEVANT_SERVICES = {"restaurant", "hotel"}


def load_dialogues(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)

def get_active_domain(turn: dict) -> str | None:
    """Returns the active domain for a USER turn, or None if not hotel/restaurant."""
    for frame in turn.get("frames", []):
        service = frame.get("service", "")
        intent = frame.get("state", {}).get("active_intent", "NONE")
        if service in {"restaurant", "hotel"} and intent != "NONE":
            return service
    return None

def is_useful_turn(utterance: str) -> bool:
    trivial = ["thank", "goodbye", "bye", "great", "thanks", "you too", "perfect"]
    utt = utterance.lower()
    return not any(t in utt for t in trivial) and len(utterance.split()) > 5

def get_first_domain(dialogue: dict) -> str | None:
    """Returns the domain of the first USER turn if it's hotel or restaurant, else None."""
    for turn in dialogue["turns"]:
        if turn["speaker"] == "USER":
            domain = get_active_domain(turn)
            if domain in {"restaurant", "hotel"}:
                return domain
            else:
                return None  # primer turno no es hotel/restaurant, descarta
    return None

def extract_turns(dialogue: dict) -> list[dict]:
    domain = get_first_domain(dialogue)
    if domain is None:
        return []  # descarta diálogos que no empiezan por hotel/restaurant

    turns = dialogue["turns"]
    examples = []
    history_parts = []

    for turn in turns:
        speaker = turn["speaker"]
        utterance = turn["utterance"]

        if speaker == "USER":
            active_domain = get_active_domain(turn)
            
            # Cortar cuando cambia de dominio
            if active_domain is not None and active_domain != domain:
                break

            if history_parts and is_useful_turn(utterance):
                examples.append({
                    "dialogue_id": dialogue["dialogue_id"],
                    "domain": domain,
                    "history": "\n".join(history_parts),
                    "query": f"User: {utterance}"
                })

            history_parts.append(f"User: {utterance}")
        else:
            history_parts.append(f"System: {utterance}")

    return examples

def call_with_retry(prompt, history, scene, retries=5):
    for attempt in range(retries):
        try:
            result = react_process(
                prompt, history, scene,
                model=llm, verbose=False
            )
            return result
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
    raise Exception("Max retries exceeded")

def generate_trajectories(dialogues_path: str, output_path: str, max_dialogues: int = None):
    dialogues = load_dialogues(dialogues_path)
    if max_dialogues:
        dialogues = dialogues[:max_dialogues]

    hotel_prompt = load_hotel_prompt()
    restaurant_prompt = load_restaurant_prompt()

    results = []
    for dialogue in dialogues:
        examples = extract_turns(dialogue)
        for example in examples:
            domain = example["domain"]
            prompt = hotel_prompt if domain == "hotel" else restaurant_prompt
            history = f"{example['history']}\n{example['query']}"

            try:
                scene = TravelScene(domain=domain, api_url=API_URL)
                result = call_with_retry(prompt, history, scene)
                results.append({
                    "dialogue_id": example["dialogue_id"],
                    "domain": domain,
                    "history": history,
                    "dialogue": result["dialogue"],
                    "predicted_finish": result["final_answer"],
                    "forced_finish": result["forced_finish"],
                    "num_badcalls": result["num_badcalls"]
                })
                print(f"✓ {example['dialogue_id']} — {domain}")
                if len(results) % 10 == 0:
                    with open(output_path, "w") as f:
                        json.dump({"instances": results}, f, indent=2)
                    print(f"  → Saved checkpoint ({len(results)} examples)")
            except Exception as e:
                print(f"✗ {example['dialogue_id']} — {e}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"instances": results}, f, indent=2)
    print(f"\nSaved {len(results)} trajectories to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialogues_path", type=str, required=True)
    parser.add_argument("--output_path", type=str, required=True)
    parser.add_argument("--max_dialogues", type=int, default=None)
    args = parser.parse_args()
     
    generate_trajectories(
        dialogues_path=args.dialogues_path,
        output_path=args.output_path,
        max_dialogues=args.max_dialogues 
    )
