# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw, ImageFont
import python_g
import ast
import math
import operator
import re

globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)

isSeriesRe = re.compile(".*_\\d*$")

binOpPrecedence = {'+':10, '-':10, '*':11, '/':11, '//':11, '%':11, '**':14,
 '<<':9, '>>':9, '|':6, '^':7, '&':8, '@':11, 'and':3, 'or':2, 'in':5, 'not in':5,
 'is':5, 'is not':5, '<':5, '<=':5, '>':5, '>=':5, '==':5, '!=':5, '=':-1, ':':-1}

unaryOpPrecedence = {'+':12, '-':12, '~':13, 'not':4, '*':-1, '**':-1}

binOpFn = {'+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv,
 '//':operator.floordiv, '%':operator.mod, '**':operator.pow, '<<':operator.lshift,
 '>>':operator.rshift, '|':operator.or_, '^':operator.xor, '&':operator.and_,
 '@':lambda x,y:x@y, 'and':lambda x,y:x and y, 'or':lambda x,y:x or y,
 'in':lambda x,y:x in y, 'not in':lambda x,y:x not in y, 'is':operator.is_,
 'is not':operator.is_not, '<':operator.lt, '<=':operator.le, '>':operator.gt,
 '>=':operator.ge, '==':operator.eq, '!=':operator.ne}

unaryOpFn = {'+':operator.pos, '-':operator.neg, '~':operator.inv, 'not':operator.not_,
 '*':lambda a:a, '**': lambda a:a}

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
SEQ_RULE_COLOR = (165, 180, 165, 255)
SEQ_CONNECT_COLOR = (70, 100, 70, 255)

DEPTH_EXPAND = 4

EMPTY_ARG_WIDTH = 11
LIST_EMPTY_ARG_WIDTH = 4
SLICE_EMPTY_ARG_WIDTH = 1

# Pixels below input/output site to place function/list/tuple icons insertion site
INSERT_SITE_X_OFFSET = 2
INSERT_SITE_Y_OFFSET = 5

# Number of pixels to indent a code block
BLOCK_INDENT = 16

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

dimAttrOutPixmap = (
 "oo",
 "oo",
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
 "o %7o",
 "o8%7o",
 "o%8 o",
 "o   o",
 "ooooo",
)
commaImageSiteYOffset = 3

colonPixmap = (
 "ooooo",
 "o   o",
 "o %6o",
 "o   o",
 "o  o.",
 "o o..",
 "o  o.",
 "o   o",
 "o %6o",
 "o   o",
 "ooooo",
)
colonImageSiteYOffset = 5

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
 "o  83  o",
 "o  58 o.",
 "o 58  o.",
 "o      o",
 "oooooooo",
)

listLBktPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o  %%% o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %7  o",
 "o  %%% o",
 "o      o",
 "oooooooo",
)

listRBktPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o %%%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7% o.",
 "o  7% o.",
 "o %%%  o",
 "o      o",
 "oooooooo",
)

subscriptLBktPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o  %%  o",
 "o  %%  o",
 "o  %   o",
 "o  %   o",
 "o  %   o",
 "o  %   o",
 "o  %   o",
 "o  %   o",
 "o  %   o",
 "o  %%  o",
 "o  %%  o",
 "o      o",
 "o      o",
 "oooooooo",
)

subscriptRBktPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o  %%  o",
 "o  %%  o",
 "o   %  o",
 "o   %  o",
 "o   %  o",
 "o   %  o",
 "o   %  o",
 "o   %  o",
 "o   %  o",
 "o  %% o.",
 "o  %% o.",
 "o      o",
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

fnLParenPixmap = (
 ".oooooooo",
 ".o      o",
 ".o      o",
 ".o      o",
 ".o    84o",
 ".o   81 o",
 ".o   28 o",
 ".o  73  o",
 ".o  56 o.",
 ".o  48o..",
 ".o  19 o.",
 ".o  19  o",
 ".o  18  o",
 "oo  28  o",
 "oo  68  o",
 ".o      o",
 ".o      o",
 ".oooooooo",
)

fnRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o  82  o",
 "o   29 o",
 "o   38 o",
 "o   37 o",
 "o   37 o",
 "o   38 o",
 "o  829 o",
 "o  74  o",
 "o  38  o",
 "o 65  o.",
 "o85   o.",
 "o      o",
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

dragSeqPixmap = (
 "..ooo",
 ".o%%o",
 "o%%%%",
 ".o%%o",
 "..ooo",
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

branchFootPixmap = (
 "ooooooooooooooooooo",
 "o%o             o%o",
 "ooooooooooooooooooo",
)

renderCache = {}

def iconsFromClipboardString(clipString, window, offset):
    try:
        clipData = ast.literal_eval(clipString)
    except:
        return None
    allIcons = []
    for clipSeq in clipData:
        prevIc = None
        seqIcons = clipboardDataToIcons(clipSeq, window, offset)
        for ic in seqIcons:
            if prevIc is not None:
                ic.replaceChild(prevIc, 'seqIn')
            prevIc = ic
        for ic in seqIcons:
            ic.layout()
        allIcons += seqIcons
    return allIcons

def clipboardDataToIcons(clipData, window, offset):
    subclasses = _getIconClasses()
    pastedIcons = []
    for clipIcon in clipData:
        if clipIcon is None:
            pastedIcons.append(None)
        else:
            iconClassName, *iconData = clipIcon
            iconClass = subclasses[iconClassName]
            iconData = (iconClass, *iconData)
            pastedIcons.append(Icon.fromClipboard(iconData, window, offset))
    return pastedIcons

def clipboardRepr(icons, offset):
    """Top level function for converting icons into their serialized string representation
    for copying to the clipboard.  icons should be a list of just the top-level icons of
    each hierarchy to be copied."""
    remainingIcons = set(icons)
    seqLists = []
    while len(remainingIcons) > 0:
        ic = next(iter(remainingIcons))  # Get an icon from remainingIcons
        sequence = []
        seqStartIc = ic
        for seqIc in traverseSeq(ic, reverse=True):
            if seqIc not in remainingIcons:
                break
            seqStartIc = seqIc
        for seqIc in traverseSeq(seqStartIc):
            if seqIc not in remainingIcons:
                break
            sequence.append(seqIc)
            remainingIcons.remove(seqIc)
        seqLists.append(sequence)
    return repr([[ic.clipboardRepr(offset) for ic in seqList] for seqList in seqLists])

def asciiToImage(asciiPixmap):
    if asciiToImage.asciiMap is None:
        asciiToImage.asciiMap = {'.': (0, 0, 0, 0), 'o': OUTLINE_COLOR,
         ' ': ICON_BG_COLOR, '%': BLACK}
        for i in range(1, 10):
            pixel = int(int(i) * 255 * 0.1)
            asciiToImage.asciiMap[str(i)] = (pixel, pixel, pixel, 255)
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiToImage.asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image
asciiToImage.asciiMap = None

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
dimAttrOutImage = asciiToImage(dimAttrOutPixmap)
leftInSiteImage = asciiToImage(leftInSitePixmap)
commaImage = asciiToImage(commaPixmap)
colonImage = asciiToImage(colonPixmap)
binOutImage = asciiToImage(binOutPixmap)
floatInImage = asciiToImage(floatInPixmap)
lParenImage = asciiToImage(binLParenPixmap)
rParenImage = asciiToImage(binRParenPixmap)
tupleLParenImage = asciiToImage(tupleLParenPixmap)
tupleRParenImage = asciiToImage(tupleRParenPixmap)
fnLParenImage = asciiToImage(fnLParenPixmap)
fnRParenImage = asciiToImage(fnRParenPixmap)
listLBktImage = asciiToImage(listLBktPixmap)
listRBktImage = asciiToImage(listRBktPixmap)
subscriptLBktImage = asciiToImage(subscriptLBktPixmap)
subscriptRBktImage = asciiToImage(subscriptRBktPixmap)
inpSeqImage = asciiToImage(inpSeqPixmap)
binInSeqImage = asciiToImage(binInSeqPixmap)
assignDragImage = asciiToImage(assignDragPixmap)
dragSeqImage = asciiToImage(dragSeqPixmap)
branchFootImage = asciiToImage(branchFootPixmap)

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
        self.drawList = None
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

    def select(self, select=True):
        """Use this method to select or unselect an icon (state can be read from .selected
        member variable, but some icons need to take action on change)."""
        self.selected = select

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

    def traverseBlock(self, includeSelf=True, hier=False):
        """If the icon owns a code block return either all the icons in the code block
        (if hier is True), or just the top level icons in the block (if hier is False)."""
        if includeSelf:
            if hier:
                yield from self.traverse()
            else:
                yield self
        if not hasattr(self, 'blockEnd'):
            return
        for ic in traverseSeq(self, includeStartingIcon=False):
            if ic is self.blockEnd:
                break
            if hier:
                yield from ic.traverse()
            else:
                yield ic
        if includeSelf:
            yield self.blockEnd

    def touchesPosition(self, x, y):
        """Return True if any of the drawn part of the icon falls at x, y"""
        if not pointInRect((x, y), self.rect) or self.drawList is None:
            return False
        for imgOffset, img in self.drawList:
            left, top = addPoints(self.rect[:2], imgOffset)
            imgX = x - left
            imgY = y - top
            if pointInRect((imgX, imgY), (0, 0, img.width, img.height)):
                pixel = img.getpixel((imgX, imgY))
                return pixel[3] > 128
        return False

    def touchesRect(self, rect):
        return python_g.rectsTouch(self.rect, rect)

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

    def parentage(self, includeSelf=False):
        """Returns a list containing the lineage of the given icon, from the icon up to
         the top of the window hierarchy."""
        parentList = []
        if includeSelf:
            parentList.append(self)
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
        self.drawList = None  # Force change at next redraw

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

    def _drawFromDrawList(self, toDragImage, location, clip, colorErr):
        if location is None:
            location = self.rect[:2]
        for imgOffset, img in self.drawList:
            imgLoc = addPoints(location, imgOffset)
            pasteImageWithClip(self.window.image if toDragImage is None else toDragImage,
             tintSelectedImage(img, self.selected, colorErr), imgLoc, clip)

    def _serialize(self, offset, **args):
        currentSeries = None
        children = []
        for site in self.sites.childSites():
            att = self.childAt(site.name)
            childRepr = None if att is None else att.clipboardRepr(offset)
            if isSeriesSiteId(site.name):
                seriesName, idx = splitSeriesSiteId(site.name)
                if currentSeries is None or seriesName != currentSeries[0]:
                    if currentSeries is not None:
                        children.append(currentSeries)
                    currentSeries = [seriesName]
                currentSeries.append(childRepr)
            else:
                if currentSeries is not None:
                    children.append(currentSeries)
                    currentSeries = None
                children.append((site.name, childRepr))
        if currentSeries is not None:
            children.append(currentSeries)
        return self.__class__.__name__, addPoints(self.rect[:2], offset), args, children

    def _restoreChildrenFromClipData(self, childrenClipData, window, offset):
        for childData in childrenClipData:
            siteName, *iconData = childData
            if self.sites.isSeries(siteName):
                self.insertChildren(clipboardDataToIcons(iconData, window, offset),
                 siteName, 0)
            else:
                getattr(self.sites, siteName).attach(self,
                 clipboardDataToIcons(iconData, window, offset)[0])

    def clipboardRepr(self, offset):
        return self._serialize(offset)

    @staticmethod
    def fromClipboard(clipData, window, offset):
        iconClass, location, args, childData = clipData
        ic = iconClass(**args, window=window, location = addPoints(location, offset))
        ic._restoreChildrenFromClipData(childData, window, offset)
        return ic

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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text, self.bodySize[1])
            img.paste(txtImg, (outSiteImage.width - 1, 0))
            if needSeqSites:
                drawSeqSites(img, outSiteImage.width-1, 0, txtImg.height)
            if needOutSite:
                outX = self.sites.output.xOffset
                outY = self.sites.output.yOffset - outSiteImage.height // 2
                img.paste(outSiteImage, (outX, outY), mask=outSiteImage)
            if self.hasAttrIn:
                attrX = self.sites.attrIcon.xOffset
                attrY = self.sites.attrIcon.yOffset
                img.paste(attrInImage, (attrX, attrY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.drawList = None  # Draw or undraw sequence sites ... refine when sites added
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
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def clipboardRepr(self, offset):
        return self._serialize(offset, text=self.text)

class IdentifierIcon(TextIcon):
    def __init__(self, name, window=None, location=None):
        _w, minTxtHgt = globalFont.getsize("Mg_")
        TextIcon.__init__(self, name, window, location, minTxtHgt=minTxtHgt)
        self.name = name

    def execute(self):
        if self.name in namedConsts:
            value = namedConsts[self.name]
        elif self.name in globals():
            value = globals()[self.name]
        else:
            raise IconExecException(self, self.name + " is not defined")
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(value)
        return value

    def clipboardRepr(self, offset):
        return self._serialize(offset, name=self.name)

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
        return self._serialize(offset, value=self.value)

class StringIcon(TextIcon):
    def __init__(self, string, window=None, location=None):
        TextIcon.__init__(self, repr(string), window, location)
        self.string = string

    def execute(self):
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(self.string)
        return self.string

    def clipboardRepr(self, offset):
        return self._serialize(offset, string=self.string)

class AttrIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        bodyWidth, _h = globalFont.getsize(self.name)
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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.name, self.bodySize[1])
            img.paste(txtImg, (attrOutImage.width - 1, 0))
            attrOutX = self.sites.attrOut.xOffset
            attrOutY = self.sites.attrOut.yOffset
            img.paste(attrOutImage, (attrOutX, attrOutY), mask=attrOutImage)
            attrInX = self.sites.attrIcon.xOffset
            attrInY = self.sites.attrIcon.yOffset
            img.paste(attrInImage, (attrInX, attrInY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        width, height = self.bodySize
        width += attrOutImage.width - 1
        top = attrSiteY - (height // 2 + ATTR_SITE_OFFSET)
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
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
        return '.' + self.name

    def execute(self, attrOfValue):
        try:
            result = getattr(attrOfValue, self.name)
        except Exception as err:
            raise IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def clipboardRepr(self, offset):
        return self._serialize(offset, name=self.name)

class SubscriptIcon(Icon):
    def __init__(self, numSubscripts=1, window=None, location=None):
        Icon.__init__(self, window)
        leftWidth, leftHeight = subscriptLBktImage.size
        attrY = leftHeight // 2 + ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrY)
        self.sites.add('indexIcon', 'input',
         leftWidth + ATTR_SITE_DEPTH - outSiteImage.width + 1, leftHeight//2)
        self.argWidths = [LIST_EMPTY_ARG_WIDTH, 0, 0]
        totalWidth, totalHeight = self._size()
        self.sites.add('attrIcon', 'attrIn', totalWidth - ATTR_SITE_DEPTH, attrY)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + totalWidth, y + totalHeight)
        self.changeNumSubscripts(numSubscripts)

    def _size(self):
        return subscriptLBktImage.width + sum(self.argWidths) + \
         subscriptRBktImage.width - 1 + ATTR_SITE_DEPTH, subscriptLBktImage.height

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if self.drawList is None:
            leftBoxX = dimAttrOutImage.width - 1
            leftBoxWidth, leftBoxHeight = subscriptLBktImage.size
            leftImg = Image.new('RGBA', (leftBoxX + leftBoxWidth, leftBoxHeight),
             color=(0, 0, 0, 0))
            # Left bracket
            leftImg.paste(subscriptLBktImage, (leftBoxX, 0))
            # attrOut site
            leftImg.paste(dimAttrOutImage,  (self.sites.attrOut.xOffset,
             self.sites.attrOut.yOffset), mask=dimAttrOutImage)
            # Index input site
            inSiteX = leftBoxX + leftBoxWidth - inSiteImage.width
            inSiteY = leftBoxHeight // 2 - inSiteImage.height // 2
            leftImg.paste(inSiteImage, (inSiteX, inSiteY))
            self.drawList = [((0, 0), leftImg)]
            x = inSiteX + self.argWidths[0] + inSiteImage.width - 1
            # Colons:
            colonY = leftBoxHeight // 2 - colonImage.height // 2
            if hasattr(self.sites, 'upperIcon'):
                self.drawList.append(((x, colonY), colonImage))
                x += self.argWidths[1]
            if hasattr(self.sites, 'stepIcon'):
                self.drawList.append(((x, colonY), colonImage))
                x += self.argWidths[2]
            # Right bracket
            self.drawList.append(((x, 0), subscriptRBktImage))
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        self.argWidths = layout.argWidths
        layout.updateSiteOffsets(self.sites.attrOut)
        top = attrSiteY - (subscriptLBktImage.height // 2 + ATTR_SITE_OFFSET)
        width, height = self._size()
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayout(self):
        if self.sites.indexIcon.att is None:
            indexLayout = None
            if hasattr(self.sites, 'upperIcon'):
                indexWidth = SLICE_EMPTY_ARG_WIDTH
            else:
                # Emphasize missing argument(s)
                indexWidth = LIST_EMPTY_ARG_WIDTH
        else:
            indexLayout = self.sites.indexIcon.att.calcLayout()
            indexWidth = indexLayout.width - 1
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperLayout = None
                upperWidth = colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
            else:
                upperLayout = self.sites.upperIcon.att.calcLayout()
                upperWidth = colonImage.width + upperLayout.width - 2
        else:
            upperWidth = 0
        if hasattr(self.sites, 'stepIcon'):
            if self.sites.stepIcon.att is None:
                stepLayout = None
                stepWidth = colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
            else:
                stepLayout = self.sites.stepIcon.att.calcLayout()
                stepWidth = colonImage.width + stepLayout.width - 2
        else:
            stepWidth = 0
        totalWidth = subscriptLBktImage.width + indexWidth + upperWidth + stepWidth + \
         subscriptRBktImage.width - 2 + ATTR_SITE_DEPTH
        x, height = subscriptLBktImage.size
        x -= 1  # Icon overlap
        layout = Layout(self, totalWidth, height, height // 2 + ATTR_SITE_OFFSET)
        layout.addSubLayout(indexLayout, 'indexIcon', x, -ATTR_SITE_OFFSET)
        x += indexWidth
        if upperWidth > 0:
            layout.addSubLayout(upperLayout, 'upperIcon', x + colonImage.width - 1,
             -ATTR_SITE_OFFSET)
            x += upperWidth
        if stepWidth > 0:
            layout.addSubLayout(stepLayout, 'stepIcon', x + colonImage.width - 1,
             -ATTR_SITE_OFFSET)
        attrIcon = self.sites.attrIcon.att
        attrLayout = None if attrIcon is None else attrIcon.calcLayout()
        layout.addSubLayout(attrLayout, 'attrIcon', layout.width - ATTR_SITE_DEPTH - 1, 0)
        layout.argWidths = [indexWidth, upperWidth, stepWidth]
        return layout

    def changeNumSubscripts(self, n):
        if hasattr(self.sites, 'stepIcon'):
            oldN = 3
        elif hasattr(self.sites, 'upperIcon'):
            oldN = 2
        else:
            oldN = 1
        if n < 3 and oldN == 3:
            self.sites.remove('stepIcon')
        if n < 2 and oldN >= 2:
            self.sites.remove('upperIcon')
        if n >= 2 and oldN < 2:
            self.sites.add('upperIcon', 'input')
        if n == 3 and oldN < 3:
            self.sites.add('stepIcon', 'input')
        self.window.undo.registerCallback(self.changeNumSubscripts, oldN)
        self.layoutDirty = True

    def textRepr(self):
        indexIcon = self.sites.indexIcon.att
        indexText = "" if indexIcon is None else indexIcon.textRepr()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperText = ":"
            else:
                upperText = ":" + self.sites.upperIcon.att.textRepr()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepText = ":" + self.sites.stepIcon.att.textRepr()
            else:
                stepText = ""
        else:
            upperText = stepText = ""
        return '[' + indexText + upperText + stepText + ']'

    def clipboardRepr(self, offset):
        if not hasattr(self.sites, 'upperIcon'):
            numSubscripts = 1
        elif not hasattr(self.sites, 'stepIcon'):
            numSubscripts = 2
        else:
            numSubscripts = 3
        return self._serialize(offset, numSubscripts=numSubscripts)

    def execute(self, attrOfValue):
        if self.sites.indexIcon.att is None:
            raise IconExecException(self, "Missing argument")
        indexValue = self.sites.indexIcon.att.execute()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperValue = None
            else:
                upperValue = self.sites.upperIcon.att.execute()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepValue = self.sites.stepIcon.att.execute()
            else:
                stepValue = None
            try:
                result = attrOfValue[indexValue:upperValue:stepValue]
            except Exception as err:
                raise IconExecException(self, err)
        else:
            try:
                result = attrOfValue[indexValue]
            except Exception as err:
                raise IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            width, height = globalFont.getsize(self.operator)
            bodyLeft = outSiteImage.width - 1
            bodyWidth = width + 2 * TEXT_MARGIN
            bodyHeight = height + 2 * TEXT_MARGIN
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth, bodyHeight),
             fill=ICON_BG_COLOR, outline=OUTLINE_COLOR)
            if needOutSite:
                outImageY = self.sites.output.yOffset - outSiteImage.height // 2
                img.paste(outSiteImage, (0, outImageY), mask=outSiteImage)
            inImageY = self.sites.argIcon.yOffset - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.argIcon.xOffset, inImageY))
            if needSeqSites:
                drawSeqSites(img, bodyLeft, 0, bodyHeight+1)
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
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def arg(self):
        return self.sites.argIcon.att

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
        if self.arg() is None:
            layout.addSubLayout(None, 'argIcon', width, 0)
        else:
            layout.addSubLayout(self.arg().calcLayout(), 'argIcon', width, 0)
        return layout

    def textRepr(self):
        if self.arg() is None:
            argText = "None"
        else:
            argText = self.arg().textRepr()
        return self.operator + " " + argText

    def clipboardRepr(self, offset):
        return self._serialize(offset, op=self.operator)

    def execute(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument")
        argValue = self.arg().execute()
        try:
            result = unaryOpFn[self.operator](argValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

class StarIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, '*', window, location)

class StarStarIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, '**', window, location)

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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            # Left paren/bracket/brace
            leftBoxWidth, leftBoxHeight = self.leftImg.size
            leftImgX = outSiteImage.width - 1
            leftImg = Image.new('RGBA', (leftBoxWidth + leftImgX, leftBoxHeight),
             color=(0, 0, 0, 0))
            leftImg.paste(self.leftImg, (leftImgX, 0))
            if needSeqSites:
                drawSeqSites(leftImg, leftImgX, 0, self.leftImg.height)
            # Output site
            if needOutSite:
                outSiteX = self.sites.output.xOffset
                outSiteY = self.sites.output.yOffset - outSiteImage.height // 2
                leftImg.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
            # Body input site
            inSiteX = outSiteImage.width - 1 + self.leftImg.width - inSiteImage.width
            inSiteY = self.sites.output.yOffset - inSiteImage.height // 2
            leftImg.paste(inSiteImage, (inSiteX, inSiteY))
            self.drawList = [((0, 0), leftImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(inSiteX,
             self.sites.output.yOffset)
            # End paren/brace/bracket
            parenY = self.sites.output.yOffset - self.rightImg.height // 2
            parenX = inSiteX + self.argList.width() + inSiteImage.width - 2
            self.drawList.append(((parenX, parenY), self.rightImg))
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        return siteSnapLists

    def touchesRect(self, rect):
        if not python_g.rectsTouch(self.rect, rect):
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
        self.drawList = None
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

class ListIcon(ListTypeIcon):
    def __init__(self, window, location=None):
        ListTypeIcon.__init__(self, '[', ']', window, location=location,
         leftImg=listLBktImage, rightImg=listRBktImage)

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
        result = [site.att.execute() for site in self.sites.argIcons]
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

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
        self.drawList = None
        self.layoutDirty = True

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
        result = tuple(argIcon.execute() for argIcon in argIcons)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def clipboardRepr(self, offset):
        return self._serialize(offset, noParens=self.noParens)

class DictIcon(ListTypeIcon):
    def __init__(self, window, location=None):
        ListTypeIcon.__init__(self, '{', '}', window, location=location)

    def execute(self):
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return {}
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
            if site.att.__class__ not in (StarStarIcon, DictElemIcon):
                raise IconExecException(self, "Bad format for dictionary element")
        result = {}
        for site in self.sites.argIcons:
            if isinstance(site.att, DictElemIcon):
                key, value = site.att.execute()
                result[key] = value
            elif isinstance(site.att, StarStarIcon):
                result = {**result, **site.att.execute()}
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

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
        self.sites.add("attrIcon", "attrIn",
         self.leftArgWidth + opWidth - ATTR_SITE_DEPTH, siteYOffset)
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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        atTop = self.parent() is None
        suppressSeqSites = toDragImage is not None and self.prevInSeq() is None
        temporaryOutputSite = suppressSeqSites and atTop and self.leftArg() is None
        if temporaryOutputSite or suppressSeqSites:
            # When toDragImage is specified the icon is being dragged, and it must display
            # something indicating where its output site is where it would otherwise
            # not normally draw anything, but don't keep this in self.drawList because
            # it's not for normal use and won't be used again for picking or drawing.
            self.drawList = None
        if self.drawList is None:
            self.drawList = []
            # Output part (connector or paren)
            outSiteX = self.sites.output.xOffset
            siteY = self.sites.output.yOffset
            leftArgX = outSiteX + outSiteImage.width - 1
            if self.hasParens:
                outSiteY = siteY - lParenImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), lParenImage))
                leftArgX = outSiteX + lParenImage.width - 1
            elif temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binOutImage))
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - binInSeqImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binInSeqImage))
            # Body
            txtImg = iconBoxedText(self.operator)
            opWidth, opHeight = self.opSize
            opWidth = txtImg.width + self.depthWidth
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            opX = leftArgX + self.leftArgWidth - 1
            opY = siteY - txtImg.height // 2
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 0, opWidth - 1, txtImg.height - 1),
                 outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
                txtSubImg = txtImg.crop((1, 0, txtImg.width - 1, txtImg.height))
                img.paste(txtSubImg, (self.depthWidth // 2 + 1, opY))
            else:
                img.paste(txtImg, (self.depthWidth // 2, opY))
            rInSiteX = opWidth - inSiteImage.width
            rInSiteY = siteY - inSiteImage.height // 2
            img.paste(inSiteImage, (rInSiteX, rInSiteY))
            self.drawList.append(((opX, 0), img))
            # End paren
            if self.hasParens:
                rParenX = opX + opWidth - 1 + self.rightArgWidth - 1
                rParenY = siteY - rParenImage.height // 2
                self.drawList.append(((rParenX, rParenY), rParenImage))
        self._drawFromDrawList(toDragImage, location, clip, colorErr)
        if temporaryOutputSite or suppressSeqSites:
            self.drawList = None  # Don't keep after drawing (see above)

    def touchesRect(self, rect):
        if not python_g.rectsTouch(self.rect, rect):
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
        self.drawList = None
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
        if self.sites.attrIcon.att is not None:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        else:
            attrLayout = None
        layout.addSubLayout(attrLayout, 'attrIcon', layout.width - ATTR_SITE_DEPTH,
         ATTR_SITE_OFFSET)
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
        return self._serialize(offset, op=self.operator)

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
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

class CallIcon(Icon):
    def __init__(self, window, location=None):
        Icon.__init__(self, window)
        leftWidth, leftHeight = fnLParenImage.size
        attrSiteY = leftHeight // 2 + ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrSiteY)
        self.argList = HorizListMgr(self, 'argIcons', leftWidth, leftHeight//2)
        width, height = self._size()
        self.sites.add('attrIcon', 'attrIn', width-1, attrSiteY)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        width, height = fnLParenImage.size
        width += self.argList.width() + fnRParenImage.width - 1
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if self.drawList is None:
            # Left paren/bracket/brace
            self.drawList = [((0, 0), fnLParenImage)]
            # Commas
            leftBoxWidth, leftBoxHeight = fnLParenImage.size
            inSiteX = leftBoxWidth - OUTPUT_SITE_DEPTH - 1
            self.drawList += self.argList.drawListCommas(inSiteX, leftBoxHeight//2)
            # End paren/brace/bracket
            parenX = leftBoxWidth + self.argList.width() - ATTR_SITE_DEPTH - 1
            self.drawList.append(((parenX, 0), fnRParenImage))
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def argIcons(self):
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, attrSiteX, attrSiteY, layout):
        self.argList.doLayout(layout)
        layout.updateSiteOffsets(self.sites.attrOut)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        width, height = self._size()
        x = attrSiteX
        y = attrSiteY - self.sites.attrOut.yOffset
        self.rect = (x, y, x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayout(self):
        bodyWidth, bodyHeight = fnLParenImage.size
        bodyWidth -= ATTR_SITE_DEPTH
        layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2 + ATTR_SITE_OFFSET)
        argWidth = self.argList.calcLayout(layout, bodyWidth - 1, -ATTR_SITE_OFFSET)
        # layout now incorporates argument layout sizes, but not end paren
        layout.width = fnLParenImage.width + argWidth + fnRParenImage.width - 2
        if self.sites.attrIcon.att:
            attrLayout = self.sites.attrIcon.att.calcLayout()
        else:
            attrLayout = None
        layout.addSubLayout(attrLayout, 'attrIcon', layout.width-ATTR_SITE_DEPTH, 0)
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
        return '(' + argText + ')'

    def execute(self, attrOfValue):
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return None
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
        args = []
        kwArgs = {}
        for site in self.sites.argIcons:
            if isinstance(site.att, ArgAssignIcon):
                key, val = site.att.execute()
                kwArgs[key] = val
            elif isinstance(site.att, StarIcon):
                args += site.att.execute()
            elif isinstance(site.att, StarStarIcon):
                kwArgs = {**kwArgs, **site.att.execute()}
            else:
                args.append(site.att.execute())
        result = attrOfValue(*args, **kwArgs)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

class ArgAssignIcon(BinOpIcon):
    """Special assignment statement for use only in function argument lists"""
    def __init__(self, window=None, location=None):
        BinOpIcon.__init__(self, "=", window, location)

    def execute(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing argument name")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing argument value")
        if not isinstance(self.leftArg(), IdentifierIcon):
            raise IconExecException(self, "Argument name is not identifier")
        return self.leftArg().name, self.rightArg().execute()

class DictElemIcon(BinOpIcon):
    """Individual entry in a dictionary constant"""
    def __init__(self, window=None, location=None):
        BinOpIcon.__init__(self, ":", window, location)

    def execute(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing key")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing value")
        key = self.leftArg().execute()
        value = self.rightArg().execute()
        return key, value

class AssignIcon(Icon):
    def __init__(self, numTargets=1, window=None, location=None):
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
        for i in range(1, numTargets):
            self.addTargetGroup(i)

    def _size(self):
        opWidth, opHeight = self.opSize
        width = assignDragImage.width
        for tgtList in self.tgtLists:
            width += tgtList.width() + opWidth - 2
        width += self.valueList.width()
        return width, inpSeqImage.height

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            self.drawList = []
            width, height = self._size()
            # Left site (seq site bar + 1st target input or drag-insert site
            tgtSiteX = self.sites.targets0[0].xOffset
            siteY = height // 2
            if temporaryDragSite:
                y = siteY - assignDragImage.height // 2
                self.drawList.append(((0, y), assignDragImage))
            else:
                y = siteY - inpSeqImage.height // 2
                self.drawList.append(((tgtSiteX, y), inpSeqImage))
            # Commas and an = for each target group
            txtImg = iconBoxedText('=')
            opWidth, opHeight = txtImg.size
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            rInSiteX = opWidth - inSiteImage.width
            rInSiteY = opHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (rInSiteX, rInSiteY))
            for tgtList in self.tgtLists:
                self.drawList += tgtList.drawListCommas(tgtSiteX, siteY)
                tgtSiteX += tgtList.width() - 1
                self.drawList.append(((tgtSiteX + OUTPUT_SITE_DEPTH, (height-opHeight)//2), img))
                tgtSiteX += opWidth - 1
            self.drawList += self.valueList.drawListCommas(tgtSiteX, siteY)
        self._drawFromDrawList(toDragImage, location, clip, colorErr)
        if temporaryDragSite:
            self.drawList = None

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
        self.drawList = None
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
        return self._serialize(offset, numTargets=len(self.tgtLists))

class DivideIcon(Icon):
    def __init__(self, floorDiv=False, window=None, location=None):
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

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            self.drawList = []
            # Input sites
            topArgX = self.sites.topArg.xOffset
            topArgY = self.sites.topArg.yOffset - floatInImage.height // 2
            self.drawList.append(((topArgX, topArgY), floatInImage))
            bottomArgX = self.sites.bottomArg.xOffset
            bottomArgY = self.sites.bottomArg.yOffset - floatInImage.height // 2
            self.drawList.append(((bottomArgX, bottomArgY), floatInImage))
            # Body
            width, height = self._size()
            bodyLeft = outSiteImage.width - 1
            bodyRight = width - 1
            cntrY = 5
            bodyHeight = 11
            img = Image.new('RGBA', (width, bodyHeight), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyRight, bodyHeight-1),
             outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
            if needSeqSites:
                drawSeqSites(img, bodyLeft, 0, bodyHeight)
            if self.floorDiv:
                cntrX = (bodyLeft + bodyRight) // 2
                draw.line((bodyLeft + 2, cntrY, cntrX - 1, cntrY), fill=BLACK)
                draw.line((cntrX + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            else:
                draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            bodyTop = self.sites.output.yOffset - 5
            if needOutSite:
                img.paste(outSiteImage, (0, cntrY - outSiteImage.height//2))
            self.drawList.append(((0, bodyTop), img))
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def touchesRect(self, rect):
        if not python_g.rectsTouch(self.rect, rect):
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
        self.drawList = None
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
        return self._serialize(offset, floorDiv=self.floorDiv)

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

class BlockEnd(Icon):
    def __init__(self, primary, location=None):
        Icon.__init__(self, primary.window)
        self.primary = primary
        self.sites.add('seqIn', 'seqIn', 1 + BLOCK_INDENT, 1)
        self.sites.add('seqOut', 'seqOut', 1, 1)
        x, y = (0, 0)  if location is None else location
        self.rect = (x, y, x + branchFootImage.width, y + branchFootImage.height)

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if self.drawList is None:
            self.drawList = [((0, 0), branchFootImage)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def select(self, select=True, selectPrimary=False):
        if selectPrimary:
            self.primary.selected = select

    def primaryRect(self):
        return self.primary.rect

    def doLayout(self, outSiteX, outSiteY, layout):
        seqSiteX = outSiteX - self.sites.seqIn.xOffset
        seqSiteY = outSiteY - self.sites.seqIn.yOffset
        width, height = branchFootImage.size
        top = seqSiteY - 1
        left = seqSiteX - 1
        self.rect = (left, top, left + width, top + height)
        self.layoutDirty = False

    def calcLayout(self):
        width, height = branchFootImage.size
        layout = Layout(self, width, height, 1)
        return layout

class WhileIcon(Icon):
    def __init__(self, window, location):
        Icon.__init__(self, window)
        bodyWidth, bodyHeight = globalFont.getsize("while")
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + dragSeqImage.width-1, y + bodyHeight)
        self.blockEnd = BlockEnd(self, (x, y + bodyHeight + 2))

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText("while", self.bodySize[1])
            img.paste(txtImg, (dragSeqImage.width - 1, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            drawSeqSites(img, dragSeqImage.width-1, 0, txtImg.height, indent="right")
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, cntrSiteY - dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)
        if temporaryDragSite:
            self.drawList = None

    def select(self, select=True):
        self.selected = select
        self.blockEnd.selected = select

    def doLayout(self, seqSiteX, seqSiteY, layout):
        width, height = self.bodySize
        width += dragSeqImage.width - 1
        left = seqSiteX - self.sites.seqIn.xOffset - 1
        top = seqSiteY - self.sites.seqIn.yOffset - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqIn)
        # ... The parent site offsets need to be adjusted one pixel left and up, here, for
        #     the child icons to draw in the right place, but I have no idea why.
        layout.doSubLayouts(self.sites.seqIn, seqSiteX-1, seqSiteY-1)
        self.layoutDirty = False

    def calcLayout(self):
        width, height = self.bodySize
        layout = Layout(self, width, height, 1)
        condIcon = self.sites.condIcon.att
        condXOff = width - 1
        condYOff = height // 2 - 1
        if condIcon is None:
            layout.addSubLayout(None, 'condIcon', condXOff, condYOff)
        else:
            layout.addSubLayout(condIcon.calcLayout(), 'condIcon', condXOff, condYOff)
        return layout

    def textRepr(self):
        return None  #... no idea what to do here, yet.

    #... ClipboardRepr

    def execute(self):
        return None  #... no idea what to do here, yet.

class ImageIcon(Icon):
    def __init__(self, image, window, location=None):
        Icon.__init__(self, window)
        self.image = image.convert('RGBA')
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + image.width, y + image.height)

    def draw(self, toDragImage=None, location=None, clip=None, colorErr=False):
        if self.drawList is None:
            self.drawList = [((0, 0), self.image)]
        self._drawFromDrawList(toDragImage, location, clip, colorErr)

    def snapLists(self, forCursor=False):
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

def drawSeqSites(img, boxLeft, boxTop, boxHeight, indent=None):
    """Draw sequence (in and out) sites on a rectangular boxed icon"""
    topIndent = 0
    bottomIndent = 0
    if indent == "right":
        bottomIndent = BLOCK_INDENT
    elif indent == "left":
        topIndent = BLOCK_INDENT
    img.putpixel((topIndent + boxLeft + 1, boxTop+1), BLACK)
    img.putpixel((topIndent + boxLeft + 2, boxTop+1), OUTLINE_COLOR)
    img.putpixel((topIndent + boxLeft + 2, boxTop+2), OUTLINE_COLOR)
    img.putpixel((topIndent + boxLeft + 1, boxTop+2), OUTLINE_COLOR)
    bottomSiteY = boxTop + boxHeight - 2
    img.putpixel((bottomIndent + boxLeft + 1, bottomSiteY), BLACK)
    img.putpixel((bottomIndent + boxLeft + 2, bottomSiteY), OUTLINE_COLOR)
    img.putpixel((bottomIndent + boxLeft + 2, bottomSiteY-1), OUTLINE_COLOR)
    img.putpixel((bottomIndent + boxLeft + 1, bottomSiteY-1), OUTLINE_COLOR)
    if indent == "right":
        img.putpixel((bottomIndent + boxLeft, bottomSiteY), OUTLINE_COLOR)
        img.putpixel((bottomIndent + boxLeft, bottomSiteY - 1), OUTLINE_COLOR)


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

def highestCoincidentIcon(ic):
    """Return highest icon with an output coincident with that of ic"""
    while True:
        parent = ic.parent()
        if parent is None or not isCoincidentSite(parent, parent.siteOf(ic)):
            return ic
        ic = parent

class HorizListMgr:
    """Manage layout for a horizontal list of icon arguments."""
    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)])
        self.emptyInOffsets = (0, 0)
        self.inOffsets = self.emptyInOffsets

    def drawListCommas(self, leftSiteX, leftSiteY):
        commaX = leftSiteX + inSiteImage.width - commaImage.width
        commaY = leftSiteY - commaImageSiteYOffset
        return [((inOff + commaX, commaY), commaImage) for inOff in self.inOffsets[1:-1]]

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
        if len(siteSeries) == 1 and site.att is None:
            # Empty Argument list leaves no space: (), [], {}
            inOffsets = [0, 0]
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
    draw.line((fromX, fromY, toX, toY), SEQ_CONNECT_COLOR)

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

def seqRuleTouches(ic, rect):
    """Return True if the icon draws an indent rule line and it intersects rect"""
    if not hasattr(ic, 'blockEnd'):
        return False
    x, toY = ic.blockEnd.posOfSite('seqOut')
    fromY = ic.posOfSite('seqOut')[1]
    l, t, r, b = rect
    if x < l or x > r:
        return False
    if fromY < t and toY < t:
        return False
    if toY > b and fromY > b:
        return False
    return True

def drawSeqRule(ic, clip=None):
    """Draw connection line between ic's seqIn site and whatever it connects."""
    if not hasattr(ic, 'blockEnd'):
        return
    x, toY = ic.blockEnd.posOfSite('seqOut')
    fromY = ic.posOfSite('seqOut')[1] + 2
    if clip is not None:
        # Clip the line to within the clip rectangle (rules are always vertical and
        # drawn downward and rectangles are ordered left, top, right, bottom).
        l, t, r, b = clip
        if x < l or x > r:
            return
        if fromY < t:
            if toY < t:
                return
            fromY = t
        if toY > b:
            if fromY > b:
                return
            toY = b
    ic.window.draw.line((x, fromY, x, toY), SEQ_RULE_COLOR)

def findSeqStart(ic, toStartOfBlock=False):
    if toStartOfBlock:
        while True:
            if not hasattr(ic.sites, 'seqIn'):
                return ic
            prevIc = ic.sites.seqIn.att
            if prevIc is None:
                return ic
            if hasattr(prevIc, 'blockEnd'):
                return ic
            ic = prevIc
            if isinstance(ic, BlockEnd):
                ic = ic.primary
    else:
        for seqStartIc in traverseSeq(ic, reverse=True):
            pass
        return seqStartIc


def findSeqEnd(ic, toEndOfBlock=False):
    if toEndOfBlock:
        while True:
            if hasattr(ic, 'blockEnd'):
                ic = ic.blockEnd
            if not hasattr(ic.sites, 'seqOut'):
                return ic
            nextIc = ic.sites.seqOut.att
            if nextIc is None:
                return ic
            if isinstance(nextIc, BlockEnd):
                return ic
            ic = nextIc
    else:
        for seqEndIc in traverseSeq(ic):
            pass
        return seqEndIc

def traverseSeq(ic, includeStartingIcon=True, reverse=False, hier=False):
    if includeStartingIcon:
        if hier:
            yield from ic.traverse()
        else:
            yield ic
    if reverse:
        while True:
            if not hasattr(ic.sites, 'seqIn'):
                return
            if ic.sites.seqIn.att is None:
                return
            ic = ic.sites.seqIn.att
            if hier:
                yield from ic.traverse()
            else:
                yield ic
    else:
        while True:
            if not hasattr(ic.sites, 'seqOut'):
                return
            if ic.sites.seqOut.att is None:
                return
            ic = ic.sites.seqOut.att
            if hier:
                yield from ic.traverse()
            else:
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
    while ic.hasSite('attrIcon') and ic.sites.attrIcon.att != None:
        ic = ic.sites.attrIcon.att
        yield ic

def findLastAttrIcon(ic):
    for i in traverseAttrs(ic):
        pass
    return i

def findAttrOutputSite(ic):
    if ic.hasSite('output'):
        return ic
    for i in ic.parentage():
        if i.hasSite('output'):
            return i
    return None

def makeSeriesSiteId(seriesName, seriesIdx):
    return seriesName + "_%d" % seriesIdx

def isSeriesSiteId(siteId):
    return isSeriesRe.match(siteId)

def splitSeriesSiteId(siteId):
    splitName = siteId.split('_')
    if len(splitName) != 2:
        return None, None
    name, idx = splitName
    if len(name) == 0 or len(idx) == 0 or not idx.isnumeric():
        return None, None
    return name, int(idx)

def containingRect(icons):
    maxRect = python_g.AccumRects()
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

def _allSubclasses(cls):
    """Like the class.__subclass__ method, but returns all of the subclasses below cls"""
    for subclass in cls.__subclasses__():
        yield from _allSubclasses(subclass)
        yield subclass

def _getIconClasses():
    """Returns a dictionary mapping Icon subclass names to classes.  This allows the
    clipboard paste command to find and instantiate any icon by name, without requiring
    the icon module to import every module that defines icons."""
    if _getIconClasses.cachedDict is None:
        _getIconClasses.cachedDict = {cls.__name__:cls for cls in _allSubclasses(Icon)}
    return  _getIconClasses.cachedDict
_getIconClasses.cachedDict = None
