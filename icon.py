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

parentSiteTypes = {'output':True, 'attrIn':True}
childSiteTypes = {'input':True, 'attrOut':True}
matingSiteType = {'output':'input', 'input':'output', 'attrIn':'attrOut',
 'attrOut':'attrIn'}

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
INSERT_SITE_Y_OFFSET = sum(globalFont.getmetrics()) // 2

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
    txtImg = Image.new('RGBA',
     (width + 2 * TEXT_MARGIN + 1, height + 2 * TEXT_MARGIN + 1), color=ICON_BG_COLOR)
    draw = ImageDraw.Draw(txtImg)
    draw.text((TEXT_MARGIN, TEXT_MARGIN), text, font=globalFont, fill=(0, 0, 0, 255))
    draw.rectangle((0, 0, width + 2 * TEXT_MARGIN, height + 2 * TEXT_MARGIN),
     fill=None, outline=OUTLINE_COLOR)
    renderCache[text] = txtImg
    return txtImg

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)
leftInSiteImage = asciiToImage(leftInSitePixmap)
commaImage = asciiToImage(commaPixmap)
binOutImage = asciiToImage(binOutPixmap)
floatInImage = asciiToImage(floatInPixmap)
lParenImage = asciiToImage(binLParenPixmap)
rParenImage = asciiToImage(binRParenPixmap)

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

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is
         drawn can be optionally overridden by specifying image and/or location."""
        pass

    def layout(self, location=None):
        """Compute layout and set locations for icon and its children (do not redraw)"""
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        self.doLayout(x, y + self.sites.output.yOffset, self.calcLayout())

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

    def snapLists(self):
        x, y = self.rect[:2]
        return self.sites.makeSnapLists(self, x, y)

    def replaceChild(self, newChild, siteId, leavePlace=False, childSite=None):
        siteId = self.sites.siteIdWarn(siteId)
        if self.sites.isSeries(siteId):
            if newChild is None and not leavePlace:
                self.sites.removeSeriesSiteById(siteId)
            else:
                seriesName, idx = self.sites.splitSeriesSiteId(siteId)
                seriesLen = len(self.sites.getSeries(seriesName))
                if idx == seriesLen:
                    self.sites.insertSeriesSiteByNameAndIndex(seriesName, idx)
                self.sites.lookup(siteId).attach(self, newChild, childSite)
        else:
            self.sites.lookup(siteId).attach(self, newChild, childSite)
        self.layoutDirty = True

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None):
        """Insert a child icon or empty icon site (child=None) at the specified site.
        siteIdOrName may specify either the complete siteId for a site, or (if
        seriesIdx is specified), the name for a series of sites with the index specified
        in seriesIdx."""
        if seriesIdx is None:
            seriesName, seriesIdx = self.sites.splitSeriesSiteId(siteIdOrSeriesName)
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
            self.sites.insertSeriesSiteByNameAndIndex(seriesName, seriesIdx)
            self.sites.lookupSeries(seriesName)[seriesIdx].attach(self, child, childSite)
        self.layoutDirty = True

    def insertChildren(self, children, seriesName, seriesIdx, childSite=None):
        """Insert a group of child icons at the specified site"""
        for i, child in enumerate(children):
            self.insertChild(child, seriesName, seriesIdx + i, childSite)

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

    def becomeTopLevel(self):
        pass  # Most icons look exactly the same at the top level

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
        series, index = self.sites.splitSeriesSiteId(siteId)
        if series is not None:
            return index
        return None

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
    def __init__(self, text, window=None, location=None):
        Icon.__init__(self, window)
        self.text = text
        bodyWidth, bodyHeight = globalFont.getsize(self.text)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrOut', bodyWidth,
         bodyHeight // 2 + ATTR_SITE_OFFSET)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text)
            self.cachedImage.paste(txtImg, (outSiteImage.width - 1, 0))
            outSiteX = self.sites.output.xOffset
            outSiteY = self.sites.output.yOffset - outSiteImage.height // 2
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        if self.sites.attrIcon.att:
            self.sites.attrIcon.att.doLayout(outSiteX + width - 2,
             outSiteY + ATTR_SITE_OFFSET, layout.subLayouts[0])

    def calcLayout(self):
        width, height = self.bodySize
        layout = Layout(self, width, height, height // 2)
        if self.sites.attrIcon.att is None:
            layout.addSubLayout(None)
        else:
            layout.addSubLayout(self.sites.attrIcon.att.calcLayout(), width,
             ATTR_SITE_OFFSET)
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
        TextIcon.__init__(self, name, window, location)
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
        TextIcon.__init__(self, repr(value), window, location)
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
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            width, height = globalFont.getsize(self.operator)
            bodyLeft = outSiteImage.width - 1
            draw = ImageDraw.Draw(self.cachedImage)
            draw.rectangle((bodyLeft, 0, bodyLeft + width + 2 * TEXT_MARGIN,
             height + 2 * TEXT_MARGIN), fill=ICON_BG_COLOR, outline=OUTLINE_COLOR)
            outImageY = self.sites.output.yOffset - outSiteImage.height // 2
            self.cachedImage.paste(outSiteImage, (0, outImageY), mask=outSiteImage)
            inImageY = self.sites.argIcon.yOffset - inSiteImage.height // 2
            self.cachedImage.paste(inSiteImage, (self.sites.argIcon.xOffset, inImageY))
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
        if self.sites.argIcon.att:
            self.sites.argIcon.att.doLayout(outSiteX + width - 3, outSiteY,
             layout.subLayouts[0])

    def calcLayout(self):
        width, height = self.bodySize
        mySiteOffset = height // 2
        layout = Layout(self, width + EMPTY_ARG_WIDTH, height, mySiteOffset)
        if self.sites.argIcon.att is None:
            layout.addSubLayout(None)
        else:
            layout.addSubLayout(self.sites.argIcon.att.calcLayout(), width, 0)
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
    def __init__(self, leftText, rightText, window, location=None):
        Icon.__init__(self, window)
        self.leftText = leftText
        self.rightText = rightText
        leftTextWidth, leftTextHeight = globalFont.getsize(leftText)
        leftTextWidth += 2 * TEXT_MARGIN + 1
        leftTextHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (leftTextWidth, leftTextHeight)
        rightTextWidth, rightTextHeight = globalFont.getsize(rightText)
        self.rightTextWidth = rightTextWidth + 2 * TEXT_MARGIN + 1
        self.sites.add('output', 'output', 0, leftTextHeight // 2)
        self.argList = HorizListMgr(self, 'argIcons', leftTextWidth-1, leftTextHeight//2)
        width, height = self._size()
        self.sites.add('attrIcon', 'attrOut', width-1,
         self.sites.output.yOffset + ATTR_SITE_OFFSET)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        width, height = self.bodySize
        width += self.argList.width() + self.rightTextWidth + 1
        return width, height

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', self._size(), color=(0, 0, 0, 0))
            # Body
            leftTxtImg = iconBoxedText(self.leftText)
            self.cachedImage.paste(leftTxtImg, (outSiteImage.width - 1, 0))
            # Output site
            outSiteX = self.sites.output.xOffset
            outSiteY = self.sites.output.yOffset - outSiteImage.height // 2
            self.cachedImage.paste(outSiteImage, (outSiteX, outSiteY), mask=outSiteImage)
            # Body input site
            inSiteX = outSiteImage.width - 1 + leftTxtImg.width - inSiteImage.width
            inSiteY = self.sites.output.yOffset - inSiteImage.height // 2
            self.cachedImage.paste(inSiteImage, (inSiteX, inSiteY))
            # Commas
            self.argList.drawCommas(self.cachedImage)
            # End paren/brace
            rightTxtImg = iconBoxedText(self.rightText)
            parenY = self.sites.output.yOffset - rightTxtImg.height // 2
            parenX = inSiteX + self.argList.width() + inSiteImage.width - 1
            self.cachedImage.paste(rightTxtImg, (parenX, parenY))
        pasteImageWithClip(image, tintSelectedImage(self.cachedImage, self.selected,
         colorErr), location, clip)

    def snapLists(self):
        """Add snap sites for insertion to those representing actual attachment sites"""
        siteSnapLists = Icon.snapLists(self)
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        return siteSnapLists

    def touchesRect(self, rect):
        if not rectsTouch(self.rect, rect):
            return False
        # If the rectangle is entirely contained within the argument space (ignoring
        # commas), then we will call it not touching
        bodyRight = self.rect[0] + self.bodySize[0]
        return not rectWithinXBounds(rect, bodyRight, bodyRight + self.argList.width())

    def doLayout(self, outSiteX, outSiteY, layout):
        bodyWidth, bodyHeight = self.bodySize
        self.argList.doLayout(outSiteX + bodyWidth - 1, outSiteY, layout.subLayouts)
        width, height = self._size()
        self.sites.attrIcon.xOffset = width - 2
        self.sites.attrIcon.yOffset = self.sites.output.yOffset + ATTR_SITE_OFFSET
        x = outSiteX
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        if self.sites.attrIcon.att is not None:
            self.sites.attrIcon.att.doLayout(outSiteX + width - 2,
             outSiteY + ATTR_SITE_OFFSET, layout.subLayouts[-1])
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        bodyWidth, bodyHeight = self.bodySize
        layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
        argWidth = self.argList.calcLayout(layout, bodyWidth, 0)
        # layout now incorporates argument layout sizes, but not end paren/brace/bracket
        layout.width = bodyWidth + outSiteImage.width + argWidth + self.rightTextWidth - 4
        if self.sites.attrIcon.att:
            layout.addSubLayout(self.sites.attrIcon.att.calcLayout(), layout.width,
             ATTR_SITE_OFFSET)
        else:
            layout.addSubLayout(None)
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
        ListTypeIcon.__init__(self, '[', ']', window, location)

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
    def __init__(self, window, location=None):
        ListTypeIcon.__init__(self, '(', ')', window, location)

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        # Modify parens to have lines through them to distinguish tuple from normal paren
        redrawingCachedImage = self.cachedImage is None
        ListTypeIcon.draw(self, image, location, clip, colorErr)
        if redrawingCachedImage:
            draw = ImageDraw.Draw(self.cachedImage)
            x = self.sites.output.xOffset + 5  # Font-dependent, could cause trouble later
            y = self.sites.output.yOffset
            draw.line((x, y, x + 2, y), GRAY_75)
            # End paren
            x = self.sites.attrIcon.xOffset - 3
            draw.line((x, y, x - 2, y), GRAY_75)
            ListTypeIcon.draw(self, image, location, clip, colorErr)

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
        # There can be an attribute site but it only appears with parenthesis
        self.leftSiteDrawn = False
        # Indicates that input site falls directly on top of output site
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
        if not temporaryOutputSite:
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

    def becomeTopLevel(self):
        # When a BinOpIcon is dropped it can become a top level icon, which may mean it
        # needs to have its's left site restored.
        if not self.leftSiteDrawn:
            self.leftSiteDrawn = True
            self.cachedImage = None
        if self.hasParens:
            self.hasParens = False
            self.coincidentSite = "leftArg"
            self.layoutDirty = True

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

    def layout(self, location=None):
        Icon.layout(self, location)
        # Use the fact that layout is called only on the top-level icon to ensure left
        # site is drawn when the icon is at the top level.
        self.leftSiteDrawn = True

    def doLayout(self, outSiteX, outSiteY, layout):
        self.hasParens = needsParens(self)
        self.coincidentSite = None if self.hasParens else "leftArg"
        lArgLayout, rArgLayout, attrLayout = layout.subLayouts
        if self.hasParens:
            self.sites.leftArg.xOffset = lParenImage.width - outSiteImage.width
        else:
            self.sites.leftArg.xOffset = 0
        if lArgLayout is None:
            self.leftArgWidth = EMPTY_ARG_WIDTH
        else:
            self.leftArgWidth = lArgLayout.width
            lArgLayout.icon.doLayout(outSiteX + self.sites.leftArg.xOffset, outSiteY,
             lArgLayout)
        if rArgLayout is None:
            self.rightArgWidth = EMPTY_ARG_WIDTH
        else:
            self.rightArgWidth = rArgLayout.width
        self.depthWidth = self.depth() * DEPTH_EXPAND
        self.sites.rightArg.xOffset = self.sites.leftArg.xOffset + self.leftArgWidth + \
         self.opSize[0] + self.depthWidth
        if rArgLayout is not None:
            rArgLayout.icon.doLayout(outSiteX + self.sites.rightArg.xOffset, outSiteY,
             rArgLayout)
        width, height = self._size()
        if self.hasParens:
            attrSiteYOffset = self.sites.output.yOffset + ATTR_SITE_OFFSET
            if hasattr(self.sites, 'attrIcon'):
                self.sites.attrIcon.xOffset = width - 2
            else:
                self.sites.add("attrIcon", "attrOut", width - 2, attrSiteYOffset)
        else:
            self.sites.remove('attrIcon')
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        if hasattr(self.sites, 'attrIcon') and self.sites.attrIcon.att is not None:
            self.sites.attrIcon.att.doLayout(outSiteX + width - 2,
             outSiteY + ATTR_SITE_OFFSET, attrLayout)
        self.leftSiteDrawn = False  # self.layout will reset on top-level icon
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        hasParens = needsParens(self)
        if hasParens:
            lParenWidth = lParenImage.width - 2
            rParenWidth = rParenImage.width - 2
        else:
            lParenWidth = rParenWidth = 0
        opWidth, opHeight = self.opSize
        layout = Layout(self, opWidth, opHeight, opHeight // 2)
        if self.leftArg() is None:
            lArgLayout = None
            lArgWidth = EMPTY_ARG_WIDTH
        else:
            lArgLayout = self.leftArg().calcLayout()
            lArgWidth = lArgLayout.width
        layout.addSubLayout(lArgLayout, lParenWidth, 0)
        if self.rightArg() is None:
            rArgLayout = None
            rArgWidth = EMPTY_ARG_WIDTH
        else:
            rArgLayout = self.rightArg().calcLayout()
            rArgWidth = rArgLayout.width
        depthWidth = self.depth() * DEPTH_EXPAND
        layout.addSubLayout(rArgLayout, lParenWidth + lArgWidth + opWidth + depthWidth, 0)
        width = lParenWidth + rParenWidth + lArgWidth + rArgWidth + opWidth + depthWidth
        layout.width = width
        parent = self.parent()
        if hasattr(self.sites, 'attrIcon') and self.sites.attrIcon.att is not None:
            layout.addSubLayout(self.sites.attrIcon.att.calcLayout(), width,
             ATTR_SITE_OFFSET)
        else:
            layout.addSubLayout(None)
        return layout

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

class AssignIcon(BinOpIcon):
    def __init__(self, window, location=None):
        BinOpIcon.__init__(self, "=", window, location)

    def execute(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing assignment target")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing value")
        # how to know if we have a valid assignment target?
        self.assignValues(self.leftArg(), self.rightArg().execute())

    def assignValues(self, leftIcon, values):
        if leftIcon.__class__ is IdentifierIcon:
            try:
                globals()[leftIcon.name] = values
            except Exception as err:
                raise IconExecException(self, err)
        elif leftIcon.__class__ in (TupleIcon, ListIcon):
            assignTargets = leftIcon.argIcons()
            for target in assignTargets:
                if target is None:
                    raise IconExecException(self, "Missing argument(s)")
            if not hasattr(values, "__len__") or len(assignTargets) != len(values):
                raise IconExecException(self, "Could not unpack")
            for target, value in zip(assignTargets, values):
                self.assignValues(target, value)
        else:
            raise IconExecException(self.leftArg(), "Not a valid assignment target")

    def clipboardRepr(self, offset):
        location = self.rect[:2]
        return (self.__class__.__name__, (addPoints(location, offset),
         (None if self.leftArg() is None else self.leftArg().clipboardRepr(offset),
          None if self.rightArg() is None else self.rightArg().clipboardRepr(offset))))

    @staticmethod
    def fromClipboard(clipData, window, offset):
        location, children = clipData
        ic = AssignIcon(window, (addPoints(location, offset)))
        leftArg, rightArg = clipboardDataToIcons(children, window, offset)
        ic.sites.leftArg.attach(ic, leftArg)
        ic.sites.rightArg.attach(ic, rightArg)
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
        self.sites.add('attrIcon', 'attrOut', width - 1, outSiteY + ATTR_SITE_OFFSET)
        self.leftSiteDrawn = False
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
            if self.floorDiv:
                cntrX = (bodyLeft + bodyRight) // 2
                draw.line((bodyLeft + 2, cntrY, cntrX - 1, cntrY), fill=BLACK)
                draw.line((cntrX + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            else:
                draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            self.cachedImage.paste(outSiteImage, (leftX, cntrY - outSiteImage.height//2))
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
        tArgLayout, bArgLayout, attrLayout = layout.subLayouts
        if tArgLayout is None:
            tArgWidth, tArgHeight = self.emptyArgSize
            tArgSiteOffset = self.emptyArgSize[1] // 2
        else:
            tArgWidth, tArgHeight = tArgLayout.width, tArgLayout.height
            tArgSiteOffset = tArgLayout.siteOffset
        if bArgLayout is None:
            bArgWidth, bArgHeight = self.emptyArgSize
            bArgSiteOffset = self.emptyArgSize[1] // 2
        else:
            bArgWidth, bArgHeight = bArgLayout.width, bArgLayout.height
            bArgSiteOffset = bArgLayout.siteOffset
        self.topArgSize = tArgWidth, tArgHeight
        self.bottomArgSize = bArgWidth, bArgHeight
        width = max(tArgWidth, bArgWidth) + 6
        cntrY = tArgHeight + 2
        self.sites.output.yOffset = cntrY
        self.sites.topArg.xOffset = (width - 2 - tArgWidth) // 2
        self.sites.topArg.yOffset = cntrY - tArgHeight + tArgSiteOffset - 1
        self.sites.bottomArg.xOffset = (width - 2 - bArgWidth) // 2
        self.sites.bottomArg.yOffset = cntrY + bArgSiteOffset + 2
        self.sites.attrIcon.xOffset = width - 2
        self.sites.attrIcon.yOffset = cntrY + ATTR_SITE_OFFSET
        width, height = self._size()
        x = outSiteX
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        if tArgLayout is not None:
            tArgLayout.icon.doLayout(x + self.sites.topArg.xOffset,
             y + self.sites.topArg.yOffset, tArgLayout)
        if bArgLayout is not None:
            bArgLayout.icon.doLayout(x + self.sites.bottomArg.xOffset,
             y + self.sites.bottomArg.yOffset, bArgLayout)
        if attrLayout is not None:
            attrLayout.icon.doLayout(outSiteX + width - 2, outSiteY + ATTR_SITE_OFFSET,
             attrLayout)
        self.cachedImage = None
        self.layoutDirty = False

    def calcLayout(self):
        if self.sites.topArg.att is None:
            tArgLayout = None
            tArgWidth, tArgHeight = self.emptyArgSize
        else:
            tArgLayout = self.sites.topArg.att.calcLayout()
            tArgWidth = tArgLayout.width
            tArgHeight = tArgLayout.height
        if self.sites.bottomArg.att is None:
            bArgLayout = None
            bArgWidth, bArgHeight = self.emptyArgSize
        else:
            bArgLayout = self.sites.bottomArg.att.calcLayout()
            bArgWidth = bArgLayout.width
            bArgHeight = bArgLayout.height
        width = max(tArgWidth, bArgWidth) + 4
        height = tArgHeight + bArgHeight + 3
        siteYOff = tArgHeight + 1
        layout = Layout(self, width, height, siteYOff, [tArgLayout, bArgLayout])
        if self.sites.attrIcon.att is not None:
            layout.addSubLayout(self.sites.attrIcon.att.calcLayout(), width,
             ATTR_SITE_OFFSET)
        else:
            layout.addSubLayout(None)
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
    def __init__(self, ico, width, height, siteYOffset, subLayouts=None):
        self.icon = ico
        self.width = width
        self.height = height
        self.siteOffset = siteYOffset
        self.subLayouts = [] if subLayouts is None else subLayouts

    def addSubLayout(self, subLayout, xSiteOffset=None, ySiteOffset=None):
        """Incorporate the area of subLayout as positioned at (xSiteOffset, ySiteOffset)
        relative to the implied site of the current layout.  subLayout can also be
        passed as None, in which case add a None to the sublayouts list."""
        self.subLayouts.append(subLayout)
        if subLayout is None or xSiteOffset is None:
            return
        heightAbove = max(self.siteOffset, subLayout.siteOffset - ySiteOffset)
        heightBelow = max(self.height - self.siteOffset, ySiteOffset +
         subLayout.height - subLayout.siteOffset)
        self.height = heightAbove + heightBelow
        self.siteOffset = heightAbove
        self.width = max(self.width, xSiteOffset + subLayout.width)

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
    if fromIcon.__class__ is AssignIcon and fromIcon.leftArg() is not None:
        # This is temporary for calculator app, until real python assignment is supported
        left = findLeftOuterIcon(clickedIcon, fromIcon.leftArg(), btnPressLoc)
        if left is fromIcon.leftArg():
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
            print("Could not attach icon: invalid back-link (fromSiteId)", fromSiteId)
            return
        # Make the bidirectional links
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

    def removeSite(self, idx):
        if len(self.sites) == 1:  # Leave a single site for insertion
            self.sites[0].attach(None, None)
        else:
            del self.sites[idx]
            for i in range(idx, len(self.sites)):
                self.sites[i].name = makeSeriesSiteId(self.name,i)

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
        seriesName, seriesIndex = self.splitSeriesSiteId(siteId)
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

    def getSeries(self, siteIdOrSeriesName):
        """If siteId is the part of a series, return a list of all of the sites in the
        list.  Otherwise return None"""
        if hasattr(self, siteIdOrSeriesName):
            seriesName = siteIdOrSeriesName
        else:
            seriesName, seriesIndex = self.splitSeriesSiteId(siteIdOrSeriesName)
            if seriesName is None:
                return None
        if hasattr(self, seriesName):
            series = getattr(self, seriesName)
            if isinstance(series, IconSiteSeries):
                return series
        return None

    def splitSeriesSiteId(self, siteId):
        for i, c in enumerate(reversed(siteId)):
            if c.isdigit():
                continue
            if c == "_":
                idx = len(siteId) - 1 - i
                return siteId[:idx], int(siteId[i+idx:])
        print("failed to get name and idx from seriesId", siteId)
        return None, None

    def remove(self, name):
        """Delete a (non-series) icon site."""
        if hasattr(self, name):
            site = getattr(self, name)
            if isinstance(site, IconSite):
                delattr(self, name)
                self._typeDict[site.type].remove(name)

    def removeSeriesSiteById(self, siteId):
        """Remove a site from a series given siteId (which encodes index)"""
        name, idx = self.splitSeriesSiteId(siteId)
        if name is None:
            print("failed to remove series site", siteId)
        else:
            self.removeSeriesSiteByNameAndIndex(name, idx)

    def removeSeriesSiteByNameAndIndex(self, seriesName, idx):
        """Remove a site from a series given the series name and index"""
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries):
            series.removeSite(idx)

    def insertSeriesSiteById(self, siteId):
        name, idx = self.splitSeriesSiteId(siteId)
        if name is None:
            print("failed to insert series site", siteId)
        else:
            self.insertSeriesSiteByNameAndIndex(name, idx)

    def insertSeriesSiteByNameAndIndex(self, seriesName, insertIdx):
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries):
            series.insertSite(insertIdx)

    def makeSnapLists(self, ic, x, y, forMatingSite=None):
        snapSites = {}
        for site in self.allSites():
            if forMatingSite is None or site.type == matingSiteType[forMatingSite]:
                if site.type not in snapSites:
                    snapSites[site.type] = []
                # Omit any site whose attached icon has a site of the same type, at the
                # same location.  In such a case we want both dropped icons and typing to
                # go to the site of the innermost (most local) icon.
                if not isCoincidentSite(site.att, site.name):
                    snapSites[site.type].append((ic, (x + site.xOffset, y + site.yOffset),
                     site.name))
        return snapSites

def isCoincidentSite(ic, siteId):
    return ic is not None and siteId == ic.hasCoincidentSite()

class HorizListMgr:
    """Manage layout for a horizontal list of icon arguments."""

    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        self.leftSiteX = leftSiteX
        self.leftSiteY = leftSiteY
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)])
        self.emptyInOffsets = (0, LIST_EMPTY_ARG_WIDTH)
        self.inOffsets = self.emptyInOffsets

    def drawCommas(self, image):
        commaXOffset = self.leftSiteX + inSiteImage.width - commaImage.width
        commaY = self.leftSiteY - commaImageSiteYOffset
        for inOff in self.inOffsets[1:-1]:
            image.paste(commaImage, (inOff + commaXOffset, commaY))

    def width(self):
        return self.inOffsets[-1]

    def makeInsertSnapList(self):
        """Generate snap sites for item insertion"""
        insertSites = []
        inputSites = self.icon.sites.getSeries(self.siteSeriesName)
        if len(inputSites) > 1 or len(inputSites) == 1 and inputSites[0].att is not None:
            x, y = self.icon.rect[:2]
            y += inputSites[0].yOffset + INSERT_SITE_Y_OFFSET
            idx = 0
            for idx, site in enumerate(inputSites):
                insertSites.append((self.icon, (x + site.xOffset, y), site.name))
            x += inputSites[0].xOffset + self.inOffsets[-1]
            siteName = makeSeriesSiteId(inputSites.name, idx + 1)
            insertSites.append((self.icon, (x, y), siteName))
        return insertSites

    def doLayout(self, leftSiteXOffset, leftSiteYOffset, argLayouts):
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if len(siteSeries) == 0 or len(siteSeries) == 1 and \
         siteSeries[0].att is None:
            self.inOffsets = self.emptyInOffsets
        else:
            self.inOffsets = []
            childX = 0
            for i in range(len(siteSeries)):
                childLayout = argLayouts[i]
                self.inOffsets.append(childX)
                if childLayout is None:
                    childX += LIST_EMPTY_ARG_WIDTH + commaImage.width - 1
                else:
                    childLayout.icon.doLayout(leftSiteXOffset + childX, leftSiteYOffset,
                        childLayout)
                    childX += childLayout.width - 1 + commaImage.width - 1
            self.inOffsets.append(childX - (commaImage.width - 1))
        for i, site in enumerate(siteSeries):
            site.xOffset = self.leftSiteX + self.inOffsets[i]
            site.yOffset = self.leftSiteY

    def calcLayout(self, layout, leftSiteX, leftSiteY):
        """Calculates sub-layouts for icons attached to the list and adds them to layout.
        Returns the width of the list. leftSiteX and leftSiteY are offsets from the icon
         output site (as used in calcLayout and doLayout), not from the icon origin."""
        width = 0
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        for site in siteSeries:
            if site.att is None:
                layout.addSubLayout(None)
                width += LIST_EMPTY_ARG_WIDTH + commaImage.width - 1
            else:
                childLayout = site.att.calcLayout()
                layout.addSubLayout(childLayout, leftSiteX + width, leftSiteY)
                width += childLayout.width - 1 + commaImage.width - 1
        return width - (commaImage.width - 1)

def makeSeriesSiteId(seriesName, seriesIdx):
    return seriesName + "_%d" % seriesIdx

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