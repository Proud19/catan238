from agents import *
from board import BeginnerLayout, Board, Edge, Hexagon, Vertex
from gameConstants import *
from collections import Counter
from draw import Draw
import time

class GameState:
    def __init__(self, layout=BeginnerLayout):
        self.board = Board(layout)
        self.playerAgents = [None] * NUM_PLAYERS
        self.diceAgent = DiceAgent()

    def deepCopy(self):
        copy = GameState()
        copy.board = self.board.deepCopy()
        copy.playerAgents = [playerAgent.deepCopy(copy.board) for playerAgent in self.playerAgents]
        return copy

    def getLegalActions(self, agentIndex):
        legalActions = []
        if self.gameOver() >= 0:
            return legalActions
        agent = self.playerAgents[agentIndex]

        if agent.canBuildRoad():
            for road in agent.roads:
                vertices = self.board.getVertexEnds(road)
                for vertex in vertices:
                    edges = self.board.getEdgesOfVertex(vertex)
                    for edge in edges:
                        if not edge.isOccupied():
                            legalActions.append((ACTIONS.ROAD, edge))

        if agent.canSettle():
            for road in agent.roads:
                vertices = self.board.getVertexEnds(road)
                for vertex in vertices:
                    if vertex.canSettle:
                        legalActions.append((ACTIONS.SETTLE, vertex))

        if agent.canBuildCity():
            for settlement in agent.settlements:
                legalActions.append((ACTIONS.CITY, settlement))

        return legalActions

    def generateSuccessor(self, playerIndex, action):
        if self.gameOver() >= 0:
            raise Exception("Can't generate a successor of a terminal state!")

        copy = self.deepCopy()
        copy.playerAgents[playerIndex].applyAction(action, copy.board)
        copy.board.applyAction(playerIndex, action)
        return copy

    def makeMove(self, playerIndex, action):
        self.playerAgents[playerIndex].applyAction(action, self.board)
        self.board.applyAction(playerIndex, action)

    def getNumPlayerAgents(self):
        return len(self.playerAgents)

    def gameOver(self):
        for agent in self.playerAgents:
            if agent.hasWon():
                return agent.agentIndex
        return -1

    def updatePlayerResourcesForDiceRoll(self, diceRoll):
        for agent in self.playerAgents:
            gainedResources = agent.updateResources(diceRoll, self.board)
            if VERBOSE and DEBUG:
                print(f"{agent.name} received: {gainedResources}")
                print(f"{agent.name} now has: {agent.resources}")

    def applyAction(self, playerIndex, action):
        self.playerAgents[playerIndex].applyAction(action, self.board, self)
        self.board.applyAction(playerIndex, action)
        if action[0] == ACTIONS.ROAD:
            self.playerAgents[playerIndex].updateLongestRoad(self.board, self)

class Game:
    def __init__(self, playerAgentNums=None):
        self.moveHistory = []
        self.gameState = GameState()
        self.playerAgentNums = playerAgentNums 
        if GRAPHICS:
            self.draw = Draw(self.gameState.board.tiles)

    def drawGame(self):
        self.draw.drawBG()
        self.draw.drawTitle()
        self.draw.drawBoard()
        self.draw.drawRoads(self.gameState.board.allRoads, self.gameState.board)
        self.draw.drawSettlements(self.gameState.board.allSettlements)
        self.draw.drawCities(self.gameState.board.allCities)

    def createPlayer(self, playerCode, index):
        color = getColorForPlayer(index)
        playerName = f"Player {index}"

        playerTypes = {
            0: PlayerAgentRandom,
            1: lambda name, index, color: PlayerAgentExpectiminimax(name, index, color, depth=DEPTH),
            2: lambda name, index, color: PlayerAgentExpectiminimax(name, index, color, depth=DEPTH, evalFn=builderEvalFn),
            3: lambda name, index, color: PlayerAgentExpectiminimax(name, index, color, depth=DEPTH, evalFn=resourceEvalFn),
            4: lambda name, index, color: PlayerAgentExpectimax(name, index, color, depth=DEPTH, evalFn=betterEvalFn),
            5: lambda name, index, color: PlayerAgentExpectimax(name, index, color, depth=DEPTH, evalFn=builderEvalFn),
            6: lambda name, index, color: PlayerAgentExpectimax(name, index, color, depth=DEPTH, evalFn=resourceEvalFn),
            7: lambda name, index, color: PlayerAgentAlphaBeta(name, index, color, depth=DEPTH),
            8: lambda name, index, color: PlayerAgentAlphaBeta(name, index, color, depth=DEPTH, evalFn=builderEvalFn),
            9: lambda name, index, color: PlayerAgentAlphaBeta(name, index, color, depth=DEPTH, evalFn=resourceEvalFn),
            10: lambda name, index, color: PlayerAgentAlphaBeta(name, index, color, depth=DEPTH, evalFn=betterEvalFn),
            11: lambda name, index, color: PlayerAgentExpectimax(name, index, color, depth=DEPTH, evalFn=betterEvalFn),
            12: lambda name, index, color: PlayerAgentExpectiminimax(name, index, color, depth=DEPTH, evalFn=betterEvalFn)
        }

        return playerTypes.get(playerCode, PlayerAgentRandom)(playerName, index, color)

    def initializePlayers(self):
        if self.playerAgentNums is None:
            self.playerAgentNums = getPlayerAgentSpecifications()
        for i in range(NUM_PLAYERS):
            self.gameState.playerAgents[i] = self.createPlayer(self.playerAgentNums[i], i)

    def initializeSettlementsAndResourcesLumberBrick(self):
        settlements = self.gameState.board.getRandomVerticesForSettlement()
        for i, playerSettlements in enumerate(settlements):
            agent = self.gameState.playerAgents[i]
            settleOne, settleTwo = playerSettlements
            agent.settlements.extend([settleOne, settleTwo])
            roadOne = self.gameState.board.getRandomRoad(settleOne)
            roadTwo = self.gameState.board.getRandomRoad(settleTwo)
            self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, roadOne))
            self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, roadTwo))
            agent.roads.extend([roadOne, roadTwo])

        for agent in self.gameState.playerAgents:
            agent.collectInitialResources(self.gameState.board)

    def initializeSettlementsAndResourcesForSettlements(self):
        if VERBOSE and DEBUG:
            print("Initializing settlements and resources for settlements")
        settlements = self.gameState.board.getRandomVerticesForAllResources()
        for i, playerSettlements in enumerate(settlements):
            agent = self.gameState.playerAgents[i]
            for settlement in playerSettlements:
                randomRoad = self.gameState.board.getRandomRoad(settlement)
                self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, randomRoad))
                agent.settlements.append(settlement)
                agent.roads.append(randomRoad)

        for agent in self.gameState.playerAgents:
            agent.collectInitialResources(self.gameState.board)

    def initializeSettlementsAndResourcesRandom(self):
        if VERBOSE and DEBUG:
            print("Initializing settlements and resources randomly")
        for agent in self.gameState.playerAgents:
            for _ in range(NUM_INITIAL_SETTLEMENTS):
                settlement = self.gameState.board.getRandomVertexForSettlement()
                self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.SETTLE, settlement))
                agent.settlements.append(settlement)
                road = self.gameState.board.getRandomRoad(settlement)
                self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, road))
                agent.roads.append(road)

        for agent in self.gameState.playerAgents:
            agent.collectInitialResources(self.gameState.board)

    def initializeSettlementsAndResourcesPreset(self):
        if VERBOSE and DEBUG:
            print("Initializing settlements and resources with preset values")
        initialSettlements = [
            (self.gameState.board.getVertex(2, 4), self.gameState.board.getVertex(4, 8)),
            (self.gameState.board.getVertex(2, 8), self.gameState.board.getVertex(3, 5)),
            (self.gameState.board.getVertex(3, 1), self.gameState.board.getVertex(4, 3)),
            (self.gameState.board.getVertex(1, 4), self.gameState.board.getVertex(4, 6))
        ]
        initialRoads = [
            (self.gameState.board.getEdge(4, 3), self.gameState.board.getEdge(8, 8)),
            (self.gameState.board.getEdge(4, 7), self.gameState.board.getEdge(6, 4)),
            (self.gameState.board.getEdge(6, 1), self.gameState.board.getEdge(8, 3)),
            (self.gameState.board.getEdge(2, 3), self.gameState.board.getEdge(8, 6))
        ]

        for i, agent in enumerate(self.gameState.playerAgents):
            for s in range(NUM_INITIAL_SETTLEMENTS):
                settlement = initialSettlements[i][s]
                self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.SETTLE, settlement))
                agent.settlements.append(settlement)
                road = initialRoads[i][s]
                self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, road))
                agent.roads.append(road)

        for agent in self.gameState.playerAgents:
            agent.collectInitialResources(self.gameState.board)

    def run(self):
        if VERBOSE:
            print("WELCOME TO SETTLERS OF CATAN!")
            print("-----------------------------")

        self.initializePlayers()
        self.initializeSettlementsAndResourcesLumberBrick()

        turnNumber = 1
        currentAgentIndex = 0

        while self.gameState.gameOver() < 0:
            if GRAPHICS:
                self.drawGame()

            currentAgent = self.gameState.playerAgents[currentAgentIndex]
            if VERBOSE:
                print(f"---------- TURN {turnNumber} --------------")
                print(f"It's {currentAgent.name}'s turn!")
                print("PLAYER INFO:")
                for a in self.gameState.playerAgents:
                    print(a)

            if GRAPHICS:
                input("Press ENTER to proceed:")

            diceRoll = self.gameState.diceAgent.rollDice()
            if VERBOSE:
                print(f"Rolled a {diceRoll}")

            self.gameState.updatePlayerResourcesForDiceRoll(diceRoll)

            value, action = currentAgent.getAction(self.gameState)
            if action is not None:
                self.gameState.applyAction(currentAgentIndex, action)

                if VERBOSE:
                    print(f"{currentAgent.name} took action {action[0]} at {action[1]}")

                if action[0] == ACTIONS.ROAD and currentAgent.numRoads >= MAX_ROADS:
                    if VERBOSE:
                        print(f"{currentAgent.name} has reached the maximum number of roads ({MAX_ROADS}).")
                elif action[0] == ACTIONS.SETTLE and currentAgent.numSettlements >= MAX_SETTLEMENTS:
                    if VERBOSE:
                        print(f"{currentAgent.name} has reached the maximum number of settlements ({MAX_SETTLEMENTS}).")
                elif action[0] == ACTIONS.CITY and currentAgent.numCities >= MAX_CITIES:
                    if VERBOSE:
                        print(f"{currentAgent.name} has reached the maximum number of cities ({MAX_CITIES}).")
                if GRAPHICS:
                    self.drawGame()
            else:
                if VERBOSE:
                    print(f"{currentAgent.name} had no actions to take")

            self.moveHistory.append((currentAgent.name, action))
            currentAgentIndex = (currentAgentIndex + 1) % self.gameState.getNumPlayerAgents()
            turnNumber += 1

            if VERBOSE:
                print("\nUpdated PLAYER INFO:")
                for a in self.gameState.playerAgents:
                    print(a)
                print()

            if turnNumber > CUTOFF_TURNS:
                print("Game reached turn limit without a winner.")
                break

        winner = self.gameState.gameOver()
        if winner < 0:
            return winner, turnNumber, -1
        agentWinner = self.gameState.playerAgents[winner]
        agentLoser = self.gameState.playerAgents[1 - winner]
        if VERBOSE:
            print(f"{agentWinner.name} won the game")
        return winner, turnNumber, agentWinner.victoryPoints - agentLoser.victoryPoints

def getStringForPlayer(playerCode):
    playerTypes = {
        0: "Random Agent",
        1: "ExpectiMiniMax Agent - with default heuristic",
        2: "ExpectiMiniMax Agent - with builder Heuristic",
        3: "ExpectiMiniMax Agent - with resource Heuristic",
        4: "Expectimax Agent - with default heuristic",
        5: "Expectimax Agent - with builder Heuristic",
        6: "Expectimax Agent - with resource Heuristic",
        7: "AlphaBeta Agent - with default Heuristic",
        8: "AlphaBeta Agent - with builder Heuristic",
        9: "AlphaBeta Agent - with resource Heuristic",
        10: "AlphaBeta Agent - with better Heuristic",
        11: "Expectimax Agent - with better Heuristic",
        12: "Expectiminimax Agent - with better Heuristic"
    }
    return playerTypes.get(playerCode, "Not a player.")

def getPlayerAgentSpecifications():
    if VERBOSE:
        print("Player Agent Specifications:")
        print("-----------------------------")
        for i, agent in enumerate([
            "Random Agent",
            "ExpectiMiniMax Agent - with default heuristic",
            "ExpectiMiniMax Agent - with builder Heuristic",
            "ExpectiMiniMax Agent - with resource Heuristic",
            "Expectimax Agent - with default heuristic",
            "Expectimax Agent - with builder Heuristic",
            "Expectimax Agent - with resource Heuristic",
            "AlphaBeta Agent - with default Heuristic",
            "AlphaBeta Agent - with builder Heuristic",
            "AlphaBeta Agent - with resource Heuristic",
            "AlphaBeta Agent - with better Heuristic",
            "Expectimax Agent - with better Heuristic",
            "Expectiminimax Agent - with better Heuristic"
        ]):
            print(f"{i}: {agent}")

        firstPlayerAgent = int(input("Which player type should the first player be: ").strip())
        secondPlayerAgent = int(input("Which player type should the second player be: "). strip())
        return [firstPlayerAgent, secondPlayerAgent]
    else:
        return DEFAULT_PLAYER_ARRAY

if __name__ == "__main__":
    game = Game()
    game.run()