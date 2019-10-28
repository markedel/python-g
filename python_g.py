# Copyright Mark Edel  All rights reserved
# Python-g main module
import tkinter as tk
import typing
import icon
from PIL import Image, ImageDraw, ImageWin, ImageGrab
import time
import compile_eval

#windowBgColor = (255, 255,255)
windowBgColor = (128, 128, 128)
defaultWindowSize = (800, 800)
dragThreshold = 2

# Tkinter event modifiers
SHIFT_MASK = 0x001
CTRL_MASK = 0x004
LEFT_ALT_MASK = 0x008
RIGHT_ALT_MASK = 0x080
LEFT_MOUSE_MASK = 0x100
RIGHT_MOUSE_MASK = 0x300

DOUBLE_CLICK_TIME = 300

SNAP_DIST = 8

startUpTime = time.monotonic()

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
    """Find the minimum rectangle enclosing rect1 and rect2"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    return min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)

def msTime():
    """Return a millisecond-resolution timestamp"""
    return int(time.monotonic() - startUpTime * 1000)

def makeRect(pos1, pos2):
    """Make a rectangle tuple from two points (our rectangles are ordered)"""
    x1, y1 = pos1
    x2, y2 = pos2
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

def exposedRegions(oldRect, newRect):
    """List rectangles covering space needing to be filled when oldRect becomes newRect"""
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
    return l+xOff, t+yOff, r+xOff, b+yOff

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
        menu.add_command(label="Cut", command=self._cutCb, accelerator="Ctrl+X")
        menu.add_command(label="Copy", command=self._copyCb, accelerator="Ctrl+C")
        menu.add_command(label="Paste", command=self._pasteCb, accelerator="Ctrl+V")
        menu.add_command(label="Delete", command=self._deleteCb, accelerator="Delete")
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
        self.top.bind("<BackSpace>", self._backspaceCb)
        self.top.bind("<Escape>", self._cancelCb)
        self.top.bind("<Return>", self._enterCb)
        self.top.bind("<Key>", self._keyCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.popup = tk.Menu(self.imgFrame, tearoff=0)
        self.popup.add_command(label="Cut", command=self._cutCb, accelerator="Ctrl+X")
        self.popup.add_command(label="Copy", command=self._copyCb, accelerator="Ctrl+C")
        self.popup.add_command(label="Paste", command=self._pasteCb, accelerator="Ctrl+V")
        self.popup.add_command(label="Delete", command=self._deleteCb, accelerator="Delete")

        self.buttonDownTime = None
        self.buttonDownLoc = None
        self.buttonDownState = None
        self.doubleClickFlag = False
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
        self.entryIcon = None
        self.entryIconOnMouse = False

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
        if ic is not None and ic.selected is False:
            self._select(evt)

    def _btn3ReleaseCb(self, evt):
        self.popup.tk_popup(evt.x_root, evt.y_root, 0)

    def _newCb(self):
        appData.newWindow()

    def _configureCb(self, evt):
        """Called when window is initially displayed or resized"""
        if evt.width != self.image.width or evt.height != self.image.height:
            self.image = Image.new('RGB', (evt.width, evt.height), color=windowBgColor)
            self.draw = ImageDraw.Draw(self.image)
        for ic in self.allIcons():
            ic.draw()

    def _exposeCb(self, _evt):
        """Called when a new part of the window is exposed and needs to be redrawn"""
        self.refresh()

    def _keyCb(self, evt):
        if evt.state & (CTRL_MASK | LEFT_ALT_MASK | RIGHT_ALT_MASK):
            return
        char = typing.tkCharFromEvt(evt)
        if char is None:
             return
        if self.entryIcon is not None:
            # There's already an entry icon.  Feed it the character
            self.entryIcon.addChar(char)
            self._redisplayChangedEntryIcon(evt)
            return
        selectedIcons = findTopIcons(self.selectedIcons())
        self.entryIcon = typing.EntryIcon(window=self, location=(0, 0),
            initialString=char)
        if len(selectedIcons) == 1:
            # A single icon was selected.  Replace it and its children
            self.entryIconOnMouse = False
            replaceIcon = selectedIcons[0]
            iconParent = self.parentOf(replaceIcon)
            iconParent.replaceChild(self.entryIcon, iconParent.siteOf(replaceIcon))
            self._redisplayChangedEntryIcon()
        else:
            # Either no icons were selected, or multiple icons were selected (so
            # we don't know what to replace).  Put the entry icon on the pointer.
            # Below is temporary code until the "empty cursor" is implemented.
            # It is unlikely we will ever summon a complete entry icon to the mouse.
            self.entryIconOnMouse = True
            x = evt.x - 6
            y = evt.y - self.entryIcon.outSiteOffset[1]
            self.entryIcon.rect = offsetRect(self.entryIcon.rect, x, y)
            self.buttonDownLoc = (evt.x, evt.y)  # drag needs starting location
            self._startDrag(evt, [self.entryIcon], needRemove=False)

    def _redisplayChangedEntryIcon(self, evt=None):
        # If the size of the entry icon changes it requests re-layout of parent.  Figure
        # out if layout needs to change and do so, otherwise just redraw the entry icon
        if self.entryIconOnMouse:
            if self.entryIcon.layoutDirty:
                self.entryIcon.layout()
                self._cancelDrag()
                self._startDrag(evt, [self.entryIcon], needRemove=False)
            else:
                self.entryIcon.draw(self.dragImage)
            return
        layoutNeeded = False
        redrawRegion = AccumRects(self.entryIcon.rect)
        for ic in self.topIcons:
            if ic.needsLayout():
                layoutNeeded = True
                redrawRegion.add(ic.hierRect())
                ic.layout()
                redrawRegion.add(ic.hierRect())
        # Redraw the areas affected by the updated layouts
        if layoutNeeded:
            self.clearBgRect(redrawRegion.get())
            for ic in self.findIconsInRegion(redrawRegion.get()):
                ic.draw(clip=redrawRegion.get())
            self.refresh(redrawRegion.get())
        else:
            self.entryIcon.draw()

    def _motionCb(self, evt):
        if self.dragging is not None:
            self._updateDrag(evt)
            return
        if self.buttonDownTime is None or not (evt.state & LEFT_MOUSE_MASK):
            return
        if self.dragging is None and not self.inRectSelect:
            btnX, btnY = self.buttonDownLoc
            if abs(evt.x - btnX) + abs(evt.y - btnY) > dragThreshold:
                ic = self.findIconAt(btnX, btnY)
                if ic is None:
                    # If nothing was clicked, start a rectangular selection
                    self._startRectSelect(evt)
                elif ic.selected:
                    # If a selected icon was clicked, drag all of the selected icons
                    self._startDrag(evt, self.selectedIcons())
                else:
                    # Otherwise, drag the icon that was clicked
                    if self.doubleClickFlag:
                        self._startDrag(evt, [ic])  # double-click drag single icon
                    else:
                        self._startDrag(evt, list(self.findLeftOuterIcon(ic).traverse()))
        elif self.inRectSelect:
            self._updateRectSelect(evt)

    def _buttonPressCb(self, evt):
        if self.dragging:
            self._endDrag()
            self.entryIconOnMouse = False
            return
        if self.buttonDownTime is not None:
            if msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
                self.doubleClickFlag = True
                return
        self.buttonDownTime = msTime()
        self.buttonDownLoc = evt.x, evt.y
        self.buttonDownState = evt.state
        self.doubleClickFlag = False
        ic = self.findIconAt(evt.x, evt.y)
        if ic is None or not ic.selected and not (evt.state & SHIFT_MASK or evt.state & CTRL_MASK):
            self.unselectAll()

    def _buttonReleaseCb(self, evt):
        if self.buttonDownTime is None:
            return
        if self.dragging is not None:
            self._endDrag()
            self.buttonDownTime = None
        elif self.inRectSelect:
            self._endRectSelect()
            self.buttonDownTime = None
        elif self.doubleClickFlag:
            if msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
                self._execute(self.findIconAt(*self.buttonDownLoc), evt)
            self.buttonDownTime = None
        elif msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
            # In order to handle double-click, button release actions are run not done
            # until we know that a double-click can't still happen (_delayedBtnUpActions).
            delay = DOUBLE_CLICK_TIME - (msTime() - self.buttonDownTime)
            self.frame.after(delay, self._delayedBtnUpActions, evt)
        else:
            # Do the button-release actions immediately, double-click wait has passed.
            self._delayedBtnUpActions(evt)

    def _delayedBtnUpActions(self, evt):
        """Button-up actions (which may be delayed to wait for possible double-click)."""
        if self.doubleClickFlag:
            return  # Second click occurred, don't do the delayed action
        if self.buttonDownState & SHIFT_MASK:
            self._select(evt, 'add')
        elif self.buttonDownState & CTRL_MASK:
            self._select(evt, 'toggle')
        else:
            self._select(evt, 'select')
        self.buttonDownTime = None

    def _destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

    def _cutCb(self, _evt=None):
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
                text = None
            # Try to parse the string as Python code
            if text is not None:
                pastedIcons = compile_eval.parsePasted(text, self, (px, py))
                if pastedIcons is None:
                    pastedIcons = [icon.IdentIcon(repr(text), self, (px, py))]
            else:
                clipImage = ImageGrab.grabclipboard()
                if clipImage is None:
                    return
                pastedIcons = [icon.ImageIcon(clipImage, self, (px, py))]
        redrawRect = AccumRects()
        for pastedTopIcon in pastedIcons:
            self.topIcons.append(pastedTopIcon)
            for ic in pastedTopIcon.traverse():
                ic.draw()  # No need to clip or erase, all drawn on top
                redrawRect.add(ic.rect)
        self.refresh(redrawRect.get())

    def _deleteCb(self, _evt=None):
        self.removeIcons(self.selectedIcons())

    def _backspaceCb(self, _evt=None):
        if self.entryIcon is None:
            self.removeIcons(self.selectedIcons())
        else:
            self.entryIcon.backspace()
            self._redisplayChangedEntryIcon()

    def _cancelCb(self, _evt=None):
        if self.entryIcon is not None:
            self.removeIcons([self.entryIcon])
            self.entryIcon = None
        self._cancelDrag()

    def _enterCb(self, _evt=None):
        if self.entryIcon is not None:
            enteredIcons = compile_eval.parsePasted(self.entryIcon.text, self, (0, 0))
            if enteredIcons is None:
                self.removeIcons([self.entryIcon])
            else:
                self.replaceIcons(self.entryIcon, enteredIcons[0])
            self.entryIcon = None
            self.entryIconOnMouse = False
            self._cancelDrag()

    def _startDrag(self, evt, icons, needRemove=True):
        self.dragging = icons
        # Remove the icons from the window image and handle the resulting detachments
        # re-layouts, and redrawing.
        if needRemove:
            self.removeIcons(self.dragging)
        # Dragging parent icons away from their children may require re-layout of the
        # (moving) parent icons
        topDraggingIcons = findTopIcons(self.dragging)
        for ic in topDraggingIcons:
            ic.becomeTopLevel()
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
        # Construct a master snap list for all mating sites between stationary and
        # dragged icons
        draggingOutputs = []
        for dragIcon in topDraggingIcons:
            for ic, (x, y), siteIdx in dragIcon.snapLists().get("output", []):
                draggingOutputs.append(((x-xOff, y-yOff), ic))
        stationaryInputs = []
        for topIcon in self.topIcons:
            for winIcon in topIcon.traverse():
                isTopIcon = winIcon is topIcon
                snapLists = winIcon.snapLists(atTop=isTopIcon)
                for ic, pos, idx in snapLists.get("input", []):
                    stationaryInputs.append((pos, ic, ("input", idx)))
                for ic, pos, idx in snapLists.get("insertInput", []):
                    stationaryInputs.append((pos, ic, ("insertInput", idx)))
        self.snapList = []
        for si in stationaryInputs:
            (sx, sy), sIcon, sSite = si
            for do in draggingOutputs:
                (dx, dy), dIcon = do
                self.snapList.append((sx-dx, sy-dy, sIcon, dIcon, sSite))
        self.snapped = None
        self._updateDrag(evt)

    def _updateDrag(self, evt):
        if not self.dragging:
            return
        x = self.dragImageOffset[0] + evt.x - self.buttonDownLoc[0]
        y = self.dragImageOffset[1] + evt.y - self.buttonDownLoc[1]
        # If the drag results in mating sites being within snapping distance, change the
        # drag position to mate them exactly (snap them together)
        self.snapped = None
        nearest = SNAP_DIST + 1
        for sx, sy, inIcon, outIcon, site in self.snapList:
            dist = abs(x-sx) + abs(y-sy)
            if dist < nearest:
                nearest = dist
                x = sx
                y = sy
                self.snapped = (inIcon, outIcon, site)
        # Erase the old drag image
        width = self.dragImage.width
        height = self.dragImage.height
        dragImageRegion = (x, y, x+width, y+height)
        if self.lastDragImageRegion is not None:
            for r in exposedRegions(self.lastDragImageRegion, dragImageRegion):
                self.refresh(r)
        # Draw the image of the moving icons in their new locations directly to the
        # display (leaving self.image clean).  This makes dragging fast by eliminating
        # individual icon drawing of while the user is dragging.
        dragImage = self.image.crop(dragImageRegion)
        dragImage.paste(self.dragImage, mask=self.dragImage)
        self.drawImage(dragImage, (x, y))
        self.lastDragImageRegion = dragImageRegion

    def _endDrag(self):
        l, t, r, b = self.lastDragImageRegion
        xOff = l - self.dragImageOffset[0]
        yOff = t - self.dragImageOffset[1]
        # self.dragging icons are not stored hierarchically, but are in draw order
        topDraggedIcons = findTopIcons(self.dragging)
        for ic in topDraggedIcons:
            ic.becomeTopLevel()
        redrawRegion = AccumRects()
        for ic in self.dragging:
            ic.rect = offsetRect(ic.rect, xOff, yOff)
            redrawRegion.add(ic.rect)
        self.topIcons += topDraggedIcons
        if self.snapped is not None:
            # The drag ended in a snap.  Attach or replace existing icons at the site
            parentIcon, childIcon, site = self.snapped
            self.topIcons.remove(childIcon)  # Added above in case there were others
            toDelete = parentIcon.childAt(site)
            redrawRegion.add(parentIcon.hierRect())
            if toDelete is not None:
                redrawRegion.add(childIcon.hierRect())
            if site[0] in ("input", "attrOut"):
                parentIcon.replaceChild(childIcon, site)
            elif site[0] == "insertInput":
                parentIcon.insertChildren([childIcon], site)
            # Redo layouts for all affected (all the way to the top)
            for ic in self.topIcons:
                if ic.needsLayout():
                    redrawRegion.add(ic.hierRect())
                    ic.layout()
                    redrawRegion.add(ic.hierRect())
            # Redraw the areas affected by the updated layouts
            self.clearBgRect(redrawRegion.get())
        for ic in self.findIconsInRegion(redrawRegion.get()):
            ic.draw(clip=redrawRegion.get())
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None
        # Refresh the entire display.  While refreshing a smaller area is technically
        # possible, after all the dragging and drawing, it's prudent to ensure that the
        # display remains in sync with the image pixmap
        self.refresh()

    def _cancelDrag(self):
        # Not properly cancelling drag, yet, just dropping the icons being dragged
        if self.dragging is None:
            return
        self.clearBgRect(self.lastDragImageRegion)
        for ic in self.findIconsInRegion(self.lastDragImageRegion):
            ic.draw(clip=self.lastDragImageRegion)
        self.refresh(self.lastDragImageRegion)
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None

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
            if ic.touchesRect(newRect):
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

    def _execute(self, iconToExecute, evt):
        if iconToExecute is None:
            return
        iconToExecute = self.findLeftOuterIcon(iconToExecute)
        result = iconToExecute.execute()
        resultIcons = compile_eval.parsePasted(repr(result), self, (0, 0))
        if resultIcons is None:
            resultIcons = [icon.IdentIcon(repr(result), self, (0, 0))]
        left, top, right, bottom = resultIcons[0].hierRect()
        ctrXOff = (right - left) // 2
        ctrYOff = (bottom - top) // 2
        for ic in resultIcons:
            ic.rect = offsetRect(ic.rect, evt.x - ctrXOff, evt.y - ctrYOff)
        self._startDrag(evt, resultIcons, needRemove=False)

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
        for ic in changedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
        for ic in self.findIconsInRegion(refreshRegion.get()):
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
        for ic in self.findIconsInRegion(refreshRegion.get()):
            ic.draw(clip=refreshRegion.get())
        self.refresh(refreshRegion.get())

    def refresh(self, region=None):
        """Redraw any rectangle (region) of the window from the pseudo-framebuffer
           (self.image).  Redraw the whole window if region==None"""
        if region is None:
            self.drawImage(self.image, (0, 0))
        else:
            self.drawImage(self.image, (region[0], region[1]), region)

    def drawImage(self, image, location, subImage=None):
        """Draw an arbitrary image anywhere in the window, ignoring the window image"""
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

    def findLeftOuterIcon(self, ic):
        """Selection method for execution and dragging:  See description in icon.py"""
        for topIcon in self.topIcons:
            leftIcon = icon.findLeftOuterIcon(ic, topIcon, btnPressLoc=self.buttonDownLoc)
            if leftIcon is not None:
                return leftIcon
        return None

    def removeIcons(self, icons):
        """Remove icons from window icon list redraw affected areas of the display"""
        if len(icons) == 0:
            return
        # deletedDict is used to quickly determine if an icon is on the deleted list
        deletedDict = {ic:True for ic in icons}
        detachList = []
        redrawRegion = AccumRects()
        for ic in icons:
            redrawRegion.add(ic.rect)
        # Find and unlink child icons from parents at deletion boundary
        addTopIcons = []
        for ic in self.allIcons():
            for child in ic.children():
                if ic in deletedDict and child not in deletedDict:
                    detachList.append((ic, child))
                    addTopIcons.append(child)
                    redrawRegion.add(child.hierRect())
                elif ic not in deletedDict and child in deletedDict:
                    detachList.append((ic, child))
        for ic, child in detachList:
            ic.replaceChild(None, ic.siteOf(child))
        # Update the window's top-icon list to remove deleted icons and add those that
        # have become top icons via deletion of their parents (bring those to the front)
        newTopIcons = []
        for ic in self.topIcons:
            if ic not in deletedDict:
                newTopIcons.append(ic)
        self.topIcons = newTopIcons + addTopIcons
        # Redo layouts of icons affected by detachment of children
        for ic in self.topIcons:
            if ic.needsLayout():
                redrawRegion.add(ic.hierRect())
                ic.layout()
                redrawRegion.add(ic.hierRect())
        # Redraw the area affected by the deletion
        self.clearBgRect(redrawRegion.get())
        for ic in self.findIconsInRegion(redrawRegion.get()):
            ic.draw(clip=redrawRegion.get())
        self.refresh(redrawRegion.get())

    def replaceIcons(self, toReplace, replaceWith):
        iconParent = self.parentOf(toReplace)
        if iconParent is None:
            self.removeIcons([toReplace])
            replaceWith.rect = offsetRect(replaceWith.rect, toReplace.rect[0], toReplace.rect[1])
            replaceWith.layoutDirty = True
            self.topIcons.append(replaceWith)
            redrawRegion = AccumRects(replaceWith.rect)
        else:
            iconParent.replaceChild(replaceWith, iconParent.siteOf(toReplace))
            redrawRegion = AccumRects(toReplace.rect)
        for ic in self.topIcons:
            if ic.needsLayout():
                redrawRegion.add(ic.hierRect())
                ic.layout()
                redrawRegion.add(ic.hierRect())
        # Redraw the areas affected by the updated layouts
        self.clearBgRect(redrawRegion.get())
        for ic in self.findIconsInRegion(redrawRegion.get()):
            ic.draw(clip=redrawRegion.get())
        self.refresh(redrawRegion.get())

    def clearBgRect(self, rect):
        """Clear but don't refresh a rectangle of the window"""
        # Fill rectangle seems to go one beyond
        l, t, r, b = rect
        self.draw.rectangle((l, t, r-1, b-1), fill=windowBgColor)

    def parentOf(self, child, fromIcon=None):
        """Find the parent of a given icon.  Don't use this casually.  Because we don't
        have a parent link, this is an exhaustive search of the hierarchy."""
        if fromIcon is None:
            icons = self.topIcons
        else:
            icons = fromIcon.children()
        for ic in icons:
            if ic == child:
                return fromIcon
            result = self.parentOf(child, fromIcon=ic)
            if result is not None:
                return result
        return None

class AccumRects:
    """Make one big rectangle out of all rectangles added."""
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if self.rect is None:
            self.rect = rect
        else:
            self.rect = combineRects(rect, self.rect)

    def get(self):
        """Return the enclosing rectangle.  Returns None if no rectangles were added"""
        return self.rect

def rectsTouch(rect1, rect2):
    """Returns true if rectangles rect1 and rect2 overlap"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    # One is to the right side of the other
    if l1 > r2 or l2 > r1:
        return False
    # One is above the other
    if t1 > b2 or t2 > b1:
        return False
    return True

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.overrideredirect(1)  # Stop vestigial root window from flashing up
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()
        self.frameCount = 0

        # window = self.windows[0]
        # for x in range(40):
        #     for y in range(90):
        #         loc = (x*60, y*20)
        #         iconType = icon.FnIcon if x % 2 else  icon.IdentIcon
        #         window.topIcons.append(iconType("Icon %d" % (x*14+y), window, loc))

    def mainLoop(self):
        # self.root.after(2000, self.animate)
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
        for child in ic.children():
            iconDir[child] = False
    return [ic for ic, isTop in iconDir.items() if isTop]

def dumpHier(ic, indent=""):
    print(indent + ic.name)
    for child in ic.children():
        dumpHier(child, indent+"  ")

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
