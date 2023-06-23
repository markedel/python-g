# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw
import comn
import iconlayout
import entryicon
import filefmt
import listicons
import icon
import reorderexpr

class CursorParenIcon(icon.Icon):
    def __init__(self, closed=False, window=None, typeover=False, location=None):
        # Note that while the constructor can accept a typeover indicator, the icon does
        # not currently support typeover, because there are no cases (yet) where initial
        # entry via typing is in closed state.
        icon.Icon.__init__(self, window)
        self.closed = False
        bodyWidth, bodyHeight = icon.globalFont.getsize("(")
        bodyWidth += 2 * icon.TEXT_MARGIN + 1
        bodyHeight += 2 * icon.TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + icon.outSiteImage.width, y + bodyHeight)
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('argIcon', 'input', bodyWidth - 1, self.sites.output.yOffset)
        seqX = icon.OUTPUT_SITE_DEPTH - icon.SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if closed:
            self.close()

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            img = Image.new('RGBA', (bodyWidth + icon.outSiteImage.width, bodyHeight),
             color=(0, 0, 0, 0))
            textWidth, textHeight = icon.globalFont.getsize("(")
            bodyLeft = icon.outSiteImage.width - 1
            draw = ImageDraw.Draw(img)
            height = textHeight + 2 * icon.TEXT_MARGIN
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth-1, bodyHeight-1),
             fill=comn.ICON_BG_COLOR, outline=comn.OUTLINE_COLOR)
            if needSeqSites:
                icon.drawSeqSites(img, bodyLeft, 0, bodyHeight)
            outSiteX = self.sites.output.xOffset
            outSiteY = self.sites.output.yOffset
            outImgY = outSiteY - icon.outSiteImage.height // 2
            if needOutSite:
                img.paste(icon.outSiteImage, (outSiteX, outImgY), mask=icon.outSiteImage)
            inSiteX = self.sites.argIcon.xOffset
            inImageY = self.sites.argIcon.yOffset - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inSiteX, inImageY))
            textLeft = bodyLeft + icon.TEXT_MARGIN
            draw.text((textLeft, icon.TEXT_MARGIN), "(",
             font=icon.globalFont, fill=(120, 120, 120, 255))
            self.drawList = [((0, 0), img)]
            if self.closed:
                closeImg = Image.new('RGBA', (bodyWidth, bodyHeight))
                draw = ImageDraw.Draw(closeImg)
                draw.rectangle((0, 0, bodyWidth-1, bodyHeight-1), fill=comn.ICON_BG_COLOR,
                 outline=comn.OUTLINE_COLOR)
                textLeft = icon.TEXT_MARGIN
                draw.text((textLeft, icon.TEXT_MARGIN), ")",
                    font=icon.globalFont, fill=(120, 120, 120, 255))
                attrX = bodyWidth - 1 - icon.ATTR_SITE_DEPTH
                attrY = self.sites.attrIcon.yOffset
                closeImg.paste(icon.attrInImage, (attrX, attrY))
                endParenLeft = comn.rectWidth(self.rect) - bodyWidth
                self.drawList.append(((endParenLeft, 0), closeImg))
            else:
                draw.line((bodyLeft, outSiteY, inSiteX, outSiteY),
                 fill=comn.ICON_BG_COLOR, width=3)
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip)

    def doLayout(self, outSiteX, outSiteY, layout):
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        bodyWidth, height = self.bodySize
        if self.closed:
            width = self.sites.attrIcon.xOffset + icon.ATTR_SITE_DEPTH + 1
        else:
            width = bodyWidth + icon.outSiteImage.width - 1
        top = outSiteY - self.sites.output.yOffset
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        singleParenWidth, height = self.bodySize
        argIcon = self.sites.argIcon.att
        argLayouts = [None] if argIcon is None else argIcon.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        else:
            attrLayouts = [None]
        layouts = []
        for argLayout, attrLayout in iconlayout.allCombinations(
                (argLayouts, attrLayouts)):
            width = singleParenWidth
            layout = iconlayout.Layout(self, width, height, height//2)
            layout.addSubLayout(argLayout, 'argIcon', singleParenWidth - 1, 0)
            width += icon.EMPTY_ARG_WIDTH if argLayout is None else argLayout.width - 1
            if self.closed:
                width += singleParenWidth - 1
                layout.width = width
                layout.addSubLayout(attrLayout, 'attrIcon', width - icon.ATTR_SITE_DEPTH,
                        icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        if self.closed:
            text = filefmt.SegmentedText("(")
        else:
            text = filefmt.SegmentedText('$:u$(')
        icon.addArgSaveText(text, brkLvl, self.sites.argIcon, contNeeded, export)
        text.add(None, ")")
        return icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)

    def textRepr(self):
        if self.sites.argIcon.att is None:
            return "None"
        return self.sites.argIcon.att.textRepr()

    def dumpName(self):
        return "(cp)" if self.closed else "(cp"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def execute(self):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary paren")
        if self.sites.argIcon.att is None:
            raise icon.IconExecException(self, "Missing argument")
        result = self.sites.argIcon.att.execute()
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def close(self, typeover=False):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Allow cursor to be set to the end paren before layout knows where it goes
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

    def textEntryHandler(self, entryIc, text, onAttr):
        # User can start typing a generator comprehension before conversion to tuple.
        # All we need to do is recognize it.  Entry icon method insertCprh will do the
        # work of conversion.  Note that the only comprehension supported is "for",
        # because "if" cannot be the first comprehension and therefore can only come
        # after tuple conversion.
        listSiteId = self.siteOf(entryIc, recursive=True)
        if listSiteId != 'argIcon':
            return None
        textStripped = text[:-1]
        delim = text[-1]
        if onAttr and text[0] in ('f', 'a'):
            if text in ('fo'[:len(text)], 'async fo'[:len(text)]):
                return 'accept'
            if text[:3] != 'for' and  text[:9] != 'async for':
                return None
            # Make sure entryIc is on the rightmost attribute site (either arg or an
            # existing comprehension), where it's safe to start a new comprehension
            entryRightmostIcon, entryRightmostSite = icon.rightmostSite(entryIc)
            listRightmostIcon, listRightmostSite = icon.rightmostFromSite(self, listSiteId)
            if entryRightmostIcon is not listRightmostIcon or entryRightmostSite != \
                    listRightmostSite:
                return None
            if text == 'for':
                return listicons.CprhForIcon(window=self.window, typeover=True), None
            if text == 'async for':
                return listicons.CprhForIcon(window=self.window, typeover=True,
                    isAsync=True), None
            forDelimiters = {*entryicon.emptyDelimiters, '(', '[', ','}
            if textStripped == 'for' and delim in forDelimiters:
                return listicons.CprhForIcon(window=self.window, typeover=True), delim
            if textStripped == 'async for' and delim in forDelimiters:
                return listicons.CprhForIcon(window=self.window, typeover=True,
                    isAsync=True), delim
            return None
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        # Color just the paren if the list is not closed, not the content
        if self.closed:
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight("Unmatched open paren")
        for ic in self.children():
            ic.highlightErrors(None)
        return

    def backspace(self, siteId, evt):
        win = self.window
        win.requestRedraw(self.topLevelParent().hierRect())
        if siteId == 'attrIcon':
            # Cursor is on attribute site of right paren.  Re-open the paren
            # On backspace from the outside right paren, reopen the list
            entryicon.reopenParen(self)
            return
        else:
            # Cursor is on the argument site: remove the parens unless an attribute is
            # attached to the parens, in which case, add a placeholder entry icon.
            attrIcon = self.childAt('attrIcon')
            if attrIcon:
                # If an attribute is attached to the right paren
                self.replaceChild(None, 'attrIcon')
                argChild = self.childAt('argIcon')
                if argChild is None:
                    attrDestIcon, attrDestSite = self, 'argIcon'
                else:
                    attrDestIcon, attrDestSite = icon.rightmostSite(argChild)
                if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                        'cursorOnly'):
                    # Can't place attribute from paren, create placeholder entry icon
                    entryIcon = entryicon.EntryIcon(window=win)
                    attrDestIcon.replaceChild(entryIcon, 'attrIcon')
                    entryIcon.appendPendingArgs([attrIcon])
                else:
                    attrDestIcon.replaceChild(attrIcon, attrDestSite)
            parent = self.parent()
            content = self.childAt('argIcon')
            if parent is None:
                if content is None:
                    # Open paren was the only thing left of the statement.  Remove
                    if self.prevInSeq() is not None:
                        cursorIc = self.prevInSeq()
                        cursorSite = 'seqOut'
                    elif self.nextInSeq() is not None:
                        cursorIc = self.nextInSeq()
                        cursorSite = 'seqIn'
                    else:
                        cursorIc = None
                        pos = self.pos()
                    win.removeIcons([self])
                    if cursorIc is None:
                        win.cursor.setToWindowPos(pos)
                    else:
                        win.cursor.setToIconSite(cursorIc, cursorSite)
                else:
                    # Open paren on top level had content
                    self.replaceChild(None, 'argIcon')
                    win.replaceTop(self, content)
                    topNode = reorderexpr.reorderArithExpr(content)
                    win.cursor.setToBestCoincidentSite(topNode, 'output')
            else:
                # Open paren had a parent.  Remove by attaching content to parent
                parentSite = parent.siteOf(self)
                if content is None:
                    parent.replaceChild(None, parentSite, leavePlace=True)
                    win.cursor.setToIconSite(parent, parentSite)
                else:
                    parent.replaceChild(content, parentSite)
                    win.cursor.setToIconSite(parent, parentSite)
                    reorderexpr.reorderArithExpr(content)
        win.requestRedraw(None, filterRedundantParens=True)

def createCursorParenFromFakeAst(astNode, window, skipArgCreate=False):
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    parenIcon = CursorParenIcon(closed=closed, window=window)
    if not skipArgCreate:
        argIcon = icon.createFromAst(astNode.arg, window)
        parenIcon.replaceChild(argIcon, 'argIcon')
    return parenIcon
icon.registerIconCreateFn(filefmt.UserParenFakeAst, createCursorParenFromFakeAst)
