import asyncio
import os
import logging
from disnake import Intents, app_commands
from disnake.ext import commands
from json import load

logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler(filename='disnake.log', encoding='utf-8', mode='w')
])

with open("config.json", "r") as file:
    data = load(file)

token = data["token"]
prefix = data["prefix"]
intents = Intents.all()
bot = commands.Bot(command_prefix=prefix, intents=intents)

# need to add a starting print

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
