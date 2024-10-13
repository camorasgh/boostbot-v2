import tls_client

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

class Filemanager:
    def __init__():
        pass

    @staticmethod
    def load_tokens(self):
        """
        Load tokens from a file
        """
        tokens = []
        with open("./input/tokens.txt", "r") as file:
                tokenlist = file.readlines()
                for token in tokenlist:
                    token = token.strip()
                    parts = token.split(":")
                    if len(parts) >= 3: # mail:pass:token
                        token = parts[-1]
                    elif (len(parts) == 1):  # token only
                        token = parts[0]
                    else:
                        # Invalid token format, skipping
                        continue
                    if token:  # if token not empty string
                        tokens.append(token)
                if tokens == None:
                    Log.console("No tokens inside of ./input/tokens.txt")
        return tokens


class Tokenmanager:
    def __init__(self, bot):
        self.bot = bot
        self.client = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )


    @staticmethod
    def headers(token: str):
        """
        Construct the headers
        Args:
        token [str]: The token used to construct the headers
        """
        headers = {
            'authority': 'discord.com',
            'accept': '*/*',
            'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'authorization': token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'x-context-properties': 'eyJsb2NhdGlvbiI6IkpvaW4gR3VpbGQiLCJsb2NhdGlvbl9ndWlsZF9pZCI6IjExMDQzNzg1NDMwNzg2Mzc1OTEiLCJsb2NhdGlvbl9jaGFubmVsX2lkIjoiMTEwNzI4NDk3MTkwMDYzMzIzMCIsImxvY2F0aW9uX2NoYW5uZWxfdHlwZSI6MH0=',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-GB',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6Iml0LUlUIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExMi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTEyLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjE5MzkwNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbCwiZGVzaWduX2lkIjowfQ==',
        }
        return headers # "hardcoded things cuz idk but it works godly" ~ borgo 2k24


    def get_boost_ids(self, token:str, proxy_:str):
        """
        Get the boost slots
        token [str]: The token to boost the server with
        proxy_ [str] The proxy to use to handle connections
        """
        try:
            proxy = {
                "http": "http://{}".format(proxy_),
                "https": "https://{}".format(proxy_)

            } if proxy_ else None
            response = self.client.get(
                url=f"https://canary.discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
                headers=self.headers(token=token),
                cookies=self.get_cookies(),
                proxy=proxy
            )
            
            response_json = response.json()
            if response.status_code == 200:
                if len(response_json) > 0:
                    boost_ids = [boost['id'] for boost in response_json]
                    return boost_ids # yippeee
            elif response.status_code == 401 and response_json['message'] == "401: Unauthorized":
                Log.err('Invalid Token ({})'.format(token))
            elif response.status_code == 403 and response_json['message'] == "You need to verify your account in order to perform this action.":
                Log.err('Flagged Token ({})'.format(token))
            elif response.status_code == 400 and response_json['captcha_key'] == ['You need to update your app to join this server.']:
                Log.err('\033[0;31m Hcaptcha ({})'.format(token))
            elif response_json['message'] == "404: Not Found":
                Log.err("No Nitro") # D:
            else:
                Log.err('Invalid response ({})'.format(response_json))
            return None
        
        except Exception as e:
            Log.err('Unknown error occurred in boosting guild: {}'.format(e))
            return None
        

class BoostingModal(ui.Modal):
    def __init__(self, bot) -> None:
        self.bot = bot
        components = [
            ui.TextInput(
                label="Guild Invite",
                placeholder="Enter the guild invite",
                custom_id="boosting.guild_invite",
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
    # not done yet ; borgo send help with callback

# TODO:
# check valid invite
# check valid boost amount
# check valid token counts
# we prob might just handle invite errors and token errors directly in joining to avoid making lot of requests
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
