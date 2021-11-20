from globalconst import *
from gameobjects import *
from particles import *
import math
import verlet

class PlayerObject(GameObject):
    def __init__(self, x, y, tile=None, particleColor = (255,128,0)):
        GameObject.__init__(self, x, y, tile)
        self.particleColor = particleColor
        self.accel = [0, 0]

    def update(self, gamestate):
        self.rotation = math.fmod(self.rotation + self.rotationDir * ROTATION_CHANGE, 360)
        r = -math.radians(self.rotation) + 0.5 * math.pi
        self.accel = [math.cos(r) * self.ydir * 50, math.sin(r) * self.ydir * 50]


        gravity = 10.0
        a = [self.accel[0], self.accel[1] + gravity]
        pos = [self.x, self.y]
        verlet.integrate1(pos, self.v, a, 1 / FPS)
        verlet.integrate2(pos, self.v, a, 1 / FPS)
        self.x, self.y = pos

    def updateLocal(self, gamestate):
        if self.ydir!=0:
            particleDirMult=-0.05
            particlesCreate(self.x,self.y,self.accel[0]*particleDirMult,self.accel[1]*particleDirMult,0.5,self.particleColor,1)

