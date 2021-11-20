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
    PS_N=2048
    PS_I=0
    psE=[]
    for i in range(PS_N):
        psE.append(Particle())

def particlesCreate(x,y,speed,color,count):
    global PS_N
    global PS_I
    global psE
    for i in range(count):
        PS_I+=1
        if PS_I==PS_N:
            PS_I=0
        psE[PS_I].x=x
        psE[PS_I].y=y
        psE[PS_I].xv=random.uniform(-speed,speed)
        psE[PS_I].yv=random.uniform(-speed,speed)
        psE[PS_I].c=color

def particlesUpdate():
    global psE
    for e in psE:
        e.x=e.x+e.xv
        e.y=e.y+e.yv
        e.yv+=0.1
        e.xv*=0.98
        e.yv*=0.98

def particlesRender(surface):
    global psE
    for e in psE:
        surface.set_at((round(e.x),round(e.y)),e.c)
