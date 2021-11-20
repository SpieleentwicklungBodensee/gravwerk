from globalconst import *
from gameobjects import *
from particles import *
from graphics import *

import math
import verlet

class PlayerObject(GameObject):
    def __init__(self, x, y, tile=None, particleColor = (255,128,0)):
        GameObject.__init__(self, x, y, tile)
        self.particleColor = particleColor

    def getThrust(self, power = 50.0):
        r = -math.radians(self.rotation) + 0.5 * math.pi
        return [math.cos(r) * self.ydir * power, math.sin(r) * self.ydir * power]

    def update(self, gamestate):
        self.rotation = math.fmod(self.rotation + self.rotationDir * ROTATION_CHANGE, 360)
        a = self.getThrust()

        gravity = 10.0
        a[1] += gravity
        pos = [self.x, self.y]
        verlet.integrate1(pos, self.v, a, 1 / FPS)
        verlet.integrate2(pos, self.v, a, 1 / FPS)
        self.x, self.y = pos


        # collision with level
        cx, cy = int(self.x // TILE_W), int(self.y // TILE_H)
        level = gamestate.level

        self.checkTileCollision(level, cx -1, cy -1)
        self.checkTileCollision(level, cx +0, cy -1)
        self.checkTileCollision(level, cx +1, cy -1)
        self.checkTileCollision(level, cx -1, cy)
        self.checkTileCollision(level, cx +0, cy)
        self.checkTileCollision(level, cx +1, cy)
        self.checkTileCollision(level, cx -1, cy +1)
        self.checkTileCollision(level, cx +0, cy +1)
        self.checkTileCollision(level, cx +1, cy +1)

    def updateLocal(self, gamestate):
        thrust = self.getThrust()
        if thrust[0] != 0 or thrust[1] != 0:
            particleDirMult = -3.0
            thrust[0] *= particleDirMult / FPS
            thrust[1] *= particleDirMult / FPS
            particlesCreate(self.x,self.y,thrust[0] + self.v[0]/FPS,thrust[1] + self.v[1]/FPS,0.5,self.particleColor,1)

    def checkTileCollision(self, level, cx, cy):
        if cx < 0 or cy < 0 or cx >= len(level[0]) or cy >= len(level):
            return

        debugTiles.append((cx, cy))

        tileId = level[cy][cx]

        if tileId == ' ':
            return False

        tile = getTiles()[tileId]

        if checkPixelTileCollision(self, tileId, cx, cy):
            debugTiles.append((cx, cy))
            print('coll!')

