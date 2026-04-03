import os
os.environ["VLLM_USE_V1"] = "0"
os.environ['HF_HOME'] = '/home/agarcia1124/.cache/huggingface'
os.environ['HF_HUB_CACHE'] = '/home/agarcia1124/.cache/huggingface'
os.environ['TRANSFORMERS_CACHE'] = '/home/agarcia1124/.cache/huggingface'
os.environ['VLLM_CACHE'] = '/home/agarcia1124/.cache/huggingface'
os.environ['HUGGINGFACE_HUB_CACHE'] = '/home/agarcia1124/.cache/huggingface'
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] = "1"

import json
import argparse
from os import PathLike
import vllm
from vllm import LLM, SamplingParams
from evaluation.llm_as_judge.create_results_set import clean_restaurants, clean_hotels

INSTRUCTION_TEMPLATE = """
### Conversation history:
{history}

### Database (use this to verify factual accuracy):
{db}
""".strip()

RUBRIC_SCORES_INFORM = {
    "score1_description": "The assistant provides ANY incorrect factual information about the restaurant or hotel (wrong price range, wrong area, wrong food type, etc.) or returns ANY hallucinated instance that is not in the database. Alternatively, the model enters into a series of unnecessary loops",
    "score2_description": "",
    "score3_description": "The model provides partially correct information  acknowledges the request but some details are inaccurate. Alternatively, the model provides correct information, but some illogical API calls or loops have been observed.",
    "score4_description": "",
    "score5_description": "The model answers the question and provides accurate and concise information (present in the database) about the relevant instance (restaurant/hotel). In addition, all the API calls were correct and no unnecessary repetitive loop was observed"
}

RUBRIC_SCORES_FALLBACK = {
    "score1_description": "The model gives up or offers hallucinated alternatives that do not exist in the database. Alternatively, the model enters into a series of unnecessary loops",
    "score2_description": "",
    "score3_description": "The assistant acknowledges that there are no results for the user's query but does not offer alternatives or some illogical API calls or loops have been observed.",
    "score4_description": "",
    "score5_description": "The assistant acknowledges that there are no results for the user's query and offers correct or reasonable alternatives. In addition, all the API calls were correct and no unnecessary repetitive loop was observed"
}

RUBRIC_CRITERIA = """
Evaluate folowing this pipeline:
1. Does the assistant correctly answer the user's question with accurate information about the restaurant/hotel? Use only the information in the database for factual evaluation.
2. Were API calls (Search/Look) correct or logical?
3. Were there any unnecessary repetitive loops?
"""
def get_relevant_db_unlabeled(instance, db):
    history = instance.get("history", "").lower()
    prediction = instance.get("predicted_finish", "").lower()
    
    combined_text = history + " " + prediction
    
    relevant = []
    for item in db:
        name = item.get("name", "").lower()
        if name and name in combined_text:
            relevant.append(item)
    if relevant:
        return relevant
    else:
        return db[:15]
    
def filter_trajectories(trajectories_file, output_file, min_score=4):
    with open(trajectories_file, "r") as f:
        data = json.load(f)
    
    valid_instances = [inst for inst in data if inst.get("predicted_finish") and not inst.get("forced_finish")]

#Model configuration

    model = LLM(
        model="prometheus-eval/prometheus-13b-v1.0",
        tensor_parallel_size=1,
        gpu_memory_utilization=0.8,
        enforce_eager=True,
        max_model_len=8192,
        trust_remote_code=True
    )
    sp = SamplingParams(temperature=0, max_tokens=512, stop=["\n###", "###", "Instruction:"])
    
#Prompt building

    prompts = []
    print(f"Preparing {len(valid_instances)} prompts...")

    for instance in valid_instances:

        domain = instance["domain"]
        db = clean_restaurants if domain == "restaurant" else clean_hotels
        relevant_db = get_relevant_db_unlabeled(instance, db)

        history_text = instance["history"]
        if len(history_text) > 2000:
            history_text = "[...History truncated...] " + history_text[-2000:]

        instructions = (INSTRUCTION_TEMPLATE.format(
            history=history_text,
            db=json.dumps(relevant_db, indent=2)
        ))
        responses = instance["predicted_finish"]
        rubrics = f"Criteria: {RUBRIC_CRITERIA}\n"
        rubrics += f"Score 1: {RUBRIC_SCORES_INFORM['score1_description']}\n"
        rubrics += f"Score 3: {RUBRIC_SCORES_INFORM['score3_description']}\n"
        rubrics += f"Score 5: {RUBRIC_SCORES_INFORM['score5_description']}"

        prompt = f"""###Task Description:
An instruction (might include an Input inside it), a response to evaluate, and a score rubric representing evaluation criteria are given.
1. Write a detailed feedback that assess the quality of the response strictly based on the given score rubric, not evaluating in general.
2. After writing a feedback, write a score that is an integer between 1 and 5.
3. The output format should look as follows: "Feedback: (write a feedback for criteria) [RESULT] (an integer number between 1 and 5)"

###The instruction to evaluate:
{instructions}

###Response to evaluate:
{responses}

###Score Rubrics:
{rubrics}

###Feedback:"""
        prompts.append(prompt)

    print(f"Evaluating {len(prompts)} trajectories...")

# Batched

    print(f"Evaluating with Prometheus...")
    outputs = model.generate(prompts, sp)

    filtered = []
    for i, (instance, output) in enumerate(zip(valid_instances, outputs)):
        text = output.outputs[0].text
        score = 1

        if "[RESULT]" in text:
            try:
                score = int(text.split("[RESULT]")[-1].strip()[0])
            except:
                score = 1

        instance["prometheus_score"] = score
        instance["prometheus_feedback"] = text
        
        if score >= min_score:
            filtered.append(instance)

    print(f"Kept {len(filtered)}/{len(valid_instances)} with score >= {min_score}")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump({"instances": filtered}, f, indent=2)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectories_file", type=str)
    parser.add_argument("--output", type=str, default="trajectories/filtered.json")
    parser.add_argument("--min_score", type=int, default=4)
    args = parser.parse_args()

    filter_trajectories(args.trajectories_file, args.output, args.min_score)