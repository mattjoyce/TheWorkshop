import json

class LLMInterface:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def get_response(self, prompt, system_message="", get_tokens=False):
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
        open("llm_response.txt", "w", encoding="utf-8").write(json.dumps(response, indent=4))

        if 'prompt_eval_count' in response:
            tokens = response['prompt_eval_count'] + response['eval_count']
        else:
            tokens = response['eval_count']

        if get_tokens:
            return response['message']['content'], tokens
        return response