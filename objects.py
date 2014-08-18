import time
import pygame
from pygame import sprite
import numpy
import objects
import pickle

def deserialize(s, game):
    d = pickle.loads(s)
    return eval("%s(d, game)" % d["class"])    

class BaseObject(sprite.Sprite):
    ''' basic sprite object '''
    
    def __init__(self, d, game, persistentMembers = None, *groups):
        if persistentMembers is None: persistentMembers = []
        self.persistentMembers = persistentMembers
        self.persistentMembers.extend(["wrect", "pos", "id"])
        
        sprite.Sprite.__init__(self, *groups)

        self.id = time.time()
        
        for member in self.persistentMembers:
            if member in d:
                self.__dict__[member] = self._deserializeValue(member, d[member])
        
        self.rect = self.wrect.copy()
        
        if not hasattr(self, "pos"):
            #self.pos = self.rect.center = numpy.array(self.wrect.center)
            self.pos = self.rect.topleft = numpy.array(self.wrect.topleft)        
        
    def update(self, game):
        # update the sprite's drawing position relative to the camera
        #self.rect.center = self.pos - game.camera.pos
        self.rect.topleft = self.pos - game.camera.pos

    
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
        if name == "pos":
            return self._stringToEval("numpy.array([%s, %s])" % (str(self.pos[0]), str(self.pos[1])))
        return value

    def serialize(self):
        return pickle.dumps(self.toDict())

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

class Image(BaseObject):
    def __init__(self, d, game):
        BaseObject.__init__(self, d, game, persistentMembers=["image"])

    def setSurface(self, surface):
        self.image = surface.convert()
        self.rect = self.image.get_rect()

    def _serializeValue(self, name, value):
        format = "RGBA"
        if name == "image":
            s = pygame.image.tostring(self.image, format)
            cs = s.encode("zlib")
            return (cs, self.image.get_size(), format)
        return super(Image, self)._serializeValue(name, value)

    def _deserializeValue(self, name, value):
        if name == "image" and type(value) == tuple:
            return pygame.image.frombuffer(value[0].decode("zlib"), *value[1:])
        return super(Image, self)._deserializeValue(name, value)

class ImageFromResource(Image):
    def __init__(self, filename, d, game):
        Image.__init__(self, d, game)
        surface = pygame.image.load(filename)
        self.setSurface(surface)
    
class Scribble(Image):
    def __init__(self, d, game):
        Image.__init__(self, d, game)
