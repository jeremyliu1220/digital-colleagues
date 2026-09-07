// SPDX-License-Identifier: Apache-2.0

import type { TranslationKey } from "./locales/en-US";

export const studioContract: {
  controls: TranslationKey[];
  states: string[];
  diffClassifications: string[];
} = {
  controls: [
    "bootstrap.token",
    "builder.profile_kicker",
    "builder.mandate_kicker",
    "revision.kicker",
    "revision.typed_policy",
    "revision.defaults",
    "builder.review_exact",
    "revision.confirm_digest",
    "revision.cancel",
    "work.kicker",
    "wake.kicker",
    "proposal.kicker",
    "proposal.approve",
    "proposal.reject",
    "audit.kicker",
    "governance.kicker",
    "governance.session_binding",
    "governance.no_credentials",
    "governance.authorize_recovery",
    "governance.credentials",
    "governance.pending_changes",
    "governance.reviewed_diff_aria",
    "governance.separate_admin",
    "nav.aria",
    "governance.safe_export",
    "audit.result_stamp",
  ],
  states: [
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
  ],
  diffClassifications: [
    "added",
    "removed",
    "changed",
    "narrowed",
    "expanded",
    "unchanged",
  ],
};
