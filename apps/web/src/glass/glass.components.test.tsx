import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { GlassButton, GlassField, GlassStatCard, GlassTabs } from "./index";

function Tabs() {
  const [value, setValue] = useState("message");
  return (
    <GlassTabs
      label="Type of content"
      value={value}
      onChange={setValue}
      tabs={[
        { id: "message", label: "Message" },
        { id: "link", label: "Link" },
        { id: "conversation", label: "Conversation" },
      ]}
    />
  );
}

describe("GlassTabs", () => {
  it("is a labelled tablist with one selected, focusable tab", () => {
    render(<Tabs />);
    expect(screen.getByRole("tablist", { name: "Type of content" })).toBeInTheDocument();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.getAttribute("aria-selected"))).toEqual(["true", "false", "false"]);
    expect(tabs.map((tab) => tab.tabIndex)).toEqual([0, -1, -1]);
  });

  it("selects on click", () => {
    render(<Tabs />);
    fireEvent.click(screen.getByRole("tab", { name: "Link" }));
    expect(screen.getByRole("tab", { name: "Link" })).toHaveAttribute("aria-selected", "true");
  });

  it("moves with arrows, wraps, and supports Home and End", () => {
    render(<Tabs />);
    const press = (key: string) => fireEvent.keyDown(document.activeElement ?? document.body, { key });
    screen.getByRole("tab", { name: "Message" }).focus();
    press("ArrowRight");
    expect(screen.getByRole("tab", { name: "Link" })).toHaveFocus();
    press("End");
    expect(screen.getByRole("tab", { name: "Conversation" })).toHaveFocus();
    press("ArrowRight");
    expect(screen.getByRole("tab", { name: "Message" })).toHaveFocus();
    press("ArrowLeft");
    expect(screen.getByRole("tab", { name: "Conversation" })).toHaveAttribute("aria-selected", "true");
    press("Home");
    expect(screen.getByRole("tab", { name: "Message" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("GlassField", () => {
  it("keeps the highlight and still calls the caller's pointer handlers", () => {
    const onPointerMove = vi.fn();
    const onPointerLeave = vi.fn();
    render(<GlassButton onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>Go</GlassButton>);
    const button = screen.getByRole("button", { name: "Go" });
    button.getBoundingClientRect = () => ({ left: 0, top: 0, width: 10, height: 10, right: 10, bottom: 10, x: 0, y: 0, toJSON: () => ({}) });
    fireEvent.pointerMove(button, { clientX: 5, clientY: 5 });
    expect(onPointerMove).toHaveBeenCalledTimes(1);
    expect(button.style.getPropertyValue("--mx")).not.toBe("");
    fireEvent.pointerLeave(button);
    expect(onPointerLeave).toHaveBeenCalledTimes(1);
    expect(button.style.getPropertyValue("--mx")).toBe("");
  });

  it("ties label, hint and error to the input", () => {
    render(<GlassField label="Sender ID" hint="Compared exactly." error="Required." />);
    const input = screen.getByLabelText("Sender ID");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Compared exactly. Required.");
  });

  it("is valid and undescribed without hint or error", () => {
    render(<GlassField label="Link" />);
    const input = screen.getByLabelText("Link");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).not.toHaveAttribute("aria-describedby");
  });

  it("passes input props through", () => {
    const onChange = vi.fn();
    render(<GlassField label="Link" placeholder="https://example.test" onChange={onChange} />);
    fireEvent.change(screen.getByPlaceholderText("https://example.test"), { target: { value: "x" } });
    expect(onChange).toHaveBeenCalled();
  });
});

describe("GlassButton and GlassStatCard", () => {
  it("renders a tier 2 interactive glass button, with a primary variant", () => {
    render(<><GlassButton>Add</GlassButton><GlassButton variant="primary">Check</GlassButton></>);
    const plain = screen.getByRole("button", { name: "Add" });
    expect(plain).toHaveClass("glass", "glass--2", "glass-btn");
    expect(plain).not.toHaveClass("glass-btn--primary");
    expect(plain).toHaveAttribute("data-interactive");
    expect(plain).toHaveAttribute("type", "button");
    expect(screen.getByRole("button", { name: "Check" })).toHaveClass("glass-btn--primary");
  });

  it("keeps a disabled button disabled", () => {
    render(<GlassButton disabled>Off</GlassButton>);
    expect(screen.getByRole("button", { name: "Off" })).toBeDisabled();
  });

  it("renders a stat card on the requested tier", () => {
    const { container } = render(<GlassStatCard tier={3} label="Limit" value="5 MB" hint="per image" />);
    expect(container.querySelector("article")).toHaveClass("glass", "glass--3");
    expect(container).toHaveTextContent("Limit");
    expect(container).toHaveTextContent("5 MB");
    expect(container).toHaveTextContent("per image");
  });

  it("moves the specular highlight with the pointer and resets on leave", () => {
    const { container } = render(<GlassStatCard label="Limit" value="5 MB" />);
    const card = container.querySelector("article") as HTMLElement;
    card.getBoundingClientRect = () => ({ left: 100, top: 50, width: 200, height: 100, right: 300, bottom: 150, x: 100, y: 50, toJSON: () => ({}) });
    fireEvent.pointerMove(card, { clientX: 200, clientY: 100 });
    expect(card.style.getPropertyValue("--mx")).toBe("50%");
    expect(card.style.getPropertyValue("--my")).toBe("50%");
    fireEvent.pointerLeave(card);
    expect(card.style.getPropertyValue("--mx")).toBe("");
  });
});
