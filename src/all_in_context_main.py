import sys
import os
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

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

SYSTEM_PROMPT = f"""You are a travel assistant helping users find hotels in Cambridge. 
Answer user questions helpfully and naturally.

Available hotels:
{clean_hotels}

Available restaurants:
{clean_restaurants}

Answer user questions based strictly on this information.
"""

if __name__ == "__main__":
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