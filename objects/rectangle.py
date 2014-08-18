import pygame
from objects import BaseObject
import os
import numpy

class Rectangle(BaseObject):
    def __init__(self, d, game):
        if type(d) != dict: # old construction
            BaseObject.__init__(self, {"wrect": d.rect}, game)
            self.setSize(d.rect.width, d.rect.height)
            self.default = self.visible = d.visibleDefault
            self.group = d.setBy
            if d.setBy == "":
                self.group = None
        else:
            BaseObject.__init__(self, d, game)
            self.setSize(self.rect.width, self.rect.height)
            
    def setSize(self, width, height):
        self.image = pygame.Surface((width, height)).convert()
        self.rect.width = width
        self.rect.height = height
    
class Scribble(BaseObject):
    def __init__(self, d, game):
        BaseObject.__init__(self, d, game, persistentMembers=["image"])

    def setSurface(self, surface):
        self.image = surface.convert()
        self.rect = self.image.get_rect()

    def update(self, game):
        # update the sprite's drawing position relative to the camera
        self.rect.topleft = self.pos - game.camera.pos
    
    def _serializeValue(self, name, value):
        format = "RGBA"
        if name == "image":
            s = pygame.image.tostring(self.image, format)
            return (s, self.image.get_size(), format)
        return super(Scribble, self)._serializeValue(name, value)

    def _deserializeValue(self, name, value):
        if name == "image" and type(value) == tuple:
            return pygame.image.frombuffer(*value)
        return super(Scribble, self)._deserializeValue(name, value)