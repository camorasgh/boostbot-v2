import asyncio
import base64
import os
import random
import re
import string
from pathlib import Path
import tls_client
import sys
import subprocess
import aiofiles

from datetime import datetime
from disnake import ApplicationInstallTypes, InteractionContextTypes, ApplicationCommandInteraction, Embed, \
    ModalInteraction, ui, TextInputStyle
from disnake.ext import commands
from typing import Dict, List, Union, TextIO, BinaryIO
from typing_extensions import Literal, TypeAlias
from core.misc_boosting import TokenTypeError, load_config, get_headers, Proxies
from core import database

# Constants
DEFAULT_CONTEXTS = InteractionContextTypes.all()
DEFAULT_INSTALL_TYPES = ApplicationInstallTypes.all()
DURATIONS: TypeAlias = Literal['1m', '3m']
FILE_OPENING_MODES: TypeAlias = Literal[
    'r', 'w', 'a', 'rb', 'wb', 'ab', 'r+', 'w+', 'a+', 'r+b', 'w+b', 'a+b', 'x', 'xb', 'x+', 'x+b', 'x+w', 'x+w+', 'x+a', 'x+a+']


class FileIOError(Exception):
    """Custom error for issues related to file operations."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def is_valid_token_type(func: callable) -> callable:
    """
    Decorator to check if the token type is valid
    Args:
    :param func: The function to decorate
    Returns:
        - wrapper: The decorated function
    """

    def wrapper(*args, **kwargs):
        token_type = kwargs.get('token_type')
        if token_type not in ['1m', '3m']:
            raise TokenTypeError(f"Invalid token type: {token_type}")
        return func(*args, **kwargs)

    return wrapper


class FileManager:
    """
    Class to handle file operations with cross-platform compatibility
    """

    @staticmethod
    def _get_base_path() -> Path:
        """Get the base path depending on whether running as executable or script"""
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        return Path(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def open(file_name: str, mode: str = 'r') -> Union[TextIO, BinaryIO]:
        """
        Open a file regardless of the execution context (script or compiled executable)

        Args:
            file_name (str): The name of the file to open
            mode (str): The mode to open the file in ('r', 'w', 'a', 'rb', 'wb', etc.)

        Returns:
            Union[TextIO, BinaryIO]: The opened file object

        Raises:
            FileIOError: If there are issues opening the file
        """
        try:
            file_path = (FileManager._get_base_path() / file_name).resolve()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return open(file_path, mode)

        except (OSError, IOError) as e:
            raise FileIOError(f"Error opening file {file_name}: {str(e)}")
        except Exception as e:
            raise FileIOError(f"Unexpected error while opening file {file_name}: {str(e)}")

    @staticmethod
    async def async_open(file_name: str, mode: str = 'r') -> aiofiles.threadpool.AiofilesContextManager:
        """
        Asynchronously open a file

        Args:
            file_name (str): The name of the file to open
            mode (str): The mode to open the file in

        Returns:
            aiofiles.File: Async file object
        """
        try:
            file_path = (FileManager._get_base_path() / file_name).resolve()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return await aiofiles.open(str(file_path), mode)
        except Exception as e:
            raise FileIOError(f"Error opening file {file_name}: {str(e)}")

    @staticmethod
    @is_valid_token_type
    async def load_tokens(amount: int, token_type: DURATIONS = '1m') -> List[str]:
        """
        Load a specified number of tokens from a file
        Args:
        :param amount: The amount of tokens to load
        :param token_type: The type of token to load
        Returns:
            - tokens: The tokens loaded from the database
        """
        tokens = []
        try:
            async with await FileManager.async_open(f"input/{token_type}.txt", 'r') as file:
                content = await file.readlines()

                if not tokens:
                    raise FileIOError(f"No tokens found in input/{token_type}.txt")
                if len(tokens) < amount:
                    raise FileIOError(
                        f"Not enough tokens in input/{token_type}.txt. Requested: {amount}, Available: {len(tokens)}")

                return tokens
        except FileIOError:
            raise
        except Exception as e:
            raise FileIOError(f"Error loading tokens: {str(e)}")
