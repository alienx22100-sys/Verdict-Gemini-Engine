"""
Emotional Bias Detector for Decision Authority.
Pre-processing layer that analyzes user input for emotional charge and subjectivity.
High bias scores trigger a warning or refusal to process.
"""

import gemini_client as genai
import json
import re
from typing import Optional

from config import Config
from models import BiasAnalysis, BiasLevel


class EmotionalBiasDetector:
    """
    Analyzes user input for emotional bias before decision processing.
    Uses Gemini 3 to detect subjective language and emotional indicators.
    """
    
    BIAS_DETECTION_PROMPT = """You are an emotional bias detector. Analyze the following input for emotional charge and subjectivity.

DETECT:
1. Subjective adjectives: "amazing", "terrible", "huge", "perfect", "worst", "best"
2. Emotional state indicators: "desperate", "excited", "afraid", "love", "hate", "hope", "dream"
3. Logical fallacies: appeals to emotion, urgency without data, absolutes ("always", "never", "only")
4. Exaggeration markers: "literally", "absolutely", "completely", "totally"

INPUT:
{input}

OUTPUT FORMAT (JSON only):
{{
    "bias_score": <0-100>,
    "flagged_phrases": ["phrase1", "phrase2", ...],
    "primary_bias_type": "emotional_state" | "subjective_language" | "logical_fallacy" | "exaggeration" | "none",
    "suggestion": "<objective rephrasing suggestion if score > 70, else null>"
}}

SCORING GUIDE:
- 0-40: LOW - Mostly objective, minor emotional language acceptable
- 41-70: MEDIUM - Noticeable bias, but can proceed with warning
- 71-100: HIGH - Too emotional, requires rephrasing

Be strict but fair. Business passion is okay, but desperation and absolutes are red flags."""

    def __init__(self):
        """Initialize the bias detector with Gemini configuration."""
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None

    async def analyze(self, user_input: str) -> BiasAnalysis:
        """
        Analyze user input for emotional bias.
        Returns BiasAnalysis with score, level, and flagged phrases.
        Includes retry logic with exponential backoff for rate limits.
        """
        import asyncio
        
        if not self.model:
            # If no API configured, return neutral score
            return BiasAnalysis(
                bias_score=0,
                bias_level=BiasLevel.LOW,
                flagged_phrases=[],
                suggestion=None
            )
        
        prompt = self.BIAS_DETECTION_PROMPT.format(input=user_input)
        
        # Retry configuration
        max_retries = 3
        base_delay = 2.0  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"🔍 [BIAS] Analyzing input for emotional bias... (attempt {attempt + 1}/{max_retries})")
                
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=500,
                        response_mime_type="application/json"
                    )
                )
                
                # Parse response
                result = self._parse_json_response(response.text)
                
                # Determine bias level
                score = result.get("bias_score", 0)
                if score > 70:
                    level = BiasLevel.HIGH
                elif score > 40:
                    level = BiasLevel.MEDIUM
                else:
                    level = BiasLevel.LOW
                
                analysis = BiasAnalysis(
                    bias_score=score,
                    bias_level=level,
                    flagged_phrases=result.get("flagged_phrases", []),
                    suggestion=result.get("suggestion")
                )
                
                print(f"🔍 [BIAS] Score: {score}% ({level})")
                if analysis.flagged_phrases:
                    print(f"🔍 [BIAS] Flagged: {', '.join(analysis.flagged_phrases)}")
                
                return analysis
                
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "429" in str(e) or "rate" in error_str or "quota" in error_str or "resource" in error_str
                
                if is_rate_limit and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    print(f"⏳ [BIAS] Rate limited. Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    continue
                
                # Check for safety ratings in the error
                if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
                    print(f"⚠️ [BIAS] Safety Ratings: {e.response.prompt_feedback}")
                
                print(f"⚠️ [BIAS] Detection failed after {attempt + 1} attempts: {e}")
                
                # On error/rate limit, allow processing but flag as potential bias to be safe
                # This prevents "silent failures" where high bias inputs slip through during outages
                return BiasAnalysis(
                    bias_score=50,  # Default to medium/caution
                    bias_level=BiasLevel.MEDIUM,
                    flagged_phrases=["(Analysis unavailable - Proceeding with caution)"],
                    suggestion=f"System is experiencing heavy load. Please ensure your input is objective."
                )
        
        # Should not reach here, but just in case
        return BiasAnalysis(
            bias_score=50,
            bias_level=BiasLevel.MEDIUM,
            flagged_phrases=["(Analysis unavailable - Proceeding with caution)"],
            suggestion="System is experiencing heavy load. Please ensure your input is objective."
        )

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
        
        raise ValueError(f"Could not parse bias detection response: {text[:200]}")

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


# Singleton instance
bias_detector = EmotionalBiasDetector()
