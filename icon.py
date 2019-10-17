from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from python_g import msTime, AccumRects, offsetRect

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)

TEXT_MARGIN = 2
SPINE_THICKNESS = 3
OUTLINE_COLOR = (180, 180, 180, 255)
ICON_BG_COLOR = (255, 255, 255, 255)
SELECT_TINT = (0, 0, 255, 0)
GRAY_75 = (192, 192, 192, 255)
GRAY_50 = (128, 128, 128, 255)
GRAY_25 = (64, 64, 64, 255)
BLACK = (0, 0, 0, 255)

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
commaImage = asciiToImage(commaPixmap)
parenImage = iconBoxedText(')')

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.selected = False
        self.layoutDirty = False
        self.cachedImage = None

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is drawn
         can be optionally overridden by specifying image and/or location."""
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

    def snapLists(self):
        x, y = self.rect[:2]
        return {"output":[(x + self.outSiteOffset[0], y + self.outSiteOffset[1])]}

    def layout(self, location=None):
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def _doLayout(self, outSiteX, outSiteY, _calculatedSizes=None):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top =  outSiteY - height//2
        self.rect = (outSiteX, top, outSiteX + width, top + height)

    def _calcLayout(self):
        width, height = self.bodySize
        return self, width, height, []

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return self.__class__.__name__, (self.name, addPoints(location, offset))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        name, location = clipData
        return IdentIcon(name, window, (addPoints(location, locationOffset)))

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
        return self.argIcons

    def snapLists(self):
        x, y = self.rect[:2]
        outOffsets = [(x + self.outSiteOffset[0], y + self.outSiteOffset[1])]
        width, height = self.bodySize
        x += width + outSiteImage.width - 1 - inSiteImage.width-1
        y += height // 2
        inOffsets = [(x+i, y) for i in self.inOffsets]
        return {"output":outOffsets, "input":inOffsets}

    def detach(self, child):
        """Remove a child icon"""
        self.argIcons.remove(child)
        self.layoutDirty = True

    def addChild(self, child, pos=None):
        """Add a child icon at the end of the child list"""
        if pos is None:
            self.argIcons.append(child)
        else:
            for index, sitePos in enumerate(self.snapLists().get("input", [])):
                if sitePos == pos:
                    self.argIcons.insert(index, child)
                    break
            else:
                print("Failed to add child icon.  Icon not found at site position")
                return
        self.layoutDirty = True

    def replaceChild(self, childToRemove, childToInsert):
        index = self.argIcons.index(childToRemove)
        self.argIcons[index] = childToInsert
        self.layoutDirty = True

    def childAt(self, pos):
        for index, sitePos in enumerate(self.snapLists().get("input", [])):
            if sitePos == pos:
                if len(self.argIcons) <= index:
                    return None
                return self.argIcons[index]
        return None

    def layout(self, location=None):
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self._doLayout(x, y+self.bodySize[1] // 2, self._calcLayout())

    def _doLayout(self, outSiteX, outSiteY, calculatedSizes):
        icn, layoutWidth, layoutHeight, childLayouts = calculatedSizes
        bodyWidth, bodyHeight = self.bodySize
        if len(childLayouts) == 0:
            self.inOffsets = self.emptyInOffsets
        else:
            self.inOffsets = []
            childXOffset = outSiteX + bodyWidth + outSiteImage.width - 1 - inSiteImage.width
            childX = 0
            for childLayout in childLayouts:
                childIcon, childWidth, childHeight, subLayouts = childLayout
                self.inOffsets.append(childX)
                childIcon._doLayout(childXOffset + childX, outSiteY, childLayout)
                childX += childWidth-1 + commaImage.width-1
            self.inOffsets.append(childX - (commaImage.width-1))
        width, height = self._size()
        x = outSiteX
        y = outSiteY - bodyHeight // 2
        self.rect = (x, y, x+width, y+height)
        self.cachedImage = None
        self.layoutDirty = False

    def _calcLayout(self):
        childLayouts = [c._calcLayout() for c in self.argIcons]
        bodyWidth, bodyHeight = self.bodySize
        if len(childLayouts) == 0:
            childWidth = self.emptyInOffsets[-1] + parenImage.width
            height = bodyHeight
        else:
            numCommas = len(childLayouts) - 2
            commaParenWidth = numCommas*(commaImage.width-1) + parenImage.width-1
            childWidth = sum((c[1]-1 for c in childLayouts)) + commaParenWidth
            height = max(bodyHeight, max((c[2] for c in childLayouts)))
        width = self.bodySize[0] + outSiteImage.width + childWidth
        return self, width, height, childLayouts

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

    def _doLayout(self, x, bottom, _calculatedSizes=None):
        self.rect = (x, bottom-self.image.height, x + self.image.width, bottom)

    def _calcLayout(self):
        return self, self.image.width, self.image.height, []

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        # ... base64 encode a jpeg
        return "IdentIcon", ("TODO", addPoints(location, offset))

    @staticmethod
    def fromClipboard(_clipData, _window, _locationOffset):
        # ... base64 decode a jpeg
        # image, location = clipData
        return None

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
