import cPickle as pickle
from objects import *
import levelformat
from pygame import sprite
from renderer import LayeredRenderer

class Canvas(LayeredRenderer):
    def __init__(self, game):
        LayeredRenderer.__init__(self)

        self.groups = {}
        self.platforms = self.addGroup(Rectangle)
        self.scribbles = self.addGroup(Scribble)
        #self.exits = self.addGroup(Exit)
        #self.portals = self.addGroup(Portal)
        '''
        if levelFile[-2:] == ".p": # old level format
            levelFormat = pickle.load(open(levelFile,'rb'))
            self.playerInitialPos = levelFormat.player.rect.center
            
            self.add(*[Platform(p, game) for p in levelFormat.platforms])
            self.exit = Exit(levelFormat.exit, game)
            self.add(self.exit)
            self.add(*[Portal(p, game) for p in levelFormat.buttons])
        else:
            d = pickle.load(file(levelFile, "rb"))
            for o in d["objects"]:
                gameObject = GameObject.fromSaveFormat(o, game)
                self.add(gameObject)
            self.playerInitialPos = d["playerInitialPos"]
        '''
    
    def addGroup(self, cls):
        group = sprite.Group()
        self.groups[cls] = group
        return group
    
    def reset(self):    
        for group in (self.platforms, self.portals):
            for sprite in group.sprites():
                sprite.reset()
        self.exit.reset()
    
    def add(self, *objects):
        LayeredRenderer.add(self, *objects)
            
        for object in objects:
            haveGroup = False
            for cls, group in self.groups.iteritems():
                if isinstance(object, cls):
                    group.add(object)
                    haveGroup = True
            if not haveGroup: raise Exception("no group for " + str(object))
    
    def saveFormat(self):
        return {
            "objects": [o.saveFormat() for o in self.sprites()],
            "playerInitialPos": self.playerInitialPos
        }
        