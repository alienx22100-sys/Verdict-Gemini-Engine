"""
Pydantic models for Decision Authority.
Strict schemas for decision objects, sensor outputs, and decision cards.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from enum import Enum


class IrreversibleType(str, Enum):
    """Irreversibility classification."""
    YES = "yes"
    NO = "no"
    PARTIAL = "partial"


class ConstraintSignal(str, Enum):
    """Green sensor signal."""
    PASS = "PASS"
    VIOLATED = "VIOLATED"


class RiskSignal(str, Enum):
    """Red sensor signal."""
    MANAGED = "MANAGED"
    CATASTROPHIC = "CATASTROPHIC"


class ROISignal(str, Enum):
    """Blue sensor signal."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class DecisionVerdict(str, Enum):
    """Final decision verdict."""
    APPROVED = "APPROVED"
    CAUTION = "CAUTION"
    BLOCKED = "BLOCKED"


class BiasLevel(str, Enum):
    """Emotional bias level classification."""
    LOW = "LOW"           # 0-40: Mostly objective
    MEDIUM = "MEDIUM"     # 41-70: Noticeable bias, proceed with warning
    HIGH = "HIGH"         # 71-100: Too emotional, requires rephrasing


# ─────────────────────────────────────────────────────────────
# INPUT MODELS
# ─────────────────────────────────────────────────────────────

class DecisionInput(BaseModel):
    """Raw user input for decision analysis."""
    # SECURITY: Enforce length limits to prevent abuse
    message: str = Field(
        ..., 
        min_length=10, 
        max_length=2000,
        description="User's decision description (10-2000 characters)"
    )


class DecisionObject(BaseModel):
    """Structured decision object extracted by gatekeeper."""
    goal: str = Field(..., description="What the user wants to achieve")
    cost: str = Field(..., description="What the user must sacrifice or invest")
    risk: str = Field(..., description="What could go wrong")
    irreversible: IrreversibleType = Field(..., description="Can this be undone?")
    
    class Config:
        use_enum_values = True


class IncompleteDecision(BaseModel):
    """Response when decision object is incomplete."""
    complete: Literal[False] = False
    missing_field: str
    question: str


class CompleteDecision(BaseModel):
    """Response when decision object is complete."""
    complete: Literal[True] = True
    decision_object: DecisionObject


# ─────────────────────────────────────────────────────────────
# SENSOR MODELS
# ─────────────────────────────────────────────────────────────

class GreenSensorOutput(BaseModel):
    """Reality Constraint Sensor output."""
    sentence: str = Field(..., description="One sentence about limiting factor")
    signal: ConstraintSignal
    
    class Config:
        use_enum_values = True


class RedSensorOutput(BaseModel):
    """Self-Deception / Failure Mode Sensor output."""
    sentence: str = Field(..., description="One sentence about hidden danger")
    signal: RiskSignal
    
    class Config:
        use_enum_values = True


class BlueSensorOutput(BaseModel):
    """Logic / ROI Sensor output."""
    sentence: str = Field(..., description="One sentence comparing value")
    signal: ROISignal
    
    class Config:
        use_enum_values = True


class YellowSensorOutput(BaseModel):
    """Opportunity Sensor output."""
    sentence: str = Field(..., description="One sentence about upside potential")
    # Yellow has no signal - only states upside if it exists


class SensorCouncilOutput(BaseModel):
    """Combined output from all four sensors."""
    green: GreenSensorOutput
    red: RedSensorOutput
    blue: BlueSensorOutput
    yellow: YellowSensorOutput


# ─────────────────────────────────────────────────────────────
# DECISION CARD MODELS
# ─────────────────────────────────────────────────────────────

class DecisionReason(BaseModel):
    """Reasons contributing to the decision."""
    constraint: str
    risk: str
    logic: str
    upside: str


class DecisionCard(BaseModel):
    """Final decision output card."""
    verdict: DecisionVerdict
    blocking_reason: Optional[str] = None  # Only set if BLOCKED
    reasons: DecisionReason
    scores: dict = Field(default_factory=dict, description="Numerical scores for visualization")
    
    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────
# BIAS ANALYSIS MODELS
# ─────────────────────────────────────────────────────────────

class BiasAnalysis(BaseModel):
    """Result from emotional bias detection."""
    bias_score: int = Field(..., ge=0, le=100, description="Emotional bias score 0-100")
    bias_level: BiasLevel
    flagged_phrases: List[str] = Field(default_factory=list)
    suggestion: Optional[str] = None  # Rephrasing suggestion if HIGH
    
    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────
# API RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class GatekeeperResponse(BaseModel):
    """Response from input gatekeeper."""
    success: bool
    data: Optional[CompleteDecision | IncompleteDecision] = None
    error: Optional[str] = None


class DecisionResponse(BaseModel):
    """Full decision response."""
    success: bool
    decision_card: Optional[DecisionCard] = None
    sensors: Optional[SensorCouncilOutput] = None
    decision_object: Optional[DecisionObject] = None
    optimizer_suggestions: Optional[List[str]] = None
    bias_analysis: Optional[BiasAnalysis] = None
    bias_rejected: bool = False  # True if blocked due to high bias
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    gemini_configured: bool
    version: str = "1.0.0"
