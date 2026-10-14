import React from 'react';

/**
 * Parses WhatsApp message formatting rules:
 * - *bold*
 * - _italic_
 * - ~strikethrough~
 * - `code`
 * - newlines and bullet points
 */
export function renderFormattedText(content) {
  if (!content) return null;

  // Split lines first to handle block-level bullets and paragraphs
  const lines = content.split('\n');

  return lines.map((line, lineIdx) => {
    return (
      <React.Fragment key={lineIdx}>
        {lineIdx > 0 && <br />}
        {formatInlineText(line)}
      </React.Fragment>
    );
  });
}

function formatInlineText(text) {
  if (!text) return null;

  // Regex for WhatsApp markdown tokens:
  // `code` | *bold* | _italic_ | ~strikethrough~
  const tokenRegex = /(`[^`]+`|\*[^*\n]+\*|_[^_\n]+_|~[^~\n]+~)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Code: `text`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code key={idx} className="wa-inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold: *text*
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return (
        <strong key={idx} className="wa-bold">
          {part.slice(1, -1)}
        </strong>
      );
    }

    // Italic: _text_
    if (part.startsWith('_') && part.endsWith('_') && part.length >= 2) {
      return (
        <em key={idx} className="wa-italic">
          {part.slice(1, -1)}
        </em>
      );
    }

    // Strikethrough: ~text~
    if (part.startsWith('~') && part.endsWith('~') && part.length >= 2) {
      return (
        <del key={idx} className="wa-strike">
          {part.slice(1, -1)}
        </del>
      );
    }

    return <span key={idx}>{part}</span>;
  });
}
