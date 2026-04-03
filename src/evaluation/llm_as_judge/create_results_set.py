import json
import os
from os import PathLike
from typing import TypeAlias
from os import path
import numpy as np

import requests

restaurant_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/restaurant_db.json"
).json()
hotel_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/hotel_db.json"
).json()

clean_restaurants = [
    {k: r[k] for k in ['name', 'food', 'area', 'pricerange', 'phone'] if k in r}
    for r in restaurant_db
]
clean_hotels = [
    {k: h[k] for k in ['name', 'type', 'area', 'pricerange', 'stars', 'parking', 'internet', 'phone'] if k in h}
    for h in hotel_db
]

Instruction: TypeAlias = str
Response: TypeAlias = str
Rubric: TypeAlias = dict
ReferenceAnswer: TypeAlias = str

INSTRUCTION_TEMPLATE = """
### Expected entities:
{gold_entities}

### Conversation history:
{history}

### Database (use this to verify factual accuracy):
{db}
""".strip()

RESPONSE_TEMPLATE = """
{final_answer}
""".strip()

REFERENCE_ANSWER_TEMPLATE = """
{correct_answer}
""".strip()

RUBRIC_SCORES_INFORM = {
    "score1_description":"The assistant provides incorrect factual information about the restaurant or hotel (wrong price range, wrong area, wrong food type, etc.) or returns ANY hallucinated instance that is not in the database.",
    "score2_description":"",
    "score3_description":"The model provides partially correct information — acknowledges the request but some details are inaccurate.",
    "score4_description":"",
    "score5_description":"The model answers the question and provides accurate and concise information (present in the database) about the relevant instance (restaurant/hotel)"
}

RUBRIC_SCORES_FALLBACK = {
    "score1_description":"The model gives up or offer hallucinated alternatives that do no exist in the database",
    "score2_description":"",
    "score3_description":"The assistant acknowledges that there are no results for the user's query but do not offer alternatives",
    "score4_description":"",
    "score5_description":"The assistant acknowledges that there are no result for the user's query and offers correct or reasonable alternatives",
}

RUBRIC_CRITERIA_TEMPLATE = """
Does the assistant correctly answer the user's question with accurate information about the restaurant/hotel? Use only the information in the databse for factual evaluation. The fields from the database that may be
used are 'area', 'address, 'pricerange', 'stars', 'internet', 'parking', 'price', 'name' and 'postcode' for hotels and 'name', 'food', 'area, 'pricerange', 'phone' and 'introduction' for restaurants. Do not confuse fields, for example,
the model can say that a restaurant serves a variety of Chinese dishes insteead of saying that is a Chinese restaurant because it is using the 'introduction'
field instead of 'food', this is accepted, it is not an hallucination by any means. Be careful with saying some info is an hallucination, you SHOULD ALWAYS double check. Offering information for restaurants from the 'introduction' field of the dataset SHOULD be rewarded.
""".strip()

def get_relevant_db(gold, db):
    entities = gold.get("gold_entities", {})
    area = entities.get("area")
    food = entities.get("food")
    name = entities.get("name") or entities.get("name_1") or entities.get("name_2")
    
    relevant = [r for r in db if 
                (not area or r.get("area") == area) or
                (not food or r.get("food") == food) or
                (not name or r.get("name") == name)]
    return relevant if relevant else db[:10]

def create_results(
        results_file: PathLike,
        gold_standard: PathLike):
    
    instructions = []
    responses= []
    rubrics = []
    reference_answers = []
    ids = []

    with open(gold_standard, "r") as f:
        gold_data = {e["id"]: e for e in json.load(f)}

    with open(results_file, "r") as f:
        results = json.load(f)["instances"]
    
    for result in results:
        example_id = result["id"]
        gold = gold_data[example_id]
        intent = gold.get("intent", "")

        if "FALLBACK" in intent:
            rubric = RUBRIC_SCORES_FALLBACK
        else:
            rubric = RUBRIC_SCORES_INFORM
        
        db = clean_restaurants if gold["domain"] == "restaurant" else clean_hotels

        instructions.append(INSTRUCTION_TEMPLATE.format(
            history=gold["history"],
            db = get_relevant_db(gold, db),
            gold_entities=gold.get("gold_entities", {})
        ))
        responses.append(result["predicted_finish"])
        reference_answers.append(gold["expected_finish"])
        rubrics.append({
            "criteria": RUBRIC_CRITERIA_TEMPLATE,
            **rubric
        })
        ids.append(example_id)

    return instructions, responses, rubrics, reference_answers, ids

def save_results(results_file: PathLike, ids: list, feedback: list, scores: list, args=None) -> None:
    
    with open(results_file, "r") as f:
        data = json.load(f)

    # Añade feedback y score a cada instancia
    for instance in data["instances"]:
        if instance["id"] in ids:
            idx = ids.index(instance["id"])
            instance["prometheus_feedback"] = feedback[idx]
            instance["prometheus_score"] = scores[idx]

    # Añade media al global
    data["global"]["prometheus_mean"] = sum(scores) / len(scores)
    data["global"]["prometheus_err"] = np.std(scores) / np.sqrt(len(scores))
    data["global"]["prometheus_score1_rate"] = sum(1 for s in scores if s == 1) / len(scores) if scores else 0
    data["global"]["prometheus_score5_rate"] = sum(1 for s in scores if s == 5) / len(scores) if scores else 0

    with open(results_file, "w") as f:
        json.dump(data, f, indent=4)
        

if __name__ == "__main__":
    instructions, responses, rubrics, reference_answers, ids = create_results(
        results_file="evaluation/results_rest_blind_5.json", 
        gold_standard="gold_standard/restaurants_gold.json"
    )
    print(f"Loaded {len(instructions)} examples")