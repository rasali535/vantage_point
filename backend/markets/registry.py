"""In-memory registry for provider-discovered instruments.

The registry only contains instruments returned by a connected provider. It
never fabricates a Forex universe or assumes cross-broker availability.
"""
from typing import Iterable

from markets.models import Instrument, MarketType


class InstrumentRegistry:
    def __init__(self):
        self._instruments: dict[str, Instrument] = {}

    def replace_provider_instruments(self, provider: str, instruments: Iterable[Instrument]) -> int:
        provider_key = provider.strip().lower()
        if not provider_key:
            raise ValueError("Provider name is required.")
        incoming = list(instruments)
        if any(item.provider.lower() != provider_key for item in incoming):
            raise ValueError("All instruments must belong to the selected provider.")

        # Replace only this provider's view; instruments from other providers
        # remain available, even when they share a normalized market symbol.
        self._instruments = {
            key: value for key, value in self._instruments.items()
            if value.provider.lower() != provider_key
        }
        for instrument in incoming:
            self._instruments[instrument.instrument_id] = instrument
        return len(incoming)

    def get(self, instrument_id: str) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def list_instruments(
        self,
        *,
        market_type: MarketType | None = None,
        provider: str | None = None,
        active_only: bool = True,
    ) -> list[Instrument]:
        results = list(self._instruments.values())
        if market_type is not None:
            results = [item for item in results if item.market_type == market_type]
        if provider is not None:
            provider_key = provider.strip().lower()
            results = [item for item in results if item.provider.lower() == provider_key]
        if active_only:
            results = [item for item in results if item.active]
        return sorted(results, key=lambda item: (item.market_type.value, item.symbol, item.provider))
