import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Bot, Clock, PauseCircle, PlayCircle, RefreshCw, ShieldCheck, TrendingDown, TrendingUp, Zap } from 'lucide-react';
import { API_BASE_URL } from '../config';
import { FOREX_PAIRS, METAL_PAIRS, INDEX_PAIRS, CRYPTO_PAIRS, ALL_TRADING_PAIRS } from '../App';

type Position = {
  pair: string;
  category?: string;
  quantity: string;
  average_entry: string;
  mark_price: string;
  market_value: string;
  unrealized_pnl_usd?: string;
  unrealized_pnl_pct?: number;
  stop_loss?: string | null;
  take_profit?: string | null;
};

type AutopilotStatus = {
  enabled: boolean;
  worker_configured: boolean;
  worker_running: boolean;
  paper_trading_enabled: boolean;
  monitor_interval_seconds: number;
  scan_interval_seconds: number;
  pairs: string[];
  execution_mode: string;
  live_execution_enabled: boolean;
};

type AutopilotRun = {
  timestamp: string;
  status: string;
  pairs_checked?: number;
  results?: Array<{ pair: string; decision: string; reason?: string; fill?: { side: string; fill_price: string; quantity: string } }>;
  protective_exits?: Array<{ pair: string; triggered_by?: string; fill_price?: string }>;
};

type Account = {
  mode: string;
  currency: string;
  cash: string;
  market_value: string;
  equity: string;
  realized_pnl: string;
  unrealized_pnl?: string;
  total_pnl?: string;
  total_return_pct?: number;
  order_count: number;
  positions: Position[];
  execution_enabled: boolean;
  exchange_order_submitted: boolean;
};

type PaperDiagnostics = {
  database_name: string;
  account_exists: boolean;
  account_version: number;
  fill_count: number;
  open_position_count: number;
  autopilot_enabled: boolean;
  execution_mode: string;
  execution_enabled: boolean;
  exchange_order_submitted: boolean;
  server_time: string;
};

type LatestAnalysis = {
  pair: string;
  action: string;
  confidence: number | null;
  timestamp: string;
  reasoning: string;
  rsi_14?: number | null;
  trend?: string | null;
};

const money = (value: string | number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value || 0));

const priceFmt = (value: string | number) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return String(value);
  if (num >= 500) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
  }
  if (num >= 10) {
    return new Intl.NumberFormat('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(num);
  }
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 5, maximumFractionDigits: 5 }).format(num);
};


type Candle = { timestamp: number; open: number; high: number; low: number; close: number };
type TradeMarker = { timestamp: string; side: string; fill_price: string; pair: string; event_type?: string; triggered_by?: string };
const CandleChart: React.FC<{ candles: Candle[]; trades: TradeMarker[]; position?: Position; currentPrice?: number }> = ({ candles, trades, position, currentPrice }) => {
  if (!candles.length) return <div className="pb-muted" style={{ padding: 28, textAlign: 'center' }}>Waiting for market candles…</div>;
  const width = 1100, height = 360, left = 18, right = 18, top = 18, bottom = 34;
  const plotW = width - left - right, plotH = height - top - bottom;
  const prices = candles.flatMap(c => [c.high, c.low]).filter(Number.isFinite);
  const levels = [...prices, ...trades.map(t => Number(t.fill_price)), ...(position ? [Number(position.stop_loss), Number(position.take_profit)] : []), ...(currentPrice ? [currentPrice] : [])].filter(v => Number.isFinite(v) && v > 0);
  const min = Math.min(...levels), max = Math.max(...levels), pad = Math.max((max - min) * 0.08, max * 0.0002);
  const low = min - pad, high = max + pad, range = high - low || 1;
  const y = (price: number) => top + ((high - price) / range) * plotH;
  const step = plotW / candles.length, bodyW = Math.max(3, Math.min(12, step * 0.62));
  const markerFor = (trade: TradeMarker) => {
    const ts = new Date(trade.timestamp).getTime() / 1000;
    let best = 0, distance = Infinity;
    candles.forEach((c, i) => { const d = Math.abs(c.timestamp - ts); if (d < distance) { best = i; distance = d; } });
    return { x: left + best * step + step / 2, y: y(Number(trade.fill_price)), trade };
  };
  const firstTs = candles[0].timestamp, lastTs = candles[candles.length - 1].timestamp;
  const visibleTrades = trades.filter(t => { const ts = new Date(t.timestamp).getTime() / 1000; return t.pair === (position?.pair || trades[0]?.pair) && ts >= firstTs && ts <= lastTs; }).slice(0, 100);
  return <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Live candlestick chart with paper trade markers" style={{ width: '100%', height: 'auto', display: 'block', background: '#0b1220', borderRadius: 10 }}>
    {[0,1,2,3,4].map(i => { const yy = top + i * plotH / 4; const value = high - i * range / 4; return <g key={i}><line x1={left} x2={width-right} y1={yy} y2={yy} stroke="#253247" strokeDasharray="3 5"/><text x={width-right} y={yy-4} textAnchor="end" fill="#9aa9bd" fontSize="11">{priceFmt(value)}</text></g>; })}
    {position?.stop_loss && <g><line x1={left} x2={width-right} y1={y(Number(position.stop_loss))} y2={y(Number(position.stop_loss))} stroke="#fb7185" strokeDasharray="7 4"/><text x={left+4} y={y(Number(position.stop_loss))-5} fill="#fb7185" fontSize="11">STOP {priceFmt(position.stop_loss)}</text></g>}
    {position?.take_profit && <g><line x1={left} x2={width-right} y1={y(Number(position.take_profit))} y2={y(Number(position.take_profit))} stroke="#34d399" strokeDasharray="7 4"/><text x={left+4} y={y(Number(position.take_profit))-5} fill="#34d399" fontSize="11">TARGET {priceFmt(position.take_profit)}</text></g>}
    {candles.map((c,i) => { const x = left + i*step + step/2; const up = c.close >= c.open; const color = up ? '#22c58b' : '#fb7185'; const bodyY = Math.min(y(c.open), y(c.close)); const bodyH = Math.max(1.5, Math.abs(y(c.open)-y(c.close))); return <g key={c.timestamp}><line x1={x} x2={x} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth="1.4"/><rect x={x-bodyW/2} y={bodyY} width={bodyW} height={bodyH} fill={color} rx="1"/></g>; })}
    {currentPrice && <g><line x1={left} x2={width-right} y1={y(currentPrice)} y2={y(currentPrice)} stroke="#60a5fa" strokeDasharray="4 4"/><text x={left+4} y={y(currentPrice)-6} fill="#60a5fa" fontSize="11">MARK {priceFmt(currentPrice)}</text></g>}
    {visibleTrades.map((t,i) => { const p = markerFor(t); const buy = t.side === 'BUY'; return <g key={`${t.timestamp}-${i}`}><circle cx={p.x} cy={p.y} r="7" fill={buy ? '#2563eb' : '#dc2626'} stroke="#fff" strokeWidth="1.5"/><text x={p.x} y={p.y-11} textAnchor="middle" fill="#fff" fontSize="11" fontWeight="700">{buy ? 'B' : 'S'} {priceFmt(t.fill_price)}</text></g>; })}
    <text x={left} y={height-8} fill="#9aa9bd" fontSize="11">{new Date(candles[0].timestamp*1000).toLocaleString()}</text>
    <text x={width-right} y={height-8} textAnchor="end" fill="#9aa9bd" fontSize="11">{new Date(candles[candles.length-1].timestamp*1000).toLocaleString()}</text>
  </svg>;
};

const PaperTrading: React.FC = () => {
  const [token, setToken] = useState(() => {
    try {
      return window.sessionStorage.getItem('vp-paper-token') || '';
    } catch {
      return '';
    }
  });
  const [account, setAccount] = useState<Account | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [autopilot, setAutopilot] = useState<AutopilotStatus | null>(null);
  const [autopilotRuns, setAutopilotRuns] = useState<AutopilotRun[]>([]);
  const [diagnostics, setDiagnostics] = useState<PaperDiagnostics | null>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<LatestAnalysis | null>(null);
  const [utcNow, setUtcNow] = useState('');
  const [pair, setPair] = useState('EUR/USD');
  const [candleInterval, setCandleInterval] = useState(5);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [marketPrice, setMarketPrice] = useState<number | undefined>();
  const [marketSource, setMarketSource] = useState('');
  const [marketError, setMarketError] = useState('');
  const [marketFeedStatus, setMarketFeedStatus] = useState('connecting');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('10');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Keep the operator's paper access token for this browser tab session so a
  // page refresh reconnects automatically. sessionStorage is cleared when the
  // tab session ends; the token is never written to persistent localStorage.
  useEffect(() => {
    try {
      if (token.trim()) window.sessionStorage.setItem('vp-paper-token', token.trim());
      else window.sessionStorage.removeItem('vp-paper-token');
    } catch {
      // Storage can be unavailable in restricted browsing contexts.
    }
  }, [token]);

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    const response = await fetch(`${API_BASE_URL}/api/trading/paper/${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-Paper-Token': token,
        ...(init.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Paper service returned ${response.status}`);
    return data;
  }, [token]);

  const refresh = useCallback(async (silent = false) => {
    try {
      const boardroomRes = await fetch(`${API_BASE_URL}/api/trading/boardroom`);
      const boardroom = boardroomRes.ok ? await boardroomRes.json() : [];
      const latest = Array.isArray(boardroom) && boardroom.length ? boardroom[boardroom.length - 1] : null;
      if (!latest) {
        setLatestAnalysis(null);
      } else {
        const strategy = latest.strategy || {};
        const technical = latest.technical_analysis || {};
        setLatestAnalysis({
          pair: latest.pair || latest.symbol || '—',
          action: String(strategy.action || latest.action || 'HOLD').toUpperCase(),
          confidence: typeof strategy.confidence === 'number' ? strategy.confidence : null,
          timestamp: latest.timestamp || '',
          reasoning: String(strategy.rationale || latest.reasoning || 'No reasoning provided.'),
          rsi_14: typeof technical.rsi_14 === 'number' ? technical.rsi_14 : null,
          trend: typeof technical.trend === 'string' ? technical.trend : null,
        });
      }
    } catch {
      setLatestAnalysis(null);
    }
    if (!token.trim()) {
      setAccount(null);
      setOrders([]);
      setAutopilot(null);
      setAutopilotRuns([]);
      setDiagnostics(null);
      if (!silent) setError('Enter the paper-trading access token configured by the operator.');
      return;
    }
    if (!silent) setBusy(true);
    setError('');
    try {
      const [summary, history, autoStatus, autoRuns, storage] = await Promise.all([
        request('account'),
        request('orders?limit=10000'),
        request('autopilot'),
        request('autopilot/runs'),
        request('diagnostics'),
      ]);
      setAccount(summary);
      setOrders(Array.isArray(history) ? history : []);
      setAutopilot(autoStatus);
      setAutopilotRuns(Array.isArray(autoRuns) ? autoRuns : []);
      setDiagnostics(storage);
      if (!silent) setMessage('Paper account and autonomous trading status refreshed from the authoritative MongoDB store.');
    } catch (err: any) {
      // Never leave a previous portfolio visible when the current authoritative
      // account refresh fails; stale balances and fills can look like live state.
      setAccount(null);
      setOrders([]);
      setAutopilot(null);
      setAutopilotRuns([]);
      setDiagnostics(null);
      setError(err.message || 'Unable to load the paper account.');
    } finally {
      if (!silent) setBusy(false);
    }
  }, [request, token]);

  useEffect(() => {
    if (!token.trim() || !autopilot?.enabled) return;
    const timer = window.setInterval(() => { void refresh(true); }, 30000);
    return () => window.clearInterval(timer);
  }, [autopilot?.enabled, token, refresh]);

  useEffect(() => {
    if (token.trim()) void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | undefined;
    let poll: number | undefined;
    let reconnectTimer: number | undefined;
    const isKrakenSpot = CRYPTO_PAIRS.includes(pair);
    const loadCandles = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/trading/market-overview?pair=${encodeURIComponent(pair)}&interval=${candleInterval}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Market data returned ${response.status}`);
        if (active) {
          setCandles(Array.isArray(data.candles) ? data.candles : []);
          setMarketPrice(Number(data.ticker?.last) || undefined);
          setMarketSource(String(data.ticker?.source || 'market feed'));
          setMarketError('');
          setMarketFeedStatus(isKrakenSpot ? 'connecting to Kraken stream' : 'snapshot feed · not streaming');
        }
      } catch (err: any) {
        if (active) {
          setMarketError(err.message || 'Market candles are temporarily unavailable.');
          setMarketFeedStatus('feed unavailable');
        }
      }
    };
    void loadCandles();

    if (isKrakenSpot) {
      const connectKraken = () => {
        if (!active) return;
        setMarketFeedStatus('connecting to Kraken stream');
        socket = new WebSocket('wss://ws.kraken.com/v2');
        socket.onopen = () => {
          if (!active || !socket || socket.readyState !== WebSocket.OPEN) return;
          socket.send(JSON.stringify({
            method: 'subscribe',
            params: { channel: 'ohlc', symbol: [pair], interval: candleInterval, snapshot: true },
          }));
        };
        socket.onmessage = (event) => {
          if (!active) return;
          try {
            const message = JSON.parse(String(event.data));
            if (message.method === 'subscribe') {
              if (message.success === false) {
                setMarketFeedStatus('Kraken subscription rejected');
                setMarketError(message.error || 'Kraken rejected the candle subscription.');
              } else if (message.result?.channel === 'ohlc') {
                setMarketFeedStatus('connected · waiting for trades');
                setMarketError('');
              }
              return;
            }
            if (message.channel !== 'ohlc' || !Array.isArray(message.data)) return;
            const updates: Candle[] = message.data
              .filter((item: any) => item.symbol === pair)
              .map((item: any): Candle => ({
                timestamp: Math.floor(Date.parse(item.interval_begin) / 1000),
                open: Number(item.open),
                high: Number(item.high),
                low: Number(item.low),
                close: Number(item.close),
              }))
              .filter((item: Candle) => Number.isFinite(item.timestamp) && [item.open, item.high, item.low, item.close].every(value => Number.isFinite(value) && value > 0));
            if (!updates.length) return;
            setCandles(previous => {
              const byTime = new Map(previous.map(candle => [candle.timestamp, candle]));
              updates.forEach(candle => byTime.set(candle.timestamp, candle));
              return Array.from(byTime.values()).sort((a, b) => a.timestamp - b.timestamp).slice(-60);
            });
            const latest = updates[updates.length - 1];
            setMarketPrice(latest.close);
            setMarketSource('Kraken Spot WebSocket v2');
            setMarketFeedStatus('streaming · Kraken');
            setMarketError('');
          } catch {
            setMarketFeedStatus('stream message error');
          }
        };
        socket.onerror = () => {
          if (active) setMarketFeedStatus('Kraken stream error');
        };
        socket.onclose = () => {
          if (!active) return;
          setMarketFeedStatus('Kraken disconnected · reconnecting');
          reconnectTimer = window.setTimeout(connectKraken, 3000);
        };
      };
      connectKraken();
    } else {
      poll = window.setInterval(() => { void loadCandles(); }, 15000);
    }

    return () => {
      active = false;
      if (poll !== undefined) window.clearInterval(poll);
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      if (socket && socket.readyState <= WebSocket.OPEN) socket.close();
    };
  }, [pair, candleInterval]);

  useEffect(() => {
    const tick = () => setUtcNow(`${new Date().toISOString().slice(11, 19)} UTC`);
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);


  const toggleAutopilot = async () => {
    if (!token.trim()) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const action = autopilot?.enabled ? 'autopilot/stop' : 'autopilot/start';
      await request(action, { method: 'POST' });
      const latest = await request('autopilot');
      setAutopilot(latest);
      setMessage(latest.enabled
        ? 'Autonomous paper trading started. It is scanning the configured markets and managing virtual positions.'
        : 'New autonomous entries stopped. Protective exits remain monitored for open paper positions.');
      await refresh(true);
    } catch (err: any) {
      setError(err.message || 'Unable to change autonomous trading state.');
    } finally {
      setBusy(false);
    }
  };

  const runCycleNow = async () => {
    if (!token.trim()) return;
    setBusy(true);
    setError('');
    setMessage('Running immediate deterministic paper-trading scan across configured markets...');
    try {
      const result = await request('autopilot/run', { method: 'POST' });
      const fillsCount = (result.results || []).filter((r: any) => r.decision === 'BUY' || r.decision === 'SELL' || r.decision === 'EXECUTED').length;
      setMessage(
        fillsCount > 0
          ? `Bot cycle complete: ${fillsCount} simulated trade(s) executed across ${result.pairs_checked || 0} pairs.`
          : `Bot cycle complete: ${result.pairs_checked || 0} pairs evaluated.`
      );
      await refresh(true);
    } catch (err: any) {
      setError(err.message || 'Immediate autopilot scan cycle failed.');
    } finally {
      setBusy(false);
    }
  };

  const resetTo100AndTrade = async () => {
    if (!token.trim()) return;
    setBusy(true);
    setError('');
    setMessage('Resetting paper account to $100.00 USD and running autonomous trade cycle...');
    try {
      const result = await request('reset', {
        method: 'POST',
        body: JSON.stringify({ initial_balance_usd: '100.00', run_cycle: true }),
      });
      const fillsCount = (result.cycle?.results || []).filter((r: any) => r.decision === 'BUY' || r.decision === 'SELL').length;
      setMessage(`Account funded with $100.00 USD; ${fillsCount} simulated trade(s) placed across ${result.cycle?.pairs_checked || 0} configured markets.`);
      await refresh(true);
    } catch (err: any) {
      setError(err.message || 'Failed to reset paper account to $100.00 USD.');
    } finally {
      setBusy(false);
    }
  };

  const monitor = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await request('monitor', { method: 'POST' });
      const count = result.triggered_exits?.length || 0;
      setMessage(count ? `${count} protective exit(s) simulated.` : 'Protective checks complete. No thresholds crossed.');
      await refresh();
    } catch (err: any) {
      setError(err.message || 'Protective monitoring failed.');
    } finally {
      setBusy(false);
    }
  };

  const submitOrder = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await request('orders', {
        method: 'POST',
        body: JSON.stringify({
          pair,
          side,
          quantity,
          idempotency_key: `ui-${crypto.randomUUID()}`,
          stop_loss_price: side === 'BUY' && stopLoss ? stopLoss : null,
          take_profit_price: side === 'BUY' && takeProfit ? takeProfit : null,
        }),
      });
      setMessage(`${result.fill.side} ${result.fill.quantity} ${result.fill.pair} simulated at ${priceFmt(result.fill.fill_price)}. No exchange order was submitted.`);
      await refresh();
    } catch (err: any) {
      setError(err.message || 'Paper order was rejected.');
    } finally {
      setBusy(false);
    }
  };

  const pnlValue = Number(account?.total_pnl ?? account?.realized_pnl ?? 0);
  const unrealizedValue = Number(account?.unrealized_pnl ?? 0);
  const fills = orders;
  const buyCount = fills.filter((o: any) => o.side === 'BUY').length;
  const sellCount = fills.filter((o: any) => o.side === 'SELL').length;
  const totalFees = fills.reduce((sum: number, o: any) => sum + Number(o.fee_usd || 0), 0);
  const avgGross = fills.length ? fills.reduce((sum: number, o: any) => sum + Number(o.gross_usd || 0), 0) / fills.length : 0;
  const topFill: any = fills.reduce((best: any, o: any) => (Number(o?.gross_usd || 0) > Number(best?.gross_usd || 0) ? o : best), null);
  const tape = [...fills].reverse().slice(-24);
  const maxTapeGross = tape.reduce((m: number, o: any) => Math.max(m, Number(o.gross_usd || 0)), 0);
  const exposure = (account?.positions || []).map((p: Position) => ({ pair: p.pair, value: Number(p.market_value || 0) }));
  const stats = [
    { label: 'Portfolio equity', value: account ? money(account.equity) : '—', sub: account ? `${account.order_count} simulated fills` : 'Connect to load', main: true, tone: '' },
    { label: 'Virtual cash', value: account ? money(account.cash) : '—', sub: account?.currency || 'USD', main: false, tone: '' },
    { label: 'Open positions value', value: account ? money(account.market_value) : '—', sub: account ? `${account.positions.length} open · floating ${money(unrealizedValue)}` : '—', main: false, tone: '' },
    { label: 'Total P&L (Realized + Floating)', value: account ? money(pnlValue) : '—', sub: account ? `Realized ${money(account.realized_pnl)} · Floating ${money(unrealizedValue)}` : 'Closed & open virtual trades', main: false, tone: !account ? '' : pnlValue >= 0 ? 'pb-pos' : 'pb-neg' },
  ];

  return (
    <div className="animate-fade-in paper-board">
      <div className="pb-topbar">
        <div>
          <div className="pb-title"><Activity size={22} /> Paper Trading</div>
          <div className="pb-sub">DETERMINISTIC SIGNALS · KRAKEN CRYPTO · VIRTUAL USD · NO LIVE ORDERS</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="pb-live"><i />SIMULATION</span>
          <span className="pb-chip">FILL #{(account?.order_count ?? 0) + 1}</span>
          <span className="pb-chip"><Clock size={12} style={{ verticalAlign: -1 }} /> {utcNow || '—'}</span>
        </div>
      </div>

      <div className="pb-panel" style={{ marginBottom: 12 }}>
        <label className="pb-label" htmlFor="paper-token">Paper access token</label>
        <div className="pb-tokenrow">
          <input id="paper-token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} placeholder="Enter operator-configured token" className="pb-input" style={{ flex: 1, minWidth: 220 }} />
          <button className="pb-btn" onClick={() => void refresh()} disabled={busy || !token.trim()}><RefreshCw size={16} /> Connect</button>
          <button className="pb-btn pb-btn-ghost" onClick={() => { setToken(''); setAccount(null); setOrders([]); setAutopilot(null); setAutopilotRuns([]); setDiagnostics(null); setMessage('Paper Trading disconnected on this tab.'); setError(''); }} disabled={!token.trim()}>Disconnect</button>
        </div>
        <div className="pb-muted" style={{ marginTop: 8 }}>Connected access is remembered for this tab and restored automatically after a page refresh. It is cleared when the tab session ends or you disconnect.</div>
      </div>

      {error && <div className="pb-alert pb-alert-error" role="alert">{error}</div>}
      {message && <div className="pb-alert pb-alert-ok" role="status">{message}</div>}

      {diagnostics && (
        <div className="pb-panel" style={{ marginTop: 12, marginBottom: 12 }}>
          <div className="pb-mini">Authoritative paper-store verification</div>
          <div className="pb-muted">
            Database: <strong>{diagnostics.database_name}</strong> · Account version: <strong>{diagnostics.account_version}</strong> ·
            Persisted fills: <strong>{diagnostics.fill_count}</strong> · Persisted open positions: <strong>{diagnostics.open_position_count}</strong> ·
            Autopilot: <strong>{diagnostics.autopilot_enabled ? 'ENABLED' : 'DISABLED'}</strong> ·
            Execution: <strong>{diagnostics.execution_enabled ? 'ENABLED' : 'LOCKED'}</strong> ·
            Broker orders submitted: <strong>{diagnostics.exchange_order_submitted ? 'YES' : 'NO'}</strong>
          </div>
          {diagnostics.fill_count !== orders.length || diagnostics.open_position_count !== (account?.positions.length || 0) || diagnostics.autopilot_enabled !== Boolean(autopilot?.enabled) ? (
            <div className="pb-alert pb-alert-error" style={{ marginTop: 8, marginBottom: 0 }}>Portfolio and persisted account state do not agree. Trading controls must be treated as unverified.</div>
          ) : null}
        </div>
      )}

      <div className="pb-hero">
        {stats.map(stat => (
          <div className={`pb-stat${stat.main ? ' pb-stat-main' : ''}`} key={stat.label}>
            <div className="k">{stat.label}</div>
            <div className={`v ${stat.tone}`}>{stat.value}</div>
            <div className="s">{stat.sub}</div>
          </div>
        ))}
      </div>

      <div className="pb-panel" style={{ marginTop: 12, marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
          <div>
            <div className="pb-section-title" style={{ margin: 0 }}>{pair} · Live candles</div>
            <div className="pb-muted">Market feed: {marketSource || 'connecting'} · {marketFeedStatus} · {CRYPTO_PAIRS.includes(pair) ? 'Kraken trade updates form the active candle' : 'This instrument currently uses periodic market snapshots, not a live stream'} · Simulated fills are marked on the chart</div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <select aria-label="Chart instrument" value={pair} onChange={e => setPair(e.target.value)} className="pb-select" style={{ width: 150, margin: 0 }}>
              {ALL_TRADING_PAIRS.map(symbol => <option key={symbol} value={symbol}>{symbol}</option>)}
            </select>
            {[1,5,15,30,60].map(value => <button key={value} type="button" className={candleInterval === value ? 'pb-btn' : 'pb-btn pb-btn-ghost'} onClick={() => setCandleInterval(value)}>{value}m</button>)}
          </div>
        </div>
        {marketError && <div className="pb-alert pb-alert-error" role="alert">{marketError}</div>}
        <CandleChart candles={candles} trades={orders.filter((o: any) => o.pair === pair)} position={account?.positions.find(p => p.pair === pair)} currentPrice={marketPrice} />
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 10 }} className="pb-muted">
          <span>🟢 Bullish candle</span><span>🔴 Bearish candle</span><span>🔵 BUY fill</span><span>🔴 SELL fill</span><span>Dashed lines = open-position stop / target</span>
        </div>
      </div>

      <div className="pb-taperow">
        <div className="pb-panel">
          <div className="pb-mini">Fill tape · last {tape.length} simulated fills</div>
          {!tape.length ? <span className="pb-muted">No fills yet. Simulated orders will appear here as bars.</span> : (
            <div className="pb-tape">
              <div className="pb-tape-stats">
                <div><span>Fills</span><strong>{fills.length}</strong></div>
                <div><span>Buys / sells</span><strong>{buyCount} / {sellCount}</strong></div>
                <div><span>Fees paid</span><strong>{money(totalFees)}</strong></div>
                <div><span>Avg fill</span><strong>{money(avgGross)}</strong></div>
              </div>
              <div>
                <div className="pb-bars">
                  {tape.map((o: any) => (
                    <div
                      key={o.idempotency_key}
                      className={`pb-bar${o.side === 'SELL' ? ' sell' : ''}`}
                      style={{ height: `${maxTapeGross > 0 ? Math.max(6, (Number(o.gross_usd || 0) / maxTapeGross) * 100) : 0}%` }}
                      title={`${o.side} ${o.quantity} ${o.pair} @ ${o.fill_price}`}
                    />
                  ))}
                </div>
                <div className="pb-muted">Oldest → newest · blue BUY · red SELL · height ∝ notional</div>
              </div>
            </div>
          )}
        </div>
        <div className="pb-panel">
          <div className="pb-mini">Top fill</div>
          {!topFill ? <span className="pb-muted">No fills yet.</span> : (
            <>
              <div className="pb-topfill-value">{money(topFill.gross_usd)}</div>
              <div className="pb-muted">{topFill.side} {topFill.quantity} {topFill.pair}</div>
              <div className="pb-muted">@ {priceFmt(topFill.fill_price)} · fee {money(topFill.fee_usd)}</div>
              <div className="pb-muted">{topFill.timestamp ? new Date(topFill.timestamp).toLocaleString() : ''}</div>
            </>
          )}
          <div className="pb-mini" style={{ marginTop: 16 }}>Exposure by pair</div>
          {!exposure.length ? <span className="pb-muted">No open positions.</span> : (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {exposure.map((e: { pair: string; value: number }) => (
                <span className="pb-chip" key={e.pair}>{e.pair} · {money(e.value)}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="pb-section-title">Latest analysis pulse</div>
      <div className="pb-panel">
        {!latestAnalysis ? <span className="pb-muted">No boardroom analysis recorded yet. Run a market scan.</span> : (
          <>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
              <strong style={{ fontSize: 16 }}>{latestAnalysis.pair}</strong>
              <span className={`pb-act pb-act-${latestAnalysis.action}`}>{latestAnalysis.action}</span>
              <span className="pb-muted">{latestAnalysis.confidence !== null ? `${Math.round(latestAnalysis.confidence * 100)}% confidence` : 'confidence —'}</span>
              <span className="pb-muted">{latestAnalysis.timestamp ? new Date(latestAnalysis.timestamp).toLocaleString() : ''}</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.65 }}>{latestAnalysis.reasoning}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
              {latestAnalysis.rsi_14 !== null && latestAnalysis.rsi_14 !== undefined && <span className="pb-chip">RSI14 {latestAnalysis.rsi_14.toFixed(1)}</span>}
              {latestAnalysis.trend && <span className="pb-chip">{latestAnalysis.trend}</span>}
            </div>
          </>
        )}
      </div>

      <div className="pb-split" style={{ marginTop: 12 }}>
        <form className="pb-panel" onSubmit={submitOrder}>
          <div className="pb-section-title" style={{ marginTop: 0 }}>Simulate Forex / Metals / Indices / Spot order</div>
          <label className="pb-label">Market Pair (Forex, Metals, Indices &amp; Crypto)</label>
          <select value={pair} onChange={e => setPair(e.target.value)} className="pb-select" style={{ marginBottom: 12 }}>
            <optgroup label="Forex Pairs">
              {FOREX_PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
            </optgroup>
            <optgroup label="Metals (Gold / Silver / Platinum / Copper)">
              {METAL_PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
            </optgroup>
            <optgroup label="Global Indices (S&P 500 / Nasdaq / Dow / DAX)">
              {INDEX_PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
            </optgroup>
            <optgroup label="Crypto Pairs">
              {CRYPTO_PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
            </optgroup>
            {!ALL_TRADING_PAIRS.includes(pair) && <option value={pair}>{pair}</option>}
          </select>
          <label className="pb-label">Side</label>
          <select value={side} onChange={e => setSide(e.target.value as 'BUY' | 'SELL')} className="pb-select" style={{ marginBottom: 12 }}>
            <option value="BUY">BUY</option><option value="SELL">SELL</option>
          </select>
          <label className="pb-label">Quantity</label>
          <input value={quantity} onChange={e => setQuantity(e.target.value)} required inputMode="decimal" className="pb-input" style={{ marginBottom: 12 }} />
          {side === 'BUY' && <>
            <label className="pb-label">Stop-loss price (optional — auto-set at -0.8% if blank)</label>
            <input value={stopLoss} onChange={e => setStopLoss(e.target.value)} inputMode="decimal" placeholder="Leave blank for automatic -0.8% protective stop" className="pb-input" style={{ marginBottom: 12 }} />
            <label className="pb-label">Take-profit price (optional — auto-set at +1.6% if blank)</label>
            <input value={takeProfit} onChange={e => setTakeProfit(e.target.value)} inputMode="decimal" placeholder="Leave blank for automatic +1.6% target" className="pb-input" style={{ marginBottom: 12 }} />
          </>}
          <button className={`pb-btn ${side === 'BUY' ? 'pb-btn-buy' : 'pb-btn-sell'}`} type="submit" disabled={busy || !token.trim()} style={{ width: '100%', marginTop: 4 }}>
            {side === 'BUY' ? <TrendingUp size={16} /> : <TrendingDown size={16} />} Simulate {side}
          </button>
        </form>

        <div className="pb-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div className="pb-section-title" style={{ margin: 0 }}>Open positions</div>
            <button className="pb-btn pb-btn-ghost" onClick={monitor} disabled={busy || !token.trim()}><Activity size={16} /> Check exits</button>
          </div>
          {!account?.positions?.length ? <span className="pb-muted">No open virtual positions.</span> : (
            <div className="pb-tablewrap">
              <table className="pb-table">
                <thead><tr><th>Asset</th><th>Qty</th><th>Avg entry</th><th>Mark</th><th>Floating P&amp;L</th><th>Stop / target</th></tr></thead>
                <tbody>{account.positions.map(position => {
                  const uPnl = Number(position.unrealized_pnl_usd || 0);
                  const uPct = Number(position.unrealized_pnl_pct || 0);
                  return (
                    <tr key={position.pair}>
                      <td><strong>{position.pair}</strong></td><td>{position.quantity}</td>
                      <td>{priceFmt(position.average_entry)}</td><td>{priceFmt(position.mark_price)}</td>
                      <td className={uPnl >= 0 ? 'pb-up' : 'pb-neg'} style={{ fontWeight: 700 }}>
                        {uPnl >= 0 ? '+' : ''}{money(uPnl)} ({uPct >= 0 ? '+' : ''}{uPct.toFixed(2)}%)
                      </td>
                      <td>{position.stop_loss ? priceFmt(position.stop_loss) : '—'} / {position.take_profit ? priceFmt(position.take_profit) : '—'}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
          )}
          <div className="pb-muted" style={{ marginTop: 12 }}>Protective checks run continuously in the background worker and when you press Check exits.</div>
        </div>
      </div>

      <div className="pb-section-title">Recent simulated fills</div>
      <div className="pb-panel pb-tablewrap">
        {!orders.length ? <span className="pb-muted">No paper fills recorded yet.</span> : (
          <table className="pb-table">
            <thead><tr><th>Time</th><th>Pair</th><th>Side</th><th>Qty</th><th>Fill price</th><th>Fee</th><th>Mode</th></tr></thead>
            <tbody>{orders.map((order: any) => (
              <tr key={order.idempotency_key}><td>{new Date(order.timestamp).toLocaleString()}</td><td>{order.pair}</td><td className={order.side === 'BUY' ? 'pb-up' : 'pb-neg'} style={{ fontWeight: 700 }}>{order.side}</td><td>{order.quantity}</td><td>{priceFmt(order.fill_price)}</td><td>{money(order.fee_usd)}</td><td><span className="pb-mode">PAPER</span></td></tr>
            ))}</tbody>
          </table>
        )}
      </div>

      <div className="pb-section-title"><Bot size={14} style={{ verticalAlign: -2, marginRight: 6 }} />Autonomous paper trader</div>
      <div className="pb-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span className={`pb-pill${autopilot?.enabled ? ' pb-pill-on' : ''}`}>
            {autopilot?.enabled ? 'Autopilot running' : 'Autopilot stopped'}
          </span>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="pb-btn pb-btn-ghost" onClick={resetTo100AndTrade} disabled={busy || !token.trim() || !autopilot?.paper_trading_enabled}>
              <RefreshCw size={16} /> Seed $100 USD &amp; Trade
            </button>
            <button className="pb-btn" onClick={runCycleNow} disabled={busy || !token.trim() || !autopilot?.paper_trading_enabled}>
              <Zap size={16} /> Run Bot Cycle Now
            </button>
            <button className={autopilot?.enabled ? 'pb-btn pb-btn-ghost' : 'pb-btn'} onClick={toggleAutopilot} disabled={busy || !token.trim() || !autopilot?.worker_configured || !autopilot?.worker_running || !autopilot?.paper_trading_enabled}>
              {autopilot?.enabled ? <><PauseCircle size={16} /> Stop new entries</> : <><PlayCircle size={16} /> Start autonomous trading</>}
            </button>
          </div>
        </div>
        <div className="pb-muted" style={{ marginTop: 10 }}>
          {autopilot ? `1m & 5m Deterministic Scalper Active · Markets: ${autopilot.pairs.join(', ')} · Scalp scan every ${autopilot.scan_interval_seconds}s · Exit & profit-harvest checks every ${autopilot.monitor_interval_seconds}s` : 'Connect the paper account to load autopilot controls.'}
        </div>
        {autopilot && !autopilot.worker_running && <div className="pb-alert pb-alert-error" style={{ marginTop: 10, marginBottom: 0 }}>Background worker is not running in this API process. Autopilot controls are unavailable.</div>}
        <div className="pb-muted" style={{ marginTop: 10 }}>
          Paper mode only. Stop prevents new entries; protective monitoring continues for existing virtual positions. No external AI provider is required; deterministic risk limits remain authoritative.
        </div>
      </div>

      <div className="pb-section-title">Autonomous analysis history</div>
      <div className="pb-panel">
        {!autopilotRuns.length ? <span className="pb-muted">No autonomous analysis cycles recorded yet.</span> : (
          <div>
            {autopilotRuns.slice(0, 5).map((run, index) => (
              <div key={`${run.timestamp}-${index}`} className="pb-run">
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <strong>{new Date(run.timestamp).toLocaleString()}</strong>
                  <span className="pb-muted" style={{ fontSize: 12 }}>{run.status}</span>
                </div>
                {run.results?.map((item, itemIndex) => (
                  <div key={`${item.pair}-${itemIndex}`} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                    <span>{item.pair} · {item.decision}</span>
                    <span className="pb-muted">{item.fill ? `${item.fill.side} ${item.fill.quantity} @ ${item.fill.fill_price}` : item.reason || 'No action'}</span>
                  </div>
                ))}
                {run.protective_exits?.map((item, itemIndex) => (
                  <div key={`exit-${item.pair}-${itemIndex}`} style={{ marginTop: 6 }}>
                    Protective exit: {item.pair} · {item.triggered_by || 'triggered'} · {item.fill_price || ''}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pb-foot">
        <span>MODE PAPER</span>
        <span>WORKER {autopilot ? (autopilot.worker_running ? 'ONLINE' : 'OFFLINE') : '—'}</span>
        <span>MARKETS {(autopilot?.pairs || []).join(', ') || '—'}</span>
        <span>{account ? `${account.order_count} FILLS` : 'NOT CONNECTED'}</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><ShieldCheck size={12} /> EXECUTION DISABLED</span>
      </div>
    </div>
  );
};

export default PaperTrading;
