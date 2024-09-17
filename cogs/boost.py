import aiohttp
import discord
import requests
import time
from discord import app_commands
from discord.ext import commands
from json import load
import sys
sys.path.append('.')
from . import boosting

with open("config.json", "r") as file:
    data = load(file)


class Boost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_token = data['token']
        self.bot_secret = data['secret']
        self.redirect_url = data['redirect']
        self.api_endpoint = data['canary_api']
        self.bot_id = 123
        self.auth_url = f"123"


    @commands.Cog.listener()
    async def on_ready(self):
        self.bot_id = self.bot.user.id
        self.auth_url = f"https://canary.discord.com/api/v9/oauth2/authorize?response_type=code&client_id={self.bot_id}&redirect_uri={self.redirect_url}&scope=guilds.join+identify"
        print("Ready")


    async def exchange_code_for_token(self, code):
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_url,
            'client_id': self.bot_id,
            'client_secret': self.bot_secret,
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_endpoint}/oauth2/token", data=data, headers=headers) as response:
                if response.status != 200:
                    print(f"Token exchange failed: {await response.text()}")
                    return None
                return await response.json()


    @app_commands.command(name="boost", description="Boost users to the server")
    @app_commands.choices(type=[
        app_commands.Choice(name="1M", value="1M"),
        app_commands.Choice(name="3M", value="3M")
    ])
    async def boost(self, interaction: discord.Interaction, server_id: str, type: app_commands.Choice[str], amount: int):
        await interaction.response.defer(thinking=True)
        if amount % 2 != 0 or amount < 2:
            await interaction.followup.send("Amount must be an even number and at least 2.")
            return

        start_time = time.time()
        try:
            server_id = int(server_id)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")
            return 
        
        file_path = f'assets/{type.value.lower()}_tokens.txt'
        try:
            with open(file_path, 'r') as file:
                tokens = file.readlines()
        except FileNotFoundError:
            await interaction.followup.send("Token file not found.")
            return

        tokens = [token.strip() for token in tokens]
        boosts_needed = amount
        total_boosts_successful = 0
        total_tokens_used = 0

        for _ in range(boosts_needed // 2):
            if not tokens:
                await interaction.followup.send("Not enough tokens to complete the boost.")
                break

            token = tokens.pop(0)
            total_tokens_used += 1

            header = {
                "Authorization": f"{token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
                "Content-Type": "application/json",
                "Origin": "https://canary.discord.com",
                "X-Discord-Locale": "en-US",
                "X-Discord-Timezone": "Europe/Vienna"
            }
            data = {
                "permissions": "0",
                "authorize": True,
                "integration_type": 0,
                "location_context": {
                    "guild_id": "10000",
                    "channel_id": "10000",
                    "channel_type": 10000
                }
            }

            response = requests.post(url=self.auth_url, headers=header, json=data)
            response_json = response.json()
            location_url = response_json.get("location")
            if location_url and "code=" in location_url:
                code = location_url.split("code=")[1].split("&")[0]
            else:
                code = None
            token_response = await self.exchange_code_for_token(code)
            if token_response is None:
                print(f"Token {token} has returned code NULL (exchange code for token)")
                continue

            access_token = token_response.get('access_token')
            if not access_token:
                print(f"Token {token} has no access_token (after exchange code for token)")
                continue

            booster = boosting.boosting()
            if await booster.add_user_to_guild(access_token, server_id):
                print('User added to guild successfully!')
                if await booster.process_boostids(token, server_id): #@suspectedesp was here
                    total_boosts_successful += 2

            await booster.remove_used_token(file_path, token)

        end_time = time.time()
        duration = end_time - start_time
        guild = self.bot.get_guild(server_id)
        guild_name = guild.name if guild else "Unknown Server"

        embed = discord.Embed(title="Operation Summary", color=0xbe00c4)
        embed.add_field(name="Guild Name", value=guild_name, inline=False)
        embed.add_field(name="Operation Duration", value=f"{duration:.2f} seconds", inline=False)
        embed.add_field(name="Joins Succeeded", value=f"{total_tokens_used}/{boosts_needed // 2}", inline=False)
        embed.add_field(name="Boosts Succeeded", value=f"{total_boosts_successful}/{amount}", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Boost(bot))