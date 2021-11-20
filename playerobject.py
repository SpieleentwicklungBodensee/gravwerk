from globalconst import *
from gameobjects import *
import math
import verlet

class PlayerObject(GameObject):
    def __init__(self, x, y, tile=None):
        GameObject.__init__(self, x, y, tile)

    def update(self, gamestate):
        self.rotation = math.fmod(self.rotation + self.rotationDir * ROTATION_CHANGE, 360)
        r = -math.radians(self.rotation) + 0.5 * math.pi
        accel = [math.cos(r) * self.ydir * 50, math.sin(r) * self.ydir * 50]

        gravity = 10.0
        a = [accel[0], accel[1] + gravity]
        pos = [self.x, self.y]
        verlet.integrate1(pos, self.v, a, 1 / FPS)
        verlet.integrate2(pos, self.v, a, 1 / FPS)
        self.x, self.y = pos

