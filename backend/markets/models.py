"""Provider-neutral market and instrument contracts.

These models describe observed provider data. They do not imply that an
instrument is enabled for paper execution or that a broker supports it.
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MarketType(str, Enum):
    CRYPTO_SPOT = "crypto_spot"
    FOREX = "forex"


class Instrument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    instrument_id: str
    market_type: MarketType
    symbol: str
    base_currency: str
    quote_currency: str
    provider: str
    provider_symbol: str
    price_precision: int = Field(ge=0, le=18)
    quantity_precision: int = Field(ge=0, le=18)
    min_quantity: Optional[Decimal] = None
    min_notional: Optional[Decimal] = None
    pip_size: Optional[Decimal] = None
    contract_size: Optional[Decimal] = None
    active: bool = True

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized or len(normalized) > 16:
            raise ValueError("Currency code is invalid.")
        return normalized

    @model_validator(mode="after")
    def validate_market_metadata(self):
        if self.market_type == MarketType.FOREX and self.pip_size is not None and self.pip_size <= 0:
            raise ValueError("Forex pip_size must be positive.")
        if self.min_quantity is not None and self.min_quantity <= 0:
            raise ValueError("min_quantity must be positive.")
        if self.min_notional is not None and self.min_notional < 0:
            raise ValueError("min_notional cannot be negative.")
        return self


class MarketQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    instrument_id: str
    provider: str
    bid: Decimal
    ask: Decimal
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_market(self):
        if self.bid <= 0 or self.ask <= 0:
            raise ValueError("Quote prices must be positive.")
        if self.ask < self.bid:
            raise ValueError("Ask cannot be lower than bid.")
        if self.observed_at.tzinfo is None:
            raise ValueError("Quote timestamp must be timezone-aware.")
        return self

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


class MarketCandle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    instrument_id: str
    provider: str
    interval_minutes: int = Field(gt=0)
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Optional[Decimal] = None

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("Candle timestamp must be timezone-aware.")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("Candle high is inconsistent with OHLC values.")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("Candle low is inconsistent with OHLC values.")
        if self.volume is not None and self.volume < 0:
            raise ValueError("Candle volume cannot be negative.")
        return self
