import typing

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

    def registerRemoveFromTopLevel(self, ic, fromX, fromY, index):
        self._addUndoRedoEntry(RemoveFromTopLevel(ic, fromX, fromY, index))

    def registerAddToTopLevel(self, ic):
        self._addUndoRedoEntry(AddToTopLevel(ic))

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
        self.redoList.append(Boundary(self.window))
        self._inUndo = True
        self._undoOrRedoToBoundary(self.undoList)
        self._inUndo = False

    def redo(self):
        """Perform operations on the redo list until the next undo boundary"""
        self.undoList.append(Boundary(self.window))
        self._inRedo = True
        self._undoOrRedoToBoundary(self.redoList)
        self._inRedo = False

    def _undoOrRedoToBoundary(self, undoList):
        if len(undoList) == 0:
            typing.beep()
            return
        if undoList[-1].__class__ is Boundary:
            undoList.pop(-1)
        redrawRegion = AccumRect()
        while len(undoList) > 0:
            u = undoList.pop(-1)
            if u.__class__ is Boundary:
                u.restoreCursorAndEntryIcon(self.window)
                break
            redrawRegion.add(u.undo(self))
        else:
            listType = "Undo" if undoList is self.undoList else "Redo"
            print("Warning:", listType, "list does not end in boundary")
            self.window.cursor.removeCursor()
        # Layouts may now be dirty
        redrawRegion.add(self.window.layoutDirtyIcons())
        # Redraw the areas affected by the updated layouts
        if redrawRegion.rect is not None:
            self.window.refresh(redrawRegion.rect)

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
            self.entryIcon = None
            self.entryText = None
        else:
            cursor = window.cursor
            self.cursorType = cursor.type
            self.cursorWindow = cursor.window
            self.cursorPos = cursor.pos
            self.cursorIcon = cursor.icon
            self.cursorSite = cursor.site
            self.entryIcon = window.entryIcon
            if self.entryIcon is None:
                self.entryText = None
            else:
                self.entryText = self.entryIcon.text

    def restoreCursorAndEntryIcon(self, window):
        cursor = window.cursor
        if self.cursorType is None:
            cursor.removeCursor()
        elif self.cursorType == "window":
            cursor.setToWindowPos(self.cursorPos)
        elif self.cursorType == "icon":
            cursor.setToIconSite(self.cursorIcon, self.cursorSite)
        elif self.cursorType == "text":
            cursor.setToEntryIcon()
        if self.entryIcon is None:
            window.entryIcon = None
        else:
            window.entryIcon = self.entryIcon
            window.entryIcon.restoreForUndo(self.entryText)
            cursor.setToEntryIcon()

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
        self.parentIcon.layoutDirty = True
        return redrawRect

class InsertSeriesSite(UndoListEntry):
    def __init__(self, ic, seriesName, idx):
        self.icon = ic
        self.seriesName = seriesName
        self.idx = idx

    def undo(self, undoData):
        self.icon.sites.removeSeriesSiteByNameAndIndex(self.icon, self.seriesName,
         self.idx)
        self.icon.layoutDirty = True
        return None

class RemoveSeriesSite(UndoListEntry):
    def __init__(self, ic, seriesName, idx):
        self.icon = ic
        self.seriesName = seriesName
        self.idx = idx

    def undo(self, undoData):
        self.icon.sites.insertSeriesSiteByNameAndIndex(self.icon, self.seriesName,
         self.idx)
        self.icon.layoutDirty = True
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
    def __init__(self, ic, fromX, fromY, idx):
        self.icon = ic
        self.fromX = fromX
        self.fromY = fromY
        self.index = idx

    def undo(self, undoData):
        undoData.window.addTop(self.icon, self.fromX, self.fromY, index=self.index)
        self.icon.layoutDirty = True
        return None

class AddToTopLevel(UndoListEntry):
    def __init__(self, ic):
        self.icon = ic

    def undo(self, undoData):
        redrawRect = self.icon.rect
        undoData.window.removeTop(self.icon)
        return redrawRect

class Callback(UndoListEntry):
    # ... Note that this is going to stop working when icon deletion is added, since
    # this callback is being used from an icon.
    def __init__(self, callback, args):
        self.callback = callback

    def undo(self, undoData):
        self.callback(*args)

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
