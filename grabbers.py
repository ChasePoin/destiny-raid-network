import os
import requests
import main

HEADERS = {'X-API-KEY': os.getenv("bungie_token"), 'Content-Type': 'application/json'}


class RootPlayer():

    def __init__(self, username, id=None):
        """"
        All relevant information relating to the player.

        """
        if '#' not in username:
            raise Exception("Please include the # with the 4 digits in the name.")
        
        # need to split numbers and name to properly and accurately perform user search
        splitString = username.split("#")
        displayName = splitString[0]
        displayNameCode = splitString[1]
        if displayNameCode[0] == "0":
            displayNameCode = displayNameCode[1:]

        print(displayName + ' ' + displayNameCode)

        # deprecated ?
        try: 
            url = f'https://www.bungie.net/Platform/User/Search/Prefix/{displayName}/0/'
            response = requests.get(url, headers=HEADERS)
            response = response.json()
        except:
            raise Exception("Error when searching user. Make sure the name and digits are correct.")

        # try:
        #     url = f'https://www.bungie.net/Platform/User/Search/GlobalName/{pagenum}/'
        #     name = {'displayNamePrefix': displayName}
        #     response = requests.post(url, json=name, headers=HEADERS)
        #     response = response.json()
        # except:
        #     raise Exception("Error when searching user AGAIN.")
        
        print(response)        
        # get prefix and numbers, important for verifying correct user

        # get any user with that prefix, then specifically search for the user with the numbers provided
        listOfUsers = response['Response']['searchResults']
        for user in listOfUsers:
            if user['bungieGlobalDisplayName'] == displayName and user['bungieGlobalDisplayNameCode'] == int(displayNameCode):
                # need bungie id, destiny id, platform for instance ids
                self.platform              =  user['destinyMemberships'][0]['membershipType']
                self.destiny_membership_id =  user['destinyMemberships'][0]['membershipId']
                self.bungie_name           =  username

        self.character_ids = self.get_character_ids(self.platform, self.destiny_membership_id)
        self.instance_ids = self.get_instance_ids(self.destiny_membership_id,self.platform,self.character_ids)
        self.players_raided_with = self.get_other_players_in_activities(self.instance_ids)
                
            



    def get_character_ids(self, platform, destiny_membership_id) -> list:
        """"
        Gets character ids due to instance ids being stored per character.

        """
        try:
            url = f"https://www.bungie.net/Platform/Destiny2/{platform}/Profile/{destiny_membership_id}/?components=Profiles,Characters"
            response = requests.get(url, headers=HEADERS)
        except:
            print("Unable to get character information. Exiting...")
            exit()
            # exits because there is no point if character ids can not be accessed
        
        profileData = response.json()

        data = profileData['Response']['profile']['data']
        # general profile data

        all_character_ids =  data['characterIds']

        return all_character_ids


    def get_instance_ids(self, destiny_membership_id, platform, character_ids) -> list:
        """
        Uses the activity history endpoint in order to get all raid instance ids for a player.

        Raises:
            Exception: If the request for a page of instance ids throws an error.

        Returns:
            list: All instance ids of raids for a player.
        """
        page_num = 0
        instance_ids = []
        # limit to 50 pages for now
        for character in character_ids:
            for page_num in range (0,50):
                try:
                    url = f"https://www.bungie.net/Platform/Destiny2/{platform}/Account/{destiny_membership_id}/Character/{character}/Stats/Activities/?mode=4&page={page_num}"
                    response = requests.get(url, headers=HEADERS)
                except: 
                    raise Exception("Error while trying to request instance ids for raids.")

                response = response.json()

                # this means we're done
                if response['Response'] == {}:
                    # print(len(instance_ids)) total successfully finished raids
                    break
                
                # probably a good idea to store a dictionary of a player with their instance ids in case of duplicate look ups? maybe, will just do an array for now
                activities = response['Response']['activities']

                # move through every single instance of a raid, only adding succesfully completed raids
                for i, _ in enumerate(activities):
                    instanceId = activities[i]['activityDetails']['instanceId']
                    if activities[i]['values']['completed']['basic']['value'] == 1.0:
                        instance_ids.append(instanceId)
            
        return instance_ids
    

    def get_other_players_in_activities(self, instance_ids):
        """
        Converts a list of instance ids into a list of players this user has succesfully completed a raid with.

        Args:
            instance_ids (list): List of player's raid instance ids.
        """
        player_dictionary = dict()
        
        for activity_id in instance_ids:
            try:
                url = f"https://www.bungie.net/Platform/Destiny2/Stats/PostGameCarnageReport/{activity_id}/"
                response = requests.get(url, headers=HEADERS)
            except:
                raise Exception(f"Issue with getting activity data for {activity_id}.")
            response = response.json() 

            # we only want full completions, can skip checkpoints
            from_checkpoint = response['Response']['activityWasStartedFromBeginning']
            # print(from_checkpoint)
            if from_checkpoint == True:

                other_players = response['Response']['entries']

                # FOR LATER: STORE USED INSTANCE IDS TO SPEED UP PROCESSOR FOR OTHER PLAYERS
                
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
                    if activity_id in main.inst_dictionary:
                        main.inst_dictionary[activity_id].append(player_data['membershipId'])
                    else:
                        main.inst_dictionary[activity_id] = [player_data['membershipId']]
        return player_dictionary
                                                                      
class AdjacentPlayer(RootPlayer):
    def __init__(self, username, destiny_membership_id, platform):
        self.platform              =  platform
        self.destiny_membership_id =  destiny_membership_id
        self.bungie_name           =  username

        self.character_ids = self.get_character_ids(self.platform, self.destiny_membership_id)
        self.instance_ids = self.get_instance_ids(self.destiny_membership_id,self.platform,self.character_ids)
        self.players_raided_with = self.get_other_players_in_activities(self.instance_ids)   


# TO DO: ADD GLOBAL INSTANCE TRACKER TO NOT REDO DATA
# TO DO: CHANGE INIT TO TAKE PLATFORM, MEMBERSHIP ID; CHANGE GET_OTHER_PLAYERS TO PUT PLATFORM IN THE DICTIONARY
                