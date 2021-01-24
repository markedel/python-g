# Copyright Mark Edel  All rights reserved
import icon
import compile_eval
import python_g
import winsound
import ast
from PIL import Image, ImageDraw
import re
import numbers
from operator import itemgetter

PEN_BG_COLOR = (255, 245, 245, 255)
PEN_OUTLINE_COLOR = (255, 97, 120, 255)

# Gap to be left between the entry icon and next icons to the right of it
ENTRY_ICON_GAP = 3

PEN_MARGIN = 6

# How far to move the cursor per arrow keystroke on the window background
WINDOW_CURSOR_INCREMENT = 20

# How far away from the edges of the window to keep the window background cursor
WINDOW_CURSOR_MARGIN = 5

# Max allowable cursor y movement for left and right arrow movement over icons
HORIZ_ARROW_Y_JUMP_MAX = 12

# Minimum threshold (pixels) for cursor movement via arrow keys (to prevent minor
# alignment issues from dominating the destination site choice
VERT_ARROW_Y_JUMP_MIN = 5
VERT_ARROW_X_JUMP_MIN = 1

# Limits (pixels) for cursor movement via arrow key
VERT_ARROW_MAX_DIST = 400
HORIZ_ARROW_MAX_DIST = 600

# Weight of x distance in y cursor movement
VERT_ARROW_X_WEIGHT = 2

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

topLevelStmts = {'async def':icon.DefIcon, 'def':icon.DefIcon, 'class':icon.ClassDefIcon,
 'break':icon.BreakIcon, 'return':icon.ReturnIcon, 'continue':icon.ContinueIcon,
 'yield':icon.YieldIcon, 'del':icon.DelIcon, 'elif':icon.ElifIcon, 'else':icon.ElseIcon,
 'except':icon.ExceptIcon, 'finally':icon.FinallyIcon, 'async for':icon.ForIcon,
 'for':icon.ForIcon, 'from':icon.FromIcon, 'global':icon.GlobalIcon, 'if':icon.IfIcon,
 'import':icon.ImportIcon, 'nonlocal':icon.NonlocalIcon, 'pass':icon.PassIcon,
 'raise':icon.RaiseIcon, 'try':icon.TryIcon, 'async while':icon.WhileIcon,
 'while':icon.WhileIcon, 'async with':icon.WithIcon, 'with':icon.WithIcon}

identPattern = re.compile('^[a-zA-z_][a-zA-Z_\\d]*$')
numPattern = re.compile('^([\\d_]*\\.?[\\d_]*)|'
 '(((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*)?$')
attrPattern = re.compile('^\\.[a-zA-z_][a-zA-Z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-z\\d_.\\(\\[\\{\\s+-~]')

inputSiteCursorPixmap = (
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    ".% .",
    "% ..",
    ".% .",
    "..% ",
    "..% ",
    "..% ",
    "..% ",
    "..% ",
)
inputSiteCursorOffset = 6
inputSiteCursorImage = icon.asciiToImage(inputSiteCursorPixmap)

attrSiteCursorPixmap = (
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    ".%",
    "%.",
    "%.",
    ".%",
    ".%",
)
attrSiteCursorOffset = 11
attrSiteCursorImage = icon.asciiToImage(attrSiteCursorPixmap)

seqInSiteCursorPixmap = (
    "   .   ",
    "%%% %%%",
    "...%...",
)
seqInSiteCursorXOffset = 3
seqInSiteCursorYOffset = 3
seqInSiteCursorImage = icon.asciiToImage(seqInSiteCursorPixmap)

seqOutSiteCursorPixmap = (
    "   %   ",
    "%%%.%%%",
    ".......",
)
seqOutSiteCursorXOffset = 3
seqOutSiteCursorYOffset = 0
seqOutSiteCursorImage = icon.asciiToImage(seqOutSiteCursorPixmap)

textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

penPixmap = (
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
    "....oooo    "
)
penImage = icon.asciiToImage(penPixmap)

attrPenPixmap = (
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
)
attrPenImage = icon.asciiToImage(attrPenPixmap)

class EntryIcon(icon.Icon):
    def __init__(self, attachedIcon, attachedSite, initialString="", window=None,
     location=None):
        icon.Icon.__init__(self, window)
        self.text = initialString
        ascent, descent = icon.globalFont.getmetrics()
        self.height = ascent + descent + 2 * icon.TEXT_MARGIN + 1
        self.initTxtWidth = icon.globalFont.getsize("i")[0]
        self.txtWidthIncr = self.initTxtWidth
        x, y = location if location is not None else (0, 0)
        self.attachedIcon = attachedIcon
        self.attachedSite = attachedSite
        if attachedIcon is None:
            self.attachedSiteType = None
        else:
            self.attachedSiteType = attachedIcon.typeOf(attachedSite)
        outSiteY = self.height // 2
        self.rect = (x, y, x + self._width(), y + self.height)
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('attrOut', 'attrOut', 0, outSiteY + icon.ATTR_SITE_OFFSET)
        self.sites.add('seqIn', 'seqIn', 0, outSiteY)
        self.sites.add('seqOut', 'seqOut', 0, outSiteY)
        self.markLayoutDirty()
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.cursorPos = len(initialString)

    def restoreForUndo(self, text):
        """Undo restores all attachments and saves the displayed text.  Update the
        remaining internal state based on attachments and passed text."""
        outIcon = self.sites.output.att
        attrIcon = self.sites.attrOut.att
        if outIcon is not None:
            self.attachedIcon = outIcon
            self.attachedSite = outIcon.siteOf(self)
            self.attachedSiteType = outIcon.typeOf(self.attachedSite)
        elif attrIcon is not None:
            self.attachedIcon = attrIcon
            self.attachedSite = attrIcon.siteOf(self)
            self.attachedSiteType = attrIcon.typeOf(self.attachedSite)
        else:
            self.attachedIcon = None
            self.attachedSite = None
            self.attachedSiteType = None
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
            img = Image.new('RGBA', (icon.rectWidth(self.rect), self.height))
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

    def addText(self, char):
        newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos + len(char))

    def backspace(self, evt=None):
        if self.text != "":
            newText = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
            self._setText(newText, self.cursorPos-1)
        elif self.pendingArg() or self.pendingAttr():
            # There's no text left but a pending arg or attribute.  The nasty hack below
            # calls the window backspace code and then restores pending args/attrs if it
            # can.  The right thing to do is (probably) not to allow the backspace if
            # pending data would be lost.  Suggest merging and integrating this code with
            # the window backspace code as a first step.
            pendingArg = self.pendingArg()
            pendingAttr = self.pendingAttr()
            self.remove()
            self.window._backspaceIcon(evt)
            entryIcon = self.window.entryIcon
            if entryIcon:
                if not (entryIcon.pendingArg() or entryIcon.pendingAttr()):
                    if pendingArg:
                        entryIcon.setPendingArg(pendingArg)
                    elif pendingAttr:
                        entryIcon.setPendingAttr(pendingAttr)
            else:
                self.window.entryIcon = self
                cursor = self.window.cursor
                if cursor.type == "icon":
                    self.attachedIcon = cursor.icon
                    self.attachedSite = cursor.site
                    cursor.icon.replaceChild(self, cursor.site)
                elif cursor.type == "window":
                    icon.moveRect(self.rect, cursor.pos)
                    self.window.addTop(self)
        else:  # No text or pending icons
            self.remove()

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

    def remove(self):
        """Get rid of entry icon, and restore pending arguments/attributes if possible"""
        if self.attachedIcon:
            if self.pendingArg() and self.attachedSiteType == "input":
                self.attachedIcon.replaceChild(self.pendingArg(), self.attachedSite)
            elif self.pendingAttr() and self.attachedSiteType == "attrIn":
                self.attachedIcon.replaceChild(self.pendingAttr(), self.attachedSite)
            else:
                self.attachedIcon.replaceChild(None, self.attachedSite, leavePlace=True)
            if self.attachedIcon.hasSite(self.attachedSite):
                self.window.cursor.setToIconSite(self.attachedIcon, self.attachedSite)
            else: # The last element of list can disappear when entry icon is removed
                seriesName, seriesIdx = icon.splitSeriesSiteId(self.attachedSite)
                newSite = icon.makeSeriesSiteId(seriesName, seriesIdx-1)
                self.window.cursor.setToIconSite(self.attachedIcon, newSite)
        else:  # Entry icon is not attached to icon (independent in window or in seq)
            pendingArg = self.pendingArg()
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

    def _setText(self, newText, newCursorPos):
        oldWidth = self._width()
        if self.attachedToAttribute():
            parseResult = parseAttrText(newText, self.window)
        elif self.attachedIcon is None or self.attachedSite in ('seqIn', 'seqOut'):
            parseResult = parseTopLevelText(newText, self.window)
        else: # Currently no other cursor places, must be expr
            parseResult = parseExprText(newText, self.window)
        # print('parse result', parseResult)
        if parseResult == "reject":
            beep()
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
        elif parseResult == "comma":
            if self.commaEntered(self.attachedIcon, self.attachedSite):
                if self.attachedIcon is not None:
                    self.attachedIcon.replaceChild(None, self.attachedSite)
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
                    self.attachedIcon = cursor.icon
                    self.attachedSite = cursor.site
                    self.attachedSiteType = cursor.siteType
                    cursor.setToEntryIcon()
            else:
                beep()
            return
        elif parseResult == "colon":
            if not self.insertColon():
                beep()
            return
        elif parseResult == "openBracket":
            self.insertOpenParen(icon.ListIcon)
            return
        elif parseResult == "endBracket":
            matchedBracket = self.getUnclosedParen(parseResult, self.attachedIcon,
             self.attachedSite)
            if matchedBracket is None:
                if not self._removeAndReplaceWithPending():
                    # Cant unload pending args from cursor.  Don't allow move
                    beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    beep()
            else:
                matchedBracket.close()
                if self._removeAndReplaceWithPending():
                    cursor.setToIconSite(matchedBracket, "attrIcon")
                else:
                    self.attachedIcon.replaceChild(None, self.attachedSite)
                    # Move entry icon with pending args past the paren
                    self.attachedIcon = matchedBracket
                    self.attachedSite = "attrIcon"
                    self.attachedSiteType = "attrIn"
            return
        elif parseResult == "openBrace":
            self.insertOpenParen(icon.DictIcon)
            return
        elif parseResult == "endBrace":
            matchedBracket = self.getUnclosedParen(parseResult, self.attachedIcon,
             self.attachedSite)
            if matchedBracket is None:
                if not self._removeAndReplaceWithPending():
                    # Cant unload pending args from cursor.  Don't allow move
                    beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    beep()
            else:
                matchedBracket.close()
                if self._removeAndReplaceWithPending():
                    cursor.setToIconSite(matchedBracket, "attrIcon")
                else:
                    self.attachedIcon.replaceChild(None, self.attachedSite)
                    # Move entry icon with pending args past the paren
                    self.attachedIcon = matchedBracket
                    self.attachedSite = "attrIcon"
                    self.attachedSiteType = "attrIn"
            return
        elif parseResult == "openParen":
            self.insertOpenParen(CursorParenIcon)
            return
        elif parseResult == "endParen":
            matchingParen = self.getUnclosedParen(parseResult, self.attachedIcon,
             self.attachedSite)
            if matchingParen is None:
                # Maybe user was just trying to move past an existing paren by typing it
                if not self._removeAndReplaceWithPending():
                    # Cant unload pending args from cursor.  Don't allow move
                    beep()
                    return
                if not cursor.movePastEndParen(parseResult):
                    beep()
            elif matchingParen.__class__ is CursorParenIcon and \
             matchingParen is self.attachedIcon and self.attachedSite == 'argIcon':
                # The entry icon is directly on the input site of a cursor paren icon to
                # be closed, this is the special case of an empty tuple: convert it to one
                parent = matchingParen.parent()
                tupleIcon = icon.TupleIcon(window=self.window)
                if parent is None:
                    self.window.replaceTop(matchingParen, tupleIcon)
                    tupleIcon.markLayoutDirty()
                else:
                    parent.replaceChild(tupleIcon, parent.siteOf(matchingParen))
                if self.pendingArg() or self.pendingAttr():
                    # Move entry icon with pending args past the paren
                    self.attachedIcon = tupleIcon
                    self.attachedSite = "attrIcon"
                    self.attachedSiteType = "attrIn"
                    tupleIcon.replaceChild(self, "attrIcon")
                else:
                    self.window.entryIcon = None
                    self.window.cursor.setToIconSite(tupleIcon, "attrIcon")
            else:
                # Try to place pending arguments where they came from.
                self._removeAndReplaceWithPending()
            return
        elif parseResult == "makeFunction":
            if not self.makeFunction(self.attachedIcon):
                beep()
            return
        elif parseResult == "makeSubscript":
            if not self.makeSubscript(self.attachedIcon):
                beep()
            return
        # Parser emitted an icon.  Splice it in to the hierarchy
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        snapLists = ic.snapLists(forCursor=True)
        if self.attachedIcon is None:
            # Note that this clause includes sequence-site attachment
            self.window.replaceTop(self, ic)
            ic.markLayoutDirty()
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            elif "attrIn" in snapLists:
                cursor.setToIconSite(ic, "attrIcon")
            elif "seqOut" in snapLists:
                cursor.setToIconSite(ic, "seqOut")
        elif ic.__class__ in (icon.AssignIcon, icon.AugmentedAssignIcon):
            if not self.insertAssign(ic):
                beep()
                return
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            if ic.__class__ is icon.AttrIcon:
                self.attachedIcon.replaceChild(ic, "attrIcon")
                cursor.setToIconSite(ic, "attrIcon")
            else:
                if not self.appendOperator(ic):
                    beep()
                    return
        elif self.attachedSiteType == "input":
            # Entry icon is attached to an input site
            self.attachedIcon.replaceChild(ic, self.attachedSite)
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            elif "attrIn in snapLists":
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
                if cursor.icon.__class__ in (icon.BinOpIcon, icon.UnaryOpIcon):
                    # Changing an operand of an arithmetic operator may require reorder
                    reorderArithExpr(cursor.icon)
        if self.pendingAttr() is not None and remainingText == "":
            if cursor.type == "icon" and cursor.siteType == "attrIn" and \
             cursor.icon.childAt(cursor.site) is None:
                cursor.icon.replaceChild(self.pendingAttr(), cursor.site)
                self.setPendingAttr(None)
        # If the entry icon can go away, remove it and we're done
        if self.pendingArg() is None and self.pendingAttr() is None and remainingText == "":
            self.window.entryIcon = None
            return
        # There is remaining text or pending arguments.  Restore the entry icon
        if cursor.type != "icon":  # I don't think this can happen
            print('Cursor type not icon in _setText')
            return
        self.attachedIcon = cursor.icon
        self.attachedSite = cursor.site
        self.attachedSiteType = cursor.icon.typeOf(cursor.site)
        self.attachedIcon.replaceChild(self, self.attachedSite)
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

    def _removeAndReplaceWithPending(self):
        """Removes the entry icon and replaces it with it's pending argument or attribute
        if that is possible.  If the pending item cannot be put in place of the entry
        icon, does nothing and returns False"""
        if self.attachedIcon is not None:
            if self.pendingArg() and self.attachedSiteType == "input":
                self.attachedIcon.replaceChild(self.pendingArg(), self.attachedSite)
                self.setPendingArg(None)
            elif self.pendingAttr() and self.attachedSiteType == "attrIn":
                self.attachedIcon.replaceChild(self.pendingAttr(), self.attachedSite)
                self.setPendingAttr(None)
            elif self.pendingArg() is None and self.pendingAttr() is None:
                self.attachedIcon.replaceChild(None, self.attachedSite,
                    leavePlace=True)
            else:
                return False
            self.window.cursor.setToIconSite(self.attachedIcon, self.attachedSite)
        else:  # Entry icon is at top level
            if self.pendingArg():
                self.window.replaceTop(self.pendingArg())
                self.window.cursor.setToIconSite(self.pendingArg(), 'output')
                self.setPendingArg(None)
            elif self.pendingAttr():
                self.window.replaceTop(self.pendingAttr())
                self.window.cursor.setToIconSite(self.pendingAttr(), 'attrOut')
                self.setPendingAttr(None)
        self.window.entryIcon = None
        return True

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
            tupleIcon = icon.TupleIcon(window=self.window)
            tupleIcon.insertChildren([None, self.pendingArg()], "argIcons", 0)
            self.setPendingArg(None)
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 0)
            self.window.replaceTop(self, tupleIcon)
            return True
        siteType = onIcon.typeOf(site)
        if icon.isSeriesSiteId(site) and siteType == "input":
            # This is essentially ",,", which means leave a new space for an arg
            # Entry icon holds pending arguments
            seriesName, seriesIndex = icon.splitSeriesSiteId(site)
            onIcon.insertChildren([None], seriesName, seriesIndex)
            siteAfterComma = icon.makeSeriesSiteId(seriesName, seriesIndex + 1)
            if onIcon.childAt(siteAfterComma) == self:
                # Remove the Entry Icon and restore its pending arguments
                if self.pendingArg() is None:
                    # replaceChild on listTypeIcon removes comma.  Put it back
                    onIcon.replaceChild(None, siteAfterComma, leavePlace=True)
                else:
                    onIcon.replaceChild(self.pendingArg(), siteAfterComma)
                    self.setPendingArg(None)
                self.attachedIcon = None
            self.window.cursor.setToIconSite(onIcon, siteAfterComma)
            return True
        if onIcon.__class__ in (icon.UnaryOpIcon, icon.DivideIcon) and \
         siteType == "input":
            return False
        elif onIcon.__class__ is icon.BinOpIcon and onIcon.hasParens:
            return False
        elif onIcon.__class__ is CursorParenIcon:  # Open-paren
            tupleIcon = icon.TupleIcon(window=self.window, closed=True)
            args = [None]
            if onIcon.sites.argIcon.att and onIcon.sites.argIcon.att is not self:
                args += [onIcon.sites.argIcon.att]
            tupleIcon.insertChildren(args, "argIcons", 0)
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 0)
            parent = onIcon.parent()
            if parent is None:
                self.window.replaceTop(onIcon, tupleIcon)
            else:
                parent.replaceChild(tupleIcon, parent.siteOf(onIcon))
            attrIcon = onIcon.sites.attrIcon.att
            onIcon.replaceChild(None, 'attrIcon')
            tupleIcon.replaceChild(attrIcon, 'attrIcon')
            return True
        if (isinstance(onIcon, icon.BinOpIcon) or isinstance(onIcon, icon.TwoArgIcon)) \
         and site == "leftArg":
            leftArg = None
            rightArg = onIcon
            if onIcon.leftArg() is self:
                onIcon.replaceChild(self.pendingArg(),"leftArg")
                self.setPendingArg(None)
                self.attachedIcon = None
        elif (isinstance(onIcon, icon.BinOpIcon) or isinstance(onIcon, icon.TwoArgIcon)) \
         and site == "rightArg":
            leftArg = onIcon
            rightArg = onIcon.rightArg()
            if rightArg is self:
                rightArg = self.pendingArg()
                self.setPendingArg(None)
                self.attachedIcon = None
            onIcon.replaceChild(None,"rightArg")
            self.window.cursor.setToIconSite(onIcon, "rightArg")
            cursorPlaced = True
        else:
            onIcon = icon.findAttrOutputSite(onIcon)
            leftArg = onIcon
            rightArg = None
        child = onIcon
        for parent in onIcon.parentage():
            childSite = parent.siteOf(child)
            if icon.isSeriesSiteId(childSite):
                onIcon.markLayoutDirty()
                parent.replaceChild(leftArg, childSite, leavePlace=True)
                seriesName, seriesIndex = icon.splitSeriesSiteId(childSite)
                parent.insertChild(rightArg, seriesName, seriesIndex + 1)
                if hasattr(parent, "closed") and not parent.closed:
                    # Once an item has a comma, we know what it is and where it ends, and
                    # an open paren/bracket/brace with commas would be hard to handle.
                    parent.close()
                if not cursorPlaced:
                    cursorIdx = seriesIndex if leftArg is None else seriesIndex + 1
                    self.window.cursor.setToIconSite(parent, seriesName, cursorIdx)
                return True
            if parent.__class__ is CursorParenIcon:
                tupleIcon = icon.TupleIcon(window=self.window)
                tupleIcon.insertChildren([leftArg, rightArg], "argIcons", 0)
                if not cursorPlaced:
                    idx = 0 if leftArg is None else 1
                    self.window.cursor.setToIconSite(tupleIcon, "argIcons", idx)
                parentParent = parent.parent()
                if parentParent is None:
                    self.window.replaceTop(parent, tupleIcon)
                else:
                    parentParent.replaceChild(tupleIcon, parentParent.siteOf(parent))
                if parent.hasSite('attrIcon'):
                    attrIcon = parent.sites.attrIcon.att
                    parent.replaceChild(None, 'attrIcon')
                    tupleIcon.replaceChild(attrIcon, 'attrIcon')
                return True
            if isinstance(parent, icon.UnaryOpIcon):
                leftArg = parent
            elif isinstance(parent, icon.BinOpIcon) and not parent.hasParens or \
             isinstance(parent, icon.TwoArgIcon):
                # Parent is a binary op icon without parens, and site is one of the two
                # input sites
                if parent.leftArg() is child:  # Insertion was on left side of operator
                    parent.replaceChild(rightArg, "leftArg")
                    if parent.leftArg() is None:
                        self.window.cursor.setToIconSite(parent, "leftArg")
                        cursorPlaced = True
                    rightArg = parent
                elif parent.rightArg() is child:   # Insertion on right side of operator
                    parent.replaceChild(leftArg, "rightArg")
                    if parent.rightArg() is None:
                        self.window.cursor.setToIconSite(parent, "rightArg")
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
        tupleIcon = icon.TupleIcon(window=self.window, noParens=True)
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
        if iconClass is CursorParenIcon:
            closed = False  # We leave even empty paren open to detect () for empty tuple
            inputSite = 'argIcon'
        else:
            closed = self.pendingArg() is None
            inputSite = 'argIcons_0'
        newParenIcon = iconClass(window=self.window, closed=closed)
        attachedIc = self.attachedIcon
        attachedSite = self.attachedSite
        if attachedIc is None:
            self.window.replaceTop(self, newParenIcon)
        else:
            attachedIc.replaceChild(newParenIcon, attachedSite)
        newParenIcon.replaceChild(self, inputSite)
        self.attachedIcon = newParenIcon
        self.attachedSite = inputSite
        self.attachedSiteType = "input"
        # Attempt to get rid of the entry icon and place pending arg in its place
        self._removeAndReplaceWithPending()
        # Reorder the expression with the new open paren in place (skip some work if the
        # entry icon was at the top level, since no reordering is necessary, there)
        if attachedIc is not None:
            top = reorderArithExpr(newParenIcon)

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
            for op in traverseExprLeftToRight(highestAffectedExpr(fromIcon),
                    closeParenAfter=fromIcon):
                if isinstance(op, CloseParenToken) and op.parenIcon is None:
                    # A CloseParenToken with parenIcon of None is the inserted end paren
                    break
                if isinstance(op, OpenParenToken) and isinstance(op.parenIcon,
                 CursorParenIcon) and not op.parenIcon.closed:
                    matchingParen = op.parenIcon
            else:
                print('getUnclosedParen failed to find close-paren site')
        if matchingParen is None:
            return None
        if matchingParen is fromIcon or isinstance(matchingParen, icon.TupleIcon):
            # matchingParen is an open cursor paren or a tuple with no parens or an
            # open cursor paren.  No reordering necessary, just add/close the parens
            if matchingParen.__class__ is icon.TupleIcon:
                matchingParen.restoreParens()
            else:
                matchingParen.close()
            return matchingParen
        # Rearrange the hierarchy so the paren/bracket/brace is above all the icons it
        # should enclose and outside of those it does not enclose.  reorderArithExpr
        # closes the parens if it succeeds.
        reorderArithExpr(matchingParen, fromIcon)
        return matchingParen

    def makeFunction(self, ic):
        callIcon = icon.CallIcon(window=self.window, closed=self.pendingArg() is None)
        ic.replaceChild(callIcon, 'attrIcon')
        if self.pendingAttr():
            self.attachedSite = 'argIcons_0'
            self.attachedIcon = callIcon
            self.attachedSiteType = 'input'
            callIcon.replaceChild(self, 'argIcons_0')
            return True
        if self.pendingArg():
            callIcon.replaceChild(self.pendingArg(), 'argIcons_0')
        self.window.entryIcon = None
        self.window.cursor.setToIconSite(callIcon, "argIcons", 0)
        return True

    def makeSubscript(self, ic):
        closed = self.pendingArg() is None
        subscriptIcon = icon.SubscriptIcon(window=self.window, closed=closed)
        ic.replaceChild(subscriptIcon, 'attrIcon')
        if self.pendingAttr():
            self.attachedSite = 'indexIcon'
            self.attachedIcon = subscriptIcon
            self.attachedSiteType = 'input'
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
        argIcon = icon.findAttrOutputSite(self.attachedIcon)
        if argIcon is None:
            return False
        self.attachedIcon.replaceChild(None, self.attachedSite)
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
            if stopAtParens or op.__class__ not in (icon.BinOpIcon, icon.UnaryOpIcon) or \
                    newOpIcon.precedence > op.precedence or \
                    newOpIcon.precedence == op.precedence and (
                     op.leftAssoc() and op.leftArg() is childOp or
                     op.rightAssoc() and op.rightArg() is childOp):
                op.replaceChild(newOpIcon, op.siteOf(childOp))
                break
            if op.__class__ is icon.UnaryOpIcon:
                op.replaceChild(leftArg, "argIcon")
                leftArg = op
            else:  # BinaryOp
                if op.leftArg() is childOp:  # Insertion was on left side of operation
                    op.replaceChild(rightArg, "leftArg")
                    if op.leftArg() is None:
                        self.window.cursor.setToIconSite(op, "leftArg")
                    rightArg = op
                else:                      # Insertion was on right side of operation
                    op.replaceChild(leftArg, "rightArg")
                    leftArg = op
                if op.hasParens:
                    # If the op has parens and the new op has been inserted within them,
                    # do not go beyond the parent operation
                    stopAtParens = True
            childOp = op
        else:  # Reached the top level without finding a parent for newOpIcon
            self.window.replaceTop(childOp, newOpIcon)
        leftSite = "topArg" if newOpIcon.__class__ is icon.DivideIcon else "leftArg"
        rightSite = "bottomArg" if newOpIcon.__class__ is icon.DivideIcon else "rightArg"
        if rightArg is None:
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
        if newOpIcon.__class__ is icon.DivideIcon:
            topArgChild = newOpIcon.childAt('topArg')
            if isinstance(topArgChild, CursorParenIcon) and topArgChild.closed:
                newOpIcon.replaceChild(topArgChild.childAt('argIcon'), 'topArg')
        return True

    def insertAssign(self, assignIcon):
        attIcon = icon.findAttrOutputSite(self.attachedIcon)
        attIconClass = attIcon.__class__
        isAugmentedAssign = assignIcon.__class__ is icon.AugmentedAssignIcon
        if not (attIconClass is icon.AssignIcon or attIconClass is icon.TupleIcon and
         attIcon.noParens or self.attachedToAttribute() and attIconClass in
         (icon.IdentifierIcon, icon.TupleIcon, icon.ListIcon, icon.AttrIcon)):
            return False
        if self.attachedToAttribute():
            highestCoincidentIcon = icon.highestCoincidentIcon(attIcon)
            if highestCoincidentIcon in self.window.topIcons:
                # The cursor is attached to an attribute of a top-level icon of a type
                # appropriate as a target. Insert assignment icon and make it the target.
                self.attachedIcon.replaceChild(None, self.attachedSite)
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
        topParent = attIcon.topLevelParent()
        if topParent.__class__ is icon.TupleIcon and topParent.noParens:
            # There is a no-paren tuple at the top level waiting to be converted in to an
            # assignment statement.  Do the conversion.
            targetIcons = topParent.argIcons()
            if isAugmentedAssign:
                # Augmented (i.e. +=) assigns have just one target, but it is possible
                # to delete out a comma and be left with a single value in the tuple
                if len(targetIcons) != 1:
                    return False
                self.attachedIcon.replaceChild(None, self.attachedSite)
                assignIcon.replaceChild(targetIcons[0], 'targetIcon')
            else:
                self.attachedIcon.replaceChild(None, self.attachedSite)
                insertSiteId = topParent.siteOf(attIcon, recursive=True)
                for tgtIcon in targetIcons:
                    topParent.replaceChild(None, topParent.siteOf(tgtIcon))
                seriesName, seriesIdx = icon.splitSeriesSiteId(insertSiteId)
                splitIdx = seriesIdx + (0 if topParent is self.attachedIcon else 1)
                assignIcon.insertChildren(targetIcons[:splitIdx], 'targets0', 0)
                assignIcon.insertChildren(targetIcons[splitIdx:], 'values', 0)
                if splitIdx < len(targetIcons):
                    assignIcon.insertChild(None, 'values_0')
            self.window.replaceTop(topParent, assignIcon)
            self.window.cursor.setToIconSite(assignIcon, "values_0")
            return True
        if topParent.__class__ is icon.AssignIcon and not isAugmentedAssign:
            # There is already an assignment icon.  Add a new clause, splitting the
            # target list at the entry location.  (assignIcon is thrown away)
            self.attachedIcon.replaceChild(None, self.attachedSite)
            insertSiteId = topParent.siteOf(attIcon, recursive=True)
            seriesName, seriesIdx = icon.splitSeriesSiteId(insertSiteId)
            splitIdx = seriesIdx + (0 if topParent is self.attachedIcon else 1)
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
                topParent.replaceChild(None, topParent.siteOf(tgtIcon))
            topParent.insertChildren(iconsToMove, 'targets%d' % newTgtGrpIdx, 0)
            if topParent.childAt(cursorSite):
                topParent.insertChild(None, cursorSite)
            self.window.cursor.setToIconSite(topParent, cursorSite)
            return True
        return False

    def insertColon(self):
        # Look for an icon that supports colons (currently, only subscript)
        for parent in self.attachedIcon.parentage(includeSelf=True):
            if isinstance(parent, icon.SubscriptIcon):
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
            if isinstance(parent, icon.DictIcon):
                dictIc = parent
                site = parent.siteOf(self, recursive=True)
                child = dictIc.childAt(site)
                dictElem = icon.DictElemIcon(window=self.window)
                if isinstance(child, icon.DictElemIcon):
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
                    if not self.commaEntered(self.attachedIcon, self.attachedSite):
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
                    # There's nothing at the site, yet
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
            cursorToIcon = self.attachedIcon
            cursorToSite = self.attachedSite
        # Decide on appropriate disposition for entry icon and cursor.  Try to remove
        # entry icon if at all possible, even if the colon was rejected, since there
        # won't be any text left in it.
        cursorSiteType = cursorToIcon.typeOf(cursorToSite)
        if self.pendingArg() and cursorSiteType == 'input' or \
         self.pendingAttr() and cursorSiteType == 'attrIn':
            # Entry icon has a pending argument which can be attached
            self.attachedIcon.replaceChild(None, self.attachedSite)
            self.window.entryIcon = None
            pend = self.pendingArg() if cursorSiteType == "input" else self.pendingAttr()
            cursorToIcon.replaceChild(pend, cursorToSite)
            self.window.cursor.setToIconSite(cursorToIcon, cursorToSite)
        elif self.pendingAttr() or self.pendingArg():
            # Entry icon has a pending arg or attr which could not be attached
            self.attachedIcon.replaceChild(None, self.attachedSite)
            self.attachedIcon = cursorToIcon
            self.attachedSite = cursorToSite
            self.attachedSiteType = "input"
            cursorToIcon.replaceChild(self, cursorToSite)
        else:
            # Entry icon has nothing pending and can safely be removed
            self.attachedIcon.replaceChild(None, self.attachedSite)
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
        if self.attachedSite and self.attachedSite == "attrIcon":
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
        width = self._width() - (1 if self.attachedToAttribute() else 2)
        siteOffset = self.height // 2
        if self.attachedSite and self.attachedSite == "attrIcon":
            siteOffset += icon.ATTR_SITE_OFFSET
        layouts = []
        for pendingArgLayout in pendingArgLayouts:
            layout = icon.Layout(self, width, self.height, siteOffset)
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
        return self.attachedSite is not None and \
         self.attachedSiteType in ("attrOut", "attrIn")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN

class CursorParenIcon(icon.Icon):
    def __init__(self, closed=False, window=None, location=None):
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

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
             fill=icon.ICON_BG_COLOR, outline=icon.OUTLINE_COLOR)
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
                draw.rectangle((0, 0, bodyWidth-1, bodyHeight-1), fill=icon.ICON_BG_COLOR,
                 outline=icon.OUTLINE_COLOR)
                textLeft = icon.TEXT_MARGIN
                draw.text((textLeft, icon.TEXT_MARGIN), ")",
                    font=icon.globalFont, fill=(120, 120, 120, 255))
                attrX = bodyWidth - 1 - icon.ATTR_SITE_DEPTH
                attrY = self.sites.attrIcon.yOffset
                closeImg.paste(icon.attrInImage, (attrX, attrY))
                endParenLeft = icon.rectWidth(self.rect) - bodyWidth
                self.drawList.append(((endParenLeft, 0), closeImg))
            else:
                draw.line((bodyLeft, outSiteY, inSiteX, outSiteY),
                 fill=icon.ICON_BG_COLOR, width=3)
        self._drawFromDrawList(toDragImage, location, clip, style)

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
        width = singleParenWidth
        argIcon = self.sites.argIcon.att
        argLayouts = [None] if argIcon is None else argIcon.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        else:
            attrLayouts = [None]
        layouts = []
        for argLayout, attrLayout in icon.allCombinations((argLayouts, attrLayouts)):
            layout = icon.Layout(self, width, height, height//2)
            layout.addSubLayout(argLayout, 'argIcon', singleParenWidth - 1, 0)
            width += icon.EMPTY_ARG_WIDTH if argLayout is None else argLayout.width - 1
            if self.closed:
                width += singleParenWidth - 1
                layout.width = width
                layout.addSubLayout(attrLayout, 'attrIcon', width - icon.ATTR_SITE_DEPTH,
                        icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

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

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Allow cursor to be set to the end paren before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', icon.rectWidth(self.rect) -
         icon.ATTR_SITE_DEPTH, icon.rectHeight(self.rect) // 2 + icon.ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

class Cursor:
    def __init__(self, window, cursorType):
        self.window = window
        self.type = cursorType
        self.pos = (0, 0)
        self.icon = None
        self.site = None
        self.siteType = None
        self.lastDrawRect = None
        self.blinkState = False
        self.anchorIc = None
        self.anchorSite = None
        self.anchorLine = None
        self.lastSelIc = None
        self.lastSelSite = None

    def setToWindowPos(self, pos):
        if self.type is not None:
            self.erase()
        self.type = "window"
        self.pos = pos
        self.blinkState = True
        self.draw()

    def setToIconSite(self, ic, siteIdOrSeriesName, seriesIndex=None):
        if self.type is not None:
            self.erase()
        self.type = "icon"
        self.icon = ic
        if seriesIndex is None:
            self.site = siteIdOrSeriesName
        else:
            self.site = icon.makeSeriesSiteId(siteIdOrSeriesName, seriesIndex)
        self.siteType = ic.typeOf(self.site)
        self.blinkState = True
        self.draw()

    def setToEntryIcon(self):
        if self.type is not None:
            self.erase()
        self.type = "text"
        self.blinkState = True
        self.draw()

    def moveToIconSite(self, ic, site, evt):
        """Place the cursor at an icon site, paying attention to keyboard modifiers"""
        shiftPressed = evt.state & python_g.SHIFT_MASK
        if shiftPressed:
            self.selectToCursor(ic, site, evt.keysym)
        else:
            self.setToIconSite(ic, site)

    def selectToCursor(self, ic, site, direction):
        """Modify selection based on cursor movement (presumably with Shift key held)"""
        selectedIcons = set(self.window.selectedIcons())
        redrawRect = python_g.AccumRects()
        if len(selectedIcons) == 0 and self.type == "icon":
            # This is a new cursor-based selection
            self.anchorIc = self.icon
            self.anchorSite = self.site
        elif self.anchorIc is not None or self.anchorLine is not None:
            # There is a current recorded selection, but verify that it is valid by
            # matching it with the current actual selection
            lastSelIcons = set(self._iconsBetween(self.lastSelIc, self.lastSelSite))
            diffIcons = selectedIcons.difference(lastSelIcons)
            if len({i for i in diffIcons if not isinstance(i, icon.BlockEnd)}):
                self.anchorIc = None
                self.anchorLine = None
        if self.anchorIc is None and self.anchorLine is None:
            # The current selection is not valid, assume it was made via mouse.  Choose
            # an anchor line as the farthest side of the selection rectangle from the
            # cursor using the direction of arrow motion to choose horiz/vert
            selectedRect = python_g.AccumRects()
            for i in selectedIcons:
                selectedRect.add(i.selectionRect())
            left, top, right, bottom = selectedRect.get()
            left += 3    # Inset rectangle to avoid overlaps and protruding sites
            right -= 3
            top += 1
            bottom -= 1
            siteX, siteY = ic.posOfSite(site)
            if direction in ("Left", "Right"):
                anchorX = right if abs(siteX - left) <= abs(siteX - right) else left
                self.anchorLine = (anchorX, top, anchorX, bottom)
            else:
                anchorY = bottom if abs(siteY - top) <= abs(siteY - bottom) else top
                self.anchorLine = (left, anchorY, right, anchorY)
        select = set(self._iconsBetween(ic, site))
        erase = selectedIcons.difference(select)
        select = select.difference(selectedIcons)
        for i in erase:
            redrawRect.add(i.hierRect())
            i.select(False)
        for i in select:
            redrawRect.add(i.hierRect())
            i.select()
        self.window.refresh(redrawRect.get())
        self.setToIconSite(ic, site)
        self.lastSelIc = ic
        self.lastSelSite = site

    def _iconsBetween(self, ic, site):
        """Find the icons that should be selected by shift-select between the current
        anchor (self.anchorIc and Pos, or self.anchorLine) and cursor at ic, site."""
        siteX, siteY = ic.posOfSite(site)
        siteType = ic.typeOf(site)
        if siteType in ("attrIn", "attrOut"):
            siteY -= icon.ATTR_SITE_OFFSET
        elif siteType in ("seqIn", "seqOut"):
            seqInX, seqInY = ic.posOfSite("seqIn")
            seqOutX, seqOutY = ic.posOfSite("seqOut")
            siteY = (seqInY + seqOutY) // 2
        if self.anchorIc is not None:
            anchorX, anchorY = self.anchorIc.posOfSite(self.anchorSite)
            anchorSiteType = self.anchorIc.typeOf(self.anchorSite)
            if anchorSiteType in ("attrIn", "attrOut"):
                anchorY -= icon.ATTR_SITE_OFFSET
            elif anchorSiteType in ("seqIn", "seqOut"):
                seqInX, seqInY = self.anchorIc.posOfSite("seqIn")
                seqOutX, seqOutY = self.anchorIc.posOfSite("seqOut")
                anchorY = (seqInY + seqOutY) // 2
            if anchorX < siteX:
                anchorX += 4  # Avoid overlapped icons and sites
                siteX -= 3
            elif siteX < anchorX:
                siteX += 4
                anchorX -= 3
            selectRect = python_g.AccumRects((anchorX, anchorY - 3, anchorX, anchorY + 3))
            selectRect.add((siteX, siteY - 3, siteX, siteY + 3))
        else:
            if self.anchorLine[0] == self.anchorLine[2]:
                anchorX = self.anchorLine[0]
                if anchorX < siteX:
                    self.anchorLine = python_g.offsetRect(self.anchorLine, 4, 0)
                    siteX -= 3
                elif siteX < anchorX:
                    siteX += 4
                    icon.moveRect(self.anchorLine, (-3, 0))
            selectRect = python_g.AccumRects(self.anchorLine)
            selectRect.add((siteX, siteY, siteX, siteY))
        # Get the icons that would be covered by a rectangular selection of the box
        iconsToSelect = self.window.findIconsInRegion(selectRect.get())
        iconsToSelect = [ic for ic in iconsToSelect if ic.inRectSelect(selectRect.get())]
        # If the selection spans multiple statements, change to statement-level selection
        topIcons = {ic.topLevelParent() for ic in iconsToSelect}
        if len(topIcons) <= 1:
            return iconsToSelect
        else:
            return self._seqIconsBetween(topIcons)

    def _seqIconsBetween(self, topIcons):
        """Return all of the icons in the sequence including topIcons (filling in gaps,
        and adding all of the icons in the statement hierarchy)"""
        # Note that we can cheat, here for efficiency, knowing that the caller is working
        # geometrically, so we can order the sequence by icon position
        topIconSet = set(topIcons)
        sortedTopIcons = sorted(topIcons, key=lambda i: i.pos()[1])
        iconsInSeq = set()
        for ic in icon.traverseSeq(sortedTopIcons[0]):
            iconsInSeq.add(ic)
            if ic is sortedTopIcons[-1]:
                break
        else:
            iconsInSeq = set()
        # Fail softly if something bad happend in the geometric ordering, and make sure
        # that at least all statements passed in are represented
        if not topIconSet.issubset(iconsInSeq):
            print("Did your last cursor movement leave a gap in selected statments?")
            iconsInSeq.union(topIconSet)
        # return the full hierarchy
        return [i for ic in iconsInSeq for i in ic.traverse()]

    def removeCursor(self):
        if self.type is not None:
            self.erase()
        self.type = None

    def blink(self):
        self.blinkState = not self.blinkState
        if self.blinkState:
            self.draw()
        else:
            self.erase()

    def draw(self):
        if self.type is None or self.window.dragging is not None:
            return
        elif self.type == "window":
            cursorImg = inputSiteCursorImage
            x, y = self.pos
            y -= inputSiteCursorOffset
        elif self.type == "icon":
            sitePos = self.icon.posOfSite(self.site)
            if sitePos is None:
                return # Cursor can be moved before site fully exists, so fail softly
            x, y = sitePos
            if self.siteType in ("input", "output"):
                cursorImg = inputSiteCursorImage
                y -= inputSiteCursorOffset
            elif self.siteType in ("attrOut", "attrIn"):
                cursorImg = attrSiteCursorImage
                y -= attrSiteCursorOffset
            elif self.siteType == "seqIn":
                cursorImg = seqInSiteCursorImage
                x -= seqInSiteCursorXOffset
                y -= seqInSiteCursorYOffset
            elif self.siteType == "seqOut":
                cursorImg = seqOutSiteCursorImage
                x -= seqOutSiteCursorXOffset
                y -= seqOutSiteCursorYOffset
            else:
                return
        elif self.type == "text":
            eIcon = self.window.entryIcon
            if eIcon is None:
                return
            cursorPos = min(eIcon.cursorPos, len(eIcon.text))
            cursorImg = textCursorImage
            x, y = eIcon.rect[:2]
            x += eIcon.textOffset + icon.globalFont.getsize(eIcon.text[:cursorPos])[0]
            y += eIcon.sites.output.yOffset - cursorImg.height // 2
        cursorRegion = (x, y, x + cursorImg.width, y + cursorImg.height)
        self.lastDrawRect = cursorRegion
        cursorRegion = self.window.contentToImageRect(cursorRegion)
        cursorDrawImg = self.window.image.crop(cursorRegion)
        cursorDrawImg.paste(cursorImg, mask=cursorImg)
        self.window.drawImage(cursorDrawImg, cursorRegion[:2])

    def processArrowKey(self, evt):
        direction = evt.keysym
        if self.type is None:
            return
        elif self.type == "text":
            self.window.entryIcon.arrowAction(direction)
            return
        if self.type == "window":
            x, y = self.pos
            directions = {"Up":(0,-1), "Down":(0,1), "Left":(-1,0), "Right":(1,0)}
            xOff, yOff = directions[direction]
            x += xOff * WINDOW_CURSOR_INCREMENT
            y += yOff * WINDOW_CURSOR_INCREMENT
            windowWidth, windowHeight = self.window.image.size
            if  WINDOW_CURSOR_MARGIN < x < windowWidth - WINDOW_CURSOR_MARGIN and \
             WINDOW_CURSOR_MARGIN < y < windowHeight - WINDOW_CURSOR_MARGIN:
                self.erase()
                self.pos = x, y
                self.draw()
            return
        elif self.type == "icon":
            self._processIconArrowKey(evt)

    def arrowKeyWithSelection(self, evt, selectedIcons):
        """Process arrow key pressed with no cursor but selected icons."""
        direction = evt.keysym
        shiftPressed = evt.state & python_g.SHIFT_MASK
        if not shiftPressed:
            self.window.unselectAll()
        selectedRects = python_g.AccumRects()
        for ic in selectedIcons:
            selectedRects.add(ic.selectionRect())
        selectedRect = selectedRects.get()
        l, t, r, b = selectedRect
        l -= 10
        t -= 10
        r += 10
        b += 10
        searchRect = l, t, r, b
        cursorSites = []
        for ic in self.window.findIconsInRegion(searchRect):
            snapLists = ic.snapLists(forCursor=True)
            for ic, (x, y), name in snapLists.get("input", []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrIn", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            outSites = snapLists.get("output", [])
            if len(outSites) > 0:
                cursorSites.append((*outSites[0][1], ic, "output"))
        if len(cursorSites) == 0:
            return  # It is possible to have icons with no viable cursor sites
        selLeft, selTop, selRight, selBottom = selectedRect
        bestDist = None
        for siteData in cursorSites:
            x, y = siteData[:2]
            if direction == "Left":  # distance from left edge
                dist = abs(x - selLeft) + max(0, selBottom-y) + max(0, y-selTop)
            elif direction == "Right":  # distance from right edge
                dist = abs(x - selRight) + max(0, selBottom-y) + max(0, y-selTop)
            elif direction == "Up":  # distance from top edge
                dist = abs(y - selTop) + max(0, selLeft-x) + max(0, x-selRight)
            elif direction == "Down":  # distance from bottom edge
                dist = abs(y - selBottom) + max(0, selLeft-x) + max(0, x-selRight)
            if bestDist is None or dist < bestDist:
                bestSiteData = siteData
                bestDist = dist
        x, y, ic, site = bestSiteData
        if site == "output":
            parent = ic.parent()
            if parent is not None:
                self.setToIconSite(parent, parent.siteOf(ic))
                return
        self.moveToIconSite(ic, site, evt)

    def _processIconArrowKey(self, evt):
        """For cursor on icon site, set new site based on arrow direction"""
        # Build a list of possible destination cursor positions, normalizing attribute
        # site positions to the center of the cursor (in/out site position).
        direction = evt.keysym
        cursorX, cursorY = self.icon.posOfSite(self.site)
        searchRect = (cursorX-HORIZ_ARROW_MAX_DIST, cursorY-VERT_ARROW_MAX_DIST,
         cursorX+HORIZ_ARROW_MAX_DIST, cursorY+VERT_ARROW_MAX_DIST)
        cursorTopIcon = self.icon.topLevelParent()
        cursorPrevIcon = cursorTopIcon.prevInSeq()
        cursorNextIcon = cursorTopIcon.nextInSeq()
        cursorSites = []
        for winIcon in self.window.findIconsInRegion(searchRect):
            topIcon = winIcon.topLevelParent()
            if topIcon not in (cursorTopIcon, cursorPrevIcon, cursorNextIcon):
                continue  # Limit statement jumps to a single statement
            snapLists = winIcon.snapLists(forCursor=True)
            hasOutSite = len(snapLists.get("output", [])) > 0
            for ic, (x, y), name in snapLists.get('input', []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqIn', []):
                if direction in ('Up', 'Down'):
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqOut', []):
                if  direction in ('Up', 'Down') or not hasOutSite:
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrIn", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            if winIcon.parent() is None:
                outSites = snapLists.get("output", [])
                if len(outSites) > 0:
                    cursorSites.append((*outSites[0][1], winIcon, "output"))
        # Rank the destination positions by nearness to the current cursor position
        # in the cursor movement direction, and cull those in the wrong direction
        if self.siteType == "attrIn":
            cursorY -= icon.ATTR_SITE_OFFSET  # Normalize to input/output site y
        choices = []
        for x, y, ic, site in cursorSites:
            if direction == "Left":
                dist = cursorX - x
            elif direction == "Right":
                dist = x - cursorX
            elif direction == "Up":
                dist = cursorY - y
            elif direction == "Down":
                dist = y - cursorY
            if dist > 0:
                choices.append((dist, x, y, ic, site))
        if len(choices) == 0:
            return
        choices.sort(key=itemgetter(0))
        if direction in ("Left", "Right"):
            # For horizontal movement, just use a simple vertical threshold to decide
            # if the movement is appropriate
            for xDist, x, y, ic, site in choices:
                if xDist > VERT_ARROW_X_JUMP_MIN:
                    if abs(y - cursorY) < HORIZ_ARROW_Y_JUMP_MAX:
                        self.moveToIconSite(ic, site, evt)
                        return
        else:  # Up, Down
            # For vertical movement, do a second round of ranking.  This time add y
            # distance to weighted X distance (ranking x jumps as further away)
            bestRank = None
            for yDist, x, y, ic, site in choices:
                if yDist > VERT_ARROW_Y_JUMP_MIN or isinstance(ic, icon.BlockEnd):
                    rank = yDist + VERT_ARROW_X_WEIGHT*abs(x-cursorX)
                    if bestRank is None or rank < bestRank[0]:
                        bestRank = (rank, ic, site)
            if bestRank is None:
                return
            rank, ic, site = bestRank
            if site == 'seqIn' and direction == "Up":
                # Typing at a seqIn site is the same as typing at the connected seqOut
                # site, so save the user a keypress by going to the seqOut site above
                prevIcon = ic.prevInSeq()
                if prevIcon:
                    ic = prevIcon
                    site = 'seqOut'
            self.moveToIconSite(ic, site, evt)

    def movePastEndParen(self, token):
        """Move the cursor past the next end paren/bracket/brace (token is one of
        "endParen", "endBracket", or "endBrace"."""
        if self.type != "icon":
            return False
        siteType = self.siteType
        child = None
        # Just tear intervening icons to the end, regardless how far (was this right?)
        for parent in self.icon.parentage(includeSelf=True):
            if child is not None:
                siteType = parent.typeOf(parent.siteOf(child))
            if siteType == "input" and (
             (token == "endParen" and (
              parent.__class__ is icon.BinOpIcon and icon.needsParens(parent) or
              parent.__class__ in (icon.CallIcon, icon.TupleIcon, icon.DefIcon) or
              parent.__class__ is CursorParenIcon and parent.closed)) or
             (token == "endBrace" and isinstance(parent, icon.DictIcon)) or
             (token == "endBracket" and
              parent.__class__ in (icon.ListIcon, icon.SubscriptIcon))):
                self.setToIconSite(parent, "attrIcon")
                return True
            child = parent
        return False

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect, redraw=False)
            self.lastDrawRect = None

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

def parseAttrText(text, window):
    if len(text) == 0:
        return "accept"
    if text == '.' or attrPattern.fullmatch(text):
        return "accept"  # Legal attribute pattern
    if text in ("i", "a", "o", "an"):
        return "accept"  # Legal precursor characters to binary keyword operation
    if text in ("and", "is", "in", "or"):
        return icon.BinOpIcon(text, window), None # Binary keyword operation
    if text in ("*", "/", "@", "<", ">", "=", "!"):
        return "accept"  # Legal precursor characters to binary operation
    if text in compareOperators:
        return icon.BinOpIcon(text, window), None
    if text in binaryOperators:
        return "accept"  # Binary ops can be part of augmented assign (i.e. +=)
    if text[:-1] in binaryOperators and text[-1] == '=':
        return icon.AugmentedAssignIcon(text[:-1], window), None
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
    if text == ':':
        return "colon"
    op = text[:-1]
    delim = text[-1]
    if attrPattern.fullmatch(op):
        return icon.AttrIcon(op[1:], window), delim
    if opDelimPattern.match(delim):
        if op in compareOperators:
            return icon.BinOpIcon(op, window), delim
        if op in binaryOperators:
            # Valid binary operator followed by allowable operand character
            if op == '/':
                return icon.DivideIcon(False, window), delim
            elif op == '//':
                return icon.DivideIcon(True, window), delim
            return icon.BinOpIcon(op, window), delim
        if op[:-1] in binaryOperators and op[-1] == '=':
            return icon.AugmentedAssignIcon(op[:-1], window), delim
    if op == '=':
        return icon.AssignIcon(1, window), delim
    return "reject"

def parseExprText(text, window):
    if len(text) == 0:
        return "accept"
    if text in unaryOperators:
        # Unary operator
        return icon.UnaryOpIcon(text, window), None
    if text == 'yield':
        return icon.YieldIcon(window), None
    if text == 'await':
        return icon.AwaitIcon(window), None
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
        return icon.AssignIcon(1, window), None
    if identPattern.fullmatch(text) or numPattern.fullmatch(text):
        return "accept"  # Nothing but legal identifier and numeric
    delim = text[-1]
    text = text[:-1]
    if opDelimPattern.match(delim):
        if text in unaryOperators:
            return icon.UnaryOpIcon(text, window), delim
    if not (identPattern.fullmatch(text) or numPattern.fullmatch(text)):
        return "reject"  # Precursor characters do not form valid identifier or number
    if len(text) == 0 or delim not in delimitChars:
        return "reject"  # No legal text or not followed by a legal delimiter
    # All but the last character is ok and the last character is a valid delimiter
    if text in ('False', 'None', 'True'):
        return icon.IdentifierIcon(text, window), delim
    if text in keywords:
        return "reject"
    exprAst = compile_eval.parseExprToAst(text)
    if exprAst is None:
        return "reject"
    if exprAst.__class__ == ast.Name:
        return icon.IdentifierIcon(exprAst.id, window), delim
    if exprAst.__class__ == ast.Num:
        return icon.NumericIcon(exprAst.n, window), delim
    if exprAst.__class__ == ast.Constant and isinstance(exprAst.value, numbers.Number):
        return icon.NumericIcon(exprAst.value, window), delim
    return "reject"

def parseTopLevelText(text, window):
    if len(text) == 0:
        return "accept"
    for stmt, icClass in topLevelStmts.items():
        if len(text) <= len(stmt) and text == stmt[:len(text)]:
            return "accept"
        delim = text[-1]
        if text[:-1] == stmt and delim in delimitChars:
            kwds = {}
            if stmt[:5] == "async":
                kwds['isAsync'] = True
            return icClass(window=window, **kwds), delim
    return parseExprText(text, window)

def tkCharFromEvt(evt):
    if 32 <= evt.keycode <= 127 or 186 <= evt.keycode <= 192 or 219 <= evt.keycode <= 222:
        return chr(evt.keysym_num)
    return None

def beep():
    # Another platform dependent bit.  tkinter has a .bell() method, but it generates
    # an elaborate sound that's supposed to alert the user of a dialog popping up, which
    # is not appropriate for the tiny nudge for your keystroke being rejected.
    winsound.Beep(1500, 120)

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
            if token == "endParen" and isinstance(ic, CursorParenIcon) and not ic.closed:
                return ic
            if token == "endParen" and isinstance(ic, icon.TupleIcon) and ic.noParens:
                # Found a no-paren (top-level) tuple to parenthesize
                return ic
            if token == "endParen" and isinstance(ic, icon.CallIcon) and not ic.closed:
                return ic
            if token == "endBracket" and \
             ic.__class__ in (icon.ListIcon, icon.SubscriptIcon) and not ic.closed:
                return ic
            if token == "endBrace" and isinstance(ic, icon.DictIcon) and not ic.closed:
                return ic
            if isinstance(ic, icon.BinOpIcon) and ic.hasParens:
                # Don't allow search to escape enclosing arithmetic parens
                return None
            if ic.__class__ not in (icon.BinOpIcon, icon.UnaryOpIcon, icon.DictElemIcon):
                # For anything but an arithmetic op, inputs are enclosed in something
                # and search should not extend beyond (calls, tuples, subscripts, etc.)
                return None
        parent = ic.parent()
        if parent is None:
            return None
        site = parent.siteOf(ic)
        ic = parent

def rightmostSite(ic, ignoreAutoParens=False):
    """Return the site that is rightmost on an icon.  For most icons, that is an attribute
    site, but for unary or binary operations with the right operand missing, it can be an
    input site.  While binary op icons may have a fake invisible attribute site, it should
    be used carefully (if ever).  ignoreAutoParens prevents choosing auto-paren attribute
    site of BinOpIcon, even if it the rightmost."""
    if isinstance(ic, icon.UnaryOpIcon):
        if ic.arg() is None:
            return ic, 'argIcon'
        return rightmostSite(icon.findLastAttrIcon(ic.arg()))
    elif ic.__class__ in (icon.AssignIcon, icon.YieldIcon, icon.YieldFromIcon):
        children = [site.att for site in ic.sites.values if site.att is not None]
        if len(children) == 0:
            return ic, 'values_0'
        return rightmostSite(icon.findLastAttrIcon(children[-1]))
    elif isinstance(ic, icon.BinOpIcon) and (not ic.hasParens or ignoreAutoParens) or \
     isinstance(ic, icon.TwoArgIcon):
        if ic.rightArg() is None:
            return ic, 'rightArg'
        return rightmostSite(icon.findLastAttrIcon(ic.rightArg()))
    elif isinstance(ic, icon.DefIcon):
        children = [site.att for site in ic.sites.argIcons if site.att is not None]
        if len(children) == 0:
            return ic, 'argIcons_0'
        return rightmostSite(icon.findLastAttrIcon(children[-1]))
    elif ic.childAt('attrIcon'):
        return rightmostSite(ic.childAt('attrIcon'))
    return ic, 'attrIcon'

def _reduceOperatorStack(operatorStack, operandStack):
    """This is the inner component of reorderArithExpr (see below).  Pop a single operator
    off of the operator stack, link it with operands popped from the operand stack, and
    push the result on the operand stack."""
    stackOp = operatorStack.pop()
    if isinstance(stackOp, OpenParenToken):
        stackOp.arg = operandStack.pop()
    elif isinstance(stackOp, BinaryOpToken):
        stackOp.rightArg = operandStack.pop()
        stackOp.leftArg = operandStack.pop()
    elif isinstance(stackOp, UnaryOpToken):
        stackOp.arg = operandStack.pop()
    else:
        print('_reduceOperatorStack: unexpected icon on operator stack')
    operandStack.append(stackOp)

def reorderArithExpr(changedIcon, closeParenAt=None):
    """Reorders the arithmetic operators surrounding changed icon to agree with the text
    of the connected icons.  Because the icon representation reflects the hierarchy of
    operations, as opposed to the precedence and associativity of operators that the user
    types, changing an operator to one of a different precedence or adding or removing a
    paren, can drastically change what the expression means to the user.  This routine
    rearranges the hierarchy to match what the user sees.  changedIcon should specify an
    icon involved in the change.  If the changed icon is a paren/bracket/brace that needs
    to be closed, use closeParenAt to specify the rightmost icon to be enclosed (if
    successful, this function will close the paren/bracket/brace of changedIcon)."""
    topNode = highestAffectedExpr(changedIcon)
    topNodeParent = topNode.parent()
    topNodeParentSite = None if topNodeParent is None else topNodeParent.siteOf(topNode)
    if changedIcon.__class__ in (icon.ListIcon, icon.DictIcon,
     icon.CallIcon, icon.DefIcon, icon.SubscriptIcon) or \
     isinstance(changedIcon, icon.ClassDefIcon) and changedIcon.argList:
        allowedNonParen = OpenParenToken(changedIcon)
    else:
        allowedNonParen = None
    operatorStack = []
    operandStack = []
    # Loop left to right over the expression below topNode, assembling a tree containing
    # the icons that may need to be re-linked organized in the form that the icons will
    # need to take.
    for op in tuple(traverseExprLeftToRight(topNode, allowedNonParen, closeParenAt)):
        if isinstance(op, BinaryOpToken):
            # Binary operation.  Check if left operand can be reduced
            while len(operatorStack) > 0:
                stackOp = operatorStack[-1]
                if isinstance(stackOp, OpenParenToken) or (
                 stackOp.ic.precedence < op.ic.precedence or
                 stackOp.ic.precedence == op.ic.precedence and op.ic.rightAssoc()):
                    break
                _reduceOperatorStack(operatorStack, operandStack)
            operatorStack.append(op)
        elif isinstance(op, UnaryOpToken):
            # It's an operator, but the only operand is on the right
            operatorStack.append(op)
        elif isinstance(op, OpenParenToken):
            if op.parenIcon is changedIcon and closeParenAt:
                op.closed = True
            operatorStack.append(op)
        elif isinstance(op, CloseParenToken):
            while len(operatorStack) > 0:
                stackOp = operatorStack[-1]
                _reduceOperatorStack(operatorStack, operandStack)
                if isinstance(stackOp, OpenParenToken) and stackOp.closed:
                    if stackOp.parenIcon is not op.parenIcon:
                        # If parens have shifted, any attributes attached to the parens
                        # also need to shift.  Likewise for attached cursor & entry icon
                        if stackOp is allowedNonParen:
                            print('reorderArithExpr did not close matching brace/bracket')
                        stackOp.endParenAttr = None if op.parenIcon is None else \
                                op.parenIcon.childAt('attrIcon')
                        stackOp.endParenIc = op.parenIcon
                        cursor = stackOp.parenIcon.window.cursor
                        stackOp.takeCursor = cursor.type == "icon" and \
                         cursor.site == 'attrIcon' and cursor.icon is stackOp.parenIcon
                        stackOp.takeEntryIcon = closeParenAt and op.parenIcon is None
                    if stackOp.closed:
                        break  # Stop reducing once a matching paren is processed
        else:
            # Everything else is considered an operand
            operandStack.append(op)
    # Upon reaching the end of the expression, reduce all of the operators remaining in
    # the operator stack.
    while len(operatorStack) > 0:
        _reduceOperatorStack(operatorStack, operandStack)
    if len(operandStack) != 1:
        print("reorderArithExpr failed to converge")
        return topNode
    # print('before reorder') ; icon.dumpHier(topNode)
    # Requested paren can now be safely closed
    if closeParenAt:
        changedIcon.close()
    # Re-link the icons to the new expression form based on the token tree
    # print('token tree') ; dumpTok(operandStack[0])
    newTopNode = relinkExprFromTokens(operandStack[0])
    # print('after reorder') ; icon.dumpHier(newTopNode)
    # If the top node of the expression changed, re-link that to its parent
    if newTopNode is not topNode:
        if topNodeParent is None:
            newTopNode.replaceChild(None, 'output')
            topNode.window.replaceTop(topNode, newTopNode)
        else:
            topNodeParent.replaceChild(newTopNode, topNodeParentSite)
    # Parent links were not necessarily intact when icons were re-linked, and even though
    # the icons themselves get marked dirty, they won't be found unless the page is
    # marked as well.  Now that everything is back in place, mark the top icon again.
    newTopNode.markLayoutDirty()
    return newTopNode

def highestAffectedExpr(changedIcon):
    topCoincidentIcon = icon.highestCoincidentIcon(changedIcon)
    for ic in topCoincidentIcon.parentage(includeSelf=True):
        parent = ic.parent()
        if parent is None:
            return ic  # ic is at top level
        site = parent.siteOf(ic)
        siteType = parent.typeOf(site)
        if siteType == "input" and parent.__class__ not in (icon.BinOpIcon,
         icon.UnaryOpIcon, CursorParenIcon):
            return ic  # Everything other than arithmetic expressions encloses args

def traverseExprLeftToRight(topNode, allowedNonParen=None, closeParenAfter=None):
    """Traverse an expression from left to right returning "token" objects containing.
    one or more icons.  Note that this is not a fully general left to right traversal,
    but one specifically tailored to reorderArithExpr which operates only within the
    bounds of a changed expression, skipping over anything contained within icons other
    than arithmetic operations, cursor parens, and a single non-arithmetic paren/bracket/
    brace being modified (allowedNonParen).  If closeParenAfter is specified, emit an
    additional CloseParenToken when that icon is encountered in the traversal."""
    representedIcons = (topNode, )
    if topNode is None:
        yield MissingArgToken()
    elif isinstance(topNode, icon.BinOpIcon):
        if topNode.hasParens:
            yield OpenParenToken(topNode)
        yield from traverseExprLeftToRight(topNode.leftArg(), allowedNonParen,
         closeParenAfter)
        yield BinaryOpToken(topNode)
        yield from traverseExprLeftToRight(topNode.rightArg(), allowedNonParen,
         closeParenAfter)
        if topNode.hasParens:
            yield CloseParenToken(topNode)
    elif isinstance(topNode, icon.UnaryOpIcon):
        yield UnaryOpToken(topNode)
        yield from traverseExprLeftToRight(topNode.arg(), allowedNonParen,
         closeParenAfter)
    elif allowedNonParen is not None and topNode is allowedNonParen.ic:
        yield allowedNonParen
        parenContent = allowedNonParen.parenIcon.childAt(allowedNonParen.contentSite)
        yield from traverseExprLeftToRight(parenContent, allowedNonParen, closeParenAfter)
        representedIcons = allowedNonParen.representedIcons
    elif isinstance(topNode, CursorParenIcon):
        openParenOp = OpenParenToken(topNode)
        yield openParenOp
        yield from traverseExprLeftToRight(topNode.childAt('argIcon'), allowedNonParen,
         closeParenAfter)
        if topNode.closed:
            yield CloseParenToken(topNode)
        representedIcons = openParenOp.representedIcons
    else:
        # Anything that is not a binary operator or a cursor paren can be treated as a
        # unit rather than descending in to it.
        yield OperandToken(topNode)
        representedIcons = topNode.traverse(includeSelf=True)
    # If we're processing a newly entered close-paren, generate a CloseParenToken for it
    # after the icon indicated by closeParenAfter is emitted.
    if closeParenAfter is not None and closeParenAfter in representedIcons:
        yield CloseParenToken(None)

class OpenParenToken:
    """This class wraps various types of parentheses-like icon (brackets, braces,
    etc.) in the operator stack to simplify paren handling in reorderArithExpr.  Most
    importantly, it allows reorderArithExpr to treat an entire chain of attributes
    leading to paren types that are connected to attribute sites (CallIcon and
    SubscriptIcon) as a unit, in the same manner it treats cursor parens, lists,
    and dicts."""
    def __init__(self, parenIcon):
        self.representedIcons = [parenIcon]
        self.parenIcon = parenIcon
        if parenIcon.hasSite('attrOut'):
            self.ic = icon.findAttrOutputSite(parenIcon)
            for parent in parenIcon.parentage():
                self.representedIcons.append(parent)
                if parent is self.ic:
                    break
        else:
            self.ic = parenIcon
        if parenIcon is not None and parenIcon.hasSite('attrIcon'):
            attrIcon = parenIcon.childAt('attrIcon')
            if attrIcon is not None:
                self.representedIcons += list(attrIcon.traverse())
        if isinstance(parenIcon, icon.BinOpIcon):
            self.contentSite = None
        elif parenIcon.hasSite('argIcons_0'):
            self.contentSite = 'argIcons_0'
        elif isinstance(parenIcon, icon.SubscriptIcon):
            self.contentSite = 'indexIcon'
        else:
            self.contentSite = 'argIcon'
        self.closed = isinstance(self.parenIcon, icon.BinOpIcon) or self.parenIcon.closed
        self.arg = None
        self.endParenAttr = None
        self.endParenIc = None
        self.takeCursor = False
        self.takeEntryIcon = False

class CloseParenToken:
    """Represent an end-paren in the operator stack"""
    def __init__(self, parenIcon):
        self.parenIcon = parenIcon

class BinaryOpToken:
    def __init__(self, ic):
        self.ic = ic
        self.leftArg = None
        self.rightArg = None

class UnaryOpToken:
    def __init__(self, ic):
        self.ic = ic
        self.arg = None

class OperandToken:
    """Represents a tree of icons that are not part of the arithmetic expression being
    reordered (the tree can contain other arithmetic expressions, if they are separated
    from it by something other than arithmetic operators and grouping parens)."""
    def __init__(self, ic):
        self.ic = ic
        self.argTree = None

class MissingArgToken:
    pass

def relinkExprFromTokens(token, parentIc=None, parentSite=None):
    """reorderArithExpr re-parses arithmetic expressions to a tree of token objects
    containing the icons being reordered.  This routine does the actual rewiring of the
    icon structure per the token tree.  Reordering the icons is postponed until after
    all of the parsing is complete so that parens can be re-established based on proper
    precedence and associativity of parent operations (and allowing it to safely back
    out if parsing fails). Rather than filtering out redundant parentheses,
    reorderArithExpr works hard to preserve the exact paren counts that the user saw
    before making the change, possibly resulting auto-parens becoming cursor parens and
    visa versa."""
    if isinstance(token, OperandToken):
        return token.ic
    elif isinstance(token, MissingArgToken):
        return None
    elif isinstance(token, UnaryOpToken):
        arg = relinkExprFromTokens(token.arg, token.ic, 'argIcon')
        if arg.parent() is not token.ic:
            token.ic.replaceChild(arg, 'argIcon')
        return token.ic
    elif isinstance(token, BinaryOpToken):
        leftArg = relinkExprFromTokens(token.leftArg, token.ic, 'leftArg')
        rightArg = relinkExprFromTokens(token.rightArg, token.ic, 'rightArg')
        if token.ic.leftArg() is not leftArg:
            token.ic.replaceChild(leftArg, 'leftArg')
        if token.ic.rightArg() is not rightArg:
            token.ic.replaceChild(rightArg, 'rightArg')
        return token.ic
    elif isinstance(token, OpenParenToken):
        if token.closed and isinstance(token.arg, BinaryOpToken) and \
                icon.needsParens(token.arg.ic, parentIc, parentSite=parentSite):
            # Binary op child icon will provide its own auto-parens
            parenIc = relinkExprFromTokens(token.arg, parentIc, parentSite)
            outIc = parenIc
            if isinstance(token.parenIcon, CursorParenIcon):
                # a cursor paren icon is being deleted in favor of the binOp parens.
                # Transfer attributes and cursor from deleted paren
                deletedIconAttr = token.parenIcon.childAt('attrIcon')
                if deletedIconAttr:
                    parenIc.replaceChild(deletedIconAttr, 'attrIcon')
                    if isinstance(deletedIconAttr, EntryIcon):
                        deletedIconAttr.attachedIcon = parenIc
                cursor = parenIc.window.cursor
                if cursor.type == 'icon' and cursor.icon is token.parenIcon:
                    cursorSite = 'leftArg' if cursor.site == 'argIcon' else 'attrIcon'
                    cursor.setToIconSite(parenIc, cursorSite)
        else:
            # Add parens around argument using existing icon if possible.  If not
            # (because parens were bin op auto-parens), create a new cursor paren
            if isinstance(token.ic, icon.BinOpIcon):
                parenIc = CursorParenIcon(window=token.ic.window, closed=token.closed)
                contentSite = 'argIcon'
                outIc = parenIc
            else:
                parenIc = token.parenIcon
                contentSite = token.contentSite
                outIc = token.ic
            arg = relinkExprFromTokens(token.arg, parenIc, contentSite)
            if parenIc.childAt(contentSite) is not arg:
                parenIc.replaceChild(arg, contentSite)
        # If parens were shifted and the original parens had an attribute, transfer the
        # attribute to the icon taking its place.  EntryIcon also has attachedIcon field.
        if token.endParenAttr is not None and \
                token.endParenAttr is not parenIc.childAt('attrIcon'):
            if token.endParenIc.childAt('attrIcon') is token.endParenAttr:
                token.endParenIc.replaceChild(None, 'attrIcon')
            parenIc.replaceChild(token.endParenAttr, 'attrIcon')
            if isinstance(token.endParenAttr, EntryIcon):
                token.endParenAttr.attachedIcon = parenIc
        # Move cursor and entry icon if directed
        if token.takeCursor:
            parenIc.window.cursor.setToIconSite(token.endParenAttr, 'attrIcon')
        if token.takeEntryIcon:
            entryIcon = parenIc.window.entryIcon
            if entryIcon is not None:
                eiParent = entryIcon.parent()
                eiParent.replaceChild(None, eiParent.siteOf(entryIcon))
                parenIc.replaceChild(entryIcon, 'attrIcon')
                entryIcon.attachedIcon = parenIc
                entryIcon.attachedSite = 'attrIcon'
                entryIcon.attachedSiteType = 'attrIn'
        return outIc
    print('Unrecognized token in relinkExprFromTokens')
    return None

def dumpTok(token, indent=0):
    if isinstance(token, OperandToken):
        print("   " * indent, 'Operand', token.ic.textRepr())
    elif isinstance(token, MissingArgToken):
        print("   " * indent, "Missing Arg")
    elif isinstance(token, UnaryOpToken):
        print("   " * indent, "UnaryOp", token.ic.dumpName())
        dumpTok(token.arg, indent+1)
    elif isinstance(token, BinaryOpToken):
        print("   " * indent, "BinaryOp", token.ic.dumpName())
        dumpTok(token.leftArg, indent+1)
        dumpTok(token.rightArg, indent+1)
    elif isinstance(token, OpenParenToken):
        parenType = "BinOp" if isinstance(token.parenIcon, icon.BinOpIcon) else ""
        attr = ""
        if token.endParenAttr is not None:
            attr = token.endParenAttr.dumpName() + " <- " + \
                    token.endParenIc.dumpName() + " " + str(token.endParenIc.id)
        print("   " * indent, parenType + "Paren", token.parenIcon.dumpName(), \
                token.parenIcon.id, attr)
        dumpTok(token.arg, indent+1)
