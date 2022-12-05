from PIL import Image, ImageDraw
import re
import ast
import astunparse  # Temporary until move to Python 3.9 or later to use ast.unparse
import math
import copy
import comn
import icon
import iconlayout
import filefmt
import cursors
import entryicon

STRING_COLOR = (40, 110, 110, 255)
STRING_SPINE_COLOR = (80, 220, 220)

tripleDoubleQuoteImage = comn.asciiToImage((
 "5%.%5",
 "5%.%5",
 ".....",
 ".....",
 ".....",
 "5%.%5",
 "5%.%5",
 ".....",
 ".....",
 ".....",
 "5%.%5",
 "5%.%5"), tint=STRING_COLOR)

tripleSingleQuoteImage = comn.asciiToImage((
 "6%",
 "6%",
 "86",
 "..",
 "..",
 "6%",
 "6%",
 "86",
 "..",
 "..",
 "6%",
 "6%",
 "86"), tint=STRING_COLOR)

errPattern = re.compile(".*can't decode bytes in position (\\d*)-(\\d*)")

prefixTypes = ('f', 'b', 'u', 'r', 'rb', 'rf', 'br', 'fr')

textCursorHeight = sum(icon.globalFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

# The current string font we're using (consolas 13 font) has an exact integer width per-
# character, but not sure that's true in general, so use a floating point number just to
# be certain that if we don't introduce errors when we multiply to convert number of
# characters to pixels.  Height is always integer pixels.
charWidth = icon.textFont.getsize('a'*100)[0] / 100
charHeight = sum(icon.textFont.getmetrics())
lineSepPixels = 2
lineSpacing = charHeight + lineSepPixels

class StringIcon(icon.Icon):
    def __init__(self, initReprStr=None, window=None, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        if initReprStr is None:
            self.strType = ''
            self.quote = "'"
            self.string = ''
        else:
            self.strType, self.quote, self.string = splitSrcStr(initReprStr)
        self.wrappedString = self.string
        self.typeoverIdx = 0 if typeover and len(self.quote) == 1 else None
        self.setCursorPos('end')
        self.hasFocus = False
        self.errRanges = None
        self.strTypeCursor = None
        bodyWidth = int(charWidth * (len(self.strType) + len(self.string) + 2)) + \
            2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtHgt + 2 * icon.TEXT_MARGIN + 1
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
            bodyHeight // 2 + icon.ATTR_SITE_OFFSET)
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
            boxLeft = icon.outSiteImage.width - 1
            boxWidth = comn.rectWidth(self.rect) - boxLeft
            boxHeight = comn.rectHeight(self.rect)
            img = Image.new('RGBA', (comn.rectWidth(self.rect), boxHeight),
                color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Icon border
            draw.rectangle((boxLeft, 0, boxLeft + boxWidth - 1, boxHeight - 1),
                fill=comn.ICON_BG_COLOR, outline=comn.OUTLINE_COLOR)
            # Text, including quotes and string type if applicable
            textLeft = boxLeft + icon.TEXT_MARGIN
            textRight = boxLeft + boxWidth - icon.TEXT_MARGIN
            textTop = icon.TEXT_MARGIN
            isMultiline = len(self.wrappedString) >= 2
            quote = self.quote if len(self.quote) == 1 else ' '
            for i, line in enumerate(self.wrappedString):
                if i == 0:
                    x = textLeft
                    line = self.strType + quote + line
                else:
                    x = textLeft + int(charWidth)
                y = textTop + i * lineSpacing
                draw.text((x,y), line, fill=STRING_COLOR, font=icon.textFont)
            endQuoteColor = icon.TYPEOVER_COLOR if self.typeoverIdx is not None else \
                STRING_COLOR
            endQuoteX = textLeft + int(charWidth * (1 + len(self.wrappedString[-1])))
            if not isMultiline:
                endQuoteX += int(len(self.strType) * charWidth)
            endQuoteY = textTop + (len(self.wrappedString)-1) * lineSpacing
            draw.text((endQuoteX, endQuoteY), quote, fill=endQuoteColor,
                font=icon.textFont)
            # Hand-drawn triple-quotes (as a pixmap) since not in font
            if quote == ' ':
                quoteImg = tripleDoubleQuoteImage if self.quote == '"""' else \
                    tripleSingleQuoteImage
                imgOff = int((charWidth - quoteImg.width) / 2)
                startQuoteLeft = textLeft + int(charWidth * len(self.strType)) + imgOff
                img.paste(quoteImg, (startQuoteLeft, textTop), mask=quoteImg)
                img.paste(quoteImg, (endQuoteX + imgOff, endQuoteY), mask=quoteImg)
            # "spines"
            if isMultiline:
                spineLeft = textLeft + int(charWidth / 2)
                spineRight = textRight - int(charWidth / 2) - 2  #... why fudge needed?
                leftSpineTop = textTop + charHeight + lineSepPixels
                rightSpineTop = textTop + lineSepPixels
                leftSpineBottom = boxHeight - icon.TEXT_MARGIN - charHeight // 2
                if endQuoteX + charWidth < textRight:
                    rightSpineBottom = leftSpineBottom
                else:
                    rightSpineBottom = leftSpineBottom - lineSpacing
                draw.line((spineLeft, leftSpineTop, spineLeft, leftSpineBottom),
                    STRING_SPINE_COLOR)
                draw.line((spineRight, rightSpineTop, spineRight, rightSpineBottom),
                    icon.TYPEOVER_COLOR if self.typeoverIdx is not None else
                    STRING_SPINE_COLOR)
            # Sites
            if needSeqSites:
                icon.drawSeqSites(img, icon.outSiteImage.width-1, 0, boxHeight)
            if needOutSite:
                outX = self.sites.output.xOffset
                outY = self.sites.output.yOffset - icon.outSiteImage.height // 2
                img.paste(icon.outSiteImage, (outX, outY))
            attrX = self.sites.attrIcon.xOffset
            attrY = self.sites.attrIcon.yOffset
            img.paste(icon.attrInImage, (attrX, attrY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def focusIn(self):
        self.hasFocus = True
        return True

    def focusOut(self, placeEntryText=False):
        # Note that the focusOut method on the entry icon also sets the cursor
        # position and returns True/False based on whether it can place args.  We do
        # none of that (setting cursor position would cause a recursive call back here).
        if self.typeoverIdx is not None:
            self.typeoverIdx = None
            self.markLayoutDirty()
        self.hasFocus = False

    def removeText(self, fromPos, toPos, isFwdDelete=False):
        if not (0 <= fromPos < toPos <= len(self.string)):
            return False
        self.window.requestRedraw(self.topLevelParent().hierRect())
        removedText = self.string[fromPos:toPos]
        self.string = self.string[:fromPos] + self.string[toPos:]
        self.markLayoutDirty()
        self.errRanges = self._findStringErrors()
        if self.errRanges is not None:
            print(f'would be highlighting {self.errRanges}')
        self.window.undo.registerCallback(self.insertText, removedText, fromPos,
            isFwdDelete)
        if len(removedText) > 1:
            self.window.undo.addBoundary()
        elif isFwdDelete:
            # Since we don't know what the previously deleted character was, we can't
            # really detect runs of characters/digits/spaces, so just put a boundary
            # at every deletion that's not a letter or digit
            if not removedText.isalnum():
                self.window.undo.addBoundary()
        elif fromPos > 0:
            prevChar = self.string[fromPos - 1]
            if not (prevChar.isalnum() and removedText.isalnum() or
                    prevChar.isspace() and removedText.isspace()):
                self.window.undo.addBoundary()
        self.cursorPos = fromPos
        return True

    def insertText(self, text, insertPos, undoFwdDelete=False):
        if text == "" or insertPos < 0 or insertPos > len(self.string):
            return False
        self.window.requestRedraw(self.topLevelParent().hierRect())
        self.string = self.string[:insertPos] + text + self.string[insertPos:]
        self.markLayoutDirty()
        self.errRanges = self._findStringErrors()
        if self.errRanges is not None:
            print(f'would be highlighting {self.errRanges}')
        self.markLayoutDirty()
        # Add an undo boundary *before* registering the operation for undo, because we
        # want the boundaries mainly between words, and there's no way to tell where the
        # end of a run of characters is, until the user types something else.
        if insertPos > 0:
            prevChar = self.string[insertPos-1]
            if prevChar.isalnum() and not (text.isalnum() or text.isspace()) or \
                    prevChar.isspace() and not text.isspace() or \
                    not text.isalnum() and not text.isspace():
                self.window.undo.addBoundary()
        self.window.undo.registerCallback(self.removeText, insertPos,
            insertPos + len(text))
        if len(text) > 1 or not (text.isspace() or text.isalnum()):
            # Multi-character (currently only pastes) and punctuation/delimiter inserts
            # are always worthy of undo
            self.window.undo.addBoundary()
        if undoFwdDelete:
            self.cursorPos = insertPos
        else:
            self.cursorPos = insertPos + len(text)
        return True

    def addText(self, text):
        """Add a character or text at the cursor."""
        if text == self.quote[0] and self.cursorPos == len(self.string) and (
                self.typeoverIdx is not None or (len(self.quote) == 3 and
                self.string[-2:] == self.quote[:2])):
            # Typeover or third quote in a row typed in triple-quote string: focus
            # out of the string and move the cursor to the site on the right.  Note
            # special case for entry icon (see arrowAction for explanation).
            if self.typeoverIdx is not None:
                self.typeoverIdx = None
            else:
                self.string = self.string[:-2]
            if isinstance(self.childAt('attrIcon'), entryicon.EntryIcon):
                self.window.cursor.setToText(self.childAt('attrIcon'))
            else:
                self.window.cursor.setToIconSite(self, 'attrIcon')
            self.markLayoutDirty()
            return
        if self.cursorPos < 0:
            # Cursor is in the quote / string-type field
            text = text.lower()
            if text in ('"', "'"):
                if self.quote == text:
                    self._changeQuoteType(text * 3)
                else:
                    self._changeQuoteType(text)
            elif text == 'u':
                if self.strType == 'u':
                    self._changeStrType('')
                else:
                    self._changeStrType('u')
            elif text == 'b':
                if self.strType == 'b':
                    self._changeStrType('')
                elif self.strType == 'br':
                    self._changeStrType('b')
                elif self.strType == 'r':
                    self._changeStrType('br')
                else:
                    self._changeStrType('b')
            elif text == 'f':
                if self.strType == 'f':
                    self._changeStrType('')
                elif self.strType == 'fr':
                    self._changeStrType('f')
                elif self.strType == 'r':
                    self._changeStrType('fr')
                else:
                    self._changeStrType('f')
            elif text == 'r':
                if self.strType == 'r':
                    self._changeStrType('')
                elif self.strType == 'b':
                    self._changeStrType('br')
                elif self.strType == 'br':
                    self._changeStrType('r')
                elif self.strType == 'f':
                    self._changeStrType('fr')
                elif self.strType == 'fr':
                    self._changeStrType('f')
                else:
                    self._changeStrType('r')
            elif text == ' ':
                self._changeStrType('')
            else:
                cursors.beep()
            return
        self.insertText(text, self.cursorPos)

    def processEnterKey(self, evt):
        if self.cursorPos < 0:
            return
        if len(self.quote) == 3:
            self.insertText('\n', self.cursorPos)
        else:
            self.insertText('\\n', self.cursorPos)

    def click(self, evt):
        self.window.cursor.erase()
        self.becomeEntryIcon(clickPos=(evt.x, evt.y))

    def pointInTextArea(self, x, y):
        if not self.hasFocus:
            # Unlike entry icons, we don't allow direct click to type, must (Alt+click)
            return False
        left, top, right, bottom = self.rect
        left += icon.outSiteImage.width - 1
        top += 2
        bottom -= 2
        right -= 2
        return left < x < right and top < y < bottom

    def setTypeover(self, idx, site=None):
        if idx == self.typeoverIdx:
            return True
        self.drawList = None  # Force redraw
        if idx is None or idx > 2:
            self.typeoverIdx = None
            return False
        self.typeoverIdx = idx
        return True

    def typeoverCursorPos(self):
        x = icon.outSiteImage.width - 1 + icon.TEXT_MARGIN + icon.textFont.getsize(
            self.strType + self.quote + self.string + self.quote[:self.typeoverIdx])[0]
        y = self.sites.output.yOffset
        return x, y

    def typeoverSites(self, allRegions=False):
        if self.typeoverIdx is None:
            return [] if allRegions else (None, None, None, None)
        retVal = 'output', 'attrIcon', self.quote, self.typeoverIdx
        return [retVal] if allRegions else retVal

    def backspaceInText(self, evt=None):
        if self.cursorPos == 0:
            # Cursor is next to quote: edit quote and string type, unless the string is
            # empty, then delete the whole thing
            if self.string == '':
                removeEmptyAttrOnlyIcon(self)
            else:
                self.cursorPos = -1
        elif self.cursorPos <= -1:
            self.cursorPos = 0
            self.focusOut()
            self.window.cursor.setToBestCoincidentSite(self, 'output')
            self.window.undo.addBoundary()
        else:
            self.removeText(self.cursorPos-1, self.cursorPos)

    def forwardDelete(self, evt=None):
        self.removeText(self.cursorPos, self.cursorPos+1, isFwdDelete=True)

    def arrowAction(self, direction):
        cursor = self.window.cursor
        cursor.erase()
        if direction == "Left":
            if self.cursorPos <= 0:
                # Move the cursor out of the string icon
                parent = self.parent()
                if parent is None:
                    self.window.cursor.setToIconSite(self, 'output')
                else:
                    self.window.cursor.setToIconSite(parent, parent.siteOf(self))
            else:
                self.cursorPos -= 1
        elif direction == "Right":
            if self.cursorPos == len(self.string):
                # Move cursor out of string icon.  Note the special case for attached
                # entry icon where we generally avoid the site to the left in lexical
                # traversal, particularly when inserting a string because the user needs
                # to continue their insertion to rejoin the code they've orphaned.
                if isinstance(self.childAt('attrIcon'), entryicon.EntryIcon):
                    self.window.cursor.setToText(self.childAt('attrIcon'))
                else:
                    self.window.cursor.setToIconSite(self, 'attrIcon')
            elif self.cursorPos < 0:
                self.cursorPos = 0
            else:
                self.cursorPos += 1
        elif direction == 'Up':
            x, y = self.cursorWindowPos()
            y -= lineSpacing
            self.window.cursor.erase()
            if self.becomeEntryIcon(clickPos=(x, y))[0] is None:
                cursors.beep()
        elif direction == 'Down':
            x, y = self.cursorWindowPos()
            y += lineSpacing
            self.window.cursor.erase()
            if self.becomeEntryIcon(clickPos=(x, y))[0] is None:
                cursors.beep()
        self._updateTypeoverState()
        cursor.draw()

    def doLayout(self, outSiteX, outSiteY, layout):
        bodyWidth, bodyHeight = layout.bodySize
        rectWidth = bodyWidth + icon.outSiteImage.width - 1
        top = outSiteY - bodyHeight // 2
        self.rect = (outSiteX, top, outSiteX + rectWidth, top + bodyHeight)
        self.sites.attrIcon.xOffset = rectWidth - 1 - icon.ATTR_SITE_DEPTH
        self.sites.attrIcon.yOffset = bodyHeight // 2 + icon.ATTR_SITE_OFFSET
        self.sites.output.yOffset =  bodyHeight // 2
        self.sites.seqOut.yOffset = bodyHeight - 2
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.wrappedString = layout.wrappedString
        self.drawList = None  # Draw or undraw sequence sites ... refine when sites added
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.attrIcon.att is None:
            attrLayouts = [None]
        else:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        stringLayouts = self._enumerateStringLayouts()
        layouts = []
        for attrLayout, stringLayout in iconlayout.allCombinations((attrLayouts,
                stringLayouts)):
            layout = copy.copy(stringLayout)
            layout.addSubLayout(attrLayout, 'attrIcon', stringLayout.width - 1,
                icon.ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return repr(self.string) + icon.attrTextRepr(self)

    def dumpName(self):
        """Give the icon a name to be used in text dumps."""
        if len(self.string) < 20:
            return self.strType + self.quote + self.string + self.quote
        else:
            return self.strType + self.quote + self.string[:20] + '...'

    def backspace(self, siteId, evt):
        if siteId != 'attrIcon':
            return
        self.cursorPos = len(self.string)
        self.window.cursor.setToText(self)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            cursorTextIdx, cursorWindowPos = self.cursorInText(clickPos)
            if cursorTextIdx is None:
                return None, None
            # CursorPos index is 0 at start of string body, negative for quote and type
            self.setCursorPos(cursorTextIdx)
            return self, cursorWindowPos
        if siteAfter is None or siteAfter == 'attrIcon':
            return self
        return None

    def cursorInText(self, clickPos):
        """Determine if a given window x,y position (clickPos) is within the text area
        of the string.  If so, return the (cursor) position within the text closest to
        clickPos, and the x,y window coordinate location for that cursor (y center).  If
        the clickpos is not within the clickable area, return (None, None)."""
        left = self.rect[0] + icon.TEXT_MARGIN + icon.outSiteImage.width - 1
        top = self.rect[1] + icon.TEXT_MARGIN
        right = self.rect[2] - icon.TEXT_MARGIN
        bottom = self.rect[3] - icon.TEXT_MARGIN
        if not icon.pointInRect(clickPos, (left, top, right, bottom)):
            return None, None
        clickX, clickY = clickPos
        clickX -= left
        clickY -= top
        lineNum = clickY // lineSpacing
        cursorY = top + lineNum * lineSpacing + lineSpacing // 2
        cursorIdx = 0
        for i in range(lineNum):
            cursorIdx += len(self.wrappedString[i])
        charNum = round(clickX / charWidth) - 1  # -1 for is quote or line border
        if lineNum == 0:
            charNum -= len(self.strType)
        elif charNum < 0:
            charNum = 0  # clickPos is on line border
        if charNum >= len(self.wrappedString[lineNum]) and \
                lineNum < len(self.wrappedString):
            # clickPos is right of the line: move cursor to the last allowed position
            charNum = len(self.wrappedString[lineNum]) - 1
        cursorIdx += charNum
        if cursorIdx < 0:
            cursorIdx = -1  # String type/quote area has only one cursor pos
            cursorX = left + int(charWidth * (len(self.strType) + 1))
        else:
            cursorX = left + int(charWidth * (charNum + 1))
        return cursorIdx, (cursorX, cursorY)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText()
        strText = self.strType + self.quote + self.string + self.quote
        if len(self.strType) == 3:
            contNeeded = False
        text.addQuotedString(None, strText, contNeeded, parentBreakLevel + 1)
        return icon.addAttrSaveText(text, self, parentBreakLevel, contNeeded, export)

    def createAst(self):
        strText = self.strType + self.quote + self.string + self.quote
        try:
            modAst = ast.parse(strText)
        except Exception as parseErr:
            raise icon.IconExecException(self, str(parseErr))
        strAst = modAst.body[0].value
        strAst.lineno = self.id
        strAst.col_offset = 0
        return strAst

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, string=self.string)

    def compareData(self, data):
        # I hope this is sufficiently fast for large structures.  If not we need to
        # cache a copy of the created object.
        if self.strType in ('f', 'r', 'fr'):
            # These string types never occur in a string object because they are
            # converted at parse/compile time.
            return False
        strText = self.strType + self.quote + self.string + self.quote
        try:
            strObj = ast.literal_eval(strText)
        except:
            return False
        return data == strObj and self.sites.attrIcon.att is None

    def textEntryHandler(self, entryIc, text, onAttr):
        if entryIc.parent() is self and self.string == '' and len(self.quote) == 1 and \
                text in ('"', "'"):
            return StringIcon(self.quote*6, window=self.window, typeover=True), None
        return None

    def textCursorImage(self):
        if self.cursorPos >= 0:
            return textCursorImage
        # Construct block cursor to surround string type and quote fields
        if self.strTypeCursor is not None:
            return self.strTypeCursor
        width = int((len(self.strType) + 1) * charWidth) + 2 * (icon.TEXT_MARGIN - 1) + 1
        height = charHeight + 2 * (icon.TEXT_MARGIN - 1) + 1
        self.strTypeCursor = Image.new('RGBA', (width, height))
        ImageDraw.Draw(self.strTypeCursor).rectangle((0, 0, width - 1, height - 1),
            outline=(0, 0, 0, 255), fill=(0, 0, 0, 0))
        return self.strTypeCursor

    def cursorWindowPos(self):
        x, y = self.rect[:2]
        x += icon.outSiteImage.width - 1 + icon.TEXT_MARGIN
        if self.cursorPos < 0:
            x -= 1
        else:
            lineCount = 0
            charCount = 0
            charsInLine = 0
            for i, line in enumerate(self.wrappedString):
                lineCount = i
                if charCount + len(line) == self.cursorPos and \
                        i != len(self.wrappedString) - 1:
                    # Cursor is between lines, put it at the start of the lower one
                    lineCount += 1
                    charsInLine = 0
                elif charCount + len(line) >= self.cursorPos:
                    charsInLine = self.cursorPos - charCount
                    if i == 0:
                        charsInLine += len(self.strType)
                    break
                charCount += len(line)
            x += int((charsInLine + 1) * charWidth)
            y += lineCount * lineSpacing
        y += charHeight // 2
        return x, y

    def setCursorPos(self, pos):
        if pos == 'end':
            self.cursorPos = len(self.string)
        else:
            self.cursorPos = max(-1, min(len(self.string), pos))
        self._updateTypeoverState()

    def _updateTypeoverState(self):
        if self.typeoverIdx is not None and not self.cursorPos == len(self.string):
            self.typeoverIdx = None
            self.markLayoutDirty()

    def _changeQuoteType(self, newQuote):
        oldQuote = self.quote
        if newQuote == oldQuote:
            return
        if len(oldQuote) < len(newQuote):
            # Convert single quote to triple quote
            newString = replaceEscapeChar(self.string, '\\' + oldQuote, oldQuote)
            newString = replaceEscapeChar(newString, '\\n', '\n')
        elif len(newQuote) < len(oldQuote):
            # Convert triple quote to single quote
            newString = replaceEscapeChar(self.string, newQuote, '\\' + newQuote)
            newString = replaceEscapeChar(newString, '\n', '\\n')
        else:
            newString = replaceEscapeChar(self.string, newQuote, '\\' + newQuote)
            newString = replaceEscapeChar(newString, '\\' + oldQuote, oldQuote)
        self.string = newString
        self.quote = newQuote
        self.markLayoutDirty()
        self.strTypeCursor = None
        self.window.undo.registerCallback(self._changeQuoteType, oldQuote)
        self.window.undo.addBoundary()

    def _changeStrType(self, newStrType):
        oldStrType = self.strType
        if newStrType == oldStrType:
            return
        self.strType = newStrType
        self.markLayoutDirty()
        self.strTypeCursor = None
        self.window.undo.registerCallback(self._changeStrType, oldStrType)
        self.window.undo.addBoundary()

    def _findStringErrors(self):
        """Feed string toCheck, which should include quotes and string type, through
        the Python parser to find anything that it does not like.  Returns a list of
        character ranges that were flagged.  If no errors were found, return None.  It is
        also (probably) possible to return an empty list, indicating that there was an
        error, but it couldn't be processed in to character ranges."""
        # The temporary hack, here, is that for Python 3.8, parsing the error message
        # text is the only way to extract the range (Python 3.10 provides this data in
        # the offset and end_offset fields, so at minimum, this should be fixed after
        # the move to Python 3.11, and of course, the eventual plan is to support actual
        # icons in f-strings, which will also remove most of the need for using error
        # data to figure out what should be colored bad in a given string.)
        errRanges = None
        start = 0
        strOffset = len(self.strType) + len(self.quote)
        while True:
            try:
                ast.parse(self.strType + self.quote + self.string[start:] + \
                    self.quote, '', 'eval')
            except SyntaxError as se:
                if errRanges is None:
                    errRanges = []
                errMatch = errPattern.match(str(se))
                if errMatch is None:
                    # Oops, there are so many different errors, here and almost none of
                    # them provide ranges.  I believe Python 3.11 will provide column
                    # ranges for most errors, which hopefully extend within the string
                    return errRanges
                errFrom = int(errMatch.group(1)) + start - strOffset
                errTo = int(errMatch.group(2)) + start - strOffset
                errRanges.append((errFrom, errTo))
                if errTo <= start:
                    return errRanges
                if errTo >= len(self.string) - 1:
                    return errRanges
                start = errTo + 1
                continue
            return errRanges
        return errRanges

    def _enumerateStringLayouts(self):
        """Return a list of possible layouts for the string.  Layout includes a special
        field called wrappedString, which breaks self.string into individual lines."""
        # Calculate the optimum (minimum) width (in characters) for each height (in
        # lines).  We assume we're using a fixed-width font, so characters are easier
        # until we need pixels for the layout structures.
        if len(self.strType) == 0:
            quote = ''
        elif len(self.strType) == 1:
            quote = self.quote if len(self.quote) == 1 else 'x'
        else:
            quote = self.strType[1] + (self.quote if len(self.quote) == 1 else 'x')
        text = quote + self.string
        currentHeight = 0
        startWidth = len(text)
        minWidth = min(int(math.sqrt(startWidth)), (self.window.margin // charWidth) // 2)
        minWidth = max(min(15, startWidth), minWidth)
        words = _splitWords(text)
        if len(words) == 0:
            widths = [len(text)]
            lineLists = [[text]]
        else:
            widths = []
            lineLists = []
            for width in range(len(text)+1, minWidth-1, -1):
                lines = _wordWrap(words, width)
                if len(lines) > currentHeight:
                    for i in range(len(lines) - currentHeight):
                        widths.append(None)
                        lineLists.append(None)
                    currentHeight = len(lines)
                widths[currentHeight - 1] = width
                lineLists[currentHeight - 1] = lines
        # Create layout structures for each of the optimal widths found.  Layout includes
        # a wrapped version of the entire string, where the first and last characters
        # (which protrude in to the margins) are reinserted and all but the first line
        # are indented by one character, so that the string can be drawn in a single call
        # to ImageDraw.multiline_text
        layouts = []
        minPossibleWraps = 0
        for w in widths:
            if width is None:
                minPossibleWraps += 1
        for i, lineWidth in enumerate(widths):
            if lineWidth is None:
                continue
            lineList = lineLists[i]
            lineList[0] = lineList[0][len(quote):]  # Back out quote bits needed for wrap
            layoutWidth = round((lineWidth + 2) * charWidth) + 2 * icon.TEXT_MARGIN
            if i == 0:
                layoutHeight = max(icon.minTxtHgt, charHeight + 2 * icon.TEXT_MARGIN)
            else:
                layoutHeight = ((i + 1) * lineSpacing) + 2 * icon.TEXT_MARGIN
            layout = iconlayout.Layout(self, layoutWidth, layoutHeight, layoutHeight//2)
            if i == minPossibleWraps:
                layout.badness = 0
            else:
                layout.badness = 9 + i - minPossibleWraps
            layout.wrappedString = lineList
            layout.bodySize = layoutWidth, layoutHeight
            layouts.append(layout)
        return layouts

def replaceEscapeChar(str, fromChars, toChars):
    """Replace escaped characters in a string being mindful of escaped backslashes."""
    noBsStrings = str.split('\\\\')
    return '\\\\'.join([s.replace(fromChars, toChars) for s in noBsStrings])

def _splitWords(text):
    """Split the string at the end of whitespace of word boundaries, and return a
    list of strings.  Newlines are considered a word by themselves."""
    foundSpace = False
    words = []
    startIdx = 0
    inEscape = False
    for i, c in enumerate(text):
        if c == '\n':
            words.append(text[startIdx:i])
            words.append('\n')
            startIdx = i + 1
            foundSpace = False
            inEscape = False
        elif c.isspace():
            foundSpace = True
        elif foundSpace:
            words.append(text[startIdx:i])
            startIdx = i
            foundSpace = False
            inEscape = c == '\\'
        elif c == '\\':
            inEscape = True
        elif inEscape and c in ('t', 'n', 'r', 'v', 'f'):
            words.append(text[startIdx:i+1])
            startIdx = i + 1
            foundSpace = False
            inEscape = False
        else:
            inEscape = False
    words.append(text[startIdx:])
    return words

def _breakLongWords(words, maxLength):
    segments = []
    for i, string in enumerate(words):
        if len(string) > maxLength:
            startIdx = 0
            while len(string) - startIdx > maxLength:
                segments.append(string[startIdx:startIdx + maxLength])
                startIdx += maxLength
            segments.append(string[startIdx:])
        else:
            segments.append(string)
    return segments

def _wordWrap(words, maxLength):
    words = _breakLongWords(words, maxLength)
    lines = []
    lineLen = 0
    lineWords = []
    for i, word in enumerate(words):
        if word == '\n':
            lineWords.append(word)
            lines.append(''.join(lineWords))
            lineLen = 0
            lineWords = []
        elif len(word) + lineLen <= maxLength or (word[-1] == ' ' and
                len(word) + lineLen == maxLength + 1 and i < len(words)-1):
            lineWords.append(word)
            lineLen += len(word)
        else:
            lines.append(''.join(lineWords))
            lineLen = len(word)
            lineWords = [word]
    lines.append(''.join(lineWords))
    return lines

def createStringIconFromAst(astNode, window):
    # I don't think this is ever called as all supported Python versions now create
    # ast.Constant objects, instead
    if hasattr(astNode, 'annSourceStrings'):
        sourceStrs = astNode.annSourceStrings
        sourceStr = joinConcatenatedSourceStrings(sourceStrs)
        if sourceStr is None:
            sourceStr = repr(astNode.s)
        else:
            sourceStr = repr(astNode.s)
    return StringIcon(sourceStr, window=window)
icon.registerIconCreateFn(ast.Str, createStringIconFromAst)

def createStringIconFromJoinedStrAst(astNode, window):
    if hasattr(astNode, 'annSourceStrings'):
        sourceStr = joinConcatenatedSourceStrings(astNode.annSourceStrings)
        if sourceStr is None:
            sourceStr = astunparse.unparse(astNode).rstrip('\n')
    else:
        sourceStr = astunparse.unparse(astNode).rstrip('\n')
    return StringIcon(sourceStr, window)
icon.registerIconCreateFn(ast.JoinedStr, createStringIconFromJoinedStrAst)

def joinConcatenatedSourceStrings(strings):
    if len(strings) == 1:
        return strings[0]
    splitStr = [splitSrcStr(s) for s in strings]
    strTypes = [strType for strType, quote, srcStr in splitStr]
    quotes = [quote for strType, quote, srcStr in splitStr]
    if len(set(strTypes)) == 1 and len(set(quotes)) == 1:
        srcStr = "".join((srcStr for strType, quote, srcStr in splitStr))
        return strTypes[0] + quotes[0] + srcStr +  quotes[0]
    # Currently can't concatenate strings of different types, give up
    return None

def splitSrcStr(srcStr):
    if len(srcStr) >= 6 and srcStr[-3:] in ("'''", '"""'):
        quote = srcStr[-3:]
    else:
         quote = srcStr[-1]
    if srcStr[:2].lower() in ('rb', 'rf', 'br', 'fr'):
        # Unusual two-character string types
        strType = srcStr[:2].lower()
    elif srcStr[0].lower() in ('f', 'b', 'u', 'r'):
        strType = srcStr[0].lower()
    else:
        strType = ''
    return strType, quote, srcStr[len(strType) + len(quote):-len(quote)]

def removeEmptyAttrOnlyIcon(ic):
    """This temporarily patches around window.removeIcons not being fully reliable at
    placing orphaned icons and leaving the cursor in the right place after removing
    icon.  This and similar code for list icons (and maybe elsewhere, as well) should be
    removed once removeIcons rewritten."""
    ic.window.requestRedraw(ic.topLevelParent().hierRect(), filterRedundantParens=False)
    parent = ic.parent()
    win = ic.window
    attrIcon = ic.childAt('attrIcon')
    if attrIcon:
        ic.replaceChild(None, 'attrIcon')
    if parent is None and attrIcon is None:
        # Empty icon the only thing left of the statement.  Remove from seq
        if ic.prevInSeq() is not None:
            cursorIc = ic.prevInSeq()
            cursorSite = 'seqOut'
        elif ic.nextInSeq() is not None:
            cursorIc = ic.nextInSeq()
            cursorSite = 'seqIn'
        else:
            cursorIc = None
            pos = ic.pos()
        win.removeIcons([ic])
        if cursorIc is None:
            win.cursor.setToWindowPos(pos)
        else:
            win.cursor.setToIconSite(cursorIc, cursorSite)
    elif parent is None:
        # Top-level empty paren w/attribute: Leave just an attribute
        if ic.prevInSeq() or ic.nextInSeq():
            # ic was part of a sequence, hang the attribute off an entry icon
            entryIcon = entryicon.EntryIcon(window=win)
            win.replaceTop(ic, entryIcon)
            entryIcon.appendPendingArgs([attrIcon])
            win.cursor.setToText(entryIcon, drawNew=False)
        else:
            # ic was not part of a sequence (loose in window), attribute can
            # simply replace it
            win.replaceTop(ic, attrIcon)
            win.cursor.setToIconSite(attrIcon, 'attrOut')
    else:
        # ic has a parent
        parentSite = parent.siteOf(ic)
        if attrIcon:
            # parent is an input site, use an entry icon to place attribute
            entryIcon = entryicon.EntryIcon(window=win)
            parent.replaceChild(entryIcon, parentSite)
            entryIcon.appendPendingArgs([attrIcon])
            win.cursor.setToText(entryIcon, drawNew=False)
        else:
            # There's no attribute icon, just remove the icon
            win.cursor.setToIconSite(parent, parentSite)
            win.removeIcons([ic])
    ic.window.undo.addBoundary()

