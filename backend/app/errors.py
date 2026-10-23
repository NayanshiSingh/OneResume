"""Domain errors raised by services and mapped to HTTP responses in main.py."""


class NotFoundError(Exception):
    """The item does not exist or does not belong to the current user."""


class ConflictError(Exception):
    """The request conflicts with existing data."""


class InvalidRequestError(Exception):
    """The request is well-formed but cannot be applied."""
