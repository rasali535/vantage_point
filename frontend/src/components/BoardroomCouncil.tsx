import { Shield, Brain } from 'lucide-react';

interface CouncilProps {
  decision?: {
    action: string;
    reasoning: string;
    risk_score: number;
    confidence: number;
    signal_quality?: number;
    whipsaw_risk?: string;
  };
  scanning?: boolean;
}

const BoardroomCouncil = ({ decision, scanning }: CouncilProps) => {
  if (scanning) {
    return (
      <div className="glass card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="spinner-small" />
          <div>
            <h3>Market Analysis in Progress</h3>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Fetching Kraken market data and evaluating the current signal</div>
          </div>
        </div>
        <style>{`
          .spinner-small {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.1);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
        `}</style>
      </div>
    );
  }

  if (!decision) {
    return (
      <div className="glass card">
        <h3 style={{ marginBottom: '0.75rem' }}>AI Market Analysis</h3>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          No completed analysis is available yet. Start a scan when MongoDB and Kraken market data are reachable.
        </div>
      </div>
    );
  }

  const signalQuality = decision.signal_quality;
  const qualityColor = signalQuality === undefined ? 'var(--text-muted)' :
    signalQuality >= 60 ? 'var(--success)' : signalQuality >= 30 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div className="glass card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
        <h3>AI Market Analysis</h3>
        <span className="badge">Recommendation only</span>
      </div>

      <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.08)', borderRadius: '8px', borderLeft: '4px solid var(--primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>
          <Brain size={14} /> Proposed action: {decision.action || 'HOLD'}
        </div>
        <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
          {decision.reasoning || 'No reasoning was returned.'}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
        <div style={{ padding: '0.85rem', background: 'rgba(255,255,255,0.025)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.35rem' }}>Model risk score</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{decision.risk_score ?? '—'}<span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/100</span></div>
        </div>
        <div style={{ padding: '0.85rem', background: 'rgba(255,255,255,0.025)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.35rem' }}>Model confidence</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{typeof decision.confidence === 'number' ? `${Math.round(decision.confidence * 100)}%` : '—'}</div>
        </div>
        <div style={{ padding: '0.85rem', background: 'rgba(255,255,255,0.025)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '0.35rem' }}>Signal quality</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: qualityColor }}>{signalQuality !== undefined ? `${signalQuality}%` : '—'}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{decision.whipsaw_risk || 'Not available'}</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1.25rem', color: 'var(--warning)', fontSize: '0.8rem' }}>
        <Shield size={15} /> Execution is disabled. This recommendation cannot submit an order.
      </div>
    </div>
  );
};

export default BoardroomCouncil;
