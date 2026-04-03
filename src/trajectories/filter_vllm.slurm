#!/usr/bin/env bash
#SBATCH --job-name=filtering_with_prometheus
#SBATCH --cpus-per-task=4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=64GB
#SBATCH --gres=gpu:2
#SBATCH --output=logs/filter_vllm.log
#SBATCH --error=logs/filter_vllm.err
#SBATCH --time=12:00:00

mkdir -p /home/agarcia1124/.cache/huggingface
export HF_HOME=/home/agarcia1124/.cache/huggingface
export HF_HUB_CACHE=/home/agarcia1124/.cache/huggingface
export HF_USERNAME=nowhereman14

export PYTORCH_ALLOC_CONF=expandable_segments:True

cd /home/agarcia1124/src
source /home/agarcia1124/src/venv/bin/activate

export PYTHONPATH=/home/agarcia1124/src:$PYTHONPATH

python trajectories/filter_vllm.py \
    "trajectories/trajectories_no_badcalls/trajectories_nobad_001.json" \
    --output="trajectories/filtered_001.json" \
    --min_score=5