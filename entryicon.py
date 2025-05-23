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
import commenticon
import cursors
import reorderexpr
import filefmt

PLAIN_BG_COLOR = (255, 255, 255, 255)
FOCUS_BG_COLOR = (255, 242, 242, 255)
OUTLINE_COLOR = (230, 230, 230, 255)

# Gap to be left between the entry icon and next icons to the right of it
ENTRY_ICON_GAP = 3

PEN_MARGIN = 6

# Maximum number of characters for a single paste operation into an entry icon
MAX_ENTRY_PASTE = 80

compareOperators = {'<', '>', '<=', '>=', '==', '!='}
binaryOperators = {'+', '-', '*', '**', '/', '//', '%', '@', '<<', '>>', '&', '|', '^'}
unaryOperators = {'+', '-', '~', 'not'}
unaryNonKeywordOps = {'+', '-', '~'}
emptyDelimiters = {' ', '\t', '\n', '\r', '\f', '\v'}
delimitChars = {*emptyDelimiters, '(', ')', '[', ']', '}', ':', '.', ';', '@', '=', ',',
 '-', '+', '*', '/', '<', '>', '%', '&', '|', '^', '!', '#'}
keywords = {'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield', 'await'}
noArgStmts = {'pass', 'continue', 'break', 'else', 'finally'}

identPattern = re.compile('^[a-zA-Z_][a-zA-Z_\\d]*$')
numPattern = re.compile('^[+-]?(([\\d_]*\\.?[\\d_]*)|(0[xX][0-9a-fA-F]*)|(0[oO][0-7]*)|'
 '(((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*))?$')
attrPattern = re.compile('^\\.[a-zA-Z_][a-zA-Z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-Z#\\d_.\\(\\[\\{\\s+-~"\']')
stringPattern = re.compile("^(f|fr|rf|b|br|rb|u|r)?['\"]$", re.IGNORECASE)
textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

# The EntryCreationTracker is a context manager that allows the caller to find all of the
# entry icons that were created within its scope, that are still alive in a given window.
# This is used to find placeholder entry icons created deep in the editing code, to
# override cursor placement.
entryRegistries = []

penImage = comn.asciiToImage((
    "....oooo....",
    "...o%%%%oo..",
    "..o%%%%%%%oo",
    "..o%%%%%%%%%",
    ".o%%%%55%%%%",
    "o77777777%%%",
    ".o%%%%55%%%%",
    "..o%%%%%%%%%",
    "..o%%%%%%%oo",
    "...o%%%%oo..",
    "....oooo...."))
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
        self.sites.add('seqIn', 'seqIn', 0, 0)
        seqOutIndent = comn.BLOCK_INDENT if willOwnBlock else 0
        self.sites.add('seqOut', 'seqOut', seqOutIndent, self.height-1)
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
            self.addCodeBlock()
        registerEntryIconCreation(self)

    def addCodeBlock(self):
        """Change the entry icon to its block-owning form (used for temporarily holding
        the code block from a block-owning statement such as 'if' or 'for'."""
        if hasattr(self, 'blockEnd'):
            return
        self.blockEnd = icon.BlockEnd(self, self.window)
        self.sites.seqOut.attach(self, self.blockEnd)
        self.window.undo.registerCallback(self.addCodeBlock)

    def removeCodeBlock(self):
        """Change the entry icon to its non-block-owning form (block-owning form is used
        to temporarily hold a code block from a block-owning statement such as 'if')."""
        if not hasattr(self, 'blockEnd'):
            return
        nextIc = self.nextInSeq()
        if nextIc is not None and nextIc is not self.blockEnd:
            print('Removing non-empty code block from entry icon!')
        if nextIc is not None:
            self.replaceChild(None, 'seqOut')
        self.window.undo.registerCallback(self.addCodeBlock)

    def restoreForUndo(self, text):
        """Undo restores all attachments and saves the displayed text.  Update the
        remaining internal state based on attachments and passed text."""
        self.text = text
        self.setCursorPos('end')
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

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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

    def focusOut(self, removeIfPossible=True, removeIfNotFocused=False):
        """Remove cursor focus from the icon.  If removeIfPossible is True, try to place
        the text as it currently stands, replacing the entry icon with whatever it
        generates.  Returns False only if removal was requested and current text or
        pending arguments prevent it from being placed.  Otherwise, the function will
        return either True, or "merged" (see below).  If it succeeds, the cursor will
        be placed to the right of whatever icon(s) the text generated, as if a delimiter
        had been entered (while most callers will immediately override this, the
        arrowAction method depends upon this side effect for right-arrow cursor movement
        out of the icon).  It is important to note that because this function gets called
        as a result of cursor movement, the fact that it can rearrange icon structure has
        far-reaching consequences: all cursor-movement calls now need to be followed by
        layout/refresh/redraw.  focusOut also handles the special case of an entry icon
        attached to the forCursor site of another entry icon.  This is allowed so that an
        operator following an entry icon can be edited normally, but is not allowed to
        persist once editing is complete.  In the case where the entry icon is attached
        to another entry icon by its forCursor site and focusOut is called but cannot
        place its content, it merges the icon with the parent and returns the special
        result "merged"."""
        if not self.hasFocus and not removeIfNotFocused:
            return not removeIfPossible
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
            parent = self.parent()
            if isinstance(parent, EntryIcon) and parent.siteOf(self) == 'forCursor':
                # An entry icon is allowed to be (temporarily) attached to the forCursor
                # site of another entry icon.  Most such attachments are never visible to
                # the  user, except in the case where an operator with an entry icon as
                # its right operand is edited, and these are only allowed to persist as
                # long as the attached entry icon has focus.  At this point, the icons
                # are consolidated.
                pendingArgs = self.listPendingArgs()
                self.popPendingArgs('all')
                parent.cursorPos = len(parent.text)
                parent.text += self.text
                parent.replaceChild(None, 'forCursor')
                parent.appendPendingArgs(pendingArgs)
                self.window.cursor.setToText(parent)
                return "merged"
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
        if isinstance(argList[0], EntryIcon) and not self.hasPendingArgs() and \
                argList[0].text == '':
            # The first entry is another entry icon, and we have no existing args.
            # Instead of embedding it in the pending arg list, consume it (take over its
            # pending args and remove it).  Note that we don't consume in the case where
            # there is text in the other icon, even though there are circumstances where
            # this would be the right thing to do, because Alt-clicking to edit will
            # overstep its bounds and merge text that we probably don't want merged
            # (though maybe the right way to do this would be to explicitly stop those
            # particular commands from doing it, rather than to stop everything)
            entryIc = argList[0]
            pendingArgs = entryIc.listPendingArgs()
            entryIc.popPendingArgs('all')
            self.appendPendingArgs(pendingArgs)
            #self.text += entryIc.text  # self.cursor stays before any appended text
            #entryIc.text = ''
            argList = argList[1:]
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
            else:
                self.replaceChild(arg, siteName)

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
                        self.replaceChild(None, removeSiteId)
                    if sum(1 for s in siteOrSeries if s.att is not None) == 0:
                        # No remaining children in the series, remove the site series
                        sitesToRemove.append(siteOrSeries)
                    break
                else:
                    # Remove entire list
                    for i in range(len(siteOrSeries)):
                        removeSiteId = f'pendingArg{siteOrSeries.order}_{i}'
                        self.replaceChild(None, removeSiteId, leavePlace=True)
            else:
                removeSiteId = f'pendingArg{siteOrSeries.order}'
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
                # Turn the series to a single input site containing just the first element
                firstArg = pendingArgs[-1][0]
                lastArg = pendingArgs[-1][-1]
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
            lowestIc.replaceChild(None, lowestSite)
            self.replaceChild(lowestArg, 'pendingArg0')
        if self.attachedSiteType() == 'attrIn':
            outIc = icon.findAttrOutputSite(self.attachedIcon())
        else:
            outIc = self
        outIc.replaceWith(pendingArg)
        lowestIc.replaceChild(outIc, lowestSite)
        reorderexpr.reorderArithExpr(pendingArg)

    def pruneEmptyPendingArgSites(self):
        """Removes any pending arg sites with no icons attached.  If empty sites are
        found, also compress the site numbering that was used to signal empty arguments
        in the original icons that were disassembled (once the user starts tearing down
        the list, we assume that they're not expecting focus-out to re-build the original
        icon as it was."""
        # Find empty sites
        sitesToRemove = []
        for siteOrSeries in list(self.iteratePendingSiteList()):
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                for site in siteOrSeries:
                    if site.att is not None:
                        break
                else:
                    sitesToRemove.append(siteOrSeries)
            elif siteOrSeries.att is None:
                sitesToRemove.append(siteOrSeries)
        if len(sitesToRemove) == 0:
            return  # Don't compress site numbering if nothing was removed
        # Remove them
        for site in sitesToRemove:
            self.removePendingArgSite(site.order)
        # Renumber the remaining sites to remove gaps in numbering
        for i, site in enumerate(list(self.iteratePendingSiteList())):
            self.renamePendingArgSite(site.order, i)

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

    def addText(self, text):
        """Add a single character or text at the cursor.  If that resulted in changes to
        the icon structure in the window, also adds an undo boundary.  Note that while
        most commands add an undo boundary after all icon manipulation is finished,
        addText only adds one on word boundaries, or if it modified the icon structure,
        and may generate undo records *after* adding the boundary, leaving the undo stack
        "unterminated".  This also handles spaces, as both a command to complete the
        current entry, and as in internal space following "async" and 'not".  Returns
        error string on failure, None on success."""
        if len(text) > MAX_ENTRY_PASTE:
            text = text[:MAX_ENTRY_PASTE]
        if text in '->' and isinstance(self.attachedIcon(), blockicons.DefIcon) and \
                self.attachedSite() == 'returnType':
            # In all other cases, typeover is to the right of the cursor or entry icon,
            # but for DefIcon return type annotation, we preemptively leap over the
            # (normally typed) '->' and trim the characters out of the entry icon,
            # implicitly assuming (hmm...) that types won't start with '-' or '>'
            self.text = ''
            self.setCursorPos(0)
            return None
        if len(text) > 1:
            # This is a multi-character paste, and could come from anywhere.  Trim and
            # Filter out non-usable characters.  We accept all of the printable ascii
            # characters, as well as the weird Unicode ones that Python 3.0 allows in
            # identifiers (via the string .isidentifier() method), though some of these
            # may not be available in our chosen font.
            text = text.replace('\t', '    ')
            chars = [c for c in text if 32 <= ord(c) < 0xff or c.isidentifier()]
            if len(chars) < len(text):
                text = ''.join(chars)
        if text == ' ' and len(self.text) == 0:
            # There's nothing to parse.  A user typing a space in an empty entry icon
            # means "parse this", indicating "get rid of the entry ic" (if possible)
            self.remove()
            return None
        if text == ' ' and not (self.text[:3] == 'not' and self.cursorPos == 3 and
                self.attachedToAttribute() or
                self.text[:5] in ('async', 'yield') and self.cursorPos == 5):
            # Move the space to the end to turn it in to command to delimit from any
            # cursor position.  Note above the exceptions for "async" and "not".  In
            # these cases the user needs to be able to be able to insert an internal
            # space in the text, so we can't take this action.
            newText = self.text + text
            newCursorPos = len(newText)
        else:
            newText = self.text[:self.cursorPos] + text + self.text[self.cursorPos:]
            newCursorPos = self.cursorPos + len(text)
        rejectMessage = self._setText(newText, newCursorPos)
        if rejectMessage is not None:
            # the resulting text was rejected.  If cursorPos was as the end of the
            # entry (or space was typed to add a delimiter), beep and do not update.
            # If not, just enter the updated text
            if newCursorPos == len(newText):
                if text == ' ':
                    # User added space delimiter.  If we had something that would
                    # otherwise have been self delimiting, try again w/o the delimiter.
                    parseResult, _, _ = self.parseEntryText(self.text)
                    if parseResult == 'accept':
                        return rejectMessage
                    if self._setText(self.text, newCursorPos-1) is not None:
                        return rejectMessage
                else:
                    # Prohibit the character (caller will beep and present message)
                    return rejectMessage
            else:
                # Allow insertion, even though it's bad, because user is "editing", and
                # may go through bad states to get to good ones.
                self.text = newText
                self.setCursorPos(newCursorPos)
        self.markLayoutDirty()
        return None

    def clearText(self):
        """(Quietly) remove all of the current text content, leaving the icon in place."""
        self.text = ''
        self.cursorPos = 0

    def backspaceInText(self, evt=None):
        if self.text != "" and self.cursorPos != 0:
            # Erase the character before the text cursor
            self.window.requestRedraw(self.topLevelParent().hierRect())
            self.text = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
            self.setCursorPos(self.cursorPos - 1)
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
        highestIcon = iconsites.highestCoincidentIcon(self)
        parent = highestIcon.parent()
        if parent is None:
            return  # Can't place and can't back up any further
        # Check if we're attached to another entry icon, either on the forCursor site
        # or as an individual pending argument, and if so, merge our content in to the
        # parent icon.  Note that punting the case where the entry icon is part of a
        # pending argument series, does leave some cases on the table that should
        # still be addressed, but the combination of directly nested entry icons and
        # pending lists is quite rare, this is not worth wasting time on, yet.
        parentSite = parent.siteOf(self, recursive=True)
        if isinstance(parent, EntryIcon) and not iconsites.isSeriesSiteId(parentSite):
            if parentSite == parent.sites.firstCursorSite():
                # We directly follow another entry icon, either on its forCursorSite, or
                # as its first pending arg
                pendingArgs = self.listPendingArgs()
                self.popPendingArgs('all')
                if parentSite == 'forCursor':
                    # forCursor site.  If this is reached, something is wrong, because if
                    # we have focus, then the parent entry icon does not, and therefore
                    # should not be allowed to hold anything on its forCursor site
                    print("On other icon's forCursorSite?")
                    parent.replaceChild(None, 'forCursor')
                    parent.appendPendingArgs(pendingArgs)
                else:
                    # First pending arg site, remove from pending args
                    parentPendingArgs = parent.listPendingArgs()
                    if parent is self.parent():
                        # We are the direct descendant of the other entry icon: just
                        # remove its first pending arg
                        parent.popPendingArgs('all')
                        parent.appendPendingArgs(pendingArgs + parentPendingArgs[1:])
                    else:
                        # We are embedded in an expression: leave the expression, but
                        # still prepend our pending args to the parent and delete this
                        # entry icon (self) from the expression
                        parent.popPendingArgs('all')
                        self.replaceWith(None)
                        parent.appendPendingArgs(pendingArgs + parentPendingArgs)
                parent.cursorPos = len(parent.text)
                parent.text += self.text
                cursor.setToText(parent)
                return
            # We are in the parent entry icon's pending arg list, but not on the left
            # side, so if there's text, we can't merge it in to the parent, so drop thru
            # and try to attach to the previous arg.  If there's no text, merge our
            # pending args with those of the parent.
            if self.text == '':
                # I don't think this code block ever runs!  The code at the start of the
                # function (if self.text == '':) handles 90% of cases and the rest seem
                # to be handled by the next clause (if self.camPlaceEntryText).  Have not
                # been able to test, but haven't removed, since I think I wrote it in
                # response to a failure of some sort.
                print('Unexercised code exercised!  look in entryIcon.py')
                pendingArgs = self.listPendingArgs()
                self.popPendingArgs('all')
                parentPendingArgs = parent.listPendingArgs()
                parent.popPendingArgs('all')
                idx = parentPendingArgs.index(self)
                parent.appendPendingArgs(parentPendingArgs[:idx] + pendingArgs +
                    parentPendingArgs[idx+1:])
                cursorSite = 'pendingArg%d' % idx
                if parent.hasSite(cursorSite):
                    cursorIcon = parent
                elif parent.hasSite(cursorSite + '_0'):
                    cursorIcon = parent
                    cursorSite += '_0'
                else:
                    cursorIcon, cursorSite = icon.rightmostSite(parent)
                cursor.setToIconSite(cursorIcon, cursorSite)
                return
        # If we can't focus out, backspace in to the next icon.  This is done by
        # temporarily removing the text cursor from the entry icon and putting an icon
        # cursor on the site to which it is currently attached, then calling the
        # backspace method for the icon.  If this results in a new entry icon, reconcile
        # that with the content of self.
        cursor.setToIconSite(parent, parent.siteOf(highestIcon),
            placeEntryText=False)
        cursor.icon.backspace(cursor.site, evt)
        if self.parent() is None and self not in self.window.topIcons:
            # The new entry icon consumed our content, so we're done
            return
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
            print('Entry icon backspaceInText: Unexpected entry icon from backspace')
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
            self.setCursorPos(len(newEntryIcon.text))
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
                if self._setText(self.text + ' ', len(self.text)) is not None:
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
        combinedText = self.text + entryIc.text
        if rightIcIsPendingArg:
            ic, idx, seriesIdx = icon.firstPlaceListIcon(self.listPendingArgs())
            if isinstance(ic, EntryIcon) or self.typeOf(self.siteOf(ic)) == \
                    self.attachedSiteType():
                entryIc.text = combinedText
                entryIc.setCursorPos(len(self.text))
                self.popPendingArgs(idx, seriesIdx)
                self.replaceWith(ic)
                cursor.setToText(entryIc)
            else:
                # Can't simply replace ourselves with the pending arg because site type
                # is not compatible.  Need to leave an empty site and remove the new
                # entry icon, instead
                self.setCursorPos('end')
                self.text = combinedText
                if entryIc.hasPendingArgs():
                    pendArgs = entryIc.popPendingArgs('all')
                    self.appendPendingArgs(pendArgs)
                entryIc.replaceWith(None)
                cursor.setToText(self)
        else:
            entryIc.text = combinedText
            entryIc.setCursorPos(len(self.text))
            entryIcSiteOnSelf = self.siteOf(entryIc, recursive=True)
            if entryIcSiteOnSelf is not None:
                entryIcTopIc = self.childAt(entryIcSiteOnSelf)
                self.replaceChild(None, entryIcSiteOnSelf)
                # entryIcTopIc must be an entry icon, because that's all we allow on
                # forCursor sites, so can use replaceWith even if site types don't match
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
                    cursorIcon = self.attachedIcon()
                    cursorSite = self.attachedSite()
                    # For 99.99% of cases, set the cursor position to the attached site
                    # but if the parent icon is an entry icon, and focusing out resulted
                    # in merging the content, leave the cursor where focusOut put it.
                    if self.focusOut() != 'merged':
                        self.window.cursor.setToIconSite(cursorIcon, cursorSite)
                self.window.refreshDirty(minimizePendingArgs=False)
            else:
                self.setCursorPos(self.cursorPos - 1)
        elif direction == "Right":
            if self.cursorPos == len(self.text):
                # Move cursor out of entry icon.  For right cursor movement, use the
                # focusOut because it leaves the cursor after the new icon(s)
                parent = self.parent()
                focusOutResult = self.focusOut()
                if focusOutResult == False:
                    # We failed to place, cursor is still in icon
                    cursor.setToIconSite(self, self.sites.firstCursorSite())
                elif focusOutResult == "merged":
                    # Focusing out merged the entry icon into its parent entry icon.  Put
                    # the cursor after that, instead
                    cursor.setToIconSite(parent, parent.sites.firstCursorSite())
                self.window.refreshDirty(minimizePendingArgs=False)
            else:
                self.setCursorPos(self.cursorPos + 1)
        elif direction in ('Up', 'Down'):
            x, y = self.cursorWindowPos()
            self.window.cursor.erase()
            cursorType, ic, site, pos = cursors.geometricTraverseFromPos(x, y,
                direction, self.window, self)
            if cursorType == 'window':
                cursorType = 'icon'
                site = {'Up': 'seqIn', 'Down': 'seqOut'}[direction]
                ic = self
            if cursorType == 'icon' and ic is self:
                # Geometric traversal would put the cursor on one of our sites.  Setting
                # the cursor to an icon site means focusing out, which could remove the
                # entry icon.  Instead, make the focusOut call preemptively, and if we
                # do get deleted, put the cursor in a reasonable place.  focusOut will
                # put the cursor at the right of the new icon, but if eometricTraverse
                # chose one of our sequence sites, put it in a sequence site.
                focusResult = self.focusOut(True)
                if focusResult:
                    ic = self.window.cursor.icon
                    if site in ('seqIn', 'seqOut'):
                        ic = self.window.cursor.icon.topLevelParent()
                    else:
                        ic = self.window.cursor.icon
                        site = self.window.cursor.site
            self.window.cursor.setTo(cursorType, ic, site, pos)
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
                pendingArgList = self.listPendingArgs()
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
                    firstArg, firstArgIdx, firstArgSeriesIdx = icon.firstPlaceListIcon(
                        pendingArgList)
                    isSingleArg = firstArgIdx == len(pendingArgList) - 1 and \
                        firstArgSeriesIdx is None
                    if forceDelete or makePlaceholder or isSingleArg:
                        # Place the first argument on the top level.  If it's a
                        # comprehension or other icon that gets a canonical substitution
                        # at the top level, use its replacement.
                        self.popPendingArgs(firstArgIdx, firstArgSeriesIdx)
                        subsIc = listicons.subsCanonicalInterchangeIcon(firstArg)
                        if subsIc is not None:
                            firstArg = subsIc
                        self.window.replaceTop(self, firstArg)
                        parentSites = firstArg.parentSites()
                        if parentSites:
                            self.window.cursor.setToIconSite(firstArg, parentSites[0])
                        elif firstArg.hasSite('seqIn'):
                            # If the icon was substituted, it may now have a seqIn site
                            self.window.cursor.setToIconSite(firstArg, 'seqIn')
                        if makePlaceholder and not isSingleArg:
                            rightmostIcon, rightmostSite = icon.rightmostSite(firstArg)
                            rightmostIcon.replaceChild(self, rightmostSite)
                    else:
                        # We would have been able to place the first pending argument on
                        # the top level, but there are more pending arguments that we're
                        # not allowed to delete or add to a placeholder, so give up.
                        return False
                elif isinstance(pendingArgList[0], (listicons.CprhForIcon,
                        listicons.CprhIfIcon)):
                    # The entry icon is part of a sequence, and the first pending
                    # argument is a comprehension clause.  While a comprehension site
                    # can't be linked in to a sequence, the canonical interchange form
                    # of a comprehension clause icon is a 'for' or 'if' icon, which does
                    # have sequence sites, so it can be linked in to the sequence
                    if forceDelete or makePlaceholder or len(pendingArgList) == 1:
                        # Pull the (comprehension clause) first element off of the
                        # pending args list, and fetch its canonical substitute.
                        firstArg = pendingArgList[0]
                        self.popPendingArgs(0)
                        firstArg = listicons.subsCanonicalInterchangeIcon(firstArg)
                        # Splice it in to the sequence
                        self.window.replaceTop(self, firstArg)
                        self.window.cursor.setToIconSite(firstArg, 'seqIn')
                        # If there are still arguments left, reattach the entry icon
                        # on the rightmost site of the element we just placed
                        if makePlaceholder and self.hasPendingArgs():
                            rightmostIcon, rightmostSite = icon.rightmostSite(firstArg)
                            rightmostIcon.replaceChild(self, rightmostSite)
                    else:
                        # We're not allowed to delete or add to a placeholder, so give up
                        return False
                else:
                    # The entry icon is part of a sequence, and the first pending
                    # argument can not be part of a sequence, so give up on placing args
                    # and either dump all of them (if forceDelete is True), or give up
                    # and return False (if forceDelete is False).  This is done
                    # regardless of makePlaceholder, as it's the first arg that failed.
                    if not forceDelete:
                        return False
                    prevIcon = self.prevInSeq(includeModuleAnchor=True)
                    nextIcon = self.nextInSeq()
                    self.window.removeIcons([self])
                    if prevIcon:
                        self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                    elif nextIcon and not (hasattr(self, 'blockEnd') and
                            nextIcon is self.blockEnd):
                        self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                    else:
                        self.window.cursor.setToWindowPos(self.posOfSite('output'))
            else:
                # No pending arguments
                prevIcon = self.prevInSeq(includeModuleAnchor=True)
                nextIcon = self.nextInSeq()
                stmtComment = self.hasStmtComment()
                if hasattr(self, 'blockEnd'):
                    self.window.removeIcons([self, self.blockEnd])
                else:
                    self.window.removeIcons([self])
                if stmtComment is not None:
                    # The entry icon was top-level statement and (before the remove),
                    # owned a comment which presumably removeIcons has now converted into
                    # a line-comment and put in our place.
                    if not stmtComment in self.window.topIcons:
                        print("Removed entry icon with stmt comment, expected "
                            "removeIcons to insert as line comment")
                    self.window.cursor.setToIconSite(stmtComment, 'prefixInsert')
                elif prevIcon:
                    self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                elif nextIcon and not (hasattr(self, 'blockEnd') and
                        nextIcon is self.blockEnd):
                    self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                else:
                    self.window.cursor.setToWindowPos(self.posOfSite('output'))
        else:
            # Entry icon is attached to another icon.  Use the _placePendingArgs method
            # to check and place the pending args (so this code can be shared with
            # _setText which needs to do the exact same thing).
            if not self._canPlacePendingArgs(attachedIcon, attachedSite,
                    overwriteStart=True, useAllArgs=not makePlaceholder):
                if not forceDelete:
                    return False
            subsIc = self._placePendingArgs(attachedIcon, attachedSite,
                overwriteStart=True)
            if subsIc is None:
                cursorIcon = attachedIcon
                cursorSite = attachedSite
            else:
                cursorIcon = subsIc
                cursorSite = 'argIcons_0'
            # If the entry icon is still attached somewhere, remove it
            if self.attachedIcon() is not None:
                self.attachedIcon().replaceChild(None, self.attachedSite(),
                    leavePlace=True)
            # Place the cursor where the entry icon was
            if cursorIcon.hasSite(cursorSite):
                self.window.cursor.setToIconSite(cursorIcon, cursorSite)
            else:  # The last element of list can disappear when entry icon is removed
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(cursorSite)
                newSite = iconsites.makeSeriesSiteId(seriesName, seriesIdx - 1)
                self.window.cursor.setToIconSite(cursorIcon, newSite)
        self.window.requestRedraw(redrawRect)
        return True

    def removeIfEmpty(self):
        """Remove the icon if it has no text and no pending arguments."""
        if self.text == '' and not self.hasPendingArgs():
            self.remove()

    def selectIfFirstArgSelected(self):
        """If the entry icon's first pending argument is selected, select it, as well.
        Call this after creating a new entry icon and adding pending arguments as a
        simple way to match the selection status of the icons being encapsulated."""
        siteId = self.sites.firstCursorSite()
        if siteId == 'forCursor':
            return
        firstIc = self.childAt(siteId)
        if firstIc is None:
            return
        if firstIc.isSelected():
            self.select(True)

    def parseEntryText(self, newText):
        """Parse proposed text for the entry icon.  Returns three values: 1) the parse
        result, one of "accept", "reject:reason", "typeover", "comma", "colon",
        "openBracket", "endBracket" "openBrace", "endBrace", "openParen", "endParen",
        "makeFunction", "makeSubscript", or a pair of a created icon and delimiter.
        2) If the text was processed by a per-icon textHandler method, the responsible
        icon, 3) A boolean  value indicating that the text represents a statement that
        needs to be prepended to the attached icon, as opposed to being inserted at the
        site."""
        if self.attachedToAttribute():
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=True)
            if parseResult is None:
                parseResult = parseAttrText(newText, self.window)
        elif self.attachedIcon() is None or self.attachedSite() in ('seqIn', 'seqOut'):
            handlerIc = None
            parseResult = parseTopLevelText(newText, self.window)
            if wasRejected(parseResult) and self.childAt('seqIn') is None and \
                    self.childAt('seqOut') is None:
                altParseResult = parseWindowBgText(newText, self.window)
                if not wasRejected(altParseResult):
                    parseResult = altParseResult
        else:  # Currently no other cursor places, must be expr
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=False)
            if parseResult is None:
                coincIcon, coincSite = iconsites.highestCoincidentSite(
                    self.attachedIcon(), self.attachedSite())
                forSeries = iconsites.isSeriesSiteId(coincSite)
                parseResult = parseExprText(newText, self.window, forSeriesSite=forSeries)
        if wasRejected(parseResult) and self.attachedSiteType() == 'input':
            coincidentSite = self.attachedIcon().hasCoincidentSite()
            if coincidentSite is not None and coincidentSite == self.attachedSite():
                highestCoincIcon = iconsites.highestCoincidentIcon(self.attachedIcon())
                if highestCoincIcon.parent() is None and \
                        not isinstance(highestCoincIcon, assignicons.AssignIcon):
                    # Site is coincident with the start of the statement. We might be
                    # able to prepend a top-level statement
                    altParseResult = parseTopLevelText(newText, self.window)
                    if len(altParseResult) == 2 and \
                            altParseResult[0].__class__ in cursors.stmtIcons and \
                            not isinstance(altParseResult[0], nameicons.NoArgStmtIcon):
                        return altParseResult, handlerIc, True
        return parseResult, handlerIc, False

    def _setText(self, newText, newCursorPos):
        """Process the text in the icon, possibly creating or rearranging the icon
        structure around it.  Returns None on success and a string containing a message
        explaining the reason for the failure on failure."""
        if newText == '#' and self.text == '' and (self.parent() is not None or
                self.hasPendingArgs()):
            # The user has typed a pound character outside of  the legal context for a
            # line comment, so we assume they want to add a statement comment.  Note
            # that the removal or placeholder conversion of this entry icon happens via
            # focusOut as a side effect of placing the cursor in the comment.
            topParent = self.topLevelParent()
            if hasattr(topParent, 'stmtComment'):
                topParent.stmtComment.detachStmtComment()
            stmtComment = commenticon.CommentIcon(attachedToStmt=topParent,
                window=self.window)
            self.window.cursor.setToText(stmtComment)
            return None
        parseResult, handlerIc, prepend = self.parseEntryText(newText)
        # print('parse result', parseResult)
        if wasRejected(parseResult):
            self.removeIfEmpty()
            return parseResult[7:]
        self.window.requestRedraw(self.topLevelParent().hierRect(),
            filterRedundantParens=True)
        if parseResult == "accept":
            self.text = newText
            self.window.cursor.erase()
            self.setCursorPos(newCursorPos)
            self.window.cursor.draw()
            self.markLayoutDirty()
            return None
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
            return None
        elif parseResult == "comma":
            rejectReason = self.insertComma()
            if rejectReason is not None:
                self.removeIfEmpty()
                return rejectReason
            else:
                self.window.undo.addBoundary()
                return None
        elif parseResult == "colon":
            rejectReason = self.insertColon()
            if rejectReason is not None:
                self.removeIfEmpty()
                return rejectReason
            else:
                self.window.undo.addBoundary()
                return None
        elif parseResult == "openBracket":
            self.insertOpenParen(listicons.ListIcon)
            self.window.undo.addBoundary()
            return None
        elif parseResult == "endBracket":
            rejectReason = self.insertEndParen(parseResult)
            if rejectReason is not None:
                self.removeIfEmpty()
                return rejectReason
            else:
                self.window.undo.addBoundary()
                return None
        elif parseResult == "openBrace":
            self.insertOpenParen(listicons.DictIcon)
            self.window.undo.addBoundary()
            return None
        elif parseResult == "endBrace":
            rejectReason = self.insertEndParen(parseResult)
            if rejectReason is not None:
                self.removeIfEmpty()
                return rejectReason
            else:
                self.window.undo.addBoundary()
                return None
        elif parseResult == "openParen":
            self.insertOpenParen(parenicon.CursorParenIcon)
            self.window.undo.addBoundary()
            return None
        elif parseResult == "endParen":
            rejectReason = self.insertEndParen(parseResult)
            if rejectReason is not None:
                self.removeIfEmpty()
                return rejectReason
            else:
                self.window.undo.addBoundary()
                return None
        elif parseResult == "makeFunction":
            if self.attachedIcon().isCursorOnlySite(self.attachedSite()):
                self.removeIfEmpty()
                #... Why would parser let this through?
                return "Can't type anything here"
            else:
                self.insertOpenParen(listicons.CallIcon)
                self.window.undo.addBoundary()
                return None
        elif parseResult == "makeSubscript":
            self.insertOpenParen(subscripticon.SubscriptIcon)
            self.window.undo.addBoundary()
            return None
        elif parseResult == "addArgList":
            # This (very specific) action is currently only added by the class def icon
            # which needs to create its inheritance list when the user types '(', but
            # textEntryHandlers are not allowed to jump the entry icon to a new site
            for ic in self.attachedIcon().parentage():
                if isinstance(ic, blockicons.ClassDefIcon):
                    classDefIc = ic
                    break
            else:
                return "Internal error, couldn't find class def to add '('"
            classDefIc.addArgs()
            self.attachedIcon().replaceChild(None, self.attachedSite())
            classDefIc.replaceChild(self, 'argIcons_0')
            self.remove()
            self.window.undo.addBoundary()
            return None
        # Parser emitted an icon.  Splice it in to the hierarchy in place of the entry
        # icon (ignoring, for now, that the entry icon may have to be reinstated if there
        # are pending args/attrs or remaining to be placed).  Figure out where the cursor
        # or entry icon should end up after the operation.
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        snapLists = ic.snapLists(forCursor=True)
        if isinstance(ic, blockicons.LambdaIcon):
            self.insertLambda(ic)
            cursorIcon = ic
            cursorSite = 'argIcons_0'
        elif ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon):
            rejectReason = self.canInsertAssign(ic)
            if rejectReason is None:
                cursorIcon, cursorSite = self.insertAssign(ic)
            else:
                self.removeIfEmpty()
                return rejectReason
        elif self.attachedIcon() is None:
            # Entry icon is on the top level
            self.window.replaceTop(self, ic)
            ic.markLayoutDirty()
            if "input" in snapLists:
                cursorIcon, cursorSite = ic, snapLists["input"][0][2]  # First input site
            elif "attrIn" in snapLists:
                cursorIcon, cursorSite = ic, "attrIcon"
            elif isinstance(ic, (commenticon.CommentIcon, commenticon.VerticalBlankIcon)):
                cursorIcon, cursorSite = ic, 'seqOut'
            else:
                cursorIcon, cursorSite = icon.rightmostSite(ic)
        elif ic.__class__ is nameicons.YieldIcon:
            cursorIcon, cursorSite = self.insertYieldIcon(ic)
        elif self.canJoinIcons(ic):
            # 'is' followed by 'not', 'yield' folloed by 'from', unary minus followed by
            # number, sinqle-quoted string followed by quote; need to be joined in a
            # single 'is not', 'yield from', negative number, or triple-quoted string.
            self.joinIcons(ic)
            cursorIcon = self.attachedIcon()
            cursorSite = self.attachedSite()
        elif ic.__class__ in (listicons.CprhIfIcon, listicons.CprhForIcon):
            cursorIcon, cursorSite = self.insertCprhIcon(ic)
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            if ic.__class__ is nameicons.AttrIcon:
                # Attribute
                attachedSite = self.attachedSite()
                self.attachedIcon().replaceChild(ic, attachedSite)
                cursorIcon, cursorSite = ic, attachedSite
            elif ic.__class__ is opicons.IfExpIcon:
                cursorIcon, cursorSite = self.insertIfExpr(ic)
            else:
                # Operator
                argIcon = icon.findAttrOutputSite(self.attachedIcon())
                if argIcon is None:
                    # We can't append an operator if there's no operand to attach it to
                    self.removeIfEmpty()
                    return "Enter left operand before typing operator"
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
            if self._canPlacePendingArgs(cursorIcon, cursorSite, overwriteStart=
                    cursorIcon==self.attachedIcon() and cursorSite==self.attachedSite()):
                # Args can be placed, and there is no remaining text, so we place them
                # and remove the entry icon (if still attached), and be done
                subsIc = self._placePendingArgs(cursorIcon, cursorSite, overwriteStart=
                    cursorIcon==self.attachedIcon() and cursorSite==self.attachedSite())
                if subsIc is not None:
                    cursorIcon = subsIc
                    cursorSite = 'argIcons_0'
                if self.attachedIcon() is not None:
                    self.attachedIcon().replaceChild(None, self.attachedSite())
                if hasattr(ic, 'setCursorPos'):
                    self.window.cursor.setToText(ic)
                else:
                    self.window.cursor.setToIconSite(cursorIcon, cursorSite)
                self.window.undo.addBoundary()
                return None
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
            # The entry icon needs to be restored.  If it formerly owned the code block
            # below it, revert it to its non-block-owning form.
            self.removeCodeBlock()
            cursorIcon.replaceChild(self, cursorSite)
        self.text = remainingText
        self.setCursorPos(len(remainingText))
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
            # Make an exception for block-introducing colon, which we ignore at the end
            # of a block-owning statement, but not as a new statement of its own.
            topIcon = self.attachedIcon().topLevelParent()
            if remainingText == ':' and blockicons.isBlockOwnerIc(topIcon) or \
                    blockicons.isPseudoBlockIc(topIcon) and not self.hasPendingArgs():
                self.text = ''
                self.remove()
                return None
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
            return None
        # There is still text that might be processable.  Recursively go around again
        # (we only get here if something was processed, so this won't loop forever).
        # self.text still contains the content that was processed, above, and (while
        # unlikely) _setText can reject, and not overwrite it, so we must clear.
        self.text = ''  # In unlikely event _setText rejects, self.text needs to be right
        self.cursorPos = 0
        self._setText(remainingText, len(remainingText))
        return None

    def canPlaceEntryText(self, requireArgPlacement=False):
        # Parse the existing text and in the entry icon as if it had a delimiter (space)
        # added to the end (on ordinary typing, the parser must wait for a delimiter to
        # process text that might be the first character multi-character operator or
        # a keyword that is might be the start of an identifier).
        parseResult, handlerIc, consumeParent = self.parseEntryText(self.text + " ")
        # print('parse result', parseResult)
        # We assume that the entry text is something legal, waiting for a delimiter.
        # It should not be something self-delimiting.
        if wasRejected(parseResult) or parseResult in ("accept", "typeover", "comma",
                "colon", "openBracket", "endBracket", "openBreace", "endBrace",
                "openParen", "endParen", "makeFunction", "makeSubscript"):
            return False
        # Parser emitted an icon.  Evaluate if it would be usable.
        ic, remainingText = parseResult
        if remainingText != " ":
            print("Remaining text in canPlaceEntry text was not injected delimiter")
            return False
        if ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon):
            if self.canInsertAssign(ic) is not None:
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
            return "Comma must follow something"
        # Look for comma typeover opportunity
        typeoverIc = _findParenTypeover(self, "comma")
        if typeoverIc is not None:
            self.remove()  # Safe, since args would have invalidated typeover
            _siteBefore, siteAfter, _text, _idx = typeoverIc.typeoverSites()
            self.window.cursor.setToIconSite(typeoverIc, siteAfter)
            return None
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
                return "Can't enter comma in a non-series field"
        if isinstance(ic, listicons.ListTypeIcon) and ic.isComprehension():
            # The bounding icon is a comprehension and won't accept additional clauses
            return "Comprehension can have only one element"
        # ic can accept a new comma clause after splitSite.  Split expression in two at
        # entry icon
        left, right = splitExprAtIcon(self, ic, None, self)
        # Place the newly-split expression in to the series, creating a new clause
        ic.replaceChild(None, splitSite)
        splitSiteSeriesName, splitSiteIdx = iconsites.splitSeriesSiteId(splitSite)
        ic.insertChildren((left, right), splitSiteSeriesName, splitSiteIdx)
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return None

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
        # Change the requested class from CursorParenIcon to TupleIcon if the entry icon
        # holds a multi-element list in its first pending argument slot.  This is done,
        # here, because later placement of pending args will be done via the placeIcons
        # call, and the one for the cursor paren icon can't change itself to a tuple in
        # order to place the additional arguments
        if iconClass is parenicon.CursorParenIcon:
            pendingArgs = self.listPendingArgs()
            if len(pendingArgs) >= 1 and isinstance(pendingArgs[0], (list, tuple)):
                iconClass = listicons.TupleIcon
        # Determine if a parent has sequence clauses to the right of the entry icon that
        # will need entries transferred to the new paren icon.  It may also be necessary
        # to change the the generated icon from parens to tuple.
        attachedIc = self.attachedIcon()
        attachedSite = self.attachedSite()
        transferParentArgs = None
        transferParentCprhs = None
        newParenIcon = None
        if attachedIc is not None:
            seqIc, seqSite = findEnclosingSite(self)
            if isinstance(seqIc, subscripticon.SubscriptIcon) and \
                    isinstance(seqIc.childAt(seqSite), subscripticon.SliceIcon):
                # User is typing within a slice.  If they're typing another subscript,
                # allow the new bracket to split the slice, but if not, keep it contained
                # to within the slice.  This code needs more work, as it can violate our
                # rules for unclosed paren ownership by leaving a paren/bracket/brace
                # that lexically would take possession of subsequent elements (and
                # possibly part of the slice to which it's attached), and will therefore
                # leave users unable to match an unclosed brace in some cases.
                if iconClass is subscripticon.SubscriptIcon:
                    newParenIcon = subscripticon.SubscriptIcon(window=self.window,
                        closed=False)
                    left, right = splitExprAtIcon(self, seqIc, newParenIcon,  self)
                    seqIc.replaceChild(None, seqSite)
                    if right is not None:
                        newParenIcon.replaceChild(right, 'argIcons_0')
                    seqIc.insertChild(left, seqSite)
                    name, idx = iconsites.splitSeriesSiteId(seqSite)
                    numParentSites = len(getattr(seqIc.sites, name))
                    transferParentArgs = seqIc, iconsites.nextSeriesSiteId(seqSite), \
                        numParentSites
                else:
                    transferParentArgs = None
            elif seqIc and iconsites.isSeriesSiteId(seqSite) and \
                    seqIc.typeOf(seqSite) == 'input':
                siteName, siteIdx = iconsites.splitSeriesSiteId(seqSite)
                rightOfSite = iconsites.makeSeriesSiteId(siteName, siteIdx + 1)
                if seqIc.hasSite(rightOfSite):
                    name, idx = iconsites.splitSeriesSiteId(rightOfSite)
                    numParentSites = len(getattr(seqIc.sites, name))
                    if isinstance(seqIc, subscripticon.SubscriptIcon) and \
                            iconClass is not subscripticon.SubscriptIcon:
                        # Inside subscripts and slices, grammar rules go out the window.
                        # Parens are lower priority than slice colons, so we don't want
                        # to cross them
                        for i in range(idx, numParentSites):
                            arg = seqIc.childAt(name, i)
                            if isinstance(arg, subscripticon.SliceIcon):
                                numParentSites = i
                                break
                    transferParentArgs = seqIc, rightOfSite, numParentSites
                    # Convert cursor paren to tuple if there are arguments to transfer
                    if iconClass is parenicon.CursorParenIcon:
                        if numParentSites > idx:
                            iconClass = listicons.TupleIcon
                        else:
                            transferParentArgs = None
            if seqIc and isinstance(seqIc, (listicons.TupleIcon, listicons.ListIcon,
                    listicons.DictIcon)) and seqIc.isComprehension():
                transferParentCprhs = seqIc
                if iconClass is parenicon.CursorParenIcon:
                    iconClass = listicons.TupleIcon  # paren can't accept comprehensions
        # Create an icon of the requested class and move the entry icon inside of it
        if newParenIcon is None:
            if iconClass is parenicon.CursorParenIcon:
                closed = False  # We leave even empty paren open to detect () for empty tuple
                typeover = False
            elif transferParentCprhs:
                closed = True  # Show ownership of comprehensions
                typeover = False
            else:
                closed = transferParentArgs is None and _canCloseParen(self)
                typeover = closed
            newParenIcon = iconClass(window=self.window, closed=closed, typeover=typeover)
            if attachedIc is None:
                self.window.replaceTop(self, newParenIcon)
            else:
                attachedIc.replaceChild(newParenIcon, attachedSite)
            if iconClass is parenicon.CursorParenIcon:
                inputSite = 'argIcon'
            else:
                inputSite = 'argIcons_0'
            newParenIcon.replaceChild(self, inputSite)
        else:
            inputSite = 'argIcons_0'
        # Attempt to get rid of the entry icon and place pending args in its place
        if not self.remove():
            if self._canPlacePendingArgs(self.attachedIcon(), self.attachedSite(),
                    overwriteStart=True, useAllArgs=False):
                subsIc = self._placePendingArgs(self.attachedIcon(), self.attachedSite(),
                    overwriteStart=True)
                if subsIc is not None:
                    self.window.cursor.setToIconSite(subsIc, 'argIcons_0')
                else:
                    self.window.cursor.setToIconSite(newParenIcon, inputSite)
        # Reorder the expression with the new open paren in place (skip some work if the
        # entry icon was at the top level, since no reordering is necessary, there)
        if attachedIc is not None:
            reorderexpr.reorderArithExpr(newParenIcon)
        # Transfer sequence clauses after the new open paren/bracket/brace to it
        if transferParentArgs:
            rightOfIc, rightOfSite, numParentSites = transferParentArgs
            name, idx = iconsites.splitSeriesSiteId(rightOfSite)
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
            if isinstance(newParenIcon, subscripticon.SubscriptIcon):
                # If we've transferred the args into a subscript icon, check for slice
                # calls that can be converted to slice icons.
                for arg in newParenIcon.argIcons():
                    if subscripticon.SliceIcon.isSliceCallForm(arg):
                        subscripticon.SliceIcon.convertCallToSlice(arg)
        # Transfer comprehension clauses to the newly opened paren/bracket/brace
        if transferParentCprhs:
            cprhIcons = [site.att for site in transferParentCprhs.sites.cprhIcons if
                site.att is not None]
            for idx in range(len(transferParentCprhs.sites.cprhIcons)):
                transferParentCprhs.replaceChild(None, 'cprhIcons_0')
            for idx, cprhIc in enumerate(cprhIcons):
                newParenIcon.insertChild(cprhIc, 'cprhIcons', idx)

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
            return None
        matchingParen, transferArgsFrom = searchForOpenParen(token, self)
        if matchingParen is None:
            # No matching paren was found.  Remove cursor and look for typeover
            typeoverIc = _findParenTypeover(self, token)
            if typeoverIc is None:
                matchChar = {'endParen':'(', 'endBracket':'[', 'endBrace':'{'}[token]
                return "No matching %s" % matchChar
            self.remove()  # Safe, since args would have invalidated typeover
            cursorSite = 'returnType' if isinstance(typeoverIc, blockicons.DefIcon) \
                else 'attrIcon'
            self.window.cursor.setToIconSite(typeoverIc, cursorSite)
            return None
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
                    #... This needs to insert an entry icon, and not just reject.
                    return "Parent can not accept series elements"
                if isinstance(transferArgsFrom, listicons.TupleIcon) and idx == 0:
                    # Tuple is down to 1 argument.  Convert to arithmetic parens
                    newParen = cvtTupleToCursorParen(transferArgsFrom, closed=False,
                        typeover=False)
                    if transferArgsFrom is matchingParen:
                        matchingParen = newParen
        # Rearrange the hierarchy so the paren/bracket/brace is above all the icons it
        # should enclose and outside of those it does not enclose.  reorderArithExpr
        # closes the parens if it succeeds.  In the unlikely event that this is a
        # comprehension (which shouldn't happen because we strive to never leave an
        # un-closed comprehension), simply close it after the last clause and move the
        # cursor there.  This violates the principle that we should always insert where
        # the user types, but there is no point to writing complex code for breaking
        # apart a comprehension when we should instead be investing in code to make sure
        # they are never left unclosed in the first place.
        if isinstance(matchingParen, (listicons.TupleIcon, listicons.ListIcon,
                listicons.DictIcon)) and matchingParen.isComprehension():
            matchingParen.close(typeover=False)
            self.window.cursor.setToIconSite(matchingParen, 'attrIcon')
            return None
        else:
            reorderexpr.reorderArithExpr(matchingParen, closeParenAt=self)
        # If there are pending args, they need to go *after* the newly-closed paren.
        # reorderArithExpr will move the entry icon there, and the remove() call below
        # will place them. ...however at some point I added (incorrect) code (here) to
        # move the entry icon after the fact.  I've now removed the code and it seems to
        # be working correctly, but this is a good place to check if something's wrong.
        self.remove()
        self.window.updateTypeoverStates()
        return None

    def canInsertAssign(self, assignIcon):
        """Does pre-checking and rejectReason generation for insertAssign.  Note that
        this returns None if assignIcon CAN be inserted, and the reason (as a string)
        that it can't.  If this does not return None, insertAssign should not be
        called."""
        topIcon, splitSite = findEnclosingSite(self)
        if not (topIcon is None or isinstance(topIcon, assignicons.AssignIcon) or
                isinstance(topIcon, listicons.TupleIcon) and topIcon.noParens):
            return "= can only be added at the top level or within calls and definitions"
        isAugmentedAssign = assignIcon.__class__ is assignicons.AugmentedAssignIcon
        if isAugmentedAssign:
            if isinstance(topIcon, assignicons.AssignIcon):
                return "Augmented assignment (i.e. +=) can not be " \
                    "combined with normal assignment (=)"
            if isinstance(topIcon, listicons.TupleIcon) and splitSite != 'argIcons_0':
                return "Augmented assignment (i.e. +=) can have only one target"
        return None

    def insertAssign(self, assignIcon):
        """Insert an assignment or augmented assignment operator.  Before calling this,
        call canInsertAssign to decide if this can be called.  THIS IS NOT SAFE to call
        if canInsertAssign has not returned None."""
        # Older versions of this code were much more restrictive with respect to where
        # users could insert an assignment.  This was surprisingly annoying in the way
        # it interfered with typing flow.  For example, not allowing users to type '='
        # after an invalid target, meant we were both throwing out their keystroke and
        # forcing them to go back and correct code we had *already accepted* before they
        # could continue typing.  The new code accepts anything that will produce a
        # correct structure, but since we're also able to highlight errors, these are
        # clearly marked so the user can go back and correct them.
        #
        # Check for all illegal cases before taking any irreversible actions.  We only
        # require that the entry icon is on either a top-level expression or one that is
        # a child of either a naked tuple or an existing assignment. For an augmented
        # assign, also ensure that the insertion will produce only a single target.
        topIcon, splitSite = findEnclosingSite(self)
        isAugmentedAssign = assignIcon.__class__ is assignicons.AugmentedAssignIcon
        # Replace the current top-level icon with the new assignment icon (unless it's
        # already an assignment icon)
        if not isinstance(topIcon, assignicons.AssignIcon):
            self.window.replaceTop(self.topLevelParent(), assignIcon)
        # Split the expression around the entry icon
        left, right = splitExprAtIcon(self, topIcon, None, self)
        # Move the icons into the new assignment statement
        if topIcon is None:
            # The entry icon is on a top-level expression
            expr = self.topLevelParent()
            tgtSite = 'targetIcon' if isAugmentedAssign else 'targets0_0'
            assignIcon.replaceChild(left, tgtSite)
            assignIcon.replaceChild(right, 'values_0')
        elif isinstance(topIcon, listicons.TupleIcon):
            # The entry icon is on a naked tuple
            _, splitIdx = iconsites.splitSeriesSiteId(splitSite)
            argIcons = topIcon.argIcons()
            tgtIcons = argIcons[:splitIdx] + [left]
            valueIcons = [right] + argIcons[splitIdx+1:]
            for _ in range(len(topIcon.sites.argIcons)):
                topIcon.replaceChild(None, 'argIcons_0')
            if isAugmentedAssign:
                assignIcon.replaceChild(tgtIcons[0], 'targetIcon')
            else:
                assignIcon.insertChildren(tgtIcons, 'targets0', 0)
            assignIcon.insertChildren(valueIcons, 'values', 0)
        elif isinstance(topIcon, assignicons.AssignIcon):
            # The entry icon is on an existing assignment icon.  Add a new target clause
            # either before the split (if it is in the values series) or after the split
            # (if it is in a target series)  assignIcon is thrown away.
            splitSeriesName, splitIdx = iconsites.splitSeriesSiteId(splitSite)
            if splitSeriesName == 'values':
                # = was typed in the value series, add a new target group at the end
                # and move the icons from before the insertion in to it.
                newTgtGrpIdx = len(topIcon.tgtLists)
                iconsToMove = [site.att for site in topIcon.sites.values][:splitIdx]
                iconsToMove.append(left)
                topIcon.replaceChild(right, splitSite)
                for _ in range(splitIdx):
                    topIcon.replaceChild(None, 'values_0')
            else:
                # = was typed in a target series, insert a new target group after the
                # split group and move the icons from after the insertion in to it.
                topIcon.replaceChild(left, splitSite, leavePlace=True)
                newTgtGrpIdx = int(splitSeriesName[7:]) + 1
                series = getattr(topIcon.sites, splitSeriesName)
                iconsToMove = [right] + [site.att for site in series][splitIdx+1:]
                removeFromSite = iconsites.makeSeriesSiteId(splitSeriesName, splitIdx+1)
                for _ in range(splitIdx+1, len(series)):
                    topIcon.replaceChild(None, removeFromSite)
            topIcon.addTargetGroup(newTgtGrpIdx)
            topIcon.insertChildren(iconsToMove, 'targets%d' % newTgtGrpIdx, 0)
        # Remove the entry icon if possible
        if not self.remove():
            return self.attachedIcon(), self.attachedSite()
        return self.window.cursor.icon, self.window.cursor.site

    def insertColon(self):
        if self.attachedIcon() is None:
            # Not allowed to type colon at the top level: Reject
            return "Colon must be in context of a dictionary or subscript, or follow " \
                "an identifier in a context where type annotation can be applied"
        # Find the top of the expression to which the entry icon is attached
        ic, splitSite = findEnclosingSite(self)
        if isinstance(ic, listicons.DictIcon):
            return self.insertDictColon(ic)
        if isinstance(ic, subscripticon.SubscriptIcon):
            return self.insertSubscriptColon(ic)
        if isinstance(ic, (blockicons.ForIcon, blockicons.WithIcon, blockicons.WhileIcon,
                blockicons.IfIcon, blockicons.ElifIcon, blockicons.DefOrClassIcon,
                blockicons.ExceptIcon)):
            rightmostIc, rightmostSite = icon.rightmostSite(ic)
            if rightmostIc is self:
                self.remove()
                return None
        if ic is None and isinstance(self.attachedIcon(), (blockicons.ElseIcon,
                blockicons.TryIcon, blockicons.DefOrClassIcon, blockicons.FinallyIcon)) \
                and self.attachedSite() == 'attrIcon':
            self.remove()
            return None
        if ic is None or isinstance(ic, listicons.TupleIcon) and ic.noParens \
                or isinstance(ic, assignicons.AssignIcon) and splitSite[:8] == 'targets0'\
                or isinstance(ic, blockicons.DefIcon) and splitSite[:8] == 'argIcons':
            return self.insertTypeAnn(ic, splitSite)
        return "Colon must be in context of a dictionary or subscript, or follow " \
            "an identifier in a context where type annotation can be applied"

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
        self.replaceWith(None)
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

    def insertLambda(self, lambdaIc):
        """When the user types "lambda" before an existing icon, they usually don't want
        the icon to end up in the parameter list for the lambda, which would be the
        default behavior without the special assistance provided here."""
        # Design note: This could be done in the lambda icon's placeIcons call and kept
        # out of general parsing.  The function def icon does almost exactly this, and
        # for similar reasons.  What makes this different is that the function-def icon
        # does it for a very narrow set of cases and in an icon that's much more
        # constrained.  For lambda, the placeArgs call would then be redirecting most
        # icon placement to a site other than the one requested by its caller, which I
        # think would get confusing.
        if self.hasPendingArgs():
            pendingArgs = self.listPendingArgs()
            compressedArgs = [ic for ic, _, _ in icon.placementListIter(pendingArgs)
                if ic is not None]
            if isinstance(pendingArgs[0], listicons.CallIcon):
                # This is almost certainly from either a lambda icon being edited, or a
                # def icon being converted to a lambda, as the call icon attaches to an
                # attribute and the lambda attaches to an input.  Here, we actually want
                # to move the content to the parameter list.  No code necessary, here,
                # because this will be done by the lambda icon's placeArgs method.
                pass
            elif len(compressedArgs) == 1 and compressedArgs[0].hasSite('output'):
                # There is one single pending arg: skip the parameter list and put it on
                # the expression site.
                ic, idx, seriesIdx = icon.firstPlaceListIcon(pendingArgs)
                self.popPendingArgs(idx, seriesIdx)
                lambdaIc.replaceChild(compressedArgs[0], 'exprIcon')
        if self.attachedIcon():
            self.attachedIcon().replaceChild(lambdaIc, self.attachedSite())
        else:
            self.window.replaceTop(self, lambdaIc)

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
                return "Entry already contains a colon"
            # Split across entry icon, insert both a colon and a comma w/typeover
            left, right = splitExprAtIcon(self, child, None, self)
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
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(left, 'leftArg')
            newDictElem.replaceChild(right, 'rightArg')
            self.remove()
        return None

    def insertTypeAnn(self, enclosingIc, enclosingSite):
        # We only get here if we know this is a reasonable parent (or lack thereof) for
        # type annotation
        if enclosingIc is None:
            # We're attached to an expression that starts at the top level.
            topParent = self.topLevelParent()
            if isinstance(topParent, infixicon.TypeAnnIcon):
                # There's already a colon in this clause.  We allow a colon to be typed
                # in the left arg of an existing clause, which is handled by adding a new
                # clause.  Since we're on the top level, that involves creating a naked
                # tuple, which we do here and let the more-general code later on do the
                # actual work.  If the colon is within the type annotation, is an error.
                typeAnnSite = topParent.siteOf(self, recursive=True)
                if typeAnnSite != 'leftArg':
                    return "Type annotation already contains a colon"
                newTuple = listicons.TupleIcon(window=self.window, noParens=True)
                self.window.replaceTop(topParent, newTuple)
                newTuple.replaceChild(topParent, 'argIcons_0')
                enclosingIc = newTuple
                enclosingSite = 'argIcons_0'
            else:
                if topParent is self:
                    # There's nothing at the site except the entry icon (and whatever we
                    # are holding).  Place a new TypeAnnIcon, move entry icon to right
                    # arg, try to place pending args and remove
                    newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
                    self.window.replaceTop(self, newTypeAnn)
                    newTypeAnn.replaceChild(self, 'rightArg')
                    if self.remove():
                        self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
                    return None
                # Vet the icon that the entry icon is attached to as a reasonable target
                # for type annotation
                attachedIc = self.attachedIcon()
                attrRoot = icon.findAttrOutputSite(attachedIc)
                highestCoincIcon = iconsites.highestCoincidentIcon(attrRoot)
                if highestCoincIcon is not topParent or not \
                        infixicon.isValidAnnotationTarget(attachedIc, stopAtIc=self):
                    return "Not a valid target for type annotation"
                # Insert the type annotation icon at the site as an operator
                newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
                left, right = splitExprAtIcon(self, enclosingIc, None, self)
                self.window.replaceTop(topParent, newTypeAnn)
                newTypeAnn.replaceChild(left, 'leftArg')
                newTypeAnn.replaceChild(right, 'rightArg')
                if self.remove():
                    self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
                # Outside of function def, should not encounter icons of lower precedence
                # (= or *), but through great contortion it is possible.
                reorderexpr.reorderArithExpr(newTypeAnn)
                return None
        child = enclosingIc.childAt(enclosingSite)
        pendingArg, pendIdx, seriesIdx = icon.firstPlaceListIcon(self.listPendingArgs())
        if isinstance(child, infixicon.TypeAnnIcon) or \
                isinstance(child, listicons.ArgAssignIcon) and \
                isinstance(child.childAt('leftArg'), infixicon.TypeAnnIcon):
            # There's already a colon in this clause.  Within a function def, w allow a
            # colon to be typed on the left of an existing clause, since that is how one
            # naturally types a new clause (when they begin after the comma or to
            # the left of the first clause).  Typing a colon on the right side of
            # a typeAnnIcon is not expected without a comma, and not allowed.
            if isinstance(child, listicons.ArgAssignIcon):
                if child.siteOf(self, recursive=True) != 'leftArg':
                    return "Can't add type annotation to argument default value"
                typeAnnIc = child.childAt('leftArg')
            else:
                typeAnnIc = child
            typeAnnSite = typeAnnIc.siteOf(self, recursive=True)
            if isinstance(enclosingIc, blockicons.DefIcon) and typeAnnSite != 'leftArg':
                return "Type annotation already contains a colon"
            # Split across entry icon, insert both a colon and a comma w/typeover
            left, right = splitExprAtIcon(self, child, None, self)
            newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
            newTypeAnn.replaceChild(left, 'leftArg')
            enclosingIc.replaceChild(newTypeAnn, enclosingSite, leavePlace=True)
            nextSite = iconsites.nextSeriesSiteId(enclosingSite)
            enclosingIc.insertChild(child, nextSite)
            child.replaceChild(right, 'leftArg')
            # Remove entry icon, placing pending args on the right side of the new
            # comma but cursor before the comma... Checking for pending args needs to
            # happen earlier while we can still bail
            if self.remove():
                self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
            enclosingIc.setTypeover(0, nextSite)
            self.window.watchTypeover(enclosingIc)
        elif isinstance(child, listicons.ArgAssignIcon):
            if child.siteOf(self, recursive=True) != 'leftArg':
                return "Can't add type annotation to argument default value"
            newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
            left, right = splitExprAtIcon(self, enclosingIc, None, self)
            enclosingIc.replaceChild(newTypeAnn, enclosingSite)
            newTypeAnn.replaceChild(left, 'leftArg')
            newTypeAnn.replaceChild(right, 'rightArg')
            if self.remove():
                self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
            reorderexpr.reorderArithExpr(newTypeAnn)
        elif child is self:
            # There's nothing at the site except entry icon and whatever we are holding.
            # Place a new TypeAnnIcon, move entry icon to right arg, try to place
            # pending args and remove
            newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
            enclosingIc.replaceChild(newTypeAnn, enclosingSite)
            newTypeAnn.replaceChild(self, 'rightArg')
            if self.remove():
                self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
        else:
            # There's something at the site.  Put a colon in it
            if isinstance(child, (listicons.StarIcon, listicons.StarStarIcon)):
                if isinstance(child.childAt('argIcon'), infixicon.TypeAnnIcon):
                    # There's already a type annotation, here
                    return "Can't add type annotation to type annotation"
            newTypeAnn = infixicon.TypeAnnIcon(window=self.window)
            left, right = splitExprAtIcon(self, enclosingIc, None, self)
            enclosingIc.replaceChild(newTypeAnn, enclosingSite)
            newTypeAnn.replaceChild(left, 'leftArg')
            newTypeAnn.replaceChild(right, 'rightArg')
            reorderexpr.reorderArithExpr(newTypeAnn)
            if self.remove():
                self.window.cursor.setToIconSite(newTypeAnn, 'rightArg')
        return None

    def insertSubscriptColon(self, onIcon):
        # onIcon will be a subscript icon.  Figure out if we're adding to an existing
        # slice or an expression
        onSite = onIcon.siteOf(self, recursive=True)
        childIc = onIcon.childAt(onSite)
        if childIc is self:
            # The entry icon is directly on the subscript icon site, meaning there is no
            # expression and no subscript icon.  Just add an empty subscript, and move
            # the entry icon after the colon
            sliceIcon = subscripticon.SliceIcon(window=self.window)
            self.replaceWith(sliceIcon)
            sliceIcon.replaceChild(self, 'upperIcon')
        elif isinstance(childIc, subscripticon.SliceIcon):
            # The entry icon is within an existing slice
            sliceIcon = childIc
            if sliceIcon.hasSite('stepIcon'):
                return "Slice already has all 3 clauses (start:stop:step)"
            sliceSite = sliceIcon.siteOf(self, recursive=True)
            # Split the expression holding the entry icon in two at the entry icon
            left, right = splitExprAtIcon(self, sliceIcon, None, self)
            # Create a new clause and put the two halves in to them
            sliceIcon.addStepSite()
            # If the cursor was on the first site, may need to shift second-site icons
            if sliceSite == 'indexIcon':
                toShift = sliceIcon.childAt('upperIcon')
                sliceIcon.replaceChild(None, "upperIcon")
                sliceIcon.replaceChild(toShift, 'stepIcon')
                nextSite = 'upperIcon'
            else:
                nextSite = 'stepIcon'
            # Place the newly-split expression in to its assigned slots
            sliceIcon.replaceChild(left, sliceSite)
            sliceIcon.replaceChild(right, nextSite)
        else:
            # The entry icon is within an expression.  Split it and divide it across
            # a new slice icon
            left, right = splitExprAtIcon(self, onIcon, None, self)
            sliceIcon = subscripticon.SliceIcon(window=self.window)
            onIcon.replaceChild(sliceIcon, onSite)
            sliceIcon.replaceChild(left, 'indexIcon')
            sliceIcon.replaceChild(right, 'upperIcon')
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return None

    def insertCprhIcon(self, ic):
        """Handle insertion of a comprehension.  Comprehension sites are cursor-
        prohibited, and the entry icon will be sitting somewhere under a list, dict, or
        tuple icon, from which we will determine the actual insertion (cprh) site."""
        child = self
        for parent in self.parentage(includeSelf=False):
            if isinstance(parent, (listicons.ListIcon, listicons.DictIcon,
                    listicons.TupleIcon, parenicon.CursorParenIcon)) and \
                    parent.siteOf(child) != 'attrIcon':
                insertIn = parent
                break
            child = parent
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
        if not insertIn.closed:
            # We can safely close the icon, now that we know where it ends
            insertIn.close(typeover=True)
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
            if not isinstance(insertedIc.value, (numbers.Real, numbers.Rational,
                    numbers.Integral)) or insertedIc.value < 0 or \
                    isinstance(insertedIc.value, bool):
                # True, False, ellipsis are also considered numbers and represented by
                # NumericIcon, but can't be negated.
                return False
            # Join unary minus and a numeric icon into a negative numeric icon
            if not doJoin:
                return True
            newNumIc = nameicons.NumericIcon("-" + insertedIc.text,
                window=attachedIc.window)
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

    def click(self, x, y):
        if not self.pointInTextArea(x, y):
            return False
        self.window.cursor.erase()
        self.cursorPos = comn.findTextOffset(icon.globalFont, self.text,
            x - self.rect[0] - self.textOffset)
        self.window.cursor.setToText(self, drawNew=False)
        return True

    def pointInTextArea(self, x, y):
        left, top, right, bottom = self.rect
        # The click boundary for the text area extends to the very edge of the pen icon
        # on the left and the icon border on the right, to give the user a sufficiently
        # wide target for pointing to the left and right edges (text cursor positions).
        left += penImage.width - 3
        top += 2
        bottom -= 2
        right -= 2
        return left < x < right and top < y < bottom

    def nearestCursorPos(self, x, y):
        """Returns cursor index and x, y position (tuple) of the cursor position nearest
        text cursor position to the given x,y coordinate."""
        textLeft = self.rect[0] + self.textOffset
        textRight = self.rect[2] - icon.TEXT_MARGIN
        textCenter = self.height // 2
        if x <= textLeft:
            return 0, (textLeft, textCenter)
        if x >= textRight:
            return len(self.text), (textRight, textCenter)
        cursorPos = comn.findTextOffset(icon.globalFont, self.text,
            x - self.rect[0] - self.textOffset)
        return cursorPos, self.cursorWindowPos()

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
            self.sites.forCursor.yOffset = self.height//2 + icon.ATTR_SITE_OFFSET
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
        layouts = []
        if len(argLayoutGroups) == 0:
            # No pending arguments, but under special circumstances, forCursor site
            # is allowed to hold another entry icon (such as when the entry icon is in
            # the left side of a binary operator and the user edits the operator).
            forCursorArg = self.childAt('forCursor')
            if forCursorArg is None:
                layouts = [iconlayout.Layout(self, baseWidth, self.height, siteOffset)]
            else:
                for forCursorLayout in forCursorArg.calcLayouts():
                    layout = iconlayout.Layout(self, baseWidth, self.height, siteOffset)
                    layout.addSubLayout(forCursorLayout, 'forCursor',
                        baseWidth - icon.ATTR_SITE_DEPTH, 0)
                    layout.width += forCursorLayout.width
                    layouts.append(layout)
            return self.debugLayoutFilter(layouts)
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

    def select(self, select=True):
        icon.Icon.select(self, select)
        if hasattr(self, 'blockEnd'):
            icon.Icon.select(self.blockEnd, select)

    def backspace(self, siteId, evt):
        if siteId == self.sites.firstCursorSite():
            # Backspace from icon cursor location right-of the entry icon into text area
            self.window.cursor.setToText(self)
        elif iconsites.isSeriesSiteId(siteId) and \
                iconsites.splitSeriesSiteId(siteId)[1] != 0:
            # Cursor is on a comma
            listicons.backspaceComma(self, siteId, evt)
        else:
            # Backspace from a pending arg site.  These sites are coincident and should
            # probably be marked as cursor-prohibited once that is supported.  For now,
            # forward to the rightmost site of the prior arg.
            prevSite = self.sites.prevCursorSite(siteId)
            rightmostIc, rightmostSite = icon.rightmostFromSite(self, prevSite)
            rightmostIc.backspace(rightmostSite, evt)

    def clipboardRepr(self, offset):
        return None

    def duplicate(self, linkToOriginal=False):
        ic = EntryIcon(initialString=self.text, window=self.window)
        if linkToOriginal:
            ic.copiedFrom = self
        dupArgs = []
        for pendingArg in self.listPendingArgs():
            if isinstance(pendingArg, list):
                seriesList = []
                for seriesArg in pendingArg:
                    if seriesArg is None:
                        seriesList.append(None)
                    else:
                        seriesList.append(seriesArg.duplicate(
                            linkToOriginal=linkToOriginal))
                dupArgs.append(seriesList)
            elif pendingArg is None:
                dupArgs.append(None)
            else:
                dupArgs.append(pendingArg.duplicate(linkToOriginal=linkToOriginal))
        ic.appendPendingArgs(dupArgs)
        return ic

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('$Entry')
        macroArgs = '' if self.text == '' else repr(self.text)
        if self.attachedToAttribute():
            macroArgs += 'A'
        argsWritten = False
        for argIdx, arg in enumerate(self.listPendingArgs()):
            if isinstance(arg, (list, tuple)):
                argText = filefmt.SegmentedText(None)
                argType = 'l'
                for i, argIcon in enumerate(arg):
                    if argIcon is None:
                        argText.add(brkLvl, '$Empty$', needsContinue=False)
                    else:
                        argText.concat(brkLvl, argIcon.createSaveText(brkLvl + 1,
                            contNeeded=False, export=export))
                    if i != len(arg) - 1:
                        argText.add(None, ', ', needsContinue=False)
            elif arg is None:
                argText = filefmt.SegmentedText('$Empty$')
                argType = ''
            else:
                argText = arg.createSaveText(brkLvl, False, export)
                if argText.isCtxMacro():
                    argType = argText.unwrapCtxMacro()
                elif isinstance(arg, (nameicons.AttrIcon, subscripticon.SubscriptIcon,
                        listicons.CallIcon)):
                    argType = 'a'
                elif isinstance(arg, infixicon.AsIcon):
                    argType = 's'
                elif isinstance(arg, listicons.DictElemIcon):
                    argType = 'd'
                elif isinstance(arg, (listicons.CprhForIcon, listicons.CprhIfIcon)):
                    argType = 'c'
                elif isinstance(arg, (listicons.ArgAssignIcon, listicons.StarStarIcon)):
                    argType = 'f'
                elif isinstance(arg, nameicons.RelativeImportIcon):
                    argType = 'i'
                else:
                    argType = ''
            if argIdx == 0:
                text.add(None, ':' + macroArgs + argType + '($')
            else:
                text.add(brkLvl, '$)' + argType + '($', needsContinue=False)
            text.concat(brkLvl, argText, needsContinue=False)
            argsWritten = True
        if argsWritten:
            # Close last macro code argument (macroArgs already written)
            text.add(brkLvl, '$)$', needsContinue=False)
        else:
            # If no code arguments were written (pending arg list was empty) , we also
            # haven't written the macroArgs.  Write them and the closing '$' of the
            # macro.  There's no point in optimizing out the : for the no arg case, since
            # that's only a backstop for failing to remove an empty entry icon.
            text.add(None, ':' + macroArgs + '$')
        return text

    def createAst(self, attrOfAst=None):
        raise icon.IconExecException(self, "Remove text-entry field")

    def execute(self):
        raise icon.IconExecException(self, "Can't execute text-entry field")

    def attachedToAttribute(self):
        return self.attachedSite() is not None and \
         self.attachedSiteType() in ("attrOut", "attrIn")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN

    def highlightErrors(self, errHighlight):
        self.errHighlight = errHighlight
        if errHighlight is None and not self.hasFocus:
            if self.hasPendingArgs() and self.text != "":
                err = "holding incomplete (unparsed) text and unprocessed argument code"
            elif self.hasPendingArgs():
                err = "holding code that is incompatible with the code to which it is " \
                      "attached"
            elif self.text != "":
                err = "holding incomplete (unparsed) text"
            else:
                err = "pending text entry: type backspace to remove"
            self.errHighlight = icon.ErrorHighlight("This is an entry icon " + err)
        if errHighlight is None:
            errHighlight = icon.ErrorHighlight(
                "Icon is disconnected from surrounding code")
        for ic in self.children():
            ic.highlightErrors(errHighlight)
        if hasattr(self, 'blockEnd'):
            blockicons.checkPseudoBlockHighlights(self)

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
        if self.window.cursor.type == 'text' and self.window.cursor.icon is self:
            self.window.requestScroll('cursor')

    def textCursorImage(self):
        return textCursorImage

    def dumpName(self):
        if len(self.text) < 15:
            entryText = self.text
        else:
            entryText = self.text[:15] + '...'
        return 'EntryIcon "' + entryText + '"'

    def siteRightOfPart(self, partId):
        return self.sites.firstCursorSite()

    def _canPlacePendingArgs(self, onIcon, onSite, overwriteStart=False,
            useAllArgs=False):
        """Returns True if _placePendingArgs will be able to place the entry icon's
        pending args on a given icon (onIcon), starting at a given site (onsite).  If
        useAllArgs is set to True, additionally requires that all (non-empty) pending
        args be used."""
        if not self.hasPendingArgs():
            return True
        pendingArgList = self.listPendingArgs()
        pendIdx, pendSeriesIdx = listicons.canPlaceArgsInclCprh(pendingArgList, onIcon,
            onSite, overwriteStart=overwriteStart)
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
        of arg/attr placement).  If some but not all of the pending args were placed,
        creates a new entry icon to hang the remaining args off of and attaches that to
        the rightmost site from the rightmost argument placed.  Also handles the special
        case of placing comprehension clause(s) on a cursor-paren icon, which requires
        swapping out onIcon for a tuple-icon.  If it makes this swap, it will return the
        tuple icon which it substituted.  Otherwise, returns None."""
        if not self.hasPendingArgs():
            return None
        pendingArgList = self.listPendingArgs()
        pendIdx, pendSeriesIdx = listicons.canPlaceArgsInclCprh(pendingArgList, onIcon,
            onSite, overwriteStart=overwriteStart)
        if pendIdx is None:
            return None
        if icon.placeListAtEnd(pendingArgList, pendIdx, pendSeriesIdx):
            # All args can be placed.  Place them and we're done
            self.popPendingArgs(pendIdx, pendSeriesIdx)
            subsIc = listicons.placeArgsInclCprh(pendingArgList, onIcon, onSite,
                overwriteStart=overwriteStart)
            return subsIc
        if icon.placeListEmpty(pendingArgList, pendIdx, pendSeriesIdx):
            # The only args we were able to place were empty: don't add/move entry icon
            return None
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
        subsIc = listicons.placeArgsInclCprh(pendingArgList, onIcon, onSite,
            overwriteStart=overwriteStart)
        return subsIc

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
    if attrPattern.fullmatch(op) and op[1:] not in keywords:
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
    return "reject:Expecting an operator, attribute, or delimiter"

def parseExprText(text, window, forSeriesSite=False):
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
    if text == '...':
        return nameicons.EllipsisIcon(window), None
    if text in ('.', '..'):
        return 'accept'
    if text == '*' and forSeriesSite:
        return listicons.StarIcon(window), None
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
        if text == '*' and forSeriesSite:
            return listicons.StarIcon(window), delim
    if text == 'lambda':
        if delim not in ' *:':
            return "reject:lambda should be followed by parameter list or colon"
        return blockicons.LambdaIcon(window, typeover=True), delim
    if text == 'yield':
        return nameicons.YieldIcon(window), delim
    if text == 'yield from':
        return nameicons.YieldFromIcon(window), delim
    if text == 'await':
        return nameicons.AwaitIcon(window), delim
    if not (identPattern.fullmatch(text) or numPattern.fullmatch(text)):
        return "reject:Not a valid identifier or value"
    if len(text) == 0:
        return "reject:No legal expression starts with this character"
    if delim not in delimitChars:
        return "reject:Not a valid delimiter"
    # All but the last character is ok and the last character is a valid delimiter
    if text in ('False', 'None', 'True'):
        #... Not sure these should be identifiers, but leaving as is, because they're not
        #    numeric icons, either, as they can have attributes: None.__class__ is legal!
        #    Probably need a new class for them.
        return nameicons.IdentifierIcon(text, window), delim
    if text in keywords:
        return "reject:%s is a keyword that should not be used in this context" % text
    exprAst = parseExprToAst(text)
    if exprAst is None:
        return "reject:%s is not a valid expression" % text
    if exprAst.__class__ == ast.Name:
        return nameicons.IdentifierIcon(exprAst.id, window), delim
    if exprAst.__class__ == ast.Num:
        return nameicons.NumericIcon(exprAst.n, window), delim
    if exprAst.__class__ == ast.UnaryOp and exprAst.op.__class__ == ast.USub and \
            exprAst.operand == ast.Num:
        return nameicons.NumericIcon(text, window), delim
    if exprAst.__class__ == ast.Constant and isinstance(exprAst.value, numbers.Number):
        return nameicons.NumericIcon(text, window), delim
    if exprAst.__class__ == ast.UnaryOp and exprAst.op.__class__ == ast.USub and \
            exprAst.operand.__class__ == ast.Constant and \
            isinstance(exprAst.operand.value, numbers.Number):
        return nameicons.NumericIcon(text, window), delim
    return "reject:Not a valid expression"

def parseTopLevelText(text, window):
    if len(text) == 0:
        return "accept"
    for stmt, icClass in cursors.topLevelStmts.items():
        if len(text) <= len(stmt) and text == stmt[:len(text)]:
            return "accept"
        delim = text[-1]
        if text[:-1] == stmt and delim in delimitChars:
            if stmt in noArgStmts and delim not in emptyDelimiters and delim != ':':
                # Accepting unusable delimiters would cause trouble later
                return "reject:%s does not take an argument" % text[:-1]
            kwds = {}
            if stmt[:5] == "async":
                kwds['isAsync'] = True
            if hasattr(icClass, 'hasTypeover') and icClass.hasTypeover:
                kwds['typeover'] = True
            return icClass(window=window, **kwds), delim
    if text == '*':
        # A star icon by itself must be allowed, as it is the beginning of *a, b = ...
        return listicons.StarIcon(window), None
    if text == '@':
        return nameicons.DecoratorIcon(window), None
    if text[0] == '#':
        return commenticon.CommentIcon(text[1:], window=window), None
    if len(text) == 2:
        op = text[0]
        delim = text[1]
        if op == '*':
            if delim.isalpha() or delim.isspace() or delim in '([{':
                return listicons.StarIcon(window), delim
            return "reject:* must be followed by identifier or iterable"
        if op == '@':
            if delim.isalpha():
                return nameicons.DecoratorIcon(window), delim
            return "reject:@ must be followed by decorator function name"
    if text == ':':
        if len(text) == 1:
            return "reject:Must specify target for type annotation"
    return parseExprText(text, window)

def parseWindowBgText(text, window):
    """Do supplementary parsing for text typed outside of a sequence (on the window
    background.  We don't allow users to type the full range of out-of-context icons,
    there, mostly because without the context, we will parse them as something else.
    However, we do allow them to type attributes, mainly because if they drag an
    attribute to the window background and click to text-edit it, we don't want them to
    lose their work because we are unable to re-parse it.  As a bonus they also get the
    ability to compose attributes from scratch without another icon as root.  Of course,
    they won't be so lucky with the other out-of-context items.  If they backspace into
    an argument assignment or a dictionary element, they will get something different
    back on re-typing."""
    if len(text) == 0:
        return "accept"
    if text == '.' or attrPattern.fullmatch(text):
        return "accept"  # Legal attribute pattern
    op = text[:-1]
    delim = text[-1]
    if attrPattern.fullmatch(op) and op[1:] not in keywords:
        return nameicons.AttrIcon(op[1:], window), delim
    return "reject:Expecting an operator, attribute, or delimiter"

def wasRejected(parseResult):
    return isinstance(parseResult, str) and parseResult[:7] == 'reject:'

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
    if isinstance(ic, opicons.IfExpIcon):
        return 'trueExpr'
    if isinstance(ic, subscripticon.SliceIcon):
        return 'indexIcon'
    return 'leftArg'

def binOpRightArgSite(ic):
    if isinstance(ic, opicons.IfExpIcon):
        return 'falseExpr'
    if isinstance(ic, subscripticon.SliceIcon):
        return 'stepIcon' if ic.hasSite('stepIcon') else 'upperIcon'
    return 'rightArg'

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
    matchSubscriptOnly = False
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
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endParen" and isinstance(ic, listicons.CallIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endBracket" and isinstance(ic, listicons.ListIcon) and \
                    not ic.closed and not matchSubscriptOnly:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endBracket" and isinstance(ic, subscripticon.SubscriptIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if token == "endBrace" and isinstance(ic, listicons.DictIcon) and \
                    not ic.closed:
                return ic, transferArgsFrom if transferArgsFrom else ic
            if ic.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and ic.hasParens:
                # Don't allow search to escape enclosing arithmetic parens
                break
            rightmostSite = ic.sites.lastCursorSite()
            if ic.typeOf(rightmostSite) not in ('input', 'cprhIn') or \
                    hasattr(ic, 'closed') and ic.closed or \
                    isinstance(ic, opicons.IfExpIcon) and site == 'testExpr' or \
                    isinstance(ic, subscripticon.SliceIcon) and site != 'indexIcon':
                # Anything that doesn't have an input on the right or is closed can be
                # assumed to enclose its children and search should not extend beyond.
                # Inline if and slice are the exceptions in having a middle site that
                # encloses its child icon (technically, there are cases where we could
                # split a slice icon to match a subscript paren, but currently the code
                # in reorderexpr that does the splitting can't handle that.
                if isinstance(ic, subscripticon.SliceIcon) and token == "endBracket" \
                        and site == 'stepIcon' or (not ic.hasSite('stepIcon') and
                        site == 'upperIcon'):
                    # Only subscripts can cross a slice colon
                    matchSubscriptOnly = True
                else:
                    break
            if hasattr(ic, 'closed'):
                # Anything that is not closed does not stop search, but may require
                # argument transfer (canonical ordering ensures that the innermost
                # paren/bracket/brace will own the arguments that need transfer
                if transferArgsFrom is None:
                    transferArgsFrom = ic
        elif siteType == 'cprhIn' and transferArgsFrom is None and isinstance(ic,
                (listicons.ListIcon, listicons.TupleIcon, listicons.DictIcon)) and \
                not ic.closed:
            # Parent is a list-type icon with at least one comprehension clause
            if token == "endParen" and isinstance(ic, listicons.TupleIcon) and \
                    not ic.noParens:
                return ic, None
            if token == "endBracket" and isinstance(ic, listicons.ListIcon):
                return ic, None
            if token == "endBrace" and isinstance(ic, listicons.DictIcon):
                return ic, None
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
        lastArgSite = ic.sites.argIcons[-1].name
    elif ic.isComprehension():
        lastArgSite = ic.sites.cprhIcons[-2].name
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
    if isinstance(boundingParent, subscripticon.SubscriptIcon):
        bpSite = boundingParent.siteOf(ic, recursive=True)
        bpChild = boundingParent.childAt(bpSite)
        if isinstance(bpChild, subscripticon.SliceIcon):
            sliceSite = bpChild.siteOf(ic, recursive=True)
            if sliceSite == 'indexIcon':
                # ic is on the left site of a slice icon.  The grammar ambiguity
                # resulting from slices having priority over parens, means we want to
                # give the rightmost element of the list/tuple/etc. to the slice and
                # the rest to the top level of the subscript level
                nArgs = 1 if isinstance(ic, parenicon.CursorParenIcon) else \
                    len(ic.sites.argIcons)
                if nArgs != 1:
                    lastArgSite = iconsites.makeSeriesSiteId('argIcons', nArgs-1)
                    lastArg = ic.childAt(lastArgSite)
                    ic.replaceChild(None, lastArgSite)
                    sliceArg = bpChild.childAt(sliceSite)
                    bpChild.replaceChild(None, sliceSite)
                    bpChild.replaceChild(lastArg, sliceSite)
                    boundingParent.insertChild(sliceArg, bpSite)
                    if isinstance(ic, listicons.TupleIcon) and nArgs == 2:
                        cvtTupleToCursorParen(ic, False, False)
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
        if hasattr(recipient, 'closed') and not recipient.closed:
            break
    else:
        recipient = ic
        print("Missed reopened paren in transfer argument search")
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

def findEnclosingSite(startIc, startSite=None):
    """Search upward in the hierarchy above startIc to find a parent that bounds the
    scope of expression-processing, such as a sequence (expressions can't cross commas)
    or parens.  If found, return the icon and site at which startIc is (indirectly)
    attached.  If the search reaches the top, return None for the icon.  If startSite is
    specified, startIc is included in search as candidate for enclosing icon."""
    # This is very similar to reorderexpr.highestAffectedExpr and might be worth unifying
    # with it, but note that this stops at arithmetic parens where that continues upward.
    if startSite is None:
        parent = startIc.parent()
        if parent is None:
            return None, None
        ic = startIc
        site = parent.siteOf(ic)
    else:
        parent = startIc
        ic = None
        site = startSite
    while True:
        if site != 'attrIcon':
            # The largest class of icons that bound expressions are sequences.  As a
            # shortcut, just look for a series site
            if iconsites.isSeriesSiteId(site):
                return parent, site
            # ic is not on a series site. Look for the remaining types that enclose their
            # arguments but are not series: cursor-parens, auto-parens of BinOp icons,
            # statements that take single arguments, and the center site of an inline-if.
            parentClass = parent.__class__
            if parentClass in (opicons.BinOpIcon, opicons.IfExpIcon) and \
                    parent.hasParens or \
                    parentClass in (opicons.DivideIcon, parenicon.CursorParenIcon,
                        listicons.CprhForIcon, listicons.CprhIfIcon) or \
                    parentClass is opicons.IfExpIcon and site == 'testExpr' or \
                    parentClass is assignicons.AugmentedAssignIcon and \
                        site == 'targetIcon' or parentClass in cursors.stmtIcons or \
                    parentClass is subscripticon.SliceIcon and site == 'upperIcon' and \
                        parent.hasSite('stepIcon'):
                return parent, site
        ic = parent
        parent = ic.parent()
        if parent is None:
            return None, None
        site = parent.siteOf(ic)

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
    will fail badly if it does not.  Also note that if splitAt is attached via an
    attribute site, replaceLeft must be capable of attachment to an attribute site."""
    if splitAt.parent() is None:
        return replaceLeft, replaceRight
    leftArg = replaceLeft
    rightArg = replaceRight
    child = splitAt
    for parent in list(splitAt.parentage(includeSelf=False)):
        childSite = parent.siteOf(child)
        childSiteType = parent.typeOf(childSite)
        if parent is splitTo:
            break
        if isinstance(parent, opicons.UnaryOpIcon):
            parent.replaceChild(leftArg, 'argIcon')
            leftArg = parent
        elif childSiteType == 'input' and (isinstance(parent, (infixicon.InfixIcon,
                subscripticon.SliceIcon)) or parent.__class__ in (opicons.BinOpIcon,
                opicons.IfExpIcon) and not parent.hasParens):
            # Parent is a binary op icon without parens, and site is one of the two
            # input sites
            if parent.leftArg() is child:  # Insertion was on left side of operator
                parent.replaceChild(rightArg, binOpLeftArgSite(parent))
                rightArg = parent
            elif parent.rightArg() is child:  # Insertion on right side of operator
                parent.replaceChild(leftArg, binOpRightArgSite(parent))
                leftArg = parent
            else:
                raise Exception(
                    'Unexpected site attachment in "splitExprAtIcon" function')
        elif childSiteType == 'input' and isinstance(parent, blockicons.LambdaIcon) and \
                childSite == 'exprIcon':
            parent.replaceChild(leftArg, 'exprIcon')
            leftArg = parent
        elif childSiteType == 'attrIn':
            leftArg = parent
        else:
            # Parent was not an arithmetic operator or had parens
            raise Exception('Bounding expression found in "splitExprAtIcon" function')
        if child is splitAt and childSiteType == 'attrIn':
            if replaceLeft is not None and replaceLeft.hasSite('attrOut'):
                parent.replaceChild(replaceLeft, 'attrIcon')
            else:
                parent.replaceChild(None, childSite)
        child = parent
    else:
        if splitTo is not None:
            raise Exception(
                '"splitExprAtIcon" function reached top without finding splitTo')
    return leftArg, rightArg

def splitExprAtSite(splitAtIc, splitAtSite, splitTo):
    """Split an expression about a specified site, returning a tree of icons lexically
    left of the site and a tree of icons lexically right of it.  Either or both of the
    returned trees can be None if there is nothing left or right of the site up to
    splitTo.  Like splitExprAtIcon, specifying None in splitTo means it is safe to split
    all the way to the top level.  It is also safe to specify splitAtIc as the same icon
    as splitTo, to indicate that the site is directly on the splitTo icon, though the
    boring result is an empty left tree and the right tree holding everything attached to
    to the site (as a consequence of all enclosing sites being right-of the icons they
    hold).  Note that the icon holding the split site will not necessarily end up on the
    left side.  If this is important, use the highest coincident site corresponding to
    (splitAtIc, splitAtSite)"""
    child = splitAtIc.childAt(splitAtSite)
    if splitAtIc is splitTo:
        return None, child
    if child is None:
        coincSite = splitAtIc.hasCoincidentSite()
        if coincSite is not None and coincSite == splitAtSite:
            return splitExprAtIcon(splitAtIc, splitTo, None, splitAtIc)
        else:
            return splitExprAtIcon(splitAtIc, splitTo, splitAtIc, None)
    return splitExprAtIcon(child, splitTo, None, child)

class EntryCreationTracker:
    def __init__(self, window):
        self.createdIcs = []
        self.window = window

    def __enter__(self):
        entryRegistries.append(self)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        entryRegistries.remove(self)
        return False

    def add(self, createdEntryIc):
        if createdEntryIc.window is self.window:
            self.createdIcs.append(createdEntryIc)

    def get(self):
        """Returns all of the entry icons that were created in the given window while the
        context was active."""
        inWindow = []
        for ic in self.createdIcs:
            topParent = ic.topLevelParent()
            if topParent is not None and topParent in self.window.topIcons:
                inWindow.append(ic)
        return inWindow

    def getLast(self):
        """Returns the las entry icon that was created in the given window while the
        context was active."""
        for ic in reversed(self.createdIcs):
            topParent = ic.topLevelParent()
            if topParent is not None and topParent in self.window.topIcons:
                return ic
        return None

def registerEntryIconCreation(entryIc):
    """Register a newly created entry icon so it can be found by listeners using an
    EntryCreationTracker context manager."""
    for entryRegistry in entryRegistries:
        entryRegistry.add(entryIc)

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
        if stopAtParens or not isinstance(op, (opicons.BinOpIcon, opicons.IfExpIcon,
                opicons.UnaryOpIcon, infixicon.InfixIcon)) or \
                newOpIcon.precedence > op.precedence or \
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
        else:  # BinaryOp or infix
            if op.leftArg() is childOp:  # Insertion was on left side of operation
                op.replaceChild(rightArg, binOpLeftArgSite(op))
                if op.leftArg() is None:
                    cursorIcon, cursorSite = op, binOpLeftArgSite(op)
                rightArg = op
            else:                       # Insertion was on right side of operation
                op.replaceChild(leftArg, binOpRightArgSite(op))
                leftArg = op
            if op.__class__ is opicons.BinOpIcon and op.hasParens:
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

def entryMacroFn(astNode, macroArgs, argAsts, window):
    if macroArgs is not None:
        singleQuoteStartIdx = macroArgs.find("'")
        singleQuoteEndIdx = macroArgs.rfind("'")
        doubleQuoteStartIdx = macroArgs.find('"')
        doubleQuoteEndIdx = macroArgs.rfind('"')
        if singleQuoteStartIdx == -1 and doubleQuoteStartIdx == -1:
            text = ''
        elif singleQuoteStartIdx != -1 and singleQuoteStartIdx != singleQuoteEndIdx:
            text = ast.literal_eval(macroArgs[singleQuoteStartIdx:singleQuoteEndIdx + 1])
        elif doubleQuoteStartIdx != -1 and doubleQuoteStartIdx != doubleQuoteEndIdx:
            text = ast.literal_eval(macroArgs[doubleQuoteStartIdx:doubleQuoteEndIdx + 1])
        else:
            # There's verification code in filefmt.py (verifyEntryMacroArgs), so this
            # shouldn't happen unless they get out of sync.  If we ever get the
            # capability to raise syntax errors from macro functions, that checking
            # should be moved, here.
            text = ''
    else:
        text = ''
    entryIc = EntryIcon(initialString=text, window=window)
    if argAsts is not None:
        for argAst in argAsts:
            if isinstance(argAst, ast.Tuple) and hasattr(argAst, 'isNakedTuple'):
                seriesIcons = [icon.createFromAst(astNode, window)
                    for astNode in argAst.elts]
                entryIc.appendPendingArgs([seriesIcons])
            else:
                argIcons = icon.createFromAst(argAst, window)
                entryIc.appendPendingArgs([argIcons])
    if not isinstance(astNode, ast.Attribute):
        return entryIc
    # If we're on an attribute site, the entry icon needs to be put underneath whatever
    # is in the .value slot of the Attribute AST.
    topIcon = icon.createFromAst(astNode.value, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(entryIc, "attrIcon")
    return topIcon

# Note that although registering the $Entry$ macro here would normally imply that the
# processing is confined to this module, $Entry$ also has hard-coded support in
# filefmt.py.
filefmt.registerBuiltInMacro('Entry', None, entryMacroFn)
