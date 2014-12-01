from collections import Counter
import copy
from gameConstants import *
from random import choice, randint


"""
EVALUATION FUNCTIONS
---------------------
"""
# EVAL FUNCTION: THE BUILDER
# --------------------------
# 5 utility points per settlement, 1 per road
def builderEvalFn(currentGameState, currentPlayerIndex):
  currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
  return 5 * len(currentPlayer.settlements) + len(currentPlayer.roads)

# EVAL FUNCTION: DEFAULT AGENT
# --------------------------
# 3 utility points per settlement, 1 per road
def defaultEvalFn(currentGameState, currentPlayerIndex):
  currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
  return 5 * len(currentPlayer.settlements) + len(currentPlayer.roads)

# EVAL FUNCTION: RESOURCE AGENT
# --------------------------
# 1 utility points per resource
def resourceEvalFn(currentGameState, currentPlayerIndex):
  currentPlayer = currentGameState.playerAgents[currentPlayerIndex]
  return sum(currentPlayer.resources.values())


"""
GAME AGENTS
---------------------
"""

class DiceAgent:
  """
  Class: DiceAgent
  ---------------------
  DiceAgent represents the random agent responsible for the
  roll of the dice for resources each turn.  It generates a
  number from 1-12 with the correct probability distribution
  corresponding to rolling 2 6-sided dice.
  ---------------------
  """

  def __init__(self):
    self.agentType = AGENT.DICE_AGENT
    self.NUM_DICE_SIDES = 6

  def rollDice(self):
    """
    Method: rollDice
    ----------------------
    Parameters: NA
    Returns: an integer representing the result of a random
      roll of 2 6-sided dice
    ----------------------
    """
    return randint(1,NUM_DICE_SIDES) + randint(1,NUM_DICE_SIDES)

  def getRollDistribution(self):
    """
    Method: getRollDistribution
    -----------------------------
    Parameters: NA
    Returns: a list of (ROLL, PROBABILITY) tuples containing
      all the possible rolls and the probabilities that they will be rolled.
    -----------------------------
    """
    # Tally up all the possible roll combinations
    # and the number of dice roll combinations per dice total
    totalRolls = 0
    rollCounter = Counter()
    for dice1 in range(1, NUM_DICE_SIDES + 1):
      for dice2 in range(1, NUM_DICE_SIDES + 1):
        rollCounter[dice1 + dice2] += 1
        totalRolls += 1

    # Return the list of probability tuples
    return [(roll, rollCounter[roll] / float(totalRolls)) for roll in rollCounter]




  def deepCopy(self):
    return DiceAgent()


class PlayerAgent:
  """
  Class: PlayerAgent
  ---------------------
  PlayerAgent defines a generic player agent in Settlers consisting of a name,
  player index, max depth, and player stats/game-specific information like number
  of victory points, lists of all roads, settlements, and cities owned by the
  player, and a counter of resources that the player has.

  Instance Variables:
  ---
  agentType = the type of game agent (PLAYER_AGENT)
  evaluationFunction = the eval function to use in the minimax algorithm
  name = a string containing the name of the player
  agentIndex = the player index
  victoryPoints = the number of victory points the player has
  depth = the maximum depth to recurse in the minimax tree
  roads = a list of Edge objects representing the roads a player has
  settlements = a list of Vertex objects representing the settlements a player has
  cities = a list of Vertex objects representing the cities a player has
  resources = a Counter containing the count of each resource type (in ResourceTypes) the player has
  ---------------------
  """

  def __init__(self, name, agentIndex, evalFn = defaultEvalFn):
    self.agentType = AGENT.PLAYER_AGENT
    self.evaluationFunction = evalFn
    self.name = name
    self.agentIndex = agentIndex
    self.victoryPoints = 0
    self.depth = 3

    # List of Edges
    self.roads = []

    # List of Vertices
    self.settlements = []

    # List of Cities owned
    self.cities = []

    # Counter of resources initialized to zero
    self.resources = Counter({ResourceTypes.WOOL: 0, 
      ResourceTypes.BRICK: 0, 
      ResourceTypes.ORE: 0, 
      ResourceTypes.GRAIN: 0, 
      ResourceTypes.LUMBER: 0})
    
  def __repr__(self):
    """
    Method: __repr__
    ---------------------
    Parameters: NA
    Returns:the player's name

    A string representation of the given PlayerAgent.
    ---------------------
    """
    s = "---------- " + self.name + " ----------\n"
    s += "Victory points: " + str(self.victoryPoints) + "\n"
    s += "Resources: " + str(self.resources) + "\n"
    s += "Settlements: " + str(self.settlements) + "\n"
    s += "Roads: " + str(self.roads) + "\n"
    s += "Cities: " + str(self.cities) + "\n"
    s += "--------------------------------------------\n"
    return s


  def canSettle(self):
    """
    Method: canSettle
    ---------------------
    Parameters: NA
    Returns: True/False whether or not this PlayerAgent has enough
      resources to build a new settlement (based on the SETTLEMENT_COST constant)
    ---------------------
    """
    modifiedResources = copy.deepcopy(self.resources)
    modifiedResources.subtract(SETTLEMENT_COST)

    # If any resource counts dip below 0, we don't have enough
    for resourceType in modifiedResources:
      if modifiedResources[resourceType] < 0:
        return False

    return True

  def canBuildCity(self):
    """
    Method: canBuildCity
    ----------------------
    Parameters: NA
    Returns: True/False whether or not this PlayerAgent has enough
      resources to build a new city (based on the CITY_COST constant)
    ----------------------
    """
    modifiedResources = copy.deepcopy(self.resources)
    modifiedResources.subtract(CITY_COST)

    # If any resource counts dip below 0, we don't have enough
    for resourceType in modifiedResources:
      if modifiedResources[resourceType] < 0:
        return False

    return True

  def canBuildRoad(self):
    """
    Method: canBuildRoad
    ----------------------
    Parameters: NA
    Returns: True/False whether or not this PlayerAgent has enough
      resources to build a new road (based on the ROAD_COST constant)
    ----------------------
    """
    modifiedResources = copy.deepcopy(self.resources)
    modifiedResources.subtract(ROAD_COST)

    # If any resource counts dip below 0, we don't have enough
    for resourceType in modifiedResources:
      if modifiedResources[resourceType] < 0:
        return False

    return True

  def deepCopy(self, board):
    """
    Method: deepCopy
    ----------------------
    Parameters:
      board - the current state of the board (an instance of Board)
    Returns: a deep copy of this instance of PlayerAgent, including full
      copies of all instance Variables
    ----------------------
    """
    newCopy = PlayerAgent(self.name, self.agentIndex)
    newCopy.victoryPoints = self.victoryPoints
    newCopy.depth = self.depth
    newCopy.roads = [board.getEdge(road.X, road.Y) for road in self.roads]
    newCopy.settlements = [board.getVertex(settlement.X, settlement.Y) for settlement in self.settlements]
    newCopy.resources = copy.deepcopy(self.resources)
    return newCopy

  def applyAction(self, action):
    """
    Method: applyAction
    -----------------------
    Parameters:
      action - the action tuple (ACTION, LOCATION) to applyAction
    Returns: NA

    Applies the given action tuple to the current player.  Does this
    by deducting resources appropriately and adding to the player's
    lists of roads, settlements, and cities.
    -----------------------
    """
    if action is None:
      return

    # Settling
    if action[0] is ACTIONS.SETTLE:
      self.settlements.append(action[1])
      if not self.canSettle():
        raise Exception("Player " + str(self.agentIndex) + " doesn't have enough resources to build a settlement!")
      self.resources.subtract(SETTLEMENT_COST)
      self.victoryPoints += SETTLEMENT_VICTORY_POINTS

    # Building a road
    if action[0] is ACTIONS.ROAD:
      self.roads.append(action[1])
      if not self.canBuildRoad():
        raise Exception("Player " + str(self.agentIndex) + " doesn't have enough resources to build a road!")
      self.resources.subtract(ROAD_COST)

    # Building a city
    if action[0] is ACTIONS.CITY:
      self.cities.append(action[1])
      if not self.canBuildCity():
        raise Exception("Player " + str(self.agentIndex) + " doesn't have enough resources to build a city!")
      self.resources.subtract(CITY_COST)
      self.victoryPoints += CITY_VICTORY_POINTS

  def updateResources(self, diceRoll, board):
    """
    Method: updateResources
    -----------------------------
    Parameters:
      diceRoll - the sum of the two dice Rolled
      board - a Board object representing the current board state
    Returns: a Counter containing the number of each resource gained

    Takes the current dice roll and board setup, and awards
    the current player resources depending on built settlements on the board.
    Returns the count of each resource that the player gained.
    -----------------------------
    """
    newResources = Counter(board.getResourcesFromDieRollForPlayer(self.agentIndex, diceRoll))
    self.resources += newResources
    return newResources

  def collectInitialResources(self, board):
    """
    Method: collectInitialResources
    --------------------------------
    Parameters:
      board - a Board object representing the current board state

    Returns: NA

    Takes the current board setup and awards the current player
    resources for each of his/her current settlements.  For example,
    if the player had a settlement bordering BRICK and ORE and another
    one bordering BRICK, this player would receive 2 BRICK and 1 ORE.
    --------------------------------
    """
    # Get resources for each settlement
    for settlement in self.settlements:

      # Find all tiles bordering this settlement and
      # take 1 resource of each of the surrounding tile types
      borderingTiles = board.getHexes(settlement)
      for borderingTile in borderingTiles:
        if borderingTile.resource is not ResourceTypes.NOTHING:
          self.resources[borderingTile.resource] += 1

  def hasWon(self):
    """
    Method: hasWon
    -----------------------------
    Parameters: NA
    Returns: True/False whether or not the curernt player
      has won the game (AKA met or exceeded VICTORY_POINTS_TO_WIN)
    -----------------------------
    """
    return self.victoryPoints >= VICTORY_POINTS_TO_WIN

  def getAction(self, state):
    """
    Method: getAction
    -----------------------------
    Parameters:
      state - a GameState object containing information about the current state of the game
    Returns: an action tuple (ACTION, LOCATION) of the action this player should take
    
    Note: must be overridden by a subclass
    -----------------------------
    """
    raise Exception("Cannot get action for superclass - must implement getAction in PlayerAgent subclass!")


class PlayerAgentExpectiminimax(PlayerAgent):
  """
  Class: PlayerAgentExpectiminimax
  --------------------------------
  A subclass of PlayerAgent that uses Expectiminimax search
  to determine what action it should take.  This assumes
  that opponents are following a min adversarial policy
  (and that the dice follow a random policy).
  --------------------------------
  """

  def __init__(self, name, agentIndex, evalFn = defaultEvalFn):
    PlayerAgent.__init__(self, name, agentIndex, evalFn)

  def getAction(self, state):
    """
    Method: getAction
    ------------------------
    Parameters:
      state - a GameState object containing information about the current state of the game
    Returns: an action tuple (ACTION, LOCATION) of the action this player should take

    Returns the best possible action that the current player can take.  Implements
    The expectiminimax algorithm for determining the best possible move based
    on the adversarial min policies of the other Agents in the game and the random policy of
    the dice roll.  Returns None if no action can be taken, or an action tuple
    otherwise - e.g. (ACTIONS.SETTLE, *corresponding Vertex object where settlement is*).
    ------------------------
    """
    # A function that recursively calculates and returns the utility for self
    # of the given game state with the given depth on the given player's turn
    def recurse(state, currDepth, playerIndex):
      # TERMINAL CASES
      # ---------------------
      
      # If the player won
      if state.gameOver() == playerIndex:
        return float('inf')

      # or lost
      elif state.gameOver() > -1:
        return float('-inf')

      # If the max depth has been reached, call the eval function
      elif currDepth is 0:
        return self.evaluationFunction(state, self.agentIndex)

      possibleActions = state.getLegalActions(playerIndex)

      # If there are no possible actions (must pass)
      if len(possibleActions) is 0:
        return self.evaluationFunction(state, self.agentIndex)

      # RECURSIVE CASE
      # ----------------------

      # Get dice roll probabilities to calculate expected utility
      rollProbabilities = agent.getRollDistribution()

      # New depth (depth - 1 for last player, otherwise depth)
      # newPlayerIndex goes through 0, 1,...numAgents - 1 (looping around)
      newDepth = currDepth - 1 if playerIndex is not self.agentIndex else currDepth
      newPlayerIndex = (playerIndex + 1) % state.getNumPlayerAgents()

      # Parallel lists of values and their corresponding actions
      vals = []
      actions = []

      # Try all possible actions
      for currAction in possibleActions:
        currVal = 0

        # For each action, the utility is the sum of the weighted
        # utilities for all possible dice rolls (we need to add all weighted
        # utilities together to get the expected utility)
        for probabilityTuple in rollProbabilities:
          roll, probability = probabilityTuple
          state = GameState(state)
          state.updatePlayerResourcesForDiceRoll(roll)
          value = recurse(state.generateSuccessor(playerIndex, currAction), newDepth, newPlayerIndex)

          currVal += probability * value

        vals.append(currVal)
        actions.append(currAction)

      # Maximize/minimize
      if playerIndex is self.agentIndex:
        return (max(vals), actions[vals.index(max(vals))])
      return (min(vals), actions[vals.index(min(vals))])      

    # Call our recursive function

    # TERMINAL CASES
    # ---------------------
    
    # If the player won
    if state.gameOver() is self.agentIndex:
      return (float('inf'), None)

    # or lost
    elif state.gameOver() > -1:
      return (float('-inf'), None)

    # If the max depth has been reached, call the eval function
    elif self.depth is 0:
      return (self.evaluationFunction(state, self.agentIndex), None)

    possibleActions = state.getLegalActions(self.agentIndex)

    # If there are no possible actions (must pass)
    if len(possibleActions) is 0:
      return (self.evaluationFunction(state, self.agentIndex), None)

    # RECURSIVE CASE
    # ----------------------

    # Parallel lists of values and their corresponding actions
    vals = []
    actions = []

    newPlayerIndex = (self.agentIndex + 1) % state.getNumPlayerAgents()

    # Try all possible actions
    for currAction in possibleActions:
      value = recurse(state.generateSuccessor(newPlayerIndex, currAction), self.depth, newPlayerIndex)
      vals.append(value)
      actions.append(currAction)

    return (max(vals), actions[vals.index(max(vals))])


class PlayerAgentRandom(PlayerAgent):
  """
  Class: PlayerAgentRandom
  --------------------------
  A subclass of PlayerAgent that randomly determines
  what action it takes (uniformly random).
  --------------------------
  """

  def getAction(self, state):
    """
    Method: getAction
    ------------------------
    Parameters:
      state - a GameState object containing information about the current state of the game
    Returns: an action tuple (ACTION, LOCATION) of the action this player should take

    Returns a random action that this player should take.  This action is
    chosen uniformly randomly from the list of all available actions.
    ------------------------
    """
    # If the game is over...
    if state.gameOver() > -1:
      return None

    possibleActions = state.getLegalActions(playerIndex)

    # If there are no possible actions (must pass)
    if len(possibleActions) is 0:
      return None

    # Otherwise pick a random action
    return choice(possibleActions)


class PlayerAgentExpectimax(PlayerAgent):
  """
  Class: PlayerAgentExpectimax
  -------------------------------
  A subclass of PlayerAgent that uses Expectimax search
  to determine what action to take.  This assumes that
  opponents are following a uniformly random policy
  to determine their actions (and that the dice roll
  follow a uniformly random policy).
  -------------------------------
  """
  def __init__(self, name, agentIndex, evalFn = defaultEvalFn):
    PlayerAgent.__init__(self, name, agentIndex, evalFn)

  def getAction(self, state):
    """
    Method: getAction
    ------------------------
    Parameters:
      state - a GameState object containing information about the current state of the game
    Returns: an action tuple (ACTION, LOCATION) of the action this player should take
    
    Returns the best possible action that the current player can take.  Implements
    The expectimax algorithm for determining the best possible move based
    on the random policies of the other PlayerAgents in the game and the random policy of
    the dice roll.  Returns None if no action can be taken, or an action tuple
    otherwise - e.g. (ACTIONS.SETTLE, *corresponding Vertex object where settlement is*).
    ------------------------
    """
    raise Exception("Not implemented yet")
    