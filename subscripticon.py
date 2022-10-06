from PIL import Image
import ast
import comn
import iconlayout
import iconsites
import icon
import filefmt
import nameicons
import listicons
import entryicon
import reorderexpr

SLICE_EMPTY_ARG_WIDTH = 1

subscriptLBktPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o %% o",
 "o %% o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %% o",
 "o %% o",
 "o    o",
 "o    o",
 "oooooo",
)
subscriptLBktImage = comn.asciiToImage(subscriptLBktPixmap)

subscriptLBktOpenPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o %% o",
 "o %% o",
 "o %  o",
 "o %  o",
 "o 7  o",
 "o    o",
 "o 7  o",
 "o %  o",
 "o %  o",
 "o %% o",
 "o %% o",
 "o    o",
 "o    o",
 "oooooo",
)
subscriptLBktOpenImage = comn.asciiToImage(subscriptLBktOpenPixmap)

subscriptRBktPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o%%  o",
 "o%%  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o%%  o",
 "o%%  o",
 "o    o",
 "o    o",
 "oooooo",
)
subscriptRBktImage = comn.asciiToImage(subscriptRBktPixmap)

subscriptRBktTypeoverPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o88  o",
 "o88  o",
 "o 8  o",
 "o 8  o",
 "o 8  o",
 "o 8  o",
 "o 8  o",
 "o 8  o",
 "o 8  o",
 "o88  o",
 "o88  o",
 "o    o",
 "o    o",
 "oooooo",
)
subscriptRBktTypeoverImage = comn.asciiToImage(subscriptRBktTypeoverPixmap)

class SubscriptIcon(icon.Icon):
    hasTypeover = True

    def __init__(self, numSubscripts=1, window=None, closed=True, typeover=False,
            location=None):
        icon.Icon.__init__(self, window)
        self.closed = False         # self.close call will set this and endParenTypeover
        self.endParenTypeover = False
        leftWidth, leftHeight = subscriptLBktImage.size
        attrY = leftHeight // 2 + icon.ATTR_SITE_OFFSET
        self.sites.add('indexIcon', 'input',
         leftWidth + icon.ATTR_SITE_DEPTH - icon.outSiteImage.width + 1, leftHeight//2)
        self.sites.add('attrOut', 'attrOut', 0, attrY)
        self.argWidths = [icon.LIST_EMPTY_ARG_WIDTH, 0, 0]
        totalWidth, totalHeight = self._size()
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + totalWidth, y + totalHeight)
        self.changeNumSubscripts(numSubscripts)
        # Property to tell wrapping layout and save-text generators not to allow wrap
        # at the attribute site (as most attributes normally can).
        self.sticksToAttr = True
        if closed:
            self.close(typeover)

    def _size(self):
        rBrktWidth = subscriptRBktImage.width - 1 if self.closed else 0
        return subscriptLBktImage.width + sum(self.argWidths) + \
         rBrktWidth + icon.ATTR_SITE_DEPTH, subscriptLBktImage.height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            leftBoxX = icon.dimAttrOutImage.width - 1
            leftBoxWidth, leftBoxHeight = subscriptLBktImage.size
            leftImg = Image.new('RGBA', (leftBoxX + leftBoxWidth, leftBoxHeight),
             color=(0, 0, 0, 0))
            # Left bracket
            lBrktImg = subscriptLBktImage if self.closed else subscriptLBktOpenImage
            leftImg.paste(lBrktImg, (leftBoxX, 0))
            # attrOut site
            leftImg.paste(icon.dimAttrOutImage,  (self.sites.attrOut.xOffset,
             self.sites.attrOut.yOffset), mask=icon.dimAttrOutImage)
            # Index input site
            inSiteX = leftBoxX + leftBoxWidth - icon.inSiteImage.width
            inSiteY = leftBoxHeight // 2 - icon.inSiteImage.height // 2
            leftImg.paste(icon.inSiteImage, (inSiteX, inSiteY))
            self.drawList = [((0, 0), leftImg)]
            x = inSiteX + self.argWidths[0] + icon.inSiteImage.width - 1
            # Colons:
            colonY = leftBoxHeight // 2 - icon.colonImage.height // 2
            if hasattr(self.sites, 'upperIcon'):
                self.drawList.append(((x, colonY), icon.colonImage))
                x += self.argWidths[1]
            if hasattr(self.sites, 'stepIcon'):
                self.drawList.append(((x, colonY), icon.colonImage))
                x += self.argWidths[2]
            # Right bracket
            if self.closed:
                if self.endParenTypeover:
                    rBrktImg = subscriptRBktTypeoverImage
                else:
                    rBrktImg = subscriptRBktImage
                self.drawList.append(((x, 0), rBrktImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        self.argWidths = layout.argWidths
        layout.updateSiteOffsets(self.sites.attrOut)
        top = attrSiteY - (subscriptLBktImage.height // 2 + icon.ATTR_SITE_OFFSET)
        width, height = self._size()
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        indexLayouts = stepLayouts = upperLayouts = attrLayouts = [None]
        if self.sites.indexIcon.att is not None:
            indexLayouts = self.sites.indexIcon.att.calcLayouts()
        if hasattr(self.sites, 'upperIcon') and self.sites.upperIcon.att is not None:
            upperLayouts = self.sites.upperIcon.att.calcLayouts()
        if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
            stepLayouts = self.sites.stepIcon.att.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        layouts = []
        for indexLayout, upperLayout, stepLayout, attrLayout in iconlayout.allCombinations(
                (indexLayouts, upperLayouts, stepLayouts, attrLayouts)):
            if indexLayout is None:
                if hasattr(self.sites, 'upperIcon'):
                    indexWidth = SLICE_EMPTY_ARG_WIDTH
                else:
                    indexWidth = icon.LIST_EMPTY_ARG_WIDTH  # Emphasize missing argument(s)
            else:
                indexWidth = indexLayout.width - 1
            if upperLayout is None:
                if hasattr(self.sites, 'upperIcon'):
                    upperWidth = icon.colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
                else:
                    upperWidth = 0
            else:
                upperWidth = icon.colonImage.width + upperLayout.width - 2
            if stepLayout is None:
                if hasattr(self.sites, 'stepIcon'):
                    stepWidth = icon.colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
                else:
                    stepWidth = 0
            else:
                stepWidth = icon.colonImage.width + stepLayout.width - 2
            rBrktWidth = subscriptRBktImage.width - 1 if self.closed else 0
            totalWidth = subscriptLBktImage.width + indexWidth + upperWidth + \
                         stepWidth + rBrktWidth - 1 + icon.ATTR_SITE_DEPTH
            x, height = subscriptLBktImage.size
            x -= 1  # Icon overlap
            layout = iconlayout.Layout(self, totalWidth, height,
                    height // 2 + icon.ATTR_SITE_OFFSET)
            layout.addSubLayout(indexLayout, 'indexIcon', x, -icon.ATTR_SITE_OFFSET)
            x += indexWidth
            if upperWidth > 0:
                layout.addSubLayout(upperLayout, 'upperIcon', x +
                        icon.colonImage.width - 1, -icon.ATTR_SITE_OFFSET)
                x += upperWidth
            if stepWidth > 0:
                layout.addSubLayout(stepLayout, 'stepIcon', x +
                        icon.colonImage.width - 1, -icon.ATTR_SITE_OFFSET)
            if self.closed:
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width - 1, 0)
            layout.argWidths = [indexWidth, upperWidth, stepWidth]
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def changeNumSubscripts(self, n):
        if hasattr(self.sites, 'stepIcon'):
            oldN = 3
        elif hasattr(self.sites, 'upperIcon'):
            oldN = 2
        else:
            oldN = 1
        if n < 3 and oldN == 3:
            self.sites.remove('stepIcon')
        if n < 2 and oldN >= 2:
            self.sites.remove('upperIcon')
        if n >= 2 and oldN < 2:
            self.sites.add('upperIcon', 'input', cursorTraverseOrder=2)
        if n == 3 and oldN < 3:
            self.sites.add('stepIcon', 'input', cursorTraverseOrder=3)
        self.window.undo.registerCallback(self.changeNumSubscripts, oldN)
        self.markLayoutDirty()

    def close(self, typeover=False):
        if self.closed:
            return
        self.closed = True
        self.endParenTypeover = typeover
        if typeover:
            self.window.watchTypeover(self)
        self.markLayoutDirty()
        # Add back the attribute site on the end paren.  Done here to allow the site to
        # be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', comn.rectWidth(self.rect) -
         icon.ATTR_SITE_DEPTH, comn.rectHeight(self.rect) // 2 + icon.ATTR_SITE_OFFSET,
         cursorTraverseOrder=4)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def textRepr(self):
        indexIcon = self.sites.indexIcon.att
        indexText = "" if indexIcon is None else indexIcon.textRepr()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperText = ":"
            else:
                upperText = ":" + self.sites.upperIcon.att.textRepr()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepText = ":" + self.sites.stepIcon.att.textRepr()
            else:
                stepText = ""
        else:
            upperText = stepText = ""
        return '[' + indexText + upperText + stepText + ']' + icon.attrTextRepr(self)

    def dumpName(self):
        return "." + "[" + ("]" if self.closed else "")

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = filefmt.SegmentedText('[')
        if self.sites.indexIcon.att is not None:
            text.concat(brkLvl, self.sites.indexIcon.att.createSaveText(brkLvl,
                False, export), False)
        if hasattr(self.sites, 'upperIcon'):
            text.add(None, ":")
            if self.sites.upperIcon.att is not None:
                text.concat(brkLvl, self.sites.upperIcon.att.createSaveText(brkLvl, False,
                    export), False)
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                text.add(None, ":")
                text.concat(brkLvl, self.sites.stepIcon.att.createSaveText(brkLvl,
                    False, export), False)
        text.add(None, ']')
        icon.addAttrSaveText(text, self, brkLvl, contNeeded, export)
        return text

    def clipboardRepr(self, offset, iconsToCopy):
        if not hasattr(self.sites, 'upperIcon'):
            numSubscripts = 1
        elif not hasattr(self.sites, 'stepIcon'):
            numSubscripts = 2
        else:
            numSubscripts = 3
        return self._serialize(offset, iconsToCopy, numSubscripts=numSubscripts,
         closed=self.closed)

    def execute(self, attrOfValue):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.sites.indexIcon.att is None:
            raise icon.IconExecException(self, "Missing argument")
        indexValue = self.sites.indexIcon.att.execute()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperValue = None
            else:
                upperValue = self.sites.upperIcon.att.execute()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepValue = self.sites.stepIcon.att.execute()
            else:
                stepValue = None
            try:
                result = attrOfValue[indexValue:upperValue:stepValue]
            except Exception as err:
                raise icon.IconExecException(self, err)
        else:
            try:
                result = attrOfValue[indexValue]
            except Exception as err:
                raise icon.IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self, attrOfAst):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if self.sites.indexIcon.att is None:
            if not self.hasSite('upperIcon'):
                raise icon.IconExecException(self, "Missing subscript")
            indexAst = None
        else:
            indexAst = self.sites.indexIcon.att.createAst()
        if self.hasSite('upperIcon'):
            if self.sites.upperIcon.att:
                upperAst = self.sites.upperIcon.att.createAst()
            else:
                upperAst = None
            if self.hasSite('stepIcon') and self.sites.stepIcon.att:
                stepAst = self.sites.stepIcon.att.createAst()
            else:
                stepAst = None
            slice = ast.Slice(indexAst, upperAst, stepAst)
        else:
            slice = ast.Index(value=indexAst)
        return icon.composeAttrAst(self, ast.Subscript(value=attrOfAst, slice=slice,
         lineno=self.id, col_offset=0, ctx=nameicons.determineCtx(self)))

    def textEntryHandler(self, entryIc, text, onAttr):
        # Typeover for end-brackets is handled by hard-coded parsing because
        # closing of matching open brackets needs to take precedence
        return None

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if idx is None or idx > 0:
            self.endParenTypeover = False
            return False
        self.endParenTypeover = True
        return True

    def typeoverSites(self, allRegions=False):
        if not self.endParenTypeover:
            return [] if allRegions else (None, None, None, None)
        if self.hasSite('stepIcon'):
            siteBefore = 'stepIcon'
        elif self.hasSite('upperIcon'):
            siteBefore = 'upperIcon'
        else:
            siteBefore = 'indexIcon'
        result = siteBefore, 'attrIcon', ']', 0
        return [result] if allRegions else result

    def placeArgs(self, placeList, startSiteId=None, ignoreOccupiedStart=False):
        return self._placeArgsCommon(placeList, startSiteId, ignoreOccupiedStart, True)

    def canPlaceArgs(self, placeList, startSiteId=None, ignoreOccupiedStart=False):
        return self._placeArgsCommon(placeList, startSiteId, ignoreOccupiedStart, False)

    def _placeArgsCommon(self, placeList, startSiteId, ignoreOccupiedStart, doPlacement):
        # The subscript icon is the only one where empty arguments are not just
        # placeholders, so they are never skipped-over in placement.  Note that this code
        # is overkill and will rarely ever encounter an appropriate placement list,
        # because the backspace method, which was originally tuned to produce a pending
        # arg list for perfect-recreation, is now tuned to minimize pending args.
        # Perfect reproduction is needed for icons that users can backspace in to or
        # click to text-edit with an entry icon, but subscript is not such an icon.
        siteOrder = ('indexIcon', 'upperIcon', 'stepIcon', 'attrIcon')
        startIdIdx = siteOrder.index(startSiteId)
        siteIds = siteOrder[startIdIdx:]
        siteTypes = ('output', 'output', 'output', 'attrOut')[startIdIdx:]
        placed = []
        for i, (ic, idx, seriesIdx) in enumerate(icon.placementListIter(placeList,
                includeEmptySites=True)):
            if ic is None:
                if siteTypes[i] == 'output':
                    placed.append((None, siteIds[i], idx, seriesIdx))
                else:
                    break
            elif siteTypes[i] in ic.parentSites():
                placed.append((ic, siteIds[i], idx, seriesIdx))
            else:
                break
        if len(placed) == 0:
            return None, None
        if doPlacement:
            for ic, siteId, _, _ in placed:
                if not self.hasSite(siteId):
                    if siteId == 'upperIcon':
                        self.changeNumSubscripts(2)
                    elif siteId == 'stepIcon':
                        self.changeNumSubscripts(3)
                    elif siteId == 'attrIcon':
                        self.close()
                self.replaceChild(ic, siteId)
        _, _, idx, seriesIdx = placed[-1]
        return idx, seriesIdx

    def backspace(self, siteId, evt):
        win = self.window
        entryIcon = None
        if siteId == 'indexIcon':
            # Cursor is on the index site.  Remove the brackets
            win.requestRedraw(self.topLevelParent().hierRect())
            argSites = ('indexIcon', 'upperIcon', 'stepIcon')
            nonEmptySites = [s for s in argSites if self.hasSite(s) and self.childAt(s)]
            nonEmptyChildren = [self.childAt(s) for s in nonEmptySites]
            attrIcon = self.childAt('attrIcon')
            if attrIcon:
                self.replaceChild(None, 'attrIcon')
            for s in nonEmptySites:
                self.replaceChild(None, s)
            if len(nonEmptySites) == 0:
                # Icon is empty, remove
                parent = self.parent()
                if parent is None:
                    if attrIcon:
                        win.replaceTop(self, attrIcon)
                        win.cursor.setToBestCoincidentSite(attrIcon, 'attrOut')
                    else:
                        win.removeTop(self)
                        x, y = self.posOfSite('attrOut')
                        win.cursor.setToWindowPos((x, y-icon.ATTR_SITE_OFFSET))
                else:
                    parent.replaceChild(attrIcon, parent.siteOf(self))
                    win.cursor.setToIconSite(parent, 'attrIcon')
                return
            # The icon had one or more arguments
            parent = self.parent()
            if parent is None:
                # The icon was on the top level (while a subscript can't be typed on the
                # top level, it can be dragged there).
                if len(nonEmptySites) == 1:
                    win.replaceTop(self, nonEmptyChildren[0])
                    win.cursor.setToBestCoincidentSite(nonEmptyChildren[0], 'output')
                else:
                    newTuple = listicons.TupleIcon(window=win, noParens=True)
                    newTuple.insertChildren(nonEmptyChildren, 'argIcons', 0)
                    win.replaceTop(self, newTuple)
                    win.cursor.setToIconSite(newTuple, 'argIcons_0')
            else:
                # The icon has a parent, but since the subscript icon sits on
                # an attribute site we can't attach, so create an entry icon
                # and make the content into pending arguments for it.
                entryIcon = entryicon.EntryIcon(window=win)
                parent.replaceChild(entryIcon, parent.siteOf(self))
                entryIcon.appendPendingArgs([nonEmptyChildren])
                win.cursor.setToText(entryIcon)
            if attrIcon:
                # If an attribute is attached to the right bracket, try to attach it
                # to the rightmost argument.  If that's not possible, create a
                # placeholder entry icon or append it to the existing one
                attrDestIcon, attrDestSite = icon.rightmostSite(nonEmptyChildren[-1])
                if attrDestSite != 'attrIcon' or hasattr(attrDestIcon.sites.attrIcon,
                        'cursorOnly'):
                    # Can't place attribute from paren, append to pending args
                    if entryIcon is None:
                        entryIcon = entryicon.EntryIcon(window=win)
                        attrDestIcon.replaceChild(entryIcon, attrDestSite)
                    entryIcon.appendPendingArgs([attrIcon])
                else:
                    attrDestIcon.replaceChild(attrIcon, attrDestSite)
                    entryIcon.recolorPending()  # attrDestIcon already appended to args
            return
        elif siteId == 'attrIcon':
            # The cursor is on the attr site, remove the end bracket
            win.requestRedraw(self.topLevelParent().hierRect(),
                filterRedundantParens=True)
            entryicon.reopenParen(self)
            return
        # Site is after a colon.  Try to remove it
        win.requestRedraw(self.topLevelParent().hierRect(), filterRedundantParens=True)
        if siteId == 'upperIcon':
            # Remove first colon
            mergeSite1 = 'indexIcon'
            mergeSite2 = 'upperIcon'
        else:
            # Remove second colon
            mergeSite1 = 'upperIcon'
            mergeSite2 = 'stepIcon'
        mergeIcon1 = self.childAt(mergeSite1)
        mergeIcon2 = self.childAt(mergeSite2)
        if mergeIcon2 is None:
            # Site after colon is empty (no need to merge)
            cursorIc, cursorSite = icon.rightmostFromSite(self, mergeSite1)
        elif mergeIcon1 is None:
            # Site before colon is empty, move the icon after the colon to it
            self.replaceChild(None, mergeSite2)
            self.replaceChild(mergeIcon2, mergeSite1)
            cursorIc, cursorSite = self, mergeSite1
        else:
            # Both sites are occupied merge the two expressions
            rightmostIc, rightmostSite = icon.rightmostSite(mergeIcon1)
            if rightmostIc.typeOf(rightmostSite) == 'input':
                # An empty input on the right allows merge without inserting entry icon
                self.replaceChild(None, mergeSite2)
                rightmostIc.replaceChild(mergeIcon2, rightmostSite)
                reorderexpr.reorderArithExpr(mergeIcon1)
                cursorIc, cursorSite = rightmostIc, rightmostSite
            else:
                lowestIc, lowestSite = iconsites.lowestCoincidentSite(self, mergeSite2)
                if lowestIc.childAt(lowestSite):
                    # Can't merge the two expressions: insert an entry icon
                    self.replaceChild(None, mergeSite2)
                    entryIcon = entryicon.EntryIcon('', window=win)
                    entryIcon.appendPendingArgs([mergeIcon2])
                    rightmostIc.replaceChild(entryIcon, rightmostSite)
                    cursorIc = cursorSite = None
                else:
                    # Empty site right of colon, merge left side in to that and reorder
                    self.replaceChild(None, mergeSite2)
                    self.replaceChild(mergeIcon2, mergeSite1)
                    lowestIc.replaceChild(mergeIcon1, lowestSite)
                    reorderexpr.reorderArithExpr(lowestIc)
                    cursorIc, cursorSite = rightmostIc, rightmostSite
        # If there is a step site that wasn't part of the merge, shift it.
        if self.hasSite('stepIcon') and mergeSite2 != 'stepIcon':
            moveIcon = self.childAt('stepIcon')
            self.replaceChild(moveIcon, 'upperIcon')
        # Remove the colon (colonectomy)
        if self.hasSite('stepIcon'):
            self.changeNumSubscripts(2)
        else:
            self.changeNumSubscripts(1)
        # Place the cursor or new entry icon, and redraw
        if entryIcon is None:
            win.cursor.setToIconSite(cursorIc, cursorSite)
        else:
            win.cursor.setToText(entryIcon, drawNew=False)

def createSubscriptIconFromAst(astNode, window):
    if astNode.slice.__class__ == ast.Index:
        slice = [astNode.slice.value]
    elif astNode.slice.__class__ == ast.Slice:
        slice = [astNode.slice.lower, astNode.slice.upper, astNode.slice.step]
    elif astNode.slice.__class__ == ast.ExtSlice:
        return nameicons.TextIcon("**Extended slices not supported***")
    else:
        return nameicons.TextIcon("**Unexpected slice type not supported***")
    nSlices = len(slice)
    subscriptIcon = SubscriptIcon(nSlices, window)
    if slice[0] is not None:
        subscriptIcon.replaceChild(icon.createFromAst(slice[0], window), "indexIcon")
    if nSlices >= 2 and slice[1] is not None:
        subscriptIcon.replaceChild(icon.createFromAst(slice[1], window), "upperIcon")
    if nSlices >= 3 and slice[2] is not None:
        subscriptIcon.replaceChild(icon.createFromAst(slice[2], window), "stepIcon")
    topIcon = icon.createFromAst(astNode.value, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(subscriptIcon, "attrIcon")
    return topIcon
icon.registerIconCreateFn(ast.Subscript, createSubscriptIconFromAst)