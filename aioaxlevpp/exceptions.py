"""Public failures returned by the client."""


class AxleError(Exception):
    """The service returned an unsuccessful or invalid response."""


class AxleAuthenticationError(AxleError):
    """The supplied token is not authorized."""


class AxleConnectionError(AxleError):
    """The service could not be reached."""
