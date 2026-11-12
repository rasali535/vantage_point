
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface MirofishTerminalProps {
  status: any;
  deliberations: any[];
  pair: string;
  onPairChange: (pair: string) => void;
  scanning: boolean;
  onRunScan: () => void;
  lastScanDecision: any;
  onOpenTab: (tab: string) => void;
}

interface KrakenTicker {
  pair: string;
  ask: number;
  bid: number;
  last: number;
  high24h: number;
  low24h: number;
  volume24h: number;
  open24h: number;
  changeUsd: number;
  changePct: number;
}

interface KrakenCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  vwap: number;
  volume: number;
}

const autoDecimals = (val: number) => {
  const abs = Math.abs(val);
  if (abs === 0) return 2;
  if (abs < 0.05) return 5;
  if (abs < 10) return 5;
  if (abs < 500) return 3;
  return 2;
};

const fmtUsd = (val: number | null | undefined, decimals?: number) => {
  if (val === null || val === undefined || Number.isNaN(val)) return '—';
  const d = decimals !== undefined ? decimals : autoDecimals(val);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: d,
    maximumFractionDigits: d,
  }).format(val);
};

const fmtSignedUsd = (val: number | null | undefined, decimals?: number) => {
  if (val === null || val === undefined || Number.isNaN(val)) return '—';
  const d = decimals !== undefined ? decimals : autoDecimals(val);
  const sign = val >= 0 ? '+' : '-';
  return `${sign}${fmtUsd(Math.abs(val), d)}`;
};

const QUICK_PAIRS: Array<{ pair: string; label: string; category: 'forex' | 'metals' | 'indices' | 'crypto' }> = [
  { pair: 'EUR/USD', label: 'EUR/USD', category: 'forex' },
  { pair: 'GBP/USD', label: 'GBP/USD', category: 'forex' },
  { pair: 'USD/JPY', label: 'USD/JPY', category: 'forex' },
  { pair: 'AUD/USD', label: 'AUD/USD', category: 'forex' },
  { pair: 'USD/CAD', label: 'USD/CAD', category: 'forex' },
  { pair: 'USD/CHF', label: 'USD/CHF', category: 'forex' },
  { pair: 'EUR/GBP', label: 'EUR/GBP', category: 'forex' },
  { pair: 'EUR/JPY', label: 'EUR/JPY', category: 'forex' },
  { pair: 'XAU/USD', label: 'XAU/USD · GOLD', category: 'metals' },
  { pair: 'XAG/USD', label: 'XAG/USD · SILVER', category: 'metals' },
  { pair: 'XPT/USD', label: 'XPT/USD · PLATINUM', category: 'metals' },
  { pair: 'XCU/USD', label: 'XCU/USD · COPPER', category: 'metals' },
  { pair: 'SPX500/USD', label: 'SPX500 · S&P 500', category: 'indices' },
  { pair: 'NAS100/USD', label: 'NAS100 · NASDAQ', category: 'indices' },
  { pair: 'US30/USD', label: 'US30 · DOW 30', category: 'indices' },
  { pair: 'GER40/USD', label: 'GER40 · DAX 40', category: 'indices' },
  { pair: 'UK100/USD', label: 'UK100 · FTSE', category: 'indices' },
  { pair: 'JPN225/USD', label: 'JPN225 · NIKKEI', category: 'indices' },
  { pair: 'BTC/USD', label: 'BTC/USD', category: 'crypto' },
  { pair: 'ETH/USD', label: 'ETH/USD', category: 'crypto' },
  { pair: 'SOL/USD', label: 'SOL/USD', category: 'crypto' },
  { pair: 'XRP/USD', label: 'XRP/USD', category: 'crypto' },
];

const inferCategory = (p: string): string => {
  const base = (p || '').split('/')[0].toUpperCase();
  if (['XAU', 'XAG', 'XPT', 'XPD', 'XCU', 'PAXG'].includes(base)) return 'METALS';
  if (['SPX500', 'NAS100', 'US30', 'UK100', 'GER40', 'JPN225'].includes(base)) return 'INDICES';
  if (['EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD'].includes(base)) return 'FOREX';
  return 'CRYPTO';
};

const MirofishTerminal: React.FC<MirofishTerminalProps> = ({
  status,
  deliberations,
  pair,
  onPairChange,
  scanning,
  onRunScan,
  lastScanDecision,
  onOpenTab,
}) => {
  const [ticker, setTicker] = useState<KrakenTicker | null>(null);
  const [candles, setCandles] = useState<KrakenCandle[]>([]);
  const [watchboard, setWatchboard] = useState<Array<{ pair: string; category: string; last: number; change_percent: number; high_24h?: number; low_24h?: number }>>([]);
  const [marketCategoryFilter, setMarketCategoryFilter] = useState<'all' | 'forex' | 'metals' | 'indices' | 'crypto'>('all');
  const [timeframe, setTimeframe] = useState<1 | 5 | 15 | 60>(5);
  const [pulseLoading, setPulseLoading] = useState(false);
  const [pulseError, setPulseError] = useState('');
  const [topWinIndex, setTopWinIndex] = useState(0);
  const [countdown, setCountdown] = useState(15);

  const fetchKrakenPulse = useCallback(async (targetPair: string, targetInterval: number = timeframe) => {
    setPulseLoading(true);
    setPulseError('');
    try {
      const encoded = encodeURIComponent(targetPair);
      // Primary: backend multi-asset market overview (supports 1m/5m/15m/60m for Forex, Metals, Indices, and Crypto)
      const backendRes = await fetch(`${API_BASE_URL}/api/trading/market-overview?pair=${encoded}&interval=${targetInterval}`).catch(() => null);
      if (backendRes && backendRes.ok) {
        const overview = await backendRes.json();
        const t = overview?.ticker;
        if (t && typeof t.last === 'number') {
          const last = Number(t.last);
          const open24h = Number(t.open || last);
          const changeUsd = open24h > 0 ? last - open24h : 0;
          const changePct = typeof t.change_percent === 'number' ? t.change_percent : (open24h > 0 ? ((last - open24h) / open24h) * 100 : 0);
          setTicker({
            pair: targetPair,
            ask: Number(t.ask || last),
            bid: Number(t.bid || last),
            last,
            high24h: Number(t.high_24h || last),
            low24h: Number(t.low_24h || last),
            volume24h: Number(t.volume_24h || 0),
            open24h,
            changeUsd,
            changePct,
          });
        }
        if (Array.isArray(overview?.candles) && overview.candles.length > 0) {
          setCandles(
            overview.candles.slice(-40).map((c: any) => ({
              timestamp: Number(c.timestamp),
              open: Number(c.open),
              high: Number(c.high),
              low: Number(c.low),
              close: Number(c.close),
              vwap: Number(c.vwap || c.close),
              volume: Number(c.volume || 0),
            }))
          );
        }
        if (Array.isArray(overview?.tickers) && overview.tickers.length > 0) {
          setWatchboard(overview.tickers);
        }
        setCountdown(15);
        return;
      }

      // Fallback: direct Kraken public REST for Forex & Crypto
      const [tickerRes, ohlcRes] = await Promise.all([
        fetch(`https://api.kraken.com/0/public/Ticker?pair=${encoded}&assetVersion=1`),
        fetch(`https://api.kraken.com/0/public/OHLC?pair=${encoded}&interval=${targetInterval}&assetVersion=1`),
      ]);
      const tickerJson = await tickerRes.json();
      const ohlcJson = await ohlcRes.json();

      if (tickerJson?.error?.length) {
        throw new Error(tickerJson.error.join(', '));
      }
      const rawTicker = tickerJson?.result ? (Object.values(tickerJson.result)[0] as any) : null;
      if (rawTicker) {
        const last = parseFloat((rawTicker.c || [0])[0]);
        const open24h = parseFloat(rawTicker.o || 0);
        const ask = parseFloat((rawTicker.a || [0])[0]);
        const bid = parseFloat((rawTicker.b || [0])[0]);
        const high24h = parseFloat((rawTicker.h || [0, 0])[1]);
        const low24h = parseFloat((rawTicker.l || [0, 0])[1]);
        const volume24h = parseFloat((rawTicker.v || [0, 0])[1]);
        const changeUsd = open24h > 0 ? last - open24h : 0;
        const changePct = open24h > 0 ? ((last - open24h) / open24h) * 100 : 0;
        setTicker({
          pair: targetPair,
          ask,
          bid,
          last,
          high24h,
          low24h,
          volume24h,
          open24h,
          changeUsd,
          changePct,
        });
      }

      if (ohlcJson?.result) {
        const candleArr = Object.entries(ohlcJson.result).find(([k]) => k !== 'last')?.[1];
        if (Array.isArray(candleArr)) {
          const parsed: KrakenCandle[] = candleArr
            .slice(-32)
            .map((c: any) => ({
              timestamp: Number(c[0]),
              open: parseFloat(c[1]),
              high: parseFloat(c[2]),
              low: parseFloat(c[3]),
              close: parseFloat(c[4]),
              vwap: parseFloat(c[5]),
              volume: parseFloat(c[6]),
            }))
            .filter((c) => c.close > 0);
          setCandles(parsed);
        }
      }
      setCountdown(15);
    } catch (err: any) {
      setPulseError(err?.message || 'Live market feed temporarily unreachable');
    } finally {
      setPulseLoading(false);
    }
  }, [timeframe]);

  useEffect(() => {
    void fetchKrakenPulse(pair, timeframe);
    const refreshId = window.setInterval(() => {
      void fetchKrakenPulse(pair, timeframe);
    }, 15000);
    return () => window.clearInterval(refreshId);
  }, [pair, timeframe, fetchKrakenPulse]);

  useEffect(() => {
    const id = window.setInterval(() => {
      setCountdown((prev) => (prev <= 1 ? 15 : prev - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  const ledgerHistory = useMemo(
    () => (Array.isArray(status?.history) ? status.history : []),
    [status]
  );

  // Combine deliberations + latest scan decision for live visual feedback
  const allDeliberations = useMemo(() => {
    const list = Array.isArray(deliberations) ? [...deliberations] : [];
    if (lastScanDecision?.agents && !list.some((d) => d.timestamp === lastScanDecision.agents.timestamp)) {
      list.unshift({
        ...lastScanDecision.agents,
        pair: lastScanDecision.pair || pair,
        timestamp: new Date().toISOString(),
      });
    }
    return list;
  }, [deliberations, lastScanDecision, pair]);

  const latestDeliberation = allDeliberations[0] || null;
  const latestStrategy = latestDeliberation?.strategy || {};
  const latestTechnical = latestDeliberation?.technical_analysis || {};

  // Aggregate signal statistics from recorded deliberations & candles
  const signalStats = useMemo(() => {
    const totalDelibs = allDeliberations.length;
    const buyDelibs = allDeliberations.filter(
      (d) => String(d?.strategy?.action || d?.action || '').toUpperCase() === 'BUY'
    ).length;
    const sellDelibs = allDeliberations.filter(
      (d) => String(d?.strategy?.action || d?.action || '').toUpperCase() === 'SELL'
    ).length;
    const holdDelibs = Math.max(0, totalDelibs - buyDelibs - sellDelibs);

    const confidences = allDeliberations
      .map((d) => d?.strategy?.confidence)
      .filter((c): c is number => typeof c === 'number' && !Number.isNaN(c));
    const avgConfidence = confidences.length
      ? confidences.reduce((a, b) => a + b, 0) / confidences.length
      : typeof latestStrategy.confidence === 'number'
      ? latestStrategy.confidence
      : 0.78;

    // Candle directional split for hourly pulse
    const upCandles = candles.filter((c) => c.close >= c.open).length;
    const downCandles = Math.max(0, candles.length - upCandles);
    const candleUpRatio = candles.length ? upCandles / candles.length : 0.54;

    const pUp =
      String(latestStrategy.action || '').toUpperCase() === 'BUY'
        ? Math.max(0.55, Math.min(0.94, avgConfidence))
        : String(latestStrategy.action || '').toUpperCase() === 'SELL'
        ? Math.max(0.08, Math.min(0.45, 1 - avgConfidence))
        : Number(candleUpRatio.toFixed(2));
    const pDown = Number((1 - pUp).toFixed(2));

    const rsi =
      typeof latestTechnical.rsi_14 === 'number'
        ? latestTechnical.rsi_14
        : candles.length >= 14
        ? (() => {
            let gains = 0;
            let losses = 0;
            const slice = candles.slice(-15);
            for (let i = 1; i < slice.length; i++) {
              const diff = slice[i].close - slice[i - 1].close;
              if (diff >= 0) gains += diff;
              else losses -= diff;
            }
            if (losses === 0) return 70;
            const rs = gains / losses;
            return 100 - 100 / (1 + rs);
          })()
        : 52.4;

    const ema20 =
      typeof latestTechnical.ema_20 === 'number'
        ? latestTechnical.ema_20
        : candles.length
        ? candles.slice(-20).reduce((s, c) => s + c.close, 0) / Math.min(20, candles.length)
        : ticker?.last || 0;

    const ema50 =
      typeof latestTechnical.ema_50 === 'number'
        ? latestTechnical.ema_50
        : candles.length
        ? candles.reduce((s, c) => s + c.close, 0) / candles.length
        : ticker?.last || 0;

    const atr14 =
      typeof latestTechnical.atr_14 === 'number'
        ? latestTechnical.atr_14
        : candles.length
        ? candles.slice(-14).reduce((s, c) => s + (c.high - c.low), 0) / Math.min(14, candles.length)
        : 0;

    return {
      totalDelibs,
      buyDelibs,
      sellDelibs,
      holdDelibs,
      avgConfidence,
      upCandles,
      downCandles,
      pUp: Number(pUp.toFixed(2)),
      pDown,
      rsi,
      ema20,
      ema50,
      atr14,
      predictedAction: String(latestStrategy.action || (pUp >= 0.55 ? 'BUY' : pUp <= 0.42 ? 'SELL' : 'HOLD')).toUpperCase(),
    };
  }, [allDeliberations, candles, latestStrategy, latestTechnical, ticker]);

  // Cards for the Top Right "TOP SIGNALS / DELIBERATIONS" carousel
  const highlightCards = useMemo(() => {
    if (allDeliberations.length > 0) {
      return allDeliberations.slice(0, 6).map((d, idx) => {
        const strat = d.strategy || {};
        const tech = d.technical_analysis || {};
        const conf = typeof strat.confidence === 'number' ? strat.confidence : 0.75;
        const action = String(strat.action || d.action || 'HOLD').toUpperCase();
        const entryRef = tech.ema_20 || ticker?.open24h || ticker?.last || 0;
        const markRef = ticker?.last || entryRef;
        return {
          id: idx,
          pair: d.pair || d.symbol || pair,
          action,
          multiplier: (1 + conf * 0.5).toFixed(2),
          confidencePct: Math.round(conf * 100),
          deltaLabel:
            action === 'BUY'
              ? `▲ BUY · ${Math.round(conf * 100)}%`
              : action === 'SELL'
              ? `▼ SELL · ${Math.round(conf * 100)}%`
              : `◆ HOLD · ${Math.round(conf * 100)}%`,
          timestamp: d.timestamp ? new Date(d.timestamp).toLocaleString() : 'Live cycle',
          subtitle: `${tech.trend || 'Spot structure'} · RSI ${typeof tech.rsi_14 === 'number' ? tech.rsi_14.toFixed(1) : signalStats.rsi.toFixed(1)}`,
          entryPrice: entryRef,
          targetPrice: markRef,
        };
      });
    }
    return [
      {
        id: 0,
        pair,
        action: signalStats.predictedAction,
        multiplier: (1 + signalStats.avgConfidence * 0.45).toFixed(2),
        confidencePct: Math.round(signalStats.avgConfidence * 100),
        deltaLabel: ticker ? fmtSignedUsd(ticker.changeUsd) : 'LIVE SPOT',
        timestamp: 'Kraken 1H Spot Feed · Ready',
        subtitle: `EMA20 ${fmtUsd(signalStats.ema20)} · RSI ${signalStats.rsi.toFixed(1)}`,
        entryPrice: ticker?.open24h || 0,
        targetPrice: ticker?.last || 0,
      },
    ];
  }, [allDeliberations, pair, signalStats, ticker]);

  const activeHighlight = highlightCards[topWinIndex % highlightCards.length] || highlightCards[0];

  // Four mini-strip items at the bottom of the top-left Hero panel
  const heroMiniStrip = useMemo(() => {
    if (allDeliberations.length >= 1) {
      return allDeliberations.slice(0, 4).map((d, i) => {
        const act = String(d?.strategy?.action || d?.action || 'HOLD').toUpperCase();
        const conf = typeof d?.strategy?.confidence === 'number' ? Math.round(d.strategy.confidence * 100) : 75;
        const dt = d.timestamp ? new Date(d.timestamp) : new Date();
        const dateStr = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase();
        return {
          key: i,
          top: `${act} · ${conf}%`,
          bottom: `${dateStr} · ${d.pair || pair}`,
          positive: act === 'BUY',
        };
      });
    }
    // Otherwise show 4 recent hourly candle moves from Kraken OHLC
    const recentCandles = candles.slice(-4);
    if (recentCandles.length > 0) {
      return recentCandles.map((c, i) => {
        const diff = c.close - c.open;
        const dt = new Date(c.timestamp * 1000);
        const timeStr = dt.toISOString().slice(11, 16);
        return {
          key: i,
          top: fmtSignedUsd(diff),
          bottom: `${timeStr} UTC · ${ diff >= 0 ? 'UP' : 'DOWN' }`,
          positive: diff >= 0,
        };
      });
    }
    return [0, 1, 2, 3].map((i) => ({
      key: i,
      top: '—',
      bottom: `SLOT ${i + 1} · AWAITING`,
      positive: true,
    }));
  }, [allDeliberations, candles, pair]);

  // Lattice histogram buckets (10 buckets: 5 bear/left in terracotta, 5 bull/right in blue)
  const latticeBuckets = useMemo(() => {
    const p = signalStats.pUp;
    // Binomial-like weights tilted by pUp
    const raw = [
      Math.pow(1 - p, 4) * 0.45,
      Math.pow(1 - p, 3) * 0.75,
      Math.pow(1 - p, 2) * 1.15,
      (1 - p) * 1.55,
      (1 - p) * 2.1,
      p * 2.45,
      p * 2.05,
      Math.pow(p, 2) * 1.45,
      Math.pow(p, 3) * 0.85,
      Math.pow(p, 4) * 0.45,
    ];
    const maxVal = Math.max(...raw, 0.01);
    const labels = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10'];
    return raw.map((v, idx) => ({
      idx,
      label: labels[idx],
      heightPct: Math.max(8, Math.round((v / maxVal) * 100)),
      isBull: idx >= 5,
    }));
  }, [signalStats.pUp]);

  // Order book L1 / OHLC depth bars for Band 4
  const depthRows = useMemo(() => {
    const center = ticker?.last || 75000;
    const step = Math.max(center * 0.0012, 0.01);
    const rows = [];
    for (let i = 4; i >= 1; i--) {
      const price = center + step * i;
      const size = Number(((5 - i) * 18.4 + (i % 2) * 7.2).toFixed(1));
      rows.push({ side: 'ask' as const, price, size, fillPct: Math.min(95, 30 + (5 - i) * 15) });
    }
    for (let i = 1; i <= 4; i++) {
      const price = center - step * i;
      const size = Number((i * 21.6 + ((i + 1) % 2) * 9.1).toFixed(1));
      rows.push({ side: 'bid' as const, price, size, fillPct: Math.min(95, 35 + i * 14) });
    }
    return rows;
  }, [ticker]);

  // Price chart coordinates for Band 4
  const chartData = useMemo(() => {
    const pts = candles.length >= 4 ? candles.slice(-24) : [];
    if (!pts.length) {
      const base = ticker?.last || 74961.37;
      return {
        hasData: false,
        path: 'M 20 85 Q 160 72, 300 68 T 560 78',
        area: 'M 20 85 Q 160 72, 300 68 T 560 78 L 560 135 L 20 135 Z',
        targetY: 75,
        ticks: [base * 1.005, base * 1.002, base, base * 0.998, base * 0.995],
        timeLabels: ['T-4H', 'T-3H', 'T-2H', 'T-1H', 'NOW'],
        annotations: [] as Array<{ x: number; y: number; label: string; isBull: boolean }>,
      };
    }
    const closes = pts.map((c) => c.close);
    const refPrice = ticker?.open24h || closes[0];
    const minP = Math.min(...closes, refPrice) * 0.9992;
    const maxP = Math.max(...closes, refPrice) * 1.0008;
    const span = Math.max(maxP - minP, 1e-6);

    const width = 560;
    const height = 130;
    const padX = 16;
    const padY = 18;
    const plotW = width - padX * 2;
    const plotH = height - padY * 2;

    const toX = (i: number) => padX + (i / Math.max(1, pts.length - 1)) * plotW;
    const toY = (p: number) => padY + (1 - (p - minP) / span) * plotH;

    const coords = pts.map((c, i) => ({ x: toX(i), y: toY(c.close), close: c.close, open: c.open, ts: c.timestamp }));
    const path = coords.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(' ');
    const area = `${path} L ${coords[coords.length - 1].x.toFixed(1)} ${(height - 6).toFixed(1)} L ${coords[0].x.toFixed(1)} ${(height - 6).toFixed(1)} Z`;
    const targetY = Math.max(padY, Math.min(height - padY, toY(refPrice)));

    const ticks = [
      maxP,
      minP + span * 0.75,
      minP + span * 0.5,
      minP + span * 0.25,
      minP,
    ];

    const stepIdx = Math.max(1, Math.floor((pts.length - 1) / 5));
    const timeLabels: string[] = [];
    for (let i = 0; i < pts.length; i += stepIdx) {
      const d = new Date(pts[i].timestamp * 1000);
      timeLabels.push(d.toISOString().slice(11, 19));
    }

    // Pick 4 notable points along the curve for callouts matching the screenshot
    const annotations: Array<{ x: number; y: number; label: string; isBull: boolean }> = [];
    const pickIndices = [
      Math.floor(coords.length * 0.18),
      Math.floor(coords.length * 0.42),
      Math.floor(coords.length * 0.64),
      coords.length - 1,
    ];
    const seen = new Set<number>();
    pickIndices.forEach((idx) => {
      if (idx >= 0 && idx < coords.length && !seen.has(idx)) {
        seen.add(idx);
        const pt = coords[idx];
        const delta = pt.close - refPrice;
        annotations.push({
          x: pt.x,
          y: pt.y,
          label: fmtSignedUsd(delta),
          isBull: delta >= 0,
        });
      }
    });

    return {
      hasData: true,
      path,
      area,
      targetY,
      ticks,
      timeLabels: timeLabels.slice(0, 6),
      annotations,
    };
  }, [candles, ticker]);

  const paperPortfolio = status?.paper_portfolio || null;
  const openPositions: any[] = Array.isArray(paperPortfolio?.positions) ? paperPortfolio.positions : [];
  const placedOrders: any[] = Array.isArray(paperPortfolio?.recent_orders) && paperPortfolio.recent_orders.length
    ? paperPortfolio.recent_orders
    : ledgerHistory;

  const filteredQuickPairs = useMemo(
    () =>
      marketCategoryFilter === 'all'
        ? QUICK_PAIRS
        : QUICK_PAIRS.filter((item) => item.category === marketCategoryFilter),
    [marketCategoryFilter]
  );

  const watchboardByPair = useMemo(() => {
    const map: Record<string, { last: number; change_percent: number }> = {};
    watchboard.forEach((w) => {
      if (w && w.pair) map[w.pair] = { last: Number(w.last), change_percent: Number(w.change_percent || 0) };
    });
    return map;
  }, [watchboard]);

  const primaryDisplayValue =
    ticker
      ? fmtUsd(ticker.last)
      : paperPortfolio?.equity
      ? fmtUsd(Number(paperPortfolio.equity), 2)
      : '—';

  const primaryDisplaySub =
    ticker
      ? `${inferCategory(pair).toLowerCase()} live feed · 24h ${ticker.changePct >= 0 ? '+' : ''}${ticker.changePct.toFixed(2)}%`
      : 'live forex, metals, indices & crypto feed';

  const convergenceSegments = 16;
  const activeSegments = Math.round(signalStats.avgConfidence * convergenceSegments);

  return (
    <div className="mf-stack">
      {/* =====================================================================
          BAND 1: DUAL HERO CARD (PORTFOLIO/MARKET HERO + TOP SIGNALS CAROUSEL)
          ===================================================================== */}
      <section className="mf-card mf-band-hero">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
          <div style={{ display: 'flex', gap: '5px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="mf-eyebrow-text" style={{ marginRight: '4px' }}>ASSET CLASSES:</span>
            {([
              { id: 'all', label: 'ALL MARKETS (22)' },
              { id: 'forex', label: 'FOREX (8)' },
              { id: 'metals', label: 'METALS · GOLD/SILVER (4)' },
              { id: 'indices', label: 'INDICES · S&P/NAS/DOW (6)' },
              { id: 'crypto', label: 'CRYPTO (4)' },
            ] as const).map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setMarketCategoryFilter(cat.id)}
                className="mf-pill-action"
                style={
                  marketCategoryFilter === cat.id
                    ? { background: '#2563eb', color: '#ffffff', borderColor: '#2563eb' }
                    : undefined
                }
              >
                {cat.label}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '5px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="mf-eyebrow-text" style={{ marginRight: '2px' }}>SCALP TIMEFRAME:</span>
            {([
              { tf: 1, label: '⚡ 1M SCALP' },
              { tf: 5, label: '⚡ 5M SCALP' },
              { tf: 15, label: '15M' },
              { tf: 60, label: '1H' },
            ] as const).map((item) => (
              <button
                key={item.tf}
                type="button"
                onClick={() => setTimeframe(item.tf)}
                className="mf-pill-action"
                style={
                  timeframe === item.tf
                    ? { background: '#9a3412', color: '#ffffff', borderColor: '#9a3412' }
                    : undefined
                }
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px', paddingBottom: '10px', borderBottom: '1px solid #eef2f6' }}>
          {filteredQuickPairs.map((qp) => {
            const liveQuote = qp.pair === pair && ticker
              ? { last: ticker.last, change_percent: ticker.changePct }
              : watchboardByPair[qp.pair];
            const isSelected = qp.pair === pair;
            return (
              <button
                key={qp.pair}
                type="button"
                onClick={() => onPairChange(qp.pair)}
                className="mf-pill-action"
                style={
                  isSelected
                    ? { background: '#111827', color: '#ffffff', borderColor: '#111827', display: 'inline-flex', gap: '6px', alignItems: 'center' }
                    : { display: 'inline-flex', gap: '6px', alignItems: 'center' }
                }
              >
                <span>{qp.label}</span>
                {liveQuote && (
                  <span
                    style={{
                      fontSize: '0.66rem',
                      fontWeight: 800,
                      color: isSelected
                        ? (liveQuote.change_percent >= 0 ? '#93c5fd' : '#fca5a5')
                        : (liveQuote.change_percent >= 0 ? '#059669' : '#9a3412'),
                    }}
                  >
                    {fmtUsd(liveQuote.last)} ({liveQuote.change_percent >= 0 ? '+' : ''}{liveQuote.change_percent.toFixed(2)}%)
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="mf-hero-grid">
          {/* Left Column */}
          <div className="mf-hero-left">
            <div className="mf-eyebrow-row">
              <span className="mf-dot mf-dot-green" />
              <span className="mf-eyebrow-text">MUSE SPARK 1.3 · {inferCategory(pair)} TELEMETRY</span>
              <span className="mf-tag-outline">{pair} · {timeframe === 60 ? '1H' : `${timeframe}M SCALP`}</span>
              <span className="mf-tag-outline">● {inferCategory(pair)}</span>
              <span className="mf-tag-outline" style={{ color: '#9a3412', borderColor: '#fed7aa', background: '#fff7ed' }}>⚡ 1M/5M SCALPER</span>
            </div>

            <div className="mf-hero-big-number">{primaryDisplayValue}</div>

            <div className="mf-hero-meta-row">
              <span className="mf-mono-muted">{primaryDisplaySub}</span>
              {ticker && (
                <span className={ticker.changeUsd >= 0 ? 'mf-badge-blue' : 'mf-badge-amber'}>
                  {ticker.changeUsd >= 0 ? '▲' : '▼'} {fmtSignedUsd(ticker.changeUsd)} ({ticker.changePct >= 0 ? '+' : ''}{ticker.changePct.toFixed(2)}%)
                </span>
              )}
              <span className="mf-badge-blue">
                {Math.round(signalStats.pUp * 100)}% BULL BIAS
              </span>
              <span className="mf-badge-amber">
                RSI {signalStats.rsi.toFixed(1)}
              </span>
            </div>

            <div className="mf-hero-strip4">
              {heroMiniStrip.map((item) => (
                <div key={item.key} className="mf-strip4-cell">
                  <div className={item.positive ? 'mf-val-blue' : 'mf-val-terra'}>
                    {item.top}
                  </div>
                  <div className="mf-strip4-sub">{item.bottom}</div>
                </div>
              ))}
            </div>

            <div className="mf-hero-footer">
              <span className="mf-mono-muted">
                kraken spot · <strong>{pair} · 1H markets</strong>
              </span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  type="button"
                  className="mf-pill-action"
                  onClick={() => onOpenTab('paper')}
                >
                  PAPER DESK →
                </button>
                <span className="mf-pill-live-sm">● LOCKED · ANALYSIS ONLY</span>
              </div>
            </div>
          </div>

          {/* Right Column: Warm Cream Card */}
          <div className="mf-hero-right-cream">
            <div className="mf-cream-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="mf-dot mf-dot-terra" />
                <span className="mf-eyebrow-terra">
                  LATEST SIGNALS · {activeHighlight.pair} · KRAKEN
                </span>
              </div>
              <div className="mf-pager">
                <button
                  type="button"
                  className="mf-pager-btn"
                  onClick={() =>
                    setTopWinIndex((i) => (i - 1 + highlightCards.length) % highlightCards.length)
                  }
                  aria-label="Previous signal"
                >
                  ‹
                </button>
                <span>
                  {(topWinIndex % highlightCards.length) + 1} / {highlightCards.length}
                </span>
                <button
                  type="button"
                  className="mf-pager-btn"
                  onClick={() => setTopWinIndex((i) => (i + 1) % highlightCards.length)}
                  aria-label="Next signal"
                >
                  ›
                </button>
              </div>
            </div>

            <div className="mf-cream-delta-top">{activeHighlight.deltaLabel}</div>

            <div className="mf-cream-main">
              <div>
                <div className="mf-cream-mult">
                  ×{activeHighlight.multiplier.split('.')[0]}
                  <small>.{activeHighlight.multiplier.split('.')[1] || '00'}</small>
                </div>
                <div className="mf-mono-muted" style={{ marginTop: '4px' }}>
                  {activeHighlight.timestamp} · {activeHighlight.subtitle}
                </div>
                <div className="mf-cream-prices">
                  <div>
                    <div className="mf-micro-label">REFERENCE</div>
                    <div className="mf-price-dark">{fmtUsd(activeHighlight.entryPrice)}</div>
                  </div>
                  <span className="mf-arrow">→</span>
                  <div>
                    <div className="mf-micro-label">SPOT MARK</div>
                    <div className="mf-price-blue">{fmtUsd(activeHighlight.targetPrice)}</div>
                  </div>
                </div>
              </div>

              {/* Mini Sparkline Area Chart */}
              <div className="mf-cream-spark">
                <svg viewBox="0 0 180 70" className="mf-spark-svg">
                  <defs>
                    <linearGradient id="mfCreamGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity="0.28" />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M 8 62 Q 55 58, 92 46 T 172 12 L 172 64 L 8 64 Z"
                    fill="url(#mfCreamGrad)"
                  />
                  <path
                    d="M 8 62 Q 55 58, 92 46 T 172 12"
                    fill="none"
                    stroke="#2563eb"
                    strokeWidth="2.2"
                  />
                  <circle cx="172" cy="12" r="3.5" fill="#2563eb" />
                </svg>
                <div className="mf-dots-indicator">
                  {highlightCards.map((c, idx) => (
                    <span
                      key={c.id}
                      className={`mf-carousel-dot ${
                        idx === topWinIndex % highlightCards.length ? 'active' : ''
                      }`}
                      onClick={() => setTopWinIndex(idx)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================================
          BAND 1B: LIVE PORTFOLIO PROFIT, OPEN POSITIONS P&L & PLACED TRADES
          ===================================================================== */}
      <section className="mf-card">
        <div className="mf-section-bar">
          <div className="mf-section-title-left">
            <span className="mf-dot mf-dot-green" />
            <span className="mf-card-heading">
              Live Bot Portfolio, Open Positions &amp; Profit / Loss — {openPositions.length} Open · {paperPortfolio?.order_count ?? placedOrders.length} Placed Trades
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="mf-pill-live-sm">
              ● {paperPortfolio?.autopilot_enabled ? 'AUTOPILOT ACTIVE' : 'PAPER PORTFOLIO'}
            </span>
            <button
              type="button"
              className="mf-pill-action"
              onClick={() => onOpenTab('paper')}
            >
              MANAGE BOT &amp; ORDERS →
            </button>
          </div>
        </div>

        {/* 4 Portfolio & P&L Summary Strip */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '10px',
            marginBottom: '14px',
          }}
        >
          <div className="mf-subcard" style={{ background: '#f8fafc', padding: '12px 14px' }}>
            <div className="mf-micro-label">PORTFOLIO EQUITY (LIVE MARK)</div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#111827', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
              {paperPortfolio ? fmtUsd(Number(paperPortfolio.equity), 2) : '$100.00'}
            </div>
            <div className="mf-mono-muted" style={{ marginTop: '2px' }}>
              Initial {paperPortfolio ? fmtUsd(Number(paperPortfolio.initial_equity || 100), 2) : '$100.00'} · {paperPortfolio?.order_count ?? placedOrders.length} placed fills
            </div>
          </div>

          <div className="mf-subcard" style={{ background: '#f8fafc', padding: '12px 14px' }}>
            <div className="mf-micro-label">TOTAL PROFIT / LOSS (REALIZED + FLOATING)</div>
            {(() => {
              const totPnl = Number(paperPortfolio?.total_pnl ?? 0);
              const totPct = Number(paperPortfolio?.total_return_pct ?? 0);
              return (
                <>
                  <div
                    style={{
                      fontSize: '1.35rem',
                      fontWeight: 800,
                      color: totPnl >= 0 ? '#059669' : '#9a3412',
                      fontFamily: 'var(--font-mono)',
                      marginTop: '4px',
                    }}
                  >
                    {fmtSignedUsd(totPnl, 2)} ({totPct >= 0 ? '+' : ''}{totPct.toFixed(2)}%)
                  </div>
                  <div className="mf-mono-muted" style={{ marginTop: '2px' }}>
                    Floating {fmtSignedUsd(Number(paperPortfolio?.unrealized_pnl ?? 0), 2)} · Realized {fmtSignedUsd(Number(paperPortfolio?.realized_pnl ?? 0), 2)}
                  </div>
                </>
              );
            })()}
          </div>

          <div className="mf-subcard" style={{ background: '#f8fafc', padding: '12px 14px' }}>
            <div className="mf-micro-label">OPEN POSITIONS MARKET VALUE</div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#2563eb', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
              {paperPortfolio ? fmtUsd(Number(paperPortfolio.market_value), 2) : '$0.00'}
            </div>
            <div className="mf-mono-muted" style={{ marginTop: '2px' }}>
              {openPositions.length} active positions across FX, Metals, Indices &amp; Crypto
            </div>
          </div>

          <div className="mf-subcard" style={{ background: '#f8fafc', padding: '12px 14px' }}>
            <div className="mf-micro-label">AVAILABLE VIRTUAL CASH</div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#111827', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
              {paperPortfolio ? fmtUsd(Number(paperPortfolio.cash), 2) : '$100.00'}
            </div>
            <div className="mf-mono-muted" style={{ marginTop: '2px' }}>
              1× spot collateral · 20% max allocation per pair
            </div>
          </div>
        </div>

        {/* Two-column layout: Open Positions with Live P&L + Recent Placed Trades */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
            gap: '14px',
          }}
        >
          {/* Left: Open Positions & Live Floating Profit/Loss */}
          <div className="mf-subcard" style={{ padding: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span className="mf-micro-header" style={{ margin: 0 }}>
                OPEN POSITIONS · LIVE MARK &amp; FLOATING PROFIT ({openPositions.length})
              </span>
              <span className="mf-mono-muted" style={{ fontSize: '0.68rem' }}>
                Click any position to view chart
              </span>
            </div>
            {openPositions.length === 0 ? (
              <div className="mf-mono-muted" style={{ padding: '18px 0', textAlign: 'center' }}>
                No open positions yet. Start the bot or place a simulated trade in Paper Desk.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="mf-ledger-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>PAIR</th>
                      <th>CLASS</th>
                      <th>QTY</th>
                      <th>ENTRY</th>
                      <th>LIVE MARK</th>
                      <th>VALUE</th>
                      <th>FLOATING P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openPositions.map((pos: any) => {
                      const uPnl = Number(pos.unrealized_pnl_usd || 0);
                      const uPct = Number(pos.unrealized_pnl_pct || 0);
                      const cat = String(pos.category || inferCategory(pos.pair)).toUpperCase();
                      return (
                        <tr
                          key={pos.pair}
                          onClick={() => onPairChange(pos.pair)}
                          style={{
                            cursor: 'pointer',
                            background: pos.pair === pair ? '#eff6ff' : undefined,
                          }}
                        >
                          <td className="mf-td-strong">{pos.pair}</td>
                          <td>
                            <span className="mf-tag-outline" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                              {cat}
                            </span>
                          </td>
                          <td>{Number(pos.quantity).toFixed(4)}</td>
                          <td>{fmtUsd(Number(pos.average_entry))}</td>
                          <td style={{ fontWeight: 700, color: '#2563eb' }}>{fmtUsd(Number(pos.mark_price))}</td>
                          <td>{fmtUsd(Number(pos.market_value), 2)}</td>
                          <td
                            style={{
                              fontWeight: 800,
                              color: uPnl >= 0 ? '#059669' : '#9a3412',
                            }}
                          >
                            {fmtSignedUsd(uPnl, 2)} ({uPct >= 0 ? '+' : ''}{uPct.toFixed(2)}%)
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right: Recent Placed Trades & Fills */}
          <div className="mf-subcard" style={{ padding: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span className="mf-micro-header" style={{ margin: 0 }}>
                PLACED TRADES &amp; BOT EXECUTION TAPE ({placedOrders.length})
              </span>
              <span className="mf-mono-muted" style={{ fontSize: '0.68rem' }}>
                Simulated fills · Live orders locked
              </span>
            </div>
            {placedOrders.length === 0 ? (
              <div className="mf-mono-muted" style={{ padding: '18px 0', textAlign: 'center' }}>
                No placed trades recorded yet.
              </div>
            ) : (
              <div style={{ overflowX: 'auto', maxHeight: '260px', overflowY: 'auto' }}>
                <table className="mf-ledger-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>PAIR</th>
                      <th>SIDE</th>
                      <th>QTY</th>
                      <th>FILL PRICE</th>
                      <th>NOTIONAL</th>
                      <th>P&amp;L</th>
                      <th>TIME</th>
                    </tr>
                  </thead>
                  <tbody>
                    {placedOrders.slice(0, 12).map((ord: any, idx: number) => {
                      const oPair = ord.pair || ord.symbol || '—';
                      const oSide = String(ord.side || 'BUY').toUpperCase();
                      const oQty = Number(ord.quantity ?? ord.volume ?? 0);
                      const oPrice = Number(ord.fill_price ?? ord.price ?? 0);
                      const oGross = Number(ord.gross_usd ?? (oQty * oPrice));
                      const rPnl = ord.realized_pnl_usd !== null && ord.realized_pnl_usd !== undefined
                        ? Number(ord.realized_pnl_usd)
                        : null;
                      const ts = ord.timestamp || ord.time;
                      return (
                        <tr
                          key={ord.idempotency_key || ord.id || idx}
                          onClick={() => oPair !== '—' && onPairChange(oPair)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td className="mf-td-strong">{oPair}</td>
                          <td>
                            <span className={`mf-side-pill ${oSide === 'BUY' ? 'buy' : 'sell'}`}>
                              {oSide}
                            </span>
                          </td>
                          <td>{oQty.toFixed(4)}</td>
                          <td>{fmtUsd(oPrice)}</td>
                          <td>{fmtUsd(oGross, 2)}</td>
                          <td
                            style={{
                              fontWeight: 700,
                              color: rPnl === null ? '#64748b' : rPnl >= 0 ? '#059669' : '#9a3412',
                            }}
                          >
                            {rPnl === null ? 'OPEN' : fmtSignedUsd(rPnl, 2)}
                          </td>
                          <td className="mf-td-muted">
                            {ts ? new Date(ts).toISOString().slice(11, 19) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* =====================================================================
          BAND 2: PROBABILITY LATTICE (GALTON BOARD + HISTOGRAM)
          ===================================================================== */}
      <section className="mf-card">
        <div className="mf-section-bar">
          <div className="mf-section-title-left">
            <span className="mf-dot mf-dot-terra" />
            <span className="mf-card-heading">
              Probability Lattice — {allDeliberations.length || candles.length || 6} Evaluations, One Board
            </span>
          </div>
          <div className="mf-section-meta-right">
            EVERY SCAN = ONE BALL · 6 AGENT GATES · RISK ENGINE TILTS THE BOARD
          </div>
        </div>

        <div className="mf-lattice-grid">
          {/* Left Stats Column */}
          <div className="mf-lattice-sidebar">
            <div className="mf-micro-header">LIVE CONVERGENCE</div>
            <div className="mf-kv-row">
              <span>CYCLES EVALUATED</span>
              <strong>{allDeliberations.length || candles.length}</strong>
            </div>
            <div className="mf-kv-row">
              <span>LANDED BULLISH</span>
              <strong className="mf-val-green">{(signalStats.pUp * 100).toFixed(1)}%</strong>
            </div>
            <div className="mf-kv-row">
              <span>CONFIDENCE / SCAN</span>
              <strong className="mf-val-blue">{Math.round(signalStats.avgConfidence * 100)}%</strong>
            </div>
            <div className="mf-kv-row">
              <span>24H SPOT DELTA</span>
              <strong className={ticker && ticker.changeUsd < 0 ? 'mf-val-terra' : 'mf-val-blue'}>
                {ticker ? fmtSignedUsd(ticker.changeUsd) : '—'}
              </strong>
            </div>

            <div className="mf-kv-divider" />

            <div className="mf-kv-row">
              <span>LEDGER EVENTS</span>
              <strong>{ledgerHistory.length}</strong>
            </div>
            <div className="mf-kv-row">
              <span>EXECUTION GATE</span>
              <strong className="mf-val-blue">LOCKED</strong>
            </div>

            <div className="mf-sidebar-footnote">
              DETERMINISTIC RISK GATES — THE EDGE ONLY NEEDS DISCIPLINE
            </div>
          </div>

          {/* Right SVG Galton Board */}
          <div className="mf-lattice-canvas-wrap">
            <div className="mf-lattice-top-caption">
              <span>
                GATE LATTICE · 6 AGENTS · BIAS {signalStats.pUp >= 0.5 ? '+' : ''}
                {((signalStats.pUp - 0.5) * 100).toFixed(1)}%
              </span>
              <div className="mf-convergence-callout">
                <div className="mf-micro-label">CONVERGENCE · 6-AGENT PIPELINE</div>
                <div className="mf-callout-bar-row">
                  <div className="mf-callout-bar">
                    <div
                      className="mf-callout-bar-fill"
                      style={{ width: `${Math.round(signalStats.pUp * 100)}%` }}
                    />
                  </div>
                  <strong>{Math.round(signalStats.pUp * 100)}%</strong>
                </div>
              </div>
            </div>

            <svg viewBox="0 0 740 230" className="mf-lattice-svg" role="img" aria-label="Six-agent probability lattice">
              <defs>
                <linearGradient id="mfLeftTint" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#fff7ed" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#fee2e2" stopOpacity="0.45" />
                </linearGradient>
                <linearGradient id="mfRightTint" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#eff6ff" stopOpacity="0.65" />
                  <stop offset="100%" stopColor="#dbeafe" stopOpacity="0.25" />
                </linearGradient>
              </defs>

              {/* Left Bear/Reject Zone & Right Bull/Pass Zone */}
              <rect x="40" y="12" width="330" height="186" fill="url(#mfLeftTint)" rx="4" />
              <rect x="370" y="12" width="330" height="186" fill="url(#mfRightTint)" rx="4" />

              {/* Zone Headers */}
              <text x="275" y="28" fontSize="9.5" fontWeight="700" fill="#9a3412" fontFamily="monospace" letterSpacing="0.08em">
                BEAR / HOLD · {Math.round(signalStats.pDown * 100)}%
              </text>
              <text x="435" y="28" fontSize="9.5" fontWeight="700" fill="#2563eb" fontFamily="monospace" letterSpacing="0.08em">
                BULL / SIGNAL · {Math.round(signalStats.pUp * 100)}%
              </text>

              {/* Center Breakeven Dashed Line */}
              <line x1="370" y1="14" x2="370" y2="198" stroke="#475569" strokeWidth="1.3" strokeDasharray="3 3" />
              <rect x="334" y="14" width="72" height="16" rx="3" fill="#ffffff" stroke="#475569" strokeWidth="1" />
              <text x="370" y="25" fontSize="8.5" fontWeight="700" fill="#1e293b" textAnchor="middle" fontFamily="monospace">
                THRESHOLD
              </text>

              {/* Funnel at top */}
              <path d="M 358 6 L 366 18 M 382 6 L 374 18" stroke="#334155" strokeWidth="1.5" fill="none" />
              <circle cx="370" cy="11" r="3.2" fill="#111827" />

              {/* Triangular Peg Lattice (7 rows) */}
              {Array.from({ length: 7 }).map((_, row) => {
                const count = row + 2;
                const y = 38 + row * 17;
                const spacing = 36;
                const startX = 370 - ((count - 1) * spacing) / 2;
                return Array.from({ length: count }).map((__, col) => (
                  <circle
                    key={`peg-${row}-${col}`}
                    cx={startX + col * spacing}
                    cy={y}
                    r="2.2"
                    fill="#94a3b8"
                  />
                ));
              })}

              {/* Particle Trajectories & Falling Balls */}
              {[
                { d: 'M 370 18 Q 388 45, 412 76 T 456 135', endX: 456, endY: 135, bull: true },
                { d: 'M 370 18 Q 395 52, 428 88 T 492 142', endX: 492, endY: 142, bull: true },
                { d: 'M 370 18 Q 378 58, 396 95 T 418 148', endX: 418, endY: 148, bull: true },
                { d: 'M 370 18 Q 350 52, 326 92 T 292 145', endX: 292, endY: 145, bull: false },
                { d: 'M 370 18 Q 362 60, 344 104 T 335 150', endX: 335, endY: 150, bull: false },
                { d: 'M 370 18 Q 406 60, 464 102 T 535 148', endX: 535, endY: 148, bull: true },
              ].map((p, idx) => (
                <g key={idx}>
                  <path
                    d={p.d}
                    fill="none"
                    stroke={p.bull ? 'rgba(37, 99, 235, 0.28)' : 'rgba(154, 52, 18, 0.25)'}
                    strokeWidth="1.4"
                    strokeDasharray="2 2"
                  />
                  <circle
                    cx={p.endX}
                    cy={p.endY}
                    r="3.6"
                    fill={p.bull ? '#1e293b' : '#7c2d12'}
                    stroke="#ffffff"
                    strokeWidth="1"
                  />
                </g>
              ))}

              {/* Histogram Bars at the Bottom */}
              {latticeBuckets.map((b, i) => {
                const barW = 34;
                const gap = 8;
                const totalW = latticeBuckets.length * (barW + gap) - gap;
                const startX = 370 - totalW / 2;
                const x = startX + i * (barW + gap);
                const maxH = 62;
                const h = (b.heightPct / 100) * maxH;
                const y = 198 - h;
                return (
                  <g key={b.label}>
                    <rect
                      x={x}
                      y={y}
                      width={barW}
                      height={h}
                      rx="2"
                      fill={b.isBull ? '#2563eb' : '#9a3412'}
                      opacity={0.75 + (b.heightPct / 100) * 0.25}
                    />
                    <text
                      x={x + barW / 2}
                      y="213"
                      fontSize="8.5"
                      fill="#64748b"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {b.label}
                    </text>
                  </g>
                );
              })}

              <line x1="40" y1="198" x2="700" y2="198" stroke="#cbd5e1" strokeWidth="1" />
            </svg>
          </div>
        </div>
      </section>

      {/* =====================================================================
          BAND 3: RELATIONSHIP GRAPH SIMULATION (SIX-AGENT NETWORK GRAPH)
          ===================================================================== */}
      <section className="mf-card">
        <div className="mf-section-bar">
          <div className="mf-section-title-left">
            <span className="mf-dot mf-dot-terra" />
            <span className="mf-card-heading">
              VANTAGE POINT · RELATIONSHIP GRAPH SIMULATION
            </span>
          </div>
          <div className="mf-section-meta-right">
            <span>AGENTS <strong>6</strong></span>
            <span>NODES <strong>48</strong></span>
            <span>SIGNAL <strong>{(signalStats.avgConfidence * 100).toFixed(1)}%</strong></span>
            <span>CYCLE <strong>#{allDeliberations.length + 1}</strong></span>
          </div>
        </div>

        <div className="mf-graph-grid">
          {/* Left Column: Node Class Legend + Metrics */}
          <div className="mf-graph-left">
            <div className="mf-micro-header">NODE CLASS</div>
            <ul className="mf-legend-list">
              <li><span className="mf-swatch" style={{ background: '#9a3412' }} /> Bear signal</li>
              <li><span className="mf-swatch" style={{ background: '#2563eb' }} /> Bull signal</li>
              <li><span className="mf-swatch" style={{ background: '#78716c' }} /> Median path</li>
              <li><span className="mf-swatch" style={{ background: '#d97706' }} /> Catalyst / Tech</li>
              <li><span className="mf-swatch" style={{ background: '#111827' }} /> Agent hub</li>
            </ul>

            <div className="mf-kv-divider" />

            <div className="mf-kv-row">
              <span>BEAR SIGNALS</span>
              <strong className="mf-val-terra">{signalStats.sellDelibs + signalStats.downCandles}</strong>
            </div>
            <div className="mf-kv-row">
              <span>BULL SIGNALS</span>
              <strong className="mf-val-blue">{signalStats.buyDelibs + signalStats.upCandles}</strong>
            </div>
            <div className="mf-kv-row">
              <span>DELIBERATIONS</span>
              <strong>{allDeliberations.length}</strong>
            </div>
            <div className="mf-kv-row">
              <span>RSI (14)</span>
              <strong>{signalStats.rsi.toFixed(1)}</strong>
            </div>

            <div className="mf-convergence-block">
              <div className="mf-kv-row" style={{ borderBottom: 'none', paddingBottom: '2px' }}>
                <span>CONVERGENCE</span>
                <strong>{Math.round(signalStats.avgConfidence * 100)}%</strong>
              </div>
              <div className="mf-seg-bar">
                {Array.from({ length: convergenceSegments }).map((_, idx) => (
                  <span
                    key={idx}
                    className={`mf-seg ${idx < activeSegments ? 'on' : ''}`}
                  />
                ))}
              </div>
            </div>

            <div className="mf-kv-row" style={{ marginTop: '6px' }}>
              <span>PREDICTED</span>
              <strong
                className={
                  signalStats.predictedAction === 'SELL'
                    ? 'mf-val-terra'
                    : 'mf-val-blue'
                }
              >
                {signalStats.predictedAction === 'BUY'
                  ? '▲ BUY'
                  : signalStats.predictedAction === 'SELL'
                  ? '▼ SELL'
                  : '◆ HOLD'}
              </strong>
            </div>
          </div>

          {/* Center Network Graph SVG */}
          <div className="mf-graph-center">
            <svg viewBox="0 0 640 275" className="mf-network-svg" role="img" aria-label="Six-agent relationship graph">
              <defs>
                <pattern id="mfDotGrid" width="18" height="18" patternUnits="userSpaceOnUse">
                  <circle cx="2" cy="2" r="0.8" fill="#cbd5e1" />
                </pattern>
              </defs>
              <rect width="640" height="275" fill="url(#mfDotGrid)" rx="8" />

              {/* Radial Spokes from Cluster 1 (Bear/Risk Hub: 145, 118) */}
              {[
                { x: 52, y: 45, c: '#9a3412', l: 'STOP_GATE' },
                { x: 86, y: 36, c: '#9a3412', l: 'DRAWDOWN' },
                { x: 38, y: 84, c: '#9a3412', l: 'DAILY_LOSS' },
                { x: 42, y: 128, c: '#78716c', l: 'LEVERAGE_1X' },
                { x: 56, y: 168, c: '#9a3412', l: 'WHIPSAW' },
                { x: 95, y: 196, c: '#d97706', l: 'VOL_SHOCK' },
                { x: 185, y: 46, c: '#9a3412', l: 'SPREAD_BPS' },
                { x: 215, y: 74, c: '#2563eb', l: 'LIQUIDITY' },
                { x: 205, y: 165, c: '#78716c', l: 'EXPOSURE' },
              ].map((n, i) => (
                <g key={`c1-${i}`}>
                  <line x1="145" y1="118" x2={n.x} y2={n.y} stroke="#cbd5e1" strokeWidth="0.9" />
                  <circle cx={n.x} cy={n.y} r="3.4" fill={n.c} />
                  <text x={n.x + 5} y={n.y + 2.5} fontSize="6.5" fill="#64748b" fontFamily="monospace">
                    {n.l}
                  </text>
                </g>
              ))}

              {/* Radial Spokes from Cluster 2 (Technical Prime Hub: 305, 188) */}
              {[
                { x: 235, y: 235, c: '#2563eb', l: 'EMA_20' },
                { x: 270, y: 254, c: '#2563eb', l: 'EMA_50' },
                { x: 342, y: 252, c: '#d97706', l: 'RSI_14' },
                { x: 376, y: 228, c: '#2563eb', l: 'ATR_14' },
                { x: 248, y: 136, c: '#78716c', l: 'VWAP_1H' },
                { x: 358, y: 132, c: '#2563eb', l: 'MOMENTUM' },
                { x: 312, y: 112, c: '#d97706', l: 'EFFICIENCY' },
              ].map((n, i) => (
                <g key={`c2-${i}`}>
                  <line x1="305" y1="188" x2={n.x} y2={n.y} stroke="#cbd5e1" strokeWidth="0.9" />
                  <circle cx={n.x} cy={n.y} r="3.5" fill={n.c} />
                  <text x={n.x + 5} y={n.y + 2.5} fontSize="6.5" fill="#64748b" fontFamily="monospace">
                    {n.l}
                  </text>
                </g>
              ))}

              {/* Radial Spokes from Cluster 3 (Strategy & Catalyst Ring: 465, 118) */}
              {[
                { x: 405, y: 44, c: '#2563eb', l: 'MUSE_SPARK' },
                { x: 455, y: 34, c: '#2563eb', l: 'MARKET_INTEL' },
                { x: 518, y: 42, c: '#d97706', l: 'STRATEGY_AI' },
                { x: 554, y: 74, c: '#2563eb', l: 'ORDER_BOOK' },
                { x: 562, y: 158, c: '#2563eb', l: 'CONFIDENCE' },
                { x: 525, y: 196, c: '#78716c', l: 'AUDIT_LOG' },
                { x: 442, y: 205, c: '#2563eb', l: 'PERF_LEDGER' },
                { x: 396, y: 82, c: '#9a3412', l: 'RISK_ADVISOR' },
              ].map((n, i) => (
                <g key={`c3-${i}`}>
                  <line x1="465" y1="118" x2={n.x} y2={n.y} stroke="#cbd5e1" strokeWidth="0.9" />
                  <circle cx={n.x} cy={n.y} r="3.5" fill={n.c} />
                  <text x={n.x + 5} y={n.y + 2.5} fontSize="6.5" fill="#64748b" fontFamily="monospace">
                    {n.l}
                  </text>
                </g>
              ))}

              {/* Soft S-Curve Envelope & Bold Dashed Median Path */}
              <path
                d="M 145 118 C 215 100, 255 155, 305 150 C 360 145, 405 110, 465 118 L 575 114"
                fill="none"
                stroke="rgba(154, 52, 18, 0.14)"
                strokeWidth="12"
                strokeLinecap="round"
              />
              <path
                d="M 145 118 C 215 100, 255 155, 305 150 C 360 145, 405 110, 465 118 L 575 114"
                fill="none"
                stroke="#7c2d12"
                strokeWidth="2"
                strokeDasharray="5 4"
              />

              {/* Hub 1: Risk / Bear Cluster */}
              <circle cx="145" cy="118" r="14" fill="#9a3412" />
              <rect x="98" y="136" width="94" height="15" rx="3" fill="#ffffff" stroke="#9a3412" strokeWidth="1" />
              <text x="145" y="146.5" fontSize="7.5" fontWeight="700" fill="#7c2d12" textAnchor="middle" fontFamily="monospace">
                RISK_CLUSTER
              </text>

              {/* Hub 2: Technical Hub Prime */}
              <circle cx="305" cy="188" r="18" fill="#111827" />
              <rect x="262" y="210" width="86" height="15" rx="3" fill="#ffffff" stroke="#111827" strokeWidth="1" />
              <text x="305" y="220.5" fontSize="7.5" fontWeight="700" fill="#111827" textAnchor="middle" fontFamily="monospace">
                HUB_TECHNICAL
              </text>

              {/* Hub 3: Strategy / Catalyst Ring */}
              <circle cx="465" cy="118" r="15" fill="#292524" />
              <rect x="415" y="137" width="100" height="15" rx="3" fill="#ffffff" stroke="#292524" strokeWidth="1" />
              <text x="465" y="147.5" fontSize="7.5" fontWeight="700" fill="#111827" textAnchor="middle" fontFamily="monospace">
                STRATEGY_RING
              </text>

              {/* Terminal Decision Box on Right */}
              <rect x="562" y="103" width="68" height="22" rx="3" fill="#ffffff" stroke="#111827" strokeWidth="1.3" />
              <text x="596" y="117" fontSize="8.5" fontWeight="800" fill="#111827" textAnchor="middle" fontFamily="monospace">
                {signalStats.predictedAction} ▲
              </text>
            </svg>
          </div>

          {/* Right Column: Probabilities + 24H Edge Distribution */}
          <div className="mf-graph-right">
            <div className="mf-prob-row">
              <span>P(UP)</span>
              <strong className="mf-prob-val mf-val-blue">{signalStats.pUp.toFixed(2)}</strong>
            </div>
            <div className="mf-prob-row">
              <span>P(DOWN)</span>
              <strong className="mf-prob-val mf-val-terra">{signalStats.pDown.toFixed(2)}</strong>
            </div>
            <div className="mf-prob-row">
              <span>EDGE VS BOOK</span>
              <strong className="mf-prob-val mf-val-blue">
                +{Math.round(Math.abs(signalStats.pUp - 0.5) * 100)}¢
              </strong>
            </div>
            <div className="mf-prob-row">
              <span>CONFIDENCE</span>
              <strong className="mf-prob-val">{(signalStats.avgConfidence * 100).toFixed(1)}%</strong>
            </div>

            <div className="mf-edge-dist">
              <div className="mf-micro-header" style={{ marginBottom: '6px' }}>
                EDGE DISTRIBUTION · 24H
              </div>
              <div className="mf-mini-hist">
                {[
                  { h: 22, bull: false },
                  { h: 38, bull: false },
                  { h: 58, bull: false },
                  { h: 82, bull: false },
                  { h: 100, bull: true },
                  { h: 86, bull: true },
                  { h: 62, bull: true },
                  { h: 38, bull: true },
                  { h: 20, bull: true },
                ].map((bar, idx) => (
                  <div
                    key={idx}
                    className="mf-mini-hist-bar"
                    style={{
                      height: `${bar.h}%`,
                      background: bar.bull ? '#2563eb' : '#9a3412',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================================
          BAND 4: HOURLY PULSE (LIVE KRAKEN TICKER, ORDER BOOK L2 & PRICE CHART)
          ===================================================================== */}
      <section className="mf-card">
        <div className="mf-pulse-toprow">
          <div className="mf-pulse-title-group">
            <h2 className="mf-pulse-heading">{pair} {timeframe === 60 ? '1H' : `${timeframe}m Scalp`} Pulse</h2>
            <span className="mf-pill-live-sm">● LIVE {timeframe === 60 ? '1H' : `${timeframe}M`}</span>
            <span className="mf-tag-outline">Round {allDeliberations.length + candles.length}</span>
            <span
              className={`mf-tag-outline ${
                ticker && ticker.changeUsd < 0 ? 'mf-val-terra' : 'mf-val-green'
              }`}
            >
              {ticker
                ? `${ticker.changeUsd >= 0 ? '▲' : '▼'} ${fmtUsd(Math.abs(ticker.changeUsd))}`
                : '▲ $0.00'}
            </span>
            <button
              type="button"
              className="mf-icon-refresh"
              onClick={() => void fetchKrakenPulse(pair, timeframe)}
              title="Refresh market feed"
            >
              <RefreshCw size={13} className={pulseLoading ? 'mf-spin' : ''} />
            </button>
          </div>
          <div className="mf-pulse-clock">
            00:{String(countdown).padStart(2, '0')}
          </div>
        </div>

        {pulseError && (
          <div className="mf-pulse-notice">
            {pulseError} — displaying cached or baseline telemetry.
          </div>
        )}

        {/* Second Row: Price to Beat (24H Open), Current Price, Up/Down Split Boxes */}
        <div className="mf-pulse-metrics-row">
          <div className="mf-pulse-price-block">
            <div className="mf-micro-label">24H OPEN · REFERENCE</div>
            <div className="mf-reference-price">
              {ticker ? fmtUsd(ticker.open24h) : '—'}
            </div>
          </div>

          <div className="mf-pulse-price-block mf-pulse-current-block">
            <div className="mf-micro-label">CURRENT KRAKEN PRICE</div>
            <div className="mf-current-price">
              {ticker ? fmtUsd(ticker.last) : '—'}
            </div>
            {ticker && (
              <span
                className={`mf-price-delta-pill ${
                  ticker.changeUsd >= 0 ? 'up' : 'down'
                }`}
              >
                {ticker.changeUsd >= 0 ? '▲' : '▼'} {fmtSignedUsd(ticker.changeUsd)} (
                {ticker.changePct >= 0 ? '+' : ''}
                {ticker.changePct.toFixed(2)}%)
              </span>
            )}
          </div>

          <div className="mf-updown-boxes">
            <div className="mf-ud-box">
              <div className="mf-ud-label mf-val-blue">▲ UP</div>
              <div className="mf-ud-val mf-val-blue">{Math.round(signalStats.pUp * 100)}¢</div>
              <div className="mf-ud-bar">
                <div
                  style={{
                    width: `${Math.round(signalStats.pUp * 100)}%`,
                    background: '#2563eb',
                  }}
                />
              </div>
            </div>
            <div className="mf-ud-box">
              <div className="mf-ud-label mf-val-terra">▼ DOWN</div>
              <div className="mf-ud-val mf-val-terra">{Math.round(signalStats.pDown * 100)}¢</div>
              <div className="mf-ud-bar">
                <div
                  style={{
                    width: `${Math.round(signalStats.pDown * 100)}%`,
                    background: '#9a3412',
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Third Row: Order Book L2 Depth + Main Annotated Price Trajectory Chart */}
        <div className="mf-pulse-chart-grid">
          {/* Left: Order Book L2 */}
          <div className="mf-orderbook">
            <div className="mf-ob-head">
              <span>ORDER BOOK · L2</span>
            </div>
            <div className="mf-ob-subhead">
              <span>PRICE</span>
              <span>SIZE</span>
            </div>
            <div className="mf-ob-rows">
              {depthRows.map((row, idx) => (
                <div key={idx} className="mf-ob-row">
                  <div
                    className="mf-ob-fill"
                    style={{
                      width: `${row.fillPct}%`,
                      background:
                        row.side === 'ask'
                          ? 'rgba(154, 52, 18, 0.12)'
                          : 'rgba(37, 99, 235, 0.12)',
                    }}
                  />
                  <span
                    className={
                      row.side === 'ask' ? 'mf-ob-price ask' : 'mf-ob-price bid'
                    }
                  >
                    {row.price >= 500
                      ? row.price.toFixed(0)
                      : row.price >= 10
                      ? row.price.toFixed(3)
                      : row.price.toFixed(5)}
                  </span>
                  <span className="mf-ob-size">{row.size.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Annotated Price Chart */}
          <div className="mf-chart-wrap">
            <svg viewBox="0 0 640 150" className="mf-pulse-svg" role="img" aria-label="Hourly price trajectory">
              {/* Horizontal Grid Lines */}
              {[22, 48, 74, 100, 124].map((y, idx) => (
                <line
                  key={idx}
                  x1="16"
                  y1={y}
                  x2="565"
                  y2={y}
                  stroke="#eef2f6"
                  strokeWidth="1"
                />
              ))}

              {/* Shaded Volatility Band */}
              <path d={chartData.area} fill="rgba(37, 99, 235, 0.06)" />

              {/* Target / 24h Open Dashed Line */}
              <line
                x1="16"
                y1={chartData.targetY}
                x2="565"
                y2={chartData.targetY}
                stroke="#334155"
                strokeWidth="1.2"
                strokeDasharray="4 4"
              />

              {/* Price Curve */}
              <path
                d={chartData.path}
                fill="none"
                stroke="#111827"
                strokeWidth="2"
              />

              {/* Annotated Callout Pills along the Curve */}
              {chartData.annotations.map((ann, idx) => (
                <g key={idx}>
                  <circle
                    cx={ann.x}
                    cy={ann.y}
                    r="3.5"
                    fill="#ffffff"
                    stroke={ann.isBull ? '#2563eb' : '#9a3412'}
                    strokeWidth="2"
                  />
                  <rect
                    x={Math.max(18, Math.min(505, ann.x - 28))}
                    y={ann.y > 42 ? ann.y - 22 : ann.y + 8}
                    width="56"
                    height="15"
                    rx="7.5"
                    fill={ann.isBull ? '#eff6ff' : '#fff7ed'}
                    stroke={ann.isBull ? '#bfdbfe' : '#fed7aa'}
                    strokeWidth="1"
                  />
                  <text
                    x={Math.max(46, Math.min(533, ann.x))}
                    y={ann.y > 42 ? ann.y - 12 : ann.y + 18}
                    fontSize="7.5"
                    fontWeight="700"
                    fill={ann.isBull ? '#2563eb' : '#9a3412'}
                    textAnchor="middle"
                    fontFamily="monospace"
                  >
                    {ann.label}
                  </text>
                </g>
              ))}

              {/* Right Axis TARGET Black Pill */}
              <rect
                x="530"
                y={chartData.targetY - 9}
                width="44"
                height="18"
                rx="3"
                fill="#111827"
              />
              <text
                x="552"
                y={chartData.targetY + 3}
                fontSize="8"
                fontWeight="800"
                fill="#ffffff"
                textAnchor="middle"
                fontFamily="monospace"
              >
                TARGET
              </text>

              {/* Right Price Axis Labels */}
              {chartData.ticks.map((t, idx) => {
                const y = 22 + idx * 25;
                return (
                  <text
                    key={idx}
                    x="634"
                    y={y}
                    fontSize="8.5"
                    fill="#64748b"
                    textAnchor="end"
                    fontFamily="monospace"
                  >
                    {fmtUsd(t, t >= 500 ? 0 : t >= 10 ? 3 : 5)}
                  </text>
                );
              })}

              {/* Bottom Time Axis Labels */}
              {chartData.timeLabels.map((lbl, idx) => {
                const x = 36 + idx * 96;
                return (
                  <text
                    key={idx}
                    x={x}
                    y="144"
                    fontSize="8"
                    fill="#94a3b8"
                    textAnchor="middle"
                    fontFamily="monospace"
                  >
                    {lbl}
                  </text>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Bottom Pulse Strength Bar & Floating Terracotta Pill */}
        <div className="mf-pulse-footer">
          <div className="mf-pulse-strength">
            <span className="mf-micro-label">PULSE STRENGTH</span>
            <div className="mf-strength-bars">
              {Array.from({ length: 12 }).map((_, i) => (
                <span
                  key={i}
                  className={`mf-sbar ${
                    i < Math.round(signalStats.avgConfidence * 12) ? 'on' : ''
                  }`}
                />
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="mf-scan-cta"
              onClick={onRunScan}
              disabled={scanning}
            >
              {scanning ? 'RUNNING 6-AGENT SCAN…' : `RUN 6-AGENT SCAN (${pair})`}
            </button>
            <div className="mf-terra-floating-pill">
              <span className="mf-dot mf-dot-amber" />
              MUSE SPARK 1.3 · SIX-AGENT CORE
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default MirofishTerminal;
