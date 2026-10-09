import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ScanForm } from "./ScanForm";

function setup() {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  render(<ScanForm busy={false} onSubmit={onSubmit} />);
  return onSubmit;
}

const type = (label: string | RegExp, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole("button", { name: "Analyze supplied content" }));

describe("ScanForm", () => {
  it("blocks an empty submission with a message", () => {
    const onSubmit = setup();
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter text, at least one URL");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks more than five URLs without echoing them", () => {
    const onSubmit = setup();
    type("URLs", Array.from({ length: 6 }, (_, index) => `https://example.test/${index}`).join("\n"));
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("You entered 6 URLs. Enter at most 5");
    expect(screen.getByRole("alert")).not.toHaveTextContent("example.test");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks a URL longer than 2,048 characters", () => {
    const onSubmit = setup();
    type("URLs", `https://example.test/${"a".repeat(2048)}`);
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("URL 1 is longer than 2,048 characters");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends trimmed text and URLs and omits a blank sender ID", () => {
    const onSubmit = setup();
    type("Message text", "  Synthetic message  ");
    type("URLs", "https://example.test/a\n\n  https://example.test/b  \n");
    type("Your sender ID in the supplied history", "   ");
    submit();
    expect(onSubmit).toHaveBeenCalledWith({
      text: "Synthetic message",
      urls: ["https://example.test/a", "https://example.test/b"],
      messages: [],
      sender_id: undefined,
      source: "manual",
    });
  });

  it("sends a non-blank protected sender ID exactly as entered", () => {
    const onSubmit = setup();
    type("Message text", "Synthetic message");
    type("Your sender ID in the supplied history", " me ");
    submit();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ sender_id: " me " }));
  });

  it("uses the conversation source only when messages are the sole input", () => {
    const onSubmit = setup();
    fireEvent.click(screen.getByRole("button", { name: "Add supplied message" }));
    type("Sender ID", "sender-a");
    type("Message", "Synthetic message");
    submit();
    expect(onSubmit).toHaveBeenLastCalledWith(expect.objectContaining({ source: "conversation" }));

    type("Message text", "Also some pasted text");
    submit();
    expect(onSubmit).toHaveBeenLastCalledWith(expect.objectContaining({ source: "manual" }));
  });

  // Fills the conversation editor with one message per [sender, text] pair.
  function enterMessages(pairs: Array<[string, string]>) {
    pairs.forEach(() => fireEvent.click(screen.getByRole("button", { name: "Add supplied message" })));
    const senders = screen.getAllByLabelText("Sender ID");
    const texts = screen.getAllByLabelText("Message");
    pairs.forEach(([sender, text], index) => {
      fireEvent.change(senders[index], { target: { value: sender } });
      fireEvent.change(texts[index], { target: { value: text } });
    });
  }

  it("sends messages as id, sender_id and text only, with no timestamp", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "Act now."], ["sender-b", "Reply"]]);
    submit();

    const payload = onSubmit.mock.calls[0][0];
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
    submit();

    const senders = onSubmit.mock.calls[0][0].messages.map((message: { sender_id: string }) => message.sender_id);
    expect(senders).toEqual(["sender-a", " sender-a", "sender-a "]);
    expect(new Set(senders).size).toBe(3);
  });

  it("matches the protected sender exactly, so only an identical ID can be excluded", () => {
    const onSubmit = setup();
    enterMessages([["me", "Act now."], ["me ", "Send your OTP."], [" me ", "Reply."]]);
    type("Your sender ID in the supplied history", " me ");
    submit();

    const payload = onSubmit.mock.calls[0][0];
    expect(payload.sender_id).toBe(" me ");
    const matching = payload.messages.filter((message: { sender_id: string }) => message.sender_id === payload.sender_id);
    expect(matching.map((message: { id: string }) => message.id)).toEqual(["m3"]);
  });

  it("sends message text exactly as entered, including surrounding spaces", () => {
    const onSubmit = setup();
    enterMessages([["sender-a", "  Act now.  "]]);
    submit();
    expect(onSubmit.mock.calls[0][0].messages[0].text).toBe("  Act now.  ");
  });

  it("blocks a message that is only whitespace and names it", () => {
    const onSubmit = setup();
    fireEvent.click(screen.getByRole("button", { name: "Add supplied message" }));
    type("Sender ID", "sender-a");
    type("Message", "   ");
    submit();
    expect(screen.getByRole("alert")).toHaveTextContent("Message m1 needs both a sender ID and message text.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("describes the character counter separately from the text label", () => {
    setup();
    expect(screen.getByLabelText("Message text")).toHaveAccessibleDescription("0 / 10,000 characters");
  });

  it("disables submit while a request is running", () => {
    render(<ScanForm busy onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Checking supplied content/ })).toBeDisabled();
  });
});
