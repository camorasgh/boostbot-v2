import json
from typing import Dict


class TokenTypeError(Exception):
    """Custom error for issues related to loading tokens."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


async def load_config() -> Dict:
    """
    Loads the config.json as a dict
    """
    with open('config.json', 'r') as file:
        config = json.load(file)
        return config