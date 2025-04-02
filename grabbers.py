import os
import requests
import main
import asyncio
import aiohttp
import sqlite3

HEADERS = {'X-API-KEY': os.getenv("bungie_token"), 'Content-Type': 'application/json'}

def edge_entry(conn, player1, player2, weight):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO edges (name1, name2, weight) 
            VALUES (?, ?, ?)
        ''', (player1, player2, weight))
    except TypeError as e: 
        print(f"Failed to insert edge from {player1} to {player2} with weight of {weight}.")

class RootPlayer():

    def __init__(self, username, id=None):
        """"
        Sets object's username and display code required for searching the root user.

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
        """
        Calls all necessary functions to get users raided with for the root user.

        """
        async with aiohttp.ClientSession() as session:
            await self.get_root_info(session)
            await self.get_character_ids(session)
            await self.get_instance_ids(session)
            await self.get_other_players_in_activities(session)
    
    async def fetch(self, session, url):
        """
        Makes endpoint request using the session and url.

        Args:
            session: active aiohttp client session used for fetching results from endpoints
            url: url of the endpoint to access

        Returns:
            endpoint response as json
        """
        async with session.get(url, headers=HEADERS) as response:
            return await response.json()  

    async def get_root_info(self, session):
        """
        Gets basic information for the root user that is necessary for the endpoints we are going to use.

        Args:
            session: active aiohttp client session used for fetching results from endpoints

        """
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

        Args:
            session: active aiohttp client session used for fetching results from endpoints

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

        Args:
            session: active aiohttp client session used for fetching results from endpoints

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
        Creates a dictionary of this user and all of the players they have raided with and the number of times they have reaided with them.
        ex// {'other player dmid': ['Hypwr#8749', 122, 3], 'other player dmid' : ['Lunar#0270', 107, 3] ...}
        Basically 'dmid' : [bungie username, times raided with, platform].

        Args:
            session: active aiohttp client session used for fetching results from endpoints
        """
        tasks = []
        player_dictionary = dict()
        # network_dict = dict()
        for activity_id in self.instance_ids:
            try:
                url = f"https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{activity_id}/"
                tasks.append(self.fetch(session, url))
            except:
                raise Exception(f"Issue with getting activity data for {activity_id}.")

        responses = await asyncio.gather(*tasks)

        
        for response in responses:
            from_beginning = response['Response']['activityWasStartedFromBeginning']

            if from_beginning == True:
            
                other_players = response['Response']['entries']
                
                for player in other_players:
                    player_data = player['player']['destinyUserInfo']
                    # need to keep track of the amount of times user has raided with another user
                    if player_data['membershipId'] in player_dictionary:
                        player_dictionary[player_data['membershipId']][1] += 1
                        # network_dict[self.bungie_name][player_data['bungieGlobalDisplayName']] += 1
                    elif player_data['membershipId'] == self.destiny_membership_id: pass
                    else:
                        # 0 gets cut off if in front of code
                        if len(str(player_data['bungieGlobalDisplayNameCode'])) == 3:
                            appended_code = "0" + str(player_data['bungieGlobalDisplayNameCode'])
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + appended_code, 1, player_data['membershipType']]
                            # network_dict[self.bungie_name][player_data['bungieGlobalDisplayName']] = 1
                        else:
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + str(player_data["bungieGlobalDisplayNameCode"]), 1, player_data['membershipType']]
                            # network_dict[self.bungie_name][player_data['bungieGlobalDisplayName']] = 1

        self.players_raided_with = player_dictionary
        # self.player_network_dict = network_dict
                                                                      
class AdjacentPlayer(RootPlayer):
    def __init__(self, username, destiny_membership_id, platform):
        """ 
        Takes username, dmid, platform: these are the only things we need for the endpoints we are going to be using.

        Args:
            username (str): Bungie username in fromat: username#0000.
            destiny_membership_id (str): Destiny membership id required for certain endpoints.
            platform (str): platform the user plays on, example: steam (3), psn (1?)
        """
        print(username, destiny_membership_id, platform)
        self.platform              =  platform
        self.destiny_membership_id =  destiny_membership_id
        self.bungie_name           =  username
    
    async def setup(self):
        """
        Setup for any adjacent player requires character_ids -> instance_ids -> iteration through other players in instance_ids.
        """
        async with aiohttp.ClientSession() as session:
            await self.get_character_ids(session)
            await self.get_instance_ids(session)
            await self.get_other_players_in_activities(session) 



                