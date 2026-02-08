"""
Gemini 3 Sensor Council for Decision Authority.
Four strict sensors that output one sentence + one signal each.
"""

import gemini_client as genai
import re
import asyncio
import json
from typing import Optional

from config import Config
from models import (
    DecisionObject,
    GreenSensorOutput,
    RedSensorOutput,
    BlueSensorOutput,
    YellowSensorOutput,
    SensorCouncilOutput,
    ConstraintSignal,
    RiskSignal,
    ROISignal
)


class SensorCouncil:
    """
    Gemini 3 Sensor Council - Four strict sensors for decision analysis.
    Refactored to use a SINGLE consolidated API call to avoid rate limits.
    """
    
    CONSOLIDATED_PROMPT = """You are the Decision Authority Sensor Council. 
Perform 4 distinct strict analyses on this decision.

DECISION:
Goal: {goal}
Cost: {cost}
Risk: {risk}
Irreversible: {irreversible}

INSTRUCTIONS:
Analyze this decision from 4 strict perspectives.
Output a JSON object with exactly these keys: "green", "red", "blue", "yellow".

1. GREEN (Reality Constraints):
   - Identify ONE hard constraint (money, time, skills, physics).
   - Sentence: "The limiting factor is [constraint]."
   - Signal: "PASS" (manageable) or "VIOLATED" (impossible).

2. RED (Failure Mode):
   - Expose the worst hidden danger or self-deception.
   - Sentence: "The real danger is [danger]."
   - Signal: "MANAGED" (mitigable) or "CATASTROPHIC" (ruinous).

3. BLUE (ROI/Logic):
   - Compare value vs cost/depreciation.
   - Sentence: "Compared to [baseline], this [compounds/depreciates]."
   - Signal: "POSITIVE" (gains value) or "NEGATIVE" (loses value).

4. YELLOW (Opportunity):
   - State the upside if successful.
   - Sentence: "If successful, within [time], you could gain [upside]."
   - Signal: "N/A" (always null for yellow).

OUTPUT FORMAT (JSON ONLY):
{{
  "green": {{ "sentence": "...", "signal": "PASS|VIOLATED" }},
  "red": {{ "sentence": "...", "signal": "MANAGED|CATASTROPHIC" }},
  "blue": {{ "sentence": "...", "signal": "POSITIVE|NEGATIVE" }},
  "yellow": {{ "sentence": "..." }}
}}
"""

    def __init__(self):
        """Initialize the sensor council with Gemini configuration."""
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None

    async def analyze(self, decision: DecisionObject, max_retries: int = 2) -> SensorCouncilOutput:
        """
        Run all four sensors in a SINGLE API call with retry logic.
        Returns structured output for all sensors.
        """
        if not self.model:
            raise ValueError("Gemini API not configured. Set GEMINI_API_KEY.")
        
        # Format the prompt
        prompt = self.CONSOLIDATED_PROMPT.format(
            goal=decision.goal,
            cost=decision.cost,
            risk=decision.risk,
            irreversible=decision.irreversible
        )
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                print(f"DEBUG: Sensor Council attempt {attempt + 1}/{max_retries + 1}")
                
                # Make SINGLE API call
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=2000,
                        response_mime_type="application/json"
                    )
                )
                
                print(f"DEBUG: Raw Gemini Response Parts: {response.parts}")
                
                # Check for safety blocking
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    error_msg = f"Blocked: {response.prompt_feedback.block_reason}"
                    print(f"DEBUG: Safety Block: {error_msg}")
                    return self._get_fallback_output(error_msg)

                try:
                    text = response.text
                    print(f"DEBUG: Raw Gemini Text: {text[:500]}...")
                except Exception as e:
                    error_msg = f"No text in response (Safety?): {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    if attempt < max_retries:
                        await asyncio.sleep((attempt + 1) * 1.5)
                        continue
                    return self._get_fallback_output(error_msg)

                # Parse JSON response
                data = self._parse_json(text)
                print(f"DEBUG: Parsed Data keys: {data.keys()}")
                
                # Check if parsing returned an error
                if "error" in data and not data.get("green", {}).get("sentence", "").startswith("The limiting"):
                    print(f"DEBUG: Parse error detected: {data.get('error')}")
                    if attempt < max_retries:
                        print(f"DEBUG: Retrying due to parse error...")
                        await asyncio.sleep((attempt + 1) * 1.5)
                        continue
                
                # Construct strict outputs with specific error messages for missing keys
                return SensorCouncilOutput(
                    green=GreenSensorOutput(
                        sentence=data.get("green", {}).get("sentence", f"Green Sensor Failed: {data.get('error', 'Unknown error')}"),
                        signal=self._parse_enum(ConstraintSignal, data.get("green", {}).get("signal"), ConstraintSignal.VIOLATED)
                    ),
                    red=RedSensorOutput(
                        sentence=data.get("red", {}).get("sentence", "Red Sensor Failed"),
                        signal=self._parse_enum(RiskSignal, data.get("red", {}).get("signal"), RiskSignal.CATASTROPHIC)
                    ),
                    blue=BlueSensorOutput(
                        sentence=data.get("blue", {}).get("sentence", "Blue Sensor Failed"),
                        signal=self._parse_enum(ROISignal, data.get("blue", {}).get("signal"), ROISignal.NEGATIVE)
                    ),
                    yellow=YellowSensorOutput(
                        sentence=data.get("yellow", {}).get("sentence", "Yellow Sensor Failed")
                    )
                )
                
            except Exception as e:
                last_error = e
                print(f"DEBUG: Sensor Council attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1.5
                    print(f"DEBUG: Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        print(f"Sensor Council Failed after {max_retries + 1} attempts: {last_error}")
        return self._get_fallback_output(f"Analysis failed after multiple attempts. Please try again.")

    def _parse_json(self, text: str) -> dict:
        """Clean and parse JSON from response, handling markdown, truncation, and extra text."""
        import ast
        text = text.strip()
        
        # 1. Strip Markdown code blocks
        if "```" in text:
            text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
            
        # 2. Try standard JSON load
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # 3. Aggressive cleanup and repair
        try:
            # Fix Python-style booleans/None
            clean = text.replace("True", "true").replace("False", "false").replace("None", "null")
            # Remove comments
            clean = re.sub(r"//.*$", "", clean, flags=re.MULTILINE)
            # Find the main JSON object
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                clean = match.group()
            
            # Remove trailing commas (common Gemini error)
            clean = re.sub(r",\s*}", "}", clean)
            clean = re.sub(r",\s*]", "]", clean)
            
            return json.loads(clean)
        except (json.JSONDecodeError, Exception) as e:
            pass
        
        # 4. Attempt to repair truncated JSON
        try:
            repaired = self._repair_truncated_json(text)
            if repaired:
                return json.loads(repaired)
        except:
            pass
            
        # 5. Last resort: AST literal eval
        try:
            return ast.literal_eval(text)
        except:
            pass

        print(f"FAILED TO PARSE: {text}")
        return {
            "error": "Failed to parse AI response", 
            "green": {"sentence": "Analysis unavailable - retrying may help"},
            "red": {"sentence": "Analysis unavailable"},
            "blue": {"sentence": "Analysis unavailable"},
            "yellow": {"sentence": "Analysis unavailable"}
        }
    
    def _repair_truncated_json(self, text: str) -> str:
        """Attempt to repair truncated JSON by closing open structures."""
        # Find the start of JSON
        start = text.find('{')
        if start == -1:
            return None
        
        text = text[start:]
        
        # Count open/close braces and brackets
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        
        # Check for unclosed string (odd number of unescaped quotes)
        in_string = False
        last_char = ''
        for char in text:
            if char == '"' and last_char != '\\':
                in_string = not in_string
            last_char = char
        
        repaired = text
        
        # Close unclosed string
        if in_string:
            repaired += '"'
        
        # Close any open brackets
        repaired += ']' * open_brackets
        
        # Close any open braces  
        repaired += '}' * open_braces
        
        return repaired

    def _parse_enum(self, enum_cls, value, default):
        """Safely parse enum values."""
        try:
            # Normalize key
            if not value: return default
            value = value.upper().strip()
            return enum_cls(value)
        except ValueError:
            return default

    def _get_fallback_output(self, error_msg: str) -> SensorCouncilOutput:
        """Return safe fallback output on error."""
        return SensorCouncilOutput(
            green=GreenSensorOutput(sentence=error_msg, signal=ConstraintSignal.VIOLATED),
            red=RedSensorOutput(sentence=error_msg, signal=RiskSignal.CATASTROPHIC),
            blue=BlueSensorOutput(sentence=error_msg, signal=ROISignal.NEGATIVE),
            yellow=YellowSensorOutput(sentence=error_msg)
        )

# Singleton instance
sensor_council = SensorCouncil()
