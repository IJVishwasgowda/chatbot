/**
 * API client for interacting with the WhatsApp AI Chatbot FastAPI backend.
 * Provides resilient fetch wrappers with timeouts, JSON parsing, and actionable error messages.
 */

const DEFAULT_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

let customBaseUrl = null;

export function getBaseUrl() {
  return (customBaseUrl || DEFAULT_BASE_URL).replace(/\/+$/, '');
}

export function setCustomBaseUrl(url) {
  customBaseUrl = url ? url.trim() : null;
}

/**
 * Enhanced fetch with timeout and structured error handling.
 */
async function apiFetch(endpoint, options = {}, timeoutMs = 25000) {
  const url = `${getBaseUrl()}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const defaultHeaders = {
    Accept: 'application/json',
  };

  if (options.body && typeof options.body === 'string') {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        } else if (errorJson.message) {
          errorDetail = errorJson.message;
        }
      } catch {
        // Fall back to status text
      }
      const error = new Error(errorDetail);
      error.status = response.status;
      throw error;
    }

    return await response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      const timeoutError = new Error(
        `Request to ${endpoint} timed out after ${Math.round(timeoutMs / 1000)}s`
      );
      timeoutError.isTimeout = true;
      throw timeoutError;
    }
    // Network errors (backend not running or connection refused)
    if (err.message && err.message.includes('Failed to fetch')) {
      const netError = new Error(
        `Cannot connect to backend server at ${getBaseUrl()}. Make sure FastAPI is running.`
      );
      netError.isNetworkError = true;
      throw netError;
    }
    throw err;
  }
}

export const api = {
  /**
   * Health check and telemetry.
   */
  async checkHealth() {
    return await apiFetch('/health', { method: 'GET' }, 5000);
  },

  /**
   * Fetch distinct conversations with last message preview.
   */
  async getConversations() {
    return await apiFetch('/conversations', { method: 'GET' }, 8000);
  },

  /**
   * Fetch conversation history for a specific sender ID.
   */
  async getHistory(senderId, limit = 50) {
    const encodedSender = encodeURIComponent(senderId);
    return await apiFetch(
      `/history/${encodedSender}?limit=${limit}`,
      { method: 'GET' },
      10000
    );
  },

  /**
   * Send a direct chat message and receive the AI agent reply.
   */
  async sendMessage(senderId, message, mediaType = 'text') {
    return await apiFetch(
      '/chat',
      {
        method: 'POST',
        body: JSON.stringify({
          sender_id: senderId,
          message: message,
          media_type: mediaType,
        }),
      },
      35000 // Antigravity LLM turn may take a few seconds
    );
  },

  /**
   * Clear conversation history for a given sender ID.
   */
  async clearHistory(senderId) {
    const encodedSender = encodeURIComponent(senderId);
    return await apiFetch(
      `/history/${encodedSender}/clear`,
      { method: 'POST' },
      8000
    );
  },
};
