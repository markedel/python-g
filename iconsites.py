# Copyright Mark Edel  All rights reserved
import re
import comn
import icon

parentSiteTypes = {'output', 'attrOut', 'cprhOut'}
childSiteTypes = {'input', 'attrIn', 'cprhIn'}
matingSiteType = {'output':'input', 'input':'output', 'attrOut':'attrIn',
 'attrIn':'attrOut', 'seqOut':'seqIn', 'seqIn':'seqOut', 'cprhIn':'cprhOut',
 'cprhOut':'cprhIn'}

isSeriesRe = re.compile(".*_\\d*$")

class IconSite:
    def __init__(self, siteName, siteType, xOffset=0, yOffset=0, cursorTravOrder=None,
            cursorOnly=False, cursorSkip=False):
        self.name = siteName
        self.type = siteType
        self.xOffset = xOffset
        self.yOffset = yOffset
        self.att = None
        if cursorTravOrder is not None:
            self.order = cursorTravOrder
        if cursorOnly:
            self.cursorOnly = True
        if cursorSkip:
            self.cursorSkip = True

    def attach(self, ownerIcon, fromIcon, fromSiteId=None):
        # Remove original link from attached site
        if self.att:
            backLinkSite = self.att.siteOf(ownerIcon)
            if backLinkSite is not None:
                self.att.sites.lookup(backLinkSite).att = None
        else:
            backLinkSite = None
        ownerIcon.window.undo.registerAttach(ownerIcon, self.name, self.att, backLinkSite)
        # If attaching None (removing attachment), no bidirectional link to make
        if fromIcon is None:
            self.att = None
            return
        # Determine the back-link
        if fromSiteId is None:
            siteType = matingSiteType[self.type]
            sites = fromIcon.sites.sitesOfType(siteType)
            if sites is None or len(sites) == 0:
                print("Failed to find appropriate back-link for attaching", ownerIcon,
                 "site", self.name, "to", fromIcon, "type", siteType)
                return
            fromSiteId = sites[0]
            if len(sites) != 1:
                print("Attaching icon,", ownerIcon, "site", self.name, "to", fromIcon,
                 "site", fromSiteId, "but multiple targets made choice ambiguous")
        fromSite = fromIcon.sites.lookup(fromSiteId)
        if fromSite is None:
            if fromIcon.sites.isSeries(fromSiteId):
                print("Could not attach icon: parent link points to series", fromSiteId)
            else:
                print("Could not attach icon: invalid back-link (fromSiteId)", fromSiteId)
            return
        # Make the (bidirectional) link
        self.att = fromIcon
        fromSite.att = ownerIcon

class IconSiteSeries:
    def __init__(self, name, siteType, initCount=0, initOffsets=None, curTravOrder=None,
            cursorSkip=False):
        self.type = siteType
        self.name = name
        self.order = curTravOrder  # Cursor traversal order in parent site list
        self.cursorSkip = cursorSkip
        self.sites = [None] * initCount
        for idx in range(initCount):
            if initOffsets is not None and idx < len(initOffsets):
                xOff, yOff = initOffsets[idx]
            else:
                xOff, yOff = 0, 0
            self.sites[idx] = IconSite(makeSeriesSiteId(name, idx), siteType, xOff, yOff,
                cursorSkip=cursorSkip)

    def __getitem__(self, idx):
        return self.sites[idx]

    def __len__(self):
        return len(self.sites)

    def insertSite(self, insertIdx):
        site = IconSite(makeSeriesSiteId(self.name, insertIdx), self.type,
            cursorSkip=self.cursorSkip)
        self.sites[insertIdx:insertIdx] = [site]
        for i in range(insertIdx+1, len(self.sites)):
            self.sites[i].name = makeSeriesSiteId(self.name, i)

    def removeSite(self, ic, idx):
        del self.sites[idx]
        for i in range(idx, len(self.sites)):
            self.sites[i].name = makeSeriesSiteId(self.name, i)

class IconSiteList:
    """
    @DynamicAttrs
    """
    def __init__(self):
        self._typeDict = {}
        self.nextCursorTraverseOrder = 0

    def lookup(self, siteId):
        """External to the icon, sites are usually identified by name, but older code
        did so with a tuple: (site-type, site-index).  If siteId is just a name, it is
        in the this object's dictionary.  If it's an old-style tuple, print a warning
        and translate."""
        # If it is an individual site, it will be in the object's dictionary
        siteId = self.siteIdWarn(siteId)
        if hasattr(self, siteId):
            site = getattr(self, siteId)
            if isinstance(site, IconSite):
                return site
            return None
        # If it is a series site, split the name up in to the series name and index
        # and return the site by-index from the series
        seriesName, seriesIndex = splitSeriesSiteId(siteId)
        if seriesName is None:
            return None
        series = getattr(self, seriesName, None)
        if not isinstance(series, IconSiteSeries) or seriesIndex >= len(series):
            return None
        return series[seriesIndex]

    def lookupSeries(self, seriesName):
        series = getattr(self, self.siteIdWarn(seriesName))
        return series if isinstance(series, IconSiteSeries) else None

    def siteIdWarn(self, idOrTypeAndIdx):
        """Temporary routine until all instances of ("siteType", idx) are removed"""
        if isinstance(idOrTypeAndIdx, tuple):
            print("Old style type+idx encountered")
            siteType, idx = idOrTypeAndIdx
            return self._typeDict[siteType][idx]
        return idOrTypeAndIdx

    def sitesOfType(self, siteType):
        return self._typeDict.get(siteType)

    def isSeries(self, siteId):
        return self.getSeries(siteId) is not None

    def allSites(self, expandSeries=True):
        """Traverse all sites in the list (generator).  If expandSeries is set to False,
        yields an IconSeries object instead of enumerating the sites of the series."""
        for siteNames in self._typeDict.values():
            for name in siteNames:
                site = getattr(self, name)
                if isinstance(site, IconSiteSeries):
                    if expandSeries:
                        for s in site.sites:
                            yield s
                    else:
                        yield site
                elif isinstance(site, IconSite):
                    yield site

    def siteOfAttachedIcon(self, ic):
        for site in self.allSites():
            if site.att == ic:
                return site
        return None

    def childSites(self, expandSeries=True):
        childList = []
        for siteType, siteNames in self._typeDict.items():
            if siteType in childSiteTypes:
                for name in siteNames:
                    site = getattr(self, name)
                    if expandSeries and isinstance(site, IconSiteSeries):
                        childList += site.sites
                    else:
                        childList.append(site)
        return childList

    def parentSites(self):
        parentList = []
        for siteType, siteNames in self._typeDict.items():
            if siteType in parentSiteTypes:
                for name in siteNames:
                    site = getattr(self, name)
                    if isinstance(site, IconSiteSeries):
                        parentList += site.sites
                    else:
                        parentList.append(site)
        return parentList

    def add(self, name, siteType, xOffset=0, yOffset=0, cursorTraverseOrder=None,
            cursorOnly=False, cursorSkip=False):
        """Add a new icon site to the site list given name and type.  Optionally add
        offset from the icon origin (sometimes these are not known until the icon has
        been through layout).  The IconSiteList also determines the text-flow through
        the icon (how cursor traversal moves from icon to icon for left and right arrow
        keys).  If cursorTraverseOrder is not specified, this is determined from the
        order in which sites are added and the site type."""
        if cursorTraverseOrder is None and siteType in childSiteTypes:
            cursorTraverseOrder = self.nextCursorTraverseOrder
            self.nextCursorTraverseOrder += 1
        elif cursorTraverseOrder is not None:
            self.nextCursorTraverseOrder = max(cursorTraverseOrder+1,
                self.nextCursorTraverseOrder)
        setattr(self, name, IconSite(name, siteType, xOffset, yOffset,
            cursorTravOrder=cursorTraverseOrder, cursorOnly=cursorOnly,
            cursorSkip=cursorSkip))
        if siteType not in self._typeDict:
            self._typeDict[siteType] = []
        self._typeDict[siteType].append(name)

    def addSeries(self, name, siteType, initCount=0, initOffsets=None,
            cursorTraverseOrder=None, cursorSkip=False):
        """Add a new icon site series to the site list given series name and type.
         Optionally add offset of the first element from the icon origin (sometimes these
         are not known until the icon has been through layout).  The IconSiteList also
         determines the text-flow through the icon (how cursor traversal moves from icon
         to icon for left and right arrow keys). Traversal within the series is automatic
         and keyed to the site index (which is part of the name of the series site).
         If curTravOrder is not specified, the positioning of the series within the
         traversal order of the site list is determined from the order in which sites and
         site series are added and the site type."""
        if cursorTraverseOrder is None and siteType in childSiteTypes:
            cursorTraverseOrder = self.nextCursorTraverseOrder
            self.nextCursorTraverseOrder += 1
        elif cursorTraverseOrder is not None:
            self.nextCursorTraverseOrder = max(cursorTraverseOrder+1,
                self.nextCursorTraverseOrder)
        series = IconSiteSeries(name, siteType, initCount, initOffsets,
            cursorTraverseOrder, cursorSkip=cursorSkip)
        setattr(self, name, series)
        if siteType not in self._typeDict:
            self._typeDict[siteType] = []
        self._typeDict[siteType].append(name)

    def removeSeries(self, name):
        series = getattr(self, name)
        delattr(self, name)
        self._typeDict[series.type].remove(name)

    def renameSeries(self, oldName, newName):
        series = self.getSeries(oldName)
        for idx, site in enumerate(series.sites):
            site.name = makeSeriesSiteId(newName, idx)
        series.name = newName
        delattr(self, oldName)
        setattr(self, newName, series)
        self._typeDict[series.type].remove(oldName)
        self._typeDict[series.type].append(newName)

    def renameSite(self, oldName, newName):
        if not hasattr(self, oldName):
            print('renameSite: passed site series')
            return
        site = getattr(self, oldName)
        if not isinstance(site, IconSite):
            print('renameSite: siteId not found in site list')
            return
        site.name = newName
        delattr(self, oldName)
        setattr(self, newName, site)
        self._typeDict[site.type].remove(oldName)
        self._typeDict[site.type].append(newName)

    def getSeries(self, siteIdOrSeriesName):
        """If siteId is the part of a series, return a list of all of the sites in the
        list.  Otherwise return None"""
        if hasattr(self, siteIdOrSeriesName):
            seriesName = siteIdOrSeriesName
        else:
            seriesName, seriesIndex = splitSeriesSiteId(siteIdOrSeriesName)
            if seriesName is None:
                return None
        if hasattr(self, seriesName):
            series = getattr(self, seriesName)
            if isinstance(series, IconSiteSeries):
                return series
        return None

    def remove(self, name):
        """Delete a (non-series) icon site."""
        if hasattr(self, name):
            site = getattr(self, name)
            if isinstance(site, IconSite):
                delattr(self, name)
                self._typeDict[site.type].remove(name)

    def removeSeriesSiteById(self, ic, siteId):
        """Remove a site from a series given siteId (which encodes index)"""
        name, idx = splitSeriesSiteId(siteId)
        if name is None:
            print("failed to remove series site", siteId)
        else:
            self.removeSeriesSiteByNameAndIndex(ic, name, idx)

    def removeSeriesSiteByNameAndIndex(self, ic, seriesName, idx):
        """Remove a site from a series given the series name and index"""
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries) and idx < len(series):
            if len(series.sites) == 1:  # Leave a single site for insertion
                series.sites[0].attach(ic, None)
            else:
                series.sites[idx].attach(ic, None)
                series.removeSite(ic, idx)
                ic.window.undo.registerRemoveSeriesSite(ic, seriesName, idx)

    def insertSeriesSiteById(self, ic, siteId):
        name, idx = splitSeriesSiteId(siteId)
        if name is None:
            print("failed to insert series site", siteId)
        else:
            self.insertSeriesSiteByNameAndIndex(ic, name, idx)

    def insertSeriesSiteByNameAndIndex(self, ic, seriesName, insertIdx):
        ic.window.undo.registerInsertSeriesSite(ic, seriesName, insertIdx)
        series = getattr(self, seriesName)
        if isinstance(series, IconSiteSeries):
            series.insertSite(insertIdx)

    def nextCursorSite(self, siteId):
        """Return the siteId of the site to the right in the text sequence, None if
        siteId is already the rightmost site in the site list.  Note that sites marked
        with 'cursorSkip' (provided they are in the traversal sequence) are included."""
        if self.isSeries(siteId):
            name, idx = splitSeriesSiteId(siteId)
            series = getattr(self, name, None)
            if series is None:
                print("nextCursorSite called with non-existent series name")
                return None
            if idx + 1 < len(series):
                return makeSeriesSiteId(name, idx + 1)
            order = series.order
        else:
            site = getattr(self, siteId, None)
            if site is None:
                print("nextCursorSite called with non-existent site")
                return None
            order = site.order
        nextSite = self.nextTraversalSiteOrSeries(order)
        if nextSite is None:
            return None
        if isinstance(nextSite, IconSiteSeries):
            return makeSeriesSiteId(nextSite.name, 0)
        return nextSite.name

    def nextTraversalSiteOrSeries(self, orderIdx):
        """Returns the next site or series in the site list with higher traversal order
        (right of) orderIdx.  Note that sites marked with 'cursorSkip' (provided they are
        in the traversal sequence) are included."""
        for i in range(orderIdx+1, self.nextCursorTraverseOrder):
            nextSite = self.nthCursorSite(i)
            if nextSite is not None:
                return nextSite
        return None

    def prevCursorSite(self, siteId):
        """Return the siteId of the site to the left in the lexical sequence, None if
        siteId is already the leftmost site in the site list.  Note that sites marked
        with 'cursorSkip' (in the traversal sequence) are included."""
        if self.isSeries(siteId):
            name, idx = splitSeriesSiteId(siteId)
            series = getattr(self, name, None)
            if series is None:
                print("prevCursorSite called with non-existent series name")
                return None
            if idx > 0:
                return makeSeriesSiteId(name, idx-1)
            order = series.order
        else:
            site = getattr(self, siteId, None)
            if site is None:
                print("prevCursorSite called with non-existent site")
                return None
            if not hasattr(site, 'order') or site.order is None:
                print("prevCursorSite called with out-of-traversal site")
                return None
            order = site.order
        for i in range(order-1, -1, -1):
            prevSite = self.nthCursorSite(i)
            if prevSite is not None:
                if isinstance(prevSite, IconSiteSeries):
                    return makeSeriesSiteId(prevSite.name, len(prevSite)-1)
                return prevSite.name
        return None

    def lastCursorSite(self):
        """Return siteId for the rightmost site (in cursor traversal) of the site list.
        Note that sites marked with 'cursorSkip' will be included.  Currently, the only
        case of this is unclosed and naked tuples, which can have a comprehension site
        on the right."""
        lastSite = self.nthCursorSite(-1)
        if lastSite is None:
            return None
        if isinstance(lastSite, IconSiteSeries):
            return makeSeriesSiteId(lastSite.name, len(lastSite) - 1)
        return lastSite.name

    def firstCursorSite(self):
        """Returns siteId for the leftmost (child-containing-type) site of the list.
        Note that sites marked with 'cursorSkip' will be included, however, currently no
        icons start with a cursorSkip site (or are ever likely to)."""
        firstSite = self.nthCursorSite(0)
        if firstSite is None:  # order of the first item does not have to be 0
            firstSite = self.nextTraversalSiteOrSeries(0)
        if firstSite is None:
            return None
        if isinstance(firstSite, IconSiteSeries):
            return makeSeriesSiteId(firstSite.name, 0)
        return firstSite.name

    def nthCursorSite(self, n):
        """Return the site or series object whose cursor traversal order matches n
        (a series has a single index).  Returns None if no site or series claims that
        index.  An n of -1 returns the last site or series in the site list."""
        lastSiteOrder = -1
        lastSite = None
        for siteNames in self._typeDict.values():
            for name in siteNames:
                site = getattr(self, name)
                if hasattr(site, 'order') and site.order is not None:
                    if n == -1:
                        if lastSiteOrder < site.order:
                            lastSiteOrder = site.order
                            lastSite = site
                    elif  site.order == n:
                        return site
        if n == -1:
            return lastSite
        return None

    def traverseLexical(self):
        """Yield the sites or site series in the site list in lexical traversal order.
        Note that this only traverses child sites (not sequence or parent)."""
        site = self.nthCursorSite(0)
        if site is None:  # order of the first item does not have to be 0
            site = self.nextTraversalSiteOrSeries(0)
        if site is None:
            return
        while True:
            yield site
            site = self.nextTraversalSiteOrSeries(site.order)
            if site is None:
                return

    def makeSnapLists(self, ic, x, y, forCursor=False):
        snapSites = {}
        for site in self.allSites():
            # Omit any site whose attached icon has a site of the same type, at the
            # same location.  In such a case we want both dropped icons and typing to
            # go to the site of the innermost (most local) icon.
            if hasLowerCoincidentSite(ic, site.name):
                continue
            # Numeric icons have attribute sites for cursor, only (no snapping)
            if site.type == 'attrIn' and not forCursor and hasattr(site, 'cursorOnly'):
                continue
            # seqIn and seqOut sites are only valid for icons at the top level
            if site.type in ('seqIn', 'seqOut') and ic.parent() is not None:
                continue
            # The first icon in a sequence hosts the snap site for the sequence
            hasPrev = ic.prevInSeq() is not None
            if hasPrev and site.type in ('output', 'seqInsert') and not forCursor:
                continue
            # Add the snap site to the list
            if site.type not in snapSites:
                snapSites[site.type] = []
            snapSites[site.type].append((ic, (x + site.xOffset, y + site.yOffset),
                site.name))
        # Add a replace site to the right of and slightly below the output site, unless
        # that puts it too close to the right edge of the icon, in which case back it off
        # by half of the exceeded distance.
        if isinstance(ic, icon.BlockEnd):
            # Giving BlockEnd icons replace sites would only bring pain
            return snapSites
        for site in self.allSites():
            if site.type in parentSiteTypes:
                parentSite = site
                break
        else:
            if ic.hasSite('seqIn') and ic.hasSite('seqOut'):
                parentSite = ic.sites.seqIn
            else:
                return snapSites
        siteType = parentSite.type
        if siteType == 'output':
            replaceName = 'replaceExprIc'
            depth = icon.OUTPUT_SITE_DEPTH
        elif siteType == 'attrOut':
            replaceName = 'replaceAttrIc'
            depth = icon.ATTR_SITE_DEPTH
        elif siteType == 'cprhOut':
            replaceName = 'replaceCprhIc'
            depth = 0
        else:
            replaceName = 'replaceStmtIc'
            depth = icon.SEQ_SITE_DEPTH
        xOffset = parentSite.xOffset + icon.REPLACE_SITE_X_OFFSET
        distToRightEdge = comn.rectWidth(ic.rect) - (xOffset + depth)
        if distToRightEdge < icon.REPLACE_SITE_X_OFFSET:
            xOffset -= distToRightEdge // 2
        if siteType == 'seqIn':
            # If we didn't find an output site on which to base the replace site, use the
            # sequence sites and guess that the icon body will be be vertically half way
            # between (in there are cases where this is wrong, the specific icon(s) will
            # need to correct it in their snapLists method).
            yCenter = (ic.sites.seqIn.yOffset + ic.sites.seqOut.yOffset) // 2
        else:
            yCenter = parentSite.yOffset
        yOffset = yCenter + icon.REPLACE_SITE_Y_OFFSET
        if not ic.hasCoincidentSite():
            # Icons that don't have sites on the left have to add their own replacement
            # sites, because we can't calculate positioning at this low level
            snapSites[replaceName] = [(ic, (x + xOffset, y + yOffset), replaceName)]
        # For top-level icons, add an additional site to the left of the icon (in the
        # margin) for full-stmt replacement.  While this is redundant with the replace
        # site for many types of statements, for those with coincident input sites
        # (particularly assignments), the top-level icon is not the lexically-first icon.
        # Also, this enables a Shift+drag method for multi-stmt drop-target selection.
        if ic.parent() is None:
            xOffset = parentSite.xOffset + depth + icon.STMT_REPLACE_SITE_X_OFFSET
            snapSites['replaceStmt'] = [(ic, (x + xOffset, y + yCenter), 'replaceStmt')]
        return snapSites

def makeSeriesSiteId(seriesName, seriesIdx):
    return seriesName + "_%d" % seriesIdx

def isSeriesSiteId(siteId):
    return isSeriesRe.match(siteId)

def splitSeriesSiteId(siteId):
    splitName = siteId.split('_')
    if len(splitName) != 2:
        return None, None
    name, idx = splitName
    if len(name) == 0 or len(idx) == 0 or not idx.isnumeric():
        return None, None
    return name, int(idx)

def nextSeriesSiteId(siteId):
    name, idx = splitSeriesSiteId(siteId)
    return makeSeriesSiteId(name, idx+1)

def prevSeriesSiteId(siteId):
    name, idx = splitSeriesSiteId(siteId)
    if idx == 0:
        return None
    return makeSeriesSiteId(name, idx-1)

def hasLowerCoincidentSite(ic, siteId):
    """Returns True if there is an icon lower in the hierarchy sharing this site of ic"""
    if ic is None or ic.typeOf(siteId) != "input":
        return False
    attachedIcon = ic.childAt(siteId)
    if attachedIcon is None:
        return False
    return attachedIcon.hasCoincidentSite() is not None

def isCoincidentSite(ic, siteId):
    """Returns True if siteId is a site of ic that is coincident with its output"""
    return ic is not None and siteId == ic.hasCoincidentSite()

def highestCoincidentIcon(ic, arithOnly=False):
    """Return highest icon with an output coincident with that of ic.  There is an
    optional (arithOnly=True) exception for naked tuples and assignments.  This is needed
    when the call is used to help find the top of an arithmetic expression"""
    while True:
        parent = ic.parent()
        if parent is None or not isCoincidentSite(parent, parent.siteOf(ic)):
            return ic
        if arithOnly and (hasattr(parent, 'noParens') and parent.noParens or
                parent.__class__.__name__ in ('AssignIcon', 'AugmentedAssignIcon',
                'SliceIcon')):
            return ic
        ic = parent

def highestCoincidentSite(ic, site):
    """Return highest icon and site at the highest level in the icon hierarchy that is
    coincident with the given icon (ic) and site."""
    if not isCoincidentSite(ic, site):
        return ic, site
    while True:
        parent = ic.parent()
        if parent is None:
            return ic, site
        parentSite = parent.siteOf(ic)
        if not isCoincidentSite(parent, parentSite):
            return parent, parentSite
        site = parentSite
        ic = parent

def lowestCoincidentSite(ic, site=None):
    """Return the icon and site occupying the lowest coincident input site at (ic, site).
    site can also be passed as None, to answer the question: "what is the lowest level
    coincident site to that holding ic.".  Note that in the site=None case the function
    can return None, None."""
    # ic itself does not need to have a coincident site (site is coincident with itself)
    if site is None:
        child = ic
        ic = ic.parent()
        if ic is None:
            return None, None
        site = ic.siteOf(child)
    else:
        child = ic.childAt(site)
    if child is None:
        return ic, site
    childSite = child.hasCoincidentSite()
    if not childSite:
        return ic, site
    ic = child
    site = childSite
    # Descend the hierarchy of icons with coincident sites
    while True:
        child = ic.childAt(site)
        if child is None:
            return ic, site
        if ic.hasCoincidentSite() == site:
            childCoincidentSite = child.hasCoincidentSite()
            if childCoincidentSite is None:
                return ic, site
            else:
                ic = child
                site = childCoincidentSite
        else:
            return ic, site
