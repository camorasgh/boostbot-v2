import asyncio
import os
import logging
from discord import Intents, app_commands
from discord.ext import commands
from json import load

logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
])

with open("config.json", "r") as file:
    data = load(file)

token = data["token"]
prefix = data["prefix"]
intents = Intents.all()
bot = commands.Bot(command_prefix=prefix, intents=intents)

print("\033[95m")
print("                  ______                                    _____                 _               ")
print("                 / ____/___ _____ ___  ____  _________ _   / ___/___  ______   __(_)_______  _____")
print("                / /   / __ `/ __ `__ \\/ __ \\/ ___/ __ `/   \\__ \\/ _ \\/ ___/ | / / / ___/ _ \\/ ___/")
print("               / /___/ /_/ / / / / / / /_/ / /  / /_/ /   ___/ /  __/ /   | |/ / / /__/  __(__  ) ")
print("               \\____/\\__,_/_/ /_/ /_/\\____/_/   \\__,_/   /____/\\___/_/    |___/_/\\___/\\___/____/  ")
print("                                                                                                  ")
print("                                               Boost Bot v1                                        ")
print("\033[0m")

async def setup_hook(loading_type: str = None) -> None:
    if loading_type is None:
        loading_type = "load"
    for filename in os.listdir(path='./cogs'):
        if not filename.endswith('.py'):
            continue

        if loading_type == "load":
            try:
                await bot.load_extension(name=f'cogs.{filename[:-3]}')
                print(f"\033[92m[+]\033[0m Loaded cog \033[97m{filename[:-3]}\033[0m")
            except Exception as e:
                print(e)
        elif loading_type == "unload":
            try:
                await bot.unload_extension(name=f'cogs.{filename[:-3]}')
                print(f"\033[92m[+]\033[0m Unloaded cog \033[97m{filename[:-3]}\033[0m")
            except Exception as e:
                print(e)

@bot.event
async def on_ready():
    print(f"\033[92m[+]\033[0m Boost bot is logged in as \033[97m{bot.user.name}\033[0m")
    await bot.tree.sync()

if __name__ == "__main__":
    asyncio.run(setup_hook())
    bot.run(token, log_handler=None)
