// SPDX-License-Identifier: Apache-2.0

export const studioContract = {
  controls: [
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
  ],
  states: ["loading", "empty", "success", "rejection", "stale", "error"],
} as const;
