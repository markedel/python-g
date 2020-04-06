# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from python_g import rectsTouch, AccumRects
import math
import operator

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)

binOpPrecedence = {'+':10, '-':10, '*':11, '/':11, '//':11, '%':11, '**':14,
 '<<':9, '>>':9, '|':6, '^':7, '&':8, '@':11, 'and':3, 'or':2, 'in':5, 'not in':5,
 'is':5, 'is not':5, '<':5, '<=':5, '>':5, '>=':5, '==':5, '!=':5, '=':-1}

unaryOpPrecedence = {'+':12, '-':12, '~':13, 'not':4}

binOpFn = {'+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv,
 '//':operator.floordiv, '%':operator.mod, '**':operator.pow, '<<':operator.lshift,
 '>>':operator.rshift, '|':operator.or_, '^':operator.xor, '&':operator.and_,
 '@':lambda x,y:x@y, 'and':lambda x,y:x and y, 'or':lambda x,y:x or y,
 'in':lambda x,y:x in y, 'not in':lambda x,y:x not in y, 'is':operator.is_,
 'is not':operator.is_not, '<':operator.lt, '<=':operator.le, '>':operator.gt,
 '>=':operator.ge, '==':operator.eq, '!=':operator.ne}

unaryOpFn = {'+':operator.pos, '-':operator.neg, '~':operator.inv, 'not':operator.not_}

namedConsts = {'True':True, 'False':False, 'None':None}

parentSiteTypes = {'output', 'attrOut'}
childSiteTypes = {'input', 'attrIn'}
matingSiteType = {'output':'input', 'input':'output', 'attrOut':'attrIn',
 'attrIn':'attrOut', 'seqOut':'seqIn', 'seqIn':'seqOut'}

ATTR_SITE_DEPTH = 1
OUTPUT_SITE_DEPTH = 2
SEQ_SITE_DEPTH = -1  # Icons extend 1 pixel to the left of the sequence site
siteDepths = {'input':OUTPUT_SITE_DEPTH, 'output':OUTPUT_SITE_DEPTH,
 'attrOut':ATTR_SITE_DEPTH, 'attrIn':ATTR_SITE_DEPTH, 'seqIn':SEQ_SITE_DEPTH}

TEXT_MARGIN = 2
OUTLINE_COLOR = (220, 220, 220, 255)
ICON_BG_COLOR = (255, 255, 255, 255)
SELECT_TINT = (0, 0, 255, 0)
ERR_TINT = (255, 0, 0, 0)
GRAY_75 = (192, 192, 192, 255)
GRAY_50 = (128, 128, 128, 255)
GRAY_25 = (64, 64, 64, 255)
BLACK = (0, 0, 0, 255)

DEPTH_EXPAND = 4

EMPTY_ARG_WIDTH = 11
LIST_EMPTY_ARG_WIDTH = 4

# Pixels below input/output site to place function/list/tuple icons insertion site
INSERT_SITE_X_OFFSET = 2
INSERT_SITE_Y_OFFSET = 5 # sum(globalFont.getmetrics()) // 2

# Pixels below input/output site to place attribute site
# This should be based on font metrics, but for the moment, we have a hard-coded cursor
ATTR_SITE_OFFSET = 4

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

attrOutPixmap = (
 "%%",
 "%%",
)

attrInPixmap = (
 "o.",
 "o.",
)

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
 "o %9o",
 "o8%9o",
 "o%8 o",
 "o   o",
 "ooooo",
)
commaImageSiteYOffset = 3

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
 "..o     o",
 "..o  85 o",
 "..o 85  o",
 "..o 38  o",
 "..o8%   o",
 ".o 3%  o.",
 "o  5% o..",
 ".o 3%  o.",
 "..o8%   o",
 "..o 38  o",
 "..o 85  o",
 "..o  85 o",
 "..o     o",
 "..ooooooo",
)

binRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o 58   o",
 "o  58  o",
 "o  83  o",
 "o   %8 o",
 "o   %3 o",
 "o   %5 o",
 "o   %3 o",
 "o   %8 o",
 "o  83 o.",
 "o  58 o.",
 "o 58   o",
 "o      o",
 "oooooooo",
)

tupleLParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o   5  o",
 "o  76  o",
 "o  47  o",
 "o  %8  o",
 "o 9%8  o",
 "o 8%8  o",
 "o 8%8  o",
 "o 8%8  o",
 "o 9%8  o",
 "o  %8  o",
 "o  47  o",
 "o  76  o",
 "o   5  o",
 "o      o",
 "oooooooo",
)

tupleRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o  5   o",
 "o  67  o",
 "o  74  o",
 "o  8%  o",
 "o  8%9 o",
 "o  8%8 o",
 "o  8%8 o",
 "o  8%8 o",
 "o  8%9 o",
 "o  8%  o",
 "o  74 o.",
 "o  67 o.",
 "o  5   o",
 "o      o",
 "oooooooo",
)

binInSeqPixmap = (
 "o8o",
 "8%8",
 "o8o",
 "o o",
 "o o",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "o o",
 "o8o",
 "8%8",
 "o8o",
)

inpSeqPixmap = (
 "o8o",
 "8%8",
 "o8o",
 "o o",
 "o o",
 "o o",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "o o",
 "o o",
 "o8o",
 "8%8",
 "o8o",
)

assignDragPixmap = (
 "......",
 "......",
 "......",
 "......",
 "......",
 "...ooo",
 "..o%%%",
 "55%%%.",
 "%%%%..",
 "55%%%.",
 "..o%%%",
 "...ooo",
 "......",
 "......",
 "......",
 "......",
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

asciiMap = {'.':(0, 0, 0, 0), 'o':OUTLINE_COLOR, ' ':ICON_BG_COLOR, '%':BLACK}
for i in range(1, 10):
    pixel = int(int(i) * 255 * 0.1)
    asciiMap[str(i)] = (pixel, pixel, pixel, 255)

def asciiToImage(asciiPixmap):
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image

def iconBoxedText(text, minHgt=None):
    if (text, minHgt) in renderCache:
        return renderCache[(text, minHgt)]
    width, height = globalFont.getsize(text)
    width += 2 * TEXT_MARGIN + 1
    height += 2 * TEXT_MARGIN + 1
    if minHgt is not None and height < minHgt:
        height = minHgt
    txtImg = Image.new('RGBA', (width, height), color=ICON_BG_COLOR)
    draw = ImageDraw.Draw(txtImg)
    draw.text((TEXT_MARGIN, TEXT_MARGIN), text, font=globalFont, fill=(0, 0, 0, 255))
    draw.rectangle((0, 0, width-1, height-1), fill=None, outline=OUTLINE_COLOR)
    renderCache[(text, minHgt)] = txtImg
    return txtImg

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)
attrOutImage = asciiToImage(attrOutPixmap)
attrInImage = asciiToImage(attrInPixmap)
leftInSiteImage = asciiToImage(leftInSitePixmap)
commaImage = asciiToImage(commaPixmap)
binOutImage = asciiToImage(binOutPixmap)
floatInImage = asciiToImage(floatInPixmap)
lParenImage = asciiToImage(binLParenPixmap)
rParenImage = asciiToImage(binRParenPixmap)
tupleLParenImage = asciiToImage(tupleLParenPixmap)
tupleRParenImage = asciiToImage(tupleRParenPixmap)
inpSeqImage = asciiToImage(inpSeqPixmap)
binInSeqImage = asciiToImage(binInSeqPixmap)
assignDragImage = asciiToImage(assignDragPixmap)

class IconExecException(Exception):
    def __init__(self, ic, exceptionText):
        self.icon = ic
        self.message = exceptionText

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.selected = False
        self.layoutDirty = False
        self.cachedImage = None
        self.sites = IconSiteList()
        window.undo.registerIconCreated(self)

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is
         drawn can be optionally overridden by specifying image and/or location."""
        pass

    def pos(self):
        """The "official" position of an icon is defined by the location of its seqIn
        site if it has one.  Otherwise, by the top-left corner of its rectangle."""
        if hasattr(self.sites, 'seqIn'):
            return self.posOfSite('seqIn')
        else:
            return self.rect[:2]

    def layout(self, location=None):
        """Compute layout and set locations for icon and its children (do not redraw).
        location (at least for the moment) is upper left corner of .rect, not .pos()."""
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        # The calcLayout and doLayout calls use the icon's output site (if it has one)
        # as its reference position even if it is connected to a sequence site.
        lo = self.calcLayout()
        if hasattr(self.sites, 'output'):
            self.doLayout(x+self.sites.output.xOffset, y+self.sites.output.yOffset, lo)
        elif hasattr(self.sites, 'seqIn'):
            self.doLayout(x+self.sites.seqIn.xOffset, y+self.sites.seqIn.yOffset, lo)
        elif hasattr(self.sites, 'attrOut'):
            self.doLayout(x+self.sites.attrOut.xOffset, y+self.sites.attrOut.yOffset, lo)
        else:
            self.doLayout(x, y, lo)
        return lo

    def traverse(self, order="draw", includeSelf=True):
        """Iterator for traversing the tree below this icon.  Traversal can be in either
        drawing (order="draw") or picking (order="pick") order."""
        if includeSelf and order is not "pick":
            yield self
        # For "pick" order to be the true opposite of "draw", this loop should run in
        # reverse, but child icons are not intended to overlap in a detectable way.
        for child in self.children():
            if child is None:
                print('icon has null child', self)
            yield from child.traverse(order)
        if includeSelf and order is "pick":
            yield self

    def touchesPosition(self, x, y):
        # ... reevaluate whether it is always best to cache the whole image when
        #     we're drawing little bits of fully-overlapped icons
        if not pointInRect((x, y), self.rect) or self.cachedImage is None:
            return False
        l, t = self.rect[:2]
        pixel = self.cachedImage.getpixel((x - l, y - t))
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
        return False

    def children(self):
        return [c.att for c in self.sites.childSites() if c is not None and
         c.att is not None]

    def parent(self):
        for site in self.sites.parentSites():
            # icons can have multiple possible parent sites (Some icon types are capable
            # of snapping to multiple site types).  Return whichever is attached.
            if site.att is not None:
                return site.att
        return None

    def parentSites(self):
        """Return siteIds for all icon sites capable of holding parent links."""
        return [site.name for site in self.sites.parentSites()]

    def parentage(self):
        """Returns a list containing the lineage of the given icon, from the icon up to
         the top of the window hierarchy."""
        parentList = []
        child = self
        while True:
            parent = child.parent()
            if parent is None:
                break
            parentList.append(parent)
            child = parent
        return parentList

    def topLevelParent(self):
        """Follow the icon hierarchy upwards and return the icon with no parent"""
        child = self
        while True:
            parent = child.parent()
            if parent is None:
                return child
            child = parent

    def nextInSeq(self):
        if not hasattr(self.sites, 'seqOut'):
            return None
        return self.sites.seqOut.att

    def prevInSeq(self):
        if not hasattr(self.sites, 'seqIn'):
            return None
        return self.sites.seqIn.att

    def snapLists(self, forCursor=False):
        x, y = self.rect[:2]
        return self.sites.makeSnapLists(self, x, y, forCursor=forCursor)

    def replaceChild(self, newChild, siteId, leavePlace=False, childSite=None):
        """Replace the icon attached at a particular site.  Note that while the name
        is "replaceChild", it is possible to use this on any site.  The convention when
        icons are arranged in a hierarchy, is to operate on child sites, so that the
        back-link (childSite) can be automatically determined.  Meaning, if icons are not
        arranged in a strict hierarchy, specify childSite or bad things will happen.
        If leavePlace is False, replacing a series site with None will remove the site
        itself from the series.  If leavePlace is True, the site will remain and be set
        to None."""
        siteId = self.sites.siteIdWarn(siteId)
        if self.sites.isSeries(siteId):
            if newChild is None and not leavePlace:
                self.sites.removeSeriesSiteById(self, siteId)
            else:
                seriesName, idx = splitSeriesSiteId(siteId)
                seriesLen = len(self.sites.getSeries(seriesName))
                if idx == seriesLen:
                    self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
                self.sites.lookup(siteId).attach(self, newChild, childSite)
        else:
            self.sites.lookup(siteId).attach(self, newChild, childSite)
        self.layoutDirty = True

    def removeEmptySeriesSite(self, siteId):
        if self.childAt(siteId):
            return
        self.sites.removeSeriesSiteById(self, siteId)
        self.layoutDirty = True

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None):
        """Insert a child icon or empty icon site (child=None) at the specified site.
        siteIdOrName may specify either the complete siteId for a site, or (if
        seriesIdx is specified), the name for a series of sites with the index specified
        in seriesIdx."""
        if seriesIdx is None:
            seriesName, seriesIdx = splitSeriesSiteId(siteIdOrSeriesName)
        else:
            seriesName = siteIdOrSeriesName
        if seriesName is None:
            print("Failed to insert icon", child, "at", siteIdOrSeriesName)
            return
        series = self.sites.getSeries(seriesName)
        if series is None:
            print("Failed to insert icon,", child, "in series", seriesName)
            return
        if len(series) == 1 and series[0].att is None and seriesIdx == 0:
            series[0].attach(self, child, childSite)
        else:
            self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, seriesIdx)
            self.sites.lookupSeries(seriesName)[seriesIdx].attach(self, child, childSite)
        self.layoutDirty = True

    def insertChildren(self, children, seriesName, seriesIdx, childSite=None):
        """Insert a group of child icons at the specified site"""
        for i, child in enumerate(children):
            self.insertChild(child, seriesName, seriesIdx + i, childSite)

    def insertAttr(self, topAttrIcon):
        """Insert an attribute or chain of attributes between the icon and its current
        attributes"""
        endAttrIcon = findLastAttrIcon(topAttrIcon)
        origAttrIcon = self.childAt('attrIcon')
        self.replaceChild(topAttrIcon, 'attrIcon')
        endAttrIcon.replaceChild(origAttrIcon, 'attrIcon')

    def childAt(self, siteOrSeriesName, seriesIdx=None):
        if seriesIdx is None:
            site = siteOrSeriesName
        else:
            site = makeSeriesSiteId(siteOrSeriesName, seriesIdx)
        icSite = self.sites.lookup(site)
        return icSite.att if icSite is not None else None

    def siteOf(self, ic, recursive=False):
        """Find the site name for an attached icon.  If recursive is True, ic is not
        required to be a direct descendant."""
        if recursive:
            while True:
                parent = ic.parent()
                if parent is None:
                    return None
                if parent is self:
                    break
                ic = parent
        icSite = self.sites.siteOfAttachedIcon(ic)
        return icSite.name if icSite is not None else None

    def hasSite(self, siteId):
        return self.sites.lookup(siteId) is not None

    def posOfSite(self, siteId):
        """Return the window position of a given site of the icon"""
        site = self.sites.lookup(siteId)
        if site is None:
            return None
        x, y = self.rect[:2]
        return x + site.xOffset, y + site.yOffset

    def typeOf(self, siteId):
        site = self.sites.lookup(siteId)
        if site is None:
            return None
        return site.type

    def indexOf(self, siteId):
        series, index = splitSeriesSiteId(siteId)
        if series is not None:
            return index
        return None

    def becomeTopLevel(self, isTop):
        """Change top level status of icon (most icons add or remove sequence sites)."""
        self.cachedImage = None  # Force change at next redraw

    def hasCoincidentSite(self):
        """If the icon has an input site in the same spot as its output site (done so
        binary operations can be arranged like text), return that input site"""
        if hasattr(self, 'coincidentSite') and self.coincidentSite is not None:
            return self.coincidentSite

    def textRepr(self):
        return repr(self)

    def doLayout(self, outSiteX, outSiteY, layout):
        pass

    def calcLayout(self):
        pass

class TextIcon(Icon):
    def __init__(self, text, window=None, location=None, hasAttrIn=True, minTxtHgt=None):
        Icon.__init__(self, window)
        self.text = text
        self.hasAttrIn = hasAttrIn
        bodyWidth, bodyHeight = globalFont.getsize(self.text)
        if minTxtHgt is not None and minTxtHgt > bodyHeight:
            bodyHeight = minTxtHgt
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
         bodyHeight // 2 + ATTR_SITE_OFFSET)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and image is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or image is not None)
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text, self.bodySize[1])
            self.cachedImage.paste(txtImg, (outSiteImage.width - 1, 0))
            if needSeqSites:
                drawSeqSites(self.cachedImage, outSiteImage.width-1, 0, txtImg.height)
            if needOutSite:
                outX = self.sites.output.xOffset
                outY = self.sites.output.yOffset - outSiteImage.height // 2
                self.cachedImage.paste(outSiteImage, (outX, outY), mask=outSiteImage)
            if self.hasAttrIn:
                attrX = self.sites.attrIcon.xOffset
                attrY = self.sites.attrIcon.yOffset
                self.cachedImage.paste(attrInImage, (attrX, attrY))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.cachedImage = None  # Draw or undraw sequence sites ... refine when sites added
        self.layoutDirty = False

    def calcLayout(self):
        width, height = self.bodySize
        layout = Layout(self, width, height, height // 2)
        if self.sites.attrIcon.att is None:
            attrLayout = None
        else:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        layout.addSubLayout(attrLayout, 'attrIcon', width, ATTR_SITE_OFFSET)
        return layout

    def textRepr(self):
        return self.text

    def execute(self):
        # This execution method is a remnant from when the IdentIcon did numbers, strings,
        # and identifiers, and is probably no longer appropriate.  Not sure if the current
        # uses of naked text icons should even be executed at all
        try:
            result = eval(self.text)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class IdentifierIcon(TextIcon):
    def __init__(self, name, window=None, location=None):
        _w, minTxtHgt = globalFont.getsize("Mg_")
        TextIcon.__init__(self, name, window, location, minTxtHgt=minTxtHgt)
        self.name = name

    def execute(self):
        if self.name in namedConsts:
            return namedConsts[self.name]
        elif self.name in globals():
            return globals()[self.name]
        raise IconExecException(self, self.name + " is not defined")

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return self.__class__.__name__, (self.name, addPoints(location, offset))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        name, location = clipData
        return IdentifierIcon(name, window, (addPoints(location, locationOffset)))

class NumericIcon(TextIcon):
    def __init__(self, value, window=None, location=None):
        if type(value) == type(""):
            try:
                value = int(value)
            except ValueError:
                value = float(value)
        TextIcon.__init__(self, repr(value), window, location, hasAttrIn=False)
        self.value = value

    def execute(self):
        return self.value

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return self.__class__.__name__, (self.text, addPoints(location, offset))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        valueStr, location = clipData
        return NumericIcon(valueStr, window, (addPoints(location, locationOffset)))

class StringIcon(TextIcon):
    def __init__(self, string, window=None, location=None):
        TextIcon.__init__(self, repr(string), window, location)
        self.string = string

    def execute(self):
        return self.string

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return self.__class__.__name__, (self.string, addPoints(location, offset))

    @staticmethod
    def fromClipboard(clipData, window, locationOffset):
        text, location = clipData
        return StringIcon(text, window, (addPoints(location, locationOffset)))

class AttrIcon(Icon):
    def __init__(self, text, window=None, location=None):
        Icon.__init__(self, window)
        self.text = text
        bodyWidth, _h = globalFont.getsize(self.text)
        _w, bodyHeight = globalFont.getsize("Mg_")
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('attrOut', 'attrOut', 0, bodyHeight // 2 + ATTR_SITE_OFFSET)
        self.sites.add('attrIcon', 'attrIn', bodyWidth - ATTR_SITE_DEPTH,
         bodyHeight // 2 + ATTR_SITE_OFFSET)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + attrOutImage.width, y + bodyHeight)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text, self.bodySize[1])
            self.cachedImage.paste(txtImg, (attrOutImage.width - 1, 0))
            attrOutX = self.sites.attrOut.xOffset
            attrOutY = self.sites.attrOut.yOffset
            self.cachedImage.paste(attrOutImage, (attrOutX, attrOutY), mask=attrOutImage)
            attrInX = self.sites.attrIcon.xOffset
            attrInY = self.sites.attrIcon.yOffset
            self.cachedImage.paste(attrInImage, (attrInX, attrInY))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        width, height = self.bodySize
        width += attrOutImage.width - 1
        top = attrSiteY - (height // 2 + ATTR_SITE_OFFSET)
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        width, height = self.bodySize
        layout = Layout(self, width, height, height // 2 + ATTR_SITE_OFFSET)
        if self.sites.attrIcon.att is None:
            attrLayout = None
        else:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        layout.addSubLayout(attrLayout, 'attrIcon', width, 0)
        return layout

    def textRepr(self):
        return '.' + self.text

    def execute(self, attrOfValue):
        # This execution method is a remnant from when the IdentIcon did numbers, strings,
        # and identifiers, and is probably no longer appropriate.  Not sure if the current
        # uses of naked text icons should even be executed at all
        try:
            result = getattr(attrOfValue, self.text)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class UnaryOpIcon(Icon):
    def __init__(self, op, window, location=None):
        Icon.__init__(self, window)
        self.operator = op
        self.precedence = unaryOpPrecedence[op]
        bodyWidth, bodyHeight = globalFont.getsize(self.operator)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('argIcon', 'input', bodyWidth - 1, siteYOffset)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and image is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or image is not None)
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            width, height = globalFont.getsize(self.operator)
            bodyLeft = outSiteImage.width - 1
            bodyWidth = width + 2 * TEXT_MARGIN
            bodyHeight = height + 2 * TEXT_MARGIN
            draw = ImageDraw.Draw(self.cachedImage)
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth, bodyHeight),
             fill=ICON_BG_COLOR, outline=OUTLINE_COLOR)
            if needOutSite:
                outImageY = self.sites.output.yOffset - outSiteImage.height // 2
                self.cachedImage.paste(outSiteImage, (0, outImageY), mask=outSiteImage)
            inImageY = self.sites.argIcon.yOffset - inSiteImage.height // 2
            self.cachedImage.paste(inSiteImage, (self.sites.argIcon.xOffset, inImageY))
            if needSeqSites:
                drawSeqSites(self.cachedImage, bodyLeft, 0, bodyHeight+1)
            if self.operator in ('+', '-', '~'):
                # Raise unary operators up and move then to the left.  Not sure if this
                # is safe for all fonts, but the Ariel font we're using pads on top.
                textTop = -1 if self.operator == '+' else -2
                textLeft = bodyLeft + 2 * TEXT_MARGIN
            else:
                textTop = TEXT_MARGIN
                textLeft = bodyLeft + TEXT_MARGIN + 1
            draw.text((textLeft, textTop), self.operator, font=globalFont,
             fill=(0, 0, 0, 255))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.layoutDirty = False

    def calcLayout(self):
        width, height = self.bodySize
        mySiteOffset = height // 2
        layout = Layout(self, width + EMPTY_ARG_WIDTH, height, mySiteOffset)
        if self.sites.argIcon.att is None:
            layout.addSubLayout(None, 'argIcon', width, 0)
        else:
            layout.addSubLayout(self.sites.argIcon.att.calcLayout(), 'argIcon', width, 0)
        return layout

    def textRepr(self):
        if self.sites.argIcon.att is None:
            argText = "None"
        else:
            argText = self.sites.argIcon.att.textRepr()
        return self.operator + " " + argText

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        if self.sites.argIcon.att is None:
            arg = None
        else:
            arg = self.sites.argIcon.att.clipboardRepr(offset)
        return self.__class__.__name__, (self.operator, addPoints(location, offset), arg)

    @staticmethod
    def fromClipboard(clipData, window, offset):
        op, location, arg = clipData
        ic = UnaryOpIcon(op, window, (addPoints(location, offset)))
        ic.sites.argIcon.attach(ic, clipboardDataToIcons([arg], window, offset)[0])
        return ic

    def execute(self):
        if self.sites.argIcon.att is None:
            raise IconExecException(self, "Missing argument")
        argValue = self.sites.argIcon.att.execute()
        try:
            result = unaryOpFn[self.operator](argValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class ListTypeIcon(Icon):
    def __init__(self, leftText, rightText, window, leftImg=None, rightImg=None,
     location=None):
        Icon.__init__(self, window)
        self.leftText = leftText
        self.rightText = rightText
        self.leftImg = iconBoxedText(self.leftText) if leftImg is None else leftImg
        if rightImg is None:
            self.rightImg = iconBoxedText( self.rightText)
            attrInX = self.rightImg.width-2
            attrInY = self.rightImg.height // 2 +  + ATTR_SITE_OFFSET
            self.rightImg.paste(attrInImage, (attrInX, attrInY))
        else:
            self.rightImg = rightImg
        leftWidth, leftHeight = self.leftImg.size
        self.sites.add('output', 'output', 0, leftHeight // 2)
        self.argList = HorizListMgr(self, 'argIcons', leftWidth-1, leftHeight//2)
        width, height = self._size()
        self.sites.add('attrIcon', 'attrIn', width-1,
         self.sites.output.yOffset + ATTR_SITE_OFFSET)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, height-2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        width, height = self.leftImg.size
        width += self.argList.width() + self.rightImg.width
        return width, height

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and image is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or image is not None)
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', self._size(), color=(0, 0, 0, 0))
            # Body
            leftImgX = outSiteImage.width - 1
            self.cachedImage.paste(self.leftImg, (leftImgX, 0))
            if needSeqSites:
                drawSeqSites(self.cachedImage, leftImgX, 0, self.leftImg.height)
            # Output site
            if needOutSite:
                outSiteX = self.sites.output.xOffset
                outSiteY = self.sites.output.yOffset - outSiteImage.height // 2
                self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY),
                 mask=outSiteImage)
            # Body input site
            inSiteX = outSiteImage.width - 1 + self.leftImg.width - inSiteImage.width
            inSiteY = self.sites.output.yOffset - inSiteImage.height // 2
            self.cachedImage.paste(inSiteImage, (inSiteX, inSiteY))
            # Commas
            self.argList.drawCommas(self.cachedImage, inSiteX, self.sites.output.yOffset)
            # End paren/brace
            parenY = self.sites.output.yOffset - self.rightImg.height // 2
            parenX = inSiteX + self.argList.width() + inSiteImage.width - 2
            self.cachedImage.paste(self.rightImg, (parenX, parenY))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        return siteSnapLists

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        # If the rectangle is entirely contained within the argument space (ignoring
        # commas), then we will call it not touching
        bodyRight = self.rect[0] + self.leftImg.width
        return not rectWithinXBounds(rect, bodyRight, bodyRight + self.argList.width())

    def doLayout(self, outSiteX, outSiteY, layout):
        self.argList.doLayout(layout)
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        bodyWidth, bodyHeight = self.leftImg.size
        layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
        argWidth = self.argList.calcLayout(layout, bodyWidth - 1, 0)
        # layout now incorporates argument layout sizes, but not end paren/brace/bracket
        layout.width = bodyWidth + outSiteImage.width + argWidth + self.rightImg.width - 5
        if self.sites.attrIcon.att:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        else:
            attrLayout = None
        layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1, ATTR_SITE_OFFSET)
        return layout

    def textRepr(self):
        argText = ""
        for site in self.sites.argIcons:
            if site.att is None:
                argText = argText + "None, "
            else:
                argText = argText + site.att.textRepr() + ", "
        if len(argText) > 0:
            argText = argText[:-2]
        return self.leftText + argText + self.rightText

class FnIcon(ListTypeIcon):
    def __init__(self, name, window, location=None):
        self.name = name
        ListTypeIcon.__init__(self, name + '(', ')', window, location)

    def execute(self):
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0] is None:
            argValues = []
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            argValues = [site.att.execute() for site in self.sites.argIcons]
        try:
            result = getattr(math, self.name)(*argValues)
        except Exception as err:
            raise IconExecException(self, err)
        return result

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.name, addPoints(location, offset),
         [None if site.att is None else site.att.clipboardRepr(offset)
          for site in self.sites.argIcons]))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        name, location, children = clipData
        ic = FnIcon(name, window, (addPoints(location, offset)))
        for i, arg in enumerate(clipboardDataToIcons(children, window, offset)):
            ic.insertChild(arg, "argIcons", i)
        return ic

class ListIcon(ListTypeIcon):
    def __init__(self, window, location=None):
        ListTypeIcon.__init__(self, '[', ']', window, location=location)

    def argIcons(self):
        """Return list of list argument icons.  This is trivial, but exists to match
        the identical TupleIcon method which has a more complicated function."""
        return [site.att for site in self.sites.argIcons]

    def execute(self):
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return []
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
        return [site.att.execute() for site in self.sites.argIcons]

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (addPoints(location, offset),
         [None if site.att is None else site.att.clipboardRepr(offset)
          for site in self.sites.argIcons]))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location, children = clipData
        ic = ListIcon(window, (addPoints(location, offset)))
        for i, arg in enumerate(clipboardDataToIcons(children, window, offset)):
            ic.insertChild(arg, "argIcons", i)
        return ic

class TupleIcon(ListTypeIcon):
    def __init__(self, window, noParens=False, location=None):
        if noParens:
            leftImg = inpSeqImage
            rightImg = Image.new('RGBA', (0, 0))
        else:
            leftImg = tupleLParenImage
            rightImg = tupleRParenImage
        ListTypeIcon.__init__(self, '(', ')', window, location=location,
         leftImg=leftImg, rightImg=rightImg)
        if noParens:
            self.sites.remove('attrIn')
        self.noParens = noParens

    def argIcons(self):
        """Return list of tuple argument icons, handling special case of a single element
        tuple represented as (x,).  It would be nice to convert these at type-in, but
        hard to distinguish from leaving a space for a second argument."""
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return []
        if len(self.sites.argIcons) == 2 and self.sites.argIcons[0].att is not None and \
         self.sites.argIcons[1] is None:
            # Special case of single item tuple allowed to have missing arg
            return [self.sites.argIcons.att[0]]
        return [site.att for site in self.sites.argIcons]

    def restoreParens(self):
        """Tuples with no parenthesis are allowed on the top level, to make typing
        multi-variable assignment statements more natural.  If one of these paren-less
        icons gets dragged or pasted in to an expression, it needs its parens back."""
        if not self.noParens:
            return
        self.noParens = False
        self.leftImg = tupleLParenImage
        self.rightImg = tupleRParenImage
        self.cachedImage = None
        self.layoutDirty = True
        width, height = self._size()
        self.sites.add('attrIcon', 'attrIn', width-1,
         self.sites.output.yOffset + ATTR_SITE_OFFSET)

    def calcLayout(self):
        # If the icon is no longer at the top level and needs its parens restored, do so
        # before calculating the layout (would be better to do this elsewhere).
        if self.noParens and self.parent() is not None:
            self.restoreParens()
        return ListTypeIcon.calcLayout(self)

    def execute(self):
        argIcons = self.argIcons()
        for argIcon in argIcons:
            if argIcon is None:
                raise IconExecException(self, "Missing argument(s)")
        return tuple(argIcon.execute() for argIcon in argIcons)

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (addPoints(location, offset),
         [None if site.att is None else site.att.clipboardRepr(offset)
          for site in self.sites.argIcons]))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location, children = clipData
        ic = TupleIcon(window, (addPoints(location, offset)))
        for i, arg in enumerate(clipboardDataToIcons(children, window, offset)):
            ic.insertChild(arg, "argIcons", i)
        return ic

class BinOpIcon(Icon):
    def __init__(self, op, window, location=None):
        Icon.__init__(self, window)
        self.operator = op
        self.precedence = binOpPrecedence[op]
        self.hasParens = False  # Filled in by layout methods
        self.leftArgWidth = EMPTY_ARG_WIDTH
        self.rightArgWidth = EMPTY_ARG_WIDTH
        opWidth, opHeight = globalFont.getsize(self.operator)
        opHeight = max(opHeight + 2*TEXT_MARGIN + 1, lParenImage.height)
        opWidth += 2*TEXT_MARGIN - 1
        self.opSize = (opWidth, opHeight)
        self.depthWidth = 0
        x, y = (0, 0) if location is None else location
        width, height = self._size()
        self.rect = (x, y, x + width, y + height)
        siteYOffset = opHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('leftArg', 'input', 0, siteYOffset)
        self.sites.add('rightArg', 'input', self.leftArgWidth + opWidth, siteYOffset)
        # Note that the attrIcon site is only usable when parens are displayed
        self.sites.add("attrIcon", "attrIn", self.leftArgWidth + opWidth, siteYOffset)
        # Indicates that input site falls directly on top of output site
        self.sites.add('seqIn', 'seqIn', - SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - SEQ_SITE_DEPTH, height-2)
        self.coincidentSite = 'leftArg'

    def _size(self):
        opWidth, opHeight = self.opSize
        opWidth += self.depthWidth
        if self.hasParens:
            parenWidth = lParenImage.width - 1 + rParenImage.width - 1
        else:
            parenWidth = 0
        width = parenWidth + self.leftArgWidth + self.rightArgWidth + opWidth
        return width, opHeight

    def leftArg(self):
        return self.sites.leftArg.att if self.sites.leftArg is not None else None

    def rightArg(self):
        return self.sites.rightArg.att if self.sites.rightArg is not None else None

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        cachedImage = self.cachedImage
        atTop = self.parent() is None
        suppressSeqSites = image is not None and self.prevInSeq() is None
        temporaryOutputSite = suppressSeqSites and atTop and self.leftArg() is None
        if temporaryOutputSite or suppressSeqSites:
            # When image is specified the icon is being dragged, and it must display
            # something indicating where its output site is where it would otherwise
            # not nor
            cachedImage = None
            self.cachedImage = None
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if cachedImage is None:
            cachedImage = Image.new('RGBA', self._size(), color=(0, 0, 0, 0))
            # Output part (connector or paren)
            outSiteX = self.sites.output.xOffset
            siteY = self.sites.output.yOffset
            leftArgX = outSiteX + outSiteImage.width - 1
            if self.hasParens:
                outSiteY = siteY - lParenImage.height // 2
                cachedImage.paste(lParenImage, (outSiteX, outSiteY), mask=lParenImage)
                leftArgX = outSiteX + lParenImage.width - 1
            elif temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                cachedImage.paste(binOutImage, (outSiteX, outSiteY), mask=binOutImage)
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - binInSeqImage.height // 2
                cachedImage.paste(binInSeqImage, (outSiteX, outSiteY), mask=binInSeqImage)
            # Body
            txtImg = iconBoxedText(self.operator)
            opX = leftArgX + self.leftArgWidth - 1
            opY = siteY - txtImg.height // 2
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(cachedImage)
                opWidth = txtImg.width + self.depthWidth
                draw.rectangle((opX, opY, opX + opWidth - 1, opY + txtImg.height - 1),
                 outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
                txtSubImg = txtImg.crop((1, 0, txtImg.width - 1, txtImg.height))
                cachedImage.paste(txtSubImg, (opX + self.depthWidth // 2 + 1, opY))
            else:
                opWidth = txtImg.width
                cachedImage.paste(txtImg, (opX + self.depthWidth // 2, opY))
            rInSiteX = opX + opWidth - inSiteImage.width
            rInSiteY = siteY - inSiteImage.height // 2
            cachedImage.paste(inSiteImage, (rInSiteX, rInSiteY))
            # End paren
            if self.hasParens:
                rParenX = opX + opWidth - 1 + self.rightArgWidth - 1
                rParenY = siteY - rParenImage.height // 2
                cachedImage.paste(rParenImage, (rParenX, rParenY))
        pasteImageWithClip(image, tintSelectedImage(cachedImage, self.selected,
         colorErr), location, clip)
        if not (temporaryOutputSite or suppressSeqSites):
            self.cachedImage = cachedImage

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        leftArgLeft = self.rect[0] + self.sites.output.xOffset + outSiteImage.width - 1
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

    def depth(self, lDepth=None, rDepth=None):
        """Calculate factor which decides how much to pad the operator to help indicate
        its level in the icon hierarchy.  The function does not expand the operator icon
        when it and a child or parent form an associative group (so chains of operations,
        like: 1 + 2 + 3 + 4, don't get out of control).  While this looks much nicer, it
        has great potential confuse users who need to understand the hierarchy to edit
        effectively.  Parameters lDepth and rDepth allow a recursive call to calculate
        parent depth, which would otherwise recurse infinitely."""
        if lDepth is None:
            lChild = self.leftArg()
            if lChild is None or lChild.__class__ is not BinOpIcon:
                lDepth = 0
            else:
                lDepth = lChild.depth()
                if not (lChild.leftAssoc() and lChild.precedence == self.precedence):
                    lDepth += 1
        if rDepth is None:
            rChild = self.rightArg()
            if rChild is None or rChild.__class__ is not BinOpIcon:
                rDepth = 0
            else:
                rDepth = rChild.depth()
                if not (rChild.rightAssoc() and rChild.precedence == self.precedence):
                    rDepth += 1
        myDepth = max(lDepth, rDepth)
        # Also expand the operator to match the parent end of the associative group
        parent = self.parent()
        if parent.__class__ is BinOpIcon and parent.precedence == self.precedence:
            if parent.siteOf(self) == "leftArg" and parent.leftAssoc():
                myDepth = max(myDepth, parent.depth(lDepth=myDepth))
            elif parent.siteOf(self) == "rightArg" and parent.rightAssoc():
                myDepth = max(myDepth, parent.depth(rDepth=myDepth))
        return myDepth

    def doLayout(self, outSiteX, outSiteY, layout):
        self.hasParens = layout.hasParens
        self.coincidentSite = None if self.hasParens else "leftArg"
        self.leftArgWidth = layout.lArgWidth
        self.rightArgWidth = layout.rArgWidth
        self.depthWidth = layout.depthWidth
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        hasParens = needsParens(self)
        if hasParens:
            lParenWidth = lParenImage.width - OUTPUT_SITE_DEPTH - 1
            rParenWidth = rParenImage.width - 1
        else:
            lParenWidth = rParenWidth = 0
        opWidth, opHeight = self.opSize
        layout = Layout(self, opWidth, opHeight, opHeight // 2)
        layout.hasParens = hasParens
        if self.leftArg() is None:
            lArgLayout = None
            lArgWidth = EMPTY_ARG_WIDTH
        else:
            lArgLayout = self.leftArg().calcLayout()
            lArgWidth = lArgLayout.width
        layout.lArgWidth = lArgWidth
        layout.addSubLayout(lArgLayout, "leftArg", lParenWidth, 0)
        if self.rightArg() is None:
            rArgLayout = None
            rArgWidth = EMPTY_ARG_WIDTH
        else:
            rArgLayout = self.rightArg().calcLayout()
            rArgWidth = rArgLayout.width
        layout.rArgWidth = rArgWidth
        depthWidth = self.depth() * DEPTH_EXPAND
        layout.depthWidth = depthWidth
        rArgSiteX = lParenWidth + lArgWidth + opWidth + depthWidth
        layout.addSubLayout(rArgLayout, "rightArg", rArgSiteX, 0)
        layout.width = rArgSiteX + rArgWidth + rParenWidth
        parent = self.parent()
        if hasattr(self.sites, 'attrIcon') and self.sites.attrIcon.att is not None:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        else:
            attrLayout = None
        layout.addSubLayout(attrLayout, 'attrIcon', layout.width, ATTR_SITE_OFFSET)
        return layout

    def snapLists(self, forCursor=False):
        # Make attribute site unavailable unless the icon has parens to hold it
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        if not self.hasParens:
            del siteSnapLists['attrIn']
        return siteSnapLists

    def textRepr(self):
        leftArgText = "None" if self.leftArg() is None else self.leftArg().textRepr()
        rightArgText = "None" if self.rightArg() is None else self.rightArg().textRepr()
        text = leftArgText + " " + self.operator + " " + rightArgText
        if self.hasParens:
            return "(" + text + ")"
        return text

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (self.operator, addPoints(location, offset),
         (None if self.leftArg() is None else self.leftArg().clipboardRepr(offset),
          None if self.rightArg() is None else self.rightArg().clipboardRepr(offset))))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        op, location, children = clipData
        ic = BinOpIcon(op, window, (addPoints(location, offset)))
        leftArg, rightArg = clipboardDataToIcons(children, window, offset)
        ic.sites.leftArg.attach(ic, leftArg)
        ic.sites.rightArg.attach(ic, rightArg)
        return ic

    def locIsOnLeftParen(self, btnPressLoc):
        iconLeft = self.rect[0]
        return iconLeft < btnPressLoc[0] < iconLeft + lParenImage.width

    def leftAssoc(self):
        return self.operator != "**"

    def rightAssoc(self):
        return self.operator == "**"

    def execute(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing left operand")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing right operand")
        leftValue = self.leftArg().execute()
        rightValue = self.rightArg().execute()
        try:
            result = binOpFn[self.operator](leftValue, rightValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class AssignIcon(Icon):
    def __init__(self, window, location=None):
        Icon.__init__(self, window)
        opWidth, opHeight = globalFont.getsize('=')
        opWidth += 2*TEXT_MARGIN + 1
        opHeight += 2*TEXT_MARGIN + 1
        siteY = inpSeqImage.height // 2
        self.opSize = (opWidth, opHeight)
        self.sites.add('seqDrag', 'seqDrag', 0, siteY)
        tgtSitesX = assignDragImage.width - 3
        seqSiteX = tgtSitesX + 1
        self.sites.add('seqIn', 'seqIn', seqSiteX, siteY - inpSeqImage.height // 2 + 1)
        self.sites.add('seqOut', 'seqOut', seqSiteX, siteY + inpSeqImage.height//2 - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteY)
        self.tgtLists = [HorizListMgr(self, 'targets0', tgtSitesX, siteY)]
        valueSitesX = tgtSitesX + EMPTY_ARG_WIDTH + opWidth
        self.valueList = HorizListMgr(self, 'values', valueSitesX, siteY)
        width, height = self._size()
        if location is None:
            x = y = 0
        else:
            x, y = location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        opWidth, opHeight = self.opSize
        width = assignDragImage.width
        for tgtList in self.tgtLists:
            width += tgtList.width() + opWidth - 2
        width += self.valueList.width()
        return width, inpSeqImage.height

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        cachedImage = self.cachedImage
        if image is None:
            temporaryDragSite = False
            image = self.window.image
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            cachedImage = None
            self.cachedImage = None
            temporaryDragSite = self.prevInSeq() is None
        if location is None:
            location = self.rect[:2]
        if cachedImage is None:
            width, height = self._size()
            cachedImage = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
            # Left site (seq site bar + 1st target input or drag-insert site
            tgtSiteX = self.sites.targets0[0].xOffset
            siteY = height // 2
            if temporaryDragSite:
                y = siteY - assignDragImage.height // 2
                cachedImage.paste(assignDragImage, (0, y), mask=assignDragImage)
            else:
                y = siteY - inpSeqImage.height // 2
                cachedImage.paste(inpSeqImage, (tgtSiteX, y), mask=inpSeqImage)
            opWidth, opHeight = self.opSize
            for tgtList in self.tgtLists:
                tgtList.drawCommas(cachedImage, tgtSiteX, siteY)
                txtImg = iconBoxedText('=')
                tgtSiteX += tgtList.width() - 1
                cachedImage.paste(txtImg, (tgtSiteX + OUTPUT_SITE_DEPTH,
                (height-opHeight)//2))
                tgtSiteX += opWidth - 1
            rInSiteX = tgtSiteX
            rInSiteY = siteY - inSiteImage.height // 2
            cachedImage.paste(inSiteImage, (rInSiteX, rInSiteY))
            self.valueList.drawCommas(cachedImage, rInSiteX, siteY)
        pasteImageWithClip(image, tintSelectedImage(cachedImage, self.selected,
         colorErr), location, clip)
        if not temporaryDragSite:
            self.cachedImage = cachedImage

    def addTargetGroup(self, idx):
        if idx < 0 or idx > len(self.tgtLists):
            raise Exception('Bad index for adding target group to assignment icon')
        # Name will be filled in by renumberTargetGroups, offset by layout
        self.tgtLists.insert(idx, HorizListMgr(self, 'targetsX', 0, 0))
        self.renumberTargetGroups(descending=True)
        self.window.undo.registerCallback(self.removeTargetGroup, idx)
        self.layoutDirty = True

    def removeTargetGroup(self, idx):
        if idx <= 0 or idx >= len(self.tgtLists):
            raise Exception('Bad index for removing target group from assignment icon')
        seriesName = 'targets%d' % idx
        for site in self.sites.getSeries(seriesName):
            if site.att is not None:
                raise Exception('Removing non-empty target group from assignment icon')
        del self.tgtLists[idx]
        self.sites.removeSeries("targets%d" % idx)
        self.renumberTargetGroups()
        self.window.undo.registerCallback(self.addTargetGroup, idx)
        self.layoutDirty = True

    def renumberTargetGroups(self, descending=False):
        tgtLists = list(enumerate(self.tgtLists))
        if descending:
            tgtLists = reversed(tgtLists)
        for i, tgtList in tgtLists:
            oldName = tgtList.siteSeriesName
            newName = "targets%d" % i
            if oldName != newName:
                tgtList.rename(newName)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        insertSites = []
        for tgtList in self.tgtLists:
            insertSites += tgtList.makeInsertSnapList()
        insertSites += self.valueList.makeInsertSnapList()
        siteSnapLists['insertInput'] = insertSites
        # Snap site for seqOut is too close to snap site for inserting the first target.
        # Nudge the seqOut site down and to the left to make it easier to snap to
        ic, (x, y), siteType = siteSnapLists['seqOut'][0]
        siteSnapLists['seqOut'][0] = (ic, (x-1, y+1), siteType)
        return siteSnapLists

    def execute(self):
        # Get the target and value icons
        tgtLists = []
        for tgtList in self.tgtLists:
            tgts = []
            for site in getattr(self.sites, tgtList.siteSeriesName):
                if site.att is None:
                    raise IconExecException(self, "Missing assignment target(s)")
                tgts.append(site.att)
            tgtLists.append(tgts)
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing assignment value")
            values.append(site.att)
        # Execute all of the value icons
        executedValues = []
        for value in values:
            executedValues.append(value.execute())
        # Assign the resulting values to the targets
        if len(values) == 1:
            value = executedValues[0]
        else:
            value = tuple(executedValues)
        for tgts in tgtLists:
            if len(tgts) == 1:
                tgtIcon = tgts[0]
            else:
                tgtIcon = tgts
            self.assignValues(tgtIcon, value)

    def assignValues(self, tgtIcon, value):
        if isinstance(tgtIcon, IdentifierIcon):
            try:
                globals()[tgtIcon.name] = value
            except Exception as err:
                raise IconExecException(self, err)
            return
        if tgtIcon.__class__ in (TupleIcon, ListIcon):
            assignTargets = tgtIcon.argIcons()
        elif isinstance(tgtIcon, list):
            assignTargets = tgtIcon
        else:
            raise IconExecException(tgtIcon, "Not a valid assignment target")
        if not hasattr(value, "__len__") or len(assignTargets) != len(value):
            raise IconExecException(self, "Could not unpack")
        for target in assignTargets:
            if target is None:
                raise IconExecException(self, "Missing argument(s)")
            for t, v in zip(assignTargets, value):
                self.assignValues(t, v)

    def doLayout(self, outSiteX, outSiteY, layout):
        for tgtList in self.tgtLists:
            tgtList.doLayout(layout)
        self.valueList.doLayout(layout)
        layout.updateSiteOffsets(self.sites.seqIn)
        layout.doSubLayouts(self.sites.seqIn, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.seqIn.xOffset
        y = outSiteY - self.sites.seqIn.yOffset
        self.rect = (x, y, x + width, y + height)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        opWidth, opHeight = self.opSize
        layout = Layout(self, opWidth, opHeight, self.sites.seqIn.yOffset)
        # Calculate for assignment target lists (each clause of =)
        x = inpSeqImage.width - 1
        y = inpSeqImage.height // 2 - 1
        for tgtList in self.tgtLists:
            tgtWidth = tgtList.calcLayout(layout, x, y)
            x += tgtWidth + opWidth - 2
        # Calculate layout for assignment value(s)
        layout.width = x + 1
        self.valueList.calcLayout(layout, x, y)
        return layout

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        clipData = [addPoints(location, offset)]
        for tgtList in self.tgtLists:
            tgts = []
            for site in getattr(self.sites, tgtList.siteSeriesName):
                tgts.append(None if site.att is None else site.att.clipboardRepr(offset))
            clipData.append(tuple(tgts))
        values = []
        for site in self.sites.values:
            values.append(None if site.att is None else site.att.clipboardRepr(offset))
        clipData.append(tuple(values))
        return (self.__class__.__name__, tuple(clipData))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location = clipData[0]
        values = clipData[-1]
        targets = clipData[1:-1]
        ic = AssignIcon(window, (addPoints(location, offset)))
        if len(targets) > 1:
            for i in range(1, len(targets)):
                ic.addTargetGroup(i)
        for i, tgt in enumerate(targets):
            tgtIcons = clipboardDataToIcons(tgt, window, offset)
            ic.insertChildren(tgtIcons, "targets%d" % i, 0)
        ic.insertChildren(clipboardDataToIcons(values, window, offset), "values", 0)
        return ic

class DivideIcon(Icon):
    def __init__(self, window, location=None, floorDiv=False):
        Icon.__init__(self, window)
        self.precedence = 11
        self.floorDiv = floorDiv
        emptyArgHeight = 14
        self.emptyArgSize = (EMPTY_ARG_WIDTH, emptyArgHeight)
        self.topArgSize = self.emptyArgSize
        self.bottomArgSize = self.emptyArgSize
        width, height = self._size()
        outSiteY = self.topArgSize[1] + 2
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('topArg', 'input', 2, outSiteY - emptyArgHeight // 2 - 2)
        self.sites.add('bottomArg', 'input', 2, outSiteY + emptyArgHeight // 2 + 2)
        self.sites.add('attrIcon', 'attrIn', width - 1, outSiteY + ATTR_SITE_OFFSET)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, emptyArgHeight - 2)
        self.sites.add('seqOut', 'seqOut', seqX, emptyArgHeight + 5)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        topWidth, topHeight = self.topArgSize
        bottomWidth, bottomHeight = self.bottomArgSize
        width = max(topWidth, bottomWidth) + 3 + outSiteImage.width
        height = topHeight + bottomHeight + 3
        return width, height

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and image is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or image is not None)
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            width, height = self._size()
            self.cachedImage = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
            # Input sites
            leftX = self.sites.output.xOffset
            cntrY = self.sites.output.yOffset
            topArgX = self.sites.topArg.xOffset
            topArgY = self.sites.topArg.yOffset - floatInImage.height // 2
            self.cachedImage.paste(floatInImage, (topArgX, topArgY))
            bottomArgX = self.sites.bottomArg.xOffset
            bottomArgY = self.sites.bottomArg.yOffset - floatInImage.height // 2
            self.cachedImage.paste(floatInImage, (bottomArgX, bottomArgY))
            # Body
            bodyLeft = outSiteImage.width - 1
            bodyRight = width - 1
            bodyTop = cntrY - 5
            bodyBottom = cntrY + 5
            draw = ImageDraw.Draw(self.cachedImage)
            draw.rectangle((bodyLeft, bodyTop, bodyRight, bodyBottom),
             outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
            if needSeqSites:
                drawSeqSites(self.cachedImage, bodyLeft, bodyTop, bodyBottom-bodyTop+1)
            if self.floorDiv:
                cntrX = (bodyLeft + bodyRight) // 2
                draw.line((bodyLeft + 2, cntrY, cntrX - 1, cntrY), fill=BLACK)
                draw.line((cntrX + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            else:
                draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            if needOutSite:
                self.cachedImage.paste(outSiteImage,
                 (leftX, cntrY - outSiteImage.height//2))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        # If rectangle passes horizontally above or below the central body of the icon,
        # it is considered to not be touching
        rectLeft, rectTop, rectRight, rectBottom = rect
        centerY = self.rect[1] + self.sites.output.yOffset
        iconTop = centerY - 5
        iconBottom = centerY + 5
        if rectBottom < iconTop or rectTop > iconBottom:
            return False
        return True

    def doLayout(self, outSiteX, outSiteY, layout):
        self.topArgSize = layout.topArgSize
        self.bottomArgSize = layout.bottomArgSize
        self.sites.output.yOffset = layout.parentSiteOffset
        layout.updateSiteOffsets(self.sites.output)
        self.sites.seqIn.yOffset = layout.parentSiteOffset - 4
        self.sites.seqOut.yOffset = layout.parentSiteOffset + 4
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        if self.sites.topArg.att is None:
            tArgLayout = None
            tArgWidth, tArgHeight = self.emptyArgSize
            tArgSiteOffset = tArgHeight // 2
        else:
            tArgLayout = self.sites.topArg.att.calcLayout()
            tArgWidth = tArgLayout.width
            tArgHeight = tArgLayout.height
            tArgSiteOffset = tArgLayout.parentSiteOffset
        if self.sites.bottomArg.att is None:
            bArgLayout = None
            bArgWidth, bArgHeight = self.emptyArgSize
            bArgSiteOffset = bArgHeight // 2
        else:
            bArgLayout = self.sites.bottomArg.att.calcLayout()
            bArgWidth = bArgLayout.width
            bArgHeight = bArgLayout.height
            bArgSiteOffset = bArgLayout.parentSiteOffset
        width = max(tArgWidth, bArgWidth) + 4
        height = tArgHeight + bArgHeight + 3
        siteYOff = tArgHeight + 1
        layout = Layout(self, width, height, siteYOff)
        layout.topArgSize = tArgWidth, tArgHeight
        layout.bottomArgSize = bArgWidth, bArgHeight
        layout.addSubLayout(tArgLayout, 'topArg', (width - tArgWidth) // 2,
         - tArgHeight + tArgSiteOffset - 1)
        layout.addSubLayout(bArgLayout, 'bottomArg', (width - bArgWidth) // 2,
         + bArgSiteOffset + 2)
        if self.sites.attrIcon.att is not None:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        else:
            attrLayout = None
        layout.addSubLayout(attrLayout, 'attrIcon', width, ATTR_SITE_OFFSET)
        return layout

    def textRepr(self):
        if self.sites.topArg.att is None:
            topArgText = "None"
        else:
            topArgText = self.sites.topArg.att.textRepr()
        if self.sites.bottomArg.att is None:
            bottomArgText = "None"
        else:
            bottomArgText = self.sites.bottomArg.att.textRepr()
        op = '//' if self.floorDiv else '/'
        text = topArgText + " " + op + " " + bottomArgText
        if needsParens(self, forText=True):
            return "(" + text + ")"
        return text

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        if self.sites.topArg.att is None:
            topArg = None
        else:
            topArg = self.sites.topArg.att.clipboardRepr(offset)
        if self.sites.bottomArg.att is None:
            bottomArg = None
        else:
            bottomArg = self.sites.bottomArg.att.clipboardRepr(offset)
        return self.__class__.__name__, (addPoints(location, offset), (topArg, bottomArg))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location, children = clipData
        ic = DivideIcon(window, (addPoints(location, offset)))
        topArg, bottomArg = clipboardDataToIcons(children, window, offset)
        ic.sites.topArg.attach(ic, topArg)
        ic.sites.bottomArg.attach(ic, bottomArg)
        return ic

    def leftAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return True

    def rightAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return False

    def execute(self):
        if self.sites.topArg.att is None:
            raise IconExecException(self, "Missing numerator")
        if self.sites.bottomArg.att is None:
            raise IconExecException(self, "Missing denominator")
        topValue = self.sites.topArg.att.execute()
        bottomValue = self.sites.bottomArg.att.execute()
        try:
            if self.floorDiv:
                result = operator.floordiv(topValue, bottomValue)
            else:
                result = operator.truediv(topValue, bottomValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class ImageIcon(Icon):
    def __init__(self, image, window, location=None):
        Icon.__init__(self, window)
        self.cachedImage = self.image = image.convert('RGBA')
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + image.width, y + image.height)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        pasteImageWithClip(image, tintSelectedImage(self.image, self.selected,
         colorErr), location, clip)

    def snapLists(self):
        return {}

    def layout(self, location=None):
        # Can't use Base class layout method because it depends on having an output site
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def doLayout(self, x, bottom, _layout):
        self.rect = (x, bottom - self.image.height, x + self.image.width, bottom)
        self.layoutDirty = False

    def calcLayout(self):
        return Layout(self, self.image.width, self.image.height, 0)

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        # ... base64 encode a jpeg
        return "TextIcon", ("TODO", addPoints(location, offset))

    @staticmethod
    def fromClipboard(_clipData, _window, _locationOffset):
        # ... base64 decode a jpeg
        # image, location = clipData
        return None

    def execute(self):
        return None

class Layout:
    """Structure to store the information that the icon has calculated about how it
    should be laid out (in calcLayout), until all the calculations are done and the
    layout is implemented (in doLayout).  The icon may also add its own externally-defined
    fields to the object for icon-specific data"""
    def __init__(self, ico, width, height, siteYOffset):
        self.icon = ico
        self.width = width
        self.height = height
        self.parentSiteOffset = siteYOffset
        self.subLayouts = {}
        self.siteOffsets = {}

    def addSubLayout(self, subLayout, siteName, xSiteOffset, ySiteOffset):
        """Incorporate the area of subLayout as positioned at (xSiteOffset, ySiteOffset)
        relative to the implied site of the current layout.  subLayout can also be
        passed as None, in which case add a None to the sublayouts list."""
        self.subLayouts[siteName] = subLayout
        self.siteOffsets[siteName] = (xSiteOffset, ySiteOffset)
        if subLayout is None or xSiteOffset is None:
            return
        heightAbove = max(self.parentSiteOffset, subLayout.parentSiteOffset - ySiteOffset)
        heightBelow = max(self.height - self.parentSiteOffset, ySiteOffset +
         subLayout.height - subLayout.parentSiteOffset)
        self.height = heightAbove + heightBelow
        self.parentSiteOffset = heightAbove
        self.width = max(self.width, xSiteOffset + subLayout.width-1)

    def updateSiteOffsets(self, parentSite):
        parentSiteDepth = siteDepths[parentSite.type]
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name)
            siteDepth = siteDepths[site.type]
            xOffset, yOffset = self.siteOffsets[name]
            site.xOffset = parentSite.xOffset + parentSiteDepth - siteDepth + xOffset
            site.yOffset = parentSite.yOffset + yOffset

    def doSubLayouts(self, parentSite, outSiteX, outSiteY):
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name)
            if site.att is not None:
                x = outSiteX + site.xOffset - parentSite.xOffset
                y = outSiteY + site.yOffset - parentSite.yOffset
                site.att.doLayout(x, y, layout)

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

def tintSelectedImage(image, selected, colorErr):
    if not selected and not colorErr:
        return image
    # ... This is wasteful and should be an image filter if I can figure out how to
    # make one properly
    if colorErr:
        color = ERR_TINT
    else:
        color = SELECT_TINT
    alphaImg = image.getchannel('A')
    colorImg = Image.new('RGBA', (image.width, image.height), color=color)
    colorImg.putalpha(alphaImg)
    selImg = Image.blend(image, colorImg, .15)
    return selImg

def needsParens(ic, parent=None, forText=False):
    """Returns True if the BinOpIcon, ic, should have parenthesis.  Specify "parent" to
    compute for a parent which is not the actual icon parent.  If forText is True, ic
    can also be a DivideIcon, and the calculation is appropriate to text rather than
    icons, where division is just another binary operator and not laid out numerator /
    denominator."""
    if parent is None:
        parent = ic.parent()
    if parent is None:
        return False
    # Unclosed cursor-parens count as a left-paren, but not a right-paren
    if parent.__class__.__name__ == "CursorParenIcon" and not parent.closed:
        parenParent = parent.parent()
        if parenParent is None or parenParent.__class__ is not BinOpIcon or \
         parenParent.siteOf(parent) != "leftArg":
            return False
        parent = parenParent
    arithmeticOpClasses = (BinOpIcon, UnaryOpIcon)
    if forText:
        arithmeticOpClasses += (DivideIcon,)
    if parent.__class__ not in arithmeticOpClasses:
        return False
    if ic.precedence > parent.precedence:
        return False
    if ic.precedence < parent.precedence:
        return True
    # Precedence is equal to parent.  Look at associativity
    if parent.siteOf(ic, recursive=True) == "leftArg" and ic.rightAssoc():
        return True
    if parent.siteOf(ic, recursive=True) == "rightArg" and ic.leftAssoc():
        return True
    return False

def findLeftOuterIcon(clickedIcon, fromIcon, btnPressLoc):
    """Because we have icons with no pickable structure left of their arguments (binary
    operations), we have to make rules about what it means to click or drag the leftmost
    icon in an expression.  For the purpose of selection, that is simply the icon that was
    clicked.  For dragging and double clicking (execution), this function finds the
    outermost operation that claims the clicked icon as its leftmost operand."""
    # One idiotic case we have to distinguish, is when the clicked icon is a BinOpIcon
    # with automatic parens visible: only if the user clicked on the left paren can
    # the icon be the leftmost object in an expression.  Clicking on the body or the
    # right paren does not count.
    if clickedIcon.__class__ is BinOpIcon and clickedIcon.hasParens:
        if not clickedIcon.locIsOnLeftParen(btnPressLoc):
            return clickedIcon
    if clickedIcon is fromIcon:
        return clickedIcon
    # Only binary operations are candidates, and only when the expression directly below
    # has claimed itself to be the leftmost operand of an expression
    if fromIcon.__class__ is AssignIcon:
        leftSiteIcon = fromIcon.sites.targets0[0].att
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, leftSiteIcon, btnPressLoc)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is BinOpIcon and fromIcon.leftArg() is not None:
        left = findLeftOuterIcon(clickedIcon, fromIcon.leftArg(), btnPressLoc)
        if left is fromIcon.leftArg():
            targetIsBinOpIcon = clickedIcon.__class__ is BinOpIcon
            if not targetIsBinOpIcon or targetIsBinOpIcon and clickedIcon.hasParens:
                # Again, we have to check before claiming outermost status for fromIcon,
                # if its left argument has parens, whether its status as outermost icon
                # was earned by promotion or by a direct click on its parens.
                if left.__class__ is not BinOpIcon or not left.hasParens or \
                 left.locIsOnLeftParen(btnPressLoc):
                    return fromIcon  # Claim outermost status for this icon
        # Pass on status from non-contiguous expressions below fromIcon in the hierarchy
        if left is not None:
            return left
        if fromIcon.rightArg() is None:
            return None
        return findLeftOuterIcon(clickedIcon, fromIcon.rightArg(), btnPressLoc)
    # Pass on any results from below fromIcon in the hierarchy
    children = fromIcon.children()
    if children is not None:
        for child in fromIcon.children():
            result = findLeftOuterIcon(clickedIcon, child, btnPressLoc)
            if result is not None:
                return result
    return None

def drawSeqSites(img, boxLeft, boxTop, boxHeight):
    """Draw sequence (in and out) sites on a rectangular boxed icon"""
    img.putpixel((boxLeft+1, boxTop+1), BLACK)
    img.putpixel((boxLeft+2, boxTop+1), OUTLINE_COLOR)
    img.putpixel((boxLeft+2, boxTop+2), OUTLINE_COLOR)
    img.putpixel((boxLeft+1, boxTop+2), OUTLINE_COLOR)
    bottomSiteY = boxTop + boxHeight - 2
    img.putpixel((boxLeft+1, bottomSiteY), BLACK)
    img.putpixel((boxLeft+2, bottomSiteY), OUTLINE_COLOR)
    img.putpixel((boxLeft+2, bottomSiteY-1), OUTLINE_COLOR)
    img.putpixel((boxLeft+1, bottomSiteY-1), OUTLINE_COLOR)

class IconSite:
    def __init__(self, siteName, siteType, xOffset=0, yOffset=0):
        self.name = siteName
        self.type = siteType
        self.xOffset = xOffset
        self.yOffset = yOffset
        self.att = None

    def attach(self, ownerIcon, fromIcon, fromSiteId=None):
        # Remove original link from attached site
        if self.att:
            backLinkSite = self.att.siteOf(ownerIcon)
            if backLinkSite is not None:
                self.att.sites.lookup(backLinkSite).att = None
        else:
            backLinkSite = None
        ownerIcon.window.undo.registerAttach(ownerIcon, self.name, self.att, backLinkSite)
        # If attaching None (removing attachment), no bidirectional link to make
        if fromIcon is None:
            self.att = None
            return
        # Determine the back-link
        if fromSiteId is None:
            siteType = matingSiteType[self.type]
            sites = fromIcon.sites.sitesOfType(siteType)
            if sites is None or len(sites) == 0:
                print("Failed to find appropriate back-link for attaching", ownerIcon,
                 "site", self.name, "to", fromIcon, "type", siteType)
                return
            fromSiteId = sites[0]
            if len(sites) != 1:
                print("Attaching icon,", ownerIcon, "site", self.name, "to", fromIcon,
                 "site", fromSiteId, "but multiple targets made choice ambiguous")
        fromSite = fromIcon.sites.lookup(fromSiteId)
        if fromSite is None:
            if fromIcon.sites.isSeries(fromSiteId):
                print("Could not attach icon: parent link points to series", fromSiteId)
            else:
                print("Could not attach icon: invalid back-link (fromSiteId)", fromSiteId)
            return
        # Make the (bidirectional) link
        self.att = fromIcon
        fromSite.att = ownerIcon

class IconSiteSeries:
    def __init__(self, name, siteType, initCount=0, initOffsets=None):
        self.type = siteType
        self.name = name
        self.sites = [None] * initCount
        for idx in range(initCount):
            if initOffsets is not None and idx < len(initOffsets):
                xOff, yOff = initOffsets[idx]
            else:
                xOff, yOff = 0, 0
            self.sites[idx] = IconSite(makeSeriesSiteId(name, idx), siteType, xOff, yOff)

    def __getitem__(self, idx):
        return self.sites[idx]

    def __len__(self):
        return len(self.sites)

    def insertSite(self, insertIdx):
        site = IconSite(makeSeriesSiteId(self.name, insertIdx), self.type)
        self.sites[insertIdx:insertIdx] = [site]
        for i in range(insertIdx+1, len(self.sites)):
            self.sites[i].name = makeSeriesSiteId(self.name, i)

    def removeSite(self, ic, idx):
        del self.sites[idx]
        for i in range(idx, len(self.sites)):
            self.sites[i].name = makeSeriesSiteId(self.name, i)

class IconSiteList:
    """
    @DynamicAttrs
    """
    def __init__(self):
        self._typeDict = {}

    def lookup(self, siteId):
        """External to the icon, sites are usually identified by name, but older code
        did so with a tuple: (site-type, site-index).  If siteId is just a name, it is
        in the this object's dictionary.  If it's an old-style tuple, print a warning
        and translate."""
        # If it is an individual site, it will be in the object's dictionary
        siteId = self.siteIdWarn(siteId)
        if hasattr(self, siteId):
            site = getattr(self, siteId)
            if isinstance(site, IconSite):
                return site
            print("site lookup failed 1")
            return None
        # If it is a series site, split the name up in to the series name and index
        # and return the site by-index from the series
        seriesName, seriesIndex = splitSeriesSiteId(siteId)
        if seriesName is None:
            print("site lookup failed 2")
            return None
        series = getattr(self, seriesName)
        if not isinstance(series, IconSiteSeries) or seriesIndex >= len(series):
            print("site lookup failed 3")
            return None
        return series[seriesIndex]

    def lookupSeries(self, seriesName):
        series = getattr(self, self.siteIdWarn(seriesName))
        return series if isinstance(series, IconSiteSeries) else None

    def siteIdWarn(self, idOrTypeAndIdx):
        """Temporary routine until all instances of ("siteType", idx) are removed"""
        if isinstance(idOrTypeAndIdx, tuple):
            print("Old style type+idx encountered")
            siteType, idx = idOrTypeAndIdx
            return self._typeDict[siteType][idx]
        return idOrTypeAndIdx

    def sitesOfType(self, siteType):
        return self._typeDict.get(siteType)

    def isSeries(self, siteId):
        return self.getSeries(siteId) is not None

    def allSites(self):
        """Traverse all sites in the list (generator)"""
        for siteNames in self._typeDict.values():
            for name in siteNames:
                site =getattr(self, name)
                if isinstance(site, IconSiteSeries):
                    for s in site.sites:
                        yield s
                elif isinstance(site, IconSite):
                    yield site

    def siteOfAttachedIcon(self, ic):
        for site in self.allSites():
            if site.att == ic:
                return site
        return None

    def childSites(self):
        childList = []
        for siteType, siteNames in self._typeDict.items():
            if siteType in childSiteTypes:
                for name in siteNames:
                    site = getattr(self, name)
                    if isinstance(site, IconSiteSeries):
                        childList += site.sites
                    else:
                        childList.append(site)
        return childList

    def parentSites(self):
        parentList = []
        for siteType, siteNames in self._typeDict.items():
            if siteType in parentSiteTypes:
                for name in siteNames:
                    site = getattr(self, name)
                    if isinstance(site, IconSiteSeries):
                        parentList += site.sites
                    else:
                        parentList.append(site)
        return parentList

    def add(self, name, siteType, xOffset=0, yOffset=0):
        """Add a new icon site to the site list given name and type.  Optionally add
        offset from the icon origin (sometimes these are not known until the icon has
        been through layout).  The ordering of calls to add determines the order in which
        sites will be traversed."""
        setattr(self, name, IconSite(name, siteType, xOffset, yOffset))
        if siteType not in self._typeDict:
            self._typeDict[siteType] = []
        self._typeDict[siteType].append(name)

    def addSeries(self, name, siteType, initCount=0, initOffsets=None):
        setattr(self, name, IconSiteSeries(name, siteType, initCount, initOffsets))
        if siteType not in self._typeDict:
            self._typeDict[siteType] = []
        self._typeDict[siteType].append(name)

    def removeSeries(self, name):
        series = getattr(self, name)
        delattr(self, name)
        self._typeDict[series.type].remove(name)

    def renameSeries(self, oldName, newName):
        series = self.getSeries(oldName)
        for idx, site in enumerate(series.sites):
            site.name = makeSeriesSiteId(newName, idx)
        series.name = newName
        delattr(self, oldName)
        setattr(self, newName, series)
        self._typeDict[series.type].remove(oldName)
        self._typeDict[series.type].append(newName)

    def getSeries(self, siteIdOrSeriesName):
        """If siteId is the part of a series, return a list of all of the sites in the
        list.  Otherwise return None"""
        if hasattr(self, siteIdOrSeriesName):
            seriesName = siteIdOrSeriesName
        else:
            seriesName, seriesIndex = splitSeriesSiteId(siteIdOrSeriesName)
            if seriesName is None:
                return None
        if hasattr(self, seriesName):
            series = getattr(self, seriesName)
            if isinstance(series, IconSiteSeries):
                return series
        return None

    def remove(self, name):
        """Delete a (non-series) icon site."""
        if hasattr(self, name):
            site = getattr(self, name)
            if isinstance(site, IconSite):
                delattr(self, name)
                self._typeDict[site.type].remove(name)

    def removeSeriesSiteById(self, ic, siteId):
        """Remove a site from a series given siteId (which encodes index)"""
        name, idx = splitSeriesSiteId(siteId)
        if name is None:
            print("failed to remove series site", siteId)
        else:
            self.removeSeriesSiteByNameAndIndex(ic, name, idx)

    def removeSeriesSiteByNameAndIndex(self, ic, seriesName, idx):
        """Remove a site from a series given the series name and index"""
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries):
            if len(series.sites) == 1:  # Leave a single site for insertion
                series.sites[0].attach(ic, None)
            else:
                series.sites[idx].attach(ic, None)
                series.removeSite(ic, idx)
                ic.window.undo.registerRemoveSeriesSite(ic, seriesName, idx)

    def insertSeriesSiteById(self, ic, siteId):
        name, idx = splitSeriesSiteId(siteId)
        if name is None:
            print("failed to insert series site", siteId)
        else:
            self.insertSeriesSiteByNameAndIndex(ic, name, idx)

    def insertSeriesSiteByNameAndIndex(self, ic, seriesName, insertIdx):
        ic.window.undo.registerInsertSeriesSite(ic, seriesName, insertIdx)
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries):
            series.insertSite(insertIdx)

    def makeSnapLists(self, ic, x, y, forCursor=False):
        snapSites = {}
        for site in self.allSites():
            # Omit any site whose attached icon has a site of the same type, at the
            # same location.  In such a case we want both dropped icons and typing to
            # go to the site of the innermost (most local) icon.
            if isCoincidentSite(site.att, site.name):
                continue
            # Numeric icons have attribute sites for cursor, only (no snapping)
            if site.type == 'attrIn' and not forCursor and isinstance(ic, NumericIcon):
                continue
            # seqIn and seqOut sites are only valid for icons at the top level
            if site.type in ('seqIn', 'seqOut') and ic.parent() is not None:
                continue
            # The first icon in a sequence hosts the snap site for the sequence
            hasPrev = ic.prevInSeq() is not None
            if hasPrev and site.type in ('output', 'seqInsert'):
                continue
            # If the icon is in a sequence, convert the output site to a seqInsert
            hasNext = ic.nextInSeq()
            if site.type == 'output' and (hasPrev or hasNext):
                siteType = 'seqInsert'
            else:
                siteType = site.type
            # If the icon has an attrIn site with something connected, also give it an
            # insertAttr site
            if site.type == 'attrIn' and ic.sites.attrIcon.att is not None:
                snapSites['insertAttr'] = [(ic, (x + site.xOffset,
                 y + site.yOffset + INSERT_SITE_Y_OFFSET), site.name)]
            # Add the snap site to the list
            if siteType not in snapSites:
                snapSites[siteType] = []
            snapSites[siteType].append((ic, (x + site.xOffset, y + site.yOffset),
             site.name))
        return snapSites

def isCoincidentSite(ic, siteId):
    return ic is not None and siteId == ic.hasCoincidentSite()

class HorizListMgr:
    """Manage layout for a horizontal list of icon arguments."""
    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)])
        self.emptyInOffsets = (0, LIST_EMPTY_ARG_WIDTH)
        self.inOffsets = self.emptyInOffsets

    def drawCommas(self, image, leftSiteX, leftSiteY):
        commaXOffset = leftSiteX + inSiteImage.width - commaImage.width
        commaY = leftSiteY - commaImageSiteYOffset
        for inOff in self.inOffsets[1:-1]:
            image.paste(commaImage, (inOff + commaXOffset, commaY))

    def width(self):
        return self.inOffsets[-1] + 1

    def makeInsertSnapList(self):
        """Generate snap sites for item insertion"""
        insertSites = []
        inputSites = self.icon.sites.getSeries(self.siteSeriesName)
        if len(inputSites) > 1 or len(inputSites) == 1 and inputSites[0].att is not None:
            x, y = self.icon.rect[:2]
            x += INSERT_SITE_X_OFFSET
            y += inputSites[0].yOffset + INSERT_SITE_Y_OFFSET
            idx = 0
            for idx, site in enumerate(inputSites):
                insertSites.append((self.icon, (x + site.xOffset, y),
                 site.name))
            x += inputSites[0].xOffset + self.inOffsets[-1]
            siteName = makeSeriesSiteId(inputSites.name, idx + 1)
            insertSites.append((self.icon, (x, y), siteName))
        return insertSites

    def doLayout(self, layout):
        """Updates the icon spacing for the list as calculated in the calcLayout method.
        This does not call doLayout for the icons in the list (but calcLayout adds the
        information to the icon layout such that layout.doSubLayouts will do them along
        with the rest of the attached icons)."""
        self.inOffsets = getattr(layout, self.siteSeriesName + "InOffsets")

    def calcLayout(self, layout, leftSiteX, leftSiteY):
        """Calculates sub-layouts for icons attached to the list and adds them to layout.
        Returns the width of the list. leftSiteX and leftSiteY are offsets from the icon
        output site (as used in calcLayout and doLayout), not from the icon origin.  The
        icon doLayout method should call the doLayout method, above, with the chosen
        layout to update icon spacings for the list."""
        width = 0
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        inOffsets = [0]
        for site in siteSeries:
            if site.att is None:
                layout.addSubLayout(None, site.name, leftSiteX + width, leftSiteY)
                width += LIST_EMPTY_ARG_WIDTH + commaImage.width - 1
            else:
                childLayout = site.att.calcLayout()
                layout.addSubLayout(childLayout, site.name, leftSiteX + width, leftSiteY)
                width += childLayout.width - 1 + commaImage.width - 1
            inOffsets.append(width)
        inOffsets[-1] -= (commaImage.width - 1)
        # Pass information doLayout will need to reconfigure
        setattr(layout, self.siteSeriesName + "InOffsets", inOffsets)
        return inOffsets[-1] + 1

    def rename(self, newName):
        self.icon.sites.renameSeries(self.siteSeriesName, newName)
        self.siteSeriesName = newName

def drawSeqSiteConnection(toIcon, image=None, clip=None):
    """Draw connection line between ic's seqIn site and whatever it connects."""
    fromIcon = toIcon.prevInSeq()
    if fromIcon is None:
        return
    fromX, fromY = fromIcon.posOfSite('seqOut')
    toX, toY = toIcon.posOfSite('seqIn')
    if clip is not None:
        # Clip the line to within the clip rectangle.  This is simplified by the fact
        # that connections are always vertical and drawn downward from seqOut to seqIn,
        # and that rectangles are defined ordered left, top, right, bottom.
        l, t, r, b = clip
        if fromX < l or fromX > r:
            return
        if fromY < t:
            if toY < t:
                return
            fromY = t
        if toY > b:
            if fromY > b:
                return
            toY = b
    if image is None:
        draw = fromIcon.window.draw
    else:
        draw = ImageDraw.Draw(image)
    draw.line((fromX, fromY, toX, toY), BLACK)

def seqConnectorTouches(toIcon, rect):
    """Return True if the icon is connected via its seqIn site and the sequence site
    connector line intersects rectangle, rect."""
    fromIcon = toIcon.prevInSeq()
    if fromIcon is None:
        return False
    fromX, fromY = fromIcon.posOfSite('seqOut')
    toX, toY = toIcon.posOfSite('seqIn')
    l, t, r, b = rect
    if fromX < l or fromX > r:
        return False
    if fromY < t and toY < t:
        return False
    if toY > b and fromY > b:
        return False
    return True

def findSeqStart(ic):
    while True:
        if not hasattr(ic.sites, 'seqIn'):
            return ic
        if ic.sites.seqIn.att is None:
            return ic
        ic = ic.sites.seqIn.att

def findSeqEnd(ic):
    for seqEndIc in traverseSeq(ic):
        pass
    return seqEndIc

def traverseSeq(ic, includeStartingIcon=True):
    if includeStartingIcon:
        yield ic
    while True:
        if not hasattr(ic.sites, 'seqOut'):
            return
        if ic.sites.seqOut.att is None:
            return
        ic = ic.sites.seqOut.att
        yield ic

def insertSeq(seqStartIc, atIc, before=False):
    seqEndIc = findSeqEnd(seqStartIc)
    if before:
        prevIcon = atIc.sites.seqIn.att
        if prevIcon is not None:
            prevIcon.replaceChild(seqStartIc, 'seqOut')
        atIc.replaceChild(seqEndIc, 'seqIn')
    else:
        nextIcon = atIc.sites.seqOut.att
        atIc.replaceChild(seqStartIc, 'seqOut')
        if nextIcon is not None:
            nextIcon.replaceChild(seqEndIc, 'seqIn')

def traverseAttrs(ic, includeStart=True):
    if includeStart:
        yield ic
    while hasattr(ic.sites, 'attrIcon') and ic.sites.attrIcon.att != None:
        ic = ic.sites.attrIcon.att
        yield ic

def findLastAttrIcon(ic):
    for i in traverseAttrs(ic):
        pass
    return i

def makeSeriesSiteId(seriesName, seriesIdx):
    return seriesName + "_%d" % seriesIdx

def splitSeriesSiteId(siteId):
    splitName = siteId.split('_')
    if len(splitName) != 2:
        return None, None
    name, idx = splitName
    if len(name) == 0 or len(idx) == 0 or not idx.isnumeric():
        return None, None
    return name, int(idx)

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