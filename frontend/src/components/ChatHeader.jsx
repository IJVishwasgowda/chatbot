import React, { useState } from 'react';
import {
  ArrowLeft,
  MoreVertical,
  Star,
  Trash2,
  Info,
} from 'lucide-react';
import { formatPhoneNumber, getAvatarColor, getInitials } from '../utils/formatters';

export function ChatHeader({
  senderId,
  isTyping,
  isConnected,
  isFavorite,
  onToggleFavorite,
  onClearHistory,
  onBack,
  onOpenInfo,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [showConfirmClear, setShowConfirmClear] = useState(false);

  const formattedName = senderId ? formatPhoneNumber(senderId) : '';
  const avatarColor = senderId ? getAvatarColor(senderId) : '#00a884';
  const initials = senderId ? getInitials(senderId) : 'AI';

  const handleClear = () => {
    setShowConfirmClear(false);
    setShowMenu(false);
    onClearHistory();
  };

  return (
    <header className="wa-chat-header">
      <div className="wa-header-left">
        {/* Mobile Back Button */}
        {onBack && (
          <button
            type="button"
            className="wa-header-back-btn"
            onClick={onBack}
            aria-label="Back to conversations"
          >
            <ArrowLeft size={20} />
          </button>
        )}

        {/* Contact Avatar */}
        <div
          className="wa-header-avatar"
          style={{ backgroundColor: avatarColor }}
          onClick={onOpenInfo}
          title="View info"
        >
          <span>{initials}</span>
          {isConnected && <span className="wa-avatar-online-dot"></span>}
        </div>

        {/* Contact Details */}
        <div className="wa-header-info" onClick={onOpenInfo}>
          <div className="wa-header-name-row">
            <h2 className="wa-header-name">{formattedName}</h2>
            {isFavorite && (
              <Star size={13} className="text-wa-gold fill-wa-gold" />
            )}
          </div>
          <span className="wa-header-status">
            {isTyping ? (
              <span className="text-wa-green font-medium">typing...</span>
            ) : isConnected ? (
              <span className="text-muted">
                <span className="inline-dot online"></span> online • Google Antigravity
              </span>
            ) : (
              <span className="text-danger">
                <span className="inline-dot offline"></span> backend offline
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Header Actions */}
      <div className="wa-header-right">
        {/* Favorite toggle */}
        <button
          type="button"
          className={`wa-icon-action-btn ${isFavorite ? 'active-star' : ''}`}
          onClick={onToggleFavorite}
          title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          aria-label="Toggle favorite"
        >
          <Star size={18} className={isFavorite ? 'fill-wa-gold text-wa-gold' : ''} />
        </button>

        {/* More Menu Dropdown */}
        <div className="wa-menu-container">
          <button
            type="button"
            className="wa-icon-action-btn"
            onClick={() => setShowMenu((prev) => !prev)}
            title="Menu"
            aria-label="Chat options"
          >
            <MoreVertical size={19} />
          </button>

          {showMenu && (
            <>
              <div
                className="wa-menu-backdrop"
                onClick={() => setShowMenu(false)}
              />
              <div className="wa-dropdown-menu">
                <button
                  type="button"
                  className="wa-menu-item"
                  onClick={() => {
                    setShowMenu(false);
                    if (onOpenInfo) {
                      onOpenInfo();
                    }
                  }}
                >
                  <Info size={16} />
                  <span>Contact info</span>
                </button>
                <button
                  type="button"
                  className="wa-menu-item text-danger"
                  onClick={() => {
                    setShowConfirmClear(true);
                    setShowMenu(false);
                  }}
                >
                  <Trash2 size={16} />
                  <span>Clear messages</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Clear Confirmation Modal */}
      {showConfirmClear && (
        <div className="wa-modal-overlay">
          <div className="wa-modal-card">
            <h3>Clear chat messages?</h3>
            <p>
              Are you sure you want to clear all conversation history for{' '}
              <strong>{formattedName}</strong>? This will permanently delete messages from SQLite.
            </p>
            <div className="wa-modal-actions">
              <button
                type="button"
                className="wa-btn-secondary"
                onClick={() => setShowConfirmClear(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="wa-btn-danger"
                onClick={handleClear}
              >
                Clear Messages
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
