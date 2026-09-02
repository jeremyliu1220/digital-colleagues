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
      "Governance & access",
      "Session role and membership revision",
      "Enrollment status without plaintext",
      "Recovery status without plaintext",
      "Credential lifecycle status",
      "Pending exact change approval",
      "Reviewed exact change diff",
      "Separate proposer and approver",
      "Role-filtered navigation",
      "Bounded safe audit export",
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
      "expired",
      "revoked",
      "read-only",
    ]);
  });

  it("declares P6 governance controls without treating the UI as authority", () => {
    expect(studioContract.controls).toContain("Governance & access");
    expect(studioContract.controls).toContain("Pending exact change approval");
    expect(studioContract.controls).toContain("Reviewed exact change diff");
    expect(studioContract.controls).toContain("Role-filtered navigation");
    expect(studioContract.controls).toContain("Bounded safe audit export");
    expect(studioContract.states).toContain("revoked");
    expect(studioContract.states).toContain("read-only");
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
