"""Typed contracts shared by the six Ras Ali AI Trader agents."""
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pair: str
    ticker: Dict[str, Any]
    candles: List[Dict[str, Any]] = Field(default_factory=list)
    observed_at: str


class AgentFinding(BaseModel):
    agent: str
    summary: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    warnings: List[str] = Field(default_factory=list)


class TechnicalReport(BaseModel):
    agent: str = "technical_analyst"
    trend: str
    rsi_14: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    atr: Optional[float] = None
    signal: TradeAction = TradeAction.HOLD
    evidence: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class StrategyProposal(BaseModel):
    action: TradeAction = TradeAction.HOLD
    rationale: str
    confidence: float = Field(ge=0, le=1)
    invalidation_conditions: List[str] = Field(default_factory=list)


class PortfolioRiskSnapshot(BaseModel):
    equity: Decimal = Decimal("0")
    daily_loss_pct: Decimal = Decimal("0")
    drawdown_pct: Decimal = Decimal("0")
    open_positions: int = 0
    leverage: Decimal = Decimal("1")


class ExecutionAssessment(BaseModel):
    approved_for_review: bool = False
    execution_enabled: bool = False
    status: str
    reasons: List[str] = Field(default_factory=list)
    risk_metrics: Dict[str, Any] = Field(default_factory=dict)


class TradingCycleResult(BaseModel):
    pair: str
    market_intelligence: AgentFinding
    technical_analysis: TechnicalReport
    risk_assessment: AgentFinding
    strategy: StrategyProposal
    execution_assessment: ExecutionAssessment
    performance_context: Dict[str, Any] = Field(default_factory=dict)
    execution_status: str = "not_submitted"
