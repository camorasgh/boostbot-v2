import aiohttp
import datetime
import disnake
import json
import os

from disnake import ApplicationCommandInteraction
from disnake.ext import commands


class Token(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_tokens = {}

        with open("config.json", "r") as f:
            self.config = json.load(f)
        self.owner_ids = self.config.get("owner_id", [])
        self.timezone = datetime.timezone.utc

    @commands.slash_command(name="tokens", description="Token management commands")
    async def tokens(self, inter):
        pass  # correct placeholder?

    @tokens.sub_command(name="check", description="Checks all tokens available")
    async def check(self, inter: ApplicationCommandInteraction, token_type: str = commands.Param(choices=["1M", "3M"])):
        await inter.response.defer(with_message=True)

        file_path = f'assets/{token_type.lower()}_tokens.txt'

        async with aiohttp.ClientSession() as session:
            with open(file_path, 'r') as file:
                tokens = [token.strip() for token in file.readlines()]

            valid_tokens, invalid_count, no_nitro_count, results = [], 0, 0, []

            for token in tokens:
                result = await self.check_token(session, token)
                if result['status'] == "valid":
                    valid_tokens.append(token)
                    results.append(result)
                    if result['type'] == "No Nitro":
                        no_nitro_count += 1
                else:
                    invalid_count += 1

            with open(file_path, 'w') as file:
                file.writelines(f"{token}\n" for token in valid_tokens)

            embed = disnake.Embed(
                title=f"Token Check Results - {token_type}",
                color=disnake.Color.purple()
            )
            for res in results:
                embed.add_field(name=res['title'], value=res['description'], inline=False)

            if invalid_count:
                embed.add_field(name="Invalid Tokens Removed", value=f"{invalid_count} invalid tokens removed.", inline=False)

            await inter.followup.send(embed=embed)

            if no_nitro_count > 0:
                removal_embed = disnake.Embed(
                    title="Remove Tokens Without Nitro?",
                    description=f"Found {no_nitro_count} tokens without Nitro. Remove them?",
                    color=disnake.Color.purple()
                )
                view = NitrolessRemovalButton(self, file_path)
                await inter.followup.send(embed=removal_embed, view=view)

    @commands.slash_command(description="Check and filter tokens")
    async def check(self, inter: disnake.ApplicationCommandInteraction,
                    token_type: str = commands.Param(choices=["1M", "3M"])):
        await inter.response.defer(with_message=True)

        file_path = f'assets/{token_type.lower()}_tokens.txt'
        valid_tokens, invalid_count, no_nitro_count, results = [], 0, 0, []

        async with aiohttp.ClientSession() as session:
            with open(file_path, 'r') as file:
                tokens = [token.strip() for token in file.readlines()]

            for token in tokens:
                result = await self.check_token(session, token)
                if result['status'] == "valid":
                    valid_tokens.append(token)
                    results.append(result)
                    if result['type'] == "No Nitro":
                        no_nitro_count += 1
                else:
                    invalid_count += 1

            with open(file_path, 'w') as file:
                file.writelines(f"{token}\n" for token in valid_tokens)

            embed = disnake.Embed(
                title=f"Token Check Results - {token_type}",
                color=disnake.Color.purple()
            )
            for res in results:
                embed.add_field(name=res['title'], value=res['description'], inline=False)

            if invalid_count:
                embed.add_field(name="Invalid Tokens Removed", value=f"{invalid_count} invalid tokens removed.",
                                inline=False)
            await inter.followup.send(embed=embed)

            if no_nitro_count > 0:
                removal_embed = disnake.Embed(
                    title="Remove Tokens Without Nitro?",
                    description=f"Found {no_nitro_count} tokens without Nitro. Remove them?",
                    color=disnake.Color.purple()
                )
                view = NitrolessRemovalButton(self, file_path)
                await inter.followup.send(embed=removal_embed, view=view)

    async def check_token(self, session, token):
        now = datetime.datetime.now(self.timezone).strftime('%H:%M')
        headers = {"Authorization": token}

        # Get user info
        async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as response:
            if response.status != 200:
                return {"status": "invalid", "title": "Invalid Token",
                        "description": f"Token: {self.mask_token(token)}"}
            user = await response.json()

        if user["premium_type"] == 0:
            return {"status": "valid", "type": "No Nitro", "title": f"{now} - No Nitro",
                    "description": f"Token: {self.mask_token(token)} | User: {user['username']}#{user['discriminator']}"}

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
                "description": f"Token: {self.mask_token(token)} | User: {user['username']} | Boosts: {available_boosts} | Expiry: {nitro_expires} | Server Boosted: {boosted_server}"
            }

        return {
            "status": "valid",
            "type": "Nitro Basic",
            "title": f"{now} - Nitro Basic",
            "description": f"Token: {self.mask_token(token)} | User: {user['username']}#{user['discriminator']}"
        }

    def mask_token(self, token):
        return token[:len(token) // 4] + "***"

    @tokens.sub_command(name="send", description="Sends all available tokens to the owner in a .txt file")
    async def send(self, inter: ApplicationCommandInteraction):
        if inter.author.id not in self.owner_ids:
            await inter.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        file_path = "input/tokens.txt"
        if not os.path.exists(file_path):
            await inter.response.send_message("The file tokens.txt does not exist.", ephemeral=True)
            return

        try:
            await inter.author.send(file=disnake.File(file_path))
            await inter.response.send_message("The tokens.txt file has been sent to your DMs.", ephemeral=True)
        except disnake.Forbidden:
            await inter.response.send_message(
                "File couldn't be sent to your DMs. Please enable DMs and try again.",
                ephemeral=True
            )


class NitrolessRemovalButton(disnake.ui.View):
    def __init__(self, cog, file_path):
        super().__init__()
        self.cog = cog
        self.file_path = file_path

    @disnake.ui.button(label="Yes", style=disnake.ButtonStyle.danger)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await self.cog.remove_nitroless_tokens(interaction, self.file_path)
        self.stop()


def setup(bot):
    bot.add_cog(Token(bot))
