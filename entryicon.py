# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw
import re
import ast
import numbers
import comn
import iconlayout
import iconsites
import icon
import nameicons
import opicons
import blockicons
import listicons
import assignicons
import subscripticon
import parenicon
import infixicon
import stringicon
import cursors
import reorderexpr

PLAIN_BG_COLOR = (255, 245, 245, 255)
FOCUS_BG_COLOR = (255, 230, 230, 255)
OUTLINE_COLOR = (230, 230, 230, 255)

# Gap to be left between the entry icon and next icons to the right of it
ENTRY_ICON_GAP = 3

PEN_MARGIN = 6

compareOperators = {'<', '>', '<=', '>=', '==', '!='}
binaryOperators = {'+', '-', '*', '**', '/', '//', '%', '@', '<<', '>>', '&', '|', '^'}
unaryOperators = {'+', '-', '~', 'not'}
unaryNonKeywordOps = {'+', '-', '~'}
emptyDelimiters = {' ', '\t', '\n', '\r', '\f', '\v'}
delimitChars = {*emptyDelimiters, '(', ')', '[', ']', '}', ':', '.', ';', '@', '=', ',',
 '-', '+', '*', '/', '<', '>', '%', '&', '|', '^', '!'}
keywords = {'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield', 'await'}
noArgStmts = {'pass', 'continue', 'break', 'else', 'finally'}

identPattern = re.compile('^[a-zA-Z_][a-zA-Z_\\d]*$')
numPattern = re.compile('^([+-]?[\\d_]*\\.?[\\d_]*)|'
 '([+-]?((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*)?$')
attrPattern = re.compile('^\\.[a-zA-Z_][a-zA-Z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-Z\\d_.\\(\\[\\{\\s+-~"\']')
stringPattern = re.compile("^(f|fr|rf|b|br|rb|u|r)?['\"]$", re.IGNORECASE)

textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

penImage = comn.asciiToImage((
    "....oooo    ",
    "...o%%%%oo  ",
    "..o%%%%%%%oo",
    "..o%%%%%%%%%",
    ".o%%%%55%%%%",
    "o77777777%%%",
    ".o%%%%55%%%%",
    "..o%%%%%%%%%",
    "..o%%%%%%%oo",
    "...o%%%%oo  ",
    "....oooo    "))
dimPenImage = penImage.point(lambda p: p + 200)

attrPenImage = comn.asciiToImage((
    "....oooo...",
    "...o%%%%o..",
    "..o%%%%%%o.",
    ".o%%%%%%%%o",
    ".o%%%77%%%o",
    ".o%%%77%%%o",
    ".o%%7%%%%%o",
    "o%%7%%%%%o.",
    "o%7%%%%%o..",
    "o7%%oooo...",
    "oooo......."
))
dimAttrPenImage = attrPenImage.point(lambda p: p + 200)

class EntryIcon(icon.Icon):
    def __init__(self, initialString="", window=None, willOwnBlock=False,
     location=None):
        icon.Icon.__init__(self, window)
        self.text = initialString
        ascent, descent = icon.globalFont.getmetrics()
        self.height = ascent + descent + 2 * icon.TEXT_MARGIN + 1
        self.initTxtWidth = icon.globalFont.getsize("i")[0]
        self.txtWidthIncr = self.initTxtWidth
        x, y = location if location is not None else (0, 0)
        outSiteY = self.height // 2
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('attrOut', 'attrOut', 0, outSiteY + icon.ATTR_SITE_OFFSET)
        self.sites.add('seqIn', 'seqIn', 0, outSiteY)
        seqOutIndent = comn.BLOCK_INDENT if willOwnBlock else 0
        self.sites.add('seqOut', 'seqOut', seqOutIndent, outSiteY)
        width = self._width()
        self.sites.add('forCursor', 'attrIn', width, outSiteY + icon.ATTR_SITE_OFFSET,
            cursorOnly=True)
        self.rect = (x, y, x + width, y + self.height)
        self.markLayoutDirty()
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.setCursorPos('end')
        self.hasFocus = False
        self.focusChanged = False
        self.pendingArgListMgrs = {}
        # If the entry icon will own a code block, create a BlockEnd icon and link it in
        if willOwnBlock:
            self.blockEnd = icon.BlockEnd(self, window)
            self.sites.seqOut.attach(self, self.blockEnd)

    def restoreForUndo(self, text):
        """Undo restores all attachments and saves the displayed text.  Update the
        remaining internal state based on attachments and passed text."""
        self.text = text
        self.setCursorPos('end')
        self.recolorPending()
        self.markLayoutDirty()

    def _width(self, boxOnly=False):
        textWidth = icon.globalFont.getsize(self.text)[0]
        if textWidth > self.initTxtWidth:
            nIncrements = (textWidth - self.initTxtWidth) // self.initTxtWidth + 1
        else:
            nIncrements = 0
        adjWidth = self.initTxtWidth + nIncrements*self.txtWidthIncr
        boxWidth = adjWidth + 2 * icon.TEXT_MARGIN + 1 + PEN_MARGIN
        if boxOnly:
            return boxWidth
        return boxWidth + self.penOffset()

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None or self.focusChanged:
            boxWidth = self._width(boxOnly=True) - 1
            img = Image.new('RGBA', (comn.rectWidth(self.rect), self.height))
            bgColor = FOCUS_BG_COLOR if self.hasFocus else PLAIN_BG_COLOR
            draw = ImageDraw.Draw(img)
            draw.rectangle((self.penOffset(), 0, self.penOffset() - 1 + boxWidth - 1,
                self.height-1), fill=bgColor, outline=OUTLINE_COLOR)
            draw.text((self.textOffset, icon.TEXT_MARGIN), self.text,
                font=icon.globalFont, fill=(0, 0, 0, 255))
            if self.attachedToAttribute():
                nibTop = self.sites.attrOut.yOffset - attrPenImage.height + 2
                img.paste(attrPenImage if self.hasFocus else dimAttrPenImage,
                    box=(0, nibTop), mask=attrPenImage)
            else:
                nibTop = self.sites.output.yOffset - penImage.height // 2
                img.paste(penImage if self.hasFocus else dimPenImage, box=(0, nibTop),
                    mask=penImage)
            self.drawList = [((0, 0), img)]
            cntrSiteY = self.sites.output.yOffset
            for siteOrSeries in self.iteratePendingSiteList():
                if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                    listOffset = siteOrSeries[0].xOffset
                    layoutMgr = self.pendingArgListMgrs[siteOrSeries.name]
                    self.drawList += layoutMgr.drawListCommas(listOffset, cntrSiteY)
                    self.drawList += layoutMgr.drawSimpleSpine(listOffset, cntrSiteY)
            self.focusChanged = False
        self._drawFromDrawList(toDragImage, location, clip, style)

    def focusIn(self):
        if not self.hasFocus:
            self.focusChanged = True
            self.hasFocus = True
            self.markLayoutDirty()

    def focusOut(self, removeIfPossible=True):
        """Remove cursor focus from the icon.  If removeIfPossible is True, try to place
        the text as it currently stands, replacing the entry icon with whatever it
        generates.  Returns False only if removal was requested and current text or
        pending arguments prevent it from being placed.  If it succeeds, the cursor will
        be placed to the right of whatever icon(s) the text generated, as if a delimiter
        had been entered (while most callers will immediately override this, the
        arrowAction method depends upon this side effect for right-arrow cursor movement
        out of the icon).  It is important to note that because this function gets called
        as a result of cursor movement, the fact that it can rearrange icon structure has
        far-reaching consequences: all cursor-movement calls now need to be followed by
        layout/refresh/redraw."""
        if self.hasFocus:
            self.focusChanged = True
            self.hasFocus = False
            self.markLayoutDirty()
            # If both text and arguments can be placed, do so.  Note that this is a bit
            # hairy, because focus out is invoked via cursor movement calls, which are
            # plentiful, and which older code did not expect to be rearranging icons.
            if not removeIfPossible:
                return True
            # Start by at least making sure that the icon is still in the window
            topIcon = self.topLevelParentSafe()
            if topIcon is None or topIcon not in self.window.topIcons:
                return True
            if self.text == '':
                if self.remove():
                    return True
            if not self.canPlaceEntryText(requireArgPlacement=True):
                return False
            newText = self.text + ' '
            self._setText(newText, len(newText))
            return True

    def hasPendingArgs(self):
        """Return True if the entry icon has pending arguments."""
        # The 'forCursor' site will only exist if there are no pending arguments
        return not hasattr(self.sites, 'forCursor')

    def maxPendingArgIdx(self):
        """Pending args are named "pendingArgN", where N is derived from their position
        in the icon from which they were orphaned (empty sites being denoted by the lack
        of a pendingArgN site/series.  Return the index (N) of the last pending arg
        of the entry icon, or -1 if there are currently none."""
        rightmostSiteName = self.sites.lastCursorSite()
        if rightmostSiteName is None or rightmostSiteName == 'forCursor':
            return -1
        return self._splitPendingArgName(rightmostSiteName)[0]

    def minPendingArgIdx(self):
        firstSiteName = self.sites.firstCursorSite()
        if firstSiteName is None or firstSiteName == 'forCursor':
            return -1
        if iconsites.isSeriesSiteId(firstSiteName):
            firstSiteName = iconsites.splitSeriesSiteId(firstSiteName)[0]
        return self._splitPendingArgName(firstSiteName)[0]

    @staticmethod
    def _splitPendingArgName(siteId):
        """Splits a pending argument name (pendingArg<n> or pendingArg<n>_<i>) to get the
        pending arg index (<n>) and (for series sites), the series index.  Returns
        both values, with <i> being None if siteId is not a series site ID."""
        if iconsites.isSeriesSiteId(siteId):
            name, listIdx = iconsites.splitSeriesSiteId(siteId)
        else:
            name, listIdx = siteId, None
        return int(name[10:]), listIdx

    def appendPendingArgs(self, argList):
        """Add new entries to the entry icon's pending argument list.  Format is a list
        whose elements are either icons, lists/tuples of icons, or None.  Individual
        icons are expected to be from a non-series site, lists are icons from a site
        series, and None represents an individual site.  Nones can also appear in the
        icon lists, to represent an empty series site."""
        if len(argList) == 0:
            return
        startIdx = self.maxPendingArgIdx() + 1
        for i, arg in enumerate(argList):
            if arg is None:
                continue
            # Create a pending arg site or site series for arg
            if isinstance(arg, (tuple, list)):
                for ic in arg:
                    if ic is not None:
                        outSiteType = ic.parentSites()[0]
                        break
                else:  # In the unlikely case of a list of all None
                    outSiteType = 'output'
                isSeries = True
            else:
                outSiteType = arg.parentSites()[0]
                isSeries = False
            siteType = iconsites.matingSiteType[outSiteType]
            siteName = f"pendingArg{startIdx + i}"
            self.addPendingArgSite(startIdx + i, siteType, isSeries=isSeries)
            # Attach the icon(s) to the newly created site/series
            if isinstance(arg, (tuple, list)):
                for insertIdx, ic in enumerate(arg):
                    self.insertChild(ic, siteName, insertIdx)
                    _addHighlights(ic, 'highlightPend')
            else:
                self.replaceChild(arg, siteName)
                _addHighlights(arg, 'highlightPend')

    def popPendingArgs(self, argIdx, seriesIdx=None):
        """Remove pending arguments and sites from the left of the list.  argIdx is the
        index (<n> of pendingArgs<n>) of the last argument returned.  If that is a series
        argument, seriesIdx can be specified to return and trim up to and including that
        element of the series.  If argIdx refers to a series and seriesIdx is None, trims
        the entire series.  argIdx can also be set to "all" to remove all of the icon's
        pending arguments."""
        # Remove the arguments from the pending arg sites and unhighlight the attached
        # icons.  Make a list the sites or series to remove
        sitesToRemove = []
        if argIdx == "all":
            argIdx = self.maxPendingArgIdx()
        for siteOrSeries in self.iteratePendingSiteList():
            if siteOrSeries.order > argIdx:
                break
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                if siteOrSeries.order == argIdx and seriesIdx is not None:
                    # remove initial elements of list up to and including seriesIdx
                    removeSiteId = f'pendingArg{siteOrSeries.order}_0'
                    for i in range(seriesIdx + 1):
                        _removeHighlights(self.childAt(removeSiteId))
                        self.replaceChild(None, removeSiteId)
                    if sum(1 for s in siteOrSeries if s.att is not None) == 0:
                        # No remaining children in the series, remove the site series
                        sitesToRemove.append(siteOrSeries)
                    break
                else:
                    # Remove entire list
                    for i in range(len(siteOrSeries)):
                        removeSiteId = f'pendingArg{siteOrSeries.order}_{i}'
                        _removeHighlights(self.childAt(removeSiteId))
                        self.replaceChild(None, removeSiteId, leavePlace=True)
            else:
                removeSiteId = f'pendingArg{siteOrSeries.order}'
                _removeHighlights(self.childAt(removeSiteId))
                self.replaceChild(None, removeSiteId)
            sitesToRemove.append(siteOrSeries)
        # Remove the sites holding the icons to be returned (removePendingArgSite will
        # also restore the 'forCursor' site upon removal of the last site).
        for site in sitesToRemove:
            self.removePendingArgSite(site.order)
        # Renumber the remaining sites to start from 0
        minIdx = self.minPendingArgIdx()
        if minIdx in (-1, 0):
            return
        for site in list(self.iteratePendingSiteList()):
            self.renamePendingArgSite(site.order, site.order-minIdx)

    def addPendingArgSite(self, idx, siteType, isSeries):
        """Add a pending argument site of type siteType at index idx to the entry icon.
        Note that this is not an "insert" call, the caller is expected to ensure that
        the requested site does not already exist.  If it does, the call will print a
        warning and do nothing."""
        newSiteName = f"pendingArg{idx}"
        if hasattr(self.sites, newSiteName):
            print(f'addPendingArgSite called on already existing site {newSiteName}')
            return
        if not self.hasPendingArgs():
            # Entry icon had no existing pending argument sites: remove 'forCursor' site
            self.sites.remove('forCursor')
        y = self.sites.output.yOffset
        x = 0  # Will be filled in by layout
        if isSeries:
            self.pendingArgListMgrs[newSiteName] = \
                iconlayout.ListLayoutMgr(self, newSiteName, x, y, simpleSpine=True,
                    cursorTraverseOrder=idx)
        elif siteType == 'attrIn':
            self.sites.add(newSiteName, siteType, x, y + icon.ATTR_SITE_OFFSET,
                cursorTraverseOrder=idx)
        else:
            self.sites.add(newSiteName, siteType, x, y, cursorTraverseOrder=idx)
        self.window.undo.registerCallback(self.removePendingArgSite, idx)

    def removePendingArgSite(self, idx):
        """Remove a pending arg site.  Does not renumber remaining arguments (use
        popPendingArgs to remove from the left per placement)"""
        siteName = f"pendingArg{idx}"
        site = getattr(self.sites, siteName)
        if site is None:
            print(f'removePendingArgSite called to remove non-existant site {siteName}')
            return
        if isinstance(site, iconsites.IconSite):
            isSeries = False
            self.sites.remove(siteName)
        else:
            isSeries = True
            seriesLen = len(site)
            if seriesLen > 1:
                # While callers are accustomed to removing arguments, they won't
                # necessarily remove the empty sites, and we need them gone, because our
                # undo callback, addPendingArgSite, does not restore sites.
                for _ in range(seriesLen):
                    self.replaceChild(None, siteName + '_0')
            self.sites.removeSeries(siteName)
            del self.pendingArgListMgrs[siteName]
        # If this is the last pending argument, restore the 'forCursor' site (note that
        # we can't use hasPendingArgs() to do this test, as it looks for 'forCursor')
        if self.sites.firstCursorSite() is None:
            self.sites.add('forCursor', 'attrIn', self._width(),
                self.height // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True)
        self.window.undo.registerCallback(self.addPendingArgSite, idx, site.type,
            isSeries)

    def renamePendingArgSite(self, oldIdx, newIdx):
        """Pending argument sites are named by their position (pendingArg<n>...), and
        need to be renumbered when arguments are removed by popPendingArgs (or for undo
        to reverse that action).  This call changes the index number of a pending
        argument site, as well as its cursor-traversal order.  The new index must be
        currently unused."""
        oldName = f"pendingArg{oldIdx}"
        newName = f"pendingArg{newIdx}"
        site = getattr(self.sites, oldName)
        if isinstance(site, iconsites.IconSite):
            self.sites.renameSite(oldName, newName)
        else:
            listMgr = self.pendingArgListMgrs[oldName]
            del self.pendingArgListMgrs[oldName]
            self.pendingArgListMgrs[newName] = listMgr
            listMgr.rename(newName)
        site.order = newIdx
        self.window.undo.registerCallback(self.renamePendingArgSite, newIdx, oldIdx)

    def minimizePendingArgs(self):
        """Unload as much data as possible from pendingArgs by moving the entry icon down
        in the hierarchy (possibly resulting in arithmetic reordering), and offloading
        series elements to an accepting parent."""
        if not self.hasPendingArgs():
            return
        pendingArgs = self.listPendingArgs()
        # Check if right pending arg is a list whose arguments can be unloaded to a
        # parent list.  If so, move all but the first element to the parent and set the
        # pending arg to whatever its first element was (and don't return, yet, since
        # more optimization may still be possible)
        if isinstance(pendingArgs[-1], (tuple, list)) and len(pendingArgs[-1]) > 1 and \
                not hasattr(self, 'blockEnd'):
            pendSiteId = self.sites.lastCursorSite()
            pendSeriesName, _ = iconsites.splitSeriesSiteId(pendSiteId)
            recipient = transferToParentList(self, 1, self, seriesSiteName=pendSeriesName)
            if recipient is not None:
                # Unhighlight the pending args transferToParentList removed
                transferredArgs = pendingArgs[-1][1:]
                for ic in transferredArgs:
                    _removeHighlights(ic)
                # Turn the series to a single input site containing just the first element
                firstArg = pendingArgs[-1][0]
                lastArg = transferredArgs[-1]
                self.popPendingArgs("all")
                self.appendPendingArgs(pendingArgs[:-1] + [firstArg])
                if recipient is not self.parent():
                    # The entry icon is part of an arithmetic expression that must be
                    # split around it.
                    lastArgSite = recipient.siteOf(lastArg)
                    recipientLeftSite = recipient.siteOf(self, recursive=True)
                    recipient.replaceChild(None, lastArgSite, leavePlace=True)
                    if self.attachedToAttribute():
                        splitAt = icon.findAttrOutputSite(self.attachedIcon())
                    else:
                        splitAt = self
                    left, right = splitExprAtIcon(splitAt, recipient, splitAt, lastArg)
                    recipient.replaceChild(left, recipientLeftSite)
                    recipient.replaceChild(right, lastArgSite)
                    reorderexpr.reorderArithExpr(left)
                    reorderexpr.reorderArithExpr(right)
                    self.recolorPending()
        # Check if the entry icon can be moved lower in the expression hierarchy.  If so,
        # rearrange expression to make that happen
        if len(pendingArgs) != 1 or not self.hasSite('pendingArg0') or \
                isinstance(self.sites.pendingArg0, iconsites.IconSiteSeries) or \
                self.sites.pendingArg0.type != 'input':
            return
        pendingArg = self.childAt('pendingArg0')
        if pendingArg is None:
            return
        coincSite = pendingArg.hasCoincidentSite()
        if coincSite is None:
            return
        lowestIc, lowestSite = iconsites.lowestCoincidentSite(pendingArg, coincSite)
        lowestArg = lowestIc.childAt(lowestSite)
        # If the leftmost site in pendingArg is empty and we're attached to an icon that
        # we could put directly in to that site, replace the attached icon with
        # pendingArg and put our attached icon (and us with it) into the empty site that
        # was on our pending argument, but is now above us.  If the leftmost pending arg
        # site is occupied or not compatible, replace pending arg 0 with the content of
        # the site (lowestArg) and move the rest of the expression above us in to the
        # expression to which we are attached.
        if lowestArg is None and (self.attachedIcon() is None or
                self.attachedToAttribute()):
            # Empty site is available, can move the entire pending arg above us
            self.popPendingArgs(0)
        else:
            # lowestSite is not empty, can move just the expression above it
            if lowestIc is pendingArg:
                return
            _removeHighlights(pendingArg)
            lowestIc.replaceChild(None, lowestSite)
            self.replaceChild(lowestArg, 'pendingArg0')
        if self.attachedSiteType() == 'attrIn':
            outIc = icon.findAttrOutputSite(self.attachedIcon())
        else:
            outIc = self
        outIc.replaceWith(pendingArg)
        lowestIc.replaceChild(outIc, lowestSite)
        reorderexpr.reorderArithExpr(pendingArg)
        self.recolorPending()

    def iteratePendingSiteList(self):
        """Iterate over pending arguments in the site list, yielding site list entries
        which are either IconSite or IconSiteSeries objects."""
        siteId = self.sites.firstCursorSite()
        if siteId == 'forCursor':
            return
        if iconsites.isSeriesSiteId(siteId):
            seriesName = iconsites.splitSeriesSiteId(siteId)[0]
            site = getattr(self.sites, seriesName)
        else:
            site = getattr(self.sites, siteId)
        while True:
            yield site
            site = self.sites.nextTraversalSiteOrSeries(site.order)
            if site is None:
                return

    def listPendingArgs(self, compress=False):
        """Create a list of pending arg icons in the form accepted by the icon methods
        placeArgs and canPlaceArgs.  If compress is set to True, empty (non-series)
        sites, which would have been set to None in the list, are skipped"""
        argList = []
        currentIdx = 0
        for siteOrSeries in self.iteratePendingSiteList():
            if not compress:
                # Empty sites are denoted by gaps in site naming
                while siteOrSeries.order > currentIdx:
                    argList.append(None)
                    currentIdx += 1
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                listArgs = [site.att for site in siteOrSeries]
                argList.append(listArgs)
            else:
                argList.append(siteOrSeries.att)
            currentIdx += 1
        return argList

    def attachedIcon(self):
        outIcon = self.sites.output.att
        if outIcon is not None:
            return outIcon
        attrIcon = self.sites.attrOut.att
        if attrIcon is not None:
            return attrIcon
        return None

    def attachedSite(self):
        attIcon = self.attachedIcon()
        if attIcon is None:
            return None
        return attIcon.siteOf(self)

    def attachedSiteType(self):
        attIcon = self.attachedIcon()
        if attIcon is None:
            return None
        return attIcon.typeOf(attIcon.siteOf(self))

    def addText(self, char):
        """Add a character at the cursor.  If that resulted in changes to the icon
        structure in the window, also adds an undo boundary.  Note that while most
        commands add an undo boundary after all icon manipulation is finished, addText
        only adds one if it modified the icon structure, and may make changes to the
        icon structure *after* adding the boundary, leaving the undo stack
        "unterminated".  This also handles spaces, as both a command to complete the
        current entry, and as in internal space following "async" and 'not"."""
        if char == ' ' and not (self.text[:3] == 'not' and self.cursorPos == 3 and
                self.attachedToAttribute() or
                self.text[:5] in ('async', 'yield') and self.cursorPos == 5):
            # Move the space to the end to turn it in to command to delimit from any
            # cursor position.  Note above the exceptions for "async" and "not".  In
            # these cases the user needs to be able to be able to insert an internal
            # space in the text, so we can't take this action.
            newText = self.text + char
            newCursorPos = len(newText)
        else:
            newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
            newCursorPos = self.cursorPos + len(char)
        if not self._setText(newText, newCursorPos):
            # the resulting text was rejected.  If cursorPos was as the end of the
            # entry (or space was typed to add a delimiter), beep and do not update.
            # If not, just enter the updated text
            if newCursorPos == len(newText):
                if char == ' ':
                    # User added space delimiter.  If we had something that would
                    # otherwise have been self delimiting, try again w/o the delimiter.
                    if not self._setText(newText[:-1], newCursorPos-1):
                        cursors.beep()
                        return
                else:
                    # Beep and prohibit the character
                    cursors.beep()
                    return
            else:
                # Allow insertion, even though it's bad, because user is "editing", and
                # may go through bad states to get to good ones.
                self.text = newText
                self.cursorPos = newCursorPos
        if self.window.cursor.type == "text" and self.window.cursor.icon is self:
            # Currently we're not coloring based on text, but may want to restore later
            self.recolorPending()

    def backspaceInText(self, evt=None):
        if self.text != "" and self.cursorPos != 0:
            # Erase the character before the text cursor
            self.window.requestRedraw(self.topLevelParent().hierRect())
            self.text = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
            self.cursorPos -= 1
            self.markLayoutDirty()
            return
        if self.text == '':
            # Icon has no text.  Try to place pending args and remove
            if self.remove(makePlaceholder=True):
                return
        # Text cursor is at the left edge of the text field.
        cursor = self.window.cursor
        # If we can place the entry text and pending args, simply focus out and move the
        # cursor one site back (since _setText is designed to place the cursor *after*
        # what was typed, rather than before.
        if self.canPlaceEntryText(requireArgPlacement=True):
            newText = self.text + ' '
            self._setText(newText, len(newText))
            if cursor.type == 'icon':
                ic, site = cursors.lexicalTraverse(cursor.icon, cursor.site, 'Left')
                cursor.setToIconSite(ic, site)
            return
        # If we can't focus out, backspace in to the next icon.  This is done by
        # temporarily removing the text cursor from the entry icon and putting an icon
        # cursor on the site to which it is currently attached, then calling the
        # backspace method for the icon.  If this results in a new entry icon, reconcile
        # that with the content of self.
        highestIcon = iconsites.highestCoincidentIcon(self)
        parent = highestIcon.parent()
        if parent is None:
            return  # Can't place and can't back up any further
        cursor.setToIconSite(parent, parent.siteOf(highestIcon),
            placeEntryText=False)
        cursor.icon.backspace(cursor.site, evt)
        # If the icon backspace method created an entry icon at the cursor, it will
        # put a text cursor in it.  If not, the original entry icon should still be in
        # the right place, and we can simply move the cursor back in to it and be done.
        if cursor.type != "text":
            cursor.setToText(self)
            return
        # The backspace method created a new entry icon.  Since the existing entry icon
        # (self) was the first thing to the right of the cursor, it should now be the
        # first pending argument of the new entry icon.  If it's not, print a warning
        # and give up.
        newEntryIcon = cursor.icon
        if not isinstance(newEntryIcon, EntryIcon):
            print('Entry icon backspaceInText: Unexpected text icon from backspace')
            return
        if not hasattr(newEntryIcon.sites, 'pendingArg0'):
            print('Entry icon backspaceInText: Entry icon site not found')
            return
        newPendingArgs = newEntryIcon.listPendingArgs()
        oldEntryIcon, oldIdx, oldSeriesIdx = icon.firstPlaceListIcon(newPendingArgs)
        if oldEntryIcon is not highestIcon:
            print('Entry icon backspaceInText: Entry icon not recovered')
            return
        # Combine the two entry icons' text and arguments in to the new icon
        self.window.requestRedraw(self.topLevelParent().hierRect())
        oldPendingArgs = self.listPendingArgs()
        self.popPendingArgs("all")
        newEntryIcon.popPendingArgs(oldIdx, oldSeriesIdx)
        newPendingArgs = newEntryIcon.listPendingArgs()
        newEntryIcon.popPendingArgs("all")
        newText = newEntryIcon.text + self.text
        if highestIcon is self:
            # Use the entry icon created by the backspace operation
            newEntryIcon.appendPendingArgs(oldPendingArgs + newPendingArgs)
            newEntryIcon.text = newText
            combinedEntryIcon = newEntryIcon
            # (no need to set cursor, as we've already confirmed it's set to entry icon)
        elif hasattr(newEntryIcon, 'blockEnd') and \
                newEntryIcon.nextInSeq() is not newEntryIcon.blockEnd:
            # Need to use the new entry icon because it owns a non-empty block (the user
            # backspaced in to a block-owning icon), but the old entry icon is embedded
            # in an expression, so we might have to leave a hole.  We know the old entry
            # icon is on the left edge of the expression, so we don't need to do any
            # expression splitting, and can simply replace it in the expression with its
            # its last pending argument (provided that's compatible with an input site).
            # If we then replace the last element of oldPendingArgs with the integrated
            # expression, we can proceed as in the previous case to concatenate the two
            # sets of pending args on to the new entry icon.
            oldParent = self.attachedIcon()
            oldParentSite = self.attachedSite()
            oldParent.replaceChild(None,oldParentSite)
            lastPendingArg = oldPendingArgs[-1]
            if isinstance(lastPendingArg, (list, tuple)):
                lastPendingArg = lastPendingArg[-1]
                oldPendingArgs[-1][-1] = highestIcon
                oldParent.replaceChild(lastPendingArg, oldParentSite)
                reorderexpr.reorderArithExpr(highestIcon)
            elif lastPendingArg is None or lastPendingArg.hasSite('output'):
                oldPendingArgs[-1] = highestIcon
                oldParent.replaceChild(lastPendingArg, oldParentSite)
                reorderexpr.reorderArithExpr(highestIcon)
            else:
                oldPendingArgs.append(highestIcon)
            newEntryIcon.appendPendingArgs(oldPendingArgs + newPendingArgs)
            newEntryIcon.text = newText
            combinedEntryIcon = newEntryIcon
        else:
            # The existing entry icon is embedded in an expression.  Use it so it can
            # retain its position within the the expression and not leave a hole.
            self.appendPendingArgs(oldPendingArgs + newPendingArgs)
            newEntryIcon.replaceWith(highestIcon)
            self.text = newText
            self.cursorPos = len(newEntryIcon.text)
            self.window.cursor.setToText(self)
            combinedEntryIcon = self
        # There are actually a small number cases where the pending args can now be
        # placed from the combined entry icon (... it's also possible that there are
        # cases where the text can also be placed, but I don't know what they are and
        # don't want to deal with that until there's an actual use case)
        if combinedEntryIcon.text == "":
            self.window.cursor.icon.remove()

    def forwardDelete(self, evt=None):
        if self.text != "" and self.cursorPos != len(self.text):
            # Erase the character after the text cursor
            self.window.requestRedraw(self.topLevelParent().hierRect())
            self.text = self.text[:self.cursorPos] + self.text[self.cursorPos+1:]
            self.markLayoutDirty()
            return
        if self.text == '':
            # Icon has no text.  Try to place pending args and remove
            if self.remove(makePlaceholder=True):
                return
        # Text cursor is at the right edge of the text field.  Find the next icon (which
        # may or may not be a pending argument) and call its becomeEntryIcon method.
        cursor = self.window.cursor
        rightIcon, rightSite = cursors.lexicalTraverse(cursor.icon,
            self.sites.firstCursorSite(), 'Right')
        if rightIcon is None:
            return
        rightIcIsPendingArg = self.siteOf(rightIcon, recursive=True) is not None
        entryIc = rightIcon.becomeEntryIcon(siteAfter=rightSite)
        if entryIc is None:
            # Next icon didn't have or wasn't able to process becomeEntryIcon method.
            # Some of these cases could be useful, such as for converting normal
            # parens to call parens, but for now, just try to focus out and beep and
            # do nothing if we can't
            if self.canPlaceEntryText(requireArgPlacement=True):
                if not self._setText(self.text + ' ', len(self.text)):
                    cursors.beep()
            else:
                cursors.beep()
            return
        # We successfully transformed the icon to the right into an entry icon.  Merge
        # the text from this icon into the new entry icon.  If the new icon was or was
        # part of a pending arg, replace self with the pending arg (even if it's not at
        # the top of the hierarchy, we know the new entry icon is at the left edge).  If
        # the new entry icon was not a pending arg, it will either be attached to our
        # forCursor site, or held by a common ancestor.
        entryIc.text = self.text + entryIc.text
        entryIc.setCursorPos('end')
        if rightIcIsPendingArg:
            ic, idx, seriesIdx = icon.firstPlaceListIcon(self.listPendingArgs())
            self.popPendingArgs(idx, seriesIdx)
            self.replaceWith(ic)
        else:
            entryIcSiteOnSelf = self.siteOf(entryIc, recursive=True)
            if entryIcSiteOnSelf is not None:
                entryIcTopIc = self.childAt(entryIcSiteOnSelf)
                self.replaceChild(None, entryIcSiteOnSelf)
                self.replaceWith(entryIcTopIc)
            else:
                self.remove()
        cursor.setToText(entryIc)

    def arrowAction(self, direction):
        cursor = self.window.cursor
        cursor.erase()
        if direction == "Left":
            if self.cursorPos == 0:
                # Move the cursor out of the entry icon.
                if self.attachedIcon() is None:
                    # If we're at the top level, use focusOut, which will leave the
                    # cursor somewhere on the icon structure, or if it was completely
                    # empty, at a proper window position.
                    if self.focusOut():
                        if cursor.type == 'icon':
                            topIcon = cursor.icon.topLevelParent()
                            topSite = cursors.topSite(topIcon, seqDown=False)
                            cursor.setToIconSite(topIcon, topSite)
                    else:
                        # focusOut failed to place
                        cursor.setToIconSite(self, "output")
                else:
                    self.window.cursor.setToIconSite(self.attachedIcon(),
                        self.attachedSite())
                self.window.refreshDirty(minimizePendingArgs=False)
            else:
                self.cursorPos -= 1
        elif direction == "Right":
            if self.cursorPos == len(self.text):
                # Move cursor out of entry icon.  For right cursor movement, use the
                # focusOut because it leaves the cursor after the new icon(s)
                if not self.focusOut():
                    # We failed to place, cursor is still in icon
                    cursor.setToIconSite(self, self.sites.firstCursorSite())
                self.window.refreshDirty(minimizePendingArgs=False)
            else:
                self.cursorPos += 1
        cursor.draw()

    def remove(self, forceDelete=False, makePlaceholder=False):
        """Removes the entry icon and replaces it with it's pending argument(s) (if
        possible).  If all of the pending items cannot be put in place of the entry icon,
        does nothing and returns False unless either forceDelete or makePlaceholder are
        True.  In the forceDelete case, any pending args that can be placed are placed,
        and the remaining ones are deleted along with the entry icon.  In the
        makePlaceholder case, if one or more pending arguments can be placed, make a
        placeholder entry icon to hold the remaining ones and attach it to the right of
        the last argument placed."""
        attachedIcon = self.attachedIcon()
        attachedSite = self.attachedSite()
        redrawRect = self.rect
        if attachedIcon is None:
            # Entry icon is at top level
            if self.hasPendingArgs():
                # Start by trying to place on a naked tuple (which is our only way to
                # place multiple args when the entry icon is on the top level).  If that
                # succeeds and places more than a single icon, proceed with stitching in
                # the tuple.  If it places just one input, throw away the tuple and try
                # to place the input.  If it fails to place anything on the naked tuple,
                # we assume there are site types other than "output", so try to place
                # that on the top level.
                nakedTuple = listicons.TupleIcon(self.window, noParens=True)
                canPlaceAllOnTuple = self._canPlacePendingArgs(nakedTuple, 'argIcons_0',
                    useAllArgs=True)
                if canPlaceAllOnTuple:
                    canPlaceSomeOnTuple = True
                else:
                    canPlaceSomeOnTuple = self._canPlacePendingArgs(nakedTuple,
                        'argIcons_0', useAllArgs=False)
                if canPlaceSomeOnTuple and not canPlaceAllOnTuple and not forceDelete \
                        and not makePlaceholder:
                    # We know that the first arg is an input, but we are not allowed to
                    # delete or make a placeholder and there are further args that can't
                    # be placed on the tuple, so we need to give up.
                    return False
                if canPlaceAllOnTuple or canPlaceSomeOnTuple and (forceDelete or
                        makePlaceholder):
                    self._placePendingArgs(nakedTuple, 'argIcons_0')
                    # Succeeded placing on naked tuple.  If it placed more than a single
                    # element, use the tuple.  If not, just use the first element.
                    if len(nakedTuple.sites.argIcons) > 1:
                        self.window.replaceTop(self, nakedTuple)
                        self.window.cursor.setToIconSite(nakedTuple, 'argIcons_0')
                    else:  # Single element
                        firstArg = nakedTuple.childAt('argIcons_0')
                        nakedTuple.replaceChild(None, 'argIcons_0')
                        self.window.replaceTop(self, firstArg)
                        firstArg.markLayoutDirty()
                        self.window.cursor.setToBestCoincidentSite(firstArg, "output")
                elif not self.childAt('seqIn') and (not self.childAt('seqOut')
                        or isinstance(self.childAt('seqOut'), icon.BlockEnd)):
                    # We know that the first item was not an input (because we could not
                    # place it on a naked tuple.  If the entry icon is not part of a
                    # sequence, we can still place any sort of icon on the top level.
                    pendingArgList = self.listPendingArgs()
                    firstArg, firstArgIdx, firstArgSeriesIdx = icon.firstPlaceListIcon(
                        self.listPendingArgs())
                    isSingleArg =  firstArgIdx == len(pendingArgList) - 1 and \
                        firstArgSeriesIdx is None
                    if forceDelete or makePlaceholder or isSingleArg:
                        # Place the first argument on the top level
                        self.popPendingArgs(firstArgIdx, firstArgSeriesIdx)
                        self.window.replaceTop(self, firstArg)
                        parentSites = firstArg.parentSites()
                        if parentSites:
                            self.window.cursor.setToIconSite(firstArg, parentSites[0])
                        if makePlaceholder and not isSingleArg:
                            rightmostIcon, rightmostSite = icon.rightmostSite(firstArg)
                            rightmostIcon.replaceChild(self, rightmostSite)
                    else:
                        # We would have been able to place the first pending argument on
                        # the top level, but there are more pending arguments that we're
                        # not allowed to delete or add to a placeholder, so give up.
                        return False
                else:
                    # The entry icon is part of a sequence, and the first pending
                    # argument can not be part of a sequence, so give up on placing args
                    # and either dump all of them (if forceDelete is True), or give up
                    # and return False (if forceDelete is False).  This is done
                    # regardless of makePlaceholder, as it's the first arg that failed.
                    if not forceDelete:
                        return False
                    prevIcon = self.prevInSeq()
                    nextIcon = self.nextInSeq()
                    self.window.removeIcons([self])
                    if prevIcon:
                        self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                    elif nextIcon and nextIcon is not self.blockEnd:
                        self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                    else:
                        self.window.cursor.setToWindowPos(self.posOfSite('output'))
            else:
                # No pending arguments
                prevIcon = self.prevInSeq()
                nextIcon = self.nextInSeq()
                if hasattr(self, 'blockEnd'):
                    self.window.removeIcons([self, self.blockEnd])
                else:
                    self.window.removeIcons([self])
                if prevIcon:
                    self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                elif nextIcon and nextIcon is not self.blockEnd:
                    self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                else:
                    self.window.cursor.setToWindowPos(self.posOfSite('output'))
        else:
            # Entry icon is attached to another icon.  Use the _placePendingArgs method
            # to check and place the pending args (so this code can be shared with
            # _setText which needs to do the exact same thing).
            if not self._canPlacePendingArgs(attachedIcon, attachedSite,
                    overwriteStart=True, useAllArgs=True):
                if not forceDelete:
                    return False
            self._placePendingArgs(attachedIcon, attachedSite, overwriteStart=True)
            # If the entry icon is still attached somewhere, remove it
            if self.attachedIcon() is not None:
                self.attachedIcon().replaceChild(None, self.attachedSite(),
                    leavePlace=True)
            # Place the cursor where the entry icon was
            if attachedIcon.hasSite(attachedSite):
                self.window.cursor.setToIconSite(attachedIcon, attachedSite)
            else:  # The last element of list can disappear when entry icon is removed
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(attachedSite)
                newSite = iconsites.makeSeriesSiteId(seriesName, seriesIdx - 1)
                self.window.cursor.setToIconSite(attachedIcon, newSite)
        self.window.requestRedraw(redrawRect)
        return True

    def removeIfEmpty(self):
        """Remove the icon if it has no text and no pending arguments."""
        if self.text == '' and not self.hasPendingArgs():
            self.remove()

    def parseEntryText(self, newText):
        """Parse proposed text for the entry icon.  Returns three values: 1) the parse
        result, one of "accept", "reject", "typeover", "comma", "colon", "openBracket",
        "end"bracket" "openBrace", "endBrace", "openParen", "endParen", "makeFunction",
        "makeSubscript", or a pair of a created icon and delimiter.  1) If the text was
        processed by a per-icon textHandler method, the responsible icon, 3) A boolean
        value indicating that the text represents a statement that needs to be prepended
        to the attached icon, as opposed to being inserted at the site."""
        if self.attachedToAttribute():
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=True)
            if parseResult is None:
                parseResult = parseAttrText(newText, self.window)
        elif self.attachedIcon() is None or self.attachedSite() in ('seqIn', 'seqOut'):
            handlerIc = None
            parseResult = parseTopLevelText(newText, self.window)
        else:  # Currently no other cursor places, must be expr
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=False)
            if parseResult is None:
                parseResult = parseExprText(newText, self.window)
        if parseResult == "reject" and self.attachedSiteType() == 'input':
            coincidentSite = self.attachedIcon().hasCoincidentSite()
            if coincidentSite is not None and coincidentSite == self.attachedSite() and \
                    iconsites.highestCoincidentIcon(self.attachedIcon()).parent() is None:
                # Site is coincident with the start of the statement. We might be able to
                # prepend a top-level statement
                altParseResult = parseTopLevelText(newText, self.window)
                if len(altParseResult) == 2 and \
                        altParseResult[0].__class__ in cursors.stmtIcons:
                    return altParseResult, handlerIc, True
        return parseResult, handlerIc, False

    def _setText(self, newText, newCursorPos):
        """Process the text in the icon, possibly creating or rearranging the icon
        structure around it."""
        parseResult, handlerIc, prepend = self.parseEntryText(newText)
        # print('parse result', parseResult)
        if parseResult == "reject":
            self.removeIfEmpty()
            return False
        self.window.requestRedraw(self.topLevelParent().hierRect(),
            filterRedundantParens=True)
        if parseResult == "accept":
            self.text = newText
            self.window.cursor.erase()
            self.cursorPos = newCursorPos
            self.window.cursor.draw()
            self.markLayoutDirty()
            return True
        elif parseResult == "typeover":
            if not self.hasPendingArgs():
                self.remove(forceDelete=True)
                siteBefore, siteAfter, text, idx = handlerIc.typeoverSites()
                if not handlerIc.setTypeover(1, siteAfter):
                    # Single character typeover, set cursor to site after typeover
                    self.window.cursor.setToIconSite(handlerIc, siteAfter)
                else:
                    self.window.cursor.setToTypeover(handlerIc)
            else:
                print('parseEntryText detected typeover, but entry icon has pending args')
            return True
        elif parseResult == "comma":
            if not self.insertComma():
                self.removeIfEmpty()
                return False
            else:
                self.window.undo.addBoundary()
                return True
        elif parseResult == "colon":
            if not self.insertColon():
                self.removeIfEmpty()
                return False
            else:
                self.window.undo.addBoundary()
                return True
        elif parseResult == "openBracket":
            self.insertOpenParen(listicons.ListIcon)
            self.window.undo.addBoundary()
            return True
        elif parseResult == "endBracket":
            if not self.insertEndParen(parseResult):
                self.removeIfEmpty()
                return False
            else:
                self.window.undo.addBoundary()
                return True
        elif parseResult == "openBrace":
            self.insertOpenParen(listicons.DictIcon)
            self.window.undo.addBoundary()
            return True
        elif parseResult == "endBrace":
            if not self.insertEndParen(parseResult):
                self.removeIfEmpty()
                return False
            else:
                self.window.undo.addBoundary()
                return True
        elif parseResult == "openParen":
            self.insertOpenParen(parenicon.CursorParenIcon)
            self.window.undo.addBoundary()
            return True
        elif parseResult == "endParen":
            if not self.insertEndParen(parseResult):
                self.removeIfEmpty()
                return False
            else:
                self.window.undo.addBoundary()
                return True
        elif parseResult == "makeFunction":
            if self.attachedIcon().isCursorOnlySite(self.attachedSite()):
                self.removeIfEmpty()
                return False
            else:
                self.insertOpenParen(listicons.CallIcon)
                self.window.undo.addBoundary()
                return True
        elif parseResult == "makeSubscript":
            self.insertOpenParen(subscripticon.SubscriptIcon)
            self.window.undo.addBoundary()
            return True
        # Parser emitted an icon.  Splice it in to the hierarchy in place of the entry
        # icon (ignoring, for now, that the entry icon may have to be reinstated if there
        # are pending args/attrs or remaining to be placed).  Figure out where the cursor
        # or entry icon should end up after the operation.
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        snapLists = ic.snapLists(forCursor=True)
        if self.attachedIcon() is None:
            # Entry icon is on the top level
            self.window.replaceTop(self, ic)
            ic.markLayoutDirty()
            if "input" in snapLists:
                cursorIcon, cursorSite = ic, snapLists["input"][0][2]  # First input site
            elif "attrIn" in snapLists:
                cursorIcon, cursorSite = ic, "attrIcon"
            else:
                cursorIcon, cursorSite = icon.rightmostSite(ic)
        elif ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon):
            cursorIcon, cursorSite = self.insertAssign(ic)
            if not cursorIcon:
                self.removeIfEmpty()
                cursors.beep()
                return
        elif ic.__class__ is nameicons.YieldIcon:
            cursorIcon, cursorSite = self.insertYieldIcon(ic)
        elif self.canJoinIcons(ic):
            # 'is' followed by 'not', 'yield' folloed by 'from', unary minus followed by
            # number, sinqle-quoted string followed by quote; need to be joined in a
            # single 'is not', 'yield from', negative number, or triple-quoted string.
            self.joinIcons(ic)
            cursorIcon = self.attachedIcon()
            cursorSite = self.attachedSite()
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            if ic.__class__ is nameicons.AttrIcon:
                # Attribute
                self.attachedIcon().replaceChild(ic, "attrIcon")
                cursorIcon, cursorSite = ic, "attrIcon"
            elif ic.__class__ is opicons.IfExpIcon:
                cursorIcon, cursorSite = self.insertIfExpr(ic)
            elif ic.__class__ in (listicons.CprhIfIcon, listicons.CprhForIcon):
                cursorIcon, cursorSite = self.insertCprhIcon(ic)
            else:
                # Operator
                argIcon = icon.findAttrOutputSite(self.attachedIcon())
                if argIcon is None:
                    # We can't append an operator if there's no operand to attach it to
                    self.removeIfEmpty()
                    return False
                cursorIcon, cursorSite = _appendOperator(ic, self.attachedIcon(),
                    self.attachedSite())
        elif self.attachedSiteType() == "input":
            # Entry icon is attached to an input site
            if prepend:
                # When the entry icon is at a site coincident with the very left of a
                # top-level statement, such as the first element of a naked tuple or the
                # left operand of a boolean operator, the user is allowed to prepend a
                # top-level statement (if it can accept an input argument).
                stmtSite = ic.sites.firstCursorSite()
                topIcon = self.attachedIcon().topLevelParent()
                if ic.isCursorOnlySite(stmtSite):
                    # The statement takes no arguments.  Insert it on its own and leave
                    # the expression containing the entry icon as the next statement
                    self.window.replaceTop(topIcon, ic)
                    icon.insertSeq(topIcon, ic)
                    self.window.addTopSingle(topIcon)
                elif isinstance(topIcon, listicons.TupleIcon):
                    # The entry icon is at the start of a naked tuple.  Replace the naked
                    # tuple with the ic and make the entry icon (or the expression
                    # holding it) its first argument and the remaining tuple elements as
                    # its 2nd-nth.
                    exprTop = topIcon.childAt('argIcons_0')
                    tupleArgs = topIcon.argIcons()
                    for icn in tupleArgs:
                        if icn is not None:
                            topIcon.replaceChild(None, topIcon.siteOf(icn))
                    self.window.replaceTop(topIcon, ic)
                    # Use the prepended statement's placeArgs method to transfer the
                    # tuple content.  This is mostly for ClassDefIcon, which won't yet
                    # have sites for its superclass list
                    placeList = [tupleArgs]
                    if isinstance(ic, (blockicons.ClassDefIcon, blockicons.DefIcon)):
                        # If we're placing on a class or def icon, and the first site
                        # after the one containing the entry icon is None, insert an
                        # additional field to preserve the comma
                        if tupleArgs[1] is None:
                            placeList[0].insert(1, None)
                    elif not self.hasPendingArgs() and exprTop is self:
                        # If entry icon has no args and is not part of an expression,
                        # it will get removed later without keepPlace=True, removing
                        # a visible comma.  To compensate, add an empty clause.
                        placeList[0].insert(1, None)
                    placeIdx, seriesIdx = ic.placeArgs(placeList, stmtSite)
                    # If not all of the tuple arguments were placed, load the rest into a
                    # placeholder icon (if pending args or expression parts make them
                    # disjoint), or into our pending args (if they are adjacent to the
                    # text entry field).  (Some minor overkill here, since no-arg stmts
                    # are handled above and all the multi-arg statements can consume the
                    # entire tuple, so this should always be a single-arg statement).
                    if not icon.placeListAtEnd(placeList, placeIdx, seriesIdx):
                        if placeIdx == 0:
                            if self.hasPendingArgs() or exprTop is not self:
                                entryIc = EntryIcon(window=self.window)
                                entryParent, entrySite = icon.rightmostSite(exprTop)
                                entryParent.replaceChild(entryIc, entrySite)
                                entryIc.appendPendingArgs([tupleArgs[seriesIdx + 1:]])
                            else:
                                self.appendPendingArgs(
                                    [[None] + tupleArgs[seriesIdx + 1:]])
                        else:
                            print('_setText prepend failed placement')
                else:
                    # The entry icon is attached to some sort of binary operator on a site
                    # coincident with the left of the statement.  Leave the entry icon
                    # where it is in the expression, and wrap the statement icon around
                    # the entire expression
                    self.window.replaceTop(topIcon, ic)
                    ic.replaceChild(topIcon, stmtSite)
                cursorIcon = self.attachedIcon()
                cursorSite = self.attachedSite()
            elif isinstance(ic, opicons.UnaryOpIcon):
                # Unary operators need to be stitched in by priority
                self.replaceWith(ic)
                ic.replaceChild(self, 'argIcon')
                reorderexpr.reorderArithExpr(ic)
                cursorIcon, cursorSite = self.attachedIcon(), self.attachedSite()
            else:
                # Entry icon is on an input site that does not require special treatment
                self.attachedIcon().replaceChild(ic, self.attachedSite())
                if "input" in snapLists:
                    cursorIcon, cursorSite = ic, snapLists["input"][0][2]  # First input site
                else:
                    cursorIcon, cursorSite = icon.rightmostSite(ic)
        # If there is no remaining text or it's an empty delimiter, try to place pending
        # arguments.  If there are no pending arguments or all can be placed, we're done.
        if len(remainingText) == 0:
            # If entry icon has pending arguments, try to place them at the cursor site.
            # If we have more than one pending arg and _placePendingArgs can't place them
            # all, it will create a new placeholder entry icon to hold the remaining ones.
            if self._placePendingArgs(cursorIcon, cursorSite, overwriteStart=
                    cursorIcon==self.attachedIcon() and cursorSite==self.attachedSite()):
                # Args were placed, and there is no remaining text, so we can remove
                # the entry icon (if still attached), and be done
                if self.attachedIcon() is not None:
                    self.attachedIcon().replaceChild(None, self.attachedSite())
                if hasattr(ic, 'setCursorPos'):
                    self.window.cursor.setToText(ic)
                else:
                    self.window.cursor.setToIconSite(cursorIcon, cursorSite)
                self.window.undo.addBoundary()
                return True
        # There is remaining text or pending arguments.  Restore the entry icon.  Note
        # that the code above is guaranteed to put the cursor in the right place, and
        # either leave or remove the entry icon (I don't think any of the code will leave
        # the entry icon in the wrong place, but the code below will handle it and print
        # a diagnostic if it does).  If the prior code has removed the entry icon, that
        # means it's safe to place the undo boundary before reestablishing the entry icon
        # (to keep the undo stream neater).
        if self.attachedIcon() is not None and self.attachedIcon() is not cursorIcon:
            print('relocating entry icon... code is necessary, remove this diagnostic')
            self.attachedIcon().replaceChild(None, self.attachedSite())
        if self.attachedIcon() is None and not self.hasPendingArgs():
            # The entry icon has been removed and it's not carrying pending arguments
            # whose dissappearance would disturb the user. Set a temporary cursor and put
            # the undo boundary here, before we restore the entry icon.
            if hasattr(ic, 'setCursorPos'):
                self.window.cursor.setToText(ic)
            else:
                self.window.cursor.setToIconSite(cursorIcon, cursorSite)
            self.window.undo.addBoundary()
            earlyBoundaryAdded = True
        else:
            if not self.hasPendingArgs():
                print('Did I add ugly entry icon to undo? ...code improvement possible?')
            earlyBoundaryAdded = False
        if self.attachedIcon() is None:
            cursorIcon.replaceChild(self, cursorSite)
        self.text = remainingText
        self.cursorPos = len(remainingText)
        if hasattr(ic, 'setCursorPos'):
            self.window.cursor.setToText(ic)
        else:
            self.window.cursor.setToText(self)
        if self.attachedIcon().isCursorOnlySite(self.attachedSite()) and \
                self.attachedIcon().__class__ in cursors.stmtIcons and \
                self.attachedSiteType() == 'attrIn':
            # We've attached the entry icon to a statement's cursor-only attribute site
            # Insert the entry icon as a new statement following the one to which it was
            # formerly attached.  This is not just saving a user keystroke, by never
            # entering the state where we have an entry icon with text and pending args
            # on a no-arg statement, we save having to worry about that state, elsewhere.
            topIcon = self.attachedIcon().topLevelParent()
            if topIcon is self.attachedIcon() and topIcon.hasSite('seqOut'):
                topIcon.replaceChild(None, self.attachedSite())
                icon.insertSeq(self, topIcon)
                self.window.addTopSingle(self)
                if len(remainingText) == 0:
                    self.remove()
            else:
                print("Entry attached to cursor-only site")
        if not earlyBoundaryAdded:
            self.window.undo.addBoundary()
        self.markLayoutDirty()
        if remainingText == "":
            self.window.cursor.draw()
            return True
        # There is still text that might be processable.  Recursively go around again
        # (we only get here if something was processed, so this won't loop forever).
        # self.text still contains the content that was processed, above, and (while
        # unlikely) _setText can reject, and not overwrite it, so we must clear.
        self.text = ''  # In unlikely event _setText rejects, self.text needs to be right
        self.cursorPos = 0
        self._setText(remainingText, len(remainingText))
        return True

    def canPlaceEntryText(self, requireArgPlacement=False):
        # Parse the existing text and in the entry icon as if it had a delimiter (space)
        # added to the end (on ordinary typing, the parser must wait for a delimiter to
        # process text that might be the first character multi-character operator or
        # a keyword that is might be the start of an identifier).
        parseResult, handlerIc, consumeParent = self.parseEntryText(self.text + " ")
        # print('parse result', parseResult)
        # We assume that the entry text is something legal, waiting for a delimiter.
        # It should not be something self-delimiting.
        if parseResult in ("reject", "accept", "typeover", "comma", "colon",
                "openBracket", "endBracket", "openBreace", "endBrace", "openParen",
                "endParen", "makeFunction", "makeSubscript"):
            return False
        # Parser emitted an icon.  Splice it in to the hierarchy in place of the entry
        # icon (ignoring, for now, that the entry icon may have to be reinstated if there
        # are pending args/attrs or remaining to be placed).  Figure out where the cursor
        # or entry icon should end up after the operation.
        ic, remainingText = parseResult
        if remainingText != " ":
            print("Remaining text in canPlaceEntry text was not injected delimiter")
            return False
        if ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon):
            if not self.canInsertAssign(ic):
                return False
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            if ic.__class__ is not nameicons.AttrIcon:
                # We assume it's an operator (...shouldn't we check?)
                argIcon = icon.findAttrOutputSite(self.attachedIcon())
                if argIcon is None:
                    # We can't append an operator if there's no operand to attach it to
                    return False
        if not requireArgPlacement:
            return True
        # If the entry icon owns a block and the new icon would not, only allow if
        # the entry icon's block is empty
        if hasattr(self, 'blockEnd'):
            if self.nextInSeq() is not self.blockEnd and not hasattr(ic, 'blockEnd'):
                return False
        # Determine if the pending arguments can be placed on the icon that would be
        # created.  For most icons, arguments are placed on the first (child-type) site
        # on the icon.  However, for icons that act like operators (operators,
        # assignments, inline-if, as, dictElem, arg-assign), the arguments go after the
        # operator.
        firstSite = ic.sites.firstCursorSite()
        if ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon,
                opicons.BinOpIcon, opicons.IfExpIcon) or \
                isinstance(ic, infixicon.InfixIcon):
            firstSite = ic.sites.nextCursorSite(firstSite)
        return self._canPlacePendingArgs(ic, firstSite, useAllArgs=True)

    def insertComma(self):
        """A comma has been entered.  Search up the hierarchy to find a list, tuple,
        cursor-paren, or parameter list, parting every expression about the newly inserted
        comma.  If no comma-separated type is found, part the expression up to either an
        assignment, or the top level.  Return False if user tries to place comma within
        unary or binary op auto-parens, or on an icon that interrupts horizontal sequence
        of icons (divide)."""
        if self.attachedIcon() is None:
            # The entry icon is on the top level.  Reject, so as not to create a naked
            # tuple containing just a comma, which is more confusing than useful
            return False
        # Look for comma typeover opportunity
        typeoverIc = _findParenTypeover(self, "comma")
        if typeoverIc is not None:
            self.remove()  # Safe, since args would have invalidated typeover
            _siteBefore, siteAfter, _text, _idx = typeoverIc.typeoverSites()
            self.window.cursor.setToIconSite(typeoverIc, siteAfter)
            return True
        # Find the top of the expression to which the entry icon is attached
        ic, splitSite = findEnclosingSite(self)
        if ic is None:
            # There's no enclosing site, add a naked tuple
            ic = listicons.TupleIcon(window=self.window, noParens=True)
            splitSite = 'argIcons_0'
            top = self.topLevelParent()
            self.window.replaceTop(top, ic)
            ic.replaceChild(top, 'argIcons_0')
        if not iconsites.isSeriesSiteId(splitSite):
            # The bounding icon is not a sequence and will not accept a comma.  If it's
            # something with parens, turn it in to a tuple.  Otherwise reject
            if ic.__class__ is parenicon.CursorParenIcon:
                # Convert cursor paren to a tuple
                closed = ic.closed or _canCloseParen(self)
                ic = cvtCursorParenToTuple(ic, closed, typeover=closed and not ic.closed)
                splitSite = 'argIcons_0'
            elif ic.__class__ is opicons.BinOpIcon and ic.hasParens or \
                    ic.__class__ is opicons.IfExpIcon and ic.hasParens and \
                        splitSite != 'testExpr':
                # Convert  binary operator with parens to a tuple
                tupleIcon = listicons.TupleIcon(window=self.window, closed=True)
                ic.replaceWith(tupleIcon)
                tupleIcon.replaceChild(ic, 'argIcons_0')
                attrIcon = ic.sites.attrIcon.att
                ic.replaceChild(None, 'attrIcon')
                tupleIcon.replaceChild(attrIcon, 'attrIcon')
                ic.hasParens = False
                ic = tupleIcon
                splitSite = 'argIcons_0'
            else:
                # Bounding icon will not accept comma: reject
                return False
        if isinstance(ic, listicons.ListTypeIcon) and ic.isComprehension():
            # The bounding icon is a comprehension and won't accept additional clauses
            return False
        # ic can accept a new comma clause after splitSite.  Split expression in two at
        # entry icon
        left, right = splitExprAtIcon(self, ic, None, self)
        if left is None and right is None:
            # Deadly failure probably dropped content (diagnostics already printed)
            return False
        # Place the newly-split expression in to the series, creating a new clause
        ic.replaceChild(None, splitSite)
        splitSiteSeriesName, splitSiteIdx = iconsites.splitSeriesSiteId(splitSite)
        ic.insertChildren((left, right), splitSiteSeriesName, splitSiteIdx)
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return True

    def insertOpenParen(self, iconClass):
        """Called when the user types an open paren, bracket, or brace to insert an icon
        of type given in iconClass.  Inserting an open paren/bracket/brace has the power
        to completely rearrange the icon hierarchy.  For a consistent user-interface, we
        maintain un-closed parens at the highest level of the hierarchy that they can
        influence (clicking and dragging behavior is dependent on the hierarchy, even if
        code appearance is identical).  It is easier to maintain parens at the highest
        level than the lowest, since the paren itself makes this happen automatically,
        and they can be found by just looking up from a prospective end position.
        Likewise, if the parent is a sequence with clauses to the right of the entry
        icon, pull these down to the level of the new open paren.  Absent closing parens,
        the syntax is ambiguous as to who owns subsequent clauses, but typographically
        they belong to the innermost, so that's how we order the tree.  Consistent order
        is important to make the interface behave predictably."""
        # Determine if a parent has sequence clauses to the right of the entry icon that
        # will need entries transferred to the new paren icon.  It may also be necessary
        # to change the the generated icon from parens to tuple.
        attachedIc = self.attachedIcon()
        attachedSite = self.attachedSite()
        transferParentArgs = None
        if attachedIc is not None and iconClass is not subscripticon.SubscriptIcon:
            seqIc, seqSite = findEnclosingSite(self)
            if seqIc and iconsites.isSeriesSiteId(seqSite) and \
                    seqIc.typeOf(seqSite) == 'input':
                siteName, siteIdx = iconsites.splitSeriesSiteId(seqSite)
                rightOfSite = iconsites.makeSeriesSiteId(siteName, siteIdx + 1)
                if seqIc.hasSite(rightOfSite):
                    transferParentArgs = seqIc, rightOfSite
                    if iconClass is parenicon.CursorParenIcon:
                        iconClass = listicons.TupleIcon
        # Create an icon of the requested class and move the entry icon inside of it
        if iconClass is parenicon.CursorParenIcon:
            closed = False  # We leave even empty paren open to detect () for empty tuple
        else:
            closed = transferParentArgs is None and _canCloseParen(self)
        newParenIcon = iconClass(window=self.window, closed=closed, typeover=closed)
        if attachedIc is None:
            self.window.replaceTop(self, newParenIcon)
        else:
            attachedIc.replaceChild(newParenIcon, attachedSite)
        if iconClass is parenicon.CursorParenIcon:
            inputSite = 'argIcon'
        elif iconClass is subscripticon.SubscriptIcon:
            inputSite = 'indexIcon'
        else:
            inputSite = 'argIcons_0'
        newParenIcon.replaceChild(self, inputSite)
        # Attempt to get rid of the entry icon and place pending args in its place
        if not self.remove():
            if self._canPlacePendingArgs(self.attachedIcon(), self.attachedSite(),
                    overwriteStart=True, useAllArgs=False):
                self._placePendingArgs(self.attachedIcon(), self.attachedSite(),
                    overwriteStart=True)
                self.window.cursor.setToIconSite(newParenIcon, inputSite)
        # Reorder the expression with the new open paren in place (skip some work if the
        # entry icon was at the top level, since no reordering is necessary, there)
        if attachedIc is not None:
            reorderexpr.reorderArithExpr(newParenIcon)
        # Transfer sequence clauses after the new open paren/bracket/brace to it
        if transferParentArgs:
            rightOfIc, rightOfSite = transferParentArgs
            name, idx = iconsites.splitSeriesSiteId(rightOfSite)
            numParentSites = len(getattr(rightOfIc.sites, name))
            args = [rightOfIc.childAt(name, i) for i in range(idx, numParentSites)]
            for i in range(idx, numParentSites):
                rightOfIc.replaceChild(None, iconsites.makeSeriesSiteId(name, idx))
            insertIdx = len(newParenIcon.sites.argIcons)
            newParenIcon.insertChildren(args, 'argIcons', insertIdx)
            # If boundingParent was a tuple which is now down to 1 arg, remove it if it
            # was a naked tuple on the top level, or replace it with a cursor paren if it
            # was an ordinary tuple (Python's single-arg tuple syntax requires a trailing
            # comma (a,), which clashes with the python-g convention of unclosed parens
            # owning the clauses that follow them).
            if isinstance(rightOfIc, listicons.TupleIcon) and idx == 1:
                if rightOfIc.noParens:
                    newTopIcon = rightOfIc.childAt('argIcons_0')
                    rightOfIc.replaceChild(None, 'argIcons_0')
                    self.window.replaceTop(rightOfIc, newTopIcon)
                else:
                    cvtTupleToCursorParen(rightOfIc, closed=rightOfIc.closed,
                        typeover=rightOfIc.typeoverSites()[0] is not None)

    def insertEndParen(self, token):
        """Find a matching open paren/bracket/brace or paren-less tuple that could be
        closed by an end paren/bracket/brace (which type is specified by token) typed at
        the attached icon/site.  If a matching unclosed item is found, relocate it to the
        appropriate level, close it, and rearrange the icon hierarchy such that the
        expressions and attribute attachments match what has been typed.  Rearrangement
        may be significant.  Excluded sequence clauses are also relocated to a parent
        icon, following the rules for canonical arrangement of sequence items."""
        fromIcon = self.attachedIcon()
        fromSite = self.attachedSite()
        # Check for special case of the entry icon directly on the input site of a cursor
        # paren icon to be closed (empty tuple): convert it to one
        if isinstance(fromIcon, parenicon.CursorParenIcon) and token == "endParen" and (
                fromSite == 'argIcon' or
                fromSite == 'attrIcon' and fromIcon.childAt('argIcon') is None):
            tupleIcon = listicons.TupleIcon(window=self.window)
            fromIcon.replaceWith(tupleIcon)
            # If there are pending args, they need to go *after* the newly-closed paren,
            # so move the entry icon before calling .remove(), which will place them
            # (if possible) or leave the entry icon (if not).
            fromIcon.replaceChild(None, fromSite)
            tupleIcon.replaceChild(self, 'attrIcon')
            self.remove()
            self.window.updateTypeoverStates()
            return True
        matchingParen, transferArgsFrom = searchForOpenParen(token, self)
        if matchingParen is None:
            # No matching paren was found.  Remove cursor and look for typeover
            typeoverIc = _findParenTypeover(self, token)
            if typeoverIc is None:
                return False
            self.remove()  # Safe, since args would have invalidated typeover
            self.window.cursor.setToIconSite(typeoverIc, 'attrIcon')
            return True
        if transferArgsFrom is not None:
            # If the icon that matches or an intervening open paren/bracket/brace might
            # have arguments beyond the inserted end paren/bracket/brace, check whether
            # it does.  If so, transfer them upward to the next icon above in the
            # hierarchy that can accept them, possibly creating a naked tuple if no
            # parents were sequence sites.  If this fails, return None.
            if transferArgsFrom is fromIcon:
                siteOfMatch = fromSite
            else:
                siteOfMatch = transferArgsFrom.siteOf(fromIcon, recursive=True)
            name, idx = iconsites.splitSeriesSiteId(siteOfMatch)
            if name == "argIcons" and idx < len(transferArgsFrom.sites.argIcons) - 1:
                if not transferToParentList(transferArgsFrom, idx+1, matchingParen):
                    return False
                if isinstance(transferArgsFrom, listicons.TupleIcon) and idx == 0:
                    # Tuple is down to 1 argument.  Convert to arithmetic parens
                    newParen = cvtTupleToCursorParen(transferArgsFrom, closed=False,
                        typeover=False)
                    if transferArgsFrom is matchingParen:
                        matchingParen = newParen
        # Rearrange the hierarchy so the paren/bracket/brace is above all the icons it
        # should enclose and outside of those it does not enclose.  reorderArithExpr
        # closes the parens if it succeeds.
        reorderexpr.reorderArithExpr(matchingParen, closeParenAt=self)
        # If there are pending args, they need to go *after* the newly-closed paren.
        # reorderArithExpr will move the entry icon there, and the remove() call below
        # will place them. ...however at some point I added (incorrect) code (here) to
        # move the entry icon after the fact.  I've now removed the code and it seems to
        # be working correctly, but this is a good place to check if something's wrong.
        self.remove()
        self.window.updateTypeoverStates()
        return True

    def canInsertAssign(self, assignIcon):
        attIcon = icon.findAttrOutputSite(self.attachedIcon())
        attIconClass = attIcon.__class__
        isAugmentedAssign = assignIcon.__class__ is assignicons.AugmentedAssignIcon
        if not (attIconClass is assignicons.AssignIcon or
                attIconClass is listicons.TupleIcon and attIcon.noParens or
                self.attachedToAttribute() and attIconClass in (nameicons.IdentifierIcon,
                 listicons.TupleIcon, listicons.ListIcon, listicons.DictIcon,
                 nameicons.AttrIcon, parenicon.CursorParenIcon) or
                isinstance(self.attachedIcon(), assignicons.AssignIcon)):
            # The icon to which the entry icon is attached cannot support adding
            # an assignment
            return False
        if self.attachedToAttribute():
            highestCoincidentIcon = iconsites.highestCoincidentIcon(attIcon)
            if highestCoincidentIcon in self.window.topIcons:
                # The cursor is attached to an attribute of a top-level icon of a type
                # appropriate as a target.
                return True
        topParent = (attIcon if attIcon is not None else self.attachedIcon()).topLevelParent()
        if topParent.__class__ is listicons.TupleIcon and topParent.noParens:
            # There is a naked tuple at the top level waiting to be converted in to an
            # assignment statement.  This is fine, unless it's an augmented assign
            # (i.e +=), which can take only a single target
            return not isAugmentedAssign or len(topParent.argIcons()) == 1
        if topParent.__class__ is assignicons.AssignIcon and not isAugmentedAssign:
            # There is already an assignment icon to which we can add a new clause.
            return True
        return False

    def insertAssign(self, assignIcon):
        attIcon = icon.findAttrOutputSite(self.attachedIcon())
        attIconClass = attIcon.__class__
        isAugmentedAssign = assignIcon.__class__ is assignicons.AugmentedAssignIcon
        if not (attIconClass is assignicons.AssignIcon or
                attIconClass is listicons.TupleIcon and attIcon.noParens or
                self.attachedToAttribute() and attIconClass in (nameicons.IdentifierIcon,
                 listicons.TupleIcon, listicons.ListIcon, listicons.DictIcon,
                 nameicons.AttrIcon, parenicon.CursorParenIcon) or
                isinstance(self.attachedIcon(), assignicons.AssignIcon)):
            return None, None
        if self.attachedToAttribute():
            highestCoincidentIcon = iconsites.highestCoincidentIcon(attIcon)
            if highestCoincidentIcon in self.window.topIcons:
                # The cursor is attached to an attribute of a top-level icon of a type
                # appropriate as a target. Insert assignment icon and make it the target.
                self.attachedIcon().replaceChild(None, self.attachedSite())
                self.window.replaceTop(highestCoincidentIcon, assignIcon)
                if highestCoincidentIcon is not attIcon:
                    parent = attIcon.parent()
                    parentSite = parent.siteOf(attIcon)
                    parent.replaceChild(None, parentSite)
                    if isinstance(highestCoincidentIcon, listicons.TupleIcon) and \
                            highestCoincidentIcon.noParens:
                        # The highest coincident icon is a naked tuple: while these are
                        # also handled further down in the function, this is a simpler
                        # case (just insert the remaining icons in to values series) and
                        # easier to handle, here, than to bail from the deeply nested if.
                        args = highestCoincidentIcon.argIcons()
                        for arg in args:
                            highestCoincidentIcon.replaceChild(None,
                                highestCoincidentIcon.siteOf(arg))
                        assignIcon.replaceChild(self, 'values_0')
                        assignIcon.insertChildren(args, 'values', 1)
                        cursorIcon, cursorSite = assignIcon, 'values_0'
                    else:
                        assignIcon.replaceChild(highestCoincidentIcon, 'values_0')
                        cursorIcon, cursorSite = parent, parentSite
                else:
                    cursorIcon, cursorSite = assignIcon, "values_0"
                if isAugmentedAssign:
                    assignIcon.replaceChild(attIcon, 'targetIcon')
                else:
                    assignIcon.replaceChild(attIcon, "targets0_0")
                return cursorIcon, cursorSite
        topParent = (attIcon if attIcon is not None else self.attachedIcon()).topLevelParent()
        if topParent.__class__ is listicons.TupleIcon and topParent.noParens:
            # There is a no-paren tuple at the top level waiting to be converted in to an
            # assignment statement.  Do the conversion.
            targetIcons = topParent.argIcons()
            if isAugmentedAssign:
                # Augmented (i.e. +=) assigns have just one target, but it is possible
                # to delete out a comma and be left with a single value in the tuple
                if len(targetIcons) != 1:
                    return None, None
                self.attachedIcon().replaceChild(None, self.attachedSite())
                assignIcon.replaceChild(targetIcons[0], 'targetIcon')
            else:
                attachedIcon = self.attachedIcon()
                attachedSite = self.attachedSite()
                attachedIcon.replaceChild(None, attachedSite)
                if attachedIcon is topParent:
                    # entry icon is directly attached to the tuple (on comma or body)
                    insertSiteId = attachedSite
                    targetIcons.remove(self)
                else:
                    insertSiteId = topParent.siteOf(attIcon, recursive=True)
                for tgtIcon in targetIcons:
                    topParent.replaceChild(None, topParent.siteOf(tgtIcon))
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(insertSiteId)
                splitIdx = seriesIdx + (0 if topParent is attachedIcon else 1)
                assignIcon.insertChildren(targetIcons[:splitIdx], 'targets0', 0)
                assignIcon.insertChildren(targetIcons[splitIdx:], 'values', 0)
                # The removed code, below inserts a useless comma and I haven't found any
                # cases where it was needed (preserved temporarily for documentation).
                #if splitIdx < len(targetIcons):
                #    assignIcon.insertChild(None, 'values_0')
            self.window.replaceTop(topParent, assignIcon)
            return assignIcon, "values_0"
        if topParent.__class__ is assignicons.AssignIcon and not isAugmentedAssign:
            # There is already an assignment icon.  Add a new clause, splitting the
            # target list at the entry location.  (assignIcon is thrown away)
            attachedIcon = self.attachedIcon()
            attachedSite = self.attachedSite()
            attachedIcon.replaceChild(None, attachedSite)
            if attachedIcon is topParent:
                # entry icon is directly attached to the assignment (on comma or body)
                insertSiteId = attachedSite
            else:
                insertSiteId = topParent.siteOf(attIcon, recursive=True)
            seriesName, seriesIdx = iconsites.splitSeriesSiteId(insertSiteId)
            splitIdx = seriesIdx + (0 if topParent is attachedIcon else 1)
            if seriesName == 'values':  # = was typed in the value series
                newTgtGrpIdx = len(topParent.tgtLists)
                cursorSite = 'values_0'
                iconsToMove = [site.att for site in topParent.sites.values][:splitIdx]
            else:  # = was typed in a target series
                newTgtGrpIdx = int(seriesName[7:]) + 1
                cursorSite = 'targets%d_0' % newTgtGrpIdx
                series = getattr(topParent.sites, seriesName)
                iconsToMove = [site.att for site in series][splitIdx:]
            topParent.addTargetGroup(newTgtGrpIdx)
            for tgtIcon in iconsToMove:
                if tgtIcon is not None:
                    topParent.replaceChild(None, topParent.siteOf(tgtIcon))
            topParent.insertChildren(iconsToMove, 'targets%d' % newTgtGrpIdx, 0)
            # The removed code, below inserts a useless comma and I haven't found any
            # cases where it was needed (preserved temporarily for documentation).
            # if topParent.childAt(cursorSite):
            #     topParent.insertChild(None, cursorSite)
            return topParent, cursorSite
        return None, None

    def insertColon(self):
        if self.attachedIcon() is None:
            # Not allowed to type colon at the top level: Reject
            return False
        # Find the top of the expression to which the entry icon is attached
        ic, splitSite = findEnclosingSite(self)
        if isinstance(ic, listicons.DictIcon):
            return self.insertDictColon(ic)
        if isinstance(ic, subscripticon.SubscriptIcon):
            return self.insertSubscriptColon(ic)
        return False

    def insertYieldIcon(self, ic):
        """This handles a weird corner case in Python syntax, where yield can be used as
        an expression, and therefore be embedded in a list, but itself takes a list with
        no terminator (like a closing paren).  It is therefore ambiguous whether list
        clauses following the yield are attached to the yield or its parent.  While
        the python documentation acknowledges this and simply states that it should be
        parenthesized when used as an expression, we can't stop users from typing it.
        And, once they type it, it has to be canonically ordered like unclosed parens or
        it will break paren matching."""
        attIcon = self.attachedIcon()
        attSite = self.attachedSite()
        # Replace the entry icon with the yield icon (ic)
        attIcon.replaceChild(ic, attSite)
        # Determine if the yield icon needs to take ownership of parent list clauses
        if not iconsites.isSeriesSiteId(attSite):
            return ic, 'values_0'
        attSeriesName, attSeriesIdx = iconsites.splitSeriesSiteId(attSite)
        numSeriesSites = len(getattr(attIcon.sites, attSeriesName))
        if len(getattr(attIcon.sites, attSeriesName)) == attSeriesIdx - 1:
            return ic, 'values_0'
        # ... yes, there are clauses to move
        args = [attIcon.childAt(attSeriesName, i) for i in range(attSeriesIdx + 1,
            numSeriesSites)]
        for i in range(attSeriesIdx+1, numSeriesSites):
            attIcon.replaceChild(None, iconsites.makeSeriesSiteId(attSeriesName,
                attSeriesIdx+1))
        insertIdx = len(ic.sites.values)
        insertIdx -= 1 if insertIdx == 1 and ic.sites.values[0].att is None else 0
        ic.insertChildren(args, 'values', insertIdx)
        # If attIcon was a naked tuple, which is now down to 1 arg, remove it
        if attIcon.parent() is None and attSeriesIdx == 0 and \
                isinstance(attIcon, listicons.TupleIcon) and attIcon.noParens:
            attIcon.replaceChild(None, 'argIcons_0')
            ic.window.replaceTop(attIcon, ic)
        return ic, 'values_0'

    def insertIfExpr(self, ifExpr):
        """Integrate a newly-entered inline if expression.  While _appendOperator can
        almost do this, the additional site made the combined code unwieldy enough that
        this code is better off on its own to keep the common code simpler."""
        # When this is called, the entry icon will be attached to an attribute site.  The
        # icon to which the entry icon is attached (or the root of its attribute chain)
        # may be embedded in an expression.  If so, split the expression around it,
        # putting it and the part of the expression that precedes it in the trueExpr site
        # of the new icon and the entry icon and any part o the expression that follows
        # it in the testExpr site.  No reordering is necessary because inline-if has the
        # lowest expression precedence.
        splitAt = icon.findAttrOutputSite(self)
        splitTo, splitToSite = findEnclosingSite(splitAt)
        if splitTo is None:
            topExprParentSite = None
            topExpr = splitAt.topLevelParent()
        else:
            topExprParentSite = splitTo.siteOf(splitAt, recursive=True)
            topExpr = splitTo.childAt(topExprParentSite)
        left, right = splitExprAtIcon(splitAt, splitTo, splitAt, self)
        if splitTo is None:
            self.window.replaceTop(topExpr, ifExpr)
        else:
            splitTo.replaceChild(ifExpr, topExprParentSite)
        ifExpr.replaceChild(left, 'trueExpr')
        ifExpr.replaceChild(right, 'testExpr')
        return self.attachedIcon(), self.attachedSite()

    def insertDictColon(self, onIcon):
        onSite = onIcon.siteOf(self, recursive=True)
        child = onIcon.childAt(onSite)
        pendingArg, pendIdx, seriesIdx = icon.firstPlaceListIcon(self.listPendingArgs())
        if isinstance(child, listicons.DictElemIcon):
            # There's already a colon in this clause.  We allow a colon to be
            # typed on the left of an existing clause, since that is how one
            # naturally types a new clause (when they begin after the comma or to
            # the left of the first clause).  Typing a colon on the right side of
            # a dictElem is not expected without a comma, and not allowed.
            dictElemSite = child.siteOf(self, recursive=True)
            if dictElemSite != 'leftArg':
                return False
            # Split across entry icon, insert both a colon and a comma w/typeover
            left, right = splitExprAtIcon(self, child, None, self)
            if left is None and right is None:
                return False
            newDictElem = listicons.DictElemIcon(window=self.window)
            newDictElem.replaceChild(left, 'leftArg')
            onIcon.replaceChild(newDictElem, onSite, leavePlace=True)
            nextSite = iconsites.nextSeriesSiteId(onSite)
            onIcon.insertChild(child, nextSite)
            child.replaceChild(right, 'leftArg')
            # Remove entry icon, placing pending args on the right side of the new comma
            # but cursor before the comma... Checking for pending args needs to happen
            # earlier while we can still bail
            if self.remove():
                self.window.cursor.setToIconSite(newDictElem, 'rightArg')
            onIcon.setTypeover(0, nextSite)
            self.window.watchTypeover(onIcon)
        elif isinstance(pendingArg, listicons.DictElemIcon):
            # We are holding a dictElem as a pending arg: add a new clause and deposit
            # the pending arg in to it.  Note that since DictElemIcons can only appear
            # on the top level of a dictionary icon, we assume that the entry icon's
            # parent expression does not extend to the right of the pending arg
            nextSite = iconsites.nextSeriesSiteId(onSite)
            self.popPendingArgs(pendIdx, seriesIdx)
            onIcon.insertChild(pendingArg, nextSite)
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(child, 'leftArg')
            self.remove()
            self.window.cursor.setToIconSite(newDictElem, 'rightArg')
            onIcon.setTypeover(0, nextSite)
            self.window.watchTypeover(onIcon)
        elif child is self:
            # There's nothing at the site except entry icon and whatever we are holding.
            # Place a new DictElemIcon, move entry icon to right arg, try to place
            # pending args and remove
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(self, 'rightArg')
            self.remove()
        else:
            # There's something at the site.  Put a colon in it
            left, right = splitExprAtIcon(self, onIcon, None, self)
            if left is None and right is None:
                return False
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(left, 'leftArg')
            newDictElem.replaceChild(right, 'rightArg')
            self.remove()
        return True

    def insertSubscriptColon(self, onIcon):
        if onIcon.hasSite('stepIcon'):
            return False   # Subscript already has all 3 colons
        onSite = onIcon.siteOf(self, recursive=True)
        # Split the expression holding the entry icon in two at the entry icon
        left, right = splitExprAtIcon(self, onIcon, None, self)
        if left is None and right is None:
            # Deadly failure probably dropped content (diagnostics already printed)
            return False
        # Create a new clause and put the two halves in to them
        if onIcon.hasSite('upperIcon'):
            onIcon.changeNumSubscripts(3)
            siteAdded = 'stepIcon'
        else:
            onIcon.changeNumSubscripts(2)
            siteAdded = 'upperIcon'
        # If the cursor was on the first site, may need to shift second-site icons
        if onSite == 'indexIcon' and siteAdded == "stepIcon":
            toShift = onIcon.childAt('upperIcon')
            onIcon.replaceChild(None, "upperIcon")
            onIcon.replaceChild(toShift, 'stepIcon')
            nextSite = 'upperIcon'
        else:
            nextSite = siteAdded
        # Place the newly-split expression in to its assigned slots
        onIcon.replaceChild(left, onSite)
        onIcon.replaceChild(right, nextSite)
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return True

    def insertCprhIcon(self, ic):
        """Handle insertion of a comprehension.  Comprehension sites are cursor-
        prohibited, and the entry icon will be sitting somewhere under a list, dict, or
        tuple icon, from which we will determine the actual insertion (cprh) site."""
        for parent in self.parentage(includeSelf=False):
            if isinstance(parent, (listicons.ListIcon, listicons.DictIcon,
                    listicons.DictIcon, listicons.TupleIcon, parenicon.CursorParenIcon)):
                insertIn = parent
                break
        else:
            print('Failed to find host icon for comprehension')
            return None, None
        if isinstance(insertIn, parenicon.CursorParenIcon):
            # User can start typing a comprehension before the icon is converted to a
            # tuple.
            tupleIcon = cvtCursorParenToTuple(insertIn, closed=True,
                typeover=not insertIn.closed)
            insertIn = tupleIcon
        siteBeforeInsert = insertIn.siteOf(self, recursive=True)
        if siteBeforeInsert == 'argIcons_0':
            insertIdx = 0
        else:
            series, idx = iconsites.splitSeriesSiteId(siteBeforeInsert)
            if series != 'cprhIcons':
                print('Failed to find correct site to insert comprehension')
                return None, None
            insertIdx = idx + 1
        insertIn.insertChild(ic, 'cprhIcons', insertIdx)
        if isinstance(ic, listicons.CprhForIcon):
            return ic, 'targets_0'
        return ic, 'testIcon'

    def canJoinIcons(self, insertedIc):
        """Returns True if joinIcons can join insertedIc with the icon which precedes the
        site where the entry icon is currently attached.  See joinIcons."""
        return self._joinIcons(insertedIc, False)

    def joinIcons(self, insertedIc):
        """The "is not", and "yield from" icons and numbers preceded by a '-' can't be
        typed as a unit, because "is", "yield" and unary minus are needed operators in
        their own right, so when such a combination is typed, _setText needs to unify
        them in to a single icon.  If found, join the icons, relocate the entry icon and
        return True."""
        return self._joinIcons(insertedIc, True)

    def _joinIcons(self, insertedIc, doJoin):
        attachedIc = self.attachedIcon()
        attachedSite = self.attachedSite()
        leftIc = attachedIc
        leftSite = attachedSite
        while iconsites.isCoincidentSite(leftIc, leftSite):
            parent = leftIc.parent()
            if parent is None:
                return False
            leftSite = parent.siteOf(leftIc)
            leftIc = parent
        if (isinstance(insertedIc,
                opicons.UnaryOpIcon) and insertedIc.operator == 'not' and
                isinstance(leftIc, opicons.BinOpIcon) and leftIc.operator == 'is' and
                leftSite == 'rightArg'):
            # Join an 'is' icon and a 'not' icon into an 'is not' icon
            if not doJoin:
                return True
            leftArg = leftIc.leftArg()
            rightArg = leftIc.rightArg()
            leftIc.replaceChild(None, 'leftArg')
            leftIc.replaceChild(None, 'rightArg')
            newOp = opicons.BinOpIcon('is not', window=self.window)
            leftIc.replaceWith(newOp)
            newOp.replaceChild(leftArg, 'leftArg')
            newOp.replaceChild(rightArg, 'rightArg')
            return True
        elif isinstance(insertedIc, nameicons.YieldFromIcon):
            # A YieldFrom icon usually signals the existence of a yield icon above, since
            # the normal way it gets typed is via the text "from" being detected by the
            # yield icon's textEntryHandler.  However, it can appear by itself if the
            # user edits a yield from icon.
            if not isinstance(leftIc, nameicons.YieldIcon):
                return False
            if not doJoin:
                return True
            values = [v.att for v in leftIc.sites.values]
            if len(values) > 1:
                argList = [[None] + values[1:]]
                recipient = transferToParentList(leftIc, 1, leftIc, 'values')
                if recipient is None:
                    for valueIc in values[1:]:
                        leftIc.replaceChild(None, leftIc.siteOf(valueIc))
                    self.appendPendingArgs(argList)
            leftIc.replaceChild(None, 'values_0')
            leftIc.replaceWith(insertedIc)
            insertedIc.replaceChild(values[0], 'argIcon')
            return True
        elif isinstance(attachedIc, opicons.UnaryOpIcon) and attachedIc.operator == '-' \
                and isinstance(insertedIc, nameicons.NumericIcon):
            # Join unary minus and a numeric icon into a negative numeric icon
            if not doJoin:
                return True
            newNumIc = nameicons.NumericIcon(-insertedIc.value, window=attachedIc.window)
            attachedIc.replaceChild(None, attachedSite)
            attachedIc.replaceWith(newNumIc)
            newNumIc.replaceChild(self, 'attrIcon')
            return newNumIc, 'attrIcon'
        elif isinstance(attachedIc, stringicon.StringIcon) and \
                attachedIc.string == '' and len(attachedIc.quote) == 1 and \
                isinstance(insertedIc, stringicon.StringIcon):
            # Change a single-quoted string to a triple-quoted string
            if not doJoin:
                return True
            attachedIc.replaceChild(None, 'attrIcon')
            attachedIc.replaceWith(insertedIc)
            insertedIc.replaceChild(self, 'attrIcon')
            return insertedIc, 'attrIcon'
        return False

    def click(self, evt):
        self.window.cursor.erase()
        self.cursorPos = comn.findTextOffset(icon.globalFont, self.text,
            evt.x - self.rect[0] - self.textOffset)
        self.window.cursor.setToText(self, drawNew=False)

    def pointInTextArea(self, x, y):
        left, top, right, bottom = self.rect
        left += penImage.width
        top += 2
        bottom -= 2
        right -= 2
        return left < x < right and top < y < bottom

    @staticmethod
    def _snapFn(ic, siteId):
        """Return False if sideId of ic is not a sequence site.  Rather than forcing the
        entry icon to divest its output sites when it owns a block, we just prevent it
        from snapping to any inputs (... I'm not sure this still makes sense, now that
        entry icons cannot change to/from block owning and not-block-owning, but it
        still avoids complicating layout code that already has to position the icon
        differently based on whether it's attached to an attribute or an output)."""
        if siteId not in ('seqOut', 'seqIn'):
            return False
        print(f'snapFn accepted: {ic.dumpName()}, {siteId}')
        return True

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        # Add snap sites for insertion (might want to reevaluate whether this is useful)
        insertSnapLists = []
        for siteOrSeries in self.iteratePendingSiteList():
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                listMgr = self.pendingArgListMgrs[siteOrSeries.name]
                insertSnapLists += listMgr.makeInsertSnapList()
        siteSnapLists['insertInput'] = insertSnapLists
        # Make snaplist for output/attrOut conditional to not snap to inputs if the entry
        # icon owns a block
        if hasattr(self, 'blockEnd'):
            if 'output' in siteSnapLists:
                outSnapSite = siteSnapLists['output'][0]
                del siteSnapLists['output']
                siteSnapLists['conditional'] = [(*outSnapSite, 'output', self._snapFn)]
            if 'attrOut' in siteSnapLists:
                outSnapSite = siteSnapLists['attrOut'][0]
                del siteSnapLists['attrOut']
                siteSnapLists['conditional'] = [(*outSnapSite, 'attrOut', self._snapFn)]
        return siteSnapLists

    def doLayout(self, siteX, siteY, layout):
        for siteOrSeries in self.iteratePendingSiteList():
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                self.pendingArgListMgrs[siteOrSeries.name].doLayout(layout)
        if self.attachedSite() == "attrIcon":
            outSiteY = siteY - icon.ATTR_SITE_OFFSET
            outSiteX = siteX - 1
            self.textOffset = attrPenImage.width + icon.TEXT_MARGIN
        else:
            outSiteY = siteY
            outSiteX = siteX
            self.textOffset = penImage.width + icon.TEXT_MARGIN
        top = outSiteY - self.height//2
        self.rect = (outSiteX, top, outSiteX + layout.width, top + self.height)
        if not self.hasPendingArgs():
            self.sites.forCursor.xOffset = layout.width - icon.ATTR_SITE_DEPTH
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.layoutDirty = False
        self.drawList = None

    def calcLayouts(self):
        argLayoutGroups = []
        argNames = []
        argYOffs = []
        for siteOrSeries in self.iteratePendingSiteList():
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                listMgr = self.pendingArgListMgrs[siteOrSeries.name]
                argLayoutGroups.append(listMgr.calcLayouts())
                argNames.append(siteOrSeries.name)
                argYOffs.append(0)
            else:
                argIc = getattr(self.sites, siteOrSeries.name).att
                if argIc is not None:
                    argLayoutGroups.append(argIc.calcLayouts())
                    argNames.append(siteOrSeries.name)
                    y = icon.ATTR_SITE_OFFSET if siteOrSeries.type == 'attrIn' else 0
                    argYOffs.append(y)
        baseWidth = self._width() - (1 if self.attachedToAttribute() else 2)
        siteOffset = self.height // 2
        if len(argLayoutGroups) == 0:
            # No pending arguments (forCursor site can't hold icons)
            return self.debugLayoutFilter([iconlayout.Layout(self, baseWidth,
                self.height, siteOffset)])
        layouts = []
        for argLayouts in iconlayout.allCombinations(argLayoutGroups):
            width = baseWidth
            layout = iconlayout.Layout(self, width, self.height, siteOffset)
            for idx, argLayout in enumerate(argLayouts):
                if isinstance(argLayout, iconlayout.ListMgrLayout):
                    argLayout.mergeInto(layout, width, argYOffs[idx])
                else:
                    layout.addSubLayout(argLayout, argNames[idx], width, argYOffs[idx])
                width += argLayout.width
            layout.width = width
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def backspace(self, siteId, evt):
        if siteId == self.sites.firstCursorSite():
            # Backspace from icon cursor location right-of the entry icon into text area
            self.window.cursor.setToText(self)
        elif iconsites.isSeriesSiteId(siteId) and \
                iconsites.splitSeriesSiteId(siteId)[1] != 0:
            # Cursor is on a comma
            listicons.backspaceComma(self, siteId, evt)
            self.recolorPending()
        else:
            # Backspace from a pending arg site.  These sites are coincident and should
            # probably be marked as cursor-prohibited once that is supported.  For now,
            # forward to the rightmost site of the prior arg.
            prevSite = self.sites.prevCursorSite(siteId)
            rightmostIc, rightmostSite = icon.rightmostFromSite(self, prevSite)
            rightmostIc.backspace(rightmostSite, evt)

    def clipboardRepr(self, offset):
        return None

    def createAst(self):
        raise icon.IconExecException(self, "Remove text-entry field")

    def execute(self):
        raise icon.IconExecException(self, "Can't execute text-entry field")

    def attachedToAttribute(self):
        return self.attachedSite() is not None and \
         self.attachedSiteType() in ("attrOut", "attrIn")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN

    def recolorPending(self):
        highlight = 'highlightPend'
        #... Todo: should we be dark-highlighting anything?
        children = self.children()
        if len(children) == 0:
            return
        for ic in children:
            _addHighlights(ic, highlight)
        self.markLayoutDirty()

    def cursorWindowPos(self):
        x, y = self.rect[:2]
        x += self.textOffset + icon.globalFont.getsize(self.text[:self.cursorPos])[0]
        y += self.sites.output.yOffset
        return x, y

    def setCursorPos(self, pos):
        if pos == 'end':
            self.cursorPos = len(self.text)
        else:
            self.cursorPos = max(0, min(len(self.text), pos))

    def textCursorImage(self):
        return textCursorImage

    def _canPlacePendingArgs(self, onIcon, onSite, overwriteStart=False,
            useAllArgs=False):
        """Returns True if _placePendingArgs will be able to place the entry icon's
        pending args on a given icon (onIcon), starting at a given site (onsite).  If
        useAllArgs is set to True, additionally requires that all (non-empty) pending
        args be used."""
        if not self.hasPendingArgs():
            return True
        pendingArgList = self.listPendingArgs()
        pendIdx, pendSeriesIdx = onIcon.canPlaceArgs(pendingArgList, onSite,
            overwriteStart=overwriteStart)
        if pendIdx is None:
            return False  # No arguments can be placed
        if icon.placeListAtEnd(pendingArgList, pendIdx, pendSeriesIdx):
            return True  # All arguments can be placed
        if icon.placeListEmpty(pendingArgList, pendIdx, pendSeriesIdx):
            # The only args that could be placed were empty.  This is allowed when the
            # whole pending arg list can be placed, as it could be restoring a statement
            # being text edited ("return ,,,"), but if the empty args are followed by a
            # rejected argument, it's better not to dislocate the entry icon for that.
            return False
        if not useAllArgs:
            return True  # Some args used and not required to use all
        if pendIdx != len(pendingArgList) - 1:
            return False  # Required to use all and did not reach last arg site/series
        if pendSeriesIdx is None:
            return True  # Last arg site either not a series, or is a fully-used series
        # If we get here, the last site is a series, but some elements were not used.
        # Accept if all of the unused series sites are empty.
        for i in range(pendSeriesIdx+1, len(pendingArgList[pendIdx])):
            if pendingArgList[pendIdx][i] is not None:
                return False
        return True

    def _placePendingArgs(self, onIcon, onSite, overwriteStart=False):
        """Note that this is not a fully-general function for placing entry icon pending
        args and attributes, but just for the specific case (shared between _setText
        and remove()) of checking whether pending args/attrs are compatible with a given
        site and placing them.  Does not remove the entry icon (unless it is in the way
        of arg/attr placement).  Returns False if none of the pending arguments could be
        placed.  If some but not all of the pending args were placed, creates a new
        entry icon to hang the remaining args off of and attaches that to the rightmost
        site from the rightmost argument placed."""
        if not self.hasPendingArgs():
            return True
        pendingArgList = self.listPendingArgs()
        pendIdx, pendSeriesIdx = onIcon.canPlaceArgs(pendingArgList, onSite,
            overwriteStart=overwriteStart)
        if pendIdx is None:
            return False
        if icon.placeListAtEnd(pendingArgList, pendIdx, pendSeriesIdx):
            # All args can be placed.  Place them and we're done
            self.popPendingArgs(pendIdx, pendSeriesIdx)
            onIcon.placeArgs(pendingArgList, onSite, overwriteStart=overwriteStart)
            return True
        if icon.placeListEmpty(pendingArgList, pendIdx, pendSeriesIdx):
            # The only args we were able to place were empty: don't add/move entry icon
            return False
        # Some but not all of the pending args can be placed, leaving the remaining ones
        # disjoint from the original entry icon.  Create a new entry icon to hold the
        # remaining args, and attach it to the rightmost site of the rightmost placed
        # arg (if that arg is None (empty), then place the entry icon in its place).
        if pendSeriesIdx is None:
            rightmostArg = pendingArgList[pendIdx]
        else:
            rightmostArg = pendingArgList[pendIdx][pendSeriesIdx]
        self.popPendingArgs(pendIdx, pendSeriesIdx)
        remainingArgs = self.listPendingArgs()
        self.popPendingArgs("all")
        if not icon.placeListEmpty(remainingArgs):
            entryIcon = EntryIcon(window=self.window)
            entryIcon.appendPendingArgs(remainingArgs)
            if rightmostArg is None:
                if pendSeriesIdx is None:
                    pendingArgList[pendIdx] = entryIcon
                else:
                    pendingArgList[pendIdx][pendSeriesIdx] = entryIcon
            else:
                rightmostIcon, rightmostSite = icon.rightmostSite(rightmostArg)
                rightmostIcon.replaceChild(entryIcon, rightmostSite)
        onIcon.placeArgs(pendingArgList, onSite, overwriteStart=overwriteStart)
        return True

def parseAttrText(text, window):
    if len(text) == 0:
        return "accept"
    if text == '.' or attrPattern.fullmatch(text):
        return "accept"  # Legal attribute pattern
    if text in ("i", "a", "o", "an", "n", "no", "not", "not ", "not i"):
        return "accept"  # Legal precursor characters to binary keyword operation
    if text == "if":
        return opicons.IfExpIcon(window, typeover=True), None # In-line if
    if text in ("and", "is", "in", "or", "not in"):
        return opicons.BinOpIcon(text, window), None # Binary keyword operation
    if text in ("*", "/", "<", ">", "=", "!"):
        return "accept"  # Legal precursor characters to binary operation
    if text in compareOperators:
        return opicons.BinOpIcon(text, window), None
    if text in binaryOperators:
        return "accept"  # Binary ops can be part of augmented assign (i.e. +=)
    if text[:-1] in binaryOperators and text[-1] == '=':
        return assignicons.AugmentedAssignIcon(text[:-1], window), None
    if text == '(':
        return "makeFunction"  # Make a function from the attached icon
    if text == ')':
        return "endParen"
    if text == '[':
        return "makeSubscript"
    if text == ']':
        return "endBracket"
    if text == '}':
        return "endBrace"
    if text == ',':
        return "comma"
    if text == ':':  #... see if this can be removed once handlers are in place
        return "colon"
    op = text[:-1]
    delim = text[-1]
    if attrPattern.fullmatch(op):
        return nameicons.AttrIcon(op[1:], window), delim
    if delim in delimitChars:
        # While these trigger, above, without delimiters, backspacing or alt+clicking
        # puts them in an entry icon that requires the user to type a delimiter
        if op == "if":
            return opicons.IfExpIcon(window, typeover=True), delim
        if op in ("and", "is", "in", "or", "not in", "is not"):
            return opicons.BinOpIcon(op, window), delim  # Binary keyword operation
    if opDelimPattern.match(delim):
        if op in compareOperators:
            return opicons.BinOpIcon(op, window), delim
        if op in binaryOperators:
            # Valid binary operator followed by allowable operand character
            if op == '/':
                return opicons.DivideIcon(False, window), delim
            elif op == '//':
                return opicons.DivideIcon(True, window), delim
            return opicons.BinOpIcon(op, window), delim
        if op[:-1] in binaryOperators and op[-1] == '=':
            return assignicons.AugmentedAssignIcon(op[:-1], window), delim
    if op == '=':
        return assignicons.AssignIcon(1, window), delim
    return "reject"

def parseExprText(text, window):
    if len(text) == 0:
        return "accept"
    if text in unaryNonKeywordOps:
        # Unary operator
        return opicons.UnaryOpIcon(text, window), None
    if text == '(':
        return "openParen"
    if text == ')':
        return "endParen"
    if text == '[':
        return "openBracket"
    if text == ']':
        return "endBracket"
    if text == '{':
        return "openBrace"
    if text == '}':
        return "endBrace"
    if text == ',':
        return "comma"
    if text == ':':
        return "colon"
    if text == '=':
        return assignicons.AssignIcon(1, window), None
    if stringPattern.fullmatch(text):
        return stringicon.StringIcon(initReprStr=text+text[-1], window=window,
            typeover=True), None
    if text == 'yield from':
        return "accept"  # No need to process immediately (here to accept space)
    if identPattern.fullmatch(text) or numPattern.fullmatch(text):
        return "accept"  # Nothing but legal identifier and numeric
    delim = text[-1]
    text = text[:-1]
    if opDelimPattern.match(delim):
        if text in unaryOperators:
            return opicons.UnaryOpIcon(text, window), delim
    if text == 'yield':
        return nameicons.YieldIcon(window), delim
    if text == 'yield from':
        return nameicons.YieldFromIcon(window), delim
    if text == 'await':
        return nameicons.AwaitIcon(window), delim
    if not (identPattern.fullmatch(text) or numPattern.fullmatch(text)):
        return "reject"  # Precursor characters do not form valid identifier or number
    if len(text) == 0 or delim not in delimitChars:
        return "reject"  # No legal text or not followed by a legal delimiter
    # All but the last character is ok and the last character is a valid delimiter
    if text in ('False', 'None', 'True'):
        return nameicons.IdentifierIcon(text, window), delim
    if text in keywords:
        return "reject"
    exprAst = parseExprToAst(text)
    if exprAst is None:
        return "reject"
    if exprAst.__class__ == ast.Name:
        return nameicons.IdentifierIcon(exprAst.id, window), delim
    if exprAst.__class__ == ast.Num:
        return nameicons.NumericIcon(exprAst.n, window), delim
    if exprAst.__class__ == ast.UnaryOp and exprAst.op.__class__ == ast.USub and \
            exprAst.operand == ast.Num:
        return nameicons.NumericIcon(-exprAst.operand.n, window), delim
    if exprAst.__class__ == ast.Constant and isinstance(exprAst.value, numbers.Number):
        return nameicons.NumericIcon(exprAst.value, window), delim
    if exprAst.__class__ == ast.UnaryOp and exprAst.op.__class__ == ast.USub and \
            exprAst.operand.__class__ == ast.Constant and \
            isinstance(exprAst.operand.value, numbers.Number):
        return nameicons.NumericIcon(-exprAst.operand.value, window), delim
    return "reject"

def parseTopLevelText(text, window):
    if len(text) == 0:
        return "accept"
    for stmt, icClass in cursors.topLevelStmts.items():
        if len(text) <= len(stmt) and text == stmt[:len(text)]:
            return "accept"
        delim = text[-1]
        if text[:-1] == stmt and delim in delimitChars:
            if stmt in noArgStmts and delim not in emptyDelimiters:
                return "reject"  # Accepting unusable delimiters would cause trouble later
            kwds = {}
            if stmt[:5] == "async":
                kwds['isAsync'] = True
            if hasattr(icClass, 'hasTypeover') and icClass.hasTypeover:
                kwds['typeover'] = True
            return icClass(window=window, **kwds), delim
    if text == '*':
        # Sadly, while very unusual, it is possible to write *a, b = c, and since we
        # don't yet even know if it's a list on the first keystroke, it's necessary to
        # generate a star icon, even though this is more likely a typing error.
        return listicons.StarIcon(window), None
    return parseExprText(text, window)

def runIconTextEntryHandlers(entryIc, text, onAttr):
    """Look for icon text entry handlers above the entry icon and execute in order,
    until one returns a result or we hit the top.  If a handler fired, return the
    parse result and the icon whose textEntryHandler fired."""
    if text == "":
        return None, None
    for ic in entryIc.parentage(includeSelf=False):
        result = ic.textEntryHandler(entryIc, text, onAttr)
        if result is not None:
            return result, ic
    return None, None

def binOpLeftArgSite(ic):
    return 'trueExpr' if ic.__class__ == opicons.IfExpIcon else 'leftArg'

def binOpRightArgSite(ic):
    return 'falseExpr' if ic.__class__ == opicons.IfExpIcon else 'rightArg'

def searchForOpenParen(token, closeParenAt):
    """Find an open paren/bracket/brace to match an end paren/bracket/brace placed at a
    given cursor position (fromIc, fromSite).  token indicates what type of paren-like
    object is to be closed.  Returns two values: 1) the matching paren icon, and 2) the
    icon whose arguments will need to be transferred away to close the matching paren.
    This will usually be the matching paren, but if there is an intervening unclosed
    paren of a different type that owns the subsequent clauses, it will be that icon."""
    # Search first for a proper match.  This takes advantage of the fact that
    # insertOpenParen places open parens/brackets/braces at the highest level possible,
    # and shifts list elements down to the level of the innermost unclosed list, so the
    # matching icon will always be a parent or owner of the site requested.
    ic = closeParenAt
    transferArgsFrom = None
    while True:
        parent = ic.parent()
        if parent is None:
            break
        site = parent.siteOf(ic)
        ic = parent
        siteType = ic.typeOf(site)
        if siteType == 'input':
            if token == "endParen" and isinstance(ic, parenicon.CursorParenIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom
            if token == "endParen" and isinstance(ic, listicons.TupleIcon) and \
                    not ic.closed and not ic.noParens:
                # Found either an unclosed tuple (... removed if clause above to activate
                # on naked tuples, which I hope was just wrong and not needed elsewhere)
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endParen" and isinstance(ic, listicons.CallIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endBracket" and isinstance(ic, listicons.ListIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endBracket" and isinstance(ic, subscripticon.SubscriptIcon) and \
                    not ic.closed:
                # Can only match from the rightmost slice, otherwise there are colons to
                # the right which can't be left on their own
                sliceSite = ic.siteOf(closeParenAt, recursive=True)
                if sliceSite is None:
                    sliceSite = site
                if ic.hasSite('stepIcon') and sliceSite != 'stepIcon' or \
                        ic.hasSite('upperIcon') and sliceSite == 'indexIcon':
                    break
                return ic, transferArgsFrom
            if token == "endBrace" and isinstance(ic, listicons.DictIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if ic.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and ic.hasParens:
                # Don't allow search to escape enclosing arithmetic parens
                break
            rightmostSite = ic.sites.lastCursorSite()
            if ic.typeOf(rightmostSite) not in ('input', 'cprhIn') or \
                    hasattr(ic, 'closed') and ic.closed or \
                    isinstance(ic, opicons.IfExpIcon) and site == 'testExpr':
                # Anything that doesn't have an input on the right or is closed can be
                # assumed to enclose its children and search should not extend beyond.
                # Inline if is the exception in having a middle site that encloses its
                # child icon
                break
            if hasattr(ic, 'closed'):
                # Anything that is not closed does not stop search, but may require
                # argument transfer (canonical ordering ensures that the innermost
                # paren/bracket/brace will own the arguments that need transfer
                if transferArgsFrom is None:
                    transferArgsFrom = ic
    # No matching paren/bracket/brace found at the level of closeParenAt
    if token != 'endParen':
        # Braces and brackets require a match at the correct level
        return None, None
    # Arithmetic parens do not require a properly-nested match.  reorderArithExpr can
    # shift parens around even if there is not a match on the appropriate level, in
    # which case, what we need is an unclosed paren left of the end paren, and the
    # end paren not to be on the other side of code that can trap it
    matchingParen = None
    for op in reorderexpr.traverseExprLeftToRight(
            reorderexpr.highestAffectedExpr(closeParenAt), closeParenAfter=closeParenAt):
        if isinstance(op, reorderexpr.CloseParenToken) and op.parenIcon is None:
            # A CloseParenToken with parenIcon of None is the inserted end paren
            break
        if isinstance(op, reorderexpr.OpenParenToken) and isinstance(op.parenIcon,
         parenicon.CursorParenIcon) and not op.parenIcon.closed:
            matchingParen = op.parenIcon
    else:
        print('searchForOpenParen internal error: failed to find close-paren site')
    return matchingParen, None

def parseExprToAst(text):
    try:
        modAst = ast.parse(text, "Pasted text")
    except:
        return None
    if not isinstance(modAst, ast.Module):
        return None
    if len(modAst.body) != 1:
        return None
    if not isinstance(modAst.body[0], ast.Expr):
        return None
    return modAst.body[0].value

def reopenParen(ic):
    """Remove the end paren/bracket/brace from ic and deal with all the consequences to
    the surrounding icons.  Consequences include arithmetic reordering around the icon
    itself and its newly-exposed right element, and pulling-in clauses from parent
    sequences that should now belong to ic (or an un-closed child icon) per our unclosed-
    list ownership rules."""
    # If there is an attribute attached to the parens, transfer to rightmost site of
    # last element (if possible).  If not, put an entry icon between.  Also sets cursor
    # position appropriately for where the end paren/bracket/brace was.
    if isinstance(ic, parenicon.CursorParenIcon):
        lastArgSite = 'argIcon'
    elif isinstance(ic, subscripticon.SubscriptIcon):
        if ic.hasSite('stepIcon'):
            lastArgSite = 'stepIcon'
        elif ic.hasSite('upperIcon'):
            lastArgSite = 'upperIcon'
        else:
            lastArgSite = 'indexIcon'
    else:
        lastArgSite = ic.sites.argIcons[-1].name
    lastArg = ic.childAt(lastArgSite)
    attrIcon = ic.childAt('attrIcon')
    if attrIcon:
        ic.replaceChild(None, 'attrIcon')
        if lastArg is None:
            # Empty site gets attribute: create an entry icon with pending attribute
            entryIcon = EntryIcon(window=ic.window)
            entryIcon.appendPendingArgs([attrIcon])
            ic.replaceChild(entryIcon, lastArgSite)
            ic.window.cursor.setToText(entryIcon, drawNew=False)
        else :
            rightmostIc, rightmostSite = icon.rightmostSite(lastArg)
            if rightmostSite != 'attrIcon' or rightmostIc.isCursorOnlySite(rightmostSite):
                # Can't place attribute: create an entry icon to stitch attribute on
                entryIcon = EntryIcon(window=ic.window)
                entryIcon.appendPendingArgs([attrIcon])
                rightmostIc.replaceChild(entryIcon, rightmostSite)
                ic.window.cursor.setToText(entryIcon, drawNew=False)
            else:
                # attrIcon can be safely attached to the last argument
                rightmostIc.replaceChild(attrIcon, rightmostSite)
                ic.window.cursor.setToIconSite(rightmostIc, rightmostSite)
    else:
        ic.window.cursor.setToIconSite(*icon.rightmostFromSite(ic, lastArgSite))
    # Remove the end paren/bracket/brace and reorder.  reorderArithExpr treats everything
    # but operators and cursor parens as bounding (will neither go outside of those above
    # the requested icon in the hierarchy, nor descend in to those below it).  However,
    # when specifically given such an icon to reorder, it treats it (and its attribute
    # chain in the case of a subscript or call) as a special sort of paren, whose last
    # clause will be treated as exposed if the icon's "closed" field is False
    ic.reopen()
    reorderexpr.reorderArithExpr(ic)
    # Determine if the bounding icon has sequence clauses to the right of ic that now
    # need to be transferred to the newly-reopened icon or one of its children
    boundingParent, boundingParentSite = findEnclosingSite(ic)
    if boundingParent is None or not iconsites.isSeriesSiteId(boundingParentSite):
        # There was no bounding icon or the bounding icon was not a sequence
        return
    siteName, siteIdx = iconsites.splitSeriesSiteId(boundingParentSite)
    nextSite = iconsites.makeSeriesSiteId(siteName, siteIdx + 1)
    if not boundingParent.hasSite(nextSite):
        # The bounding icon has no clauses(s) beyond ic to transfer
        return
    # At this point we know boundingParent has arguments we need to transfer.  ic itself
    # may be the recipient, or it could itself hold an unclosed paren.  Determine what
    # icon should receive the arguments from boundingParent (recipient)
    rightmostIc, rightmostSite = icon.rightmostSite(ic)
    for recipient in rightmostIc.parentage():
        if recipient is ic:
            break
        if hasattr(recipient, 'closed') and not recipient.closed and not isinstance(ic,
                subscripticon.SubscriptIcon):
            break
    else:
        recipient = ic
        print("Missed reopened paren in transfer argument search")
    if isinstance(recipient, subscripticon.SubscriptIcon):
        # If recipient is a subscript, we can't transfer args, leaving an open bracket
        # with clauses following that belong to a parent. This is weird, but necessary so
        # users can adjust the right paren of a subscript that happens to be in a list.
        return
    if isinstance(recipient, parenicon.CursorParenIcon):
        # recipient is a cursor paren: change it to tuple to accept more arguments
        tupleIcon = listicons.TupleIcon(window=recipient.window, closed=False)
        arg = recipient.childAt('argIcon')
        recipient.replaceChild(None, 'argIcon')
        tupleIcon.replaceChild(arg, "argIcons_0")
        recipient.replaceWith(tupleIcon)
        recipient = tupleIcon
    # Transfer sequence clauses following the newly-opened paren/bracket/brace from
    # boundingParent to recipient, after the current last element of recipient
    name, idx = iconsites.splitSeriesSiteId(nextSite)
    numParentSites = len(getattr(boundingParent.sites, name))
    args = [boundingParent.childAt(name, i) for i in range(idx, numParentSites)]
    for i in range(idx, numParentSites):
        boundingParent.replaceChild(None, iconsites.makeSeriesSiteId(name, idx))
    insertIdx = len(recipient.sites.argIcons)
    recipient.insertChildren(args, 'argIcons', insertIdx)
    # If boundingParent was a tuple which is now down to 1 arg, remove it if it was a
    # naked tuple on the top level, or replace it with a cursor paren if it was an
    # ordinary tuple.  The reason that the ordinary tuple needs to be converted back to
    # a cursor paren has to do with the clash between the python syntax for a single-
    # element tuple (a,) and the python-g convention that an unclosed paren owns all of
    # the clauses that follow it: if the tuple owns the last comma it violates the
    # python-g convention, and if the open paren/bracket/brace owns it, it violates the
    # python syntax convention.
    if isinstance(boundingParent, listicons.TupleIcon) and idx == 1:
        if boundingParent.noParens:
            newTopIcon = boundingParent.childAt('argIcons_0')
            boundingParent.replaceChild(None, 'argIcons_0')
            recipient.window.replaceTop(boundingParent, newTopIcon)
        else:
            cvtTupleToCursorParen(boundingParent, closed=boundingParent.closed,
                typeover=boundingParent.typeoverSites()[0] is not None)

def transferToParentList(fromIc, startIdx, aboveIc, seriesSiteName='argIcons'):
    """Find a suitable parent to receive remaining arguments from a site series that
    needs to be shortened, and transfer those arguments (beginning at startIdx) to the
    selected parent if possible.  This will not be possible when an enclosing parent does
    not take a sequence (such as the testIcon site of an inline-if, or an if or while
    statement), in which case the function will do nothing and return None.  Search for
    a suitable parent begins at the parent of aboveIc (which may be the same as fromIc,
    but if fromIc is attached to an attribute site, would typically be set to the base of
    the attribute chain).  seriesSiteName is the base name of the site series.  If
    arguments were transferred, returns the icon that received them."""
    numListArgs = len(getattr(fromIc.sites, seriesSiteName))
    if numListArgs < startIdx:
        # There are no arguments to transfer
        return None
    recipient, site = findEnclosingSite(aboveIc)
    if recipient is None:
        # We reached the top of the hierarchy without getting trapped.  Add a naked tuple
        # as parent to which to transfer the arguments
        recipient = listicons.TupleIcon(window=fromIc.window, noParens=True)
        topIc = fromIc.topLevelParent()
        fromIc.window.replaceTop(topIc, recipient)
        recipient.replaceChild(topIc, 'argIcons_0')
        siteName = 'argIcons'
        siteIdx = 1
    elif iconsites.isSeriesSiteId(site):
        # Found a suitable site
        siteName, siteIdx = iconsites.splitSeriesSiteId(site)
        siteIdx += 1
    elif isinstance(recipient, parenicon.CursorParenIcon):
        # Found a cursor paren icon that can be converted to a tuple
        recipient = cvtCursorParenToTuple(recipient, recipient.closed, typeover=False)
        siteName = 'argIcons'
        siteIdx = 1
    else:
        # There are arguments to transfer, but no place to put them
        return None
    # Transfer the arguments beyond startIdx
    args = [fromIc.childAt(seriesSiteName, i) for i in range(startIdx, numListArgs)]
    for i in range(startIdx, numListArgs):
        fromIc.replaceChild(None, iconsites.makeSeriesSiteId(seriesSiteName, startIdx))
    recipient.insertChildren(args, siteName, siteIdx)
    return recipient

def findEnclosingSite(startIc):
    """Search upward in the hierarchy above startIc to find a parent that bounds the
    scope of expression-processing, such as a sequence (expressions can't cross commas)
    or parens.  If found, return the icon and site at which startIc is (indirectly)
    attached.  If the search reaches the top, return None for the icon."""
    # This is very similar to reorderexpr.highestAffectedExpr and might be worth unifying
    # with it, but note that this stops at arithmetic parens where that continues upward.
    for ic in startIc.parentage(includeSelf=True):
        parent = ic.parent()
        if parent is None:
            return None, None
        site = parent.siteOf(ic)
        if site == 'attrIcon':
            continue
        # The largest class of icons that bound expressions are sequences.  As a
        # shortcut, just look for a series site
        if iconsites.isSeriesSiteId(site):
            return parent, site
        # ic is not on a series site.  Look for the remaining types that enclose their
        # arguments but are not series: cursor-parens, auto-parens of BinOp icons,
        # statements that take single arguments, and the center site of an inline-if.
        parentClass = parent.__class__
        if parentClass in (opicons.BinOpIcon, opicons.IfExpIcon) and parent.hasParens or \
                parentClass in (opicons.DivideIcon, parenicon.CursorParenIcon,
                    subscripticon.SubscriptIcon, listicons.CprhForIcon,
                    listicons.CprhIfIcon) or \
                parentClass is opicons.IfExpIcon and site == 'testExpr' or \
                parentClass in cursors.stmtIcons:
            return parent, site

def _findParenTypeover(entryIc, token):
    """If there is an icon with active typeover matching token ("endBracket", "endBrace",
    "endParen", or "comma") directly to the right of the entry icon, return it. Note that
    pending args and attributes invalidate typeover, so if entryIc has them, there can't
    be active typeover.  If there's no active typeover to process, return None."""
    if entryIc.hasPendingArgs():
        return None
    # March up the hierarchy from the entry icon, looking for a matching paren icon
    # with active typeover
    for ic in entryIc.parentage(includeSelf=False):
        rightmostIcon, rightmostSite = icon.rightmostSite(ic)
        if rightmostIcon == entryIc:
            continue
        if isinstance(rightmostIcon, opicons.DivideIcon):
            # Divide icon has *two* sites considered next-to adjacent typeover
            # (due to how it's typed): attribute (handled above) and bottomArg
            divisor = rightmostIcon.childAt('bottomArg')
            if divisor is None and rightmostIcon is entryIc or divisor is not None and \
                    icon.rightmostSite(divisor)[0] == entryIc:
                continue
        if token == "endBracket" and ic.__class__ in (listicons.ListIcon,
                    subscripticon.SubscriptIcon) or \
                token == "endParen" and ic.__class__ in (listicons.TupleIcon,
                    listicons.CallIcon) or \
                token == "endBrace" and ic.__class__ is listicons.DictIcon:
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.endParenTypeover:
                return ic
        if token == "endParen" and ic.__class__ in (blockicons.DefIcon,
                    blockicons.ClassDefIcon):
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.rParenTypeover:
                return ic
        if token == "comma" and ic.__class__ in (listicons.TupleIcon, listicons.DictIcon):
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.commaTypeover:
                return ic
    return None

def splitExprAtIcon(splitAt, splitTo, replaceLeft, replaceRight):
    """Split a (paren-less) arithmetic expression in two parts at splitAt, up to splitTo.
    Returns everything lexically left of split at in the first returned value and
    everything right of it in the second.  The call replaces splitAt with two values, one
    for the left expression, replaceLeft, and one for the right, replaceRight. It is safe
    to pass None as splitTo, provided that the top level is the appropriate stopping
    point.  It is important to note that this call expects that splitTo has already been
    vetted as holding the root of the expression (probably by findEnclosingSite), and
    will fail badly if it does not."""
    if splitAt.parent() is None:
        return None, splitAt
    leftArg = replaceLeft
    rightArg = replaceRight
    child = splitAt
    for parent in list(splitAt.parentage(includeSelf=False)):
        childSite = parent.siteOf(child)
        childSiteType = parent.typeOf(childSite)
        if parent is splitTo:
            break
        if isinstance(parent, opicons.UnaryOpIcon):
            leftArg = parent
        elif childSiteType == 'input' and (isinstance(parent, infixicon.InfixIcon) or
                parent.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and not
                parent.hasParens):
            # Parent is a binary op icon without parens, and site is one of the two
            # input sites
            if parent.leftArg() is child:  # Insertion was on left side of operator
                parent.replaceChild(rightArg, binOpLeftArgSite(parent))
                rightArg = parent
            elif parent.rightArg() is child:  # Insertion on right side of operator
                parent.replaceChild(leftArg, binOpRightArgSite(parent))
                leftArg = parent
            else:
                print('Unexpected site attachment in "splitExprAtIcon" function')
                return None, None
        elif childSiteType == 'attrIn':
            leftArg = parent
        else:
            # Parent was not an arithmetic operator or had parens
            print('Bounding expression found in "splitExprAtIcon" function')
            return None, None
        if child is splitAt and childSiteType == 'attrIn':
            parent.replaceChild(None, childSite)
        child = parent
    else:
        if splitTo is not None:
            print('"splitExprAtIcon" function reached top without finding splitTo')
            return None, None
    return leftArg, rightArg

def _canCloseParen(entryIc):
    """Determine if it is safe to close a newly-entered open-paren/bracket/brace.  Also
    used when close of an open cursor-paren has been deferred until we know what sort of
    paren it is."""
    if entryIc.hasPendingArgs():
        return False
    if entryIc.attachedIcon() is not None:
        seqIc, seqSite = findEnclosingSite(entryIc)
        if seqIc:
            rightmostIc, rightmostSite = icon.rightmostFromSite(seqIc, seqSite)
            if rightmostIc is not entryIc and \
                    entryIc.siteOf(rightmostIc, recursive=True) is None:
                return False
    return True

def _removeHighlights(icTree):
    """Remove highlight property from icons in icTree.  This is called automatically by
    setProperty, but is sometimes invoked explicitly when the existing pending arg may
    have already been linked somewhere else."""
    if icTree is not None and not isinstance(icTree, EntryIcon):
        _removeHighlight(icTree)
        for ic in icTree.children():
            _removeHighlights(ic)

def _removeHighlight(ic):
    if ic is not None and hasattr(ic, 'highlight'):
        ic.window.undo.registerCallback(_addHighlight, ic, ic.highlight)
        del ic.highlight

def _addHighlight(ic, highlight):
    if ic is not None:
        ic.highlight = highlight
        ic.window.undo.registerCallback(_removeHighlight, ic)

def _addHighlights(icTree, highlight):
    """Add highlight property to icTree and all of its children"""
    if icTree is not None:
        _addHighlight(icTree, highlight)
        for ic in icTree.children():
            _addHighlights(ic, highlight)

def _appendOperator(newOpIcon, onIcon, onSite):
    """Stitch a binary operator in at onIcon, onSite and reorder the surrounding
    expression.  Returns the icon and site at which the cursor or entry icon should be
    placed upon completion."""
    argIcon = icon.findAttrOutputSite(onIcon)
    onIcon.replaceChild(None, onSite)
    leftArg = argIcon
    rightArg = None
    childOp = argIcon
    stopAtParens = False
    cursorIcon = cursorSite = None
    # Walk up the hierarchy of binary operations, breaking each one in to left and
    # right operands for the new operation.  Stop when the parent operation has
    # lower precedence, or is not a binary operation.  Also stop if the parent
    # operation has equal precedence, and the associativity of the operation matches
    # the side of the operation on which the insertion is being made.
    for op in argIcon.parentage():
        if stopAtParens or op.__class__ not in (opicons.BinOpIcon, opicons.IfExpIcon,
                opicons.UnaryOpIcon) or newOpIcon.precedence > op.precedence or \
                newOpIcon.precedence == op.precedence and (
                 op.leftAssoc() and op.leftArg() is childOp or
                 op.rightAssoc() and op.rightArg() is childOp):
            op.replaceChild(newOpIcon, op.siteOf(childOp))
            break
        if op.__class__ is opicons.IfExpIcon and op.siteOf(childOp) == "testExpr":
            op.replaceChild(newOpIcon, op.siteOf(childOp))
            break
        if op.__class__ is opicons.UnaryOpIcon:
            op.replaceChild(leftArg, "argIcon")
            leftArg = op
        else:  # BinaryOp
            if op.leftArg() is childOp:  # Insertion was on left side of operation
                op.replaceChild(rightArg, binOpLeftArgSite(op))
                if op.leftArg() is None:
                    cursorIcon, cursorSite = op, binOpLeftArgSite(op)
                rightArg = op
            else:                       # Insertion was on right side of operation
                op.replaceChild(leftArg, binOpRightArgSite(op))
                leftArg = op
            if op.hasParens:
                # If the op has parens and the new op has been inserted within them,
                # do not go beyond the parent operation
                stopAtParens = True
        childOp = op
    else:  # Reached the top level without finding a parent for newOpIcon
        onIcon.window.replaceTop(childOp, newOpIcon)
    leftSite = "topArg" if newOpIcon.__class__ is opicons.DivideIcon else \
        binOpLeftArgSite(newOpIcon)
    rightSite = "bottomArg" if newOpIcon.__class__ is opicons.DivideIcon else \
        binOpRightArgSite(newOpIcon)
    if isinstance(newOpIcon, opicons.IfExpIcon):
        cursorIcon, cursorSite = newOpIcon, 'testExpr'
    elif rightArg is None:
        cursorIcon, cursorSite = newOpIcon, rightSite
    newOpIcon.markLayoutDirty()
    newOpIcon.replaceChild(leftArg, leftSite)
    newOpIcon.replaceChild(rightArg, rightSite)
    # The conventional method to type a division operation with lower precedent
    # operator(s) in the numerator is to use parenthesis.  However because of our
    # vertical arrangement, those parens are thereafter unnecessary and unaesthetic.
    # Removing them here (when the divide icon is first inserted) rather than as a
    # general rule in filterRedundantParens, allows the user to add them back later
    # if needed for subsequent edits and not be unexpectedly removed.
    if newOpIcon.__class__ is opicons.DivideIcon:
        topArgChild = newOpIcon.childAt('topArg')
        if isinstance(topArgChild, parenicon.CursorParenIcon) and topArgChild.closed:
            newOpIcon.replaceChild(topArgChild.childAt('argIcon'), 'topArg')
    return cursorIcon, cursorSite

def cvtCursorParenToTuple(parenIcon, closed, typeover):
    tupleIcon = listicons.TupleIcon(window=parenIcon.window, closed=closed,
        typeover=typeover)
    arg = parenIcon.childAt('argIcon')
    attr = parenIcon.childAt('attrIcon') if parenIcon.closed else None
    parenIcon.replaceChild(None, 'argIcon')
    parenIcon.replaceWith(tupleIcon)
    tupleIcon.replaceChild(arg, 'argIcons_0')
    if attr and closed:
        parenIcon.replaceChild(None, 'attrIcon')
        tupleIcon.replaceChild(attr, 'attrIcon')
    return tupleIcon

def cvtTupleToCursorParen(tupleIcon, closed, typeover):
    arg = tupleIcon.childAt("argIcons_0")
    attr = tupleIcon.childAt('attrIcon') if tupleIcon.closed else None
    tupleIcon.replaceChild(None, 'argIcons_0')
    newParen = parenicon.CursorParenIcon(window=tupleIcon.window, closed=closed,
        typeover=typeover)
    newParen.replaceChild(arg, 'argIcon')
    tupleIcon.replaceWith(newParen)
    if attr and closed:
        tupleIcon.replaceChild(None, 'attrIcon')
        newParen.replaceChild(attr, 'attrIcon')
    return newParen
