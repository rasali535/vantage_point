import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  CheckSquare, 
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

// Mock Pages
const Dashboard = ({ onSelectMeeting, onNewMeeting }: { onSelectMeeting: (id: string) => void, onNewMeeting: () => void }) => (
  <div className="animate-fade-in">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
      <h1>Manager Dashboard</h1>
      <button className="btn btn-primary" onClick={onNewMeeting}><Plus size={20} /> New Meeting</button>
    </div>
    
    <div className="grid">
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <Activity color="var(--primary)" />
          <h3 style={{ color: 'var(--text-muted)' }}>Meetings Processed</h3>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>24</div>
        <div style={{ color: 'var(--success)', fontSize: '0.875rem' }}>+12% from last week</div>
      </div>
      
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <CheckSquare color="var(--success)" />
          <h3 style={{ color: 'var(--text-muted)' }}>Actions Executed</h3>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>142</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>85% autonomous</div>
      </div>
      
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <AlertCircle color="var(--danger)" />
          <h3 style={{ color: 'var(--text-muted)' }}>At-Risk Deals</h3>
        </div>
        <div style={{ fontSize: '2.5rem', fontWeight: 700 }}>4</div>
        <div style={{ color: 'var(--danger)', fontSize: '0.875rem' }}>Immediate action required</div>
      </div>
    </div>

    <h2 style={{ marginTop: '3rem', marginBottom: '1.5rem' }}>Recent Activity</h2>
    <div className="glass" style={{ overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead style={{ background: 'var(--surface-light)' }}>
          <tr>
            <th style={{ padding: '1rem' }}>Meeting</th>
            <th style={{ padding: '1rem' }}>Status</th>
            <th style={{ padding: '1rem' }}>Actions Taken</th>
            <th style={{ padding: '1rem' }}>Confidence</th>
            <th style={{ padding: '1rem' }}></th>
          </tr>
        </thead>
        <tbody>
          {[
            { id: '1', title: 'Acme Corp Contract Review', status: 'Executed', actions: 5, confidence: '98%' },
            { id: '2', title: 'Global Tech Partnership', status: 'Pending Approval', actions: 3, confidence: '72%' },
            { id: '3', title: 'Weekly Pipeline Sync', status: 'Executed', actions: 12, confidence: '94%' },
          ].map(m => (
            <tr key={m.id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }} onClick={() => onSelectMeeting(m.id)}>
              <td style={{ padding: '1rem', fontWeight: 500 }}>{m.title}</td>
              <td style={{ padding: '1rem' }}>
                <span className={`badge ${m.status === 'Executed' ? 'badge-success' : 'badge-warning'}`}>
                  {m.status}
                </span>
              </td>
              <td style={{ padding: '1rem' }}>{m.actions} items</td>
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
      <aside className="sidebar">
        {/* ... Logo ... */}
        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); setSelectedMeetingId(null); }}
          >
            <LayoutDashboard size={20} /> Dashboard
          </div>
          <div 
            className={`nav-item ${activeTab === 'trading' ? 'active' : ''}`}
            onClick={() => setActiveTab('trading')}
          >
            <TrendingUp size={20} /> Kraken Trading
          </div>
          <div 
            className={`nav-item ${activeTab === 'meetings' ? 'active' : ''}`}
            onClick={() => setActiveTab('meetings')}
          >
            <FileText size={20} /> Meetings
          </div>
          <div 
            className={`nav-item ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <History size={20} /> Audit Trail
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
