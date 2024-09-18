import disnake
from disnake.ext import commands


class RemoveTokens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(name="removetokens", description="Removes all tokens from the specified file")
    async def removetokens(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        token_type: str = commands.Param(choices=["1M", "3M"])
    ):
        file_path = f'assets/{token_type.lower()}_tokens.txt'
        with open(file_path, 'w') as f:
            f.write('')

        embed = disnake.Embed(
            title="Tokens Removed",
            description=f"All tokens have been removed from the {token_type} file.",
            color=disnake.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RemoveTokens(bot))