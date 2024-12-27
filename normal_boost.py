import asyncio
import base64
import os
import random
import re
import string
from os import times
from pathlib import Path
import tls_client
import sys
import subprocess
import aiofiles
from aiofiles import base as aiofiles_base

from datetime import datetime
from disnake import ApplicationInstallTypes, InteractionContextTypes, ApplicationCommandInteraction, Embed, \
    ModalInteraction, ui, TextInputStyle
from disnake.ext import commands
from typing import Dict, List, Union, TextIO, BinaryIO, TypeVar, overload, Tuple, Optional
from typing_extensions import Literal, TypeAlias

from core.misc_boosting import Proxies, get_headers

# File mode type definitions
TextMode: TypeAlias = Literal['r', 'w', 'a', 'r+', 'w+', 'a+', 'x', 'x+']
BinaryMode: TypeAlias = Literal['rb', 'wb', 'ab', 'r+b', 'w+b', 'a+b', 'xb', 'x+b']
FileMode: TypeAlias = Union[TextMode, BinaryMode]

# Type variables for return types
T_TextIO = TypeVar('T_TextIO', bound=TextIO)
T_BinaryIO = TypeVar('T_BinaryIO', bound=BinaryIO)
T_AsyncTextIO = TypeVar('T_AsyncTextIO', bound=aiofiles_base.AsyncBase)
T_AsyncBinaryIO = TypeVar('T_AsyncBinaryIO', bound=aiofiles_base.AsyncBase)

DURATIONS: TypeAlias = Literal['1m', '3m']


class FileIOError(Exception):
    """Custom error for issues related to file operations."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def is_valid_token_type(func: callable) -> callable:
    """Decorator to check if token type is valid"""

    def wrapper(*args, **kwargs):
        token_type = kwargs.get('token_type')
        if token_type not in ['1m', '3m']:
            raise TokenTypeError(f"Invalid token type: {token_type}")
        return func(*args, **kwargs)

    return wrapper


class FileManager:
    """Class to handle file operations with cross-platform compatibility"""

    @staticmethod
    def _get_base_path() -> Path:
        """Get the base path depending on whether running as executable or script"""
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        return Path(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    @overload
    def open(file_name: str, mode: TextMode = 'r') -> TextIO:
        ...

    @staticmethod
    @overload
    def open(file_name: str, mode: BinaryMode) -> BinaryIO:
        ...

    @staticmethod
    def open(file_name: str, mode: FileMode = 'r') -> Union[TextIO, BinaryIO]:
        """
        Open a file regardless of the execution context

        Args:
            file_name: The name of the file to open
            mode: The mode to open the file in

        Returns:
            A file object (text or binary based on mode)

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
    @overload
    async def async_open(file_name: str, mode: TextMode = 'r') -> T_AsyncTextIO:
        ...

    @staticmethod
    @overload
    async def async_open(file_name: str, mode: BinaryMode) -> T_AsyncBinaryIO:
        ...

    @staticmethod
    async def async_open(file_name: str, mode: FileMode = 'r') -> Union[T_AsyncTextIO, T_AsyncBinaryIO]:
        """
        Asynchronously open a file

        Args:
            file_name: The name of the file to open
            mode: The mode to open the file in

        Returns:
            An async file object (text or binary based on mode)

        Raises:
            FileIOError: If there are issues opening the file
        """
        try:
            file_path = (FileManager._get_base_path() / file_name).resolve()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return await aiofiles.open(str(file_path), mode)
        except Exception as e:
            raise FileIOError(f"Error opening file {file_name}: {str(e)}")

    @staticmethod
    @is_valid_token_type
    async def load_tokens(boosts_amount: int, token_type: DURATIONS = '1m') -> Tuple[List[str], int]:
        """
        Load a specified number of tokens from a file

        Args:
            boosts_amount: The amount of boosts to laod for
            token_type: The type of token to load

        Returns:
            List of tokens loaded from the database

        Raises:
            FileIOError: If there are issues with the file
            TokenTypeError: If the token type is invalid
        """
        tokens = []
        try:
            async with await FileManager.async_open(f"input/{token_type}.txt", 'r') as file:
                content = await file.readlines()
                for token in content:
                    parts = token.strip().split(':')
                    if len(parts) == 3: # mail:pass:token
                        token = parts[-1]
                    elif len(parts) == 1: # token
                        token = parts[0]
                    else:
                        continue

                    if token:
                        tokens.append(token)

                if not tokens:
                    raise FileIOError(f"No tokens found in input/{token_type}.txt")

                available_tokens = len(tokens) * 2
                if available_tokens < boosts_amount:
                    raise FileIOError(f"Insufficient tokens available: {available_tokens} < {boosts_amount}")
                return tokens, available_tokens
        except Exception as e:
            raise FileIOError(f"Error loading tokens: {str(e)}")

    @staticmethod
    async def save_results(invite: str, amount: int, join_results: dict, boosts_results: dict, boost_key: Optional[str] = None, user_id: Optional[int] = None) -> None:
        """
        Save the results of the boosting process to a file

        Args:
            invite: The invite link used for boosting
            amount: The amount of boosts to save
            join_results: The results of the join process
            boosts_results: The results of the boosting process
            boost_key: The key used for boosting
            user_id: The user ID of the user who used the key
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_guild_invite = re.sub(r'[<>:"/\\|?*]', '_', invite)
        folder_name = f"output/{timestamp}-{safe_guild_invite}-{amount}x"
        folder_path = FileManager._get_base_path() / folder_name
        os.makedirs(os.path.dirname(folder_path), exist_ok=True)

        successful_joins = [token for token, success in join_results.items() if success]
        failed_joins = [token for token, success in join_results.items() if not success]

        successful_boosts = [token for token, success in boosts_results.items() if success]
        failed_boosts = [token for token, success in boosts_results.items() if not success]

        async with await FileManager.async_open(folder_path / "successful_joins.txt", 'w') as file:
            await file.write('\n'.join(successful_joins))

        async with await FileManager.async_open(folder_path / "failed_joins.txt", 'w') as file:
            await file.write('\n'.join(failed_joins))

        async with await FileManager.async_open(folder_path / "successful_boosts.txt", 'w') as file:
            await file.write('\n'.join(successful_boosts))

        async with await FileManager.async_open(folder_path / "failed_boosts.txt", 'w') as file:
            await file.write('\n'.join(failed_boosts))

        async with await FileManager.async_open(folder_path / "boost_key_usage.txt", 'w') as file:
            if boost_key and user_id:
                await file.write(f"Key: {boost_key}\nUser ID: {user_id}\nTimestamp: {timestamp}")
            else:
                await file.write("No key used")

        async with await FileManager.async_open(folder_path / "summary.txt", 'w') as file:
            await file.write(f"Invite: {invite}\nAmount: {amount}\nTimestamp: {timestamp}\n\n")
            await file.write("Total Boosts Attempted: {amount}\n\n")

            await file.write(f"Successful joins: {len(successful_joins)}\nFailed joins: {len(failed_joins)}\n\n")
            await file.write(f"Successful boosts: {len(successful_boosts)}\nFailed boosts: {len(failed_boosts)}")



class Discord:
    """
    Class to handle Discord API requests for one single token
    """

    def __init__(self, token: str, bot: Union[commands.Bot, commands.InteractionBot, commands.AutoShardedInteractionBot, commands.AutoShardedBot, commands.BotBase]) -> None:
        """
        Initialize the Discord class ù
        Args:
            token: The token to use for requests
            bot: The bot instance to use for logging
        """
        self.not_joined_count = 0
        self.joined_count = 0
        self.token = token
        self.bot = bot
        self.client = tls_client.Session(
            client_identifier="chrome112", # Dont change this
            random_tls_extension_order=True,
        )
        self.join_results = {}
        self.boosts_results = {}
        self.proxies = Proxies()

    def get_cookies(self):
        """
        Retrieve cookies dict
        """
        cookies = {}
        try:
            response = self.client.get('https://discord.com')
            for cookie in response.cookies:
                if cookie.name.startswith('__') and cookie.name.endswith('uid'):
                    cookies[cookie.name] = cookie.value
                return cookies

        except Exception as e:
            self.bot.logger.error(f"Error getting cookies: {str(e)}")
            return cookies

    async def get_boost_ids(self, token: str, proxy_: str):
        """
        Get the boost slots
        Args:
        token [str]: The token to boost the server with
        proxy_ [str]: The proxy to use to handle connections
        """
        try:
            # noinspection HttpUrlsUsage
            proxy = {
                "http": "http://{}".format(proxy_),
                "https": "https://{}".format(proxy_)

            } if proxy_ else None
            response = self.client.get(
                url=f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
                headers=get_headers(token=token),
                cookies=self.get_cookies(),
                proxy=proxy
            )

            r_json = response.json()
            if response.status_code == 200:
                if len(r_json) > 0:
                    boost_ids = [boost['id'] for boost in r_json]
                    return boost_ids

            elif response.status_code == 401 and r_json['message'] == "401: Unauthorized":
                self.bot.logger.error('Invalid Token ({})'.format(token))

            elif response.status_code == 403 and r_json[
                'message'] == "You need to verify your account in order to perform this action.":
                self.bot.logger.error('Flagged Token ({})'.format(token))

            elif response.status_code == 400 and r_json['captcha_key'] == [
                'You need to update your app to join this server.']:
                self.bot.logger.error('\033[0;31m Hcaptcha ({})'.format(token))

            elif r_json['message'] == "404: Not Found":
                self.bot.logger.error("No Nitro")  # D:

            else:
                self.bot.logger.error('Invalid response ({})'.format(r_json))

            return None

        except Exception as e:
            self.bot.logger.error('Unknown error occurred in boosting guild: {}'.format(e))
            return None

    async def get_userid(self, token):
        """
        Uses base64 to decode the first part of the token into the discord ID
        Args:
        token [str]: The single token that gets processed
        """
        x = self.join_results; x.items() # Just to make it look like it's being used
        first_part = token.split('.')[0]    # cause 3 parts of token

        # Add padding if necessary          | cause base64 requirement of being divided by 4
        missing_padding = len(first_part) % 4
        if missing_padding:
            first_part += '=' * (4 - missing_padding)

        decoded_bytes = base64.b64decode(first_part)
        decoded_str = decoded_bytes.decode('utf-8')

        return decoded_str

    async def join_guild(self, token, inv, proxy_):
        """
        Joins guild via token

        Args:
        token [str]: token that joins
        inv [str]: Invite (will get formatted correctly)
        proxy : proxy to be used (none if none)
        """
        payload = {
            'session_id': ''.join(
                random.choice(string.ascii_lowercase) + random.choice(string.digits) for _ in range(16))
        }

        # noinspection HttpUrlsUsage
        proxy = {
            "http": "http://{}".format(proxy_),
            "https": "https://{}".format(proxy_)

        } if proxy_ else None

        invite_code = r"(discord\.gg/|discord\.com/invite/)?([a-zA-Z0-9-]+)$"
        match = re.search(invite_code, inv)
        if match:
            invite_code = match.group(2)
        else:
            pass

        response = self.client.post(
            url='https://discord.com/api/v9/invites/{}'.format(invite_code),
            headers=get_headers(token=token),
            json=payload,
            cookies=self.get_cookies(),
            proxy=proxy
        )

        r_json = response.json()
        if response.status_code == 200:
            self.bot.logger.success('Joined! {} ({})'.format(token, invite_code))
            self.joined_count += 1
            guild_id = r_json.get("guild", {}).get("id")
            return True, guild_id

        elif response.status_code == 401 and r_json['message'] == "401: Unauthorized":
            self.bot.logger.error('Invalid Token ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif response.status_code == 403 and r_json[
            'message'] == "You need to verify your account in order to perform this action.":
            self.bot.logger.error('Flagged Token ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif response.status_code == 400 and r_json['captcha_key'] == [
            'You need to update your app to join this server.']:
            self.bot.logger.error('\033[0;31m Hcaptcha ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif r_json['message'] == "404: Not Found":
            self.bot.logger.error('Unknown invite ({})'.format(invite_code))
            self.not_joined_count += 1
            return False, None
        else:
            self.bot.logger.error('Invalid response ({})'.format(r_json))
            self.not_joined_count += 1
            return False, None

    async def get_boost_data(self, token: str, selected_proxy):
        """
        Retrieves the boost ids and session
        :param token:
        :param selected_proxy:
        :return:
        """
        url = "https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots"
        headers = {"Authorization": token}

        if selected_proxy:
            self.client.proxies = {"http": selected_proxy, "https": selected_proxy}
        try:

            r = self.client.get(url=url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 0:
                    boost_ids = [boost['id'] for boost in data]
                    return boost_ids, self.client
            elif r.status_code == 401:
                self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Invalid Token ({token[:10]}...)')
            elif r.status_code == 403:
                self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Flagged Token ({token[:10]}...)')
            else:
                self.bot.logger.error(
                    f'`ERR_UNEXPECTED_STATUS` Unexpected status code {r.status_code} for token {token[:10]}...')
            return None, None

        except tls_client.sessions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error while retrieving boost data: {str(e)}")
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error retrieving boost data: {str(e)}")

    async def boost_server(self, token: str, guild_id: str, boost_ids) -> bool:
        """
        Boosts the server via guild id
        :param token: account token
        :param guild_id: id of the server to boost

        :param boost_ids: boost ids as a list/tuple/etc.
        :return:
        """
        url = f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions"
        try:
            if not boost_ids:
                self.bot.logger.error(f"`ERR_NO_BOOSTS` No boost IDs available for token: {token[:10]}...")
                return False

            boosted = False
            for boost_id in boost_ids:
                payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
                headers = {"Authorization": token}
                r = self.client.put(url=url, headers=headers, json=payload)
                if r.status_code == 201:
                    self.bot.logger.success(f"Boosted! {token[:10]} ({guild_id})")
                    boosted = True
                    break
                else:
                    response_json = r.json()
                    if "Must wait for premium server subscription cooldown to expire" in response_json.get("message", ""):
                        self.bot.logger.error(f"`ERR_COOLDOWN` Boosts Cooldown for Token {token[:10]}")
                        break
                    self.bot.logger.error(f"`ERR_NOT_SUCCESS` Boost failed: {token[:10]} ({guild_id}). Response: {response_json}")
            return boosted

        except tls_client.sessions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during boosting with token {token[:10]}: {str(e)}")
            return False

        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error boosting with token {token[:10]}: {str(e)}")
            return False

    async def process(self, invite: str) -> None:
        try:
            proxy = await self.proxies.get_random_proxy(self.bot)
            user_id = str(await self.get_userid(token=token))