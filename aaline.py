# (C) 2014 by Dominik Jain (djain@gmx.net)

import pygame
import logging

log = logging.getLogger(__name__)

def aaline(surface, colour, pos1, pos2, lineWidth=3):
    log.debug("aaline: %s -> %s", pos1, pos2)
    if True: #pos1[0] != pos2[0] and pos1[1] != pos2[1]:
        x1, y1 = pos1
        x2, y2 = pos2
        offset = (lineWidth - 1) / 2
        if x2 == x1:
            m = 1000
        else:
            m = float(y2 - y1) / (x2 - x1)
        #log.debug("m = %s", m)
        if m > 0:
            if m >= 1:
                offs1 = (-(offset), 0)
                offs2 = (offset, 0)
            else:
                offs1 = (lineWidth-2, -(offset))
                offs2 = (0, offset)
        else:
            if m <= -1:
                offs1 = (-offset, 0)
                offs2 = (offset, 0)
            else:
                offs1 = (0, -offset)
                offs2 = (lineWidth-2, offset)
        #log.debug("offsets: %s, %s", offs1, offs2)
        pygame.draw.aaline(surface, colour, (pos1[0]+offs1[0], pos1[1]+offs1[1]), (pos2[0]+offs1[0], pos2[1]+offs1[1]))
        pygame.draw.aaline(surface, colour, (pos1[0]+offs2[0], pos1[1]+offs2[1]), (pos2[0]+offs2[0], pos2[1]+offs2[1]))
    pygame.draw.line(surface, colour, pos1, pos2, lineWidth)

if __name__=='__main__':
    lines = []
    lines.append(((10,10), (90,90)))
    lines.append(((10,90), (90,10)))
    lines.append(((10,90), (20,10)))
    lines.append(((10,10), (20,90)))
    lines.append(((10,10), (90,30)))
    lines.append(((10,30), (90,10)))
    lines.append([[29, 7], [28, 7], [27, 7], [26, 7], [25, 7], [21, 5], [19, 5], [15, 3], [13, 3], [8, 3], [5, 4], [3, 7]])
    for l in lines:
        surface = pygame.Surface((100,100), flags=0) # NOTE: does not work with SRCALPHA! Why?
        surface.fill((255,255,255))
        colour = (0,0,0)
        for i in range(len(l)-1):
            pos1, pos2 = l[i], l[i+1]
            aaline(surface, colour, pos1, pos2)    
        #pygame.draw.aaline(surface, colour, (20,10), (80,70))
        pygame.image.save(surface, "aatest%s.png" % str(l))
