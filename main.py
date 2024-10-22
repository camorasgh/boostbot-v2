import disnake
from disnake.ext import commands
from typing import Dict, Any
import json
import colorama
from colorama import Fore
import datetime
import os
import sys
import ctypes

class Logger:
    @staticmethod
    def log(message: str, status: str, status_color: Any) -> None: # i hate pycharm errors
        """
        A helper method to format and print log messages.

        :param message: The message to log.
        :param status: The status label (e.g., 'SUCCESS', 'ERROR').
        :param status_color: The color to use for the status.
        """
        current_time = Utils.format_time()
        formatted_time = f"{Fore.LIGHTBLACK_EX}[{Fore.LIGHTCYAN_EX}{current_time}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        formatted_status = f"{Fore.LIGHTBLACK_EX}[{status_color}{status}{Fore.LIGHTBLACK_EX}]{Fore.RESET}"
        full_msg = f"{formatted_time} {formatted_status} {Fore.LIGHTBLACK_EX}[{Fore.LIGHTMAGENTA_EX}{__name__}{Fore.LIGHTBLACK_EX}] {message}"
        print(full_msg)

    @staticmethod
    def success(message: str) -> None:
        Logger.log(message, "SUCCESS", Fore.GREEN)

    @staticmethod
    def error(message: str) -> None:
        Logger.log(message, "ERROR", Fore.RED)

    @staticmethod
    def info(message: str) -> None:
        Logger.log(message, "INFO", Fore.YELLOW)

    @staticmethod
    def custom(status: str, message: str, status_color: Any = Fore.MAGENTA) -> None:
        Logger.log(message, status, status_color)

class Banner:
    
    def __init__(self):
        self.banner = r"""
 ▄▀▀▄ ▄▀▀▄  ▄▀▀▀▀▄   ▄▀▀▄▀▀▀▄  ▄▀▀▀█▀▀▄  ▄▀▀█▄▄▄▄  ▄▀▀▄  ▄▀▄ 
█   █    █ █      █ █   █   █ █    █  ▐ ▐  ▄▀   ▐ █    █   █ 
▐  █    █  █      █ ▐  █▀▀█▀  ▐   █       █▄▄▄▄▄  ▐     ▀▄▀  
   █   ▄▀  ▀▄    ▄▀  ▄▀    █     █        █    ▌       ▄▀ █  
    ▀▄▀      ▀▀▀▀   █     █    ▄▀        ▄▀▄▄▄▄       █  ▄▀  
                    ▐     ▐   █          █    ▐     ▄▀  ▄▀   
                              ▐          ▐         █    ▐    
                              
 """
        self.links = "[https://discord.gg/camora]    [https://discord.gg/borgo]"

    def enable_virtual_terminal(self):
        if os.name == 'nt':
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x4)

    def print_banner(self):
        self.enable_virtual_terminal()
        terminal_size = os.get_terminal_size()
        self.terminal_size = terminal_size
        banner_lines = self.banner.split("\n")
        gradient_purple = [53, 55, 56, 57, 93, 129, 165, 201]

        for i, line in enumerate(banner_lines):
            color_index = gradient_purple[i % len(gradient_purple)]
            print(f"\033[38;5;{color_index}m{line.center(terminal_size.columns)}")

        self.print_alternating_color_text(self.links, (terminal_size.columns - len(self.links)) // 2)
        print("\033[0m")

    def print_alternating_color_text(self, text, center):
        color1, color2 = 93 #, 57
        for i, char in enumerate(text.center(self.terminal_size.columns)):
            color_code = color1 if i % 2 == 0 else color2
            print(f"\033[38;5;{color_code}m{char}", end="")
            
class Utils:
    @staticmethod
    def format_time() -> str:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        formatted = current_time.strftime("%d/%m - %H:%M")
        return formatted

    @staticmethod
    def load_config(fp: str ="./config.json")-> Dict[Any, Any] | bool:
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
            results['errors'] = ', '.join(str(error) for error in self.errors)
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

class Banner:
    
    def __init__(self):
        self.banner = r"""
 ▄▀▀▄ ▄▀▀▄  ▄▀▀▀▀▄   ▄▀▀▄▀▀▀▄  ▄▀▀▀█▀▀▄  ▄▀▀█▄▄▄▄  ▄▀▀▄  ▄▀▄ 
█   █    █ █      █ █   █   █ █    █  ▐ ▐  ▄▀   ▐ █    █   █ 
▐  █    █  █      █ ▐  █▀▀█▀  ▐   █       █▄▄▄▄▄  ▐     ▀▄▀  
   █   ▄▀  ▀▄    ▄▀  ▄▀    █     █        █    ▌       ▄▀ █  
    ▀▄▀      ▀▀▀▀   █     █    ▄▀        ▄▀▄▄▄▄       █  ▄▀  
                    ▐     ▐   █          █    ▐     ▄▀  ▄▀   
                              ▐          ▐         █    ▐    
                              
 """
        self.links = "[https://discord.gg/camora]    [https://discord.gg/borgo]"

    def enable_virtual_terminal(self):
        if os.name == 'nt':
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x4)

    def print_banner(self):
        self.enable_virtual_terminal()
        terminal_size = os.get_terminal_size()
        self.terminal_size = terminal_size
        banner_lines = self.banner.split("\n")
        gradient_purple = [53, 55, 56, 57, 93, 129, 165, 201]

        for i, line in enumerate(banner_lines):
            color_index = gradient_purple[i % len(gradient_purple)]
            print(f"\033[38;5;{color_index}m{line.center(terminal_size.columns)}")

        self.print_alternating_color_text(self.links, (terminal_size.columns - len(self.links)) // 2)
        print("\033[0m")

    def print_alternating_color_text(self, text, center):
        color1, color2 = 93, 93 #, 57
        for i, char in enumerate(text.center(self.terminal_size.columns)):
            color_code = color1 if i % 2 == 0 else color2
            print(f"\033[38;5;{color_code}m{char}", end="")
        
class Bot(commands.InteractionBot): # no message commands
    def __init__(self, intents=disnake.Intents.all(), **kwargs):
        self.config = self.load_and_validate_config()
        owner_ids = self.config.get('owner_ids', [])
        owner_ids = {int(owner_id) for owner_id in owner_ids}

        super().__init__(owner_ids=owner_ids, intents=intents)
        self.logger = Logger
        self.global_cooldown = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

    def load_and_validate_config(self) -> Dict[str, Any]:
        config = Utils.load_config()
        if not config:
            raise ValueError("Configuration file could not be loaded.")

        config = {k.lower(): v for k, v in config.items()} #key, value

        required_keys = ['token', 'client_id', 'client_secret', 'redirect_uri', 'owner_ids']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required configuration parameter: {key}")

        return config

    #cooldown
    async def process_commands(self, message: disnake.Message):
        if message.author.bot:
            return

        bucket = self.global_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            await message.channel.send(f"You're using commands too fast. Try again in {retry_after:.2f} seconds.", delete_after=5)
            return

        await super().process_commands(message) # type: ignore


bot = Bot()


@bot.listen("on_ready")
async def on_ready_listener():
    cogs = Cogloader(bot)
    cogs.load()
    Logger.success(f"Bot is online as: {bot.user.name}")
    Logger.info(f"Loaded {cogs.get_results()}")
    Logger.info(f"Owner(s): {', '.join(str(owner) for owner in bot.owner_ids)}")
    Logger.info(f"Commands: {len(bot.all_slash_commands)}")

@bot.event
async def on_application_command(inter: disnake.ApplicationCommandInteraction):
    bucket = bot.global_cooldown.get_bucket(inter) # type: ignore
    retry_after = bucket.update_rate_limit()
    if retry_after:
        await inter.response.send_message(f"You're using commands too fast. Try again in {retry_after:.2f} seconds.", ephemeral=True)
        return
    await bot.process_application_commands(inter)


# pip install git+https://github.com/DisnakeDev/disnake.git@feature/user-apps-v2
if __name__ == "__main__":
    
    Banner = Banner()
    Banner.print_banner()
    colorama.init(autoreset=True)
    try:
        bot.run(bot.config.get("token"))
    except disnake.errors.LoginFailure:
        Logger.error("Improper token has been passed.")
        raise Exception("Improper token has been passed")
    except KeyboardInterrupt:
        sys.exit()