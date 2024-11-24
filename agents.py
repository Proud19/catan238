from collections import Counter
import copy
from gameConstants import *
import random
import time

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
            return True
        return False
    
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

    def __repr__(self):
        s = f"---------- {self.name} : {self.color} ----------\n"
        s += f"Victory points: {self.victoryPoints}\n"
        s += f"Resources: {self.resources}\n"
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

    def print_resources(self):
        for resource, amount in self.resources.items():
            print(f"{resource.name.capitalize()}: {amount}")

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
                print(f"Player {self.agentIndex} bought a development card: {card}")
            else:
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
                            edge = board.getEdge(road_coords[0], road_coords[1])
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
                        amount = player.resources[resource]
                        player.resources[resource] = 0
                        self.resources[resource] += amount
                        total_stolen += amount
                if VERBOSE:
                    if total_stolen > 0:
                        print(f"{self.name} used Monopoly and collected {total_stolen} {resource.name}")
                    else:
                        print(f"{self.name} used Monopoly on {resource.name}, but no resources were collected")
            elif card_type == DevCardTypes.VICTORY_POINT:
                self.victoryPoints += 1

            # Mark that a dev card has been played this turn
            self.dev_card_played_this_turn = True

            return action[1]  # Return the card_action for dev cards

    def updateResources(self, diceRoll, board):
        newResources = Counter(board.getResourcesFromDieRollForPlayer(self.agentIndex, diceRoll))
        self.resources += newResources
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

        self.resources -= discarded
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
        victim.resources[resource] -= 1
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
            edge = board.getEdge(road_coords[0], road_coords[1])
            if edge and not edge.isOccupied():
                if board.canBuildRoadAt(self.agentIndex, road_coords[0], road_coords[1]):
                    edge.build(self.agentIndex)
                    self.roads.append(edge)
                    board.allRoads.append(edge)
                    # Remove the increment from here, as it's now done in applyAction
                    return True
        return False
    
class PlayerAgentExpectiminimax(PlayerAgent):
    def __init__(self, name, agentIndex, color, depth=3, evalFn=defaultEvalFn):
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

class PlayerAgentAlphaBeta(PlayerAgent):
    def __init__(self, name, agentIndex, color, depth=3, evalFn=defaultEvalFn):
        super(PlayerAgentAlphaBeta, self).__init__(name, agentIndex, color, depth, evalFn=evalFn)
        self.TIME_LIMIT = 5  # 5 seconds

    def getAction(self, state):
        start_time = time.time()

        def recurse(currState, currDepth, playerIndex, alpha, beta):
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
                            value, _ = recurse(successor, newDepth, playerIndex, alpha, beta)
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    if currVal > bestValue:
                        bestValue = currVal
                        bestAction = currAction
                    alpha = max(alpha, bestValue)
                    if beta <= alpha:
                        break
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
                            value, _ = recurse(successor, newDepth, playerIndex, alpha, beta)
                            if value is None:  # Timeout
                                return None, None
                            currVal += probability * value
                    if currVal < worstValue:
                        worstValue = currVal
                        worstAction = currAction
                    beta = min(beta, worstValue)
                    if beta <= alpha:
                        break
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is the worst action, no need to check further
                return worstValue, worstAction

        value, action = recurse(state, 0, self.agentIndex, float("-inf"), float("inf"))
        if value is None or action is None:
            # If we've timed out, just return PASS
            return 0, (ACTIONS.PASS, None)
        return value, action

    def filterActions(self, actions):
        filtered_actions = actions + [(ACTIONS.PASS, None)]
        return filtered_actions
    
    def discard_half_on_seven(self, gameState):
        return super().discard_half_on_seven(gameState)

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
    def getAction(self, gameState):
        possibleActions = gameState.getLegalActions(self.agentIndex)
        if possibleActions:

            print(f"Player {self.agentIndex} - Choose an action:")
            for i, action in enumerate(possibleActions):
                print(f"{i + 1}: {action}")

            actionIndex = int(input("Enter the number of the action you want to take: ")) - 1

            if actionIndex < 0 or actionIndex >= len(possibleActions):
                print("Invalid action index. Please try again.")
                actionIndex = int(input("Enter the number of the action you want to take: ")) - 1

            chosenAction = possibleActions[actionIndex]
            
            if chosenAction[0] == ACTIONS.PLAY_DEV_CARD:
                card_type = chosenAction[1]
                if card_type == DevCardTypes.ROAD_BUILDING:
                    legal_spots = self.get_legal_road_spots(gameState.board)

                    print("Choose two roads to build:")
                    for i, spot in enumerate(legal_spots):
                        print(f"{i + 1}: {spot}")
                    road1 = int(input("Enter the number of the first road: ")) - 1
                    road2 = int(input("Enter the number of the second road: ")) - 1
                    roads = [legal_spots[road1], legal_spots[road2]]
                    return (0, (ACTIONS.PLAY_DEV_CARD, (DevCardTypes.ROAD_BUILDING, roads)))
                elif card_type == DevCardTypes.YEAR_OF_PLENTY:
                    print("Choose two resources to collect:")
                    resources = []
                    for i in range(2):
                        resource = int(input(f"Enter the number of resource {i + 1}: "))
                        resources.append(ResourceTypes(resource))
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, resources)))
                elif card_type == DevCardTypes.MONOPOLY:
                    resource = int(input("Choose a resource to steal: "))
                    return (0, (ACTIONS.PLAY_DEV_CARD, (card_type, ResourceTypes(resource))))
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

        print("Choose a hex to place the robber:")
        for i, hex in enumerate(valid_hexes):
            print(f"{i + 1}: {hex}")
        hexIndex = int(input("Enter the number of the hex you want to place the robber on: ")) - 1

        if hexIndex < 0 or hexIndex >= len(valid_hexes):
            print("Invalid hex index. Please try again.")
            hexIndex = int(input("Enter the number of the hex you want to place the robber on: ")) - 1

        return valid_hexes[hexIndex]
    
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