import sys
import os
import requests
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("FIREWORKS_API_KEY"),
    base_url="https://api.fireworks.ai/inference/v1"
)
MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct"

hotel_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/hotel_db.json"
).json()

restaurant_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/restaurant_db.json"
).json()

clean_hotels = [
    {k: h[k] for k in ['name', 'type', 'area', 'pricerange', 'stars', 'parking', 'internet', 'phone'] if k in h}
    for h in hotel_db
]

clean_restaurants = [
    {k: r[k] for k in ['name', 'food', 'area', 'pricerange', 'phone'] if k in r}
    for r in restaurant_db
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('domain', type=str, choices=['hotel', 'restaurant'])
    args = parser.parse_args()

    db = clean_hotels if args.domain == "hotel" else clean_restaurants

    SYSTEM_PROMPT = f"""You are a travel assistant helping users find {args.domain}s in Cambridge. 
    Answer user questions helpfully and naturally.

    Available {args.domain}s:
    {db}

    Answer user questions based strictly on this information.
    """
    history = ""

    print("All-in-context Travel Assistant ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            break

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{history}User: {user_input}"}
            ],
            max_tokens=200
        )

        answer = response.choices[0].message.content
        history += f"User: {user_input}\nSystem: {answer}\n"
        print(f"\nSystem: {answer}\n")