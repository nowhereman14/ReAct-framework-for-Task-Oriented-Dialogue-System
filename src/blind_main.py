import sys
import os
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key= os.getenv("OPEN_ROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

SYSTEM_PROMPT = """You are a travel assistant helping users find hotels in Cambridge. 
Answer user questions helpfully and naturally."""

if __name__ == "__main__":
    history = ""

    print("Baseline Travel Assistant ready. Type 'exit' to quit.\n")

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