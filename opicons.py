# Copyright Mark Edel  All rights reserved
import iconsites
import icon
import operator
import ast
from PIL import Image, ImageDraw
import comn
import iconlayout
import typing

DEPTH_EXPAND = 4

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

class UnaryOpIcon(icon.Icon):
    def __init__(self, op, window, location=None):
        icon.Icon.__init__(self, window)
        self.operator = op
        self.precedence = unaryOpPrecedence[op]
        bodyWidth, bodyHeight = icon.getTextSize(self.operator)
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
            width, height = icon.getTextSize(self.operator)
            bodyLeft = icon.outSiteImage.width - 1
            bodyWidth = width + 2 * icon.TEXT_MARGIN
            bodyHeight = height + 2 * icon.TEXT_MARGIN
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth, bodyHeight),
             fill=comn.ICON_BG_COLOR, outline=comn.OUTLINE_COLOR)
            if needOutSite:
                outImageY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (0, outImageY), mask=icon.outSiteImage)
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
            draw.text((textLeft, textTop), self.operator, font=icon.globalFont,
             fill=(0, 0, 0, 255))
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
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        addSpace = " " if self.operator[-1].isalpha() else ""
        return self.operator + addSpace + icon.argTextRepr(self.sites.argIcon)

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

class BinOpIcon(icon.Icon):
    def __init__(self, op, window, location=None):
        icon.Icon.__init__(self, window)
        self.operator = op
        self.precedence = binOpPrecedence[op]
        self.hasParens = False  # Filled in by layout methods
        self.leftArgWidth = icon.EMPTY_ARG_WIDTH
        self.rightArgWidth = icon.EMPTY_ARG_WIDTH
        opWidth, opHeight = icon.getTextSize(self.operator)
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
            txtImg = icon.iconBoxedText(self.operator)
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
            return ast.Compare(left=self.leftArg().createAst(),
             ops=[compareAsts[self.operator]()],
             comparators=[self.rightArg().createAst()], lineno=self.id, col_offset=0)
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

def needsParens(ic, parent=None, forText=False, parentSite=None):
    """Returns True if the BinOpIcon, ic, should have parenthesis.  Specify "parent" to
    compute for a parent which is not the actual icon parent.  If forText is True, ic
    can also be a DivideIcon, and the calculation is appropriate to text rather than
    icons, where division is just another binary operator and not laid out numerator /
    denominator."""
    if ic.childAt('attrIcon'):
        return True  # BinOps can have attributes, and need parens to support the site
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
    if parentSite is None:
        parentSite = parent.siteOf(ic, recursive=True)
    if parentSite == "leftArg" and ic.rightAssoc():
        return True
    if parentSite == "rightArg" and ic.leftAssoc():
        return True
    return False

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
                cursorIc, cursorSite = typing.rightmostSite(
                    icon.findLastAttrIcon(bottomArg))
            win.cursor.setToIconSite(cursorIc, cursorSite)
        else:
            # Cursor is on attribute site of right paren.  Convert to open
            # (unclosed) cursor paren
            redrawRegion = comn.AccumRects(ic.topLevelParent().hierRect())
            attrIcon = ic.childAt('attrIcon')
            if attrIcon:
                # If an attribute is attached to the parens, just select
                win.unselectAll()
                for i in attrIcon.traverse():
                    win.select(i)
                win.refresh(redrawRegion.get())
                return
            parent = ic.parent()
            cursorParen = typing.CursorParenIcon(window=win)
            if parent is None:
                # Insert cursor paren at top level with ic as its child
                cursorParen.replaceChild(ic, 'argIcon')
                win.replaceTop(ic, cursorParen)
            else:
                # Insert cursor paren between parent and ic
                parentSite = parent.siteOf(ic)
                cursorParen.replaceChild(ic, 'argIcon')
                parent.replaceChild(cursorParen, parentSite)
            # Manually change status of icon to no-parens so it will be treated
            # as not parenthesised as icons are rearranged
            ic.hasParens = False
            cursIc, cursSite = typing.rightmostSite(icon.findLastAttrIcon(ic))
            # Expand the scope of the paren to its max, by rearranging the icon
            # hierarchy around it
            typing.reorderArithExpr(cursorParen)
            redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
            win.refresh(redrawRegion.get())
            win.cursor.setToIconSite(cursIc, cursSite)
        return
    if site == 'leftArg' and ic.hasParens:
        # Cursor is on left paren: User wants to remove parens
        redrawRegion = comn.AccumRects(ic.topLevelParent().hierRect())
        attrIcon = ic.childAt('attrIcon')
        if attrIcon:
            # If an attribute is attached to the parens, don't delete, just select
            win.unselectAll()
            for i in attrIcon.traverse():
                win.select(i)
            win.refresh(redrawRegion.get())
            return
        # Finding the correct position for the cursor after reorderArithExpr is
        # surprisingly difficult.  It is done by temporarily setting the cursor
        # to the output site of the icon at the lowest coincident site and then
        # restoring it to the parent site after reordering.  If the site is empty,
        # use the further hack of creating a temporary icon to track the empty
        # site.  The reason for setting the cursor position as opposed to just
        # recording the lowest icon, is that reorderArithExpr can remove parens,
        # but will relocate the cursor it does.
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
        typing.reorderArithExpr(ic)
        # Restore the cursor that was temporarily set to the output site to the
        # parent icon and site (see above)
        updatedCursorIc = win.cursor.icon.parent()
        updatedCursorSite = updatedCursorIc.siteOf(win.cursor.icon)
        if removeTempCursorIcon:
            updatedCursorIc.replaceChild(None, updatedCursorSite)
        win.cursor.setToIconSite(updatedCursorIc, updatedCursorSite)
        redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
        win.refresh(redrawRegion.get())
        return
    # Cursor was on the operator itself
    redrawRect = ic.topLevelParent().hierRect()
    if not isinstance(ic, DivideIcon) and ic.hasParens:
        # If the operation had parens, place temporary parens for continuity
        cursorParen = typing.CursorParenIcon(window=win, closed=True)
        cpParent = ic.parent()
        if cpParent is None:
            win.replaceTop(ic, cursorParen)
        else:
            cpParent.replaceChild(cursorParen, cpParent.siteOf(ic))
            cursorParen.replaceChild(ic, 'argIcon')
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
        # Ignore auto parens because we are removing the supporting operator
        entryAttachedIcon, entryAttachedSite = typing.rightmostSite(
            icon.findLastAttrIcon(leftArg), ignoreAutoParens=True)
    win.entryIcon = typing.EntryIcon(entryAttachedIcon, entryAttachedSite,
        initialString=op, window=win)
    if leftArg is not None:
        leftArg.replaceChild(None, 'output')
    if rightArg is not None:
        rightArg.replaceChild(None, 'output')
        win.entryIcon.setPendingArg(rightArg)
    if parent is None:
        if leftArg is None:
            win.replaceTop(ic, win.entryIcon)
        else:
            win.replaceTop(ic, leftArg)
            entryAttachedIcon.replaceChild(win.entryIcon, entryAttachedSite)
    else:
        parentSite = parent.siteOf(ic)
        if leftArg is not None:
            parent.replaceChild(leftArg, parentSite)
        entryAttachedIcon.replaceChild(win.entryIcon, entryAttachedSite)
    if isinstance(ic, DivideIcon):
        ic.replaceChild(None, 'topArg')
        ic.replaceChild(None, 'bottomArg')
    else:
        ic.replaceChild(None, 'leftArg')
        ic.replaceChild(None, 'rightArg')
    win.cursor.setToEntryIcon()
    win.redisplayChangedEntryIcon(evt, redrawRect)
