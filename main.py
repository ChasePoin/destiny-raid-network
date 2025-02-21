import grabbers

def main():
    # ask for username then create an object of the player
    name = input("Enter the username of the player you want to add. Example: Khazicus#9648: ")
    player = grabbers.Player(name)
    print(player.players_raided_with.items())
    sorted_data = dict(sorted(player.players_raided_with.items(), key=lambda x: x[1][1], reverse=True))

    print(sorted_data)
    for element in sorted_data:
        print(sorted_data[element][0] + " : " + str(sorted_data[element][1]))
    

if __name__ == "__main__":
    main()