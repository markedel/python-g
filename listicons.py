# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw
import ast
import comn
import icon
import filefmt
import iconlayout
import iconsites
import nameicons
import opicons
import blockicons
import assignicons
import parenicon
import entryicon
import infixicon
import cursors
import reorderexpr

listLBktImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o  %%% o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %%% o",
 "..o      o",
 "..oooooooo"))
listLBrktExtendDupRows = (9,)

listMutableBktImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o  %%% o",
 "..o  %  %o",
 "..o  %  %o",
 "..o  5%% o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %%% o",
 "..o      o",
 "..oooooooo"))

listMutableModBktImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o  rRr o",
 "..o rRRRro",
 "..o RRRRRo",
 "..o rRRRro",
 "..o  rRr o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %%% o",
 "..o      o",
 "..oooooooo"))

listRBktImage = comn.asciiToImage((
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
 "o  7%  o",
 "o  7%  o",
 "o %%%  o",
 "o      o",
 "oooooooo"))
listRBrktExtendDupRows = (9,)

listRBktTypeoverImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o 888  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o  98  o",
 "o 888  o",
 "o      o",
 "oooooooo"))

tupleLParenImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o   5  o",
 "..o  76  o",
 "..o  47  o",
 "..o  %8  o",
 "..o 9%8  o",
 "..o 8%8  o",
 "..o 8%8  o",
 "..o 8%8  o",
 "..o 9%8  o",
 "..o  %8  o",
 "..o  47  o",
 "..o  76  o",
 "..o   5  o",
 "..o      o",
 "..oooooooo"))
tupleLParenExtendDupRows = (9,)

tupleRParenImage = comn.asciiToImage((
 "ooooooo",
 "o     o",
 "o     o",
 "o 5   o",
 "o 67  o",
 "o 74  o",
 "o 8%  o",
 "o 8%9 o",
 "o 8%8 o",
 "o 8%8 o",
 "o 8%8 o",
 "o 8%9 o",
 "o 8%  o",
 "o 74  o",
 "o 67  o",
 "o 5   o",
 "o     o",
 "ooooooo"))
tupleRParenExtendDupRows = (9,)

tupleRParenTypeoverImage = comn.asciiToImage((
 "ooooooo",
 "o     o",
 "o     o",
 "o 9   o",
 "o 99  o",
 "o 99  o",
 "o  8  o",
 "o  8  o",
 "o  99 o",
 "o  99 o",
 "o  99 o",
 "o  8  o",
 "o  8  o",
 "o 99  o",
 "o 99  o",
 "o 9   o",
 "o     o",
 "ooooooo"))

lBraceImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o      o",
 "..o  912 o",
 "..o  639 o",
 "..o  65  o",
 "..o  65  o",
 "..o 9%7  o",
 "..o %%   o",
 "..o 9%7  o",
 "..o  65  o",
 "..o  65  o",
 "..o  639 o",
 "..o  912 o",
 "..o      o",
 "..o      o",
 "..oooooooo"))
lBraceExtendDupRows = 7, 11

mutableModBraceImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o  rRr o",
 "..o rRRRro",
 "..o RRRRRo",
 "..o rRRRro",
 "..o  rRr o",
 "..o  65  o",
 "..o 9%7  o",
 "..o %%   o",
 "..o 9%7  o",
 "..o  65  o",
 "..o  65  o",
 "..o  639 o",
 "..o  912 o",
 "..o      o",
 "..o      o",
 "..oooooooo"))

mutableBraceImage = comn.asciiToImage((
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o  9%% o",
 "..o  %  %o",
 "..o  %  %o",
 "..o  6%% o",
 "..o  65  o",
 "..o 9%7  o",
 "..o %%   o",
 "..o 9%7  o",
 "..o  65  o",
 "..o  65  o",
 "..o  639 o",
 "..o  912 o",
 "..o      o",
 "..o      o",
 "..oooooooo"))

rBraceImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o 219  o",
 "o 936  o",
 "o  56  o",
 "o  56  o",
 "o  7%9 o",
 "o   %% o",
 "o  7%9 o",
 "o  56  o",
 "o  56  o",
 "o 936  o",
 "o 219  o",
 "o      o",
 "o      o",
 "oooooooo"))
rBraceExtendDupRows = 7, 11

rBraceTypeoverImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o 99   o",
 "o  8   o",
 "o  99  o",
 "o  99  o",
 "o   8  o",
 "o   88 o",
 "o   8  o",
 "o  99  o",
 "o  99  o",
 "o  8   o",
 "o 99   o",
 "o      o",
 "o      o",
 "oooooooo"))

cphSiteImage = comn.asciiToImage((
 "oo",
 ".o",
 ".o",
 ".o",
 ".o",
 ".o",
 "oo"))

inpOptionalSeqImage = comn.asciiToImage((
 "ooo",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "ooo"))

fnLParenImage = comn.asciiToImage((
 ".oooooooo",
 ".o      o",
 ".o      o",
 ".o      o",
 ".o   84 o",
 ".o  81  o",
 ".o  28  o",
 ".o 73   o",
 ".o 56   o",
 ".o 48   o",
 ".o 19   o",
 ".o 19   o",
 ".o 18   o",
 ".o 28   o",
 ".o 68   o",
 ".o      o",
 ".o      o",
 ".oooooooo"))
fnLParenExtendDupRows = 11,

fnLParenOpenImage = comn.asciiToImage((
 ".oooooooo",
 ".o      o",
 ".o      o",
 ".o      o",
 ".o   84 o",
 ".o  81  o",
 ".o  28  o",
 ".o 73   o",
 ".o 98   o",
 ".o      o",
 ".o 5    o",
 ".o 19   o",
 ".o 18   o",
 ".o 28   o",
 ".o 68   o",
 ".o      o",
 ".o      o",
 ".oooooooo"))

fnRParenImage = comn.asciiToImage( (
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
 "o 65   o",
 "o85    o",
 "o      o",
 "o      o",
 "oooooooo"))
fnRParenExtendDupRows = 7,

fnRParenTypeoverImage = comn.asciiToImage( (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o   8  o",
 "o   8  o",
 "o   8  o",
 "o   99 o",
 "o   99 o",
 "o   99 o",
 "o   8  o",
 "o  99  o",
 "o  99  o",
 "o 99   o",
 "o99    o",
 "o      o",
 "o      o",
 "oooooooo"))

argAssignImage = comn.asciiToImage((
 "ooooooooo",
 "o       o",
 "o       o",
 "o       o",
 "o %%%%% o",
 "o      o.",
 "o     o..",
 "o %%%%%o.",
 "o       o",
 "o       o",
 "o       o",
 "o       o",
 "ooooooooo"))

class ListTypeIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, leftText, rightText, window, leftImgFn=None,
            rightImgFn=None, closed=True, typeover=False, obj=None, location=None):
        """Note that the images generated by leftImgFn and rightImgFn get modified by
        the draw method, so must not return template images."""
        icon.Icon.__init__(self, window)
        self.closed = False
        self.leftText = leftText
        self.rightText = rightText
        self.leftImgFn = leftImgFn
        self.rightImgFn = rightImgFn
        self.object = obj
        if typeover and closed:
            self.typeoverActive = True
            self.window.watchTypeover(self)
        else:
            self.typeoverActive = False
        leftWidth, height = leftImgFn(0).size
        self.sites.add('output', 'output', 0, height // 2)
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', leftWidth-1, height//2)
        self.sites.addSeries('cprhIcons', 'cprhIn', 1, [(leftWidth-1, height//2)])
        width = self.sites.cprhIcons[-1].xOffset + rightImgFn(0).width
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, height-2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if closed:
            self.close()

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            # Left paren/bracket/brace
            leftImg = self.leftImgFn(self.argList.spineHeight)
            leftImgX = min(icon.outSiteImage.width - 1, leftImg.width - 3)
            if needSeqSites:
                icon.drawSeqSites(leftImg, leftImgX, 0, leftImg.height)
            # Output site
            if needOutSite:
                outSiteX = self.sites.output.xOffset
                outSiteY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                leftImg.paste(icon.outSiteImage, (outSiteX, outSiteY))
            # Body input site(s)
            self.argList.drawBodySites(leftImg)
            # Unclosed icons need to be dimmed and crossed out
            inSiteX = leftImg.width - icon.inSiteImage.width
            if not self.closed:
                cntrY = self.sites.output.yOffset
                draw = ImageDraw.Draw(leftImg)
                draw.line((leftImgX+1, cntrY, inSiteX, cntrY),
                        fill=comn.ICON_BG_COLOR, width=3)
            self.drawList = [((0, 0), leftImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(inSiteX,
                    self.sites.output.yOffset)
            # End paren/brace/bracket
            if self.closed:
                rightImg = self.rightImgFn(self.argList.spineHeight)
                if self.acceptsComprehension():
                    cphYOff = self.sites.output.yOffset - cphSiteImage.height // 2
                    rightImg.paste(cphSiteImage, (0, cphYOff))
                attrInXOff = rightImg.width - icon.attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rightImg.paste(icon.attrInImage, (attrInXOff, attrInYOff))
                parenX = self.sites.cprhIcons[-1].xOffset
                self.drawList.append(((parenX, 0), rightImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def isComprehension(self):
        return len(self.sites.cprhIcons) > 1

    def acceptsComprehension(self):
        return len(self.sites.argIcons) <= 1

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None):
        # Checks and special rules for comprehension series with no commas.
        if seriesIdx is None:
            seriesName, idx = iconsites.splitSeriesSiteId(siteIdOrSeriesName)
        else:
            seriesName = siteIdOrSeriesName
            idx = seriesIdx
        if seriesName == "argIcons":
            if self.isComprehension():
                print('Attempt to add elements to comprehension')
                return
        if seriesName != 'cprhIcons':
            icon.Icon.insertChild(self, child, siteIdOrSeriesName, seriesIdx, childSite)
            return
        if len(self.sites.argIcons) > 1:
            print("Can't add comprehension to multi-element list")
            return
        #  Without commas we need to never leave an empty site, except for the last one,
        #  which must always exist and remain empty
        if child is None:
            return
        self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
        self.sites.lookupSeries(seriesName)[idx].attach(self, child, childSite)
        self.markLayoutDirty()

    def replaceChild(self, newChild, siteId, leavePlace=False, childSite=None):
        # Checks and special rules for comprehension series with no commas.
        siteName, seriesIdx = iconsites.splitSeriesSiteId(siteId)
        if siteName == 'cprhIcons':
            # Generic version of insertChild is intended for series with commas.  Never
            # leave an empty site when there is no way to see or access it
            if seriesIdx == len(self.sites.cprhIcons) - 1:
                self.insertChild(newChild, siteName, seriesIdx)
            else:
                icon.Icon.replaceChild(self, newChild, siteId, False, childSite)
        else:
            icon.Icon.replaceChild(self, newChild, siteId, leavePlace, childSite)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if self.isComprehension():
            if forCursor:
                return siteSnapLists
            x = self.rect[0] + icon.INSERT_SITE_X_OFFSET
            y = self.rect[1] + self.sites.cprhIcons[0].yOffset + icon.INSERT_SITE_Y_OFFSET
            siteSnapLists['insertCprh'] = [(self, (x + site.xOffset, y), site.name)
             for site in self.sites.cprhIcons[:-1]]
        else:
            siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
            if not self.acceptsComprehension():
                del siteSnapLists['cprhIn']
        return siteSnapLists

    def inRectSelect(self, rect):
        # Require selection rectangle to touch both parens to be considered selected
        if not icon.Icon.inRectSelect(self, rect):
            return False
        selLeft, selTop, selRight, selBottom = rect
        icLeft, icTop, icRight, icBottom = self.rect
        if selLeft > icLeft + self.leftImgFn(0).width:
            return False
        if selRight < icRight - self.rightImgFn(0).width:
            return False
        return True

    def doLayout(self, outSiteX, outSiteY, layout):
        if self.object is not None and hasattr(self, 'mutableModified'):
            self.mutableModified = not self.compareData(self.object, compareContent=True)
        self.argList.doLayout(layout)
        self.sites.output.yOffset = self.argList.spineTop
        self.sites.seqOut.yOffset = self.argList.spineHeight - 2
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        if self.closed:
            width = self.sites.cprhIcons[-1].xOffset + self.rightImgFn(0).width
        else:
            width = self.sites.cprhIcons[-1].xOffset
        x = outSiteX
        y = outSiteY - self.argList.spineTop
        self.rect = (x, y, x + width, y + self.argList.spineHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        argListLayouts = self.argList.calcLayouts()
        cprhLayoutLists = [(None,) if site.att is None else site.att.calcLayouts()
                for site in self.sites.cprhIcons]
        if not self.closed or self.sites.attrIcon.att is None:
            attrLayouts = (None,)
        else:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        layouts = []
        for argListLayout, attrLayout, *cprhLayouts in iconlayout.allCombinations(
                (argListLayouts, attrLayouts, *cprhLayoutLists)):
            leftWidth, minHeight = self.leftImgFn(0).size
            leftWidth -= icon.OUTPUT_SITE_DEPTH
            layout = iconlayout.Layout(self, leftWidth, minHeight, minHeight // 2)
            argListLayout.mergeInto(layout, leftWidth - 1, 0)
            cprhWidth = 0
            leftCprhX = leftWidth - 1 + argListLayout.width - 1
            cprhY = 0  # In-line with output because comprehensions have only one arg
            for siteIdx, site in enumerate(self.sites.cprhIcons):
                cprhLayout = cprhLayouts[siteIdx]
                layout.addSubLayout(cprhLayout, site.name, leftCprhX + cprhWidth, cprhY)
                cprhWidth += 0 if cprhLayout is None else cprhLayout.width - 1
            if self.closed:
                layout.width = leftWidth - 1 + argListLayout.width - 1 + cprhWidth + \
                        self.rightImgFn(0).width
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1,
                        icon.ATTR_SITE_OFFSET)
            else:
                layout.width = leftWidth - 1 + argListLayout.width - 1 + cprhWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Add back the attribute site on the end brace/bracket.  Done here to allow the
        # site to be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', comn.rectWidth(self.rect) -
         icon.ATTR_SITE_DEPTH, comn.rectHeight(self.rect) // 2 + icon.ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def textRepr(self):
        argText = icon.seriesTextRepr(self.sites.argIcons)
        cprhText = ""
        for site in self.sites.cprhIcons[:-1]:
            cprhText += " " + site.att.textRepr()
        return self.leftText + argText + cprhText + self.rightText + \
               icon.attrTextRepr(self)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.leftText)
        argText = icon.seriesSaveText(brkLvl, self.sites.argIcons, False, export)
        text.concat(None, argText)
        cprhText = filefmt.SegmentedText(None)
        for site in self.sites.cprhIcons[:-1]:
            cprhText.add(None, " ")
            icon.addArgSaveText(cprhText, brkLvl, site, False, export)
        text.concat(brkLvl, cprhText, False)
        text.add(None, self.rightText)
        return text

    def backspace(self, siteId, evt):
        backspaceListIcon(self, siteId, evt)

    def textEntryHandler(self, entryIc, text, onAttr):
        # Typeover for lists, tuples, and dicts is handled by hard-coded parsing because
        # we closing of matching open parens/brackets/braces needs to take precedence
        # This only handles the special case of typing a * (pack/unpack) operator
        if entryIc.parent() != self:
            return None
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId is None or not iconsites.isSeriesSiteId(siteId):
            return None
        name, idx = iconsites.splitSeriesSiteId(siteId)
        if name != 'argIcons' or idx != len(self.sites.argIcons)-1:
            return None
        if text == '*' and not onAttr:
            return StarIcon(self.window), None
        return None

    def setTypeover(self, idx, site):
        self.drawList = None
        if idx is None or idx > 0:
            self.typeoverActive = False
            return False
        self.typeoverActive = True
        return True

    def typeoverSites(self, allRegions=False):
        if self.typeoverActive:
            before = iconsites.makeSeriesSiteId('argIcons', len(self.sites.argIcons) - 1)
            returnData = before, 'attrIcon', ')', 0
            return [returnData] if allRegions else returnData
        return [] if allRegions else (None, None, None, None)

    def argIcons(self):
        """Return list of list argument icons.  This is trivial, but exists to give list
        and dict icons an identical interface with that of the TupleIcon version which
        which has to deal with odd single-element syntax."""
        return [site.att for site in self.sites.argIcons]

    def dumpName(self):
        return self.leftText + ("" if self.closed else self.rightText)

    def compareData(self, data, compareContent=False):
        if self.object is None or data is not self.object:
            return False
        mutable = hasattr(self, 'mutableModified')
        if mutable and not compareContent and self.sites.attrIcon.att is not None:
            # An attribute must be executed, so unless we're looking at the content of a
            # mutable icon, execution is required to generate data from the attribute.
            return False
        if mutable and not compareContent:
            # Data object is identical per first test, above, so for mutable icons
            # comparison stops here (even if content differs).
            return True
        # A detailed comparison of the content is required
        if len(data) == 0 and len(self.sites.argIcons) == 1 and \
                self.sites.argIcons[0].att is None:
            return True  # Empty list
        if len(data) != len(self.sites.argIcons):
            return False
        for i, site in enumerate(self.sites.argIcons):
            value = data[i]
            ic = site.att
            if ic is None or not ic.compareData(value):
                return False
        return True

class ListIcon(ListTypeIcon):
    def __init__(self, window, closed=True, obj=None, typeover=False, location=None):
        if obj is not None:
            self.mutableModified = False
        ListTypeIcon.__init__(self, '[', ']', window, obj=obj, location=location,
                closed=closed, leftImgFn=self._stretchedLBracketImage,
                rightImgFn=self._stretchedRBracketImage, typeover=typeover)

    def execute(self):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return eval(self.textRepr())
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return []
        for site in self.sites.argIcons:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
        result = [site.att.execute() for site in self.sites.argIcons]
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self, skipAttr=False):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return composeAttrAstIf(self, createComprehensionAst(self), skipAttr)
        if self.object is not None and self.sites.attrIcon.att is None and \
                isinstance(self.parent(), assignicons.AssignIcon) and \
                self.parent().siteOf(self)[:6] == 'target':
            # This is a mutable list icon as a direct assignment target, emit code for
            # a target to replace the content of the list.  Normally we would execute
            # content, but the assignment will blow it all away, so don't bother.
            return ast.Subscript(value=icon.createAstDataRef(self),
                    slice=ast.Slice(lower=None, upper=None, step=None),
                    ctx=ast.Store(), lineno=self.id, col_offset=0)
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            elts = []
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            elts = [site.att.createAst() for site in self.sites.argIcons]
        listContentAst = ast.List(elts=elts,
                ctx=nameicons.determineCtx(self), lineno=self.id, col_offset=0)
        # If this is not a mutable icon, we're done
        if self.object is None:
            return composeAttrAstIf(self, listContentAst, skipAttr)
        # The icon represents a list data object (mutable list).  The list may or may not
        # need update, but since we still need to execute/update the data within each of
        # the elements, we blindly update the list content, regardless.  The update is
        # done via a function that takes the list generated by listContentAst (above) as
        # and argument, updates the data object, and returns it is the function value.
        # The function is stored in __windowExecContext__[self.id] and createAst returns
        # an ast to call it in-line with listContentAst as its argument.
        def updateFn(src, tgt=self.object):
            tgt[:] = src
            return tgt
        return composeAttrAstIf(self, ast.Call(func=icon.createAstDataRef(self, updateFn),
            args=[listContentAst], keywords=[], lineno=self.id, col_offset=0), skipAttr)

    def _stretchedLBracketImage(self, desiredHeight):
        if self.object is None:
            bracketImg = listLBktImage
        elif self.mutableModified:
             bracketImg = listMutableModBktImage
        else:
            bracketImg = listMutableBktImage
        return icon.yStretchImage(bracketImg, listLBrktExtendDupRows, desiredHeight)

    def _stretchedRBracketImage(self, desiredHeight):
        img = listRBktTypeoverImage if self.typeoverActive else listRBktImage
        return icon.yStretchImage(img, listRBrktExtendDupRows, desiredHeight)

class TupleIcon(ListTypeIcon):
    def __init__(self, window, noParens=False, closed=True, obj=None, typeover=False,
                 location=None):
        self.noParens = noParens
        self.argList = None  # Temporary to help with initialization
        ListTypeIcon.__init__(self, '(', ')', window, closed=closed, obj=obj,
                location=location, leftImgFn=self._stretchedLTupleImage,
                rightImgFn=self._stretchedRTupleImage, typeover=typeover)
        if noParens:
            self.sites.remove('attrIn')

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
        self.drawList = None
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.removeParens)

    def removeParens(self):
        if self.noParens:
            return
        self.noParens = True
        self.drawList = None
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.restoreParens)

    def acceptsComprehension(self):
        # Redefine to add prohibition on no-paren tuple becoming generator comprehension
        return len(self.sites.argIcons) <= 1 and not self.noParens

    def calcLayouts(self):
        # If the icon is no longer at the top level and needs its parens restored, do so
        # before calculating the layout (would be better to do this elsewhere). Exception
        # is EntryIcon, which can hold a naked tuple
        parent = self.parent()
        if self.noParens and parent is not None:
            if not isinstance(parent, entryicon.EntryIcon):
                self.restoreParens()
        return ListTypeIcon.calcLayouts(self)

    def execute(self):
        if self.isComprehension():
            return eval(self.textRepr())
        argIcons = self.argIcons()
        for argIcon in argIcons:
            if argIcon is None:
                raise icon.IconExecException(self, "Missing argument(s)")
        result = tuple(argIcon.execute() for argIcon in argIcons)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return icon.composeAttrAst(self, createComprehensionAst(self))
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            elts = []
        elif len(self.sites.argIcons) == 2 and self.sites.argIcons[0].att is not None \
         and self.sites.argIcons[1].att is None:
            elts = [self.sites.argIcons[0].att.createAst()]  # Traditional form: (1, )
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            elts = [site.att.createAst() for site in self.sites.argIcons]
        contentAst = ast.Tuple(elts=elts, ctx=nameicons.determineCtx(self),
                lineno=self.id, col_offset=0)
        # If this tuple icon does not represent an existing data object or represents one
        # that needs to change, emit an ast the generates a new tuple when executed.
        if self.object is None or not self.compareData(self.object):
            return icon.composeAttrAst(self, contentAst)
        # If the icon still faithfully represents its data object, produce an AST
        # referencing the existing data rather than an AST to make a new tuple.  Note
        # that we still need execute any code or data updates that might exist in below
        # the immediate children of the tuple, so we return an AST that references the
        # data object, but also (even though it may be pointless) executes each of the
        # elements.  The returned AST codes: (ref-to-self.object, contentAst)[0]
        return icon.composeAttrAst(self, ast.Subscript(
                value=ast.Tuple(elts=[icon.createAstDataRef(self), contentAst],
                    ctx=ast.Load(), lineno=self.id, col_offset=0),
                slice=ast.Index(value=ast.Constant(value=0, kind=None, lineno=self.id,
                    col_offset=0)),
                ctx=ast.Load(), lineno=self.id, col_offset=0))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, noParens=self.noParens,
         closed=self.closed)

    def _stretchedLTupleImage(self, desiredHeight):
        if self.noParens:
            if self.argList is not None and self.argList.rowWidths is not None and \
                    len(self.argList.rowWidths) >= 2:
                img = icon.lSimpleSpineImage
            else:
                img = inpOptionalSeqImage
        else:
            img = tupleLParenImage
        return icon.yStretchImage(img, tupleLParenExtendDupRows, desiredHeight)

    def _stretchedRTupleImage(self, desiredHeight):
        if self.noParens:
            if self.argList is not None and self.argList.rowWidths is not None and \
                    len(self.argList.rowWidths) >= 2:
                img = icon.rSimpleSpineImage
            else:
                return icon.emptyImage
        elif self.typeoverActive:
            img = tupleRParenTypeoverImage
        else:
            img = tupleRParenImage
        return icon.yStretchImage(img, tupleRParenExtendDupRows, desiredHeight)

class DictIcon(ListTypeIcon):
    def __init__(self, window, closed=True, obj=None, typeover=False, location=None):
        if obj is not None:
            self.mutableModified = False
        ListTypeIcon.__init__(self, '{', '}', window, obj=obj,
                leftImgFn=self._stretchedLBraceImage,
                rightImgFn=self._stretchedRBraceImage, closed=closed,
                typeover=typeover, location=location)

    def execute(self):
        if self.isComprehension():
            return eval(self.textRepr())
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return {}
        for site in self.sites.argIcons:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if site.att.__class__ not in (StarStarIcon, DictElemIcon):
                raise icon.IconExecException(self, "Bad format for dictionary element")
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

    def createAst(self, skipAttr=False):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return composeAttrAstIf(self, createComprehensionAst(self), skipAttr)
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            elts = []
            isDict = True if self.object is None else type(self.object) is dict
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            elts = [site.att for site in self.sites.argIcons]
            # Check for consistency: are we a set or a dictionary constant
            isDict = len(elts) == 0 or isinstance(elts[0], DictElemIcon) or \
             isinstance(elts[0], StarStarIcon)
            for elt in elts:
                if isDict and elt.__class__ not in (DictElemIcon, StarStarIcon) or \
                        not isDict and elt.__class__ in (DictElemIcon, StarStarIcon):
                    raise icon.IconExecException(self, "Inconsistent dict/set content")
            # If the icon represents a data object, check for consistency between the
            # object and the implied (set versus dict) type of the icon.  If they're
            # different, this can no longer be associated with the original data.
            if self.object is not None and (type(self.object) is set and isDict
                    or type(self.object) is dict and not isDict):
                self.object = None
                self.mutableModified = False
        # If this is an icon that does not represent existing data, or expects to
        # change the data, create an AST for the dictionary or set constant.
        if isDict:
            keyAsts = []
            valueAsts = []
            for elt in elts:
                if isinstance(elt, DictElemIcon):
                    keyAsts.append(elt.childAt('leftArg').createAst())
                    valueAsts.append(elt.childAt('rightArg').createAst())
                else:  # StarStarIcon
                    keyAsts.append(None)
                    valueAsts.append(elt.childAt('argIcon').createAst())
            contentAst = ast.Dict(keyAsts, valueAsts, lineno=self.id, col_offset=0)
        else:
            eltAsts = [elt.createAst() for elt in elts]
            contentAst = ast.Set(elts=eltAsts, lineno=self.id, col_offset=0)
        # If the icon does not represent data, put it together with any attribute
        # icons and we're done.
        if self.object is None:
            return composeAttrAstIf(self, contentAst, skipAttr)
        # The icon represents a data object (mutable dict or set).  It may or may not
        # need update, but since we still need to execute/update the data within each of
        # the elements, we blindly update the content, regardless.  The update is done
        # via a function that takes the object generated by contentAst (above) as
        # and argument, updates the data object, and returns it is the function value.
        # The function is stored in __windowExecContext__[self.id] and createAst returns
        # an ast to call it in-line with listContentAst as its argument.
        def updateFn(src, tgt=self.object):
            tgt.clear()
            tgt.update(src)
            return tgt
        return composeAttrAstIf(self, ast.Call(func=icon.createAstDataRef(self, updateFn),
                args=[contentAst], keywords=[], lineno=1, col_offset=0), skipAttr)

    def snapLists(self, forCursor=False):
        siteSnapLists = ListTypeIcon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        restoreConditionalTargets(self, siteSnapLists, (DictElemIcon, StarStarIcon))
        return siteSnapLists

    def _stretchedLBraceImage(self, desiredHeight):
        if self.object is None:
            braceImg = lBraceImage
        elif self.mutableModified:
             braceImg = mutableModBraceImage
        else:
            braceImg = mutableBraceImage
        return icon.yStretchImage(braceImg, lBraceExtendDupRows, desiredHeight)

    def _stretchedRBraceImage(self, desiredHeight):
        img = rBraceTypeoverImage if self.typeoverActive else rBraceImage
        return icon.yStretchImage(img, rBraceExtendDupRows, desiredHeight)

    def textEntryHandler(self, entryIc, text, onAttr):
        # Handle typing of ** (and prevent * from immediately generating an icon)
        if entryIc.parent() != self:
            return ListIcon.textEntryHandler(self, entryIc, text, onAttr)
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId is None or not iconsites.isSeriesSiteId(siteId):
            return ListIcon.textEntryHandler(self, entryIc, text, onAttr)
        name, idx = iconsites.splitSeriesSiteId(siteId)
        if name != 'argIcons' or idx != len(self.sites.argIcons)-1:
            return ListIcon.textEntryHandler(self, entryIc, text, onAttr)
        if text == '*' and not onAttr:
            return "accept"
        if text[0] == '*' and len(text) == 2 and (text[1] in " ([{" or text[1].isalpha()):
            return StarIcon(self.window), text[1]
        if text == '**' and not onAttr:
            return StarStarIcon(self.window), None
        return None

    def compareData(self, data, compareContent=False):
        if self.object is None or data is not self.object:
            return False
        if not compareContent:
            # Dictionaries and sets are both mutable icons, so content does not need to
            # be examined in detail, just that the icon .object field matches the data
            # (which the test above already established).  However, we do need to check
            # 1) if the icon has an attribute that needs to be executed, and 2) if
            # execution will change the data from a dict to a set or visa versa.
            if self.sites.attrIcon.att is not None:
                return False
            if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
                elts = []
                isDict = True if self.object is None else type(self.object) is dict
            else:
                for site in self.sites.argIcons:
                    if site.att is None:
                        return True  # Missing arguments, won't execute
                elts = [site.att for site in self.sites.argIcons]
                # Check for consistency: are we a set or a dictionary constant
                isDict = len(elts) == 0 or isinstance(elts[0], DictElemIcon) or \
                 isinstance(elts[0], StarStarIcon)
                for elt in elts:
                    if isDict and elt.__class__ not in (DictElemIcon, StarStarIcon):
                        return True  # Inconsistent status, won't execute
                # If the icon content will drive a change from dict to a set or visa
                # versa, then the object will have to change
                if type(data) is dict and not isDict or type(data) is not dict and isDict:
                    return False
                return True
        # Compare each element and return True only for an exact match
        if len(data) == 0 and len(self.sites.argIcons) == 1 and \
                self.sites.argIcons[0].att is None:
            return True  # Empty braces
        if len(data) != len(self.sites.argIcons):
            return False
        if type(data) is dict:
            for site, (key, value) in zip(self.sites.argIcons, data.items()):
                elemIcon = site.att
                if not isinstance(elemIcon, DictElemIcon):
                    return False
                keyIc = elemIcon.leftArg()
                valueIc = elemIcon.rightArg()
                if keyIc is None or valueIc is None:
                    return False
                if not keyIc.compareData(key) or not valueIc.compareData(value):
                    return False
        else:  # set (must be because otherwise object would not match data)
            for ic, value in zip(self.argIcons(), data):
                if ic is None:
                    return False
                if not ic.compareData(value):
                    return False
        return True

class CallIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, window, closed=True, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        self.closed = False
        if typeover and closed:
            self.typeoverActive = True
            self.window.watchTypeover(self)
        else:
            self.typeoverActive = False
        leftWidth, leftHeight = fnLParenImage.size
        attrSiteY = leftHeight // 2 + icon.ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrSiteY)
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', leftWidth,
                leftHeight // 2)
        width, height = self._size()
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        # Property to tell wrapping layout and save-text generators not to allow wrap
        # at the attribute site (as most attributes normally can).
        self.sticksToAttr = True
        if closed:
            self.close()

    def _size(self):
        width = fnLParenImage.width
        height = self.argList.spineHeight
        if self.closed:
            width += self.argList.width + fnRParenImage.width - 1
        else:
            width += self.argList.width
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            # Left paren/bracket/brace
            lParenImg = fnLParenImage if self.closed else fnLParenOpenImage
            lParenImg = icon.yStretchImage(lParenImg, fnLParenExtendDupRows,
                    self.argList.spineHeight)
            # Output site
            outSiteX = self.sites.attrOut.xOffset
            outSiteY = self.sites.attrOut.yOffset - icon.attrOutImage.height // 2
            lParenImg.paste(icon.dimAttrOutImage, (outSiteX, outSiteY),
                    mask=icon.attrOutImage)
            # Body input site(s)
            self.argList.drawBodySites(lParenImg)
            self.drawList = [((0, 0), lParenImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(lParenImg.width -
                    icon.OUTPUT_SITE_DEPTH - 1,
                    self.sites.attrOut.yOffset - icon.ATTR_SITE_OFFSET)
            # End paren/brace/bracket
            if self.closed:
                parenX = lParenImg.width + self.argList.width - icon.ATTR_SITE_DEPTH - 1
                rParenSrcImg = fnRParenTypeoverImage if self.typeoverActive else \
                    fnRParenImage
                rParenImg = icon.yStretchImage(rParenSrcImg, fnRParenExtendDupRows,
                    self.argList.spineHeight)
                attrInXOff = rParenImg.width - icon.attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rParenImg.paste(icon.attrInImage, (attrInXOff, attrInYOff))
                self.drawList.append(((parenX, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def argIcons(self):
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        restoreConditionalTargets(self, siteSnapLists,
         (StarIcon, StarStarIcon, ArgAssignIcon))
        return siteSnapLists

    def doLayout(self, attrSiteX, attrSiteY, layout):
        self.argList.doLayout(layout)
        self.sites.attrOut.yOffset = self.argList.spineTop + icon.ATTR_SITE_OFFSET
        layout.updateSiteOffsets(self.sites.attrOut)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        width, height = self._size()
        x = attrSiteX
        y = attrSiteY - self.argList.spineTop - icon.ATTR_SITE_OFFSET
        self.rect = (x, y, x + width, y + self.argList.spineHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = fnLParenImage.size
        bodyWidth -= icon.ATTR_SITE_DEPTH
        argListLayouts = self.argList.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        else:
            attrLayouts = [None]
        layouts = []
        for argLayout, attrLayout in iconlayout.allCombinations(
                (argListLayouts, attrLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight,
                    bodyHeight // 2 + icon.ATTR_SITE_OFFSET)
            argLayout.mergeInto(layout, bodyWidth - 1, -icon.ATTR_SITE_OFFSET)
            argWidth = argLayout.width
            # layout now incorporates argument layout sizes, but not end paren
            if self.closed:
                layout.width = fnLParenImage.width-1 + argWidth-1 + fnRParenImage.width-1
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1, 0,)
            else:
                layout.width = fnLParenImage.width-1 + argWidth-1
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Add back the attribute site on the end paren.  Done here to allow the site to
        # be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', comn.rectWidth(self.rect) -
         icon.ATTR_SITE_DEPTH, comn.rectHeight(self.rect) // 2 + icon.ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def textRepr(self):
        return '(' + icon.seriesTextRepr(self.sites.argIcons) + ')' + \
               icon.attrTextRepr(self)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('(')
        argText = icon.seriesSaveText(brkLvl, self.sites.argIcons, False, export)
        text.concat(brkLvl, argText)
        text.add(None, ')')
        return text

    def dumpName(self):
        return "call("  + (")" if self.closed else "")

    def execute(self, attrOfValue):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return None
        for site in self.sites.argIcons:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
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

    def createAst(self, attrOfAst):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        argAsts = []
        kwdArgAsts = []
        for site in self.sites.argIcons:
            arg = site.att
            if arg is None:
                if site.name == 'argIcons_0':
                    continue  # 1st site can be empty, meaning "no arguments"
                raise icon.IconExecException(self, "Missing argument(s)")
            if isinstance(arg, ArgAssignIcon):
                key = arg.sites.leftArg.att
                value = arg.sites.rightArg.att
                if key is None:
                    raise icon.IconExecException(arg, "Missing keyword")
                if not isinstance(key, nameicons.IdentifierIcon):
                    raise icon.IconExecException(arg, "Keyword must be identifier")
                if value is None:
                    raise icon.IconExecException(arg, "Missing keyword value")
                kwdArgAsts.append(ast.keyword(key.name, value.createAst()))
            elif isinstance(arg, StarStarIcon):
                if arg.sites.argIcon.att is None:
                    raise icon.IconExecException(arg, "Missing value for **")
                kwdArgAsts.append(ast.keyword(None, arg.sites.argIcon.att.createAst()))
            else:
                argAsts.append(arg.createAst())
        return icon.composeAttrAst(self, ast.Call(attrOfAst, argAsts, kwdArgAsts,
         lineno=self.id, col_offset=0))

    def backspace(self, siteId, evt):
        backspaceListIcon(self, siteId, evt)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:8] != 'argIcons':
            return None
        entryOnIc = entryIc.parent() is self
        if entryOnIc and text == '*':
            return "accept"
        if entryOnIc and text[0] == '*' and len(text) == 2 and (text[1].isalnum() or \
                text[1] == ' '):
            return StarIcon(self.window), text[1]
        if entryOnIc and text[:2] == '**':
            return StarStarIcon(self.window), None
        if isinstance(entryIc.parent(), nameicons.IdentifierIcon) and \
                text == '=' and onAttr:
            return ArgAssignIcon(self.window), None
        # Typeover for lists, tuples, and dicts is handled by hard-coded parsing because
        # closing of matching open parens/brackets/braces needs to take precedence
        return None

    def setTypeover(self, idx, site):
        self.drawList = None
        if idx is None or idx > 0:
            self.typeoverActive = False
            return False
        self.typeoverActive = True
        return True

    def typeoverSites(self, allRegions=False):
        if self.typeoverActive:
            before = iconsites.makeSeriesSiteId('argIcons', len(self.sites.argIcons) - 1)
            returnData = before, 'attrIcon', ')', 0
            return [returnData] if allRegions else returnData
        return [] if allRegions else (None, None, None, None)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch both parens to be considered selected
        if not icon.Icon.inRectSelect(self, rect):
            return False
        selLeft, selTop, selRight, selBottom = rect
        icLeft, icTop, icRight, icBottom = self.rect
        if selLeft > icLeft + fnLParenImage.width:
            return False
        if selRight < icRight - fnRParenImage.width:
            return False
        return True

class CprhIfIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth = icon.getTextSize(" if", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('cprhOut', 'cprhOut', 0, siteYOffset)
        self.sites.add('testIcon', 'input', bodyWidth-1 - icon.OUTPUT_SITE_DEPTH,
                siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            img = Image.new('RGBA', (bodyWidth, bodyHeight), color=(0, 0, 0, 0))
            img.paste(icon.iconBoxedText(" if", icon.boldFont, icon.KEYWORD_COLOR),
                    (0, 0))
            cphYOff = bodyHeight // 2 - cphSiteImage.height // 2
            img.paste(cphSiteImage, (0, cphYOff))
            inImageY = self.sites.testIcon.yOffset - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.testIcon.xOffset, inImageY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, cprhX, cprhY, layout):
        width, height = self.bodySize
        top = cprhY - height // 2
        self.rect = (cprhX, top, cprhX + width, top + height)
        layout.doSubLayouts(self.sites.cprhOut, cprhX, cprhY)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        if self.sites.testIcon.att is None:
            testIconLayouts = (None,)
        else:
            testIconLayouts = self.sites.testIcon.att.calcLayouts()
        layouts = []
        for testIconLayout in testIconLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(testIconLayout, 'testIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "if " + icon.argTextRepr(self.sites.testIcon)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("if ")
        icon.addArgSaveText(text, brkLvl, self.sites.testIcon, contNeeded, export)
        return text

    def createAst(self):
        if self.sites.testIcon.att is None:
            raise icon.IconExecException(self,
                    'Missing argument to "if" in comprehension')
        return self.sites.testIcon.att.createAst()

class CprhForIcon(icon.Icon):
    def __init__(self, isAsync=False, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.isAsync = isAsync
        text = " async for" if isAsync else " for"
        bodyWidth = icon.getTextSize(text)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        inWidth = icon.getTextSize("in")[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, inWidth)
        siteYOffset = bodyHeight // 2
        targetXOffset = bodyWidth - icon.OUTPUT_SITE_DEPTH
        self.tgtList = iconlayout.ListLayoutMgr(self, 'targets', targetXOffset,
                siteYOffset, simpleSpine=True)
        self.sites.add('cprhOut', 'cprhOut', 0, siteYOffset)
        iterX = bodyWidth-1 + self.tgtList.width-1 + inWidth-1
        self.sites.add('iterIcon', 'input', iterX, siteYOffset)
        totalWidth = iterX
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            bodyWidth, bodyHeight, inWidth = self.bodySize
            img = Image.new('RGBA', (bodyWidth, bodyHeight),
             color=(0, 0, 0, 0))
            txt = " async for" if self.isAsync else " for"
            txtImg = icon.iconBoxedText(txt, color=icon.KEYWORD_COLOR)
            img.paste(txtImg, (0, 0))
            img.paste(cphSiteImage, (0, bodyHeight // 2 - cphSiteImage.height // 2))
            inImgX = bodyWidth - 1 - icon.inSiteImage.width
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            cntrSiteY = self.tgtList.spineTop
            bodyTopY = cntrSiteY - bodyHeight // 2
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            tgtListOffset = bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            self.drawList += self.tgtList.drawSimpleSpine(tgtListOffset, cntrSiteY)
            # Target list commas
            self.drawList += self.tgtList.drawListCommas(tgtListOffset, cntrSiteY)
            # "in"
            txtImg = icon.iconBoxedText("in", color=icon.KEYWORD_COLOR)
            img = Image.new('RGBA', (txtImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            inImgX = txtImg.width - icon.inSiteImage.width
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            inOffset = bodyWidth - 1 + self.tgtList.width - 1
            self.drawList.append(((inOffset, bodyTopY), img))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.tgtList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, cprhX, cprhY, layout):
        self.tgtList.doLayout(layout)
        bodyWidth, bodyHeight, inWidth = self.bodySize
        width = bodyWidth-1 + self.tgtList.width-1 + inWidth
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        if self.tgtList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.tgtList.spineTop)
            heightBelow = max(heightBelow, self.tgtList.spineHeight -
                    self.tgtList.spineTop)
        self.sites.cprhOut.yOffset = heightAbove
        left = cprhX
        top = cprhY - heightAbove
        self.rect = (left, top, left + width, top + heightAbove + heightBelow)
        layout.updateSiteOffsets(self.sites.cprhOut)
        layout.doSubLayouts(self.sites.cprhOut, cprhX, cprhY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        tgtListLayouts = self.tgtList.calcLayouts()
        if self.sites.iterIcon.att is None:
            iterLayouts = (None,)
        else:
            iterLayouts = self.sites.iterIcon.att.calcLayouts()
        bodyWidth, bodyHeight, inWidth = self.bodySize
        tgtXOff = bodyWidth - 1
        layouts = []
        for tgtListLayout, iterLayout in iconlayout.allCombinations(
                (tgtListLayouts, iterLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            tgtListLayout.mergeInto(layout, tgtXOff, 0)
            iterXOff = bodyWidth - 1 + tgtListLayout.width - 1 + inWidth - 1
            layout.addSubLayout(iterLayout, 'iterIcon', iterXOff, 0)
            iterWidth = 0 if iterLayout is None else iterLayout.width
            layout.width = iterXOff + iterWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        text = "async for" if self.isAsync else "for"
        tgtText = icon.seriesTextRepr(self.sites.targets)
        iterText = icon.argTextRepr(self.sites.iterIcon)
        return text + " " + tgtText + " in " + iterText

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("async for " if self.isAsync else "for ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.targets, contNeeded, export)
        text.add(None, " in ")
        icon.addArgSaveText(text, brkLvl, self.sites.iterIcon, contNeeded, export)
        return text

    def dumpName(self):
        return "for (cprh)"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self, ifAsts):
        if self.sites.iterIcon.att is None:
            raise icon.IconExecException(self, 'Missing iteration value in comprehension')
        iterAst = self.sites.iterIcon.att.createAst()
        for target in self.sites.targets:
            if target.att is None:
                raise icon.IconExecException(self, 'Missing target in comprehension')
        tgtAsts = [tgt.att.createAst() for tgt in self.sites.targets]
        if len(tgtAsts) == 1:
            targetAst = tgtAsts[0]
        else:
            targetAst = ast.Tuple(tgtAsts, ctx=ast.Store(), lineno=self.id, col_offset=0)
        return ast.comprehension(targetAst, iterAst, ifAsts, self.isAsync)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft - 1
        bodyWidth, bodyHeight, inWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

class DictElemIcon(infixicon.InfixIcon):
    """Individual entry in a dictionary constant"""
    def __init__(self, window=None, location=None):
        infixicon.InfixIcon.__init__(self, ":", icon.colonImage, False, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a dictionary constant
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            return isinstance(ic, DictIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = \
                [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def execute(self):
        if self.sites.leftArg.att is None:
            raise icon.IconExecException(self, "Missing argument name")
        if self.sites.rightArg.att is None:
            raise icon.IconExecException(self, "Missing argument value")
        key = self.sites.leftArg.att.execute()
        value = self.sites.rightArg.att.execute()
        return key, value

class ArgAssignIcon(infixicon.InfixIcon):
    """Special assignment statement for use only in function argument lists"""
    def __init__(self, window=None, location=None):
        infixicon.InfixIcon.__init__(self, "=", argAssignImage, False, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            return ic.__class__ in (CallIcon, blockicons.DefIcon,
                    blockicons.ClassDefIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = \
            [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def execute(self):
        if self.sites.leftArg.att is None:
            raise icon.IconExecException(self, "Missing argument name")
        if self.sites.rightArg.att is None:
            raise icon.IconExecException(self, "Missing argument value")
        if not isinstance(self.sites.leftArg.att, nameicons.IdentifierIcon):
            raise icon.IconExecException(self, "Argument name is not identifier")
        return self.sites.leftArg.att.name, self.sites.rightArg.att.execute()

class StarIcon(opicons.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, '*', window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list,
        # list, tuple, or assignment
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def matingIcon(ic, siteId):
            siteName, idx = iconsites.splitSeriesSiteId(siteId)
            if ic.__class__ in (CallIcon, blockicons.DefIcon, ListIcon, TupleIcon):
                return siteName == "argIcons"
            if ic.__class__ is assignicons.AssignIcon:
                return siteName is not None and siteName[:7] in ("targets", "values")
            return False
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = \
                [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def createAst(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument to star")
        return ast.Starred(self.arg().createAst(), nameicons.determineCtx(self),
                lineno=self.id, col_offset=0)

    def clipboardRepr(self, offset, iconsToCopy):
        # Parent UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

class StarStarIcon(opicons.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, '**', window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list,
        # or dictionary
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def matingIcon(ic, siteId):
            siteName, idx = iconsites.splitSeriesSiteId(siteId)
            return ic.__class__ in (CallIcon, blockicons.DefIcon, DictIcon) and \
                   siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = \
                [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

def createComprehensionAst(ic):
    eltIcon = ic.childAt('argIcons_0')
    if eltIcon is None:
        raise icon.IconExecException(ic, "Missing expression")
    generators = []
    for site in ic.sites.cprhIcons:
        cprhIcon = site.att
        if cprhIcon is None:
            continue
        if isinstance(cprhIcon, CprhForIcon):
            generators.append([cprhIcon])
        elif isinstance(cprhIcon, CprhIfIcon):
            generators[-1].append(cprhIcon)
        else:
            raise icon.IconExecException(cprhIcon, 'Unexpected item in comprehension')
    if len(generators) == 0:
        raise icon.IconExecException(ic, 'Missing "for" in comprehension')
    generatorAsts = []
    for generator in generators:
        ifAsts = [ifClause.createAst() for ifClause in generator[1:]]
        generatorAsts.append(generator[0].createAst(ifAsts))
    if isinstance(ic, DictIcon):
        if isinstance(eltIcon, DictElemIcon):
            key = eltIcon.childAt('leftArg')
            value = eltIcon.childAt('rightArg')
            if not key or not value:
                raise icon.IconExecException(eltIcon,
                        "Missing argument to dictionary element")
            return ast.DictComp(key.createAst(), value.createAst(), generatorAsts,
             lineno=ic.id, col_offset=0)
        else:
            return ast.SetComp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
             col_offset=0)
    elif isinstance(ic, ListIcon):
        return ast.ListComp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
         col_offset=0)
    return ast.GeneratorExp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
     col_offset=0)

def restoreConditionalTargets(ic, snapLists, directAttachmentClasses):
    """Add back versions of sites that were filtered out for having more local snap
    targets (such as left arg of BinOpIcon).  The ones added back are conditional on
    icon types that must be directly connected (directAttachmentClasses)."""
    snapFn = lambda ic, s: ic.__class__ in directAttachmentClasses
    if 'conditional' not in snapLists:
        snapLists['conditional'] = []
    for site in ic.sites.argIcons:
        for i, pos, name in snapLists.get("input", []):
            if name == site.name:
                break
        else:
            snapLists['conditional'].append((ic, ic.posOfSite(site.name),
            site.name, site.type, snapFn))

def backspaceListIcon(ic, site, evt):
    siteName, index = iconsites.splitSeriesSiteId(site)
    allArgs = ic.argIcons()
    nonEmptyArgs = [i for i in allArgs if i is not None]
    numArgs = len(nonEmptyArgs)
    redrawRegion = comn.AccumRects(ic.topLevelParent().hierRect())
    attrAttached = ic.closed and ic.childAt('attrIcon')
    win = ic.window
    if site == "attrIcon":
        # On backspace from the outside right paren
        if len(allArgs) < 2 and not attrAttached:
            if isinstance(ic, TupleIcon):
                # For tuple icons, turn back in to cursor paren
                cursorParen = parenicon.CursorParenIcon(window=win)
                parent = ic.parent()
                child = ic.childAt('argIcons_0')
                if parent is None:
                    ic.replaceChild(None, 'argIcons_0')
                    win.replaceTop(ic, cursorParen)
                else:
                    parent.replaceChild(cursorParen, parent.siteOf(ic))
                cursorParen.replaceChild(child, 'argIcon')
                ic = cursorParen
            # With either 0 or 1 argument, safe to remove right bracket
            if numArgs == 0:
                cursIc = ic
                cursSite = 'argIcon' if isinstance(ic, parenicon.CursorParenIcon) \
                    else 'argIcons_0'
            else:
                cursIc, cursSite = icon.rightmostSite(icon.findLastAttrIcon(allArgs[-1]))
            # Expand scope of the paren to its max, rearrange hierarchy around it
            reorderexpr.reorderArithExpr(ic)
            ic.reopen()
            win.cursor.setToIconSite(cursIc, cursSite)
            redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
            win.refresh(redrawRegion.get())
            return
        else:
            # Multiple arguments remaining or attribute attached to right paren.
            # Not safe to open.  Just move the cursor in to the list.
            lastIdx = len(allArgs) - 1
            if allArgs[lastIdx] is None:
                win.cursor.setToIconSite(ic, "argIcons", lastIdx)
            else:
                rightmostIcon = icon.findLastAttrIcon(allArgs[lastIdx])
                rightmostIcon, rightmostSite = icon.rightmostSite(rightmostIcon)
                win.cursor.setToIconSite(rightmostIcon, rightmostSite)
            return
    elif index == 0:
        # Backspace in to the open paren/bracket/brace: delete if possible
        parent = ic.parent()
        if numArgs == 0 and not attrAttached:
            # Delete the list if it's empty
            if parent is None:
                # Open paren was the only thing left of the statement.  Remove
                if ic.prevInSeq() is not None:
                    cursorIc = ic.prevInSeq()
                    cursorSite = 'seqOut'
                elif ic.nextInSeq() is not None:
                    cursorIc = ic.nextInSeq()
                    cursorSite = 'seqIn'
                else:
                    cursorIc = None
                    pos = ic.pos()
                win.removeIcons([ic])
                if cursorIc is None:
                    win.cursor.setToWindowPos(pos)
                else:
                    win.cursor.setToIconSite(cursorIc, cursorSite)
            else:
                parentSite = None if parent is None else parent.siteOf(ic)
                redrawRect = win.removeIcons([ic], refresh=False)
                redrawRegion.add(redrawRect)
                if not parent.hasSite(parentSite):
                    # Last element of a list can disappear when icon is removed
                    parent.insertChild(None, parentSite)
                    redrawRegion.add(win.layoutDirtyIcons(
                        filterRedundantParens=False))
                win.cursor.setToIconSite(parent, parentSite)
                win.refresh(redrawRegion.get())
            return
        elif numArgs == 1 and not attrAttached:
            # Just one item left in the list.  Unwrap the parens/brackets/braces
            # from around the content
            parent = ic.parent()
            content = nonEmptyArgs[0]
            if parent is None:
                # List was on top level
                ic.replaceChild(None, ic.siteOf(content))
                win.replaceTop(ic, content)
                topNode = reorderexpr.reorderArithExpr(content)
                coincSite = topNode.hasCoincidentSite()
                if coincSite:
                    curIc, curSite = iconsites.lowestCoincidentSite(topNode, coincSite)
                    win.cursor.setToIconSite(curIc, curSite)
                else:
                    win.cursor.setToIconSite(topNode, 'output')
            else:
                # List had a parent.  Remove by attaching content to parent if
                # the parent site is an input site.  If it's not (CallIcon), then
                # load the content in to the pendingArg of an entry icon
                parentSite = parent.siteOf(ic)
                if parent.typeOf('parentSite') == 'input':
                    parent.replaceChild(content, parentSite)
                    reorderexpr.reorderArithExpr(content)
                    win.cursor.setToIconSite(parent, parentSite)
                else:  # ic is on an attribute site.  Create an entry icon
                    win.entryIcon = entryicon.EntryIcon(window=win)
                    parent.replaceChild(win.entryIcon, parentSite)
                    win.entryIcon.setPendingArg(content)
                    win.cursor.setToEntryIcon()
                    win.redisplayChangedEntryIcon(evt, redrawRegion.get())
                    return
            redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
            win.refresh(redrawRegion.get())
            return
        else:
            # Multiple arguments remaining in list, or icon attached to attribute
            # site.  Not safe to remove.  Pop  up context menu to change type.
            win.listPopupIcon = ic
            win.listPopupVal.set(
                '(' if isinstance(ic, TupleIcon) else '[')
            # Tkinter's pop-up grab does not allow accelerator keys to operate
            # while up, which is unfortunate as you'd really like to type [ or (
            win.listPopup.tk_popup(evt.x_root, evt.y_root, 0)
    else:
        # Cursor is on comma input.  Delete if empty or previous site is empty.
        # Otherwise, create an entry icon with the comma clause content as pending
        # argument, and attach to right of previous argument
        backspaceComma(ic, site, evt)

def backspaceComma(ic, cursorSite, evt):
    """Backspace when cursor is at the comma site of an icon with a sequence.  Deletes
    empty site left or right of the comma, or if both sites are occupied, join them
    with an entry icon."""
    win = ic.window
    siteName, index = iconsites.splitSeriesSiteId(cursorSite)
    prevSite = iconsites.makeSeriesSiteId(siteName, index - 1)
    childAtCursor = ic.childAt(cursorSite)
    childAtPrevSite = ic.childAt(prevSite)
    topIcon = ic.topLevelParent()
    redrawRegion = comn.AccumRects(topIcon.hierRect())
    if not childAtPrevSite:
        # Previous comma clause is empty, remove the site
        ic.removeEmptySeriesSite(prevSite)
        win.cursor.setToIconSite(ic, prevSite)
        redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
        win.refresh(redrawRegion.get())
        return
    rightmostIcon, rightmostSite = icon.rightmostSite(childAtPrevSite)
    if not childAtCursor:
        # Comma clause with cursor is empty, remove the site
        ic.removeEmptySeriesSite(cursorSite)
        win.cursor.setToIconSite(rightmostIcon, rightmostSite)
        redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
        win.refresh(redrawRegion.get())
        return
    # Neither the cursor site nor the prior site is empty.  Stitch together the
    # content of the two sites with an entry icon, and remove the cursor site
    win.entryIcon = entryicon.EntryIcon(window=win)
    ic.replaceChild(None, cursorSite)
    if ic.hasSite(cursorSite):
        ic.removeEmptySeriesSite(cursorSite)
    rightmostIcon.replaceChild(win.entryIcon, rightmostSite)
    win.entryIcon.setPendingArg(childAtCursor)
    win.cursor.setToEntryIcon()
    win.redisplayChangedEntryIcon(evt, redrawRegion.get())

def composeAttrAstIf(ic, icAst, skipAttr):
    """Wrapper for icon.composeAttrAst, giving it a disable flag (skipAttr), to simplify
    createAst methods for mutable icons which may need to suppress execution of
    attributes for updating mutables alone."""
    if skipAttr:
        return icAst
    return icon.composeAttrAst(ic, icAst)

def createListIconFromAst(astNode, window):
    topIcon = ListIcon(window)
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.List, createListIconFromAst)

def createTupleIconFromAst(astNode, window):
    topIcon = TupleIcon(window)
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Tuple, createTupleIconFromAst)

def createDictIconFromAst(astNode, window):
    topIcon = DictIcon(window)
    argIcons = []
    for i, key in enumerate(astNode.keys):
        value = icon.createFromAst(astNode.values[i], window)
        if key is None:
            starStar = StarStarIcon(window)
            starStar.replaceChild(value, "argIcon")
            argIcons.append(starStar)
        else:
            dictElem = DictElemIcon(window)
            dictElem.replaceChild(icon.createFromAst(key, window), "leftArg")
            dictElem.replaceChild(value, "rightArg")
            argIcons.append(dictElem)
    topIcon.insertChildren(argIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Dict, createDictIconFromAst)

def createSetIconFromAst(astNode, window):
    topIcon = DictIcon(window)
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Set, createSetIconFromAst)

def createCallIconFromAst(astNode, window):
    callIcon = CallIcon(window)
    argIcons = [icon.createFromAst(e, window) for e in astNode.args]
    for key in astNode.keywords:
        valueIcon = icon.createFromAst(key.value, window)
        if key.arg is None:
            starStarIcon = StarStarIcon(window)
            starStarIcon.replaceChild(valueIcon, 'argIcon')
            argIcons.append(starStarIcon)
        else:
            kwIcon = ArgAssignIcon(window)
            kwIcon.replaceChild(nameicons.IdentifierIcon(key.arg, window), 'leftArg')
            kwIcon.replaceChild(valueIcon, 'rightArg')
            argIcons.append(kwIcon)
    topIcon = icon.createFromAst(astNode.func, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(callIcon, "attrIcon")
    callIcon.insertChildren(argIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Call, createCallIconFromAst)

def createComprehensionIconFromAst(astNode, window):
    if astNode.__class__ is ast.DictComp:
        tgt = astNode.value
        key = astNode.key
    else:
        tgt = astNode.elt
        key = None
    cprhType = {ast.ListComp: ListIcon, ast.SetComp: DictIcon,
        ast.GeneratorExp: TupleIcon, ast.DictComp: DictIcon}[astNode.__class__]
    topIcon = cprhType(window=window)
    if key is None:
        topIcon.replaceChild(icon.createFromAst(tgt, window), 'argIcons_0')
    else:
        dictElem = DictElemIcon(window)
        dictElem.replaceChild(icon.createFromAst(key, window), "leftArg")
        dictElem.replaceChild(icon.createFromAst(tgt, window), "rightArg")
        topIcon.replaceChild(dictElem, 'argIcons_0')
    clauseIdx = 0
    for gen in astNode.generators:
        forIcon = CprhForIcon(gen.is_async, window)
        if isinstance(gen.target, ast.Tuple):
            tgtIcons = [icon.createFromAst(t, window) for t in gen.target.elts]
            forIcon.insertChildren(tgtIcons, "targets", 0)
        else:
            forIcon.insertChild(icon.createFromAst(gen.target, window), "targets", 0)
        forIcon.replaceChild(icon.createFromAst(gen.iter, window), 'iterIcon')
        topIcon.insertChild(forIcon, "cprhIcons", clauseIdx)
        clauseIdx += 1
        for i in gen.ifs:
            ifIcon = CprhIfIcon(window)
            testIcon = icon.createFromAst(i, window)
            ifIcon.replaceChild(testIcon, 'testIcon')
            topIcon.insertChild(ifIcon, "cprhIcons", clauseIdx)
            clauseIdx += 1
    return topIcon
icon.registerIconCreateFn(ast.ListComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.DictComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.SetComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.GeneratorExp, createComprehensionIconFromAst)

def createStarIconFromAst(astNode, window):
    topIcon = StarIcon(window)
    topIcon.replaceChild(icon.createFromAst(astNode.value, window), "argIcon")
    return topIcon
icon.registerIconCreateFn(ast.Starred, createStarIconFromAst)