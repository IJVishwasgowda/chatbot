import React from 'react';
import {
  MessageSquarePlus,
  Settings,
  Search,
  X,
  Moon,
  Sun,
  Bot,
  RefreshCw,
} from 'lucide-react';
import { ConversationList } from './ConversationList';

export function Sidebar({
  conversations,
  activeSenderId,
  onSelectConversation,
  searchQuery,
  onSearchChange,
  filterTab,
  onFilterChange,
  favorites,
  isConnected,
  onOpenNewChat,
  onOpenSettings,
  darkMode,
  onToggleDarkMode,
  onRefresh,
}) {
  const unreadCount = conversations.filter((c) => c.last_role === 'user').length;
  const favoritesCount = favorites.length;

  return (
    <aside className="wa-sidebar">
      {/* Sidebar Top Header */}
      <div className="wa-sidebar-header">
        <div className="wa-brand">
          <div className="wa-brand-icon">
            <Bot size={22} className="text-white" />
          </div>
          <div className="wa-brand-info">
            <h1 className="wa-brand-title">WhatsApp AI</h1>
            <div className="wa-connection-indicator">
              <span
                className={`wa-status-dot ${isConnected ? 'online' : 'offline'}`}
              />
              <span className="wa-status-text">
                {isConnected ? 'Backend Active' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>

        <div className="wa-sidebar-actions">
          {/* Refresh Conversations */}
          <button
            type="button"
            className="wa-icon-action-btn"
            onClick={onRefresh}
            title="Refresh conversations"
            aria-label="Refresh conversations"
          >
            <RefreshCw size={18} />
          </button>

          {/* New Chat Button */}
          <button
            type="button"
            className="wa-icon-action-btn"
            onClick={onOpenNewChat}
            title="New Chat"
            aria-label="New Chat"
          >
            <MessageSquarePlus size={20} />
          </button>

          {/* Theme Toggle Button */}
          <button
            type="button"
            className="wa-icon-action-btn"
            onClick={onToggleDarkMode}
            title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle Theme"
          >
            {darkMode ? <Sun size={19} /> : <Moon size={19} />}
          </button>

          {/* Settings Button */}
          <button
            type="button"
            className="wa-icon-action-btn"
            onClick={onOpenSettings}
            title="Settings & Diagnostics"
            aria-label="Settings"
          >
            <Settings size={19} />
          </button>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="wa-search-bar-wrap">
        <div className="wa-search-input-box">
          <Search size={16} className="wa-search-icon" />
          <input
            type="text"
            className="wa-search-input"
            placeholder="Search or start new chat"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              className="wa-clear-search-btn"
              onClick={() => onSearchChange('')}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs: All, Unread, Favorites */}
      <div className="wa-filter-tabs">
        <button
          type="button"
          className={`wa-tab-pill ${filterTab === 'all' ? 'active' : ''}`}
          onClick={() => onFilterChange('all')}
        >
          <span>All</span>
          <span className="wa-tab-count">{conversations.length}</span>
        </button>

        <button
          type="button"
          className={`wa-tab-pill ${filterTab === 'unread' ? 'active' : ''}`}
          onClick={() => onFilterChange('unread')}
        >
          <span>Unread</span>
          {unreadCount > 0 && (
            <span className="wa-tab-count highlight">{unreadCount}</span>
          )}
        </button>

        <button
          type="button"
          className={`wa-tab-pill ${filterTab === 'favorites' ? 'active' : ''}`}
          onClick={() => onFilterChange('favorites')}
        >
          <span>Favorites</span>
          {favoritesCount > 0 && (
            <span className="wa-tab-count">{favoritesCount}</span>
          )}
        </button>
      </div>

      {/* Conversations List */}
      <ConversationList
        conversations={conversations}
        activeSenderId={activeSenderId}
        onSelectConversation={onSelectConversation}
        favorites={favorites}
        searchQuery={searchQuery}
        onOpenNewChat={onOpenNewChat}
      />
    </aside>
  );
}
