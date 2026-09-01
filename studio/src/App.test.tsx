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
      "Revisioned colleague builder",
      "Typed policy",
      "Explicit defaults",
      "Review exact revision",
      "Confirm exact revision & digest",
      "Cancel draft",
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
      "validation",
      "permission",
      "rejection",
      "stale",
      "conflict",
      "cancelled",
      "error",
    ]);
  });

  it("declares every authority diff classification used by P5 review", () => {
    expect(studioContract.diffClassifications).toEqual([
      "added",
      "removed",
      "changed",
      "narrowed",
      "expanded",
      "unchanged",
    ]);
  });
});
