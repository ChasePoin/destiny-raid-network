import grabbers

inst_dictionary = dict()

def main():
    # ask for username then create an object of the player
    name = input("Enter the username of the player you want to add. Example: Khazicus#9648: ")
    player = grabbers.Player(name)
    print(player.players_raided_with.items())
    sorted_data = dict(sorted(player.players_raided_with.items(), key=lambda x: x[1][1], reverse=True))

    print(sorted_data)
    for element in sorted_data:
        print(sorted_data[element][0] + " : " + str(sorted_data[element][1]))
    
    # contains users connected to me and users connected to them
    full_user_dict = dict()
    full_user_dict[name] = sorted_data

    for other_player in sorted_data:
        print(sorted_data[other_player][0])
        player_obj = grabbers.Player(sorted_data[other_player][0])
        sorted_data = dict(sorted(player_obj.players_raided_with.items(), key=lambda x: x[1][1], reverse=True))
        full_user_dict[player_obj.bungie_name] = sorted_data
    
    for user in full_user_dict:
        print(user + "has raided with " + full_user_dict[user][0] + " " + 
              full_user_dict[user][1] + " times.")  

if __name__ == "__main__":
    main()