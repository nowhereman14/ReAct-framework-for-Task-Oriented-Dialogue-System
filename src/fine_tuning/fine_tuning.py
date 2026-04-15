'''
python fine_tuning.py \
    --model_name "meta-llama/Llama-3.1-8B-Instruct" \
    --dataset_name "./hf_set/dataset_hf_hf" \
    --splits train \
    --output_directory "/content/drive/MyDrive/Colab Notebooks/llama" \
    --lora_rank 32 \
    --use_datacollator \
    --max_steps -1
'''
import torch
import argparse
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, EarlyStoppingCallback
import datasets
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from trl import SFTTrainer, SFTConfig, DataCollatorForCompletionOnlyLM

bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )

def get_model_and_tokenizer(model_name: str) -> tuple:
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="sdpa",
        torch_dtype=torch.bfloat16)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return model, tokenizer

def apply_lora(model, rank: int):
    config = LoraConfig(
        r=rank,
        lora_alpha=rank
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    return model

def load_dataset(dataset_name: str, splits: list) -> datasets.Dataset:
    dataset = datasets.load_from_disk(dataset_name)
    data_splits = [dataset[split] for split in splits]
    new_dataset = datasets.concatenate_datasets(data_splits, split="train")
    new_dataset = new_dataset.shuffle(seed=42)
    return new_dataset

def formatting_func(example):
    user_input = example['input'].strip()
    if "<example_4>" in user_input:
        # Cortamos justo antes del ejemplo 3 y mantenemos el cierre de las instrucciones
        partes = user_input.split("<example_4>")
        # Reconstruimos el input solo con las reglas y los 2 primeros ejemplos
        user_input = partes[0] + "\n(He recortado los ejemplos restantes para ahorrar espacio)\n"
    
    text = (
        f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_input}<|eot_id|>" 
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{example['output'].strip()}<|eot_id|>"
    )
    return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a model with LoRA")
    parser.add_argument("--model_name", type=str, default="meta-llama/Llama-3.1-8B-Instruct", help="Name of the model to fine-tune")
    parser.add_argument("--lora_rank", type=int, default=16, help="Rank for LoRA")
    parser.add_argument("--dataset_name", type=str, default="dataset-ft-no-filter", help="Name of the dataset to use for fine-tuning")
    parser.add_argument("--splits", type=str, required=True, nargs="+", help="List of splits to use for fine-tuning")
    parser.add_argument("--output_directory", type=str, default="output_model", help="Output directory for the fine-tuned model")
    parser.add_argument("--max_steps", type=int, default=-1, help="Maximum number of training steps")
    parser.add_argument("--max_seq_length", type=int, default=4096, help="Maximum sequence length for the model")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for training")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate for training")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs for training")
    parser.add_argument("--save_steps", type=int, default=60, help="Number of steps between model saves")
    parser.add_argument("--use_datacollator", action="store_true", help="Use data collator for training")
    parser.add_argument("--data_collector_text", type=str, default="<|start_header_id|>assistant<|end_header_id|>\n\n", help="Text to use for data collection")
    args = parser.parse_args()
    print(args)
    
    config = SFTConfig(
            max_seq_length=args.max_seq_length,
            output_dir=args.output_directory,
            per_device_train_batch_size=args.batch_size,
            per_device_eval_batch_size=1,
            eval_accumulation_steps=1,
            learning_rate=args.learning_rate,
            save_strategy="steps",
            gradient_checkpointing=True,
            save_steps=args.save_steps,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            push_to_hub=False,
            bf16 = True,
            packing=False,
            #deepspeed="src/fine_tuning/deepspeed_config.json",
            optim="paged_adamw_32bit", #Optim for QLoRA
            #optim="adamw_torch_fused",
            logging_steps=1,
            eval_strategy="steps",
            eval_steps=20,
            load_best_model_at_end=False,
            metric_for_best_model=None,
            greater_is_better=False
    ) 

    model, tok = get_model_and_tokenizer(args.model_name)
    model = prepare_model_for_kbit_training(model)
    tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    tok.truncation_side = "left"
    tok.padding = True
    model.config.use_cache = False

    dataset = load_dataset(args.dataset_name, args.splits)
    val_dataset = load_dataset(args.dataset_name, ["validation"])

    response_template = "<|start_header_id|>assistant<|end_header_id|>\n\n"

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        eval_dataset=val_dataset,
        peft_config=LoraConfig(
            r=args.lora_rank,
            lora_alpha=args.lora_rank
        ),
        processing_class=tok,
        formatting_func=formatting_func,
        data_collator=DataCollatorForCompletionOnlyLM(response_template=response_template, tokenizer=tok) if args.use_datacollator else None,
        args=config
    )

    trainer.train()

    history = trainer.state.log_history

#Plotting the learning curve

    steps = [x['step'] for x in history if 'loss' in x]
    loss = [x['loss'] for x in history if 'loss' in x]

    eval_steps = [x['step'] for x in history if 'eval_loss' in x]
    eval_loss = [x['eval_loss'] for x in history if 'eval_loss' in x]

    plt.figure(figsize=(10, 6))
    plt.plot(steps, loss, label='Train Loss', color='red', alpha=0.5)
    if eval_loss:
        plt.plot(eval_steps, eval_loss, label='Eval Loss', color='blue', marker='o')

    plt.title('Llama-3.1 8B ReAct Fine-Tuning: Learning Curve')
    plt.xlabel('Steps')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)

    plt.savefig("training_curve.png")
    print("Graphic saved")

    trainer.save_model(os.path.join(args.output_directory, "final"))
    tok.save_pretrained(os.path.join(args.output_directory, "final"))
