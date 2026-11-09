# Copyright Mark Edel  All rights reserved
import heapq
import functools
import itertools
from dataclasses import dataclass
import copy
import operator
import sys
import comn
import icon
import iconsites

# Number of pixels to indent wrapped expression continuation rows, not including the wrap
# indicator pixmap or additional indent is added to indicate nesting (see BRK_LVL_INDENT)
CONTINUATION_INDENT = 14 #15

# Number of pixels to add to indent of wrapped lines per increment of break-level (break-
# level represents precedence and nesting depth for the purpose of expression wrapping)
BRK_LVL_INDENT = 0

# Height above the top site and below the bottom site in pixels beyond the site image to
# which parens/brackets/braces and simple spines will be stretched for inline-wrapped
# lists.  Note that this does not apply to lists that fit within a single row, which get
# either an un-stretched paren/bracket/brace or no spine.
SPINE_SITE_Y_CLEARANCE = 5

# We don't particularly want to break at attribute boundaries, so set the level very high
ATTR_BRK_LVL = 50

class Layout:
    """Structure to store the information that the icon has calculated about how it
    should be laid out (in calcLayouts), until all the calculations are done and the
    layout is implemented (in doLayout).  The icon may also add its own externally-defined
    fields to the object for icon-specific data.  If setIconRect is set to True, will
    use the width and height values to initialize the prototype icon rectangle that
    expression-layouts accumulate.  indentDepthAdjust allows statement-level icons to
    have a portion that extends into the indent margin.  This is the number of pixels by
    which icons are to be shifted into the left margin.  It is used by icons that have a
    (normally invisible) input site that still allows the visible parts to left-align, or
    that shift a full indentation level (else, elif, except, etc.) left of the sequence
    line to which they actually attach."""
    # Note that the concept of a "layout rectangle" has decayed with the introduction of
    # wrapped expression layouts. Now that we have declared the layout origin to be fixed
    # in X at the attachment site, there is no representation of how far left of the
    # origin the layout extends.  This would be a one-line addition to addSubLayout to
    # maintain, but so far nothing uses it so there's no reason to waste data on it.

    # Sparsely populated attributes that may appear in some layouts
    wraps = None
    wrappedExprData = None
    containsBulkObject = False
    indentDepthAdj = 0

    def __init__(self, ico, width, height, siteYOffset, setIconRect=False,
            indentDepthAdj=0):
        self.icon = ico
        self.width = width
        self.height = height
        self.badness = 0
        # parentSiteOffset is the distance from the top of the layout to the site that
        # positions the icon.  For sequence sites, this is the seqInsert site, but
        # otherwise, output, attrOut, etc.  The layout origin is considered to be this
        # point on the left edge of the layout rectangle.
        self.parentSiteOffset = siteYOffset
        self.subLayoutCount = 0
        self.subLayouts = {}
        self.siteOffsets = {}  # relative to origin of layout (0, parentSiteOffset)
        if indentDepthAdj != 0:
            self.indentDepthAdj = indentDepthAdj
        # If layout was constructed from a wrapped-expression layout, since we're given
        # the footprints of all of the icon parts, we have enough information to pre-
        # calculate the icon rectangle and save the icon code from having to do it.
        if setIconRect:
            self.iconRectLeft = -indentDepthAdj
            self.iconRectTop = -siteYOffset
            self.iconRectRight = width
            self.iconRectBottom = height - siteYOffset
        else:
            self.iconRectLeft = None
            self.iconRectTop = None
            self.iconRectRight = None
            self.iconRectBottom = None

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

    def updateIconSites(self, originSiteOffset=None):
        """Transfer site positions calculated in the layout phase into the icon that
        the layout represents.  Icon site positions are relative to the icon rectangle.
        Layout site positions are relative to the implied site of the layout (on the left
        edge of the layout rectangle, parentSiteOffset from the top, and idealized to
        zero site depth).  If the layout was specified in expression-form (ExprLayout),
        updateIconSites will use the automatically generated icon rectangle (result of
        calcIconRect) for the conversion.  If the icon is not of a form that generates
        the icon rectangle or needs to change the rectangle, it must supply the parameter
        originSiteOffset as the position of the origin site for the layout relative to
        the icon rectangle. Also attaches wrap information from the layout to the icon.
        The convention for wrapped sites is that the site itself contains the location of
        the site on the parent icon, and the location of it's content is at the 'to'
        location specified in the .wraps dictionary entry for the site."""
        # Figure out offsets to convert from layout to icon rect coordinates
        parentSite = self.icon.sites.lookup(self.icon.anchorSite())
        parentSiteDepth = icon.siteDepths[parentSite.type]
        if originSiteOffset is None:
            if self.iconRectLeft is None:
                RuntimeError("updateIconSites w/o originSiteOffset and no rect data")
            layoutOriginXOff = -self.iconRectLeft + parentSiteDepth
            layoutOriginYOff = -self.iconRectTop
        else:
            originSiteXOffset, originSiteYOffset = originSiteOffset
            layoutOriginXOff = originSiteXOffset + parentSiteDepth
            layoutOriginYOff = originSiteYOffset
        # Fill in parent site and if this is a top-level icon (and the necessary
        # information was provided to the layout calculation).
        parentSite.xOffset = layoutOriginXOff - parentSiteDepth
        parentSite.yOffset = layoutOriginYOff
        if hasattr(self, 'seqInOutYOffsets'):
            xOffset = layoutOriginXOff + icon.SEQ_SITE_OFFSET + self.indentDepthAdj
            seqInYOffset, seqOutYOffset = self.seqInOutYOffsets
            seqInSite = self.icon.sites.lookup('seqIn')
            if seqInSite is not None:
                seqInSite.xOffset = xOffset
                seqInSite.yOffset = layoutOriginYOff - seqInYOffset
            seqOutSite = self.icon.sites.lookup('seqOut')
            if hasattr(self.icon, 'blockEnd'):
                xOffset += comn.BLOCK_INDENT
                seqOutYOffset += icon.BLOCK_SEQ_MARGIN
            elif self.icon.__class__.__name__ in ('ElifIcon', 'ElseIcon', 'ExceptIcon',
                    'FinallyIcon'):
                seqInSite.yOffset -= icon.PSEUDO_BLOCK_SEQ_MARGIN
                seqOutYOffset += icon.PSEUDO_BLOCK_SEQ_MARGIN
            if seqOutSite is not None:
                seqOutSite.xOffset = xOffset
                seqOutSite.yOffset = layoutOriginYOff + seqOutYOffset
        # Add or remove .wraps field to/from the icon, translating
        if self.wraps is None:
            # The layout does not specify wraps, clear the field in the icon.  The odd
            # method of deleting it from the instance dictionary to revert it to the
            # value (None) in the Icon class definition, might save some memory in the
            # long term (or might just waste cpu cycles), as owning wraps is a transient
            # and sparse property of icons.
            if self.icon.wraps is not None:
                del self.icon.wraps
            wraps = {}
        else:
            # The layout specifies wraps: transfer them to the icon and convert coords to
            # be site-depth positions relative to the icon rectangle origin
            wraps = self.wraps[0]
            wraps = self.offsetWrapList(wraps, layoutOriginXOff, layoutOriginYOff,
                includeSiteDepth=True)
            self.icon.wraps = wraps, self.wraps[1]
        if self.wrappedExprData is None:
            if self.icon.wrappedExprData is not None:
                del self.icon.wrappedExprData
        else:
            x, y = self.wrappedExprData
            self.icon.wrappedExprData = x + layoutOriginXOff, y + layoutOriginYOff
        # Update site offsets.  Note that siteOffsets can contain entries that are not
        # sites (used to pass non-site locations back to the icon doLayout code from the
        # layout process.
        for name, (xOffset, yOffset) in self.siteOffsets.items():
            site = self.icon.sites.lookup(name) if isinstance(name, str) else None
            if site is None:
                continue
            if name in wraps:
                # Assign wrapped sites their position on the parent icon, rather than the
                # (wrapped) location that its attached icon occupies (from the layout).
                # (Note that wraps[] has already been adjusted to icon coordinates)
                (fromX, fromY), _, _ = wraps[name]
                site.xOffset = fromX
                site.yOffset = fromY
            else:
                siteDepth = icon.siteDepths[site.type]
                site.xOffset = layoutOriginXOff + xOffset - siteDepth
                site.yOffset = layoutOriginYOff + yOffset
        # If the layout has set up icon-specific callbacks (such as filling in data
        # for list-managers), call them
        doLayoutCbs = getattr(self, 'doLayoutCallbacks', None)
        if doLayoutCbs is not None:
            for cb in doLayoutCbs:
                cb(self, layoutOriginXOff, layoutOriginYOff)

    def layoutToIconCoords(self, x, y, originSiteOffset=None):
        parentSite = self.icon.sites.lookup(self.icon.anchorSite())
        parentSiteDepth = icon.siteDepths[parentSite.type]
        if originSiteOffset is None:
            if self.iconRectLeft is None:
                RuntimeError("layoutToIconCoords w/o originSiteOffset and no rect data")
            layoutOriginXOff = -self.iconRectLeft + parentSiteDepth
            layoutOriginYOff = -self.iconRectTop
        else:
            originSiteXOffset, originSiteYOffset = originSiteOffset
            layoutOriginXOff = originSiteXOffset + parentSiteDepth
            layoutOriginYOff = originSiteYOffset
        return x + layoutOriginXOff, y + layoutOriginYOff

    def updateSiteOffsets(self, parentSite, parentSiteDepthAdj=0):
        """This is the obsolete original version of updateIconSites that does much less
        for the caller and requires a reference site to have already been configured.
        Icon site positions are relative to the icon rectangle.  Set them from the
        layout site positions, which are relative to the implied site of the layout
        (on the left edge of the layout rectangle, parentSiteOffset from the top, and
        idealized to zero site depth).  The parentSite argument should provide the site
        object (which has presumably already been positioned relative to the icon
        rectangle).  parentSiteDepthAdj can be specified if the parent site is not
        positioned at the standard depth (else, elif, except, finally).  Note that sites
        that are wrapped are incorrectly set to the wrapped location of their connected
        icon (where our convention is to set it to the location of the site itself).  We
        can't do that here because the icon's .wrap field is not yet set up, but this is
        automatically corrected in the post-processing pass that sets up that field."""
        parentSiteDepth = icon.siteDepths[parentSite.type] + parentSiteDepthAdj
        for name, layout in self.subLayouts.items():  #... why not loop over siteOffsets?
            site = self.icon.sites.lookup(name)
            siteDepth = icon.siteDepths[site.type]
            xOffset, yOffset = self.siteOffsets[name]
            site.xOffset = parentSite.xOffset + parentSiteDepth - siteDepth + xOffset
            site.yOffset = parentSite.yOffset + yOffset
        # Add or remove .wraps field to/from the icon, translating
        if self.wraps is None:
            # The layout does not specify wraps, clear the field in the icon.  The odd
            # method of deleting it from the instance dictionary to revert it to the
            # value (None) in the Icon class definition, might save some memory in the
            # long term (or might just waste cpu cycles), as owning wraps is a transient
            # and sparse property of icons.
            if self.icon.wraps is not None:
                del self.icon.wraps
        else:
            # The layout specifies wraps: transfer them to the icon and convert coords to
            # be site-depth positions relative to the icon rectangle origin
            parentSite = self.icon.sites.lookup(self.icon.anchorSite())
            parentSiteDepth = icon.siteDepths[parentSite.type] - self.indentDepthAdj
            layoutOriginXOff = parentSite.xOffset + parentSiteDepth
            layoutOriginYOff = parentSite.yOffset
            wraps = self.wraps[0]
            wraps = self.offsetWrapList(wraps, layoutOriginXOff, layoutOriginYOff,
                includeSiteDepth=True)
            self.icon.wraps = wraps, self.wraps[1]

    def calcIconRect(self, outSiteX, outSiteY):
        """If the layout came from an ExprLayout (most icons), we have pre-calculated the
        icon rectangle, and just need to add the icon coordinates and protruding site
        width (layout-form disregards this).  Note that there are two forms for this
        call due to the dumb convention of laying out icons with sequence sites by top,
        left and icons with output-type sites by output site position: for icons with
        sequence sites only, use calcIconRectByLeftTop."""
        outSite = self.icon.anchorSite()
        if outSite is None or outSite == 'seqInsert':
            raise RuntimeError('calcIconRect called for icon with no output-type site')
        if self.iconRectLeft is None:
            return None
        outSiteType = self.icon.typeOf(outSite)
        siteDepth = icon.siteDepths[outSiteType]
        #... this should be removed
        # Note that self.indentDepthAdj is included below only to stop it from getting
        # lost if the 'byTopLeft' layout methods are removed.  We clearly can't dedent
        # anything but top-level statements and will only ever be set on such statements.
        left = outSiteX + self.iconRectLeft + self.indentDepthAdj
        top = outSiteY + self.iconRectTop
        right = outSiteX + siteDepth + self.iconRectRight
        bottom = outSiteY + self.iconRectBottom
        return left, top, right, bottom

    def calcIconRectByLeftTop(self, left, top):
        """If the layout came from an ExprLayout (most icons), we have pre-calculated the
        icon rectangle, and just need to add the icon coordinates and protruding site
        width (layout-form disregards this).  Note that there are two forms for this
        call due to the dumb convention of laying out icons with sequence sites by top,
        left and icons with output-type sites by output site position: for icons with
        output-type sites only, use calcIconRect."""
        if not self.icon.hasSite('seqInsert'):
            raise RuntimeError('calcIconRectByLeftTop called for non sequence-only icon')
        outSite = self.icon.anchorSite()
        outSiteType = self.icon.typeOf(outSite)
        siteDepth = icon.siteDepths[outSiteType]
        #left -= self.indentDepthAdj
        right = left + self.iconRectRight - self.iconRectLeft + siteDepth
        bottom = top + self.iconRectBottom - self.iconRectTop
        return left, top, right, bottom

    # Remove params once no icon uses them
    def doSubLayouts(self, parentSite=None, outSiteX=None, outSiteY=None):
        """Call doLayout on all icons listed in the subLayouts list of the layout.  Args
        are for legacy code that may not set up the icon rectangle before calling."""
        if parentSite is None:
            xOrigin, yOrigin, _, _ = self.icon.rect
        else:
            xOrigin = outSiteX - parentSite.xOffset
            yOrigin = outSiteY - parentSite.yOffset
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name) if isinstance(name, str) else None
            if site is None or site.att is None:
                continue
            if self.icon.wraps is not None and name in self.icon.wraps[0]:
                (fromX, fromY), (toX, toY), _ = self.icon.wraps[0][name]
                x = xOrigin + toX
                y = yOrigin + toY
            else:
                x = xOrigin + site.xOffset
                y = yOrigin + site.yOffset
            site.att.doLayout(x, y, layout)

    def mergeLayout(self, layoutToMerge, xOff, yOff, expandIconRect=False):
        """Expand the current layout (self) to encompass layoutToMerge at reference
        location (xOff, yOff) relative to the reference location of the layout
        (0, self.parentSiteOffset)."""
        self.width = max(self.width, xOff + layoutToMerge.width)
        heightAbove = max(self.parentSiteOffset, layoutToMerge.parentSiteOffset - yOff)
        heightBelow = max(self.height - self.parentSiteOffset,
                yOff + layoutToMerge.height - layoutToMerge.parentSiteOffset)
        self.height = heightAbove + heightBelow
        self.parentSiteOffset = heightAbove
        if expandIconRect and layoutToMerge.iconRectLeft is not None:
            left = layoutToMerge.iconRectLeft + xOff
            top = layoutToMerge.iconRectTop + yOff
            right = layoutToMerge.iconRectRight + xOff
            bottom = layoutToMerge.iconRectBottom + yOff
            if self.iconRectLeft is None:
                self.iconRectLeft = left
                self.iconRectTop = top
                self.iconRectRight = right
                self.iconRectBottom = bottom
            else:
                self.iconRectLeft = min(left, self.iconRectLeft)
                self.iconRectTop = min(top, self.iconRectTop)
                self.iconRectRight = max(right, self.iconRectRight)
                self.iconRectBottom = max(bottom, self.iconRectBottom)
        self.badness += layoutToMerge.badness
        self.subLayoutCount += layoutToMerge.subLayoutCount
        self.subLayouts.update(layoutToMerge.subLayouts)
        for siteName, siteOffset in layoutToMerge.siteOffsets.items():
            self.siteOffsets[siteName] = siteOffset[0] + xOff, siteOffset[1] + yOff

    def _expandIconRectDataForWraps(self):
        """Update the layout icon-rectangle data to incorporate wrap arrows."""
        if self.wraps is None:
            return
        for siteId, ((fromX, fromY), (toX, toY), _) in self.wraps[0].items():
            fromImage, _, toImage, _ = icon.wrapArrowImagesForSite(self.icon, siteId)
            if self.iconRectLeft is None:
                # This rectangle will probably not be used, as the icon has not populated
                # anything, but fill it in anyhow.
                self.iconRectLeft = toX - toImage.width
                self.iconRectTop = fromX + fromImage.width
                self.iconRectRight = fromY - fromImage.height // 2
                self.iconRectBottom = toY + toImage.height // 2
            else:
                self.iconRectLeft = min(toX - toImage.width, self.iconRectLeft)
                self.iconRectRight = max(fromX + fromImage.width, self.iconRectRight)
                self.iconRectTop = min(fromY - fromImage.height // 2, self.iconRectTop)
                self.iconRectBottom = max(toY + toImage.height // 2, self.iconRectBottom)

    #... This method is currently not used and already known to be out of date, so
    #    either use it and fix it, or remove it.
    def expandIconRectForWraps(self, rect):
        """Return updated rect (does not modify self.icon.rect) to encompass any wrap
        arrows that the icon owns."""
        ic = self.icon
        origL, origT, origR, origB = rect
        newL, newT, newR, newB = rect
        if ic.wraps is not None:
            for siteName, ((fromX, fromY), (toX, toY), _) in ic.wraps[0].items():
                fromXAbs = fromX + origL
                toXAbs = toX + origL
                fromYAbs = fromY + origT
                toYAbs = toY + origT
                site = self.icon.sites.lookup(siteName)
                siteDepth = icon.siteDepths[site.type]
                newL = min(toXAbs + siteDepth - icon.wrapToImage.width, fromXAbs, newL)
                newR = max(toXAbs, fromXAbs + icon.wrapFromImage.width, newR)
                newT = min(fromYAbs - icon.wrapFromImage.height // 2, newT)
                newB = max(toYAbs + icon.wrapToImage.height // 2, newB)
                if newT < rect[1]:
                    print('Did not expect wraps to expand icon rectangle upwards')
        return newL, newT, newR, newB

    def offsetWrapList(self, wrapList, xOffset, yOffset, includeSiteDepth=False):
        """Offset the wrap site positions for the wrap data for a single icon.  If
        includeSiteDepths is set to True, will subtract additional offset to convert
        from body position to site position."""
        newWrapList = {}
        for siteName, ((fromX, fromY), (toX, toY), boundaryY) in wrapList.items():
            if includeSiteDepth:
                if isinstance(siteName, int):
                    siteDepth = 0
                else:
                    site = self.icon.sites.lookup(siteName)
                    siteDepth = 0 if site is None else icon.siteDepths[site.type]
            else:
                siteDepth = 0
            newWrapList[siteName] = (fromX + xOffset - siteDepth, fromY + yOffset), \
                (toX + xOffset - siteDepth, toY + yOffset), boundaryY + yOffset
        return newWrapList

    def addDoLayoutCallback(self, cb):
        """Attach a callback to the layout to be executed by the icon's doLayout method
        (via the updateSites call).  This allows an icon's layout specification (in
        its calcLayouts method) to specify code to be executed on the winning layout.  It
        is usually used to avoid having the caller responsible for internal complexities
        of the layout process, beyond just specifying the type of layout."""
        if not hasattr(self, 'doLayoutCallbacks'):
            self.doLayoutCallbacks = []
        self.doLayoutCallbacks.append(cb)

class ListLayoutMgr:
    """Manage layout for a one-dimensional list of icon arguments.  An icon can have
    multiple argument lists, and each list should have its own ListLayoutMgr.  By default,
    the icon is responsible for drawing parens/brackets/braces around the list.  However
    for icons that don't draw these, a "simple spine" (minimal visual grouping guide to
    help the user associate the list with the parent icon) can be requested that will
    appear when the list becomes multi-row.  Both the layout and the .width attribute
    incorporate the additional space where the spine will draw, but the caller must
    invoke drawSimpleSpine to actually draw it.  Also handles the simpler case of
    expression-wrapped lists, where most of the work is done by the expression wrapping
    code, and the most common case where both layout types are supported.  Control for
    this is via the layoutType parameter which can be set to any of 'alwaysExpr',
    'defaultExpr', 'alwaysInline', or 'defaultInline', which select either expression
    wrapping or inline wrapping (always...), or selectable via the window Settings dialog
    with the given default (default...)."""
    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY, simpleSpine=False,
            cursorTraverseOrder=None, allowsTrailingComma=False,
            layoutType='defaultExpr'):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        self.simpleSpine = simpleSpine
        self.allowsTrailingComma = allowsTrailingComma
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)],
            cursorTraverseOrder=cursorTraverseOrder)
        self.width = 0
        self.height = icon.minTxtIconHgt
        self.spineHeight = icon.minTxtIconHgt
        self.spineTop = icon.minTxtIconHgt // 2
        self.bodySitePositions = None
        self.commaSitePositions = None
        self.bodySiteIdxs = None
        self.rowWidths = None
        self.layoutType = layoutType
        self.exprEndParenPos = None

    def inlineLayout(self):
        """Returns True if the the list either defaults to inline layout (list, tuple,
        dict), or is overridden by application settings to display all series inline."""
        window = self.icon.window
        return self.layoutType == 'alwaysInline' or \
            self.layoutType == 'defaultExpr' and window.settings.inlineWrapAllLists or \
            self.layoutType == 'defaultInline' and not window.settings.noInlineWrap

    def appendToExprLayout(self, exprLayout, brkLvl=0, argRequired=False,
            allowTrailingComma=True, marginLimit=None):
        """Add layouts for list elements and commas to an expression-wrapping layout.
        This works for both inline-style and expression-wrapped layouts, but if inline-
        wrapped layouts are allowed, you must specify argRequired.  The call also assumes
        that the first site (siteName_0) is attached to an icon part, and expects that
        the expression already contains that part and the part is already labeled with
        the appropriate site name.  Also note that brkLvl provides the break level
        between the preceding part or layout and the list (the break level between
        elements is always set to 0).  For icons that draw spines (as opposed to just
        using the built-in simple-spines) brkLvl must be set to None."""
        if self.inlineLayout():
            if marginLimit is None:
                listLayouts = LazyLayout(self, argRequired=argRequired)
            else:
                listLayouts = self.calcLayouts(argRequired=argRequired,
                    marginLimit=marginLimit)
            # allowTrailingComma is not being enforced on inline layouts.  I think this
            # is ok at least for core python, since I believe it's only used on the
            # Subscript icon, which has no real need inline-wrapping.
            exprLayout.appendLayout(brkLvl, listLayouts)
        else:
            siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
            lastExprPart = exprLayout.partLayouts[-1]
            if not (isinstance(lastExprPart, _ExprPartLayout) and
                    lastExprPart.siteName == siteSeries[0].name):
                print("appendToExprLayout called without initial series site")
                siteYOffset = 0
            else:
                siteYOffset = lastExprPart.siteYOffset
            for i, site in enumerate(siteSeries):
                if i > 0:
                    exprLayout.appendPart(None, self.icon, site.name,
                        icon.commaImage.width, icon.commaImage.height,
                        icon.commaImageSiteYOffset - siteYOffset, siteYOffset)
                argIcon = site.att
                if argIcon is None:
                    if i == len(siteSeries) - 1 and allowTrailingComma:
                        continue
                    argLayout = EmptyArgLayout(self.icon, site.name, forListArg=True)
                else:
                    argLayout = LazyLayout(argIcon)
                    pushBrkLvl(argLayout)
                exprLayout.appendLayout(brkLvl if i==0 else 0, argLayout)
            # Append an empty marker part to use for computing end-paren position, and
            # add a doLayout callback to pass the winning layout's result to the layout
            # manager(and otherwise clear unused fields.
            exprLayout.appendPart(None, self.icon,
                self.siteSeriesName + 'EndParenMarker', 1, 0, -siteYOffset, siteYOffset)
            exprLayout.addDoLayoutCallback(self.doLayoutExprList)

    #... get rid of leftSiteX and leftSiteY in callers
    def drawListCommas(self, leftSiteX=None, leftSiteY=None, typeoverIdx=None):
        sites = getattr(self.icon.sites, self.siteSeriesName)
        if self.inlineLayout():
            if self.commaSitePositions is None:
                print("ListLayoutMgr draw before layout")
                return []
            commaIdxs = [s[0] for s in self.commaSitePositions]
        else:
            commaIdxs = range(1, len(sites))
        xOff = icon.inSiteImage.width - icon.commaImage.width
        yOff = -icon.commaImageSiteYOffset
        drawList = []
        for siteIdx in commaIdxs:
            site = sites[siteIdx]
            img = icon.commaTypeoverImage if siteIdx == typeoverIdx else icon.commaImage
            drawList.append(((site.xOffset + xOff, site.yOffset + yOff), img))
        return drawList

    def drawBodySites(self, bodyImg):
        xOff = bodyImg.width - icon.inSiteImage.width
        if not self.inlineLayout():
            yOff = bodyImg.height // 2 - icon.inSiteImage.height // 2
            bodyImg.paste(icon.inSiteImage, (xOff, yOff), mask=icon.inSiteMask)
            return
        yOff = self.spineTop - icon.inSiteImage.height // 2
        if self.bodySitePositions is None:
            print("ListLayoutMgr drawing before layout")
            return
        for x, y in self.bodySitePositions:
            bodyImg.paste(icon.inSiteImage, (x + xOff, y + yOff), mask=icon.inSiteMask)

    #... remove unused parameters once callers are converted
    def drawSimpleSpine(self, leftSiteXxx=None, leftSiteYxx=None, drawOutputSite=True):
        """Returns left and right spine images suitable for an icon draw list for the
        minimal "simple spine" used by icons which do not draw parens/brackets/braces
        around argument lists.  If drawOutputSite is specified as False, the spine will
        not include an output site (but note that position is still specified as if it
        were on an output site, two pixels left of the spine)."""
        if not self.simpleSpineWillDraw():
            return []
        return self.drawParens(icon.lSimpleSpineImage, icon.simpleSpineExtendDupRows,
            icon.rSimpleSpineImage, icon.simpleSpineExtendDupRows,
            drawOutputSite='output' if drawOutputSite else None)

    def drawParens(self, lImg, lImgExtDupRows, rImg=None, rImgExtDupRows=None,
            drawOutputSite=None, drawInputSite=None):
        """Create drawList entries for parens or spines for both inline and expression
        layouts.  In the inline case, stretch the images at the points listed in
        lImgExtDupRows and rImgExtDupRows (see icon.yStretchImage).  If drawOutputSite
        or drawInputSite are set to icon siteIds a site of the appropriate type will
        be drawn on the images.  Note that for the output site (on left paren) be sure
        to leave horizontal space for site drawing in lImg."""
        if self.inlineLayout():
            # Inline layout: stretch spines and draw body sites
            if self.bodySitePositions is None:
                print("ListLayoutMgr drawing spine before layout")
                return []
            lSpine = icon.yStretchImage(lImg, lImgExtDupRows, self.spineHeight)
            leftX, leftY = self.spineOutSiteOffset(spineWidth=lImg.width)
            leftY -= self.spineTop
            if rImg is None:
                rSpine = None
                rightX = rightY = 0
            else:
                # Note that simple spine width is included in layout versus explicit parens,
                # which are not included in layout width.
                contentWidth = self.width - (2 * (rImg.width - 1) if self.simpleSpine else 0)
                rightX = leftX + lImg.width + contentWidth - 2
                rightY = leftY
                self.drawBodySites(lSpine)
                rSpine = icon.yStretchImage(rImg, rImgExtDupRows, self.spineHeight)
            outSiteYOffset = inSiteYOffset = self.spineTop
        else:
            # Expression layout: just draw normal parens
            sites = getattr(self.icon.sites, self.siteSeriesName)
            leftSite = sites[0]
            leftX = leftSite.xOffset + icon.OUTPUT_SITE_DEPTH - lImg.width
            outSiteYOffset = lImg.height // 2
            leftY = leftSite.yOffset - outSiteYOffset
            if rImg is None:
                rightX = rightY = inSiteYOffset = 0
            else:
                if self.exprEndParenPos is not None:
                    rightX, rightY = self.exprEndParenPos
                else:
                    print("ListLayoutMgr could not find end paren location")
                    rightX = rightY = 0
                inSiteYOffset = rImg.height // 2
                rightY -= inSiteYOffset
            lSpine = lImg.copy() if drawOutputSite else lImg
            rSpine = rImg.copy() if rImg is not None and drawInputSite else rImg
        # If site drawing is requested, figure out what site type to draw and modify the
        # lSpine and rSpine images generated above (these are guaranteed to be copies
        # and not originals by the code above).
        if drawOutputSite:
            outSiteType = self.icon.typeOf(drawOutputSite)
            if outSiteType == 'output':
                outSiteImg = icon.outSiteImage
                outSiteY = outSiteYOffset - outSiteImg.height // 2
            elif outSiteType == 'attrOut':
                outSiteImg = icon.dimAttrOutImage  # usually don't want dot before paren
                outSiteY = outSiteYOffset - outSiteImg.height // 2 + icon.ATTR_SITE_OFFSET
            else:
                print("_drawParens can't draw site of type:", outSiteType)
                outSiteImg = icon.outSiteImage
                outSiteY = outSiteYOffset - outSiteImg.height // 2
            lSpine.paste(outSiteImg, (0, outSiteY), mask=outSiteImg)
        if drawInputSite and rImg is not None:
            inSiteType = self.icon.typeOf(drawInputSite)
            if inSiteType == 'input':
                inSiteImg = icon.inSiteImage
                inSiteMask = icon.inSiteMask
                inSiteY = inSiteYOffset - inSiteImg.height // 2
            elif inSiteType == 'attrIn':
                inSiteImg = icon.attrInImage
                inSiteMask = icon.attrInImage
                inSiteY = inSiteYOffset - inSiteImg.height // 2 + icon.ATTR_SITE_OFFSET
            else:
                print("_drawParens can't draw site of type:", inSiteType)
                inSiteImg = icon.inSiteImage
                inSiteMask = icon.inSiteMask
                inSiteY = inSiteYOffset - inSiteImg.height // 2
            inSiteX = rSpine.width - inSiteImg.width
            rSpine.paste(inSiteImg, (inSiteX, inSiteY), mask=inSiteMask)
        if rImg is None:
            return [((leftX, leftY), lSpine)]
        return [((leftX, leftY), lSpine), ((rightX, rightY), rSpine)]

    def spineOutSiteOffset(self, preWrap=False, spineWidth=None):
        """Return the theoretical (not drawn) output site x, y offset from the icon
        origin for the inline-wrapped spine if it would draw, or the position of the
        first site in the series if it's expression-wrapped or no spine would draw.
        If preWrap is True and the site is expression-wrapped, return the position of
        the site before the wrap.  If the layout is drawn with explicit parens rather
        than simple spines, specify the width, INCLUDING SITE DEPTH for the LEFT
        spine/paren for the list."""
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if self.icon.wraps is not None:
            if siteSeries[0].name in self.icon.wraps[0]:
                fromPos, toPos, _ = self.icon.wraps[0][siteSeries[0].name]
                if preWrap:
                    return fromPos
                else:
                    return toPos
            # In the expression wrapped case when there's a wrap before a spine, the
            # wrap becomes a no-site wrap and gets reassigned to the series name.  Since
            # we promised to return the 'site' position (even though this is not used
            # for anything site-related), also correct the x coord to site depth
            if self.siteSeriesName in self.icon.wraps[0]:
                (fromX, fromY), (toX, toY), _ = self.icon.wraps[0][self.siteSeriesName]
                if preWrap:
                    return fromX - icon.OUTPUT_SITE_DEPTH, fromY
                else:
                    return toX - icon.OUTPUT_SITE_DEPTH, toY
        siteX = siteSeries[0].xOffset
        siteY = siteSeries[0].yOffset
        if self.simpleSpineWillDraw():
            return siteX - (icon.rSimpleSpineImage.width - 1), \
                siteY - self.bodySitePositions[0][1]
        if spineWidth is not None:
            return siteX - spineWidth + 1 + icon.OUTPUT_SITE_DEPTH,\
                siteY - self.bodySitePositions[0][1]
        return siteX, siteY

    def simpleSpineWillDraw(self, isMultiRow=None):
        """Return True if ListLayoutMgr has simpleSpine enabled and the chosen layout
        (last doLayout call) was multi-row (requires drawSimpleSpine call and includes
        space for drawing the simple spine).  isMultiRow can be omitted (passed as None)
        if the list manager has been configured with layout data.  If not, it must be set
        to True or False based upon what sort of layout we will be constructing."""
        if isMultiRow is None:
            isMultiRow = self.isMultiRow()
        return self.inlineLayout() and self.simpleSpine and isMultiRow

    def isMultiRow(self):
        return self.rowWidths and len(self.rowWidths) >= 2

    def makeInsertSnapList(self):
        """Generate snap sites for series item insertion"""
        insertSites = []
        inputSites = self.icon.sites.getSeries(self.siteSeriesName)
        if not (len(inputSites) > 1 or inputSites[0].att is not None):
            return []
        # Add site positions for the sites themselves
        x, y = self.icon.rect[:2]
        y += icon.SERIES_INSERT_SITE_Y_OFFSET
        minXOffset = inputSites[0].xOffset
        for i, site in enumerate(inputSites):
            xOff = x + site.xOffset
            if site.xOffset != minXOffset:
                xOff += icon.SERIES_INSERT_SITE_X_OFFSET
            insertSites.append((self.icon, (xOff, y + site.yOffset), site.name))
        # Add additional sites for wraps (both inline and expression-wrap)
        numInputSites = len(inputSites)
        if self.inlineLayout():
            if self.bodySitePositions is None:
                return []
            bodySiteXOffset = inputSites[0].xOffset - self.bodySitePositions[0][0]
            bodySiteYOffset = inputSites[0].yOffset - self.bodySitePositions[0][1]
            for i, rowWidth in enumerate(self.rowWidths):
                bodySite = self.icon.sites.getSeries(self.siteSeriesName) \
                    [self.bodySiteIdxs[i]]
                bodySiteIcon = bodySite.att
                if bodySiteIcon is not None and bodySiteIcon.wrappedExprData is not None:
                    # If the row consists of a wrapped expression (always single icon),
                    # the insert site can't simply be placed at the end of the row, and
                    # instead must be placed at the end of the expression
                    siteX, siteY = bodySite.att.wrappedExprData
                    siteX += bodySiteIcon.rect[0]
                    siteY += bodySiteIcon.rect[1] + icon.SERIES_INSERT_SITE_Y_OFFSET
                else:
                    _siteX, siteY = self.bodySitePositions[i]
                    siteX = x + bodySiteXOffset + rowWidth
                    siteY += y + bodySiteYOffset
                if i < len(self.rowWidths) - 1:
                    siteName = iconsites.makeSeriesSiteId(self.siteSeriesName,
                            self.bodySiteIdxs[i+1])
                else:
                    siteName = iconsites.makeSeriesSiteId(self.siteSeriesName,
                        numInputSites)
                insertSites.append((self.icon, (siteX, siteY), siteName))
        else:  # Expression-wrapped layout
            if self.icon.wraps is not None:
                for siteName, (_, (toX, toY), _) in self.icon.wraps[0].items():
                    if not isinstance(siteName, str) or not self.icon.hasSite(siteName):
                        continue  # Wraps are allowed not to be sites
                    insertSites.append((self.icon, (x + toX, y + toY), siteName))
                # Because we don't have access to the original data used to calculate
                # wraps (as we do for inline), we have to follow the icons from the last
                # comma to determine the rightmost insert site.
                siteX, siteY = self._rightmostInsertSitePos(inputSites[-1].name)
                siteName = iconsites.makeSeriesSiteId(self.siteSeriesName, numInputSites)
                insertSites.append((self.icon, (siteX, siteY), siteName))
        return insertSites

    def _rightmostInsertSitePos(self, siteName):
        """Find the position of the rightmost site of the rightmost icon attached to the
        series at siteName, and adjust it to the appropriate insert site X and Y to
        follow that expression.  Used for finding the correct insert position following
        wrapped expressions."""
        rightIc, rightSiteName = icon.rightmostFromSite(self.icon, siteName)
        rightSite = rightIc.sites.lookup(rightSiteName)
        x, y = rightIc.rect[:2]
        siteX = x + rightSite.xOffset + icon.siteDepths[rightSite.type]
        siteY = y + rightSite.yOffset - icon.siteOffsets[rightSite.type] + \
                icon.SERIES_INSERT_SITE_Y_OFFSET
        return siteX, siteY

    def doLayout(self, layout, loToIconX=None, loToIconY=None):
        if self.inlineLayout():
            return self.doLayoutInline(layout)
        else:
            print('ListMgr.doLayout called on a non-inline layout')
            return

    def doLayoutInline(self, layout):
        """Updates spine position for the list as calculated in the calcLayouts method.
        This does not call doLayout for the icons in the list (but calcLayouts adds the
        information to the icon layout such that layout.doSubLayouts will do them along
        with the rest of the attached icons)."""
        # layout for managed list gets merged in to layout of entire icon. List-specific
        # data is added as an attribute based on site name
        self.width, self.height, siteOffsets, self.rowWidths = getattr(layout,
                self.siteSeriesName + 'ListMgrData')
        leftSublayoutOffset = siteOffsets[self.siteSeriesName + '_0'][0]
        self.commaSitePositions = []
        self.bodySitePositions = []
        self.bodySiteIdxs = []
        for i, offset in enumerate(siteOffsets.values()):
            if offset[0] == leftSublayoutOffset:
                self.bodySitePositions.append(offset)
                self.bodySiteIdxs.append(i)
            else:
                self.commaSitePositions.append((i, offset))
        # Decide the y extent of the spine, which must include the anchor point (y == 0),
        # the body sites, and if the last site is expression wrapped, the last row of
        # wrapping (which I'm not sure why, but seems to be aesthetically necessary)
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        minSiteY = min(0, siteOffsets[siteSeries[0].name][1])
        lastSiteName = siteSeries[-1].name
        lastSiteY = siteOffsets[lastSiteName][1]
        lastSitelayout = layout.subLayouts[lastSiteName]
        if lastSitelayout is None or lastSitelayout.wrappedExprData is None:
            maxSiteY = max(0, lastSiteY)
        else:
            maxSiteY = max(0, lastSiteY + lastSitelayout.wrappedExprData[1])
        if minSiteY == sys.maxsize or maxSiteY == minSiteY:
            self.spineHeight = icon.minTxtIconHgt
            self.spineTop = icon.minTxtIconHgt // 2
        else:
            self.spineHeight = maxSiteY - minSiteY + icon.inSiteImage.height + \
                2 * SPINE_SITE_Y_CLEARANCE
            self.spineTop = -minSiteY + icon.inSiteImage.height // 2 + \
                SPINE_SITE_Y_CLEARANCE
        self.exprEndParenPos = None

    def doLayoutExprList(self, layout, loToIconX, loToIconY):
        x, y = layout.siteOffsets[self.siteSeriesName + 'EndParenMarker']
        self.exprEndParenPos = x + loToIconX, y + loToIconY
        self.bodySitePositions = None
        self.commaSitePositions = None
        self.bodySiteIdxs = None
        self.rowWidths = None
        self.spineHeight = 0
        self.spineTop = 0

    def exprCommaRect(self, layout, layoutOriginX, layoutOriginY):
        """Extracts comma positions from the layout generated for the icon containing
        the list being managed, and calculates the smallest rectangle covering all of
        the commas given the layout positioned at the given (output site) position
        (layoutOriginX, layoutOriginY)."""
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        minX, minY = layout.siteOffsets[siteSeries[0].name]
        maxX = minX
        maxY = minY
        for site in siteSeries[1:]:
            loX, loY = layout.siteOffsets[site.name]
            minX = min(minX, loX)
            minY = min(minY, loY)
            maxX = max(maxX, loX)
            maxY = max(maxY, loY)
        minX -= icon.commaImage.width
        minY -= icon.commaImageSiteYOffset
        maxY += icon.commaImage.height - icon.commaImageSiteYOffset
        return minX + layoutOriginX, minY + layoutOriginY, maxX + layoutOriginX, \
            maxY + layoutOriginY

    def calcLayouts(self, argRequired=False, marginLimit=999999999):
        """Create a list of ListMgrLayout structures (incomplete Layout structures which
        can be merged in to the owning icon's Layouts using mergeLayout (Layout) or
        mergeInto (additional method of ListMgrLayout) object."""
        # Avoiding combinatorial explosion with all the possible layouts, is extremely
        # challenging.  Simply exploring all combinations of sublayouts for all possible
        # list dimensions, can explode far beyond keypress time for even short lists.  The
        # method used here, is to work from narrow layouts to wide ones, caching the work
        # expended to layout the start of each row, and culling per-row as the layout
        # develops.
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if len(siteSeries) == 1 and siteSeries[0].att is None:
            # Empty argument list
            layout = ListMgrLayout(self.siteSeriesName, (), self)
            layout.addSubLayout(None,  siteSeries[0].name, 0, 0)
            if argRequired:  # If user must supply an arg, leave room for highlight
                layout.width = icon.LIST_EMPTY_ARG_WIDTH
            else:  # Non-required lists get no space: (), [], {}
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
                if isinstance(childLayoutList, ExprLayout):
                    # If we get an expression layout, wrap it (which converts to a single
                    # Layout object)
                    childLayoutList = [childLayoutList.wrap(marginLimit)]
                minWidth = min((lo.width for lo in childLayoutList))
            childLayoutLists.append(childLayoutList)
            margin = max(margin, minWidth)
        rowLayoutMgr = self.RowLayoutManager(childLayoutLists,
            self.allowsTrailingComma)
        finishedLayouts = []
        # Loop, increasing margin until we 1) exhaust all layouts (margin == sys.maxsize),
        # or 2) hit the requested margin limit with at least one acceptable choice.
        while margin < sys.maxsize and not (margin > marginLimit and
                len(finishedLayouts) > 0):
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
            for height, rowData, badness, sublayouts in perMarginLayouts:
                leftSublayoutOffset = icon.rSimpleSpineImage.width - 1 \
                    if self.simpleSpine and len(rowData) >= 2 else 0
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
                    lo = ListMgrLayout(self.siteSeriesName, rowWidths, self)
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
                        x += (self.emptyArgWidth(siteNum) if sublayout is None else
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

        def __init__(self, layoutLists, allowsTrailingComma):
            self.layoutLists = layoutLists
            maxRows = len(layoutLists)
            self.finishedLayouts = [[] for _ in range(maxRows)]
            self.branchesToProcess = [None] * maxRows
            self.allowsTrailingComma = allowsTrailingComma

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
                for loIdx, lo in enumerate(self.layoutLists[rowStartIdx]):
                    loWidth = self.emptyArgWidth(rowStartIdx, loIdx) if lo is None \
                        else lo.width
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
                        for loIdx, lo in enumerate(self.layoutLists[nextIdx]):
                            loWidth = self.emptyArgWidth(nextIdx, loIdx) if lo is None \
                                else lo.width
                            rowWidth = width + loWidth + icon.commaImage.width-2
                            heapq.heappush(rowBranches, (rowWidth, newRowLayout, lo))
                            maxRowWidth = max(maxRowWidth, rowWidth)
                    else:
                        maxRowWidth = width
                    self.finishedLayouts[rowStartIdx].append((maxRowWidth, newRowLayout))
                # if we've consumed an expression-wrapped layout that has wraps in it,
                # end the row, since we don't want commas at intermediate levels.
                if newItemLayout is not None and newItemLayout.wrappedExprData is not \
                        None:
                    nextMarginChange = sys.maxsize
                    break
            else:
                nextMarginChange = rowBranches[0][0] if len(
                    rowBranches) > 0 else sys.maxsize
            # Strip off relevance tags from finished layout list and return it along with
            # the margin at which the next change will happen to rows at this index
            finished = [rowLayout for _, rowLayout in self.finishedLayouts[rowStartIdx]]
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

        def emptyArgWidth(self, rowStartIdx, layoutIdx):
            nElems = len(self.layoutLists)
            if self.allowsTrailingComma and \
                    rowStartIdx + layoutIdx == nElems - 1:
                return icon.TRAILING_EMPTY_ARG_WIDTH
            return icon.LIST_EMPTY_ARG_WIDTH

    def calcLayoutsAllCombos(self):
        """Deprecated version of calcLayouts for list manager that provides every
        possible layout for the list.  Deprecated because (obviously) every combination
        of a list of any significant size or complexity is a combinatorial explosion.
        Kept around for exploring layouts that the normal method will not generate."""
        siteSeries = self.icon.sites.getSeries(self.siteSeriesName)
        if len(siteSeries) == 1 and siteSeries[0].att is None:
            # Empty Argument list leaves no space: (), [], {}
            layout = ListMgrLayout(self.siteSeriesName, (), self)
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
                for childLayoutIdx, childLayout in enumerate(childLayouts):
                    rowXOffsets.append(rowWidth)
                    if childLayout is None:
                        childWidth = self.emptyArgWidth(childLayoutIdx)
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
                    layout = ListMgrLayout(self.siteSeriesName, rowWidths, self)
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

    def emptyArgWidth(self, subLayoutIdx):
        if self.allowsTrailingComma and subLayoutIdx == \
                len(self.icon.sites.getSeries(self.siteSeriesName)) - 1:
            return icon.TRAILING_EMPTY_ARG_WIDTH
        return icon.LIST_EMPTY_ARG_WIDTH

class ListMgrLayout(Layout):
    """Represents the part of an icon layout associated with a single variable-length
    list of icons managed by a ListLayoutMgr object."""
    def __init__(self, siteSeriesName, rowWidths, listMgr):
        Layout.__init__(self, listMgr.icon, 0, 0, 0)
        self.siteSeriesName = siteSeriesName
        self.rowWidths = rowWidths
        self.listMgr = listMgr

    def mergeInto(self, destLayout, xOff, yOff):
        """Merge this layout in to another layout (presumably that of the parent icon)."""
        self.iconRectLeft, self.iconRectTop, self.iconRectRight, self.iconRectBottom = \
            self.calcIconRectCoverage()
        if len(self.rowWidths) > 1:
            # Our convention for adding icon parts to an expression layout asks the
            # caller to identify the part with the first site of the list.  However, if
            # spines will draw, the site will be recorded incorrectly as the anchor point
            # for the spine.  Save the anchor point in the table under the series name.
            leftSiteName = self.siteSeriesName + '_0'
            if leftSiteName in destLayout.siteOffsets:
                destLayout.siteOffsets[self.siteSeriesName] = \
                    destLayout.siteOffsets[leftSiteName]
            if destLayout.wraps is not None and leftSiteName in destLayout.wraps[0]:
                (fromX, fromY), (toX, toY), bY = destLayout.wraps[0][leftSiteName]
                del destLayout.wraps[0][leftSiteName]
                destLayout.wraps[0][self.siteSeriesName] = (fromX, fromY), (toX, toY), bY
        destLayout.mergeLayout(self, xOff, yOff, expandIconRect=True)
        destLayout.addDoLayoutCallback(self.listMgr.doLayout)
        #... once all icons are using callback, pass this as callback data
        setattr(destLayout, self.siteSeriesName + "ListMgrData", (self.width,
            self.height, self.siteOffsets, self.rowWidths))

    def calcIconRectCoverage(self):
        spineTop, spineHeight = self.calcSpineTopAndHeight()
        return 0, -spineTop, self.width, spineHeight-spineTop

    def calcSpineTopAndHeight(self):
        # Note that this duplicates and needs to match the calculation in doLayoutInline
        # for spineTop and spineHeight (while this object is the original source for the
        # list layout data, it no longer exists at doLayout time)
        siteSeries = self.listMgr.icon.sites.getSeries(self.siteSeriesName)
        firstSiteY = self.siteOffsets[siteSeries[0].name][1]
        lastSiteY = self.siteOffsets[siteSeries[-1].name][1]
        if firstSiteY == lastSiteY:
            spineHeight = icon.minTxtIconHgt
            spineTop = icon.minTxtIconHgt // 2
        else:
            spineHeight = lastSiteY - firstSiteY + icon.inSiteImage.height + \
                2 * SPINE_SITE_Y_CLEARANCE
            spineTop = -firstSiteY + icon.inSiteImage.height//2 + SPINE_SITE_Y_CLEARANCE
        return spineTop, spineHeight

    def incorporateRectIntoLayout(self, parentLayout, originXOff, originYOff):
        """Expand the layout rectangle of parentLayout to incorporate the list manager
        layout content (self) given the placement of the ListMgrLayout within
        parentLayout (originXOff, originYOff)."""
        parentHeightAbove = max(parentLayout.parentSiteOffset,
            self.parentSiteOffset - originYOff)
        parentHeightBelow = max(parentLayout.height - parentLayout.parentSiteOffset,
            self.height - self.parentSiteOffset - originYOff)
        parentLayout.height = parentHeightAbove + parentHeightBelow
        parentLayout.parentSiteOffset = parentHeightAbove
        parentLayout.width = max(parentLayout.width, originXOff + self.width)

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

class ExprLayout:
    """Collect a series of icon parts, layout objects and lists of of layout objects to
    be arranged in a linear (but potentially wrapped) organization.  These are
    (optionally) separated by potential break points, where the expr can be wrapped.
    When initializing with an icon part, siteName should normally be set to the siteId
    of the site on the right of the part.  However for parts that do not have such a
    site, any identifying value or object can be used.  For legitimate sites of ic, the
    wrap() method will automatically populate sublayout entries in the layout object it
    constructs.  For siteNames other than None, wrap will however, produce an entry in
    the siteOffsets field of the layout, which the doLayout call can then process to
    position the part (for None, we assume that the icon's doLayout call has some
    alternative way to position the part).

    Note that ExprLayouts have no built-in margin specification.  Margin is imposed only
    upon wrap (call to .wrap() method).

    While an ExprLayout can be initialized and appended with completed layouts, icon
    calcLayout functions that generate ExprLayouts should not call calcLayouts directly
    on arguments.  They should instead use the lazy form (or appendArgLayout).  This
    pushes the job of calculating margin limits to the wrapping code, which gets called
    on the top-level of the expression (statement-level or top of an enclosed context,
    usually an inline wrap).  While the marginLimit parameter to the calcLayouts function
    will be correct, the wrapping code has more context to optimize sub-layout margins on
    specified argument icons and embedded series.  Making the calls directly will only
    make sense if the icon somehow has sites that are not part of the expression, but
    such icons are almost certainly better off generating Layouts from their calcLayouts
    function rather than an ExprLayout.

    For block-owning icons, the icon body (part) should be added to the expression with
    a height value that excludes the 'sequence-bump' that extends into the vertical
    margin between the icon and the code block.  This is required because we want to nest
    the wrapped code after the bump such that the margin appears below the full wrapped
    statement rather than between the first and second wrapped row.  The wrap() call will
    automatically add this back both to the layout and to the icon rectangle for any
    block-owning icon (whether it has a sequence bump or not, but I believe all do)."""

    # Format of self.partLayouts is a list of _ExprPartLayout and/or lists of Layout
    # objects separated by integer break-level values to indicate possible wrap points.
    # These break values may also be None to indicate no break.

    def __init__(self, topIcon, layouts=None, siteName=None, width=None, height=None,
            yOffset=None, siteYOffset=None, indentDepthAdj=0):
        self.partLayouts = None
        self.topIcon = topIcon
        self.indentDepthAdj = indentDepthAdj
        if siteName is not None or width is not None or height is not None or \
                yOffset is not None or siteYOffset is not None:
            if width is None or height is None or yOffset is None:
                print("ExprLayout specified as part without width, height, or yOffset")
                return
            self.appendPart(None, topIcon, siteName, width, height, yOffset, siteYOffset)
        elif layouts is not None:
            self.appendLayout(None, layouts)
        else:
            self.partLayouts = None

    def appendPart(self, brkLvl, ic, siteName, width, height, yOffset,
            siteYOffset):
        self._appendPartsOrLayouts(brkLvl, _ExprPartLayout(ic, siteName, width,
            height, yOffset, siteYOffset))

    def appendEmptySite(self, ic, siteName, forListArg=False):
        partLayout = EmptyArgLayout(ic, siteName, forListArg=forListArg)
        self._appendPartsOrLayouts(None, partLayout)

    def appendLayout(self, brkLvl, layouts):
        """Append a layout choice list or ExprLayout to this expression layout, either
        concatenating (brkLvl=None) or including a wrap point (brkLvl = 0)."""
        if isinstance(layouts, ExprLayout):
            self.appendExprLayout(brkLvl, layouts)
        else:
            self._appendPartsOrLayouts(brkLvl, layouts)

    def appendArgLayout(self, brkLvl, ic, siteName, marginLimit=None, demoteArgBrkLvl=1,
            argRequired=True):
        """Append the sub-layout for a given site to the expression.  Handles empty arg
        case and demotion of break-levels in the layout. If marginLimit is not specified,
        calcLayouts for the argument is deferred to expression wrap time via the
        LazyLayout mechanism.  By default, demotes break-level of the argument expression
        by 1, even when the argument is joined with icon-part owning the site (to keep
        break-levels aligned with the icon-hierarchy)."""
        argIc = ic.childAt(siteName)
        if argIc is None:
            if not argRequired:
                return
            argLayouts = EmptyArgLayout(ic, siteName)
        else:
            if marginLimit is None:
                argLayouts = LazyLayout(argIc)
            else:
                argLayouts = argIc.calcLayouts(marginLimit)
            if demoteArgBrkLvl != 0:
                pushBrkLvl(argLayouts, nLevels=demoteArgBrkLvl)
        self.appendLayout(brkLvl, argLayouts)

    def _appendPartsOrLayouts(self, brkLvl, layouts):
        """Append an _ExprPartLayout, individual Layout, or list of Layouts; to the
        expression series, joined by the given brkLvl."""
        if isinstance(layouts, (list, tuple)) and len(layouts) == 1:
            # A single layout choice is a fixed layout, which we indicate as a Layout
            # object w/o enclosing list (CalcLayouts currently produces only list form).
            layouts = layouts[0]
        if self.partLayouts is None:
            self.partLayouts = [layouts]
        else:
            self.partLayouts.append(brkLvl)
            self.partLayouts.append(layouts)

    def appendExprLayout(self, brkLvl, exprLayout):
        """Join (append) the given exprLayout with this one, optionally allowing a wrap
        point between the two segments.  To disallow wrap, set brkLvl to None.  To allow
        wrap, first adjust break levels in the two ExprLayouts being appended, and then
        set brkLvl to the separating level (which will usually be 0)."""
        if exprLayout.partLayouts is None:
            return
        elif self.partLayouts is None:
            self.partLayouts = exprLayout.copy()
        else:
            self.partLayouts.append(brkLvl)
            self.partLayouts.extend(exprLayout.partLayouts)
        if hasattr(exprLayout, 'doLayoutCallbacks'):
            if hasattr(self, 'doLayoutCallbacks'):
                self.doLayoutCallbacks.update(exprLayout.doLayoutCallbacks)
            else:
                self.doLayoutCallbacks = exprLayout.doLayoutCallbacks

    def prependPart(self, ic, siteName, width, height, yOffset, siteYOffset, brkLvl):
        self._prependPartsOrLayouts(_ExprPartLayout(ic, siteName,
            width, height, yOffset, siteYOffset), brkLvl)

    def prependLayout(self, layouts, brkLvl):
        if isinstance(layouts, ExprLayout):
            self.prependExprLayout(layouts, brkLvl)
        else:
            self._prependPartsOrLayouts(layouts, brkLvl)

    def prependArgLayout(self, ic, siteName, brkLvl, marginLimit=None, demoteArgBrkLvl=1):
        """Prepend the sub-layout for a given site to the expression.  Handles empty arg
        case and demotion of break-levels in the layout. If marginLimit is not specified,
        calcLayouts for the argument is deferred to expression wrap time via the
        LazyLayout mechanism.  By default, demotes break-level of the argument expression
        by 1, even when the argument is joined with icon-part owning the site (to keep
        break-levels aligned with the icon-hierarchy)."""
        argIc = ic.childAt(siteName)
        if argIc is None:
            argLayouts = EmptyArgLayout(ic, siteName)
        else:
            if marginLimit is None:
                argLayouts = LazyLayout(argIc)
            else:
                argLayouts = argIc.calcLayouts(marginLimit)
            if demoteArgBrkLvl != 0:
                pushBrkLvl(argLayouts, nLevels=demoteArgBrkLvl)
        if brkLvl is not None:
            pushBrkLvl(argLayouts)
        self.prependLayout(argLayouts, brkLvl)

    def _prependPartsOrLayouts(self, layouts, brkLvl):
        if isinstance(layouts, (list, tuple)) and len(layouts) == 1:
            # See _appendPartsOrLayouts
            layouts = layouts[0]
        if self.partLayouts is None:
            self.partLayouts = [layouts]
        else:
            self.partLayouts.insert(0, brkLvl)
            self.partLayouts.insert(0, layouts)

    def prependExprLayout(self, exprLayout, brkLvl):
        """Join (prepend) the given exprLayout with this one, optionally allowing a wrap
        point between the two segments.  To disallow wrap, set brkLvl to None.  To allow
        wrap, first adjust break levels in the two ExprLayouts being appended, and then
        set brkLvl to the separating level (which will usually be 0)."""
        if exprLayout.partLayouts is None:
            return
        elif self.partLayouts is None:
            self.partLayouts = exprLayout.copy()
        else:
            self.partLayouts.insert(0, brkLvl)
            self.partLayouts[:0] = exprLayout.partLayouts
        if hasattr(exprLayout, 'doLayoutCallbacks'):
            if hasattr(self, 'doLayoutCallbacks'):
                self.doLayoutCallbacks.update(exprLayout.doLayoutCallbacks)
            else:
                self.doLayoutCallbacks = exprLayout.doLayoutCallbacks

    def addDoLayoutCallback(self, cb):
        """Attach a callback to the layout to be executed by the icon's doLayout method
        (via the updateSites call).  The function must take 3 arguments: layout,
        loToIconX, loToIconY.  loToIconX and loToIconY are the offsets from layout
        coordinates as used in the Layout.siteOffsets dictionary and the icon-rectangle-
        relative coordinates of icon site offsets."""
        if hasattr(self, 'doLayoutCallbacks'):
            cbList = self.doLayoutCallbacks[self.topIcon]
        else:
            cbList = []
            self.doLayoutCallbacks = {self.topIcon:cbList}
        cbList.append(cb)

    def wrap(self, margin):
        """Produce a single Layout structure resulting from comparing and choosing the
        best layout among all possible arrangements of the expression for the given
        margin.  Currently, expression wrapping is always maximal to the given margin
        (I'm fairly sure there will be cases where this produces ugly results, but I
        prefer to start out with this, since it will hopefully be much more efficient).
        """
        # Call calcLayouts on all icons and ListLayoutMgr objects that were deferred (by
        # being wrapped in LazyLayout objects), updating self.partLayouts with results.
        self._expandLazyLayouts(margin)
        # Expand all of the layout choices to make "flattened" expression lists, each
        # with a fixed set of choices and None (no-break) separators removed
        layoutChoiceLists = []
        layoutChoiceIdxs = []
        flattenedLayouts = []
        choiceIdx = 0
        for layoutList in self.partLayouts:
            if isinstance(layoutList, (list, tuple)):
                layoutChoiceLists.append(layoutList)
                layoutChoiceIdxs.append(choiceIdx)
                choiceIdx += 1
            else:
                layoutChoiceIdxs.append(None)
        if len(layoutChoiceLists) == 0:
            flattenedLayouts.append(self.partLayouts)
        else:
            for chosenLayouts in allCombinations(layoutChoiceLists):
                flattenedLayout = []
                for i, partLayout in enumerate(self.partLayouts):
                    if partLayout is None:
                        continue  # remove Nones
                    choiceIdx = layoutChoiceIdxs[i]
                    if choiceIdx is None:
                        flattenedLayout.append(partLayout)
                    else:
                        flattenedLayout.append(chosenLayouts[choiceIdx])
                flattenedLayouts.append(flattenedLayout)
        # Wrap the flattened layouts and return the best result
        wrappedLayouts = []
        for flattenedLayout in flattenedLayouts:
            wrappedLayouts.append(self._wrapFlattened(flattenedLayout, margin))
        bestLayout = self._chooseBestLayout(wrappedLayouts)
        # If the layout is for a block owning icon, add the vertical margin for the block
        # or pseudo-block
        if hasattr(self.topIcon, 'blockEnd'):
            bestLayout.height += icon.BLOCK_SEQ_MARGIN
            bestLayout.iconRectBottom += icon.BLOCK_SEQ_MARGIN
        elif self._isPseudoBlock():
            bestLayout.height += 2
            bestLayout.parentSiteOffset += icon.PSEUDO_BLOCK_SEQ_MARGIN
            bestLayout.iconRectBottom += icon.PSEUDO_BLOCK_SEQ_MARGIN
            bestLayout.iconRectTop -= icon.PSEUDO_BLOCK_SEQ_MARGIN
        return bestLayout

    def _wrapFlattened(self, partLayouts, margin):
        """Wrap an exprLayout (partLayouts) that has been 'flattened' to represent a
        single set of alternative subLayouts)."""
        # First compute a baseline wrap where we wrap as close to the margin as possible
        # by ignoring break level
        baselineLayout, isWrapped = self._wrapToLevel(partLayouts, margin, None)
        if not isWrapped:
            # No wrapping needed
            return baselineLayout
        # Now try to improve the wrap by limiting wrap points to the highest possible
        # without increasing resulting height.  This is still not optimal, however, as
        # once we have descended to a lower break level, we treat all break levels below
        # that threshold as equal and miss opportunities for improvement.
        # Note that since we use brkLvl somewhat like badness and leave gaps (in
        # particular, ATTR_BRK_LVL == 50), we sort the actual break levels found in
        # partLayouts rather than simply iterating from 0 to the max level.
        brkLvls = sorted({lvl for lvl in partLayouts if isinstance(lvl, int)})
        if len(brkLvls) == 0 or brkLvls[-1] == 0:
            # All possible wraps are at optimal (top) break level
            return baselineLayout
        for lvl in brkLvls:
            layout, _ = self._wrapToLevel(partLayouts, margin, lvl)
            if layout is None or layout.width > margin:
                continue
            if layout.height <= baselineLayout.height:
                print('wrap improved over baseline: lvl', lvl)
                return layout
        print('wrap not improved over baseline')  #... remove this
        return baselineLayout

    def _expandLazyLayouts(self, marginLimit, accumulatedWidth=0):
        """Find unevaluated layouts in partLayouts (LazyLayout objects indicating an icon
        or series layout waiting for margin restrictions), calculate the new margin
        restrictions the best we can, and call the appropriate calcLayouts for each lazy
        item.  Note that this"""
        # Divide partLayouts into groups of non-separable parts/layouts
        group = []
        groups = [group]
        for idx, partLayout in enumerate(self.partLayouts):
            if partLayout is None:
                continue
            elif isinstance(partLayout, int):
                group = []
                groups.append(group)
            else:
                group.append(idx)
        # For each group, find the fixed size restrictions (mostly from icon parts
        # specified as _ExprPartLayouts, since we won't know the size of LazyLayouts or
        # lists of Layouts, but individual pre-calculated Layouts are counted, too).
        # Then call calcLayouts on the LazyLayouts in the group, with the new margin
        # restriction
        idxShift = 0
        for group in groups:
            lazyLayouts = []
            allocatedWidth = 0
            for idx in group:
                adjIdx = idx + idxShift
                partLayout = self.partLayouts[adjIdx]
                if isinstance(partLayout, LazyLayout):
                    lazyLayouts.append(idx)
                elif isinstance(partLayout, (_ExprPartLayout, Layout)):
                    allocatedWidth += partLayout.width
            for idx in lazyLayouts:
                adjIdx = idx + idxShift
                lazyLayout = self.partLayouts[adjIdx]
                remainingMargin = marginLimit - min(self._continuationIndent(),
                    allocatedWidth + accumulatedWidth)
                layout = lazyLayout.calcLayouts(remainingMargin)
                if isinstance(layout, ExprLayout):
                    accumulatedWidth += layout._expandLazyLayouts(remainingMargin,
                        accumulatedWidth)
                    # Note that break level demotion can only be done after expansion of
                    # lower-level layouts
                    if lazyLayout.addedBrkLvl > 0 and isinstance(layout, ExprLayout):
                        pushBrkLvl(layout, lazyLayout.addedBrkLvl)
                    # We're also doing an end run around appendExprLayout, which
                    # propagates doLayoutCallbacks to the level of the top expression
                    if hasattr(layout, 'doLayoutCallbacks'):
                        if hasattr(self, 'doLayoutCallbacks'):
                            self.doLayoutCallbacks.update(layout.doLayoutCallbacks)
                        else:
                            self.doLayoutCallbacks = layout.doLayoutCallbacks
                    # Insert the result in place of the lazy layout we expanded
                    self.partLayouts[adjIdx:adjIdx+1] = layout.partLayouts
                    idxShift += len(layout.partLayouts) - 1
                else:
                    self.partLayouts[adjIdx] = layout
                    if not isinstance(layout, (list, tuple)):
                        accumulatedWidth += layout.width
        return accumulatedWidth

    def _wrapToLevel(self, partLayouts, margin, brkThreshold):
        """Wrap the specified flattened layout to the given margin breaking only at
        break levels at or below brkThreshold.  brkThreshold can be set to None, in
        which case, all break points are acceptable and exceeding margin is allowed.
        Returns a Layout object (probably tree) for topIcon, and a boolean indicating
        if the expression was, indeed, wrapped."""
        # Flattened layout (partLayouts) is a list of Layout and JoinedPartLayout objects
        # separated by integer break-levels with all concatenated runs of Layout or
        # ExprPartLayout objects joined.  Find the acceptable break points and divide
        # partLayouts in to a list of rows of icon and part layouts.
        continueIndent = self._continuationIndent()
        doLayoutCbs = self.doLayoutCallbacks if hasattr(self, 'doLayoutCallbacks') else {}
        rows = []
        rowOffsets = []
        supSubYAdj = {}
        lastSupSubAdj = 0
        wraps = {}
        rowStart = 0
        rowTop = 0
        indent = -self.indentDepthAdj
        totalWidth = 0
        wrapIc = wrapSite = wrapFromPos = None
        while rowStart < len(partLayouts):
            brkIdx, rowWidth = self._findLastAcceptableBreakPoint(partLayouts, rowStart,
                brkThreshold, margin - indent)
            if brkIdx is None:  # No acceptable break point found
                return None, False
            row = [lo for lo in partLayouts[rowStart:brkIdx] if not isinstance(lo,
                (int, type(None)))]
            rows.append(row)
            # Compute a per-layout site y position adjustment (supSubYAdj).  This is the
            # fine adjustment to the wrap baseline that will be recorded in rowOffsets
            # based on how the sites on the icons fit together (rowOffsets reflects only
            # the original baseline, to which the per-layout deviation in supSubYAdj
            # should be added to get the actual layout Y origin.
            for layout in row:
                # Note that we're entering the offset for the current icon in supSubYAdj
                # but computing the offset for the NEXT entry in lastSupSubAdj
                if isinstance(layout, ListMgrLayout):
                    # continue  # ListMgrLayouts have no site to affect sup/sub
                    # ListMgrLayouts (always?) follow an input site
                    supSubYAdj[layout] = lastSupSubAdj
                elif isinstance(layout, Layout):
                    supSubYAdj[layout.icon] = lastSupSubAdj
                    lastSupSubAdj += _layoutSupSubAdj(layout)
                else:  # _ExprPartLayout: lastSupSubAdj will restore that of first part
                    if layout.ic in supSubYAdj:
                        newSupSubAdj = supSubYAdj[layout.ic] + layout.siteYOffset
                    else:
                        supSubYAdj[layout.ic] = lastSupSubAdj
                        newSupSubAdj = lastSupSubAdj + layout.siteYOffset
                    lastSupSubAdj = newSupSubAdj
            # Compute the height and (baseline) y offset for the row
            rowYOffset = 0
            rowHeightBelow = 0
            for layout in row:
                if isinstance(layout, ListMgrLayout):
                    yOffset = layout.parentSiteOffset - supSubYAdj[layout]
                elif isinstance(layout, Layout):
                    yOffset = layout.parentSiteOffset - supSubYAdj[layout.icon]
                else:  # _ExprPartLayout
                    yOffset = layout.yOffset - supSubYAdj[layout.ic]
                rowYOffset = max(rowYOffset, yOffset)
                rowHeightBelow = max(rowHeightBelow, layout.height - yOffset)
            if len(rows) > 1:
                wrapData = wrapFromPos, (indent, rowYOffset + rowTop), rowTop
                if wrapIc not in wraps:
                    wraps[wrapIc] = {}
                wraps[wrapIc][wrapSite] = wrapData
            rowOffsets.append((indent, rowYOffset + rowTop))
            wrapFromPos = indent + rowWidth, rowYOffset + rowTop
            rowTop += rowYOffset + rowHeightBelow - 1  # -1 for icon boundary overlap
            rowStart = brkIdx + 1
            if rowStart >= len(partLayouts):
                totalWidth = max(totalWidth, indent + rowWidth)
                break
            totalWidth = max(totalWidth, indent + rowWidth +
                icon.noSiteWrapFromImage.width - 1)
            brkPartLayout = partLayouts[brkIdx-1]
            if isinstance(brkPartLayout, ListMgrLayout):
                wrapIc = brkPartLayout.icon
                wrapSite = None
            else:
                wrapIc, wrapSite = _findRightmostLayoutSite(brkPartLayout)
                if not wrapIc.childAt(wrapSite):
                    # Wrap is not between connected icons (no-site wrap).  Unfortunately,
                    # we can't blindly turn this into a no-site wrap, because we could be
                    # wrapping in to series whose first element happens to be empty
                    wrapToSeries, wrapToIdx = iconsites.splitSeriesSiteId(wrapSite)
                    if wrapToSeries is None:
                        wrapSite = None
            if wrapSite is None:
                # To indicate no-site-wrap, we put integer instead of site in wrap dict
                wrapSite = len(wraps[wrapIc]) if wrapIc in wraps else 0
            indent = continueIndent + BRK_LVL_INDENT * partLayouts[brkIdx]
        # Create Layout objects for each of the icons in the expression that are not
        # already in Layout form.  The layouts cannot yet be fully constructed, but we
        # can fill in siteOffsets and incorporate the area of the icon parts as they
        # appear in the expression.  Subsequent steps will link the layout tree via the
        # subLayouts field and finish determining the size.
        unifiedPartLayouts = {}
        existingExprLayouts = {}
        listMgrLayouts = []
        layoutOrigins = {}
        for rowNum, row in enumerate(rows):
            leftX, baselineY = rowOffsets[rowNum]
            overlap = 1  # Icon overlap in pixels
            for layoutOrPart in row:
                if isinstance(layoutOrPart, _ExprPartLayout):
                    ic = layoutOrPart.ic
                    if isinstance(layoutOrPart, EmptyArgLayout):
                        # An empty arg is just a space holder and not a real icon part
                        layout = unifiedPartLayouts.get(ic, None)
                        if layout is None:
                            print('_wrapToLevel: EmptyArg should not be on left of icon')
                        else:
                            originX, originY = layoutOrigins[ic]
                            layoutOrPart.incorporateRectIntoLayout(layout,
                                leftX - originX, baselineY - originY)
                        leftX += layoutOrPart.width - overlap  #... why overlap?
                        continue
                    if ic in unifiedPartLayouts:
                        # Incorporate part rectangle into layout rectangle and prototype
                        # icon rectangle.  Note that because of wrapping, we can extend
                        # the rectangle left of the layout origin.
                        layout = unifiedPartLayouts[ic]
                        originX, originY = layoutOrigins[ic]
                        layoutOrPart.incorporateRectIntoLayout(layout, leftX - originX,
                            baselineY - originY)
                    else:
                        # Create layout object sized to initial part
                        layout = unifiedPartLayouts[ic] = Layout(ic, layoutOrPart.width,
                            layoutOrPart.height, layoutOrPart.yOffset, setIconRect=True)
                        if ic in doLayoutCbs:
                            layout.doLayoutCallbacks = doLayoutCbs[ic]
                        originX = leftX
                        originY = baselineY + supSubYAdj[ic]
                        layoutOrigins[ic] = originX, originY
                    # Fill in site offset for site associated with part
                    wrapSite = layoutOrPart.siteName
                    if ic in wraps and wrapSite in wraps[ic]:
                        # At wrap sites
                        (fromX, fromY), (toX, toY), rowTop = wraps[ic][wrapSite]
                        if isinstance(wrapSite, str) and ic.childAt(wrapSite):
                            # We're wrapping at a connected site, adjust the y offsets of
                            # the wrap points to conform with the site offset (while we
                            # do wrap at non-part layouts, we don't extend sites across
                            # them or use site-specific arrows that need aligning).
                            fromY += supSubYAdj[ic] + layoutOrPart.siteYOffset
                            toY += supSubYAdj[ic] + layoutOrPart.siteYOffset
                            wraps[ic][wrapSite] = (fromX, fromY), (toX, toY), rowTop
                        x = toX - originX
                        y = toY - originY
                    else:
                        x = leftX + layoutOrPart.width - originX - overlap
                        y = baselineY + supSubYAdj[ic] + layoutOrPart.siteYOffset - originY
                    layout.siteOffsets[layoutOrPart.siteName] = x, y
                else:  # Layout objects
                    ic = layoutOrPart.icon
                    if isinstance(layoutOrPart, ListMgrLayout):
                        listMgrLayouts.append((layoutOrPart, leftX,
                            baselineY + supSubYAdj[layoutOrPart]))
                        # Note that origin for listMgr is recorded under layout instead
                        # of Ic, since it's separate from layout for ic (and never copied)
                        #if ic not in layoutOrigins:
                        #    layoutOrigins[ic] = leftX, baselineY + supSubYAdj[ic]
                    else:
                        existingExprLayouts[ic] = layoutOrPart
                        layoutOrigins[ic] = leftX, baselineY + supSubYAdj[ic]
                leftX += layoutOrPart.width - overlap
        # Attach wrap site information to sublayouts, translating coordinates from those
        # of the top-level layout to those of the sublayout for the icon that will own
        # the wrap site.  While we can safely attach wrap site information to subLayouts
        # that we've generated (those that the caller specified in the form of
        # ExprLayouts), those that were originally specified in Layout form may be
        # shared with other layout choices, hence the shallow copy of the Layout object.
        if len(wraps) > 0:
            # Wrap data is currently in the coordinates of the top-level layout
            for ic, wrapData in wraps.items():
                if ic in existingExprLayouts:
                    layoutCopy = copy.copy(existingExprLayouts[ic])
                    existingExprLayouts[ic] = layoutCopy
                    originX, originY = layoutOrigins[ic]
                elif ic in unifiedPartLayouts:
                    layoutCopy = unifiedPartLayouts[ic]
                    originX, originY = layoutOrigins[ic]
                else:
                    # Wrap is on an icon that is buried within an icon that is not using
                    # expression-wrapped layout.  I'm not sure this will ever happen once
                    # the transition to expression wrapping is finished, but for now, we
                    # need to put in a whole bunch of work to find the appropriate layout
                    # object and its origin, and then copy the layout so we can safely
                    # add wrap data to it.
                    layout, originX, originY = _findSublayoutAndOriginFromDict(ic,
                        existingExprLayouts, layoutOrigins)
                    layoutCopy = copy.copy(layout)
                newWraps = layoutCopy.offsetWrapList(wrapData, -originX, -originY), \
                    self.topIcon
                layoutCopy.wraps = newWraps
                layoutCopy._expandIconRectDataForWraps()
        # Find the layout we created for the top icon of the expression or statement
        # (this will be the one we return as the wrap result) and transfer any attributes
        # not otherwise generated from the expression parts.
        topLayout = unifiedPartLayouts[self.topIcon]
        if self.indentDepthAdj != 0:
            topLayout.indentDepthAdj = self.indentDepthAdj
        if len(rows) > 1:
            topLayout.wrappedExprData = icon.subtractPoints(wrapFromPos,
                layoutOrigins[self.topIcon])
        # Build a layout tree for the expression, by filling in the the subLayouts fields
        # for the new layouts constructed above
        self._linkSubLayouts(self.topIcon, unifiedPartLayouts, existingExprLayouts,
            listMgrLayouts)
        # Merge in any ListMgrLayouts from the expression to their owner icons.  We allow
        # these in expression layouts and handle merging for them to simplify inline-list
        # layout.  While most inline-list layout is turned off by default, a lot of work
        # went in to developing it, and simplifying their integration into expression-
        # wrapped layout will make it easier to keep the capability alive.
        for listLayout, xOff, yOff in listMgrLayouts:
            if listLayout.icon in unifiedPartLayouts:
                ownerLayout = unifiedPartLayouts[listLayout.icon]
                ownerOriginX, ownerOriginY = layoutOrigins[ownerLayout.icon]
                listLayout.mergeInto(ownerLayout, xOff - ownerOriginX,
                    yOff - ownerOriginY)
                if ownerLayout is not topLayout:
                    # ListMgrLayouts can be found deep within the expression hierarchy.
                    # Since we're merging them after assembling the layout structures, we
                    # have not yet expanded their parent layouts to incorporate them.
                    # This is safe because their parent layouts designated them as parts
                    # of an ExprLayout, expecting to be modified by the expression
                    # wrapping process.
                    for parent in ownerLayout.icon.parentage():
                        parentOriginX, parentOriginY = layoutOrigins[parent]
                        parentLayout = unifiedPartLayouts[parent]
                        listLayout.incorporateRectIntoLayout(parentLayout,
                            xOff - parentOriginX, yOff - parentOriginY)
                        if parent is self.topIcon:
                            break
            else:
                print('wrapTextToLevel encountered ListMgrLayout for icon not in expr')
        # Width of the returned layout is filled in via part processing (the same as for
        # sub-layouts), however we need to override this explicitly for the top-level
        # layout to include wrap arrows, which are not yet included at this point.
        if len(wraps) > 0:
            topLayout.width = totalWidth
        # Add y positions for seqIn/seqOut from first item in partLayouts (If we can
        # figure out from spine calculations (ListMgr) or icon part height
        if self.topIcon.parent() is None:
            firstPartOrLayout = partLayouts[0]
            if isinstance(firstPartOrLayout, ListMgrLayout):
                # First item is a list-manager layout which will (awkwardly) get sequence
                # sites on its spines for multi-row layouts.  For single-row layouts,
                # this provides site offsets at icon.minTxtIconHgt but hopefully the icon
                # overrides these with referred sequence sites to the icon in the first
                # argument position.
                spineTop, spineHeight = firstPartOrLayout.calcSpineTopAndHeight()
                topLayout.seqInOutYOffsets = spineTop, spineHeight - spineTop
            elif isinstance(firstPartOrLayout, _ExprPartLayout):
                topLayout.seqInOutYOffsets = firstPartOrLayout.yOffset, \
                    firstPartOrLayout.height - firstPartOrLayout.yOffset - 1
        return topLayout, len(wraps) > 0

    def _linkSubLayouts(self, ic, newLayouts, existingLayouts, listMgrLayouts):
        """Fill in subLayouts fields and expand layout size to include subLayouts for
        layouts created in _wrapToLevel in the icon tree beneath ic.  _wrapToLevel
        creates the Layout objects and fills in their siteOffset fields and size based
        on the icon parts it encounters in the expression it is wrapping.  This recursive
        call finishes the construction in bottom-up order so that lower-level subLayouts
        get fully-constructed and sized before their data is needed for sizing the levels
        above them."""
        layout = newLayouts[ic]
        for siteName, siteOffsets in layout.siteOffsets.items():
            child = None if siteName is None else ic.childAt(siteName)
            if child is None:
                subLayout = None
            elif child in existingLayouts:
                subLayout = existingLayouts[child]
            elif child in newLayouts:
                self._linkSubLayouts(child, newLayouts, existingLayouts, listMgrLayouts)
                subLayout = newLayouts[child]
            else:
                # Print a warning if layout isn't for one of the expression parts listed
                # in the expression.  ...Unless it is a sublayout handled by a list-mgr,
                # which we allow the icons of the expression to include, in which case,
                # it's already been merged.
                siteSeriesName, _ = iconsites.splitSeriesSiteId(siteName)
                for listLayout, _, _ in listMgrLayouts:
                    if siteSeriesName == listLayout.siteSeriesName:
                        break
                else:
                    print('_wrapToLevel found part site with icon not in expression')
                continue
            # addSubLayout does all the work of resizing the layout to include the linked
            # sublayout.  Note that we've already filled in siteOffsets field with site
            # positions, and we're just feeding them back so we don't have to change the
            # interface of addSubLayout.
            layout.addSubLayout(subLayout, siteName, siteOffsets[0], siteOffsets[1])
            if subLayout is not None:
                layout.badness += subLayout.badness

    @staticmethod
    def _findLastAcceptableBreakPoint(partLayouts, startIdx, brkThreshold, margin):
        """Find the index of the last (integer) break position in partLayouts <=
        brkThreshold.  Returns index of break in partLayouts and width of the resulting
        row.  If brkThreshold is None, margin exceeding lines are accepted"""
        lastBrkIdx = None
        lastBrkWidth = None
        width = 0
        for idx in range(startIdx, len(partLayouts)):
            layoutOrBrkLvl = partLayouts[idx]
            if layoutOrBrkLvl is None:
                continue
            elif isinstance(layoutOrBrkLvl, int):
                if brkThreshold is None or layoutOrBrkLvl <= brkThreshold:
                    lastBrkIdx = idx
                    lastBrkWidth = width
            else:
                width += layoutOrBrkLvl.width - 1  # -1 for icon boundary overlap
                if width > margin:
                    if lastBrkIdx is None and brkThreshold is None:
                        # We've exceeded margin and haven't found a break point, yet
                        for i in range(idx + 1, len(partLayouts)):
                            if isinstance(partLayouts[i], int):
                                return i, width
                            width += layoutOrBrkLvl.width - 1
                        return len(partLayouts), width
                    return lastBrkIdx, lastBrkWidth
        return len(partLayouts), width

    @staticmethod
    def _chooseBestLayout(layouts):
        minHeight = min((layout.height for layout in layouts))
        for layout in layouts:
            layout.badness += (layout.height - minHeight) // 2
        bestScore = bestLayout = None
        for layout in layouts:
            if bestScore is None or layout.badness < bestScore:
                bestLayout = layout
                bestScore = layout.badness
        return bestLayout

    def _dumpExpr(self):
        for layoutList in self.partLayouts:
            if isinstance(layoutList, (list, tuple)):
                print(' ' + layoutList[0].icon.dumpName(), end='')
            elif isinstance(layoutList, (int, type(None))):
                print('', layoutList, end=' ')
            elif isinstance(layoutList, _ExprPartLayout):
                print(layoutList.ic.dumpName(), layoutList.width, end='')
        print()

    def _continuationIndent(self):
        # pseudo-block icons (else, elif, except, finally) are wrapped to outer block
        indentStyle = self.topIcon.window.settings.indentStyle
        if indentStyle == 'blkDbl':
            if hasattr(self.topIcon, 'blockEnd'):
                return CONTINUATION_INDENT + 2 * comn.BLOCK_INDENT
            else:
                return CONTINUATION_INDENT + comn.BLOCK_INDENT
        elif indentStyle == 'single':
            if self._isPseudoBlock():
                return CONTINUATION_INDENT
            else:
                return CONTINUATION_INDENT + comn.BLOCK_INDENT
        else:
            if self._isPseudoBlock():
                return CONTINUATION_INDENT - comn.BLOCK_INDENT
            else:
                return CONTINUATION_INDENT

    def _isPseudoBlock(self):
        """This is a stand-in for blockicons.isPseudoBlockIc, and applies to any
        statement that hangs significantly left of the sequence line (currently only
        pseudo-block icons) but mainly avoids a circular import of blockicons."""
        return self.indentDepthAdj > 16


class LazyLayout:
    """Object to stand in for a yet-uncalculated layout in an ExprLayout part list."""
    def __init__(self, icOrListMgr, argRequired=False, addBrkLvl=0):
        self.icOrListMgr = icOrListMgr
        if isinstance(self.icOrListMgr, ListLayoutMgr):
            self.argRequired = argRequired
        self.addedBrkLvl = addBrkLvl

    def calcLayouts(self, marginLimit):
        if isinstance(self.icOrListMgr, ListLayoutMgr):
            return self.icOrListMgr.calcLayouts(marginLimit=marginLimit,
                argRequired=self.argRequired)
        layout = self.icOrListMgr.calcLayouts(marginLimit)
        # Note that although we have break-level information, we can't apply it here
        # because calcLayouts may itself return a lazy layout, and pushBrkLvl requires
        # these all to be expanded before processing (see ExprLayout._expandlazyLayout).
        return layout

def pushBrkLvl(layout, nLevels=1):
    """If the layout is an expression layout (or LazyLayout containing an icon whose
    calcLayouts call produces one), increase break levels in the given layout by nLevels
    to make room for a new one (presumably 0).  Also returns layout (which is technically
    unnecessary, since layout is modified, but allows it to be wrapped around a
    calcLayouts call."""
    if isinstance(layout, (list, tuple)):
        return layout
    if isinstance(layout, LazyLayout):
        layout.addedBrkLvl += nLevels
        return layout
    if layout.partLayouts is None:
        return layout
    for i, lvlOrLayout in enumerate(layout.partLayouts):
        if isinstance(lvlOrLayout, int):
            layout.partLayouts[i] += nLevels
    return layout

def setSeqOffsetsToReferred(ic):
    """If the given icon has an input site coincident with its output or sequence
    sites, find the child icon that owns the lowest coincident input at that site
    and set the yOffsets for this layout's icon seqIn and seqOut sites to the Y values
    from the "referred" icon that will draw them.  This should be called from the
    doLayout method of any icon that has a coincident input/sequence site and must
    appear AFTER the call to doSubLayouts to ensure that icon owning the referred
    sites has finished setting up its site offsets."""
    coincSite = ic.hasCoincidentSite()
    if not coincSite:
        return  # No coincident site: do nothing
    coincIc, coincSite = iconsites.lowestCoincidentSite(ic, coincSite)
    childIc = coincIc.childAt(coincSite)
    if childIc is None:
        return  # The lowest coincident site is empty: do nothing
    # There is a valid icon that will get the referred sites: copy its siteOffsets
    icYOff = childIc.rect[1] - ic.rect[1]
    found = False
    newLeft, newTop, newRight, newBottom = ic.rect
    if childIc.hasSite('seqIn'):
        ic.sites.seqIn.yOffset = childIc.sites.seqIn.yOffset + icYOff
        found = True
        newTop = max(0, ic.rect[1] + ic.sites.seqIn.yOffset)
    if childIc.hasSite('seqOut'):
        ic.sites.seqOut.yOffset = childIc.sites.seqOut.yOffset + icYOff
        newBottom = max(ic.rect[3] + icYOff, ic.rect[1] + ic.sites.seqOut.yOffset)
        found = True
    if found:
        # I am on the fence about expanding the icon's rectangle to encompass the new
        # site positions.  In practice all of the current code that searches by site
        # position, looks at entire statements and does not filter sites out based on
        # their icon rectangle, so as long as we're not drawing them, we don't need the
        # rectangle to cover them.  The argument for enabling the code below is that the
        # inconsistency that an icon can own something outside of its rectangle might
        # be confusing to future developers.
        # icon.expandIconRect(ic, (newLeft, newTop, newRight, newBottom))
        pass
    else:
        print("setSeqOffsetsToReferred could not find referred site(s) for icon",
            ic.dumpName(), 'in', childIc.dumpName())

@dataclass
class _ExprPartLayout:
    """Layout information for a single icon part.  A part for expression layout purposes
    is a rectangle of a fixed size that needs to be placed serially that represents an
    independently movable part of an icon."""
    ic: object
    siteName: object
    width: int
    height: int
    yOffset: int        # Equivalent of Layout parentSiteOffset
    siteYOffset: int    # Site is expected to be on the right edge of the part, but
                        # but might be offset up/down if it were an attribute site

    def incorporateRectIntoLayout(self, layout, layoutX, layoutY):
        """Expand the layout rectangle and the prototype icon rectangle to incorporate
        the layout part (self) at the given location in layout coordinates.  If layoutX
        is negative (as it will be if the layout part is wrapped to a position left of
        the layout origin) expand the icon's rectangles left to the new origin.  Note
        that the rectangle defined by the layout itself is not adjusted left in this
        case.  The layout origin is still considered to be at the output/seqInsert site
        of the icon, and siteOffsets may end up with negative values.  Indeed,
        layout.width will be wrong at this point, but since this is a layout generated
        via the wrapping process, only the boundaries for the top-level of the expression
        are ever used, and those will be correct as nothing is wrapped left of it."""
        heightAbove = self.yOffset - layoutY
        heightBelow = layoutY - self.height - self.yOffset
        layoutHeightAbove = max(heightAbove, layout.parentSiteOffset)
        layoutHeightBelow = max(heightBelow, layout.height - layout.parentSiteOffset)
        layout.height = layoutHeightAbove + layoutHeightBelow
        layout.parentSiteOffset = layoutHeightAbove
        layout.width = max(layout.width, layoutX + self.width)
        if layout.iconRectLeft is None:
            layout.iconRectLeft = layoutX
            layout.iconRectTop = layoutY - self.yOffset
            layout.iconRectRight = layoutX + self.width
            layout.iconRectBottom = layoutY + self.height - self.yOffset
        else:
            layout.iconRectLeft = min(layout.iconRectLeft, layoutX)
            layout.iconRectTop = min(layout.iconRectTop, layoutY - self.yOffset)
            layout.iconRectRight = max(layout.iconRectRight, layoutX + self.width)
            layout.iconRectBottom = max(layout.iconRectBottom, layoutY + self.height
                - self.yOffset)

class EmptyArgLayout(_ExprPartLayout):
    #... are ic and/or siteName actually used?
    def __init__(self, ic, siteName, forListArg=False):
        self.ic = ic
        self.siteName = siteName
        self.width = icon.LIST_EMPTY_ARG_WIDTH if forListArg else \
            icon.EMPTY_ARG_WIDTH
        self.height = icon.minTxtIconHgt
        self.yOffset = icon.minTxtIconHgt // 2
        self.siteYOffset = 0

def _findRightmostLayoutSite(layout):
    """Find the icon and siteName to own the wrap-arrow symbols given the Layout
    or _ExprPartLayout to the left of the wrap break-point."""
    if isinstance(layout, _ExprPartLayout):
        return layout.ic, layout.siteName
    # layout is Layout object
    return icon.rightmostSite(layout.icon)

def _findSublayoutAndOriginFromDict(ic, existingLayouts, existingLayoutOrigins):
    """Return the layout and layout origin x and y for icon, ic, which has an ancestor in
    dictionary, existingLayouts, and whose ancestor has an origin position in
    existinglayoutOrigins.  Once the transition to expression wrapping is complete, It's
    possible this code may never be called again, as it depends upon an inline-wrapped
    layout designating a child icon as being to its right in an expression, which
    hopefully will not happen."""
    # Look upwards through the parents of ic to find the one for which we have a layout
    parents = list(ic.parentage(includeSelf=True))
    for i, parent in enumerate(parents):
        if parent in existingLayouts:
            parentLayout = existingLayouts[parent]
            parentOriginX, parentOriginY = existingLayoutOrigins[parent]
            return _findSubLayoutAndOrigin(ic, parentLayout, parentOriginX, parentOriginY)
    raise RuntimeError("_findSublayoutAndOriginFromDict could not find icon parent")

def _findSubLayoutAndOrigin(ic, parentLayout, parentOriginX, parentOriginY):
    parents = list(ic.parentage(includeSelf=True))
    for i, parent in enumerate(parents):
        if parent is parentLayout.icon:
            parents = parents[:i+1]
            break
    else:
        raise RuntimeError("_findSublayoutOrigin could not find given parent layout")
    # Trace downward through the layout hierarchy from the top known layout to get
    # intermediate layouts, and eventually the prize of the layout for ic and its origin.
    parents.reverse()
    parent = parents[0]
    layouts = [parentLayout]
    childLayout = parentLayout
    childOriginX = parentOriginX
    childOriginY = parentOriginY
    for child in parents[1:]:
        childSite = parent.siteOf(child)
        childLayout = parentLayout.subLayouts[childSite]
        childOffsetX, childOffsetY = parentLayout.siteOffsets[childSite]
        childOriginX = parentOriginX + childOffsetX
        childOriginY = parentOriginY + childOffsetY
        layouts.append(childLayout)
        parent = child
        parentLayout = childLayout
        parentOriginX = childOriginX
        parentOriginY = childOriginY
    return childLayout, childOriginX, childOriginY

def _layoutSupSubAdj(parentLayout):
    rightmostIc, rightmostSite = icon.rightmostSite(parentLayout.icon)
    layout, originX, originY = _findSubLayoutAndOrigin(rightmostIc, parentLayout, 0, 0)
    return originY + layout.siteOffsets[rightmostSite][1]
