from enum import Enum
import random
from gameConstants import *
import pygame
from pygame.locals import *
from draw import choose_vertex, choose_edge

# # Possible actions a player can take
# class Actions(Enum):
#     DRAW = 1
#     SETTLE = 2
#     CITY = 3
#     ROAD = 4
#     TRADE = 5

class Hexagon:
    def __init__(self, X, Y, resource, diceValue):
        self.X = X
        self.Y = Y
        self.resource = resource
        self.diceValue = diceValue
        self.center = None

    def deepCopy(self):
        return Hexagon(self.X, self.Y, self.resource, self.diceValue)

    def __repr__(self):
        return f"/{ResourceDict[self.resource]}{self.diceValue} ({self.X}, {self.Y})\\"

class Vertex:
    def __init__(self, X, Y):
        self.X = X
        self.Y = Y
        self.player = None
        self.isSettlement = False
        self.isCity = False
        self.canSettle = True

    def equivLocation(self, other):
        return other.X == self.X and other.Y == self.Y

    def isOccupied(self):
        return self.isSettlement or self.isCity

    def deepCopy(self):
        copy = Vertex(self.X, self.Y)
        copy.player = self.player
        copy.isSettlement = self.isSettlement
        copy.isCity = self.isCity
        copy.canSettle = self.canSettle
        return copy

    def settle(self, playerIndex):
        if self.isSettlement:
            raise Exception(f"Can't settle here - already settled by player {self.player}! At {self}")
        elif self.isCity:
            raise Exception(f"Can't settle here - already a city owned by player {self.player}! At {self}")

        self.isSettlement = True
        self.player = playerIndex
        self.canSettle = False

    def upgrade(self, playerIndex):
        if self.isCity:
            raise Exception(f"Player {self.player} already built a city here!")
        elif not self.isSettlement:
            raise Exception(f"Player {playerIndex} can't upgrade to a city without building a settlement first!")
        elif self.player != playerIndex:
            raise Exception(f"Player {playerIndex} is trying to upgrade Player {self.player}'s settlement!")
        
        self.isCity = True
        self.isSettlement = False

    def __repr__(self):
        coordinateString = f" ({self.X}, {self.Y})"

        if self.isOccupied():
            s = "S" if self.isSettlement else "C"
            return f"{s}{self.player}{coordinateString}"
        elif not self.canSettle:
            return f"Unsettlable{coordinateString}"
        else:
            return f"Unoccupied{coordinateString}"

class Edge:
    def __init__(self, X, Y, playerIndex=None):
        self.X = X
        self.Y = Y
        self.player = playerIndex

    def equivLocation(self, other):
        return other.X == self.X and other.Y == self.Y

    def isOccupied(self):
        return self.player is not None

    def deepCopy(self):
        return Edge(self.X, self.Y, self.player)
    
    def build(self, playerIndex):
        if self.player is not None:
            raise Exception(f"Player {self.player} already has a road here! At {self}")
        self.player = playerIndex

    def __repr__(self):
        coordinateString = f" ({self.X}, {self.Y})"
        return f"R{self.player}{coordinateString}" if self.isOccupied() else f"Unoccupied{coordinateString}"

class Tile:
    def __init__(self, resource, number):
        self.resource = resource
        self.number = number

BeginnerLayout = [
    [None, None, Tile(ResourceTypes.GRAIN, 9), None, None],
    [Tile(ResourceTypes.LUMBER, 11), Tile(ResourceTypes.WOOL, 12), Tile(ResourceTypes.BRICK, 5), Tile(ResourceTypes.WOOL, 10), Tile(ResourceTypes.GRAIN, 8)],
    [Tile(ResourceTypes.BRICK, 4), Tile(ResourceTypes.ORE, 6), Tile(ResourceTypes.GRAIN, 11), Tile(ResourceTypes.LUMBER, 4), Tile(ResourceTypes.ORE, 3)],
    [Tile(ResourceTypes.NOTHING, 7), Tile(ResourceTypes.LUMBER, 3), Tile(ResourceTypes.WOOL, 10), Tile(ResourceTypes.WOOL, 9), Tile(ResourceTypes.LUMBER, 6)],
    [None, Tile(ResourceTypes.BRICK, 8), Tile(ResourceTypes.ORE, 5), Tile(ResourceTypes.GRAIN, 2), None]
]

class Robber:
    def __init__(self, initial_hex):
        self.hex = initial_hex

    def move(self, new_hex):
        self.hex = new_hex

class Board:
    def __init__(self, layout=None):
        if layout is None:
            raise Exception("Must pass layout to Board.")
        self.layout = layout
        random.seed()
        
        self.numRows = len(layout)
        self.numCols = len(layout[0])
        self.hexagons = [[None for _ in range(self.numCols)] for _ in range(self.numRows)]
        self.edges = [[None for _ in range(self.numCols*2+2)] for _ in range(self.numRows*2+2)]
        self.vertices = [[None for _ in range(self.numCols*2+2)] for _ in range(self.numRows*2+2)]
        self.allSettlements = []
        self.allCities = []
        self.allRoads = []
        self.dieRollDict = {}
        self.resourceDict = {}
        self.draw = None

        for i in range(self.numRows):
            for j in range(self.numCols):
                tile = layout[j][i]
                if tile is None:
                    self.hexagons[i][j] = None
                else:
                    self.hexagons[i][j] = Hexagon(i, j, tile.resource, tile.number)
                    if tile.number in self.dieRollDict:
                        self.dieRollDict[tile.number].append(self.hexagons[i][j])
                    else:
                        self.dieRollDict[tile.number] = [self.hexagons[i][j]]

                    if tile.resource in self.resourceDict:
                        self.resourceDict[tile.resource].append(self.hexagons[i][j])
                    else:
                        self.resourceDict[tile.resource] = [self.hexagons[i][j]]

        for row in self.hexagons:
            for hexagon in row:
                if hexagon is None:
                    continue
                edgeLocations = self.getEdgeLocations(hexagon)
                vertexLocations = self.getVertexLocations(hexagon)
                for xLoc, yLoc in edgeLocations:
                    if self.edges[xLoc][yLoc] is None:
                        self.edges[xLoc][yLoc] = Edge(xLoc, yLoc)
                for xLoc, yLoc in vertexLocations:
                    if self.vertices[xLoc][yLoc] is None:
                        self.vertices[xLoc][yLoc] = Vertex(xLoc, yLoc)

        if self.numRows == 5 and self.numCols == 5:
            self.visualBoard = [
                [None, None, self.hexagons[0][1], self.hexagons[1][1], self.hexagons[2][0]],
                [None, self.hexagons[0][2], self.hexagons[1][2], self.hexagons[2][1], self.hexagons[3][1]],
                [self.hexagons[0][3], self.hexagons[1][3], self.hexagons[2][2], self.hexagons[3][2], self.hexagons[4][1]],
                [None, self.hexagons[1][4], self.hexagons[2][3], self.hexagons[3][3], self.hexagons[4][2]],
                [None, None, self.hexagons[2][4], self.hexagons[3][4], self.hexagons[4][3]]
            ]
        else:
            self.visualBoard = None
        self.tiles = [tile for row in self.visualBoard if row for tile in row if tile is not None]

        self.robber = Robber(self.get_desert_hex())

    def set_draw(self, draw):
        self.draw = draw

    def printData(self):
        print(self.hexagons)
        print(self.edges)
        print(self.vertices)

    def deepCopy(self):
        copy = Board(self.layout)
        copy.hexagons = [[h.deepCopy() if h is not None else None for h in row] for row in self.hexagons]
        copy.edges = [[e.deepCopy() if e is not None else None for e in row] for row in self.edges]
        copy.vertices = [[v.deepCopy() if v is not None else None for v in row] for row in self.vertices]
        copy.allSettlements = [s.deepCopy() for s in self.allSettlements]
        copy.allRoads = [r.deepCopy() for r in self.allRoads]
        return copy

    def applyAction(self, playerIndex, action):
        if action is None:
            return
        
        if action[0] == ACTIONS.SETTLE:
            actionVertex = action[1]
            vertex = self.getVertex(actionVertex.X, actionVertex.Y)
            vertex.settle(playerIndex)
            for neighborVertex in self.getNeighborVertices(vertex):
                neighborVertex.canSettle = False
            self.allSettlements.append(vertex)

        if action[0] == ACTIONS.ROAD:
            actionEdge = action[1]
            edge = self.getEdge(actionEdge.X, actionEdge.Y)
            edge.build(playerIndex)
            self.allRoads.append(edge)

        if action[0] == ACTIONS.CITY:
            actionVertex = action[1]
            vertex = self.getVertex(actionVertex.X, actionVertex.Y)
            vertex.upgrade(playerIndex)
            self.allCities.append(vertex)
            self.allSettlements = [
                s for s in self.allSettlements if not (s.X == vertex.X and s.Y == vertex.Y)
            ]

    def getResourcesFromDieRollForPlayer(self, playerIndex, dieRoll):
        hexagons = self.dieRollDict.get(dieRoll, [])
        resources = []
        for hexagon in hexagons:
            for vertex in self.getVertices(hexagon):
                if vertex.player == playerIndex:
                    if hexagon.resource != ResourceTypes.NOTHING:
                        resources.append(hexagon.resource)
                        if vertex.isCity:
                            resources.append(hexagon.resource)
        return resources

    def getRandomResourceHex(self, resource):
        return random.choice(self.resourceDict[resource])

    def getRandomVerticesForAllResources(self):
        resourcesForSettlement = [ResourceTypes.LUMBER, ResourceTypes.BRICK, ResourceTypes.WOOL, ResourceTypes.GRAIN]
        randomVerticesForBothPlayers = []
        for playerAgent in range(2):
            verticesForPlayer = []
            for resource in resourcesForSettlement:
                randomHex = self.getRandomResourceHex(resource)
                randomVertex = self.getRandomVertexOnHex(randomHex)
                self.applyAction(playerAgent, (ACTIONS.SETTLE, randomVertex))
                verticesForPlayer.append(randomVertex)
            randomVerticesForBothPlayers.append(verticesForPlayer)
        return randomVerticesForBothPlayers

    def getLumberHex(self, index):
        return {
            1: self.hexagons[0][1],
            2: self.hexagons[3][2],
            3: self.hexagons[1][3],
            4: self.hexagons[4][3]
        }.get(index, None)

    def getBrickHex(self, index):
        return {
            1: self.hexagons[2][1],
            2: self.hexagons[0][2],
            3: self.hexagons[1][4]
        }.get(index, None)

    def getRandomVertexOnHex(self, hex):
        vertices = self.getVertices(hex)
        vertex = None
        while vertex is None:
            index = random.randint(0, len(vertices)-1)
            vertex = vertices[index]
            if not vertex.canSettle:
                vertex = None
        return vertex

    def getRandomVerticesForSettlement(self):
        lumberHexes = [self.getLumberHex(i) for i in range(1, 5)]
        brickHexes = [self.getBrickHex(i) for i in range(1, 4)]
        
        random.shuffle(lumberHexes)
        random.shuffle(brickHexes)
        
        settlements = []
        
        for playerIndex in range(2):
            playerSettlements = []
            for hex in [lumberHexes[playerIndex], brickHexes[playerIndex]]:
                vertex = self.getRandomUnoccupiedVertexOnHex(hex)
                if vertex:
                    self.applyAction(playerIndex, (ACTIONS.SETTLE, vertex))
                    playerSettlements.append(vertex)
            settlements.append(playerSettlements)
        
        print("Settlements: ", settlements)
        return settlements

    def getRandomUnoccupiedVertexOnHex(self, hex):
        vertices = self.getVertices(hex)
        random.shuffle(vertices)
        for vertex in vertices:
            if vertex.canSettle:
                return vertex
        return None

    def getHumanVertexForSettlement(self):
        possibleVertices = []
        for i in range(len(self.vertices)):
            for j in range(len(self.vertices[i])):
                if self.vertices[i][j] != None and self.vertices[i][j].canSettle:
                    possibleVertices.append(self.vertices[i][j])
        
        return choose_vertex(possibleVertices, self.draw)

    def getRandomVertexForSettlement(self):
        vertex = None
        while vertex is None:
            vX = random.randint(0, len(self.vertices)-1)
            vY = random.randint(0, len(self.vertices[vX])-1)
            vertex = self.vertices[vX][vY]
            if vertex is not None and not vertex.canSettle:
                vertex = None
        return vertex

    def getHumanRoad(self, vertex):
        possibleEdges = self.getEdgesOfVertex(vertex)
        return choose_edge(possibleEdges, self, self.draw)

    def getRandomRoad(self, vertex):
        edges = self.getEdgesOfVertex(vertex)
        random.shuffle(edges)
        for edge in edges:
            if not edge.isOccupied():
                return edge
        return None

    def getEdge(self, x, y):
        return self.edges[x][y]

    def getVertex(self, x, y):
        return self.vertices[x][y]

    def getHex(self, x, y):
        return self.hexagons[x][y]

    def getNeighborHexes(self, hex):
        neighbors = []
        x, y = hex.X, hex.Y
        offset = -1 if x % 2 != 0 else 1

        directions = [
            (0, 1), (0, -1), (1, 0), (-1, 0),
            (1, offset), (-1, offset)
        ]

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(self.hexagons) and 0 <= ny < len(self.hexagons[nx]):
                neighbor = self.hexagons[nx][ny]
                if neighbor is not None:
                    neighbors.append(neighbor)

        return neighbors

    def getNeighborVerticesViaRoad(self, vertex, player):
        neighbors = []
        edgesOfVertex = self.getEdgesOfVertex(vertex)
        for edge in edgesOfVertex:
            if edge.player == player:
                vertexEnds = self.getVertexEnds(edge)
                for vertexEnd in vertexEnds:
                    if vertexEnd != vertex:
                        neighbors.append(vertexEnd)
        return neighbors

    def getNeighborVertices(self, vertex):
        neighbors = []
        x, y = vertex.X, vertex.Y
        offset = 1 if x % 2 == y % 2 else -1

        if y + 1 < len(self.vertices[0]):
            vertexOne = self.vertices[x][y+1]
            if vertexOne is not None:
                neighbors.append(vertexOne)
        if y > 0:
            vertexTwo = self.vertices[x][y-1]
            if vertexTwo is not None:
                neighbors.append(vertexTwo)
        if 0 <= x + offset < len(self.vertices):
            vertexThree = self.vertices[x+offset][y]
            if vertexThree is not None:
                neighbors.append(vertexThree)
        return neighbors

    def getVertexLocations(self, hex):
        x, y = hex.X, hex.Y
        offset = -(x % 2)
        return [
            (x, 2*y+offset), (x, 2*y+1+offset), (x, 2*y+2+offset),
            (x+1, 2*y+offset), (x+1, 2*y+1+offset), (x+1, 2*y+2+offset)
        ]

    def getEdgeLocations(self, hex):
        x, y = hex.X, hex.Y
        offset = -(x % 2)
        return [
            (2*x, 2*y+offset), (2*x, 2*y+1+offset),
            (2*x+1, 2*y+offset), (2*x+1, 2*y+2+offset),
            (2*x+2, 2*y+offset), (2*x+2, 2*y+1+offset)
        ]

    def getVertices(self, hex):
        x, y = hex.X, hex.Y
        offset = -(x % 2)
        return [
            self.vertices[x][2*y+offset],
            self.vertices[x][2*y+1+offset],
            self.vertices[x][2*y+2+offset],
            self.vertices[x+1][2*y+offset],
            self.vertices[x+1][2*y+1+offset],
            self.vertices[x+1][2*y+2+offset]
        ]

    def getEdges(self, hex):
        x, y = hex.X, hex.Y
        offset = -(x % 2)
        return [
            self.edges[2*x][2*y+offset],
            self.edges[2*x][2*y+1+offset],
            self.edges[2*x+1][2*y+offset],
            self.edges[2*x+1][2*y+2+offset],
            self.edges[2*x+2][2*y+offset],
            self.edges[2*x+2][2*y+1+offset]
        ]

    def getVertexEnds(self, edge):
        x, y = edge.X, edge.Y
        if x % 2 == 0:
            return (self.vertices[x//2][y], self.vertices[x//2][y+1])
        else:
            return (self.vertices[(x-1)//2][y], self.vertices[(x+1)//2][y])

    def getEdgesOfVertex(self, vertex):
        x, y = vertex.X, vertex.Y
        offset = 1 if x % 2 == y % 2 else -1
        edges = [
            self.edges[x*2][y-1],
            self.edges[x*2][y],
            self.edges[x*2+offset][y]
        ]
        return [edge for edge in edges if edge is not None]

    def getHexes(self, vertex):
        x, y = vertex.X, vertex.Y
        xOffset, yOffset = x % 2, y % 2
        vertexHexes = []

        if x < len(self.hexagons) and y // 2 < len(self.hexagons[x]):
            hexOne = self.hexagons[x][y // 2]
            if hexOne is not None:
                vertexHexes.append(hexOne)

        weirdX = x - 1 if (xOffset + yOffset) == 1 else x
        weirdY = y // 2 + (1 if yOffset == 1 else -1)
        if 0 <= weirdX < len(self.hexagons) and 0 <= weirdY < len(self.hexagons[0]):
            hexTwo = self.hexagons[weirdX][weirdY]
            if hexTwo is not None:
                vertexHexes.append(hexTwo)

        if 0 < x < len(self.hexagons) and y // 2 < len(self.hexagons[x]):
            hexThree = self.hexagons[x-1][y // 2]
            if hexThree is not None:
                vertexHexes.append(hexThree)
        
        return vertexHexes
    
    def calculateLongestRoad(self, playerIndex):
        def dfs(start, visited=None, length=0):
            if visited is None:
                visited = set()
            if start in visited:
                return length
            
            visited.add(start)
            max_length = length
            
            for neighbor in self.getConnectedVertices(start, playerIndex):
                if neighbor not in visited:
                    max_length = max(max_length, dfs(neighbor, visited.copy(), length + 1))
            
            return max_length
        
        max_road_length = 0
        for road in [road for road in self.allRoads if road.player == playerIndex]:
            start_vertex, end_vertex = self.getVertexEnds(road)
            max_road_length = max(max_road_length, dfs(start_vertex), dfs(end_vertex))
        
        return max_road_length
    
    def getConnectedVertices(self, vertex, playerIndex):
        connected = []
        for edge in self.getEdgesOfVertex(vertex):
            if edge.player == playerIndex:
                start, end = self.getVertexEnds(edge)
                connected.append(end if start == vertex else start)
        return connected
    
    def get_desert_hex(self):
        for row in self.hexagons:
            for hex in row:
                if hex is not None and hex.resource == ResourceTypes.NOTHING:
                    return hex
        raise Exception("No desert hex found on the board")

    def get_valid_robber_hexes(self):
        return [hex for row in self.hexagons for hex in row if hex is not None and hex != self.robber.hex and hex.resource != ResourceTypes.NOTHING]

    def move_robber(self, new_hex):
        if new_hex not in self.get_valid_robber_hexes():
            raise ValueError("Invalid hex for robber placement")
        self.robber.move(new_hex)

    def canBuildRoadAt(self, playerIndex, row, col):
        edge = self.edges[row][col]
        if edge is None or edge.isOccupied():
            return False

        # Check if the road is connected to an existing road or settlement/city of the player
        connected = False
        vertex_ends = self.getVertexEnds(edge)
        
        for vertex in vertex_ends:
            # Check if the player has a settlement or city at this vertex
            if vertex.player == playerIndex:
                connected = True
                break
            
            # Check if the player has a connected road
            for neighbor_edge in self.getEdgesOfVertex(vertex):
                if neighbor_edge.player == playerIndex:
                    connected = True
                    break
            
            if connected:
                break

        return connected