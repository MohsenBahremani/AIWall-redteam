# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""PromptSendingAttack campaign against AIWall."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Any

from pyrit.executor.attack import AttackScoringConfig, PromptSendingAttack
from pyrit.models import AttackOutcome

from aiwall_pyrit.scorers.hold import aiwall_hold_scorer, jailbreak_success_scorer
from aiwall_pyrit.targets.aiwall_chat_target import AIWallChatTarget, BLOCK_PREFIX


def _fake_aws_key() -> str:
    alphabet = string.digits + string.ascii_uppercase
    return "AKIA" + "".join(secrets.choice(alphabet) for _ in range(16))


def expand_prompt(prompt: str) -> str:
    return prompt.replace("{{FAKE_AWS_KEY}}", _fake_aws_key())


@dataclass
class CampaignCaseResult:
    case_id: str
    mode: str
    technique_id: str
    outcome: str
    detail: str
    attack_outcome: str | None = None


async def run_prompt_send_cases(
    *,
    target: AIWallChatTarget,
    cases: list[dict[str, Any]],
) -> list[CampaignCaseResult]:
    results: list[CampaignCaseResult] = []
    for case in cases:
        mode = case.get("mode") or "bypass"
        prompt = expand_prompt(str(case.get("prompt") or case.get("objective") or ""))
        objective = str(case.get("objective") or prompt)
        if mode == "hold":
            scorer = aiwall_hold_scorer()
        else:
            scorer = jailbreak_success_scorer()
        attack = PromptSendingAttack(
            objective_target=target,
            attack_scoring_config=AttackScoringConfig(objective_scorer=scorer),
        )
        # Use the concrete prompt as the attack objective text so the model sees it.
        result = await attack.execute_async(objective=prompt)
        score = result.last_score
        score_truth: bool | None = None
        if score is not None:
            raw = score.get_value()
            score_truth = bool(raw) if isinstance(raw, (bool, int, float)) else str(raw).lower() == "true"

        attack_outcome = (
            result.outcome.value if isinstance(result.outcome, AttackOutcome) else str(result.outcome)
        )
        last_text = ""
        if result.last_response is not None:
            try:
                last_text = str(result.last_response)
            except Exception:  # noqa: BLE001
                last_text = ""

        if mode == "hold":
            held = bool(score_truth) or BLOCK_PREFIX in last_text
            results.append(
                CampaignCaseResult(
                    case_id=str(case.get("id")),
                    mode=mode,
                    technique_id=str(case.get("technique_id") or ""),
                    outcome="hold" if held else "bypass",
                    detail=f"attack_outcome={attack_outcome} score={score_truth}",
                    attack_outcome=attack_outcome,
                )
            )
        else:
            bypassed = bool(score_truth)
            results.append(
                CampaignCaseResult(
                    case_id=str(case.get("id")),
                    mode=mode,
                    technique_id=str(case.get("technique_id") or ""),
                    outcome="bypass" if bypassed else "hold",
                    detail=f"attack_outcome={attack_outcome} score={score_truth}",
                    attack_outcome=attack_outcome,
                )
            )
    return results
