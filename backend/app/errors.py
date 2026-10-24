"""Domain errors raised by services and mapped to HTTP responses in main.py."""


class NotFoundError(Exception):
    """The item does not exist or does not belong to the current user."""


class ConflictError(Exception):
    """The request conflicts with existing data."""


class InvalidRequestError(Exception):
    """The request is well-formed but cannot be applied."""


class ProviderUnavailableError(Exception):
    """An external AI provider is not configured or cannot be reached."""


class RateLimitedError(Exception):
    """A limit was reached; the caller may try again after retry_after seconds."""

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after
