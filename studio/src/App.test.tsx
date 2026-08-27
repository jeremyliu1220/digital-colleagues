// SPDX-License-Identifier: Apache-2.0

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("P1 Studio scaffold", () => {
  it("states the milestone and runtime boundary", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain("P1 · Scaffold");
    expect(markup).toContain("Runtime behavior begins after P1");
    expect(markup).toContain("no live provider required");
  });
});
