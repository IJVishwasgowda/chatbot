/**
 * Formatting helpers for WhatsApp-inspired timestamps, phone numbers, and avatars.
 */

export function formatMessageTime(isoString) {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function formatConversationTime(isoString) {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    // If today
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // If yesterday
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    }

    // Within last 6 days
    if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }

    // Older
    return date.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: '2-digit' });
  } catch {
    return '';
  }
}

export function formatDateDivider(isoString) {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    if (date.toDateString() === now.toDateString()) {
      return 'TODAY';
    }

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return 'YESTERDAY';
    }

    return date.toLocaleDateString([], {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    }).toUpperCase();
  } catch {
    return '';
  }
}

export function formatPhoneNumber(senderId) {
  if (!senderId) return 'Unknown';
  const clean = senderId.replace(/\D/g, '');
  if (clean.length === 11 && clean.startsWith('1')) {
    return `+1 (${clean.slice(1, 4)}) ${clean.slice(4, 7)}-${clean.slice(7)}`;
  }
  if (clean.length === 10) {
    return `(${clean.slice(0, 3)}) ${clean.slice(3, 6)}-${clean.slice(6)}`;
  }
  if (clean.length > 7) {
    return `+${clean.slice(0, clean.length - 10)} ${clean.slice(-10)}`;
  }
  return senderId;
}

const AVATAR_COLORS = [
  '#00a884', // WhatsApp Teal
  '#25d366', // WhatsApp Bright Green
  '#027eb5', // Blue
  '#e542a3', // Pink
  '#8b5cf6', // Violet
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#10b981', // Emerald
  '#06b6d4', // Cyan
  '#6366f1', // Indigo
];

export function getAvatarColor(id) {
  if (!id) return AVATAR_COLORS[0];
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash << 5) - hash + id.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index];
}

export function getInitials(nameOrNumber) {
  if (!nameOrNumber) return '?';
  const clean = nameOrNumber.trim();
  if (/^\+?\d+$/.test(clean)) {
    // If it's a number, return last 2 digits
    return clean.slice(-2);
  }
  const parts = clean.split(' ').filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return clean.slice(0, 2).toUpperCase();
}
