import time
import pygame
from pygame import sprite
import numpy
import objects
import pickle
import threading

def deserialize(s, game):
    d = pickle.loads(s)
    return eval("%s(d, game)" % d["class"])    

class BaseObject(sprite.Sprite):
    ''' basic sprite object '''
    
    def __init__(self, d, game, persistentMembers = None, isUserObject=False, *groups):
        self.isUserObject = isUserObject
        
        if persistentMembers is None: persistentMembers = []
        self.persistentMembers = persistentMembers
        self.persistentMembers.extend(["rect", "pos", "id"])
        
        sprite.Sprite.__init__(self, *groups)

        self.id = time.time()
        
        for member in self.persistentMembers:
            if member in d:
                self.__dict__[member] = self._deserializeValue(member, d[member])
        
        #if hasattr(self, "wrect"):
        #    self.rect = self.wrect.copy()
        
        if not hasattr(self, "pos"):
            #self.pos = self.rect.center = numpy.array(self.wrect.center)
            self.pos = self.rect.topleft = numpy.array(self.rect.topleft)
    
    class MovementAnimationThread(threading.Thread):
        def __init__(self, obj, pos, duration):
            threading.Thread.__init__(self)
            self.obj = obj
            self.pos = pos
            self.duration = duration
            self.animating = True
        
        def run(self):
            startPos = self.obj.pos
            translation = numpy.array(self.pos) - startPos
            startTime = time.time()
            while self.animating:
                passed = min(time.time() - startTime, self.duration)
                self.obj.pos = startPos + (passed / self.duration) * translation
                if passed == self.duration:
                    break
                time.sleep(0.010)
    
    def animateMovement(self, pos, duration):
        if hasattr(self, "movementAnimationThread"):
            self.movementAnimationThread.animating = False
        self.movementAnimationThread = BaseObject.MovementAnimationThread(self, pos, duration)
        self.movementAnimationThread.start()
    
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
        if name == "rect":
            return self._stringToEval("pygame.Rect(%d, %d, %d, %d)" % (self.rect.left, self.rect.top, self.rect.width, self.rect.height))
        if name == "pos":
            return self._stringToEval("numpy.array([%s, %s])" % (str(self.pos[0]), str(self.pos[1])))
        return value

    def serialize(self):
        return pickle.dumps(self.toDict())

class Rectangle(BaseObject):
    def __init__(self, d, game, **kwargs):
        BaseObject.__init__(self, d, game, persistentMembers=["colour"], isUserObject=True, **kwargs)
        self.setSize(self.rect.width, self.rect.height)
            
    def setSize(self, width, height):
        surface = pygame.Surface((width, height))
        surface.fill(self.colour)
        self.image = surface.convert()
        self.rect.width = width
        self.rect.height = height

class Image(BaseObject):
    def __init__(self, d, game, persistentMembers = None, **kwargs):
        if persistentMembers is None: persistentMembers = []
        BaseObject.__init__(self, d, game, persistentMembers=persistentMembers+["image"], **kwargs)

    def setSurface(self, surface):
        self.image = surface.convert()
        self.rect = self.image.get_rect()

    def _serializeValue(self, name, value):
        format = "RGBA"
        if name == "image":
            s = pygame.image.tostring(self.image, format)
            cs = s.encode("zlib")
            print "compression: %d -> %d" % (len(s), len(cs))
            return (cs, self.image.get_size(), format)
        return super(Image, self)._serializeValue(name, value)

    def _deserializeValue(self, name, value):
        if name == "image" and type(value) == tuple:
            dim = value[1:][0]
            if dim[0] == 0 or dim[1] == 0:
                return pygame.Surface((10,10)).convert()
            return pygame.image.frombuffer(value[0].decode("zlib"), *value[1:])
        return super(Image, self)._deserializeValue(name, value)

class ImageFromResource(Image):
    def __init__(self, filename, d, game):
        Image.__init__(self, d, game)
        surface = pygame.image.load(filename)
        self.setSurface(surface)
    
class Scribble(Image):
    def __init__(self, d, game):
        Image.__init__(self, d, game, isUserObject=True)

class Text(Image):
    def __init__(self, d, game):
        Image.__init__(self, d, game, persistentMembers=["text", "colour", "fontSize", "fontName"], isUserObject=True)
        self.font = pygame.font.SysFont(self.fontName, self.fontSize)
        self.setText(self.text)
        
    def setText(self, text):
        #font = pygame.freetype.get_default_font()
        #self.image = font.render(self.text, fgcolor=self.colour, size=10)
        self.text = text
        lines = text.split("\n")
        width = 0
        height = 0
        for l in lines:
            w, h = self.font.size(l)
            width = max(w, width)
            height += h
        
        surface = pygame.Surface((width, height))
        surface.fill((255, 255, 255))
        
        y = 0
        for l in lines:
            s = self.font.render(l, True, self.colour, (255,255,255))
            surface.blit(s, (0, y))
            y += s.get_height()
        
        self.setSurface(surface)