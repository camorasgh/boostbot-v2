import disnake
from disnake.ext import commands

class ExampleCog(commands.Cog):
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
    
    @commands.slash_command(name="test", description="Test command")
    @commands.is_owner()
    async def testcmd(self, inter: disnake.ApplicationCommandInteraction):
        return await inter.send("Test!", ephemeral=True)
    
def setup(bot: commands.InteractionBot):
    bot.add_cog(ExampleCog)