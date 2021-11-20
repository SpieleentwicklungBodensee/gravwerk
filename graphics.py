import pygame

from bitmapfont import *
from globalconst import *

tiles = {}
font = None
rotatedSprites = {}
masks = {}
rotatedMasks = {}

debugTiles = []


def loadGraphics():
    global font
    font = BitmapFont('gfx/heimatfont.png', scr_w=SCR_W, scr_h=SCR_H, colors=[(255,255,255), (240,0,240)])

    global tiles
    tiles = {'#': pygame.image.load('gfx/wall-solid.png'),
            '1': pygame.image.load('gfx/wall-ramp-lowerright.png'),
            '2': pygame.image.load('gfx/wall-ramp-lowerleft.png'),
            '3': pygame.image.load('gfx/wall-ramp-upperright.png'),
            '4': pygame.image.load('gfx/wall-ramp-upperleft.png'),

            'player0': pygame.image.load('gfx/player0.png'),
            'player1': pygame.image.load('gfx/player1.png'),
            'player2': pygame.image.load('gfx/player2.png'),
            'player3': pygame.image.load('gfx/player3.png'),
            'player4': pygame.image.load('gfx/player4.png'),
            'player5': pygame.image.load('gfx/player5.png'),

            'debug': pygame.image.load('gfx/debugtile.png'),
            }

    global masks
    for tileId in tiles.keys():
        masks[tileId] = pygame.mask.from_surface(tiles[tileId])

def getFont():
    return font

def rotateSprite(obj):
    tileId = obj.getSprite()

    if not tileId in tiles:
        return (None, None)

    tile = tiles[tileId]

    rotated_sprite = pygame.transform.rotate(tile, obj.rotation)
    rotated_sprite = pygame.transform.scale(rotated_sprite, (round(rotated_sprite.get_size()[0]/16),round(rotated_sprite.get_size()[1]/16)))
    rotated_rect = rotated_sprite.get_rect(center = (obj.x,obj.y))

    rotatedSprites[obj] = (rotated_sprite, rotated_rect)
    rotatedMasks[obj] = pygame.mask.from_surface(rotated_sprite)

    return rotated_sprite, rotated_rect


def getTiles():
    return tiles

def getFont():
    return font

def getRotatedSprites():
    return rotatedSprites

def checkPixelTileCollision(obj, tileId, tilex, tiley):
    mask = masks[tileId]
    playermask = rotatedMasks[obj]

    objx = rotatedSprites[obj][1].x
    objy = rotatedSprites[obj][1].y

    return mask.overlap(playermask, (int(objx - tilex * TILE_W), int(objy - tiley * TILE_H)))
