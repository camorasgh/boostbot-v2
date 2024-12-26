import json
import random
from disnake import ApplicationCommandInteraction, Embed
from disnake.ext import commands
from core.database import add_boost_key, add_user, assign_boost_key_to_user, remove_boost_key_from_user
from core.database import transfer_boost_key, get_boost_keys_for_user, update_boosts_for_key

with open("config.json", "r") as f:
    config = json.load(f)


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = config["owner_ids"]

    @commands.slash_command(name="users", description="User management commands")
    async def users(self, inter: ApplicationCommandInteraction):
        pass

    @users.sub_command(name="add_key", description="Adds a boost key to a user")
    async def add_key(self, inter: ApplicationCommandInteraction, user=None, redeemable_boosts: int = None):
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
        if redeemable_boosts % 2 != 0:
            embed = Embed(
                title="Invalid Amount",
                description="The amount of redeemable boosts must be an even number.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        # noinspection PyUnusedLocal,PyBroadException
        try:
            user_id = user.id
        except Exception as e:
            user_id = user
            user_id = str(user_id)
            user_id = user_id.replace('<', '').replace('>', '').replace('@', '')

        # Create random boost key
        abc = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        length = random.randint(15, 20)
        boost_key = ''.join(random.choice(abc) for _ in range(length))

        try:
            database_name = config["boost_keys_database"]["name"]
            await add_boost_key(boost_key=boost_key, redeemable_boosts=redeemable_boosts, database_name=database_name)
            await add_user(user_id=user_id, database_name=database_name)
            await assign_boost_key_to_user(user_id=user_id, boost_key=boost_key, database_name=database_name)
            embed = Embed(
                title="Boost Key Assigned",
                description=f"Assigned Boost Key `{boost_key}` with {redeemable_boosts} redeemable boosts to <@{user_id}>",
                color=0x00FF00  # Green
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = Embed(
                title="Database Error",
                description=f"An error occurred while adding the boost key: {str(e)}.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)

    @users.sub_command(name="remove_key", description="Removes a boost key from a user.")
    async def remove_key(self, inter: ApplicationCommandInteraction, user=None, boost_key: str = None):
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user is None or boost_key is None:
            embed = Embed(
                title="Missing Parameters",
                description="You must provide both a user and a boost key to remove.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id = user.id
        except Exception as e:
            try:
                user_id = str(user).replace('<', '').replace('>', '').replace('@', '')
            except Exception as e:
                embed = Embed(
                                title="Invalid User Format",
                                description=f"An error occurred while processing the user ID: {str(e)}.",
                                color=0xFF0000  # Red
                            )
                await inter.response.send_message(embed=embed, ephemeral=True)
                return
        try:
            database_name = config["boost_keys_database"]["name"]
            await remove_boost_key_from_user(user_id=user_id, boost_key=boost_key, database_name=database_name)
            embed = Embed(
                title="Boost Key Removed",
                description=f"The boost key `{boost_key}` has been removed from user <@{user_id}>.",
                color=0x00FF00  # Green
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = Embed(
                title="Database Error",
                description=f"An error occurred while removing the boost key: {str(e)}.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)

    @users.sub_command(name="transfer_key", description="Transfers a boost key from one user to another.")
    async def transfer_key(self, inter: ApplicationCommandInteraction, sender=None, receiver=None, boost_key: str = None):
        if inter.author.id not in self.owner_ids:
            embed = Embed(
                title="Unauthorized Access",
                description="You are not authorized to use this command.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        if sender is None or receiver is None or boost_key is None:
            embed = Embed(
                title="Missing Parameters",
                description="You must provide a sender, a receiver, and a boost key to transfer.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse user IDs and handle errors
        try:
            sender_id = sender.id if hasattr(sender, 'id') else str(sender).replace('<', '').replace('>', '').replace('@', '')
            receiver_id = receiver.id if hasattr(receiver, 'id') else str(receiver).replace('<', '').replace('>', '').replace('@', '')
        except Exception as e:
            embed = Embed(
                title="Invalid User Format",
                description=f"An error occurred while processing the user IDs: {str(e)}.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            sender_id = int(sender_id)
            receiver_id = int(receiver_id)
            database_name = config["boost_keys_database"]["name"]
            success = await transfer_boost_key(sender_id=sender_id, receiver_id=receiver_id, boost_key=boost_key, database_name=database_name)
            
            if success:
                embed = Embed(
                    title="Boost Key Transferred",
                    description=f"The boost key `{boost_key}` has been transferred from <@{sender_id}> to <@{receiver_id}>.",
                    color=0x00FF00  # Green
                )
            else:
                embed = Embed(
                    title="Transfer Failed",
                    description=f"The sender <@{sender_id}> does not own the boost key `{boost_key}`.",
                    color=0xFF0000  # Red
                )
        except ValueError as e:
            embed = Embed(
                title="Invalid Data",
                description=f"Invalid user data encountered: {str(e)}.",
                color=0xFF0000  # Red
            )
        except Exception as e:
            embed = Embed(
                title="Transfer Error",
                description=f"An error occurred while transferring the boost key: {str(e)}.",
                color=0xFF0000  # Red
            )
        
        await inter.response.send_message(embed=embed, ephemeral=True)

    @users.sub_command(name="list_boost_keys", description="Lists all boost keys for a specified user.")
    async def list_boost_keys(self, inter: ApplicationCommandInteraction, user=None):
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
                title="Missing User",
                description="You must provide a user to list their boost keys.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id = user.id if hasattr(user, 'id') else str(user).replace('<', '').replace('>', '').replace('@', '')
        except Exception as e:
            embed = Embed(
                title="Invalid User Format",
                description=f"An error occurred while processing the user ID: {str(e)}.",
                color=0xFF0000  # Red
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id = int(user_id)
            database_name = config["boost_keys_database"]["name"]
            keys = await get_boost_keys_for_user(user_id=user_id, database_name=database_name)
            
            if not keys:
                embed = Embed(
                    title="No Boost Keys Found",
                    description=f"No boost keys found for user `<@{user_id}>`.",
                    color=0xFF0000  # Red
                )
            else:
                keys_list = "\n".join([f"`{key[0]}` - Redeemable Boosts: `{key[1]}`" for key in keys])
                embed = Embed(
                    title="Boost Keys",
                    description=f"Boost keys for <@{user_id}>:\n\n{keys_list}",
                    color=0x00FF00  # Green
                )
        except Exception as e:
            embed = Embed(
                title="Error Fetching Keys",
                description=f"An error occurred while fetching boost keys: {str(e)}.",
                color=0xFF0000  # Red
            )
        
        await inter.response.send_message(embed=embed, ephemeral=True)

    @users.sub_command(name="add_boosts", description="Adds boosts to a boost key")
    async def add_boosts(self,
        inter: ApplicationCommandInteraction,
        boost_key: str = commands.Param(description="The boost key to update."), 
        boosts: int = commands.Param(description="Number of boosts to add.")
    ):
        try:
            success = await update_boosts_for_key(boost_key, boosts, config["boost_keys_database"]["name"], "add")
            if success:
                await inter.response.send_message(f"✅ Successfully added {boosts} boosts to `{boost_key}`.", ephemeral=True)
            else:
                await inter.response.send_message(f"❌ Could not add boosts to `{boost_key}`. Key may not exist.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"⚠️ Error: {str(e)}", ephemeral=True)

    @users.sub_command(name="remove_boosts", description="Removes boosts from a boost key")
    async def remove_boosts(self,
        inter: ApplicationCommandInteraction,
        boost_key: str = commands.Param(description="The boost key to update."),
        boosts: int = commands.Param(description="Number of boosts to remove.")
    ):
        try:
            success = await update_boosts_for_key(boost_key, boosts, config["boost_keys_database"]["name"], "remove")
            if success:
                await inter.response.send_message(f"✅ Successfully removed {boosts} boosts from `{boost_key}`.", ephemeral=True)
            else:
                await inter.response.send_message(f"❌ Could not remove boosts from `{boost_key}`. Key may not exist or lacks enough boosts.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"⚠️ Error: {str(e)}", ephemeral=True)

def setup(bot):
    if config["boost_keys_database"]["enabled"]:
        bot.add_cog(Users(bot))
