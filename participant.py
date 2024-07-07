""" Participant module for the workshop"""
from dataclasses import dataclass, field
from llm_interface import LLMInterface
import uuid

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
            {self.get_context_for_llm()}
            You are participating in this workshop, {workshop_context}
            Here is the transcript so far : {transcript}
          [/CONTEXT]
          [INSTRUCTIONS]
            It's your turn to contribute, ask a question, challenge something, or make a comment.
          [/INSTRUCTIONS]
          [GUIDANCE]
            Be concise, be clear, and be authentic to your persona.
          [/GUIDANCE]
          """
        if prompt is None:
            prompt = default_prompt

        response, tokens = llm.get_response(prompt, system_message=f"You're persona is {self.name}, a willing participant in a workshop.",get_tokens=True)
        with open(f"state/participant_{self.name}_reponse.txt", "a") as f:
          f.write(
              f"Participant: {self.name}\nPrompt: {prompt}\nResponse: {response}"
          )
        return response, tokens