import json
import os

folder_path = "trajectories/filtered_trajectories"
output_file = os.path.join(folder_path, "train_set_final_total.json")

target_files = [
    "filtered_001.json",
    "filtered_002.json",
    "filtered_003.json",
    "filtered_004.json",
    "filtered_005.json" 
]

all_trajectories = []

print("--- Starting Unification Process ---")

for filename in target_files:
    file_path = os.path.join(folder_path, filename)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                initial_count = len(all_trajectories)
                
                if isinstance(data, dict):
                    for category in data:
                        if isinstance(data[category], list):
                            all_trajectories.extend(data[category])
                
                elif isinstance(data, list):
                    all_trajectories.extend(data)
                
                added_count = len(all_trajectories) - initial_count
                print(f"File '{filename}': Found {added_count} trajectories.")
            
            except json.JSONDecodeError:
                print(f"Error: '{filename}' is not a valid JSON file.")
    else:
        print(f"Warning: '{filename}' was not found in the directory.")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_trajectories, f, indent=4, ensure_ascii=False)

print("\n--- Final Report ---")
print(f"Total trajectories ready for training: {len(all_trajectories)}")
print(f"Output saved to: {output_file}")