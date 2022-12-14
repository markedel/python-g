# Copyright Mark Edel  All rights reserved
from PIL import Image
import ast
import numbers
import inspect
import comn
import iconlayout
import iconsites
import icon
import filefmt
import opicons
import listicons
import assignicons
import entryicon
import infixicon
import parenicon
import stringicon

namedConsts = {'True':True, 'False':False, 'None':None}

class TextIcon(icon.Icon):
    def __init__(self, text, window=None, location=None, cursorOnlyAttrSite=False):
        icon.Icon.__init__(self, window)
        self.text = text
        self.hasAttrIn = not cursorOnlyAttrSite
        bodyWidth, bodyHeight = icon.getTextSize(self.text)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
         bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=cursorOnlyAttrSite)
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + icon.outSiteImage.width, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
                comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText(self.text)
            img.paste(txtImg, (icon.outSiteImage.width - 1, 0))
            if needSeqSites:
                icon.drawSeqSites(img, icon.outSiteImage.width-1, 0, txtImg.height)
            if needOutSite:
                outX = self.sites.output.xOffset
                outY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (outX, outY))
            if self.hasAttrIn:
                attrX = self.sites.attrIcon.xOffset
                attrY = self.sites.attrIcon.yOffset
                img.paste(icon.attrInImage, (attrX, attrY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += icon.outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.drawList = None  # Draw or undraw sequence sites ... refine when sites added
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.attrIcon.att is None:
            attrLayouts = [None]
        else:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        width, height = self.bodySize
        layouts = []
        for attrLayout in attrLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(attrLayout, 'attrIcon', width-1, icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return self.text + icon.attrTextRepr(self)

    def dumpName(self):
        """Give the icon a name to be used in text dumps."""
        return self.text

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return icon.addAttrSaveText(filefmt.SegmentedText(self.text), self,
            parentBreakLevel, contNeeded, export)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, text=self.text)

    def backspace(self, siteId, evt):
        self.window.backspaceIconToEntry(evt, self, self.text, pendingArgSite=siteId)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.outSiteImage.width - 1
            textOriginY = self.rect[1] + self.sites.output.yOffset
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.globalFont, self.text)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, self.text, 'attrIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, self.text, 'attrIcon')
        return None

class IdentifierIcon(TextIcon):
    def __init__(self, name, window=None, location=None):
        TextIcon.__init__(self, name, window, location)
        self.name = name

    def execute(self):
        if self.name in namedConsts:
            value = namedConsts[self.name]
        elif self.name in globals():
            value = globals()[self.name]
        else:
            raise icon.IconExecException(self, self.name + " is not defined")
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(value)
        return value

    def createAst(self):
        if self.name in namedConsts:
            return ast.NameConstant(namedConsts[self.name], lineno=self.id, col_offset=0)
        ctx = determineCtx(self)
        identAst = ast.Name(self.name, ctx=ctx, lineno=self.id, col_offset=0)
        return icon.composeAttrAst(self, identAst)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

    def compareData(self, data):
        # Identifiers are considered code and rejected.  However, currently our only
        # representation for complex numbers is complex(real, imag), and those are
        # considered data.
        if self.name != 'complex':
            return False
        attr = self.sites.attrIcon.att
        if not isinstance(attr, listicons.CallIcon):
            return False
        if len(attr.sites.argIcons) != 2:
            return False
        realIconSite, imagIconSite = attr.sites.argIcons
        realIcon = realIconSite.att
        imagIcon = imagIconSite.att
        if not isinstance(realIcon, NumericIcon) or not isinstance(imagIcon, NumericIcon):
            return False
        if not isinstance(data, complex):
            return False
        return complex(realIcon.value, imagIcon.value) == data

class NumericIcon(TextIcon):
    def __init__(self, value, window=None, location=None):
        if type(value) is str:
            text = value
            value = ast.literal_eval(value)
        else:
            text = repr(value)
        TextIcon.__init__(self, text, window, location, cursorOnlyAttrSite=True)
        self.value = value

    def execute(self):
        return self.value

    def createAst(self):
        return ast.Num(self.value, lineno=self.id, col_offset=0)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, value=self.value)

    def compareData(self, data):
        return data == self.value

class CommentIcon(TextIcon):
    """Temporary class for displaying comments (move to commenticon.py)"""
    def __init__(self, text, window=None, location=None, args=None):
        TextIcon.__init__(self, '# ' + text, window, location)
        self.string = text
        self.wrap = args is not None and "w" in args

    def createAst(self):
        print("Creating AST for comment.  ...Try to prevent this from happening")
        return ast.Pass(lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        priorComment = isinstance(self.sites.seqIn.att, CommentIcon)
        text = filefmt.SegmentedText()
        text.addComment(self.string, priorComment)
        return text

class PosOnlyMarkerIcon(TextIcon):
    def __init__(self, window=None, location=None):
        TextIcon.__init__(self, '/', window, location)

class AttrIcon(icon.Icon):
    def __init__(self, name, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.name = name
        bodyWidth, bodyHeight = icon.getTextSize(self.name)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight = max(bodyHeight, icon.minTxtHgt) + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('attrOut', 'attrOut', 0, bodyHeight // 2 + icon.ATTR_SITE_OFFSET)
        self.sites.add('attrIcon', 'attrIn', bodyWidth - icon.ATTR_SITE_DEPTH,
         bodyHeight // 2 + icon.ATTR_SITE_OFFSET)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + icon.attrOutImage.width, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
             comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = icon.iconBoxedText(self.name)
            img.paste(txtImg, (icon.attrOutImage.width - 1, 0))
            attrOutX = self.sites.attrOut.xOffset
            attrOutY = self.sites.attrOut.yOffset
            img.paste(icon.attrOutImage, (attrOutX, attrOutY), mask=icon.attrOutImage)
            attrInX = self.sites.attrIcon.xOffset
            attrInY = self.sites.attrIcon.yOffset
            img.paste(icon.attrInImage, (attrInX, attrInY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        width, height = self.bodySize
        width += icon.attrOutImage.width - 1
        top = attrSiteY - (height // 2 + icon.ATTR_SITE_OFFSET)
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        layouts = []
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        for attrLayout in attrLayouts:
            layout = iconlayout.Layout(self, width, height,
                    height // 2 + icon.ATTR_SITE_OFFSET)
            layout.addSubLayout(attrLayout, 'attrIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return '.' + self.name + icon.attrTextRepr(self)

    def dumpName(self):
        return "." + self.name

    def execute(self, attrOfValue):
        try:
            result = getattr(attrOfValue, self.name)
        except Exception as err:
            raise icon.IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return icon.addAttrSaveText(filefmt.SegmentedText("." + self.name), self,
            parentBreakLevel, contNeeded, export)

    def createAst(self, attrOfAst):
        return icon.composeAttrAst(self, ast.Attribute(value=attrOfAst, attr=self.name,
         lineno=self.id, col_offset=0, ctx=determineCtx(self)))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

    def backspace(self, siteId, evt):
        self.window.backspaceIconToEntry(evt, self, '.' + self.name,
                pendingArgSite=siteId)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.attrOutImage.width - 1
            textOriginY = self.rect[1] + self.sites.attrOut.yOffset - \
                    icon.ATTR_SITE_OFFSET
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.globalFont, self.name)
            if cursorTextIdx is None:
                return None, None
            entryIc = self.window.replaceIconWithEntry(self, '.' + self.name, 'attrIcon')
            entryIc.setCursorPos(cursorTextIdx + 1)
            return entryIc, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, '.' + self.name, 'attrIcon')
        return None

class NoArgStmtIcon(icon.Icon):
    def __init__(self, stmt, window, location):
        icon.Icon.__init__(self, window)
        self.stmt = stmt
        bodyWidth = icon.getTextSize(stmt, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
            bodyHeight // 2 + icon.ATTR_SITE_OFFSET, cursorOnly=True)
        totalWidth = icon.dragSeqImage.width + bodyWidth
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

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
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = icon.dragSeqImage.width - 1
            txtImg = icon.iconBoxedText(self.stmt, icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            icon.drawSeqSites(img, bodyOffset, 0, txtImg.height)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, bodyHeight//2 -
                        icon.dragSeqImage.height//2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        bodyWidth, bodyHeight = self.bodySize
        width = icon.dragSeqImage.width - 1 + bodyWidth
        self.rect = (left, top, left + width, top + bodyHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        return [iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)]

    def textRepr(self):
        return self.stmt

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText(self.stmt)

    def dumpName(self):
        return self.stmt

    def execute(self):
        return None  #... no idea what to do here, yet.

    def backspace(self, siteId, evt):
        self.window.backspaceIconToEntry(evt, self, self.stmt, pendingArgSite=siteId)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, self.stmt)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, self.stmt, 'attrIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self.window.replaceIconWithEntry(self, self.stmt, 'attrIcon')
        return None

class PassIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "pass", window, location)

    def createAst(self):
        return ast.Pass(lineno=self.id, col_offset=0)

class ContinueIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "continue", window, location)

    def createAst(self):
        return ast.Continue(lineno=self.id, col_offset=0)

class BreakIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "break", window, location)

    def createAst(self):
        return ast.Break(lineno=self.id, col_offset=0)

class SeriesStmtIcon(icon.Icon):
    def __init__(self, stmt, window, seqIndent=False, location=None):
        icon.Icon.__init__(self, window)
        self.stmt = stmt
        self.drawIndent = seqIndent
        bodyWidth = icon.getTextSize(stmt, icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        seqOutIndent = comn.BLOCK_INDENT if seqIndent else 0
        self.sites.add('seqOut', 'seqOut', seqX + seqOutIndent, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = icon.dragSeqImage.width + bodyWidth
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', bodyWidth+1,
                siteYOffset, simpleSpine=True)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

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
            if self.drawIndent:
                icon.drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
                 extendWidth=txtImg.width)
            else:
                icon.drawSeqSites(img, bodyOffset, 0, txtImg.height)
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

    def textRepr(self):
        return self.stmt + " " + icon.seriesTextRepr(self.sites.values)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.stmt + " ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export)
        return text

    def dumpName(self):
        return self.stmt

    def execute(self):
        return None  #... no idea what to do here, yet.

    def backspace(self, siteId, evt):
        return backspaceSeriesStmt(self, siteId, evt, self.stmt)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, self.stmt)
            if cursorTextIdx is None:
                return None, None
            entryIcon = seriesStmtToEntryIcon(self, self.stmt)
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'values_0':
            return seriesStmtToEntryIcon(self, self.stmt)
        return None

class ReturnIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "return", window, location=location)

    def createAst(self):
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            valueAst = None
        else:
            for site in self.sites.values:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            valueAsts = [site.att.createAst() for site in self.sites.values]
            if len(valueAsts) == 1:
                valueAst = valueAsts[0]
            else:
                valueAst = ast.Tuple(valueAsts, ctx=ast.Load(), lineno=self.id,
                 col_offset=0)
        return ast.Return(value=valueAst, lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        # This differs from the superclass version in that a trailing comma is allowed
        # after a single entry (to indicate a single-element tuple )
        brkLvl = parentBreakLevel + 1
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            return filefmt.SegmentedText(self.stmt)
        text = filefmt.SegmentedText(self.stmt + " ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export,
            allowTrailingComma=True)
        return text

class DelIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "del", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
        targetAsts = [site.att.createAst() for site in self.sites.values]
        return ast.Delete(targetAsts, lineno=self.id, col_offset=0)

class GlobalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "global", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise icon.IconExecException(site.att, "Argument must be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Global(names, lineno=self.id, col_offset=0)

class NonlocalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "nonlocal", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise icon.IconExecException(site.att, "Argument must be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Nonlocal(names, lineno=self.id, col_offset=0)

class ImportIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "import", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
        imports = []
        for site in self.sites.values:
            importIcon = site.att
            if isinstance(importIcon, infixicon.AsIcon):
                nameIcon = importIcon.sites.leftArg.att
                if nameIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import name")
                moduleName = _moduleNameFromAttrs(nameIcon)
                if moduleName is None:
                    raise icon.IconExecException(nameIcon,
                        "Improper module name in import")
                asNameIcon = importIcon.sites.rightArg.att
                if asNameIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import as name")
                if not isinstance(asNameIcon, IdentifierIcon):
                    raise icon.IconExecException(asNameIcon,
                            "Import as name must be identifier")
                imports.append(ast.alias(moduleName, asNameIcon.name,
                    lineno=importIcon.id, col_offset=0))
            else:
                if importIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import name")
                moduleName = _moduleNameFromAttrs(importIcon)
                if moduleName is None:
                    raise icon.IconExecException(importIcon,
                        "Improper module name in import")
                imports.append(ast.alias(moduleName, None, lineno=importIcon.id,
                    col_offset=0))
        return ast.Import(imports, level=0, lineno=self.id, col_offset=0)

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
                    return IdentifierIcon(name, self.window), text[-1]
                return "accept"
            elif text == ',':
                return "comma"
            elif onAttr:
                # Allow "as" to be typed
                if text == 'a':
                    return "accept"
                elif text in ('as', 'as '):
                    return infixicon.AsIcon(self.window), None
        return None

class ImportFromIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, window=None, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth = icon.getTextSize('from', icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        impWidth = icon.getTextSize("import", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, impWidth)
        self.moduleNameWidth = icon.EMPTY_ARG_WIDTH
        if typeover:
            self.typeoverIdx = 0
            self.window.watchTypeover(self)
        else:
            self.typeoverIdx = None
        siteYOffset = bodyHeight // 2
        moduleOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('moduleIcon', 'input', moduleOffset, siteYOffset)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        importsX = icon.dragSeqImage.width + bodyWidth-1 + icon.EMPTY_ARG_WIDTH-1 + \
                   impWidth-1
        self.importsList = iconlayout.ListLayoutMgr(self, 'importsIcons', importsX,
            siteYOffset, simpleSpine=True)
        totalWidth = importsX + self.importsList.width - 1
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight, importWidth = self.bodySize
            bodyOffset = icon.dragSeqImage.width - 1
            # "from"
            img = Image.new('RGBA', (bodyWidth + bodyOffset, bodyHeight),
                color=(0, 0, 0, 0))
            fromImg = icon.iconBoxedText("from", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(fromImg, (bodyOffset, 0))
            cntrSiteY = self.sites.seqInsert.yOffset
            fromImgX = bodyOffset + bodyWidth - 1 - icon.inSiteImage.width
            fromImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (fromImgX, fromImageY))
            icon.drawSeqSites(img, bodyOffset, 0, fromImg.height)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, cntrSiteY - icon.dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            # "import"
            importImg = icon.iconBoxedText("import", icon.boldFont, icon.KEYWORD_COLOR,
                typeover=self.typeoverIdx)
            img = Image.new('RGBA', (importImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(importImg, (0, 0))
            importImgX = importImg.width - icon.inSiteImage.width
            img.paste(icon.inSiteImage, (importImgX, fromImageY))
            importOffset = bodyOffset + bodyWidth - 1 + self.moduleNameWidth - 1
            self.drawList.append(((importOffset, self.sites.seqIn.yOffset - 1), img))
            # Commas and possible list simple-spines
            listOffset = importOffset + importWidth - 1 - icon.OUTPUT_SITE_DEPTH
            self.drawList += self.importsList.drawListCommas(listOffset, cntrSiteY)
            self.drawList += self.importsList.drawSimpleSpine(listOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.importsList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, left, top, layout):
        self.moduleNameWidth = layout.moduleNameWidth
        self.importsList.doLayout(layout)
        bodyWidth, bodyHeight, importWidth = self.bodySize
        width = icon.dragSeqImage.width-1 + bodyWidth-1 + self.moduleNameWidth-1 + \
            importWidth-1 + self.importsList.width
        heightAbove = max(bodyHeight // 2, self.importsList.spineTop)
        heightBelow = max(bodyHeight - bodyHeight // 2,
            self.importsList.spineHeight - self.importsList.spineTop)
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
        bodyWidth, bodyHeight, importWidth = self.bodySize
        cntrYOff = bodyHeight // 2
        moduleIcon = self.sites.moduleIcon.att
        moduleLayouts = [None] if moduleIcon is None else moduleIcon.calcLayouts()
        moduleXOff = bodyWidth - 1
        importsListLayouts = self.importsList.calcLayouts()
        layouts = []
        for moduleLayout, importListLayout in iconlayout.allCombinations(
                (moduleLayouts, importsListLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, cntrYOff)
            layout.addSubLayout(moduleLayout, 'moduleIcon', moduleXOff, 0)
            moduleNameWidth = icon.EMPTY_ARG_WIDTH if moduleLayout is None \
                else moduleLayout.width
            layout.moduleNameWidth = moduleNameWidth
            argXOff = bodyWidth - 1 + moduleNameWidth - 1 + importWidth + 1
            importListLayout.mergeInto(layout, argXOff - icon.OUTPUT_SITE_DEPTH, 0)
            layout.width = argXOff + importListLayout.width + importWidth - 2
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        moduleText = icon.argTextRepr(self.sites.moduleIcon)
        importsText = icon.seriesTextRepr(self.sites.importsIcons)
        return "from " + moduleText + " import " + importsText

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("from ")
        icon.addArgSaveText(text, brkLvl, self.sites.moduleIcon, contNeeded, export)
        text.add(brkLvl, " import ", contNeeded)
        icon.addSeriesSaveText(text, brkLvl, self.sites.importsIcons, contNeeded,
            export)
        return text

    def dumpName(self):
        return "import from"

    def createAst(self):
        moduleIcon = self.sites.moduleIcon.att
        if moduleIcon is None:
            raise icon.IconExecException(self, "Import-from missing module name")
        moduleName = _moduleNameFromAttrs(moduleIcon)
        if moduleName is None:
            raise icon.IconExecException(moduleIcon, "Improper module name in import")
        imports = []
        for site in self.sites.importsIcons:
            importIcon = site.att
            if isinstance(importIcon, infixicon.AsIcon):
                nameIcon = importIcon.sites.leftArg.att
                if nameIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import name")
                if not isinstance(nameIcon, IdentifierIcon):
                    raise icon.IconExecException(nameIcon,
                            "Import name must be identifier")
                asNameIcon = importIcon.sites.rightArg.att
                if asNameIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import as name")
                if not isinstance(asNameIcon, IdentifierIcon):
                    raise icon.IconExecException(asNameIcon,
                            "Import as name must be identifier")
                imports.append(ast.alias(nameIcon.name, asNameIcon.name,
                    lineno=importIcon.id, col_offset=0))
            else:
                if importIcon is None:
                    raise icon.IconExecException(importIcon, "Missing import name")
                if not isinstance(importIcon, IdentifierIcon):
                    raise icon.IconExecException(importIcon,
                        "Import name must be identifier")
                imports.append(ast.alias(importIcon.name, None, lineno=importIcon.id,
                    col_offset=0))
        return ast.ImportFrom(moduleName, imports, level=0, lineno=self.id, col_offset=0)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + icon.dragSeqImage.width - 1
        bodyWidth, bodyHeight, importWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId == 'moduleIcon':
            name = text.lstrip('.')
            level = len(text) - len(name)
            name = name.rstrip(' ')
            if not name.isidentifier() and level < 1:
                # The only valid text for the module site is an identifier with optional
                # preceding dots
                return "reject"
            iconOnModuleSite = self.sites.moduleIcon.att
            if iconOnModuleSite is entryIc:
                # Nothing but the entry icon is at the site, allow for typing leading
                # dots by explicitly accepting
                if text[-1] == ' ':
                    if level > 0:
                        return ModuleNameIcon(level * '.' + name, self.window), ' '
                    return IdentifierIcon(name, self.window), ' '
                return "accept"
            rightmostIc, rightmostSite = icon.rightmostSite(iconOnModuleSite)
            if rightmostIc is entryIc and text == "i":
                return "typeover"
            if onAttr:
                # No attributes or operators of any kind are allowed on module names
                return "reject"
            return None
        elif siteId[:12] == 'importsIcons':
            parent = entryIc.parent()
            if parent is self or isinstance(parent, infixicon.AsIcon):
                name = text.rstrip(' ')
                if name == ',':
                    return "comma"
                name = name.rstrip(',')
                if not name.isidentifier():
                    return "reject"
                if text[-1] in (' ', ','):
                    return IdentifierIcon(name, self.window), text[-1]
                return "accept"
            elif text == ',':
                return "comma"
            else:
                if text == 'a':
                    return "accept"
                elif text in ('as', 'as '):
                    return infixicon.AsIcon(self.window), None
                return "reject"

    def setTypeover(self, idx, site=None):
        self.drawList = None  # Force redraw
        if idx is None or idx > 5:
            self.typeoverIdx = None
            return False
        self.typeoverIdx = idx
        return True

    def typeoverCursorPos(self):
        importSite = self.sites.importsIcons[0]
        xOffset = importSite.xOffset + icon.OUTPUT_SITE_DEPTH - icon.TEXT_MARGIN - \
            icon.getTextSize("import"[self.typeoverIdx:], icon.boldFont)[0]
        return xOffset, importSite.yOffset

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        retVal = 'moduleIcon', 'importsIcons_0', 'import', self.typeoverIdx
        return [retVal] if allRegions else retVal

    def backspace(self, siteId, evt):
        if siteId == 'moduleIcon':
            # Cursor is directly on 'from', open for editing
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon)
        elif siteId[:12] == 'importsIcons':
            siteName, index = iconsites.splitSeriesSiteId(siteId)
            if index == 0:
                # Cursor is directly on 'import', Move cursor
                moduleIcon = self.childAt('moduleIcon')
                if moduleIcon is None:
                    self.window.cursor.setToIconSite(self, 'moduleIcon')
                else:
                    rightmostIc, rightmostSite = icon.rightmostSite(moduleIcon)
                    self.window.cursor.setToIconSite(rightmostIc, rightmostSite)
            else:
                # Cursor is on a comma input
                listicons.backspaceComma(self, siteId, evt)

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart,  False)

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        # ImportFromIcon has a module name and an import list.  The backspace method
        # places the module name in the first pending arg, followed by a series
        # containing the import list.  If placeList is in this form, attempt to recreate
        # the original.  If not (or if the module ame is specified, since the base class
        # call handles that correctly, as well), use the base-class method which blindly
        # throws the first input in to the module name field and everything else in to
        # the import list.
        if len(placeList) == 0:
            return None, None
        placeArgsCall = icon.Icon.placeArgs if doPlacement else icon.Icon.canPlaceArgs
        startAtName = startSiteId is None or startSiteId[:10] == 'moduleIcon'
        if startAtName and placeList[0] is None:
            # The base class code can almost do everything we need, but if the first site
            # is empty, it would skip ahead through the placement list and fill the name
            # from the first non-empty argument (so editing an import-from icon with an
            # empty module-name field, then focusing out, would mess up what was
            # originally there).
            argIdx, argSeriesIdx = placeArgsCall(self, placeList[1:], 'importsIcons_0',
                overwriteStart=overwriteStart)
            return argIdx + 1, argSeriesIdx
        # No special processing needed: use the base class method to fill in the name and
        # import list.
        return placeArgsCall(self, placeList, startSiteId, overwriteStart=overwriteStart)

    def _becomeEntryIcon(self):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        moduleIcon = self.childAt('moduleIcon')
        importsIcons = [site.att for site in self.sites.importsIcons]
        entryIcon = entryicon.EntryIcon(window=self.window, initialString='from')
        self.replaceWith(entryIcon)
        self.replaceChild(None, 'moduleIcon')
        for imp in importsIcons:
            if imp is not None:
                self.replaceChild(None, self.siteOf(imp))
        # Put the module name and imports in to separate pending arguments on the
        # entry icon
        if importsIcons is None:
            entryIcon.appendPendingArgs([moduleIcon])
        else:
            entryIcon.appendPendingArgs([moduleIcon, importsIcons])
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'from')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'moduleIcon':
            return self._becomeEntryIcon()
        return None

class ModuleNameIcon(TextIcon):
    def __init__(self, name, window=None, location=None):
        TextIcon.__init__(self, name, window, location)
        self.name = name

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent site belonging to an ImportFrom icon
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            return isinstance(ic, ImportFromIcon) and siteId == "moduleIcon"
        snapData = snapLists['output'][0]
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn)]
        return snapLists

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

class YieldIcon(icon.Icon):
    def __init__(self, window=None, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth = icon.getTextSize("yield", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        seqX = icon.outSiteImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = icon.outSiteImage.width - 1 + bodyWidth
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', bodyWidth-1,
                siteYOffset, simpleSpine=True)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (comn.rectWidth(self.rect),
                    comn.rectHeight(self.rect)), color=(0, 0, 0, 0))
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = icon.outSiteImage.width - 1
            txtImg = icon.iconBoxedText("yield", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImgX = bodyOffset + bodyWidth - icon.inSiteImage.width
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImageY))
            if needSeqSites:
                icon.drawSeqSites(img, bodyOffset, 0, txtImg.height)
            if needOutSite:
                outImageY = bodyHeight // 2 - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (0, outImageY), mask=icon.outSiteImage)
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valueList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valueList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valueList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, outSiteX, outSiteY, layout):
        self.valueList.doLayout(layout)
        bodyWidth, bodyHeight = self.bodySize
        width = icon.outSiteImage.width - 1 + bodyWidth + self.valueList.width
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        if self.valueList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.valueList.spineTop)
            heightBelow = max(heightBelow, self.valueList.spineHeight -
                    self.valueList.spineTop)
        self.sites.output.yOffset = heightAbove
        self.sites.seqInsert.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        left = outSiteX - self.sites.output.xOffset
        top = outSiteY - self.sites.output.yOffset
        self.rect = (left, top, left + width, top + heightAbove + heightBelow)
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        layouts = []
        for valueListLayout in self.valueList.calcLayouts():
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            valueListLayout.mergeInto(layout, bodyWidth - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "yield " + icon.seriesTextRepr(self.sites.values)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            return filefmt.SegmentedText("yield")
        text = filefmt.SegmentedText("yield ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export,
            allowTrailingComma=True)
        return text

    def dumpName(self):
        return "yield"

    def createAst(self):
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            valueAst = None
        else:
            for site in self.sites.values:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            valueAsts = [site.att.createAst() for site in self.sites.values]
            if len(valueAsts) == 1:
                valueAst = valueAsts[0]
            else:
                valueAst = ast.Tuple(valueAsts, ctx=ast.Load(), lineno=self.id,
                 col_offset=0)
        return ast.Yield(value=valueAst, lineno=self.id, col_offset=0)

    def textEntryHandler(self, entryIc, text, onAttr):
        if text[:-1] == 'from' and text[-1] in entryicon.delimitChars:
            leftIc = entryIc.attachedIcon()
            leftSite = entryIc.attachedSite()
            while iconsites.isCoincidentSite(leftIc, leftSite):
                parent = leftIc.parent()
                if parent is None:
                    return None, None
                leftSite = parent.siteOf(leftIc)
                leftIc = parent
            if leftIc is self and leftSite == 'values_0':
                return YieldFromIcon(window=self.window), text[-1]
        return None

    def backspace(self, siteId, evt):
        return backspaceSeriesStmt(self, siteId, evt, "yield")

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.outSiteImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'yield')
            if cursorTextIdx is None:
                return None, None
            entryIcon = seriesStmtToEntryIcon(self, 'yield')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'values_0':
            return seriesStmtToEntryIcon(self, 'yield')
        return None

class YieldFromIcon(opicons.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, 'yield from', window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def createAst(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument to yield from")
        return ast.YieldFrom(self.arg().createAst(), lineno=self.id, col_offset=0)

class AwaitIcon(opicons.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, 'await', window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def createAst(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument to await")
        return ast.Await(self.arg().createAst(), lineno=self.id, col_offset=0)

class RaiseIcon(icon.Icon):
    def __init__(self, hasFrom=False, window=None, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        self.hasFrom = hasFrom
        bodyWidth = icon.getTextSize('raise', icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        fromWidth = icon.getTextSize("from", icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = bodyWidth, bodyHeight, fromWidth
        self.exceptWidth = icon.EMPTY_ARG_WIDTH
        siteYOffset = bodyHeight // 2
        exceptOffset = bodyWidth + icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('exceptIcon', 'input', exceptOffset, siteYOffset)
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        if typeover:
            self.typeoverIdx = 0
            self.window.watchTypeover(self)
        else:
            self.typeoverIdx = None
        if hasFrom:
            totalWidth = icon.dragSeqImage.width + bodyWidth-1 + \
                icon.EMPTY_ARG_WIDTH-1 + fromWidth-1
            fromX = totalWidth - icon.OUTPUT_SITE_DEPTH
            self.sites.add('causeIcon', 'input', fromX, siteYOffset)
        else:
            totalWidth = exceptOffset + icon.OUTPUT_SITE_DEPTH
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight, fromWidth = self.bodySize
            bodyOffset = icon.dragSeqImage.width - 1
            # "raise"
            img = Image.new('RGBA', (bodyWidth + bodyOffset, bodyHeight),
                color=(0, 0, 0, 0))
            raiseImg = icon.iconBoxedText("raise", icon.boldFont, icon.KEYWORD_COLOR)
            img.paste(raiseImg, (bodyOffset, 0))
            cntrSiteY = self.sites.seqInsert.yOffset
            inImgX = bodyOffset + bodyWidth - icon.inSiteImage.width
            inImgY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImgX, inImgY))
            icon.drawSeqSites(img, bodyOffset, 0, raiseImg.height)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, cntrSiteY-icon.dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            # "from"
            if self.hasFrom:
                fromImg = icon.iconBoxedText("from", icon.boldFont, icon.KEYWORD_COLOR,
                    typeover=self.typeoverIdx)
                img = Image.new('RGBA', (fromImg.width, bodyHeight), color=(0, 0, 0, 0))
                img.paste(fromImg, (0, 0))
                inImgX = fromImg.width - icon.inSiteImage.width
                img.paste(icon.inSiteImage, (inImgX, inImgY))
                importOffset = bodyOffset + bodyWidth - 1 + self.exceptWidth - 1
                self.drawList.append(((importOffset, self.sites.seqIn.yOffset - 1), img))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def addFrom(self):
        if self.hasFrom:
            return
        bodyWidth, bodyHeight, fromWidth = self.bodySize
        fromX = icon.dragSeqImage.width + bodyWidth-1 + \
            icon.EMPTY_ARG_WIDTH-1 + fromWidth-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('causeIcon', 'input', fromX, bodyHeight // 2)
        self.hasFrom = True
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.removeFrom)

    def removeFrom(self):
        if not self.hasFrom:
            return
        if self.sites.causeIcon.att is not None:
            print("trying to remove non-empty cause site from raise icon")
            return
        self.sites.remove('causeIcon')
        self.hasFrom = False
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.addFrom)

    def doLayout(self, left, top, layout):
        self.exceptWidth = layout.exceptWidth
        bodyWidth, bodyHeight, fromWidth = self.bodySize
        width = icon.dragSeqImage.width - 1 + bodyWidth
        if self.hasFrom:
            width += -1 + self.exceptWidth-1 + fromWidth
        self.rect = (left, top, left + width, top + bodyHeight)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + bodyHeight // 2)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight, fromWidth = self.bodySize
        cntrYOff = bodyHeight // 2
        exceptIcon = self.sites.exceptIcon.att
        exceptLayouts = [None] if exceptIcon is None else exceptIcon.calcLayouts()
        exceptXOff = bodyWidth - 1
        layouts = []
        causeLayouts = [None]
        if self.hasFrom:
            causeIcon = self.sites.causeIcon.att
            if causeIcon is not None:
                causeLayouts = causeIcon.calcLayouts()
        for exceptLayout, causeLayout in iconlayout.allCombinations((exceptLayouts,
                causeLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, cntrYOff)
            layout.addSubLayout(exceptLayout, 'exceptIcon', exceptXOff, 0)
            exceptWidth = icon.EMPTY_ARG_WIDTH if exceptLayout is None \
                else exceptLayout.width
            layout.exceptWidth = exceptWidth
            layout.width = bodyWidth - 1 + exceptWidth - 1 + fromWidth
            if self.hasFrom:
                layout.addSubLayout(causeLayout, 'causeIcon', layout.width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        if self.sites.exceptIcon.att is None and not self.hasFrom:
            # Empty raise is legal.  Don't place $Empty$ macro if there's no exception
            # and no from keyword
            return filefmt.SegmentedText("raise")
        text = filefmt.SegmentedText("raise ")
        icon.addArgSaveText(text, brkLvl, self.sites.exceptIcon, contNeeded, export)
        if self.hasFrom:
            text.add(brkLvl, " from ", contNeeded)
            icon.addArgSaveText(text, brkLvl, self.sites.causeIcon, contNeeded, export)
        return text

    def dumpName(self):
        return "raise"

    def createAst(self):
        exceptIcon = self.sites.exceptIcon.att
        if exceptIcon is None:
            exc = None
        else:
            exc = exceptIcon.createAst()
        cause = None
        if self.hasFrom:
            causeIcon = self.sites.causeIcon.att
            if causeIcon is None:
                raise icon.IconExecException(self, "raise missing cause after from")
            cause = causeIcon.createAst()
        return ast.Raise(exc, cause, lineno=self.id, col_offset=0)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not icon.Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + icon.dragSeqImage.width - 1
        bodyWidth, bodyHeight, fromWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return comn.rectsTouch(rect, bodyRect)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId == 'exceptIcon':
            # The raise icon is drawn initially without "from".  When the
            # user types an 'f' in the appropriate place, have to turn it
            if text == 'f':
                rightmostIcon, rightmostSite = icon.rightmostFromSite(self, siteId)
                if entryIc is rightmostIcon:
                    self.addFrom()
                    self.setTypeover(0, None)
                    self.window.watchTypeover(self)
                    return "typeover"
        return None

    def setTypeover(self, idx, site=None):
        self.drawList = None  # Force redraw
        if idx is None or idx > 3:
            self.typeoverIdx = None
            return False
        self.typeoverIdx = idx
        return True

    def typeoverCursorPos(self):
        causeSite = self.sites.causeIcon
        xOffset = causeSite.xOffset + icon.OUTPUT_SITE_DEPTH - icon.TEXT_MARGIN - \
            icon.getTextSize("from"[self.typeoverIdx:], icon.boldFont)[0]
        return xOffset, causeSite.yOffset

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        retVal = 'exceptIcon', 'causeIcon', 'from', self.typeoverIdx
        return [retVal] if allRegions else retVal

    def backspace(self, siteId, evt):
        if siteId == 'exceptIcon':
            # Cursor is directly on 'raise', open for editing
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon)
        elif siteId == 'causeIcon':
            causeIcon = self.childAt('causeIcon')
            # Cursor is directly on 'from', remove from if it is empty
            if self.childAt('causeIcon') is not None:
                for ic in causeIcon.traverse():
                    self.window.requestRedraw(ic.rect)
                    self.window.select(ic)
            else:
                self.removeFrom()
                rightmostIc, rightmostSite = icon.rightmostFromSite(self, 'exceptIcon')
                self.window.cursor.setToIconSite(rightmostIc, rightmostSite)

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, False)

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        # RaiseIcon has an exception expression and an optional cause expression.  The
        # placeArgs method is responsible for adding the cause ("from" keyword) if there
        # are two arguments in placeList that are usable.  The backspace method places
        # the exception and cause expressions in individual arguments, so in the
        # (unlikely) case that the user has an empty exception and a filled-in cause, we
        # want to faithfully reconstruct that.  Otherwise we just take the first two
        # non-empty arguments (provided that they're compatible with inputs).
        startAtExcept = startSiteId is None or startSiteId == 'exceptIcon'
        if not startAtExcept and startSiteId != 'causeIcon':
            print('RaiseIcon passed invalid site for arg placement')
            return None, None
        nonEmptyArgs = list(
            icon.placementListIter(placeList, includeEmptySeriesSites=False))
        if len(nonEmptyArgs) == 0:
            return None, None
        if startAtExcept and placeList[0] is None:
            # This is the special case where there's something in the cause field, but
            # nothing in the except field
            if self.childAt('exceptIcon') and not overwriteStart:
                return None, None
            placeExcept = None
            placeCause = 0
        elif not startAtExcept:
            # We're starting in the cause field
            if self.childAt('causeIcon') and not overwriteStart:
                return None, None
            placeExcept = None
            placeCause = 0
        else:
            # We're starting at the except field
            if self.childAt('exceptIcon') and not overwriteStart:
                return None, None
            placeExcept = 0
            if len(nonEmptyArgs) == 1 or self.childAt('causeIcon'):
                placeCause = None
            else:
                placeCause = 1
        placeListIdx = seriesIdx = None
        if placeExcept is not None:
            ic, placeListIdx, seriesIdx = nonEmptyArgs[placeExcept]
            if doPlacement:
                self.replaceChild(ic, 'exceptIcon')
        if placeCause is not None:
            ic, placeListIdx, seriesIdx = nonEmptyArgs[placeCause]
            if doPlacement:
                if not self.hasFrom:
                    self.addFrom()
                self.replaceChild(ic, 'causeIcon')
        return placeListIdx, seriesIdx

    def _becomeEntryIcon(self):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        exceptIcon = self.childAt('exceptIcon')
        causeIcon = self.childAt('causeIcon') if self.hasFrom else None
        entryIcon = entryicon.EntryIcon(window=self.window, initialString='raise')
        self.replaceWith(entryIcon)
        if exceptIcon is not None:
            self.replaceChild(None, 'exceptIcon')
        if causeIcon is not None:
            self.replaceChild(None, 'causeIcon')
        # Put the exception and cause expressions in to separate pending arguments on the
        # entry icon
        if exceptIcon is not None and causeIcon is None:
            entryIcon.appendPendingArgs([exceptIcon])
        elif causeIcon is not None:
            entryIcon.appendPendingArgs([exceptIcon, causeIcon])
        return entryIcon

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width - 1
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, 'raise')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'exceptIcon':
            return self._becomeEntryIcon()
        return None

def backspaceSeriesStmt(ic, site, evt, text):
    siteName, index = iconsites.splitSeriesSiteId(site)
    win = ic.window
    if siteName == "values" and index == 0:
        entryIcon = seriesStmtToEntryIcon(ic, text)
        win.cursor.setToText(entryIcon, drawNew=False)
    elif siteName == "values":
        # Cursor is on comma input.  Delete if empty or previous site is empty, merge
        # surrounding sites if not
        listicons.backspaceComma(ic, site, evt)

def seriesStmtToEntryIcon(ic, text):
    win = ic.window
    valueIcons = [s.att for s in ic.sites.values]
    if len(valueIcons) in (0, 1):
        # Zero or one argument, convert to entry icon (with pending arg if
        # there was an argument)
        if len(valueIcons) == 1 and valueIcons[0] is not None:
            pendingArgSite = 'values_0'
        else:
            pendingArgSite = None
        entryIcon = win.replaceIconWithEntry(ic, text, pendingArgSite)
    else:
        # Multiple remaining arguments: convert to entry icon with pending args in
        # a list (entry icon's minimizePendingArgs will unload to parent if possible)
        win.requestRedraw(ic.topLevelParent().hierRect())
        entryIcon = entryicon.EntryIcon(initialString=text, window=win)
        for arg in valueIcons:
            if arg is not None:
                ic.replaceChild(None, ic.siteOf(arg))
        entryIcon.appendPendingArgs([valueIcons])
        ic.replaceWith(entryIcon)
    return entryIcon

def _moduleNameFromAttrs(identOrAttrIcon):
    isIdentifier = identOrAttrIcon.__class__ in (IdentifierIcon, ModuleNameIcon)
    isAttribute = isinstance(identOrAttrIcon, AttrIcon)
    if not isIdentifier and not isAttribute:
        return None
    name = ("." + identOrAttrIcon.name) if isAttribute else identOrAttrIcon.name
    attrIcon = identOrAttrIcon.sites.attrIcon.att
    if attrIcon is None:
        return name
    attrString = _moduleNameFromAttrs(identOrAttrIcon.sites.attrIcon.att)
    if attrString is None:
        return None
    return name + attrString

# Getting resources (particularly icon class definitions) from other icon files requires
# circular imports, unfortunately.  Here, the import is deferred far enough down the file
# that the dependencies can resolve.
import blockicons

def determineCtx(ic):
    """Figure out the load/store/delete context of a given icon.  Returns an object
    of class ast.Load, ast.Store, or ast.Del based on the result."""
    # Architecture note: it would have been more direct and efficient to to add a
    # parameter to createAst to pass the context from parent icons as asts are created.
    # I am calculating this per-icon, because I suspect the information will be important
    # for display and interaction purposes later on (for example, showing current errors).
    if ic.hasSite('attrIcon') and ic.childAt('attrIcon'):
        return ast.Load()  # Has attribute but is not at the end of the attribute chain
    parent = ic.parent()
    if parent is None:
        return ast.Load()  # At the top level
    if parent.siteOf(ic) == 'attrIcon':
        # ic is the end of an attribute chain.  Determine ctx from parent of its root.
        ic = icon.findAttrOutputSite(ic)
        if ic is None:
            return ast.Load()
        parent = ic.parent()
        if parent is None:
            return ast.Load()
    parentClass = parent.__class__
    if parentClass in (listicons.ListIcon, listicons.TupleIcon,
            parenicon.CursorParenIcon):
        # An element of a list or tuple can be an assignment target (provided the list is
        # not a mutable): look above for assignment
        if hasattr(parent, 'mutableModified'):
            return ast.Load()
        return determineCtx(parent)
    # Return ast.Store() if parent site is an assignment target, ast.Del() if it is a
    # deletion target, or ast.Load() if neither.
    parentSite = parent.siteOf(ic, recursive=True)
    if parentClass in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon,
            blockicons.ForIcon, listicons.CprhForIcon):
        if parentSite[:6] == 'target':
            return ast.Store()
    elif parentClass in (blockicons.DefIcon, blockicons.ClassDefIcon):
        if parentSite == 'nameIcon':
            return ast.Store()
    elif parentClass is infixicon.AsIcon:
        if parentSite == 'rightArg':
            return ast.Store()
    elif parentClass is DelIcon:
        return ast.Del()
    return ast.Load()

def createReturnIconFromAst(astNode, window):
    topIcon = ReturnIcon(window)
    if astNode.value is None:
        return topIcon
    if isinstance(astNode.value, ast.Tuple):
        valueIcons = [icon.createFromAst(v, window) for v in astNode.value.elts]
        topIcon.insertChildren(valueIcons, "values", 0)
        if len(valueIcons) == 1:
            topIcon.insertChild(None, "values", 1)
    else:
        topIcon.replaceChild(icon.createFromAst(astNode.value, window), "values_0")
    return topIcon
icon.registerIconCreateFn(ast.Return, createReturnIconFromAst)

def createImportIconFromAst(astNode, window):
    topIcon = ImportIcon(window)
    aliases = []
    for alias in astNode.names:
        if alias.asname is None:
            aliases.append(IdentifierIcon(alias.name, window))
        else:
            asIcon = infixicon.AsIcon(window)
            asIcon.replaceChild(IdentifierIcon(alias.name, window), 'leftArg')
            asIcon.replaceChild(IdentifierIcon(alias.asname, window), 'rightArg')
            aliases.append(asIcon)
    topIcon.insertChildren(aliases, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Import, createImportIconFromAst)

def createImportFromIconFromAst(astNode, window):
    topIcon = ImportFromIcon(window)
    if astNode.level != 0:
        moduleName = "" if astNode.module is None else astNode.module
        moduleNameIcon = ModuleNameIcon((astNode.level * '.') + moduleName, window)
    else:
        moduleNameIcon = IdentifierIcon(astNode.module, window)
    topIcon.replaceChild(moduleNameIcon, 'moduleIcon')
    aliases = []
    for alias in astNode.names:
        if alias.asname is None:
            aliases.append(IdentifierIcon(alias.name, window))
        else:
            asIcon = infixicon.AsIcon(window)
            asIcon.replaceChild(IdentifierIcon(alias.name, window), 'leftArg')
            asIcon.replaceChild(IdentifierIcon(alias.asname, window), 'rightArg')
            aliases.append(asIcon)
    topIcon.insertChildren(aliases, "importsIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.ImportFrom, createImportFromIconFromAst)

def createDeleteIconFromAst(astNode, window):
    topIcon = DelIcon(window)
    targets = [icon.createFromAst(t, window) for t in astNode.targets]
    topIcon.insertChildren(targets, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Delete, createDeleteIconFromAst)

def createPassIconFromAst(astNode, window):
    return PassIcon(window)
icon.registerIconCreateFn(ast.Pass, createPassIconFromAst)

def createContinueIconFromAst(astNode, window):
    return ContinueIcon(window)
icon.registerIconCreateFn(ast.Continue, createContinueIconFromAst)

def createBreakIconFromAst(astNode, window):
    return BreakIcon(window)
icon.registerIconCreateFn(ast.Break, createBreakIconFromAst)

def createGlobalIconFromAst(astNode, window):
    topIcon = GlobalIcon(window)
    nameIcons = [IdentifierIcon(name, window) for name in astNode.names]
    topIcon.insertChildren(nameIcons, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Global, createGlobalIconFromAst)

def createNonlocalIconFromAst(astNode, window):
    topIcon = NonlocalIcon(window)
    nameIcons = [IdentifierIcon(name, window) for name in astNode.names]
    topIcon.insertChildren(nameIcons, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Nonlocal, createNonlocalIconFromAst)

def createNumericIconFromAst(astNode, window):
    # Deprecated in Python 3.8 and beyond (not called)
    return NumericIcon(astNode.n, window)
icon.registerIconCreateFn(ast.Num, createNumericIconFromAst)

def createNameConstantFromAst(astNode, window):
    return NumericIcon(astNode.value, window)
icon.registerIconCreateFn(ast.NameConstant, createNameConstantFromAst)

def createConstIconFromAst(astNode, window):
    if isinstance(astNode.value, numbers.Number) or astNode.value is None:
        # Note that numbers.Number includes True and False
        if hasattr(astNode, 'annNumberSrcStr'):
            # We have a source string available.  Use it if it matches the value
            # stored in the ast
            if astNode.value == ast.literal_eval(astNode.annNumberSrcStr):
                return NumericIcon(astNode.annNumberSrcStr, window)
        return NumericIcon(astNode.value, window)
    elif isinstance(astNode.value, (str, bytes)):
        if hasattr(astNode, 'annSourceStrings'):
            initStr = stringicon.joinConcatenatedSourceStrings(astNode.annSourceStrings)
            if initStr is None:
                initStr = repr(astNode.value)
        else:
            initStr = repr(astNode.value)
        if hasattr(astNode, 'annIsDocString') and \
                initStr[:3] in ("'''", '"""') and initStr[-3:] in ("'''", '"""'):
            quote = initStr[:3]
            strippedInitString = initStr[3:-3]
            initStr = quote + inspect.cleandoc(strippedInitString) + quote
        return stringicon.StringIcon(initStr, window)
    if isinstance(astNode.value, type(...)):
        return NumericIcon(astNode.value, window)
    # Documentation threatens to return constant tuples and frozensets (which could
    # get quite complex), but 3.8 seems to stick to strings and numbers
    return IdentifierIcon("**Couldn't Parse Constant**", window)
icon.registerIconCreateFn(ast.Constant, createConstIconFromAst)

def createIdentifierIconFromAst(astNode, window):
    return IdentifierIcon(astNode.id, window)
icon.registerIconCreateFn(ast.Name, createIdentifierIconFromAst)

def createAttrIconFromAst(astNode, window):
    # Note that the icon hierarchy and the AST hierarchy differ with respect to
    # attributes. ASTs put the attribute at the top, we put the root icon at the top.
    attrIcon = AttrIcon(astNode.attr, window)
    topIcon = icon.createFromAst(astNode.value, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(attrIcon, "attrIcon")
    return topIcon
icon.registerIconCreateFn(ast.Attribute, createAttrIconFromAst)

def createYieldIconFromAst(astNode, window):
    topIcon = YieldIcon(window)
    if astNode.value is None:
        return topIcon
    if isinstance(astNode.value, ast.Tuple):
        valueIcons = [icon.createFromAst(v, window) for v in astNode.value.elts]
        topIcon.insertChildren(valueIcons, "values", 0)
        if len(valueIcons) == 1:
            topIcon.insertChild(None, "values", 1)
    else:
        topIcon.replaceChild(icon.createFromAst(astNode.value, window), "values_0")
    return topIcon
icon.registerIconCreateFn(ast.Yield, createYieldIconFromAst)

def createYieldFromIconFromAst(astNode, window):
    topIcon = YieldFromIcon(window)
    topIcon.replaceChild(icon.createFromAst(astNode.value, window), "argIcon")
    return topIcon
icon.registerIconCreateFn(ast.YieldFrom, createYieldFromIconFromAst)

def createAwaitIconFromAst(astNode, window):
    topIcon = AwaitIcon(window)
    topIcon.replaceChild(icon.createFromAst(astNode.value, window), "argIcon")
    return topIcon
icon.registerIconCreateFn(ast.Await, createAwaitIconFromAst)

def createRaiseIconFromAst(astNode, window):
    hasFrom = astNode.cause is not None
    topIcon = RaiseIcon(hasFrom, window)
    if astNode.exc is not None:
        topIcon.replaceChild(icon.createFromAst(astNode.exc, window), "exceptIcon")
    if hasFrom:
        topIcon.replaceChild(icon.createFromAst(astNode.cause, window), "causeIcon")
    return topIcon
icon.registerIconCreateFn(ast.Raise, createRaiseIconFromAst)

def createParseFailIcon(astNode, window):
    return IdentifierIcon("**Couldn't Parse AST node: %s**" % astNode.__class__.__name__,
        window)
icon.registerAstDecodeFallback(createParseFailIcon)