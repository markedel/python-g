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
import subscripticon
import entryicon
import infixicon
import reorderexpr

UNASSOC_IF_IDENT = '___pyg_cprh_unassoc_if'
UNASSOC_IF_MACRO_NAME = 'CprhUnassocIf'

listLBktImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o        o",
 "..o   %%%  o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %%%  o",
 "..o        o",
 "..oooooooooo"))
listLBrktExtendDupRows = (9,)

listMutableBktImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o        o",
 "..o   %%%  o",
 "..o   %  % o",
 "..o   %  % o",
 "..o   5%%  o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %%%  o",
 "..o        o",
 "..oooooooooo"))

listMutableModBktImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o   rRr  o",
 "..o  rRRRr o",
 "..o  RRRRR o",
 "..o  rRRRr o",
 "..o   rRr  o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %7   o",
 "..o   %%%  o",
 "..o        o",
 "..oooooooooo"))

listRBktImage = comn.asciiToImage((
 "oooooooooo",
 "o        o",
 "o        o",
 "o  %%%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o   7%   o",
 "o  %%%   o",
 "o        o",
 "oooooooooo"))
listRBrktExtendDupRows = (9,)

listRBktTypeoverImage = comn.asciiToImage((
 "oooooooooo",
 "o        o",
 "o        o",
 "o  888   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o   98   o",
 "o  888   o",
 "o        o",
 "oooooooooo"))

tupleLParenImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o        o",
 "..o    5   o",
 "..o   76   o",
 "..o   47   o",
 "..o   %8   o",
 "..o  9%8   o",
 "..o  8%8   o",
 "..o  8%8   o",
 "..o  8%8   o",
 "..o  9%8   o",
 "..o   %8   o",
 "..o   47   o",
 "..o   76   o",
 "..o    5   o",
 "..o        o",
 "..oooooooooo"))
tupleLParenExtendDupRows = (9,)

tupleRParenImage = comn.asciiToImage((
 "ooooooooo",
 "o       o",
 "o       o",
 "o  5    o",
 "o  67   o",
 "o  74   o",
 "o  8%   o",
 "o  8%9  o",
 "o  8%8  o",
 "o  8%8  o",
 "o  8%8  o",
 "o  8%9  o",
 "o  8%   o",
 "o  74   o",
 "o  67   o",
 "o  5    o",
 "o       o",
 "ooooooooo"))
tupleRParenExtendDupRows = (9,)

tupleRParenTypeoverImage = comn.asciiToImage((
 "ooooooooo",
 "o       o",
 "o       o",
 "o  9    o",
 "o  99   o",
 "o  99   o",
 "o   8   o",
 "o   8   o",
 "o   99  o",
 "o   99  o",
 "o   99  o",
 "o   8   o",
 "o   8   o",
 "o  99   o",
 "o  99   o",
 "o  9    o",
 "o       o",
 "ooooooooo"))

lBraceImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o        o",
 "..o        o",
 "..o   912  o",
 "..o   639  o",
 "..o   65   o",
 "..o   65   o",
 "..o  9%7   o",
 "..o  %%    o",
 "..o  9%7   o",
 "..o   65   o",
 "..o   65   o",
 "..o   639  o",
 "..o   912  o",
 "..o        o",
 "..o        o",
 "..oooooooooo"))
lBraceExtendDupRows = 7, 11

mutableModBraceImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o   rRr  o",
 "..o  rRRRr o",
 "..o  RRRRR o",
 "..o  rRRRr o",
 "..o   rRr  o",
 "..o   65   o",
 "..o  9%7   o",
 "..o  %%    o",
 "..o  9%7   o",
 "..o   65   o",
 "..o   65   o",
 "..o   639  o",
 "..o   912  o",
 "..o        o",
 "..o        o",
 "..oooooooooo"))

mutableBraceImage = comn.asciiToImage((
 "..oooooooooo",
 "..o        o",
 "..o        o",
 "..o   9%%  o",
 "..o   %  % o",
 "..o   %  % o",
 "..o   6%%  o",
 "..o   65   o",
 "..o  9%7   o",
 "..o  %%    o",
 "..o  9%7   o",
 "..o   65   o",
 "..o   65   o",
 "..o   639  o",
 "..o   912  o",
 "..o        o",
 "..o        o",
 "..oooooooooo"))

rBraceImage = comn.asciiToImage((
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o  219   o",
 "o  936   o",
 "o   56   o",
 "o   56   o",
 "o   7%9  o",
 "o    %%  o",
 "o   7%9  o",
 "o   56   o",
 "o   56   o",
 "o  936   o",
 "o  219   o",
 "o        o",
 "o        o",
 "oooooooooo"))
rBraceExtendDupRows = 7, 11

rBraceTypeoverImage = comn.asciiToImage((
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o  99    o",
 "o   8    o",
 "o   99   o",
 "o   99   o",
 "o    8   o",
 "o    88  o",
 "o    8   o",
 "o   99   o",
 "o   99   o",
 "o   8    o",
 "o  99    o",
 "o        o",
 "o        o",
 "oooooooooo"))

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
 ".oooooooooo",
 ".o        o",
 ".o        o",
 ".o        o",
 ".o   84   o",
 ".o  81    o",
 ".o  28    o",
 ".o 73     o",
 ".o 56     o",
 ".o 48     o",
 ".o 19     o",
 ".o 19     o",
 ".o 18     o",
 ".o 28     o",
 ".o 68     o",
 ".o        o",
 ".o        o",
 ".oooooooooo"))
fnLParenExtendDupRows = 11,

fnLParenOpenImage = comn.asciiToImage((
 ".oooooooooo",
 ".o        o",
 ".o        o",
 ".o        o",
 ".o   84   o",
 ".o  81    o",
 ".o  28    o",
 ".o 73     o",
 ".o 98     o",
 ".o        o",
 ".o 5      o",
 ".o 19     o",
 ".o 18     o",
 ".o 28     o",
 ".o 68     o",
 ".o        o",
 ".o        o",
 ".oooooooooo"))

fnRParenImage = comn.asciiToImage( (
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o   82   o",
 "o    29  o",
 "o    38  o",
 "o    37  o",
 "o    37  o",
 "o    38  o",
 "o   829  o",
 "o   74   o",
 "o   38   o",
 "o  65    o",
 "o 85     o",
 "o        o",
 "o        o",
 "oooooooooo"))
fnRParenExtendDupRows = 7,

fnRParenTypeoverImage = comn.asciiToImage( (
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o    8   o",
 "o    8   o",
 "o    8   o",
 "o    99  o",
 "o    99  o",
 "o    99  o",
 "o    8   o",
 "o   99   o",
 "o   99   o",
 "o  99    o",
 "o 99     o",
 "o        o",
 "o        o",
 "oooooooooo"))

argAssignImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o %%%% o",
 "o     o.",
 "o    o..",
 "o %%%%o.",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "oooooooo"))

colonImage = comn.asciiToImage((
 "ooooooo",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "o %%  o",
 "o %%  o",
 "o    o.",
 "o   o..",
 "o    o.",
 "o %%  o",
 "o %%  o",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "ooooooo"))

class ListTypeIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, leftText, rightText, window, leftImgFn=None,
            rightImgFn=None, closed=True, typeover=False, obj=None, location=None):
        """Note that the images generated by leftImgFn and rightImgFn get modified by
        the draw method, so must not return template images."""
        icon.Icon.__init__(self, window)
        self.closed = False         # self.close call will set this and endParenTypeover
        self.endParenTypeover = False
        self.commaTypeover = None
        self.leftText = leftText
        self.rightText = rightText
        self.leftImgFn = leftImgFn
        self.rightImgFn = rightImgFn
        self.object = obj
        leftWidth, height = leftImgFn(0).size
        self.sites.add('output', 'output', 0, height // 2)
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', leftWidth-1, height//2,
            allowsTrailingComma=True)
        self.sites.addSeries('cprhIcons', 'cprhIn', 1, [(leftWidth-1, height//2)],
            cursorSkip=True)
        width = self.sites.cprhIcons[-1].xOffset + rightImgFn(0).width
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, height-2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if closed:
            self.close(typeover)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
                    self.sites.output.yOffset, typeoverIdx=self.commaTypeover)
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
        self._drawEmptySites(toDragImage, clip, allowTrailingComma=True,
            hilightEmptySeries=self.isComprehension())

    def isComprehension(self):
        return len(self.sites.cprhIcons) > 1

    def acceptsComprehension(self):
        return len(self.sites.argIcons) <= 1

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None,
            preserveNoneAtZero=False):
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
            icon.Icon.insertChild(self, child, siteIdOrSeriesName, seriesIdx, childSite,
                preserveNoneAtZero=preserveNoneAtZero)
            return
        #  Without commas, a comprehension list must never have an empty site, except for
        #  the last one, which must always exist and remain empty
        if child is None:
            return
        if len(self.sites.argIcons) > 1:
            # Single element tuples (x,) can still get a comprehension
            if not (isinstance(self, TupleIcon) and len(self.sites.argIcons) == 2 and
                    self.sites.argIcons[1].att is None):
                print("Can't add comprehension to multi-element list")
                return
        self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
        self.sites.lookupSeries(seriesName)[idx].attach(self, child, childSite)
        if len(self.sites.argIcons) == 2:
            # Changing a single-element tuple to a comprehension: remove the extra comma
            icon.Icon.replaceChild(self, None, 'argIcons_1')
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
        argListLayouts = self.argList.calcLayouts(argRequired=self.isComprehension())
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
                layout.width = leftWidth - 1 + argListLayout.width + cprhWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def close(self, typeover=False):
        if self.closed:
            return
        self.closed = True
        self.endParenTypeover = typeover
        if typeover:
            self.window.watchTypeover(self)
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

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False, ctx=None):
        # List and tuple icons are valid in delete and save contexts, hence the optional
        # ctx parameter.  If ctx is not None, all of the entries need to be validated as
        # store or del targets and wrapped in $Ctx$ macros if not.  Note that if the list
        # or tuple has attributes, it becomes a source of data for those attributes, and
        # we get called with ctx=None.  The attribute case is handled in
        # argSaveTextForContext, so no additional code is needed, here.
        ctxMacroNeeded = ctx is not None and self.isComprehension() and not export
        brkLvl = parentBreakLevel + 1 + (1 if ctxMacroNeeded else 0)
        if self.closed or export:
            text = filefmt.SegmentedText(self.leftText)
        else:
            text = filefmt.SegmentedText('$:o$' + self.leftText)
        # Process the elements of the list.  If we're putting a $Ctx$ macro around the
        # whole list, don't propagate the store/del context to them, but if we're not,
        # the elements need to be processed in that context.
        argText = seriesSaveTextForContext(brkLvl, self.sites.argIcons, False, export,
            None if ctxMacroNeeded else ctx, allowTrailingComma=True,
            allowEmpty=not self.isComprehension())
        text.concat(brkLvl, argText)
        # If this is a comprehension, add the comprehension components
        cprhText = filefmt.SegmentedText(None)
        for site in self.sites.cprhIcons[:-1]:
            cprhText.add(None, " ")
            icon.addArgSaveText(cprhText, brkLvl, site, False, export)
        text.concat(brkLvl, cprhText, False)
        # Right paren/bracket and possible attribute
        text.add(None, self.rightText)
        if self.closed:
            text = icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)
        if ctxMacroNeeded:
            text.wrapCtxMacro(parentBreakLevel+1, needsCont=contNeeded)
        return text

    def backspace(self, siteId, evt):
        backspaceListIcon(self, siteId, evt)

    def textEntryHandler(self, entryIc, text, onAttr):
        # Typeover for lists, tuples, and dicts is mostly handled by hard-coded parsing
        # because closing of matching open parens/brackets/braces needs to take
        # precedence.  This only handles comprehensions.
        listSiteId = self.siteOf(entryIc, recursive=True)
        if listSiteId is None or not iconsites.isSeriesSiteId(listSiteId):
            return None
        seriesName, seriesIdx = iconsites.splitSeriesSiteId(listSiteId)
        if seriesName not in ('argIcons', 'cprhIcons'):
            return None
        if not (len(self.sites.argIcons) == 1 or isinstance(self, TupleIcon) and
                len(self.sites.argIcons) == 2 and self.sites.argIcons[1].att is None):
            return None
        if not text[0] in ('f', 'a', 'i'):
            return None
        # Make sure entryIc is on the rightmost site before a comprehension site (entry
        # icons and cursors are not allowed on comprehension sites) where it's safe
        # to start a new comprehension.
        entryRightmostIcon, entryRightmostSite = icon.rightmostSite(entryIc)
        listRightmostIcon, listRightmostSite = icon.rightmostFromSite(self, listSiteId)
        if entryRightmostIcon is not listRightmostIcon or entryRightmostSite != \
                listRightmostSite:
            return None
        # Even when entryIc is the rightmost icon from a qualifying site, it could be so
        # by virtue of an unclosed paren/bracket/brace, which would become the owner
        # of the new comprehension clause.
        for ic in entryIc.parentage():
            if ic is self:
                break
            if isinstance(ic, (ListTypeIcon, parenicon.CursorParenIcon)) and \
                    not ic.closed:
                return None
        if text in ('i', 'if', 'if ') and seriesName == 'argIcons':
            # Not allowed to type 'if' as the first comprehension component.  This
            # isn't simply to discourage the bad syntax (which we do allow), but
            # because the user needs to be able to type "x if y else z" as the first
            # element of a list, without it getting turned in to a comprehension.
            return None
        if text in ('fo'[:len(text)], 'async fo'[:len(text)], 'i'):
            return 'accept'
        if text[:3] != 'for' and text[:2] != 'if' and text[:9] != 'async for':
            return None
        if onAttr:
            # On an attribute site, we can accept cprh kwds w/o waiting for delimiter
            if text == 'for':
                return CprhForIcon(window=self.window, typeover=True), None
            if text == 'async for':
                return CprhForIcon(window=self.window, typeover=True, isAsync=True), None
            if text == 'if':
                return CprhIfIcon(window=self.window), None
        textStripped = text[:-1]
        delim = text[-1]
        forDelimiters = {*entryicon.emptyDelimiters, '(', '[', ','}
        if textStripped == 'for' and delim in forDelimiters:
            return CprhForIcon(window=self.window, typeover=True), delim
        if textStripped == 'async for' and delim in forDelimiters:
            return CprhForIcon(window=self.window, typeover=True, isAsync=True), delim
        if textStripped == 'if' and delim in entryicon.delimitChars:
            return CprhIfIcon(window=self.window), delim
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        # Color just the paren if the list is not closed, not the content
        if self.closed:
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight("Unmatched open bracket/brace/paren")
        for ic in self.children():
            ic.highlightErrors(None)
        return

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if idx is None or idx > 0:
            self.endParenTypeover = False
            self.commaTypeover = None
            return False
        if site is None or site == "attrIcon":
            self.endParenTypeover = True
            return True
        name, idx = iconsites.splitSeriesSiteId(site)
        if name == 'argIcons' and idx >= 1:
            self.commaTypeover = idx
            #... It's not normal to call watchTypeover from a setTypeover call.  I've
            #    removed, but temporarily added reminder to check if anything's amiss.
            # self.window.watchTypeover(self)
            print('Removed call to watchTypeover.  Any problems with typeover?')
            return True
        return False

    def typeoverSites(self, allRegions=False):
        # Note that the code below takes advantage of the fact that both typeover regions
        # will not be active at the same time (comma typeovers are used in very limited
        # circumstances, none of which currently will lead to them being adjacent with
        # the end paren)
        if self.endParenTypeover:
            if self.isComprehension():
                series = 'cprhIcons'
                idx = len(self.sites.cprhIcons) - 2
                if idx < 0:
                    print('Did not expect comprehension to have no comprehension')
                    idx = 0
            else:
                series = 'argIcons'
                idx = len(self.sites.argIcons) - 1
            before = iconsites.makeSeriesSiteId(series, idx)
            returnData = before, 'attrIcon', ')', 0
            return [returnData] if allRegions else returnData
        if self.commaTypeover:
            before = 'argIcons_%d' % (self.commaTypeover - 1)
            after = 'argIcons_%d' % self.commaTypeover
            returnData = before, after, ',', 0
            return [returnData] if allRegions else returnData
        return [] if allRegions else (None, None, None, None)

    def argIcons(self):
        """Return list of list argument icons.  This is trivial, but exists to give list
        and dict icons an identical interface with that of the TupleIcon version which
        which has to deal with odd single-element syntax."""
        return [site.att for site in self.sites.argIcons]

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, False)

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        # The base-class placeArgs method can only handle comprehensions if they are the
        # only thing in place list (the only case for following a *series* of one type
        # with a series of another type, is list-type icons, so there's no point in
        # complicating it).  Here we also deal with the weird form of an expression or
        # comprehension clause attached via a placeholder entry icon.  This results from
        # editing off the paren/bracket/brace of a list or dragging the content out of
        # one.  In fact, unless it gets translated into a for or if icon, a comprehension
        # clause can only exist outside of a list, dict, or tuple icon if it is embedded
        # in a placeholder entry icon, since we have no concept of a naked comprehension
        # clause list.
        if canPlaceCprhArgsFromEntry(self, placeList, startSiteId, overwriteStart):
            newPlaceList = promoteCprhArgsFromEntry(placeList, removeEntryIc=doPlacement)
            addedArgs = len(newPlaceList) - len(placeList)
            placeList = newPlaceList
        else:
            addedArgs = 0
        if doPlacement:
            idx, seriesIdx = icon.Icon.placeArgs(self, placeList, startSiteId,
                overwriteStart=overwriteStart)
        else:
            idx, seriesIdx = icon.Icon.canPlaceArgs(self, placeList, startSiteId,
                overwriteStart=overwriteStart)
        # The base class method can place comprehension clauses if they are the only
        # thing in the place list.  If that happened, we can safely close the list.
        if doPlacement and self.isComprehension() and not self.closed:
            self.close(typeover=True)
        # We're done if whatever is left is not a comprehension clause
        adjustedIdx = idx if idx is None or idx == 0 else idx - addedArgs
        if icon.placeListAtEnd(placeList, idx, seriesIdx):
            return adjustedIdx, seriesIdx  # All icons placed
        if seriesIdx is not None and seriesIdx != len(placeList[idx]) - 1:
            return adjustedIdx, seriesIdx  # Place-list series aren't comprehensions
        endIdx = -1 if idx is None else idx
        if not isinstance(placeList[endIdx + 1], (CprhIfIcon, CprhForIcon)):
            return adjustedIdx, None  # Next placeList item is not a comprehension
        if len(self.sites.argIcons) > 1 or isinstance(self, TupleIcon) and self.noParens:
            return adjustedIdx, None  # The list can't accept a comprehension
        # If the first attempt at placement did nothing, we still need to perform
        # overwriteStart, and will do so even if startSiteId is in argIcons
        if doPlacement and idx is None and overwriteStart:
            self.replaceChild(None, 'argIcons_0')
        # The next thing on the (updated) placement list is a comprehension.
        # Place (or determine placement for) comprehensions at the (new) start of
        # placeList (since it's a list, it can absorb as many as there are).  We can't
        # place any other icon types, as nothing follows a comprehension clause list and
        # we can only prepend.
        if doPlacement:
            self.close(typeover=True)
        cprhIdx = 0
        while endIdx < len(placeList) - 1:
            cprhIc = placeList[endIdx + 1]
            if not isinstance(cprhIc, (CprhIfIcon, CprhForIcon)):
                return endIdx - addedArgs, None
            endIdx += 1
            if doPlacement:
                self.insertChild(cprhIc, 'cprhIcons', cprhIdx)
            cprhIdx += 1
        return endIdx - addedArgs, None

    def dumpName(self):
        return self.leftText + (self.rightText if self.closed else "")

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
        self.canProcessCtx = True

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
        ctx = nameicons.determineCtx(self)
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            if isinstance(ctx, ast.Store):
                raise icon.IconExecException(self, "Can't assign to empty list")
            if isinstance(ctx, ast.Del):
                raise icon.IconExecException(self, "Can't delete empty list")
            elts = []
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            if self.sites.attrIcon.att is None and isinstance(ctx, (ast.Store, ast.Del)):
                for site in self.sites.argIcons:
                    if not site.att.canProcessCtx:
                        ctxName = 'assignment' if isinstance(ctx, ast.Store) else 'del'
                        raise icon.IconExecException(site.att,
                            "Not a valid target for %s" % ctxName)
            elts = [site.att.createAst() for site in self.sites.argIcons]
        listContentAst = ast.List(elts=elts,  ctx=ctx, lineno=self.id, col_offset=0)
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

    def duplicate(self, linkToOriginal=False):
        ic = ListIcon(closed=self.closed, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def _stretchedLBracketImage(self, desiredHeight):
        if self.object is None:
            bracketImg = listLBktImage
        elif self.mutableModified:
             bracketImg = listMutableModBktImage
        else:
            bracketImg = listMutableBktImage
        return icon.yStretchImage(bracketImg, listLBrktExtendDupRows, desiredHeight)

    def _stretchedRBracketImage(self, desiredHeight):
        img = listRBktTypeoverImage if self.endParenTypeover else listRBktImage
        return icon.yStretchImage(img, listRBrktExtendDupRows, desiredHeight)

class TupleIcon(ListTypeIcon):
    """Tuple icons have a bunch of special cases worth mentioning:
        1) We retain the python text-syntax for a single element tuple containing a
           comma.  I tried, initially, to eliminate this and allow the differing paren
           appearance alone to distinguish tuples from parens.  The problem was that it
           made using conventional text-editing techniques for converting back and forth,
           impossible to use, requiring users to learn new editing methods.
        2) The concept of a paren-less (naked) tuple is necessary to allow typing of
           lists that precede the assignment operator.  They are also used in dragging
           elements from one list to another.  Naked tuples are only allowed in three
           places: 1) on the top level, 2) being dragged, and 3) as the pending arg of
           the entry icon.  In the entry icon, it allows the entire list to be easily
           dragged away as a unit.  The entry icon holds the list without parens
           because parens have too much meaning to the user, who will interpret them
           as gathering the arguments in to a single object."""
    def __init__(self, window, noParens=False, closed=True, obj=None, typeover=False,
                 location=None):
        self.noParens = noParens
        self.coincidentSite = "argIcons_0" if noParens else None
        if noParens:
            closed = False
        self.argList = None  # Temporary to help with initialization
        ListTypeIcon.__init__(self, '(', ')', window, closed=closed, obj=obj,
                location=location, leftImgFn=self._stretchedLTupleImage,
                rightImgFn=self._stretchedRTupleImage, typeover=typeover)
        self.canProcessCtx = True

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

    def restoreParens(self, closed=True, typeover=False):
        """Tuples with no parenthesis are allowed on the top level, to make typing
        multi-variable assignment statements more natural.  If one of these paren-less
        icons gets dragged or pasted in to an expression, it needs its parens back."""
        if not self.noParens:
            return
        self.noParens = False
        if closed:
            self.close(typeover=typeover)
        self.drawList = None
        self.coincidentSite = None
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.removeParens)

    def removeParens(self):
        if self.noParens:
            return
        self.reopen()
        self.noParens = True
        self.drawList = None
        self.coincidentSite = 'argIcons_0'
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.restoreParens)

    def acceptsComprehension(self):
        # Redefine to add prohibition on no-paren tuple becoming generator comprehension
        # and to allow comprehensions to be snapped to a one-arg tuple
        nArgs = len(self.sites.argIcons)
        return (nArgs <= 1 or nArgs == 2 and self.sites.argIcons[1].att is None) \
            and not self.noParens

    def close(self, typeover=False):
        # This code is temporary, for catching old code that thinks it can treat naked
        # tuples as closed (new code requires that they not be closed)
        if self.noParens:
            print("Something tried to close a naked tuple")
            return
        super().close(typeover=typeover)

    def calcLayouts(self):
        # If a naked tuple is no longer at the top level and needs its parens restored,
        # do so before calculating the layout (would be better to do this elsewhere).
        # Exception is EntryIcon, which can hold a naked tuple
        parent = self.parent()
        if self.noParens and parent is not None:
            if not isinstance(parent, entryicon.EntryIcon):
                self.restoreParens()
        # Enforce no display of single (populated) site tuple without comma.  (This is
        # also a questionable side-effect for a layout calculation.  It's safe because
        # we already do site-list adjustments in doLayout, and this change must be done
        # regardless of which layout is chosen.  Doing it early saves having to special-
        # case the layout calculations for a comma that doesn't yet exist.).  Do the
        # reverse when the last values are removed from an icon that still has a comma,
        # converting that in to the proper form for the empty tuple: ()
        if self.sites.argIcons[0].att is not None and len(self.sites.argIcons) <= 1 and \
                not self.noParens and not self.isComprehension():
            self.sites.argIcons.insertSite(1)
            self.commaTypeover = 1
            self.window.watchTypeover(self)
            self.window.updateTypeoverStates(draw=False)
        elif len(self.sites.argIcons) == 2 and self.sites.argIcons[0].att is None and \
                self.sites.argIcons[1].att is None and not self.noParens:
            curs = self.window.cursor
            if not (curs.type == "icon" and curs.icon is self and
                    curs.site == 'argIcons_1'):
                self.sites.argIcons.removeSite(self, 1)
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

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False, ctx=None):
        # Process naked tuple and single-element tuple syntax, (x,), not handled by
        # ListTypeIcon.
        if self.noParens:
            return icon.seriesSaveText(parentBreakLevel, self.sites.argIcons, contNeeded,
                export, allowEmpty=True)
        if not (len(self.sites.argIcons) == 2 and self.sites.argIcons[1].att is None):
            return super().createSaveText(parentBreakLevel, contNeeded, export, ctx)
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('(' if self.closed else '$:o$(')
        argText = argSaveTextForContext(brkLvl, self.sites.argIcons[0], contNeeded,
            export, ctx)
        text.concat(brkLvl, argText)
        text.add(None, ",)")
        if self.closed:
            return icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)
        return text

    def highlightErrors(self, errHighlight):
        # Can't use ListTypeIcon method on naked tuples, because we set .closed to False
        # which would trigger a highlight
        if errHighlight is None or self.noParens:
            icon.Icon.highlightErrors(self, errHighlight)
        else:
            ListTypeIcon.highlightErrors(self, errHighlight)

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
            elts = [site.att.createAst() for site in self.sites.argIcons]
        ctx = nameicons.determineCtx(self)
        if self.sites.attrIcon.att is None and isinstance(ctx, (ast.Store, ast.Del)):
            for site in self.sites.argIcons:
                if site.att is not None and not site.att.canProcessCtx:
                    ctxName = 'assignment' if isinstance(ctx, ast.Store) else 'del'
                    raise icon.IconExecException(site.att,
                        "Not a valid target for %s" % ctxName)
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

    def duplicate(self, linkToOriginal=False):
        ic = TupleIcon(noParens=self.noParens, closed=self.closed, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

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
        elif self.endParenTypeover:
            img = tupleRParenTypeoverImage
        else:
            img = tupleRParenImage
        return icon.yStretchImage(img, tupleRParenExtendDupRows, desiredHeight)

    def dumpName(self):
        if self.noParens:
            return "(naked tuple)"
        return "(" + ("" if self.closed else self.rightText)

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
        img = rBraceTypeoverImage if self.endParenTypeover else rBraceImage
        return icon.yStretchImage(img, rBraceExtendDupRows, desiredHeight)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        # Can use the superclass method for comprehensions and if the entries are either
        # all dictionary elements or all not dictionary elements, but for mixed sets,
        # need to wrap $Ctx$ macros around the minority types to get them past the Python
        # parser.
        mismatchedElems = self._findCtxViolations()
        if mismatchedElems is None:
            return ListTypeIcon.createSaveText(self, parentBreakLevel, contNeeded, export)
        brkLvl = parentBreakLevel + 1
        if self.closed or export:
            text = filefmt.SegmentedText('{')
        else:
            text = filefmt.SegmentedText('$:o${')
        argTextList = []
        for site in self.sites.argIcons:
            needsCtx = site.att in mismatchedElems and not export
            argBrkLvl = brkLvl + (1 if needsCtx else 0)
            argText = icon.argSaveText(argBrkLvl, site, contNeeded, export)
            if needsCtx:
                argText.wrapCtxMacro(brkLvl, parentCtx='D', needsCont=contNeeded)
            argTextList.append(argText)
        text.concat(brkLvl, argTextList[0])
        for argText in argTextList[1:]:
            text.add(None, ', ', contNeeded)
            text.concat(brkLvl, argText, contNeeded)
        text.add(None, '}')
        if self.closed:
            return icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)
        return text

    def duplicate(self, linkToOriginal=False):
        ic = DictIcon(closed=self.closed, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

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
        if text[0] != '*':
            return None
        if text == '*':
            return "accept"
        delimValid = entryicon.opDelimPattern.match(text[-1])
        if text[0] == '*' and len(text) == 2 and delimValid:
            return StarIcon(self.window), text[1]
        if text == '**':
            return StarStarIcon(self.window), None
        if text[:2] == '**' and len(text) == 3 and delimValid:
            return StarStarIcon(self.window), text[2]
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        if self.closed:
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight("Unmatched open brace")
        nonEmptyArgs = [site.att for site in self.sites.argIcons if site.att is not None]
        mismatchedElems = self._findCtxViolations()
        for ic in nonEmptyArgs:
            if mismatchedElems is not None and ic in mismatchedElems:
                ic.highlightErrors(icon.ErrorHighlight(
                    "Mixed set/dict elements within braces"))
            else:
                ic.highlightErrors(None)
        for ic in (site.att for site in self.sites.cprhIcons if site.att is not None):
            ic.highlightErrors(None)
        if self.closed and self.sites.attrIcon.att is not None:
            self.sites.attrIcon.att.highlightErrors(None)

    def _findCtxViolations(self):
        """Decide if the icon is a dictionary or a set, and return either None, or a set
        containing elements that do not conform to the decided type.  Note that for a
        dictionary with empty sites, the set will include None (as empty sites are a
        context violation)."""
        if len(self.sites.argIcons) < 2:
            return None
        nonEmptyArgs = [site.att for site in self.sites.argIcons if site.att is not None]
        # Decide if we're a dictionary or a set
        dictElemCount = nonDictCount = 0
        for ic in nonEmptyArgs:
            if isinstance(ic, DictElemIcon):
                dictElemCount += 1
            else:
                nonDictCount += 1
        if dictElemCount > nonDictCount:
            isDict = True
        elif dictElemCount < nonDictCount:
            isDict = False
        else:
            isDict = isinstance(nonEmptyArgs[0], DictElemIcon)
        # Return a set listing the violating icons.
        violators = None
        for site in self.sites.argIcons:
            ic = site.att
            isDictElem = isinstance(ic, DictElemIcon)
            if isDict and not isDictElem or not isDict and isDictElem:
                if violators is None:
                    violators = set()
                violators.add(ic)
        return violators

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
        self.closed = False         # self.close call will set this and endParenTypeover
        self.endParenTypeover = False
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
            self.close(typeover)

    def _size(self):
        width = fnLParenImage.width
        height = self.argList.spineHeight
        if self.closed:
            width += self.argList.width + fnRParenImage.width - 1
        else:
            width += self.argList.width
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
                rParenSrcImg = fnRParenTypeoverImage if self.endParenTypeover else \
                    fnRParenImage
                rParenImg = icon.yStretchImage(rParenSrcImg, fnRParenExtendDupRows,
                    self.argList.spineHeight)
                attrInXOff = rParenImg.width - icon.attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rParenImg.paste(icon.attrInImage, (attrInXOff, attrInYOff))
                self.drawList.append(((parenX, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip)

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

    def close(self, typeover=False):
        if self.closed:
            return
        self.closed = True
        self.endParenTypeover = typeover
        if typeover:
            self.window.watchTypeover(self)
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

    def duplicate(self, linkToOriginal=False):
        ic = CallIcon(closed=self.closed, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def textRepr(self):
        return '(' + icon.seriesTextRepr(self.sites.argIcons) + ')' + \
               icon.attrTextRepr(self)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + (2 if self.parent() is None else 1)
        text = filefmt.SegmentedText('(' if self.closed or export else '$:o$(')
        if len(self.sites.argIcons) > 1 or len(self.sites.argIcons) == 1 and \
                self.sites.argIcons[0].att is not None:
            kwArgEncountered = False
            argTextList = []
            for site in self.sites.argIcons:
                needsCtx = False
                if isinstance(site.att, (StarStarIcon, ArgAssignIcon)):
                    kwArgEncountered = True
                elif kwArgEncountered and not export:
                    needsCtx = True
                argBrkLvl = brkLvl + (1 if needsCtx else 0)
                argText = icon.argSaveText(argBrkLvl, site, contNeeded, export)
                if needsCtx:
                    argText.wrapCtxMacro(brkLvl, parentCtx='K', needsCont=contNeeded)
                argTextList.append(argText)
            text.concat(brkLvl, argTextList[0])
            for argText in argTextList[1:]:
                text.add(None, ', ', contNeeded)
                text.concat(brkLvl, argText, contNeeded)
        text.add(None, ')')
        if self.closed:
            text = icon.addAttrSaveText(text, self, brkLvl-1, contNeeded, export)
        if self.parent() is None and not export:
            text.wrapFragmentMacro(parentBreakLevel, 'a', needsCont=contNeeded)
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
                text[0] == '=' and len(text) <= 2 and onAttr:
            delim = text[1] if len(text) == 2 else None
            if delim is None or delim in entryicon.emptyDelimiters:
                attachedIc = entryIc.attachedIcon()
                if isinstance(attachedIc, nameicons.IdentifierIcon) and \
                        attachedIc.parent() is self:
                    return ArgAssignIcon(self.window), delim
        # Typeover for lists, tuples, and dicts is handled by hard-coded parsing because
        # closing of matching open parens/brackets/braces needs to take precedence
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        # Highlight the paren itself if not closed, but don't propagate
        if self.closed:
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight("Unmatched open paren")
        # Highlight out-of-order use of positional arguments after keywords
        kwArgEncountered = False
        for arg in (site.att for site in self.sites.argIcons if site.att is not None):
            if isinstance(arg, (StarStarIcon, ArgAssignIcon)):
                kwArgEncountered = True
                errHighlight = None
            elif kwArgEncountered:
                errHighlight = icon.ErrorHighlight(
                    "Positional argument follows keyword argument")
            else:
                errHighlight = None
            arg.highlightErrors(errHighlight)

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if idx is None or idx > 0:
            self.endParenTypeover = False
            return False
        self.endParenTypeover = True
        return True

    def typeoverSites(self, allRegions=False):
        if self.endParenTypeover:
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

    def isComprehension(self):
        # Python allows calls to contain a comprehension instead of an argument list.
        # This is a weird case that we will eventually need to support, but which we
        # currently punt by adding an embedded generator tuple upon translation from
        # AST form on read: f(a for a in b) -> f((a for a in b)).
        return False

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
        self.rect = (x, y, x + bodyWidth + icon.EMPTY_ARG_WIDTH, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
        self._drawEmptySites(toDragImage, clip)

    def doLayout(self, cprhX, cprhY, layout):
        width, height = self.bodySize
        top = cprhY - height // 2
        self.rect = (cprhX, top, cprhX + width + icon.EMPTY_ARG_WIDTH, top + height)
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
            testWidth = icon.EMPTY_ARG_WIDTH if testIconLayout is None else \
                testIconLayout.width
            layout.width = width + testWidth - 1
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def backspace(self, siteId, evt):
        if siteId == "testIcon":
            # Cursor is on first target site.  Remove icon and replace with entry
            # icon, converting both targets and iterators in to a flat list
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon, drawNew=False)
        else:
            print('if comprehension icon backspace passed bad siteId')

    def _becomeEntryIcon(self):
        win = self.window
        win.requestRedraw(self.topLevelParent().hierRect(), filterRedundantParens=True)
        entryIcon = entryicon.EntryIcon(initialString='if', window=win)
        testIcon = self.childAt('testIcon')
        if testIcon is not None:
            self.replaceChild(None, 'testIcon')
            entryIcon.appendPendingArgs([testIcon])
        # The entry icon can't simply take the place of a comprehension, because the
        # comprehension site is neither a valid cursor site nor a supported attachment
        # site for an entry icon.  Instead, it has to go on to the rightmost site of the
        # parent list's first argument.
        parentList = self.parent()
        if parentList is None:
            # A comprehension can sit on the top level as a fragment
            win.replaceTop(self, entryIcon)
        else:
            parentListSite = parentList.siteOf(self)
            prevSite = parentList.sites.prevCursorSite(parentListSite)
            parentList.replaceChild(None, parentListSite)
            rightmostIc, rightmostSite = icon.rightmostFromSite(parentList, prevSite)
            rightmostIc.replaceChild(entryIcon, rightmostSite)
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, ' if')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(max(0, cursorTextIdx - 1))
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'testIcon':
            return self._becomeEntryIcon()
        return None

    def textRepr(self):
        return "if " + icon.argTextRepr(self.sites.testIcon)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + (1 if self.parent() is not None else 2)
        if self._detectBadOrder() and not export:
            text = filefmt.SegmentedText("$%s$ " % UNASSOC_IF_MACRO_NAME)
        else:
            text = filefmt.SegmentedText("if ")
        icon.addArgSaveText(text, brkLvl, self.sites.testIcon, contNeeded, export)
        if self.parent() is None and not export:
            text.wrapFragmentMacro(parentBreakLevel+1, 'c', needsCont=False)
        return text

    def createAst(self):
        if self.sites.testIcon.att is None:
            raise icon.IconExecException(self,
                    'Missing argument to "if" in comprehension')
        return self.sites.testIcon.att.createAst()

    def highlightErrors(self, errHighlight):
        if errHighlight is None and self._detectBadOrder():
            errHighlight = icon.ErrorHighlight("'if' comprehension clause must follow "
                "'for' clause")
        icon.Icon.highlightErrors(self, errHighlight)

    def _detectBadOrder(self):
        parent = self.parent()
        if parent is None:
            return False
        for parentCprhSite in parent.sites.cprhIcons:
            if parentCprhSite.att is self:
                return True
            if isinstance(parentCprhSite.att, CprhForIcon):
                return False
        return False  # Shouldn't happen

class CprhForIcon(icon.Icon):
    def __init__(self, isAsync=False, typeover=False, window=None, location=None):
        icon.Icon.__init__(self, window)
        if typeover:
            self.typeoverIdx = 0
            self.window.watchTypeover(self)
        else:
            self.typeoverIdx = None
        self.isAsync = isAsync
        text = " async for" if isAsync else " for"
        bodyWidth = icon.getTextSize(text, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        inWidth = icon.getTextSize("in", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, inWidth)
        siteYOffset = bodyHeight // 2
        targetXOffset = bodyWidth - icon.OUTPUT_SITE_DEPTH
        self.tgtList = iconlayout.ListLayoutMgr(self, 'targets', targetXOffset,
                siteYOffset, simpleSpine=True)
        self.sites.add('cprhOut', 'cprhOut', 0, siteYOffset)
        iterX = bodyWidth-1 + self.tgtList.width-1 + inWidth-1
        self.sites.add('iterIcon', 'input', iterX, siteYOffset)
        totalWidth = iterX + icon.EMPTY_ARG_WIDTH
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            bodyWidth, bodyHeight, inWidth = self.bodySize
            img = Image.new('RGBA', (bodyWidth, bodyHeight),
             color=(0, 0, 0, 0))
            txt = " async for" if self.isAsync else " for"
            txtImg = icon.iconBoxedText(txt, icon.boldFont, color=icon.KEYWORD_COLOR)
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
            txtImg = icon.iconBoxedText("in", icon.boldFont, icon.KEYWORD_COLOR,
                typeover=self.typeoverIdx)
            img = Image.new('RGBA', (txtImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            inImgX = txtImg.width - icon.inSiteImage.width
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            inOffset = bodyWidth - 1 + self.tgtList.width - 1
            self.drawList.append(((inOffset, bodyTopY), img))
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip, hilightEmptySeries=True)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.tgtList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, cprhX, cprhY, layout):
        self.tgtList.doLayout(layout)
        bodyWidth, bodyHeight, inWidth = self.bodySize
        width = bodyWidth-1 + self.tgtList.width-1 + inWidth + icon.EMPTY_ARG_WIDTH
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
        tgtListLayouts = self.tgtList.calcLayouts(argRequired=True)
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
            iterWidth = icon.EMPTY_ARG_WIDTH if iterLayout is None else iterLayout.width
            layout.width = iterXOff + iterWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        text = "async for" if self.isAsync else "for"
        tgtText = icon.seriesTextRepr(self.sites.targets)
        iterText = icon.argTextRepr(self.sites.iterIcon)
        return text + " " + tgtText + " in " + iterText

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId is None or not iconsites.isSeriesSiteId(siteId):
            return None
        name, idx = iconsites.splitSeriesSiteId(siteId)
        if name != 'targets':
            return None
        if idx != len(self.sites.targets)-1:
            return None
        iconOnTgtSite = self.sites.targets[idx].att
        if iconOnTgtSite is entryIc:
            # If nothing but the entry icon is at the site, don't interfere with typing
            # the target (which could start with "in")
            return None
        rightmostIc, rightmostSite = icon.rightmostSite(iconOnTgtSite)
        if rightmostIc is entryIc and text == "i" and self.typeoverIdx == 0:
            return "typeover"
        return None

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, False)

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        # The backspace an becomeEntryIcon methods set up the entry icon's pending
        # arguments as a list followed by a single argument, so the most important thing
        # for this method to accomplish is to faithfully reproduce that arrangement when
        # it's detected.  Other than that, use the base class method to do the placement.
        # This could be improved for the case where the last item to place is clearly not
        # a valid target, but multi-element placement opportunities outside of reproducing
        # the original icon don't come up often enough to justify the extra work, yet.
        if len(placeList) == 0:
            return None, None
        if doPlacement:
            placeArgsCall = icon.Icon.placeArgs
        else:
            placeArgsCall = icon.Icon.canPlaceArgs
        if startSiteId == 'iterIcon':
            # Just the one site to place
            return placeArgsCall(self, placeList, startSiteId, overwriteStart)
        if startSiteId is None:
            startSiteId = 'targets_0'
        startSiteName, startIdx = iconsites.splitSeriesSiteId(startSiteId)
        if startSiteName != 'targets':
            print('ForIcon.placeArgs: bad startSiteId')
            return None, None
        if len(placeList) == 2 and not isinstance(placeList[1], (list, tuple)):
            # Can faithfully recreate placement in both targets and iterIcon
            tgts = placeList[0]
            iterIcon = placeList[1]
            idx, seriesIdx = placeArgsCall(self, [tgts], startSiteId, overwriteStart)
            if not icon.placeListAtEnd([tgts], idx, seriesIdx):
                return idx, seriesIdx
            self.replaceChild(iterIcon, 'iterIcon')
            return 1, None
        # Cannot faithfully recreate placement from the given place list.  Just let the
        # base class method put everything in targets list
        return placeArgsCall(self, placeList, startSiteId, overwriteStart)

    def setTypeover(self, idx, site=None):
        self.drawList = None  # Force redraw
        if idx is None or idx > 1:
            self.typeoverIdx = None
            return False
        self.typeoverIdx = idx
        return True

    def typeoverCursorPos(self):
        xOffset = self.sites.iterIcon.xOffset + icon.OUTPUT_SITE_DEPTH - \
            icon.TEXT_MARGIN - icon.getTextSize("in"[self.typeoverIdx:], icon.boldFont)[0]
        return xOffset, self.sites.iterIcon.yOffset

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        before = iconsites.makeSeriesSiteId('targets', len(self.sites.targets) - 1)
        retVal = before, 'iterIcon', 'in', self.typeoverIdx
        return [retVal] if allRegions else retVal

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        win = self.window
        if siteName == "targets":
            if index == 0:
                # Cursor is on first target site.  Remove icon and replace with entry
                # icon, converting both targets and iterators in to a flat list
                parent = self.parent()
                entryIcon = self._becomeEntryIcon()
                if not parent.isComprehension() and isinstance(parent, TupleIcon):
                    # If this was the last comprehension removed from a tuple icon, it
                    # needs to be converted back to a cursor paren, otherwise it will
                    # get an unwanted comma.
                    entryicon.cvtTupleToCursorParen(parent, closed=parent.closed,
                        typeover=parent.typeoverSites()[0] is not None)
                win.cursor.setToText(entryIcon, drawNew=False)
            else:
                # Cursor is on comma input
                backspaceComma(self, siteId, evt)
        elif siteId == "iterIcon":
            # Cursor is on "in", jump over it to last target
            lastTgtSite = iconsites.makeSeriesSiteId('targets',
                len(self.sites.targets) - 1)
            win.cursor.setToIconSite(*icon.rightmostFromSite(self, lastTgtSite))

    def _becomeEntryIcon(self):
        win = self.window
        win.requestRedraw(self.topLevelParent().hierRect(), filterRedundantParens=True)
        targetIcons = [s.att for s in self.sites.targets]
        iterIcon = self.sites.iterIcon.att
        text = "async for" if self.isAsync else "for"
        if len(targetIcons) <= 1 and iterIcon is None:
            # Zero or one argument, convert to entry icon (with single pending arg if
            # there was an argument)
            entryIcon = entryicon.EntryIcon(initialString=text, window=win)
            if len(targetIcons) == 1 and targetIcons[0] is not None:
                self.replaceChild(None, 'targets_0')
                entryIcon.appendPendingArgs([targetIcons[0]])
        else:
            # Multiple remaining arguments: convert to entry icon holding pending
            # arguments in the form a list for targets and an individual site for values.
            entryIcon = entryicon.EntryIcon(initialString=text, window=win)
            targetPlaceList = targetIcons[0] if len(targetIcons) == 1 else targetIcons
            if iterIcon is None:
                entryIcon.appendPendingArgs([targetIcons])
            else:
                entryIcon.appendPendingArgs([targetIcons, iterIcon])
            if iterIcon is not None:
                self.replaceChild(None, 'iterIcon')
            for arg in targetIcons:
                if arg is not None:
                    self.replaceChild(None, self.siteOf(arg))
        # The entry icon can't simply take the place of a comprehension, because a
        # comprehension site is neither a valid cursor site nor a supported attachment
        # site for an entry icon.  Instead, it has to go on to the rightmost site of the
        # parent list's first argument.
        parentList = self.parent()
        if parentList is None:
            # A comprehension can sit on the top level as a fragment
            win.replaceTop(self, entryIcon)
        else:
            parentListSite = parentList.siteOf(self)
            prevSite = parentList.sites.prevCursorSite(parentListSite)
            parentList.replaceChild(None, parentListSite)
            rightmostIc, rightmostSite = icon.rightmostFromSite(parentList, prevSite)
            rightmostIc.replaceChild(entryIcon, rightmostSite)
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            text = " async for" if self.isAsync else " for"
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, text)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(max(0, cursorTextIdx - 1))
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'targets_0':
            return self._becomeEntryIcon()
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            self.errHighlight = None
            highlightSeriesErrorsForContext(self.sites.targets, 'store')
            iterIcon = self.childAt('iterIcon')
            if iterIcon is not None:
                iterIcon.highlightErrors(None)
        else:
            icon.Icon.highlightErrors(self, errHighlight)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + (1 if self.parent() is not None else 2)
        text = filefmt.SegmentedText("async for " if self.isAsync else "for ")
        tgtText = seriesSaveTextForContext(brkLvl, self.sites.targets, contNeeded,
            export, 'store', allowTrailingComma=True, allowEmpty=False)
        text.concat(brkLvl, tgtText)
        text.add(None, " in ")
        icon.addArgSaveText(text, brkLvl, self.sites.iterIcon, contNeeded, export)
        if self.parent() is None and not export:
            text.wrapFragmentMacro(parentBreakLevel+1, 'c', needsCont=False)
        return text

    def dumpName(self):
        return "for (cprh)"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync)

    def duplicate(self, linkToOriginal=False):
        ic = CprhForIcon(isAsync=self.isAsync, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self, ifAsts):
        if self.sites.iterIcon.att is None:
            raise icon.IconExecException(self, 'Missing iteration value in comprehension')
        iterAst = self.sites.iterIcon.att.createAst()
        for target in self.sites.targets:
            if target.att is None:
                raise icon.IconExecException(self, 'Missing target in comprehension')
            if not target.att.canProcessCtx:
                raise icon.IconExecException(target.att,
                    "Not a valid target for assignment")
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
        infixicon.InfixIcon.__init__(self, ":", colonImage, False, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a dictionary constant
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            return isinstance(ic, DictIcon) and siteName == "argIcons"
        if 'output' in snapLists:
            outSites = snapLists['output']
            snapLists['output'] = []
            snapLists['conditional'] = \
                    [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
        elif not (isinstance(self.parent(), DictIcon) or self.parent() is None and
                self.sites.seqIn.att is None and self.sites.seqOut.att is None):
            icon.Icon.highlightErrors(self, icon.ErrorHighlight("Dictionary element "
                "(':') can only appear in { }"))
        else:
            icon.Icon.highlightErrors(self, None)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        needsCtx = not isinstance(self.parent(), DictIcon) and not export
        brkLvl = parentBreakLevel + (2 if needsCtx else 1)
        text = icon.argSaveText(brkLvl, self.sites.leftArg, contNeeded, export)
        text.add(None, ":")
        icon.addArgSaveText(text, brkLvl, self.sites.rightArg, contNeeded, export)
        if needsCtx:
            text.wrapCtxMacro(parentBreakLevel+1, parseCtx='d')
        return text

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
            return ic.__class__ in (CallIcon, blockicons.DefIcon, blockicons.LambdaIcon,
                blockicons.ClassDefIcon) and siteName == "argIcons"
        if 'output' in snapLists:  # ArgAssigns can end up in a sequence (via deletion)
            outSites = snapLists['output']
            snapLists['output'] = []
            snapLists['conditional'] = \
                [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        if not self._validateContext(forHighlight=True):
            icon.Icon.highlightErrors(self, icon.ErrorHighlight("Argument assignment "
                "('=') can only appear in calls, lambdas, and def and class statements"))
            return
        self.errHighlight = None
        leftArg = self.leftArg()
        if leftArg is not None:
            if isinstance(leftArg, nameicons.IdentifierIcon):
                leftArg.errHighlight = None
                attr = leftArg.sites.attrIcon.att
                if attr is not None:
                    attr.highlightErrors(icon.ErrorHighlight("Left side of "
                        "argument assignment ('=') must be unqualified name"))
            else:
                errHighlight = icon.ErrorHighlight(
                    "Left side of argument assignment ('=') must be name")
                leftArg.highlightErrors(errHighlight)
        rightArg = self.rightArg()
        if rightArg is not None:
            rightArg.highlightErrors(None)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        needsCtx = not self._validateContext() and not export
        brkLvl = parentBreakLevel + (2 if needsCtx else 1)
        text = nameicons.createNameFieldSaveText(brkLvl, self.sites.leftArg, contNeeded,
            export)
        text.add(None, "=")
        icon.addArgSaveText(text, brkLvl, self.sites.rightArg, contNeeded, export)
        if needsCtx:
            text.wrapCtxMacro(parentBreakLevel+1, parseCtx='f')
        return text

    def _validateContext(self, forHighlight=False):
        """Return True if icon is attached to a parent and parent site where it is
        syntactically legal in Python to have an argument assignment.  If forHighlight
        is True, consider free fragment valid."""
        parent = self.parent()
        if parent is None:
            return forHighlight and self.sites.seqIn.att is None and \
                   self.sites.seqOut.att is None
        siteName, _ = iconsites.splitSeriesSiteId(parent.siteOf(self))
        return isinstance(parent, (CallIcon, blockicons.DefIcon, blockicons.LambdaIcon,
            blockicons.ClassDefIcon)) and siteName == 'argIcons'

    def execute(self):
        if self.sites.leftArg.att is None:
            raise icon.IconExecException(self, "Missing argument name")
        if self.sites.rightArg.att is None:
            raise icon.IconExecException(self, "Missing argument value")
        if not isinstance(self.sites.leftArg.att, nameicons.IdentifierIcon):
            raise icon.IconExecException(self, "Argument name is not identifier")
        return self.sites.leftArg.att.name, self.sites.rightArg.att.execute()

class StarIcon(opicons.UnaryOpIcon):
    individualAllowedParents = (CallIcon, blockicons.DefIcon, ListIcon, TupleIcon)

    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, '*', window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list,
        # list, tuple, or assignment
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def matingIcon(ic, siteId):
            # Allow snapping to any series site (Python does not allow * in most contexts
            # without other elements, but it's necessary as an intermediate form for ease
            # of editing, and will be highlighted as a syntax error)
            return iconsites.isSeriesSiteId(siteId)
        if 'output' in snapLists:
            outSites = snapLists['output']
            snapLists['output'] = []
            snapLists['conditional'] = \
                    [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def doLayout(self, outSiteX, outSiteY, layout):
        # I apologize for the awful hack below to support the star in "from x import *".
        # There is not yet a mechanism for swapping icons based on snap context, so
        # instead, we have a star icon that temporarily turns off its argument site
        # (through the questionable means of directly manipulating the cursorOnly field
        # of the site object).
        if isinstance(self.parent(), nameicons.ImportFromIcon):
            self.sites.argIcon.cursorOnly = True
        elif hasattr(self.sites.argIcon, 'cursorOnly'):
            del self.sites.argIcon.cursorOnly
        return opicons.UnaryOpIcon.doLayout(self, outSiteX, outSiteY, layout)

    def calcLayouts(self):
        # suppressEmptyArgHighlight is an ugly mechanism to dynamically control empty
        # argument highlighting, made even uglier, here by doing so inside of the layout
        # calculation.  It's done here because the context in which the star icon appears
        # informs whether its argument is required or optional, and thus whether it needs
        # extra width for the highlight.  StarIcon really should not be inheriting from
        # UnaryOpIcon and should implement its own calcLayouts, doLayout and draw
        # functions.
        if isinstance(self.parent(), (blockicons.DefIcon, nameicons.ImportFromIcon)):
            self.suppressEmptyArgHighlight = True
        elif hasattr(self, 'suppressEmptyArgHighlight'):
            del self.suppressEmptyArgHighlight
        return opicons.UnaryOpIcon.calcLayouts(self)

    def createAst(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument to star")
        return ast.Starred(self.arg().createAst(), nameicons.determineCtx(self),
                lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False, ctx=None):
        # The method has an additional ctx argument because StarIcons can be used in
        # a store or del context.
        text = filefmt.SegmentedText('*')
        parent = self.parent()
        if self.sites.argIcon.att is None and not export:
            # Python only allows * with no arg in function def and lambda
            if not isinstance(parent, (blockicons.DefIcon, blockicons.LambdaIcon)):
                text.wrapCtxMacro(parentBreakLevel + 1, 'f', needsCont=contNeeded)
            return text
        needCtx = not export and parent is not None and \
            not iconsites.isSeriesSiteId(parent.siteOf(self)) and \
            not isinstance(parent, parenicon.CursorParenIcon)
        brkLvl = parentBreakLevel + (1 if needCtx else 0)
        arg = argSaveTextForContext(brkLvl, self.sites.argIcon, contNeeded, export, ctx)
        text.concat(None, arg, contNeeded)
        if needCtx:
            text.wrapCtxMacro(brkLvl, parseCtx='f', needsCont=contNeeded)
        return text

    def clipboardRepr(self, offset, iconsToCopy):
        # Parent UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            parent = self.parent()
            if parent is not None:
                parentSiteId = parent.siteOf(self)
                if iconsites.isSeriesSiteId(parentSiteId):
                    siteName, siteIdx = iconsites.splitSeriesSiteId(parentSiteId)
                    parentSiteSeries = getattr(parent.sites, siteName)
                    if len(parentSiteSeries) == 1:
                        if not isinstance(parent, self.individualAllowedParents):
                            errHighlight = icon.ErrorHighlight("Can only use starred "
                            "expression here in the context of a list")
                else:
                    errHighlight = icon.ErrorHighlight(
                        "Can't use starred expression in this context")
        self.errHighlight = errHighlight
        for ic in self.children():
            ic.highlightErrors(errHighlight)

    def dumpName(self):
        return "star"

class StarStarIcon(opicons.UnaryOpIcon):
    allowedParents = (CallIcon, blockicons.DefOrClassIcon, DictIcon)

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
        if 'output' in snapLists:
            outSites = snapLists['output']
            snapLists['output'] = []
            snapLists['conditional'] = \
                    [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText('**')
        parent = self.parent()
        needCtx = not isinstance(parent, (CallIcon, blockicons.DefIcon,
            blockicons.ClassDefIcon)) and not export
        brkLvl = parentBreakLevel + (1 if needCtx else 0)
        icon.addArgSaveText(text, brkLvl, self.sites.argIcon, contNeeded, export)
        if needCtx:
            text.wrapCtxMacro(brkLvl, parseCtx='f', needsCont=contNeeded)
        return text

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            parent = self.parent()
            if parent is None:
                if self.sites.seqIn.att is not None or self.sites.seqOut.att is not None:
                    errHighlight = icon.ErrorHighlight(
                        "** by itself is not legal as a statement")
            elif not isinstance(parent, self.allowedParents):
                errHighlight = icon.ErrorHighlight(
                    "Can't use dictionary expansion ('**') in this context")
        icon.Icon.highlightErrors(self, errHighlight)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def dumpName(self):
        return "star star"

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
    # Note that much of the code in here is now redundant with window.removeIcons.  It is
    # left here, because it works, and is purpose-built for typing, versus the great
    # Brobdingnagian splitDeletedIcons which has to handle every possible weird
    # combination of icons being removed.
    siteName, index = iconsites.splitSeriesSiteId(site)
    allArgs = ic.argIcons()
    nonEmptyArgs = [i for i in allArgs if i is not None]
    numArgs = len(nonEmptyArgs)
    win = ic.window
    win.requestRedraw(ic.topLevelParent().hierRect())
    attrIcon = ic.childAt('attrIcon') if ic.closed else None
    if site == "attrIcon":
        # On backspace from the outside right paren, reopen the list
        if isinstance(ic, TupleIcon) and len(ic.sites.argIcons) == 1 and \
                ic.sites.argIcons[0].att is None:
            # Special case of removing the right paren of an empty tuple, change it to
            # a paren icon before opening so we don't get lingering comma
            attr = ic.childAt('attrIcon')
            parenIcon = parenicon.CursorParenIcon(window=ic.window, closed=True)
            ic.replaceWith(parenIcon)
            if attr:
                ic.replaceChild(None, 'attrIcon')
                parenIcon.replaceChild(attr, 'attrIcon')
            ic = parenIcon
        entryicon.reopenParen(ic)
        return
    elif index == 0:
        # Backspace in to the open paren/bracket/brace: delete and spill the content
        # in to the surrounding context
        parent = ic.parent()
        attrPlaceFail = False
        attrDestination = None
        if attrIcon:
            if ic.isComprehension():
                rightmostCprh = ic.sites.cprhIcons[-2]
                attrDestination, attrDestSite = icon.rightmostSite(rightmostCprh.att)
                if attrDestSite != 'attrIcon' or hasattr(attrDestination.sites.attrIcon,
                        'cursorOnly'):
                    attrPlaceFail = True
            elif numArgs == 0:
                attrPlaceFail = parent is not None and not isinstance(ic, CallIcon)
                attrDestination = parent
            else:
                attrDestination, attrDestSite = icon.rightmostSite(nonEmptyArgs[-1])
                if attrDestSite != 'attrIcon' or hasattr(attrDestination.sites.attrIcon,
                        'cursorOnly'):
                    attrPlaceFail = True
        if numArgs == 0:
            # Empty list, though may still contain comprehensions and/or attributes,
            # which win.removeIcons will package into either an entry icon or (at the top
            # level outside of a sequence), just left.
            substitutions = None
            if parent is None:
                # Empty paren was the only thing left of the statement.  Remove
                if ic.prevInSeq(includeModuleAnchor=True) is not None:
                    cursorIc = ic.prevInSeq(includeModuleAnchor=True)
                    cursorSite = 'seqOut'
                elif ic.nextInSeq() is not None:
                    cursorIc = ic.nextInSeq()
                    cursorSite = 'seqIn'
                elif ic.isComprehension():
                    cursorIc = ic.childAt('cprhIcons_0')
                    substitutions = {cursorIc:None}
                    cursorSite = None  # Can only accept cursor after substitution
                elif attrIcon:
                    cursorIc = attrIcon
                    cursorSite = 'attrOut'
                else:
                    cursorIc = None
                    pos = ic.pos()
                win.removeIcons([ic], watchSubs=substitutions)
                if substitutions is not None:
                    subsIc = substitutions[cursorIc]
                    if subsIc is not None:
                        # removeIcons substituted the canonical form of a cprh icon which
                        # can accept the cursor
                        cursorIc = subsIc
                        cursorSite = 'seqIn'
                    else:
                        cursorIc = None
                        pos = ic.pos
                if cursorIc is None:
                    win.cursor.setToWindowPos(pos)
                else:
                    win.cursor.setToIconSite(cursorIc, cursorSite)
            else:
                # ic is an empty list with a parent.  removeIcons will deal with
                # attributes and comprehensions, just make sure cursor is placed well.
                parentSite = parent.siteOf(ic)
                win.cursor.setToIconSite(parent, parentSite)
                win.removeIcons([ic])
                if not parent.hasSite(parentSite):
                    # Last element of a list can disappear when icon is removed
                    parent.insertChild(None, parentSite)
                    win.cursor.setToIconSite(parent, parentSite)
                if isinstance(parent.childAt(parentSite), entryicon.EntryIcon):
                    # If removal created an entry icon, put the cursor in that
                    win.cursor.setToText(parent.childAt(parentSite))
            return
        elif numArgs == 1:
            # Just one item left in the list.  Unwrap the parens/brackets/braces
            # from around the content
            parent = ic.parent()
            content = nonEmptyArgs[0]
            ic.replaceChild(None, ic.siteOf(content))
            if ic.isComprehension():
                # The list contains comprehension clause(s).  Need to attach them to the
                # end of the argument with an entry icon, unless we can promote them to
                # the parent.
                cprhIcons = [site.att for site in ic.sites.cprhIcons]
                for _ in range(len(ic.sites.cprhIcons)):
                    ic.replaceChild(None, 'cprhIcons_0')
                if isinstance(parent, (TupleIcon, ListIcon, DictIcon)) and \
                        len(parent.sites.argIcons) == 1:
                    # Can promote comprehension to parent and safely close if open
                    parent.insertChildren(cprhIcons, 'cprhIcons_0')
                    parent.close()
                elif isinstance(parent, parenicon.CursorParenIcon):
                    # Can promote comprehension to parent, but must change it to a tuple
                    newTuple = TupleIcon(window=ic.window, closed=True)
                    parent.replaceChild(None, 'argIcon')
                    newTuple.replaceChild(ic, 'argIcons_0')
                    newTuple.insertChildren(cprhIcons, 'cprhIcons_0')
                    parent.replaceWith(newTuple)
                    parent = newTuple
                else:
                    # Can't promote to parent
                    entryIcon = entryicon.EntryIcon(window=win)
                    attIcon, attSite = icon.rightmostSite(content)
                    attIcon.replaceChild(entryIcon, attSite)
                    entryIcon.appendPendingArgs(cprhIcons)
            if attrIcon and not attrPlaceFail:
                # Place attribute on the content icon or last comprehension
                attrDestination.replaceChild(attrIcon, attrDestSite)
            elif attrIcon and not isinstance(ic, CallIcon):
                # Can't place attribute on content icon, add an entry icon, but don't
                # give it the cursor.  Note that we don't do this if ic is a callIcon
                # because we don't want to create two entry icons
                entryIcon = entryicon.EntryIcon(window=win)
                attrDestination.replaceChild(entryIcon, attrDestSite)
                entryIcon.appendPendingArgs([attrIcon])
            if parent is None:
                # List was on top level
                win.replaceTop(ic, content)
                topNode = reorderexpr.reorderArithExpr(content)
                coincSite = topNode.hasCoincidentSite()
                if coincSite:
                    curIc, curSite = iconsites.lowestCoincidentSite(topNode, coincSite)
                    win.cursor.setToIconSite(curIc, curSite)
                else:
                    win.cursor.setToIconSite(topNode, 'output')
            else:
                # List had a parent.  Remove by attaching content to parent if the parent
                # site can accept it.  If not (ic is CallIcon and attached to attribute),
                # then load the content in to the pendingArg of an entry icon
                parentSite = parent.siteOf(ic)
                if not isinstance(ic, CallIcon):
                    parent.replaceChild(content, parentSite)
                    topNode = reorderexpr.reorderArithExpr(content)
                    coincSite = topNode.hasCoincidentSite()
                    if coincSite:
                        curIc, curSite = iconsites.lowestCoincidentSite(topNode,
                            coincSite)
                        win.cursor.setToIconSite(curIc, curSite)
                    else:
                        win.cursor.setToIconSite(topNode, 'output')
                else:  # ic is on an attribute site.  Create an entry icon
                    entryIcon = entryicon.EntryIcon(window=win)
                    parent.replaceChild(entryIcon, 'attrIcon')
                    entryIcon.appendPendingArgs([content])
                    if attrPlaceFail:
                        entryIcon.appendPendingArgs([attrIcon])
                    win.cursor.setToText(entryIcon, drawNew=False)
                    return
            return
        elif numArgs > 1 and ic.parent() is None:
            # Multi-argument list on top level.  Make naked tuple and transfer all
            # arguments to it
            if isinstance(ic, TupleIcon):
                ic.removeParens()
                newTuple = ic
            else:
                newTuple = TupleIcon(window=ic.window, noParens=True)
                ic.window.replaceTop(ic, newTuple)
                args = [site.att for site in ic.sites.argIcons]
                for i in range(len(args)):
                    ic.replaceChild(None, 'argIcons_0')
                newTuple.insertChildren(args, 'argIcons', 0)
            if attrPlaceFail and not isinstance(ic, CallIcon):
                # Can't place attribute on last arg, add an entry icon, but don't
                # give it the cursor.  Note that we don't do this if ic is a callIcon
                # because we don't want to create two entry icons
                entryIcon = entryicon.EntryIcon(window=win)
                attrDestination.replaceChild(entryIcon, 'attrIcon')
                entryIcon.appendPendingArgs([attrIcon])
            elif attrDestination is not None and not attrPlaceFail:
                attrDestination.replaceChild(ic.childAt('attrIcon'), 'attrIcon')
            win.cursor.setToIconSite(newTuple, 'argIcons_0')
            return
        elif numArgs > 1 and ic.parent() is not None:
            # The list has multiple arguments and is not on the top level.  Determine
            # whether argument transfer is possible, and if so, what icon will receive
            # the remaining arguments.
            recipient, recipientSite = entryicon.findEnclosingSite(ic)
            if recipient is None or iconsites.isSeriesSiteId(recipientSite) or \
                    isinstance(recipient, parenicon.CursorParenIcon):
                # Argument transfer is doable.  Do the transfer.
                if recipient is None:
                    # We reached the top of the hierarchy without getting trapped.
                    # Add a naked tuple as parent to which to transfer the arguments
                    recipient = TupleIcon(window=ic.window, noParens=True)
                    topIc = ic.topLevelParent()
                    ic.window.replaceTop(topIc, recipient)
                    recipient.replaceChild(topIc, 'argIcons_0')
                    recipientSite = 'argIcons_0'
                elif isinstance(recipient, parenicon.CursorParenIcon):
                    # Found a cursor paren icon that can be converted to a tuple
                    newTuple = TupleIcon(window=ic.window)
                    arg = recipient.childAt('argIcon')
                    recipient.replaceChild(None, 'argIcon')
                    recipient.replaceWith(newTuple)
                    newTuple.replaceChild(arg, 'argIcons_0')
                    recipient = newTuple
                    recipientSite = 'argIcons_0'
                cursorIcon = ic.parent()
                cursorSite = cursorIcon.siteOf(ic)
                if isinstance(ic, CallIcon):
                    # If ic is a CallIcon, it's attached to an attribute site, so we need
                    # to create an entry icon to adapt the first element of the list
                    # (which is an input site).  The code below is a bit of a hack.
                    # Rather than complicating the already complex code for splitting and
                    # reordering after paren removal, we temporarily rearrange the icons
                    # representing the function call from the root of its attribute chain
                    # in to a tuple icon that will yield the correct result when removed
                    # by the code that handles the general case.  For example:
                    #   a * b.c(d, e) * f   ->   a * (b.c|d, e) * f
                    callRoot = icon.findAttrOutputSite(ic)
                    newTuple = TupleIcon(window=ic.window)
                    entryIcon = entryicon.EntryIcon(window=win)
                    firstArg = ic.childAt('argIcons_0')
                    ic.parent().replaceChild(entryIcon, 'attrIcon')
                    ic.replaceChild(None, 'argIcons_0')
                    entryIcon.appendPendingArgs([firstArg])
                    rootParent = callRoot.parent()  # recipient is above so can't be None
                    rootParentSite = rootParent.siteOf(callRoot)
                    rootParent.replaceChild(newTuple, rootParentSite)
                    newTuple.replaceChild(callRoot, 'argIcons_0')
                    for i in range(len(ic.sites.argIcons)):
                        arg = ic.childAt('argIcons_0')
                        ic.replaceChild(None, 'argIcons_0')
                        newTuple.insertChild(arg, 'argIcons', i+1)
                    attrIcon = ic.childAt('attrIcon')
                    if attrIcon is not None:
                        ic.replaceChild(None, 'attrIcon')
                        newTuple.replaceChild(attrIcon, 'attrIcon')
                    print('reorder call to tuple...')
                    ic.window._dumpCb()
                    ic = newTuple
                    cursorIcon = entryIcon
                    cursorSite = None
                if recipient is not ic.parent():
                    # The list is part of an arithmetic expression that must be split
                    # around it.  The splitExprAtIcon function will return a left
                    # side and a right side with firstArg integrated in to the left
                    # expression and lastArg integrated into the right expression.  We
                    # then replace the first and last elements of the list with those
                    # results, replace the expression in recipient with ic itself, and
                    # then reorder the left and right expressions.  This leaves recipient
                    # directly holding ic, whose first and last elements now incorporate
                    # the left and right portions of the expression that formerly held ic.
                    firstArg = ic.childAt('argIcons_0')
                    lastArgSite = ic.sites.argIcons[-1].name
                    lastArg = ic.sites.argIcons[-1].att
                    left, right = entryicon.splitExprAtIcon(ic, recipient, firstArg,
                        lastArg)
                    ic.replaceChild(left, 'argIcons_0')
                    ic.replaceChild(right, lastArgSite)
                    recipient.replaceChild(ic, recipientSite)
                    reorderexpr.reorderArithExpr(left)
                    reorderexpr.reorderArithExpr(right)
                    cursorIcon = recipient
                    cursorSite = recipientSite
                args = [site.att for site in ic.sites.argIcons]
                for i in range(len(args)):
                    ic.replaceChild(None, 'argIcons_0')
                recipient.replaceChild(None, recipientSite)
                recipient.insertChildren(args,
                    *iconsites.splitSeriesSiteId(recipientSite))
                if attrPlaceFail:
                    placeholderEntryIcon = entryicon.EntryIcon(window=win)
                    attrDestination.replaceChild(placeholderEntryIcon, 'attrIcon')
                    placeholderEntryIcon.appendPendingArgs([attrIcon])
                else:
                    if attrDestination is not None:
                        attrDestination.replaceChild(ic.childAt('attrIcon'), 'attrIcon')
                if cursorSite is None and isinstance(cursorIcon, entryicon.EntryIcon):
                    win.cursor.setToText(entryIcon, drawNew=False)
                else:
                    win.cursor.setToIconSite(cursorIcon, cursorSite)
                return
        # Argument transfer was not possible, create an entry icon and stuff everything
        # into its pending argument list.
        entryIcon = entryicon.EntryIcon(window=win)
        argList = ic.argIcons()
        for _ in range(len(argList)):
            ic.replaceChild(None, 'argIcons_0')
        entryIcon.appendPendingArgs([argList])
        attrIcon = ic.childAt('attrIcon')
        if attrIcon is not None:
            ic.replaceChild(None, 'attrIcon')
            if attrPlaceFail or attrDestination is None:
                entryIcon.appendPendingArgs([attrIcon])
            else:
                attrDestination.replaceChild(attrIcon, 'attrIcon')
        parent = ic.parent()
        parentSite = parent.siteOf(ic)
        parent.replaceChild(entryIcon, parentSite)
        win.cursor.setToText(entryIcon, drawNew=False)
        return
    else:
        # Cursor is on comma input.  Use the backspaceComma function common to all
        # sequences, except: 1) Backspacing the last comma out of a single-element tuple,
        # and 2) If this is a naked tuple, remove if no longer needed
        if isinstance(ic, TupleIcon) and len(ic.sites.argIcons) == 2 and \
                site == 'argIcons_1' and ic.sites.argIcons[1].att is  None and \
                ic.sites.argIcons[0].att is not None and not ic.noParens:
            # Backspace of last comma of single (populated) element tuple: change to paren
            redrawRegion = comn.AccumRects(ic.topLevelParent().hierRect())
            arg = ic.childAt("argIcons_0")
            attr = ic.childAt("attrIcon")
            ic.replaceChild(None, 'argIcons_0')
            newParen = parenicon.CursorParenIcon(window=win, closed=True)
            newParen.replaceChild(arg, 'argIcon')
            ic.replaceWith(newParen)
            if attr:
                newParen.replaceChild(attr, 'attrIcon')
            win.cursor.setToIconSite(*icon.rightmostSite(arg))
            win.requestRedraw(None, filterRedundantParens=True)
            return
        backspaceComma(ic, site, evt)
        if isinstance(ic, TupleIcon) and ic.noParens and len(ic.sites.argIcons) <= 1:
            # If this is a naked tuple down to 0 or 1 arguments, get rid of it
            redrawRegion = comn.AccumRects(ic.topLevelParent().hierRect())
            argIcon = ic.sites.argIcons[0].att
            parent = ic.parent()
            if parent is None:
                if argIcon is None:
                    # This (the 0-argument case) normally can't happen since a single
                    # backspace can only take out one argument and naked tuple with a
                    # single argument should not be allowed to exist, however, the
                    # backspace hack for assign icons can, in fact, set this up.
                    print("Naked tuple removed in backspace of single element")
                    nextIc = ic.nextInSeq()
                    prevIc = ic.prevInSeq(includeModuleAnchor=True)
                    win.removeIcons([ic])
                    if prevIc is not None:
                        win.cursor.setToIconSite(prevIc, 'seqOut')
                    elif nextIc is not None:
                        win.cursor.setToIconSite(nextIc, 'seqIn')
                    else:
                        win.cursor.setToWindowPos(ic.pos())
                else:
                    cursorOnIcon = win.cursor.type == "icon" and win.cursor.icon is ic
                    ic.replaceChild(None, 'argIcons_0')
                    win.replaceTop(ic, argIcon)
                    if cursorOnIcon:
                        win.cursor.setToIconSite(argIcon, 'output')
            else:
                parentSite = parent.siteOf(ic)
                cursorOnIcon = win.cursor.type == "icon" and win.cursor.icon is ic
                parent.replaceChild(argIcon, parentSite)
                if cursorOnIcon:
                    win.cursor.setToIconSite(parent, parentSite)

def backspaceComma(ic, cursorSite, evt, joinOccupied=True):
    """Backspace when cursor is at the comma site of an icon with a sequence.  Deletes
    empty site left or right of the comma, or if both sites are occupied and joinOccupied
    is True, join them with an entry icon."""
    win = ic.window
    siteName, index = iconsites.splitSeriesSiteId(cursorSite)
    prevSite = iconsites.makeSeriesSiteId(siteName, index - 1)
    childAtCursor = ic.childAt(cursorSite)
    childAtPrevSite = ic.childAt(prevSite)
    topIcon = ic.topLevelParent()
    redrawRect = topIcon.hierRect()
    if not childAtPrevSite:
        # Previous comma clause is empty, remove the site
        ic.removeEmptySeriesSite(prevSite)
        win.cursor.setToIconSite(ic, prevSite)
        win.requestRedraw(redrawRect)
        return True
    rightmostIcon, rightmostSite = icon.rightmostSite(childAtPrevSite)
    if not childAtCursor:
        # Comma clause with cursor is empty, remove the site
        ic.removeEmptySeriesSite(cursorSite)
        win.cursor.setToIconSite(rightmostIcon, rightmostSite)
        win.requestRedraw(redrawRect)
        return True
    # Neither the cursor site nor the prior site is empty.  Does either clause have an
    # adjacent empty site?
    if rightmostIcon.typeOf(rightmostSite) != 'input' or \
            rightmostIcon.childAt(rightmostSite):
        leftEmptyIc, leftEmptySite = None, None
    else:
        leftEmptyIc, leftEmptySite = rightmostIcon, rightmostSite
    lowestIc, lowestSite = iconsites.lowestCoincidentSite(ic, cursorSite)
    if lowestIc.childAt(lowestSite):
        rightEmptyIc, rightEmptySite = None, None
    else:
        rightEmptyIc, rightEmptySite = lowestIc, lowestSite
    if leftEmptyIc and not rightEmptyIc:
        # Empty site left of cursor, merge right side in to that and reorder arithmetic
        ic.replaceChild(None, cursorSite)
        leftEmptyIc.replaceChild(childAtCursor, leftEmptySite)
        reorderexpr.reorderArithExpr(leftEmptyIc)
        win.cursor.setToIconSite(leftEmptyIc, leftEmptySite)
        win.requestRedraw(redrawRect, filterRedundantParens=True)
        return True
    if rightEmptyIc and not leftEmptyIc:
        # Empty site right of cursor, merge left side in to that and reorder arithmetic
        ic.replaceChild(None, prevSite)
        rightEmptyIc.replaceChild(childAtPrevSite, rightEmptySite)
        reorderexpr.reorderArithExpr(rightEmptyIc)
        win.cursor.setToIconSite(rightmostIcon, rightmostSite)
        win.requestRedraw(redrawRect, filterRedundantParens=True)
        win.updateTypeoverStates()
        return True
    # Left and right sites both have content and can only be merged by inserting an entry
    # icon.  Stitch together the two sites with an entry icon in the middle
    if not joinOccupied:
        return False
    win.requestRedraw(redrawRect, filterRedundantParens=True)
    entryIcon = entryicon.EntryIcon(window=win)
    if leftEmptyIc and rightEmptyIc:
        # There are empty sites both left and right.  Put the right clause into the empty
        # site of the left clause and put the entry icon into the right empty site.
        ic.replaceChild(None, cursorSite)
        rightEmptyIc.replaceChild(entryIcon, rightEmptySite)
        leftEmptyIc.replaceChild(childAtCursor, leftEmptySite)
        reorderexpr.reorderArithExpr(leftEmptyIc)
    else:
        ic.replaceChild(None, cursorSite)
        rightmostIcon.replaceChild(entryIcon, rightmostSite)
        entryIcon.appendPendingArgs([childAtCursor])
    win.cursor.setToText(entryIcon, drawNew=False)
    return True

def highlightSeriesErrorsForContext(series, ctx):
    if isinstance(series[0].att, StarIcon) and ctx == 'store' and len(series) <= 1:
        # * (star) is allowed in a series of store targets, but not by itself, and only
        # a single starred element is allowed.  Note that this works in conjunction with
        # highlightErrorsForContext, and the highlightErrors method of the star icon.
        errHighlight = icon.ErrorHighlight("Starred expression not allowed in store to "
            "single-element target")
        ic = series[0].att
        if ic is not None:
            ic.highlightErrors(errHighlight)
        return
    starEncountered = False
    for site in series:
        ic = site.att
        if ic is not None and isinstance(ic, StarIcon) and ctx == 'store':
            if starEncountered:
                ic.highlightErrors(icon.ErrorHighlight("Starred expression can only "
                    "appear once in a series of assignment targets"))
                continue
            starEncountered = True
        highlightErrorsForContext(site, ctx)

def highlightErrorsForContext(site, ctx, restrictToSingle=False):
    ic = site.att
    if ic is None:
        return
    if ctx is None:
        ic.highlightErrors(None)
        return
    attr = None
    if isinstance(ic, nameicons.IdentifierIcon):
        attr = ic.sites.attrIcon.att
        ic.errHighlight = None
    elif isinstance(ic, StarIcon):
        if ctx == "del":
            ic.highlightErrors(icon.ErrorHighlight(
                "Starred expression not allowed in del context"))
        elif restrictToSingle:
            ic.highlightErrors(icon.ErrorHighlight("Starred expression can only be used "
                "as an assignment target as an element of a series"))
        else:
            ic.errHighlight = None
            highlightErrorsForContext(ic.sites.argIcon, ctx, restrictToSingle)
    elif isinstance(ic, (TupleIcon, ListIcon)):
        if ic.isComprehension():
            ic.highlightErrors(icon.ErrorHighlight(
                "Comprehension not allowed in %s context" % ctx))
        elif ctx == 'store' and len(ic.sites.argIcons) == 1 and \
                ic.sites.argIcons[0].att is None:
            ic.highlightErrors(icon.ErrorHighlight(
                "Cannot store to empty list or tuple"))
        elif restrictToSingle:
            # restrictToSingle is only used in the "store" context, so it's not worth
            # adding a case for "del".
            ic.highlightErrors(icon.ErrorHighlight("Cannot assign to a literal"))
        else:
            ic.errHighlight = None
            highlightSeriesErrorsForContext(ic.sites.argIcons, ctx)
            if ic.closed:
                attr = ic.sites.attrIcon.att
    elif isinstance(ic, parenicon.CursorParenIcon):
        ic.errHighlight = None
        if ic.closed:
            attr = ic.sites.attrIcon.att
        argCtx = ctx if attr is None else None
        highlightErrorsForContext(ic.sites.argIcon, argCtx, restrictToSingle)
    else:
        ic.highlightErrors(icon.ErrorHighlight("Not a valid target for %s" % ctx))
    while attr is not None:
        nextAttr = attr.sites.attrIcon.att if attr.hasSite('attrIcon')  else None
        if isinstance(attr, CallIcon):
            if nextAttr is None:
                attr.highlightErrors(icon.ErrorHighlight(
                    "Function call cannot be used in a %s context" % ctx))
                break
            attr.highlightErrors(None)
        elif isinstance(attr, (subscripticon.SubscriptIcon, entryicon.EntryIcon)):
            attr.highlightErrors(None)
        attr.errHighlight = None
        attr = nextAttr

def seriesSaveTextForContext(breakLevel, seriesSite, cont, export, ctx,
        allowTrailingComma=False, allowEmpty=True):
    """Store/del context-aware version of icon.seriesSaveText which wraps $Ctx$ macros
    around any element that is not valid for the context."""
    if len(seriesSite) == 0 or len(seriesSite) == 1 and seriesSite[0].att is None:
        return filefmt.SegmentedText(None if allowEmpty or export else '$Empty$')
    # Multiple star targets are illegal Python syntax, and code, here, originally
    # surrounded them with $Ctx$ macros, but since the Python AST parser accepts them
    # them, we now skip the macro and save them as-is.
    args = [argSaveTextForContext(breakLevel, site, cont, export, ctx) for site in
        seriesSite]
    combinedText = args[0]
    if allowTrailingComma and len(args) == 2 and seriesSite[1].att is None:
        combinedText.add(None, ', ', cont)
    else:
        for arg in args[1:]:
            combinedText.add(None, ', ', cont)
            combinedText.concat(breakLevel, arg, cont)
    return combinedText

def argSaveTextForContext(breakLevel, site, cont, export, ctx):
    """Create SegmentedText list of an individual argument for store (ctx == 'store' or
    delete (ctx == 'del') context."""
    ic = site.att
    if ic is None:
        return filefmt.SegmentedText(None if export else "$Empty$")
    if ctx is None:
        return ic.createSaveText(breakLevel, cont, export)
    attr = ic.sites.attrIcon.att if hasattr(ic.sites, 'attrIcon') else None
    # If the icon has an attribute, we need to judge it by what's at the end of the
    # attribute chain: if it's a function, it needs a context macro, but ordinary
    # attributes and subscripts are allowable in both store and del contexts
    if attr is not None or export:
        if export or attrValidForContext(ic, ctx):
            text = ic.createSaveText(breakLevel, cont, export)
        else:
            text = ic.createSaveText(breakLevel + 1, cont, export)
            text.wrapCtxMacro(breakLevel, needsCont=cont)
        return text
    # Icons that are allowed in a store or delete context (tuples, lists, cursorParens)
    # have an additional ctx argument to their createSaveText method, and propagate the
    # context information down to their own arguments as needed.
    if isinstance(ic, (nameicons.IdentifierIcon, TupleIcon, ListIcon,
            parenicon.CursorParenIcon, StarIcon)):
        return ic.createSaveText(breakLevel, cont, export, ctx)
    # If we reach here, we have an icon that is not compatible with the given context
    # and need to wrap a Ctx macro
    text = ic.createSaveText(breakLevel + 1, cont, export)
    text.wrapCtxMacro(breakLevel, needsCont=cont)
    return text

def attrValidForContext(ic, ctx):
    """Given an icon (ic) that is valid for store or del context, check and return True
    if its attribute(s) are also allowed for the context (for both store and del
    attributes, the only non-allowed condition is when the attribute chain ends in a
    function call)."""
    attr = ic.sites.attrIcon.att
    if ctx is None or attr is None:
        return True
    while attr is not None:
        nextAttr = attr.sites.attrIcon.att if attr.hasSite('attrIcon') else None
        if isinstance(attr, CallIcon) and nextAttr is None:
            return False
        attr = nextAttr
    return True

def canPlaceArgsInclCprh(placeList, onIcon, onSite, overwriteStart=False):
    """Determine which arguments from placeList would be placed if the placeArgsInclCprh
    were called on the same arguments (see placeArgsInclCprh for description)."""
    return _placeArgsInclCprhOnParen(placeList, onIcon, onSite, overwriteStart, False)
    if not _needToCvtParenToPlace(placeList, onIcon, onSite, overwriteStart):
        return

def placeArgsInclCprh(placeList, onIcon, onSite, overwriteStart=False):
    """Comprehension sites can't hold a cursor or an entry icon (a design decision due to
    their being coincident with other sites).  Therefore the coincident site becomes a
    proxy site for insertion of comprehension clauses.  This call is the equivalent of
    onIcon.placeArgs which takes this in to account and can place arguments both on
    onIcon and, if it is also a proxy site for a comprehension, on the associated
    comprehension.  placeArgsInclCprh also differs from a placeArgs method in that if
    it is asked to place arguments on a cursor paren icon, and those arguments happen to
    be or contain (via an embedded placeholder entry icon) one or more comprehension
    clauses, it will replace onIcon with a tuple icon before placement.  Because it can
    do this substitution, its return value also differs from a placeArgs method in that
    it will return None if no substitution was done, or the substituted icon if it was.
    Another difference to note is that overwriteStart does not apply to the comprehension
    site, as the only current use case is for replacing an entry icon which can only be
    on the proxy site.  Also note that it can (and will) place icons on BOTH sites if
    placeList contains a compatible sequence of icons."""
    return _placeArgsInclCprhOnParen(placeList, onIcon, onSite, overwriteStart, True)

def _needToCvtParenToPlace(placeList, onIcon, onSite, overwriteStart):
    cprhIc, cprhIdx = isProxyForCprhSite(onIcon, onSite, overwriteStart, True)
    if not isinstance(cprhIc, parenicon.CursorParenIcon):
        return None
    # onIcon is on a proxy site for a comprehension on cprhIc and cprhIc is a cursor
    # paren icon
    if isinstance(placeList[0], (CprhForIcon, CprhIfIcon)):
        return cprhIc
    if canPlaceCprhArgsFromEntry(None, placeList, 'argIcons_0', overwriteStart):
        return cprhIc
    # placeList does not start with either a comprehension clause or something compatible
    # with a tuple icon with an attached comprehension clause
    return None

def _placeArgsInclCprhOnParen(placeList, onIcon, onSite, overwriteStart, doPlacement):
    """This is the common part of placeArgsInclCprh and canPlaceArgsInclCprh, or rather,
    a wrapper around it that if comprehensions could be placed if the associated icon
    were a tuple, but is a paren, will do the substitution and then place.  Note that
    while the return value for canPlaceArgsInclCprh is the same as a canPlaceArgs icon
    method, the return value for placeArgsInclCprh is different because it needs to
    report if it has done an icon substitution and return the substituted icon."""
    # Determine if onSite is a proxy site for a comprehension and if so, which one
    cprhIc, cprhIdx = isProxyForCprhSite(onIcon, onSite, overwriteStart, True)
    if not isinstance(cprhIc, parenicon.CursorParenIcon):
        # Just place on the requested icon if onIcon and onSite could not be interpreted
        # as a comprehension site if onIcon were converted to a tuple
        idx, seriesIdx = _placeArgsInclCprhCommon(placeList, onIcon, onSite,
            overwriteStart, doPlacement)
        return None if doPlacement else (idx, seriesIdx)
    # cprhIc is a cursor paren icon, so determine if we need to convert it to a tuple
    # before placing
    idx, seriesIdx = _placeArgsInclCprhCommon(placeList, onIcon, onSite,
        overwriteStart, False)
    canPlaceAll = icon.placeListAtEnd(placeList, idx, seriesIdx)
    if canPlaceAll and not doPlacement:
        # All icons can be placed without converting the cursor paren.  If we're not
        # actually placing, the answer from _placeArgsInclCprhCommon will be correct
        # even if we succeed in extracting comprehension clauses from the placed content.
        return idx, seriesIdx
    preferTuple = canPlaceCprhArgsFromEntry(None, placeList, 'argIcons_0', overwriteStart)
    if not preferTuple and not isinstance(placeList[0], (CprhForIcon, CprhIfIcon)):
        # If placeList does not start with either a comprehension clause or something
        # compatible with a tuple icon with an attached comprehension clause, don't
        # convert to tuple
        if doPlacement:
            _placeArgsInclCprhCommon(placeList, onIcon, onSite, overwriteStart, True)
            return None
        else:
            return idx, seriesIdx
    # We need to convert to a tuple, but should not convert unless doPlacement is True
    if not doPlacement:
        if preferTuple:
            return 0, None
        nCprh = len([ic for ic in placeList if isinstance(ic, (CprhIfIcon, CprhForIcon))])
        return nCprh-1, None
    tupleIcon = entryicon.cvtCursorParenToTuple(cprhIc, closed=True, typeover=False)
    _placeArgsInclCprhCommon(placeList, tupleIcon, 'argIcons_0', overwriteStart, True)
    return tupleIcon

def _placeArgsInclCprhCommon(placeList, onIcon, onSite, overwriteStart, doPlacement):
    """Lower-level common component to placeArgsInclCprh and canPlaceArgsInclCprh, that
    computes and does placement and handles comprehension proxy sites, but does not do
    substitution of paren icons with tuple icons.  Return values are the same as for
    icon placeArgs and canPlaceArgs methods."""
    # Place (if doPlacement is True) or determine placement for  whatever can be placed
    # directly on onIcon (including actual comprehension sites).
    if doPlacement:
        idx, seriesIdx = onIcon.placeArgs(placeList, onSite,
            overwriteStart=overwriteStart)
    else:
        idx, seriesIdx = onIcon.canPlaceArgs(placeList, onSite,
            overwriteStart=overwriteStart)
    if icon.placeListAtEnd(placeList, idx, seriesIdx):
        return idx, seriesIdx  # All icons placed
    if seriesIdx is not None and seriesIdx != len(placeList[idx])-1:
        return idx, seriesIdx  # We won't find comprehensions in the middle of a series
    endIdx = -1 if idx is None else idx
    if not isinstance(placeList[endIdx + 1], (CprhIfIcon, CprhForIcon)):
        return idx, seriesIdx  # Next placeList item is not a comprehension
    # Determine if onSite is a proxy site for a comprehension and if so, which one
    parentList, cprhIdx = isProxyForCprhSite(onIcon, onSite, overwriteStart, False)
    if parentList is None:
        return idx, seriesIdx
    # Place (or determine placement for) comprehensions at the (new) start of placeList
    # (since it's a list, we can absorb as many as there are).  We can't place any other
    # icon types, as nothing follows a comprehension clause list and we can only prepend.
    while endIdx < len(placeList) - 1:
        cprhIc = placeList[endIdx+1]
        if not isinstance(cprhIc, (CprhIfIcon, CprhForIcon)):
            return endIdx, None
        endIdx += 1
        if doPlacement:
            parentList.insertChild(cprhIc, 'cprhIcons', cprhIdx)
        cprhIdx += 1
    return endIdx, None

def canPlaceCprhArgsFromEntry(ic, placeList, siteName, overwriteStart):
    """Return True if the first element of placeList is compatible with site, siteName,
    of a ListTypeIcon ic, and includes an entry icon touching its right edge whose
    pending argument list contains only comprehension clauses.  ic can be passed as None
    to represent an empty (not yet created) ListType icon."""
    if len(placeList) == 0 or isinstance(placeList[0], (list, tuple)):
        return False
    firstEntry = placeList[0]
    if siteName == 'argIcons_0':
        if not firstEntry.hasSite('output'):
            return False
        if ic is not None:
            if not overwriteStart and ic.childAt('argIcons_0'):
                return False
            argLen = len(ic.sites.argIcons)
            if isinstance(ic, TupleIcon):
                if argLen > 2 or argLen > 1 and ic.childAt('argIcons_1'):
                    return False
            else:
                if argLen > 1:
                    return False
    elif siteName == 'cprhIcons':
        if not (isinstance(firstEntry, entryicon.EntryIcon) or
                not firstEntry.hasSite('cprhOut')):
            return False
    else:
        return False
    rightmostIc, rightmostSite = icon.rightmostSite(firstEntry)
    for parent in rightmostIc.parentage(includeSelf=True):
        if isinstance(parent, entryicon.EntryIcon) and parent.text == '':
            pendingArgs = parent.listPendingArgs()
            if len(pendingArgs) == 0:
                return False
            for arg in pendingArgs:
                if not isinstance(arg, (CprhForIcon, CprhIfIcon)):
                    return False
            return True
        if parent is firstEntry:
            return False
    return False

def promoteCprhArgsFromEntry(placeList, removeEntryIc):
    """Return a modified version of placeList with entry icon containing comprehension
    clauses removed and the contained clauses promoted to the top level of the list.
    Note that this assumes that the place list has been validated for compatibility by
    canPlaceCprhArgsFromEntry, and should not be called if that returned False."""
    firstEntry = placeList[0]
    rightmostIc, rightmostSite = icon.rightmostSite(firstEntry)
    for parent in rightmostIc.parentage(includeSelf=True):
        if isinstance(parent, entryicon.EntryIcon) and parent.text == '':
            pendingArgs = parent.listPendingArgs()
            cprhArgs = [a for a in pendingArgs if isinstance(a, (CprhForIcon,
            CprhIfIcon))]
            if len(cprhArgs) == len(pendingArgs) and len(cprhArgs) > 0:
                newPlaceList = [placeList[0]] + cprhArgs + placeList[1:]
                if removeEntryIc:
                    parent.popPendingArgs("all")
                    parent.attachedIcon().replaceChild(None,  parent.attachedSite())
                return newPlaceList
        if parent is firstEntry:
            break
    return placeList

def isProxyForCprhSite(ic, site, allowNonEmpty, includeParenIcon):
    """Determine if site (site) on icon (ic) either is a comprehension site, or can be
    a proxy site for a comprehension site, and if so, whether there's an icon in the way
    (if allowNonEmpty is False).  If the site is acceptable, return the icon and site.
    If not, return None, None.  If includeParenIcon is True, the function will also
    recognize paren icons that can be converted to comprehension icons."""
    # If site is an actual comprehension site, return ic and site as-is
    if isinstance(ic, (ListIcon, DictIcon, TupleIcon)) and site[:9] == 'cprhIcons':
        _, idx = iconsites.splitSeriesSiteId(site)
        return ic, idx
    # Search up the icon hierarchy for an icon type that can hold a comprehension
    for cprhIc in ic.parentage(includeSelf=True):
        if isinstance(cprhIc, (ListIcon, DictIcon)) or \
                isinstance(cprhIc, TupleIcon) and not cprhIc.noParens or \
                includeParenIcon and isinstance(cprhIc, parenicon.CursorParenIcon):
            break
    else:
        return None, None
    # Find the site on the comprehension-friendly icon that holds ic and site
    if cprhIc is ic:
        listSite = site
    else:
        listSite = cprhIc.siteOf(ic, recursive=True)
    # Bail out if the site can't either hold a comprehension clause or be a proxy for
    # such a site.  If the site is acceptable, figure out the index of the cprh site for
    # which it is a proxy.
    if isinstance(cprhIc, parenicon.CursorParenIcon):
        if listSite == 'argIcon':
            cprhIdx = 0
        else:
            return None, None
    else:
        if not iconsites.isSeriesSiteId(listSite):
            return None, None
        isTupleIcon = isinstance(cprhIc, TupleIcon)
        nArgs = len(cprhIc.sites.argIcons)
        if nArgs > 1 and not (isTupleIcon and nArgs == 2 and
                cprhIc.sites.argIcons[1].att is None):
            return None, None
        listSeriesName, listSiteIdx = iconsites.splitSeriesSiteId(listSite)
        if listSeriesName in ('argIcons', 'argIcon'):
            cprhIdx = 0
        elif listSeriesName == 'cprhIcons':
            cprhIdx = listSiteIdx + 1
        else:
            return None, None
    # Find the rightmost icon on the list site that holds the candidate proxy site,
    # and if that does not directly match the candidate, check if there's something
    # attached to the site that could be removed if allowNonEmpty is True.
    proxyIc, proxySite = icon.rightmostFromSite(cprhIc, listSite)
    if proxyIc != ic or proxySite != site:
        if not allowNonEmpty or ic.childAt(site) is None:
            return None, None
        rightmostIc, rightmostSite = icon.rightmostFromSite(ic, site)
        if rightmostIc != proxyIc or rightmostSite != proxySite:
            return None, None
    return cprhIc, cprhIdx

def proxyForCprhSite(ic, site):
    """Given a comprehension site (ic, site), find the icon and site that should be used
    in its place to hold a cursor or entry icon."""
    if not isinstance(ic, (ListIcon, DictIcon, TupleIcon)):
        return ic, site
    seriesName, seriesIdx = iconsites.splitSeriesSiteId(site)
    if seriesName != 'cprhIcons':
        return ic, site
    if seriesIdx == 0:
        return icon.rightmostFromSite(ic, 'argIcons_0')
    return icon.rightmostFromSite(ic, iconsites.makeSeriesSiteId(seriesName, seriesIdx-1))

def  subsCanonicalInterchangeIcon(ic):
    """When an icon with an equivalent text representation but unique form within its
    normal context, is dragged or cut/copied out of that context, return an equivalent
    icon of its canonical (non-contextual) form.  For example, if an if clause is dragged
    out of a comprehension this call will return an equivalent if statement.  Currently,
    this only applies to comprehension components.  It was originally intended to apply
    to argument assignment as well, but that led to complex ambiguities in the resulting
    icon structure when an argument assignment became exposed outside of a call.  It will
    probably eventually apply to slices versus dictionary elements (once slices are
    separated from subscripts)."""
    subsIc = None
    if isinstance(ic, CprhForIcon):
        subsIc = blockicons.ForIcon(isAsync=ic.isAsync, window=ic.window)
        tgtIcons = [tgtSite.att for tgtSite in ic.sites.targets]
        for tgtSite in ic.sites.targets:
            ic.replaceChild(None, tgtSite.name)
        subsIc.insertChildren(tgtIcons, 'targets', 0)
        iterIcon = ic.childAt('iterIcon')
        ic.replaceChild(None, 'iterIcon')
        subsIc.replaceChild(iterIcon, 'iterIcons_0')
    elif isinstance(ic, CprhIfIcon):
        subsIc = blockicons.IfIcon(window=ic.window)
        condIcon = ic.childAt('testIcon')
        ic.replaceChild(None, 'testIcon')
        subsIc.replaceChild(condIcon, 'condIcon')
    if subsIc is not None:
        filefmt.moveIconToPos(subsIc, ic.pos())
        if ic.isSelected():
            subsIc.select(True)
    return subsIc

def composeAttrAstIf(ic, icAst, skipAttr):
    """Wrapper for icon.composeAttrAst, giving it a disable flag (skipAttr), to simplify
    createAst methods for mutable icons which may need to suppress execution of
    attributes for updating mutables alone."""
    if skipAttr:
        return icAst
    return icon.composeAttrAst(ic, icAst)

def createListIconFromAst(astNode, window):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    topIcon = ListIcon(window, closed=closed)
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.List, createListIconFromAst)

def createTupleIconFromAst(astNode, window):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    if len(astNode.elts) == 0 and not closed:
        # While parenicon writes empty open parens as $:o$($Empty$)$)$,  $:o$() is also
        # acceptable, which Python parses as an empty tuple, in which case, convert
        return parenicon.CursorParenIcon(closed=False, window=window)
    topIcon = TupleIcon(window, closed=closed, noParens=hasattr(astNode, 'isNakedTuple'))
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Tuple, createTupleIconFromAst)

def createDictIconFromAst(astNode, window):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    topIcon = DictIcon(window, closed=closed)
    argIcons = []
    fieldAnn = astNode.fieldMacroAnnotations if hasattr(astNode,
        'fieldMacroAnnotations') else None
    for i, key in enumerate(astNode.keys):
        value = icon.createFromAst(astNode.values[i], window)
        if fieldAnn is not None and fieldAnn[i] is not None:
            macroName, macroArgs, iconCreateFn, argAsts = fieldAnn[i]
        else:
            macroName = macroArgs = argAsts = None
        if macroName == 'Ctx' and macroArgs is not None and 'D' in macroArgs:
            # This is a Ctx macro with D (masquerade as dict elem) arg, use macro arg
            argIcons.append(icon.createFromAst(fieldAnn[i][3][0], window))
        elif macroName == 'Empty' and macroArgs is not None and 'D' in macroArgs:
            # This is an Empty macro with D (masquerade as dict elem) arg
            argIcons.append(None)
        elif key is None:
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

def createDictElemFromFakeAst(astNode, window):
    # The filefmt module provides its own "fake" ast node to represent a free (on the
    # top level, or inside a Ctx or Entry macro) dictionary element.  Translate to icon.
    dictElem = DictElemIcon(window)
    key = icon.createFromAst(astNode.key, window)
    dictElem.replaceChild(key, "leftArg")
    value = icon.createFromAst(astNode.value, window)
    dictElem.replaceChild(value, "rightArg")
    return dictElem
icon.registerIconCreateFn(filefmt.DictElemFakeAst, createDictElemFromFakeAst)

def createSetIconFromAst(astNode, window):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    topIcon = DictIcon(window, closed=closed)
    childIcons = [icon.createFromAst(e, window) for e in astNode.elts]
    topIcon.insertChildren(childIcons, "argIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.Set, createSetIconFromAst)

def createCallIconFromAst(astNode, window):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    callIcon = CallIcon(window, closed=closed)
    argIcons = [icon.createFromAst(e, window) for e in astNode.args]
    for key in astNode.keywords:
        valueIcon = icon.createFromAst(key.value, window)
        if hasattr(key, 'fieldMacroAnnotations'):
            fieldName, macroArgs, iconCreateFn, argAsts = key.fieldMacroAnnotations[0]
        else:
            fieldName = macroArgs = argAsts = None
        if fieldName == 'Ctx' and 'K' in macroArgs:
            # This is a Ctx macro with K (masquerade as keyword) argument, use macro arg
            argIcons.append(icon.createFromAst(argAsts[0], window))
        elif key.arg is None:
            starStarIcon = StarStarIcon(window)
            starStarIcon.replaceChild(valueIcon, 'argIcon')
            argIcons.append(starStarIcon)
        else:
            kwIcon = ArgAssignIcon(window)
            nameIcon = nameicons.createIconForNameField(key, key.arg, window)
            kwIcon.replaceChild(nameIcon, 'leftArg')
            kwIcon.replaceChild(valueIcon, 'rightArg')
            argIcons.append(kwIcon)
    callIcon.insertChildren(argIcons, "argIcons", 0)
    return callIcon

def createFnIconFromAst(astNode, window):
    callIcon = createCallIconFromAst(astNode, window)
    if filefmt.isAttrParseStub(astNode.func):
        return callIcon  # This is a free call paren on the top level
    topIcon = icon.createFromAst(astNode.func, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(callIcon, "attrIcon")
    return topIcon
icon.registerIconCreateFn(ast.Call, createFnIconFromAst)

def createArgAssignIconFromFakeAst(astNode, window):
    # The filefmt module provides its own "fake" ast node to represent an argument
    # assignment expression outside of the the context of a call or function def.
    # Translate it to an icon.
    assignIcon = ArgAssignIcon(window)
    kwdAst = astNode.keywordAst
    valueIcon = icon.createFromAst(kwdAst.value, window)
    if kwdAst.arg is None:
        starStarIcon = StarStarIcon(window)
        starStarIcon.replaceChild(valueIcon, 'argIcon')
        return starStarIcon
    nameIcon = nameicons.createIconForNameField(kwdAst, kwdAst.arg, window)
    assignIcon.replaceChild(nameIcon, 'leftArg')
    assignIcon.replaceChild(valueIcon, 'rightArg')
    return assignIcon
icon.registerIconCreateFn(filefmt.ArgAssignFakeAst, createArgAssignIconFromFakeAst)

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
    # Note the use of createOpArgFromAst to create the rightmost arg for of comprehension
    # clauses.  This is for processing the unusual case of an inline-if in that spot,
    # which gets auto-parens per Python syntax rules, to ensure that it doesn't conflict
    # with a cprh 'if' clause.
    for gen in astNode.generators:
        forIcon = CprhForIcon(gen.is_async, window=window)
        if isinstance(gen.target, ast.Tuple) and not \
                hasattr(gen.target, 'tupleHasParens'):
            tgtIcons = [icon.createFromAst(t, window) for t in gen.target.elts]
            forIcon.insertChildren(tgtIcons, "targets", 0)
        elif isinstance(gen.target, ast.Name) and gen.target.id == UNASSOC_IF_IDENT:
            # To fake out the parser for an 'if' comprehension clause not associated with
            # a 'for', we define a macro to replace itself with: 'for unique_ident in'
            # and when we see the unique identifier, we turn it back in to an 'if'
            # comprehension with the test taken from the iterator of the 'for'.
            ifIcon = CprhIfIcon(window)
            testIcon = opicons.createOpArgFromAst(ifIcon, 'testIcon', gen.iter, window)
            ifIcon.replaceChild(testIcon, 'testIcon')
            topIcon.insertChild(ifIcon, "cprhIcons", clauseIdx)
            clauseIdx += 1
            continue
        else:
            forIcon.insertChild(icon.createFromAst(gen.target, window), "targets", 0)
        forIcon.replaceChild(opicons.createOpArgFromAst(forIcon, 'iterIcon',
            gen.iter, window), 'iterIcon')
        topIcon.insertChild(forIcon, "cprhIcons", clauseIdx)
        clauseIdx += 1
        for i in gen.ifs:
            ifIcon = CprhIfIcon(window)
            testIcon = opicons.createOpArgFromAst(ifIcon, 'testIcon', i, window)
            ifIcon.replaceChild(testIcon, 'testIcon')
            topIcon.insertChild(ifIcon, "cprhIcons", clauseIdx)
            clauseIdx += 1
    return topIcon
icon.registerIconCreateFn(ast.ListComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.DictComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.SetComp, createComprehensionIconFromAst)
icon.registerIconCreateFn(ast.GeneratorExp, createComprehensionIconFromAst)
filefmt.registerBuiltInMacro(UNASSOC_IF_MACRO_NAME, f'for {UNASSOC_IF_IDENT} in')

def createCprhIfFromFakeAst(astNode, window):
    ifIcon = CprhIfIcon(window)
    testIcon = opicons.createOpArgFromAst(ifIcon, 'testIcon', astNode.cmp, window)
    ifIcon.replaceChild(testIcon, 'testIcon')
    return ifIcon
icon.registerIconCreateFn(filefmt.CprhIfFakeAst, createCprhIfFromFakeAst)

def createCprhForFromFakeAst(astNode, window):
    forIcon = CprhForIcon(astNode.isAsync, window=window)
    if isinstance(astNode.target, ast.Tuple) and not \
            hasattr(astNode.target, 'tupleHasParens'):
        tgtIcons = [icon.createFromAst(t, window) for t in astNode.target.elts]
        forIcon.insertChildren(tgtIcons, "targets", 0)
    else:
        forIcon.insertChild(icon.createFromAst(astNode.target, window), "targets", 0)
    forIcon.replaceChild(opicons.createOpArgFromAst(forIcon, 'iterIcon',
        astNode.iter, window), 'iterIcon')
    return forIcon
icon.registerIconCreateFn(filefmt.CprhForFakeAst, createCprhForFromFakeAst)

def createStarIconFromAst(astNode, window):
    topIcon = StarIcon(window)
    # If the starred item matches filefmt.FN_CALL_PARSE_STUB, this is the weird hack
    # allowing the 'f' parse context to handle function def syntax, which needs a
    # stand-alone (no-argument) *
    if not (astNode.value is None or isinstance(astNode.value, ast.Name) and
            astNode.value.id == filefmt.FN_CALL_PARSE_STUB):
        topIcon.replaceChild(icon.createFromAst(astNode.value, window), "argIcon")
    return topIcon
icon.registerIconCreateFn(ast.Starred, createStarIconFromAst)