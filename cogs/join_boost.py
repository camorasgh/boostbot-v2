import aiohttp
import asyncio
import base64
import random
import re
import string
import tls_client

from colorama import Fore, Style

from disnake import ModalInteraction, ui, TextInputStyle
from disnake.ext import commands
from typing import Dict, Any

from disnake import InteractionContextTypes, ApplicationIntegrationTypes, ApplicationCommandInteraction

# Constants
DEFAULT_CONTEXTS = InteractionContextTypes.all()
DEFAULT_INTEGRATION_TYPES = ApplicationIntegrationTypes.all()


class Log:
    """
    Log class for custom logging functions
    """
    @staticmethod
    def err(msg):
        """
        Log an error message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTRED_EX}-{Fore.RESET}] {msg}')

    @staticmethod
    def succ(msg):
        """
        Log a success message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTMAGENTA_EX}+{Fore.RESET}] {msg}')

    @staticmethod
    def console(msg):
        """
        Log a console message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTMAGENTA_EX}-{Fore.RESET}] {msg}')

class Filemanager:
    def __init__(self):
        self.proxies = []

    @staticmethod
    async def load_tokens(amount):
        """
        Load a specified number of tokens from a file.
        
        Args:
            amount (int): The number of tokens to load.

        Returns:
            list: A list of loaded tokens.
            
        Raises:
            ValueError: If the number of tokens in the file is less than the specified amount.
        """
        tokens = []
        with open("./input/tokens.txt", "r") as file:
            tokenlist = file.readlines()
            for token in tokenlist:
                token = token.strip()
                parts = token.split(":")
                if len(parts) >= 3:  # mail:pass:token
                    token = parts[-1]
                elif len(parts) == 1:  # token only
                    token = parts[0]
                else:
                    # Invalid token format, skipping
                    continue
                
                if token:  # if token not empty string
                    tokens.append(token)

        available_tokens = len(tokens) * 2
        if available_tokens < amount:
            raise ValueError(f"Not enough tokens found in ./input/tokens.txt. Required: {amount}, Found: {len(tokens)*2}")
        
        return tokens[:amount // 2]

    
    async def load_proxies(self) -> None:
        try:
            with open("./input/proxies.txt", "r") as file:
                self.proxies = [await self.format_proxy(line.strip()) for line in file if line.strip()]
            Log.console(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            Log.err("proxies.txt file not found.")
        except Exception as e:
            Log.err(f"Error loading proxies: {str(e)}")

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

    async def get_random_proxy(self) -> Any | None:
        """Return a random proxy from the loaded list, or None if no proxies are available."""
        await self.load_proxies()
        if self.proxies:
            return random.choice(self.proxies)
        return None

class Tokenmanager:
    def __init__(self, bot):
        self.bot = bot
        self.client = tls_client.Session(
            client_identifier="chrome_112",
            random_tls_extension_order=True
        )
        self.join_results: Dict[str, bool] = {}
        self.boost_results: Dict[str, bool] = {}
        self.filemanager = Filemanager()
        self.joined_count = 0
        self.not_joined_count = 0


    
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
            print('Failed to obtain cookies ({})'.format(e))
            return cookies
    
    @staticmethod
    def headers(token: str):
        """
        Construct the headers
        Args:
        token [str]: The token used to construct the headers
        """
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
        return headers # "hardcoded things cuz idk but it works godly" ~ borgo 2k24


    async def get_boost_ids(self, token:str, proxy_:str):
        """
        Get the boost slots
        Args:
        token [str]: The token to boost the server with
        proxy_ [str]: The proxy to use to handle connections
        """
        try:
            proxy = {
                "http": "http://{}".format(proxy_),
                "https": "https://{}".format(proxy_)

            } if proxy_ else None
            response = self.client.get(
                url=f"https://canary.discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
                headers=self.headers(token=token),
                cookies=self.get_cookies(),
                proxy=proxy
            )
            
            r_json = response.json()
            if response.status_code == 200:
                if len(r_json) > 0:
                    boost_ids = [boost['id'] for boost in r_json]
                    return boost_ids # yippeee
                
            elif response.status_code == 401 and r_json['message'] == "401: Unauthorized":
                Log.err('Invalid Token ({})'.format(token))

            elif response.status_code == 403 and r_json['message'] == "You need to verify your account in order to perform this action.":
                Log.err('Flagged Token ({})'.format(token))

            elif response.status_code == 400 and r_json['captcha_key'] == ['You need to update your app to join this server.']:
                Log.err('\033[0;31m Hcaptcha ({})'.format(token))

            elif r_json['message'] == "404: Not Found":
                Log.err("No Nitro") # D:

            else:
                Log.err('Invalid response ({})'.format(r_json))

            return None
        
        except Exception as e:
            Log.err('Unknown error occurred in boosting guild: {}'.format(e))
            return None

    async def get_userid(self, token): # "may be static" ~ pycharm (woah)
        """
        Uses base64 to decode the first part of the token into the discord ID
        Args:
        token [str]: The single token that gets processed
        """
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
        token [str]: token that joins
        inv [str]: Invite (will get formatted correctly)
        proxy : proxy to be used (none if none)
        """
        payload = {
            'session_id': ''.join(random.choice(string.ascii_lowercase) + random.choice(string.digits) for _ in range(16))
        }
        invite_code = r"(discord\.gg/|discord\.com/invite/)?([a-zA-Z0-9-]+)$"
        match = re.search(invite_code, inv)
        if match:
            invite_code = match.group(2)
        else:
            pass

        proxy = {
            "http": "http://{}".format(proxy_),
            "https": "https://{}".format(proxy_)

        } if proxy_ else None
        
        response = self.client.post(
            url='https://discord.com/api/v9/invites/{}'.format(invite_code),
            headers=self.headers(token=token),
            json=payload,
            cookies=self.get_cookies(),
            proxy=proxy
        )

        r_json = response.json()
        if response.status_code == 200:
            Log.succ('Joined! {} ({})'.format(token, invite_code))
            self.write_joined_token(token, invite_code) # Here error
            self.joined_count += 1
            guild_id = r_json.get("guild", {}).get("id")
            return True, guild_id
           
        elif response.status_code == 401 and r_json['message'] == "401: Unauthorized":
            Log.err('Invalid Token ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif response.status_code == 403 and r_json['message'] == "You need to verify your account in order to perform this action.":
            Log.err('Flagged Token ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif response.status_code == 400 and r_json['captcha_key'] == ['You need to update your app to join this server.']:
            Log.err('\033[0;31m Hcaptcha ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif r_json['message'] == "404: Not Found":
            Log.err('Unknown invite ({})'.format(invite_code))
            self.not_joined_count += 1
            return False, None
        else:
            Log.err('Invalid response ({})'.format(r_json))
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
        try:
            async with aiohttp.ClientSession() as session:
                session.proxies = selected_proxy
                headers = {"Authorization": token}
                async with session.get(url=url, headers=headers) as r:
                    if r.status == 200:
                        data = await r.json()
                        if len(data) > 0:
                            boost_ids = [boost['id'] for boost in data]
                            return boost_ids, session
                    elif r.status == 401:
                        self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Invalid Token ({token[:10]}...)')
                    elif r.status == 403:
                        self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Flagged Token ({token[:10]}...)')
                    else:
                        self.bot.logger.error(f'`ERR_UNEXPECTED_STATUS` Unexpected status code {r.status} for token {token[:10]}...')
                return None, None
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error while retrieving boost data: {str(e)}")
            return None, None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error retrieving boost data: {str(e)}")
            return None, None

    async def boost_server(self, token: str, guild_id: str, session, boost_ids) -> bool:
        url = f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions"
        try:
            if not boost_ids:
                self.bot.logger.error(f"`ERR_NO_BOOSTS` No boost IDs available for token: {token[:10]}...")
                return False

            boosted = False
            for boost_id in boost_ids:
                payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
                headers = {"Authorization": token}
                async with session.put(url=url, headers=headers, json=payload) as r:
                    if r.status == 201:
                        self.bot.logger.success(f"Boosted! {token[:10]} ({guild_id})")
                        boosted = True
                        break
                    else:
                        response_json = await r.json()
                        self.bot.logger.error(f"`ERR_NOT_SUCCESS` Boost failed: {token[:10]} ({guild_id}). Response: {response_json}")
            return boosted

        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during boosting with token {token[:10]}: {str(e)}")
            return False

        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error boosting with token {token[:10]}: {str(e)}")
            return False


    async def process_single_token(self, token: str, guild_invite: str):
        """
        Starts single token process from getting a proxy to boosting the server
        :param token:
        :param guild_invite:
        :return:
        """
        try:
            selected_proxy = await self.filemanager.get_random_proxy()
            user_id = str(await self.get_userid(token=token)) # still needs to be made
            joined, guild_id = await self.join_guild(token=token, inv=guild_invite, proxy_=selected_proxy) # still needs to be made | possibly done
            if joined:
                boost_ids, session = await self.get_boost_data(token=token, selected_proxy=selected_proxy)
                boosted = await self.boost_server(token=token, guild_id=guild_id, session=session, boost_ids=boost_ids)
                self.boost_results[user_id] = False if boosted == False else True
                pass
            else:
                self.boost_results[user_id] = False
        except Exception as e:
            self.bot.logger.error(f"Error processing token {token[:10]}...: {str(e)}")


    async def process_tokens(self, guild_invite: str, amount: int):
        tokens_to_process = await Filemanager.load_tokens(amount)
        tasks = [self.process_single_token(token, guild_invite) for token in tokens_to_process]
        await asyncio.gather(*tasks) 


class BoostingModal(ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        components = [
            ui.TextInput(
                label="Guild Invite",
                placeholder="Enter the guild invite",
                custom_id="boosting.guild_invite",
                style=TextInputStyle.short,
                min_length=3,
                max_length=30,
            ),
            ui.TextInput(
                label="Amount",
                placeholder="The amount of boosts",
                custom_id="boosting.amount",
                style=TextInputStyle.short,
                min_length=1,
                max_length=2
            ),
        ]
        super().__init__(title="Join Booster", components=components)

    async def callback(self, interaction: ModalInteraction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            guild_invite = interaction.text_values['boosting.guild_invite']
            amount = int(interaction.text_values['boosting.amount'])
            token_mngr = Tokenmanager(self.bot)
            await token_mngr.process_tokens(guild_invite=guild_invite, amount=amount)

        except Exception as e:
            self.bot.logger.error(str(e))
            await interaction.followup.send("An error occurred while boosting.", ephemeral=True)


# TODO:
# check valid invite
# check valid boost amount
# check valid token counts
# we prob might just handle invite errors and token errors directly in joining to avoid making lot of requests
class JoinBoost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="join",
        description="Join group handler",
        contexts=DEFAULT_CONTEXTS,
        integration_types=DEFAULT_INTEGRATION_TYPES
    )
    async def join_decorator(self, inter: ApplicationCommandInteraction):
        pass

    @join_decorator.sub_command(name="boost", description="Boost a GUILD using join")
    async def join_boost_guild(self, inter: ApplicationCommandInteraction):
        try:
            modal = BoostingModal(self.bot)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # Unresolved attribute reference 'logger' for class 'Bot' ~ pycharm
            await inter.response.send_message("An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(JoinBoost(bot))
