from colorama import Fore, Style
from disnake import InteractionContextType, ApplicationIntegrationType, ApplicationCommandInteraction, ui, TextInputStyle
from disnake.ext import commands


DEFAULT_CONTEXTS = [InteractionContextType.guild, InteractionContextType.private_channel]
DEFAULT_INTEGRATION_TYPES = [ApplicationIntegrationType.guild, ApplicationIntegrationType.user]


class Log:
    """
    Log class for custom logging functions
    """
    @staticmethod
    def err(msg):
        """
        Log an error message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTRED_EX}-{Fore.RESET}] {msg}')

    @staticmethod
    def succ(msg):
        """
        Log a success message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTMAGENTA_EX}+{Fore.RESET}] {msg}')

    @staticmethod
    def console(msg):
        """
        Log a console message
        
        Args:
        msg [str]: The message to log
        """
        print(f'{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTMAGENTA_EX}-{Fore.RESET}] {msg}')


class BoostingModal(ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        components = [
            ui.TextInput(
                label="Guild ID",
                placeholder="Enter the guild ID",
                custom_id="boosting.guild_id",
                style=TextInputStyle.short,
                min_length=18,
                max_length=19,
            ),
            ui.TextInput(
                label="Amount",
                placeholder="The amount of boosts",
                custom_id="boosting.amount",
                style=TextInputStyle.short,
                min_length=1,
                max_length=3
            ),
        ]
        super().__init__(title="Join Booster", components=components)
    # not done yet


class JoinBoost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="join",
        description="Join group handler",
        contexts=DEFAULT_CONTEXTS,
        integration_types=DEFAULT_INTEGRATION_TYPES
    )
    async def join_decorator(self, inter: ApplicationCommandInteraction):
        pass

    @join_decorator.sub_command(name="boost", description="Boost a GUILD using join")
    async def join_boost_guild(self, inter: ApplicationCommandInteraction):
        try:
            modal = BoostingModal(self.bot)
            await inter.response.send_modal(modal)
        except Exception as e:
            self.bot.logger.error(str(e)) # Unresolved attribute reference 'logger' for class 'Bot' ~ pycharm
            await inter.response.send_message("An error occurred while preparing the boost modal.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(JoinBoost(bot))