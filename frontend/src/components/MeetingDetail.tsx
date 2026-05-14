import React from 'react';
import { 
  ArrowLeft, 
  Download, 
  Zap, 
  Clock,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';

interface MeetingDetailProps {
  meetingId: string;
  onBack: () => void;
}

const MeetingDetail: React.FC<MeetingDetailProps> = ({ meetingId, onBack }) => {
  // Mock data for the treasury event
  const meeting = {
    title: `AWS Infrastructure Invoice (#${meetingId.slice(0, 5)})`,
    date: "May 13, 2026",
    health: 87, // Equinox Score
    status: "Anchored",
    analysis: {
      decisions: [
        "Delay liquidation until T-24h penalty threshold.",
        "Execute sell order on Kraken for TSLAx to fund A/P."
      ],
    }
  };

  return (
    <div className="animate-fade-in">
      <button 
        onClick={onBack}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '1.5rem' }}
      >
        <ArrowLeft size={18} /> Back to Command
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h1 style={{ margin: 0 }}>{meeting.title}</h1>
            <span className="badge badge-success">Anchored</span>
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Clock size={14} /> {meeting.date}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><ShieldCheck size={14} /> SOX-Ready Hash: 0x82f...a12</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button 
            className="btn" 
            style={{ background: 'var(--surface-light)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Download size={18} /> Audit PDF
          </button>
          <div className="glass" style={{ padding: '0.75rem 1.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Equinox Score</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{meeting.health}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
        {/* Left Column: Boardroom Path */}
        <div className="glass card" style={{ height: '70vh', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={20} color="var(--primary)" /> Boardroom Path 
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}> (Multi-Agent Deliberation)</span>
            </h3>
          </div>
          <div className="reasoning-log" style={{ flex: 1, overflowY: 'auto' }}>
            <div style={{ color: 'var(--primary)', marginBottom: '0.5rem' }}>[CEO] Initiating liquidation strategy for AWS Invoice-99283...</div>
            <div style={{ color: 'var(--vantage-gold)', marginBottom: '0.5rem' }}>[General Counsel] Auditing Section 4.2: 5-day grace period detected. Penalty: 2.5% after Day 15. Recommendation: Liquidate Day 14 for max yield capture.</div>
            <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>[Risk Officer] Warning: Selling ETHx at current vol levels (IV 74%) increases delta exposure. Suggesting TSLAx liquidation instead.</div>
            <div style={{ color: 'var(--success)', marginBottom: '1rem' }}>[Macro Strategist] Settlement windows for xStocks align at 14:00 UTC tomorrow. Executing sell-side order for $42,500.</div>
            <div style={{ color: '#6ee7b7' }}>--- HASH ANCHOR GENERATED: 0x2838...a2 ---</div>
            <div style={{ color: 'var(--text-muted)', marginTop: '1rem' }}>&gt; Awaiting autonomous execution...</div>
          </div>
        </div>

        {/* Right Column: Execution Insights */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* General Counsel Audit */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <ShieldCheck size={20} color="var(--vantage-gold)" /> General Counsel Audit
            </h3>
            
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Late Fee Detection</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                <span className="badge badge-danger" style={{ fontSize: '0.75rem' }}>2.5% Penalty Found</span>
                <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>15-day Grace Period</span>
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Optimized Date</div>
              <div style={{ color: 'var(--success)', fontSize: '1.1rem', fontWeight: 600 }}>
                May 27, 2026 (T-24h before penalty)
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Yield Capture Potential</div>
              <div style={{ color: 'var(--primary)', fontSize: '0.9rem', fontWeight: 500 }}>
                +14.2 bps extra yield by delaying settlement.
              </div>
            </div>
          </div>

          {/* Treasury Execution Queue */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <TrendingUp size={20} color="var(--primary)" /> Execution Queue
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[
                { id: 1, task: "Liquidate $42k TSLAx on Kraken", status: "Scheduled", color: "var(--warning)" },
                { id: 2, task: "ACH Transfer to Chase (A/P Account)", status: "Pending", color: "var(--text-muted)" }
              ].map((c) => (
                <div key={c.id} className="glass" style={{ padding: '1rem', border: '1px solid var(--glass-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: c.color, fontSize: '0.65rem' }}>
                      {c.status}
                    </span>
                  </div>
                  <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{c.task}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MeetingDetail;
