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


@dataclass(frozen=True, slots=True)
class AxleStatus:
    """Grid event and raw participation flag returned by Axle."""

    event: GridEvent | None
    opted_out: bool | None


def _timestamp(value: object) -> datetime:
    """Parse an API timestamp without assuming the machine's timezone."""
    if not isinstance(value, str):
        raise ValueError("Expected a timestamp")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Timestamp must have a timezone")
    return result


def parse_status(payload: object) -> AxleStatus:
    """Parse the event and raw participation flag without inferring consent."""
    if payload is None or payload == {}:
        return AxleStatus(None, None)
    if not isinstance(payload, dict):
        raise AxleError("Invalid event response")
    opted_out = payload.get("opted_out")
    if "opted_out" in payload and not isinstance(opted_out, bool):
        raise AxleError("Invalid event response")
    if all(
        key in payload and payload[key] is None
        for key in ("start_time", "end_time", "import_export")
    ):
        return AxleStatus(None, opted_out)
    try:
        start = _timestamp(payload["start_time"])
        end = _timestamp(payload["end_time"])
        updated_at = _timestamp(payload["updated_at"])
        direction = payload["import_export"]
        if direction not in ("import", "export") or end <= start:
            raise ValueError("Invalid event window or direction")
    except (KeyError, ValueError, TypeError):
        raise AxleError("Invalid event response") from None
    event = GridEvent(
        start,
        end,
        direction,
        updated_at,
        False if opted_out is None else opted_out,
    )
    return AxleStatus(event, opted_out)


def parse_event(payload: object) -> GridEvent | None:
    """Compatibility wrapper returning only the parsed grid event."""
    return parse_status(payload).event
