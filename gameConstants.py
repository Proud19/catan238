from enum import Enum
from collections import Counter

GRAPHICS = True
VERBOSE = True
DEBUG = False
AUTORUN = True

def getColorForPlayer(player):
    return {
      0: "red",
      1: "blue",
      2: "black",
      3: "brown"
    }.get(player, None)

VICTORY_POINTS_TO_WIN = 10
SETTLEMENT_VICTORY_POINTS = 1
CITY_VICTORY_POINTS = SETTLEMENT_VICTORY_POINTS + 1

NUM_INITIAL_SETTLEMENTS = 2
TOTAL_NUM_AGENTS = 13
CUTOFF_TURNS = 600

MAX_ROADS = 15
MAX_SETTLEMENTS = 5
MAX_CITIES = 4

LONGEST_ROAD_LENGTH = 5
LONGEST_ROAD_POINTS = 2

LARGEST_ARMY_REQUIREMENT = 3
LARGEST_ARMY_POINTS = 2

DEFAULT_PLAYER_ARRAY = [4,0]

class ACTIONS(Enum):
    SETTLE = 1
    CITY = 2
    ROAD = 3
    TRADE = 4
    PASS = 5
    BUY_DEV_CARD = 6
    PLAY_KNIGHT = 7
    PLAY_DEV_CARD = 8

class ResourceTypes(Enum):
    BRICK = 1
    WOOL = 2
    ORE = 3
    GRAIN = 4
    LUMBER = 5
    NOTHING = 6

class AGENT(Enum):
    PLAYER_AGENT = 1
    DICE_AGENT = 2

BANK_RESOURCES = {
    ResourceTypes.BRICK: 19,
    ResourceTypes.WOOL: 19,
    ResourceTypes.ORE: 19,
    ResourceTypes.GRAIN: 19,
    ResourceTypes.LUMBER: 19
}

# Resource costs of a Road, a Settlement, and a City
ROAD_COST = Counter({ResourceTypes.BRICK: 1, ResourceTypes.LUMBER: 1})
SETTLEMENT_COST = Counter({ResourceTypes.LUMBER: 1, ResourceTypes.BRICK: 1, ResourceTypes.WOOL: 1, ResourceTypes.GRAIN: 1})
CITY_COST = Counter({ResourceTypes.GRAIN: 2, ResourceTypes.ORE: 3})
DEV_CARD_COST = Counter({ResourceTypes.GRAIN: 1, ResourceTypes.WOOL: 1, ResourceTypes.ORE: 1})

class DevCardTypes(Enum):
    KNIGHT = 1
    VICTORY_POINT = 2
    ROAD_BUILDING = 3
    YEAR_OF_PLENTY = 4
    MONOPOLY = 5

DEV_CARD_DECK = [DevCardTypes.KNIGHT] * 14 + [DevCardTypes.VICTORY_POINT] * 5 + \
                [DevCardTypes.ROAD_BUILDING] * 2 + [DevCardTypes.YEAR_OF_PLENTY] * 2 + \
                [DevCardTypes.MONOPOLY] * 2

# A dictionary from resource type (enum, above) to string representation
# so we can print out the resource type easily
ResourceDict = {ResourceTypes.GRAIN:"G", ResourceTypes.WOOL:"W", ResourceTypes.ORE:"O", ResourceTypes.LUMBER:"L", ResourceTypes.BRICK:"B", ResourceTypes.NOTHING:"N"}
NUM_PLAYERS = 2
NUM_ITERATIONS = 4
DEPTH = 2