# SPDX-License-Identifier: Apache-2.0

"""Run unittest once and emit a structured, fail-closed result."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class UnittestOutcome:
    tests_run: int
    failures: int
    errors: int
    skipped: int
    expected_failures: int
    unexpected_successes: int
    gate_passed: bool

    @classmethod
    def from_result(cls, result: unittest.TestResult) -> UnittestOutcome:
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        expected_failures = len(result.expectedFailures)
        unexpected_successes = len(result.unexpectedSuccesses)
        gate_passed = (
            result.testsRun > 0
            and failures == 0
            and errors == 0
            and skipped == 0
            and expected_failures == 0
            and unexpected_successes == 0
        )
        return cls(
            tests_run=result.testsRun,
            failures=failures,
            errors=errors,
            skipped=skipped,
            expected_failures=expected_failures,
            unexpected_successes=unexpected_successes,
            gate_passed=gate_passed,
        )

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)


def run_suite(suite: unittest.TestSuite, *, stream: TextIO) -> UnittestOutcome:
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    return UnittestOutcome.from_result(runner.run(suite))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a required unittest suite once.")
    parser.add_argument("--start-directory", default="tests")
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--top-level-directory")
    parser.add_argument("--json-output")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=arguments.start_directory,
        pattern=arguments.pattern,
        top_level_dir=arguments.top_level_directory,
    )
    outcome = run_suite(suite, stream=sys.stderr)
    serialized = json.dumps(outcome.to_dict(), indent=2, sort_keys=True) + "\n"
    if arguments.json_output:
        Path(arguments.json_output).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if outcome.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
