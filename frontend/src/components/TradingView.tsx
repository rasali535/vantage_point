import { useState, useEffect } from 'react';
import { TrendingUp, DollarSign, Activity, ShoppingCart, RefreshCcw } from 'lucide-react';
import { API_BASE_URL } from '../config';
import BoardroomCouncil from './BoardroomCouncil';

interface TradingViewProps {
  autoStartScan?: boolean;
  onScanStarted?: () => void;
}

const TradingView = ({ autoStartScan, onScanStarted }: TradingViewProps) => {
  const [status, setStatus] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [lastDecision, setLastDecision] = useState<any>(null);
  const [pair, setPair] = useState('EUR/USD');
  const majorPairs = [
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF',
    'EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/AUD', 'EUR/CAD', 'AUD/JPY',
    'XAU/USD', 'XAG/USD', 'XPT/USD', 'XCU/USD',
    'SPX500/USD', 'NAS100/USD', 'US30/USD', 'UK100/USD', 'GER40/USD', 'JPN225/USD',
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD', 'DOGE/USD', 'LTC/USD', 'LINK/USD', 'DOT/USD', 'BCH/USD'
  ];

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoStartScan && !scanning) {
      runScanner();
      if (onScanStarted) {
        onScanStarted();
      }
    }
  }, [autoStartScan]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/status`);
      const data = await res.json();
      if (!res.ok) {
        setStatus({ balance: null, history: [], pnl_24h: null, active_strategy: 'Unavailable', exchange_status: 'unavailable', error: data.detail || 'Service unavailable' });
        return;
      }
      setStatus({ ...data, history: Array.isArray(data.history) ? data.history : [] });
    } catch (err) {
      console.error(err);
    }
  };

  const runScanner = async () => {
    setScanning(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pair }),
      });
      if (!res.ok) {
        let message = `Server Error (${res.status})`;
        let requestId = '';
        try {
          const payload = await res.json();
          const detail = payload?.detail;
          if (typeof detail === 'string') message = detail;
          else if (detail && typeof detail === 'object') {
            message = detail.message || message;
            requestId = detail.request_id || '';
          }
        } catch {
          // Keep the status-based message when the server response is not JSON.
        }
        throw new Error(requestId ? `${message} (Reference: ${requestId})` : message);
      }
      const data = await res.json();
      setLastDecision({ ...data.decision, pair: data.pair, signal_quality: data.signal_quality_report?.signal_quality_index, whipsaw_risk: data.signal_quality_report?.whipsaw_risk });
      await fetchStatus();
    } catch (err: any) {
      console.error('Scan Error:', err);
      alert(`Market analysis failed. No order was submitted.\n\nDetails: ${err.message}`);
    }
    setScanning(false);
  };

  if (!status) return <div className="glass card">Loading Kraken Terminal...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
        <div className="glass card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>Kraken Account Balance</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <DollarSign size={20} color="var(--success)" /> {status.balance?.USD != null ? status.balance.USD.toLocaleString() : 'Unavailable'}
          </div>
        </div>
        <div className="glass card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>24h Profit/Loss</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={20} /> {status.pnl_24h ?? 'Not calculated'}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <BoardroomCouncil decision={lastDecision} scanning={scanning} />
          
          {/* Recent Trades */}
          <div className="glass card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShoppingCart size={20} color="var(--warning)" /> Trade Ledger (read-only)
              </h3>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  list="scan-pairs"
                  value={pair}
                  onChange={e => setPair(e.target.value.toUpperCase())}
                  disabled={scanning}
                  pattern="[A-Z0-9]+/[A-Z0-9]+"
                  title="Kraken pair, e.g. ETH/USD"
                  aria-label="Market pair to scan"
                  style={{ background: 'var(--surface-light)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text)', padding: '0.6rem 0.75rem', width: '140px', fontWeight: 600, marginRight: '0.75rem' }}
                />
                <datalist id="scan-pairs">
                  {majorPairs.map(option => <option key={option} value={option} />)}
                </datalist>
              <button 
                className={`btn btn-primary ${scanning ? 'loading' : ''}`} 
                onClick={runScanner}
                disabled={scanning}
              >
                <RefreshCcw size={16} /> {scanning ? 'Scanning Market...' : 'Run Market Analysis'}
              </button>
              </div>
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
                  {(status.history || []).map((trade: any) => (
                    <tr key={trade.id || trade.order_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem', fontWeight: 600 }}>{trade.symbol}</td>
                      <td style={{ padding: '1rem' }}>
                        <span className={`badge ${trade.side === 'buy' ? 'badge-success' : 'badge-danger'} ${trade.side === 'expense' ? 'badge-warning' : ''}`}>
                          {trade.side.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '1rem' }}>{trade.volume}</td>
                      <td style={{ padding: '1rem' }}>${trade.price}</td>
                      <td style={{ padding: '1rem' }}>
                        <span style={{ fontSize: '0.8rem', color: trade.status === 'processed' ? 'var(--primary)' : 'var(--success)' }}>● {trade.status}</span>
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>{trade.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Portfolio Allocation */}
        <div className="glass card">
          <h3 style={{ marginBottom: '1.5rem' }}>Portfolio Holdings</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {status.balance?.holdings && Object.entries(status.balance.holdings).map(([asset, amount]: [string, any]) => (
              <div key={asset} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'var(--surface-light)', borderRadius: '8px' }}>
                <div style={{ fontWeight: 600 }}>{asset}</div>
                <div style={{ color: 'var(--text-muted)' }}>{amount} units</div>
              </div>
            ))}
            {(!status.balance?.holdings || Object.keys(status.balance.holdings).length === 0) && (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1rem' }}>
                Exchange holdings are unavailable until Kraken connectivity is verified.
              </div>
            )}
          </div>
          <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(255, 193, 7, 0.1)', borderRadius: '8px', border: '1px solid var(--warning)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--warning)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>AI Strategy Note</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Analysis-only mode. No orders can be submitted from this build.
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default TradingView;
