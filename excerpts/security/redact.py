# Excerpt from the private mcp-tool-integrity-harness prototype, shown for evaluation only.
# Not runnable on its own: the modules it imports are not published. All rights reserved.

"""Mask secrets in harness traces.

A secret value is never written back into a trace, a reason or an error. The patterns cover fake tokens and the
usual shape of xAI or "sk-" keys without needing the exact value.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from agent_harness.env_secrets import secret_values

from .limits import SECRET_MIN_CHARS

_PATTERN = re.compile(r"(?i)(?:xai-[a-z0-9][a-z0-9_\-]{7,}|sk-[a-z0-9]{8,}|bearer\s+[a-z0-9._\-]{8,})")
REDACTED = "[REDACTED]"


def collect_secrets(extra: Sequence[str] = ()) -> tuple[str, ...]:
    """Explicit secrets plus the API keys read by ``env_secrets``.

    This module does not read the environment itself.
    """

    found = [value.strip() for value in extra if value and value.strip()]
    found.extend(secret_values())
    unique = tuple(dict.fromkeys(item for item in found if len(item) >= SECRET_MIN_CHARS))
    return tuple(sorted(unique, key=len, reverse=True))


def redact(text: str, secrets: Sequence[str]) -> str:
    """Replace exact secrets, then token patterns."""

    cleaned = text
    for secret in sorted({item for item in secrets if len(item) >= SECRET_MIN_CHARS}, key=len, reverse=True):
        cleaned = cleaned.replace(secret, REDACTED)
    return _PATTERN.sub(REDACTED, cleaned)


def contains_secret(text: str, secrets: Sequence[str]) -> bool:
    """True if the text carries a known secret or a token pattern."""

    for secret in secrets:
        if len(secret) >= SECRET_MIN_CHARS and secret in text:
            return True
    return _PATTERN.search(text) is not None
