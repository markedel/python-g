# Copyright Mark Edel  All rights reserved
# Icon window cursor, and some support code for icon backspace functionality (in here,
# rather than icon.py, because it needs to know about many icon types, and icon.py, being
# the base class for icons, will tie the import system in knots if it tries to import its
# own subclasses).
import winsound
from PIL import Image
from operator import itemgetter
import comn
import iconsites
import icon
import opicons
import blockicons
import nameicons
import listicons
import subscripticon
import parenicon
import python_g
import entryicon

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

textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

class Cursor:
    def __init__(self, window, cursorType):
        self.window = window
        self.type = cursorType
        self.pos = (0, 0)
        self.icon = None
        self.site = None
        self.siteType = None
        self.lastDrawRect = None
        self.blinkState = False
        self.anchorIc = None
        self.anchorSite = None
        self.anchorLine = None
        self.lastSelIc = None
        self.lastSelSite = None

    def setToWindowPos(self, pos, eraseOld=True, drawNew=True, placeEntryText=True):
        """Place the cursor at an arbitrary location on the window background.  Be
        aware that this can cause rearrangement of icons by virtue of taking focus from
        an entry icon, which will then try to place its text content and pending
        arguments.  You must therefore either call this where rearrangement is safe,
        or suppress this behavior by setting placeEntryText=False.  Even if
        placeEntryText is set to False, it is still necessary to check for dirty icon
        layouts after calling, as this is the mechanism by which icons that draw
        additional focus graphics can redraw them."""
        if self.type == "text":
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "window"
        self.pos = pos
        self.window.updateTypeoverStates()
        self.blinkState = True
        if drawNew:
            self.draw()

    def setToIconSite(self, ic, siteIdOrSeriesName, seriesIndex=None, eraseOld=True,
            drawNew=True, placeEntryText=True):
        """Place the cursor on an icon site.  Be aware that this can cause
        rearrangement of icons by virtue of taking focus from an entry icon, which will
        then try to place its text content and pending arguments.  You must therefore
        either call this where rearrangement is safe, or suppress this behavior by
        setting placeEntryText=False.  Even if placeEntryText is set to False, it is
        still necessary to check for dirty icon layouts after calling, as this is the
        mechanism by which icons that draw additional focus graphics can redraw them."""
        if self.type == "text":
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
        self.blinkState = True
        if drawNew:
            self.draw()

    def setToText(self, ic, eraseOld=True, drawNew=True, placeEntryText=True):
        """Place the cursor within a text-edit-capable icon (ic), such as an entry
        icon, text icon or comment icon.  Note that the cursor position within the text
        is not held by the cursor object, but by ic.  Also be aware that this can cause
        rearrangement of icons by virtue of taking focus from an entry icon, which will
        then try to place its text content and pending arguments.  You must therefore
        either call this where rearrangement is safe, or suppress this behavior by
        setting placeEntryText=False.  Even if placeEntryText is set to False, it is
        still necessary to check for dirty icon layouts after calling, as this is the
        mechanism by which icons that draw additional focus graphics can redraw them."""
        if self.type == "text" and self.icon != ic:
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "text"
        self.icon = ic
        self.window.updateTypeoverStates()
        self.blinkState = True
        ic.focusIn()
        if drawNew:
            self.draw()

    def setToTypeover(self, ic, eraseOld=True, drawNew=True):
        """Place the cursor into a typeover-icon.  Note that you must also call the
        icon's setTypeover() function to actually set the typeover index (this function
        directs keyboard focus and controls cursor drawing)"""
        if self.type is not None and eraseOld:
            self.erase()
        self.type = "typeover"
        self.icon = ic
        self.window.updateTypeoverStates()
        self.blinkState = True
        if drawNew:
            self.draw()

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

    def moveToIconSite(self, ic, site, evt):
        """Place the cursor at an icon site, paying attention to keyboard modifiers"""
        shiftPressed = evt.state & python_g.SHIFT_MASK
        if shiftPressed:
            self.selectToCursor(ic, site, evt.keysym)
        else:
            self.setToIconSite(ic, site)

    def selectToCursor(self, ic, site, direction):
        """Modify selection based on cursor movement (presumably with Shift key held)"""
        selectedIcons = set(self.window.selectedIcons())
        redrawRect = comn.AccumRects()
        if len(selectedIcons) == 0 and self.type == "icon":
            # This is a new cursor-based selection
            self.anchorIc = self.icon
            self.anchorSite = self.site
        elif self.anchorIc is not None or self.anchorLine is not None:
            # There is a current recorded selection, but verify that it is valid by
            # matching it with the current actual selection
            lastSelIcons = set(self._iconsBetween(self.lastSelIc, self.lastSelSite))
            diffIcons = selectedIcons.difference(lastSelIcons)
            if len({i for i in diffIcons if not isinstance(i, icon.BlockEnd)}):
                self.anchorIc = None
                self.anchorLine = None
        if self.anchorIc is None and self.anchorLine is None:
            # The current selection is not valid, assume it was made via mouse.  Choose
            # an anchor line as the farthest side of the selection rectangle from the
            # cursor using the direction of arrow motion to choose horiz/vert
            selectedRect = comn.AccumRects()
            for i in selectedIcons:
                selectedRect.add(i.selectionRect())
            left, top, right, bottom = selectedRect.get()
            left += 3    # Inset rectangle to avoid overlaps and protruding sites
            right -= 3
            top += 1
            bottom -= 1
            siteX, siteY = ic.posOfSite(site)
            if direction in ("Left", "Right"):
                anchorX = right if abs(siteX - left) <= abs(siteX - right) else left
                self.anchorLine = (anchorX, top, anchorX, bottom)
            else:
                anchorY = bottom if abs(siteY - top) <= abs(siteY - bottom) else top
                self.anchorLine = (left, anchorY, right, anchorY)
        select = set(self._iconsBetween(ic, site))
        erase = selectedIcons.difference(select)
        select = select.difference(selectedIcons)
        for i in erase:
            redrawRect.add(i.hierRect())
            i.select(False)
        for i in select:
            redrawRect.add(i.hierRect())
            i.select()
        if redrawRect.get() is not None:
            self.window.refresh(redrawRect.get(), redraw=True, clear=False)
        self.setToIconSite(ic, site)
        self.lastSelIc = ic
        self.lastSelSite = site

    def _iconsBetween(self, ic, site):
        """Find the icons that should be selected by shift-select between the current
        anchor (self.anchorIc and Pos, or self.anchorLine) and cursor at ic, site."""
        siteX, siteY = ic.posOfSite(site)
        siteType = ic.typeOf(site)
        if siteType in ("attrIn", "attrOut"):
            siteY -= icon.ATTR_SITE_OFFSET
        elif siteType in ("seqIn", "seqOut"):
            seqInX, seqInY = ic.posOfSite("seqIn")
            seqOutX, seqOutY = ic.posOfSite("seqOut")
            siteY = (seqInY + seqOutY) // 2
        if self.anchorIc is not None:
            anchorX, anchorY = self.anchorIc.posOfSite(self.anchorSite)
            anchorSiteType = self.anchorIc.typeOf(self.anchorSite)
            if anchorSiteType in ("attrIn", "attrOut"):
                anchorY -= icon.ATTR_SITE_OFFSET
            elif anchorSiteType in ("seqIn", "seqOut"):
                seqInX, seqInY = self.anchorIc.posOfSite("seqIn")
                seqOutX, seqOutY = self.anchorIc.posOfSite("seqOut")
                anchorY = (seqInY + seqOutY) // 2
            if anchorX < siteX:
                anchorX += 4  # Avoid overlapped icons and sites
                siteX -= 3
            elif siteX < anchorX:
                siteX += 4
                anchorX -= 3
            selectRect = comn.AccumRects((anchorX, anchorY - 3, anchorX, anchorY + 3))
            selectRect.add((siteX, siteY - 3, siteX, siteY + 3))
        else:
            if self.anchorLine[0] == self.anchorLine[2]:
                anchorX = self.anchorLine[0]
                if anchorX < siteX:
                    self.anchorLine = comn.offsetRect(self.anchorLine, 4, 0)
                    siteX -= 3
                elif siteX < anchorX:
                    siteX += 4
                    icon.moveRect(self.anchorLine, (-3, 0))
            selectRect = comn.AccumRects(self.anchorLine)
            selectRect.add((siteX, siteY, siteX, siteY))
        # Get the icons that would be covered by a rectangular selection of the box
        iconsToSelect = self.window.findIconsInRegion(selectRect.get())
        iconsToSelect = [ic for ic in iconsToSelect if ic.inRectSelect(selectRect.get())]
        # If the selection spans multiple statements, change to statement-level selection
        topIcons = {ic.topLevelParent() for ic in iconsToSelect}
        if len(topIcons) <= 1:
            return iconsToSelect
        else:
            return self._seqIconsBetween(topIcons)

    def _seqIconsBetween(self, topIcons):
        """Return all of the icons in the sequence including topIcons (filling in gaps,
        and adding all of the icons in the statement hierarchy)"""
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
        return [i for ic in iconsInSeq for i in ic.traverse()]

    def removeCursor(self, eraseOld=True, placeEntryText=True):
        """Remove the cursor from the window.  Be aware that this can cause rearrangement
        of icons by virtue of taking focus from an entry icon, which will then try to
        place its text content and pending arguments (so 1. don't call this where such
        rearrangement would cause trouble and 2. be sure to check for dirty icon layouts
        after calling)."""
        if self.type == "text":
            self.icon.focusOut(placeEntryText)
        if self.type is not None and eraseOld:
            self.erase()
        self.type = None

    def blink(self):
        self.blinkState = not self.blinkState
        if self.blinkState:
            self.draw()
        else:
            self.erase()

    def draw(self):
        if self.type is None or self.window.dragging is not None:
            return
        elif self.type == "window":
            cursorImg = inputSiteCursorImage
            x, y = self.pos
            y -= inputSiteCursorOffset
        elif self.type == "icon":
            sitePos = self.icon.posOfSite(self.site)
            if sitePos is None:
                return # Cursor can be moved before site fully exists, so fail softly
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
            else:
                return
        elif self.type == "text":
            eIcon = self.icon
            if eIcon is None:
                return
            cursorPos = min(eIcon.cursorPos, len(eIcon.text))
            cursorImg = textCursorImage
            x, y = eIcon.cursorWindowPos()
            y -= cursorImg.height // 2
        elif self.type == "typeover":
            if self.icon is None:
                return
            cursorImg = textCursorImage
            x, y = self.icon.rect[:2]
            xOffset, yOffset = self.icon.typeoverCursorPos()
            x += xOffset
            y += yOffset - cursorImg.height // 2
        cursorRegion = (x, y, x + cursorImg.width, y + cursorImg.height)
        self.lastDrawRect = cursorRegion
        cursorRegion = self.window.contentToImageRect(cursorRegion)
        cursorDrawImg = self.window.image.crop(cursorRegion)
        cursorDrawImg.paste(cursorImg, mask=cursorImg)
        self.window.drawImage(cursorDrawImg, cursorRegion[:2])

    def processArrowKey(self, evt):
        direction = evt.keysym
        if self.type is None:
            return
        elif self.type == "text":
            self.icon.arrowAction(direction)
            return
        elif self.type == "typeover":
            self.erase()
            if direction in ("Up", "Down"):
                fromIcon = self.icon
                fromSite = fromIcon.sites.lastCursorSite()
                toIcon, toSite = self._geometricTraverse(fromIcon, fromSite, direction)
                self.moveToIconSite(toIcon, toSite, evt)
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
                self.moveToIconSite(toIcon, toSite, evt)
            return
        if self.type == "window":
            x, y = self.pos
            directions = {"Up":(0,-1), "Down":(0,1), "Left":(-1,0), "Right":(1,0)}
            xOff, yOff = directions[direction]
            x += xOff * WINDOW_CURSOR_INCREMENT
            y += yOff * WINDOW_CURSOR_INCREMENT
            windowWidth, windowHeight = self.window.image.size
            if  WINDOW_CURSOR_MARGIN < x < windowWidth - WINDOW_CURSOR_MARGIN and \
             WINDOW_CURSOR_MARGIN < y < windowHeight - WINDOW_CURSOR_MARGIN:
                self.erase()
                self.pos = x, y
                self.draw()
            return
        elif self.type == "icon":
            self._processIconArrowKey(evt)

    def arrowKeyWithSelection(self, evt, selectedIcons):
        """Process arrow key pressed with no cursor but selected icons."""
        direction = evt.keysym
        shiftPressed = evt.state & python_g.SHIFT_MASK
        if not shiftPressed:
            self.window.unselectAll()
        selectedRects = comn.AccumRects()
        for ic in selectedIcons:
            selectedRects.add(ic.selectionRect())
        selectedRect = selectedRects.get()
        l, t, r, b = selectedRect
        l -= 10
        t -= 10
        r += 10
        b += 10
        searchRect = l, t, r, b
        cursorSites = []
        for ic in self.window.findIconsInRegion(searchRect):
            snapLists = ic.snapLists(forCursor=True)
            for ic, (x, y), name in snapLists.get("input", []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrIn", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            outSites = snapLists.get("output", [])
            if len(outSites) > 0:
                cursorSites.append((*outSites[0][1], ic, "output"))
        if len(cursorSites) == 0:
            return  # It is possible to have icons with no viable cursor sites
        selLeft, selTop, selRight, selBottom = selectedRect
        bestDist = None
        for siteData in cursorSites:
            x, y = siteData[:2]
            if direction == "Left":  # distance from left edge
                dist = abs(x - selLeft) + max(0, selBottom-y) + max(0, y-selTop)
            elif direction == "Right":  # distance from right edge
                dist = abs(x - selRight) + max(0, selBottom-y) + max(0, y-selTop)
            elif direction == "Up":  # distance from top edge
                dist = abs(y - selTop) + max(0, selLeft-x) + max(0, x-selRight)
            elif direction == "Down":  # distance from bottom edge
                dist = abs(y - selBottom) + max(0, selLeft-x) + max(0, x-selRight)
            if bestDist is None or dist < bestDist:
                bestSiteData = siteData
                bestDist = dist
        x, y, ic, site = bestSiteData
        if site == "output":
            parent = ic.parent()
            if parent is not None:
                self.setToIconSite(parent, parent.siteOf(ic))
                return
        self.moveToIconSite(ic, site, evt)

    def processBreakingArrowKey(self, evt):
        """Alt+arrow action (since we don't have configurable bindings, yet, I can say
        this).  Breaks in to and text edits the icon in the direction of the arrow key
        from the cursor."""
        if self.type != 'icon' or self.site in ('attrOut', 'seqIn', 'seqOut'):
            return
        if evt.keysym == 'Left':
            ic = self.icon
            site = self.site
        elif evt.keysym == 'Right':
            ic, site = self._lexicalTraverse(self.icon, self.site, 'Right')
        else:
            return
        # If the icon site being entered is coincident with the output of the icon,
        # the user is probably trying to edit the parent
        while site == ic.hasCoincidentSite():
            parent = ic.parent()
            if parent is None:
                # Site is coincident with output, but is at the top level.  Call the
                # icon's backspace routine, but I can't imagine why it would do anything.
                break
            site = parent.siteOf(ic)
            ic = parent
        # If the icon has a method for text-editing, do that, otherwise fall back to
        # normal arrow processing.
        entryIcon = ic.becomeEntryIcon(siteAfter=site)
        if entryIcon is None:
            self._processIconArrowKey(evt)
            return
        # Put the text cursor on the end from which the arrow was typed
        if evt.keysym == 'Left':
            entryIcon.cursorPos = len(entryIcon.text)
        else:
            entryIcon.cursorPos = 0
        self.window.cursor.setToText(entryIcon)

    def _processIconArrowKey(self, evt):
        """For cursor on icon site (self.type == "icon"), set new site based on arrow
        direction"""
        if evt.keysym in ('Left', 'Right') and not (evt.state & python_g.CTRL_MASK):
            # Lexical traversal. This also visits icons that hold a text cursor (probably
            # only the entry icon, maybe strings and/or comments).
            if evt.keysym == 'Left' and _isEntryIcBodySite(self.icon, self.site):
                self.setToText(self.icon)
                return
            ic, site = self._lexicalTraverse(self.icon, self.site, evt.keysym)
            while ic.typeOf(site) == 'cprhIn':
                # lexical traversal returns comprehension sites which are usually
                # coincident with an attribute site and shouldn't get cursor
                ic, site = self._lexicalTraverse(ic, site, evt.keysym)
            if evt.keysym == 'Right' and _isEntryIcBodySite(ic, site):
                self.setToText(ic)
                return
        else:
            ic, site = self._geometricTraverse(self.icon, self.site, evt.keysym)
        self.moveToIconSite(ic, site, evt)

    def _lexicalTraverse(self, fromIcon, fromSite, direction):
        """Return the cursor position (icon and siteId) to the left or right according
        to the "text-flow"."""
        fromSiteType = fromIcon.typeOf(fromSite)
        if direction == 'Left':
            if fromSiteType in iconsites.parentSiteTypes:
                # Cursor is on an output site.  There's probably nowhere to go (return
                # the same cursor position).  In the unlikely case that it is attached to
                # something, make a recursive call with the proper cursor site (input)
                attachedIc = fromIcon.childAt(fromSite)
                if attachedIc is None:
                    return fromIcon, fromSite
                attachedSite = attachedIc.siteOf(fromIcon)
                return self._lexicalTraverse(attachedIc, attachedSite, direction)
            elif fromSite == 'seqOut':
                if isinstance(fromIcon, icon.BlockEnd):
                    return fromIcon, "seqIn"
                return icon.rightmostSite(fromIcon)
            elif fromSite == 'seqIn':
                prevStmt = fromIcon.prevInSeq()
                if prevStmt is None:
                    return fromIcon, fromSite
                if isinstance(prevStmt, icon.BlockEnd):
                    return prevStmt, "seqIn"
                return icon.rightmostSite(prevStmt)
            # Cursor is on an input site of some sort (input, attrIn, cprhIn)
            prevSite = fromIcon.sites.prevCursorSite(fromSite)
            if prevSite is None:
                highestIc = iconsites.highestCoincidentIcon(fromIcon)
                parent = highestIc.parent()
                if parent is None:
                    if highestIc.hasCoincidentSite():
                        return iconsites.lowestCoincidentSite(highestIc,
                            highestIc.hasCoincidentSite())
                    return highestIc, topSite(highestIc, seqDown=False)
                parentSite = parent.siteOf(highestIc)
                if fromIcon.hasCoincidentSite():
                    return self._lexicalTraverse(parent, parentSite, direction)
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
                    return self._lexicalTraverse(fromIcon, nextSite, direction)
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
                    return nextIcon, topSite(nextIcon, seqDown=True)
                parentSite = parent.siteOf(nextIcon)
                nextSite = parent.sites.nextCursorSite(parentSite)
                nextIcon = parent
            return nextIcon, nextSite

    def _geometricTraverse(self, fromIcon, fromSite, direction):
        """Return the next cursor position (icon and siteId) in a given direction
        (physically, not lexically) from the given position (fromIcon, fromSite)."""
        # Special cases for traversing block end icons up and down, since their sites
        # are not physically up and down from each other, but need to be visited as such
        if isinstance(fromIcon, icon.BlockEnd) and fromSite == 'seqIn' and \
                direction == 'Down':
            return fromIcon, 'seqOut'
        if isinstance(fromIcon.nextInSeq(), icon.BlockEnd) and fromSite == 'seqOut' and \
                direction == 'Down':
            return fromIcon.nextInSeq(), 'seqOut'
        if isinstance(fromIcon, icon.BlockEnd) and fromSite == 'seqOut' and \
                direction == 'Up':
            return fromIcon, 'seqIn'
        if isinstance(fromIcon.prevInSeq(), icon.BlockEnd) and fromSite == 'seqIn' and \
                direction == 'Up':
            return fromIcon.prevInSeq(), 'seqIn'
        # Build a list of possible destination cursor positions, normalizing attribute
        # site positions to the center of the cursor (in/out site position).
        cursorX, cursorY = fromIcon.posOfSite(fromSite)
        searchRect = (cursorX-HORIZ_ARROW_MAX_DIST, cursorY-VERT_ARROW_MAX_DIST,
         cursorX+HORIZ_ARROW_MAX_DIST, cursorY+VERT_ARROW_MAX_DIST)
        cursorTopIcon = fromIcon.topLevelParent()
        cursorPrevIcon = cursorTopIcon.prevInSeq()
        cursorNextIcon = cursorTopIcon.nextInSeq()
        cursorSites = []
        for winIcon in self.window.findIconsInRegion(searchRect):
            topIcon = winIcon.topLevelParent()
            if topIcon not in (cursorTopIcon, cursorPrevIcon, cursorNextIcon):
                continue  # Limit statement jumps to a single statement
            snapLists = winIcon.snapLists(forCursor=True)
            hasOutSite = len(snapLists.get("output", [])) > 0
            for ic, (x, y), name in snapLists.get('input', []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqIn', []):
                if direction in ('Up', 'Down'):
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqOut', []):
                if  direction in ('Up', 'Down') or not hasOutSite:
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrIn", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            if winIcon.parent() is None:
                outSites = snapLists.get("output", [])
                if len(outSites) > 0:
                    cursorSites.append((*outSites[0][1], winIcon, "output"))
        # Rank the destination positions by nearness to the current cursor position
        # in the cursor movement direction, and cull those in the wrong direction
        if fromIcon.typeOf(fromSite) == "attrIn":
            cursorY -= icon.ATTR_SITE_OFFSET  # Normalize to input/output site y
        choices = []
        for x, y, ic, site in cursorSites:
            if direction == "Left":
                dist = cursorX - x
            elif direction == "Right":
                dist = x - cursorX
            elif direction == "Up":
                dist = cursorY - y
            elif direction == "Down":
                dist = y - cursorY
            if dist > 0:
                choices.append((dist, x, y, ic, site))
        if len(choices) == 0:
            return fromIcon, fromSite
        choices.sort(key=itemgetter(0))
        if direction in ("Left", "Right"):
            # For horizontal movement, just use a simple vertical threshold to decide
            # if the movement is appropriate
            for xDist, x, y, ic, site in choices:
                if xDist > VERT_ARROW_X_JUMP_MIN:
                    if abs(y - cursorY) < HORIZ_ARROW_Y_JUMP_MAX:
                        return ic, site
        else:  # Up, Down
            # For vertical movement, do a second round of ranking.  This time add y
            # distance to weighted X distance (ranking x jumps as further away)
            bestRank = None
            for yDist, x, y, ic, site in choices:
                if yDist > VERT_ARROW_Y_JUMP_MIN or isinstance(ic, icon.BlockEnd):
                    rank = yDist + VERT_ARROW_X_WEIGHT*abs(x-cursorX)
                    if bestRank is None or rank < bestRank[0]:
                        bestRank = (rank, ic, site)
            if bestRank is None:
                return fromIcon, fromSite
            rank, ic, site = bestRank
            if site == 'seqIn' and direction == "Up":
                # Typing at a seqIn site is the same as typing at the connected seqOut
                # site, so save the user a keypress by going to the seqOut site above
                prevIcon = ic.prevInSeq()
                if prevIcon:
                    ic = prevIcon
                    site = 'seqOut'
            return ic, site
        return fromIcon, fromSite

    def moveOutOfEndParen(self, token):
        """Move the cursor past the next end paren/bracket/brace (token is one of
        "endParen", "endBracket", or "endBrace", even if it is not adjacent to the
        cursor."""
        if self.type != "icon":
            return False
        siteType = self.siteType
        child = None
        # Just tear intervening icons to the end, regardless how far (was this right?)
        for parent in self.icon.parentage(includeSelf=True):
            if child is not None:
                siteType = parent.typeOf(parent.siteOf(child))
            if siteType == "input" and (
             (token == "endParen" and (
              parent.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and \
              opicons.needsParens(parent) or parent.__class__ in (listicons.CallIcon,
               listicons.TupleIcon, blockicons.DefIcon) and parent.closed or
              parent.__class__ is blockicons.ClassDefIcon and parent.hasArgs or
              parent.__class__ is parenicon.CursorParenIcon and parent.closed)) or
             (token == "endBrace" and isinstance(parent, listicons.DictIcon) and
              parent.closed) or
             (token == "endBracket" and
              parent.__class__ in (listicons.ListIcon, subscripticon.SubscriptIcon) and
              parent.closed)):
                self.setToIconSite(parent, "attrIcon")
                return True
            child = parent
        return False

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect, redraw=False)
            self.lastDrawRect = None

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

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

def _isEntryIcBodySite(ic, siteId):
    """Return True if ic is an entry icon and siteId is the site adjacent to the icon
    body.  This is a temporary placeholder for a more general routine that will do this
    for all icons that can host text editing (as opposed to interchanging with an entry
    icon to do so)."""
    return isinstance(ic, entryicon.EntryIcon) and siteId == ic.sites.firstCursorSite()

topLevelStmts = {'async def': blockicons.DefIcon, 'def': blockicons.DefIcon,
    'class': blockicons.ClassDefIcon, 'break': nameicons.BreakIcon,
    'return': nameicons.ReturnIcon, 'continue': nameicons.ContinueIcon,
    'yield': nameicons.YieldIcon, 'del': nameicons.DelIcon,
    'elif': blockicons.ElifIcon,
    'else': blockicons.ElseIcon, 'except': blockicons.ExceptIcon,
    'finally': blockicons.FinallyIcon, 'async for': blockicons.ForIcon,
    'for': blockicons.ForIcon, 'from': nameicons.ImportFromIcon,
    'global': nameicons.GlobalIcon,
    'if': blockicons.IfIcon, 'import': nameicons.ImportIcon,
    'nonlocal': nameicons.NonlocalIcon, 'pass': nameicons.PassIcon,
    'raise': nameicons.RaiseIcon, 'try': blockicons.TryIcon,
    'async while': blockicons.WhileIcon, 'while': blockicons.WhileIcon,
    'async with': blockicons.WithIcon, 'with': blockicons.WithIcon}

stmtIcons = {v for v in topLevelStmts.values()}