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
from graphics import *

import network
import sound

actions = []
gamestate = None
playerColor = 0
particleColors = [(62,154,193),(221,61,0),(49,221,0),(188,62,193),(193,182,62),(120,120,120)]

parser = argparse.ArgumentParser()
parser.add_argument('--connect')
parser.add_argument('--port', type=int, default=2000)
parser.add_argument('--host', action='store_true')
args = parser.parse_args()

net = None
clients = {}
ownId = int(random.random() * 1000000)
if args.connect is not None:
    net = network.connect(args.connect, args.port)
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




level = ['###############################################################################',
         '#4                                                                           3#',
         '#                                                                             #',
         '#                                                                             #',
         '#                                                                             #',
         '#                                                                             #',
         '#                                1#######2                                    #',
         '#                               1#########2                                   #',
         '#                           1#####4  3#####2                                  #',
         '#                      1##########    ####4                                1###',
         '#                     1##########4   1####                                1####',
         '#                    1#4      3##    3##4                                1#####',
         '#2                  1##        3#     #4                                 3#####',
         '#######F___T##########4                                                   #####',
         '#################4                                                      1######',
         '##########4                                                            1#######',
         '####4                                                                1#########',
         '###4                                                               1###########',
         '##4                                                               1############',
         '#4                         1###################################################',
         '#                          ####################################################',
         '#                         1#######4                 3###4                     #',
         '#                       1##4                         ###                      #',
         '#                   1####4                           ###                      #',
         '#                  1#####                            ###                      #',
         '#              1######4                              ###                      #',
         '#            1####4                                  ###                      #',
         '#          1####4                                    3#4                      #',
         '#          3###4                                                              #',
         '#           3#4                                                               #',
         '#                             1#2                                             #',
         '#                            1###2                                            #',
         '#                            1######                                          #',
         '#                            ##########2                                      #',
         '#2                         1##############2          1#######F___T####2      1#',
         '###############################################################################',
         ]

gamestate = GameState()


def render_object(obj,camera_pos):
    tileId = obj.getSprite()
    if not tileId in getTiles():
        return
    tile = getTiles()[tileId]

    rotated_sprite, rotated_rect = rotateSprite(obj)

    screen.blit(rotated_sprite, (rotated_rect.x - camera_pos[0], rotated_rect.y - camera_pos[1]))


def toggleFullscreen():
    global FULLSCREEN, window
    FULLSCREEN = not FULLSCREEN
    if FULLSCREEN:
        window = pygame.display.set_mode(pygame.display.list_modes()[0], pygame.FULLSCREEN)
    else:
        window = pygame.display.set_mode((WIN_W, WIN_H), 0)

def createPlayer(objId):
    global playerColor, gamestate


    # create ordinary player
    x, y = (0,0)
    newPlayer = PlayerObject(SCR_W // 2, SCR_H // 2, tile='player'+str(playerColor), particleColor=particleColors[playerColor])
    playerColor += 1
    playerColor %= 6
    gamestate.objects[objId] = newPlayer
    print('created player with id=', objId)

def removePlayer(objId):
    del gamestate.objects[objId]

def controls():
    global ownId, actions, gamestate

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

            if e.key in KEYS_RESET:
                actions.append(('reset', ownId))

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
                    actions.append(('rotate-left', ownId))
                elif e.value > JOY_DEADZONE:
                    actions.append(('rotate-right', ownId))
                else:
                    actions.append(('stop-rotate-left', ownId))
                    actions.append(('stop-rotate-right', ownId))

        if e.type == pygame.JOYBUTTONDOWN:
            actions.append(('move-up', ownId))

        if e.type == pygame.JOYBUTTONUP:
            actions.append(('stop-up', ownId))

    return True

def render():
    screen.fill((0, 0, 0))
    if tick < 180:
        getFont().drawText(screen, 'GRAVWERK', 2, 2, fgcolor=(255,255,255))#, bgcolor=(0,0,0))

    #get own position
    camera_pos = (0,0)
    for obj_id ,obj in gamestate.objects.items():
        if obj_id == ownId:
            camera_pos = (math.floor(obj.x - SCR_W/2 + TILE_W/2), math.floor(obj.y - SCR_H/2 + TILE_H/2))
            break


    #blit all the tiles onto the screen
    for y in range(len(level)):
        for x in range(len(level[y])):
            tileId = level[y][x]

            if tileId in getTiles():
                screen.blit(getTiles()[tileId], (x * TILE_W - camera_pos[0], y * TILE_H - camera_pos[1]))

    #blit objects on the screen
    for wobjId, obj in gamestate.objects.items():
        render_object(obj,camera_pos)

    if DEBUG_MODE:
        for cx, cy in debugTiles:
            screen.blit(getTiles()['debug'], (cx * TILE_W - camera_pos[0], cy * TILE_H - camera_pos[1]))
    debugTiles.clear()

    particlesRender(screen,camera_pos)

def update():
    global actions, gamestate

    if net is None or net.isHost():
        for obj in gamestate.objects.values():
            obj.update(gamestate)

    for obj in gamestate.objects.values():
        obj.updateLocal(gamestate)


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

        if action == 'client-actions':
            clientId = objId
            continue
        if action == 'client-disconnect':
            if objId in clients:
                removePlayer(clients[objId])
            continue

        if action == 'create-player':
            clients[clientId] = objId
            createPlayer(objId)
            continue

        obj = gamestate.objects.get(objId)

        print('action:', action, 'objId:', objId)

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
        elif action == 'reset':
            obj.reset()
        elif action == 'fire-press':
            obj.interact(gamestate)
        elif action == 'fire-release':
            obj.interact(gamestate, release=True)

    actions = []


def init():
    global gamestate,playerColor,particleColors

    player = PlayerObject(SCR_W // 2, SCR_H // 2, tile='player'+str(playerColor),particleColor = particleColors[playerColor])

    playerColor +=1

    gamestate = GameState()
    gamestate.objects[ownId] = player
    gamestate.level = level

    particlesInit()


loadGraphics()
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
    if net is not None:
        net.stop()

    pygame.quit()
