import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { fixtureScamResponse, noWarningResponse, partialResponse, unavailableResponse } from "../../test-fixtures";
import type { AnalysisResponse, ConversationMessage } from "../../types/analysis";
import { ResultPanel } from "./ResultPanel";

describe("ResultPanel", () => {
  it("shows category, severity, recommendation and evidence in plain language", () => {
    render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByRole("heading", { level: 2, name: "Potential scam" })).toBeInTheDocument();
    expect(screen.getByText("Verify independently before responding.")).toBeInTheDocument();
    const summary = screen.getByText("Severity").closest("div");
    expect(summary).toHaveTextContent("High");
    expect(screen.getByText(/Send your OTP/)).toBeInTheDocument();
    expect(screen.getByText("Fixture rule matched a request to disclose a secret.")).toBeInTheDocument();
  });

  it("renders all four coverage fields in a fixed order with their own status text", () => {
    render(<ResultPanel result={unavailableResponse} />);
    const items = within(screen.getByRole("list", { name: "Coverage" })).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "TextUnavailable",
      "URLsNot applicable",
      "ConversationNot applicable",
      "ReputationNot run",
    ]);
  });

  it("keeps a null aggregate score absent and never shows a percentage", () => {
    const { container } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.queryByText(/aggregate/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/risk score/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\d\s?%/);
  });

  it("shows the Demo data badge for fixture responses only", () => {
    const { rerender } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByText("Demo data")).toBeInTheDocument();

    rerender(<ResultPanel result={noWarningResponse} />);
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();
  });

  it("shows the Demo data badge when only a module result is fixture-generated", () => {
    const result: AnalysisResponse = { ...unavailableResponse, fixture_generated: false };
    result.module_results = { text: { ...unavailableResponse.module_results.text, fixture_generated: true } };
    render(<ResultPanel result={result} />);
    expect(screen.getByText("Demo data")).toBeInTheDocument();
  });

  it("never claims safety for a result without a warning", () => {
    const { container } = render(<ResultPanel result={noWarningResponse} />);
    expect(screen.getByRole("heading", { level: 2, name: "No strong warning found" })).toBeInTheDocument();
    expect(screen.getByText(/not a guarantee/i)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\bsafe\b/i);
  });

  it("does not style partial or unavailable results as success", () => {
    const partialNoWarning: AnalysisResponse = { ...partialResponse, verdict: "legitimate" };
    const { container, rerender } = render(<ResultPanel result={partialNoWarning} />);
    expect(container.querySelector(".result-panel")).toHaveClass("verdict-unknown");
    expect(container.querySelector(".result-panel")).not.toHaveClass("verdict-legitimate");

    rerender(<ResultPanel result={unavailableResponse} />);
    expect(container.querySelector(".result-panel")).toHaveClass("verdict-unknown");
  });

  it("explains partial and unavailable results in a status banner", () => {
    const { rerender } = render(<ResultPanel result={partialResponse} />);
    const partial = screen.getByRole("status");
    expect(partial).toHaveTextContent("Partial result");
    expect(partial).toHaveTextContent("Unavailable: URLs.");
    expect(partial).toHaveTextContent("Not run: Reputation.");

    rerender(<ResultPanel result={unavailableResponse} />);
    const unavailable = screen.getByRole("status");
    expect(unavailable).toHaveTextContent("Checks unavailable");
    expect(unavailable).toHaveTextContent("not a clean result");
    expect(screen.getByText("text service returned HTTP 503")).toBeInTheDocument();
  });

  it("shows no status banner for a complete result", () => {
    render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("moves focus to the result heading", () => {
    render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveFocus();
  });

  it("renders submitted values as plain text and never as links", () => {
    const result: AnalysisResponse = {
      ...fixtureScamResponse,
      evidence: [
        {
          id: "url-1",
          indicator_type: "url_feature",
          source_module: "url",
          quote: "see https://example.test/login",
          observed_value: "https://example.test/login",
          explanation: "Observed URL value.",
        },
      ],
    };
    const { container } = render(<ResultPanel result={result} />);
    expect(container.querySelector("a")).toBeNull();
    expect(screen.getByText("https://example.test/login").tagName).toBe("CODE");
  });

  it("tolerates repeated limitation text", () => {
    const result: AnalysisResponse = { ...fixtureScamResponse, limitations: ["Same.", "Same."] };
    render(<ResultPanel result={result} />);
    expect(screen.getAllByText("Same.")).toHaveLength(2);
  });

  describe("conversation evidence", () => {
    const submitted: ConversationMessage[] = [
      { id: "m1", sender_id: "sender-a", text: "Act now, this is urgent." },
      { id: "m2", sender_id: "sender-a", text: "Send your OTP to verify, then reply." },
    ];
    const withEvidence = (quote: string, messageId: string): AnalysisResponse => ({
      ...fixtureScamResponse,
      evidence: [
        {
          id: "conv-1",
          indicator_type: "urgent_secret_request",
          source_module: "conversation",
          quote,
          message_id: messageId,
          explanation: "Urgent wording from one sender.",
        },
      ],
    });

    it("names the message and sender and shows the full submitted message", () => {
      const { container } = render(<ResultPanel result={withEvidence("Send your OTP", "m2")} messages={submitted} />);
      expect(container.querySelector(".message-ref")).toHaveTextContent("Message m2 - sender-a");
      expect(container.querySelector(".source-message")).toHaveTextContent("Send your OTP to verify, then reply.");
    });

    it("does not repeat a message that the quote already shows in full", () => {
      const { container } = render(
        <ResultPanel result={withEvidence("Act now, this is urgent.", "m1")} messages={submitted} />,
      );
      expect(container.querySelector(".message-ref")).toHaveTextContent("Message m1 - sender-a");
      expect(container.querySelector(".source-message")).toBeNull();
    });

    it("says so when an evidence message ID is not in the submitted conversation", () => {
      const { container } = render(<ResultPanel result={withEvidence("Act now", "m9")} messages={submitted} />);
      expect(container.querySelector(".message-ref")).toHaveTextContent(
        "Message m9 is not part of the submitted conversation.",
      );
    });

    it("never shows a long machine-generated ID", () => {
      const { container } = render(<ResultPanel result={withEvidence("Act now", "m1")} messages={submitted} />);
      expect(container.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/i);
    });
  });
});
