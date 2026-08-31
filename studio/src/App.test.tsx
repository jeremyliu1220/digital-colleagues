// SPDX-License-Identifier: Apache-2.0

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { studioContract } from "./studioContract";

describe("P4 Studio workflow", () => {
  it("renders a recognizable loading state before session resolution", () => {
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("Loading durable state");
    expect(markup).toContain('aria-live="polite"');
  });

  it("declares every Golden Path workspace and exact-effect control", () => {
    expect(studioContract.controls).toEqual([
      "Bootstrap token",
      "Descriptive Profile",
      "Authoritative Mandate",
      "Finite work",
      "Wake-cycle inspector",
      "Proposal inbox",
      "Approve exact revision",
      "Reject exact revision",
      "Causal audit",
      "ACTIONRESULT",
    ]);
  });

  it("declares all required main workflow states", () => {
    expect(studioContract.states).toEqual([
      "loading",
      "empty",
      "success",
      "rejection",
      "stale",
      "error",
    ]);
  });
});
