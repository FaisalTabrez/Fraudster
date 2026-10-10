import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { fixtureScamResponse, noWarningResponse, partialResponse, unavailableResponse } from "../../test-fixtures";
import type { AnalysisResponse, ConversationMessage } from "../../types/analysis";
import { ResultPanel } from "./ResultPanel";

describe("ResultPanel", () => {
  it("leads with what to do now, then the verdict, then the evidence", () => {
    const { container } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByRole("heading", { level: 2, name: "Pause. Don't reply, pay, or share codes yet." })).toBeInTheDocument();
    expect(screen.getByText("What to do now")).toBeInTheDocument();
    expect(screen.getByText("Verify independently before responding.")).toBeInTheDocument();

    const action = container.querySelector(".fr-action");
    expect(action).toHaveClass("fr-tone-scam");
    expect(action).toHaveTextContent("Potential scam");
    expect(action).toHaveTextContent("1 warning sign found · High severity · Not a guarantee");

    expect(screen.getByRole("heading", { level: 3, name: "Why we're warning you" })).toBeInTheDocument();
    expect(screen.getByText(/Send your OTP/)).toBeInTheDocument();
    expect(screen.getByText("Fixture rule matched a request to disclose a secret.")).toBeInTheDocument();

    const order = [...container.querySelectorAll("h2, h3")].map((heading) => heading.textContent);
    expect(order).toEqual([
      "Pause. Don't reply, pay, or share codes yet.",
      "Why we're warning you",
      "What we checked",
      "Limits of this result",
    ]);
  });

  it("tags evidence with the human module name and the rule enum", () => {
    render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByText("Secret request")).toBeInTheDocument();
    expect(screen.getByText("Message wording", { selector: ".fr-tag" })).toBeInTheDocument();
    expect(screen.getByText("secret_request")).toBeInTheDocument();
  });

  it("renders all four coverage fields in a fixed order with their own status text", () => {
    render(<ResultPanel result={unavailableResponse} />);
    const items = within(screen.getByRole("list", { name: "What we checked" })).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Message wordingtext service returned HTTP 503Unavailable",
      "Link structureNot applicable",
      "Conversation patternNot applicable",
      "Sender reputationNot run",
    ]);
  });

  it("counts the applicable checks that ran", () => {
    const { rerender } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByText("1 of 2 applicable checks ran")).toBeInTheDocument();
    rerender(<ResultPanel result={unavailableResponse} />);
    expect(screen.getByText("0 of 2 applicable checks ran")).toBeInTheDocument();
  });

  it("keeps a null aggregate score absent and never shows a percentage", () => {
    const { container } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.queryByText(/aggregate/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/risk score/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/\d\s?%/);
  });

  it("shows the Demo data banner for fixture responses only", () => {
    const { rerender } = render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByText("Demo data")).toBeInTheDocument();

    rerender(<ResultPanel result={noWarningResponse} />);
    expect(screen.queryByText("Demo data")).not.toBeInTheDocument();
  });

  it("shows the Demo data banner when only a module result is fixture-generated", () => {
    const result: AnalysisResponse = { ...unavailableResponse, fixture_generated: false };
    result.module_results = { text: { ...unavailableResponse.module_results.text, fixture_generated: true } };
    render(<ResultPanel result={result} />);
    expect(screen.getByText("Demo data")).toBeInTheDocument();
  });

  it("never claims safety for a result without a warning", () => {
    const { container } = render(<ResultPanel result={noWarningResponse} />);
    expect(container.querySelector(".fr-action")).toHaveTextContent("No strong warning found");
    expect(container.querySelector(".fr-action")).toHaveClass("fr-tone-clear");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Still verify anything you didn't expect");
    expect(container.textContent).toMatch(/not a guarantee/i);
    expect(container.textContent).not.toMatch(/\bsafe\b/i);
  });

  it("does not take a verdict tone for partial or unavailable results", () => {
    const partialNoWarning: AnalysisResponse = { ...partialResponse, verdict: "legitimate" };
    const { container, rerender } = render(<ResultPanel result={partialNoWarning} />);
    expect(container.querySelector(".fr-action")).toHaveClass("fr-tone-unknown");
    expect(container.querySelector(".fr-action")).not.toHaveClass("fr-tone-clear");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Only some checks ran");

    rerender(<ResultPanel result={unavailableResponse} />);
    expect(container.querySelector(".fr-action")).toHaveClass("fr-tone-unknown");
    expect(container.querySelector(".fr-action")).toHaveTextContent("No checks completed");
  });

  it("explains partial and unavailable results in a banner that names what did not run", () => {
    const { container, rerender } = render(<ResultPanel result={partialResponse} />);
    const partial = container.querySelector(".fr-banner--partial");
    expect(partial).toHaveAttribute("role", "status");
    expect(partial).toHaveTextContent("Partial result.");
    expect(partial).toHaveTextContent("Unavailable: Link structure.");
    expect(partial).toHaveTextContent("Not run: Sender reputation.");

    rerender(<ResultPanel result={unavailableResponse} />);
    const unavailable = container.querySelector(".fr-banner--unavailable");
    expect(unavailable).toHaveTextContent("Checks unavailable.");
    expect(unavailable).toHaveTextContent("not a clean result");
  });

  it("shows no coverage banner for a complete result", () => {
    const { container } = render(<ResultPanel result={noWarningResponse} />);
    expect(container.querySelector(".fr-banner--partial, .fr-banner--unavailable")).toBeNull();
  });

  it("moves focus to the action headline", () => {
    render(<ResultPanel result={fixtureScamResponse} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveFocus();
  });

  it("keeps technical details collapsed and holds the raw enums", () => {
    const { container } = render(<ResultPanel result={fixtureScamResponse} />);
    const details = container.querySelector("details.fr-details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(details).toHaveTextContent("Technical details");
    expect(within(details).getByText("suspected_scam")).toBeInTheDocument();
    expect(within(details).getByText("fixture-example-1")).toBeInTheDocument();
    expect(details).toHaveTextContent("Scores are not probabilities");
  });

  it("shows only the strongest three evidence items and folds the rest away", () => {
    const evidence = Array.from({ length: 5 }, (_, index) => ({
      id: `ev-${index}`,
      indicator_type: `signal_${index}`,
      source_module: "text" as const,
      quote: `Quote ${index}`,
      explanation: `Why ${index}.`,
    }));
    const { container } = render(<ResultPanel result={{ ...fixtureScamResponse, evidence }} />);
    const more = container.querySelector("details.more-evidence") as HTMLDetailsElement;
    expect(more.open).toBe(false);
    expect(more).toHaveTextContent("Show 2 more");
    expect(container.querySelectorAll(".fr-evidence")).toHaveLength(5);
    expect(more.querySelectorAll(".fr-evidence")).toHaveLength(2);
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
