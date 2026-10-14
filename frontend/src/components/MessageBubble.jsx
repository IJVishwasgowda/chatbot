import React, { useState } from 'react';
import { CheckCheck, Clock, AlertCircle, Copy, Bot, User } from 'lucide-react';
import { formatMessageTime } from '../utils/formatters';
import { renderFormattedText } from '../utils/textParser';

export function MessageBubble({ message, onRetry }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isFailed = message.status === 'failed';
  const isSending = message.status === 'sending';

  const handleCopy = () => {
    if (message.content) {
      navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <div className={`wa-bubble-wrapper ${isUser ? 'wa-outgoing-wrapper' : 'wa-incoming-wrapper'}`}>
      {/* Role Avatar Badge (subtle on mobile, helpful for distinguishing AI vs user) */}
      <div className={`wa-bubble-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>

      <div
        className={`wa-bubble ${isUser ? 'wa-bubble-outgoing' : 'wa-bubble-incoming'} ${
          isFailed ? 'wa-bubble-error' : ''
        }`}
      >
        {/* Optional Media badge */}
        {message.media_type && message.media_type !== 'text' && (
          <div className="wa-media-badge">
            <span className="wa-media-tag">{message.media_type.toUpperCase()}</span>
          </div>
        )}

        {/* Message Content */}
        <div className="wa-bubble-text">
          {renderFormattedText(message.content)}
        </div>

        {/* Message Footer: Timestamp + Status ticks + Action */}
        <div className="wa-bubble-meta">
          {/* Quick Copy button */}
          <button
            type="button"
            className="wa-bubble-action-btn"
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy text'}
            aria-label="Copy message"
          >
            <Copy size={11} className={copied ? 'text-green' : ''} />
          </button>

          <span className="wa-bubble-time">
            {formatMessageTime(message.created_at)}
          </span>

          {isUser && (
            <span className="wa-bubble-status">
              {isSending ? (
                <Clock size={12} className="wa-status-clock" />
              ) : isFailed ? (
                <button
                  type="button"
                  className="wa-retry-btn"
                  onClick={() => onRetry && onRetry(message)}
                  title="Failed to send. Click to retry."
                >
                  <AlertCircle size={13} className="text-danger" />
                  <span className="wa-retry-text">Retry</span>
                </button>
              ) : (
                <CheckCheck size={14} className="wa-status-checks-read" />
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
