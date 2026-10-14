import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { MessageList } from './components/MessageList';
import { MessageInput } from './components/MessageInput';
import { WelcomeScreen } from './components/WelcomeScreen';
import { NewChatModal } from './components/NewChatModal';
import { SettingsPanel } from './components/SettingsPanel';
import { useChat } from './hooks/useChat';
import './App.css';

export function App() {
  const {
    conversations,
    filteredConversations,
    activeSenderId,
    messages,
    isLoadingMessages,
    isSending,
    backendHealth,
    isConnected,
    connectionError,
    checkConnection,
    searchQuery,
    setSearchQuery,
    filterTab,
    setFilterTab,
    favorites,
    toggleFavorite,
    selectConversation,
    sendMessage,
    retryMessage,
    startNewChat,
    clearCurrentHistory,
    refreshConversations,
  } = useChat();

  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showMobileChat, setShowMobileChat] = useState(false);

  // Dark mode management
  const [darkMode, setDarkMode] = useState(() => {
    try {
      const saved = localStorage.getItem('wa_ai_theme');
      if (saved) return saved === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('wa_ai_theme', darkMode ? 'dark' : 'light');
    } catch {
      // Ignore
    }
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode((prev) => !prev);
  };

  const handleSelectConversation = (senderId) => {
    selectConversation(senderId);
    setShowMobileChat(true);
  };

  const handleStartChat = (newSenderId) => {
    startNewChat(newSenderId);
    setShowMobileChat(true);
  };

  const isFav = activeSenderId ? favorites.includes(activeSenderId) : false;

  return (
    <div className={`wa-app-layout ${darkMode ? 'dark-theme' : 'light-theme'}`}>
      <div className="wa-app-frame">
        {/* Left Sidebar (Desktop always visible, Mobile conditionally visible) */}
        <div
          className={`wa-sidebar-wrapper ${
            showMobileChat ? 'wa-mobile-hidden' : 'wa-mobile-visible'
          }`}
        >
          <Sidebar
            conversations={filteredConversations}
            activeSenderId={activeSenderId}
            onSelectConversation={handleSelectConversation}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            filterTab={filterTab}
            onFilterChange={setFilterTab}
            favorites={favorites}
            isConnected={isConnected}
            onOpenNewChat={() => setIsNewChatOpen(true)}
            onOpenSettings={() => setIsSettingsOpen(true)}
            darkMode={darkMode}
            onToggleDarkMode={toggleDarkMode}
            onRefresh={refreshConversations}
          />
        </div>

        {/* Main Chat Panel (Desktop always visible, Mobile conditionally visible) */}
        <main
          className={`wa-main-panel ${
            showMobileChat ? 'wa-mobile-visible' : 'wa-mobile-hidden'
          }`}
        >
          {activeSenderId ? (
            <div className="wa-chat-view">
              <ChatHeader
                senderId={activeSenderId}
                isTyping={isSending}
                isConnected={isConnected}
                isFavorite={isFav}
                onToggleFavorite={() => toggleFavorite(activeSenderId)}
                onClearHistory={clearCurrentHistory}
                onBack={() => setShowMobileChat(false)}
                onOpenInfo={() => setIsSettingsOpen(true)}
              />

              <MessageList
                messages={messages}
                isLoading={isLoadingMessages}
                isSending={isSending}
                onRetry={retryMessage}
                onSendPreset={(presetText) => sendMessage(presetText)}
                contactName={activeSenderId}
              />

              <MessageInput
                onSendMessage={sendMessage}
                isSending={isSending}
                isConnected={isConnected}
                connectionError={connectionError}
                onReconnect={checkConnection}
              />
            </div>
          ) : (
            <WelcomeScreen
              onStartNewChat={() => setIsNewChatOpen(true)}
              backendHealth={backendHealth}
            />
          )}
        </main>
      </div>

      {/* Modals */}
      <NewChatModal
        isOpen={isNewChatOpen}
        onClose={() => setIsNewChatOpen(false)}
        onStartChat={handleStartChat}
        existingSenders={conversations.map((c) => c.sender_id)}
      />

      <SettingsPanel
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        backendHealth={backendHealth}
        isConnected={isConnected}
        onRefreshHealth={checkConnection}
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
      />
    </div>
  );
}

export default App;
