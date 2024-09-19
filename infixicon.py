from PIL import Image
import comn
import iconlayout
import iconsites
import icon
import entryicon
import nameicons
import opicons
import listicons

# Self-delimiting infix operators, which respond to backspace by removing the
# delimiting character.  This both mimics normal typing, and avoids having a pre-typed
# delimiter in the entry text which would require special consideration in the parser
# (which is not currently there).
delimitOperators = (':')

class InfixIcon(icon.Icon):
    def __init__(self, op, opImg=None, isKwd=False, window=None, location=None):
        icon.Icon.__init__(self, window)
        self.precedence = -1
        self.operator = op
        if opImg is None:
            if isKwd:
                opTxt = icon.iconBoxedText(op, icon.boldFont, icon.KEYWORD_COLOR)
            else:
                opTxt = icon.iconBoxedText(op)
            opImg = Image.new('RGBA', opTxt.size, color=(0, 0, 0, 0))
            opImg.paste(opTxt, (0, 0))
            rInSiteX = opTxt.width - icon.inSiteImage.width
            rInSiteY = opTxt.height // 2 - icon.inSiteImage.height // 2
            opImg.paste(icon.inSiteImage, (rInSiteX, rInSiteY))
        self.opImg = opImg
        self.leftArgWidth = icon.EMPTY_ARG_WIDTH
        x, y = (0, 0) if location is None else location
        width = self.leftArgWidth - 1 + opImg.width + icon.EMPTY_ARG_WIDTH
        self.rect = (x, y, x + width, y + opImg.height)
        siteYOffset = opImg.height // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('leftArg', 'input', 0, siteYOffset)
        self.sites.add('rightArg', 'input', self.leftArgWidth + opImg.width, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - icon.SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - icon.SEQ_SITE_DEPTH, opImg.height-2)
        # Indicates that input site falls directly on top of output site
        self.coincidentSite = 'leftArg'

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        atTop = self.parent() is None
        suppressSeqSites = toDragImage is not None and self.prevInSeq() is None
        temporaryOutputSite = suppressSeqSites and atTop and \
                self.sites.leftArg.att is None
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
            if temporaryOutputSite:
                outSiteY = siteY - opicons.binOutImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), opicons.binOutImage))
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - opicons.binInSeqImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), opicons.binInSeqImage))
            # Body
            self.drawList.append(((leftArgX + self.leftArgWidth - 1, 0), self.opImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip)

    def doLayout(self, outSiteX, outSiteY, layout):
        self.leftArgWidth = layout.lArgWidth
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        opWidth, height = self.opImg.size
        width = opWidth + self.leftArgWidth - 1 + icon.EMPTY_ARG_WIDTH
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        opWidth, opHeight = self.opImg.size
        lArg = self.leftArg()
        lArgLayouts = [None] if lArg is None else lArg.calcLayouts()
        rArg = self.rightArg()
        rArgLayouts = [None] if rArg is None else rArg.calcLayouts()
        layouts = []
        for lArgLayout, rArgLayout in iconlayout.allCombinations(
                (lArgLayouts, rArgLayouts)):
            layout = iconlayout.Layout(self, opWidth, opHeight, opHeight // 2)
            layout.addSubLayout(lArgLayout, "leftArg", 0, 0)
            lArgWidth = icon.EMPTY_ARG_WIDTH if lArgLayout is None else lArgLayout.width
            layout.lArgWidth = lArgWidth
            rArgSiteX = lArgWidth - 1 + opWidth - 1
            layout.addSubLayout(rArgLayout, "rightArg", rArgSiteX, 0)
            rArgWidth = icon.EMPTY_ARG_WIDTH if rArgLayout is None else rArgLayout.width
            layout.width = rArgSiteX + rArgWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        leftArgText = icon.argTextRepr(self.sites.leftArg)
        rightArgText = icon.argTextRepr(self.sites.rightArg)
        return leftArgText + " " + self.operator + " " + rightArgText

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = icon.argSaveText(brkLvl, self.sites.leftArg, contNeeded, export)
        text.add(None, " " + self.operator + " ")
        icon.addArgSaveText(text, brkLvl, self.sites.rightArg, contNeeded, export)
        return text

    def dumpName(self):
        return self.operator

    def selectionRect(self):
        # Limit selection rectangle for extending selection to op itself
        opWidth, opHeight = self.opImg.size
        rightOffset = self.sites.rightArg.xOffset + icon.OUTPUT_SITE_DEPTH
        leftOffset = rightOffset - opWidth
        x, top = self.rect[:2]
        left = x + leftOffset
        return left, top, left + opWidth, top + opHeight

    def inRectSelect(self, rect):
        if not comn.rectsTouch(rect, self.rect):
            return False
        return comn.rectsTouch(rect, self.selectionRect())

    def leftArg(self):
        return self.sites.leftArg.att if self.sites.leftArg is not None else None

    def rightArg(self):
        return self.sites.rightArg.att if self.sites.rightArg is not None else None

    def leftAssoc(self):
        return True

    def rightAssoc(self):
        return False

    def snapLists(self, forCursor=False):
        # Add replace site in the center of the icon (default snap site generation does
        # not automatically create these for icons with sites coincident with their
        # outputs, since it does not know where the icon body is.
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        x, y = self.rect[:2]
        centerX = self.sites.rightArg.xOffset - self.opImg.width // 2
        bottomY = self.sites.output.yOffset + icon.REPLACE_SITE_Y_OFFSET
        snapLists['replaceExprIc'] = [(self, (x+centerX, y+bottomY), 'replaceExprIc')]
        if forCursor or not hasattr(self, 'allowableParents'):
            return snapLists
        # For subclass icon types that define an 'allowableParents' attribute, make
        # snapping  conditional on being snapped directly to the listed site of the named
        # icon class(es), or to the replace sites of icons coincident with those listed
        # in allowableParents (see below)
        def snapFn(ic, siteId):
            if isinstance(ic, self.__class__) and siteId == 'replaceExprIc':
                return True
            if siteId == 'replaceExprIc':
                # Also allow snapping to replace sites on leftmost icon in allowable
                # parent sites.  Note that the mechanics of processing this modified use
                # of a replace site are handled in expredit.extendDefaultReplaceSite,
                # which notices snapped icons with allowableParents attributes and
                # expands the replace target to reach the allowable parent site, provided
                # that the icon being replaced is coincident with that site.
                highestIcon = iconsites.highestCoincidentIcon(ic)
                parent = highestIcon.parent()
                if parent is not None:
                    allowable = self.allowableParents.get(parent.__class__.__name__)
                    if allowable is not None :
                        parentSite = parent.siteOf(highestIcon)
                        if iconsites.isSeriesSiteId(parentSite):
                            parentSite, _ = iconsites.splitSeriesSiteId(parentSite)
                        if allowable == parentSite:
                            return True
            if iconsites.isSeriesSiteId(siteId):
                siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            else:
                siteName = siteId
            allowable = self.allowableParents.get(ic.__class__.__name__)
            if allowable is not None and allowable == siteName:
                return True
        if 'output' in snapLists:  # Infix icons can end up in a sequence (via deletion)
            outSites = snapLists['output']
            snapLists['output'] = []
            snapLists['conditional'] = \
                [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def backspace(self, siteId, evt):
        if siteId == 'leftArg':
            # We shouldn't be called in this case, because we have no content to the
            # left of the left input, but this can happen on the top level
            return
        entryIcon = self._becomeEntryIcon()
        self.window.cursor.setToText(entryIcon, drawNew=False)

    def drawListIdxToPartId(self, idx):
        if self.parent() is None:
            return idx + 1
        return idx + 2

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + self.sites.output.xOffset + \
                icon.outSiteImage.width + self.leftArgWidth + icon.TEXT_MARGIN - 2
            textOriginY = self.rect[1] + self.sites.output.yOffset
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.globalFont, self.operator)
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'rightArg':
            return self._becomeEntryIcon()
        return None

    def _becomeEntryIcon(self):
        win = self.window
        win.requestRedraw(self.topLevelParent().hierRect())
        parent = self.parent()
        leftArg = self.leftArg()
        rightArg = self.rightArg()
        op = self.operator
        if parent is None and leftArg is None:
            entryAttachedIcon, entryAttachedSite = None, None
        elif parent is not None and leftArg is None:
            entryAttachedIcon = parent
            entryAttachedSite = parent.siteOf(self)
        else:  # leftArg is not None, attach to that
            entryAttachedIcon, entryAttachedSite = icon.rightmostSite(
                icon.findLastAttrIcon(leftArg))
        entryString = op[:-1] if op in delimitOperators else op
        entryIcon = entryicon.EntryIcon(initialString=entryString, window=win)
        if leftArg is not None:
            leftArg.replaceChild(None, 'output')
        if rightArg is not None:
            rightArg.replaceChild(None, 'output')
            entryIcon.appendPendingArgs([rightArg])
        if parent is None:
            if leftArg is None:
                win.replaceTop(self, entryIcon)
            else:
                win.replaceTop(self, leftArg)
                entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
        else:
            parentSite = parent.siteOf(self)
            if leftArg is not None:
                parent.replaceChild(leftArg, parentSite)
            entryAttachedIcon.replaceChild(entryIcon, entryAttachedSite)
        self.replaceChild(None, 'leftArg')
        self.replaceChild(None, 'rightArg')
        return entryIcon

class AsIcon(InfixIcon):
    # Defining 'allowableParents' triggers two important and non-obvious external
    # features related to snapping: 1) It tells the super-class (InfixIcon) snapList
    # method to make snapping conditional on the parent site being directly on an icon
    # of the given class and a site with the given name.  2) It enables dragged icons of
    # this class to also snap to replacement sites of icons that are coincident with (but
    # not directly attached to) the listed icons and sites.  The mechanism for #2 is
    # handled in expredit.extendDefaultReplaceSite, which notices snapped icons with an
    # allowableParents attribute and expands the replace target to reach the allowable
    # parent site, provided that the icon being replaced is coincident with that site.
    allowableParents = {"WithIcon": "values", "ImportIcon": "values",
        "ImportFromIcon": "importsIcons", "ExceptIcon": "typeIcon"}

    def __init__(self, window=None, location=None):
        InfixIcon.__init__(self, "as", None, True, window, location)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        parent = self.parent()
        parentClass = None if parent is None else parent.__class__.__name__
        if export:
            needCtx = False
        elif parent is None:
            needCtx = True
        else:
            if parentClass in self.allowableParents:
                parentSite = parent.siteOf(self)
                if iconsites.isSeriesSiteId(parentSite):
                    siteName, siteIdx = iconsites.splitSeriesSiteId(parentSite)
                else:
                    siteName = parentSite
                needCtx = siteName != self.allowableParents[parentClass]
            else:
                needCtx = True
        brkLvl = parentBreakLevel + (2 if needCtx else 1)
        text = icon.argSaveText(brkLvl, self.sites.leftArg, contNeeded, export)
        text.add(None, " as ")
        if parentClass == 'WithIcon':
            argText = listicons.argSaveTextForContext(brkLvl, self.sites.rightArg,
                contNeeded, export, 'store')
        else:
            argText = nameicons.createNameFieldSaveText(brkLvl, self.sites.rightArg,
                contNeeded, export)
        text.concat(brkLvl, argText)
        if needCtx:
            text.wrapCtxMacro(parentBreakLevel+1, parseCtx='s', needsCont=contNeeded)
        return text
    
    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            parent = self.parent()
            if parent is not None:
                parentClass = parent.__class__.__name__
                if parentClass in self.allowableParents:
                    parentSite = parent.siteOf(self)
                    if iconsites.isSeriesSiteId(parentSite):
                        siteName, siteIdx = iconsites.splitSeriesSiteId(parentSite)
                    else:
                        siteName = parentSite
                    if siteName != self.allowableParents[parentClass]:
                        errHighlight = icon.ErrorHighlight(
                            "An 'as' statement is not allowed, here")
                else:
                    errHighlight = icon.ErrorHighlight("'as' can only be used in "
                            "the context of a 'with', 'import', or 'except' statement")
        self.errHighlight = errHighlight
        for ic in self.children():
            ic.highlightErrors(errHighlight)
