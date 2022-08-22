# Copyright Mark Edel  All rights reserved
import heapq
import functools
import itertools
import operator
import sys
import icon
import iconsites

class Layout:
    """Structure to store the information that the icon has calculated about how it
    should be laid out (in calcLayouts), until all the calculations are done and the
    layout is implemented (in doLayout).  The icon may also add its own externally-defined
    fields to the object for icon-specific data"""
    def __init__(self, ico, width, height, siteYOffset):
        self.icon = ico
        self.width = width
        self.height = height
        self.badness = 0
        self.parentSiteOffset = siteYOffset
        self.subLayoutCount = 0
        self.subLayouts = {}
        self.siteOffsets = {}

    # heapq does not understand sort keys (it can only use the default sort mechanism),
    # so to use if for sorting tuples containing an integer score and a layout, we need
    # to give it a way to compare layouts, even though we don't care what the answer is.
    def __lt__(self, other):
        return 0

    def addSubLayout(self, subLayout, siteName, xSiteOffset, ySiteOffset):
        """Incorporate the area of child layout positioned at (xSiteOffset, ySiteOffset)
        relative to the implied site of the current layout.  subLayout can also be
        passed as None, in which case add a None to the sublayouts list."""
        self.subLayouts[siteName] = subLayout
        self.siteOffsets[siteName] = (xSiteOffset, ySiteOffset)
        if subLayout is None or xSiteOffset is None:
            return
        heightAbove = max(self.parentSiteOffset, subLayout.parentSiteOffset - ySiteOffset)
        heightBelow = max(self.height - self.parentSiteOffset, ySiteOffset +
         subLayout.height - subLayout.parentSiteOffset)
        self.height = heightAbove + heightBelow
        self.parentSiteOffset = heightAbove
        self.width = max(self.width, xSiteOffset + subLayout.width)
        self.subLayoutCount += 1 + subLayout.subLayoutCount

    def updateSiteOffsets(self, parentSite, parentSiteDepthAdj=0):
        """Icon site positions are relative to the icon rectangle.  Set them from the
        layout site positions, which are relative to the implied site of the layout
        (on the left edge of the layout rectangle, parentSiteOffset from the top, and
        idealized to zero site depth).  The parentSite argument should provide the site
        object (which has presumably already been positioned relative to the icon
        rectangle).  parentSiteDepthAdj can be specified if the parent site is not
        positioned at the standard depth (else, elif, except, finally)"""
        parentSiteDepth = icon.siteDepths[parentSite.type] + parentSiteDepthAdj
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name)
            siteDepth = icon.siteDepths[site.type]
            xOffset, yOffset = self.siteOffsets[name]
            site.xOffset = parentSite.xOffset + parentSiteDepth - siteDepth + xOffset
            site.yOffset = parentSite.yOffset + yOffset

    def doSubLayouts(self, parentSite, outSiteX, outSiteY):
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name)
            if site.att is not None:
                x = outSiteX + site.xOffset - parentSite.xOffset
                y = outSiteY + site.yOffset - parentSite.yOffset
                site.att.doLayout(x, y, layout)

    def mergeLayout(self, layoutToMerge, xOff, yOff):
        """Expand the current layout (self) to encompass layoutToMerge at reference
        location (xOff, yOff) relative to the reference location of the layout
        (0, self.parentSiteOffset)."""
        self.width = max(self.width, xOff + layoutToMerge.width)
        heightAbove = max(self.parentSiteOffset, layoutToMerge.parentSiteOffset - yOff)
        heightBelow = max(self.height - self.parentSiteOffset,
                yOff + layoutToMerge.height - layoutToMerge.parentSiteOffset)
        self.height = heightAbove + heightBelow
        self.parentSiteOffset = heightAbove
        self.badness += layoutToMerge.badness
        self.subLayoutCount += layoutToMerge.subLayoutCount
        self.subLayouts.update(layoutToMerge.subLayouts)
        for siteName, siteOffset in layoutToMerge.siteOffsets.items():
            self.siteOffsets[siteName] = siteOffset[0] + xOff, siteOffset[1] + yOff

class ListLayoutMgr:
    """Manage layout for a one-dimensional list of icon arguments.  An icon can have
    multiple argument lists, and each list should have its own ListLayoutMgr.  By default,
    the icon is responsible for drawing parens/brackets/braces around the list.  However
    for icons that don't draw these, a "simple spine" (minimal visual grouping guide to
    help the user associate the list with the parent icon) can be requested that will
    appear when the list becomes multi-row.  Both the layout and the .width attribute
    incorporate the additional space where the spine will draw, but the caller must
    invoke drawSimpleSpine to actually draw it"""
    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY, simpleSpine=False,
            cursorTraverseOrder=None):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        self.simpleSpine = simpleSpine
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)],
            cursorTraverseOrder=cursorTraverseOrder)
        self.width = 0
        self.height = icon.minTxtIconHgt
        self.spineHeight = icon.minTxtIconHgt
        self.spineTop = icon.minTxtIconHgt // 2
        self.bodySitePositions = None
        self.commaSitePositions = None
        self.rowWidths = None

    def drawListCommas(self, leftSiteX, leftSiteY, typeoverIdx=None):
        xOff = leftSiteX + icon.inSiteImage.width - icon.commaImage.width
        yOff = leftSiteY - icon.commaImageSiteYOffset
        if self.commaSitePositions is None:
            print("ListLayoutMgr draw before layout")
            return []
        drawList = []
        for siteIdx, (x, y) in self.commaSitePositions:
            img = icon.commaTypeoverImage if siteIdx == typeoverIdx else icon.commaImage
            drawList.append(((x+xOff, y+yOff), img))
        return drawList

    def drawBodySites(self, bodyImg):
        xOff = bodyImg.width - icon.inSiteImage.width
        yOff = self.spineTop - icon.inSiteImage.height // 2
        if self.bodySitePositions is None:
            print("ListLayoutMgr drawing before layout")
            return
        for x, y in self.bodySitePositions:
            bodyImg.paste(icon.inSiteImage, (x + xOff, y + yOff), mask=icon.inSiteMask)

    def drawSimpleSpine(self, leftSiteX, leftSiteY, drawOutputSite=True):
        """Returns left and right spine images suitable for an icon draw list for the
        minimal "simple spine" used by icons which do not draw parens/brackets/braces
        around argument lists.  If drawOutputSite is specified as False, the spine will
        not include an output site (but note that position is still specified as if it
        were on an output site, two pixels left of the spine)."""
        if not self.simpleSpineWillDraw():
            return []
        lImg = icon.lSimpleSpineImage if drawOutputSite else icon.rSimpleSpineImage
        lSpine = icon.yStretchImage(lImg, icon.simpleSpineExtendDupRows, self.spineHeight)
        outSiteY = self.spineTop - icon.outSiteImage.height // 2
        if drawOutputSite:
            lSpine.paste(icon.outSiteImage, (0, outSiteY), mask=icon.outSiteImage)
        self.drawBodySites(lSpine)
        rSpine = icon.yStretchImage(icon.rSimpleSpineImage, icon.simpleSpineExtendDupRows,
                self.spineHeight)
        rightX = leftSiteX + icon.OUTPUT_SITE_DEPTH + self.width - icon.rSimpleSpineImage.width
        if not drawOutputSite:
            leftSiteX += icon.OUTPUT_SITE_DEPTH
        return [((leftSiteX, leftSiteY - self.spineTop), lSpine),
                ((rightX, leftSiteY - self.spineTop), rSpine)]

    def simpleSpineWillDraw(self):
        """Return True if ListLayoutMgr has simpleSpine enabled and the chosen layout
        (last doLayout call) was multi-row (requires drawSimpleSpine call and includes
        space for drawing the simple spine)."""
        return self.simpleSpine and self.rowWidths and len(self.rowWidths) >= 2

    def makeInsertSnapList(self):
        """Generate snap sites for item insertion"""
        if self.bodySitePositions is None:
            return []
        insertSites = []
        inputSites = self.icon.sites.getSeries(self.siteSeriesName)
        if len(inputSites) > 1 or len(inputSites) == 1 and inputSites[0].att is not None:
            x, y = self.icon.rect[:2]
            x += icon.INSERT_SITE_X_OFFSET
            y += icon.INSERT_SITE_Y_OFFSET
            minXOffset = inputSites[0].xOffset
            bodySiteXOffset = inputSites[0].xOffset - self.bodySitePositions[0][0]
            bodySiteYOffset = inputSites[0].yOffset - self.bodySitePositions[0][1]
            for site in inputSites:
                insertSites.append((self.icon, (x + site.xOffset, y + site.yOffset), site.name))
            numInputSites = len(inputSites)
            bodySiteIdxs = [idx
                    for idx, site in enumerate(inputSites) if site.xOffset == minXOffset]
            for i, rowWidth in enumerate(self.rowWidths):
                _siteX, siteY = self.bodySitePositions[i]
                siteX = x + bodySiteXOffset + rowWidth
                siteY += y + bodySiteYOffset
                if i < len(self.rowWidths) - 1:
                    siteName = iconsites.makeSeriesSiteId(self.siteSeriesName + 'Dup',
                            bodySiteIdxs[i+1])
                else:
                    siteName = iconsites.makeSeriesSiteId(self.siteSeriesName, numInputSites)
                insertSites.append((self.icon, (siteX, siteY), siteName))
        return insertSites

    def doLayout(self, layout):
        """Updates the icon spacing for the list as calculated in the calcLayouts method.
        This does not call doLayout for the icons in the list (but calcLayouts adds the
        information to the icon layout such that layout.doSubLayouts will do them along
        with the rest of the attached icons)."""
        # layout for managed list gets merged in to layout of entire icon. List-specific
        # data is added as an attribute based on site name
        leftSublayoutOffset = icon.OUTPUT_SITE_DEPTH if self.simpleSpineWillDraw() else 0
        self.width, self.height, siteOffsets, self.rowWidths = getattr(layout,
                self.siteSeriesName + 'ListMgrData')
        self.commaSitePositions = []
        self.bodySitePositions = []
        for i, offset in enumerate(siteOffsets.values()):
            if offset[0] == leftSublayoutOffset:
                self.bodySitePositions.append(offset)
            else:
                self.commaSitePositions.append((i, offset))
        minBodySiteY = 0   # Include the anchor point (y == 0)
        maxBodySiteY = 0
        for bodySitePos in self.bodySitePositions:
            minBodySiteY = min(minBodySiteY, bodySitePos[1])
            maxBodySiteY = max(maxBodySiteY, bodySitePos[1])
        if minBodySiteY == sys.maxsize or maxBodySiteY == minBodySiteY:
            self.spineHeight = icon.minTxtIconHgt
            self.spineTop = icon.minTxtIconHgt // 2
        else:
            self.spineHeight = maxBodySiteY - minBodySiteY + icon.inSiteImage.height + 10
            self.spineTop = -minBodySiteY + icon.inSiteImage.height // 2 + 5

    def wrapped(self):
        return self.bodySitePositions == 1

    def calcLayouts(self):
        # Avoiding combinatorial explosion with all the possible layouts, is extremely
        # challenging.  Simply exploring all combinations of sublayouts for all possible
        # list dimensions, can explode far beyond keypress time for even short lists.  The
        # method used here, is to work from narrow layouts to wide ones, caching the work
        # expended to layout the start of each row, and culling per-row as the layout
        # develops.
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if len(siteSeries) == 1 and siteSeries[0].att is None:
            # Empty Argument list leaves no space: (), [], {}
            layout = ListMgrLayout(self.siteSeriesName, ())
            layout.addSubLayout(None,  siteSeries[0].name, 0, 0)
            layout.width = 1
            layout.height = icon.minTxtIconHgt
            layout.parentSiteOffset = icon.minTxtIconHgt // 2
            return [layout]
        childLayoutLists = []
        margin = 0
        for ic in (site.att for site in siteSeries):
            if ic is None:
                childLayoutList = (None,)
                minWidth = 1
            else:
                childLayoutList = ic.calcLayouts()
                minWidth = min((lo.width for lo in childLayoutList))
            childLayoutLists.append(childLayoutList)
            margin = max(margin, minWidth)
        rowLayoutMgr = self.RowLayoutManager(childLayoutLists)
        finishedLayouts = []
        # Loop, increasing margin
        while margin < sys.maxsize:
            # Loop building row layout choices in to full layouts, one row at a time.
            # Combined layouts are a tuple of the form: height, rowData, badness,
            # sublayouts.  RowData is of the form: (start-index, yOffset, width)
            row1Layouts, nextMargin = rowLayoutMgr.rowLayoutChoices(0, margin)
            combinedLayouts = []
            for rowLayout in row1Layouts:
                width, heightAbove, heightBelow, badness, sublayouts = rowLayout
                combinedLayouts.append((heightAbove + heightBelow,
                        [(0, heightAbove, width)], badness, sublayouts))
            perMarginLayouts = []
            while len(combinedLayouts) > 0:
                newCombinedLayouts = []
                for combinedLayout in combinedLayouts:
                    height, rowData, badness, sublayouts = combinedLayout
                    rowStartIdx = len(sublayouts)
                    if rowStartIdx >= len(childLayoutLists):
                        maxWidth = max((rd[2] for rd in rowData))
                        if maxWidth == margin:  # layout is a dup if maxWidth < margin
                            perMarginLayouts.append(combinedLayout)
                        continue
                    rowLayouts, rowNextMargin = rowLayoutMgr.rowLayoutChoices(rowStartIdx, margin)
                    nextMargin = min(nextMargin, rowNextMargin)
                    for rowLayout in rowLayouts:
                        width, heightAbove, heightBelow, rowBadness, rowSublayouts = \
                                rowLayout
                        # ... should cull, here, too.  But, let's get this working, first
                        newCombinedLayouts.append((height-1 + heightAbove + heightBelow,
                                rowData + [(rowStartIdx, height-1 + heightAbove, width)],
                                badness + rowBadness, sublayouts + rowSublayouts))
                combinedLayouts = newCombinedLayouts
            # Make Layout objects for the finished layouts for this margin
            leftSublayoutOffset = icon.OUTPUT_SITE_DEPTH if self.simpleSpineWillDraw() else 0
            for height, rowData, badness, sublayouts in perMarginLayouts:
                # Cull new layouts against finishedLayouts list
                for finLo in tuple(finishedLayouts):
                    if margin >= finLo.width and height >= finLo.height and \
                            badness >= finLo.badness:
                        break  # Layout is provably worse than an existing layout
                    if finLo.width >= margin and finLo.height >= height and \
                            finLo.badness >= badness:
                        finishedLayouts.remove(finLo)
                else:  # Layout is not provably worse than an existing layout: add
                    rowWidths = [width for _startIdx, _yOffset, width in rowData]
                    lo = ListMgrLayout(self.siteSeriesName, rowWidths)
                    rowNum = 0
                    x = leftSublayoutOffset
                    # If only one row, align with the output, otherwise, center by height
                    centerY = rowData[0][1] if len(rowData) == 1 else height // 2
                    for siteNum, sublayout in enumerate(sublayouts):
                        if rowNum < len(rowData)-1 and siteNum == rowData[rowNum+1][0]:
                            rowNum += 1
                            x = leftSublayoutOffset
                        startIdx, rowYOffset, rowWidth = rowData[rowNum]
                        siteName = siteSeries[siteNum].name
                        lo.addSubLayout(sublayout, siteName, x, rowYOffset - centerY)
                        x += (icon.LIST_EMPTY_ARG_WIDTH if sublayout is None else
                              sublayout.width) + icon.commaImage.width - 2
                    lo.width = margin
                    if self.simpleSpine and len(rowData) >= 2:
                        lo.width += icon.rSimpleSpineImage.width * 2 - 2
                    lo.height = height
                    lo.badness = badness
                    finishedLayouts.append(lo)
            margin = nextMargin
        # Incorporate layout shape in badness score (penalize tall, thin layouts)
        for i, lo in enumerate(finishedLayouts):
            if len(lo.rowWidths) > 0:
                shapeBadness = int((max(1, lo.height * 4 / lo.width) - 1) * 5)
                if shapeBadness > 0:
                    lo.badness += shapeBadness
        return cullLayoutList(finishedLayouts)

    class RowLayoutManager:
        """Computes optimal row layouts and manages cache of row layout combinations that
        have already been computed.  Expects to be re-instantiated for every new layout,
        and to be used such that that the margin always increases."""

        def __init__(self, layoutLists):
            self.layoutLists = layoutLists
            maxRows = len(layoutLists)
            self.finishedLayouts = [[] for _ in range(maxRows)]
            self.branchesToProcess = [None] * maxRows

        def rowLayoutChoices(self, rowStartIdx, margin):
            """Returns a list of row layouts (tuple form) and the next larger margin
            that would cause a change.  Tuple-form row-layouts are tuples containing:
            width, heightAbove, heightBelow, badness, and subLayout-list."""
            # The self.branchesToProcess structure is a sorted list (heapq) existing row
            # layouts and the next list-item-layout organized by margin width.  If the
            # row has not yet been requested, seed choices for the first element.
            rowBranches = self.branchesToProcess[rowStartIdx]
            if rowBranches is None:
                rowBranches = self.branchesToProcess[rowStartIdx] = []
                for lo in self.layoutLists[rowStartIdx]:
                    loWidth = icon.LIST_EMPTY_ARG_WIDTH if lo is None else lo.width
                    heapq.heappush(rowBranches, (loWidth, (0, 0, 0, 0, ()), lo))
            # Loop, incrementally incorporating new layout choices until the margin is
            # reached
            while len(rowBranches) > 0 and rowBranches[0][0] <= margin:
                # pull the shortest non-margin-exceeding layout from rowBranches
                width, baseRowLayout, newItemLayout = heapq.heappop(rowBranches)
                # Make a new row layout by advancing baseRowLayout with newItemLayout
                _, heightAbove, heightBelow, badness, sublayouts = baseRowLayout
                if newItemLayout is None:
                    itemHeightAbove = icon.minTxtIconHgt // 2
                    itemHeightBelow = icon.minTxtIconHgt - itemHeightAbove
                    itemBadness = 0
                else:
                    itemHeightAbove = newItemLayout.parentSiteOffset
                    itemHeightBelow = newItemLayout.height - itemHeightAbove
                    itemBadness = newItemLayout.badness
                newSublayouts = sublayouts + (newItemLayout,)
                heightAbove = max(heightAbove, itemHeightAbove)
                heightBelow = max(heightBelow, itemHeightBelow)
                badness += itemBadness
                newRowLayout = width, heightAbove, heightBelow, badness, newSublayouts
                # Removes any row layouts that are not applicable to this margin or are
                # provably worse than the one we are about to add.
                survivedCull = self.cullRowLayouts(rowStartIdx, newRowLayout, width)
                # If the new layout survived the cull and can be extended, add all
                # layouts for the next item in the list to self.branchesToProcess to set
                # them up to be processed later in this or subsequent calls
                nextIdx = rowStartIdx + len(sublayouts) + 1
                if survivedCull:
                    if nextIdx < len(self.layoutLists):
                        maxRowWidth = 0
                        for lo in self.layoutLists[nextIdx]:
                            loWidth = icon.LIST_EMPTY_ARG_WIDTH if lo is None else lo.width
                            rowWidth = width + loWidth + icon.commaImage.width-2
                            heapq.heappush(rowBranches, (rowWidth, newRowLayout, lo))
                            maxRowWidth = max(maxRowWidth, rowWidth)
                    else:
                        maxRowWidth = width
                    self.finishedLayouts[rowStartIdx].append((maxRowWidth, newRowLayout))
            # Strip off relevance tags from finished layout list and return it along with
            # the margin at which the next change will happen to rows at this index
            finished = [rowLayout for _, rowLayout in self.finishedLayouts[rowStartIdx]]
            nextMarginChange = rowBranches[0][0] if len(rowBranches) > 0 else sys.maxsize
            return finished, nextMarginChange

        def cullRowLayouts(self, rowStartIdx, newRowLayout, margin):
            """Cull existing layouts in self.finishedLayouts[rowStartIdx] for the addition
            of a new rowLayout (newRowLayout) and relevance to a new margin.  Compares the
            new layout to each existing layout.  Removes any existing layouts that are
            provably worse, and returns True if the new layout should be added, or False
            if the new layout should be culled."""
            removedOffset = 0
            newWidth, newHeightAbove, newHeightBelow, newBadness, newSublayouts = \
                    newRowLayout
            newHeight = newHeightAbove + newHeightBelow
            newNItems = len(newSublayouts)
            for oldLayoutIdx, (oldLayoutRelevance, oldLayout) in enumerate(
                    tuple(self.finishedLayouts[rowStartIdx])):  # Copy to remove elements
                oldWidth, oldHeightAbove, oldHeightBelow, oldBadness, oldSublayouts = \
                        oldLayout
                oldHeight = oldHeightAbove + oldHeightBelow
                oldNItems = len(oldSublayouts)
                if oldLayoutRelevance < margin or oldHeight >= newHeight and \
                        oldBadness >= newBadness and oldNItems <= newNItems:
                    # Existing row layout is worse: cull it.  Since this is by index,
                    # indices for subsequent removals need to be adjusted (removedOffset)
                    del self.finishedLayouts[rowStartIdx][oldLayoutIdx - removedOffset]
                    removedOffset += 1
                elif newHeight >= oldHeight and newBadness >= oldBadness and \
                        newNItems <= oldNItems:
                    # Layout is worse than one of the existing layouts: don't add
                    return False
            return True

    def calcLayoutsAllCombos(self):
        """Deprecated version of calcLayouts for list manager that provides every
        possible layout for the list.  Deprecated because (obviously) every combination
        of a list of any significant size or complexity is a combinatorial explosion.
        Kept around for exploring layouts that the normal method will not generate."""
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if len(siteSeries) == 1 and siteSeries[0].att is None:
            # Empty Argument list leaves no space: (), [], {}
            layout = ListMgrLayout(self.siteSeriesName, ())
            layout.width = 1
            layout.height = icon.minTxtIconHgt
            return [layout]
        commaWidth = icon.commaImage.width - 1
        childLayoutLists = []
        for ic in (site.att for site in siteSeries):
            childLayoutLists.append((None,) if ic is None else ic.calcLayouts())
        layouts = []
        heightCull = 0
        for childLayouts in allCombinations(childLayoutLists, 200):
            # Figure out wrapping for margin widths beginning at the widest single item in
            # the list and increasing by whatever increment will trigger a change in wrap
            margin = max((1 if lo is None else lo.width for lo in childLayouts))
            prevHeight = sys.maxsize
            while True:
                height = 0
                rowWidth = 0
                rowHeightAbove = 0
                rowHeightBelow = 0
                nextWiderMargin = sys.maxsize
                rowXOffsets = []
                rowWidths = []
                siteOffsets = []
                for childLayout in childLayouts:
                    rowXOffsets.append(rowWidth)
                    if childLayout is None:
                        childWidth = icon.LIST_EMPTY_ARG_WIDTH
                        childHeightAbove = icon.minTxtIconHgt // 2
                        childHeightBelow = icon.minTxtIconHgt - childHeightAbove
                    else:
                        childWidth = childLayout.width
                        childHeightAbove = childLayout.parentSiteOffset
                        childHeightBelow = childLayout.height - childHeightAbove
                    rowWidth += childWidth + (0 if rowWidth == 0 else commaWidth)
                    if rowWidth > margin:  # Margin exceeded, wrap
                        nextWiderMargin = min(nextWiderMargin, rowWidth)
                        for x in rowXOffsets[:-1]:
                            siteOffsets.append((x, height + rowHeightAbove))
                        rowWidths.append(rowXOffsets[-1])
                        height += rowHeightAbove + rowHeightBelow
                        rowWidth = childWidth
                        rowHeightAbove = childHeightAbove
                        rowHeightBelow = childHeightBelow
                        rowXOffsets = [0]
                    else:
                        rowHeightAbove = max(rowHeightAbove, childHeightAbove)
                        rowHeightBelow = max(rowHeightBelow, childHeightBelow)
                for x in rowXOffsets:
                    siteOffsets.append((x, height + rowHeightAbove))
                rowWidths.append(rowWidth)
                height += rowHeightAbove + rowHeightBelow
                if height < prevHeight:  # Cull wider margin for same height
                    heightCull += 1
                    prevHeight = height
                    layout = ListMgrLayout(self.siteSeriesName, rowWidths)
                    if margin < height * 4:
                        layout.badness = ((height * 4) / margin - 1)*10
                    centerY = height // 2
                    for siteNum, childLayout in enumerate(childLayouts):
                        siteName = siteSeries[siteNum].name
                        x, y = siteOffsets[siteNum]
                        layout.addSubLayout(childLayout, siteName, x, y - centerY)
                    layout.width = margin
                    layouts.append(layout)
                if nextWiderMargin == sys.maxsize:
                    break
                margin = nextWiderMargin
        return cullLayoutList(layouts)

    def rename(self, newName):
        self.icon.sites.renameSeries(self.siteSeriesName, newName)
        self.siteSeriesName = newName

class ListMgrLayout(Layout):
    """Represents the part of an icon layout associated with a single variable-length
    list of icons managed by a ListLayoutMgr object."""
    def __init__(self, siteSeriesName, rowWidths):
        Layout.__init__(self, None, 0, 0, 0)
        self.siteSeriesName = siteSeriesName
        self.rowWidths = rowWidths

    def mergeInto(self, destLayout, xOff, yOff):
        """Merge this layout in to another layout (presumably that of the parent icon)."""
        destLayout.mergeLayout(self, xOff, yOff)
        setattr(destLayout, self.siteSeriesName + "ListMgrData", (self.width,
                self.height, self.siteOffsets, self.rowWidths))


def cullLayoutList(layouts):
    """Prune back a list of layouts for the same hierarchy.  Number of items to leave is
    based on the number of sublayouts that the layout represents.  The decision as to
    which layouts to cull is based on quality as determined by rankLayouts."""
    nSublayouts = layouts[0].subLayoutCount
    if nSublayouts <= 5:
        maxLayoutChoices = [1, 2, 2, 3, 3, 4][nSublayouts]
    elif nSublayouts <= 19:
        maxLayoutChoices = 5
    elif nSublayouts <= 300:
        maxLayoutChoices = 5 + nSublayouts // 20
    else:
        maxLayoutChoices = 20
    if len(layouts) > maxLayoutChoices:
        layouts = rankLayouts(layouts, maxLayoutChoices)
    # Remove any layouts that are provably worse than others in the set
    removed = set()
    for layout1 in layouts:
        if layout1 in removed:
            continue
        for layout2 in layouts:
            if layout2 is layout1 or layout2 in removed:
                continue
            if layout2.width >= layout1.width and layout2.height >= layout1.height and \
                    layout2.badness >= layout1.badness:
                removed.add(layout2)
    return [layout for layout in layouts if layout not in removed]

def rankLayouts(layouts, nReturned=sys.maxsize):
    """Given a list of layout objects, return a ranked list based on area and badness,
    culled to nReturned layouts."""
    minArea = sys.maxsize
    maxArea = 0
    maxBadness = 0
    for lo in layouts:
        area = lo.width * lo.height
        maxArea = max(maxArea, area)
        minArea = min(minArea, area)
        maxBadness = max(maxBadness, lo.badness)
    scoredLayouts = []
    for lo in layouts:
        area = lo.width * lo.height
        areaExpandFraction = (area - minArea) / minArea
        score = lo.badness + maxBadness * min(areaExpandFraction, 1.0)
        heapq.heappush(scoredLayouts, (score, lo))
    nReturned = min(len(layouts), nReturned)
    return [heapq.heappop(scoredLayouts)[1] for _ in range(nReturned)]

def allCombinations(lists, iterationLimit=None):
    """Iterate over all combinations of sublayouts in lists of sublayouts, yielding
    tuples containing one item from each list in lists. Each list must contain at
    least one item.  Items can be either a Layout or None.  If iterationLimit is
    specified, cull the number of combinations explored to (approximately) the given
    number.  Culling is based on badness and sparseness (see rankLayouts).  Rather than
    culling to equal length lists, we decide the length of each list by the (minimum)
    area it represents, therefore giving more options for (probably) more critical
    layouts."""
    totalIter = functools.reduce(operator.mul, (len(lst) for lst in lists))
    if iterationLimit is not None and totalIter > iterationLimit:
        numLists = len(lists)
        # The total number of combinations is above cull threshold
        # Calculate # of slots that will be allocated to each list
        #print("allCombinations culling to reduce iterations (%d, max %d).  Culling..." %
        #     (totalIter, iterationLimit))
        minAreas = [min((lo.width*lo.height for lo in loList)) for loList in lists]
        areaRank = list(zip(minAreas, range(numLists)))
        areaRank.sort(key=operator.itemgetter(0), reverse=True)
        slotsPerListAllocated = [1] * numLists
        numIter = 1
        while True:
            numAssigned = 0
            for _area, slot in areaRank:
                numAllocated = slotsPerListAllocated[slot]
                if len(lists[slot]) <= numAllocated:
                    continue
                newIter = numIter * (numAllocated + 1) / numAllocated
                if newIter > iterationLimit:
                    continue
                slotsPerListAllocated[slot] += 1
                numAssigned += 1
                numIter = newIter
            if numAssigned == 0:
                break
        # For each list, take the best n layouts based on badness and area
        for i, loList in enumerate(lists):
            lists = rankLayouts(lists, slotsPerListAllocated[i])
    # Return all combinations (the cartesian product) of items from all of the lists.
    yield from itertools.product(*lists)
