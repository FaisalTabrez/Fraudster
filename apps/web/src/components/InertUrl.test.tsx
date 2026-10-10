import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InertUrl } from "./InertUrl";

describe("InertUrl", () => {
  it("emphasises the real authority after deceptive user information without creating a link", () => {
    const { container } = render(<InertUrl value="https://google.example@evil.test/pay" />);

    expect(container.querySelector("a")).toBeNull();
    expect(container.querySelector(".fr-url__host")).toHaveTextContent("evil.test");
    expect(container.querySelector(".fr-url__dim")).toHaveTextContent("https://google.example@");
    expect(container).toHaveTextContent("Not opened");
  });

  it("is plain text with a Not opened badge and no link", () => {
    const { container } = render(<InertUrl value="https://example.test/login?x=1" />);
    expect(container.querySelector("a")).toBeNull();
    expect(container).toHaveTextContent("Not opened");
    expect(container.querySelector(".fr-url__text")).toHaveTextContent("https://example.test/login?x=1");
  });

  it("dims user-info so only the real host is emphasised", () => {
    const { container } = render(<InertUrl value="https://google.com@evil.example/pay" />);
    const dim = [...container.querySelectorAll(".fr-url__dim")].map((node) => node.textContent);
    expect(dim).toEqual(["https://google.com@", "/pay"]);
    expect(container.querySelector(".fr-url__text")?.textContent).toBe("https://google.com@evil.example/pay");
  });
});
