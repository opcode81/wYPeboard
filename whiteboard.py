import wx
import os
import thread
import traceback
import sys
import numpy
from pprint import pprint
import pickle
import time
import logging

# deferred pygame imports
global pygame
global canvas
global renderer
global objects

logging.basicConfig(level=logging.DEBUG)

class SDLPanel(wx.Panel):
    def __init__(self, parent, ID, tplSize):
        global pygame, level, renderer, objects
        wx.Panel.__init__(self, parent, ID, size=tplSize)
        self.Fit()

        # initialize pygame-related stuff
        os.environ['SDL_WINDOWID'] = str(self.GetHandle())
        os.environ['SDL_VIDEODRIVER'] = 'windib'
        import pygame  # this has to happen after setting the environment variables.
        import canvas
        import renderer
        import objects
        pygame.display.init()
        screen = pygame.display.set_mode(tplSize)

        # initialize level viewer
        self.screen = screen
        self.viewer = Viewer(screen, tplSize, parent)
        self.canvas = canvas.Canvas(self.viewer)
        self.viewer.setCanvas(self.canvas)

        # start pygame thread
        thread.start_new_thread(self.viewer.mainLoop, ())

    def __del__(self):
        self.viewer.running = False


class Camera(object):
    def __init__(self, pos, game):
        self.translate = numpy.array([-game.width / 2, -game.height / 2])
        self.pos = pos + self.translate

    def update(self, game):
        return self.pos

    def offset(self, o):
        self.pos += o


class Viewer(object):
    def __init__(self, screen, size, app):
        self.screen = screen
        self.width, self.height = size
        self.running = False
        self.renderer = renderer.GameRenderer(self)
        self.camera = Camera((0, 0), self)
        self.app = app
        self.objectsById = {}
        self.userCursors = {}

    def setCanvas(self, canvas):
        self.canvas = canvas
        self.renderer.add(self.canvas)

        self.scroll = False
        self.selectedObject = None
        self.activeTool = None

    def update(self):
        self.camera.update(self)
        self.renderer.update(self)

    def draw(self):
        self.renderer.draw()

    def mainLoop(self):
        self.running = True
        try:
            while self.running:
                for event in pygame.event.get():
                    # log(event)

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        x, y = event.pos
                        if event.button == 3:
                            self.onRightMouseButtonDown(x, y)
                        elif event.button == 1:
                            self.onLeftMouseButtonDown(x, y)

                    if event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 3:
                            self.onRightMouseButtonUp()
                        elif event.button == 1:
                            self.onLeftMouseButtonUp()

                    if event.type == pygame.MOUSEMOTION:
                        self.onMouseMove(*(event.pos + event.rel))

                self.update()
                self.draw()

        except:
            e, v, tb = sys.exc_info()
            print v
            traceback.print_tb(tb)

    def setObjects(self, objects):
        for o in self.getObjects():
            o.kill()
        for o in objects:
            self.addObject(o)

    def getObjects(self):
        return self.canvas.userObjects.sprites()

    def addObject(self, object):
        self.objectsById[object.id] = object
        self.canvas.add(object)

    def deleteObjects(self, *ids):
        deletedIds = []
        for id in ids:
            obj = self.objectsById.get(id)
            if obj is not None:
                obj.kill()
                del self.objectsById[id]
                deletedIds.append(id)
        return deletedIds

    def moveObjects(self, offset, *ids):
        for id in ids:
            obj = self.objectsById.get(id)
            if obj is not None:
                obj.offset(*offset)

    def addUser(self, name):
        sprite = objects.ImageFromResource(os.path.join("img", "HandPointer.png"), {"wrect": pygame.Rect(0, 0, 0, 0)}, self)
        self.addObject(sprite)
        self.userCursors[name] = sprite
        return sprite

    def moveUserCursor(self, userName, pos):
        sprite = self.userCursors.get(userName)
        if sprite is not None:
            sprite.pos = pos

    def onRightMouseButtonDown(self, x, y):
        self.scroll = True

    def onLeftMouseButtonDown(self, x, y):
        if self.activeTool is None:  # select object
            matches = filter(lambda o: o.rect.collidepoint((x, y)), self.canvas.userObjects.sprites())
            if len(matches) > 0:
                self.selectedObject = matches[0]
                #log("selected", self.selectedObject)

        else:
            self.activeTool.active = True
            pos = numpy.array([x, y]) + self.camera.pos
            createdObject = self.activeTool.startPos(pos[0], pos[1])
            if createdObject is not None:
                self.selectedObject = createdObject
                self.addObject(createdObject)

    def onRightMouseButtonUp(self):
        self.scroll = False

    def onLeftMouseButtonUp(self):
        if self.activeTool is not None:
            self.activeTool.end()
            self.activeTool.active = False
        #self.activeTool = None
        self.selectedObject = None

    def onMouseMove(self, x, y, dx, dy):
        pos = numpy.array([x, y]) + self.camera.pos

        if self.scroll:
            self.camera.offset(numpy.array([-dx, -dy]))

        elif self.activeTool is None:  # move selected object
            if self.selectedObject is not None:
                self.selectedObject.offset(dx, dy)

        elif self.activeTool.active:
            self.activeTool.addPos(*pos)

        self.app.onCursorMoved(pos)

class Tool(object):
    def __init__(self, name, viewer):
        self.name = name
        self.viewer = viewer
        self.camera = viewer.camera
        self.app = viewer.app
        self.obj = None
        self.active = False

    def startPos(self, x, y):
        pass

    def addPos(self, x, y):
        pass

    def screenPoint(self, x, y):
        return numpy.array([x, y]) - self.camera.pos

    def end(self):
        self.obj = None

class SelectTool(Tool):
    def __init__(self, viewer):
        Tool.__init__(self, "select", viewer)
        self.selectedObjects = None
        self.selectMode = True

    def startPos(self, x, y):
        self.pos1 = self.screenPoint(x, y)
        self.pos2 = self.pos1
        self.offset = numpy.array([0, 0])

    def addPos(self, x, y):
        self.pos2= self.screenPoint(x, y)
        if not self.selectMode:
            offset = self.pos2 - self.pos1
            self.offset += offset
            self.pos1 = self.pos2
            for o in self.selectedObjects:
                o.offset(*offset)

    def end(self):
        if self.selectMode:
            width = self.pos2[0] - self.pos1[0]
            height = self.pos2[1] - self.pos1[1]
            self.selectedObjects = filter(lambda o: o.rect.colliderect(pygame.Rect(self.pos1[0], self.pos1[1], width, height)), self.viewer.canvas.userObjects.sprites())
            log.debug("selected: %s", str(self.selectedObjects))
        else:
            self.app.onObjectsMoved(self.offset, *[o.id for o in self.selectedObjects])
        self.selectMode = not self.selectMode

class RectTool(Tool):
    def __init__(self, viewer):
        Tool.__init__(self, "rectangle", viewer)

    def startPos(self, x, y):
        self.obj = objects.Rectangle({"wrect": pygame.Rect(x, y, 10, 10)}, self.viewer)
        return self.obj

    def addPos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

    def end(self):
        if self.obj is not None: self.app.onObjectCreationCompleted(self.obj)
        super(RectTool, self).end()

class EraserTool(Tool):
    def __init__(self, viewer):
        Tool.__init__(self, "erase", viewer)

    def startPos(self, x, y):
        self.erase(x, y)

    def erase(self, x, y):
        x, y = self.screenPoint(x, y)
        sprites = self.viewer.canvas.sprites() # TODO
        #print sprites
        matches = filter(lambda o: o.rect.collidepoint((x, y)), sprites)
        #print "eraser matches:", matches
        if len(matches) > 0:
            ids = [o.id for o in matches]
            self.app.deleteObjects(*ids)
            #for sprite in matches:
            #    sprite.kill()

    def addPos(self, x, y):
        self.erase(x, y)

class PenTool(Tool):
    def __init__(self, viewer):
        Tool.__init__(self, "pen", viewer)
        self.lineWidth = 3
        self.margin = 2*self.lineWidth
        self.color = (0, 0, 0)
        self.inputCache = []
        self.lastProcessTime = 0

    def startPos(self, x, y):
        self.lineStartPos = numpy.array([x, y])
        surface = pygame.Surface((self.margin, self.margin))#, pygame.SRCALPHA)
        surface.fill((255, 0, 255))
        surface.set_colorkey((255, 0, 255))
        self.surface = surface
        self.translateOrigin = numpy.array([-x, -y])
        self.obj = objects.Scribble({"wrect": pygame.Rect(x - self.margin/2, y - self.margin/2, self.margin, self.margin), "image": surface.convert()}, self.viewer)
        self.minX = self.maxX = x
        self.minY = self.maxY = y
        return self.obj

    def addPos(self, x, y):
        if self.obj is None: return

        self.inputCache.append((x, y))

        t = time.time()
        if t - self.lastProcessTime >= 0.02:
            self.processInputs()
            self.lastProcessTime = t

    def processInputs(self):
        if self.obj is None: return

        padLeft = 0
        padTop = 0

        oldWidth = self.surface.get_width()
        oldHeight = self.surface.get_height()
        newWidth = oldWidth
        newHeight = oldHeight

        for x, y in self.inputCache:
            # determine growth
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

            # create new larger surface and copy old surface content
            margin = self.margin
            newWidth += growLeft + growRight
            newHeight += growBottom + growTop

        if newWidth > oldWidth or newHeight > oldHeight:
            #print "newDim: (%d, %d)" % (newWidth, newHeight)
            surface = pygame.Surface((newWidth, newHeight))#, pygame.SRCALPHA)
            surface.fill((255, 0, 255))
            surface.set_colorkey((255, 0, 255))
            surface.blit(self.surface, (padLeft, padTop))
            self.surface = surface

        # apply new surface and translate pos
        self.obj.setSurface(self.surface)
        self.obj.offset(-padLeft, -padTop)

        for x, y in self.inputCache:
            self.draw(x, y)

        self.inputCache = []

    def draw(self, x, y):
        # draw line
        margin = self.margin
        self.translateOrigin = -self.obj.pos + numpy.array([-margin, -margin])
        #print "translateOrigin=%s" % str(self.translateOrigin)
        marginTranslate = numpy.array([margin, margin])
        pos1 = self.lineStartPos + self.translateOrigin + marginTranslate
        pos2 = numpy.array([x, y]) + self.translateOrigin + marginTranslate
        #print "drawing from %s to %s" % (str(pos1), str(pos2))
        pygame.draw.line(self.surface, self.color, pos1, pos2, self.lineWidth)
        self.lineStartPos = numpy.array([x, y])

    def end(self):
        self.processInputs()
        if self.obj is not None: self.app.onObjectCreationCompleted(self.obj)
        super(PenTool, self).end()

class Whiteboard(wx.Frame):
    def __init__(self, strTitle, size=(800, 600)):
        parent = None
        tplSize = size
        wx.Frame.__init__(self, parent, wx.ID_ANY, strTitle, size=tplSize, style=wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX)
        self.pnlSDL = SDLPanel(self, -1, tplSize)

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.SetMenuBar(self.frame_menubar)
        # - file Menu
        self.file_menu = wx.Menu()
        self.file_menu.Append(1, "&Open", "Open from file..")
        self.file_menu.Append(2, "&Save", "Open a file..")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(3, "&Close", "Quit")
        self.Bind(wx.EVT_MENU, self.onOpen, id=1)
        self.Bind(wx.EVT_MENU, self.onSave, id=2)
        self.Bind(wx.EVT_MENU, self.onExit, id=3)
        self.frame_menubar.Append(self.file_menu, "File")

        self.viewer = self.pnlSDL.viewer

        toolbar = wx.Panel(self)
        self.toolbar = toolbar
        tools = [
             SelectTool(self.viewer),
             PenTool(self.viewer),
             RectTool(self.viewer),
             EraserTool(self.viewer)
        ]
        box = wx.BoxSizer(wx.HORIZONTAL)
        for i, tool in enumerate(tools):
            btn = wx.Button(toolbar, label=tool.name)
            self.Bind(wx.EVT_BUTTON, lambda evt, tool=tool: self.onSelectTool(tool), btn)
            box.Add(btn)
        toolbar.SetSizer(box)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(toolbar, flag=wx.EXPAND | wx.BOTTOM, border=0)
        sizer.Add(self.pnlSDL, 1, flag=wx.EXPAND)
        self.SetSizer(sizer)

    def onSelectTool(self, tool):
        tool.active = False
        self.viewer.activeTool = tool
        log.debug("selected tool %s" % tool.name)

    def onOpen(self, event):
        dlg = wx.FileDialog(self, "Choose a file", os.path.join(".", "assets", "levels"), "", "*.wyb", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = file(path, "rb")
            d = pickle.load(f)
            f.close()
            self.viewer.setObjects([objects.deserialize(o, self.viewer) for o in d["objects"]])

    def onSave(self, event):
        dlg = wx.FileDialog(self, "Choose a file", os.path.join(".", "assets", "levels"), "", "*.wyb", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = file(path, "wb")
            pickle.dump({"objects": [o.serialize() for o in self.viewer.getObjects()]}, f)
            f.close()

    def onExit(self, event):
        self.viewer.running = False
        sys.exit(0)

    def addObject(self, object):
        self.viewer.addObject(object)

    def onObjectCreationCompleted(self, object):
        pass

    def onObjectsDeleted(self, *objectIds):
        pass

    def onObjectsMoved(self, offset, *objectIds):
        pass

    def onCursorMoved(self, pos):
        pass

    def deleteObjects(self, *objectIds):
        deletedIds = self.viewer.deleteObjects(*objectIds)
        if len(deletedIds) > 0:
            self.onObjectsDeleted(*deletedIds)

    def moveObjects(self, offset, *objectIds):
        self.viewer.moveObjects(offset, *objectIds)

    def addUser(self, name):
        self.viewer.addUser(name)

    def moveUserCursor(self, userName, pos):
        self.viewer.moveUserCursor(userName, pos)

    def errorDialog(self, errormessage):
        """Display a simple error dialog.
        """
        edialog = wx.MessageDialog(self, errormessage, 'Error', wx.OK | wx.ICON_ERROR)
        edialog.ShowModal()

    def questionDialog(self, message, title = "Error"):
        """Displays a yes/no dialog, returning true if the user clicked yes, false otherwise
        """
        return wx.MessageDialog(self, message, title, wx.YES_NO | wx.ICON_QUESTION).ShowModal() == wx.ID_YES

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = Whiteboard("wYPeboard")
    frame.Show()
    app.MainLoop()
