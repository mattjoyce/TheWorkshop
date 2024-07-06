from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
import os
from pathlib import Path

console = Console()

# Create the layout
layout = Layout()

# Upper panel for the transcript
layout.split(
    Layout(name="transcript", ratio=3),
    Layout(name="command", ratio=1)
)

transcript_content = []
command_feedback = ""

def render_transcript_panel():
    content = "\n".join(transcript_content[-20:])  # Last 20 lines
    return Panel(content, title="Transcript", border_style="green")

def render_command_panel():
    return Panel(command_feedback, title="Command", border_style="blue")

layout["transcript"].update(render_transcript_panel())
layout["command"].update(render_command_panel())

def main():
    global command_feedback

    with Live(layout, refresh_per_second=10, screen=True):
        while True:
            try:
                command = console.input(">>> ")
                handle_command(command)
            except KeyboardInterrupt:
                break

def handle_command(command):
    global command_feedback
    if command.startswith("/"):
        parts = command[1:].split()
        cmd = parts[0]
        args = parts[1:]
        
        if cmd == "new":
            handle_new_command(args)
        elif cmd == "load":
            handle_load_command(args)
        elif cmd == "list":
            handle_list_command(args)
        elif cmd == "remove":
            handle_remove_command(args)
        elif cmd == "show":
            handle_show_command(args)
        elif cmd == "start":
            handle_start_command(args)
        elif cmd == "say":
            handle_say_command(args)
        elif cmd == "next":
            handle_next_command(args)
        elif cmd == "endsession":
            handle_endsession_command(args)
        elif cmd == "view_transcript":
            handle_view_transcript_command(args)
        else:
            command_feedback = "Unknown command"
    else:
        command_feedback = "Invalid command format. Commands should start with '/'"

    layout["command"].update(render_command_panel())

def handle_new_command(args):
    global transcript_content, command_feedback
    if len(args) == 1:
        workshop_name = args[0]
        transcript_content.append(f"New workshop '{workshop_name}' started.")
        command_feedback = f"Workshop '{workshop_name}' created."
        layout["transcript"].update(render_transcript_panel())
    else:
        command_feedback = "Usage: /new [workshop name]"

def handle_load_command(args):
    global transcript_content, command_feedback
    if len(args) == 1:
        filename = args[0]
        transcript_content.append(f"Loaded configuration from '{filename}'.")
        command_feedback = f"Configuration file '{filename}' loaded."
        layout["transcript"].update(render_transcript_panel())
    else:
        command_feedback = "Usage: /load [filename]"

def handle_list_command(args):
    global command_feedback
    # List loaded configuration files
    command_feedback = "Listing configuration files..."
    # Implement listing logic here

def handle_remove_command(args):
    global command_feedback
    # Remove a specific loaded file
    if len(args) == 1:
        file_number = args[0]
        command_feedback = f"Removing configuration file #{file_number}..."
        # Implement remove logic here
    else:
        command_feedback = "Usage: /remove [file number]"

def handle_show_command(args):
    global command_feedback
    # Display the current configuration
    command_feedback = "Current configuration:"
    # Implement show logic here

def handle_start_command(args):
    global transcript_content, command_feedback
    if len(args) >= 1:
        prompt = " ".join(args)
        transcript_content.append(f"Workshop started with prompt: {prompt}")
        command_feedback = "Workshop started."
        layout["transcript"].update(render_transcript_panel())
    else:
        command_feedback = "Usage: /start [prompt]"

def handle_say_command(args):
    global transcript_content, command_feedback
    if len(args) >= 1:
        content = " ".join(args)
        transcript_content.append(f"Facilitator: {content}")
        command_feedback = "Facilitator comment added."
        layout["transcript"].update(render_transcript_panel())
    else:
        command_feedback = "Usage: /say [content]"

def handle_next_command(args):
    global transcript_content, command_feedback
    transcript_content.append("Next participant's turn.")
    command_feedback = "Moved to next participant."
    layout["transcript"].update(render_transcript_panel())

def handle_endsession_command(args):
    global transcript_content, command_feedback
    transcript_content.append("Workshop session ended.")
    command_feedback = "Workshop session ended."
    layout["transcript"].update(render_transcript_panel())

def handle_view_transcript_command(args):
    global command_feedback
    command_feedback = "Opening full transcript..."
    # Save transcript to a file and open it
    transcript_file = Path("transcript.txt")
    with transcript_file.open("w") as f:
        f.write("\n".join(transcript_content))
    os.system(f"notepad {transcript_file}")

if __name__ == "__main__":
    main()
