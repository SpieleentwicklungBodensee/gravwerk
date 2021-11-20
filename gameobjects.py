from globalconst import *

class GameObject(object):
    def __init__(self, x, y, tile = None):
        self.x = x
        self.y = y
        self.tile = tile

        self.spawnx = x
        self.spawny = y

        self.xdir = 0
        self.ydir = 0
        self.facedir = LEFT

        self.speed = 1

        self.width = TILE_W
        self.height = TILE_H

    def getSprite(self):
        return self.tile

    def moveLeft(self):
        self.xdir = -1

    def moveRight(self):
        self.xdir = 1

    def moveUp(self):
        self.ydir = -1

    def moveDown(self):
        self.ydir = 1


    def stopLeft(self):
        if self.xdir < 0:
            self.xdir = 0

    def stopRight(self):
        if self.xdir > 0:
            self.xdir = 0

    def stopUp(self):
        if self.ydir < 0:
            self.ydir = 0

    def stopDown(self):
        if self.ydir > 0:
            self.ydir = 0


    def update(self, gamestate):
        pass

    def draw(self, screen, tiles, gamestate):
        pass

    def interact(self, gamestate, release=False):
        pass

    def collides(self, game_object):
        if self.x < game_object.x + game_object.width and \
                self.x + self.width > game_object.x and \
                self.y < game_object.y + game_object.height and \
                self.y + self.height > game_object.y:
            #debugList.append([self.x, self.y])
            #debugList.append([game_object.x, game_object.y])

            return True
        return False
