from globalconst import *
import math

class GameObject(object):
    def __init__(self, x, y, tile = None):
        self.x = x
        self.y = y
        self.rotation = 0

        self.tile = tile

        self.spawnx = x
        self.spawny = y

        self.xdir = 0
        self.ydir = 0
        self.facedir = LEFT

        self.speed = 1

        self.v = [0.0, 0.0]

        self.width = TILE_W
        self.height = TILE_H

        self.rotationDir = 0
        self.rotationSpeed = 0

    def getSprite(self):
        return self.tile

    def move(self, xdir = None, ydir = None):
        if xdir is not None:
            self.xdir = xdir
        if ydir is not None:
            self.ydir = ydir

    def stop(self, left, right, up, down):
        if left and self.xdir < 0:
            self.xdir = 0
        if right and self.xdir > 0:
            self.xdir = 0
        if up and self.ydir < 0:
            self.ydir = 0
        if down and self.ydir > 0:
            self.ydir = 0

    def rotate(self, direction):
        self.rotationDir = direction



    def update(self, gamestate):
        pass

    def updateLocal(self,gamestate):
        pass

    def reset(self):
        self.x = self.spawnx
        self.y = self.spawny
        self.v = [0.0, 0.0]

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
