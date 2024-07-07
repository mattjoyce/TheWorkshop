import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
from participant import Participant

@dataclass
class WorkshopState:
    transcript_content: List[str] = field(default_factory=list)
    control_feedback: List[str] = field(default_factory=list)
    global_config: Dict[str, Any] = field(default_factory=dict)
    participants: List[Participant] = field(default_factory=list)
    facilitator: Participant = None
    current_participant_index: int = -1
    workshop_started: bool = False
    previous_participant: Participant = None
    current_turn: int = 0

    def to_json(self):
        state_dict = asdict(self)
        state_dict['facilitator'] = asdict(self.facilitator) if self.facilitator else None
        state_dict['participants'] = [asdict(p) for p in self.participants]
        state_dict['previous_participant'] = asdict(self.previous_participant) if self.previous_participant else None
        return json.dumps(state_dict, indent=2)

    @classmethod
    def from_json(cls, json_str):
        state_dict = json.loads(json_str)
        state = cls(**state_dict)
        state.facilitator = Participant(**state_dict['facilitator']) if state_dict['facilitator'] else None
        state.participants = [Participant(**p) for p in state_dict['participants']]
        state.previous_participant = Participant(**state_dict['previous_participant']) if state_dict['previous_participant'] else None
        return state

def save_state(state: WorkshopState, filename: str = 'workshop_state.json'):
    with open(filename, 'w') as f:
        f.write(state.to_json())

def load_state(filename: str = 'workshop_state.json') -> WorkshopState:
    with open(filename, 'r') as f:
        return WorkshopState.from_json(f.read())