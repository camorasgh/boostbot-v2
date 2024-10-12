import tls_client
import random
import time
from colorama import Fore, Style
import time
import string
import os
import threading

lc = (Fore.RESET + "[" + Fore.LIGHTMAGENTA_EX + ">" + Fore.RESET + "]")

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


class DiscordJoinerPY:
    """
    Discord Joiner Class
    """
    def __init__(self):
        """
        Initializer Function
        """
        self.done_event = threading.Event()
        self.not_joined_count = 0
        self.joined_count = 0
        
        self.boosted_count = 0
        self.not_boosted_count = 0
        self.joined_tokens_lock = threading.Lock()
        self.client = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
        self.tokens = []
        self.proxies = []
        self.check()
        

    def write_joined_token(self, token, invite):
        """
        Write the joined token to a file
        Args:
        token [str]: The token to write
        invite [str]: The invite of the server
        """
        with self.joined_tokens_lock:
            with open("output/" + invite + ".txt", "a") as f:
                f.write(f"{token}\n")
            with open("input/tokens.txt", "r") as f:
                lines = f.readlines()
            if token in lines:
                lines.remove(token)
                with open("input/tokens.txt", "w") as f:
                    f.writelines(lines) #PORCODIOOOOOOOOOOOOOOOOOOOOOOOOOOO NON FUNZIONA

    def headers(self, token: str):
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
        return headers #hardcoded things cuz idk but it works godly
    

    def get_cookies(self):
        """
        Retrieve cookies dict
        """
        cookies = {}
        try:
          response = self.client.get('https://discord.com')
          for cookie in response.cookies:
            if cookie.name.startswith('__') and cookie.name.endswith('uid'):
                cookies[cookie.name] = cookie.value
          return cookies
        
        except Exception as e:
          Log.err('Failed to obtain cookies ({})'.format(e))
          return cookies

    def boost(self, token: str, guild_id:str, boost_id:str, proxy_:str):
        """
        Boost a discord server
        token [str]: The token to boost the server with
        guild_id [str]: The ID of the guild to boost
        boost_id [str]: The ID of the empty boost slot
        proxy_ [str] The proxy to use to handle connections
        """
        try:
            
            payload = {"user_premium_guild_subscription_slot_ids": [int(boost_id)]}
            
            proxy = {
                "http": "http://{}".format(proxy_),
                "https": "https://{}".format(proxy_)

            } if proxy_ else None
            
            response = self.client.put(
                url=f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions",
                headers=self.headers(token=token),
                json=payload,
                cookies=self.get_cookies(),
                proxy=proxy
            )
            response_json = response.json()
            #print(response_json)
            if response.status_code == 201:
                Log.succ("Boosted! {} ({})".format(token, guild_id))
                self.boosted_count += 1
            elif response.status_code == 401 and response_json['message'] == "401: Unauthorized":
                Log.err('Invalid Token ({})'.format(token))
                self.not_boosted_count += 1
            elif "You need to verify your account in order to perform this action." in response.text:
                Log.err('Flagged Token ({})'.format(token))
                self.not_boosted_count += 1
            elif 'You need to update your app to join this server.' in response.text:
                Log.err('\033[0;31m Hcaptcha ({})'.format(token))
                self.not_boosted_count += 1
            elif "404 Not Found" in response.text:
                Log.err('Unknown invite ({})'.format(guild_id))
            elif "Must wait for premium server subscription cooldown to expire" in response.text:
                Log.err("\033[0;31m Boosts not expired ({})".format(token))
            else:
                Log.err('Invalid response ({})'.format(response_json))
                self.not_boosted_count += 1
        except Exception as e:
            Log.err('Unknown error occurred in boosting guild: {}'.format(e))
            self.not_boosted_count += 1
    def get_boost_data(self, token:str, proxy_:str):
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
                url=f"https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
                headers=self.headers(token=token),
                cookies=self.get_cookies(),
                proxy=proxy
            )
            
            response_json = response.json()
            if response.status_code == 200:
                if len(response_json) > 0:
                    boost_ids = [boost['id'] for boost in response_json]
                    #Log.console(boost_ids)
                    return boost_ids
            elif response.status_code == 401 and response_json['message'] == "401: Unauthorized":
                Log.err('Invalid Token ({})'.format(token))
            elif response.status_code == 403 and response_json['message'] == "You need to verify your account in order to perform this action.":
                Log.err('Flagged Token ({})'.format(token))
            elif response.status_code == 400 and response_json['captcha_key'] == ['You need to update your app to join this server.']:
                Log.err('\033[0;31m Hcaptcha ({})'.format(token))
            elif response_json['message'] == "404: Not Found":
                Log.err("No Nitre")
            else:
                Log.err('Invalid response ({})'.format(response_json))
            return None
        except Exception as e:
            Log.err('Unknown error occurred in boosting guild: {}'.format(e))
            return None
    def accept_invite(self, token: str, invite: str, proxy_: str):
        """
        Accept an invite
        token [str]: The token to boost the server with
        invite [str]: The invite of the guild
        proxy_ [str] The proxy to use to handle connections
        """
        try:
            payload = {
                'session_id': ''.join(random.choice(string.ascii_lowercase) + random.choice(string.digits) for _ in range(16))
            }

            proxy = {
                "http": "http://{}".format(proxy_),
                "https": "https://{}".format(proxy_)

            } if proxy_ else None

            response = self.client.post(
                url='https://discord.com/api/v9/invites/{}'.format(invite),
                headers=self.headers(token=token),
                json=payload,
                cookies=self.get_cookies(),
                proxy=proxy
            )
            response_json = response.json()
            
            if response.status_code == 200:
                Log.succ('Joined! {} ({})'.format(token, invite))
                self.write_joined_token(token, invite)
                self.joined_count += 1
                #print(response_json)
                boost_ids = self.get_boost_data(token=token, proxy_=proxy_)
                guild_id = response.json()['guild']['id']
                #print("GUild:", guild_id)
                for idd in boost_ids:
                    #print("ID", idd)
                    #print("IDS", boost_ids)
                    self.boost(token, guild_id, idd, proxy_)
                return True, response_json["guild"]["id"]
            elif response.status_code == 401 and response_json['message'] == "401: Unauthorized":
                Log.err('Invalid Token ({})'.format(token))
                self.not_joined_count += 1
                return False, None
            elif response.status_code == 403 and response_json['message'] == "You need to verify your account in order to perform this action.":
                Log.err('Flagged Token ({})'.format(token))
                self.not_joined_count += 1
                return False, None
            elif response.status_code == 400 and response_json['captcha_key'] == ['You need to update your app to join this server.']:
                Log.err('\033[0;31m Hcaptcha ({})'.format(token))
                self.not_joined_count += 1
                return False, None
            elif response_json['message'] == "404: Not Found":
                Log.err('Unknown invite ({})'.format(invite))
                self.not_joined_count += 1
                return False, None
            else:
                Log.err('Invalid response ({})'.format(response_json))
                self.not_joined_count += 1
                return False, None

        except Exception as e:
            Log.err('Unknown error occurred in accept_invite: {}'.format(e))
            self.not_joined_count += 1
            return False, None



    def check(self):
        """
        Checks if paths exists
        """
        folder_path = "input"
        file_path = os.path.join(folder_path, "tokens.txt")

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if not os.path.exists(file_path):
            for file_name in ['proxies.txt', 'tokens.txt']:
                file_path = os.path.join(folder_path, file_name)
                if not os.path.exists(file_path):
                    with open(file_path, "w") as file:
                        file.write("Delete! proxies: ip:port:host:pass")

        self.load_tokens()


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
                    if len(parts) >= 3:
                        token = parts[-1]
                    elif (
                        len(parts) == 1
                    ):  #  simple token
                        token = parts[0]
                    else:
                        # Invalid token format, skip it
                        continue
                    if token:  # Check if token is not an empty string
                        tokens.append(token)
        self.tokens.extend(tokens)

        

        self.start()

    

    def load_proxies(self):
        """
        Load proxies from a file
        """
        with open("./input/proxies.txt", "r") as file:
           for line in file:
             content = line.replace("\n",  "")
             self.proxies.append(content)

    def print_results(self):
        """
        Print the boosting results
        """
        print(f"{Fore.RESET}{Style.BRIGHT}[{Fore.LIGHTGREEN_EX}RESULTS{Fore.RESET}] Joined Tokens: {self.joined_count}, Failed Tokens: {self.not_joined_count}, Boosted Tokens: {self.boosted_count}, Failed Boosted Tokens: {self.not_boosted_count}")
        return self.joined_count, self.not_joined_count, self.boosted_count, self.not_boosted_count
    def wait_for_completion(self):
        self.done_event.wait()


    def start(self):
        """
        Start the boosting process
        """
        os.system("title discord.gg/unkn0wn ")
        self.iterator = iter(self.proxies)
        self.load_proxies()
        os.system("cls")
        print(f"""{Fore.LIGHTMAGENTA_EX}
Booster (?)
""")
        available = len(self.tokens) * 2
        import re
        while True:
                invite_code = option = input(
    lc + "Invite code: discord.gg/"

)   
                #invite_code = self.sinput(f"[{times()}] [>] Invite code: discord.gg/")
                match = re.search(
                    r"(discord\.gg/|discord\.com/invite/)?([a-zA-Z0-9-]+)$", invite_code
                )
                if match:
                    invite_code = match.group(2)
                else:
                    pass
                break
        
        amount = int(input("Boosts? (Available: %s) " % available))
        if (
                    amount <= available and amount % 2 == 0
                ):  # CHeck if even and max amount
                    pass
        else:
                    if amount % 2 == 0:
                        Log.err("Amount must be an even number")
                    elif amount <= available:
                        Log.err("Amount surpasses the available boosts amount")
                    else:
                        Log.err("Unhandled err")
        tokenCount = amount // 2
        if len(self.tokens) >= tokenCount:
            tokens = self.tokens[:tokenCount]
        ts = []
        for token in tokens:
            if self.proxies == [] or self.proxies[0] == "/// Remove this line":
                proxy = None
            else:
                proxy = next(self.iterator)
                Log.succ('Using ({})'.format(proxy))

            ts.append(threading.Thread(target=self.accept_invite, args=(token, invite_code, proxy)))
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        
        self.done_event.set()
if __name__ == '__main__':
    joiner = DiscordJoinerPY()
    joiner.wait_for_completion()
    Joined, NotJoined, Boosted, NotBoosted = joiner.print_results()
    input("")