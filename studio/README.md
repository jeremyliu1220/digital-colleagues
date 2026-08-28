<!-- SPDX-License-Identifier: Apache-2.0 -->

# Studio scaffold

This directory remains the React, TypeScript, and Vite shell. P2 updates its milestone
copy to reflect the immutable core contracts, but it deliberately contains no API client,
authentication flow, colleague builder, work surface, approval UI, or audit viewer.
Runtime orchestration begins in P3; product workflows begin only at their documented later
milestones.

From the repository root:

```bash
make studio-dev
```

The command resolves the lockfile in a disposable copy, then starts Vite. Restart it after
editing source. Development and preview servers bind to loopback by default. That reduces
exposure; it is not authentication or a production security boundary.
