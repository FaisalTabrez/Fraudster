import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import type { ConversationMessage } from "../../types/analysis";
import { ConversationEditor } from "./ConversationEditor";

let latest: ConversationMessage[] = [];

function Harness() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  latest = messages;
  return <ConversationEditor messages={messages} onChange={setMessages} />;
}

const add = () => fireEvent.click(screen.getByRole("button", { name: "Add supplied message" }));

describe("ConversationEditor", () => {
  it("gives new messages short sequential IDs", () => {
    render(<Harness />);
    add();
    add();
    add();
    expect(latest.map((message) => message.id)).toEqual(["m1", "m2", "m3"]);
    expect(screen.getByRole("group", { name: "Message m2" })).toBeInTheDocument();
  });

  it("never reuses a message number after a removal", () => {
    render(<Harness />);
    add();
    add();
    add();
    fireEvent.click(screen.getByRole("button", { name: "Remove message m2" }));
    add();
    expect(latest.map((message) => message.id)).toEqual(["m1", "m3", "m4"]);

    fireEvent.click(screen.getByRole("button", { name: "Remove message m4" }));
    add();
    expect(latest.map((message) => message.id)).toEqual(["m1", "m3", "m5"]);
    expect(new Set(latest.map((message) => message.id)).size).toBe(latest.length);
  });

  it("stores the sender ID and text typed for each message", () => {
    render(<Harness />);
    add();
    add();
    const second = within(screen.getByRole("group", { name: "Message m2" }));
    fireEvent.change(second.getByLabelText("Sender ID"), { target: { value: "sender-b" } });
    fireEvent.change(second.getByLabelText("Message"), { target: { value: "Synthetic reply" } });
    expect(latest[0]).toEqual({ id: "m1", sender_id: "", text: "" });
    expect(latest[1]).toEqual({ id: "m2", sender_id: "sender-b", text: "Synthetic reply" });
  });

  it("allows exactly 20 messages, shows a counter, and then stops adding", () => {
    render(<Harness />);
    expect(screen.getByText("0 / 20 messages")).toBeInTheDocument();
    for (let count = 0; count < 20; count += 1) add();
    expect(latest).toHaveLength(20);

    expect(screen.getByText("20 / 20 messages. Remove one to add another.")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Add supplied message" });
    expect(button).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(button);
    expect(latest).toHaveLength(20);
    expect(screen.getAllByRole("group", { name: /^Message m\d+$/ })).toHaveLength(20);
  });

  it("moves focus to the new sender field after adding, and to the add button after removing", () => {
    render(<Harness />);
    add();
    expect(screen.getByLabelText("Sender ID")).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Remove message m1" }));
    expect(screen.getByRole("button", { name: "Add supplied message" })).toHaveFocus();
  });

  it("states what is analysed and claims no access to other conversations", () => {
    const { container } = render(<Harness />);
    expect(container.textContent).toContain("Only the messages entered here are analyzed");
    expect(container.textContent).toContain("cannot see other chats");
    expect(container.textContent).not.toMatch(/\b(your|all|every) (chats|conversations|inbox|messages)\b/i);
  });
});
