"""Six-agent research cycle. All outputs are advisory and execution stays disabled."""
from decimal import Decimal
import asyncio
import logging
import os
import time

from agents.contracts import PortfolioRiskSnapshot, TradingCycleResult
from agents.market_intelligence import MarketIntelligenceAgent
from agents.technical_analyst import TechnicalAnalystAgent
from agents.risk_manager import RiskManagerAgent
from agents.strategy import StrategyAgent
from agents.execution import ExecutionAgent
from agents.performance import PerformanceAgent

logger = logging.getLogger(__name__)


class AgentStageTimeout(TimeoutError):
    """A named Boardroom stage exceeded its configured time budget."""

    def __init__(self, stage: str, timeout_seconds: float):
        self.stage = stage
        self.timeout_seconds = timeout_seconds
        super().__init__(f"{stage} exceeded {timeout_seconds:.1f}s")


def _agent_timeout_seconds() -> float:
    try:
        configured = float(os.getenv("AGENT_TIMEOUT_SECONDS", "18"))
    except (TypeError, ValueError):
        configured = 18.0
    return min(30.0, max(5.0, configured))


async def _run_stage(stage: str, awaitable):
    timeout = _agent_timeout_seconds()
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(awaitable, timeout=timeout)
    except asyncio.TimeoutError as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.warning(
            "boardroom_stage_timeout stage=%s timeout_seconds=%.1f elapsed_ms=%d",
            stage, timeout, elapsed_ms,
        )
        raise AgentStageTimeout(stage, timeout) from exc
    except Exception:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.exception("boardroom_stage_failed stage=%s elapsed_ms=%d", stage, elapsed_ms)
        raise
    elapsed_ms = round((time.monotonic() - started) * 1000)
    logger.info("boardroom_stage_completed stage=%s elapsed_ms=%d", stage, elapsed_ms)
    return result


class TradingOrchestrator:
    def __init__(self):
        self.market = MarketIntelligenceAgent()
        self.technical = TechnicalAnalystAgent()
        self.risk = RiskManagerAgent()
        self.strategy = StrategyAgent()
        self.execution = ExecutionAgent()
        self.performance = PerformanceAgent()

    async def run(self, pair: str, ticker: dict, candles: list, portfolio: PortfolioRiskSnapshot | None = None, closed_trades: list | None = None) -> TradingCycleResult:
        portfolio = portfolio or PortfolioRiskSnapshot()
        closed_trades = closed_trades or []
        technical = self.technical.analyse(candles)

        market_task = _run_stage("market_intelligence", self.market.analyse(pair, ticker, candles))
        risk_task = _run_stage(
            "risk_manager",
            self.risk.assess(pair, ticker, technical.model_dump(mode="json"), portfolio.model_dump(mode="json")),
        )
        market, risk = await asyncio.gather(market_task, risk_task)

        performance = self.performance.summarize(closed_trades)
        proposal = await _run_stage(
            "strategy",
            self.strategy.propose(
                market.model_dump(mode="json"),
                technical.model_dump(mode="json"),
                risk.model_dump(mode="json"),
                performance,
            ),
        )
        entry = Decimal(str(ticker.get("last", "0")))
        assessment = self.execution.assess(pair, proposal, entry, portfolio)
        return TradingCycleResult(
            pair=pair,
            market_intelligence=market,
            technical_analysis=technical,
            risk_assessment=risk,
            strategy=proposal,
            execution_assessment=assessment,
            performance_context=performance,
        )


trading_orchestrator = TradingOrchestrator()
