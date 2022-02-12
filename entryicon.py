# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw
import re
import ast
import numbers
import comn
import iconlayout
import iconsites
import icon
import nameicons
import opicons
import listicons
import assignicons
import subscripticon
import parenicon
import infixicon
import cursors
import reorderexpr

PEN_BG_COLOR = (255, 245, 245, 255)
PEN_OUTLINE_COLOR = (255, 97, 120, 255)

# Gap to be left between the entry icon and next icons to the right of it
ENTRY_ICON_GAP = 3

PEN_MARGIN = 6

compareOperators = {'<', '>', '<=', '>=', '==', '!='}
binaryOperators = {'+', '-', '*', '**', '/', '//', '%', '@<<', '<<', '>>', '&', '|', '^'}
unaryOperators = {'+', '-', '~', 'not'}
emptyDelimiters = {' ', '\t', '\n', '\r', '\f', '\v'}
delimitChars = {*emptyDelimiters, '(', ')', '[', ']', '}', ':', '.', ';', '@', '=', ',',
 '-', '+', '*', '/', '<', '>', '%', '&', '|', '^', '!'}
keywords = {'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield', 'await'}

identPattern = re.compile('^[a-zA-z_][a-zA-Z_\\d]*$')
numPattern = re.compile('^([\\d_]*\\.?[\\d_]*)|'
 '(((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*)?$')
attrPattern = re.compile('^\\.[a-zA-z_][a-zA-Z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-z\\d_.\\(\\[\\{\\s+-~]')

penImage = comn.asciiToImage((
    "....oooo    ",
    "...o%%%%oo  ",
    "..o%%%%%%%oo",
    "..o%%%%%%%%%",
    ".o%%%%55%%%%",
    "o77777777%%%",
    ".o%%%%55%%%%",
    "..o%%%%%%%%%",
    "..o%%%%%%%oo",
    "...o%%%%oo  ",
    "....oooo    "))

attrPenImage = comn.asciiToImage((
    "....oooo...",
    "...o%%%%o..",
    "..o%%%%%%o.",
    ".o%%%%%%%%o",
    ".o%%%77%%%o",
    ".o%%%77%%%o",
    ".o%%7%%%%%o",
    "o%%7%%%%%o.",
    "o%7%%%%%o..",
    "o7%%oooo...",
    "oooo......."
))

class EntryIcon(icon.Icon):
    def __init__(self, initialString="", window=None, willOwnBlock=False,
     location=None):
        icon.Icon.__init__(self, window)
        self.text = initialString
        ascent, descent = icon.globalFont.getmetrics()
        self.height = ascent + descent + 2 * icon.TEXT_MARGIN + 1
        self.initTxtWidth = icon.globalFont.getsize("i")[0]
        self.txtWidthIncr = self.initTxtWidth
        x, y = location if location is not None else (0, 0)
        outSiteY = self.height // 2
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('attrOut', 'attrOut', 0, outSiteY + icon.ATTR_SITE_OFFSET)
        self.sites.add('seqIn', 'seqIn', 0, outSiteY)
        seqOutIndent = comn.BLOCK_INDENT if willOwnBlock else 0
        self.sites.add('seqOut', 'seqOut', seqOutIndent, outSiteY)
        self.rect = (x, y, x + self._width(), y + self.height)
        self.markLayoutDirty()
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.cursorPos = len(initialString)
        # If the entry icon will own a code block, create a BlockEnd icon and link it in
        if willOwnBlock:
            self.blockEnd = icon.BlockEnd(self, window)
            self.sites.seqOut.attach(self, self.blockEnd)

    def restoreForUndo(self, text):
        """Undo restores all attachments and saves the displayed text.  Update the
        remaining internal state based on attachments and passed text."""
        self.text = text
        self.cursorPos = len(text)
        self.markLayoutDirty()

    def _width(self, boxOnly=False):
        textWidth = icon.globalFont.getsize(self.text)[0]
        if textWidth > self.initTxtWidth:
            nIncrements = (textWidth - self.initTxtWidth) // self.initTxtWidth + 1
        else:
            nIncrements = 0
        adjWidth = self.initTxtWidth + nIncrements*self.txtWidthIncr
        boxWidth = adjWidth + 2 * icon.TEXT_MARGIN + 1 + PEN_MARGIN
        if boxOnly:
            return boxWidth
        return boxWidth + self.penOffset()

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            boxWidth = self._width(boxOnly=True) - 1
            img = Image.new('RGBA', (comn.rectWidth(self.rect), self.height))
            bgColor = PEN_OUTLINE_COLOR if style else PEN_BG_COLOR
            draw = ImageDraw.Draw(img)
            draw.rectangle((self.penOffset(), 0, self.penOffset() + boxWidth,
             self.height-1), fill=bgColor, outline=PEN_OUTLINE_COLOR)
            draw.text((self.textOffset, icon.TEXT_MARGIN), self.text,
             font=icon.globalFont, fill=(0, 0, 0, 255))
            if self.attachedToAttribute():
                nibTop = self.sites.attrOut.yOffset - attrPenImage.height + 2
                img.paste(attrPenImage, box=(0, nibTop), mask=attrPenImage)
            else:
                nibTop = self.sites.output.yOffset - penImage.height // 2
                img.paste(penImage, box=(0, nibTop), mask=penImage)
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def setPendingArg(self, newArg):
        if self.hasSite('pendingAttr'):
            self.sites.remove('pendingAttr')
        if not self.hasSite('pendingArg'):
            x = self.sites.output.xOffset + self._width()
            y = self.sites.output.yOffset
            self.sites.add('pendingArg', 'input', x, y)
        self.sites.pendingArg.attach(self, newArg, "output")

    def pendingArg(self):
        return self.sites.pendingArg.att if self.hasSite('pendingArg') else None

    def setPendingAttr(self, newAttr):
        if self.hasSite('pendingArg'):
            self.sites.remove('pendingArg')
        if not self.hasSite('pendingAttr'):
            x = self.sites.output.xOffset + self._width()
            y = self.sites.output.yOffset + icon.ATTR_SITE_OFFSET
            self.sites.add('pendingAttr', 'attrIn', x, y)
        self.sites.pendingAttr.attach(self, newAttr, "attrOut")

    def pendingAttr(self):
        return self.sites.pendingAttr.att if self.hasSite('pendingAttr') else None

    def attachedIcon(self):
        outIcon = self.sites.output.att
        if outIcon is not None:
            return outIcon
        attrIcon = self.sites.attrOut.att
        if attrIcon is not None:
            return attrIcon
        return None

    def attachedSite(self):
        attIcon = self.attachedIcon()
        if attIcon is None:
            return None
        return attIcon.siteOf(self)

    def attachedSiteType(self):
        attIcon = self.attachedIcon()
        if attIcon is None:
            return None
        return attIcon.typeOf(attIcon.siteOf(self))

    def addText(self, char):
        newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos + len(char))

    def backspaceInText(self, evt=None):
        if self.text != "":
            newText = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
            self._setText(newText, self.cursorPos-1)
            return
        # The entry icon contains no text.  Attempt to remove it
        if self.remove():
            return
        # The remove() call was unable to place pending args.  The nasty hack below
        # calls the window backspace code and then restores pending args/attrs if it
        # can.
        pendingArg = self.pendingArg()
        pendingAttr = self.pendingAttr()
        self.remove(forceDelete=True)
        self.window._backspaceIcon(evt)
        entryIcon = self.window.entryIcon
        if entryIcon:
            if not (entryIcon.pendingArg() or entryIcon.pendingAttr()):
                if pendingArg:
                    entryIcon.setPendingArg(pendingArg)
                elif pendingAttr:
                    entryIcon.setPendingAttr(pendingAttr)
        else:
            cursor = self.window.cursor
            if cursor.type == "icon":
                if cursor.site not in ('output', 'attrOut'):
                    self.window.entryIcon = self
                    cursor.icon.replaceChild(self, cursor.site)
            elif cursor.type == "window":
                self.window.entryIcon = self
                icon.moveRect(self.rect, cursor.pos)
                self.window.addTop(self)

    def arrowAction(self, direction):
        newCursorPos = self.cursorPos
        if direction == "Left":
            newCursorPos = max(0, self.cursorPos - 1)
        elif direction == "Right":
            newCursorPos = min(self.cursorPos + 1, len(self.text))
        if newCursorPos == self.cursorPos:
            return
        self.window.cursor.erase()
        self.cursorPos = newCursorPos
        self.window.cursor.draw()

    def remove(self, forceDelete=False):
        """Removes the entry icon and replaces it with it's pending argument or attribute
        if that is possible.  If the pending item cannot be put in place of the entry
        icon, does nothing and returns False, unless forceDelete is true, in which case
        the pending args or attributes are deleted along with the entry icon."""
        attachedIcon = self.attachedIcon()
        attachedSite = self.attachedSite()
        pendingArg = self.pendingArg()
        pendingList = isinstance(pendingArg, listicons.TupleIcon) and pendingArg.noParens
        if attachedIcon is not None:
            if pendingArg and self.attachedSiteType() == "input":
                if iconsites.isSeriesSiteId(attachedSite) and pendingList:
                    # Pending argument is naked tuple, and entry icon is attached to
                    # a series site.  Splice pending arguments in to that list
                    attachedIcon.replaceChild(None, attachedSite)
                    parentName, parentIdx = iconsites.splitSeriesSiteId(attachedSite)
                    for i, site in enumerate(list(pendingArg.sites.argIcons)):
                        arg = site.att
                        if arg is not None:
                            pendingArg.replaceChild(None, site.name, leavePlace=True)
                        attachedIcon.insertChild(arg, parentName, parentIdx + i)
                else:
                    attachedIcon.replaceChild(pendingArg, attachedSite)
                self.setPendingArg(None)
            elif self.pendingAttr() and self.attachedSiteType() == "attrIn":
                attachedIcon.replaceChild(self.pendingAttr(), attachedSite)
                self.setPendingAttr(None)
            elif forceDelete or self.pendingArg() is None and self.pendingAttr() is None:
                attachedIcon.replaceChild(None, attachedSite, leavePlace=True)
            else:
                return False
            if attachedIcon.hasSite(attachedSite):
                self.window.cursor.setToIconSite(attachedIcon, attachedSite)
            else:  # The last element of list can disappear when entry icon is removed
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(attachedSite)
                newSite = iconsites.makeSeriesSiteId(seriesName, seriesIdx-1)
                self.window.cursor.setToIconSite(attachedIcon, newSite)
        else:  # Entry icon is at top level
            if pendingArg:
                self.replaceChild(None, 'pendingArg', 'output')
                self.window.replaceTop(self, pendingArg)
                pendingArg.markLayoutDirty()
                self.window.cursor.setToIconSite(pendingArg, "output")
            elif self.pendingAttr():
                pendingAttr = self.pendingAttr()
                self.replaceChild(None, 'pendingAttr', 'attrOut')
                self.window.replaceTop(self, pendingAttr)
                pendingAttr.markLayoutDirty()
                self.window.cursor.setToIconSite(pendingAttr, "attrOut")
            else:
                prevIcon = self.prevInSeq()
                nextIcon = self.nextInSeq()
                self.window.removeIcons([self])
                if prevIcon:
                    self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                elif nextIcon:
                    self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                else:
                    self.window.cursor.setToWindowPos((self.rect[0], self.rect[1]))
        self.window.entryIcon = None
        return True

    def _setText(self, newText, newCursorPos):
        oldWidth = self._width()
        if self.attachedToAttribute():
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=True)
            if parseResult is None:
                parseResult = parseAttrText(newText, self.window)
        elif self.attachedIcon() is None or self.attachedSite() in ('seqIn', 'seqOut'):
            parseResult = parseTopLevelText(newText, self.window)
        else:  # Currently no other cursor places, must be expr
            parseResult, handlerIc = runIconTextEntryHandlers(self, newText, onAttr=False)
            if parseResult is None:
                parseResult = parseExprText(newText, self.window)
        # print('parse result', parseResult)
        if parseResult == "reject":
            cursors.beep()
            return
        cursor = self.window.cursor
        if parseResult == "accept":
            self.text = newText
            cursor.erase()
            self.cursorPos = newCursorPos
            cursor.draw()
            if self._width() != oldWidth:
                self.markLayoutDirty()
            return
        elif parseResult == "typeover":
            if self.pendingArg() is None and self.pendingAttr() is None:
                self.remove(forceDelete=True)
                siteBefore, siteAfter, text, idx = handlerIc.typeoverSites()
                if not handlerIc.setTypeover(1, siteAfter):
                    # Single character typeover, set cursor to site after typeover
                    cursor.setToIconSite(handlerIc, siteAfter)
                else:
                    cursor.setToTypeover(handlerIc)
                return
            else:
                cursors.beep()
                return
        elif parseResult == "comma":
            if self.commaEntered(self.attachedIcon(), self.attachedSite()):
                if self.attachedIcon() is not None:
                    self.attachedIcon().replaceChild(None, self.attachedSite())
                if self.pendingArg() is None and self.pendingAttr() is None:
                    self.window.entryIcon = None
                elif self.pendingArg() is not None and cursor.type == "icon" and \
                 cursor.siteType == "input" and cursor.icon.childAt(cursor.site) is None:
                    # Pending args can safely be placed (note that commaEntered will not
                    # put the cursor on an attribute site, so don't bother with them)
                    cursor.icon.replaceChild(self.pendingArg(), cursor.site)
                    self.setPendingArg(None)
                    self.window.entryIcon = None
                elif cursor.icon.childAt(cursor.site):
                    print("Yipes, can't place pending icons")
                    self.window.entryIcon = None
                else:
                    # Could not remove entry icon due to pending arguments
                    cursor.icon.replaceChild(self, cursor.site)
                    cursor.setToEntryIcon()
            else:
                cursors.beep()
            return
        elif parseResult == "colon":
            if not self.insertColon():
                cursors.beep()
            return
        elif parseResult == "openBracket":
            self.insertOpenParen(listicons.ListIcon)
            return
        elif parseResult == "endBracket":
            matchedBracket = self.getUnclosedParen(parseResult, self.attachedIcon(),
             self.attachedSite())
            if matchedBracket is None:
                if not self.remove():
                    # Cant unload pending args from cursor.  Don't allow move
                    cursors.beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    cursors.beep()
            else:
                matchedBracket.close()
                if self.remove():
                    cursor.setToIconSite(matchedBracket, "attrIcon")
                else:
                    # Move entry icon past the paren
                    self.attachedIcon().replaceChild(None, self.attachedSite())
                    matchedBracket.replaceChild(self, 'attrIcon')
                    # May now be possible (though unlikely) to remove entry icon
                    self.remove()
            return
        elif parseResult == "openBrace":
            self.insertOpenParen(listicons.DictIcon)
            return
        elif parseResult == "endBrace":
            matchedBracket = self.getUnclosedParen(parseResult, self.attachedIcon(),
             self.attachedSite())
            if matchedBracket is None:
                if not self.remove():
                    # Cant unload pending args from cursor.  Don't allow move
                    cursors.beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    cursors.beep()
            else:
                matchedBracket.close()
                if self.remove():
                    cursor.setToIconSite(matchedBracket, "attrIcon")
                else:
                    # Move entry icon past the paren
                    self.attachedIcon().replaceChild(None, self.attachedSite())
                    matchedBracket.replaceChild(self, 'attrIcon')
                    # May now be possible (though unlikely) to remove entry icon
                    self.remove()
            return
        elif parseResult == "openParen":
            self.insertOpenParen(parenicon.CursorParenIcon)
            return
        elif parseResult == "endParen":
            matchingParen = self.getUnclosedParen(parseResult, self.attachedIcon(),
             self.attachedSite())
            if matchingParen is None:
                # Maybe user was just trying to move past an existing paren by typing it
                if not self.remove():
                    # Cant unload pending args from cursor.  Don't allow move
                    cursors.beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    cursors.beep()
            elif matchingParen.__class__ is parenicon.CursorParenIcon and \
             matchingParen is self.attachedIcon() and self.attachedSite() == 'argIcon':
                # The entry icon is directly on the input site of a cursor paren icon to
                # be closed, this is the special case of an empty tuple: convert it to one
                parent = matchingParen.parent()
                tupleIcon = listicons.TupleIcon(window=self.window)
                if parent is None:
                    self.window.replaceTop(matchingParen, tupleIcon)
                    tupleIcon.markLayoutDirty()
                else:
                    parent.replaceChild(tupleIcon, parent.siteOf(matchingParen))
                if self.pendingArg() or self.pendingAttr():
                    # Move entry icon with pending args past the paren
                    tupleIcon.replaceChild(self, "attrIcon")
                else:
                    self.window.entryIcon = None
                    self.window.cursor.setToIconSite(tupleIcon, "attrIcon")
            else:
                # Try to place pending arguments where they came from.
                self.remove()
            return
        elif parseResult == "makeFunction":
            if not self.makeFunction(self.attachedIcon()):
                cursors.beep()
            return
        elif parseResult == "makeSubscript":
            if not self.makeSubscript(self.attachedIcon()):
                cursors.beep()
            return
        # Parser emitted an icon.  Splice it in to the hierarchy
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        snapLists = ic.snapLists(forCursor=True)
        if self.attachedIcon() is None:
            # Note that this clause includes sequence-site attachment
            self.window.replaceTop(self, ic)
            ic.markLayoutDirty()
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            elif "attrIn" in snapLists:
                cursor.setToIconSite(ic, "attrIcon")
            elif "seqOut" in snapLists:
                cursor.setToIconSite(ic, "seqOut")
        elif ic.__class__ in (assignicons.AssignIcon, assignicons.AugmentedAssignIcon):
            if not self.insertAssign(ic):
                cursors.beep()
                return
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            if ic.__class__ is nameicons.AttrIcon:
                self.attachedIcon().replaceChild(ic, "attrIcon")
                cursor.setToIconSite(ic, "attrIcon")
            else:
                if not self.appendOperator(ic):
                    cursors.beep()
                    return
        elif self.attachedSiteType() == "input":
            # Entry icon is attached to an input site
            self.attachedIcon().replaceChild(ic, self.attachedSite())
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            elif "attrIn" in snapLists:
                cursor.setToIconSite(ic, snapLists["attrIn"][0][2])
            else:
                cursor.removeCursor()
        # If entry icon has pending arguments, try to place them.  Code does its best
        # to place the cursor at the most reasonable spot.  If vacant, place pending
        # args there
        if self.pendingArg() is not None and remainingText == "":
            if cursor.type == "icon" and cursor.siteType == "input" and \
             cursor.icon.childAt(cursor.site) is None:
                cursor.icon.replaceChild(self.pendingArg(), cursor.site)
                self.setPendingArg(None)
                if cursor.icon.__class__ in (opicons.BinOpIcon, opicons.UnaryOpIcon,
                        opicons.IfExpIcon):
                    # Changing an operand of an arithmetic operator may require reorder
                    reorderexpr.reorderArithExpr(cursor.icon)
        if self.pendingAttr() is not None and remainingText == "":
            if cursor.type == "icon" and cursor.siteType == "attrIn" and \
             cursor.icon.childAt(cursor.site) is None:
                cursor.icon.replaceChild(self.pendingAttr(), cursor.site)
                self.setPendingAttr(None)
        # If the entry icon can go away, remove it and we're done
        if self.pendingArg() is None and self.pendingAttr() is None and \
                remainingText == "":
            self.window.entryIcon = None
            return
        # There is remaining text or pending arguments.  Restore the entry icon
        if cursor.type != "icon":  # I don't think this can happen
            print('Cursor type not icon in _setText')
            return
        cursor.icon.replaceChild(self, cursor.site)
        cursor.setToEntryIcon()
        self.markLayoutDirty()
        self.text = ""
        self.cursorPos = 0
        if remainingText == "":
            cursor.draw()
            return
        # There is still text that might be processable.  Recursively go around again
        # (we only get here if something was processed, so this won't loop forever)
        self._setText(remainingText, len(remainingText))

    def commaEntered(self, onIcon, site):
        """A comma has been entered.  Search up the hierarchy to find a list, tuple,
        cursor-paren, or parameter list, parting every expression about the newly inserted
        comma.  If no comma-separated type is found, part the expression up to either an
        assignment, or the top level.  Return False if user tries to place comma within
        unary or binary op auto-parens, or on an icon that interrupts horizontal sequence
        of icons (divide)."""
        # This allows a comma to be typed anywhere in an expression, which is probably
        # massive overkill.  Probably just beeping to say "no, you can't put a comma
        # there", would be just as reasonable as ripping apart the enclosing expression
        # and leaving a hole somewhere.
        cursorPlaced = False
        if onIcon is None:
            # The cursor is on the top level
            tupleIcon = listicons.TupleIcon(window=self.window)
            tupleIcon.insertChildren([None, self.pendingArg()], "argIcons", 0)
            self.setPendingArg(None)
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 0)
            self.window.replaceTop(self, tupleIcon)
            return True
        siteType = onIcon.typeOf(site)
        if iconsites.isSeriesSiteId(site) and siteType == "input":
            # This is essentially ",,", which means leave a new space for an arg
            # Entry icon holds pending arguments
            seriesName, seriesIndex = iconsites.splitSeriesSiteId(site)
            onIcon.insertChildren([None], seriesName, seriesIndex)
            siteAfterComma = iconsites.makeSeriesSiteId(seriesName, seriesIndex + 1)
            if onIcon.childAt(siteAfterComma) == self:
                # Remove the Entry Icon and restore its pending arguments
                if self.pendingArg() is None:
                    # replaceChild on listTypeIcon removes comma.  Put it back
                    onIcon.replaceChild(None, siteAfterComma, leavePlace=True)
                else:
                    onIcon.replaceChild(self.pendingArg(), siteAfterComma)
                    self.setPendingArg(None)
            self.window.cursor.setToIconSite(onIcon, siteAfterComma)
            return True
        if onIcon.__class__ in (opicons.UnaryOpIcon, opicons.DivideIcon) and \
         siteType == "input":
            return False
        elif onIcon.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and \
                siteType == "input" and onIcon.hasParens:
            return False
        elif onIcon.__class__ is parenicon.CursorParenIcon and siteType != 'attrIn':
            # Cursor paren needs to be converted to a tuple
            tupleIcon = listicons.TupleIcon(window=self.window, closed=True,
                typeoverIdx=0)
            args = [None]
            if onIcon.sites.argIcon.att and onIcon.sites.argIcon.att is not self:
                args += [onIcon.sites.argIcon.att]
            tupleIcon.insertChildren(args, "argIcons", 0)
            parent = onIcon.parent()
            if parent is None:
                self.window.replaceTop(onIcon, tupleIcon)
            else:
                parent.replaceChild(tupleIcon, parent.siteOf(onIcon))
            if onIcon.closed:
                attrIcon = onIcon.sites.attrIcon.att
                onIcon.replaceChild(None, 'attrIcon')
                tupleIcon.replaceChild(attrIcon, 'attrIcon')
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 0)
            return True
        if onIcon.__class__ in (opicons.BinOpIcon, infixicon.InfixIcon,
                opicons.IfExpIcon) and site == binOpLeftArgSite(onIcon):
            leftArg = None
            rightArg = onIcon
            if onIcon.leftArg() is self:
                onIcon.replaceChild(self.pendingArg(), binOpLeftArgSite(onIcon))
                self.setPendingArg(None)
        elif onIcon.__class__ in (opicons.BinOpIcon, infixicon.InfixIcon,
                opicons.IfExpIcon) and site == binOpRightArgSite(onIcon):
            leftArg = onIcon
            rightArg = onIcon.rightArg()
            if rightArg is self:
                rightArg = self.pendingArg()
                self.setPendingArg(None)
            onIcon.replaceChild(None, binOpRightArgSite(onIcon))
            self.window.cursor.setToIconSite(onIcon,  binOpRightArgSite(onIcon))
            cursorPlaced = True
        else:
            onIcon = icon.findAttrOutputSite(onIcon)
            leftArg = onIcon
            rightArg = None
        child = onIcon
        for parent in onIcon.parentage():
            childSite = parent.siteOf(child)
            if iconsites.isSeriesSiteId(childSite):
                onIcon.markLayoutDirty()
                parent.replaceChild(leftArg, childSite, leavePlace=True)
                seriesName, seriesIndex = iconsites.splitSeriesSiteId(childSite)
                parent.insertChild(rightArg, seriesName, seriesIndex + 1)
                if hasattr(parent, "closed") and not parent.closed:
                    # Once an item has a comma, we know what it is and where it ends, and
                    # an open paren/bracket/brace with commas would be hard to handle.
                    parent.close()
                if not cursorPlaced:
                    cursorIdx = seriesIndex if leftArg is None else seriesIndex + 1
                    self.window.cursor.setToIconSite(parent, seriesName, cursorIdx)
                return True
            if parent.__class__ is parenicon.CursorParenIcon:
                tupleIcon = listicons.TupleIcon(window=self.window, typeover=True)
                tupleIcon.insertChildren([leftArg, rightArg], "argIcons", 0)
                parentParent = parent.parent()
                if parentParent is None:
                    self.window.replaceTop(parent, tupleIcon)
                else:
                    parentParent.replaceChild(tupleIcon, parentParent.siteOf(parent))
                if parent.hasSite('attrIcon'):
                    attrIcon = parent.sites.attrIcon.att
                    parent.replaceChild(None, 'attrIcon')
                    tupleIcon.replaceChild(attrIcon, 'attrIcon')
                if not cursorPlaced:
                    idx = 0 if leftArg is None else 1
                    self.window.cursor.setToIconSite(tupleIcon, "argIcons", idx)
                return True
            if isinstance(parent, opicons.UnaryOpIcon):
                leftArg = parent
            elif parent.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and \
                    not parent.hasParens or isinstance(parent, infixicon.InfixIcon):
                # Parent is a binary op icon without parens, and site is one of the two
                # input sites
                if parent.leftArg() is child:  # Insertion was on left side of operator
                    parent.replaceChild(rightArg, binOpLeftArgSite(parent))
                    if parent.leftArg() is None:
                        self.window.cursor.setToIconSite(parent, binOpLeftArgSite(parent))
                        cursorPlaced = True
                    rightArg = parent
                elif parent.rightArg() is child:   # Insertion on right side of operator
                    parent.replaceChild(leftArg, binOpRightArgSite(parent))
                    if parent.rightArg() is None:
                        self.window.cursor.setToIconSite(parent, binOpRightArgSite(parent))
                        cursorPlaced = True
                    leftArg = parent
                else:
                    print('Unexpected site attachment in "commaEntered" function')
                    return False
            else:
                # Parent was not an arithmetic operator or had parens
                return False
            child = parent
        # Reached top level.  Create Tuple
        tupleIcon = listicons.TupleIcon(window=self.window, noParens=True)
        self.window.replaceTop(child, tupleIcon)
        tupleIcon.insertChildren([leftArg, rightArg], "argIcons", 0)
        if not cursorPlaced:
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 1)
        return True

    def insertOpenParen(self, iconClass):
        """Called when the user types an open paren, bracket, or brace to insert an icon
        of type given in iconClass.  Inserting an open paren/bracket/brace has the power
        to completely rearrange the icon hierarchy.  For a consistent user-interface, we
        maintain un-closed parens at the highest level of the hierarchy that they can
        influence (clicking and dragging behavior is dependent on the hierarchy, even if
        code appearance is identical).  It is easier to maintain parens at the highest
        level than the lowest, since the paren itself makes this happen automatically,
        and they can be found by just looking up from a prospective end position."""
        # Create an icon of the requested class and move the entry icon inside of it
        if iconClass is parenicon.CursorParenIcon:
            closed = False  # We leave even empty paren open to detect () for empty tuple
            inputSite = 'argIcon'
        else:
            closed = self.pendingArg() is None
            inputSite = 'argIcons_0'
        newParenIcon = iconClass(window=self.window, closed=closed, typeover=closed)
        attachedIc = self.attachedIcon()
        attachedSite = self.attachedSite()
        if attachedIc is None:
            self.window.replaceTop(self, newParenIcon)
        else:
            attachedIc.replaceChild(newParenIcon, attachedSite)
        newParenIcon.replaceChild(self, inputSite)
        # Attempt to get rid of the entry icon and place pending arg in its place
        self.remove()
        # Reorder the expression with the new open paren in place (skip some work if the
        # entry icon was at the top level, since no reordering is necessary, there)
        if attachedIc is not None:
            reorderexpr.reorderArithExpr(newParenIcon)

    def getUnclosedParen(self, token, fromIcon, fromSite):
        """Find a matching open paren/bracket/brace or paren-less tuple that could be
        closed by an end paren/bracket/brace (which type is specified by token) at
        fromIcon, fromSite.  If a matching unclosed item is found, relocate it to the
        appropriate level and rearrange the icon hierarchy such that it can be closed.
        Rearrangement may be significant.  Unclosed icons are inserted and maintained at
        the highest level in the hierarchy that they can reach.  In addition to changing
        the level of the matching item itself, closing can expose lower-precedence
        operations that will get moved above it in the hierarchy."""
        matchingParen = searchForOpenParen(token, fromIcon, fromSite)
        if matchingParen is None and token == 'endParen':
            # Arithmetic parens are more forgiving and reorderArithExpr can shift
            # them around even if there is not a match on the appropriate level, in
            # which case, all we need is an unclosed paren left of the end paren
            for op in reorderexpr.traverseExprLeftToRight(
                    reorderexpr.highestAffectedExpr(fromIcon), closeParenAfter=fromIcon):
                if isinstance(op, reorderexpr.CloseParenToken) and op.parenIcon is None:
                    # A CloseParenToken with parenIcon of None is the inserted end paren
                    break
                if isinstance(op, reorderexpr.OpenParenToken) and isinstance(op.parenIcon,
                 parenicon.CursorParenIcon) and not op.parenIcon.closed:
                    matchingParen = op.parenIcon
            else:
                print('getUnclosedParen failed to find close-paren site')
        if matchingParen is None:
            return None
        if matchingParen is fromIcon or isinstance(matchingParen, listicons.TupleIcon):
            # matchingParen is an open cursor paren or a tuple with no parens or an
            # open cursor paren.  No reordering necessary, just add/close the parens
            if matchingParen.__class__ is listicons.TupleIcon:
                matchingParen.restoreParens()
            else:
                matchingParen.close()
            return matchingParen
        # Rearrange the hierarchy so the paren/bracket/brace is above all the icons it
        # should enclose and outside of those it does not enclose.  reorderArithExpr
        # closes the parens if it succeeds.
        reorderexpr.reorderArithExpr(matchingParen, fromIcon)
        return matchingParen

    def makeFunction(self, ic):
        closed = self.pendingArg() is None
        callIcon = listicons.CallIcon(window=self.window,
            closed=closed, typeover=closed)
        ic.replaceChild(callIcon, 'attrIcon')
        if self.pendingAttr():
            callIcon.replaceChild(self, 'argIcons_0')
            return True
        if self.pendingArg():
            callIcon.replaceChild(self.pendingArg(), 'argIcons_0')
        self.window.entryIcon = None
        self.window.cursor.setToIconSite(callIcon, "argIcons", 0)
        return True

    def makeSubscript(self, ic):
        closed = self.pendingArg() is None
        subscriptIcon = subscripticon.SubscriptIcon(window=self.window, closed=closed,
            typeover=closed)
        ic.replaceChild(subscriptIcon, 'attrIcon')
        if self.pendingAttr():
            subscriptIcon.replaceChild(self, 'indexIcon')
            return True
        if self.pendingArg():
            subscriptIcon.replaceChild(self.pendingArg(), 'indexIcon')
        self.window.entryIcon = None
        self.window.cursor.setToIconSite(subscriptIcon, 'indexIcon')
        return True

    def appendOperator(self, newOpIcon):
        """The entry icon is attached to an attribute site and a binary operator has been
        entered.  Stitch the operator in to the correct level with respect to the
        surrounding binary operators, and move the cursor to the empty operand slot."""
        argIcon = icon.findAttrOutputSite(self.attachedIcon())
        if argIcon is None:
            return False
        self.attachedIcon().replaceChild(None, self.attachedSite())
        leftArg = argIcon
        rightArg = None
        childOp = argIcon
        stopAtParens = False
        # Walk up the hierarchy of binary operations, breaking each one in to left and
        # right operands for the new operation.  Stop when the parent operation has
        # lower precedence, or is not a binary operation.  Also stop if the parent
        # operation has equal precedence, and the associativity of the operation matches
        # the side of the operation on which the insertion is being made.
        for op in argIcon.parentage():
            if stopAtParens or op.__class__ not in (opicons.BinOpIcon, opicons.IfExpIcon,
                    opicons.UnaryOpIcon) or newOpIcon.precedence > op.precedence or \
                    newOpIcon.precedence == op.precedence and (
                     op.leftAssoc() and op.leftArg() is childOp or
                     op.rightAssoc() and op.rightArg() is childOp):
                op.replaceChild(newOpIcon, op.siteOf(childOp))
                break
            if op.__class__ is opicons.IfExpIcon and op.siteOf(childOp) == "testExpr":
                op.replaceChild(newOpIcon, op.siteOf(childOp))
                break
            if op.__class__ is opicons.UnaryOpIcon:
                op.replaceChild(leftArg, "argIcon")
                leftArg = op
            else:  # BinaryOp
                if op.leftArg() is childOp:  # Insertion was on left side of operation
                    op.replaceChild(rightArg, binOpLeftArgSite(op))
                    if op.leftArg() is None:
                        self.window.cursor.setToIconSite(op, binOpLeftArgSite(op))
                    rightArg = op
                else:                      # Insertion was on right side of operation
                    op.replaceChild(leftArg, binOpRightArgSite(op))
                    leftArg = op
                if op.hasParens:
                    # If the op has parens and the new op has been inserted within them,
                    # do not go beyond the parent operation
                    stopAtParens = True
            childOp = op
        else:  # Reached the top level without finding a parent for newOpIcon
            self.window.replaceTop(childOp, newOpIcon)
        leftSite = "topArg" if newOpIcon.__class__ is opicons.DivideIcon else \
            binOpLeftArgSite(newOpIcon)
        rightSite = "bottomArg" if newOpIcon.__class__ is opicons.DivideIcon else \
            binOpRightArgSite(newOpIcon)
        if isinstance(newOpIcon, opicons.IfExpIcon):
            self.window.cursor.setToIconSite(newOpIcon, 'testExpr')
        elif rightArg is None:
            self.window.cursor.setToIconSite(newOpIcon, rightSite)
        newOpIcon.markLayoutDirty()
        newOpIcon.replaceChild(leftArg, leftSite)
        newOpIcon.replaceChild(rightArg, rightSite)
        # The conventional method to type a division operation with lower precedent
        # operator(s) in the numerator is to use parenthesis.  However because of our
        # vertical arrangement, those parens are thereafter unnecessary and unaesthetic.
        # Removing them here (when the divide icon is first inserted) rather than as a
        # general rule in filterRedundantParens, allows the user to add them back later
        # if needed for subsequent edits and not be unexpectedly removed.
        if newOpIcon.__class__ is opicons.DivideIcon:
            topArgChild = newOpIcon.childAt('topArg')
            if isinstance(topArgChild, parenicon.CursorParenIcon) and topArgChild.closed:
                newOpIcon.replaceChild(topArgChild.childAt('argIcon'), 'topArg')
        return True

    def insertAssign(self, assignIcon):
        attIcon = icon.findAttrOutputSite(self.attachedIcon())
        attIconClass = attIcon.__class__
        isAugmentedAssign = assignIcon.__class__ is assignicons.AugmentedAssignIcon
        if not (attIconClass is assignicons.AssignIcon or
                attIconClass is listicons.TupleIcon and attIcon.noParens or
                self.attachedToAttribute() and attIconClass in (nameicons.IdentifierIcon,
                 listicons.TupleIcon, listicons.ListIcon, listicons.DictIcon,
                 nameicons.AttrIcon) or
                isinstance(self.attachedIcon(), assignicons.AssignIcon)):
            return False
        if self.attachedToAttribute():
            highestCoincidentIcon = iconsites.highestCoincidentIcon(attIcon)
            if highestCoincidentIcon in self.window.topIcons:
                # The cursor is attached to an attribute of a top-level icon of a type
                # appropriate as a target. Insert assignment icon and make it the target.
                self.attachedIcon().replaceChild(None, self.attachedSite())
                self.window.replaceTop(highestCoincidentIcon, assignIcon)
                if highestCoincidentIcon is not attIcon:
                    parent = attIcon.parent()
                    parentSite = parent.siteOf(attIcon)
                    parent.replaceChild(None, parentSite)
                    assignIcon.replaceChild(highestCoincidentIcon, 'values_0')
                    self.window.cursor.setToIconSite(parent, parentSite)
                else:
                    self.window.cursor.setToIconSite(assignIcon, "values_0")
                if isAugmentedAssign:
                    assignIcon.replaceChild(attIcon, 'targetIcon')
                else:
                    assignIcon.replaceChild(attIcon, "targets0_0")
                return True
        topParent = (attIcon if attIcon is not None else self.attachedIcon()).topLevelParent()
        if topParent.__class__ is listicons.TupleIcon and topParent.noParens:
            # There is a no-paren tuple at the top level waiting to be converted in to an
            # assignment statement.  Do the conversion.
            targetIcons = topParent.argIcons()
            if isAugmentedAssign:
                # Augmented (i.e. +=) assigns have just one target, but it is possible
                # to delete out a comma and be left with a single value in the tuple
                if len(targetIcons) != 1:
                    return False
                self.attachedIcon().replaceChild(None, self.attachedSite())
                assignIcon.replaceChild(targetIcons[0], 'targetIcon')
            else:
                attachedIcon = self.attachedIcon()
                attachedSite = self.attachedSite()
                attachedIcon.replaceChild(None, attachedSite)
                if attachedIcon is topParent:
                    # entry icon is directly attached to the tuple (on comma or body)
                    insertSiteId = attachedSite
                    targetIcons.remove(self)
                else:
                    insertSiteId = topParent.siteOf(attIcon, recursive=True)
                for tgtIcon in targetIcons:
                    topParent.replaceChild(None, topParent.siteOf(tgtIcon))
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(insertSiteId)
                splitIdx = seriesIdx + (0 if topParent is attachedIcon else 1)
                assignIcon.insertChildren(targetIcons[:splitIdx], 'targets0', 0)
                assignIcon.insertChildren(targetIcons[splitIdx:], 'values', 0)
                if splitIdx < len(targetIcons):
                    assignIcon.insertChild(None, 'values_0')
            self.window.replaceTop(topParent, assignIcon)
            self.window.cursor.setToIconSite(assignIcon, "values_0")
            return True
        if topParent.__class__ is assignicons.AssignIcon and not isAugmentedAssign:
            # There is already an assignment icon.  Add a new clause, splitting the
            # target list at the entry location.  (assignIcon is thrown away)
            attachedIcon = self.attachedIcon()
            attachedSite = self.attachedSite()
            attachedIcon.replaceChild(None, attachedSite)
            if attachedIcon is topParent:
                # entry icon is directly attached to the assignment (on comma or body)
                insertSiteId = attachedSite
            else:
                insertSiteId = topParent.siteOf(attIcon, recursive=True)
            seriesName, seriesIdx = iconsites.splitSeriesSiteId(insertSiteId)
            splitIdx = seriesIdx + (0 if topParent is attachedIcon else 1)
            if seriesName == 'values':  # = was typed in the value series
                newTgtGrpIdx = len(topParent.tgtLists)
                cursorSite = 'values_0'
                iconsToMove = [site.att for site in topParent.sites.values][:splitIdx]
            else:  # = was typed in a target series
                newTgtGrpIdx = int(seriesName[7:]) + 1
                cursorSite = 'targets%d_0' % newTgtGrpIdx
                series = getattr(topParent.sites, seriesName)
                iconsToMove = [site.att for site in series][splitIdx:]
            topParent.addTargetGroup(newTgtGrpIdx)
            for tgtIcon in iconsToMove:
                if tgtIcon is not None:
                    topParent.replaceChild(None, topParent.siteOf(tgtIcon))
            topParent.insertChildren(iconsToMove, 'targets%d' % newTgtGrpIdx, 0)
            if topParent.childAt(cursorSite):
                topParent.insertChild(None, cursorSite)
            self.window.cursor.setToIconSite(topParent, cursorSite)
            return True
        return False

    def insertColon(self):
        # Look for a parent icon that supports colons (subscript or dictionary)
        for parent in self.attachedIcon().parentage(includeSelf=True):
            if isinstance(parent, subscripticon.SubscriptIcon):
                if parent.hasSite('stepIcon'):
                    # Subscript already has all 3 colons
                    colonInserted = False
                    break
                # Subscript icon accepting colon, found.  Add a new site to it
                subsIc = parent
                if subsIc.hasSite('upperIcon'):
                    subsIc.changeNumSubscripts(3)
                    siteAdded = 'stepIcon'
                else:
                    subsIc.changeNumSubscripts(2)
                    siteAdded = 'upperIcon'
                # If the cursor was on the first site, may need to shift second-site icons
                entrySite = subsIc.siteOf(self, recursive=True)
                if entrySite == 'indexIcon' and siteAdded == "stepIcon":
                    toShift = subsIc.childAt('upperIcon')
                    subsIc.replaceChild(None, "upperIcon")
                    subsIc.replaceChild(toShift, 'stepIcon')
                    cursorToSite = 'upperIcon'
                else:
                    cursorToSite = siteAdded
                cursorToIcon = subsIc
                colonInserted = True
                break
            if isinstance(parent, listicons.DictIcon):
                dictIc = parent
                site = parent.siteOf(self, recursive=True)
                child = dictIc.childAt(site)
                dictElem = listicons.DictElemIcon(window=self.window)
                if isinstance(child, listicons.DictElemIcon):
                    # There's already a colon in this clause.  We allow a colon to be
                    # typed on the left of an existing clause, since that is how one
                    # naturally types a new clause (when they begin after the comma or to
                    # the left of the first clause).  Typing a colon on the right side of
                    # a dictElem is not expected without a comma, and not supported.
                    dictElemSite = child.siteOf(self, recursive=True)
                    if dictElemSite != 'leftArg':
                        colonInserted = False
                        break
                    # Splitting apart an expression is hard.  Here we cheat and use the
                    # commaEntered function to do it (since we need a comma, too).
                    if not self.commaEntered(self.attachedIcon(), self.attachedSite()):
                        colonInserted = False
                        break
                    # commaEntered will set the cursor position to the site where any
                    # pending args should be deposited.  If appropriate, deposit them.
                    cursor = self.window.cursor
                    if self.pendingArg() and cursor.type == 'icon' and \
                     cursor.siteType == 'input' and \
                     cursor.icon.childAt(cursor.site) is None:
                        cursor.icon.replaceChild(self.pendingArg(), cursor.site)
                        self.replaceChild(None, 'pendingArg')
                    # Insert the new dictElem before the dictElem that originally held
                    # the entry icon in its left argument.
                    dictElemArg = parent.childAt(site)
                    parent.replaceChild(dictElem, site)
                    dictElem.replaceChild(dictElemArg, 'leftArg')
                elif child is self:
                    # There's nothing at the site except entry icon and whatever we are
                    # holding, move entry icon to right arg, unless we're *holding* a
                    # dictElem, in which case, don't insert the new dictElem
                    if isinstance(self.pendingArg(), listicons.DictElemIcon):
                        colonInserted = False
                        break
                    dictIc.replaceChild(dictElem, site)
                    dictElem.replaceChild(self, 'rightArg')
                else:
                    # There's something at the site.  Put a colon after it
                    dictIc.replaceChild(dictElem, site)
                    dictElem.replaceChild(child, 'leftArg')
                cursorToIcon = dictElem
                cursorToSite = 'rightArg'
                colonInserted = True
                break
        else:
            colonInserted = False
        if not colonInserted:
            # Icon not found or colon couldn't be placed
            cursorToIcon = self.attachedIcon()
            cursorToSite = self.attachedSite()
        # Decide on appropriate disposition for entry icon and cursor.  Try to remove
        # entry icon if at all possible, even if the colon was rejected, since there
        # won't be any text left in it.
        cursorSiteType = cursorToIcon.typeOf(cursorToSite)
        if self.pendingArg() and cursorSiteType == 'input' or \
         self.pendingAttr() and cursorSiteType == 'attrIn':
            # Entry icon has a pending argument which can be attached
            self.attachedIcon().replaceChild(None, self.attachedSite())
            self.window.entryIcon = None
            pend = self.pendingArg() if cursorSiteType == "input" else self.pendingAttr()
            cursorToIcon.replaceChild(pend, cursorToSite)
            self.window.cursor.setToIconSite(cursorToIcon, cursorToSite)
        elif self.pendingAttr() or self.pendingArg():
            # Entry icon has a pending arg or attr which could not be attached
            self.attachedIcon().replaceChild(None, self.attachedSite())
            cursorToIcon.replaceChild(self, cursorToSite)
        else:
            # Entry icon has nothing pending and can safely be removed
            self.attachedIcon().replaceChild(None, self.attachedSite())
            self.window.entryIcon = None
            self.window.cursor.setToIconSite(cursorToIcon, cursorToSite)
        return colonInserted

    def click(self, evt):
        self.window.cursor.erase()
        self.cursorPos = findTextOffset(self.text, evt.x - self.rect[0] - self.textOffset)
        self.window.cursor.draw()

    def pointInTextArea(self, x, y):
        left, top, right, bottom = self.rect
        left += penImage.width
        top += 2
        bottom -= 2
        right -= 2
        return left < x < right and top < y < bottom

    def doLayout(self, siteX, siteY, layout):
        width = self._width() + icon.outSiteImage.width - 1
        if self.attachedSite() == "attrIcon":
            outSiteY = siteY - icon.ATTR_SITE_OFFSET
            outSiteX = siteX - 1
            self.textOffset = attrPenImage.width + icon.TEXT_MARGIN
        else:
            outSiteY = siteY
            outSiteX = siteX
            self.textOffset = penImage.width + icon.TEXT_MARGIN
        top = outSiteY - self.height//2
        self.rect = (outSiteX, top, outSiteX + width, top + self.height)
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.layoutDirty = False
        self.drawList = None

    def calcLayouts(self):
        if self.pendingArg():
            pendingArgLayouts = self.pendingArg().calcLayouts()
        elif self.pendingAttr():
            pendingArgLayouts = self.pendingAttr().calcLayouts()
        else:
            pendingArgLayouts = (None,)
        baseWidth = self._width() - (1 if self.attachedToAttribute() else 2)
        siteOffset = self.height // 2
        if self.attachedSite() == "attrIcon":
            siteOffset += icon.ATTR_SITE_OFFSET
        layouts = []
        for pendingArgLayout in pendingArgLayouts:
            width = baseWidth
            layout = iconlayout.Layout(self, width, self.height, siteOffset)
            if self.pendingArg():
                layout.addSubLayout(pendingArgLayout, 'pendingArg', width, 0)
                width += pendingArgLayout.width
            elif self.pendingAttr():
                layout.addSubLayout(pendingArgLayout, 'pendingAttr', width,
                 icon.ATTR_SITE_OFFSET)
                width += pendingArgLayout.width
            layout.width = width + ENTRY_ICON_GAP
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def clipboardRepr(self, offset):
        return None

    def execute(self):
        raise icon.IconExecException(self, "Can't execute text-entry field")

    def attachedToAttribute(self):
        return self.attachedSite() is not None and \
         self.attachedSiteType() in ("attrOut", "attrIn")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN


def parseAttrText(text, window):
    if len(text) == 0:
        return "accept"
    if text == '.' or attrPattern.fullmatch(text):
        return "accept"  # Legal attribute pattern
    if text in ("i", "a", "o", "an"):
        return "accept"  # Legal precursor characters to binary keyword operation
    if text == "if":
        return opicons.IfExpIcon(window, typeover=True), None # In-line if
    if text in ("and", "is", "in", "or"):
        return opicons.BinOpIcon(text, window), None # Binary keyword operation
    if text in ("*", "/", "@", "<", ">", "=", "!"):
        return "accept"  # Legal precursor characters to binary operation
    if text in compareOperators:
        return opicons.BinOpIcon(text, window), None
    if text in binaryOperators:
        return "accept"  # Binary ops can be part of augmented assign (i.e. +=)
    if text[:-1] in binaryOperators and text[-1] == '=':
        return assignicons.AugmentedAssignIcon(text[:-1], window), None
    if text == '(':
        return "makeFunction"  # Make a function from the attached icon
    if text == ')':
        return "endParen"
    if text == '[':
        return "makeSubscript"
    if text == ']':
        return "endBracket"
    if text == '}':
        return "endBrace"
    if text == ',':
        return "comma"
    if text == ':':  #... see if this can be removed once handlers are in place
        return "colon"
    op = text[:-1]
    delim = text[-1]
    if attrPattern.fullmatch(op):
        return nameicons.AttrIcon(op[1:], window), delim
    if opDelimPattern.match(delim):
        if op in compareOperators:
            return opicons.BinOpIcon(op, window), delim
        if op in binaryOperators:
            # Valid binary operator followed by allowable operand character
            if op == '/':
                return opicons.DivideIcon(False, window), delim
            elif op == '//':
                return opicons.DivideIcon(True, window), delim
            return opicons.BinOpIcon(op, window), delim
        if op[:-1] in binaryOperators and op[-1] == '=':
            return assignicons.AugmentedAssignIcon(op[:-1], window), delim
    if op == '=':
        return assignicons.AssignIcon(1, window), delim
    return "reject"

def parseExprText(text, window):
    if len(text) == 0:
        return "accept"
    if text in unaryOperators:
        # Unary operator
        return opicons.UnaryOpIcon(text, window), None
    if text == 'yield':
        return nameicons.YieldIcon(window), None
    if text == 'await':
        return nameicons.AwaitIcon(window), None
    if text == '(':
        return "openParen"
    if text == ')':
        return "endParen"
    if text == '[':
        return "openBracket"
    if text == ']':
        return "endBracket"
    if text == '{':
        return "openBrace"
    if text == '}':
        return "endBrace"
    if text == ',':
        return "comma"
    if text == ':':
        return "colon"
    if text == '=':
        return assignicons.AssignIcon(1, window), None
    if identPattern.fullmatch(text) or numPattern.fullmatch(text):
        return "accept"  # Nothing but legal identifier and numeric
    delim = text[-1]
    text = text[:-1]
    if opDelimPattern.match(delim):
        if text in unaryOperators:
            return opicons.UnaryOpIcon(text, window), delim
    if not (identPattern.fullmatch(text) or numPattern.fullmatch(text)):
        return "reject"  # Precursor characters do not form valid identifier or number
    if len(text) == 0 or delim not in delimitChars:
        return "reject"  # No legal text or not followed by a legal delimiter
    # All but the last character is ok and the last character is a valid delimiter
    if text in ('False', 'None', 'True'):
        return nameicons.IdentifierIcon(text, window), delim
    if text in keywords:
        return "reject"
    exprAst = parseExprToAst(text)
    if exprAst is None:
        return "reject"
    if exprAst.__class__ == ast.Name:
        return nameicons.IdentifierIcon(exprAst.id, window), delim
    if exprAst.__class__ == ast.Num:
        return nameicons.NumericIcon(exprAst.n, window), delim
    if exprAst.__class__ == ast.Constant and isinstance(exprAst.value, numbers.Number):
        return nameicons.NumericIcon(exprAst.value, window), delim
    return "reject"

def parseTopLevelText(text, window):
    if len(text) == 0:
        return "accept"
    for stmt, icClass in cursors.topLevelStmts.items():
        if len(text) <= len(stmt) and text == stmt[:len(text)]:
            return "accept"
        delim = text[-1]
        if text[:-1] == stmt and delim in delimitChars:
            kwds = {}
            if stmt[:5] == "async":
                kwds['isAsync'] = True
            if hasattr(icClass, 'hasTypeover') and icClass.hasTypeover:
                kwds['typeover'] = True
            return icClass(window=window, **kwds), delim
    if text == '*':
        # Sadly, while very unusual, it is possible to write *a, b = c, and since we
        # don't yet even know if it's a list on the first keystroke, it's necessary to
        # generate a star icon, even though this is more likely a typing error.
        return listicons.StarIcon(window), None
    return parseExprText(text, window)

def runIconTextEntryHandlers(entryIc, text, onAttr):
    """Look for icon text entry handlers above the entry icon and execute in order,
    until one returns a result or we hit the top.  If a handler fired, return the
    parse result and the icon whose textEntryHandler fired."""
    if text == "":
        return None, None
    for ic in entryIc.parentage(includeSelf=False):
        result = ic.textEntryHandler(entryIc, text, onAttr)
        if result is not None:
            return result, ic
    return None, None

def findTextOffset(text, pixelOffset):
    # We use a proportionally-spaced font, but don't have full access to the font
    # rendering code, so the only tool we have to see how it got laid out is the
    # font.getsize method, which can only answer the question: "how many pixels long is
    # this entire string".  Rather than try to measure individual characters and adjust
    # for kerning and other oddness, this code makes a statistical starting guess and
    # brutally iterates until it finds the right place.
    nChars = len(text)
    if nChars == 0:
        return 0
    textLength = icon.globalFont.getsize(text)[0]
    guessedPos = (nChars * pixelOffset) // textLength
    lastGuess = None
    lastGuessDist = textLength
    while True:
        pixelOfGuess = icon.globalFont.getsize(text[:guessedPos])[0]
        guessDist = abs(pixelOfGuess - pixelOffset)
        if pixelOfGuess > pixelOffset:
            if lastGuess == '<':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '>'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos -= 1
            if guessedPos <= 0:
                return 0 if pixelOffset < guessDist else lastGuessedPos
        elif pixelOfGuess < pixelOffset:
            if lastGuess == '>':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '<'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos += 1
            if guessedPos >= nChars:
                return nChars if textLength - pixelOffset < guessDist else lastGuessedPos
        else:
            return guessedPos

def binOpLeftArgSite(ic):
    return 'trueExpr' if ic.__class__ == opicons.IfExpIcon else 'leftArg'

def binOpRightArgSite(ic):
    return 'falseExpr' if ic.__class__ == opicons.IfExpIcon else 'rightArg'

def searchForOpenParen(token, ic, site):
    """Find an open paren/bracket/brace to match an end paren/bracket/brace placed at a
    given cursor position (ic, site).  token indicates what type of paren-like-object is
    to be closed.  In the case of an open paren, can also return a naked tuple that needs
    parentheses added."""
    # Note that this takes advantage of the fact that insertOpenParen places open parens/
    # brackets/braces at the highest level possible, so the matching icon will always be
    # a parent or owner of the site requested.
    while True:
        siteType = ic.typeOf(site)
        if siteType == 'input':
            if token == "endParen" and isinstance(ic, parenicon.CursorParenIcon) and \
                    not ic.closed:
                return ic
            if token == "endParen" and isinstance(ic, listicons.TupleIcon) and \
                    ic.noParens:
                # Found a no-paren (top-level) tuple to parenthesize
                return ic
            if token == "endParen" and isinstance(ic, listicons.CallIcon) and \
                    not ic.closed:
                return ic
            if token == "endBracket" and \
             ic.__class__ in (listicons.ListIcon, subscripticon.SubscriptIcon) and \
                    not ic.closed:
                return ic
            if token == "endBrace" and isinstance(ic, listicons.DictIcon) and \
                    not ic.closed:
                return ic
            if ic.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and ic.hasParens:
                # Don't allow search to escape enclosing arithmetic parens
                return None
            rightmostSite = ic.sites.lastCursorSite()
            if ic.typeOf(rightmostSite) != 'input':
                # Anything that doesn't have an input on the right (calls, tuples,
                # subscripts, etc.) can be assumed to be enclosing its children and
                # search should not extend beyond.
                return None
        parent = ic.parent()
        if parent is None:
            return None
        site = parent.siteOf(ic)
        ic = parent

def parseExprToAst(text):
    try:
        modAst = ast.parse(text, "Pasted text")
    except:
        return None
    if not isinstance(modAst, ast.Module):
        return None
    if len(modAst.body) != 1:
        return None
    if not isinstance(modAst.body[0], ast.Expr):
        return None
    return modAst.body[0].value
