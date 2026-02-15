class GenerationError(Exception):
    """Raised when a problem cannot be generated after retries."""


class InputValidationError(Exception):
    """Raised when input passage does not meet minimum constraints."""
