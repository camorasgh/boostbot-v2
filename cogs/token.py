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

    @commands.slash_command(name="tokens", description="Token management commands")
    async def tokens(self, inter):
        pass  # correct placeholder?

    @tokens.sub_command(name="check", description="Checks all tokens available")
    async def check(self, inter: ApplicationCommandInteraction):
        pass # just act like this is getting tokens from input/tokens.txt and then checks

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


def setup(bot):
    bot.add_cog(Token(bot))
