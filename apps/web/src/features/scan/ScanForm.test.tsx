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

  it("includes a non-blank sender ID", () => {
    const onSubmit = setup();
    type("Message text", "Synthetic message");
    type("Your sender ID in the supplied history", " me ");
    submit();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ sender_id: "me" }));
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

  it("describes the character counter separately from the text label", () => {
    setup();
    expect(screen.getByLabelText("Message text")).toHaveAccessibleDescription("0 / 10,000 characters");
  });

  it("disables submit while a request is running", () => {
    render(<ScanForm busy onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Checking supplied content/ })).toBeDisabled();
  });
});
