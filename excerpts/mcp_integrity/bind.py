# Excerpt from the private mcp-tool-integrity-harness prototype, shown for evaluation only.
# Not runnable on its own: the modules it imports are not published. All rights reserved.

"""Canonical digest of tool metadata.

The compared form strips format characters (zero-width, bidi), folds common homoglyphs and sorts schema keys.
Two visually identical texts bind the same digest. One extra visible word changes the digest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_harness.security.normalize import canonical


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("nom d'outil vide")
        if not isinstance(self.input_schema, Mapping):
            raise ValueError("unreadable input schema")


def canonical_tool(tool: ToolSpec) -> str:
    payload = {
        "description": canonical(tool.description),
        "name": canonical(tool.name).replace(" ", ""),
        "schema": _canonical_schema(tool.input_schema),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def binding_digest(tool: ToolSpec) -> str:
    return hashlib.sha256(canonical_tool(tool).encode("utf-8")).hexdigest()


def _canonical_schema(schema: Mapping[str, Any]) -> str:
    try:
        return json.dumps(schema, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("input schema is not serializable") from exc
