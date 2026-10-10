import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScanForm } from "./ScanForm";

function setup() {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  render(<ScanForm busy={false} onSubmit={onSubmit} />);
  return onSubmit;
}

const type = (label: string | RegExp, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
const choose = (name: "Message" | "Link" | "Conversation") => fireEvent.click(screen.getByRole("button", { name }));
const submit = (name: string) => fireEvent.click(screen.getByRole("button", { name }));

const MESSAGE_LABEL = "Paste the message exactly as received";
const LINKS_LABEL = /One link per line/;

describe("ScanForm input types", () => {
  it("shows one input type at a time, starting with a message", () => {
    setup();
    expect(screen.getByRole("button", { name: "Message" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText(MESSAGE_LABEL)).toBeInTheDocument();
    expect(screen.queryByLabelText(LINKS_LABEL)).not.toBeInTheDocument();

    choose("Link");
    expect(screen.getByRole("button", { name: "Link" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Message" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByLabelText(LINKS_LABEL)).toBeInTheDocument();
    expect(screen.queryByLabelText(MESSAGE_LABEL)).not.toBeInTheDocument();

    choose("Conversation");
    expect(screen.getByRole("button", { name: "Add supplied message" })).toBeInTheDocument();
    expect(screen.queryByLabelText(LINKS_LABEL)).not.toBeInTheDocument();
  });

  it("keeps what was typed when switching types and back", () => {
    setup();
    type(MESSAGE_LABEL, "Synthetic message");
    choose("Link");
    choose("Message");
    expect(screen.getByLabelText(MESSAGE_LABEL)).toHaveValue("Synthetic message");
  });

  it("labels the submit button for the chosen type", () => {
    setup();
    expect(screen.getByRole("button", { name: "Check this message" })).toBeInTheDocument();
    choose("Link");
    expect(screen.getByRole("button", { name: "Check this link" })).toBeInTheDocument();
    choose("Conversation");
    expect(screen.getByRole("button", { name: "Check this conversation" })).toBeInTheDocument();
  });

  it("describes the character counter separately from the text label", () => {
    setup();
    expect(screen.getByLabelText(MESSAGE_LABEL)).toHaveAccessibleDescription("0 / 10,000 characters");
  });

  it("states the privacy limits precisely, including provider processing", () => {
    const { container } = render(<ScanForm busy={false} onSubmit={vi.fn()} />);
    const note = container.querySelector(".fr-privacy");
    expect(note).toHaveTextContent("keeps no history of what you submit");
    expect(note).toHaveTextContent("may send your message to the analysis provider");
    expect(note).toHaveTextContent("never opened");
    expect(note?.textContent).not.toMatch(/nothing is stored/i);
  });

  it("disables submit while a request is running", () => {
    render(<ScanForm busy onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Checking…" })).toBeDisabled();
  });
});

describe("ScanForm message type", () => {
  it("blocks an empty message with a plain error", () => {
    const onSubmit = setup();
    submit("Check this message");
    expect(screen.getByRole("alert")).toHaveTextContent("Paste a message to check.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends trimmed text only, with no links or messages", () => {
    const onSubmit = setup();
    type(MESSAGE_LABEL, "  Synthetic message  ");
    submit("Check this message");
    expect(onSubmit).toHaveBeenCalledWith({ text: "Synthetic message", urls: [], messages: [], source: "manual" });
  });
});

describe("ScanForm link type", () => {
  it("blocks an empty list of links", () => {
    const onSubmit = setup();
    choose("Link");
    submit("Check this link");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter at least one link.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks more than five links without echoing them", () => {
    const onSubmit = setup();
    choose("Link");
    type(LINKS_LABEL, Array.from({ length: 6 }, (_, index) => `https://example.test/${index}`).join("\n"));
    submit("Check this link");
    expect(screen.getByRole("alert")).toHaveTextContent("You entered 6 links. Enter at most 5");
    expect(screen.getByRole("alert")).not.toHaveTextContent("example.test");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks a link longer than 2,048 characters", () => {
    const onSubmit = setup();
    choose("Link");
    type(LINKS_LABEL, `https://example.test/${"a".repeat(2048)}`);
    submit("Check this link");
    expect(screen.getByRole("alert")).toHaveTextContent("Link 1 is longer than 2,048 characters");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends trimmed links on their own", () => {
    const onSubmit = setup();
    choose("Link");
    type(LINKS_LABEL, "https://example.test/a\n\n  https://example.test/b  \n");
    submit("Check this link");
    expect(onSubmit).toHaveBeenCalledWith({
      urls: ["https://example.test/a", "https://example.test/b"],
      messages: [],
      source: "manual",
    });
  });

  it("previews links as inert text that is never opened", () => {
    const { container } = render(<ScanForm busy={false} onSubmit={vi.fn()} />);
    choose("Link");
    type(LINKS_LABEL, "https://example.test/login\nhttp://192.0.2.10/verify");
    const list = screen.getByRole("list", { name: "Links to check" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getAllByText("Not opened")).toHaveLength(2);
    expect(container.querySelector("a")).toBeNull();
    expect(screen.getByLabelText(LINKS_LABEL)).toHaveAccessibleDescription(/2 of 5 links/);
  });
});

describe("ScanForm conversation type", () => {
  // Fills the conversation editor with one message per [sender, text] pair.
  function enterMessages(pairs: Array<[string, string]>) {
    choose("Conversation");
    pairs.forEach(() => fireEvent.click(screen.getByRole("button", { name: "Add supplied message" })));
    const senders = screen.getAllByLabelText("Sender ID");
    const texts = screen.getAllByLabelText("Message");
    pairs.forEach(([sender, text], index) => {
      fireEvent.change(senders[index], { target: { value: sender } });
      fireEvent.change(texts[index], { target: { value: text } });
    });
  }

  it("blocks a conversation with no messages", () => {
    const onSubmit = setup();
    choose("Conversation");
    submit("Check this conversation");
    expect(screen.getByRole("alert")).toHaveTextContent("Add at least one message.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends messages as id, sender_id and text only, with the conversation source and no timestamp", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "Act now."], ["sender-b", "Reply"]]);
    submit("Check this conversation");

    const payload = onSubmit.mock.calls[0][0];
    expect(payload).toMatchObject({ urls: [], source: "conversation" });
    expect(payload.text).toBeUndefined();
    expect(payload.messages).toEqual([
      { id: "m1", sender_id: "sender-a", text: "Act now." },
      { id: "m2", sender_id: "sender-b", text: "Reply" },
    ]);
    expect(payload.messages.every((message: object) => !("timestamp" in message))).toBe(true);
  });

  it("keeps whitespace-distinct sender IDs distinct instead of merging them", () => {
    const onSubmit = setup();
    enterMessages([
      ["sender-a", "Act now, this is urgent."],
      [" sender-a", "Send your OTP to verify."],
      ["sender-a ", "Send your OTP to verify."],
    ]);
    submit("Check this conversation");

    const senders = onSubmit.mock.calls[0][0].messages.map((message: { sender_id: string }) => message.sender_id);
    expect(senders).toEqual(["sender-a", " sender-a", "sender-a "]);
    expect(new Set(senders).size).toBe(3);
  });

  it("matches the protected sender exactly, so only an identical ID can be excluded", () => {
    const onSubmit = setup();
    enterMessages([["me", "Act now."], ["me ", "Send your OTP."], [" me ", "Reply."]]);
    type("Your sender ID in this conversation", " me ");
    submit("Check this conversation");

    const payload = onSubmit.mock.calls[0][0];
    expect(payload.sender_id).toBe(" me ");
    const matching = payload.messages.filter((message: { sender_id: string }) => message.sender_id === payload.sender_id);
    expect(matching.map((message: { id: string }) => message.id)).toEqual(["m3"]);
  });

  it("omits a blank protected sender ID", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "Act now."]]);
    type("Your sender ID in this conversation", "   ");
    submit("Check this conversation");
    expect(onSubmit.mock.calls[0][0].sender_id).toBeUndefined();
  });

  it("sends message text exactly as entered, including surrounding spaces", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "  Act now.  "]]);
    submit("Check this conversation");
    expect(onSubmit.mock.calls[0][0].messages[0].text).toBe("  Act now.  ");
  });

  it("blocks a message that is only whitespace and names it", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "   "]]);
    submit("Check this conversation");
    expect(screen.getByRole("alert")).toHaveTextContent("Message m1 needs both a sender ID and message text.");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
