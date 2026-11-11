import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  History, 
  Plus, 
  Activity,
  AlertCircle,
  TrendingUp,
  RefreshCcw,
  Users,
  Mic,
  Loader2
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
          { name: 'Strategy Synthesis', status: 'LLM-assisted analysis', color: 'var(--primary)' },
          { name: 'Signal Risk Filter', status: 'Deterministic whipsaw checks', color: 'var(--danger)' },
          { name: 'Market Research', status: 'Kraken public market data', color: 'var(--success)' },
          { name: 'Audit Ledger', status: 'MongoDB event persistence', color: 'var(--vantage-gold)' }
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
        {deliberations.map((d: any, idx) => {
          const actionColor = d.action === 'BUY' ? 'var(--success)' : d.action === 'SELL' ? 'var(--danger)' : 'var(--vantage-gold)';
          return (
            <div key={idx} className="glass card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '1rem' }}>{d.pair || d.symbol || 'N/A'}</span>
                  <span style={{
                    background: actionColor,
                    color: '#000',
                    fontWeight: 800,
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.75rem',
                    borderRadius: '999px',
                    letterSpacing: '0.05em'
                  }}>{d.action || '—'}</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(d.timestamp).toLocaleString()}</div>
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '1rem' }}>
                {d.reasoning || d.deliberation || 'No reasoning provided.'}
              </div>
              <div style={{ display: 'flex', gap: '2rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {d.risk_score !== undefined && (
                  <div>Risk Score: <span style={{ color: d.risk_score > 70 ? 'var(--danger)' : 'var(--success)', fontWeight: 700 }}>{d.risk_score}/100</span></div>
                )}
                {d.confidence !== undefined && (
                  <div>Confidence: <span style={{ color: 'var(--primary)', fontWeight: 700 }}>{(d.confidence * 100).toFixed(0)}%</span></div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
const Dashboard = ({ onSelectEvent, onSelectBoardroom, onNewMeeting, status, onRefresh }: any) => {
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
          <button className="btn btn-primary" onClick={onNewMeeting}>
            <Plus size={20} /> Analyze Audio Note
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

        <div className="glass card" style={{ cursor: 'pointer', border: '1px solid rgba(79, 70, 229, 0.3)' }} onClick={onSelectBoardroom}>
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
                  <tr key={item.id || item.order_id} style={{ borderTop: '1px solid var(--border)', cursor: 'pointer' }} onClick={onSelectEvent}>
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
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [triggerScanOnLoad, setTriggerScanOnLoad] = useState(false);

  // Speechmatics Voice Recorder State
  const [isRecording, setIsRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [bgStatus, setBgStatus] = useState<string | null>(null);
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const audioChunksRef = React.useRef<Blob[]>([]);
  const timerRef = React.useRef<any>(null);

  const formatTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const startRecording = async () => {
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        stream.getTracks().forEach(track => track.stop());
        await uploadAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => {
        setSeconds(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.warn("Microphone access denied or error:", err);
      alert("Microphone access denied or unavailable. Falling back to high-fidelity audio simulation desk.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const uploadAudio = async (audioBlob: Blob) => {
    setBgStatus("🎙️ Speechmatics ASR transcribing...");
    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "executive_memo.wav");
      
      const res = await fetch(`${API_BASE_URL}/api/meetings/upload`, {
        method: "POST",
        body: formData
      });
      
      if (!res.ok) {
        throw new Error(`Upload failed: ${res.statusText}`);
      }
      
      setBgStatus("🧠 Council deliberating...");
      
      const data = await res.json();
      console.log("ASR meeting upload response:", data);
      setBgStatus(null);
      
      // Notify user with premium overlay/alert
      alert("Audio note transcribed and sent for analysis. No trade was placed.");
      
      // Automatically refresh the page/stats
      fetchStatus();
      // Navigate to boardroom tab to view the live deliberation
      setActiveTab('boardroom');
    } catch (err: any) {
      console.error(err);
      setBgStatus(null);
      alert("Audio note could not be processed. No trade was placed.");
    }
  };


  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => {
      clearInterval(interval);
      if (timerRef.current) clearInterval(timerRef.current);
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

  const handleUploadComplete = () => {
    setShowUploadModal(false);
    fetchStatus();
    // Redirect to Kraken Terminal (Hedge Fund) tab to begin council deliberation
    setActiveTab('trading');
    setTriggerScanOnLoad(true);
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
            className={`nav-item ${activeTab === 'trading' ? 'active' : ''}`}
            onClick={() => setActiveTab('trading')}
          >
            <TrendingUp size={20} /> AI Trader
          </div>
          <div 
            className={`nav-item ${activeTab === 'meetings' ? 'active' : ''}`}
            onClick={() => setActiveTab('meetings')}
          >
            <FileText size={20} /> Analysis Notes
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

        {/* Market Research Audio Note */}
        <div className="glass" style={{
          margin: '2rem 1.25rem',
          padding: '1.25rem',
          borderRadius: '16px',
          border: '1px solid var(--glass-border)',
          background: 'rgba(255, 255, 255, 0.01)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              background: isRecording ? 'var(--danger)' : 'var(--success)', 
              boxShadow: isRecording ? '0 0 10px var(--danger)' : '0 0 10px var(--success)',
              animation: isRecording ? 'pulse 1s infinite' : 'none' 
            }}></div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
              {isRecording ? "Recording Live..." : "Audio Research Note"}
            </span>
          </div>

          {bgStatus ? (
            <div style={{ textAlign: 'center', padding: '0.5rem 0', color: 'var(--primary)' }}>
              <Loader2 className="animate-spin" size={24} style={{ margin: '0 auto 0.5rem', animation: 'spin 1.5s linear infinite' }} />
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{bgStatus}</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', alignItems: 'center' }}>
              {isRecording ? (
                <>
                  <div style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--danger)', letterSpacing: '0.05em' }}>
                    {formatTime(seconds)}
                  </div>
                  <button 
                    onClick={stopRecording}
                    className="btn btn-danger"
                    style={{ width: '100%', padding: '0.6rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', background: 'var(--danger)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Stop & Transcribe
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={startRecording}
                    className="btn btn-primary"
                    style={{ width: '100%', padding: '0.6rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', background: 'var(--primary)', color: '#000', border: 'none', borderRadius: '8px', fontWeight: 700, cursor: 'pointer' }}
                  >
                    <Mic size={16} /> Record Memo
                  </button>
                  

                </>
              )}
            </div>
          )}
        </div>
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
        {activeTab === 'trading' && (
          <TradingView 
            autoStartScan={triggerScanOnLoad} 
            onScanStarted={() => setTriggerScanOnLoad(false)} 
          />
        )}
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
