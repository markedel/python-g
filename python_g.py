# Copyright Mark Edel  All rights reserved
# Python-g main module
import copy
import io
import math
import tkinter as tk
import tkinter.filedialog
import ast
import os.path
import comn
import cursors
import iconsites
import icon
import iconlayout
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
import expredit
from PIL import Image, ImageDraw, ImageWin, ImageGrab, ImageEnhance
import time
import tkinter.messagebox
import ctypes
import reorderexpr
import contextlib
import sys
# import cProfile

WINDOW_BG_COLOR = (255, 255, 255)
#WINDOW_BG_COLOR = (128, 128, 128)
RECT_SELECT_COLOR = (128, 128, 255, 255)

DEFAULT_WINDOW_SIZE = (800, 800)

# Number of pixels mouse can move with button down before we consider it a drag.
# Experience shows that 2 pixels is too small and results in misinterpretation of around
# 1 out of 15 clicks.
DRAG_THRESHOLD = 4

# Tkinter event modifiers
SHIFT_MASK = 0x001
CTRL_MASK = 0x004
ALT_MASK = 0x20000
LEFT_MOUSE_MASK = 0x100
RIGHT_MOUSE_MASK = 0x300

DOUBLE_CLICK_TIME = 300

CURSOR_BLINK_RATE = 500

SNAP_DIST = 8

# Distance to search around icons to find appropriate cursor sites
SITE_SELECT_DIST = 8

# Extension to SITE_SELECT_DIST for empty sites to allow clicking anywhere in the
# highlighted area
EMPTY_SITE_EXT_DIST = 7

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

# Number of pixels of mouse movement to advance a structural drag target selection up one
# level in the icon hierarchy
TARGET_SELECT_STEP_DIST = 10

# Max. number of statements allowed in a single page.  Splitting sequences in to pages
# makes edits, scrolling, and finding icons within a region, more efficient.  It does
# so by segmenting the list of top-level icons that when a long file is edited,
# operations can be done just on the area of interest, without scanning the whole icon
# tree.  A larger value will raise the maximum file size that the program can handle
# without performance degrading.  A smaller value (up to a point) will improve
# performance for everything else.  At around 70 there a minor delay can be detected,
# but not objectionable.
PAGE_SPLIT_THRESHOLD = 100

# Maximum line width in characters for save-file and copy/paste text
DEFAULT_SAVE_FILE_MARGIN = 100
# Number of columns to indent in save-file and copy/paste text
DEFAULT_SAVE_FILE_TAB_SIZE = 4

WIN_TITLE_PREFIX = "Python-G - "

TYPING_ERR_COLOR = '#FFAAAA'
TYPING_ERR_HOLD_TIME = 5000

# How transparent (0.0=transparent - 1.0=opaque) to draw dragging icons.  0.25 is dark
# enough to read but light enough to be able to make out text underneath, which allows
# users to see icons highlighted for replacement.
DRAG_OVLY_OPACITY = 0.25

# anchorImage = comn.asciiToImage((
#  ".......6%%6.......",
#  ".......%..%.......",
#  "......8%..%8......",
#  ".......2%%2.......",
#  "........%%........",
#  "........%%........",
#  "....5%%%%%%%%5....",
#  "........%%........",
#  "........%%........",
#  "........%%........",
#  ".%7.....%%.....7%.",
#  ".%%7....%%....7%%.",
#  ".%%%5...%%...5%%%.",
#  "5%%6....%%....6%%5",
#  "8.%%....%%....%%.8",
#  "..8%%...%%...%%8..",
#  "...8%%%2%%2%%%8...",
#  ".....72%%%%%......",
#  "........oo........"))
# moduleAnchorSeqOutOffset = anchorImage.width//2, anchorImage.height-1
# MODULE_ANCHOR_X = 5
# MODULE_ANCHOR_Y = 1
anchorImage = comn.asciiToImage((
 "oooooooooo",
 "o%%%%%%%%o",
 "o%%%%%%%%o",
 "o%%%%%%%%o",
 "o5%%%%%%5o",
 ".o%%%%%%o.",
 ".o5%%%%5o.",
 "..o%%%%o..",
 "..o5%%5o..",
 "...o%%o...",
 "...o44o...",
 "...o%%o...",
 "...o%%o...",
 "....oo....",
))
moduleAnchorSeqOutOffset = anchorImage.width//2, anchorImage.height-2
MODULE_ANCHOR_X = 9
MODULE_ANCHOR_Y = 1

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
        outerFrame = tk.Frame(self.top)
        self.menubar = tk.Menu(outerFrame)
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
        menu.add_command(label="Split", command=self._splitCb, accelerator="Ctrl+T")
        menu.add_command(label="Join", command=self._joinCb, accelerator="Ctrl+J")

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
        panes = tk.PanedWindow(outerFrame, orient=tk.VERTICAL, sashwidth=4,
            width=width, height=height)

        iconFrame = tk.Frame(panes, background='white')
        self.imgFrame = tk.Frame(iconFrame, bg="", takefocus=True)
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
        self.top.bind("<Control-t>", self._splitCb)
        self.top.bind("<Control-j>", self._joinCb)
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
        self.top.bind("<KeyPress-Shift_L>", self._shiftPressCb)
        self.top.bind("<KeyPress-Shift_R>", self._shiftPressCb)
        self.top.bind("<KeyRelease-Shift_L>", self._shiftReleaseCb)
        self.top.bind("<KeyRelease-Shift_R>", self._shiftReleaseCb)
        self.imgFrame.grid(row=0, column=0, sticky=tk.NSEW)
        self.xScrollbar = tk.Scrollbar(iconFrame, orient=tk.HORIZONTAL,
            width=SCROLL_BAR_WIDTH, command=self._xScrollCb)
        self.xScrollbar.grid(row=1, column=0, sticky=tk.EW)
        self.yScrollbar = tk.Scrollbar(iconFrame,
            width=SCROLL_BAR_WIDTH, command=self._yScrollCb)
        self.yScrollbar.grid(row=0, column=2, sticky=tk.NS)
        self.scrollOrigin = 0, 0
        self.scrollExtent = 0, 0, width, height
        iconFrame.grid_rowconfigure(0, weight=1)
        iconFrame.grid_columnconfigure(0, weight=1)
        #iconFrame.pack(fill=tk.BOTH, expand=True) #... try removing
        panes.add(iconFrame, minsize=20, stretch='always')

        self.outputFrame = tk.Frame(panes)
        self.typingErrPane = tk.Label(self.outputFrame, text='', bg=TYPING_ERR_COLOR)
        self.outputPane = tk.Text(self.outputFrame, wrap=tk.WORD, height=1, takefocus=0)
        self.outputPane.bind("<ButtonRelease-1>", self._outputSelectCb)
        self.outputPane.config(state=tk.DISABLED)
        self.outputPane.grid(row=1, column=0, sticky=tk.NSEW)
        outputScrollbar = tk.Scrollbar(self.outputFrame,  width=SCROLL_BAR_WIDTH,
            command=self.outputPane.yview)
        outputScrollbar.grid(row=0, rowspan=2, column=1, sticky=tk.NS)
        self.outputPane.config(yscrollcommand=outputScrollbar.set)
        self.outputFrame.grid_columnconfigure(0, weight=1)
        self.outputFrame.grid_rowconfigure(1, weight=1)
        panes.add(self.outputFrame, minsize=0, stretch='never', sticky=tk.NSEW)
        panes.pack(fill=tk.BOTH, expand=1)
        outerFrame.pack(fill=tk.BOTH, expand=1)

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
        self.dragTagetModePtrOffset = None
        self.dragImageOffset = None
        self.dragImage = None
        self.snapped = None
        self.transparentDragimage = None
        self.lastDragImageRegion = None
        self.highlightedForReplace = set()
        self.inRectSelect = False
        self.lastRectSelect = None  # Note, in image coords (not content)
        self.inStmtSelect = False
        self.lastStmtHighlightRects = None
        self.rectSelectInitialStates = {}
        self.popupIcon = None
        self.typingErrCancelId = None

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
        # Create an icon to top the main module sequence.  Except for the seqOut site,
        # this will normally be invisible (above the top of the window).  Only when the
        # window content gets dragged above or left of (0,0) do we allow scrolling to
        # that region.  When that area does get exposed, the module sequence snap point
        # needs to be clearly visible.
        with self.pauseUndoRecording():
            self.modSeqIcon = ModuleAnchorIcon(self)
        page = Page(forModSeq=self.modSeqIcon)
        self.sequences.append(page)
        self.topIcons[self.modSeqIcon] = page
        self.cursor = cursors.Cursor(self, 'icon', ic=self.modSeqIcon, site='seqOut')

    def openFile(self, filename):
        """Open a .pyg or .py file in the window.  Uses file type to determine whether to
        parse as Python or Python-g.  Returns True if the file was successfully opened.
        Note that an empty file returns success."""
        print("reading file...", end="")
        with open(filename) as f:
            text = f.read()
        print("done")
        _base, ext = os.path.splitext(filename)
        seqs = filefmt.parseTextToIcons(text, self, source=filename,
            forImport=ext!=".pyg", asModule=True)
        if seqs is None:
            return False
        if len(seqs) == 0 or len(seqs) == 1 and len(seqs[0]) == 0:
            return True
        for seq in seqs:
            self.addTop(seq)
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
        """Return a list of the icons in the window that are currently selected.  Due to
        the odd method by which this is implemented (see below), performance will be
        enhanced somewhat if code that deletes all the icons from the selection, calls
        self.clearSelection() once it no longer needs to poll the selection."""
        # Selection was initially a property of icons, but that caused performance issues
        # because finding the current selection required traversing all icons.  Now the
        # selection is held in a set, but to support existing code which does not expect
        # to see deleted icons in the selection, it must be cleaned per-use (which will
        # make performance significantly WORSE when more than half of the icons in the
        # window are selected).  It is intended that there will be a formal mechanism for
        # removing icons, after which this code can be removed.
        self._pruneSelectedIcons()
        return list(self.selectedSet)

    def _pruneSelectedIcons(self):
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
        self.selectedSet.clear()

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
        popup.add_command(label="Split", command=self._splitCb, accelerator="Ctrl+T")
        popup.add_command(label="Join", command=self._joinCb, accelerator="Ctrl+J")

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
            parent=self.imgFrame, title="Open")
        print("tkinter filedialog returns", repr(filename))
        if filename is None or filename == '':
            return
        existingWindow = appData.findWindowWithFile(filename)
        if existingWindow is not None:
            reload = tkinter.messagebox.askokcancel(message="Reload %s" % filename,
                parent=self.imgFrame)
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
        if self.filename is None:
            initialDir = None
            initialFile = None
        else:
            initialDir, initialFile = os.path.split(self.filename)
        filename = tkinter.filedialog.asksaveasfilename(defaultextension=".pyg",
            filetypes=[("Python-g file", ".pyg"), ("Python file", ".py"),
            ("Python file", ".pyw")], initialfile=initialFile, initialdir=initialDir,
            parent=self.imgFrame, title="Save As")
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
                yMin = 0 if page.startIcon is self.modSeqIcon else min(page.topY, yMin)
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
        # If there's a cursor displayed somewhere, use it, otherwise, use selection.
        # Except in the case of typeovers, text is either fed directly to an accepting
        # widget using its addText method, or an entry icon is created at the requested
        # site and text is added to that.  The addText method for icons that support a
        # text cursor return a reject-reason string on failure and None on success.
        if self.cursor.type == "text":
            # If it's an active entry icon, feed it the character
            self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
            rejectReason = self.cursor.icon.addText(char)
        elif self.cursor.type == "icon":
            if char == ' ':
                # Quietly ignore extra space to eat unnecessary padding
                return
            origCursorIcon = self.cursor.icon
            origCursorSite = self.cursor.site
            self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
            self._insertEntryIconAtCursor(allowOnCursorOnly=char=='#')
            rejectReason = self.cursor.icon.addText(char)
            if rejectReason is not None:
                # Nothing was inserted and inserted entry icon was presumably deleted
                self.cursor.setToIconSite(origCursorIcon, origCursorSite)
        elif self.cursor.type == "window":
            x, y = self.cursor.pos
            entryIcon = entryicon.EntryIcon(window=self)
            y -= entryIcon.sites.output.yOffset
            entryIcon.rect = comn.offsetRect(entryIcon.rect, x, y)
            self.addTopSingle(entryIcon, newSeq=True)
            self.cursor.setToText(entryIcon, drawNew=False)
            rejectReason = entryIcon.addText(char)
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
            # ... This is extremely incomplete and wrong, as we can do much better than
            #     single-icon substitution that deletes all substructure.
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
                    replaceSite = iconParent.siteOf(replaceIcon)
                    if iconParent.typeOf(replaceSite) == "cprhIn":
                        ic, site = listicons.proxyForCprhSite(iconParent, replaceSite)
                        ic.replaceChild(entryIcon, site)
                        iconParent.replaceChild(None, replaceSite)
                    else:
                        iconParent.replaceChild(entryIcon, replaceSite)
                entryIcon.appendPendingArgs([pendingAttr])
                self.cursor.setToText(entryIcon, drawNew=False)
                rejectReason = entryIcon.addText(char)
                self.clearSelection()
            elif len(selectedIcons) == 0:
                rejectReason = "No cursor"
            else:
                # Either no icons were selected, or multiple icons were selected (so
                # we don't know what to replace).
                rejectReason = "Multiple selections (ambiguous replace)"
        if rejectReason is not None:
            # Text was rejected, beep and flash the error reason
            self.displayTypingError(rejectReason)
        else:
            # Text was accepted.  Note that no undo boundary is added here, as .addText
            # methods handle it to control grouping of operations.
            self.refreshDirty()

    def _insertEntryIconAtCursor(self, allowOnCursorOnly=False):
        # Note that location is set in the entry icon for the single case where it
        # becomes the beginning of a sequence.  All others are overwritten by layout
        self.requestRedraw(self.cursor.icon.topLevelParent().hierRect())
        entryIcon = entryicon.EntryIcon(window=self,
            location=self.cursor.icon.rect[:2])
        if self.cursor.siteType == "output":
            if isinstance(self.cursor.icon, commenticon.CommentIcon):
                commentIc = self.cursor.icon
                self.replaceTop(commentIc, entryIcon)
                commentIc.attachStmtComment(entryIcon)
            else:
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
        # This is a workaround for a weird issue with the text widget in the output pane.
        # Despite having takefocus set to False, as soon as this widget is clicked, not
        # only does it take focus, but it holds on and won't let go even when the icon
        # pane is explicitly clicked.  It would be nice to understand why.
        if evt.widget == self.outputPane:
            self.imgFrame.focus_set()

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

    def _shiftPressCb(self, evt):
        # If the shift key is pressed while dragging icons, we don't want the user to
        # have to wait for mouse movement to engage target selection
        if evt.state & SHIFT_MASK:
            # The shift key repeats, but luckily the KeyPress binding gives us the old
            # state, so we can filter the repeats from the key being held
            return
        if self.dragging and self.dragTagetModePtrOffset is None:
            # As noted above, Tkinter dispatches this event before changing the key mask
            # evt.state.  It *might* be safe to just clear the bit in evt, but I can't
            # guarantee that this won't affect the calling Tkinter code, so make a copy.
            evtCopy = copy.copy(evt)
            evtCopy.state = evt.state | SHIFT_MASK
            self._updateDrag(evtCopy)

    def _shiftReleaseCb(self, evt):
        # If the shift key is released while dragging icons, we want to disengage target
        # selection immediately (as opposed to on the next mouse movement, which is how
        # updateDrag is otherwise driven).
        if self.dragging and self.dragTagetModePtrOffset is not None:
            # Tkinter, for whatever reason, dispatches this event before changing the
            # key mask in evt.state.  While it might be safe to just clear the SHIFT_MASK
            # bit in evt, I can't guarantee that changing it won't affect the calling
            # Tkinter code, so instead, we pass _updateDrag a modified copy.
            evtCopy = copy.copy(evt)
            evtCopy.state = evt.state & ~SHIFT_MASK
            self._updateDrag(evtCopy)

    def _buttonPressCb(self, evt):
        if self.dragging:
            self._endDrag(evt)
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
            self._endDrag(evt)
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
            self.top.after(delay, self._delayedBtnUpActions, evt)
        else:
            # Do the button-release actions immediately, double-click wait has passed.
            self._delayedBtnUpActions(evt)

    def _outputSelectCb(self, evt):
        selection = self.outputPane.tag_ranges(tk.SEL)
        if len(selection) == 0:
            return
        # Copy the selected text to clipboard and clear the selection
        left, right = selection[:2]
        text = self.outputPane.get(left, right)
        self.top.clipboard_clear()
        self.top.clipboard_append(text, type='STRING')
        self.outputPane.tag_remove(tk.SEL, "0.0", tk.END)

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
        self.clearSelection()
        self.refreshDirty(addUndoBoundary=True)

    def _copyCb(self, evt=None):
        selectedIcons = self.selectedIcons()
        selectedRect = icon.containingRect(selectedIcons)
        if selectedRect is None:
            return
        with io.StringIO() as outStream:
            self.writeSaveFileText(outStream, selectedOnly=True, exportPython=False)
            pygText = outStream.getvalue()
        with io.StringIO() as outStream:
            self.writeSaveFileText(outStream, selectedOnly=True, exportPython=True)
            pyText = outStream.getvalue()
        self.top.clipboard_clear()
        self.top.clipboard_append(pygText, type='PYG')
        print(pygText)  # *******
        self.top.clipboard_append(pyText, type='STRING')

    def _pasteCb(self, evt=None):
        print('start icon creation', time.monotonic())
        if self.cursor.type == "typeover":
            self.displayTypingError("Can't paste into type-over region")
            return
        text = None
        if self.cursor.type == "text":
            # If the user is pasting in to the entry icon, string, or comment, use the
            # clipboard text, if possible.
            try:
                text = self.top.clipboard_get(type="STRING")
            except:
                text = None
            if text is not None:
                # Try a text insert, first.  If rejected, don't complain about it, yet,
                # because it could be code that the entry icon can't handle in text form,
                # but that the insertion code can handle in PYG form or after parsing
                # in plain Python form..
                self.requestRedraw(self.cursor.icon.hierRect())
                textRejectReason = self.cursor.icon.addText(text)
                if textRejectReason is None:
                    self.refreshDirty()  # Undo boundary added by addText
                    return
        # Look at what is on the clipboard and make the best possible conversion to icons
        try:
            iconString = self.top.clipboard_get(type="PYG")
        except:
            iconString = None
        if iconString is not None:
            pastedSeqs = filefmt.parseTextToIcons(iconString, self)
            if pastedSeqs is None:
                return  # Rejection reason was already presented in dialog-form
        else:
            # Couldn't get our icon data format.  Try string as python code
            if text is None:
                try:
                    text = self.top.clipboard_get(type="STRING")
                except:
                    text = None
            # Try to parse the string as Python code
            if text is not None:
                pastedSeqs = filefmt.parseTextToIcons(text, self)
                if pastedSeqs is None:
                    return  # Rejection reason was already presented in dialog-form
            else:
                # No text available in a form we can use.  Try for image.  Currently,
                # image only pastes as background image.  Eventually, needs to be some
                # way to choose image expression icon.
                clipImage = ImageGrab.grabclipboard()
                if clipImage is None:
                    self.displayTypingError("No usable data on the clipboard to paste")
                elif self.cursor.type != "window":
                    self.displayTypingError("(Currently) can only paste images as "
                        "background")
                else:
                    pastedIcon = icon.ImageIcon(clipImage, self, self.cursor.pos)
                    self.addTop(pastedIcon)
                    self.refreshDirty(addUndoBoundary=True)
                return
        if len(pastedSeqs) == 0:
            self.displayTypingError("Clipboard data was blank")
            return
        # There was something clipboard that could be converted to icon form.  Figure out
        # where to put it.  If there's a selection, replace it, otherwise paste it at
        # the current cursor position
        self._pruneSelectedIcons()
        if len(self.selectedSet) > 0:
            cursorIcon, cursorSite = self.replaceSelectedIcons(self.selectedSet,
                pastedSeqs)
            if cursorIcon is None and cursorSite is None:
                self.displayTypingError("Can't paste code containing top-level "
                    "statements into this context")
                return
        elif self.cursor.type is None:
            self.displayTypingError("No cursor or selection")
            return
        elif self.cursor.type == "window":
            cursorIcon, cursorSite = self.insertIconsFromSequences(None, None,
                pastedSeqs, self.cursor.pos)
        elif self.cursor.type == "text":
            # If we get here, the cursor is in a text editing icon, and a text insert was
            # already tried and failed, but we were able to parse the clipboard content
            # as code.  The target icon should be an entry icon, because we always
            # provide STRING content along with PYG, and the other text icons will digest
            # any text.  While we can't yet handle the general case of pasting code in
            # the middle of text, we can handle pasting after (if the text was parseable
            # with a delimiter, or, of course, if there's no text).  This is allowed for
            # two reasons: 1) to allow pastes to consume pending arguments, and 2) for
            # keystroke efficiency, since not doing so requires users to type an extra
            # delimiter before pasting, making us worse than a text editor in some cases.
            entryIc = self.cursor.icon
            if not isinstance(entryIc, entryicon.EntryIcon):
                print('Unexpected text destination in _pasteCb')
                return
            # We're being expected to paste at the cursor location, but unfortunately,
            # that general case is beyond our current capability.  All we can do is
            # paste before or after.
            if entryIc.cursorPos != len(entryIc.text):
                self.displayTypingError("Pasting code objects in to a text entry field "
                    "is only allowed at the rightmost cursor position.")
                return
            if len(entryIc.text) != 0 and not entryIc.canPlaceEntryText():
                self.displayTypingError("Can only paste code in text entry field after "
                    "valid (or empty) text")
                return
            # Instantiate the text in the entry icon by removing pending args and calling
            # focusOut (the pending arguments are right-of the pasted code, so we can
            # only append them after it). focusOut sets the cursor icon and site to the
            # right of whatever was entered.  This could be a window cursor if the text
            # was empty, but should not be a text cursor (at least I hope not)
            pendingArgs = entryIc.listPendingArgs()
            insertAtPos = None
            if len(entryIc.text) == 0:
                insertAtIcon = entryIc.attachedIcon()
                insertAtSite = entryIc.attachedSite()
                removedEntryIcon = False
            else:
                entryIc.popPendingArgs('all')
                if not entryIc.focusOut():
                    print('Failed to place entry text when canPlaceEntryText accepted')
                    entryIc.appendPendingArgs(pendingArgs)
                    return
                if self.cursor.type == 'text':
                    print("Paste in entry field failed to place text (got text cursor)")
                    return
                if self.cursor.type == 'window':
                    insertAtIcon = insertAtSite = None
                    insertAtPos = self.cursor.pos
                elif self.cursor.type == 'icon':
                    insertAtIcon = self.cursor.icon
                    insertAtSite = self.cursor.site
                else:
                    print("Paste in entry field failed to place text (no cursor)")
                    return
                removedEntryIcon = True
            # Insert the pasted code after the entry text
            cursorIcon, cursorSite = self.insertIconsFromSequences(insertAtIcon,
                insertAtSite, pastedSeqs, atPos = insertAtPos)
            if cursorIcon is None and cursorSite is None:
                self.displayTypingError("Can't paste code containing top-level "
                    "statements into this context")
                if len(pendingArgs) > 0:
                    entryIc.appendPendingArgs(pendingArgs)
                    self.insertIconsFromSequences(self.cursor.icon,
                        self.cursor.site, [[entryIc]])
                    self.cursor.setToText(entryIc)
                self.refreshDirty(addUndoBoundary=True)
                return
            # If there were pending args, use the original entry icon to place them.
            # The entry icon will be in one of two state: 1) still in place and still
            # holding its pending arguments (removedEntryIc==False), or 2) removed from
            # the tree and missing its pending arguments (removedEntryIc==True).  In the
            # second case, restore its pending args and insert it after the pasted code
            # before calling its remove() method to place its pending args.
            if len(pendingArgs) > 0:
                if removedEntryIcon:
                    entryIc.text = ''  # Just in case
                    entryIc.appendPendingArgs(pendingArgs)
                    self.insertIconsFromSequences(cursorIcon, cursorSite, [[entryIc]])
                self.cursor.setToText(entryIc)
                entryIc.remove()
            else:
                if not removedEntryIcon:  # Entry icon would have been empty with no args
                    entryIc.remove()
            self.refreshDirty(addUndoBoundary=True)
            return
        elif self.cursor.type == "icon":
            cursorIcon, cursorSite = self.insertIconsFromSequences(self.cursor.icon,
                self.cursor.site, pastedSeqs)
            if cursorIcon is None and cursorSite is None:
                self.displayTypingError("Can't paste code containing top-level "
                    "statements into this context")
                return
        print('start layout', time.monotonic())
        self.requestRedraw(self.layoutDirtyIcons(filterRedundantParens=False))
        print('finish layout', time.monotonic())
        if self.refreshRequests.get() is not None:
            print('start redraw/refresh', time.monotonic())
            self.refresh(self.refreshRequests.get(), redraw=True)
            print('end redraw/refresh', time.monotonic())
            self.refreshRequests.clear()
        self.undo.addBoundary()
        if cursorSite is None:
            self.cursor.setToText(cursorIcon)
        else:
            self.cursor.setToIconSite(cursorIcon, cursorSite)

    def _deleteCb(self, evt=None):
        selected = self.selectedIcons()
        if selected:
            self.removeIcons(selected)
            self.clearSelection()
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

    def _splitCb(self, evt):
        # This is inconsistent in its treatment of comments and entry icons (whose text
        # we actually split) and strings (which we treat as a unit and don't split), but
        # I'm not sure yet what splitting strings should actually do, because if it
        # breaks apart statements like the other two, it's not particularly useful, but
        # if it breaks strings into list elements, it's not consistent with everything
        # else. ... Also should do something with selections.
        if self.cursor.type == 'text':
            if isinstance(self.cursor.icon, commenticon.CommentIcon):
                cursorIc = self.cursor.icon
                if cursorIc.cursorPos >= len(cursorIc.string):
                    self.displayTypingError("Move cursor to desired location for split "
                        "(splitting on right side of comment does nothing)")
                elif cursorIc.cursorPos == 0 and cursorIc.attachedToStmt is None:
                    self.displayTypingError("Move cursor to desired location for split "
                        "(splitting on left side of comment does nothing)")
                else:
                    cursorIc.splitAtCursor()
                    self.refreshDirty(addUndoBoundary=True)
                return
            elif isinstance(self.cursor.icon, stringicon.StringIcon):
                cursorIc = self.cursor.icon
                if cursorIc.cursorPos < len(cursorIc.string) / 2:
                    parent = cursorIc.parent()
                    if parent is None:
                        splitAtIcon = cursorIc
                        splitAtSite = 'output'
                    else:
                        splitAtIcon = parent
                        splitAtSite = parent.siteOf(cursorIc)
                else:
                    splitAtIcon = cursorIc
                    splitAtSite = 'attrIcon'
            elif isinstance(self.cursor.icon, entryicon.EntryIcon):
                entryIc = self.cursor.icon
                if entryIc.cursorPos == 0:
                    # Split left of entry icon
                    splitAtIcon = self.cursor.icon.parent()
                    if splitAtIcon is None:
                        self.displayTypingError("Already at left of statement")
                        return
                    splitAtSite = splitAtIcon.siteOf(self.cursor.icon)
                elif entryIc.cursorPos == len(entryIc.text) and \
                        not entryIc.hasPendingArgs():
                    # Split right of entry icon
                    splitAtIcon, splitAtSite = icon.rightmostSite(entryIc)
                elif entryIc.cursorPos == len(entryIc.text):
                    # Split between entryIc text and pending args
                    if entryIc.parent() is not None:
                        failMsg = expredit.canSplitStmtAtSite(entryIc.attachedIcon(),
                            entryIc.attachedSite())
                        if failMsg is not None:
                            self.displayTypingError(failMsg)
                            return
                    # Split the statement at the site where the entry icon is, making it
                    # the start of stmt2, move its text into a new entry icon, and insert
                    # that at the site of the split, then try to place both entry icons.
                    newEntryIc = entryicon.EntryIcon(initialString=entryIc.text,
                        window = entryIc.window)
                    entryIc.text = ''
                    atIcon, atSite = entryIc.attachedIcon(), entryIc.attachedSite()
                    if atIcon is None:
                        icon.insertSeq(newEntryIc, entryIc, before=True)
                        self.addTop(newEntryIc)
                        stmt1 = entryIc
                    else:
                        stmt1, stmt2 = expredit.splitStmtAtSite(atIcon, atSite)
                        atIcon, atSite = icon.rightmostSite(stmt1)
                        cursorIc, _ = expredit.insertAtSite(atIcon, atSite, newEntryIc)
                        stmt1 = cursorIc.topLevelParent()
                    if newEntryIc.topLevelParent() in self.topIcons:
                        newEntryIc.focusOut(removeIfNotFocused=True)
                        stmt1 = self.cursor.icon.topLevelParent()
                    if entryIc.topLevelParent() in self.topIcons:
                        entryIc.focusOut(removeIfNotFocused=True)
                    self.cursor.setToIconSite(stmt1, 'seqOut')
                    self.refreshDirty(addUndoBoundary=True)
                    return
                else:
                    self.displayTypingError("Can't split entry text with split command")
                    return
        elif self.cursor.type == 'icon':
            splitAtIcon = self.cursor.icon
            splitAtSite = self.cursor.site
        else:
            self.displayTypingError("Place the cursor where you want to split")
            return
        # If the cursor is at the right of the statement, check if there's a statement
        # comment that the user might be trying to split off.
        stmtIcon = self.cursor.icon.topLevelParent()
        rightmostIc, rightmostSite = icon.rightmostSite(stmtIcon)
        if splitAtIcon is rightmostIc and splitAtSite == rightmostSite:
            stmtComment = stmtIcon.hasStmtComment()
            if stmtComment is not None:
                self.requestRedraw(stmtComment.hierRect())
                stmtComment.detachStmtComment()
                icon.insertSeq(stmtComment, stmtIcon)
                self.addTop(stmtComment)
                self.cursor.setToIconSite(stmtIcon, 'seqOut')
                self.refreshDirty(addUndoBoundary=True)
                return
        failMsg = expredit.canSplitStmtAtSite(splitAtIcon, splitAtSite)
        if failMsg is not None:
            self.displayTypingError(failMsg)
            return
        # Split the statement
        self.requestRedraw(stmtIcon.hierRect())
        stmt1, stmt2 = expredit.splitStmtAtSite(splitAtIcon, splitAtSite)
        # Place the cursor on the seqOut site of the first stmt, handling the dumb case
        # where stmt1 would get substituted when it's the entry icon holding the cursor.
        if self.cursor.type == 'text' and self.cursor.icon is stmt1:
            self.cursor.icon.focusOut()
            stmt1 = self.cursor.icon.topLevelParent()
        self.cursor.setToIconSite(stmt1, 'seqOut')
        # If the new statement (stmt2) has an entry icon on the left, it may now be
        # possible to remove it.
        leftIc = stmt2
        while leftIc is not None:
            if isinstance(leftIc, entryicon.EntryIcon) and \
                    leftIc.topLevelParent() in self.topIcons:
                leftIc.focusOut(removeIfNotFocused=True)
                break
            coincSite = leftIc.hasCoincidentSite()
            if coincSite is None:
                break
            leftIc = leftIc.childAt(coincSite)
        self.refreshDirty(addUndoBoundary=True)

    def _joinCb(self, evt):
        #... this should probably do something with selections
        failMsg = "Place the cursor between the statements you want to join"
        if self.cursor.type == 'text':
            if isinstance(self.cursor.icon, commenticon.CommentIcon):
                cursorIc = self.cursor.icon
                if cursorIc.cursorPos == 0 and  cursorIc.attachedToStmt is None and \
                        cursorIc.prevInSeq() is not None and \
                        (isinstance(cursorIc.prevInSeq(), commenticon.CommentIcon) or
                         cursorIc.prevInSeq().hasStmtComment()):
                    topStmtIcon = cursorIc.prevInSeq()
                    joinedStmtTopIcon = cursorIc
                elif cursorIc.cursorPos == len(cursorIc.string):
                    if cursorIc.attachedToStmt is None:
                        topStmtIcon = cursorIc
                    else:
                        topStmtIcon = cursorIc.attachedToStmt
                    joinedStmtTopIcon = topStmtIcon.nextInSeq()
                    if joinedStmtTopIcon is None:
                        self.displayTypingError(failMsg)
                        return
                    if not isinstance(joinedStmtTopIcon, (commenticon.CommentIcon,
                            commenticon.VerticalBlankIcon)):
                        self.displayTypingError("Can't join code to end of comment")
                        return
                else:
                    self.displayTypingError(failMsg)
                    return
            else:  # Both entry icon and string icon
                textIc = self.cursor.icon
                parent = textIc.parent()
                if textIc.cursorPos == 0 and (parent is None or
                        expredit.isLeftmostSite(parent, parent.siteOf(textIc))):
                    # Join left of entry icon (with previous statement)
                    joinedStmtTopIcon = textIc.topLevelParent()
                    topStmtIcon = joinedStmtTopIcon.prevInSeq()
                    if topStmtIcon is None:
                        self.displayTypingError(failMsg)
                        return
                else:
                    # Join with next statement
                    topStmtIcon = textIc.topLevelParent()
                    joinedStmtTopIcon = topStmtIcon.nextInSeq()
                    if joinedStmtTopIcon is None:
                        self.displayTypingError(failMsg)
                        return
        elif self.cursor.type == "icon":
            cursorTopIcon = self.cursor.icon.topLevelParent()
            if self.cursor.site == 'seqIn':
                topStmtIcon = cursorTopIcon.prevInSeq()
            elif self.cursor.site == 'seqOut':
                topStmtIcon = cursorTopIcon
            elif self.cursor.site == 'prefixInsert':
                topStmtIcon = cursorTopIcon.prevInSeq()
            elif expredit.isLeftmostSite(self.cursor.icon, self.cursor.site):
                topStmtIcon = cursorTopIcon.prevInSeq()
            else:
                topStmtIcon = cursorTopIcon
            if topStmtIcon is None:
                self.displayTypingError(failMsg)
                return
            joinedStmtTopIcon = topStmtIcon.nextInSeq()
            if joinedStmtTopIcon is None:
                self.displayTypingError(failMsg)
                return
        else:
            self.displayTypingError(failMsg)
            return
        if isinstance(topStmtIcon, commenticon.CommentIcon) and \
                not isinstance(joinedStmtTopIcon, (commenticon.CommentIcon,
                commenticon.VerticalBlankIcon)):
            self.displayTypingError("Can't join code to right of comment")
            return
        self.requestRedraw(topStmtIcon.hierRect(), filterRedundantParens=True)
        self.requestRedraw(joinedStmtTopIcon.hierRect())
        cursorIcon, cursorSite = expredit.joinStmts(topStmtIcon)
        if cursorIcon is None and cursorSite is None:
            self.displayTypingError("Statement being joined on the right is a top-"
                "level statement that can't be embedded in other code.")
            return
        elif cursorSite is None:
            self.cursor.setToText(cursorIcon)
        else:
            self.cursor.setToIconSite(cursorIcon, cursorSite)
        self.refreshDirty(addUndoBoundary=True)

    def _backspaceCb(self, evt=None):
        if self.cursor.type == "text":
            self.cursor.icon.backspaceInText(evt)
            self.refreshDirty(addUndoBoundary=False)
        else:
            selectedIcons = self.selectedIcons()
            if len(selectedIcons) > 0:
                self.removeIcons(selectedIcons)
                self.clearSelection()
            elif self.cursor.type == "icon":
                if self.cursor.siteType in ('seqIn', 'seqOut'):
                    cursorIc = self.cursor.icon
                    if self.cursor.siteType == 'seqIn' and cursorIc.prevInSeq(
                            includeModuleAnchor=True):
                        cursorIc = cursorIc.prevInSeq(includeModuleAnchor=True)
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
            self.cursor.icon.processEnterKey()
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
            blockOwnerIcon = blockStartIcon.prevInSeq()
            if blockOwnerIcon is not None:
                topIcon = blockOwnerIcon.blockEnd
        self.cursor.setToIconSite(topIcon, 'seqOut')
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
        subsIcs = {self.buttonDownIcon:None}
        draggingSequences = self.removeIcons(icons, assembleDeleted=True,
            watchSubs=subsIcs)
        if subsIcs[self.buttonDownIcon] is not None:
            self.buttonDownIcon = subsIcs[self.buttonDownIcon]
        # For icons that depend on context to distinguish identical text syntax,
        # (currently only for/if comprehension fields vs compatible for/if statements),
        # choose the non-contextual representation for dragging.
        for i in range(len(draggingSequences)):
            seq = draggingSequences[i]
            if len(seq) != 1:
                # Apply to single icons only, not sequences
                continue
            ic = seq[0]
            subsIc = listicons.subsCanonicalInterchangeIcon(ic)
            if subsIc is not None:
                draggingSequences[i] = [subsIc, subsIc.blockEnd]
                if ic is self.buttonDownIcon:
                    self.buttonDownIcon = subsIc
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
        self.dragging = draggingSequences
        # Recalculate layouts for dirty icons remaining in the window and those that will
        # be dragged, and refresh the whole display with icon outlines turned on.
        self.layoutDirtyIcons()
        self.refresh(redraw=True, showOutlines=True)
        self.refreshRequests.clear()
        self.layoutDirtyIcons(topDraggingIcons, filterRedundantParens=False)
        # For top performance, make a separate image containing the moving icons against
        # a transparent background, which can be redrawn with imaging calls, only.
        moveRegion = comn.AccumRects()
        for ic in topDraggingIcons:
            moveRegion.add(ic.hierRect())
        el, et, er, eb = moveRegion.get()
        self.dragImageOffset = el - self.buttonDownLoc[0], et - self.buttonDownLoc[1]
        self.dragImage = Image.new('RGBA', (er - el, eb - et), color=(0, 0, 0, 0))
        self.lastDragImageRegion = None
        for topIc in topDraggingIcons:
            for ic in topIc.traverse(inclStmtComment=True):
                ic.rect = comn.offsetRect(ic.rect, -el, -et)
                ic.draw(self.dragImage, style=icon.STYLE_OUTLINE)
        for ic in topDraggingIcons:
            icon.drawSeqRule(ic, image=self.dragImage)
        # Make an additional transparent copy of the drag image to use when snapped to a
        # replacement site
        alphaImage = self.dragImage.getchannel('A')
        enhancer = ImageEnhance.Brightness(alphaImage)
        alphaImg = enhancer.enhance(DRAG_OVLY_OPACITY)
        self.transparentDragimage = self.dragImage.copy()
        self.transparentDragimage.putalpha(alphaImg)
        # Fine-tune the positioning of the drag image based on the specific part of the
        # icon that the user dragged (for example, a right paren)
        if btnDownIcPartPos is not None:
            newPartPos = icon.addPoints(icon.addPoints(self.buttonDownIcon.rect[:2],
                self.buttonDownIcon.offsetOfPart(self.buttonDownIcPart)), (el, et))
            if newPartPos != btnDownIcPartPos:
                newPartOffset = icon.subtractPoints(btnDownIcPartPos, newPartPos)
                self.dragImageOffset = icon.addPoints(self.dragImageOffset, newPartOffset)
        # Construct a master snap list for all mating sites between stationary and
        # dragged icons.  Earlier versions of this code carefully paired free outputs
        # and seqInsert sites so the user could drag on a selection containing disjoint
        # icons and have any one of them snap on to corresponding stationary sites.  This
        # was unnecessary and counter productive, as the primary use-case for multi-
        # sequence dragging is moving groups of icons, where any snapping is probably
        # unintended and undesirable.  Now we just choose a single attachment site based
        # on the clicked icon.
        draggingOutputs = []
        draggingSeqInserts = []
        draggingAttrOuts = []
        draggingCprhOuts = []
        draggingConditionals = []
        dragIcon = self.buttonDownIcon.topLevelParent()
        dragIcon = icon.findSeqStart(dragIcon)
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
        draggingComment = isinstance(dragIcon, commenticon.CommentIcon)
        # The code has gone back and forth between supporting dedicated sites for list-
        # style insert ('insertInput' type) and having a single insert site with modifier
        # keys to disambiguate list insert from append/prepend.  Having just one type of
        # insert site would make the sites less crowded, and could have a fairly easy to
        # understand default behavior: if there is a matching open site then concatenate,
        # otherwise add as list (if on series site), and use the shift key on drop to
        # switch to the non-default option.  The current method trades higher required
        # mouse precision, for less cognitive load on the user.
        for winIcon in self.findIconsInRegion(order='pick', inclModSeqIcon=True):
            snapLists = winIcon.snapLists()
            if draggingComment:
                # Allow comments to snap to all input types (for insert), but not to
                # replace sites (except for whole-statement)
                for snapType in ('input', 'attrIn', 'cprhIn', 'replaceStmt'):
                    for ic, pos, name in snapLists.get(snapType, []):
                        stationaryInputs.append((pos, 0, ic, snapType, name, None))
            else:
                for snapType in ('input', 'attrIn', 'cprhIn', 'insertInput',
                        'replaceExprIc', 'replaceAttrIc', 'replaceCprhIc',
                        'replaceStmtIc', 'replaceStmt'):
                    for ic, pos, name in snapLists.get(snapType, []):
                        stationaryInputs.append((pos, 0, ic, snapType, name, None))
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
                    icon.BlockEnd, ModuleAnchorIcon)):
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
                if sSiteType in ('input', 'insertInput', 'seqIn', 'seqOut',
                        'replaceExprIc', 'replaceStmtIc', 'replaceStmt'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingAttrOuts:
                if sSiteType in ('attrIn', 'replaceAttrIc'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingCprhOuts:
                if sSiteType in ('cprhIn', 'replaceCprhIc'):
                    if sTest is None or sTest(siteData[1], siteData[2]):
                        matingSites.append(siteData)
            for siteData in draggingSeqInserts:
                if sSiteType in ('seqIn', 'seqOut', 'replaceStmtIc', 'replaceStmt',
                        'replaceCprhIc'):
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
        if self.dragTagetModePtrOffset is not None and not evt.state & SHIFT_MASK:
            # The user has released the shift key: cancel target selection and resume
            # normal dragging
            self.dragTagetModePtrOffset = None
        # If the drag results in mating sites being within snapping distance, change the
        # drag position to mate them exactly (snap them together)
        btnX, btnY = self.imageToContentCoord(evt.x, evt.y)
        if self.dragTagetModePtrOffset is not None:
            # If we're in drag-target selection mode, allow the drag image to move, even
            # though we're technically snapped to the highlighted site
            snappedX = self.dragImageOffset[0] + btnX
            snappedY = self.dragImageOffset[1] + btnY
        else:
            x = snappedX = self.dragImageOffset[0] + btnX
            y = snappedY = self.dragImageOffset[1] + btnY
            wasSnapped = self.snapped
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
            # Commented out code below is useful for debugging snapping
            # if not wasSnapped and self.snapped:
            #     sIcon, movIcon, siteType, siteName = self.snapped
            #     print("snapped %s to %s type %s name %s" % (movIcon.dumpName(),
            #         sIcon.dumpName(), siteType, siteName))
            # If the user has pressed the shift key while the dragging icons are snapped
            # to a replace site, switch to drag target selection mode
            if evt.state & SHIFT_MASK and self.snapped is not None:
                sIcon, movIcon, siteType, siteName = self.snapped
                if siteType in ('replaceExprIc', 'replaceAttrIc', 'replaceCprhIc',
                        'replaceStmtIc', 'replaceStmt'):
                    sIconSnapList = sIcon.snapLists()
                    snapSiteX, snapSiteY = sIconSnapList[siteType][0][1]
                    snapBtnX = snappedX - self.dragImageOffset[0]
                    snapBtnY = snappedY - self.dragImageOffset[1]
                    self.dragTagetModePtrOffset = snapSiteX-snapBtnX, snapSiteY-snapBtnY
        # Erase the old drag image
        width = self.dragImage.width
        height = self.dragImage.height
        dragImageRegion = (snappedX, snappedY, snappedX+width, snappedY+height)
        if self.lastDragImageRegion is not None:
            for r in exposedRegions(self.lastDragImageRegion, dragImageRegion):
                self.refresh(r, redraw=False)
        # Manage highlighting of icons showing pending replacements
        useTransparentDragImage = False
        if self.dragTagetModePtrOffset is not None:
            sIcon, movIcon, siteType, siteName = self.snapped
            btnToSiteX, btnToSiteY = self.dragTagetModePtrOffset
            pointerX = btnX + btnToSiteX
            pointerY = btnY + btnToSiteY
            snapSiteX, snapSiteY = sIcon.snapLists()[siteType][0][1]
            if siteType == 'replaceStmt':
                highlightedIcons = expredit.extendDragTargetByStmt(sIcon, pointerX,
                    pointerY)
            elif pointerX <= snapSiteX and pointerY <= snapSiteY:
                step = int(math.sqrt((snapSiteX - pointerX)**2 + \
                    (snapSiteY - pointerY)**2) / TARGET_SELECT_STEP_DIST)
                topReplaceIc = expredit.extendDefaultReplaceSite(movIcon, sIcon)
                highlightedIcons = expredit.extendDragTargetStructural(topReplaceIc, step)
                useTransparentDragImage = True
            else:
                highlightedIcons = expredit.extendDragTargetLexical(sIcon, pointerX,
                    pointerY)
        else:
            snappedToReplaceSite = self.snapped is not None and (self.snapped[2] in
                ('replaceExprIc', 'replaceAttrIc', 'replaceCprhIc', 'replaceStmtIc',
                 'replaceStmt') or self.snapped[3] == 'replaceComment')
            if snappedToReplaceSite:
                sIcon, movIcon, siteType, siteName = self.snapped
                topReplaceIc = expredit.extendDefaultReplaceSite(movIcon, sIcon)
                highlightedIcons = set(topReplaceIc.traverse(inclStmtComment=
                    self.snapped[2] == 'replaceStmt'))
                useTransparentDragImage = True
            else:
                highlightedIcons = set()
        if self.highlightedForReplace != highlightedIcons:
            redrawRegion = comn.AccumRects()
            for ic in self.highlightedForReplace | highlightedIcons:
                redrawRegion.add(ic.rect)
            self.highlightedForReplace = highlightedIcons
            self.refresh(redrawRegion.get(), redraw=True, showOutlines=True)
        # Draw the image of the moving icons in their new locations directly to the
        # display (leaving self.image clean).  This makes dragging fast by eliminating
        # individual icon drawing while the user is dragging.
        crop = self.contentToImageRect(dragImageRegion)
        dragImage = self.image.crop(crop)
        if useTransparentDragImage:
            dragImage.paste(self.transparentDragimage, mask=self.transparentDragimage)
        else:
            dragImage.paste(self.dragImage, mask=self.dragImage)
        self.drawImage(dragImage, self.contentToImageCoord(snappedX, snappedY))
        self.lastDragImageRegion = dragImageRegion

    def _endDrag(self, evt):
        topDraggingIcons = [ic for seq in self.dragging for ic in seq]
        if self.snapped is not None:
            # The drag ended in a snap.  Attach or replace existing icons at the site
            statIcon, movIcon, siteType, siteName = self.snapped
            if siteName == "stmtComment":
                rightmostIc, rightmostSite = icon.rightmostSite(statIcon)
                self.insertIconsFromSequences(rightmostIc, rightmostSite, self.dragging)
            elif siteType == "input":
                if evt.state & SHIFT_MASK:
                    self.insertIconsFromSequences(statIcon, siteName, self.dragging,
                        asSeries=True)
                else:
                    self.insertIconsFromSequences(statIcon, siteName, self.dragging)
            elif siteType == "attrIn":
                self.insertIconsFromSequences(statIcon, siteName, self.dragging)
            elif siteType == "insertInput":
                self.insertIconsFromSequences(statIcon, siteName, self.dragging,
                    asSeries=True)
            elif siteType == "cprhIn":
                self.insertIconsFromSequences(statIcon, siteName, self.dragging)
            elif siteName in ('replaceExprIc', 'replaceAttrIc', 'replaceCprhIc',
                    'replaceStmtIc', 'replaceStmt', 'replaceComment'):
                self.replaceSelectedIcons(self.highlightedForReplace, self.dragging)
            elif siteType == 'seqOut':
                self.insertIconsFromSequences(statIcon, siteName, self.dragging)
            elif siteType == 'seqIn' and siteName == 'prefixInsert':
                # This is the insert site of a line comment, used to convert it to a
                # statement comment
                self.insertIconsFromSequences(statIcon, siteName, self.dragging)
            elif siteType == 'seqIn':
                self.insertIconsFromSequences(statIcon, siteName, self.dragging)
        else:
            # Not snapped.  Place on window background.  Dropping an entry icon on the
            # top level outside of a sequence may allow it to be removed, since
            # placeholders are not needed
            l, t, r, b = self.lastDragImageRegion
            for topIc in topDraggingIcons:
                for ic in topIc.traverse(inclStmtComment=True):
                    ic.rect = comn.offsetRect(ic.rect, l, t)
            unsequencedEntryIcons = [ic for ic in topDraggingIcons \
                if isinstance(ic, entryicon.EntryIcon) and ic.parent() is None and \
                ic.childAt('seqIn') is None and ic.childAt('seqOut') is None and \
                ic.text == '']
            for ic in unsequencedEntryIcons:
                pendingArgs = ic.listPendingArgs()
                nonEmptyArgs = list(icon.placementListIter(pendingArgs,
                    includeEmptySeriesSites=False))
                if len(nonEmptyArgs) == 0:
                    topDraggingIcons.remove(ic)
                if len(nonEmptyArgs) == 1:
                    topDraggingIcons.remove(ic)
                    ic.popPendingArgs("all")
                    arg = nonEmptyArgs[0][0]
                    subsIc = listicons.subsCanonicalInterchangeIcon(arg)
                    if subsIc is not None:
                        filefmt.moveIconToPos(subsIc, ic.pos())
                        topDraggingIcons.append(subsIc)
                        topDraggingIcons.append(subsIc.blockEnd)
                        arg = subsIc
                    else:
                        topDraggingIcons.append(arg)
                    if self.cursor.type in ('icon', 'text') and self.cursor.icon is ic:
                        self.cursor.setToIconSite(arg, cursors.topSite(arg))
            self.addTop(topDraggingIcons)
        self.dragging = None
        self.highlightedForReplace = set()
        self.dragTagetModePtrOffset = None
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
        self.dragTagetModePtrOffset = None
        if len(self.highlightedForReplace) > 0:
            redrawRegion = comn.AccumRects()
            for ic in self.highlightedForReplace:
                redrawRegion.add(ic.rect)
            self.refresh(redrawRegion.get(), redraw=True, showOutlines=True)
            self.highlightedForReplace = set()

    def _startRectSelect(self, evt):
        self.rectSelectCursor = self.cursor.saveState()
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
        # It's unclear whether we actually want to remove the cursor after a rectangular
        # selection, but we definitely don't want to if no selection was made.  Using
        # selectedSet rather than selectedIcons() might be a questionable choice as it
        # may be wrong, but it's also much cheaper.
        if len(self.selectedSet) == 0:
            self.cursor.restoreState(self.rectSelectCursor)
            self.cursor.draw()

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
                exprAst = iconToExecute.createAst()
            except icon.IconExecException as excep:
                self._handleExecErr(excep)
                return False
            if exprAst is None:
                return True
            try:
                astToExecute = ast.Expression(exprAst)
            except icon.IconExecException as excep:
                self._handleExecErr(excep)
                return False
        else:
            # Create ast for exec (may be a sequence)
            execType = 'exec'
            iconToExecute = icon.findSeqStart(iconToExecute)
            seqIcons = icon.traverseSeq(iconToExecute, skipInnerBlocks=True)
            body = []
            for ic in seqIcons:
                try:
                    stmtAst = icon.createStmtAst(ic)
                except icon.IconExecException as excep:
                    self._handleExecErr(excep)
                    return False
                if stmtAst is not None:  # Comments and decorators create no ASTs
                    body.append(stmtAst)
            astToExecute = ast.Module(body, type_ignores=[])
        #print(ast.dump(astToExecute, include_attributes=True))
        # Compile the AST
        try:
            code = compile(astToExecute, self.winName, execType)
        except Exception as excep:
            self._handleExecErr(excep, iconToExecute)
            return False
        # Execute the compiled AST, providing variable __windowExecContext__ for
        # mutable icons to use to pass their live data into the compiled code.
        try:
            with self.streamToOutputPane():
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
            with self.streamToOutputPane():
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
        elif isinstance(obj, (int, float)) or obj is None:
            ic = nameicons.NumericIcon(obj, window=self)
        elif isinstance(obj, str):
            ic = stringicon.StringIcon(initReprStr=repr(obj), window=self)
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
            message = str(excep)
        elif isinstance(excep, SyntaxError):
            excepIcon = self.iconIds[excep.lineno]
            message = 'Syntax Error: ' + excep.msg
        else:
            message = excep.__class__.__name__ + ': ' + str(excep)
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
        tkinter.messagebox.showerror("Error Executing", message=message,
            parent=self.imgFrame)
        for ic in excepIcon.traverse():
            ic.draw(clip=iconRect)
        self.refresh(iconRect, redraw=False)

    def _showSyntaxErr(self, _evt=None):
        errHighlight = self.popupIcon.errHighlight
        if errHighlight is not None:
            tkinter.messagebox.showerror("Syntax Error", message=errHighlight.text,
                parent=self.imgFrame)

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
        # ... I'm leaving the commented-out code below as a reminder that I removed it
        #     because it's clearly wrong for comments and strings, but worried that I've
        #     forgotten about cases where the entry icon needs to preserve a selection.
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

    def displayTypingError(self, errText, quiet=False):
        if not quiet:
            cursors.beep()
        self.typingErrPane.config(text=errText)
        self.typingErrPane.grid(row=0, column=0, sticky=tk.EW)
        if self.typingErrCancelId is not None:
            self.top.after_cancel(self.typingErrCancelId)
        self.typingErrCancelId = self.top.after(TYPING_ERR_HOLD_TIME,
            self._closeTypingErrPane)

    def _closeTypingErrPane(self):
        self.typingErrPane.config(text='')
        self.typingErrPane.grid_forget()
        self.typingErrCancelId = None

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
        for ic in self.findIconsInRegion(region, inclSeqRules=True, inclModSeqIcon=True):
            ic.draw(clip=region, style=drawStyle)
            # Looks better without connectors, but not willing to remove permanently, yet:
            # if region is None or icon.seqConnectorTouches(topIcon, region):
            #     icon.drawSeqSiteConnection(topIcon, clip=region)
            if icon.seqRuleTouches(ic, region):
                icon.drawSeqRule(ic, clip=region)

    def _dumpCb(self, evt=None):
        for seqStartPage in self.sequences:
            if seqStartPage.startIcon is self.modSeqIcon:
                print('Module Sequence')
            else:
                print(f'@{seqStartPage.startIcon.pos()}')
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

    def findIconsInRegion(self, rect=None, inclSeqRules=False, order='draw',
            inclModSeqIcon=False):
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
                    for topIc in page.traverseSeq(inclModSeqIcon=inclModSeqIcon):
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
                blockStart = icon.findBlockOwner(blockStart)
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

    def removeIcons(self, icons, assembleDeleted=False, watchSubs=None,
            preserveSite=None):
        """Remove icons from window icon list, request redraw of affected areas of the
        display (does not perform redraw, call refreshDirty() to draw marked changes).
        If assembleDeleted is True, applies the same reassembly techniques to the removed
        icon structures as it does to the remaining ones and returns a list per sequence
        of the top-level deleted icons, in sequence-order.  watchSubs can be set to a
        dictionary whose keys are icons for which the caller wants to be notified of
        substitutions (for example, removeIcons might convert a paren-icon to a tuple so
        that it can merge a list that got promoted because its brackets were deleted).
        When the method returns, any icons specified in watchSubs will be mapped to the
        icon that replaced them.  preserveSite can be set to a tuple to save it from
        conversion to paren or removal (in the case of a naked tuple) when down to a
        single argument (used in replacement, which is implemented as removal followed by
        insert)."""
        if len(icons) == 0:
            return []
        # If parameter 'icons' is not already a set, turn it into one to more efficiently
        # determines if an icon is on the deleted list.
        if isinstance(icons, set):
            deletedSet = icons
        else:
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
            prevIc = ic.prevInSeq(includeModuleAnchor=True)
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
        # Before doing the deletion, waste some cycles to scan blocks under removed
        # block-owning and pseudo-block-owning icons for icons whose error highlighting
        # might change as a result of their removal.  Mark them dirty so error
        # highlighting will be called on them.
        for ic in topIcons:
            blockicons.markDependentStmts(ic)
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
            stmtComment = topIcon.hasStmtComment()
            remainingIcons, assembledDeletions, removedTopIcon = \
                expredit.splitDeletedIcons(topIcon, deletedSet, assembleDeleted,
                    needReorder, watchSubs, preserveSite)
            if remainingIcons is None:
                newTopIcon = topIcon
            else:
                forSeq = topIcon.childAt('seqIn') or topIcon.childAt('seqOut')
                newTopIcon = expredit.placeListToTopLevelIcon(remainingIcons, forSeq,
                    watchSubs)
            newTopIcon = expredit.reorderMarkedExprs(newTopIcon, needReorder,
                watchSubs=watchSubs)
            if assembleDeleted:
                if assembledDeletions is None:
                    addToDelSeq = topIcon
                    addBlockEnd = False
                else:
                    addToDelSeq = expredit.placeListToTopLevelIcon(assembledDeletions,
                        False, watchSubs)
                    addBlockEnd = addToDelSeq is not None and hasattr(addToDelSeq,
                        'blockEnd')  # a for/if from a cprh subs
                addToDelSeq = expredit.reorderMarkedExprs(addToDelSeq, needReorder,
                    watchSubs=watchSubs)
                if addToDelSeq is not None:
                    deletedSeqList[iconToSeqId[topIcon]].append(addToDelSeq)
                    if addBlockEnd:
                        deletedSeqList[iconToSeqId[topIcon]].append(addToDelSeq.blockEnd)
                if stmtComment in deletedSet and addToDelSeq is not topIcon:
                    stmtComment.detachStmtComment()
                    if addToDelSeq is None:
                        deletedSeqList[iconToSeqId[topIcon]].append(stmtComment)
                    else:
                        stmtComment.attachStmtComment(addToDelSeq)
            else:
                if stmtComment is not None and stmtComment in deletedSet:
                    stmtComment.detachStmtComment()
            if newTopIcon is None:
                if stmtComment is not None and stmtComment not in deletedSet:
                    stmtComment = topIcon.stmtComment
                    stmtComment.detachStmtComment()
                    if hasattr(topIcon, 'blockEnd'):
                        ignoreRemovedBlockEnds.add(topIcon.blockEnd)
                    self.replaceTop(topIcon, stmtComment, alreadyRemoved=removedTopIcon)
                else:
                    topDeletedIcons.add(topIcon)
            elif newTopIcon is not topIcon:
                if stmtComment is not None and stmtComment not in deletedSet:
                    stmtComment = topIcon.stmtComment
                    stmtComment.detachStmtComment()
                    stmtComment.attachStmtComment(newTopIcon)
                if hasattr(topIcon, 'blockEnd'):
                    ignoreRemovedBlockEnds.add(topIcon.blockEnd)
                self.replaceTop(topIcon, newTopIcon, alreadyRemoved=removedTopIcon)
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
            prevIcon = topIcon.prevInSeq(includeModuleAnchor=True)
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
                            entryIc.selectIfFirstArgSelected()
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

    def replaceSelectedIcons(self, selectedSet, insertedSequences):
        """Remove the icons listed in selectDict from the window and replace them with
        those listed in insertedSequences.  Both the removed and inserted icons can be
        disjoint, in which case, replace the topmost (and leftmost if there's a tie)
        contiguous group of icons with icons in insertedSequences, and delete the
        remaining selected icons.  If insertedSequences contains statement-only icons and
        the first contiguous selection happens to be within code that cannot be broken
        apart to insert such statements, the replacement will not be performed and the
        function will return None, None.  On success, the function will return the icon
        and site on which to place the cursor.  Note that while the window keeps track of
        selected icons using a set (self.selectedSet), it is not directly usable for the
        selectedSet parameter, as it can contain icons that have been deleted.  To remove
        those icons and make it usable, call _pruneSelectedIcons() before passing it to
        this function."""
        firstStmtOfSelection, firstIconOfSelection, iconAfterFirstSelection, \
            spansStmtBoundaries, startsOnStmtBoundary, endsOnStmtBoundary = \
            self.findFirstContiguousSelection(selectedSet)
        # Figure out insert site based on the first contiguous selection.  Set
        # insertSiteIcon and insertSite to a site that will survive icon removal.  The
        # site also subtly indicates the type of insertion in the same way as the cursor
        # would: a sequence site implies a statement break, where a non-sequence site
        # implies that a merge with the statement is desired (if possible).
        recalcInsertSite = None
        insertPos = insertSiteIcon = insertSite = None
        if isinstance(firstIconOfSelection, commenticon.CommentIcon) and \
                firstIconOfSelection.attachedToStmt is not None:
            # The selection starts with a statement comment.  Using the rightmost site
            # of the statement to which it is attached, allows the user to either replace
            # the comment, or insert code (or a comment followed by code).  Note, that we
            # don't consider the next statement to be contiguous, which only means that
            # we forgo the text-editor analog of merging the last inserted statement with
            # the remainder of a partially-selected statement at the selection end.
            insertSiteIcon, insertSite = icon.rightmostSite(firstStmtOfSelection)
        elif startsOnStmtBoundary:
            # The selection starts on a statement boundary.  Insert site may change after
            # deletion of selected icons, or may encompass the entire sequence.
            if endsOnStmtBoundary:
                # Selection is a range of complete statements.  To prevent the insert
                # function from concatenating, specify sequence site as destination.
                if firstStmtOfSelection.childAt('seqIn') is None:
                    if iconAfterFirstSelection is None:
                        # Selection encompasses the entire sequence.  Insert at
                        # position, instead of icon site
                        insertPos = firstStmtOfSelection.pos()
                    else:
                        insertSiteIcon = iconAfterFirstSelection
                        insertSite = 'seqIn'
                else:
                    insertSiteIcon = firstStmtOfSelection.childAt('seqIn')
                    insertSite = 'seqOut'
            else:
                recalcInsertSite = iconAfterFirstSelection
        else:
            # Selection starts in the middle of the statement
            if isinstance(firstIconOfSelection, tuple):
                # The selection starts with an empty site (findFirstContiguousSelection
                # returns a tuple containing icon and site to indicate this).
                insertSiteIcon, insertSite = firstIconOfSelection
            else:
                leftSite = firstIconOfSelection.hasCoincidentSite()
                if leftSite is None or firstIconOfSelection.childAt(leftSite) is None:
                    insertSiteIcon = firstIconOfSelection.parent()
                    while insertSiteIcon in selectedSet:
                        # firstIconOfSelection is lexically first, but may be a (left
                        # argument) child of an icon that is part of the selected range
                        insertSiteIcon = insertSiteIcon.parent()
                    if insertSiteIcon is None:
                        # The selection does not start on a statement boundary, but its
                        # parents (all the way up) are also being deleted.  This can
                        # happen for naked tuples and assignments being deleted out from
                        # under their content.  Use rightmost site of the prior entry.
                        topParent = firstStmtOfSelection.topLevelParent()
                        if isinstance(topParent, assignicons.AssignIcon) or \
                                isinstance(topParent, listicons.TupleIcon) and \
                                topParent.noParens:
                            topParentSite = topParent.siteOf(firstIconOfSelection,
                                recursive=True)
                            prevSite = iconsites.prevSeriesSiteId(topParentSite)
                            if prevSite is None or topParent.childAt(prevSite) is None:
                                print("replaceSelectedIcons failed to find insert site 1")
                                return None, None
                            insertSiteIcon, insertSite = icon.rightmostFromSite(
                                topParent, prevSite)
                        else:
                            print("replaceSelectedIcons failed to find insert site 2")
                            return None, None
                    else:
                        insertSite = insertSiteIcon.siteOf(firstIconOfSelection,
                            recursive=True)
                else:
                    # The first icon of the selection has a coincident site on the left
                    leftSiteIcon = firstIconOfSelection.childAt(leftSite)
                    insertSiteIcon, insertSite = icon.rightmostSite(leftSiteIcon)
        # If the insert site is enclosed by a bounding icon and the inserted code
        # contains statement-only icons, we may not be able to split around them.
        # Bail out and return failure indication if that is the case.
        if not (startsOnStmtBoundary or endsOnStmtBoundary):
            insertingStmtOnlyIcons = False
            numStmtsInserted = 0
            for ic in (i for seq in insertedSequences for i in seq):
                if expredit.isStmtLevelOnly(ic) and \
                        not isinstance(ic, commenticon.VerticalBlankIcon):
                    insertingStmtOnlyIcons = True
                numStmtsInserted += 1
            enclosingIcon, enclosingSite = entryicon.findEnclosingSite(insertSiteIcon,
                insertSite)
            if insertingStmtOnlyIcons and  \
                not (expredit.openOnRight(enclosingIcon, enclosingSite) or
                    isinstance(enclosingIcon, assignicons.AssignIcon) and
                    numStmtsInserted == 1 and
                    isinstance(insertedSequences[0][0], assignicons.AssignIcon) or
                    isinstance(insertedSequences[0][0],  (blockicons.ForIcon,
                    blockicons.IfIcon, listicons.CprhIfIcon, listicons.CprhIfIcon)) and
                    numStmtsInserted <= 2 and listicons.isProxyForCprhSite(
                    insertSiteIcon, insertSite, True, True)[0] is not None):
                # ... Yipes, what a horrible 'if'.  This really needs to be modularized
                return None, None
        # removeIcons and insertIconsFromSequences (surprisingly) will properly handle
        # statement comment transfer in most cases.  The single case where they need
        # help is with the comments of fully-deleted statements in the range being
        # replaced.  removeIcons transforms these into line comments that can prevent the
        # insertion from spanning the deleted range.  Temporarily remove these to restore
        # after we know where it's safe to insert them as line comments, or whether we
        # need to coalesce them into a single (weird) statement comment.
        removedComments = []
        if spansStmtBoundaries:
            if startsOnStmtBoundary:
                startStmt = firstStmtOfSelection
            else:
                startStmt = firstStmtOfSelection.nextInSeq()
            if endsOnStmtBoundary:
                endStmt = None if iconAfterFirstSelection is None else \
                    iconAfterFirstSelection.prevInSeq()
            else:
                endStmt = iconAfterFirstSelection.topLevelParent().prevInSeq()
            if endStmt is not None and endStmt.nextInSeq() is not startStmt:
                stmt = startStmt
                while stmt is not None:
                    stmtComment = stmt.hasStmtComment()
                    if stmtComment is not None:
                        stmtComment.detachStmtComment()
                        removedComments.append(stmtComment)
                    if stmt is endStmt:
                        break
                    stmt = stmt.nextinSeq()
        # Remove the selected icons
        self.requestRedraw(firstStmtOfSelection.hierRect())
        stmtBeforeSelection = firstStmtOfSelection.prevInSeq()
        if iconAfterFirstSelection is not None:
            self.requestRedraw(iconAfterFirstSelection.topLevelParent().hierRect())
        if recalcInsertSite:
            watchedIcon = recalcInsertSite
        elif insertSiteIcon is not None:
            watchedIcon = insertSiteIcon
        else:
            watchedIcon = None
        watchSubs = {watchedIcon:None} if watchedIcon is not None else None
        self.removeIcons(selectedSet, watchSubs=watchSubs, preserveSite=
            insertSiteIcon if isinstance(insertSiteIcon, listicons.TupleIcon) else None)
        if watchedIcon is not None and watchSubs[watchedIcon] is not None:
            # removeIcons did a substitution on the intended insert site
            if recalcInsertSite is not None:
                recalcInsertSite = watchSubs[watchedIcon]
            elif insertSiteIcon is not None:
                # Failed to figure out a test case for this code.  Is it dead?
                insertSiteIcon = watchSubs[watchedIcon]
                if isinstance(insertSiteIcon, parenicon.CursorParenIcon):
                    insertSite = 'argIcon'
                elif isinstance(insertSiteIcon, listicons.TupleIcon):
                    insertSite = 'argIcons_0'
                elif isinstance(insertSiteIcon, opicons.BinOpIcon):
                    insertSite = 'leftArg'
                else:
                    print("*** replaceSelectedIcons: need support for this substitution")
        # removeIcons might also have added an entry icon or naked tuple on top of the
        # first icon after the selection.  If so, redirect the insert site, there.
        if recalcInsertSite:
            topIcon = recalcInsertSite.topLevelParent()
            insertSiteIcon = topIcon
            for siteName in ('output', 'prefixInsert', 'attrOut'):
                if topIcon.hasSite(siteName):
                    insertSite = siteName
                    break
            else:
                insertSite = 'seqIn'  # cprh icons can produce for/if with no output site
            if insertSite == 'output':
                coincSite = insertSiteIcon.hasCoincidentSite()
                if coincSite is not None:
                    insertSite = coincSite
        # Insert (all) the new icons where the first selection section was removed
        asSeries = insertSiteIcon is not None and iconsites.isSeriesSiteId(insertSite)
        cursorIc, cursorSite = self.insertIconsFromSequences(insertSiteIcon, insertSite,
            insertedSequences, insertPos, asSeries=asSeries, alwaysConsolidate=True)
        # removeIcons operates entirely per-statement (does not join statements across
        # removed selections), but for a paste, this is what users will expect (I think),
        # so if the selection ended in the middle of a statement, join it to the last
        # inserted statement.
        # ... (and I think it's what they well expect on a delete command, but we're
        #     not doing yet)
        if not endsOnStmtBoundary:
            lastInsertedStmt = cursorIc.topLevelParent()
            if not (lastInsertedStmt is None or isinstance(lastInsertedStmt,
                    (commenticon.CommentIcon, commenticon.VerticalBlankIcon))):
                newCursorIc, newCursorSite = expredit.joinStmts(lastInsertedStmt)
                if newCursorIc is not None and newCursorSite is not None:
                    cursorIc, cursorSite = newCursorIc, newCursorSite
        # Restore any removed statement comments.  If the end result of the replacement
        # was a single statement, we make them into a single newline-separated statement
        # comment, otherwise, insert them as line-comments before the stmt containing
        # the cursor.
        if len(removedComments) > 0:
            # To determine whether we did a single-line replacement, compare the cursor
            # position returned from insertIconsFromSequences and the last statement in
            # the sequence with no selection (the stmt prior to firstStmtOfSelection).
            # The cursor position takes in to account all of the changes we have made,
            # and the prior statement is guaranteed to survive those changes (note that
            # this can be None if the selection starts in the first stmt of the sequence.
            cursorStmt = cursorIc.topLevelParent()
            if cursorStmt.prevInSeq() is stmtBeforeSelection:
                existingComment = cursorStmt.hasStmtComment()
                if existingComment is None:
                    stmtComment = removedComments.pop(0)
                    stmtComment.attachStmtComment(cursorStmt)
                else:
                    stmtComment = existingComment
                for comment in removedComments:
                    stmtComment.mergeTextFromComment(comment, sep='\n')
            else:
                for comment in removedComments:
                    icon.insertSeq(comment, cursorStmt, before=True)
                    cursorStmt.window.addTop(comment)
        return cursorIc, cursorSite

    def insertIconsFromSequences(self, atIcon, atSite, insertedSequences, atPos=None,
            asSeries=False, alwaysConsolidate=False):
        """Insert all of the icons in list of (already sequence-connected) sequences in
        insertedSequences.  For pasting at a window-cursor, set atIcon to None and
        specify atPos as the position in the window at which to place them.  If
        insertedSequences contains statement-only icons and the insertion site is within
        code that cannot be broken apart to insert such statements, the insertion will
        not be performed and the function will return None, None.  On success, return
        the icon and site on which to place the cursor after the operation.  If asSeries
        is set to True, force insertion as a series element if possible.  In the case of
        placing at a window location (atIcon==None and window position in atPos), the
        inserted sequences are not combined into a single sequence or series as they are
        in all other cases, but placed in separate sequences with their existing
        positions offset by atPos (the user is relocating loose icons).  If this is not
        the desired behavior (such as when processing a replace operation) setting
        alwaysConsolidate to True, tells the function to combine the sequences as normal,
        and also to treat atPos as overriding the position for the icon or sequence, as
        opposed to an offset to its existing position."""
        # Analyze the inserted sequences to determine what we will be able do with them
        insertingStmtOnlyIcons = insertingNonExprIcons = False
        numExprsInserted = numStmtsInserted = 0
        for ic in (i for seq in insertedSequences for i in seq):
            if expredit.isStmtLevelOnly(ic) and \
                    not isinstance(ic, commenticon.VerticalBlankIcon):
                insertingStmtOnlyIcons = True
            if ic.hasSite('output'):
                if isinstance(ic, listicons.TupleIcon) and ic.noParens:
                    numExprsInserted += 2  # Anything > 1 is all the same
                else:
                    numExprsInserted += 1
            elif not isinstance(ic, commenticon.VerticalBlankIcon):
                insertingNonExprIcons = True
            numStmtsInserted += 1
        # Handle the case of "inserting" to the window background (not integrating with
        # other icons).  Unlike insertions into existing code, we will not aggregate them
        # (unless alwaysConsolidate is True), but instead add them as individual new
        # sequences. maintaining their relative positions, but offset to atPos.
        if atIcon is None:
            if alwaysConsolidate:
                if asSeries and not insertingNonExprIcons:
                    insertList, strippedComments = cvtSeqsToList(insertedSequences)
                    newTuple = listicons.TupleIcon(window=self, noParens=True)
                    newTuple.insertChildren(insertList)
                    if len(strippedComments) > 0:
                        stmtComment = strippedComments.pop(0)
                        stmtComment.attachStmtComment(newTuple)
                        for comment in strippedComments:
                            stmtComment.mergeTextFromComment(comment)
                    topInsIcons =[newTuple]
                else:
                    _, topInsIcons = concatenateSequences(insertedSequences)
                filefmt.moveIconToPos(topInsIcons[0], (0, 0))
                insertedSequences = [topInsIcons]
            cursorStmt = insertedSequences[-1][-1]
            for seq in insertedSequences:
                x, y = atPos
                seqStartIcon = seq[0]
                seqStartIcon.rect = comn.offsetRect(seqStartIcon.rect, x, y)
                if seqStartIcon.childAt('seqOut') is None and isinstance(seqStartIcon,
                        entryicon.EntryIcon) and seqStartIcon.text == '':
                    # Since we're placing something on the window background, take the
                    # opportunity to remove unneeded placeholder entry icons.
                    pendingArgs = seqStartIcon.listPendingArgs()
                    nonEmptyArgs = list(icon.placementListIter(pendingArgs,
                        includeEmptySeriesSites=False))
                    if len(nonEmptyArgs) == 1:
                        seqStartIcon.popPendingArgs("all")
                        arg = nonEmptyArgs[0][0]
                        filefmt.moveIconToPos(arg, seqStartIcon.pos())
                        subsIc = listicons.subsCanonicalInterchangeIcon(arg)
                        if subsIc is not None:
                            arg = subsIc
                        self.addTop(arg)
                        if seqStartIcon is cursorStmt:
                            cursorStmt = arg
                    else:
                        self.addTop(seq)
                else:
                    self.addTop(seq)
            return icon.rightmostSite(cursorStmt)
        # Check for insertion of comprehension icons or 'for' or 'if' icons that can be
        # substituted them, on comprehension-compatible sites.  Since these can only be
        # inserted at very specific sites, we can handle them up-front and keep them from
        # complicating the later code.
        if len(insertedSequences) == 1 and isinstance(insertedSequences[0][0],
                (blockicons.ForIcon, blockicons.IfIcon, listicons.CprhIfIcon,
                listicons.CprhIfIcon)) and len(insertedSequences[0]) <= 2:
            cprhProxyIc, cprhIdx = listicons.isProxyForCprhSite(atIcon, atSite,
                allowNonEmpty=True, includeParenIcon=True)
            if cprhProxyIc is not None:
                if isinstance(insertedSequences[0][0], (blockicons.ForIcon,
                        blockicons.IfIcon)):
                    subsIcons, alsoRemove = restoreFromCanonicalInterchangeIcon(
                        insertedSequences[0][0], 'cprhIn')
                    if subsIcons is not None:
                        listicons.placeArgsInclCprh(subsIcons, atIcon, atSite)
                        return icon.rightmostSite(subsIcons[-1])
        # Another peculiar special case, is inserting a single block owning statement
        # (such as for or while) with an empty block to the left of a statement-level
        # icon with an output or attribute-out site.  Even though we're inserting a
        # block-end-icon, it still *looks* like a single statement, and so we treat it
        # as such, and do the insert as a prefix.
        if len(insertedSequences) == 1 and isinstance(insertedSequences[0][0],
                (blockicons.ForIcon, blockicons.IfIcon, blockicons.WhileIcon,
                blockicons.WithIcon)) and len(insertedSequences[0]) <= 2 and \
                expredit.isLeftmostSite(atIcon, atSite):
            insIc = insertedSequences[0][0]
            insStmtComment = insIc.hasStmtComment()
            exprTop = atIcon.topLevelParent()
            existingStmtComment = exprTop.hasStmtComment()
            self.replaceTop(exprTop, insIc, transferStmtComment=False)
            if existingStmtComment is not None:
                existingStmtComment.detachStmtComment()
            cursorIcon, cursorSite = expredit.insertAtSite(*icon.rightmostSite(insIc),
                exprTop, cursorLeft=True)
            # Merge-in the statement comments
            if existingStmtComment is not None:
                if insStmtComment is None:
                    existingStmtComment.attachStmtComment(insIc)
                else:
                    insStmtComment.mergeTextFromComment(existingStmtComment)
            return cursorIcon, cursorSite
        # The one case we can't handle is when the inserted code contains statement-only
        # icons, and the destination is within an enclosing icon that bounds it from
        # being split.  Bail out and return failure indication if that is the case.
        isLeftmostSite = expredit.isLeftmostSite(atIcon, atSite) or atSite == 'seqIn'
        rightmostIcon, rightmostSite = icon.rightmostSite(atIcon.topLevelParent())
        isRightmostSite = rightmostIcon == atIcon and atSite == rightmostSite or \
            atSite == 'seqOut'
        topIcon = atIcon.topLevelParent()
        enclosingIcon, enclosingSite = entryicon.findEnclosingSite(atIcon, atSite)
        if insertingStmtOnlyIcons and not isLeftmostSite and not isRightmostSite and \
            not (expredit.openOnRight(enclosingIcon, enclosingSite) or
                isinstance(enclosingIcon, assignicons.AssignIcon) and
                numStmtsInserted == 1 and
                isinstance(insertedSequences[0][0], assignicons.AssignIcon)):
            return None, None
        self.requestRedraw(topIcon.hierRect())
        # Choose how to do the insert: whether to treat statements in the inserted code
        # as list elements or to leave them as statements or individual expressions.
        insertAsStmts = insertAsIndividual = insertAsList = insertAsStmtComment = False
        if isinstance(insertedSequences[0][0], commenticon.CommentIcon) and \
                not (isLeftmostSite or atSite in ('seqIn', 'seqOut')):
            # The inserted code starts with a comment, and the insertion site is neither
            # a sequence site nor the left site of the stmt.  (excluding the left site is
            # a somewhat random choice, mostly for text-editor-accustomed users who might
            # want to paste a line-comment there).
            insertAsStmtComment = True
        elif atSite in ('seqIn', 'seqOut'):
            # We're inserting specifically at the statement (at a sequence site).
            insertAsStmts = True
        elif insertingStmtOnlyIcons:
            # We're inserting icons that must stay at the statement level.  Assignments
            # are a special case, because while they need to be on the top level, they
            # also have sites on the right, allowing them to be "appended" to things.
            insIc = insertedSequences[0][0]
            topIcon = atIcon.topLevelParent()
            if numStmtsInserted == 1 and (
                    isinstance(insIc, assignicons.AssignIcon) and (isRightmostSite or (
                     isinstance(enclosingIcon, assignicons.AssignIcon) or
                     isinstance(enclosingIcon, listicons.TupleIcon) and
                      enclosingIcon.noParens)) or
                    isinstance(insIc, assignicons.AugmentedAssignIcon) and
                     isRightmostSite and expredit.leftSiteIsEmpty(insIc) and
                     topIcon.hasSite('output')):
                insertAsIndividual = True
            else:
                insertAsStmts = True
        elif atIcon.isCursorOnlySite(atSite) and \
                atIcon.__class__ in cursors.stmtIcons and \
                atIcon.typeOf(atSite) == 'attrIn':
            # We're appending to a statement that can't be appended to, such as pass
            # or def, and need to redirect to the seqOut site
            atSite = 'seqOut'
            insertAsStmts = True
        elif not insertingNonExprIcons and (numExprsInserted > 1 or asSeries) and (
                enclosingIcon is not None and
                enclosingIcon.typeOf(enclosingSite) == 'input' or
                enclosingIcon is None and atIcon.topLevelParent().hasSite('output')):
            # The criteria for list-style insertion are there are multiple icons, all
            # compatible with input sites, and that the destination site is either
            # enclosed by an input-capable site or not enclosed and capable of being
            # part of a series.
            insertAsList = True
        elif numStmtsInserted == 1 and not \
                isinstance(insertedSequences[0][0], commenticon.VerticalBlankIcon):
            insertAsIndividual = True
        else:
            insertAsStmts = True
        # Insert the new icons
        if insertAsStmtComment:
            # The first inserted icon is a comment and the destination is vetted as
            # accepting one.  If there are more statements left, insert them after the
            # statement to which we attached the comment.  Note that we don't split at
            # the insertion site as we would normally do for insertion, mirroring the
            # way statement comments can be typed anywhere in the statement.
            insertSeqStart, topInsertedIcons = concatenateSequences(insertedSequences)
            commentIc = insertSeqStart
            nextIc = commentIc.nextInSeq()
            commentIc.replaceChild(None, 'seqOut')
            topParent = atIcon.topLevelParent()
            existingStmtComment = topParent.hasStmtComment()
            if existingStmtComment is None:
                commentIc.attachStmtComment(topParent)
            else:
                existingStmtComment.mergeTextFromComment(commentIc, before=True)
            if nextIc is not None:
                icon.insertSeq(nextIc, topParent)
                self.addTop(topInsertedIcons[1:])
                cursorIcon = topInsertedIcons[-1]
                cursorSite = 'seqOut'
            else:
                cursorIcon, cursorSite = icon.rightmostSite(topParent)
        elif insertAsStmts:
            insertSeqStart, topInsertedIcons = concatenateSequences(insertedSequences)
            if atSite in ('seqIn', 'seqOut'):
                # When a sequence site is specified we don't do any merging of statement
                # code, just insert them in the sequence at the specified site.
                icon.insertSeq(insertSeqStart, atIcon, before=atSite=='seqIn')
                self.addTop(topInsertedIcons)
                cursorIcon = topInsertedIcons[-1]
                cursorSite = 'seqOut'
            elif atSite == 'prefixInsert':
                # The insert site is the special site before a line comment for dropping
                # pasting, or typing code that will convert it to a statement comment
                nextInsertStmts = insertSeqStart.nextInSeq()
                if nextInsertStmts is not None:
                    insertSeqStart.replaceChild(None, 'seqOut')
                self.replaceTop(atIcon, insertSeqStart)
                atIcon.attachStmtComment(insertSeqStart)
                if nextInsertStmts is not None:
                    icon.insertSeq(nextInsertStmts, insertSeqStart)
                    self.addTop(topInsertedIcons[1:])
                cursorIcon = topInsertedIcons[-1]
                cursorSite = 'seqOut'
            else:
                # We're not starting at a stmt boundary, merge first stmt from inserted
                # code with the first inserted stmt, and prepend the last inserted stmt
                # to the code after the insert position.  For this operation, we take the
                # simpler but more wasteful approach of inserting the statements, first
                # (without merging) then attempting to join them to the surrounding code
                # in subsequent operation(s).  Note that statement comment transfer is
                # handled by the 'split' and 'join' calls.
                cursorIcon, cursorSite = icon.rightmostSite(topInsertedIcons[-1])
                topParent = atIcon.topLevelParent()
                if not topParent.hasSite('seqOut'):
                    # We are going to make a multi-statement sequence, and we can't do
                    # that if we're inserting on an icon that can't be part of a
                    # sequence (such as an attribute alone on the window background).
                    entryIc = entryicon.EntryIcon(window=atIcon.window)
                    topParent.replaceWith(entryIc)
                    entryIc.appendPendingArgs([topParent])
                    topParent = entryIc
                if isLeftmostSite:
                    # Insert the sequence before the statement holding the insertion
                    # site and merge the last statement of the sequence with it.
                    lastInsertedStmt = topInsertedIcons[-1]
                    icon.insertSeq(insertSeqStart, topParent, before=True)
                    self.addTop(topInsertedIcons)
                    expredit.joinStmts(lastInsertedStmt)
                elif isRightmostSite:
                    # Merge the first element of the sequence with the statement holding
                    # the insertion site, and splice the remaining ones in to the
                    # sequence, after it
                    icon.insertSeq(insertSeqStart, topParent)
                    atIcon.window.addTop(topInsertedIcons)
                    expredit.joinStmts(topParent)
                else:
                    # The sequence is to be inserted in the middle of the statement
                    # holding the insertion site. (we verified, earlier, that this was
                    # possible):
                    # 1) split the statement holding the insertion site around the
                    #    insertion site,
                    # 2) insert the remaining icons at the site of the split
                    # 3) join the last inserted statement with the right half of the
                    #    split expression.
                    leftStmt, rightStmt = expredit.splitStmtAtSite(atIcon, atSite)
                    icon.insertSeq(insertSeqStart, leftStmt)
                    atIcon.window.addTop(topInsertedIcons)
                    expredit.joinStmts(leftStmt)
                    if rightStmt is not None:
                        expredit.joinWithPrev(rightStmt)
        elif insertAsIndividual:
            insertedTopIcon = insertedSequences[0][0]
            insertedStmtComment = insertedTopIcon.hasStmtComment()
            if insertedStmtComment is not None:
                insertedStmtComment.detachStmtComment()
            cursorIcon, cursorSite = expredit.insertAtSite(atIcon, atSite,
                insertedTopIcon)
            # Merge-in the statement comment (if any) from the inserted tree (relocation
            # of the statement comment associated with the tree above atIcon is already
            # done for us by insertAtSite and reorderMarkedExprs)
            if insertedStmtComment is not None:
                newTopIcon = cursorIcon.topLevelParent()
                stmtComment = newTopIcon.hasStmtComment()
                if stmtComment is None:
                    insertedStmtComment.attachStmtComment(newTopIcon)
                else:
                    stmtComment.mergeTextFromComment(insertedStmtComment,
                        before=isLeftmostSite)
        elif insertAsList:
            # Convert the inserted sequences into a single list, removing sequence links.
            insertList, strippedComments = cvtSeqsToList(insertedSequences)
            cursorIcon, cursorSite = expredit.insertListAtSite(atIcon, atSite, insertList)
            # Merge any statement comments from the list elements (insertListAtSite will
            # transfer a statement comment across any reparenting).
            if len(strippedComments) > 0:
                topIcon = cursorIcon.topLevelParent()
                stmtComment = topIcon.hasStmtComment()
                if stmtComment is None:
                    stmtComment = strippedComments.pop(0)
                    stmtComment.attachStmtComment(topIcon)
                for comment in strippedComments:
                    stmtComment.mergeTextFromComment(comment)
        return cursorIcon, cursorSite

    def findFirstContiguousSelection(self, selectedSet):
        """Find the first (top left) icon(s) in the window in selectedSet.  Returns:
        1) The top-level statement icon containing the start of the selection
        2) The (lexically) leftmost icon of the selection (start of selection).  If the
           selection starts with an empty site (which it can because this is lexical
           traversal) returns a tuple of the parent and parent site name.
        3) The (lexically) first un-selected icon after the selection
        4) (True/False) Whether the selection spans statement boundaries
        5) (True/False) Whether the selection starts on a statement boundary
        6) (True/False) Whether the selection ends on a statement boundary"""
        # Find the top left selected icon
        topLeft = 99999999, 99999999
        topLeftIc = None
        for ic in selectedSet:
            pos = ic.pos()
            if pos[1] < topLeft[1] or pos[1] == topLeft[1] and pos[0] < topLeft[0]:
                topLeft = pos
                topLeftIc = ic
        if topLeftIc is None:
            return None, None, None, False, False, False
        firstSelectedStmt = topLeftIc.topLevelParent()
        if isinstance(topLeftIc, commenticon.CommentIcon) and \
                topLeftIc.attachedToStmt is not None:
            # The selection starts with a statement-comment.  While we might the next
            # next statement as being contiguous with the comment, this would not lead
            # to processing it differently in most circumstances
            stmt = topLeftIc.attachedToStmt
            return stmt, topLeftIc, stmt.nextInSeq(), False, False, True
        # Iterate in lexical order over the icons in the statement to find the find the
        # start of the selection and whether it continues to the end of the statement.
        # If it does not, we're done and can return the result.
        foundSelection = None
        firstIconOfSelection = None
        startsOnStmtBoundary = True
        spansStmtBoundaries = False
        for ic, partId in expredit.lexicalTraverse(firstSelectedStmt):
            if isinstance(ic, tuple):  # Empty site indicator (NOT tuple icon)
                # Empty site: What we do depends upon whether the parent is selected or
                # not.  If the parent is selected, we consider the empty site part of the
                # selection, and part of the contiguous run.  If not, then we consider it
                # to be unselected and therefore, the end of the contiguous selection.
                parent, parentSite = ic
                if parent in selectedSet:
                    if not foundSelection:
                        # Found the start of the selection
                        foundSelection = True
                        firstIconOfSelection = parent, parentSite
                    continue
                return firstSelectedStmt, firstIconOfSelection, None, \
                    spansStmtBoundaries, startsOnStmtBoundary, False
            elif ic in selectedSet:
                if not foundSelection:
                    # Found the start of the selection
                    foundSelection = True
                    firstIconOfSelection = ic
            else:
                if not foundSelection:
                    startsOnStmtBoundary = False
                else:
                    # Found the end of the selection within the first statement
                    return firstSelectedStmt, firstIconOfSelection, ic, \
                        spansStmtBoundaries, startsOnStmtBoundary, False
        if not foundSelection:
            print('findFirstContiguousSelection internal consistency error')
            return None, None, None, False, False, False
        # The first contiguous selection reaches the right edge of the statement.  Scan
        # (in lexical order) subsequent statements for the first un-selected icon.
        unselBlockEnd = None
        for stmt in icon.traverseSeq(firstSelectedStmt, includeStartingIcon=False):
            # If we haven't yet determined if the selection spans the first statement
            # boundary, explicitly check that the selection crosses the first icon
            if isinstance(stmt, icon.BlockEnd):
                # It's normal to have unselected block-ends within the selected range, as
                # they reflect the selection status of the block owner, but if the
                # selection ends immediately after one, the block end is appropriate as
                # the first unselec
                unselBlockEnd = stmt
                continue
            for i, (ic, partId) in enumerate(expredit.lexicalTraverse(stmt)):
                if ic not in selectedSet:
                    if i == 0:
                        # The selection ends at the start of this statement
                        icAfterSel = stmt if unselBlockEnd is None else unselBlockEnd
                        return firstSelectedStmt, firstIconOfSelection, icAfterSel, \
                            spansStmtBoundaries, startsOnStmtBoundary, True
                    else:
                        # The selection ends in the middle of the statement
                        spansStmtBoundaries = True
                        return firstSelectedStmt, firstIconOfSelection, ic, \
                            spansStmtBoundaries, startsOnStmtBoundary, False
            unselBlockEnd = None
        # We reached the end of the sequence (therefore selection ends on stmt boundary)
        return firstSelectedStmt, firstIconOfSelection, unselBlockEnd, \
            spansStmtBoundaries, startsOnStmtBoundary, True

    def saveFile(self, filename):
        _base, ext = os.path.splitext(filename)
        print('Started save')
        with open(filename, "w") as f:
            self.writeSaveFileText(f, exportPython=ext != ".pyg")
        print('Finished save')

    def writeSaveFileText(self, outStream, selectedOnly=False, exportPython=False):
        """Write save-file-format text to outStream.  By default, will save all icons in
        the window.  If selectedOnly is specified, only the selected icons in the window
        will be written."""
        # Iterate over sequences determined by _findtSequencesForOutput.  While it would
        # seem obvious to write the position macro in the outer (per sequence) loop, it's
        # actually written in the inner (per stmt) loop because there are some cases
        # where the generated text helps determine the form of the macro. There are also
        # some ugly inefficiencies in the clipboard case (see _findtSequencesForOutput),
        # particularly when selections get large.
        pruneBlockEnds = set()
        tabSize = DEFAULT_SAVE_FILE_TAB_SIZE
        isFirstSeq = True
        for pos, isModSeqIcon, seqIter in self._findtSequencesForOutput(selectedOnly):
            haveWrittenSeqPos = False
            branchDepth = 0
            isStartOfOwnedBlock = False
            pendingDecorators = False
            blockCtx = blockicons.BlockContextStack()
            for isSingleStmt, ic in flagIndividual(seqIter):
                if isinstance(ic, icon.BlockEnd) and ic not in pruneBlockEnds:
                    # Python requires a 'pass' statement for empty blocks and something
                    # to decorate for decorators
                    if pendingDecorators:
                        outStream.write(tabSize*branchDepth*' ' + '$UnusedDecorator$\n')
                        pendingDecorators = False
                    elif isStartOfOwnedBlock:
                        self._writePassStmt(outStream, tabSize * branchDepth,
                            not exportPython)
                        isStartOfOwnedBlock = False
                    # If user makes a selection that would go negative indent, we just
                    # flatten at 0, since the only alternative would be to invent non-
                    # existent block owning statements to preserve their indentation.
                    branchDepth = max(0, branchDepth - 1)
                    # The Python parser will not accept a try block without either an
                    # except or a finally block, so emit $EmptyTry$ workaround macro
                    if not exportPython and blockCtx.isIncompleteTryBlock():
                        outStream.write(tabSize * branchDepth * ' ' + '$EmptyTry$')
                    blockCtx.pop()
                    continue
                # If we're outputting selected icons and some of the icons in the
                # current statement are not selected, make a temporary copy and use
                # splitDeletedIcons to reassemble the remaining ones.  Note that
                # we're going statement-by-statement and don't care about re-linking
                # block-end pointers, just that we don't indent for pruned block-owners
                # or dedent for their corresponding block-ends.
                stmtComment = ic.stmtComment if hasattr(ic, 'stmtComment') else None
                if selectedOnly and (
                        any((c not in self.selectedSet for c in ic.traverse())) or
                        stmtComment is not None and stmtComment not in self.selectedSet):
                    prunedIc = _makePrunedCopy(ic, self.selectedSet, not isSingleStmt)
                    if hasattr(ic, 'blockEnd') and ic not in self.selectedSet:
                        pruneBlockEnds.add(ic.blockEnd)
                else:
                    prunedIc = ic
                # Work-around statement-level differences between Python parser and icon
                # form: pass statements are required decorators must decorate something
                if isinstance(prunedIc, (blockicons.DefIcon, blockicons.ClassDefIcon)):
                    pendingDecorators = False
                elif pendingDecorators and not isinstance(prunedIc,
                        (commenticon.CommentIcon, commenticon.VerticalBlankIcon)):
                    outStream.write(tabSize * branchDepth * ' ' + '$UnusedDecorator$\n')
                    pendingDecorators = False
                elif isStartOfOwnedBlock and blockicons.isPseudoBlockIc(prunedIc):
                    self._writePassStmt(outStream, tabSize*branchDepth, not exportPython)
                if isinstance(ic, nameicons.DecoratorIcon):
                    pendingDecorators = True
                if not isinstance(ic, (commenticon.CommentIcon,
                        commenticon.VerticalBlankIcon)):
                    isStartOfOwnedBlock = False
                # Compute the indent needed for this statement: pseudo-blocks get dedent
                # (but only valid ones).
                indent = tabSize * branchDepth
                pseudoBlockInvalid = False
                if blockicons.isPseudoBlockIc(prunedIc):
                    if exportPython:
                        indent = max(0, branchDepth - 1) * tabSize
                    elif branchDepth == 0 or not blockCtx.validForContext(prunedIc):
                        indent = tabSize * branchDepth
                        pseudoBlockInvalid = True
                    else:
                        blockCtx.push(prunedIc)
                        indent = tabSize * (branchDepth - 1)
                # Create the save text
                if pseudoBlockInvalid and not exportPython:
                    saveText = prunedIc.createInvalidCtxSaveText(export=exportPython)
                else:
                    saveText = prunedIc.createSaveText(export=exportPython)
                if blockicons.isBlockOwnerIc(prunedIc):
                    continueIndent = 8
                    branchDepth += 1
                    blockCtx.push(prunedIc)
                else:
                    continueIndent = tabSize
                # Compose an @ (pos) macro if one is needed.  Note that the rules for
                # whether one is needed are different between the clipboard and file
                # formats.  In the .pyg file, an @ macro is written for any sequence
                # that's not the module sequence.  In the clipboard format, the first
                # sequence written (regardless of whether it is the module sequence) is
                # written without the @ macro, except for the case where it is sequence-
                # unfriendly $Fragment$, where it gets a position of (0, 0).  Likewise,
                # positions in the file format are based on the absolute position of the
                # first element in the sequence, but in the clipboard format, are
                # relative to the first selected
                needsSeparator = False
                if exportPython:
                    needPosMacro = False
                    needsSeparator = not haveWrittenSeqPos and not isFirstSeq
                elif haveWrittenSeqPos:
                    needPosMacro = False
                elif selectedOnly:
                    needPosMacro = not isFirstSeq or saveText.isFragmentMacro()
                else:
                    needPosMacro = not isModSeqIcon
                if needPosMacro:
                    if saveText.isFragmentMacro() or ic.nextInSeq() is None and \
                            saveText.isCtxMacro():
                        # This is a single statement or fragment of some sort.  These
                        # can hold icons that cannot be part of a sequence, which is only
                        # determined by creating save text and checking for a $Ctx$ or
                        # $Fragment$ macro.  Note that here the pos macro is wrapped
                        # around the statement and will be output with the statement,
                        # whereas in the normal case (else, below) we write it on a
                        # separate line
                        saveText.cvtCtxOrFragmentToPosMacro(*pos)
                    else:
                        # Don't wrap the pos macro around the statement, just write it
                        # above the statement
                        outStream.write("$@%+d%+d$\n" % pos)
                if needsSeparator:
                    outStream.write('\n\n')
                haveWrittenSeqPos = True
                isFirstSeq = False
                if hasattr(prunedIc, 'stmtComment') and prunedIc.stmtComment is not None:
                    saveText.addComment(prunedIc.stmtComment.createSaveText(
                        export=exportPython), isStmtComment=True)
                # Wrap the save text and write it to outStream
                stmtText = saveText.wrapText(indent, indent + continueIndent,
                    margin=DEFAULT_SAVE_FILE_MARGIN, export=exportPython)
                outStream.write(stmtText)
                outStream.write('\n')
                if blockicons.isBlockOwnerIc(prunedIc) or blockicons.isPseudoBlockIc(ic) \
                        and not pseudoBlockInvalid:
                    isStartOfOwnedBlock = True
            # If we ended the sequence with a block-owning statement (user had block
            # owner as last statement in selection) or unassociated decorator, add a
            # 'pass' statement or an $UnusedDecorator$ macro.
            if pendingDecorators:
                outStream.write(tabSize * branchDepth * ' ' + '$UnusedDecorator$\n')
            if isStartOfOwnedBlock:
                self._writePassStmt(outStream, tabSize * branchDepth, not exportPython)

    def _findtSequencesForOutput(self, forClipboard):
        """Figure out what icons to iterate over for generating save-file and clipboard
        content.  This is an iterator over sequences, that also returns an iterator over
        icons within each sequence.  It is structured this way to handle both sorting of
        sequences and (in the clipboard case), culling the sequences themselves of icons
        that are not either themselves or parents of selelected icons.  Sorting is done
        To make the save file format stable for use by version control systems and
        diff/review tools, we need to order the sequence list consistently.  To do that,
        we sort it by y, then by x coordinate. of the start of the sequence. The method
        yields:
            1) The position to use for the the sequence in the '@' macro (if needed).
               For files, this is simply the position first icon of the sequence, but for
               the clipboard, it is the relative offset from the first selected icon of
               the first sequence to the first selected icon of the current sequence
               (therefore, (0, 0) for the first icon).  Also note that in the clipboard
               case, the position may not be that of the first icon of the sequence,
               since the selection may not include the top icon of the hierarchy.
            2) True if the sequence is the window module-sequence, False if not.
            3) An iterator yielding the relevant top-level icons in the seqeuence.  For
               files, this is all of them.  For clipboard data, this will skip over those
               which do not contain selected icons."""
        # As is currently the case for everything involving large selections, this may
        # be inefficient, as it traces up the icon hierarchy for every selected icon.  It
        # may also be inefficient for small selections in large files, as it traces
        # through all of the top-level icons in the process of assembling the icons into
        # sequences.  There might be some clever way to improve this, but it's more of
        # a structural issue, requiring change to the basic mechanisms for organizing
        # icons, sequences, and selections (probably starting with sequences).
        seqStartIcons = []
        if forClipboard:
            # Traverse just the sequences containing selected icons and just the top
            # icons that contain selections
            selectedTopIcons = set()
            for ic in self.selectedSet:
                if isStmtComment(ic):
                    selectedTopIcons.add(ic.attachedToStmt)
                else:
                    selectedTopIcons.add(ic.topLevelParent())
            for startPage in self.sequences:
                for ic in icon.traverseSeq(startPage.startIcon):
                    if ic in selectedTopIcons:
                        for i in ic.traverse(includeSelf=True, inclStmtComment=True):
                            if i in self.selectedSet:
                                firstSelectedIcon = i
                                break
                        break
                else:
                    continue
                x, y = firstSelectedIcon.pos()
                if isinstance(firstSelectedIcon, commenticon.CommentIcon) and \
                        firstSelectedIcon.attachedToStmt is not None:
                    seqStartIcons.append((y, x, firstSelectedIcon.attachedToStmt))
                else:
                    seqStartIcons.append((y, x, firstSelectedIcon.topLevelParent()))
            seqStartIcons.sort()
            firstSeqPos = None
            for y, x, startIcon in seqStartIcons:
                seqIter = (ic for ic in icon.traverseSeq(startIcon) if ic in
                    selectedTopIcons)
                if firstSeqPos is None:
                    firstSeqPos = x, y
                    pos = 0, 0
                else:
                    pos = icon.subtractPoints((x, y), firstSeqPos)
                yield pos, startIcon is self.modSeqIcon, seqIter
        else:
            # Traverse all sequences in the window
            for startPage in self.sequences:
                startIcon = startPage.startIcon
                if startIcon is startIcon.window.modSeqIcon:
                    x, y = -999999999,  -999999999
                else:
                    x, y = startIcon.pos()
                seqStartIcons.append((y, x, startIcon))
            seqStartIcons.sort()
            for y, x, startIcon in seqStartIcons:
                yield (x, y), startIcon is self.modSeqIcon, icon.traverseSeq(startIcon)

    @staticmethod
    def _writePassStmt(outStream, indent, withIgnoreMacro):
        outStream.write(indent * ' ')
        if withIgnoreMacro:
            outStream.write('$:x$')
        outStream.write('pass\n')

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
        self.undo.registerRemoveFromTopLevel(ic, lastOfSeq)
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
        if pageToRemove.startIcon is self.modSeqIcon:
            print("something tried to remove the module sequence page")
            return
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

    def replaceTop(self, old, new, transferStmtComment=True, alreadyRemoved=False):
        """Replace an existing top-level icon with a new icon.  If the existing icon was
        part of a sequence, replace it in the sequence.  If the icon was not part of a
        sequence place it in the same location.  If "new" will own a code block, also
        integrate its corresponding block-end icon.  Does not re-layout or re-draw.
        Note that this call is not intended for integrating a new code block (new must
        have an empty block if it has one).  If the old icon owned a code block, the new
        icon will take it over if it can, or the owned block will be dedented back to the
        parent sequence.  alreadyRemoved can be specified as True of removeTop has
        already been called on the old icon (which may be necessary to comply with the
        required ordering of operations for undo).  Passing new as None is allowed as a
        method for removing a single statement from a sequence without the additional
        overhead associated with removeIcons."""
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
            if not alreadyRemoved:
                self.removeTop([old, old.blockEnd])
            old.replaceChild(None, 'seqOut')
            old.blockEnd.replaceChild(None, 'seqIn')
            old.blockEnd.replaceChild(None, 'seqOut')
            if not isinstance(nextInSeq, icon.BlockEnd) and new is not None:
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
            if not alreadyRemoved:
                self.removeTop(old)
            if nextInSeq is not None:
                old.replaceChild(None, 'seqOut')
                if hasattr(new, 'blockEnd'):
                    # BlockEnd (which is already attached to new icon's seqOut) linked in
                    new.blockEnd.replaceChild(nextInSeq, 'seqOut')
                elif new is not None:
                    # Neither icon can own a code block
                    new.replaceChild(nextInSeq, 'seqOut')
        prevInSeq = old.prevInSeq(includeModuleAnchor=True)
        if prevInSeq:
            old.replaceChild(None, 'seqIn')
            if new is None:
                prevInSeq.replaceChild(nextInSeq, 'seqOut')
            else:
                new.replaceChild(prevInSeq, 'seqIn')
        if new is None and prevInSeq is None:
            filefmt.moveIconToPos(nextInSeq, old.pos())
        if new is not None:
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
        prevIcon = ic.prevInSeq(includeModuleAnchor=True)
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
        self._updateScrollRanges()
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
            if page.startIcon.nextInSeq() is None and \
                    page.startIcon.prevInSeq(includeModuleAnchor=True) is None:
                if isinstance(page.startIcon, ModuleAnchorIcon):
                    continue
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
        if isinstance(seqStartIcon, ModuleAnchorIcon):
            x = seqStartIcon.rect[0] + seqStartIcon.sites.seqOut.xOffset
            y = seqStartIcon.rect[1] + seqStartIcon.sites.seqOut.yOffset
            fromTopY = y
            seqStartIcon = seqStartIcon.sites.seqOut.att
            if seqStartIcon is None:
                return
        else:
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
        left = btnX - SITE_SELECT_DIST - EMPTY_SITE_EXT_DIST
        right = btnX + SITE_SELECT_DIST
        top = btnY - SITE_SELECT_DIST
        bottom = btnY + SITE_SELECT_DIST
        minDist = SITE_SELECT_DIST + 1
        minSite = (None, None, None)
        for ic in self.findIconsInRegion((left, top, right, bottom), order='pick',
                inclModSeqIcon=True):
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
                    if siteType == 'input' and siteIcon.childAt(siteName) is None:
                        # For empty sites, extend search range past middle of pink area
                        dist = min(dist, abs(btnX - x - EMPTY_SITE_EXT_DIST) +
                            abs(btnY - y))
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

    @contextlib.contextmanager
    def streamToOutputPane(self, includeStderr=True):
        """Redirect stdout and stderr streams to deposit text in the window's output
        pane.  This is done only during execution of the already-compiled code and inside
        of execution error handling, so hopefully will only ever apply to the user's
        actual output, and not to any of our crashes or diagnostic output.  Written as a
        context manager due to the devastating consequences of not restoring the output
        streams at the end of execution and likelihood of exceptions being involved."""
        origStdout = sys.stdout
        sys.stdout = StreamToTextWidget(self.outputPane)
        if includeStderr:
            origStderr = sys.stderr
            sys.stderr = StreamToTextWidget(self.outputPane)
        try:
            yield None
        finally:
            sys.stdout = origStdout
            if includeStderr:
                sys.stderr = origStderr

    @contextlib.contextmanager
    def pauseUndoRecording(self, includeStderr=True):
        """Stop undo recording.  Obviously, this needs to be used carefully."""
        savedUndoRedoList = self.undo
        self.undo = undo.undoNoOp
        try:
            yield None
        finally:
            self.undo = savedUndoRedoList

    def undoRecordingIsPaused(self):
        return self.undo == undo.undoNoOp

class Page:
    """The fact that icons know their own window positions becomes problematic for very
    large files, because tiny edits can relocate every single icon below them in the
    sequence.  To make this work, the Page structure was added to maintain an "unapplied
    offset" to a range of icons in a sequence.  When icons become visible and need to
    know their absolute positions, applyOffset can be called to update them.  The other
    issue that pages address is the need to quickly find icons by position, without
    traversing the entire tree.  The initialization for a window object can pass
    its module sequence anchor icon in forModSeq to create the module sequence start page
    (which persists for the life of the window)."""
    def __init__(self, forModSeq=None):
        self.unappliedOffset = 0
        self.layoutDirty = False
        self.topY = 0
        self.bottomY = 0
        self.iconCount = 1 if forModSeq else 0
        self.startIcon = forModSeq if forModSeq else None
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
        startIcon = page.startIcon
        if startIcon is startIcon.window.modSeqIcon:
            startIcon = startIcon.sites.seqOut.att
            pageStmtCnt += 1
            totalStmtCnt += 1
        for ic in icon.traverseSeq(startIcon):
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

    def traverseSeq(self, hier=False, order="draw", inclStmtComments=False,
            inclModSeqIcon=False):
        """Traverse the icons in the page (note, generator).  If hier is False, just
        return the top icons in the sequence.  If hier is True, return all icons.  order
        can be either "pick" or "draw", and controls hierarchical (hier=True) traversal.
        Parent icons are allowed to hide structure under child icons, so picking must be
        done child-first, and drawing must be done parent-first.  By default, the module
        anchor icon is not included, but can ba if inclModSeqIcon is set to True."""
        if self.startIcon is self.startIcon.window.modSeqIcon:
            if inclModSeqIcon:
                yield self.startIcon
            count = 1
        else:
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

class ModuleAnchorIcon(icon.Icon):
    def __init__(self,  window, location=None):
        icon.Icon.__init__(self, window)
        seqOutX, seqOutY = moduleAnchorSeqOutOffset
        self.sites.add('seqOut', 'seqOut', seqOutX, seqOutY)
        # The tip of the anchor is the seqOut site position
        rectX = MODULE_ANCHOR_X - seqOutX
        rectY = MODULE_ANCHOR_Y - seqOutY
        self.rect = (rectX, rectY, rectX + anchorImage.width, rectY+anchorImage.height)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            self.drawList = [((0, 0), anchorImage)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, x, bottom, _layout):
        # Never moves or changes
        pass

    def calcLayouts(self):
        print('something is trying to call calcLayouts on module anchor')
        return [iconlayout.Layout(self, anchorImage.width, anchorImage.height, 0)]

    def dumpName(self):
        return "module-anchor"

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
        if window.openFile(filename):
            window.top.lift()
            window.top.focus_force()
        else:
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
            if focusWidget in (window.top, window.imgFrame):
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
    # Since this can be expensive, short-cut the process for a single icon.  The single
    # icon case is common on its own, and but more importantly, code such as that in
    # replaceIcons that feed removeIcons per-statement, would multiply this expense by
    # the number of statements processed.
    if len(topIcons) == 0:
        return []
    if len(topIcons) == 1:
        return [[next(iter(topIcons))]]
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

def restoreFromCanonicalInterchangeIcon(ic, siteType):
    """Decides whether to substitute the site-specific version of a text-equivalent icon
    (see listicons.subsCanonicalInterchangeIcon for what this means).  If so, returns
    A LIST of icons to substitute and a list of linked icons (blockEnd and possibly pass)
    that also need to be removed.  If not, returns None, None."""
    if siteType != 'cprhIn':
        return None, None
    if isinstance(ic, blockicons.ForIcon):
        subsIcon = listicons.CprhForIcon(isAsync=ic.stmt == "async for",
            window=ic.window)
        tgtIcons = [tgtSite.att for tgtSite in ic.sites.targets]
        for _ in range(len(tgtIcons)):
            ic.replaceChild(None, 'targets_0')
        subsIcon.insertChildren(tgtIcons, 'targets', 0)
        if len(ic.sites.iterIcons) == 1:
            iterIcon = ic.childAt('iterIcons_0')
            ic.replaceChild(None, 'iterIcons_0')
        else:
            iterIcon = listicons.ListIcon(window=ic.window)
            iterEntries = [site.att for site in ic.sites.iterIcons]
            for _ in range(len(iterEntries)):
                ic.replaceChild(None, 'iterIcons_0')
            iterIcon.insertChildren(iterEntries, 'argIcons', 0)
        subsIcon.replaceChild(iterIcon, 'iterIcon')
    elif isinstance(ic, blockicons.IfIcon):
        subsIcon = listicons.CprhIfIcon(window=ic.window)
        condIcon = ic.childAt('condIcon')
        ic.replaceChild(None, 'condIcon')
        subsIcon.replaceChild(condIcon, 'testIcon')
    else:
        return None, None
    if ic.isSelected():
        subsIcon.select(True)
    subsIcons = [subsIcon]
    # If there was an entry icon attached to the right of the original icon, check to
    # see whether it contains additional comprehension clauses, and if so, add them to
    # the list of icons to substitute
    rightmostIc, rightmostSite = icon.rightmostSite(subsIcon)
    for parent in rightmostIc.parentage(includeSelf=True):
        if parent is subsIcon:
            break
        if isinstance(parent, entryicon.EntryIcon) and parent.text == '':
            pendingArgs = parent.listPendingArgs()
            cprhArgs = [a for a in pendingArgs if isinstance(a, (listicons.CprhForIcon,
                listicons.CprhIfIcon))]
            if len(cprhArgs) == len(pendingArgs) and len(cprhArgs) > 0:
                subsIcons += cprhArgs
                parent.popPendingArgs("all")
                parent.attachedIcon().replaceChild(None, parent.attachedSite())
                break
    # If the original icon owned a block-end icon and possibly a pass icon, inform the
    # caller that they will need to remove
    topIconsToRemove = []
    if hasattr(ic, 'blockEnd'):
        nextIc = ic.nextInSeq()
        if nextIc is not ic.blockEnd:
            topIconsToRemove.append(nextIc)  # Block can have 'pass' icon
        topIconsToRemove.append(ic.blockEnd)
    return subsIcons, topIconsToRemove

def _makePrunedCopy(topIcon, keepSet, forSeq):
    """Return a temporary-icon copy of topIcon with icons not in keepSet removed.  Stitch
    the tree back together in the same manner as removeIcons.Note the SEVERE
    restrictions on the use of temporary icons (see icon.temporaryDuplicate)."""
    # Create a full copy of the tree out of temporary icons.  The linkToOriginal option
    # adds a property (.copiedFrom) pointing back to the original.
    copiedTopIcon = topIcon.temporaryDuplicate(inclStmtComment=True, linkToOriginal=True)
    # Translate keepSet from a set of original icons to preserve, into a set of copied
    # icons to remove.
    deletedSet = {c for c in copiedTopIcon.traverse(inclStmtComment=True)
        if c.copiedFrom not in keepSet}
    # Use splitDeletedIcons to remove the unwanted icons and assemble the remaining ones
    # into a single coherent tree.
    stmtComment = copiedTopIcon.stmtComment if hasattr(copiedTopIcon, 'stmtComment') \
        else None
    needReorder = []
    remainingIcons, _, _ = expredit.splitDeletedIcons(copiedTopIcon, deletedSet, False,
        needReorder, None)
    if remainingIcons is None:
        prunedCopy = copiedTopIcon
    else:
        prunedCopy = expredit.placeListToTopLevelIcon(remainingIcons, forSeq, None)
    prunedCopy = expredit.reorderMarkedExprs(prunedCopy, needReorder)
    # If the top icon was removed, move the statement comment to the new top icon (or
    # convert it to a line comment if the entire statement was removed).
    if stmtComment is not None:
        if stmtComment in deletedSet:
            stmtComment.detachStmtComment()
        else:
            if prunedCopy is None:
                stmtComment = copiedTopIcon.stmtComment
                stmtComment.detachStmtComment()
                prunedCopy = stmtComment
            elif prunedCopy is not copiedTopIcon:
                stmtComment = copiedTopIcon.stmtComment
                stmtComment.detachStmtComment()
                stmtComment.attachStmtComment(prunedCopy)
    return prunedCopy

def flagIndividual(iter):
    """Wrapper for iterator in the same form as 'enumerate', that returns a flag
    indicating that iterator will only return a single value.  Why, you might ask?
    It is being used to avoid creating what would be a very long list in a performance
    critical operation (at least I think this will be more efficient)."""
    isFirstValue = True
    isSingleValue = True
    lastValue = None
    for value in iter:
        if isFirstValue:
            isFirstValue = False
        else:
            yield False, lastValue
            isSingleValue = False
        lastValue = value
    if lastValue is not None:
        yield isSingleValue, lastValue

def concatenateSequences(sequences):
    if len(sequences) == 0 or len(sequences) == 1 and len(sequences[0]) == 0:
        return None
    insertSeqStart = lastSeqStartIc = sequences[0][0]
    if not insertSeqStart.hasSite('seqOut'):
        entryIc = entryicon.EntryIcon(window=insertSeqStart.window)
        entryIc.appendPendingArgs([insertSeqStart])
        insertSeqStart = lastSeqStartIc = entryIc
    for seq in sequences[1:]:
        seqStartIc = seq[0]
        if not seqStartIc.hasSite('seqOut'):
            entryIc = entryicon.EntryIcon(window=seqStartIc.window)
            entryIc.appendPendingArgs([seqStartIc])
            seqStartIc = entryIc
        icon.insertSeq(seqStartIc, icon.findSeqEnd(lastSeqStartIc))
        lastSeqStartIc = seqStartIc
    return insertSeqStart, list(icon.traverseSeq(insertSeqStart))

def cvtSeqsToList(sequences):
    listElems = []
    strippedComments = []
    for seq in sequences:
        for ic in seq:
            if isinstance(ic, commenticon.VerticalBlankIcon):
                continue
            if ic.childAt('seqOut'):
                ic.replaceChild(None, 'seqOut')
            if isinstance(ic, listicons.TupleIcon) and ic.noParens:
                listElems += ic.argIcons()
                for _ in range(len(ic.sites.argIcons)):
                    ic.replaceChild(None, 'argIcons_0')
            else:
                listElems.append(ic)
            if hasattr(ic, 'stmtComment'):
                stmtComment = ic.stmtComment
                stmtComment.detachStmtComment()
                strippedComments.append(stmtComment)
    return listElems, strippedComments

class StreamToTextWidget:
    """Imitate an output text stream and append any text written to it to a specified
    Tkinter text widget."""
    def __init__(self, textWidget):
        self.widget = textWidget

    def write(self, str):
        self.widget.config(state=tk.NORMAL)
        self.widget.insert('end', str)
        self.widget.see('end')
        self.widget.config(state=tk.DISABLED)

    def flush(self):
        pass

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
    #cProfile.run('appData.mainLoop()', 'prof_stats')
