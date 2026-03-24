import argparse
from pathlib import Path
import json
import numpy as np
from collections import defaultdict

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Path to the input folder")
    '''parser.add_argument("--output", type=str, help="Path to the output folder")'''
    args = parser.parse_args()
    folder = Path(args.input)

    bleu_dict = defaultdict(list)
    rouge_dict = defaultdict(list)
    inform_dict = defaultdict(list)
    prom_dict = defaultdict(list)

    for file in folder.iterdir():
        if file.is_file():
            with open(file, "r") as f:
                file_json = json.load(f)
            for inst in file_json["instances"]:
                inst_id = inst["id"]
                bleu_dict[inst_id].append(inst["BLEU4"])
                rouge_dict[inst_id].append(inst["ROUGE"])
                inform_dict[inst_id].append(inst["Inform-rate"])
                prom_dict[inst_id].append(inst["prometheus_score"])
    
    bleu_per_instance = [np.mean(v) for v in bleu_dict.values()]
    rouge_per_instance = [np.mean(v) for v in rouge_dict.values()]
    inform_per_instance = [np.mean(v) for v in inform_dict.values()]
    prom_per_instance = [np.mean(v) for v in prom_dict.values()]

    def compute_stats(values):
        mean = np.mean(values)
        std = np.std(values)
        stderr = std / np.sqrt(len(values))
        return mean, std, stderr

    bleu_mean, bleu_std, bleu_stderr = compute_stats(bleu_per_instance)
    rouge_mean, rouge_std, rouge_stderr = compute_stats(rouge_per_instance)
    inform_mean, inform_std, inform_stderr = compute_stats(inform_per_instance)
    prom_mean, prom_std, prom_stderr = compute_stats(prom_per_instance)

    print("=== FINAL METRICS (per-instance aggregated) ===")
    print(f"BLEU: {bleu_mean:.4f} ± {bleu_stderr:.4f}")
    print(f"ROUGE: {rouge_mean:.4f} ± {rouge_stderr:.4f}")
    print(f"Inform: {inform_mean:.4f} ± {inform_stderr:.4f}")
    print(f"Prometheus: {prom_mean:.4f} ± {prom_stderr:.4f}")          