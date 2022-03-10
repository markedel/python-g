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
import blockicons
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
        # can, but deletes them if it cannot
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
                    cursor.setToEntryIcon()
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
                reorderexpr.reorderArithExpr(attachedIcon)
            elif self.pendingAttr() and self.attachedSiteType() == "attrIn" and not \
                    attachedIcon.isCursorOnlySite(attachedSite):
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
                self.window.cursor.setToBestCoincidentSite(pendingArg, "output")
            elif self.pendingAttr():
                pendingAttr = self.pendingAttr()
                self.replaceChild(None, 'pendingAttr', 'attrOut')
                self.window.replaceTop(self, pendingAttr)
                pendingAttr.markLayoutDirty()
                self.window.cursor.setToIconSite(pendingAttr, "attrOut")
            else:
                prevIcon = self.prevInSeq()
                nextIcon = self.nextInSeq()
                if hasattr(self, 'blockEnd'):
                    self.window.removeIcons([self, self.blockEnd])
                else:
                    self.window.removeIcons([self])
                if prevIcon:
                    self.window.cursor.setToIconSite(prevIcon, 'seqOut')
                elif nextIcon and nextIcon is not self.blockEnd:
                    self.window.cursor.setToIconSite(nextIcon, 'seqIn')
                else:
                    self.window.cursor.setToWindowPos(self.rect[:2])
        self.window.entryIcon = None
        return True

    def _setText(self, newText, newCursorPos):
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
            if not self.insertComma():
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
            if not self.insertEndParen(parseResult):
                cursors.beep()
            return
        elif parseResult == "openBrace":
            self.insertOpenParen(listicons.DictIcon)
            return
        elif parseResult == "endBrace":
            if not self.insertEndParen(parseResult):
                cursors.beep()
            return
        elif parseResult == "openParen":
            self.insertOpenParen(parenicon.CursorParenIcon)
            return
        elif parseResult == "endParen":
            if not self.insertEndParen(parseResult):
                cursors.beep()
            return
        elif parseResult == "makeFunction":
            if self.attachedIcon().isCursorOnlySite(self.attachedSite()):
                cursors.beep()
                return
            self.insertOpenParen(listicons.CallIcon)
            return
        elif parseResult == "makeSubscript":
            self.insertOpenParen(subscripticon.SubscriptIcon)
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
        # If the inserted icon had typeover parts, placing pending arguments usually
        # separates the cursor from them.  Negate if necessary
        self.window.updateTypeoverStates()
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

    def insertComma(self):
        """A comma has been entered.  Search up the hierarchy to find a list, tuple,
        cursor-paren, or parameter list, parting every expression about the newly inserted
        comma.  If no comma-separated type is found, part the expression up to either an
        assignment, or the top level.  Return False if user tries to place comma within
        unary or binary op auto-parens, or on an icon that interrupts horizontal sequence
        of icons (divide)."""
        if self.attachedIcon() is None:
            # The entry icon is on the top level.  Reject, so as not to create a naked
            # tuple containing just a comma, which is more confusing than useful
            return False
        # Look for comma typeover opportunity
        typeoverIc = _findParenTypeover(self, "comma")
        if typeoverIc is not None:
            self.remove()  # Safe, since args would have invalidated typeover
            _siteBefore, siteAfter, _text, _idx = typeoverIc.typeoverSites()
            self.window.cursor.setToIconSite(typeoverIc, siteAfter)
            return True
        # Find the top of the expression to which the entry icon is attached
        ic, splitSite = _findEnclosingSite(self)
        if ic is None:
            # There's no enclosing site, add a naked tuple
            ic = listicons.TupleIcon(window=self.window, noParens=True)
            splitSite = 'argIcons_0'
            top = self.topLevelParent()
            self.window.replaceTop(top, ic)
            ic.replaceChild(top, 'argIcons_0')
        if not iconsites.isSeriesSiteId(splitSite):
            # The bounding icon is not a sequence and will not accept a comma.  If it's
            # something with parens, turn it in to a tuple.  Otherwise reject
            if ic.__class__ is parenicon.CursorParenIcon:
                # Convert cursor paren to a tuple
                closed = ic.closed or _canCloseParen(self)
                tupleIcon = listicons.TupleIcon(window=self.window, closed=closed,
                    typeover=closed and not ic.closed)
                arg = ic.childAt('argIcon')
                ic.replaceChild(None, 'argIcon')
                parent = ic.parent()
                if parent is None:
                    self.window.replaceTop(ic, tupleIcon)
                else:
                    parent.replaceChild(tupleIcon, parent.siteOf(ic))
                tupleIcon.replaceChild(arg, 'argIcons_0')
                if ic.closed:
                    attrIcon = ic.sites.attrIcon.att
                    ic.replaceChild(None, 'attrIcon')
                    tupleIcon.replaceChild(attrIcon, 'attrIcon')
                ic = tupleIcon
                splitSite = 'argIcons_0'
            elif ic.__class__ is opicons.BinOpIcon and ic.hasParens or \
                    ic.__class__ is opicons.IfExpIcon and ic.hasParens and \
                        splitSite != 'testExpr':
                # Convert  binary operator with parens to a tuple
                tupleIcon = listicons.TupleIcon(window=self.window, closed=True)
                parent = ic.parent()
                if parent is None:
                    self.window.replaceTop(ic, tupleIcon)
                else:
                    parent.replaceChild(tupleIcon, parent.siteOf(ic))
                tupleIcon.replaceChild(ic, 'argIcons_0')
                attrIcon = ic.sites.attrIcon.att
                ic.replaceChild(None, 'attrIcon')
                tupleIcon.replaceChild(attrIcon, 'attrIcon')
                ic.hasParens = False
                ic = tupleIcon
                splitSite = 'argIcons_0'
            else:
                # Bounding icon will not accept comma: reject
                return False
        # ic can accept a new comma clause after splitSite.  Split expression in two at
        # entry icon
        left, right = _splitExprAtEntryIcon(self, ic)
        if left is None and right is None:
            # Deadly failure probably dropped content (diagnostics already printed)
            return False
        # Place the newly-split expression in to the series, creating a new clause
        ic.replaceChild(None, splitSite)
        splitSiteSeriesName, splitSiteIdx = iconsites.splitSeriesSiteId(splitSite)
        ic.insertChildren((left, right), splitSiteSeriesName, splitSiteIdx)
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return True

    def insertOpenParen(self, iconClass):
        """Called when the user types an open paren, bracket, or brace to insert an icon
        of type given in iconClass.  Inserting an open paren/bracket/brace has the power
        to completely rearrange the icon hierarchy.  For a consistent user-interface, we
        maintain un-closed parens at the highest level of the hierarchy that they can
        influence (clicking and dragging behavior is dependent on the hierarchy, even if
        code appearance is identical).  It is easier to maintain parens at the highest
        level than the lowest, since the paren itself makes this happen automatically,
        and they can be found by just looking up from a prospective end position.
        Likewise, if the parent is a sequence with clauses to the right of the entry
        icon, pull these down to the level of the new open paren.  Absent closing parens,
        the syntax is ambiguous as to who owns subsequent clauses, but typographically
        they belong to the innermost, so that's how we order the tree.  Consistent order
        is important to make the interface behave predictably."""
        pendingArg = self.pendingArg()
        if self.parent() is None and isinstance(pendingArg, listicons.TupleIcon) and \
                pendingArg.noParens:
            # Pending arg is a naked tuple: deal with it explicitly, rather than leaving
            # it to get parens automatically (which would then get another, unwanted, set)
            self.setPendingArg(None)
            if iconClass is parenicon.CursorParenIcon:
                iconClass = listicons.TupleIcon
            newList = iconClass(window=self.window, closed=False)
            for i, arg in enumerate(list(pendingArg.argIcons())):
                pendingArg.replaceChild(None, 'argIcons_0')
                newList.insertChild(arg, "argIcons", i)
            self.window.replaceTop(self, newList)
            self.window.entryIcon = None
            self.window.cursor.setToIconSite(newList, 'argIcons_0')
            return
        # Determine if a parent has sequence clauses to the right of the entry icon that
        # will need entries transferred to the new paren icon.  It may also be necessary
        # to change the the generated icon from parens to tuple.
        attachedIc = self.attachedIcon()
        attachedSite = self.attachedSite()
        transferParentArgs = None
        if attachedIc is not None and iconClass is not subscripticon.SubscriptIcon:
            seqIc, seqSite = _findEnclosingSite(self)
            if seqIc and iconsites.isSeriesSiteId(seqSite):
                siteName, siteIdx = iconsites.splitSeriesSiteId(seqSite)
                rightOfSite = iconsites.makeSeriesSiteId(siteName, siteIdx + 1)
                if seqIc.hasSite(rightOfSite):
                    transferParentArgs = seqIc, rightOfSite
                    if iconClass is parenicon.CursorParenIcon:
                        iconClass = listicons.TupleIcon
        # Create an icon of the requested class and move the entry icon inside of it
        if iconClass is parenicon.CursorParenIcon:
            closed = False  # We leave even empty paren open to detect () for empty tuple
        else:
            closed = transferParentArgs is None and _canCloseParen(self)
        newParenIcon = iconClass(window=self.window, closed=closed, typeover=closed)
        if attachedIc is None:
            self.window.replaceTop(self, newParenIcon)
        else:
            attachedIc.replaceChild(newParenIcon, attachedSite)
        if iconClass is parenicon.CursorParenIcon:
            inputSite = 'argIcon'
        elif iconClass is subscripticon.SubscriptIcon:
            inputSite = 'indexIcon'
        else:
            inputSite = 'argIcons_0'
        newParenIcon.replaceChild(self, inputSite)
        # Attempt to get rid of the entry icon and place pending arg in its place
        self.remove()
        # Reorder the expression with the new open paren in place (skip some work if the
        # entry icon was at the top level, since no reordering is necessary, there)
        if attachedIc is not None:
            reorderexpr.reorderArithExpr(newParenIcon)
        # Transfer sequence clauses after the new open paren/bracket/brace to it
        if transferParentArgs:
            rightOfIc, rightOfSite = transferParentArgs
            name, idx = iconsites.splitSeriesSiteId(rightOfSite)
            numParentSites = len(getattr(rightOfIc.sites, name))
            args = [rightOfIc.childAt(name, i) for i in range(idx, numParentSites)]
            for i in range(idx, numParentSites):
                rightOfIc.replaceChild(None, iconsites.makeSeriesSiteId(name, idx))
            insertIdx = len(newParenIcon.sites.argIcons)
            newParenIcon.insertChildren(args, 'argIcons', insertIdx)
            # If the parent was a naked tuple, which is now down to 1 arg, remove it
            if rightOfIc.parent() is None and idx == 1 and \
                    isinstance(rightOfIc, listicons.TupleIcon) and rightOfIc.noParens:
                newTopIcon = rightOfIc.childAt('argIcons_0')
                rightOfIc.replaceChild(None, 'argIcons_0')
                self.window.replaceTop(rightOfIc, newTopIcon)

    def insertEndParen(self, token):
        """Find a matching open paren/bracket/brace or paren-less tuple that could be
        closed by an end paren/bracket/brace (which type is specified by token) typed at
        the attached icon/site.  If a matching unclosed item is found, relocate it to the
        appropriate level, close it, and rearrange the icon hierarchy such that the
        expressions and attribute attachments match what has been typed.  Rearrangement
        may be significant.  Excluded sequence clauses are also relocated to a parent
        icon, following the rules for canonical arrangement of sequence items."""
        fromIcon = self.attachedIcon()
        fromSite = self.attachedSite()
        # Check for special case of the entry icon directly on the input site of a cursor
        # paren icon to be closed (empty tuple): convert it to one
        if isinstance(fromIcon, parenicon.CursorParenIcon) and token == "endParen" and (
                fromSite == 'argIcon' or
                fromSite == 'attrIcon' and fromIcon.childAt('argIcon') is None):
            parent = fromIcon.parent()
            tupleIcon = listicons.TupleIcon(window=self.window)
            if parent is None:
                self.window.replaceTop(fromIcon, tupleIcon)
                tupleIcon.markLayoutDirty()
            else:
                parent.replaceChild(tupleIcon, parent.siteOf(fromIcon))
            # If there are pending args or attributes, they need to go *after* the newly-
            # closed paren, so we can't just use .remove() to place them
            fromIcon.replaceChild(None, fromSite)
            if self.pendingArg():
                # Have to keep the entry icon, but move it to after the end paren
                tupleIcon.replaceChild(self, 'attrIcon')
            else:
                # Can safely remove entry icon (placing pending attribute on paren)
                if self.pendingAttr():
                    tupleIcon.replaceChild(self.pendingAttr(), 'attrIcon')
                    self.setPendingAttr(None)
                self.window.entryIcon = None
                self.window.cursor.setToIconSite(tupleIcon, 'attrIcon')
            self.window.updateTypeoverStates()
            return True
        matchingParen = searchForOpenParen(token, self)
        if matchingParen is None:
            # No matching paren was found.  Remove cursor and look for typeover
            typeoverIc = _findParenTypeover(self, token)
            if typeoverIc is None:
                return False
            self.remove()  # Safe, since args would have invalidated typeover
            self.window.cursor.setToIconSite(typeoverIc, 'attrIcon')
            return True
        if not isinstance(matchingParen, parenicon.CursorParenIcon):
            # If the icon that matches might have arguments beyond the end paren/bracket/
            # brace, check whether it does.  If so, transfer them upward to the next icon
            # above in the hierarchy that can accept them, possibly creating a naked
            # tuple if no parents were sequence sites.  If this fails (and it usually
            # won't because most of the cases were already screened out), return None.
            if matchingParen is fromIcon:
                siteOfMatch = fromSite
            else:
                siteOfMatch = matchingParen.siteOf(fromIcon, recursive=True)
            name, idx = iconsites.splitSeriesSiteId(siteOfMatch)
            if name == "argIcons" and idx < len(matchingParen.sites.argIcons) - 1:
                if not _transferToParentList(matchingParen, idx+1):
                    return False
                if isinstance(matchingParen, listicons.TupleIcon) and idx == 0:
                    # Tuple is down to 1 argument.  Convert to arithmetic parens
                    arg = matchingParen.childAt("argIcons_0")
                    matchingParen.replaceChild(None, 'argIcons_0')
                    newParen = parenicon.CursorParenIcon(window=self.window, closed=False)
                    newParen.replaceChild(arg, 'argIcon')
                    parent = matchingParen.parent()
                    if parent is None:
                        self.window.replaceTop(matchingParen, newParen)
                    else:
                        parent.replaceChild(newParen, parent.siteOf(matchingParen))
                    matchingParen = newParen
        # Rearrange the hierarchy so the paren/bracket/brace is above all the icons it
        # should enclose and outside of those it does not enclose.  reorderArithExpr
        # closes the parens if it succeeds.
        reorderexpr.reorderArithExpr(matchingParen, closeParenAt=self)
        # If there are pending args or attributes, they need to go *after* the newly-
        # closed paren, so we can't just use .remove() to place them
        cursorPos = self.attachedIcon(), self.attachedSite()
        self.attachedIcon().replaceChild(None, self.attachedSite())
        if self.pendingArg():
            # Have to keep the entry icon, but move it to after the end paren
            matchingParen.replaceChild(self, 'attrIcon')
        else:
            # Can safely remove entry icon (possibly placing pending attribute on paren)
            if self.pendingAttr():
                matchingParen.replaceChild(self.pendingAttr(), 'attrIcon')
                self.setPendingAttr(None)
            self.window.entryIcon = None
            self.window.cursor.setToIconSite(*cursorPos)
        self.window.updateTypeoverStates()
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
        if self.attachedIcon() is None:
            # Not allowed to type colon at the top level: Reject
            return False
        # Find the top of the expression to which the entry icon is attached
        ic, splitSite = _findEnclosingSite(self)
        if isinstance(ic, listicons.DictIcon):
            return self.insertDictColon(ic)
        if isinstance(ic, subscripticon.SubscriptIcon):
            return self.insertSubscriptColon(ic)
        return False

    def insertDictColon(self, onIcon):
        onSite = onIcon.siteOf(self, recursive=True)
        child = onIcon.childAt(onSite)
        if isinstance(child, listicons.DictElemIcon):
            # There's already a colon in this clause.  We allow a colon to be
            # typed on the left of an existing clause, since that is how one
            # naturally types a new clause (when they begin after the comma or to
            # the left of the first clause).  Typing a colon on the right side of
            # a dictElem is not expected without a comma, and not allowed.
            dictElemSite = child.siteOf(self, recursive=True)
            if dictElemSite != 'leftArg':
                return False
            # Split across entry icon, insert both a colon and a comma w/typeover
            left, right = _splitExprAtEntryIcon(self, child)
            if left is None and right is None:
                return False
            newDictElem = listicons.DictElemIcon(window=self.window)
            newDictElem.replaceChild(left, 'leftArg')
            onIcon.replaceChild(newDictElem, onSite, leavePlace=True)
            nextSite = iconsites.nextSeriesSiteId(onSite)
            onIcon.insertChild(child, nextSite)
            child.replaceChild(right, 'leftArg')
            # Remove entry icon, placing pending args on the right side of the new comma
            # but cursor before the comma... Checking for pending args needs to happen
            # earlier while we can still bail
            if self.remove():
                self.window.cursor.setToIconSite(newDictElem, 'rightArg')
            onIcon.setTypeover(0, nextSite)
            self.window.watchTypeover(onIcon)
        elif isinstance(self.pendingArg(), listicons.DictElemIcon):
            # We are holding a dictElem as a pending arg: add a new clause and deposit
            # the pending arg in to it.  Note that since DictElemIcons can only appear
            # on the top level of a dictionary icon, we assume that the entry icon's
            # parent expression does not extend to the right of the pending arg
            nextSite = iconsites.nextSeriesSiteId(onSite)
            onIcon.insertChild(self.pendingArg(), nextSite)
            self.setPendingArg(None)
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(child, 'leftArg')
            self.remove()
            self.window.cursor.setToIconSite(newDictElem, 'rightArg')
            onIcon.setTypeover(0, nextSite)
            self.window.watchTypeover(onIcon)
        elif child is self:
            # There's nothing at the site except entry icon and whatever we are holding.
            # Place a new DictElemIcon, move entry icon to right arg, try to place
            # pending args and remove
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(self, 'rightArg')
            self.remove()
        else:
            # There's something at the site.  Put a colon in it
            left, right = _splitExprAtEntryIcon(self, onIcon)
            if left is None and right is None:
                return False
            newDictElem = listicons.DictElemIcon(window=self.window)
            onIcon.replaceChild(newDictElem, onSite)
            newDictElem.replaceChild(left, 'leftArg')
            newDictElem.replaceChild(right, 'rightArg')
            self.remove()
        return True

    def insertSubscriptColon(self, onIcon):
        if onIcon.hasSite('stepIcon'):
            return False   # Subscript already has all 3 colons
        onSite = onIcon.siteOf(self, recursive=True)
        # Split the expression holding the entry icon in two at the entry icon
        left, right = _splitExprAtEntryIcon(self, onIcon)
        if left is None and right is None:
            # Deadly failure probably dropped content (diagnostics already printed)
            return False
        # Create a new clause and put the two halves in to them
        if onIcon.hasSite('upperIcon'):
            onIcon.changeNumSubscripts(3)
            siteAdded = 'stepIcon'
        else:
            onIcon.changeNumSubscripts(2)
            siteAdded = 'upperIcon'
        # If the cursor was on the first site, may need to shift second-site icons
        if onSite == 'indexIcon' and siteAdded == "stepIcon":
            toShift = onIcon.childAt('upperIcon')
            onIcon.replaceChild(None, "upperIcon")
            onIcon.replaceChild(toShift, 'stepIcon')
            nextSite = 'upperIcon'
        else:
            nextSite = siteAdded
        # Place the newly-split expression in to its assigned slots
        onIcon.replaceChild(left, onSite)
        onIcon.replaceChild(right, nextSite)
        # Remove entry icon and place pending arguments (if possible)
        self.remove()
        return True

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

def searchForOpenParen(token, closeParenAt):
    """Find an open paren/bracket/brace to match an end paren/bracket/brace placed at a
    given cursor position (fromIc, fromSite).  token indicates what type of paren-like
    object is to be closed."""
    # Search first for a proper match.  This takes advantage of the fact that
    # insertOpenParen places open parens/brackets/braces at the highest level possible,
    # and shifts list elements down to the level of the innermost unclosed list, so the
    # matching icon will always be a parent or owner of the site requested.
    ic = closeParenAt
    while True:
        parent = ic.parent()
        if parent is None:
            break
        site = parent.siteOf(ic)
        ic = parent
        siteType = ic.typeOf(site)
        if siteType == 'input':
            if token == "endParen" and isinstance(ic, parenicon.CursorParenIcon) and \
                    not ic.closed:
                return ic
            if token == "endParen" and isinstance(ic, listicons.TupleIcon) and (
                    not ic.closed or ic.noParens):
                # Found either an unclosed tuple or a naked tuple
                return ic
            if token == "endParen" and isinstance(ic, listicons.CallIcon) and \
                    not ic.closed:
                return ic
            if token == "endBracket" and isinstance(ic, listicons.ListIcon) and \
                    not ic.closed:
                return ic
            if token == "endBracket" and isinstance(ic, subscripticon.SubscriptIcon) and \
                    not ic.closed:
                # Can only match from the rightmost slice, otherwise there are colons to
                # the right which can't be left on their own
                sliceSite = ic.siteOf(closeParenAt, recursive=True)
                if sliceSite is None:
                    sliceSite = site
                if ic.hasSite('stepIcon') and sliceSite != 'stepIcon' or \
                        ic.hasSite('upperIcon') and sliceSite == 'indexIcon':
                    break
                return ic
            if token == "endBrace" and isinstance(ic, listicons.DictIcon) and \
                    not ic.closed:
                return ic
            if ic.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and ic.hasParens:
                # Don't allow search to escape enclosing arithmetic parens
                break
            rightmostSite = ic.sites.lastCursorSite()
            if ic.typeOf(rightmostSite) not in ('input', 'cprhIn') or \
                    hasattr(ic, 'closed') or \
                    isinstance(ic, opicons.IfExpIcon) and site == 'testExpr':
                # Anything that doesn't have an input on the right or could be closed can
                # be assumed to enclose its children and search should not extend beyond.
                # Inline if is the exception in having a middle site that encloses its
                # child icon
                break
    # No matching paren/bracket/brace found at the level of closeParenAt
    if token != 'endParen':
        # Braces and brackets require a match at the correct level
        return None
    # Arithmetic parens do not require a properly-nested match.  reorderArithExpr can
    # shift parens around even if there is not a match on the appropriate level, in
    # which case, what we need is an unclosed paren left of the end paren, and the
    # end paren not to be on the other side of code that can trap it
    matchingParen = None
    for op in reorderexpr.traverseExprLeftToRight(
            reorderexpr.highestAffectedExpr(closeParenAt), closeParenAfter=closeParenAt):
        if isinstance(op, reorderexpr.CloseParenToken) and op.parenIcon is None:
            # A CloseParenToken with parenIcon of None is the inserted end paren
            break
        if isinstance(op, reorderexpr.OpenParenToken) and isinstance(op.parenIcon,
         parenicon.CursorParenIcon) and not op.parenIcon.closed:
            matchingParen = op.parenIcon
    else:
        print('searchForOpenParen internal error: failed to find close-paren site')
    return matchingParen

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

def reopenParen(ic):
    """Remove the end paren/bracket/brace from ic and deal with all the consequences to
    the surrounding icons.  Consequences include arithmetic reordering around the icon
    itself and its newly-exposed right element, and pulling-in clauses from parent
    sequences that should now belong to ic per our unclosed-list ownership rules."""
    # If there is an attribute attached to the parens, transfer to rightmost site of
    # last element (if possible).  If not, put an entry icon between.  Also sets cursor
    # position appropriately for where the end paren/bracket/brace was.
    if isinstance(ic, parenicon.CursorParenIcon):
        lastArgSite = 'argIcon'
    elif isinstance(ic, subscripticon.SubscriptIcon):
        if ic.hasSite('stepIcon'):
            lastArgSite = 'stepIcon'
        elif ic.hasSite('upperIcon'):
            lastArgSite = 'upperIcon'
        else:
            lastArgSite = 'indexIcon'
    else:
        lastArgSite = ic.sites.argIcons[-1].name
    lastArg = ic.childAt(lastArgSite)
    attrIcon = ic.childAt('attrIcon')
    if attrIcon:
        ic.replaceChild(None, 'attrIcon')
        if lastArg is None:
            # Empty site gets attribute: create an entry icon with pending attribute
            ic.window.entryIcon = EntryIcon(window=ic.window)
            ic.window.entryIcon.setPendingAttr(attrIcon)
            ic.replaceChild(ic.window.entryIcon, lastArgSite)
            ic.window.cursor.setToEntryIcon()
        else :
            rightmostIc, rightmostSite = icon.rightmostSite(lastArg)
            if rightmostSite != 'attrIcon' or rightmostIc.isCursorOnlySite(rightmostSite):
                # Can't place attribute: create an entry icon to stitch attribute on
                ic.window.entryIcon = EntryIcon(window=ic.window)
                ic.window.entryIcon.setPendingAttr(attrIcon)
                rightmostIc.replaceChild(ic.window.entryIcon, rightmostSite)
                ic.window.cursor.setToEntryIcon()
            else:
                # attrIcon can be safely attached to the last argument
                rightmostIc.replaceChild(attrIcon, rightmostSite)
                ic.window.cursor.setToIconSite(rightmostIc, rightmostSite)
    else:
        ic.window.cursor.setToIconSite(*icon.rightmostFromSite(ic, lastArgSite))
    # Remove the end paren/bracket/brace and reorder.  reorderArithExpr treats everything
    # but operators and cursor parens as bounding (will neither go outside of those above
    # the requested icon in the hierarchy, nor descend in to those below it).  However,
    # when specifically given such an icon to reorder, it treats it (and its attribute
    # chain in the case of a subscript or call) as a special sort of paren, whose last
    # clause will be treated as exposed if the icon's "closed" field is False
    ic.reopen()
    reorderexpr.reorderArithExpr(ic)
    # Determine if the bounding icon has sequence clauses to the right of ic that now
    # need to be transferred to the newly-reopened icon.  It may also be necessary to
    # change the icon from parens to tuple to accomodate the transferred clauses.
    boundingParent, boundingParentSite = _findEnclosingSite(ic)
    if boundingParent is None or not iconsites.isSeriesSiteId(boundingParentSite):
        # There was no bounding icon or the bounding icon was not a sequence
        return
    siteName, siteIdx = iconsites.splitSeriesSiteId(boundingParentSite)
    nextSite = iconsites.makeSeriesSiteId(siteName, siteIdx + 1)
    if not boundingParent.hasSite(nextSite):
        # The bounding icon has no clauses(s) beyond ic to transfer
        return
    # At this point we know boundingParent has arguments we need to transfer to ic
    if isinstance(ic, subscripticon.SubscriptIcon):
        # If ic is a subscript, we can't transfer args, which leaves an open bracket with
        # clauses following that belong to a parent.  This is weird, but necessary so
        # users can adjust the right paren of a subscript that happens to be in a list.
        return
    # If ic is a cursor paren, change it to tuple to accept more arguments
    if isinstance(ic, parenicon.CursorParenIcon):
        tupleIcon = listicons.TupleIcon(window=ic.window, closed=False)
        arg = ic.childAt('argIcon')
        ic.replaceChild(None, 'argIcon')
        tupleIcon.replaceChild(arg, "argIcons_0")
        parent = ic.parent()
        if parent is None:
            ic.window.replaceTop(ic, tupleIcon)
        else:
            parent.replaceChild(tupleIcon, parent.siteOf(ic))
        ic = tupleIcon
    # Transfer sequence clauses after the newly-opened paren/bracket/brace
    # from boundingParent after the current last element
    name, idx = iconsites.splitSeriesSiteId(nextSite)
    numParentSites = len(getattr(boundingParent.sites, name))
    args = [boundingParent.childAt(name, i) for i in range(idx, numParentSites)]
    for i in range(idx, numParentSites):
        boundingParent.replaceChild(None, iconsites.makeSeriesSiteId(name, idx))
    insertIdx = len(ic.sites.argIcons)
    ic.insertChildren(args, 'argIcons', insertIdx)
    # If boundingParent was a naked tuple, which is now down to 1 arg, remove it
    if boundingParent.parent() is None and idx == 1 and \
            isinstance(boundingParent, listicons.TupleIcon) and boundingParent.noParens:
        newTopIcon = boundingParent.childAt('argIcons_0')
        boundingParent.replaceChild(None, 'argIcons_0')
        ic.window.replaceTop(boundingParent, newTopIcon)

def _transferToParentList(listIc, startIdx):
    """Find a suitable parent to receive remaining arguments from a list whose end paren
    is being closed, and transfer arguments beyond startIdx to that icon.  If there is
    not a suitable icon because an enclosing parent does not take a sequence (such as the
    testIcon site of an inline-if, or an if or while statement), returns False."""
    numListArgs = len(listIc.sites.argIcons)
    if numListArgs < startIdx:
        # There are no arguments to transfer
        return True
    recipient, site = _findEnclosingSite(listIc)
    if recipient is None:
        # We reached the top of the hierarchy without getting trapped.  Add a naked tuple
        # as parent to which to transfer the arguments
        recipient = listicons.TupleIcon(window=listIc.window, noParens=True)
        topIc = listIc.topLevelParent()
        listIc.window.replaceTop(topIc, recipient)
        recipient.replaceChild(topIc, 'argIcons_0')
        siteName = 'argIcons'
        siteIdx = 1
    elif iconsites.isSeriesSiteId(site):
        # Found a suitable site
        siteName, siteIdx = iconsites.splitSeriesSiteId(site)
        siteIdx += 1
    else:
        # There are arguments to transfer, but no place to put them
        return False
    # Transfer the arguments beyond startIdx
    args = [listIc.childAt('argIcons', i) for i in range(startIdx, numListArgs)]
    for i in range(startIdx, numListArgs):
        listIc.replaceChild(None, iconsites.makeSeriesSiteId('argIcons', startIdx))
    recipient.insertChildren(args, siteName, siteIdx)
    return True

def _findEnclosingSite(startIc):
    """Search upward in the hierarchy above startIc to find a parent that bounds the
    scope of expression-processing, such as a sequence (expressions can't cross commas)
    or parens.  If found, return the icon and site at which startIc is (indirectly)
    attached.  If the search reaches the top, return None for the icon."""
    # This is very similar to reorderexpr.highestAffectedExpr and might be worth unifying
    # with it, but note that this stops at arithmetic parens where that continues upward.
    for ic in startIc.parentage(includeSelf=True):
        parent = ic.parent()
        if parent is None:
            return None, None
        site = parent.siteOf(ic)
        if site == 'attrIcon':
            continue
        # The largest class of icons that bound expressions are sequences.  As a
        # shortcut, just look for a series site
        if iconsites.isSeriesSiteId(site):
            return parent, site
        # ic is not on a series site.  Look for the remaining types that enclose their
        # arguments but are not series: cursor-parens, auto-parens of BinOp icons,
        # statements that take single arguments, and the center site of an inline-if.
        parentClass = parent.__class__
        if parentClass in (opicons.BinOpIcon, opicons.IfExpIcon) and parent.hasParens or \
                parentClass in (opicons.DivideIcon, parenicon.CursorParenIcon,
                    subscripticon.SubscriptIcon) or \
                parentClass is opicons.IfExpIcon and site == 'textExpr' or \
                parentClass in cursors.topLevelStmts:
            return parent, site

def _findParenTypeover(entryIc, token):
    """If there is an icon with active typeover matching token ("endBracket", "endBrace",
    "endParen", or "comma") directly to the right of the entry icon, return it. Note that
    pending args and attributes invalidate typeover, so if entryIc has them, there can't
    be active typeover.  If there's no active typeover to process, return None."""
    if entryIc.pendingArg() or entryIc.pendingAttr():
        return None
    # March up the hierarchy from the entry icon, looking for a matching paren icon
    # with active typeover
    for ic in entryIc.parentage(includeSelf=False):
        rightmostIcon, rightmostSite = icon.rightmostSite(ic)
        if rightmostIcon == entryIc:
            continue
        if isinstance(rightmostIcon, opicons.DivideIcon):
            # Divide icon has *two* sites considered next-to adjacent typeover
            # (due to how it's typed): attribute (handled above) and bottomArg
            divisor = rightmostIcon.childAt('bottomArg')
            if divisor is None and rightmostIcon is entryIc or divisor is not None and \
                    icon.rightmostSite(divisor)[0] == entryIc:
                continue
        if token == "endBracket" and ic.__class__ in (listicons.ListIcon,
                    subscripticon.SubscriptIcon) or \
                token == "endParen" and ic.__class__ in (listicons.TupleIcon,
                    listicons.CallIcon) or \
                token == "endBrace" and ic.__class__ is listicons.DictIcon:
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.endParenTypeover:
                return ic
        if token == "endParen" and ic.__class__ in (blockicons.DefIcon,
                    blockicons.ClassDefIcon):
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.rParenTypeover:
                return ic
        if token == "comma" and ic.__class__ in (listicons.TupleIcon, listicons.DictIcon):
            siteBefore, siteAfter, _text, _idx  = ic.typeoverSites()
            if ic.siteOf(entryIc, recursive=True) == siteBefore and ic.commaTypeover:
                return ic
    return None

def _splitExprAtEntryIcon(entryIc, splitTo):
    """Split a (paren-less) arithmetic expression in two parts at entryIc, up to splitTo.
    Note that this expects that splitTo has already been vetted as holding the root of
    the expression (probably by _findEnclosingSite), and will fail badly if splitTo does
    not."""
    if entryIc.parent() is None:
        return None, entryIc
    leftArg = None
    rightArg = entryIc
    child = entryIc
    for parent in list(entryIc.parentage(includeSelf=False)):
        childSite = parent.siteOf(child)
        childSiteType = parent.typeOf(childSite)
        if parent is splitTo:
            break
        if isinstance(parent, opicons.UnaryOpIcon):
            leftArg = parent
        elif childSiteType == 'input' and (isinstance(parent, infixicon.InfixIcon) or
                parent.__class__ in (opicons.BinOpIcon, opicons.IfExpIcon) and not
                parent.hasParens):
            # Parent is a binary op icon without parens, and site is one of the two
            # input sites
            if parent.leftArg() is child:  # Insertion was on left side of operator
                parent.replaceChild(rightArg, binOpLeftArgSite(parent))
                rightArg = parent
            elif parent.rightArg() is child:  # Insertion on right side of operator
                parent.replaceChild(leftArg, binOpRightArgSite(parent))
                leftArg = parent
            else:
                print('Unexpected site attachment in "_splitExprAtEntryIcon" function')
                return None, None
        elif childSiteType == 'attrIn':
            leftArg = parent
        else:
            # Parent was not an arithmetic operator or had parens
            print('Bounding expression found in "_splitExprAtEntryIcon" function')
            return None, None
        if child is entryIc and child.attachedSite() == 'attrIcon':
            parent.replaceChild(None, childSite)
        child = parent
    else:
        print('"_splitExprAtEntryIcon" function reached top without finding splitTo')
        return None, None
    return leftArg, rightArg

def _canCloseParen(entryIc):
    """Determine if it is safe to close a newly-entered open-paren/bracket/brace.  Also
    used when close of an open cursor-paren has been deferred until we know what sort of
    paren it is."""
    if entryIc.pendingArg():
        return False
    if entryIc.attachedIcon() is not None:
        seqIc, seqSite = _findEnclosingSite(entryIc)
        if seqIc:
            rightmostIc, rightmostSite = icon.rightmostFromSite(seqIc, seqSite)
            if rightmostIc is not entryIc and \
                    entryIc.siteOf(rightmostIc, recursive=True) is None:
                return False
    return True