import os
import requests
import main
import asyncio
import aiohttp

HEADERS = {'X-API-KEY': os.getenv("bungie_token"), 'Content-Type': 'application/json'}


class RootPlayer():

    def __init__(self, username, id=None):
        """"
        All relevant information relating to the player.

        """
        if '#' not in username:
            raise Exception("Please include the # with the 4 digits in the name.")
        self.username = username
        # need to split numbers and name to properly and accurately perform user search
        splitString = self.username.split("#")
        self.displayName = splitString[0]
        self.displayNameCode = splitString[1]
        if self.displayNameCode[0] == "0":
            self.displayNameCode = self.displayNameCode[1:]

        print(self.displayName + ' ' + self.displayNameCode)
    
    async def setup(self):
        async with aiohttp.ClientSession() as session:
            await self.get_starting_info(session)
            await self.get_character_ids(session)
            await self.get_instance_ids(session)
            await self.get_other_players_in_activities(session)
    
    async def fetch(self, session, url):
        async with session.get(url, headers=HEADERS) as response:
            return await response.json()  

    async def get_starting_info(self, session):
        try: 
            url = f'https://www.bungie.net/Platform/User/Search/Prefix/{self.displayName}/0/'
            response = await self.fetch(session, url)
        except:
            raise Exception("Error when searching user. Make sure the name and digits are correct.")

        # get any user with that prefix, then specifically search for the user with the numbers provided
        listOfUsers = response['Response']['searchResults']
        for user in listOfUsers:
            if user['bungieGlobalDisplayName'] == self.displayName and user['bungieGlobalDisplayNameCode'] == int(self.displayNameCode):
                # need bungie id, destiny id, platform for instance ids
                self.platform              =  user['destinyMemberships'][0]['membershipType']
                self.destiny_membership_id =  user['destinyMemberships'][0]['membershipId']
                self.bungie_name           =  self.username
                      


    async def get_character_ids(self, session) -> list:
        """"
        Gets character ids due to instance ids being stored per character.

        """
        try:
            url = f"https://www.bungie.net/Platform/Destiny2/{self.platform}/Profile/{self.destiny_membership_id}/?components=Profiles,Characters"
            response = await self.fetch(session, url)
        except:
            raise Exception("character issue")
            # exits because there is no point if character ids can not be accessed

        self.character_ids = response['Response']['profile']['data']['characterIds']
        



    async def get_instance_ids(self, session) -> list:
        """
        Uses the activity history endpoint in order to get all raid instance ids for a player.

        Raises:
            Exception: If the request for a page of instance ids throws an error.

        Returns:
            list: All instance ids of raids for a player.
        """
        
        instance_ids = []
        tasks = []
        # limit to 50 pages for now
        for character in self.character_ids:
            for page_num in range (0,50):
                try:
                    url = f"https://www.bungie.net/Platform/Destiny2/{self.platform}/Account/{self.destiny_membership_id}/Character/{character}/Stats/Activities/?mode=4&page={page_num}"
                    tasks.append(self.fetch(session, url))
                except: 
                    raise Exception("Error while trying to request instance ids for raids.")

        responses = await asyncio.gather(*tasks)
        

        # this means we're done
        for response in responses:        
            if response['Response'] == {}:
                pass # print(len(instance_ids)) # total successfully finished raids
            else:
                # probably a good idea to store a dictionary of a player with their instance ids in case of duplicate look ups? maybe, will just do an array for now
                activities = response['Response']['activities']

                # move through every single instance of a raid, only adding succesfully completed raids
                for activity in activities:
                    instanceId = activity['activityDetails']['instanceId']
                    if activity['values']['completed']['basic']['value'] == 1.0:
                        instance_ids.append(instanceId)
        self.instance_ids = instance_ids
    

    async def get_other_players_in_activities(self, session):
        """
        Converts a list of instance ids into a list of players this user has succesfully completed a raid with.

        Args:
            instance_ids (list): List of player's raid instance ids.
        """
        player_dictionary = dict()
        tasks = []
        
        for activity_id in self.instance_ids:
            try:
                url = f"https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{activity_id}/"
                tasks.append(self.fetch(session, url))
            except:
                raise Exception(f"Issue with getting activity data for {activity_id}.")

        responses = await asyncio.gather(*tasks)
            # we only want full completions, can skip checkpoints
        for response in responses:
            from_checkpoint = response['Response']['activityWasStartedFromBeginning']
            # print(from_checkpoint)
            if from_checkpoint == True:

                other_players = response['Response']['entries']
                
                for player in other_players:
                    player_data = player['player']['destinyUserInfo']
                    # need to keep track of the amount of times user has raided with another user
                    if player_data['membershipId'] in player_dictionary:
                        player_dictionary[player_data['membershipId']][1] += 1
                    elif player_data['membershipId'] == self.destiny_membership_id: pass
                    else:
                        # 0 gets cut off if in front of code
                        if len(str(player_data['bungieGlobalDisplayNameCode'])) == 3:
                            appended_code = "0" + str(player_data['bungieGlobalDisplayNameCode'])
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + appended_code, 1, player_data['membershipType']]
                        else:
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + str(player_data["bungieGlobalDisplayNameCode"]), 1, player_data['membershipType']]

                # keep track of each instance's activity id and players within it
                # if activity_id in main.inst_dictionary:
                #     main.inst_dictionary[activity_id].append(player_data['membershipId'])
                # else:
                #     main.inst_dictionary[activity_id] = [player_data['membershipId']]
        self.players_raided_with = player_dictionary
                                                                      
class AdjacentPlayer(RootPlayer):
    def __init__(self, username, destiny_membership_id, platform):
        print(username, destiny_membership_id, platform)
        self.platform              =  platform
        self.destiny_membership_id =  destiny_membership_id
        self.bungie_name           =  username
    
    async def setup(self):
        async with aiohttp.ClientSession() as session:
            await self.get_character_ids(session)
            await self.get_instance_ids(session)
            await self.get_other_players_in_activities(session) 



                