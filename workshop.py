""" Module to simulate a workshop session with large language models """
import json
import random
import sys
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List

import jsonschema
import yaml
from ollama import Client, show as llmshow
from rich import print as rprint
from rich.console import Console
from rich.pretty import Pretty
from rich.prompt import Prompt

from llm_interface import LLMInterface
from participant import Participant
from dataclasses import dataclass


@dataclass
class TranscriptEntry:
    round: int
    turn: int
    participant_uuid: str
    content: str

    
    def __str__(self):
        return f"{self.round}:{self.turn}:{self.participant_uuid}:{self.content}"

console = Console()



class WorkshopState(Enum):
    """ Enum for the workshop state """
    NOT_STARTED = 0
    STARTED = 1
    ENDING = 2


class Workshop:
    """ Main class for the workshop """
    def __init__(self, llm_client, context_length=4000):
        self.llm = llm_client
        self.transcript_content: List[TranscriptEntry] = []
        self.control_feedback: List[str] = []
        self.global_config: Dict[str, Any] = {}
        self.participants: List[Participant] = []
        self.facilitator: Participant = None
        self.current_participant_index: int = -1
        self.state: WorkshopState = WorkshopState.NOT_STARTED
        self.previous_participant: Participant = None
        self.current_turn: int = 0
        self.tokens_used: int = 0
        self.context_length : int = context_length
        self.current_round : int= 0
        
    def get_transcript(self) -> List[str]:
        """
        Retrieves the full transcript as a list of strings.

        Returns:
            List[str]: The full transcript.
        """
        return [str(entry) for entry in self.transcript_content]
    
    def get_participant_by_uuid(self, uuid):
        for participant in self.participants:
            if participant.uuid == uuid:
                return participant
        return None

    def get_state(self) -> WorkshopState:
        """ Getter for the workshop state """
        return self.state

    def save_state(self, filename: str = "workshop_state.json"):
        """ Save the state to JSON, in a restartable format """
        state = {
            "transcript_content": [asdict(t) for t in self.transcript_content],
            "control_feedback": self.control_feedback,
            "global_config": self.global_config,
            "participants": [asdict(p) for p in self.participants],
            "facilitator": asdict(self.facilitator) if self.facilitator else None,
            "current_participant_index": self.current_participant_index,
            "state": self.state.value,
            "previous_participant": (
                asdict(self.previous_participant) if self.previous_participant else None
            ),
            "current_turn": self.current_turn,
            "tokens_used": self.tokens_used,
            "context_length": self.context_length,
            "current_round": self.current_round,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load_state(self, filename: str = "workshop_state.json"):
        """ Load the state from JSON """
        with open(filename, "r", encoding="utf-8") as f:
            state = json.load(f)

        self.transcript_content = [TranscriptEntry(**t) for t in state["transcript_content"]]
        self.control_feedback = state["control_feedback"]
        self.global_config = state["global_config"]
        self.participants = [Participant(**p) for p in state["participants"]]
        self.facilitator = (
            Participant(**state["facilitator"]) if state["facilitator"] else None
        )
        self.current_participant_index = state["current_participant_index"]
        self.state = WorkshopState(state["state"])
        self.previous_participant = (
            Participant(**state["previous_participant"])
            if state["previous_participant"]
            else None
        )
        self.current_turn = state["current_turn"]
        self.tokens_used = state["tokens_used"]
        self.context_length = state["context_length"]
        self.current_round = state["current_round"]

    def extract_participants(self):
        """ Extract participants from the configuration and instantiate as objects """
        if "participants" in self.global_config:
            for p_data in self.global_config["participants"]:
                participant = Participant(
                    name=p_data["name"],
                    role=p_data["role"],
                    background=p_data.get("background", ""),
                    is_facilitator=p_data.get("is_facilitator", False),
                )
                if participant.is_facilitator:
                    self.facilitator = participant
                else:
                    self.participants.append(participant)

        if not self.facilitator:
            self.control_feedback.append(
                "Warning: No facilitator defined. First participant will be set as facilitator."
            )
            if self.participants:
                self.facilitator = self.participants.pop(0)
                self.facilitator.is_facilitator = True

        random.shuffle(self.participants)

    def load_yaml(self, file_path: str) -> Dict[str, Any]:
        """ Load YAML config file to build a full config """
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def load_json_schema(self, file_path: str) -> Dict[str, Any]:
        """ Load JSON schema file to validate the config """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format in {file_path}: {e}")

    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]):
        """ Validate the config against the schema """
        jsonschema.validate(instance=config, schema=schema)

    def merge_configs(self, configs: list[Dict[str, Any]]) -> Dict[str, Any]:
        """ Merge multiple configs into one """
        merged_config = {}
        for config in configs:
            for key, value in config.items():
                if isinstance(value, list):
                    if key not in merged_config:
                        merged_config[key] = []
                    merged_config[key].extend(value)
                elif isinstance(value, dict):
                    if key not in merged_config:
                        merged_config[key] = {}
                    merged_config[key].update(value)
                else:
                    merged_config[key] = value
        return merged_config

    def handle_command(self, command):
        """ main command handler """
        if command.startswith("/"):
            parts = command[1:].split()
            cmd = parts[0]
            args = parts[1:]

            if cmd == "load":
                self.handle_load_command(args)
            elif cmd == "show":
                self.handle_show_command(args)
            elif cmd == "start":
                self.handle_start_command(args)
            elif cmd == "say":
                self.handle_say_command(args)
            elif cmd == "next":
                self.handle_next_command(args)
            elif cmd == "end":
                self.handle_endsession_command()
            elif cmd == "util":
                self.handle_util_command(args)
            elif cmd == "backup":
                self.handle_backup_command(args)
            elif cmd == "restore":
                self.handle_restore_command(args)
            elif cmd == "exit":
                self.handle_exit_command()
            else:
                self.control_feedback.append("Unknown command")
        else:
            self.control_feedback.append(
                "Invalid command format. Commands should start with '/'"
            )

    def handle_exit_command(self):
        """ Exit the workshop, but do not end the session """
        self.control_feedback.append("Exiting workshop.")
        self.handle_backup_command(["workshop_state.json"])
        sys.exit(0)
        

    def handle_backup_command(self, args):
        """ Handle commands """
        if len(args) == 1:
            filename = args[0]
            try:
                self.save_state(filename)
                self.control_feedback.append(f"Workshop state saved to '{filename}'.")
            except Exception as e:
                self.control_feedback.append(
                    f"Error saving workshop state to '{filename}': {e}"
                )
        else:
            self.control_feedback.append("Usage: /save [filename]")

    def handle_restore_command(self, args):
        """ Handle commands """
        if len(args) == 1:
            filename = args[0]
            try:
                self.load_state(filename)
                self.control_feedback.append(
                    f"Workshop state loaded from '{filename}'."
                )
            except Exception as e:
                self.control_feedback.append(
                    f"Error loading workshop state from '{filename}': {e}"
                )
        else:
            self.control_feedback.append("Usage: /load [filename]")

    def handle_load_command(self, args):
        """ Handle commands """
        if len(args) == 1:
            filename = args[0]
            try:
                new_config = self.load_yaml(filename)
                merged_config = self.merge_configs([self.global_config, new_config])
                schema = self.load_json_schema("schema.json")
                self.validate_config(merged_config, schema)
                self.global_config.update(merged_config)

                self.control_feedback.append(
                    f"Configuration file '{filename}' loaded and merged."
                )
            except Exception as e:
                self.control_feedback.append(
                    f"Error loading configuration file '{filename}': {e}"
                )
        else:
            self.control_feedback.append("Usage: /load [filename]")

    def handle_show_command(self, args):
        """ Handle commands """
        self.control_feedback.append("Current configuration:")
        pretty_config = Pretty(self.global_config)
        self.control_feedback.append(pretty_config)

    def handle_start_command(self, args):
        """ Start the workshop """
        if self.state == WorkshopState.STARTED:
            self.control_feedback.append("Workshop is already in progress.")
            return

        if not self.global_config.get("workshop", {}).get("name"):
            self.control_feedback.append(
                "Please create a workshop via loading config before starting."
            )
            return

        self.extract_participants()

        if not self.participants:
            self.control_feedback.append(
                "No participants found. Please load a configuration with participants."
            )
            return

        prompt = (
            " ".join(args)
            if args
            else f"Let's begin our workshop session. {self.global_config['workshop']}"
        )
        self.control_feedback.append(
            "Workshop started. Use /next to proceed with turns."
        )
        self.state = WorkshopState.STARTED
        self.take_facilitator_turn(prompt)

    def handle_say_command(self, args):
        """ Say something to the participants as facilitor """
        if len(args) >= 1:
            content = " ".join(args)

            prompt = f"""
            [CONTEXT]
                You are participating in a workshop as facilitator, here are the details {self.global_config}
                Here is the transcript so far : {self.get_transcript()}
              [/CONTEXT]
              [INSTRUCTIONS]
                Say this '{content}' in your voice.
              [/INSTRUCTIONS]
              [GUIDANCE]
                Be concise, be clear, and be authentic to your persona.
              [/GUIDANCE]
            """
            self.take_facilitator_turn(prompt)
        else:
            self.control_feedback.append("Usage: /say [content]")

    def handle_next_command(self, args=[]):
        """ main action to start new truns """
        if not self.state == WorkshopState.STARTED:
            self.control_feedback.append(
                "Workshop hasn't started. Use /start to begin the workshop."
            )
            return

        # Default behavior: take 1 turn or auto run a few turns
        turn_to_take = 1
        if args and args[0].isdigit():
            turn_to_take = int(args[0])
            args = args[1:]  # Remove the number from args

        next_participant = None
        for _ in range(turn_to_take):
            if not args:
                # Default behavior: pick random but not last
                available_participants = [
                    p for p in self.participants if p != self.previous_participant
                ]
                if not available_participants:
                    available_participants = self.participants
                next_participant = random.choice(available_participants)
            elif args[0] == "?":
                # Use LLM to determine who should be next
                next_participant = self.llm_pick_participant()
            else:
                # nominate
                # Try to find a participant that starts with the given string
                next_participant = self.pick_participant_by_name(args[0])

            if next_participant:
                self.take_participant_turn(next_participant)

    def pick_participant_by_name(self, name):
        """ Pick the next participant based on a name """
        next_participant = None
        matching_participants = [
            p for p in self.participants if p.name.lower().startswith(name.lower())
        ]
        if matching_participants:
            next_participant = matching_participants[0]
        else:
            self.control_feedback.append(
                f"No participant found whose name starts with '{name}'"
            )

        return next_participant

    def llm_pick_participant(self):
        """ Pick the next participant based assessment of the conversation flow """
        prompt = f"""
        [CONTEXT]
          You are an AI assistant helping to manage a workshop. Here are the workshop details: {self.global_config}
          Here is the transcript so far: {self.get_transcript()}
        [/CONTEXT]
        [INSTRUCTIONS]
          Based on the conversation flow and content, suggest which participant should speak next.
          Consider factors like:
          - Who was asked a direct question
          - Who might have relevant expertise for the current topic
          - Who hasn't spoken in a while
        [/INSTRUCTIONS]
        [CONSTRAINTS]
          - Suggested participant must be a participant in the workshop
          - Suggested participant must not be the same as the previous speaker
          - Suggested participant must not be the facilitator
          - Suggested participant must not be the same as the current speaker
          - Only Respond in the format: 'Next speaker: Participant Name'
          - Any other response format will fail.
        [/CONSTRAINTS]
        """
        suggestion = self.llm.get_response(
            prompt=prompt,
            system_message=f"You analyse conversations and provide a single name.",get_tokens=False,
        )
        suggested_name = suggestion.split("Next speaker:")[-1].strip()

        next_participant = self.pick_participant_by_name(suggested_name)
        return next_participant or None

    def handle_endsession_command(self):
        """ End the workshop """
        self.control_feedback.append("Workshop session ended.")
        self.state = WorkshopState.ENDING

    # def handle_view_transcript_command(self):
    #     self.control_feedback.append("Opening full transcript...")
    #     transcript_file = Path("transcript.txt")
    #     with transcript_file.open("w") as f:
    #         f.write("\n".join(self.transcript_content))
    #     os.system(f"notepad {transcript_file}")

    # def get_responsefrom_llm(self, prompt, participant):
    #     response = self.llm_client.get_response(prompt=prompt, system_message=f"You're persona is {participant}.")

    #     # save prompt and reponse to last_response.txt, overwrite each time
    #     with open("last_response.txt", "w") as f:
    #         f.write(f"Prompt: {prompt}\nResponse: {response['message']['content']}")

    #     return response["message"]["content"]

    def take_facilitator_turn(self, prompt):
        """ Take the facilitator turn"""
        self.previous_participant = self.facilitator
        self.current_turn += 1
        prompt = f"""
        [CONTEXT]
          You are the workshop facilitator!
          Here are the workshop details: {self.global_config}
          Here is the transcript so far: {self.get_transcript()}
        [/CONTEXT]
        [INSTRUCTIONS]
          Review the transcript and the goals.
          Use your skill to ask open-ended questions to keep the conversation flow going.
        [/INSTRUCTIONS]
        """

        response, tokens = self.facilitator.generate_response(
            self.llm, self.global_config, self.get_transcript(), prompt=prompt,
        )

        entry=TranscriptEntry(round=self.current_round,turn=self.current_turn,participant_uuid=self.facilitator.uuid,content=response)
        self.transcript_content.append(entry)
        self.control_feedback.append(
            f"{self.facilitator.name} (F) has spoken. Use /next to continue."
        )
        self.tokens_used = tokens

    def take_participant_turn(self, participant=None):
        """ Take the participant turn """
        if participant is None:
            return

        self.previous_participant = participant
        self.current_turn += 1
        participant.update_stats(self.current_turn)

        participant_response, tokens = participant.generate_response(llm=self.llm, workshop_context=self.global_config, transcript=self.get_transcript(), prompt=None)
        
        entry=TranscriptEntry(round=self.current_round,turn=self.current_turn,participant_uuid=participant.uuid,content=participant_response)
        self.transcript_content.append(entry)

        self.control_feedback.append(
            f"{participant.name} has spoken. Use /next to continue."
        )
        self.tokens_used = tokens

    def display_transcript(self):
        """ Display the transcript """
        console.clear()
        console.print("[bold green]Transcript:[/bold green]")
        for entry in self.transcript_content[-20:]:
            participant=self.get_participant_by_uuid(entry.participant_uuid)
            rprint(f"[blue]{entry.round}.{entry.round}[/blue][bold blue]{entry.participant_uuid}[/bold blue]: {entry.content}")

        with open("latest_transcript.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(self.get_transcript()))

    def display_control_feedback(self):
        """ Display the control feedback """
        console.print("\n[bold red]Control Messages:[/bold red]")
        for line in self.control_feedback[-5:]:
            console.print(line)

    def handle_util_command(self, args):
        """ Handle commands """
        if not args:
            self.control_feedback.append("Usage: /util [action] [parameters]")
            return

        action = args[0]
        params = args[1:]
        if action == "summerize":
            prompt = f"""
              [TASK]
                Compress the following content, the goal is to reduce tokens, without losing information.
              [/TASK]
              [GUIDANCE]
                Prioritise key predicates, ideas, insights, and conclusions.
                Discard irrelevant information.
              [/GUIDANCE]
              [CONTENT]
                {self.get_transcript()}
              [/CONTENT]
              """
            response = self.llm.get_response(
                prompt=prompt,
                system_message=f"You are a summarizer, you compress text.",
            )
            summary = response["message"]["content"]
            with open("summary.txt", "w") as f:
                f.write(summary)
        else:
            self.control_feedback.append(f"Unknown util action: {action}")


def main(arg):
    """ main function to run the workshop """
    model="phi3:latest"

    llm = LLMInterface(
        client=Client(host="http://localhost:11434"), model=model
    )
    workshop = Workshop(llm_client=llm, context_length=32000)


    if arg and arg.endswith(".json"):
        workshop.load_state(arg)
        print(f"Loaded workshop state from {arg}")
    elif arg:
        print(f"Loading configuration file {arg}")
        workshop.handle_load_command([arg])

    ## Main Turn Loop
    while workshop.get_state() != WorkshopState.ENDING:
        try:
            workshop.display_transcript()
            workshop.display_control_feedback()
            command = Prompt.ask("\n>>>")
            workshop.handle_command(command)
            workshop.save_state("final_state.json")  # Save final state when exiting
        except KeyboardInterrupt:
            workshop.handle_command("/exit")

    workshop.save_state("final_state.json")
    print("Workshop ended. Final state saved.")

    workshop.save_state("final_state.json")  # Save final state when exiting
    print("Workshop ended. Final state saved.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
