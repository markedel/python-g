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

WINDOW_BG_COLOR = (255, 255, 255)
RECT_SELECT_COLOR = (128, 128, 255, 255)

DEFAULT_WINDOW_SIZE = (800, 800)
DRAG_THRESHOLD = 2

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

SITE_SELECT_DIST = 8

# How far to the left of an icon does the statement select/drag band extend
SEQ_SELECT_WIDTH = 15

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
            size = DEFAULT_WINDOW_SIZE
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
        self.top.bind("<Control-Return>", self._execCb)
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

        self.listPopup = tk.Menu(self.imgFrame, tearoff=0)
        self.listPopupVal = tk.StringVar()
        self.listPopup.add_radiobutton(label="Tuple", variable=self.listPopupVal,
         command=self._listPopupCb, value="(")
        self.listPopup.add_radiobutton(label="List", variable=self.listPopupVal,
         command=self._listPopupCb, value="[")
        self.listPopup.add_radiobutton(label="Set", variable=self.listPopupVal,
         command=self._listPopupCb, value="{")
        self.listPopup.add_radiobutton(label="Params", variable=self.listPopupVal,
         command=self._listPopupCb, value="p")
        self.listPopup.entryconfig("Set", state=tk.DISABLED)
        self.listPopup.entryconfig("Params", state=tk.DISABLED)
        self.listPopupIcon = None

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
        self.inStmtSelect = False
        self.lastStmtHighlightRects = None
        self.rectSelectInitialStates = {}

        self.topIcons = []
        self.image = Image.new('RGB', (width, height), color=WINDOW_BG_COLOR)
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
        selectedIcons = self.selectedIcons()
        lastMenuEntry = self.popup.index(tk.END)
        # Add context-sensitive items to pop-up menu
        if len(selectedIcons) == 1:
            selIcon = selectedIcons[0]
            if isinstance(selIcon, icon.ListTypeIcon):
                self.listPopupIcon = selIcon
                self.listPopupVal.set('(' if isinstance(selIcon, icon.TupleIcon) else '[')
                self.popup.add_separator()
                self.popup.add_cascade(label="Change To", menu=self.listPopup)
        # Pop it up
        self.popup.tk_popup(evt.x_root, evt.y_root, 0)
        # Remove context-sensitive items
        newLastMenuEntry = self.popup.index(tk.END)
        if newLastMenuEntry != lastMenuEntry:
            self.popup.delete(lastMenuEntry+1, newLastMenuEntry)

    def _newCb(self):
        appData.newWindow()

    def _configureCb(self, evt):
        """Called when window is initially displayed or resized"""
        if evt.width != self.image.width or evt.height != self.image.height:
            self.image = Image.new('RGB', (evt.width, evt.height), color=WINDOW_BG_COLOR)
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
            self.insertTopLevel(self.entryIcon)
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
            pendingAttr = replaceIcon.childAt('attrIcon')
            if iconParent is None:
                # Icon is at top, but may be part of a sequence
                self.entryIcon = typing.EntryIcon(None, None, window=self)
                self.replaceTop(replaceIcon, self.entryIcon)
            else:
                self.entryIcon = typing.EntryIcon(iconParent, iconParent.siteOf(replaceIcon),
                 window=self)
                iconParent.replaceChild(self.entryIcon, iconParent.siteOf(replaceIcon))
            self.entryIcon.setPendingAttr(pendingAttr)
            self.cursor.setToEntryIcon()
            self.entryIcon.addText(char)
            self._redisplayChangedEntryIcon()
        else:
            # Either no icons were selected, or multiple icons were selected (so
            # we don't know what to replace).
            typing.beep()

    def _insertEntryIconAtCursor(self, initialText):
        if self.cursor.siteType == "output":
            self.entryIcon = typing.EntryIcon(None, None, window=self)
            self.entryIcon.setPendingArg(self.cursor.icon)
            self.replaceTop(self.cursor.icon, self.entryIcon)
            self.cursor.setToEntryIcon()
        elif self.cursor.siteType in ("seqIn", "seqOut"):
            self.entryIcon = typing.EntryIcon(None, None, window=self,
             location=self.cursor.icon.rect[:2])
            before = self.cursor.siteType == "seqIn"
            icon.insertSeq(self.entryIcon, self.cursor.icon, before=before)
            self.cursor.setToEntryIcon()
            self.insertTopLevel(self.entryIcon)
        else:  # Cursor site type is input or attrIn
            self.entryIcon = typing.EntryIcon(self.cursor.icon, self.cursor.site,
             window=self)
            pendingArg = self.cursor.icon.childAt(self.cursor.site)
            self.cursor.icon.replaceChild(self.entryIcon, self.cursor.site)
            if self.cursor.site == 'attrIcon':
                self.entryIcon.setPendingAttr(pendingArg)
            else:
                self.entryIcon.setPendingArg(pendingArg)
            self.cursor.setToEntryIcon()
        self.entryIcon.addText(initialText)
        self._redisplayChangedEntryIcon()

    def _redisplayChangedEntryIcon(self, evt=None, oldLoc=None):
        # ... This currently operates on all of the icons in the window, and needs to be
        #      narrowed to just the top icon that held the cursor
        redrawRegion = AccumRects(oldLoc)
        if self.entryIcon is not None:
            redrawRegion.add(self.entryIcon.rect)
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
        if self.buttonDownTime is None or not (evt.state & LEFT_MOUSE_MASK):
            return
        if self.dragging is not None:
            self._updateDrag(evt)
            return
        if self.inRectSelect:
            self._updateRectSelect(evt)
            return
        if self.inStmtSelect:
            self._updateStmtSelect(evt)
            return
        # Not currently dragging, but button is down
        btnX, btnY = self.buttonDownLoc
        if abs(evt.x - btnX) + abs(evt.y - btnY) <= DRAG_THRESHOLD:
            return  # Mouse has not moved sufficiently to start a drag
        # Start a drag
        ic = self.findIconAt(btnX, btnY)
        if ic is None:
            # If nothing was clicked, start a rectangular selection
            seqSiteIc = self._leftOfSeq(evt.x, evt.y)
            if seqSiteIc is not None:
                self._startStmtSelect(seqSiteIc, evt)
            else:
                self._startRectSelect(evt)
        elif evt.state & SHIFT_MASK:
            self._startRectSelect(evt)
        elif ic.selected:
            # If a selected icon was clicked, drag all of the selected icons
            self._startDrag(evt, self.selectedIcons())
        else:
            # Otherwise, drag the icon that was clicked
            if self.doubleClickFlag:
                if hasattr(ic, 'blockEnd') or isinstance(ic, icon.BlockEnd):
                    # Double-click drag of branch icons takes just the icon and its
                    # children (without the code block)
                    if isinstance(ic, icon.BlockEnd):
                        ic = ic.primary
                    icons = list(ic.traverse())
                    icons.append(ic.blockEnd)
                    self._startDrag(evt, icons)
                else:
                    # double-click drag, ignores associativity and outer icon
                    self._startDrag(evt, list(ic.traverse()))
            # It would seem natural to drag an entire sequence by the top icon, but that
            # can also be done by double-clicking to the right of the icon then dragging.
            # Prefer to reserve that gesture for dragging the icon and its block.
            # elif ic.parent() is None and ic.hasSite('seqOut') and \
            #  ic.childAt('seqOut') is not None and ic.childAt('seqIn') is None:
            #     self._startDrag(evt, list(icon.traverseSeq(ic, hier=True)))
            elif hasattr(ic, 'blockEnd'):
                self._startDrag(evt, list(ic.traverseBlock(hier=True)))
            elif isinstance(ic, icon.BlockEnd):
                self._startDrag(evt, list(ic.primary.traverseBlock(hier=True)))
            elif ic.__class__ in (icon.ElseIcon, icon.ElifIcon):
                self._startDrag(evt, icon.elseElifBlockIcons(ic))
            else:
                self._startDrag(evt, list(self.findLeftOuterIcon(
                 self.assocGrouping(ic)).traverse()))

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
        if (ic is None or not ic.selected) and not (evt.state & SHIFT_MASK or \
         evt.state & CTRL_MASK):
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
        elif self.inStmtSelect:
            self._endStmtSelect()
            self.buttonDownTime = None
        elif self.doubleClickFlag:
            if msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
                iconToExecute = self.findIconAt(*self.buttonDownLoc)
                if iconToExecute is None:
                    ic = self._leftOfSeq(evt.x, evt.y)
                    if ic is None:
                        self.doubleClickFlag = False
                        self._delayedBtnUpActions(evt)
                        return
                    self._select(ic, op="block")
                else:
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
            ic = self._leftOfSeq(evt.x, evt.y)
            if ic is not None and ic.posOfSite('seqOut')[1] >= evt.y:
                self._select(ic, op="hier")
                return
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
        if hasattr(clickedIcon, 'blockEnd'):
            singleSel.append(clickedIcon.blockEnd)
            hierSel.append(clickedIcon.blockEnd)
        if not currentSel:
            if siteIcon is not None and (not siteSelected or site != self.cursor.site):
                return "moveCursor"
            return "select"
        if currentSel == singleSel:
            if hierSel == currentSel:
                if leftSel == currentSel:
                    return "moveCursor"
                return "left"
            return "hier"
        if currentSel == hierSel:
            if hasattr(clickedIcon, 'blockEnd'):
                return "icAndblock"
            if leftSel == currentSel:
                return "moveCursor"
            return "left"
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
        clipIcons = icon.clipboardRepr(selectedIcons, (-xOff, -yOff))
        clipTxt = icon.textRepr(selectedIcons)
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
        if pastedIcons is None or len(pastedIcons) == 0:
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

    def _backspaceCb(self, evt=None):
        if self.entryIcon is None:
            selectedIcons = self.selectedIcons()
            if len(selectedIcons) > 0:
                self.removeIcons(selectedIcons)
            elif self.cursor.type == "icon":
                self._backspaceIcon(evt)
        else:
            topIcon = self.entryIcon.topLevelParent()
            redrawRect = topIcon.hierRect()
            self.entryIcon.backspace()
            self._redisplayChangedEntryIcon(evt, redrawRect)

    def _backspaceIcon(self, evt):
        if self.cursor.type != 'icon' or self.cursor.site in ('output', 'seqIn', 'seqOut'):
            return
        ic = self.cursor.icon
        # For different types of icon, the method for re-editing is different.  For
        # identifiers, strings, and numeric constants, it's simply replacing the icon
        # with an entry icon containing the text of the icon.  For unary operators.
        # it's similar, just the argument needs to be attached to the pendingArgument
        # site on the entry icon.  Tuples, lists, and sets, use the same mechanism as
        # as the context menu.  Binary operations are more complicated (see code below).
        if isinstance(ic, icon.TextIcon) or isinstance(ic, icon.UnaryOpIcon) or \
         isinstance(ic, icon.AttrIcon):
            if isinstance(ic, icon.UnaryOpIcon):
                text = ic.operator
            elif isinstance(ic, icon.AttrIcon):
                text = "." + ic.name
            elif isinstance(ic, icon.NumericIcon):
                text = ic.text
            else:
                text = ic.name
            self._backspaceIconToEntry(evt, ic, text, self.cursor.site)

        elif isinstance(ic, icon.ListTypeIcon) or ic.__class__ in (icon.CallIcon,
         icon.DefIcon):
            siteName, index = icon.splitSeriesSiteId(self.cursor.site)
            if self.cursor.site == "attrIcon" or index == 0:
                # On backspace in to a list or tuple from the outside, or from the first
                # argument site
                argIcons = ic.argIcons()
                if len([i for i in argIcons if i != None]) == 0:
                    # Delete the list if it's empty
                    parent = ic.parent()
                    if parent is not None:
                        parentSite = parent.siteOf(ic)
                    self.removeIcons([ic])
                    if parent is not None:
                        self.cursor.setToIconSite(parent, parentSite)
                elif self.cursor.site == "attrIcon":
                    # Move in to the list if it's not empty and bs is from attribute site
                    lastIdx = len(argIcons) - 1
                    if argIcons[lastIdx] is None:
                        self.cursor.setToIconSite(ic, "argIcons", lastIdx)
                    else:
                        rightmostIcon = icon.findLastAttrIcon(argIcons[lastIdx])
                        rightmostIcon, rightmostSite = typing.rightmostSite(rightmostIcon)
                        self.cursor.setToIconSite(rightmostIcon, rightmostSite)
                    return
                else:
                    # Pop up context menu to change type if it's not empty and bs is from
                    # the first argument site
                    self.listPopupIcon = ic
                    self.listPopupVal.set('(' if isinstance(ic, icon.TupleIcon) else '[')
                    # Tkinter's pop-up grab does not allow accelerator keys to operate
                    # while up, which is unfortunate as you'd really like to type [ or (
                    self.listPopup.tk_popup(evt.x_root, evt.y_root, 0)
            else:
                # Cursor is on comma input.  Delete if empty or previous site is empty
                prevSite = icon.makeSeriesSiteId(siteName, index-1)
                childAtCursor = ic.childAt(self.cursor.site)
                if childAtCursor and ic.childAt(prevSite):
                    typing.beep()
                    return
                topIcon = ic.topLevelParent()
                redrawRegion = AccumRects(topIcon.hierRect())
                if not ic.childAt(prevSite):
                    ic.removeEmptySeriesSite(prevSite)
                    self.cursor.setToIconSite(ic, prevSite)
                else:
                    rightmostIcon = icon.findLastAttrIcon(ic.childAt(prevSite))
                    rightmostIcon, rightmostSite = typing.rightmostSite(rightmostIcon)
                    ic.removeEmptySeriesSite(self.cursor.site)
                    self.cursor.setToIconSite(rightmostIcon, rightmostSite)
                redrawRegion.add(self.layoutDirtyIcons())
                self.refresh(redrawRegion.get())

        elif isinstance(ic, icon.SubscriptIcon):
            if self.cursor.site in ('indexIcon', 'attrIcon'):
                # Cursor is on attribute site or index site
                if ic.childAt('indexIcon') or \
                 ic.hasSite('upperIcon') and ic.childAt('upperIcon') or \
                 ic.hasSite('stepIcon') and ic.childAt('stepIcon'):
                    # Icon is not empty.
                    if self.cursor.site == 'attrIcon':
                        # If cursor is on attr site, move it to end of args
                        for siteId in ('stepIcon', 'upperIcon', 'indexIcon'):
                            if ic.hasSite(siteId):
                                break
                        siteIcon = ic.childAt(siteId)
                        if siteIcon:
                            rightIcon = icon.findLastAttrIcon(siteIcon)
                            rightIcon, rightSite = typing.rightmostSite(rightIcon)
                            self.cursor.setToIconSite(rightIcon, rightSite)
                        else:
                            self.cursor.setToIconSite(ic, siteId)
                    else:
                        # If cursor is on the first subscript site, select it and children
                        self._select(ic, op='hier')
                else:
                    # Icon is empty, remove
                    parent = ic.parent()
                    self.removeIcons([ic])
                    if parent is not None:
                        self.cursor.setToIconSite(parent, 'attrIcon')
                return
            # Site is after a colon.  Try to remove it
            redrawRegion = AccumRects(ic.topLevelParent().hierRect())
            if self.cursor.site == 'upperIcon':
                # Remove first colon
                mergeSite1 = 'indexIcon'
                mergeSite2 = 'upperIcon'
            else:
                # Remove second colon
                mergeSite1 = 'upperIcon'
                mergeSite2 = 'stepIcon'
            mergeIcon1 = ic.childAt(mergeSite1)
            mergeIcon2 = ic.childAt(mergeSite2)
            if mergeIcon2 is None:
                # Site after colon is empty (no need to merge)
                pass
            elif mergeIcon1 is None:
                # Site before colon is empty, move the icon after the colon to it
                ic.replaceChild(mergeIcon2, mergeSite1)
            elif mergeIcon1.hasSite('attrIcon'):
                # Site before colon is not empty, but has site for entry icon
                self.entryIcon = typing.EntryIcon(mergeIcon1, 'attrIcon', window=self)
                self.entryIcon.setPendingArg(mergeIcon2)
                mergeIcon1.replaceChild(self.entryIcon, 'attrIcon')
            else:
                # Can't safely remove the colon
                typing.beep()
                return
            # If there is a step site that wasn't part of the merge, shift it.
            if ic.hasSite('stepIcon') and mergeSite2 != 'stepIcon':
                moveIcon = ic.childAt('stepIcon')
                ic.replaceChild(moveIcon, 'upperIcon')
            # Clear the site to be removed (may not be necessary, but may be safer) and
            # remove the colon (colonectomy)
            if ic.hasSite('stepIcon'):
                ic.replaceChild(None, 'stepIcon')
                ic.changeNumSubscripts(2)
            else:
                ic.replaceChild(None, 'upperIcon')
                ic.changeNumSubscripts(1)
            # Place the cursor or new entry icon, and redraw
            if self.entryIcon is None:
                if mergeIcon2 is None and mergeIcon1 is not None and \
                 mergeIcon1.hasSite('attrIcon'):
                    self.cursor.setToIconSite(mergeIcon1, "attrIcon")
                else:
                    self.cursor.setToIconSite(ic, mergeSite1)
                redrawRegion.add(self.layoutDirtyIcons())
                self.refresh(redrawRegion.get())
            else:
                self.cursor.setToEntryIcon()
                self._redisplayChangedEntryIcon(evt, redrawRegion.get())

        elif isinstance(ic, typing.CursorParenIcon):
            arg = ic.sites.argIcon.att
            if self.cursor.site == 'attrIcon':
                # Cursor is on attribute site of right paren.  Move cursor in
                if arg is None:
                    cursIc = arg
                    cursSite = 'argIcon'
                else:
                    cursIc, cursSite =  typing.rightmostSite(icon.findLastAttrIcon(arg))
                self.cursor.setToIconSite(cursIc, cursSite)
            else:
                # Cursor is on argument site: remove if empty, otherwise, select
                if arg is None:
                    self.removeIcons([arg])
                else:
                    self._select(ic, op='hier')

        elif isinstance(ic, icon.BinOpIcon) or isinstance(ic, icon.DivideIcon):
            # Binary operations replace the icon with its left argument and attach the
            # entry icon to its attribute site, with the right argument as a pending
            # argument.
            if self.cursor.site == 'attrIcon':
                # Cursor is on attribute site of right paren.  Move cursor in
                if isinstance(ic, icon.DivideIcon):
                    rightArg = ic.sites.bottomArg.att
                else:
                    rightArg = ic.rightArg()
                if rightArg is None:
                    cursorIc = ic
                    cursorSite = 'leftArg'
                else:
                    cursorIc, cursorSite = typing.rightmostSite(
                     icon.findLastAttrIcon(rightArg))
                self.cursor.setToIconSite(cursorIc, cursorSite)
                return
            redrawRect = ic.topLevelParent().hierRect()
            parent = ic.parent()
            if isinstance(ic, icon.DivideIcon):
                leftArg = ic.sites.topArg.att
                rightArg = ic.sites.bottomArg.att
                op = '//' if ic.floorDiv else '/'
            else:
                leftArg = ic.leftArg()
                rightArg = ic.rightArg()
                op = ic.operator
            if parent is None and leftArg is None:
                entryAttachedIcon, entryAttachedSite = None, None
            elif parent is not None and leftArg is None:
                entryAttachedIcon = parent
                entryAttachedSite = parent.siteOf(ic)
            else:  # leftArg is not None, attach to that
                # Ignore auto parens because we are removing the supporting operator
                entryAttachedIcon, entryAttachedSite = typing.rightmostSite(
                 icon.findLastAttrIcon(leftArg), ignoreAutoParens=True)
            self.entryIcon = typing.EntryIcon(entryAttachedIcon, entryAttachedSite,
                initialString=op, window=self)
            if leftArg is not None:
                leftArg.replaceChild(None, 'output')
            if rightArg is not None:
                rightArg.replaceChild(None, 'output')
                self.entryIcon.setPendingArg(rightArg)
            if parent is None:
                if leftArg is None:
                    self.replaceTop(ic, self.entryIcon)
                else:
                    self.replaceTop(ic, leftArg)
                    entryAttachedIcon.replaceChild(self.entryIcon, entryAttachedSite)
            else:
                parentSite = parent.siteOf(ic)
                if leftArg is not None:
                    parent.replaceChild(leftArg, parentSite)
                entryAttachedIcon.replaceChild(self.entryIcon, entryAttachedSite)
            if isinstance(ic, icon.DivideIcon):
                ic.replaceChild(None, 'topArg')
                ic.replaceChild(None, 'bottomArg')
            else:
                ic.replaceChild(None, 'leftArg')
                ic.replaceChild(None, 'rightArg')
            self.cursor.setToEntryIcon()
            self._redisplayChangedEntryIcon(evt, redrawRect)

        elif ic.__class__ in (icon.YieldIcon, icon.ReturnIcon):
            siteName, index = icon.splitSeriesSiteId(self.cursor.site)
            if siteName == "values" and index is 0:
                # Cursor is on first input site.  Remove icon and replace with cursor
                valueIcons = [s.att for s in ic.sites.values if s.att is not None]
                text = "return" if isinstance(ic, icon.ReturnIcon) else "yield"
                if len(valueIcons) in (0, 1):
                    # Zero or one argument, convert to entry icon (with pending arg if
                    # there was an argument)
                    if len(valueIcons) == 1:
                        pendingArgSite = ic.siteOf(valueIcons[0])
                    else:
                        pendingArgSite = None
                    self._backspaceIconToEntry(evt, ic, text, pendingArgSite)
                else:
                    # Multiple remaining arguments: convert to tuple with entry icon as
                    # first element
                    redrawRegion = AccumRects(ic.topLevelParent().hierRect())
                    valueIcons = [s.att for s in ic.sites.values]
                    newTuple = icon.TupleIcon(window=self, noParens=True)
                    self.entryIcon = typing.EntryIcon(newTuple, 'argIcons_0',
                     initialString= text, window=self)
                    newTuple.replaceChild(self.entryIcon, "argIcons_0")
                    for i, arg in enumerate(valueIcons):
                        if i == 0:
                            self.entryIcon.setPendingArg(arg)
                        else:
                            if arg is not None:
                                ic.replaceChild(None, ic.siteOf(arg))
                            newTuple.insertChild(arg, "argIcons", i)
                    parent = ic.parent()
                    if parent is None:
                        self.replaceTop(ic, newTuple)
                    else:
                        parentSite = parent.siteOf(ic)
                        parent.replaceChild(newTuple, parentSite)
                    self.cursor.setToEntryIcon()
                    self._redisplayChangedEntryIcon(evt, redrawRegion.get())
            elif siteName == "values":
                # Cursor is on comma input.  Delete if empty or previous site is empty
                prevSite = icon.makeSeriesSiteId(siteName, index-1)
                childAtCursor = ic.childAt(self.cursor.site)
                if childAtCursor and ic.childAt(prevSite):
                    typing.beep()
                    return
                topIcon = ic.topLevelParent()
                redrawRegion = AccumRects(topIcon.hierRect())
                if not ic.childAt(prevSite):
                    ic.removeEmptySeriesSite(prevSite)
                    self.cursor.setToIconSite(ic, prevSite)
                else:
                    rightmostIcon = icon.findLastAttrIcon(ic.childAt(prevSite))
                    rightmostIcon, rightmostSite = typing.rightmostSite(rightmostIcon)
                    ic.removeEmptySeriesSite(self.cursor.site)
                    self.cursor.setToIconSite(rightmostIcon, rightmostSite)
                redrawRegion.add(self.layoutDirtyIcons())
                self.refresh(redrawRegion.get())
                self.undo.addBoundary()

        elif isinstance(ic, icon.AugmentedAssignIcon):
            siteName, index = icon.splitSeriesSiteId(self.cursor.site)
            if siteName == "values" and index is 0:
                # Cursor is on first input site.  Remove icon and replace with cursor
                text = ic.op + '='
                valueIcons = [s.att for s in ic.sites.values if s.att is not None]
                targetIcon = ic.childAt("targetIcon")
                if len(valueIcons) in (0, 1):
                    # Zero or one argument, convert to entry icon (with pending arg if
                    # there was an argument) attached to name icon
                    redrawRegion = AccumRects(ic.topLevelParent().hierRect())
                    if ic.parent() is not None:
                        print('AugmentedAssign has parent?????')
                        return
                    if targetIcon is None:
                        self.entryIcon = typing.EntryIcon(None, None,
                         initialString=text, window=self)
                        self.replaceTop(ic, self.entryIcon)
                    else:
                        self.entryIcon =  typing.EntryIcon(targetIcon, 'attrIcon',
                         initialString=text, window=self)
                        self.replaceTop(ic, targetIcon)
                        targetIcon.replaceChild(self.entryIcon, 'attrIcon')
                    if len(valueIcons) == 1:
                        self.entryIcon.setPendingArg(valueIcons[0])
                else:
                    # Multiple remaining arguments: convert to tuple with entry icon as
                    # first element
                    redrawRegion = AccumRects(ic.topLevelParent().hierRect())
                    valueIcons = [s.att for s in ic.sites.values if s.att is not None]
                    newTuple = icon.TupleIcon(window=self, noParens=True)
                    if targetIcon is None:
                        self.entryIcon = typing.EntryIcon(newTuple, 'argIcons_0',
                         initialString=text, window=self)
                        newTuple.replaceChild(self.entryIcon, "argIcons_0")
                    else:
                        self.entryIcon = typing.EntryIcon(targetIcon, 'attrIcon',
                         initialString=text, window=self)
                        targetIcon.replaceChild(self.entryIcon, 'attrIcon')
                        newTuple.replaceChild(targetIcon, 'argIcons_0')
                    for i, arg in enumerate(valueIcons):
                        if i == 0:
                            self.entryIcon.setPendingArg(arg)
                        else:
                            ic.replaceChild(None, ic.siteOf(arg))
                            newTuple.insertChild(arg, "argIcons", i)
                    self.replaceTop(ic, newTuple)
                self.cursor.setToEntryIcon()
                self._redisplayChangedEntryIcon(evt, redrawRegion.get())
            elif siteName == "values":
                # Cursor is on comma input.  Delete if empty or previous site is empty
                prevSite = icon.makeSeriesSiteId(siteName, index-1)
                childAtCursor = ic.childAt(self.cursor.site)
                if childAtCursor and ic.childAt(prevSite):
                    typing.beep()
                    return
                topIcon = ic.topLevelParent()
                redrawRegion = AccumRects(topIcon.hierRect())
                if not ic.childAt(prevSite):
                    ic.removeEmptySeriesSite(prevSite)
                    self.cursor.setToIconSite(ic, prevSite)
                else:
                    rightmostIcon = icon.findLastAttrIcon(ic.childAt(prevSite))
                    rightmostIcon, rightmostSite = typing.rightmostSite(rightmostIcon)
                    ic.removeEmptySeriesSite(self.cursor.site)
                    self.cursor.setToIconSite(rightmostIcon, rightmostSite)
                redrawRegion.add(self.layoutDirtyIcons())
                self.refresh(redrawRegion.get())
                self.undo.addBoundary()

        elif isinstance(ic, icon.AssignIcon):
            siteName, index = icon.splitSeriesSiteId(self.cursor.site)
            topIcon = ic.topLevelParent()
            redrawRegion = AccumRects(topIcon.hierRect())
            if index == 0:
                if siteName == "targets0":
                    return
                if siteName == "values" and not hasattr(ic.sites, 'targets1'):
                    # This is the only '=' in the assignment, convert it to a tuple
                    argIcons = [site.att for site in ic.sites.targets0]
                    numTargets = len(argIcons)
                    argIcons += [site.att for site in ic.sites.values]
                    newTuple = icon.TupleIcon(window=self, noParens=True)
                    for i, arg in enumerate(argIcons):
                        ic.replaceChild(None, ic.siteOf(arg))
                        newTuple.insertChild(arg, "argIcons", i)
                    parent = ic.parent()
                    if parent is None:
                        self.replaceTop(ic, newTuple)
                    else:
                        # I don't think this is possible, remove if print never appears
                        print("Assign icon has parent?????")
                        parentSite = parent.siteOf(ic)
                        parent.replaceChild(newTuple, parentSite)
                    cursorSite = icon.makeSeriesSiteId('argIcons', numTargets)
                    self.cursor.setToIconSite(newTuple, cursorSite)
                else:
                    # Merge lists around '=' to convert it to ','
                    topIcon = ic.topLevelParent()
                    redrawRegion = AccumRects(topIcon.hierRect())
                    if siteName == "values":
                        removetgtGrpIdx = len(ic.tgtLists) - 1
                        srcSite = "targets%d" % removetgtGrpIdx
                        destSite = "values"
                        destIdx = 0
                        cursorIdx = len(getattr(ic.sites, srcSite)) - 1
                    else:
                        srcSite = siteName
                        removetgtGrpIdx = int(siteName[7:])
                        destSite = siteName[:7] + str(removetgtGrpIdx - 1)
                        destIdx = len(getattr(ic.sites, destSite))
                        cursorIdx = destIdx - 1
                    argIcons = [site.att for site in getattr(ic.sites, srcSite)]
                    for i, arg in enumerate(argIcons):
                        ic.replaceChild(None, ic.siteOf(arg))
                        ic.insertChild(arg, destSite, destIdx + i)
                    ic.removeTargetGroup(removetgtGrpIdx)
                    cursorSite = icon.makeSeriesSiteId(destSite, cursorIdx)
                    cursorIc = ic.childAt(cursorSite)
                    if cursorIc is None:
                        cursorIc = ic
                    else:
                        cursorIc, cursorSite = typing.rightmostSite(
                         icon.findLastAttrIcon(cursorIc))
                    self.cursor.setToIconSite(cursorIc, cursorSite)
            else:
                # Cursor is on comma input.  Delete if empty or previous site is empty
                prevSite = icon.makeSeriesSiteId(siteName, index-1)
                childAtCursor = ic.childAt(self.cursor.site)
                if childAtCursor and ic.childAt(prevSite):
                    typing.beep()
                    return
                topIcon = ic.topLevelParent()
                redrawRegion = AccumRects(topIcon.hierRect())
                if not ic.childAt(prevSite):
                    ic.removeEmptySeriesSite(prevSite)
                    self.cursor.setToIconSite(ic, prevSite)
                else:
                    rightmostIcon = icon.findLastAttrIcon(ic.childAt(prevSite))
                    rightmostIcon, rightmostSite = typing.rightmostSite(rightmostIcon)
                    ic.removeEmptySeriesSite(self.cursor.site)
                    self.cursor.setToIconSite(rightmostIcon, rightmostSite)
            redrawRegion.add(self.layoutDirtyIcons())
            self.refresh(redrawRegion.get())
            self.undo.addBoundary()

    def _backspaceIconToEntry(self, evt, ic, entryText, pendingArgSite=None):
        """Replace the icon holding the cursor with the entry icon, pre-loaded with text,
        entryText"""
        redrawRegion = AccumRects(ic.topLevelParent().hierRect())
        parent = ic.parent()
        if parent is None:
            self.entryIcon = typing.EntryIcon(None, None, initialString=entryText,
                window=self)
            self.replaceTop(ic, self.entryIcon)
        else:
            parentSite = parent.siteOf(ic)
            self.entryIcon = typing.EntryIcon(parent, parentSite,
                initialString=entryText, window=self)
            parent.replaceChild(self.entryIcon, parentSite)
        if pendingArgSite is not None:
            child = ic.childAt(pendingArgSite)
            if child is not None:
                siteType = ic.typeOf(pendingArgSite)
                if siteType == "input":
                    self.entryIcon.setPendingArg(child)
                elif siteType == "attrIn":
                    self.entryIcon.setPendingAttr(child)
        self.cursor.setToEntryIcon()
        self._redisplayChangedEntryIcon(evt, redrawRegion.get())

    def _listPopupCb(self):
        char = self.listPopupVal.get()
        fromIcon = self.listPopupIcon
        if char == "[" and not isinstance(fromIcon, icon.ListIcon):
            ic = icon.ListIcon(fromIcon.window)
        elif char == "(" and not isinstance(fromIcon, icon.TupleIcon):
            ic = icon.TupleIcon(fromIcon.window)
        else:
            return
        topIcon = fromIcon.topLevelParent()
        redrawRegion = AccumRects(topIcon.hierRect())
        argIcons = fromIcon.argIcons()
        for i, arg in enumerate(argIcons):
            fromIcon.replaceChild(None, fromIcon.siteOf(arg))
            ic.insertChild(arg, "argIcons", i)
        attrIcon = fromIcon.sites.attrIcon.att
        fromIcon.replaceChild(None, 'attrIcon')
        ic.replaceChild(attrIcon, 'attrIcon')
        parent = fromIcon.parent()
        if parent is None:
            self.replaceTop(fromIcon, ic)
        else:
            parentSite = parent.siteOf(fromIcon)
            parent.replaceChild(ic, parentSite)
        self.cursor.setToIconSite(ic, self.cursor.site)
        redrawRegion.add(self.layoutDirtyIcons())
        self.refresh(redrawRegion.get())

    def _arrowCb(self, evt):
        if self.cursor.type is None:
            selected = self.selectedIcons()
            if selected:
                self.cursor.arrowKeyWithSelection(evt, selected)
            return
        if not evt.state & SHIFT_MASK:
            self.unselectAll()
        self.cursor.processArrowKey(evt)

    def _cancelCb(self, evt=None):
        if self.entryIcon is not None:
            oldLoc = self.entryIcon.hierRect()
            self.entryIcon.remove()
            self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
        else:
            self.cursor.removeCursor()
        self._cancelDrag()

    def _enterCb(self, evt):
        """Move Entry icon after the top-level icon where the cursor is found."""
        if not self._completeEntry(evt):
            return
        if self.cursor.type != "icon":
            return  # Not on an icon
        # Find the top level icon associated with the icon at the cursor
        topIcon = self.cursor.icon.topLevelParent()
        if topIcon is None or not topIcon.hasSite('seqOut'):
            return
        if evt.state & SHIFT_MASK:
            #... not correct/complete.  Need to create entry icon with pending block
            blockStartIcon = icon.findSeqStart(topIcon, toStartOfBlock=True)
            blockOwnerIcon = blockStartIcon.childAt('seqIn')
            if blockOwnerIcon is not None:
                topIcon = blockOwnerIcon.blockEnd
        self.cursor.setToIconSite(topIcon, 'seqOut')
        self._insertEntryIconAtCursor("")

    def _execCb(self, evt):
        """Execute the top level icon at the entry or icon cursor"""
        # Find the icon at the cursor.  If there's still an entry icon, try to process
        # its content before executing.
        if not self._completeEntry(evt):
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

    def _completeEntry(self, evt):
        """Attempt to finish any text entry in progress.  Returns True if successful,
        false if text remains unprocessed in the entry icon."""
        if self.entryIcon is None:
            return True
        # Add a delimiter character to force completion
        oldLoc = self.entryIcon.rect
        self.entryIcon.addText(" ")
        self._redisplayChangedEntryIcon(evt, oldLoc=oldLoc)
        # If the entry icon is still there, check if it's empty and attached to an icon.
        # If so, remove.  Otherwise, give up and fail out
        if self.entryIcon is not None and self.entryIcon.attachedIcon is not None:
            if len(self.entryIcon.text) == 0 and \
             self.entryIcon.pendingAttr() is None and \
             self.entryIcon.pendingArg() is None:
                self.cursor.setToIconSite(self.entryIcon.attachedIcon,
                 self.entryIcon.attachedSite)
                self.removeIcons([self.entryIcon])
                self.entryIcon = None
            else:
                return False
        return True

    def _startDrag(self, evt, icons, needRemove=True):
        self.dragging = icons
        # Remove the icons from the window image and handle the resulting detachments
        # re-layouts, and redrawing.
        sequences = findSeries(icons)
        if needRemove:
            self.removeIcons(self.dragging, refresh=False)
        # Refresh the whole display with icon outlines turned on
        self.refresh(redraw=True, showOutlines=True)
        # Dragging parent icons away from their children may require re-layout of the
        # (moving) parent icons, and in some cases adding icons to keep lists intact
        self.dragging += restoreSeries(sequences)
        topDraggingIcons = findTopIcons(self.dragging)
        for ic in topDraggingIcons:
            if isinstance(ic, icon.BinOpIcon) and ic.hasParens:
                ic.layoutDirty = True  # BinOp icons need to check check auto-parens
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
            ic.draw(self.dragImage, style="outline")
            # Looks better without connectors, but not willing to remove permanently, yet
            # icon.drawSeqSiteConnection(ic, image=self.dragImage)
        for ic in topDraggingIcons:
            icon.drawSeqRule(ic, image=self.dragImage)
        # Construct a master snap list for all mating sites between stationary and
        # dragged icons
        draggingOutputs = []
        draggingSeqInserts = []
        draggingAttrOuts = []
        draggingCprhOuts = []
        draggingConditionals = []
        for dragIcon in topDraggingIcons:
            dragSnapList = dragIcon.snapLists()
            for ic, (x, y), name in dragSnapList.get("output", []):
                draggingOutputs.append(((x, y), ic, name))
            for ic, (x, y), name in dragSnapList.get("seqInsert", []):
                draggingSeqInserts.append(((x, y), ic, name))
            for ic, (x, y), name in dragSnapList.get("attrOut", []):
                draggingAttrOuts.append(((x, y), ic, name))
            for ic, (x, y), name in dragSnapList.get("cprhOut", []):
                draggingCprhOuts.append(((x, y), ic, name))
            for ic, (x, y), name, siteType, test in dragSnapList.get("conditional", []):
                draggingConditionals.append(((x, y), ic, name, test))
        stationaryInputs = []
        for topIcon in self.topIcons:
            for winIcon in topIcon.traverse():
                snapLists = winIcon.snapLists()
                for ic, pos, name in snapLists.get("input", []):
                    stationaryInputs.append((pos, 0, ic, "input", name, None))
                for ic, pos, name in snapLists.get("insertInput", []):
                    stationaryInputs.append((pos, 0, ic, "insertInput", name, None))
                for ic, pos, name in snapLists.get("attrIn", []):
                    stationaryInputs.append((pos, 0, ic, "attrIn", name, None))
                for ic, pos, name in snapLists.get("insertAttr", []):
                    stationaryInputs.append((pos, 0, ic, "insertAttr", name, None))
                for ic, pos, name in snapLists.get("cprhIn", []):
                    stationaryInputs.append((pos, 0, ic, "cprhIn", name, None))
                for ic, pos, name in snapLists.get("insertCprh", []):
                    stationaryInputs.append((pos, 0, ic, "insertCprh", name, None))
                for ic, pos, name, siteType, test in snapLists.get("conditional", []):
                    stationaryInputs.append((pos, 0, ic, siteType, name, test))
                for ic, pos, name in snapLists.get("seqIn", []):
                    if ic.sites.seqIn.att is None:
                        stationaryInputs.append((pos, 0, ic, "seqIn", name, None))
                for ic, pos, name in snapLists.get("seqOut", []):
                    nextIc = ic.sites.seqOut.att
                    if nextIc is None:
                        sHgt = 0
                    else:
                        nextInX, nextInY = nextIc.posOfSite('seqIn')
                        sHgt = nextInY - pos[1]
                    stationaryInputs.append((pos, sHgt, ic, "seqOut", name, None))
        self.snapList = []
        for si in stationaryInputs:
            (sx, sy), sh, sIcon, sSiteType, sName, sTest = si
            matingSites = []
            for siteData in draggingOutputs:
                if sSiteType in ('input', 'insertInput', 'seqIn', 'seqOut'):
                    if sTest is None or sTest(sIcon, sName):
                        matingSites.append(siteData)
            for siteData in draggingAttrOuts:
                if sSiteType in ('attrIn', 'insertAttr'):
                    if sTest is None or sTest(sIcon, sName):
                        matingSites.append(siteData)
            for siteData in draggingCprhOuts:
                if sSiteType in ('cprhIn', 'insertCprh'):
                    if sTest is None or sTest(sIcon, sName):
                        matingSites.append(siteData)
            for siteData in draggingSeqInserts:
                if sSiteType in ('seqIn', 'seqOut'):
                    if sTest is None or sTest(sIcon, sName):
                        matingSites.append(siteData)
            for pos, ic, name, test in draggingConditionals:
                if test(sIcon, sName):
                    if sTest is None or sTest(ic, name):
                        matingSites.append((pos, ic, name))
            for (dx, dy), dIcon, dName in matingSites:
                self.snapList.append((sx-dx, sy-dy, sh, sIcon, dIcon, sSiteType, sName))
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
            if siteType == "input":
                topDraggedIcons.remove(movIcon)
                if icon.isSeriesSiteId(siteName) and isinstance(movIcon, icon.TupleIcon) \
                 and movIcon.noParens:  # Splice in naked tuple
                    statIcon.replaceChild(None, siteName)
                    seriesName, seriesIdx = icon.splitSeriesSiteId(siteName)
                    statIcon.insertChildren(movIcon.argIcons(), seriesName, seriesIdx)
                else:
                    statIcon.replaceChild(movIcon, siteName)
            elif siteType == "attrIn":
                topDraggedIcons.remove(movIcon)
                statIcon.replaceChild(movIcon, siteName)
            elif siteType == "insertInput":
                topDraggedIcons.remove(movIcon)
                if icon.isSeriesSiteId(siteName) and isinstance(movIcon, icon.TupleIcon) \
                 and movIcon.noParens:  # Splice in naked tuple
                    seriesName, seriesIdx = icon.splitSeriesSiteId(siteName)
                    statIcon.insertChildren(movIcon.argIcons(), seriesName, seriesIdx)
                else:
                    statIcon.insertChild(movIcon, siteName)
            elif siteType == "insertAttr":
                topDraggedIcons.remove(movIcon)
                statIcon.insertAttr(movIcon)
            elif siteType == "cprhIn":
                topDraggedIcons.remove(movIcon)
                statIcon.replaceChild(movIcon, siteName)
            elif siteType == "insertCprh":
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
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None
        # Refresh the entire display.  While refreshing a smaller area is technically
        # possible, after all the dragging and drawing, it's prudent to ensure that the
        # display remains in sync with the image pixmap
        self.refresh(redraw=True)
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
        for ic in self.findIconsInRegion(combinedRegion):
            if ic.inRectSelect(newRect):
                newSelect = (not self.rectSelectInitialStates[ic]) if toggle else True
            else:
                newSelect = self.rectSelectInitialStates[ic]
            if ic.selected != newSelect:
                ic.select(newSelect)
                redrawRegion.add(ic.rect)
        self.refresh(redrawRegion.get(), clear=False)
        l, t, r, b = newRect
        hLineImg = Image.new('RGB', (r - l, 1), color=RECT_SELECT_COLOR)
        vLineImg = Image.new('RGB', (1, b - t), color=RECT_SELECT_COLOR)
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

    def _startStmtSelect(self, seqSiteIc, evt):
        self.unselectAll()
        self.stmtSelectSeqStart = icon.findSeqStart(seqSiteIc)
        self.inStmtSelect = True
        self.lastStmtHighlightRects = None
        self._updateStmtSelect(evt)

    def _updateStmtSelect(self, evt):
        anchorY = self.buttonDownLoc[1]
        drawTop = min(anchorY, evt.y)
        drawBottom = max(anchorY, evt.y)
        # Trim selection top to start of sequence
        seqTopY = self.stmtSelectSeqStart.posOfSite('seqIn')[1]
        if drawTop < seqTopY:
            drawTop = seqTopY
        redrawRegion = AccumRects()
        # Traverse sequence of icons, selecting those whose top icons touch new range
        # and deselecting any that are selected and out of the range.  Also collect X
        # coordinate change points within the range
        xChangePoints = None
        icBottom = None
        for ic in icon.traverseSeq(self.stmtSelectSeqStart):
            seqInX, seqInY = ic.posOfSite('seqIn')
            seqOutX, seqOutY = ic.posOfSite('seqOut')
            nextIc = ic.childAt('seqOut')
            icBottom = seqOutY if nextIc is None  else nextIc.posOfSite('seqIn')[1]
            if xChangePoints is None and drawTop < icBottom:
                xChangePoints = [(seqInX, seqInY)]
            if xChangePoints is not None and seqInX != seqOutX and seqOutY <= drawBottom:
                xChangePoints.append((seqOutX, seqOutY + 2))
            needsSelect = drawBottom > seqInY and drawTop < seqOutY
            if not ic.selected and needsSelect or ic.selected and not needsSelect:
                for selIc in ic.traverse():
                    selIc.select(needsSelect)
                    redrawRegion.add(selIc.rect)
            if seqInY < anchorY < seqOutY:
                if drawTop > seqInY:  # If user started next to icon, highlight it fully
                    drawTop = seqInY
                if drawBottom  < seqOutY:
                    drawBottom = seqOutY
        # Trim selection bottom to end of sequence
        if drawBottom > icBottom:
            drawBottom = icBottom
        # Compute the selection and deselection rectangles from the change points
        prevX = None
        for x, y in xChangePoints:
            if y > drawTop:
                break
            prevX = x
        drawRects = [(prevX - SEQ_SELECT_WIDTH, drawTop, prevX, drawBottom)]
        for x, y in xChangePoints:
            if drawBottom > y > drawTop and drawRects is not None:
                splitL, splitT, splitR, splitB = drawRects[-1]
                drawRects[-1] = (splitL, splitT, splitR, y)
                drawRects.append((x - SEQ_SELECT_WIDTH, y, x, drawBottom))
        # Refresh selection changes and clear erase areas
        if self.lastStmtHighlightRects is not None:
            for eraseRect in self.lastStmtHighlightRects:
                redrawRegion.add(eraseRect)
        self.refresh(redrawRegion.get(), clear=False)
        # Draw the selection shading
        for drawRect in drawRects:
            image = self.image.crop(drawRect)
            colorImg = Image.new('RGB', (image.width, image.height), color=(0, 0, 255)) # color=icon.SELECT_TINT)
            selImg = Image.blend(image, colorImg, .15)
            self.drawImage(selImg, drawRect[:2])
        self.lastStmtHighlightRects = drawRects

    def _endStmtSelect(self):
        redrawRegion = AccumRects()
        self.inStmtSelect = False
        # Erase the shaded zone
        if self.lastStmtHighlightRects is not None:
            for eraseRect in self.lastStmtHighlightRects:
                redrawRegion.add(eraseRect)
        self.refresh(redrawRegion.get(), clear=False)
        self.lastStmtHighlightRects = None

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
                self.removeIcons(list(lastResultIcon.traverse()))
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
        self.insertTopLevel(resultIcon)
        resultIcon.layout()
        resultRect = resultIcon.hierRect()
        for ic in resultIcon.traverse():
            ic.select()
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
            style = "error" if ic==excep.icon else None
            ic.draw(clip=iconRect, style=style)
        self.refresh(iconRect, redraw=False)
        tkinter.messagebox.showerror("Error Executing", message=excep.message)
        for ic in excep.icon.traverse():
            ic.draw(clip=iconRect)
        self.refresh(iconRect, redraw=False)

    def _select(self, ic, op='select'):
        """Change the selection.  Options are 'select': selects single icon, 'toggle':
        changes the state of a single icon, 'add': adds a single icon to the selection,
        'hier': changes the selection to the icon and it's children, 'left': changes
        the selection to the icon and associated expression for which it is the
        leftmost component, 'block' changes the selection to the entire code block
        containing ic"""
        if op in ('select', 'hier', 'left', 'block'):
            self.unselectAll()
        if ic is None or ic is self.entryIcon:
            return
        refreshRegion = AccumRects()
        if op == 'hier':
            changedIcons = list(ic.traverse())
        elif op == 'block':
            topParent = ic.topLevelParent()
            changedIcons = []
            seqStart = icon.findSeqStart(topParent, toStartOfBlock=True)
            seqEnd = icon.findSeqEnd(topParent, toEndOfBlock=True)
            for i in icon.traverseSeq(seqStart):
                changedIcons += list(i.traverse())
                if i is seqEnd:
                    break
        elif op == 'icAndblock':
            changedIcons = list(ic.traverseBlock(hier=True))
        elif op == 'left':
            changedIcons = list(self.findLeftOuterIcon(self.assocGrouping(ic)).traverse())
        else:
            changedIcons = [ic]
        for ic in changedIcons:
            refreshRegion.add(ic.rect)
            if op is 'toggle':
                ic.select(not ic.selected)
            else:
                ic.select()
        self.refresh(refreshRegion.get(), clear=False)
        self.cursor.removeCursor()

    def unselectAll(self):
        refreshRegion = AccumRects()
        selectedIcons = self.selectedIcons()
        if len(selectedIcons) == 0:
            return
        for ic in selectedIcons:
            refreshRegion.add(ic.rect)
            ic.select(False)
        self.refresh(refreshRegion.get(), clear=False)

    def redraw(self, region=None, clear=True, showOutlines=False):
        """Cause all icons to redraw to the pseudo-framebuffer (call refresh to transfer
        from there to the display).  Setting clear to False suppresses clearing the
        region to the background color before redrawing."""
        if clear:
            self.clearBgRect(region)
        # Traverse all top icons (only way to find out what's in the region).  Correct
        # drawing depends on everything being ordered so overlaps happen properly.
        # Sequence lines must be drawn on top of the icons they connect but below any
        # icons that might be placed on top of them.
        drawStyle = "outline" if showOutlines else None
        for topIcon in self.topIcons:
            for ic in topIcon.traverse():
                if region is None or rectsTouch(region, ic.rect):
                    ic.draw(style=drawStyle)
            # Looks better without connectors, but not willing to remove permanently, yet:
            # if region is None or icon.seqConnectorTouches(topIcon, region):
            #     icon.drawSeqSiteConnection(topIcon, clip=region)
            if region is None or icon.seqRuleTouches(topIcon, region):
                icon.drawSeqRule(topIcon, clip=region)

    def refresh(self, region=None, redraw=True, clear=True, showOutlines=False):
        """Redraw any rectangle (region) of the window.  If redraw is set to False, the
         window will be refreshed from the pseudo-framebuffer (self.image).  If redraw
         is True, the framebuffer is first refreshed from the underlying icon structures.
         If no region is specified (region==None), redraw the whole window.  Setting
         clear to False will not clear the background area before redrawing."""
        if redraw:
            self.redraw(region, clear, showOutlines)
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

    def _leftOfSeq(self, x, y):
        """Return True if x,y is in the appropriate zone to start a statement-selection"""
        for ic in self.topIcons:
            if ic.hasSite('seqIn'):
                seqInX, seqInY = ic.posOfSite('seqIn')
                seqOutX, seqOutY = ic.posOfSite('seqOut')
                if y < seqInY:
                    continue
                if seqInY <= y <= seqOutY and seqInX - SEQ_SELECT_WIDTH <= x <= seqInX:
                    return ic  # Point is adjacent to icon body
                nextIc = ic.nextInSeq()
                if nextIc is None:
                    continue
                nextSeqInX, nextSeqInY = nextIc.posOfSite('seqIn')
                if seqOutY <= y < nextSeqInY and seqOutX-SEQ_SELECT_WIDTH <= x <= seqOutX:
                    return ic  # Point is adjacent to connector to next icon
        return None

    def findLeftOuterIcon(self, ic):
        """Selection method for execution and dragging:  See description in icon.py"""
        for topIcon in self.topIcons:
            leftIcon = icon.findLeftOuterIcon(ic, topIcon, btnPressLoc=self.buttonDownLoc)
            if leftIcon is not None:
                return leftIcon
        return None

    def removeIcons(self, icons, refresh=True):
        """Remove icons from window icon list redraw affected areas of the display"""
        if len(icons) == 0:
            return
        # deletedSet more efficiently determines if an icon is on the deleted list
        deletedSet = set(icons)
        detachList = []
        seqReconnectList = []
        reconnectList = {}
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
        # Find and unlink child icons from parents at deletion boundary.  Note use of
        # child icon rather than siteId in detachList because site names change as icons
        # are removed from variable-length sequences.
        addTopIcons = []
        for topIcon in self.topIcons:
            nextIcon = topIcon.nextInSeq()
            if nextIcon is not None:
                if topIcon in deletedSet and nextIcon not in deletedSet:
                    detachList.append((topIcon, nextIcon))
                    topIcon.layoutDirty = True
                if topIcon not in deletedSet and nextIcon in deletedSet:
                    detachList.append((topIcon, nextIcon))
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
                        detachList.append((ic, child))
                        if child not in reconnectList:
                            addTopIcons.append(child)
                        redrawRegion.add(child.hierRect())
                    elif ic not in deletedSet and child in deletedSet:
                        detachList.append((ic, child))
                        if ic.siteOf(child) == 'attrIcon':
                            for i in icon.traverseAttrs(ic, includeStart=False):
                                if i not in deletedSet:
                                    reconnectList[i] = (ic, 'attrIcon')
                                    break
        for ic, child in detachList:
            ic.replaceChild(None, ic.siteOf(child))
        for outIcon, inIcon in seqReconnectList:
            outIcon.replaceChild(inIcon, 'seqOut')
        for outIcon, (inIcon, site) in reconnectList.items():
            inIcon.replaceChild(outIcon, site)
        # Remove unsightly "naked tuples" left behind empty by deletion of their children
        for ic, child in detachList:
            if child in deletedSet and isinstance(ic, icon.TupleIcon) and \
             ic.noParens and len(ic.children()) == 0 and ic.parent() is None and \
             ic.nextInSeq() is None and ic.prevInSeq() is None and ic in self.topIcons:
                redrawRegion.add(ic.rect)
                self.removeTop(ic)
        # Update the window's top-icon list to remove deleted icons and add those that
        # have become top icons via deletion of their parents (bring those to the front)
        self.removeTop([ic for ic in self.topIcons if ic in deletedSet])
        self.addTop(addTopIcons)
        # Redo layouts of icons affected by detachment of children
        redrawRegion.add(self.layoutDirtyIcons())
        # Redraw the area affected by the deletion
        if refresh:
            self.refresh(redrawRegion.get())
        return redrawRegion.get()

    def clearBgRect(self, rect=None):
        """Clear but don't refresh a rectangle of the window"""
        # Fill rectangle seems to go one beyond
        if rect is None:
            l, t, r, b = 0, 0, self.image.width, self.image.height
        else:
            l, t, r, b = rect
        self.draw.rectangle((l, t, r-1, b-1), fill=WINDOW_BG_COLOR)

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
        """Remove top-level icon or icons from the top level.  Does NOT remove from
        sequence (use removeIcons for that).  Also, does not re-layout or re-draw."""
        if hasattr(ic, '__iter__'):
            for i in ic:
                self.removeTop(i)
        else:
            self.undo.registerRemoveFromTopLevel(ic, ic.rect[:2], self.topIcons.index(ic))
            self.topIcons.remove(ic)
            ic.becomeTopLevel(True)  #... ??? This does not seem right

    def replaceTop(self, old, new):
        """Replace an existing top-level icon with a new icon.  If the existing icon was
         part of a sequence, replace it in the sequence.  If the icon was not part of a
         sequence place it in the same location.  If "new" will own a code block, also
         integrate its corresponding block-end icon.  Does not re-layout or re-draw."""
        self.removeTop(old)
        nextInSeq = old.nextInSeq()
        if nextInSeq:
            old.replaceChild(None, 'seqOut')
            if hasattr(new, 'blockEnd'):
                new.blockEnd.replaceChild(nextInSeq, 'seqOut')
            else:
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
        new.rect = icon.moveRect(new.rect, (newX, newY))
        if hasattr(new, 'blockEnd'):
            self.addTop((new, new.blockEnd))
        else:
            self.addTop(new)

    def addTop(self, ic):
        """Place an icon or icons on the window at the top level.  If the icon(s) are
         part of a sequence, maintain sequence order in the list, otherwise place them
         at the end of the list (last-drawn, on-top).  Does not re-layout or re-draw."""
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
            if ic.hasSite('seqIn'):
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
        self.insertTopLevel(list(addedIcons))

    def insertTopLevel(self, icons, index=None, pos=None):
        """Add icon or icons to the window's top-level icon list at a specific position
        in the list.  If index is None, append to the end.  Note that this is not
        appropriate for adding icons that are attached to sequences that have icons
        already in the window. If pos is specified, attempt to place the (single) ic at
        that position in the window."""
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
            if pos is not None:
                ic.rect = icon.moveRect(ic.rect, pos)
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
        if not seqStartIcon.hasSite('seqIn'):
            # Icon can not be laid out by sequence site.  Just lay it out by itself
            redrawRegion.add(seqStartIcon.hierRect())
            seqStartIcon.layout((x, y))
            redrawRegion.add(seqStartIcon.hierRect())
            return redrawRegion.get()
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
                if seqIc.hasSite('output'):
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
            y = seqIcNewRect[3] - 1  # Minimal line spacing (overlap icon borders)
            x = seqIc.posOfSite('seqOut')[0]
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
            iconSites = ic.snapLists(forCursor=True)
            for siteType, siteList in iconSites.items():
                for siteIcon, (x, y), siteName in siteList:
                    # Tweak site location based on cursor appearance and differentiation
                    if siteType in ("input", "output"):
                        x += 2
                    elif siteType in ("attrIn", "attrOut"):
                        y -= icon.ATTR_SITE_OFFSET
                        x += 1
                    elif siteType in "seqIn":
                        y -= 1
                    elif siteType in "seqOut":
                        y += 1
                    else:
                        continue  # not a visible site type
                    dist = (abs(evt.x - x) + abs(evt.y - y))
                    if dist < minDist or (dist == minDist and
                     minSite[2] in ("attrOut", "output")):  # Prefer inputs, for now
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
        attrIcon = ic.sites.attrIcon.att
        ic.replaceChild(None, 'attrIcon')
        if attrIcon is not None and argIcon.hasSite('attrIcon'):
            argIcon.replaceChild(attrIcon, 'attrIcon')
        # If the cursor was on the paren being removed, move it to the icon that has
        # taken its place (BinOp or CursorParen)
        if self.cursor.type == "icon" and self.cursor.icon is ic and \
         self.cursor.siteType == "attrIn":
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
        #self.animate()

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

def findSeries(icons):
    """Returns a list of groups of icons that appear on the same sequence, list, tuple,
    set, parameter list, or dictionary(disregarding intervening icons not in "icons", in
    the order that they appear in the series, and tagged with the type of series."""
    # Sequences
    series = {}
    topIcons = findTopIcons(icons)
    unsequenced = set(topIcons)
    sequences = []
    individuals = set()
    for topIc in topIcons:
        if topIc not in unsequenced:
            continue
        sequence = []
        seqStart = icon.findSeqStart(topIc)
        for ic in icon.traverseSeq(seqStart):
            if ic in unsequenced:
                sequence.append(ic)
                unsequenced.remove(ic)
        if len(sequence) > 1:
            sequences.append(sequence)
        else:
            individuals.update(sequence)
    series['sequences'] = sequences
    # Other series types (these all return as naked tuples)
    # Record icons in the list whose parents are not in the list, and cull those to
    # icons whose parents have multiple children from the same series.
    allIcons = set(icons)
    missingParents = {}
    for ic in icons:
        parent = ic.parent()
        if parent is None or parent in allIcons:
            continue
        if parent not in missingParents:
            missingParents[parent] = []
        missingParents[parent].append((ic, parent.siteOf(ic)))
    listSeries = []
    for parent, children in missingParents.items():
        if len(children) < 2:
            continue
        argGrps = {}
        for child, parentSite in children:
            if not icon.isSeriesSiteId(parentSite):
                continue
            seriesName, idx = icon.splitSeriesSiteId(parentSite)
            if seriesName not in argGrps:
                argGrps[seriesName] = []
            argGrps[seriesName].append(child)
        for seriesName, argGrp in argGrps.items():
            if len(argGrp) < 2:
                continue
            listSeries.append(argGrp)
            individuals.difference_update(argGrp)
    series['lists'] = listSeries
    series['individual'] = list(individuals)
    return series

def restoreSeries(series):
    """Connect icons into sequences and lists according to "sequences" in the format
     generated by findSeries"""
    for sequence in series['sequences']:
        prevIcon = None
        for ic in sequence:
            if ic.hasSite('seqOut'):
                ic.replaceChild(prevIcon, 'seqIn')
            prevIcon = ic
    newIcons = []
    for icons in series['lists']:
        newTuple = icon.TupleIcon(icons[0].window, noParens=True,
         location=icons[0].rect[:2])
        newTuple.insertChildren(icons, 'argIcons', 0)
        newTuple.select(icons[0].selected)
        newIcons.append(newTuple)
    return newIcons

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
