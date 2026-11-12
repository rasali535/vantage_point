import React, { useState, useEffect } from 'react';
import {
  Key,
  Globe,
  Download,
  Check,
  AlertCircle,
  Copy,
  Power,
  X,
  Shield,
  Zap,
  Server,
  Eye,
  EyeOff,
  RefreshCw,
} from 'lucide-react';

interface BrokerConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl: string;
  onBrokerChanged?: () => void;
}

export interface BrokerStatus {
  mode: 'paper' | 'api_key' | 'meta_trader';
  connected: boolean;
  provider: string;
  label: string;
  masked_key?: string;
  live_orders_enabled?: boolean;
  last_tested_at?: string;
  details?: {
    exchange?: string;
    platform?: string;
    server?: string;
    login?: string;
    method?: string;
    webhook_url?: string;
    webhook_token?: string;
    currency?: string;
    execution?: string;
    equity?: string;
    withdrawals?: string;
    connected_at?: string;
  };
}

const SUPPORTED_EXCHANGES = [
  { id: 'kraken', name: 'Kraken', category: 'Crypto / FX Spot', hasPassphrase: false },
  { id: 'binance', name: 'Binance', category: 'Crypto Spot & Futures', hasPassphrase: false },
  { id: 'bybit', name: 'Bybit', category: 'Crypto Spot & Derivatives', hasPassphrase: false },
  { id: 'coinbase', name: 'Coinbase Advanced', category: 'Crypto Spot', hasPassphrase: true },
  { id: 'alpaca', name: 'Alpaca', category: 'US Stocks & Crypto', hasPassphrase: false },
  { id: 'custom', name: 'Custom CCXT Exchange', category: 'Any Supported Exchange', hasPassphrase: true },
];

const POPULAR_MT_SERVERS = [
  'ICMarketsSC-Live01',
  'ICMarkets-Live02',
  'Exness-Real10',
  'Exness-Real12',
  'Pepperstone-Live01',
  'VantageFX-Live',
  'XMGlobal-Real',
  'FPMarkets-Live',
];

export const BrokerConnectionModal: React.FC<BrokerConnectionModalProps> = ({
  isOpen,
  onClose,
  apiBaseUrl,
  onBrokerChanged,
}) => {
  const [activeTab, setActiveTab] = useState<'api_key' | 'meta_trader'>('api_key');
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string; latency_ms?: number } | null>(null);
  const [testing, setTesting] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // API Key Form
  const [exchange, setExchange] = useState('kraken');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [label, setLabel] = useState('');
  const [liveOrdersEnabled, setLiveOrdersEnabled] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  // MetaTrader Form
  const [mtPlatform, setMtPlatform] = useState<'MT5' | 'MT4'>('MT5');
  const [mtMethod, setMtMethod] = useState<'webhook_ea' | 'cloud'>('webhook_ea');
  const [mtServer, setMtServer] = useState('ICMarketsSC-Live01');
  const [mtLogin, setMtLogin] = useState('');
  const [mtPassword, setMtPassword] = useState('');
  const [mtLiveOrders, setMtLiveOrders] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/status`);
      if (res.ok) {
        const data = await res.json();
        setBrokerStatus(data);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (isOpen) {
      void fetchStatus();
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2200);
  };

  const handleTestApiKey = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'api_key',
          exchange,
          api_key: apiKey,
          api_secret: apiSecret,
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({ status: 'error', message: err.message || 'Connection test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleConnectApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !apiSecret) {
      alert('Please provide both API Key and API Secret.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/connect/api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exchange,
          api_key: apiKey,
          api_secret: apiSecret,
          passphrase: passphrase || undefined,
          label: label || undefined,
          live_orders_enabled: liveOrdersEnabled,
        }),
      });
      if (res.ok) {
        await fetchStatus();
        onBrokerChanged?.();
        alert(`Successfully connected ${exchange.toUpperCase()} broker!`);
      } else {
        const err = await res.json();
        alert(`Connection failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestMetaTrader = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'meta_trader',
          server: mtServer,
          login: mtLogin,
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({ status: 'error', message: err.message || 'MetaTrader test failed.' });
    } finally {
      setTesting(false);
    }
  };

  const handleConnectMetaTrader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mtServer || !mtLogin) {
      alert('Please specify the Broker Server and Account Login number.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/connect/meta-trader`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: mtPlatform,
          method: mtMethod,
          server: mtServer,
          login: mtLogin,
          password: mtPassword || undefined,
          live_orders_enabled: mtLiveOrders,
        }),
      });
      if (res.ok) {
        await fetchStatus();
        onBrokerChanged?.();
        alert(`MetaTrader ${mtPlatform} bridge activated!`);
      } else {
        const err = await res.json();
        alert(`Connection failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Disconnect broker and revert safely to Paper Simulation ($100 Seed)?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/trading/broker/disconnect`, { method: 'POST' });
      if (res.ok) {
        await fetchStatus();
        onBrokerChanged?.();
        alert('Reverted safely to Paper Simulation mode.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadEA = () => {
    window.open(`${apiBaseUrl}/api/trading/broker/download-ea`, '_blank');
  };

  const selectedExch = SUPPORTED_EXCHANGES.find((e) => e.id === exchange);

  return (
    <div className="mf-modal-overlay" onClick={onClose} style={{ zIndex: 9999 }}>
      <div
        className="mf-modal-card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '640px', width: '92%', maxHeight: '90vh', overflowY: 'auto' }}
      >
        {/* Modal Header */}
        <div className="mf-modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={18} style={{ color: '#2563eb' }} />
              <h2 className="mf-modal-title" style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800 }}>
                CONNECT YOUR BROKER
              </h2>
            </div>
            <p className="mf-modal-subtitle" style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#64748b' }}>
              Non-custodial trading · Connect API Keys or MetaTrader 4 / 5 bridges
            </p>
          </div>
          <button type="button" onClick={onClose} className="mf-btn-ghost-sm" style={{ padding: '4px' }}>
            <X size={16} />
          </button>
        </div>

        {/* Current Active Status Pill */}
        <div
          style={{
            margin: '12px 0 16px',
            padding: '10px 14px',
            borderRadius: '8px',
            background: brokerStatus?.mode === 'paper' ? '#f8fafc' : '#ecfdf5',
            border: `1px solid ${brokerStatus?.mode === 'paper' ? '#e2e8f0' : '#a7f3d0'}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: brokerStatus?.mode === 'paper' ? '#64748b' : '#059669',
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: brokerStatus?.mode === 'paper' ? '#334155' : '#065f46' }}>
              {brokerStatus?.label || 'Paper Simulation ($100 Seed)'}
            </span>
            {brokerStatus?.live_orders_enabled && (
              <span className="mf-tag-outline" style={{ color: '#b91c1c', borderColor: '#fca5a5', background: '#fef2f2', fontSize: '0.65rem' }}>
                LIVE ORDERS ACTIVE
              </span>
            )}
          </div>
          {brokerStatus?.mode !== 'paper' && (
            <button
              type="button"
              onClick={handleDisconnect}
              disabled={loading}
              className="mf-btn-ghost-sm"
              style={{ fontSize: '0.72rem', color: '#dc2626', borderColor: '#fca5a5' }}
            >
              <Power size={11} style={{ marginRight: '4px' }} /> Disconnect to Paper
            </button>
          )}
        </div>

        {/* Primary Tabs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
          <button
            type="button"
            className={`mf-nav-pill ${activeTab === 'api_key' ? 'active' : ''}`}
            onClick={() => setActiveTab('api_key')}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '9px 12px' }}
          >
            <Key size={14} />
            <span>CONNECT VIA API KEY</span>
          </button>
          <button
            type="button"
            className={`mf-nav-pill ${activeTab === 'meta_trader' ? 'active' : ''}`}
            onClick={() => setActiveTab('meta_trader')}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '9px 12px' }}
          >
            <Globe size={14} />
            <span>CONNECT VIA MT4 / MT5</span>
          </button>
        </div>

        {/* ============================================================== */}
        {/* TAB 1: CONNECT VIA API KEY (CRYPTO & EXCHANGES)                */}
        {/* ============================================================== */}
        {activeTab === 'api_key' && (
          <form onSubmit={handleConnectApiKey} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.75rem', color: '#475569' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: '#0f172a', marginBottom: '3px' }}>
                <Shield size={13} style={{ color: '#2563eb' }} />
                <span>Non-Custodial &amp; Encrypted Security</span>
              </div>
              Withdrawals are strictly disabled. Your API secret is encrypted at rest using AES-256. Vantage Point never holds or touches your deposits.
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                SELECT BROKER / EXCHANGE
              </label>
              <select
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
                className="mf-pair-input"
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.82rem' }}
              >
                {SUPPORTED_EXCHANGES.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.name} — {ex.category}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                API KEY
              </label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Paste your exchange API Key..."
                className="mf-pair-input"
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.82rem', fontFamily: 'monospace' }}
                required
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={{ fontSize: '0.72rem', fontWeight: 700, color: '#334155', margin: 0 }}>
                  API SECRET
                </label>
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.7rem', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '3px' }}
                >
                  {showSecret ? <EyeOff size={11} /> : <Eye size={11} />}
                  <span>{showSecret ? 'Hide' : 'Show'}</span>
                </button>
              </div>
              <input
                type={showSecret ? 'text' : 'password'}
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Paste your exchange API Secret..."
                className="mf-pair-input"
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.82rem', fontFamily: 'monospace' }}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                ACCOUNT NICKNAME (OPTIONAL)
              </label>
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. My Primary Trading Account"
                className="mf-pair-input"
                style={{ width: '100%', padding: '7px 10px', fontSize: '0.82rem' }}
              />
            </div>

            {selectedExch?.hasPassphrase && (
              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                  PASSPHRASE / API PASSWORD (IF REQUIRED)
                </label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="Optional passphrase..."
                  className="mf-pair-input"
                  style={{ width: '100%', padding: '7px 10px', fontSize: '0.82rem' }}
                />
              </div>
            )}

            <div style={{ padding: '8px 10px', background: '#fff7ed', border: '1px solid #ffedd5', borderRadius: '6px' }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '0.75rem', color: '#9a3412' }}>
                <input
                  type="checkbox"
                  checked={liveOrdersEnabled}
                  onChange={(e) => setLiveOrdersEnabled(e.target.checked)}
                  style={{ marginTop: '2px' }}
                />
                <span>
                  <strong>Authorize Live Order Placement:</strong> Allow the autonomous bot to send real buy/sell orders directly to your {exchange.toUpperCase()} account using conviction-weighted sizing. Leave unchecked for read-only tracking.
                </span>
              </label>
            </div>

            {testResult && (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.76rem',
                  background: testResult.status === 'verified' ? '#ecfdf5' : '#fef2f2',
                  border: `1px solid ${testResult.status === 'verified' ? '#a7f3d0' : '#fca5a5'}`,
                  color: testResult.status === 'verified' ? '#065f46' : '#991b1b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {testResult.status === 'verified' ? <Check size={14} /> : <AlertCircle size={14} />}
                <span>
                  {testResult.message} {testResult.latency_ms ? `(${testResult.latency_ms}ms)` : ''}
                </span>
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              <button
                type="button"
                onClick={handleTestApiKey}
                disabled={testing || !apiKey}
                className="mf-btn-ghost-sm"
                style={{ flex: 1, padding: '8px 12px', justifyContent: 'center' }}
              >
                {testing ? <RefreshCw size={12} className="spin" /> : <Zap size={12} />}
                <span>{testing ? 'Testing...' : 'Test Connection'}</span>
              </button>
              <button
                type="submit"
                disabled={loading || !apiKey}
                className="mf-action-btn run"
                style={{ flex: 2, padding: '8px 12px', justifyContent: 'center' }}
              >
                {loading ? 'Connecting...' : `Save & Connect ${exchange.toUpperCase()}`}
              </button>
            </div>
          </form>
        )}

        {/* ============================================================== */}
        {/* TAB 2: CONNECT VIA METATRADER 4 / 5 (METALS & FOREX)           */}
        {/* ============================================================== */}
        {activeTab === 'meta_trader' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                type="button"
                className={`mf-nav-pill ${mtMethod === 'webhook_ea' ? 'active' : ''}`}
                onClick={() => setMtMethod('webhook_ea')}
                style={{ flex: 1, fontSize: '0.72rem', padding: '6px 8px' }}
              >
                1-CLICK EXPERT ADVISOR (EA)
              </button>
              <button
                type="button"
                className={`mf-nav-pill ${mtMethod === 'cloud' ? 'active' : ''}`}
                onClick={() => setMtMethod('cloud')}
                style={{ flex: 1, fontSize: '0.72rem', padding: '6px 8px' }}
              >
                CLOUD MT5 SERVER SYNC
              </button>
            </div>

            {mtMethod === 'webhook_ea' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ background: '#f0f9ff', padding: '12px', borderRadius: '6px', border: '1px solid #bae6fd', fontSize: '0.76rem', color: '#0369a1' }}>
                  <div style={{ fontWeight: 800, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Download size={13} />
                    <span>Recommended for IC Markets, Pepperstone, Exness, XM &amp; Vantage</span>
                  </div>
                  No password sharing required. Download the pre-configured Expert Advisor, drag it onto your MetaTrader chart, and Vantage Point executes trades automatically!
                </div>

                {/* 1-Click EA Download Card */}
                <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div>
                      <div style={{ fontSize: '0.84rem', fontWeight: 800, color: '#0f172a' }}>
                        VantagePointBridge.mq5
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                        Automated execution bridge for MetaTrader 5 (Gold, Silver, Indices &amp; FX)
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleDownloadEA}
                      className="mf-action-btn run"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '4px' }}
                    >
                      <Download size={12} />
                      <span>Download .mq5</span>
                    </button>
                  </div>

                  <div style={{ marginTop: '10px' }}>
                    <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: '#64748b', marginBottom: '3px' }}>
                      YOUR PRIVATE MT5 WEBHOOK URL
                    </label>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <input
                        type="text"
                        readOnly
                        value={brokerStatus?.details?.webhook_url || `${apiBaseUrl}/api/trading/broker/mt-webhook/poll`}
                        className="mf-pair-input"
                        style={{ flex: 1, padding: '5px 8px', fontSize: '0.72rem', fontFamily: 'monospace', background: '#f8fafc' }}
                      />
                      <button
                        type="button"
                        onClick={() => handleCopy(brokerStatus?.details?.webhook_url || `${apiBaseUrl}/api/trading/broker/mt-webhook/poll`, 'wh_url')}
                        className="mf-btn-ghost-sm"
                        style={{ padding: '4px 8px' }}
                      >
                        {copiedKey === 'wh_url' ? <Check size={12} style={{ color: '#059669' }} /> : <Copy size={12} />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* 3 Step Instruction Guide */}
                <div style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.74rem', fontWeight: 800, color: '#0f172a', marginBottom: '6px' }}>
                    SIMPLE 3-STEP SETUP IN METATRADER:
                  </div>
                  <ol style={{ margin: 0, paddingLeft: '18px', fontSize: '0.73rem', color: '#475569', lineHeight: 1.6 }}>
                    <li>Open MT5 → Click <strong>Tools → Options → Expert Advisors</strong>.</li>
                    <li>Check <strong>"Allow WebRequest for listed URL"</strong> and paste your Webhook URL above.</li>
                    <li>Drag <strong>VantagePointBridge</strong> onto any Gold (`XAUUSD`) or Index chart. Enable AutoTrading!</li>
                  </ol>
                </div>
              </div>
            ) : (
              /* Cloud MetaTrader Form */
              <form onSubmit={handleConnectMetaTrader} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                      PLATFORM
                    </label>
                    <select
                      value={mtPlatform}
                      onChange={(e) => setMtPlatform(e.target.value as any)}
                      className="mf-pair-input"
                      style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                    >
                      <option value="MT5">MetaTrader 5 (Recommended)</option>
                      <option value="MT4">MetaTrader 4</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                      ACCOUNT LOGIN NUMBER
                    </label>
                    <input
                      type="text"
                      value={mtLogin}
                      onChange={(e) => setMtLogin(e.target.value)}
                      placeholder="e.g. 5123456"
                      className="mf-pair-input"
                      style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                    BROKER SERVER NAME
                  </label>
                  <input
                    type="text"
                    list="popular-mt-servers"
                    value={mtServer}
                    onChange={(e) => setMtServer(e.target.value)}
                    placeholder="e.g. ICMarketsSC-Live01 or Exness-Real"
                    className="mf-pair-input"
                    style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                    required
                  />
                  <datalist id="popular-mt-servers">
                    {POPULAR_MT_SERVERS.map((s) => (
                      <option key={s} value={s} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                    TRADE PASSWORD (OR INVESTOR PASSWORD FOR READ-ONLY)
                  </label>
                  <input
                    type="password"
                    value={mtPassword}
                    onChange={(e) => setMtPassword(e.target.value)}
                    placeholder="MetaTrader account password..."
                    className="mf-pair-input"
                    style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                  />
                </div>

                <div style={{ padding: '8px 10px', background: '#fff7ed', border: '1px solid #ffedd5', borderRadius: '6px' }}>
                  <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '0.74rem', color: '#9a3412' }}>
                    <input
                      type="checkbox"
                      checked={mtLiveOrders}
                      onChange={(e) => setMtLiveOrders(e.target.checked)}
                      style={{ marginTop: '2px' }}
                    />
                    <span>
                      <strong>Enable Live Execution:</strong> Dispatch automated orders to this MetaTrader account with dynamic lot sizing.
                    </span>
                  </label>
                </div>

                {testResult && (
                  <div
                    style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      background: testResult.status === 'verified' ? '#ecfdf5' : '#fef2f2',
                      border: `1px solid ${testResult.status === 'verified' ? '#a7f3d0' : '#fca5a5'}`,
                      color: testResult.status === 'verified' ? '#065f46' : '#991b1b',
                    }}
                  >
                    {testResult.message}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <button
                    type="button"
                    onClick={handleTestMetaTrader}
                    disabled={testing || !mtServer}
                    className="mf-btn-ghost-sm"
                    style={{ flex: 1, padding: '8px 12px', justifyContent: 'center' }}
                  >
                    {testing ? <RefreshCw size={12} className="spin" /> : <Zap size={12} />}
                    <span>{testing ? 'Testing...' : 'Test Server'}</span>
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !mtServer || !mtLogin}
                    className="mf-action-btn run"
                    style={{ flex: 2, padding: '8px 12px', justifyContent: 'center' }}
                  >
                    {loading ? 'Connecting...' : `Activate MT${mtPlatform.slice(-1)} Sync`}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
