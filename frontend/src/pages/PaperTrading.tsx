import React, { useCallback, useEffect, useState } from 'react';
import { Activity, RefreshCw, ShieldCheck, TrendingDown, TrendingUp } from 'lucide-react';
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

  const refresh = useCallback(async () => {
    if (!token.trim()) {
      setError('Enter the paper-trading access token configured by the operator.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const [summary, history] = await Promise.all([
        request('account'),
        request('orders'),
      ]);
      setAccount(summary);
      setOrders(Array.isArray(history) ? history : []);
      setMessage('Paper account refreshed from MongoDB.');
    } catch (err: any) {
      setError(err.message || 'Unable to load the paper account.');
    } finally {
      setBusy(false);
    }
  }, [request, token]);

  useEffect(() => {
    if (!token.trim()) return;
    refresh();
  }, [token, refresh]);

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

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <div>
          <h1>Paper Trading</h1>
          <p style={{ color: 'var(--text-muted)' }}>Real Kraken public prices · Virtual USD funds · No live orders</p>
        </div>
        <span className="badge badge-success"><ShieldCheck size={14} style={{ display: 'inline', marginRight: 5 }} /> Simulation only</span>
      </div>

      <div className="glass card" style={{ marginBottom: '1.5rem' }}>
        <label htmlFor="paper-token" style={{ display: 'block', marginBottom: 8, color: 'var(--text-muted)' }}>Paper access token</label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input id="paper-token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} placeholder="Enter operator-configured token" style={{ flex: 1, minWidth: 220, padding: 12, borderRadius: 8, background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }} />
          <button className="btn btn-primary" onClick={refresh} disabled={busy || !token.trim()}><RefreshCw size={16} /> Connect</button>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>The token stays in this page's memory and is not saved to browser storage.</p>
      </div>

      {error && <div className="glass card" role="alert" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>{error}</div>}
      {message && <div className="glass card" role="status" style={{ borderColor: 'var(--success)' }}>{message}</div>}

      <div className="grid">
        {[
          ['Portfolio equity', account ? money(account.equity) : '—'],
          ['Virtual cash', account ? money(account.cash) : '—'],
          ['Open positions value', account ? money(account.market_value) : '—'],
          ['Realized P&L', account ? money(account.realized_pnl) : '—'],
        ].map(([label, value]) => (
          <div className="glass card" key={label}>
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 800, marginTop: 8 }}>{value}</div>
          </div>
        ))}
      </div>

      <div className="grid" style={{ marginTop: 8, alignItems: 'start' }}>
        <form className="glass card" onSubmit={submitOrder}>
          <h2 style={{ marginBottom: 16 }}>Simulate spot order</h2>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: 6 }}>Pair</label>
          <input value={pair} onChange={e => setPair(e.target.value.toUpperCase())} required pattern="[A-Z0-9]+/USD" title="Use a USD-quoted pair such as BTC/USD" style={fieldStyle} />
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: 6 }}>Side</label>
          <select value={side} onChange={e => setSide(e.target.value as 'BUY' | 'SELL')} style={fieldStyle}>
            <option value="BUY">BUY</option><option value="SELL">SELL</option>
          </select>
          <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: 6 }}>Quantity</label>
          <input value={quantity} onChange={e => setQuantity(e.target.value)} required inputMode="decimal" style={fieldStyle} />
          {side === 'BUY' && <>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: 6 }}>Stop-loss price (required by risk policy)</label>
            <input value={stopLoss} onChange={e => setStopLoss(e.target.value)} inputMode="decimal" placeholder="e.g. 64000" style={fieldStyle} />
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: 6 }}>Take-profit price (optional)</label>
            <input value={takeProfit} onChange={e => setTakeProfit(e.target.value)} inputMode="decimal" placeholder="e.g. 70000" style={fieldStyle} />
          </>}
          <button className="btn btn-primary" type="submit" disabled={busy || !token.trim()} style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}>
            {side === 'BUY' ? <TrendingUp size={16} /> : <TrendingDown size={16} />} Simulate {side}
          </button>
        </form>

        <div className="glass card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <h2>Open positions</h2>
            <button className="btn" onClick={monitor} disabled={busy || !token.trim()}><Activity size={16} /> Check exits</button>
          </div>
          {!account?.positions?.length ? <p style={{ color: 'var(--text-muted)' }}>No open virtual positions.</p> : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead><tr><th style={cellStyle}>Asset</th><th style={cellStyle}>Qty</th><th style={cellStyle}>Avg entry</th><th style={cellStyle}>Mark</th><th style={cellStyle}>Stop / target</th></tr></thead>
                <tbody>{account.positions.map(position => (
                  <tr key={position.pair}>
                    <td style={cellStyle}>{position.pair}</td><td style={cellStyle}>{position.quantity}</td>
                    <td style={cellStyle}>{money(position.average_entry)}</td><td style={cellStyle}>{money(position.mark_price)}</td>
                    <td style={cellStyle}>{position.stop_loss ? money(position.stop_loss) : '—'} / {position.take_profit ? money(position.take_profit) : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 12 }}>Protective checks run when you press Check exits. This is not a continuously running background service.</p>
        </div>
      </div>

      <div className="glass card" style={{ marginTop: 16 }}>
        <h2 style={{ marginBottom: 12 }}>Recent simulated fills</h2>
        {!orders.length ? <p style={{ color: 'var(--text-muted)' }}>No paper fills recorded yet.</p> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead><tr><th style={cellStyle}>Time</th><th style={cellStyle}>Pair</th><th style={cellStyle}>Side</th><th style={cellStyle}>Qty</th><th style={cellStyle}>Fill price</th><th style={cellStyle}>Fee</th><th style={cellStyle}>Mode</th></tr></thead>
              <tbody>{orders.map((order: any) => (
                <tr key={order.idempotency_key}><td style={cellStyle}>{new Date(order.timestamp).toLocaleString()}</td><td style={cellStyle}>{order.pair}</td><td style={cellStyle}>{order.side}</td><td style={cellStyle}>{order.quantity}</td><td style={cellStyle}>{money(order.fill_price)}</td><td style={cellStyle}>{money(order.fee_usd)}</td><td style={cellStyle}>PAPER</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 12 }}>Live execution is disabled. Every fill is simulated; no Kraken private trading endpoint is called.</p>
    </div>
  );
};

const fieldStyle: React.CSSProperties = {
  width: '100%', padding: 11, marginBottom: 14, borderRadius: 8,
  background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)',
};
const cellStyle: React.CSSProperties = { padding: '10px 8px', borderBottom: '1px solid var(--border)', fontSize: 13 };

export default PaperTrading;
