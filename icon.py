from PIL import Image, ImageDraw, ImageFont
from python_g import msTime, AccumRects, offsetRect

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 11)

textMargin = 2
spineThickness = 4
outSiteWidth = 5
iconOutlineColor = (230, 230, 230, 255)
iconBgColor = (255, 255, 255, 255)
selectModColor = (0, 0, 80, 50)

outSitePixmap = (
 "obbbo",
 ".obo.",
 "..o..")
inSitePixmap = (
 "oxxxo",
 "boxob",
 "bbobb")

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
        iconClass, iconData = clipIcon
        try:
            parseMethod = eval(iconClass).fromClipboard
        except:
            continue
        pastedIcons.append(parseMethod(iconData, window, offset))
    return pastedIcons

def clipboardRepr(icons, offset):
    return repr([ic.clipboardRepr(offset) for ic in icons])

def overlayColor(c1, c2):
    r1, g1, b1, a1 = c1
    r2, g2, b2, a2 = c2
    w1 = (255 - a2) / 255.0
    w2 = a2 / 255.0
    return int(r1*w1 + r2*w2), int(g1*w1 + g2*w2), int(b1*w1+b2*w2), a1

iconOutlineSelColor = overlayColor(iconOutlineColor, selectModColor)
iconBgSelColor = overlayColor(iconBgColor, selectModColor)

def asciiToImage(asciiPixmap, selected=False):
    if selected:
        outLineColor = iconOutlineSelColor
        bgColor = iconBgSelColor
    else:
        outLineColor = iconOutlineColor
        bgColor = iconBgColor
    asciiMap = {'.': (0, 0, 0, 0), 'o': outLineColor, 'b': bgColor, 'x': (0, 0, 0, 0)}
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

outSiteImage = asciiToImage(outSitePixmap)
outSiteSelImage = asciiToImage(outSitePixmap, selected=True)
inSiteImage = asciiToImage(inSitePixmap)
inSiteSelImage = asciiToImage(inSitePixmap, selected=True)

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.selected = False
        self.outOffset = (0, 0)
        self.children = []
        self.layoutDirty = False

    def draw(self, image=None, location=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is drawn
         can be optionally overridden by specifying image and/or location."""
        pass

    def layout(self):
        "Compute layout and set locations for icon and its children, but do not redraw"
        pass

    def traverse(self, includeSelf=True):
        "Iterator for traversing the tree below this icon"
        if includeSelf:
            yield self
        for child in self.children:
            yield from child.traverse()

    def hierRect(self):
        "Return a rectangle covering this icon and its children"
        return containingRect(self.traverse())

    def detach(self, child):
        "Remove a child icon"
        self.children.remove(child)
        self.layoutDirty = True

    def addChild(self, child):
        "Add a child icon"
        self.children.append(child)
        self.layoutDirty = True

    def needsLayout(self):
        "Returns True if the icon requires re-layout due to changes to child icons"
        # For the moment need to lay-out propagates all the way to the top of
        # the hierarchy.  Once sequences are introduced.  This will probably
        # stop, there
        for ic in self.traverse():
            if ic.layoutDirty:
                return True

class IdentIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        bodyWidth, bodyHeight = globalFont.getsize(self.name)
        bodyWidth += 2*textMargin
        bodyHeight += 2*textMargin
        self.bodySize = (bodyWidth, bodyHeight)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth, y + bodyHeight + outSiteImage.height)
        self.outSiteOffset = (5, bodyHeight + outSiteImage.height)

    def draw(self, image=None, location=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        drawIconBoxedText(self.name, image, location, self.selected)
        x, y = location
        outImg = outSiteSelImage if self.selected else outSiteImage
        outSiteX, outSiteY = self.outSiteOffset
        outSiteX += x - outImg.width//2
        outSiteY += y - outImg.height -1
        image.paste(outImg, (outSiteX, outSiteY), mask=outImg)

    def layout(self, location=None):
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def _doLayout(self, x, bottom, calculatedSizes=None):
        width, height = self.bodySize
        self.rect = (x, bottom-height, x + width, bottom+outSiteImage.height)

    def _calcLayout(self):
        width, height = rectSize(self.rect)
        return (self, width, height-outSiteImage.height, [])

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.name, addPoints(location, offset)))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        name, location = clipData
        return IdentIcon(name, window, (addPoints(location, locationOffset)))

class FnIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        self.emptyInOffsets = (inSiteImage.width//2 + 1, )
        self.inOffsets = self.emptyInOffsets
        bodyWidth, bodyHeight = globalFont.getsize(self.name)
        self.bodySize = (bodyWidth + 2*textMargin, bodyHeight + 2*textMargin)
        width, height = self._size()
        self.outSiteOffset = (5, height)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        width, height = globalFont.getsize(self.name)
        width += 2*textMargin + self._spineLength(self.inOffsets)
        height += 2*textMargin + outSiteImage.height
        return width, height

    def draw(self, image=None, location=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        width, height = drawIconBoxedText(self.name, image, location, self.selected)
        x, y = location
        self._drawSpine(image, x+width-1, y+height)
        outSiteX, outSiteY = self.outSiteOffset
        outImg = outSiteSelImage if self.selected else outSiteImage
        outSiteX += x - outImg.width//2
        outSiteY += y - outImg.height -1
        image.paste(outImg, (outSiteX, outSiteY), mask=outImg)

    def _spineLength(self, inOffsets):
        return max(inOffsets) + inSiteImage.width // 2 + 2

    def _drawSpine(self, image, x, y):
        spineLength = self._spineLength(self.inOffsets)
        if self.selected:
            bgColor = iconBgSelColor
            outlineColor = iconOutlineSelColor
            inImg = inSiteSelImage
        else:
            bgColor = iconBgColor
            outlineColor = iconOutlineColor
            inImg = inSiteImage
            outImg = outSiteImage
        spineImage = Image.new('RGBA', (spineLength, spineThickness), bgColor)
        draw = ImageDraw.Draw(spineImage)
        draw.line((0, 0, spineLength, 0), fill=outlineColor)
        draw.line((0, spineThickness-1, spineLength, spineThickness-1), fill=outlineColor)
        draw.line((spineLength-1, 0, spineLength-1, spineThickness), fill=outlineColor)
        for inOff in self.inOffsets:
            spineImage.paste(inImg, (inOff - inImg.width // 2, 0))
        image.paste(spineImage, (x, y-spineThickness, x+spineLength, y), mask=spineImage)

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y+self.bodySize[1], self._calcLayout())

    def _doLayout(self, x, bottom, calculatedSizes):
        icn, layoutWidth, layoutHeight, childLayouts = calculatedSizes
        bodyWidth, bodyHeight = self.bodySize
        if len(childLayouts) == 0:
            self.inOffsets = self.emptyInOffsets
        else:
            self.inOffsets = []
            childX = 0
            for childLayout in childLayouts:
                childIcon, childWidth, childHeight, subLayouts = childLayout
                self.inOffsets.append(childX + childIcon.outSiteOffset[0])
                childIcon._doLayout(x+bodyWidth+childX, bottom-spineThickness,
                        childLayout)
                childX += childWidth
        width, height = self._size()
        self.rect = (x, bottom-bodyHeight, x+width, bottom+outSiteImage.height)
        self.layoutDirty = False

    def _calcLayout(self):
        childLayouts = [c._calcLayout() for c in self.children]
        if len(childLayouts) == 0:
            childWidth = self._spineLength(self.emptyInOffsets)
            height = self.bodySize[1]
        else:
            childWidth = sum((c[1] for c in childLayouts))
            height = max((c[2] for c in childLayouts)) + spineThickness
        return (self, self.bodySize[0] + childWidth, height, childLayouts)

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.name, addPoints(location, offset),
         [c.clipboardRepr(offset) for c in self.children]))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        name, location, children = clipData
        ic = FnIcon(name, window, (addPoints(location, offset)))
        ic.children = clipboardDataToIcons(children, window, offset)
        return ic

def drawIconBoxedText(text, image, location, selected):
    if text not in renderCache:
        width, height = globalFont.getsize(text)
        txtImg = Image.new('RGBA', (width+2*textMargin, height+2*textMargin),
         color=iconBgColor)
        draw = ImageDraw.Draw(txtImg)
        draw.text((textMargin, textMargin), text, font=globalFont,
         fill=(0, 0, 0, 255))
        draw.rectangle((0, 0, width+2*textMargin-1, height+2*textMargin-1),
         fill=None, outline=iconOutlineColor)
        renderCache[text] = txtImg
    else:
        txtImg = renderCache[text]
    x, y = location
    textDrawRect = (x, y, x + txtImg.width, y + txtImg.height)
    image.paste(txtImg, textDrawRect)
    if selected:
        selImg = Image.new('RGBA', (txtImg.width, txtImg.height), color=(0, 0, 80, 50))
        image.paste(selImg, textDrawRect, mask=selImg)
    return txtImg.width, txtImg.height

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

def moveRect(rect, newLoc):
    l, t, r, b = rect
    x, y = newLoc
    return(x, y, x+r-l, y+b-t)

def addPoints(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return (x1 + x2, y1 + y2)