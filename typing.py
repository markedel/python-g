# Copyright Mark Edel  All rights reserved
import icon
import python_g
from PIL import Image, ImageDraw

PEN_BG_COLOR = (235, 255, 235, 255)
RIGHT_LAYOUT_MARGIN = 3

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
textCursorImage = Image.new('RGBA', (3, textCursorHeight), color=(255, 255, 255, 255))
textCursorImageDraw = ImageDraw.Draw(textCursorImage)
textCursorImageDraw.line((1, 1, 1, textCursorHeight-2), fill=(0, 0, 0, 255))

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
penOffset = 6
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
attrPenOffset = 5
attrPenImage = icon.asciiToImage(attrPenPixmap)

class EntryIcon(icon.Icon):
    def __init__(self, initialString="", window=None, location=None):
        icon.Icon.__init__(self, window)
        self.text = initialString
        ascent, descent = icon.globalFont.getmetrics()
        self.height = ascent + descent + 2 * icon.TEXT_MARGIN + 1
        self.initTxtWidth = icon.globalFont.getsize("abcDef")[0]
        self.txtWidthIncr = self.initTxtWidth
        x, y = location if location is not None else (0, 0)
        self.rect = (x, y, x + self._width(), y + self.height)
        self.outSiteOffset = (0, self.height // 2)
        self.attrSiteOffset = (0, self.height - 3)
        self.attachedToAttrSite = False
        self.layoutDirty = True
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.cursorPos = len(initialString)

    def _width(self, text=None, boxOnly=False):
        if text is None:
            text = self.text
        textWidth = icon.globalFont.getsize(self.text)[0]
        if textWidth > self.initTxtWidth:
            nIncrements = (textWidth - self.initTxtWidth) // self.initTxtWidth + 1
        else:
            nIncrements = 0
        adjWidth = self.initTxtWidth + nIncrements*self.txtWidthIncr
        boxWidth = adjWidth + 2 * icon.TEXT_MARGIN + 1 + penImage.width - penOffset
        if boxOnly:
            return boxWidth
        return boxWidth + penOffset

    def touchesPosition(self, x, y):
        if not icon.pointInRect((x, y), self.rect):
            return False
        rectLeft, rectTop = self.rect[:2]
        if x > rectLeft + penOffset:
            return True
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
        draw.rectangle((x + penOffset, y, x + penOffset + boxWidth, y + self.height-1),
         fill=PEN_BG_COLOR, outline=icon.OUTLINE_COLOR)
        textLeft = x + self.textOffset
        draw.text((textLeft, y + icon.TEXT_MARGIN), self.text, font=icon.globalFont,
         fill=(0, 0, 0, 255))
        if self.attachedToAttrSite:
            nibTop = y + self.attrSiteOffset - attrPenImage.height
            image.paste(attrPenImage, box=(x, nibTop), mask=attrPenImage)
        else:
            nibTop = y + self.outSiteOffset[1] - penImage.height // 2
            image.paste(penImage, box=(x, nibTop), mask=penImage)

    def addChar(self, char):
        oldWidth = self._width()
        self.text = self.text + char
        self.cursorPos += len(char)
        if self._width() != oldWidth:
            self.layoutDirty = True

    def backspace(self):
        self._setText(self.text[:-1])

    def _setText(self, newText):
        oldWidth = self._width()
        self.text = newText
        if self._width() != oldWidth:
            self.layoutDirty = True

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        return {"output":[(self, (x + self.outSiteOffset[0], y + self.outSiteOffset[1]), 0)]}

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y+self.outSiteOffset[1], self._calcLayout())

    def _doLayout(self, outSiteX, outSiteY, _layouts, parentPrecedence=None):
        width = self._width() + icon.outSiteImage.width - 1
        top = outSiteY - self.height//2
        self.rect = (outSiteX, top, outSiteX + width, top + self.height)

    def _calcLayout(self, parentPrecedence=None):
        width = self._width() - icon.outSiteImage.width + 1 + RIGHT_LAYOUT_MARGIN
        return icon.Layout(self, width, self.height, self.height//2, [])

    def clipboardRepr(self, offset):
        return None


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
