# (C) 2014 by Dominik Jain (djain@gmx.net)

import time
import pygame
from pygame import sprite
import numpy
import objects
import pickle
import threading
import aaline
import logging 

log = logging.getLogger(__name__)

def deserialize(s, game):
    d = pickle.loads(s)
    return eval("%s(d, game)" % d["class"])    

class Alignment(object):
    TOP_LEFT, CENTRE, BOTTOM_LEFT = range(3)

class BaseObject(sprite.Sprite):
    ''' basic sprite object '''
    
    def __init__(self, d, game, persistentMembers = None, isUserObject=False, layer=1, alignment=Alignment.TOP_LEFT):
        self.isUserObject = isUserObject
        
        if persistentMembers is None: persistentMembers = []
        self.persistentMembers = persistentMembers
        self.persistentMembers.extend(["rect", "pos", "id"])
        
        sprite.Sprite.__init__(self)

        self.alignment = alignment
        self.layer = layer
        self.id = time.time()
        
        for member in self.persistentMembers:
            if member in d:
                self.__dict__[member] = self._deserializeValue(member, d[member])
        
        if not hasattr(self, "pos"):
            if hasattr(self, "rect"):
                if self.alignment == Alignment.TOP_LEFT:
                    self.pos = self.rect.topleft
                elif self.alignment == Alignment.CENTRE:
                    self.pos = self.rect.center
                elif self.alignment == Alignment.BOTTOM_LEFT:
                    self.pos = self.rect.bottomleft
                else:
                    raise Exception("unknown alignment: %s" % self.alignment)
            else:
                self.pos = (0, 0)
    
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
        coord = self.pos - game.camera.pos
        if self.alignment == Alignment.TOP_LEFT:
            self.rect.topleft = coord
        elif self.alignment == Alignment.CENTRE:
            self.rect.center = coord
        elif self.alignment == Alignment.BOTTOM_LEFT:
            self.rect.bottomleft = coord
    
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
            if hasattr(self, member):
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

    def absRect(self):
        ''' returns a rectangle reflecting the abolute extents of the object '''
        return pygame.Rect(self.pos[0], self.pos[1], self.rect.width, self.rect.height)

class Rectangle(BaseObject):
    def __init__(self, d, game, **kwargs):
        if not "isUserObject" in kwargs: kwargs["isUserObject"] = True
        BaseObject.__init__(self, d, game, persistentMembers=["colour"], **kwargs)
        self.setSize(self.rect.width, self.rect.height)
            
    def setSize(self, width, height):
        width, height = max(1, width), max(1, height)
        alpha = len(self.colour) == 4
        surface = pygame.Surface((width, height), flags=pygame.SRCALPHA if alpha else 0)
        surface.fill(self.colour)
        self.image = surface.convert() if not alpha else surface.convert_alpha()
        self.rect.width = width
        self.rect.height = height

class Image(BaseObject):
    def __init__(self, d, game, persistentMembers = None, **kwargs):
        if persistentMembers is None: persistentMembers = []
        BaseObject.__init__(self, d, game, persistentMembers=persistentMembers+["image"], **kwargs)

    def setSurface(self, surface, ppAlpha = False):
        self.image = surface.convert() if not ppAlpha else surface.convert_alpha()
        self.rect = self.image.get_rect()

    def _serializeValue(self, name, value):
        if name == "image":
            format = "RGBA"
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
    def __init__(self, filename, game, ppAlpha=False, **kwargs):
        Image.__init__(self, {}, game, **kwargs)        
        surface = pygame.image.load(filename)
        self.setSurface(surface, ppAlpha=ppAlpha)

class ScribbleRenderer(object):
    def __init__(self, scribble):    
        self.antialiasing = False
        self.margin = 2*scribble.lineWidth
        self.colour = scribble.colour
        self.lineWidth = scribble.lineWidth
        surface = pygame.Surface((self.margin, self.margin), flags=pygame.SRCALPHA if self.antialiasing else 0) # TODO: aaline does not work with SRCALPHA!
        self.backgroundColour = (255, 0, 255) if not self.antialiasing else (255, 255, 255, 0)
        surface.fill(self.backgroundColour)
        if not self.antialiasing:
            surface.set_colorkey(self.backgroundColour)
        self.surface = surface
        self.isFirstPoint = True
        self.obj = scribble
        self.inputBuffer = []
        
    def addPoint(self, x, y, draw=True):
        if self.isFirstPoint:
            self.lineStartPos = numpy.array([x, y])
            self.translateOrigin = numpy.array([-x, -y])
            self.minX = self.maxX = x
            self.minY = self.maxY = y
            self.isFirstPoint = False
        
        self.inputBuffer.append((x, y))
        
        if draw:
            self._processInputs()
    
    def addPoints(self, points):
        for point in points:
            self.addPoint(*point, draw=False)
        self._processInputs()
            
    def _processInputs(self):
        padLeft = 0
        padTop = 0

        oldWidth = self.surface.get_width()
        oldHeight = self.surface.get_height()
        newWidth = oldWidth
        newHeight = oldHeight

        # determine growth
        for x, y in self.inputBuffer:
            #print "\nminX=%d maxX=%d" % (self.minX, self.maxX)
            #print "x=%d y=%d" % (x,y)
            growRight = x - self.maxX if x > self.maxX else 0
            growLeft = self.minX - x if x < self.minX else 0
            growBottom = y - self.maxY if y > self.maxY else 0
            growTop = self.minY - y if y < self.minY else 0

            padLeft += growLeft
            padTop += growTop

            #print "grow: right=%d left=%d top=%d bottom=%d" % (growRight, growLeft, growTop, growBottom)
            self.maxX = max(self.maxX, x)
            self.maxY = max(self.maxY, y)
            self.minX = min(self.minX, x)
            self.minY = min(self.minY, y)
            #print "new: minX=%d maxX=%d" % (self.minX, self.maxX)

            newWidth += growLeft + growRight
            newHeight += growBottom + growTop

        # create new larger surface and copy old surface content
        if newWidth > oldWidth or newHeight > oldHeight:
            #print "newDim: (%d, %d)" % (newWidth, newHeight)
            surface = pygame.Surface((newWidth, newHeight), pygame.SRCALPHA if self.antialiasing else 0)
            surface.fill(self.backgroundColour)
            if not self.antialiasing:
                surface.set_colorkey(self.backgroundColour)
            surface.blit(self.surface, (padLeft, padTop))
            self.surface = surface

        # translate pos
        self.obj.offset(-padLeft, -padTop)

        # draw new lines
        for x, y in self.inputBuffer:
            self._drawLineTo(x, y)

        # apply new surface
        self.obj.setSurface(self.surface, ppAlpha=self.antialiasing)

        # reset input buffer
        self.inputBuffer = []

    def _drawLineTo(self, x, y):
        # draw line
        margin = self.margin
        self.translateOrigin = -self.obj.pos + numpy.array([-margin, -margin])
        #print "translateOrigin=%s" % str(self.translateOrigin)
        marginTranslate = numpy.array([margin, margin])
        pos1 = self.lineStartPos + self.translateOrigin + marginTranslate
        pos2 = numpy.array([x, y]) + self.translateOrigin + marginTranslate
        #print "drawing from %s to %s" % (str(pos1), str(pos2))
        if not self.antialiasing:
            pygame.draw.line(self.surface, self.colour, pos1, pos2, self.lineWidth)
        else:
            aaline.aaline(self.surface, self.colour, pos1, pos2, self.lineWidth)
        self.lineStartPos = numpy.array([x, y])

    def end(self):
        self._processInputs()
        
class Scribble(Image):
    ''' an image-based scribble sprite '''
    def __init__(self, d, game, startPoint=None, persistentMembers=None):
        if startPoint is not None:
            if "lineWidth" not in d: raise Exception("construction with startPoint requires lineWidth")
            margin = 2 * d["lineWidth"]
            d["rect"] = pygame.Rect(startPoint[0] - margin/2, startPoint[1] - margin/2, margin, margin)
            if "pos" in d: del d["pos"] # will be set from rect
        if persistentMembers is None: persistentMembers = []
        Image.__init__(self, d, game, isUserObject=True, persistentMembers=persistentMembers+["lineWidth", "colour"])
    
    def addPoints(self, points):
        if not hasattr(self, "scribbleRenderer"):
            self.scribbleRenderer = ScribbleRenderer(self)
        self.scribbleRenderer.addPoints(points)
    
    def endDrawing(self):
        self.scribbleRenderer.end()
        del self.scribbleRenderer

class PointBasedScribble(Scribble):
    ''' a point-based scribble sprite, which, when persisted, is reconstructed from the individual points '''
    def __init__(self, d, game, startPoint=None):
        pos = None
        if "pos" in d:
            pos = self._deserializeValue("pos", d["pos"])
        if startPoint is None:
            if "points" in d and len(d["points"]) > 0:
                startPoint = d["points"][0]
            else:
                raise Exception('construction requires either startPoint or non-empty d["points"]"')
        else:
            if "points" in d: raise Exception('cannot provide both startPoint and d["points"]')
        Scribble.__init__(self, d, game, persistentMembers=["points"], startPoint=startPoint)
        self.persistentMembers.remove("image")
        self.persistentMembers.remove("rect")
        if not hasattr(self, "points"):
            self.points = []
        else:
            Scribble.addPoints(self, self.points)
        if pos is not None:
            self.pos = pos
    
    def addPoints(self, points):
        self.points.extend(points)        
        Scribble.addPoints(self, points)
        #log.debug("relative points: %s", map(list, [numpy.array(p)-self.pos for p in self.points]))
        
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

def boundingRect(objects):
    r = objects[0].absRect()
    return r.unionall([o.absRect() for o in objects[1:]])
