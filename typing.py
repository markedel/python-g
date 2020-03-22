# Copyright Mark Edel  All rights reserved
import icon
import compile_eval
import python_g
import winsound
import ast
from PIL import Image, ImageDraw
import re
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
VERT_ARROW_X_JUMP_MIN = 3

# Limits (pixels) for cursor movement via arrow key
VERT_ARROW_MAX_DIST = 400
HORIZ_ARROW_MAX_DIST = 600

# Weight of x distance in y cursor movement
VERT_ARROW_X_WEIGHT = 2

binaryOperators = ['+', '-', '*', '**', '/', '//', '%', '@<<', '>>', '&', '|', '^', '<',
 '>', '<=', '>=', '==', '!=']
unaryOperators = ['+', '-', '~']
emptyDelimiters = [' ', '\t', '\n', '\r', '\f', '\v']
delimitChars = emptyDelimiters + ['(', ')', ']', '}', ':', '.', ';', '@', '=', ',',
 '-', '+', '*', '/', '<', '>', '%', '&', '|', '^', '!']
keywords = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from',
 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
 'return', 'try', 'while', 'with', 'yield']

identPattern = re.compile('^[a-zA-z_][a-zA-Z_\\d]*$')
numPattern = re.compile('^([\\d_]*\\.?[\\d_]*)|'
 '(((\\d[\\d_]*\\.?[\\d_]*)|([\\d_]*\\.?[\\d_]*\\d))[eE][+-]?[\\d_]*)?$')
attrPattern = re.compile('^\\.[a-zA-z_][a-zA-z_\\d]*$')
# Characters that can legally follow a binary operator
opDelimPattern = re.compile('[a-zA-z\\d_.\\(\\[\\{\\s+-~]')

inputSiteCursorPixmap = (
    "..   ",
    ".. % ",
    ".. % ",
    ". % .",
    " % ..",
    ". % .",
    ".. % ",
    ".. % ",
    ".. % ",
    ".. % ",
    ".. % ",
    "..   ",
)
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
    ".o%%%%22%%%%",
    "o33333333%%%",
    ".o%%%%22%%%%",
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
    ".o%%%33%%%o",
    ".o%%%33%%%o",
    ".o%%3%%%%%o",
    "o%%3%%%%%o.",
    "o%3%%%%%o..",
    "o3%%oooo...",
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
        self.sites.add('attrIn', 'attrIn', 0, outSiteY + icon.ATTR_SITE_OFFSET)
        self.sites.add('seqIn', 'seqIn', 1, 1)
        self.sites.add('seqOut', 'seqOut', 1, self.height - 2)
        self.layoutDirty = True
        self.textOffset = penImage.width + icon.TEXT_MARGIN
        self.cursorPos = len(initialString)

    def restoreForUndo(self, text):
        """Undo restores all attachments and saves the displayed text.  Update the
        remaining internal state based on attachments and passed text."""
        outIcon = self.sites.output.att
        attrIcon = self.sites.attrIn.att
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
        self.layoutDirty = True

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

    def touchesPosition(self, x, y):
        if not icon.pointInRect((x, y), self.rect):
            return False
        rectLeft, rectTop = self.rect[:2]
        if x > rectLeft + self.penOffset():
            return True
        if self.attachedToAttribute():
            penImgYOff = self.sites.attrIn.yOffset - attrPenImage.height
            pixel = attrPenImage.getpixel((x - rectLeft, y - rectTop - penImgYOff))
        else:
            penImgYOff = self.sites.output.yOffset - penImage.height // 2
            pixel = penImage.getpixel((x - rectLeft, y-rectTop - penImgYOff))
        return pixel[3] > 128

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        if image is None:
            image = self.window.image
            draw = self.window.draw
        else:
            draw = ImageDraw.Draw(image)
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        boxWidth = self._width(boxOnly=True) - 1
        bgColor = PEN_OUTLINE_COLOR if colorErr else PEN_BG_COLOR
        draw.rectangle((x + self.penOffset(), y, x + self.penOffset() + boxWidth,
         y + self.height-1), fill=bgColor, outline=PEN_OUTLINE_COLOR)
        textLeft = x + self.textOffset
        draw.text((textLeft, y + icon.TEXT_MARGIN), self.text, font=icon.globalFont,
         fill=(0, 0, 0, 255))
        if self.attachedToAttribute():
            nibTop = y + self.sites.attrIn.yOffset - attrPenImage.height
            image.paste(attrPenImage, box=(x, nibTop), mask=attrPenImage)
        else:
            nibTop = y + self.sites.output.yOffset - penImage.height // 2
            image.paste(penImage, box=(x, nibTop), mask=penImage)

    def setPendingArg(self, newArg):
        self.sites.remove('pendingAttr')
        if not hasattr(self.sites, 'pendingArg'):
            x = self.sites.output.xOffset + self._width()
            y = self.sites.output.yOffset
            self.sites.add('pendingArg', 'input', x, y)
        self.sites.pendingArg.attach(self, newArg, "output")

    def pendingArg(self):
        return self.sites.pendingArg.att if hasattr(self.sites, 'pendingArg') else None

    def _setPendingAttr(self, newArg):
        self.sites.remove('pendingArg')
        if not hasattr(self.sites, 'pendingAttr'):
            x = self.sites.output.xOffset + self._width()
            y = self.sites.output.yOffset + icon.ATTR_SITE_OFFSET
            self.sites.add('pendingAttr', 'attrOut', x, y)
        self.sites.pendingArg.attach(self, newArg)

    def _pendingAttr(self):
        return self.sites.pendingArg.att if hasattr(self.sites, 'pendingAttr') else None

    def addText(self, char):
        newText = self.text[:self.cursorPos] + char + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos + len(char))

    def backspace(self):
        newText = self.text[:self.cursorPos-1] + self.text[self.cursorPos:]
        self._setText(newText, self.cursorPos-1)

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
            elif self._pendingAttr() and self.attachedSiteType == "attrOut":
                self.attachedIcon.replaceChild(self._pendingAttr(), self.attachedSite)
            else:
                self.attachedIcon.replaceChild(None, self.attachedSite)
            if self.attachedIcon.hasSite(self.attachedSite):
                self.window.cursor.setToIconSite(self.attachedIcon, self.attachedSite)
            else: # The last element of list can disappear when entry icon is removed
                seriesName, seriesIdx = icon.splitSeriesSiteId(self.attachedSite)
                newSite = icon.makeSeriesSiteId(seriesName, seriesIdx-1)
                self.window.cursor.setToIconSite(self.attachedIcon, newSite)
        else:  # Entry icon is not attached to icon (independent in window)
            if self not in self.window.topIcons:
                print("why was entry icon not in top level icon list?")
            else:
                self.window.removeTop(self)
            pendingArg = self.pendingArg()
            if pendingArg:
                self.replaceChild(None, 'pendingArg', 'output')
                self.window.insertTopLevel(pendingArg, pos=self.rect[:2])
                pendingArg.layoutDirty = True
                self.window.cursor.setToIconSite(pendingArg, "output")
            elif self._pendingAttr():
                pendingAttr = self._pendingAttr()
                self.replaceChild(None, 'pendingAttr', 'attrIn')
                self.window.insertTopLevel(pendingAttr, pos=self.rect[:2])
                pendingAttr.layoutDirty = True
                self.window.cursor.setToIconSite(pendingAttr, "attrIn")
            else:
                self.window.cursor.setToWindowPos((self.rect[0], self.rect[1]))
        self.window.entryIcon = None

    def _setText(self, newText, newCursorPos):
        oldWidth = self._width()
        parseResult = parseEntryText(newText, self.attachedToAttribute(), self.window)
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
                self.layoutDirty = True
            return
        elif parseResult == "comma":
            if self.commaEntered(self.attachedIcon, self.attachedSite):
                if self.pendingArg() is None:
                    if self.attachedIcon is not None:
                        self.attachedIcon.replaceChild(None, self.attachedSite)
                    self.window.entryIcon = None
                else:
                    if cursor.type is "icon" and cursor.siteType == "input" and \
                            cursor.icon.childAt(cursor.site) is None:
                        cursor.icon.replaceChild(self.pendingArg(), cursor.site)
                        if self.attachedIcon is not None:
                            self.attachedIcon.replaceChild(None, self.attachedSite)
                        self.setPendingArg(None)
                        self.window.entryIcon = None
            else:
                beep()
            return
        elif parseResult == "endBracket":
            if self.pendingArg() and self.attachedSiteType == "input":
                self.attachedIcon.replaceChild(self.pendingArg(), self.attachedSite)
            else:
                self.attachedIcon.replaceChild(None, self.attachedSite, leavePlace=True)
            self.window.entryIcon = None
            cursor.setToIconSite(self.attachedIcon, self.attachedSite)
            if not cursor.movePastEndBracket():
                beep()
            return
        elif parseResult == "endParen":
            matchingParen = self.findOpenParen(self.attachedIcon, self.attachedSite)
            if matchingParen is None:
                # Maybe user was just trying to move past an existing paren by typing it
                if self.pendingArg() and self.attachedSiteType == "input":
                    self.attachedIcon.replaceChild(self.pendingArg(), self.attachedSite)
                else:
                    self.attachedIcon.replaceChild(None, self.attachedSite,
                     leavePlace=True)
                self.window.entryIcon = None
                cursor.setToIconSite(self.attachedIcon, self.attachedSite)
                if not cursor.movePastEndParen():
                    beep()
            elif matchingParen.__class__ is CursorParenIcon and \
             matchingParen is self.attachedIcon:
                # Empty tuple
                parent = matchingParen.parent()
                tupleIcon = icon.TupleIcon(window=self.window)
                if parent is None:
                    self.window.replaceTop(matchingParen, tupleIcon)
                    tupleIcon.layoutDirty = True
                else:
                    parent.replaceChild(tupleIcon, parent.siteOf(matchingParen))
                if self.pendingArg():
                    self.attachedIcon = tupleIcon
                    self.attachedSite = "attrIcon"
                    self.attachedSiteType = "attrOut"
                    tupleIcon.replaceChild(self, "attrIcon")
                else:
                    self.window.entryIcon = None
                    self.window.cursor.setToIconSite(tupleIcon, "attrIcon")
            else:
                if matchingParen.__class__ is icon.TupleIcon and matchingParen.noParens:
                    # matchingParen is a tuple at the top level with no parens.  Add them
                    matchingParen.restoreParens()
                else:
                    # matchingParen is an cursor paren, close it
                    matchingParen.close()
                if self.pendingArg():
                    self.attachedIcon.replaceChild(None, self.attachedSite)
                    self.attachedIcon = matchingParen
                    self.attachedSite = "attrIcon"
                    self.attachedSiteType = "attrOut"
                    matchingParen.replaceChild(self, "attrIcon")
                else:
                    self.attachedIcon.replaceChild(None, self.attachedSite)
                    self.window.entryIcon = None
                    cursor.setToIconSite(matchingParen, "attrIcon")
            return
        elif parseResult == "makeFunction":
            if not self.makeFunction(self.attachedIcon):
                beep()
            return
        # Parser emitted an icon.  Splice it in to the hierarchy
        ic, remainingText = parseResult
        if remainingText is None or remainingText in emptyDelimiters:
            remainingText = ""
        snapLists = ic.snapLists()
        if self.attachedIcon is None:
            self.window.insertTopLevel(ic, pos=self.rect[:2])
            if self not in self.window.topIcons:
                print("why was entry icon not in top level icon list?")
            else:
                self.window.removeTop(self)
            ic.layoutDirty = True
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            else:
                cursor.setToIconSite(ic, "attrIcon")
        elif ic.__class__ is icon.AssignIcon:
            if not self.insertAssign(ic):
                beep()
                return
        elif self.attachedToAttribute():
            # Entry icon is attached to an attribute site (ic is operator or attribute)
            self.appendOperator(ic)
        elif self.attachedSiteType == "input":
            # Entry icon is attached to an input site
            self.attachedIcon.replaceChild(ic, self.attachedSite)
            if "input" in snapLists:
                cursor.setToIconSite(ic, snapLists["input"][0][2])  # First input site
            elif "attrOut in snapLists":
                cursor.setToIconSite(ic, snapLists["attrOut"][0][2])
            else:
                cursor.removeCursor()
        # If entry icon has pending arguments, try to place them.  Code does its best
        # to place the cursor at the most reasonable spot.  If vacant, place pending
        # args there
        if self.pendingArg() is not None and remainingText == "":
            if cursor.type is "icon" and cursor.siteType == "input" and \
             cursor.icon.childAt(cursor.site) is None:
                cursor.icon.replaceChild(self.pendingArg(), cursor.site)
                self.setPendingArg(None)
        # If the entry icon can go away, remove it and we're done
        if self.pendingArg() is None and remainingText == "":
            self.window.entryIcon = None
            return
        # There is remaining text or pending arguments.  Restore the entry icon
        if cursor.type is not "icon":  # I don't think this can happen
            print('Cursor type not icon in _setText')
            return
        self.attachedIcon = cursor.icon
        self.attachedSite = cursor.site
        self.attachedSiteType = cursor.icon.typeOf(cursor.site)
        self.attachedIcon.replaceChild(self, self.attachedSite)
        cursor.setToEntryIcon()
        self.layoutDirty = True
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
            tupleIcon = icon.TupleIcon(window=self.window)
            tupleIcon.insertChildren([None, self.pendingArg()], "argIcons", 0)
            self.setPendingArg(None)
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 0)
            if self not in self.window.topIcons:
                print("why was entry icon not in top level icon list?")
            else:
                self.window.removeTop(self)
            self.window.insertTopLevel(tupleIcon, pos=self.rect[:2])
            return True
        siteType = onIcon.typeOf(site)
        if onIcon.__class__ in (icon.FnIcon, icon.ListIcon, icon.TupleIcon,
         icon.AssignIcon) and siteType == "input":
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
            tupleIcon = icon.TupleIcon(window=self.window)
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
            return True
        if onIcon.__class__ is icon.BinOpIcon and site == "leftArg":
            leftArg = None
            rightArg = onIcon
            if onIcon.leftArg() is self:
                onIcon.replaceChild(self.pendingArg(),"leftArg")
                self.setPendingArg(None)
                self.attachedIcon = None
        elif onIcon.__class__ is icon.BinOpIcon and site == "rightArg":
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
            leftArg = onIcon
            rightArg = None
        child = onIcon
        for parent in onIcon.parentage():
            if parent.__class__ in (icon.FnIcon, icon.ListIcon, icon.TupleIcon,
             icon.AssignIcon):
                onIcon.layoutDirty = True
                childSite = parent.siteOf(child)
                parent.replaceChild(leftArg, childSite, leavePlace=True)
                seriesName, seriesIndex = icon.splitSeriesSiteId(childSite)
                parent.insertChild(rightArg, seriesName, seriesIndex + 1)
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
                return True
            if parent.__class__ is not icon.BinOpIcon:
                return False
            if parent.hasParens:
                return False
            # Parent is a binary op icon without parens, and site is one of the two
            # input sites
            if parent.leftArg() is child:  # Insertion was on left side of operator
                parent.replaceChild(rightArg, "leftArg")
                if parent.leftArg() is None:
                    self.window.cursor.setToIconSite(parent, "leftArg")
                    cursorPlaced = True
                rightArg = parent
            elif parent.rightArg() is child:   # Insertion was on right side of operator
                parent.replaceChild(leftArg, "rightArg")
                if parent.rightArg() is None:
                    self.window.cursor.setToIconSite(parent, "rightArg")
                    cursorPlaced = True
                leftArg = parent
            else:
                print('Unexpected site attachment in "commaEntered" function')
                return False
            child = parent
        # Reached top level.  Create Tuple
        tupleIcon = icon.TupleIcon(window=self.window, noParens=True)
        self.window.replaceTop(child, tupleIcon)
        tupleIcon.insertChildren([leftArg, rightArg], "argIcons", 0)
        if not cursorPlaced:
            self.window.cursor.setToIconSite(tupleIcon, "argIcons", 1)
        return True

    def findOpenParen(self, fromIcon, fromSite):
        """Find a matching open paren, and if necessary, relocate it among coincident
        sites to match a close paren at fromIcon, fromSite"""
        matchingParen = searchForOpenCursorParen(fromIcon, fromSite)
        if matchingParen is None:
            return None
        if matchingParen is fromIcon or matchingParen.__class__ is icon.TupleIcon:
            return matchingParen
        # Find the lowest common ancestor of the start paren and end location, looking at
        # the visually-equivalent coincident sites to which the open-paren can be moved.
        commonAncestor = tryMoveOpenParenDown(matchingParen, fromIcon)
        if commonAncestor is matchingParen:
            return matchingParen  # No re-parenting is necessary
        if commonAncestor is None:
            # No common ancestor found at the open paren or more local: broaden the scope
            commonAncestor = tryMoveOpenParenUp(matchingParen, fromIcon)
        if commonAncestor is None:
            # Failed to find a common ancestor.  Give up
            return None
        # The matching open-paren needs re-parenting to match the close-paren
        oldArg = matchingParen.sites.argIcon.att
        matchingParen.replaceChild(None, "argIcon")
        oldParenParent = matchingParen.parent()
        if oldParenParent is None:
            self.window.replaceTop(matchingParen, oldArg)
        else:
            oldParenParent.replaceChild(oldArg, oldParenParent.siteOf(matchingParen))
        newParenParent = commonAncestor.parent()
        if newParenParent is None:
            self.window.replaceTop(commonAncestor, matchingParen)
        else:
            newParenParent.replaceChild(matchingParen, newParenParent.siteOf(commonAncestor))
        matchingParen.replaceChild(commonAncestor, "argIcon")
        return matchingParen

    def makeFunction(self, ic):
        if ic.__class__ is not icon.IdentifierIcon:
            return False
        parent = ic.parent()
        fnIcon = icon.FnIcon(ic.name, window=self.window)
        fnIcon.layoutDirty = True
        if parent is None:
            self.window.replaceTop(ic, fnIcon)
        else:
            parent.replaceChild(fnIcon, parent.siteOf(ic))
        self.window.cursor.setToIconSite(fnIcon, "argIcons", 0)
        return True

    def appendOperator(self, newOpIcon):
        """The entry icon is attached to an attribute site and a binary operator has been
        entered.  Stitch the operator in to the correct level with respect to the
        surrounding binary operators, and move the cursor to the empty operand slot."""
        argIcon = self.attachedIcon
        entryIconParents = self.parentage()
        argIcon.replaceChild(None, self.attachedSite)
        leftArg = argIcon
        rightArg = None
        childOp = argIcon
        stopAtParens = False
        # Walk up the hierarchy of binary operations, breaking each one in to left and
        # right operands for the new operation.  Stop when the parent operation has
        # lower precedence, or is not a binary operation.  Also stop if the parent
        # operation has equal precedence, and the associativity of the operation matches
        # the side of the operation on which the insertion is being made.
        for op in entryIconParents[1:]:
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
        newOpIcon.layoutDirty = True
        newOpIcon.replaceChild(leftArg, leftSite)
        newOpIcon.replaceChild(rightArg, rightSite)

    def insertAssign(self, assignIcon):
        attIconClass = self.attachedIcon.__class__
        if not (attIconClass is icon.AssignIcon or attIconClass is icon.TupleIcon and
         self.attachedIcon.noParens or self.attachedToAttribute() and attIconClass in
         (icon.IdentifierIcon, icon.TupleIcon, icon.ListIcon)):
            return False
        if self.attachedIcon in self.window.topIcons and self.attachedToAttribute():
            # The cursor is attached to an attribute of a top-level icon of a type
            # appropriate as a target. Insert assignment icon and make it the target.
            self.attachedIcon.replaceChild(None, self.attachedSite)
            assignIcon.replaceChild(self.attachedIcon, "targets0_0")
            self.window.replaceTop(self.attachedIcon, assignIcon)
            self.window.cursor.setToIconSite(assignIcon, "values_0")
            return True
        topParent = self.attachedIcon.topLevelParent()
        if topParent.__class__ is icon.TupleIcon and topParent.noParens:
            # There is a no-paren tuple at the top level waiting to be converted in to an
            # assignment statement.  Do the conversion.
            self.attachedIcon.replaceChild(None, self.attachedSite)
            if topParent is self.attachedIcon:
                insertSiteId = self.attachedSite
            else:
                insertSiteId = topParent.siteOf(self.attachedIcon, recursive=True)
            targetIcons = topParent.argIcons()
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
        if topParent.__class__ is icon.AssignIcon:
            # There is already an assignment icon.  Add a new clause, splitting the
            # target list at the entry location.  (assignIcon is thrown away)
            self.attachedIcon.replaceChild(None, self.attachedSite)
            if topParent is self.attachedIcon:
                insertSiteId = self.attachedSite
            else:
                insertSiteId = topParent.siteOf(self.attachedIcon, recursive=True)
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

    def calcLayout(self):
        width = self._width() - (1 if self.attachedToAttribute() else 2)
        siteOffset = self.height // 2
        if self.attachedSite and self.attachedSite == "attrIcon":
            siteOffset += icon.ATTR_SITE_OFFSET
        layout = icon.Layout(self, width, self.height, siteOffset)
        if self.pendingArg():
            pendingArgLayout = self.pendingArg().calcLayout()
            layout.addSubLayout(pendingArgLayout, 'pendingArg', width, 0)
            width += pendingArgLayout.width
        elif self._pendingAttr():
            pendingAttrLayout = self._pendingAttr().calcLayout()
            layout.addSubLayout(pendingAttrLayout, 'pendingAttr', width,
             icon.ATTR_SITE_OFFSET)
            width += pendingAttrLayout.width
        layout.width = width + ENTRY_ICON_GAP
        return layout

    def clipboardRepr(self, offset):
        return None

    def execute(self):
        raise icon.IconExecException(self, "Can't execute text-entry field")

    def attachedToAttribute(self):
        return self.attachedSite is not None and \
         self.attachedSiteType in ("attrIn", "attrOut")

    def penOffset(self):
        penImgWidth = attrPenImage.width if self.attachedToAttribute() else penImage.width
        return penImgWidth - PEN_MARGIN

class CursorParenIcon(icon.Icon):
    def __init__(self, window=None, location=None):
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

    def draw(self, image=None, location=None, clip=None, colorErr=False):
        needSeqSites = self.parent() is None and image is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or image is not None)
        if image is None:
            image = self.window.image
        if location is None:
            location = self.rect[:2]
        if self.cachedImage is None:
            self.cachedImage = Image.new('RGBA', (icon.rectWidth(self.rect),
             icon.rectHeight(self.rect)), color=(0, 0, 0, 0))
            textWidth, textHeight = icon.globalFont.getsize("(")
            bodyLeft = icon.outSiteImage.width - 1
            draw = ImageDraw.Draw(self.cachedImage)
            width = textWidth + 2 * icon.TEXT_MARGIN
            height = textHeight + 2 * icon.TEXT_MARGIN
            draw.rectangle((bodyLeft, 0, bodyLeft + width, height),
             fill=icon.ICON_BG_COLOR, outline=icon.OUTLINE_COLOR)
            if needSeqSites:
                icon.drawSeqSites(self.cachedImage, bodyLeft, 0, height+1)
            outSiteX = self.sites.output.xOffset
            outSiteY = self.sites.output.yOffset
            outImageY = outSiteY - icon.outSiteImage.height // 2
            if needOutSite:
                self.cachedImage.paste(icon.outSiteImage, (outSiteX, outImageY),
                 mask=icon.outSiteImage)
            inSiteX = self.sites.argIcon.xOffset
            inImageY = self.sites.argIcon.yOffset - icon.inSiteImage.height // 2
            self.cachedImage.paste(icon.inSiteImage, (inSiteX, inImageY))
            textLeft = bodyLeft + icon.TEXT_MARGIN + 1
            draw.text((textLeft, icon.TEXT_MARGIN), "(",
             font=icon.globalFont, fill=(180, 180, 180, 255))
            if self.closed:
                bodyWidth, bodyHeight = self.bodySize
                endParenLeft = self.cachedImage.width - bodyWidth - 1
                draw.rectangle((endParenLeft, 0, endParenLeft + bodyWidth,
                 bodyHeight-1), fill=icon.ICON_BG_COLOR, outline=icon.OUTLINE_COLOR)
                textLeft = endParenLeft + icon.TEXT_MARGIN + 1
                draw.text((textLeft, icon.TEXT_MARGIN), ")",
                    font=icon.globalFont, fill=(180, 180, 180, 255))
            else:
                draw.line((bodyLeft, outSiteY, inSiteX, outSiteY),
                 fill=icon.ICON_BG_COLOR, width=3)
        icon.pasteImageWithClip(image, icon.tintSelectedImage(self.cachedImage,
         self.selected, colorErr), location, clip)

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
        self.cachedImage = None

    def calcLayout(self):
        singleParenWidth, height = self.bodySize
        width = singleParenWidth
        layout = icon.Layout(self, width, height, height//2)
        if self.sites.argIcon.att is None:
            layout.addSubLayout(None, 'argIcon', singleParenWidth-1, 0)
            width += icon.EMPTY_ARG_WIDTH
        else:
            argLayout = self.sites.argIcon.att.calcLayout()
            layout.addSubLayout(argLayout, 'argIcon', singleParenWidth-1, 0)
            width += argLayout.width - 1
        if self.closed:
            if self.sites.attrIcon.att:
                attrLayout = self.sites.attrIcon.att.calcLayout()
            else:
                attrLayout = None
            width += singleParenWidth
            layout.width = width
            layout.addSubLayout(attrLayout, 'attrIcon', width - icon.ATTR_SITE_DEPTH,
             icon.ATTR_SITE_OFFSET)
        return layout

    def textRepr(self):
        if self.sites.argIcon.att is None:
            return "None"
        return self.sites.argIcon.att.textRepr()

    def clipboardRepr(self, offset):
        if self.sites.argIcon.att is None:
            return ""
        return self.sites.argIcon.att.clipboardRepr(offset)

    def execute(self):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary paren")
        if self.sites.argIcon.att is None:
            raise icon.IconExecException(self, "Missing argument")
        return self.sites.argIcon.att.execute()

    def close(self):
        self.closed = True
        self.layoutDirty = True
        # Allow cursor to be set to the end paren before layout knows where it goes
        self.sites.add('attrIcon', 'attrOut', icon.rectWidth(self.rect),
         icon.rectHeight(self.rect) // 2 + icon.ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        self.closed = False
        self.layoutDirty = True
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
            elif self.siteType in ("attrIn", "attrOut"):
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
        cursorDrawImg = self.window.image.crop(cursorRegion)
        cursorDrawImg.paste(cursorImg, mask=cursorImg)
        self.window.drawImage(cursorDrawImg, (x, y))
        self.lastDrawRect = cursorRegion

    def processArrowKey(self, direction):
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
            self._processIconArrowKey(direction)

    def arrowKeyWithSelection(self, direction, selectedIcons):
        """Process arrow key pressed with no cursor but selected icons.  Icons have been
        unselected before this is called, but passed in via the selectedIcons parameter"""
        cursorSites = []
        for ic in selectedIcons:
            snapLists = ic.snapLists()
            for ic, (x, y), name in snapLists.get("input", []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrOut", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            outSites = snapLists.get("output", [])
            if len(outSites) > 0:
                cursorSites.append((*outSites[0][1], ic, "output"))
        if len(cursorSites) == 0:
            return  # It is possible to have icons with no viable cursor sites
        if direction == "Left":
            cursorSites.sort(key=itemgetter(0))
        elif direction == "Right":
            cursorSites.sort(key=itemgetter(0), reverse=True)
        elif direction == "Up":
            cursorSites.sort(key=itemgetter(1))
        elif direction == "Down":
            cursorSites.sort(key=itemgetter(1), reverse=True)
        x, y, ic, site = cursorSites[0]
        if site == "output":
            parent = ic.parent()
            if parent is not None:
                self.setToIconSite(parent, parent.siteOf(ic))
                return
        self.setToIconSite(ic, site)

    def _processIconArrowKey(self, direction):
        """For cursor on icon site, set new site based on arrow direction"""
        # Build a list of possible destination cursor positions, normalizing attribute
        # site positions to the center of the cursor (in/out site position).
        cursorX, cursorY = self.icon.posOfSite(self.site)
        searchRect = (cursorX-HORIZ_ARROW_MAX_DIST, cursorY-VERT_ARROW_MAX_DIST,
         cursorX+HORIZ_ARROW_MAX_DIST, cursorY+VERT_ARROW_MAX_DIST)
        cursorSites = []
        for winIcon in self.window.findIconsInRegion(searchRect):
            snapLists = winIcon.snapLists()
            for ic, (x, y), name in snapLists.get('input', []):
                cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqIn', []):
                if direction in ('Up', 'Down'):
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get('seqOut', []):
                if not hasattr(ic.sites, 'output') or direction in ('Up', 'Down'):
                    cursorSites.append((x, y, ic, name))
            for ic, (x, y), name in snapLists.get("attrOut", []):
                cursorSites.append((x, y - icon.ATTR_SITE_OFFSET, ic, name))
            if winIcon.parent() is None:
                outSites = snapLists.get("output", [])
                if len(outSites) > 0:
                    cursorSites.append((*outSites[0][1], winIcon, "output"))
        # Rank the destination positions by nearness to the current cursor position
        # in the cursor movement direction, and cull those in the wrong direction
        if self.siteType == "attrOut":
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
                        self.setToIconSite(ic, site)
                        return
        else:  # Up, Down
            # For vertical movement, do a second round of ranking.  This time add y
            # distance to weighted X distance (ranking x jumps as further away)
            bestRank = None
            for yDist, x, y, ic, site in choices:
                if yDist > VERT_ARROW_Y_JUMP_MIN:
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
            self.setToIconSite(ic, site)

    def movePastEndParen(self):
        if self.type is not "icon":
            return False
        if self.icon.__class__ is icon.TupleIcon and self.siteType == "input":
            self.setToIconSite(self.icon, "attrIcon")
            return True
        child = self.icon
        moveTo = False
        for parent in self.icon.parentage():
            if parent.__class__ is icon.BinOpIcon:
                if child is parent.leftArg():
                    return False
                if parent.hasParens:
                    moveTo = True
            elif parent.__class__ in (icon.FnIcon, icon.TupleIcon):
                moveTo = True
            elif parent.__class__ is CursorParenIcon and parent.closed:
                moveTo = True
            # If a parenthesized icon was found with cursor preceding its left paren,
            # move the cursor after that paren
            if moveTo:
                self.setToIconSite(parent, "attrIcon")
                return True
            # At this point, the cursor is still on the right side of all of the parent
            # icons, but no parens have been found yet.  Check further up the tree
            child = parent
        return False

    def movePastEndBracket(self):
        if self.type is not "icon":
            return False
        if self.icon.__class__ is icon.ListIcon and self.siteType == "input":
            self.setToIconSite(self.icon, "attrIcon")
            return True
        # Just tear intervening icons to the end bracket (was this right?)
        for parent in self.icon.parentage():
            if parent.__class__ is icon.ListIcon:
                self.setToIconSite(parent, "attrIcon")
                return True
        return False

    def erase(self):
        if self.lastDrawRect is not None and self.window.dragging is None:
            self.window.refresh(self.lastDrawRect, redraw=False)
            self.lastDrawRect = None

    def cursorAtIconSite(self, ic, site):
        """Returns True if the cursor is already at a given icon site"""
        return self.type == "icon" and self.icon == ic and self.site == site

def parseEntryText(text, forAttrSite, window):
    if len(text) == 0:
        return "accept"
    if forAttrSite:
        if attrPattern.fullmatch(text):
            return "accept"  # Legal attribute pattern
        if text in ("i", "a", "o", "an"):
            return "accept"  # Legal precursor characters to binary keyword operation
        if text in ("and", "is", "in", "or"):
            return icon.BinOpIcon(text, window), None # Binary keyword operation
        if text in ("*", "/", "@", "<", ">", "=", "!"):
            return "accept"  # Legal precursor characters to binary operation
        if text in binaryOperators:
            if text == '//':
                return icon.DivideIcon(window, floorDiv=True), None
            return icon.BinOpIcon(text, window), None
        if text == '(':
            return "makeFunction"  # Make a function from the attached icon
        if text == ')':
            return "endParen"
        if text == ']':
            return "endBracket"
        if text == ',':
            return "comma"
        op = text[:-1]
        delim = text[-1]
        if op in binaryOperators and opDelimPattern.match(delim):
            # Valid binary operator followed by allowable operand character
            if op == '/':
                return icon.DivideIcon(window, floorDiv=False), delim
            elif op == '//':
                return icon.DivideIcon(window, floorDiv=True), delim
            return icon.BinOpIcon(op, window), delim
        if op == '=':
            return icon.AssignIcon(window), delim
        return "reject"
    else:
        # input site
        if text in ('+', '-', '~', "not"):
            # Unary operator
            return icon.UnaryOpIcon(text, window), None
        if text == '(':
            return CursorParenIcon(window), None
        if text == ')':
            return "endParen"
        if text == '[':
            return icon.ListIcon(window), None
        if text == ']':
            return "endBracket"
        if text == ',':
            return "comma"
        if text == '=':
            return icon.AssignIcon(window), None
        if identPattern.fullmatch(text) or numPattern.fullmatch(text):
            return "accept"  # Nothing but legal identifier and numeric
        delim = text[-1]
        text = text[:-1]
        if opDelimPattern.match(delim):
            if text in ('+', '-', '~', "not"):
                return icon.UnaryOpIcon(text, window), delim
            if text == '(':
                return CursorParenIcon(window), delim
            if text == '[':
                return icon.ListIcon(window), delim
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
        return "reject"

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

def tryMoveOpenParenDown(cursorParen, desiredChild):
    """Cursor-parens are part of the icon hierarchy, but their meaning is partly defined
    by the end-paren that the user eventually types to close them.  When they appear in
    a site that has multiple coincident inputs, we don't really know which one the user
    intends.  This function finds the most-local icon to which the parens can be moved
    that is an ancestor to the icon holding the newly-typed end-paren.  If no such icon
    exists, it returns None."""
    ic = cursorParen
    result = None
    while True:
        for dcParent in [desiredChild, *desiredChild.parentage()]:
            if dcParent is ic:
                # It can be mated with the end-paren
                result = ic
                break
        else:
            return result
        if ic.__class__ is CursorParenIcon:
            cpChild = ic.childAt('argIcon')
        else:
            cpChild = ic.childAt(ic.hasCoincidentSite())
        if cpChild is None or not cpChild.hasCoincidentSite():
            return result
        # There is a lower coincident site, try that
        ic = cpChild

def tryMoveOpenParenUp(cursorParen, desiredChild):
    """Cursor-parens are part of the icon hierarchy, but their meaning is partly defined
    by the end-paren that the user eventually types to close them.  When they appear in
    a site that has multiple coincident inputs, we don't really know which one the user
    intends.  This function looks for icons above the cursor paren in the hierarchy, to
    which it may be moved such that it has a common ancestor with the icon holding the
    newly-typed end-paren.  If no such icon exists, it returns None."""
    while True:
        cpParent = cursorParen.parent()
        if cpParent is None:
            return None
        cpSite = cpParent.siteOf(cursorParen)
        if not icon.isCoincidentSite(cpParent, cpSite):
            return None
        # Found a visually-equivalent spot to which the open-paren could be relocated
        for dcParent in [desiredChild, *desiredChild.parentage()]:
            if dcParent is cpParent:
                # It can be mated with the end-paren
                return cpParent
        cursorParen = cpParent

def searchForOpenCursorParen(ic, site):
    """Traverse "leftward" across the expression hierarchy looking for an open paren that
    can be mated with an end-paren at the specified icon and site.  If found, return it.
    Otherwise, return None."""
    while True:
        if ic.__class__ is CursorParenIcon and not ic.closed:
            # Found an open paren
            return ic
        if ic.__class__ is icon.TupleIcon and ic.noParens:
            # Found a no-paren (top-level) tuple to parenthesize
            return ic
        if site == "all":
            siteType = "input"
        else:
            siteType = ic.typeOf(site)
        nextSite = None
        scanAll = False
        if siteType == "attrOut":
            if ic.childAt("output"):
                nextSite = "output"
            elif ic.childAt("attrIn"):
                nextSite = "attrIn"
        elif siteType == "output":
            if ic.childAt("output"):
                nextSite = "output"
        elif siteType == "input":
            # siteType is "input", but inputs inside of fns, lists, parenthesized ops are
            # all dead ends, so all we care about are arithmetic operations
            if ic.__class__ is icon.UnaryOpIcon:
                if site == "all" and ic.childAt("argIcon"):
                    nextSite = "argIcon"
                    scanAll = True
                elif ic.childAt("output"):
                    nextSite = "output"
            elif ic.__class__ is icon.BinOpIcon:
                if site == "all" and ic.childAt("rightArg"):
                    nextSite = "rightArg"
                    scanAll = True
                elif site == "rightArg" and ic.childAt("leftArg"):
                    nextSite = "leftArg"
                    scanAll = True
                elif not ic.hasParens and ic.childAt("output"):
                    nextSite = "output"
        if nextSite is None:
            return None
        nextIc = ic.childAt(nextSite)
        if scanAll:
            # Start at the right side of the icon and scan everything if it's an
            # arithmetic expression, but skip over parenthesis
            if nextIc.__class__ is icon.UnaryOpIcon or \
             nextIc.__class__ is icon.BinOpIcon and not nextIc.hasParens:
                site = "all"
            else:
                site = "output"
        else:
            site = nextIc.siteOf(ic)
        ic = nextIc
