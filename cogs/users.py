import json
import random

from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands

from core.database import add_boost_key, add_user, assign_boost_key_to_user


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("config.json", "r") as f:
            self.config = json.load(f)
        self.owner_ids = self.config["owner_ids"]

    @commands.slash_command(name="users", description="User management commands")
    async def users(self, inter: ApplicationCommandInteraction):
        pass

    @users.sub_command(name="add_key", description="Adds a bosot key to an user")
    async def add_key(self, inter: ApplicationCommandInteraction, user = None, redeemable_boosts: int = None):
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if user is None:
            embed = Embed(
                title="Missing User ID or Mention",
                description="You must either provide a user ID or mention a user.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        if redeemable_boosts is None:
            embed = Embed(
                title="Missing Amount",
                description="You must provide an amount for redeemable_boosts.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        try:
            user_id = user.id
        except Exception:
            user_id = user

        user_id = str(user_id)
        user_id = user_id.replace('<', '').replace('>', '').replace('@', '')
        print(user_id)
        abc = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        length = random.randint(15, 20)
        boost_key = ""
        for i in range(length):
            boost_key += random.choice(abc)
        database_name = self.config["database"]["name"]
        await add_boost_key(boost_key=boost_key,
                            redeemable_boosts=redeemable_boosts,
                            database_name=database_name
                            )
        await add_user(user_id=user_id, 
                       database_name=database_name
                      )
        await assign_boost_key_to_user(user_id=user_id, 
                                        boost_key=boost_key, 
                                        database_name=database_name
                                      )
        await inter.response.send_message(f"{boost_key}, {redeemable_boosts}, {database_name}", ephemeral=True)


def setup(bot):
    bot.add_cog(Users(bot))