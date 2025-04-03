import grabbers
import networkx as nx
import asyncio
import matplotlib.pyplot as plt
import os

players_searched = []
async def search_for_players(depth, root_user: grabbers.AdjacentPlayer | grabbers.RootPlayer):
    queue = [(depth, root_user)]

    while queue:
        curr_depth, player_in_question = queue.pop(0)
        if curr_depth == 0:
            continue
        for connected_player in player_in_question.players_raided_with:
            if player_in_question.players_raided_with[connected_player][0] not in players_searched:
                adjacent_player = grabbers.AdjacentPlayer(
                    player_in_question.players_raided_with[connected_player][0],
                    connected_player,
                    player_in_question.players_raided_with[connected_player][2]
                )
                # make sure we aren't searching the same users
                players_searched.append(player_in_question.players_raided_with[connected_player][0])
                # go through adjacent player
                await adjacent_player.setup()
                # add adjacent player to queue to be searched
                queue.append((curr_depth-1,adjacent_player))
        

async def main():
    # ask for username then create an object of the player
    name = input("Enter the username of the player you want to add. Example: Khazicus#9648: ")
    player = grabbers.RootPlayer(name)
    await player.setup()

    print(player.players_raided_with)
    g = nx.Graph()
    for connection in player.players_raided_with:
        g.add_edge(player.bungie_name, player.players_raided_with[connection][0], weight=player.players_raided_with[connection][1])
    # nx.draw(g,with_labels=True)

    print("Nodes:", g.nodes())
    print("Edges:", g.edges())

    # plt.show()
    players_searched.append(name)
    await search_for_players(5, player)
if __name__ == "__main__":
    asyncio.run(main())
    grabbers.CONNECT.close()