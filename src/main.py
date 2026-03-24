import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import argparse
from react import react_process, TravelScene
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument('domain', type=str, choices=['hotel', 'restaurant'], help='Domain to use')
args = parser.parse_args()

if args.domain == 'hotel':
    from hotel_scene.prompt_hotel import load_prompt
else:
    from restaurant_scene.prompt_restaurant import load_prompt

from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("FIREWORKS_API_KEY"),
    base_url="https://api.fireworks.ai/inference/v1"
)
#client = Groq(api_key=os.getenv("GROQ_API_KEY"))
'''client = OpenAI(
    api_key= os.getenv("OPEN_ROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)'''
API_URL = os.getenv("API_URL")
MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct" #meta-llama/llama-3.3-70b-instruct:free" #llama-3.3-70b-versatile
SYSTEM_PROMPT = load_prompt()

if __name__ == "__main__":

    scene = TravelScene(domain=args.domain, api_url = API_URL)
    history = ""

    '''
    result = react_process(
        prompt=SYSTEM_PROMPT,
        question="User: I need a place to stay that has free wifi",
        scene=scene,
        verbose=True
    )

    print(f"\n=== Final Answer ===")
    print(result['final_answer'])
    '''

    print("Travel Assistant ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            break

        question = f"{history}User: {user_input}"
        result = react_process(
            prompt=SYSTEM_PROMPT,
            question=question,
            scene=scene,
            client=client,
            model=MODEL,
            verbose=True
        )

        answer = result['final_answer']
        history = result['all_conversation'].replace(SYSTEM_PROMPT + "\n", "")
        print(f"\nSystem: {answer}\n")