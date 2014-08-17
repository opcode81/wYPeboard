from pygame import sprite
from events import EventHandler
import numpy
import objects


class BaseObject(sprite.Sprite, EventHandler):
    ''' basic game object '''
    
    def __init__(self, d, game, *groups):
        if not hasattr(self, "peristentMembers"):
            self.persistentMembers = []
        
        self.persistentMembers.append("wrect")
        
        sprite.Sprite.__init__(self, *groups)
        EventHandler.__init__(self, game)
        
        for member in self.persistentMembers:
            self.__dict__[member] = d[member]
        
        self.rect = self.wrect.copy()
        self.pos = self.rect.center = numpy.array(self.wrect.center)        
        
    def update(self, game):
        # update the sprite's drawing position relative to the camera
        self.rect.center = self.pos - game.camera.pos
    
    def collide(self, group, doKill=False, collided=None):
        return sprite.spritecollide(self, group, doKill, collided)

    def kill(self):
        self.unbindAll()
        sprite.Sprite.kill(self)

    def offset(self, x, y):
        self.pos += numpy.array([x,y])
    
    def saveFormat(self):    	
        d = {
            "class": "%s.%s" % (self.__class__.__module__, self.__class__.__name__)            
        }
        for member in self.persistentMembers:
            d[member] = self.__dict__[member]

    @staticmethod
    def fromSaveFormat(d, game):
        return eval("%s(d, game)" % d["class"])
