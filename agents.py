from collections import Counter, deque, namedtuple
import copy
from gameConstants import *
import random
import time
from draw import choose_edge, choose_hex, choose_vertex
import math
from board import Edge, Hexagon, Vertex  # Add Hexagon and Vertex here
import pygame
import numpy as np
import pickle
import os
import re
import numpy as np

Experience = namedtuple('Experience', ['state', 'action', 'next_state', 'reward', 'gameState', 'priority'])

def builderEvalFn(currentGameState, currentPlayerIndex):
    currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
    return 5 * len(currentPlayer.settlements) + 5 * len(currentPlayer.cities) + 2 * len(currentPlayer.roads)

def defaultEvalFn(currentGameState, currentPlayerIndex):
    currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
    otherPlayer = currentGameState.playerAgents[1-currentPlayerIndex]
    return (3 * len(currentPlayer.settlements) + 5 * len(currentPlayer.cities) + len(currentPlayer.roads)
        - (2 * len(otherPlayer.settlements) + 4 * len(otherPlayer.cities) + len(otherPlayer.roads)))

def betterEvalFn(currentGameState, currentPlayerIndex):
    board = currentGameState.board
    currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
    otherPlayer = currentGameState.playerAgents[1-currentPlayerIndex]
    currentResourceTouches = getResourceTouches(currentPlayer.settlements, board)
    otherResourceTouches = getResourceTouches(otherPlayer.settlements, board)
    return 3 * len(currentResourceTouches) + 2 * len(currentPlayer.cities)

def getResourceTouches(settlements, board):
    resourceTouches = []
    for settlement in settlements:
        hexes = board.getHexes(settlement)
        resourceTouches.extend(hexes)
    return resourceTouches

def resourceEvalFn(currentGameState, currentPlayerIndex):
    currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
    return sum(currentPlayer.resources.values())

def valueFunctionEvalFn(currentGameState, currentPlayerIndex):
    pass 


class DiceAgent:
    def __init__(self, numDiceSides = 6):
        self.agentType = AGENT.DICE_AGENT
        self.NUM_DICE_SIDES = numDiceSides

    def rollDice(self):
        return random.randint(1, self.NUM_DICE_SIDES) + random.randint(1, self.NUM_DICE_SIDES)

    def getRollDistribution(self):
        totalRolls = 0
        rollCounter = Counter()
        for dice1 in range(1, self.NUM_DICE_SIDES + 1):
            for dice2 in range(1, self.NUM_DICE_SIDES + 1):
                rollCounter[dice1 + dice2] += 1
                totalRolls += 1
        return [(roll, rollCounter[roll] / float(totalRolls)) for roll in rollCounter]

    def deepCopy(self):
        return DiceAgent()

class DevCard:
    def __init__(self, card_type):
        self.type = card_type
        self.can_be_used = False
        self.has_been_used = False
        if card_type == DevCardTypes.VICTORY_POINT:
            self.has_been_used = True  # Victory points are always "used"

    def make_usable(self):
        self.can_be_used = True

    def use(self):
        if self.can_be_used and not self.has_been_used:
            self.has_been_used = True
            self.can_be_used = False
            return True
        return False

    def deepCopy(self):
        newCard = DevCard(self.type)
        newCard.can_be_used = self.can_be_used
        newCard.has_been_used = self.has_been_used
        return newCard
    
    def __repr__(self):
        status = "Used" if self.has_been_used else "Usable" if self.can_be_used else "Not Usable"
        return f"{self.type.name}: {status}"

class PlayerAgent(object):
    def __init__(self, name, agentIndex, color, depth=3, evalFn=defaultEvalFn):
        self.agentType = AGENT.PLAYER_AGENT
        self.evaluationFunction = evalFn
        self.name = name
        self.agentIndex = agentIndex
        self.color = color
        self.victoryPoints = 2  # Each player starts with initial settlements giving 2 VP
        self.depth = depth
        self.draw = None

        self.roads = []
        self.settlements = []
        self.cities = []

        self.numRoads = 2
        self.numSettlements = 2
        self.numCities = 0

        self.hasLongestRoad = False
        self.longestRoadLength = 0

        self.resources = Counter({
            ResourceTypes.WOOL: 0,
            ResourceTypes.BRICK: 0,
            ResourceTypes.ORE: 0,
            ResourceTypes.GRAIN: 0,
            ResourceTypes.LUMBER: 0,
        })

        self.dev_cards = []
        self.played_knights = 0
        self.has_largest_army = False
        self.dev_card_played_this_turn = False

    def __repr__(self):
        s = f"---------- {self.name} : {self.color} ----------\n"
        s += f"Victory points: {self.victoryPoints}\n"
        s += self.get_resources_as_string()
        s += "\n"
        s += f"Settlements ({self.numSettlements}/{MAX_SETTLEMENTS}): {self.settlements}\n"
        s += f"Roads ({self.numRoads}/{MAX_ROADS}): {self.roads}\n"
        s += f"Cities ({self.numCities}/{MAX_CITIES}): {self.cities}\n"
        
        # Add Development Cards information
        s += "Development Cards:\n"
        for card in self.dev_cards:
            s += f"  - {card}\n"
        
        # Add Largest Army and Longest Road information
        if self.has_largest_army:
            s += "Has Largest Army\n"
        if self.hasLongestRoad:
            s += "Has Longest Road\n"
        
        s += "--------------------------------------------\n"
        return s

    def get_resources_as_string(self):
        s = f"Resources: "
        for resource in self.resources:
            s += f"{resource.name.capitalize()} ({self.resources[resource]}) "
        return s

    def canBuildRoad(self):
        return (
            self.resources[ResourceTypes.BRICK] >= 1
            and self.resources[ResourceTypes.LUMBER] >= 1
            and self.numRoads < MAX_ROADS
        )

    def canSettle(self):
        return (
            self.resources[ResourceTypes.BRICK] >= 1
            and self.resources[ResourceTypes.LUMBER] >= 1
            and self.resources[ResourceTypes.WOOL] >= 1
            and self.resources[ResourceTypes.GRAIN] >= 1
            and self.numSettlements < MAX_SETTLEMENTS
        )

    def canBuildCity(self):
        return self.resources[ResourceTypes.ORE] >= 3 and \
               self.resources[ResourceTypes.GRAIN] >= 2 and \
               self.numCities < MAX_CITIES and \
               self.numSettlements > 0

    def deepCopy(self, board):
        newCopy = PlayerAgent(self.name, self.agentIndex, self.color, depth=self.depth, evalFn=self.evaluationFunction)
        newCopy.victoryPoints = self.victoryPoints
        newCopy.depth = self.depth
        newCopy.roads = [board.getEdge(road.X, road.Y) for road in self.roads]
        newCopy.settlements = [board.getVertex(settlement.X, settlement.Y) for settlement in self.settlements]
        newCopy.resources = copy.deepcopy(self.resources)
        newCopy.cities = [board.getVertex(city.X, city.Y) for city in self.cities]
        newCopy.hasLongestRoad = self.hasLongestRoad
        newCopy.longestRoadLength = self.longestRoadLength
        newCopy.dev_cards = [copy.deepcopy(card) for card in self.dev_cards]
        return newCopy

    def applyAction(self, action, board, gameState):
        if action is None:
            return
        
        elif action[0] is ACTIONS.SETTLE:
            if not self.canSettle():
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to build a settlement!")
            
            actionVertex = action[1]
            vertex = board.getVertex(actionVertex.X, actionVertex.Y)
            self.settlements.append(vertex)
            self.resources.subtract(SETTLEMENT_COST)
            gameState.bank.update(SETTLEMENT_COST)  # Add resources back to the bank
            self.victoryPoints += SETTLEMENT_VICTORY_POINTS
            self.numSettlements += 1

        elif action[0] is ACTIONS.ROAD:
            if not self.canBuildRoad():
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to build a road!")
            
            actionEdge = action[1]
            road = board.getEdge(actionEdge.X, actionEdge.Y)
            self.roads.append(road)
            self.resources.subtract(ROAD_COST)
            gameState.bank.update(ROAD_COST)  # Add resources back to the bank
            self.numRoads += 1
          
        elif action[0] is ACTIONS.CITY:
            if not self.canBuildCity():
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to build a city!")
            
            actionVertex = action[1]
            vertex = board.getVertex(actionVertex.X, actionVertex.Y)
            self.cities.append(vertex)
            for settlement in self.settlements:
                if settlement.X == vertex.X and settlement.Y == vertex.Y:
                    self.settlements.remove(settlement)
                    break

            self.resources.subtract(CITY_COST)
            gameState.bank.update(CITY_COST)  # Add resources back to the bank
            self.victoryPoints += 1
            self.numCities += 1
            self.numSettlements -= 1

        elif action[0] is ACTIONS.TRADE:
            give_resource, get_resource = action[1]
            if give_resource != ResourceTypes.NOTHING and get_resource != ResourceTypes.NOTHING:
                if self.resources[give_resource] >= 4 and gameState.bank[get_resource] > 0:
                    self.resources[give_resource] -= 4
                    self.resources[get_resource] += 1
                    gameState.bank[give_resource] += 4
                    gameState.bank[get_resource] -= 1
                else:
                    raise Exception(f"Player {self.agentIndex} doesn't have enough resources to make this trade or bank is out of the requested resource!")
            else:
                raise Exception(f"Cannot trade with NOTHING resource type!")

        elif action[0] is ACTIONS.BUY_DEV_CARD:
            if not self.canBuyDevCard(gameState):
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to buy a dev card!")
            self.resources.subtract(DEV_CARD_COST)
            gameState.bank.update(DEV_CARD_COST)
            card = gameState.drawDevCard()
            if card is not None:
                new_card = DevCard(card)
                self.dev_cards.append(new_card)
                if card == DevCardTypes.VICTORY_POINT:
                    self.victoryPoints += 1
                if VERBOSE: 
                    print(f"Player {self.agentIndex}  bought a development card: {card}")
            else:
                if VERBOSE:
                    print(f"No development cards left in the deck.")

        elif action[0] is ACTIONS.PLAY_DEV_CARD:
            card_type, card_action = action[1]
            card = next((card for card in self.dev_cards if card.type == card_type and card.can_be_used and not card.has_been_used), None)
            if card is None:
                raise Exception(f"Player {self.agentIndex} can't play this development card!")
            
            card.use()

            if card_type == DevCardTypes.KNIGHT:
                self.played_knights += 1
                gameState.move_robber_and_steal(self, card_action)
            elif card_type == DevCardTypes.ROAD_BUILDING:
                if self.numRoads >= MAX_ROADS:
                    return (card_type, [])  # Return empty list if already at max roads
                roads_built = []
                for road_coords in card_action:
                    if self.numRoads < MAX_ROADS:  # Change to < instead of <=
                        if self.buildRoad(road_coords, board, gameState):
                            roads_built.append(road_coords)
                            edge = board.getEdge(road_coords.X, road_coords.Y)
                            board.allRoads.append(edge)
                            self.numRoads += 1
                    else:
                        break
                return (card_type, roads_built)
            elif card_type == DevCardTypes.YEAR_OF_PLENTY:
                for resource in card_action:
                    if gameState.bank[resource] > 0:
                        self.resources[resource] += 1
                        gameState.bank[resource] -= 1
            elif card_type == DevCardTypes.MONOPOLY:
                resource = card_action
                total_stolen = 0
                for player in gameState.playerAgents:
                    if player != self:
                        if resource not in player.resources:
                            continue
                        amount = player.resources[resource]
                        player.resources[resource] = 0
                        self.resources[resource] += amount
                        total_stolen += amount
                if VERBOSE:
                    if total_stolen > 0:
                        if VERBOSE: 
                            print(f"{self.name} used Monopoly and collected {total_stolen} {resource.name}")
                    else:
                        if VERBOSE:
                            print(f"{self.name} used Monopoly on {resource.name}, but no resources were collected")
            elif card_type == DevCardTypes.VICTORY_POINT:
                self.victoryPoints += 1

            # Mark that a dev card has been played this turn
            self.dev_card_played_this_turn = True

            return action[1]  # Return the card_action for dev cards

    def updateResources(self, diceRoll, board):
        newResources = Counter(board.getResourcesFromDieRollForPlayer(self.agentIndex, diceRoll))
        for resource, amount in newResources.items():
            self.resources[resource] = max(0, self.resources[resource] + amount)
        return newResources

    def collectInitialResources(self, board):
        if VERBOSE and DEBUG:
            print(f"Collecting initial resources for player {self.agentIndex}")

        initial_resources = Counter()

        for settlement in self.settlements:
            surroundingHexes = board.getHexes(settlement)
            for hex in surroundingHexes:
                if hex.resource != ResourceTypes.NOTHING:
                    initial_resources[hex.resource] += 1

        if VERBOSE and DEBUG:
            print(f"Player {self.agentIndex} initial resources: {initial_resources}")

        return initial_resources

    def hasWon(self):
        return self.victoryPoints >= VICTORY_POINTS_TO_WIN

    def getAction(self, state):
        raise Exception("Cannot get action for superclass - must implement getAction in PlayerAgent subclass!")

    def updateLongestRoad(self, board, gameState):
        longestRoadLength = board.calculateLongestRoad(self.agentIndex)
        otherPlayer = gameState.playerAgents[1 - self.agentIndex]

        if longestRoadLength >= LONGEST_ROAD_LENGTH and longestRoadLength > otherPlayer.longestRoadLength:
            if not self.hasLongestRoad:
                self.hasLongestRoad = True
                self.victoryPoints += LONGEST_ROAD_POINTS
            if otherPlayer.hasLongestRoad:
                otherPlayer.hasLongestRoad = False
                otherPlayer.victoryPoints -= LONGEST_ROAD_POINTS
        elif self.hasLongestRoad and longestRoadLength < otherPlayer.longestRoadLength:
            self.hasLongestRoad = False
            self.victoryPoints -= LONGEST_ROAD_POINTS

        self.longestRoadLength = longestRoadLength

    def discard_half_on_seven(self, gameState):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return None

        discard_count = total_resources // 2
        discarded = Counter()

        resources_list = list(self.resources.elements())
        
        if not resources_list:  # If the player has no resources
            return None

        for _ in range(discard_count):
            if resources_list:  # Check if there are still resources to discard
                resource = random.choice(resources_list)
                discarded[resource] += 1
                resources_list.remove(resource)
            else:
                break

        for resource, amount in discarded.items():
            self.resources[resource] = max(0, self.resources[resource] - amount)
        gameState.bank += discarded  # Add discarded resources back to the bank
        return discarded

    def choose_robber_placement(self, board):
        valid_hexes = board.get_valid_robber_hexes()
        return random.choice(valid_hexes)

    def steal_resource(self, victim):
        if not victim.resources or sum(victim.resources.values()) == 0:
            return None
        resources_list = [r for r in victim.resources.elements()]
        if not resources_list:
            return None
        resource = random.choice(resources_list)
        victim.resources[resource] = max(0, victim.resources[resource] - 1)
        self.resources[resource] += 1
        return resource

    def canTrade(self, gameState):
        for give_resource, count in self.resources.items():
            if give_resource == ResourceTypes.NOTHING:
                continue
            if count >= 4:
                for get_resource in ResourceTypes:
                    if get_resource == ResourceTypes.NOTHING or get_resource == give_resource:
                        continue
                    if gameState.bank[get_resource] > 0:
                        return True
        return False

    def getPossibleTrades(self, gameState):
        trades = []
        for give_resource, count in self.resources.items():
            if give_resource != ResourceTypes.NOTHING and count >= 4:
                for get_resource in ResourceTypes:
                    if get_resource != ResourceTypes.NOTHING and get_resource != give_resource:
                        if gameState.bank[get_resource] > 0:
                            trades.append((give_resource, get_resource))
        return trades
    def canPass(self):
        return True  # Passing is always an option

    def canBuyDevCard(self, gameState):
        return (self.resources[ResourceTypes.GRAIN] >= 1 and
                self.resources[ResourceTypes.WOOL] >= 1 and
                self.resources[ResourceTypes.ORE] >= 1 and
                len(gameState.dev_card_deck) > 0)

    def canPlayKnight(self):
        return any(card.type == DevCardTypes.KNIGHT and card.can_be_used and not card.has_been_used for card in self.dev_cards)
    
    def canPlayDevCard(self, card_type):
        return any(card.type == card_type and card.can_be_used and not card.has_been_used for card in self.dev_cards)

    def updateLargestArmy(self, gameState):
        if self.played_knights >= LARGEST_ARMY_REQUIREMENT:
            if not self.has_largest_army:
                current_largest = max((player.played_knights for player in gameState.playerAgents if player != self), default=0)
                if self.played_knights > current_largest:
                    for player in gameState.playerAgents:
                        if player.has_largest_army:
                            player.has_largest_army = False
                            player.victoryPoints -= LARGEST_ARMY_POINTS
                    self.has_largest_army = True
                    self.victoryPoints += LARGEST_ARMY_POINTS

    def endTurn(self):
        for card in self.dev_cards:
            if not card.has_been_used:
                card.make_usable()
        self.dev_card_played_this_turn = False

    def get_legal_road_spots(self, board):
        legal_spots = []
        for road in self.roads:
            vertices = board.getVertexEnds(road)
            for vertex in vertices:
                edges = board.getEdgesOfVertex(vertex)
                for edge in edges:
                    if not edge.isOccupied() and board.canBuildRoadAt(self.agentIndex, edge.X, edge.Y):
                        legal_spots.append((edge.X, edge.Y))
        return legal_spots

    def buildRoad(self, road_coords, board, gameState):
        if self.numRoads < MAX_ROADS:  # Change to < instead of <=
            edge = board.getEdge(road_coords.X, road_coords.Y)
            if edge and not edge.isOccupied():
                if board.canBuildRoadAt(self.agentIndex, road_coords.X, road_coords.Y):
                    edge.build(self.agentIndex)
                    self.roads.append(edge)
                    board.allRoads.append(edge)
                    # Remove the increment from here, as it's now done in applyAction
                    return True
        return False
    
class PlayerAgentRandom(PlayerAgent):
    def getAction(self, gameState):
        possibleActions = gameState.getLegalActions(self.agentIndex)
        if possibleActions:
            chosenAction = random.choice(possibleActions)
            if chosenAction[0] == ACTIONS.PLAY_DEV_CARD:
                card_type = chosenAction[1]
                if card_type == DevCardTypes.ROAD_BUILDING:
                    legal_spots = self.get_legal_road_spots(gameState.board)
                    roads = random.sample(legal_spots, min(2, len(legal_spots)))
                    return (0, (ACTIONS.PLAY_DEV_CARD, (DevCardTypes.ROAD_BUILDING, roads)))
                elif card_type == DevCardTypes.YEAR_OF_PLENTY:
                    resources = self.choose_random_resources(2)
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, resources)))
                elif card_type == DevCardTypes.MONOPOLY:
                    resource = random.choice(list(ResourceTypes))
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, resource)))
                else:
                    return (0, chosenAction)
            else:
                return (0, chosenAction)
        return (0, (ACTIONS.PASS, None))

    def canTakeAction(self, action):
        if action[0] == ACTIONS.ROAD:
            return self.canBuildRoad()
        elif action[0] == ACTIONS.SETTLE:
            return self.canSettle()
        elif action[0] == ACTIONS.CITY:
            return self.canBuildCity()
        elif action[0] == ACTIONS.TRADE:
            return self.canTrade()
        elif action[0] == ACTIONS.PASS:
            return self.canPass()
        return False

    def choose_robber_placement(self, board):
        valid_hexes = board.get_valid_robber_hexes()
        return random.choice(valid_hexes)
    
    def discard_half_on_seven(self, gameState):
        return super().discard_half_on_seven(gameState)

    def choose_random_roads(self, board, count):
        possible_roads = []
        if self.canBuildRoad():
            for road in self.roads:
                vertices = board.getVertexEnds(road)
                for vertex in vertices:
                    edges = board.getEdgesOfVertex(vertex)
                    for edge in edges:
                        if not edge.isOccupied():
                            possible_roads.append((edge.X, edge.Y))
        if len(possible_roads) < count:
            return possible_roads  # Return all possible roads if there are fewer than requested
        return random.sample(possible_roads, count)

    def choose_random_resources(self, count):
        return random.choices(list(ResourceTypes), k=count)

class PlayerAgentHuman(PlayerAgent):
    def set_draw(self, draw):
        self.draw = draw

    def getAction(self, gameState):
        possibleActions = gameState.getLegalActions(self.agentIndex)
        #print(possibleActions)
        #print(self.settlements)
        #print(self.roads)
        #print(self.canBuildRoad())
        if possibleActions:

            print(self.get_resources_as_string())
            print(f"Player {self.agentIndex} - Choose an action:")
            
            action_map = {}
            for i, action in enumerate(possibleActions):
                if action[0] not in action_map:
                    action_map[action[0]] = []
                action_map[action[0]].append(action[1])

            if self.dev_card_played_this_turn and ACTIONS.PLAY_DEV_CARD in action_map:
                del action_map[ACTIONS.PLAY_DEV_CARD]

            index_map = {}
            for i, action in enumerate(action_map):
                index_map[i] = action
                print(f"{i+1}: {action.name.capitalize()}")

            actionIndex = input("Enter the number of the action you want to take: ")
            while not actionIndex.isdigit() or int(actionIndex) < 1 or int(actionIndex) > len(action_map):
                print("Invalid action index. Please try again.")
                actionIndex = input("Enter the number of the action you want to take: ")
            actionIndex = int(actionIndex) - 1

            chosenAction = index_map[actionIndex]
            if DEBUG and VERBOSE:
                print(f"Chose action: {chosenAction}")

            if chosenAction == ACTIONS.ROAD:
                road_spot = choose_edge(action_map[chosenAction], gameState.board, self.draw)
                return (0, (chosenAction, road_spot))
            
            elif chosenAction == ACTIONS.SETTLE or chosenAction == ACTIONS.CITY:
                spot = choose_vertex(action_map[chosenAction], self.draw, chosenAction)
                return (0, (chosenAction, spot))
            
            elif chosenAction == ACTIONS.TRADE:
                chosen_trade = -1
                print("Possible trades: ")
                for i, trade_items in enumerate(action_map[chosenAction]):
                    print(f"{i+1}: Trade {trade_items[0].name.capitalize()} for {trade_items[1].name.capitalize()}")
                
                chosen_trade = input("Enter the number of the trade you want to make: ")
                while not chosen_trade.isdigit() or int(chosen_trade) < 1 or int(chosen_trade) > len(action_map[chosenAction]):
                    print("Invalid trade index. Please try again.")
                    chosen_trade = input("Enter the number of the trade you want to make: ")
                chosen_trade = int(chosen_trade) - 1
                
                return (0, (chosenAction, action_map[chosenAction][chosen_trade]))
            
            elif chosenAction == ACTIONS.PLAY_DEV_CARD:
                possible_cards = []
                j = 1
                print("Possible cards: ")
                for i, item in enumerate(action_map[chosenAction]):
                    card_type = item if isinstance(item, DevCardTypes) else item[0]
                    if card_type not in possible_cards:
                        possible_cards.append(card_type)
                        print(f"{j}: {card_type.name.capitalize()}")
                        j += 1
                
                card_index = input("Enter the number of the card you want to play: ")
                while not card_index.isdigit() or int(card_index) < 1 or int(card_index) > len(possible_cards):
                    print("Choose a valid card.")
                    card_index = input("Enter the number of the card you want to play: ")
                card_index = int(card_index) - 1

                card_type = possible_cards[card_index]
                print(card_type)

                if card_type == DevCardTypes.VICTORY_POINT:
                    pass # automatically used
                elif card_type == DevCardTypes.KNIGHT:
                    return (0, (chosenAction, (card_type, self.choose_robber_placement(gameState.board))))

                elif card_type == DevCardTypes.ROAD_BUILDING:
                    legal_edges = [Edge(spot[0], spot[1]) for spot in self.get_legal_road_spots(gameState.board)]

                    print("Choose two roads to build:")
                    edge1 = choose_edge(legal_edges, gameState.board, self.draw)
                    self.buildRoad(edge1, gameState.board, gameState)
                    legal_edges = [Edge(spot[0], spot[1]) for spot in self.get_legal_road_spots(gameState.board)]
                    edge2 = choose_edge(legal_edges, gameState.board, self.draw)

                    return (0, (ACTIONS.PLAY_DEV_CARD, (DevCardTypes.ROAD_BUILDING, [edge1, edge2])))
                elif card_type == DevCardTypes.YEAR_OF_PLENTY:
                    print("Choose two resources to collect:")

                    # Print out the numbers associated with each resource type
                    for resource, amount in gameState.bank.items():
                        if amount > 0:
                            print(f"{resource.value}: {resource.name.capitalize()}")

                    resources = []
                    while (len(resources) < 2):
                        resource_num = int(input(f"Enter the number of the resource you would like from the bank: "))
                        resource = ResourceTypes(resource_num)
                        if gameState.bank[resource] > 1 or (gameState.bank[resource] > 0 and resource not in resources):
                            resources.append(resource)
                    
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, resources)))
                elif card_type == DevCardTypes.MONOPOLY:
                    for resource, amount in gameState.bank.items():
                        if amount > 0:
                            print(f"{resource.value}: {resource.name.capitalize()}")
                    resource = -1
                    while resource not in [1,2,3,4,5]:
                        resource = int(input("Choose a resource to steal: "))
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, ResourceTypes(resource))))
            else:
                # buy dev card, play knight, pass
                return (0, (chosenAction, None))
                
        return (0, (ACTIONS.PASS, None))

    def canTakeAction(self, action):
        if action[0] == ACTIONS.ROAD:
            return self.canBuildRoad()
        elif action[0] == ACTIONS.SETTLE:
            return self.canSettle()
        elif action[0] == ACTIONS.CITY:
            return self.canBuildCity()
        elif action[0] == ACTIONS.TRADE:
            return self.canTrade()
        elif action[0] == ACTIONS.PASS:
            return self.canPass()
        return False

    def choose_robber_placement(self, board):
        print("Choose robber location on the GUI.")
        valid_hexes = board.get_valid_robber_hexes()
        return choose_hex(valid_hexes, self.draw)
    
    def discard_half_on_seven(self, gameState):
        total_count = sum(self.resources.values())
        if total_count <= 7:
            return None

        print("Choose half of your resources to discard:")
        for resource, count in self.resources.items():
            print(f"{resource.name.capitalize()}: {count}")

        # Print the number associated with each resource
        resource_index = 1
        resource_indices = {}
        for resource, count in self.resources.items():
            if count > 0:
                print(f"{resource_index}: {resource.name.capitalize()}")
                resource_indices[resource_index] = resource
                resource_index += 1

        discard_count = total_count // 2
        discarded = Counter()
        for i in range(discard_count):
            resource = int(input("Enter the number of the resource you want to discard: "))
            resource_type = resource_indices.get(resource)
            if resource_type and self.resources[resource_type] > 0:
                discarded[resource_type] += 1
                self.resources[resource_type] -= 1
            else:
                print("Invalid resource index. Please try again.")
                i -= 1

        gameState.bank += discarded
        return discarded
    
    def choose_road_spot(self, legal_edges, gameState):
        print("Choose one road to build by clicking the GUI.")
        selected_spot = None
        threshold = 10  # Distance threshold for detecting clicks on roads

        while selected_spot is None:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    x, y = event.pos
                    if VERBOSE and DEBUG:
                        print(f"Clicked GUI at {x}, {y}")
                    for edge in legal_edges:
                        start, end = gameState.board.getVertexEnds(edge)
                        ox, oy = self.draw.calculateVertexPosition(start)
                        ex, ey = self.draw.calculateVertexPosition(end)
                        if DEBUG and VERBOSE:
                            print("Args: ")
                            print(x, y, ox, oy, ex, ey)
                        dist = point_to_line_distance(x, y, ox, oy, ex, ey)
                        if dist < threshold:
                            selected_edge = edge
                            if VERBOSE and DEBUG:
                                print(f"Selected edge: {edge}")
                            return selected_edge


    def choose_spot(self, legal_vertices, action):
        if action.name == "CITY":
            print("Choose one city to build by clicking the GUI.")
        elif action.name == "SETTLE":
            print("Choose one settlement to build by clicking the GUI.")
        else:
            print("Error")
    
        selected_vertex = None
        threshold = 10  # Distance threshold for detecting clicks on roads

        while selected_vertex is None:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    x, y = event.pos
                    for vertex in legal_vertices:
                        xPos, yPos = self.draw.calculateVertexPosition(vertex)
                        dist = point_to_point_distance(x, y, xPos, yPos)
                        if dist < threshold:
                            selected_vertex = vertex
                            if VERBOSE and DEBUG:
                                print(f"Selected vertex: {vertex}")
                            return selected_vertex
    
    def choose_robber_loc(self, legal_hexes):
        selected_hex = None
        threshold = 10  # Distance threshold for detecting clicks on roads

        while selected_hex is None:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    x, y = event.pos
                    for hex in legal_hexes:
                        xPos, yPos = self.draw.hex_centers[hex]

                        dist = point_to_point_distance(x, y, xPos, yPos)
                        if dist < threshold:
                            selected_hex = hex
                            if VERBOSE and DEBUG:
                                print(f"Selected hex: {hex}")
                            return hex

def point_to_line_distance(px, py, x1, y1, x2, y2):
    # Calculate the distance from point (px, py) to the line segment (x1, y1) - (x2, y2)
    line_mag = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if line_mag < 1e-6:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
    u = max(min(u, 1), 0)
    ix = x1 + u * (x2 - x1)
    iy = y1 + u * (y2 - y1)
    return math.sqrt((px - ix) ** 2 + (py - iy) ** 2)

def point_to_point_distance(x1, y1, x2, y2):
    # Calculate the distance from point (x1, y1) to point (x2, y2)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


class PlayerAgentExpectimax(PlayerAgent):
    def __init__(self, name, agentIndex, color, depth=DEPTH, evalFn=defaultEvalFn):
        super(PlayerAgentExpectimax, self).__init__(name, agentIndex, color, depth, evalFn=evalFn)
        self.TIME_LIMIT = 5  # 5 seconds

    def getAction(self, state):
        start_time = time.time()

        def recurse(currState, currDepth, playerIndex):
            if time.time() - start_time > self.TIME_LIMIT:
                return None, None  # Timeout

            if currState.gameOver() == playerIndex:
                return float('inf'), None
            elif currState.gameOver() > -1:
                return float('-inf'), None
            elif currDepth >= self.depth:
                return self.evaluationFunction(currState, self.agentIndex), None

            possibleActions = self.filterActions(currState.getLegalActions(playerIndex))

            if len(possibleActions) == 0:
                return self.evaluationFunction(currState, self.agentIndex), None

            rollProbabilities = currState.diceAgent.getRollDistribution()
            newDepth = currDepth + 1
            newPlayerIndex = (playerIndex + 1) % currState.getNumPlayerAgents()

            if playerIndex == self.agentIndex:
                bestValue = float('-inf')
                bestAction = None
                for currAction in possibleActions:
                    if currAction[0] == ACTIONS.PASS:
                        currVal = self.evaluationFunction(currState, self.agentIndex)
                    else:
                        currVal = 0
                        for roll, probability in rollProbabilities:
                            successor = currState.generateSuccessor(playerIndex, currAction)
                            successor.updatePlayerResourcesForDiceRoll(roll)
                            value, _ = recurse(successor, newDepth, playerIndex)
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    if currVal > bestValue:
                        bestValue = currVal
                        bestAction = currAction
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is the best action, no need to check further
                return bestValue, bestAction
            else:
                totalValue = 0
                count = 0
                for currAction in possibleActions:
                    if currAction[0] == ACTIONS.PASS:
                        currVal = self.evaluationFunction(currState, self.agentIndex)
                    else:
                        currVal = 0
                        for roll, probability in rollProbabilities:
                            successor = currState.generateSuccessor(playerIndex, currAction)
                            successor.updatePlayerResourcesForDiceRoll(roll)
                            value, _ = recurse(successor, newDepth, playerIndex)
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    totalValue += currVal
                    count += 1
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is an option, no need to check further
                return totalValue / count if count > 0 else 0, None

        value, action = recurse(state, 0, self.agentIndex)
        if value is None or action is None:
            # If we've timed out, just return PASS
            return 0, (ACTIONS.PASS, None)
        return value, action

    def filterActions(self, actions):
        filtered_actions = actions + [(ACTIONS.PASS, None)]
        return filtered_actions
    
    def discard_half_on_seven(self, gameState):
        return super().discard_half_on_seven(gameState)
    
    def choose_initial_settlement(self, board):
        best_value = float('-inf')
        best_vertex = None
        for vertex in board.getAllVertices():
            if vertex.canSettle:
                value = self.evaluate_settlement_spot(vertex, board)
                if value > best_value:
                    best_value = value
                    best_vertex = vertex
        return best_vertex

    def choose_initial_road(self, vertex, board):
        best_value = float('-inf')
        best_edge = None
        for edge in board.getEdgesOfVertex(vertex):
            if not edge.isOccupied():
                value = self.evaluate_road_spot(edge, board)
                if value > best_value:
                    best_value = value
                    best_edge = edge
        return best_edge

    def evaluate_settlement_spot(self, vertex, board):
        hexes = board.getHexes(vertex)
        value = 0
        for hex in hexes:
            if hex.resource != ResourceTypes.NOTHING:
                value += 6 - abs(7 - hex.diceValue)  # Higher value for more probable numbers
        return value

    def evaluate_road_spot(self, edge, board):
        vertices = board.getVertexEnds(edge)
        value = 0
        for vertex in vertices:
            if vertex.canSettle:
                value += self.evaluate_settlement_spot(vertex, board)
        return value
    


class PlayerAgentExpectiminimax(PlayerAgent):
    def __init__(self, name, agentIndex, color, depth=DEPTH, evalFn=defaultEvalFn):
        super(PlayerAgentExpectiminimax, self).__init__(name, agentIndex, color, depth=depth, evalFn=evalFn)
        self.TIME_LIMIT = 5  # 5 seconds

    def getAction(self, state):
        start_time = time.time()

        def recurse(currState, currDepth, playerIndex):
            if time.time() - start_time > self.TIME_LIMIT:
                return None, None  # Timeout

            if currState.gameOver() == playerIndex:
                return float('inf'), None
            elif currState.gameOver() > -1:
                return float('-inf'), None
            elif currDepth >= self.depth:
                return self.evaluationFunction(currState, self.agentIndex), None

            possibleActions = self.filterActions(currState.getLegalActions(playerIndex))

            if len(possibleActions) == 0:
                return self.evaluationFunction(currState, self.agentIndex), None

            rollProbabilities = currState.diceAgent.getRollDistribution()
            newDepth = currDepth + 1
            newPlayerIndex = (playerIndex + 1) % currState.getNumPlayerAgents()

            if playerIndex == self.agentIndex:
                bestValue = float('-inf')
                bestAction = None
                for currAction in possibleActions:
                    if currAction[0] == ACTIONS.PASS:
                        currVal = self.evaluationFunction(currState, self.agentIndex)
                    else:
                        currVal = 0
                        for roll, probability in rollProbabilities:
                            successor = currState.generateSuccessor(playerIndex, currAction)
                            successor.updatePlayerResourcesForDiceRoll(roll)
                            value, _ = recurse(successor, newDepth, playerIndex)  # Continue with same player
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    if currVal > bestValue:
                        bestValue = currVal
                        bestAction = currAction
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is the best action, no need to check further
                return bestValue, bestAction
            else:
                worstValue = float('inf')
                worstAction = None
                for currAction in possibleActions:
                    if currAction[0] == ACTIONS.PASS:
                        currVal = self.evaluationFunction(currState, self.agentIndex)
                    else:
                        currVal = 0
                        for roll, probability in rollProbabilities:
                            successor = currState.generateSuccessor(playerIndex, currAction)
                            successor.updatePlayerResourcesForDiceRoll(roll)
                            value, _ = recurse(successor, newDepth, playerIndex)  # Continue with same player
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    if currVal < worstValue:
                        worstValue = currVal
                        worstAction = currAction
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is the worst action, no need to check further
                return worstValue, worstAction

        value, action = recurse(state, 0, self.agentIndex)
        if value is None or action is None:
            # If we've timed out, just return PASS
            return 0, (ACTIONS.PASS, None)
        return value, action

    def filterActions(self, actions):
        filtered_actions = actions + [(ACTIONS.PASS, None)]
        return filtered_actions
    
    def discard_half_on_seven(self, gameState):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return None

        discard_count = total_resources // 2
        discarded = self.choose_cards_to_discard(discard_count)
        self.resources -= discarded
        gameState.bank += discarded  # Add discarded resources back to the bank
        return discarded

    def choose_cards_to_discard(self, discard_count):
        discarded = Counter()
        resources_list = sorted(self.resources.items(), key=lambda x: x[1], reverse=True)
        
        for resource, count in resources_list:
            while count > 0 and sum(discarded.values()) < discard_count:
                discarded[resource] += 1
                count -= 1
            
            if sum(discarded.values()) == discard_count:
                break
        

        return discarded
    
    def choose_initial_settlement(self, board):
        best_value = float('-inf')
        best_vertex = None
        for vertex in board.getAllVertices():
            if vertex.canSettle:
                value = self.evaluate_settlement_spot(vertex, board)
                if value > best_value:
                    best_value = value
                    best_vertex = vertex
        return best_vertex

    def choose_initial_road(self, vertex, board):
        best_value = float('-inf')
        best_edge = None
        for edge in board.getEdgesOfVertex(vertex):
            if not edge.isOccupied():
                value = self.evaluate_road_spot(edge, board)
                if value > best_value:
                    best_value = value
                    best_edge = edge
        return best_edge

    def evaluate_settlement_spot(self, vertex, board):
        hexes = board.getHexes(vertex)
        value = 0
        for hex in hexes:
            if hex.resource != ResourceTypes.NOTHING:
                value += 6 - abs(7 - hex.diceValue)  # Higher value for more probable numbers
        return value

    def evaluate_road_spot(self, edge, board):
        vertices = board.getVertexEnds(edge)
        value = 0
        for vertex in vertices:
            if vertex.canSettle:
                value += self.evaluate_settlement_spot(vertex, board)
        return value
    

"""

IMPLEMENTING THE VALUE FUNCTION PLAYER inspired by the code here: 
https://github.com/bcollazo/catanatron/blob/f2b016d29ccacea8965dbb8356c54cf84313b3f2/catanatron_experimental/catanatron_experimental/machine_learning/players/value.py#L57 

"""

TRANSLATE_VARIETY = 4
DEFAULT_WEIGHTS = {
    # Where to place. Note winning is best at all costs
    "public_vps": 3e9,
    "production": 1e8,
    "enemy_production": -1e8,
    "num_tiles": 17,
    # Towards where to expand and when
    "reachable_production_0": 0,
    "reachable_production_1": 1e4,
    "buildable_nodes": 1e3,
    "longest_road": 10,
    # Hand, when to hold and when to use.
    "hand_synergy": 1e2,
    "hand_resources": 63,
    "discard_penalty": -5,
    "hand_devs": 10,
    "army_size": 10.1,
}

# Change these to play around with new values
CONTENDER_WEIGHTS = {
    "public_vps": 300000000000001.94,
    "production": 100000002.04188395,
    "enemy_production": -99999998.03389844,
    "num_tiles": 2.91440418,
    "reachable_production_0": 2.03820085,
    "reachable_production_1": 10002.018773150001,
    "buildable_nodes": 1001.86278466,
    "longest_road": 12.127388499999999,
    "hand_synergy": 102.40606877,
    "hand_resources": 2.43644327,
    "discard_penalty": -3.00141993,
    "hand_devs": 10.721669799999999,
    "army_size": 12.93844622,
}

REACHABILITY_DEPTH = 2

DEVELOPMENT_CARDS = list(DevCardTypes)

def value_production(sample, player_name="P0", include_variety=True):
    proba_point = 2.778 / 100
    features = [
        f"EFFECTIVE_{player_name}_GRAIN_PRODUCTION",
        f"EFFECTIVE_{player_name}_ORE_PRODUCTION",
        f"EFFECTIVE_{player_name}_WOOL_PRODUCTION",
        f"EFFECTIVE_{player_name}_LUMBER_PRODUCTION",
        f"EFFECTIVE_{player_name}_BRICK_PRODUCTION",
    ]
    prod_sum = sum([sample[f] for f in features])
   
    prod_variety = (
        sum([sample[f] != 0 for f in features]) * TRANSLATE_VARIETY * proba_point
    )
    return prod_sum + (0 if not include_variety else prod_variety)


def player_key(playerIndex): 
    return f"P{playerIndex}"

def resource_hand_features(gameState, playerIndex):
    features = {}
    for currentPlayerIndex in range(2):
        key = player_key(currentPlayerIndex)
        hand = gameState.playerAgents[currentPlayerIndex].resources
        if currentPlayerIndex == playerIndex:
            for resource in RESOURCES:
                features[f"{key}_{resource}_IN_HAND"] = hand[resource]
            cardDict = Counter(gameState.playerAgents[currentPlayerIndex].dev_cards)
            for card in DEVELOPMENT_CARDS: 
                features[f"{key}_{card}_IN_HAND"] = cardDict[card]
            features[f"{key}_HAS_PLAYED_DEVELOPMENT_CARD_IN_TURN"] = gameState.playerAgents[currentPlayerIndex].dev_card_played_this_turn

        for cardtype in DEVELOPMENT_CARDS:
            if cardtype == DevCardTypes.VICTORY_POINT:
                continue
            playedCardsOfType = len([card for card in gameState.playerAgents[currentPlayerIndex].dev_cards if card.type == cardtype and card.has_been_used])
            features[f"{key}_{cardtype}_PLAYED"] = playedCardsOfType
        
        features[f"{key}_NUM_RESOURCES_IN_HAND"] = sum(gameState.playerAgents[currentPlayerIndex].resources.values())
        features[f"{key}_NUM_DEVELOPMENT_CARDS_IN_HAND"] = len(gameState.playerAgents[currentPlayerIndex].dev_cards)
    return features


def base_fn(params=DEFAULT_WEIGHTS):
    
    def fn(currentGameState, currentPlayerIndex):
        enemyIndex = 1 - currentPlayerIndex
        our_production_sample = currentGameState.board.getProductionSample(currentPlayerIndex)
        enemy_production_sample = currentGameState.board.getProductionSample(enemyIndex)
        

        
        production = value_production(our_production_sample, player_key(currentPlayerIndex), False)
        enemy_production = value_production(enemy_production_sample, player_key(enemyIndex), False)

        key = player_key(currentPlayerIndex)
        longest_road_length = currentGameState.board.calculateLongestRoad(currentPlayerIndex)

        reachability_sample = currentGameState.board.reachability_features(REACHABILITY_DEPTH)
        features = [f"{key}_0_ROAD_REACHABLE_{resource}" for resource in RESOURCES]
        reachable_production_at_zero = sum([reachability_sample[f] for f in features])
        features = [f"{key}_1_ROAD_REACHABLE_{resource}" for resource in RESOURCES]
        reachable_production_at_one = sum([reachability_sample[f] for f in features])

        hand_sample = resource_hand_features(currentGameState, currentPlayerIndex)
      
        features = [f"{key}_{resource}_IN_HAND" for resource in RESOURCES]
        distance_to_city = (
            max(2 - hand_sample[f"{key}_GRAIN_IN_HAND"], 0)
            + max(3 - hand_sample[f"{key}_ORE_IN_HAND"], 0)
        ) / 5.0  # 0 means good. 1 means bad.
        distance_to_settlement = (
            max(1 - hand_sample[f"{key}_GRAIN_IN_HAND"], 0)
            + max(1 - hand_sample[f"{key}_WOOL_IN_HAND"], 0)
            + max(1 - hand_sample[f"{key}_BRICK_IN_HAND"], 0)
            + max(1 - hand_sample[f"{key}_LUMBER_IN_HAND"], 0)
        ) / 4.0  # 0 means good. 1 means bad.
        hand_synergy = (2 - distance_to_city - distance_to_settlement) / 2

        num_in_hand = hand_sample[f"{key}_NUM_RESOURCES_IN_HAND"]
        discard_penalty = params["discard_penalty"] if num_in_hand > 7 else 0

        # blockability
        num_tiles = currentGameState.board.getNumTiles(currentPlayerIndex) 
     
        num_buildable_nodes = currentGameState.board.getNumBuildableTiles(currentPlayerIndex) 
        longest_road_factor = (
            params["longest_road"] if num_buildable_nodes == 0 else 0.1
        )

        player_num_dev_cards = len(currentGameState.playerAgents[currentPlayerIndex].dev_cards)
        played_knights = len([card for card in currentGameState.playerAgents[currentPlayerIndex].dev_cards if card.type == DevCardTypes.KNIGHT and card.has_been_used])

        return float(
            currentGameState.playerAgents[currentPlayerIndex].victoryPoints * params["public_vps"]
            + production * params["production"]
            + enemy_production * params["enemy_production"]
            + reachable_production_at_zero * params["reachable_production_0"]
            + reachable_production_at_one * params["reachable_production_1"]
            + hand_synergy * params["hand_synergy"]
            + num_buildable_nodes * params["buildable_nodes"]
            + num_tiles * params["num_tiles"]
            + num_in_hand * params["hand_resources"]
            + discard_penalty
            + longest_road_length * longest_road_factor
            + player_num_dev_cards * params["hand_devs"]
            + played_knights * params["army_size"]
        )

    return fn

def contender_fn(params):
    return base_fn(params or CONTENDER_WEIGHTS)

def get_value_fn(name, params, value_function=None):
    if value_function is not None:
        return value_function
    elif name == "base_fn":
        return base_fn(DEFAULT_WEIGHTS)
    elif name == "contender_fn":
        return contender_fn(params)
    else:
        raise ValueError

class ValueFunctionPlayer(PlayerAgent):
    def __init__(self, name, agentIndex, color, params= None, epsilon=None, value_fn_builder_name=None):
        super(ValueFunctionPlayer, self).__init__(name, agentIndex, color)
        self.params = params
        self.epsilon = epsilon
        self.value_fn_builder_name = (
            "base_fn"
        )

    def getAction(self, state):
        # In our code rn, self.epsilon is always None
        if self.epsilon is not None and random.random() < self.epsilon:
            return random.choice(state.getLegalActions(self.agentIndex))

        best_value = float("-inf")
        best_action = None
        for action in state.getLegalActions(self.agentIndex):
            if action[0] == ACTIONS.PASS:  # remove pass action from possible actions
                continue 
            
            successor = state.generateSuccessor(self.agentIndex, action)
            value_fn = get_value_fn(self.value_fn_builder_name, self.params)
            value = value_fn(successor, self.agentIndex)
           
            if value > best_value:
                best_value = value
                best_action = action
        return 0 if not best_action else best_value, best_action if best_action else (ACTIONS.PASS, None)

    def filterActions(self, actions):
        filtered_actions = actions + [(ACTIONS.PASS, None)]
        return filtered_actions
    
    def discard_half_on_seven(self, gameState):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return None

        discard_count = total_resources // 2
        discarded = self.choose_cards_to_discard(discard_count)
        self.resources -= discarded
        gameState.bank += discarded  # Add discarded resources back to the bank
        return discarded

    def choose_cards_to_discard(self, discard_count):
        discarded = Counter()
        resources_list = sorted(self.resources.items(), key=lambda x: x[1], reverse=True)
        
        for resource, count in resources_list:
            while count > 0 and sum(discarded.values()) < discard_count:
                discarded[resource] += 1
                count -= 1
            
            if sum(discarded.values()) == discard_count:
                break
        return discarded
    
    def choose_initial_settlement(self, board):
        best_value = float('-inf')
        best_vertex = None
        for vertex in board.getAllVertices():
            if vertex.canSettle:
                value = self.evaluate_settlement_spot(vertex, board)
                if value > best_value:
                    best_value = value
                    best_vertex = vertex
        return best_vertex

    def choose_initial_road(self, vertex, board):
        best_value = float('-inf')
        best_edge = None
        for edge in board.getEdgesOfVertex(vertex):
            if not edge.isOccupied():
                value = self.evaluate_road_spot(edge, board)
                if value > best_value:
                    best_value = value
                    best_edge = edge
        return best_edge

    def evaluate_settlement_spot(self, vertex, board):
        hexes = board.getHexes(vertex)
        value = 0
        for hex in hexes:
            if hex.resource != ResourceTypes.NOTHING:
                value += 6 - abs(7 - hex.diceValue)  # Higher value for more probable numbers
        return value

    def evaluate_road_spot(self, edge, board):
        vertices = board.getVertexEnds(edge)
        value = 0
        for vertex in vertices:
            if vertex.canSettle:
                value += self.evaluate_settlement_spot(vertex, board)
        return value

class QLearningAgent(PlayerAgent):
    def __init__(self, name, agentIndex, color, alpha=0.2, alpha_decay=0.9999, min_alpha=0.05, gamma=0.99, 
             epsilon_start=0.3, epsilon_end=0.05, epsilon_decay=0.9995, buffer_size=100000, batch_size=64):
        super().__init__(name, agentIndex, color)
        self.alpha = alpha
        self.alpha_decay = alpha_decay
        self.min_alpha = min_alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.q_table, self.iteration = self.load_q_table()
        self.default_q_value = 0.1
        self.last_state = None
        self.last_action = None
        self.experience_buffer = []
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.visit_counts = Counter()
        self.prune_threshold = 5
        self.prune_frequency = 100
    
    def get_state(self, gameState):
        return (
            self.victoryPoints,
            len(self.settlements),
            len(self.cities),
            len(self.roads),
            tuple(self.resources.values()),
            gameState.playerAgents[1 - self.agentIndex].victoryPoints if gameState else 0,
            gameState.board.robber.hex.X if gameState else 0,
            gameState.board.robber.hex.Y if gameState else 0
        )

    def getAction(self, gameState):
        state = self.get_state(gameState)
        legal_actions = gameState.getLegalActions(self.agentIndex)

        if not legal_actions:
            return 0, (ACTIONS.PASS, None)

        if random.random() < self.epsilon:
            action = random.choice(legal_actions)
        else:
            action = max(legal_actions, key=lambda a: self.get_q_value(state, self.make_action_hashable(a)) * 0.7 + 
                        self.evaluate_win_likelihood(self.get_state(gameState.generateSuccessor(self.agentIndex, a))) * 0.3)

        self.last_state = state
        self.last_action = action
        return 0, action

    def update(self, state, action, next_state, reward, gameState):
        td_error = abs(reward + self.gamma * self.get_max_q_value(next_state) - self.get_q_value(state, action))
        priority = (td_error + 0.01) ** 0.6

        # Consider the opponent's likely next action
        opponent_action = self.predict_opponent_action(gameState)
        if opponent_action:
            opponent_next_state = self.get_state(gameState.generateSuccessor(1 - self.agentIndex, opponent_action))
            opponent_impact = self.evaluate_win_likelihood(opponent_next_state)
            priority *= (1 + opponent_impact)  # Increase priority if the opponent's action is impactful

        experience = Experience(state, action, next_state, reward, gameState, priority)
        
        if len(self.experience_buffer) < self.buffer_size:
            self.experience_buffer.append(experience)
        else:
            index = np.random.randint(0, self.buffer_size)
            self.experience_buffer[index] = experience
        
        self.perform_experience_replay()
        self.visit_counts[state] += 1

        # Prune Q-table periodically
        if self.iteration % self.prune_frequency == 0:
            self.prune_q_table()

        self.alpha = max(self.alpha * self.alpha_decay, self.min_alpha)
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_end)
    
    def perform_experience_replay(self):
        if len(self.experience_buffer) < self.batch_size:
            return

        priorities = np.array([exp.priority for exp in self.experience_buffer])
        probabilities = priorities / np.sum(priorities)
        
        indices = np.random.choice(len(self.experience_buffer), size=self.batch_size, p=probabilities, replace=False)
        batch = [self.experience_buffer[i] for i in indices]
        
        for experience in batch:
            self.q_learning_update(experience.state, experience.action, experience.next_state, experience.reward, experience.gameState)
    
    def q_learning_update(self, state, action, next_state, reward, gameState):
        old_q = self.get_q_value(state, action)
        next_max = self.get_max_q_value(next_state)

        # Adjust reward based on game outcome and VP difference
        if gameState.gameOver() == self.agentIndex:
            reward = 10000  # Huge reward for winning
        elif gameState.gameOver() >= 0:
            reward = -10000  # Huge penalty for losing
        else:
            vp_gain = next_state[0] - state[0]
            opponent_vp = next_state[5]
            vp_difference = next_state[0] - opponent_vp
            reward = vp_gain * 100 + vp_difference * 50  # Increase emphasis on VP gain and difference

        new_q = (1 - self.alpha) * old_q + self.alpha * (reward + self.gamma * next_max)
        self.q_table[state][self.make_action_hashable(action)] = new_q
    
    def evaluate_win_likelihood(self, state):
        my_vp = state[0]
        opponent_vp = state[5]
        vp_difference = my_vp - opponent_vp
        
        if my_vp >= 10:
            return 1.0
        elif opponent_vp >= 10:
            return 0.0
        else:
            return (my_vp / 10.0) * 0.8 + (vp_difference / 10.0) * 0.2
    
    def get_max_q_value(self, state):
        if state not in self.q_table:
            return self.default_q_value
        return max(self.q_table[state].values(), default=self.default_q_value)

    def end_game_update(self, gameState):
        if self.last_state and self.last_action:
            final_state = self.get_state(gameState)
            game_outcome = 1 if gameState.gameOver() == self.agentIndex else -1
            reward = game_outcome * 100  # Large reward/penalty for winning/losing
            self.update(self.last_state, self.last_action, final_state, reward, gameState)
        self.iteration += 1
        self.save_q_table()

    def save_q_table(self):
        filename = f"q_table_player_{self.agentIndex}.pkl"
        data = {
            'q_table': self.q_table,
            'iteration': self.iteration
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        print(f"Updated Q-table for Player {self.agentIndex}, iteration {self.iteration}")

    def load_q_table(self):
        filename = f"q_table_player_{self.agentIndex}.pkl"
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                    return data['q_table'], data['iteration']
            except (EOFError, pickle.UnpicklingError, KeyError):
                print(f"Warning: Q-table file {filename} is corrupted or in old format. Starting with a new Q-table.")
                os.remove(filename)
        return {}, 0
    
    def choose_initial_settlement(self, board):
        best_value = float('-inf')
        best_vertex = None
        valid_vertices = [v for v in board.getAllVertices() if v.canSettle]

        for vertex in valid_vertices:
            value = self.evaluate_settlement_spot(vertex, board)
            value += random.uniform(0, 1)  # Add some randomness
            if value > best_value:
                best_value = value
                best_vertex = vertex
        return best_vertex

    def choose_initial_road(self, vertex, board):
        best_value = float('-inf')
        best_edge = None
        valid_edges = [e for e in board.getEdgesOfVertex(vertex) if not e.isOccupied()]

        for edge in valid_edges:
            value = self.evaluate_road_spot(edge, board)
            value += random.uniform(0, 1)  # Add some randomness
            if value > best_value:
                best_value = value
                best_edge = edge
        return best_edge

    def evaluate_settlement_spot(self, vertex, board):
        hexes = board.getHexes(vertex)
        value = 0
        resource_types = set()
        production_value = 0

        for hex in hexes:
            if hex.resource != ResourceTypes.NOTHING:
                # Calculate production value (6 and 8 are most valuable)
                probability_value = 6 - abs(7 - hex.diceValue)
                production_value += probability_value
                value += probability_value * 2

                resource_types.add(hex.resource)

                if hex.resource in [ResourceTypes.ORE, ResourceTypes.GRAIN]:
                    value += 1  # Slightly favor resources needed for cities

        # Reward resource variety
        variety_bonus = len(resource_types) * 3
        value += variety_bonus

        # Significant bonus for being on three productive hexes
        if len([h for h in hexes if h.resource != ResourceTypes.NOTHING]) == 3:
            value += 10

        # Penalty for being on the coast (less than 3 hexes)
        if len(hexes) < 3:
            value -= 5

        # Consider potential for expansion
        expandable_edges = sum(1 for edge in board.getEdgesOfVertex(vertex) if not edge.isOccupied())
        value += expandable_edges * 2

        # Store production value for potential city upgrades
        vertex.production_value = production_value

        return value

    def evaluate_road_spot(self, edge, board):
        value = 0
        vertices = board.getVertexEnds(edge)

        for vertex in vertices:
            if vertex.canSettle:
                settlement_value = self.evaluate_settlement_spot(vertex, board)
                value += settlement_value * 0.5

                # Extra value for roads leading to 3-hex spots
                if len(board.getHexes(vertex)) == 3:
                    value += 5

        unexplored_vertices = sum(1 for v in vertices if not v.isOccupied() and v.canSettle)
        value += unexplored_vertices * 3

        # Check for connected roads
        adjacent_edges = board.getEdgesOfVertex(vertices[0]) + board.getEdgesOfVertex(vertices[1])
        connected_roads = sum(1 for adj_edge in adjacent_edges if adj_edge.isOccupied() and adj_edge.player == self.agentIndex)
        value += connected_roads * 2

        return value

    def choose_robber_placement(self, board):
        valid_hexes = board.get_valid_robber_hexes()
        return max(valid_hexes, key=lambda h: self.evaluate_robber_placement(h, board))

    def evaluate_robber_placement(self, hex, board):
        value = 0
        for vertex in board.getVertices(hex):
            if vertex.player is not None and vertex.player != self.agentIndex:
                value += 10  # Bonus for blocking opponent
            if vertex.player == self.agentIndex:
                value -= 5  # Penalty for blocking self
        return value + (6 - abs(7 - hex.diceValue))  # Consider hex productivity

    def discard_half_on_seven(self, gameState):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return None

        discard_count = total_resources // 2
        discarded = Counter()
        resource_values = self.calculate_resource_values()

        for _ in range(discard_count):
            resource = min(self.resources.keys(), key=lambda r: resource_values.get(r, 0) if self.resources[r] > 0 else float('inf'))
            discarded[resource] += 1
            self.resources[resource] = max(0, self.resources[resource] - 1)

        gameState.bank += discarded
        return discarded
    
    def calculate_resource_values(self):
        values = {r: 0 for r in ResourceTypes if r != ResourceTypes.NOTHING}
        if self.canSettle():
            for r in SETTLEMENT_COST:
                values[r] += 2
        if self.canBuildCity():
            for r in CITY_COST:
                values[r] += 3
        if len(self.roads) < MAX_ROADS:
            for r in ROAD_COST:
                values[r] += 1
        return values

    def steal_resource(self, victim):
        if not victim.resources or sum(victim.resources.values()) == 0:
            return None
        
        # Use a simplified state representation that doesn't depend on gameState
        state = (
            self.victoryPoints,
            len(self.settlements),
            len(self.cities),
            len(self.roads),
            tuple(self.resources.values())
        )
        
        if state not in self.q_table or not victim.resources:
            resource = random.choice([r for r in victim.resources.keys() if victim.resources[r] > 0])
        else:
            resource = max(
                [r for r in victim.resources.keys() if victim.resources[r] > 0],
                key=lambda r: self.q_table[state].get((ACTIONS.STEAL, r), 0)
            )
        
        victim.resources[resource] = max(0, victim.resources[resource] - 1)
        self.resources[resource] += 1
        return resource
    
    def get_q_value(self, state, action):
        if state not in self.q_table:
            self.q_table[state] = {}
        hashable_action = self.make_action_hashable(action)
        if hashable_action not in self.q_table[state]:
            self.q_table[state][hashable_action] = self.default_q_value
        return self.q_table[state][hashable_action]

    def make_action_hashable(self, action):
        if isinstance(action, tuple):
            return tuple(self.make_action_hashable(item) for item in action)
        elif isinstance(action, list):
            return tuple(self.make_action_hashable(item) for item in action)
        elif isinstance(action, (Edge, Hexagon, Vertex)):
            return (action.X, action.Y)
        else:
            return action
    
    def prune_q_table(self):
        states_to_remove = [state for state, count in self.visit_counts.items() if count < self.prune_threshold]
        for state in states_to_remove:
            if state in self.q_table:
                del self.q_table[state]
            del self.visit_counts[state]
        print(f"Pruned {len(states_to_remove)} states from Q-table")
        self.save_q_table()  # Save the pruned Q-table

    def predict_opponent_action(self, gameState):
        opponent_index = 1 - self.agentIndex
        opponent_actions = gameState.getLegalActions(opponent_index)
        if not opponent_actions:
            return None
        
        # Assume the opponent will take the action that gives them the most victory points
        return max(opponent_actions, key=lambda a: gameState.generateSuccessor(opponent_index, a).playerAgents[opponent_index].victoryPoints)

class LookAheadRolloutPlayer(PlayerAgent):
    # The rollout policy should draw the action from action distribution pi(s)
    # To produce rollout simulartions, we need to use a generative model 
    # that generates s' from T(s' | s, a); this is actually deterministic in our case.

    def __init__(self, name, agentIndex, color, depth=1, rollout_policy=None, value_fn_builder_name=("base_fn")):
        super(LookAheadRolloutPlayer, self).__init__(name, agentIndex, color)
        self.depth = depth
        self.rollout_policy = rollout_policy
        self.value_fn_builder_name = value_fn_builder_name

        # Random policy
        if rollout_policy is None:
            self.pi = lambda state: random.choice(state.getLegalActions(self.agentIndex))