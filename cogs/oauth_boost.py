import asyncio
import random
# threading currently unused (?)
import threading
from typing import List, Dict, Optional

import aiohttp
import disnake
from disnake import InteractionContextTypes, ApplicationIntegrationTypes, ApplicationCommandInteraction
from disnake.ext import commands

# Constants

DEFAULT_CONTEXTS = [InteractionContextTypes.private_channel, InteractionContextTypes.guild]
DEFAULT_INTEGRATION_TYPES = [ApplicationIntegrationTypes.guild, ApplicationIntegrationTypes.user]


class TokenManager:
    def __init__(self, bot):
        self.bot = bot
        self.tokens: List[str] = []
        self.proxies: List[str] = []
        self.failed_proxies: set = set()
        self.join_results: Dict[str, bool] = {}
        self.boost_results: Dict[str, bool] = {}
        self.authorized_users: Dict[str, Dict[str, str]] = {}

    async def load_tokens(self, amount: int) -> List[str]:
        try:
            with open("./input/tokens.txt", "r") as file:
                all_tokens = [line.strip() for line in file if line.strip()]

            tokens_to_process = all_tokens[:amount]
            remaining_tokens = all_tokens[amount:]

            with open("./input/tokens.txt", "w") as file:
                for token in remaining_tokens:
                    file.write(f"{token}\n")

            self.bot.logger.info(f"Loaded {len(tokens_to_process)} tokens for processing")
            return tokens_to_process
        except FileNotFoundError:
            self.bot.logger.error("tokens.txt file not found.")
            return []
        except Exception as e:
            self.bot.logger.error(f"Error loading tokens: {str(e)}")
            return []

    async def load_proxies(self) -> None:
        try:
            with open("./input/proxies.txt", "r") as file:
                self.proxies = [self.format_proxy(line.strip()) for line in file if line.strip()]
            self.bot.logger.info(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            self.bot.logger.error("proxies.txt file not found.")
        except Exception as e:
            self.bot.logger.error(f"Error loading proxies: {str(e)}")

    @staticmethod
    def format_proxy(proxy: str) -> str:
        if '@' in proxy:
            auth, ip_port = proxy.split('@')
            return f"http://{auth}@{ip_port}"
        return f"http://{proxy}"

    def get_proxy(self) -> Optional[Dict[str, str]]:
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not available_proxies:
            return None
        proxy = random.choice(available_proxies)
        return {"http": proxy, "https": proxy}

    async def join_guild(self, user_id: str, access_token: str, guild_id: str) -> bool:
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
                        return True
                    else:
                        self.bot.logger.error(f"Failed to add user: {user_id}. Status code: {response.status}")
                        return False
        except Exception as e:
            self.bot.logger.error(f"Error joining guild for user {user_id}: {str(e)}")
            return False

    async def _put_boost(self, token: str, guild_id: str) -> bool:
        url = f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions"
        boost_ids, session = await self.__get_boost_data(token=token)
        if not boost_ids:
            return False

        boosted = False
        for boost_id in boost_ids:
            payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
            headers = {"Authorization": token}
            async with session.put(url=url, headers=headers, json=payload) as r:
                if r.status == 201:
                    self.bot.logger.success(f"Boosted! {token} ({guild_id})")
                    boosted = True
                    break
                else:
                    response_json = await r.json()
                    self.bot.logger.error(f"Boost failed: {token} ({guild_id}). Response: {response_json}")

        return boosted

    async def __get_boost_data(self, token: str):
        url = "https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots"
        async with aiohttp.ClientSession() as session:
            session.proxies = self.get_proxy()
            headers = {"Authorization": token}
            async with session.get(url=url, headers=headers) as r:
                if r.status == 200:
                    data = await r.json()
                    if len(data) > 0:
                        boost_ids = [boost['id'] for boost in data]
                        return boost_ids, session
                elif r.status == 401:
                    self.bot.logger.error(f'Invalid Token ({token})')
                elif r.status == 403:
                    self.bot.logger.error(f'Flagged Token ({token})')
                else:
                    self.bot.logger.error(f'Invalid response ({await r.json()})')
                return None, None

    async def process_single_token(self, token: str, guild_id: str):
        try:
            user_data = await self.authorize_single_token(token, guild_id)
            if user_data:
                user_id = user_data['id']
                access_token = user_data['access_token']
                joined = await self.join_guild(user_id, access_token, guild_id)
                self.join_results[user_id] = joined
                if joined:
                    boosted = await self._put_boost(token, guild_id)
                    self.boost_results[user_id] = boosted
                else:
                    self.boost_results[user_id] = False
        except Exception as e:
            self.bot.logger.error(f"Error processing token {token[:10]}...: {str(e)}")

    async def process_tokens(self, guild_id: str, amount: int):
        tokens_to_process = await self.load_tokens(amount)
        tasks = [self.process_single_token(token, guild_id) for token in tokens_to_process]
        await asyncio.gather(*tasks)

    async def authorize_single_token(self, token: str, guild_id: str) -> Optional[Dict[str, str]]:
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
                        if location_url and "code=" in location_url:
                            code = location_url.split("code=")[1].split("&")[0]
                            access_token, _ = await self._do_exchange(code, session)
                            user_data = await self.get_user_data(access_token, session)
                            user_data['access_token'] = access_token
                            self.bot.logger.success(f"Authorized: {token}")
                            return user_data
                        else:
                            self.bot.logger.error(f"Failed to authorize token {token[:10]}...")
                            return None

        except Exception as e:
            self.bot.logger.error(f"Error authorizing token {token[:10]}...: {str(e)}")
            return None

    async def _do_exchange(self, code: str, session: aiohttp.ClientSession):
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
            self.bot.logger.error(f"Failed to exchange code for token: {str(e)}")
            return None, None

    async def get_user_data(self, access_token: str, session: aiohttp.ClientSession):
        users_url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with session.get(users_url, headers=headers) as r:
                return await r.json()
        except aiohttp.ClientError as e:
            self.bot.logger.error(f"Failed to get user data: {str(e)}")
            return None


class BoostingModal(disnake.ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="Guild Invite",
                placeholder="Enter the guild Invite",
                custom_id="boosting.guild_invite",
                style=disnake.TextInputStyle.short,
                min_length=18,
                max_length=19,
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
        await inter.response.defer(ephemeral=True)
        try:
            guild_id = inter.text_values['boosting.guild_invite']
            amount = int(inter.text_values['boosting.amount'])
            token_manager = TokenManager(self.bot)
            await token_manager.process_tokens(guild_id, amount)

            joined_count = sum(token_manager.join_results.values())
            boosted_count = sum(token_manager.boost_results.values())
            embed = disnake.Embed(
                title="Boosting Results",
                description=f"Joined: {joined_count}\nBoosted: {boosted_count}",
                color=disnake.Color.green(),
            )
            await inter.followup.send(embed=embed)
        except Exception as e:
            self.bot.logger.error(str(e))
            await inter.followup.send("An error occurred while boosting.", ephemeral=True)


class OAuthBoost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="oauth",
        description="OAUTH group handler",
        #contexts=DEFAULT_CONTEXTS,
        #integration_types=DEFAULT_INTEGRATION_TYPES
    )
    async def oauth_decorator(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @oauth_decorator.sub_command(name="boost", description="Boost a GUILD using OAUTH")
    async def oauth_boost_guild(self, inter: disnake.ApplicationCommandInteraction):
        try:
            modal = BoostingModal(self.bot)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # Unresolved attribute reference 'logger' for class 'Bot' ~ pycharm
            await inter.response.send_message("An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(OAuthBoost(bot))