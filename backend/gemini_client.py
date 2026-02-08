"""
Lightweight Gemini API Client for Decision Authority.
Replaces google-generativeai library to avoid heavy dependencies (grpcio, protobuf)
that require compilation on some environments.

Uses standard HTTP/REST API via requests/aiohttp.
"""

import os
import json
import asyncio
import time
from typing import Optional, List, Any

# Try to import aiohttp, fallback to requests if not available (though we prefer async)
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    import requests

class GenerationConfig:
    """Mimics genai.types.GenerationConfig"""
    def __init__(
        self, 
        temperature: float = 0.5, 
        max_output_tokens: int = 1000, 
        response_mime_type: str = "text/plain",
        candidate_count: int = 1,
        stop_sequences: Optional[List[str]] = None
    ):
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.response_mime_type = response_mime_type
        self.candidate_count = candidate_count
        self.stop_sequences = stop_sequences

class GeminiResponse:
    """Mimics genai.types.GenerateContentResponse"""
    def __init__(self, data: dict):
        self._data = data
        self.parts = []
        self._text = ""
        self.prompt_feedback = PromptFeedback(data.get("promptFeedback", {}))
        
        # Parse candidates
        candidates = data.get("candidates", [])
        if candidates:
            # Check for content
            content = candidates[0].get("content", {})
            parts_data = content.get("parts", [])
            
            # Extract text
            texts = [p.get("text", "") for p in parts_data if "text" in p]
            self._text = "".join(texts)
            self.parts = parts_data

    @property
    def text(self) -> str:
        if not self._text and self.prompt_feedback.block_reason:
            raise ValueError(f"Response blocked: {self.prompt_feedback.block_reason}")
        return self._text

class PromptFeedback:
    """Mimics prompt feedback object"""
    def __init__(self, data: dict):
        self.block_reason = data.get("blockReason")
        self.safety_ratings = data.get("safetyRatings", [])

class GenerativeModel:
    """Mimics genai.GenerativeModel"""
    def __init__(self, model_name: str):
        # Handle model name mapping if needed, generally strictly passes through
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_content_async(
        self, 
        prompt: str, 
        generation_config: Optional[GenerationConfig] = None
    ) -> GeminiResponse:
        """
        Generate content using REST API.
        Mimics the async interface.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        
        # Build request body
        body = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        if generation_config:
            gen_config_dict = {
                "temperature": generation_config.temperature,
                "maxOutputTokens": generation_config.max_output_tokens,
            }
            # API expects camelCase for MIME type, but some versions allow snake_case?
            # Let's map it explicitly
            if generation_config.response_mime_type:
                 gen_config_dict["responseMimeType"] = generation_config.response_mime_type
            
            body["generationConfig"] = gen_config_dict

        headers = {"Content-Type": "application/json"}

        # Execute request
        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body, headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        # try to parse error
                        try:
                            err_json = json.loads(text)
                            msg = err_json.get("error", {}).get("message", text)
                            code = err_json.get("error", {}).get("code", response.status)
                            # Propagate 429 as recognizable string for retry logic
                            if response.status == 429:
                                raise Exception(f"429 Resource exhausted: {msg}")
                            raise Exception(f"Gemini API Error {code}: {msg}")
                        except json.JSONDecodeError:
                            raise Exception(f"Gemini API Error {response.status}: {text}")
                    
                    data = await response.json()
                    return GeminiResponse(data)
        else:
            # Fallback to sync requests in thread
            import requests
            def _sync_request():
                resp = requests.post(url, json=body, headers=headers)
                return resp

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _sync_request)
            
            if response.status_code != 200:
                text = response.text
                try:
                    err_json = response.json()
                    msg = err_json.get("error", {}).get("message", text)
                    if response.status_code == 429:
                         raise Exception(f"429 Resource exhausted: {msg}")
                    raise Exception(f"Gemini API Error {response.status_code}: {msg}")
                except:
                     raise Exception(f"Gemini API Error {response.status_code}: {text}")
            
            return GeminiResponse(response.json())

# Module level configuration (mimics genai.configure)
def configure(api_key: str):
    os.environ["GEMINI_API_KEY"] = api_key

# Module level types (mimics genai.types)
class types:
    GenerationConfig = GenerationConfig
