import asyncio
import datetime
import os
import tls_client
from typing import List, Dict, Optional, Tuple

import disnake
from disnake import Embed, InteractionContextTypes, ApplicationIntegrationTypes
from disnake.ext import commands

from core.misc_boosting import TokenTypeError, load_config, Proxies
from core import database

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
        self.counter = JoinBoostCounter()
        self.authorized_users: Dict[str, Dict[str, str]] = {}
        self.client = tls_client.Session(
            client_identifier="chrome112", # type: ignore
            random_tls_extension_order=True
        )
        self.Proxies = Proxies()

    async def load_tokens(self, amount: int, token_type: str) -> Optional[str]:
        """
        Loads a specified amount of tokens from a file.

        Args:
            :param amount: The number of tokens to load.
            :param token_type: Type of the token (1m/3m).

        Returns:
            An error message if loading fails, or None if successful.
        """
        
        if token_type == "1m":
            file_name = "1m_tokens.txt"
        elif token_type == "3m":
            file_name = "3m_tokens.txt"
        else:
            raise TokenTypeError(f"Invalid token type: {token_type}. Choose '1m' or '3m'.")#
        try:
            with open(f"./input/{file_name}", "r") as file:
                all_tokens = [line.strip() for line in file if line.strip()]

            available_tokens = len(all_tokens) * 2
            if available_tokens < amount:
                raise Exception(f"Insufficient tokens. Available Boosts: {available_tokens}, Required: {amount}")
            tokens_to_process = all_tokens[:amount]
            remaining_tokens = all_tokens[amount:]

            with open(f"./input/{file_name}", "r") as file:
                for token in remaining_tokens:
                    file.write(f"{token}\n")

            self.tokens = tokens_to_process
            return None
        except FileNotFoundError:
            return "`ERR_FILE_NOT_FOUND` tokens.txt file not found."
        except Exception as e:
            return f"`ERR_UNKNOWN_EXCEPTION` Error loading tokens: {str(e)}"

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

            response = self.client.put(url=join_url, headers=headers, json=data)

            if response.status_code in (201, 204):
                self.bot.logger.success(f"Successfully added user: {user_id}")
                self.counter.increment_joins(token)
                return None
            else:
                self.bot.logger.error(f"`ERR_NOT_SUCCESS` Failed to add user: {user_id}. Status code: {response.status_code}")
                self.counter.increment_failed_joins(token)
                return f"Failed to join user: {user_id}, Status: {response.status_code}"

        except tls_client.sessions.TLSClientExeption as e:
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
            boost_ids = self.__get_boost_data(token=token)
            if not boost_ids:
                self.counter.increment_failed_boosts(token)
                return f"No boost IDs available for token: {token[:10]}..."

            boosted = False
            errors = []

            for boost_id in boost_ids:
                payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
                headers = {"Authorization": token}

                try:
                    proxy = await self.Proxies.get_random_proxy(self.bot)()
                    response = self.client.put(
                        url=url,
                        headers=headers,
                        json=payload,
                        proxies={"http": proxy, "https": proxy} if proxy else None,
                    )

                    if response.status_code == 201:
                        self.bot.logger.success(f"Boosted! {token[:10]} ({guild_id})")
                        self.counter.increment_boosts(token)
                        boosted = True
                    else:
                        response_json = response.json()
                        self.bot.logger.error(
                            f"`ERR_NOT_SUCCESS` Boost failed: {token[:10]} ({guild_id}). Response: {response_json}"
                        )
                        self.counter.increment_failed_boosts(token)
                        errors.append(f"Failed to boost token: {token[:10]}, Response: {response_json}")
                except tls_client.exceptions.TLSClientExeption as e:
                    self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during boosting with token {token[:10]}: {str(e)}")
                    self.counter.increment_failed_boosts(token)
                    errors.append(f"Network error boosting token: {token[:10]}")
                except Exception as e:
                    self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error boosting with token {token[:10]}: {str(e)}")
                    self.counter.increment_failed_boosts(token)
                    errors.append(f"Error boosting token: {token[:10]}")

            if errors:
                return "\n".join(errors)

            if not boosted:
                self.counter.increment_failed_boosts(token)
                return f"Boosting failed for token: {token[:10]}"
            return None

        except tls_client.exceptions.TLSClientExeption as e:
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
            proxy = await self.Proxies.get_random_proxy(self.bot)()
            headers = {"Authorization": token}

            response = self.client.get(
                url=url,
                headers=headers,
                proxies={"http": proxy, "https": proxy} if proxy else None,
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    boost_ids = [boost["id"] for boost in data]
                    return boost_ids
            else:
                self.bot.logger.error(f"Unexpected status code {response.status_code} for token {token[:10]}...")
            return None
        except tls_client.exceptions.TLSClientExeption as e:
            self.bot.logger.error(f"Network error while retrieving boost data: {str(e)}")
            return None
        except Exception as e:
            self.bot.logger.error(f"Error retrieving boost data: {str(e)}")
            return None


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

    async def process_tokens(self, guild_ids: List[str], amount: int, token_type: str) -> List[str]:
        """
        Processes multiple tokens to join and boost a guild.

        Args:
            :param guild_ids: The IDs of the guild to join and boost.
            :param amount: The number of boosts required.
            :param token_type: Type of token (1m/3m).

        Returns:
            A list of error messages encountered during processing.
        """
        try:
            for guild_id in guild_ids:
                load_tokens_error = await self.load_tokens(amount, token_type)
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
            proxy = await self.Proxies.get_random_proxy(self.bot)()
            response = self.client.get(login_url, proxies={"http": proxy, "https": proxy} if proxy else None)
            
            if response.status_code != 200:
                self.bot.logger.error(f"`ERR_NOT_SUCCESS` Failed to request login URL for token {token[:10]}...")
                return None

            headers = {
                "Authorization": token,
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
            response = self.client.post(login_url, json=payload, headers=headers, proxies={"http": proxy, "https": proxy} if proxy else None)
            
            if response.status_code == 200:
                data = response.json()
                location_url = data.get("location")
                
                if "https://discord.com/oauth2/error?" in location_url:
                    error = location_url.split("error=")[1].split("&")[0]
                    error_description = location_url.split("error_description=")[1].split("&")[0]
                    self.bot.logger.error(f"Oauth Error: {token[:10]}... error: {error} description: {error_description}")
                    return None

                if location_url and "code=" in location_url:
                    code = location_url.split("code=")[1].split("&")[0]
                    access_token, _ = self._do_exchange(code, self.client)
                    user_data = self.get_user_data(access_token, self.client)
                    user_data['access_token'] = access_token
                    self.bot.logger.success(f"Authorized: {token[:10]}...")
                    return user_data
                else:
                    self.bot.logger.error(f"`ERR_UNHANDLED_RESPONSE` Failed to authorize token {token[:10]}...")
                    return None
            else:
                self.bot.logger.error(f"`ERR_NOT_SUCCESS` Failed to authorize token {token[:10]}... Status: {response.status_code}, Body: {response.text}")
                return None

        except tls_client.exceptions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during token authorization for {token[:10]}: {str(e)}")
            return None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error authorizing token {token[:10]}: {str(e)}")
            return None

    async def _do_exchange(self, code: str, session: tls_client.Session) -> Tuple[Optional[str], Optional[str]]:
        """
        Exchanges an authorization code for an access token and refresh token.

        Args:
            code: The authorization code received from Discord.
            session: The active tls_client session.

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
            response = session.post(oauth_url, data=payload, headers=headers, proxies={"http": await self.Proxies.get_random_proxy(self.bot)(), "https": await self.Proxies.get_random_proxy(self.bot)()})
            data = response.json()

            return data.get("access_token"), data.get("refresh_token")
        except tls_client.exceptions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Failed to exchange code for token: {str(e)}")
            return None, None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error exchanging code for token: {str(e)}")
            return None, None


    async def get_user_data(self, access_token: str, session: tls_client.Session) -> Optional[Dict[str, str]]:
        """
        Retrieves user data using the access token.

        Args:
            access_token: The access token to authorize the request.
            session: The active tls_client session.

        Returns:
            A dictionary of user data if successful, or None.
        """
        users_url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = session.get(users_url, headers=headers, proxies={"http": await self.Proxies.get_random_proxy(self.bot)(), "https": await self.Proxies.get_random_proxy(self.bot)()})
            return response.json()
        except tls_client.exceptions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Failed to get user data: {str(e)}")
            return None
        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error getting user data: {str(e)}")
            return None


    def save_results(self, guild_ids: List[str], amount: int, boost_key = None, user_id = None) -> None:
        """
        Saves results of the join and boost processes to output files.

        Args:
            guild_ids: The guild ID for which results are saved.
            amount: The number of boosts processed.
        """
        for guild_id in guild_ids:
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
            
            if boost_key and user_id:
                with open(os.path.join(folder_name, "boost_key_usage.txt"), "w") as file:
                    file.write(f"Boost Key: {boost_key}\nUser ID: {user_id}\nTimestamp: {timestamp}")
            else:
                with open(os.path.join(folder_name, "boost_key_usage.txt"), "w") as file:
                    file.write(f"None used")


class BoostingModal(disnake.ui.Modal):
    """Displays a modal for user input on guild boosting details."""
    def __init__(self, bot, boost_data, mass_boost: bool = False) -> None:
        """
        Initializes the modal with the required input fields.

        Args:
            bot: The bot instance for interacting with Discord.
        """
        self.bot: commands.InteractionBot = bot
        self.mass_boost: bool = mass_boost
        self.boost_data = boost_data
        components = [
            disnake.ui.TextInput(
                label="Guild IDs" if mass_boost else "Guild ID",
                placeholder="Enter Guild IDs, separated by commas" if mass_boost else "Enter the Guild ID",
                custom_id="boosting.guild_id",
                style=disnake.TextInputStyle.paragraph if mass_boost else disnake.TextInputStyle.short,
                min_length=3,
                max_length=1000 if mass_boost else 30,
            ),
            disnake.ui.TextInput(
                label="Amount",
                placeholder="The amount of boosts for each Guild" if mass_boost else "The amount of boosts",
                custom_id="boosting.amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=3
            ),
            disnake.ui.TextInput(
                label="Token Type (1m for 1 Month, 3m for 3 Months)",
                placeholder="Enter '1m' or '3m'",
                custom_id="boosting.token_type",
                style=disnake.TextInputStyle.short,
                min_length=2,
                max_length=2,
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
            guild_ids = [gid.strip() for gid in guild_id.split(",")] if self.mass_boost else [guild_id]
            amount = int(inter.text_values['boosting.amount'])
            token_type = inter.text_values['boosting.token_type']

            if amount % 2 != 0:
                await inter.followup.send("`ERR_ODD_AMOUNT` Amount must be an even number.", ephemeral=True)
                return
            
            if self.boost_data:
                boost_key, remaining_boosts = self.boost_data
                if amount > remaining_boosts:
                    await inter.followup.send(
                        f"`ERR_INSUFFICIENT_BOOSTS` Your boost key `{boost_key:4}` only allows "
                        f"{remaining_boosts} boosts, but you requested {amount}.",
                        ephemeral=True,
                    )
                    return

            # Check if bot is in the guild
            for guild_id in guild_ids:
                for guild in self.bot.guilds:
                    if guild.id == int(guild_id):
                        break
                else:
                    await inter.followup.send("`ERR_NOT_IN_GUILD` Bot is not in the specified guild.", ephemeral=True)
                    return

            token_manager = TokenManager(self.bot)
            self.bot.logger.info(f"Boosting {amount} users to guilds {guild_ids}" if self.mass_boost else f"Boosting {amount} users to guild {guild_id}") # type: ignore
            errors = await token_manager.process_tokens(guild_ids, amount, token_type, boost_data=self.boost_data)
            config = await load_config()

            if self.boost_data:
                boost_key, remaining_boosts = self.boost_data
                boosts_needed_to_remove = len(self.success_tokens["boosted"])
                removed_boosts_success = database.remove_boost_from_key(boost_key=boost_key,
                                                        boosts=boosts_needed_to_remove,
                                                        database_name=config["boost_keys_database"]["name"]
                                                        )
                    
            token_manager.save_results(guild_ids, amount,  boost_key if self.boost_data else None, inter.author.id if self.boost_data else None) # Possible Error here

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
                        f"Not Boosted: {token_manager.counter.FAILED_BOOSTS}\n"
                        f"Removed boosts from key: {removed_boosts_success}",
                    ),
                    color=disnake.Color.green(),
                )
                if config["logging"]["boost_dm_notifications"]:
                    await inter.author.send(embed=embed)
                if config["logging"]["enabled"]:
                    log_server_id = config["logging"]["server_id"]
                    log_channel_id = config["logging"]["channel_id"]
                    logserver = self.bot.get_guild(log_server_id)
                    logchannel = logserver.get_channel(log_channel_id)
                    await logchannel.send(embed=embed)
                await inter.followup.send(embed=embed)
        except Exception as e:
            self.bot.logger.error(str(e)) # type: ignore
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
        config = await load_config()
        owner_ids = config['owner_ids']
        boost_data = await database.check_user_has_valid_boost_key(user_id=inter.author.id, 
                                                                   database_name=config["boost_keys_database"]["name"]
                                                                   ) if config["boost_keys_database"]["enabled"] else None
        if inter.author.id not in owner_ids and boost_data is None:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            modal = BoostingModal(bot=self.bot, mass_boost=False, boost_data=boost_data)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # type: ignore
            await inter.response.send_message("`ERR_UNKNOWN_EXCEPTION` An error occurred while preparing the boost modal.", ephemeral=True)

    @oauth_decorator.sub_command(name="mass_boost", description="Mass Boost a guild using OAUTH")
    async def oauth_massboost_guild(self, inter: disnake.ApplicationCommandInteraction) -> None:
        """
        Slash command for initiating the guild boosting modal.

        Args:
            inter: The interaction object from the command.
        """
        config = await load_config()
        owner_ids = config['owner_ids']
        boost_data = await database.check_user_has_valid_boost_key(user_id=inter.author.id, 
                                                                   database_name=config["boost_keys_database"]["name"]
                                                                   )
        if inter.author.id not in owner_ids and not boost_data:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            modal = BoostingModal(bot=self.bot, mass_boost=False, boost_data=boost_data)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # type: ignore
            await inter.response.send_message("`ERR_UNKNOWN_EXCEPTION` An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(OAuthBoost(bot))