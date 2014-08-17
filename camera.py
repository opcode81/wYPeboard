import pygame
import numpy


class CenteringCamera(pygame.sprite.Sprite):
    ''' a basic camera that always centres the camera on the player '''
    
    def __init__(self, game):
        self.translate = numpy.array([-game.width/2, -game.height/2])
        
    def update(self, game):        
        self.pos = game.avatar.pos + self.translate


class ChasingCamera(pygame.sprite.Sprite):
    ''' a basic chasing camera '''
    
    def __init__(self, game):
        self.translate = numpy.array([-game.width/2, -game.height/2])
        self.pos = game.avatar.pos
        
    def update(self, game):        
        self.pos += (game.avatar.pos + self.translate - self.pos) *0.03