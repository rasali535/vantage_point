import React from 'react';
import { 
  ArrowLeft, 
  Play, 
  Download, 
  MessageSquare, 
  Zap, 
  AlertTriangle, 
  User, 
  Clock,
  ShieldCheck,
  Mail,
  Copy
} from 'lucide-react';

interface MeetingDetailProps {
  meetingId: string;
  onBack: () => void;
}

const MeetingDetail: React.FC<MeetingDetailProps> = ({ meetingId, onBack }) => {
  // Mock data for the meeting
  const meeting = {
    title: "Acme Corp Contract Review",
    date: "May 13, 2026",
    duration: "45 min",
    health: 85,
    status: "Completed",
    transcript: [
      { speaker: "Alice (Sales)", text: "Hi everyone, thanks for joining. I wanted to walk through the latest proposal for Acme Corp." },
      { speaker: "Bob (Client)", text: "Thanks Alice. We've reviewed the draft. The pricing looks okay, but we have some concerns about the SLA terms." },
      { speaker: "Alice (Sales)", text: "I understand. We can definitely look into adjusting the SLA for your tier. What specific metrics are you looking for?" },
      { speaker: "Bob (Client)", text: "We need 99.99% uptime guarantee, especially for the core API services." },
      { speaker: "Charlie (Ops)", text: "99.99% is doable if we move them to the enterprise infrastructure cluster. I'll need to check the budget for that." },
      { speaker: "Alice (Sales)", text: "Great. Charlie, could you get that budget estimate by Friday? I'll send Bob a follow-up email with the updated SLA draft once I have your confirmation." }
    ],
    analysis: {
      decisions: [
        "Move Acme Corp to enterprise infrastructure for 99.99% SLA.",
        "Update contract draft with new uptime guarantees."
      ],
      blockers: [
        "Ops budget approval for enterprise cluster migration."
      ],
      commitments: [
        { id: 1, owner: "Charlie", task: "Check budget for enterprise cluster migration", deadline: "Friday, May 15", completed: false },
        { id: 2, owner: "Alice", task: "Send follow-up email with updated SLA draft", deadline: "After budget check", completed: false }
      ]
    }
  };

  const [tasks, setTasks] = React.useState(meeting.analysis.commitments);

  const toggleTask = (id: number) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  return (
    <div className="animate-fade-in">
      <button 
        onClick={onBack}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '1.5rem' }}
      >
        <ArrowLeft size={18} /> Back to Dashboard
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h1 style={{ margin: 0 }}>{meeting.title}</h1>
            <span className="badge badge-success">{meeting.status}</span>
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Clock size={14} /> {meeting.date}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><User size={14} /> 3 Participants</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button 
            className="btn" 
            style={{ background: 'var(--surface-light)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            onClick={() => {
              const report = `Meeting: ${meeting.title}\nDate: ${meeting.date}\nHealth: ${meeting.health}%\n\nDecisions:\n${meeting.analysis.decisions.join('\n')}\n\nTasks:\n${tasks.map(t => `- [${t.completed ? 'x' : ' '}] ${t.task} (${t.owner})`).join('\n')}`;
              const blob = new Blob([report], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${meeting.title.replace(/\s+/g, '_')}_Report.txt`;
              a.click();
            }}
          >
            <Download size={18} /> Export Report
          </button>
          <div className="glass" style={{ padding: '0.75rem 1.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Deal Health</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>{meeting.health}%</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
        {/* Left Column: Transcript */}
        <div className="glass card" style={{ height: '70vh', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', position: 'sticky', top: 0, background: 'var(--glass)', padding: '0.5rem 0' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><MessageSquare size={20} color="var(--primary)" /> Transcript</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn" style={{ padding: '0.4rem', background: 'var(--surface-light)' }}><Play size={16} /></button>
              <button className="btn" style={{ padding: '0.4rem', background: 'var(--surface-light)' }}><Download size={16} /></button>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {meeting.transcript.map((t, i) => (
              <div key={i}>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.25rem', color: t.speaker.includes('Alice') ? 'var(--primary)' : 'var(--text)' }}>{t.speaker}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>{t.text}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: AI Analysis */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* RevenueOps Insights */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <ShieldCheck size={20} color="var(--primary)" /> RevenueOps Insights
            </h3>
            
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Sales Objections</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {(meeting.analysis["Sales Objections"] || ["None detected"]).map((obj, i) => (
                  <span key={i} className="badge badge-warning" style={{ fontSize: '0.75rem' }}>{obj}</span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Competitive Intel</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                {meeting.analysis["Competitive Intel"] || "No competitors mentioned."}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Risk Assessment</div>
              <div style={{ color: 'var(--danger)', fontSize: '0.9rem', fontWeight: 500 }}>
                {meeting.analysis["Risk Assessment"] || "Low risk."}
              </div>
            </div>
          </div>

          {/* Action Items */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <Zap size={20} color="var(--warning)" /> Autonomous Actions
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {tasks.map((c) => (
                <div key={c.id} className="glass" style={{ 
                  padding: '1rem', 
                  border: '1px solid var(--glass-border)',
                  opacity: c.completed ? 0.6 : 1,
                  transition: 'all 0.3s ease'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span className={`badge ${c.completed ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
                      {c.completed ? 'Completed' : 'Action Required'}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Due {c.deadline}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                    <input 
                      type="checkbox" 
                      checked={c.completed} 
                      onChange={() => toggleTask(c.id)}
                      style={{ marginTop: '0.25rem', width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <div style={{ fontWeight: 500, marginBottom: '0.75rem', textDecoration: c.completed ? 'line-through' : 'none' }}>{c.task}</div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyItems: 'center', fontSize: '0.7rem', color: 'white', justifyContent: 'center' }}>{c.owner[0]}</div>
                      <span>{c.owner}</span>
                    </div>
                    <button className="btn" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', background: 'var(--surface-light)' }}><Mail size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* Blockers */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <AlertTriangle size={20} color="var(--danger)" /> Key Blockers
            </h3>
            {meeting.analysis.blockers.map((b, i) => (
              <div key={i} style={{ fontSize: '0.95rem', color: 'var(--text)', marginBottom: '0.5rem' }}>• {b}</div>
            ))}
          </div>

          {/* Generated Follow-up */}
          <div className="glass card">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Mail size={20} color="var(--primary)" /> Drafted Follow-up
            </h3>
            <div className="glass" style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)', fontFamily: 'monospace', maxHeight: '150px', overflowY: 'auto' }}>
              Subject: Follow-up: Acme Corp Contract & SLA Update<br/><br/>
              Hi Bob,<br/><br/>
              Great speaking with you today. We've decided to move your account to our enterprise infrastructure cluster to support the 99.99% uptime guarantee you requested.<br/><br/>
              Charlie is currently finalizing the budget estimate for this migration, and I will share the updated SLA draft with you by Friday.<br/><br/>
              Best regards,<br/>
              Alice
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button className="btn btn-primary" style={{ flex: 1, fontSize: '0.875rem' }}><Mail size={16} /> Send Now</button>
              <button className="btn" style={{ background: 'var(--surface-light)', flex: 1, fontSize: '0.875rem' }}><Copy size={16} /> Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MeetingDetail;
