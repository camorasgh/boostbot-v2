import datetime
import json
import os
from typing import Tuple

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction, Option
from disnake.ext import commands

from misc import get_headers


class Token(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        with open("config.json", "r") as f:
            self.config = json.load(f)
        self.owner_ids = self.config["owner_ids"]
        self.timezone = datetime.timezone.utc
        self.file_paths = ["./input/1m_tokens.txt", "./input/3m_tokens.txt"]

    @commands.slash_command(name="tokens", description="Token management commands")
    async def tokens(self, inter):
        pass  # correct placeholder?

    @tokens.sub_command(name="check", description="Checks all tokens available")
    async def check(self, inter: ApplicationCommandInteraction, token_type: str = commands.Param(choices=["1M", "3M"])):
        await inter.response.defer(with_message=True)

        file_path = f'./input/{token_type.lower()}_tokens.txt'

        async with aiohttp.ClientSession() as session:
            with open(file_path, 'r') as file:
                tokens = [token.strip() for token in file.readlines()]

            invalid_count, no_nitro_count, results = 0, 0, []
            valid_tokens, nitroless_tokens = [], []
            for token in tokens:
                result = await self.check_token(session, token)
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

            embed = disnake.Embed(
                title=f"Token Check Results - {token_type}",
                color=disnake.Color.purple()
            )
            """
            for res in results:
                embed.add_field(name=res['title'], value=res['description'], inline=False)
            """

            if invalid_count:
                embed.add_field(name="Invalid Tokens Removed", value=f"{invalid_count} invalid tokens removed.", inline=False)

            await inter.followup.send(embed=embed)

            if no_nitro_count > 0:
                removal_embed = disnake.Embed(
                    title="Remove Tokens Without Nitro?",
                    description=f"Found {no_nitro_count} tokens without Nitro. Remove them?",
                    color=disnake.Color.purple()
                )
                view = NitrolessRemovalButton(self, file_path, nitroless_tokens)
                await inter.followup.send(embed=removal_embed, view=view)

    async def check_token(self, session, token):
        now = datetime.datetime.now(self.timezone).strftime('%H:%M')
        headers = {"Authorization": token}

        async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as response:
            if response.status != 200:
                return {"status": "invalid", "title": "Invalid Token",
                        "description": f"Token: {self.mask_token(token)}"}
            user = await response.json()

        if user["premium_type"] == 0:
            return {"status": "valid", "type": "No Nitro", "title": f"{now} - No Nitro",
                    "description": f"Token: {self.mask_token(token)}"}

        elif user["premium_type"] == 2:
            async with session.get("https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
                                   headers=headers) as response:
                boost_data = await response.json() if response.status == 200 else []

            available_boosts = sum(1 for slot in boost_data if not slot.get('cooldown_ends_at') or
                                   datetime.datetime.fromisoformat(slot['cooldown_ends_at']).replace(
                                       tzinfo=datetime.timezone.utc) <= datetime.datetime.now(datetime.timezone.utc))
            boosted_server = boost_data[0]['premium_guild_subscription']['guild_id'] if boost_data and boost_data[
                0].get('premium_guild_subscription') else "None"

            async with session.get("https://discord.com/api/v9/users/@me/billing/subscriptions",
                                   headers=headers) as response:
                if response.status == 200:
                    nitro_data = await response.json()
                    nitro_expires = datetime.datetime.fromisoformat(nitro_data[0]['trial_ends_at']).strftime("%d.%m.%y")
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
        token_type: str = Option(
            name="token_type",
            description="Choose the token type",
            choices=["1m_token", "3m_token", "all"],
            required=True
        ),
    ):
        """
        Brands the token from 1m_tokens/3m_tokens with stuff from config.json
        :param inter: Provided by discord, interaction
        :param token_type: Type of token stock to be branded, either 1m tokens or 3m tokens or all
        """

        tokens = []
        if token_type == "1m_token":
            file_names = ["1m_tokens.txt"]
        elif token_type == "3m_token":
            file_names = ["3m_tokens.txt"]
        else:  # aka if all is chosen
            file_names = ["1m_tokens.txt", "3m_tokens.txt"]

        for file_name in file_names:
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

            for token in tokens:
                headers = get_headers(token)
                brand_bio, brand_displayname = await get_brandingdata()
                
                json_data = {
                    "bio": brand_bio,
                    "global_name": brand_displayname
                }

                async with aiohttp.ClientSession() as session:
                    async with session.patch("https://discord.com/api/v9/users/%40me/profile", headers=headers, json=json_data) as response: # brand about me stuff
                        if int(response.status) == 200:
                            pass # successful, still needs to add a lot of stuff

    @tokens.sub_command(name="send", description="Sends all available tokens to the owner in a .txt file")
    async def send(self, inter: ApplicationCommandInteraction):
        if inter.author.id not in self.owner_ids:
            await inter.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        for file_path in self.file_paths:
            if not os.path.exists(file_path):
                await inter.response.send_message("The file tokens.txt does not exist.", ephemeral=True)
                return

            try:
                await inter.author.send(file=disnake.File(file_path))
                await inter.response.send_message("The tokens.txt file(s) has/have been sent to your DMs.", ephemeral=True)
            except disnake.Forbidden:
                await inter.response.send_message(
                    "File couldn't be sent to your DMs. Please enable DMs and try again.",
                    ephemeral=True
                )


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
