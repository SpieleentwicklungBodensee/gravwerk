import pygame
import random
import math

import globalconst

class Particle():
    def __init__(self):
        self.x=-1      # position; <0 means inactive
        self.y=0       # position
        self.xv=0      # velocity
        self.yv=0      # velocity
        self.c=(0,0,0) # color

PS_N=0
PS_I=0
psE=[]

def particlesInit():
    global PS_N
    global PS_I
    global psE
    PS_N=1024
    PS_I=0
    psE=[]
    for i in range(PS_N):
        psE.append(Particle())

def particlesCreate(x,y,xSpeed,ySpeed,rndSpeed,color,count):
    global PS_N
    global PS_I
    global psE
    for i in range(count):
        PS_I+=1
        if PS_I==PS_N:
            PS_I=0
        psE[PS_I].x=x
        psE[PS_I].y=y
        psE[PS_I].xv=xSpeed+random.uniform(-rndSpeed,rndSpeed)
        psE[PS_I].yv=ySpeed+random.uniform(-rndSpeed,rndSpeed)
        psE[PS_I].c=color

def particlesUpdate():
    global psE
    for e in psE:
        e.x+=e.xv
        e.y+=e.yv
        e.yv+=0.02
        e.xv*=0.99
        e.yv*=0.99

def particlesRender(surface,camera):
    global psE
    for e in psE:
        surface.set_at((round(e.x-camera[0]),round(e.y-camera[1])),e.c)

    # screen crumble effect
    if random.uniform(0,1)<0.1:
        x=round(random.uniform(0,surface.get_size()[0]-1))
        y=round(random.uniform(0,surface.get_size()[1]-1))
        c=surface.get_at((x,y))
        if c!=(0,0,0):
            particlesCreate(x+camera[0],y+camera[1],0,0,0,c,1)
