# TheWorkshop

TheWorkshop is a Python-based tool designed to facilitate and manage workshops using an LLM (Large Language Model). It supports various commands to create, load, list, remove, show configurations, and control the flow of the workshop, including participant interactions and session management.
Features

    Participant and Facilitator Management: Add and manage participants and facilitators.
    Configuration Loading: Load workshop configurations from YAML files.
    Schema Validation: Validate configurations against a predefined JSON schema.
    Workshop Commands: Control workshop flow with commands like /new, /load, /list, /remove, /show, /start, /say, /next, /endsession, /view_transcript, and /util.
    Transcript Management: Keep track of the workshop transcript and view the latest updates.
    LLM Integration: Use an LLM to suggest next speakers, facilitate turns, and summarize content.

## Installation

Ensure you have the following dependencies installed:

    Python 3.x
    jsonschema
    PyYAML
    rich
    ollama (for LLM client)

You can install the required Python packages using pip:

bash

pip install jsonschema pyyaml rich ollama

Usage

    Initialize the Workshop:

    python

workshop = Workshop(llm_client=Client(host="http://localhost:11434"), llm_model="mistral:latest")

Run the Main Loop:

python

    if __name__ == "__main__":
        main()

    Available Commands:
        /new [workshop name]: Create a new workshop.
        /load [filename]: Load a configuration file.
        /list: List available configuration files.
        /remove [file number]: Remove a configuration file.
        /show: Show the current configuration.
        /start: Start the workshop.
        /say [content]: Facilitator says something.
        /next: Proceed to the next participant's turn.
        /endsession: End the current workshop session.
        /view_transcript: View the full transcript.
        /util [action] [parameters]: Execute a utility action (e.g., summarize transcript).

Example

To start a new workshop:

bash

/new MyWorkshop

To load a configuration file:

bash

/load config.yaml

To start the workshop:

bash

/start

To proceed to the next participant:

bash

/next

To view the transcript:

bash

/view_transcript

Contributing

Contributions are welcome! Please fork the repository and submit a pull request.
License

This project is licensed under the MIT License.