<div align="center">

<img src="https://raw.githubusercontent.com/Herbertmt978/python-axle/main/brand/header.svg" alt="aioaxlevpp wordmark with a grid event pulse" width="760">

# aioaxlevpp

An asynchronous, read-only Python client for Axle Energy Home Assistant grid events.

[![PyPI](https://img.shields.io/pypi/v/aioaxlevpp?color=0EA5E9)](https://pypi.org/project/aioaxlevpp/)
![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache--2.0-0F766E.svg)](LICENSE)

[Install](#install) | [Quick start](#quick-start) | [Response and errors](#response-and-errors) | [Scope](#scope-and-security) | [Development](#development)

</div>

`aioaxlevpp` reads the event exposed by Axle Energy's
[Home Assistant endpoint](https://vpp.axle.energy/landing/home-assistant).
It accepts a caller-owned `aiohttp.ClientSession` and an Axle Home Assistant
token. The package does not enrol an account, control an inverter, opt in or
out of an event, or dispatch a device.

## Install

Python 3.13 or newer is required.

```bash
python -m pip install aioaxlevpp
```

## Quick start

```python
import asyncio
import os

from aiohttp import ClientSession
from aioaxlevpp import AxleClient


async def main() -> None:
    token = os.environ["AXLE_HOME_ASSISTANT_TOKEN"]
    async with ClientSession() as session:
        event = await AxleClient(session, token).get_event()

    if event is None:
        print("No event announced")
    else:
        print(event.direction, event.start, event.end)


asyncio.run(main())
```

Get the token through Axle's Home Assistant setup. Keep it out of source code,
logs, and issue reports. The client does not close the session; the caller
owns its lifetime and polling schedule. Axle's published example polls every
600 seconds.

## Response and errors

`get_event()` returns a frozen `GridEvent` with timezone-aware `start`, `end`,
and `updated_at` values, a direction of `import` or `export`, and a Boolean
`opted_out` flag. It returns `None` for JSON `null`, an empty object, or an
object whose `start_time`, `end_time`, and `import_export` fields are explicitly
null. Malformed events raise an error rather than being treated as no event.

| Exception | Meaning |
| --- | --- |
| `AxleAuthenticationError` | The endpoint returned HTTP 401 or 403. Check the token. |
| `AxleConnectionError` | The request failed or timed out. |
| `AxleError` | The endpoint returned another unsuccessful status or invalid event data. |

The client applies a 10-second request timeout, rejects redirects, and omits
credentials and response bodies from its own exception messages. It makes one
read-only request per call.

## Scope and security

This independent package implements only Axle's Home Assistant grid-event read
path. It does not contain account, payment, opt-in, or equipment-control
operations. The public Axle OpenAPI document does not currently describe this
endpoint; the endpoint behaviour has been checked against a development
account and covered by local tests. No code was copied from the unlicensed HACS
repository. Treat the returned event as schedule data for the calling
application, which remains responsible for its own decisions and timing.

Report reproducible problems through
[GitHub Issues](https://github.com/Herbertmt978/python-axle/issues). Do not
include tokens or private account data. This project is independent of Axle
Energy.

## Development

From a checkout, run:

```bash
uv run pytest
uv run ruff check .
uv run mypy aioaxlevpp
```

The package is released under the [Apache 2.0 licence](LICENSE).
