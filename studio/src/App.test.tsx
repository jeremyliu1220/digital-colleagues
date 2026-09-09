// SPDX-License-Identifier: Apache-2.0

import {
  Children,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  AgentRegistry,
  AuthoritySelection,
  deploymentDraftBody,
  type PackageRecord,
} from "./AgentRegistry";
import { App } from "./App";
import {
  resources,
  resolveLocale,
  setLocale,
  t,
  validateResources,
} from "./i18n";
import { studioContract } from "./studioContract";

const githubPackage: PackageRecord = {
  package: {
    metadata: {
      package_id: "review-package",
      version: "2.3.4",
      display: { "en-US": { name: "Review package" } },
    },
    content: { requested_capabilities: ["propose_reference_message"] },
  },
  package_digest: `sha256:${"1".repeat(64)}`,
  archive_digest: `sha256:${"2".repeat(64)}`,
  source: "github_release",
  trust_state: "untrusted",
  install_state: "not_installed",
  attestation: {
    verification: "verified",
    artifact_digest: `sha256:${"2".repeat(64)}`,
    signer:
      "https://github.com/review/repository/.github/workflows/release.yml",
    signer_digest: `sha256:${"3".repeat(64)}`,
    repository: "review/repository",
    workflow: "review/repository/.github/workflows/release.yml",
    build_identity: "release.yml@refs/tags/v2.3.4",
    source_ref: "refs/tags/v2.3.4",
    source_digest: `sha256:${"4".repeat(64)}`,
    predicate_type: "https://slsa.dev/provenance/v1",
  },
  revision: 1,
};

type InteractiveInput = ReactElement<{
  value?: string;
  onChange?: (event?: { target: { checked: boolean } }) => void;
}>;

function findInput(node: ReactNode, value: string): InteractiveInput | null {
  if (!isValidElement(node)) return null;
  const element = node as ReactElement<{
    children?: ReactNode;
    value?: string;
  }>;
  if (element.type === "input" && element.props.value === value) {
    return element as InteractiveInput;
  }
  for (const child of Children.toArray(element.props.children)) {
    const result = findInput(child, value);
    if (result) return result;
  }
  return null;
}

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

  it("renders the complete GitHub trust review without implying authority", () => {
    setLocale("en-US");
    const markup = renderToStaticMarkup(
      <AgentRegistry
        csrf="synthetic"
        canManage={true}
        initialPackages={[githubPackage]}
      />,
    );
    for (const value of [
      "verified",
      githubPackage.attestation?.signer,
      githubPackage.attestation?.repository,
      githubPackage.attestation?.workflow,
      githubPackage.attestation?.build_identity,
      githubPackage.attestation?.signer_digest,
      githubPackage.attestation?.artifact_digest,
      githubPackage.archive_digest,
      githubPackage.attestation?.source_ref,
      githubPackage.attestation?.source_digest,
      githubPackage.attestation?.predicate_type,
      githubPackage.package.metadata.version,
      "propose_reference_message",
    ]) {
      expect(markup).toContain(value);
    }
    expect(markup).toContain(
      "Attestation proves origin only; it does not establish trust or safety.",
    );
    expect(markup).toContain(
      "Trust is a separate Admin decision for this exact package digest.",
    );
    expect(markup).toContain(
      "Authority and permissions are not bound: no deployment binding exists",
    );
  });

  it("requires explicit capability interaction and never auto-grants notify_human", () => {
    setLocale("en-US");
    let toggled = "";
    const selection = AuthoritySelection({
      requested: githubPackage.package.content.requested_capabilities,
      granted: [],
      busy: false,
      extraConfirmed: false,
      onToggle: (capability) => {
        toggled = capability;
      },
      onConfirmExtra: () => undefined,
    });
    const markup = renderToStaticMarkup(selection);
    expect(markup).toContain('value="notify_human"');
    expect(markup).not.toContain('checked=""');
    findInput(selection, "propose_reference_message")?.props.onChange?.();
    expect(toggled).toBe("propose_reference_message");
    const body = deploymentDraftBody(
      githubPackage,
      "review-deployment",
      [toggled],
      false,
      "explicit-selection",
    );
    expect(body.granted_capabilities).toEqual(["propose_reference_message"]);
    expect(body.granted_capabilities).not.toContain("notify_human");
  });

  it("renders admin_extra prominently and blocks submission until confirmed", () => {
    setLocale("en-US");
    let confirmed = false;
    const selection = AuthoritySelection({
      requested: githubPackage.package.content.requested_capabilities,
      granted: ["notify_human"],
      busy: false,
      extraConfirmed: false,
      onToggle: () => undefined,
      onConfirmExtra: (value) => {
        confirmed = value;
      },
    });
    const markup = renderToStaticMarkup(selection);
    expect(markup).toContain("Admin grants not requested");
    expect(markup).toContain("notify_human");
    expect(markup).toContain("expand the proposed Mandate");
    findInput(selection, "confirm_admin_extra")?.props.onChange?.({
      target: { checked: true },
    });
    expect(confirmed).toBe(true);
    expect(() =>
      deploymentDraftBody(
        githubPackage,
        "review-deployment",
        ["notify_human"],
        false,
        "unconfirmed-extra",
      ),
    ).toThrow();
    expect(
      deploymentDraftBody(
        githubPackage,
        "review-deployment",
        ["notify_human"],
        true,
        "confirmed-extra",
      ).granted_capabilities,
    ).toEqual(["notify_human"]);
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
