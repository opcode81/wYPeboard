# (C) 2014 by Dominik Jain (djain@gmx.net)

import os
import pygame
from pygame import sprite

class WhiteboardRenderer(sprite.LayeredUpdates):
    def __init__(self, game):
        sprite.LayeredUpdates.__init__(self)
        
        self.game = game
        
        self.userObjects = sprite.Group()
        self.uiObjects = sprite.Group()
        
        #sprite.LayeredUpdates.add(self, self.userObjects, self.uiObjects)
        
        self.setBackgroundSize(self.game.screen.get_size())
    
    def add(self, *objects):
        sprite.LayeredUpdates.add(self, *objects)
        for object in objects:
            if object.isUserObject:
                self.userObjects.add(object)
            else:
                self.uiObjects.add(object)
    
    def setBackgroundSize(self, size):
        self.background = pygame.Surface(self.game.screen.get_size())
        self.background.fill((255,255,255))
        self.game.screen.blit(self.background, [0,0])    
    
    def draw(self):
        self.clear(self.game.screen, self.background)
        things = sprite.LayeredUpdates.draw(self, self.game.screen)
        pygame.display.update(things)
        pygame.display.flip()
    