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
            rect = d["wrect"]
            self.setSize(rect.width, rect.height)
            
    def setSize(self, width, height):
        self.image = pygame.Surface((width, height)).convert()
        self.rect.width = width
        self.rect.height = height
    
    def activate(self):
        self.visible = not self.default

    def deactivate(self):
        self.visible = self.default

    def reset(self):
        pass
