import disnake
from disnake.ext import commands
from typing import Dict, Any
import json
import colorama
from colorama import Fore
import datetime
import os
import sys

class Logger:
    @staticmethod
    def success(message: str) -> None:
        current_time = Utils.format_time()
        fornatted_time = f"{Fore.LIGHTBLACK_EX}[{Fore.LIGHTCYAN_EX}{current_time}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        formatted_status = f"{Fore.LIGHTBLACK_EX}[{Fore.GREEN}SUCCESS{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        full_msg =  f"{fornatted_time} {formatted_status} {Fore.LIGHTBLACK_EX}[{Fore.LIGHTMAGENTA_EX}{__name__}{Fore.LIGHTBLACK_EX}] {message}"
        return print(full_msg)
    @staticmethod
    def error(message: str) -> None:
        current_time = Utils.format_time()
        fornatted_time = f"{Fore.LIGHTBLACK_EX}[{Fore.LIGHTCYAN_EX}{current_time}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        formatted_status = f"{Fore.LIGHTBLACK_EX}[{Fore.RED}ERROR{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        full_msg =  f"{fornatted_time} {formatted_status} {Fore.LIGHTBLACK_EX}[{Fore.LIGHTMAGENTA_EX}{__name__}{Fore.LIGHTBLACK_EX}] {message}"
        return print(full_msg)
    @staticmethod
    def info(message: str) -> None:
        current_time = Utils.format_time()
        fornatted_time = f"{Fore.LIGHTBLACK_EX}[{Fore.LIGHTCYAN_EX}{current_time}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        formatted_status = f"{Fore.LIGHTBLACK_EX}[{Fore.YELLOW}INFO{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        full_msg =  f"{fornatted_time} {formatted_status} {Fore.LIGHTBLACK_EX}[{Fore.LIGHTMAGENTA_EX}{__name__}{Fore.LIGHTBLACK_EX}] {message}"
        return print(full_msg)
    @staticmethod
    def custom(status: str, message: str, status_color: Any = Fore.MAGENTA ) -> None:
        current_time = Utils.format_time()
        fornatted_time = f"{Fore.LIGHTBLACK_EX}[{Fore.LIGHTCYAN_EX}{current_time}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        formatted_status = f"{Fore.LIGHTBLACK_EX}[{status_color}SUCCESS{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        full_msg =  f"{fornatted_time} {formatted_status} {Fore.LIGHTBLACK_EX}[{Fore.LIGHTMAGENTA_EX}{__name__}{Fore.LIGHTBLACK_EX}] {message}"
        return print(full_msg)

class Utils:
    @staticmethod
    def format_time() -> str:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        formatted = current_time.strftime("%d/%m - %H:%M")
        return formatted
    @staticmethod
    def load_config(fp: str ="./config.json")-> Dict[Any, Any]:
        try:
            with open(fp, "r") as config_file:
                config = json.load(config_file)
                return config
        except FileNotFoundError:
            Logger.error(f"File {fp} not found")
            return False
        except json.JSONDecodeError as e:
            Logger.error(f"JSONDecodeError: {e}")
            return False

class Cogloader:
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.loaded = 0
        self.not_loaded = 0
        self.errors = []
    def get_results(self) -> Dict:
        results = {
            "loaded":self.loaded,
            "not_loaded": self.not_loaded,
            
        }
        if len(self.errors) > 0:
            results['errors'] = ', '.join(error for error in self.errors)
        return results
    def load(self):
        if os.path.exists("./cogs"):
            for file in os.listdir("./cogs"):
                if file.endswith(".py"):
                    if f"cogs.{file[:-3]}" in self.bot.extensions:
                        pass
                    else:
                        try:
                            self.bot.load_extension(f"cogs.{file[:-3]}")
                            self.loaded += 1
                        except commands.ExtensionError as e:
                            if "already" in str(e):
                                pass
                            else:
                                self.not_loaded += 1
                                self.errors.append(e)
                        except Exception as e:
                            self.not_loaded += 1
                            self.errors.append(e)
        else:
            self.errors.append("./cogs folder does not exist.")
class Bot(commands.InteractionBot): # no message commands
    def __init__(self, owner_ids, intents=disnake.Intents.all(), **kwargs):
        self.config = Utils.load_config()
        owner_ids = None
        if "owner_ids" in str(self.config).lower():
            for key, value in self.config.items():
                self.config[key] = None
                self.config[str(key).lower()] = value
            owner_ids = self.config['owner_ids']
        super().__init__(owner_ids=owner_ids, intents=intents)
        self.logger = Logger
        self.config = Utils.load_config()
        self.global_cooldown = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)
        
    #cooldown
    async def process_commands(self, message: disnake.Message):
        if message.author.bot:
            return

        bucket = self.global_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await message.channel.send(f"You're using commands too fast. Try again in {retry_after:.2f} seconds.", delete_after=5)
            return
        
        await super().process_commands(message)
        
bot = Bot()


@bot.listen("on_ready")
async def on_ready_listener():
    cogs = Cogloader(bot)
    cogs.LoadCogs()
    Logger.success(f"Bot is online as: {bot.user.name}")

@bot.event
async def on_application_command(inter: disnake.ApplicationCommandInteraction):
    bucket = bot.global_cooldown.get_bucket(inter)
    retry_after = bucket.update_rate_limit()
    if retry_after:
        await inter.response.send_message(f"You're using commands too fast. Try again in {retry_after:.2f} seconds.", ephemeral=True)
        return
    await bot.process_application_commands(inter)
    
    
if __name__ == "__main__":
    colorama.init(autoreset=True)
    print("cool ascii here")
    try:
        bot.run(bot.config.get("token"))
    except disnake.errors.LoginFailure:
        Logger.error("Improper token has been passed.")
        raise Exception("Improper token has been passed")
    except KeyboardInterrupt:
        sys.exit()