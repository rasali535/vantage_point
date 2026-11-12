import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Bot, PauseCircle, PlayCircle, RefreshCw, ShieldCheck, TrendingDown, TrendingUp } from 'lucide-react';
import { API_BASE_URL } from '../config';

type Position = {
  pair: string;
  quantity: string;
  average_entry: string;
  mark_price: string;
  market_value: string;
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
  order_count: number;
  positions: Position[];
  execution_enabled: boolean;
  exchange_order_submitted: boolean;
};

const money = (value: string | number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value || 0));

const PaperTrading: React.FC = () => {
  const [token, setToken] = useState('');
  const [account, setAccount] = useState<Account | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [autopilot, setAutopilot] = useState<AutopilotStatus | null>(null);
  const [autopilotRuns, setAutopilotRuns] = useState<AutopilotRun[]>([]);
  const [pair, setPair] = useState('BTC/USD');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('0.001');
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
        ? 'Autonomous paper trading started. It will analyse markets and manage virtual positions automatically.'
        : 'New autonomous entries stopped. Protective exits remain monitored for open paper positions.');
    } catch (err: any) {
      setError(err.message || 'Unable to change autonomous trading state.');
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
      setMessage(`${result.fill.side} simulated at ${money(result.fill.fill_price)}. No exchange order was submitted.`);
      await refresh();
    } catch (err: any) {
      setError(err.message || 'Paper order was rejected.');
    } finally {
      setBusy(false);
    }
  };

  const pnlValue = Number(account?.realized_pnl || 0);
  const stats = [
    { label: 'Portfolio equity', value: account ? money(account.equity) : '—', sub: account ? `${account.order_count} simulated fills` : 'Connect to load', main: true, tone: '' },
    { label: 'Virtual cash', value: account ? money(account.cash) : '—', sub: account?.currency || 'USD', main: false, tone: '' },
    { label: 'Open positions value', value: account ? money(account.market_value) : '—', sub: account ? `${account.positions.length} open` : '—', main: false, tone: '' },
    { label: 'Realized P&L', value: account ? money(account.realized_pnl) : '—', sub: 'Closed virtual trades', main: false, tone: !account ? '' : pnlValue >= 0 ? 'pb-pos' : 'pb-neg' },
  ];

  return (
    <div className="animate-fade-in paper-board">
      <div className="pb-topbar">
        <div>
          <div className="pb-title"><Activity size={22} /> Paper Trading</div>
          <div className="pb-sub">Real Kraken public prices · Virtual USD funds · No live orders</div>
        </div>
        <span className="pb-live"><i />SIMULATION</span>
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

      <div className="pb-section-title"><Bot size={14} style={{ verticalAlign: -2, marginRight: 6 }} />Autonomous paper trader</div>
      <div className="pb-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span className={`pb-pill${autopilot?.enabled ? ' pb-pill-on' : ''}`}>
            {autopilot?.enabled ? 'Autopilot running' : 'Autopilot stopped'}
          </span>
          <button className={autopilot?.enabled ? 'pb-btn pb-btn-ghost' : 'pb-btn'} onClick={toggleAutopilot} disabled={busy || !token.trim() || !autopilot?.worker_configured || !autopilot?.worker_running || !autopilot?.paper_trading_enabled}>
            {autopilot?.enabled ? <><PauseCircle size={16} /> Stop new entries</> : <><PlayCircle size={16} /> Start autonomous trading</>}
          </button>
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

      <div className="pb-split" style={{ marginTop: 12 }}>
        <form className="pb-panel" onSubmit={submitOrder}>
          <div className="pb-section-title" style={{ marginTop: 0 }}>Simulate spot order</div>
          <label className="pb-label">Pair</label>
          <input value={pair} onChange={e => setPair(e.target.value.toUpperCase())} required pattern="[A-Z0-9]+/USD" title="Use a USD-quoted pair such as BTC/USD" className="pb-input" style={{ marginBottom: 12 }} />
          <label className="pb-label">Side</label>
          <select value={side} onChange={e => setSide(e.target.value as 'BUY' | 'SELL')} className="pb-select" style={{ marginBottom: 12 }}>
            <option value="BUY">BUY</option><option value="SELL">SELL</option>
          </select>
          <label className="pb-label">Quantity</label>
          <input value={quantity} onChange={e => setQuantity(e.target.value)} required inputMode="decimal" className="pb-input" style={{ marginBottom: 12 }} />
          {side === 'BUY' && <>
            <label className="pb-label">Stop-loss price (required by risk policy)</label>
            <input value={stopLoss} onChange={e => setStopLoss(e.target.value)} inputMode="decimal" placeholder="e.g. 64000" className="pb-input" style={{ marginBottom: 12 }} />
            <label className="pb-label">Take-profit price (optional)</label>
            <input value={takeProfit} onChange={e => setTakeProfit(e.target.value)} inputMode="decimal" placeholder="e.g. 70000" className="pb-input" style={{ marginBottom: 12 }} />
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
                <thead><tr><th>Asset</th><th>Qty</th><th>Avg entry</th><th>Mark</th><th>Stop / target</th></tr></thead>
                <tbody>{account.positions.map(position => (
                  <tr key={position.pair}>
                    <td>{position.pair}</td><td>{position.quantity}</td>
                    <td>{money(position.average_entry)}</td><td>{money(position.mark_price)}</td>
                    <td>{position.stop_loss ? money(position.stop_loss) : '—'} / {position.take_profit ? money(position.take_profit) : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <div className="pb-muted" style={{ marginTop: 12 }}>Protective checks run when you press Check exits. This is not a continuously running background service.</div>
        </div>
      </div>

      <div className="pb-section-title">Recent simulated fills</div>
      <div className="pb-panel pb-tablewrap">
        {!orders.length ? <span className="pb-muted">No paper fills recorded yet.</span> : (
          <table className="pb-table">
            <thead><tr><th>Time</th><th>Pair</th><th>Side</th><th>Qty</th><th>Fill price</th><th>Fee</th><th>Mode</th></tr></thead>
            <tbody>{orders.map((order: any) => (
              <tr key={order.idempotency_key}><td>{new Date(order.timestamp).toLocaleString()}</td><td>{order.pair}</td><td className={order.side === 'BUY' ? 'pb-up' : 'pb-neg'} style={{ fontWeight: 700 }}>{order.side}</td><td>{order.quantity}</td><td>{money(order.fill_price)}</td><td>{money(order.fee_usd)}</td><td><span className="pb-mode">PAPER</span></td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
      <div className="pb-muted" style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <ShieldCheck size={14} /> Live execution is disabled. Every fill is simulated; no Kraken private trading endpoint is called.
      </div>
    </div>
  );
};

export default PaperTrading;
