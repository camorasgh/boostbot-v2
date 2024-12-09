import asyncio
import base64
import os
import random
import re
import string
import tls_client

from datetime import datetime
from disnake import InteractionContextTypes, ApplicationIntegrationTypes, ApplicationCommandInteraction
from disnake import ModalInteraction, ui, TextInputStyle, Embed
from disnake.ext import commands
from typing import Dict

from core.misc_boosting import TokenTypeError, load_config, get_headers, Proxies
from core import database

# Constants
DEFAULT_CONTEXTS = InteractionContextTypes.all()
DEFAULT_INTEGRATION_TYPES = ApplicationIntegrationTypes.all()


class Filemanager:
    @staticmethod
    async def load_tokens(amount : int, token_type : str):
        """
        Load a specified number of tokens from a file.
        
        Args:
            amount (int):       The number of tokens to load.
            token_type (str):   The token type to load (1m/3m)

        Returns:
            list: A list of loaded tokens.
            
        Raises:
            ValueError: If the number of tokens in the file is less than the specified amount.
        """
        tokens = []
        if token_type == "1m":
            file_name = "1m_tokens.txt"
        elif token_type == "3m":
            file_name = "3m_tokens.txt"
        else:
            raise TokenTypeError(f"Invalid token type: {token_type}. Choose '1m' or '3m'.")

        with open(f"./input/{file_name}", "r") as file:
            token_list = file.readlines()
            for token in token_list:
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
    @staticmethod
    async def save_results(guild_invite: str, amount: int, join_results: dict, boost_results: dict, boost_key = None, user_id = None) -> None:
        """
        Saves results of the join and boost processes to output files.
        Args:
            guild_invite: The guild Invite for which results are saved.
            amount: The number of boosts processed.
            join_results: The results of the joining attempts (successful and failed).
            boost_results: The results of the boosting attempts (successful and failed).
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_guild_invite = re.sub(r'[<>:"/\\|?*]', '_', guild_invite) # in order to avoid syntax for file names / folder names
        folder_name = f"./output/{timestamp}-{safe_guild_invite}-({amount}x)"
        os.makedirs(folder_name, exist_ok=True)

        with open(os.path.join(folder_name, "successful_joins.txt"), "w") as file:
            for token, success in join_results.items():
                if success:
                    file.write(f"{token}\n")

        with open(os.path.join(folder_name, "failed_joins.txt"), "w") as file:
            for token, success in join_results.items():
                if not success:
                    file.write(f"{token}\n")

        with open(os.path.join(folder_name, "successful_boosts.txt"), "w") as file:
            for token, success in boost_results.items():
                if success:
                    file.write(f"{token}\n")

        with open(os.path.join(folder_name, "failed_boosts.txt"), "w") as file:
            for token, success in boost_results.items():
                if not success:
                    file.write(f"{token}\n")

        if boost_key and user_id:
            with open(os.path.join(folder_name, "boost_key_usage.txt"), "w") as file:
                file.write(f"Boost Key: {boost_key}\nUser ID: {user_id}\nTimestamp: {timestamp}")
        else:
            with open(os.path.join(folder_name, "boost_key_usage.txt"), "w") as file:
                file.write(f"None used")


class Tokenmanager:
    def __init__(self, bot):
        self.bot = bot
        # PLEASE DO NOT CHANGE THIS UNLESS I GIVE YOU PERMISSION, THIS FUCKING CLIENT IDENTIFIER IS THE REASON OF MY MENTAL ISSUES
        self.client = tls_client.Session(
            client_identifier="chrome112", # type: ignore
            random_tls_extension_order=True
        )
        self.join_results: Dict[str, bool] = {}
        self.boost_results: Dict[str, bool] = {}
        self.Proxies = Proxies()
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

    async def get_boost_ids(self, token:str, proxy_:str):
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

            elif response.status_code == 403 and r_json['message'] == "You need to verify your account in order to perform this action.":
                self.bot.logger.error('Flagged Token ({})'.format(token))

            elif response.status_code == 400 and r_json['captcha_key'] == ['You need to update your app to join this server.']:
                self.bot.logger.error('\033[0;31m Hcaptcha ({})'.format(token))

            elif r_json['message'] == "404: Not Found":
                self.bot.logger.error("No Nitro") # D:

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
            'session_id': ''.join(random.choice(string.ascii_lowercase) + random.choice(string.digits) for _ in range(16))
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
        elif response.status_code == 403 and r_json['message'] == "You need to verify your account in order to perform this action.":
            self.bot.logger.error('Flagged Token ({})'.format(token))
            self.not_joined_count += 1
            return False, None
        elif response.status_code == 400 and r_json['captcha_key'] == ['You need to update your app to join this server.']:
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
            if r.status_code  == 200:
                data = r.json()
                if len(data) > 0:
                    boost_ids = [boost['id'] for boost in data]
                    return boost_ids, self.client
            elif r.status_code == 401:
                self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Invalid Token ({token[:10]}...)')
            elif r.status_code == 403:
                self.bot.logger.error(f'`ERR_TOKEN_VALIDATION` Flagged Token ({token[:10]}...)')
            else:
                self.bot.logger.error(f'`ERR_UNEXPECTED_STATUS` Unexpected status code {r.status_code} for token {token[:10]}...')
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
                        self.bot.logger.error(f"`ERR_COOLDOWN` Boosts Cooldown {token[:10]}")
                        break
                    self.bot.logger.error(f"`ERR_NOT_SUCCESS` Boost failed: {token[:10]} ({guild_id}). Response: {response_json}")
            return boosted

        except tls_client.sessions.TLSClientExeption as e:
            self.bot.logger.error(f"`ERR_CLIENT_EXCEPTION` Network error during boosting with token {token[:10]}: {str(e)}")
            return False

        except Exception as e:
            self.bot.logger.error(f"`ERR_UNKNOWN_EXCEPTION` Error boosting with token {token[:10]}: {str(e)}")
            return False

    async def process_single_token(self, token: str, guild_invite: str):
        """
        Starts single token process from getting a proxy to boosting the server
        :param token: account token
        :param guild_invite: invite to the server
        :return:
        """
        try:
            
            selected_proxy = await self.Proxies.get_random_proxy(self.bot)
            user_id = str(await self.get_userid(token=token))
            joined, guild_id = await self.join_guild(token=token, inv=guild_invite, proxy_=selected_proxy) # still needs to be made | possibly done
            if joined:
                boost_data = await self.get_boost_data(token=token, selected_proxy=selected_proxy)
                if boost_data is None:
                    self.bot.logger.error("Failed to retrieve boost data.")
                    return
                boost_ids, session = boost_data
                boosted = await self.boost_server(token=token, guild_id=guild_id, boost_ids=boost_ids)
                self.boost_results[user_id] = False if boosted == False else True
                pass
            else:
                self.boost_results[user_id] = False
        except Exception as e:
            self.bot.logger.error(f"Error processing token {token[:10]}...: {str(e)}")

    async def send_summary_embed(self, inter: ApplicationCommandInteraction, guild_invite, amount, boost_data=None):
        """
        Sends an embed summarizing the join and boost results.
        Resets the stats afterward to avoid stale data.
        Params:
        :param inter: Interaction, Provided by Discord
        :param guild_invite: The guild invite
        :param amount: The amount of boosts
        :param boost_data: The boost data (boost key, remaining boosts) if available
        """

        async def censor_token(token: str) -> str:
            """Censors the token to show only the part till the first dot"""
            parts = token.split('.')
            return f"{parts[0]}.***" if len(parts) > 1 else "***"
        embed = Embed(
            title="Boosting Operation Summary",
            color=0x00FF00 if self.joined_count > 0 else 0xFF0000,  # Green if any joined, red if none
        )
        embed.add_field(
            name="Joining Results",
            value=f"**Joined Successfully:** {self.joined_count}\n"
                  f"**Failed to Join:** {self.not_joined_count}",
            inline=False
        )
        if self.join_results:
            join_results_str = "\n".join(
                [f"• `{await censor_token(token)}`: {'✅' if success else '❌'}" for token, success in
                 self.join_results.items()]
            )
            embed.add_field(
                name="Join Results Details",
                value=join_results_str[:1024],  # Discord field size limit
                inline=False
            )
        success_boosts = sum(1 for success in self.boost_results.values() if success) * 2
        failed_boosts = (len(self.boost_results) - success_boosts) * 2
        embed.add_field(
            name="Boosting Results",
            value=f"**Successful Boosts:** {success_boosts}\n"
                  f"**Failed Boosts:** {failed_boosts}",
            inline=False
        )
        config = await load_config()

        if boost_data:
            boost_key, remaining_boosts = boost_data
            boosts_needed_to_remove = remaining_boosts - success_boosts
            success = database.remove_boost_from_key(boost_key=boost_key,
                                                     boosts=boosts_needed_to_remove,
                                                     database_name=config["boost_keys_database"]["name"]
                                                     )

        
        await Filemanager.save_results(guild_invite, amount, self.join_results, self.boost_results, boost_key if boost_data else None, inter.author.id if boost_data else None) # Possible error here
        if config["logging"]["boost_dm_notifications"]:
            await inter.author.send(embed=embed)
        if config["logging"]["enabled"]:
            log_server_id = config["logging"]["server_id"]
            log_channel_id = config["logging"]["channel_id"]
            logserver = self.bot.get_guild(log_server_id)
            logchannel = logserver.get_channel(log_channel_id)
            await logchannel.send(embed=embed)
        await inter.followup.send(embed=embed, ephemeral=True)

    async def process_tokens(self, inter, guild_invite: str, amount: int, token_type: str, boost_data=None):
        """
        Processes the all the tokens aka gathers all tasks for asyncio to process each one afterwards
        :param inter: Interaction in case of not enough tokens
        :param guild_invite: guild invite from modal
        :param amount: amount to boost
        :param token_type: type of token (1m/3m)
        :param boost_data: boost data if available
        """
        tokens_to_process = []
        try:
            tokens_to_process = await Filemanager.load_tokens(amount, token_type)
        except ValueError as e:
            if "Not enough tokens in" in str(e):
                await inter.followup.send("`ERR_INSUFFICIENT_TOKENS` Amount is higher than the amount of tokens available.", ephemeral=True)
                return
        except TokenTypeError:
            await inter.followup.send("`ERR_INVALID_TOKEN_TYPE` Please use a valid token type such as 1m/3m")
            return

        tasks = [self.process_single_token(token, guild_invite) for token in tokens_to_process]
        await asyncio.gather(*tasks)
        await self.send_summary_embed(inter, guild_invite, amount, boost_data if boost_data else None)


class BoostingModal(ui.Modal):
    """
    Handles the modal submission by initiating the boosting process.

    Bot: The bot instance.
    """
    def __init__(self, bot: commands.InteractionBot, boost_data = None) -> None:
        self.bot = bot
        self.boost_data = boost_data
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
            ui.TextInput(
                label="Token Type (1m for 1 Month, 3m for 3 Months)",
                placeholder="Enter '1m' or '3m'",
                custom_id="boosting.token_type",
                style=TextInputStyle.short,
                min_length=2,
                max_length=2,
            ),
        ]
        super().__init__(title="Join Booster", components=components)

    async def callback(self, interaction: ModalInteraction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            guild_invite = interaction.text_values['boosting.guild_invite']
            amount = int(interaction.text_values['boosting.amount'])
            token_type = interaction.text_values['boosting.token_type']

            if amount % 2 != 0:
                await interaction.followup.send("`ERR_ODD_AMOUNT` Amount must be an even number.", ephemeral=True)
                return
            
            if self.boost_data:
                boost_key, remaining_boosts = self.boost_data
                if amount > remaining_boosts:
                    await interaction.followup.send(
                        f"`ERR_INSUFFICIENT_BOOSTS` Your boost key `{boost_key:4}` only allows "
                        f"{remaining_boosts} boosts, but you requested {amount}.",
                        ephemeral=True,
                    )
                    return

            
            tkn = Tokenmanager(self.bot)
            self.bot.logger.info(f"Boosting {int(amount / 2)} users to guild {guild_invite}") # type: ignore
            await tkn.process_tokens(inter=interaction, guild_invite=guild_invite, amount=amount, token_type=token_type, boost_data=self.boost_data)

        except Exception as e:
            self.bot.logger.error(str(e)) # type: ignore
            await interaction.followup.send("`ERR_UNKNOWN_EXCEPTION` An error occurred while boosting.", ephemeral=True)


class JoinBoost(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
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
        config = await load_config()
        owner_ids = config["owner_ids"]
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
            modal = BoostingModal(self.bot,boost_data if boost_data else None)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # type: ignore
            await inter.response.send_message("`ERR_UNKNOWN_EXCEPTION` An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(JoinBoost(bot))