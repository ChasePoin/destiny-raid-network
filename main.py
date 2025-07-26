import grabbers
import networkx as nx
import asyncio
import matplotlib.pyplot as plt
import os

players_searched = []

async def search_through_group(player_in_question, start, end, curr_depth, queue):
        tasks = [] 
        # searches through start to end of passed in user's raided with users
        for connected_player in list(player_in_question.players_raided_with.items())[start:end]:
            player_name = connected_player[1][0]
            player_id = connected_player[0]
            player_platform = connected_player[1][2]
            # if the player in their list is not already searched make an object of them
            if player_name not in players_searched:
                adjacent_player = grabbers.AdjacentPlayer(
                    player_name,
                    player_id,
                    player_platform,
                    curr_depth
                )
                # append it to players searched
                players_searched.append(player_name)
                # go through adjacent player
                try: 
                    # search every user in the adjacent user, allowing it to have a list of users raided with
                    tasks.append(adjacent_player.setup())
                    # now add the adjacent user in unless depth is 0
                    if curr_depth > 0:
                        queue.append((curr_depth-1,adjacent_player))
                except:
                    print(f"failed to add search/append {player_name}")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"Task failed with exception: {result}")

# async def use_for_end(player_in_question, start, end, curr_depth):
#     tasks = []
#     for connected_player in list(player_in_question.players_raided_with.items())[start:end]:
#         player_name = connected_player[1][0]
#         player_id = connected_player[0]
#         player_platform = connected_player[1][2]  
#         if player_name not in players_searched:
#             adjacent_player = grabbers.AdjacentPlayer(
#                 player_name,
#                 player_id,
#                 player_platform,
#                 curr_depth
#             )
#             players_searched.append(player_name)
#             # go through adjacent player
#             try: 
#                 # search every user in the adjacent user, allowing it to have a list of users raided with
#                 tasks.append(adjacent_player.setup())
#     pass

async def search_for_players(depth, root_user: grabbers.AdjacentPlayer | grabbers.RootPlayer):
    queue = [(depth, root_user)]

    while queue:
        curr_depth, player_in_question = queue.pop(0)
        # if curr_depth == 0:
        #     try:
        #         # depth 0 we want to check if the last set of nodes has connections to anyone else already present in the network
        #         for i in range(0,len(player_in_question.players_raided_with), 20):
        #             if i + 20 > len(player_in_question.players_raided_with):
        #                 start = i
        #                 end = len(player_in_question.players_raided_with)
        #             else:
        #                 start = i
        #                 end = i + 20
        #             await use_for_end(player_in_question, start, end, curr_depth)
        #     except:
        #         print(f"error for {player_in_question.bungie_name}")
        #     continue
        try:
            for i in range(0,len(player_in_question.players_raided_with), 20):
                if i + 20 > len(player_in_question.players_raided_with):
                    start = i
                    end = len(player_in_question.players_raided_with)
                else:
                    start = i
                    end = i + 20
                await search_through_group(player_in_question,start,end,curr_depth,queue)
        except:
            print(f"failed user {player_in_question.bungie_name}")
            continue


async def main():
    # ask for username then create an object of the player
    name = input("Enter the username of the player you want to add. Example: Khazicus#9648: ")
    player = grabbers.RootPlayer(name, 2)
    await player.setup()

    print(player.players_raided_with)
    
    players_searched.append(name)
    await search_for_players(1, player)
    
    nx.write_gml(grabbers.graphilicious, "nooticing.gml")
    # nx.set_node_attributes(g, grabbers.players_clans)
    # grabbers.add_edge_to_graph(g)
    # nx.write_gml(g, "path2_degree_1_graph_with_attr.gml")
if __name__ == "__main__":
    asyncio.run(main())
    grabbers.CONNECT.close()