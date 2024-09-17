import discord
from discord import app_commands
from discord.ext import commands


class Restock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="restock", description="Restocks tokens")
    @app_commands.choices(type=[
        app_commands.Choice(name="1M", value="1M"),
        app_commands.Choice(name="3M", value="3M")
    ])
    async def restock(self, interaction: discord.Interaction, type: app_commands.Choice[str], file: discord.Attachment):
        if not file:
            await interaction.response.send_message("Please upload a file with the tokens.")
            return

        file_path = f'assets/{type.value.lower()}_tokens.txt'
        content = await file.read()
        tokens = content.decode('utf-8').splitlines()
        with open(file_path, 'a') as f:
            for token in tokens:
                f.write(f"{token}\n")

        embed = discord.Embed(
            title="Restock Successful",
            description=f"Successfully restocked ``{len(tokens)}`` tokens for {type.value}.",
            color=discord.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Restock(bot))