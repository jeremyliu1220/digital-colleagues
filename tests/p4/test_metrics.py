# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest

from digital_colleagues.application.p4_services import calculate_colleague_experience_metrics


class P4MetricTests(unittest.TestCase):
    def test_unauthorized_denominator_includes_governance_rejections_and_zero_is_not_applicable(
        self,
    ) -> None:
        base = {
            "rebrief_turns": 0,
            "resumptions_evaluated": 0,
            "wrong_resumptions": 0,
            "ai_eligible_opportunities": 0,
            "ai_visible_outputs": 0,
            "proactive_reviewed": 0,
            "proactive_accepted": 0,
            "ai_interactions_reviewed": 0,
            "unnecessary_interruptions": 0,
            "human_interventions": 0,
            "scenarios_started": 0,
            "scenarios_completed": 0,
            "unauthorized_candidates": 0,
            "unauthorized_escapes": 0,
        }
        zero = {item.metric: item for item in calculate_colleague_experience_metrics(base)}
        self.assertEqual(zero["ai_initiated_rate"].status, "not_applicable")
        self.assertEqual(zero["ai_initiated_rate"].denominator, 0)
        self.assertIsNotNone(zero["ai_initiated_rate"].reason)

        evaluated = {
            **base,
            "unauthorized_candidates": 7,
            "unauthorized_escapes": 0,
        }
        metric = {item.metric: item for item in calculate_colleague_experience_metrics(evaluated)}[
            "unauthorized_proposal_escape_rate"
        ]
        self.assertEqual(metric.denominator, 7)
        self.assertEqual(metric.numerator, 0)
        self.assertEqual(metric.value, 0.0)


if __name__ == "__main__":
    unittest.main()
