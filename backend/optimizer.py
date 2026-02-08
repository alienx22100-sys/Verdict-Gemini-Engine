"""
Strategic Optimizer for Decision Authority.
Provides measurable, actionable suggestions to improve BLOCKED/CAUTION decisions.
"""

import gemini_client as genai
import json
import re
from typing import List, Optional

from config import Config
from models import DecisionObject, SensorCouncilOutput, DecisionVerdict


class StrategicOptimizer:
    """
    AI-powered optimizer that generates measurable improvement suggestions.
    Only called when verdict is BLOCKED or CAUTION.
    """
    
    OPTIMIZER_PROMPT = """You are a Strategic Decision Optimizer.
A decision has been analyzed and received a {verdict} verdict.

DECISION:
- Goal: {goal}
- Cost: {cost}
- Risk: {risk}
- Irreversible: {irreversible}

ANALYSIS RESULTS:
- Constraint: {constraint_sentence} (Signal: {constraint_signal})
- Risk: {risk_sentence} (Signal: {risk_signal})
- ROI: {roi_sentence} (Signal: {roi_signal})
- Opportunity: {upside_sentence}

BLOCKING REASON: {blocking_reason}

YOUR TASK:
Generate exactly 3 specific, MEASURABLE suggestions to improve this decision to APPROVED.

CRITICAL RULES:
1. Each suggestion MUST include specific numbers, percentages, or timeframes
2. NO vague advice like "save more money" or "reduce risk"
3. GOOD example: "Increase your financial safety margin by 25% before starting"
4. GOOD example: "Extend your timeline by 6 months to build required skills"
5. GOOD example: "Reduce initial investment to 40% of savings as risk buffer"
6. Each suggestion should directly address the blocking issues
7. Be concise - one clear sentence per suggestion

OUTPUT FORMAT (JSON array only):
["suggestion 1", "suggestion 2", "suggestion 3"]
"""

    def __init__(self):
        """Initialize the optimizer with Gemini configuration."""
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None

    async def optimize(
        self,
        decision: DecisionObject,
        sensors: SensorCouncilOutput,
        verdict: DecisionVerdict,
        blocking_reason: Optional[str]
    ) -> List[str]:
        """
        Generate measurable improvement suggestions.
        
        Args:
            decision: The original decision object
            sensors: Results from sensor council
            verdict: The decision verdict (BLOCKED/CAUTION)
            blocking_reason: Why the decision was blocked/cautioned
            
        Returns:
            List of 3 measurable suggestions
        """
        if not self.model:
            return ["Unable to generate suggestions - API not configured"]
        
        # Don't optimize APPROVED decisions
        if verdict == DecisionVerdict.APPROVED:
            return []
        
        try:
            prompt = self.OPTIMIZER_PROMPT.format(
                verdict=verdict,
                goal=decision.goal,
                cost=decision.cost,
                risk=decision.risk,
                irreversible=decision.irreversible,
                constraint_sentence=sensors.green.sentence,
                constraint_signal=sensors.green.signal,
                risk_sentence=sensors.red.sentence,
                risk_signal=sensors.red.signal,
                roi_sentence=sensors.blue.sentence,
                roi_signal=sensors.blue.signal,
                upside_sentence=sensors.yellow.sentence,
                blocking_reason=blocking_reason or "Decision requires improvement"
            )
            
            print("DEBUG: Calling Strategic Optimizer...")
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                    response_mime_type="application/json"
                )
            )
            
            # Parse response
            text = response.text.strip()
            print(f"DEBUG: Optimizer response: {text[:200]}...")
            
            suggestions = self._parse_suggestions(text)
            return suggestions
            
        except Exception as e:
            print(f"ERROR: Optimizer failed: {e}")
            return [
                "Review and quantify your financial buffer requirements",
                "Establish specific milestones with measurable success criteria",
                "Define a clear exit strategy with specific trigger conditions"
            ]

    def _parse_suggestions(self, text: str) -> List[str]:
        """Parse JSON array of suggestions from response."""
        try:
            # Try direct JSON parse
            suggestions = json.loads(text)
            if isinstance(suggestions, list) and len(suggestions) >= 1:
                return suggestions[:3]
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON array from text
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                suggestions = json.loads(match.group())
                if isinstance(suggestions, list):
                    return suggestions[:3]
        except:
            pass
        
        # Fallback
        return [
            "Increase your safety margin by at least 30%",
            "Extend timeline by 3-6 months for proper preparation",
            "Reduce initial commitment to 50% of planned resources"
        ]


# Singleton instance
optimizer = StrategicOptimizer()
