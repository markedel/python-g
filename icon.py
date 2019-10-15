from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from python_g import msTime, AccumRects, offsetRect

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)

textMargin = 2
spineThickness = 4
outSiteWidth = 5
iconOutlineColor = (180, 180, 180, 255)
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

def asciiToImage(asciiPixmap, selected=False):
    asciiMap = {'.': (0, 0, 0, 0), 'o': iconOutlineColor, 'b': iconBgColor, 'x': (0, 0, 0, 0)}
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.selected = False
        self.children = []
        self.layoutDirty = False
        self.cachedImage = None

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is drawn
         can be optionally overridden by specifying image and/or location."""
        pass

    def layout(self):
        "Compute layout and set locations for icon and its children, but do not redraw"
        pass

    def traverse(self, order="draw", includeSelf=True):
        """Iterator for traversing the tree below this icon.  Traversal can be in either
        drawing (order="draw") or picking (order="pick") order."""
        if includeSelf and order is not "pick":
            yield self
        # For "pick" order to be the true opposite of "draw", this loop should run in
        # reverse, but child icons are not intended to overlap in a detectable way.
        for child in self.children:
            yield from child.traverse(order)
        if includeSelf and order is "pick":
            yield self

    def touchesPosition(self, x, y):
        if not pointInRect((x, y), self.rect) or self.cachedImage is None:
            return False
        l, t = self.rect[:2]
        pixel = self.cachedImage.getpixel((x-l, y-t))
        return pixel[3] > 128

    def hierRect(self):
        "Return a rectangle covering this icon and its children"
        return containingRect(self.traverse())

    def detach(self, child):
        "Remove a child icon"
        self.children.remove(child)
        self.layoutDirty = True

    def addChild(self, child, pos=None):
        "Add a child icon at the end of the child list"
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
        self.outSiteOffset = (5, bodyHeight + outSiteImage.height - 1)

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect), rectHeight(self.rect)), color=(0,0,0,0))
            drawIconBoxedText(self.name, self.cachedImage, (0,0), False)
            outSiteX, outSiteY = self.outSiteOffset
            outSiteX -= outSiteImage.width//2
            outSiteY -= outSiteImage.height
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected),
         location, clip)

    def snapLists(self):
        x, y = self.rect[:2]
        return {"output":[(x + self.outSiteOffset[0], y + self.outSiteOffset[1])]}

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

    def draw(self, image=None, location=None, clip=None):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect), rectHeight(self.rect)), color=(0,0,0,0))
            width, height = drawIconBoxedText(self.name, self.cachedImage, (0,0), False)
            self._drawSpine(self.cachedImage, width-1, height)
            outSiteX, outSiteY = self.outSiteOffset
            outSiteX -= outSiteImage.width//2
            outSiteY -= outSiteImage.height + 1
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected),
         location, clip)  # ... try w/o mask

    def _spineLength(self, inOffsets):
        return max(inOffsets) + inSiteImage.width // 2 + 2

    def _drawSpine(self, image, x, y):
        spineLength = self._spineLength(self.inOffsets)
        draw = ImageDraw.Draw(image)
        draw.rectangle((x, y-spineThickness, x+spineLength-1, y-1), fill=iconBgColor)
        draw.line((x, y-1, x+spineLength-1, y-1), fill=iconOutlineColor)
        draw.line((x, y-spineThickness, x+spineLength, y-spineThickness), fill=iconOutlineColor)
        draw.line((x+spineLength-1, y-1, x+spineLength-1, y-spineThickness), fill=iconOutlineColor)
        for inOff in self.inOffsets:
            image.paste(inSiteImage, (x+inOff - inSiteImage.width // 2, y-spineThickness))

    def snapLists(self):
        x, y = self.rect[:2]
        outOffsets = [(x + self.outSiteOffset[0], y + self.outSiteOffset[1])]
        width, height = self.bodySize
        x += width - 1
        y += height - spineThickness + outSiteImage.height
        inOffsets = [(x+i, y) for i in self.inOffsets]
        return {"output":outOffsets, "input":inOffsets}

    def addChild(self, child, pos=None):
        "Add a child icon at the end of the child list"
        if pos is None:
            self.children.append(child)
        else:
            index = 0
            for sitePos in self.snapLists().get("input", []):
                if sitePos == pos:
                    self.children.insert(index, child)
                index += 1
                break
            else:
                print("Failed to add child icon.  Icon not found at site position")
                return
        self.layoutDirty = True

    def replaceChild(self, childToRemove, childToInsert):
        index = self.children.index(childToRemove)
        self.children[index] = childToInsert
        self.layoutDirty = True

    def childAt(self, pos):
        for child in self.children:
            index = 0
            for sitePos in child.snapLists().get("output", []):
                if sitePos == pos:
                    return child
        return None

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
                childIcon._doLayout(x+bodyWidth-1+childX, bottom-spineThickness+1,
                        childLayout)
                childX += childWidth-1
        width, height = self._size()
        self.rect = (x, bottom-bodyHeight, x+width, bottom+outSiteImage.height)
        self.cachedImage = None
        self.layoutDirty = False

    def _calcLayout(self):
        childLayouts = [c._calcLayout() for c in self.children]
        if len(childLayouts) == 0:
            childWidth = self._spineLength(self.emptyInOffsets)
            height = self.bodySize[1]
        else:
            childWidth = sum((c[1]-1 for c in childLayouts))
            height = max((c[2] for c in childLayouts)) + spineThickness - 1
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

    def snapLists(self):
        return {}

    def layout(self, location=None):
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def _doLayout(self, x, bottom, calculatedSizes=None):
        self.rect = (x, bottom-self.image.height, x + self.image.width, bottom)

    def _calcLayout(self):
        width, height = rectSize(self.rect)
        return (self, self.image.width, self.image.height, [])

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        #... base64 encode a jpeg
        return ("IdentIcon", ("TODO", addPoints(location, offset)))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        #... base64 decode a jpeg
        # image, location = clipData
        return None

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
    #... This is wasteful and should be an image filter if I can figure out how to
    # make one properly
    alphaImg = image.getchannel('A')
    colorImg = Image.new('RGBA', (image.width, image.height), color=(0, 0, 255, 0))
    colorImg.putalpha(alphaImg)
    selImg = Image.blend(image, colorImg, .15)
    return selImg

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
    return x >= l and x < r and y >= t and y < b

def moveRect(rect, newLoc):
    l, t, r, b = rect
    x, y = newLoc
    return(x, y, x+r-l, y+b-t)

def addPoints(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return (x1 + x2, y1 + y2)