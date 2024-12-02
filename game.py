# Fixes with initialization
# Collecting initial resources
# If I let the bot go first, I have to initialize 2x
# I think there may be a bug with canBuildRoad in agents.

import pygame
from agents import *
from board import BeginnerLayout, Board, Edge, Hexagon, Vertex
from gameConstants import *
from collections import Counter
from draw import Draw
import time

import argparse

class GameState:
    def __init__(self, layout=BeginnerLayout):
        self.board = Board(layout)
        self.playerAgents = [None] * NUM_PLAYERS
        self.diceAgent = DiceAgent()
        self.bank = Counter(BANK_RESOURCES)
        self.dev_card_deck = DEV_CARD_DECK.copy()
        random.shuffle(self.dev_card_deck)
        self.largest_army_holder = None

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

        if agent.canTrade(self):
            for trade in agent.getPossibleTrades(self):
                legalActions.append((ACTIONS.TRADE, trade))

        if agent.canBuyDevCard(self):
            legalActions.append((ACTIONS.BUY_DEV_CARD, None))
        for card in agent.dev_cards:
            if card.can_be_used and not card.has_been_used:
                if card.type == DevCardTypes.KNIGHT:
                    for hex in self.board.get_valid_robber_hexes():
                        legalActions.append((ACTIONS.PLAY_DEV_CARD, (card.type, hex)))
                elif card.type == DevCardTypes.ROAD_BUILDING: 
                    for road in agent.roads:
                        vertices = self.board.getVertexEnds(road)
                        for vertex in vertices:
                            edges = self.board.getEdgesOfVertex(vertex)
                            for edge in edges:
                                if not edge.isOccupied():
                                    legalActions.append((ACTIONS.PLAY_DEV_CARD, (card.type, [edge]))) 
                                    #TODO: Should be able to build more than one road but limiting to one for now 
                                    """
                                    Consider doing: 
                                    print("Choose two roads to build:")
                                    edge1 = choose_edge(legal_edges, gameState.board, self.draw)
                                    self.buildRoad((edge1.X, edge1.Y), gameState.board, gameState)
                                    legal_edges = [Edge(spot[0], spot[1]) for spot in self.get_legal_road_spots(gameState.board)]
                                    edge2 = choose_edge(legal_edges, gameState.board, self.draw)
                                    """
                elif card.type == DevCardTypes.YEAR_OF_PLENTY: 
                    legalActions.append((ACTIONS.PLAY_DEV_CARD, (card.type, [ResourceTypes.GRAIN, ResourceTypes.LUMBER])))
                elif card.type == DevCardTypes.MONOPOLY: 
                    legalActions.append((ACTIONS.PLAY_DEV_CARD, (card.type, ResourceTypes.GRAIN)))
            

        legalActions.append((ACTIONS.PASS, None))
        # print(legalActions)

        return legalActions

    def generateSuccessor(self, playerIndex, action):
        if self.gameOver() >= 0:
            raise Exception("Can't generate a successor of a terminal state!")

        copy = self.deepCopy()
        # copy.playerAgents[playerIndex].applyAction(action, copy.board, copy)
        copy.board.applyAction(playerIndex, action)
        copy.playerAgents[playerIndex].applyAction(action, copy.board, copy)
        
        
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
        hexagons = self.board.dieRollDict.get(diceRoll, [])
        player_resources = {i: Counter() for i in range(NUM_PLAYERS)}

        for hexagon in hexagons:
            if (hexagon.resource != ResourceTypes.NOTHING):
                for vertex in self.board.getVertices(hexagon):
                    if vertex.player is not None:
                        player_resources[vertex.player][hexagon.resource] += 1
                        if vertex.isCity:
                            player_resources[vertex.player][hexagon.resource] += 1

        for player_index, resources in player_resources.items():
            can_fulfill = all(self.bank[resource] >= amount for resource, amount in resources.items())
            if can_fulfill:
                for resource, amount in resources.items():
                    self.bank[resource] -= amount
                    self.playerAgents[player_index].resources[resource] += amount
            else:
                # If bank can't fulfill the entire request, no one gets any resources
                pass

        if VERBOSE and DEBUG:
            for agent in self.playerAgents:
                print(f"{agent.name} received: {player_resources[agent.agentIndex] if can_fulfill else 'Nothing'}")
                print(f"{agent.name} now has: {agent.resources}")

    def applyAction(self, playerIndex, action):
        # raise NotImplementedError
        result = self.playerAgents[playerIndex].applyAction(action, self.board, self)
        self.board.applyAction(playerIndex, action)
        if action[0] == ACTIONS.ROAD:
            self.playerAgents[playerIndex].updateLongestRoad(self.board, self)
        return result

    def format_bank_resources(self):
        return ', '.join([f"{ResourceDict[resource]}: {count}" for resource, count in self.bank.items()])

    def drawDevCard(self):
        if len(self.dev_card_deck) > 0:
            return self.dev_card_deck.pop()
        return None
    
    def move_robber_and_steal(self, moving_player, new_hex):
        if VERBOSE:
            print(f"{moving_player.name} moved the robber to hex {new_hex}")
        
        self.board.move_robber(new_hex)
        victims = [p for p in self.playerAgents 
                if p != moving_player and any(v in self.board.getVertices(new_hex) 
                                                for v in p.settlements + p.cities)]
        if victims:
            victim = random.choice(victims)
            stolen_resource = moving_player.steal_resource(victim)
            if VERBOSE:
                if stolen_resource:
                    print(f"{moving_player.name} stole a {stolen_resource.name} from {victim.name}")
                else:
                    print(f"{moving_player.name} attempted to steal from {victim.name}, but they had no resources")
        elif VERBOSE:
            print(f"No players to steal from at the new robber location")
    
    def checkLargestArmy(self):
        players_with_3_plus_knights = [player for player in self.playerAgents if player.played_knights >= LARGEST_ARMY_REQUIREMENT]
        
        if not players_with_3_plus_knights:
            if self.largest_army_holder:
                self.largest_army_holder.has_largest_army = False
                self.largest_army_holder.victoryPoints -= LARGEST_ARMY_POINTS
                self.largest_army_holder = None
            return

        new_largest_army_player = max(players_with_3_plus_knights, key=lambda p: p.played_knights)

        if self.largest_army_holder != new_largest_army_player:
            if self.largest_army_holder:
                self.largest_army_holder.has_largest_army = False
                self.largest_army_holder.victoryPoints -= LARGEST_ARMY_POINTS
            
            new_largest_army_player.has_largest_army = True
            new_largest_army_player.victoryPoints += LARGEST_ARMY_POINTS
            self.largest_army_holder = new_largest_army_player

        if VERBOSE:
            print(f"{self.largest_army_holder.name} now holds the Largest Army with {self.largest_army_holder.played_knights} knights played.")

class Game:
    def __init__(self, playerAgentNums=None):
        if GRAPHICS: 
            pygame.init()
            self.screen_width = 1020
            self.screen_height = 800
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            pygame.display.set_caption("Settlers of Catan")
            self.clock = pygame.time.Clock()

        self.moveHistory = []
        self.gameState = GameState()
        self.playerAgentNums = playerAgentNums 
        self.menu_state = "MAIN"  # Can be "MAIN", "GAME", or "WINNER"
        
        
        if GRAPHICS: 
            self.load_images()
            self.init_menu()

        # Initialize game-specific variables
        self.currentAgentIndex = 0
        self.turnNumber = 1
    
    def load_images(self):
        self.menu_bg = pygame.image.load("resources/menuScreen.gif").convert()
        self.menu_bg = pygame.transform.scale(self.menu_bg, (self.screen_width, self.screen_height))
        self.catan_logo = pygame.image.load("resources/catan.gif").convert_alpha()
        self.winner_bg = pygame.image.load("resources/winner.gif").convert()
        self.winner_bg = pygame.transform.scale(self.winner_bg, (self.screen_width, self.screen_height))

    def init_menu(self):
        # Create buttons
        self.font = pygame.font.Font(None, 36)
        button_width, button_height = 200, 50
        self.start_button = pygame.Rect((self.screen_width - button_width) // 2, 300, button_width, button_height)
        self.quit_button = pygame.Rect((self.screen_width - button_width) // 2, 400, button_width, button_height)

    def draw_menu(self):
        self.screen.blit(self.menu_bg, (0, 0))
        pygame.draw.rect(self.screen, (0, 255, 0), self.start_button)
        pygame.draw.rect(self.screen, (255, 0, 0), self.quit_button)
        
        start_text = self.font.render("Start Game", True, (0, 0, 0))
        quit_text = self.font.render("Quit", True, (0, 0, 0))
        
        self.screen.blit(start_text, (self.start_button.x + (self.start_button.width - start_text.get_width()) // 2,
                                      self.start_button.y + (self.start_button.height - start_text.get_height()) // 2))
        self.screen.blit(quit_text, (self.quit_button.x + (self.quit_button.width - quit_text.get_width()) // 2,
                                     self.quit_button.y + (self.quit_button.height - quit_text.get_height()) // 2))

    def draw_winner(self, winner):
        self.screen.blit(self.winner_bg, (0, 0))
        winner_text = self.font.render(f"Player {winner} wins!", True, (255, 255, 255))
        text_rect = winner_text.get_rect(center=(self.screen_width // 2, 200))
        self.screen.blit(winner_text, text_rect)
        
        pygame.draw.rect(self.screen, (0, 255, 0), self.start_button)
        new_game_text = self.font.render("New Game", True, (0, 0, 0))
        self.screen.blit(new_game_text, (self.start_button.x + (self.start_button.width - new_game_text.get_width()) // 2,
                                         self.start_button.y + (self.start_button.height - new_game_text.get_height()) // 2))

    def reset_game(self):
        if VERBOSE and DEBUG:
            print("Resetting game")
        self.moveHistory = []
        self.gameState = GameState()
        self.currentAgentIndex = 0
        self.turnNumber = 1
        if GRAPHICS:
            self.draw = Draw(self.gameState.board.tiles, self.screen, self.gameState.board)
        self.initializePlayers()
        # self.initializeSettlementsAndResourcesLumberBrick()
        self.gameState.board.set_draw(self.draw)
        self.initializeBasedOnPlayerAgent()

        if VERBOSE and DEBUG:
            print("Player agent nums: ", self.playerAgentNums)

        for i, agent_num in enumerate(self.playerAgentNums):
            if VERBOSE and DEBUG:
                print("Agent num: ", agent_num)
            if agent_num == 1:
                if VERBOSE and DEBUG:
                    print("Setting draw for human avent")
                self.gameState.playerAgents[i].set_draw(self.draw)


    def drawGame(self):
        self.draw.drawBG()
        self.screen.blit(self.catan_logo, (20, 20))  # Draw Catan logo in top-left corner
        self.draw.drawBoard()
        self.draw.drawRoads(self.gameState.board.allRoads, self.gameState.board)
        self.draw.drawSettlements(self.gameState.board.allSettlements)
        self.draw.drawCities(self.gameState.board.allCities)

    def createPlayer(self, playerCode, index):
        color = getColorForPlayer(index)
        playerName = f"Player {index}"

        playerTypes = {
            0: PlayerAgentRandom,
            1: lambda name, index, color: PlayerAgentHuman(name, index, color), 
            2: lambda name, index, color: PlayerAgentExpectimax(name, index, color),
            3: lambda name, index, color: ValueFunctionPlayer(name, index, color),
        }

        return playerTypes.get(playerCode, PlayerAgentRandom)(playerName, index, color)

    def initializePlayers(self):
        if self.playerAgentNums is None:
            self.playerAgentNums = getPlayerAgentSpecifications()
        for i in range(NUM_PLAYERS):
            self.gameState.playerAgents[i] = self.createPlayer(self.playerAgentNums[i], i)

    def initializeBasedOnPlayerAgent(self):
        self.drawGame()
        pygame.display.flip()
        for i in [0,1,1,0]:
            agent = self.gameState.playerAgents[i]

            # Get settlement
            if isinstance(self.gameState.playerAgents[i], PlayerAgentHuman):
                vertex = self.gameState.board.getHumanVertexForSettlement()
            elif isinstance(self.gameState.playerAgents[i], PlayerAgentRandom) or isinstance(self.gameState.playerAgents[i], PlayerAgentExpectimax) or isinstance(self.gameState.playerAgents[i], ValueFunctionPlayer):
                vertex = self.gameState.board.getRandomVertexForSettlement()
            
            
            self.gameState.board.applyAction(i, (ACTIONS.SETTLE, vertex))
            agent.settlements.extend([vertex])

            self.drawGame()
            pygame.display.flip()

            # Get connected road
            if isinstance(self.gameState.playerAgents[i], PlayerAgentHuman):
                road = self.gameState.board.getHumanRoad(vertex)
            elif isinstance(self.gameState.playerAgents[i], PlayerAgentRandom) or isinstance(self.gameState.playerAgents[i], PlayerAgentExpectimax) or isinstance(self.gameState.playerAgents[i], ValueFunctionPlayer):
                road = self.gameState.board.getRandomRoad(vertex)
            
            self.gameState.board.applyAction(i, (ACTIONS.ROAD, road))
            agent.roads.extend([road])

            self.drawGame()
            pygame.display.flip()

        for i in range(2):
            self.gameState.playerAgents[i].collectInitialResources(self.gameState.board)

    def initializeSettlementsAndResourcesLumberBrick(self):
        settlements = self.gameState.board.getRandomVerticesForSettlement()
        for i, playerSettlements in enumerate(settlements):
            agent = self.gameState.playerAgents[i]
            settleOne, settleTwo = playerSettlements
            agent.settlements.extend([settleOne, settleTwo])
            roadOne = self.gameState.board.getRandomRoad(settleOne) #TODO: These should not be random
            roadTwo = self.gameState.board.getRandomRoad(settleTwo)
            self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, roadOne))
            self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, roadTwo))
            agent.roads.extend([roadOne, roadTwo])

        for agent in self.gameState.playerAgents:
            initial_resources = agent.collectInitialResources(self.gameState.board)
            if initial_resources:  # Check if initial_resources is not empty
                can_fulfill = all(self.gameState.bank[resource] >= amount for resource, amount in initial_resources.items())
                if can_fulfill:
                    for resource, amount in initial_resources.items():
                        self.gameState.bank[resource] -= amount
                        agent.resources[resource] += amount
                else:
                    if VERBOSE:
                        print(f"Bank couldn't fulfill initial resources for {agent.name}")
            else:
                if VERBOSE:
                    print(f"No initial resources collected for {agent.name}")

    # def initializeSettlementsAndResourcesForSettlements(self):
    #     if VERBOSE and DEBUG:
    #         print("Initializing settlements and resources for settlements")
    #     settlements = self.gameState.board.getRandomVerticesForAllResources()
    #     for i, playerSettlements in enumerate(settlements):
    #         agent = self.gameState.playerAgents[i]
    #         for settlement in playerSettlements:
    #             randomRoad = self.gameState.board.getRandomRoad(settlement)
    #             self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, randomRoad))
    #             agent.settlements.append(settlement)
    #             agent.roads.append(randomRoad)

    #     for agent in self.gameState.playerAgents:
    #         agent.collectInitialResources(self.gameState.board)

    # def initializeSettlementsAndResourcesRandom(self):
    #     if VERBOSE and DEBUG:
    #         print("Initializing settlements and resources randomly")
    #     for agent in self.gameState.playerAgents:
    #         for _ in range(NUM_INITIAL_SETTLEMENTS):
    #             settlement = self.gameState.board.getRandomVertexForSettlement()
    #             self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.SETTLE, settlement))
    #             agent.settlements.append(settlement)
    #             road = self.gameState.board.getRandomRoad(settlement)
    #             self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, road))
    #             agent.roads.append(road)

    #     for agent in self.gameState.playerAgents:
    #         agent.collectInitialResources(self.gameState.board)

    # def initializeSettlementsAndResourcesPreset(self):
    #     if VERBOSE and DEBUG:
    #         print("Initializing settlements and resources with preset values")
    #     initialSettlements = [
    #         (self.gameState.board.getVertex(2, 4), self.gameState.board.getVertex(4, 8)),
    #         (self.gameState.board.getVertex(2, 8), self.gameState.board.getVertex(3, 5)),
    #         (self.gameState.board.getVertex(3, 1), self.gameState.board.getVertex(4, 3)),
    #         (self.gameState.board.getVertex(1, 4), self.gameState.board.getVertex(4, 6))
    #     ]
    #     initialRoads = [
    #         (self.gameState.board.getEdge(4, 3), self.gameState.board.getEdge(8, 8)),
    #         (self.gameState.board.getEdge(4, 7), self.gameState.board.getEdge(6, 4)),
    #         (self.gameState.board.getEdge(6, 1), self.gameState.board.getEdge(8, 3)),
    #         (self.gameState.board.getEdge(2, 3), self.gameState.board.getEdge(8, 6))
    #     ]

    #     for i, agent in enumerate(self.gameState.playerAgents):
    #         for s in range(NUM_INITIAL_SETTLEMENTS):
    #             settlement = initialSettlements[i][s]
    #             self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.SETTLE, settlement))
    #             agent.settlements.append(settlement)
    #             road = initialRoads[i][s]
    #             self.gameState.board.applyAction(agent.agentIndex, (ACTIONS.ROAD, road))
    #             agent.roads.append(road)

    #     for agent in self.gameState.playerAgents:
    #         agent.collectInitialResources(self.gameState.board)
    
    def handle_seven_rolled(self, current_player):
        if VERBOSE:
            print("A 7 was rolled! Moving the robber...")

        # First, handle discarding
        for player in self.gameState.playerAgents:
            discarded = player.discard_half_on_seven(self.gameState)
            if discarded:
                if VERBOSE:
                    print(f"{player.name} discarded {sum(discarded.values())} resources: {discarded}")

        # Now, move the robber and steal
        new_hex = current_player.choose_robber_placement(self.gameState.board)
        self.gameState.move_robber_and_steal(current_player, new_hex)

        if GRAPHICS:
            self.drawGame()

    def run(self):
        if VERBOSE:
            print("WELCOME TO SETTLERS OF CATAN!")
            print("-----------------------------")


        self.initializePlayers()
        self.initializeSettlementsAndResourcesLumberBrick()
        running = True

        if GRAPHICS: 
            while running:
                if self.menu_state == "MAIN":
                    self.draw_menu()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self.start_button.collidepoint(event.pos):
                                self.menu_state = "GAME"
                                self.reset_game()
                            elif self.quit_button.collidepoint(event.pos):
                                running = False

                elif self.menu_state == "GAME":
                    if self.gameState.gameOver() >= 0:
                        self.menu_state = "WINNER"
                    elif not AUTORUN:
                        self.drawGame()
                        waiting_for_input = True
                        while waiting_for_input:
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    running = False
                                    waiting_for_input = False
                                elif event.type == pygame.KEYDOWN:
                                    if event.key == pygame.K_RETURN:
                                        waiting_for_input = False
                                        self.run_game_turn()
                            pygame.display.flip()
                            self.clock.tick(60)
                    else:
                        self.run_game_turn()

                elif self.menu_state == "WINNER":
                    self.draw_winner(self.gameState.gameOver())
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self.start_button.collidepoint(event.pos):
                                self.menu_state = "MAIN"
                                self.reset_game()

                pygame.display.flip()
                self.clock.tick(60)

            pygame.quit()
        else: 
            while running: 
                if self.gameState.gameOver() >= 0: 
                    running = False
                    break
                self.run_game_turn()

        winner = self.gameState.gameOver()
        if winner < 0:
            return winner, self.turnNumber, -1
        agentWinner = self.gameState.playerAgents[winner]
        agentLoser = self.gameState.playerAgents[1 - winner]
        if VERBOSE:
            print(f"{agentWinner.name} won the game")
        return winner, self.turnNumber, agentWinner.victoryPoints - agentLoser.victoryPoints
    
    def run_game_turn(self):
        if GRAPHICS and not hasattr(self, 'draw'):
            self.draw = Draw(self.gameState.board.tiles, self.screen, self.gameState.board)

        currentAgent = self.gameState.playerAgents[self.currentAgentIndex]
        if VERBOSE:
            print(f"---------- TURN {self.turnNumber} --------------")
            print(f"It's {currentAgent.name}'s turn!")
            print("BANK INFO:")
            print(self.gameState.format_bank_resources())
            print("\nPLAYER INFO:")
            for a in self.gameState.playerAgents:
                print(a)

        diceRoll = self.gameState.diceAgent.rollDice()
        if VERBOSE:
            print(f"Rolled a {diceRoll}")

        if diceRoll == 7:
            self.handle_seven_rolled(currentAgent)
        else:
            self.gameState.updatePlayerResourcesForDiceRoll(diceRoll)

        actions_taken = []
        currentAgent.dev_card_played_this_turn = False  # Reset at the start of the turn
        while True:
            value, action = currentAgent.getAction(self.gameState)
            if action[0] == ACTIONS.PASS:
                if VERBOSE:
                    print(f"{currentAgent.name} chose to pass.")
                break

            if action[0] == ACTIONS.PLAY_DEV_CARD:
                card_type, card_action = action[1]

                # Apply the action
                self.gameState.applyAction(self.currentAgentIndex, action)
            else:
                self.gameState.applyAction(self.currentAgentIndex, action)

            actions_taken.append(action)

            if VERBOSE:
                print(f"{currentAgent.name} took action {action[0]} at {action[1]}")

            if GRAPHICS:
                self.drawGame()
        
        self.gameState.checkLargestArmy()
        currentAgent.endTurn()
        self.moveHistory.append((currentAgent.name, actions_taken))
        self.currentAgentIndex = (self.currentAgentIndex + 1) % self.gameState.getNumPlayerAgents()
        self.turnNumber += 1

        if VERBOSE:
            print("\nUpdated BANK INFO:")
            print(self.gameState.format_bank_resources())
            print("\nUpdated PLAYER INFO:")
            for a in self.gameState.playerAgents:
                print(a)
            print()

        if self.turnNumber > CUTOFF_TURNS:
            print("Game reached turn limit without a winner.")
            self.menu_state = "WINNER"
        


def getStringForPlayer(playerCode):
    playerTypes = {
        0: "Random Agent",
        1: "Human Player",
        2: "Expectimax Agent",
        3: "Value Function Player"
    }
    return playerTypes.get(playerCode, "Not a player.")

def getPlayerAgentSpecifications():
    if VERBOSE:
        print("Player Agent Specifications:")
        print("-----------------------------")
        for i, agent in enumerate([
            "Random Agent",
            "Human Player",
            "Expectimax Agent",
            "Value Function Player"
        ]):
            print(f"{i}: {agent}")

        firstPlayerAgent = int(input("Which player type should the first player be: ").strip())
        secondPlayerAgent = int(input("Which player type should the second player be: "). strip())
        return [firstPlayerAgent, secondPlayerAgent]
    else:
        return DEFAULT_PLAYER_ARRAY
    


def run_simulations(n):
    # setting suitable params to run simulations 
    VERBOSE = False
    GRAPHICS = False
    DEBUG = False


    playerAgentNums = [0, 3]  # This currently simulates random players
    agentNames = ["PlayerAgentRandom", "ValueFunctionPlayer"]
    wins = [0, 0]

    for _ in range(n): 
        game = Game(playerAgentNums=playerAgentNums)
        winnerIndex, _, _ = game.run()
        if winnerIndex == 0 or winnerIndex == 1: 
            wins[winnerIndex] += 1
        print("The winner of this round is ", winnerIndex)

    # Formatting the results nicely
    print("\nSimulation Results:")
    print("=" * 20)
    print(f"{'Agent Name':<10} | {'Wins':<5}")
    print("-" * 20)
    for i, name in enumerate(agentNames):
        print(f"{name:<10} | {wins[i]:<5}")
    print("=" * 20)
    print(f"Total Simulations: {n}")
    

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run game simulations or a single game.")
    parser.add_argument(
        "-s", "--simulation-type",
        type=str,
        choices=["random"],  # Add more simulation types as needed
        help="The type of simulation to run (e.g., 'random')."
    )
    parser.add_argument(
        "-n", "--num-simulations",
        type=int,
        help="The number of simulations to run."
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Conditional execution
    if args.simulation_type and args.num_simulations:
        # Run simulations if both arguments are provided
        run_simulations(args.num_simulations)
    else:
        # Run a single game otherwise
        print("\nRunning a single game...")
        game = Game()
        game.run()
