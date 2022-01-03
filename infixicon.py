from PIL import Image
import comn
import iconlayout
import iconsites
import icon
import filefmt
import entryicon
import opicons
import cursors

class InfixIcon(icon.Icon):
    def __init__(self, op, opImg=None, isKwd=False, window=None, location=None):
        icon.Icon.__init__(self, window)
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
        width = self.leftArgWidth - 1 + opImg.width
        self.rect = (x, y, x + width, y + opImg.height)
        siteYOffset = opImg.height // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('leftArg', 'input', 0, siteYOffset)
        self.sites.add('rightArg', 'input', self.leftArgWidth + opImg.width, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - icon.SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - icon.SEQ_SITE_DEPTH, opImg.height-2)
        # Indicates that input site falls directly on top of output site
        self.coincidentSite = 'leftArg'

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
        if temporaryOutputSite or suppressSeqSites:
            self.drawList = None  # Don't keep after drawing (see above)

    def doLayout(self, outSiteX, outSiteY, layout):
        self.leftArgWidth = layout.lArgWidth
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        opWidth, height = self.opImg.size
        width = opWidth + self.leftArgWidth - 1
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
            layout.width = lArgWidth - 1 + opWidth
            layout.addSubLayout(rArgLayout, "rightArg", layout.width - 1, 0)
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

    def backspace(self, siteId, evt):
        redrawRect = self.topLevelParent().hierRect()
        parent = self.parent()
        leftArg = self.leftArg()
        rightArg = self.rightArg()
        op = self.operator
        win = self.window
        if parent is None and leftArg is None:
            entryAttachedIcon, entryAttachedSite = None, None
        elif parent is not None and leftArg is None:
            entryAttachedIcon = parent
            entryAttachedSite = parent.siteOf(self)
        else:  # leftArg is not None, attach to that
            entryAttachedIcon, entryAttachedSite = cursors.rightmostSite(
                icon.findLastAttrIcon(leftArg), ignoreAutoParens=True)
        win.entryIcon = entryicon.EntryIcon(initialString=op, window=win)
        if leftArg is not None:
            leftArg.replaceChild(None, 'output')
        if rightArg is not None:
            rightArg.replaceChild(None, 'output')
            win.entryIcon.setPendingArg(rightArg)
        if parent is None:
            if leftArg is None:
                win.replaceTop(self, win.entryIcon)
            else:
                win.replaceTop(self, leftArg)
                entryAttachedIcon.replaceChild(win.entryIcon, entryAttachedSite)
        else:
            parentSite = parent.siteOf(self)
            if leftArg is not None:
                parent.replaceChild(leftArg, parentSite)
            entryAttachedIcon.replaceChild(win.entryIcon, entryAttachedSite)
        self.replaceChild(None, 'leftArg')
        self.replaceChild(None, 'rightArg')
        win.cursor.setToEntryIcon()
        win.redisplayChangedEntryIcon(evt, redrawRect)

class AsIcon(InfixIcon):
    allowableSnaps = {"WithIcon": "values", "ImportIcon": "values",
        "ImportFromIcon": "importsIcons"}

    def __init__(self, window=None, location=None):
        InfixIcon.__init__(self, "as", None, True, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a "with" or "import" statement
        snapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = iconsites.splitSeriesSiteId(siteId)
            allowable = self.allowableSnaps.get(ic.__class__.__name__)
            return allowable is not None and allowable == siteName
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = icon.argSaveText(brkLvl, self.sites.leftArg, contNeeded, export)
        text.add(None, " as ")
        icon.addArgSaveText(text, brkLvl, self.sites.rightArg, contNeeded, export)
        return text