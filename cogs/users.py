from disnake.ext import commands

class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.slash_command(name="users", description="User management commands")
    async def tokens(self, inter):
        pass  # correct placeholder?


def setup(bot):
    bot.add_cog(Users(bot))