# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from python_g import rectsTouch, AccumRects
import math
import operator

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)

binOpPrecedence = {'+':10, '-':10, '*':11, '/':11, '//':11, '%':11, '**':14,
 '<<':9, '>>':9, '|':6, '^':7,'&':8, '@':11, 'and':3, 'or':2}

binOpFn = {'+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv,
 '//':operator.floordiv, '%':operator.mod, '**':operator.pow, '<<':operator.lshift,
 '>>':operator.rshift, '|':operator.or_, '^':operator.xor, '&':operator.and_,
 '@':lambda x,y:x@y, 'and':lambda x,y:x and y, 'or':lambda x,y:x or y}

TEXT_MARGIN = 2
INSERT_SITE_Y_OFFSET = 6
OUTLINE_COLOR = (220, 220, 220, 255)
ICON_BG_COLOR = (255, 255, 255, 255)
SELECT_TINT = (0, 0, 255, 0)
GRAY_75 = (192, 192, 192, 255)
GRAY_50 = (128, 128, 128, 255)
GRAY_25 = (64, 64, 64, 255)
BLACK = (0, 0, 0, 255)

DEPTH_EXPAND = 4

outSitePixmap = (
 "..o",
 ".o ",
 "o  ",
 ".o ",
 "..o")

inSitePixmap = (
 "  o",
 " o.",
 "o..",
 " o.",
 "  o")

leftInSitePixmap = (
    "...o ",
    "..o  ",
    ".o  o",
    "o  o.",
    "o o..",
    "o  o.",
    ".o  o",
    "..o  ",
    "...o ",
)
commaPixmap = (
 "ooooo",
 "o   o",
 "o  o.",
 "o o..",
 "o  o.",
 "o   o",
 "o   o",
 "o % o",
 "o1% o",
 "o21 o",
 "o   o",
 "ooooo",
)

binOutPixmap = (
 "..ooo",
 ".o  o",
 "o   o",
 ".o  o",
 "..ooo",
)

floatInPixmap = (
 "ooo",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "ooo",
)

binLParenPixmap = (
 "..ooooooo",
 "..o     o",
 "..o  32 o",
 "..o 1%  o",
 "..o 32  o",
 "..o %   o",
 ".o 1%  o.",
 "o  2% o..",
 ".o 1%  o.",
 "..o %   o",
 "..o 32  o",
 "..o 1%  o",
 "..o  32 o",
 "..o     o",
 "..ooooooo",
)

binRParenPixmap = (
 "oooooooo",
 "o      o",
 "o 23   o",
 "o  %1  o",
 "o  23  o",
 "o   %  o",
 "o   %1 o",
 "o   %2 o",
 "o   %1 o",
 "o   %  o",
 "o  23  o",
 "o  %1  o",
 "o 23   o",
 "o      o",
 "oooooooo",
)

renderCache = {}

def iconsFromClipboardString(clipString, window, offset):
    try:
        clipData = eval(clipString)
    except:
        return None
    icons = clipboardDataToIcons(clipData, window, offset)
    for ic in icons:
        ic.layout()
    return icons

def clipboardDataToIcons(clipData, window, offset):
    pastedIcons = []
    for clipIcon in clipData:
        if clipIcon is None:
            pastedIcons.append(None)
        else:
            iconClass, iconData = clipIcon
            try:
                parseMethod = eval(iconClass).fromClipboard
            except:
                continue
            pastedIcons.append(parseMethod(iconData, window, offset))
    return pastedIcons

def clipboardRepr(icons, offset):
    return repr([ic.clipboardRepr(offset) for ic in icons])

def asciiToImage(asciiPixmap):
    asciiMap = {'.':(0, 0, 0, 0), 'o':OUTLINE_COLOR, ' ':ICON_BG_COLOR,
     '1':GRAY_25, '2':GRAY_50, '3':GRAY_75, '%':BLACK}
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

def iconBoxedText(text):
    if text in renderCache:
        return renderCache[text]
    width, height = globalFont.getsize(text)
    txtImg = Image.new('RGBA', (width + 2 * TEXT_MARGIN + 1, height + 2 * TEXT_MARGIN + 1),
     color=ICON_BG_COLOR)
    draw = ImageDraw.Draw(txtImg)
    draw.text((TEXT_MARGIN, TEXT_MARGIN), text, font=globalFont,
     fill=(0, 0, 0, 255))
    draw.rectangle((0, 0, width + 2 * TEXT_MARGIN, height + 2 * TEXT_MARGIN),
     fill=None, outline=OUTLINE_COLOR)
    renderCache[text] = txtImg
    return txtImg

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)
leftInSiteImage = asciiToImage(leftInSitePixmap)
commaImage = asciiToImage(commaPixmap)
parenImage = iconBoxedText(')')
binOutImage = asciiToImage(binOutPixmap)
floatInImage = asciiToImage(floatInPixmap)
lParenImage = asciiToImage(binLParenPixmap)
rParenImage = asciiToImage(binRParenPixmap)

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.selected = False
        self.layoutDirty = False
        self.cachedImage = None

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is
         drawn can be optionally overridden by specifying image and/or location."""
        pass

    def layout(self):
        """Compute layout and set locations for icon and its children, but do not redraw"""
        pass

    def traverse(self, order="draw", includeSelf=True):
        """Iterator for traversing the tree below this icon.  Traversal can be in either
        drawing (order="draw") or picking (order="pick") order."""
        if includeSelf and order is not "pick":
            yield self
        # For "pick" order to be the true opposite of "draw", this loop should run in
        # reverse, but child icons are not intended to overlap in a detectable way.
        for child in self.children():
            yield from child.traverse(order)
        if includeSelf and order is "pick":
            yield self

    def touchesPosition(self, x, y):
        # ... reevaluate whether it is always best to cache the whole image when
        #     we're drawing little bits of fully-overlapped icons
        if not pointInRect((x, y), self.rect) or self.cachedImage is None:
            return False
        l, t = self.rect[:2]
        pixel = self.cachedImage.getpixel((x-l, y-t))
        return pixel[3] > 128

    def touchesRect(self, rect):
        return rectsTouch(self.rect, rect)

    def hierRect(self):
        """Return a rectangle covering this icon and its children"""
        return containingRect(self.traverse())

    def needsLayout(self):
        """Returns True if the icon requires re-layout due to changes to child icons"""
        # For the moment need to lay-out propagates all the way to the top of
        # the hierarchy.  Once sequences are introduced.  This will probably
        # stop, there
        for ic in self.traverse():
            if ic.layoutDirty:
                return True

    def children(self):
        return []

    def becomeTopLevel(self):
        pass  # Most icons look exactly the same at the top level

class IdentIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        bodyWidth, bodyHeight = globalFont.getsize(self.name)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)
        self.outSiteOffset = (0, bodyHeight // 2)
        self.attrSiteOffset = (bodyWidth, bodyHeight - 3)
        self.attrIcon = None

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.name)
            self.cachedImage.paste(txtImg, (outSiteImage.width-1, 0))
            outSiteX, outSiteY = self.outSiteOffset
            outSiteY -= outSiteImage.height // 2
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected),
         location, clip)

    def children(self):
        if self.attrIcon:
            return [self.attrIcon]
        return []

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        outSite = (self, (x + self.outSiteOffset[0], y + self.outSiteOffset[1]), 0)
        attrOutSite = (self, (x + self.attrSiteOffset[0], y + self.attrSiteOffset[1]), 0)
        return {"output":[outSite], "attrOut":[attrOutSite]}

    def layout(self, location=None):
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def _doLayout(self, outSiteX, outSiteY, _layouts, parentPrecedence=None):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height//2
        self.rect = (outSiteX, top, outSiteX + width, top + height)

    def _calcLayout(self, parentPrecedence=None):
        width, height = self.bodySize
        return Layout(self, width, height, height//2, [])

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return self.__class__.__name__, (self.name, addPoints(location, offset))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        name, location = clipData
        return IdentIcon(name, window, (addPoints(location, locationOffset)))

    def execute(self):
        # Until this icon gets more specific about what it holds
        return eval(self.name)

class FnIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        self.argIcons = []
        self.emptyInOffsets = (0, 6)
        self.inOffsets = self.emptyInOffsets
        bodyWidth, bodyHeight = globalFont.getsize(self.name + '(')
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        closeWidth, closeHeight = globalFont.getsize(')')
        self.closeParenWidth = closeWidth + 2 * TEXT_MARGIN + 1
        self.outSiteOffset = (0, bodyHeight // 2)
        x, y = (0, 0) if location is None else location
        width, height = self._size()
        self.rect = (x, y, x + width, y + height)
        self.attrSiteOffset = (width-1, height - 3)
        self.attrIcon = None

    def _size(self):
        width, height = self.bodySize
        width += self.inOffsets[-1] + parenImage.width
        return width, height

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', self._size(), color=(0, 0, 0, 0))
            # Body
            txtImg = iconBoxedText(self.name + '(')
            self.cachedImage.paste(txtImg, (outSiteImage.width-1, 0))
            # Output site
            outSiteX, siteY = self.outSiteOffset
            outSiteY = siteY - outSiteImage.height // 2
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
            # Body input site
            inSiteX = outSiteImage.width-1 + txtImg.width - inSiteImage.width
            inSiteY = siteY - inSiteImage.height // 2
            self.cachedImage.paste(inSiteImage, (inSiteX, inSiteY))
            # Commas
            commaXOffset = inSiteX + inSiteImage.width - commaImage.width
            commaY = siteY + txtImg.height//2 - commaImage.height
            for inOff in self.inOffsets[1:-1]:
                self.cachedImage.paste(commaImage, (inOff + commaXOffset, commaY))
            # End paren
            parenY = siteY - parenImage.height//2
            parenX = inSiteX + self.inOffsets[-1] + inSiteImage.width - 1
            self.cachedImage.paste(parenImage, (parenX, parenY))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected),
         location, clip)  # ... try w/o mask

    def children(self):
        if self.attrIcon:
            return self.argIcons + [self.attrIcon]
        return self.argIcons

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        outSite = (self, (x + self.outSiteOffset[0], y + self.outSiteOffset[1]), 0)
        width, height = self.bodySize
        x += width + outSiteImage.width - 1 - inSiteImage.width
        y += height // 2
        inSites = []
        for i, child in enumerate(self.argIcons):
            xOff = self.inOffsets[i]
            snapListEntry = (self, (x + xOff, y), i)
            inSites.append(giveInputSiteToBinOpChild(child, snapListEntry))
        insertSites = []
        if len(self.argIcons) == 0:
            insertSites.append((self, (x, y), 0))
        else:
            for i, inOff in enumerate(self.inOffsets):
                insertSites.append((self, (x + inOff, y + INSERT_SITE_Y_OFFSET), i))
        attrOutSite = (self, (x + self.attrSiteOffset[0], y + self.attrSiteOffset[1]), 0)
        return {"output":[outSite], "input":inSites, "attrOut":[attrOutSite],
         "insertInput":insertSites}

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        # If the rectangle is entirely contained within the argument space (ignoring
        # commas), then we will call it not touching
        bodyRight = self.rect[0] + self.bodySize[0]
        return not rectWithinXBounds(rect, bodyRight, bodyRight + self.inOffsets[-1])

    def insertChildren(self, children, site):
        """Insert one or more child icons at the specified site"""
        siteType, siteIndex = site
        if siteType in ("input", "insertInput"):
            self.argIcons[siteIndex:siteIndex] = children
        self.layoutDirty = True

    def replaceChild(self, newChild, site):
        siteType, siteIndex = site
        if siteType == "input":
            self.argIcons[siteIndex] = newChild
        elif siteType == "attrOut":
            self.attrIcon = newChild
        self.layoutDirty = True

    def childAt(self, site):
        siteType, siteIndex = site
        if siteType == "input":
            if siteIndex < len(self.argIcons):
                return self.argIcons[siteIndex]
        elif siteType == "attrOut" and siteIndex == 0:
            return self.attrIcon
        return None

    def siteOf(self, child):
        for i, a in enumerate(self.argIcons):
            if a is child:
                return ("input", i)
        if child is self.attrIcon:
            return ("attrOut", 0)
        return None

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y+self.bodySize[1] // 2, self._calcLayout())

    def _doLayout(self, outSiteX, outSiteY, layout, parentPrecedence=None):
        bodyWidth, bodyHeight = self.bodySize
        if len(layout.subLayouts) == 0:
            self.inOffsets = self.emptyInOffsets
        else:
            self.inOffsets = []
            childXOffset = outSiteX + bodyWidth + outSiteImage.width-1 - inSiteImage.width
            childX = 0
            for childLayout in layout.subLayouts:
                self.inOffsets.append(childX)
                childLayout.icon._doLayout(childXOffset + childX, outSiteY, childLayout)
                childX += childLayout.width-1 + commaImage.width-1
            self.inOffsets.append(childX - (commaImage.width-1))
        width, height = self._size()
        self.outSiteOffset = (0, bodyHeight // 2)
        x = outSiteX
        y = outSiteY - self.outSiteOffset[1]
        self.rect = (x, y, x+width, y+height)
        self.cachedImage = None
        self.layoutDirty = False

    def _calcLayout(self, parentPrecedence=None):
        childLayouts = [c._calcLayout() for c in self.argIcons]
        bodyWidth, bodyHeight = self.bodySize
        if len(childLayouts) == 0:
            childWidth = self.emptyInOffsets[-1] + parenImage.width
            height = bodyHeight
        else:
            numCommas = len(childLayouts) - 2
            commaParenWidth = numCommas*(commaImage.width-1) + parenImage.width-1
            childWidth = sum((c.width-1 for c in childLayouts)) + commaParenWidth
            height = max(bodyHeight, max((c.height for c in childLayouts)))
        width = self.bodySize[0] + outSiteImage.width + childWidth
        return Layout(self, width, height, height//2, childLayouts)

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.name, addPoints(location, offset),
         [c.clipboardRepr(offset) for c in self.argIcons]))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        name, location, children = clipData
        ic = FnIcon(name, window, (addPoints(location, offset)))
        ic.argIcons = clipboardDataToIcons(children, window, offset)
        return ic

    def execute(self):
        argValues = [c.execute() for c in self.children()]
        return getattr(math, self.name)(*argValues)

class BinOpIcon(Icon):
    def __init__(self, operator, window=None, location=None):
        Icon.__init__(self, window)
        self.operator = operator
        self.precedence = binOpPrecedence[operator]
        self.hasParens = False  # Filled in by layout methods
        self.leftArg = None
        self.rightArg = None
        self.emptyArgWidth = 11
        self.leftArgWidth = self.emptyArgWidth
        self.rightArgWidth = self.emptyArgWidth
        opWidth, opHeight = globalFont.getsize(self.operator)
        opHeight = max(opHeight + 2*TEXT_MARGIN + 1, lParenImage.height)
        opWidth += 2*TEXT_MARGIN - 1
        self.opSize = (opWidth, opHeight)
        self.depthWidth = 0
        self.rect = (0, 0, *self._size())
        self.outSiteOffset = (0, opHeight // 2)
        self.leftSiteDrawn = False

    def _size(self):
        opWidth, opHeight = self.opSize
        opWidth += self.depthWidth
        if self.hasParens:
            parenWidth = lParenImage.width - 1 + rParenImage.width - 1
        else:
            parenWidth = 0
        width = parenWidth + self.leftArgWidth + self.rightArgWidth + opWidth
        return width, opHeight

    def draw(self, image=None, location=None, clip=None):
        cachedImage = self.cachedImage
        temporaryOutputSite = False
        if image is not None and self.leftSiteDrawn:
            # When image is specified the icon is being dragged, and it must display
            # something indicating where its output site is
            cachedImage = None
            self.cachedImage = None
            temporaryOutputSite = True
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if cachedImage is None:
            cachedImage = Image.new('RGBA', self._size(), color=(0, 0, 0, 0))
            # Output part (connector or paren)
            outSiteX, siteY = self.outSiteOffset
            leftArgX = outSiteX + outSiteImage.width - 1
            if self.hasParens:
                outSiteY = siteY - lParenImage.height // 2
                cachedImage.paste(lParenImage, (outSiteX, outSiteY), mask=lParenImage)
                leftArgX = outSiteX + lParenImage.width - 1
            elif temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                cachedImage.paste(binOutImage, (outSiteX, outSiteY), mask=binOutImage)
            elif self.leftSiteDrawn:
                outSiteY = siteY - floatInImage.height // 2
                cachedImage.paste(floatInImage, (outSiteX, outSiteY), mask=floatInImage)
            # Body
            txtImg = iconBoxedText(self.operator)
            opX = leftArgX + self.leftArgWidth - 1
            opY = siteY - txtImg.height // 2
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(cachedImage)
                opWidth = txtImg.width + self.depthWidth
                draw.rectangle((opX, opY, opX+opWidth-1, opY+txtImg.height-1),
                 outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
                txtSubImg = txtImg.crop((1, 0, txtImg.width-1, txtImg.height))
                cachedImage.paste(txtSubImg, (opX + self.depthWidth//2 + 1, opY))
            else:
                opWidth = txtImg.width
                cachedImage.paste(txtImg, (opX + self.depthWidth//2, opY))
            rInSiteX = opX + opWidth - inSiteImage.width
            rInSiteY = siteY - inSiteImage.height // 2
            cachedImage.paste(inSiteImage, (rInSiteX, rInSiteY))
            # End paren
            if self.hasParens:
                rParenX = opX + opWidth - 1 + self.rightArgWidth - 1
                rParenY = siteY - rParenImage.height//2
                cachedImage.paste(rParenImage, (rParenX, rParenY))
        pasteImageWithClip(image, tintSelectedImage(cachedImage, self.selected),
         location, clip)
        if not temporaryOutputSite:
            self.cachedImage = cachedImage

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        leftArgLeft = self.rect[0] + self.outSiteOffset[0] + outSiteImage.width - 1
        opWidth = self.opSize[0] + self.depthWidth
        if self.hasParens:
            # If rectangle passes vertically within one of the argument slots, it is
            # considered to not be touching
            leftArgLeft += lParenImage.width
            leftArgRight = leftArgLeft + self.leftArgWidth - 1
            if rectWithinXBounds(rect, leftArgLeft, leftArgRight):
                return False
            rightArgLeft = leftArgRight + opWidth
            rightArgRight = rightArgLeft + self.rightArgWidth - 1
            if rectWithinXBounds(rect, rightArgLeft, rightArgRight):
                return False
        else:
            # If the rectangle is entirely left of or right of the icon body, it is
            # considered not touching
            bodyLeft = leftArgLeft + self.leftArgWidth - 1
            bodyRight = bodyLeft + opWidth
            rectLeft, rectTop, rectRight, rectBottom = rect
            if rectRight < bodyLeft or rectLeft > bodyRight:
                return False
        return True

    def becomeTopLevel(self):
        # When a BinOpIcon is dropped it can become a top level icon, which may mean it
        # needs to have its's left site restored.
        if not self.leftSiteDrawn:
            self.leftSiteDrawn = True
            self.cachedImage = None
        if self.hasParens:
            self.hasParens = False
            self.layoutDirty = True

    def children(self):
        return [arg for arg in (self.rightArg, self.leftArg) if arg is not None]

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        y += self.outSiteOffset[1]
        outSite = (self, (x + self.outSiteOffset[0], y), 0)
        bodyX = x + self.leftArgWidth - 1
        if self.hasParens:
            lArgX = x + lParenImage.width - inSiteImage.width
            bodyX += lParenImage.width - 1
        else:
            lArgX = x
            bodyX += 1
        rArgX = bodyX + self.opSize[0] + self.depthWidth
        inSites = []
        if self.hasParens or self.leftArg is None or atTop:
            snapEntry = (self, (lArgX, y), 0)
            inSites.append(giveInputSiteToBinOpChild(self.leftArg, snapEntry))
        snapEntry = (self, (rArgX, y), 1)
        inSites.append(giveInputSiteToBinOpChild(self.rightArg, snapEntry))
        return {"output":[outSite], "input":inSites}

    def replaceChild(self, newChild, site):
        siteType, siteIndex = site
        if siteType == "input":
            if siteIndex == 0:
                self.leftArg = newChild
            else:
                self.rightArg = newChild
        self.layoutDirty = True

    def childAt(self, site):
        siteType, siteIndex = site
        if siteType == "input":
            if siteIndex == 0:
                return self.leftArg
            elif siteIndex == 1:
                return self.rightArg
        return None

    def siteOf(self, child):
        if child is self.leftArg:
           return ("input", 0)
        elif child is self.rightArg:
            return ("input", 1)
        return None

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y + self.opSize[1] // 2, self._calcLayout())
        # Layout is called only on the top-level icon.  Ensure left site is drawn
        self.leftSiteDrawn = True

    def _doLayout(self, outSiteX, outSiteY, layout, parentPrecedence=None):
        if parentPrecedence is None:
            self.hasParens = False
        else:
            self.hasParens = self.precedence < parentPrecedence
        lArgLayout, rArgLayout = layout.subLayouts
        if self.hasParens:
            lArgX = outSiteX + lParenImage.width - outSiteImage.width
        else:
            lArgX = outSiteX
        if lArgLayout is None:
            self.leftArgWidth = self.emptyArgWidth
            lDepth = 0
        else:
            self.leftArgWidth = lArgLayout.width
            lArgLayout.icon._doLayout(lArgX, outSiteY, lArgLayout,
             parentPrecedence=self.precedence)
            lDepth = lArgLayout.exprDepth
        if rArgLayout is None:
            self.rightArgWidth = self.emptyArgWidth
            self.depthWidth = lDepth * DEPTH_EXPAND
        else:
            self.depthWidth = max(lDepth, rArgLayout.exprDepth) * DEPTH_EXPAND
            self.rightArgWidth = rArgLayout.width
            rArgX = lArgX + self.leftArgWidth + self.opSize[0] + self.depthWidth
            rArgLayout.icon._doLayout(rArgX, outSiteY, rArgLayout,
             parentPrecedence=self.precedence)
        width, height = self._size()
        self.outSiteOffset = (0, height // 2)
        x = outSiteX
        y = outSiteY - self.outSiteOffset[1]
        self.rect = (x, y, x+width, y+height)
        self.leftSiteDrawn = False # self.layout will reset on top-level icon
        self.cachedImage = None
        self.layoutDirty = False

    def _calcLayout(self, parentPrecedence=None):
        if parentPrecedence is None:
            hasParens = False
        else:
            hasParens = self.precedence < parentPrecedence
        if self.leftArg is None:
            lArgLayout = None
            lArgWidth, lArgHeight = (self.emptyArgWidth, 0)
            lArgYSiteOff = self.opSize[1] // 2
            lDepth = 0
        else:
            lArgLayout = self.leftArg._calcLayout(parentPrecedence=self.precedence)
            lArgWidth = lArgLayout.width
            lArgHeight = lArgLayout.height
            lArgYSiteOff = lArgLayout.siteOffset
            lDepth = lArgLayout.exprDepth
        if self.rightArg is None:
            rArgLayout = None
            rArgWidth, rArgHeight = (self.emptyArgWidth, 0)
            rArgYSiteOff = self.opSize[1] // 2
            rDepth = 0
        else:
            rArgLayout = self.rightArg._calcLayout(parentPrecedence=self.precedence)
            rArgWidth = rArgLayout.width
            rArgHeight = rArgLayout.height
            rArgYSiteOff = rArgLayout.siteOffset
            rDepth = rArgLayout.exprDepth
        opWidth, opHeight = self.opSize
        if hasParens:
            parenWidth = lParenImage.width - 2 + rParenImage.width - 2
        else:
            parenWidth = 0
        depth = max(lDepth, rDepth)
        depthWidth = depth * DEPTH_EXPAND
        width = parenWidth + lArgWidth + rArgWidth + opWidth + depthWidth
        depth += 1
        height = max(lArgHeight, rArgHeight, opHeight)
        siteYOff = max(lArgYSiteOff, rArgYSiteOff)
        return Layout(self, width, height, siteYOff, (lArgLayout, rArgLayout), depth)

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.operator, addPoints(location, offset),
         (None if self.leftArg is None else self.leftArg.clipboardRepr(offset),
          None if self.rightArg is None else self.rightArg.clipboardRepr(offset))))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        op, location, children = clipData
        ic = BinOpIcon(op, window, (addPoints(location, offset)))
        ic.leftArg, ic.rightArg = clipboardDataToIcons(children, window, offset)
        return ic

    def locIsOnLeftParen(self, btnPressLoc):
        iconLeft = self.rect[0]
        return iconLeft < btnPressLoc[0] < iconLeft + lParenImage.width

    def execute(self):
        leftValue = self.leftArg.execute()
        rightValue = self.rightArg.execute()
        return binOpFn[self.operator](leftValue, rightValue)

class DivideIcon(Icon):
    def __init__(self, window=None, location=None, floorDiv=False):
        Icon.__init__(self, window)
        self.precedence = 11
        self.topArg = None
        self.bottomArg = None
        self.floorDiv = floorDiv
        emptyArgWidth = 11
        emptyArgHeight = 14
        self.emptyArgSize = (emptyArgWidth, emptyArgHeight)
        self.topArgSize = self.emptyArgSize
        self.topArgSiteOffset = (2, -emptyArgHeight // 2 - 2)
        self.bottomArgSize = self.emptyArgSize
        self.bottomArgSiteOffset = (2, emptyArgHeight // 2 + 2)
        width, height = self._size()
        x, y = location
        self.rect = (x, y, x + width, y + height)
        self.outSiteOffset = (0, self.topArgSize[1] + 2)
        self.attrSiteOffset = (width-1, height - 3)
        self.attrIcon = None

    def _size(self):
        topWidth, topHeight = self.topArgSize
        bottomWidth, bottomHeight = self.bottomArgSize
        width = max(topWidth, bottomWidth) + 3 + outSiteImage.width
        height = topHeight + bottomHeight + 3
        return width, height

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            width, height = self._size()
            self.cachedImage = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
            # Input sites
            leftX, cntrY = self.outSiteOffset
            topArgX, topArgY = self.topArgSiteOffset
            topArgX += leftX
            topArgY += cntrY - floatInImage.height // 2
            self.cachedImage.paste(floatInImage, (topArgX, topArgY))
            bottomArgX, bottomArgY = self.bottomArgSiteOffset
            bottomArgX += leftX
            bottomArgY += cntrY - floatInImage.height // 2
            self.cachedImage.paste(floatInImage, (bottomArgX, bottomArgY))
            # Body
            bodyLeft = outSiteImage.width - 1
            bodyRight = width - 1
            bodyTop = cntrY - 5
            bodyBottom = cntrY + 5
            draw = ImageDraw.Draw(self.cachedImage)
            draw.rectangle((bodyLeft, bodyTop, bodyRight, bodyBottom),
             outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
            draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            self.cachedImage.paste(outSiteImage, (leftX, cntrY - outSiteImage.height//2))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected),
         location, clip)  # ... try w/o mask

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        # If rectangle passes horizontally above or below the central body of the icon,
        # it is considered to not be touching
        rectLeft, rectTop, rectRight, rectBottom = rect
        centerY = self.rect[1] + self.outSiteOffset[1]
        iconTop = centerY - 5
        iconBottom = centerY + 5
        if rectBottom < iconTop or rectTop > iconBottom:
            return False
        return True

    def children(self):
        return [arg for arg in (self.topArg, self.bottomArg, self.attrIcon) if arg is not None]

    def snapLists(self, atTop=False):
        x, y = self.rect[:2]
        y += self.outSiteOffset[1]
        outSite = (self, (x + self.outSiteOffset[0], y), 0)
        topArgX = x + self.topArgSiteOffset[0]
        topArgY = y + self.topArgSiteOffset[1]
        topArgSnapEntry = (self, (topArgX, topArgY), 0)
        bottomArgX = x + self.bottomArgSiteOffset[0]
        bottomArgY = y + self.bottomArgSiteOffset[1]
        bottomArgSnapEntry = (self, (bottomArgX, bottomArgY), 1)
        inSites = [giveInputSiteToBinOpChild(self.topArg, topArgSnapEntry),
          giveInputSiteToBinOpChild(self.bottomArg, bottomArgSnapEntry)]
        attrOutSite = (self, (x + self.attrSiteOffset[0], y + self.attrSiteOffset[1]), 0)
        return {"output":[outSite], "input":inSites, "attrOut":[attrOutSite]}

    def replaceChild(self, newChild, site):
        "Add or replace a child icon"
        siteType, siteIndex = site
        if siteType == "input":
            if siteIndex == 0:
                self.topArg = newChild
            else:
                self.bottomArg = newChild
        elif siteType == "attrOut":
            self.attrIcon = newChild
        self.layoutDirty = True

    def childAt(self, site):
        siteType, siteIndex = site
        if siteType == "input":
            if siteIndex == 0:
                return self.topArg
            elif siteIndex == 1:
                return self.bottomArg
        elif siteType == "attrOut" and siteIndex == 0:
            return self.attrIcon
        return None

    def siteOf(self, child):
        if child is self.topArg:
           return ("input", 0)
        elif child is self.bottomArg:
            return ("input", 1)
        elif child is self.attrIcon:
            return ("attrOut", 0)
        return None

    # ... not sure using old top left is the best way to determine where to place
    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y + self.topArgSize[1] + 2, self._calcLayout())

    def _doLayout(self, outSiteX, outSiteY, layout, parentPrecedence=None):
        width = layout.width + 2
        tArgLayout, bArgLayout = layout.subLayouts
        emptyArgWidth, emptyArgHeight = self.emptyArgSize
        if tArgLayout is None:
            self.topArgSize = self.emptyArgSize
            self.topArgSiteOffset = ((width-emptyArgWidth)//2, -emptyArgHeight//2 - 2)
        else:
             self.topArgSize = (tArgLayout.width, tArgLayout.height)
             self.topArgSiteOffset = ((width - 2 - tArgLayout.width)//2,
              - tArgLayout.height + tArgLayout.siteOffset - 1)
        if bArgLayout is None:
            self.bottomArgSize = self.emptyArgSize
            self.bottomArgSiteOffset = ((width-emptyArgWidth)//2, emptyArgHeight//2 + 2)
        else:
            self.bottomArgSize = (bArgLayout.width, bArgLayout.height)
            self.bottomArgSiteOffset = ((width - 2 - bArgLayout.width)//2,
             bArgLayout.siteOffset + 2)
        self.outSiteOffset = (0, self.topArgSize[1] + 2)
        width, height = self._size()
        x = outSiteX
        y = outSiteY - self.outSiteOffset[1]
        self.rect = (x, y, x+width, y+height)
        cntrX = outSiteX + (width - outSiteImage.width) // 2 + outSiteImage.width
        if tArgLayout is not None:
            topArgX, topArgY = self.topArgSiteOffset
            tArgLayout.icon._doLayout(outSiteX + topArgX, outSiteY + topArgY, tArgLayout)
        if bArgLayout is not None:
            bottomArgX, bottomArgY = self.bottomArgSiteOffset
            bArgLayout.icon._doLayout(outSiteX + bottomArgX, outSiteY + bottomArgY,
             bArgLayout)
        self.cachedImage = None
        self.layoutDirty = False

    def _calcLayout(self, parentPrecedence=None):
        if self.topArg is None:
            tArgLayout = None
            tArgWidth, tArgHeight = self.emptyArgSize
        else:
            tArgLayout = self.topArg._calcLayout()
            tArgWidth = tArgLayout.width
            tArgHeight = tArgLayout.height
        if self.bottomArg is None:
            bArgLayout = None
            bArgWidth, bArgHeight = self.emptyArgSize
        else:
            bArgLayout = self.bottomArg._calcLayout()
            bArgWidth = bArgLayout.width
            bArgHeight = bArgLayout.height
        width = max(tArgWidth, bArgWidth) + 4
        height = tArgHeight + bArgHeight + 2
        return Layout(self, width, height, tArgHeight + 1, (tArgLayout, bArgLayout))

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (addPoints(location, offset),
         (None if self.topArg is None else self.topArg.clipboardRepr(offset),
          None if self.bottomArg is None else self.bottomArg.clipboardRepr(offset))))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location, children = clipData
        ic = DivideIcon(window, (addPoints(location, offset)))
        ic.leftArg, ic.rightArg = clipboardDataToIcons(children, window, offset)
        return ic

    def execute(self):
        topValue = self.topArg.execute()
        bottomValue = self.bottomArg.execute()
        if self.floorDiv:
            return operator.floordiv(topValue, bottomValue)
        else:
            return operator.truediv(topValue, bottomValue)

class ImageIcon(Icon):
    def __init__(self, image, window=None, location=None):
        Icon.__init__(self, window)
        self.cachedImage = self.image = image.convert('RGBA')
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + image.width, y + image.height)

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        pasteImageWithClip(image, tintSelectedImage(self.image, self.selected),
         location, clip)

    def snapLists(self, atTop=False):
        return {}

    def layout(self, location=None):
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def _doLayout(self, x, bottom, _layout, parentPrecedence=None):
        self.rect = (x, bottom-self.image.height, x + self.image.width, bottom)

    def _calcLayout(self, parentPrecedence=None):
        return Layout(self, self.image.width, self.image.height, 0, [])

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        # ... base64 encode a jpeg
        return "IdentIcon", ("TODO", addPoints(location, offset))

    @staticmethod
    def fromClipboard(_clipData, _window, _locationOffset):
        # ... base64 decode a jpeg
        # image, location = clipData
        return None

    def execute(self):
        return None

class Layout:
    def __init__(self, ico, width, height, siteOffset, subLayouts, exprDepth=0):
        self.icon = ico
        self.width = width
        self.height = height
        self.siteOffset = siteOffset
        self.subLayouts = subLayouts
        self.exprDepth = exprDepth

def pasteImageWithClip(dstImage, srcImage, pos, clipRect):
    """clipping rectangle is in the coordinate system of the destination image"""
    if clipRect is None:
        dstImage.paste(srcImage, box=pos, mask=srcImage)
        return
    cl, ct, cr, cb = clipRect
    pl, pt = pos
    pr, pb = pl + srcImage.width, pt + srcImage.height
    # Pasted region is entirely outside of the clip rectangle
    if cl > pr or pl > cr or ct > pb or pt > cb:
        return
    # Pasted region is entirely inside of the clip rectangle
    if pl >= cl and pr <= cr and pt >= ct and pb <= cb:
        dstImage.paste(srcImage, box=pos, mask=srcImage)
        return
    # Find the area that will be drawn
    dl = max(pl, cl)
    dt = max(pt, ct)
    dr = min(pr, cr)
    db = min(pb, cb)
    # Crop the pasted image to the drawn area transformed to its coordinates
    croppedImage = srcImage.crop((dl - pl, dt - pt, dr - pl, db - pt))
    # Paste the cropped image in the drawn area
    dstImage.paste(croppedImage, box=(dl, dt), mask=croppedImage)

def tintSelectedImage(image, selected):
    if not selected:
        return image
    # ... This is wasteful and should be an image filter if I can figure out how to
    # make one properly
    alphaImg = image.getchannel('A')
    colorImg = Image.new('RGBA', (image.width, image.height), color=SELECT_TINT)
    colorImg.putalpha(alphaImg)
    selImg = Image.blend(image, colorImg, .15)
    return selImg

def findLeftOuterIcon(clickedIcon, fromIcon, btnPressLoc=None):
    """Because we have icons with no pickable structure left of their arguments (binary
    operations), we have to make rules about what it means to click or drag the leftmost
    icon in an expression.  For the purpose of selection, that is simply the icon that was
    clicked.  For dragging and double clicking (execution), this function finds the
    outermost operation that claims the clicked icon as its leftmost operand."""
    if btnPressLoc is not None:
        # One idiotic case we have to distinguish, is when the clicked icon is a BinOpIcon
        # with automatic parens visible: only if the user clicked on the left paren, can
        # the icon be the leftmost object in an expression.  Clicking on the body or the
        # right paren does not count.
        if clickedIcon.__class__ is BinOpIcon and clickedIcon.hasParens:
            if not clickedIcon.locIsOnLeftParen(btnPressLoc):
                return clickedIcon
    if clickedIcon is fromIcon:
        return clickedIcon
    # Only binary operations are candidates, and only when the expression directly below
    # has claimed itself to be the leftmost operand of an expression
    if fromIcon.__class__ is BinOpIcon and fromIcon.leftArg is not None and not fromIcon.hasParens:
        left = findLeftOuterIcon(clickedIcon, fromIcon.leftArg)
        if left is fromIcon.leftArg:
            targetIsBinOpIcon = clickedIcon.__class__ is BinOpIcon
            if not targetIsBinOpIcon or targetIsBinOpIcon and clickedIcon.hasParens:
                return fromIcon  # Claim outermost status for this icon
        # Pass on status from non-contiguous expressions below fromIcon in the hierarchy
        if left is not None:
            return left
        if fromIcon.rightArg is None:
            return None
        return findLeftOuterIcon(clickedIcon, fromIcon.rightArg)
    # Pass on any results from below fromIcon in the hierarchy
    children = fromIcon.children()
    if children is not None:
        for child in fromIcon.children():
            result = findLeftOuterIcon(clickedIcon, child)
            if result is not None:
                return result
    return None

def giveInputSiteToBinOpChild(child, snapListEntry):
    parent, pos, site = snapListEntry
    if child is None or child.__class__ is not BinOpIcon or child.hasParens:
        # child is empty or pick-able on the left
        return snapListEntry
    childLeft = child.leftArg
    if childLeft is None or childLeft.__class__ is not BinOpIcon:
        # Give the site to the child, but can't go further
        return (child, pos, 0)
    # Try to pass the site even further down
    return giveInputSiteToBinOpChild(childLeft, (child, pos, 0))

def containingRect(icons):
    maxRect = AccumRects()
    for ic in icons:
        maxRect.add(ic.rect)
    return maxRect.get()

def rectWidth(rect):
    return rect[2] - rect[0]

def rectHeight(rect):
    return rect[3] - rect[1]

def rectSize(rect):
    l, t, r, b = rect
    return r - l, b - t

def pointInRect(point, rect):
    l, t, r, b = rect
    x, y = point
    return l <= x < r and t <= y < b

def moveRect(rect, newLoc):
    l, t, r, b = rect
    x, y = newLoc
    return x, y, x + r - l, y + b - t

def addPoints(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return x1 + x2, y1 + y2

def rectWithinXBounds(rect, leftBound, rightBound):
    left, top, right, bottom = rect
    return left > leftBound and right < rightBound