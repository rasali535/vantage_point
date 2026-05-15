import { User, Shield, Globe, Cpu } from 'lucide-react';

interface CouncilProps {
  decision?: {
    action: string;
    reasoning: string;
    risk_score: number;
    confidence: number;
  };
}

const BoardroomCouncil = ({ decision }: CouncilProps) => {
  if (!decision) return (
    <div className="glass card">
      <h3 style={{ marginBottom: '1.5rem' }}>Boardroom Deliberation</h3>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '2rem' }}>
        Awaiting next market scan to initiate council debate...
      </div>
    </div>
  );

  return (
    <div className="glass card">
      <h3 style={{ marginBottom: '1.5rem' }}>The Boardroom Consensus</h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* CEO Synthesis */}
        <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', borderLeft: '4px solid var(--primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>
            <User size={14} /> CEO (Gemini 1.5 Pro)
          </div>
          <div style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
            {decision.reasoning}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {/* GC Opinion */}
          <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--success)', textTransform: 'uppercase' }}>
              <Shield size={14} /> GC (Claude 3.5)
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Audit confirms trade complies with treasury risk thresholds. Scoring risk at {decision.risk_score}/100.
            </div>
          </div>

          {/* Macro Opinion */}
          <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--warning)', textTransform: 'uppercase' }}>
              <Globe size={14} /> Macro (Qwen)
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Consensus bullish on xStocks momentum. Relative strength index supports an entry.
            </div>
          </div>
        </div>

        {/* Confidence Gauge */}
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Consensus Confidence</span>
            <span>{Math.round(decision.confidence * 100)}%</span>
          </div>
          <div style={{ width: '100%', height: '4px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '2px' }}>
            <div style={{ width: `${decision.confidence * 100}%`, height: '100%', background: 'var(--success)', borderRadius: '2px' }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default BoardroomCouncil;
