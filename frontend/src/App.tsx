import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  History, 
  Plus, 
  MoreVertical,
  Activity,
  AlertCircle,
  TrendingUp
} from 'lucide-react';

import MeetingDetail from './components/MeetingDetail';
import UploadModal from './components/UploadModal';
import AuditLog from './pages/AuditLog';
import TradingView from './components/TradingView';
import ChatBot from './components/ChatBot';

// Mock Components for Vantage-Point 2.0
const Dashboard = ({ onSelectMeeting, onNewMeeting }: { onSelectMeeting: (id: string) => void, onNewMeeting: () => void }) => (
  <div className="animate-fade-in">
    {/* Float Yield Ticker */}
    <div className="ticker-container" style={{ margin: '-2rem -3rem 2rem -3rem' }}>
      <div className="ticker-content">
        BTCx +2.4% • ETHx -0.5% • SPYx +1.2% • TSLAx +4.7% • AAPLx +0.8% • Total Float Yield (Q2): +8.4 bps ($47,231 captured) • Liquidation Queue: AWS-99283 pending...
      </div>
    </div>

    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
      <div>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Vantage Command</h1>
        <p style={{ color: 'var(--text-muted)' }}>Self-driving corporate treasury & float orchestration</p>
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <button className="glass btn" style={{ border: '1px solid var(--primary)' }}>
          <TrendingUp size={18} style={{ marginRight: '0.5rem' }} /> Briefing
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
        <div className="equinox-score">87</div>
        <div style={{ color: 'var(--success)', fontSize: '0.875rem' }}>Optimized • +1.2 from yesterday</div>
        {/* Simple CSS-based wave or graph could go here */}
      </div>
      
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <TrendingUp color="var(--success)" />
          <h3 style={{ color: 'var(--text-muted)' }}>Float Yield (24h)</h3>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>+$1,242.40</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Current APY: 5.42% (Weighted)</div>
      </div>
      
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <AlertCircle color="var(--vantage-gold)" />
          <h3 style={{ color: 'var(--text-muted)' }}>Liquidation Events</h3>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>3</div>
        <div style={{ color: 'var(--vantage-gold)', fontSize: '0.875rem' }}>$42k scheduled for T-48h</div>
      </div>
    </div>

    {/* The Boardroom - Multi-Agent Council */}
    <h2 style={{ marginTop: '3rem', marginBottom: '1.5rem' }}>The Boardroom <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Live Deliberation)</span></h2>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
      {[
        { name: 'CEO', icon: 'Gemini', status: 'Orchestrating', color: 'var(--primary)' },
        { name: 'GC', icon: 'Llama', status: 'Auditing Contracts', color: 'var(--vantage-gold)' },
        { name: 'Risk', icon: 'Gemini', status: 'Computing Greeks', color: 'var(--danger)' },
        { name: 'Macro', icon: 'Llama', status: 'Settlement Timing', color: 'var(--success)' }
      ].map((agent, i) => (
        <div key={i} className={`boardroom-agent ${i === 0 ? 'active' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600, fontSize: '0.8rem' }}>{agent.name}</span>
            <span style={{ fontSize: '0.7rem', color: agent.color }}>{agent.status}</span>
          </div>
          <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
            <div style={{ width: i === 0 ? '70%' : '100%', height: '100%', background: agent.color, borderRadius: '2px' }}></div>
          </div>
        </div>
      ))}
    </div>

    <h2 style={{ marginTop: '3rem', marginBottom: '1.5rem' }}>Reasoning Path Ledger</h2>
    <div className="glass" style={{ overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead style={{ background: 'var(--surface-light)' }}>
          <tr>
            <th style={{ padding: '1rem' }}>Event</th>
            <th style={{ padding: '1rem' }}>Strategy</th>
            <th style={{ padding: '1rem' }}>Float Yield</th>
            <th style={{ padding: '1rem' }}>Confidence</th>
            <th style={{ padding: '1rem' }}></th>
          </tr>
        </thead>
        <tbody>
          {[
            { id: '1', title: 'Invoice Liquidation: AWS-99283', strategy: 'Sell TSLAx (High Vol)', yield: '+2.4 bps', confidence: '98%' },
            { id: '2', title: 'Payroll Rebalancing', strategy: 'Delay ACH 24h', yield: '+0.8 bps', confidence: '72%' },
            { id: '3', title: 'Treasury Swap: USD → BTCx', strategy: 'Macro Alignment', yield: '+12.4 bps', confidence: '94%' },
          ].map(m => (
            <tr key={m.id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }} onClick={() => onSelectMeeting(m.id)}>
              <td style={{ padding: '1rem', fontWeight: 500 }}>{m.title}</td>
              <td style={{ padding: '1rem' }}>
                <span className="badge" style={{ background: 'rgba(79, 70, 229, 0.1)', color: 'var(--primary)' }}>
                  {m.strategy}
                </span>
              </td>
              <td style={{ padding: '1rem', color: 'var(--success)' }}>{m.yield}</td>
              <td style={{ padding: '1rem' }}>{m.confidence}</td>
              <td style={{ padding: '1rem' }} onClick={(e) => e.stopPropagation()}><MoreVertical size={18} cursor="pointer" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const handleSelectMeeting = (id: string) => {
    setSelectedMeetingId(id);
    setActiveTab('meetings');
  };

  const handleUploadComplete = (id: string) => {
    setShowUploadModal(false);
    setSelectedMeetingId(id);
    setActiveTab('meetings');
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
        {/* ... Logo ... */}
        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); setSelectedMeetingId(null); }}
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
        </nav>
        {/* ... Settings ... */}
      </aside>

      <main className="main-content">
        {/* ... Header ... */}

        {activeTab === 'dashboard' && (
          <Dashboard onSelectMeeting={handleSelectMeeting} onNewMeeting={() => setShowUploadModal(true)} />
        )}
        {activeTab === 'trading' && <TradingView />}
        {activeTab === 'meetings' && selectedMeetingId && (
          <MeetingDetail meetingId={selectedMeetingId} onBack={() => { setActiveTab('dashboard'); setSelectedMeetingId(null); }} />
        )}
        {activeTab === 'audit' && <AuditLog />}
      </main>
    </div>
  );
};

export default App;
