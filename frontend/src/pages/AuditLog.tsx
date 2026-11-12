import { useEffect, useState } from 'react';
import { ShieldCheck, Loader2 } from 'lucide-react';
import { API_BASE_URL } from '../config';

const AuditLog = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/audit`);
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
      <Loader2 className="animate-spin" size={32} />
    </div>
  );

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Audit Trail</h1>
        <div className="glass" style={{ padding: '0.5rem 1rem', display: 'flex', gap: '1rem', fontSize: '0.875rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }}></div> Success
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--warning)' }}></div> Warning
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

        {logs.map((log, idx) => {
          const status = String(log.status || log.event_type || 'success').toLowerCase();
          const isSuccess = status.includes('success') || status.includes('filled') || status.includes('connected');
          const isWarning = status.includes('warning') || status.includes('rejected') || status.includes('error');
          const statusText = String(log.status || log.event_type || 'LOGGED').replace(/_/g, ' ');
          const agentName = log.agent || (log.event_type ? String(log.event_type).replace(/_/g, ' ') : 'SYSTEM');
          const actionText = log.action || log.event_type || 'System Event';
          const timeText = log.time || (log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Just now');
          const reasoningText = log.reasoning || (log.exchange ? `Exchange: ${String(log.exchange).toUpperCase()} (Key: ${log.masked_key || '—'})` : '') || (log.server ? `MetaTrader Server: ${log.server}` : '') || 'System audit log entry recorded.';

          return (
            <div key={log.id || log._id || idx} style={{ marginBottom: '2.5rem', position: 'relative', zIndex: 1 }}>
              <div style={{ 
                position: 'absolute', 
                left: '-2rem', 
                top: '4px',
                width: '16px', 
                height: '16px', 
                borderRadius: '50%', 
                background: isSuccess ? 'var(--success)' : (isWarning ? 'var(--warning)' : 'var(--primary)'),
                border: '4px solid var(--background)'
              }}></div>
              
              <div className="glass card" style={{ padding: '1.5rem', marginLeft: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontWeight: 700, color: 'var(--primary)' }}>{agentName}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        {timeText}
                      </span>
                    </div>
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{actionText}</h3>
                  </div>
                  <span className={`badge ${isSuccess ? 'badge-success' : (isWarning ? 'badge-warning' : '')}`}>
                    {statusText}
                  </span>
                </div>
                
                <div style={{ 
                  background: '#f4f6f9', 
                  padding: '1rem', 
                  borderRadius: '8px', 
                  fontSize: '0.9rem', 
                  color: 'var(--text-muted)',
                  lineHeight: 1.6,
                  border: '1px solid rgba(36, 86, 230, 0.3)'
                }}>
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--text)', fontWeight: 500 }}>
                    <ShieldCheck size={16} /> Reasoning / Details
                  </div>
                  {reasoningText}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AuditLog;
