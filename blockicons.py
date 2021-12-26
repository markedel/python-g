# Copyright Mark Edel  All rights reserved
from PIL import Image
import ast
import comn
import iconlayout
import iconsites
import icon
import filefmt
import nameicons
import listicons
import infixicon

# Number of pixels to the left of sequence site to start else and elif icons
ELSE_DEDENT = 21

blockStmts = {ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler, ast.With,
 ast.FunctionDef, ast.ClassDef, ast.AsyncFor, ast.AsyncWith, ast.AsyncFunctionDef}

defLParenImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o   84 o",
 "o  81  o",
 "o  28  o",
 "o 73   o",
 "o 56   o",
 "o 48   o",
 "o 19   o",
 "o 19   o",
 "o 18   o",
 "o 28   o",
 "o 68   o",
 "o      o",
 "o      o",
 "oooooooo"))
defLParenExtendDupRows = 11,

defRParenImage = comn.asciiToImage((
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
defRParenExtendDupRows = 7,

class WithAsIcon(infixicon.InfixIcon):
    def __init__(self, window=None, location=None):
        infixicon.InfixIcon.__init__(self, "as", None, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a "with" statement
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            return isinstance(ic, WithIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

class PosOnlyMarkerIcon(nameicons.TextIcon):
    def __init__(self, window=None, location=None):
        nameicons.TextIcon.__init__(self, '/', window, location)

class WithIcon(nameicons.SeriesStmtIcon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        stmt = "async with" if isAsync else "with"
        nameicons.SeriesStmtIcon.__init__(self, stmt, window, seqIndent=True,
                location=location)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window)
            self.sites.seqOut.attach(self, self.blockEnd)

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("with ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export)
        text.add(None, ":")
        return text

    def createAst(self):
        withItems = []
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if isinstance(site.att, WithAsIcon):
                leftArg = site.att.leftArg()
                rightArg = site.att.rightArg()
                if leftArg is None:
                    raise icon.IconExecException(site.att, "Missing argument")
                if rightArg is None:
                    raise icon.IconExecException(site.att, 'Missing name(s) for "as"')
                withItems.append(ast.withitem(leftArg.createAst(), rightArg.createAst()))
            else:
                withItems.append(ast.withitem(site.att.createAst(), None))
        bodyAsts = createBlockAsts(self)
        return ast.With(withItems, body=bodyAsts, lineno=self.id, col_offset=0)

class WhileIcon(icon.Icon):
    def __init__(self, createBlockEnd=True, window=None, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("while", icon.boldFont)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        bodyHeight = max(bodyHeight, icon.minTxtIconHgt)
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + comn.BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + icon.dragSeqImage.width-1, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            txtImg = icon.iconBoxedText("while", icon.boldFont, icon.KEYWORD_COLOR)
            bodyOffset = icon.dragSeqImage.width - 1
            bodyWidth, bodyHeight = txtImg.size
            img = Image.new('RGBA', (bodyOffset + max(comn.BLOCK_INDENT + 3, bodyWidth),
             bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (icon.dragSeqImage.width - 1, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            icon.drawSeqSites(img, bodyOffset, 0, bodyHeight, indent="right",
             extendWidth=bodyWidth)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage,
                        (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += icon.dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            condXOff = width - 1
            layout.addSubLayout(condLayout, 'condIcon', condXOff, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "while " + icon.argTextRepr(self.sites.condIcon) + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("while ")
        icon.addArgSaveText(text, brkLvl, self.sites.condIcon, contNeeded, export)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "while"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        if self.sites.condIcon.att is None:
            raise icon.IconExecException(self, "Missing condition in while statement")
        testAst = self.sites.condIcon.att.createAst()
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElse=True)
        return ast.While(testAst, bodyAsts, orElseAsts, lineno=self.id, col_offset=0)

class ForIcon(icon.Icon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.isAsync = isAsync
        text = "async for" if isAsync else "for"
        bodyWidth = icon.getTextSize(text, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        inWidth = icon.getTextSize("in", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, inWidth)
        siteYOffset = bodyHeight // 2
        targetXOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.tgtList = iconlayout.ListLayoutMgr(self, 'targets', targetXOffset,
                siteYOffset, simpleSpine=True)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + comn.BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        iterX = icon.dragSeqImage.width + bodyWidth-1 + self.tgtList.width-1 + inWidth-1
        self.iterList = iconlayout.ListLayoutMgr(self, 'iterIcons', iterX, siteYOffset,
                simpleSpine=True)
        totalWidth = iterX + self.iterList.width - 1
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.elseIcon = None
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight, inWidth = self.bodySize
            bodyOffset = icon.dragSeqImage.width - 1
            img = Image.new('RGBA', (max(comn.BLOCK_INDENT + 3, bodyWidth) + bodyOffset,
             bodyHeight), color=(0, 0, 0, 0))
            txt = "async for" if self.isAsync else "for"
            txtImg = icon.iconBoxedText(txt, icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            cntrSiteY = self.sites.seqInsert.yOffset
            inImgX = bodyOffset + bodyWidth - 1 - icon.inSiteImage.width
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            icon.drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            # Target list commas and possible list simple-spines
            tgtListOffset = bodyWidth + bodyOffset - 1 - icon.OUTPUT_SITE_DEPTH
            self.drawList += self.tgtList.drawListCommas(tgtListOffset, cntrSiteY)
            self.drawList += self.tgtList.drawSimpleSpine(tgtListOffset, cntrSiteY)
            # "in"
            txtImg = icon.iconBoxedText("in", icon.boldFont, icon.KEYWORD_COLOR)
            img = Image.new('RGBA', (txtImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            inImgX = txtImg.width - icon.inSiteImage.width
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            inOffset = bodyOffset + bodyWidth - 1 + self.tgtList.width - 1
            self.drawList.append(((inOffset, self.sites.seqIn.yOffset - 1), img))
            # Commas and possible list simple-spines
            iterOffset = inOffset + inWidth - 1 - icon.OUTPUT_SITE_DEPTH
            self.drawList += self.iterList.drawListCommas(iterOffset, cntrSiteY)
            self.drawList += self.iterList.drawSimpleSpine(iterOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def addElse(self, ic):
        self.elseIcon = ic
        ic.parentIf = self

    def removeElse(self, ic):
        self.elseIcon = None
        ic.parentIf = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.tgtList.makeInsertSnapList() + \
         self.iterList.makeInsertSnapList()
        return siteSnapLists

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        self.tgtList.doLayout(layout)
        self.iterList.doLayout(layout)
        bodyWidth, bodyHeight, inWidth = self.bodySize
        width = icon.dragSeqImage.width-1 + bodyWidth-1 + self.tgtList.width-1 + \
                inWidth-1 + self.iterList.width
        heightAbove = max(bodyHeight // 2, self.tgtList.spineTop, self.iterList.spineTop)
        heightBelow = max(bodyHeight - bodyHeight // 2, self.tgtList.spineHeight -
                self.tgtList.spineTop, self.iterList.spineHeight - self.iterList.spineTop)
        height = heightAbove + heightBelow
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = heightAbove + bodyHeight // 2 - 1
        self.sites.seqInsert.yOffset = heightAbove
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight, inWidth = self.bodySize
        tgtListLayouts = self.tgtList.calcLayouts()
        iterListLayouts = self.iterList.calcLayouts()
        layouts = []
        for tgtListLayout, iterListLayout in iconlayout.allCombinations((tgtListLayouts,
                iterListLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            tgtXOff = bodyWidth - 1
            tgtListLayout.mergeInto(layout, tgtXOff, 0)
            iterXOff = bodyWidth - 1 + tgtListLayout.width - 1 + inWidth - 1
            iterListLayout.mergeInto(layout, iterXOff, 0)
            layout.width = iterXOff + iterListLayout.width + defRParenImage.width - 2
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        text = "async for" if self.isAsync else "for"
        tgtText = icon.seriesTextRepr(self.sites.targets)
        iterText = icon.seriesTextRepr(self.sites.iterIcons)
        return text + " " + tgtText + " in " + iterText + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("async for " if self.isAsync else "for ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.targets, contNeeded,
            export)
        text.add(brkLvl, " in ", contNeeded)
        icon.addSeriesSaveText(text, brkLvl, self.sites.iterIcons, contNeeded,
            export)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "for"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync,
         createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        # Get the target and iteration icons
        tgts = []
        for site in self.sites.targets:
            if site.att is None:
                raise icon.IconExecException(self, "Missing assignment target(s)")
            tgts.append(site.att)
        if len(tgts) == 1:
            tgtAst = tgts[0].createAst()
        else:
            perTgtAsts = [tgt.createAst() for tgt in tgts]
            tgtAst = ast.Tuple(perTgtAsts, ctx=ast.Store(), lineno=self.id,
             col_offset=0)
        iterValues = []
        for site in self.sites.iterIcons:
            if site.att is None:
                raise icon.IconExecException(self, "Missing iteration value")
            iterValues.append(site.att)
        # Make asts for targets and values, adding tuples if packing/unpacking is
        # specified
        if len(iterValues) == 1:
            valueAst = iterValues[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in iterValues], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElse=True)
        return ast.For(tgtAst, valueAst, bodyAsts, orElseAsts, lineno=self.id,
         col_offset=0)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + icon.dragSeqImage.width - 1
        bodyWidth, bodyHeight, inWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

class IfIcon(icon.Icon):
    def __init__(self, createBlockEnd=True, window=None, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("if", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + comn.BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        width = max(seqX + comn.BLOCK_INDENT + 1, bodyWidth + icon.dragSeqImage.width-1)
        self.rect = (x, y, x + width, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)
        self.elifIcons = []
        self.elseIcon = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
                    comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            boxLeft = icon.dragSeqImage.width - 1
            txtImg = icon.iconBoxedText("if", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            icon.drawSeqSites(img, boxLeft, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage,
                        (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def select(self, select=True, includeElses=False):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)
        if includeElses:
            if self.elseIcon is not None:
                icon.Icon.select(self.elseIcon, select)
            for elifIc in self.elifIcons:
                icon.Icon.select(elifIc, select)

    def addElse(self, ic):
        if isinstance(ic, ElifIcon):
            self.elifIcons.append(self)
        else:
            self.elseIcon = ic
        ic.parentIf = self

    def removeElse(self, ic):
        if isinstance(ic, ElifIcon):
            self.elifIcons.remove(self)
        else:
            self.elseIcon = None
        ic.parentIf = None

    def doLayout(self, left, top, layout):
        layout.updateSiteOffsets(self.sites.seqInsert)
        width, height = self.bodySize
        width = max(comn.BLOCK_INDENT + 3, width) + icon.dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.doSubLayouts(self.sites.seqInsert, left, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(condLayout, 'condIcon', width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "if " + icon.argTextRepr(self.sites.condIcon) + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("if ")
        icon.addArgSaveText(text, brkLvl, self.sites.condIcon, contNeeded, export)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "if"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        if self.sites.condIcon.att is None:
            raise icon.IconExecException(self, "Missing condition in if statement")
        testAst = self.sites.condIcon.att.createAst()
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElifElse=True)
        return ast.If(testAst, bodyAsts, orElseAsts, lineno=self.id, col_offset=0)

class ElifIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("elif ", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + icon.dragSeqImage.width - 1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + icon.dragSeqImage.width - 1, y + bodyHeight)
        self.parentIf = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
                    comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText("elif ", icon.boldFont, icon.KEYWORD_COLOR)
            boxLeft = icon.dragSeqImage.width - 1
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            seqSiteX = self.sites.seqIn.xOffset-1
            img.paste(icon.seqSiteImage, (seqSiteX, self.sites.seqIn.yOffset-1))
            img.paste(icon.seqSiteImage, (seqSiteX, self.sites.seqOut.yOffset-1))
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += icon.dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(condLayout, 'condIcon', width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "elif " + icon.argTextRepr(self.sites.condIcon) + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("elif ")
        icon.addArgSaveText(text, brkLvl, self.sites.condIcon, contNeeded, export)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "elif"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class ElseIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("else", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        seqX = icon.dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, bodyHeight // 2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + icon.dragSeqImage.width - 1, y + bodyHeight)
        self.parentIf = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
                    comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText("else", icon.boldFont, icon.KEYWORD_COLOR)
            boxLeft = icon.dragSeqImage.width - 1
            img.paste(txtImg, (boxLeft, 0))
            seqSiteX = self.sites.seqIn.xOffset-1
            img.paste(icon.seqSiteImage, (seqSiteX, self.sites.seqIn.yOffset-1))
            img.paste(icon.seqSiteImage, (seqSiteX, self.sites.seqOut.yOffset-1))
            if temporaryDragSite:
                img.paste(icon.dragSeqImage,
                        (0, txtImg.height//2 - icon.dragSeqImage.height//2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += icon.dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        layout = iconlayout.Layout(self, width, height, height // 2)
        return [layout]

    def textRepr(self):
        return "else:"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText("else:")

    def dumpName(self):
        return "else"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class DefOrClassIcon(icon.Icon):
    def __init__(self, text, hasArgs, createBlockEnd=True, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.text = text
        bodyWidth = icon.getTextSize(self.text, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        nameXOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('nameIcon', 'input', nameXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + comn.BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        if hasArgs:
            lParenWidth = defLParenImage.width
            self.nameWidth = icon.EMPTY_ARG_WIDTH
            argX = icon.dragSeqImage.width + bodyWidth + self.nameWidth + lParenWidth
            self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', argX, siteYOffset)
            rParenWidth = defRParenImage.width
            totalWidth = argX + self.argList.width + rParenWidth - 3
            self.sites.add('attrIcon', 'attrIn', totalWidth,
                bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True)
        else:
            totalWidth = max(bodyWidth, comn.BLOCK_INDENT+2) + icon.dragSeqImage.width
            self.argList = None
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = icon.dragSeqImage.width - 1
            img = Image.new('RGBA', (max(bodyWidth, comn.BLOCK_INDENT+3) + bodyOffset,
             bodyHeight), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText(self.text, icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.nameIcon.xOffset, inImageY))
            icon.drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage,
                        (0, bodyHeight // 2 - icon.dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            if self.argList is not None:
                # Open Paren
                lParenOffset = bodyOffset + bodyWidth - 1 + self.nameWidth - 1
                lParenImg = icon.yStretchImage(defLParenImage,
                        defLParenExtendDupRows, self.argList.spineHeight)
                # Open paren body sites
                self.argList.drawBodySites(lParenImg)
                self.drawList.append(((lParenOffset, 0), lParenImg))
                # Commas
                argsOffset = lParenOffset + defLParenImage.width - 1
                self.drawList += self.argList.drawListCommas(
                        argsOffset - icon.OUTPUT_SITE_DEPTH, self.argList.spineTop)
                # End Paren
                rParenOffset = argsOffset + self.argList.width - 1
                rParenImg = icon.yStretchImage(defRParenImage, defRParenExtendDupRows,
                        self.argList.spineHeight)
                self.drawList.append(((rParenOffset, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def argIcons(self):
        if self.argList is None:
            return []
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor or not self.argList is not None:
            return siteSnapLists
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        listicons.restoreConditionalTargets(self, siteSnapLists,
         (listicons.StarIcon, listicons.StarStarIcon, listicons.ArgAssignIcon))
        return siteSnapLists

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        self.nameWidth = layout.nameWidth
        bodyWidth, bodyHeight = self.bodySize
        width = icon.dragSeqImage.width - 1 + bodyWidth - 1 + self.nameWidth
        if self.argList is None:
            height = bodyHeight
            centerY = bodyHeight // 2 + 1
        else:
            self.argList.doLayout(layout)
            width += defLParenImage.width - 1 + self.argList.width - 1 + \
                    defRParenImage.width
            height = self.argList.spineHeight
            centerY = self.argList.spineTop
        self.sites.seqInsert.yOffset = centerY
        seqInY = centerY - bodyHeight // 2 + 1
        self.sites.seqIn.yOffset = seqInY
        self.sites.seqOut.yOffset = seqInY + bodyHeight - 2
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        # ... The parent site offsets need to be adjusted one pixel left and up, here, for
        #     the child icons to draw in the right place, but I have no idea why.
        layout.doSubLayouts(self.sites.seqInsert, left, top + centerY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        argListLayouts = [None] if self.argList is None else self.argList.calcLayouts()
        nameIcon = self.sites.nameIcon.att
        nameLayouts = [None] if nameIcon is None else nameIcon.calcLayouts()
        nameXOff = bodyWidth - 1
        cntrYOff = bodyHeight // 2
        layouts = []
        for nameLayout, argListLayout in iconlayout.allCombinations(
                (nameLayouts, argListLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, cntrYOff)
            layout.addSubLayout(nameLayout, 'nameIcon', nameXOff, 0)
            nameWidth = icon.EMPTY_ARG_WIDTH if nameLayout is None else nameLayout.width
            layout.nameWidth = nameWidth
            if argListLayout is not None:
                argXOff = bodyWidth - 1 + nameWidth - 1 + defLParenImage.width
                argListLayout.mergeInto(layout, argXOff - icon.OUTPUT_SITE_DEPTH, 0)
                layout.width = argXOff + argListLayout.width + defRParenImage.width - 2
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        nameIcon = self.sites.nameIcon.att
        text = self.text + " " + ("" if nameIcon is None else nameIcon.textRepr())
        if self.argList is None:
            return text
        return text + "(" + icon.seriesTextRepr(self.sites.argIcons) + "):"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.text + " ")
        icon.addArgSaveText(text, brkLvl, self.sites.nameIcon, contNeeded, export)
        if self.argList is None:
            text.add(None, ":")
            return text
        text.add(None, "(")
        icon.addSeriesSaveText(text, brkLvl, self.sites.argIcons, contNeeded, export)
        text.add(None, "):")
        return text

    def dumpName(self):
        return self.text

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + icon.dragSeqImage.width - 1
        bodyWidth, bodyHeight = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

    def addArgs(self):
        if self.argList is not None:
            return
        argX = comn.rectWidth(self.rect)
        argY = self.sites.nameIcon.yOffset
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', argX, argY)
        self.window.undo.registerCallback(self.removeArgs)

    def removeArgs(self):
        if self.argList is None:
            return
        if len(self.argIcons()) > 0:
            print("trying to remove non-empty argument list")
            return
        self.argList = None
        self.window.undo.registerCallback(self.addArgs)

class ClassDefIcon(DefOrClassIcon):
    def __init__(self, hasArgs=False, createBlockEnd=True, window=None, location=None):
        DefOrClassIcon.__init__(self, "class", hasArgs, createBlockEnd, window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, hasArgs=self.argList is not None,
         createBlockEnd=False)

    def createAst(self):
        nameIcon = self.sites.nameIcon.att
        if nameIcon is None:
            raise icon.IconExecException(self, "Definition missing function name")
        if not isinstance(nameIcon, nameicons.IdentifierIcon):
            raise icon.IconExecException(nameIcon, "Argument name must be identifier")
        bases = []
        kwds = []
        if self.argList is not None:
            for site in self.sites.argIcons:
                base = site.att
                if base is None:
                    if site.name == 'argIcons_0':
                        continue  # 1st site can be empty, meaning parens but no bases
                    raise icon.IconExecException(self, "Missing argument(s)")
                if isinstance(base, listicons.ArgAssignIcon):
                    keyIcon = base.sites.leftArg.att
                    valueIcon = base.sites.rightArg.att
                    if keyIcon is None:
                        raise icon.IconExecException(base, "Missing keyword name")
                    if not isinstance(keyIcon, nameicons.IdentifierIcon):
                        raise icon.IconExecException(keyIcon,
                                "Keyword must be identifier")
                    kwds.append(ast.keyword(keyIcon.name, valueIcon.createAst(),
                     lineno=base.id, col_offset=0))
                else:
                    bases.append(base.createAst())
        bodyAsts = createBlockAsts(self)
        return ast.ClassDef(nameIcon.name, bases, keywords=kwds, body=bodyAsts,
         decorator_list=[], lineno=self.id, col_offset=0)

class DefIcon(DefOrClassIcon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        self.isAsync = isAsync
        text = "async def" if isAsync else "def"
        DefOrClassIcon.__init__(self, text, True, createBlockEnd, window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync,
         createBlockEnd=False)

    def createAst(self):
        nameIcon = self.sites.nameIcon.att
        if nameIcon is None:
            raise icon.IconExecException(self, "Definition missing function name")
        if not isinstance(nameIcon, nameicons.IdentifierIcon):
            raise icon.IconExecException(nameIcon, "Argument name must be identifier")
        posOnlyArgAsts = []
        normalArgAsts = []
        kwdOnlyAsts = []
        normalArgDefaults = []
        kwOnlyDefaults = []
        accumArgAsts = normalArgAsts
        accumArgDefaults = normalArgDefaults
        starArgAst = None
        starStarArgAst = None
        for site in self.sites.argIcons:
            arg = site.att
            if arg is None:
                if site.name == 'argIcons_0':
                    continue  # 1st site can be empty, meaning "no arguments"
                raise icon.IconExecException(self, "Missing argument(s)")
            if isinstance(arg, listicons.ArgAssignIcon):
                argIcon = arg.sites.leftArg.att
                defaultIcon = arg.sites.rightArg.att
                if argIcon is None:
                    raise icon.IconExecException(arg, "Missing argument name")
                if not isinstance(argIcon, nameicons.IdentifierIcon):
                    raise icon.IconExecException(arg, "Argument name must be identifier")
                if defaultIcon is None:
                    raise icon.IconExecException(arg, "Missing default value")
                accumArgAsts.append(ast.arg(argIcon.name, lineno=arg.id, col_offset=0))
                accumArgDefaults.append(defaultIcon.createAst())
            elif isinstance(arg, listicons.StarStarIcon):
                starStarArg = arg.sites.argIcon.att
                if starStarArg is None:
                    raise icon.IconExecException(arg, "Missing value for **")
                if not isinstance(starStarArg, nameicons.IdentifierIcon):
                    raise icon.IconExecException(starStarArg,
                            "Argument must be identifier")
                starStarArgAst = ast.arg(starStarArg.name, lineno=arg.id, col_offset=0)
            elif isinstance(arg, listicons.StarIcon):
                # A star icon with an argument is a vararg list.  Without, it is a
                # keyword-only marker.  Either way, subsequent arguments are keyword-only
                # and should go in the kwdOnly lists
                starArg = arg.sites.argIcon.att
                if starArg is not None:
                    if not isinstance(starArg, nameicons.IdentifierIcon):
                        raise icon.IconExecException(starArg,
                                "Argument must be identifier")
                    starArgAst = ast.arg(starArg.name, lineno=arg.id, col_offset=0)
                accumArgAsts = kwdOnlyAsts
                accumArgDefaults = kwOnlyDefaults
            elif isinstance(arg, PosOnlyMarkerIcon):
                posOnlyArgAsts = normalArgAsts
                normalArgAsts = []
                accumArgAsts = normalArgAsts
            else:
                if not isinstance(arg, nameicons.IdentifierIcon):
                    raise icon.IconExecException(arg, "Argument name must be identifier")
                accumArgAsts.append(ast.arg(arg.name, lineno=arg.id, col_offset=0))
        argumentAsts = ast.arguments(posOnlyArgAsts, normalArgAsts, starArgAst,
         kwdOnlyAsts, kwOnlyDefaults, starStarArgAst, normalArgDefaults)
        bodyAsts = createBlockAsts(self)
        if self.isAsync:
            return ast.AsyncFunctionDef(nameIcon.name, argumentAsts, bodyAsts,
             decorator_list=[], returns=None, lineno=self.id, col_offset=0)
        return ast.FunctionDef(nameIcon.name, argumentAsts, bodyAsts,
         decorator_list=[], returns=None, lineno=self.id, col_offset=0)

def createBlockAsts(ic, allowsElse=False, allowsElifElse=False):
    """Create ASTs for icons in the block belonging to ic, suitable for the "body"
    parameter to ASTs for statements that own an indented block.  If allowsElse is
    True, the block can contain an else clause.  If allowsElifElse is True, the block
    may also contain elif statements and the function returns two items: 1) a list of
    the statement ASTs, and 2) a list of the else-clause ASTs (there is no elif AST,
    elifs are converted to an else clause containing chained "if" ASTs).  Without
    either allowsElse or allowsElifElse, the function returns just the list of statement
    ASTs"""
    stmtAsts = []
    endBlock = ic.blockEnd
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise icon.IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            if not allowsElifElse:
                raise icon.IconExecException(stmt, "Elif statement should not be here")
            return stmtAsts, [createElifAst(stmt, endBlock)]
        elif isinstance(stmt, ElseIcon):
            if not (allowsElse or allowsElifElse):
                raise icon.IconExecException(stmt, "Else statement should not be here")
            return stmtAsts, createElseAsts(stmt, endBlock)
        else:
            stmtAsts.append(icon.createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    if allowsElse or allowsElifElse:
        return stmtAsts, []
    return stmtAsts

def createElseAsts(ic, endBlock):
    """Return a list of statement ASTs from the else clause starting at"""
    stmtAsts = []
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise icon.IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            raise icon.IconExecException(stmt, "Elif statement found after else")
        if isinstance(stmt, ElseIcon):
            raise icon.IconExecException(stmt, "Multiple else statements")
        stmtAsts.append(icon.createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    return stmtAsts

def createElifAst(ic, endBlock):
    """Returns a single "if" AST representing the remaining elif and else clauses starting
    at elif icon, ic."""
    if ic.sites.condIcon.att is None:
        raise icon.IconExecException(ic, "Missing condition in elif")
    stmtAsts = []
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise icon.IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            return ast.If(ic.sites.condIcon.att.createAst(), stmtAsts,
             [createElifAst(stmt, endBlock)], lineno=ic.id, col_offset=0)
        if isinstance(stmt, ElseIcon):
            return ast.If(ic.sites.condIcon.att.createAst(), stmtAsts,
             createElseAsts(stmt, endBlock), lineno=ic.id, col_offset=0)
        stmtAsts.append(icon.createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    return stmtAsts

def elseElifBlockIcons(ic):
    """Returns a list of all icons (hierarchy) in an else or elif clause, including
    the else or elif icon itself."""
    seqIcons = list(ic.traverse())
    for seqIcon in icon.traverseSeq(ic, includeStartingIcon=False):
        if isinstance(seqIcon, icon.BlockEnd):
            break
        if seqIcon.__class__ in (ElifIcon, ElseIcon):
            break
        seqIcons += list(seqIcon.traverse())
    return seqIcons

def createWhileIconFromAst(astNode, window):
    topIcon = WhileIcon(window=window)
    topIcon.replaceChild(icon.createFromAst(astNode.test, window), 'condIcon')
    return topIcon
icon.registerIconCreateFn(ast.While, createWhileIconFromAst)

def createForIconFromAst(astNode, window):
    isAsync = astNode.__class__ is ast.AsyncFor
    topIcon = ForIcon(isAsync, window=window)
    if isinstance(astNode.target, ast.Tuple):
        tgtIcons = [icon.createFromAst(t, window) for t in astNode.target.elts]
        topIcon.insertChildren(tgtIcons, "targets", 0)
    else:
        topIcon.replaceChild(icon.createFromAst(astNode.target, window), "targets_0")
    if isinstance(astNode.iter, ast.Tuple):
        iterIcons = [icon.createFromAst(i, window) for i in astNode.iter]
        topIcon.insertChildren(iterIcons, "iterIcons", 0)
    else:
        topIcon.replaceChild(icon.createFromAst(astNode.iter, window), "iterIcons_0")
    return topIcon
icon.registerIconCreateFn(ast.For, createForIconFromAst)
icon.registerIconCreateFn(ast.AsyncFor, createForIconFromAst)

def createIfIconFromAst(astNode, window):
    topIcon = IfIcon(window=window)
    topIcon.replaceChild(icon.createFromAst(astNode.test, window), 'condIcon')
    return topIcon
icon.registerIconCreateFn(ast.If, createIfIconFromAst)

def createDefIconFromAst(astNode, window):
    isAsync = astNode.__class__ is ast.AsyncFunctionDef
    if hasattr(astNode.args, 'posonlyargs'):
        args = [arg.arg for arg in astNode.args.posonlyargs]
    else:
        args = []
    nPosOnly = len(args)
    defIcon = DefIcon(isAsync, window=window)
    nameIcon = nameicons.IdentifierIcon(astNode.name, window)
    defIcon.replaceChild(nameIcon, 'nameIcon')
    defaults = [icon.createFromAst(e, window) for e in astNode.args.defaults]
    if len(defaults) < len(astNode.args.args):
        # Weird rule in defaults list for ast that defaults can be shorter than args
        defaults = ([None] * (len(astNode.args.args) - len(defaults))) + defaults
    numArgs = 0
    for i, arg in enumerate(arg.arg for arg in astNode.args.args):
        default = defaults[i]
        argNameIcon = nameicons.IdentifierIcon(arg, window)
        if nPosOnly != 0 and numArgs == nPosOnly:
            posOnlyMarker = PosOnlyMarkerIcon(window=window)
            defIcon.insertChild(posOnlyMarker, 'argIcons', numArgs)
            numArgs += 1
        if default is None:
            defIcon.insertChild(argNameIcon, 'argIcons', numArgs)
        else:
            defaultIcon = default
            argAssignIcon = listicons.ArgAssignIcon(window)
            argAssignIcon.replaceChild(argNameIcon, 'leftArg')
            argAssignIcon.replaceChild(defaultIcon, 'rightArg')
            defIcon.insertChild(argAssignIcon, "argIcons", numArgs)
        numArgs += 1
    varArg = astNode.args.vararg.arg if astNode.args.vararg is not None else None
    if varArg is not None:
        argNameIcon = nameicons.IdentifierIcon(varArg, window)
        starIcon = listicons.StarIcon(window)
        starIcon.replaceChild(argNameIcon, 'argIcon')
        defIcon.insertChild(starIcon, 'argIcons', numArgs)
        numArgs += 1
    kwOnlyArgs = [arg.arg for arg in astNode.args.kwonlyargs]
    kwDefaults = [icon.createFromAst(e, window) for e in astNode.args.kw_defaults]
    if len(kwOnlyArgs) > 0 and varArg is None:
        defIcon.insertChild(listicons.StarIcon(window), 'argIcons', numArgs)
        numArgs += 1
    for i, arg in enumerate(kwOnlyArgs):
        argNameIcon = nameicons.IdentifierIcon(arg, window)
        if kwDefaults[i] is None:
            defIcon.insertChild(argNameIcon, 'argIcons', i)
        else:
            defaultIcon = kwDefaults[i]
            argAssignIcon = listicons.ArgAssignIcon(window)
            argAssignIcon.replaceChild(argNameIcon, 'leftArg')
            argAssignIcon.replaceChild(defaultIcon, 'rightArg')
            defIcon.insertChild(argAssignIcon, "argIcons", numArgs + i)
    numArgs += len(kwOnlyArgs)
    if astNode.args.kwarg is not None:
        argNameIcon = nameicons.IdentifierIcon(astNode.args.kwarg.arg, window)
        starStarIcon = listicons.StarStarIcon(window)
        starStarIcon.replaceChild(argNameIcon, 'argIcon')
        defIcon.insertChild(starStarIcon, 'argIcons', numArgs)
    return defIcon
icon.registerIconCreateFn(ast.FunctionDef, createDefIconFromAst)
icon.registerIconCreateFn(ast.AsyncFunctionDef, createDefIconFromAst)

def createClassDefIconFromAst(astNode, window):
    hasArgs = len(astNode.bases) + len(astNode.keywords) > 0
    topIcon = ClassDefIcon(hasArgs, window=window)
    nameIcon = nameicons.IdentifierIcon(astNode.name, window)
    topIcon.replaceChild(nameIcon, 'nameIcon')
    bases = [icon.createFromAst(base, window) for base in astNode.bases]
    topIcon.insertChildren(bases, "argIcons", 0)
    kwdIcons = []
    for idx, kwd in enumerate(astNode.keywords):
        argAssignIcon = listicons.ArgAssignIcon(window)
        kwdIcon = nameicons.IdentifierIcon(kwd, window)
        valueIcon = icon.createFromAst(kwd.value, window)
        argAssignIcon.replaceChild(kwdIcon, 'leftArg')
        argAssignIcon.replaceChild(valueIcon, 'rightArg')
        kwdIcons.append(argAssignIcon)
    topIcon.insertChildren(kwdIcons, "argIcons", len(bases))
    return topIcon
icon.registerIconCreateFn(ast.ClassDef, createClassDefIconFromAst)

def createWithIconFromAst(astNode, window):
    isAsync = isinstance(astNode, ast.AsyncWith)
    topIcon = WithIcon(isAsync, window=window)
    for idx, item in enumerate(astNode.items):
        contextIcon = icon.createFromAst(item.context_expr, window)
        if item.optional_vars is None:
            topIcon.insertChild(contextIcon, "values", idx)
        else:
            asIcon = WithAsIcon(window)
            asIcon.replaceChild(contextIcon, "leftArg")
            asIcon.replaceChild(icon.createFromAst(item.optional_vars, window),
                "rightArg")
            topIcon.insertChild(asIcon, "values", idx)
    return topIcon
icon.registerIconCreateFn(ast.With, createWithIconFromAst)
icon.registerIconCreateFn(ast.AsyncWith, createWithIconFromAst)

def createIconsFromBodyAst(bodyAst, window):
    icons = []
    seqStartIcon = None
    for stmt in bodyAst:
        if hasattr(stmt, 'linecomments'):
            for comment in stmt.linecomments:
                commentIcon = nameicons.CommentIcon(comment, window)
                if seqStartIcon is None:
                    seqStartIcon = commentIcon
                else:
                    icons[-1].sites.seqOut.attach(icons[-1], commentIcon, 'seqIn')
                icons.append(commentIcon)
        if isinstance(stmt, ast.Expr):
            stmtIcon = icon.createFromAst(stmt.value, window)
            bodyIcons = None
        elif stmt.__class__ in blockStmts:
            stmtIcon = icon.createFromAst(stmt, window)
            bodyIcons = createIconsFromBodyAst(stmt.body, window)
            stmtIcon.sites.seqOut.attach(stmtIcon, bodyIcons[0], 'seqIn')
            while stmt.__class__ is ast.If and len(stmt.orelse) == 1 and \
                    stmt.orelse[0].__class__ is ast.If:
                # Process elif blocks.  The ast encodes these as a single if, nested
                # in and else (nested as many levels deep as there are elif clauses).
                elifIcon = ElifIcon(window)
                condIcon = icon.createFromAst(stmt.orelse[0].test, window)
                elifIcon.replaceChild(condIcon, 'condIcon')
                elifBlockIcons = createIconsFromBodyAst(stmt.orelse[0].body, window)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elifIcon, 'seqIn')
                bodyIcons.append(elifIcon)
                elifIcon.sites.seqOut.attach(elifIcon, elifBlockIcons[0], 'seqIn')
                bodyIcons += elifBlockIcons
                stmtIcon.addElse(elifIcon)
                stmt = stmt.orelse[0]
            if stmt.__class__ in (ast.If, ast.For, ast.AsyncFor, ast.While) and \
                    len(stmt.orelse) != 0:
                # Process else block (note that after elif processing above, stmt may in
                # some cases point to a nested statement being flattened out)
                elseIcon = ElseIcon(window)
                elseBlockIcons = createIconsFromBodyAst(stmt.orelse, window)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elseIcon, 'seqIn')
                bodyIcons.append(elseIcon)
                elseIcon.sites.seqOut.attach(elseIcon, elseBlockIcons[0], 'seqIn')
                bodyIcons += elseBlockIcons
                stmtIcon.addElse(elseIcon)
            blockEnd = stmtIcon.blockEnd
            bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], blockEnd, 'seqIn')
            bodyIcons.append(blockEnd)
        else:
            stmtIcon = icon.createFromAst(stmt, window)
            bodyIcons = None
        if seqStartIcon is None:
            seqStartIcon = stmtIcon
        elif icons[-1].hasSite('seqOut') and stmtIcon.hasSite('seqIn'):
            # Link the statement to the previous statement
            icons[-1].sites.seqOut.attach(icons[-1], stmtIcon, 'seqIn')
        else:
            print('Cannot link icons (no sequence sites)')  # Shouldn't happen
        icons.append(stmtIcon)
        if bodyIcons is not None:
            icons += bodyIcons
    return icons
