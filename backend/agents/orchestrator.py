"""Six-agent research cycle. All outputs are advisory and execution stays disabled."""
from datetime import datetime, timezone
from decimal import Decimal
import asyncio
from agents.contracts import PortfolioRiskSnapshot, TradingCycleResult
from agents.market_intelligence import MarketIntelligenceAgent
from agents.technical_analyst import TechnicalAnalystAgent
from agents.risk_manager import RiskManagerAgent
from agents.strategy import StrategyAgent
from agents.execution import ExecutionAgent
from agents.performance import PerformanceAgent


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
        market_task = self.market.analyse(pair, ticker, candles)
        risk_task = self.risk.assess(pair, ticker, technical.model_dump(mode="json"), portfolio.model_dump(mode="json"))
        market, risk = await asyncio.gather(market_task, risk_task)
        proposal = await self.strategy.propose(market.model_dump(mode="json"), technical.model_dump(mode="json"), risk.model_dump(mode="json"))
        entry = Decimal(str(ticker.get("last", "0")))
        assessment = self.execution.assess(pair, proposal, entry, None, portfolio)
        performance = self.performance.summarize(closed_trades)
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
