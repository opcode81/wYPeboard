import cPickle as pickle
from objects import *
import levelformat
from pygame import sprite
from renderer import LayeredRenderer

class Canvas(LayeredRenderer):
    def __init__(self, game):
        LayeredRenderer.__init__(self)

        self.groups = {}
        self.userObjects = sprite.Group()
    
    def addGroup(self, cls):
        group = sprite.Group()
        self.groups[cls] = group
        return group
    
    def add(self, *objects):
        LayeredRenderer.add(self, *objects)

        for object in objects:
            if object.isUserObject:
                self.userObjects.add(object)
    
    def saveFormat(self):
        return {
            "objects": [o.saveFormat() for o in self.sprites()],
            "playerInitialPos": self.playerInitialPos
        }
        