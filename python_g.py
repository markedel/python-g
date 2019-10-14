# Python-g main module
import tkinter as tk
import icon
from PIL import Image, ImageDraw, ImageTk, ImageWin
import time
import compile_eval

windowBgColor = (128, 128, 128, 255)
defaultWindowSize = (800, 800)
dragThreshold = 2

SHIFT_MASK = 0x001
CTRL_MASK = 0x004
LEFT_MOUSE_MASK = 0x100
RIGHT_MOUSE_MASK = 0x300

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
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)
        menu.add_command(label="New", command=self._newCb)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=menu)
        menu.add_command(label="Cut", command = self._cutCb, accelerator="Ctrl+X")
        menu.add_command(label="Copy", command = self._copyCb, accelerator="Ctrl+C")
        menu.add_command(label="Paste", command = self._pasteCb, accelerator="Ctrl+V")
        menu.add_command(label="Delete", command = self._deleteCb, accelerator="Delete")
        self.top.config(menu=self.menubar)
        if size is None:
            size = defaultWindowSize
        width, height = size
        self.imgFrame = tk.Frame(self.frame, bg="", width=width, height=height)
        self.imgFrame.bind("<Expose>", self._exposeCb)
        self.imgFrame.bind("<Configure>", self._configureCb)
        self.imgFrame.bind("<Button-1>", self._buttonPressCb)
        self.imgFrame.bind("<ButtonRelease-1>", self._buttonReleaseCb)
        self.imgFrame.bind('<Button-3>', self._btn3Cb)
        self.imgFrame.bind('<ButtonRelease-3>', self._btn3ReleaseCb)
        self.imgFrame.bind("<Motion>", self._motionCb)
        self.top.bind("<Control-x>", self._cutCb)
        self.top.bind("<Control-c>", self._copyCb)
        self.top.bind("<Control-v>", self._pasteCb)
        self.top.bind("<Delete>", self._deleteCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.popup = tk.Menu(self.imgFrame, tearoff=0)
        self.popup.add_command(label="Cut", command = self._cutCb, accelerator="Ctrl+X")
        self.popup.add_command(label="Copy", command = self._copyCb, accelerator="Ctrl+C")
        self.popup.add_command(label="Paste", command = self._pasteCb, accelerator="Ctrl+V")
        self.popup.add_command(label="Delete", command=self._deleteCb, accelerator="Delete")

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

        self.topIcons = []
        self.image = Image.new('RGB', (width, height), color=windowBgColor)
        self.draw = ImageDraw.Draw(self.image)
        self.dc = None

    def allIcons(self, order="draw"):
        """Iterate over of all icons in the window, in drawing order, "draw", by default,
         but optionally in opposite, "pick", order.  (warning: generator)"""
        for ic in reversed(self.topIcons) if order is "pick" else self.topIcons:
            yield from ic.traverse(order)

    def selectedIcons(self, order="draw"):
        """Return a list of the icons in the window that are currently selected.  Result
        can be returned in "draw" or "pick" order"""
        return [ic for ic in self.allIcons(order) if ic.selected]

    def _btn3Cb(self, evt):
        ic = self.findIconAt(evt.x, evt.y)
        if ic is not None and ic.selected == False:
            self._select(evt)

    def _btn3ReleaseCb(self, evt):
        self.popup.tk_popup(evt.x_root, evt.y_root, 0)

    def _newCb(self):
        appData.newWindow()

    def _configureCb(self, evt):
        "Called when window is initially displayed or resized"
        if evt.width != self.image.width or evt.height != self.image.height:
            self.image = Image.new('RGB', (evt.width, evt.height), color=windowBgColor)
            self.draw = ImageDraw.Draw(self.image)
        for ic in self.allIcons():
            ic.draw()

    def _exposeCb(self, evt):
        "Called when a new part of the window is exposed and needs to be redrawn"
        self.refresh()

    def _motionCb(self, evt):
        if self.buttonDownTime is None or not (evt.state & LEFT_MOUSE_MASK):
            return
        if self.dragging is None and not self.inRectSelect:
            xDist = abs(evt.x - self.buttonDownLoc[0])
            yDist = abs(evt.y - self.buttonDownLoc[1])
            if xDist + yDist > dragThreshold:
                ic = self.findIconAt(evt.x, evt.y)
                if ic is None:
                    self._startRectSelect(evt)
                else:
                    self._startDrag(evt, list(ic.traverse()))
        else:
            if self.dragging is not None:
                self._updateDrag(evt)
            elif self.inRectSelect:
                self._updateRectSelect(evt)

    def _buttonPressCb(self, evt):
        self.buttonDownTime = msTime()
        self.buttonDownLoc = evt.x, evt.y
        self.buttonDownState = evt.state
        ic = self.findIconAt(evt.x, evt.y)
        if ic is None or not ic.selected and not (evt.state & SHIFT_MASK or evt.state & CTRL_MASK):
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

    def _cutCb(self, evt=None):
        self._copyCb()
        self.removeIcons(self.selectedIcons())

    def _copyCb(self, evt=None):
        selectedIcons = self.selectedIcons()
        selectedRect = icon.containingRect(selectedIcons)
        if selectedRect is None:
            return
        xOff, yOff = selectedRect[:2]
        clipIcons = icon.clipboardRepr(findTopIcons(selectedIcons), (-xOff, -yOff))
        clipTxt = " ".join([ic.name for ic in selectedIcons])
        self.top.clipboard_clear()
        self.top.clipboard_append(clipIcons, type='ICONS')
        self.top.clipboard_append(clipTxt, type='STRING')

    def _pasteCb(self, evt=None):
        selectedRect = icon.containingRect(self.selectedIcons())
        if selectedRect is not None:
            px, py = selectedRect[:2]
            self.removeIcons(self.selectedIcons())
        elif evt is not None:
            px, py = evt.x, evt.y
        else:
            px, py = 10, 10
        try:
            iconString = self.top.clipboard_get(type="ICONS")
        except:
            iconString = None
        if iconString is not None:
            pastedIcons = icon.iconsFromClipboardString(iconString, self, (px, py))
        else:
            # Couldn't get icon data.  Use string on clipboard
            try:
                text = self.top.clipboard_get(type="STRING")
            except:
                return
            # Try to parse the string as Python code
            pastedIcons = compile_eval.parsePasted(text, self, (px, py))
            if pastedIcons is None:
                pastedIcons = [icon.IdentIcon(repr(text), self, (px, py))]
        redrawRect = AccumRects()
        for pastedTopIcon in pastedIcons:
            self.topIcons.append(pastedTopIcon)
            for ic in pastedTopIcon.traverse():
                ic.selected = True
                ic.draw() # No need to clip or erase, all drawn on top
                redrawRect.add(ic.rect)
        self.refresh(redrawRect.get())

    def _deleteCb(self, evt=None):
        self.removeIcons(self.selectedIcons())

    def _startDrag(self, evt, icons):
        # Determine what icons to drag: if a selected icon was clicked, drag all of
        # the selected icons.  Otherwise, drag anything that was clicked
        for ic in icons:
            if ic.selected:
                self.dragging = self.selectedIcons()
                break
        else:
            self.dragging = icons
        # Remove the icons from the window image and handle the resulting detachments
        # re-layouts, and redrawing.
        self.removeIcons(self.dragging)
        # Dragging parent icons away from their children may require re-layout of the
        # (moving) parent icons
        for ic in findTopIcons(self.dragging):
            if ic.needsLayout():
                ic.layout()
        # For top performance, make a separate image containing the moving icons against
        # a transparent background, which can be redrawn with imaging calls, only.
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
            ic.draw(self.dragImage, (l-xOff, t-yOff))
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

    def _endDrag(self):
        l, t, r, b = self.lastDragImageRegion
        xOff = l - self.dragImageOffset[0]
        yOff = t - self.dragImageOffset[1]
        # self.dragging icons are not stored hierarchically, but are in draw order
        for ic in self.dragging:
            ic.rect = offsetRect(ic.rect, xOff, yOff)
            ic.draw()
        self.topIcons += findTopIcons(self.dragging) # ... do snapping here
        self.dragging = None
        # A refresh, here, is technically unnecessary, but after all that's been written
        # to the display, it's better to ensure it's really in sync with the image pixmap
        self.refresh()

    def _startRectSelect(self, evt):
        self.inRectSelect = True
        self.lastRectSelect = None
        self.rectSelectInitialStates = {ic:ic.selected for ic in self.allIcons()}
        self._updateRectSelect(evt)

    def _updateRectSelect(self, evt):
        toggle = evt.state & CTRL_MASK
        newRect = makeRect(self.buttonDownLoc, (evt.x, evt.y))
        if self.lastRectSelect is None:
            combinedRegion = newRect
        else:
            combinedRegion = combineRects(newRect, self.lastRectSelect)
            self._eraseRectSelect()
        redrawRegion = AccumRects()
        changedIcons = []
        for ic in self.findIconsInRegion(combinedRegion):
            if rectsTouch(newRect, ic.rect):
                newSelect = (not self.rectSelectInitialStates[ic]) if toggle else True
            else:
                newSelect = self.rectSelectInitialStates[ic]
            if ic.selected != newSelect:
                ic.selected = newSelect
                redrawRegion.add(ic.rect)
                changedIcons.append(ic)
        for ic in self.allIcons():
            ic.draw(clip=redrawRegion.get())
        self.refresh(redrawRegion.get())
        l, t, r, b = newRect
        hLineImg = Image.new('RGB', (r - l, 1), color=(255, 255, 255, 255))
        vLineImg = Image.new('RGB', (1, b - t), color=(255, 255, 255, 255))
        self.drawImage(hLineImg, (l, t))
        self.drawImage(hLineImg, (l, b))
        self.drawImage(vLineImg, (l, t))
        self.drawImage(vLineImg, (r, t))
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
        """Select or toggle the top icon being pointed at, and bring it to the top.
           Options are 'select', 'toggle' and 'add'"""
        if op is 'select':
            self.unselectAll()
        refreshRegion = AccumRects()
        ic = self.findIconAt(evt.x, evt.y)
        if ic is None:
            return
        changedIcons = list(ic.traverse())
        #... bring these icons to the top: self.bringToTop(changedIcons)
        for ic in changedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
        for ic in changedIcons:
            ic.draw(clip=refreshRegion.get())
        self.refresh(refreshRegion.get())

    def unselectAll(self):
        refreshRegion = AccumRects()
        selectedIcons = self.selectedIcons()
        if len(selectedIcons) == 0:
            return
        for ic in selectedIcons:
            refreshRegion.add(ic.rect)
            ic.selected = False
        for ic in selectedIcons:
            ic.draw(clip=refreshRegion.get())
        self.refresh(refreshRegion.get())

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
        if width == 0 or height == 0:
            return
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
        return [ic for ic in self.allIcons() if rectsTouch(rect, ic.rect)]

    def findIconAt(self, x, y):
        for ic in self.allIcons(order="pick"):
            if ic.touchesPosition(x, y):
                return ic
        return None

    def removeIcons(self, icons):
        "Remove icons from window icon list redraw affected areas of the display"
        if len(icons) == 0:
            return
        deletedDict = {ic:True for ic in icons}
        detachList = []
        redrawRegion = AccumRects()
        for ic in icons:
            redrawRegion.add(ic.rect)
        for ic in self.allIcons():
            for child in ic.children:
                if ic in deletedDict and child not in deletedDict:
                    detachList.append((ic, child))
                elif ic not in deletedDict and child in deletedDict:
                    detachList.append((ic, child))
        newTopIcons = [ic for ic in self.topIcons if ic not in deletedDict]
        for ic, child in detachList:
            ic.detach(child)
            if child not in deletedDict:
                newTopIcons.append(child)
        self.topIcons = newTopIcons
        for ic in self.topIcons:
            if ic.needsLayout():
                redrawRegion.add(ic.hierRect())
                ic.layout()
                redrawRegion.add(ic.hierRect())
        self.clearBgRect(redrawRegion.get())
        for ic in self.findIconsInRegion(redrawRegion.get()):
            ic.draw(clip=redrawRegion.get())
        self.refresh(redrawRegion.get())

    def clearBgRect(self, rect):
        """Clear but don't refresh a rectangle of the window"""
        # Fill rectangle seems to go one beyond
        l, t, r, b = rect
        self.draw.rectangle((l, t, r-1, b-1), fill=windowBgColor)

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

def rectsTouch(rect1, rect2):
    "Returns true if rectangles rect1 and rect2 overlap"
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    # One is to the right side of the other
    if l1 > r2  or l2 > r1:
        return False
    # One is above the other
    if t1 > b2 or t2 > b1:
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
        # for x in range(40):
        #     for y in range(90):
        #         loc = (x*60, y*20)
        #         iconType = icon.FnIcon if x % 2 else  icon.IdentIcon
        #         window.topIcons.append(iconType("Icon %d" % (x*14+y), window, loc))

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


def findTopIcons(icons):
    iconDir = {ic:True for ic in icons}
    for ic in icons:
        for child in ic.children:
            iconDir[child] = False
    return [ic for ic, isTop in iconDir.items() if isTop]

def dumpHier(ic, indent=""):
    print(indent + ic.name)
    for child in ic.children:
        dumpHier(child, indent+"  ")

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()