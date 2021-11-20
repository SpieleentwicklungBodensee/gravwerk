from globalconst import *
from gameobjects import *
import math

class PlayerObject(GameObject):
    def __init__(self, x, y, tile=None):
        GameObject.__init__(self, x, y, tile)

    def update(self, gamestate):
        self.x += self.xdir * self.speed
        self.y += self.ydir * self.speed

        self.rotation = math.fmod(self.rotation + self.rotationDir * ROTATION_CHANGE, 360)

