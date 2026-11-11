"""Provider-neutral market-data interface."""
from abc import ABC, abstractmethod

from markets.models import Instrument, MarketCandle, MarketQuote


class MarketDataProvider(ABC):
    provider_name: str

    @abstractmethod
    async def list_instruments(self) -> list[Instrument]:
        raise NotImplementedError

    @abstractmethod
    async def get_quote(self, instrument: Instrument) -> MarketQuote:
        raise NotImplementedError

    @abstractmethod
    async def get_candles(self, instrument: Instrument, interval_minutes: int = 60) -> list[MarketCandle]:
        raise NotImplementedError
