
class TokenTypeError(Exception):
    """Custom error for issues related to loading tokens."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)