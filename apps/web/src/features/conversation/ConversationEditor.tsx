import type { ConversationMessage } from "../../types/analysis";

interface Props {
  messages: ConversationMessage[];
  onChange: (messages: ConversationMessage[]) => void;
}

export function ConversationEditor({ messages, onChange }: Props) {
  const addMessage = () => {
    onChange([
      ...messages,
      { id: crypto.randomUUID(), sender_id: "", text: "" },
    ]);
  };

  const update = (index: number, patch: Partial<ConversationMessage>) => {
    onChange(messages.map((message, position) => (position === index ? { ...message, ...patch } : message)));
  };

  return (
    <fieldset className="conversation-editor">
      <legend>Visible conversation history</legend>
      <p className="field-hint">Optional. Only the messages entered here are analyzed; the app cannot see other chats.</p>
      {messages.map((message, index) => (
        <div className="message-row" key={message.id}>
          <label>
            Sender ID
            <input
              maxLength={128}
              value={message.sender_id}
              onChange={(event) => update(index, { sender_id: event.target.value })}
              placeholder="sender-a"
              required
            />
          </label>
          <label className="message-text">
            Message
            <input
              maxLength={2000}
              value={message.text}
              onChange={(event) => update(index, { text: event.target.value })}
              placeholder="Paste one visible message"
              required
            />
          </label>
          <button
            className="ghost-button"
            type="button"
            onClick={() => onChange(messages.filter((_, position) => position !== index))}
            aria-label={`Remove message ${index + 1}`}
          >
            Remove
          </button>
        </div>
      ))}
      {messages.length < 20 && (
        <button className="secondary-button" type="button" onClick={addMessage}>
          Add supplied message
        </button>
      )}
    </fieldset>
  );
}
