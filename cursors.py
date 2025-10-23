# Copyright Mark Edel  All rights reserved
# Icon window cursor, and some support code for icon backspace functionality (in here,
# rather than icon.py, because it needs to know about many icon types, and icon.py, being
# the base class for icons, will tie the import system in knots if it tries to import its
# own subclasses).
import winsound
import tokenize
import token
from PIL import Image
from operator import itemgetter
from dataclasses import dataclass
from typing import Optional
import ast
import io
import comn
import iconsites
import icon
import opicons
import blockicons
import nameicons
import listicons
import stringicon
import subscripticon
import parenicon
import entryicon
import commenticon
import expredit

# How far to move the cursor per arrow keystroke on the window background
WINDOW_CURSOR_INCREMENT = 20

# How far away from the edges of the window to keep the window background cursor
WINDOW_CURSOR_MARGIN = 5

# Max allowable cursor y movement for left and right arrow movement over icons
HORIZ_ARROW_Y_JUMP_MAX = 12

# Minimum threshold (pixels) for cursor movement via arrow keys (to prevent minor
# alignment issues from dominating the destination site choice
VERT_ARROW_Y_JUMP_MIN = 5
VERT_ARROW_X_JUMP_MIN = 1

# Limits (pixels) for cursor movement via arrow key
VERT_ARROW_MAX_DIST = 400
HORIZ_ARROW_MAX_DIST = 600

# Weight of x distance in y cursor movement
VERT_ARROW_X_WEIGHT = 2

# Number of pixels beyond cursor position to reveal with autoscroll
AUTOSCROLL_H_MARGIN = 5
AUTOSCROLL_V_MARGIN = 7

inputSiteCursorImage = comn.asciiToImage((
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    ".% .",
    "% ..",
    ".% .",
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    "..% ",))
inputSiteCursorOffset = 6

attrSiteCursorImage = comn.asciiToImage((
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    "%.",
    "%.",
    ".%",
    ".%",))
attrSiteCursorOffset = 11

cprhSiteCursorImage = comn.asciiToImage((
    "%.",
    "%.",
    "%.",
    "%.",
    "%%",
    "%%",
    "%%",
    "%%",
    "%%",
    "%.",
    "%.",
    "%.",
    "%.",))
cprhSiteCursorXOffset = 1
cprhSiteCursorYOffset = 6

seqInSiteCursorImage = comn.asciiToImage((
    ".......",
    "%25852%",
    ".52%25.",
))
seqInSiteCursorXOffset = 3
seqInSiteCursorYOffset = 3

seqOutSiteCursorImage = comn.asciiToImage((
    ".52%25.",
    "%25852%",
    ".......",))
seqOutSiteCursorXOffset = 3
seqOutSiteCursorYOffset = 0

typeoverCursorHeight = sum(icon.globalFont.getmetrics()) + 2
typeoverCursorImage = Image.new('RGBA', (1, typeoverCursorHeight), color=(0, 0, 0, 255))

multiTokenOperators = {'is': {'not'}, 'not':{'in'},
    'async':{'def', 'for', 'while', 'with'}}

class Cursor:
    def __init__(self, window, cursorType=None, ic=None, site=None):
        self.window = window
        self.type = cursorType
        self.pos = (0, 0)
        self.icon = ic
        self.site = site
        self.siteType = None if site is None else ic.typeOf(site)
        self.lastDrawRect = None
        self.blinkState = False
        self.anchorHint = None
        self.protoTextPos = None
        self.textPartId = None

    def setTo(self, cursorType, ic=None, site=None, pos=None, eraseOld=True,
            drawNew=False, placeEntryText=True, partId=1):
        """Place the cursor of a given cursor type (cursorType).  See other setToXXX
        methods for details of each type."""
        if cursorType == 'window':
            self.setToWindowPos(pos, eraseOld, drawNew, placeEntryText)
        elif cursorType == 'icon':
            self.setToIconSite(ic, site, eraseOld=eraseOld, drawNew=drawNew,
                placeEntryText=placeEntryText)
        elif cursorType == 'text':
            self.setToText(ic, pos, eraseOld, drawNew, placeEntryText, partId)
        elif cursorType == 'typeover':
            self.setToTypeover(ic, eraseOld, drawNew)

    def setToWindowPos(self, pos, eraseOld=True, drawNew=False, placeEntryText=True):
        """Place the cursor at an arbitrary location on the window background.  Be
        aware that this can cause rearrangement of icons by virtue of taking focus from
        an entry icon, which will then try to place its text content and pending
        arguments.  You must therefore either call this where rearrangement is safe,
        or suppress this behavior by setting placeEntryText=False.  Even if
        placeEntryText is set to False, it is still necessary to check for dirty icon
        layouts after calling, as this is the mechanism by which icons that draw
        additional focus graphics can redraw them.  By default, erases and does not
        redraw the cursor, as the convention is to move the cursor before making layout
        calls to rearrange the icon structure, and then calling drawAndHold() to give
        the user immediate feedback as to where the cursor landed after an operation."""
        if self.type == "text" and isIconAndCanEditText(self.icon) or \
                self.type == "typeover" and hasattr(self.icon, 'focusOut'):
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "window"
        self.pos = pos
        self.window.updateTypeoverStates()
        if drawNew:
            self.draw()
        self.window.resetBlinkTimer()
        self.window.requestScroll('cursor')
        self.clearAnchorHint()

    def setToIconSite(self, ic, siteIdOrSeriesName, seriesIndex=None, eraseOld=True,
            drawNew=False, placeEntryText=True, requestScroll=True):
        """Place the cursor on an icon site.  Be aware that this can cause
        rearrangement of icons by virtue of taking focus from an entry icon, which will
        then try to place its text content and pending arguments.  You must therefore
        either call this where rearrangement is safe, or suppress this behavior by
        setting placeEntryText=False.  Even if placeEntryText is set to False, it is
        still necessary to check for dirty icon layouts after calling, as this is the
        mechanism by which icons that draw additional focus graphics can redraw them.
        By default, erases and does not redraw the cursor, as the convention is to move
        the cursor before making layout calls to rearrange the icon structure, and then
        calling drawAndHold() to give the user immediate feedback as to where the cursor
        landed after an operation."""
        if self.type == "text" and isIconAndCanEditText(self.icon) or \
                self.type == "typeover" and hasattr(self.icon, 'focusOut'):
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "icon"
        self.icon = ic
        if seriesIndex is None:
            self.site = siteIdOrSeriesName
        else:
            self.site = iconsites.makeSeriesSiteId(siteIdOrSeriesName, seriesIndex)
        self.siteType = ic.typeOf(self.site)
        self.window.updateTypeoverStates()
        if drawNew:
            self.draw()
        self.window.resetBlinkTimer()
        if requestScroll:
            self.window.requestScroll('cursor')
        self.clearAnchorHint()

    def setToText(self, ic, pos=None, eraseOld=True, drawNew=False, placeEntryText=True,
             partId=1):
        """Place the cursor within a text-edit-capable icon (entry, comment or string) or
        a proto-text cursor position on a non-text-edit-capabable one.  ic can also be
        passed as a tuple of an icon and and icon site to place a proto-text cursor on
        an empty series site.  Note that the cursor position within  text-editable icons
        is not held by the cursor object, but by ic.  Also be aware that this can cause
        rearrangement of icons by virtue of taking focus from an entry icon, which will
        then try to place its text content and pending arguments.  You must therefore
        either call this where rearrangement is safe, or suppress this behavior by
        setting placeEntryText=False.  Even if placeEntryText is set to False, it is
        still necessary to check for dirty icon layouts after calling, as this is the
        mechanism by which icons that draw additional focus graphics can redraw them.
        By default, erases and does not redraw the cursor, as the convention is to move
        the cursor before making layout calls to rearrange the icon structure, and then
        calling drawAndHold() to give the user immediate feedback as to where the cursor
        landed after an operation."""
        if self.icon != ic and (self.type == "text" and isIconAndCanEditText(self.icon)
                or self.type == "typeover" and hasattr(self.icon, 'focusOut')):
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "text"
        self.icon = ic
        self.window.updateTypeoverStates()
        if isIconAndCanEditText(self.icon):
            ic.focusIn()
            if pos is not None:
                ic.setCursorPos(pos)
            self.protoTextPos = None
        else:
            self.protoTextPos = pos
        self.textPartId = partId
        if drawNew:
            self.draw()
        self.window.resetBlinkTimer()
        # Note that the autoscroll request is done in in the icon's setCursorPos method,
        # but skipped if the icon doesn't have the cursor.  Therefore, when code calls
        # setCursorPos first, it will not yet have been done.
        self.window.requestScroll('cursor')
        self.clearAnchorHint()

    def setToTypeover(self, ic, eraseOld=True, drawNew=False):
        """Place the cursor into a typeover-icon.  Note that you must also call the
        icon's setTypeover() function to actually set the typeover index (this function
        directs keyboard focus and controls cursor drawing).  By default, erases and does
        not redraw the cursor, as the convention is to move the cursor before making
        layout calls to rearrange the icon structure, and then calling drawAndHold() to
        give immediate feedback as to where the cursor landed after an operation."""
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "typeover"
        self.icon = ic
        self.window.updateTypeoverStates()
        if drawNew:
            self.draw()
        self.window.resetBlinkTimer()
        self.window.requestScroll('cursor')
        self.clearAnchorHint()

    def setToBestCoincidentSite(self, ic, site):
        if site == "output":
            coincidentSite = ic.hasCoincidentSite()
            if coincidentSite:
                cursorIc, cursorSite = iconsites.lowestCoincidentSite(ic, coincidentSite)
            else:
                cursorIc, cursorSite = ic, site
        else:
            cursorIc, cursorSite = iconsites.lowestCoincidentSite(ic, site)
        self.setToIconSite(cursorIc, cursorSite)

    def clearAnchorHint(self):
        if self.anchorHint is not None and self.type == 'icon':
            cursorIc, cursorSite, anchorIc, anchorSite = self.anchorHint
            if cursorIc is self.icon and cursorSite == self.site:
                if len(self.window.sel.selSet) > 0:
                    # The cursor didn't move and selection wasn't cleared, so preserve it
                    return
        self.anchorHint = None

    def moveToIconSite(self, cursorType, ic, site, pos, evt):
        """Place the cursor at an icon site, and possibly extend the selection to it (if
        the shift key was pressed in the event (evt) that triggered the movement)."""
        shiftPressed = evt.state & comn.SHIFT_MASK
        if shiftPressed:
            if cursorType != 'icon':
                print('moveToIconSite tried to select to a non-site destination')
                return
            self.selectToSiteOrPart(ic, site)
        else:
            self.setTo(cursorType, ic, site, pos)

    def moveToTextSite(self, ic, partId, pos, evt):
        """Place the cursor at a text site, and possibly extend the selection to it (if
        the shift key was pressed in the event (evt) that triggered the movement)."""
        if evt.state & comn.SHIFT_MASK:
            self.selectToTextPos(ic, partId, pos)
        else:
            self.setToText(ic, pos, partId=partId)

    def getOutline(self, addAutoscrollMargin=False):
        cursorImg, left, top = self._getImgAndPos()
        if cursorImg is None:
            return None
        right = left + cursorImg.width
        bottom = top + cursorImg.height
        if addAutoscrollMargin:
            return (left - AUTOSCROLL_H_MARGIN, top - AUTOSCROLL_V_MARGIN,
            right + AUTOSCROLL_H_MARGIN, bottom + AUTOSCROLL_V_MARGIN)

    @dataclass
    class SavedState:
        cursorType: str
        ic: Optional[icon.Icon]
        site: Optional[str]
        pos:Optional[tuple]

    def saveState(self):
        return self.SavedState(self.type, self.icon, self.site, pos=self.pos)

    def restoreState(self, state, eraseOld=True, drawNew=False, placeEntryText=True):
        self.setTo(state.cursorType, state.ic, state.site, state.pos, eraseOld=True,
            drawNew=False, placeEntryText=True)

    def selectToSiteOrPart(self, ic, site=None, partId=None):
        """Extend or reduce the existing selection (or select from the existing cursor
        location) to site: (ic, site) if site is specified, or icon part (ic, partId) if
        partId is specified.  Also places the cursor at the requested site if site was
        specified, or on the appropriate side of ic if partId was specified."""
        # Earlier versions were written with the idea of the cursor being independent of
        # the primary selection to enable operations between them.  That strayed too far
        # from the conventional editor model, since we're all accustomed to the cursor
        # and primary selection behaving as a unified entity.  Instead, we've settled on
        # the common convention that when there's a selection, the cursor may accompany
        # it to indicate the 'active' end of the selection (and in the case of a disjoint
        # selection, the active segment). We go one step further in also using selections
        # with no cursor to indicate that a selection is 'unanchored' (has no active
        # end).  These allow our single-click selections to be used to start a lexical
        # range-selections in either direction.
        selectedIcons = set(self.window.sel.selectedIcons())
        redrawRect = comn.AccumRects()
        if len(selectedIcons) == 0:
            if self.type != "icon":
                # There's no selection or cursor to extend from
                if site is None:
                    self.window.sel.select(ic)
                    self.window.refresh(ic.rect)
                else:
                    self.setToIconSite(ic, site)
                return
            # This is a new cursor-based selection
            anchorIc = self.icon
            anchorSite = self.site
            origSel = set()
            if site is None:
                # The caller specified an icon part rather than a site, and we need to
                # figure out which site (left or right) of the icon part to use.
                partOnRight = expredit.partIsRightOfSite(anchorIc, anchorSite, ic, partId)
                if partOnRight is None:
                    # There is an icon cursor, but it's in different sequence from ic
                    self.window.sel.select(ic)
                    self.window.refresh(ic.rect)
                    return
                if partOnRight:
                    ic, site = expredit.siteRightOfPart(ic, partId)
                else:
                    ic, site = expredit.siteLeftOfPart(ic, partId)
        else:
            # There is a selection.  If the starting cursor position is within the
            # a selection, use the contiguous range it touches.  If not, use the nearest
            # selection to the new position.  Anchor the expansion at the (lexically)
            # opposite end from the original cursor, or if there is no original cursor,
            # from the new cursor position.
            nearestIc = None
            if self.type == "icon":
                # There is also a cursor, which can tell us where to anchor the selection
                # and in some cases which fragment of a disjoint selection to use.
                # But, before using it, ensure that it's in the same sequence as ic.
                order = expredit.stmtOrder(self.icon.topLevelParent(),
                    ic.topLevelParent())
                if order is not None:
                    refIc = self.icon
                    refSite = self.site
                    nearestIc, nearestIcDist = expredit.nearestSelectedIcon(refIc, refSite)
                    if nearestIcDist > 2:
                        # If cursor isn't near a selection (it can be at least one icon
                        # part away due to unselected assignIcon '=' part), disregard it
                        # and find the selection nearest the requested icon/site, instead.
                        nearestIc = None
            if nearestIc is None:
                refIc = ic
                refSite = site
                nearestIc, nearestIcDist = expredit.nearestSelectedIcon(ic, site, partId)
            if nearestIc is None:
                # There may be a selection, but it's not in this sequence, so there's
                # nothing to extend
                if site is None:
                    self.window.sel.select(ic)
                    self.window.refresh(ic.rect)
                else:
                    self.setToIconSite(ic, site)
                return
            if nearestIcDist == 0:
                # The cursor site, clicked site, or clicked icon is within the selection
                if refSite is None:
                    rightIc, rightSite = expredit.siteRightOfPart(ic, partId)
                    leftIc, leftSite = expredit.siteLeftOfPart(ic, partId)
                    fwdIc, fwdSite, fwdDist = expredit.searchFwdForUnselected(rightIc,
                        rightSite)
                    revIc, revSite, revDist = expredit.searchRevForUnselected(leftIc,
                        leftSite)
                else:
                    fwdIc, fwdSite, fwdDist = expredit.searchFwdForUnselected(refIc,
                        refSite)
                    revIc, revSite, revDist = expredit.searchRevForUnselected(refIc,
                        refSite)
                if revDist > fwdDist:
                    anchorIc, anchorSite = revIc, revSite
                elif fwdDist > revDist:
                    anchorIc, anchorSite = fwdIc, fwdSite
                else:
                    # Anchor is ambiguous (fwdDist == revDist).  If we have an anchor
                    # hint and it matches one of our choices, use it.  Otherwise, use
                    # the random choice, below.
                    anchorIc, anchorSite = fwdIc, fwdSite
                    if self.anchorHint is not None and self.type == 'icon':
                        hintCursorIc, hintCursorSite, hintAnchorIc, hintAnchorSite = \
                            self.anchorHint
                        if self.icon is hintCursorIc and self.site == hintCursorSite:
                            if fwdIc is hintAnchorIc and fwdSite == hintAnchorSite:
                                anchorIc, anchorSite = fwdIc, fwdSite
                            elif revIc is hintAnchorIc and revSite == hintAnchorSite:
                                anchorIc, anchorSite = revIc, revSite
            else:
                # The reference site is outside of the selection.  This is probably an
                # unanchored selection (as we set refIc to the requested site for
                # unanchored selections).  However, it's also remotely possible that
                # we've somehow got a separated cursor and selection.
                fwdIc, fwdSite, fwdDist = expredit.searchFwdForUnselected(nearestIc)
                revIc, revSite, revDist = expredit.searchRevForUnselected(nearestIc)
                if nearestIcDist > 0:
                    # The selection is lexically right-of the reference site
                    anchorIc, anchorSite = fwdIc, fwdSite
                else:
                    # The selection is lexically left-of the reference site
                    anchorIc, anchorSite = revIc, revSite
            origSel = expredit.iconsInLexicalRangeBySite(revIc, revSite, fwdIc, fwdSite,
                preOrdered=True)
            if site is None:
                # Caller specified a partId rather than a site, but now we need a site to
                # make the selection and place the cursor.  Choose the left or right side
                # of the icon part based upon being opposite from that of the anchor.
                if expredit.partIsRightOfSite(anchorIc, anchorSite, ic, partId):
                    ic, site = expredit.siteRightOfPart(ic, partId)
                else:
                    ic, site = expredit.siteLeftOfPart(ic, partId)
        # Record an anchor-hint for use only in the very specific case of an ambiguous
        # selection+cursor combination (such as when you select an empty list or tuple
        # by moving the cursor with Shift+Arrow to middle of two selected icon parts)
        self.anchorHint = ic, site, anchorIc, anchorSite
        # Update the selection
        newSel = expredit.iconsInLexicalRangeBySite(anchorIc, anchorSite, ic, site)
        erase = origSel.difference(newSel)
        select = newSel.difference(selectedIcons)
        for i in erase:
            redrawRect.add(expredit.iconOfSelEntry(i).hierRect())
            self.window.sel.select(i, False)
        for i in select:
            redrawRect.add(expredit.iconOfSelEntry(i).hierRect())
            self.window.sel.select(i, True)
        if redrawRect.get() is not None:
            self.window.refresh(redrawRect.get(), redraw=True)
        # Place the cursor at the requested location
        self.setToIconSite(ic, site)

    def selectToTextPos(self, newIc, newPartId, newPos):
        """Extend existing text selection or start new selection from cursor to new text
        cursor position.  Does nothing if there is not a suitable selection or cursor
        from which to start (the starting location must be a text selection or a text or
        icon cursor, it is not currently possible to start from an icon selection)."""
        sel = self.window.sel
        sel.pruneSelectedIcons()
        fixAnchorPosGuess = None
        fixAnchorSiteGuess = False
        if sel.isText():
            # If there is an existing text selection, extend it
            if sel.anchorDirection is None:
                # There's an unanchored text selection, and we need to figure out which
                # end to anchor.  Luckily the only kind of unanchored text selection we
                # support is a word selection which exists entirely within a single icon.
                # Since we at least know the *icon* at which the selection is anchored,
                # we can either 1) (if the new cursor position is also in that icon),
                # figure out the direction from the relative text positions, or 2) (if
                # the new cursor position is in a different icon), randomly choose one
                # end of the selection (left) as the anchor and fix up the text position
                # if we guessed wrong and selectTextBetween determines that the anchor
                # icon is not indeed on the left end of the selection.
                if sel.leftIc is newIc and sel.rightIc is newIc and \
                        sel.leftPartId == sel.rightPartId == newPartId:
                    selCtr = (sel.rightPos + sel.leftPos) // 2
                    sel.anchorDirection = 'Right' if newPos < selCtr else 'Left'
                else:
                    sel.anchorDirection = 'Left'
                    fixAnchorPosGuess = sel.rightPos
            if sel.anchorDirection == 'Left':
                anchorIc = sel.leftIc
                anchorPartId = sel.leftPartId
                anchorPos = sel.leftPos
            else:
                anchorIc = sel.rightIc
                anchorPartId = sel.rightPartId
                anchorPos = sel.rightPos
            origSel = sel.textSel.copy()
            origSelEnds = {sel.leftIc, sel.rightIc}
        elif self.type == 'text':
            # There is no selection and a text cursor, select between cursor and new icon
            # (we know that the original cursor position is the anchor and the new
            # position is the active end).
            anchorIc = self.icon
            if isIconAndCanEditText(anchorIc):
                anchorPartId = 1
                anchorPos = anchorIc.cursorPos
            else:
                anchorPartId = self.textPartId
                anchorPos = self.protoTextPos
            origSel = {}
            origSelEnds = set()
        elif self.type == 'icon':
            # There is no selection and an icon cursor.  We need to choose a text site as
            # an anchor, but we don't know what direction, yet, so guess the location
            # right of the site, and fix it up later if we get it wrong.
            anchorIc, anchorPartId, anchorPos = nextTextPos(self.icon, siteId=self.site)
            fixAnchorSiteGuess = True
            origSel = {}
            origSelEnds = set()
        else:
            # No usable anchor (give up)
            return
        if anchorIc == newIc and anchorPartId == newPartId and anchorPos == newPos:
            # If both ends of the new selection point to the same character position, we
            # now have a 0-length selection and should remove it.
            redrawRect = comn.AccumRects()
            for i in origSel.keys():
                if isinstance(i, tuple):
                    icon.rectOfEmptySite(i[0], i[1])
                else:
                    redrawRect.add(i.rect)
            sel.clearSelection()
            if redrawRect.get() is not None:
                self.window.refresh(redrawRect.get(), redraw=True)
            self.setToText(newIc, newPos, partId=newPartId)
            return
        sel.selectTextBetween(anchorIc, anchorPartId, anchorPos, newIc, newPartId, newPos)
        # While the code above is mostly able to figure out which end of the *existing*
        # selection was the anchor, the new selection might now invert this, which we
        # can now deduce by looking at the resulting selection created by the call to
        # selectTextBetween (which will use our anchor at one end).
        if sel.leftIc is sel.rightIc:
            if sel.leftPartId == sel.rightPartId:
                sel.anchorDirection = 'Right' if newPos < anchorPos else 'Left'
            else:
                sel.anchorDirection = 'Right' if newPartId < anchorPartId else 'Left'
        elif sel.rightIc is anchorIc:
            sel.anchorDirection = 'Right'
        elif sel.leftIc is anchorIc:
            sel.anchorDirection = 'Left'
        else:
            print("selectToTextPos did not find anchorIc after selection")
        if fixAnchorPosGuess is not None and sel.anchorDirection == 'Right':
            sel.rightPos = fixAnchorPosGuess
        if fixAnchorSiteGuess and sel.anchorDirection == 'Right':
            sel.rightIc, sel.rightPartId, sel.rightPos = prevTextPos(self.icon,
                siteId=self.site)
            del sel.textSel[self.icon]
        # Redraw changed icons
        changedIcons = set(sel.textSel.keys()).symmetric_difference(set(origSel.keys()))
        for key, value in sel.textSel.items():
            if key in origSel and value != origSel[key]:
                changedIcons.add(key)
        changedIcons |= origSelEnds
        changedIcons.add(sel.leftIc)
        changedIcons.add(sel.rightIc)
        redrawRect = comn.AccumRects()
        for i in changedIcons:
            if isinstance(i, tuple):
                redrawRect.add(icon.rectOfEmptySite(i[0], i[1]))
            else:
                redrawRect.add(i.rect)
        if redrawRect.get() is not None:
            self.window.refresh(redrawRect.get(), redraw=True)
        # We have established the selection anchor (by virtue of being asked to select
        # *to* a particular text position), which we indicate to the user by moving the
        # cursor to the 'active' (opposite from the anchor) end of the selection.
        self.setToText(newIc, newPos, partId=newPartId, placeEntryText=False)

    def _seqIconsBetween(self, topIcons):
        """Return all of the icons in the sequence including topIcons (filling in gaps,
        and adding all of the icons in the statement hierarchy and statement-comments)"""
        # Note that we can cheat, here for efficiency, knowing that the caller is working
        # geometrically, so we can order the sequence by icon position
        topIconSet = set(topIcons)
        sortedTopIcons = sorted(topIcons, key=lambda i: i.pos()[1])
        iconsInSeq = set()
        for ic in icon.traverseSeq(sortedTopIcons[0]):
            iconsInSeq.add(ic)
            if ic is sortedTopIcons[-1]:
                break
        else:
            iconsInSeq = set()
        # Fail softly if something bad happend in the geometric ordering, and make sure
        # that at least all statements passed in are represented
        if not topIconSet.issubset(iconsInSeq):
            print("Did your last cursor movement leave a gap in selected statments?")
            iconsInSeq.union(topIconSet)
        # return the full hierarchy
        return [i for ic in iconsInSeq for i in ic.traverse(inclStmtComment=True)]

    def removeCursor(self, eraseOld=True, placeEntryText=True):
        """Remove the cursor from the window.  Be aware that this can cause rearrangement
        of icons by virtue of taking focus from an entry icon, which will then try to
        place its text content and pending arguments (so 1. don't call this where such
        rearrangement would cause trouble and 2. be sure to check for dirty icon layouts
        after calling)."""
        if self.type == "text" and isIconAndCanEditText(self.icon):
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = None
        self.clearAnchorHint()

    def blink(self):
        self.blinkState = not self.blinkState
        if self.blinkState:
            self.draw()
        else:
            self.erase()

    def draw(self):
        if self.type is None or self.window.dragging is not None:
            return
        cursorImg, x, y = self._getImgAndPos()
        if cursorImg is None:
            return
        cursorRegion = (x, y, x + cursorImg.width, y + cursorImg.height)
        self.lastDrawRect = cursorRegion
        cursorRegion = self.window.contentToImageRect(cursorRegion)
        cursorDrawImg = self.window.image.crop(cursorRegion)
        cursorDrawImg.paste(cursorImg, mask=cursorImg)
        self.window.drawImage(cursorDrawImg, cursorRegion[:2])
        self.blinkState = True

    def _getImgAndPos(self):
        if self.type == "window":
            cursorImg = inputSiteCursorImage
            x, y = self.pos
            y -= inputSiteCursorOffset
        elif self.type == "icon":
            sitePos = self.icon.posOfSite(self.site)
            if sitePos is None:
                return None, 0, 0  # fail softly if cursor moved before site fully exists
            x, y = sitePos
            if self.siteType in ("input", "output"):
                cursorImg = inputSiteCursorImage
                y -= inputSiteCursorOffset
            elif self.siteType in ("attrOut", "attrIn"):
                cursorImg = attrSiteCursorImage
                y -= attrSiteCursorOffset
            elif self.siteType == "seqIn":
                cursorImg = seqInSiteCursorImage
                x -= seqInSiteCursorXOffset
                y -= seqInSiteCursorYOffset
            elif self.siteType == "seqOut":
                cursorImg = seqOutSiteCursorImage
                x -= seqOutSiteCursorXOffset
                y -= seqOutSiteCursorYOffset
            elif self.siteType in ("cprhIn", "cprhOut"):
                cursorImg = cprhSiteCursorImage
                x -= cprhSiteCursorXOffset
                y -= cprhSiteCursorYOffset
            else:
                return None, 0, 0
        elif self.type == "text":
            if self.icon is None:
                return None, 0, 0
            elif isinstance(self.icon, tuple):
                eIcon = self.icon[0]
            else:
                eIcon = self.icon
            cursorImg = eIcon.textCursorImage()
            if isinstance(self.icon, tuple):
                x, y = icon.emptySiteTextCursorPos(self.icon, self.protoTextPos)
            elif eIcon.canEditText:
                x, y = eIcon.cursorWindowPos()
            else:
                x, y = eIcon.textCursorWindowPos(self.textPartId, self.protoTextPos)
            x -= cursorImg.width // 2
            y -= cursorImg.height // 2
        elif self.type == "typeover":
            if self.icon is None:
                return None, 0, 0
            cursorImg = typeoverCursorImage
            x, y = self.icon.rect[:2]
            xOffset, yOffset = self.icon.typeoverCursorPos()
            x += xOffset
            y += yOffset - cursorImg.height // 2
        else:
            return None, 0, 0
        return cursorImg, x, y

    def drawAndHold(self, holdTime=comn.CURSOR_BLINK_RATE):
        """Redraw cursor and reset the blink timer to keep it visible for a full blink
        cycle (or longer/shorter if holdTime (milliseconds) is explicitly specified)."""
        self.draw()
        self.window.resetBlinkTimer(holdTime=holdTime)

    def processArrowKey(self, evt):
        direction = evt.keysym
        if self.type is None:
            return
        elif self.type == "text":
            if isIconAndCanEditText(self.icon):
                self.icon.arrowAction(direction, evt)
            else:
                self.protoTextArrowAction(direction, self.textPartId, evt)
            return
        elif self.type == "typeover":
            self.erase()
            if direction in ("Up", "Down"):
                fromIcon = self.icon
                fromSite = fromIcon.sites.lastCursorSite()
                cursorType, toIcon, toSite, toPos = geometricTraverse(fromIcon, fromSite,
                    direction, enterTextFields=not evt.state & comn.SHIFT_MASK)
                self.moveToIconSite(cursorType, toIcon, toSite, toPos, evt)
            siteBefore, siteAfter, text, idx = self.icon.typeoverSites()
            if direction == 'Right':
                # Move to site after (typeover will be automatically cancelled)
                self.setToIconSite(self.icon, siteAfter)
            if direction == 'Left':
                # reset typeover and move to previous site
                self.icon.setTypeover(0, siteAfter)
                self.icon.draw()
                self.window.refresh(self.icon.rect, redraw=False, clear=False)
                siteBeforeIcon = self.icon.childAt(siteBefore)
                if siteBeforeIcon is None:
                    toIcon, toSite = self.icon, siteBefore
                else:
                    toIcon, toSite = icon.rightmostSite(siteBeforeIcon)
                self.moveToIconSite('icon', toIcon, toSite, None, evt)
            return
        if self.type == "window":
            cursorType, ic, site, pos, partId = geometricTraverseFromPos(*self.pos,
                direction, self.window, limitDist=(WINDOW_CURSOR_INCREMENT,
                WINDOW_CURSOR_INCREMENT), editableTextFields=False)
            self.setTo(cursorType, ic, site, pos)
        elif self.type == "icon":
            self._processIconArrowKey(evt)

    def processBreakingArrowKey(self, evt):
        """Alt+arrow action (since we don't have configurable bindings, yet, I can say
        this).  Breaks in to and text edits the icon in the direction of the arrow key
        from the cursor."""
        if evt.keysym == 'Left':
            ic, partId, pos = prevTextPos(self.icon, siteId=self.site, direction='Left')
        elif evt.keysym == 'Right':
            ic, partId, pos = nextTextPos(self.icon, siteId=self.site, direction='Right')
        else:
            # Up/down movement
            cursorX, cursorY = self.icon.posOfSite(self.site)
            cursorType, ic, site, pos, partId = geometricTraverseFromPos(cursorX,
                cursorY, evt.keysym, self.window, limitAdjacentStmt=self.icon,
                editableTextFields=True, onlyTextFields=True)
            if ic is None:
                print("No text sites on adjacent stmt (remove once all icons have "
                    "them or means of skipping established)")
                return
            self.window.sel.clearSelection()
            if evt.state & comn.SHIFT_MASK:
                # If the Shift key is pressed, moveToTextSite can't start a text
                # selection from an icon cursor position.
                if evt.keysym == 'Up':
                    selStartIc, selStartPartId, selStartPos = prevTextPos(self.icon,
                        siteId=self.site, direction='Left')
                else:
                    selStartIc, selStartPartId, selStartPos = nextTextPos(self.icon,
                        siteId=self.site, direction='Right')
                self.setToText(selStartIc, selStartPos, partId=selStartPartId)
            self.moveToTextSite(ic, partId, pos, evt)
            return
        if pos is None:
            # Reached start or end of sequence
            return
        # We started on an icon site, so even if the user is holding shift, all we do is
        # move the cursor in to the text of the icon (and clear the selection for good
        # measure, as either type would mean something was wrong)
        self.window.sel.clearSelection()
        self.setToText(ic, pos, partId=partId)

    def protoTextArrowAction(self, direction, partId, evt):
        """Move cursor from a proto-text position in the given arrow direction"""
        # ...It sometimes feels like we abandon proto-text cursors too easily (user moves
        # the cursor without holding Alt).  It might be worth considering staying within
        # the text and adding some other exit mechanism.
        if direction == 'Left':
            if evt.state & comn.SHIFT_MASK or evt.state & comn.ALT_MASK:
                newIc, newPartId, newPos = prevTextPos(self.icon, pos=self.protoTextPos,
                    partId=self.textPartId, direction='Left')
            else:
                # Move cursor out of text if alt or shift is not pressed
                if isinstance(self.icon, tuple):  # Empty site
                    self.setToIconSite(self.icon[0], self.icon[1])
                else:
                    parent = self.icon.parent()
                    if parent is None:
                        ic, site = expredit.siteLeftOfPart(self.icon, partId)
                        self.setToIconSite(ic, site)
                    else:
                        self.setToIconSite(parent, parent.siteOf(self.icon))
                return
        elif direction == 'Right':
            if evt.state & comn.SHIFT_MASK or evt.state & comn.ALT_MASK:
                newIc, newPartId, newPos = nextTextPos(self.icon, pos=self.protoTextPos,
                    partId=self.textPartId, direction='Right')
            else:
                # Move cursor out of text if alt or shift is not pressed
                if isinstance(self.icon, tuple):  # Empty site
                    ic, siteId = self.icon
                    siteId = iconsites.nextSeriesSiteId(siteId)
                    if not ic.hasSite(siteId):
                        # If this actually happens, write some code for it...
                        print("protoTextArrowAction: moving cursor from non-existant"
                            "empty-icon-site text site")
                        return
                    self.setToIconSite(ic, siteId)
                else:
                    self.setToIconSite(self.icon, self.icon.siteRightOfPart(partId))
                return
        else:
            # direction is up or down, do a geometric traverse
            if isinstance(self.icon, tuple):  # Empty site
                cursorX, cursorY = icon.emptySiteTextCursorPos(self.icon,
                    self.protoTextPos)
                stmtOfCursor = self.icon[0].topLevelParent()
            else:
                cursorX, cursorY = self.icon.textCursorWindowPos(self.textPartId,
                    self.protoTextPos)
                stmtOfCursor = self.icon.topLevelParent()
            onlyTextFields = evt.state & comn.SHIFT_MASK or evt.state & comn.ALT_MASK
            cursorType, ic, site, pos, partId = geometricTraverseFromPos(cursorX,
                cursorY, direction, self.window, limitAdjacentStmt=stmtOfCursor,
                limitDist=(HORIZ_ARROW_MAX_DIST, VERT_ARROW_MAX_DIST),
                editableTextFields=True, onlyTextFields=onlyTextFields)
            if onlyTextFields:
                if ic is None:
                    print("No text sites on adjacent stmt (remove once all icons have "
                        "them or means of skipping established)")
                    return
                self.moveToTextSite(ic, partId, pos, evt)
            else:
                self.moveToIconSite(cursorType, ic, site, pos, evt)
            return
        if newIc is None:
            # No more text sites (start or end of sequence)
            return
        self.moveToTextSite(newIc, newPartId, newPos, evt)

    def _processIconArrowKey(self, evt):
        """For cursor on icon site (self.type == "icon"), set new site based on arrow
        direction"""
        if evt.keysym in ('Left', 'Right') and not (evt.state & comn.CTRL_MASK):
            # Lexical traversal. This also visits text in entry icons (and possibly
            # comments, but that code is not done, yet).  Note particularly that we skip
            # over the site to the left of the entry icon in normal traversal, because
            # we'd prefer they typed there, instead.
            if evt.keysym == 'Left' and _isTextIcBodySite(self.icon, self.site) and \
                    not (evt.state & comn.SHIFT_MASK):
                self.setToText(self.icon)
                return
            traverseToText = not (evt.state & comn.SHIFT_MASK)
            ic, site = lexicalTraverse(self.icon, self.site, evt.keysym,
                traverseStmtComment=traverseToText)
            if evt.keysym == 'Right' and traverseToText:
                if _isTextIcBodySite(ic, site):
                    ic.setCursorPos(0)
                    self.setToText(ic)
                    return
                elif isinstance(ic.childAt(site), entryicon.EntryIcon):
                    ic.childAt(site).setCursorPos(0)
                    self.setToText(ic.childAt(site))
                    return
            cursorType = 'icon'
            pos = None
        else:
            cursorType, ic, site, pos = geometricTraverse(self.icon, self.site,
                evt.keysym, enterTextFields=not evt.state & comn.SHIFT_MASK)
        self.moveToIconSite(cursorType, ic, site, pos, evt)

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect, redraw=False)
            self.lastDrawRect = None
            self.blinkState = False

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

    def protoTextPosToEntryPos(self):
        """Translate the current text cursor position in a non-text-editing icon
        (self.protoTextPos) into a text position for an entry icon created by call to
        the icon's becomeEntryIcon method.  Normally, these are the same, but for some
        icons, such as attribute icons (and currently no others), additional characters
        are added.  Returns the adjusted cursor position.  Note that this assumes that
        the current cursor position is a text cursor position."""
        return protoTextToEntryPos(self.icon, self.textPartId, self.protoTextPos)

class Selection:

    def __init__(self, window):
        self.window = window
        self.selSet = set()
        # Text selections use a dictionary, rather than a set, because a text selection
        # cuts across icons and can involve some icon parts and not others.  textSel is
        # a dictionary that maps icons and empty series sites to a list of their involved
        # parts.  The part list is an integer whose bits represent parts as a one shifted
        # by the partId.  The starting and ending icon(s) are also explicitly recorded,
        # as they can contain partially-selected text.  The textSel dictionary keys are
        # of the same form as selSet icon selections: a mixture of icons and tuple pairs
        # denoting selected empty series sites.
        self.textSel = None
        self.leftIc = None
        self.rightIc = None
        self.leftPartId = None
        self.rightPartId = None
        self.leftPos = 0
        self.rightPos = -1
        self.anchorDirection = None

    def isText(self):
        """Return True if text (as opposed to entire icons) is selected.  A text
        selection consists of any number of contiguous, fully-selected, icon parts, and
        (potentially) partially selected start (self.leftIc, self.leftPardId) and end
        (self.rightIc, self.rightPartId) icon parts.  The selection can contain only a
        single, contiguous, selected range of parts."""
        return self.textSel is not None

    def isSelected(self, ic, onlyAsIcon=False, onlyAsText=False):
        """Return True if an icon (ic) is in the current selection (icon or text), False
        if not.  Empty series sites can also be tested by passing ic as a tuple (icon,
        siteName).  To return results for only for icon selections, set onlyAsIcon to
        True.  Likewise for text selections, set onlyAsText to restrict the result to
        text selections."""
        if self.textSel is None:
            return (not onlyAsText) and ic in self.selSet
        return (not onlyAsIcon) and ic in self.textSel

    def select(self, ic, select=True):
        """Add (select=True) or remove (select=False) an icon from the current (icon
        not text) selection.  Does not redraw or mark the icon as dirty.  Use
        .isSelected() to read the selection state of an icon.  ic can also specify an
        empty series site to select or unselect in the form of a tuple: (icon, siteName).
        """
        if select:
            self.selSet.add(ic)
        else:
            self.selSet.discard(ic)

    def clearSelection(self):
        """Clear the current selection (text or icon) with no redraw (caller must handle
        redraw)."""
        self.selSet.clear()
        self.textSel = None
        self.leftIc = None
        self.rightIc = None
        self.leftPartId = None
        self.rightPartId = None
        self.leftPos = None
        self.rightPos = None
        self.anchorDirection = None

    def unselectAll(self):
        """Clear the current selection and redraw to remove selection highlighting."""
        refreshRegion = comn.AccumRects()
        if self.isText():
            for ic in self.textSel.keys():
                if isinstance(ic, tuple):
                    refreshRegion.add(icon.rectOfEmptySite(ic[0], ic[1]))
                else:
                    refreshRegion.add(ic.rect)
        else:
            self.pruneSelectedIcons()
            if len(self.selSet) == 0:
                return
            for icOrSite in self.selSet:
                if isinstance(icOrSite, icon.Icon):
                    refreshRegion.add(icOrSite.rect)
                else:
                    refreshRegion.add(icOrSite[0].rect)
        self.clearSelection()
        if refreshRegion.get() is not None:
            self.window.refresh(refreshRegion.get(), redraw=True)

    def selectedIcons(self, excludeEmptySites=False):
        """Return a list of the icons in the window that are currently (icon) selected.
        Due to the odd method by which this is implemented (see below), performance will
        be enhanced somewhat if code that deletes all the icons from the selection, calls
        self.clearSelection() once it no longer needs to poll the selection.  By default,
        the list will also contain icon+site tuples for selected empty sites.  We allow
        these in selections to support the text-editor idiom of selecting ranges code to
        replace/delete.  Here, only empty *series* sites are supported, as they are the
        only type of site where removing the content usually implies removing the site
        itself (the comma clause).  Specifying excludeEmptySites will filter out these
        tuples and return a pure icon list.  Note that the absence of a corresponding
        tuple implies that a given empty site is specifically not selected, so while code
        that only cares about physical icons can ignore these entries, code that alters
        selections must include these whenever an empty series site should be included.
        """
        # Selection was initially a property of icons, but that caused performance issues
        # because finding the current selection required traversing all icons.  Now the
        # selection is held in a set, but to support existing code which does not expect
        # to see deleted icons in the selection, it must be cleaned per-use (which will
        # make performance significantly WORSE when more than half of the icons in the
        # window are selected).  It is intended that there will be a formal mechanism for
        # removing icons, after which this code can be removed.
        #
        # Eventually might be nice to support extracting '=' clauses with the same editor
        # idiom and similar mechanism used to handle empty series sites.
        self.window.sel.pruneSelectedIcons()
        if excludeEmptySites:
            return [ic for ic in self.selSet if isinstance(ic, icon.Icon)]
        return list(self.selSet)

    def pruneSelectedIcons(self):
        """For efficiency, much of the python-g code directly references the set which
        specifies which icons are in the current icon selection (self.selSet)  This set
        is allowed to contain deleted icons, which selectedIcons() will remove, but at
        the cost of scanning each icon in the set.  Functions that only need to check
        selection status, and those that want to control when the removal of deleted
        icons happens (to ensure that it only happens once) can call this function to do
        the removal, and thereafter know that self.selSet is free of deleted icons. """
        removeSet = set()
        if self.isText():
            for ic in self.textSel.keys():
                topParent = topLevelParentOfIcOrEmptySite(ic, inclStmtComment=True)
                if topParent is None or topParent not in self.window.topIcons:
                    print("Removing deleted icon from text selection: did something not"
                        " clear?")
                    removeSet.add(ic)
            for k in removeSet:
                self.textSel.pop(k, None)
        else:
            for icOrSite in self.selSet:
                ic = icOrSite if isinstance(icOrSite, icon.Icon) else icOrSite[0]
                topParent = ic.topLevelParent(inclStmtComment=True)
                if topParent is None or topParent not in self.window.topIcons:
                    print("Removing deleted icon from selection: did something not clear?")
                    removeSet.add(icOrSite)
            self.selSet -= removeSet

    def isTextSelected(self, ic, partId):
        """For text selections, return two boolean values: 1) whether the icon, ic, is
        part of the current text selection, and 2) whether the given icon part, partId,
        is within the main body (underlined part) of the selection."""
        if self.textSel is None or ic not in self.textSel:
            return False, False
        underlinedBits = self.textSel[ic]
        return True, bool(underlinedBits & (1 << partId))

    def selectSingleIconText(self, ic, partId, fromPos, toPos, anchorDir=None):
        """Select the text within a single icon part.  Caller must clear prior selection
        before calling and redraw after calling."""
        self.leftIc = ic
        self.leftPartId = partId
        self.leftPos = fromPos
        self.rightIc = ic
        self.rightPartId = partId
        self.rightPos = toPos
        self.textSel = {ic:1 << partId}
        self.anchorDirection = anchorDir

    def selectTextBetween(self, fromIc, fromPartId, fromPos, toIc, toPartId, toPos,
            preOrdered=False):
        """Create or replace the current selection to contain all text between two text
        positions.  If the order is known, set preOrdered=True to save cycles.  Returns
        False if the icons are not in the same sequence (or preOrdered was specified
        inappropriately).  Note that this does not set or clear the existing (icon)
        selection, nor does it set anchorDirection."""
        # If we don't yet know if fromSite and toSite are in the same sequence and
        # correct order, call stmtOrder to pre-scan the top-level icons. Note that
        # order-independence within a range that is confined to a single statement is
        # not handled, here, but in the lexicalTraverse call.
        toIcTopIcon = topLevelParentOfIcOrEmptySite(toIc, inclStmtComment=True)
        fromIcTopIcon = topLevelParentOfIcOrEmptySite(fromIc, inclStmtComment=True)
        if not preOrdered:
            order = expredit.stmtOrder(fromIcTopIcon, toIcTopIcon)
            if order is None:
                # fromIc and toIc are not part of the same sequence
                return False
            elif order == 2:
                # toIc comes first in sequence
                toIc, fromIc = fromIc, toIc
                toPartId, fromPartId = fromPartId, toPartId
                toPos, fromPos = fromPos, toPos
                toIcTopIcon, fromIcTopIcon = fromIcTopIcon, toIcTopIcon
        # Loop over top icons in the sequence between fromIcTopIcon and toIcTopIcon,
        # lexically scanning everything between fromIc, fromPartId to toIc, toPartId
        # to create the text selection
        iconsInRange = {}
        started = False
        for topIc in icon.traverseSeq(fromIcTopIcon, includeStartingIcon=True):
            if isinstance(topIc, icon.BlockEnd):
                # Include traversed block-end icons only if their corresponding owner is
                # selected
                if topIc.primary in iconsInRange:
                    iconsInRange[topIc] = 0
                continue
            # Traverse all statatements in the range, lexically, recording all icon parts
            # that appear between fromIc, fromPartId and toIc, toPartId inclusive.
            for ic, partId in expredit.lexicalTraverse(topIc, yieldNakedTuples=True,
                    yieldEmptySites=True):
                if (ic is toIc and partId == toPartId or isinstance(ic, tuple) and
                        ic == toIc) and not started:
                    # toIc may be before fromIc in the statement.  If so, reverse them
                    if fromIc == toIc and fromPartId == toPartId:
                        if fromPos > toPos:
                            toPos, fromPos = fromPos, toPos
                    else:
                        toIc, fromIc = fromIc, toIc
                        toPartId, fromPartId = fromPartId, toPartId
                        toPos, fromPos = fromPos, toPos
                if ic is fromIc and partId == fromPartId or isinstance(ic, tuple) and \
                        ic == fromIc:
                    started = True
                if started:
                    if isinstance(ic, listicons.TupleIcon) and ic.noParens:
                        # Include naked tuples in the returned set only if all of their
                        # arguments are included in the range
                        for elem in ic.argIcons():
                            if elem not in iconsInRange:
                                break
                        else:
                            iconsInRange[ic] = 0
                    else:
                        if isinstance(ic, tuple):
                            # For empty sites, lexicalTraverse returns partId of 0, but
                            # to indicate underline, we need a nonzero value.
                            partId = 1
                        if ic in iconsInRange:
                            iconsInRange[ic] |= 1 << partId
                        else:
                            iconsInRange[ic] = 1 << partId
                        if not isinstance(ic, tuple):
                            # We include the hierarchy under the icon to give us either
                            # a single hierarchy or a series, as well as a contiguous
                            # lexical range, allowing the result to be reparsed as a unit
                            for i in expredit.createHierSel(ic, inclStmtComment=False):
                                if i not in iconsInRange:
                                    iconsInRange[i] = 0
                if ic is toIc and partId == toPartId or isinstance(ic, tuple) and \
                        ic == toIc:
                    break
            if topIc is toIcTopIcon:
                self.leftIc = fromIc
                self.leftPartId = fromPartId
                self.leftPos = fromPos
                self.rightIc = toIc
                self.rightPartId = toPartId
                self.rightPos = toPos
                self.textSel = iconsInRange
                return True
        # If we escape the loop without finding toIc (which I think will only happen if
        # the function is incorrectly called with preOrdered=True), we have failed
        print("selectTextBetween failed to find end of range")
        return False

    def getSelectionText(self):
        """For a text selection, return 1) the text associated with the selection, and 2,
        3) the starting and ending character positions within that text of the underlined
        portion of the selection.  Also calculates whether the last few icons in the
        selection can be kept intact as pending arguments should the text be destined
        for an entry icon.  If not the 3rd and 4th returned values are set to None.  If
        so the 3rd argument is set to the text index where the pending arguments can
        start, and the 4th argument returns the icons that appear after the index."""
        # Note that this uses a potentially brittle hack to trim the selection text and
        # find the underlined range (the findSaveTextRanges call, below).  I hope that
        # save text generation will eventually have modes to annotate text with the icon
        # and part IDs (probably needed for search).
        if not self.isText():
            return None, None, None, None, None
        stmtOfLeftIc = topLevelParentOfIcOrEmptySite(self.leftIc)
        stmtOfRightIc = topLevelParentOfIcOrEmptySite(self.rightIc)
        if self.leftIc is self.rightIc and isinstance(self.leftIc, stringicon.StringIcon):
            # For a selection contained within a single string icon, the general code
            # can produce undesirable results, since the string may be split across
            # lines with intervening quote and line continuation characters (when the
            # user clearly wants text)
            prefix = self.leftIc.strType + self.leftIc.quote
            return prefix + self.leftIc.string + self.leftIc.quote, self.leftPos + \
                len(prefix), self.rightPos + len(prefix), None, None
        stmtTextList = []
        stmtCharOffset = 0
        underlineStartIdx = underlineEndIdx = pendingArgIdx = pendingArgIcons = None
        for stmt in icon.traverseSeq(stmtOfLeftIc):
            if isinstance(stmt, icon.BlockEnd):
                stmtTextList.append('')
                continue
            saveText = stmt.createSaveText(export=True)
            if hasattr(stmt, 'stmtComment') and stmt.stmtComment is not None:
                saveText.addComment(stmt.stmtComment.createSaveText(
                    export=True), isStmtComment=True)
            stmtText = saveText.wrapText(0, 1, export=True)
            if stmt is stmtOfLeftIc or stmt is stmtOfRightIc:
                # For left and right selection parts, trim the statement save text and
                # calculate the character offsets for the start and end of the underlined
                # portion of the selection (for all other statements, just blindly copy
                # the save text, as it is all selected)
                stmtStartSelIdx, stmtStartUnderlineIdx, stmtEndUnderlineIdx,\
                    stmtEndSelIdx, stmtPendingIdx, stmtPendingIcons = \
                    self.findStmtSaveTextRanges(stmtText, stmt)
                if stmtStartSelIdx is None:
                    print("getAnnotatedText: failed to extract selection text")
                    return None, None, None, None, None
                if stmt is stmtOfLeftIc:
                    stmtText = stmtText[stmtStartSelIdx:]
                    underlineStartIdx = stmtStartUnderlineIdx - stmtStartSelIdx
                if stmt is stmtOfRightIc:
                    underlineEndIdx = stmtEndUnderlineIdx + stmtCharOffset
                    if stmtPendingIdx is not None:
                        pendingArgIdx = stmtPendingIdx + stmtCharOffset
                        pendingArgIcons = stmtPendingIcons
                    if stmt is stmtOfLeftIc:
                        # Selection is confined to a single statement, adjust for the
                        # trimming already applied to left end of selection
                        stmtEndSelIdx -= stmtStartSelIdx
                        underlineEndIdx -= stmtStartSelIdx
                        if pendingArgIdx is not None:
                            pendingArgIdx -= stmtStartSelIdx
                    stmtText = stmtText[:stmtEndSelIdx]
            stmtTextList.append(stmtText)
            if stmt == stmtOfRightIc:
                break
            stmtCharOffset += len(stmtText) + 1
        else:
            print("getAnnotatedText failed to find end of selection")
        selectedText = '\n'.join(stmtTextList)
        print('getSelectionText:', selectedText[:underlineStartIdx] + '^' +
              selectedText[underlineStartIdx:underlineEndIdx] + '^' +
              selectedText[underlineEndIdx:], pendingArgIdx, pendingArgIcons)
        return selectedText, underlineStartIdx, underlineEndIdx, pendingArgIdx, \
            pendingArgIcons

    def findStmtSaveTextRanges(self, stmtText, stmt):
        """Compare lexical traversal of stmt with save text generated for the
        statement to correlate the icon parts.  This is a temporary solution until
        save text generation can tag the text with icon+part ids (slated to be added
        during implementation of search)."""
        # Tokenize the save text (our icon parts roughly match, and the tokenizer parses
        # larger structures like comments and strings)
        with io.BytesIO(stmtText.encode('utf-8')) as f:
            tokens = list(tokenize.tokenize(f.readline))
            if tokens[0].type == tokenize.ENCODING:
                tokenIdx = 1
            else:
                tokenIdx = 0
        # Lexically traverse the statement associating each icon part with tokens
        # generated from the save text
        startSelIdx = startUnderlineIdx = endSelIdx = endUnderlineIdx = pendingIdx = None
        pendingIcons = None
        for ic, partId in expredit.lexicalTraverse(stmt, yieldEmptySites=True):
            leftPrefixOffset = rightPrefixOffset = 0
            if isinstance(ic, tuple):
                # Empty sites: When processing icons, the main loop of this function
                # skips over whitespace and commas before looking for matching text.
                # When we're looking for an empty site, we need to pay attention to
                # commas and skip just the right number (0 for site _0 and 1 for all
                # others) of them, and label the following whitespace (for which
                # tokenize does not actually produce a token).
                _, siteIdx = iconsites.splitSeriesSiteId(ic[1])
                if siteIdx == 0:
                    # We're' already advanced to the next token
                    startIdx = 0 if tokenIdx == 0 else (tokens[tokenIdx-1].end[1])
                else:
                    # Advance to the token holding the series-site comma
                    while tokens[tokenIdx].type in (tokenize.NL, tokenize.INDENT,
                            tokenize.DEDENT):
                        tokenIdx += 1
                    if tokens[tokenIdx].string != ',':
                        print(f"getAnnotatedText: failed match because expected comma "
                            f"before empty site {ic[0].dumpName()}, {ic[1]}")
                        return None, None, None, None, None, None
                    startIdx = tokens[tokenIdx].end[1]
                    tokenIdx += 1
                # We duplicate the match==True processing, here and then recycle the loop
                # to keep the rest of the code free of the complications of having no
                # associated token and ic not being an icon.
                if ic in self.textSel:
                    if startSelIdx is None:
                        startSelIdx = startIdx
                    if ic == self.leftIc:
                        startUnderlineIdx = startIdx + self.leftPos
                    if ic == self.rightIc:
                        endUnderlineIdx = startIdx + self.rightPos
                else:
                    if startSelIdx is not None and endSelIdx is None:
                        endSelIdx = startIdx
                continue
            elif isinstance(ic, stringicon.StringIcon):
                partText = ic.strType + ic.quote + ic.string + ic.quote
                leftPrefixOffset = rightPrefixOffset = len(ic.quote)
            elif isinstance(ic, commenticon.CommentIcon):
                partText = '# ' + ic.string
                leftPrefixOffset = rightPrefixOffset = 2
            elif isinstance(ic, nameicons.AttrIcon):
                partText = '.' + ic.getTextSelMetrics(partId)[0]
                leftPrefixOffset = rightPrefixOffset = 1
            elif isinstance(ic, entryicon.EntryIcon):
                partText = ic.text
            else:
                partText = ic.getTextSelMetrics(partId)[0]
            if partText is None:
                print('skipping empty text (probably normal)', ic.dumpName(), partId)
                continue
            preSkipCharIdx = tokens[tokenIdx].start[1]
            while tokens[tokenIdx].type in (tokenize.NL, tokenize.COMMA, tokenize.INDENT,
                    tokenize.DEDENT) or tokens[tokenIdx].string == ',':
                # Skip whitespace and commas
                tokenIdx += 1
            if tokenIdx >= len(tokens):
                print("getAnnotatedText prematurely reached end of stmt text")
                break
            tok = tokens[tokenIdx]
            charIdx = tok.start[1]
            if tok.string == partText:
                match = True
            elif isinstance(ic, stringicon.StringIcon):
                # Collect all of the consecutive string segments from the icon-save text.
                # Concatenated strings will only appear in save text when they come from
                # a single icon, and will have the same quote style and string type as
                # the source icon, but will have newlines, continuation, and indent in
                # between them
                stringTokens = [tok]
                while True:
                    lookAheadIdx = 1
                    while tokens[tokenIdx + lookAheadIdx].type in (tokenize.NL,
                            tokenize.INDENT, tokenize.DEDENT):
                        tokenIdx += 1
                    if tokens[tokenIdx + lookAheadIdx].type != token.STRING:
                        break
                    tokenIdx += lookAheadIdx
                    tok = tokens[tokenIdx]
                    stringTokens.append(tok)
                stringContent = []
                strPrefix = ic.strType + ic.quote
                for strTok in stringTokens:
                    if strTok.string[:len(strPrefix)] != strPrefix or \
                            strTok.string[-len(ic.quote):] != ic.quote:
                        match = False
                        break
                    tokStr = strTok.string[len(strPrefix):-len(ic.quote)]
                    tokStr = tokStr.replace('\\\n', '')
                    stringContent.append(tokStr)
                else:
                    match = ''.join(stringContent) == ic.string
                if match:
                    icStrStart = 0
                    tokOff = len(strPrefix)
                    for i, strTok in enumerate(stringTokens):
                        if i != 0:
                            tokOff += strTok.start[1] + len(strPrefix)
                        icStrEnd = icStrStart + len(strTok.string) - len(strPrefix) - \
                            len(ic.quote)
                        if ic is self.leftIc and icStrStart <= self.leftPos < icStrEnd:
                            leftPrefixOffset = tokOff
                        if ic is self.rightIc and icStrStart <= self.rightPos < icStrEnd:
                            rightPrefixOffset = tokOff
                        icStrStart = icStrEnd
                        tokOff += len(ic.quote) + len(strTok.line[strTok.start[1] +
                            len(strTok.string):])
            elif isinstance(ic, commenticon.CommentIcon) and ic.attachedToStmt:
                # Multi-line stmt comments are encoded by save as: "# line-1\nline-2"
                # which reads back in the token as "#line-1\\nline-2"
                tokLines = tok.string[2:].split('\\n')
                iconLines = ic.string.split('\n')
                if tokLines == iconLines:
                    match = True
                    if ic is self.leftIc or ic is self.rightIc:
                        iconStrOff = 0
                        for i, line in enumerate(iconLines):
                            lineLen = len(line)
                            if ic is self.leftIc and iconStrOff <= self.leftPos <= \
                                    iconStrOff + lineLen:
                                leftPrefixOffset = i + 2
                            if ic is self.rightIc and iconStrOff <= self.rightPos <= \
                                    iconStrOff + lineLen:
                                rightPrefixOffset = i + 2
                            iconStrOff += lineLen + 1
                else:
                    match = False
            elif isinstance(ic, commenticon.CommentIcon):
                # Multi-line line-comments are encoded by save as multiple comment lines
                # split at the newline characters in ic.string.
                iconLineStart = 0
                tokOff = 2
                while tok.type == token.COMMENT:
                    tokStr = tok.string[2:]
                    if tokStr[-1:] == '\\':
                        tokStr = tokStr[:-1]
                        joinedLine = True
                    else:
                        joinedLine = False
                    iconLineEnd = iconLineStart + len(tokStr)
                    if ic.string[iconLineStart:iconLineEnd] != tokStr:
                        match = False
                        break
                    if ic is self.leftIc and iconLineStart <= self.leftPos <= iconLineEnd:
                        leftPrefixOffset = tokOff
                    if ic is self.rightIc and iconLineStart <= self.rightPos <= iconLineEnd:
                        rightPrefixOffset = tokOff
                    if iconLineEnd == len(ic.string):
                        match = True
                        break
                    tokenIdx += 1
                    while tokens[tokenIdx].type in (tokenize.NL, tokenize.INDENT,
                            tokenize.DEDENT):
                        tokenIdx += 1
                    tok = tokens[tokenIdx]
                    # Add the space before the next token and for the '# ' to the running
                    # offset between the icon string and the save string.  It's done here
                    # at the bottom of the loop to exclude the first comment line, whose
                    # leading space should not count toward the offset.
                    tokOff += tok.start[1] + 2 + (2 if joinedLine else 0)
                    # Skip newline character in icon (unless we wrote a continuation)
                    iconLineStart = iconLineEnd + (0 if joinedLine else 1)
                else:
                    match = False
            elif isinstance(ic, nameicons.AttrIcon) and tok.string == '.':
                # Attributes correspond to two tokens, an OP tok and a NAME
                charIdx = tok.start[1]
                tokenIdx += 1
                tok = tokens[tokenIdx]
                match = tok.string == partText[1:]
            elif isinstance(ic, commenticon.VerticalBlankIcon):
                # As a statement, the vertical blank parses to *nothing*
                match = tok.type == token.ENDMARKER
            elif isinstance(ic, entryicon.EntryIcon):
                # Entry icon text will be in the form of a quoted string.
                if ic.text == '':
                    continue  # Save text will have only spaces for empty entry icon body
                match = tok.type == token.STRING and \
                    ic.text == ast.literal_eval(tok.string)
            elif tok.string in multiTokenOperators and len(tokens) > tokenIdx and \
                    tokens[tokenIdx+1].string in multiTokenOperators[tok.string]:
                # Space-containing operators 'async x' not-in is-not consist of 2 tokens
                tokenIdx += 1
                match = True
            else:
                match = False
            if match:
                if ic in self.textSel:
                    if startSelIdx is None:
                        startSelIdx = charIdx
                    if ic is self.leftIc and partId == self.leftPartId:
                        startUnderlineIdx = charIdx + leftPrefixOffset + self.leftPos
                    if ic is self.rightIc and partId == self.rightPartId:
                        endUnderlineIdx = charIdx + rightPrefixOffset + self.rightPos
                    if endUnderlineIdx is not None:
                        if self.textSel[ic] == 0:
                            if partId == 1:
                                if pendingIdx is None:
                                    pendingIdx = charIdx
                                    pendingIcons = []
                                pendingIcons.append(ic)
                            elif ic not in pendingIcons:
                                # If we encounter part of an icon after the underline
                                # whose left part is not in pendingIcons, restart list
                                pendingIdx = None
                                pendingIcons = None
                        else:
                            pendingIdx = None
                            pendingIcons = None
                else:
                    if startSelIdx is not None and endSelIdx is None:
                        endSelIdx = preSkipCharIdx
                tokenIdx += 1
            else:
                # Text diverges from expected
                print("getAnnotatedText: stmt text diverges from selection at "
                    "character %d:" % charIdx)
                return None, None, None, None, None, None
        if startSelIdx is None:
            print("getAnnotatedText: did not find selection")
            return None, None, None, None, None, None
        if endUnderlineIdx is None:
            endUnderlineIdx = len(stmtText)
        if endSelIdx is None:
            endSelIdx = len(stmtText)
        return startSelIdx, startUnderlineIdx, endUnderlineIdx, endSelIdx, pendingIdx, \
            pendingIcons

def nextTextPosInStmt(ic, pos=None, partId=None, siteId=None, direction=None):
    """Return icon, partId, and cursorPosition for the first text-site (including
    proto-text) to the right of either the text position represented by (ic, pos, partId)
    or the site represented by (ic, siteId).  If neither pos nor siteId is specified,
    assumes that ic is a top-level statement and returns the first (lexical) icon and
    part of the statement. direction can be specified as 'Left' or 'Right' (direction
    from anchor site) to skip the initial site of non-editable icon parts such as end
    parens and inline-else.  Returns None for icon if the specified partId or site is at
    the right edge of the statement containing ic (note that this is different from
    nextTextPos(), which returns the passed position)."""
    startAtSite = None
    started = False
    if pos is not None:
        if isIconAndCanEditText(ic):
            minPos, maxPos = ic.textCursorRange()
            textLen = maxPos - minPos
            editable = True
        elif isinstance(ic, tuple):
            if pos == 0:
                return ic, 1, 1
            else:
                startAtSite = lexicalTraverse(ic[0], ic[1], 'Right',
                    traverseStmtComment=True)
                started = True
                textLen = 1
                editable = False
                ic = ic[0]
        else:
            text, font, _, _, _, _, _, editable = ic.getTextSelMetrics(partId)
            textLen = 1 if font is None else len(text)
        if pos < textLen and (editable or direction == 'Right'):
            return ic, partId, pos + 1
    elif siteId is not None:
        startAtSite = (ic, siteId)
        started = True
    else:  # No pos or startId, ic is top level (stmt) icon
        started = True
    for travIc, travPart in expredit.lexicalTraverse(
            ic.topLevelParent(inclStmtComment=True), fromSite=startAtSite):
        if not started:
            if travIc is ic and travPart == partId:
                started = True
            continue
        return travIc, travPart, 0
    return None, None, None

def nextTextPos(ic, pos=None, partId=None, siteId=None, direction=None):
    """Return icon, partId, and cursorPosition for the first text-site (including
    proto-text) to the right of either the text position represented by (ic, pos, partId)
    or the site represented by (ic, siteId).  direction can be specified as 'Left' or
    'Right' (direction from anchor site) to skip the initial site of non-editable icon
    parts such as end parens and inline-else.  If the given text position is the last
    text position in a statement, returns the first text position in the next statement,
    or the original text position (ic, pos, partId) if the given position is at the right
    edge of the last statement of the sequence containing ic (note that this is different
    from nextTextPosInStmt which returns None at the start of a statement).  Callers who
    pass a siteId also need to note that the returned (ic, part, pos) will not be a valid
    text position if there is no subsequent text site, and need to check that pos is not
    None before using this result as one."""
    while isinstance(ic, (icon.BlockEnd, commenticon.VerticalBlankIcon)):
        newIc = ic.nextInSeq()
        if newIc is None:
            return prevTextPos(ic, siteId='seqIn')
        ic = newIc
        pos = None
        partId = None
        siteId = None
    nextIc, nextPart, nextPos = nextTextPosInStmt(ic, pos, partId, siteId, direction)
    if nextIc is not None:
        return nextIc, nextPart, nextPos
    nextStmt = ic.topLevelParent(inclStmtComment=True).childAt('seqOut')
    while isinstance(nextStmt, (icon.BlockEnd, commenticon.VerticalBlankIcon)):
        nextStmt = nextStmt.nextInSeq()
    if nextStmt is None:
        return ic, partId, pos
    return nextTextPosInStmt(nextStmt, direction=direction)

def prevTextPosInStmt(ic, pos=None, partId=None, siteId=None, direction=None):
    """Return icon, partId, and cursorPosition for the first text-site (including
    proto-text) to the left of either the text position represented by (ic, pos, partId)
    or the icon site represented by (ic, siteId).  direction can be specified as 'Left'
    or 'Right' (direction from anchor site) to skip the initial site of non-editable icon
    parts such as end parens and inline-else.  Returns None for icon if the specified
    partId or site is at the left edge of the statement containing ic (note that this is
    different from prevTextPos(), which returns the starting position)."""
    if pos is not None:
        stopAtSite = False
        if isIconAndCanEditText(ic):
            editable = True
            partId = 1
        elif isinstance(ic, tuple):
            editable = False
            if pos == 1:
                return ic, 1, 0
            stopAtSite = True
            partId = None
            ic, siteId = ic
        else:
            _, _, _, _, _, _, _, editable = ic.getTextSelMetrics(partId)
        if pos > 0 and (editable or direction == 'Left'):
            return ic, partId, pos - 1
    else:
        stopAtSite = True
    lastIc = lastPartId = None
    for travIc, travPart in expredit.lexicalTraverse(ic.topLevelParent(
            inclStmtComment=True), yieldAllSites=stopAtSite, yieldEmptySites=True):
        if stopAtSite and isinstance(travIc, tuple) and isinstance(travIc[0], str) and \
                travIc[0] == siteId and travIc[1] == ic:
            break
        elif travIc is ic and travPart == partId:
            break
        elif not isinstance(travIc, tuple) or isinstance(travIc[0], icon.Icon):
            lastIc = travIc
            lastPartId = travPart
    if lastIc is None:
        # Stop condition was not found, assume we're at the start of the statement
        return None, None, None
    if isIconAndCanEditText(lastIc):
        return lastIc, 1, lastIc.textCursorRange(1)[1]
    elif isinstance(lastIc, tuple):
        # lastIc is an empty site: return the rightmost text position
        return lastIc, 1, 1
    else:
        text, font, _, _, _, _, _, editable = lastIc.getTextSelMetrics(lastPartId)
        textLen = 1 if font is None else len(text)
        if editable or direction == 'Left':
            return lastIc, lastPartId, textLen
        else:
            return lastIc, lastPartId, textLen - 1

def prevTextPos(ic, pos=None, partId=None, siteId=None, direction=None):
    """Return icon, partId, and cursorPosition for the first text-site (including
    proto-text) to the left of either the text position represented by (ic, pos, partId)
    or the site represented by (ic, siteId).  direction can be specified as 'Left' or
    'Right' (direction from anchor site) to skip the initial site of non-editable icon
    parts such as end parens and inline-else.  If the given text position is the first
    text position in a statement, returns the last text position in the previous
    statement or the original text position (ic, pos, partId) if the given position is at
    the left edge of the first statement of the sequence containing ic (note that this is
    different from prevTextPosInStmt which returns None at the start of a statement).
    Callers who pass a siteId also need to note that the returned (ic, part, pos) will
    not be a valid text position if there is no previous text site, and need to check
    that pos is not None before using this result as one."""
    while isinstance(ic, (icon.BlockEnd, commenticon.VerticalBlankIcon)):
        newIc = ic.prevInSeq()
        if newIc is None:
            return nextTextPos(ic, siteId='seqIn')
        ic = newIc
        pos = None
        partId = None
        siteId = None
    prevIc, prevPart, prevPos = prevTextPosInStmt(ic, pos, partId, siteId, direction)
    if prevIc is not None:
        return prevIc, prevPart, prevPos
    prevStmt = topLevelParentOfIcOrEmptySite(ic).childAt('seqIn')
    while isinstance(prevStmt, (icon.BlockEnd, commenticon.VerticalBlankIcon)):
        prevStmt = prevStmt.prevInSeq()
    if prevStmt is None:
        return ic, partId, pos
    if hasattr(prevStmt, 'stmtComment'):
        return prevStmt.stmtComment, 1, prevStmt.stmtComment.textCursorRange()[1]
    rightmostIc, rightmostSite = icon.rightmostSite(prevStmt)
    prevIc, prevPart, prevPos = prevTextPosInStmt(rightmostIc, siteId=rightmostSite,
        direction=direction)
    if prevIc is None:
        return ic, partId, pos
    return prevIc, prevPart, prevPos

def lexicalTraverse(fromIcon, fromSite, direction, traverseStmtComment=False):
    """Return the cursor position (icon and siteId) to the left or right according
    to the "text-flow".  If travStmtComment is specified, will return the statement
    comment following the rightmost cursor position at the end of a statement, with
    a site of None (since statement comments are not attached to a site)."""
    ic, site = _lexicalTraverse(fromIcon, fromSite, direction, traverseStmtComment)
    while site is not None and ic.isCursorSkipSite(site):
        # lexical traversal includes comprehension sites, and we want the icon
        # that is on the comprehension site, so go around again.
        ic, site = _lexicalTraverse(ic, site, direction, traverseStmtComment)
    return ic, site

def _lexicalTraverse(fromIcon, fromSite, direction, travStmtComment):
    """Guts of lexicalTraverse, but will visit cursorSkipSites."""
    fromSiteType = fromIcon.typeOf(fromSite)
    if direction == 'Left':
        if fromSiteType in iconsites.parentSiteTypes:
            # Cursor is on an output site.  In the unlikely case that it is attached to
            # something, make a recursive call with the proper cursor site (input), but
            # otherwise, traverse to the seqIn site.
            attachedIc = fromIcon.childAt(fromSite)
            if attachedIc is None:
                return fromIcon, 'seqIn'
            attachedSite = attachedIc.siteOf(fromIcon)
            return _lexicalTraverse(attachedIc, attachedSite, direction, travStmtComment)
        elif fromSite == 'seqOut':
            if isinstance(fromIcon, icon.BlockEnd):
                return fromIcon, "seqIn"
            if fromIcon.sites.lastCursorSite() is None:
                return fromIcon, "seqIn"
            return icon.rightmostSite(fromIcon)
        elif fromSite == 'seqIn':
            prevStmt = fromIcon.prevInSeq(includeModuleAnchor=True)
            if prevStmt is None:
                return fromIcon, fromSite
            if isinstance(prevStmt, icon.BlockEnd):
                return prevStmt, "seqIn"
            if prevStmt.sites.lastCursorSite() is None:
                return prevStmt, "seqIn"
            return icon.rightmostSite(prevStmt)
        # Cursor is on an input site of some sort (input, attrIn, cprhIn)
        prevSite = fromIcon.sites.prevCursorSite(fromSite)
        if prevSite is None:
            highestIc = iconsites.highestCoincidentIcon(fromIcon)
            parent = highestIc.parent()
            if parent is None:
                if highestIc.hasCoincidentSite():
                    toIc, toSite = iconsites.lowestCoincidentSite(highestIc,
                        highestIc.hasCoincidentSite())
                    if toIc == fromIcon and toSite == fromSite:
                        return highestIc, 'seqIn'
                    return toIc, toSite
                return highestIc, topSite(highestIc, seqDown=False)
            parentSite = parent.siteOf(highestIc)
            if fromIcon.hasCoincidentSite():
                return _lexicalTraverse(parent, parentSite, direction, travStmtComment)
            return iconsites.lowestCoincidentSite(parent, parentSite)
        iconAtPrevSite = fromIcon.childAt(prevSite)
        if iconAtPrevSite is None:
            return fromIcon, prevSite
        return icon.rightmostSite(iconAtPrevSite)
    else:  # 'Right'
        if fromSiteType in iconsites.parentSiteTypes or fromSiteType == 'seqIn':
            nextSite = fromIcon.sites.firstCursorSite()
            if nextSite is None:
                return fromIcon, topSite(fromIcon, seqDown=True)
            if fromSite == 'output' and nextSite == fromIcon.hasCoincidentSite():
                return _lexicalTraverse(fromIcon, nextSite, direction, travStmtComment)
            return fromIcon, nextSite
        if fromSite == 'seqOut':
            nextStmt = fromIcon.nextInSeq()
            if nextStmt is None:
                return fromIcon, fromSite
            nextSite = nextStmt.sites.firstCursorSite()
            if nextSite is None:
                return nextStmt, 'seqOut'
            return nextStmt, nextSite
        # Start from the lowest coincident site at the cursor
        ic, site = iconsites.lowestCoincidentSite(fromIcon, fromSite)
        childIc = ic.childAt(site)
        if childIc is not None:
            # There is an icon attached to it that can accept a cursor, go there
            firstChildSite = childIc.sites.firstCursorSite()
            if firstChildSite is not None:
                return childIc, firstChildSite
        # There is no icon attached to the site that can accept a cursor.  Iterate up
        # the hierarchy to find an icon with a site to take one.  If none is found,
        # attach to the seqOut or output site of the top icon
        nextSite = ic.sites.nextCursorSite(site)
        nextIcon = ic
        while nextSite is None or nextSite == nextIcon.hasCoincidentSite():
            parent = nextIcon.parent()
            if parent is None:
                if travStmtComment and hasattr(nextIcon, 'stmtComment'):
                    return nextIcon.stmtComment, None
                else:
                    return nextIcon, topSite(nextIcon, seqDown=True)
            parentSite = parent.siteOf(nextIcon)
            nextSite = parent.sites.nextCursorSite(parentSite)
            nextIcon = parent
        return nextIcon, nextSite

def geometricTraverse(fromIcon, fromSite, direction, enterTextFields=True,
        allowEscapeToWindow=False):
    """Return the next (icon) cursor position (icon and siteId) in a given direction
    (physically, not lexically) from the given (icon site) position (fromIcon, fromSite).
    """
    # Special cases for traversing block end icons up and down, since their sites
    # are not physically up and down from each other, but need to be visited as such
    if isinstance(fromIcon, icon.BlockEnd) and fromSite == 'seqIn' and \
            direction == 'Down':
        return 'icon', fromIcon, 'seqOut', None
    if isinstance(fromIcon.nextInSeq(), icon.BlockEnd) and fromSite == 'seqOut' and \
            direction == 'Down':
        return 'icon', fromIcon.nextInSeq(), 'seqOut', None
    if isinstance(fromIcon, icon.BlockEnd) and fromSite == 'seqOut' and \
            direction == 'Up':
        return 'icon', fromIcon, 'seqIn', None
    if isinstance(fromIcon.prevInSeq(), icon.BlockEnd) and fromSite == 'seqIn' and \
            direction == 'Up':
        return 'icon', fromIcon.prevInSeq(includeModuleAnchor=True), 'seqIn', None
    # Build a list of possible destination cursor positions, normalizing attribute
    # site positions to the center of the cursor (in/out site position), and sequence
    # sites to be far enough left to find output and prefix-insert sites.
    cursorX, cursorY = fromIcon.posOfSite(fromSite)
    if fromIcon.typeOf(fromSite) == "attrIn":
        cursorY -= icon.ATTR_SITE_OFFSET  # Normalize to input/output site y
    if fromSite in ('seqIn', 'seqOut'):
        cursorX -= icon.SEQ_SITE_OFFSET
    cursorType, ic, site, pos, _ = geometricTraverseFromPos(cursorX, cursorY, direction,
        fromIcon.window, limitAdjacentStmt=fromIcon, editableTextFields=enterTextFields)
    if not allowEscapeToWindow and cursorType == 'window':
        return 'icon', fromIcon, fromSite, None
    return cursorType, ic, site, pos

def geometricTraverseFromPos(cursorX, cursorY, direction, window, limitAdjacentStmt=None,
        limitDist=(HORIZ_ARROW_MAX_DIST, VERT_ARROW_MAX_DIST), editableTextFields=True,
        onlyTextFields=False):
    """Find the nearest cursor position in the given direction, starting from the the
    given x, y coordinates (cursorX, cursorY).  The traversal can be limited to adjacent
    statements (limitAdjacentStmt=top-stmt-icon), and by physical distance (limitDist=
    (xDist, yDist)).  By default it will traverse to icon-cursor sites and text sites
    of icons with text-editing capabilities, but not to proto-text sites.  It can be
    restricted to icon-cursor sites (editableTextFields=False), or to text-cursor sites
    (including proto-text cursor sites) by setting onlyTextFields to True."""
    searchRect = (cursorX-limitDist[0], cursorY-limitDist[1],
        cursorX+limitDist[0], cursorY+limitDist[1])
    if limitAdjacentStmt is not None:
        cursorTopIcon = limitAdjacentStmt.topLevelParent()
        cursorPrevIcon = cursorTopIcon.prevInSeq(includeModuleAnchor=True)
        cursorNextIcon = cursorTopIcon.nextInSeq()
        limitToStmts = [cursorTopIcon]
        if hasattr(cursorTopIcon, 'stmtComment'):
            limitToStmts.append(cursorTopIcon.stmtComment)
        if cursorPrevIcon:
            prevTopIcon = cursorPrevIcon.topLevelParent()
            limitToStmts.append(prevTopIcon)
            if hasattr(prevTopIcon, 'stmtComment'):
                limitToStmts.append(prevTopIcon.stmtComment)
        if cursorNextIcon is not None:
            nextTopIcon = cursorNextIcon.topLevelParent()
            limitToStmts.append(nextTopIcon)
            if hasattr(nextTopIcon, 'stmtComment'):
                limitToStmts.append(nextTopIcon.stmtComment)
        if onlyTextFields:
            # BlockEnd icons have no text sites and need to be skipped
            while isinstance(cursorPrevIcon, icon.BlockEnd):
                cursorPrevIcon = cursorPrevIcon.prevInSeq()
                if cursorPrevIcon is not None:
                    limitToStmts.append(cursorPrevIcon)
            while isinstance(cursorNextIcon, icon.BlockEnd):
                cursorNextIcon = cursorNextIcon.nextInSeq()
                if cursorNextIcon is not None:
                    limitToStmts.append(cursorNextIcon)
    cursorSites = []
    for winIcon in window.findIconsInRegion(searchRect, inclModSeqIcon=True):
        if limitAdjacentStmt is not None:
            topIcon = winIcon.topLevelParent()
            if topIcon not in limitToStmts:
                continue  # Limit statement jumps to a single statement
        if not onlyTextFields:
            snapLists = winIcon.snapLists(forCursor=True)
            hasOutSite = len(snapLists.get("output", [])) > 0
            for ic, (x, y), name in snapLists.get('input', []):
                cursorSites.append((x, y, 'icon', ic, name, None, None))
            for ic, (x, y), name in snapLists.get('seqIn', []):
                if direction in ('Up', 'Down'):
                    cursorSites.append((x - icon.SEQ_SITE_OFFSET, y, 'icon', ic, name,
                        None, None))
            for ic, (x, y), name in snapLists.get('seqOut', []):
                if  direction in ('Up', 'Down') or not hasOutSite:
                    cursorSites.append((x - icon.SEQ_SITE_OFFSET, y, 'icon', ic, name,
                        None, None))
            for ic, (x, y), name in snapLists.get("attrIn", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, 'icon', ic, name,
                    None, None))
            if winIcon.parent() is None:
                outSites = snapLists.get("output", [])
                if len(outSites) > 0:
                    cursorSites.append((*outSites[0][1], 'icon', winIcon, outSites[0][2],
                        None, None))
        if editableTextFields or onlyTextFields:
            if winIcon.canEditText:
                # Editable text fields
                cursorPos, (x, y) = winIcon.nearestCursorPos(cursorX, cursorY)
                cursorSites.append((x, y, 'text', winIcon, None, cursorPos, 1))
            elif onlyTextFields:
                if isinstance(winIcon, icon.BlockEnd):
                    continue
                # Proto-text fields for all icons
                for partId in winIcon.activePartIds():
                    cursorPos, pos = winIcon.nearestTextCursorPos(partId, cursorX,
                        cursorY)
                    if pos is not None:
                        cursorSites.append((*pos, 'text', winIcon, None, cursorPos,
                            partId))
                # Empty series sites get proto-text sites (regardless of highlighting),
                # because they allow users to selectively include the commas that
                # separate them within a text selection.  The rightmost (icon) site of
                # the series, however, gets none as it has no comma to represent.
                for siteSeries in winIcon.sites.childSites(expandSeries=False):
                    if isinstance(siteSeries, iconsites.IconSiteSeries):
                        for i, site in enumerate(siteSeries):
                            if site.att is not None or i - 1 >= len(siteSeries):
                                continue
                            cursorIc = (winIcon, site.name)
                            x, y = icon.emptySiteTextCursorPos(cursorIc, 0)
                            cursorSites.append((x, y, 'text', cursorIc, None, 0, 1))
                            x, y = icon.emptySiteTextCursorPos(cursorIc, 1)
                            cursorSites.append((x, y, 'text', cursorIc, None, 1, 1))
    # Rank the destination positions by nearness to the current cursor position
    # in the cursor movement direction, and cull those in the wrong direction
    choices = []
    for x, y, cursorType, ic, site, pos, partId in cursorSites:
        if direction == "Left":
            dist = cursorX - x
        elif direction == "Right":
            dist = x - cursorX
        elif direction == "Up":
            dist = cursorY - y
        elif direction == "Down":
            dist = y - cursorY
        if dist > 0:
            choices.append((dist, x, y, cursorType, ic, site, pos, partId))
    if len(choices) == 0:
        return "window", None, None, _windowCursorIncr(cursorX, cursorY, direction), None
    choices.sort(key=itemgetter(0))
    if direction in ("Left", "Right"):
        # For horizontal movement, just use a simple vertical threshold to decide
        # if the movement is appropriate
        for xDist, x, y, cursorType, ic, site, pos, partId in choices:
            if xDist > VERT_ARROW_X_JUMP_MIN:
                if abs(y - cursorY) < HORIZ_ARROW_Y_JUMP_MAX:
                    return cursorType, ic, site, pos, partId
    else:  # Up, Down
        # For vertical movement, do a second round of ranking.  This time add y
        # distance to weighted X distance (ranking x jumps as further away)
        bestRank = None
        for yDist, x, y, cursorType, ic, site, pos, partId in choices:
            if yDist > VERT_ARROW_Y_JUMP_MIN or isinstance(ic, icon.BlockEnd):
                rank = yDist + VERT_ARROW_X_WEIGHT*abs(x-cursorX)
                if bestRank is None or rank < bestRank[0]:
                    bestRank = (rank, cursorType, ic, site, pos, partId)
        if bestRank is None:
            return "window", None, None, _windowCursorIncr(cursorX, cursorY, direction), \
                None
        rank, cursorType, ic, site, pos, partId = bestRank
        if site == 'seqIn' and direction == "Up":
            # Typing at a seqIn site is the same as typing at the connected seqOut
            # site, so save the user a keypress by going to the seqOut site above
            prevIcon = ic.prevInSeq(includeModuleAnchor=True)
            if prevIcon:
                ic = prevIcon
                site = 'seqOut'
        return cursorType, ic, site, pos, partId
    return "window", None, None, _windowCursorIncr(cursorX, cursorY, direction), None

def protoTextToEntryPos(ic, partId, pos):
    """Translate the given text cursor position in a non-text-editing icon into a text
    position for an entry icon created by call to the icon's becomeEntryIcon method.
    Normally, these are the same, but for some icons, such as attribute icons (and
    currently no others), additional characters are added.  Returns the adjusted cursor
    position."""
    if isinstance(ic, nameicons.AttrIcon):
        return pos + 1
    return pos

def isIconAndCanEditText(icOrSite):
    if isinstance(icOrSite, tuple):
        return False
    return icOrSite.canEditText

def topLevelParentOfIcOrEmptySite(icOrSite, inclStmtComment=False):
    if isinstance(icOrSite, tuple):
        return icOrSite[0].topLevelParent(inclStmtComment=inclStmtComment)
    return icOrSite.topLevelParent(inclStmtComment=inclStmtComment)

def topSite(ic, seqDown=True):
    """Return the attachment site (and therefore leftmost cursor site) for an icon at
    the top of the hierarchy."""
    if seqDown and ic.hasSite('seqOut'):
        return 'seqOut'
    elif not seqDown and ic.hasSite('output'):
        return 'output'
    elif not seqDown and ic.hasSite('seqIn'):
        return 'seqIn'
    else:
        parentSites = ic.parentSites()
        if parentSites is not None:
            return parentSites[0]
    return None

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 192 or 219 <= evt.keycode <= 222:
        return chr(evt.keysym_num)
    return None

def beep():
    # Another platform dependent bit.  tkinter has a .bell() method, but it generates
    # an elaborate sound that's supposed to alert the user of a dialog popping up, which
    # is not appropriate for the tiny nudge for your keystroke being rejected.
    winsound.Beep(1500, 120)

def _isTextIcBodySite(ic, siteId):
    """Return True if ic is an entry icon and siteId is the site adjacent to the icon
    body.  This is a temporary placeholder for a more general routine that will do this
    for all icons that can host text editing (as opposed to interchanging with an entry
    icon to do so).  Also accepts the non-standard return from lexicalTraverse with
    traverseStmtComment option set, of a statement comment and siteId of None."""
    if  ic.__class__.__name__ in ('EntryIcon', 'StringIcon'):
        return siteId == ic.sites.firstCursorSite()
    if ic.__class__.__name__ in ('CommentIcon'):
        return siteId in ('seqOut', None)

def _windowCursorIncr(x, y, direction):
    directions = {"Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0)}
    xOff, yOff = directions[direction]
    x += xOff * WINDOW_CURSOR_INCREMENT
    y += yOff * WINDOW_CURSOR_INCREMENT
    return x, y

topLevelStmts = {'async def': blockicons.DefIcon, 'def': blockicons.DefIcon,
    'class': blockicons.ClassDefIcon, 'break': nameicons.BreakIcon,
    'return': nameicons.ReturnIcon, 'continue': nameicons.ContinueIcon,
    'yield': nameicons.YieldIcon, 'del': nameicons.DelIcon,
    'elif': blockicons.ElifIcon,
    'else': blockicons.ElseIcon, 'except': blockicons.ExceptIcon,
    'finally': blockicons.FinallyIcon, 'async for': blockicons.ForIcon,
    'for': blockicons.ForIcon, 'from': nameicons.ImportFromIcon,
    'assert': nameicons.AssertIcon,
    'global': nameicons.GlobalIcon,
    'if': blockicons.IfIcon, 'import': nameicons.ImportIcon,
    'nonlocal': nameicons.NonlocalIcon, 'pass': nameicons.PassIcon,
    'raise': nameicons.RaiseIcon, 'try': blockicons.TryIcon,
    'async while': blockicons.WhileIcon, 'while': blockicons.WhileIcon,
    'async with': blockicons.WithIcon, 'with': blockicons.WithIcon}

stmtIcons = {v for v in topLevelStmts.values()}