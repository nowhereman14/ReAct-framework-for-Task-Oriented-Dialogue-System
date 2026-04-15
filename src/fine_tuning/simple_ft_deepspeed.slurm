#!/usr/bin/env bash
#SBATCH --job-name=SIMMC-SFT
#SBATCH --cpus-per-task=8
#SBATCH --mem=256GB
#SBATCH --gpus=4
#SBATCH --constraint=a100-sxm4
#SBATCH --nodes=1
#SBATCH --output=logs/SIMMC-SFT-%A.log
#SBATCH --error=logs/SIMMC-SFT-%A.err
#SBATCH --time=05:00:00

set -a; . .env; set +a
source .venv/bin/activate


export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
MASTER_PORT=9327
MAIN_PROCESS_IP=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -n 1)
num_nodes=$SLURM_JOB_NUM_NODES

srun accelerate launch \
        --num_processes $SLURM_GPUS \
        --num_machines $num_nodes \
        --main_process_port $MASTER_PORT \
        --mixed_precision bf16 \
        --dynamo_backend "no" \
        --rdzv_backend static \
        --main_process_ip $MAIN_PROCESS_IP \
        --main_process_port $MASTER_PORT \
        --machine_rank $SLURM_NODEID \
        src/fine_tuning/fine_tuning.py \
        --lora_rank 8 \
        --splits train_furniture_5 train_fashion_5 \
        --dataset_name dataset-ft-no-filter \
        --output_directory src/fine_tuning/adapters/hyperparam_tuning/20250527_70B_test \
        --epochs 2 \
        --batch_size 2 \
        --save_steps 500 \
        --model_name meta-llama/Llama-3.3-70B-Instruct

# python src/fine_tuning/fine_tuning.py \
#     --lora_rank 8 \
#     --splits train_furniture_5 train_fashion_5 \
#     --dataset_name dataset-ft-no-filter \
#     --output_directory src/fine_tuning/adapters/hyperparam_tuning/20250527_70B_test \
#     --epochs 2 \
#     --batch_size 2 \
#     --save_steps 500 \
#     --model_name meta-llama/Llama-3.3-70B-Instruct
