import grabbers
import asyncio

inst_dictionary = dict()

async def main():
    # ask for username then create an object of the player
    name = input("Enter the username of the player you want to add. Example: Khazicus#9648: ")
    player = grabbers.RootPlayer(name)
    await player.setup()
    root_user_sorted = dict(sorted(player.players_raided_with.items(), key=lambda x: x[1][1], reverse=True))

    for element in root_user_sorted:
        print(root_user_sorted[element][0] + " : " + str(root_user_sorted[element][1]))
    
    # contains users connected to me and users connected to them
    full_user_dict = dict()
    full_user_dict[name] = root_user_sorted

    for other_player in root_user_sorted:
        try:
            print(root_user_sorted[other_player][0])
            player_obj = grabbers.AdjacentPlayer(root_user_sorted[other_player][0], other_player, root_user_sorted[other_player][2])
            await player_obj.setup()
            new_sort = dict(sorted(player_obj.players_raided_with.items(), key=lambda x: x[1][1], reverse=True))
            full_user_dict[player_obj.bungie_name] = new_sort
        except:
            print(f"failed to get data for {root_user_sorted[other_player][0]}")
    
    print(full_user_dict)

if __name__ == "__main__":
    asyncio.run(main())