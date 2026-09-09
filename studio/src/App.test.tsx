// SPDX-License-Identifier: Apache-2.0

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import {
  resources,
  resolveLocale,
  setLocale,
  t,
  validateResources,
} from "./i18n";
import { studioContract } from "./studioContract";

describe("Digital Colleagues Studio workflow", () => {
  it("renders a recognizable loading state before session resolution", () => {
    setLocale("en-US");
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("Loading durable state");
    expect(markup).toContain('aria-live="polite"');
  });

  it("declares every Golden Path workspace and exact-effect control", () => {
    for (const key of studioContract.controls) {
      expect(resources["en-US"][key]).toBeTruthy();
      expect(resources["zh-TW"][key]).toBeTruthy();
    }
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

  it("declares governance controls without treating the UI as authority", () => {
    expect(studioContract.controls).toContain("governance.kicker");
    expect(studioContract.controls).toContain("governance.pending_changes");
    expect(studioContract.controls).toContain("governance.reviewed_diff_aria");
    expect(studioContract.controls).toContain("nav.aria");
    expect(studioContract.controls).toContain("governance.safe_export");
    expect(studioContract.states).toContain("revoked");
    expect(studioContract.states).toContain("read-only");
  });

  it("declares every authority diff classification used by review", () => {
    expect(studioContract.diffClassifications).toEqual([
      "added",
      "removed",
      "changed",
      "narrowed",
      "expanded",
      "unchanged",
    ]);
  });

  it("declares package trust and deployment lifecycle as separate controls", () => {
    expect(studioContract.controls).toContain("registry.provenance");
    expect(studioContract.controls).toContain("registry.trust");
    expect(studioContract.controls).toContain("registry.install");
    expect(studioContract.controls).toContain("registry.activate");
    expect(studioContract.controls).toContain("registry.drafts");
    expect(studioContract.controls).toContain("registry.review");
    expect(studioContract.controls).toContain("registry.confirm");
    expect(studioContract.controls).toContain("registry.upgrade");
    expect(studioContract.controls).toContain("registry.rollback");
    expect(studioContract.controls).toContain("registry.select");
    expect(studioContract.controls).toContain("registry.audit");
  });

  it("keeps locale resources exact and falls back safely", () => {
    expect(() => validateResources()).not.toThrow();
    expect(Object.keys(resources["zh-TW"]).sort()).toEqual(
      Object.keys(resources["en-US"]).sort(),
    );
    expect(resolveLocale("unknown")).toBe("en-US");
    setLocale("zh-TW");
    expect(t("loading.state")).toContain("載入");
    setLocale("en-US");
  });
});
