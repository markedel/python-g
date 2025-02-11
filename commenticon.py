from PIL import Image, ImageDraw
import math
import comn
import icon
import iconsites
import iconlayout
import filefmt
import cursors

COMMENT_COLOR = (120, 140, 170, 255)
COMMENT_POUND_COLOR = (190, 210, 240, 255)
COMMENT_SPINE_COLOR = (200, 240, 255, 255)

COMMENT_MIN_WIDTH = 15

# Our fixed-width font for comments and strings (icon.textFont) is two pixels shorter
# than the font we use for code.  For line comments, rather than make comment icons
# shorter, or centering the text as we do in the string icon and statement comment, we
# add both spare pixels to the top of the icon, biasing the text toward the bottom as a
# subtle nod to the convention that line comments document the code underneath them.
STMT_COMMENT_V_TEXT_OFFSET = 1
LINE_COMMENT_V_TEXT_OFFSET = 2

poundImage = comn.asciiToImage((
 "  28  28",
 " 74  74 ",
 "8%%%%%%2",
 " 65 65  ",
 " 47 47  ",
 "2%%%%%8 ",
 " 28 28  ",
 " %  %   "), tint=COMMENT_POUND_COLOR)

verticalBlankImage = comn.asciiToImage((
 "..ooooooooooo",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o 9999999 o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..o         o",
 "..ooooooooooo"))

textCursorHeight = sum(icon.textFont.getmetrics()) + 2
textCursorImage = Image.new('RGBA', (1, textCursorHeight), color=(0, 0, 0, 255))

# The current comment font we're using (consolas 13 font) has an exact integer width per-
# character, but not sure that's true in general, so use a floating point number just to
# be certain that if we don't introduce errors when we multiply to convert number of
# characters to pixels.  Height is always integer pixels.
charWidth = icon.textFont.getsize('a'*100)[0] / 100
charHeight = sum(icon.textFont.getmetrics())
lineSepPixels = 2
lineSpacing = charHeight + lineSepPixels

class CommentIcon(icon.Icon):
    def __init__(self, text='', attachedToStmt=None, window=None, location=None,
            ann=None):
        icon.Icon.__init__(self, window)
        self.string = text
        self.attachedToStmt = None
        if attachedToStmt is not None:
            self.attachStmtComment(attachedToStmt)
        self.cursorPos = len(text)
        self.hasFocus = False
        self.wrappedString = text.split('\n')
        stringWidth = max((len(s) for s in self.wrappedString))
        self.annotation = ann  # No options, yet, but "fill" will be one
        width = int(stringWidth * charWidth) + poundImage.width + 2*icon.TEXT_MARGIN + 1
        height = max(icon.minTxtHgt, (len(self.wrappedString)) * lineSpacing) + 2 * \
            icon.TEXT_MARGIN + 1
        seqX = icon.dragSeqImage.width
        if not attachedToStmt:
            self.sites.add('seqIn', 'seqIn', seqX, 1)
            self.sites.add('seqOut', 'seqOut', seqX, height-2)
            self.sites.add('prefixInsert', 'output', seqX-4, height//2, cursorOnly=True)
        self.sites.add('seqInsert', 'seqInsert', 0, icon.minTxtIconHgt // 2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + width + 4, y + height)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if toDragImage is None or self.attachedToStmt is not None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start,
            # or a statement-comment attached to a statement.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        needSeqSites = not self.attachedToStmt and toDragImage is None
        if self.drawList is None:
            boxOffset = icon.dragSeqImage.width - 1
            boxWidth = comn.rectWidth(self.rect) - boxOffset
            boxHeight = comn.rectHeight(self.rect)
            img = Image.new('RGBA', (comn.rectWidth(self.rect), boxHeight),
                color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Icon border
            draw.rectangle((boxOffset, 0, boxOffset + boxWidth - 1, boxHeight - 1),
                fill=comn.ICON_BG_COLOR, outline=comn.OUTLINE_COLOR)
            # Text
            spineLeft = boxOffset + 1
            textLeft = spineLeft + poundImage.width + icon.TEXT_MARGIN
            textTop = icon.TEXT_MARGIN + (STMT_COMMENT_V_TEXT_OFFSET if
                self.attachedToStmt else  LINE_COMMENT_V_TEXT_OFFSET)
            isMultiline = len(self.wrappedString) >= 2
            for i, line in enumerate(self.wrappedString):
                y = textTop + i * lineSpacing
                draw.text((textLeft, y), line, fill=COMMENT_COLOR, font=icon.textFont)
            # Spine
            img.paste(poundImage, (spineLeft, textTop+1), mask=poundImage)
            if isMultiline:
                line1X = spineLeft + 1
                line2X = line1X + 3
                spineTop = textTop + poundImage.height
                spineBottom = boxHeight - icon.TEXT_MARGIN - charHeight // 2
                draw.line((line1X, spineTop, line1X, spineBottom), COMMENT_SPINE_COLOR)
                draw.line((line2X, spineTop, line2X, spineBottom), COMMENT_SPINE_COLOR)
            # Sequence sites
            if needSeqSites:
                icon.drawSeqSites(img, icon.dragSeqImage.width-1, 0, boxHeight)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, icon.minTxtIconHgt // 2 -
                    icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def focusIn(self):
        self.hasFocus = True
        return True

    def focusOut(self, placeEntryText=False):
        self.hasFocus = False

    def removeText(self, fromPos, toPos, isFwdDelete=False):
        if not (0 <= fromPos < toPos <= len(self.string)):
            return False
        removedText = self.string[fromPos:toPos]
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
        self._removeText(fromPos, toPos, moveCursorTo=fromPos, isUnterminated=True)
        return True

    def insertText(self, text, insertPos):
        if insertPos == 'end':
            insertPos = len(self.string)
        if text == "" or insertPos < 0 or insertPos > len(self.string):
            return ''  # Not sure this happens, but should not for addText
        # Add an undo boundary *before* _insertText registers the operation for undo,
        # because we want the boundaries mainly between words, and there's no way to tell
        # where the end of a run of characters is, until the user types something else.
        if insertPos > 0:
            prevChar = self.string[insertPos-1]
            if prevChar.isalnum() and not (text.isalnum() or text.isspace()) or \
                    prevChar.isspace() and not text.isspace() or \
                    not text.isalnum() and not text.isspace():
                self.window.undo.addBoundary()
        if len(text) > 1 or not (text.isspace() or text.isalnum()):
            # Multi-character (currently only pastes) and punctuation/delimiter inserts
            # are always worthy of undo
            self.window.undo.addBoundary()
        cursorTo = insertPos + len(text)
        self._insertText(insertPos, text, moveCursorTo=cursorTo, isUnterminated=True)
        return None

    def addText(self, text):
        """Add a character or text at the cursor.  Returns error string on failure, None
        on success."""
        return self.insertText(text, self.cursorPos)

    def processEnterKey(self):
        self.insertText('\n', self.cursorPos)

    def click(self, x, y):
        if not icon.pointInRect((x,y), self.rect):
            return False
        self.window.cursor.erase()
        self.becomeEntryIcon(clickPos=(x, y))
        self.window.cursor.setToText(self)
        return True

    def _textAreaClickBoundary(self):
        left, top, right, bottom = self.rect
        left += icon.dragSeqImage.width + poundImage.width
        top += icon.TEXT_MARGIN
        bottom -= icon.TEXT_MARGIN
        right -= icon.TEXT_MARGIN
        return left, top, right, bottom

    def pointInTextArea(self, x, y):
        left, top, right, bottom = self._textAreaClickBoundary()
        return left <= x <= right and top <= y <= bottom

    def backspaceInText(self, evt=None):
        if self.cursorPos == 0:
            # Cursor is next to pound:remove the comment if it's empty, otherwise, select
            # the content of the comment
            if self.string == '':
                stmt = self.attachedToStmt
                if stmt:
                    self.detachStmtComment()
                    rightmostIc, rightmostSite = icon.rightmostSite(stmt)
                    self.window.cursor.setToIconSite(rightmostIc, rightmostSite)
                else:
                    self.window.removeIcons([self])
            else:
                #... Once we have text selections
                pass
        else:
            self.removeText(self.cursorPos-1, self.cursorPos)

    def forwardDelete(self, evt=None):
        self.removeText(self.cursorPos, self.cursorPos+1, isFwdDelete=True)

    def arrowAction(self, direction):
        cursor = self.window.cursor
        cursor.erase()
        if direction == "Left":
            if self.cursorPos <= 0:
                # Move the cursor out of the icon
                if self.attachedToStmt:
                    rightmostIc, rightmostSite = icon.rightmostSite(self.attachedToStmt)
                    self.window.cursor.setToIconSite(rightmostIc, rightmostSite)
                else:
                    self.window.cursor.setToIconSite(self, 'prefixInsert')
            else:
                self.cursorPos -= 1
        elif direction == "Right":
            if self.cursorPos == len(self.string):
                # Move the cursor out of the icon
                if self.attachedToStmt:
                    if self.attachedToStmt.hasSite('seqOut'):
                        self.window.cursor.setToIconSite(self.attachedToStmt, 'seqOut')
                    else:
                        cursors.topSite(self.attachedToStmt)
                else:
                    self.window.cursor.setToIconSite(self, 'seqOut')
            else:
                self.cursorPos += 1
        elif direction in ('Up', 'Down'):
            x, y = self.cursorWindowPos()
            newY = y + lineSpacing * {'Up':-1, 'Down':1}[direction]
            self.window.cursor.erase()
            stmt = self.attachedToStmt if self.attachedToStmt is not None else self
            if self.becomeEntryIcon(clickPos=(x, newY))[0] is None:
                cursorType, ic, site, pos = cursors.geometricTraverseFromPos(x, y,
                    direction, self.window, stmt)
                if cursorType == 'window':
                    cursorType = 'icon'
                    site = {'Up': 'seqIn', 'Down': 'seqOut'}[direction]
                    ic = self if self.attachedToStmt is None else self.attachedToStmt
                self.window.cursor.setTo(cursorType, ic, site, pos)
        cursor.draw()

    def doLayout(self, left, top, layout):
        self.rect = (left, top, left + layout.width + icon.dragSeqImage.width - 1,
            top + layout.height)
        if not self.attachedToStmt:
            self.sites.seqOut.yOffset = layout.height - 2
            self.sites.prefixInsert.yOffset = lineSpacing // 2
        self.sites.seqInsert.yOffset = icon.minTxtIconHgt // 2
        self.wrappedString = layout.wrappedString
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        layouts = self._enumerateStringLayouts()
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return repr(self.string) + icon.attrTextRepr(self)

    def dumpName(self):
        commentType = 'stmt comment' if self.attachedToStmt else 'line comment'
        commentStr = self.string if len(self.string) < 20 else (self.string[:20] + '...')
        return commentType + ' ' + commentStr.replace('\n', '\\n')

    def backspace(self, siteId, evt):
        if siteId != 'seqOut':
            return
        self.setCursorPos('end')
        self.window.cursor.setToText(self)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            cursorTextIdx, cursorWindowPos = self.cursorInText(clickPos)
            if cursorTextIdx is None:
                return None, None
            self.setCursorPos(cursorTextIdx)
            return self, cursorWindowPos
        return None

    def cursorInText(self, clickPos, nearestToClick=True):
        """Determine if a given window x,y position (clickPos) is within the text area
        of the icon.  If so, return the (cursor) position within the text closest to
        clickPos, and the x,y window coordinate location for that cursor (y center).  If
        the clickpos is not within the clickable area, return (None, None).  In order to
        have a single cursor location associated with ends of lines, the cursor position
        to the right of the line (which often follows a space when lines are word
        wrapped) actually belongs to the start of the next line, so the nearest cursor
        position to a wrapped line end is one character left of the wrap.  This behavior
        can be changed by specifying nearestToClick as False."""
        left = self.rect[0] + icon.dragSeqImage.width + poundImage.width + \
            icon.TEXT_MARGIN
        poundXCenter = self.rect[0] + icon.dragSeqImage.width + poundImage.width // 2
        top = self.rect[1] + icon.TEXT_MARGIN
        right = self.rect[2] - icon.TEXT_MARGIN
        bottom = self.rect[3] - icon.TEXT_MARGIN
        if not icon.pointInRect(clickPos,
                (poundXCenter, top, right + int(charWidth/2), bottom)):
            return None, None
        clickX, clickY = clickPos
        clickX -= left
        clickY -= top
        lineNum = clickY // lineSpacing
        cursorY = top + lineNum * lineSpacing + lineSpacing // 2
        cursorIdx = 0
        for i in range(lineNum):
            cursorIdx += len(self.wrappedString[i])
        charNum = max(0, round(clickX / charWidth))
        if charNum >= len(self.wrappedString[lineNum]) and \
                lineNum < len(self.wrappedString):
            # clickPos is right of the line: move cursor to the last allowed position
            # (see details of line-ending behavior in function description).
            charNum = len(self.wrappedString[lineNum])
            if lineNum != len(self.wrappedString) - 1:
                if nearestToClick:
                    charNum = max(0, charNum - 1)
                else:
                    cursorY += lineSpacing
        cursorIdx += charNum
        cursorX = left + int(charWidth * charNum)
        return cursorIdx, (cursorX, cursorY)

    def nearestCursorPos(self, x, y):
        """Returns cursor index and x, y position of the cursor position nearest text
        cursor position to the given x,y coordinate.  This is the same information as
        returned by cursorInText, except in this case we expect x,y to be outside of the
        text area, presumably processing geometric arrow key traversal."""
        left, top, right, bottom = self._textAreaClickBoundary()
        xMargin = int(charWidth / 2)
        yMargin = charHeight // 2
        cursorX = min(right - xMargin, max(left + xMargin, x))
        cursorY = min(bottom - yMargin, max(top + yMargin, y))
        return self.cursorInText((cursorX, cursorY))

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        text = filefmt.SegmentedText()
        # Multi-line comments are represented in the save file as contiguous lines
        # starting with the pound character in the same column.  Since users can place
        # multiple comment icons contiguously in the same sequence, we need to keep them
        # separate, and do so by adding an empty macro when separation is needed.
        prevIcon = self.prevInSeq()
        sepFromPrev = prevIcon is not None and isinstance(prevIcon, CommentIcon)
        text.addComment(self.string, isStmtComment=self.attachedToStmt is not None,
            annotation='' if sepFromPrev else None)
        return text

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, string=self.string)

    def duplicate(self, linkToOriginal=False):
        ic = CommentIcon(text=self.string, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def textCursorImage(self):
        return textCursorImage

    def cursorWindowPos(self):
        x, y = self.rect[:2]
        x += icon.dragSeqImage.width - 1 + icon.TEXT_MARGIN + poundImage.width
        y += icon.TEXT_MARGIN + (STMT_COMMENT_V_TEXT_OFFSET if
            self.attachedToStmt else LINE_COMMENT_V_TEXT_OFFSET)
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
                break
            charCount += len(line)
        x += int(charsInLine * charWidth)
        y += lineCount * lineSpacing
        y += charHeight // 2
        return x, y

    def setCursorPos(self, pos):
        if pos == 'end':
            self.cursorPos = len(self.string)
        else:
            self.cursorPos = max(0, min(len(self.string), pos))

    def markLayoutDirty(self):
        if self.attachedToStmt:
            # When a statement comment is changed, the attached statement will also need
            # layout to re-balance the space between them. Marking the attached statement
            # also serves a second purpose: to mark the page containing the comment
            # dirty, which the root markLayoutDirty method can't otherwise do from a stmt
            # comment, because they are outside of the icon/site hierarchy.
            self.layoutDirty = True
            icon.Icon.markLayoutDirty(self.attachedToStmt)
        else:
            icon.Icon.markLayoutDirty(self)

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # If this is a statement comment, we have no parent, and are given a seqInsert
        # site, which is wrong. Instead, we need a replacement site that is conditional
        # to comments.  Note that for statement comments, we're adding a site that's
        # restricted to comments, whereas line comments can be replaced by anything.
        if self.attachedToStmt is not None:
            def snapFn(ic, siteId):
                return isinstance(ic, CommentIcon) and siteId == 'seqInsert'
            # seqInsX, seqInsY = siteSnapLists['seqInsert'][0][1]
            # seqDragSiteDepth = seqInsX + icon.dragSeqImage.width - 1
            replaceSiteX = self.rect[0] + icon.REPLACE_SITE_X_OFFSET
            replaceSiteY = siteSnapLists['seqInsert'][0][1][1] + \
                icon.REPLACE_SITE_Y_OFFSET
            del siteSnapLists['seqInsert']
            siteSnapLists['conditional'] = [(self, (replaceSiteX, replaceSiteY),
                'replaceComment', 'seqIn', snapFn)]
            return siteSnapLists
        # prefixInsert is an output-type site, but we don't want it to snap to anything
        if 'output' in siteSnapLists:
            del siteSnapLists['output']
        # Add snap site for converting line comment to stmt comment
        def snapFn(ic, siteId):
            return isRightmostSiteOfStmt(ic, siteId)
        siteSnapLists['conditional'] = [(self, self.posOfSite('prefixInsert'),
            'prefixInsert', 'seqIn', snapFn)]
        return siteSnapLists

    def siteRightOfPart(self, partId):
        # This is the only icon that can return None from this method (having no possible
        # site to return).  Rather than complicating the method by having all the other
        # icons add a second return value, or making callers add special-case code just
        # for this icon; we encourage callers instead to use expredit.siteRightOfPart
        # which returns an icon and site, where the returned icon can be different just
        # for this case.
        if self.attachedToStmt is not None:
            return None
        return 'seqOut'

    def _enumerateStringLayouts(self):
        """Return a list of possible layouts for the string.  Layout includes a special
        field called wrappedString, which breaks self.string into individual lines."""
        # Calculate the optimum (minimum) width (in characters) for each height (in
        # lines).  We assume we're using a fixed-width font, so characters are easier
        # until we need pixels for the layout structures.
        text = self.string
        currentHeight = 0
        startWidth = min(len(text), int(self.window.margin // charWidth))
        minWidth = min(int(math.sqrt(startWidth)), (self.window.margin // charWidth) // 2)
        minWidth = max(min(COMMENT_MIN_WIDTH, startWidth), minWidth)
        words = comn.splitWords(text)
        widths = []
        lineLists = []
        for widthReq in range(startWidth+1, minWidth-1, -1):
            lines, width = comn.wordWrap(words, widthReq)
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
            if w is None:
                minPossibleWraps += 1
        for i, lineWidth in enumerate(widths):
            if lineWidth is None:
                continue
            lineList = lineLists[i]
            layoutWidth = round(lineWidth * charWidth) + poundImage.width + \
                2 * icon.TEXT_MARGIN + 2
            if i == 0:
                layoutHeight = max(icon.minTxtHgt, charHeight + 2 * icon.TEXT_MARGIN)
            else:
                layoutHeight = ((i + 1) * lineSpacing) + 2 * icon.TEXT_MARGIN
            layout = iconlayout.Layout(self, layoutWidth, layoutHeight,
                icon.minTxtIconHgt // 2)
            if i == minPossibleWraps:
                layout.badness = 0
            else:
                layout.badness = 9 + i - minPossibleWraps
            layout.wrappedString = lineList
            layouts.append(layout)
        return layouts

    def attachStmtComment(self, toIc):
        toIc.stmtComment = self
        self.attachedToStmt = toIc
        if self.hasSite('seqIn'):
            self.sites.remove('seqIn')
            self.sites.remove('seqOut')
            self.sites.remove('prefixInsert')
        self.markLayoutDirty()
        toIc.markLayoutDirty()
        self.window.undo.registerCallback(self.detachStmtComment)

    def detachStmtComment(self):
        self.window.requestRedraw(self.rect)
        attachedStmt = self.attachedToStmt
        if attachedStmt is None:
            return
        del attachedStmt.stmtComment
        self.attachedToStmt = None
        self.markLayoutDirty()
        attachedStmt.markLayoutDirty()
        if not self.hasSite('seqIn'):
            seqX = icon.dragSeqImage.width
            self.sites.add('seqIn', 'seqIn', seqX, 1)
            self.sites.add('seqOut', 'seqOut', seqX, comn.rectHeight(self.rect) - 2)
            self.sites.add('prefixInsert', 'output', seqX-4, lineSpacing // 2,
                cursorOnly=True)
        self.window.undo.registerCallback(self.attachStmtComment, attachedStmt)

    def mergeTextFromComment(self, otherComment, before=False, sep=' '):
        """Merge the text from another comment into this comment (separated by a newline
        character).  If 'before' is True, insert the other comment text before the
        existing text in 'self'.  Otherwise, insert it after.  If otherComment held the
        cursor (either text or seqIn/Out), also transfer that to self."""
        self.window.requestRedraw(self.topLevelParent().hierRect())
        originalTextLen = len(self.string)
        if otherComment is None:
            return
        if before:
            self._insertText(0, otherComment.string + sep)
        else:
            self._insertText(len(self.string), sep + otherComment.string)
        # If the other comment held cursor, transfer it
        cursor = self.window.cursor
        if cursor.icon is otherComment and cursor.type in('text', 'icon'):
            otherPos = 0 if cursor.type == 'icon' else otherComment.cursorPos
            if before:
                self.cursorPos = otherPos
            else:
                self.cursorPos = originalTextLen + len(sep) + otherPos
            cursor.setToText(self, placeEntryText=False)
        self.markLayoutDirty()

    def splitAtCursor(self):
        if self.cursorPos >= len(self.string):
            return
        if self.cursorPos == 0:
            attachedStmt = self.attachedToStmt
            if attachedStmt is not None:
                self.detachStmtComment()
                icon.insertSeq(self, attachedStmt)
                self.window.addTop(self)
            return
        if self.string[self.cursorPos] == ' ':
            splitText = self.string[self.cursorPos + 1:]
            self._removeText(self.cursorPos, len(self.string))
        elif self.cursorPos > 0 and self.string[self.cursorPos - 1] == ' ':
            splitText = self.string[self.cursorPos:]
            self._removeText(self.cursorPos - 1, len(self.string))
        else:
            splitText = self.string[self.cursorPos:]
            self._removeText(self.cursorPos, len(self.string))
        newComment = CommentIcon(text=splitText, window=self.window)
        if self.attachedToStmt is not None:
            icon.insertSeq(newComment, self.attachedToStmt.topLevelParent())
        else:
            icon.insertSeq(newComment, self)
        self.window.addTop(newComment)
        self.window.cursor.setToText(newComment, 0)

    def _insertText(self, pos, text, moveCursorTo=None, isUnterminated=False):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        self.markLayoutDirty()
        self.string = self.string[:pos] + text + self.string[pos:]
        if moveCursorTo is not None:
            movedCursorFrom = self.cursorPos
            self.cursorPos = moveCursorTo
        else:
            movedCursorFrom = None
        self.window.undo.registerCallback(self._removeText, pos, pos + len(text),
           movedCursorFrom, isUnterminated=isUnterminated)

    def _removeText(self, fromPos, toPos, moveCursorTo=None, isUnterminated=False):
        self.window.requestRedraw(self.topLevelParent().hierRect())
        self.markLayoutDirty()
        removedText = self.string[fromPos:toPos]
        self.string = self.string[:fromPos] + self.string[toPos:]
        if moveCursorTo is not None:
            movedCursorFrom = self.cursorPos
            self.cursorPos = moveCursorTo
        else:
            movedCursorFrom = None
        self.window.undo.registerCallback(self._insertText, fromPos, removedText,
            movedCursorFrom, isUnterminated=isUnterminated)

class VerticalBlankIcon(icon.Icon):
    def __init__(self, window, location=None):
        icon.Icon.__init__(self, window)
        bodyWidth, bodyHeight = verticalBlankImage.size
        bodyHeight = icon.minTxtIconHgt
        siteYOffset = bodyHeight // 2
        seqX = icon.dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
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
            bodyOffset = icon.dragSeqImage.width - 1
            img.paste(verticalBlankImage, (bodyOffset, 0))
            icon.drawSeqSites(img, bodyOffset, 0, verticalBlankImage.height)
            if temporaryDragSite:
                img.paste(icon.dragSeqImage, (0, verticalBlankImage.height // 2 -
                        icon.dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        bodyWidth, bodyHeight = verticalBlankImage.size
        width = icon.dragSeqImage.width - 1 + bodyWidth
        self.rect = (left, top, left + width, top + bodyHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = verticalBlankImage.size
        return [iconlayout.Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)]

    def textRepr(self):
        return ''

    def dumpName(self):
        return '--'

    def siteRightOfPart(self, partId):
        return 'seqOut'

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        return filefmt.SegmentedText(None)

    def backspace(self, siteId, evt):
        if siteId == 'seqOut':
            prevIcon = self.sites.seqIn.att
            nextIcon = self.sites.seqOut.att
            self.window.removeIcons([self])
            if prevIcon is not None:
                self.window.cursor.setToIconSite(prevIcon, 'seqOut')
            elif nextIcon is not None:
                self.window.cursor.setToIconSite(nextIcon, 'seqIn')
            else:
                self.window.cursor.setToWindowPos(self.pos())

def topParentInclComment(ic):
    if isinstance(ic, CommentIcon) and ic.attachedToStmt:
        ic = ic.attachedToStmt
    return ic.topLevelParent()

def isRightmostSiteOfStmt(ic, siteId):
    if ic.childAt(siteId): # Just for efficiency, as this cheaply eliminates most sites
        return False
    rightmostIc, rightmostSite = icon.rightmostSite(ic.topLevelParent())
    return rightmostIc is ic and rightmostSite == siteId

# Note that most comment icons are not created by the (fake ast) method, below.  This is
# only used for the case where there's statement to which to attach the comment, which
# happens only for comments at the end of (or alone in) a file or @pos block
def createCommentIconFromAst(astNode, window):
    if astNode.text is None:
        return VerticalBlankIcon(window)
    return CommentIcon(astNode.text, ann=astNode.ann, window=window)
icon.registerIconCreateFn(filefmt.CommentFakeAst, createCommentIconFromAst)
