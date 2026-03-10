import sys
import os
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

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