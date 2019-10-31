# Copyright Mark Edel  All rights reserved
import icon
import python_g
import winsound
from PIL import Image, ImageDraw

PEN_BG_COLOR = (255, 245, 245, 255)
PEN_OUTLINE_COLOR = (255, 97, 120, 255)
RIGHT_LAYOUT_MARGIN = 3
PEN_MARGIN = 6

operators = ['+', '-', '*', '**', '/', '//', '%', '@<<', '>>', '&', '|', '^', '~', '<',
 '>', '<=', '>=', '==', '!=']
delimiters = ['(', ')', '[', ']', '{', '},', ':', '.', ';', '@', '=', '->', '+=', '-=',
 '*=', '/=', '//=', '%=', '@=', '&=', '|=', '^=', '>>=', '<<=', '**=']
delimitChars = list(dict.fromkeys("".join(operators + delimiters)))
keywords = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield']

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

    def addChar(self, char):
        newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos + len(char))

    def backspace(self):
        newText = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos-1)

    def _setText(self, newText, newCursorPos):
        oldWidth = self._width()
        self.text = newText
        self.window.cursor.erase()
        self.cursorPos = newCursorPos
        self.window.cursor.draw()
        if self._width() != oldWidth:
            self.layoutDirty = True

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

    def _doLayout(self, outSiteX, outSiteY, layout, parentPrecedence=None):
        width = self._width() + icon.outSiteImage.width - 1
        top = outSiteY - self.height//2
        if self.attachedSite and self.attachedSite[0] == "attrOut":
            top -= icon.ATTR_SITE_OFFSET
            self.textOffset = attrPenImage.width + icon.TEXT_MARGIN
        else:
            self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.rect = (outSiteX, top, outSiteX + width, top + self.height)
        if self.pendingArgument is not None:
            self.pendingArgument._doLayout(outSiteX + width - 5, # Should be lower #???
             outSiteY, layout.subLayouts[0])
        elif self.pendingAttribute is not None:
            self.pendingAttribute._doLayout(outSiteX + width - 5,
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

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect)
            self.lastDrawRect = None

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 191 or 220 <= evt.keycode <= 222:
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
    textLength = icon.globalFont.getsize(text)[0]
    nChars = len(text)
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

