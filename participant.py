""" Participant module for the workshop"""
from dataclasses import dataclass, field
from llm_interface import LLMInterface
import uuid
import json

@dataclass
class Participant:
    """Participant class for the workshop"""
    name: str
    role: str
    background: str
    is_facilitator: bool = False
    contributions: int = 0
    last_spoke_turn: int = 0
    mood: str = "neutral"
    prompts: list = field(default_factory=list)
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))


    def add_prompt(self, name:str, prompt: str):
        """Add a prompt to the participant's prompts list"""
        self.prompts.append({"name": name, "prompt": prompt})

    def update_stats(self, current_turn):
        """Update the participant's stats based on the current turn"""
        self.contributions += 1
        self.last_spoke_turn = current_turn

    def generate_bio(self, full: bool = False) -> str:
        """Generate a bio for the participant"""
        if full:
            return f"{self.name}, {self.role}. {self.background}"
        return f"{self.name}, {self.role}"

    def get_context_for_llm(self) -> dict:
        """Get the context for the participant for the LLM"""
        return {
            "name": self.name,
            "role": self.role,
            "background": self.background,
            "contributions": self.contributions,
            "mood": self.mood
        }

    def update_mood(self, new_mood: str):
        """Update the participant's mood based on the new mood"""
        self.mood = new_mood

    def turns_since_last_contribution(self, current_turn: int) -> int:
        """Calculate the number of turns since the last contribution"""
        return current_turn - self.last_spoke_turn

    def generate_response(self, llm: LLMInterface, workshop_context: dict, transcript: list, prompt:str):
        """Generate a response for the participant based on the LLM and the prompt"""
        default_prompt = f"""
          [CONTEXT]
            This is you: {self.get_context_for_llm()}
            You are participating in this workshop: {workshop_context}
            Here is the transcript so far: {transcript}
          [/CONTEXT]

          [INSTRUCTIONS]
            It's your turn to shine. Contribute to the scene by asking a question, challenging a point, or making a comment relevant to the discussion.
          [/INSTRUCTIONS]

          [GUIDENCE]
            - Always be concise and clear in your lines.
            - Always stay true to your character.
            - Always be mindful of the conversation 
            - Always speak in the first person.
            - Never break the fourth wall by mentioning the context or your persona explicitly.
            - Never Stray from your character.
            - Never Impersonate another participant.
            - Never share more than one contribution.
          [/GUIDENCE]

        """

        if prompt is None:
            prompt = default_prompt

        response, tokens = llm.get_response(prompt, system_message=f"You're persona is {self.name}, a willing participant in a workshop.",get_tokens=True)
        with open(f"state/participant_{self.name}_reponse.txt", "a") as f:
          f.write(
              f"Participant: {self.name}\nPrompt: {prompt}\nResponse: {response}"
          )

        check=self.check_reponse(llm, response, self.name)
        if check:
            response = f"PASS: {response}"
        else:
            response = f"FAIL: {response}"


        return response, tokens
    
    def check_reponse(self, llm: LLMInterface, response: str, name: str) -> bool:
        """Check if the response is relevant to the prompt"""
        # use llm to chgeck the previous response is compliant with the prompt
        prompt = f"""We have recived a response from {name}, a workshop participate.
        Here's the guidence we provided.
          [GUIDENCE]
            - Always be concise and clear in your lines.
            - Always stay true to your character.
            - Always be mindful of the conversation 
            - Always speak in the first person.
            - Never break the fourth wall by mentioning the context or your persona explicitly.
            - Never Stray from your character.
            - Never Impersonate another participant.
            - Never share more than one contribution.
          [/GUIDENCE]
        
        
        Heres' the response:
        [RESPONSE]
        {response}
        [/RESPONSE]

        You your task is do judge the response.
        [TASK format=json]
                If the response violates guidance, prefix you judgement with FAIL.
                If the response is in compliance, prefix you judgement with PASS.
        [/TASK]
        """

        response, tokens = llm.get_response(prompt, system_message=f"You are a checker bot.",get_tokens=True)
        print("Checking")
        with open(f"state/checker_reponse.txt", "a") as f:
            f.write(json.dumps({"prompt": prompt, "response": response, "tokens": tokens}, indent=4))

        if response.lstrip().lower()[:4] == "pass":
            return True
        else:
            return False