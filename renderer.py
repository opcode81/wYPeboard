import os
import pygame
from pygame import sprite

SpriteLayer = {} # TODO use it
for layer, name in enumerate(["background", "foreground", "ghost", "avatar"]):
    SpriteLayer[name] = layer


class HierarchicalGroup(object):
    ''' a group of sprites that is a aware of the groups/renderers it is
    added to, enabling a hierarchy of sprites to be maintained '''
    
    def __init__(self):
        self.containingGroups = []
    
    def add(self, *spritesAndGroups):
        for sprite in spritesAndGroups:
            if isinstance(sprite, HierarchicalGroup):
                sprite.containingGroups.append(self)
        for group in self.containingGroups:
            group.add(*spritesAndGroups)


class LayeredRenderer(sprite.LayeredUpdates, HierarchicalGroup):
    def __init__(self):
        HierarchicalGroup.__init__(self)
        sprite.LayeredUpdates.__init__(self)
    
    def add(self, *spritesAndGroups):
        sprite.LayeredUpdates.add(self, *spritesAndGroups)
        HierarchicalGroup.add(self, *spritesAndGroups)
    
    # TODO add remove


class SpriteGroup(sprite.Group, HierarchicalGroup):
    def __init__(self):
        HierarchicalGroup.__init__(self)
        sprite.Group.__init__(self)
    
    def add(self, *spritesAndGroups):
        sprite.Group.add(self, *spritesAndGroups)
        HierarchicalGroup.add(self, *spritesAndGroups)


class GameRenderer(LayeredRenderer):
    ''' the main game renderer '''
    
    def __init__(self, game):
        LayeredRenderer.__init__(self)
        
        self.game = game
        
        #self.background = pygame.image.load(os.path.join('assets', 'images', 'background2.png')).convert()
        #self.background = pygame.transform.scale(self.background, (game.width, game.height))
    
        self.setBackgroundSize(self.game.screen.get_size())
    
    def setBackgroundSize(self, size):
        self.background = pygame.Surface(self.game.screen.get_size())
        self.background.fill((255,255,255))
        self.game.screen.blit(self.background, [0,0])    
    
    def draw(self):
        self.clear(self.game.screen, self.background)
        things = sprite.LayeredUpdates.draw(self, self.game.screen)
        pygame.display.update(things)
        pygame.display.flip()
    