import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  History, 
  Activity,
  AlertCircle,
  TrendingUp,
  RefreshCcw,
  Users
} from 'lucide-react';

import AuditLog from './pages/AuditLog';
import TradingView from './components/TradingView';
import ChatBot from './components/ChatBot';
import { API_BASE_URL } from './config';
import PaperTrading from './pages/PaperTrading';

const Boardroom = () => {
  const [deliberations, setDeliberations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBoardroom();
  }, []);

  const fetchBoardroom = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/boardroom`);
      if (!res.ok) throw new Error("Boardroom history is unavailable.");
      const data = await res.json();
      setDeliberations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <h2 style={{ marginBottom: '1.5rem' }}>The Boardroom <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Live Deliberation)</span></h2>
      
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: '2rem' }}>
        {[
          { name: 'Market Intelligence', status: 'Meta AI · verified market context', color: 'var(--primary)' },
          { name: 'Technical Analyst', status: 'EMA · RSI · ATR calculations', color: 'var(--success)' },
          { name: 'Strategy', status: 'Meta AI · BUY / SELL / HOLD proposal', color: 'var(--primary)' },
          { name: 'Risk Manager', status: 'Meta AI advisory · deterministic limits', color: 'var(--danger)' },
          { name: 'Execution', status: 'Risk preflight · order submission locked', color: 'var(--vantage-gold)' },
          { name: 'Performance', status: 'Confirmed closed trades only', color: 'var(--success)' }
        ].map((agent) => (
          <div key={agent.name} className="glass card" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: agent.color, flexShrink: 0 }}></span>
              <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{agent.name}</div>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{agent.status}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {deliberations.length === 0 && !loading && (
          <div className="glass card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No six-agent analysis cycles have been recorded yet. Run a market scan to start the boardroom.
          </div>
        )}
        {deliberations.map((d: any, idx) => {
          const strategy = d.strategy || {};
          const technical = d.technical_analysis || {};
          const risk = d.risk_assessment || {};
          const execution = d.execution_assessment || {};
          const performance = d.performance_context || {};
          const action = strategy.action || d.action || 'HOLD';
          const reasoning = strategy.rationale || d.reasoning || 'No reasoning provided.';
          const actionColor = action === 'BUY' ? 'var(--success)' : action === 'SELL' ? 'var(--danger)' : 'var(--vantage-gold)';
          return (
            <div key={idx} className="glass card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '1rem' }}>{d.pair || d.symbol || 'N/A'}</span>
                  <span style={{
                    background: actionColor,
                    color: '#fff',
                    fontWeight: 800,
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.75rem',
                    borderRadius: '999px',
                    letterSpacing: '0.05em'
                  }}>{action}</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(d.timestamp).toLocaleString()}</div>
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text)', lineHeight: 1.7, marginBottom: '1rem' }}>
                {reasoning}
              </div>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', fontSize: '0.8rem' }}>
                <div><span style={{ color: 'var(--text-muted)' }}>Technical trend</span><br /><strong>{technical.trend || 'Unavailable'}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>RSI 14</span><br /><strong>{typeof technical.rsi_14 === 'number' ? technical.rsi_14.toFixed(1) : '—'}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Risk assessment</span><br /><strong>{risk.summary || 'Not available'}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Execution gate</span><br /><strong>{execution.status || 'Not evaluated'}</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Performance sample</span><br /><strong>{performance.sample_size ?? 0} confirmed trades</strong></div>
                <div><span style={{ color: 'var(--text-muted)' }}>Execution</span><br /><strong style={{ color: 'var(--warning)' }}>Disabled · research only</strong></div>
              </div>
              <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Strategy confidence: {typeof strategy.confidence === 'number' ? `${(strategy.confidence * 100).toFixed(0)}%` : '—'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
const Dashboard = ({ onSelectBoardroom, status, onRefresh }: any) => {
  const history = Array.isArray(status?.history) ? status.history : [];
  const balance = status?.balance?.USD;
  const exchangeConnected = status?.exchange_status === "connected";
  const completedOrders = history.filter((item: any) => ["buy", "sell"].includes(String(item.side).toLowerCase()));

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Ras Ali AI Trader</h1>
          <p style={{ color: 'var(--text-muted)' }}>Kraken spot market intelligence · Paper-first research · Controlled execution</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="glass btn" onClick={onRefresh} style={{ border: '1px solid var(--primary)' }}>
            <RefreshCcw size={18} style={{ marginRight: '0.5rem' }} /> Refresh
          </button>
        </div>
      </div>

      <div className="grid">
        <div className="glass card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <AlertCircle color="var(--warning)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Execution Mode</h3>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>LOCKED</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Analysis only. No orders can be submitted.</div>
          <div style={{ color: 'var(--warning)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
            Risk policy: {status?.risk_policy_status === 'configured' ? 'configured' : 'not configured'}
          </div>
        </div>

        <div className="glass card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <Activity color="var(--primary)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Kraken Connection</h3>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>{exchangeConnected ? 'CONNECTED' : 'NOT VERIFIED'}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Market data and account access are reported separately.</div>
        </div>

        <div className="glass card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <TrendingUp color="var(--success)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Account Balance</h3>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>{typeof balance === 'number' ? `$${balance.toLocaleString()}` : 'Unavailable'}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No estimated or simulated balances are displayed.</div>
        </div>

        <div className="glass card" style={{ cursor: 'pointer', border: '1px solid rgba(36, 86, 230, 0.35)' }} onClick={onSelectBoardroom}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <Users color="var(--primary)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Boardroom Intelligence</h3>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>{history.length}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Recorded ledger events · Open analysis history</div>
        </div>
      </div>

      <div className="glass card" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', gap: '1rem' }}>
          <h2>Trade & Decision Ledger</h2>
          <span className="badge">Read only</span>
        </div>
        {history.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', padding: '1.5rem 0' }}>
            No persisted trading events yet. The ledger will populate when MongoDB is available and verified events are recorded.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr>
                  <th style={{ padding: '1rem' }}>Asset</th>
                  <th style={{ padding: '1rem' }}>Side</th>
                  <th style={{ padding: '1rem' }}>Volume</th>
                  <th style={{ padding: '1rem' }}>Price</th>
                  <th style={{ padding: '1rem' }}>Status</th>
                  <th style={{ padding: '1rem' }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 10).map((item: any) => (
                  <tr key={item.id || item.order_id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '1rem' }}>{item.symbol || item.pair || '—'}</td>
                    <td style={{ padding: '1rem' }}>{String(item.side || item.action || '—').toUpperCase()}</td>
                    <td style={{ padding: '1rem' }}>{item.volume ?? '—'}</td>
                    <td style={{ padding: '1rem' }}>{item.price ?? '—'}</td>
                    <td style={{ padding: '1rem' }}>{item.status || item.execution_status || 'recorded'}</td>
                    <td style={{ padding: '1rem' }}>{item.time || item.timestamp || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          {completedOrders.length} historical order records · P&amp;L is not shown until it can be calculated from confirmed fills.
        </div>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [status, setStatus] = useState<any>(null);
  const [triggerScanOnLoad, setTriggerScanOnLoad] = useState(false);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => {
      clearInterval(interval);
    };
  }, []);

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

  return (
    <div className="app-container">
      <ChatBot />
      <aside className="sidebar">
        <div style={{ padding: '2rem', fontSize: '1.5rem', fontWeight: 900, letterSpacing: '-1px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '32px', height: '32px', background: 'var(--primary)', borderRadius: '8px' }}></div> Ras Ali Labs
        </div>
        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); }}
          >
            <LayoutDashboard size={20} /> Dashboard
          </div>
          <div 
            className={`nav-item ${activeTab === 'paper' ? 'active' : ''}`}
            onClick={() => setActiveTab('paper')}
          >
            <Activity size={20} /> Paper Trading
          </div>
          <div 
            className={`nav-item ${activeTab === 'trading' ? 'active' : ''}`}
            onClick={() => setActiveTab('trading')}
          >
            <TrendingUp size={20} /> AI Trader
          </div>
          <div 
            className={`nav-item ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <History size={20} /> Audit Trail
          </div>
          <div 
            className={`nav-item ${activeTab === 'boardroom' ? 'active' : ''}`}
            onClick={() => setActiveTab('boardroom')}
          >
            <Users size={20} /> Boardroom
          </div>
        </nav>
      </aside>

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <Dashboard 
            onSelectBoardroom={() => setActiveTab('boardroom')}
            status={status}
            onRefresh={fetchStatus}
          />
        )}
        {activeTab === 'paper' && <PaperTrading />}
        {activeTab === 'trading' && (
          <TradingView 
            autoStartScan={triggerScanOnLoad} 
            onScanStarted={() => setTriggerScanOnLoad(false)} 
          />
        )}
        {activeTab === 'audit' && <AuditLog />}
        {activeTab === 'boardroom' && <Boardroom />}
      </main>
    </div>
  );
};

export default App;
