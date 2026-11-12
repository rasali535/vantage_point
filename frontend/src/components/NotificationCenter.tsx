import React, { useEffect, useState, useCallback } from 'react';
import { BellRing, Send, CheckCircle, Smartphone, Globe, X, Settings } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface AppNotification {
  id: string;
  title: string;
  body: string;
  type: 'buy' | 'profit' | 'stop' | 'test';
  pair?: string;
  side?: string;
  price?: string;
  realized_pnl_usd?: string;
  timestamp: string;
}

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ isOpen, onClose }) => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [perm, setPerm] = useState<NotificationPermission>(typeof window !== 'undefined' && 'Notification' in window ? Notification.permission : 'default');
  const [settings, setSettings] = useState<{ telegram_configured: boolean; telegram_chat_id: string; webhook_url: string }>({
    telegram_configured: false,
    telegram_chat_id: '',
    webhook_url: '',
  });
  const [showConfig, setShowConfig] = useState(false);
  const [tgToken, setTgToken] = useState('');
  const [tgChatId, setTgChatId] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState('');

  const fetchNotifs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/notifications?limit=30`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(Array.isArray(data) ? data : []);
      }
    } catch {
      // silent
    }
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/notifications/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        if (data.telegram_chat_id) setTgChatId(data.telegram_chat_id);
        if (data.webhook_url) setWebhookUrl(data.webhook_url);
      }
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      void fetchNotifs();
      void fetchSettings();
    }
  }, [isOpen, fetchNotifs, fetchSettings]);

  const requestBrowserPermission = async () => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      alert('This browser does not support Web Notifications.');
      return;
    }
    try {
      const result = await Notification.requestPermission();
      setPerm(result);
      if (result === 'granted') {
        new Notification('⚡ Vantage Point Alerts Enabled', {
          body: 'You will now receive instant scalp trade notifications on your device.',
          icon: '/favicon.svg',
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/notifications/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telegram_bot_token: tgToken || undefined,
          telegram_chat_id: tgChatId || undefined,
          webhook_url: webhookUrl || undefined,
        }),
      });
      if (res.ok) {
        setMsg('Push notification channels saved successfully!');
        void fetchSettings();
        setTgToken('');
      } else {
        setMsg('Failed to save notification settings.');
      }
    } catch {
      setMsg('Network error saving settings.');
    } finally {
      setSaving(false);
    }
  };

  const sendTest = async () => {
    setTesting(true);
    setMsg('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/trading/notifications/test`, { method: 'POST' });
      if (res.ok) {
        setMsg('Test alert dispatched to Telegram, Webhook & database!');
        void fetchNotifs();
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('⚡ Test Scalp Notification', {
            body: 'Autonomous scalper alerts are connected. Scalp buys, exits & profits will notify you here.',
            icon: '/favicon.svg',
          });
        }
      }
    } catch {
      setMsg('Failed to dispatch test alert.');
    } finally {
      setTesting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="mf-modal-overlay" onClick={onClose}>
      <div className="mf-modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="mf-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BellRing size={18} color="#2563eb" />
            <span style={{ fontWeight: 800, fontSize: '0.98rem', fontFamily: 'var(--font-mono)' }}>
              LIVE TRADE NOTIFICATIONS &amp; PUSH ALERTS
            </span>
          </div>
          <button type="button" onClick={onClose} className="mf-pager-btn" style={{ width: '28px', height: '28px' }}>
            <X size={16} />
          </button>
        </div>

        {/* Content Body */}
        <div className="mf-modal-body">
          {/* Channel Cards */}
          <div className="mf-channel-cards">
            {/* Browser Push Card */}
            <div className="mf-subcard" style={{ padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <Globe size={18} color="#059669" />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.84rem' }}>Phone &amp; Browser Push</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Desktop &amp; Mobile Web Notifications
                    </div>
                  </div>
                </div>
                {perm === 'granted' ? (
                  <span className="mf-badge-blue" style={{ background: '#ecfdf5', color: '#059669' }}>
                    <CheckCircle size={11} style={{ marginRight: 3, verticalAlign: -1 }} /> ACTIVE
                  </span>
                ) : (
                  <button type="button" onClick={requestBrowserPermission} className="mf-pill-action" style={{ background: '#2563eb', color: '#fff' }}>
                    ENABLE PUSH
                  </button>
                )}
              </div>
            </div>

            {/* Telegram / Phone Lock Screen Card */}
            <div className="mf-subcard" style={{ padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <Smartphone size={18} color="#2563eb" />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.84rem' }}>Telegram Phone Lock Screen</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Alerts sent when app is closed
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowConfig(!showConfig)}
                  className="mf-pill-action"
                  style={settings.telegram_configured ? { background: '#ecfdf5', color: '#059669', borderColor: '#a7f3d0' } : undefined}
                >
                  <Settings size={11} style={{ marginRight: 3, verticalAlign: -1 }} />
                  {settings.telegram_configured ? 'CONFIGURED' : 'CONNECT'}
                </button>
              </div>
            </div>
          </div>

          {/* Telegram / Webhook Config Accordion */}
          {showConfig && (
            <form onSubmit={saveSettings} className="mf-subcard" style={{ padding: '14px', background: '#f8fafc', marginTop: '10px' }}>
              <div className="mf-micro-label" style={{ marginBottom: '8px' }}>
                CONFIGURE TELEGRAM BOT &amp; WEBHOOK (WORKS WITH APP CLOSED)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                    TELEGRAM BOT TOKEN (From @BotFather)
                  </label>
                  <input
                    type="password"
                    placeholder="e.g. 123456789:ABCdefGHIjk_lmn"
                    value={tgToken}
                    onChange={(e) => setTgToken(e.target.value)}
                    className="pb-input"
                    style={{ fontSize: '0.8rem', padding: '6px 10px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                    TELEGRAM CHAT ID (Your Telegram User or Group ID)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 987654321"
                    value={tgChatId}
                    onChange={(e) => setTgChatId(e.target.value)}
                    className="pb-input"
                    style={{ fontSize: '0.8rem', padding: '6px 10px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.74rem', fontWeight: 700, color: '#334155', marginBottom: '3px' }}>
                    DISCORD / SLACK / CUSTOM WEBHOOK URL (Optional)
                  </label>
                  <input
                    type="url"
                    placeholder="https://discord.com/api/webhooks/..."
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="pb-input"
                    style={{ fontSize: '0.8rem', padding: '6px 10px' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <button type="submit" disabled={saving} className="mf-pill-action" style={{ background: '#111827', color: '#fff', padding: '6px 14px' }}>
                    {saving ? 'SAVING…' : 'SAVE CHANNELS'}
                  </button>
                  <button type="button" disabled={testing} onClick={sendTest} className="mf-pill-action" style={{ padding: '6px 12px' }}>
                    <Send size={11} style={{ marginRight: 4, verticalAlign: -1 }} /> {testing ? 'TESTING…' : 'SEND TEST ALERT'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {msg && (
            <div style={{ marginTop: '10px', padding: '8px 12px', background: '#ecfdf5', color: '#065f46', borderRadius: '6px', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
              {msg}
            </div>
          )}

          {/* Live Notification Feed */}
          <div style={{ marginTop: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span className="mf-micro-header" style={{ margin: 0 }}>
                RECENT SCALP ALERTS &amp; BOT EXECUTIONS ({notifications.length})
              </span>
              <button type="button" onClick={fetchNotifs} className="mf-pill-action" style={{ fontSize: '0.68rem', padding: '2px 7px' }}>
                REFRESH
              </button>
            </div>

            {notifications.length === 0 ? (
              <div className="mf-mono-muted" style={{ padding: '24px 0', textAlign: 'center' }}>
                No scalp notifications recorded yet. The bot will automatically notify you on new BUY entries and profit harvests!
              </div>
            ) : (
              <div className="mf-notif-list">
                {notifications.map((n) => {
                  const isProfit = n.type === 'profit';
                  const isBuy = n.type === 'buy';
                  return (
                    <div
                      key={n.id}
                      className="mf-subcard mf-notif-item"
                      style={{
                        borderLeft: isProfit ? '3px solid #059669' : isBuy ? '3px solid #2563eb' : '3px solid #9a3412',
                        padding: '10px 12px',
                        marginBottom: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '8px' }}>
                        <div style={{ fontWeight: 800, fontSize: '0.84rem', color: '#111827' }}>{n.title}</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                          {n.timestamp ? new Date(n.timestamp).toLocaleTimeString() : ''}
                        </div>
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#334155', marginTop: '4px', lineHeight: 1.45 }}>
                        {n.body}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
