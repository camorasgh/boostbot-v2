import colorama
import ctypes
import datetime
import disnake
import json
import os
import re
import shutil  # For getting terminal size
import sys

from colorama import Fore, Style
from disnake.ext import commands
from typing import Dict, Any


class Logger:
    @staticmethod
    def strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @staticmethod
    def get_true_length(text: str) -> int:
        """Get the true visual length of text by removing ANSI codes."""
        return len(Logger.strip_ansi(text))

    @staticmethod
    def center_with_ansi(text: str, width: int) -> str:
        """Center text while preserving ANSI color codes."""
        true_length = Logger.get_true_length(text)
        padding = max(0, width - true_length)
        left_padding = ' ' * (padding // 2)
        return f"{left_padding}{text}"  # Remove right padding to prevent overflow

    @staticmethod
    def log(message: str, status: str, status_color: Any) -> None:
        """
        Format and print log messages with proper gradients and centering.
        """
        current_time = datetime.datetime.now().strftime("%m/%d - %H:%M:%S")
        terminal_width = shutil.get_terminal_size().columns
        
        gradient_colors = [53, 55, 56, 57, 93, 129, 165, 201]

        formatted_time = Logger.apply_gradient(f"[{current_time}]", gradient_colors)
        
        # Create status with brackets
        brackets = Logger.apply_gradient("[ ]", gradient_colors)
        brackets = brackets.split(" ")
        formatted_status = f"{brackets[0]}{status_color}{status}{Fore.RESET}{brackets[1]}"

        gradient_message = Logger.apply_gradient(message, [93])

        # Combine all parts
        full_msg = f"{formatted_time} {formatted_status} {gradient_message}"
        
        # Handle multi-line messages
        lines = full_msg.split('\n')
        for i, line in enumerate(lines):
            if i == len(lines) - 1:  # Last line
                centered_msg = Logger.center_with_ansi(line.rstrip(), terminal_width)
                print(centered_msg + Style.RESET_ALL)
            else:
                centered_msg = Logger.center_with_ansi(line.rstrip(), terminal_width)
                print(centered_msg + Style.RESET_ALL + '\n')

    @staticmethod
    def apply_gradient(text: str, colors: list) -> str:
        """Applies a gradient to the given text using the specified colors."""
        return ''.join(f"\033[38;5;{colors[i % len(colors)]}m{char}" for i, char in enumerate(text))

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

    @staticmethod
    def gradient(text: str) -> str:
        """Apply default gradient to a text."""
        gradient_colors = [53, 55, 56, 57, 93, 129, 165, 201]
        return Logger.apply_gradient(text, gradient_colors)


            
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


class Cog_Loader:
    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self.loaded = 0
        self.not_loaded = 0
        self.errors = []

    def get_results(self) -> Dict:
        results = {
            "loaded": self.loaded,
            "not_loaded": self.not_loaded,
            "errors": self.errors

        }
        if len(self.errors) > 0:
            results['errors'] = ', '.join(str(error) for error in self.errors)

        return results

    def load(self):
        if not os.path.exists("./cogs"):
            self.errors.append("./cogs folder does not exist.")
            return

        for file in os.listdir("./cogs"):
            if not file.endswith(".py"):
                continue

            extension = f"cogs.{file[:-3]}"
            if extension in self.bot.extensions:
                continue

            try:
                self.bot.load_extension(extension)
                self.loaded += 1
            except commands.ExtensionError as e:
                if "already" not in str(e):
                    self.not_loaded += 1
                    self.errors.append(e)
            except Exception as e:
                self.not_loaded += 1
                self.errors.append(e)


class Banner:
    
    def __init__(self):
        self.terminal_size = None
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
        self.banner.islower()
        if os.name == 'nt':
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x4)

    def print_banner(self):
        self.enable_virtual_terminal()
        terminal_size = shutil.get_terminal_size()
        self.terminal_size = terminal_size
        banner_lines = self.banner.split("\n")
        gradient_purple = [53, 55, 56, 57, 93, 129, 165, 201]

        for i, line in enumerate(banner_lines):
            color_index = gradient_purple[i % len(gradient_purple)]
            print(f"\033[38;5;{color_index}m{line.center(terminal_size.columns)}")

        self.print_alternating_color_text(self.links, (terminal_size.columns - len(self.links)) // 2)
        print("\033[0m")

    def print_alternating_color_text(self, text):
        color1, color2 = 93, 93 #, 57
        for i, char in enumerate(text.center(self.terminal_size.columns)):
            color_code = color1 if i % 2 == 0 else color2
            print(f"\033[38;5;{color_code}m{char}", end="")
        
class Bot(commands.InteractionBot): # no message commands
    def __init__(self, intents=disnake.Intents.all(), **kwargs):

        self.config = self.load_and_validate_config()
        owner_ids = self.config.get('owner_ids', [])
        owner_ids = {int(owner_id) for owner_id in owner_ids}

        super().__init__(owner_ids=owner_ids, intents=intents, **kwargs)
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
        self.__repr__()
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


vortex = Bot()


@vortex.listen("on_ready")
async def on_ready_listener():
    cogs = Cog_Loader(vortex)
    cogs.load()
    print()

    Logger.success(f"Bot is online as: {vortex.user.name}")
    cogs_results = cogs.get_results()
    Logger.info(f"Loaded {cogs_results['loaded']} cogs")
    if cogs_results.get('not_loaded'):
        Logger.error(f"Failed to load {cogs_results['not_loaded']} cogs")
        for error in cogs_results['errors']:
            Logger.error(error)
    Logger.info(f"Registered Commands: {len(vortex.all_slash_commands)}")

@vortex.event
async def on_application_command(inter: disnake.ApplicationCommandInteraction):
    bucket = vortex.global_cooldown.get_bucket(inter) # type: ignore
    retry_after = bucket.update_rate_limit()
    if retry_after:
        await inter.response.send_message(f"You're using commands too fast. Try again in {retry_after:.2f} seconds.", ephemeral=True)
        return
    await vortex.process_application_commands(inter)


# pip install git+https://github.com/DisnakeDev/disnake.git@feature/user-apps-v2
if __name__ == "__main__":
    
    Banner = Banner()
    Banner.print_banner()
    try:
        vortex.run(vortex.config.get("token"))
        colorama.init(autoreset=True)
    except disnake.errors.LoginFailure:
        Logger.error("Improper token has been passed.")
        raise Exception("Improper token has been passed")
    except KeyboardInterrupt:
        sys.exit()