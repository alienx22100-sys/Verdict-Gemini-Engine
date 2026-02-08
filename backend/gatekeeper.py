"""
Input Gatekeeper for Decision Authority.
Extracts structured decision fields from user input using Gemini 3.
"""

import gemini_client as genai
import json
import re
from typing import Union

from config import Config
from models import (
    DecisionObject, 
    CompleteDecision, 
    IncompleteDecision,
    IrreversibleType
)


class InputGatekeeper:
    """
    Gatekeeper that extracts decision fields from user input.
    Uses Gemini 3 ONCE to parse the input into structured fields.
    """
    
    EXTRACTION_PROMPT = """You are a decision field extractor. Extract ONLY these fields from the user's input:

1. goal: What they want to achieve
2. cost: What they must sacrifice/invest (money, time, effort, relationships, etc.)
3. risk: What could go wrong
4. irreversible: "yes", "no", or "partial"

RULES:
- Extract what is explicitly stated OR IMPLIED by the context
- If a field is missing, make a REASONABLE INFERENCE based on the scenario
- Only set to "UNCLEAR" if it is impossible to infer
- Do NOT judge the decision
- Output ONLY valid JSON, nothing else

USER INPUT:
{input}

OUTPUT FORMAT (JSON only):
{{"goal": "...", "cost": "...", "risk": "...", "irreversible": "yes|no|partial"}}"""

    MISSING_FIELD_QUESTIONS = {
        "goal": "What specific outcome are you trying to achieve?",
        "cost": "What will you sacrifice or invest? (money, time, effort, etc.)",
        "risk": "What could go wrong with this decision?",
        "irreversible": "Can this decision be undone? (yes / no / partially)"
    }

    def __init__(self):
        """Initialize the gatekeeper with Gemini configuration."""
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None

    async def extract_decision_object(
        self, 
        user_input: str,
        max_retries: int = 2
    ) -> Union[CompleteDecision, IncompleteDecision]:
        """
        Extract decision fields from user input.
        Returns CompleteDecision if all fields are present,
        or IncompleteDecision with the first missing field.
        """
        import asyncio
        
        if not self.model:
            raise ValueError("Gemini API not configured. Set GEMINI_API_KEY.")
        
        # Call Gemini to extract fields
        prompt = self.EXTRACTION_PROMPT.format(input=user_input)
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                print(f"DEBUG: Gatekeeper attempt {attempt + 1}/{max_retries + 1}")
                
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=1500,
                        response_mime_type="application/json"
                    )
                )
                
                # Parse JSON response
                extracted = self._parse_json_response(response.text)
                
                # Validate completeness
                return self._validate_fields(extracted)
                
            except Exception as e:
                last_error = e
                print(f"DEBUG: Gatekeeper attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1.5  # 1.5s, 3s backoff
                    print(f"DEBUG: Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        raise ValueError(f"Failed to extract decision fields after {max_retries + 1} attempts: {str(last_error)}")

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from Gemini response, with robust error handling."""
        text = response_text.strip()
        
        # 1. Remove markdown code blocks if present
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = text.replace("```", "").strip()
        
        # 2. Try standard JSON load
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 3. Aggressive cleanup
        try:
            clean = text.replace("True", "true").replace("False", "false").replace("None", "null")
            clean = re.sub(r"//.*$", "", clean, flags=re.MULTILINE)
            
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                clean = match.group()
            
            clean = re.sub(r",\s*}", "}", clean)
            clean = re.sub(r",\s*]", "]", clean)
            
            return json.loads(clean)
        except (json.JSONDecodeError, Exception):
            pass
        
        # 4. Attempt to repair truncated JSON
        try:
            repaired = self._repair_truncated_json(text)
            if repaired:
                return json.loads(repaired)
        except:
            pass
        
        raise ValueError(f"Could not parse JSON from response: {text[:200]}...")
    
    def _repair_truncated_json(self, text: str) -> str:
        """Attempt to repair truncated JSON by closing open structures."""
        start = text.find('{')
        if start == -1:
            return None
        
        text = text[start:]
        
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        
        in_string = False
        last_char = ''
        for char in text:
            if char == '"' and last_char != '\\':
                in_string = not in_string
            last_char = char
        
        repaired = text
        
        if in_string:
            repaired += '"'
        
        repaired += ']' * open_brackets
        repaired += '}' * open_braces
        
        return repaired

    def _validate_fields(
        self, 
        extracted: dict
    ) -> Union[CompleteDecision, IncompleteDecision]:
        """Validate extracted fields and return appropriate response."""
        
        required_fields = ["goal", "cost", "risk", "irreversible"]
        
        for field in required_fields:
            value = extracted.get(field, "").strip()
            
            # Check if field is missing or unclear
            if not value or value.upper() == "UNCLEAR":
                return IncompleteDecision(
                    complete=False,
                    missing_field=field,
                    question=self.MISSING_FIELD_QUESTIONS[field]
                )
        
        # Normalize irreversible value
        irreversible_raw = extracted["irreversible"].lower().strip()
        if irreversible_raw in ["yes", "true", "1"]:
            irreversible = IrreversibleType.YES
        elif irreversible_raw in ["no", "false", "0"]:
            irreversible = IrreversibleType.NO
        else:
            irreversible = IrreversibleType.PARTIAL
        
        # All fields present - create decision object
        decision_object = DecisionObject(
            goal=extracted["goal"],
            cost=extracted["cost"],
            risk=extracted["risk"],
            irreversible=irreversible
        )
        
        return CompleteDecision(
            complete=True,
            decision_object=decision_object
        )


# Singleton instance
gatekeeper = InputGatekeeper()
