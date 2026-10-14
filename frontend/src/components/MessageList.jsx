import React, { useEffect, useRef, useState } from 'react';
import { ArrowDown, Lock, Sparkles } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { formatDateDivider } from '../utils/formatters';

export function MessageList({
  messages,
  isLoading,
  isSending,
  onRetry,
  onSendPreset,
  contactName,
}) {
  const containerRef = useRef(null);
  const bottomRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Auto-scroll to bottom on new messages or when typing state changes
  useEffect(() => {
    if (!showScrollBottom) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isSending, showScrollBottom]);

  // Initial load scroll
  useEffect(() => {
    if (!isLoading) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto' });
    }
  }, [isLoading]);

  // Detect user scroll position
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 180;
    setShowScrollBottom(isUp);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollBottom(false);
  };

  // Group messages by calendar date for date dividers
  const renderGroupedMessages = () => {
    let lastDate = null;

    return messages.map((msg, index) => {
      const msgDate = msg.created_at
        ? new Date(msg.created_at).toDateString()
        : null;
      const showDivider = msgDate && msgDate !== lastDate;
      if (showDivider) {
        lastDate = msgDate;
      }

      return (
        <React.Fragment key={msg.id || index}>
          {showDivider && (
            <div className="wa-date-divider-wrapper">
              <span className="wa-date-divider">
                {formatDateDivider(msg.created_at)}
              </span>
            </div>
          )}
          <MessageBubble message={msg} onRetry={onRetry} />
        </React.Fragment>
      );
    });
  };

  return (
    <div
      className="wa-messages-container"
      ref={containerRef}
      onScroll={handleScroll}
    >
      {/* WhatsApp Security / Info Pill Banner */}
      <div className="wa-encryption-banner">
        <Lock size={12} className="wa-lock-icon" />
        <span>
          Messages are processed with <strong>Google Antigravity AI</strong>. Conversations are stored in local SQLite persistent memory.
        </span>
      </div>

      {isLoading ? (
        <div className="wa-messages-loading">
          <div className="wa-spinner"></div>
          <span>Loading conversation history...</span>
        </div>
      ) : messages.length === 0 ? (
        <div className="wa-messages-empty">
          <div className="wa-empty-icon-wrap">
            <Sparkles size={28} className="text-wa-green" />
          </div>
          <h3>Start a conversation with {contactName || 'WhatsApp AI'}</h3>
          <p>
            Ask questions, inquire about operating hours, check live weather,
            or request service pricing quotes.
          </p>

          <div className="wa-preset-grid">
            <button
              type="button"
              className="wa-preset-pill"
              onClick={() => onSendPreset && onSendPreset('What is the weather in London?')}
            >
              🌤️ What is the weather in London?
            </button>
            <button
              type="button"
              className="wa-preset-pill"
              onClick={() => onSendPreset && onSendPreset('What are your operating hours and return policy?')}
            >
              💡 Operating hours & return policy
            </button>
            <button
              type="button"
              className="wa-preset-pill"
              onClick={() => onSendPreset && onSendPreset('Calculate a service quote for Professional tier with 5 users')}
            >
              📊 Calculate quote for 5 users
            </button>
          </div>
        </div>
      ) : (
        <>
          {renderGroupedMessages()}

          {/* WhatsApp Typing Indicator */}
          {isSending && (
            <div className="wa-bubble-wrapper wa-incoming-wrapper">
              <div className="wa-bubble wa-bubble-incoming wa-typing-bubble">
                <span className="wa-typing-dots">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </span>
                <span className="wa-typing-label">AI is generating response...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} style={{ height: 1 }} />
        </>
      )}

      {/* Floating Scroll-to-Bottom Button */}
      {showScrollBottom && (
        <button
          type="button"
          className="wa-scroll-bottom-btn"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
          title="Scroll to bottom"
        >
          <ArrowDown size={18} />
        </button>
      )}
    </div>
  );
}
