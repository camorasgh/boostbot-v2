import datetime

import disnake
import pytz
import requests
from disnake.ext import commands


class NitrolessRemovalButton(disnake.ui.View):
    def __init__(self, cog, file_path):
        super().__init__(timeout=None)
        self.cog = cog
        self.file_path = file_path

    @disnake.ui.button(label="Yes", style=disnake.ButtonStyle.green, custom_id="remove_nitroless_yes")
    async def yes_button(self, interaction: disnake.MessageInteraction, button: disnake.ui.Button):
        # Call the cog's remove method
        await self.cog.remove_nitroless_tokens(interaction, self.file_path)

        # Disable both buttons
        button.disabled = True
        for item in self.children:
            item.disabled = True

        # Edit the original message to reflect the new button states
        await interaction.message.edit(view=self)

    @disnake.ui.button(label="No", style=disnake.ButtonStyle.red, custom_id="remove_nitroless_no")
    async def no_button(self, interaction: disnake.MessageInteraction, button: disnake.ui.Button):
        # Send an embed indicating the action was cancelled
        embed = disnake.Embed(
            title="Action Cancelled",
            description="Nitroless tokens will not be removed.",
            color=disnake.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)

        # Disable both buttons
        button.disabled = True
        for item in self.children:
            item.disabled = True

        # Edit the original message to reflect the new button states
        await interaction.message.edit(view=self)


class TokenChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timezone = pytz.timezone('Europe/Berlin')
        
    @commands.slash_command(name="check", description="Checks tokens")
    async def check(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        token_type: str = commands.Param(choices=["1M", "3M"])
    ):
        await interaction.response.defer(thinking=True)

        file_path = f'assets/{token_type.lower()}_tokens.txt'
        no_nitro_count = 0
        invalid_count = 0
        results = []
        valid_tokens = []
        session = requests.Session()

        with open(file_path, 'r') as file:
            tokens = file.readlines()
        tokens = [token.strip() for token in tokens]

        for token in tokens:
            result = self.check_token(session, token)
            if result['title'] != "Invalid token":
                results.append(result)
                valid_tokens.append(token)
                if "No Nitro" in result['title']:
                    no_nitro_count += 1
            else:
                invalid_count += 1

        session.close()

        with open(file_path, 'w') as file:
            file.writelines(f"{token}\n" for token in valid_tokens)

        embed = disnake.Embed(
            title=f"Token Check Results - {token_type}",
            color=disnake.Color.from_rgb(190, 0, 196)
        )

        for result in results:
            embed.add_field(name=result['title'], value=result['description'], inline=False)

        if invalid_count > 0:
            embed.add_field(name="Invalid Tokens Removed", value=f"Removed {invalid_count} invalid tokens", inline=False)

        await interaction.followup.send(embed=embed)

        if no_nitro_count > 0:
            removal_embed = disnake.Embed(
                title="Remove Nitroless Tokens?",
                description=f"Found {no_nitro_count} tokens without Nitro. Should I remove all Nitroless tokens?",
                color=disnake.Color.from_rgb(190, 0, 196)
            )

            view = NitrolessRemovalButton(self, file_path)
            await interaction.followup.send(embed=removal_embed, view=view)


    def get_current_time(self):
        return datetime.datetime.now(self.timezone).strftime('%H:%M')


    @staticmethod
    def mask_token(token):
        return token[:len(token)//4] + "***"


    @staticmethod
    def get_user_info(session, token):
        headers = {"Authorization": token}
        try:
            response = session.get("https://discord.com/api/v9/users/@me", headers=headers)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.HTTPError, ValueError):
            return None


    @staticmethod
    def get_guild_subscription_slots(session, token):
        headers = {"Authorization": token}
        try:
            response = session.get("https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            return []


    @staticmethod
    def calculate_available_boosts(boost_check):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        return sum(
            1 for slot in boost_check
            if slot.get('cooldown_ends_at') is None or 
            datetime.datetime.fromisoformat(slot['cooldown_ends_at'].split('+')[0] + '+00:00').replace(tzinfo=datetime.timezone.utc) <= now_utc
        )


    @staticmethod
    def get_boosted_server(boost_check):
        if boost_check and boost_check[0]['premium_guild_subscription'] is not None:
            return boost_check[0]['premium_guild_subscription']['guild_id']
        return "None"


    @staticmethod
    def get_nitro_expiration(session, token):
        headers = {"Authorization": token}
        try:
            response = session.get("https://discord.com/api/v9/users/@me/billing/subscriptions", headers=headers)
            response.raise_for_status()
            nitro_data = response.json()
            expires_at = datetime.datetime.fromisoformat(nitro_data[0]['trial_ends_at']).replace(tzinfo=datetime.timezone.utc)
            return f'Expires: {expires_at.strftime("%d.%m.%y")}'
        except (requests.exceptions.HTTPError, IndexError, KeyError):
            return ""


    def format_invalid_token_response(self, token):
        token_masked = self.mask_token(token)
        return {
            'title': "Invalid token",
            'description': f"Token: {token_masked}"
        }


    def format_no_nitro_response(self, now, user, token):
        token_masked = self.mask_token(token)
        return {
            'title': f"{now} - No Nitro",
            'description': f"Token: {token_masked}\nUser: {user['username']}#{user['discriminator']}"
        }


    def format_nitro_boost_response(self, now, user, available_boosts, nitro_expires, boosted_server, token):
        token_masked = self.mask_token(token)
        return {
            'title': f"{now} - Nitro Boost",
            'description': (
                f"Token: {token_masked}\n"
                f"User: {user['username']}\n"
                f"Boosts: {available_boosts}\n"
                f"{nitro_expires}\n"
                f"Server Boosted: {boosted_server}"
            )
        }


    def format_nitro_basic_response(self, now, user, token):
        token_masked = self.mask_token(token)
        return {
            'title': f"{now} - Nitro Basic",
            'description': f"Token: {token_masked}\nUser: {user['username']}#{user['discriminator']}"
        }


    def check_token(self, session, token):
        now = self.get_current_time()
        user = self.get_user_info(session, token)
        
        if not user:
            return self.format_invalid_token_response(token)
        
        if user["premium_type"] == 0:
            return self.format_no_nitro_response(now, user, token)
        
        elif user["premium_type"] == 2:
            boost_check = self.get_guild_subscription_slots(session, token)
            available_boosts = self.calculate_available_boosts(boost_check)
            boosted_server = self.get_boosted_server(boost_check)
            nitro_expires = self.get_nitro_expiration(session, token)

            return self.format_nitro_boost_response(now, user, available_boosts, nitro_expires, boosted_server, token)
        
        else:
            return self.format_nitro_basic_response(now, user, token)
        

    async def remove_nitroless_tokens(self, interaction: disnake.Interaction, file_path):
        with open(file_path, 'r') as file:
            tokens = file.readlines()

        nitro_tokens = []
        session = requests.Session()

        for token in tokens:
            result = self.check_token(session, token.strip())
            if "No Nitro" not in result['title']:
                nitro_tokens.append(token)

        session.close()

        with open(file_path, 'w') as file:
            file.writelines(nitro_tokens)

        removed_count = len(tokens) - len(nitro_tokens)
        embed = disnake.Embed(
            title="Nitroless Tokens Removed",
            description=f"Removed {removed_count} Nitroless tokens.",
            color=disnake.Color.from_rgb(190, 0, 196)
        )
        await interaction.response.send_message(embed=embed)


def setup(bot):
    bot.add_cog(TokenChecker(bot))