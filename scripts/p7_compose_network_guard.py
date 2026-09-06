# SPDX-License-Identifier: Apache-2.0

"""Remove the publisher namespace's default route before serving host ingress."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

RUNTIME_UID = 10001
RUNTIME_GID = 10001


def default_route_count() -> int:
    lines = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()[1:]
    return sum(
        len(fields) >= 8 and fields[1] == "00000000" and fields[7] == "00000000"
        for fields in (line.split() for line in lines)
    )


def main() -> int:
    route_command = shutil.which("ip")
    if route_command is None or os.geteuid() != 0:
        raise RuntimeError("publisher route guard is unavailable")
    for _ in range(4):
        if default_route_count() == 0:
            break
        completed = subprocess.run(
            [route_command, "route", "del", "default"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError("publisher default route could not be removed")
    if default_route_count() != 0:
        raise RuntimeError("publisher retained an external default route")
    os.setgroups([])
    os.setgid(RUNTIME_GID)
    os.setuid(RUNTIME_UID)
    if os.geteuid() != RUNTIME_UID or default_route_count() != 0:
        raise RuntimeError("publisher privilege drop or route boundary failed")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
