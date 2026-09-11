# aioaxlevpp

An independent asynchronous client for Axle Energy's read-only Home Assistant
grid-event endpoint. This is an unpublished development candidate.

The caller supplies an `aiohttp.ClientSession` and an Axle Home Assistant token.
`await AxleClient(session, token).get_event()` returns a frozen `GridEvent` or
`None` when the service returns JSON `null` or an empty object. No account,
inverter, opt-in, payment, or dispatch operations are implemented.

Authentication failures raise `AxleAuthenticationError`; transport failures raise
`AxleConnectionError`; unsuccessful responses and malformed events raise
`AxleError`. Exceptions omit response bodies and credentials. The client uses a
10-second timeout, does not follow redirects, and never closes the supplied session.
Polling belongs to the caller. Axle's example uses 600 seconds.

Contract source: https://vpp.axle.energy/landing/home-assistant

The public OpenAPI document does not currently include this endpoint. A real
event was verified using a development account. No-event responses have only
synthetic coverage; JSON `null` and empty objects are accepted. No code has been
copied from the unlicensed HACS repository.

Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy aioaxlevpp`.
