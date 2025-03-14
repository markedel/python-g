# Copyright Mark Edel  All rights reserved
from PIL import Image
import ast
import re
import comn
import icon
import iconlayout
import iconsites
import nameicons
import listicons
import opicons
import entryicon
import expredit

tgtSiteNamePattern = re.compile('targets(\d?)_')

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
 "o o",
 "o o",
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
 "o o",
 "o o",
 "ooo"))

equalImage = comn.asciiToImage( (
 "oooooooooooooooooooo",
 "o                  o",
 "o                  o",
 "o                  o",
 "o                  o",
 "o                  o",
 "o                  o",
 "o     %%%%%%%%     o",
 "o     77777777    o.",
 "o                o..",
 "o     %%%%%%%%    o.",
 "o     77777777     o",
 "o                  o",
 "o                  o",
 "o                  o",
 "o                  o",
 "o                  o",
 "oooooooooooooooooooo"))

class AssignIcon(icon.Icon):
    def __init__(self, numTargets=1, window=None, location=None):
        icon.Icon.__init__(self, window)
        opWidth, opHeight = equalImage.size
        siteY = inpSeqImage.height // 2
        self.opSize = (opWidth, opHeight)
        tgtSitesX = assignDragImage.width - 3
        seqSiteX = tgtSitesX + 6
        self.sites.add('seqIn', 'seqIn', seqSiteX, siteY - inpSeqImage.height // 2)
        self.sites.add('seqOut', 'seqOut', seqSiteX, siteY + inpSeqImage.height // 2 - 1)
        self.sites.add('seqInsert', 'seqInsert', 0, siteY)
        self.tgtLists = [iconlayout.ListLayoutMgr(self, 'targets0', tgtSitesX, siteY,
                simpleSpine=True, allowsTrailingComma=True)]
        valueSitesX = tgtSitesX + icon.EMPTY_ARG_WIDTH + opWidth
        self.valueList = iconlayout.ListLayoutMgr(self, 'values', valueSitesX, siteY,
                simpleSpine=True, allowsTrailingComma=True)
        self.dragSiteDrawn = False
        if location is None:
            x = y = 0
        else:
            x, y = location
        width = assignDragImage.width + self.tgtLists[0].width + opWidth - 2 + \
                self.valueList.width
        self.rect = (x, y, x + width, y + inpSeqImage.height)
        for i in range(1, numTargets):
            self.addTargetGroup(i)
        self.coincidentSite = 'targets0_0'

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        needDragSite = toDragImage is not None and self.prevInSeq() is None
        if self.drawList is None or self.dragSiteDrawn and not needDragSite:
            self.drawList = []
            siteY = self.sites.seqInsert.yOffset
            # Left site (seq site bar + 1st target input or drag-insert site
            leftTgtHasSpine = self.tgtLists[0].simpleSpineWillDraw()
            tgtSiteX = self.sites.targets0[0].xOffset
            if leftTgtHasSpine:
                tgtSiteX -= icon.OUTPUT_SITE_DEPTH
            if needDragSite:
                y = siteY - assignDragImage.height // 2
                self.drawList.append(((0, y), assignDragImage))
            elif not leftTgtHasSpine:
                y = siteY - inpSeqImage.height // 2
                self.drawList.append(((tgtSiteX, y), inpSeqImage))
            # Commas, spines and an = for each target group
            opWidth, opHeight = equalImage.size
            for i, tgtList in enumerate(self.tgtLists):
                self.drawList += tgtList.drawListCommas(tgtSiteX, siteY)
                spines = tgtList.drawSimpleSpine(tgtSiteX, siteY, drawOutputSite=False)
                # We can no longer draw sequence sites on a simple spine, as they are now
                # just beyond the spine edge.  Code below if this becomes possible again.
                # if i == 0 and leftTgtHasSpine:
                #     (leftSpineX, leftSpineY), leftSpineImg = spines[0]
                #     icon.drawSeqSites(self, leftSpineImg, leftSpineX, leftSpineY)
                self.drawList += spines
                tgtSiteX += tgtList.width - 1
                self.drawList.append(((tgtSiteX + icon.OUTPUT_SITE_DEPTH,
                        siteY - opHeight // 2), equalImage))
                tgtSiteX += opWidth - 1
            self.drawList += self.valueList.drawListCommas(tgtSiteX, siteY)
            self.drawList += self.valueList.drawSimpleSpine(tgtSiteX, siteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip, hilightEmptySeries=True,
            allowTrailingComma=True)
        self.dragSiteDrawn = needDragSite

    def addTargetGroup(self, idx):
        if idx < 0 or idx > len(self.tgtLists):
            raise Exception('Bad index for adding target group to assignment icon')
        # Name will be filled in by renumberTargetGroups, offset by layout
        self.tgtLists.insert(idx, iconlayout.ListLayoutMgr(self, 'targetsX', 0, 0,
                simpleSpine=True, allowsTrailingComma=True))
        self.renumberTargetGroups(descending=True)
        self.window.undo.registerCallback(self.removeTargetGroup, idx)
        self.markLayoutDirty()

    def removeTargetGroup(self, idx):
        if idx < 0 or idx >= len(self.tgtLists):
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
                getattr(self.sites, newName).order = i
        self.sites.values.order = len(self.tgtLists)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = icon.Icon.snapLists(self, forCursor=forCursor)
        insertSites = []
        for tgtList in self.tgtLists:
            insertSites += tgtList.makeInsertSnapList()
        insertSites += self.valueList.makeInsertSnapList()
        # Adjust the leftmost list-insert site of targets0 further to the left to
        # deconflict it with the sequence site
        if len(insertSites) > 0 and insertSites[0][2] == 'targets0_0' and \
                not self.tgtLists[0].simpleSpineWillDraw():
            adjX, adjY = insertSites[0][1]
            adjX -= 6
            insertSites[0] = (insertSites[0][0], (adjX, adjY), insertSites[0][2])
        siteSnapLists['insertInput'] = insertSites
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
            tgts = [site.att for site in getattr(self.sites, tgtList.siteSeriesName)]
            if len(tgts) > 1 and tgts[-1] is None:
                tgts = tgts[:-1]
                trailingComma = True
            else:
                trailingComma = False
            for tgt in tgts:
                if tgt is None:
                    raise icon.IconExecException(self, "Missing assignment target(s)")
                if not tgt.canProcessCtx:
                    raise icon.IconExecException(tgt, "Not a valid target for assignment")
            if len(tgts) == 1 and not trailingComma:
                tgtLists.append(tgts[0])
            else:
                tgtLists.append(tgts)
        values = [site.att for site in self.sites.values]
        if len(values) > 1 and values[-1] is None:
            values = values[:-1]
            valuesTrailingComma = True
        else:
            valuesTrailingComma = False
        for value in values:
            if value is None:
                raise icon.IconExecException(self, "Missing assignment value")
        # Make asts for targets and values, adding tuples if packing/unpacking is
        # specified
        if len(values) == 1 and not valuesTrailingComma:
            valueAst = values[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in values], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        tgtAsts = []
        for tgts in tgtLists:
            if isinstance(tgts, list):
                perTgtAsts = [tgt.createAst() for tgt in tgts]
                tgtAst = ast.Tuple(perTgtAsts, ctx=ast.Store(), lineno=self.id,
                    col_offset=0)
            else:
                tgtAst = tgts.createAst()
            tgtAsts.append(tgtAst)
        return ast.Assign(tgtAsts, valueAst, lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = listicons.seriesSaveTextForContext(brkLvl, getattr(self.sites,
            self.tgtLists[0].siteSeriesName), contNeeded, export, 'store',
            allowTrailingComma=True, allowEmpty=False)
        text.add(None, " = ")
        for tgtList in self.tgtLists[1:]:
            tgtText = listicons.seriesSaveTextForContext(brkLvl,
                getattr(self.sites, tgtList.siteSeriesName), contNeeded, export, 'store',
                allowTrailingComma=True, allowEmpty=False)
            text.concat(brkLvl, tgtText, contNeeded)
            text.add(None, " = ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export,
            allowTrailingComma=True, allowEmpty=False)
        return text

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
        self.sites.seqIn.yOffset = leftSpineTop
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
        tgtListsLayouts = [tgtList.calcLayouts(argRequired=True)
            for tgtList in self.tgtLists]
        valueLayouts = self.valueList.calcLayouts(argRequired=True)
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

    def duplicate(self, linkToOriginal=False):
        ic = AssignIcon(numTargets=len(self.tgtLists), window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def highlightErrors(self, errHighlight):
        if errHighlight is not None:
            icon.Icon.highlightErrors(self, errHighlight)
            return
        self.errHighlight = None
        for tgtList in self.tgtLists:
            tgtSeries = getattr(self.sites, tgtList.siteSeriesName)
            listicons.highlightSeriesErrorsForContext(tgtSeries, 'store')
        for site in self.sites.values:
            if site.att is not None:
                site.att.highlightErrors(None)

    def textRepr(self):
        text = ""
        for tgtList in self.tgtLists:
            text += icon.seriesTextRepr(getattr(self.sites, tgtList.siteSeriesName)) + \
                    " = "
        return text + icon.seriesTextRepr(self.sites.values)

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        topIcon = self.topLevelParent()
        win = self.window
        win.requestRedraw(topIcon.hierRect())
        #... There's an ugly hack, here, which happened because the original code was
        #    written to replace the = with a comma (before entry icon backspacing was
        #    established).  Instead of rewriting the code, I just added calls to
        #    backspaceComma after the existing code.  This is wastefull, and will fail if
        #    backspaceComma ever adds comma text to the entry icon, which might happen.
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
                self.replaceWith(newTuple)
                cursorSite = iconsites.makeSeriesSiteId('argIcons', numTargets)
                win.cursor.setToIconSite(newTuple, cursorSite)
                newTuple.backspace(cursorSite, evt)  # Also handles num args <= 1 case
            else:
                # Merge lists around '=' to convert it to ','
                if siteName == "values":
                    removetgtGrpIdx = len(self.tgtLists) - 1
                    srcSite = "targets%d" % removetgtGrpIdx
                    destSite = "values"
                    destIdx = 0
                    cursorIdx = len(getattr(self.sites, srcSite))
                else:
                    srcSite = siteName
                    removetgtGrpIdx = int(siteName[7:])
                    destSite = siteName[:7] + str(removetgtGrpIdx - 1)
                    destIdx = len(getattr(self.sites, destSite))
                    cursorIdx = destIdx
                argIcons = [s.att for s in getattr(self.sites, srcSite)]
                removeFromSite = iconsites.makeSeriesSiteId(srcSite, 0)
                for _ in argIcons:
                    self.replaceChild(None, removeFromSite)
                self.insertChildren(argIcons, destSite, destIdx, preserveNoneAtZero=True)
                self.removeTargetGroup(removetgtGrpIdx)
                cursorSite = iconsites.makeSeriesSiteId(destSite, cursorIdx)
                win.cursor.setToIconSite(self, cursorSite)
                listicons.backspaceComma(self, cursorSite, evt)
        else:
            # Cursor is on comma input.  Delete if empty or previous site is empty
            listicons.backspaceComma(self, siteId, evt)
            return

    def drawListIdxToPartId(self, idx):
        # Give consistent partIds to '=' (3,6,9,12...) regardless of whether spines and
        # connectors (1,2, 4,5, 7,8) are drawn.  Commas, per partId convention, always
        # return 0, as they have a visual presence, but are not used for picking.
        if self.drawList[idx][1] is icon.commaImage:
            return 0
        partId = 0
        for i in range(idx + 1):
            img = self.drawList[i][1]
            if img is icon.commaImage or img is icon.commaTypeoverImage:
                continue
            if img is equalImage:
                partId += 3 - (partId % 3)
            else:
                partId += 1  # Spine
        return partId

    def siteRightOfPart(self, partId):
        clause = (partId - 1) // 3
        numTgtLists = len(self.tgtLists)
        partType = (partId - 1) % 3
        if clause < numTgtLists:
            # Target clause or = following target clause
            if partType == 0:
                # left spine of a target list
                return 'targets%d_0' % clause
            if clause < numTgtLists - 1:
                # Right spine or = preceding another target clause
                return 'targets%d_0' % (clause + 1)
        # Values clause or right spine or = following last target clause
        return 'values_0'

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
        seqX = icon.dragSeqImage.width - 1 + icon.SEQ_SITE_OFFSET
        self.sites.add('seqIn', 'seqIn', seqX, 0)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-1)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.targetWidth = icon.EMPTY_ARG_WIDTH
        argX = icon.dragSeqImage.width + self.targetWidth + bodyWidth
        self.valuesList = iconlayout.ListLayoutMgr(self, 'values', argX, siteYOffset,
                simpleSpine=True, allowsTrailingComma=True)
        totalWidth = argX + self.valuesList.width - 2
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.coincidentSite = 'targetIcon'

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
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
            bodyTopY = self.sites.seqIn.yOffset
            self.drawList.append(((bodyOffset, bodyTopY), img))
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - icon.OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valuesList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valuesList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        self._drawEmptySites(toDragImage, clip, hilightEmptySeries=True,
            allowTrailingComma=True)

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
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 1
        height = heightAbove + heightBelow
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, left, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        valueListLayouts = self.valuesList.calcLayouts(argRequired=True)
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

    def duplicate(self, linkToOriginal=False):
        ic = AugmentedAssignIcon(op=self.op, window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def highlightErrors(self, errHighlight):
        if errHighlight is None:
            self.errHighlight = None
            listicons.highlightErrorsForContext(self.sites.targetIcon, "store",
                restrictToSingle=True)
            for site in self.sites.values:
                if site.att is not None:
                    site.att.highlightErrors(None)
        else:
            icon.Icon.highlightErrors(self, errHighlight)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        # Get the target and value icons
        tgtIc = self.sites.targetIcon.att
        if tgtIc is None:
            raise icon.IconExecException(self, "Missing assignment target")
        if not tgtIc.canProcessCtx:
            raise icon.IconExecException(tgtIc, "Not a valid target for assignment")
        if isinstance(tgtIc, listicons.ListIcon):
            # List icons are ok in storage context, but not augmented assign
            raise icon.IconExecException(tgtIc,
                "List is not a valid target for augmented assignment")
        tgtAst = self.sites.targetIcon.att.createAst()
        values = [site.att for site in self.sites.values]
        if len(values) > 1 and values[-1] is None:
            values = values[:-1]
            trailingComma = True
        else:
            trailingComma = False
        for value in values:
            if value is None:
                raise icon.IconExecException(self, "Missing assignment value")
        # If there are multiple values, make a tuple out of them
        if len(values) == 1 and not trailingComma:
            valueAst = values[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in values], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        opAst = opicons.binOpAsts[self.op]()
        return ast.AugAssign(tgtAst, opAst, valueAst, lineno=self.id, col_offset=0)

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        brkLvl = parentBreakLevel + 1
        text = listicons.argSaveTextForContext(brkLvl, self.sites.targetIcon, contNeeded,
            export, 'store')
        text.add(None, " " + self.op + "= ")
        icon.addSeriesSaveText(text, brkLvl, self.sites.values, contNeeded, export,
            allowTrailingComma=True, allowEmpty=False)
        return text

    def backspace(self, siteId, evt):
        siteName, index = iconsites.splitSeriesSiteId(siteId)
        if siteName == "values" and index == 0:
            # Cursor is on first input site.  Remove icon and replace with entry icon
            entryIcon = self._becomeEntryIcon()
            self.window.cursor.setToText(entryIcon, drawNew=False)
        elif siteName == "values":
            # Cursor is on comma input.  Delete if empty or previous site is empty
            listicons.backspaceComma(self, siteId, evt)

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        if clickPos is not None:
            textOriginX = self.rect[0] + icon.dragSeqImage.width - 1 + \
                self.targetWidth - 1 + icon.TEXT_MARGIN
            textOriginY = self.rect[1] + self.sites.targetIcon.yOffset
            cursorTextIdx, cursorWindowPos = icon.cursorInText(
                (textOriginX, textOriginY), clickPos, icon.globalFont, self.op + '=')
            if cursorTextIdx is None:
                return None, None
            entryIcon = self._becomeEntryIcon()
            entryIcon.setCursorPos(cursorTextIdx)
            return entryIcon, cursorWindowPos
        if siteAfter is None or siteAfter == 'values_0':
            return self._becomeEntryIcon()
        return None

    def _becomeEntryIcon(self):
        win = self.window
        text = self.op + '='
        valueIcons = [s.att for s in self.sites.values if s.att is not None]
        targetIcon = self.childAt("targetIcon")
        if len(valueIcons) in (0, 1):
            # Zero or one argument, convert to entry icon (with pending arg if
            # there was an argument) attached to name icon
            win.requestRedraw(self.topLevelParent().hierRect(),
                filterRedundantParens=True)
            if self.parent() is not None:
                print('AugmentedAssign has parent?????')
                return
            entryIcon = entryicon.EntryIcon(initialString=text, window=win)
            if targetIcon is None:
                win.replaceTop(self, entryIcon)
            else:
                self.replaceChild(None, 'targetIcon')
                win.replaceTop(self, targetIcon)
                targetIcon.replaceChild(entryIcon, 'attrIcon')
            if len(valueIcons) == 1:
                entryIcon.appendPendingArgs([valueIcons[0]])
        else:
            # Multiple remaining arguments: convert to tuple with entry icon as
            # first element
            win.requestRedraw(self.topLevelParent().hierRect(),
                filterRedundantParens=True)
            valueIcons = [s.att for s in self.sites.values if s.att is not None]
            newTuple = listicons.TupleIcon(window=win, noParens=True)
            if targetIcon is None:
                entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                newTuple.replaceChild(entryIcon, "argIcons_0")
            else:
                entryIcon = entryicon.EntryIcon(initialString=text, window=win)
                targetIcon.replaceChild(entryIcon, 'attrIcon')
                newTuple.replaceChild(targetIcon, 'argIcons_0')
            for i, arg in enumerate(valueIcons):
                if i == 0:
                    entryIcon.appendPendingArgs([arg])
                else:
                    self.replaceChild(None, self.siteOf(arg))
                    newTuple.insertChild(arg, "argIcons", i)
            win.replaceTop(self, newTuple)
        return entryIcon

    def siteRightOfPart(self, partId):
        if partId == 1:
            return 'targetIcon'
        return 'values_0'

def insertAssignIcon(atIcon, atSite, insertedAssign):
    if isinstance(atIcon, AssignIcon):
        return combineAssignIcons(atIcon, atSite, insertedAssign)
    elif isinstance(atIcon, listicons.TupleIcon) and atIcon.noParens:
        return insertAssignInNakedTuple(atIcon, atIcon, atSite, insertedAssign)
    else:
        enclosingIc, splitSite = entryicon.findEnclosingSite(atIcon)
        if isinstance(enclosingIc, AssignIcon):
            return combineAssignIcons(atIcon, atSite, insertedAssign)
        elif isinstance(enclosingIc, listicons.TupleIcon) and enclosingIc.noParens:
            return insertAssignInNakedTuple(enclosingIc, atIcon, atSite, insertedAssign)
        else:
            print('insertAssignIcon did not find assign or naked tuple icon')
            return atIcon, atSite

def insertAssignInNakedTuple(tupleIc, atIcon, atSite, insertedAssign):
    # Split the expression holding the insert site
    entries = tupleIc.argIcons()
    if atIcon is tupleIc:
        splitSite = atSite
    else:
        splitSite = tupleIc.siteOf(atIcon, recursive=True)
    _, splitIdx = iconsites.splitSeriesSiteId(splitSite)
    left, right = entryicon.splitExprAtSite(atIcon, atSite, tupleIc)
    # Strip icons off of the tuple
    for _ in entries:
        tupleIc.replaceChild(None, 'argIcons_0')
    # Replace it with the new assignment icon
    tupleIc.window.replaceTop(tupleIc, insertedAssign)
    # Add icons left of split to the start of the existing targets0 series
    expredit.insertListAtSite(insertedAssign, 'targets0_0', (left,))
    insertedAssign.insertChildren(entries[:splitIdx], 'targets0_0')
    # Add icons right of the split to the end of the values series
    rightIc, rightSite = icon.rightmostSite(insertedAssign)
    if right is None:
        cursorIc, cursorSite = rightIc, rightSite
    else:
        cursorIc, cursorSite = expredit.insertListAtSite(rightIc, rightSite, (right,))
    nextValuesIdx = len(insertedAssign.sites.values)
    insertedAssign.insertChildren(entries[splitIdx+1:], 'values',nextValuesIdx)
    return cursorIc, cursorSite

def combineAssignIcons(atIcon, atSite, insertedAssign):
    if isinstance(atIcon, AssignIcon):
        assignIc = atIcon
        splitSite = atSite
    else:
        assignIc, splitSite = entryicon.findEnclosingSite(atIcon)
        if not isinstance(assignIc, AssignIcon):
            print('combineAssignIcons did not find assign icon')
            return atIcon, atSite
    # Strip the inserted icon of its entries
    entries = []
    for tgtList in insertedAssign.tgtLists:
        tgts = [site.att for site in getattr(insertedAssign.sites, tgtList.siteSeriesName)]
        tgtsSite = iconsites.makeSeriesSiteId(tgtList.siteSeriesName, 0)
        for _ in tgts:
            insertedAssign.replaceChild(None, tgtsSite)
        entries.append(tgts)
    values = [site.att for site in insertedAssign.sites.values]
    for _ in values:
        insertedAssign.replaceChild(None, 'values_0')
    entries.append(values)
    # Split the expression across atSite
    left, right = entryicon.splitExprAtSite(atIcon, atSite, assignIc)
    # Insert the entries removed from the inserted icon into assignIc
    splitSeriesName, splitIdx = iconsites.splitSeriesSiteId(splitSite)
    numInsGroups = len(entries) - 1
    if splitSeriesName == 'values':
        # Assign icon was inserted in the value series.  Turn the values before the
        # insertion site into targets, add new targets for..., and insert the last set
        # of elements at the start of the values series
        iconsToMove = [site.att for site in assignIc.sites.values][:splitIdx]
        for _ in range(splitIdx+1):
            assignIc.replaceChild(None, 'values_0')
        newTgtGrpIdxs = [len(assignIc.tgtLists) + i for i in range(numInsGroups)]
        for newTgtGrpIdx in newTgtGrpIdxs:
            assignIc.addTargetGroup(newTgtGrpIdx)
        iconsToMove.append(left)
        firstNewTgtGrp = f"targets{newTgtGrpIdxs[0]}"
        assignIc.insertChildren(iconsToMove, firstNewTgtGrp, 0)
        expredit.insertListAtSite(*icon.rightmostFromSite(assignIc,
             iconsites.makeSeriesSiteId(firstNewTgtGrp, splitIdx)), entries[0])
        for i, grpIdx in enumerate(newTgtGrpIdxs[1:]):
            grpStartSiteId = f"targets{grpIdx}_0"
            assignIc.insertChildren(entries[i + 1], grpStartSiteId)
        assignIc.insertChildren(entries[-1], 'values_0')
        lastInsSite = iconsites.makeSeriesSiteId('values', len(entries[-1]) - 1)
        rightOfInsId, rightOfInsSite = icon.rightmostFromSite(assignIc, lastInsSite)
        if right is not None:
            expredit.insertListAtSite(rightOfInsId, rightOfInsSite, (right,))
    else:
        # Assign icon was inserted in a target series.  The inserted clauses all become
        # targets..
        assignIc.replaceChild(left, splitSite, leavePlace=True)
        series = getattr(assignIc.sites, splitSeriesName)
        iconsToMove = [site.att for site in series][splitIdx + 1:]
        removeFromSite = iconsites.makeSeriesSiteId(splitSeriesName, splitIdx + 1)
        for _ in range(splitIdx + 1, len(series)):
            assignIc.replaceChild(None, removeFromSite)
        expredit.insertListAtSite(*icon.rightmostFromSite(assignIc, splitSite), entries[0])
        newTgtGrpIdxs = [int(splitSeriesName[7:]) + 1 + i for i in range(numInsGroups)]
        for newTgtGrpIdx in newTgtGrpIdxs:
            assignIc.addTargetGroup(newTgtGrpIdx)
        for i, groupIdx in enumerate(newTgtGrpIdxs):
            grpStartSiteId = f"targets{groupIdx}_0"
            assignIc.insertChildren(entries[i+1], grpStartSiteId)
        lastInsSite = f"targets{newTgtGrpIdxs[-1]}_{len(entries[-1])-1}"
        rightOfInsId, rightOfInsSite = icon.rightmostFromSite(assignIc, lastInsSite)
        if right is not None:
            expredit.insertListAtSite(rightOfInsId, rightOfInsSite, (right,))
        assignIc.insertChildren(iconsToMove, iconsites.nextSeriesSiteId(lastInsSite))
    return rightOfInsId, rightOfInsSite

def splitAssignAtTargetSite(assignIc, atIcon, atSite):
    """Split an assignment statement into two statements at (atIcon, atSite).  Note that
    this only handles splitting at sites attached to assignIc at its target sites (this
    is used by the more general expredit.splitStmtAtSite, which has common code for
    splitting icons with series' that are unconstrained on the right).  The calling code
    is also expected to have verified that there is no enclosing icon separating the
    specified site from the assignment icon.  assignIc can be on augmented assignment
    icon.  The fact that Python does not support expressions in the target of an
    augmented assign, makes this is kind of useless, but Python-g does, so it needs to be
    supported for completeness (the ability to split between the target and the operator
    actually is useful)."""
    if isinstance(assignIc, AugmentedAssignIcon):
        left, right = entryicon.splitExprAtSite(atIcon, atSite, assignIc)
        if left is None:
            return assignIc, None
        assignIc.replaceChild(right, 'targetIcon')
        icon.insertSeq(left, assignIc, before=True)
        assignIc.window.addTop(left)
        return left, assignIc
    if atIcon is assignIc:
        splitSite = atSite
        if atSite == 'targets0_0':
            return assignIc, None  # Splitting left of icon is a noop
    else:
        splitSite = assignIc.siteOf(atIcon, recursive=True)
        if splitSite is None or splitSite[:7] != 'targets':
            print("splitAssignAtTargetSite failed to find assign icon or expected site")
            return assignIc, None
    tgtGrpIdx = getTgtGrpIdx(splitSite)
    seriesName, seriesIdx = iconsites.splitSeriesSiteId(splitSite)
    left, right = entryicon.splitExprAtSite(atIcon, atSite, assignIc)
    siteSeries = getattr(assignIc.sites, seriesName)
    iconsForValuesSeries = [site.att for site in siteSeries[:seriesIdx]]
    leftSeriesSite = iconsites.makeSeriesSiteId(seriesName, 0)
    for _ in range(seriesIdx):
        assignIc.replaceChild(None, leftSeriesSite)
    assignIc.replaceChild(right, leftSeriesSite)
    if left is not None:
        iconsForValuesSeries.append(left)
    if tgtGrpIdx == 0:
        # We're splitting the first target group, so no group removal or shifting
        # necessary, and the new stmt will be either a naked tuple, or an individual
        if len(iconsForValuesSeries) == 1:
            newStmt = iconsForValuesSeries[0]
        else:
            newStmt = listicons.TupleIcon(assignIc.window, noParens=True)
            newStmt.insertChildren(iconsForValuesSeries, 'argIcons_0')
        icon.insertSeq(newStmt, assignIc, before=True)
        assignIc.window.addTop(newStmt)
        return newStmt, assignIc
    # We're splitting a target group other than group 0, so we need to make a new
    # assignment icon and transfer everything left of the split site, to it.
    newAssignStmt = AssignIcon(numTargets=tgtGrpIdx, window = assignIc.window)
    icon.insertSeq(newAssignStmt, assignIc, before=True)
    assignIc.window.addTop(newAssignStmt)
    newAssignStmt.insertChildren(iconsForValuesSeries, 'values_0')
    for idx in range(tgtGrpIdx):
        iconsToMove = [site.att for site in getattr(assignIc.sites, 'targets0')]
        for _ in iconsToMove:
            assignIc.replaceChild(None, 'targets0_0')
        assignIc.removeTargetGroup(0)
        leftSeriesSite = iconsites.makeSeriesSiteId('targets' + str(idx), 0)
        newAssignStmt.insertChildren(iconsToMove, leftSeriesSite)
    return newAssignStmt, assignIc

def joinAssignIcons(stmt1, stmt2):
    stmt1Comment = stmt1.hasStmtComment()
    stmt2Comment = stmt2.hasStmtComment()
    stmt1.window.replaceTop(stmt2, None)
    rightmostIc, rightmostSite = icon.rightmostSite(stmt1)
    combineAssignIcons(rightmostIc, rightmostSite, stmt2)
    # Merge any statement comments associated with the two statements
    if stmt1Comment is not None and stmt2Comment is not None:
        stmt1Comment.mergeTextFromComment(stmt2Comment)
    elif stmt2Comment is not None:
        stmt2Comment.attachStmtComment(stmt1)
    return rightmostIc, rightmostSite

def joinToAssignIcon(toStmt, assignIcon):
    """Implement join command between a statement compatible with an assignIcon's target
    field (toStmt) on the left, with an assignment icon (assignIcon) on the right.  A
    compatible statement is any icon at the top level with an output site."""
    toStmtComment = toStmt.hasStmtComment()
    assignStmtComment = assignIcon.hasStmtComment()
    toStmt.window.replaceTop(toStmt, None)
    if isinstance(assignIcon, AugmentedAssignIcon):
        cursorIcAndSite = expredit.insertAtSite(assignIcon, 'targetIcon', toStmt)
    elif isinstance(toStmt, listicons.TupleIcon) and toStmt.noParens:
        argIcons = toStmt.argIcons()
        for _ in argIcons:
            toStmt.replaceChild(None, 'argIcons_0')
        cursorIcAndSite = expredit.insertListAtSite(assignIcon, 'targets0_0', argIcons)
    elif hasattr(toStmt, 'closed') and not toStmt.closed:
        return expredit.insertAtSite(assignIcon, 'targets0_0', toStmt)
    else:
        cursorIcAndSite = expredit.insertListAtSite(assignIcon, 'targets0_0', (toStmt,))
    # Merge any statement comments associated with the two statements
    if toStmtComment is not None and assignStmtComment is not None:
        assignStmtComment.mergeTextFromComment(toStmtComment, before=True)
    elif toStmtComment is not None:
        toStmtComment.attachStmtComment(assignIcon)
    return cursorIcAndSite

def getTgtGrpIdx(siteName):
    match = tgtSiteNamePattern.match(siteName)
    return int(match.group(1))

def createAssignIconFromAst(astNode, window):
    topIcon = AssignIcon(len(astNode.targets), window)
    for i, tgt in enumerate(astNode.targets):
        if isinstance(tgt, ast.Tuple) and not hasattr(tgt, 'tupleHasParens'):
            tgtIcons = [icon.createFromAst(t, window) for t in tgt.elts]
            if len(tgtIcons) == 1:
                tgtIcons.append(None)  # Trailing comma syntax allowed w/o parens
        else:
            tgtIcons = [icon.createFromAst(tgt, window)]
        topIcon.insertChildren(tgtIcons, "targets%d" % i, 0)
    if isinstance(astNode.value, ast.Tuple) and not \
            hasattr(astNode.value, 'tupleHasParens'):
        valueIcons = [icon.createFromAst(v, window) for v in astNode.value.elts]
        topIcon.insertChildren(valueIcons, "values", 0)
        if len(valueIcons) == 1:
            topIcon.insertChild(None, "values", 1)
    else:
        topIcon.replaceChild(icon.createFromAst(astNode.value, window), "values_0")
    return topIcon
icon.registerIconCreateFn(ast.Assign, createAssignIconFromAst)

def createAugmentedAssignIconFromAst(astNode, window):
    assignIcon = AugmentedAssignIcon(opicons.binOps[astNode.op.__class__], window)
    targetIcon = icon.createFromAst(astNode.target, window)
    assignIcon.replaceChild(targetIcon, "targetIcon")
    if isinstance(astNode.value, ast.Tuple):
        valueIcons = [icon.createFromAst(v, window) for v in astNode.value.elts]
        assignIcon.insertChildren(valueIcons, "values", 0)
        if len(valueIcons) == 1:
            assignIcon.insertChild(None, "values", 1)
    else:
        assignIcon.replaceChild(icon.createFromAst(astNode.value, window), "values_0")
    return assignIcon
icon.registerIconCreateFn(ast.AugAssign, createAugmentedAssignIconFromAst)
