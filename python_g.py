# Copyright Mark Edel  All rights reserved
# Python-g main module
import tkinter as tk
import typing
import icon
from PIL import Image, ImageDraw, ImageWin, ImageGrab
import time
import compile_eval
import tkinter.messagebox

#windowBgColor = (255, 255,255)
windowBgColor = (128, 128, 128)
defaultWindowSize = (800, 800)
dragThreshold = 2

# Tkinter event modifiers
SHIFT_MASK = 0x001
CTRL_MASK = 0x004
LEFT_ALT_MASK = 0x20000
RIGHT_ALT_MASK = 0x40000 # Note that numeric keypad divide comes up with this on mine
LEFT_MOUSE_MASK = 0x100
RIGHT_MOUSE_MASK = 0x300

DOUBLE_CLICK_TIME = 300

CURSOR_BLINK_RATE = 500

SNAP_DIST = 8

SITE_SELECT_DIST = 4

# How far to the right of icons to deposit the result of executing them
RESULT_X_OFFSET = 5

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
        self.top.bind("<FocusIn>", self._focusInCb)
        self.top.bind("<FocusOut>", self._focusOutCb)
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
        self.cursor = typing.Cursor(self, None)
        self.execResultPositions = {}

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
            self._select(evt, self.findIconAt(evt.x, evt.y))

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
        if evt.state & (CTRL_MASK | LEFT_ALT_MASK):
            return
        char = typing.tkCharFromEvt(evt)
        if char is None:
             return
        # If there's a cursor displayed somewhere, use it
        if self.cursor.type == "text":
            # If it's an active entry icon, feed it the character
            oldLoc = self.entryIcon.rect
            self.entryIcon.addChar(char)
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
            return
        elif self.cursor.type == "icon":
            self._insertEntryIconAtCursor(char)
            return
        elif self.cursor.type == "window":
            self.entryIcon = typing.EntryIcon(None, None, window=self,
             location=self.cursor.pos)
            self.entryIcon.addChar(char)
            if self.entryIcon is not None:
                self.topIcons.append(self.entryIcon)
                self.cursor.setToEntryIcon()
            self._redisplayChangedEntryIcon()
            return
        # If there's an appropriate selection, use that
        selectedIcons = findTopIcons(self.selectedIcons())
        if len(selectedIcons) == 1:
            # A single icon was selected.  Replace it and its children
            replaceIcon = selectedIcons[0]
            iconParent = self.parentOf(replaceIcon)
            self.entryIcon = typing.EntryIcon(iconParent, iconParent.siteOf(replaceIcon),
             window=self)
            iconParent.replaceChild(self.entryIcon, iconParent.siteOf(replaceIcon))
            self.cursor.setToEntryIcon()
            self.entryIcon.addChar(char)
            self._redisplayChangedEntryIcon()
        else:
            # Either no icons were selected, or multiple icons were selected (so
            # we don't know what to replace).
            typing.beep()

    def _insertEntryIconAtCursor(self, initialChar):
        self.entryIcon = typing.EntryIcon(self.cursor.icon, self.cursor.site,
         window=self)
        pendingArgs = self.cursor.icon.childAt(self.cursor.site)
        self.cursor.icon.replaceChild(self.entryIcon, self.cursor.site)
        self.entryIcon.replaceChild(pendingArgs, (self.cursor.site[0], 0))
        self.cursor.setToEntryIcon()
        self.entryIcon.addChar(initialChar)
        self._redisplayChangedEntryIcon()

    def _redisplayChangedEntryIcon(self, evt=None, oldLoc=None):
        if self.entryIcon is None:
            redrawRegion = AccumRects(oldLoc)
        else:
            redrawRegion = AccumRects(self.entryIcon.rect)
        # If the size of the entry icon changes it requests re-layout of parent.  Figure
        # out if layout needs to change and do so, otherwise just redraw the entry icon
        layoutNeeded = False
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
                        # double-click drag
                        self._startDrag(evt, list(self.assocGrouping(ic).traverse()))
                    else:
                        self._startDrag(evt, list(self.findLeftOuterIcon(
                         self.assocGrouping(ic)).traverse()))
        elif self.inRectSelect:
            self._updateRectSelect(evt)

    def _focusInCb(self, evt):
        pass

    def _focusOutCb(self, evt):
        self.cursor.erase()

    def _buttonPressCb(self, evt):
        if self.dragging:
            self._endDrag()
            return
        if self.buttonDownTime is not None:
            if msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
                self.doubleClickFlag = True
                return
        if self.entryIcon and self.entryIcon.pointInTextArea(evt.x, evt.y):
            self.entryIcon.click(evt)
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
                iconToExecute = self.findIconAt(*self.buttonDownLoc)
                if iconToExecute is None:
                    return
                iconToExecute = self.findLeftOuterIcon(self.assocGrouping(iconToExecute))
                if iconToExecute not in self.topIcons:
                    self.doubleClickFlag = False
                    self._delayedBtnUpActions(evt)
                    return
                self._execute(iconToExecute)

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
        siteIcon, site = self.siteSelected(evt)
        clickedIcon = self.findIconAt(evt.x, evt.y)
        clickedIconSelected = clickedIcon is not None and clickedIcon.selected
        # The horrible logic below implements the combination of
        clickedIconCanMultiSelect = clickedIconSelected and \
         (len(clickedIcon.children()) > 0 and not clickedIcon.children()[0].selected)
        if self.buttonDownState & SHIFT_MASK:
            self._select(evt, clickedIcon, 'add')
        elif self.buttonDownState & CTRL_MASK:
            self._select(evt, clickedIcon, 'toggle')
        elif clickedIconCanMultiSelect:
            self._select(evt, clickedIcon, hier=True)
        elif siteIcon is not None and not self.cursor.cursorAtIconSite(siteIcon, site):
            self.unselectAll()
            if self.entryIcon is None:  # Might want to flash entry icon, here
                self.cursor.setToIconSite(siteIcon, site)
        elif clickedIconSelected:
            self.unselectAll()
        elif clickedIcon is None:
            self.unselectAll()
            if self.entryIcon is None:  # Might want to flash entry icon, here
                 self.cursor.setToWindowPos((evt.x, evt.y))
        else:
            self._select(evt, clickedIcon, 'select', hier=False)
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
        if self.cursor.type == "window":
            px, py = self.cursor.pos
        else:
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
        if len(pastedIcons) > 0 and pastedIcons[0].outSiteOffset is not None:
            # If the top icon has an output site, line it up on the paste point
            xOff, yOff = pastedIcons[0].outSiteOffset
            for topIcon in pastedIcons:
                for ic in topIcon.traverse():
                    ic.rect = offsetRect(ic.rect, -xOff, -yOff)
        redrawRect = AccumRects()
        for pastedTopIcon in pastedIcons:
            self.topIcons.append(pastedTopIcon)
            for ic in pastedTopIcon.traverse():
                ic.draw()  # No need to clip or erase, all drawn on top
                redrawRect.add(ic.rect)
        self.refresh(redrawRect.get())
        if self.cursor.type == "window":
            if len(pastedIcons) > 0 and pastedIcons[0].outSiteOffset is not None:
                self.cursor.setToIconSite(pastedIcons[0], ("output", 0))
            else:
                self.cursor.removeCursor()

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
        self.cursor.removeCursor()

    def _enterCb(self, evt=None):
        """Execute the top level icon at the entry or icon cursor"""
        # Find the icon at the cursor.  If there's still an entry icon, try to process
        # its content before executing.
        if self.entryIcon is not None:
            iconToExecute = self.entryIcon.attachedIcon
            # Add a delimiter character to force completion
            oldLoc = self.entryIcon.rect
            self.entryIcon.addChar(" ")
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
            # If the entry icon is still there, check if it's empty, and if so, remove
            # Otherwise, just give up trying to execute
            if self.entryIcon is not None:
                if len(self.entryIcon.text) == 0 and \
                 self.entryIcon.pendingAttribute is None and \
                 self.entryIcon.pendingArgument is None:
                    self.cursor.setToIconSite(self.entryIcon.attachedIcon, self.entryIcon.attachedSite)
                    self.removeIcons([self.entryIcon])
                    self.entryIcon = None
                else:
                    return
        if self.cursor.type == "icon":
            iconToExecute = self.cursor.icon
        else:
            return  # Nothing to execute
        # Find and execute the top level icon associated with the icon at the cursor
        iconToExecute = self.topLevelParent(iconToExecute)
        if iconToExecute is None:
            print("Could not find top level icon to execute")
            return
        self._execute(iconToExecute)

    def _startDrag(self, evt, icons, needRemove=True):
        self.cursor.removeCursor()
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
        self.cursor.removeCursor()
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

    def _execute(self, iconToExecute):
        # Execute the requested icon.  Icon execution methods will throw exception
        # IconExecException which provides the icon where things went bad so it can
        # be shown in self._handleExecErr
        try:
            result = iconToExecute.execute()
        except icon.IconExecException as excep:
            self._handleExecErr(excep)
            return
        # If the last execution result of the same icon is still laying where it was
        # placed, remove it so that results don't pile up
        outSitePos = iconToExecute.posOfSite(("output", 0))
        if outSitePos in self.execResultPositions:
            lastResultIcon, lastResultPos = self.execResultPositions[outSitePos]
            if lastResultIcon is not None and lastResultIcon in self.topIcons and \
             lastResultPos == lastResultIcon.rect[:2]:
                self.removeIcons([lastResultIcon])
            del self.execResultPositions[outSitePos]
        # Convert results to icon form
        resultIcons = compile_eval.parsePasted(repr(result), self, (0, 0))
        if resultIcons is None:
            resultIcons = [icon.IdentIcon(repr(result), self, (0, 0))]
        resultIcon = resultIcons[0]
        # Place the results to the left of the icon being executed
        if outSitePos is None:
            outSiteX, top, right, bottom = iconToExecute.rect
            outSiteY = (bottom + top) // 2
        else:
            outSiteX, outSiteY = outSitePos
        resultRect = resultIcon.hierRect()
        resultOutSitePos = resultIcon.posOfSite(("output", 0))
        if resultOutSitePos is None:
            resultOutSiteX, top, right, bottom = resultIcon.rect
            resultOutSiteY = (bottom + top) // 2
        else:
            resultOutSiteX, resultOutSiteY = resultOutSitePos
        resultX = outSiteX - RESULT_X_OFFSET - icon.rectWidth(resultRect)
        resultY = outSiteY - resultOutSiteY - resultIcon.rect[1]
        resultIcon.rect = offsetRect(resultIcon.rect, resultX, resultY)
        self.topIcons.append(resultIcon)
        resultIcon.layout()
        resultRect = resultIcon.hierRect()
        for ic in resultIcon.traverse():
            ic.selected = True
            ic.draw(clip=resultRect)
        self.refresh(resultRect)
        # Remember where the last result was drawn, so it can be erased if it is still
        # there the next time the same icon is executed
        self.execResultPositions[outSitePos] = resultIcon, resultIcon.rect[:2]

    def _handleExecErr(self, excep):
        iconRect = excep.icon.hierRect()
        for ic in excep.icon.traverse():
            ic.draw(clip=iconRect, colorErr=ic==excep.icon)
        self.refresh(iconRect)
        tkinter.messagebox.showerror("Error Executing", message=excep.message)
        for ic in excep.icon.traverse():
            ic.draw(clip=iconRect, colorErr=False)
        self.refresh(iconRect)

    def _select(self, evt, ic, op='select', hier=True):
        """Select or toggle the top icon being pointed at, and bring it to the top.
           Options are 'select', 'toggle' and 'add'"""
        if op is 'select':
            self.unselectAll()
        if ic is None or ic is self.entryIcon:
            return
        refreshRegion = AccumRects()
        if hier:
            changedIcons = list(self.assocGrouping(ic).traverse())
        else:
            changedIcons = [ic]
        for ic in changedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
        for ic in self.findIconsInRegion(refreshRegion.get()):
            ic.draw(clip=refreshRegion.get())
        self.refresh(refreshRegion.get())
        self.cursor.removeCursor()

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

    def parentOf(self, ic):
        """Find the parent of a given icon.  Don't use this casually.  Because we don't
        have a parent link, this is an exhaustive search of the hierarchy."""
        parents = self.parentage(ic)
        if parents is None or parents == ():
            return None
        return parents[-1]

    def topLevelParent(self, ic):
        parents = self.parentage(ic)
        if parents is None:
            return None
        if parents == ():
            return ic
        return parents[0]

    def parentage(self, child, fromIcon=None):
        """Returns a tuple containing the lineage of the given icon, from window.topIcons
        down to the direct parent of the icon.  Don't use this casually.  Because we don't
        have a parent link, this is an exhaustive search of the hierarchy.  For an icon at
        the top of the hierarchy, returns an empty tuple.  If the icon is not found at all
        in the hierarchy, returns None."""
        if fromIcon is None:
            icons = self.topIcons
        else:
            icons = fromIcon.children()
        for ic in icons:
            if ic == child:
                return ()
            result = self.parentage(child, fromIcon=ic)
            if result is not None:
                return (ic, *result)
        return None

    def assocGrouping(self, ic):
        """Find the root binary operation associated with a group of equal precedence
        operations"""
        child = ic
        if ic.__class__ is not icon.BinOpIcon:
            return ic
        for parent in reversed(self.parentage(ic)):
            if parent.__class__ is not icon.BinOpIcon or parent.precedence != ic.precedence:
                return child
            child = parent
        return child

    def siteSelected(self, evt):
        """Look for icon sites near button press, if found return icon and site"""
        left = evt.x - SITE_SELECT_DIST
        right = evt.x + SITE_SELECT_DIST
        top = evt.y - SITE_SELECT_DIST
        bottom = evt.y + SITE_SELECT_DIST
        minDist = SITE_SELECT_DIST + 1
        minSite = (None, None)
        for ic in self.findIconsInRegion((left, top, right, bottom)):
            iconSites = ic.snapLists(atTop=True)
            for siteType, siteList in iconSites.items():
                for siteIcon, (x, y), siteIdx in siteList:
                    if siteType in ("input", "output"):
                        x += 2
                    elif siteType in ("attrOut", "attrIn"):
                        y -= icon.ATTR_SITE_OFFSET
                        x += 1
                    else:
                        continue  # not a visible site type
                    dist = (abs(evt.x - x) + abs(evt.y - y)) // 2
                    if dist < minDist or (dist == minDist and \
                     minSite[0] in ("output", "attrIn")):  # Prefer inputs, for now
                        minDist = dist
                        minSite = siteIcon, (siteType, siteIdx)
        if minDist < SITE_SELECT_DIST + 1:
            return minSite
        return None, None

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
        self.root.after(CURSOR_BLINK_RATE, self._blinkCursor)
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

    def _blinkCursor(self):
        focusWidget = self.root.focus_get()
        for window in self.windows:
            if window.top == focusWidget:
                window.cursor.blink()
                break
        self.root.after(CURSOR_BLINK_RATE, self._blinkCursor)

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
