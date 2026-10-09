import { FormEvent, useState } from "react";

import type { AnalysisRequest, ConversationMessage } from "../../types/analysis";
import { ConversationEditor } from "../conversation/ConversationEditor";

// Limits mirror contracts/analysis-request.schema.json.
const MAX_TEXT_LENGTH = 10000;
const MAX_URLS = 5;
const MAX_URL_LENGTH = 2048;

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
    if (parsedUrls.length > MAX_URLS) {
      setLocalError(`You entered ${parsedUrls.length} URLs. Enter at most ${MAX_URLS}, one per line.`);
      return;
    }
    const longUrl = parsedUrls.findIndex((value) => value.length > MAX_URL_LENGTH);
    if (longUrl !== -1) {
      setLocalError(`URL ${longUrl + 1} is longer than ${MAX_URL_LENGTH.toLocaleString()} characters. Shorten it or remove it.`);
      return;
    }
    const incomplete = messages.find((message) => !message.sender_id.trim() || !message.text.trim());
    if (incomplete) {
      setLocalError(`Message ${incomplete.id} needs both a sender ID and message text.`);
      return;
    }
    setLocalError("");
    await onSubmit({
      text: text.trim() || undefined,
      urls: parsedUrls,
      // Fresh copies, so the submitted request is a snapshot that later edits cannot change.
      // Sender IDs and message text are sent exactly as entered: the gateway compares sender
      // IDs exactly, so trimming would merge whitespace-distinct senders or mis-match the
      // protected sender. trim() above is only used to detect blank values.
      messages: messages.map((message) => ({
        id: message.id,
        sender_id: message.sender_id,
        text: message.text,
      })),
      sender_id: senderId.trim() ? senderId : undefined,
      source: messages.length && !text.trim() && !parsedUrls.length ? "conversation" : "manual",
    });
  };

  return (
    <form className="scan-form" onSubmit={submit} aria-labelledby="scan-heading">
      <div className="section-heading">
        <span className="eyebrow">P0 manual flow</span>
        <h2 id="scan-heading">Check what you can see</h2>
        <p>Paste content directly. Submitted links are parsed as text and are never opened by this interface.</p>
      </div>

      <div className="field">
        <label htmlFor="scan-text">Message text</label>
        <textarea
          id="scan-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={MAX_TEXT_LENGTH}
          rows={7}
          placeholder="Paste the message exactly as received"
          aria-describedby="scan-text-hint"
        />
        <span className="field-hint" id="scan-text-hint">
          {text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()} characters
        </span>
      </div>

      <div className="field">
        <label htmlFor="scan-urls">URLs</label>
        <textarea
          id="scan-urls"
          value={urls}
          onChange={(event) => setUrls(event.target.value)}
          rows={3}
          placeholder={`One URL per line, up to ${MAX_URLS}`}
          aria-describedby="scan-urls-hint"
        />
        <span className="field-hint" id="scan-urls-hint">
          Links are checked as text only and are never opened.
        </span>
      </div>

      <div className="field">
        <label htmlFor="scan-sender">Your sender ID in the supplied history</label>
        <input
          id="scan-sender"
          value={senderId}
          onChange={(event) => setSenderId(event.target.value)}
          maxLength={128}
          placeholder="Optional, used to exclude your own messages from sender rules"
        />
      </div>

      <ConversationEditor messages={messages} onChange={setMessages} />

      {localError && <p className="form-error" role="alert">{localError}</p>}
      <button className="primary-button" type="submit" disabled={busy}>
        {busy ? "Checking supplied content…" : "Analyze supplied content"}
      </button>
    </form>
  );
}
