import React from 'react';
import { MessageSquare, Star, CheckCheck, UserPlus } from 'lucide-react';
import {
  formatConversationTime,
  formatPhoneNumber,
  getAvatarColor,
  getInitials,
} from '../utils/formatters';

export function ConversationList({
  conversations,
  activeSenderId,
  onSelectConversation,
  favorites,
  searchQuery,
  onOpenNewChat,
}) {
  if (conversations.length === 0) {
    return (
      <div className="wa-conv-empty-state">
        {searchQuery ? (
          <>
            <p className="wa-empty-title">No chats found</p>
            <p className="wa-empty-subtitle">
              No results matching "{searchQuery}"
            </p>
          </>
        ) : (
          <>
            <div className="wa-empty-icon-bubble">
              <MessageSquare size={24} className="text-muted" />
            </div>
            <p className="wa-empty-title">No conversations yet</p>
            <p className="wa-empty-subtitle">
              Start a new chat to interact with the WhatsApp AI assistant.
            </p>
            <button
              type="button"
              className="wa-btn-primary wa-new-chat-empty-btn"
              onClick={onOpenNewChat}
            >
              <UserPlus size={16} />
              <span>Start New Chat</span>
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="wa-conversation-list" role="list">
      {conversations.map((conv) => {
        const isActive = conv.sender_id === activeSenderId;
        const isFav = favorites.includes(conv.sender_id);
        const avatarColor = getAvatarColor(conv.sender_id);
        const initials = getInitials(conv.sender_id);
        const displayName = formatPhoneNumber(conv.sender_id);

        // Format preview text
        let previewPrefix = '';
        if (conv.last_role === 'user') {
          previewPrefix = 'You: ';
        } else if (conv.last_role === 'assistant') {
          previewPrefix = 'AI: ';
        }
        const previewText = conv.last_message
          ? `${previewPrefix}${conv.last_message.replace(/[\n\r]+/g, ' ')}`
          : 'No messages yet';

        return (
          <div
            key={conv.sender_id}
            className={`wa-conversation-item ${isActive ? 'active' : ''}`}
            onClick={() => onSelectConversation(conv.sender_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                onSelectConversation(conv.sender_id);
              }
            }}
          >
            {/* Avatar */}
            <div
              className="wa-conv-avatar"
              style={{ backgroundColor: avatarColor }}
            >
              <span>{initials}</span>
            </div>

            {/* Chat preview content */}
            <div className="wa-conv-content">
              <div className="wa-conv-top-row">
                <span className="wa-conv-name" title={conv.sender_id}>
                  {displayName}
                </span>
                <span className="wa-conv-time">
                  {formatConversationTime(conv.last_timestamp)}
                </span>
              </div>

              <div className="wa-conv-bottom-row">
                <p className="wa-conv-preview" title={conv.last_message || ''}>
                  {conv.last_role === 'user' && (
                    <CheckCheck size={14} className="wa-preview-checks" />
                  )}
                  <span>{previewText}</span>
                </p>

                <div className="wa-conv-badges">
                  {isFav && (
                    <Star size={12} className="text-wa-gold fill-wa-gold" />
                  )}
                  {conv.total_messages > 0 && (
                    <span className="wa-message-count-pill" title={`${conv.total_messages} turns`}>
                      {conv.total_messages}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
