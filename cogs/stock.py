import disnake
from disnake import app_commands
from disnake.ext import commands

class Stock(commands.Cog): 
    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(name="stock", description="Displays the boost stock information")
    async def stock(self, interaction: disnake.ApplicationCommandInteraction):
        with open('assets/1m_tokens.txt', 'r') as file:
            tokens_1m = len(file.readlines())
        with open('assets/3m_tokens.txt', 'r') as file:
            tokens_3m = len(file.readlines())
        boosts_1m = tokens_1m * 2
        boosts_3m = tokens_3m * 2

        embed = disnake.Embed(
            title="Boost Stock",
            description=(
                f"1M Tokens: ``{tokens_1m}``\n"
                f"1M Boosts: ``{boosts_1m}``\n\n"
                f"3M Tokens: ``{tokens_3m}``\n"
                f"3M Boosts: ``{boosts_3m}``"
            ),
            color=disnake.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Stock(bot))