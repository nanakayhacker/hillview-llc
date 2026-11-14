"""Shared helpers for the MCP server layer: JSON-safe serialization and tool annotations."""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from enum import Enum
from typing import Any

READ_ONLY = {"readOnlyHint": True, "destructiveHint": False}
MUTATING = {"readOnlyHint": False, "destructiveHint": False}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


def to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / enums / dates into plain JSON-safe values."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj
