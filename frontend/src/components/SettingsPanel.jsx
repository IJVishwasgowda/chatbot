import React, { useState } from 'react';
import {
  X,
  Settings,
  Server,
  Database,
  Cpu,
  Moon,
  Sun,
  Shield,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { getBaseUrl, setCustomBaseUrl } from '../api/client';

export function SettingsPanel({
  isOpen,
  onClose,
  backendHealth,
  isConnected,
  onRefreshHealth,
  darkMode,
  onToggleDarkMode,
}) {
  const [apiUrl, setApiUrl] = useState(getBaseUrl());
  const [saveSuccess, setSaveSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSaveApiUrl = (e) => {
    e.preventDefault();
    setCustomBaseUrl(apiUrl);
    setSaveSuccess(true);
    onRefreshHealth();
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  const handleResetApiUrl = () => {
    setCustomBaseUrl(null);
    setApiUrl(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000');
    onRefreshHealth();
  };

  const storage = backendHealth?.storage || {};
  const settings = backendHealth?.settings || {};
  const queue = backendHealth?.queue || {};

  return (
    <div className="wa-modal-overlay">
      <div className="wa-modal-card wa-settings-card">
        {/* Modal Header */}
        <div className="wa-modal-header">
          <div className="wa-modal-title-wrap">
            <div className="wa-modal-icon-circle">
              <Settings size={18} className="text-wa-green" />
            </div>
            <h3>Settings & Diagnostics</h3>
          </div>
          <button
            type="button"
            className="wa-modal-close-btn"
            onClick={onClose}
            aria-label="Close settings"
          >
            <X size={18} />
          </button>
        </div>

        <div className="wa-modal-body wa-settings-body">
          {/* Section: Profile */}
          <div className="wa-settings-section">
            <div className="wa-profile-card">
              <div className="wa-profile-avatar">
                <Shield size={28} className="text-white" />
              </div>
              <div className="wa-profile-details">
                <h4 className="wa-profile-name">WhatsApp AI Web Assistant</h4>
                <p className="wa-profile-sub">
                  Powered by Google Antigravity & Meta Cloud API
                </p>
                <div className="wa-profile-pill">
                  <span className={`wa-status-dot ${isConnected ? 'online' : 'offline'}`} />
                  <span>{isConnected ? 'Backend Operational' : 'Backend Disconnected'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section: Theme */}
          <div className="wa-settings-section">
            <h4 className="wa-section-title">Appearance</h4>
            <div className="wa-setting-row">
              <div className="wa-setting-meta">
                <span className="wa-setting-label">Dark Theme</span>
                <span className="wa-setting-desc">
                  Toggle dark and light color palette
                </span>
              </div>
              <button
                type="button"
                className={`wa-toggle-switch ${darkMode ? 'active' : ''}`}
                onClick={onToggleDarkMode}
                aria-label="Toggle dark mode"
              >
                <span className="wa-toggle-thumb">
                  {darkMode ? <Moon size={12} /> : <Sun size={12} />}
                </span>
              </button>
            </div>
          </div>

          {/* Section: Backend Configuration */}
          <div className="wa-settings-section">
            <h4 className="wa-section-title">API Connection</h4>
            <form onSubmit={handleSaveApiUrl} className="wa-api-form">
              <div className="wa-form-group">
                <label htmlFor="apiBaseUrl">FastAPI Backend URL</label>
                <div className="wa-input-button-group">
                  <input
                    id="apiBaseUrl"
                    type="url"
                    className="wa-form-input"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    placeholder="http://127.0.0.1:8000"
                  />
                  <button
                    type="submit"
                    className="wa-btn-primary"
                    disabled={!apiUrl.trim()}
                  >
                    Apply
                  </button>
                </div>
              </div>
              <div className="wa-api-form-links">
                <button
                  type="button"
                  className="wa-link-btn"
                  onClick={handleResetApiUrl}
                >
                  Reset to default (http://127.0.0.1:8000)
                </button>
                {saveSuccess && (
                  <span className="text-wa-green text-sm flex items-center gap-1">
                    <CheckCircle2 size={13} /> Saved!
                  </span>
                )}
              </div>
            </form>
          </div>

          {/* Section: System Diagnostics */}
          <div className="wa-settings-section">
            <div className="wa-section-header-row">
              <h4 className="wa-section-title">System Diagnostics</h4>
              <button
                type="button"
                className="wa-link-btn flex items-center gap-1"
                onClick={onRefreshHealth}
              >
                <RefreshCw size={12} />
                <span>Refresh</span>
              </button>
            </div>

            <div className="wa-diagnostic-grid">
              <div className="wa-diag-item">
                <div className="wa-diag-icon">
                  <Cpu size={16} />
                </div>
                <div className="wa-diag-info">
                  <span className="wa-diag-key">AI Model</span>
                  <span className="wa-diag-val">
                    {settings.agent_model || 'gemini-2.5-flash'}
                  </span>
                </div>
              </div>

              <div className="wa-diag-item">
                <div className="wa-diag-icon">
                  <Server size={16} />
                </div>
                <div className="wa-diag-info">
                  <span className="wa-diag-key">Active Provider</span>
                  <span className="wa-diag-val capitalize">
                    {settings.messaging_provider || 'whatsapp'}
                  </span>
                </div>
              </div>

              <div className="wa-diag-item">
                <div className="wa-diag-icon">
                  <Database size={16} />
                </div>
                <div className="wa-diag-info">
                  <span className="wa-diag-key">SQLite Messages</span>
                  <span className="wa-diag-val">
                    {storage.total_messages ?? '—'}
                  </span>
                </div>
              </div>

              <div className="wa-diag-item">
                <div className="wa-diag-icon">
                  <Database size={16} />
                </div>
                <div className="wa-diag-info">
                  <span className="wa-diag-key">Distinct Contacts</span>
                  <span className="wa-diag-val">
                    {storage.distinct_users ?? '—'}
                  </span>
                </div>
              </div>

              <div className="wa-diag-item">
                <div className="wa-diag-icon">
                  <Layers size={16} />
                </div>
                <div className="wa-diag-info">
                  <span className="wa-diag-key">Queue Workers</span>
                  <span className="wa-diag-val">
                    {queue.active_workers ?? 4} active
                  </span>
                </div>
              </div>
            </div>

            {/* Credential Status Checks (Safe boolean, no secrets leaked) */}
            <div className="wa-credential-checks">
              <div className="wa-cred-item">
                <span className="wa-cred-name">Gemini API Key</span>
                {settings.gemini_configured || settings.antigravity_configured ? (
                  <span className="wa-cred-badge success">
                    <CheckCircle2 size={12} /> Configured
                  </span>
                ) : (
                  <span className="wa-cred-badge fallback">
                    <AlertCircle size={12} /> Not Configured
                  </span>
                )}
              </div>

              <div className="wa-cred-item">
                <span className="wa-cred-name">WhatsApp Cloud API</span>
                {settings.whatsapp_configured ? (
                  <span className="wa-cred-badge success">
                    <CheckCircle2 size={12} /> Configured
                  </span>
                ) : (
                  <span className="wa-cred-badge fallback">
                    <AlertCircle size={12} /> Web Direct / Mock Mode
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="wa-modal-actions">
          <button
            type="button"
            className="wa-btn-primary"
            onClick={onClose}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
