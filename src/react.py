"""
ReAct implementation
"""
import os
from string import Template
from typing import Any, Literal
import pandas as pd
import re
import requests as req


class TravelScene:
    def __init__(self, domain: str, api_url: str, area: str = None):
        self.domain = domain #Hotel or restaurant
        self.api_url = api_url
        self.area = area
    
    def look(self) -> tuple[str, int]:
        params = {'area': self.area} if self.area else {}
        response = req.get(f'{self.api_url}/look/{self.domain}', params = params)
        if response.status_code == 200:
            results = response.json()
            return (f'Here are {len(results)} options available: {str(results)}', 0)
        return('No results found.', 2)
    
    def search(self, query: str) -> tuple[str, int]:
        params = self._parse_query(query)
        response = req.get(f'{self.api_url}/search/{self.domain}', params = params)
        if response.status_code == 200:
            results = response.json()
            if self.domain == 'hotel':
                fields = ['name', 'type', 'area', 'pricerange', 'stars', 'parking', 'internet', 'phone']
            else:
                fields = ['name', 'food', 'area', 'pricerange', 'phone']
            clean = [
                {k: r[k] for k in fields if k in r}
                for r in results[:5]
            ]
            return (f"Here are {len(clean)} results matching your query: {str(clean)}", 0)
        elif response.status_code == 404:
            return ("No items matching the query have been found.", 2)
        return ("No items have been retrieved as the query has invalid syntax.", 1)
    
    def _parse_query(self, query: str) -> dict:
        """
        Converts the model's query string into API parameters.
        Ex: "stars=='3' and pricerange=='cheap'" → {"stars": "3", "pricerange": "cheap"}
        """
        params = {}
        matches = re.findall(r"(\w+)==['\"]?([^'\"&\s]+)['\"]?", query)
        for key, value in matches:
            if ',' in value:
                params[key] = [v.strip() for v in value.split(',')] #List of values
            else:
                params[key] = value
        return params
    
    def action(self, action: str) -> tuple[str, bool, Literal[0, 1, 2]]:
        """
        Perform an action based on the provided action string.

        Args:
            action (str): The action to be performed. It should be a string that
                          specifies the action to be taken. Valid actions include:
                          - "search[<query>]": Perform a search with the given query.
                          - "look[]": Perform a look action.

        Returns:
            tuple: A tuple containing:
                - str: The result of the action.
                - bool: A boolean indicating whether the conversation has finished.
                - int: 0 for correct performed action, 1 for incorrect performed action,
                  2 correctly performed but empty outcome.
        """
        try:
            done = False
            action = action.strip()
            action = action[0].lower() + action[1:]

            if action.startswith("search[") and action.endswith("]"):
                answer, return_code = self.search(action[7:-1])
            elif action == "look[]":
                answer, return_code = self.look()
            elif action.startswith("finish[") and action.endswith("]"):
                answer = action[7:-1]
                done = True
                return_code = 0
            else:
                answer = "Invalid action. Available actions: Search[query], Look[], Finish[answer]."
                return_code = 1

            return (answer, done, return_code)
        except Exception:
            return ("An error occurred while performing the action.", False, 1)
        
def react_process(prompt: str,
                question: str,
                scene: TravelScene,
                client: str = None,
                model: str = None,
                verbose: bool = True,
                max_rounds: int = 8) -> dict:

    dialogue = {}
    forced_finish = False
    num_rounds: int

    def llm(start_text: str, stop: list[str] = None) -> str:
        response = client.chat.completions.create(
            model = model,
            messages = [{'role': 'user', 'content': start_text}],
            max_tokens = 200,
            stop=stop[:4] if stop else None 
        )
        result = response.choices[0].message.content
        # Avoid the trailing end of the "User:", "Observation:", etc.
        for s in stop:
            if result.endswith(s):
                result = result[:result.rfind(s)]
        return result
    
    previous_text = prompt + "\n" + question + '\n'
    num_calls, num_badcalls = 0, 0

    for i in range(1, max_rounds):
        num_calls += 1
        current_turn_generation: Literal["try", "except"] = "try"

        thought_action = llm(previous_text + f"Thought {i}:",
                             stop=[f"\nObservation {i}:", "\nUser:", "\nSystem:", "<|eot_id|>", "]\n"])
        try:
            thought, action = thought_action.strip().split(f"\nAction {i}: ")
            thought = thought.replace(f"Thought {i}:", "").strip() #Eliminate thought duplicate
            if verbose: print("  \033[32;1;22mThought " + str(i) + "\033[0m: " + thought.replace('\n', ' ') + "\n  \033[32;1;22mAction " + str(i) + "\033[0m: " + action) # Perfect interaction print (green thought and action)
        except:
            # Sometimes the model will not generate and action, therefore we take what is already generated as the thought
            # and force the generation of an action.
            if verbose: print("  \033[31;1;22mThought " + str(i) + "\033[0m: " + thought_action.replace('\n', ' ')) # No action was generated (red thought)

            num_badcalls += 1
            num_calls += 1
            current_turn_generation = "except"

            thought = thought_action.strip().split('\n')[0] # Just take the first line of the thought
            action = llm(previous_text + f"Thought {i}: {thought}\nAction {i}:",
                         stop=[f"\n", "<|eot_id|>"]).strip()

            if verbose: print("  \033[33;1;22mThought " + str(i) + "\033[0m: " + thought[-150:].replace('\n', ' ') + "\n  \033[33;1;22mAction " + str(i) + "\033[0m: " + action) # Backup thought and action print (yellow thought and action)

        observation, is_done, return_code = scene.action(action) # Execute the action
        observation = observation.replace('\\n', '')
        if verbose and not is_done:
            match return_code:
                case 0:
                    color = "\033[32;1;22m"
                case 1:
                    color = "\033[31;1;22m"
                    num_badcalls += 1
                case 2:
                    color = "\033[33;1;22m"
            print(f"  {color}Observation {i}\033[0m: {observation}") # Result of the observation (green with content, red with error, yellow with empty)
        else:
            if return_code == 1:
                num_badcalls += 1

        # Save the current interaction
        current_step_text = f"Thought {i}: {thought}\nAction {i}: {action}\nObservation {i}: {observation}\n"
        dialogue[i] = {'thought': thought, 'action': action, 'observation': observation, 'mode': current_turn_generation}
        previous_text += current_step_text
        
        if is_done: # If Finish already present, no need for more interactions
            num_rounds = i
            break

    if not is_done:
        observation, is_done, return_code = scene.action("finish[]")
        forced_finish = True
        num_rounds = i + 1
        if verbose: print(f"  \033[31;1;22mForced finish.\033[0m")

    return {'final_answer': observation,
            "question": question,
            'forced_finish': forced_finish,
            'num_rounds': num_rounds,
            'num_calls': num_calls,
            'num_badcalls': num_badcalls,
            'dialogue': dialogue,
            'all_conversation': previous_text}