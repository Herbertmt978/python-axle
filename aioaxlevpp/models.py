"""Validated grid event data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .exceptions import AxleError


@dataclass(frozen=True, slots=True)
class GridEvent:
    """One grid event, with timezone-aware timestamps."""

    start: datetime
    end: datetime
    direction: Literal["import", "export"]
    updated_at: datetime
    opted_out: bool = False


def _timestamp(value: object) -> datetime:
    """Parse an API timestamp without assuming the machine's timezone."""
    if not isinstance(value, str):
        raise ValueError("Expected a timestamp")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Timestamp must have a timezone")
    return result


def parse_event(payload: object) -> GridEvent | None:
    """Parse the documented event fields; never mask malformed events as empty."""
    if payload is None or payload == {}:
        return None
    if not isinstance(payload, dict):
        raise AxleError("Invalid event response")
    if all(
        key in payload and payload[key] is None
        for key in ("start_time", "end_time", "import_export")
    ):
        return None
    try:
        start = _timestamp(payload["start_time"])
        end = _timestamp(payload["end_time"])
        updated_at = _timestamp(payload["updated_at"])
        direction = payload["import_export"]
        opted_out = payload.get("opted_out", False)
        if not isinstance(opted_out, bool):
            raise ValueError("Invalid opt-out flag")
        if direction not in ("import", "export") or end <= start:
            raise ValueError("Invalid event window or direction")
    except (KeyError, ValueError, TypeError):
        raise AxleError("Invalid event response") from None
    return GridEvent(start, end, direction, updated_at, opted_out)
