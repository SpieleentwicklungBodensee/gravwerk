import pygame
import argparse
import io
import os
import random
import math

from bitmapfont import BitmapFont

from globalconst import *
from gameobjects import *
from playerobject import *
from gamestate import *
from particles import *

import network
import sound

actions = []
gamestate = None

parser = argparse.ArgumentParser()
parser.add_argument('--connect')
parser.add_argument('--port', type=int, default=2000)
parser.add_argument('--host', action='store_true')
parser.add_argument('--nosnake', action='store_true')
parser.add_argument('--level', type=str, default='LEV1')
args = parser.parse_args()

net = None
clients = {}
if args.connect is not None:
    net = network.connect(args.connect, args.port)
    ownId = int(random.random() * 1000000)
    actions.append(('create-player', ownId))
    print('i am player with id=', ownId)
elif args.host:
    net = network.serve(args.port)

pygame.display.init()

if FULLSCREEN:
    window = pygame.display.set_mode(pygame.display.list_modes()[0], pygame.FULLSCREEN)
else:
    window = pygame.display.set_mode((WIN_W, WIN_H), 0)

screen = pygame.Surface((SCR_W, SCR_H))

clock = pygame.time.Clock()

pygame.mixer.init(44100)
pygame.joystick.init()

for i in range(pygame.joystick.get_count()):
    pygame.joystick.Joystick(i).init()

pygame.mouse.set_visible(False)

font = BitmapFont('gfx/heimatfont.png', scr_w=SCR_W, scr_h=SCR_H, colors=[(255,255,255), (240,0,240)])


ownId = 0

tiles = {'#': pygame.image.load('gfx/wall-solid.png'),
         '1': pygame.image.load('gfx/wall-ramp-lowerright.png'),
         '2': pygame.image.load('gfx/wall-ramp-lowerleft.png'),
         '3': pygame.image.load('gfx/wall-ramp-upperright.png'),
         '4': pygame.image.load('gfx/wall-ramp-upperleft.png'),

         'player': pygame.image.load('gfx/player.png'),
         }

level = ['#########################################',
         '#4                                    3#',
         '#                                      #',
         '#                                   1###',
         '#                                  1####',
         '#                                 1#####',
         '#2                                ######',
         '#####################             ######',
         '#################4               1######',
         '##########4                  ###########',
         '####4                        3##########',
         '###4                          3##########',
         '##4                            3########',
         '#4                                    3#',
         '#                                      #',
         '#                                      #',
         '#                    1#2               #',
         '#                   1###2              #',
         '#                 1######              #',
         '#              ##########2             #',
         '#2            1##############2        1#',
         '########################################',
         ]

gamestate = GameState()


def toggleFullscreen():
    global FULLSCREEN, window
    FULLSCREEN = not FULLSCREEN
    if FULLSCREEN:
        window = pygame.display.set_mode(pygame.display.list_modes()[0], pygame.FULLSCREEN)
    else:
        window = pygame.display.set_mode((WIN_W, WIN_H), 0)

def controls():
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return False
            if e.key in KEYS_THRUST:
                actions.append(('move-up', ownId))
            if e.key in KEYS_ROTATE_LEFT:
                actions.append(('rotate-left', ownId))
            if e.key in KEYS_ROTATE_RIGHT:
                actions.append(('rotate-right', ownId))


            if e.key in KEYS_FIRE:
                actions.append(('fire-press', ownId))

            if e.key == pygame.K_RETURN:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_LALT or mods & pygame.KMOD_RALT:
                    toggleFullscreen()

        if e.type == pygame.KEYUP:
            if e.key in KEYS_THRUST:
                actions.append(('stop-up', ownId))
            if e.key in KEYS_ROTATE_LEFT:
                actions.append(('stop-rotate-left', ownId))
            if e.key in KEYS_ROTATE_RIGHT:
                actions.append(('stop-rotate-right', ownId))

            if e.key in KEYS_FIRE:
                actions.append(('fire-release', ownId))

            if e.key == pygame.K_F11:
                global FPS
                if FPS == 20:
                    FPS = 60
                else:
                    FPS = 20

            if e.key == pygame.K_F12:
                global DEBUG_MODE
                DEBUG_MODE = not DEBUG_MODE

        if e.type == pygame.JOYAXISMOTION:
            if e.axis == 0:
                if e.value < -JOY_DEADZONE:
                    actions.append(('move-left', ownId))
                elif e.value > JOY_DEADZONE:
                    actions.append(('move-right', ownId))
                else:
                    if ownPlayer.xdir < 0:
                        actions.append(('stop-left', ownId))
                    if ownPlayer.xdir > 0:
                        actions.append(('stop-right', ownId))

            if e.axis == 1:
                if e.value < -JOY_DEADZONE:
                    actions.append(('move-up', ownId))
                elif e.value > JOY_DEADZONE:
                    actions.append(('move-down', ownId))
                else:
                    if ownPlayer.ydir < 0:
                        actions.append(('stop-up', ownId))
                    if ownPlayer.ydir > 0:
                        actions.append(('stop-down', ownId))

        if e.type == pygame.JOYBUTTONDOWN:
            actions.append(('fire-press', ownId))

        if e.type == pygame.JOYBUTTONUP:
            actions.append(('fire-release', ownId))

    return True

def render():
    screen.fill((0, 0, 0))
    if tick < 180:
        font.drawText(screen, 'GRAVWERK', 2, 2, fgcolor=(255,255,255))#, bgcolor=(0,0,0))

    for y in range(LEV_H):
        for x in range(LEV_W):
            tileId = level[y][x]

            if tileId in tiles:
                screen.blit(tiles[tileId], (x * TILE_W, y * TILE_H))

    for objId, obj in gamestate.objects.items():
        tileId = obj.getSprite()
        if not tileId in tiles:
            continue
        tile = tiles[tileId]

        rotated_sprite = pygame.transform.rotate(tile, obj.rotation)
        rotated_sprite = pygame.transform.scale(rotated_sprite, (round(rotated_sprite.get_size()[0]/8),round(rotated_sprite.get_size()[1]/8)))
        rotated_rect = rotated_sprite.get_rect(center = (obj.x,obj.y))
        screen.blit(rotated_sprite, rotated_rect)

    particlesRender(screen)

def update():
    global actions, gamestate

    if net is None or net.isHost():
        for obj in gamestate.objects.values():
            obj.update(gamestate)

    if net is not None:
        # as a host, put all played sounds into the queue
        if net.isHost():
            for soundname in sound.popHistory():
                gamestate.soundQueue.add(soundname)

        # sync gamestate over network
        gamestate, actions = net.update(gamestate, actions)
        ownPlayer = gamestate.objects.get(ownId)

        # retrieve sounds to be played as a client
        if not net.isHost():
            for soundname in gamestate.soundQueue:
                sound.playSound(soundname)
        gamestate.soundQueue = set()

    particlesUpdate()

    clientId = None
    for action, objId in actions:

        obj = gamestate.objects.get(objId)

        if not obj:
            continue

        if action == 'move-left':
            obj.move(-1, None)
        elif action == 'move-right':
            obj.move(1, None)
        elif action == 'move-up':
            obj.move(None, -1)
        elif action == 'move-down':
            obj.move(None, 1)
        elif action == 'rotate-left':
            obj.rotate(1)
        elif action == 'rotate-right':
            obj.rotate(-1)
        elif action == 'stop-left':
            obj.stop(True,False,False,False)
        elif action == 'stop-right':
            obj.stop(False,True,False,False)
        elif action == 'stop-up':
            obj.stop(False,False,True,False)
        elif action == 'stop-down':
            obj.stop(False,False,False,True)
        elif action == 'stop-rotate-left':
            obj.rotate(0)
        elif action == 'stop-rotate-right':
            obj.rotate(0)
        elif action == 'fire-press':
            obj.interact(gamestate)
        elif action == 'fire-release':
            obj.interact(gamestate, release=True)

    actions = []


def init():
    global gamestate

    player = PlayerObject(SCR_W // 2, SCR_H // 2, tile='player')

    gamestate = GameState()
    gamestate.objects[ownId] = player

    particlesInit()


init()

tick = 0
running = True

try:
    while running:
        tick += 1

        render()

        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()

        cont = controls()

        if not cont:
            running = False

        update()


        clock.tick(FPS)

finally:
    pygame.quit()
