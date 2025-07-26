import os
import asyncio
import aiohttp
import sqlite3
import networkx as nx
clans_searched=[]
platforms=[]
graphilicious = nx.Graph()
HEADERS = {'X-API-KEY': os.getenv("bungie_token"), 'Content-Type': 'application/json'}

CONNECT = sqlite3.connect("path2_fixed_connected.db")
CONNECT1 = sqlite3.connect("path2_fixed_connected_c.db")

def create_database(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name1 TEXT NOT NULL,
            name2 TEXT NOT NULL,
            weight INT NOT NULL
        )
    ''')

def platform_db_entry(conn, player, platform):
    cursor = conn.cursor()
    cursor.execute('''INSERT OR IGNORE INTO platforms (name, platform)
                   VALUES (?,?)
                   ''', (player,platform))

def user_db_entry(conn, player, clan):
    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT OR IGNORE INTO clans (name, clan) 
            VALUES (?, ?)
        ''', (player, clan))
    except TypeError:
        print(f"failed to insert player {player}")

def edge_entry(conn, player1, player2, weight):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO edges (name1, name2, weight) 
            VALUES (?, ?, ?)
        ''', (player1, player2, weight))
    except TypeError: 
        print(f"Failed to insert edge from {player1} to {player2} with weight of {weight}.")

def add_edge_to_graph(graph):
    cursor = CONNECT.cursor()
    cursor.execute('SELECT name1, name2, weight FROM edges')
    edges = cursor.fetchall()
    for name1, name2, weight in edges:
        print(name1, " ", name2)
        graph.add_edge(name1,name2,weight=weight)
    return graph
        

class RootPlayer():

    def __init__(self, username, depth):
        """"
        Sets object's username and display code required for searching the root user.

        """
        # create_database(CONNECT)
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
        self.depth = depth
    
    async def setup(self):
        """
        Calls all necessary functions to get users raided with for the root user.

        """
        semaphore = asyncio.Semaphore(20)
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                await self.get_root_info(session)
                await self.get_character_ids(session)
                # await self.get_player_clan(session)
                await self.get_instance_ids(session)
                await self.get_other_players_in_activities(session)
                # await self.add_to_graph()
                # await self.add_to_platforms()
                # await self.add_to_db()
                # await self.add_to_clan_db(session)
    
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
            return await response.json(content_type=None)  

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
            for page_num in range (0,25):
                try:
                    url = f"https://www.bungie.net/Platform/Destiny2/{self.platform}/Account/{self.destiny_membership_id}/Character/{character}/Stats/Activities/?mode=4&page={page_num}"
                    tasks.append(self.fetch(session, url))
                except: 
                    raise Exception("Error while trying to request instance ids for raids.")

        responses = await asyncio.gather(*tasks)
        

        # this means we're done
        for response in responses:     
            try: response['Response']
            except KeyError: continue   
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
    
    async def get_player_clan(self, session, platform, dmid):
        # want to get player clan for attribute
        # no simple way to get it with the calls currently used, so use "GetGroupsForMember" endpoint
        try:
            url = f"https://www.bungie.net/Platform/GroupV2/User/{platform}/{dmid}/0/1/"

            response = await self.fetch(session, url)
            return response['Response']['results'][0]['group']['name']
            # players_clans[self.bungie_name] = {"clan": self.clan}
        except:
            print(f"error getting clan for user {dmid} \n {response}")
            return "None"

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
      
        for activity_id in self.instance_ids:
            try:
                url = f"https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{activity_id}/"
                tasks.append(self.fetch(session, url))
            except:
                raise Exception(f"Issue with getting activity data for {activity_id}.")
        
        responses = await asyncio.gather(*tasks)


        # we need the bungie name + platform for future requests about a user, otherwise we could just do links and weights
        for response in responses:
            try: response['Response']
            except KeyError: continue 
            from_beginning = response['Response']['activityWasStartedFromBeginning']

            if from_beginning == True:
                other_players = response['Response']['entries']
                
                for player in other_players:
                    player_data = player['player']['destinyUserInfo']
                    # need to keep track of the amount of times user has raided with another user
                    if player_data['membershipId'] in player_dictionary:
                        player_dictionary[player_data['membershipId']][1] += 1
                        
                    elif player_data['membershipId'] == self.destiny_membership_id: pass
                    else:
                        # 0 gets cut off if in front of code
                        try: 
                            player_data['bungieGlobalDisplayNameCode']
                        except KeyError: 
                            continue
                        if len(str(player_data['bungieGlobalDisplayNameCode'])) == 3:
                            appended_code = "0" + str(player_data['bungieGlobalDisplayNameCode'])
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + appended_code, 1, player_data['membershipType']]
                           
                        else:
                            player_dictionary[player_data['membershipId']] = [player_data['bungieGlobalDisplayName'] + "#" + str(player_data["bungieGlobalDisplayNameCode"]), 1, player_data['membershipType']]
                            

        self.players_raided_with = player_dictionary

        
    async def add_to_db(self):
        for other_player in self.players_raided_with:
            edge_entry(CONNECT, self.bungie_name, self.players_raided_with[other_player][0], weight=self.players_raided_with[other_player][1])
        CONNECT.commit()

    async def add_to_clan_db(self, session):
        for other_player in self.players_raided_with:
            if other_player not in clans_searched:
                clan = await self.get_player_clan(session, self.players_raided_with[other_player][2], other_player)       
                user_db_entry(CONNECT, self.players_raided_with[other_player][0], clan)  
                clans_searched.append(other_player)
        CONNECT.commit()
    
    async def add_to_platforms(self):
        for other_player in self.players_raided_with:
            if other_player not in platforms:
                platform_db_entry(CONNECT, self.players_raided_with[other_player][0],self.players_raided_with[other_player][2])
                platforms.append(other_player)
        CONNECT.commit()
    
    async def add_to_graph(self):
        if self.depth > 0:
            for other_player in self.players_raided_with:
                this_user_name = self.bungie_name
                other_user_name = self.players_raided_with[other_player][0]
                weight = self.players_raided_with[other_player][1]
                graphilicious.add_edge(this_user_name, other_user_name, weight=weight)
        else:
            for other_player in self.players_raided_with:
                if self.players_raided_with[other_player][0] in graphilicious:
                    this_user_name = self.bungie_name
                    other_user_name = self.players_raided_with[other_player][0]
                    weight = self.players_raided_with[other_player][1]
                    graphilicious.add_edge(this_user_name, other_user_name, weight=weight)     
                        
class AdjacentPlayer(RootPlayer):
    def __init__(self, username, destiny_membership_id, platform, depth):
        """ 
        Takes username, dmid, platform: these are the only things we need for the endpoints we are going to be using.

        Args:
            username (str): Bungie username in fromat: username#0000.
            destiny_membership_id (str): Destiny membership id required for certain endpoints.
            platform (str): platform the user plays on, example: steam (3), psn (1?)
        """
        print(username, destiny_membership_id, platform, depth)
        self.platform              =  platform
        self.destiny_membership_id =  destiny_membership_id
        self.bungie_name           =  username
        self.depth = depth
    async def setup(self):
        """
        Setup for any adjacent player requires character_ids -> instance_ids -> iteration through other players in instance_ids.
        """
        semaphore = asyncio.Semaphore(20)
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                await self.get_character_ids(session)
                # await self.get_player_clan(session)
                await self.get_instance_ids(session)
                await self.get_other_players_in_activities(session) 
                # await self.add_to_platforms()
                # await self.add_to_db()
                # await self.add_to_clan_db(session)
                await self.add_to_graph()



                