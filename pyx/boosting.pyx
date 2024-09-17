import aiohttp
from json import load

with open("config.json", "r") as file:
    data = load(file)

def PyInit_boosting():
    pass

class boosting:    

    def __init__(self):
        self.bot_token = data['token']
        self.bot_secret = data['secret']
        self.redirect_url = data['redirect']
        self.api_endpoint = data['canary_api']


    async def add_user_to_guild(self, access_token, guild_id):
            headers = {
                'Authorization': f'Bot {self.bot_token}', 
                'Content-Type': 'application/json'
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.api_endpoint}/users/@me", headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }) as user_response:
                        if user_response.status != 200:
                            raise Exception(f"Failed to get user data, status code: {user_response.status}")

                        user_data = await user_response.json()
                        user_id = user_data['id']

                        guild_payload = {
                            'access_token': access_token
                        }

                        async with session.put(f"{self.api_endpoint}/guilds/{guild_id}/members/{user_id}", headers=headers, json=guild_payload) as guild_response:
                            guild_response_text = await guild_response.text()
                            if guild_response.status in {201, 204}:
                                return True
                            else:
                                raise Exception(f"Failed to add user to guild, status code: {guild_response.status}, response: {guild_response_text}")

            except Exception as e:
                print(f"Error adding user to guild: {str(e)}")
                return False


    async def boost_user(self, boostids_list, access_token, guild_id):
        failed_boosts = 0
        if boostids_list is None:
            return False
        async with aiohttp.ClientSession() as session:
            for boost_id in boostids_list:
                boost_url = f"{self.api_endpoint}/guilds/{guild_id}/premium/subscriptions"
                headers = {
                    'Authorization': f'{access_token}',
                    'Content-Type': 'application/json'
                }
                boost_payload = {
                        "user_premium_guild_subscription_slot_ids": [f"{boost_id}"]
                }

                async with session.put(boost_url, headers=headers, json=boost_payload) as boost_response:
                    if boost_response.status not in [204, 201]:
                        print(f"Failed to apply boost, status code: {boost_response.status}, response: {await boost_response.text()}")
                        failed_boosts += 1
                        if failed_boosts == 2:
                            return False
                    print('Boost applied successfully!')
        return True


    async def process_boostids(self, access_token, guild_id):
        boostids_list = []
        async with aiohttp.ClientSession() as session:
            subscription_url = f"{self.api_endpoint}/users/@me/guilds/premium/subscription-slots"
            subscription_headers = {
                'Authorization': f"{access_token}",
                'Content-Type': 'application/json'
            }
            
            async with session.get(subscription_url, headers=subscription_headers) as subscriptions_response:
                subscriptions_response_data = await subscriptions_response.json()
                for subscription in subscriptions_response_data:
                    boostids_list.append(subscription['id'])

        return await self.boost_user(boostids_list, access_token, guild_id)


    async def remove_used_token(self, file_path, token):
        with open(file_path, 'r') as file:
            tokens = file.readlines()
        tokens = [t.strip() for t in tokens if t.strip() != token]

        with open(file_path, 'w') as file:
            for token in tokens:
                file.write(f"{token}\n")