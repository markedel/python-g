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
import parenicon
import opicons
import reorderexpr

SLICE_EMPTY_ARG_WIDTH = 1

# The unique mechanism for converting slice icons back and forth between call and slice
# form (see comment in convertDirtySlices()) hooks the markLayoutDirty call to find out
# when slice and subscript icons are attached and detached, and records those icons that
# need to be investigated in this dictionary of lists indexed by window.
dirtySlicesAndSubscripts = {}

subscriptLBktPixmap = (
 ".ooooooooo",
 ".o       o",
 ".o       o",
 ".o       o",
 ".o   %%% o",
 ".o  82   o",
 ".o  64   o",
 ".o  46   o",
 ".o  28   o",
 ".o  %    o",
 ".o 82    o",
 ".o 64    o",
 ".o 46    o",
 ".o 28    o",
 ".o %%%   o",
 ".o       o",
 ".o       o",
 ".ooooooooo",
)
subscriptLBktImage = comn.asciiToImage(subscriptLBktPixmap)
subscriptLBrktExtendDupRows = (9,)

subscriptLBktOpenPixmap = (
 ".ooooooooo",
 ".o       o",
 ".o       o",
 ".o       o",
 ".o   %%% o",
 ".o  82   o",
 ".o  64   o",
 ".o  46   o",
 ".o  39   o",
 ".o       o",
 ".o 93    o",
 ".o 64    o",
 ".o 46    o",
 ".o 28    o",
 ".o %%%   o",
 ".o       o",
 ".o       o",
 ".ooooooooo",
)
subscriptLBktOpenImage = comn.asciiToImage(subscriptLBktOpenPixmap)

subscriptRBktPixmap = (
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o  %%%   o",
 "o   82   o",
 "o   64   o",
 "o   46   o",
 "o   28   o",
 "o   %    o",
 "o  82    o",
 "o  64    o",
 "o  46    o",
 "o  28    o",
 "o%%%     o",
 "o        o",
 "o        o",
 "oooooooooo",
)
subscriptRBktImage = comn.asciiToImage(subscriptRBktPixmap)
subscriptRBrktExtendDupRows = (9,)

subscriptRBktTypeoverPixmap = (
 "oooooooooo",
 "o        o",
 "o        o",
 "o        o",
 "o  888   o",
 "o    8   o",
 "o   99   o",
 "o   99   o",
 "o   99   o",
 "o   8    o",
 "o  99    o",
 "o  99    o",
 "o  99    o",
 "o  8     o",
 "o888     o",
 "o        o",
 "o        o",
 "oooooooooo",
)
subscriptRBktTypeoverImage = comn.asciiToImage(subscriptRBktTypeoverPixmap)

sliceColonImage = comn.asciiToImage((
 "ooooooo",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "o  %% o",
 "o  %% o",
 "o    o.",
 "o   o..",
 "o    o.",
 "o%%   o",
 "o%%   o",
 "o     o",
 "o     o",
 "o     o",
 "o     o",
 "ooooooo"))

class SubscriptIcon(icon.Icon):
    hasTypeover = True
    pythonDocRef = [("Subscripts", "reference/expressions.html#subscriptions")]
    # Property to tell wrapping layout and save-text generators not to allow wrap
    # at the attribute site (as most attributes normally can).
    sticksToAttr = True

    def __init__(self, window=None, closed=True, typeover=False, location=None):
        icon.Icon.__init__(self, window)
        self.closed = False         # self.close call will set this and endParenTypeover
        self.endParenTypeover = False
        leftWidth, leftHeight = subscriptLBktImage.size
        attrY = leftHeight // 2 + icon.ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrY)
        self.argList = iconlayout.ListLayoutMgr(self, 'argIcons', leftWidth,
                leftHeight // 2, allowsTrailingComma=False)
        width, height = self._size()
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if closed:
            self.close(typeover)

    def _size(self):
        width = subscriptLBktImage.width
        height = self.argList.spineHeight
        if self.closed:
            width += self.argList.width + subscriptRBktImage.width - 1
        else:
            width += self.argList.width
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            # Left bracket
            lBrktImg = subscriptLBktImage if self.closed else subscriptLBktOpenImage
            lBrktImg = icon.yStretchImage(lBrktImg, subscriptLBrktExtendDupRows,
                    self.argList.spineHeight)
            # Output site
            outSiteX = self.sites.attrOut.xOffset
            outSiteY = self.sites.attrOut.yOffset - icon.attrOutImage.height // 2
            lBrktImg.paste(icon.dimAttrOutImage, (outSiteX, outSiteY),
                    mask=icon.attrOutImage)
            # Body input site(s)
            self.argList.drawBodySites(lBrktImg)
            self.drawList = [((0, 0), lBrktImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(lBrktImg.width -
                    icon.OUTPUT_SITE_DEPTH - 1,
                    self.sites.attrOut.yOffset - icon.ATTR_SITE_OFFSET)
            # End bracket
            if self.closed:
                parenX = lBrktImg.width + self.argList.width - icon.ATTR_SITE_DEPTH - 1
                rParenSrcImg = subscriptRBktTypeoverImage if self.endParenTypeover else \
                    subscriptRBktImage
                rParenImg = icon.yStretchImage(rParenSrcImg, subscriptRBrktExtendDupRows,
                    self.argList.spineHeight)
                attrInXOff = rParenImg.width - icon.attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rParenImg.paste(icon.attrInImage, (attrInXOff, attrInYOff))
                self.drawList.append(((parenX, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip, allowTrailingComma=False)

    def argIcons(self):
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, attrSiteX, attrSiteY, layout):
        self.argList.doLayout(layout)
        self.sites.attrOut.yOffset = self.argList.spineTop + icon.ATTR_SITE_OFFSET
        layout.updateSiteOffsets(self.sites.attrOut)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        width, height = self._size()
        x = attrSiteX
        y = attrSiteY - self.argList.spineTop - icon.ATTR_SITE_OFFSET
        self.rect = (x, y, x + width, y + self.argList.spineHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = subscriptLBktImage.size
        bodyWidth -= icon.ATTR_SITE_DEPTH
        argListLayouts = self.argList.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        else:
            attrLayouts = [None]
        layouts = []
        for argLayout, attrLayout in iconlayout.allCombinations(
                (argListLayouts, attrLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight,
                    bodyHeight // 2 + icon.ATTR_SITE_OFFSET)
            argLayout.mergeInto(layout, bodyWidth - 1, -icon.ATTR_SITE_OFFSET)
            argWidth = argLayout.width
            # layout now incorporates argument layout sizes, but not end paren
            if self.closed:
                layout.width = subscriptLBktImage.width-1 + argWidth-1 + \
                    subscriptRBktImage.width-1
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1, 0,)
            else:
                layout.width = subscriptLBktImage.width-1 + argWidth-1
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

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
        return '[' + icon.seriesTextRepr(self.sites.argIcons) + ']' + \
               icon.attrTextRepr(self)

    def dumpName(self):
        return "." + "[" + ("]" if self.closed else "")

    def siteRightOfPart(self, partId):
        if partId == 1:
            # Left bracket
            return 'argIcons_0'
        if partId == 2:
            # Right bracket
            return 'attrIcon'
        # Error
        return self.sites.lastCursorSite()

    def inRectSelect(self, rect):
        # Require selection rectangle to touch both parens to be considered selected
        if not icon.Icon.inRectSelect(self, rect):
            return False
        selLeft, selTop, selRight, selBottom = rect
        icLeft, icTop, icRight, icBottom = self.rect
        if selLeft > icLeft + subscriptLBktImage.width:
            return False
        if selRight < icRight - subscriptRBktImage.width:
            return False
        return True

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + (2 if self.parent() is None else 1)
        text = filefmt.SegmentedText('[' if self.closed or export else '$:o$[')
        icon.addSeriesSaveText(text, brkLvl, self.sites.argIcons, contNeeded, export,
            allowTrailingComma=True)
        text.add(None, ']')
        if self.closed:
            text = icon.addAttrSaveText(text, self, brkLvl-1, contNeeded, export)
        if self.parent() is None and not export:
            text.wrapFragmentMacro(parentBreakLevel, 'a', needsCont=contNeeded)
        return text

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def duplicate(self, linkToOriginal=False):
        ic = SubscriptIcon(closed=self.closed, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def createAst(self, attrOfAst):
        if not self.closed:
            raise icon.IconExecException(self, "Unclosed temporary icon")
        if len(self.sites.argIcons) == 1 and self.childAt('argIcons_0') is None:
            raise icon.IconExecException(self, "Missing subscript")
        args = [site.att for site in self.sites.argIcons]
        if None in args:
            raise icon.IconExecException(self, "Missing argument(s)")
        sliceAsts = []
        for slice in args:
            if isinstance(slice, SliceIcon):
                sliceAsts.append(slice.createAst())
            else:
                sliceAsts.append(ast.Index(value=slice.createAst()))
        if len(sliceAsts) == 1:
            sliceAst = sliceAsts[0]
        else:
            sliceAst = ast.ExtSlice(dims=sliceAsts)
        return icon.composeAttrAst(self, ast.Subscript(value=attrOfAst, slice=sliceAst,
            lineno=self.id, col_offset=0, ctx=nameicons.determineCtx(self)))

    def textEntryHandler(self, entryIc, text, onAttr):
        # Typeover for end-brackets is handled by hard-coded parsing because closing of
        # matching open brackets needs to take precedence.  Handling colons in slices is
        # also handled in parsing
        return None

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        # Highlight the paren itself if not closed, but don't propagate
        if self.closed:
            self.errHighlight = None
        else:
            self.errHighlight = icon.ErrorHighlight("Unmatched open subscript bracket")
        for ic in self.children():
            ic.highlightErrors(None)

    def setTypeover(self, idx, site=None):
        self.drawList = None
        if idx is None or idx > 0:
            self.endParenTypeover = False
            return False
        self.endParenTypeover = True
        return True

    def typeoverSites(self, allRegions=False):
        if self.endParenTypeover:
            before = iconsites.makeSeriesSiteId('argIcons', len(self.sites.argIcons) - 1)
            returnData = before, 'attrIcon', ')', 0
            return [returnData] if allRegions else returnData
        return [] if allRegions else (None, None, None, None)

    def backspace(self, siteId, evt):
        # backspaceListIcon can handle commas and brace removal, even the fact that we're
        # on an attribute site, but if we're enclosing slices, we need to convert them to
        # calls to the slice() function.
        if siteId == 'argIcons_0':
            # We're removing brackets
            for site in self.sites.argIcons:
                if isinstance(site.att, SliceIcon):
                    site.att.convertToCall()
        listicons.backspaceListIcon(self, siteId, evt)

    def isComprehension(self):
        # This is defined to allow the icon to use the list icon backspace method, which
        # needs to ask this.
        return False

    def placeArgs(self, placeList, startSiteId=None, overwriteStart=False):
        idx, seriesIdx = icon.Icon.placeArgs(self, placeList, startSiteId, overwriteStart)
        if idx is not None:
            for arg in self.argIcons():
                if isinstance(arg, nameicons.IdentifierIcon) and arg.name == 'slice' \
                        and isinstance(arg.childAt('attrIcon'), listicons.CallIcon):
                    SliceIcon.convertCallToSlice(arg)
        return idx, seriesIdx

    def canPlaceArgs(self, placementList, startSiteId=None, overwriteStart=False):
        """Determine which arguments from placementList would be placed if the placeArgs
        method were called.  Arguments and return values are the same as for placeArgs
        method (see placeArgs for descriptions)."""
        return self._placeArgs(placementList, startSiteId, overwriteStart, False)

    def markLayoutDirty(self):
        # See convertDirtySlices for description of how call/slice substitution works.
        # Here we hook the markLayoutDirty mechanism to detect any attachment changes, so
        # that the subscript can later be checked for unconverted slice() calls.
        global dirtySlicesAndSubscripts
        icon.Icon.markLayoutDirty(self)
        if self.window not in dirtySlicesAndSubscripts:
            dirtySlicesAndSubscripts[self.window] = {self}
        else:
            dirtySlicesAndSubscripts[self.window].add(self)

    def rebalanceTopLevelLists(self):
        """Maintain Python-G series element ownership rules in the face of grammar
        ambiguity caused by unclosed parens/brackets/braces on the right side of a slice
        (elements between the unclosed paren and a following slice could belong to either
        subscript or open parens).  Per our ownership rules, we want the paren to own of
        all elements left of the slice, which allows normal series editing operations to
        work within the parens (leaving the last comma before the slice icon belonging to
        the subscript)."""
        idx = 0
        while idx < len(self.sites.argIcons):
            # We iterate over a changing argument list by index, because both the
            # stopping value (length of the argument list) and the icon pointed
            # to by the index (startIndex) may change with argument transfer.
            arg = self.sites.argIcons[idx].att
            if arg is not None:
                rightmostIc, rightmostSite = icon.rightmostSite(arg)
                enclosingIcon, enclosingSite = entryicon.findEnclosingSite(rightmostIc,
                    rightmostSite)
                if enclosingIcon is not self and iconsites.isSeriesSiteId(enclosingSite):
                    if self._moveSlicesOutOfParens(idx, enclosingIcon):
                        continue
                    self._moveArgsIntoParen(idx, enclosingIcon)
            idx += 1

    def _moveSlicesOutOfParens(self, argIdx, unclosedIcon):
        """Called with the index or an unclosed paren/bracket/brace in the icon's
        argument list, search that argument for slice icons or slices converted to
        'slice()' function call form, and move them and every item after them out of the
        tuple/list/paren/dict/call"""
        if isinstance(unclosedIcon, SubscriptIcon):
            # A subscript icon can own slices, so don't move anything out
            return False
        if isinstance(unclosedIcon, parenicon.CursorParenIcon):
            firstParenSite = 'argIcon'
        else:
            firstParenSite = 'argIcons_0'
        firstParenArg = unclosedIcon.childAt(firstParenSite)
        movedArg = False
        if SliceIcon.isSliceOrSliceCall(firstParenArg):
            # If the first thing in the unclosed paren is a slice, need to do more than
            # just move args: also move the paren into the slice it contains
            unclosedIcon.replaceChild(None, firstParenSite)
            if SliceIcon.isSliceCallForm(firstParenArg):
                firstParenArg = SliceIcon.convertCallToSlice(firstParenArg, replace=False)
            unclosedIcon.replaceWith(firstParenArg)
            indexIcon = firstParenArg.childAt('indexIcon')
            firstParenArg.replaceChild(None, 'indexIcon')
            unclosedIcon.replaceChild(indexIcon, firstParenSite)
            firstParenArg.replaceChild(unclosedIcon, 'indexIcon')
            movedArg = True
        if isinstance(unclosedIcon, parenicon.CursorParenIcon):
            return movedArg
        srcIdx = 1
        destIdx = argIdx + 1
        while srcIdx < len(unclosedIcon.sites.argIcons):
            srcSite = iconsites.makeSeriesSiteId('argIcons', srcIdx)
            arg = unclosedIcon.childAt(srcSite)
            if movedArg or SliceIcon.isSliceOrSliceCall(arg):
                unclosedIcon.replaceChild(None, srcSite)
                if SliceIcon.isSliceCallForm(arg):
                    arg = SliceIcon.convertCallToSlice(arg, replace=False)
                self.insertChild(arg, 'argIcons', destIdx)
                destIdx += 1
                movedArg = True
            else:
                srcIdx += 1
        if movedArg and isinstance(unclosedIcon, listicons.TupleIcon) and \
                len(unclosedIcon.sites.argIcons) == 1:
            # If we've cut a tuple down to 1 argument, convert it to a paren
            cursor = self.window.cursor
            hadCursor = cursor.type == 'icon' and cursor.icon is unclosedIcon
            entryicon.cvtTupleToCursorParen(unclosedIcon, False, False)
            if hadCursor:
                cursor.setToIconSite(unclosedIcon, 'argIcon', eraseOld=False,
                    placeEntryText=False, requestScroll=False)
        return movedArg

    def _moveArgsIntoParen(self, argIdx, destIc):
        """Called with the index or an unclosed paren/bracket/brace in the icon's
        argument list, move any non-slice icons right of it into that icon's argument
        list, stopping at the first Slice icon encountered.  For subscript icons, move
        ALL of the parent icon (self) arguments following argIdx into the open icon
        (including slices)"""
        srcIdx = argIdx + 1
        srcSite = iconsites.makeSeriesSiteId('argIcons', srcIdx)
        if isinstance(destIc, parenicon.CursorParenIcon):
            if not self.hasSite(srcSite):
                return
            if SliceIcon.isSliceOrSliceCall(self.childAt(srcSite)):
                return
            cursor = self.window.cursor
            hadCursor = cursor.type == 'icon' and cursor.icon is destIc
            destIc = entryicon.cvtCursorParenToTuple(destIc, False, False)
            if hadCursor:
                cursor.setToIconSite(destIc, 'argIcons_0',eraseOld=False,
                    placeEntryText=False, requestScroll=False)
        destIdx = len(destIc.sites.argIcons)
        while srcIdx < len(self.sites.argIcons):
            moveArg = self.childAt(srcSite)
            if not isinstance(destIc, SubscriptIcon) and \
                    SliceIcon.isSliceOrSliceCall(moveArg):
                break
            self.replaceChild(None, srcSite)
            destIc.insertChild(moveArg, 'argIcons', destIdx)
            destIdx += 1

class SliceIcon(icon.Icon):
    pythonDocRef = [("Subscripts", "reference/expressions.html#subscriptions"),
        ("Slicing", "library/stdtypes.html#typesseq-common")]
    # Indicates that input site falls directly on top of output site
    coincidentSite = 'indexIcon'
    # Slices can act as binary/ternary operators for arithmetic reordering
    precedence = -1

    def __init__(self, window=None, hasStep=False, location=None):
        icon.Icon.__init__(self, window)
        colonWidth, height = sliceColonImage.size
        siteYOffset = height // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('indexIcon', 'input', 0, siteYOffset)
        self.sites.add('upperIcon', 'input', colonWidth - 2,  siteYOffset)
        self.argWidths = [0, 0, 0]
        width = colonWidth - 2
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if hasStep:
            self.addStepSite()

    def _size(self):
        colonWidths = (3 if self.hasSite('stepIcon') else 2) * (sliceColonImage.width -1)
        return sum(self.argWidths) + colonWidths, sliceColonImage.height

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            self.drawList = []
            colonWidth = sliceColonImage.width
            x = self.argWidths[0] + icon.OUTPUT_SITE_DEPTH
            self.drawList.append(((x, 0), sliceColonImage))
            x += self.argWidths[1] + colonWidth - 1
            if hasattr(self.sites, 'stepIcon'):
                self.drawList.append(((x, 0), sliceColonImage))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, outSiteX, outSiteY, layout):
        self.argWidths = layout.argWidths
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        if self.hasSite('stepIcon'):
            width = self.sites.stepIcon.xOffset + icon.OUTPUT_SITE_DEPTH
        else:
            width = self.sites.upperIcon.xOffset + icon.OUTPUT_SITE_DEPTH
        height = sliceColonImage.height
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y,  x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        indexLayouts = stepLayouts = upperLayouts = [None]
        if self.sites.indexIcon.att is not None:
            indexLayouts = self.sites.indexIcon.att.calcLayouts()
        if self.sites.upperIcon.att is not None:
            upperLayouts = self.sites.upperIcon.att.calcLayouts()
        if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
            stepLayouts = self.sites.stepIcon.att.calcLayouts()
        layouts = []
        for indexLayout, upperLayout, stepLayout, in iconlayout.allCombinations(
                (indexLayouts, upperLayouts, stepLayouts)):
            indexWidth = 0 if indexLayout is None else indexLayout.width - 1
            upperWidth = 0 if upperLayout is None else upperLayout.width - 1
            stepWidth = 0 if stepLayout is None else stepLayout.width - 1
            colonWidth, height = sliceColonImage.size
            colonWidths = (2 if self.hasSite('stepIcon') else 1) * colonWidth
            totalWidth = indexWidth + upperWidth + stepWidth + colonWidths
            layout = iconlayout.Layout(self, totalWidth, height, height // 2)
            x = 0
            layout.addSubLayout(indexLayout, 'indexIcon', x, 0)
            x += indexWidth + colonWidth - 1
            layout.addSubLayout(upperLayout, 'upperIcon', x, 0)
            x += upperWidth + colonWidth - 1
            if hasattr(self.sites, 'stepIcon'):
                layout.addSubLayout(stepLayout, 'stepIcon', x, 0)
            layout.argWidths = [indexWidth, upperWidth, stepWidth]
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def addStepSite(self):
        if hasattr(self.sites, 'stepIcon'):
            return
        self.sites.add('stepIcon', 'input', cursorTraverseOrder=3)
        self.window.undo.registerCallback(self.removeStepSite)
        self.markLayoutDirty()

    def removeStepSite(self):
        if not hasattr(self.sites, 'stepIcon'):
            return
        self.sites.remove('stepIcon')
        self.window.undo.registerCallback(self.addStepSite)
        self.markLayoutDirty()

    def snapLists(self, forCursor=False):
        # Add replace site in the center of the icon (default snap site generation does
        # not automatically create these for icons with sites coincident with their
        # outputs, since it does not know where the icon body is.
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        x, y = self.rect[:2]
        centerX = self.sites.indexIcon.xOffset - sliceColonImage.width // 2
        bottomY = self.sites.indexIcon.yOffset + icon.REPLACE_SITE_Y_OFFSET
        replaceSites = [(self, (x + centerX, y + bottomY), 'replaceExprIc')]
        if self.hasSite('stepIcon'):
            centerX = self.sites.upperIcon.xOffset - sliceColonImage.width // 2
            bottomY = self.sites.upperIcon.yOffset + icon.REPLACE_SITE_Y_OFFSET
            replaceSites.append((self, (x + centerX, y + bottomY), 'replaceExprIc'))
        snapLists['replaceExprIc'] = replaceSites
        return snapLists

    def textRepr(self):
        indexIcon = self.sites.indexIcon.att
        indexText = "" if indexIcon is None else indexIcon.textRepr()
        if self.sites.upperIcon.att is None:
            upperText = ":"
        else:
            upperText = ":" + self.sites.upperIcon.att.textRepr()
        if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
            stepText = ":" + self.sites.stepIcon.att.textRepr()
        else:
            stepText = ""
        return indexText + upperText + stepText

    def duplicate(self, linkToOriginal=False):
        ic = SliceIcon(hasStep=hasattr(self.sites, 'stepIcon'), window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        saveAsCall = not isinstance(self.parent(), SubscriptIcon)
        if saveAsCall:
            text = filefmt.SegmentedText("slice(")
            sep = ','
        else:
            text = filefmt.SegmentedText()
            sep = ':'
        if self.sites.indexIcon.att is not None:
            text.concat(brkLvl, self.sites.indexIcon.att.createSaveText(brkLvl,
                False, export), False)
        text.add(None, sep)
        if self.sites.upperIcon.att is not None:
            text.concat(brkLvl, self.sites.upperIcon.att.createSaveText(brkLvl, False,
                export), False)
        if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
            # Note that we're quietly dropping the extraneous trailing ':' when there's
            # no expression in the step slot.  I believe this is a code improvement, as
            # a trailing ':' has no useful documentation value (AFAIK).
            text.add(None, sep)
            text.concat(brkLvl, self.sites.stepIcon.att.createSaveText(brkLvl,
                False, export), False)
        if saveAsCall:
            text.add(None, ')')
        return text

    def createAst(self):
        if self.sites.indexIcon.att is None:
            indexAst = None
        else:
            indexAst = self.sites.indexIcon.att.createAst()
        if self.sites.upperIcon.att:
            upperAst = self.sites.upperIcon.att.createAst()
        else:
            upperAst = None
        if self.hasSite('stepIcon') and self.sites.stepIcon.att:
            stepAst = self.sites.stepIcon.att.createAst()
        else:
            stepAst = None
        return ast.Slice(indexAst, upperAst, stepAst)

    def touchesPosition(self, x, y):
        rVal = icon.Icon.touchesPosition(self, x, y)
        return rVal

    def backspace(self, siteId, evt):
        win = self.window
        entryIcon = None
        if siteId == 'indexIcon':
            # We shouldn't be called in this case, because we have no content to the
            # left of the left input, but this can happen on the top level
            return
        # Site is after a colon.  Try to remove it
        win.requestRedraw(self.topLevelParent().hierRect(), filterRedundantParens=True)
        if siteId == 'upperIcon':
            # Remove first colon
            mergeSite1 = 'indexIcon'
            mergeSite2 = 'upperIcon'
        elif siteId == 'stepIcon':
            # Remove second colon
            mergeSite1 = 'upperIcon'
            mergeSite2 = 'stepIcon'
        else:
            print('backspace called on non-existant site of slice icon')
            return
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
        # Remove the colon (colonectomy).  If this leaves us with none, convert the icon
        # to an expression by replacing it with its start expression
        if self.hasSite('stepIcon'):
            self.removeStepSite()
        else:
            parentIc = self.parent()
            parentSite = parentIc.siteOf(self)
            indexIcon = self.childAt('indexIcon')
            self.replaceChild(None, 'indexIcon')
            self.replaceWith(indexIcon)
            if cursorIc is self:
                cursorIc, cursorSite = parentIc, parentSite
        # Place the cursor or new entry icon, and redraw
        if entryIcon is None:
            win.cursor.setToIconSite(cursorIc, cursorSite)
        else:
            win.cursor.setToText(entryIcon, drawNew=False)

    def convertToCall(self, replace=True):
        sliceIdent = nameicons.IdentifierIcon(name='slice', window=self.window)
        sliceCall = listicons.CallIcon(window=self.window)
        sliceIdent.replaceChild(sliceCall, 'attrIcon')
        indexIcon = self.childAt('indexIcon')
        self.replaceChild(None, 'indexIcon')
        upperIcon = self.childAt('upperIcon')
        self.replaceChild(None, 'upperIcon')
        hasStep = self.hasSite('stepIcon') and self.childAt('stepIcon') is not None
        if indexIcon is None and not hasStep:
            # Single-argument form (upperIcon only)
            if upperIcon is None:
                upperIcon = nameicons.IdentifierIcon('None', self.window)
            sliceCall.replaceChild(upperIcon, 'argIcons_0')
        else:
            # 2 or 3 argument form.  If either index or upper is empty, we want a None
            # icon, rather than an empty site, but for step, we prefer to omit, since
            # the second slice colon serves no purpose w/o a corresponding argument.
            if indexIcon is None:
                indexIcon = nameicons.IdentifierIcon('None', self.window)
            if upperIcon is None:
                upperIcon = nameicons.IdentifierIcon('None', self.window)
            sliceCall.replaceChild(indexIcon, 'argIcons_0')
            sliceCall.replaceChild(upperIcon, 'argIcons_1')
            if hasStep:
                stepIcon = self.childAt('stepIcon')
                self.replaceChild(None, 'stepIcon')
                sliceCall.replaceChild(stepIcon, 'argIcons_2')
        if replace:
            self.replaceWith(sliceIdent)
        return sliceIdent

    @staticmethod
    def convertCallToSlice(ic, replace=True):
        """Convert the call form of a slice 'slice(a, b, c) into the slice icon form
        'a:b:c'.  If replace is True, replaces the icon in in the parent's arg list
        (parent must be Subscript).  If replace is False, replaces regardless of parent
        and returns the substituted Slice icon"""
        if ic is None or ic.childAt('attrIcon') is None:
            return ic
        parent = ic.parent()
        if (replace and not isinstance(parent, SubscriptIcon)) or \
                not SliceIcon.isSliceCallForm(ic):
            return ic
        callIcon = ic.childAt('attrIcon')
        hasStep = len(callIcon.sites.argIcons) == 3
        if hasStep:
            stepIcon = _noneToEmpty(callIcon.childAt('argIcons_2'))
            if stepIcon is None:
                hasStep = False
        sliceIcon = SliceIcon(hasStep=hasStep, window=ic.window)
        if hasStep:
            callIcon.replaceChild(None, 'argIcons_2')
            sliceIcon.replaceChild(stepIcon, 'stepIcon')
        if len(callIcon.sites.argIcons) == 1:
            upperIcon = _noneToEmpty(callIcon.childAt('argIcons_0'))
            indexIcon = None
        else:
            indexIcon = _noneToEmpty(callIcon.childAt('argIcons_0'))
            upperIcon = _noneToEmpty(callIcon.childAt('argIcons_1'))
            callIcon.replaceChild(None, 'argIcons_1')
        callIcon.replaceChild(None, 'argIcons_0')
        sliceIcon.replaceChild(upperIcon, 'upperIcon')
        sliceIcon.replaceChild(indexIcon, 'indexIcon')
        if replace:
            ic.replaceWith(sliceIcon)
        return sliceIcon

    @staticmethod
    def isSliceCallForm(ic):
        if not isinstance(ic, nameicons.IdentifierIcon) or ic.name != 'slice':
            return False
        callIcon = ic.childAt('attrIcon')
        if callIcon.childAt('attrIcon'):
            return False   # If call has an attribute it would be lost on conversion
        return isinstance(callIcon, listicons.CallIcon) and \
            1 <= len(callIcon.sites.argIcons) <= 3

    @staticmethod
    def isSliceOrSliceCall(ic):
        return isinstance(ic, SliceIcon) or SliceIcon.isSliceCallForm(ic)

    def leftArg(self):
        # Used in expression splitting operation
        return self.childAt('indexIcon')

    def rightArg(self):
        # Used in expression splitting operation
        if self.hasSite('stepIcon'):
            return self.childAt('stepIcon')
        return self.childAt('upperIcon')

    def markLayoutDirty(self):
        # See convertDirtySlices for description of how call/slice substitution works.
        # Here hook the markLayoutDirty mechanism to detect slices that have been
        # detached from their parent subscript.
        global dirtySlicesAndSubscripts
        icon.Icon.markLayoutDirty(self)
        if self.window not in dirtySlicesAndSubscripts:
            dirtySlicesAndSubscripts[self.window] = {self}
        else:
            dirtySlicesAndSubscripts[self.window].add(self)

def convertDirtySlices(window, draggingIcons=None, pointerIcon=None):
    # The (weird) mechanism used to convert between call ('slice(a:b)') and slice ('a:b')
    # form is used, because there are too many different ways for slice icons to leak out
    # from a subscript, and we don't want to have to manage them in those other contexts.
    # The original intent was to use the normal mechanism for icon substitution (see
    # listicons.subsCanonicalInterchangeIcons), but this is only hooked in to a small set
    # of operations on comprehensions and top-level icons, and extending it to handle
    # slice conversion would have required hooking and complicating a much larger swath
    # of the editing code.  Instead, we hook just markLayoutDirty to check for slices
    # getting severed from subscripts and subscripts getting code added in, and do the
    # conversion just before layout (in the same manner as redundant paren removal).  By
    # itself this is almost sufficient, but can still leave slice icons in places where
    # they should not be during the pre-layout (editing) phase.  They shouldn't (I hope)
    # interfere with arithmetic reordering due to lower precedent, but could end up with
    # unwanted attribute attachments to the right argument or direct attachments to the
    # empty upperIcon or stepIcon site.  To prevent this, we temporarily add an attribute
    # site to capture such attachments, that we then redirect during the conversion below
    # either to the Call icon attribute site, or to the right argument of the slice icon
    # if no conversion is necessary.  It is still technically possible for the modifying
    # code to use a site that it calculated before detaching the slice from the subscript
    # (I don't think such code exists), but this will at least fail softly as a minor
    # code misplacement rather than a crash.
    global dirtySlicesAndSubscripts
    if window in dirtySlicesAndSubscripts:
        checkRebalance = set()
        for ic in list(dirtySlicesAndSubscripts[window]):
            # Check that the slice or subscript icon is still attached in the window
            topParent = ic.topLevelParent()
            if topParent is None or topParent not in window.topIcons:
                if draggingIcons is None or topParent not in draggingIcons:
                    # Ic is no longer displayed in the window or drag overlay
                    continue
                if ic is pointerIcon or ic.parent() is pointerIcon and isinstance(
                        pointerIcon, listicons.TupleIcon) and pointerIcon.noParens:
                    # Ic is the pointing icon in a drag, and allowed to remain in slice
                    # form for aesthetics, to be cleaned up by convertDroppedSlices()
                    if pointerIcon.nextInSeq() is None:
                        continue
            if isinstance(ic, SliceIcon):
                if isinstance(ic.parent(), SubscriptIcon):
                    # Preserve slice icon, but check arguments for slice icons or calls
                    # that could be merged (note that even though we might detect a slice
                    # icon here that needs to be converted to a call, we don't bother,
                    # since that's already handled elsewhere).
                    mergeSite = mergeIndexIc = mergeUpperIc = None
                    if not ic.hasSite('stepIcon'):
                        for site in ('indexIcon', 'upperIcon'):
                            child = ic.childAt(site)
                            if isinstance(child, SliceIcon):
                                if not child.hasSite('stepIcon'):
                                    mergeSite = site
                                    mergeIndexIc = child.childAt('indexIcon')
                                    mergeUpperIc = child.childAt('upperIcon')
                                    break
                            elif SliceIcon.isSliceCallForm(child):
                                callIcon = child.childAt('attrIcon')
                                nArgs = len(callIcon.sites.argIcons)
                                if nArgs < 3:
                                    mergeSite = site
                                    if nArgs == 1:
                                        mergeIndexIc = None
                                        mergeUpperIc = callIcon.childAt('argIcons_0')
                                    elif nArgs == 2:
                                        mergeIndexIc = callIcon.childAt('argIcons_0')
                                        mergeUpperIc = callIcon.childAt('argIcons_1')
                                    break
                    if mergeSite is not None:
                        # We found an embedded slice to merge
                        ic.replaceChild(None, mergeSite)
                        ic.addStepSite()
                        if mergeSite == 'indexIcon':
                            ic.replaceChild(mergeIndexIc, 'indexIcon')
                            moveToStep = ic.childAt('upperIcon')
                            ic.replaceChild(mergeUpperIc, 'upperIcon')
                            ic.replaceChild(moveToStep, 'stepIcon')
                        else:  # mergeSite == 'upperIcon'
                            ic.replaceChild(mergeIndexIc, 'upperIcon')
                            ic.replaceChild(mergeUpperIc, 'stepIcon')
                    checkRebalance.add(ic.parent())
                else:
                    # Parent is not a subscript, convert to 'slice()' form
                    ic.convertToCall()
            else:  # Subscript icon
                # Maintain Python-G series element ownership rules (see description for
                # rebalanceTopLevelLists)
                ic.rebalanceTopLevelLists()
                if ic in checkRebalance:
                    checkRebalance.remove(ic)
                # Convert any unconverted slice() calls into slice icons
                for arg in ic.argIcons():
                    convertCallFormsInSubscriptArg(arg)
        for ic in checkRebalance:
            ic.rebalanceTopLevelLists()
            for arg in ic.argIcons():
                convertCallFormsInSubscriptArg(arg)
        del dirtySlicesAndSubscripts[window]

def convertCallFormsInSubscriptArg(arg):
    """Convert slice call forms within an argument 'arg' of a subscript icon, into colon
    form (if possible).  Note that other than converting the top level argument (the
    first line of code in the function), this function is mostly useless.  Its intent is
    to reconstitute slices from slice() calls buried in expressions, but it rarely gets
    to do this, because we don't have a mechanism to be notified of the sort of changes
    that result in such structures.  It will handle such an expression pasted into the
    top level of a subscript or slice, but this is an exceedingly rare situation, since
    slices have lower precedence, and thus only appear inside expressions via deletion of
    of surrounding code in ways that don't result in this being called.  It remains here
    mostly in the hope that someone will figure out a way to trigger it better."""
    # If the top-level argument is the call form, convert it (convertCallToSlice will
    # ignore anything that's not)
    arg = SliceIcon.convertCallToSlice(arg)
    if isinstance(arg, SliceIcon):
        numColonsAvail = 0 if arg.hasSite('stepIcon') else 1
    else:
        numColonsAvail = 2
    while numColonsAvail > 0:
        sliceCall = findConvertibleCallFormInExpr(arg, numColonsAvail)
        if sliceCall is None:
            return
        # We have a slice call we can convert
        subscriptIc = arg.parent()
        argSite = subscriptIc.siteOf(sliceCall, recursive=True)
        if isinstance(arg, SliceIcon):
            # The top level subscript argument is a slice.  findConvertibleCallFormInExpr
            # counted colons and checked for bounding sites, so all we need to do is
            # splice the arguments with the surrounding expression, and incorporate them
            # into the top level slice
            callIcon = sliceCall.childAt('attrIcon')
            if len(callIcon.sites.argIcons) == 1:
                upperIc = _noneToEmpty(callIcon.childAt('argIcons_0'))
                indexIc = None
                callIcon.replaceChild(None, 'argIcons_0')
            else:
                indexIc = _noneToEmpty(callIcon.childAt('argIcons_0'))
                upperIc = _noneToEmpty(callIcon.childAt('argIcons_1'))
                callIcon.replaceChild(None, 'argIcons_0')
                callIcon.replaceChild(None, 'argIcons_0')
            arg.addStepSite()
            sliceSite = arg.siteOf(sliceCall, recursive=True)
            left, right = entryicon.splitExprAtIcon(sliceCall, arg, indexIc, upperIc)
            if sliceSite == 'indexIcon':
                origUpperIc = arg.childAt('upperIcon')
                arg.replaceChild(None, 'upperIcon')
                arg.replaceChild(origUpperIc, 'stepIcon')
                arg.replaceChild(left, 'indexIcon')
                arg.replaceChild(right, 'upperIcon')
            else:
                arg.replaceChild(left, 'upperIcon')
                arg.replaceChild(right, 'stepIcon')
        else:
            # The top level subscript argument is not a slice: create a slice from the
            # identified call form, and incorporate the rest of the expression into it.
            sliceIc = SliceIcon.convertCallToSlice(sliceCall, replace=False)
            sliceLeft = sliceIc.childAt('indexIcon')
            sliceIc.replaceChild(None, 'indexIcon')
            sliceRight = sliceIc.childAt('upperIcon')
            sliceIc.replaceChild(None, 'upperIcon')
            left, right = entryicon.splitExprAtIcon(sliceCall, subscriptIc, sliceLeft,
                sliceRight)
            subscriptIc.replaceChild(None, argSite)
            sliceIc.replaceChild(left, 'indexIcon')
            sliceIc.replaceChild(right, 'upperIcon')
            subscriptIc.insertChild(sliceIc, argSite)
            if not numColonsAvail == 2 and not sliceIc.hasSite('stepIcon'):
                return
            # We still have room to convert another slice call
            arg = sliceIc
            numColonsAvail = 1

def findConvertibleCallFormInExpr(ic, numColonsAvail):
    if ic is None or numColonsAvail == 0:
        return None
    if SliceIcon.isSliceCallForm(ic):
        callIcon = ic.childAt('attrIcon')
        numColonsNeeded = 2 if callIcon.hasSite('argIcons_2') else 1
        if numColonsNeeded <= numColonsAvail:
            return ic
    if not isinstance(ic, (opicons.BinOpIcon, opicons.UnaryOpIcon, opicons.IfExpIcon,
            SliceIcon)):
        return None
    if isinstance(ic, opicons.UnaryOpIcon):
        return findConvertibleCallFormInExpr(ic.childAt('argIcon'), numColonsAvail)
    if not isinstance(ic, SliceIcon) and ic.hasParens:
        return None
    leftArgResult = findConvertibleCallFormInExpr(ic.leftArg(), numColonsAvail)
    if leftArgResult is not None:
        return leftArgResult
    rightArgResult = findConvertibleCallFormInExpr(ic.rightArg(), numColonsAvail)
    if rightArgResult is not None:
        return rightArgResult
    return None

def convertDroppedSlices(movIcon, statIcon, siteName, draggingSeqs):
    if isinstance(movIcon, SliceIcon):
        if not isinstance(statIcon, SubscriptIcon) or siteName[:8] != 'argIcons':
            subsIcon = movIcon.convertToCall(replace=False)
            for seq in draggingSeqs:
                if seq[0] is movIcon and len(seq) == 1:
                    seq[0] = subsIcon
    elif isinstance(movIcon, listicons.TupleIcon) and movIcon.noParens:
        if not isinstance(statIcon, SubscriptIcon) or siteName[:8] != 'argIcons':
            for arg in movIcon.argIcons():
                if isinstance(arg, SliceIcon):
                    arg.convertToCall()

def _noneToEmpty(ic):
    """If ic is the 'None' icon, return None (for the purpose of creating an empty site,
    as we use in a SliceIcon, instead of an explicit None)"""
    if isinstance(ic, nameicons.IdentifierIcon) and ic.text == 'None':
        return None
    return ic

def createSubscriptIconFromAst(astNode, window):
    # Decompose the subscript AST into a list of ASTs to become elements of the
    # subscript list (subscripts with lists are used for multidimensional NumPy Arrays
    # as well as type values
    if isinstance(astNode.slice, (ast.Index, ast.Slice)):
        sliceAsts = [astNode.slice]
    elif isinstance(astNode.slice, ast.ExtSlice):
        sliceAsts = astNode.slice.dims
    elif isinstance(astNode.slice, ast.Tuple):
        # Not used in 3.8, but future Python versions use this, instead of ExtSlice
        sliceAsts = astNode.slice.elts
    else:
        # Not used in 3.8, but future Python versions omit ast.Index wrapper
        sliceAsts = [astNode.slice]
    sliceIcons = []
    # Convert the collected ASTs to icons, manually processing the Index ast for which
    # we have no handler.
    for sliceAst in sliceAsts:
        if isinstance(sliceAst, ast.Index):
            sliceIcons.append(icon.createFromAst(sliceAst.value, window))
        else:
            sliceIcons.append(icon.createFromAst(sliceAst, window))
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        closed = 'o' not in macroArgs
    else:
        closed = True
    subscriptIcon = SubscriptIcon(window, closed=closed)
    subscriptIcon.insertChildren(sliceIcons, 'argIcons_0')
    if filefmt.isAttrParseStub(astNode.value):
        return subscriptIcon  # This is a free subscript on the top level
    topIcon = icon.createFromAst(astNode.value, window)
    parentIcon = icon.findLastAttrIcon(topIcon)
    parentIcon.replaceChild(subscriptIcon, "attrIcon")
    return topIcon
icon.registerIconCreateFn(ast.Subscript, createSubscriptIconFromAst)

def createSliceIconFromAst(astNode, window):
    sliceIc = SliceIcon(window=window, hasStep=astNode.step is not None)
    if astNode.lower is not None:
        indexIc = icon.createFromAst(astNode.lower, window)
        sliceIc.replaceChild(indexIc, "indexIcon")
    if astNode.upper is not None:
        upperIc = icon.createFromAst(astNode.upper, window)
        sliceIc.replaceChild(upperIc, "upperIcon")
    if astNode.step is not None:
        stepIc = icon.createFromAst(astNode.step, window)
        sliceIc.replaceChild(stepIc, "stepIcon")
    return sliceIc
icon.registerIconCreateFn(ast.Slice, createSliceIconFromAst)