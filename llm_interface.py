class LLMInterface:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def get_response(self, prompt, system_message=""):
        response = self.client.chat(
            model=self.model,
            keep_alive=600,
            options={"temperature": 0.7, "num_gpu": -1},
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        return response['message']['content']