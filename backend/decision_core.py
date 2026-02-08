"""
Deterministic Decision Core for Decision Authority.
Pure Python code - NO AI reasoning allowed here.
"""

from typing import Tuple, Optional

from models import (
    DecisionCard,
    DecisionReason,
    DecisionVerdict,
    ConstraintSignal,
    RiskSignal,
    ROISignal
)


class DecisionCore:
    """
    Deterministic Decision Core.
    
    This layer is PURE CODE. No AI reasoning.
    No probability. No human override. No emotional weighting.
    
    Decision Logic:
        IF constraint == VIOLATED → BLOCKED
        ELSE IF risk == CATASTROPHIC → BLOCKED
        ELSE IF ROI == NEGATIVE → BLOCKED
        ELSE → APPROVED
    """
    
    @staticmethod
    def decide(extracted: dict) -> DecisionCard:
        """
        Make a deterministic decision based on extracted signals.
        
        Args:
            extracted: Dictionary from SignalExtractor.extract()
            
        Returns:
            DecisionCard with verdict and reasons
        """
        constraint_signal = extracted["constraint_signal"]
        risk_signal = extracted["risk_signal"]
        roi_signal = extracted["roi_signal"]
        
        # Build reasons
        reasons = DecisionReason(
            constraint=extracted["constraint_sentence"],
            risk=extracted["risk_sentence"],
            logic=extracted["roi_sentence"],
            upside=extracted["upside_sentence"]
        )
        
        # ─────────────────────────────────────────────────────────
        # DETERMINISTIC DECISION LOGIC
        # ─────────────────────────────────────────────────────────
        
        verdict, blocking_reason = DecisionCore._apply_logic(
            constraint_signal,
            risk_signal,
            roi_signal,
            reasons
        )
        
        return DecisionCard(
            verdict=verdict,
            blocking_reason=blocking_reason,
            reasons=reasons,
            scores=extracted["scores"]
        )
    
    @staticmethod
    def _apply_logic(
        constraint: ConstraintSignal,
        risk: RiskSignal,
        roi: ROISignal,
        reasons: DecisionReason
    ) -> Tuple[DecisionVerdict, Optional[str]]:
        """
        Apply deterministic decision logic.
        
        Returns:
            Tuple of (verdict, reason_message)
        
        Decision Logic:
            - BLOCKED: Only when Constraint is VIOLATED (impossible to proceed)
            - CAUTION: Risk CATASTROPHIC or ROI NEGATIVE (proceed with care)
            - APPROVED: All signals positive
        """
        
        # Rule 1: Constraint Violation → BLOCKED (truly impossible)
        if constraint == ConstraintSignal.VIOLATED:
            return (
                DecisionVerdict.BLOCKED,
                f"CONSTRAINT VIOLATED: {reasons.constraint}"
            )
        
        # Rule 2: Catastrophic Risk → CAUTION (high risk, but possible)
        if risk == RiskSignal.CATASTROPHIC:
            return (
                DecisionVerdict.CAUTION,
                f"HIGH RISK: {reasons.risk}"
            )
        
        # Rule 3: Negative ROI → CAUTION (not profitable, but possible)
        if roi == ROISignal.NEGATIVE:
            return (
                DecisionVerdict.CAUTION,
                f"NEGATIVE ROI: {reasons.logic}"
            )
        
        # All checks passed → APPROVED
        return (DecisionVerdict.APPROVED, None)


# Singleton instance
decision_core = DecisionCore()
