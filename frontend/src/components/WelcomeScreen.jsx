import React from 'react';
import { Bot, Lock, MessageSquare, Zap, ShieldCheck, CloudSun } from 'lucide-react';

export function WelcomeScreen({ onStartNewChat, backendHealth }) {
  return (
    <div className="wa-welcome-screen">
      <div className="wa-welcome-content">
        <div className="wa-welcome-hero-bubble">
          <div className="wa-welcome-icon-ring">
            <Bot size={54} className="text-wa-green" />
          </div>
        </div>

        <h2 className="wa-welcome-title">WhatsApp AI for Web</h2>
        <p className="wa-welcome-description">
          Seamlessly chat with your AI assistant powered by{' '}
          <strong>Google Antigravity</strong>. All conversations are stored in persistent
          SQLite memory and synced with your WhatsApp backend.
        </p>

        {/* Feature Highlights Grid */}
        <div className="wa-welcome-features">
          <div className="wa-feature-card">
            <CloudSun size={20} className="text-wa-teal" />
            <div className="wa-feature-text">
              <h4>Real-time Weather</h4>
              <p>Ask for live weather and forecast anywhere in the world.</p>
            </div>
          </div>

          <div className="wa-feature-card">
            <Zap size={20} className="text-wa-gold" />
            <div className="wa-feature-text">
              <h4>Knowledge Base & FAQ</h4>
              <p>Instant answers on business hours, returns, and pricing plans.</p>
            </div>
          </div>

          <div className="wa-feature-card">
            <ShieldCheck size={20} className="text-wa-green" />
            <div className="wa-feature-text">
              <h4>Persistent SQLite Memory</h4>
              <p>Maintains multi-turn context across chat sessions and devices.</p>
            </div>
          </div>
        </div>

        <div className="wa-welcome-cta">
          <button
            type="button"
            className="wa-btn-primary wa-btn-large"
            onClick={onStartNewChat}
          >
            <MessageSquare size={18} />
            <span>Start a New Conversation</span>
          </button>
        </div>

        {backendHealth && (
          <div className="wa-welcome-stats-pill">
            <span>Model: <strong>{backendHealth.settings?.agent_model || 'gemini-3.8-flash'}</strong></span>
            <span className="dot-divider">•</span>
            <span>Total Messages: <strong>{backendHealth.storage?.total_messages || 0}</strong></span>
            <span className="dot-divider">•</span>
            <span>Users: <strong>{backendHealth.storage?.distinct_users || 0}</strong></span>
          </div>
        )}

        <div className="wa-welcome-footer">
          <Lock size={12} />
          <span>Encrypted with Google Antigravity & Meta WhatsApp Cloud API standards</span>
        </div>
      </div>
    </div>
  );
}
