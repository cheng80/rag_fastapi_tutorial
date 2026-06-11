import requests

from app.core.config import Settings


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_chat_model
        self.timeout = settings.ollama_request_timeout

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "think": self.settings.llm_think,
                "keep_alive": self.settings.ollama_keep_alive,
                "options": {
                    "temperature": self.settings.llm_temperature,
                    "num_predict": self.settings.llm_num_predict,
                },
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        answer = data.get("response")
        if not isinstance(answer, str):
            raise RuntimeError(f"Ollama 생성 응답 형식이 올바르지 않습니다: {data}")

        return answer.strip()
