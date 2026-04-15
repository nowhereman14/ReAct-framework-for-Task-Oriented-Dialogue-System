import json
import os
import argparse
import datasets
from hotel_scene.prompt_hotel import load_prompt as load_hotel_prompt
from restaurant_scene.prompt_restaurant import load_prompt as load_restaurant_prompt

hotel_prompt = load_hotel_prompt()
restaurant_prompt = load_restaurant_prompt()

def format_trajectory(instance: dict) -> dict | None:
    """Converts a filtered trajectory to input/output format for fine-tuning."""
    
    domain = instance["domain"]
    prompt = hotel_prompt if domain == "hotel" else restaurant_prompt
    history = instance["history"]
    dialogue = instance["dialogue"]
    
    # Build output from dialogue steps
    output_parts = []
    for i, step in dialogue.items():
        thought = step["thought"]
        action = step["action"]
        observation = step["observation"]
        mode = step["mode"]
        
        # Skip steps with bad mode
        if mode == "except":
            return None
        
        output_parts.append(f"Thought {i}: {thought}")
        output_parts.append(f"Action {i}: {action}")
        
        # Don't include observation for Finish actions
        if not action.lower().startswith("finish["):
            output_parts.append(f"Observation {i}: {observation}")
    
    output = "\n".join(output_parts)
    
    return {
        "domain": domain,
        "input": f"{prompt}\n{history}",
        "output": output
    }

def format_dataset(filtered_file: str, output_file: str):
    with open(filtered_file, "r") as f:
        data = json.load(f)
    
    formatted = []
    skipped = 0
    
    for instance in data:
        result = format_trajectory(instance)
        if result is None:
            skipped += 1
            continue
        formatted.append(result)
    
    print(f"Formatted {len(formatted)} examples ({skipped} skipped due to except mode)")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(formatted, f, indent=2)
    
    print(f"Saved to {output_file}")

def convert_to_hf_dataset(json_file: str, output_dir: str):
    
    dataset = datasets.Dataset.from_json(json_file)
    
    # Split train/val 90/10
    split = dataset.train_test_split(test_size=0.1, seed=42)
    
    dataset_dict = datasets.DatasetDict({
        "train": split["train"],
        "validation": split["test"]
    })
    dataset_dict.save_to_disk(output_dir)
    
    print(f"Saved HuggingFace dataset to {output_dir}")
    print(f"Train: {len(split['train'])} examples")
    print(f"Validation: {len(split['test'])} examples")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filtered_file", type=str)
    parser.add_argument("--output", type=str, default="fine_tuning/hf_set/dataset_hf.json")
    args = parser.parse_args()
    
    format_dataset(args.filtered_file, args.output)

    hf_output = args.output.replace(".json", "_hf")
    convert_to_hf_dataset(args.output, hf_output)