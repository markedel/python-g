import icon
import iconsites
import listicons
import entryicon
import parenicon
import opicons
import assignicons
import infixicon
import commenticon
import reorderexpr
import filefmt
import cursors
import blockicons

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
    if topInsertedIcon is None:
        return atIcon, atSite
    insRightIc, insRightSite = icon.rightmostSite(topInsertedIcon)
    # We accept output sites At the top level, since the cursor can be attached to them.
    if atIcon.typeOf(atSite) in iconsites.parentSiteTypes:
        parent = atIcon.parent()
        if parent is not None:
            # We hope not to see cursors on output sites that are not on the top level,
            # but they can't be ruled out.  In this case, use the parent site instead.
            atSite = parent.siteOf(atIcon)
            atIcon = parent
        elif isinstance(atIcon, commenticon.CommentIcon) and atSite == 'prefixInsert':
            # Line comments have a special (cursor-only output) site for inserting code
            # to the left of them in text-editor-style to convert them to a stmt comment
            atIcon.window.replaceTop(atIcon, topInsertedIcon)
            atIcon.attachStmtComment(topInsertedIcon)
            return insRightIc, insRightSite
        else:
            # Reverse the insertion, replacing the tree holding the insert point with
            # the tree being inserted before it.  insertAtSite does not do statement
            # comment transfer itself, but it is expected to preserve the comment on the
            # top-level statement on which it is inserting (normally happens implicitly
            # via our calls to replaceTop, but must be done explicitly, here).
            stmtComment = atIcon.hasStmtComment()
            atIcon.window.replaceTop(atIcon, topInsertedIcon, transferStmtComment=False)
            rightIcOfIns, rightSiteOfIns = icon.rightmostSite(topInsertedIcon)
            cursorIc, cursorSite = insertAtSite(rightIcOfIns, rightSiteOfIns, atIcon,
                cursorLeft=True)
            if stmtComment is not None:
                stmtComment.attachStmtComment(cursorIc.topLevelParent())
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
    topParent = atIcon.topLevelParent()
    rightmostIc, rightmostSite = icon.rightmostSite(topParent)
    if isStmtLevelOnly(topInsertedIcon):
        # Assignment icons are statement-level, but also have an input site on the right,
        # which allows them to be appended to icons with an output.  They can also be
        # inserted within other assignment statements
        if atIcon is rightmostIc and atSite == rightmostSite and \
                topParent.hasSite('output') and \
                (isinstance(topInsertedIcon, assignicons.AssignIcon) or
                 isinstance(topInsertedIcon, assignicons.AugmentedAssignIcon) and
                    leftSiteIsEmpty(topInsertedIcon)):
            # Appending an assignment statement to a top-level icon with an output site
            if isinstance(topParent, listicons.TupleIcon) and topParent.noParens and \
                    not isinstance(topInsertedIcon, assignicons.AugmentedAssignIcon):
                insIcons = topParent.argIcons()
                for _ in insIcons:
                    topParent.replaceChild(None, 'argIcons_0')
            else:
                insIcons = (topParent,)
            topParent.window.replaceTop(topParent, topInsertedIcon)
            if leftSiteIsEmpty(topInsertedIcon) and len(insIcons) == 1:
                insIc, insSite = lowestLeftSite(topInsertedIcon)
                insIc.replaceChild(topParent, insSite)
            else:
                topInsertedIcon.insertChildren(insIcons, 'targets0_0')
            return insRightIc, insRightSite
        if isinstance(topInsertedIcon, assignicons.AssignIcon) and (
                isinstance(topParent, assignicons.AssignIcon) or
                isinstance(topParent, listicons.TupleIcon) and topParent.noParens):
            # Insert an assignment icon inside of existing assignment or naked tuple
            return assignicons.insertAssignIcon(atIcon, atSite, topInsertedIcon)
        # The leftmost and rightmost sites are always usable for inserting statement-
        # level icons, because they are adjacent to the statement boundary.
        if atIcon is rightmostIc and (atSite == rightmostSite or atSite == 'seqOut'):
            # Inserting at rightmost site: we must start a new statement, as the inserted
            # icon must be kept at the statement level.
            if not topParent.hasSite('seqOut'):
                # We're appending to the right of a free attribute
                entryIc = entryicon.EntryIcon(window=atIcon.window)
                entryIc.appendPendingArgs([topParent])
                topParent.window.replaceTop(topParent, entryIc)
                topParent = entryIc
            icon.insertSeq(topInsertedIcon, topParent)
            atIcon.window.addTop(topInsertedIcon)
            if cursorLeft:
                return topInsertedIcon, 'seqIn'
            return insRightIc, insRightSite
        if isLeftmostSite(atIcon, atSite):
            # Inserting at the leftmost site.  It may be possible to prefix the inserted
            # statement to the existing statement.  If not, make a new statement
            if isStmtLevelOnly(topParent):
                # Absolutely has to be a new statement
                icon.insertSeq(topInsertedIcon, topParent, before=True)
                atIcon.window.addTop(topInsertedIcon)
                if cursorLeft:
                    return topInsertedIcon, 'seqIn'
                return insRightIc, insRightSite
            else:
                # Try to prefix the inserted statement to the existing one.  This may
                # be dead code, as I can't find any examples that reach here.  If not,
                # consider replacing with better code in unused.py that replaces the
                # recursive call with appendAtSite (written, but couldn't exercise)
                print('Not dead code: remove this print stmt and update comment')
                atIcon.window.replaceTop(topParent, topInsertedIcon,
                    transferStmtComment=False)
                insertAtSite(insRightIc, insRightSite, topParent)
                if cursorLeft:
                    return cursorLeftOfIcon(topInsertedIcon.topLevelParent())
                return insRightIc, insRightSite
        # Inserting a statement-only icon at sites in the middle of an expression is
        # possible if we can split the expression around them.
        enclosingIcon, enclosingSite = entryicon.findEnclosingSite(atIcon, atSite)
        if enclosingIcon is not None:
            return None, None
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
    isUnclosed = hasattr(topInsertedIcon, 'closed') and not topInsertedIcon.closed
    addToUnclosedSeries = None
    if relocatedTree is None:
        cursorIcon, cursorSite = insRightIc, insRightSite
    elif icon.validateCompatibleChild(relocatedTree, insRightIc, insRightSite):
        insRightIc.replaceChild(relocatedTree, insRightSite)
        if isinstance(relocatedTree, entryicon.EntryIcon) and \
                len(relocatedTree.text) == 0:
            # If we just inserted a placeholder icon, see if it can be stripped out
            relocatedTree.remove()
        if insRightIc.typeOf(insRightSite) == 'input':
            checkReorder(insRightIc, needReorder)
        cursorIcon, cursorSite = insRightIc, insRightSite
    elif isUnclosed and relocatedTree.hasSite('output'):
        addToUnclosedSeries = relocatedTree
        cursorIcon, cursorSite = insRightIc, insRightSite
    else:
        entryIc = entryicon.EntryIcon(window=atIcon.window)
        entryIc.appendPendingArgs([relocatedTree])
        insRightIc.replaceChild(entryIc, insRightSite)
        cursorIcon, cursorSite = entryIc, None
    reorderMarkedExprs(atIcon.topLevelParent(), needReorder, replaceTop=True)
    # If we inserted an unclosed series or cursor paren icon, incorporate any adjacent
    # series entries into it (per required tree ordering with unclosed series).
    if isUnclosed:
        if addToUnclosedSeries is not None:
            if isinstance(topInsertedIcon, parenicon.CursorParenIcon):
                topInsertedIcon = entryicon.cvtCursorParenToTuple(topInsertedIcon, False,
                False)
            insertIdx = len(topInsertedIcon.sites.argIcons)
            topInsertedIcon.insertChild(addToUnclosedSeries, 'argIcons', insertIdx)
        entryicon.reopenParen(topInsertedIcon)
    if cursorLeft:
        return cursorLeftIc, cursorLeftSite
    return cursorIcon, cursorSite

def appendAtSite(atIc, atSite, topInsertedIcon, needReorder):
    """Attach code under topInsertedIcon to site (atIc, atSite), as best as possible,
    including making use of empty site on the left (which will affect the hierarchy above
    the given site) or adapting it with a placeholder.  Assumes that the caller has
    filtered out all the cases where topInsertedIcon can't be attached."""
    if topInsertedIcon is None:
        return atIc, atSite
    # If the inserted icon is a placeholder, check if we can strip it off and use its
    # first pending argument, instead.
    if isinstance(topInsertedIcon, entryicon.EntryIcon) and topInsertedIcon.text == '':
        pendingArgs = topInsertedIcon.listPendingArgs()
        if len(pendingArgs) == 0:
            return atIc, atSite
        arg1 = pendingArgs[0]
        if icon.validateCompatibleChild(arg1, atIc, atSite):
            topInsertedIcon.popPendingArgs(0)
            if topInsertedIcon.hasPendingArgs():
                rightmostIcon, rightmostSite = icon.rightmostSite(arg1)
                rightmostIcon.replaceChild(topInsertedIcon, rightmostSite)
            topInsertedIcon = arg1
    # If the inserted code is directly compatible with the requested site: just attach
    if icon.validateCompatibleChild(topInsertedIcon, atIc, atSite):
        atIc.replaceChild(topInsertedIcon, atSite)
        if atIc.typeOf(atSite) == 'input':
            checkReorder(topInsertedIcon, needReorder)
        return atIc, atSite
    # If the insertion site is not directly compatible with the top of the inserted
    # tree, it still may be possible to join the two trees without a placeholder.
    # If the inserted code has an empty site on the left, it may be possible to
    # move code from above the insertion site into that empty site.  Empty sites on
    # the left of the tree are, by nature, input sites, as only binary operators have
    # them.
    if leftSiteIsEmpty(topInsertedIcon) and atSite == 'attrIcon':
        leftIc, leftSite = lowestLeftSite(topInsertedIcon)
        attrRoot = icon.findAttrOutputSite(atIc)
        if attrRoot is not None:
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
    if len(seriesIcons) == 0 or len(seriesIcons) == 1 and seriesIcons[0] is None:
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
    # Handle special cases of joining with comment icons
    if isinstance(nextStmt, commenticon.VerticalBlankIcon):
        nextStmt.window.replaceTop(nextStmt, None)
        return firstStmt, 'seqOut'
    elif isinstance(firstStmt, commenticon.VerticalBlankIcon):
        firstStmt.window.replaceTop(firstStmt, None)
        return nextStmt, 'seqIn'
    if isinstance(nextStmt, commenticon.CommentIcon):
        nextStmt.window.replaceTop(nextStmt, None)
        if isinstance(firstStmt, commenticon.CommentIcon):
            firstStmt.cursorPos = len(firstStmt.string)
            firstStmt.mergeTextFromComment(nextStmt)
            return firstStmt, None
        else:
            stmtComment = firstStmt.hasStmtComment()
            if stmtComment is not None:
                stmtComment.cursorPos = len(stmtComment.string)
                stmtComment.mergeTextFromComment(nextStmt)
                return stmtComment, None
            else:
                nextStmt.attachStmtComment(firstStmt)
                rightmostIc, rightmostSite = icon.rightmostSite(firstStmt)
                return rightmostIc, rightmostSite
    # Handle special cases of assignment statements and joining across block-end icons
    if isinstance(firstStmt, assignicons.AssignIcon) and \
            isinstance(nextStmt, assignicons.AssignIcon):
        return assignicons.joinAssignIcons(firstStmt, nextStmt)
    if isinstance(nextStmt, (assignicons.AssignIcon, assignicons.AugmentedAssignIcon)) \
            and firstStmt.hasSite('output'):
        return assignicons.joinToAssignIcon(firstStmt, nextStmt)
    if isinstance(firstStmt, icon.BlockEnd) or isinstance(nextStmt, icon.BlockEnd):
        if isinstance(firstStmt, icon.BlockEnd):
            blockOwner, blockEnd, joinIc = firstStmt.prevInSeq(), firstStmt, nextStmt
        else:
            blockOwner, blockEnd, joinIc = firstStmt, nextStmt, nextStmt.nextInSeq()
        if isinstance(blockOwner, (blockicons.ForIcon, blockicons.IfIcon,
                blockicons.WhileIcon, blockicons.WithIcon)):
            if joinIc is not None and (joinIc.hasSite('output') or
                    joinIc.hasSite('attrOut')):
                blockEnd.window.removeTop(joinIc)
                blockEnd.replaceChild(joinIc.childAt('seqOut'), 'seqOut')
                joinIc.replaceChild(None, 'seqIn')
                joinIc.replaceChild(None, 'seqOut')
                return insertAtSite(*icon.rightmostSite(blockOwner), joinIc,
                    cursorLeft=True)
    if isStmtLevelOnly(nextStmt):
        return None, None
    rightmostIcon, rightmostSite = icon.rightmostSite(firstStmt)
    if rightmostIcon.isCursorOnlySite(rightmostSite) or rightmostSite == 'seqOut':
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
        if enclIcon is not None and iconsites.isSeriesSiteId(enclSite) or \
                enclIcon is None and not nextStmtNakedTuple and \
                icon.findAttrOutputSite(rightmostIcon, inclEntryIc=False) is not None:
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
    elif firstStmtSeriesSite is not None and nextStmt.hasSite('output') and \
            not isinstance(nextStmt, entryicon.EntryIcon):
        # If the first statement can accept a series and the next statement is compatible
        # with a series, let insertListAtSite decide what to do with it (excluding entry
        # icons, which can join directly to the last argument).
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
    if isinstance(enclosingIcon, (assignicons.AssignIcon,
            assignicons.AugmentedAssignIcon)):
        return None
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
        if right is not None:
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
    if isinstance(enclosingIcon, (assignicons.AssignIcon,
            assignicons.AugmentedAssignIcon)) and enclosingSite[:6] == 'target':
        return assignicons.splitAssignAtTargetSite(enclosingIcon, atIcon, atSite)
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
        if iconsToMove[0] is not None:
            icon.insertSeq(iconsToMove[0], topParent)
            atIcon.window.addTop(iconsToMove[0])
        return topParent, iconsToMove[0]
    else:
        newTuple = listicons.TupleIcon(window=atIcon.window, noParens=True)
        newTuple.insertChildren(iconsToMove, 'argIcons', 0)
        icon.insertSeq(newTuple, topParent)
        atIcon.window.addTop(newTuple)
        return topParent, newTuple

def lexicalTraverse(topNode, includeStmtComment=True, parentIc=None, parentSite=None,
        yieldNakedTuples=False):
    """Both cursors.py and reorderexpr.py have lexical traversal code.  This version
    focuses on the visible parts of the icon structure, as  opposed to the cursors
    version that traverses cursor sites and the reorderexpr version that produces tokens
    and avoids descending into subexpressions.  It visits the icons beneath and including
    topNode, in lexical (left to right, only)  order, and will yield the same icon
    multiple times if that icon has multiple parts at different points in lexical path.
    To distinguish the the icon parts, it yields both and an icon and a partId.  partId
    matches the numbering scheme used in icon.touchesPosition and offsetOfPart.  This
    correspondence is important because click/drag selection and drag target selection
    all use this call to translate mouse position into a lexical icon range.  For empty
    sites, rather than yielding None for the icon, it yields a tuple of the parent icon
    and parent site.  Also note that this will not emit naked tuple icons unless
    yieldNakedTuples is set to True (as they have no lexical presence outside of the
    commas that we ignore in all other cases).  With yieldNakedTuples set to True, it
    will yield the tuple AFTER its entries, and only if all of its (non-empty) arguments
    are included in the traversal.  Recursive calls are made with topNode set to None and
    parentIc and parentSite, instead, indicating where to start traversal."""
    if topNode is None:
        node = parentIc.childAt(parentSite)
    else:
        node = topNode
    if node is None:
        if parentSite == 'output':
            yield (parentIc, parentSite), 0
        return
    elif isinstance(node, (opicons.BinOpIcon, infixicon.InfixIcon)):
        if hasattr(node, 'hasParens') and node.hasParens:
            yield node, 1
        yield from lexicalTraverse(None, False, node, 'leftArg')
        yield node, 2
        yield from lexicalTraverse(None, False, node, 'rightArg')
        if hasattr(node, 'hasParens') and node.hasParens:
            yield node, 3
            yield from lexicalTraverse(None, False, node, 'attrIcon')
    elif isinstance(node, opicons.DivideIcon):
        yield from lexicalTraverse(None, False, node, 'topArg')
        yield node, 1
        yield from lexicalTraverse(None, False, node, 'bottomArg')
    elif isinstance(node, opicons.IfExpIcon):
        if node.hasParens:
            yield node, 1
        yield from lexicalTraverse(None, False, node, 'trueExpr')
        yield node, 2
        yield from lexicalTraverse(None, False, node, 'testExpr')
        yield node, 3
        yield from lexicalTraverse(None, False, node, 'falseExpr')
        if node.hasParens:
            yield node, 4
            yield from lexicalTraverse(None, False, node, 'attrIcon')
    elif isinstance(node, listicons.TupleIcon) and node.noParens:
        for site in node.sites.argIcons:
            yield from lexicalTraverse(None, False, node, site.name)
        if yieldNakedTuples:
            yield node, 0
    elif isinstance(node, (listicons.ListTypeIcon, listicons.CallIcon)):
        yield node, 1
        for site in node.sites.argIcons:
            yield from lexicalTraverse(None, False, node, site.name)
        if hasattr(node.sites, 'cprhIcons'):
            for site in node.sites.cprhIcons:
                if site.att is not None:
                    yield from lexicalTraverse(None, False, node, site.name)
        yield node, 2
        yield from lexicalTraverse(None, False, node, 'attrIcon')
    elif isinstance(node, parenicon.CursorParenIcon):
        yield node, 1
        yield from lexicalTraverse(None, False, node, 'argIcon')
        yield node, 2
        yield from lexicalTraverse(None, False, node, 'attrIcon')
    elif isinstance(node, assignicons.AssignIcon):
        for i, tgtList in enumerate(node.tgtLists):
            for site in getattr(node.sites, tgtList.siteSeriesName):
                yield from lexicalTraverse(None, False, node, site.name)
            yield node, (i + 1) * 3
        for site in node.sites.values:
            yield from lexicalTraverse(None, False, node, site.name)
    elif isinstance(node, assignicons.AugmentedAssignIcon):
        yield from lexicalTraverse(None, False, node, 'targetIcon')
        yield node, 2
        for site in node.sites.values:
            yield from lexicalTraverse(None, False, node, site.name)
    elif isinstance(node, blockicons.ForIcon):
        yield node, 1
        for site in node.sites.targets:
            yield from lexicalTraverse(None, False, node, site.name)
        yield node, 2
        for site in node.sites.iterIcons:
            yield from lexicalTraverse(None, False, node, site.name)
    elif isinstance(node, blockicons.DefOrClassIcon):
        yield node, 1
        yield from lexicalTraverse(None, False, node, 'nameIcon')
        if node.hasArgs:
            yield node, 2
            for site in node.sites.argIcons:
                yield from lexicalTraverse(None, False, node, site.name)
            yield node, 3
    else:
        yield node, 1
        for siteOrSeries in node.sites.traverseLexical():
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                for site in siteOrSeries:
                    yield from lexicalTraverse(None, False, node, site.name)
            else:
                yield from lexicalTraverse(None, False, node, siteOrSeries.name)
    if includeStmtComment:
        stmtComment = node.hasStmtComment()
        if stmtComment:
            yield stmtComment, 1

def extendDragTargetLexical(startIcon, pointerX, pointerY):
    """Return a set of the icons to highlight for replacement as a drag target based on
    the location pointed to by coordinates pointerX and pointerY (as this is a drag
    target, these actually represent the dragging icons insert site as opposed to the
    mouse but we assume that the caller has calculated this for us).  Will always return
    a set of icons, regardless of the pointer position (never returns None)."""
    # Figure out the statement (vertically) containing the pointer in the sequence
    # following (and including) the statement containing startIcon.
    startIconStmt = startIcon.topLevelParent()
    lastStmtInSeq = None
    pointerBeyondSeq = False
    for stmtIcon in icon.traverseSeq(startIconStmt, includeStartingIcon=True):
        nextStmt = stmtIcon.nextInSeq()
        if nextStmt is not None and nextStmt.rect[1] < pointerY:
            # Safe to skip testing this statement if the next one starts above pointerY
            continue
        hierRect = stmtIcon.hierRect()
        minY = hierRect[1]
        maxY = hierRect[3]
        if pointerY < minY:
            if stmtIcon is startIconStmt:
                # Pointer is above the starting statement
                return {startIcon}
            # Pointer is between the previous statement and this one, which shouldn't be
            # possible, but handle it, just in case this somehow becomes possible
            endIconStmt = stmtIcon.prevInSeq()
            break
        if pointerY <= maxY:
            endIconStmt = stmtIcon
            break
        lastStmtInSeq = stmtIcon
    else:
        # Pointer is beyond the end of the sequence
        endIconStmt = lastStmtInSeq
        pointerBeyondSeq = True
    # Lexically traverse the statement containing the pointer (or preceding it if the
    # pointer is beyond the end of the last statement (pointerBeyondSeq is True)
    foundStart = startIconStmt is not endIconStmt
    minDistToLeftIc = minDistToRightIc = None
    icOnLeft = icOnRight = None
    leftIcPart = rightIcPart = None
    for ic, partId in lexicalTraverse(endIconStmt):
        if pointerBeyondSeq:
            lastIc = ic
            lastIcPart = partId
            continue
        if not foundStart:
            if ic is startIcon:
                foundStart = True
            continue
        distToLeftIc = ic.partIsLeftOfPoint(partId, pointerX, pointerY)
        if distToLeftIc is None:
            distToRightIc = ic.partIsRightOfPoint(partId, pointerX, pointerY)
            if distToRightIc is None:
                continue
            if minDistToRightIc is None or minDistToRightIc > distToRightIc:
                minDistToRightIc = distToRightIc
                icOnRight = ic
                rightIcPart = partId
        else:
            if minDistToLeftIc is None or \
                    distToLeftIc < minDistToLeftIc:
                minDistToLeftIc = distToLeftIc
                icOnLeft = ic
                leftIcPart = partId
    if pointerBeyondSeq:
        rVal = iconsInLexicalRange(startIcon, lastIc, lastIcPart)
        return rVal if rVal is not None else {startIcon}
    elif icOnLeft:
        rVal = iconsInLexicalRange(startIcon, icOnLeft, leftIcPart)
        return rVal if rVal is not None else {startIcon}
    elif icOnRight:
        rVal = iconsInLexicalRange(startIcon, icOnRight, rightIcPart,
            stopBeforeLast=True)
        return rVal if rVal is not None else {startIcon}
    else:
        return {startIcon}

def extendDragTargetStructural(fromIcon, step):
    """Uses step value (integer 0-n) to figure out what icons to highlight as a drag
    target.  Conceptually, step resents a hierarchy level with 0 being fromIcon, 1
    being fromIcon's parent, etc..  However, there are a few cases where strict hierarchy
    is not what the user would want:  We also 1) condense associative chains (a+b+c+d)
    into a single level, and 2) add a step to series sites that have multiple entries
    (and are not naked tuples) which selects all of the elements of the series without
    selecting the parent.  Returns a selection set, containing icons and tuples, with
    the tuples representing empty sites in the form: (parent, site)."""
    selectedIcons = set(fromIcon.traverse())
    if step == 0:
        return selectedIcons
    parent = fromIcon.parent()
    attachSiteType = None if parent is None else parent.typeOf(parent.siteOf(fromIcon))
    rootIc = fromIcon
    seriesSitesSelected = None
    for i in range(step):
        # If seriesSitesSelected was set, this iteration will be the same rootIc, (parent
        # of the series) but for the icon itself rather than its series entries.
        if seriesSitesSelected is not None:
            seriesSitesSelected = None
            continue
        parent = rootIc.parent()
        if parent is None:
            break
        # If ic is on a series site with multiple entries, return the series, as a step,
        # before returning the parent (see top of loop).  That is, unless the parent is a
        # naked tuple, which we don't want to exist with no entries.
        parentSite = parent.siteOf(rootIc)
        if iconsites.isSeriesSiteId(parentSite) and not (
                isinstance(parent, listicons.TupleIcon) and parent.noParens):
            seriesName, _ = iconsites.splitSeriesSiteId(parentSite)
            if len(getattr(parent.sites, seriesName)) > 1:
                seriesSitesSelected = seriesName
                rootIc = parent
                continue
        # Moving up the hierarchy can change the type of the attachment site.  If the new
        # site is not compatible, continue upwards until we find one that is.
        grandparent = parent.parent()
        if attachSiteType is not None:
            while grandparent is not None and \
                    grandparent.typeOf(grandparent.siteOf(parent)) != attachSiteType:
                rootIc = parent
                parent = grandparent
                grandparent = parent.parent()
        # If parent is a binary operator that's part of an associative chain, return
        # the top of the chain rather than just the next operator up
        while isinstance(parent, opicons.BinOpIcon) and isinstance(grandparent,
                opicons.BinOpIcon) and parent.precedence == grandparent.precedence:
            rootIc = parent
            parent = grandparent
            grandparent = parent.parent()
        rootIc = parent
    # Replace the uncommented code below with the commented-out version once we have
    # support for selection of empty sites
    # if seriesSitesSelected is None:
    #     return selectSetHier(rootIc)
    # else:
    #     selectedSet = set()
    #     for site in getattr(rootIc.sites, seriesSitesSelected):
    #         ic = rootIc.childAt(site.name)
    #         if ic is None:
    #             selectedSet.add((ic, site.name))
    #         else:
    #             selectedSet += selectSetHier(ic)
    if seriesSitesSelected is None:
        return set(rootIc.traverse(includeSelf=True))
    else:
        selectedSet = set()
        for site in getattr(rootIc.sites, seriesSitesSelected):
            ic = rootIc.childAt(site.name)
            if ic is not None:
                selectedSet |= set(ic.traverse(includeSelf=True))
    return selectedSet

def extendDragTargetByStmt(startStmt, pointerX, pointerY):
    """Returns a set of icons to highlight for replacement as a drag target, starting
    from (and including) startStmt and continuing through whatever statement in the
    sequence containing startStme is vertically in range of pointerY.  If pointerY is
    beyond the start or end of the sequence, returns the set of icons in all statements
    from startStmt through the start or end of the sequence.  Currently, pointerX is not
    used, but is left as a parameter should we want to revert to the lexical selection
    that earlier versions of this did."""
    hierRect = startStmt.hierRect()
    topSelectStmt = bottomSelectStmt = startStmt
    if pointerY < hierRect[1]:
        # Pointer is above the starting statement: traverse upward from it to find the
        # first statement to which it is (vertically) adjacent
        for stmtIcon in icon.traverseSeq(startStmt, includeStartingIcon=True,
                reverse=True):
            prevStmt = stmtIcon.prevInSeq()
            if prevStmt is None:
                # Pointer is above the start of the sequence
                topSelectStmt = stmtIcon
                break
            if prevStmt.rect[3] > pointerY:
                # Safe to skip testing this statement if prev one ends below pointerY
                continue
            hierRect = stmtIcon.hierRect(inclStmtComment=True)
            minY = hierRect[1]
            maxY = hierRect[3]
            if pointerY > maxY:
                # Pointer is between the previous statement and this one, which won't
                # happen based on current layout rules, but may be possible, someday.
                topSelectStmt = stmtIcon.nextInSeq()
                break
            if pointerY >= minY:
                topSelectStmt = stmtIcon
                break
    elif pointerY <= hierRect[3]:
        # Pointer is vertically within the the range of the starting statement
        topSelectStmt = bottomSelectStmt = startStmt
    else:
        # Pointer is below the starting statement: traverse downward from it to find the
        # last statement to which it is (vertically) adjacent
        topSelectStmt = startStmt
        for stmtIcon in icon.traverseSeq(startStmt, includeStartingIcon=False):
            nextStmt = stmtIcon.nextInSeq()
            if nextStmt is None:
                # Pointer is beyond the end of the sequence
                bottomSelectStmt = stmtIcon
                break
            if nextStmt.rect[1] < pointerY:
                # Safe to skip testing this stmt if the next one starts above pointerY
                continue
            hierRect = stmtIcon.hierRect()
            minY = hierRect[1]
            maxY = hierRect[3]
            if pointerY < minY:
                # Pointer is between the previous statement and this one, which won't
                # happen based on current layout rules, but may be possible, someday.
                bottomSelectStmt = stmtIcon.prevInSeq()
                break
            if pointerY <= maxY:
                bottomSelectStmt = stmtIcon
                break
    # Create a set to return, containing all of the icons in the determined range
    selectedIcons = set()
    for stmtIcon in icon.traverseSeq(topSelectStmt, includeStartingIcon=True):
        if isinstance(stmtIcon, icon.BlockEnd):
            if stmtIcon.primary in selectedIcons:
                selectedIcons.add(stmtIcon)
        else:
            for ic in stmtIcon.traverse(inclStmtComment=True):
                selectedIcons.add(ic)
        if stmtIcon is bottomSelectStmt:
            break
    return selectedIcons

def extendDefaultReplaceSite(movIcon, sIcon):
    """Normally, when the user snaps an icon to a replace site, the default replacement
    target is the hierarchy under that icon.  However, there are some cases where that
    is inappropriate. Currently, all involve dragging children of the InfixIcon that have
    rules about what icons they can appear under.  We want the user to be able to snap
    these to the replace site of the leftmost coincident icon, as this is usually easier
    than locating the top icon, and would otherwise need to be prohibited to prevent
    embedding one of these at a lower level (i.e. f(a=b=c) or {a:b:c})."""
    if not hasattr(movIcon, 'allowableParents'):
        return sIcon
    allowableParents = movIcon.allowableParents
    highestIcon = iconsites.highestCoincidentIcon(sIcon)
    parent = highestIcon.parent()
    allowableSite = allowableParents.get(parent.__class__.__name__)
    if allowableSite is None:
        return sIcon
    siteName = parent.siteOf(highestIcon)
    if iconsites.isSeriesSiteId(siteName):
        siteName, _ = iconsites.splitSeriesSiteId(siteName)
    if allowableSite == siteName:
        return highestIcon
    return sIcon

def iconsInLexicalRange(fromIcon, toIcon, toPartId=None, stopBeforeLast=False):
    """Return a set containing all of the icons lexically between fromIcon and toIcon.
    Returns None if fromIcon does not precede toIcon in traversal."""
    # This wastes resources by scanning all the way to the end of the sequence to reject
    # invalid toIcon.  To make it waste less, scan just the top icons of the sequence
    # starting at fromIcon's top parent, looking for toIcon's top parent.
    toIconTopIcon = toIcon.topLevelParent()
    fromIconTopIcon = fromIcon.topLevelParent()
    for topIc in icon.traverseSeq(fromIconTopIcon, includeStartingIcon=True):
        if topIc is toIconTopIcon:
            break
    else:
        return None
    iconsInRange = set()
    foundStart = False
    for topIc in icon.traverseSeq(fromIconTopIcon, includeStartingIcon=True):
        if isinstance(topIc, icon.BlockEnd):
            # Include traversed block-end icons if their corresponding owner is selected,
            # but otherwise ignore unless they are specifically the stopping icon
            if topIc.primary in iconsInRange:
                iconsInRange.add(topIc)
            if topIc is toIcon:
                return iconsInRange
            continue
        for ic, partId in lexicalTraverse(topIc, yieldNakedTuples=True):
            if not foundStart and ic is fromIcon:
                foundStart = True
            if stopBeforeLast and ic is toIcon and (toPartId is None or
                    toPartId == partId):
                return iconsInRange
            if foundStart:
                if isinstance(ic, listicons.TupleIcon) and ic.noParens:
                    # Include naked tuples in the returned set only if all of their
                    # arguments are included in the range
                    for elem in ic.argIcons():
                        if elem not in iconsInRange:
                            break
                    else:
                        iconsInRange.add(ic)
                if isinstance(ic, assignicons.AssignIcon):
                    # Include assignment icons in the returned set only if their
                    # rightmost '=' is within the range.  This (somewhat) mitigates the
                    # problem of users seeing '=' as a character rather than as part of
                    # a larger assignment statement icon, and trying to replace multiple
                    # target groups together.  They still won't get what they want, but
                    # at least we won't delete the whole assignment, as we would if we
                    # treated them like other icons.
                    if partId == len(ic.tgtLists) * 3:
                        iconsInRange.add(ic)
                else:
                    iconsInRange.add(ic)
                if ic is toIcon and (toPartId is None or partId == toPartId):
                    return iconsInRange
    return None

def splitDeletedIcons(ic, toDelete, assembleDeleted, needReorder, watchSubs=None,
        preserveSite=None):
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
    substitutions (see removeIcons description for details).  preserveSite can be set to
    a tuple icon (destined for re-insertion in a replace operation) to keep it from being
    removed when it gets down to a single entry."""
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
            # If we're stripping off the entry icon and it held the cursor, move it to a
            # parent or connected icon.  (This is a hackish patch for a very specific
            # problem that probably needs a more general solution.  splitDeletedIcons
            # does not normally concern itself with cursors, but unfortunately has no
            # mechanism for reporting dropped, as opposed to explicitly deleted, icons)
            cursor = ic.window.cursor
            if subsList is not None and cursor.icon is ic and cursor.type in ('icon',
                    'text'):
                entryParent = ic.parent()
                if entryParent is not None:
                    cursor.setToIconSite(entryParent, entryParent.siteOf(ic),
                        placeEntryText=False)
                elif ic.childAt('seqIn') is not None:
                    cursor.setToIconSite(ic.childAt('seqIn'), 'seqOut',
                        placeEntryText=False)
                elif ic.childAt('seqOut') is not None:
                    cursor.setToIconSite(ic.childAt('seqOut'), 'seqIn',
                        placeEntryText=False)
                elif len(subsList) > 0:
                    cursor.setToIconSite(subsList[0], cursors.topSite(subsList[0]),
                        placeEntryText=False)
                else:
                    cursor.setToWindowPos(ic.pos(), placeEntryText=False)
    # If ic is a naked tuple, deletion of its content could leave it empty or owning a
    # single element.  If so, remove it.
    if subsList is None and isinstance(ic, listicons.TupleIcon) and ic.noParens and \
            len(ic.sites.argIcons) == 1 and ic is not preserveSite:
        argIcon = ic.childAt('argIcons_0')
        if argIcon is None:
            subsList = []
        else:
            ic.replaceChild(None, 'argIcons_0')
            subsList = [argIcon]
        # If we're stripping off a tuple icon that held the cursor, move it to an
        # adjacent icon (see explanation above in similar code, above, for entry icons)
        cursor = ic.window.cursor
        if subsList is not None and cursor.icon is ic and cursor.type == 'icon':
            if argIcon is not None:
                if cursor.site == 'argIcons_0':
                    cursor.setToIconSite(subsList[0], 'output', placeEntryText=False)
                else:
                    cursor.setToIconSite(*icon.rightmostSite(argIcon),
                        placeEntryText=False)
            elif ic.childAt('seqIn') is not None:
                cursor.setToIconSite(ic.childAt('seqIn'), 'seqIn', placeEntryText=False)
            elif ic.childAt('seqOut') is not None:
                cursor.setToIconSite(ic.childAt('seqOut'), 'seqOut', placeEntryText=False)
            else:
                cursor.setToWindowPos(ic.pos(), placeEntryText=False)
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

def reorderMarkedExprs(topIcon, exprsNeedingReorder, replaceTop=False, watchSubs=None):
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
        newTopIc = reorderexpr.reorderArithExpr(ic, skipReplaceTop=True,
            watchSubs=watchSubs)
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
    if parent is None and site in ('output', 'attrOut'):
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
