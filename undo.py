import cursors

class UndoRedoList:
    def __init__(self, window):
        self.window = window
        self.undoList = [Boundary(None)]  # Empty boundary removes cursor and entry icon
        self.redoList = []
        self._inUndo = False
        self._inRedo = False
        # for the first pass, deleted icons hang around as objects in the undo list
        # Eventually, these should be allowed to go away and the lists should contain
        # an abbreviated version of the icon (either shrunk or replaced with an id).
        #self.iconToId = {}
        #self.idToIcon = {}
        #self.currentId = 0

    def registerIconCreated(self, ic):
        self._addUndoRedoEntry(IconCreated(ic))
        #self.iconToId[self.currentId] = ic
        #self.idToIcon[ic] = self.currentId
        #self.currentId += 1

    def registerIconDelete(self, ic):
        self._addUndoRedoEntry(IconDeleted(ic))

    def registerRemoveFromTopLevel(self, ic, topOfSeq):
        self._addUndoRedoEntry(RemoveFromTopLevel(ic, topOfSeq))

    def registerAddToTopLevel(self, ic, newSeq):
        self._addUndoRedoEntry(AddToTopLevel(ic, newSeq))

    def registerAttach(self, parentIcon, siteId, origChild, childSite):
        self._addUndoRedoEntry(Attach(parentIcon, siteId, origChild, childSite))

    def registerInsertSeriesSite(self, ic, seriesName, insertIdx):
        self._addUndoRedoEntry(InsertSeriesSite(ic, seriesName, insertIdx))

    def registerRemoveSeriesSite(self, ic, seriesName, insertIdx):
        self._addUndoRedoEntry(RemoveSeriesSite(ic, seriesName, insertIdx))

    def registerCallback(self, callback, *args):
        self._addUndoRedoEntry(Callback(callback, args))

    def addBoundary(self):
        if len(self.undoList) > 0 and self.undoList[-1].__class__ is Boundary:
            # Don't record every keystroke, but rather capture the entry icon and cursor
            # on the brink of the operation to best allow user to correct a mistaken entry
            self.undoList[-1] = (Boundary(self.window))
        else:
            self.undoList.append(Boundary(self.window))
        # Typing (which is reflected only in addBoundary) is sufficient reason to
        # invalidate the redo list
        if not self._inRedo and not self._inUndo:
            self.redoList = []

    def undo(self):
        """Perform operations on the undo list until the next undo boundary"""
        self._inUndo = True
        self._undoOrRedoToBoundary(False)
        self._inUndo = False

    def redo(self):
        """Perform operations on the redo list until the next undo boundary"""
        self._inRedo = True
        self._undoOrRedoToBoundary(True)
        self._inRedo = False

    def _undoOrRedoToBoundary(self, isRedo):
        undoList = self.redoList if isRedo else self.undoList
        if len(undoList) == 0:
            cursors.beep()
            return
        #... I don't understand why I put the boundary before the operation, here.
        #    Normally, the convention is to put it at the end of an operation,
        #    particularly since the boundary caries cursor positioning information.
        if isRedo:
            self.undoList.append(Boundary(self.window))
        else:
            self.redoList.append(Boundary(self.window))
        if undoList[-1].__class__ is Boundary:
            undoList.pop(-1)
        while len(undoList) > 0:
            u = undoList.pop(-1)
            if u.__class__ is Boundary:
                u.restoreCursorAndEntryIcon(self.window)
                break
            redrawRect = u.undo(self)
            self.window.requestRedraw(redrawRect)
        else:
            listType = "Undo" if undoList is self.undoList else "Redo"
            #... I don't think the redo list is supposed to end in a boundary
            print("Warning:", listType, "list does not end in boundary")
            self.window.cursor.removeCursor()
        # Update dirty layouts and redraw the areas affected
        self.window.refreshDirty()

    def _addUndoRedoEntry(self, undoEntry):
        """Add undo entry to the appropriate list (undo or redo) based upon whether
        operations are being recorded in the context of processing an undo command,
        or driven by an an original operation or a redo operation.  Also clears the
        redo list if new operations are done outside of the context of undo/redo"""
        if self._inUndo:
            undoList =  self.redoList
        else:
            undoList = self.undoList
        undoList.append(undoEntry)
        if not self._inRedo and not self._inUndo:
            self.redoList = []

class UndoListEntry:
    pass

class Boundary:
    def __init__(self, window):
        if window is None:
            self.cursorType = None
            self.cursorWindow = None
            self.cursorPos = None
            self.cursorSite = None
            self.cursorIcon = None
            self.entryText = None
        else:
            cursor = window.cursor
            self.cursorType = cursor.type
            self.cursorWindow = cursor.window
            self.cursorPos = cursor.pos
            self.cursorIcon = cursor.icon
            self.cursorSite = cursor.site
            if window.cursor.type == "text":
                self.entryText = window.cursor.icon.text
            else:
                self.entryText = None

    def restoreCursorAndEntryIcon(self, window):
        cursor = window.cursor
        if self.cursorType is None:
            cursor.removeCursor(placeEntryText=False)
        elif self.cursorType == "window":
            cursor.setToWindowPos(self.cursorPos, placeEntryText=False)
        elif self.cursorType == "icon":
            cursor.setToIconSite(self.cursorIcon, self.cursorSite, placeEntryText=False)
        elif self.cursorType == "text":
            self.cursorIcon.restoreForUndo(self.entryText)
            cursor.setToText(self.cursorIcon, placeEntryText=False)

class Attach(UndoListEntry):
    def __init__(self, parentIcon, siteId, origChild, childSite):
        self.parentIcon = parentIcon
        self.siteId = siteId
        self.origChild = origChild
        self.childSite = childSite

    def undo(self, undoData):
        redrawRect = self.parentIcon.hierRect()
        self.parentIcon.sites.lookup(self.siteId).attach(self.parentIcon, self.origChild,
         self.childSite)
        self.parentIcon.markLayoutDirty()
        return redrawRect

class InsertSeriesSite(UndoListEntry):
    def __init__(self, ic, seriesName, idx):
        self.icon = ic
        self.seriesName = seriesName
        self.idx = idx

    def undo(self, undoData):
        self.icon.sites.removeSeriesSiteByNameAndIndex(self.icon, self.seriesName,
         self.idx)
        self.icon.markLayoutDirty()
        return None

class RemoveSeriesSite(UndoListEntry):
    def __init__(self, ic, seriesName, idx):
        self.icon = ic
        self.seriesName = seriesName
        self.idx = idx

    def undo(self, undoData):
        self.icon.sites.insertSeriesSiteByNameAndIndex(self.icon, self.seriesName,
         self.idx)
        self.icon.markLayoutDirty()
        return None

class IconCreated(UndoListEntry):
    def __init__(self, ic):
        self.iconClass = type(ic)

    def undo(self, window):
        return None

class IconDeleted(UndoListEntry):
    # For the moment, this does nothing.  Eventually, icons will actually be deleted
    # from memory (or at least shrunk), but these events are not even registered, yet.
    def __init__(self, ic):
        self.iconClass = type(ic)

    def undo(self, undoData):
        return None

class RemoveFromTopLevel(UndoListEntry):
    def __init__(self, ic, topOfSeq):
        self.icon = ic
        self.topOfSeq = topOfSeq

    def undo(self, undoData):
        parent = self.icon.parent()
        if parent is not None:
            # Remove any parent link from the icon before adding it to the top level.
            # I believe that the presence of such a link is benign, and happens when
            # the original operation rearranged icons before changing the top-level icon
            # (presumably a subsequent undo operation would have removed the link, but
            # not before addTopSingle issued an error about a "lingering parent").
            print('Undo RemoveFromTopLevel removing parent (is this normal?)')
            parentSite = self.icon.siteOf(parent)
            self.icon.replaceChild(None, parentSite)
        undoData.window.addTopSingle(self.icon, pos=self.topOfSeq, newSeq=self.topOfSeq)
        self.icon.markLayoutDirty()
        return None

class AddToTopLevel(UndoListEntry):
    def __init__(self, ic, newSeq):
        self.icon = ic
        self.newSeq = newSeq

    def undo(self, undoData):
        redrawRect = self.icon.rect
        undoData.window.removeTopSingle(self.icon, self.newSeq)
        return redrawRect

class Callback(UndoListEntry):
    # ... Note that this is going to stop working when icon deletion is added, since
    # this callback is being used from an icon.
    def __init__(self, callback, args):
        self.callback = callback
        self.args = args

    def undo(self, undoData):
        self.callback(*self.args)

class AccumRect:
    """Make one big rectangle out of all rectangles added."""
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if rect is None:
            return
        if self.rect is None:
            self.rect = rect
        else:
            l1, t1, r1, b1 = rect
            l2, t2, r2, b2 = self.rect
            self.rect =  min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)
