"""
LLM Client - Hỗ trợ nhiều providers:
- OpenAI-compatible (Mimo, OpenAI, custom)
- Google Gemini API (Gemma 4)
"""
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """Universal LLM client cho PokeMMO bot"""

    def __init__(self, config):
        """
        Args:
            config: LLMConfig instance từ config.py
        """
        self.config = config
        self.active = config.get_active_config()
        self.api_base = self.active["api_base"].rstrip("/")
        self.api_key = self.active["api_key"]
        self.model = self.active["model"]
        self.api_format = self.active["api_format"]

        if not self.api_key:
            raise ValueError(
                f"API key không được set cho provider '{config.provider}'. "
                f"Set env var hoặc truyền key trực tiếp."
            )

        logger.info(f"LLM Client initialized: provider={config.provider}, "
                     f"model={self.model}, format={self.api_format}")

    def chat(self, system_prompt: str, user_message: str,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        """
        Gửi message đến LLM và nhận response.

        Args:
            system_prompt: System instruction
            user_message: User message (game state JSON)
            temperature: Override temperature
            max_tokens: Override max_tokens

        Returns:
            LLM response text (string)
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        if self.api_format == "gemini":
            return self._call_gemini(system_prompt, user_message, temp, tokens)
        else:
            return self._call_openai_compat(system_prompt, user_message, temp, tokens)

    def chat_json(self, system_prompt: str, user_message: str,
                  temperature: Optional[float] = None,
                  max_tokens: Optional[int] = None) -> dict:
        """
        Gửi message và parse response thành JSON.

        Returns:
            Parsed JSON dict
        """
        response = self.chat(system_prompt, user_message, temperature, max_tokens)

        # Extract JSON from response (handle markdown code blocks)
        text = response.strip()
        if text.startswith("```"):
            # Remove markdown code block
            lines = text.split("\n")
            # Find opening and closing ```
            start = 1  # skip ```json
            end = len(lines) - 1
            for i, line in enumerate(lines):
                if i > 0 and line.strip().startswith("```"):
                    end = i
                    break
            text = "\n".join(lines[start:end])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            # Return fallback
            return {"action": "wait", "parameters": {"duration_ms": 1000},
                    "error": "failed_to_parse", "raw_response": response[:500]}

    def _call_openai_compat(self, system_prompt: str, user_message: str,
                            temperature: float, max_tokens: int) -> str:
        """Call OpenAI-compatible API (Mimo, OpenAI, custom)"""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers,
                                 timeout=self.config.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'

    def _call_gemini(self, system_prompt: str, user_message: str,
                     temperature: float, max_tokens: int) -> str:
        """Call Google Gemini API (for Gemma 4)"""
        url = (f"{self.api_base}/models/{self.model}:generateContent"
               f"?key={self.api_key}")

        headers = {"Content-Type": "application/json"}

        # Gemini API format: contents + systemInstruction
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers,
                                 timeout=self.config.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("No candidates in Gemini response")
                return '{"action": "wait", "parameters": {"duration_ms": 1000}}'

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                logger.warning("No parts in Gemini response")
                return '{"action": "wait", "parameters": {"duration_ms": 1000}}'

            return parts[0].get("text", "")

        except requests.exceptions.Timeout:
            logger.error("Gemini request timed out")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini request failed: {e}")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return '{"action": "wait", "parameters": {"duration_ms": 2000}}'


# === CONVENIENCE FUNCTIONS ===

def create_client(config) -> LLMClient:
    """Tạo LLM client từ config"""
    return LLMClient(config.llm)


def quick_test(provider: str = "gemma", api_key: str = "") -> bool:
    """Test nhanh kết nối LLM"""
    from config import LLMConfig

    llm_config = LLMConfig(provider=provider)
    if provider == "gemma":
        llm_config.gemma_api_key = api_key
    elif provider == "mimo":
        llm_config.mimo_api_key = api_key

    client = LLMClient(llm_config)

    response = client.chat(
        system_prompt="You are a helpful assistant. Reply in JSON.",
        user_message='Say hello in JSON format: {"message": "hello"}',
        max_tokens=100,
    )
    print(f"Response: {response}")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        quick_test(provider=sys.argv[1], api_key=sys.argv[2])
    else:
        print("Usage: python client.py <provider> <api_key>")
        print("Providers: gemma, mimo, openai, custom")
