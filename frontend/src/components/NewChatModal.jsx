import React, { useState } from 'react';
import { X, UserPlus, Phone, Sparkles } from 'lucide-react';

export function NewChatModal({ isOpen, onClose, onStartChat, existingSenders = [] }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const clean = phoneNumber.replace(/[^0-9+]/g, '').trim();
    if (!clean || clean.length < 3) {
      setError('Please enter a valid phone number or sender ID (min 3 digits)');
      return;
    }
    setError('');
    onStartChat(clean);
    setPhoneNumber('');
    onClose();
  };

  const handleSelectPreset = (num) => {
    setPhoneNumber(num);
    setError('');
  };

  return (
    <div className="wa-modal-overlay">
      <div className="wa-modal-card wa-new-chat-card">
        <div className="wa-modal-header">
          <div className="wa-modal-title-wrap">
            <div className="wa-modal-icon-circle">
              <UserPlus size={18} className="text-wa-green" />
            </div>
            <h3>New Chat</h3>
          </div>
          <button
            type="button"
            className="wa-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="wa-modal-body">
            <p className="wa-modal-instruction">
              Enter a recipient's phone number or sender ID to start a direct
              conversation with the WhatsApp AI assistant.
            </p>

            <div className="wa-form-group">
              <label htmlFor="phoneNumberInput">Phone Number / Sender ID</label>
              <div className="wa-input-with-icon">
                <Phone size={16} className="wa-field-icon" />
                <input
                  id="phoneNumberInput"
                  type="text"
                  className={`wa-form-input ${error ? 'has-error' : ''}`}
                  placeholder="e.g. 15554445555 or +1 (555) 444-5555"
                  value={phoneNumber}
                  onChange={(e) => {
                    setPhoneNumber(e.target.value);
                    if (error) setError('');
                  }}
                  autoFocus
                />
              </div>
              {error && <span className="wa-form-error">{error}</span>}
            </div>

            {/* Quick Presets */}
            <div className="wa-presets-section">
              <span className="wa-presets-label">
                <Sparkles size={13} />
                <span>Quick Contacts:</span>
              </span>
              <div className="wa-presets-list">
                {existingSenders && existingSenders.length > 0 ? (
                  existingSenders.slice(0, 4).map((sender) => (
                    <button
                      key={sender}
                      type="button"
                      className="wa-chip-btn"
                      onClick={() => handleSelectPreset(sender)}
                    >
                      {sender}
                    </button>
                  ))
                ) : (
                  <>
                    <button
                      type="button"
                      className="wa-chip-btn"
                      onClick={() => handleSelectPreset('15554445555')}
                    >
                      15554445555 (Demo User)
                    </button>
                    <button
                      type="button"
                      className="wa-chip-btn"
                      onClick={() => handleSelectPreset('18005550199')}
                    >
                      18005550199 (Support Desk)
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="wa-modal-actions">
            <button
              type="button"
              className="wa-btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="wa-btn-primary"
              disabled={!phoneNumber.trim()}
            >
              Start Chat
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
