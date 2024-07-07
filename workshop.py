import json
import os
import random
from pathlib import Path
from typing import Any, Dict
import sys

import jsonschema
import yaml
from ollama import Client
from rich import print as rprint
from rich.console import Console
from rich.pretty import Pretty
from rich.prompt import Prompt
from participant import Participant
from llm_interface import LLMInterface
from workshop_state import WorkshopState, save_state, load_state
console = Console()

class Workshop:
    def __init__(self, llm_client, state: WorkshopState = None):
        self.llm = llm_client
        if state:
            self.load_state(state)
        else:
            self.state = WorkshopState()

    def load_state(self, state: WorkshopState):
        self.state = state
        self.transcript_content = state.transcript_content
        self.control_feedback = state.control_feedback
        self.global_config = state.global_config
        self.participants = state.participants
        self.facilitator = state.facilitator
        self.current_participant_index = state.current_participant_index
        self.workshop_started = state.workshop_started
        self.previous_participant = state.previous_participant
        self.current_turn = state.current_turn

    def save_current_state(self, filename: str = 'workshop_state.json'):
        self.state.transcript_content = self.transcript_content
        self.state.control_feedback = self.control_feedback
        self.state.global_config = self.global_config
        self.state.participants = self.participants
        self.state.facilitator = self.facilitator
        self.state.current_participant_index = self.current_participant_index
        self.state.workshop_started = self.workshop_started
        self.state.previous_participant = self.previous_participant
        self.state.current_turn = self.current_turn
        save_state(self.state, filename)



    def extract_participants(self):
        if "participants" in self.global_config:
            for p_data in self.global_config["participants"]:
                participant = Participant(
                    name=p_data['name'],
                    role=p_data['role'],
                    background=p_data.get('background', ''),
                    is_facilitator=p_data.get('is_facilitator', False)
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
        with open(file_path, "r") as file:
            return yaml.safe_load(file)

    def load_json_schema(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format in {file_path}: {e}")

    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]):
        jsonschema.validate(instance=config, schema=schema)

    def merge_configs(self, configs: list[Dict[str, Any]]) -> Dict[str, Any]:
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
        if command.startswith("/"):
            parts = command[1:].split()
            cmd = parts[0]
            args = parts[1:]

            if cmd == "load":
                self.handle_load_command(args)
            elif cmd == "list":
                self.handle_list_command(args)
            elif cmd == "remove":
                self.handle_remove_command(args)
            elif cmd == "show":
                self.handle_show_command(args)
            elif cmd == "start":
                self.handle_start_command(args)
            elif cmd == "say":
                self.handle_say_command(args)
            elif cmd == "next":
                self.handle_next_command(args)
            elif cmd == "endsession":
                self.handle_endsession_command()
            elif cmd == "view_transcript":
                self.handle_view_transcript_command()
            elif cmd == "util":
                self.handle_util_command(args)
            else:
                self.control_feedback.append("Unknown command")
        else:
            self.control_feedback.append(
                "Invalid command format. Commands should start with '/'"
            )

    def handle_load_command(self, args):
        if len(args) == 1:
            filename = args[0]
            try:
                new_config = self.load_yaml(filename)
                merged_config = self.merge_configs([self.global_config, new_config])
                schema = self.load_json_schema("schema.json")
                self.validate_config(merged_config, schema)
                self.global_config.update(merged_config)
                self.transcript_content.append(
                    f"Loaded configuration from '{filename}'."
                )
                self.control_feedback.append(
                    f"Configuration file '{filename}' loaded and merged."
                )
            except Exception as e:
                self.control_feedback.append(
                    f"Error loading configuration file '{filename}': {e}"
                )
        else:
            self.control_feedback.append("Usage: /load [filename]")

    def handle_list_command(self, args):
        self.control_feedback.append("Listing configuration files...")
        # Implement listing logic here

    def handle_remove_command(self, args):
        if len(args) == 1:
            file_number = args[0]
            self.control_feedback.append(
                f"Removing configuration file #{file_number}..."
            )
            # Implement remove logic here
        else:
            self.control_feedback.append("Usage: /remove [file number]")

    def handle_show_command(self, args):
        self.control_feedback.append("Current configuration:")
        pretty_config = Pretty(self.global_config)
        self.control_feedback.append(pretty_config)

    def handle_start_command(self, args):
        if self.workshop_started:
            self.control_feedback.append("Workshop is already in progress.")
            return

        if not self.global_config.get("workshop", {}).get("name"):
            self.control_feedback.append(
                "Please create a workshop using /new before starting."
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
        self.transcript_content.append(f"Workshop started with prompt: {prompt}")
        self.control_feedback.append(
            "Workshop started. Use /next to proceed with turns."
        )
        self.workshop_started = True
        self.take_facilitator_turn(prompt)

    def handle_say_command(self, args):
        if len(args) >= 1:
            content = " ".join(args)

            prompt = f"""
            [CONTEXT]
                You are participating in a workshop as facilitator, here are the details {self.global_config}
                Here is the transcript so far : {self.transcript_content}
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
        if not self.workshop_started:
            self.control_feedback.append(
                "Workshop hasn't started. Use /start to begin the workshop."
            )
            return

        turns = 1
        if args and args[0].isdigit():
            turns = int(args[0])
            args = args[1:]  # Remove the number from args

        for _ in range(turns):
            if not args:
                # Default behavior: pick random but not last
                available_participants = [
                    p for p in self.participants if p != self.previous_participant
                ]
                if not available_participants:
                    available_participants = self.participants
                participant = random.choice(available_participants)
                self.take_participant_turn(participant)
            elif args[0] == "?":
                # Use LLM to determine who should be next
                self.take_llm_suggested_turn()
            else:
                # Try to find a participant that starts with the given string
                name_start = args[0].lower()
                matching_participants = [
                    p
                    for p in self.participants
                    if p["name"].lower().startswith(name_start)
                ]
                if matching_participants:
                    self.take_participant_turn(matching_participants[0])
                else:
                    self.control_feedback.append(
                        f"No participant found whose name starts with '{args[0]}'"
                    )
                    break  # Stop the loop if no matching participant is found

            # Optional: Add a small delay between turns
            # import time
            # time.sleep(1)

    def take_llm_suggested_turn(self):
        prompt = f"""
        [CONTEXT]
          You are an AI assistant helping to manage a workshop. Here are the workshop details: {self.global_config}
          Here is the transcript so far: {self.transcript_content}
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
        suggestion = self.llm.get_response(prompt=prompt, system_message=f"You analyse conversations and provide a single name.")
        suggested_name = suggestion.split("Next speaker:")[-1].strip()

        matching_participants = [
            p for p in self.participants if p.name.lower() == suggested_name.lower()
        ]
        if matching_participants:
            self.take_participant_turn(matching_participants[0])
        else:
            self.control_feedback.append(
                f"Suggested participant '{suggested_name}' not found. Choosing randomly."
            )
            self.handle_next_command()  # This will choose randomly

    def handle_endsession_command(self):
        self.transcript_content.append("Workshop session ended.")
        self.control_feedback.append("Workshop session ended.")

    def handle_view_transcript_command(self):
        self.control_feedback.append("Opening full transcript...")
        transcript_file = Path("transcript.txt")
        with transcript_file.open("w") as f:
            f.write("\n".join(self.transcript_content))
        os.system(f"notepad {transcript_file}")

    # def get_responsefrom_llm(self, prompt, participant):
    #     response = self.llm_client.get_response(prompt=prompt, system_message=f"You're persona is {participant}.")

    #     # save prompt and reponse to last_response.txt, overwrite each time
    #     with open("last_response.txt", "w") as f:
    #         f.write(f"Prompt: {prompt}\nResponse: {response['message']['content']}")

    #     return response["message"]["content"]

    def take_facilitator_turn(self, prompt):
        response = self.llm.get_response(prompt=prompt, system_message=f"You're persona is {self.facilitator}.")
        self.transcript_content.append(f"{self.facilitator.name}: {response}")
        self.control_feedback.append(
            f"Facilitator {self.facilitator.name} has spoken. Use /next to continue."
        )
        self.display_transcript()
        self.display_control_feedback()


    def take_participant_turn(self, participant=None):
        if participant is None:
            return

        self.previous_participant = participant
        self.current_turn += 1
        participant.update_stats(self.current_turn)
        
        participant_response = participant.generate_response(self.llm, self.global_config, self.transcript_content)

        self.transcript_content.append(f"{participant.name}: {participant_response}")
        self.control_feedback.append(
            f"{participant.name} has spoken. Use /next to continue."
        )
        self.display_transcript()
        self.display_control_feedback()

    def display_transcript(self):
        console.clear()
        console.print("[bold green]Transcript:[/bold green]")
        for line in self.transcript_content[-20:]:
            parts = line.split(": ", 1)
            if len(parts) == 2:
                rprint(f"[bold blue]{parts[0]}[/bold blue]: {parts[1]}")
            else:
                console.print(line)
        with open("latest_transcript.txt", "w") as f:
            f.write("\n".join(self.transcript_content))

    def display_control_feedback(self):
        console.print("\n[bold red]Control Messages:[/bold red]")
        for line in self.control_feedback[-5:]:
            console.print(line)

    def handle_util_command(self, args):
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
                {self.transcript_content}
              [/CONTENT]
              """
            response = self.llm_client.get_response(prompt=prompt, system_message=f"You are a summarizer, you compress text.")
            summary = response["message"]["content"]
            with open("summary.txt", "w") as f:
                f.write(summary)
        else:
            self.control_feedback.append(f"Unknown util action: {action}")


def main(arg):
    LLM = LLMInterface(client=Client(host="http://localhost:11434"), model="mistral:latest")
    workshop = Workshop(
        llm_client=LLM
    )
    if len(sys.argv) > 1:
        rprint(f"Loading configuration file {sys.argv[0]}")
        workshop.handle_load_command([sys.argv[1]])
    while True:
        try:
            workshop.display_transcript()
            workshop.display_control_feedback()

            command = Prompt.ask("\n>>>")

            workshop.handle_command(command)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
