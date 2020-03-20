# Copyright Mark Edel  All rights reserved
# Python-g main module
import tkinter as tk
import typing
import icon
import undo
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
# Tkinter canvas can't handle individual images for each icon.  After about 4000
# pixmaps, it breaks and dies.  Drawing directly to the screen is also problematic.
# Here, we have a Windows-only solution, provided by ImageWin module of pillow.  This
# is a kind-of messed up module which gets very little use due to bugs and poor
# documentation.  While it doesn't give us direct access to the windows framebuffer,
# it does allow us to copy data there from a PIL image in a two-step process that is
# sufficiently fast for the purposes of this program.
#
# Presumably for a cross platform version, it should be possible to get the equivalent
# of a window handle from tkinter to allow us to write pixmaps to the display within a
# tkinter window.

# UI Notes:
#
# Generally we don't want both the selection and cursor to exist at the same time, since
# that makes the destination for typing and pasting, ambiguous.  It is allowed in the case
# of execution results, so that the user can easily delete them but resume typing at the
# same spot.  Therefore, rules for what takes priority when both are present are guided
# by that particular use case.  It is also important that the interface does not remain
# very long in the state where both are present, so take any reasonable opportunity to
# remove the selection.

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
        menu.add_command(label="Undo", command=self._undoCb, accelerator="Ctrl+Z")
        menu.add_command(label="Redo", command=self._redoCb, accelerator="Ctrl+Y")
        menu.add_separator()
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
        self.top.bind("<Control-z>", self._undoCb)
        self.top.bind("<Control-y>", self._redoCb)
        self.top.bind("<Control-x>", self._cutCb)
        self.top.bind("<Control-c>", self._copyCb)
        self.top.bind("<Control-v>", self._pasteCb)
        self.top.bind("<Delete>", self._deleteCb)
        self.top.bind("<BackSpace>", self._backspaceCb)
        self.top.bind("<Escape>", self._cancelCb)
        self.top.bind("<Return>", self._enterCb)
        self.top.bind("<Up>", self._arrowCb)
        self.top.bind("<Down>", self._arrowCb)
        self.top.bind("<Left>", self._arrowCb)
        self.top.bind("<Right>", self._arrowCb)
        self.top.bind("<Key>", self._keyCb)
        self.imgFrame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.popup = tk.Menu(self.imgFrame, tearoff=0)
        self.popup.add_command(label="Undo", command=self._undoCb, accelerator="Ctrl+Z")
        self.popup.add_command(label="Redo", command=self._redoCb, accelerator="Ctrl+Y")
        self.popup.add_separator()
        self.popup.add_command(label="Cut", command=self._cutCb, accelerator="Ctrl+X")
        self.popup.add_command(label="Copy", command=self._copyCb, accelerator="Ctrl+C")
        self.popup.add_command(label="Paste", command=self._pasteCb, accelerator="Ctrl+V")
        self.popup.add_command(label="Delete", command=self._deleteCb,
         accelerator="Delete")

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
        self.undo = undo.UndoRedoList(self)

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
            self._select(self.findIconAt(evt.x, evt.y))

    def _btn3ReleaseCb(self, evt):
        self.popup.tk_popup(evt.x_root, evt.y_root, 0)

    def _newCb(self):
        appData.newWindow()

    def _configureCb(self, evt):
        """Called when window is initially displayed or resized"""
        if evt.width != self.image.width or evt.height != self.image.height:
            self.image = Image.new('RGB', (evt.width, evt.height), color=windowBgColor)
            self.draw = ImageDraw.Draw(self.image)
        self.redraw()

    def _exposeCb(self, _evt):
        """Called when a new part of the window is exposed and needs to be redrawn"""
        self.refresh(redraw=False)

    def _keyCb(self, evt):
        if evt.state & (CTRL_MASK | LEFT_ALT_MASK):
            return
        char = typing.tkCharFromEvt(evt)
        if char is None:
            return
        # If there's a cursor displayed somewhere, use it
        if self.cursor.type == "text":
            # If it's an active entry icon, feed it the character
            oldLoc = self.entryIcon.hierRect()
            self.entryIcon.addText(char)
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
            return
        elif self.cursor.type == "icon":
            self._insertEntryIconAtCursor(char)
            return
        elif self.cursor.type == "window":
            x, y = self.cursor.pos
            self.entryIcon = typing.EntryIcon(None, None, window=self)
            y -= self.entryIcon.sites.output.yOffset
            self.entryIcon.rect = offsetRect(self.entryIcon.rect, x, y)
            self.addTop(self.entryIcon)
            self.cursor.setToEntryIcon()
            self.entryIcon.addText(char)
            self._redisplayChangedEntryIcon()
            return
        # If there's an appropriate selection, use that
        selectedIcons = findTopIcons(self.selectedIcons())
        if len(selectedIcons) == 1:
            # A single icon was selected.  Replace it and its children
            replaceIcon = selectedIcons[0]
            iconParent = replaceIcon.parent()
            if iconParent is None:
                self.entryIcon = typing.EntryIcon(None, None, window=self)
                self.replaceTop(replaceIcon, self.entryIcon)
            else:
                self.entryIcon = typing.EntryIcon(iconParent, iconParent.siteOf(replaceIcon),
                 window=self)
                iconParent.replaceChild(self.entryIcon, iconParent.siteOf(replaceIcon))
            self.cursor.setToEntryIcon()
            self.entryIcon.addText(char)
            self._redisplayChangedEntryIcon()
        else:
            # Either no icons were selected, or multiple icons were selected (so
            # we don't know what to replace).
            typing.beep()

    def _insertEntryIconAtCursor(self, initialChar):
        if self.cursor.siteType == "output":
            self.entryIcon = typing.EntryIcon(None, None, window=self,
             location=self.cursor.icon.rect[:2])
            self.entryIcon.setPendingArg(self.cursor.icon)
            self.removeTop(self.cursor.icon)
            self.cursor.setToEntryIcon()
            self.addTop(self.entryIcon)
        else:
            self.entryIcon = typing.EntryIcon(self.cursor.icon, self.cursor.site,
             window=self)
            pendingArg = self.cursor.icon.childAt(self.cursor.site)
            self.cursor.icon.replaceChild(self.entryIcon, self.cursor.site)
            self.entryIcon.setPendingArg(pendingArg)
            self.cursor.setToEntryIcon()
        self.entryIcon.addText(initialChar)
        self._redisplayChangedEntryIcon()

    def _redisplayChangedEntryIcon(self, evt=None, oldLoc=None):
        # ... This currently operates on all of the icons in the window, and needs to be
        #      narrowed to just the top icon that held the cursor
        if self.entryIcon is None:
            redrawRegion = AccumRects(oldLoc)
        else:
            redrawRegion = AccumRects(self.entryIcon.rect)
        # If the size of the entry icon changes it requests re-layout of parent.  Figure
        # out if layout needs to change and do so, otherwise just redraw the entry icon
        for ic in self.topIcons.copy():  # Copy because function can change list
            self.filterRedundantParens(ic)
        layoutNeeded = self.layoutDirtyIcons()
        # Redraw the areas affected by the updated layouts
        if layoutNeeded:
            redrawRegion.add(layoutNeeded)
            self.refresh(redrawRegion.get())
        else:
            if self.entryIcon is not None:
                self.entryIcon.draw()
        self.undo.addBoundary()

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
                        # double-click drag, ignores associativity and outer icon
                        self._startDrag(evt, list(ic.traverse()))
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
        if (ic is None or not ic.selected) and not (evt.state & SHIFT_MASK or evt.state & CTRL_MASK):
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
        self.buttonDownTime = None
        clickedIcon = self.findIconAt(evt.x, evt.y)
        if clickedIcon is None:
            # Clicked on window background, move cursor
            if self.entryIcon is not None:  # Might want to flash entry icon, here
                return
            siteIcon, site = self.siteSelected(evt)
            if siteIcon:
                self.cursor.setToIconSite(siteIcon, site)
            else:
                self.unselectAll()
                self.cursor.setToWindowPos((evt.x, evt.y))
            return
        if self.buttonDownState & SHIFT_MASK:
            self._select(clickedIcon, 'add')
            return
        elif self.buttonDownState & CTRL_MASK:
            self._select(clickedIcon, 'toggle')
            return
        action = self._nextProgressiveClickAction(clickedIcon, evt)
        if action == "moveCursor":
            self.unselectAll()
            if self.entryIcon is None:  # Might want to flash entry icon, here
                siteIcon, site = self.siteSelected(evt)
                if siteIcon is not None:
                    self.cursor.setToIconSite(siteIcon, site)
            return
        self._select(clickedIcon, action)

    def _nextProgressiveClickAction(self, clickedIcon, evt):
        """If an icon was clicked, determine the action to be taken: one of either
        'moveCursor', which implies unselect and (if possible) move the cursor to the
        nearest cursor site; or a selection operation.  Selection operations are
        compatible with the self._select function: 'select': select just the icon,
        'hier': select the icon and its arguments, and 'left': select the expression of
        which the icon is the leftmost argument."""
        siteIcon, site = self.siteSelected(evt)
        siteSelected = self.cursor.type == "icon" and self.cursor.icon is siteIcon
        currentSel = self.selectedIcons()
        singleSel = [clickedIcon]
        hierSel = list(clickedIcon.traverse())
        leftSel = list(self.findLeftOuterIcon(self.assocGrouping(clickedIcon)).traverse())
        if not currentSel:
            if siteIcon is not None and not siteSelected:
                return "moveCursor"
            return "select"
        if currentSel == singleSel:
            if hierSel == currentSel:
                if leftSel == currentSel:
                    return "moveCursor"
                return "left"
            return "hier"
        if currentSel == hierSel:
            if leftSel == currentSel:
                return "moveCursor"
            return "left"
        if currentSel == leftSel:
            return "moveCursor"
        return "moveCursor"

    def _destroyCb(self, evt):
        if evt.widget == self.top:
            appData.removeWindow(self)

    def _undoCb(self, _evt=None):
        self.undo.undo()

    def _redoCb(self, _evt=None):
        self.undo.redo()

    def _cutCb(self, _evt=None):
        self._copyCb()
        self.removeIcons(self.selectedIcons())
        self.undo.addBoundary()

    def _copyCb(self, evt=None):
        selectedIcons = self.selectedIcons()
        selectedRect = icon.containingRect(selectedIcons)
        if selectedRect is None:
            return
        xOff, yOff = selectedRect[:2]
        topIcons = findTopIcons(selectedIcons)
        clipIcons = icon.clipboardRepr(topIcons, (-xOff, -yOff))
        clipTxt = "\n".join([ic.textRepr() for ic in topIcons])
        self.top.clipboard_clear()
        self.top.clipboard_append(clipIcons, type='ICONS')
        self.top.clipboard_append(clipTxt, type='STRING')

    def _pasteCb(self, evt=None):
        if self.cursor.type == "text":
            # If the user is pasting in to the entry icon use clipboard text, only
            try:
                text = self.top.clipboard_get(type="STRING")
            except:
                return
            oldLoc = self.entryIcon.hierRect()
            self.entryIcon.addText(text)
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
            return
        # Look at what is on the clipboard and make the best possible conversion to icons
        try:
            iconString = self.top.clipboard_get(type="ICONS")
        except:
            iconString = None
        if iconString is not None:
            pastedIcons = icon.iconsFromClipboardString(iconString, self, (0, 0))
        else:
            # Couldn't get our icon data format.  Try string as python code
            try:
                text = self.top.clipboard_get(type="STRING")
            except:
                text = None
            # Try to parse the string as Python code
            if text is not None:
                pastedIcons = compile_eval.parsePasted(text, self, (0, 0))
                # Not usable python code, put in to single icon as string
                if pastedIcons is None:
                    pastedIcons = [icon.TextIcon(repr(text), self, (0, 0))]
            else:
                # No text available in a form we can use.  Try for image
                clipImage = ImageGrab.grabclipboard()
                if clipImage is None:
                    return
                pastedIcons = [icon.ImageIcon(clipImage, self, (0, 0))]
        if len(pastedIcons) == 0:
            return  # Nothing usable on the clipboard
        # There was something clipboard that could be converted to icon form.  Figure out
        # where to put it
        iconOutputSite = pastedIcons[0].posOfSite("output")
        replaceParent = None
        replaceSite = None
        pastePos = None
        if self.cursor.type == "window":
            x, y = self.cursor.pos
            if iconOutputSite is not None:
                xOff, yOff = iconOutputSite
                x -= xOff
                y -= yOff
            pastePos = x, y
        elif self.cursor.type == "icon":
            if self.cursor.site[0] is not "input" or len(pastedIcons) != 1:
                typing.beep()
                return
            replaceParent = self.cursor.icon
            replaceSite = self.cursor.site
        else:
            # There's no cursor.  See if there's a selection
            selectedIcons = self.selectedIcons()
            if len(selectedIcons) == 0:
                typing.beep()
                return
            selectedIcons = findTopIcons(self.selectedIcons())
            if len(selectedIcons) == 1 and len(pastedIcons) == 1:
                replaceParent = selectedIcons[0].parent()
                replaceSite = replaceParent.siteOf(selectedIcons[0])
            else:
                selectedRect = icon.containingRect(self.selectedIcons())
                pastePos = selectedRect[:2]
                self.removeIcons(self.selectedIcons())
        # We now know where to put the pasted icons: If replaceParent is True, replace
        # the icon at replaceSite.  Otherwise place the icons at the top level of the
        # window at position given by pastePos
        if replaceParent is not None:
            topIcon = replaceParent.topLevelParent()
            redrawRegion = AccumRects(topIcon.hierRect())
            replaceParent.replaceChild(pastedIcons[0], replaceSite)
            topIcon = self.filterRedundantParens(topIcon)
            topIcon.layout()
            redrawRegion.add(topIcon.hierRect())
            self.refresh(redrawRegion.get())
            self.cursor.setToIconSite(replaceParent, replaceSite)
        else:  # Put
            x, y = pastePos
            for topIcon in pastedIcons:
                for ic in topIcon.traverse():
                    ic.rect = offsetRect(ic.rect, x, y)
            redrawRect = AccumRects()
            for pastedTopIcon in pastedIcons:
                self.addTop(pastedTopIcon)
                for ic in pastedTopIcon.traverse():
                    redrawRect.add(ic.rect)
            self.refresh(redrawRect.get(), clear=False)
            if iconOutputSite is None:
                self.cursor.removeCursor()
            else:
                self.cursor.setToIconSite(pastedIcons[0], "output")
        self.undo.addBoundary()

    def _deleteCb(self, _evt=None):
        selected = self.selectedIcons()
        if selected:
            self.removeIcons(selected)
        elif self.cursor.type == "icon":
            # Not using removeIcons here, to take advantage or replaceChild operation
            # on listType icons and remove an empty argument spot.
            self.cursor.icon.replaceChild(None, self.cursor.site)
            self.redoLayout(self.cursor.icon.topLevelParent())
        self.undo.addBoundary()

    def _backspaceCb(self, _evt=None):
        if self.entryIcon is None:
            self.removeIcons(self.selectedIcons())
        else:
            self.entryIcon.backspace()
            self._redisplayChangedEntryIcon()

    def _arrowCb(self, evt):
        if self.cursor.type is None:
            selected = self.selectedIcons()
            if selected:
                self.unselectAll()
                self.cursor.arrowKeyWithSelection(evt.keysym, selected)
            return
        self.unselectAll()
        self.cursor.processArrowKey(evt.keysym)

    def _cancelCb(self, evt=None):
        if self.entryIcon is not None:
            oldLoc = self.entryIcon.hierRect()
            self.entryIcon.remove()
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
        else:
            self.cursor.removeCursor()
        self._cancelDrag()

    def _enterCb(self, evt=None):
        """Execute the top level icon at the entry or icon cursor"""
        # Find the icon at the cursor.  If there's still an entry icon, try to process
        # its content before executing.
        if self.entryIcon is not None:
            # Add a delimiter character to force completion
            oldLoc = self.entryIcon.rect
            self.entryIcon.addText(" ")
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
            # If the entry icon is still there, check if it's empty, and if so, remove
            # Otherwise, just give up trying to execute
            if self.entryIcon is not None:
                if len(self.entryIcon.text) == 0 and \
                 self.entryIcon.pendingAttribute is None and \
                 self.entryIcon.pendingArg() is None:
                    self.cursor.setToIconSite(self.entryIcon.attachedIcon,
                     self.entryIcon.attachedSite)
                    self.removeIcons([self.entryIcon])
                    self.entryIcon = None
                else:
                    return
        if self.cursor.type == "icon":
            iconToExecute = self.cursor.icon
        else:
            return  # Nothing to execute
        # Find and execute the top level icon associated with the icon at the cursor
        iconToExecute = iconToExecute.topLevelParent()
        if iconToExecute is None:
            print("Could not find top level icon to execute")
            return
        self._execute(iconToExecute)

    def _startDrag(self, evt, icons, needRemove=True):
        self.dragging = icons
        # Remove the icons from the window image and handle the resulting detachments
        # re-layouts, and redrawing.
        if needRemove:
            self.removeIcons(self.dragging)
        # Dragging parent icons away from their children may require re-layout of the
        # (moving) parent icons
        topDraggingIcons = findTopIcons(self.dragging)
        self.layoutDirtyIcons(topDraggingIcons)
        # For top performance, make a separate image containing the moving icons against
        # a transparent background, which can be redrawn with imaging calls, only.
        moveRegion = AccumRects()
        for ic in self.dragging:
            moveRegion.add(ic.rect)
        el, et, er, eb = moveRegion.get()
        self.dragImageOffset = el - self.buttonDownLoc[0], et - self.buttonDownLoc[1]
        self.dragImage = Image.new('RGBA', (er - el, eb - et), color=(0, 0, 0, 0))
        self.lastDragImageRegion = None
        for ic in self.dragging:
            ic.rect = offsetRect(ic.rect, -el, -et)
            ic.draw(self.dragImage)
            icon.drawSeqSiteConnection(ic, image=self.dragImage)
        # Construct a master snap list for all mating sites between stationary and
        # dragged icons
        draggingOutputs = []
        draggingSeqInserts = []
        for dragIcon in topDraggingIcons:
            dragSnapList = dragIcon.snapLists()
            for ic, (x, y), name in dragSnapList.get("output", []):
                draggingOutputs.append(((x, y), ic))
            for ic, (x, y), name in dragSnapList.get("seqInsert", []):
                draggingSeqInserts.append(((x, y), ic))
        stationaryInputs = []
        for topIcon in self.topIcons:
            for winIcon in topIcon.traverse():
                snapLists = winIcon.snapLists()
                for ic, pos, name in snapLists.get("input", []):
                    stationaryInputs.append((pos, 0, ic, "input", name))
                for ic, pos, name in snapLists.get("insertInput", []):
                    stationaryInputs.append((pos, 0, ic, "insertInput", name))
                for ic, pos, name in snapLists.get("seqIn", []):
                    if ic.sites.seqIn.att is None:
                        stationaryInputs.append((pos, 0, ic, "seqIn", name))
                for ic, pos, name in snapLists.get("seqOut", []):
                    nextIc = ic.sites.seqOut.att
                    if nextIc is None:
                        sHgt = 0
                    else:
                        nextInX, nextInY = nextIc.posOfSite('seqIn')
                        sHgt = nextInY - pos[1]
                    stationaryInputs.append((pos, sHgt, ic, "seqOut", name))
        self.snapList = []
        for si in stationaryInputs:
            (sx, sy), sh, sIcon, sSiteType, sSiteName = si
            for (dx, dy), dIcon in draggingOutputs:
                self.snapList.append((sx-dx, sy-dy, sh, sIcon, dIcon, sSiteType, sSiteName))
            for (dx, dy), dIcon in draggingSeqInserts:
                if sSiteType in ('seqIn', 'seqOut'):
                    self.snapList.append((sx - dx, sy - dy, sh, sIcon, dIcon, sSiteType, sSiteName))
        self.snapped = None
        self._updateDrag(evt)

    def _updateDrag(self, evt):
        if not self.dragging:
            return
        x = snappedX = self.dragImageOffset[0] + evt.x
        y = snappedY = self.dragImageOffset[1] + evt.y
        # If the drag results in mating sites being within snapping distance, change the
        # drag position to mate them exactly (snap them together)
        self.snapped = None
        nearest = SNAP_DIST + 1
        for sx, sy, sHgt, sIcon, movIcon, siteType, siteName in self.snapList:
            if sHgt == 0 or y < sy:
                dist = abs(x-sx) + abs(y-sy)
            elif y > sy + sHgt:
                dist = abs(x-sx) + abs(y-sy-sHgt)
                sy += sHgt
            else:  # y is vertically within the range of a sequence site
                dist = abs(x-sx)
                sy = y
            if dist < nearest:
                nearest = dist
                snappedX = sx
                snappedY = sy
                self.snapped = (sIcon, movIcon, siteType, siteName)
        # Erase the old drag image
        width = self.dragImage.width
        height = self.dragImage.height
        dragImageRegion = (snappedX, snappedY, snappedX+width, snappedY+height)
        if self.lastDragImageRegion is not None:
            for r in exposedRegions(self.lastDragImageRegion, dragImageRegion):
                self.refresh(r, redraw=False)
        # Draw the image of the moving icons in their new locations directly to the
        # display (leaving self.image clean).  This makes dragging fast by eliminating
        # individual icon drawing of while the user is dragging.
        dragImage = self.image.crop(dragImageRegion)
        dragImage.paste(self.dragImage, mask=self.dragImage)
        self.drawImage(dragImage, (snappedX, snappedY))
        self.lastDragImageRegion = dragImageRegion

    def _endDrag(self):
        # self.dragging icons are not stored hierarchically, but are in draw order
        topDraggedIcons = findTopIcons(self.dragging)
        redrawRegion = AccumRects()
        l, t, r, b = self.lastDragImageRegion
        for ic in self.dragging:
            ic.rect = offsetRect(ic.rect, l, t)
            redrawRegion.add(ic.rect)
        if self.snapped is not None:
            # The drag ended in a snap.  Attach or replace existing icons at the site
            statIcon, movIcon, siteType, siteName = self.snapped
            redrawRegion.add(statIcon.hierRect())
            if siteType != "insertInput" and statIcon.childAt(siteName):
                redrawRegion.add(movIcon.hierRect())
            if siteType in ("input", "attrOut"):
                topDraggedIcons.remove(movIcon)
                statIcon.replaceChild(movIcon, siteName)
            elif siteType == "insertInput":
                topDraggedIcons.remove(movIcon)
                statIcon.insertChild(movIcon, siteName)
            elif siteType == 'seqOut':
                icon.insertSeq(movIcon, statIcon)
            elif siteType == 'seqIn':
                icon.insertSeq(movIcon, statIcon, before=True)
            for ic in self.topIcons:
                self.filterRedundantParens(ic)
            # Redo layouts for all affected (all the way to the top)
            redrawRegion.add(self.layoutDirtyIcons())
            # Redraw the areas affected by the updated layouts
            self.clearBgRect(redrawRegion.get())
        self.addTop(topDraggedIcons)
        self.redraw(redrawRegion.get())
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None
        # Refresh the entire display.  While refreshing a smaller area is technically
        # possible, after all the dragging and drawing, it's prudent to ensure that the
        # display remains in sync with the image pixmap
        self.refresh(redraw=False)
        self.undo.addBoundary()

    def _cancelDrag(self):
        # Not properly cancelling drag, yet, just dropping the icons being dragged
        if self.dragging is None:
            return
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
        self.refresh(redrawRegion.get(), clear=False)
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
        self.refresh((l, t, r+1, t+1), redraw=False)
        self.refresh((l, b, r+1, b+1), redraw=False)
        self.refresh((l, t, l+1, b+1), redraw=False)
        self.refresh((r, t, r+1, b+1), redraw=False)

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
        outSitePos = iconToExecute.posOfSite("output")
        if outSitePos in self.execResultPositions:
            lastResultIcon, lastResultPos = self.execResultPositions[outSitePos]
            if lastResultIcon is not None and lastResultIcon in self.topIcons and \
             lastResultPos == lastResultIcon.rect[:2]:
                self.removeIcons([lastResultIcon])
            del self.execResultPositions[outSitePos]
        # Convert results to icon form
        resultIcons = compile_eval.parsePasted(repr(result), self, (0, 0))
        if resultIcons is None:
            resultIcons = [icon.TextIcon(repr(result), self, (0, 0))]
        resultIcon = resultIcons[0]
        # Place the results to the left of the icon being executed
        if outSitePos is None:
            outSiteX, top, right, bottom = iconToExecute.rect
            outSiteY = (bottom + top) // 2
        else:
            outSiteX, outSiteY = outSitePos
        resultRect = resultIcon.hierRect()
        resultOutSitePos = resultIcon.posOfSite("output")
        if resultOutSitePos is None:
            resultOutSiteX, top, right, bottom = resultIcon.rect
            resultOutSiteY = (bottom + top) // 2
        else:
            resultOutSiteX, resultOutSiteY = resultOutSitePos
        resultX = outSiteX - RESULT_X_OFFSET - icon.rectWidth(resultRect)
        resultY = outSiteY - resultOutSiteY - resultIcon.rect[1]
        resultIcon.rect = offsetRect(resultIcon.rect, resultX, resultY)
        self.addTop(resultIcon)
        resultIcon.layout()
        resultRect = resultIcon.hierRect()
        for ic in resultIcon.traverse():
            ic.selected = True
            ic.draw(clip=resultRect)
        self.refresh(resultRect, redraw=False)
        # For expressions that yield "None", show it, then automatically erase
        if result is None:
            time.sleep(0.4)
            self.removeIcons([resultIcon])
        else:
            # Remember where the last result was drawn, so it can be erased if it is still
            # there the next time the same icon is executed
            self.execResultPositions[outSitePos] = resultIcon, resultIcon.rect[:2]
        self.undo.addBoundary()

    def _handleExecErr(self, excep):
        iconRect = excep.icon.hierRect()
        for ic in excep.icon.traverse():
            ic.draw(clip=iconRect, colorErr=ic==excep.icon)
        self.refresh(iconRect, redraw=False)
        tkinter.messagebox.showerror("Error Executing", message=excep.message)
        for ic in excep.icon.traverse():
            ic.draw(clip=iconRect, colorErr=False)
        self.refresh(iconRect, redraw=False)

    def _select(self, ic, op='select'):
        """Change the selection.  Options are 'select': selects single icon, 'toggle':
        changes the state of a single icon, 'add': adds a single icon to the selection,
        'hier': changes the selection to the icon and it's children, 'left': changes
        the selection to the icon and associated expression for which it is the
        leftmost component"""
        if op in ('select', 'hier', 'left'):
            self.unselectAll()
        if ic is None or ic is self.entryIcon:
            return
        refreshRegion = AccumRects()
        if op == 'hier':
            changedIcons = list(ic.traverse())
        elif op == 'left':
            changedIcons = list(self.findLeftOuterIcon(self.assocGrouping(ic)).traverse())
        else:
            changedIcons = [ic]
        for ic in changedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.selected = not ic.selected
            else:
                ic.selected = True
        self.refresh(refreshRegion.get(), clear=False)
        self.cursor.removeCursor()

    def unselectAll(self):
        refreshRegion = AccumRects()
        selectedIcons = self.selectedIcons()
        if len(selectedIcons) == 0:
            return
        for ic in selectedIcons:
            refreshRegion.add(ic.rect)
            ic.selected = False
        self.refresh(refreshRegion.get(), clear=False)

    def redraw(self, region=None, clear=True):
        """Cause all icons to redraw to the pseudo-framebuffer (call refresh to transfer
        from there to the display).  Setting clear to False suppresses clearing the
        region to the background color before redrawing."""
        if clear:
            self.clearBgRect(region)
        # Traverse all top icons (only way to find out what's in the region).  Correct
        # drawing depends on everything being ordered so overlaps happen properly.
        # Sequence lines must be drawn on top of the icons they connect but below any
        # icons that might be placed on top of them.
        for topIcon in self.topIcons:
            for ic in topIcon.traverse():
                if region is None or rectsTouch(region, ic.rect):
                    ic.draw()
            if region is None or icon.seqConnectorTouches(topIcon, region):
                icon.drawSeqSiteConnection(topIcon, clip=region)

    def refresh(self, region=None, redraw=True, clear=True):
        """Redraw any rectangle (region) of the window.  If redraw is set to False, the
         window will be refreshed from the pseudo-framebuffer (self.image).  If redraw
         is True, the framebuffer is first refreshed from the underlying icon structures.
         If no region is specified (region==None), redraw the whole window.  Setting
         clear to False will not clear the background area before redrawing."""
        if redraw:
            self.redraw(region, clear)
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
        # deletedSet more efficiently determines if an icon is on the deleted list
        deletedSet = set(icons)
        detachList = []
        seqReconnectList = []
        # Find region needing erase, including following sequence connectors
        redrawRegion = AccumRects()
        for ic in icons:
            redrawRegion.add(ic.rect)
            nextIc = ic.nextInSeq()
            if nextIc is not None:
                tx, ty = ic.posOfSite('seqOut')
                bx, by = nextIc.posOfSite('seqIn')
                redrawRegion.add((tx-1, ty-1, tx+1, by+1))
            prevIc = ic.prevInSeq()
            if prevIc is not None:
                tx, ty = prevIc.posOfSite('seqOut')
                bx, by = ic.posOfSite('seqIn')
                redrawRegion.add((tx-1, ty-1, tx+1, by+1))
        # Find and unlink child icons from parents at deletion boundary
        addTopIcons = []
        for topIcon in self.topIcons:
            nextIcon = topIcon.nextInSeq()
            if nextIcon is not None:
                if topIcon in deletedSet and nextIcon not in deletedSet:
                    detachList.append((topIcon, 'seqOut'))
                    topIcon.layoutDirty = True
                if topIcon not in deletedSet and nextIcon in deletedSet:
                    detachList.append((topIcon, 'seqOut'))
                    topIcon.layoutDirty = True
                    while True:
                        nextIcon = nextIcon.nextInSeq()
                        if nextIcon is None:
                            break
                        if nextIcon not in deletedSet:
                            seqReconnectList.append((topIcon, nextIcon))
                            break
            for ic in topIcon.traverse():
                for child in ic.children():
                    if ic in deletedSet and child not in deletedSet:
                        detachList.append((ic, ic.siteOf(child)))
                        addTopIcons.append(child)
                        redrawRegion.add(child.hierRect())
                    elif ic not in deletedSet and child in deletedSet:
                        detachList.append((ic, ic.siteOf(child)))
        for ic, site in detachList:
            ic.replaceChild(None, site)
        for outIcon, inIcon in seqReconnectList:
            outIcon.replaceChild(inIcon, 'seqOut')
        # Update the window's top-icon list to remove deleted icons and add those that
        # have become top icons via deletion of their parents (bring those to the front)
        self.removeTop([ic for ic in self.topIcons if ic in deletedSet])
        self.addTop(addTopIcons)
        # Redo layouts of icons affected by detachment of children
        redrawRegion.add(self.layoutDirtyIcons())
        # Redraw the area affected by the deletion
        self.refresh(redrawRegion.get())

    def clearBgRect(self, rect=None):
        """Clear but don't refresh a rectangle of the window"""
        # Fill rectangle seems to go one beyond
        if rect is None:
            l, t, r, b = 0, 0, self.image.width, self.image.height
        else:
            l, t, r, b = rect
        self.draw.rectangle((l, t, r-1, b-1), fill=windowBgColor)

    def assocGrouping(self, ic):
        """Find the root binary operation associated with a group of equal precedence
        operations"""
        child = ic
        if ic.__class__ is not icon.BinOpIcon:
            return ic
        for parent in ic.parentage():
            if parent.__class__ is not icon.BinOpIcon or parent.precedence !=\
             ic.precedence:
                return child
            child = parent
        return child

    def removeTop(self, ic):
        """Remove top-level icon or icons (without re-layout or re-draw)."""
        if hasattr(ic, '__iter__'):
            for i in ic:
                self.removeTop(i)
        else:
            x, y = ic.rect[:2]
            self.undo.registerRemoveFromTopLevel(ic, x, y, self.topIcons.index(ic))
            self.topIcons.remove(ic)
            ic.becomeTopLevel(True)  #... ??? This does not seem right

    def replaceTop(self, old, new):
        """Replace an existing top-level icon with a new icon.  If the existing icon was
         part of a sequence, replace it in the sequence.  If the icon was not part of a
         sequence place it in the same location.  Does not re-layout or re-draw."""
        self.removeTop(old)
        nextInSeq = old.nextInSeq()
        if nextInSeq:
            old.replaceChild(None, 'seqOut')
            new.replaceChild(nextInSeq, 'seqOut')
        prevInSeq = old.prevInSeq()
        if prevInSeq:
            old.replaceChild(None, 'seqIn')
            new.replaceChild(prevInSeq, 'seqIn')
        oldSite = old.sites.lookup("output")
        newSite = new.sites.lookup("output")
        oldX, oldY = old.rect[:2]
        if oldSite is None or newSite is None:
            newX, newY = oldX, oldY
        else:
            newX = oldX + oldSite.xOffset - newSite.xOffset
            newY = oldY + oldSite.yOffset - newSite.yOffset
        self.addTop(new, newX, newY)

    def addTop(self, ic, x=None, y=None, index=None):
        """Place an icon or icons on the window at the top level (without re-layout or
        re-draw).  If ic is a list, x, y will not be applied."""
        # Find the appropriate index at which to place each icon.  The fact that python 3
        # dictionaries are ordered preserves the order of the added icons, except where
        # we reorder to join sequences with existing sequences.
        addedIcons = {i:True for i in (ic if hasattr(ic, '__iter__') else [ic])}
        # Find any icons in list that are connected to icons outside of the list.  If
        # found look for the attached icon in the topIcons list and insert them in the
        # appropriate place in the list.  This is done first for sequences attached at
        # the top, then for sequences attached at the bottom.  As these sequences are
        # spliced in to the topIcons list, they are removed from addedIcons, so sequences
        # attached at both the top and bottom will not be done twice, and the the
        # remaining (unattached) icons will be left at the end in addedIcons
        attachedSeqs = []
        for ic in addedIcons:
            if hasattr(ic.sites, 'seqIn'):
                prevIcon = ic.sites.seqIn.att
                if prevIcon is not None and prevIcon not in addedIcons:
                    attachedSeqs.append((ic, prevIcon))
        for ic, attachedTo in attachedSeqs:
            try:
                idx = self.topIcons.index(attachedTo) + 1
            except ValueError:
                continue
            iconsInSeq = []
            seqIc = ic
            while True:
                del addedIcons[seqIc]
                iconsInSeq.append(seqIc)
                seqIc = seqIc.nextInSeq()
                if seqIc is None or seqIc not in addedIcons:
                    break
            self.insertTopLevel(iconsInSeq, idx)
        attachedSeqs = []
        for ic in addedIcons:
            nextIcon = ic.nextInSeq()
            if nextIcon is not None and nextIcon not in addedIcons:
                attachedSeqs.append((ic, nextIcon))
        for ic, attachedTo in attachedSeqs:
            try:
                idx = self.topIcons.index(attachedTo)
            except ValueError:
                continue
            iconsInSeq = []
            seqIc = ic
            while True:
                del addedIcons[seqIc]
                iconsInSeq.append(seqIc)
                seqIc = seqIc.prevInSeq()
                if seqIc is None or seqIc not in addedIcons:
                    break
            iconsInSeq.reverse()
            self.insertTopLevel(iconsInSeq, idx)
        # Insert the remaining icons (not needing to be placed in sequence), at the end
        # of the list.
        self.insertTopLevel(list(addedIcons), x=x, y=y)

    def insertTopLevel(self, icons, index=None, x=None, y=None):
        """Add icon or icons to the window's top-level icon list at a specific position
        in the list.  If index is None, append to the end.  Note that this is not
        appropriate for adding icons that are attached to sequences that have icons
        already in the window."""
        if not hasattr(icons, '__iter__'):
            icons = [icons]
        for ic in icons:
            self.undo.registerAddToTopLevel(ic)
        if index is None:
            self.topIcons += icons
        else:
            self.topIcons[index:index] = icons
        for ic in icons:
            # Detaching icons should remove all connections, but the consequence to
            # leaving a parent link at the top level is dire, so make sure all parent
            # links are removed.
            for parentSite in ic.parentSites():
                lingeringParent = ic.childAt(parentSite)
                if lingeringParent:
                    print("Removing lingering parent link to icon added to top")
                    lingeringParent.replaceChild(None, lingeringParent.siteOf(ic))
            # If position was specified, relocate the icon
            if x is not None and y is not None:
                ic.rect = icon.moveRect(ic.rect, (x, y))
            ic.becomeTopLevel(True)

    def findSequences(self, topIcons=None):
        """Find the starting icons for all sequences in the window.  If topIcons is
        None, look at all of the icons in the window.  Otherwise look for just those
        in topIcons (which do not have to be in self.topIcons)"""
        sequenceTops = {}
        topIconSeqs = {}
        if topIcons is None:
            topIcons = self.topIcons
        for topIcon in topIcons:
            if topIcon not in topIconSeqs:
                topOfSeq = icon.findSeqStart(topIcon)
                sequenceTops[topOfSeq] = True
                for seqIcon in icon.traverseSeq(topOfSeq):
                    topIconSeqs[seqIcon] = topOfSeq
        return sequenceTops.keys()

    def layoutDirtyIcons(self, topIcons=None):
        """Look for icons marked as needing layout and lay them out.  If topIcons is
        None, look at all of the icons in the window.  Otherwise look for just those
        in topIcons (which do not have to be in self.topIcons).  Returns a rectangle
        representing the changed areas that need to be redrawn, or None if nothing
        changed."""
        redrawRegion = AccumRects()
        for seqTopIcon in self.findSequences(topIcons):
            redrawRegion.add(self.layoutIconsInSeq(seqTopIcon))
        return redrawRegion.get()

    def layoutIconsInSeq(self, seqStartIcon, checkAllForDirty=True):
        """Lay out all icons in a sequence starting from seqStartIcon. if checkAllForDirty
        is True, will traverse all trees looking for dirty icons and redo those layouts
        as well.  If False, only the top icon is assumed to require layout, and the
        rest in the sequence will be moved up or down without additional checking."""
        redrawRegion = AccumRects()
        x, y = seqStartIcon.pos()
        for seqIc in icon.traverseSeq(seqStartIcon):
            seqIcOrigRect = seqIc.hierRect()
            xOffsetToSeqIn, yOffsetToSeqIn = seqIc.posOfSite('seqIn')
            yOffsetToSeqIn -= seqIcOrigRect[1]
            if (seqIc is seqStartIcon or checkAllForDirty) and seqIc.needsLayout():
                layout = seqIc.layout((0, 0))
                # Find y offset from top of layout to the seqIn site by which the icon
                # needs to be positioned.  If seqIc has an output site, parentSiteOffset
                # of layout is to the output site and needs to be moved to the seqIn site.
                yOffsetToSeqIn = layout.parentSiteOffset
                if hasattr(seqIc.sites, 'output'):
                    yOffsetToSeqIn += seqIc.sites.seqIn.yOffset-seqIc.sites.output.yOffset
            # At this point, y is the seqIn site position if it is the first icon in the
            # sequence.  Otherwise y is the bottom of the layout of the statement above.
            # Adjust it to be the desired y of the seqIn site.
            if seqIc is not seqStartIcon:
                y += yOffsetToSeqIn
            # Figure out how much to move the icons of the statement
            seqIcX, seqIcY = seqIc.posOfSite('seqIn')
            yOffset = y - seqIcY
            xOffset = x - seqIcX
            # If the icons need to be moved, offset them
            if xOffset == 0 and yOffset == 0:
                seqIcNewRect = seqIc.hierRect()  # Already in the right place
            else:
                redrawRegion.add(seqIcOrigRect)
                for ic in seqIc.traverse():
                    ic.rect = offsetRect(ic.rect, xOffset, yOffset)
                seqIcNewRect = seqIc.hierRect()
                redrawRegion.add(seqIcNewRect)
            y = seqIcNewRect[3] + 1
            # ... loop and condition icons will adjust x
        return redrawRegion.get()

    def siteSelected(self, evt):
        """Look for icon sites near button press, if found return icon and site"""
        left = evt.x - SITE_SELECT_DIST
        right = evt.x + SITE_SELECT_DIST
        top = evt.y - SITE_SELECT_DIST
        bottom = evt.y + SITE_SELECT_DIST
        minDist = SITE_SELECT_DIST + 1
        minSite = (None, None, None)
        for ic in self.findIconsInRegion((left, top, right, bottom)):
            iconSites = ic.snapLists()
            for siteType, siteList in iconSites.items():
                for siteIcon, (x, y), siteName in siteList:
                    if siteType in ("input", "output"):
                        x += 2
                    elif siteType in ("attrOut", "attrIn"):
                        y -= icon.ATTR_SITE_OFFSET
                        x += 1
                    else:
                        continue  # not a visible site type
                    dist = (abs(evt.x - x) + abs(evt.y - y)) // 2
                    if dist < minDist or (dist == minDist and
                     minSite[2] in ("attrIn", "output")):  # Prefer inputs, for now
                        minDist = dist
                        minSite = siteIcon, siteName, siteType
        if minDist < SITE_SELECT_DIST + 1:
            return minSite[0], minSite[1]
        return None, None

    def filterRedundantParens(self, ic, parentIcon=None, parentSite=None):
        """Remove parenthesis whose arguments now have their own parenthesis"""
        if ic.__class__ is not typing.CursorParenIcon or not ic.closed:
            for c in ic.children():
                self.filterRedundantParens(c, ic, ic.siteOf(c))
            return ic
        argIcon = ic.sites.argIcon.att
        if argIcon is None:
            return ic
        if not (argIcon.__class__ is typing.CursorParenIcon or
         argIcon.__class__ is icon.BinOpIcon and icon.needsParens(argIcon, parentIcon)):
            self.filterRedundantParens(argIcon, ic, "leftArg")
            return ic
        # Redundant parens found: remove them
        if parentIcon is None:
            # Not sure this ever happens: arithmetic ops require parent to force parens,
            # and tuple conversion removes the redundant paren icon, itself.
            self.replaceTop(ic, argIcon)
        else:
            parentIcon.replaceChild(argIcon, parentSite)
            argIcon.layoutDirty = True
        # If the cursor was on the paren being removed, move it to the icon that has
        # taken its place (BinOp or CursorParen)
        if self.cursor.type == "icon" and self.cursor.icon is ic and \
         self.cursor.siteType == "attrOut":
            self.cursor.setToIconSite(argIcon, "attrIcon")
        return argIcon

    def redoLayout(self, topIcon):
        """Recompute layout for a top-level icon and redraw all affected icons"""
        redrawRect = self.layoutIconsInSeq(topIcon, checkAllForDirty=True)
        self.refresh(redrawRect)

class AccumRects:
    """Make one big rectangle out of all rectangles added."""
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if rect is None:
            return
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
    """ Find the top icon(s) within a list of icons (the returned icons do not have to be
     at the top of the window icon hierarchy, just the highest within the given list)."""
    iconDir = {ic:True for ic in icons}
    for ic in icons:
        for child in ic.children():
            iconDir[child] = False
    return [ic for ic, isTop in iconDir.items() if isTop]

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
