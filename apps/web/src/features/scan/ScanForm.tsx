import { FormEvent, useState } from "react";

import { Icon, type IconName } from "../../components/Icon";
import { InertUrl } from "../../components/InertUrl";
import { GlassButton } from "../../glass";
import type { AnalysisRequest, ConversationMessage } from "../../types/analysis";
import { ConversationEditor } from "../conversation/ConversationEditor";

// Limits mirror contracts/analysis-request.schema.json.
const MAX_TEXT_LENGTH = 10000;
const MAX_URLS = 5;
const MAX_URL_LENGTH = 2048;

type Mode = "message" | "link" | "conversation";

// One input type at a time, in the brand kit's order: a message, a link, a conversation.
const modes: Array<{ id: Mode; label: string; icon: IconName; submit: string }> = [
  { id: "message", label: "Message", icon: "input-message", submit: "Check this message" },
  { id: "link", label: "Link", icon: "input-link", submit: "Check this link" },
  { id: "conversation", label: "Conversation", icon: "input-conversation", submit: "Check this conversation" },
];

interface Props {
  busy: boolean;
  onSubmit: (request: AnalysisRequest) => Promise<void>;
}

export function ScanForm({ busy, onSubmit }: Props) {
  const [mode, setMode] = useState<Mode>("message");
  const [text, setText] = useState("");
  const [urls, setUrls] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [senderId, setSenderId] = useState("");
  const [localError, setLocalError] = useState("");

  const parsedUrls = urls
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);

  const choose = (next: Mode) => {
    setMode(next);
    setLocalError("");
  };

  const fail = (message: string) => {
    setLocalError(message);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();

    if (mode === "message") {
      if (!text.trim()) return fail("Paste a message to check.");
      setLocalError("");
      await onSubmit({ text: text.trim(), urls: [], messages: [], source: "manual" });
      return;
    }

    if (mode === "link") {
      if (parsedUrls.length === 0) return fail("Enter at least one link.");
      if (parsedUrls.length > MAX_URLS) {
        return fail(`You entered ${parsedUrls.length} links. Enter at most ${MAX_URLS}, one per line.`);
      }
      const longUrl = parsedUrls.findIndex((value) => value.length > MAX_URL_LENGTH);
      if (longUrl !== -1) {
        return fail(`Link ${longUrl + 1} is longer than ${MAX_URL_LENGTH.toLocaleString()} characters. Shorten it or remove it.`);
      }
      setLocalError("");
      await onSubmit({ urls: parsedUrls, messages: [], source: "manual" });
      return;
    }

    if (messages.length === 0) return fail("Add at least one message.");
    const incomplete = messages.find((message) => !message.sender_id.trim() || !message.text.trim());
    if (incomplete) return fail(`Message ${incomplete.id} needs both a sender ID and message text.`);
    setLocalError("");
    await onSubmit({
      urls: [],
      // Fresh copies, so the submitted request is a snapshot that later edits cannot change.
      // Sender IDs and message text are sent exactly as entered: the gateway compares sender
      // IDs exactly, so trimming would merge whitespace-distinct senders or mis-match the
      // protected sender. trim() above is only used to detect blank values.
      messages: messages.map((message) => ({ id: message.id, sender_id: message.sender_id, text: message.text })),
      sender_id: senderId.trim() ? senderId : undefined,
      source: "conversation",
    });
  };

  const active = modes.find((candidate) => candidate.id === mode)!;

  return (
    <form className="fr-card scan-card glass glass--1" onSubmit={submit} aria-labelledby="scan-heading">
      <div>
        <p className="fr-eyebrow">Step 1</p>
        <h2 id="scan-heading" className="fr-h2">What did you receive?</h2>
      </div>

      <div className="fr-seg fr-seg--fill glass-seg" role="group" aria-label="Type of content to check">
        {modes.map((candidate) => (
          <button
            key={candidate.id}
            type="button"
            aria-pressed={mode === candidate.id}
            onClick={() => choose(candidate.id)}
            className="seg-button"
          >
            <Icon name={candidate.icon} size={18} />
            {candidate.label}
          </button>
        ))}
      </div>

      {mode === "message" && (
        <div className="fr-field">
          <label htmlFor="scan-text">Paste the message exactly as received</label>
          <textarea
            id="scan-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="glass-control"
            maxLength={MAX_TEXT_LENGTH}
            rows={8}
            aria-describedby="scan-text-hint"
          />
          <span className="fr-hint" id="scan-text-hint">
            {text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()} characters
          </span>
        </div>
      )}

      {mode === "link" && (
        <div className="link-panel">
          <div className="fr-field">
            <label htmlFor="scan-urls">One link per line, up to {MAX_URLS}</label>
            <textarea
              id="scan-urls"
              value={urls}
              onChange={(event) => setUrls(event.target.value)}
              className="glass-control"
              rows={4}
              aria-describedby="scan-urls-hint"
            />
            <span className="fr-hint" id="scan-urls-hint">
              {parsedUrls.length} of {MAX_URLS} links. Links are read as text and never opened.
            </span>
          </div>
          {parsedUrls.length > 0 && (
            <ul className="url-list" aria-label="Links to check">
              {parsedUrls.map((value, index) => (
                <li key={`${index}-${value}`}><InertUrl value={value} /></li>
              ))}
            </ul>
          )}
        </div>
      )}

      {mode === "conversation" && (
        <>
          <ConversationEditor messages={messages} onChange={setMessages} />
          <div className="fr-field">
            <label htmlFor="scan-sender">Your sender ID in this conversation</label>
            <input id="scan-sender" className="fr-input glass-control" value={senderId} onChange={(event) => setSenderId(event.target.value)} maxLength={128} aria-describedby="scan-sender-hint" />
            <span className="fr-hint" id="scan-sender-hint">Optional. Messages from this sender are not counted as warning signs.</span>
          </div>
        </>
      )}

      <div className="fr-privacy">
        <Icon name="privacy-lock" />
        <span>
          Only what you paste here is checked. Fraudster can't see your other chats or apps and keeps no history of what you
          submit. A text check may send your message to the analysis provider this app is configured with, which handles and
          retains it under its own terms. Links are read as text and never opened.
        </span>
      </div>

      {localError && <p className="fr-banner fr-banner--unavailable" role="alert"><Icon name="coverage-unavailable" />{localError}</p>}

      <div className="scan-submit">
        <GlassButton variant="primary" className="glass-btn--block" type="submit" disabled={busy}>
          {busy ? "Checking…" : active.submit}
        </GlassButton>
      </div>
    </form>
  );
}
