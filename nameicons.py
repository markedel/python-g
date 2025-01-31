# Copyright Mark Edel  All rights reserved
from PIL import Image
import ast
import numbers
import inspect
import re
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

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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

    def duplicate(self, linkToOriginal=False):
        ic = TextIcon(text=self.text, window=self.window,
            cursorOnlyAttrSite=self.sites.attrIcon.isCursorOnlySite())
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

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
        self.canProcessCtx = True

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

    def duplicate(self, linkToOriginal=False):
        ic = IdentifierIcon(name=self.name, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False, ctx=None):
        # Identifiers are valid in delete and save contexts, hence the optional ctx
        # parameter.  If ctx is not None, check that the attributes are legal in the
        # given context, and wrap the identifier and its attribute chain in a $Ctx$ macro
        # if it is not.
        if ctx is None or listicons.attrValidForContext(self, ctx):
            return TextIcon.createSaveText(self, parentBreakLevel, contNeeded, export)
        # Currently, this code is never reached, because parent icons handle this for us
        # in every case.  It's left here, to be ready if something changes, as it would
        # be confusing for an icon not to be able to handle its own save-text generation.
        text = TextIcon.createSaveText(self, parentBreakLevel+1, contNeeded, export)
        if not export:
            text.wrapCtxMacro(parentBreakLevel, needsCont=contNeeded)
        return text

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

    def duplicate(self, linkToOriginal=False):
        ic = NumericIcon(value=self.value, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        # While other icons with cursor-only sites can temporarily host entry icons
        # during parsing, numeric icons can hold them indefinitely, and therefore need
        # to take responsibility for saving.  In order to do that, we wrap a paren with
        # $:x$ (remove option) around ourselves
        numberText = filefmt.SegmentedText(self.text)
        attr = self.childAt('attrIcon')
        if attr is None:
            return numberText
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('$:x$(')
        text.concat(brkLvl, numberText)
        text.add(None, ")")
        return icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)

    def compareData(self, data):
        return data == self.value

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

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
        breakLvl = parentBreakLevel + (1 if self.parent() is None else 0)
        text = icon.addAttrSaveText(filefmt.SegmentedText("." + self.name), self,
            breakLvl, contNeeded, export)
        if self.parent() is None and not export:
            text.wrapFragmentMacro(parentBreakLevel, 'a', needsCont=contNeeded)
        return text

    def createAst(self, attrOfAst):
        # No need to check ctx, since all are acceptable
        return icon.composeAttrAst(self, ast.Attribute(value=attrOfAst, attr=self.name,
            lineno=self.id, col_offset=0, ctx=determineCtx(self)))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

    def duplicate(self, linkToOriginal=False):
        ic = AttrIcon(name=self.name, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

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

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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

    def highlightErrors(self, errHighlight):
        if errHighlight is None and isOutsideOfLoop(self):
            errHighlight = "continue statement outside of loop"
        icon.Icon.highlightErrors(self, errHighlight)

class BreakIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "break", window, location)

    def createAst(self):
        return ast.Break(lineno=self.id, col_offset=0)

    def highlightErrors(self, errHighlight):
        if errHighlight is None and isOutsideOfLoop(self):
            errHighlight = "break statement outside of loop"
        icon.Icon.highlightErrors(self, errHighlight)

class SeriesStmtIcon(icon.Icon):
    def __init__(self, stmt, window, seqIndent=False, requireArg=False,
            allowTrailingComma=False, location=None):
        icon.Icon.__init__(self, window)
        self.stmt = stmt
        self.drawIndent = seqIndent
        self.requireArg = requireArg
        self.allowTrailingComma = allowTrailingComma
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
        if self.requireArg:
            totalWidth += icon.LIST_EMPTY_ARG_WIDTH
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', bodyWidth+1,
                siteYOffset, simpleSpine=True)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
        self._drawEmptySites(toDragImage, clip, hilightEmptySeries=self.requireArg,
            allowTrailingComma=self.allowTrailingComma)
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
        if self.requireArg:
            width += icon.LIST_EMPTY_ARG_WIDTH
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
        valueListLayouts = self.valueList.calcLayouts(argRequired=self.requireArg)
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

    def siteRightOfPart(self, partId):
        return 'values_0'

class ReturnIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "return", window, allowTrailingComma=True,
            location=location)

    def createAst(self):
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            valueAst = None
        else:
            for site in self.sites.values[:-1]:
                if site.att is None:
                    raise icon.IconExecException(self, "Missing argument(s)")
            trailingComma = self.sites.values[-1].att is None
            if trailingComma:
                valueAsts = [site.att.createAst() for site in self.sites.values[:-1]]
            else:
                valueAsts = [site.att.createAst() for site in self.sites.values]
            if len(valueAsts) == 1 and not trailingComma:
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

    def highlightErrors(self, errHighlight):
        if errHighlight is None and isOutsideOfDef(self):
            errHighlight = icon.ErrorHighlight("return statement outside of def")
        icon.Icon.highlightErrors(self, errHighlight)

class DelIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "del", window, requireArg=True, location=location)

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            self.errHighlight = None
            valuesSeries = getattr(self.sites, 'values')
            listicons.highlightSeriesErrorsForContext(valuesSeries, 'del')
        else:
            icon.Icon.highlightErrors(self, errHighlight)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if not site.att.canProcessCtx:
                raise icon.IconExecException(site.att, "Not a valid target for del")
        targetAsts = [site.att.createAst() for site in self.sites.values]
        return ast.Delete(targetAsts, lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText(self.stmt + " ")
        tgtTxt = listicons.seriesSaveTextForContext(brkLvl, self.sites.values,
            contNeeded, export, 'del')
        text.concat(brkLvl, tgtTxt)
        return text

class GlobalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "global", window, requireArg=True,
            location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise icon.IconExecException(site.att, "Argument must be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Global(names, lineno=self.id, col_offset=0)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:6] != 'values':
            return None
        if text == ',':
            return "comma"
        elif onAttr:
            return "reject:global statement expects only unqualified identifiers"
        elif text.isidentifier():
            return "accept"
        elif text[-1] in ' ,' and text[:-1].isidentifier():
            if text[:-1] in entryicon.keywords:
                return "reject:%s is a reserved keyword and cannot be used " \
                    "as a variable name" % text[:-1]
            return IdentifierIcon(text[:-1], self.window), text[-1]
        return "reject:Only valid identifiers can be declared global"

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("global ")
        valuesSites = self.sites.values
        if len(valuesSites) == 0 or len(valuesSites) == 1 and valuesSites[0].att is None:
            if not export:
                text.add(brkLvl, '$Empty$', contNeeded)
            return text
        args = [createNameFieldSaveText(brkLvl, site, contNeeded, export) for site in
            valuesSites]
        text.concat(brkLvl, args[0], contNeeded)
        for arg in args[1:]:
            text.add(None, ', ', contNeeded)
            text.concat(brkLvl, arg, contNeeded)
        return text

    def highlightErrors(self, errHighlight):
        # textEntryHandler prohibits typing of anything but correct syntax, but we
        # (currently) allow snapping of illegal stuff for users to edit later.
        self.errHighlight = errHighlight
        if errHighlight is not None:
            for ic in self.children():
                ic.highlightErrors(errHighlight)
            return
        for ic in (site.att for site in self.sites.values if site.att is not None):
            if isinstance(ic, IdentifierIcon):
                ic.errHighlight = None
                attr = ic.childAt('attrIcon')
                if attr is not None:
                    attr.highlightErrors(icon.ErrorHighlight(
                        "Variable name may not have anything attached"))
                    continue
            else:
                ic.highlightErrors(icon.ErrorHighlight(
                    "Not a valid variable name (identifier)"))

class NonlocalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "nonlocal", window, requireArg=True,
            location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise icon.IconExecException(site.att, "Argument must be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Nonlocal(names, lineno=self.id, col_offset=0)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:6] != 'values':
            return None
        if text == ',':
            return "comma"
        elif onAttr:
            return "reject:nonlocal statement expects only unqualified identifiers"
        elif text.isidentifier():
            return "accept"
        elif text[-1] in ' ,' and text[:-1].isidentifier():
            if text[:-1] in entryicon.keywords:
                return "reject:%s is a reserved keyword and cannot be used " \
                    "as a variable name" % text[:-1]
            return IdentifierIcon(text[:-1], self.window), text[-1]
        return 'reject:Only valid identifiers can be declared nonlocal'

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText("nonlocal ")
        valuesSites = self.sites.values
        if len(valuesSites) == 0 or len(valuesSites) == 1 and valuesSites[0].att is None:
            if not export:
                text.add(brkLvl, '$Empty$', contNeeded)
            return text
        args = [createNameFieldSaveText(brkLvl, site, contNeeded, export) for site in
            valuesSites]
        text.concat(brkLvl, args[0], contNeeded)
        for arg in args[1:]:
            text.add(None, ', ', contNeeded)
            text.concat(brkLvl, arg, contNeeded)
        return text

    def highlightErrors(self, errHighlight):
        # textEntryHandler prohibits typing of anything but correct syntax, but we
        # (currently) allow snapping of illegal stuff for users to edit later.
        self.errHighlight = errHighlight
        if errHighlight is not None:
            for ic in self.children():
                ic.highlightErrors(errHighlight)
            return
        for ic in (site.att for site in self.sites.values if site.att is not None):
            if isinstance(ic, IdentifierIcon):
                ic.errHighlight = None
                attr = ic.childAt('attrIcon')
                if attr is not None:
                    attr.highlightErrors(icon.ErrorHighlight(
                        "Variable name may not have anything attached"))
                    continue
            else:
                ic.highlightErrors(icon.ErrorHighlight(
                    "This is not valid as a variable name (identifier)"))

class ImportIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "import", window, requireArg=True,
            location=location)

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
                moduleName = moduleNameFromIcons(nameIcon)
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
                moduleName = moduleNameFromIcons(importIcon)
                if moduleName is None:
                    raise icon.IconExecException(importIcon,
                        "Improper module name in import")
                imports.append(ast.alias(moduleName, None, lineno=importIcon.id,
                    col_offset=0))
        return ast.Import(imports, level=0, lineno=self.id, col_offset=0)

    def textEntryHandler(self, entryIc, text, onAttr):
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId[:6] != 'values':
            return None
        parent = entryIc.parent()
        if isinstance(parent, infixicon.AsIcon):
            # Enforce identifiers-only on right argument of "as"
            name = text.rstrip(' ')
            if name == ',':
                return "comma"
            name = name.rstrip(',')
            if not name.isidentifier():
                return "reject:as requires a simple identifier as module name"
            if text[-1] in (' ', ','):
                if text[:-1] in entryicon.keywords:
                    return "reject:%s is a reserved keyword and cannot be used " \
                           "as a module identifier" % text[:-1]
                return IdentifierIcon(name, self.window), text[-1]
            return "accept"
        elif text == ',':
            return "comma"
        elif onAttr:
            # Allow only "as" or simple attribute to be typed
            if text in '.a':
                return "accept"
            elif text in ('as', 'as '):
                return infixicon.AsIcon(self.window), ' ' if text == 'as ' else None
            elif text[0] != '.':
                return "reject:Not a valid module identifier, must be name or " \
                    "dot-separated names"
            elif text[1:].isidentifier():
                return "accept"
            elif text[-1] in ' .,' and text[1:-1].isidentifier():
                return AttrIcon(text[:-1], self.window), text[-1]
        elif text.isidentifier():
            return "accept"
        elif text[-1] in ' .,' and text[:-1].isidentifier():
            if text[:-1] in entryicon.keywords:
                return "reject:%s is a reserved keyword and cannot be used " \
                       "as a module name" % text[:-1]
            return IdentifierIcon(text[:-1], self.window), text[-1]
        return 'reject:Not a valid module name'

    def highlightErrors(self, errHighlight):
        # textEntryHandler prohibits typing of anything but correct syntax, but we
        # (currently) allow snapping of illegal stuff for users to edit later.
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        self.errHighlight = None
        for ic in (site.att for site in self.sites.values if site.att is not None):
            if isinstance(ic, IdentifierIcon):
                ic.errHighlight = None
                attr = ic.childAt('attrIcon')
                while attr is not None:
                    if not isinstance(attr, AttrIcon):
                        attr.highlightErrors(icon.ErrorHighlight(
                            "Not a valid format for a module name for import"))
                        break
                    attr.errHighlight = None
                    attr = attr.childAt('attrIcon')
            elif isinstance(ic, infixicon.AsIcon):
                ic.errHighlight = None
                leftArg = ic.leftArg()
                if leftArg is not None:
                    if isinstance(leftArg, IdentifierIcon):
                        attr = leftArg.childAt('attrIcon')
                        while attr is not None:
                            if not isinstance(attr, AttrIcon):
                                attr.highlightErrors(icon.ErrorHighlight(
                                    "Not a valid format for a module name for import"))
                                break
                            attr.errHighlight = None
                            attr = attr.childAt('attrIcon')
                    else:
                        leftArg.highlightErrors(icon.ErrorHighlight(
                            "Not a valid module name for import"))
                rightArg = ic.rightArg()
                if rightArg is not None:
                    if not isinstance(rightArg, IdentifierIcon):
                        rightArg.highlightErrors(icon.ErrorHighlight(
                            "Import alias must be an identifier"))
                        continue
                    rightArg.errHighlight = None
                    rightArgAttr = rightArg.childAt('attrIcon')
                    if rightArgAttr is not None:
                        rightArgAttr.highlightErrors(icon.ErrorHighlight(
                            "Import alias must be a valid identifier"))
                        continue
            else:
                ic.highlightErrors(icon.ErrorHighlight(
                    "Not a valid module name for import"))

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText('import ')
        args = []
        for ic in (site.att for site in self.sites.values):
            parseCtx = None
            if isinstance(ic, IdentifierIcon):
                ic.errHighlight = None
                attr = ic.childAt('attrIcon')
                needsCtx = False
                while attr is not None:
                    if not isinstance(attr, AttrIcon):
                        needsCtx = True
                        break
                    attr = attr.childAt('attrIcon')
            elif isinstance(ic, infixicon.AsIcon):
                # 'as' icon enforces identifier as right arg, but does not enforce
                # left arg constraints specific to import
                needsCtx = False
                leftArg = ic.leftArg()
                if leftArg is not None:
                    if isinstance(leftArg, IdentifierIcon):
                        attr = leftArg.childAt('attrIcon')
                        while attr is not None:
                            if not isinstance(attr, AttrIcon):
                                needsCtx = True
                                break
                            attr.errHighlight = None
                            attr = attr.childAt('attrIcon')
                    else:
                        needsCtx = True
                        parseCtx = 's'
            elif ic is not None:
                needsCtx = True
            if ic is None:
                if not export:
                    args.append(filefmt.SegmentedText('$Empty$'))
            else:
                brkLvl = parentBreakLevel + (2 if needsCtx and not export else 1)
                arg = ic.createSaveText(brkLvl, contNeeded, export)
                if needsCtx and not export:
                    arg.wrapCtxMacro(parentBreakLevel+1, needsCont=contNeeded,
                        parseCtx=parseCtx)
                args.append(arg)
        text.concat(parentBreakLevel, args[0], contNeeded)
        for arg in args[1:]:
            text.add(None, ', ', contNeeded)
            text.concat(parentBreakLevel+1, arg, contNeeded)
        return text

class ImportFromIcon(icon.Icon):
    hasTypeover = True
    relDelimPattern = re.compile('[a-zA-Z ]')

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
        self.dragSiteDrawn = False
        totalWidth = importsX + self.importsList.width - 1 + icon.EMPTY_ARG_WIDTH
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        needDragSite = toDragImage is not None and self.prevInSeq() is None
        if self.drawList is None or self.dragSiteDrawn and not needDragSite:
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
            if needDragSite:
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
        self._drawEmptySites(toDragImage, clip, hilightEmptySeries=True)
        self.dragSiteDrawn = needDragSite

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
            importWidth-1 + self.importsList.width + icon.EMPTY_ARG_WIDTH
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
            layout.width = argXOff + icon.EMPTY_ARG_WIDTH
            importListLayout.mergeInto(layout, argXOff - icon.OUTPUT_SITE_DEPTH, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        moduleText = icon.argTextRepr(self.sites.moduleIcon)
        importsText = icon.seriesTextRepr(self.sites.importsIcons)
        return "from " + moduleText + " import " + importsText

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText("from ")
        needsCtx = False
        moduleNameIcon = self.childAt('moduleIcon')
        if isinstance(moduleNameIcon, RelativeImportIcon):
            moduleNameIcon = moduleNameIcon.childAt('argIcon')
        if isinstance(moduleNameIcon, IdentifierIcon):
            attr = moduleNameIcon.childAt('attrIcon')
            while attr is not None:
                if not isinstance(attr, AttrIcon):
                    needsCtx = True
                    break
                attr = attr.childAt('attrIcon')
        elif moduleNameIcon is not None:
            needsCtx = True
        brkLvl = parentBreakLevel + (2 if needsCtx  and not export else 1)
        moduleNameText = icon.argSaveText(brkLvl, self.sites.moduleIcon, contNeeded,
            export)
        if needsCtx and not export:
            moduleNameText.wrapCtxMacro(parentBreakLevel + 1, needsCont=contNeeded)
        text.concat(parentBreakLevel + 1, moduleNameText)
        text.add(parentBreakLevel+1, " import ", contNeeded)
        args = []
        for ic in (site.att for site in self.sites.importsIcons):
            needsCtx = False
            parseCtx = None
            if isinstance(ic, IdentifierIcon):
                attr = ic.childAt('attrIcon')
                if attr is not None:
                    needsCtx = True
            elif isinstance(ic, infixicon.AsIcon):
                # 'as' icon enforces identifier as right arg, but does not enforce
                # left arg also being constrained to an identifier
                leftArg = ic.leftArg()
                if leftArg is not None:
                    if isinstance(leftArg, IdentifierIcon):
                        if leftArg.childAt('attrIcon') is not None:
                            needsCtx = True
                            parseCtx = 's'
                    else:
                        needsCtx = True
                        parseCtx = 's'
            elif isinstance(ic, listicons.StarIcon):
                if len(self.sites.importsIcons) > 1:
                    needsCtx = True
                    parseCtx = 'f'
                if ic.arg() is not None:
                    needsCtx = True
                    parseCtx = 'f'
            elif ic is not None:
                needsCtx = True
            if ic is None:
                args.append(filefmt.SegmentedText(None if export else '$Empty$'))
            else:
                brkLvl = parentBreakLevel + (2 if needsCtx and not export else 1)
                arg = ic.createSaveText(brkLvl, contNeeded, export)
                if needsCtx and not export:
                    arg.wrapCtxMacro(parentBreakLevel+1, needsCont=contNeeded,
                        parseCtx=parseCtx)
                args.append(arg)
        text.concat(parentBreakLevel, args[0], contNeeded)
        for arg in args[1:]:
            text.add(None, ', ', contNeeded)
            text.concat(parentBreakLevel+1, arg, contNeeded)
        return text

    def dumpName(self):
        return "import from"

    def createAst(self):
        moduleIcon = self.sites.moduleIcon.att
        if moduleIcon is None:
            raise icon.IconExecException(self, "Import-from missing module name")
        moduleName = moduleNameFromIcons(moduleIcon)
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
            if self.sites.moduleIcon.att is entryIc:
                if text[0] == '.':
                    delim = text.lstrip('.')
                    if delim == '':
                        return 'accept'
                    if not self.relDelimPattern.fullmatch(delim):
                        return "reject:Module names must be dot-separated identifiers"
                    return RelativeImportIcon(len(text) - len(delim), self.window), delim
            if self.sites.moduleIcon.att is entryIc or isinstance(entryIc.parent(),
                    RelativeImportIcon):
                name = text.rstrip(' .')
                if not name.isidentifier():
                    # The only valid text for the module site itself, is an identifier
                    return "reject:Module name must be a valid identifier"
                if text[-1] in ' .':
                    if name in entryicon.keywords:
                        return "reject:%s is a reserved keyword and cannot be used " \
                            "in a module name" % name
                    else:
                        return IdentifierIcon(name, self.window), text[-1]
                return "accept"
            if onAttr:
                rightmostIc, rightmostSite = icon.rightmostSite(self.sites.moduleIcon.att)
                if rightmostIc is entryIc and text == "i":
                    return "typeover"
                # Allow only simple attributes to be typed
                if text[0] != '.':
                    return "reject:module name can only be identifier or dot-saparated " \
                        "identifiers"
                elif text == '.' or text[1:].isidentifier():
                    return "accept"
                elif text[-1] in ' .' and text[1:-1].isidentifier():
                    return AttrIcon(text[1:-1], self.window), text[-1]
            return "reject:Not a valid module name"
        elif siteId[:12] == 'importsIcons':
            parent = entryIc.parent()
            if isinstance(parent, listicons.StarIcon):
                return "reject:Nothing can follow *"
            if parent is self and len(self.sites.importsIcons) == 1 and text == '*':
                return listicons.StarIcon(self.window), None
            if parent is self and text in ('as ', 'as,'):
                return infixicon.AsIcon(self.window), text[-1]
            if parent is self or isinstance(parent, infixicon.AsIcon):
                name = text.rstrip(' ')
                if name == ',':
                    return "comma"
                name = name.rstrip(',')
                if not name.isidentifier():
                    return "reject:Modules can only be named with simple identifier"
                if text[-1] in (' ', ','):
                    if name in entryicon.keywords:
                        return "reject:%s is a reserved keyword and cannot be used " \
                           "as a module identifier" % name
                    else:
                        return IdentifierIcon(name, self.window), text[-1]
                return "accept"
            elif text == ',':
                return "comma"
            elif onAttr and text[0] == 'a':
                if isinstance(parent, IdentifierIcon) and parent.parent() is self:
                    if text == 'as':
                        return infixicon.AsIcon(self.window), None
                    if text == 'a':
                        return "accept"
            return "reject:Not a valid target for import"
        return None

    def highlightErrors(self, errHighlight):
        # textEntryHandler prohibits typing of anything but correct syntax, but we
        # (currently) allow snapping of illegal stuff for users to edit later.
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        self.errHighlight = None
        moduleNameIcon = self.childAt('moduleIcon')
        if isinstance(moduleNameIcon, RelativeImportIcon):
            moduleNameIcon.errHighlight = None
            moduleNameIcon = moduleNameIcon.childAt('argIcon')
        if isinstance(moduleNameIcon, IdentifierIcon):
            moduleNameIcon.errHighlight = None
            attr = moduleNameIcon.childAt('attrIcon')
            while attr is not None:
                if not isinstance(attr, AttrIcon):
                    attr.highlightErrors(icon.ErrorHighlight(
                        "Not a valid format for a module name for import"))
                    break
                attr.errHighlight = None
                attr = attr.childAt('attrIcon')
        elif moduleNameIcon is not None:
            moduleNameIcon.highlightErrors(icon.ErrorHighlight(
                "Not a valid format for a module name for import"))
        for ic in (site.att for site in self.sites.importsIcons if site.att is not None):
            if isinstance(ic, IdentifierIcon):
                ic.errHighlight = None
                attr = ic.childAt('attrIcon')
                if attr is not None:
                    attr.highlightErrors(icon.ErrorHighlight(
                        "Name must be an individual identifier (dotted "
                            "names are not allowed)"))
                    continue
            elif isinstance(ic, infixicon.AsIcon):
                ic.errHighlight = None
                leftArg = ic.leftArg()
                if leftArg is not None:
                    if not isinstance(leftArg, IdentifierIcon):
                        leftArg.highlightErrors(icon.ErrorHighlight(
                            "Not a valid module name for import"))
                        continue
                    attr = leftArg.childAt('attrIcon')
                    if attr is not None:
                        attr.highlightErrors(icon.ErrorHighlight(
                            "Name must be an individual identifier (dotted "
                            "names are not allowed)"))
                        continue
                rightArg = ic.rightArg()
                if rightArg is not None:
                    if not isinstance(rightArg, IdentifierIcon):
                        rightArg.highlightErrors(icon.ErrorHighlight(
                            "Import alias must be an identifier"))
                        continue
                    rightArg.errHighlight = None
                    rightArgAttr = rightArg.childAt('attrIcon')
                    if rightArgAttr is not None:
                        rightArgAttr.highlightErrors(icon.ErrorHighlight(
                            "Import alias must be a valid identifier"))
                        continue
            elif isinstance(ic, listicons.StarIcon):
                if len(self.sites.importsIcons) > 1:
                    ic.highlightErrors(icon.ErrorHighlight(
                        "* must stand alone (can not be part of list)"))
                    continue
                ic.errHighlight = None
                arg = ic.arg()
                if arg is not None:
                    arg.highlightErrors(icon.ErrorHighlight(
                            "* cannot be qualified"))
            else:
                ic.highlightErrors(icon.ErrorHighlight(
                    "Not a valid module name for import"))

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
        if moduleIcon is not None and importsIcons == [None]:
            entryIcon.appendPendingArgs([moduleIcon])
        elif importsIcons != [None]:
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

    def siteRightOfPart(self, partId):
        if partId == 1:
            return 'moduleIcon'
        return 'importsIcons_0'

class RelativeImportIcon(opicons.UnaryOpIcon):
    def __init__(self, level, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, '. ' * level, window, location)
        self.level = level
        self.suppressEmptyArgHighlight = True

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        # We lied to the UnaryOpIcon superclass about the text content to make it more
        # readable  (. . . vs. ...), but we don't want that to go in to the entry icon
        entryIcon, curWinPos = opicons.UnaryOpIcon.becomeEntryIcon(self, clickPos,
            siteAfter)
        entryIcon.text = '.' * self.level
        entryIcon.setCursorPos((entryIcon.cursorPos + 1) // 2)
        return entryIcon, curWinPos

    def backspace(self, siteId, evt):
        # We lied to the UnaryOpIcon superclass about the text content to make it more
        # readable  (. . . vs. ...), but we don't want that to go in to the entry icon
        self.window.backspaceIconToEntry(evt, self, self.level * '.',
            pendingArgSite=siteId)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent site belonging to an ImportFrom icon
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            return isinstance(ic, ImportFromIcon) and siteId == "moduleIcon"
        if 'output' in snapLists:
            snapData = snapLists['output'][0]
            snapLists['output'] = []
            snapLists['conditional'] = [(*snapData, 'output', snapFn)]
        return snapLists

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            parent = self.parent()
            if parent is None:
                if self.sites.seqIn.att is not None or self.sites.seqOut.att is not None:
                    errHighlight = icon.ErrorHighlight("Relative import (one or "
                    "more leading '.') by itself is not legal as a statement")
            elif not isinstance(parent, ImportFromIcon):
                errHighlight = icon.ErrorHighlight("Can only use relative import (one or "
                    "more leading '.') in the context of an import-from statement")
        icon.Icon.highlightErrors(self, errHighlight)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText("." * self.level)
        parent = self.parent()
        ctxNeeded = not export and (not isinstance(parent, ImportFromIcon) or
            parent.siteOf(self) != 'moduleIcon')
        brkLvl = parentBreakLevel + (2 if ctxNeeded else 1)
        arg = self.sites.argIcon.att
        if arg is not None:
            argText = arg.createSaveText(brkLvl, contNeeded, export)
            text.concat(None, argText, contNeeded)
        if ctxNeeded:
            text.wrapCtxMacro(parentBreakLevel+1, needsCont=contNeeded, parseCtx='i')
        return text

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def duplicate(self, linkToOriginal=False):
        ic = RelativeImportIcon(level=self.level, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

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

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = icon.outSiteImage.width - 1
            img = Image.new('RGBA', (bodyWidth + bodyOffset, bodyHeight),
                color=(0, 0, 0, 0))
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
        self._drawEmptySites(toDragImage, clip, allowTrailingComma=True)

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

    def highlightErrors(self, errHighlight):
        if errHighlight is None and isOutsideOfDef(self.topLevelParent()):
            errHighlight = icon.ErrorHighlight("yield statement outside of def")
        icon.Icon.highlightErrors(self, errHighlight)

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

    def siteRightOfPart(self, partId):
        return 'values_0'

class YieldFromIcon(opicons.UnaryOpIcon):
    def __init__(self, window=None, location=None):
        opicons.UnaryOpIcon.__init__(self, 'yield from', window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def highlightErrors(self, errHighlight):
        if errHighlight is None and isOutsideOfDef(self.topLevelParent()):
            errHighlight = icon.ErrorHighlight("'yield from' outside of def")
        icon.Icon.highlightErrors(self, errHighlight)

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
            totalWidth = exceptOffset + icon.OUTPUT_SITE_DEPTH + icon.EMPTY_ARG_WIDTH
        self.dragSiteDrawn = False
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        needDragSite = toDragImage is not None and self.prevInSeq() is None
        if self.drawList is None or self.dragSiteDrawn and not needDragSite:
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
            if needDragSite:
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
        self._drawEmptySites(toDragImage, clip)
        self.dragSiteDrawn = needDragSite

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
        width = icon.dragSeqImage.width - 1 + bodyWidth + icon.EMPTY_ARG_WIDTH
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

    def siteRightOfPart(self, partId):
        return 'exceptIcon'

class DecoratorIcon(icon.Icon):
    # The decorator iccon is just "@" sign part of the decorator, with an input site for
    # attaching the name, optional module components, and call icon to provide arguments.
    # The input site, has both typing and snapping conditions placed on it, to restrict
    # users from typing incompatible stuff, but as usual, users can use tricky methods
    # that will result in things that need to be highlighted and saved.  Originally,
    # the decorator icon held the more of the decorator content, but to make it easier
    # to edit (for example, to add a module name), it is now just '@'.  Currently
    # parameterized decorators use a call icon, which is different from, function or
    # class def icons, which own their parens. However in the decorator case, this
    # parallels the AST form, which uses and actual ast.Call node to hold the decorator
    # information.
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth = icon.getTextSize('@', icon.boldFont)[0] + 2*icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.sites.add('argIcon', 'input', bodyWidth - 1, siteYOffset)
        totalWidth = icon.dragSeqImage.width + bodyWidth
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
            txtImg = icon.iconBoxedText('@')
            img.paste(txtImg, (bodyOffset, 0))
            inImageY = self.sites.argIcon.yOffset - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.argIcon.xOffset, inImageY))
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
        layout.doSubLayouts(self.sites.seqInsert, left, top + bodyHeight // 2)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.argIcon.att is None:
            argLayouts = [None]
        else:
            argLayouts = self.sites.argIcon.att.calcLayouts()
        width, height = self.bodySize
        layouts = []
        for attrLayout in argLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(attrLayout, 'argIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return '@'

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText('@')
        argSaveText = icon.argSaveText(parentBreakLevel, self.sites.argIcon,
            contNeeded, export)
        text.concat(None, argSaveText, contNeeded)
        return text

    def dumpName(self):
        return '@'

    def createAst(self):
        # The decorator icon does not produce any code.  The decorated function or class
        # def calls our createAstForAppliedIc method (below) to generate the associated
        # code.  However we do generate errors associated with the icon.  Technically,
        # the python compiler will catch all of these, but the Python messages are
        # unhelpful 'syntax error' or generic expression error.
        argIcon = self.childAt('argIcon')
        if argIcon is None:
            raise icon.IconExecException(self, "Expected decorator function")
        if not isinstance(argIcon, IdentifierIcon):
            raise icon.IconExecException(self, "Invalid decorator name")
        attr = argIcon.childAt('attrIcon')
        while isinstance(attr, AttrIcon):
            attr.errHighlight = None
            attr = attr.childAt('attrIcon')
        if isinstance(attr, listicons.CallIcon) and attr.childAt('attrIcon'):
            raise icon.IconExecException(self,
                "Nothing can follow decorator function argument list")
        if attr is not None:
            raise icon.IconExecException(self, "Decorator can only accept decorator "
                "function name, module components, and arguments")
        if not isFollowedByDefOrClass(self):
            raise icon.IconExecException(self,
                "Decorator must be followed by a def or class statement")

    def createAstForAppliedIc(self, forIc):
        """The createAst call for a decorator does nothing because decorator ASTs are
        attached to the decorated statement, as opposed to the decorator statement."""
        argIcon = self.childAt('argIcon')
        if argIcon is None:
            raise icon.IconExecException(self, "No decorator specified")
        else:
            return argIcon.createAst()

    def textEntryHandler(self, entryIc, text, onAttr):
        # Prohibit from typing anything but a name, attributes, or call icon directly on
        # our (decorator icon) input site or its direct attributes. Within the call
        # argument list, users can still type whatever the call icon allows.  Once the
        # user has mangled it (through deletion, paste, or snapping), relax the rules
        # and allow anything (bad stuff will be highlighted).
        if self.siteOf(entryIc, recursive=True) != 'argIcon':
            return None
        onIcon = entryIc.attachedIcon()
        if onIcon is self:
            # Entry icon is directly on the input site of the '@'
            if text.isidentifier():
                return "accept"
            elif text[-1] in ' .(' and text[:-1].isidentifier():
                if text[:-1] in entryicon.keywords:
                    return "reject:%s is a reserved keyword and cannot be used " \
                        "as a decorator or module name" % text[:-1]
                return IdentifierIcon(text[:-1], self.window), text[-1]
            return "reject:Decorator name must be a valid identifier"
        else:
            argIcon = self.childAt('argIcon')
            if not isinstance(argIcon, IdentifierIcon):
                # The user has managed to mess up the decorator syntax.  Let them type
                # anything, but highlight to show it's wrong
                return None
            attr = argIcon.childAt('attrIcon')
            while isinstance(attr, AttrIcon):
                attr = attr.childAt('attrIcon')
            if attr is entryIc:
                # The entry icon is on an appropriate attribute site
                if text == '(' or text == '.' or text[0] == '.' and (
                        text[1:].isidentifier() or text[1:-1].isidentifier() and
                        text[-1] in ' .('):
                    return None
                return "reject:Decorator can only accept decorator name and module " \
                        "components, optionally followed by '(' (if it takes " \
                        "arguments)"
            if isinstance(attr, listicons.CallIcon):
                # Anything can appear within call arguments, but not after
                if attr.childAt('attrIcon') is entryIc:
                    return "reject:Nothing can follow decorator argument list"
                return None
            # The user has managed to get something other than attributes or a call after
            # the decorator.  Let them type anything, but highlight to show it's wrong
            return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        if isFollowedByDefOrClass(self):
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight(
                "Decorator is not followed by a def or class statement")
        argIcon = self.childAt('argIcon')
        if argIcon is None:
            return
        if not isinstance(argIcon, IdentifierIcon):
            argIcon.highlightErrors(icon.ErrorHighlight("Invalid decorator name"))
            return
        attr = argIcon.childAt('attrIcon')
        while isinstance(attr, AttrIcon):
            attr.errHighlight = None
            attr = attr.childAt('attrIcon')
        if attr is None:
            argIcon.highlightErrors(None)
            return
        if isinstance(attr, listicons.CallIcon):
            # Anything can appear within call arguments, but not after.  For simplicity,
            # we start by calling highlightErrors all of the call icon's children,
            # including the unwanted attribute, and re-highlight the attribute.
            attr.highlightErrors(None)
            callAttr = attr.childAt('attrIcon')
            if callAttr is not None:
                callAttr.highlightErrors(icon.ErrorHighlight(
                    "Nothing can follow decorator argument list"))
            return
        attr.highlightErrors(icon.ErrorHighlight("Decorator can only accept decorator "
            "name, module components, and arguments"))

    def snapLists(self, forCursor=False):
        # Make snapping on attribute site conditional on icon being a call icon
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            return isinstance(ic, IdentifierIcon)
        inputSites = snapLists['input']
        snapLists['input'] = []
        snapLists['conditional'] = [(*inputSites[0], 'input', snapFn)]
        return snapLists

    def backspace(self, siteId, evt):
        self.window.backspaceIconToEntry(evt, self, '@', pendingArgSite=siteId)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.dragSeqImage.width
            textOriginY = self.rect[1] + comn.rectHeight(self.rect) // 2
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.boldFont, '@')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, '@', 'argIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'argIcon':
            return self.window.replaceIconWithEntry(self, '@', 'argIcon')
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

def moduleNameFromIcons(ic):
    if isinstance(ic, RelativeImportIcon):
        arg = ic.arg()
        icName = ic.level * '.'
    elif isinstance(ic, IdentifierIcon):
        arg = ic.sites.attrIcon.att
        icName = ic.name
    elif isinstance(ic, AttrIcon):
        arg = ic.sites.attrIcon.att
        icName = '.' + ic.Name
    else:
        return None  # Bad icon type
    if arg is None:
        return icName
    argName = moduleNameFromIcons(arg)
    if argName is None:
        return None  # Bad icon type somewhere within arg
    return icName + argName

def moduleNameToIcons(name, level, window):
    if name is None:
        baseIdentifier = None
    else:
        components = name.split('.')
        baseIdentName = components[0]
        baseIdentifier = IdentifierIcon(baseIdentName, window)
        rightIc = baseIdentifier
        for component in components[1:]:
            attr = AttrIcon(component, window)
            rightIc.replaceChild(attr, 'attrIcon')
            rightIc = attr
    if level == 0:
        return baseIdentifier
    relativeIcon = RelativeImportIcon(level, window)
    relativeIcon.replaceChild(baseIdentifier, 'argIcon')
    return relativeIcon

def createIconForNameField(astNode, nameFieldString, window, fieldIdx=0):
    """Same as plural version of the call for a single field (the more common case)."""
    icons = createIconsForNameFields(astNode, (nameFieldString,), window, fieldIdx)
    return icons[0]

def createIconsForNameFields(astNode, nameFieldStrings, window, startIdx=0):
    """For AST nodes that have text fields where we allow arbitrary icons, a macro,
    such as $Ctx$ or $Empty$ may provide something other than a name.  Look for a
    .fieldMacroAnnotations annotation on the ast node, and if it exists, check if any
    of the fields have corresponding macro data, and can be used to create the icon(s)
    for the field.  If so, use that, otherwise, create an identifier for each field
    annotation exists use the referenced macro(s) to create the icon(s).  Otherwise
    just create an identifier icon the corresponding nameFieldString as its name.  If
    startIdx is specified, skip the first startX fields"""
    if not hasattr(astNode, 'fieldMacroAnnotations'):
        return [IdentifierIcon(s, window) for s in nameFieldStrings]
    icons = []
    for name, ann in zip(nameFieldStrings, astNode.fieldMacroAnnotations[startIdx:]):
        if ann is None:
            icons.append(IdentifierIcon(name, window))
        else:
            macroName, macroArgs, iconCreateFn, argAsts = ann
            if iconCreateFn is not None:
                icons.append(iconCreateFn(None, macroArgs, argAsts, window))
            else:
                icons.append(IdentifierIcon(name, window))
    return icons

def createNameFieldSaveText(brkLvl, site, needsCont, export):
    """Create file/paste text to represent the content of a field where Python will only
    accept a simple identifier, but is an input site in the icon representation and so
    may contain any sort of expression.  Generates a $Ctx$ macro to hold anything that
    is not an identifier."""
    if site.att is None or isinstance(site.att, IdentifierIcon) or export:
        return icon.argSaveText(brkLvl, site, needsCont, export)
    argText = icon.argSaveText(brkLvl+1, site, needsCont, export)
    argText.wrapCtxMacro(brkLvl, parseCtx=None, needsCont=needsCont)
    return argText

# Getting resources (particularly icon class definitions) from other icon files requires
# circular imports, unfortunately.  Here, the import is deferred far enough down the file
# that the dependencies can resolve.
import blockicons, commenticon

def isOutsideOfDef(iconToTest):
    for ic in icon.traverseSeq(iconToTest, includeStartingIcon=False, reverse=True,
            skipInnerBlocks=True):
        if isinstance(ic, blockicons.ClassDefIcon):
            return True
        if isinstance(ic, blockicons.DefIcon):
            return False
    return True

def isOutsideOfLoop(iconToTest):
    for ic in icon.traverseSeq(iconToTest, includeStartingIcon=False, reverse=True,
            skipInnerBlocks=True):
        if isinstance(ic, (blockicons.ClassDefIcon, blockicons.DefIcon)):
            return True
        if isinstance(ic, (blockicons.ForIcon, blockicons.WhileIcon)):
            return False
    return True

def isFollowedByDefOrClass(iconToTest):
    for seqIc in icon.traverseSeq(iconToTest, includeStartingIcon=False):
        if isinstance(seqIc, (commenticon.CommentIcon, commenticon.VerticalBlankIcon,
                DecoratorIcon)):
            continue
        return isinstance(seqIc, (blockicons.DefIcon, blockicons.ClassDefIcon))
    return False

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
    if isinstance(astNode.value, ast.Tuple) and not \
            hasattr(astNode.value, 'tupleHasParens'):
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
        if alias.name.find('.') != -1:
            # Assume a macro won't inject a dotted name just to reprocess it, and avoid
            # calling createIconForNameField, which would create a dotted identifier.
            nameIcon = moduleNameToIcons(alias.name, 0, window)
            if alias.asname is None:
                asNameIcon = None
            else:
                asNameIcon = createIconForNameField(alias, alias.asname, window, 1)
        elif alias.asname is None:
            nameIcon = createIconForNameField(alias, alias.name, window)
            asNameIcon = None
        else:
            nameIcon, asNameIcon = createIconsForNameFields(alias,
                (alias.name, alias.asname), window)
        if alias.asname is None:
            aliases.append(nameIcon)
        else:
            asIcon = infixicon.AsIcon(window)
            asIcon.replaceChild(nameIcon, 'leftArg')
            asIcon.replaceChild(asNameIcon, 'rightArg')
            aliases.append(asIcon)
    topIcon.insertChildren(aliases, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Import, createImportIconFromAst)

def createImportFromIconFromAst(astNode, window):
    topIcon = ImportFromIcon(window)
    if astNode.module is None or astNode.level > 0 or astNode.module.find('.') != -1:
        # If module name is missing or contains a dot, use moduleNameToIcons to create an
        # attribute chain to represent the dots.  moduleNameToIcons will not process
        # associated macros, but none of our macros operate on a dotted form, and we
        # don't publicise that macros even work for fields that don't hold asts.
        moduleNameIcon = moduleNameToIcons(astNode.module, astNode.level, window)
    else:
        moduleNameIcon = createIconForNameField(astNode, astNode.module, window)
    topIcon.replaceChild(moduleNameIcon, 'moduleIcon')
    aliases = []
    for alias in astNode.names:
        if alias.asname is None:
            nameIcon = createIconForNameField(alias, alias.name, window)
            asNameIcon = None
        else:
            nameIcon, asNameIcon = createIconsForNameFields(alias,
                (alias.name, alias.asname), window)
        if alias.asname is None:
            aliases.append(nameIcon)
        else:
            asIcon = infixicon.AsIcon(window)
            asIcon.replaceChild(nameIcon, 'leftArg')
            asIcon.replaceChild(asNameIcon, 'rightArg')
            aliases.append(asIcon)
    topIcon.insertChildren(aliases, "importsIcons", 0)
    return topIcon
icon.registerIconCreateFn(ast.ImportFrom, createImportFromIconFromAst)

def createModuleNameIconFromFakeAst(astNode, window):
    return moduleNameToIcons(astNode.moduleName, astNode.level, window)
icon.registerIconCreateFn(filefmt.RelImportNameFakeAst, createModuleNameIconFromFakeAst)

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
    nameIcons = createIconsForNameFields(astNode, astNode.names, window)
    topIcon.insertChildren(nameIcons, "values", 0)
    return topIcon
icon.registerIconCreateFn(ast.Global, createGlobalIconFromAst)

def createNonlocalIconFromAst(astNode, window):
    topIcon = NonlocalIcon(window)
    nameIcons = createIconsForNameFields(astNode, astNode.names, window)
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
    if filefmt.isAttrParseStub(astNode.value):
        return attrIcon    # This is a free attribute on the top level
    topIcon = icon.createFromAst(astNode.value, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(attrIcon, "attrIcon")
    return topIcon
icon.registerIconCreateFn(ast.Attribute, createAttrIconFromAst)

def createYieldIconFromAst(astNode, window):
    topIcon = YieldIcon(window)
    if astNode.value is None:
        return topIcon
    if isinstance(astNode.value, ast.Tuple) and not \
            hasattr(astNode.value, 'tupleHasParens'):
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
