import { ShieldCheck } from 'lucide-react';

const AuditLog = () => {
  const logs = [
    { 
      id: 1, 
      time: "10:45 AM", 
      agent: "Reasoning Agent", 
      action: "Extracted Commitments", 
      reasoning: "Detected verbal confirmation from Bob: 'We need 99.99% uptime'. Assigned as high-priority commitment.",
      status: "success" 
    },
    { 
      id: 2, 
      time: "10:46 AM", 
      agent: "Decision Agent", 
      action: "Created Follow-up Task", 
      reasoning: "Confidence score 94%. Meeting owner Alice committed to sending SLA draft. Created task with deadline Friday.",
      status: "success" 
    },
    { 
      id: 3, 
      time: "10:46 AM", 
      agent: "Execution Agent", 
      action: "Drafted Email", 
      reasoning: "Generated draft based on decisions: move to enterprise cluster and 99.99% SLA. Saved for approval.",
      status: "pending_approval" 
    },
    { 
      id: 4, 
      time: "10:47 AM", 
      agent: "Context Agent", 
      action: "Flagged Risk", 
      reasoning: "Budget concerns raised by Charlie. Detected 'budget might be a blocker'. Escalated to Manager dashboard.",
      status: "warning" 
    }
  ];

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Audit Trail</h1>
        <div className="glass" style={{ padding: '0.5rem 1rem', display: 'flex', gap: '1rem', fontSize: '0.875rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }}></div> Success
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--warning)' }}></div> Escalated
          </span>
        </div>
      </div>

      <div style={{ position: 'relative', paddingLeft: '2rem' }}>
        <div style={{ 
          position: 'absolute', 
          left: '7px', 
          top: 0, 
          bottom: 0, 
          width: '2px', 
          background: 'var(--border)',
          zIndex: 0
        }}></div>

        {logs.map((log) => (
          <div key={log.id} style={{ marginBottom: '2.5rem', position: 'relative', zIndex: 1 }}>
            <div style={{ 
              position: 'absolute', 
              left: '-2rem', 
              top: '4px',
              width: '16px', 
              height: '16px', 
              borderRadius: '50%', 
              background: log.status === 'success' ? 'var(--success)' : (log.status === 'warning' ? 'var(--warning)' : 'var(--primary)'),
              border: '4px solid var(--background)'
            }}></div>
            
            <div className="glass card" style={{ padding: '1.5rem', marginLeft: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 700, color: 'var(--primary)' }}>{log.agent}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{log.time}</span>
                  </div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{log.action}</h3>
                </div>
                <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-warning'}`}>
                  {log.status.replace('_', ' ')}
                </span>
              </div>
              
              <div style={{ 
                background: 'rgba(0,0,0,0.2)', 
                padding: '1rem', 
                borderRadius: '8px', 
                fontSize: '0.9rem', 
                color: 'var(--text-muted)',
                lineHeight: 1.6,
                borderLeft: '2px solid var(--primary)'
              }}>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--text)', fontWeight: 500 }}>
                  <ShieldCheck size={16} /> Agent Reasoning
                </div>
                {log.reasoning}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AuditLog;
