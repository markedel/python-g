# Copyright Mark Edel  All rights reserved
# Icon window cursor, and some support code for icon backspace functionality (in here,
# rather than icon.py, because it needs to know about many icon types, and icon.py, being
# the base class for icons, will tie the import system in knots if it tries to import its
# own subclasses).
import winsound
from PIL import Image, ImageDraw
from operator import itemgetter
import ast
import comn
import iconsites
import icon
import opicons
import blockicons
import nameicons
import listicons
import assignicons
import subscripticon
import parenicon
import infixicon
import python_g

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
    "   .   ",
    "%%% %%%",
    "...%...",
))
seqInSiteCursorXOffset = 3
seqInSiteCursorYOffset = 3

seqOutSiteCursorImage = comn.asciiToImage((
    "   %   ",
    "%%%.%%%",
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

    def setToWindowPos(self, pos):
        if self.type is not None:
            self.erase()
        self.type = "window"
        self.pos = pos
        self.blinkState = True
        self.draw()

    def setToIconSite(self, ic, siteIdOrSeriesName, seriesIndex=None):
        if self.type is not None:
            self.erase()
        self.type = "icon"
        self.icon = ic
        if seriesIndex is None:
            self.site = siteIdOrSeriesName
        else:
            self.site = iconsites.makeSeriesSiteId(siteIdOrSeriesName, seriesIndex)
        self.siteType = ic.typeOf(self.site)
        self.blinkState = True
        self.draw()

    def setToEntryIcon(self):
        if self.type is not None:
            self.erase()
        self.type = "text"
        self.blinkState = True
        self.draw()

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
        self.window.refresh(redrawRect.get())
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

    def removeCursor(self):
        if self.type is not None:
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
            eIcon = self.window.entryIcon
            if eIcon is None:
                return
            cursorPos = min(eIcon.cursorPos, len(eIcon.text))
            cursorImg = textCursorImage
            x, y = eIcon.rect[:2]
            x += eIcon.textOffset + icon.globalFont.getsize(eIcon.text[:cursorPos])[0]
            y += eIcon.sites.output.yOffset - cursorImg.height // 2
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
            self.window.entryIcon.arrowAction(direction)
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

    def _processIconArrowKey(self, evt):
        """For cursor on icon site, set new site based on arrow direction"""
        # Build a list of possible destination cursor positions, normalizing attribute
        # site positions to the center of the cursor (in/out site position).
        direction = evt.keysym
        cursorX, cursorY = self.icon.posOfSite(self.site)
        searchRect = (cursorX-HORIZ_ARROW_MAX_DIST, cursorY-VERT_ARROW_MAX_DIST,
         cursorX+HORIZ_ARROW_MAX_DIST, cursorY+VERT_ARROW_MAX_DIST)
        cursorTopIcon = self.icon.topLevelParent()
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
        if self.siteType == "attrIn":
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
            return
        choices.sort(key=itemgetter(0))
        if direction in ("Left", "Right"):
            # For horizontal movement, just use a simple vertical threshold to decide
            # if the movement is appropriate
            for xDist, x, y, ic, site in choices:
                if xDist > VERT_ARROW_X_JUMP_MIN:
                    if abs(y - cursorY) < HORIZ_ARROW_Y_JUMP_MAX:
                        self.moveToIconSite(ic, site, evt)
                        return
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
                return
            rank, ic, site = bestRank
            if site == 'seqIn' and direction == "Up":
                # Typing at a seqIn site is the same as typing at the connected seqOut
                # site, so save the user a keypress by going to the seqOut site above
                prevIcon = ic.prevInSeq()
                if prevIcon:
                    ic = prevIcon
                    site = 'seqOut'
            self.moveToIconSite(ic, site, evt)

    def movePastEndParen(self, token):
        """Move the cursor past the next end paren/bracket/brace (token is one of
        "endParen", "endBracket", or "endBrace"."""
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
              parent.__class__ is opicons.BinOpIcon and opicons.needsParens(parent) or
              parent.__class__ in (listicons.CallIcon, listicons.TupleIcon,
               blockicons.DefIcon) or
              parent.__class__ is parenicon.CursorParenIcon and parent.closed)) or
             (token == "endBrace" and isinstance(parent, listicons.DictIcon)) or
             (token == "endBracket" and
              parent.__class__ in (listicons.ListIcon, subscripticon.SubscriptIcon))):
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

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 192 or 219 <= evt.keycode <= 222:
        return chr(evt.keysym_num)
    return None

def beep():
    # Another platform dependent bit.  tkinter has a .bell() method, but it generates
    # an elaborate sound that's supposed to alert the user of a dialog popping up, which
    # is not appropriate for the tiny nudge for your keystroke being rejected.
    winsound.Beep(1500, 120)

def rightmostSite(ic, ignoreAutoParens=False):
    """Return the site that is rightmost on an icon.  For most icons, that is an attribute
    site, but for unary or binary operations with the right operand missing, it can be an
    input site.  While binary op icons may have a fake invisible attribute site, it should
    be used carefully (if ever).  ignoreAutoParens prevents choosing auto-paren attribute
    site of BinOpIcon, even if it the rightmost."""
    if isinstance(ic, opicons.UnaryOpIcon):
        if ic.arg() is None:
            return ic, 'argIcon'
        return rightmostSite(icon.findLastAttrIcon(ic.arg()))
    elif ic.__class__ in (assignicons.AssignIcon, nameicons.YieldIcon,
            nameicons.YieldFromIcon):
        children = [site.att for site in ic.sites.values if site.att is not None]
        if len(children) == 0:
            return ic, 'values_0'
        return rightmostSite(icon.findLastAttrIcon(children[-1]))
    elif isinstance(ic, opicons.BinOpIcon) and (not ic.hasParens or ignoreAutoParens) \
            or isinstance(ic, infixicon.InfixIcon):
        if ic.rightArg() is None:
            return ic, 'rightArg'
        return rightmostSite(icon.findLastAttrIcon(ic.rightArg()))
    elif isinstance(ic, blockicons.DefIcon):
        children = [site.att for site in ic.sites.argIcons if site.att is not None]
        if len(children) == 0:
            return ic, 'argIcons_0'
        return rightmostSite(icon.findLastAttrIcon(children[-1]))
    elif ic.childAt('attrIcon'):
        return rightmostSite(ic.childAt('attrIcon'))
    return ic, 'attrIcon'

topLevelStmts = {'async def': blockicons.DefIcon, 'def': blockicons.DefIcon,
    'class': blockicons.ClassDefIcon, 'break': nameicons.BreakIcon,
    'return': nameicons.ReturnIcon, 'continue': nameicons.ContinueIcon,
    'yield': nameicons.YieldIcon, 'del': nameicons.DelIcon,
    'elif': blockicons.ElifIcon,
    'else': blockicons.ElseIcon, 'except': nameicons.ExceptIcon,
    'finally': nameicons.FinallyIcon, 'async for': blockicons.ForIcon,
    'for': blockicons.ForIcon, 'from': nameicons.ImportFromIcon,
    'global': nameicons.GlobalIcon,
    'if': blockicons.IfIcon, 'import': nameicons.ImportIcon,
    'nonlocal': nameicons.NonlocalIcon, 'pass': nameicons.PassIcon,
    'raise': nameicons.RaiseIcon, 'try': nameicons.TryIcon,
    'async while': blockicons.WhileIcon, 'while': blockicons.WhileIcon,
    'async with': blockicons.WithIcon, 'with': blockicons.WithIcon}
