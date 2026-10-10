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
});
