import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

export function useChat() {
  const [conversations, setConversations] = useState([]);
  const [activeSenderId, setActiveSenderId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [backendHealth, setBackendHealth] = useState(null);
  const [isConnected, setIsConnected] = useState(true);
  const [connectionError, setConnectionError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState('all'); // 'all' | 'unread' | 'favorites'
  const [favorites, setFavorites] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('wa_ai_favorites') || '[]');
    } catch {
      return [];
    }
  });

  // Track activeSenderId ref to avoid race conditions during async fetches
  const activeSenderRef = useRef(activeSenderId);
  useEffect(() => {
    activeSenderRef.current = activeSenderId;
  }, [activeSenderId]);

  // Save favorites to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('wa_ai_favorites', JSON.stringify(favorites));
    } catch {
      // Ignore localStorage issues
    }
  }, [favorites]);

  /**
   * Health check poll
   */
  const checkConnection = useCallback(async () => {
    try {
      const data = await api.checkHealth();
      setBackendHealth(data);
      setIsConnected(true);
      setConnectionError(null);
    } catch (err) {
      setIsConnected(false);
      setConnectionError(err.message || 'Backend disconnected');
    }
  }, []);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 15000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  /**
   * Select a conversation and load history
   */
  const selectConversation = useCallback(async (senderId) => {
    if (!senderId) return;
    setActiveSenderId(senderId);
    activeSenderRef.current = senderId;
    setIsLoadingMessages(true);

    try {
      const data = await api.getHistory(senderId, 50);
      if (activeSenderRef.current === senderId) {
        setMessages(data.history || []);
      }
    } catch (err) {
      console.error(`Failed to fetch history for ${senderId}:`, err);
      if (activeSenderRef.current === senderId) {
        setMessages([]);
      }
    } finally {
      if (activeSenderRef.current === senderId) {
        setIsLoadingMessages(false);
      }
    }
  }, []);

  /**
   * Fetch conversation list
   */
  const refreshConversations = useCallback(async () => {
    try {
      const data = await api.getConversations();
      const list = data.conversations || [];
      setConversations(list);

      // Auto-select first conversation if none selected
      if (!activeSenderRef.current && list.length > 0) {
        selectConversation(list[0].sender_id);
      }
    } catch (err) {
      console.warn('Failed to fetch conversations:', err);
    }
  }, [selectConversation]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  /**
   * Send a message to the active conversation
   */
  const sendMessage = useCallback(
    async (text, mediaType = 'text') => {
      const cleanText = text.trim();
      const senderId = activeSenderRef.current;
      if (!cleanText || !senderId || isSending) return;

      const tempId = `temp_${Date.now()}`;
      const nowIso = new Date().toISOString();

      // Optimistic user turn
      const optimisticMsg = {
        id: tempId,
        sender_id: senderId,
        role: 'user',
        content: cleanText,
        media_type: mediaType,
        created_at: nowIso,
        status: 'sending',
      };

      setMessages((prev) => [...prev, optimisticMsg]);
      setIsSending(true);

      try {
        const result = await api.sendMessage(senderId, cleanText, mediaType);

        // Update optimistic user message status to 'sent'
        setMessages((prev) =>
          prev.map((m) => (m.id === tempId ? { ...m, status: 'sent' } : m))
        );

        // Append assistant reply turn
        const assistantMsg = {
          id: `reply_${Date.now()}`,
          sender_id: senderId,
          role: 'assistant',
          content: result.reply,
          media_type: 'text',
          created_at: result.timestamp || new Date().toISOString(),
          status: 'received',
        };

        setMessages((prev) => [...prev, assistantMsg]);

        // Refresh conversation preview in sidebar
        refreshConversations();
      } catch (err) {
        console.error('Error sending message:', err);
        // Mark the optimistic message as failed
        setMessages((prev) =>
          prev.map((m) =>
            m.id === tempId
              ? { ...m, status: 'failed', errorMessage: err.message }
              : m
          )
        );
      } finally {
        setIsSending(false);
      }
    },
    [isSending, refreshConversations]
  );

  /**
   * Retry a failed message
   */
  const retryMessage = useCallback(
    async (failedMsg) => {
      if (!failedMsg || !failedMsg.content) return;
      // Remove failed message from list
      setMessages((prev) => prev.filter((m) => m.id !== failedMsg.id));
      // Re-send
      await sendMessage(failedMsg.content, failedMsg.media_type || 'text');
    },
    [sendMessage]
  );

  /**
   * Start a new chat with a given sender ID
   */
  const startNewChat = useCallback(
    async (newSenderId) => {
      const cleanId = newSenderId.trim();
      if (!cleanId) return;

      // Check if conversation already exists
      const existing = conversations.find((c) => c.sender_id === cleanId);
      if (existing) {
        selectConversation(cleanId);
        return;
      }

      // Add to conversations list optimistically
      const newConv = {
        sender_id: cleanId,
        last_message: 'Chat started',
        last_role: 'system',
        media_type: 'text',
        last_timestamp: new Date().toISOString(),
        total_messages: 0,
        isNew: true,
      };

      setConversations((prev) => [newConv, ...prev]);
      setActiveSenderId(cleanId);
      setMessages([]);
    },
    [conversations, selectConversation]
  );

  /**
   * Clear history for active conversation
   */
  const clearCurrentHistory = useCallback(async () => {
    const senderId = activeSenderRef.current;
    if (!senderId) return;

    try {
      await api.clearHistory(senderId);
      setMessages([]);
      refreshConversations();
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  }, [refreshConversations]);

  /**
   * Toggle favorite
   */
  const toggleFavorite = useCallback((senderId) => {
    setFavorites((prev) =>
      prev.includes(senderId)
        ? prev.filter((id) => id !== senderId)
        : [...prev, senderId]
    );
  }, []);

  /**
   * Filtered conversation list
   */
  const filteredConversations = conversations.filter((conv) => {
    // Search match
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      conv.sender_id.toLowerCase().includes(q) ||
      (conv.last_message && conv.last_message.toLowerCase().includes(q));

    if (!matchesSearch) return false;

    // Tab filter
    if (filterTab === 'favorites') {
      return favorites.includes(conv.sender_id);
    }
    if (filterTab === 'unread') {
      // Heuristic: conversations where last message was from user
      return conv.last_role === 'user';
    }

    return true;
  });

  return {
    conversations,
    filteredConversations,
    activeSenderId,
    activeConversation: conversations.find(
      (c) => c.sender_id === activeSenderId
    ),
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
  };
}
