import pygame

sounds = {}
soundhistory = []

def loadSound(name, filename):
    sound = pygame.mixer.Sound(filename)
    sounds[name] = sound

def playSound(name):
    sounds[name].play()
    soundhistory.append(name)

def popHistory():
    global soundhistory
    copy = list(soundhistory)
    soundhistory = []

    return copy