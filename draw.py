import pygame
from gameConstants import getColorForPlayer, DEBUG, VERBOSE, ResourceTypes, ACTIONS
from pygame.locals import *
import math
import sys

class Draw:
    def __init__(self, tiles, screen, board):
        self.screen = screen
        self.tiles = tiles
        self.board = board
        self.vertexOffsets = self.verticesInit()
        self.dimenInit()
        self.imageInit()
        self.pieceInit()
        self.hex_centers = {}

    def findSImage(self, color, settlement, city):
        if settlement:
            return {
                "red": self.redS,
                "blue": self.blueS,
                "black": self.blackS,
                "brown": self.brownS
            }.get(color)
        elif city:
            return {
                "red": self.redC,
                "blue": self.blueC,
                "black": self.blackC,
                "brown": self.brownC
            }.get(color)
        return None

    def dimenInit(self):
        self.d = 70  # distance from center to edge of hex
        self.hexWidth = self.d * 1.4  # equal to sqrt(3)/2 * height
        self.hexHeight = self.d * 1.6
        self.rowHeight = self.hexHeight * 0.75
        self.numR = 11  # radius of number oval
        self.width = 1020
        self.height = 800
        self.yOffset = self.height / 4
        self.xOffset = self.width / 2

    def imageInit(self):
        self.desert = pygame.image.load('resources/desert.gif').convert_alpha()
        self.field = pygame.image.load('resources/field.gif').convert_alpha()
        self.forest = pygame.image.load('resources/forest.gif').convert_alpha()
        self.hill = pygame.image.load('resources/hill.gif').convert_alpha()
        self.mountain = pygame.image.load('resources/mountain.gif').convert_alpha()
        self.pasture = pygame.image.load('resources/pasture.gif').convert_alpha()

    def pieceInit(self):
        self.redS = pygame.image.load('resources/redS.gif').convert_alpha()
        self.blueS = pygame.image.load('resources/blueS.gif').convert_alpha()
        self.blackS = pygame.image.load('resources/blackS.gif').convert_alpha()
        self.brownS = pygame.image.load('resources/brownS.gif').convert_alpha()
        self.redC = pygame.image.load('resources/redC.gif').convert_alpha()
        self.blueC = pygame.image.load('resources/blueC.gif').convert_alpha()
        self.blackC = pygame.image.load('resources/blackC.gif').convert_alpha()
        self.brownC = pygame.image.load('resources/brownC.gif').convert_alpha()

    def verticesInit(self):
        return (
            [None, None, (3, 0), (2, 0.25), (2, 0.75), (1, 1), (1, 1.5), (0, 1.75), (0, 2.25), None, None],
            [None, (5, 0), (4, 0.25), (4, 0.75), (3, 1), (3, 1.5), (2, 1.75), (2, 2.25), (1, 2.5), (1, 3), None],
            [(7, 0), (6, 0.25), (6, 0.75), (5, 1), (5, 1.5), (4, 1.75), (4, 2.25), (3, 2.5), (3, 3), (2, 3.25), (2, 3.75)],
            [(8, 0.25), (8, 0.75), (7, 1), (7, 1.5), (6, 1.75), (6, 2.25), (5, 2.5), (5, 3), (4, 3.25), (4, 3.75), (3, 4)],
            [None, (9, 1), (9, 1.5), (8, 1.75), (8, 2.25), (7, 2.5), (7, 3), (6, 3.25), (6, 3.75), (5, 4), None],
            [None, None, (10, 1.75), (10, 2.25), (9, 2.5), (9, 3), (8, 3.25), (8, 3.75), (7, 4), None, None]
        )

    def drawBoard(self):
        cY = self.yOffset
        index = 0
        tilesInRow = [3, 4, 5, 4, 3]
        for row in tilesInRow:
            cX = self.xOffset - self.hexWidth / 2 * row
            self.drawRow(row, index, cX, cY)
            index += row
            cY += self.rowHeight
        
        if hasattr(self.board, 'robber') and self.board.robber.hex is not None:
            self.drawRobber(self.board.robber.hex)

    def drawRow(self, numTiles, index, cX, cY):
        for tile in range(numTiles):
            cX += self.hexWidth
            hexagon = self.tiles[index]
            image = self.getImageForResource(hexagon.resource)
            self.screen.blit(image, (cX - image.get_width()//2, cY - image.get_height()//2))
            self.drawNum(cX, cY, hexagon.diceValue)
            self.hex_centers[hexagon] = (cX, cY)
            index += 1

    def drawNum(self, xOffset, yOffset, num):
        color = (255, 0, 0) if num in (8, 6) else (0, 0, 0)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(xOffset), int(yOffset)), self.numR)
        font = pygame.font.Font(None, 36)
        text = font.render(str(num), True, color)
        text_rect = text.get_rect(center=(xOffset, yOffset))
        self.screen.blit(text, text_rect)

    def drawSettlements(self, vertices):
        for vertex in vertices:
            if vertex.isSettlement or vertex.isCity:
                color = getColorForPlayer(vertex.player)
                image = self.findSImage(color, vertex.isSettlement, vertex.isCity)
                if image:
                    xPos, yPos = self.calculateVertexPosition(vertex)
                    self.screen.blit(image, (xPos - image.get_width()//2, yPos - image.get_height()//2))

    def drawCities(self, vertices):
        self.drawSettlements(vertices)

    def calculateVertexPosition(self, vertex):
        xOffset, yOffset = self.vertexOffsets[vertex.X][vertex.Y]
        xPos = (self.xOffset
                - self.hexWidth / 2 * 4
                + self.hexWidth / 2 * xOffset)
        yPos = (self.yOffset - self.hexHeight * 0.5
                + self.hexHeight * yOffset)
        return (xPos, yPos)

    def drawRoads(self, roads, board):
        for road in roads:
            if DEBUG and VERBOSE:
                print("Drawing road: ", road)
            start, end = board.getVertexEnds(road)
            ox, oy = self.calculateVertexPosition(start)
            ex, ey = self.calculateVertexPosition(end)
            color = getColorForPlayer(road.player)
            pygame.draw.line(self.screen, pygame.Color(color), (ox, oy), (ex, ey), 5)

    def drawTitle(self):
        self.screen.blit(self.title, (120 - self.title.get_width()//2, 70 - self.title.get_height()//2))

    def getImageForResource(self, resource):
        return {
            ResourceTypes.GRAIN: self.field,
            ResourceTypes.WOOL: self.pasture,
            ResourceTypes.ORE: self.mountain,
            ResourceTypes.LUMBER: self.forest,
            ResourceTypes.BRICK: self.hill,
            ResourceTypes.NOTHING: self.desert
        }.get(resource, None)

    def drawBG(self):
        self.screen.fill((135, 206, 235))  # Light sky blue

    def drawRobber(self, robber_hex):
        if robber_hex is None or robber_hex not in self.hex_centers:
            return

        center_x, center_y = self.hex_centers[robber_hex]
        
        circle_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
        circle_surface.fill((0, 0, 0, 0))  # Transparent fill

        # Draw a grey circle
        pygame.draw.circle(circle_surface, (128, 128, 128, 200), (15, 15), 15)  # Grey color with some transparency

        circle_rect = circle_surface.get_rect(center=(center_x, center_y))
        self.screen.blit(circle_surface, circle_rect)

def choose_edge(legal_edges, gameState, draw):
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
                    ox, oy = draw.calculateVertexPosition(start)
                    ex, ey = draw.calculateVertexPosition(end)
                    if DEBUG and VERBOSE:
                        print("Args: ")
                        print(x, y, ox, oy, ex, ey)
                    dist = point_to_line_distance(x, y, ox, oy, ex, ey)
                    if dist < threshold:
                        selected_edge = edge
                        if VERBOSE and DEBUG:
                            print(f"Selected edge: {edge}")
                        return selected_edge

def choose_vertex(legal_vertices, draw, action=ACTIONS.SETTLE):
    if action.name == "CITY":
        print("Choose one city to build by clicking the GUI.")
    elif action.name == "SETTLE":
        print("Choose one settlement to build by clicking the GUI.")
    
    selected_vertex = None
    threshold = 10  # Distance threshold

    while selected_vertex is None:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == MOUSEBUTTONDOWN:
                x, y = event.pos
                for vertex in legal_vertices:
                    xPos, yPos = draw.calculateVertexPosition(vertex)
                    dist = point_to_point_distance(x, y, xPos, yPos)
                    if dist < threshold:
                        selected_vertex = vertex
                        if VERBOSE and DEBUG:
                            print(f"Selected vertex: {vertex}")
                        return selected_vertex
    
def choose_hex(legal_hexes, draw):
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
                    xPos, yPos = draw.hex_centers[hex]

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