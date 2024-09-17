import discord
from discord.ext import commands
from discord import app_commands


class RemoveTokens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="removetokens", description="Removes all tokens from the specified file")
    @app_commands.choices(type=[
        app_commands.Choice(name="1M", value="1M"),
        app_commands.Choice(name="3M", value="3M")
    ])
    async def removetokens(self, interaction: discord.Interaction, type: app_commands.Choice[str]):
        file_path = f'assets/{type.value.lower()}_tokens.txt'
        with open(file_path, 'w') as f:
            f.write('')

        embed = discord.Embed(
            title="Tokens Removed",
            description=f"All tokens have been removed from the {type.value} file.",
            color=discord.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RemoveTokens(bot))