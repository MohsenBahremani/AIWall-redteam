# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""AIWall-aware OpenAI chat target for PyRIT."""

from __future__ import annotations

import json
import logging

from pyrit.models import Message
from pyrit.prompt_target import OpenAIChatTarget

logger = logging.getLogger(__name__)

BLOCK_PREFIX = "[AIWALL_BLOCK]"


def format_block_message(reason: str | None, body: object = None) -> str:
    reason_s = reason or "blocked"
    extra = ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("policy"):
            extra = f" policy={err['policy']}"
    return f"{BLOCK_PREFIX} reason={reason_s}{extra}"


def parse_block_from_exception(exc: BaseException) -> str | None:
    text = str(exc)
    looks_blocked = (
        "403" in text
        or "PermissionDenied" in type(exc).__name__
        or "aiwall_policy" in text
        or "secret-detected" in text
        or "category-blocked" in text
    )
    if not looks_blocked:
        return None
    try:
        if "{" in text:
            blob = text[text.index("{") :].replace("'", '"')
            data = json.loads(blob)
            err = data.get("error") if isinstance(data, dict) else None
            if isinstance(err, dict):
                reason = err.get("reason") or err.get("code") or "blocked"
                return format_block_message(str(reason), data)
    except Exception:  # noqa: BLE001
        pass
    for hint in ("secret-detected", "category-blocked", "cost-threshold", "daily-limit"):
        if hint in text:
            return format_block_message(hint)
    return format_block_message("blocked")


class AIWallChatTarget(OpenAIChatTarget):
    """OpenAIChatTarget that converts AIWall 403 blocks into scoreable messages."""

    async def send_prompt_async(self, *, message: Message) -> list[Message]:
        try:
            return await super().send_prompt_async(message=message)
        except Exception as exc:  # noqa: BLE001
            block = parse_block_from_exception(exc)
            if block is None:
                raise
            logger.info("AIWall blocked prompt; synthesizing scorer message: %s", block)
            piece = message.message_pieces[0]
            response = Message.from_prompt(prompt=block, role="assistant")
            for resp_piece in response.message_pieces:
                resp_piece.conversation_id = piece.conversation_id
                resp_piece.sequence = piece.sequence + 1
            return [response]
