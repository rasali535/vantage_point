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

const PaperTrading: React.FC = () => {
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('paper_trading_token') || '';
    } catch {
      return '';
    }
  });
  const [account, setAccount] = useState<Account | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [autopilot, setAutopilot] = useState<AutopilotStatus | null>(null);
  const [autopilotRuns, setAutopilotRuns] = useState<AutopilotRun[]>([]);
  const [latestAnalysis, setLatestAnalysis] = useState<LatestAnalysis | null>(null);
  const [utcNow, setUtcNow] = useState('');
  const [pair, setPair] = useState('EUR/USD');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('10');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

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
      if (!silent) setError('Enter the paper-trading access token configured by the operator.');
      return;
    }
    if (!silent) setBusy(true);
    setError('');
    try {
      const [summary, history, autoStatus, autoRuns] = await Promise.all([
        request('account'),
        request('orders'),
        request('autopilot'),
        request('autopilot/runs'),
      ]);
      setAccount(summary);
      setOrders(Array.isArray(history) ? history : []);
      setAutopilot(autoStatus);
      setAutopilotRuns(Array.isArray(autoRuns) ? autoRuns : []);
      try {
        localStorage.setItem('paper_trading_token', token);
      } catch {
        // Private browsing: the token simply won't persist.
      }
      if (!silent) setMessage('Paper account and autonomous trading status refreshed from MongoDB.');
    } catch (err: any) {
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
        ? 'Autonomous paper trading started. It is now scanning Forex and Crypto pairs and managing virtual positions.'
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
    setMessage('Running immediate autonomous Forex & Crypto scan cycle...');
    try {
      const result = await request('autopilot/run', { method: 'POST' });
      const fillsCount = (result.results || []).filter((r: any) => r.decision === 'EXECUTED').length;
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
          <div className="pb-sub">MUSE SPARK · FOREX &amp; KRAKEN SPOT · VIRTUAL USD · NO LIVE ORDERS</div>
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
        </div>
        <div className="pb-muted" style={{ marginTop: 8 }}>The token stays in this page's memory and is not saved to browser storage.</div>
      </div>

      {error && <div className="pb-alert pb-alert-error" role="alert">{error}</div>}
      {message && <div className="pb-alert pb-alert-ok" role="status">{message}</div>}

      <div className="pb-hero">
        {stats.map(stat => (
          <div className={`pb-stat${stat.main ? ' pb-stat-main' : ''}`} key={stat.label}>
            <div className="k">{stat.label}</div>
            <div className={`v ${stat.tone}`}>{stat.value}</div>
            <div className="s">{stat.sub}</div>
          </div>
        ))}
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
            <button className="pb-btn" onClick={runCycleNow} disabled={busy || !token.trim() || !autopilot?.paper_trading_enabled}>
              <Zap size={16} /> Run Bot Cycle Now
            </button>
            <button className={autopilot?.enabled ? 'pb-btn pb-btn-ghost' : 'pb-btn'} onClick={toggleAutopilot} disabled={busy || !token.trim() || !autopilot?.worker_configured || !autopilot?.worker_running || !autopilot?.paper_trading_enabled}>
              {autopilot?.enabled ? <><PauseCircle size={16} /> Stop new entries</> : <><PlayCircle size={16} /> Start autonomous trading</>}
            </button>
          </div>
        </div>
        <div className="pb-muted" style={{ marginTop: 10 }}>
          {autopilot ? `Markets: ${autopilot.pairs.join(', ')} · Analysis every ${Math.round(autopilot.scan_interval_seconds / 60)} min · Exit checks every ${autopilot.monitor_interval_seconds}s` : 'Connect the paper account to load autopilot controls.'}
        </div>
        {autopilot && !autopilot.worker_running && <div className="pb-alert pb-alert-error" style={{ marginTop: 10, marginBottom: 0 }}>Background worker is not running in this API process. Autopilot controls are unavailable.</div>}
        <div className="pb-muted" style={{ marginTop: 10 }}>
          Paper mode only. Stop prevents new entries; protective monitoring continues for existing virtual positions. The AI cannot bypass the deterministic risk limits.
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
