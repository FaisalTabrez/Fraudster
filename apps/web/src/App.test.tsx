import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { fixtureScamResponse } from "./test-fixtures";
import type { AnalysisResponse } from "./types/analysis";

const conversationResponse: AnalysisResponse = {
  ...fixtureScamResponse,
  coverage: { ...fixtureScamResponse.coverage, text: "not_applicable", conversation: "complete" },
  evidence: [
    {
      id: "conv-1",
      indicator_type: "urgent_secret_request",
      source_module: "conversation",
      quote: "Act now",
      message_id: "m1",
      explanation: "Urgent wording from one sender.",
    },
  ],
};

const actionHeading = "Pause. Don't reply, pay, or share codes yet.";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("resolves evidence message IDs against the submitted conversation, not later edits", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(conversationResponse), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Conversation" }));
    fireEvent.click(screen.getByRole("button", { name: "Add supplied message" }));
    fireEvent.change(screen.getByLabelText("Sender ID"), { target: { value: "sender-a" } });
    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Act now, this is urgent." } });
    fireEvent.click(screen.getByRole("button", { name: "Check this conversation" }));

    expect(await screen.findByRole("heading", { level: 2, name: actionHeading })).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/analyze");
    expect(JSON.parse(init.body as string)).toEqual({
      urls: [],
      messages: [{ id: "m1", sender_id: "sender-a", text: "Act now, this is urgent." }],
      source: "conversation",
    });
    expect(document.querySelector(".message-ref")).toHaveTextContent("Message m1 - sender-a");
    expect(document.querySelector(".source-message")).toHaveTextContent("Act now, this is urgent.");

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Edited after the analysis" } });
    fireEvent.change(screen.getByLabelText("Sender ID"), { target: { value: "someone-else" } });
    await waitFor(() => expect(screen.getByLabelText("Message")).toHaveValue("Edited after the analysis"));
    expect(document.querySelector(".message-ref")).toHaveTextContent("Message m1 - sender-a");
    expect(document.querySelector(".source-message")).toHaveTextContent("Act now, this is urgent.");
  });

  it("puts whitespace-distinct sender IDs on the wire unchanged", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ...fixtureScamResponse, verdict: "unknown", severity: "unknown", evidence: [], module_results: {} }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Conversation" }));
    const add = () => fireEvent.click(screen.getByRole("button", { name: "Add supplied message" }));
    add();
    add();
    const senders = screen.getAllByLabelText("Sender ID");
    const texts = screen.getAllByLabelText("Message");
    fireEvent.change(senders[0], { target: { value: "sender-a" } });
    fireEvent.change(texts[0], { target: { value: "Act now, this is urgent." } });
    fireEvent.change(senders[1], { target: { value: " sender-a " } });
    fireEvent.change(texts[1], { target: { value: " Send your OTP to verify. " } });
    fireEvent.change(screen.getByLabelText("Your sender ID in this conversation"), { target: { value: " me " } });
    fireEvent.click(screen.getByRole("button", { name: "Check this conversation" }));

    await screen.findByRole("heading", { level: 2, name: /couldn't assess this/ });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({
      urls: [],
      messages: [
        { id: "m1", sender_id: "sender-a", text: "Act now, this is urgent." },
        { id: "m2", sender_id: " sender-a ", text: " Send your OTP to verify. " },
      ],
      sender_id: " me ",
      source: "conversation",
    });
  });

  it("checks a pasted message and shows the action card first", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(fixtureScamResponse), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByLabelText("Paste the message exactly as received"), { target: { value: "Send your OTP" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this message" }));

    expect(await screen.findByRole("heading", { level: 2, name: actionHeading })).toHaveFocus();
    expect(screen.getByText("Demo data")).toBeInTheDocument();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ text: "Send your OTP", urls: [], messages: [], source: "manual" });
  });

  it("shows a plain error and no result when the service cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<App />);

    fireEvent.change(screen.getByLabelText("Paste the message exactly as received"), { target: { value: "Synthetic message" } });
    fireEvent.click(screen.getByRole("button", { name: "Check this message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the analysis service. Nothing was saved.");
    expect(screen.getByText("No analysis yet")).toBeInTheDocument();
  });

  it("identifies the product with the brand mark and wordmark", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".fr-brand")).toHaveTextContent("Fraudster");
    expect(container.querySelector(".fr-brand svg")).toHaveAttribute("aria-hidden", "true");
  });
});
