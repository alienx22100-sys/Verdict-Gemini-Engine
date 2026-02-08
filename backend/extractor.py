"""
Extraction Layer for Decision Authority.
Parses sensor outputs and extracts digital signals.
"""

from models import (
    SensorCouncilOutput,
    ConstraintSignal,
    RiskSignal,
    ROISignal
)


class SignalExtractor:
    """
    Extraction Layer - Parses sensor outputs and extracts signals.
    This is a pure code layer, no AI involved.
    """
    
    @staticmethod
    def extract(sensors: SensorCouncilOutput) -> dict:
        """
        Extract signals from sensor council output.
        
        Returns:
            dict with extracted signals and sentences
        """
        return {
            # Signals (for deterministic core)
            "constraint_signal": sensors.green.signal,
            "risk_signal": sensors.red.signal,
            "roi_signal": sensors.blue.signal,
            
            # Sentences (for decision card)
            "constraint_sentence": sensors.green.sentence,
            "risk_sentence": sensors.red.sentence,
            "roi_sentence": sensors.blue.sentence,
            "upside_sentence": sensors.yellow.sentence,
            
            # Numeric scores for visualization (0-100)
            "scores": SignalExtractor._calculate_scores(sensors)
        }
    
    @staticmethod
    def _calculate_scores(sensors: SensorCouncilOutput) -> dict:
        """
        Calculate numeric scores for visualization.
        These are derived from signals, not from AI.
        """
        # Constraint score: 100 = no constraint issues, 0 = violated
        constraint_score = 100 if sensors.green.signal == ConstraintSignal.PASS else 15
        
        # Risk score: 100 = well managed, 0 = catastrophic
        risk_score = 85 if sensors.red.signal == RiskSignal.MANAGED else 10
        
        # ROI score: 100 = highly positive, 0 = negative
        roi_score = 80 if sensors.blue.signal == ROISignal.POSITIVE else 20
        
        # Overall viability score
        if sensors.green.signal == ConstraintSignal.VIOLATED:
            overall = 10
        elif sensors.red.signal == RiskSignal.CATASTROPHIC:
            overall = 15
        elif sensors.blue.signal == ROISignal.NEGATIVE:
            overall = 25
        else:
            overall = 90
        
        return {
            "constraint": constraint_score,
            "risk": risk_score,
            "roi": roi_score,
            "overall": overall
        }


# Singleton instance
extractor = SignalExtractor()
