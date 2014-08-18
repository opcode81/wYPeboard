import pygame
from pygame import sprite
from events import EventHandler
import numpy
import objects
import pickle

def deserialize(s, game):
    d = pickle.loads(s)
    return eval("%s(d, game)" % d["class"])    

class BaseObject(sprite.Sprite, EventHandler):
    ''' basic game object '''
    
    def __init__(self, d, game, persistentMembers = None, *groups):
        if persistentMembers is None: persistentMembers = []
        if not hasattr(self, "peristentMembers"):
            self.persistentMembers = persistentMembers
        
        self.persistentMembers.append("wrect")
        
        sprite.Sprite.__init__(self, *groups)
        EventHandler.__init__(self, game)
        
        evalTag = "_EVAL_:"
        for member in self.persistentMembers:
            self.__dict__[member] = self._deserializeValue(member, d[member])
        
        self.rect = self.wrect.copy()
        self.pos = self.rect.center = numpy.array(self.wrect.center)        
        
    def update(self, game):
        # update the sprite's drawing position relative to the camera
        self.rect.center = self.pos - game.camera.pos
    
    def collide(self, group, doKill=False, collided=None):
        return sprite.spritecollide(self, group, doKill, collided)

    def kill(self):
        #self.unbindAll()
        sprite.Sprite.kill(self)

    def offset(self, x, y):
        self.pos += numpy.array([x,y])
    
    def toDict(self):    	
        d = {
            "class": "%s.%s" % (self.__class__.__module__, self.__class__.__name__)            
        }
        for member in self.persistentMembers:
            d[member] = self._serializeMember(member)
        return d

    def _serializeMember(self, name):
        return self._serializeValue(name, self.__dict__[name])        

    def _deserializeValue(self, name, value):
        evalTag = "_EVAL_:"
        if type(value) == str and value[:len(evalTag)] == evalTag:
            value = eval(value[len(evalTag):])
        return value

    def _stringToEval(self, s):
        return "_EVAL_:" + s

    def _serializeValue(self, name, value):
        if name == "wrect":
            return self._stringToEval("pygame.Rect(%d, %d, %d, %d)" % (self.rect.left, self.rect.top, self.rect.width, self.rect.height))
        return value

    def serialize(self):
        return pickle.dumps(self.toDict())
