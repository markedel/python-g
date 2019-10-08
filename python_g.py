# Python-g main module
import tkinter as tk
import icon
from PIL import Image, ImageDraw, ImageTk, ImageWin
import time

windowBgColor = (128, 128, 128, 255)
defaultWindowSize = (800, 800)
dragThreshold = 2

SHIFT_MASK = 0x001
CTRL_MASK = 0x004
LEFT_MOUSE_MASK = 0x100
RIGHT_MOUSE_MASK = 0x200

# Notes on window drawing:
#
# Tkinter canvas can't handle individual images for each icon.  After about
# 4000 pixmaps, it breaks and dies.  Drawing directly to the screen is also
# problematic.  Here, we have a Windows-only solution, provided by ImageWin
# module of pillow.  This is a kind-of messed up module which gets very little
# use due to bugs and poor documentation.  While it doesn't give us direct
# access to the windows framebuffer, it does allow us to copy data there from
# a PIL image in a two-step process that is sufficiently fast for the purposes
# of this program.

def combineRects(rect1, rect2):
    "Find the minimum rectangle enclosing rect1 and rect2"
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    return min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)

def msTime():
    "Return a millisecond-resolution timestamp"
    return int(time.process_time() * 1000)

def makeRect(pos1, pos2):
    "Make a rectangle tuple from two points (our rectangles are ordered)"
    x1, y1 = pos1
    x2, y2 = pos2
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

class Window:
    def __init__(self, master, size=None):
        self.top = tk.Toplevel(master)
        self.top.bind("<Destroy>", self.destroyCb)
        self.top.title("Python-G")
        self.frame = tk.Frame(self.top)
        self.menubar = tk.Menu(self.frame)
        self.icons = []
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New", command=self.newCb)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=menu)
        menu.add_command(label="Cut")
        menu.add_command(label="Copy")
        menu.add_command(label="Paste")
        self.top.config(menu=self.menubar)
        if size is None:
            size = defaultWindowSize
        width, height = size
        self.imgFrame = tk.Frame(self.frame, bg="", width=width, height=height)
        self.imgFrame.bind("<Expose>", self.exposeCb)
        self.imgFrame.bind("<Configure>", self.configureCb)
        self.imgFrame.bind("<Button>", self.buttonPressCb)
        self.imgFrame.bind("<ButtonRelease>", self.buttonReleaseCb)
        self.imgFrame.bind("<Motion>", self.motionCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.buttonDownTime = None
        self.buttonDownLoc = None
        self.dragging = None
        self.inRectSelect = False
        self.lastRectSelect = None

        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)
        self.dc = None
        self.dirty = False

    def newCb(self):
        appData.newWindow()

    def configureCb(self, evt):
        "Called when window is initially displayed or resized"
        if evt.width != self.image.width or evt.height != self.image.height:
            print('resizing', evt.width, evt.height)
            self.resize(evt.width, evt.height)
        for ic in self.icons:
            ic.drawIcon()

    def exposeCb(self, evt):
        "Called when a new part of the window is exposed and needs to be redrawn"
        self.refresh()

    def motionCb(self, evt):
        if self.buttonDownTime is None:
            return
        print('motion')
        if self.dragging is None and not self.inRectSelect:
            xDist = abs(evt.x - self.buttonDownLoc[0])
            yDist = abs(evt.y - self.buttonDownLoc[1])
            if xDist + yDist > dragThreshold:
                icons = self.findIconsAt((evt.x, evt.y))
                if len(icons) > 0:
                    self.startDrag(evt, icons)
                else:
                    self.startRectSelect(evt)
        else:
            if self.dragging is not None:
                self.updateDrag(evt)
            elif self.inRectSelect:
                self.updateRectSelect(evt)

    def buttonPressCb(self, evt):
        self.buttonDownTime = msTime()
        self.buttonDownLoc = evt.x, evt.y
        self.buttonDownState = evt.state
        print('button press')

    def buttonReleaseCb(self, evt):
        if self.buttonDownTime is None:
            return
        print('button release')
        if self.dragging is not None:
            self.endDrag()
        elif self.inRectSelect:
            self.endRectSelect()
        elif self.buttonDownState & SHIFT_MASK:
            self.select(evt, 'add')
        elif self.buttonDownState & CTRL_MASK:
            self.select(evt, 'toggle')
        else:
            self.select(evt, 'select')
        self.buttonDownTime = None

    def destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

    def startDrag(self, evt, icons):
        for ic in icons:
            if ic.selected:
                self.dragging = [i for i in self.icons if i.selected]
                break
        else:
            self.dragging = icons
        self.lastDragOffset = (0, 0)
        self.updateDrag(evt)
        print("starting drag", self.dragging)

    def updateDrag(self, evt):
        if self.buttonDownTime is None or not self.dragging:
            return
        print("dragged to", evt.x, evt.y)
        offsetX = evt.x - self.buttonDownLoc[0] - self.lastDragOffset[0]
        offsetY = evt.y - self.buttonDownLoc[1] - self.lastDragOffset[1]
        self.moveIcons(self.dragging, (offsetX, offsetY))
        self.lastDragOffset = evt.x - self.buttonDownLoc[0], evt.y - self.buttonDownLoc[1]

    def endDrag(self):
        print('ending drag')
        self.dragging = None

    def startRectSelect(self, evt):
        self.inRectSelect = True
        self.lastRectSelect = None
        refreshRegion = AccumRects()
        for ic in self.icons:
            if ic.selected:
                refreshRegion.add(ic.rect)
                ic.selected = False
                ic.drawIcon()
                self.refresh(refreshRegion.get())
        self.updateRectSelect(evt)

    def updateRectSelect(self, evt):
        if self.lastRectSelect is not None:
            self._eraseRectSelect()
        newRect = makeRect(self.buttonDownLoc, (evt.x, evt.y))
        redrawRegion = AccumRects()
        for ic in self.icons:
            if ic.selected and not rectsTouch(ic.rect, newRect):
                ic.selected = False
                redrawRegion.add(ic.rect)
                ic.drawIcon()
        selectedIcons = self.findIconsInRegion(newRect)
        for ic in selectedIcons:
            if not ic.selected:
                ic.selected = True
                redrawRegion.add(ic.rect)
                ic.drawIcon()
        self.refresh(redrawRegion.get())
        l, t, r, b = newRect
        hLineImg = Image.new('RGB', (r - l, 1), color=(255, 255, 255, 255))
        vLineImg = Image.new('RGB', (1, b - t), color=(255, 255, 255, 255))
        self.drawImage(hLineImg, (l, t))
        self.drawImage(hLineImg, (l, b))
        self.drawImage(vLineImg, (l, t))
        self.drawImage(vLineImg, (r, t))
        print('updating rect select')
        self.lastRectSelect = newRect

    def _eraseRectSelect(self):
        l, t, r, b = self.lastRectSelect
        self.refresh((l, t, r+1, t+1))
        self.refresh((l, b, r+1, b+1))
        self.refresh((l, t, l+1, b+1))
        self.refresh((r, t, r+1, b+1))

    def endRectSelect(self):
        print('ending rect select')
        self._eraseRectSelect()
        self.inRectSelect = False

    def select(self, evt, op='select'):
        "Make a selection.  Options are 'select', 'toggle' and 'add'"
        refreshRegion = AccumRects()
        if op is 'select':
            for ic in self.icons:
                if ic.selected:
                    refreshRegion.add(ic.rect)
                    ic.selected = False
                    ic.drawIcon()
        selectedIcons = self.findIconsAt((evt.x, evt.y))
        for ic in selectedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
            ic.drawIcon()
        self.refresh(refreshRegion.get())
        print('select')

    def resize(self, width, height):
        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)

    def refresh(self, region=None):
        """Redraw any rectangle (region) of the window from the pseudo-framebuffer
           (self.image).  Redraw the whole window if region==None"""
        if region == None:
            self.drawImage(self.image, (0, 0))
        else:
            self.drawImage(self.image, (region[0], region[1]), region)

    def drawImage(self, image, location, subImage=None):
        "Draw an arbitrary image anywhere in the window"
        if subImage:
            x1, y1, x2, y2 = subImage
            width = x2 - x1
            height = y2 - y1
            image = image.crop(subImage)
        else:
            width = image.width
            height = image.height
        dib = ImageWin.Dib('RGB', (width, height))
        dib.paste(image)
        x, y = location
        # While the documentation says that Dib.draw can take a window handle,
        # it really can't.  If you pass the integer ID, it doesn't know that
        # it has a window handle.  And if you pass it the output from
        # ImageWin.HWND, it tries to use it as an integer and fails.  Here,
        # we're using an undocumented internal function to get the device
        # context from the window ID
        if self.dc is None:
            self.dc = dib.image.getdc(self.imgFrame.winfo_id())
        dib.draw(self.dc, (x, y, x + width, y + height))

    def findIconsInRegion(self, rect):
        return [ic for ic in self.icons if rectsTouch(rect, ic.rect)]

    def findIconsAt(self, loc):
        return [ic for ic in self.icons if pointInRect(loc, ic.rect)]

    def moveIcons(self, icons, offset):
        redrawRect = AccumRects()
        xOffset, yOffset = offset
        for ic in icons:
            redrawRect.add(ic.rect)
            self.icons.remove(ic)
            self.draw.rectangle(ic.rect, fill=windowBgColor)
            x1, y1, x2, y2 = ic.rect
            ic.rect = (x1+xOffset, y1+yOffset, x2+xOffset, y2+yOffset)
        for ic in self.findIconsInRegion(redrawRect.get()):
            if ic is not self:
                ic.drawIcon()
        for ic in icons:
            redrawRect.add(ic.rect)
            ic.drawIcon()
        self.refresh(redrawRect.get())
        self.icons += icons

class AccumRects:
    def __init__(self):
        self.rect = None

    def add(self, rect):
        if self.rect is None:
            self.rect = rect
        else:
            self.rect = combineRects(rect, self.rect)

    def get(self):
        return self.rect

def pointInRect(point, rect):
    l, t, r, b = rect
    x, y = point
    print('pir', l, t, r, b, '  ', x, y, '->', x >= l and x <= r and y <= b and y >= t)
    return x >= l and x <= r and y <= b and y >= t

def rectsTouch(rect1, rect2):
    "Returns true if rectangles rect1 and rect2 overlap"
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    # One is to the right side of the other
    if l1 > r2  or l2 > r1:
        return False
    # One is above the other
    if (t1 > b2 or t2 > b1):
        return False
    return True

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.overrideredirect(1) # Stop vestigial root window from flashing up
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()
        self.frameCount = 0

        window = self.windows[0]
        for x in range(8):
            for y in range(18):
                loc = (x*60, y*20)
                window.icons.append(icon.Icon("Icon %d" % (x*8+y), loc,
                 42, (5, 10), window))
        self.animateIcons = list(window.icons[:80])

    def mainLoop(self):
        #self.root.after(2000, self.animate)
        self.root.mainloop()

    def animate(self):
        print(self.frameCount, msTime())
        self.frameCount += 1
        offset = 1 if self.frameCount % 1000 < 500 else -1
        self.windows[0].moveIcons(self.animateIcons, (offset, offset))
        self.root.after(10, self.animate)

    def removeWindow(self, window):
        self.windows.remove(window)
        if len(self.windows) == 0:
            exit(1)

    def newWindow(self):
        window = Window(self.root)
        self.windows.append(window)

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
