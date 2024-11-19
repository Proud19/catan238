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

    def __repr__(self):
        s = f"---------- {self.name} : {self.color} ----------\n"
        s += f"Victory points: {self.victoryPoints}\n"
        s += f"Resources: {self.resources}\n"
        s += f"Settlements ({self.numSettlements}/{MAX_SETTLEMENTS}): {self.settlements}\n"
        s += f"Roads ({self.numRoads}/{MAX_ROADS}): {self.roads}\n"
        s += f"Cities ({self.numCities}/{MAX_CITIES}): {self.cities}\n"
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

    def applyAction(self, action, board, gameState=None):
        if action is None:
            return

        if action[0] is ACTIONS.SETTLE:
            if not self.canSettle():
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to build a settlement!")
            
            actionVertex = action[1]
            vertex = board.getVertex(actionVertex.X, actionVertex.Y)
            self.settlements.append(vertex)
            self.resources.subtract(SETTLEMENT_COST)
            self.victoryPoints += SETTLEMENT_VICTORY_POINTS
            self.numSettlements += 1

        if action[0] is ACTIONS.ROAD:
            if not self.canBuildRoad():
                raise Exception(f"Player {self.agentIndex} doesn't have enough resources to build a road!")

            actionEdge = action[1]
            road = board.getEdge(actionEdge.X, actionEdge.Y)
            self.roads.append(road)
            self.resources.subtract(ROAD_COST)
            self.numRoads += 1
            if gameState:
                self.updateLongestRoad(board, gameState)

        if action[0] is ACTIONS.CITY:
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
            self.victoryPoints += 1
            self.numCities += 1
            self.numSettlements -= 1

        if action[0] is ACTIONS.TRADE:
            give_resource, get_resource = action[1]
            if give_resource != ResourceTypes.NOTHING and get_resource != ResourceTypes.NOTHING:
                if self.resources[give_resource] >= 4:
                    self.resources[give_resource] -= 4
                    self.resources[get_resource] += 1
                else:
                    raise Exception(f"Player {self.agentIndex} doesn't have enough resources to make this trade!")
            else:
                raise Exception(f"Cannot trade with NOTHING resource type!")

    def updateResources(self, diceRoll, board):
        newResources = Counter(board.getResourcesFromDieRollForPlayer(self.agentIndex, diceRoll))
        self.resources += newResources
        return newResources

    def collectInitialResources(self, board):
        if VERBOSE and DEBUG:
            print(f"Collecting initial resources for player {self.agentIndex}")

        for settlement in self.settlements:
            surroundingHexes = board.getHexes(settlement)
            for hex in surroundingHexes:
                if hex.resource != ResourceTypes.NOTHING:
                    self.resources[hex.resource] += 1

        if VERBOSE and DEBUG:
            print(f"Player {self.agentIndex} resources after collection: {self.resources}")

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

    def discard_half_on_seven(self):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return

        discard_count = total_resources // 2
        discarded = Counter()

        while sum(discarded.values()) < discard_count:
            resource = random.choice(list(self.resources.keys()))
            if self.resources[resource] > discarded[resource]:
                discarded[resource] += 1

        self.resources -= discarded
        return discarded

    def choose_robber_placement(self, board):
        valid_hexes = board.get_valid_robber_hexes()
        return random.choice(valid_hexes)

    def steal_resource(self, victim):
        if len(victim.resources) == 0:
            return None
        resource = random.choice(list(victim.resources.elements()))
        victim.resources[resource] -= 1
        self.resources[resource] += 1
        return resource

    def canTrade(self):
        return any(count >= 4 for count in self.resources.values())

    def getPossibleTrades(self):
        trades = []
        for give_resource in ResourceTypes:
            if give_resource != ResourceTypes.NOTHING and self.resources[give_resource] >= 4:
                for get_resource in ResourceTypes:
                    if get_resource != ResourceTypes.NOTHING and get_resource != give_resource:
                        trades.append((give_resource, get_resource))
        return trades

    def canPass(self):
        return True  # Passing is always an option

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
    
    def choose_cards_to_discard(self, discard_count):
        # Implement a smarter discarding strategy here
        # For now, we'll use a simple strategy of discarding the most abundant resources
        discarded = Counter()
        resources_list = sorted(self.resources.items(), key=lambda x: x[1], reverse=True)
        
        for resource, count in resources_list:
            while count > 0 and sum(discarded.values()) < discard_count:
                discarded[resource] += 1
                count -= 1
            
            if sum(discarded.values()) == discard_count:
                break
        
        return discarded

    def discard_half_on_seven(self):
        total_resources = sum(self.resources.values())
        if total_resources <= 7:
            return None

        discard_count = total_resources // 2
        discarded = self.choose_cards_to_discard(discard_count)
        self.resources -= discarded
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

class PlayerAgentRandom(PlayerAgent):
    def getAction(self, state):
        possibleActions = state.getLegalActions(self.agentIndex)
        if possibleActions:
            possibleActions.append((ACTIONS.PASS, None))  # Add PASS as a possible action
            chosenAction = random.choice(possibleActions)
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
                    if currAction[0] == ACTIONS.PASS:
                        break  # If PASS is an option, no need to check further
                return totalValue / len(possibleActions), None

        value, action = recurse(state, 0, self.agentIndex)
        if value is None or action is None:
            # If we've timed out, just return PASS
            return 0, (ACTIONS.PASS, None)
        return value, action

    def filterActions(self, actions):
        filtered_actions = actions + [(ACTIONS.PASS, None)]
        return filtered_actions