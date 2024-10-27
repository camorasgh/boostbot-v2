import aiohttp
import asyncio
import datetime
import disnake
import os
import random
import threading
from typing import List, Dict, Optional, Tuple

from disnake import InteractionContextTypes, ApplicationIntegrationTypes, ApplicationCommandInteraction
from disnake.ext import commands


# Constants
DEFAULT_CONTEXTS = InteractionContextTypes.all()
DEFAULT_INTEGRATION_TYPES = ApplicationIntegrationTypes.all()

class JoinBoostCounter:
    """Handles the counting of successful and failed join and boost attempts."""
    def __init__(self):
        """Initializes counters and lists for tracking joins and boosts."""
        self.JOINS = 0
        self.FAILED_JOINS = 0
        self.BOOSTS = 0
        self.FAILED_BOOSTS = 0
        self.success_tokens = {
            "joined": [],
            "boosted": []
        }
        self.failed_tokens = {
            "join_failed": [],
            "boost_failed": []
        }

    def increment_joins(self, token: str) -> None:
        """Increments the count for successful joins and logs the token."""
        self.JOINS += 1
        self.success_tokens["joined"].append(token)

    def increment_failed_joins(self, token: str) -> None:
        """Increments the count for failed joins and logs the token."""
        self.FAILED_JOINS += 1
        self.failed_tokens["join_failed"].append(token)

    def increment_boosts(self, token: str) -> None:
        """Increments the count for successful boosts and logs the token."""
        self.BOOSTS += 1
        self.success_tokens["boosted"].append(token)

    def increment_failed_boosts(self, token: str) -> None:
        """Increments the count for failed boosts and logs the token."""
        self.FAILED_BOOSTS += 1
        self.failed_tokens["boost_failed"].append(token)


class TokenManager:
    """Manages tokens and proxies, handles joins, boosts, and authorization requests."""
    def __init__(self, bot) -> None:
        """
        Initializes TokenManager with bot instance and sets up token and proxy lists.

        Args:
            bot: The Discord bot instance used for interactions and logging.
        """
        self.bot = bot
        self.tokens: List[str] = []
        self.proxies: List[str] = []
        self.failed_proxies: set = set()
        self.counter = JoinBoostCounter()
        self.authorized_users: Dict[str, Dict[str, str]] = {}

    async def load_tokens(self, amount: int) -> Optional[str]:
        """
        Loads a specified amount of tokens from a file.

        Args:
            amount: The number of tokens to load.

        Returns:
            An error message if loading fails, or None if successful.
        """
        try:
            with open("input/tokens.txt", "r") as file:
                all_tokens = [line.strip() for line in file if line.strip()]

            available_tokens = len(all_tokens) * 2
            if available_tokens < amount:
                raise Exception(f"Insufficient tokens. Available Boosts: {available_tokens}, Required: {amount}")
            tokens_to_process = all_tokens[:amount]
            remaining_tokens = all_tokens[amount:]

            with open("input/tokens.txt", "w") as file:
                for token in remaining_tokens:
                    file.write(f"{token}\n")

            self.tokens = tokens_to_process
            return None
        except FileNotFoundError:
            return "`ERR_FILE_NOT_FOUND` tokens.txt file not found."
        except Exception as e:
            return f"`ERR_UNKNOWN_EXCEPTION` Error loading tokens: {str(e)}"

    async def load_proxies(self) -> Optional[str]:
        """
        Loads proxies from a file and formats them.

        Returns:
            An error message if loading fails, or None if successful.
        """
        try:
            with open("input/proxies.txt", "r") as file:
                self.proxies = [self.format_proxy(line.strip()) for line in file if line.strip()]
            self.bot.logger.info(f"Loaded {len(self.proxies)} proxies")
            return None
        except FileNotFoundError:
            return "`ERR_FILE_NOT_FOUND` proxies.txt file not found."
        except Exception as e:
            return f"`ERR_UNKNOWN_EXCEPTION` Error loading proxies: {str(e)}"

    @staticmethod
    def format_proxy(proxy: str) -> str:
        """
        Formats a proxy string with or without authentication.

        Args:
            proxy: The raw proxy string.

        Returns:
            A formatted proxy URL.
        """
        try:
            if '@' in proxy:
                auth, ip_port = proxy.split('@')
                return f"http://{auth}@{ip_port}"
            return f"http://{proxy}"
        except Exception as e:
            return f"`ERR_PROXY_FORMATTING` Error formatting proxy: {str(e)}"

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Retrieves a random available proxy.

        Returns:
            A dictionary with HTTP and HTTPS proxy URLs or None if no proxies are available.
        """
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not available_proxies:
            self.bot.logger.info("Not enough proxies available. Using no proxy.")
            return {"http": None, "https": None}
        proxy = random.choice(available_proxies)
        return {"http": proxy, "https": proxy}

    async def join_guild(self, user_id: str, access_token: str, guild_id: str, token: str) -> Optional[str]:
        """
        Attempts to add a user to a specified guild.

        Args:
            user_id: The user's Discord ID.
            access_token: Access token to authorize the join.
            guild_id: The guild ID to join.
            token: The user’s token.

        Returns:
            An error message if the join fails, or None if successful.
        """
        try:
            join_url = f"https://discord.com/api/guilds/{guild_id}/members/{user_id}"
            headers = {
                "Authorization": f"Bot {self.bot.config['token']}",
                "Content-Type": "application/json",
            }
            data = {"access_token": access_token}
            async with aiohttp.ClientSession() as session:
                async with session.put(url=join_url, headers=headers, json=data) as response:
                    if response.status in (201, 204):
                        self.bot.logger.success(f"Successfully added user: {user_id}")
                        self.counter.increment_joins(token)
                        return None
                    else:
                        self.bot.logger.error(f"`ERR_NOT_SUCCESS` Failed to add user: {user_id}. Status code: {response.status}")
                        self.counter.increment_failed_joins(token)
                        return f"Failed to join user: {user_id}, Status: {response.status}"
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error while adding user {user_id}: {str(e)}")
            self.counter.increment_failed_joins(token)
            return f"Network error joining user: {user_id}"
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error joining guild for user {user_id}: {str(e)}")
            self.counter.increment_failed_joins(token)
            return f"Error joining user: {user_id}"

    async def _put_boost(self, token: str, guild_id: str) -> Optional[str]:
        """
        Attempts to boost a guild with the provided token.

        Args:
            token: The token used for boosting.
            guild_id: The guild ID to boost.

        Returns:
            An error message if the boost fails, or None if successful.
        """
        url = f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions"
        try:
            boost_ids = await self.__get_boost_data(token=token)
            if not boost_ids:
                self.counter.increment_failed_boosts(token)
                return f"No boost IDs available for token: {token[:10]}..."

            boosted = False
            errors = []
            for boost_id in boost_ids:
                payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
                headers = {"Authorization": token}
                async with aiohttp.ClientSession() as session: 
                    proxies = self.get_proxy()
                    session.proxies = proxies
                    async with session.put(url=url, headers=headers, json=payload) as r:
                        if r.status == 201:
                            self.bot.logger.success(f"Boosted! {token[:10]} ({guild_id})")
                            self.counter.increment_boosts(token)
                            boosted = True
                            
                        else:
                            response_json = await r.json()
                            self.bot.logger.error(f"`ERR_NOT_SUCCESS` Boost failed: {token[:10]} ({guild_id}). Response: {response_json}")
                            self.counter.increment_failed_boosts(token)
                            errors.append(f"Failed to boost token: {token[:10]}, Response: {response_json}")
            if errors:
                return "\n".join(errors)

            if not boosted:
                self.counter.increment_failed_boosts(token)
                return f"Boosting failed for token: {token[:10]}"
            return None
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during boosting with token {token[:10]}: {str(e)}")
            self.counter.increment_failed_boosts(token)
            return f"Network error boosting token: {token[:10]}"
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error boosting with token {token[:10]}: {str(e)}")
            self.counter.increment_failed_boosts(token)
            return f"Error boosting token: {token[:10]}"

    async def __get_boost_data(self, token: str) -> Optional[List[str]]:
        """
        Retrieves boost slot IDs for the given token.

        Args:
            token: The token to check for available boost slots.

        Returns:
            A list of boost slot IDs or None if none are available.
        """
        url = "https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots"
        try:
            async with aiohttp.ClientSession() as session:
                session.proxies = self.get_proxy() 
                headers = {"Authorization": token}
                async with session.get(url=url, headers=headers) as r:
                    if r.status == 200:
                        data = await r.json()
                        if len(data) > 0:
                            boost_ids = [boost['id'] for boost in data]
                            return boost_ids
                    else:
                        self.bot.logger.error(f'Unexpected status code {r.status} for token {token[:10]}...')
                return None, None
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"Network error while retrieving boost data: {str(e)}")
            return None, None
        except Exception as e:
            self.bot.logger.error(f"Error retrieving boost data: {str(e)}")
            return None, None

    async def process_single_token(self, token: str, guild_id: str) -> List[str]:
        """
        Processes a single token for joining and boosting a guild.

        Args:
            token: The token to process.
            guild_id: The guild ID to boost.

        Returns:
            A list of error messages encountered during processing.
        """
        errors = []
        try:
            user_data = await self.authorize_single_token(token, guild_id)
            if user_data:
                user_id = user_data['id']
                access_token = user_data['access_token']
                join_error = await self.join_guild(user_id, access_token, guild_id, token)
                if join_error:
                    errors.append(join_error)
                else:
                    boost_error = await self._put_boost(token, guild_id)
                    if boost_error:
                        errors.append(boost_error)
            else:
                errors.append(f"Authorization failed for token: {token[:10]}...")
        except Exception as e:
            self.bot.logger.error(f"Error processing token {token[:10]}: {str(e)}")
            errors.append(f"Processing error for token {token[:10]}...: {str(e)}")

        return errors

    async def process_tokens(self, guild_id: str, amount: int) -> List[str]:
        """
        Processes multiple tokens to join and boost a guild.

        Args:
            guild_id: The ID of the guild to join and boost.
            amount: The number of boosts required.

        Returns:
            A list of error messages encountered during processing.
        """
        try:
            load_tokens_error = await self.load_tokens(amount)
            if load_tokens_error:
                return [load_tokens_error]

            tasks = [self.process_single_token(token, guild_id) for token in self.tokens]
            results = await asyncio.gather(*tasks)

            errors = [error for error_list in results for error in error_list if error]
            return errors
        except Exception as e:
            self.bot.logger.error(f"Error processing tokens: {str(e)}")
            return [f"Error processing tokens: {str(e)}"]

    async def authorize_single_token(self, token: str, guild_id: str) -> Optional[Dict[str, str]]:
        """
        Authorizes a token for use with Discord's OAuth.

        Args:
            token: The token to authorize.
            guild_id: The guild ID for the authorization context.

        Returns:
            User data including access token if successful, or None.
        """
        try:
            login_url = f"https://discord.com/api/v9/oauth2/authorize?client_id={self.bot.config['client_id']}&response_type=code&redirect_uri={self.bot.config['redirect_uri']}&scope=identify%20guilds.join"
            async with aiohttp.ClientSession() as session:
                session.proxies = self.get_proxy()
                await session.get(login_url)
                headers = {
                    "Authorization": f"{token}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
                    "Content-Type": "application/json",
                    "Origin": "https://canary.discord.com",
                    "X-Discord-Locale": "en-US",
                    "X-Discord-Timezone": "Europe/Vienna"
                }
                payload = {
                    "permissions": "0",
                    "authorize": True,
                    "integration_type": 0,
                    "location_context": {
                        "guild_id": guild_id,
                        "channel_id": "10000",  # Example placeholder
                        "channel_type": 10000  # Example placeholder
                    }
                }
                async with session.post(url=login_url, json=payload, headers=headers) as r:
                    if r.status == 200:
                        data = await r.json()
                        location_url = data.get("location")
                        if "https://discord.com/oauth2/error?" in location_url:
                            error = location_url.split("error=")[1].split("&")[0]
                            error_description = location_url.split("error_description=")[1].split("&")[0]
                            self.bot.logger.error(f"Oauth Error: {token[:10]}... error: {error} description: {error_description}")
                            return None
                        if location_url and "code=" in location_url:
                            code = location_url.split("code=")[1].split("&")[0]
                            access_token, _ = await self._do_exchange(code, session)
                            user_data = await self.get_user_data(access_token, session)
                            user_data['access_token'] = access_token
                            self.bot.logger.success(f"Authorized: {token[:10]}...")
                            return user_data
                        else:
                            self.bot.logger.error(f"`ERR_UNHANDLED_RESPONSE` Failed to authorize token {token[:10]}...")
                            return None
                    else:
                        self.bot.logger.error(f"`ERR_NOT_SUCCESS` Failed to authorize token {token[:10]}... Status: {r.status}, Body: {await r.text()}")
                        return None
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during token authorization for {token[:10]}: {str(e)}")
            return None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error authorizing token {token[:10]}: {str(e)}")
            return None

    async def _do_exchange(self, code: str, session: aiohttp.ClientSession) -> Tuple[Optional[str], Optional[str]]:
        """
        Exchanges an authorization code for an access token and refresh token.

        Args:
            code: The authorization code received from Discord.
            session: The active aiohttp session.

        Returns:
            A tuple containing the access and refresh tokens or None.
        """
        oauth_url = "https://discord.com/api/v10/oauth2/token"
        payload = {
            "client_id": self.bot.config['client_id'],
            "client_secret": self.bot.config['client_secret'],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.bot.config['redirect_uri'],
            "scope": "identify guilds.join",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with session.post(url=oauth_url, data=payload, headers=headers) as r:
                data = await r.json()
            return data.get("access_token"), data.get("refresh_token")
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Failed to exchange code for token: {str(e)}")
            return None, None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error exchanging code for token: {str(e)}")
            return None, None

    async def get_user_data(self, access_token: str, session: aiohttp.ClientSession) -> Optional[Dict[str, str]]:
        """
        Retrieves user data using the access token.

        Args:
            access_token: The access token to authorize the request.
            session: The active aiohttp session.

        Returns:
            A dictionary of user data if successful, or None.
        """
        users_url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with session.get(users_url, headers=headers) as r:
                return await r.json()
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Failed to get user data: {str(e)}")
            return None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error getting user data: {str(e)}")
            return None

    def save_results(self, guild_id: str, amount: int) -> None:
        """
        Saves results of the join and boost processes to output files.

        Args:
            guild_id: The guild ID for which results are saved.
            amount: The number of boosts processed.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        folder_name = f"./output/{timestamp}-{guild_id}-({amount}x)"
        os.makedirs(folder_name, exist_ok=True)

        with open(os.path.join(folder_name, "successful_joins.txt"), "w") as file:
            for token in self.counter.success_tokens["joined"]:
                file.write(f"{token}\n")

        with open(os.path.join(folder_name, "failed_joins.txt"), "w") as file:
            for token in self.counter.failed_tokens["join_failed"]:
                file.write(f"{token}\n")

        with open(os.path.join(folder_name, "successful_boosts.txt"), "w") as file:
            for token in self.counter.success_tokens["boosted"]:
                file.write(f"{token}\n")

        with open(os.path.join(folder_name, "failed_boosts.txt"), "w") as file:
            for token in self.counter.failed_tokens["boost_failed"]:
                file.write(f"{token}\n")


class BoostingModal(disnake.ui.Modal):
    """Displays a modal for user input on guild boosting details."""
    def __init__(self, bot) -> None:
        """
        Initializes the modal with the required input fields.

        Args:
            bot: The bot instance for interacting with Discord.
        """
        self.bot: commands.InteractionBot = bot
        components = [
            disnake.ui.TextInput(
                label="Guild ID",
                placeholder="Enter the guild ID",
                custom_id="boosting.guild_id",
                style=disnake.TextInputStyle.short,
                min_length=3,
                max_length=30,
            ),
            disnake.ui.TextInput(
                label="Amount",
                placeholder="The amount of boosts",
                custom_id="boosting.amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=3
            ),
        ]
        super().__init__(title="OAUTH Booster", components=components)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        """
        Handles the modal submission by initiating the boosting process.

        Args:
            inter: The interaction object from the modal submission.
        """
        await inter.response.defer(ephemeral=True)
        try:
            guild_id = inter.text_values['boosting.guild_id']
            # Check if bot is in the guild
            for guild in self.bot.guilds:
                if guild.id == int(guild_id):
                    break
            else:
                await inter.followup.send("`ERR_NOT_IN_GUILD` Bot is not in the specified guild.", ephemeral=True)
                return
            amount = int(inter.text_values['boosting.amount'])
            if amount % 2 != 0:
                await inter.followup.send("`ERR_ODD_AMOUNT` Amount must be an even number.", ephemeral=True)
                return

            token_manager = TokenManager(self.bot)
            self.bot.logger.info(f"Boosting {amount} users to guild {guild_id}")
            errors = await token_manager.process_tokens(guild_id, amount)
            token_manager.save_results(guild_id, amount)

            if errors:
                error_msg = "\n".join(errors)
                await inter.followup.send(f"Errors occurred during boosting:\n{error_msg}", ephemeral=True)
            else:
                embed = disnake.Embed(
                    title="Boosting Results",
                    description=(
                        f"Joined: {token_manager.counter.JOINS}\n"
                        f"Not Joined: {token_manager.counter.FAILED_JOINS}\n"
                        f"Boosted: {token_manager.counter.BOOSTS}\n"
                        f"Not Boosted: {token_manager.counter.FAILED_BOOSTS}"
                    ),
                    color=disnake.Color.green(),
                )
                await inter.followup.send(embed=embed)
        except Exception as e:
            self.bot.logger.error(str(e))
            await inter.followup.send("`ERR_UNKNOWN_EXCEPTION` An error occurred while boosting.", ephemeral=True)


class OAuthBoost(commands.Cog):
    """Cog for handling OAuth-based guild boosting commands."""
    def __init__(self, bot: commands.Bot):
        """
        Initializes the cog with the bot instance.

        Args:
            bot: The bot instance for interaction with Discord.
        """
        self.bot = bot

    @commands.slash_command(
        name="oauth",
        description="OAUTH group handler",
        contexts=DEFAULT_CONTEXTS,
        integration_types=DEFAULT_INTEGRATION_TYPES
    )
    async def oauth_decorator(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """Slash command decorator for grouping OAuth-related commands."""
        pass

    @oauth_decorator.sub_command(name="boost", description="Boost a guild using OAUTH")
    async def oauth_boost_guild(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """
        Slash command for initiating the guild boosting modal.

        Args:
            inter: The interaction object from the command.
        """
        try:
            modal = BoostingModal(self.bot)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e))
            await inter.response.send_message("`ERR_UNKNOWN_EXCEPTION` An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(OAuthBoost(bot))
