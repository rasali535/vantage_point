import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCcw, LayoutDashboard, Bot, Activity, Users, Shield, Smartphone, Tablet, Monitor } from 'lucide-react';

import AuditLog from './pages/AuditLog';
import TradingView from './components/TradingView';
import ChatBot from './components/ChatBot';
import { API_BASE_URL } from './config';
import PaperTrading from './pages/PaperTrading';
import MirofishTerminal from './components/MirofishTerminal';

export const FOREX_PAIRS = [
  'EUR/USD',
  'GBP/USD',
  'USD/JPY',
  'AUD/USD',
  'USD/CAD',
  'USD/CHF',
  'EUR/GBP',
  'EUR/JPY',
  'EUR/CHF',
  'EUR/AUD',
  'EUR/CAD',
  'AUD/JPY',
];

export const METAL_PAIRS = [
  'XAU/USD',
  'XAG/USD',
  'XPT/USD',
  'XCU/USD',
];

export const INDEX_PAIRS = [
  'SPX500/USD',
  'NAS100/USD',
  'US30/USD',
  'UK100/USD',
  'GER40/USD',
  'JPN225/USD',
];

export const CRYPTO_PAIRS = [
  'BTC/USD',
  'ETH/USD',
  'SOL/USD',
  'XRP/USD',
  'ADA/USD',
  'DOGE/USD',
  'LTC/USD',
  'LINK/USD',
  'DOT/USD',
  'BCH/USD',
];

export const ALL_TRADING_PAIRS = [
  ...FOREX_PAIRS,
  ...METAL_PAIRS,
  ...INDEX_PAIRS,
  ...CRYPTO_PAIRS,
];

const Boardroom = ({ deliberations, loading, onRefresh }: { deliberations: any[]; loading: boolean; onRefresh: () => void }) => {
  return (
    <div className="animate-fade-in">
      <div className="mf-card" style={{ marginBottom: '12px' }}>
        <div className="mf-section-bar" style={{ marginBottom: '14px' }}>
          <div className="mf-section-title-left">
            <span className="mf-dot mf-dot-terra" />
            <span className="mf-card-heading">SIX-AGENT BOARDROOM · LIVE DELIBERATION LEDGER</span>
          </div>
          <button type="button" className="mf-pill-action" onClick={onRefresh}>
            <RefreshCcw size={12} style={{ marginRight: 5 }} /> REFRESH
          </button>
        </div>

        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(185px, 1fr))', gap: '10px' }}>
          {[
            { name: 'Market Intelligence', status: 'Meta AI · verified FX & crypto context', color: '#2563eb' },
            { name: 'Technical Analyst', status: 'EMA · RSI · ATR calculations', color: '#10b981' },
            { name: 'Strategy', status: 'Meta AI · BUY / SELL / HOLD proposal', color: '#2563eb' },
            { name: 'Risk Manager', status: 'Meta AI advisory · deterministic limits', color: '#9a3412' },
            { name: 'Execution', status: 'Risk preflight · paper simulation gate', color: '#b45309' },
            { name: 'Performance', status: 'Confirmed closed trades only', color: '#10b981' },
          ].map((agent) => (
            <div key={agent.name} className="mf-subcard">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: agent.color, flexShrink: 0 }} />
                <div style={{ fontWeight: 700, fontSize: '0.82rem' }}>{agent.name}</div>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{agent.status}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {deliberations.length === 0 && !loading && (
          <div className="mf-card" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
            No six-agent analysis cycles have been recorded yet. Use the pair scanner in the top bar to start the boardroom.
          </div>
        )}
        {deliberations.map((d: any, idx: number) => {
          const strategy = d.strategy || {};
          const technical = d.technical_analysis || {};
          const risk = d.risk_assessment || {};
          const execution = d.execution_assessment || {};
          const performance = d.performance_context || {};
          const action = String(strategy.action || d.action || 'HOLD').toUpperCase();
          const reasoning = strategy.rationale || d.reasoning || 'No reasoning provided.';
          const actionColor = action === 'BUY' ? '#2563eb' : action === 'SELL' ? '#9a3412' : '#b45309';
          return (
            <div key={idx} className="mf-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontWeight: 800, color: '#111827', fontSize: '0.95rem', fontFamily: 'var(--font-mono)' }}>{d.pair || d.symbol || 'N/A'}</span>
                  <span
                    style={{
                      background: actionColor,
                      color: '#fff',
                      fontWeight: 800,
                      fontSize: '0.7rem',
                      padding: '0.2rem 0.65rem',
                      borderRadius: '999px',
                      letterSpacing: '0.06em',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {action}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {d.timestamp ? new Date(d.timestamp).toLocaleString() : '—'}
                </div>
              </div>
              <div style={{ fontSize: '0.86rem', color: 'var(--text)', lineHeight: 1.65, marginBottom: '1rem' }}>
                {reasoning}
              </div>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.65rem', fontSize: '0.76rem', fontFamily: 'var(--font-mono)' }}>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>TECHNICAL TREND</span><br /><strong>{technical.trend || 'Unavailable'}</strong></div>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>RSI 14</span><br /><strong>{typeof technical.rsi_14 === 'number' ? technical.rsi_14.toFixed(1) : '—'}</strong></div>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>RISK ASSESSMENT</span><br /><strong>{risk.summary || 'Not available'}</strong></div>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>EXECUTION GATE</span><br /><strong>{execution.status || 'Not evaluated'}</strong></div>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>PERF SAMPLE</span><br /><strong>{performance.sample_size ?? 0} confirmed trades</strong></div>
                <div className="mf-subcard"><span style={{ color: 'var(--text-muted)' }}>EXECUTION</span><br /><strong style={{ color: '#9a3412' }}>Paper Sim · Live Locked</strong></div>
              </div>
              <div style={{ marginTop: '0.65rem', fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                STRATEGY CONFIDENCE: {typeof strategy.confidence === 'number' ? `${(strategy.confidence * 100).toFixed(0)}%` : '—'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'terminal' | 'paper' | 'trading' | 'boardroom' | 'audit'>('terminal');
  const [viewportMode, setViewportMode] = useState<'auto' | 'tablet' | 'mobile'>('auto');
  const [status, setStatus] = useState<any>(null);
  const [deliberations, setDeliberations] = useState<any[]>([]);
  const [boardroomLoading, setBoardroomLoading] = useState(true);
  const [pair, setPair] = useState('EUR/USD');
  const [scanning, setScanning] = useState(false);
  const [lastScanDecision, setLastScanDecision] = useState<any>(null);
  const [scanBanner, setScanBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const [utcClock, setUtcClock] = useState('');

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/status`);
      const data = await res.json();
      if (!res.ok) {
        setStatus({
          balance: null,
          history: [],
          pnl_24h: null,
          active_strategy: 'Unavailable',
          exchange_status: 'unavailable',
          error: data.detail || 'Service unavailable',
        });
        return;
      }
      setStatus({ ...data, history: Array.isArray(data.history) ? data.history : [] });
    } catch (err) {
      console.error(err);
    }
  }, []);

  const fetchBoardroom = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/boardroom`);
      if (!res.ok) return;
      const data = await res.json();
      setDeliberations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    } finally {
      setBoardroomLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
    void fetchBoardroom();
    const interval = window.setInterval(() => {
      void fetchStatus();
      void fetchBoardroom();
    }, 15000);
    return () => window.clearInterval(interval);
  }, [fetchStatus, fetchBoardroom]);

  useEffect(() => {
    const tick = () => setUtcClock(`${new Date().toISOString().slice(11, 19)} UTC`);
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  const handleRunScan = async () => {
    if (scanning) return;
    setScanning(true);
    setScanBanner(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pair }),
      });
      if (!res.ok) {
        let message = `Server Error (${res.status})`;
        let requestId = '';
        try {
          const payload = await res.json();
          const detail = payload?.detail;
          if (typeof detail === 'string') message = detail;
          else if (detail && typeof detail === 'object') {
            message = detail.message || message;
            requestId = detail.request_id || '';
          }
        } catch {
          // Keep status fallback
        }
        throw new Error(requestId ? `${message} (Ref: ${requestId})` : message);
      }
      const data = await res.json();
      setLastScanDecision({
        ...data.decision,
        pair: data.pair,
        signal_quality: data.signal_quality_report?.signal_quality_index,
        whipsaw_risk: data.signal_quality_report?.whipsaw_risk,
      });
      setScanBanner({
        type: 'ok',
        text: `Six-agent scan completed for ${data.pair}: Proposed ${data.decision?.action || 'HOLD'} (${Math.round((data.decision?.confidence || 0) * 100)}% confidence).`,
      });
      await Promise.all([fetchStatus(), fetchBoardroom()]);
    } catch (err: any) {
      setScanBanner({
        type: 'err',
        text: `Market analysis failed. No order was submitted. ${err.message || ''}`,
      });
    } finally {
      setScanning(false);
    }
  };

  const totalRounds = deliberations.length + (Array.isArray(status?.history) ? status.history.length : 0);
  const paperEquity = status?.paper_portfolio?.equity ? Number(status.paper_portfolio.equity) : null;
  const paperPnl = status?.paper_portfolio?.total_pnl ? Number(status.paper_portfolio.total_pnl) : 0;

  return (
    <div className={`mf-shell ${viewportMode === 'mobile' ? 'mf-force-mobile' : viewportMode === 'tablet' ? 'mf-force-tablet' : ''}`}>
      <ChatBot />

      <div className="mf-container">
        {/* ===================================================================
            TOP HEADER BAR (CLAUDE FABLE 5 · MIROFISH INSPIRED HEADER CARD)
            =================================================================== */}
        <header className="mf-card mf-topbar">
          <div className="mf-brand-left" onClick={() => setActiveTab('terminal')} style={{ cursor: 'pointer' }}>
            <div className="mf-orbital-logo" aria-hidden="true">
              <svg viewBox="0 0 38 38" width="38" height="38">
                <circle cx="19" cy="19" r="17" fill="#f8fafc" stroke="#475569" strokeWidth="1.2" />
                <circle cx="19" cy="19" r="2.6" fill="#111827" />
                <circle cx="26" cy="13" r="1.5" fill="#9a3412" />
                <circle cx="12" cy="24" r="1.2" fill="#2563eb" />
              </svg>
            </div>
            <div>
              <div className="mf-brand-eyebrow">
                VANTAGE POINT · 1M/5M SCALPER · FX, METALS, INDICES &amp; CRYPTO
              </div>
              <div className="mf-brand-title">
                MUSE SPARK 1.3 <span className="mf-brand-sep">·</span>{' '}
                <span className="mf-brand-accent">VANTAGE POINT</span>
              </div>
            </div>
          </div>

          {/* View Switcher Pills */}
          <nav className="mf-nav-pills" aria-label="Workspace navigation">
            {[
              { id: 'terminal', label: 'TERMINAL BOARD' },
              { id: 'paper', label: 'PAPER DESK & BOT' },
              { id: 'trading', label: 'AI SCANNER' },
              { id: 'boardroom', label: 'BOARDROOM' },
              { id: 'audit', label: 'AUDIT TRAIL' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`mf-nav-pill ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id as any)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Right Status, Device View Switcher & Pair Controls */}
          <div className="mf-topbar-right">
            <div className="mf-device-switcher" role="group" aria-label="Device layout mode">
              <button
                type="button"
                className={`mf-device-btn ${viewportMode === 'auto' ? 'active' : ''}`}
                onClick={() => setViewportMode('auto')}
                title="Auto responsive layout (Desktop / Tablet / Mobile)"
              >
                <Monitor size={12} /> <span>AUTO</span>
              </button>
              <button
                type="button"
                className={`mf-device-btn ${viewportMode === 'tablet' ? 'active' : ''}`}
                onClick={() => setViewportMode('tablet')}
                title="Tablet layout (820px)"
              >
                <Tablet size={12} /> <span>TABLET</span>
              </button>
              <button
                type="button"
                className={`mf-device-btn ${viewportMode === 'mobile' ? 'active' : ''}`}
                onClick={() => setViewportMode('mobile')}
                title="Mobile layout (412px)"
              >
                <Smartphone size={12} /> <span>MOBILE</span>
              </button>
            </div>

            <div className="mf-pair-control" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <select
                value={ALL_TRADING_PAIRS.includes(pair) ? pair : 'CUSTOM'}
                onChange={(e) => {
                  if (e.target.value !== 'CUSTOM') setPair(e.target.value);
                }}
                className="mf-pair-input"
                style={{ width: '132px', cursor: 'pointer' }}
                aria-label="Select Forex, Metals, Indices, or Crypto pair"
              >
                <optgroup label="Metals (Gold / Silver / Platinum / Copper)">
                  {METAL_PAIRS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </optgroup>
                <optgroup label="Forex Pairs">
                  {FOREX_PAIRS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </optgroup>
                <optgroup label="Global Indices (S&P / Nasdaq / Dow / DAX)">
                  {INDEX_PAIRS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </optgroup>
                <optgroup label="Crypto Pairs">
                  {CRYPTO_PAIRS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </optgroup>
              </select>
            </div>

            {paperEquity !== null && (
              <button
                type="button"
                onClick={() => setActiveTab('paper')}
                className="mf-status-round"
                style={{
                  cursor: 'pointer',
                  borderColor: paperPnl >= 0 ? '#a7f3d0' : '#fed7aa',
                  background: paperPnl >= 0 ? '#ecfdf5' : '#fff7ed',
                  color: paperPnl >= 0 ? '#065f46' : '#9a3412',
                }}
                title="Open Paper Bot Portfolio"
              >
                BOT ${paperEquity.toFixed(2)} ({paperPnl >= 0 ? '+' : ''}${paperPnl.toFixed(2)})
              </button>
            )}

            <span className="mf-status-live mf-hide-xs">
              <i /> LIVE · 1M/5M SCALP
            </span>
            <span className="mf-status-round mf-hide-sm">ROUND #{totalRounds || 1}</span>
            <span className="mf-status-clock mf-hide-xs">{utcClock}</span>
          </div>
        </header>

        {scanBanner && (
          <div className={`mf-banner ${scanBanner.type === 'ok' ? 'ok' : 'err'}`} role="status">
            <span>{scanBanner.text}</span>
            <button type="button" onClick={() => setScanBanner(null)} className="mf-banner-close">
              ×
            </button>
          </div>
        )}

        {/* ===================================================================
            MAIN VIEWPORT
            =================================================================== */}
        <main className="mf-main">
          {activeTab === 'terminal' && (
            <MirofishTerminal
              status={status}
              deliberations={deliberations}
              pair={pair}
              onPairChange={setPair}
              scanning={scanning}
              onRunScan={handleRunScan}
              lastScanDecision={lastScanDecision}
              onOpenTab={(tab) => setActiveTab(tab as any)}
            />
          )}
          {activeTab === 'paper' && <PaperTrading />}
          {activeTab === 'trading' && <TradingView />}
          {activeTab === 'boardroom' && (
            <Boardroom
              deliberations={deliberations}
              loading={boardroomLoading}
              onRefresh={() => void fetchBoardroom()}
            />
          )}
          {activeTab === 'audit' && <AuditLog />}
        </main>

        {/* ===================================================================
            BOTTOM FOOTER STATUS STRIP
            =================================================================== */}
        <footer className="mf-card mf-footer-bar">
          <div className="mf-footer-left">
            <span className="mf-footer-online">
              <i /> AGENT ONLINE
            </span>
            <span>MODEL: MUSE-SPARK-1.3</span>
            <span>MARKETS: 12 FX · 4 METALS · 6 INDICES · 10 CRYPTO</span>
            <span>RISK POLICY: {(status?.risk_policy_status || 'CONFIGURED').toUpperCase()}</span>
            <span className="mf-footer-blue">MODE: PAPER &amp; RESEARCH</span>
          </div>
          <div className="mf-footer-right">
            STACK: VANTAGE-POINT · META-AI · KRAKEN FX
          </div>
        </footer>
      </div>

      {/* ===================================================================
          MOBILE & TABLET BOTTOM APP NAVIGATION BAR
          =================================================================== */}
      <nav className="mf-mobile-bottom-nav" aria-label="Mobile workspace navigation">
        {[
          { id: 'terminal', label: 'Terminal', icon: LayoutDashboard },
          { id: 'paper', label: 'Paper Bot', icon: Bot },
          { id: 'trading', label: 'Scanner', icon: Activity },
          { id: 'boardroom', label: 'Boardroom', icon: Users },
          { id: 'audit', label: 'Audit', icon: Shield },
        ].map((item) => {
          const IconComp = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`mf-mobile-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id as any)}
            >
              <IconComp size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default App;
