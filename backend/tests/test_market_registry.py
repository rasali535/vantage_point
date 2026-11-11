import unittest
from decimal import Decimal
from unittest.mock import AsyncMock

from markets.models import Instrument, MarketQuote, MarketType
from markets.providers.kraken import KrakenMarketDataProvider
from markets.registry import InstrumentRegistry


class InstrumentRegistryTests(unittest.TestCase):
    def make_instrument(self, provider="kraken", symbol="BTC/USD"):
        base, quote = symbol.split("/")
        return Instrument(
            instrument_id=f"crypto_spot:{symbol}:{provider}",
            market_type=MarketType.CRYPTO_SPOT,
            symbol=symbol,
            base_currency=base,
            quote_currency=quote,
            provider=provider,
            provider_symbol=symbol.replace("/", ""),
            price_precision=2,
            quantity_precision=6,
        )

    def test_registry_filters_market_and_provider(self):
        registry = InstrumentRegistry()
        registry.replace_provider_instruments("kraken", [self.make_instrument()])
        self.assertEqual(len(registry.list_instruments(market_type=MarketType.CRYPTO_SPOT)), 1)
        self.assertEqual(registry.list_instruments(provider="oanda"), [])

    def test_replacing_one_provider_preserves_other_providers(self):
        registry = InstrumentRegistry()
        registry.replace_provider_instruments("kraken", [self.make_instrument()])
        other = self.make_instrument(provider="other")
        registry.replace_provider_instruments("other", [other])
        registry.replace_provider_instruments("kraken", [])
        self.assertEqual([item.provider for item in registry.list_instruments()], ["other"])

    def test_provider_mismatch_is_rejected(self):
        registry = InstrumentRegistry()
        with self.assertRaises(ValueError):
            registry.replace_provider_instruments("kraken", [self.make_instrument(provider="other")])

    def test_quote_requires_valid_spread(self):
        with self.assertRaises(ValueError):
            MarketQuote(
                instrument_id="crypto_spot:BTC/USD:kraken",
                provider="kraken",
                bid=Decimal("101"),
                ask=Decimal("100"),
            )


class KrakenProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_asset_pairs_are_normalized_and_provider_attributed(self):
        agent = type("FakeAgent", (), {})()
        agent.get_asset_pairs = AsyncMock(return_value={
            "XXBTZUSD": {
                "altname": "XBTUSD", "wsname": "XBT/USD", "base": "XXBT",
                "quote": "ZUSD", "pair_decimals": 1, "lot_decimals": 8,
                "ordermin": "0.0001", "costmin": "0.5", "status": "online",
            },
            "BAD": {"altname": "bad", "wsname": "invalid", "status": "online"},
        })
        provider = KrakenMarketDataProvider(agent=agent)
        instruments = await provider.list_instruments()
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments[0].symbol, "BTC/USD")
        self.assertEqual(instruments[0].provider_symbol, "XBTUSD")
        self.assertEqual(instruments[0].min_quantity, Decimal("0.0001"))

    async def test_quote_uses_normalized_bid_ask(self):
        agent = type("FakeAgent", (), {})()
        agent.get_ticker = AsyncMock(return_value={"bid": 100, "ask": 101})
        provider = KrakenMarketDataProvider(agent=agent)
        instrument = Instrument(
            instrument_id="crypto_spot:BTC/USD:kraken", market_type=MarketType.CRYPTO_SPOT,
            symbol="BTC/USD", base_currency="BTC", quote_currency="USD", provider="kraken",
            provider_symbol="XBTUSD", price_precision=1, quantity_precision=8,
        )
        quote = await provider.get_quote(instrument)
        self.assertEqual(quote.mid, Decimal("100.5"))
        self.assertEqual(quote.spread, Decimal("1"))


if __name__ == "__main__":
    unittest.main()
