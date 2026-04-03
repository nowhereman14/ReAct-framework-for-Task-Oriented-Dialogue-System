import json
import os
import argparse

def filter_by_badcall(input_file: str, output_file:str):
    with open(input_file, "r") as f:
        data = json.load(f)

    accepted = []
    skipped = 0

    for instance in data["instances"]:
        if instance["num_badcalls"] == 0:
            accepted.append(instance)
        else:
            skipped += 1
    
    print(f"Selected {len(accepted)} examples, {skipped} instances were not included")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(accepted, f, indent=2)
    
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    parser.add_argument("--output_file", type=str, default="trajectories_no_badcalls/trajectories.json")
    args = parser.parse_args()

    filter_by_badcall(args.input_file, args.output_file)