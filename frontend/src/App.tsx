import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  History, 
  Plus, 
  MoreVertical,
  Activity,
  AlertCircle,
  TrendingUp,
  RefreshCcw,
  Users
} from 'lucide-react';

import UploadModal from './components/UploadModal';
import AuditLog from './pages/AuditLog';
import TradingView from './components/TradingView';
import ChatBot from './components/ChatBot';
import { API_BASE_URL } from './config';

const Boardroom = () => {
  const [deliberations, setDeliberations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBoardroom();
  }, []);

  const fetchBoardroom = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/boardroom`);
      const data = await res.json();
      setDeliberations(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <h2 style={{ marginBottom: '1.5rem' }}>The Boardroom <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Live Deliberation)</span></h2>
      
      <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '2rem' }}>
        {[
          { name: 'CEO (Gemini)', status: 'Orchestrating', color: 'var(--primary)' },
          { name: 'Risk (DeepSeek)', status: 'Computing Greeks', color: 'var(--danger)' },
          { name: 'Macro (Qwen)', status: 'Analyzing Trends', color: 'var(--success)' },
          { name: 'Audit (Llama)', status: 'Verifying Compliance', color: 'var(--vantage-gold)' }
        ].map((agent, i) => (
          <div key={i} className="glass card" style={{ padding: '1rem', borderLeft: `4px solid ${agent.color}` }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.25rem' }}>{agent.name}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{agent.status}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {deliberations.length === 0 && !loading && (
          <div className="glass card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No active deliberations in the boardroom. Scanning markets...
          </div>
        )}
        {deliberations.map((d: any, idx) => (
          <div key={idx} className="glass card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div style={{ fontWeight: 700, color: 'var(--primary)' }}>Symbol: {d.symbol}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(d.timestamp).toLocaleString()}</div>
            </div>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              {d.deliberation}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
const Dashboard = ({ onSelectEvent, onSelectBoardroom, onNewMeeting, status, onRefresh }: any) => {
  const pnlStr = status?.pnl_24h || "+$0.00 (0.0%)";
  const equinoxScore = 80 + (status?.history?.length || 0);

  return (
    <div className="animate-fade-in">
      {/* Float Yield Ticker */}
      <div className="ticker-container" style={{ margin: '-2rem -3rem 2rem -3rem' }}>
        <div className="ticker-content">
          AAPLx +2.4% • MSFTx -0.5% • SPYx +1.2% • TSLAx +4.7% • NVDAx +0.8% • Total Float Yield (Q2): +8.4 bps ($47,231 captured) • Liquidation Queue: AWS-99283 pending...
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Vantage Command</h1>
          <p style={{ color: 'var(--text-muted)' }}>Self-driving corporate treasury & float orchestration</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="glass btn" onClick={onRefresh} style={{ border: '1px solid var(--primary)' }}>
            <RefreshCcw size={18} style={{ marginRight: '0.5rem' }} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={onNewMeeting}>
            <Plus size={20} /> Process Invoice
          </button>
        </div>
      </div>
      
      <div className="grid">
        <div className="glass card" style={{ position: 'relative', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <Activity color="var(--primary)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Equinox Score</h3>
          </div>
          <div className="equinox-score">{equinoxScore}</div>
          <div style={{ color: 'var(--success)', fontSize: '0.875rem' }}>Optimized • +1.2 from yesterday</div>
        </div>
        
        <div className="glass card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <TrendingUp color="var(--success)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Float Yield (24h)</h3>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>{pnlStr.split(' ')[0]}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Current APY: 5.42% (Weighted)</div>
        </div>
        
        <div className="glass card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <AlertCircle color="var(--vantage-gold)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Liquidation Events</h3>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>{status?.history?.filter((h: any) => h.side === 'expense').length || 0}</div>
          <div style={{ color: 'var(--vantage-gold)', fontSize: '0.875rem' }}>Active obligations in ledger</div>
        </div>

        <div className="glass card" style={{ cursor: 'pointer', border: '1px solid rgba(79, 70, 229, 0.3)' }} onClick={() => onSelectBoardroom()}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <Users color="var(--primary)" />
            <h3 style={{ color: 'var(--text-muted)' }}>Boardroom Pulse</h3>
          </div>
          <div style={{ fontSize: '0.9rem', color: 'var(--primary)', fontWeight: 600, marginBottom: '0.5rem' }}>CEO & Risk Officers Active</div>
          <div className="ticker-content" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap', overflow: 'hidden' }}>
            Analyzing {status?.history?.[0]?.symbol || 'latest markets'}... Council recommending {status?.history?.[0]?.side === 'buy' ? 'hedged entry' : 'liquidation'}...
          </div>
        </div>
      </div>

      <h2 style={{ marginTop: '3rem', marginBottom: '1.5rem' }}>Reasoning Path Ledger</h2>
      <div className="glass" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead style={{ background: 'var(--surface-light)' }}>
            <tr>
              <th style={{ padding: '1rem' }}>Event</th>
              <th style={{ padding: '1rem' }}>Strategy</th>
              <th style={{ padding: '1rem' }}>Yield Impact</th>
              <th style={{ padding: '1rem' }}>Confidence</th>
              <th style={{ padding: '1rem' }}></th>
            </tr>
          </thead>
          <tbody>
            {(status?.history || []).slice(0, 5).map((m: any) => (
              <tr key={m.id || m.order_id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }} onClick={onSelectEvent}>
                <td style={{ padding: '1rem', fontWeight: 500 }}>{m.side === 'expense' ? 'Invoice Liquidation' : 'Market Rebalance'}: {m.symbol}</td>
                <td style={{ padding: '1rem' }}>
                  <span className="badge" style={{ background: 'rgba(79, 70, 229, 0.1)', color: 'var(--primary)' }}>
                    {m.reasoning?.slice(0, 30)}...
                  </span>
                </td>
                <td style={{ padding: '1rem', color: 'var(--success)' }}>{m.side === 'buy' ? '+2.4 bps' : '-'}</td>
                <td style={{ padding: '1rem' }}>98%</td>
                <td style={{ padding: '1rem' }} onClick={(e) => e.stopPropagation()}><MoreVertical size={18} cursor="pointer" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
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

  const handleUploadComplete = () => {
    setShowUploadModal(false);
    fetchStatus();
    // Redirect to dashboard to see the new entry
    setActiveTab('dashboard');
  };

  return (
    <div className="app-container">
      {showUploadModal && (
        <UploadModal 
          onClose={() => setShowUploadModal(false)} 
          onUploadComplete={handleUploadComplete} 
        />
      )}
      <ChatBot />
      <aside className="sidebar">
        <div style={{ padding: '2rem', fontSize: '1.5rem', fontWeight: 900, letterSpacing: '-1px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ width: '32px', height: '32px', background: 'var(--primary)', borderRadius: '8px' }}></div> ActionPilot
        </div>
        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); }}
          >
            <LayoutDashboard size={20} /> Vantage Command
          </div>
          <div 
            className={`nav-item ${activeTab === 'trading' ? 'active' : ''}`}
            onClick={() => setActiveTab('trading')}
          >
            <TrendingUp size={20} /> Treasury (Hedge Fund)
          </div>
          <div 
            className={`nav-item ${activeTab === 'meetings' ? 'active' : ''}`}
            onClick={() => setActiveTab('meetings')}
          >
            <FileText size={20} /> Ledger (Events)
          </div>
          <div 
            className={`nav-item ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <History size={20} /> Audit (SOX)
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
            onSelectEvent={() => setActiveTab('meetings')}
            onSelectBoardroom={() => setActiveTab('boardroom')}
            onNewMeeting={() => setShowUploadModal(true)} 
            status={status}
            onRefresh={fetchStatus}
          />
        )}
        {activeTab === 'trading' && <TradingView />}
        {activeTab === 'meetings' && (
          <div className="animate-fade-in">
            <h2>Treasury Ledger</h2>
            <div className="glass card" style={{ marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>
                    <th style={{ padding: '1rem' }}>Time</th>
                    <th style={{ padding: '1rem' }}>Asset</th>
                    <th style={{ padding: '1rem' }}>Side</th>
                    <th style={{ padding: '1rem' }}>Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {(status?.history || []).map((h: any) => (
                    <tr key={h.id || h.order_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                      <td style={{ padding: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{h.time || 'recent'}</td>
                      <td style={{ padding: '1rem', fontWeight: 600 }}>{h.symbol}</td>
                      <td style={{ padding: '1rem' }}>
                        <span className={`badge ${h.side === 'buy' ? 'badge-success' : 'badge-warning'}`}>
                          {h.side.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{h.reasoning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {activeTab === 'audit' && <AuditLog />}
        {activeTab === 'boardroom' && <Boardroom />}
      </main>
    </div>
  );
};

export default App;
