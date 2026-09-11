"""HTTP transport for the public Home Assistant event endpoint."""

from aiohttp import ClientError, ClientSession, ClientTimeout

from .exceptions import AxleAuthenticationError, AxleConnectionError, AxleError
from .models import GridEvent, parse_event

EVENT_URL = "https://api.axle.energy/vpp/home-assistant/event"


class AxleClient:
    """Fetch events using a caller-owned HTTP session."""

    def __init__(self, session: ClientSession, token: str) -> None:
        """Keep the caller's session and token without changing session defaults."""
        self._session = session
        self._token = token

    async def get_event(self) -> GridEvent | None:
        """Read the next event; transport failures never include response bodies."""
        try:
            async with self._session.get(
                EVENT_URL,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
                timeout=ClientTimeout(total=10),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise AxleAuthenticationError("Authentication failed")
                if response.status != 200:
                    raise AxleError(f"Unexpected HTTP status {response.status}")
                try:
                    payload = await response.json()
                except ValueError:
                    raise AxleError("Invalid JSON response") from None
        except (ClientError, TimeoutError):
            raise AxleConnectionError("Unable to retrieve grid events") from None
        return parse_event(payload)
