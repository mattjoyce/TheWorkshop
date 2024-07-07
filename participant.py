from dataclasses import dataclass, field
from llm_interface import LLMInterface

@dataclass
class Participant:
    name: str
    role: str
    background: str
    is_facilitator: bool = False
    contributions: int = 0
    last_spoke_turn: int = 0
    mood: str = "neutral"
    prompts: list = field(default_factory=list)

    def add_prompt(self, name:str, prompt: str):
        self.prompts.append({"name": name, "prompt": prompt})

    def update_stats(self, current_turn):
        self.contributions += 1
        self.last_spoke_turn = current_turn

    def generate_bio(self, full: bool = False) -> str:
        if full:
            return f"{self.name}, {self.role}. {self.background}"
        return f"{self.name}, {self.role}"

    def get_context_for_llm(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "background": self.background,
            "contributions": self.contributions,
            "mood": self.mood
        }

    def update_mood(self, new_mood: str):
        self.mood = new_mood

    def turns_since_last_contribution(self, current_turn: int) -> int:
        return current_turn - self.last_spoke_turn

    def generate_response(self, llm: LLMInterface, workshop_context: dict, transcript: list):
        prompt = f"""
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
        participant_response = llm.get_response(prompt, f"You're persona is {self.name}, a willing participant in a workshop.")
        with open(f"state/participant_{self.name}_reponse.txt", "a") as f:
          f.write(
              f"Participant: {self.name}\nPrompt: {prompt}\nResponse: {participant_response}"
          )
        return participant_response