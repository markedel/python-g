# Copyright Mark Edel  All rights reserved
# Python-g main module
import tkinter as tk
import tkinter.filedialog
import ast
import os.path
import comn
import cursors
import iconsites
import icon
import blockicons
import listicons
import opicons
import nameicons
import assignicons
import entryicon
import stringicon
import parenicon
import commenticon
import undo
import filefmt
from PIL import Image, ImageDraw, ImageWin, ImageGrab
import time
import tkinter.messagebox
import ctypes
import reorderexpr

WINDOW_BG_COLOR = (255, 255, 255)
#WINDOW_BG_COLOR = (128, 128, 128)
RECT_SELECT_COLOR = (128, 128, 255, 255)

DEFAULT_WINDOW_SIZE = (800, 800)
DRAG_THRESHOLD = 2

# Tkinter event modifiers
SHIFT_MASK = 0x001
CTRL_MASK = 0x004
ALT_MASK = 0x20000
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

# How wide (pixels) are the window scroll bars
SCROLL_BAR_WIDTH = 15

# How much to scroll per push of scroll bar arrow buttons.  In a normal text editor, this
# is 1 line.  The equivalent for this font is 17 pixels
SCROLL_INCR = 17

# Scrolling a little bit beyond bottom and right of content is allowed to give room for
# cursors and seeing were we're snapping.
SCROLL_RIGHT_PAD = SCROLL_BOTTOM_PAD = 9

# Mouse wheel delta is a quantity which the industry has decided is 120 per "step" (some
# mouse wheels allow finer control than one step).  A typical text editor scrolls 3 lines
# per step.  A scale factor of .42 yields 50 pixels per step, which is a similar distance.
MOUSE_WHEEL_SCALE = 0.42

# Max. number of statements allowed in a single page.  Splitting sequences in to pages
# makes edits, scrolling, and finding icons within a region, more efficient.  It does
# so by segmenting the list of top-level icons that when a long file is edited,
# operations can be done just on the area of interest, without scanning the whole icon
# tree.  A larger value will raise the maximum file size that the program can handle
# without performance degrading.  A smaller value (up to a point) will improve
# performance for everything else.  At around 70 there a minor delay can be detected,
# but not objectionable.
PAGE_SPLIT_THRESHOLD = 100

WIN_TITLE_PREFIX = "Python-G - "

startUpTime = time.monotonic()

# Icons which automatically redirect to seqOut site if user attempts to type right-of
noAppendIcons = {blockicons.ElseIcon, blockicons.TryIcon, blockicons.FinallyIcon,
    blockicons.DefIcon, blockicons.ClassDefIcon, nameicons.PassIcon,
    nameicons.ContinueIcon, nameicons.BreakIcon}

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

class Window:
    untitledWinNum = 1

    def __init__(self, master, filename=None, size=None):
        print("start of new window")
        self.top = tk.Toplevel(master)
        self.top.bind("<Destroy>", self._destroyCb)
        if filename is None:
            self.winName = 'Untitled %d' % Window.untitledWinNum
            Window.untitledWinNum += 1
            self.filename = None
        else:
            base, ext = os.path.splitext(filename)
            if ext == ".py":
                self.winName = base + ".pyg"
                self.filename = self.winName
            else:
                self.winName = filename
                self.filename = filename
        self.top.title(WIN_TITLE_PREFIX + self.winName)
        self.frame = tk.Frame(self.top)
        self.menubar = tk.Menu(self.frame)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu, underline=0)
        menu.add_command(label="New File", accelerator="Ctrl+N", command=self._newCb)
        menu.add_command(label="Open...", accelerator="Ctrl+O", command=self._openCb)
        menu.add_separator()
        menu.add_command(label="Save", accelerator="Ctrl+S", command=self._saveCb)
        menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S",
            command=self._saveAsCb)
        menu.add_separator()
        menu.add_command(label="Close", command=self.close)
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=menu, underline=0)
        menu.add_command(label="Undo", command=self._undoCb, accelerator="Ctrl+Z")
        menu.add_command(label="Redo", command=self._redoCb, accelerator="Ctrl+Y")
        menu.add_separator()
        menu.add_command(label="Cut", command=self._cutCb, accelerator="Ctrl+X")
        menu.add_command(label="Copy", command=self._copyCb, accelerator="Ctrl+C")
        menu.add_command(label="Paste", command=self._pasteCb, accelerator="Ctrl+V")
        menu.add_command(label="Delete", command=self._deleteCb, accelerator="Delete")

        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Run", menu=menu, underline=0)
        menu.add_command(label="Execute", command=self._execCb,
                accelerator="Ctrl+Enter")
        menu.add_command(label="Update Mutables", command=self._execMutablesCb,
                accelerator="Ctrl+U")
        menu.add_command(label="Discard Mutable Edit", command=self._resyncMutablesCb,
                accelerator="Ctrl+M")

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
        self.imgFrame.bind("<MouseWheel>", self._mouseWheelCb)
        self.top.bind("<FocusIn>", self._focusInCb)
        self.top.bind("<FocusOut>", self._focusOutCb)
        self.top.bind("<Control-n>", self._newCb)
        self.top.bind("<Control-o>", self._openCb)
        self.top.bind("<Control-s>", self._saveCb)
        self.top.bind("<Control-Shift-S>", self._saveAsCb)
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
        self.top.bind("<Control-u>", self._execMutablesCb)
        self.top.bind("<Control-m>", self._resyncMutablesCb)
        self.top.bind("<Up>", self._arrowCb)
        self.top.bind("<Down>", self._arrowCb)
        self.top.bind("<Left>", self._arrowCb)
        self.top.bind("<Right>", self._arrowCb)
        self.top.bind("<Key>", self._keyCb)
        self.top.bind("<Control-d>", self._dumpCb)
        self.top.bind("<Control-l>", self._debugLayoutCb)
        self.top.bind("<Alt-l>", self._undebugLayoutCb)
        self.top.bind("<KeyRelease-Alt_L>", self._altReleaseCb)
        self.imgFrame.grid(row=0, column=0, sticky=tk.NSEW)
        self.xScrollbar = tk.Scrollbar(self.frame, orient=tk.HORIZONTAL,
         width=SCROLL_BAR_WIDTH, command=self._xScrollCb)
        self.xScrollbar.grid(row=1, column=0, sticky=tk.EW)
        self.yScrollbar = tk.Scrollbar(self.frame,
         width=SCROLL_BAR_WIDTH, command=self._yScrollCb)
        self.yScrollbar.grid(row=0, column=2, sticky=tk.NS)
        self.scrollOrigin = 0, 0
        self.scrollExtent = 0, 0, width, height
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.pack(fill=tk.BOTH, expand=True)

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

        self.buttonDownTime = None
        self.buttonDownLoc = None
        self.buttonDownState = None
        self.buttonDownIcon = None
        self.buttonDownIcPart = None
        self.doubleClickFlag = False
        self.dragging = None
        self.dragImageOffset = None
        self.dragImage = None
        self.lastDragImageRegion = None
        self.inRectSelect = False
        self.lastRectSelect = None  # Note, in image coords (not content)
        self.inStmtSelect = False
        self.lastStmtHighlightRects = None
        self.rectSelectInitialStates = {}
        self.popupIcon = None

        self.margin = 800

        # .sequences holds the first Page structure for each sequence in the window.  The
        # ordering the list controls which icons are drawn on top when sequences overlap.
        self.sequences = []
        # .topIcons maps icons at the top of the parent hierarchy to the page structures
        # (see above) that index those sequences.  When edits are made and layouts need
        # to be updated, they are batched and done per-page.
        self.topIcons = {}
        # List (set) of all icons that are currently selected in the window
        self.selectedSet = set()
        self.image = Image.new('RGB', (width, height), color=WINDOW_BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)
        self.dc = None
        self.cursor = cursors.Cursor(self, None)
        self.execResultPositions = {}
        self.undo = undo.UndoRedoList(self)
        self.macroParser = filefmt.MacroParser()
        # .iconIds holds a dictionary translating icon ID #s to icons.  Icon IDs have to
        # be in the range of positive 32-bit integers, as they are passed to the compiler
        # in the lineno field of generated asts so a stack trace can refer directly to
        # them.  They are per-window to minimize the liklihood that the limit will ever
        # be exceeded.  Icon IDs will also eventually be used by undo in place of pointers
        # to icon structures, to allow deleted icons to be reclaimed.
        self.iconIds = {}
        self.nextId = 1
        # Variables for icons executed in the window
        self.locals = {}
        self.globals = {'__windowExecContext__': {}}
        # List of mutable icons displayed in the window
        self.liveMutableIcons = set()
        # list of icons with dimmed text to receive (unnecessary) user typing when we've
        # already filled in to the right of the cursor.
        self.activeTypeovers = set()
        # Accumulates screen area needing refresh, to be processed by refreshDirty()
        self.refreshRequests = comn.AccumRects()
        # Set if icons marked with dirty layouts should also be run through redundant
        # parenthesis removal.
        self.redundantParenFilterRequested = False
        # Set on Alt+Mouse presses to suppress menu-bar highlighting, which Tkinter will
        # sometimes do when the Alt key is released
        self.suppressAltReleaseAction = False

    def openFile(self, filename):
        """Open a .pyg or .py file in the window.  Uses file type to determine whether to
        parse as Python or Python-g.  Returns True if the file was successfully opened.
        Note that an empty file returns success."""
        print("reading file...", end="")
        with open(filename) as f:
            text = f.read()
        print("done")
        _base, ext = os.path.splitext(filename)
        icons = filefmt.parseTextToIcons(text, self, source=filename,
            forImport=ext!=".pyg")
        if icons is None:
            return False
        if len(icons) == 0:
            return True
        self.addTop(icons)
        print('start layout', time.monotonic())
        redrawRect = self.layoutDirtyIcons(filterRedundantParens=False)
        print('finish layout', time.monotonic())
        print('start draw', time.monotonic())
        self.redraw(redrawRect, clear=False)
        print('finish draw', time.monotonic())
        self.refresh(redrawRect, clear=False, redraw=False)
        self.undo.addBoundary()
        return True

    def close(self):
        self.top.destroy()

    def selectedIcons(self):
        """Return a list of the icons in the window that are currently selected."""
        # Selection was initially a property of icons, but that caused performance issues
        # because finding the current selection required traversing all icons.  Now the
        # selection is held in a set, but to support existing code which does not expect
        # to see deleted icons in the selection, it must be cleaned per-use (which will
        # make performance significantly WORSE when more than half of the icons in the
        # window are selected).  It is intended that there will be a formal mechanism for
        # removing icons, after which this code can be removed.
        removeSet = set()
        for ic in self.selectedSet:
            if isStmtComment(ic):
                topParent = ic.attachedToStmt
            else:
                topParent = ic.topLevelParent()
            if topParent is None or topParent not in self.topIcons:
                print("Removing deleted icon from selection")
                removeSet.add(ic)
        self.selectedSet -= removeSet
        return list(self.selectedSet)

    def isSelected(self, ic):
        """Return True if an icon is in the current selection, False if not."""
        return ic in self.selectedSet

    def select(self, ic, select=True):
        """Add (select=True) or remove (select=False) an icon from the current selection.
        Does not redraw or mark the icon as dirty.  Use .isSelected() to read the
        selection state of an icon."""
        if select:
            self.selectedSet.add(ic)
        else:
            self.selectedSet.remove(ic)

    def clearSelection(self):
        self.selectedSet = set()

    def watchMutableIcon(self, ic):
        self.liveMutableIcons.add(ic)

    def dirtyMutableIcons(self, iconsBeingExecuted=None):
        """Returns a list of icons in the window that are mutable and have been modified
        since last updated in the window.  If iconsBeingExecuted is not None, icons
        beneath those in the list are returned as in need of update regardless if they
        have edits."""
        # Since we don't track removal of mutable icons (only addition), the list must
        # be pruned of removed icons before use:
        removeList = []
        for ic in self.liveMutableIcons:
            topParent = ic.topLevelParent()
            if topParent is None or topParent not in self.topIcons:
                removeList.append(ic)
        for ic in removeList:
            self.liveMutableIcons.remove(ic)
        # Check each displayed mutable icon for modification
        inExecTree = set()
        if iconsBeingExecuted is not None:
            for topIcon in iconsBeingExecuted:
                for ic in topIcon.traverse(includeSelf=True):
                    if ic in self.liveMutableIcons:
                        inExecTree.add(ic)
        changedList = []
        for ic in self.liveMutableIcons:
            if ic in inExecTree or (not ic.compareData(ic.object, compareContent=True)
                    and not ic.mutableModified):
                changedList.append(ic)
        return changedList

    def updateMutableIcons(self, iconsBeingExecuted=None):
        """Update any mutable icons in the window whose content has changed.  Does
        layout and redraw for changed icons."""
        # Find the highest level of the hierarchy that needs updating and do so
        needUpdate = set(self.dirtyMutableIcons(iconsBeingExecuted))
        ignore = set()
        for ic in needUpdate:
            for parent in ic.parentage(includeSelf=False):
                if parent in needUpdate:
                    ignore.add(ic)
                    break
        for ic in needUpdate:
            if ic in ignore:
                continue
            self.requestRedraw(ic.topLevelParent().hierRect(), filterRedundantParens=True)
            # Update the icon.  For the moment, this is brutal reconstruction and
            # replacement of the entire hierarchy from the data (losing selections and
            # attached comments).  This also blows away the cursor attachment (if that
            # is attached to one of the deleted icons), which is restored by a very hacky
            # method. It would be desirable to replace this with something that better
            # preserves icon identities.
            cursorPath = self.recordCursorPositionInData(ic)
            newIcon = self.objectToIcons(ic.object, updateMutable=ic)
            self.restoreCursorPositionInData(newIcon, cursorPath)

    def makeId(self, ic):
        """Return an unused icon ID number.  ID numbers correlate icons with executing
        code, via the lineno field in ASTs.  IDs are per-window as lineno field is of
        limited size."""
        # Currently creates a new ID for each request.  Eventually, this should re-use
        # IDs as icons are deleted.
        id = self.nextId
        self.nextId += 1
        if self.nextId == 2147483647:
            print('Icon ID limit Exceeded!  Save your work and close window ASAP')
        self.iconIds[id] = ic
        return id

    def _btn3Cb(self, evt):
        x, y = self.imageToContentCoord(evt.x, evt.y)
        self.popupIcon = self.findIconAt(x, y)

    def _btn3ReleaseCb(self, evt):
        popup = tk.Menu(self.imgFrame, tearoff=0)
        popup.add_command(label="Undo", command=self._undoCb, accelerator="Ctrl+Z")
        popup.add_command(label="Redo", command=self._redoCb, accelerator="Ctrl+Y")
        popup.add_separator()
        popup.add_command(label="Cut", command=self._cutCb, accelerator="Ctrl+X")
        popup.add_command(label="Copy", command=self._copyCb, accelerator="Ctrl+C")
        popup.add_command(label="Paste", command=self._pasteCb, accelerator="Ctrl+V")
        popup.add_command(label="Delete", command=self._deleteCb, accelerator="Delete")

        # Add context-sensitive items to pop-up menu
        if self.popupIcon is not None:
            if isinstance(self.popupIcon, listicons.ListTypeIcon):
                self.listPopupVal.set('(' if isinstance(self.popupIcon,
                        listicons.TupleIcon) else '[')
                popup.add_separator()
                popup.add_cascade(label="Change To", menu=self.listPopup)
            if self.popupIcon.errHighlight is not None:
                popup.add_command(label="Why Highlighted...", command=self._showSyntaxErr)
        # Pop it up
        try:
            popup.tk_popup(evt.x_root, evt.y_root, 0)
        finally:
            popup.grab_release()

    def _newCb(self, evt=None):
        appData.newWindow()

    def _openCb(self, evt=None):
        filename = tkinter.filedialog.askopenfilename(defaultextension=".pyg", filetypes=[
            ("Python-g file", ".pyg"), ("Python file", ".py"), ("Python file", ".pyw")],
            parent=self.top, title="Open")
        print("tkinter filedialog returns", repr(filename))
        if filename is None or filename == '':
            return
        existingWindow = appData.findWindowWithFile(filename)
        if existingWindow is not None:
            reload = tkinter.messagebox.askokcancel(message="Reload %s" % filename)
            if reload:
                existingWindow.top.destroy()
            else:
                return
        appData.newWindow(filename)

    def _saveCb(self, evt=None):
        if self.filename is None:
            self._saveAsCb(evt)
        else:
            self.saveFile(self.filename)

    def _saveAsCb(self, evt=None):
        filename = tkinter.filedialog.asksaveasfilename(defaultextension=".pyg",
            filetypes=[("Python-g file", ".pyg"), ("Python file", ".py"),
            ("Python file", ".pyw")], parent=self.top, title="Save As")
        if filename is None or filename == '':
            return
        self.saveFile(filename)
        _base, ext = os.path.splitext(filename)
        if ext == ".pyg":
            self.filename = filename
            self.winName = filename
            self.top.title(WIN_TITLE_PREFIX + self.winName)

    def _configureCb(self, evt):
        """Called when window is initially displayed or resized"""
        if evt.width != self.image.width or evt.height != self.image.height:
            self.image = Image.new('RGB', (evt.width, evt.height), color=WINDOW_BG_COLOR)
            self.draw = ImageDraw.Draw(self.image)
        self._updateScrollRanges()
        self.redraw()

    def _updateScrollRanges(self):
        """Update scroll bar widgets to reflect changes in window content or scrolling."""
        # Note that because dragging the scroll bars calls this function, if both don't
        # agree, a loop can occur that will iterate until they do agree.  I did not try
        # to break this loop, since it seems to both mitigate and flag inconsistencies
        # in scroll bar positioning that do occur, just be aware that it can happen.
        scrollOriginX, scrollOriginY = self.scrollOrigin
        xMin, yMin, xMax, yMax = self.scrollExtent = self._calcScrollExtent()
        contentWidth = max(1, xMax - xMin)  # Avoid division by 0 if window is empty
        contentHeight = max(1, yMax - yMin)
        barLeft = (scrollOriginX - xMin)
        barRight = (scrollOriginX + self.image.width - xMin)
        barTop = (scrollOriginY - yMin)
        barBottom = (scrollOriginY + self.image.height - yMin)
        self.xScrollbar.set(barLeft / contentWidth, barRight / contentWidth)
        self.yScrollbar.set(barTop / contentHeight, barBottom / contentHeight)
        # Remove scroll bars if no scrolling is possible
        if barLeft <= 0 and barRight >= contentWidth:
            self.xScrollbar.config(width=0)
        else:
            self.xScrollbar.config(width=SCROLL_BAR_WIDTH)
        if barTop <= 0 and barBottom >= contentHeight:
            self.yScrollbar.config(width=0)
        else:
            self.yScrollbar.config(width=SCROLL_BAR_WIDTH)

    def _calcScrollExtent(self):
        """Calculate scrolling range (minimum and maximum coordinates in the content
        coordinate system that scrolling can reach) from page lists in self.sequences."""
        xMin = yMin = xMax = yMax = 0
        scrollOriginX, scrollOriginY = self.scrollOrigin
        windowWidth, windowHeight = self.image.size
        # Page structures contain y range of page, so y extent can be based entirely on
        # them, but x extent should vary based on content within the displayed y range
        # (must include area under x scroll bar, since automatic removal will expose).
        windowBottom = scrollOriginY + windowHeight + int(self.xScrollbar.cget('width'))
        for seqStartPage in self.sequences:
            for page in seqStartPage.traversePages():
                yMin = min(page.topY, yMin)
                yMax = max(page.bottomY, yMax)
                if page.bottomY >= scrollOriginY and page.topY <= windowBottom:
                    page.applyOffset()
                    for ic in page.traverseSeq(hier=True, inclStmtComments=True):
                        l, t, r, b = ic.rect
                        if b >= scrollOriginY and t <= windowBottom:
                            xMin = min(ic.rect[0], xMin)
                            xMax = max(ic.rect[2], xMax)
        xMax += SCROLL_RIGHT_PAD
        yMax += SCROLL_BOTTOM_PAD
        if scrollOriginX < xMin:
            xMin = scrollOriginX
        if scrollOriginY < yMin:
            yMin = scrollOriginY
        if scrollOriginX + windowWidth > xMax:
            xMax = scrollOriginX + windowWidth
        if scrollOriginY + windowHeight > yMax:
            yMax = scrollOriginY + windowHeight
        # Always allow scrolling to the original 0, 0 (xMin and yMin can extend above
        # and to the left of zero so allow scrolling to see that content, but don't allow
        # scrolling beyond it).
        xMin = min(0, xMin)
        yMin = min(0, yMin)
        return xMin, yMin, xMax, yMax

    def _xScrollCb(self, scrollOp, fract, unit=None):
        scrollOriginX, scrollOriginY = self.scrollOrigin
        if scrollOp == tk.SCROLL:
            if unit == tk.UNITS:
                delta = SCROLL_INCR * int(fract)
            elif unit == tk.PAGES:
                delta = (self.image.width - SCROLL_INCR) * int(fract)
            left, top, right, bottom = self.scrollExtent
            newXOrigin = scrollOriginX + delta
            if delta < 0 and newXOrigin < min(left, 0):
                newXOrigin = min(left, 0)
            elif delta > 0 and newXOrigin + self.image.width > right:
                newXOrigin = (right - self.image.width)
            if newXOrigin != scrollOriginX:
                self.scrollOrigin = newXOrigin, scrollOriginY
        elif scrollOp == tk.MOVETO:
            xMin, yMin, xMax, yMax = self.scrollExtent
            self.scrollOrigin = xMin + int((xMax - xMin) * float(fract)), scrollOriginY
        self._updateScrollRanges()
        self.refresh(redraw=True)

    def _yScrollCb(self, scrollOp, fract, unit=None):
        scrollOriginX, scrollOriginY = self.scrollOrigin
        if scrollOp == tk.SCROLL:
            if unit == tk.UNITS:
                delta = SCROLL_INCR * int(fract)
            elif unit == tk.PAGES:
                delta = (self.image.height - SCROLL_INCR) * int(fract)
            left, top, right, bottom = self.scrollExtent
            newYOrigin = scrollOriginY + delta
            if delta < 0 and newYOrigin < top:
                newYOrigin = top
            elif delta > 0 and newYOrigin + self.image.height > bottom:
                newYOrigin = (bottom - self.image.height)
            if newYOrigin == scrollOriginY:
                return
            self.scrollOrigin = scrollOriginX, newYOrigin
        elif scrollOp == tk.MOVETO:
            xMin, yMin, xMax, yMax = self.scrollExtent
            self.scrollOrigin = scrollOriginX, yMin + int((yMax - yMin) * float(fract))
        self._updateScrollRanges()
        self.refresh(redraw=True)

    def _exposeCb(self, _evt):
        """Called when a new part of the window is exposed and needs to be redrawn"""
        self.refresh(redraw=False)

    def _keyCb(self, evt):
        if evt.state & ALT_MASK:
            return
        char = cursors.tkCharFromEvt(evt)
        if char is None:
            return
        # If there's a cursor displayed somewhere, use it, otherwise, use selection
        if self.cursor.type == "text":
            # If it's an active entry icon, feed it the character
            self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
            self.cursor.icon.addText(char)
        elif self.cursor.type == "icon":
            self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
            self._insertEntryIconAtCursor(allowOnCursorOnly=char=='#')
            self.cursor.icon.addText(char)
        elif self.cursor.type == "window":
            x, y = self.cursor.pos
            entryIcon = entryicon.EntryIcon(window=self)
            y -= entryIcon.sites.output.yOffset
            entryIcon.rect = comn.offsetRect(entryIcon.rect, x, y)
            self.addTopSingle(entryIcon, newSeq=True)
            self.cursor.setToText(entryIcon, drawNew=False)
            entryIcon.addText(char)
        elif self.cursor.type == "typeover":
            self.cursor.erase()
            ic = self.cursor.icon
            siteBefore, siteAfter, text, idx = ic.typeoverSites()
            if text[idx] == char:
                cancelTypeover = not ic.setTypeover(idx + 1, siteAfter)
            else:
                cancelTypeover = True
            if cancelTypeover:
                # Reached the end of the typeover text or user typed something
                # non-matching, move to site after
                self.cursor.setToIconSite(ic, siteAfter)
            self.refresh(ic.rect, redraw=True)
            return
        else:
            # If there's an appropriate selection, use that
            selectedIcons = findTopIcons(self.selectedIcons())
            if len(selectedIcons) == 1:
                # A single icon was selected.  Replace it and its children
                replaceIcon = selectedIcons[0]
                self.requestRedraw(replaceIcon.topLevelParent().hierRect())
                iconParent = replaceIcon.parent()
                pendingAttr = replaceIcon.childAt('attrIcon')
                if iconParent is None:
                    # Icon is at top, but may be part of a sequence
                    entryIcon = entryicon.EntryIcon(window=self)
                    self.replaceTop(replaceIcon, entryIcon)
                else:
                    entryIcon = entryicon.EntryIcon(window=self)
                    iconParent.replaceChild(entryIcon, iconParent.siteOf(replaceIcon))
                entryIcon.appendPendingArgs([pendingAttr])
                self.cursor.setToText(entryIcon, drawNew=False)
                entryIcon.addText(char)
            else:
                # Either no icons were selected, or multiple icons were selected (so
                # we don't know what to replace).
                cursors.beep()
                return
        self.refreshDirty()  # Undo boundary added within entryIcon.addText

    def _insertEntryIconAtCursor(self, allowOnCursorOnly=False):
        # Note that location is set in the entry icon for the single case where it
        # becomes the beginning of a sequence.  All others are overwritten by layout
        self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
        entryIcon = entryicon.EntryIcon(window=self,
            location=self.cursor.icon.rect[:2])
        if self.cursor.siteType == "output":
            entryIcon.appendPendingArgs([self.cursor.icon])
            self.replaceTop(self.cursor.icon, entryIcon)
        elif self.cursor.siteType == "attrOut":
            entryIcon.appendPendingArgs([self.cursor.icon])
            self.replaceTop(self.cursor.icon, entryIcon)
        elif self.cursor.siteType in ("seqIn", "seqOut"):
            before = self.cursor.siteType == "seqIn"
            icon.insertSeq(entryIcon, self.cursor.icon, before=before)
            self.addTopSingle(entryIcon)
        elif self.cursor.siteType == "attrIn":  # Cursor site type is input or attrIn
            if self.cursor.icon.__class__ in noAppendIcons and not allowOnCursorOnly:
                icon.insertSeq(entryIcon, self.cursor.icon)
                self.addTopSingle(entryIcon)
            else:
                pendingArg = self.cursor.icon.childAt(self.cursor.site)
                self.cursor.icon.replaceChild(entryIcon, self.cursor.site)
                entryIcon.appendPendingArgs([pendingArg])
        else:  # Cursor site type is input
            entryIcon = entryicon.EntryIcon(window=self)
            cursorIc, cursorSite = iconsites.lowestCoincidentSite(self.cursor.icon,
                self.cursor.site)
            if cursorIc != self.cursor.icon:
                #... leave this in until better understood
                print('Moved cursor to lowest coincident site')
            pendingArg = cursorIc.childAt(cursorSite)
            cursorIc.replaceChild(entryIcon, cursorSite)
            entryIcon.appendPendingArgs([pendingArg])
        self.cursor.setToText(entryIcon, drawNew=False)

    def watchTypeover(self, ic):
        """Register an icon with active typeover for cancellation when it's no longer
        directly ahead of the cursor or entry icon in the text-traversal path (The
        typeover state itself is maintained in the icon structure. The watch list simply
        makes those icons with active typeover, findable)."""
        self.activeTypeovers.add(ic)

    def cancelAllTypeovers(self, draw=True):
        self._refreshTypeovers([], draw)

    def updateTypeoverStates(self, draw=True):
        """Typeover is only allowed directly in front of the cursor, and goes away if
        the user would need to navigate somehow to reach it (in which case they can
        just as well navigate over it as type over it)"""
        keepAlive = set()
        if self.cursor.type == "text" and isinstance(self.cursor.icon,
                entryicon.EntryIcon):
            cursorIcon = self.cursor.icon
            cursorSite = cursorIcon.sites.firstCursorSite()
            includeCursorIcon = True
        elif self.cursor.type  == "icon" and self.cursor.site not in ('seqIn', 'seqOut'):
            cursorIcon = self.cursor.icon
            cursorSite = self.cursor.site
            includeCursorIcon = True
        elif self.cursor.type == "typeover":
            cursorIcon = self.cursor.icon
            _, cursorSite, _, _ = cursorIcon.typeoverSites()
            for _, siteAfter, _, idx in cursorIcon.typeoverSites(allRegions=True):
                if idx > 0:
                    keepAlive.add((cursorIcon, siteAfter))
                    break
            else:
                print(f'updateTypeoverStates could not find typeover cursor data')
                return
            includeCursorIcon = False
        else: # cursor type is window or on sequence site: cancel all typeovers
            self._refreshTypeovers([], draw)
            return
        # March up the hierarchy from the cursor or entry icon, finding entries in
        # self.activeTypeovers that are either directly to the right of it, or have only
        # typeover-dimmed parts between it and the entry.  This also serves to purge the
        # list of deleted entries, and anything that is not directly next to the cursor.
        for ic in cursorIcon.parentage(includeSelf=includeCursorIcon):
            rightmostIcon, rightmostSite = icon.rightmostSite(ic)
            if rightmostIcon != cursorIcon or rightmostSite != cursorSite:
                if isinstance(rightmostIcon, opicons.DivideIcon):
                    # Divide icon has *two* sites considered next-to adjacent typeover
                    # (due to how it's typed): attribute (handled above) and bottomArg
                    bottomArg = rightmostIcon.childAt('bottomArg')
                    if bottomArg is None:
                        altIcon, altSite = rightmostIcon, 'bottomArg'
                    else:
                        altIcon, altSite = icon.rightmostSite(bottomArg)
                    if altIcon == cursorIcon and altSite == cursorSite:
                        cursorIcon, cursorSite = rightmostIcon, rightmostSite
                        continue
                if ic not in self.activeTypeovers:
                    break
                typeoverSiteData = ic.typeoverSites(allRegions=True)
                foundTypeover = False
                for siteBefore, siteAfter, text, idx in typeoverSiteData:
                    activeSiteIcon = ic.childAt(siteBefore)
                    if activeSiteIcon is None:
                        rightmostIcon, rightmostSite = ic, siteBefore
                    else:
                        rightmostIcon, rightmostSite = icon.rightmostSite(activeSiteIcon)
                    if rightmostIcon == cursorIcon and rightmostSite == cursorSite:
                        keepAlive.add((ic, siteAfter))
                        cursorIcon, cursorSite = ic, siteAfter
                        foundTypeover = True
                if not foundTypeover:
                    break
        self._refreshTypeovers(keepAlive, draw)
        # If the cursor is on an icon site, check the typeover list and reset any typeover
        # that thinks it's still in the middle of the text.  (this can happen when the
        # user clicks back to a legal typeover position, rather than cursor-traversing).
        if self.cursor.type == 'icon':
            for ic in self.activeTypeovers:
                for siteBefore, siteAfter, text, idx in ic.typeoverSites(allRegions=True):
                    if idx is not None and idx != 0:
                        ic.setTypeover(0, siteAfter)
                        if draw:
                            self.refresh(ic.rect, redraw=True)

    def _refreshTypeovers(self, toPreserve, draw=True):
        """Clears all typeovers except those represented by an (icon, siteAfter) pair in
        toPreserve, then remove any icon from the typeover watch list that doesn't still
        have an active typeover.  Redraw icons whose typeovers have been removed, unless
        draw=False."""
        iconsToRemove = set(self.activeTypeovers)
        sitesToRemove = []
        for ic in self.activeTypeovers:
            for siteBefore, siteAfter, text, idx in ic.typeoverSites(allRegions=True):
                if (ic, siteAfter) in toPreserve:
                    iconsToRemove.discard(ic)
                else:
                    sitesToRemove.append((ic, siteAfter))
        for ic, siteAfter in sitesToRemove:
            topParent = ic.topLevelParent()
            if topParent is not None and topParent in self.topIcons:
                ic.setTypeover(None, siteAfter)
                if draw:
                    self.refresh(ic.rect, redraw=True)
        for ic in iconsToRemove:
            self.activeTypeovers.remove(ic)

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
            seqSiteIc = self._leftOfSeq(*self.imageToContentCoord(evt.x, evt.y))
            if seqSiteIc is not None:
                self._startStmtSelect(seqSiteIc, evt)
            else:
                self._startRectSelect(evt)
        elif evt.state & SHIFT_MASK:
            self._startRectSelect(evt)
        elif ic.isSelected():
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
                    icons = list(ic.traverse(inclStmtComment=True))
                    icons.append(ic.blockEnd)
                    self._startDrag(evt, icons)
                else:
                    # double-click drag, ignores associativity and outer icon
                    self._startDrag(evt, list(ic.traverse(inclStmtComment=True)))
            # It would seem natural to drag an entire sequence by the top icon, but that
            # can also be done by double-clicking to the right of the icon then dragging.
            # Prefer to reserve that gesture for dragging the icon and its block.
            # elif ic.parent() is None and ic.hasSite('seqOut') and \
            #  ic.childAt('seqOut') is not None and ic.childAt('seqIn') is None:
            #     self._startDrag(evt, list(icon.traverseSeq(ic, hier=True)))
            elif hasattr(ic, 'blockEnd'):
                self._startDrag(evt, list(ic.traverseBlock(hier=True,
                    inclStmtComment=True)))
            elif isinstance(ic, icon.BlockEnd):
                self._startDrag(evt, list(ic.primary.traverseBlock(hier=True,
                    inclStmtComment=True)))
            elif ic.__class__ in (blockicons.ElseIcon, blockicons.ElifIcon,
                    blockicons.ExceptIcon, blockicons.FinallyIcon):
                self._startDrag(evt, blockicons.clauseBlockIcons(ic))
            else:
                self._startDrag(evt, list(findLeftOuterIcon(self.assocGrouping(ic),
                        self.buttonDownLoc).traverse(inclStmtComment=True)))

    def _mouseWheelCb(self, evt):
        delta = -int(evt.delta * MOUSE_WHEEL_SCALE)
        scrollOriginX, scrollOriginY = self.scrollOrigin
        left, top, right, bottom = self.scrollExtent
        newYOrigin = scrollOriginY + delta
        if delta < 0 and newYOrigin < top:
            newYOrigin = top
        elif delta > 0 and newYOrigin + self.image.height > bottom:
            newYOrigin = (bottom - self.image.height)
        if newYOrigin == scrollOriginY:
            return
        self.scrollOrigin = scrollOriginX,  newYOrigin
        self._updateScrollRanges()
        self.refresh(redraw=True)

    def _focusInCb(self, evt):
        pass

    def _focusOutCb(self, evt):
        self.cursor.erase()

    def _altReleaseCb(self, evt):
        # This is a hack to stop Tkinter from sometimes doing its menubar alt-key
        # activation when an Alt+MouseButton press has occurred.  This is not ideal,
        # because we're stopping it from getting the event that it also uses to erase
        # the underlines, which it will then leave up until the next alt press.  I can't
        # find an answer to this, so probably need to look at tkinter source code.
        if self.suppressAltReleaseAction:
            self.suppressAltReleaseAction = False
            return "break"
        return None

    def _buttonPressCb(self, evt):
        if self.dragging:
            self._endDrag()
            return
        if self.buttonDownTime is not None:
            if msTime() - self.buttonDownTime < DOUBLE_CLICK_TIME:
                self.doubleClickFlag = True
                return
        x, y = self.imageToContentCoord(evt.x, evt.y)
        ic = self.findIconAt(x, y)
        if ic is not None and evt.state & ALT_MASK:
            if self.cursor.type == 'text':
                if ic is self.cursor.icon:
                    # Don't re-edit an entry icon or string we're already editing
                    if ic.click(x, y):
                        self.refreshDirty(addUndoBoundary=False)
                        self.cursor.draw()
                    return
                else:
                    self.cursor.icon.focusOut()
            entryIc, oldCursorLoc = ic.becomeEntryIcon((x, y))
            if entryIc is not None:
                self.cursor.setToText(entryIc)
                self.refreshDirty()
                # Jump the mouse cursor to correct for font and text location differences
                # after replacing the icon with the entry icon.  The icon becomeEntryIcon
                # methods return the window location where the cursor would be placed
                # were it placed in the original icon.  We then nudge the screen cursor
                # by the difference between that and the location of the new entry icon's
                # cursor in the window, thus accounting for font, spacing, and layout.
                oldCursorX, oldCursorY = oldCursorLoc
                newCursorX, newCursorY = entryIc.cursorWindowPos()
                nudgeMouseCursor(newCursorX - oldCursorX, newCursorY - oldCursorY)
            else:
                self._select(ic)
            return
        if hasattr(ic, "pointInTextArea") and ic.pointInTextArea(x, y) and not \
                ic.isSelected():
            if not (evt.state & SHIFT_MASK or evt.state & CTRL_MASK):
                self.unselectAll()
            ic.click(x, y)
            self.refreshDirty(addUndoBoundary=True)
            self.cursor.draw()
            return
        self.buttonDownTime = msTime()
        self.buttonDownLoc = x, y
        self.buttonDownIcon = ic
        self.buttonDownIcPart = None if ic is None else ic.touchesPosition(x, y)
        self.buttonDownState = evt.state
        self.doubleClickFlag = False
        if (ic is None or not ic.isSelected()) and not (evt.state & SHIFT_MASK or
                evt.state & CTRL_MASK):
            self.unselectAll()

    def _buttonReleaseCb(self, evt):
        if evt.state & ALT_MASK:
            self.suppressAltReleaseAction = True
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
                    ic = self._leftOfSeq(*self.imageToContentCoord(evt.x, evt.y))
                    if ic is None:
                        self.doubleClickFlag = False
                        self._delayedBtnUpActions(evt)
                        return
                    self._select(ic, op="block")
                else:
                    iconToExecute = findLeftOuterIcon(self.assocGrouping(iconToExecute),
                            self.buttonDownLoc)
                    if iconToExecute not in self.topIcons:
                        self.doubleClickFlag = False
                        self._delayedBtnUpActions(evt)
                        return
                    self._execute(iconToExecute)
                self.refreshDirty(addUndoBoundary=True)
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
        x, y = self.imageToContentCoord(evt.x, evt.y)
        clickedIcon = self.findIconAt(x, y)
        if clickedIcon is None:
            # Clicked on window background, move cursor
            ic = self._leftOfSeq(x, y)
            if ic is not None and ic.posOfSite('seqOut')[1] >= y:
                self._select(ic, op="hier")
                return
            siteIcon, site = self.siteSelected(evt)
            if siteIcon:
                self.cursor.setToIconSite(siteIcon, site)
            else:
                self.unselectAll()
                self.cursor.setToWindowPos((x, y))
            self.refreshDirty()
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
            siteIcon, site = self.siteSelected(evt)
            if siteIcon is not None:
                self.cursor.setToIconSite(siteIcon, site)
                self.refreshDirty()
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
        currentSel = set(self.selectedIcons())
        singleSel = {clickedIcon}
        hierSel = set(clickedIcon.traverse())
        hasHierSel = singleSel != hierSel
        leftIc = findLeftOuterIcon(self.assocGrouping(clickedIcon), self.buttonDownLoc)
        leftSel = set(leftIc.traverse())
        hasLeftSel = leftSel != hierSel
        if hasattr(leftIc, 'stmtComment'):
            commentSel = {*leftSel, leftIc.stmtComment}
            hasCommentSel = True
        else:
            commentSel = leftSel
            hasCommentSel = False
        if hasattr(clickedIcon, 'blockEnd'):
            hasBlockSel = True
            singleSel.add(clickedIcon.blockEnd)
            hierSel.add(clickedIcon.blockEnd)
            leftSel.add(clickedIcon.blockEnd)
            commentSel.add(clickedIcon.blockEnd)
        else:
            hasBlockSel = False
        if not currentSel:
            if siteIcon is not None and (not siteSelected or site != self.cursor.site):
                return "moveCursor"
            return "select"
        elif currentSel == singleSel:
            if hasHierSel:
                return "hier"
            if hasLeftSel:
                return "left"
            if hasCommentSel:
                return "comment"
            if hasBlockSel:
                return "icAndBlock"
            return "moveCursor"
        elif currentSel == hierSel:
            if hasLeftSel:
                return "left"
            if hasCommentSel:
                return "comment"
            if hasBlockSel:
                return "icAndBlock"
            return "moveCursor"
        elif currentSel == leftSel:
            if hasCommentSel:
                return "comment"
            if hasBlockSel:
                return "icAndBlock"
            return "moveCursor"
        elif currentSel == commentSel:
            if hasBlockSel:
                return "icAndBlock"
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
        self.refreshDirty(addUndoBoundary=True)

    def _copyCb(self, evt=None):
        selectedIcons = self.selectedIcons()
        selectedRect = icon.containingRect(selectedIcons)
        if selectedRect is None:
            return
        xOff, yOff = selectedRect[:2]
        clipIcons = clipboardRepr(selectedIcons, (-xOff, -yOff))
        clipTxt = textRepr(selectedIcons)
        self.top.clipboard_clear()
        self.top.clipboard_append(clipIcons, type='ICONS')
        self.top.clipboard_append(clipTxt, type='STRING')

    def _pasteCb(self, evt=None):
        print('start icon creation', time.monotonic())
        if self.cursor.type == "typeover":
            cursors.beep()
            return
        if self.cursor.type == "text":
            # If the user is pasting in to the entry icon use clipboard text, only
            try:
                text = self.top.clipboard_get(type="STRING")
            except:
                return
            self.requestRedraw(self.cursor.icon.hierRect())
            self.cursor.icon.addText(text)
            self.refreshDirty()  # Undo boundary added by addText
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
                pastedIcons = filefmt.parseTextToIcons(text, self)
                # Not usable python code, put in to single icon as string
                if pastedIcons is None:
                    pastedIcons = [nameicons.TextIcon(repr(text), self, (0, 0))]
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
            if self.cursor.siteType != "input" or len(pastedIcons) != 1:
                cursors.beep()
                return
            replaceParent = self.cursor.icon
            replaceSite = self.cursor.site
        else:
            # There's no cursor.  See if there's a selection
            selectedIcons = self.selectedIcons()
            if len(selectedIcons) == 0:
                cursors.beep()
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
            self.requestRedraw(topIcon.hierRect())
            replaceParent.replaceChild(pastedIcons[0], replaceSite)
            self.cursor.setToIconSite(replaceParent, replaceSite)
        else:  # Place at top level
            x, y = pastePos
            for topIcon in pastedIcons:
                for ic in topIcon.traverse():
                    ic.rect = comn.offsetRect(ic.rect, x, y)
            self.addTop(pastedIcons)
            if iconOutputSite is None:
                self.cursor.removeCursor()
            else:
                self.cursor.setToBestCoincidentSite(pastedIcons[0], "output")
        print('start layout', time.monotonic())
        self.requestRedraw(self.layoutDirtyIcons(filterRedundantParens=False))
        print('finish layout', time.monotonic())
        if self.refreshRequests.get() is not None:
            print('start redraw/refresh', time.monotonic())
            self.refresh(self.refreshRequests.get(), redraw=True)
            print('end redraw/refresh', time.monotonic())
            self.refreshRequests.clear()
        self.undo.addBoundary()

    def _deleteCb(self, evt=None):
        selected = self.selectedIcons()
        if selected:
            self.removeIcons(selected)
            self.refreshDirty(addUndoBoundary=True)
        elif self.cursor.type == "icon":
            # Edit or remove the icon to the right of the cursor
            rightIcon, rightSite = cursors.lexicalTraverse(self.cursor.icon,
                self.cursor.site, 'Right')
            if rightIcon is None:
                cursors.beep()
                return
            if not isinstance(rightIcon,
                    (commenticon.CommentIcon, commenticon.VerticalBlankIcon)) and \
                    rightSite != rightIcon.sites.firstCursorSite():
                cursors.beep()
                return
            if evt.state & CTRL_MASK:
                # Delete the icon to the right of the cursor
                self.removeIcons([rightIcon])
            else:
                # Edit the icon to the right of the cursor
                rightIcon.backspace(rightSite, evt)
                if self.cursor.type == 'text':
                    # If the icon backspace response was to edit the icon, it will
                    # leave the cursor at the end rather than the beginning, move it.
                    self.cursor.icon.setCursorPos(0)
            self.refreshDirty(addUndoBoundary=True)
        elif self.cursor.type == 'text':
            self.cursor.icon.forwardDelete(evt)
            self.refreshDirty(addUndoBoundary=False)
        else:
            cursors.beep()

    def _backspaceCb(self, evt=None):
        if self.cursor.type == "text":
            self.cursor.icon.backspaceInText(evt)
            self.refreshDirty(addUndoBoundary=False)
        else:
            selectedIcons = self.selectedIcons()
            if len(selectedIcons) > 0:
                self.removeIcons(selectedIcons)
            elif self.cursor.type == "icon":
                if self.cursor.siteType in ('seqIn', 'seqOut'):
                    cursorIc = self.cursor.icon
                    if self.cursor.siteType == 'seqIn' and cursorIc.prevInSeq():
                        cursorIc = cursorIc.prevInSeq()
                    if isinstance(cursorIc, icon.BlockEnd):
                        ic, site = cursorIc, 'seqIn'
                    elif isinstance(cursorIc, commenticon.CommentIcon):
                        cursorIc.setCursorPos('end')
                        self.cursor.setToText(cursorIc)
                        return
                    elif isinstance(cursorIc, commenticon.VerticalBlankIcon):
                        cursorIc.backspace('seqOut', evt)
                        self.refreshDirty(addUndoBoundary=True)
                        return
                    else:
                        ic, site = icon.rightmostSite(cursorIc)
                    self.cursor.setToIconSite(ic, site)
                else:
                    self._backspaceIcon(evt)
            elif self.cursor.type == "typeover":
                ic = self.cursor.icon
                siteBefore, siteAfter, text, idx = ic.typeoverSites()
                ic.setTypeover(0, siteAfter)
                ic.draw()
                self.cursor.setToIconSite(*icon.rightmostFromSite(ic, siteBefore))
            self.refreshDirty(addUndoBoundary=True)

    def _backspaceIcon(self, evt):
        if self.cursor.type != 'icon' or self.cursor.site in ('output', 'attrOut'):
            return
        ic = self.cursor.icon
        site = self.cursor.site
        # If the icon site being backspaced into is coincident with the output of the
        # icon, the user is probably trying to backspace the parent
        while site == ic.hasCoincidentSite():
            parent = ic.parent()
            if parent is None:
                # Site is coincident with output, but is at the top level.  Call the
                # icon's backspace routine, but I can't imagine why it would do anything.
                break
            site = parent.siteOf(ic)
            ic = parent
        if evt.state & CTRL_MASK:
            # Delete the icon to the left of the cursor
            self.removeIcons([ic])
        else:
            # Edit the icon to the left of the cursor.  For different types of icon, the
            # method for re-editing and action per-site is different, so this is done
            # with an icon-specific method (see individual icon types for specifics).
            ic.backspace(site, evt)

    def backspaceIconToEntry(self, evt, ic, entryText, pendingArgSite=None):
        """Replace the icon (ic)) with the entry icon, pre-loaded with text, entryText,
        and make it active by setting the cursor to it.  This is used by icon backspace
        methods for the simple case of no or one single argument."""
        entryIcon = self.replaceIconWithEntry(ic, entryText, pendingArgSite)
        self.cursor.setToText(entryIcon, drawNew=False)

    def replaceIconWithEntry(self, ic, entryText, pendingArgSite=None):
        """Replace the icon (ic)) with the entry icon, pre-loaded with text, entryText.
        This is used by icon becomeEntryIcon methods for the simple case of no or one
        single argument."""
        self.requestRedraw(ic.topLevelParent().hierRect(), filterRedundantParens=True)
        parent = ic.parent()
        if parent is None:
            entryIcon = entryicon.EntryIcon(initialString=entryText, window=self,
                willOwnBlock=hasattr(ic, 'blockEnd'))
            self.replaceTop(ic, entryIcon)
        else:
            parentSite = parent.siteOf(ic)
            entryIcon = entryicon.EntryIcon(initialString=entryText, window=self)
            parent.replaceChild(entryIcon, parentSite)
        if pendingArgSite is not None:
            child = ic.childAt(pendingArgSite)
            if child is not None:
                ic.replaceChild(None, pendingArgSite)
                entryIcon.appendPendingArgs([child])
        return entryIcon

    def _listPopupCb(self):
        char = self.listPopupVal.get()
        fromIcon = self.popupIcon
        if char == "[" and not isinstance(fromIcon, listicons.ListIcon):
            ic = listicons.ListIcon(fromIcon.window)
        elif char == "(" and not isinstance(fromIcon, listicons.TupleIcon):
            ic = listicons.TupleIcon(fromIcon.window)
        else:
            return
        topIcon = fromIcon.topLevelParent()
        self.requestRedraw(topIcon.hierRect(), filterRedundantParens=True)
        argIcons = fromIcon.argIcons()
        for i, arg in enumerate(argIcons):
            fromIcon.replaceChild(None, fromIcon.siteOf(arg))
            ic.insertChild(arg, "argIcons", i)
        attrIcon = fromIcon.sites.attrIcon.att
        fromIcon.replaceChild(None, 'attrIcon')
        ic.replaceChild(attrIcon, 'attrIcon')
        fromIcon.replaceWith(ic)
        self.cursor.setToIconSite(ic, self.cursor.site)
        self.refreshDirty(addUndoBoundary=True)

    def _arrowCb(self, evt):
        if self.cursor.type is None:
            selected = self.selectedIcons()
            if selected:
                self.cursor.arrowKeyWithSelection(evt, selected)
            return
        if not evt.state & SHIFT_MASK:
            self.unselectAll()
        if evt.state & ALT_MASK and evt.keysym in ("Left", "Right") and \
                self.cursor.type == 'icon':
            self.cursor.processBreakingArrowKey(evt)
        else:
            self.cursor.processArrowKey(evt)
        self.refreshDirty()

    def _cancelCb(self, evt=None):
        if self.cursor.type == "text" and \
                isinstance(self.cursor.icon, entryicon.EntryIcon):
            self.requestRedraw(self.cursor.icon.hierRect())
            self.cursor.icon.remove(forceDelete=True)
        else:
            self.cursor.removeCursor()
        self._cancelDrag()
        self.refreshDirty(addUndoBoundary=True)

    def _enterCb(self, evt):
        """Move Entry icon after the top-level icon where the cursor is found."""
        if self.cursor.type == 'text' and isinstance(self.cursor.icon,
                (stringicon.StringIcon, commenticon.CommentIcon)):
            self.cursor.icon.processEnterKey(evt)
            self.refreshDirty(addUndoBoundary=True)
            return
        if not self._completeEntry(evt):
            return
        if self.cursor.type not in ("icon", "typeover"):
            return  # Not on an icon
        if self.cursor.type == 'icon' and self.cursor.site in ('seqIn', 'seqOut'):
            blankIc = commenticon.VerticalBlankIcon(self)
            icon.insertSeq(blankIc, self.cursor.icon, before=self.cursor.site=='seqIn')
            self.addTopSingle(blankIc)
            self.cursor.setToIconSite(blankIc, 'seqOut')
            self.refreshDirty(addUndoBoundary=True)
            return
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
        self._insertEntryIconAtCursor()
        self.refreshDirty()  # No undo boundary, as this is just an entry icon

    def _execCb(self, evt=None):
        """Execute the top level icon at the entry or icon cursor"""
        # Find the icon at the cursor.  If there's still an entry icon, try to process
        # its content before executing.
        if not self._completeEntry(evt):
            return
        if self.cursor.type in ("icon", "typeover") or self.cursor.type == 'text' and \
                isinstance(self.cursor.icon, stringicon.StringIcon):
            iconToExecute = self.cursor.icon
        else:
            return  # Nothing to execute
        # Find and execute the top level icon associated with the icon at the cursor
        iconToExecute = iconToExecute.topLevelParent()
        if iconToExecute is None:
            print("Could not find top level icon to execute")
            return
        self._execute(iconToExecute)
        self.refreshDirty(addUndoBoundary=True)

    def _execMutablesCb(self, evt=None):
        """Execute and update the content of mutable icons below the top level icon
         currently holding the entry or icon cursor.  No results are displayed."""
        # Find the icon at the cursor.  If there's still an entry icon, try to process
        # its content before executing.
        if not self._completeEntry(evt):
            return
        if self.cursor.type in ("icon", "typeover"):
            iconToExecute = self.cursor.icon
        else:
            return  # Nothing to execute
        # Find the top level icon associated with the icon at the cursor
        topIcon = iconToExecute.topLevelParent()
        if topIcon is None:
            print("Could not find top level icon to execute")
            return
        # Find the mutable icons below it in the hierarchy
        all = set([ic for ic in topIcon.traverse() if ic in self.liveMutableIcons])
        # Remove icons that will already be executed by executing others in the set
        # (noting that executing a mutable will not execute its attribute).
        dups = set()
        for ic in all:
            child = ic
            for parent in ic.parentage(includeSelf=False):
                if parent in all and parent.siteOf(child) != "attrIcon":
                    dups.add(ic)
                    break
                child = parent
        mutablesToExecute = all - dups
        # Execute to update
        for ic in mutablesToExecute:
            self._executeMutable(ic)
        # Update displayed mutable icons that might have been affected by execution
        self.updateMutableIcons([topIcon])
        self.refreshDirty(addUndoBoundary=True)

    def _resyncMutablesCb(self, evt=None):
        """Abandon edits to all mutable icon parents to the current cursor position.
        If there's still an entry icon, try to process its content before executing."""
        if not self._completeEntry(evt):
            return
        if self.cursor.type in ("icon", "typeover"):
            cursorIcon = self.cursor.icon
        else:
            return  # No cursor
        # Find the highest-level mutable icon above the cursor
        parentage = cursorIcon.parentage(includeSelf=True)
        iconToSync = None
        for ic in parentage:
            if ic in self.liveMutableIcons and not \
                    ic.compareData(ic.object, compareContent=True):
                iconToSync = ic
        if iconToSync is None:
            return  # No mutable icons
        self.requestRedraw(iconToSync.hierRect(), filterRedundantParens=True)
        # Update the icon.  See comments in updateMutableIcons from which this is copied.
        cursorPath = self.recordCursorPositionInData(iconToSync)
        newIcon = self.objectToIcons(iconToSync.object, updateMutable=iconToSync)
        self.restoreCursorPositionInData(newIcon, cursorPath)
        # Redraw the areas affected by the updated layouts
        self.refreshDirty(addUndoBoundary=True)

    def _completeEntry(self, evt):
        """Attempt to finish any text entry in progress.  Returns True if successful,
        false if text remains unprocessed in the entry icon."""
        if self.cursor.type == "text" and isinstance(self.cursor.icon,
                entryicon.EntryIcon):
            return self.cursor.icon.focusOut()
        return True

    def _startDrag(self, evt, icons):
        btnDownIcPartPos = icon.addPoints(self.buttonDownIcon.rect[:2],
            self.buttonDownIcon.offsetOfPart(self.buttonDownIcPart))
        self.cancelAllTypeovers(draw=False)
        # Remove the icons from the window image and handle the resulting detachments
        # re-layouts, and redrawing.  removeIcons (with assembleDeleted=True) also does
        # the important job of re-building deleted icons into a set of dragable sequences
        # and hierarchies.
        draggingSequences = self.removeIcons(icons, assembleDeleted=True)
        # removeIcons will remove placeholder icons that no longer hold anything, so if
        # one of those just happens to be the icon that the user dragged, we 1) need make
        # sure that there's still something to drag, and 2) stop using the icon as a
        # reference for positioning the dragged icons
        if isinstance(self.buttonDownIcon, entryicon.EntryIcon) and \
                not self.buttonDownIcon.hasPendingArgs() and \
                len(self.buttonDownIcon.text) == 0:
            if len(draggingSequences) == 0:
                draggingSequences = [[self.buttonDownIcon]]
            else:
                btnDownIcPartPos = None
        # Note that the icons we'll actually drag may not be identical to the function
        # parameter (icons) because removeIcons may have added placeholders or naked
        # tuples to reassemble the icons based on the expressions and sequences to which
        # they were originally attached.
        topDraggingIcons = [ic for seq in draggingSequences for ic in seq]
        self.dragging = [ic for top in topDraggingIcons for ic in
            top.traverse(inclStmtComment=True)]
        # Recalculate layouts for dirty icons remaining in the window and those that will
        # be dragged, and refresh the whole display with icon outlines turned on.
        self.layoutDirtyIcons()
        self.refresh(redraw=True, showOutlines=True)
        self.refreshRequests.clear()
        self.layoutDirtyIcons(topDraggingIcons, filterRedundantParens=False)
        # For top performance, make a separate image containing the moving icons against
        # a transparent background, which can be redrawn with imaging calls, only.
        moveRegion = comn.AccumRects()
        for ic in self.dragging:
            moveRegion.add(ic.rect)
        el, et, er, eb = moveRegion.get()
        self.dragImageOffset = el - self.buttonDownLoc[0], et - self.buttonDownLoc[1]
        self.dragImage = Image.new('RGBA', (er - el, eb - et), color=(0, 0, 0, 0))
        self.lastDragImageRegion = None
        for ic in self.dragging:
            ic.rect = comn.offsetRect(ic.rect, -el, -et)
            ic.draw(self.dragImage, style=icon.STYLE_OUTLINE)
            # Looks better without connectors, but not willing to remove permanently, yet
            # icon.drawSeqSiteConnection(ic, image=self.dragImage)
        for ic in topDraggingIcons:
            icon.drawSeqRule(ic, image=self.dragImage)
        # Fine-tune the positioning of the drag image based on the specific part of the
        # icon that the user dragged (for example, a right paren)
        if btnDownIcPartPos is not None:
            newPartPos = icon.addPoints(icon.addPoints(self.buttonDownIcon.rect[:2],
                self.buttonDownIcon.offsetOfPart(self.buttonDownIcPart)), (el, et))
            if newPartPos != btnDownIcPartPos:
                newPartOffset = icon.subtractPoints(btnDownIcPartPos, newPartPos)
                self.dragImageOffset = icon.addPoints(self.dragImageOffset, newPartOffset)
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
        draggingComment = any((isinstance(i, commenticon.CommentIcon) for i in
            topDraggingIcons))
        for winIcon in self.findIconsInRegion(order='pick'):
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
            if draggingComment and winIcon.parent() is None and not isinstance(winIcon,
                    (commenticon.CommentIcon, commenticon.VerticalBlankIcon,
                    icon.BlockEnd)):
                ic, name = icon.rightmostSite(winIcon)
                x, y = ic.posOfSite(name)
                x += icon.STMT_COMMENT_OFFSET
                if ic.typeOf(name) == 'attrIn':
                    y -= icon.ATTR_SITE_OFFSET
                stationaryInputs.append(((x, y), 0, winIcon, 'seqIn', 'stmtComment',
                    lambda snapIc, _: isinstance(snapIc, commenticon.CommentIcon)))
        self.snapList = []
        for si in stationaryInputs:
            (sx, sy), sh, sIcon, sSiteType, sName, sTest = si
            matingSites = []
            for siteData in draggingOutputs:
                if sSiteType in ('input', 'insertInput', 'seqIn', 'seqOut'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingAttrOuts:
                if sSiteType in ('attrIn', 'insertAttr'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingCprhOuts:
                if sSiteType in ('cprhIn', 'insertCprh'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingSeqInserts:
                if sSiteType in ('seqIn', 'seqOut'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
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
        btnX, btnY = self.imageToContentCoord(evt.x, evt.y)
        x = snappedX = self.dragImageOffset[0] + btnX
        y = snappedY = self.dragImageOffset[1] + btnY
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
        crop = self.contentToImageRect(dragImageRegion)
        dragImage = self.image.crop(crop)
        dragImage.paste(self.dragImage, mask=self.dragImage)
        self.drawImage(dragImage, self.contentToImageCoord(snappedX, snappedY))
        self.lastDragImageRegion = dragImageRegion

    def _endDrag(self):
        # self.dragging icons are not stored hierarchically, but are in draw order
        topDraggedIcons = findTopIcons(self.dragging)
        l, t, r, b = self.lastDragImageRegion
        for ic in self.dragging:
            ic.rect = comn.offsetRect(ic.rect, l, t)
        if self.snapped is not None:
            # The drag ended in a snap.  Attach or replace existing icons at the site
            statIcon, movIcon, siteType, siteName = self.snapped
            if siteName == "stmtComment":
                topDraggedIcons.remove(movIcon)
                if hasattr(statIcon, 'stmtComment'):
                    statIcon.stmtComment.detachStmtComment()
                movIcon.attachStmtComment(statIcon)
            elif siteType == "input":
                topDraggedIcons.remove(movIcon)
                if hasattr(movIcon, 'stmtComment'):
                    # Icon owning stmt comment is no longer top icon.  Move or merge
                    stmtComment = movIcon.stmtComment
                    stmtComment.detachStmtComment()
                    topParent = statIcon.topLevelParent()
                    if hasattr(topParent, 'stmtComment'):
                        topParent.stmtComment.insertText(' ' + stmtComment.string, "end")
                    else:
                        stmtComment.attachStmtComment(topParent)
                if iconsites.isSeriesSiteId(siteName) and \
                        isinstance(movIcon, listicons.TupleIcon) and movIcon.noParens:
                    # Splice in naked tuple
                    statIcon.replaceChild(None, siteName)
                    seriesName, seriesIdx = iconsites.splitSeriesSiteId(siteName)
                    statIcon.insertChildren(movIcon.argIcons(), seriesName, seriesIdx)
                else:
                    statIcon.replaceChild(movIcon, siteName)
            elif siteType == "attrIn":
                topDraggedIcons.remove(movIcon)
                statIcon.replaceChild(movIcon, siteName)
            elif siteType == "insertInput":
                topDraggedIcons.remove(movIcon)
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(siteName)
                if seriesName[-3:] == "Dup":
                    seriesName = seriesName[:-3]
                if isinstance(movIcon, listicons.TupleIcon) and movIcon.noParens:
                    # Splice in naked tuple
                    statIcon.insertChildren(movIcon.argIcons(), seriesName, seriesIdx)
                else:
                    statIcon.insertChild(movIcon, seriesName, seriesIdx)
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
        # Dropping an entry icon on the top level outside of a sequence may allow it to
        # be removed, since placeholders are not needed
        unsequencedEntryIcons = [ic for ic in topDraggedIcons \
            if isinstance(ic, entryicon.EntryIcon) and ic.parent() is None and \
            ic.childAt('seqIn') is None and ic.childAt('seqOut') is None and ic.text == '']
        for ic in unsequencedEntryIcons:
            pendingArgs = ic.listPendingArgs()
            nonEmptyArgs = list(icon.placementListIter(pendingArgs,
                includeEmptySeriesSites=False))
            if len(nonEmptyArgs) == 0:
                topDraggedIcons.remove(ic)
            if len(nonEmptyArgs) == 1:
                topDraggedIcons.remove(ic)
                ic.popPendingArgs("all")
                topDraggedIcons.append(nonEmptyArgs[0][0])
        self.addTop(topDraggedIcons)
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None
        # Layout icons and refresh the entire display.  While refreshing a smaller area
        # is technically possible, after all the dragging and drawing, it's prudent to
        # ensure that the display remains in sync with the image pixmap
        self.requestRedraw("all")
        self.refreshDirty(addUndoBoundary=True)

    def _cancelDrag(self):
        # Not properly cancelling drag, yet, just dropping the icons being dragged
        if self.dragging is None:
            return
        self.refresh(self.lastDragImageRegion, redraw=True)
        self.dragging = None
        self.snapped = None
        self.snapList = None
        self.buttonDownTime = None

    def _startRectSelect(self, evt):
        self.cursor.removeCursor()
        self.inRectSelect = True
        self.lastRectSelect = None
        self.rectSelectInitialState = self.selectedSet.copy()
        self._updateRectSelect(evt)
        self.refreshDirty()

    def _updateRectSelect(self, evt):
        toggle = evt.state & CTRL_MASK
        newRect = makeRect(self.buttonDownLoc, self.imageToContentCoord(evt.x, evt.y))
        if self.lastRectSelect is None:
            combinedRegion = newRect
        else:
            combinedRegion = comn.combineRects(newRect, self.lastRectSelect)
            self._eraseRectSelect()
        redrawRegion = comn.AccumRects()
        for ic in self.findIconsInRegion(combinedRegion):
            if ic.inRectSelect(newRect):
                newSelect = (ic not in self.rectSelectInitialState) if toggle else True
            else:
                newSelect = ic in self.rectSelectInitialState
            if ic.isSelected() != newSelect:
                ic.select(newSelect)
                redrawRegion.add(ic.rect)
        self.refresh(redrawRegion.get(), redraw=True)
        l, t, r, b = self.contentToImageRect(newRect)
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
        self.topIcons[self.stmtSelectSeqStart].applyOffset()
        self.inStmtSelect = True
        self.lastStmtHighlightRects = None
        self._updateStmtSelect(evt)

    def _updateStmtSelect(self, evt):
        anchorY = self.buttonDownLoc[1]
        btnX, btnY = self.imageToContentCoord(evt.x, evt.y)
        drawTop = min(anchorY, btnY)
        drawBottom = max(anchorY, btnY)
        # Trim selection top to start of sequence
        seqTopY = self.stmtSelectSeqStart.posOfSite('seqIn')[1]
        if drawTop < seqTopY:
            drawTop = seqTopY
        redrawRegion = comn.AccumRects()
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
            selected = ic.isSelected()
            if not selected and needsSelect or selected and not needsSelect:
                for selIc in ic.traverse(inclStmtComment=True):
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
        selectLeft = self.stmtSelectSeqStart.posOfSite('seqIn')[0] - 1
        selectRight = selectLeft + 3
        drawRects = [(selectLeft, drawTop, selectRight, drawBottom)]
        for x, y in xChangePoints:
            if drawBottom > y > drawTop and drawRects is not None:
                splitL, splitT, splitR, splitB = drawRects[-1]
                drawRects[-1] = (splitL, splitT, splitR, y)
                drawRects.append((selectLeft, y, selectRight, drawBottom))
        # Refresh selection changes and clear erase areas
        if self.lastStmtHighlightRects is not None:
            for eraseRect in self.lastStmtHighlightRects:
                redrawRegion.add(eraseRect)
        self.refresh(redrawRegion.get(), redraw=True)
        # Draw the selection shading
        for drawRect in drawRects:
            drawImgRect = self.contentToImageRect(drawRect)
            image = self.image.crop(drawImgRect)
            colorImg = Image.new('RGB', (image.width, image.height), color=(0, 0, 255)) # color=icon.SELECT_TINT)
            selImg = Image.blend(image, colorImg, .15)
            self.drawImage(selImg, drawImgRect[:2])
        self.lastStmtHighlightRects = drawRects

    def _endStmtSelect(self):
        redrawRegion = comn.AccumRects()
        self.inStmtSelect = False
        # Erase the shaded zone
        if self.lastStmtHighlightRects is not None:
            for eraseRect in self.lastStmtHighlightRects:
                redrawRegion.add(eraseRect)
        self.refresh(redrawRegion.get(), redraw=True)
        self.lastStmtHighlightRects = None

    def recordCursorPositionInData(self, topIcon):
        if self.cursor.type != "icon":
            return None
        cursorParentage = self.cursor.icon.parentage(includeSelf=True)
        if topIcon not in cursorParentage:
            return None
        # Loop through cursor icon parentage from topIcon down to cursor location,
        # creating a tuple with class and child site for each icon.
        cursorParentage = cursorParentage[:cursorParentage.index(topIcon)]
        cursorLocSteps = []
        parent = topIcon
        for child in reversed(cursorParentage):
            childSite = parent.siteOf(child)
            if childSite is None:
                print("Internal error transfering cursor position")
                return None
            cursorLocSteps.append((parent.__class__, childSite))
            parent = child
        # Add a final entry for the cursor icon and site
        return cursorLocSteps + [(self.cursor.icon.__class__, self.cursor.site)]

    def restoreCursorPositionInData(self, topIcon, recordedPos):
        if recordedPos is None:
            return  # Cursor was not in this expression
        ic = topIcon
        for cls, site in recordedPos[:-1]:
            if not isinstance(ic, cls):
                cursorIc, cursorSite = icon.rightmostSite(ic)
                break
            child = ic.childAt(site)
            if child is None:
                cursorIc, cursorSite = icon.rightmostSite(ic)
                break
            ic = child
        else:
            # If we made it all the way through the loop, ic is equivalent to cursor.icon
            cursorIcCls, cursorSite = recordedPos[-1]
            if isinstance(ic, cursorIcCls):
                cursorIc = ic
            else:
                cursorIc, cursorSite = icon.rightmostSite(ic)
        # Move the cursor
        self.cursor.setToIconSite(cursorIc, cursorSite)

    def _execute(self, iconToExecute):
        """Execute the requested top-level icon or sequence."""
        # Begin by creating Python Abstract Syntax Tree (AST) for the icon or icons.
        # Icon AST creation methods will throw exception IconExecException which provides
        # the icon where things went bad so it can be shown in self._handleExecErr
        # Icons can be executed either by "eval" or "exec".  Choose which based upon
        # whether we need the result of the evaluation.
        self.globals['__windowExecContext__'] = {}
        if iconToExecute.hasSite('output') and iconToExecute.prevInSeq() is None and \
         iconToExecute.nextInSeq() is None:
            # Create ast for eval
            execType = 'eval'
            seqIcons = [iconToExecute]
            try:
                astToExecute = ast.Expression(iconToExecute.createAst())
            except icon.IconExecException as excep:
                self._handleExecErr(excep)
                return False
        else:
            # Create ast for exec (may be a sequence)
            execType = 'exec'
            iconToExecute = icon.findSeqStart(iconToExecute)
            seqIcons = icon.traverseSeq(iconToExecute, skipInnerBlocks=True)
            try:
                body = [icon.createStmtAst(ic) for ic in seqIcons]
            except icon.IconExecException as excep:
                self._handleExecErr(excep)
                return False
            astToExecute = ast.Module(body, type_ignores=[])
        #print(ast.dump(astToExecute, include_attributes=True))
        # Compile the AST
        code = compile(astToExecute, self.winName, execType)
        # Execute the compiled AST, providing variable __windowExecContext__ for
        # mutable icons to use to pass their live data into the compiled code.
        try:
            if execType == 'eval':
                result = eval(code, self.globals, self.locals)
            else:
                result = exec(code, self.globals, self.locals)
        except Exception as excep:
            self._handleExecErr(excep, iconToExecute)
            return False
        self.globals['__windowExecContext__'] = {}
        # Update any displayed mutable icons that might have been affected by execution
        self.updateMutableIcons(seqIcons)
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
        resultIcon = self.objectToIcons(result)
        # Place the results to the left of the icon being executed
        if outSitePos is None:
            outSiteX, top, right, bottom = iconToExecute.rect
            outSiteY = (bottom + top) // 2
        else:
            outSiteX, outSiteY = outSitePos
        resultIcon.layout()
        resultIcon.markLayoutDirty()  # Initial layout call was just to measure size
        resultRect = resultIcon.hierRect()
        resultOutSitePos = resultIcon.posOfSite("output")
        if resultOutSitePos is None:
            resultOutSiteX, top, right, bottom = resultIcon.rect
            resultOutSiteY = (bottom + top) // 2
        else:
            resultOutSiteX, resultOutSiteY = resultOutSitePos
        resultX = outSiteX - RESULT_X_OFFSET - comn.rectWidth(resultRect)
        resultY = outSiteY - resultOutSiteY - resultIcon.rect[1]
        resultIcon.rect = comn.offsetRect(resultIcon.rect, resultX, resultY)
        self.addTopSingle(resultIcon, newSeq=True)
        self.requestRedraw(resultIcon.hierRect())
        # For expressions that yield "None", show it, then automatically erase
        if result is None:
            self.refreshDirty(addUndoBoundary=True)
            time.sleep(0.4)
            self.removeIcons([resultIcon])
        else:
            # Remember where the last result was drawn, so it can be erased if it is still
            # there the next time the same icon is executed
            self.execResultPositions[outSitePos] = resultIcon, resultIcon.rect[:2]
        return True

    def _executeMutable(self, ic):
        """Execute a mutable icon and all of the icons beneath it.  Attribute icons are
        not executed, and no layout or drawing are done.  (Attributes are children from
        an icon perspective, but parents from an AST perspective)"""
        self.globals['__windowExecContext__'] = {}
        try:
            astToExecute = ast.Expression(ic.createAst(skipAttr=True))
        except icon.IconExecException as excep:
            self._handleExecErr(excep)
            return False
        code = compile(astToExecute, self.winName, 'eval')
        try:
            eval(code, self.globals, self.locals)
        except Exception as excep:
            self._handleExecErr(excep, ic)
            return False
        self.globals['__windowExecContext__'] = {}

    def objectToIcons(self, obj, updateMutable=None):
        """Create icons representing a data object.  Returns the top-level created icon.
        If updateMutable is specified, fill in the children of the given icon, rather
        than creating a new one (this icon must be a mutable icon of the type appropriate
        for representing the data in obj)."""
        ic = updateMutable
        objClass = obj.__class__
        if objClass is list:
            if ic is None:
                ic = listicons.ListIcon(window=self, obj=obj)
                self.watchMutableIcon(ic)
            else:
                for site in tuple(ic.sites.argIcons):
                    ic.replaceChild(None, site.name)
            ic.insertChildren([self.objectToIcons(elem) for elem in obj], 'argIcons', 0)
        elif objClass is tuple:
            ic = listicons.TupleIcon(window=self, obj=obj)
            ic.insertChildren([self.objectToIcons(elem) for elem in obj], 'argIcons', 0)
        elif objClass is dict:
            if ic is None:
                ic = listicons.DictIcon(window=self, obj=obj)
                self.watchMutableIcon(ic)
            else:
                for site in tuple(ic.sites.argIcons):
                    ic.replaceChild(None, site.name)
            elems = []
            for key, value in obj.items():
                dictElem = listicons.DictElemIcon(window=self)
                dictElem.replaceChild(self.objectToIcons(key), 'leftArg')
                dictElem.replaceChild(self.objectToIcons(value), 'rightArg')
                elems.append(dictElem)
            ic.insertChildren(elems, 'argIcons', 0)
        elif objClass is set:
            if ic is None:
                ic = listicons.DictIcon(window=self, obj=obj)
                self.watchMutableIcon(ic)
            else:
                for site in tuple(ic.sites.argIcons):
                    ic.replaceChild(None, site.name)
            elems = [self.objectToIcons(value) for value in obj]
            ic.insertChildren(elems, 'argIcons', 0)
        elif isinstance(obj, (int, float)):
            ic = nameicons.NumericIcon(obj, window=self)
        elif isinstance(obj, complex):
            # Complex should probably be a numeric icon subtype or a specialty icon of
            # its own, or maybe just left as an object type.
            ic = filefmt.parseTextToIcons(f'complex({obj.real}, {obj.imag})', self)[0]
        else:
            ic = filefmt.parseTextToIcons(repr(obj), self)[0]
        return ic

    def _handleExecErr(self, excep, executedIcon=None):
        """Process exceptions that need to point to an icon."""
        # Does not yet handle tracebacks.  Eventually needs to allow examination of the
        # entire stack (icon and text modules).
        if isinstance(excep, icon.IconExecException):
            excepIcon = excep.icon
        else:
            tb = excep.__traceback__.tb_next  # One level down in traceback stack
            if tb is None:
                excepIcon = executedIcon
            else:
                excepIcon = self.iconIds[tb.tb_lineno]
        iconRect = excepIcon.hierRect()
        for ic in excepIcon.traverse():
            style = icon.STYLE_EXEC_ERR if ic==excepIcon else 0
            ic.draw(clip=iconRect, style=style)
        self.refresh(iconRect, redraw=False)
        message = excep.__class__.__name__ + ': ' + str(excep)
        tkinter.messagebox.showerror("Error Executing", message=message)
        for ic in excepIcon.traverse():
            ic.draw(clip=iconRect)
        self.refresh(iconRect, redraw=False)

    def _showSyntaxErr(self, _evt=None):
        errHighlight = self.popupIcon.errHighlight
        if errHighlight is not None:
            tkinter.messagebox.showerror("Syntax Error", message=errHighlight.text, )

    def _select(self, ic, op='select'):
        """Change the selection.  Options are 'select': selects single icon, 'toggle':
        changes the state of a single icon, 'add': adds a single icon to the selection,
        'hier': changes the selection to the icon and it's children, 'left': changes
        the selection to the icon and associated expression for which it is the
        leftmost component, 'comment' changes the selection to the top icon in the
        statement and its associated statement comment, 'icAndBlock' changes the
        selection to the entire code block containing ic"""
        if op in ('select', 'hier', 'left', 'block'):
            self.unselectAll()
        #... I'm leaving the commented-out code below as a reminder that I removed it
        #    because it's clearly wrong for comments and strings, but worried that I've
        #    forgotten about cases where the entry icon needs to preserve a selection.
        # if ic is None or self.cursor.type == "text" and ic is self.cursor.icon:
        #    return
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
        elif op == 'comment':
            changedIcons = list(ic.topLevelParent().traverse(inclStmtComment=True))
        elif op == 'icAndBlock':
            changedIcons = list(ic.traverseBlock(hier=True, inclStmtComment=True))
        elif op == 'left':
            ic = findLeftOuterIcon(self.assocGrouping(ic), self.buttonDownLoc)
            changedIcons = list(ic.traverse())
        else:
            changedIcons = [ic]
        for ic in changedIcons:
            self.requestRedraw(ic.rect)
            if op == 'toggle':
                ic.select(not ic.isSelected())
            else:
                ic.select()
        self.cursor.removeCursor()
        self.refreshDirty()

    def unselectAll(self):
        refreshRegion = comn.AccumRects()
        selectedIcons = self.selectedIcons()
        if len(selectedIcons) == 0:
            return
        for ic in selectedIcons:
            refreshRegion.add(ic.rect)
        self.clearSelection()
        if refreshRegion.get() is not None:
            self.refresh(refreshRegion.get(), redraw=True)

    def redraw(self, region=None, clear=True, showOutlines=False):
        """Cause all icons to redraw to the pseudo-framebuffer (call refresh to transfer
        from there to the display).  Setting clear to False suppresses clearing the
        region to the background color before redrawing.  Note that the "clear" keyword
        is reserved for the small number of cases where the background is already known
        to be cleared (in earlier versions, this flag could be used more liberally, but
        the drawing model now allows for transparency via alpha blending, so clearing is
        required to stop transparent regions from building-up with repeated drawing)."""
        left, top = self.scrollOrigin
        width, height = self.image.size
        right, bottom = left + width, top + height
        if region is None:
            region = left, top, right, bottom
        else:
            # Clip the region to the visible area of the window
            l, t, r, b = region
            region = max(left, l), max(top, t), min(right, r), min(bottom, b)
        if clear:
            self.clearBgRect(region)
        # Traverse all the visible icons in the window.  Note that correct drawing depends
        # on ordering so overlaps happen properly, so this is subtly dependent on the
        # order returned from findIconsInRegion.  Sequence lines must be drawn on top of
        # the icons they connect but below any icons that might be placed on top of them.
        drawStyle = icon.STYLE_OUTLINE if showOutlines else 0
        for ic in self.findIconsInRegion(region, inclSeqRules=True):
            ic.draw(clip=region, style=drawStyle)
            # Looks better without connectors, but not willing to remove permanently, yet:
            # if region is None or icon.seqConnectorTouches(topIcon, region):
            #     icon.drawSeqSiteConnection(topIcon, clip=region)
            if icon.seqRuleTouches(ic, region):
                icon.drawSeqRule(ic, clip=region)

    def _dumpCb(self, evt=None):
        for seqStartPage in self.sequences:
            for ic in icon.traverseSeq(seqStartPage.startIcon):
                icon.dumpHier(ic)
        print(f"Cursor type {self.cursor.type} ", end='')
        if self.cursor.type == "window":
            print(f"{self.cursor.pos}")
        elif self.cursor.type == "typeover":
            print(f"Icon: {self.cursor.icon.dumpName()}")
        elif self.cursor.type == "icon":
            print(f"Icon: {self.cursor.icon.dumpName()}, Site: {self.cursor.site}")
        elif self.cursor.type == "text":
            if isinstance(self.cursor.icon, entryicon.EntryIcon):
                print(f"Entry Icon {repr(self.cursor.icon.text)},"
                      f"{self.cursor.icon.cursorPos}")
            elif isinstance(self.cursor.icon, stringicon.StringIcon):
                ic = self.cursor.icon
                print(f"String {ic.dumpName()}, {ic.cursorPos}")

    def _debugLayoutCb(self, evt):
        topIcons = findTopIcons(self.selectedIcons())
        for ic in topIcons:
            if hasattr(ic, 'debugLayoutFilterIdx'):
                ic.debugLayoutFilterIdx += 1
            else:
                ic.debugLayoutFilterIdx = 0
            ic.markLayoutDirty()
        self.refreshDirty(addUndoBoundary=True)

    def _undebugLayoutCb(self, evt):
        for ic in self.selectedIcons():
            if hasattr(ic, 'debugLayoutFilterIdx'):
                delattr(ic, 'debugLayoutFilterIdx')
                ic.markLayoutDirty()
        self.refreshDirty(addUndoBoundary=True)

    def refresh(self, region=None, redraw=True, clear=True, showOutlines=False):
        """Redraw any rectangle (region) of the window.  If redraw is set to False, the
         window will be refreshed from the pseudo-framebuffer (self.image).  If redraw
         is True, the framebuffer is first refreshed from the underlying icon structures.
         If no region is specified (region==None), redraw the whole window.  Setting
         clear to False will not clear the background area before redrawing.  Note that
         this does *not* process pending refresh requests in self.refreshRequests, which
         will still be pending after the call.  Also be careful about passing regions
         from comn.AccumRects, which use None to indicate an empty region, whereas this
         call, conversely, uses None to indicate that the *entire window* be redrawn."""
        if redraw:
            self.redraw(region, clear, showOutlines)
        if region is None:
            self.drawImage(self.image, (0, 0))
        else:
            region = self.contentToImageRect(region)
            self.drawImage(self.image, (region[0], region[1]), region)

    def requestRedraw(self, redrawArea, filterRedundantParens=False):
        """Add a rectangle (redrawArea) to the requested area to be redrawn on the next
        call to refreshDirty.  Setting filterRedundantParens to True will additionally
        request refreshDirty to apply redundant parenthesis removal to to icons whose
        layouts are marked as dirty."""
        if redrawArea == "all":
            left, top = self.imageToContentCoord(0, 0)
            width, height = self.image.size
            redrawArea = (left, top, left + width, top + height)
        self.refreshRequests.add(redrawArea)
        if filterRedundantParens:
            self.redundantParenFilterRequested = True

    def refreshDirty(self, addUndoBoundary=False, minimizePendingArgs=True,
            redrawCursor=True):
        """Refresh any icons whose layout is marked as dirty (via the markLayoutDirty
        method of the icon), and redraw and refresh any window areas marked as needing
        redraw (via window method requestRedraw).  If nothing is marked as dirty, no
        redrawing will be done.  The function serves a more general purpose of finishing
        any user operation that may have altered the icon structure (including simple
        cursor movement because focus changes can also alter the icon structure).  As
        such, it also includes clean-up for entry icon pending args (minimizePendingArgs),
        cursor redraw and hold (redrawCursor), and optionally adding an undo boundary
        (addUndoBoundary)."""
        if minimizePendingArgs and self.cursor.type == "text" and \
                isinstance(self.cursor.icon, entryicon.EntryIcon):
            self.cursor.icon.minimizePendingArgs()
        self.refreshRequests.add(self.layoutDirtyIcons(
            filterRedundantParens=self.redundantParenFilterRequested))
        if self.refreshRequests.get() is not None:
            self.refresh(self.refreshRequests.get(), redraw=True)
        if addUndoBoundary:
            self.undo.addBoundary()
        self.refreshRequests.clear()
        self.redundantParenFilterRequested = False
        if redrawCursor:
            self.cursor.erase()
            self.cursor.drawAndHold()

    def drawImage(self, image, location, subImage=None):
        """Draw an arbitrary image anywhere in the window, ignoring the window image.
        Note that location and subImage are in image (not window content) coordinates."""
        if subImage:
            # image.crop will create an image the size of the crop area, even if the
            # original is smaller. Pre-crop the crop-rectangle to the window size.
            winWidth, winHeight = self.image.size
            x1, y1, x2, y2 = subImage
            subImage = max(0, x1), max(0, y1), min(winWidth, x2), min(winHeight, y2)
            location = max(0, location[0]), max(0, location[1])
            image = image.crop(subImage)
        if image.width == 0 or image.height == 0:
            return
        dib = ImageWin.Dib('RGB', (image.width, image.height))
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
        dib.draw(self.dc, (x, y, x + image.width, y + image.height))

    def findIconsInRegion(self, rect=None, inclSeqRules=False, order='draw'):
        """Find the icons that touch a (content coordinate) rectangle of the window.  If
        rect is not specified, assume the visible region of the window.  This function
        uses an efficient searching technique, so it is also used to cull candidate icons
        by location, to avoid scanning all icons in the window when location is known. If
        inclSeqRule is True, includes icons at the start of sequence rules in rect."""
        if rect is None:
            left, top = self.scrollOrigin
            width, height = self.image.size
            right = left + width
            bottom = top + height
            rect = left, top, right, bottom
        else:
            left, top, right, bottom = rect
        iconsInRegion = []
        seqRuleSeed = None
        sequences = reversed(self.sequences) if order == "pick" else self.sequences
        for seqStartPage in sequences:
            for page in seqStartPage.traversePages():
                if page.bottomY >= rect[1] and page.topY <= bottom:
                    page.applyOffset()
                    for topIc in page.traverseSeq():
                        for ic in topIc.traverse(order=order, inclStmtComment=True):
                            if comn.rectsTouch(rect, ic.rect):
                                iconsInRegion.append(ic)
                        if inclSeqRules and seqRuleSeed is None and topIc.rect[1] >= top:
                            seqRuleSeed = topIc
        if inclSeqRules and seqRuleSeed is not None:
            alreadyCollected = set(iconsInRegion)
            # Follow code blocks up to the top of the sequence to find the start for each
            # sequence rule left of seqRuleSeed
            blockStart = seqRuleSeed
            while True:
                blockStart = icon.findSeqStart(blockStart, toStartOfBlock=True).prevInSeq()
                if blockStart is None:
                    break
                if icon.seqRuleTouches(blockStart, rect):
                    if blockStart not in alreadyCollected:
                        iconsInRegion.append(blockStart)
                    page = self.topIcons[blockStart]
                    page.applyOffset()
            # Follow code within the y range down from seqRule seed to the bottom of rect
            # to find any icons whose sequence rules need to be drawn
            for ic in icon.traverseSeq(seqRuleSeed):
                if icon.seqRuleTouches(ic, rect):
                    if ic not in alreadyCollected:
                        iconsInRegion.append(ic)
                    page = self.topIcons[ic]
                    page.applyOffset()
                if ic.rect[1] > bottom:
                    break
        return iconsInRegion

    def findIconAt(self, x, y):
        for seqStartPage in reversed(self.sequences):
            for page in seqStartPage.traversePages():
                if page.bottomY >= y >= page.topY:
                    page.applyOffset()
                    for ic in page.traverseSeq(order="pick", hier=True,
                            inclStmtComments=True):
                        if ic.touchesPosition(x, y):
                            return ic
        return None

    def _leftOfSeq(self, x, y):
        """Return top level icon near x,y if x,y is in the appropriate zone to start a
        statement-selection"""
        for seqStartPage in self.sequences:
            for page in seqStartPage.traversePages():
                if page.bottomY >= y >= page.topY:
                    page.applyOffset()
                    for ic in page.traverseSeq():
                        if ic.hasSite('seqIn'):
                            seqInX, seqInY = ic.posOfSite('seqIn')
                            seqOutX, seqOutY = ic.posOfSite('seqOut')
                            if y < seqInY:
                                continue
                            if seqInY <= y <= seqOutY and \
                             seqInX - SEQ_SELECT_WIDTH <= x <= seqInX:
                                return ic  # Point is adjacent to icon body
                            nextIc = ic.nextInSeq()
                            if nextIc is None:
                                continue
                            nextSeqInX, nextSeqInY = nextIc.posOfSite('seqIn')
                            if seqOutY <= y < nextSeqInY and \
                             seqOutX-SEQ_SELECT_WIDTH <= x <= seqOutX:
                                return ic  # Point is adjacent to connector to next icon
        return None

    def removeIcons(self, icons, assembleDeleted=False):
        """Remove icons from window icon list, request redraw of affected areas of the
        display (does not perform redraw, call refreshDirty() to draw marked changes)."""
        if len(icons) == 0:
            return []
        # deletedSet more efficiently determines if an icon is on the deleted list
        deletedSet = set(icons)
        # Cursors and selections can coexist, and it is possible for the cursor to be on
        # an icon that is being deleted.  If so, move it to an icon that will remain.
        if self.cursor.type in ("icon", "text") and self.cursor.icon in deletedSet \
                and not assembleDeleted:
            cursorPos = self.cursor.icon.pos()
            cursorIc, cursorSite = None, None
            for ic in self.cursor.icon.parentage(includeSelf=False):
                if ic not in deletedSet:
                    cursorIc, cursorSite = ic, ic.siteOf(self.cursor.icon, recursive=True)
                    break
                cursorPos = ic.pos()
            else:
                for ic in icon.traverseSeq(self.cursor.icon):
                    if ic not in deletedSet:
                        cursorIc, cursorSite = ic, 'seqIn'
                        break
                else:
                    for ic in icon.traverseSeq(self.cursor.icon, reverse=True):
                        if ic not in deletedSet:
                            cursorIc, cursorSite = ic, 'seqOut'
                            break
            if cursorIc is None:
                self.cursor.setToWindowPos(cursorPos, eraseOld=False, drawNew=False,
                        placeEntryText=False)
            else:
                self.cursor.setToIconSite(cursorIc, cursorSite, eraseOld=False,
                    drawNew=False, placeEntryText=False)
        # Find the top icons of the statement hierarchy for the icons being deleted
        topIcons = set()
        for ic in icons:
            if isStmtComment(ic):
                topIcons.add(ic.attachedToStmt)
            else:
                topIcons.add(ic.topLevelParent())
        # Find region needing erase, including following sequence connectors
        self.requestRedraw(None, filterRedundantParens=True)
        for ic in topIcons:
            self.requestRedraw(ic.hierRect())
            nextIc = ic.nextInSeq()
            if nextIc is not None:
                tx, ty = ic.posOfSite('seqOut')
                bx, by = nextIc.posOfSite('seqIn')
                self.requestRedraw((tx-1, ty-1, tx+1, by+1))
            prevIc = ic.prevInSeq()
            if prevIc is not None:
                tx, ty = prevIc.posOfSite('seqOut')
                bx, by = ic.posOfSite('seqIn')
                self.requestRedraw((tx-1, ty-1, tx+1, by+1))
        # If we're being asked to assemble the deleted icons, need to do additional work
        # before deletion to associate the top icons with the sequence from which they
        # come and their order in the sequence.  We randomly assign an integer identifier
        # to each sequence, and build a dictionary (iconToSeqId) to map the top icons
        # involved in the deletion to its sequence.  Rather than store the original
        # ordering of the sequence, we use the fact that topIcons controls the order of
        # deletion, and simply replace the set (topIcons) that was used to find the top
        # affected icons, with an ordered list, and collect them as they are processed.
        if assembleDeleted:
            sequences = orderTopIcons(topIcons)
            iconToSeqId = {}
            orderedTopIcons = []
            deletedSeqList = [[] for _ in range(len(sequences))]
            for seqId, seq in enumerate(sequences):
                for order, ic in enumerate(seq):
                    iconToSeqId[ic] = seqId
                    orderedTopIcons.append(ic)
            topIcons = orderedTopIcons
        else:
            deletedSeqList = None
        # Before doing the deletion, waste some cycles to scan for else icons among the
        # deleted icons, if one is found, mark the owner of the containing block, dirty
        # so its highlightErrors method will re-scan and potentially clear else-related
        # errors
        for ic in topIcons:
            if isinstance(ic, blockicons.ElseIcon):
                blockOwner = icon.findBlockOwner(ic)
                if blockOwner is not None:
                    blockOwner.markLayoutDirty()
        # Recursively call splitDeletedIcons to build up a replacement tree for
        # each of those top-level icons.  The deletion code will return either 1) None
        # indicating no change (leave current icon), 2) Empty list (fully delete),
        # 3) a list, in placement list format (call appropriate translation code to
        # convert to either a series or a single icon).  Do any replacement immediately,
        # but leave the full statement deletion to the next step (which handles runs of
        # connected statement-level icons without unlinking and re-linking them).
        topDeletedIcons = set()
        ignoreRemovedBlockEnds = set()
        for topIcon in topIcons:
            needReorder = []
            stmtComment = topIcon.stmtComment if hasattr(topIcon, 'stmtComment') else None
            remainingIcons, assembledDeletions = splitDeletedIcons(topIcon, deletedSet,
                assembleDeleted, needReorder)
            if remainingIcons is None:
                newTopIcon = topIcon
            else:
                forSequence = topIcon.childAt('seqIn') or topIcon.childAt('seqOut')
                newTopIcon = placeListToTopLevelIcon(remainingIcons, forSequence)
            if isinstance(newTopIcon, listicons.TupleIcon) and newTopIcon.noParens and \
                    len(newTopIcon.sites.argIcons) == 1:
                # Deletion left an empty or single-element naked tuple: remove it (note
                # that this step is skipped when assembling deleted icons later on,
                # because users can't select or drag a naked tuple)
                argIcon = newTopIcon.childAt('argIcons_0')
                if argIcon is None:
                    newTopIcon = None
                else:
                    newTopIcon.replaceChild(None, 'argIcons_0')
                    newTopIcon = argIcon
            newTopIcon = reorderMarkedExprs(newTopIcon, needReorder)
            if assembleDeleted:
                if assembledDeletions is None:
                    addToDelSeq = topIcon
                else:
                    delTree = placeListToTopLevelIcon(assembledDeletions, False)
                    addToDelSeq = delTree if delTree is not None else None
                addToDelSeq = reorderMarkedExprs(addToDelSeq, needReorder)
                if addToDelSeq is not None:
                    deletedSeqList[iconToSeqId[topIcon]].append(addToDelSeq)
                if stmtComment in deletedSet and addToDelSeq is not topIcon:
                    stmtComment.detachStmtComment()
                    if addToDelSeq is None:
                        deletedSeqList[iconToSeqId[topIcon]].append(stmtComment)
                    else:
                        stmtComment.attachStmtComment(addToDelSeq)
            if newTopIcon is None:
                if stmtComment is not None and stmtComment not in deletedSet:
                    stmtComment = topIcon.stmtComment
                    stmtComment.detachStmtComment()
                    if hasattr(topIcon, 'blockEnd'):
                        ignoreRemovedBlockEnds.add(topIcon.blockEnd)
                    self.replaceTop(topIcon, stmtComment)
                else:
                    topDeletedIcons.add(topIcon)
            elif newTopIcon is not topIcon:
                if stmtComment is not None and stmtComment not in deletedSet:
                    stmtComment = topIcon.stmtComment
                    stmtComment.detachStmtComment()
                    stmtComment.attachStmtComment(newTopIcon)
                if hasattr(topIcon, 'blockEnd'):
                    ignoreRemovedBlockEnds.add(topIcon.blockEnd)
                self.replaceTop(topIcon, newTopIcon)
        # Unlink runs of deleted statement-level icons. Note that order is important,
        # here.  .removeTop() must be called before disconnecting the icon sequences, and
        # .addTop() must be called after connecting them.  Therefore, the first step is
        # to remove deleted top-level icons from the .topIcon and .sequences lists.
        topDeletedIcons -= ignoreRemovedBlockEnds
        self.removeTop(topDeletedIcons)
        detachList = set()
        reconnectList = []
        affectedTopIcons = set()
        for topIcon in topDeletedIcons:
            affectedTopIcons.add(topIcon)
            prevIcon = topIcon.prevInSeq()
            if prevIcon is not None:
                affectedTopIcons.add(prevIcon)
            nextIcon = topIcon.nextInSeq()
            if nextIcon is not None:
                affectedTopIcons.add(nextIcon)
        for topIcon in affectedTopIcons:
            nextIcon = topIcon.nextInSeq()
            if nextIcon is not None:
                if topIcon in topDeletedIcons and nextIcon not in topDeletedIcons:
                    detachList.add((topIcon, nextIcon))
                    topIcon.markLayoutDirty()
                if topIcon not in topDeletedIcons and nextIcon in topDeletedIcons:
                    detachList.add((topIcon, nextIcon))
                    topIcon.markLayoutDirty()
                    while True:
                        nextIcon = nextIcon.nextInSeq()
                        if nextIcon is None:
                            break
                        if nextIcon not in topDeletedIcons:
                            reconnectList.append((topIcon, nextIcon))
                            break
        for ic, child in detachList:
            ic.replaceChild(None, ic.siteOf(child))
        for outIcon, inIcon in reconnectList:
            outIcon.replaceChild(inIcon, 'seqOut')
        if assembleDeleted:
            # Link the deleted sequences from deletedSeqList (which holds deleted top
            # level icons already ordered and categorized by sequence), leaving alone
            # those that are already correctly linked.  This code also checks that the
            # deleted icons that need to be linked to a sequence, can be, and if not,
            # adds a placeholder icon to hold them. This is necessary, because we created
            # the entries for the list with placeListToTopLevelIcon with forSequence set
            # to False, as we did not yet know if the deleted list would form a sequence
            # (and, typically, users would not intentionally create a sequence of, for
            # example, attributes), but it can still happen.
            deletedSeqs = [s for s in deletedSeqList if len(s) > 0]
            for seqList in deletedSeqs:
                if len(seqList) >= 2:
                    prevIc = None
                    for i, ic in enumerate(seqList):
                        if not ic.hasSite('seqIn'):
                            entryIc = entryicon.EntryIcon(window=self)
                            entryIc.appendPendingArgs([ic])
                            ic = entryIc
                            seqList[i] = entryIc
                        if prevIc is not None and ic is not prevIc.childAt('seqOut'):
                            prevIc.replaceChild(ic, 'seqOut')
                        prevIc = ic
            # If any rearrangement happened among the deleted icons, mark the top icon in
            # the statement as dirty, since the layout code requires this to find dirty
            # icons, and the normal mechanism for marking it does not work for these.
            for seqList in deletedSeqs:
                for topIc in seqList:
                    for ic in topIc.traverse(inclStmtComment=True):
                        if ic.layoutDirty:
                            topIc.layoutDirty = True
            return deletedSeqs
        return None

    def saveFile(self, filename):
        _base, ext = os.path.splitext(filename)
        exportPython = ext != ".pyg"
        tabSize = 4
        print('Started save')
        with open(filename, "w") as f:
            for seqStartPage in sorted(self.sequences, key=self.seqSortKeyFn):
                startIcon = seqStartPage.startIcon
                left, top = startIcon.hierRect()[:2]
                if not exportPython:
                    f.write("$@%+d%+d$\n" % (left, top))
                branchDepth = 0
                for ic in icon.traverseSeq(startIcon):
                    if isinstance(ic, icon.BlockEnd):
                        branchDepth -= 1
                    else:
                        saveText = ic.createSaveText(export=exportPython)
                        if saveText.requiresTempDedent:
                            indent = tabSize * max(0, branchDepth - 1)
                        else:
                            indent = tabSize * max(0, branchDepth)
                        if hasattr(ic, 'blockEnd'):
                            continueIndent = 8
                            branchDepth += 1
                        else:
                            continueIndent = tabSize
                        if hasattr(ic, 'stmtComment') and ic.stmtComment is not None:
                            saveText.addComment(ic.stmtComment.createSaveText(
                                export=exportPython), isStmtComment=True)
                        stmtText = saveText.wrapText(indent, indent + continueIndent,
                            margin=100, export=exportPython)
                        f.write(stmtText)
                        f.write('\n')
                        if (hasattr(ic, 'blockEnd') or saveText.requiresTempDedent) and \
                                blockicons.checkEmptyBlockNeedsPass(ic):
                            # Python requires a 'pass' statement for empty blocks
                            f.write((tabSize * max(0, branchDepth)) * ' ')
                            if not exportPython:
                                f.write('$:x$')
                            f.write('pass\n')
        print('Finished save')

    @staticmethod
    def seqSortKeyFn(seqStartPage):
        """To make the save file format stable for use by version control systems and
        diff/review tools, we need to order the sequence list consistently.  To do that,
        we sort it by y, then by x coordinate. of the start of the sequence."""
        startIcon = seqStartPage.startIcon
        left, top = startIcon.hierRect()[:2]
        return top, left

    def clearBgRect(self, rect=None):
        """Clear but don't refresh a rectangle of the window.  rect is in content
        coordinates (not the coordinates of the window image)"""
        # Fill rectangle seems to go one beyond
        if rect is None:
            l, t, r, b = 0, 0, self.image.width, self.image.height
        else:
            l, t, r, b = self.contentToImageRect(rect)
        self.draw.rectangle((l, t, r-1, b-1), fill=WINDOW_BG_COLOR)

    def assocGrouping(self, ic):
        """Find the root binary operation associated with a group of equal precedence
        operations"""
        child = ic
        if ic.__class__ not in (opicons.BinOpIcon, opicons.IfExpIcon):
            return ic
        for parent in ic.parentage():
            if parent.__class__ not in (opicons.BinOpIcon, opicons.IfExpIcon) \
                    or parent.precedence != ic.precedence:
                return child
            child = parent
        return child

    def removeTop(self, icons):
        """Remove top-level icon or icons from the .topIcons and page list.  Does NOT
        remove from sequence (use removeIcons for that).  Also, does not re-layout or
        re-draw.  Note that if removing a sequence, this should be 1) called with all of
        the icons being removed (as opposed to individual icons), and 2) called before
        the sequence links are reordered.  These are required so that the inverse of
        the operation (undo) can assign pages consistent with the sequence."""
        if hasattr(icons, '__iter__'):
            # Control the order in which icons are removed, so that when undone, they
            # will go back in an order that page membership can be reestablished
            # reverse of the order used in addTop
            for seqIc, newSeq in reversed(self._orderIconsForAdd(icons)):
                self.removeTopSingle(seqIc, newSeq)
        else:
            lastOfSeq = icons.nextInSeq() is None and icons.prevInSeq() is None
            self.removeTopSingle(icons, lastOfSeq)

    def removeTopSingle(self, ic, lastOfSeq):
        """Remove a single top-level icon from the window .topIcon and .sequences
        structures.  If this icon is part of a sequence, use removeTop, instead, because
        ordering of removal is necessary to rebuild page structures when the operation
        is undone."""
        self.undo.registerRemoveFromTopLevel(ic, ic.rect[:2] if lastOfSeq else None)
        page = self.topIcons.get(ic)
        page.layoutDirty = True
        page.iconCount -= 1
        if page.iconCount == 0:
            self.removePage(page)
        else:
            if page.startIcon is ic:
                # The removed icon was the reference icon for the page.  Because we
                # require the sequence to be in pre-removal state, we can find a
                # replacement, but it may require iteration as we don't require icons
                # to be removed top-to-bottom, so some candidates may already be gone.
                while True:
                    page.startIcon = page.startIcon.nextInSeq()
                    pageOfStartIcon = self.topIcons.get(page.startIcon)
                    if pageOfStartIcon is page:
                        break
                    if pageOfStartIcon is None:
                        continue
                    print('Page list out of sync with icon sequence')
        del self.topIcons[ic]
        ic.becomeTopLevel(True)  #... ??? This does not seem right

    def removePage(self, pageToRemove):
        """Remove a (presumably empty) page.  Because pages are single-direction linked
         list, this can only be done by exhaustively searching for the page, starting
        from self.sequences."""
        for seqStartPage in self.sequences:
            if seqStartPage is pageToRemove:
                idx = self.sequences.index(pageToRemove)
                nextPage = pageToRemove.nextPage
                if nextPage is None:
                    del self.sequences[idx]
                else:
                    self.sequences[idx] = nextPage
                return
            for page in seqStartPage.traversePages():
                if page.nextPage is pageToRemove:
                    page.nextPage = pageToRemove.nextPage
                    return
        print("removePage could not find page to remove")

    def replaceTop(self, old, new, transferStmtComment=True):
        """Replace an existing top-level icon with a new icon.  If the existing icon was
        part of a sequence, replace it in the sequence.  If the icon was not part of a
        sequence place it in the same location.  If "new" will own a code block, also
        integrate its corresponding block-end icon.  Does not re-layout or re-draw.
        Note that this call is not intended for integrating a new code block (new must
        have an empty block if it has one).  If the old icon owned a code block, the new
        icon will take it over if it can, or the owned block will be dedented back to the
        parent sequence."""
        # Note that order is important here, because the page infrastructure duplicates
        # some of the information in the icon sequences.  .removeTop should always be
        # called before tearing down the sequence connections, and .addTop should always
        # be called after building them up.  This is important for undo, as well which
        # separately tracks icon attachments and add/remove from the window structures.
        nextInSeq = old.nextInSeq()
        if isinstance(old, blockicons.ElseIcon):
            # Waste cycles to mark the block-owner of a removed else, dirty.  Necessary
            # because highlightError functions for block owners and else-icons can't
            # detect a *removed* else.
            blockOwner = icon.findBlockOwner(old)
            if blockOwner is not None:
                blockOwner.markLayoutDirty()
        if hasattr(old, 'blockEnd'):
            beforeBlockEnd = old.blockEnd.prevInSeq()
            if beforeBlockEnd is old:
                beforeBlockEnd = new
            afterBlockEnd = old.blockEnd.nextInSeq()
            self.removeTop([old, old.blockEnd])
            old.replaceChild(None, 'seqOut')
            old.blockEnd.replaceChild(None, 'seqIn')
            old.blockEnd.replaceChild(None, 'seqOut')
            if not isinstance(nextInSeq, icon.BlockEnd):
                new.replaceChild(nextInSeq, 'seqOut')
            if hasattr(new, 'blockEnd'):
                # New icon takes over old icon's code block (by transferring site
                # links, not ownership of the BlockEnd icon, to integrate with undo)
                if not isinstance(nextInSeq, icon.BlockEnd):
                    new.blockEnd.replaceChild(beforeBlockEnd, 'seqIn')
                new.blockEnd.replaceChild(afterBlockEnd, 'seqOut')
            else:
                # Icons in old block are dedented back to parent sequence
                beforeBlockEnd.replaceChild(afterBlockEnd, 'seqOut')
        else:
            self.removeTop(old)
            if nextInSeq is not None:
                old.replaceChild(None, 'seqOut')
                if hasattr(new, 'blockEnd'):
                    # BlockEnd (which is already attached to new icon's seqOut) linked in
                    new.blockEnd.replaceChild(nextInSeq, 'seqOut')
                else:
                    # Neither icon can own a code block
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
        if transferStmtComment and hasattr(old, 'stmtComment'):
            stmtComment = old.stmtComment
            stmtComment.detachStmtComment()
            stmtComment.attachStmtComment(new)

    def addTop(self, icons):
        """Place an icon or icons on the window at the top level.  If the icons are
        part of a sequence, they must be linked in to the sequence before calling this
        function. This call adds them to the window topIcons dictionary and assigns them
        to a (new or existing) page.  Does not re-layout or re-draw. """
        # Convert the added icon list to a set so it can be quickly tested against
        for ic, newSeq in self._orderIconsForAdd(icons):
            self.addTopSingle(ic, newSeq=newSeq)

    def _orderIconsForAdd(self, icons):
        """Takes a list of top-level icons to be added to or removed from the window,
        and returns them in an order in which they can be added such that pages
        can be inferred from adjacent icons as they are added (or for removal, that
        when removal is undone, they will be added in the appropriate order).  The fact
        that this ordering is necessary is unfortunate"""
        addedIcons = {i for i in (icons if hasattr(icons, '__iter__') else [icons])}
        # Find any icons in list that are connected to icons outside of the list.  If
        # found look for the attached icon in the topIcons list.  This is done first for
        # sequences attached at the top, then for sequences attached at the bottom.  As
        # these sequences are added to the sequencedIcons list, they are removed from
        # addedIcons, so sequences attached at both the top and bottom will not be listed
        # twice, and the the  remaining (unattached) icons will be left at the end.
        attachedSeqs = []
        sequencedIcons = []
        for ic in addedIcons:
            if ic.hasSite('seqIn'):
                prevIcon = ic.sites.seqIn.att
                if prevIcon is not None and prevIcon not in addedIcons:
                    attachedSeqs.append((ic, prevIcon))
        for ic, attachedTo in attachedSeqs:
            if self.topIcons.get(attachedTo) is None:
                print('Removed top icon with seqIn site pointed to unknown icon')
                continue
            seqIc = ic
            while True:
                addedIcons.remove(seqIc)
                sequencedIcons.append((seqIc, False))
                seqIc = seqIc.nextInSeq()
                if seqIc is None or seqIc not in addedIcons:
                    break
        attachedSeqs = []
        for ic in addedIcons:
            nextIcon = ic.nextInSeq()
            if nextIcon is not None and nextIcon not in addedIcons:
                attachedSeqs.append((ic, nextIcon))
        for ic, attachedTo in attachedSeqs:
            if self.topIcons.get(attachedTo) is None:
                print('Removed top icon with seqOut site pointed to unknown icon')
                continue
            seqIc = ic
            while True:
                addedIcons.remove(seqIc)
                sequencedIcons.append((seqIc, False))
                seqIc = seqIc.prevInSeq()
                if seqIc is None or seqIc not in addedIcons:
                    break
        # Any remaining icons are not part of an existing sequence.  Organize them in to
        # (new) sequences and add them top-down to sequencedIcons.  Adding them top-down
        # allows addTopSingle to create a new page and add it to the sequence list, and
        # put the remaining icons in the sequence in the same page.
        remainingSeqs = []
        for ic in addedIcons:
            if ic.prevInSeq() is None:
                remainingSeqs.append(ic)
        for ic in remainingSeqs:
            seqIc = ic
            while True:
                addedIcons.remove(seqIc)
                sequencedIcons.append((seqIc, seqIc==ic))
                seqIc = seqIc.nextInSeq()
                if seqIc is None or seqIc not in addedIcons:
                    break
        # As a check on the whole process, addedIcons should now have all been sorted in
        # sequencedIcons, so addedIcons should be empty.
        if len(addedIcons) != 0:
            print('addTop left icons unaccounted')
        return sequencedIcons

    def addTopSingle(self, ic, newSeq=False, pos=None):
        """Add a single icon to the window's top-level icon lists (.topIcons and
        .sequences).  If ic is part of a sequence, this is probably not the appropriate
        call (use .addTop(), instead), as each icon of a sequence must be added in an
        order that allows the page to be determined.  If newSeq is True, will force
        creation of a new .sequences entry and a new page rather than looking at sequence
        attachments.  If ic is part of a sequence, this call must be made AFTER ic has
        been linked in to the sequence."""
        # Page is determined by the icon's seqIn/seqOut attachments as follows: if the
        # icon is attached with its seqIn site, it is added to the page of the previous
        # icon.  If it is attached only via seqOut, it is added to the page of the next
        # icon in the sequence.  If it is attached to neither, a new page is created.
        self.undo.registerAddToTopLevel(ic, newSeq)
        if pos is not None:
            ic.rect = icon.moveRect(ic.rect, pos)
        prevIcon = ic.prevInSeq()
        if prevIcon is None:
            nextIcon = ic.nextInSeq()
            if nextIcon is None or newSeq:
                page = Page()
                page.startIcon = ic
                pageRect = ic.rect
                page.topY = pageRect[1]
                page.bottomY = pageRect[3]
                page.iconCount = 0
                self.sequences.append(page)
            else:
                page = self.topIcons.get(nextIcon)
                if page is None:
                    print("addTopSingle couldn't infer page for attached icon")
                if page.startIcon is nextIcon:
                    page.startIcon = ic
        else:
            page = self.topIcons.get(prevIcon)
            if page is None:
                nextIcon = ic.nextInSeq()
                if nextIcon is None or nextIcon not in self.topIcons:
                    print("addTopSingle couldn't infer page for added icon")
                page = self.topIcons[nextIcon]
                if page.startIcon is nextIcon:
                    page.startIcon = ic
        self.topIcons[ic] = page
        page.layoutDirty = True
        page.iconCount += 1  # Splitting too-large pages is deferred to layout time
        # Detaching icons should remove all connections, but the consequence to
        # leaving a parent link at the top level is dire, so make sure all parent
        # links are removed.
        for parentSite in ic.parentSites():
            lingeringParent = ic.childAt(parentSite)
            if lingeringParent:
                print("Removing lingering parent link to icon added to top")
                lingeringParent.replaceChild(None, lingeringParent.siteOf(ic))
        # Even if the icon was properly laid out in its former context, the margin at
        # this location and indent level is probably different.
        ic.markLayoutDirty()
        ic.becomeTopLevel(True)

    def findSequences(self, topIcons):
        """Find the starting icons for all sequences in a list of top (stmt) icons."""
        sequenceTops = {}
        topIconSeqs = {}
        for topIcon in topIcons:
            if topIcon not in topIconSeqs:
                topOfSeq = icon.findSeqStart(topIcon)
                sequenceTops[topOfSeq] = True
                for seqIcon in icon.traverseSeq(topOfSeq):
                    topIconSeqs[seqIcon] = topOfSeq
        return sequenceTops.keys()

    def layoutDirtyIcons(self, draggingIcons=None, filterRedundantParens=True):
        """Look for icons marked as needing layout and lay them out.  If draggingIcons is
        specified, assume a stand-alone list of top icons not of the window.  Otherwise
        look at all of the icons in the window.  Returns a rectangle representing the
        changed areas that need to be redrawn, or None if nothing changed."""
        redrawRegion = comn.AccumRects()
        if draggingIcons is not None:
            for seq in self.findSequences(draggingIcons):
                redraw, _, _ = self.layoutIconsInSeq(seq, filterRedundantParens)
                redrawRegion.add(redraw)
        else:
            for seqStartPage in self.sequences:
                redrawRegion.add(self.layoutIconsInPage(seqStartPage, filterRedundantParens))
        return redrawRegion.get()

    def layoutIconsInPage(self, startPage, filterRedundantParens, checkAllForDirty=True):
        """Lay out all icons on a given page. if checkAllForDirty is True, will check the
        entire sequence following page for dirty icons and redo those layouts as well.
        If False, only startPage is assumed to require layout, and the remaining pages
        will only be traversed if an offset needs to be propagated to them.  Side effects
        are: splitting large pages and updating the window's scroll bars if the content
        extent has changed."""
        # Traverse the pages in the sequence: 1) looking for pages that need to be laid
        # out, and 2) applying accumulated changes to y position from earlier changes.
        redrawRegion = comn.AccumRects()
        offsetDelta = 0
        pagesNeedingSplit = []
        for page in startPage.traversePages():
            if page.iconCount > PAGE_SPLIT_THRESHOLD:
                pagesNeedingSplit.append(page)
            if not page.layoutDirty:
                # The page does not need layout
                if offsetDelta == 0:
                    if not checkAllForDirty:
                        break
                else:
                    # The page needs offset but not layout, so just update the unapplied
                    # offset and y range, which will be applied to icons when needed.
                    page.unappliedOffset += offsetDelta
                    page.topY += offsetDelta
                    page.bottomY += offsetDelta
                    windowLeft = self.scrollOrigin[0]
                    windowRight = windowLeft + self.image.width
                    redrawRegion.add((windowLeft, page.topY, windowRight, page.bottomY))
                continue
            # The page is marked as needing layout.
            if page.startIcon.nextInSeq() is None and page.startIcon.prevInSeq() is None:
                # The page contains a single icon that is not part of a sequence
                redrawRegion.add(page.startIcon.hierRect())
                if filterRedundantParens:
                    self.filterRedundantParens(page.startIcon)
                page.startIcon.layout()
                pageRect = page.startIcon.hierRect()
                page.topY = pageRect[1]
                page.bottomY = pageRect[3]
                redrawRegion.add(pageRect)
                continue
            # Traverse the sequence of icons in the page looking for icons that need to
            # be laid out.  The page may have unapplied offset, but that will be remedied
            # by layoutIconsInSeq (unapplied offset will mess up the call's redraw rect
            # for the original location, but presumably, displayed areas will not have
            # unapplied offset, and redraw regions outside the window are clipped off).
            page.topY += offsetDelta
            redrawRect, bottomY, seqOutX = self.layoutIconsInSeq(page.startIcon,
             filterRedundantParens, fromTopY=page.topY, restrictToPage=page)
            redrawRegion.add(redrawRect)
            page.unappliedOffset = 0
            page.layoutDirty = False
            page.bottomY = bottomY
            if page.nextPage is not None:
                offsetDelta = bottomY - page.nextPage.topY
                nextIcon = page.nextPage.startIcon
                if nextIcon is not None:
                    x, y = nextIcon.pos(preferSeqIn=True)
                    if x != seqOutX:
                        # X shifts are rare as edits are usually balanced, but can
                        # happen: propagate to next page and force layout.
                        nextIcon.rect = comn.offsetRect(nextIcon.rect, seqOutX - x, 0)
                        if hasattr(nextIcon, 'stmtComment'):
                            nextIcon.stmtComment.rect = comn.offsetRect(
                                nextIcon.stmtComment.rect, seqOutX - x, 0)
                        page.nextPage.layoutDirty = True
                        nextIcon.markLayoutDirty()
        # If a page was found with more than PAGE_SPLIT_THRESHOLD icons, split it up
        for page in pagesNeedingSplit:
            page.split()
        # Window content likely changed, update the scroll bars
        self._updateScrollRanges()
        return redrawRegion.get()

    def layoutIconsInSeq(self, seqStartIcon, filterRedundantParens, fromTopY=None,
            restrictToPage=None):
        """Lay out all icons in a sequence starting from seqStartIcon. if
        filterRedundantParens is True, apply redundant paren filter before laying out.
        If fromTop specifies a value, line up the layout below that y value.  If fromTop
        is None, position the sequence or output site of seqStartIcon identically.  If
        restrictToPage is True, stop at the end of the page rather than processing the
        entire sequence.  Returns three values: the modified region (rectangle) of the
        window, the new bottomY of the sequence/page, and the seqOut site offset of the
        last icon on the page."""
        redrawRegion = comn.AccumRects()
        x, y = seqStartIcon.pos(preferSeqIn=True)
        if fromTopY is not None:
            y = fromTopY
        if not seqStartIcon.hasSite('seqIn'):
            # Icon can not be laid out by sequence site.  Just lay it out by itself
            redrawRegion.add(seqStartIcon.hierRect())
            seqStartIcon.layout((x, y))
            hierRect = seqStartIcon.hierRect()
            redrawRegion.add(hierRect)
            return redrawRegion.get(), hierRect[3], x
        if filterRedundantParens:
            # filterRedundantParens can modify sequence, so must operate on a copy
            for ic in list(icon.traverseSeq(seqStartIcon, restrictToPage=restrictToPage)):
                if ic.layoutDirty:
                    self.filterRedundantParens(ic)
        for seqIc in icon.traverseSeq(seqStartIcon, restrictToPage=restrictToPage):
            seqIcOrigRect = seqIc.hierRect()
            xOffsetToSeqIn, yOffsetToSeqIn = seqIc.posOfSite('seqIn')
            yOffsetToSeqIn -= seqIcOrigRect[1]
            if seqIc.layoutDirty or hasattr(seqIc, 'stmtComment') and \
                    seqIc.stmtComment.layoutDirty:
                redrawRegion.add(seqIcOrigRect)
                layout = seqIc.layout((0, 0))
                # Find y offset from top of layout to the seqIn site by which the icon
                # needs to be positioned.  parentSiteOffset of layout may represent either
                # output site or seqInsert site and needs to be moved to the seqIn.
                if seqIc.hasSite('output'):
                    anchorSite = seqIc.sites.output
                elif seqIc.hasSite('seqInsert'):
                    anchorSite = seqIc.sites.seqInsert
                else:
                    anchorSite = seqIc.sites.seqIn  # Only BlockEndIcon
                yOffsetToSeqIn = layout.parentSiteOffset + seqIc.sites.seqIn.yOffset - \
                        anchorSite.yOffset
            # At this point, y is the seqIn site position if it is the first icon in the
            # sequence and fromTopY is False.  Otherwise y is the bottom of the layout of
            # the statement above.  Adjust it to be the desired y of the seqIn site.
            if fromTopY is not None or seqIc is not seqStartIcon:
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
                for ic in seqIc.traverse(inclStmtComment=True):
                    ic.rect = comn.offsetRect(ic.rect, xOffset, yOffset)
                seqIcNewRect = seqIc.hierRect()
                redrawRegion.add(seqIcNewRect)
            y = seqIcNewRect[3] - 1  # Minimal line spacing (overlap icon borders)
            x = seqIc.posOfSite('seqOut')[0]
        return redrawRegion.get(), y, x

    def siteSelected(self, evt):
        """Look for icon sites near button press, if found return icon and site"""
        btnX, btnY = self.imageToContentCoord(evt.x, evt.y)
        left = btnX - SITE_SELECT_DIST
        right = btnX + SITE_SELECT_DIST
        top = btnY - SITE_SELECT_DIST
        bottom = btnY + SITE_SELECT_DIST
        minDist = SITE_SELECT_DIST + 1
        minSite = (None, None, None)
        for ic in self.findIconsInRegion((left, top, right, bottom), order='pick'):
            iconSites = ic.snapLists(forCursor=True)
            for siteType, siteList in iconSites.items():
                for siteIcon, (x, y), siteName, *_ in siteList:
                    # Tweak site location based on cursor appearance and differentiation
                    if siteType in ("input", "output"):
                        x += 2
                    elif siteType in ("attrIn", "attrOut"):
                        y -= icon.ATTR_SITE_OFFSET
                        x += 1
                    elif siteType == "seqIn":
                        y -= 1
                    elif siteType == "seqOut":
                        y += 1
                    elif siteType == "cprhOut" and not ic.childAt(siteName):
                        pass
                    else:
                        continue  # not a visible site type
                    dist = (abs(btnX - x) + abs(btnY - y))
                    if dist < minDist or (dist == minDist and
                     minSite[2] in ("attrOut", "output")):  # Prefer inputs, for now
                        minDist = dist
                        minSite = siteIcon, siteName, siteType
        if minDist < SITE_SELECT_DIST + 1:
            return minSite[0], minSite[1]
        return None, None

    def filterRedundantParens(self, ic, parentIcon=None, parentSite=None):
        """Remove parentheses whose arguments are BinOpIcons that would deploy their own
        parentheses upon the next layout if not for the enclosing cursor paren."""
        if ic.__class__ is not parenicon.CursorParenIcon or not ic.closed:
            for c in ic.children():
                self.filterRedundantParens(c, ic, ic.siteOf(c))
            return
        argIcon = ic.sites.argIcon.att
        if argIcon is None:
            return
        if not (argIcon.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and
                not argIcon.hasParens and opicons.needsParens(argIcon, parentIcon)):
            self.filterRedundantParens(argIcon, ic, "argIcon")
            return
        # Redundant parens found: remove them
        if parentIcon is None:
            # Not sure this ever happens: arithmetic ops require parent to force parens,
            # and tuple conversion removes the redundant paren icon, itself.
            self.replaceTop(ic, argIcon)
        else:
            parentIcon.replaceChild(argIcon, parentSite)
            argIcon.markLayoutDirty()
        # Transfer any attribute icons to the promoted expression
        attrIcon = ic.sites.attrIcon.att
        ic.replaceChild(None, 'attrIcon')
        if attrIcon is not None and argIcon.hasSite('attrIcon'):
            argIcon.replaceChild(attrIcon, 'attrIcon')
        # If the cursor was on the paren being removed, move it to the icon that has
        # taken its place (BinOp or CursorParen)
        if self.cursor.type == "icon" and self.cursor.icon is ic and \
         self.cursor.siteType == "attrIn":
            self.cursor.setToIconSite(argIcon, "attrIcon")
        self.filterRedundantParens(argIcon)

    def imageToContentCoord(self, imageX, imageY):
        """Convert a coordinate from the screen image of the window to the underlying
        content of the window (convert scrolled to unscrolled coordinates)"""
        return imageX + self.scrollOrigin[0], imageY + self.scrollOrigin[1]

    def contentToImageCoord(self, contentX, contentY):
        """Convert a coordinate from icon content of the window to the screen image
        content of the window (convert scrolled to unscrolled coordinates)"""
        return contentX - self.scrollOrigin[0], contentY - self.scrollOrigin[1]

    def contentToImageRect(self, contentRect):
        return comn.offsetRect(contentRect, -self.scrollOrigin[0], -self.scrollOrigin[1])

    def resetBlinkTimer(self, holdTime=CURSOR_BLINK_RATE):
        """Stop pending cursor blink event and reschedule it for holdTime milliseconds in
        the future."""
        appData.resetBlinkTimer(holdTime=holdTime)

class Page:
    """The fact that icons know their own window positions becomes problematic for very
    large files, because tiny edits can relocate every single icon below them in the
    sequence.  To make this work, the Page structure was added to maintain an "unapplied
    offset" to a range of icons in a sequence.  When icons become visible and need to
    know their absolute positions, applyOffset can be called to update them.  The other
    issue that pages address is the need to quickly find icons by position, without
    traversing the entire tree."""
    def __init__(self):
        self.unappliedOffset = 0
        self.layoutDirty = False
        self.topY = 0
        self.bottomY = 0
        self.iconCount = 0
        self.startIcon = None
        self.nextPage = None

    def split(self):
        """Split this page, if it is too long, in to as many pages as necessary to bring
        the size of each below PAGE_SPLIT_THRESHOLD."""
        origStmtCnt = self.iconCount
        if origStmtCnt <= PAGE_SPLIT_THRESHOLD:
            return
        numNewPages = 1 + (origStmtCnt - 1) // PAGE_SPLIT_THRESHOLD
        newPageMax = 1 + (origStmtCnt - 1) // numNewPages
        pageStmtCnt = 0
        totalStmtCnt = 0
        page = self
        for ic in icon.traverseSeq(self.startIcon):
            pageStmtCnt += 1
            totalStmtCnt += 1
            if pageStmtCnt > newPageMax:
                # number of stmts on page exceeds max.  ic should start a new page
                page.bottomY = ic.hierRect()[1] + page.unappliedOffset
                page.iconCount = pageStmtCnt - 1
                newPage = Page()
                newPage.nextPage = page.nextPage
                page.nextPage = newPage
                newPage.unappliedOffset = page.unappliedOffset
                newPage.layoutDirty = page.layoutDirty
                newPage.topY = page.bottomY
                newPage.startIcon = ic
                page = newPage
                pageStmtCnt = 1
            if page is not self:
                # Update entries in .topIcons list to point to new owning page
                ic.window.topIcons[ic] = page
            if totalStmtCnt >= origStmtCnt:
                # ic is the last icon in the original page
                break
        page.bottomY = ic.hierRect()[3] + page.unappliedOffset
        page.iconCount = pageStmtCnt

    def traversePages(self):
        """Return each of the pages following this page in the sequence"""
        page = self
        while page is not None:
            yield page
            page = page.nextPage

    def traverseSeq(self, hier=False, order="draw", inclStmtComments=False):
        """Traverse the icons in the page (note, generator).  If hier is False, just
        return the top icons in the sequence.  If hier is True, return all icons.  order
        can be either "pick" or "draw", and controls hierarchical (hier=True) traversal.
        Parent icons are allowed to hide structure under child icons, so picking must be
        done child-first, and drawing must be done parent-first."""
        count = 0
        for ic in icon.traverseSeq(self.startIcon):
            page = ic.window.topIcons[ic]
            if page is not self:
                break
            count += 1
            if hier:
                yield from ic.traverse(order=order, inclStmtComment=inclStmtComments)
            else:
                yield ic
        if count != self.iconCount:
            # This shouldn't happen, but this is a cheap place to verify that iconCount
            # matches the length of the sequence to which it is attached.
            print('Page icon count does not agree with attached sequence, fixing')
            self.iconCount = count

    def applyOffset(self):
        """If the page has an unapplied offset, apply it (move all of the icons on the
        page vertically by unappliedOffset and set it to 0)."""
        if self.unappliedOffset == 0:
            return
        for ic in self.traverseSeq(hier=True, inclStmtComments=True):
            l, t, r, b = ic.rect
            ic.rect = l, t + self.unappliedOffset, r, b + self.unappliedOffset
        self.unappliedOffset = 0

def findLeftOuterIcon(clickedIcon, btnPressLoc, fromIcon=None):
    """Because we have icons with no pickable structure left of their arguments (binary
    operations), we have to make rules about what it means to click or drag the leftmost
    icon in an expression.  For the purpose of selection, that is simply the icon that was
    clicked.  For dragging and double clicking (execution), this function finds the
    outermost operation that claims the clicked icon as its leftmost operand."""
    # One idiotic case we have to distinguish, is when the clicked icon is a BinOpIcon
    # with automatic parens visible: only if the user clicked on the left paren can
    # the icon be the leftmost object in an expression.  Clicking on the body or the
    # right paren does not count.
    if fromIcon is None:
        fromIcon = clickedIcon.topLevelParent()
    if clickedIcon.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and \
            clickedIcon.hasParens:
        if not clickedIcon.locIsOnLeftParen(btnPressLoc):
            return clickedIcon
    if clickedIcon is fromIcon:
        return clickedIcon
    # Only binary operations are candidates, and only when the expression directly below
    # has claimed itself to be the leftmost operand of an expression
    if fromIcon.__class__ is assignicons.AssignIcon:
        leftSiteIcon = fromIcon.sites.targets0[0].att
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is assignicons.AugmentedAssignIcon:
        leftSiteIcon = fromIcon.sites.targetIcon.att
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is listicons.TupleIcon and fromIcon.noParens:
        leftSiteIcon = fromIcon.childAt('argIcons_0')
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and \
            fromIcon.leftArg() is not None:
        left = findLeftOuterIcon(clickedIcon, btnPressLoc, fromIcon.leftArg())
        if left is fromIcon.leftArg():
            targetIsBinOpIcon = \
                clickedIcon.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon)
            if not targetIsBinOpIcon or targetIsBinOpIcon and clickedIcon.hasParens:
                # Again, we have to check before claiming outermost status for fromIcon,
                # if its left argument has parens, whether its status as outermost icon
                # was earned by promotion or by a direct click on its parens.
                if left.__class__ not in (opicons.BinOpIcon, opicons.IfExpIcon) or \
                        not left.hasParens or left.locIsOnLeftParen(btnPressLoc):
                    return fromIcon  # Claim outermost status for this icon
    # Pass on any results from below fromIcon in the hierarchy
    children = fromIcon.children()
    if children is not None:
        for child in fromIcon.children():
            result = findLeftOuterIcon(clickedIcon, btnPressLoc, child)
            if result is not None:
                return result
    return None

def textRepr(icons):
    topIcons = findTopIcons(icons)
    branchDepth = 0
    clipText = []
    for ic in topIcons:
        if isinstance(ic, icon.BlockEnd):
            branchDepth -= 1
        else:
            if ic.__class__ in (blockicons.ElifIcon, blockicons.ElseIcon):
                indent = "    " * max(0, branchDepth-1)
            else:
                indent = "    " * max(0, branchDepth)
            if hasattr(ic, 'blockEnd'):
                branchDepth += 1
            clipText.append(indent + ic.textRepr())
    return "\n".join(clipText)

class App:
    def __init__(self):
        self.windows = []
        self.root = tk.Tk()
        self.root.overrideredirect(1)  # Stop vestigial root window from flashing up
        self.root.iconbitmap("python-g.ico")
        self.root.withdraw()
        self.newWindow()
        self.frameCount = 0
        self.blinkCancelId = None
        #self.animate()

    def mainLoop(self):
        # self.root.after(2000, self.animate)
        self.blinkCancelId = self.root.after(CURSOR_BLINK_RATE, self._blinkCursor)
        self.root.mainloop()

    def animate(self):
        print(self.frameCount, msTime())
        self.frameCount += 1
        self.root.after(10, self.animate)

    def removeWindow(self, window):
        self.windows.remove(window)
        if len(self.windows) == 0:
            exit(1)

    def newWindow(self, filename=None):
        window = Window(self.root, filename)
        self.windows.append(window)
        if filename is None:
            return
        print("before open file")
        if not window.openFile(filename):
            window.close()

    def resetBlinkTimer(self, holdTime=CURSOR_BLINK_RATE):
        """Cancel the next cursor blink and reschedule it for holdTime milliseconds in
        the future."""
        if self.blinkCancelId is not None:
            self.root.after_cancel(self.blinkCancelId)
        self.blinkCancelId = self.root.after(holdTime, self._blinkCursor)

    def _blinkCursor(self):
        focusWidget = self.root.focus_get()
        for window in self.windows:
            if window.top == focusWidget:
                window.cursor.blink()
                break
        self.blinkCancelId = self.root.after(CURSOR_BLINK_RATE, self._blinkCursor)

    def findWindowWithFile(self, filename):
        for window in self.windows:
            if window.winName == filename:
                return window
        return None

def isStmtComment(ic):
    return isinstance(ic, commenticon.CommentIcon) and ic.attachedToStmt is not None

def findTopIcons(icons, stmtLvlOnly=False):
    """ Find the top icon(s) within a list of icons.  If stmtLvlOnly is True, the only
    criteria is that the icons have no parent.  If stmtLvlOnly is False, icons that have
    a parent but that parent is not in the list, are also returned."""
    if stmtLvlOnly:
        return [ic for ic in icons if ic.parent() is None and not isStmtComment(ic)]
    iconSet = set(icons)
    return [ic for ic in icons if ic.parent() not in iconSet and not isStmtComment(ic)]

def clipboardRepr(icons, offset):
    """Top level function for converting icons into their serialized string representation
    for copying to the clipboard.  icons should be a list of icons to be copied."""
    seriesLists = findSeries(icons)
    iconsToCopy = set(icons)
    seqLists = []
    for sequence in seriesLists['sequences']:
        seqLists.append([ic.clipboardRepr(offset, iconsToCopy) for ic in sequence])
    for series in seriesLists['lists']:
        children = ["argIcons"] + [ic.clipboardRepr(offset, iconsToCopy) for ic in series]
        seqLists.append([("TupleIcon", icon.addPoints(series[0].rect[:2], (0, 5)),
         {'noParens':True}, [children])])
    for ic in seriesLists['individual']:
        seqLists.append([ic.clipboardRepr(offset, iconsToCopy)])
    return repr(seqLists)

def orderTopIcons(topIcons):
    """Given a list of top icons, returns a list of groups of those icons that appear on
    the same sequence, in the order in which they appear in that sequence."""
    unsequenced = set(topIcons)
    sequences = []
    for topIc in topIcons:
        if topIc not in unsequenced:
            continue
        # The code, below runs just once for each sequence found, so it only costs order
        # N for each sequence.  Unfortunately, that's still wasteful as N is the length
        # of the sequence (probably the entire module), not of the length of topIcons, so
        # this could be improved.
        sequence = []
        seqStart = icon.findSeqStart(topIc)
        for ic in icon.traverseSeq(seqStart):
            if ic in unsequenced:
                sequence.append(ic)
                unsequenced.remove(ic)
        sequences.append(sequence)
    return sequences

def findSeries(icons):
    """Returns a list of groups of icons that appear on the same sequence, list, tuple,
    set, parameter list, or dictionary(disregarding intervening icons not in "icons", in
    the order that they appear in the series, and tagged with the type of series."""
    #... This function can be significantly pruned, now that it is no longer responsible
    #    for reassembling icons on deletion, and is only used for finding sequences in
    #    pasted icons.  I'm not bothering, yet, because the code for pasting from the
    #    clipboard is due for rewrite
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
            if not iconsites.isSeriesSiteId(parentSite):
                continue
            seriesName, idx = iconsites.splitSeriesSiteId(parentSite)
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

def splitDeletedIcons(ic, toDelete, assembleDeleted, needReorder):
    """Remove icons in set, toDelete, from ic and the icons below it in the hierarchy,
    and return a pair of results, the first representing the icons remaining in the tree
    and the second representing the icons removed from the tree (if assembleDeleted is
    True).  A value of None indicates that ic remains in the corresponding tree.  If not
    None, the value will be a placement-list (see icon.placeArgs) style list (possibly
    empty), representing the remaining icons that need to replace it in the corresponding
    tree.  If ic itself appears in toDelete, it will appear in the deleted icon placement
    list but will not be detached from its parent. The function calls itself recursively,
    creating a single tree (or placement list of trees) out of the remaining icons and
    (if requested via assembleDeleted), a single tree or list out of the deleted icons.
    If necessary, it inserts placeholder icons to retain icons that cannot otherwise be
    attached to incompatible sites."""
    # Note that this code can be confusing to read, because rather than keep the deleted
    # and non-deleted trees separate, it immediately categorizes them into the tree that
    # will remain attached to ic (withIc) and the tree that will be detached from it
    # (splitFromIc).  This reduces duplication in the code but also adds an extra layer
    # of indirection.
    icDeleted = ic in toDelete
    splitList = []
    argsDetached = False
    for siteOrSeries in ic.sites.traverseLexical():
        if isinstance(siteOrSeries, iconsites.IconSiteSeries):
            # Site series
            removedCprhSites = [] if siteOrSeries.type == 'cprhIn' else None
            splitSeriesList = []
            for site in list(siteOrSeries):
                if site.att is None:
                    # Empty sites are considered an attribute of the icon (as we can't
                    # delete the absence of something), so stay with it, deleted or not.
                    continue
                if icDeleted:
                    splitFromIc, withIc = splitDeletedIcons(site.att, toDelete,
                        assembleDeleted, needReorder)
                else:
                    withIc, splitFromIc = splitDeletedIcons(site.att, toDelete,
                        assembleDeleted, needReorder)
                if splitFromIc is None:
                    if assembleDeleted or icDeleted:
                        splitSeriesList.append([site.att])
                else:
                    if len(splitFromIc) > 0 and (assembleDeleted or icDeleted):
                        splitSeriesList.append(splitFromIc)
                if withIc is not None:
                    # The attached icon needs to be removed.  Reduce the replacement list
                    # (unless it's a simple deletion as indicated by an empty list) to a
                    # series and splice the resulting icons into the series.  The code
                    # uses the fact that sites are renamed on insert and delete, to get
                    # the current series index regardless of prior inserts/deletes)
                    argsDetached = True
                    seriesIcons = placeListToSeries(withIc)
                    if len(seriesIcons) == 0:
                        ic.replaceChild(None, site.name)
                    elif removedCprhSites is not None:
                        removedCprhSites.append((site, seriesIcons))
                    else:
                        ic.replaceChild(seriesIcons[0], site.name)
                        name, idx = iconsites.splitSeriesSiteId(site.name)
                        ic.insertChildren(seriesIcons[1:], name, idx+1)
            if removedCprhSites is not None and len(removedCprhSites) > 0:
                # Comprehensions were removed from ic
                if len(removedCprhSites) == len(siteOrSeries) - 1:
                    # All comprehensions removed: turn back in to a list
                    for site, siteIcons in removedCprhSites:
                        ic.replaceChild(None, site.name)
                    toInsert = [i for il in removedCprhSites for i in il[1]]
                    ic.insertChildren(toInsert, 'argIcons', 1)
                else:
                    # A rare and horrible mix of comprehensions and other icons resulting
                    # from the deletion of the comprehension without deleting its args.
                    # Create  placeholder icons to hang all non-matching bits from either
                    # the rightmost site of the comprehension target or of the remaining
                    # prior comprehension
                    attachToSites = []
                    removedIdxs = set()
                    for site, siteIcons in removedCprhSites:
                        _, siteIdx = iconsites.splitSeriesSiteId(site.name)
                        for idx in range(siteIdx-1, -1, -1):
                            if idx not in removedIdxs:
                                attachToSites.append(ic.sites.cprhIcons[idx])
                                break
                        else:
                            attachToSites.append(ic.sites.argIcons[0])
                        removedIdxs.add(siteIdx)
                    for site, _ in removedCprhSites:
                        ic.replaceChild(None, site.name)
                    attachToEntryIcs = {}
                    for (_, siteIcons), attachToSite in zip(removedCprhSites,
                            attachToSites):
                        if attachToSite in attachToEntryIcs:
                            entryIc = attachToEntryIcs[attachToSite]
                        else:
                            entryAttachIc, entryAttachSite = icon.rightmostFromSite(ic,
                                attachToSite.name)
                            entryIc = entryicon.EntryIcon(window=ic.window)
                            entryAttachIc.replaceChild(entryIc, entryAttachSite)
                            attachToEntryIcs[attachToSite] = entryIc
                        entryIc.appendPendingArgs(siteIcons)
            if assembleDeleted or icDeleted:
                if len(splitSeriesList) == 1:
                    appendToPlaceList(splitList, splitSeriesList[0], needReorder)
                elif len(splitSeriesList) > 1:
                    for p in splitSeriesList:
                        appendToPlaceList(splitList, [placeListToSeries(p)], needReorder)
        elif siteOrSeries.att is not None:
            # Individual site
            if icDeleted:
                splitFromIc, withIc = splitDeletedIcons(siteOrSeries.att, toDelete,
                    assembleDeleted, needReorder)
            else:
                withIc, splitFromIc = splitDeletedIcons(siteOrSeries.att, toDelete,
                    assembleDeleted, needReorder)
            if assembleDeleted or icDeleted:
                if splitFromIc is None:
                    appendToPlaceList(splitList, [siteOrSeries.att], needReorder)
                elif len(splitFromIc) > 0:
                    appendToPlaceList(splitList, splitFromIc, needReorder)
            if withIc is not None:
                # Deletion resulted in a placement list (though it may be empty).  Reduce
                # it to a single icon and replace the existing attached icon with it.
                argsDetached = True
                singleIcon = placeListToSingleIcon(withIc, siteOrSeries.type)
                ic.replaceChild(singleIcon, siteOrSeries.name)
    subsList = None
    if isinstance(ic, entryicon.EntryIcon):
        if argsDetached:
            ic.pruneEmptyPendingArgSites()
        if ic.text == '':
            # The icon is a placeholder entry icon.  If the there's just one pending
            # argument and it's compatible with the site: get rid of the placeholder.
            pendingArgs = ic.listPendingArgs()
            nonEmptyArgs = [ic for ic, _, _ in icon.placementListIter(pendingArgs,
                includeEmptySeriesSites=False)]
            if len(nonEmptyArgs) == 0:
                # Everything has been stripped off of placeholder icon, get rid of it
                subsList = []
            elif len(nonEmptyArgs) == 1 and ic.attachedIcon() is not None and \
                    iconsites.matingSiteType[ic.attachedSiteType()] in \
                    (s.type for s in nonEmptyArgs[0].sites.parentSites()):
                # Entry icon has a single pending arg that's compatible with parent site.
                # remove the entry icon.  (Note that this is stupidly testing against the
                # original parent.  Testing the new parent is more complicated, so we do
                # this and let the parent iteration recreate the placeholder if we're
                # wrong.  This will also miss some opportunities for cleanup, though, in
                # practice I haven't found any cases not handled by other placeholder-
                # trimming code)
                ic.popPendingArgs('all')
                subsList = [nonEmptyArgs[0]]
    return (splitList, subsList) if icDeleted else (subsList, splitList)

def placeListToTopLevelIcon(placeList, forSequence):
    """Create an icon tree from a placement-list-format list of icons (placeList).
    Specify forSequence if the icon will need to be part of a sequence (for which icons
    that attach only to attribute and comprehension sites need a placeholder icon to
    adapt)."""
    # Since we can make a reasonable top level icon by creating a naked tuple, we can use
    # placeListToSeries to do most of the work.  However, if the placement list contains
    # just one icon, and that one icon is not compatible with an input site and the icon
    # is not destined to be part of a sequence, placeListToSeries would create an
    # unnecessary placeholder icon, so handle this case first and separately.
    if not forSequence and len(placeList) == 1 and \
            not isinstance(placeList[0], (list, tuple, entryicon.EntryIcon)) and \
            'output' not in placeList[0].sites.parentSites():
        return placeList[0]
    # Use placeListToSeries, to transform the list.  This is reasonable even for single
    # icons, since placement lists are not allowed to contain statement-level icons, and
    # anything else that needs a placeholder icon to be part of a series, also needs one
    # to be part of a sequence.
    seriesIcons = placeListToSeries(placeList)
    if len(seriesIcons) == 0:
        return None
    elif len(seriesIcons) == 1:
        return seriesIcons[0]
    firstIcon, _, _ = icon.firstPlaceListIcon(placeList)
    if firstIcon is None:
        return None
    topIcon = listicons.TupleIcon(window=firstIcon.window, noParens=True)
    topIcon.insertChildren(seriesIcons, 'argIcons', 0)
    topIcon.rect = icon.moveRect(topIcon.rect, firstIcon.rect[:2])
    return topIcon

def placeListToSeries(placeList):
    """Convert the place list to a list of icons to be represented as a series (while
    we do have the concept of a series of comprehension sites, this call returns only
    the normal input-site series type)."""
    seriesIcons = []
    for entry in placeList:
        if isinstance(entry, (list, tuple)):
            # Series are expected to be inputs, add entire series
            seriesIcons += entry
        elif isinstance(entry, entryicon.EntryIcon) and entry.text == '':
            # entry is an entry icon.  If it's all inputs, it can be dropped, and if
            # it's not, it's still a valid series member.
            pendingArgs = entry.listPendingArgs()
            nonEmptyArgs = [ic for ic, _, _ in icon.placementListIter(pendingArgs,
                includeEmptySeriesSites=False)]
            if len(nonEmptyArgs) == 0:
                continue
            for ic in nonEmptyArgs:
                if 'output' not in (s.name for s in ic.sites.parentSites()):
                    seriesIcons.append(entry)
                    break
            else:
                entry.popPendingArgs('all')
                seriesIcons += nonEmptyArgs
        elif entry is None or 'output' in (s.name for s in entry.sites.parentSites()):
            # entry is icon that is compatible with an input
            seriesIcons.append(entry)
        else:
            # entry is icon that is not compatible with an input site.  Since the
            # deletion process merges icons into the placement list as it adds them, we
            # know all possible merging is already done, and all we can do is create a
            # placeholder icon.  The one exception is that we may have converted the
            # prior icon to a placeholder (or it may already have been), in which case,
            # we can just add the icon to the prior one's pending args.
            if len(seriesIcons) > 0 and seriesIcons[-1] is not None and \
                    isinstance(seriesIcons[-1], entryicon.EntryIcon):
                entryIc = seriesIcons[-1]
            else:
                entryIc = entryicon.EntryIcon(window=entry.window)
                seriesIcons.append(entryIc)
            entryIc.appendPendingArgs([entry])
    return seriesIcons

def placeListToSingleIcon(placeList, requiredMatingSiteType):
    """Create an icon tree with a single icon at the top from, a placement list
    (placeList) for a site of type requiredMatingSite.  Adds placeholder icons as needed
    to adapt the type and/or number of icons to the requested site type.  This code is
    aggressive in trying to avoid adding placeholders, in that it will throw away empty
    series sites (losing commas that the user typed) to get down to a single icon."""
    firstIc = None
    secondIc = None
    for ic, _, _ in icon.placementListIter(placeList, includeEmptySeriesSites=False):
        if firstIc is None:
            firstIc = ic
        else:
            secondIc = ic
            break
    if firstIc is None:
        return None
    if secondIc is None:
        requiredParentSiteType = iconsites.matingSiteType[requiredMatingSiteType]
        if requiredParentSiteType in (s.type for s in firstIc.sites.parentSites()):
            # There is only a single icon in placeList and it's a compatible type
            return firstIc
    # The list is not compatible, create an entry icon
    entryIc = entryicon.EntryIcon(window=firstIc.window)
    entryIc.appendPendingArgs(placeList)
    return entryIc

def appendToPlaceList(placeList, toAdd, needReorder):
    """Lexically merge a placement list, toAdd, to the end of an existing one, placeList,
    assuming that all of the intervening icons have been removed.  This is used for
    reconstructing an icon hierarchy following deletion, with the end goal of creating
    either a tree with a single icon at the root, or a series that can be merged in to a
    parent series or become a naked tuple at the top level.  Since reducing the list to a
    single icon or a series the goal, the call tries to merge everything that can be
    merged.  In particular, it tries to eliminate loose attributes and empty sites on
    the left or right of an operator.  The caller needs to supply a list (needReorder) to
    receive icons to be reexamined after reassembly for arithmetic reordering based on
    precedence."""
    if len(toAdd) == 0:
        return
    if len(placeList) == 0:
        placeList += toAdd
        return
    placeListEndsWithList = isinstance(placeList[-1], (list, tuple))
    toAddStartsWithList = isinstance(toAdd[0], (list, tuple))
    if placeListEndsWithList and toAddStartsWithList:
        # Both the end of placeList and the start of toAdd are series.  Just join them
        placeList[-1] += toAdd[0]
        placeList += toAdd[1:]
        return
    if placeListEndsWithList:
        lastPlaceListIc = placeList[-1][-1]
    else:
        lastPlaceListIc = placeList[-1]
    rightmostIc, rightmostSiteId = icon.rightmostSite(lastPlaceListIc)
    firstToAddIc = toAdd[0][0] if isinstance(toAdd[0], (list, tuple)) else toAdd[0]
    matingType = iconsites.matingSiteType[rightmostIc.typeOf(rightmostSiteId)]
    if isinstance(firstToAddIc, entryicon.EntryIcon) or matingType in \
            [s.type for s in firstToAddIc.sites.parentSites()]:
        # We can attach the left icon from toAdd to the right icon from placeList
        rightmostIc.replaceChild(firstToAddIc, rightmostSiteId)
        checkReorder(rightmostIc, needReorder)
        if toAddStartsWithList:
            toAdd[0] = placeList[-1]
            placeList[-1] = toAdd[0]
            placeList += toAdd[1:]
        else:
            placeList += toAdd[1:]
        return
    firstIcCoincSite = firstToAddIc.hasCoincidentSite()
    if firstIcCoincSite and \
            not firstToAddIc.childAt(firstToAddIc.sites.firstCursorSite()) and \
            icon.validateCompatibleChild(lastPlaceListIc, firstToAddIc, firstIcCoincSite):
        # There's an empty site on the left of the left icon added, combine
        firstToAddIc.replaceChild(lastPlaceListIc, firstIcCoincSite)
        checkReorder(firstToAddIc, needReorder)
        if placeListEndsWithList:  # and toAdd does not start with list, per above
            return
        placeList[-1] = toAdd[0]
        placeList += toAdd[1:]
        return
    else:
        placeList += toAdd

def checkReorder(ic, needReorder):
    """Deletion from expressions is done lexically, but the deletion operation itself is
    done blindly on the icon hierarchy, so when a deletion operation reorders an
    expression, it calls this to mark potentially affected icons to recheck the
    precedence relationships to see if the new lexical order needs to cause rearrangement
    of the hierarchy.  It marks them by adding the potentially affected icons to the list,
    needReorder."""
    if isinstance(ic, (opicons.UnaryOpIcon, opicons.BinOpIcon, opicons.IfExpIcon)):
        needReorder.append(ic)

def reorderMarkedExprs(topIcon, exprsNeedingReorder):
    """Reorder the hierarchy of arithmetic expressions below topIcon, whose relative
    precedences may have changed due to deletion of the icons around them.  The deletion
    code marks expressions that need to be checked by adding icons to the list passed as
    exprsNeedReorder.  The function reorders the icon hierarchy to match what it looks
    like (lexically), rather than what the hierarchy itself implies.  Even though the
    deletion code restarts this list for every top icon involved in deletion, we do a
    second check that the icon is within the hierarchy of topIcon.  This is done beaause
    the same routine is used for processing both the remaining icons in the expression
    and the new tree of deleted icons that is (optionally) assembled by removeIcons.
    Returns the (possibly replaced) top top icon of the statement."""
    reorderExprTops = set()
    for ic in exprsNeedingReorder:
        if ic.topLevelParent() == topIcon:
            reorderExprTops.add(reorderexpr.highestAffectedExpr(ic))
    modifiedTopIcon = topIcon
    for ic in reorderExprTops:
        newTopIc = reorderexpr.reorderArithExpr(ic, skipReplaceTop=True)
        if ic is topIcon and newTopIc is not ic:
            modifiedTopIcon = newTopIc
    return modifiedTopIcon

#... Move to OS-dependent module (once that's created)
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
def nudgeMouseCursor(x, y):
    cursorPos = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursorPos))
    cursorPos.x += x
    cursorPos.y += y
    ctypes.windll.user32.SetCursorPos(cursorPos.x, cursorPos.y)

if __name__ == '__main__':
    appData = App()
    appData.mainLoop()
