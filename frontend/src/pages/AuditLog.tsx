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

        {logs.map((log) => (
          <div key={log.id || log._id} style={{ marginBottom: '2.5rem', position: 'relative', zIndex: 1 }}>
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
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {log.time || new Date(log.timestamp).toLocaleTimeString()}
                    </span>
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
