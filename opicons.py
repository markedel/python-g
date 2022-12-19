# Copyright Mark Edel  All rights reserved
import ast
import numbers
from PIL import Image, ImageDraw
import iconlayout
import iconsites
import icon
import filefmt
import operator
import comn
import re

DEPTH_EXPAND = 4

isKwdPattern = re.compile('^[a-z ]*$')

lParenImage = comn.asciiToImage((
 "..ooooooo",
 "..o     o",
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
 "..o     o",
 "..ooooooo"))

rParenImage = comn.asciiToImage((
 "oooooooo",
 "o      o",
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
 "o      o",
 "oooooooo"))

binOutImage = comn.asciiToImage((
 "..ooo",
 ".o  o",
 "o   o",
 ".o  o",
 "..ooo"))

binInSeqImage = comn.asciiToImage((
 "ooo",
 "ooo",
 "ooo",
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
 "ooo",
 "ooo",
 "ooo"))

floatInImage = comn.asciiToImage((
 "ooo",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "ooo"))

binOpPrecedence = {'+':10, '-':10, '*':11, '/':11, '//':11, '%':11, '**':14,
 '<<':9, '>>':9, '|':6, '^':7, '&':8, '@':11, 'and':3, 'or':2, 'in':5, 'not in':5,
 'is':5, 'is not':5, '<':5, '<=':5, '>':5, '>=':5, '==':5, '!=':5, '=':-1, ':':-1}

unaryOpPrecedence = {'+':12, '-':12, '~':13, 'not':4, '*':-1, '**':-1, 'yield from':-1,
 'await':-1}

unaryOpFn = {'+':operator.pos, '-':operator.neg, '~':operator.inv, 'not':operator.not_,
 '*':lambda a:a, '**': lambda a:a, 'await': lambda a:a}

unaryOpAsts = {'+':ast.UAdd, '-':ast.USub, '~':ast.Invert, 'not':ast.Not}

binOpFn = {'+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv,
 '//':operator.floordiv, '%':operator.mod, '**':operator.pow, '<<':operator.lshift,
 '>>':operator.rshift, '|':operator.or_, '^':operator.xor, '&':operator.and_,
 '@':lambda x,y:x@y, 'and':lambda x,y:x and y, 'or':lambda x,y:x or y,
 'in':lambda x,y:x in y, 'not in':lambda x,y:x not in y, 'is':operator.is_,
 'is not':operator.is_not, '<':operator.lt, '<=':operator.le, '>':operator.gt,
 '>=':operator.ge, '==':operator.eq, '!=':operator.ne}

binOpAsts = {'+':ast.Add, '-':ast.Sub, '*':ast.Mult, '/':ast.Div, '//':ast.FloorDiv,
 '%':ast.Mod, '**':ast.Pow, '<<':ast.LShift, '>>':ast.RShift, '|':ast.Or, '^':ast.BitXor,
 '&':ast.BitAnd}

compareAsts = {'is':ast.Is, 'is not':ast.IsNot, '<':ast.Lt, '<=':ast.LtE, '>':ast.Gt,
 '>=':ast.GtE, '==':ast.Eq, '!=':ast.NotEq}

binOps = {ast.Add:'+', ast.Sub:'-', ast.Mult:'*', ast.Div:'/', ast.FloorDiv:'//',
 ast.Mod:'%', ast.Pow:'**', ast.LShift:'<<', ast.RShift:'>>', ast.BitOr:'|',
 ast.BitXor:'^', ast.BitAnd:'&', ast.MatMult:'@'}

unaryOps = {ast.UAdd:'+', ast.USub:'-', ast.Not:'not', ast.Invert:'~'}

boolOps = {ast.And:'and', ast.Or:'or'}

compareOps = {ast.Eq:'==', ast.NotEq:'!=', ast.Lt:'<', ast.LtE:'<=', ast.Gt:'>',
 ast.GtE:'>=', ast.Is:'is', ast.IsNot:'is not', ast.In:'in', ast.NotIn:'not in'}

class UnaryOpIcon(icon.Icon):
    def __init__(self, op, window, location=None):
        icon.Icon.__init__(self, window)
        self.operator = op
        self.precedence = unaryOpPrecedence[op]
        if isKwdPattern.fullmatch(op):
            self.font = icon.boldFont
            self.color = icon.KEYWORD_COLOR
        else:
            self.font = icon.globalFont
            self.color = (0, 0, 0, 255)
        bodyWidth, bodyHeight = icon.getTextSize(self.operator, self.font)
        bodyHeight = max(icon.minTxtHgt, bodyHeight)
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('argIcon', 'input', bodyWidth - 1, siteYOffset)
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
#            width, height = icon.getTextSize(self.operator, self.font)
            bodyLeft = icon.outSiteImage.width - 1
            bodyWidth, bodyHeight = self.bodySize
#            bodyWidth = width + 2 * icon.TEXT_MARGIN
#            bodyHeight = height + 2 * icon.TEXT_MARGIN
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth  - 1, bodyHeight - 1),
             fill=comn.ICON_BG_COLOR, outline=comn.OUTLINE_COLOR)
            if needOutSite:
                outImageY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (0, outImageY))
            inImageY = self.sites.argIcon.yOffset - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (self.sites.argIcon.xOffset, inImageY))
            if needSeqSites:
                icon.drawSeqSites(img, bodyLeft, 0, bodyHeight+1)
            if self.operator in ('+', '-', '~'):
                # Raise unary operators up and move then to the left.  Not sure if this
                # is safe for all fonts, but the Ariel font we're using pads on top.
                textTop = -1 if self.operator == '+' else -2
                textLeft = bodyLeft + 2 * icon.TEXT_MARGIN
            else:
                textTop = icon.TEXT_MARGIN
                textLeft = bodyLeft + icon.TEXT_MARGIN + 1
            draw.text((textLeft, textTop), self.operator, font=self.font, fill=self.color)
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def arg(self):
        return self.sites.argIcon.att

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += icon.outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.argIcon.att is None:
            argLayouts = (None,)
        else:
            argLayouts = self.sites.argIcon.att.calcLayouts()
        width, height = self.bodySize
        layouts = []
        for argLayout in argLayouts:
            layout = iconlayout.Layout(self, width, height, height // 2)
            layout.addSubLayout(argLayout, 'argIcon', width-1, 0)
            if argLayout is None:
                layout.width += icon.EMPTY_ARG_WIDTH
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        addSpace = " " if self.operator[-1].isalpha() else ""
        return self.operator + addSpace + icon.argTextRepr(self.sites.argIcon)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        addSpace = " " if self.operator[-1].isalpha() else ""
        text = filefmt.SegmentedText(self.operator + addSpace)
        arg = icon.argSaveText(parentBreakLevel, self.sites.argIcon, contNeeded, export)
        text.concat(None, arg, contNeeded)
        return text

    def dumpName(self):
        return "unary " + self.operator

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, op=self.operator)

    def execute(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument")
        argValue = self.arg().execute()
        try:
            result = unaryOpFn[self.operator](argValue)
        except Exception as err:
            raise icon.IconExecException(self, err)
        return result

    def createAst(self):
        if self.arg() is None:
            raise icon.IconExecException(self, "Missing argument")
        operandAst = self.arg().createAst()
        return ast.UnaryOp(unaryOpAsts[self.operator](), operandAst, lineno=self.id,
         col_offset=0)

    def backspace(self, siteId, evt):
        self.window.backspaceIconToEntry(evt, self, self.operator, pendingArgSite=siteId)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.TEXT_MARGIN + icon.outSiteImage.width
            textOriginY = self.rect[1] + self.sites.output.yOffset
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, self.font, self.operator)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self.window.replaceIconWithEntry(self, self.operator, 'argIcon')
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'argIcon':
            return self.window.replaceIconWithEntry(self, self.operator, 'argIcon')
        return None

    def compareData(self, data):
        # The UnaryOp icon can be used in data representation (though maybe it should not
        # be), so must supply a function for checking against real data.  The only case
        # in which it is considered legitimate as data, is when its argument is a single
        # positive numeric value.  Any other use is considered code and rejected.
        if self.operator != "-":
            return False
        if not isinstance(data, numbers.Number) or isinstance(data, complex):
            return False
        if data >= 0:
            return False
        argIcon = self.sites.argIcon.att
        return argIcon is not None and argIcon.compareData(-data)

class BinOpIcon(icon.Icon):
    def __init__(self, op, window, location=None):
        icon.Icon.__init__(self, window)
        self.operator = op
        if isKwdPattern.fullmatch(op):
            self.font = icon.boldFont
            self.color = icon.KEYWORD_COLOR
        else:
            self.font = icon.globalFont
            self.color = (0, 0, 0, 255)
        self.precedence = binOpPrecedence[op]
        self.hasParens = False  # Filled in by layout methods
        self.leftArgWidth = icon.EMPTY_ARG_WIDTH
        self.rightArgWidth = icon.EMPTY_ARG_WIDTH
        opWidth, opHeight = icon.getTextSize(self.operator, self.font)
        opHeight = max(opHeight + 2*icon.TEXT_MARGIN + 1, lParenImage.height)
        opWidth += 2*icon.TEXT_MARGIN - 1
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
         self.leftArgWidth + opWidth - icon.ATTR_SITE_DEPTH, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - icon.SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - icon.SEQ_SITE_DEPTH, height-2)
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

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
            leftArgX = outSiteX + icon.outSiteImage.width - 1
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
            txtImg = icon.iconBoxedText(self.operator, self.font, color=self.color)
            opWidth, opHeight = self.opSize
            opWidth = txtImg.width + self.depthWidth
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            opX = leftArgX + self.leftArgWidth - 1
            opY = siteY - txtImg.height // 2
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 0, opWidth - 1, txtImg.height - 1),
                 outline=comn.OUTLINE_COLOR, fill=comn.ICON_BG_COLOR)
                txtSubImg = txtImg.crop((1, 0, txtImg.width - 1, txtImg.height))
                img.paste(txtSubImg, (self.depthWidth // 2 + 1, opY))
            else:
                img.paste(txtImg, (self.depthWidth // 2, opY))
            rInSiteX = opWidth - icon.inSiteImage.width
            rInSiteY = siteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (rInSiteX, rInSiteY))
            self.drawList.append(((opX, 0), img))
            # End paren
            if self.hasParens:
                rParenX = opX + opWidth - 1 + self.rightArgWidth - 1
                rParenY = siteY - rParenImage.height // 2
                self.drawList.append(((rParenX, rParenY), rParenImage))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryOutputSite or suppressSeqSites:
            self.drawList = None  # Don't keep after drawing (see above)

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
        self.sites.attrIcon.order = 2 if self.hasParens else None
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

    def calcLayouts(self):
        hasParens = needsParens(self)
        if hasParens:
            lParenWidth = lParenImage.width - icon.OUTPUT_SITE_DEPTH - 1
            rParenWidth = rParenImage.width - 1
        else:
            lParenWidth = rParenWidth = 0
        opWidth, opHeight = self.opSize
        lArg = self.leftArg()
        lArgLayouts = [None] if lArg is None else lArg.calcLayouts()
        rArg = self.rightArg()
        rArgLayouts = [None] if rArg is None else rArg.calcLayouts()
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        layouts = []
        for lArgLayout, rArgLayout, attrLayout in iconlayout.allCombinations((lArgLayouts,
                rArgLayouts, attrLayouts)):
            layout = iconlayout.Layout(self, opWidth, opHeight, opHeight // 2)
            layout.hasParens = hasParens
            layout.addSubLayout(lArgLayout, "leftArg", lParenWidth, 0)
            lArgWidth = icon.EMPTY_ARG_WIDTH if lArgLayout is None else lArgLayout.width
            layout.lArgWidth = lArgWidth
            depthWidth = self.depth() * DEPTH_EXPAND
            layout.depthWidth = depthWidth
            rArgSiteX = lParenWidth + lArgWidth + opWidth + depthWidth
            layout.addSubLayout(rArgLayout, "rightArg", rArgSiteX, 0)
            rArgWidth = icon.EMPTY_ARG_WIDTH if rArgLayout is None else rArgLayout.width
            layout.rArgWidth = rArgWidth
            layout.width = rArgSiteX + rArgWidth + rParenWidth
            layout.addSubLayout(attrLayout, 'attrIcon',
                    layout.width - icon.ATTR_SITE_DEPTH, icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def snapLists(self, forCursor=False):
        # Make attribute site unavailable unless the icon has parens to hold it
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if not self.hasParens:
            del siteSnapLists['attrIn']
        return siteSnapLists

    def textRepr(self):
        leftArgText = icon.argTextRepr(self.sites.leftArg)
        rightArgText = icon.argTextRepr(self.sites.rightArg)
        text = leftArgText + " " + self.operator + " " + rightArgText
        if self.hasParens:
            return "(" + text + ")" + icon.attrTextRepr(self)
        return text

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        hasParens = needsParens(self, forText=True)
        brkLvl = parentBreakLevel + 1
        # If this operation is part of an associative grouping, don't add to level
        if not hasParens:
            parent = self.parent()
            if parent is not None and parent.__class__ is BinOpIcon:
                if parent.precedence == self.precedence:
                    brkLvl = parentBreakLevel
        if hasParens:
            contNeeded = False
        leftArgText = icon.argSaveText(brkLvl, self.sites.leftArg, contNeeded, export)
        if hasParens:
            text = filefmt.SegmentedText('(')
            text.concat(brkLvl, leftArgText, contNeeded)
        else:
            text = leftArgText
        text.add(None, " " + self.operator + " ", contNeeded)
        rightArgText = icon.argSaveText(brkLvl, self.sites.rightArg, contNeeded, export)
        text.concat(brkLvl, rightArgText, contNeeded)
        if hasParens:
            text.add(None, ")")
        return text

    def canPlaceArgs(self, placementList, startSiteId=None, overwriteStart=False):
        iconToPlace, placeListIdx, seriesIdx = icon.firstPlaceListIcon(placementList)
        if iconToPlace is None:
            return None, None
        siteId = 'leftArg' if startSiteId is None else startSiteId
        if not icon.validateCompatibleChild(iconToPlace, self, siteId):
            return None, None
        if not overwriteStart and self.childAt(siteId):
            return None, None
        return placeListIdx, seriesIdx

    def placeArgs(self, placementList, startSiteId=None, overwriteStart=False):
        placeListIdx, seriesIdx = self.canPlaceArgs(placementList, startSiteId,
            overwriteStart)
        if placeListIdx is None:
            return None, None
        if seriesIdx is None:
            argIcon = placementList[placeListIdx]
        else:
            argIcon = placementList[placeListIdx][seriesIdx]
        siteId = 'leftArg' if startSiteId is None else startSiteId
        self.replaceChild(argIcon, siteId)
        reorderexpr.reorderArithExpr(self)
        return placeListIdx, seriesIdx

    def dumpName(self):
        return ("(%s)" if self.hasParens else "%s") % self.operator

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, op=self.operator)

    def locIsOnLeftParen(self, btnPressLoc):
        iconLeft = self.rect[0]
        return iconLeft < btnPressLoc[0] < iconLeft + lParenImage.width

    def leftAssoc(self):
        return self.operator != "**"

    def rightAssoc(self):
        return self.operator == "**"

    def execute(self):
        if self.leftArg() is None:
            raise icon.IconExecException(self, "Missing left operand")
        if self.rightArg() is None:
            raise icon.IconExecException(self, "Missing right operand")
        leftValue = self.leftArg().execute()
        rightValue = self.rightArg().execute()
        try:
            result = binOpFn[self.operator](leftValue, rightValue)
        except Exception as err:
            raise icon.IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if self.leftArg() is None:
            raise icon.IconExecException(self, "Missing left operand")
        if self.rightArg() is None:
            raise icon.IconExecException(self, "Missing right operand")
        if self.operator in compareAsts:
            leftArgAst = self.leftArg().createAst()
            ops = [compareAsts[self.operator]()]
            comparators = [self.rightArg().createAst()]
            if isinstance(leftArgAst, ast.Compare) and not self.leftArg().hasParens:
                # This is a chained comparison.  Extend the chain.  Note: I *think* the
                # hasParens check, above, is unnecessary, since all comparison operators
                # have the same precedence and are left-associative, but it's a cheap
                # test that will handle the problem completely in case I'm wrong.
                ops = leftArgAst.ops + ops
                comparators = leftArgAst.comparators + comparators
                leftArgAst = leftArgAst.left
            return ast.Compare(left=leftArgAst, ops=ops, comparators=comparators,
                lineno=self.id, col_offset=0)
        return ast.BinOp(lineno=self.id, col_offset=0, left=self.leftArg().createAst(),
            op=binOpAsts[self.operator](), right=self.rightArg().createAst())

    def selectionRect(self):
        # Limit selection rectangle for extending selection to op itself
        opWidth, opHeight = self.opSize
        opWidth += self.depthWidth
        rightOffset = self.sites.rightArg.xOffset + icon.OUTPUT_SITE_DEPTH
        leftOffset = rightOffset - opWidth
        x, top = self.rect[:2]
        left = x + leftOffset
        return left, top, left + opWidth, top + opHeight

    def inRectSelect(self, rect):
        if not comn.rectsTouch(rect, self.rect):
            return False
        return comn.rectsTouch(rect, self.selectionRect())

    def backspace(self, siteId, evt):
        backspaceBinOpIcon(self, siteId, evt)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            depthWidth = (self.depthWidth // 2 + 1) if self.depthWidth > 0 else 0
            textOriginX = self.rect[0] + self.sites.output.xOffset + depthWidth + \
                icon.outSiteImage.width + self.leftArgWidth + icon.TEXT_MARGIN - 2
            textOriginY = self.rect[1] + self.sites.output.yOffset
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, self.font, self.operator,
                padLeft=depthWidth, padRight=depthWidth)
            if cursorTextIdx is None:
                return None, None
            entryIcon = _becomeEntryIcon(self)
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'rightArg':
            return _becomeEntryIcon(self)
        return None

    def updateParens(self):
        needs = needsParens(self)
        if needs and not self.hasParens:
            self.hasParens = True
            self.sites.attrIcon.order = 2
        elif self.hasParens and not needs:
            self.hasParens = False
            self.sites.attrIcon.order = None

class DivideIcon(icon.Icon):
    def __init__(self, floorDiv=False, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.precedence = 11
        self.floorDiv = floorDiv
        emptyArgHeight = 14
        self.emptyArgSize = (icon.EMPTY_ARG_WIDTH, emptyArgHeight)
        self.topArgSize = self.emptyArgSize
        self.bottomArgSize = self.emptyArgSize
        width, height = self._size()
        outSiteY = self.topArgSize[1] + 2
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('topArg', 'input', 2, outSiteY - emptyArgHeight // 2 - 2)
        self.sites.add('bottomArg', 'input', 2, outSiteY + emptyArgHeight // 2 + 2)
        self.sites.add('attrIcon', 'attrIn', width - 1, outSiteY + icon.ATTR_SITE_OFFSET)
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
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
        width = max(topWidth, bottomWidth) + 3 + icon.outSiteImage.width
        height = topHeight + bottomHeight + 3
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
            bodyLeft = icon.outSiteImage.width - 1
            bodyRight = width - 1
            cntrY = 5
            bodyHeight = 11
            img = Image.new('RGBA', (width, bodyHeight), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyRight, bodyHeight-1),
             outline=comn.OUTLINE_COLOR, fill=comn.ICON_BG_COLOR)
            if needSeqSites:
                icon.drawSeqSites(img, bodyLeft, 0, bodyHeight)
            if self.floorDiv:
                cntrX = (bodyLeft + bodyRight) // 2
                draw.line((bodyLeft + 2, cntrY, cntrX - 1, cntrY), fill=icon.BLACK)
                draw.line((cntrX + 2, cntrY, bodyRight - 2, cntrY), fill=icon.BLACK)
            else:
                draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=icon.BLACK)
            bodyTop = self.sites.output.yOffset - 5
            if needOutSite:
                img.paste(icon.outSiteImage, (0, cntrY - icon.outSiteImage.height//2))
            self.drawList.append(((0, bodyTop), img))
        self._drawFromDrawList(toDragImage, location, clip, style)

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

    def calcLayouts(self):
        topArg = self.sites.topArg.att
        tArgLayouts = [None] if topArg is None else topArg.calcLayouts()
        bottomArg = self.sites.bottomArg.att
        bArgLayouts = [None] if bottomArg is None else bottomArg.calcLayouts()
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        layouts = []
        for tArgLayout, bArgLayout, attrLayout in iconlayout.allCombinations((tArgLayouts,
                bArgLayouts, attrLayouts)):
            if tArgLayout is None:
                tArgWidth, tArgHeight = self.emptyArgSize
                tArgSiteOffset = tArgHeight // 2
            else:
                tArgWidth = tArgLayout.width
                tArgHeight = tArgLayout.height
                tArgSiteOffset = tArgLayout.parentSiteOffset
            if bArgLayout is None:
                bArgWidth, bArgHeight = self.emptyArgSize
                bArgSiteOffset = bArgHeight // 2
            else:
                bArgWidth = bArgLayout.width
                bArgHeight = bArgLayout.height
                bArgSiteOffset = bArgLayout.parentSiteOffset
            width = max(tArgWidth, bArgWidth) + 4
            height = tArgHeight + bArgHeight + 3
            siteYOff = tArgHeight + 1
            layout = iconlayout.Layout(self, width, height, siteYOff)
            layout.topArgSize = tArgWidth, tArgHeight
            layout.bottomArgSize = bArgWidth, bArgHeight
            layout.addSubLayout(tArgLayout, 'topArg', (width - tArgWidth) // 2,
             - tArgHeight + tArgSiteOffset - 1)
            layout.addSubLayout(bArgLayout, 'bottomArg', (width - bArgWidth) // 2,
             + bArgSiteOffset + 2)
            layout.addSubLayout(attrLayout, 'attrIcon', width, icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        topArgText = icon.argTextRepr(self.sites.topArg)
        bottomArgText = icon.argTextRepr(self.sites.bottomArg)
        op = '//' if self.floorDiv else '/'
        text = topArgText + " " + op + " " + bottomArgText
        if needsParens(self, forText=True):
            return "(" + text + ")" + icon.attrTextRepr(self)
        return text

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        hasParens = needsParens(self, forText=True)
        op = '//' if self.floorDiv else '/'
        brkLvl = parentBreakLevel + 1
        # If this operation is part of an associative grouping, don't add to level
        if not hasParens:
            parent = self.parent()
            if parent is not None and parent.__class__ is BinOpIcon:
                if parent.precedence == self.precedence:
                    brkLvl = parentBreakLevel
        if hasParens:
            contNeeded = False
        leftArgText = icon.argSaveText(brkLvl, self.sites.topArg, contNeeded, export)
        if hasParens:
            text = filefmt.SegmentedText('(')
            text.concat(brkLvl, leftArgText, contNeeded)
        else:
            text = leftArgText
        text.add(None, " " + op + " ", contNeeded)
        rightArgText = icon.argSaveText(brkLvl, self.sites.bottomArg, contNeeded, export)
        text.concat(brkLvl, rightArgText, contNeeded)
        if hasParens:
            text.add(None, ")")
        return text

    def dumpName(self):
        return '//' if self.floorDiv else '/'

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, floorDiv=self.floorDiv)

    def leftAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return True

    def rightAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return False

    def execute(self):
        if self.sites.topArg.att is None:
            raise icon.IconExecException(self, "Missing numerator")
        if self.sites.bottomArg.att is None:
            raise icon.IconExecException(self, "Missing denominator")
        topValue = self.sites.topArg.att.execute()
        bottomValue = self.sites.bottomArg.att.execute()
        try:
            if self.floorDiv:
                result = operator.floordiv(topValue, bottomValue)
            else:
                result = operator.truediv(topValue, bottomValue)
        except Exception as err:
            raise icon.IconExecException(self, err)
        return result

    def createAst(self):
        if self.sites.topArg.att is None:
            raise icon.IconExecException(self, "Missing numerator")
        if self.sites.bottomArg.att is None:
            raise icon.IconExecException(self, "Missing denominator")
        left = self.sites.topArg.att.createAst()
        right = self.sites.bottomArg.att.createAst()
        op = ast.FloorDiv() if self.floorDiv else ast.Div()
        return ast.BinOp(lineno=self.id, col_offset=0, left=left, op=op, right=right)

    def backspace(self, siteId, evt):
        backspaceBinOpIcon(self, siteId, evt)

class IfExpIcon(icon.Icon):
    """Ternary if-else expression"""
    hasTypeover = True

    def __init__(self, window, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        if typeover:
            self.typeoverIdx = 0
            self.window.watchTypeover(self)
        else:
            self.typeoverIdx = None
        self.precedence = 0
        self.hasParens = False  # Filled in by layout methods
        self.trueExprWidth = icon.EMPTY_ARG_WIDTH
        self.falseExprWidth = icon.EMPTY_ARG_WIDTH
        self.testExprWidth = icon.EMPTY_ARG_WIDTH
        ifWidth = icon.getTextSize('if', icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        elseWidth = icon.getTextSize('else', icon.boldFont)[0] + 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (ifWidth, elseWidth, icon.minTxtIconHgt)
        self.depthWidth = 0
        x, y = (0, 0) if location is None else location
        width, height = self._size()
        self.rect = (x, y, x + width, y + height)
        siteYOffset = height // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('trueExpr', 'input', 0, siteYOffset)
        testExprXOffset = self.testExprWidth-1 + ifWidth - icon.OUTPUT_SITE_DEPTH
        self.sites.add('testExpr', 'input', testExprXOffset, siteYOffset)
        falseExprXOffset = testExprXOffset-1 + self.testExprWidth-1 + elseWidth
        self.sites.add('falseExpr', 'input', falseExprXOffset, siteYOffset)
        # Note that the attrIcon site is only usable when parens are displayed
        self.sites.add("attrIcon", "attrIn",
         self.trueExprWidth + ifWidth - icon.ATTR_SITE_DEPTH, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - icon.SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - icon.SEQ_SITE_DEPTH, height-2)
        # Indicates that input site falls directly on top of output site
        self.coincidentSite = 'trueExpr'

    def _size(self):
        ifWidth, elseWidth, height = self.bodySize
        ifWidth += self.depthWidth
        if self.hasParens:
            parenWidth = lParenImage.width - 1 + rParenImage.width - 1
        else:
            parenWidth = 0
        width = parenWidth + self.trueExprWidth-1 + self.testExprWidth-1 + \
                self.falseExprWidth-1 + ifWidth-1 + elseWidth
        return width, height

    def leftArg(self):
        # Provided for BinOp compatibility
        return self.sites.trueExpr.att

    def rightArg(self):
        return self.sites.falseExpr.att

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
            trueExprX = outSiteX + icon.outSiteImage.width - 1
            if self.hasParens:
                outSiteY = siteY - lParenImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), lParenImage))
                trueExprX = outSiteX + lParenImage.width - 1
            elif temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binOutImage))
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - binInSeqImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binInSeqImage))
            # if body
            ifImg = icon.iconBoxedText("if", icon.boldFont, icon.KEYWORD_COLOR)
            ifWidth, elseWidth, height = self.bodySize
            ifWidth = ifImg.width + self.depthWidth // 2  # if gets half, else gets half
            img = Image.new('RGBA', (ifWidth, height), color=(0, 0, 0, 0))
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 0, ifWidth - 1, ifImg.height - 1),
                 outline=comn.OUTLINE_COLOR, fill=comn.ICON_BG_COLOR)
                ifSubImg = ifImg.crop((1, 0, ifImg.width - 1, ifImg.height))
                img.paste(ifSubImg, (self.depthWidth // 2 + 1, 0))
            else:
                img.paste(ifImg, (0, 0))
            ifInSiteX = ifWidth - icon.inSiteImage.width
            ifInSiteY = siteY - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (ifInSiteX, ifInSiteY))
            ifX = trueExprX + self.trueExprWidth - 1
            ifY = siteY - lParenImage.height // 2
            self.drawList.append(((ifX, ifY), img))
            # else body
            elseImg = icon.iconBoxedText("else", icon.boldFont, icon.KEYWORD_COLOR,
                typeover=self.typeoverIdx)
            elseWidth = elseImg.width + self.depthWidth // 2
            img = Image.new('RGBA', (elseWidth, height), color=(0, 0, 0, 0))
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 0, elseWidth - 1, elseImg.height - 1),
                    outline=comn.OUTLINE_COLOR, fill=comn.ICON_BG_COLOR)
                elseSubImg = elseImg.crop((1, 0, elseImg.width - 1, elseImg.height))
                img.paste(elseSubImg, (0, 0))
            else:
                img.paste(elseImg, (0, 0))
            elseInSiteX = elseWidth - icon.inSiteImage.width
            img.paste(icon.inSiteImage, (elseInSiteX, ifInSiteY))
            elseX = ifX + ifWidth - 1 + self.testExprWidth - 1
            self.drawList.append(((elseX, ifY), img))
            # End paren
            if self.hasParens:
                rParenX = elseX + elseWidth-1 + self.falseExprWidth-1
                self.drawList.append(((rParenX, 0), rParenImage))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryOutputSite or suppressSeqSites:
            self.drawList = None  # Don't keep after drawing (see above)

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
        if parent.__class__ in (BinOpIcon, IfExpIcon) and \
                parent.precedence == self.precedence:
            if parent.siteOf(self) == "trueExpr" and parent.leftAssoc():
                myDepth = max(myDepth, parent.depth(lDepth=myDepth))
            elif parent.siteOf(self) == "falseExpr" and parent.rightAssoc():
                myDepth = max(myDepth, parent.depth(rDepth=myDepth))
        return myDepth

    def doLayout(self, outSiteX, outSiteY, layout):
        self.hasParens = layout.hasParens
        self.sites.attrIcon.order = 3 if self.hasParens else None
        self.coincidentSite = None if self.hasParens else "trueExpr"
        self.trueExprWidth = layout.lArgWidth
        self.falseExprWidth = layout.rArgWidth
        self.testExprWidth = layout.testArgWidth
        self.depthWidth = layout.depthWidth
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        hasParens = needsParens(self)
        if hasParens:
            lParenWidth = lParenImage.width - icon.OUTPUT_SITE_DEPTH - 1
            rParenWidth = rParenImage.width - 1
        else:
            lParenWidth = rParenWidth = 0
        ifWidth, elseWidth, height = self.bodySize
        lArg = self.sites.trueExpr.att
        lArgLayouts = [None] if lArg is None else lArg.calcLayouts()
        testExpr = self.sites.testExpr.att
        testArgLayouts = [None] if testExpr is None else testExpr.calcLayouts()
        rArg = self.sites.falseExpr.att
        rArgLayouts = [None] if rArg is None else rArg.calcLayouts()
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        layouts = []
        for lArgLayout, testArgLayout, rArgLayout, attrLayout in iconlayout. \
                allCombinations((lArgLayouts, testArgLayouts, rArgLayouts, attrLayouts)):
            layout = iconlayout.Layout(self, ifWidth, height, height // 2)
            layout.hasParens = hasParens
            layout.addSubLayout(lArgLayout, "trueExpr", lParenWidth, 0)
            lArgWidth = icon.EMPTY_ARG_WIDTH if lArgLayout is None else lArgLayout.width
            layout.lArgWidth = lArgWidth
            depthWidth = self.depth() * DEPTH_EXPAND
            layout.depthWidth = depthWidth
            testArgSiteX = lParenWidth + lArgWidth - 1 + ifWidth - 1 + depthWidth // 2
            layout.addSubLayout(testArgLayout, "testExpr", testArgSiteX, 0)
            testArgWidth = icon.EMPTY_ARG_WIDTH if testArgLayout is None else \
                testArgLayout.width
            layout.testArgWidth = testArgWidth
            rArgSiteX = testArgSiteX + testArgWidth-1 + elseWidth-1 + depthWidth // 2
            layout.addSubLayout(rArgLayout, "falseExpr", rArgSiteX, 0)
            rArgWidth = icon.EMPTY_ARG_WIDTH if rArgLayout is None else rArgLayout.width
            layout.rArgWidth = rArgWidth
            layout.width = rArgSiteX + rArgWidth + rParenWidth
            layout.addSubLayout(attrLayout, 'attrIcon',
                    layout.width - icon.ATTR_SITE_DEPTH, icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def snapLists(self, forCursor=False):
        # Make attribute site unavailable unless the icon has parens to hold it
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if not self.hasParens:
            del siteSnapLists['attrIn']
        return siteSnapLists

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        hasParens = needsParens(self, forText=True)
        brkLvl = parentBreakLevel + 1
        # If this operation is part of an associative grouping, don't add to level
        if not hasParens:
            parent = self.parent()
            if parent is not None and parent.__class__ in (BinOpIcon, IfExpIcon):
                if parent.precedence == self.precedence:
                    brkLvl = parentBreakLevel
        if hasParens:
            contNeeded = False
        trueExprText = icon.argSaveText(brkLvl, self.sites.trueExpr, contNeeded, export)
        if hasParens:
            text = filefmt.SegmentedText('(')
            text.concat(brkLvl, trueExprText, contNeeded)
        else:
            text = trueExprText
        text.add(None, " if ", contNeeded)
        testExprText = icon.argSaveText(brkLvl, self.sites.testExpr, contNeeded, export)
        text.concat(brkLvl, testExprText, contNeeded)
        text.add(None, " else ", contNeeded)
        falseExprText = icon.argSaveText(brkLvl, self.sites.falseExpr, contNeeded, export)
        text.concat(brkLvl, falseExprText, contNeeded)
        if hasParens:
            text.add(None, ")")
        return text

    def dumpName(self):
        return "(if-expr)" if self.hasParens else "if-expr"

    def locIsOnLeftParen(self, btnPressLoc):
        iconLeft = self.rect[0]
        return iconLeft < btnPressLoc[0] < iconLeft + lParenImage.width

    def leftAssoc(self):
        return True

    def rightAssoc(self):
        return False

    def createAst(self):
        if self.sites.trueExpr.att is None:
            raise icon.IconExecException(self, "Missing if-true operand")
        if self.sites.testExpr.att is None:
            raise icon.IconExecException(self, "Missing test expression")
        if self.sites.falseExpr.att is None:
            raise icon.IconExecException(self, "Missing if-false operand")
        return ast.IfExp(test=self.sites.testExpr.att.createAst(),
            body=self.sites.trueExpr.att.createAst(),
            orelse=self.sites.falseExpr.att.createAst(), lineno=self.id, col_offset=0)

    def selectionRect(self):
        # Limit selection rectangle for extending selection to the if
        ifWidth, elseWidth, height = self.bodySize
        ifWidth += self.depthWidth // 2
        x, top = self.rect[:2]
        left = x + self.trueExprWidth
        return left, top, left + ifWidth, top + height

    def inRectSelect(self, rect):
        if not comn.rectsTouch(rect, self.rect):
            return False
        return comn.rectsTouch(rect, self.selectionRect())

    def textEntryHandler(self, entryIc, text, onAttr):
        # Typeover when on rightmost attribute site of test expression and user types 'e'
        siteId = self.siteOf(entryIc, recursive=True)
        if siteId != "testExpr" or not onAttr:
            return None
        rightmostIc, rightmostSite = icon.rightmostFromSite(self, 'testExpr')
        if rightmostIc is entryIc and text == "e":
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
        falseExprSite = self.sites.falseExpr
        xOffset = falseExprSite.xOffset + icon.OUTPUT_SITE_DEPTH - icon.TEXT_MARGIN - \
            icon.getTextSize("else"[self.typeoverIdx:], icon.boldFont)[0]
        return xOffset, falseExprSite.yOffset

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        retVal = 'testExpr', 'falseExpr', 'else', self.typeoverIdx
        return [retVal] if allRegions else retVal

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, overwriteStart=False):
        return self._placeArgsCommon(placeList, startSiteId, overwriteStart, False)

    def _placeArgsCommon(self, placeList, startSiteId, overwriteStart, doPlacement):
        # Inline-if has a left, a center, and a right argument, none of which can be a
        # series.  Given that placeArgs methods are currently only by the entry icon,
        # there are not yet any contexts in which operators like inline-if and binary
        # operators with an argument to the left of the icon body are asked to place
        # their left arguments, though this code is provided for completeness.
        if len(placeList) == 0:
            return None, None
        if startSiteId in (None, 'trueExpr'):
            placeSites = ('trueExpr', 'testExpr', 'falseExpr')
        elif startSiteId == 'testExpr':
            placeSites = ('testExpr', 'falseExpr')
        elif startSiteId == 'falseExpr':
            placeSites = ('falseExpr', )
        elif startSiteId == 'attrIcon':
            if placeList[0] is not None and self.hasParens and \
                    'attrOut' in placeList[0].parentSites():
                if doPlacement:
                    self.replaceChild(placeList[0], 'attrIcon')
                return 0, None
            return None, None
        for i in range(len(placeSites)):
            if i >= len(placeList):
                break
            if isinstance(placeList[i], (tuple, list)):
                # If all of the requested arguments are not individual values, we know
                # we're not reconstituting a dissolved if, so there's no reason to
                # respect the original packing, and we can just use the base-class method
                # which will deal with series.
                if doPlacement:
                    return icon.Icon.placeArgs(self, placeList, startSiteId)
                else:
                    return icon.Icon.canPlaceArgs(self, placeList, startSiteId)
        # At this point, we know that the placement list contains only individual icons
        # (and/or Nones for empty sites).  Pair place list entries with sites, and test
        # for compatible site types and already-occupied sites, and place if requested
        nPlaced = min(len(placeList), len(placeSites))
        for i in range(nPlaced):
            placedIc = placeList[i]
            if placedIc is not None:
                if not placedIc.hasSite('output') or \
                        not (overwriteStart and i == 0) and \
                        self.childAt(placeSites[i]) is not None:
                    return None if i == 0 else i-1, None
            if doPlacement:
                self.replaceChild(placedIc, placeSites[i])
        return nPlaced-1, None

    def backspace(self, siteId, evt):
        win = self.window
        if siteId == 'attrIcon':
            # Cursor is on attribute site of right paren.  Convert to open
            # (unclosed) cursor paren
            win.requestRedraw(self.topLevelParent().hierRect())
            attrIcon = self.childAt('attrIcon')
            entryIcon = None
            if attrIcon is not None:
                # If an attribute is attached to the parens, try to attach it to the
                # else clause.  If that's not possible, create an entry icon
                self.replaceChild(None, 'attrIcon')
                elseChild = self.childAt('falseExpr')
                if elseChild is None:
                    attrDestIcon, attrDestSite = self, 'falseExpr'
                else:
                    attrDestIcon, attrDestSite  = icon.rightmostSite(elseChild)
                if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                        'cursorOnly'):
                    # Can't place attribute icon from paren, create an entry icon
                    entryIcon = entryicon.EntryIcon(window=win)
                    attrDestIcon.replaceChild(entryIcon, 'attrIcon')
                    entryIcon.appendPendingArgs([attrIcon])
                else:
                    attrDestIcon.replaceChild(attrIcon, attrDestSite)
                cursIc, cursSite = attrDestIcon, attrDestSite
            else:
                cursIc, cursSite = icon.rightmostSite(icon.findLastAttrIcon(self))
            cursorParen = parenicon.CursorParenIcon(window=win)
            self.insertParent(cursorParen, 'argIcon')
            # Manually change status of icon to no-parens so it will be treated
            # as not parenthesised as icons are rearranged
            self.hasParens = False
            # Expand the scope of the paren to its max, by rearranging the icon
            # hierarchy around it
            reorderexpr.reorderArithExpr(cursorParen)
            if entryIcon:
                win.cursor.setToText(entryIcon)
            else:
                win.cursor.setToIconSite(cursIc, cursSite)
            return
        if siteId == 'trueExpr' and self.hasParens:
            # Cursor is on left paren: User wants to remove parens
            win.requestRedraw(self.topLevelParent().hierRect())
            attrIcon = self.childAt('attrIcon')
            if attrIcon:
                # If an attribute is attached to the right paren, try to attach it to the
                # else clause.  If that's not possible, create a placeholder entry icon
                self.replaceChild(None, 'attrIcon')
                elseChild = self.childAt('falseExpr')
                if elseChild is None:
                    attrDestIcon, attrDestSite = self, 'falseExpr'
                else:
                    attrDestIcon, attrDestSite  = icon.rightmostSite(elseChild)
                if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                        'cursorOnly'):
                    # Can't place attribute from paren, create placeholder entry icon
                    entryIcon = entryicon.EntryIcon(window=win)
                    attrDestIcon.replaceChild(entryIcon, 'attrIcon')
                    entryIcon.appendPendingArgs([attrIcon])
                else:
                    attrDestIcon.replaceChild(attrIcon, attrDestSite)
            # Finding the correct position for the cursor after reorderArithExpr is
            # surprisingly difficult.  It is done by temporarily setting the cursor
            # to the output site of the icon at the lowest coincident site and then
            # restoring it to the parent site after reordering.  If the site is empty,
            # use the further hack of creating a temporary icon to track the empty
            # site.  The reason for setting the cursor position as opposed to just
            # recording the lowest icon, is that reorderArithExpr can remove parens,
            # but will relocate the cursor if it does.
            cursorIc, cursorSite = iconsites.lowestCoincidentSite(self, siteId)
            cursorChild = cursorIc.childAt(cursorSite)
            if cursorChild is None:
                cursorChild = UnaryOpIcon('***Internal Temporary***', window=win)
                cursorIc.replaceChild(cursorChild, cursorSite)
                removeTempCursorIcon = True
            else:
                removeTempCursorIcon = False
            win.cursor.setToIconSite(cursorChild, 'output')
            # To remove the parens we run reorderArithExpr, hiding the parens from it
            # by setting the icon's hasParens flag to false (which is what it uses to
            # determine if parens are displayed).
            self.hasParens = False
            self.markLayoutDirty()
            reorderexpr.reorderArithExpr(self)
            # Restore the cursor that was temporarily set to the output site to the
            # parent icon and site (see above)
            updatedCursorIc = win.cursor.icon.parent()
            updatedCursorSite = updatedCursorIc.siteOf(win.cursor.icon)
            if removeTempCursorIcon:
                updatedCursorIc.replaceChild(None, updatedCursorSite)
            win.cursor.setToIconSite(updatedCursorIc, updatedCursorSite)
            return
        if siteId == 'falseExpr':
            # Cursor was on else, just move the cursor to the test
            win.requestRedraw(self.topLevelParent().hierRect())
            if self.sites.testExpr.att is None:
                updatedCursorIc = self
                updatedCursorSite = 'testExpr'
            else:
                updatedCursorIc, updatedCursorSite = icon.rightmostSite(
                    icon.findLastAttrIcon(self.sites.testExpr.att), ignoreAutoParens=True)
            win.cursor.setToIconSite(updatedCursorIc, updatedCursorSite)
            return
        # Cursor was on the if itself.  Create an entry icon loaded with text "if" and
        # pending args for testExpr and falseExpr icons (the goal being that placeArgs
        # can faithfully reconstitute the if regardless of empty sites).  Attach the
        # entry icon to the rightmost site of the trueExpr if it exists, or to the parent
        # if it does not.
        win.requestRedraw(self.topLevelParent().hierRect(), filterRedundantParens=True)
        if self.hasParens:
            # If the operation had parens, place temporary parens for continuity
            attrIcon = self.childAt('attrIcon')
            cursorParen = parenicon.CursorParenIcon(window=win, closed=True)
            self.insertParent(cursorParen, 'argIcon')
            if attrIcon is not None:
                cursorParen.replaceChild(attrIcon, 'attrIcon')
        parent = self.parent()
        leftArg = self.leftArg()
        rightArg = self.rightArg()
        if parent is None and leftArg is None:
            entryAttachedIcon, entryAttachedSite = None, None
        elif parent is not None and leftArg is None:
            entryAttachedIcon = parent
            entryAttachedSite = parent.siteOf(self)
        else:  # leftArg is not None, attach to that
            entryAttachedIcon, entryAttachedSite = icon.rightmostSite(
                icon.findLastAttrIcon(leftArg))
        entryIcon = entryicon.EntryIcon(initialString="if", window=win)
        testExpr = self.childAt('testExpr')
        if testExpr is not None:
            self.replaceChild(None, 'testExpr')
            entryIcon.appendPendingArgs([testExpr])
        if leftArg is not None:
            leftArg.replaceChild(None, 'output')
        if rightArg is not None:
            rightArg.replaceChild(None, 'output')
            if testExpr is None:
                entryIcon.appendPendingArgs([None, rightArg])
            else:
                entryIcon.appendPendingArgs([rightArg])
        if parent is None:
            if leftArg is None:
                win.replaceTop(self, entryIcon)
            else:
                win.replaceTop(self, leftArg)
                entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
        else:
            parentSite = parent.siteOf(self)
            if leftArg is not None:
                parent.replaceChild(leftArg, parentSite)
            entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
        self.replaceChild(None, 'trueExpr')
        self.replaceChild(None, 'testExpr')
        self.replaceChild(None, 'falseExpr')
        win.cursor.setToText(entryIcon, drawNew=False)

    def updateParens(self):
        needs = needsParens(self)
        if needs and not self.hasParens:
            self.hasParens = True
            self.sites.attrIcon.order = 2
        elif self.hasParens and not needs:
            self.hasParens = False
            self.sites.attrIcon.order = None

def needsParens(ic, parent=None, forText=False, parentSite=None):
    """Returns True if the BinOpIcon or IfExpr icon, ic, should have parenthesis.
    Specify "parent" to compute for a parent which is not the actual icon parent.  If
    forText is True, ic can also be a DivideIcon, and the calculation is appropriate to
    text rather than icons, where division is just another binary operator and not laid
    out numerator / denominator."""
    if ic.childAt('attrIcon'):
        return True  # BinOps can have attributes, and need parens to support the site
    if parent is None:
        parent = ic.parent()
    if parent is None:
        return False
    # Unclosed cursor-parens count as a left-paren, but not a right-paren
    if parent.__class__.__name__ == "CursorParenIcon" and not parent.closed:
        parenParent = parent.parent()
        if parenParent is None or parenParent.__class__ not in (BinOpIcon, IfExpIcon) or \
                parenParent.siteOf(parent) != leftSiteOf(parenParent):
            return False
        parent = parenParent
    arithmeticOpClasses = (BinOpIcon, UnaryOpIcon, IfExpIcon)
    if forText:
        arithmeticOpClasses += (DivideIcon,)
    if parent.__class__ not in arithmeticOpClasses:
        return False
    if ic.precedence > parent.precedence:
        return False
    if ic.precedence < parent.precedence:
        return True
    # Precedence is equal to parent.  Look at associativity
    if parentSite is None:
        parentSite = parent.siteOf(ic, recursive=True)
    if parentSite == leftSiteOf(parent) and ic.rightAssoc():
        return True
    if parentSite == rightSiteOf(parent) and ic.leftAssoc():
        return True
    return False

def recalculateParens(topNode):
    """While layout is where the hasParens field is normally filled in, There are special
    cases (typeover), where it is needed before layout.  This call will update both the
    state of hasParens, and restore attribute sites on icons whose parens are optional"""
    for ic in topNode.traverse(includeSelf=True):
        if hasattr(ic, 'hasParens'):
            ic.updateParens()

def leftSiteOf(ic):
    return 'trueExpr' if ic.__class__ == IfExpIcon else 'leftArg'

def rightSiteOf(ic):
    return 'falseExpr' if ic.__class__ == IfExpIcon else 'rightArg'

# The ugly hack of not putting these at the top of the file allows the backspace code
# to be in the same module as the icon definitions, and but not mess up initialization
import parenicon
import entryicon
import reorderexpr

def backspaceBinOpIcon(ic, site, evt):
    win = ic.window
    if site == 'attrIcon':
        if isinstance(ic, DivideIcon):
            # On a divide icon, just move cursor to denominator
            bottomArg = ic.sites.bottomArg.att
            if bottomArg is None:
                cursorIc = ic
                cursorSite = 'bottomArg'
            else:
                cursorIc, cursorSite = icon.rightmostSite(
                    icon.findLastAttrIcon(bottomArg))
            win.cursor.setToIconSite(cursorIc, cursorSite)
        else:
            # Cursor is on attribute site of right paren.  Convert to open
            # (unclosed) cursor paren
            win.requestRedraw(ic.topLevelParent().hierRect())
            attrIcon = ic.childAt('attrIcon')
            entryIcon = None
            if attrIcon:
                # If an attribute is attached to the parens, try to attach it to the
                # right argument.  If that's not possible, create an entry icon
                ic.replaceChild(None, 'attrIcon')
                rightChild = ic.childAt('rightArg')
                if rightChild is None:
                    attrDestIcon, attrDestSite = ic, 'rightArg'
                else:
                    attrDestIcon, attrDestSite  = icon.rightmostSite(rightChild)
                if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                        'cursorOnly'):
                    # Can't place attribute icon from paren, create an entry icon
                    entryIcon = entryicon.EntryIcon(window=win)
                    attrDestIcon.replaceChild(entryIcon, 'attrIcon')
                    entryIcon.appendPendingArgs([attrIcon])
                else:
                    attrDestIcon.replaceChild(attrIcon, attrDestSite)
                cursIc, cursSite = attrDestIcon, attrDestSite
            else:
                cursIc, cursSite = icon.rightmostSite(icon.findLastAttrIcon(ic))
            cursorParen = parenicon.CursorParenIcon(window=win)
            ic.insertParent(cursorParen, 'argIcon')
            # Manually change status of icon to no-parens so it will be treated
            # as not parenthesised as icons are rearranged
            ic.hasParens = False
            # Expand the scope of the paren to its max, by rearranging the icon
            # hierarchy around it
            reorderexpr.reorderArithExpr(cursorParen)
            if entryIcon is not None:
                win.cursor.setToText(entryIcon)
            else:
                win.cursor.setToIconSite(cursIc, cursSite)
        return
    if site == leftSiteOf(ic):
        if not ic.hasParens:
            # We shouldn't be called in this case, because we have no content to the
            # left of the left input, but this can happen on the top level
            return
        # Cursor is on left paren: User wants to remove parens
        win.requestRedraw(ic.topLevelParent().hierRect())
        attrIcon = ic.childAt('attrIcon')
        if attrIcon:
            # If an attribute is attached to the right paren, try to attach it to the
            # right argument.  If that's not possible, create a placeholder entry icon
            ic.replaceChild(None, 'attrIcon')
            rightChild = ic.childAt('rightExpr')
            if rightChild is None:
                attrDestIcon, attrDestSite = ic, 'rightExpr'
            else:
                attrDestIcon, attrDestSite = icon.rightmostSite(rightChild)
            if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                    'cursorOnly'):
                # Can't place attribute from paren, create placeholder entry icon
                entryIcon = entryicon.EntryIcon(window=win)
                attrDestIcon.replaceChild(entryIcon, 'attrIcon')
                entryIcon.appendPendingArgs([attrIcon])
            else:
                attrDestIcon.replaceChild(attrIcon, attrDestSite)
        # Finding the correct position for the cursor after reorderArithExpr is
        # surprisingly difficult.  It is done by temporarily setting the cursor
        # to the output site of the icon at the lowest coincident site and then
        # restoring it to the parent site after reordering.  If the site is empty,
        # use the further hack of creating a temporary icon to track the empty
        # site.  The reason for setting the cursor position as opposed to just
        # recording the lowest icon, is that reorderArithExpr can remove parens,
        # but will relocate the cursor if it does.
        cursorIc, cursorSite = iconsites.lowestCoincidentSite(ic, site)
        cursorChild = cursorIc.childAt(cursorSite)
        if cursorChild is None:
            cursorChild = UnaryOpIcon('***Internal Temporary***', window=win)
            cursorIc.replaceChild(cursorChild, cursorSite)
            removeTempCursorIcon = True
        else:
            removeTempCursorIcon = False
        win.cursor.setToIconSite(cursorChild, 'output')
        # To remove the parens we run reorderArithExpr, hiding the parens from it
        # by setting the icon's hasParens flag to false (which is what it uses to
        # determine if parens are displayed).
        ic.hasParens = False
        ic.markLayoutDirty()
        reorderexpr.reorderArithExpr(ic)
        # Restore the cursor that was temporarily set to the output site to the
        # parent icon and site (see above)
        updatedCursorIc = win.cursor.icon.parent()
        updatedCursorSite = updatedCursorIc.siteOf(win.cursor.icon)
        if removeTempCursorIcon:
            updatedCursorIc.replaceChild(None, updatedCursorSite)
        win.cursor.setToIconSite(updatedCursorIc, updatedCursorSite)
        return
    # Cursor was on the operator itself
    entryIcon = _becomeEntryIcon(ic)
    win.cursor.setToText(entryIcon, drawNew=False)

def _becomeEntryIcon(ic):
    win = ic.window
    win.requestRedraw(ic.topLevelParent().hierRect(), filterRedundantParens=True)
    if not isinstance(ic, DivideIcon) and ic.hasParens:
        # If the operation had parens, place temporary parens for continuity
        attrIcon = ic.childAt('attrIcon')
        cursorParen = parenicon.CursorParenIcon(window=win, closed=True)
        ic.insertParent(cursorParen, 'argIcon')
        if attrIcon is not None:
            cursorParen.replaceChild(attrIcon, 'attrIcon')
    parent = ic.parent()
    if isinstance(ic, DivideIcon):
        leftArg = ic.sites.topArg.att
        rightArg = ic.sites.bottomArg.att
        op = '//' if ic.floorDiv else '/'
    else:
        leftArg = ic.leftArg()
        rightArg = ic.rightArg()
        op = ic.operator
    if parent is None and leftArg is None:
        entryAttachedIcon, entryAttachedSite = None, None
    elif parent is not None and leftArg is None:
        entryAttachedIcon = parent
        entryAttachedSite = parent.siteOf(ic)
    else:  # leftArg is not None, attach to that
        #... This had ignoreAutoParens=True in earlier versions, with the comment:
        #    "Ignore auto parens because we are removing the supporting operator",
        #    however we are not removing the operator of the left arg, and this resulted
        #    in weird behavior in the following case: a*(b+c)*d (backspace second *)
        entryAttachedIcon, entryAttachedSite = icon.rightmostSite(
            icon.findLastAttrIcon(leftArg))
    entryIcon = entryicon.EntryIcon(initialString=op, window=win)
    if leftArg is not None:
        leftArg.replaceChild(None, 'output')
    if rightArg is not None:
        rightArg.replaceChild(None, 'output')
        entryIcon.appendPendingArgs([rightArg])
    if parent is None:
        if leftArg is None:
            win.replaceTop(ic, entryIcon)
        else:
            win.replaceTop(ic, leftArg)
            entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
    else:
        parentSite = parent.siteOf(ic)
        if leftArg is not None:
            parent.replaceChild(leftArg, parentSite)
        entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
    if isinstance(ic, DivideIcon):
        ic.replaceChild(None, 'topArg')
        ic.replaceChild(None, 'bottomArg')
    else:
        ic.replaceChild(None, 'leftArg')
        ic.replaceChild(None, 'rightArg')
    return entryIcon

import nameicons
def createUnaryOpIconFromAst(astNode, window):
    if astNode.op.__class__ == ast.USub and \
            astNode.operand.__class__ == ast.Constant and \
            isinstance(astNode.operand.value, (numbers.Real, numbers.Rational,
            numbers.Integral)) and not isinstance(astNode.operand.value, bool):
        if hasattr(astNode.operand, 'annNumberSrcStr'):
            # We have a source string available.  Use it if it matches the value
            # stored in the ast
            if astNode.operand.value == ast.literal_eval(astNode.operand.annNumberSrcStr):
                return nameicons.NumericIcon('-' + astNode.operand.annNumberSrcStr,
                    window)
        return nameicons.NumericIcon(-astNode.operand.value, window)
    if astNode.__class__ == ast.UnaryOp and astNode.op.__class__ == ast.USub and \
            astNode.operand == ast.Num:
        return nameicons.NumericIcon(-astNode.operand.n, window)
    topIcon = UnaryOpIcon(unaryOps[astNode.op.__class__], window)
    topIcon.replaceChild(icon.createFromAst(astNode.operand, window), "argIcon")
    return topIcon
icon.registerIconCreateFn(ast.UnaryOp, createUnaryOpIconFromAst)

def createBinOpIconFromAst(astNode, window):
    if astNode.op.__class__ in (ast.Div, ast.FloorDiv):
        topIcon = DivideIcon(astNode.op.__class__ is ast.FloorDiv, window)
        topIcon.replaceChild(icon.createFromAst(astNode.left, window), "topArg")
        topIcon.replaceChild(icon.createFromAst(astNode.right, window), "bottomArg")
        return topIcon
    topIcon = BinOpIcon(binOps[astNode.op.__class__], window)
    topIcon.replaceChild(icon.createFromAst(astNode.left, window), "leftArg")
    topIcon.replaceChild(icon.createFromAst(astNode.right, window), "rightArg")
    return topIcon
icon.registerIconCreateFn(ast.BinOp, createBinOpIconFromAst)

def createBoolOpIconFromAst(astNode, window):
    topIcon = BinOpIcon(boolOps[astNode.op.__class__], window)
    topIcon.replaceChild(icon.createFromAst(astNode.values[0], window), "leftArg")
    topIcon.replaceChild(icon.createFromAst(astNode.values[1], window), "rightArg")
    for value in astNode.values[2:]:
        newTopIcon = BinOpIcon(boolOps[astNode.op.__class__], window)
        newTopIcon.replaceChild(topIcon, "leftArg")
        newTopIcon.replaceChild(icon.createFromAst(value, window), "rightArg")
        topIcon = newTopIcon
    return topIcon
icon.registerIconCreateFn(ast.BoolOp, createBoolOpIconFromAst)

def createCompareIconFromAst(astNode, window):
    compareIcons = [BinOpIcon(compareOps[op.__class__], window) for op in astNode.ops]
    topIcon = None
    for ic, compAst in zip(compareIcons, astNode.comparators):
        if topIcon is None:
            ic.replaceChild(icon.createFromAst(astNode.left, window), 'leftArg')
        else:
            ic.replaceChild(topIcon, 'leftArg')
        ic.replaceChild(icon.createFromAst(compAst, window), 'rightArg')
        topIcon = ic
    return topIcon
icon.registerIconCreateFn(ast.Compare, createCompareIconFromAst)

def createIfExpIconFromAst(astNode, window):
    topIcon = IfExpIcon(window)
    topIcon.replaceChild(icon.createFromAst(astNode.test, window), "testExpr")
    topIcon.replaceChild(icon.createFromAst(astNode.body, window), "trueExpr")
    topIcon.replaceChild(icon.createFromAst(astNode.orelse, window), "falseExpr")
    return topIcon
icon.registerIconCreateFn(ast.IfExp, createIfExpIconFromAst)
