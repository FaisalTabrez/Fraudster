import { useEffect, useRef } from "react";

import { Icon } from "../../components/Icon";
import type { ConversationMessage } from "../../types/analysis";

// Limit mirrors contracts/analysis-request.schema.json.
export const MAX_MESSAGES = 20;

interface Props {
  messages: ConversationMessage[];
  onChange: (messages: ConversationMessage[]) => void;
}

function idNumber(id: string): number {
  const match = /^m(\d+)$/.exec(id);
  return match ? Number(match[1]) : 0;
}

export function ConversationEditor({ messages, onChange }: Props) {
  // Highest message number handed out so far. A removed number is never reused, so the
  // short IDs shown in results always point at one message of the submitted conversation.
  const issued = useRef(0);
  const addButton = useRef<HTMLButtonElement>(null);
  const focusAfterAdd = useRef<string | null>(null);
  const full = messages.length >= MAX_MESSAGES;

  useEffect(() => {
    if (focusAfterAdd.current) {
      document.getElementById(`message-${focusAfterAdd.current}-sender`)?.focus();
      focusAfterAdd.current = null;
    }
  }, [messages]);

  const addMessage = () => {
    if (full) return;
    const next = Math.max(issued.current, ...messages.map((message) => idNumber(message.id))) + 1;
    issued.current = next;
    focusAfterAdd.current = `m${next}`;
    onChange([...messages, { id: `m${next}`, sender_id: "", text: "" }]);
  };

  const update = (index: number, patch: Partial<ConversationMessage>) => {
    onChange(messages.map((message, position) => (position === index ? { ...message, ...patch } : message)));
  };

  const remove = (index: number) => {
    onChange(messages.filter((_, position) => position !== index));
    addButton.current?.focus();
  };

  return (
    <fieldset className="conversation-editor">
      <legend className="fr-field-legend">Messages in the conversation</legend>
      <p className="fr-hint">
        Only the messages entered here are analyzed; the app cannot see other chats.
        Sender IDs are compared exactly as typed, including spaces.
      </p>
      {messages.map((message, index) => (
        <div className="message-row" role="group" aria-labelledby={`message-${message.id}-title`} key={message.id}>
          <div className="message-row-head">
            <strong id={`message-${message.id}-title`}>Message <code className="fr-chip fr-mono">{message.id}</code></strong>
            <button
              className="fr-btn fr-btn--icon"
              type="button"
              onClick={() => remove(index)}
              aria-label={`Remove message ${message.id}`}
            >
              <Icon name="remove" size={20} />
            </button>
          </div>
          <div className="fr-field">
            <label htmlFor={`message-${message.id}-sender`}>Sender ID</label>
            <input
              id={`message-${message.id}-sender`}
              className="fr-input"
              maxLength={128}
              value={message.sender_id}
              onChange={(event) => update(index, { sender_id: event.target.value })}
              placeholder="sender-a"
              required
            />
          </div>
          <div className="fr-field message-text">
            <label htmlFor={`message-${message.id}-text`}>Message</label>
            <textarea
              id={`message-${message.id}-text`}
              maxLength={2000}
              rows={2}
              value={message.text}
              onChange={(event) => update(index, { text: event.target.value })}
              placeholder="Paste one visible message"
              required
            />
          </div>
        </div>
      ))}
      <p className="fr-hint message-count" aria-live="polite">
        {messages.length} / {MAX_MESSAGES} messages{full ? ". Remove one to add another." : ""}
      </p>
      <button
        ref={addButton}
        className="fr-btn fr-btn--secondary"
        type="button"
        onClick={addMessage}
        aria-disabled={full}
      >
        Add supplied message
      </button>
    </fieldset>
  );
}
