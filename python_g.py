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

def exposedRegions(oldRect, newRect):
    "List rectangles covering space needing to be filled when oldRect becomes newRect"
    lo, to, ro, bo = oldRect
    ln, tn, rn, bn = newRect
    exposed = []
    if lo < ln:
        exposed.append((lo, to, ln, bo))
    if ro > rn:
        exposed.append((rn, to, ro, bo))
    if to < tn:
        exposed.append((lo, to, ro, tn))
    if bo > bn:
        exposed.append((lo, bn, ro, bo))
    return exposed

def offsetRect(rect, xOff, yOff):
    l, t, r, b = rect
    return (l+xOff, t+yOff, r+xOff, b+yOff)

class Window:
    def __init__(self, master, size=None):
        self.top = tk.Toplevel(master)
        self.top.bind("<Destroy>", self._destroyCb)
        self.top.title("Python-G")
        self.frame = tk.Frame(self.top)
        self.menubar = tk.Menu(self.frame)
        self.icons = []
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New", command=self._newCb)
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
        self.imgFrame.bind("<Expose>", self._exposeCb)
        self.imgFrame.bind("<Configure>", self._configureCb)
        self.imgFrame.bind("<Button>", self._buttonPressCb)
        self.imgFrame.bind("<ButtonRelease>", self._buttonReleaseCb)
        self.imgFrame.bind("<Motion>", self._motionCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.buttonDownTime = None
        self.buttonDownLoc = None
        self.buttonDownState = None
        self.dragging = None
        self.dragImageOffset = None
        self.dragImage = None
        self.lastDragImageRegion = None
        self.inRectSelect = False
        self.lastRectSelect = None
        self.rectSelectInitialStates = {}

        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)
        self.dc = None

    def _newCb(self):
        appData.newWindow()

    def _configureCb(self, evt):
        "Called when window is initially displayed or resized"
        if evt.width != self.image.width or evt.height != self.image.height:
            self.resize(evt.width, evt.height)
        for ic in self.icons:
            ic.drawIcon()

    def _exposeCb(self, evt):
        "Called when a new part of the window is exposed and needs to be redrawn"
        self.refresh()

    def _motionCb(self, evt):
        if self.buttonDownTime is None:
            return
        if self.dragging is None and not self.inRectSelect:
            xDist = abs(evt.x - self.buttonDownLoc[0])
            yDist = abs(evt.y - self.buttonDownLoc[1])
            if xDist + yDist > dragThreshold:
                icons = self.findIconsAt((evt.x, evt.y))
                if len(icons) > 0:
                    self._startDrag(evt, icons)
                else:
                    self._startRectSelect(evt)
        else:
            if self.dragging is not None:
                self._updateDrag(evt)
            elif self.inRectSelect:
                self._updateRectSelect(evt)

    def _buttonPressCb(self, evt):
        self.buttonDownTime = msTime()
        self.buttonDownLoc = evt.x, evt.y
        self.buttonDownState = evt.state
        print('button press')
        selected = [ic for ic in self.findIconsAt((evt.x, evt.y)) if ic.selected]
        if len(selected) == 0 and not (evt.state & SHIFT_MASK or evt.state & CTRL_MASK):
            self.unselectAll()

    def _buttonReleaseCb(self, evt):
        if self.buttonDownTime is None:
            return
        if self.dragging is not None:
            self._endDrag()
        elif self.inRectSelect:
            self._endRectSelect()
        elif self.buttonDownState & SHIFT_MASK:
            self._select(evt, 'add')
        elif self.buttonDownState & CTRL_MASK:
            self._select(evt, 'toggle')
        else:
            self._select(evt, 'select')
        self.buttonDownTime = None

    def _destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

    def _startDrag(self, evt, icons):
        for ic in icons:
            if ic.selected:
                self.dragging = [i for i in self.icons if i.selected]
                break
        else:
            self.dragging = icons
        self.removeIcons(self.dragging)
        moveRegion = AccumRects()
        for ic in self.dragging:
            moveRegion.add(ic.rect)
        el, et, er, eb = moveRegion.get()
        xOff = el
        yOff = et
        self.dragImageOffset = xOff, yOff
        self.dragImage = Image.new('RGBA', (er - xOff, eb - yOff), color=(0, 0, 0, 0))
        self.lastDragImageRegion = None
        for ic in self.dragging:
            l, t = ic.rect[:2]
            ic.drawIcon(self.dragImage, (l-xOff, t-yOff))
        self._updateDrag(evt)

    def _updateDrag(self, evt):
        if self.buttonDownTime is None or not self.dragging:
            return
        x = self.dragImageOffset[0] + evt.x - self.buttonDownLoc[0]
        y = self.dragImageOffset[1] + evt.y - self.buttonDownLoc[1]
        width = self.dragImage.width
        height = self.dragImage.height
        dragImageRegion = (x, y, x+width, y+height)
        if self.lastDragImageRegion is not None:
            for r in exposedRegions(self.lastDragImageRegion, dragImageRegion):
                self.refresh(r)
        dragImage = self.image.crop(dragImageRegion)
        dragImage.paste(self.dragImage, mask=self.dragImage)
        self.drawImage(dragImage, (x, y))
        self.lastDragImageRegion = dragImageRegion
        print("dragged to", evt.x, evt.y)

    def _endDrag(self):
        l, t, r, b = self.lastDragImageRegion
        xOff = l - self.dragImageOffset[0]
        yOff = t - self.dragImageOffset[1]
        for ic in self.dragging:
            ic.rect = offsetRect(ic.rect, xOff, yOff)
            ic.drawIcon()
        self.icons += self.dragging
        self.dragging = None
        # A refresh, here, is technically unnecessary, but after all that's been written to
        # the display, it's better to ensure it's really in sync with the image pixmap
        self.refresh()

    def _startRectSelect(self, evt):
        self.inRectSelect = True
        self.lastRectSelect = None
        self.rectSelectInitialStates = {ic:ic.selected for ic in self.icons}
        self._updateRectSelect(evt)

    def _updateRectSelect(self, evt):
        toggle = evt.state & CTRL_MASK
        if self.lastRectSelect is not None:
            self._eraseRectSelect()
        newRect = makeRect(self.buttonDownLoc, (evt.x, evt.y))
        redrawRegion = AccumRects()
        for ic in self.icons:
            if ic.selected != self.rectSelectInitialStates[ic] and not rectsTouch(ic.rect, newRect):
                ic.selected = self.rectSelectInitialStates[ic]
                redrawRegion.add(ic.rect)
                ic.drawIcon()
        selectedIcons = self.findIconsInRegion(newRect)
        for ic in selectedIcons:
            newSelect = (not self.rectSelectInitialStates[ic]) if toggle else True
            if ic.selected != newSelect:
                ic.selected = newSelect
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

    def _endRectSelect(self):
        self._eraseRectSelect()
        self.inRectSelect = False

    def _select(self, evt, op='select'):
        "Make a selection.  Options are 'select', 'toggle' and 'add'"
        if op is 'select':
            self.unselectAll()
        refreshRegion = AccumRects()
        for ic in self.findIconsAt((evt.x, evt.y)):
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
            ic.drawIcon()
        self.refresh(refreshRegion.get())

    def unselectAll(self):
        refreshRegion = AccumRects()
        for ic in self.icons:
            if ic.selected:
                refreshRegion.add(ic.rect)
                ic.selected = False
                ic.drawIcon()
        if refreshRegion.get() is not None:
            self.refresh(refreshRegion.get())

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
        "Draw an arbitrary image anywhere in the window, ignoring the window image"
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

    def removeIcons(self, icons):
        "Remove icons from window icon list redraw affected areas of the display"
        redrawRegion = AccumRects()
        for ic in icons:
            self.icons.remove(ic)
            redrawRegion.add(ic.rect)
        self.draw.rectangle(redrawRegion.get(), fill=windowBgColor)
        for ic in self.findIconsInRegion(redrawRegion.get()):
            ic.drawIcon()
            redrawRegion.add(ic.rect)
        self.refresh(redrawRegion.get())

class AccumRects:
    "Make one big rectangle out of all rectangles added."
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if self.rect is None:
            self.rect = rect
        else:
            self.rect = combineRects(rect, self.rect)

    def get(self):
        "Return the enclosing rectangle.  Returns None if no rectangles were added"
        return self.rect

def pointInRect(point, rect):
    l, t, r, b = rect
    x, y = point
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
        for x in range(40):
            for y in range(90):
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
