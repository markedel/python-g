# Copyright Mark Edel  All rights reserved
from PIL import Image
import ast
import comn
import icon
import iconlayout
import iconsites
import nameicons
import listicons
import opicons
import entryicon
import cursors

assignDragImage = comn.asciiToImage((
 "......",
 "......",
 "......",
 "......",
 "......",
 "...ooo",
 "..o%%%",
 "55%%%.",
 "%%%%..",
 "55%%%.",
 "..o%%%",
 "...ooo",
 "......",
 "......",
 "......",
 "......"))

inpSeqImage = comn.asciiToImage((
 "ooo",
 "ooo",
 "ooo",
 "o o",
 "o o",
 "o o",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "o o",
 "o o",
 "ooo",
 "ooo",
 "ooo"))

class AssignIcon(icon.Icon):
    def __init__(self, numTargets=1, window=None, location=None):
        icon.Icon.__init__(self, window)
        opWidth, opHeight = icon.getTextSize('=')
        opWidth += 2*icon.TEXT_MARGIN + 1
        opHeight += 2*icon.TEXT_MARGIN + 1
        siteY = inpSeqImage.height // 2
        self.opSize = (opWidth, opHeight)
        tgtSitesX = assignDragImage.width - 3
        seqSiteX = tgtSitesX + 1
        self.sites.add('seqIn', 'seqIn', seqSiteX, siteY - inpSeqImage.height // 2 + 1)
        self.sites.add('seqOut', 'seqOut', seqSiteX, siteY + inpSeqImage.height//2 - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteY)
        self.tgtLists = [iconlayout.ListLayoutMgr(self, 'targets0', tgtSitesX, siteY,
                simpleSpine=True)]
        valueSitesX = tgtSitesX + icon.EMPTY_ARG_WIDTH + opWidth
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', valueSitesX, siteY,
                simpleSpine=True)
        if location is None:
            x = y = 0
        else:
            x, y = location
        width = assignDragImage.width + self.tgtLists[0].width + opWidth - 2 + \
                self.valueList.width
        self.rect = (x, y, x + width, y + inpSeqImage.height)
        for i in range(1, numTargets):
            self.addTargetGroup(i)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            self.drawList = []
            siteY = self.sites.seqInsert.yOffset
            # Left site (seq site bar + 1st target input or drag-insert site
            leftTgtHasSpine = self.tgtLists[0].simpleSpineWillDraw()
            tgtSiteX = self.sites.targets0[0].xOffset
            if leftTgtHasSpine:
                tgtSiteX -= icon.OUTPUT_SITE_DEPTH
            if temporaryDragSite:
                y = siteY - assignDragImage.height // 2
                self.drawList.append(((0, y), assignDragImage))
            elif not leftTgtHasSpine:
                y = siteY - inpSeqImage.height // 2
                self.drawList.append(((tgtSiteX, y), inpSeqImage))
            # Commas, spines and an = for each target group
            txtImg = icon.iconBoxedText('=')
            opWidth, opHeight = txtImg.size
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            rInSiteX = opWidth - icon.inSiteImage.width
            rInSiteY = opHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (rInSiteX, rInSiteY))
            for i, tgtList in enumerate(self.tgtLists):
                self.drawList += tgtList.drawListCommas(tgtSiteX, siteY)
                spines = tgtList.drawSimpleSpine(tgtSiteX, siteY, drawOutputSite=False)
                if i == 0 and leftTgtHasSpine:
                    # If the leftmost target list has a spine, drawing of inpSeqImage
                    # was skipped, above, and we draw the sequence sites on the spine
                    leftSpineImg = spines[0][1]
                    icon.drawSeqSites(leftSpineImg, 0, 0, leftSpineImg.height)
                self.drawList += spines
                tgtSiteX += tgtList.width - 1
                self.drawList.append(((tgtSiteX + icon.OUTPUT_SITE_DEPTH,
                        siteY - opHeight // 2), img))
                tgtSiteX += opWidth - 1
            self.drawList += self.valueList.drawListCommas(tgtSiteX, siteY)
            self.drawList += self.valueList.drawSimpleSpine(tgtSiteX, siteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def addTargetGroup(self, idx):
        if idx < 0 or idx > len(self.tgtLists):
            raise Exception('Bad index for adding target group to assignment icon')
        # Name will be filled in by renumberTargetGroups, offset by layout
        self.tgtLists.insert(idx, iconlayout.ListLayoutMgr(self, 'targetsX', 0, 0,
                simpleSpine=True))
        self.renumberTargetGroups(descending=True)
        self.window.undo.registerCallback(self.removeTargetGroup, idx)
        self.markLayoutDirty()

    def removeTargetGroup(self, idx):
        if idx <= 0 or idx >= len(self.tgtLists):
            raise Exception('Bad index for removing target group from assignment icon')
        seriesName = 'targets%d' % idx
        for site in self.sites.getSeries(seriesName):
            if site.att is not None:
                raise Exception('Removing non-empty target group from assignment icon')
        del self.tgtLists[idx]
        self.sites.removeSeries("targets%d" % idx)
        self.renumberTargetGroups()
        self.window.undo.registerCallback(self.addTargetGroup, idx)
        self.markLayoutDirty()

    def renumberTargetGroups(self, descending=False):
        tgtLists = list(enumerate(self.tgtLists))
        if descending:
            tgtLists = reversed(tgtLists)
        for i, tgtList in tgtLists:
            oldName = tgtList.siteSeriesName
            newName = "targets%d" % i
            if oldName != newName:
                tgtList.rename(newName)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        insertSites = []
        for tgtList in self.tgtLists:
            insertSites += tgtList.makeInsertSnapList()
        insertSites += self.valueList.makeInsertSnapList()
        siteSnapLists['insertInput'] = insertSites
        # Snap site for seqOut is too close to snap site for inserting the first target.
        # Nudge the seqOut site down and to the left to make it easier to snap to
        ic, (x, y), siteType = siteSnapLists['seqOut'][0]
        siteSnapLists['seqOut'][0] = (ic, (x-1, y+1), siteType)
        return siteSnapLists

    def execute(self):
        # Get the target and value icons
        tgtLists = []
        for tgtList in self.tgtLists:
            tgts = []
            for site in getattr(self.sites, tgtList.siteSeriesName):
                if site.att is None:
                    raise icon.IconExecException(self, "Missing assignment target(s)")
                tgts.append(site.att)
            tgtLists.append(tgts)
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing assignment value")
            values.append(site.att)
        # Execute all of the value icons
        executedValues = []
        for value in values:
            executedValues.append(value.execute())
        # Assign the resulting values to the targets
        if len(values) == 1:
            value = executedValues[0]
        else:
            value = tuple(executedValues)
        for tgts in tgtLists:
            if len(tgts) == 1:
                tgtIcon = tgts[0]
            else:
                tgtIcon = tgts
            self.assignValues(tgtIcon, value)

    def createAst(self):
        # Get the target and value icons
        tgtLists = []
        for tgtList in self.tgtLists:
            tgts = []
            for site in getattr(self.sites, tgtList.siteSeriesName):
                if site.att is None:
                    raise icon.IconExecException(self, "Missing assignment target(s)")
                tgts.append(site.att)
            tgtLists.append(tgts)
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing assignment value")
            values.append(site.att)
        # Make asts for targets and values, adding tuples if packing/unpacking is
        # specified
        if len(values) == 1:
            valueAst = values[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in values], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        tgtAsts = []
        for tgts in tgtLists:
            if len(tgts) == 1:
                tgtAst = tgts[0].createAst()
            else:
                perTgtAsts = [tgt.createAst() for tgt in tgts]
                tgtAst = ast.Tuple(perTgtAsts, ctx=ast.Store(), lineno=self.id,
                 col_offset=0)
            tgtAsts.append(tgtAst)
        return ast.Assign(tgtAsts, valueAst, lineno=self.id, col_offset=0)

    def assignValues(self, tgtIcon, value):
        if isinstance(tgtIcon, nameicons.IdentifierIcon):
            try:
                globals()[tgtIcon.name] = value
            except Exception as err:
                raise icon.IconExecException(self, err)
            return
        if tgtIcon.__class__ in (listicons.TupleIcon, listicons.ListIcon):
            assignTargets = tgtIcon.argIcons()
        elif isinstance(tgtIcon, list):
            assignTargets = tgtIcon
        else:
            raise icon.IconExecException(tgtIcon, "Not a valid assignment target")
        if not hasattr(value, "__len__") or len(assignTargets) != len(value):
            raise icon.IconExecException(self, "Could not unpack")
        for target in assignTargets:
            if target is None:
                raise icon.IconExecException(self, "Missing argument(s)")
            for t, v in zip(assignTargets, value):
                self.assignValues(t, v)

    def doLayout(self, left, top, layout):
        for tgtList in self.tgtLists:
            tgtList.doLayout(layout)
        self.valueList.doLayout(layout)
        opWidth, opHeight = self.opSize
        heightAbove = opHeight // 2
        heightBelow = opHeight - heightAbove
        for tgtList in self.tgtLists:
            heightAbove = max(heightAbove, tgtList.spineTop)
            heightBelow = max(heightBelow, tgtList.spineHeight - tgtList.spineTop)
        heightAbove = max(heightAbove, self.valueList.spineTop)
        heightBelow = max(heightBelow, self.valueList.spineHeight-self.valueList.spineTop)
        leftSpineTop = heightAbove - self.tgtLists[0].spineTop
        self.sites.seqIn.yOffset = leftSpineTop + 1
        self.sites.seqOut.yOffset = leftSpineTop + self.tgtLists[0].spineHeight - 1
        self.sites.seqInsert.yOffset = heightAbove
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + heightAbove)
        height = heightAbove + heightBelow
        width = self.sites.seqIn.xOffset - 1 + layout.width
        self.rect = (left, top, left + width, top + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        opWidth, opHeight = self.opSize
        tgtListsLayouts = [tgtList.calcLayouts() for tgtList in self.tgtLists]
        valueLayouts = self.valueList.calcLayouts()
        layouts = []
        for valueLayout, *tgtLayouts in iconlayout.allCombinations(
                (valueLayouts, *tgtListsLayouts)):
            layout = iconlayout.Layout(self, opWidth, opHeight, opHeight // 2)
            # Calculate for assignment target lists (each clause of =)
            if tgtLayouts[0] is not None and len(tgtLayouts[0].rowWidths) >= 2:
                x = 0  # If first target group includes spine, don't offset
            else:
                x = inpSeqImage.width - 1
            for i, tgtLayout in enumerate(tgtLayouts):
                tgtLayout.mergeInto(layout, x, 0)
                x += tgtLayout.width + opWidth - 2
            # Calculate layout for assignment value(s)
            layout.width = x + 1
            valueLayout.mergeInto(layout, x, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, numTargets=len(self.tgtLists))

    def textRepr(self):
        text = ""
        for tgtList in self.tgtLists:
            text += icon.seriesTextRepr(getattr(self.sites, tgtList.siteSeriesName)) + \
                    " = "
        return text + icon.seriesTextRepr(self.sites.values)

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        topIcon = self.topLevelParent()
        redrawRegion = comn.AccumRects(topIcon.hierRect())
        win = self.window
        if index == 0:
            if siteName == "targets0":
                return
            if siteName == "values" and not hasattr(self.sites, 'targets1'):
                # This is the only '=' in the assignment, convert it to a tuple
                argIcons = [tgtSite.att for tgtSite in self.sites.targets0]
                numTargets = len(argIcons)
                argIcons += [valueSite.att for valueSite in self.sites.values]
                newTuple = listicons.TupleIcon(window=win, noParens=True)
                for i, arg in enumerate(argIcons):
                    if arg is not None:
                        self.replaceChild(None, self.siteOf(arg))
                    newTuple.insertChild(arg, "argIcons", i)
                parent = self.parent()
                if parent is None:
                    win.replaceTop(self, newTuple)
                else:
                    # I don't think this is possible, remove if print never appears
                    print("Assign icon has parent?????")
                    parentSite = parent.siteOf(self)
                    parent.replaceChild(newTuple, parentSite)
                cursorSite = iconsites.makeSeriesSiteId('argIcons', numTargets)
                win.cursor.setToIconSite(newTuple, cursorSite)
            else:
                # Merge lists around '=' to convert it to ','
                topIcon = self.topLevelParent()
                redrawRegion = comn.AccumRects(topIcon.hierRect())
                if siteName == "values":
                    removetgtGrpIdx = len(self.tgtLists) - 1
                    srcSite = "targets%d" % removetgtGrpIdx
                    destSite = "values"
                    destIdx = 0
                    cursorIdx = len(getattr(self.sites, srcSite)) - 1
                else:
                    srcSite = siteName
                    removetgtGrpIdx = int(siteName[7:])
                    destSite = siteName[:7] + str(removetgtGrpIdx - 1)
                    destIdx = len(getattr(self.sites, destSite))
                    cursorIdx = destIdx - 1
                argIcons = [s.att for s in getattr(self.sites, srcSite)]
                for i, arg in enumerate(argIcons):
                    self.replaceChild(None, self.siteOf(arg))
                    self.insertChild(arg, destSite, destIdx + i)
                self.removeTargetGroup(removetgtGrpIdx)
                cursorSite = iconsites.makeSeriesSiteId(destSite, cursorIdx)
                cursorIc = self.childAt(cursorSite)
                if cursorIc is None:
                    cursorIc = self
                else:
                    cursorIc, cursorSite = cursors.rightmostSite(
                        icon.findLastAttrIcon(cursorIc))
                win.cursor.setToIconSite(cursorIc, cursorSite)
        else:
            # Cursor is on comma input.  Delete if empty or previous site is empty
            prevSite = iconsites.makeSeriesSiteId(siteName, index - 1)
            childAtCursor = self.childAt(siteId)
            if childAtCursor and self.childAt(prevSite):
                cursors.beep()
                return
            topIcon = self.topLevelParent()
            redrawRegion = comn.AccumRects(topIcon.hierRect())
            if not self.childAt(prevSite):
                self.removeEmptySeriesSite(prevSite)
                win.cursor.setToIconSite(self, prevSite)
            else:
                rightmostIcon = icon.findLastAttrIcon(self.childAt(prevSite))
                rightmostIcon, rightmostSite = cursors.rightmostSite(rightmostIcon)
                self.removeEmptySeriesSite(siteId)
                win.cursor.setToIconSite(rightmostIcon, rightmostSite)
        redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
        win.refresh(redrawRegion.get())
        win.undo.addBoundary()


class AugmentedAssignIcon(icon.Icon):
    def __init__(self, op, window, location=None):
        icon.Icon.__init__(self, window)
        self.op = op
        bodyWidth = icon.getTextSize(self.op + '=')[0] + 2 * icon.TEXT_MARGIN + 1
        bodyHeight = icon.minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        targetXOffset = icon.dragSeqImage.width-1 - icon.OUTPUT_SITE_DEPTH
        self.sites.add('targetIcon', 'input', targetXOffset, siteYOffset)
        seqX = icon.dragSeqImage.width - 1
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.targetWidth = icon.EMPTY_ARG_WIDTH
        argX = icon.dragSeqImage.width + self.targetWidth + bodyWidth
        self.valuesList = iconlayout.ListLayoutMgr(self, 'values', argX, siteYOffset,
                simpleSpine=True)
        totalWidth = argX + self.valuesList.width - 2
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            self.drawList = []
            bodyWidth, bodyHeight = self.bodySize
            # Left site (seq site bar + 1st target input or drag-insert site
            tgtSiteX = self.sites.targetIcon.xOffset
            tgtSiteY = self.sites.targetIcon.yOffset
            if temporaryDragSite:
                y = tgtSiteY - assignDragImage.height // 2
                self.drawList.append(((0, y), assignDragImage))
            else:
                y = tgtSiteY - inpSeqImage.height // 2
                self.drawList.append(((tgtSiteX, y), inpSeqImage))
            img = Image.new('RGBA', (bodyWidth, bodyHeight), color=(0, 0, 0, 0))
            targetOffset = icon.dragSeqImage.width - 1
            bodyOffset = targetOffset + self.targetWidth - 1
            txtImg = icon.iconBoxedText(self.op + '=')
            img.paste(txtImg, (0, 0))
            inImageX = bodyWidth - icon.inSiteImage.width
            inImageY = bodyHeight // 2 - icon.inSiteImage.height // 2
            img.paste(icon.inSiteImage, (inImageX, inImageY))
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList.append(((bodyOffset, bodyTopY), img))
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valuesList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valuesList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valuesList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, left, top, layout):
        self.valuesList.doLayout(layout)
        self.targetWidth = layout.targetWidth
        bodyWidth, bodyHeight = self.bodySize
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        width = icon.dragSeqImage.width - 1 + bodyWidth - 1 + self.targetWidth - 1 + \
                self.valuesList.width - 1
        if self.valuesList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.valuesList.spineTop)
            heightBelow = max(heightBelow, self.valuesList.spineHeight -
                    self.valuesList.spineTop)
        self.sites.seqInsert.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        height = heightAbove + heightBelow
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        valueListLayouts = self.valuesList.calcLayouts()
        targetIcon = self.sites.targetIcon.att
        tgtLayouts = [None] if targetIcon is None else targetIcon.calcLayouts()
        layouts = []
        for valueListLayout, tgtLayout in iconlayout.allCombinations(
                (valueListLayouts, tgtLayouts)):
            layout = iconlayout.Layout(self, bodyWidth, bodyHeight, 1)
            layout.addSubLayout(tgtLayout, 'targetIcon', 0, 0)
            tgtWidth = icon.EMPTY_ARG_WIDTH if tgtLayout is None else tgtLayout.width
            valuesXOffset = tgtWidth - 1 + bodyWidth - 1
            valueListLayout.mergeInto(layout, valuesXOffset, 0)
            layout.width = valuesXOffset + valueListLayout.width - 1
            layout.targetWidth = tgtWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        if self.sites.targetIcon.att is None:
            target = " "
        else:
            target = self.sites.targetIcon.att.textRepr()
        argText = icon.seriesTextRepr(self.sites.values)
        return target + ' ' + self.op + '=' + ' ' + argText

    def dumpName(self):
        return self.op + '='

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, op=self.op)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        # Get the target and value icons
        if self.sites.targetIcon.att is None:
            raise icon.IconExecException(self, "Missing assignment target")
        tgtAst = self.sites.targetIcon.att.createAst()
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise icon.IconExecException(self, "Missing assignment value")
            values.append(site.att)
        # If there are multiple values, make a tuple out of them
        if len(values) == 1:
            valueAst = values[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in values], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        opAst = opicons.binOpAsts[self.op]()
        return ast.AugAssign(tgtAst, opAst, valueAst, lineno=self.id, col_offset=0)

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        win = self.window
        if siteName == "values" and index == 0:
            # Cursor is on first input site.  Remove icon and replace with cursor
            text = self.op + '='
            valueIcons = [s.att for s in self.sites.values if s.att is not None]
            targetIcon = self.childAt("targetIcon")
            if len(valueIcons) in (0, 1):
                # Zero or one argument, convert to entry icon (with pending arg if
                # there was an argument) attached to name icon
                redrawRegion = comn.AccumRects(self.topLevelParent().hierRect())
                if self.parent() is not None:
                    print('AugmentedAssign has parent?????')
                    return
                if targetIcon is None:
                    win.entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                    win.replaceTop(self, win.entryIcon)
                else:
                    win.entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                    win.replaceTop(self, targetIcon)
                    targetIcon.replaceChild(win.entryIcon, 'attrIcon')
                if len(valueIcons) == 1:
                    win.entryIcon.setPendingArg(valueIcons[0])
            else:
                # Multiple remaining arguments: convert to tuple with entry icon as
                # first element
                redrawRegion = comn.AccumRects(self.topLevelParent().hierRect())
                valueIcons = [s.att for s in self.sites.values if s.att is not None]
                newTuple = listicons.TupleIcon(window=win, noParens=True)
                if targetIcon is None:
                    win.entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                    newTuple.replaceChild(win.entryIcon, "argIcons_0")
                else:
                    win.entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                    targetIcon.replaceChild(win.entryIcon, 'attrIcon')
                    newTuple.replaceChild(targetIcon, 'argIcons_0')
                for i, arg in enumerate(valueIcons):
                    if i == 0:
                        win.entryIcon.setPendingArg(arg)
                    else:
                        self.replaceChild(None, self.siteOf(arg))
                        newTuple.insertChild(arg, "argIcons", i)
                win.replaceTop(self, newTuple)
            win.cursor.setToEntryIcon()
            win.redisplayChangedEntryIcon(evt, redrawRegion.get())
        elif siteName == "values":
            # Cursor is on comma input.  Delete if empty or previous site is empty
            prevSite = iconsites.makeSeriesSiteId(siteName, index - 1)
            childAtCursor = self.childAt(siteId)
            if childAtCursor and self.childAt(prevSite):
                cursors.beep()
                return
            topIcon = self.topLevelParent()
            redrawRegion = comn.AccumRects(topIcon.hierRect())
            if not self.childAt(prevSite):
                self.removeEmptySeriesSite(prevSite)
                win.cursor.setToIconSite(self, prevSite)
            else:
                rightmostIcon = icon.findLastAttrIcon(self.childAt(prevSite))
                rightmostIcon, rightmostSite = cursors.rightmostSite(rightmostIcon)
                self.removeEmptySeriesSite(siteId)
                win.cursor.setToIconSite(rightmostIcon, rightmostSite)
            redrawRegion.add(win.layoutDirtyIcons(filterRedundantParens=False))
            win.refresh(redrawRegion.get())
            win.undo.addBoundary()
