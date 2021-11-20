from globalconst import *
from gameobjects import *
import math

class PlayerObject(GameObject):
    def __init__(self, x, y, tile=None):
        GameObject.__init__(self, x, y, tile)

    def update(self, gamestate):
        self.x += self.xdir * self.speed
        self.y += self.ydir * self.speed

        self.rotationSpeed += self.rotationDir * ROTATION_CHANGE
        if self.rotationSpeed > MAX_ROTATION_SPEED:
            self.rotationSpeed = MAX_ROTATION_SPEED
        elif self.rotationSpeed < -MAX_ROTATION_SPEED:
            self.rotationSpeed = -MAX_ROTATION_SPEED
        self.rotation = math.fmod(self.rotation + self.rotationSpeed, 360)

