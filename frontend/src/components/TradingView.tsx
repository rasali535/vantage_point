import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, ShoppingCart, RefreshCcw } from 'lucide-react';
import { API_BASE_URL } from '../config';

const TradingView = () => {
  const [status, setStatus] = useState<any>(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error(err);
    }
  };

  const runScanner = async () => {
    setScanning(true);
    try {
      await fetch(`${API_BASE_URL}/api/trading/scan`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error(err);
    }
    setScanning(false);
  };

  if (!status) return <div className="glass card">Loading Kraken Terminal...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
        <div className="glass card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Portfolio Balance (xStocks)</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <DollarSign size={20} color="var(--success)" /> {status.balance.USD?.toLocaleString()}
          </div>
        </div>
        <div className="glass card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>24h Profit/Loss</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={20} /> {status.pnl_24h}
          </div>
        </div>
        <div className="glass card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Active Strategy</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={20} color="var(--primary)" /> {status.active_strategy}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        {/* Recent Trades */}
        <div className="glass card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShoppingCart size={20} color="var(--warning)" /> Execution Log (Kraken CLI)
            </h3>
            <button 
              className={`btn btn-primary ${scanning ? 'loading' : ''}`} 
              onClick={runScanner}
              disabled={scanning}
            >
              <RefreshCcw size={16} /> {scanning ? 'Scanning Market...' : 'Run Autonomous Scan'}
            </button>
          </div>
          
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Asset</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Side</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Volume</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Price</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Status</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {status.history.map((trade: any) => (
                  <tr key={trade.id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                    <td style={{ padding: '1rem', fontWeight: 600 }}>{trade.symbol}</td>
                    <td style={{ padding: '1rem' }}>
                      <span className={`badge ${trade.side === 'buy' ? 'badge-success' : 'badge-danger'}`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '1rem' }}>{trade.volume}</td>
                    <td style={{ padding: '1rem' }}>${trade.price}</td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--success)' }}>● {trade.status}</span>
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>{trade.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Portfolio Allocation */}
        <div className="glass card">
          <h3 style={{ marginBottom: '1.5rem' }}>Portfolio Holdings</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.entries(status.balance).map(([asset, amount]: [string, any]) => (
              asset !== 'USD' && (
                <div key={asset} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'var(--surface-light)', borderRadius: '8px' }}>
                  <div style={{ fontWeight: 600 }}>{asset}</div>
                  <div style={{ color: 'var(--text-muted)' }}>{amount} units</div>
                </div>
              )
            ))}
          </div>
          <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(255, 193, 7, 0.1)', borderRadius: '8px', border: '1px solid var(--warning)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--warning)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>AI Strategy Note</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Currently overweight in <strong>AAPLx</strong>. Seeking momentum signals in <strong>NVDAx</strong> for potential rebalancing.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingView;
