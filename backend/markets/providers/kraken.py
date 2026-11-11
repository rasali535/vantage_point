"""Kraken public spot market-data adapter for the normalized market layer."""
from datetime import datetime, timezone
from decimal import Decimal

from agents.kraken import KrakenAgent
from markets.models import Instrument, MarketCandle, MarketQuote, MarketType
from markets.providers.base import MarketDataProvider


_ASSET_ALIASES = {"XBT": "BTC", "XDG": "DOGE"}


def _currency(value: str) -> str:
    value = value.upper()
    return _ASSET_ALIASES.get(value, value)


class KrakenMarketDataProvider(MarketDataProvider):
    provider_name = "kraken"

    def __init__(self, agent: KrakenAgent | None = None):
        self.agent = agent or KrakenAgent()

    async def list_instruments(self) -> list[Instrument]:
        pairs = await self.agent.get_asset_pairs()
        instruments = []
        for provider_key, raw in pairs.items():
            if not isinstance(raw, dict):
                continue
            wsname = raw.get("wsname")
            altname = raw.get("altname")
            if not isinstance(wsname, str) or "/" not in wsname or not isinstance(altname, str):
                continue
            base_raw, quote_raw = wsname.split("/", 1)
            base, quote = _currency(base_raw), _currency(quote_raw)
            status = str(raw.get("status", "online")).lower()
            instruments.append(Instrument(
                instrument_id=f"crypto_spot:{base}/{quote}:kraken",
                market_type=MarketType.CRYPTO_SPOT,
                symbol=f"{base}/{quote}",
                base_currency=base,
                quote_currency=quote,
                provider=self.provider_name,
                provider_symbol=altname,
                price_precision=int(raw.get("pair_decimals", 8)),
                quantity_precision=int(raw.get("lot_decimals", 8)),
                min_quantity=Decimal(str(raw["ordermin"])) if raw.get("ordermin") else None,
                min_notional=Decimal(str(raw["costmin"])) if raw.get("costmin") else None,
                active=status == "online",
            ))
        return instruments

    async def get_quote(self, instrument: Instrument) -> MarketQuote:
        self._validate_instrument(instrument)
        ticker = await self.agent.get_ticker(instrument.symbol)
        return MarketQuote(
            instrument_id=instrument.instrument_id,
            provider=self.provider_name,
            bid=Decimal(str(ticker["bid"])),
            ask=Decimal(str(ticker["ask"])),
            observed_at=datetime.now(timezone.utc),
        )

    async def get_candles(self, instrument: Instrument, interval_minutes: int = 60) -> list[MarketCandle]:
        self._validate_instrument(instrument)
        candles = await self.agent.get_ohlc(instrument.symbol, interval=interval_minutes)
        return [MarketCandle(
            instrument_id=instrument.instrument_id,
            provider=self.provider_name,
            interval_minutes=interval_minutes,
            timestamp=datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
            volume=Decimal(str(item["volume"])),
        ) for item in candles]

    def _validate_instrument(self, instrument: Instrument) -> None:
        if instrument.provider != self.provider_name or instrument.market_type != MarketType.CRYPTO_SPOT:
            raise ValueError("Instrument is not a Kraken crypto spot instrument.")
