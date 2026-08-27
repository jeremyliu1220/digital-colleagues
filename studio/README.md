<!-- SPDX-License-Identifier: Apache-2.0 -->

# Studio scaffold

This directory is the P1 React, TypeScript, and Vite shell. It deliberately contains no
API client, authentication flow, colleague builder, work surface, approval UI, or audit
viewer. Those capabilities begin only at their documented milestones.

From the repository root:

```bash
make studio-dev
```

The command resolves the lockfile in a disposable copy, then starts Vite. Restart it after
editing source. Development and preview servers bind to loopback by default. That reduces
exposure; it is not authentication or a production security boundary.
