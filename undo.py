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
        """Undo boundaries mark the completion of a command and therefore define the
        granularity of the corresponding undo operation.  While boundaries usually
        correspond to the the end of a user command, they can also be tweaked to provide
        better flow.  For example, when a command ends with the insertion of an entry
        icon, the boundary can be shifted to between the end of the structural change
        and the entry icon insertion to keep the undo stream clean of unnecessary entry
        icons popping up and making it harder to see the actual code changes."""
        # Undo and redo processing inserts its own boundaries.  While callbacks don't
        # usually insert boundaries, better to ignore them if they do.
        if self._inRedo or self._inUndo:
            return
        # If this is a repeated boundary, give priority to the earlier boundary data.
        # (Prior code did the opposite but for reasons that are now obsolete.  As far as
        # I know, no upstream code actively depends on this ordering)
        if len(self.undoList) > 0 and self.undoList[-1].__class__ is Boundary:
            return
        self.undoList.append(Boundary(self.window))

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
        redoList = self.undoList if isRedo else self.redoList
        if len(undoList) == 0:
            cursors.beep()
            return
        # Strip off any boundary or boundaries at the end of the undo list
        while len(undoList) > 0 and isinstance(undoList[-1], Boundary):
            if len(undoList) == 1:
                cursors.beep()
                return  # List is empty except for a boundary, so leave it
            undoList.pop(-1)
        # When the redo list is cleared, it will have no boundary at the beginning, and
        # we need to provide one to establish cursor data for the end of the last redo
        if len(redoList) == 0:
            redoList.append(Boundary(self.window))
        # Perform the undo operations on the list until the next boundary.  Do not remove
        # the boundary, however, as it's still needed to separate subsequent operations.
        while len(undoList) > 0:
            if isinstance(undoList[-1], Boundary):
                undoList[-1].restoreCursorAndEntryIcon(self.window)
                break
            u = undoList.pop(-1)
            redrawRect = u.undo(self)
            self.window.requestRedraw(redrawRect)
        else:
            listType = "Undo" if undoList is self.undoList else "Redo"
            print("Warning:", listType, "list does not end in boundary")
            self.window.cursor.removeCursor()
        # While we were undoing, the opposite list was accumulating the records for
        # undoing/redoing the undo operation.  Top it off with a boundary
        redoList.append(Boundary(self.window))
        # Update dirty layouts and redraw the areas affected
        self.window.refreshDirty(addUndoBoundary=False, minimizePendingArgs=False)

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
            if cursor.type == "text" and cursor.icon.__class__.__name__ == 'EntryIcon':
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
            if self.cursorIcon.__class__.__name__ == 'EntryIcon':
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
        site = self.parentIcon.sites.lookup(self.siteId)
        if site is None:
            print(f"Undo holding non-existant site {self.siteId}, for icon "
                    f"{self.parentIcon.dumpName()}")
            return redrawRect
        site.attach(self.parentIcon, self.origChild, self.childSite)
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

class UndoNoOp:
    """Do-nothing version of UndoRedoList that window can swap-in so code can perform
    operations without recording."""
    # For now, all interaction with the UndoRedoList objects is in the form of calls
    # that return no values, so this weird object just accepts any arbitrary method call
    # and does nothing  May need to be more involved if the class interface changes.
    def __getattr__(self, name):
        return lambda *args, **kwargs: None
undoNoOp = UndoNoOp()