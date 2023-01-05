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
import entryicon
import commenticon

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

defLParenTypeoverImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o    8 o",
 "o   8  o",
 "o  8   o",
 "o  8   o",
 "o 99   o",
 "o 8    o",
 "o 8    o",
 "o 8    o",
 "o 8    o",
 "o 8    o",
 "o 9    o",
 "o      o",
 "o      o",
 "oooooooo"))

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

defRParenTypeoverImage = comn.asciiToImage( (
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

lambdaColonImage = comn.asciiToImage( (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o  %%  o",
 "o  %% o.",
 "o    o..",
 "o     o.",
 "o  %%  o",
 "o  %%  o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "oooooooo"))

lambdaColonTypeoverImage = comn.asciiToImage( (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "o  88  o",
 "o  88 o.",
 "o    o..",
 "o     o.",
 "o  88  o",
 "o  88  o",
 "o      o",
 "o      o",
 "o      o",
 "o      o",
 "oooooooo"))

class WithIcon(icon.Icon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        stmt = "async with" if isAsync else "with"
        icon.Icon.__init__(self, window)
        self.stmt = stmt
        bodyWidth = icon.getTextSize(stmt, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        seqOutIndent = comn.BLOCK_INDENT
        self.sites.add('seqOut', 'seqOut', seqX + seqOutIndent, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = icon.dragSeqImage.width + bodyWidth
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', bodyWidth+1,
                siteYOffset, simpleSpine=True)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window)
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
            img = Image.new('RGBA', (bodyOffset + max(bodyWidth, comn.BLOCK_INDENT+2),
             bodyHeight), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText(self.stmt, icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImgX = bodyOffset + bodyWidth - icon.inSiteImage.width
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            icon.drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
                 extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, bodyHeight // 2 -
                        icon.dragSeqImage.height // 2))
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valueList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valueList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valueList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, left, top, layout):
        self.valueList.doLayout(layout)
        bodyWidth, bodyHeight = self.bodySize
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        width = icon.dragSeqImage.width - 1 + bodyWidth + self.valueList.width + 2
        if self.valueList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.valueList.spineTop)
            heightBelow = max(heightBelow, self.valueList.spineHeight -
                    self.valueList.spineTop)
        self.sites.seqInsert.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        height = heightAbove + heightBelow
        self.rect = left, top, left + width, top + height
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        valueListLayouts = self.valueList.calcLayouts()
        layouts = []
        for valueListLayout in valueListLayouts:
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            valueListLayout.mergeInto(layout, bodyWidth - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def textRepr(self):
        return self.stmt + " " + icon.seriesTextRepr(self.sites.values)

    def dumpName(self):
        return self.stmt

    def execute(self):
        return None  #... no idea what to do here, yet.

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:6] == 'values':
            parent = entryIc.parent()
            if isinstance(parent, infixicon.AsIcon):
                # Enforce identifiers-only on right argument of "as"
                name = text.rstrip(' ')
                if name == ',':
                    return "comma"
                name = name.rstrip(',')
                if not name.isidentifier():
                    return "reject"
                if text[-1] in (' ', ','):
                    return nameicons.IdentifierIcon(name, self.window), text[-1]
                return "accept"
            elif text == ',':
                return "comma"
            elif onAttr:
                # Allow "as" to be typed
                if text == 'a':
                    return "accept"
                elif text == 'as':
                    return infixicon.AsIcon(self.window), None
                delim = text[-1]
                text = text[:-1]
                if text == 'as' and delim in entryicon.emptyDelimiters:
                    return infixicon.AsIcon(self.window), delim
        return None

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        if siteName == "values" and index == 0:
            # Cursor is on first input site.  Remove icon and replace with cursor
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon, drawNew=False)
        elif siteName == "values":
            # Cursor is on comma input.  Delete if empty or previous site is empty, merge
            # surrounding sites if not
            listicons.backspaceComma(self, siteId, evt)

    def _becomeEntryIcon(self):
        win = self.window
        valueIcons = [s.att for s in self.sites.values]
        if len(valueIcons) in (0, 1):
            # Zero or one argument, convert to entry icon (with pending arg if
            # there was an argument)
            if len(valueIcons) == 1 and valueIcons[0] is not None:
                pendingArgSite = self.siteOf(valueIcons[0])
            else:
                pendingArgSite = None
            entryIcon = win.replaceIconWithEntry(self, self.stmt, pendingArgSite)
        else:
            # Multiple remaining arguments: convert to entry icon with pending
            # arguments as a single list
            self.window.requestRedraw(self.topLevelParent().hierRect(),
                filterRedundantParens=True)
            valueIcons = [s.att for s in self.sites.values]
            entryIcon = entryicon.EntryIcon(initialString=self.stmt, window=win,
                willOwnBlock=True)
            for arg in valueIcons:
                if arg is not None:
                    self.replaceChild(None, self.siteOf(arg))
            entryIcon.appendPendingArgs([valueIcons])
            self.replaceWith(entryIcon)
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, self.stmt)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'values_0':
            return self._becomeEntryIcon()
        return None

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
            if isinstance(site.att, infixicon.AsIcon):
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
        return ast.With(withItems, **bodyAsts, lineno=self.id, col_offset=0)

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
        bodyAsts = createBlockAsts(self)
        return ast.While(testAst, **bodyAsts, lineno=self.id, col_offset=0)

    def backspace(self, siteId, evt):
        if siteId != "condIcon":
            return None
        # Cursor is directly on condition site.  Remove icon and replace with entry
        # icon, converting condition to pending argument
        self.window.backspaceIconToEntry(evt, self, "while", "condIcon")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'while')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'while', 'condIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'values_0':
            return self.window.replaceIconWithEntry(self, 'while', 'condIcon')
        return None

class ForIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, isAsync=False, createBlockEnd=True, typeover=False,
            window=None, location=None):
        icon.Icon.__init__(self, window)
        if typeover:
            self.typeoverIdx = 0
            self.window.watchTypeover(self)
        else:
            self.typeoverIdx = None
        self.stmt = "async for" if isAsync else "for"
        bodyWidth = icon.getTextSize(self.stmt, icon.boldFont)[0]+2 * icon.TEXT_MARGIN+1
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
            txtImg = icon.iconBoxedText(self.stmt, icon.boldFont, icon.KEYWORD_COLOR)
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
            txtImg = icon.iconBoxedText("in", icon.boldFont, icon.KEYWORD_COLOR,
                typeover=self.typeoverIdx)
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
        tgtText = icon.seriesTextRepr(self.sites.targets)
        iterText = icon.seriesTextRepr(self.sites.iterIcons)
        return self.stmt + " " + tgtText + " in " + iterText + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.stmt + ' ')
        icon.addSeriesSaveText(text, brkLvl, self.sites.targets, contNeeded,
            export)
        text.add(brkLvl, " in ", contNeeded)
        icon.addSeriesSaveText(text, brkLvl, self.sites.iterIcons, contNeeded,
            export, allowTrailingComma=True)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "for"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.stmt == "async for",
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
        bodyAsts = createBlockAsts(self)
        return ast.For(tgtAst, valueAst, **bodyAsts, lineno=self.id,
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

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId is None or not iconsites.isSeriesSiteId(siteId):
            return None
        name, idx = iconsites.splitSeriesSiteId(siteId)
        if name != 'targets':
            return None
        if text[0] == '*' and entryIc.parent() == self:
            if text == '*':
                return listicons.StarIcon(self.window), None
            textStripped = text[:-1]
            delim = text[-1]
            if textStripped == '*' and entryicon.opDelimPattern.match(delim):
                return listicons.StarIcon(self.window), delim
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
        return self._placeArgsCommon(placeList, startSiteId, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, False)

    def _placeArgsCommon(self, placeList, startSiteId, doPlacement):
        # ForIcon has two lists: targets and iterIcons.  To properly reassemble the icon
        # from entry icon pending args, we take whatever is in the first element of
        # placement list (be it single input or series) as targets and the rest (that can
        # be placed) as iterIcons.  This uses the superclass placeArgs and canPlaceArgs
        # methods to do verification and placement, but feeds the two series separately.
        # This is somewhat complicated by the need to allow placement to start on the
        # iterIcons list if startSiteId is in that series.
        if len(placeList) == 0:
            return None, None
        if doPlacement:
            placeArgsCall = icon.Icon.placeArgs
        else:
            placeArgsCall = icon.Icon.canPlaceArgs
        tgtsStartId = 'targets_0'
        iterIconsStartId = 'iterIcons_0'
        tgts = placeList[:1]
        iterIcons = placeList[1:]
        if startSiteId is not None:
            startSeriesName, startSeriesIdx = iconsites.splitSeriesSiteId(startSiteId)
            if startSeriesName == 'targets':
                tgtsStartId = startSiteId
            elif startSeriesName == 'iterIcons':
                iterIconsStartId = startSiteId
                tgts = []
                iterIcons = placeList
            else:
                print('ForIcon.placeArgs: bad startSiteId')
                return None, None
        if len(tgts) != 0:
            placedIdx, placedSeriesIdx = placeArgsCall(self, tgts, tgtsStartId)
            if placedIdx is None:
                return None, None
            if len(iterIcons) == 0:
                return placedIdx, placedSeriesIdx
        placedIdx, placedSeriesIdx = placeArgsCall(self, iterIcons, iterIconsStartId)
        if placedIdx is None:
            return (0 if len(tgts) != 0 else None), None
        return placedIdx + len(tgts), placedSeriesIdx

    def setTypeover(self, idx, site=None):
        self.drawList = None  # Force redraw
        if idx is None or idx > 1:
            self.typeoverIdx = None
            return False
        self.typeoverIdx = idx
        return True

    def typeoverCursorPos(self):
        iterSite = self.sites.iterIcons[0]
        xOffset = iterSite.xOffset + icon.OUTPUT_SITE_DEPTH - icon.TEXT_MARGIN - \
            icon.getTextSize("in"[self.typeoverIdx:], icon.boldFont)[0]
        return xOffset, iterSite.yOffset

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        before = iconsites.makeSeriesSiteId('targets', len(self.sites.targets) - 1)
        retVal = before, 'iterIcons_0', 'in', self.typeoverIdx
        return [retVal] if allRegions else retVal

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        win = self.window
        if siteName == "targets":
            if index == 0:
                # Cursor is on first target site.  Remove icon and replace with entry
                # icon, converting both targets and iterators in to a flat list
                entryIcon = self._becomeEntryIcon()
                win.cursor.setToText(entryIcon, drawNew=False)
            else:
                # Cursor is on comma input
                listicons.backspaceComma(self, siteId, evt)
        elif siteName == "iterIcons":
            if index == 0:
                # Cursor is on "in", jump over it to last target
                lastTgtSite = iconsites.makeSeriesSiteId('targets',
                    len(self.sites.targets) - 1)
                win.cursor.setToIconSite(*icon.rightmostFromSite(self, lastTgtSite))
            else:
                # Cursor is on comma input
                listicons.backspaceComma(self, siteId, evt)

    def _becomeEntryIcon(self):
        win = self.window
        targetIcons = [s.att for s in self.sites.targets]
        iterIcons = [s.att for s in self.sites.iterIcons]
        if len(targetIcons) <= 1 and (len(iterIcons) == 0 or len(iterIcons) == 1 and
                iterIcons[0] is None):
            # Zero or one argument, convert to entry icon (with single pending arg if
            # there was an argument)
            if len(targetIcons) == 1:
                pendingArgSite = 'targets_0'
            else:
                pendingArgSite = None
            entryIcon = win.replaceIconWithEntry(self, self.stmt, pendingArgSite)
        else:
            # Multiple remaining arguments: convert to entry icon holding pending
            # arguments in the form of two lists: targets and values
            win.requestRedraw(self.topLevelParent().hierRect(),
                filterRedundantParens=True)
            entryIcon = entryicon.EntryIcon(initialString=self.stmt, window=win,
                willOwnBlock=True)
            if len(iterIcons) == 0:
                entryIcon.appendPendingArgs([targetIcons])
            else:
                entryIcon.appendPendingArgs([targetIcons, iterIcons])
            for arg in targetIcons + iterIcons:
                if arg is not None:
                    self.replaceChild(None, self.siteOf(arg))
            win.replaceTop(self, entryIcon)
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, self.stmt)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'targets_0':
            return self._becomeEntryIcon()
        return None

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

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

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
        bodyAsts = createBlockAsts(self)
        return ast.If(testAst, **bodyAsts, lineno=self.id, col_offset=0)

    def backspace(self, siteId, evt):
        if siteId != "condIcon":
            return None
        # Cursor is directly on condition site.  Remove icon and replace with entry
        # icon, converting condition to pending argument
        self.window.backspaceIconToEntry(evt, self, "if", "condIcon")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'if')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'if', 'condIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == "condIcon":
            return self.window.replaceIconWithEntry(self, 'if', 'condIcon')
        return None

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
        self.sites.add('seqInsert', 'seqInsert', seqX, siteYOffset)
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
        dedentAdj = icon.dragSeqImage.width + ELSE_DEDENT
        layout.updateSiteOffsets(self.sites.seqInsert, parentSiteDepthAdj=-dedentAdj)
        layout.doSubLayouts(self.sites.seqInsert, left + dedentAdj, top + height // 2)
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

    @staticmethod
    def _snapFn(ic, siteId):
        """Return True if sideId of ic is a sequence site within an if block (a suitable
        site for snapping an elif icon)"""
        if siteId != 'seqOut' or isinstance(ic, icon.BlockEnd):
            return False
        if isinstance(ic, IfIcon):
            return True
        seqStartIc = icon.findSeqStart(ic, toStartOfBlock=True)
        blockOwnerIcon = seqStartIc.childAt('seqIn')
        return isinstance(blockOwnerIcon, IfIcon)

    def snapLists(self, forCursor=False):
        # Make snapping conditional being within the block of an if statement
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        seqInsertSites = snapLists.get('seqInsert')
        if seqInsertSites is None:
            return snapLists
        snapLists['seqInsert'] = []
        snapLists['conditional'] = [(*seqInsertSites[0], 'seqInsert', self._snapFn)]
        return snapLists

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

    def backspace(self, siteId, evt):
        if siteId != "condIcon":
            return None
        # Cursor is directly on condition site.  Remove icon and replace with entry
        # icon, converting condition to pending argument
        self.window.backspaceIconToEntry(evt, self, "elif", "condIcon")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'elif')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'elif', 'condIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'condIcon':
            return self.window.replaceIconWithEntry(self, 'elif', 'condIcon')
        return None

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
        self.sites.add('seqInsert', 'seqInsert', seqX, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
            bodyHeight // 2 + icon.ATTR_SITE_OFFSET,
            cursorOnly=True)
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

    @staticmethod
    def _snapFn(ic, siteId):
        """Return True if sideId of ic is a sequence site within an if, for, or try block
        (a site suitible for snapping an else icon"""
        if siteId != 'seqOut' or isinstance(ic, icon.BlockEnd):
            return False
        if ic.__class__ in (IfIcon, ForIcon):
            return True
        seqStartIc = icon.findSeqStart(ic, toStartOfBlock=True)
        blockOwnerIcon = seqStartIc.childAt('seqIn')
        return blockOwnerIcon.__class__ in (IfIcon, ForIcon, WhileIcon, TryIcon)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being within the block of an if, for, or try stmt
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        seqInsertSites = snapLists.get('seqInsert')
        if seqInsertSites is None:
            return snapLists
        snapLists['seqInsert'] = []
        snapLists['conditional'] = [(*seqInsertSites[0], 'seqInsert', self._snapFn)]
        return snapLists

    def backspace(self, siteId, evt):
        if siteId != "attrIcon":
            return None
        self.window.backspaceIconToEntry(evt, self, "else")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'else')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'else')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, 'else')
        return None

    def textRepr(self):
        return "else:"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText("else:")

    def dumpName(self):
        return "else"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class TryIcon(icon.Icon):
    def __init__(self, createBlockEnd=True, window=None, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("try", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + comn.BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
            bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True)
        x, y = (0, 0) if location is None else location
        width = max(seqX + comn.BLOCK_INDENT + 2, bodyWidth + icon.dragSeqImage.width-1)
        self.rect = (x, y, x + width, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = icon.BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)
        self.exceptIcons = []

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
            txtImg = icon.iconBoxedText("try", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.seqInsert.yOffset
            icon.drawSeqSites(img, boxLeft, 0, txtImg.height, indent="right",
                extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage,
                        (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        bodyWidth, height = self.bodySize
        width = icon.dragSeqImage.width + max(comn.BLOCK_INDENT + 2, bodyWidth - 1)
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, height = self.bodySize
        width = icon.dragSeqImage.width + max(comn.BLOCK_INDENT + 2, bodyWidth - 1)
        layout = iconlayout.Layout(self, width, height, height // 2)
        return [layout]

    def select(self, select=True):
        icon.Icon.select(self, select)
        icon.Icon.select(self.blockEnd, select)

    def backspace(self, siteId, evt):
        if siteId != "attrIcon":
            return None
        self.window.backspaceIconToEntry(evt, self, "try")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'try')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'try')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, 'try')
        return None

    def textRepr(self):
        return "try:"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText("try:")

    def dumpName(self):
        return "try"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        bodyAsts = createBlockAsts(self)
        return ast.Try(**bodyAsts, lineno=self.id, col_offset=0)

class ExceptIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("except", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + icon.dragSeqImage.width - 1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('typeIcon', 'input', condXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', seqX, siteYOffset)
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
            txtImg = icon.iconBoxedText("except", icon.boldFont, icon.KEYWORD_COLOR)
            boxLeft = icon.dragSeqImage.width - 1
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.typeIcon.yOffset
            inImageY = cntrSiteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.typeIcon.xOffset, inImageY))
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
        dedentAdj = icon.dragSeqImage.width + ELSE_DEDENT
        layout.updateSiteOffsets(self.sites.seqInsert, parentSiteDepthAdj=-dedentAdj)
        layout.doSubLayouts(self.sites.seqInsert, left + dedentAdj, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        typeIcon = self.sites.typeIcon.att
        condLayouts = [None] if typeIcon is None else typeIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(condLayout, 'typeIcon', width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    @staticmethod
    def _snapFn(ic, siteId):
        """Return True if sideId of ic is a sequence site within a try block (a suitable
        site for snapping an except icon)"""
        if siteId != 'seqOut' or isinstance(ic, icon.BlockEnd):
            return False
        if isinstance(ic, TryIcon):
            return True
        seqStartIc = icon.findSeqStart(ic, toStartOfBlock=True)
        blockOwnerIcon = seqStartIc.childAt('seqIn')
        return isinstance(blockOwnerIcon, TryIcon)

    def snapLists(self, forCursor=False):
        # Make snapping conditional being within the block of a try statement
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        seqInsertSites = snapLists.get('seqInsert')
        if seqInsertSites is None:
            return snapLists
        snapLists['seqInsert'] = []
        snapLists['conditional'] = [(*seqInsertSites[0], 'seqInsert', self._snapFn)]
        return snapLists

    def backspace(self, siteId, evt):
        if siteId != "typeIcon":
            return None
        # Cursor is directly on type site.  Remove icon and replace with entry
        # icon, converting typeIcon to pending argument
        self.window.backspaceIconToEntry(evt, self, "except", "typeIcon")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'except')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'except', 'typeIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'typeIcon':
            return self.window.replaceIconWithEntry(self, 'except', 'typeIcon')
        return None

    def textRepr(self):
        return "except " + icon.argTextRepr(self.sites.typeIcon) + ":"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        if self.sites.typeIcon.att is None:
            return filefmt.SegmentedText("except:")
        text = filefmt.SegmentedText("except ")
        icon.addArgSaveText(text, brkLvl, self.sites.typeIcon, contNeeded, export)
        text.add(None, ":")
        return text

    def dumpName(self):
        return "except"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class FinallyIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = icon.getTextSize("finally", icon.boldFont)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        seqX = icon.dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', seqX, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
            bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True)
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
            txtImg = icon.iconBoxedText("finally", icon.boldFont, icon.KEYWORD_COLOR)
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

    def backspace(self, siteId, evt):
        if siteId != "attrIcon":
            return None
        self.window.backspaceIconToEntry(evt, self, "finally")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'finally')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, 'finally')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, 'finally')
        return None

    def textRepr(self):
        return "finally:"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText("finally:")

    def dumpName(self):
        return "finally"

class DefOrClassIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, text, hasArgs, createBlockEnd=True, window=None, typeover=False,
            location=None):
        icon.Icon.__init__(self, window)
        self.text = text
        self.hasArgs = hasArgs
        if typeover and hasArgs:
            self.lParenTypeover = True
            self.rParenTypeover = True
            self.window.watchTypeover(self)
        else:
            self.lParenTypeover = False
            self.rParenTypeover = False
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
        self.nameWidth = icon.EMPTY_ARG_WIDTH
        if hasArgs:
            lParenWidth = defLParenImage.width
            argX = icon.dragSeqImage.width + bodyWidth + self.nameWidth + lParenWidth
            self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', argX, siteYOffset,
                cursorTraverseOrder=1)
            rParenWidth = defRParenImage.width
            totalWidth = argX + self.argList.width + rParenWidth - 3
            self.sites.add('attrIcon', 'attrIn', totalWidth,
                bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True,
                cursorTraverseOrder=2)
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
            if self.hasArgs:
                # Open Paren
                lParenOffset = bodyOffset + bodyWidth - 1 + self.nameWidth - 1
                lParenImg = defLParenTypeoverImage if self.lParenTypeover else \
                    defLParenImage
                lParenImg = icon.yStretchImage(lParenImg,
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
                rParenImg = defRParenTypeoverImage if self.rParenTypeover else \
                    defRParenImage
                rParenImg = icon.yStretchImage(rParenImg, defRParenExtendDupRows,
                    self.argList.spineHeight)
                self.drawList.append(((rParenOffset, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def argIcons(self):
        if not self.hasArgs:
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
        if not self.hasArgs:
            height = bodyHeight
            centerY = bodyHeight // 2 + 1
        else:
            self.argList.doLayout(layout)
            width += defLParenImage.width - 1 + self.argList.width - 1 + \
                    defRParenImage.width
            height = self.argList.spineHeight
            centerY = self.argList.spineTop
            self.sites.attrIcon.xOffset = width - icon.ATTR_SITE_DEPTH
            self.sites.attrIcon.yOffset = centerY + icon.ATTR_SITE_OFFSET
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
        argListLayouts = self.argList.calcLayouts() if self.hasArgs else [None]
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
        if not self.hasArgs:
            return text
        return text + "(" + icon.seriesTextRepr(self.sites.argIcons) + "):"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.text + " ")
        icon.addArgSaveText(text, brkLvl, self.sites.nameIcon, contNeeded, export)
        if not self.hasArgs:
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
        if self.hasArgs:
            return
        self.hasArgs = True
        argX = comn.rectWidth(self.rect)
        argY = self.sites.nameIcon.yOffset
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', argX, argY,
            cursorTraverseOrder=1)
        self.sites.add('attrIcon', 'attrIn', cursorOnly=True, cursorTraverseOrder=2)
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.removeArgs)

    def removeArgs(self):
        if not self.hasArgs:
            return
        self.hasArgs = False
        if len(self.argIcons()) > 0:
            print("trying to remove non-empty argument list")
            return
        seriesLen = len(self.sites.argIcons)
        if seriesLen > 1:
            # While callers are accustomed to removing arguments, they won't
            # necessarily remove the empty sites, and we need them gone, because our
            # undo callback, addArgs, does not restore sites.
            for _ in range(seriesLen):
                self.replaceChild(None, 'argIcons_0')
        self.argList = None
        self.sites.removeSeries('argIcons')
        self.sites.remove('attrIcon')
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.addArgs)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId == 'nameIcon':
            if text == '(':
                return "typeover"
            name = text.rstrip(' (')
            if not name.isidentifier():
                # The only valid text for a function or class name is an identifier
                return "reject"
            iconOnNameSite = self.sites.nameIcon.att
            if iconOnNameSite is entryIc:
                # Nothing but the entry icon is at the site, allow for typing leading
                # dots by explicitly accepting
                if text[-1] in (' ', '('):
                    return nameicons.IdentifierIcon(name, self.window), text[-1]
                return "accept"
            if onAttr:
                # No attributes or operators of any kind are allowed on argument names
                return "reject"
            return None
        elif siteId[:8] == 'argIcons':
            if text == '*' and not onAttr:
                return "accept"
            if text[0] == '*' and len(text) == 2 and (text[1].isalnum() or text[1] == ' '):
                return listicons.StarIcon(self.window), text[1]
            if text[:2] == '**':
                return listicons.StarStarIcon(self.window), None
            if text == '=' and onAttr:
                return listicons.ArgAssignIcon(self.window), None
            if not (text.isidentifier() or text in "), =" or \
                    text[:-1].isidentifier() and text[-1] in "), ="):
                # The only valid arguments are identifiers, *, **, =, and comma, *unless*
                # they are on the right side of argument assignment
                argAtSite = self.childAt(siteId)
                if argAtSite is None or not isinstance(argAtSite,
                        listicons.ArgAssignIcon):
                    return "reject"
            # Typeover for end-paren is handled by the general code
            return None
        else:
            return None

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if site is None or site == 'argIcons_0':
            self.lParenTypeover = idx is not None and idx == 0
        if site is None or site == 'attrIcon':
            self.rParenTypeover = idx is not None and idx == 0
        if site is None:
            return self.lParenTypeover or self.rParenTypeover
        if site == 'argIcons_0':
            return self.lParenTypeover
        if site == 'attrIcon':
            return self.rParenTypeover
        return False

    def typeoverSites(self, allRegions=False):
        lParenTo = rParenTo = None
        if self.hasArgs and self.lParenTypeover:
            lParenTo = 'nameIcon', 'argIcons_0', '(', 0
        if self.hasArgs and self.rParenTypeover:
            rParenTo = iconsites.makeSeriesSiteId('argIcons',
                len(self.sites.argIcons) - 1), 'attrIcon', ')', 0
        if allRegions:
            return [s for s in (lParenTo, rParenTo) if s is not None]
        if lParenTo:
            return lParenTo
        if rParenTo:
            return rParenTo
        return None, None, None, None

    def backspace(self, siteId, evt):
        win = self.window
        if siteId == "nameIcon":
            # Cursor is directly on def, open for editing
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon)
        elif siteId[:8] == 'argIcons':
            siteName, index = iconsites.splitSeriesSiteId(siteId)
            if index == 0:
                if isinstance(self, ClassDefIcon):
                    # Remove parens if that won't cause argument deletion, otherwise
                    # select remaining args that will need to be deleted to make
                    # deleting the parens possible
                    if self.argList is not None:
                        argIcons = [site.att for site in self.sites.argIcons \
                            if site.att is not None]
                        if len(argIcons) > 0:
                            self.window.unselectAll()
                            for arg in argIcons:
                                for i in arg.traverse():
                                    self.window.requestRedraw(i.rect)
                                    win.select(i)
                            return
                    self.removeArgs()
                # Move cursor (in the case of a function def, that's all we ever do)
                nameIcon = self.childAt('nameIcon')
                if nameIcon is None:
                    self.window.cursor.setToIconSite(self, 'nameIcon')
                else:
                    rightmostIc, rightmostSite = icon.rightmostSite(nameIcon)
                    self.window.cursor.setToIconSite(rightmostIc, rightmostSite)
            else:
                # Cursor is on a comma input
                listicons.backspaceComma(self, siteId, evt)
        elif siteId == 'attrIcon':
            # Cursor is on the right paren.  Mo reason to ever remove closing paren,
            # so just move the cursor inside.
            lastArgSite = self.sites.argIcons[-1].name
            lastArg = self.childAt(lastArgSite)
            if lastArg is None:
                self.window.cursor.setToIconSite(self, lastArgSite)
            else:
                rightmostIc, rightmostSite = icon.rightmostSite(lastArg)
                self.window.cursor.setToIconSite(rightmostIc, rightmostSite)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, self.text)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'nameIcon':
            return self._becomeEntryIcon()
        return None

    def _becomeEntryIcon(self):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        nameIcon = self.childAt('nameIcon')
        if self.hasArgs:
            argIcons = [site.att for site in self.sites.argIcons]
            if len(argIcons) == 1 and argIcons[0] is None:
                argIcons = None  # Empty first site means nothing in list
        else:
            argIcons = None
        entryIcon = entryicon.EntryIcon(window=self.window, initialString=self.text,
            willOwnBlock=self.nextInSeq() is not self.blockEnd)
        self.replaceWith(entryIcon)
        self.replaceChild(None, 'nameIcon')
        if argIcons is not None:
            for arg in argIcons:
                if arg is not None:
                    self.replaceChild(None, self.siteOf(arg))
        if self.hasArgs and (isinstance(nameIcon, nameicons.IdentifierIcon) and
                nameIcon.childAt('attrIcon') is None or nameIcon is None):
            # Dissolving in to a function call is weird, but it's slightly closer
            # to what the user originally typed (this may be a dumb idea, but I'm
            # going with it)
            callIcon = listicons.CallIcon(window=self.window, closed=True)
            if argIcons is not None and len(argIcons) > 0:
                callIcon.insertChildren(argIcons, 'argIcons', 0)
            if nameIcon is None:
                entryIcon.appendPendingArgs([callIcon])
            else:
                nameIcon.replaceChild(callIcon, 'attrIcon')
                entryIcon.appendPendingArgs([nameIcon])
        else:
            # If we can't dissolve in to a function call, put the name and args
            # in to separate pending arguments on the entry icon
            if argIcons is None or len(argIcons) == 0:
                entryIcon.appendPendingArgs([nameIcon])
            else:
                entryIcon.appendPendingArgs([nameIcon, argIcons])
        return entryIcon

class ClassDefIcon(DefOrClassIcon):
    def __init__(self, hasArgs=False, createBlockEnd=True, window=None, typeover=False,
            location=None):
        DefOrClassIcon.__init__(self, "class", hasArgs, createBlockEnd, window, typeover,
            location)

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
        return ast.ClassDef(nameIcon.name, bases, keywords=kwds, **bodyAsts,
         decorator_list=[], lineno=self.id, col_offset=0)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId == 'nameIcon':
            # The class def is drawn initially without parent-class parens.  When the
            # user types a paren in the appropriate place, have to turn those on
            if text == '(':
                self.addArgs()
                self.setTypeover(0, None)
                self.window.watchTypeover(self)
                return "typeover"
            # Let the parent handler enforce name
            return DefOrClassIcon.textEntryHandler(self, entryIc, text, onAttr)
        elif siteId[:8] == 'argIcons':
            # Enforce names only
            if not (text.isidentifier() or text in "), " or text[:-1].isidentifier() and \
                    text[-1] in "), "):
                # The only valid arguments are identifier and comma
                return "reject"
            # Typeover for end-paren is handled by the general code
            return None
        return None

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        # Sleazy hack: temporarily add argIcons site and then the method used for DefIcon
        # does exactly what we want for ClassDef.  Note that this is slightly different
        # from the placeArgs call which fully commits by calling addArgs to create a list
        # manager and an undo record, and then removes them based on the result of the
        # placement call.  Instead, this adds a site only (which has less overhead), and
        # then removes it afterward.  This is still sleazy due to the odd state we're
        # putting the icon in (weird temporary site) and use of the DefIcon method.
        siteAdded = False
        if not self.hasArgs:
            self.sites.addSeries('argIcons', 'input')
            siteAdded = True
        rv = _defPlaceArgsCommon(self, placeList, startSiteId, overwriteStart, False)
        if siteAdded:
            self.sites.removeSeries('argIcons')
        return rv

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        # Sleazy hack: if placeList is longer than one entry or starts beyond the name
        # field, assume we're going to require a superclass list and add it, then use
        # the function-def method to place arguments.  The sleazy part is that 1) we're
        # using a method meant for something else, and 2) we may be wrong about needing
        # to create the superclass list parens, in which case we have to pull them back
        # off, unnecessarily bloating the undo list and generally wasting cycles.
        if len(placeList) == 0:
            return None, None
        siteAdded = False
        startAtName = startSiteId is None or startSiteId == 'nameIcon'
        numArgs = len(list(icon.placementListIter(placeList, includeEmptySites=True)))
        if not self.hasArgs and (numArgs > 1 or not startAtName or
                isinstance(placeList[0], nameicons.IdentifierIcon) and
                isinstance(placeList[0].childAt('attrIcon'), listicons.CallIcon)):
            self.addArgs()
            siteAdded = True
        rv = _defPlaceArgsCommon(self, placeList, startSiteId, overwriteStart, True)
        if siteAdded:
            for site in self.sites.argIcons:
                if site.att is not None:
                    break
            else:
                self.removeArgs()
        return rv

class DefIcon(DefOrClassIcon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, typeover=False,
            location=None):
        self.isAsync = isAsync
        text = "async def" if isAsync else "def"
        DefOrClassIcon.__init__(self, text, True, createBlockEnd, window, typeover,
            location)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync,
         createBlockEnd=False)

    def createAst(self):
        nameIcon = self.sites.nameIcon.att
        if nameIcon is None:
            raise icon.IconExecException(self, "Definition missing function name")
        if not isinstance(nameIcon, nameicons.IdentifierIcon):
            raise icon.IconExecException(nameIcon, "Argument name must be identifier")
        argumentAsts = _createFnDefArgsAst(self.sites.argIcons)
        bodyAsts = createBlockAsts(self)
        if self.isAsync:
            return ast.AsyncFunctionDef(nameIcon.name, argumentAsts, **bodyAsts,
             decorator_list=[], returns=None, lineno=self.id, col_offset=0)
        return ast.FunctionDef(nameIcon.name, argumentAsts, **bodyAsts,
         decorator_list=[], returns=None, lineno=self.id, col_offset=0)

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return _defPlaceArgsCommon(self, placeList, startSiteId, overwriteStart,
            True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return _defPlaceArgsCommon(self, placeList, startSiteId, overwriteStart,
            False)

class LambdaIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, window=None, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        self.colonTypeover = typeover
        if typeover:
            self.window.watchTypeover(self)
        bodyWidth = icon.getTextSize('lambda', icon.boldFont)[0] + 2*icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.colonWidth = lambdaColonImage.width - icon.inSiteImage.width + 1
        argX = icon.inSiteImage.width - 1 + bodyWidth
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', argX, siteYOffset,
            simpleSpine=True)
        totalWidth = argX + self.argList.width + self.colonWidth
        self.sites.add('exprIcon', 'input', totalWidth, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
                self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            bodyLeft = icon.outSiteImage.width - 1
            bodyWidth, bodyHeight = self.bodySize
            img = Image.new('RGBA', (bodyLeft + bodyWidth, bodyHeight),
                color=(0, 0, 0, 0))
            textImg = icon.iconBoxedText("lambda", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(textImg, (bodyLeft, 0))
            if needOutSite:
                outImageY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (0, outImageY))
            if needSeqSites:
                icon.drawSeqSites(img, bodyLeft, 0, bodyHeight + 1)
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if arg-list has multi-row layout)
            argsOffset = bodyLeft + bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.argList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.argList.drawListCommas(bodyWidth - 1,
                self.sites.output.yOffset)
            # Colon
            colonImg = lambdaColonTypeoverImage if self.colonTypeover else \
                lambdaColonImage
            colonX = bodyLeft + bodyWidth - 1 + self.argList.width - 1
            self.drawList.append(((colonX, bodyTopY), colonImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def argIcons(self):
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        listicons.restoreConditionalTargets(self, siteSnapLists,
            (listicons.StarIcon, listicons.StarStarIcon, listicons.ArgAssignIcon))
        return siteSnapLists

    def doLayout(self, outSiteX, outSiteY, layout):
        self.argList.doLayout(layout)
        bodyWidth, bodyHeight = self.bodySize
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        width = icon.outSiteImage.width - 1 + bodyWidth - 1 + self.argList.width - 1 + \
            self.colonWidth - 1
        if self.argList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.argList.spineTop)
            heightBelow = max(heightBelow, self.argList.spineHeight -
                    self.argList.spineTop)
        self.sites.output.yOffset = heightAbove
        self.sites.exprIcon.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        height = heightAbove + heightBelow
        left = outSiteX - self.sites.output.xOffset
        top = outSiteY - self.sites.output.yOffset
        self.rect = left, top, left + width, top + height
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, left, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        argListLayouts = self.argList.calcLayouts()
        exprIcon = self.sites.exprIcon.att
        exprLayouts = [None] if exprIcon is None else exprIcon.calcLayouts()
        cntrYOff = bodyHeight // 2
        layouts = []
        for argListLayout, exprLayout in iconlayout.allCombinations(
                (argListLayouts, exprLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, cntrYOff)
            argListLayout.mergeInto(layout, bodyWidth - 1, 0)
            exprXOff = bodyWidth + argListLayout.width - 1 + self.colonWidth
            layout.addSubLayout(exprLayout, 'exprIcon', exprXOff, 0)
            exprWidth = icon.EMPTY_ARG_WIDTH if exprLayout is None else exprLayout.width
            layout.width = exprXOff + exprWidth - 1
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        exprIcon = self.sites.exprIcon.att
        exprText = '' if exprIcon is None else exprIcon.textRepr()
        return 'lambda ' + icon.seriesTextRepr(self.sites.argIcons) + ':' + exprText

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('lambda ')
        icon.addSeriesSaveText(text, brkLvl, self.sites.argIcons, contNeeded, export)
        text.add(None, ": ")
        icon.addArgSaveText(text, brkLvl, self.sites.exprIcon, contNeeded, export)
        return text

    def dumpName(self):
        return "lambda"

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + icon.outSiteImage.width - 1
        bodyWidth, bodyHeight = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:8] == 'argIcons':
            if text == '*' and not onAttr:
                return "accept"
            if text[0] == '*' and len(text) == 2 and (text[1].isalnum() or text[1] == ' '):
                return listicons.StarIcon(self.window), text[1]
            if text[:2] == '**':
                return listicons.StarStarIcon(self.window), None
            if text == '=' and onAttr:
                return listicons.ArgAssignIcon(self.window), None
            if text[-1] == ':':
                rightmostArgSite = self.sites.argIcons[-1].name
                rightmostIc, _ = icon.rightmostFromSite(self, rightmostArgSite)
                acceptTypeover = rightmostIc is entryIc and self.colonTypeover
                if text == ':' and acceptTypeover:
                    return 'typeover'
            else:
                acceptTypeover = False
            if not (text.isidentifier() or text in "), =" or \
                    text[:-1].isidentifier() and (text[-1] in "), =") or
                    text[-1] == ':' and acceptTypeover):
                # The only valid arguments are identifiers, *, **, =, and comma, *unless*
                # they are on the right side of argument assignment or a typeover colon
                argAtSite = self.childAt(siteId)
                if argAtSite is None or not isinstance(argAtSite,
                        listicons.ArgAssignIcon):
                    return "reject"
        return None

    def createAst(self):
        exprIcon = self.sites.exprIcon.att
        if exprIcon is None:
            raise icon.IconExecException(self, "Lambda missing body expression")
        argumentAsts = _createFnDefArgsAst(self.sites.argIcons)
        return ast.Lambda(argumentAsts, exprIcon.createAst(),  lineno=self.id,
            col_offset=0)

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if site is None or site == 'exprIcon':
            self.colonTypeover = idx is not None and idx == 0
            return self.colonTypeover
        return False

    def typeoverSites(self, allRegions=False):
        rVals = None, None, None, None
        if self.colonTypeover:
            rVals = iconsites.makeSeriesSiteId('argIcons',
                len(self.sites.argIcons) - 1), 'exprIcon', ':', 0
        if allRegions:
            return [rVals]
        return rVals

    def backspace(self, siteId, evt):
        win = self.window
        if siteId[:8] == 'argIcons':
            siteName, index = iconsites.splitSeriesSiteId(siteId)
            if index == 0:
                # Cursor is on body of icon: edit its text
                entryIcon = self._becomeEntryIcon()
                self.window.cursor.setToText(entryIcon, drawNew=False)
            else:
                # Cursor is on a comma input
                listicons.backspaceComma(self, siteId, evt)
        elif siteId == 'exprIcon':
            # Cursor is on the colon.  Move the cursor inside.
            lastArgSite = self.sites.argIcons[-1].name
            lastArg = self.childAt(lastArgSite)
            if lastArg is None:
                self.window.cursor.setToIconSite(self, lastArgSite)
            else:
                rightmostIc, rightmostSite = icon.rightmostSite(lastArg)
                self.window.cursor.setToIconSite(rightmostIc, rightmostSite)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.outSiteImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, "lambda")
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'argIcons_0':
            return self._becomeEntryIcon()
        return None

    def _becomeEntryIcon(self):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        entryIcon = entryicon.EntryIcon(window=self.window, initialString='lambda')
        self.replaceWith(entryIcon)
        argIcons = self.argIcons()
        if len(argIcons) == 1 and argIcons[0] is None:
            argIcons = []
        for arg in argIcons:
            if arg is not None:
                self.replaceChild(None, self.siteOf(arg))
        exprIcon = self.sites.exprIcon.att
        if exprIcon is not None:
            self.replaceChild(None, 'exprIcon')
        # Put the args into a call icon and expression in to a separate pending argument
        if len(argIcons) > 0 or exprIcon is not None:
            callIcon = listicons.CallIcon(self.window)
            callIcon.insertChildren(argIcons, 'argIcons', 0)
            if len(argIcons) > 0 and exprIcon is None:
                entryIcon.appendPendingArgs([callIcon])
            else:
                entryIcon.appendPendingArgs([callIcon, exprIcon])
        return entryIcon

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        if startSiteId is None:
            startSiteId = 'argIcons_0'
        compressedPL = [ic for ic in icon.placementListIter(placeList,
            includeEmptySeriesSites=False)]
        if startSiteId == 'argIcons_0' and (len(compressedPL) == 1 or
                len(compressedPL) == 2 and
                compressedPL[1][0].hasSite('output')) and \
                isinstance(compressedPL[0][0], listicons.CallIcon) \
                and (overwriteStart or not self.childAt('argIcons_0')):
            # placeList is in a format at least close to what _becomeEntryIcon, above,
            # would create, or possibly an edited version of a function def icon.
            # Reconstruct it to match the original
            callIcon = compressedPL[0][0]
            callAttrIcon = callIcon.childAt('attrIcon')
            if doPlacement:
                if overwriteStart:
                    self.replaceChild(None, 'argIcons_0')
                argList = callIcon.argIcons()
                self.insertChildren(argList, 'argIcons', 0)
                if callAttrIcon is not None:
                    # While the _becomeEntryIcon method will never attach an attribute
                    # to the call icon it creates, the user can subsequently do so (and
                    # is in fact, easy to do accidentally by changing the text of the
                    # lambda to a valid identifier).  We don't want it to disappear,
                    # so make an entry icon and put it on the exprIcon site.
                    callIcon.replaceChild(None, 'attrIcon')
                    if isinstance(callAttrIcon, entryicon.EntryIcon):
                        entryIc = callAttrIcon
                    else:
                        entryIc = entryicon.EntryIcon(window=self.window)
                        entryIc.appendPendingArgs([callAttrIcon])
                    self.replaceChild(entryIc, 'exprIcon')
                    entryIc.remove(makePlaceholder=True)
                elif len(compressedPL) == 2:
                    self.replaceChild(compressedPL[1][0], 'exprIcon')
            if callAttrIcon is not None:
                return compressedPL[0][1], compressedPL[0][2]
            else:
                return compressedPL[-1][1], compressedPL[-1][2]
        else:
            # We don't know what we have, let the root icon method do whatever it wants
            if doPlacement:
                return icon.Icon.placeArgs(self, placeList, startSiteId, overwriteStart)
            return icon.Icon.canPlaceArgs(self, placeList, startSiteId, overwriteStart)

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, False)

def _createFnDefArgsAst(argSiteList):
    posOnlyArgAsts = []
    normalArgAsts = []
    kwdOnlyAsts = []
    normalArgDefaults = []
    kwOnlyDefaults = []
    accumArgAsts = normalArgAsts
    accumArgDefaults = normalArgDefaults
    starArgAst = None
    starStarArgAst = None
    for site in argSiteList:
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
        elif isinstance(arg, nameicons.PosOnlyMarkerIcon):
            posOnlyArgAsts = normalArgAsts
            normalArgAsts = []
            accumArgAsts = normalArgAsts
        else:
            if not isinstance(arg, nameicons.IdentifierIcon):
                raise icon.IconExecException(arg, "Argument name must be identifier")
            accumArgAsts.append(ast.arg(arg.name, lineno=arg.id, col_offset=0))
    return ast.arguments(posOnlyArgAsts, normalArgAsts, starArgAst,
        kwdOnlyAsts, kwOnlyDefaults, starStarArgAst, normalArgDefaults)

def _defPlaceArgsCommon(ic, placeList, startSiteId, overwriteStart, doPlacement):
    # DefIcon has a name and an argument list.  The backspace method uses two
    # different methods to produce pending arguments for faithful reassembly: 1) the
    # name and arguments become a function call, 2) the name becomes the first
    # pending arg, followed by a series containing the parameter list.  As a fallback
    # we use the base-class method which blindly throws the first input in to the
    # name field and everything else in to the parameter list.  Also, if given a call
    # icon by itself, the method will place the argument list in the parameter list.
    # This makes it easier to edit a lambda expression to a function call.
    if len(placeList) == 0:
        return None, None
    placeArgsCall = icon.Icon.placeArgs if doPlacement else icon.Icon.canPlaceArgs
    startAtName = startSiteId is None or startSiteId[:8] == 'nameIcon'
    if startAtName and placeList[0] is None:
        # The base class code can almost do everything we need, but if the first site
        # is empty, it would skip ahead through the placement list and fill the name
        # from the first non-empty argument (so editing a def icon with an empty name
        # field, then focusing out, would mess up what was originally there).
        argIdx, argSeriesIdx = placeArgsCall(ic, placeList[1:], 'argIcons_0')
        return argIdx + 1, argSeriesIdx
    elif startAtName and (isinstance(placeList[0], nameicons.IdentifierIcon) and
            isinstance(placeList[0].childAt('attrIcon'), listicons.CallIcon) or
            isinstance(placeList[0], listicons.CallIcon)):
        # The first pending arg is a function call or a call icon by itself.
        if doPlacement:
            if isinstance(placeList[0], nameicons.IdentifierIcon):
                # The first pending arg is a function call
                callIcon = placeList[0].childAt('attrIcon')
                placeList[0].replaceChild(None, 'attrIcon')
                ic.replaceChild(placeList[0], 'nameIcon')
            else:
                # The first item in a call icon by itself: skip the name site and place
                # the arguments from the call icon in the parameter list.
                callIcon = placeList[0]
            args = callIcon.argIcons()
            attrIcon = callIcon.childAt('attrIcon')
            for arg in args:
                if arg is not None:
                    callIcon.replaceChild(None, callIcon.siteOf(arg))
            ic.insertChildren(args, 'argIcons', 0)
            if attrIcon is not None:
                # Call icon has an attribute and we don't have a usable attribute site:
                # move it to a new statement in our block (but since it's an attribute,
                # it will need an entry icon to adapt it).  Note afterward, the call to
                # entryIc.remove.  This handles the case where the attribute was already
                # an entry icon that may have been adapting an input site for the
                # attribute (exactly what happens when you backspace a lambda).
                callIcon.replaceChild(None, 'attrIcon')
                if isinstance(attrIcon, entryicon.EntryIcon):
                    entryIc = attrIcon
                else:
                    entryIc = entryicon.EntryIcon(window=ic.window)
                    entryIc.appendPendingArgs([attrIcon])
                icon.insertSeq(entryIc, ic)
                ic.window.addTopSingle(entryIc)
                entryIc.remove(makePlaceholder=True)
        return 0, None
    # None of the special cases applied, so use the base class method to fill in the
    # name and argument list.
    return placeArgsCall(ic, placeList, startSiteId, overwriteStart=overwriteStart)

def createBlockAsts(ic):
    """Create ASTs for icons in the block belonging to ic.  Returns a dictionary mapping
    ast parameter (body, orelse, handlers, finalbody) to body asts.  Normally, the
    dictionary simply contains {'body':[body-asts...]}, but if the icon has clauses
    (elif, else, except, finally), then the ast parameters associated with them are also
    filled in."""
    paramDict = {}
    blockType = 'body'
    stmtAsts = []
    handlerIcs = []
    stmt = ic.nextInSeq()
    while not isinstance(stmt, icon.BlockEnd):
        if stmt is None:
            raise icon.IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            if ic.__class__ not in (IfIcon, ElifIcon):
                raise icon.IconExecException(stmt, "Elif statement should not be here")
            # Python does not have an elif ast, instead, it creates an if embedded in
            # an orelse block.  Make recursive callback to collect body and orelse for
            # the embedded if (which may, themselves embed deeper elifs and elses), and
            # then return immediately as the recursive call will finish the block
            subsequentBlockAsts = createBlockAsts(stmt)
            ifAst = ast.If(stmt.sites.condIcon.att.createAst(), **subsequentBlockAsts,
                lineno=stmt.id, col_offset=0)
            return {'body':stmtAsts, 'orelse':[ifAst]}
        elif isinstance(stmt, ElseIcon):
            if ic.__class__ not in (IfIcon, ElifIcon, ForIcon, WhileIcon, TryIcon):
                raise icon.IconExecException(stmt, "Else statement should not be here")
            paramDict[blockType] = stmtAsts
            blockType = 'orelse'
            stmtAsts = []
        elif isinstance(stmt, FinallyIcon):
            if not isinstance(ic, TryIcon):
                raise icon.IconExecException(stmt, "finally statement should not be here")
            paramDict[blockType] = stmtAsts
            blockType = 'finalbody'
            stmtAsts = []
        elif isinstance(stmt, ExceptIcon):
            if not isinstance(ic, TryIcon):
                raise icon.IconExecException(stmt, "except statement should not be here")
            paramDict[blockType] = stmtAsts
            blockType = 'handler%d' % len(handlerIcs)
            handlerIcs.append(stmt)
            stmtAsts = []
        else:
            stmtAsts.append(icon.createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    paramDict[blockType] = stmtAsts
    if isinstance(ic, TryIcon):
        _consolidateHandlerBlocks(paramDict, handlerIcs)
    return paramDict

def _consolidateHandlerBlocks(paramDict, handlerIcs):
    """createBlockAsts puts each except clause block of a try statement in a separate
    entry (indexed as "handler0", "handler1", ...) in paramDict.  To create the handler
    list for the try statement AST, this function combines each of these blocks with an
    ast generated from the corresponding except statement (from handlerIcs), in to a
    single list of ast.ExceptHandlers indexed as "handlers"."""
    handlers = []
    for i, ic in enumerate(handlerIcs):
        typeIcon = ic.sites.typeIcon.att
        name = None
        if typeIcon is None:
            typeAst = None
        else:
            name = None
            if isinstance(typeIcon, infixicon.AsIcon):
                nameIcon = typeIcon.rightArg()
                if nameIcon is None:
                    raise icon.IconExecException(ic, "except as missing name")
                if not isinstance(nameIcon, nameicons.IdentifierIcon):
                    raise icon.IconExecException(ic, "except name is not identifier")
                name = nameIcon.name
                typeIcon = typeIcon.leftArg()
                if typeIcon is None:
                    raise icon.IconExecException(ic, "except statement missing type")
            typeAst = typeIcon.createAst()
        paramDictKey = 'handler%d' % i
        body = paramDict[paramDictKey]
        del paramDict[paramDictKey]
        handlerAst = ast.ExceptHandler(type=typeAst, name=name, body=body)
        handlers.append(handlerAst)
    paramDict['handlers'] = handlers

def clauseBlockIcons(ic):
    """Returns a list of all icons (hierarchy) in an else or elif clause, including
    the else or elif icon itself."""
    seqIcons = list(ic.traverse())
    nestLevel = 0
    for seqIcon in icon.traverseSeq(ic, includeStartingIcon=False):
        if isinstance(seqIcon, icon.BlockEnd):
            if nestLevel <= 0:
                break
            nestLevel -= 1
        elif hasattr(seqIcon, 'blockEnd'):
            nestLevel += 1
        elif seqIcon.__class__ in (ElifIcon, ElseIcon, ExceptIcon, FinallyIcon) and \
                nestLevel == 0:
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
        iterIcons = [icon.createFromAst(i, window) for i in astNode.iter.elts]
        topIcon.insertChildren(iterIcons, "iterIcons", 0)
        if len(iterIcons) == 1:
            topIcon.insertChild(None, "iterIcons", 1)
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

def createTryIconFromAst(astNode, window):
    return TryIcon(window=window)
icon.registerIconCreateFn(ast.Try, createTryIconFromAst)

def createDefIconFromAst(astNode, window):
    isAsync = astNode.__class__ is ast.AsyncFunctionDef
    defIcon = DefIcon(isAsync, window=window)
    nameIcon = nameicons.IdentifierIcon(astNode.name, window)
    defIcon.replaceChild(nameIcon, 'nameIcon')
    _addFnDefArgs(defIcon, astNode.args)
    return defIcon
icon.registerIconCreateFn(ast.FunctionDef, createDefIconFromAst)
icon.registerIconCreateFn(ast.AsyncFunctionDef, createDefIconFromAst)

def createLambdaIconFromAst(astNode, window):
    defIcon = LambdaIcon(window=window)
    _addFnDefArgs(defIcon, astNode.args)
    exprIcon = icon.createFromAst(astNode.body, window)
    defIcon.replaceChild(exprIcon, 'exprIcon')
    return defIcon
icon.registerIconCreateFn(ast.Lambda, createLambdaIconFromAst)

def _addFnDefArgs(defIcon, astNodeArgs):
    if hasattr(astNodeArgs, 'posonlyargs'):
        args = [arg.arg for arg in astNodeArgs.posonlyargs]
    else:
        args = []
    nPosOnly = len(args)
    window = defIcon.window
    defaults = [icon.createFromAst(e, window) for e in astNodeArgs.defaults]
    if len(defaults) < len(astNodeArgs.args):
        # Weird rule in defaults list for ast that defaults can be shorter than args
        defaults = ([None] * (len(astNodeArgs.args) - len(defaults))) + defaults
    numArgs = 0
    for i, arg in enumerate(arg.arg for arg in astNodeArgs.args):
        default = defaults[i]
        argNameIcon = nameicons.IdentifierIcon(arg, window)
        if nPosOnly != 0 and numArgs == nPosOnly:
            posOnlyMarker = nameicons.PosOnlyMarkerIcon(window=window)
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
    varArg = astNodeArgs.vararg.arg if astNodeArgs.vararg is not None else None
    if varArg is not None:
        argNameIcon = nameicons.IdentifierIcon(varArg, window)
        starIcon = listicons.StarIcon(window)
        starIcon.replaceChild(argNameIcon, 'argIcon')
        defIcon.insertChild(starIcon, 'argIcons', numArgs)
        numArgs += 1
    kwOnlyArgs = [arg.arg for arg in astNodeArgs.kwonlyargs]
    kwDefaults = [icon.createFromAst(e, window) for e in astNodeArgs.kw_defaults]
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
    if astNodeArgs.kwarg is not None:
        argNameIcon = nameicons.IdentifierIcon(astNodeArgs.kwarg.arg, window)
        starStarIcon = listicons.StarStarIcon(window)
        starStarIcon.replaceChild(argNameIcon, 'argIcon')
        defIcon.insertChild(starStarIcon, 'argIcons', numArgs)

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
            asIcon = infixicon.AsIcon(window)
            asIcon.replaceChild(contextIcon, "leftArg")
            asIcon.replaceChild(icon.createFromAst(item.optional_vars, window),
                "rightArg")
            topIcon.insertChild(asIcon, "values", idx)
    return topIcon
icon.registerIconCreateFn(ast.With, createWithIconFromAst)
icon.registerIconCreateFn(ast.AsyncWith, createWithIconFromAst)

def createIconsFromBodyAst(bodyAst, window):
    icons = []
    for stmt in bodyAst:
        if isinstance(stmt, (ast.FunctionDef, ast.ClassDef)):
            # Process decorators
            for decorator in stmt.decorator_list:
                if hasattr(decorator, 'linecomments'):
                    _addLineCommentIcons(decorator.linecomments, window, icons)
                decoratorIc = _createDecoratorIconFromAst(decorator, window)
                if hasattr(decorator, 'stmtcomment'):
                    _addStmtComment(decoratorIc, decorator.stmtcomment)
                if len(icons) > 0:
                    if icons[-1].hasSite('seqOut'):
                        icons[-1].sites.seqOut.attach(icons[-1], decoratorIc, 'seqIn')
                icons.append(decoratorIc)
        if hasattr(stmt, 'linecomments'):
            _addLineCommentIcons(stmt.linecomments, window, icons)
        if isinstance(stmt, ast.Expr):
            stmtIcon = icon.createFromAst(stmt.value, window)
            bodyIcons = None
        elif stmt.__class__ in blockStmts:
            stmtIcon = icon.createFromAst(stmt, window)
            bodyIcons = createIconsFromBodyAst(stmt.body, window)
            stmtIcon.sites.seqOut.attach(stmtIcon, bodyIcons[0], 'seqIn')
            if isinstance(stmt, ast.Try):
                # Process except blocks
                for handlerIdx, handler in enumerate(stmt.handlers):
                    lineCommentProp = 'exceptlinecomments' + str(handlerIdx)
                    if hasattr(stmt, lineCommentProp):
                        _addLineCommentIcons(getattr(stmt, lineCommentProp), window,
                            bodyIcons)
                    exceptIcon = ExceptIcon(window)
                    stmtCommentProp = 'exceptstmtcomment' + str(handlerIdx)
                    if hasattr(stmt, stmtCommentProp):
                        _addStmtComment(exceptIcon, getattr(stmt, stmtCommentProp))
                    if handler.type is not None:
                        typeIcon = icon.createFromAst(handler.type, window)
                        if handler.name is not None:
                            asIcon = infixicon.AsIcon(window)
                            nameIcon = nameicons.IdentifierIcon(handler.name, window)
                            asIcon.replaceChild(typeIcon, 'leftArg')
                            asIcon.replaceChild(nameIcon, 'rightArg')
                            exceptIcon.replaceChild(asIcon, 'typeIcon')
                        else:
                            exceptIcon.replaceChild(typeIcon, 'typeIcon')
                    bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], exceptIcon, 'seqIn')
                    bodyIcons.append(exceptIcon)
                    exceptBlockIcons = createIconsFromBodyAst(handler.body, window)
                    exceptIcon.sites.seqOut.attach(exceptIcon, exceptBlockIcons[0], 'seqIn')
                    bodyIcons += exceptBlockIcons
            while stmt.__class__ is ast.If and len(stmt.orelse) == 1 and \
                    stmt.orelse[0].__class__ is ast.If:
                # Process elif blocks.  The ast encodes these as a single if, nested
                # in and else (nested as many levels deep as there are elif clauses).
                if hasattr(stmt, 'elselinecomments'):
                    _addLineCommentIcons(stmt.elselinecomments, window, bodyIcons)
                elifIcon = ElifIcon(window)
                if hasattr(stmt, 'elsestmtcomment'):
                    _addStmtComment(elifIcon, stmt.elsestmtcomment)
                condIcon = icon.createFromAst(stmt.orelse[0].test, window)
                elifIcon.replaceChild(condIcon, 'condIcon')
                elifBlockIcons = createIconsFromBodyAst(stmt.orelse[0].body, window)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elifIcon, 'seqIn')
                bodyIcons.append(elifIcon)
                elifIcon.sites.seqOut.attach(elifIcon, elifBlockIcons[0], 'seqIn')
                bodyIcons += elifBlockIcons
                if hasattr(stmt, 'stmtcomment'):
                    _addStmtComment(stmtIcon, stmt.stmtcomment)
                stmt = stmt.orelse[0]
            if stmt.__class__ in (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try) and \
                    len(stmt.orelse) != 0:
                # Process else block (note that after elif processing above, stmt may in
                # some cases point to a nested statement being flattened out)
                if hasattr(stmt, 'elselinecomments'):
                    _addLineCommentIcons(stmt.elselinecomments, window, bodyIcons)
                elseIcon = ElseIcon(window)
                if hasattr(stmt, 'elsestmtcomment'):
                    _addStmtComment(elseIcon, stmt.elsestmtcomment)
                elseBlockIcons = createIconsFromBodyAst(stmt.orelse, window)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], elseIcon, 'seqIn')
                bodyIcons.append(elseIcon)
                elseIcon.sites.seqOut.attach(elseIcon, elseBlockIcons[0], 'seqIn')
                bodyIcons += elseBlockIcons
            if isinstance(stmt, ast.Try) and len(stmt.finalbody) != 0:
                if hasattr(stmt, 'finallylinecomments'):
                    _addLineCommentIcons(stmt.finallylinecomments, window, bodyIcons)
                finallyIcon = FinallyIcon(window)
                if hasattr(stmt, 'finallystmtcomment'):
                    _addStmtComment(finallyIcon, stmt.finallystmtcomment)
                finallyBlockIcons = createIconsFromBodyAst(stmt.finalbody, window)
                bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], finallyIcon, 'seqIn')
                bodyIcons.append(finallyIcon)
                finallyIcon.sites.seqOut.attach(finallyIcon, finallyBlockIcons[0], 'seqIn')
                bodyIcons += finallyBlockIcons
            blockEnd = stmtIcon.blockEnd
            bodyIcons[-1].sites.seqOut.attach(bodyIcons[-1], blockEnd, 'seqIn')
            bodyIcons.append(blockEnd)
        else:
            stmtIcon = icon.createFromAst(stmt, window)
            bodyIcons = None
        if hasattr(stmt, 'stmtcomment'):
            _addStmtComment(stmtIcon, stmt.stmtcomment)
        if len(icons) > 0:
            if icons[-1].hasSite('seqOut') and stmtIcon.hasSite('seqIn'):
                # Link the statement to the previous statement
                icons[-1].sites.seqOut.attach(icons[-1], stmtIcon, 'seqIn')
            else:
                print('Cannot link icons (no sequence sites)')  # Shouldn't happen
        icons.append(stmtIcon)
        if bodyIcons is not None:
            icons += bodyIcons
    return icons

def _createDecoratorIconFromAst(decoratorAst, window):
    if isinstance(decoratorAst, ast.Name):
        decoratorIc = nameicons.DecoratorIcon(decoratorAst.id, window)
    else:  # decoratorAst is ast.Call
        decoratorIc = nameicons.DecoratorIcon(decoratorAst.func.id, window)
        callIcon = listicons.createCallIconFromAst(decoratorAst, window)
        decoratorIc.replaceChild(callIcon, "attrIcon")
    return decoratorIc

def _addLineCommentIcons(commentList, window, sequence):
    # Comment list contains both line comments in form (annotation, text), and blank
    # lines (None, None)
    for annotation, text in commentList:
        if text is None:
            commentIcon = commenticon.VerticalBlankIcon(window)
        else:
            commentIcon = commenticon.CommentIcon(text, window=window, ann=annotation)
        if len(sequence) > 0:
            sequence[-1].sites.seqOut.attach(sequence[-1], commentIcon, 'seqIn')
        sequence.append(commentIcon)

def _addStmtComment(ic, comment):
    commentText = comment[1].replace('\\n', '\n')
    commentIcon = commenticon.CommentIcon(commentText, attachedToStmt=ic,
        window=ic.window, ann=comment[0])
    ic.stmtComment = commentIcon
    print('Attached stmt comment to %s (args %s): %s' %
          (ic.dumpName(), comment[0], comment[1]))
