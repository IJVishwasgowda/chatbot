import React, { useState, useRef, useEffect } from 'react';
import { Send, Smile, Paperclip, AlertTriangle, RefreshCw } from 'lucide-react';

const COMMON_EMOJIS = ['👋', '🌤️', '💡', '📊', '✅', '❤️', '👍', '🙏', '⚡', '🚀'];

export function MessageInput({
  onSendMessage,
  isSending,
  isConnected,
  onReconnect,
}) {
  const [text, setText] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const textareaRef = useRef(null);

  // Auto-resize textarea height up to 140px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollH = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollH, 140)}px`;
    }
  }, [text]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!text.trim() || isSending || !isConnected) return;
    onSendMessage(text);
    setText('');
    setShowEmojiPicker(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const addEmoji = (emoji) => {
    setText((prev) => prev + emoji);
    setShowEmojiPicker(false);
    textareaRef.current?.focus();
  };

  const isButtonDisabled = !text.trim() || isSending || !isConnected;

  return (
    <div className="wa-composer-wrapper">
      {/* Backend Disconnected Warning Strip */}
      {!isConnected && (
        <div className="wa-connection-warning">
          <AlertTriangle size={15} />
          <span>Backend is unreachable. Messages cannot be sent right now.</span>
          <button
            type="button"
            className="wa-reconnect-btn"
            onClick={onReconnect}
          >
            <RefreshCw size={12} />
            <span>Reconnect</span>
          </button>
        </div>
      )}

      {/* Quick Emoji Bar (Popup) */}
      {showEmojiPicker && (
        <div className="wa-emoji-picker-bar">
          {COMMON_EMOJIS.map((emoji) => (
            <button
              key={emoji}
              type="button"
              className="wa-emoji-btn"
              onClick={() => addEmoji(emoji)}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}

      <div className="wa-composer">
        {/* Emoji Toggle Button */}
        <button
          type="button"
          className={`wa-composer-icon-btn ${showEmojiPicker ? 'active' : ''}`}
          onClick={() => setShowEmojiPicker((prev) => !prev)}
          title="Insert Emoji"
          aria-label="Insert Emoji"
        >
          <Smile size={22} />
        </button>

        {/* Attachment Button */}
        <button
          type="button"
          className="wa-composer-icon-btn"
          title="Attach Media (Simulated)"
          aria-label="Attach File"
          onClick={() => {
            setText((prev) => (prev ? `${prev} [Attached File]` : '[Attached File] '));
          }}
        >
          <Paperclip size={20} />
        </button>

        {/* Multiline Message Textarea */}
        <div className="wa-input-container">
          <textarea
            ref={textareaRef}
            className="wa-composer-textarea"
            placeholder={
              !isConnected
                ? 'Backend unavailable...'
                : isSending
                ? 'AI is responding...'
                : 'Type a message... (Shift+Enter for new line)'
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isConnected}
            rows={1}
          />
        </div>

        {/* Send Button */}
        <button
          type="button"
          className={`wa-send-btn ${!isButtonDisabled ? 'ready' : ''}`}
          onClick={handleSend}
          disabled={isButtonDisabled}
          title={
            !isConnected
              ? 'Backend offline'
              : isSending
              ? 'Waiting for AI response'
              : 'Send message (Enter)'
          }
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
