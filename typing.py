# Copyright Mark Edel  All rights reserved
import icon
import compile_eval
import python_g
import winsound
import ast
from PIL import Image, ImageDraw
import re
from operator import itemgetter

PEN_BG_COLOR = (255, 245, 245, 255)
PEN_OUTLINE_COLOR = (255, 97, 120, 255)
RIGHT_LAYOUT_MARGIN = 3
PEN_MARGIN = 6

# How far to move the cursor per arrow keystroke on the window background
WINDOW_CURSOR_INCREMENT = 20

# How far away from the edges of the window to keep the window background cursor
WINDOW_CURSOR_MARGIN = 5

# Max allowable cursor y movement for left and right arrow movement over icons
HORIZ_ARROW_Y_JUMP_MAX = 12

# Minimum threshold for y cursor movement on up/down arrow (to prevent minor alignment
# issues from dominating the destination site choice
VERT_ARROW_Y_JUMP_MIN = 5

# Allowable variance in y site positions for two sites to be considered the same y
# distance during up/down arrow cursor movement
VERT_ARROW_Y_EQUIVALENCE_DIST = 4

binaryOperators = ['+', '-', '*', '**', '/', '//', '%', '@<<', '>>', '&', '|', '^', '<',
 '>', '<=', '>=', '==', '!=']
unaryOperators = ['+', '-', '~']
emptyDelimiters = [' ', '\t', '\n', '\r', '\f', '\v']
delimiters = emptyDelimiters + ['(', ')', '[', ']', '{', '},', ':', '.', ';', '@', '=',
 '->', '+=', '-=', '*=', '/=', '//=', '%=', '@=', '&=', '|=', '^=', '>>=', '<<=', '**=']
delimitChars = list(dict.fromkeys("".join(binaryOperators + unaryOperators + delimiters)))
keywords = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield']

identPattern = re.compile('^[a-zA-z_][a-zA-z_\\d]*$')
numPattern = re.compile('^([\\d_]*\\.?[\\d_]*)|'
 '(((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*)?$')
attrPattern = re.compile('^\\.[a-zA-z_][a-zA-z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-z\\d_.\\(\\[\\{\\s+-~]')

inputSiteCursorPixmap = (
    "..   ",
    ".. % ",
    ".. % ",
    ". % .",
    " % ..",
    ". % .",
    ".. % ",
    ".. % ",
    ".. % ",
    ".. % ",
    ".. % ",
    "..   ",
)
inputSiteCursorPixmap = (
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
    "..% ",
)
inputSiteCursorOffset = 6
inputSiteCursorImage = icon.asciiToImage(inputSiteCursorPixmap)

attrSiteCursorPixmap = (
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
    ".%",
)
attrSiteCursorOffset = 11
attrSiteCursorImage = icon.asciiToImage(attrSiteCursorPixmap)

textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

penPixmap = (
    "....oooo    ",
    "...o%%%%oo  ",
    "..o%%%%%%%oo",
    "..o%%%%%%%%%",
    ".o%%%%22%%%%",
    "o33333333%%%",
    ".o%%%%22%%%%",
    "..o%%%%%%%%%",
    "..o%%%%%%%oo",
    "...o%%%%oo  ",
    "....oooo    "
)
penImage = icon.asciiToImage(penPixmap)

attrPenPixmap = (
    "....oooo...",
    "...o%%%%o..",
    "..o%%%%%%o.",
    ".o%%%%%%%%o",
    ".o%%%33%%%o",
    ".o%%%33%%%o",
    ".o%%3%%%%%o",
    "o%%3%%%%%o.",
    "o%3%%%%%o..",
    "o3%%oooo...",
    "oooo......."
)
attrPenImage = icon.asciiToImage(attrPenPixmap)

class EntryIcon(icon.Icon):
    def __init__(self, attachedIcon, attachedSite, initialString="", window=None,
     location=None):
        icon.Icon.__init__(self, window)
        self.text = initialString
        ascent, descent = icon.globalFont.getmetrics()
        self.height = ascent + descent + 2 * icon.TEXT_MARGIN + 1
        self.initTxtWidth = icon.globalFont.getsize("i")[0]
        self.txtWidthIncr = self.initTxtWidth
        x, y = location if location is not None else (0, 0)
        self.attachedIcon = attachedIcon
        self.attachedSite = attachedSite
        self.rect = (x, y, x + self._width(), y + self.height)
        self.outSiteOffset = (0, self.height // 2)
        self.attrSiteOffset = (0, self.height - 3)
        self.layoutDirty = True
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.cursorPos = len(initialString)
        self.pendingArgument = None   # Icons that hang off the right
        self.pendingAttribute = None  # "

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

    def touchesPosition(self, x, y):
        if not icon.pointInRect((x, y), self.rect):
            return False
        rectLeft, rectTop = self.rect[:2]
        if x > rectLeft + self.penOffset():
            return True
        if self.attachedToAttribute():
            penImgYOff = self.attrSiteOffset[1] - attrPenImage.height
            pixel = attrPenImage.getpixel((x - rectLeft, y - rectTop - penImgYOff))
        else:
            penImgYOff = self.outSiteOffset[1] - penImage.height // 2
            pixel = penImage.getpixel((x - rectLeft, y-rectTop - penImgYOff))
        return pixel[3] > 128

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
            draw = self.window.draw
        else:
            draw = ImageDraw.Draw(image)
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        boxWidth = self._width(boxOnly=True) - 1
        draw.rectangle((x + self.penOffset(), y, x + self.penOffset() + boxWidth,
         y + self.height-1), fill=PEN_BG_COLOR, outline=PEN_OUTLINE_COLOR)
        textLeft = x + self.textOffset
        draw.text((textLeft, y + icon.TEXT_MARGIN), self.text, font=icon.globalFont,
         fill=(0, 0, 0, 255))
        if self.attachedToAttribute():
            nibTop = y + self.attrSiteOffset[1] - attrPenImage.height
            image.paste(attrPenImage, box=(x, nibTop), mask=attrPenImage)
        else:
            nibTop = y + self.outSiteOffset[1] - penImage.height // 2
            image.paste(penImage, box=(x, nibTop), mask=penImage)

    def addText(self, char):
        newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos + len(char))

    def backspace(self):
        newText = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos-1)

    def arrowAction(self, direction):
        newCursorPos = self.cursorPos
        if direction == "Left":
            newCursorPos = max(0, self.cursorPos - 1)
        elif direction == "Right":
            newCursorPos = min(self.cursorPos + 1, len(self.text))
        if newCursorPos == self.cursorPos:
            return
        self.window.cursor.erase()
        self.cursorPos = newCursorPos
        self.window.cursor.draw()

    def _setText(self, newText, newCursorPos):
        oldWidth = self._width()
        parseResult = parseEntryText(newText, self.attachedToAttribute())
        print('parse result', parseResult)
        if parseResult == "reject":
            beep()
            return
        cursor = self.window.cursor
        if parseResult == "accept":
            self.text = newText
            cursor.erase()
            self.cursorPos = newCursorPos
            cursor.draw()
            if self._width() != oldWidth:
                self.layoutDirty = True
            return
        if parseResult == "comma":
            if not self.commaEntered(self.attachedIcon):
                beep()
            return
        if parseResult == "endParen":
            print('connect to end paren')
            return
        if parseResult == "makeFunction":
            if not self.makeFunction(self.attachedIcon):
                beep()
            return
        # Parser emitted an icon.  Splice it in to the hierarchy
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        ic.window = self.window
        snapLists = ic.snapLists()
        if self.attachedIcon is None:
            ic.rect = python_g.offsetRect(ic.rect, self.rect[0], self.rect[1])
            self.window.topIcons.append(ic)
            if self in self.window.topIcons:
                self.window.topIcons.remove(self)
            ic.layoutDirty = True
            if "input" in snapLists:
                cursor.setToIconSite(ic, ("input", 0))
            else:
                cursor.setToIconSite(ic, ("attrOut", 0))
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            self.appendOperator(ic)
        elif self.attachedSite[0] == "input":
            # Entry icon is attached to an input site
            self.attachedIcon.replaceChild(ic, self.attachedSite)
            if "input" in snapLists:
                cursor.setToIconSite(ic, ("input", 0))
            elif "attrOut in snapLists":
                cursor.setToIconSite(ic, ("attrOut", 0))
            else:
                cursor.removeCursor()
        # If entry icon has pending arguments, try to place them.  Code does its best
        # to place the cursor at the most reasonable spot.  If vacant, place pending
        # args there
        if self.pendingArgument is not None and remainingText == "":
            if cursor.type is "icon" and cursor.site[0] == "input" and \
             cursor.icon.childAt(cursor.site) is None:
                cursor.icon.replaceChild(self.pendingArgument, cursor.site)
                self.pendingArgument = None
        # If the pending text needs no further input, process it, now
        if remainingText == ')':
            print('connect with nearest open paren')
            remainingText = ""
        elif remainingText == '(' and ic.__class__ is icon.IdentIcon:
            if not self.makeFunction(ic):
                beep()
            remainingText = ""
        elif remainingText == ',':
            if not self.commaEntered(ic):
                beep()
            remainingText = ""
        # If the entry icon can go away, remove it and we're done
        if self.pendingArgument is None and remainingText == "":
            self.window.entryIcon = None
            return
        # The entry icon needs to remain (cursor was set above to appropriate destination)
        if cursor.type is not "icon":
            return
        self.attachedIcon = cursor.icon
        self.attachedSite = cursor.site
        self.text = remainingText
        self.attachedIcon.replaceChild(self, self.attachedSite)
        self.cursorPos = len(remainingText)
        cursor.setToEntryIcon()
        cursor.draw()
        self.layoutDirty = True

    def commaEntered(self, onIcon):
        if onIcon.__class__ is icon.FnIcon:
            onIcon.insertChildren([self], ("input", len(onIcon.argIcons)))
        child = onIcon
        for parent in self.window.parentage(onIcon):
            if parent.__class__ is icon.FnIcon:
                onIcon.layoutDirty = True
                siteType, siteIdx = parent.siteOf(child)
                insertSite = (siteType, siteIdx + 1)
                parent.insertChildren([None], insertSite)
                self.window.cursor.setToIconSite(parent, insertSite)
                return True
        return False

    def makeFunction(self, ic):
        if ic.__class__ is not icon.IdentIcon or not identPattern.fullmatch(ic.name):
            return False
        parent = self.window.parentOf(ic)
        fnIcon = icon.FnIcon(ic.name, window=self.window)
        fnIcon.layoutDirty = True
        if parent is None:
            self.window.topIcons.remove(ic)
            self.window.topIcons.append(fnIcon)
            fnIcon.rect = python_g.offsetRect(fnIcon.rect, ic.rect[0], ic.rect[1])
        else:
            parent.replaceChild(fnIcon, parent.siteOf(ic))
        self.window.cursor.setToIconSite(fnIcon, ("input", 0))
        return True

    def appendOperator(self, newOpIcon):
        """The entry icon is attached to an attribute site and a binary operator has been
        entered.  Stitch the operator in to the correct level with respect to the
        surrounding binary operators, and move the cursor to the empty operand slot."""
        argIcon = self.attachedIcon
        entryIconParents = self.window.parentage(self)
        argIcon.replaceChild(None, self.attachedSite)
        leftArg = argIcon
        rightArg = None
        childOp = argIcon
        # Walk up the hierarchy of binary operations, breaking each one in to left and
        # right operands for the new operation.  Stop when the parent operation has
        # lower precedence, or is not a binary operation.  Also stop if the parent
        # operation has equal precedence, and the associativity of the operation matches
        # the side of the operation on which the insertion is being made.
        for op in reversed(entryIconParents[:-1]):
            if op.__class__ != icon.BinOpIcon or newOpIcon.precedence > op.precedence or \
                    newOpIcon.precedence == op.precedence and (
                     op.leftAssoc() and op.leftArg is childOp or
                     op.rightAssoc() and op.rightArg is childOp):
                op.replaceChild(newOpIcon, op.siteOf(childOp))
                break
            if op.leftArg is childOp:  # Insertion was on left side of operation
                op.leftArg = rightArg
                if op.leftArg is None:
                    self.window.cursor.setToIconSite(op, ("input", 0))
                rightArg = op
            else:                      # Insertion was on right side of operation
                op.rightArg = leftArg
                leftArg = op
            childOp = op
        else:  # Reached the top level without finding a parent for newOpIcon
            self.window.topIcons.remove(childOp)
            self.window.topIcons.append(newOpIcon)
            newOpIcon.rect = python_g.offsetRect(newOpIcon.rect, leftArg.rect[0],
                argIcon.rect[1])
        if rightArg is None:
            self.window.cursor.setToIconSite(newOpIcon, ("input", 1))
        newOpIcon.layoutDirty = True
        newOpIcon.replaceChild(leftArg, ("input", 0))
        newOpIcon.replaceChild(rightArg, ("input", 1))

    def children(self):
        if self.pendingArgument:
            return [self.pendingArgument]
        elif self.pendingAttribute:
            return [self.pendingAttribute]
        return []

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        return {"output":[(self, (x + self.outSiteOffset[0], y + self.outSiteOffset[1]), 0)]}

    def replaceChild(self, newChild, site):
        siteType, siteIndex = site
        if siteType == "input":
            self.pendingArgument = newChild
            self.pendingAttribute = None
        elif siteType == "attrOut":
            self.pendingAttribute = newChild
            self.pendingArgument = None
        self.layoutDirty = True

    def siteOf(self, child):
        if child is self.pendingArgument:
            return ("input", 0)
        elif child is self.pendingAttribute:
            return ("attrOut", 0)
        return None

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y+self.outSiteOffset[1], self._calcLayout())

    def click(self, evt):
        self.window.cursor.erase()
        self.cursorPos = findTextOffset(self.text, evt.x - self.rect[0] - self.textOffset)
        self.window.cursor.draw()

    def pointInTextArea(self, x, y):
        left, top, right, bottom = self.rect
        left += penImage.width
        top += 2
        bottom -= 2
        right -= 2
        return left < x < right and top < y < bottom

    def _doLayout(self, siteX, siteY, layout, parentPrecedence=None):
        width = self._width() + icon.outSiteImage.width - 1
        if self.attachedSite and self.attachedSite[0] == "attrOut":
            outSiteY = siteY - icon.ATTR_SITE_OFFSET
            outSiteX = siteX - 1
            self.textOffset = attrPenImage.width + icon.TEXT_MARGIN
        else:
            outSiteY = siteY
            outSiteX = siteX
            self.textOffset = penImage.width + icon.TEXT_MARGIN
        top = outSiteY - self.height//2
        self.rect = (outSiteX, top, outSiteX + width, top + self.height)
        if self.pendingArgument is not None:
            self.pendingArgument._doLayout(outSiteX + width - 4,
             outSiteY, layout.subLayouts[0])
        elif self.pendingAttribute is not None:
            self.pendingAttribute._doLayout(outSiteX + width - 4,
             outSiteY + icon.ATTR_SITE_OFFSET, layout.subLayouts[0])

    def _calcLayout(self, parentPrecedence=None):
        if self.attachedToAttribute():
            width = self._width() - 1 + RIGHT_LAYOUT_MARGIN
        else:
            width = self._width() - 2 + RIGHT_LAYOUT_MARGIN
        siteOffset = self.height // 2
        if self.attachedSite and self.attachedSite[0] == "attrOut":
            siteOffset += icon.ATTR_SITE_OFFSET
        if self.pendingArgument is None and self.pendingAttribute is None:
            return icon.Layout(self, width, self.height, siteOffset, [])
        if self.pendingArgument:
            pendingLayout = self.pendingArgument._calcLayout()
            heightAbove = max(siteOffset, pendingLayout.siteOffset)
            pendingHeightBelow = pendingLayout.height - pendingLayout.siteOffset
            heightBelow = max(self.height - siteOffset, pendingHeightBelow)
        else:
            pendingLayout = self.pendingAttribute._calcLayout()
            heightAbove = max(siteOffset, pendingLayout.siteOffset - icon.ATTR_SITE_OFFSET)
            pendingHeightBelow = icon.ATTR_SITE_OFFSET + pendingLayout.height - pendingLayout.siteOffset
            heightBelow = max(self.height - siteOffset, pendingHeightBelow)
        height = heightAbove + heightBelow
        width += pendingLayout.width
        return icon.Layout(self, width, height, heightAbove, [pendingLayout])

    def clipboardRepr(self, offset):
        return None

    def attachedToAttribute(self):
        return self.attachedSite is not None and \
         self.attachedSite[0] in ("attrIn", "attrOut")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN

class CursorParenIcon(icon.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        icon.UnaryOpIcon.__init__(self, "(", window=window, location=location)

    def clipboardRepr(self, offset):
        pass

class Cursor:
    def __init__(self, window, cursorType):
        self.window = window
        self.type = cursorType
        self.pos = (0, 0)
        self.icon = None
        self.site = None
        self.lastDrawRect = None
        self.blinkState = False

    def setToWindowPos(self, pos):
        if self.type is not None:
            self.erase()
        self.type = "window"
        self.pos = pos
        self.blinkState = True
        self.draw()

    def setToIconSite(self, ic, site):
        if self.type is not None:
            self.erase()
        self.type = "icon"
        self.icon = ic
        self.site = site
        self.blinkState = True
        self.draw()

    def setToEntryIcon(self):
        if self.type is not None:
            self.erase()
        self.type = "text"
        self.blinkState = True
        self.draw()

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
            siteType, siteIdx = self.site
            x, y = self.icon.posOfSite(self.site)
            if siteType in ("input", "output"):
                cursorImg = inputSiteCursorImage
                y -= inputSiteCursorOffset
            elif siteType in ("attrIn", "attrOut"):
                cursorImg = attrSiteCursorImage
                y -= attrSiteCursorOffset
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
            y += eIcon.outSiteOffset[1] - cursorImg.height // 2
        cursorRegion = (x, y, x + cursorImg.width, y + cursorImg.height)
        cursorDrawImg = self.window.image.crop(cursorRegion)
        cursorDrawImg.paste(cursorImg, mask=cursorImg)
        self.window.drawImage(cursorDrawImg, (x, y))
        self.lastDrawRect = cursorRegion

    def processArrowKey(self, direction):
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
            self._processIconArrowKey(direction)

    def _processIconArrowKey(self, direction):
        """For cursor on icon site, set new site based on arrow direction"""
        # Build a list of possible destination cursor positions, normalizing attribute
        # site positions to the center of the cursor (in/out site position).  For the
        # moment, limit to icons with the same top level parent
        topIcon = self.window.topLevelParent(self.icon)
        cursorSites = []
        for winIcon in topIcon.traverse():
            snapLists = winIcon.snapLists(atTop=winIcon is topIcon)
            for ic, (x, y), idx in snapLists.get("input", []):
                cursorSites.append((x, y, ic, ("input", idx)))
            for ic, (x, y), idx in snapLists.get("attrOut", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, ("attrOut", idx)))
            if winIcon is topIcon:
                outSites = snapLists.get("output", [])
                if len(outSites) > 0:
                    cursorSites.append((*outSites[0][1], winIcon, ("output", 0)))
        cursorX, cursorY = self.icon.posOfSite(self.site)
        # Rank the destination positions by nearness to the current cursor position
        # in the cursor movement direction, and cull those in the wrong direction
        if self.site[0] == "attrOut":
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
                if abs(y - cursorY) < HORIZ_ARROW_Y_JUMP_MAX:
                    self.setToIconSite(ic, site)
                    return
        else:  # Up, Down
            # For vertical movement, do a second round of culling and ranking.  This time
            # cull to only nearest equivalent y distance and re-rank by x distance
            nearestYDist = None
            newRanking = []
            for yDist, x, y, ic, site in choices:
                if yDist > VERT_ARROW_Y_JUMP_MIN:
                    if nearestYDist is None:
                        nearestYDist = yDist
                    if yDist - nearestYDist < VERT_ARROW_Y_EQUIVALENCE_DIST:
                        newRanking.append((abs(x-cursorX), ic, site))
            if len(newRanking) == 0:
                return
            newRanking.sort(key=itemgetter(0))
            xDist, ic, site = newRanking[0]
            self.setToIconSite(ic, site)

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect)
            self.lastDrawRect = None

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

def parseEntryText(text, forAttrSite):
    if len(text) == 0:
        return "accept"
    if forAttrSite:
        if attrPattern.fullmatch(text):
            return "accept"  # Legal attribute pattern
        if text in ("i", "a", "o", "an"):
            return "accept"  # Legal precursor characters to binary keyword operation
        if text in ("and", "is", "in", "or"):
            return icon.BinOpIcon(text), None # Binary keyword operation
        if text in ("*", "/", "@", "<", ">", "=", "!"):
            return "accept"  # Legal precursor characters to binary operation
        if text in binaryOperators:
            if text == '/':
                return icon.DivideIcon(floorDiv=False), None
            elif text == '//':
                return icon.DivideIcon(floorDiv=True), None
            return icon.BinOpIcon(text), None
        if text == '(':
            return "makeFunction"  # Make a function from the attached icon
        if text == ',':
            return "comma"
        op = text[:-1]
        delim = text[-1]
        print ('op in binop', op in binaryOperators, 'delim', delim, 'pat match', opDelimPattern.match(delim))
        if op in binaryOperators and opDelimPattern.match(delim):
            # Valid binary operator followed by allowable operand character
            if op == '/':
                return icon.DivideIcon(floorDiv=False), delim
            elif op == '//':
                return icon.DivideIcon(floorDiv=True), delim
            return icon.BinOpIcon(op), delim
        return "reject"
    else:
        # input site
        if text in ('+', '-', '~', "not"):
            # Unary operator
            return icon.UnaryOpIcon(text), None
        if text == '(':
            return icon.FnIcon('('), None  # Temporary stand-in for cursor-paren
        if text == ')':
            return "endParen"
        if text == ',':
            return "comma"
        if identPattern.fullmatch(text) or numPattern.fullmatch(text):
            return "accept"  # Nothing but legal identifier and numeric
        delim = text[-1]
        text = text[:-1]
        if text in ('+', '-', '~', "not") and opDelimPattern.match(delim):
            return icon.UnaryOpIcon(text), delim
        if not (identPattern.fullmatch(text) or numPattern.fullmatch(text)):
            return "reject"  # Precursor characters do not form valid identifier or number
        if len(text) == 0 or delim not in delimitChars:
            return "reject"  # No legal text or not followed by a legal delimiter
        # All but the last character is ok and the last character is a valid delimiter
        if text in ('False', 'None', 'True'):
            return icon.IdIcon(text), delim
        if text in keywords:
            return "reject"
        exprAst = compile_eval.parseExprToAst(text)
        if exprAst is None:
            return "reject"
        if exprAst.__class__ == ast.Name:
            return icon.IdentIcon(exprAst.id), delim
        if exprAst.__class__ == ast.Num:
            return icon.IdentIcon(str(exprAst.n)), delim
        return "reject"

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 192 or 220 <= evt.keycode <= 222:
        return chr(evt.keysym_num)
    return None

def beep():
    # Another platform dependent bit.  tkinter has a .bell() method, but it generates
    # an elaborate sound that's supposed to alert the user of a dialog popping up, which
    # is not appropriate for the tiny nudge for your keystroke being rejected.
    winsound.Beep(1500, 120)

def findTextOffset(text, pixelOffset):
    # We use a proportionally-spaced font, but don't have full access to the font
    # rendering code, so the only tool we have to see how it got laid out is the
    # font.getsize method, which can only answer the question: "how many pixels long is
    # this entire string".  Rather than try to measure individual characters and adjust
    # for kerning and other oddness, this code makes a statistical starting guess and
    # brutally iterates until it finds the right place.
    nChars = len(text)
    if nChars == 0:
        return 0
    textLength = icon.globalFont.getsize(text)[0]
    guessedPos = (nChars * pixelOffset) // textLength
    lastGuess = None
    lastGuessDist = textLength
    while True:
        pixelOfGuess = icon.globalFont.getsize(text[:guessedPos])[0]
        guessDist = abs(pixelOfGuess - pixelOffset)
        if pixelOfGuess > pixelOffset:
            if lastGuess == '<':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '>'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos -= 1
            if guessedPos <= 0:
                return 0 if pixelOffset < guessDist else lastGuessedPos
        elif pixelOfGuess < pixelOffset:
            if lastGuess == '>':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '<'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos += 1
            if guessedPos >= nChars:
                return nChars if textLength - pixelOffset < guessDist else lastGuessedPos
        else:
            return guessedPos

