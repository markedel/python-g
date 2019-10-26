# Copyright Mark Edel  All rights reserved
import icon
import python_g
from PIL import Image, ImageDraw

BLINK_RATE = 500
PEN_BG_COLOR = (235, 255, 235, 255)
RIGHT_LAYOUT_MARGIN = 3

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
        self.layoutDirty = True

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
        textLeft = x + penImage.width + icon.TEXT_MARGIN
        draw.text((textLeft, y + icon.TEXT_MARGIN), self.text, font=icon.globalFont,
         fill=(0, 0, 0, 255))
        nibTop = y + self.outSiteOffset[1] - penImage.height // 2
        image.paste(penImage, box=(x, nibTop), mask=penImage)

    def blinkCursor(self):
        erase = (python_g.msTime() % BLINK_RATE*2) > BLINK_RATE
        # ... finish this later

    def addChar(self, char):
        oldWidth = self._width()
        self.text = self.text + char
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
        return {"output":[(self, x + self.outSiteOffset[0], y + self.outSiteOffset[1])]}

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

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 191 or 220 <= evt.keycode <= 222:
        return chr(evt.keysym_num)
    return None
