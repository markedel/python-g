import icon
import iconsites
import listicons
import entryicon
import parenicon
import opicons
import infixicon
import reorderexpr
import filefmt

def insertAtSite(atIcon, atSite, topInsertedIcon, cursorLeft=False):
    """Insert a single tree of icons into another tree of icons.  Note that this is low-
    level insertion code, which does not deal with bigger questions of how to organize
    statements for insertion, and will not take advantage of list sites to avoid adding
    unnecessary placeholder icons.  Returns the icon and site at which the cursor should
    be placed (should this operation determine cursor placement).  If an entry icon was
    needed after the insertion, returns that as the cursor icon and None as the cursor
    site.  This may replace top-level icons to satisfy arithmetic priorities, or produce
    two statements when the inserted icon can't be merged.  You can safely use the
    returned cursor icon (call the icon's .topLevelParent() method) to find the updated
    top icon and detect the change if that is needed.  Setting cursorLeft to True will
    return the appropriate cursor position to the left of the insertion (approximately
    equivalent to  (atIcon, atSite), but adjusted for arithmetic reordering and
    positioned inside any added placeholder entry icon."""
    insRightIc, insRightSite = icon.rightmostSite(topInsertedIcon)
    # We accept output sites At the top level, since the cursor can be attached to them.
    if atIcon.typeOf(atSite) in iconsites.parentSiteTypes:
        parent = atIcon.parent()
        if parent is not None:
            # We hope not to see cursors on output sites that are not on the top level,
            # but they can't be ruled out.  In this case, use the parent site instead.
            atSite = parent.siteOf(atIcon)
            atIcon = parent
        else:
            # Reverse the insertion, replacing the tree holding the insert point with
            # the tree being inserted before it.  Note that in the initial replaceTop
            # call, we're passing transferStmtComment as False, because we don't yet
            # know whether the recursive call to insertAtSite will be keeping the
            # inserted code as a distinct statement, or merging it with the existing
            # statement.
            atIcon.window.replaceTop(atIcon, topInsertedIcon, transferStmtComment=False)
            rightIcOfIns, rightSiteOfIns = icon.rightmostSite(topInsertedIcon)
            cursorIc, cursorSite = insertAtSite(rightIcOfIns, rightSiteOfIns, atIcon,
                cursorLeft=True)
            if cursorLeft:
                return cursorLeftOfIcon(atIcon)
            return cursorIc, cursorSite
    # Inserting something at a sequence site, by definition, means don't join it
    if atSite == 'seqIn':
        icon.insertSeq(topInsertedIcon, atIcon, before=True)
        atIcon.window.addTop(topInsertedIcon)
        if cursorLeft:
            return topInsertedIcon, 'seqIn'
        return insRightIc, insRightSite
    elif atSite == 'seqOut':
        icon.insertSeq(topInsertedIcon, atIcon)
        atIcon.window.addTop(topInsertedIcon)
        if cursorLeft:
            return topInsertedIcon, 'seqIn'
        return insRightIc, insRightSite
    # If the inserted code is statement-level-only, we can only insert it at either the
    # leftmost or rightmost sites, or within expressions that can be split all the way to
    # the top level.
    rightmostIc, rightmostSite = icon.rightmostSite(atIcon.topLevelParent())
    if isStmtLevelOnly(topInsertedIcon):
        if atIcon is rightmostIc and (atSite == rightmostSite or atSite == 'seqOut'):
            # The rightmost site is a safe places to start a new statement, and we must
            # because the inserted icon has to be kept at the statement level.
            icon.insertSeq(topInsertedIcon, atIcon.topLevelParent())
            atIcon.window.addTop(topInsertedIcon)
            if cursorLeft:
                return topInsertedIcon, 'seqIn'
            return insRightIc, insRightSite
        if isLeftmostSite(atIcon, atSite):
            # The leftmost site is also safe because it can be a statement boundary, but
            # we may still be able to join the two.
            topDestIc = atIcon.topLevelParent()
            if isStmtLevelOnly(topDestIc):
                # Absolutely has to be a new statement
                icon.insertSeq(topInsertedIcon, topDestIc, before=True)
                atIcon.window.addTop(topInsertedIcon)
                if cursorLeft:
                    return topInsertedIcon, 'seqIn'
                return insRightIc, insRightSite
            else:
                # Attempt to join by reversing the places of the two icons and
                # recursively calling insertAtSite.
                atIcon.window.replaceTop(topDestIc, topInsertedIcon,
                    transferStmtComment=False)
                insertAtSite(insRightIc, insRightSite, topDestIc)
                if cursorLeft:
                    return cursorLeftOfIcon(topInsertedIcon.topLevelParent())
                return insRightIc, insRightSite
        # Sites not at the left or right are only possible if we can split the
        # expression around them
        enclosingIcon, enclosingSite = entryicon.findEnclosingSite(atIcon, atSite)
        if enclosingIcon is not None:
            return None, None
        topParent = atIcon.topLevelParent()
        left, right = entryicon.splitExprAtSite(atIcon, atSite, None)
        if left is not topParent:
            atIcon.window.replaceTop(topParent, left)
        icon.insertSeq(topInsertedIcon, left)
        atIcon.window.addTop(topInsertedIcon)
        needReorder = []
        appendAtSite(insRightIc, insRightSite, right, needReorder)
        reorderMarkedExprs(topInsertedIcon, needReorder, replaceTop=True)
        if cursorLeft:
            return topInsertedIcon, 'seqIn'
        return insRightIc, insRightSite
    # Replace the existing icons at the insertion site with the inserted tree.  Preserve
    # the removed icons as relocatedTree.  I don't think it's actually necessary to
    # insert at the lowest coincident site, as arithmetic reordering will ultimately
    # rearrange everything properly.  However, I made a comment in the original code
    # claiming that this was somehow essential, and now I'm afraid to remove it.
    lowestIc, lowestSite = iconsites.lowestCoincidentSite(atIcon, atSite)
    relocatedTree = lowestIc.childAt(lowestSite)
    lowestIc.replaceChild(None, lowestSite, leavePlace=True)
    needReorder = []
    cursorLeftIc, cursorLeftSite = appendAtSite(lowestIc, lowestSite, topInsertedIcon,
        needReorder)
    # Stitch relocatedTree to the right of the inserted icon tree.  If the sites are
    # compatible, just attach, otherwise add a placeholder entry icon.
    if relocatedTree is None:
        cursorIcon, cursorSite = insRightIc, insRightSite
    elif icon.validateCompatibleChild(relocatedTree, insRightIc, insRightSite):
        insRightIc.replaceChild(relocatedTree, insRightSite)
        if insRightIc.typeOf(rightmostSite) == 'input':
            checkReorder(insRightIc, needReorder)
        cursorIcon, cursorSite = insRightIc, insRightSite
    else:
        entryIc = entryicon.EntryIcon(window=atIcon.window)
        entryIc.appendPendingArgs([relocatedTree])
        insRightIc.replaceChild(entryIc, insRightSite)
        cursorIcon, cursorSite = entryIc, None
    reorderMarkedExprs(atIcon.topLevelParent(), needReorder, replaceTop=True)
    if cursorLeft:
        return cursorLeftIc, cursorLeftSite
    return cursorIcon, cursorSite

def appendAtSite(atIc, atSite, topInsertedIcon, needReorder):
    """Attach code under topInsertedIcon to site (atIc, atSite), as best as possible,
    including making use of empty site on the left (which will affect the hierarchy above
    the given site) or adapting it with a placeholder.  Assumes that the caller has
    filtered out all the cases where topInsertedIcon can't be attached."""
    if icon.validateCompatibleChild(topInsertedIcon, atIc, atSite):
        # The inserted code is directly compatible with the requested site: just attach
        atIc.replaceChild(topInsertedIcon, atSite)
        if atIc.typeOf(atSite) == 'input':
            checkReorder(topInsertedIcon, needReorder)
        return atIc, atSite
    else:
        # If the insertion site is not directly compatible with the top of the inserted
        # tree, it still may be possible to join the two trees without a placeholder.
        # If the inserted code has an empty site on the left, it may be possible to
        # move code from above the insertion site into that empty site.  Empty sites on
        # the left of the tree are, by nature, input sites, as only binary operators have
        # them.
        if leftSiteIsEmpty(topInsertedIcon) and atSite == 'attrIcon':
            leftIc, leftSite = lowestLeftSite(topInsertedIcon)
            attrRoot = icon.findAttrOutputSite(atIc)
            attrRootParent = attrRoot.parent()
            if attrRootParent is None:
                atIc.window.replaceTop(attrRoot, topInsertedIcon)
                leftIc.replaceChild(attrRoot, leftSite)
            else:
                attrRootSite = attrRootParent.siteOf(attrRoot)
                attrRootParent.replaceChild(None, attrRootSite, leavePlace=True)
                leftIc.replaceChild(attrRoot, leftSite)
                attrRootParent.replaceChild(topInsertedIcon, attrRootSite)
            checkReorder(topInsertedIcon, needReorder)
            return atIc, atSite
        else:
            # The inserted code could not be joined at the insert site, and must be
            # adapted with a placeholder icon
            entryIc = entryicon.EntryIcon(window=atIc.window)
            entryIc.appendPendingArgs([topInsertedIcon])
            if atIc.typeOf(atSite) == "cprhIn":
                # While users can't put a cursor on a comprehension site, they can do an
                # insertion at one by means of a selection that starts on one
                atIc, atSite = listicons.proxyForCprhSite(atIc, atSite)
            atIc.replaceChild(entryIc, atSite)
            return entryIc, None

def insertListAtSite(atIcon, atSite, seriesIcons, mergeAdjacent=True, cursorLeft=False):
    """Insert a series of icons into another tree of icons.  Note that this is low-level
    insertion code, and does not first check that it is safe to insert seriesIcons at
    atSite.  Also note that it will do both arithmetic reordering and possibly adding
    a top-level tuple, so icons above atIcon may be changed by the call.  Returns the
    icon and site at which the cursor should be placed (should this operation determine
    cursor placement).  If an entry icon was needed after the insertion, returns that as
    the cursor icon and None as the cursor site.  Normally (mergeAdjacent=True), the
    function will try to integrate the first and last elements with the icons preceding
    and following the insert site.  Setting mergeAdjacent to False tells the function to
    insert the first and last elements as-is even if they are compatible (of course, this
    won't work if the insertion point is in the middle of an expression, but the use case
    for this is list-insertion sites, which are only placed at list-element boundaries).
    Setting cursorLeft to True will return the appropriate cursor position to the left of
    the insertion (approximately equivalent to (atIcon, atSite), but adjusted for
    arithmetic reordering and positioned after any added comma or inside any added
    placeholder entry icon."""
    if len(seriesIcons) == 0:
        return atIcon, atSite
    # Use insertAtSite for single entries where no new series elements are needed.
    # Weeding out those cases makes it safe to do the prep-work for adding elements
    # (such as paren-to-tuple conversion), first, so the insert code can be simpler.
    enclosingIcon, enclosingSite = entryicon.findEnclosingSite(atIcon, atSite)
    if len(seriesIcons) == 1 and ((atIcon.typeOf(atSite) == 'input') and
            (atIcon.childAt(atSite) is None or rightSiteIsEmptyInput(seriesIcons[0])) or
            atSite == 'output' and rightSiteIsEmptyInput(seriesIcons[0]) or
            leftSiteIsEmpty(seriesIcons[0]) and atIcon.typeOf(atSite) == 'attrIn' or
            enclosingIcon is not None and not iconsites.isSeriesSiteId(enclosingSite)):
        return insertAtSite(atIcon, atSite, seriesIcons[0], cursorLeft=cursorLeft)
    # output sites at the top level are legal cursor sites, but will wreak havoc with
    # the later code.  Since we know we're inserting a list, it's safe to add a tuple
    # parent, here, and turn them in to input site references.
    if atIcon.typeOf(atSite) in iconsites.parentSiteTypes:
        parent = atIcon.parent()
        if parent is not None:
            # We hope not to see cursors on output sites that are not on the top level,
            # but they can't be ruled out.  In this case, use the parent site instead.
            atSite = parent.siteOf(atIcon)
            atIcon = parent
        else:
            newTuple = listicons.TupleIcon(window=atIcon.window, noParens=True)
            atIcon.window.replaceTop(atIcon, newTuple)
            if atIcon.typeOf(atSite) == 'output':
                newTuple.insertChild(atIcon, 'argIcons_0')
                atIcon = enclosingIcon = newTuple
                atSite = enclosingSite = 'argIcons_0'
            else:
                # Weird output site types 'attrOut' or 'cprhOut'
                newTuple.insertChildren(seriesIcons, 'argIcons_0')
                entryIc = entryicon.EntryIcon(window=atIcon.window)
                entryIc.appendPendingArgs([atIcon])
                rightmostIcon, rightmostSite = icon.rightmostSite(seriesIcons[-1])
                return insertAtSite(rightmostIcon, rightmostSite, atIcon,
                    cursorLeft=cursorLeft)
    if enclosingIcon is None:
        # We reached the top of the hierarchy without getting trapped.  Add a naked tuple
        # as parent to which to transfer the elements.
        enclosingIcon = listicons.TupleIcon(window=atIcon.window, noParens=True)
        topIc = atIcon.topLevelParent()
        atIcon.window.replaceTop(topIc, enclosingIcon)
        enclosingIcon.replaceChild(topIc, 'argIcons_0')
        enclosingSite = 'argIcons_0'
    elif isinstance(enclosingIcon, parenicon.CursorParenIcon):
        # Found a cursor paren icon that can be converted to a tuple
        newTuple = listicons.TupleIcon(window=atIcon.window)
        arg = enclosingIcon.childAt('argIcon')
        enclosingIcon.replaceChild(None, 'argIcon')
        enclosingIcon.replaceWith(newTuple)
        newTuple.replaceChild(arg, 'argIcons_0')
        if atIcon is enclosingIcon:
            atIcon = newTuple
            atSite = 'argIcons_0'
        enclosingIcon = newTuple
        enclosingSite = 'argIcons_0'
    elif not iconsites.isSeriesSiteId(enclosingSite):
        # We allow inserting a list at a non-series-capable site by making the list into
        # a tuple.  This is ugly, because it adds parens that the user didn't type, and
        # is only marginally useful, because non-series enclosing sites tend to be name
        # fields.  However, the alternative is rejecting and doing nothing, and the user
        # may conceivably want something inside the list or could be adding a function
        # call in the middle of an inline-if.
        newTuple = listicons.TupleIcon(window=atIcon.window)
        newTuple.insertChildren(seriesIcons, 'argIcons_0')
        return insertAtSite(atIcon, atSite, newTuple, cursorLeft=cursorLeft)
    # If we're inserting in an empty site of the series or on the left or right of a
    # series element with mergeAdjacent set to False, insert the list without merging
    # the first and/or last elements with the adjacent code.
    if (enclosingIcon is atIcon or isLeftmostSite(atIcon, atSite, enclosingIcon)) and \
            not mergeAdjacent:
        if enclosingIcon.childAt(enclosingSite):
            enclosingIcon.insertChildren(seriesIcons, enclosingSite)
            elemsAdded = len(seriesIcons)
        else:
            enclosingIcon.replaceChild(seriesIcons[0], enclosingSite)
            enclosingIcon.insertChildren(seriesIcons[1:],
                iconsites.nextSeriesSiteId(enclosingSite))
            elemsAdded = len(seriesIcons) - 1
        if cursorLeft:
            cursorIcon, cursorSite = enclosingIcon, enclosingSite
        else:
            if seriesIcons[-1] is None:  # Trailing comma
                name, idx = iconsites.splitSeriesSiteId(enclosingSite)
                cursorIcon = enclosingIcon
                cursorSite = iconsites.makeSeriesSiteId(name, idx + elemsAdded - 1)
            else:
                cursorIcon, cursorSite = icon.rightmostSite(seriesIcons[-1])
        return cursorIcon, cursorSite
    rightmostIcon, rightmostSite = icon.rightmostFromSite(enclosingIcon, enclosingSite)
    if atIcon is rightmostIcon and atSite == rightmostSite and not mergeAdjacent:
        insertSite = iconsites.nextSeriesSiteId(enclosingSite)
        enclosingIcon.insertChildren(seriesIcons, insertSite)
        if cursorLeft:
            cursorIcon, cursorSite = enclosingIcon, insertSite
        if seriesIcons[-1] is None:  # Inserted list has trailing comma
            name, idx = iconsites.splitSeriesSiteId(enclosingSite)
            cursorIcon = enclosingIcon
            cursorSite = iconsites.makeSeriesSiteId(name, idx + len(seriesIcons))
        else:
            cursorIcon, cursorSite = icon.rightmostSite(seriesIcons[-1])
        return cursorIcon, cursorSite
    # Inserting in an arithmetic expression that may have to be split around it.  The
    # splitExprAtSite function will return a left side and a right side, which then
    # must be merged with the leftmost icon in the inserted series and the rightmost
    # item in the inserted series.  Because our ability to insert new series elements
    # has already been vetted, we can avoid placeholders by using empty sites and adding
    # list elements.
    coincAtIcon, coincAtSite = iconsites.highestCoincidentSite(atIcon, atSite)
    left, right = entryicon.splitExprAtSite(atIcon, atSite, enclosingIcon)
    firstElem = seriesIcons[0]
    lastElem = seriesIcons[-1]
    if lastElem is None:  # Trailing comma
        rightIcOfLastElem = rightSiteOfLastElem = None
        name, idx = iconsites.splitSeriesSiteId(enclosingSite)
        cursorIcon = enclosingIcon
        cursorSite = iconsites.makeSeriesSiteId(name, idx + len(seriesIcons) - 1)
    else:
        rightIcOfLastElem, rightSiteOfLastElem = icon.rightmostSite(lastElem)
        # Set cursor assuming merge with right of expression, and correct later if not
        cursorIcon, cursorSite = rightIcOfLastElem, rightSiteOfLastElem
    mergeLeft = left is not None and firstElem is not None and \
        (atIcon.typeOf(atSite) =='input' or leftSiteIsEmpty(firstElem))
    mergeRight = right is not None and lastElem is not None and \
        (rightIcOfLastElem.typeOf(rightSiteOfLastElem) == 'input' or
         leftSiteIsEmpty(right))
    enclosingIcon.replaceChild(left, enclosingSite)
    if mergeLeft:
        # We merge at the highest coincident site to guarantee that it's in the left
        # tree (it doesn't matter that that's more-often the wrong place to merge, as
        # the expressions get arithmetically reordered).
        insertAtSite(coincAtIcon, coincAtSite, firstElem)
    leftIdx = 1 if mergeLeft or firstElem is None and left is not None else 0
    rightIdx = len(seriesIcons) - (1 if lastElem is None else 0)
    listInsertSite = enclosingSite if left is None else \
        iconsites.nextSeriesSiteId(enclosingSite)
    enclosingIcon.insertChildren(seriesIcons[leftIdx:rightIdx], listInsertSite)
    if mergeRight:
        insertAtSite(rightIcOfLastElem, rightSiteOfLastElem, right)
    else:
        seriesName, insertIdx = iconsites.splitSeriesSiteId(listInsertSite)
        if right is not None:
            rightInsertSite = iconsites.makeSeriesSiteId(seriesName,
                insertIdx + rightIdx - leftIdx)
            enclosingIcon.insertChild(right, rightInsertSite)
            cursorIcon, cursorSite = enclosingIcon, rightInsertSite
    if isinstance(enclosingIcon, listicons.TupleIcon) and \
            len(enclosingIcon.sites.argIcons) == 1:
        # If the initial culling of cases that do not create new elements is wrong, we
        # can create a single-element naked tuple or unnecessarily convert a paren to a
        # tuple.  Print a diagnostic to make sure this gets attention.
        print("May have created single-element naked tuple or single-element tuple from "
            "cursor paren")
    if cursorLeft:
        if leftIdx == 0:
            return enclosingIcon, listInsertSite
        return coincAtIcon, coincAtSite
    return cursorIcon, cursorSite

def joinStmts(firstStmt):
    """Attempt to join firstStmt and the statement following it into a single statement.
    On success, returns an appropriate icon and site for the cursor (with site of None
    indicating a text icon).  On failure, returns None, None."""
    # Note that when joining across series sites, uses list append rather than text-
    # editor conventions (adds an automatic comma), and places the cursor after the
    # inserted comma, allowing the user to delete if they actually wanted to merge
    nextStmt = firstStmt.nextInSeq()
    if nextStmt is None:
        return None, None
    if isStmtLevelOnly(nextStmt):
        return None, None
    rightmostIcon, rightmostSite = icon.rightmostSite(firstStmt)
    if rightmostIcon.isCursorOnlySite(rightmostSite):
        return None, None
    firstStmt.window.requestRedraw(firstStmt.hierRect())
    firstStmtComment = firstStmt.hasStmtComment()
    nextStmtComment = nextStmt.hasStmtComment()
    # Figure out if we're merging the first stmt into the second, or the second into
    # the first (and as a byproduct, whether to use list or non-list style insertion).
    # The only case where we merge the first into the second, is if the second is a
    # naked tuple and the first can be added to it or merged with its first element.
    firstStmtSeriesIc = firstStmtSeriesSite = None
    nextStmtNakedTuple = isinstance(nextStmt, listicons.TupleIcon) and nextStmt.noParens
    if iconsites.isSeriesSiteId(rightmostSite) or isinstance(rightmostIcon,
            parenicon.CursorParenIcon) and rightmostSite == 'argIcon':
        firstStmtSeriesIc = rightmostIcon
        firstStmtSeriesSite = rightmostSite
    elif rightmostSite == 'attrIcon':
        enclIcon, enclSite = entryicon.findEnclosingSite(rightmostIcon, rightmostSite)
        if enclIcon is None and not nextStmtNakedTuple or \
                enclIcon is not None and iconsites.isSeriesSiteId(enclSite):
            firstStmtSeriesIc = rightmostIcon
            firstStmtSeriesSite = rightmostSite
    # If we're merging the first statement into the second, do so and return
    if firstStmtSeriesIc is None and nextStmtNakedTuple and \
            not isStmtLevelOnly(firstStmt):
        if firstStmtComment:
            firstStmtComment.detachStmtComment()
        nextStmt.window.replaceTop(firstStmt, None)
        cursorIc, cursorSite = insertListAtSite(nextStmt, 'argIcons_0', [firstStmt])
        if nextStmtComment is not None:
            nextStmtComment.mergeTextFromComment(firstStmtComment, before=True)
        elif firstStmtComment is not None:
            firstStmtComment.attachStmtComment(nextStmt)
        return cursorIc, cursorSite
    # We're merging the second statement at the end of the first
    # Remove the second statement
    if nextStmtComment:
        nextStmtComment.detachStmtComment()
    firstStmt.window.removeTop(nextStmt)
    firstStmt.replaceChild(nextStmt.childAt('seqOut'), 'seqOut')
    nextStmt.replaceChild(None, 'seqIn')
    nextStmt.replaceChild(None, 'seqOut')
    # Add it to the right of the first statement, either by appending to its rightmost
    # site, or by extending a trailing series (whichever is the best fit).
    needReorder = []
    if nextStmtNakedTuple and firstStmtSeriesSite is not None:
        # The next statement is a naked tuple and the first statement can accept a
        # series.  Transfer the tuple's arguments to the first stmt's series.
        argIcons = nextStmt.argIcons()
        for _ in range(len(argIcons)):
            nextStmt.replaceChild(None, 'argIcons_0')
        cursorIc, cursorSite = insertListAtSite(firstStmtSeriesIc, firstStmtSeriesSite,
            argIcons, cursorLeft=True)
    elif firstStmtSeriesSite is not None and nextStmt.hasSite('output'):
        # If the first statement can accept a series and the next statement is compatible
        # with a series, let insertListAtSite decide what to do with it.
        cursorIc, cursorSite = insertListAtSite(firstStmtSeriesIc, firstStmtSeriesSite,
            [nextStmt], cursorLeft=True)
    else:
        # We've vetted the next statement to be adaptable, go ahead and append
        cursorIc, cursorSite = appendAtSite(rightmostIcon, rightmostSite, nextStmt,
            needReorder)
    mergedStmt = reorderMarkedExprs(firstStmt, needReorder, replaceTop=True)
    if mergedStmt is not firstStmt:
        if firstStmtComment is not None:
            firstStmtComment.detatchStmtComment()
            firstStmtComment.attachStmtComment(mergedStmt)
    # Merge the statement comments of the two statement
    if firstStmtComment is not None:
        firstStmtComment.mergeTextFromComment(nextStmtComment)
    elif nextStmtComment is not None:
        nextStmtComment.attachStmtComment(mergedStmt)
    return cursorIc, cursorSite

def joinWithPrev(bottomStmt):
    prevStmt = bottomStmt.prevInSeq()
    if prevStmt is None:
        return None, None
    return joinStmts(prevStmt)

def canSplitStmtAtSite(atIcon, atSite):
    if isLeftmostSite(atIcon, atSite):
        return "Split command at left edge of statement does nothing"
    rightmostIc, rightmostSite = icon.rightmostSite(atIcon.topLevelParent())
    if atIcon is rightmostIc and atSite == rightmostSite:
        return "Split command at right edge of statement does nothing"
    enclosingIcon, enclosingSite = entryicon.findEnclosingSite(atIcon, atSite)
    # Figure out if the enclosing icon ends in a series that reaches the rightmost edge
    # of the statement, such as naked tuples, unclosed parens/brackets/braces, and series
    # statements.
    if openOnRight(enclosingIcon, enclosingSite):
        return None
    return "Cannot split inside of enclosing context (such as parens, braces, or" \
        "constrained fields"

def splitStmtAtSite(atIcon, atSite):
    """Make two separate statements out of the statement containing atIcon by splitting
    it at site (atIcon, atSite) and splice them into the sequence containing atIcon
    replacing the top-level icon of the statement.  Call this ONLY after first verifying
    that canSplitStmtAtSite returns None for the site.  Returns the top icons of the
    resulting statements."""
    topParent = atIcon.topLevelParent()
    enclosingIcon, enclosingSite =  entryicon.findEnclosingSite(atIcon, atSite)
    if enclosingIcon is None:
        # Split to the top level
        left, right = entryicon.splitExprAtSite(atIcon, atSite, None)
        if left is not topParent:
            atIcon.window.replaceTop(topParent, left)
        icon.insertSeq(right, left)
        atIcon.window.addTop(right)
        return left, right
    if isinstance(enclosingIcon, parenicon.CursorParenIcon):
        # An unclosed cursor paren icon encloses the split site (which canSplitStmtAtSite
        # determined to be open to the right edge of the statement)
        left, right = entryicon.splitExprAtSite(atIcon, atSite, enclosingIcon)
        if right is None:
            return topParent, None  # Shouldn't happen if verified with canSplitStmtAtSite
        enclosingIcon.replaceChild(left, enclosingSite)
        icon.insertSeq(right, topParent)
        atIcon.window.addTop(right)
        return topParent, right
    # Split to enclosing icon (which canSplitStmtAtSite determined to be a series, open
    # to the right of the statement)
    if atIcon is enclosingIcon:
        seriesSplitSite = atSite
    else:
        seriesSplitSite = enclosingIcon.siteOf(atIcon, recursive=True)
    seriesName, splitIdx = iconsites.splitSeriesSiteId(seriesSplitSite)
    siteSeries = getattr(enclosingIcon.sites, seriesName)
    left, right = entryicon.splitExprAtSite(atIcon, atSite, enclosingIcon)
    iconsToMove = [site.att for site in siteSeries[splitIdx+1:]]
    if left is None:
        for _ in range(splitIdx, len(siteSeries)):
            enclosingIcon.replaceChild(None, seriesSplitSite)
    else:
        enclosingIcon.replaceChild(left, seriesSplitSite)
        for _ in range(splitIdx+1, len(siteSeries)):
            enclosingIcon.replaceChild(None, iconsites.nextSeriesSiteId(seriesSplitSite))
    if isinstance(enclosingIcon, listicons.TupleIcon) and \
            len(enclosingIcon.sites.argIcons) < 2:
        # If removing icons from series left a one-argument naked tuple or a one-argument
        # unclosed tuple, get rid of the tuple.  In the unusual case of a naked tuple
        # whose remaining element is empty, leave the tuple, as deleting everything
        # would both confuse the user and needlessly complicate the code.
        if enclosingIcon.noParens:
            argIcon = enclosingIcon.childAt('argIcons_0')
            if argIcon is None:
                enclosingIcon.replaceChild(None, 'argIcons_1', leavePlace=True)
            else:
                enclosingIcon.replaceChild(None, 'argIcons_0')
                atIcon.window.replaceTop(enclosingIcon, argIcon)
                topParent = argIcon
        else:
            newParen = entryicon.cvtTupleToCursorParen(enclosingIcon, closed=False,
                typeover=False)
            topParent = newParen.topLevelParent()
    if right is not None:
        iconsToMove.insert(0, right)
    if len(iconsToMove) == 0:
        return topParent, None  # Shouldn't happen if verified with canSplitStmtAtSite
    elif len(iconsToMove) == 1:
        icon.insertSeq(iconsToMove[0], topParent)
        atIcon.window.addTop(iconsToMove[0])
        return topParent, iconsToMove[0]
    else:
        newTuple = listicons.TupleIcon(window=atIcon.window, noParens=True)
        newTuple.insertChildren(iconsToMove, 'argIcons', 0)
        icon.insertSeq(newTuple, topParent)
        atIcon.window.addTop(newTuple)
        return topParent, newTuple

def lexicalTraverse(topNode, includeStmtComment=True):
    """Both cursors.py and reorderexpr.py have lexical traversal code.  This version
    simply visits icons in lexical (left to right, only) order, as opposed to the cursors
    version that traverses cursor sites and the reorderexpr version that produces tokens
    and avoids descending into subexpressions."""
    if topNode is None:
        yield None
    elif isinstance(topNode, (opicons.BinOpIcon, infixicon.InfixIcon)):
        # Body of icon is in the middle
        yield from lexicalTraverse(topNode.leftArg())
        yield topNode
        yield from lexicalTraverse(topNode.rightArg())
    elif isinstance(topNode, opicons.IfExpIcon):
        yield from lexicalTraverse(topNode.childAt('trueExpr'))
        yield topNode
        yield from lexicalTraverse(topNode.childAt('testExpr'))
        yield from lexicalTraverse(topNode.childAt('falseExpr'))
    else:
        yield topNode
        for siteOrSeries in topNode.sites.traverseLexical():
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                for site in siteOrSeries:
                    yield from lexicalTraverse(site.att)
            else:
                yield from lexicalTraverse(siteOrSeries.att)
    if includeStmtComment:
        stmtComment = topNode.hasStmtComment()
        if stmtComment:
            yield stmtComment

def splitDeletedIcons(ic, toDelete, assembleDeleted, needReorder, watchSubs=None):
    """Remove icons in set, toDelete, from ic and the icons below it in the hierarchy,
    and return a pair of results, the first representing the icons remaining in the tree
    and the second representing the icons removed from the tree (if assembleDeleted is
    True).  A value of None indicates that ic remains in the corresponding tree.  If not
    None, the value will be a placement-list (see icon.placeArgs) style list (possibly
    empty), representing the remaining icons that need to replace it in the corresponding
    tree.  If ic itself appears in toDelete, it will appear in the deleted icon placement
    list but will not be detached from its parent. The function calls itself recursively,
    creating a single tree (or placement list of trees) out of the remaining icons and
    (if requested via assembleDeleted), a single tree or list out of the deleted icons.
    If necessary, it inserts placeholder icons to retain icons that cannot otherwise be
    attached to incompatible sites.  In addition to the two trees, splitDeletedIcons
    returns a boolean value indicating whether it *also* moved ic.  While the premise of
    the function is that it rearranges only the trees *under* ic, unfortunately there are
    cases where ic has to move down the hierarchy (as a consequence of owning a list that
    needs to move up).  If the function moves ic, and ic is a top-level icon, it will
    also call removeTop() on it (which needs to be done first for undo to work properly),
    and main purpose of the returned boolean value is to inform the calling function that
    this has been done so it won't repeat the operation.  While the function will do the
    single-level reordering necessary to propagate lists upward in the hierarchy, it
    leaves  arithmetic reordering (which may involve multiple levels) to the caller.  The
    caller should provide a list in needReorder to receive a list of operators that
    should be checked for precedence inversions.  watchSubs can be set to None, or to a
    dictionary whose keys are icons for which the caller wants to be notified of
    substitutions (see removeIcons description for details)."""
    # Note that this code can be confusing to read, because rather than keep the deleted
    # and non-deleted trees separate, it immediately categorizes them into the tree that
    # will remain attached to ic (withIc) and the tree that will be detached from it
    # (splitFromIc).  This reduces duplication in the code but also adds an extra layer
    # of indirection.  Also, when reading the code, remember that a 'None' return from a
    # recursive call to splitDeletedIcons means that the icon was *not split* which is
    # easy to misconstrue as 'deleted'.
    icDeleted = ic in toDelete
    splitList = []
    argsDetached = False
    subsList = None
    removedTopIcon = False
    for siteOrSeries in ic.sites.traverseLexical():
        if isinstance(siteOrSeries, iconsites.IconSiteSeries):
            # Site series
            isCprhSeries = siteOrSeries.type == 'cprhIn'
            splitSeriesList = []
            for site in list(siteOrSeries):
                if site.att is None:
                    # Empty sites are considered an attribute of the icon (as we can't
                    # delete the absence of something), so stay with it, deleted or not.
                    continue
                if icDeleted:
                    splitFromIc, withIc, _ = splitDeletedIcons(site.att, toDelete,
                        assembleDeleted, needReorder, watchSubs)
                else:
                    withIc, splitFromIc, _ = splitDeletedIcons(site.att, toDelete,
                        assembleDeleted, needReorder, watchSubs)
                if assembleDeleted or icDeleted:
                    if splitFromIc is None:
                        splitSeriesList.append([site.att])
                    elif len(splitFromIc) > 0:
                        splitSeriesList.append(splitFromIc)
                if withIc is not None:
                    # The attached icon needs to be removed (withIc will be None if the
                    # argument was unchanged but a (potentially empty) place-list if
                    # there are icons to reintegrate).  If there is a replacement list,
                    # reduce it to a series and splice it in to the series site.  The
                    # code uses the fact that sites are renamed on insert and delete, to
                    # get the current series index regardless of prior insertions and
                    # deletions.  That is, unless this is either a comprehension site,
                    # or the first item to place is itself a comprehension.  Cprh sites
                    # are series sites on icons, but are individuals in a place-list.
                    argsDetached = True
                    if isCprhSeries:
                        replaceCprhArgWithPlaceList(ic, site.name, withIc)
                    elif len(withIc) > 0 and isinstance(ic, (listicons.TupleIcon,
                            listicons.ListIcon,  listicons.DictIcon)) and \
                            siteOrSeries.name == 'argIcons' and \
                            len(ic.sites.argIcons) <= 1 and (isinstance(withIc[0],
                            (listicons.CprhForIcon, listicons.CprhIfIcon)) or
                            listicons.canPlaceCprhArgsFromEntry(None, withIc,
                            'argIcons_0', True)):
                        replaceCprhArgWithPlaceList(ic, 'argIcons_0', withIc)
                    else:
                        seriesIcons = placeListToSeries(withIc)
                        if len(seriesIcons) == 0:
                            ic.replaceChild(None, site.name)
                        else:
                            ic.replaceChild(seriesIcons[0], site.name)
                            name, idx = iconsites.splitSeriesSiteId(site.name)
                            ic.insertChildren(seriesIcons[1:], name, idx+1)
            if assembleDeleted or icDeleted:
                # splitList contains a list of placelists from each of the sites of the
                # series.  In the comprehension case, these go directly in to splitList,
                # but in the normal series case we integrate them as (comma separated)
                # series (provided there are more than one).
                if isCprhSeries:
                    for p in splitSeriesList:
                        appendToPlaceList(splitList, p, needReorder)
                else:
                    if len(splitSeriesList) == 1:
                        appendToPlaceList(splitList, splitSeriesList[0], needReorder)
                    elif len(splitSeriesList) > 1:
                        for p in splitSeriesList:
                            appendToPlaceList(splitList, [placeListToSeries(p)],
                                needReorder)
        elif siteOrSeries.att is not None:
            # Individual site
            if icDeleted:
                splitFromIc, withIc, _ = splitDeletedIcons(siteOrSeries.att, toDelete,
                    assembleDeleted, needReorder, watchSubs)
            else:
                withIc, splitFromIc, _ = splitDeletedIcons(siteOrSeries.att, toDelete,
                    assembleDeleted, needReorder, watchSubs)
            if assembleDeleted or icDeleted:
                if splitFromIc is None:
                    appendToPlaceList(splitList, [siteOrSeries.att], needReorder)
                elif len(splitFromIc) > 0:
                    appendToPlaceList(splitList, splitFromIc, needReorder)
            if withIc is not None:
                # Deletion resulted in a placement list (though it may be empty).  If it
                # can be reduced to a single icon, replace the existing attached icon
                # with it.  If placeList contains a single series and we're trying to put
                # it on ic's rightmost site, move ic into the series and punt the the
                # place list up to the next level in the hope that somewhere above us is
                # a series it can be merged into.
                argsDetached = True
                subsList = placeOnSingleSite(ic, siteOrSeries, withIc, subsList,
                    needReorder, watchSubs)
                removedTopIcon = isinstance(subsList, (list, tuple))
    if subsList is None and isinstance(ic, entryicon.EntryIcon):
        if argsDetached:
            ic.pruneEmptyPendingArgSites()
        if ic.text == '':
            # The icon is a placeholder entry icon.  If the there's just one pending
            # argument and it's compatible with the site: get rid of the placeholder.
            pendingArgs = ic.listPendingArgs()
            nonEmptyArgs = [ic for ic, _, _ in icon.placementListIter(pendingArgs,
                includeEmptySeriesSites=False)]
            if len(nonEmptyArgs) == 0:
                # Everything has been stripped off of placeholder icon, get rid of it
                subsList = []
            elif len(nonEmptyArgs) == 1 and ic.attachedIcon() is not None and \
                    iconsites.matingSiteType[ic.attachedSiteType()] in \
                    (s.type for s in nonEmptyArgs[0].sites.parentSites()):
                # Entry icon has a single pending arg that's compatible with parent site.
                # remove the entry icon.  (Note that this is stupidly testing against the
                # original parent.  Testing the new parent is more complicated, so we do
                # this and let the parent iteration recreate the placeholder if we're
                # wrong.  This will also miss some opportunities for cleanup, though, in
                # practice I haven't found any cases not handled by other placeholder-
                # trimming code)
                ic.popPendingArgs('all')
                subsList = [nonEmptyArgs[0]]
    # If ic is a naked tuple, deletion of its content could leave it empty or owning a
    # single element.  If so, remove it.
    if subsList is None and isinstance(ic, listicons.TupleIcon) and ic.noParens and \
            len(ic.sites.argIcons) == 1:
        argIcon = ic.childAt('argIcons_0')
        if argIcon is None:
            subsList = []
        else:
            ic.replaceChild(None, 'argIcons_0')
            subsList = [argIcon]
    if icDeleted:
        return splitList, subsList, removedTopIcon
    else:
        return subsList, splitList, removedTopIcon

def placeListToTopLevelIcon(placeList, forSequence, watchSubs=None):
    """Create an icon tree from a placement-list-format list of icons (placeList).
    Specify forSequence if the icon will need to be part of a sequence (for which icons
    that attach only to attribute and comprehension sites need a placeholder icon to
    adapt).  Note that this can return a block-owning icon if the placelist contains a
    single comprehension clause, because we return the corresponding for/if stmt.
    watchSubs can be set to a dictionary of icons for whom callers need a record of icon
    substitutions (see window.removeIcons)."""
    if len(placeList) == 0:
        return None
    numInputs = 0
    for entry in placeList:
        if isinstance(entry, list):
            numInputs += len(entry)
        elif entry.hasSiteType('output'):
            numInputs += 1
    firstIc = placeList[0]
    if numInputs <= len(placeList)//2 and not isinstance(firstIc, (list, tuple)):
        # Less than half of the place list entries have output sites, so use an entry
        # icon to join them, rather than a list.  If the first item in placeList
        # needs an entry icon, just put the whole place list in that, but if it
        # doesn't, create the first element without and hang an entry icon with the
        # remaining elements off of the rightmost icon of the first.
        if isinstance(firstIc, entryicon.EntryIcon):
            # Not sure if any of our callers will do this, but it's easy to handle
            firstIc.appendPendingArgs(placeList)
            return firstIc
        # We really shouldn't be doing substitution, here, as it complicates everything.
        # Unfortunately, our caller may be assembling a sequence and our only alternatives
        # are to hand it a comprehension, or a comprehension embedded in an entry icon.
        if isinstance(firstIc, (listicons.CprhForIcon, listicons.CprhIfIcon)):
            subsIc = listicons.subsCanonicalInterchangeIcon(firstIc)
            if subsIc is not None:
                window = firstIc.window
                if watchSubs is not None and firstIc in watchSubs:
                    watchSubs[firstIc] = subsIc
                firstIc = subsIc
        if not forSequence or firstIc.hasSiteType('output') or \
                firstIc.hasSiteType('seqIn'):
            # The first element of placeList can stand alone: hang the remaining
            # elements off of it with an entry icon
            if len(placeList) == 1:
                return firstIc  # Don't need an entry icon (no entries to add)
            rightmostIc, rightmostSite = icon.rightmostSite(firstIc)
            entryIc = entryicon.EntryIcon(window=firstIc.window)
            entryIc.appendPendingArgs(placeList[1:])
            entryIc.selectIfFirstArgSelected()
            rightmostIc.replaceChild(entryIc, rightmostSite)
            return firstIc
        else:
            # The first element of placeList requires an entry icon: make one big
            # entry icon
            entryIc = entryicon.EntryIcon(window=firstIc.window)
            entryIc.appendPendingArgs(placeList)
            entryIc.selectIfFirstArgSelected()
            return entryIc
    # Use placeListToSeries, to transform the list.  This is reasonable even for single
    # icons, since placement lists are not allowed to contain statement-level icons, and
    # anything else that needs a placeholder icon to be part of a series, also needs one
    # to be part of a sequence.
    seriesIcons = placeListToSeries(placeList)
    if len(seriesIcons) == 0:
        return None
    elif len(seriesIcons) == 1:
        return seriesIcons[0]
    firstIcon, _, _ = icon.firstPlaceListIcon(placeList)
    if firstIcon is None:
        return None
    topIcon = listicons.TupleIcon(window=firstIcon.window, noParens=True)
    topIcon.insertChildren(seriesIcons, 'argIcons', 0)
    topIcon.rect = icon.moveRect(topIcon.rect, firstIcon.rect[:2])
    return topIcon

def placeListToSeries(placeList):
    """Convert the place list to a list of icons to be represented as a series (while
    we do have the concept of a series of comprehension sites, this call returns only
    the normal input-site series type)."""
    seriesIcons = []
    for entry in placeList:
        if isinstance(entry, (list, tuple)):
            # Series are expected to be inputs, add entire series
            seriesIcons += entry
        elif isinstance(entry, entryicon.EntryIcon) and entry.text == '':
            # entry is an entry icon.  If it's all inputs, it can be dropped, and if
            # it's not, it's still a valid series member.
            pendingArgs = entry.listPendingArgs()
            nonEmptyArgs = [ic for ic, _, _ in icon.placementListIter(pendingArgs,
                includeEmptySeriesSites=False)]
            if len(nonEmptyArgs) == 0:
                continue
            for ic in nonEmptyArgs:
                if 'output' not in (s.name for s in ic.sites.parentSites()):
                    seriesIcons.append(entry)
                    break
            else:
                entry.popPendingArgs('all')
                seriesIcons += nonEmptyArgs
        elif entry is None or 'output' in (s.name for s in entry.sites.parentSites()):
            # entry is icon that is compatible with an input
            seriesIcons.append(entry)
        else:
            # entry is icon that is not compatible with an input site.  Since the
            # deletion process merges icons into the placement list as it adds them, we
            # know all possible merging is already done, and all we can do is create a
            # placeholder icon.  The one exception is that we may have converted the
            # prior icon to a placeholder (or it may already have been), in which case,
            # we can just add the icon to the prior one's pending args.
            if len(seriesIcons) > 0 and seriesIcons[-1] is not None and \
                    isinstance(seriesIcons[-1], entryicon.EntryIcon):
                entryIc = seriesIcons[-1]
            else:
                entryIc = entryicon.EntryIcon(window=entry.window)
                seriesIcons.append(entryIc)
                if entry.isSelected():
                    entryIc.select(True)
            entryIc.appendPendingArgs([entry])
    return seriesIcons

def placeOnSingleSite(toIcon, toSite, placeList, subsPlaceList, needReorder, watchSubs):
    """Attempt to attach the icons in placeList to site toSite on icon toIcon.  If
    placeList contains a single series, and the caller has some hope of merging the
    the series with one higher up, attach the first element of the series to toSite, and
    return a version of placeList with toIcon spliced in.  Alternatively, if toIcon is a
    paren icon, a series can be placed on it by substituting it with a tuple icon.  If
    neither such swaps were done, returns None.  If toIcon is already being substituted
    with a place list (presumably by this function), the caller should pass it in
    subsPlaceList, so that if a series is encountered in another argument of toIcon
    (usually the left and right arguments of a binary operator), the function can return
    a combined placement list.  needReorder and watchSubs are passed down from
    splitDeletedIcons and window.removeIcons (see descriptions) to notify the caller of
    expressions  needing reorder and icons that have been substituted."""
    # splitDeletedIcons was originally only allowed to act on the arguments of the icon
    # it was splitting.  Unfortunately, I didn't realize until long after designing it,
    # that it would need to move lists upward in the hierarchy.  To do this, we allow
    # splitDeletedIcons to produce a placement list for an icon that's not being deleted,
    # which adds all kinds of complexity because we now have to remove that icon from the
    # top level (since that always needs to be done first for undo), and tell the caller
    # about it, and be prepared to operate on an icon that has been substituted with a
    # placement list (for example, removing both brackets from '[a,b]*[c,d]').
    firstIc = None
    secondIc = None
    for ic, _, _ in icon.placementListIter(placeList, includeEmptySeriesSites=False):
        if firstIc is None:
            firstIc = ic
        else:
            secondIc = ic
            break
    if firstIc is None:
        # placeList contains no icons needing placement
        toIcon.replaceChild(None, toSite.name)
        return subsPlaceList
    # If the destination icon is a cursor-paren, it may be possible to convert it to a
    # tuple for the purpose of placing a multi-element list or one or more comprehension
    # clauses.
    if isinstance(toIcon, parenicon.CursorParenIcon) and toSite.name == 'argIcon' and \
            not subsPlaceList:
        cvtToTuple = False
        insertArgs = None
        insertCprhs = None
        if secondIc is not None and len(placeList) == 1 and isinstance(placeList[0],
                (list, tuple)) and len(placeList[0]) > 1:
            # placeList contains a multi-element list: convert to tuple
            cvtToTuple = True
            insertArgs = placeList[0]
        elif isinstance(placeList[0], (listicons.CprhForIcon, listicons.CprhIfIcon)):
            # placeList starts with a comprehension clause.  If that's all it contains,
            # then convert to tuple
            cprhIcons = [ic for ic in placeList if isinstance(ic, (listicons.CprhForIcon,
                listicons.CprhIfIcon))]
            if len(cprhIcons) == len(placeList):
                cvtToTuple = True
                insertCprhs = cprhIcons
        elif len(placeList) == 1 and listicons.canPlaceCprhArgsFromEntry(None, placeList,
                'argIcons_0', True):
            # placeList contains either a single placeholder entry icon containing
            # comprehension clauses, or a single expression with a placeholder entry icon
            # on its right that contains them: convert to tuple
            cvtToTuple = True
            placeList = listicons.promoteCprhArgsFromEntry(placeList, True)
            if isinstance(placeList[0], (listicons.CprhForIcon, listicons.CprhIfIcon)):
                insertCprhs = placeList
            else:
                insertArgs = placeList[:1]
                insertCprhs = placeList[1:]
        if cvtToTuple:
            # We can convert to a tuple.  Note, however, that we're not actually doing
            # the replacement, just returning the new tuple for splitDeletedIcons to
            # process as the replacement for toIcon.
            newTuple = listicons.TupleIcon(window=toIcon.window)
            parent = toIcon.parent()
            if parent is not None:
                parent.replaceChild(None, parent.siteOf(toIcon))
            elif toIcon in toIcon.window.topIcons:
                toIcon.window.removeTop(toIcon)
            if insertArgs is not None:
                newTuple.insertChildren(insertArgs, 'argIcons_0')
            if insertCprhs is not None:
                newTuple.insertChildren(insertCprhs, 'cprhIcons_0')
            filefmt.moveIconToPos(newTuple, toIcon.pos())
            attr = toIcon.childAt('attrIcon') if toIcon.closed else None
            if attr:
                toIcon.replaceChild(None, 'attrIcon')
                newTuple.replaceChild(attr, 'attrIcon')
            toIcon.replaceChild(None, toSite.name)
            if watchSubs is not None and toIcon in watchSubs:
                watchSubs[toIcon] = newTuple
            cursor = toIcon.window.cursor
            if cursor.type == 'icon' and cursor.icon is toIcon:
                cursor.icon = newTuple
                if cursor.site == 'argIcon':
                    cursor.site = 'argIcons_0'
            return [newTuple]
    if secondIc is None:
        requiredParentSiteType = iconsites.matingSiteType[toSite.type]
        if requiredParentSiteType in (s.type for s in firstIc.sites.parentSites()):
            # There is only a single icon in placeList and it's a compatible type
            checkReorder(firstIc, needReorder)
            toIcon.replaceChild(firstIc, toSite.name)
            return subsPlaceList
    # if placeList contains a multi-element list, try to merge toIcon into placeList (see
    # function description) and return the modified list
    if len(placeList) == 1 and isinstance(placeList[0], (list, tuple)) and \
            len(placeList[0]) > 1 and toSite.type == 'input':
        parent = toIcon.parent()
        if toSite is toIcon.sites.nthCursorSite(-1):
            if subsPlaceList is None:
                if parent is not None:
                    parent.replaceChild(None, parent.siteOf(toIcon))
                elif toIcon in toIcon.window.topIcons:
                    toIcon.window.removeTop(toIcon)
                toIcon.replaceChild(placeList[0][0], toSite.name)
                checkReorder(toIcon, needReorder)
                placeList[0][0] = toIcon
                return placeList
            elif len(subsPlaceList) == 1 and isinstance(subsPlaceList[0],
                    (list, tuple)) and len(subsPlaceList[0]) > 0 and \
                    subsPlaceList[0][-1] is toIcon:
                # The icon is already being substituted out for a multi-element list
                # with toIcon as the last element.  Merge the two lists by attaching the
                # first element of the new place list (placeList) to the designated site
                # on toIcon (now at the end of subsPlaceList), and adding the remaining
                # elements from placeList after toIcon in subsPlaceList.
                toIcon.replaceChild(placeList[0][0], toSite.name)
                subsPlaceList[0] += placeList[0][1:]
                return subsPlaceList
        if toIcon.hasCoincidentSite() == toSite.name:
            if parent is not None:
                parent.replaceChild(None, parent.siteOf(toIcon))
            elif toIcon in toIcon.window.topIcons:
                toIcon.window.removeTop(toIcon)
            toIcon.replaceChild(placeList[0][-1], toSite.name)
            checkReorder(toIcon, needReorder)
            placeList[0][-1] = toIcon
            return placeList
    # The list is not compatible, create an entry icon
    entryIc = entryicon.EntryIcon(window=firstIc.window)
    entryIc.appendPendingArgs(placeList)
    entryIc.selectIfFirstArgSelected()
    toIcon.replaceChild(entryIc, toSite.name)
    return subsPlaceList

def appendToPlaceList(placeList, toAdd, needReorder):
    """Lexically merge a placement list, toAdd, to the end of an existing one, placeList,
    assuming that all of the intervening icons have been removed.  This is used for
    reconstructing an icon hierarchy following deletion, with the end goal of creating
    either a tree with a single icon at the root, or a series that can be merged in to a
    parent series or become a naked tuple at the top level.  Since reducing the list to a
    single icon or a series the goal, the call tries to merge everything that can be
    merged.  In particular, it tries to eliminate loose attributes and empty sites on
    the left or right of an operator.  The caller needs to supply a list (needReorder) to
    receive icons to be reexamined after reassembly for arithmetic reordering based on
    precedence."""
    if len(toAdd) == 0:
        return
    if len(placeList) == 0:
        placeList += toAdd
        return
    if isinstance(placeList[-1], (listicons.CprhForIcon, listicons.CprhIfIcon)) and \
            isinstance(toAdd[0], (listicons.CprhForIcon, listicons.CprhIfIcon)):
        placeList += toAdd  # lists of cprh icons become individuals in place lists
        return
    placeListEndsWithList = isinstance(placeList[-1], (list, tuple))
    toAddStartsWithList = isinstance(toAdd[0], (list, tuple))
    if placeListEndsWithList and toAddStartsWithList:
        # Both the end of placeList and the start of toAdd are series.  Just join them
        placeList[-1] += toAdd[0]
        placeList += toAdd[1:]
        return
    if placeListEndsWithList:
        lastPlaceListIc = placeList[-1][-1]
    else:
        lastPlaceListIc = placeList[-1]
    rightmostIc, rightmostSiteId = icon.rightmostSite(lastPlaceListIc)
    firstToAddIc = toAdd[0][0] if isinstance(toAdd[0], (list, tuple)) else toAdd[0]
    if not rightmostIc.isCursorOnlySite(rightmostSiteId):
        matingType = iconsites.matingSiteType[rightmostIc.typeOf(rightmostSiteId)]
    else:
        matingType = None
    if isinstance(firstToAddIc, entryicon.EntryIcon) or matingType in \
            [s.type for s in firstToAddIc.sites.parentSites()]:
        # We can attach the left icon from toAdd to the right icon from placeList
        rightmostIc.replaceChild(firstToAddIc, rightmostSiteId)
        checkReorder(rightmostIc, needReorder)
        if toAddStartsWithList:
            toAdd[0] = placeList[-1]
            placeList[-1] = toAdd[0]
            placeList += toAdd[1:]
        else:
            placeList += toAdd[1:]
        return
    firstIcCoincSite = firstToAddIc.hasCoincidentSite()
    if firstIcCoincSite and \
            not firstToAddIc.childAt(firstToAddIc.sites.firstCursorSite()) and \
            icon.validateCompatibleChild(lastPlaceListIc, firstToAddIc, firstIcCoincSite):
        # There's an empty site on the left of the left icon added, combine
        firstToAddIc.replaceChild(lastPlaceListIc, firstIcCoincSite)
        checkReorder(firstToAddIc, needReorder)
        if placeListEndsWithList:  # and toAdd does not start with list, per above
            return
        placeList[-1] = toAdd[0]
        placeList += toAdd[1:]
        return
    else:
        # This function is tailored to the needs of removeIcons, which builds place lists
        # outside-in, and, with the exception of input series, cannot ever re-unify a
        # multi-item place-list.  If we just blindly tack additional items on to the
        # the list, we'll just end up putting more icons in some future entry icon's
        # pending args, so as long as the place list is not already multi-element, make
        # the entry icon, here and add it to the rightmost icon in placeList.
        if len(placeList) > 1:
            placeList += toAdd
        else:
            rightmostEntry = placeList[0][-1] if isinstance(placeList[0], (list, tuple)) \
                else placeList[0]
            rightmostIc, rightmostSite = icon.rightmostSite(rightmostEntry)
            for ic in rightmostIc.parentage(includeSelf=True):
                if isinstance(ic, entryicon.EntryIcon):
                    # There's already an entry icon, here.  Add to that, instead
                    ic.appendPendingArgs(toAdd)
                    break
            else:
                entryIc = entryicon.EntryIcon(window=rightmostIc.window)
                entryIc.appendPendingArgs(toAdd)
                entryIc.selectIfFirstArgSelected()
                rightmostIc.replaceChild(entryIc, rightmostSite)

def replaceCprhArgWithPlaceList(ic, siteName, placeList):
    """Remove  icon currently attached to siteName (which must be a cprhIn site or
    argIcons_0), and insert the icon(s) in placeList in its place.  This may place
    non-cprh icons (adapted if necessary with a placeholder entry icon) on whatever is
    occupying the previous site, which might be either the previous comprehension clause
    or the comprehension expression (if siteName is the leftmost cprh clause).  It may
    also add or remove sites from the cprhIcons series.  Note that because this may need
    to place icons on the previous site, it requires that the previous site be already
    fully assembled and accessible from ic with the expected site name (and, of course,
    by extension, this call must be invoked left-to-right)."""
    if len(placeList) == 0:
        ic.replaceChild(None, siteName)
        return
    placeIdx, placeSeriesIdx = ic.canPlaceArgs(placeList, siteName, overwriteStart=True)
    canPlace = False
    placeOnPrev = None
    placeOnSelf = None
    if placeIdx is None:
        # No arguments can be placed
        placeOnPrev = placeList
    elif icon.placeListAtEnd(placeList, placeIdx, placeSeriesIdx):
        # All arguments can be placed
        canPlace = True
    elif icon.placeListEmpty(placeList, placeIdx, placeSeriesIdx):
        # The only args that could be placed were empty
        placeOnPrev = placeList
    elif placeIdx != len(placeList) - 1:
        # The site can be successfully replaced, but args remain
        canPlace = True
        placeOnSelf = placeList[placeIdx:]
    if canPlace:
        ic.placeArgs(placeList, siteName, overwriteStart=True)
    else:
        ic.replaceChild(None, siteName)
    seriesName, idx = iconsites.splitSeriesSiteId(siteName)
    if placeOnPrev is not None:
        if idx == 0:
            # Place the icons on the comprehension expression
            placeSite = ic.sites.argIcons[0].name
        else:
            # Place the icons on the previous comprehension clause.  Note that we don't
            # expect an empty comprehension site.  If there is one, we risk putting an
            # entry icon there, which the entry icon doesn't support.
            placeSite = iconsites.makeSeriesSiteId(seriesName, idx-1)
            if ic.childAt(placeSite) is None:
                print("Unexpected empty cprh site can't support entry icon")
        placeAtEndOfArg(ic, placeSite, placeOnPrev)
    if placeOnSelf is not None:
        placeSite = iconsites.makeSeriesSiteId(seriesName, idx + placeIdx)
        placeAtEndOfArg(ic, placeSite, placeOnSelf)

def placeAtEndOfArg(ic, siteName, placeList):
    """Place all of the icons in placeList after the icons attached to site, siteName, on
    icon, ic.  If they need adaptation to make them fit, add an entry icon in between."""
    siteTopIc = ic.childAt(siteName)
    if siteTopIc is None:
        placeOnIc = ic
        placeOnSite = siteName
    else:
        placeOnIc, placeOnSite = icon.rightmostSite(siteTopIc)
    prevPlaceIdx, prevPlaceSeriesIdx = placeOnIc.canPlaceArgs(placeList,
        placeOnSite, overwriteStart=False)
    if icon.placeListAtEnd(placeList, prevPlaceIdx, prevPlaceSeriesIdx):
        # All arguments can be placed
        placeOnIc.placeArgs(placeList, placeOnSite, overwriteStart=False)
    else:
        # Not all arguments can be placed, create an entry icon to adapt
        entryIc = entryicon.EntryIcon(window=ic.window)
        entryIc.appendPendingArgs(placeList)
        entryIc.selectIfFirstArgSelected()
        placeOnIc.replaceChild(entryIc, placeOnSite)

def checkReorder(ic, needReorder):
    """Deletion from expressions is done lexically, but the deletion operation itself is
    done blindly on the icon hierarchy, so when a deletion operation reorders an
    expression, it calls this to mark potentially affected icons to recheck the
    precedence relationships to see if the new lexical order needs to cause rearrangement
    of the hierarchy.  It marks them by adding the potentially affected icons to the list,
    needReorder."""
    if isinstance(ic, (opicons.UnaryOpIcon, opicons.BinOpIcon, opicons.IfExpIcon,
            infixicon.InfixIcon)):
        needReorder.append(ic)

def reorderMarkedExprs(topIcon, exprsNeedingReorder, replaceTop=False):
    """Reorder the hierarchy of arithmetic expressions below topIcon, whose relative
    precedences may have changed due to deletion of the icons around them.  The deletion
    code marks expressions that need to be checked by adding icons to the list passed as
    exprsNeedReorder.  The function reorders the icon hierarchy to match what it looks
    like (lexically), rather than what the hierarchy itself implies.  Even though the
    deletion code restarts this list for every top icon involved in deletion, we do a
    second check that the icon is within the hierarchy of topIcon.  This is done beaause
    the same routine is used for processing both the remaining icons in the expression
    and the new tree of deleted icons that is (optionally) assembled by removeIcons.
    Returns the (possibly replaced) top top icon of the statement. if replaceTop is
    set to True, will perform a window.replaceTop operation if a new icon became top."""
    reorderExprTops = set()
    for ic in exprsNeedingReorder:
        if ic.topLevelParent() == topIcon:
            reorderExprTops.add(reorderexpr.highestAffectedExpr(ic))
    modifiedTopIcon = topIcon
    for ic in reorderExprTops:
        newTopIc = reorderexpr.reorderArithExpr(ic, skipReplaceTop=True)
        if ic is topIcon and newTopIc is not ic:
            modifiedTopIcon = newTopIc
    if replaceTop and modifiedTopIcon is not topIcon:
        topIcon.window.replaceTop(topIcon, modifiedTopIcon)
    return modifiedTopIcon

def openOnRight(enclosingIcon, enclosingSite):
    """Return true if (enclosingIcon, enclosingSite) is a a series or cursor-paren site
    of an icon that is not closed at the right and touches the right edge of the top-
    level statement to which it belongs.  Meaning, that it could be split around by
    truncating the list at enclosingSite and inserting even a statement-level icon.
    Also returns True if enclosingIcon is None, since we assume enclosingIcon and
    enclosingSite come from findEnclosingSite, which will return None when there is
    nothing bounding the expression holding the given site."""
    if enclosingIcon is None:
        return True
    if isinstance(enclosingIcon, parenicon.CursorParenIcon) and \
            enclosingSite == 'argIcon' and not enclosingIcon.closed:
        lastSeriesSite = 'argIcon'
    else:
        if not iconsites.isSeriesSiteId(enclosingSite):
            return False
        seriesName, _ = iconsites.splitSeriesSiteId(enclosingSite)
        siteSeries = getattr(enclosingIcon.sites, seriesName)
        lastSeriesSite = siteSeries[-1].name
    rightmostIc, rightmostSite = icon.rightmostSite(enclosingIcon.topLevelParent())
    lastIc, lastSite = icon.rightmostFromSite(enclosingIcon, lastSeriesSite)
    return rightmostIc is lastIc and rightmostSite == lastSite

def isStmtLevelOnly(ic):
    for site in ic.sites.allSites(expandSeries=False):
        if site.type in iconsites.parentSiteTypes:
            return False
    return True

def isLeftmostSite(ic, site, withinIc=None):
    """Return True if ic and site are (one of several sites) coincident with the left
    edge of the statement containing ic.  To determine whether (ic, site) is leftmost
    within a given subtree, specify a bounding icon io withinIc.  Note that this function
    is focused on expressions and does not consider sequence sites to be 'leftmost', so
    to include sequence sites, you'll have to detect them separately."""
    # In reading this code, remember that 'site' is the site of ic that we're evaluating,
    # as opposed to the ic's site in its parent (as often seen in similar code).
    parent = ic.parent()
    if parent is None and site == 'output':
        return True
    while True:
        coincSite = ic.hasCoincidentSite()
        if coincSite is None or coincSite != site:
            return False
        if parent is withinIc:
            return True
        site = parent.siteOf(ic)
        ic = parent
        parent = ic.parent()

def leftSiteIsEmpty(ic):
    """Return True if the left most site of the tree under ic is an empty input site
    (which will be an input site as that is the only type of site that can be on the
    left of an icon)."""
    leftSite = ic.hasCoincidentSite()
    if leftSite is not None:
        leftIc, leftSite = iconsites.lowestCoincidentSite(ic, leftSite)
        if leftIc.childAt(leftSite) is None:
            return True
    return False

def rightSiteIsEmptyInput(ic):
    rightmostIc, rightmostSite = icon.rightmostSite(ic)
    return rightmostIc.typeOf(rightmostSite) == 'input'

def isRightmostSite(ic, site):
    rightmostIc, rightmostSite = icon.rightmostSite(ic.topLevelParent())
    return rightmostIc is ic and rightmostSite == site

def lowestLeftSite(ic):
    """If ic has a site on the left, return icon with the lowest coincident site, there,
    and its corresponding site.  If not, returns None, None."""
    leftSite = ic.hasCoincidentSite()
    if leftSite is not None:
        return iconsites.lowestCoincidentSite(ic, leftSite)
    return None, None

def cursorLeftOfIcon(ic):
    """Returns a cursor icon and site to the left of ic (which may be an output site,
    if ic has no parent).  A site name of None indicates a text icon site."""
    parent = ic.parent()
    if parent is None:
        if ic.hasSite('output'):
            return ic, 'output'
        return ic, 'seqIn'
    site = parent.siteOf(ic)
    if parent.typeOf(site) == 'cprhIn':
        return listicons.proxyForCprhSite(parent, site)
    # If the cursor would follow an entry icon, put the cursor in that, instead
    coincIcon, coincSite = iconsites.highestCoincidentSite(parent, site)
    if isinstance(coincIcon.parent(), entryicon.EntryIcon):
        return coincIcon.parent(), None
    return parent, site
