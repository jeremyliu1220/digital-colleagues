// SPDX-License-Identifier: Apache-2.0

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("P2 Studio boundary", () => {
  it("states the milestone and runtime boundary", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain("P2 · Core primitives");
    expect(markup).toContain("Runtime orchestration begins");
    expect(markup).toContain("in P3");
    expect(markup).toContain("no live provider required");
  });
});
