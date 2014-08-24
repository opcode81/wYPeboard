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
import platform

# deferred pygame imports
global pygame
global canvas
global renderer
global objects

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

class SDLPanel(wx.Panel):
    def __init__(self, parent, ID, tplSize, caption, isInline):
        global pygame, level, renderer, objects
        wx.Panel.__init__(self, parent, ID, size=tplSize)
        self.Fit()

        # initialize pygame-related stuff
        if isInline:
            os.environ['SDL_WINDOWID'] = str(self.GetHandle())
            os.environ['SDL_VIDEODRIVER'] = 'windib'
        import pygame  # this has to happen after setting the environment variables.
        import canvas
        import renderer
        import objects
        pygame.display.init()   
        pygame.font.init()
        #import pygame.freetype
        #pygame.freetype.init()
        screen = pygame.display.set_mode(tplSize)
        pygame.display.set_caption(caption)

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
            clock = pygame.time.Clock()
            while self.running:
                try:
                    clock.tick(60)
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
                                self.onLeftMouseButtonUp(*event.pos)
    
                        if event.type == pygame.MOUSEMOTION:
                            self.onMouseMove(*(event.pos + event.rel))
    
                    self.update()
                    self.draw()
                except:
                    log.warning("rendering pass failed")
                    e, v, tb = sys.exc_info()
                    print v
                    traceback.print_tb(tb)

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
        sprite = objects.ImageFromResource(os.path.join("img", "HandPointer.png"), {"rect": pygame.Rect(0, 0, 0, 0)}, self)
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

    def onLeftMouseButtonUp(self, x, y):
        pos = numpy.array([x, y]) + self.camera.pos
        if self.activeTool is not None:
            self.activeTool.end(*pos)
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
    def __init__(self, name, wb):
        self.name = name
        self.wb = wb
        self.viewer = wb.viewer
        self.camera = wb.viewer.camera
        self.obj = None
        self.active = False

    def toolbarItem(self, parent, onActivate):
        btn = wx.Button(parent, label=self.name)
        btn.Bind(wx.EVT_BUTTON, lambda evt: onActivate(self), btn)
        return btn

    def startPos(self, x, y):
        pass

    def addPos(self, x, y):
        pass

    def screenPoint(self, x, y):
        return numpy.array([x, y]) - self.camera.pos

    def end(self, x, y):
        self.obj = None

class SelectTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "select", wb)
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

    def end(self, x, y):
        if self.selectMode:
            width = self.pos2[0] - self.pos1[0]
            height = self.pos2[1] - self.pos1[1]
            self.selectedObjects = filter(lambda o: o.rect.colliderect(pygame.Rect(self.pos1[0], self.pos1[1], width, height)), self.viewer.canvas.userObjects.sprites())
            log.debug("selected: %s", str(self.selectedObjects))
        else:
            self.wb.onObjectsMoved(self.offset, *[o.id for o in self.selectedObjects])
        self.selectMode = not self.selectMode

class RectTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "rectangle", wb)

    def startPos(self, x, y):
        self.obj = objects.Rectangle({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        return self.obj

    def addPos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

    def end(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj)
        super(RectTool, self).end(x, y)

class EraserTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "eraser", wb)

    def startPos(self, x, y):
        self.erase(x, y)

    def erase(self, x, y):
        x, y = self.screenPoint(x, y)
        sprites = self.viewer.canvas.userObjects.sprites() # TODO
        #log.debug(sprites
        matches = filter(lambda o: o.rect.collidepoint((x, y)), sprites)
        log.debug("eraser matches: %s", matches)
        if len(matches) > 0:
            ids = [o.id for o in matches]
            self.wb.deleteObjects(*ids)

    def addPos(self, x, y):
        self.erase(x, y)

class PenTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "pen", wb)
        self.lineWidth = 3
        self.margin = 2*self.lineWidth
        self.inputBuffer = []
        self.lastProcessTime = 0

    def startPos(self, x, y):
        self.lineStartPos = numpy.array([x, y])
        self.colour = self.wb.getColour()
        surface = pygame.Surface((self.margin, self.margin))#, pygame.SRCALPHA)
        surface.fill((255, 0, 255))
        surface.set_colorkey((255, 0, 255))
        self.surface = surface
        self.translateOrigin = numpy.array([-x, -y])
        self.obj = objects.Scribble({"rect": pygame.Rect(x - self.margin/2, y - self.margin/2, self.margin, self.margin), "image": surface.convert()}, self.viewer)
        self.minX = self.maxX = x
        self.minY = self.maxY = y
        return self.obj

    def addPos(self, x, y):
        #log.debug("pen at %s" % str((x,y)))
        if self.obj is None: return

        self.inputBuffer.append((x, y))

        t = time.time()
        if t - self.lastProcessTime >= 0.0: # buffering of inputs currently disabled
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
            surface = pygame.Surface((newWidth, newHeight))#, pygame.SRCALPHA)
            surface.fill((255, 0, 255))
            surface.set_colorkey((255, 0, 255))
            surface.blit(self.surface, (padLeft, padTop))
            self.surface = surface

        # apply new surface and translate pos
        self.obj.setSurface(self.surface)
        self.obj.offset(-padLeft, -padTop)

        for x, y in self.inputBuffer:
            self.draw(x, y)

        self.inputBuffer = []

    def draw(self, x, y):
        # draw line
        margin = self.margin
        self.translateOrigin = -self.obj.pos + numpy.array([-margin, -margin])
        #print "translateOrigin=%s" % str(self.translateOrigin)
        marginTranslate = numpy.array([margin, margin])
        pos1 = self.lineStartPos + self.translateOrigin + marginTranslate
        pos2 = numpy.array([x, y]) + self.translateOrigin + marginTranslate
        #print "drawing from %s to %s" % (str(pos1), str(pos2))
        pygame.draw.line(self.surface, self.colour, pos1, pos2, self.lineWidth)
        self.lineStartPos = numpy.array([x, y])

    def end(self, x, y):
        self.processInputs()
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj)
        super(PenTool, self).end(x, y)

class ColourTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "colour", wb)

    def toolbarItem(self, parent, onActivate):
        self.picker = wx.ColourPickerCtrl(parent)
        return self.picker

    def getColour(self):
        return self.picker.GetColour()

class TextEditDialog(wx.Frame):
    # TODO unfinished
    def __init__(self, parent, **kw):
        #wx.Dialog.__init__(self, parent, **kw)
        wx.Frame.__init__(self, parent)

        self.textControl = wx.TextCtrl(self, 1, style=wx.TE_MULTILINE)
       
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Ok')
        closeButton = wx.Button(self, label='Close')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.textControl, proportion=1, 
            flag=wx.ALL|wx.EXPAND, border=5)
        vbox.Add(hbox2, 
            flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

        self.SetSizer(vbox)
        
        okButton.Bind(wx.EVT_BUTTON, self.OnClose)
        closeButton.Bind(wx.EVT_BUTTON, self.OnClose)
        
        self.SetSize((250, 200))
        self.SetTitle("Change Color Depth")
        
    def OnClose(self, e):
        self.Destroy()

class TextTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "text", wb)
    
    def end(self, x, y):
        wx.CallAfter(self.enterText, x, y)
    
    def enterText(self, x, y):
        dlg = wx.TextEntryDialog(self.wb, "Please enter the text", "Text", "") # TODO
        dlg.ShowModal()
        text = dlg.GetValue()
        self.obj = objects.Text({"pos": (x, y), "text": text, "colour": self.wb.getColour(), "fontName": "Arial", "fontSize": 12}, self.viewer)
        self.wb.addObject(self.obj)

class Whiteboard(wx.Frame):
    def __init__(self, strTitle, canvasSize=(800, 600)):
        self.isMultiWindow = platform.system() != "Windows"
        parent = None
        size = canvasSize if not self.isMultiWindow else (80, 200)
        if not self.isMultiWindow:
            style = wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX
        else:
            style = (wx.STAY_ON_TOP | wx.CAPTION) & ~wx.SYSTEM_MENU
        wx.Frame.__init__(self, parent, wx.ID_ANY, strTitle, size=size, style=style)
        self.pnlSDL = SDLPanel(self, -1, canvasSize, strTitle, not self.isMultiWindow)
        self.clipboard = wx.Clipboard()

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.SetMenuBar(self.frame_menubar)
        # - file Menu        
        self.file_menu = wx.Menu()
        self.file_menu.Append(101, "&Open", "Open contents from file")
        self.file_menu.Append(102, "&Save", "Save contents to file")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(103, "&Exit", "Quit the application")
        self.Bind(wx.EVT_MENU, self.onOpen, id=101)
        self.Bind(wx.EVT_MENU, self.onSave, id=102)
        self.Bind(wx.EVT_MENU, self.onExit, id=103)
        # - edit menu
        self.edit_menu = wx.Menu()
        self.edit_menu.Append(201, "&Paste image", "Paste an image")
        self.Bind(wx.EVT_MENU, self.onPasteImage, id=201)
        
        menus = ((self.file_menu, "File"), (self.edit_menu, "Edit"))
        
        if not self.isMultiWindow:
            for menu, name in menus:
                self.frame_menubar.Append(menu, name)
        else:
            joinedMenu = wx.Menu()
            for i, (menu, name) in enumerate(menus):
                joinedMenu.AppendMenu(i, name, menu)
            self.frame_menubar.Append(joinedMenu, "Menu")

        self.viewer = self.pnlSDL.viewer

        toolbar = wx.Panel(self)
        self.toolbar = toolbar
        self.colourTool = ColourTool(self)
        tools = [
             SelectTool(self),
             self.colourTool,
             PenTool(self),
             RectTool(self),
             TextTool(self),
             EraserTool(self)
        ]
        box = wx.BoxSizer(wx.HORIZONTAL if not self.isMultiWindow else wx.VERTICAL)
        for i, tool in enumerate(tools):
            control = tool.toolbarItem(toolbar, self.onSelectTool)
            box.Add(control, 1, flag=wx.EXPAND)
        toolbar.SetSizer(box)
                
        if self.isMultiWindow:
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(toolbar, flag=wx.EXPAND)
            self.pnlSDL.Hide()
            sizer.Add(self.pnlSDL) # the panel must be added because clicks will not get through otherwise
            self.SetSizerAndFit(sizer)
            self.pnlSDL.Show()
        else:
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(toolbar, flag=wx.EXPAND | wx.BOTTOM, border=0)
            sizer.Add(self.pnlSDL, 1, flag=wx.EXPAND)
            self.SetSizer(sizer)

    def onSelectTool(self, tool):
        tool.active = False
        self.viewer.activeTool = tool
        log.debug("selected tool %s" % tool.name)
    
    def getColour(self):
        return self.colourTool.getColour()

    def onOpen(self, event):
        log.debug("selected 'open'")
        dlg = wx.FileDialog(self, "Choose a file", os.path.join(".", "assets", "levels"), "", "*.wyb", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = file(path, "rb")
            d = pickle.load(f)
            f.close()
            self.viewer.setObjects([objects.deserialize(o, self.viewer) for o in d["objects"]])

    def onSave(self, event):
        log.debug("selected 'save'")
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
    
    def onPasteImage(self, event):
        bdo = wx.BitmapDataObject()
        self.clipboard.Open()
        self.clipboard.GetData(bdo)
        self.clipboard.Close()
        bmp = bdo.GetBitmap()
        #print bmp.SaveFile("foo.png", wx.BITMAP_TYPE_PNG)        
        #buf = bytearray([0]*4*bmp.GetWidth()*bmp.GetHeight())
        #bmp.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        #image = pygame.image.frombuffer(buf, (bmp.getWidth(), bmp.getHeight()), "RBGA")
        data = bmp.ConvertToImage().GetData()
        image = pygame.image.fromstring(data, (bmp.GetWidth(), bmp.GetHeight()), "RGB")
        obj = objects.Image({"image": image, "rect": image.get_rect()}, self.viewer, isUserObject=True)
        self.addObject(obj)

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
    
    def setObjects(self, objects):
        self.viewer.setObjects(objects)
    
    def getObjects(self):
        return self.viewer.getObjects()

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
    app = wx.App(False)
    frame = Whiteboard("wYPeboard")
    frame.Show()
    app.MainLoop()
