"""Exercise response handling without contacting Axle."""

from asyncio import CancelledError
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectionError, ClientSession

from aioaxlevpp import (
    AxleAuthenticationError,
    AxleClient,
    AxleConnectionError,
    AxleError,
)
from aioaxlevpp.client import EVENT_URL

EVENT = {
    "start_time": "2026-09-11T18:00:00+01:00",
    "end_time": "2026-09-11T19:00:00+01:00",
    "import_export": "export",
    "updated_at": "2026-09-11T08:00:00Z",
}


class Responses:
    """Return HTTP responses at the caller-owned session boundary."""

    def __init__(self, get_mock: MagicMock) -> None:
        self.get_mock = get_mock

    def get(
        self,
        url: str,
        *,
        payload: object = None,
        status: int = 200,
        body: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        import json

        response = MagicMock()
        response.status = status
        response.json = AsyncMock(return_value=payload)
        if body is not None:
            try:
                response.json.return_value = json.loads(body)
            except ValueError:
                response.json.side_effect = ValueError()
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=response, side_effect=exception)
        self.get_mock.return_value = manager


@contextmanager
def mock_responses() -> Iterator[Responses]:
    """Mock aiohttp without depending on private ClientResponse constructors."""
    with patch.object(ClientSession, "get") as get_mock:
        yield Responses(get_mock)


@pytest.mark.parametrize("direction", ["import", "export"])
async def test_event(direction: str) -> None:
    """Read typed event data and preserve caller ownership of the session."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, payload={**EVENT, "import_export": direction})
            event = await AxleClient(session, "test-token").get_event()
            assert event is not None
            assert event.direction == direction
            assert event.start == datetime(2026, 9, 11, 17, tzinfo=UTC)
            assert event.end == datetime(2026, 9, 11, 18, tzinfo=UTC)
            assert event.updated_at == datetime(2026, 9, 11, 8, tzinfo=UTC)
            request = responses.get_mock.call_args
            assert request.args == (EVENT_URL,)
            assert request.kwargs["headers"]["Authorization"] == "Bearer test-token"
            assert request.kwargs["allow_redirects"] is False
            assert request.kwargs["timeout"].total == 10
            assert not session.closed


@pytest.mark.parametrize("body", ["null", "{}"])
async def test_no_event(body: str) -> None:
    """Accept empty successful responses."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, body=body)
            assert await AxleClient(session, "test-token").get_event() is None


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, AxleAuthenticationError),
        (403, AxleAuthenticationError),
        (429, AxleError),
        (500, AxleError),
        (302, AxleError),
        (404, AxleError),
    ],
)
async def test_http_errors(status: int, error: type[AxleError]) -> None:
    """Separate invalid credentials from service failures."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, status=status, body="private-body-test-token")
            with pytest.raises(error) as raised:
                await AxleClient(session, "test-token").get_event()
            assert "test-token" not in str(raised.value)
            assert "private-body" not in str(raised.value)


@pytest.mark.parametrize("error", [TimeoutError(), ClientConnectionError()])
async def test_connection_errors(error: Exception) -> None:
    """Translate connection failures without including request metadata."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, exception=error)
            with pytest.raises(AxleConnectionError):
                await AxleClient(session, "test-token").get_event()


async def test_cancellation() -> None:
    """Allow callers to cancel a request."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, exception=CancelledError())
            with pytest.raises(CancelledError):
                await AxleClient(session, "test-token").get_event()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "bad",
        {"error": "bad"},
        {**EVENT, "start_time": None},
        {**EVENT, "start_time": "2026-09-11T17:00:00"},
        {**EVENT, "start_time": "invalid"},
        {**EVENT, "import_export": 1},
        {**EVENT, "end_time": EVENT["start_time"]},
        {**EVENT, "end_time": "2026-09-10T17:00:00Z"},
    ],
)
async def test_invalid_event(payload: object) -> None:
    """Malformed data must not look like a cancelled event."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, payload=payload)
            with pytest.raises(AxleError, match="Invalid event response"):
                await AxleClient(session, "test-token").get_event()


async def test_invalid_json() -> None:
    """Reject invalid JSON without including the response body."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, body="not-json")
            with pytest.raises(AxleError, match="Invalid JSON response"):
                await AxleClient(session, "test-token").get_event()


@pytest.mark.parametrize("opted_out", [True, False])
async def test_opt_out_flag(opted_out: bool) -> None:
    """Preserve the explicit participation flag returned by the live API."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, payload={**EVENT, "opted_out": opted_out})
            event = await AxleClient(session, "test-token").get_event()
            assert event is not None
            assert event.opted_out is opted_out


async def test_invalid_opt_out_flag() -> None:
    """Do not interpret arbitrary strings as participation consent."""
    async with ClientSession() as session:
        with mock_responses() as responses:
            responses.get(EVENT_URL, payload={**EVENT, "opted_out": "false"})
            with pytest.raises(AxleError, match="Invalid event response"):
                await AxleClient(session, "test-token").get_event()
