import datetime
import disnake
import json
import os
import tls_client
from typing import Tuple

from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands

from core.misc_boosting import get_headers, Proxies

Tokentype = commands.option_enum({
    "1M Token": "1m_token",
    "3M Token": "3m_token",
    "All": "all",
})


class Token(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        with open("config.json", "r") as f:
            self.config = json.load(f)
        self.owner_ids = self.config["owner_ids"]
        self.timezone = datetime.timezone.utc
        self.file_paths = ["./input/1m_tokens.txt", "./input/3m_tokens.txt"]
        self.client = tls_client.Session(
            client_identifier="chrome112", # type: ignore
            random_tls_extension_order=True
        )


    @commands.slash_command(name="tokens", description="Token management commands")
    async def tokens(self, inter):
        pass

    @tokens.sub_command(name="check", description="Checks all tokens available")
    async def check(self, inter: ApplicationCommandInteraction, token_type: str = commands.Param(choices=["1M", "3M"])):
        await inter.response.defer()
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.edit_original_message(embed=embed)
            return

        file_path = f'./input/{token_type.lower()}_tokens.txt'
        if not os.path.exists(file_path):
            embed = Embed(
                title="File Not Found",
                description=f"The file `{token_type.lower()}_tokens.txt` does not exist.",
                color=0xFFA500  # Orange
            )
            await inter.edit_original_message(embed=embed)
            return
        try:
            with open(file_path, 'r') as file:
                raw_tokens = [token.strip() for token in file.readlines()]
            invalid_count, no_nitro_count, results = 0, 0, []
            valid_tokens, nitroless_tokens = [], []
            tokens = []
            for token in raw_tokens:
                token = token.strip()
                parts = token.split(":")
                if len(parts) >= 3:  # mail:pass:token format
                    token = parts[-1]
                elif len(parts) == 1:  # token only
                    token = parts[0]
                else:
                    # Invalid token format, skipping
                    continue

                if token:  # Only add non-empty tokens
                    tokens.append(token)

            for token in tokens:
                result = await self.check_token(self.client, token)
                if result['status'] == "valid":
                    valid_tokens.append(token)
                    results.append(result)
                    if result['type'] == "No Nitro":
                        no_nitro_count += 1
                        nitroless_tokens.append(token)
                else:
                    invalid_count += 1

            with open(file_path, 'w') as file:
                file.writelines(f"{token}\n" for token in valid_tokens)
            embed = Embed(
                title=f"Token Check Results - {token_type}",
                color=0x800080  # Purple
            )
            embed.add_field(name="Total Tokens", value=f"{len(tokens)} token(s) found.", inline=False)
            valid_descriptions = "\n".join([result['description'] for result in results if result['status'] == 'valid'])
            embed.add_field(name="Valid Tokens", value=f"`{valid_descriptions[:1024]}`", inline=False)
            invalid_descriptions = "\n".join([result['description'] for result in results if result['status'] == 'invalid'])
            embed.add_field(name="Invalid Tokens", value=f"`{invalid_descriptions[:1024]}`", inline=False)

            if invalid_count:
                embed.add_field(name="Invalid Tokens Removed", value=f"{invalid_count} invalid tokens removed.", inline=False)


            await inter.edit_original_message(embed=embed)
            if no_nitro_count > 0:
                removal_embed = Embed(
                    title="Remove Tokens Without Nitro?",
                    description=f"Found {no_nitro_count} tokens without Nitro. Remove them?",
                    color=0x800080  # Purple
                )
                view = NitrolessRemovalButton(self, file_path, nitroless_tokens)
                await inter.edit_original_message(embed=removal_embed, view=view)

        except Exception as e:
            self.bot.logger.error(f"An error occurred: {str(e)}")
            error_embed = Embed(
                title="Error",
                description="An error occurred while checking tokens. Please check the logs.",
                color=0xFF0000  # Red
            )
            await inter.edit_original_message(embed=error_embed)


    async def check_token(self, session, token):
        now = datetime.datetime.now(self.timezone).strftime('%H:%M')
        headers = {"Authorization": token}
        response = session.get("https://discord.com/api/v9/users/@me", headers=headers)
        if response.status_code != 200:
            return {
                "status": "invalid",
                "title": "Invalid Token",
                "description": f"Token: {self.mask_token(token)}"
            }
        user = response.json()
        if user.get("premium_type") == 0:
            return {
                "status": "valid",
                "type": "No Nitro",
                "title": f"{now} - No Nitro",
                "description": f"Token: {self.mask_token(token)}"
            }
        elif user.get("premium_type") == 2:
            boost_response = session.get("https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers=headers)
            boost_data = boost_response.json() if boost_response.status_code == 200 else []

            available_boosts = sum(
                1 for slot in boost_data if not slot.get('cooldown_ends_at') or
                datetime.datetime.fromisoformat(slot['cooldown_ends_at']).replace(
                    tzinfo=datetime.timezone.utc) <= datetime.datetime.now(datetime.timezone.utc)
            )
            boosted_server = boost_data[0]['premium_guild_subscription']['guild_id'] if boost_data and boost_data[0].get(
                'premium_guild_subscription') else "None"

            billing_response = session.get("https://discord.com/api/v9/users/@me/billing/subscriptions", headers=headers)
            if billing_response.status_code == 200:
                nitro_data = billing_response.json()
                nitro_expires = datetime.datetime.fromisoformat(nitro_data[0]['trial_ends_at']).strftime("%d.%m.%y") if nitro_data else "Unknown"
            else:
                nitro_expires = "Unknown"

            return {
                "status": "valid",
                "type": "Nitro Boost",
                "title": f"{now} - Nitro Boost",
                "description": f"Token: {self.mask_token(token)} | Boosts: {available_boosts} | Expiry: {nitro_expires} | Server Boosted: {boosted_server}"
            }

        return {
            "status": "valid",
            "type": "Nitro Basic",
            "title": f"{now} - Nitro Basic",
            "description": f"Token: {self.mask_token(token)}"
        }

    @staticmethod
    def mask_token(token):
        return token[:len(token) // 4] + "***"

    @staticmethod
    async def remove_nitroless_tokens(interaction, file_path, nitroless_tokens):
        """
        Removes the specified list of tokens without Nitro from the file.
        :param interaction: disnake interaction
        :param file_path: path to and the file (e.g. input/3m_tokens.txt)
        :param nitroless_tokens: list of tokens not owning nitro
        """
        with open(file_path, 'r') as file:
            tokens = [token.strip() for token in file.readlines()]
        tokens_with_nitro = [token for token in tokens if token not in nitroless_tokens]
        
        with open(file_path, 'w') as file:
            file.writelines(f"{token}\n" for token in tokens_with_nitro)
        removed_count = len(tokens) - len(tokens_with_nitro)
        await interaction.response.send_message(f"Removed {removed_count} tokens without Nitro.", ephemeral=True)

    @tokens.sub_command(name="brand", description="Brands a whole stock to your configuration")
    async def brand_token(
            self,
            inter: ApplicationCommandInteraction,
            token_type: Tokentype, # type: ignore
            guild_id: str
    ):
        """
        Brands the token from 1m_tokens/3m_tokens with stuff from config.json
        :param inter: Provided by discord, interaction
        :param token_type: Type of token stock to be branded, either 1m tokens or 3m tokens or all
        :param guild_id: Guild ID to brand the user in
        """
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        await inter.response.defer()

        try:
            guild_id = int(guild_id)
        except ValueError:
            return await inter.followup.send("`ERR_INVALID_INT` couldn't convert Guild ID to an Integer.")
        tokens = []
        if token_type == "1m_token":
            file_names = ["1m_tokens.txt"]
        elif token_type == "3m_token":
            file_names = ["3m_tokens.txt"]
        else:  # aka if all is chosen
            file_names = ["1m_tokens.txt", "3m_tokens.txt"]

        for file_name in file_names:
            try:
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
            except FileNotFoundError:
                await inter.followup.send(f"`ERR_FILE_NOT_FOUND` File `{file_name}` not found. Skipping...", ephemeral=True)
                continue

        if not tokens:
            await inter.followup.send("No valid tokens found to process.", ephemeral=True)
            return

        success_count = 0
        failed_tokens = []

        for token in tokens:
            headers = get_headers(token)
            brand_bio, brand_displayname = await get_brandingdata()
            prx = Proxies()
            json_data = {
                "bio": brand_bio
            }
            # seperated because of different url and lazy
            json_data2 = {
                "nick": brand_displayname
            }
            profile_response, display_name_response = None, None
            try:
                # Update the user profile
                profile_response = self.client.patch(
                    "https://discord.com/api/v9/users/@me/profile",
                    headers=headers,
                    json=json_data,
                )
                response_text = profile_response.text

                if profile_response.status_code != 200:
                    failed_tokens.append((token, f"`BRANDING_BIO` | HTTP {profile_response.status_code}: {response_text}"))

            except tls_client.sessions.TLSClientExeption as e:
                failed_tokens.append((token, f"Connection Error: {str(e)}"))
            except Exception as e:
                failed_tokens.append((token, f"Unexpected Exception: {str(e)}"))

            try:
                # Get a random proxy
                proxy = await prx.get_random_proxy(self.bot)
                # noinspection HttpUrlsUsage
                proxy = {
                    "http": "http://{}".format(proxy),
                    "https": "https://{}".format(proxy)
                } if proxy else None

                # Update the guild display name
                display_name_response = self.client.patch(
                    f"https://discord.com/api/v9/guilds/{guild_id}/members/@me",
                    headers=headers,
                    json=json_data2,
                    proxy=proxy
                )
                response_text2 = display_name_response.text

                if display_name_response.status_code == 200 and profile_response.status_code == 200:
                    success_count += 1
                elif display_name_response.status_code == 404:
                    failed_tokens.append((token, f"`BRANDING_DISPLAYNAME` | HTTP {display_name_response.status_code}: {response_text2}"))
                else:
                    failed_tokens.append((token, f"`BRANDING_DISPLAYNAME` | HTTP {display_name_response.status_code}: {response_text2}"))

            except tls_client.sessions.TLSClientExeption as e:
                failed_tokens.append((token, f"Connection Error: {str(e)}"))
            except Exception as e:
                failed_tokens.append((token, f"Unexpected Exception: {str(e)}"))

        # Summary of operation | ephemeral
        embed = Embed(
            title="Branding Operation Summary",
            color=0x00FF00 if success_count == len(tokens) else 0xFF0000,  # Green if all succeeded, red otherwise
            description=f"Branding completed: **{success_count}/{len(tokens)}** successful."
        )
        if failed_tokens:
            #token.split('.')[0] means token until first dot
            failed_tokens_list = "\n".join([f"• `{token.split('.')[0]}`: {reason}" for token, reason in failed_tokens])
            embed.add_field(
                name="Failed Tokens",
                value=failed_tokens_list[:1024],  # Discord field value limit is 1024 characters
                inline=False
            )
        else:
            embed.add_field(
                name="Failed Tokens",
                value="None 🎉",
                inline=False
            )
        await inter.followup.send(embed=embed, ephemeral=True)

    @tokens.sub_command(name="send", description="Sends all available tokens to the owner in a .txt file")
    async def send(self, inter: ApplicationCommandInteraction):
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        for file_path in self.file_paths:
            if not os.path.exists(file_path):
                embed = Embed(
                    title="File Not Found",
                    description="The file `tokens.txt` does not exist.",
                    color=0xFFA500  # Orange
                )
                await inter.response.send_message(embed=embed, ephemeral=True)
                return
            try:
                await inter.author.send(file=disnake.File(file_path))
                embed_dm_success = Embed(
                    title="File Sent",
                    description="The `tokens.txt` file(s) has/have been sent to your DMs.",
                    color=0x00FF00  # Green
                )
                await inter.response.send_message(embed=embed_dm_success, ephemeral=True)
            except disnake.Forbidden:
                embed_dm_fail = Embed(
                    title="DM Error",
                    description=(
                        "The file couldn't be sent to your DMs. Please enable direct messages from this server and try again."
                    ),
                    color=0xFF0000  # Red
                )
                await inter.response.send_message(embed=embed_dm_fail, ephemeral=True)


async def get_brandingdata() -> Tuple[str, str]:
    with open('config.json', 'r') as file:
        config = json.load(file)
    return config["brand_bio"], config["brand_displayname"]

class NitrolessRemovalButton(disnake.ui.View):
    def __init__(self, cog, file_path, nitroless_tokens):
        """
        Button cog to remove nitroless tokens
        :param cog:
        :param file_path:
        """
        super().__init__()
        self.cog = cog
        self.file_path = file_path
        self.nitroless_tokens = nitroless_tokens

    # noinspection PyUnusedLocal
    # (button variable)
    @disnake.ui.button(label="Yes", style=disnake.ButtonStyle.danger)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await self.cog.remove_nitroless_tokens(interaction, self.file_path, self.nitroless_tokens)
        self.stop()


def setup(bot):
    bot.add_cog(Token(bot))
