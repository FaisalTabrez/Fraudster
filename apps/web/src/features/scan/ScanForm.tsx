import { FormEvent, useState } from "react";

import type { AnalysisRequest, ConversationMessage } from "../../types/analysis";
import { ConversationEditor } from "../conversation/ConversationEditor";

interface Props {
  busy: boolean;
  onSubmit: (request: AnalysisRequest) => Promise<void>;
}

export function ScanForm({ busy, onSubmit }: Props) {
  const [text, setText] = useState("");
  const [urls, setUrls] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [senderId, setSenderId] = useState("");
  const [localError, setLocalError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const parsedUrls = urls
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter(Boolean);
    if (!text.trim() && parsedUrls.length === 0 && messages.length === 0) {
      setLocalError("Enter text, at least one URL, or a supplied conversation message.");
      return;
    }
    setLocalError("");
    await onSubmit({
      text: text.trim() || undefined,
      urls: parsedUrls,
      messages,
      sender_id: senderId.trim() || undefined,
      source: messages.length && !text.trim() && !parsedUrls.length ? "conversation" : "manual",
    });
  };

  return (
    <form className="scan-form" onSubmit={submit}>
      <div className="section-heading">
        <span className="eyebrow">P0 manual flow</span>
        <h2>Check what you can see</h2>
        <p>Paste content directly. Submitted links are parsed as text and are never opened by this interface.</p>
      </div>

      <label>
        Message text
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={10000}
          rows={7}
          placeholder="Paste the message exactly as received"
        />
        <span className="field-hint">{text.length.toLocaleString()} / 10,000 characters</span>
      </label>

      <label>
        URLs
        <textarea
          value={urls}
          onChange={(event) => setUrls(event.target.value)}
          rows={3}
          placeholder="One URL per line, up to five"
        />
        <span className="field-hint">The gateway validates URL strings without dereferencing them.</span>
      </label>

      <label>
        Your sender ID in the supplied history
        <input
          value={senderId}
          onChange={(event) => setSenderId(event.target.value)}
          maxLength={128}
          placeholder="Optional, used to exclude your own messages from sender rules"
        />
      </label>

      <ConversationEditor messages={messages} onChange={setMessages} />

      {localError && <p className="form-error" role="alert">{localError}</p>}
      <button className="primary-button" type="submit" disabled={busy}>
        {busy ? "Checking supplied content…" : "Analyze supplied content"}
      </button>
    </form>
  );
}
