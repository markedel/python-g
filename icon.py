# Copyright Mark Edel  All rights reserved
from PIL import Image, ImageDraw, ImageFont, ImageMath
import comn
import iconlayout
import iconsites
import filefmt
import ast

# Some general notes on drawing and layout:
#
# PIL (Pillow) uses pixel grid coordinates, as opposed to pixel centered, meaning that
# 0,0 is at the top left corner of the top left pixel, not in the center of the pixel.
#
# An icon's rectangle (rect) is a rectangle covering the entire drawn area of the icon.
# It is used to determine whether the icon should be involved in any drawing operation
# at a particular location in a window.  If redrawing is needed outside of the icon's
# rectangle, the icon can safely be ignored.
#
# Icons also have a selection rectangle (.selectionRect()) which defines the "primary"
# area of the icon for the purpose of extending a selection from it, and various calls
# for more precisely determining whether a clicked or dragged point is on the icon.
#
# Layout coordinates (used in calcLayouts) are simplified to boxes with attachment sites
# along their edges.  An icon's layout provides a width and height that it and its
# children wish to occupy, but omits protruding sites that can be safely overlaid by
# another icon.
#
# A confusing aspect of the code is that mating icons are intended to overlap by one
# pixel at the edges, so size calculations are peppered with -1 (the convention in the
# code is to explicitly write a -1 for each overlap, rather than coalescing them in to
# a single constant).
#
# This prototype code, is much more pixel-oriented than it should be, given the current
# variety of higher density displays, which may make it difficult to port to such an
# environment.
globalFont = ImageFont.truetype('c:/Windows/fonts/arial.ttf', 12)
boldFont = ImageFont.truetype('c:/Windows/fonts/arialbd.ttf', 12)
textFont = ImageFont.truetype('c:/Windows/fonts/consola.ttf', 13)

stmtAstClasses = {ast.Assign, ast.AugAssign, ast.While, ast.For, ast.AsyncFor, ast.If,
 ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Return, ast.With,
 ast.AsyncWith, ast.Delete, ast.Pass, ast.Continue, ast.Break, ast.Global, ast.Nonlocal,
 ast.Import, ast.ImportFrom, ast.Raise, ast.Assert}

# Site depths are offsets from the icon (left or right) border.  Sequence sites were
# originally positioned 1 pixel in from the left and bottom border, which led to the
# confusing and now deprecated use of SEQ_SITE_DEPTH as a negative number.  Sequence
# sites are now positioned directly on the bottom icon border and 3 pixels from the left
# border of most icons, with a few having more 'overhang' for additional graphics (we
# align the always-drawn parts and allow the more ephemeral border parts to float)
ATTR_SITE_DEPTH = 1
OUTPUT_SITE_DEPTH = 2
SEQ_SITE_OFFSET = 3
SEQ_SITE_DEPTH = -SEQ_SITE_OFFSET

siteDepths = {'input':OUTPUT_SITE_DEPTH, 'output':OUTPUT_SITE_DEPTH,
        'attrOut':ATTR_SITE_DEPTH, 'attrIn':ATTR_SITE_DEPTH,
        'seqIn':SEQ_SITE_DEPTH, 'seqInsert':4, 'cprhIn':0, 'cprhOut':0}

TEXT_MARGIN = 2

# The rendered color for outlines when drawn
SHOW_OUTLINE_TINT = (220, 220, 220, 255)

KEYWORD_COLOR = (48, 0, 128, 255)
TYPEOVER_COLOR = (220, 220, 220, 255)
SELECT_TINT = (0, 0, 255, 40)
EXEC_ERR_TINT = (255, 0, 0, 100)
SYNTAX_ERR_TINT = (255, 64, 64, 40)
TYPE_ANN_TINT = (255, 255, 255, 128)
PENDING_REMOVE_TINT = (255, 10, 10, 100)
IMMEDIATE_COPY_TINT = (0, 180, 255, 40)
BLACK = (0, 0, 0, 255)
SEQ_RULE_COLOR = (165, 180, 165, 255)
SEQ_CONNECT_COLOR = (220, 220, 220, 255)
EMPTY_ARG_COLOR = (255, 0, 0, 30)

EMPTY_ARG_WIDTH = 11
LIST_EMPTY_ARG_WIDTH = 8
TRAILING_EMPTY_ARG_WIDTH = 0

# Options for (post layout) icon drawing
STYLE_OUTLINE = 1
STYLE_SELECTED = 2
STYLE_SYNTAX_ERR = 4
STYLE_EXEC_ERR = 8
STYLE_PENDING_REMOVE = 16
STYLE_IMMEDIATE_COPY = 32
STYLE_TYPE_ANN = 64

# Pixel offset from input/output site to series insertion site.  Corresponds to the dot
# of the comma symbol.  (Note that this is dynamically repositioned at the left and right
# edges of most series icons)
SERIES_INSERT_SITE_X_OFFSET = -4
SERIES_INSERT_SITE_Y_OFFSET = 5

# X distance in pixels from left edge of icon for the icon replacement site.
REPLACE_SITE_X_OFFSET = 8
# Y distance in pixels from (center-adjusted) parent site to icon replacement site.
# Replace sites were originally lower, to give better visibility of the replacement vs
# the dragged icons, but for better site separation for snapping, they are now directly
# right of the prefix-insert site.
REPLACE_SITE_Y_OFFSET = 0

# X distance in pixels from left edge of icon for the additional icon replacement site
# (automatically added by iconsites.makeSnapLists for statement-level icons)
STMT_REPLACE_SITE_X_OFFSET = -16

# Pixels below input/output site to place attribute site
# This should be based on font metrics, but for the moment, we have a hard-coded cursor
ATTR_SITE_OFFSET = 4

# How far (pixels in addition to dragSeqImage.width) to the right of a statement to place
# the statement comment
STMT_COMMENT_OFFSET = 4

# Number of pixels of vertical space left below a block-owning icon and the first icon of
# the block.  This is usually filled by the sequence 'bump' or connector below the icon,
# but may be empty when the statement arguments take up more vertical space, and elevate
# the seqOut site above the bottom of the space allocated for the statement.
BLOCK_SEQ_MARGIN = 2

outSiteImage = comn.asciiToImage((
 "..o",
 ".o ",
 "o  ",
 ".o ",
 "..o"))

inSiteImage = comn.asciiToImage((
 "  o",
 " o.",
 "o..",
 " o.",
 "  o"))

inSiteMask = comn.asciiToImage((
 "..%",
 ".%%",
 "%%%",
 ".%%",
 "..%"))

attrOutImage = comn.asciiToImage((
 "%%",
 "%%"))

dimAttrOutImage = comn.asciiToImage((
 "oo",
 "oo"))

attrInImage = comn.asciiToImage((
 "o.",
 "o."))

leftInSiteImage = comn.asciiToImage((
 "...o ",
 "..o  ",
 ".o  o",
 "o  o.",
 "o o..",
 "o  o.",
 ".o  o",
 "..o  ",
 "...o "))

commaImage = comn.asciiToImage((
 "ooooooooo",
 "o       o",
 "o      o.",
 "o     o..",
 "o      o.",
 "o       o",
 "o       o",
 "o %7    o",
 "o8%7    o",
 "o%8     o",
 "o       o",
 "ooooooooo"))
commaImageSiteYOffset = 3

commaTypeoverImage = comn.asciiToImage((
 "ooooooooo",
 "o       o",
 "o      o.",
 "o     o..",
 "o      o.",
 "o       o",
 "o       o",
 "o 89    o",
 "o 89    o",
 "o8      o",
 "o       o",
 "ooooooooo"))

colonImage = comn.asciiToImage((
 "ooooo",
 "o   o",
 "o   o",
 "o%% o",
 "o%%o.",
 "o o..",
 "o  o.",
 "o%% o",
 "o%% o",
 "o   o",
 "ooooo"))
colonImageSiteYOffset = 5

lSimpleSpineImage = comn.asciiToImage((
 "..ooo",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..o7o",
 "..ooo"))
simpleSpineExtendDupRows = 9,

rSimpleSpineImage = comn.asciiToImage((
 "ooo",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "o7o",
 "ooo"))

# Sequence insert sites were originally drawn by the draw() methods, but since we've
# changed to a single-active-site model for dragging, we don't want these sites showing
# up on icons that won't actually snap.  However, we do still want icons to reserve space
# for the marker that extends to the site, hence (for now) this mostly-empty image.
dragSeqImage = comn.asciiToImage((
 "....o",
 "....o",
 "....o",
 "....o",
 "....o"))

branchFootImage = comn.asciiToImage((
 "ooooooooooooooooooooooooooo",
 "ooo                     ooo",
 "ooooooooooooooooooooooooooo"))

seqOutBumpImage = comn.asciiToImage((
 "o  o  o",
 "o ooo o",
 "ooooooo"))

emptyImage = Image.new('RGBA', (0, 0))

renderCache = {}

# Icon to insert when createIconFromAst fails (set by registerAstDecodeFallback())
astDecodeFallback = None
# Table mapping Python ASTs to functions registered to create icons from them.
astCreationFunctions = {}

def iconsFromClipboardString(clipString, window, offset):
    try:
        clipData = ast.literal_eval(clipString)
    except:
        return None
    allIcons = []
    for clipSeq in clipData:
        prevIc = None
        seqIcons = clipboardDataToIcons(clipSeq, window, offset)
        branchStack = []
        for ic in seqIcons:
            if prevIc is not None:
                ic.replaceChild(prevIc, 'seqIn')
            prevIc = ic
            if hasattr(ic, 'blockEnd'):
                branchStack.append(ic)
            elif isinstance(ic, BlockEnd):
                if len(branchStack) == 0:
                    print("Unbalanced branches in clipboard data")
                else:
                    branchIc = branchStack.pop()
                    branchIc.blockEnd = ic
                    ic.primary = branchIc
            ic.markLayoutDirty()
        if len(branchStack) != 0:
            print("Unbalanced branches in clipboard data")
        allIcons += seqIcons
    return allIcons

def clipboardDataToIcons(clipData, window, offset):
    subclasses = _getIconClasses()
    pastedIcons = []
    for clipIcon in clipData:
        if clipIcon is None:
            pastedIcons.append(None)
        else:
            iconClassName, *iconData = clipIcon
            iconClass = subclasses[iconClassName]
            iconData = (iconClass, *iconData)
            pastedIcons.append(Icon.fromClipboard(iconData, window, offset))
    return pastedIcons

def iconBoxedText(text, font=globalFont, color=BLACK, typeover=None):
    if typeover is None and (text, font, color) in renderCache:
        txtImg = renderCache[(text, font, color)]
    else:
        width, height = font.getsize(text)
        if height < minTxtHgt:
            height = minTxtHgt
        width += 2 * TEXT_MARGIN + 1
        height += 2 * TEXT_MARGIN + 1
        txtImg = Image.new('RGBA', (width, height), color=comn.ICON_BG_COLOR)
        draw = ImageDraw.Draw(txtImg)
        if typeover is None:
            draw.text((TEXT_MARGIN, TEXT_MARGIN), text, font=font, fill=color)
        else:
            typeoverOffset = getTextSize(text[:typeover], font)[0]
            draw.text((TEXT_MARGIN, TEXT_MARGIN), text[:typeover], font=font, fill=color)
            draw.text((TEXT_MARGIN + typeoverOffset, TEXT_MARGIN), text=text[typeover:],
                font=font, fill=TYPEOVER_COLOR)
        draw.rectangle((0, 0, width-1, height-1), fill=None, outline=comn.OUTLINE_COLOR)
        if typeover is None:
            renderCache[(text, font, color)] = txtImg
    return txtImg

textSizeCache = {}
def getTextSize(text, font=globalFont):
    key = text, font
    size = textSizeCache.get(key)
    if size is None:
        size = textSizeCache[key] = font.getsize(text)
    return size

# Sadly, hand drawn components are drawn in pixels rather than being dynamically based
# on font size, so the font can not be arbitrarily enlarged or reduced without hurting
# appearance.  The eventual, non-prototype, version of this will need to have higher
# resolution pixmaps for these, and scale them to match the chosen font.
minTxtIconHgt = 18
minTxtHgt = minTxtIconHgt - 2 * TEXT_MARGIN - 1

class IconExecException(Exception):
    def __init__(self, ic, exceptionText):
        self.icon = ic
        self.message = exceptionText
        super().__init__(self.message)

class Icon:

    # Icons that can be used in store and del contexts will override this to be True
    canProcessCtx = False

    # Icon classes can set this to provide static html reference(s) to the Python
    # documentation, that will appear in the context-sensitive icon menu.  Icons that
    # need to actively select references should provide a getDocRef() method, instead.
    # The format is a list of tuples, each containing two items: 1) the menu item name
    # (not including the leading 'Doc:', part), and 2) the html reference including
    # location of the .html file in the (Windows) .chm document collection in href form,
    # for example: [("del Statement", "reference/simple_stmts.html#the-del-statement")]
    pythonDocRef = None

    def __init__(self, window=None, canProcessCtx=False):
        self.window = window
        self.rect = None
        self.layoutDirty = False
        self.drawList = None
        self.sites = iconsites.IconSiteList()
        self.id = None if self._isTemporaryIcon() else self.window.makeId(self)
        self.errHighlight = None
        if canProcessCtx:
            self.canProcessCtx = True
        window.undo.registerIconCreated(self)

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is
         drawn can be optionally overridden by specifying image and/or location."""
        pass

    def _anchorSite(self):
        """Return the name of the site that establishes the "official" position of the
        icon (as returned by .pos())"""
        for siteId in ['seqInsert', 'output', 'attrOut', 'cprhOut']:
            if hasattr(self.sites, siteId):
                return siteId
        return None

    def pos(self, preferSeqIn=False):
        """The "official" position of an icon.  This is used to record and restore the
        icon to its original location via the @ macro in the save file.  It is also used
        to determine where place the window-cursor when the last remaining icon of a
        structure is deleted.  The position is defined by the location of its seqInsert,
        output, seqIin, attrOut, or cprhOut site (in that order).  Icons that don't have
        any such sites return the top-left corner of their rectangle.  For backward
        compatibility with earlier versions of the call, setting preferSeqIn to True will
        return the position of the seqIn site over the seqInsert site."""
        if preferSeqIn and hasattr(self.sites, 'seqIn'):
            return self.posOfSite('seqIn')
        return self.posOfSite(self._anchorSite())

    def select(self, select=True):
        """Use this method to select (select=True) or unselect (select=False) an icon.
        Use .isSelected() to read the selection state of the icon."""
        # Icon selection was initially a property of the icon itself, but many operations
        # need to look up "which icons are currently selected" which is too expensive for
        # windows with large numbers of icons, so it is now maintained as a set in the
        # window structure rather than an icon property
        self.window.select(self, select)

    def isSelected(self):
        return self.window.isSelected(self)

    def layout(self, location=None, siteId=None):
        """Compute layout and set locations for icon and its children (do not redraw).
        If location and site are specified, position the icon with the given site at the
        given location.  If site is not specified, default to the same site as .pos(). If
        location is not specified, maintain the icon the icon's existing position
        (anchored on the specified siteId).  This should only be called on top-level
        icons."""
        if siteId is None:
            siteId = self._anchorSite()
        if location is None:
            if siteId is None:
                location = self.rect[:2]
            else:
                location = self.posOfSite(siteId)
        # Calculate layout choices (... This would be a good place to add a hint when
        # the layout is sequential for optimization)
        layouts = self.calcLayouts()
        if hasattr(self, 'stmtComment'):
            incorporateStmtCommentLayouts(layouts, self.stmtComment.calcLayouts(),
                self.window.margin)
        # Determine the best of the calculated layouts based on size and "badness" rating
        # recorded in each of the layouts.  Incorporate size and margin exceeded penalties
        # directly in to the layout badness score
        if layouts is None:
            print("No viable layouts for top level icon", self.dumpName())
            return
        for layout in layouts:
            if layout.width > self.window.margin:
                layout.badness += 100 + 2 * layout.width - self.window.margin
        if self.nextInSeq() or self.prevInSeq(includeModuleAnchor=True):
            # Icon is part of a sequence.  Optimize for height
            minHeight = min((layout.height for layout in layouts))
            for layout in layouts:
                layout.badness += (layout.height - minHeight) // 2
        else:
            # Icon is not in a sequence.  Optimize for perimeter
            minBadness = min((layout.width + layout.height * 4 for layout in layouts))
            for layout in layouts:
                layout.badness += (layout.width + layout.height * 4 - minBadness) // 8
        bestScore = bestLayout = None
        for layout in layouts:
            if bestScore is None or layout.badness < bestScore:
                bestLayout = layout
                bestScore = layout.badness
        # Arrange the icon and its children according to bestLayout.  Attempt to pick
        # appropriate x and y for doLayout for on the requested location using the site
        # offset of the current layout.  However, because the act of laying out the icon
        # and its children can shift sites around within the icon rectangle, the
        # resulting layout may still need to be shifted after the layout is completed.
        x, y = location
        if siteId is None:
            rectLeft, rectTop = location
        else:
            site = self.sites.lookup(siteId)
            rectLeft = x - site.xOffset
            rectTop = y - site.yOffset
        for layoutAnchor in ['output', 'attrOut', 'cprhOut']:
            if hasattr(self.sites, layoutAnchor):
                anchorSite = self.sites.lookup(layoutAnchor)
                anchorX = rectLeft + anchorSite.xOffset
                anchorY = rectTop + anchorSite.yOffset
                self.doLayout(anchorX, anchorY, bestLayout)
                break
        else:
            self.doLayout(rectLeft, rectTop, bestLayout)
        # Relocate the icon if the requested site did not land at the requested location
        if location != self.posOfSite(siteId):
            if siteId is None:
                newLeft = x
                newTop = y
            else:
                site = self.sites.lookup(siteId)
                newLeft = x - site.xOffset
                newTop = y - site.yOffset
            xOff = newLeft - self.rect[0]
            yOff = newTop - self.rect[1]
            for ic in self.traverse():
                left, top = ic.rect[:2]
                ic.rect = moveRect(ic.rect, (left + xOff, top + yOff))
        if hasattr(self, 'stmtComment'):
            xOff = bestLayout.width - bestLayout.stmtCommentLayout.width + \
                STMT_COMMENT_OFFSET
            self.stmtComment.doLayout(self.rect[0]+xOff, y-bestLayout.parentSiteOffset,
                bestLayout.stmtCommentLayout)
        # Traverse the hierarchy and recalculate .errHighlight flag per icon
        self.highlightErrors(None)
        return bestLayout

    def highlightErrors(self, errHighlight):
        """Set the .errHighlight field (recursively) for the icon and its children, based
        on the error state requested by the parent (errHighlight parameter), and the per-
        icon error calculation by those that implement the method.  The .errHighlight
        field of the icon represents both icon coloring and textual description of the
        error for allowed syntax errors in the icon structure, such as incorrect context,
        or being the child of an entry icon.  The errHighlight parameter can either be
        None, or and ErrorHighlight object.  If errHighlight is not None, the method
        should do nothing but forward it on to all of its children (meaning the top error
        description wins, even if a lower one happens to be more egregious).  If
        errHighlight is None, the icon should do whatever special error processing it
        needs to do to determine if it, or in some cases, which of its children, needs
        highlighting (for example, it's easier for "as" or "**" icons to process their
        own highlighting, but for icons that care about storage context, such as
        assignment and del to dictate their children's highlighting.  Because this (the
        superclass version of the method) simply calls the highlightErrors methods of the
        icon's children and propagates the errHighlight value to them, it is also often
        delegated-to by subclass methods to set the same error status on the icon and all
        of its children."""
        self.errHighlight = errHighlight
        for ic in self.children():
            ic.highlightErrors(errHighlight)

    def traverse(self, order="draw", includeSelf=True, inclStmtComment=False):
        """Iterator for traversing the tree below this icon.  Traversal can be in either
        drawing (order="draw") or picking (order="pick") order."""
        if order == 'pick':
            if inclStmtComment and hasattr(self, 'stmtComment'):
                yield self.stmtComment
        else:
            if includeSelf:
                yield self
        # For "pick" order to be the true opposite of "draw", this loop should run in
        # reverse, but child icons are not intended to overlap in a detectable way.
        for child in self.children():
            if child is None:
                print('icon has null child', self)
            yield from child.traverse(order)
        if order == "pick":
            if includeSelf:
                yield self
        else:
            if inclStmtComment and hasattr(self, 'stmtComment'):
                yield self.stmtComment

    def traverseBlock(self, includeSelf=True, hier=False, inclStmtComment=False):
        """If the icon owns a code block return either all the icons in the code block
        (if hier is True), or just the top level icons in the block (if hier is False)."""
        if includeSelf:
            if hier:
                yield from self.traverse(inclStmtComment=inclStmtComment)
            else:
                yield self
        if not hasattr(self, 'blockEnd'):
            return
        for ic in traverseSeq(self, includeStartingIcon=False):
            if ic is self.blockEnd:
                break
            if hier:
                yield from ic.traverse(inclStmtComment=inclStmtComment)
            else:
                yield ic
        if includeSelf:
            yield self.blockEnd

    def drawListIdxToPartId(self, idx):
        """Icons that are not drawn as a single monolithic image can have multiple parts
        whose relative positioning may depend on intervening arguments or continuation
        dynamics.  If the user grabs and drags one of these icons by such a part, we want
        the mouse to continue to point to the same part of the same icon, even if the
        dragged icons are laid out differently from how they originally appeared in the
        code from which they were removed or copied.  Icon part IDs are a bit of a hack,
        in that they take advantage of the icon's drawList to identify these parts, so
        that most multi-part icons don't need to do anything to take advantage of this
        capability.  The only ones that need to do anything are those with drawLists that
        can vary across layout changes, such as those with intermittently drawn parts
        (such as optional parens).  partIds are also used in drag-selection to uniquely
        identify those separated components when they appear in different places in the
        lexical ordering (for example parens have parts that appear both before and after
        the icons they surround).  As such, they also need to match the partId values
        returned from expredit.lexicalTraverse.  The special partId of 0 represents a
        drawn image that is part of the icon, but is ignored in picking and lexical
        traversal (commas being the only current example of such).  Note that there are
        still some icons that delete their drawLists after drawing temporary sites for
        dragging.  I'm not sure how these get through all the partId-related code without
        dumping diagnostics or messing up dragging or target selection, but they may need
        to be fixed at some point."""
        if self.drawList is None:
            print('drawListIdxToPartId missing drawlist (%s)?' % self.dumpName())
            return None
        img = self.drawList[idx][1]
        if img is commaImage or img is commaTypeoverImage:
            return 0
        partId = 1
        for i, (imgOffset, img) in enumerate(self.drawList):
            if i == idx:
                return partId
            if img is not commaImage:
                partId += 1
        print('drawListIdxToPartId idx beyond end of drawList (%s)?' % self.dumpName())
        return partId

    def partIdToDrawListIdx(self, partId):
        """Inverse of drawListIdxToPartId, uses drawListIdxToPartId, so icons do not need
        to override to support their own mapping."""
        if self.drawList is None or len(self.drawList) == 0:
            print('No mapping for partId of icon %s' % self.dumpName())
            return None
        for idx in range(len(self.drawList)):
            if partId == self.drawListIdxToPartId(idx):
                return idx
        print('Could not find partId %d of icon %s' % (partId, self.dumpName()))
        return None

    def touchesPosition(self, x, y):
        """Return a non-zero integer value if any of the drawn part of the icon falls at
        x, y.  The returned value can be use to identify what sub-part of the icon was
        clicked, to the offsetOfPart() method.  Note that for most icons, this method
        will only operate properly if the icon is *drawn* (not just laid-out), as it uses
        the alpha channel of the images in the self.drawList to judge whether the icon
        is drawn there.  Icons that have opaque parts that they want ignored (commas
        drawn with icon.commaImage are automatically ignored) or transparent parts they
        want counted, can override this, though overriding drawListIdxToPartId to return
        None or 0 for the entire entry may be simpler."""
        if not pointInRect((x, y), self.rect):
            return None
        if self.drawList is None:
            print('Missing drawlist (%s)?' % self.dumpName())
        for i, (imgOffset, img) in enumerate(self.drawList):
            left, top = addPoints(self.rect[:2], imgOffset)
            imgX = x - left
            imgY = y - top
            if pointInRect((imgX, imgY), (0, 0, img.width, img.height)):
                pixel = img.getpixel((imgX, imgY))
                return self.drawListIdxToPartId(i) if pixel[3] > 128 else 0
        return None

    def siteRightOfPart(self, partId):
        """Returns the name of the site on the right side of the icon part given by
        partId.  Be aware that this method will return None for the singular case of
        a statement-comment icon.  There is a function in expredit.py of the same name,
        that returns both an icon and a site, that will do the None-check ahd return an
        appropriate icon when the icon can be a statement comment.
        Note that this base class method is only useful for single-part icons for which
        the lastCursorSite() method of the site list will reliably produce the desired
        site.  All other icons need to override this method to provide this function.
        Currently these methods don't check for bad partIds, and instead, just return
        the rightmost site of the icon."""
        return self.sites.lastCursorSite()

    def touchesEmptySeriesSite(self, x, y):
        """Determine if the point (x, y) touches the highlighted rectangle of an empty
        series site of this icon.  If so, return the site name."""
        for siteOrSeries in self.sites.allSites(expandSeries=False):
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                for idx, site in enumerate(siteOrSeries):
                    if idx < len(siteOrSeries) - 1:
                        if site.att is None and site.type == 'input':
                            iconX, iconY, _, _ = self.rect
                            height = minTxtIconHgt - 2
                            width = LIST_EMPTY_ARG_WIDTH - 2
                            l = iconX + site.xOffset + inSiteImage.width
                            t = iconY + site.yOffset - height // 2
                            r = l + width
                            b = t + height
                            if pointInRect((x, y), (l, t, r, b)):
                                return site.name
        return None

    def offsetOfPart(self, partId):
        """Returns the position of a sub-part of the icon (identified by partId) relative
        to the icon rectangle.  partId is the value returned by the touchesPosition
        method.  The calculation of partId used here (Icon superclass) for offsetOfPart
        and touchesPosition, works for most Python-syntax icons, but by the somewhat
        sleazy method of counting images in the icon's drawList and ignoring those that
        point to icon.commaImage.  Icons that are not consistent in their usage of
        drawList images or use something other than comma images as separators between
        variable numbers of arguments, can override this, but in most cases, its better
        to override drawListIdxToPartId, as this will enable the base-class methods for
        touchesPosition, offsetOfPart, partsLeftOfPoint, and partsRightOfPoint to use
        the images in self.drawList. Note, also, that it returns the position (top, left)
        of the underlying pixmap used for drawing the part, which may not correspond to a
        visible pixel (since this call is only used to determine offset relative to a
        previous icon layout, it only matters that the position has a consistent
        relationship to the drawn location of the part)."""
        if self.drawList is None or len(self.drawList) == 0:
            return 0, 0
        for idx, (imgOffset, img) in enumerate(self.drawList):
            if partId == self.drawListIdxToPartId(idx):
                return imgOffset
        return self.drawList[-1][0]

    def partIsLeftOfPoint(self, partId, x, y):
        """If a visible part of the icon, designated by partId, is horizontally left of
        point (x,y), return the distance to the closest opaque pixel.  Returns None if
        the icon part has no opaque pixels left of x,y at the given y value.  Note that
        all of the caveats associated with icon partIds (see touchesPosition and
        offsetOfPart) apply.  In particular, the icon must be *drawn*, not just laid out
        for this to be usable, and if self.drawList can vary, the icon needs to override
        drawListIdxToPartId to provide a stable mapping of displayList images to partIds.
        """
        minX, minY, maxX, maxY = self.rect
        if y < minY or y >= maxY or x < minX:
            return None
        drawListIdx = self.partIdToDrawListIdx(partId)
        if drawListIdx is None:
            return None
        imgOffset, partImg = self.drawList[drawListIdx]
        partX, partY = addPoints(self.rect[:2], imgOffset)
        if y < partY or y >= partY + partImg.height or x < partX:
            return None
        imgX = x - partX
        imgY = y - partY
        if imgX >= partImg.width:
            xDist = imgX - partImg.width
            imgX = partImg.width - 1
        else:
            xDist = 0
        while imgX >= 0:
            pixel = partImg.getpixel((imgX, imgY))
            if pixel[3] > 0:
                # ... The criterion for opaque in touchesPosition is 128, but we
                # definitely don't want to miss icon borders, so be sure to test this
                break
            xDist += 1
            imgX -= 1
        else:
            # No opaque pixels found
            return None
        return xDist

    def partIsRightOfPoint(self, partId, x, y):
        """If a visible part of the icon, designated by partId, is horizontally left of
        point (x,y), return the distance to the closest opaque pixel.  Note that all of
        the caveats associated with icon partIds (see touchesPosition and offsetOfPart)
        apply.  In particular, the icon must be *drawn*, not just laid out for this to be
        usable.  If the icon part has no opaque pixels left of x,y at the given y value,
        returns None."""
        minX, minY, maxX, maxY = self.rect
        if y < minY or y > maxY or x > maxX:
            return None
        drawListIdx = self.partIdToDrawListIdx(partId)
        if drawListIdx is None:
            return None
        imgOffset, partImg = self.drawList[drawListIdx]
        partX, partY = addPoints(self.rect[:2], imgOffset)
        if y < partY or y >= partY + partImg.height or x >= partX + partImg.width:
            return None
        imgX = x - partX
        imgY = y - partY
        if imgX < 0:
            xDist = -imgX
            imgX = 0
        else:
            xDist = 0
        while imgX < partImg.width:
            pixel = partImg.getpixel((imgX, imgY))
            if pixel[3] > 0:
                # ... The criterion for opaque alpha in touchesPosition is 128, but we
                # definitely don't want to miss icon borders, so be sure to test this
                break
            xDist += 1
            imgX += 1
        else:
            # No opaque pixels found
            return None
        return xDist

    def inRectSelect(self, rect):
        """Return True if rect overlaps any visible part of the icon (commas excepted).
        Note that this is not as thorough as touchesPosition, which answers at the level
        of pixels.  This only answers at the level of rectangles in which the icon
        draws something."""
        if not comn.rectsTouch(self.rect, rect):
            return False
        if self.drawList is None:
            print('Missing drawlist (%s)?' % self.dumpName())
        for imgOffset, img in self.drawList:
            if img is commaImage or img is commaTypeoverImage:
                continue
            left, top = addPoints(self.rect[:2], imgOffset)
            right = left + img.width
            bottom = top + img.height
            if comn.rectsTouch((left, top, right, bottom), rect):
                return True
        return False

    def selectionRect(self):
        """Return the area of the icon that constitutes the selected portion of the icon.
        This is used for extending existing selections (Shift+select), and typically
        excludes tiny connectors and snap sites"""
        return self.rect

    def hierRect(self, inclStmtComment=True):
        """Return a rectangle covering this icon and its children"""
        return containingRect(self.traverse(inclStmtComment=inclStmtComment))

    def needsLayout(self):
        """Returns True if the icon requires re-layout due to changes to child icons"""
        # For the moment need to lay-out propagates all the way to the top of
        # the hierarchy.  Once sequences are introduced.  This will probably
        # stop, there
        for ic in self.traverse():
            if ic.layoutDirty:
                return True
        return False

    def markLayoutDirty(self):
        """Mark the icon layout dirty and mark the page it is found on dirty, as well
        so that the icon can be found for layout.  Be aware that this code needs intact
        parent links to find the page.  If the icon is not linked to a page, it is the
        responsibility of the caller to ensure that the page gets marked.  Returns False
        if the parent links are broken or cyclic and the page can not be found."""
        if self._isTemporaryIcon():
            return True
        self.layoutDirty = True
        # Dirty layouts are found through the window Page structure, then iterating over
        # just the top icons of the page sequence, so mark the page and the top icon.
        if self.window is None:
            return False
        topParent = self.topLevelParentSafe()
        if topParent is None:
            print('parent cycle in markLayoutDirty')
            return False
        topParent.layoutDirty = True
        page = self.window.topIcons.get(topParent)
        if page is None:
            return False
        page.layoutDirty = True
        return True

    def children(self):
        return [c.att for c in self.sites.childSites() if c is not None and
         c.att is not None]

    def parent(self):
        for site in self.sites.parentSites():
            # icons can have multiple possible parent sites (Some icon types are capable
            # of snapping to multiple site types).  Return whichever is attached.
            if site.att is not None:
                return site.att
        return None

    def parentSites(self):
        """Return siteIds for all icon sites capable of holding parent links."""
        return [site.name for site in self.sites.parentSites()]

    def parentage(self, includeSelf=False):
        """Returns a list containing the lineage of the given icon, from the icon up to
         the top of the window hierarchy."""
        parentList = []
        if includeSelf:
            parentList.append(self)
        child = self
        while True:
            parent = child.parent()
            if parent is None:
                break
            parentList.append(parent)
            child = parent
        return parentList

    def topLevelParent(self):
        """Follow the icon hierarchy upwards and return the icon with no parent"""
        child = self
        while True:
            parent = child.parent()
            if parent is None:
                return child
            child = parent

    def topLevelParentSafe(self):
        """Same as topLevelParent, but tolerates bad parent links, returning None if
        a cycle was found."""
        child = self
        visited = set()
        while True:
            if child in visited:
                return None
            visited.add(child)
            parent = child.parent()
            if parent is None:
                return child
            child = parent

    def nextInSeq(self):
        if not hasattr(self.sites, 'seqOut'):
            return None
        return self.sites.seqOut.att

    def prevInSeq(self, includeModuleAnchor=False):
        if not hasattr(self.sites, 'seqIn'):
            return None
        prevIcon = self.sites.seqIn.att
        if prevIcon is self.window.modSeqIcon and not includeModuleAnchor:
            return None
        return self.sites.seqIn.att

    def snapLists(self, forCursor=False):
        x, y = self.rect[:2]
        return self.sites.makeSnapLists(self, x, y, forCursor=forCursor)

    def replaceChild(self, newChild, siteId, leavePlace=False, childSite=None):
        """Replace the icon attached at a particular site.  Note that while the name
        is "replaceChild", it is possible to use this on any site.  The convention when
        icons are arranged in a hierarchy, is to operate on child sites, so that the
        back-link (childSite) can be automatically determined.  Meaning, if icons are not
        arranged in a strict hierarchy, specify childSite or bad things will happen.
        If leavePlace is False, replacing a series site with None will remove the site
        itself from the series.  If leavePlace is True, the site will remain and be set
        to None."""
        siteId = self.sites.siteIdWarn(siteId)
        if self.sites.isSeries(siteId):
            if newChild is None and not leavePlace:
                self.sites.removeSeriesSiteById(self, siteId)
            else:
                seriesName, idx = iconsites.splitSeriesSiteId(siteId)
                seriesLen = len(self.sites.getSeries(seriesName))
                if idx == seriesLen:
                    self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
                self.sites.lookup(siteId).attach(self, newChild, childSite)
        else:
            self.sites.lookup(siteId).attach(self, newChild, childSite)
        self.markLayoutDirty()
        if newChild is not None:
            newChild.markLayoutDirty()

    def replaceWith(self, replacementIcon):
        """Replace this icon (self) with another icon in the parent site to which it
        is currently attached, or on the top level of the window"""
        parent = self.parent()
        if parent is None:
            if replacementIcon is None:
                self.window.removeIcons(self)  # Curr. unused, untested, but should work
            else:
                self.window.replaceTop(self, replacementIcon)
        else:
            parent.replaceChild(replacementIcon, parent.siteOf(self))

    def insertParent(self, parentToWrap, parentSite):
        """Add an icon between this icon and its parent (or this icon and the top level
        if the icon has no parent)."""
        parent = self.parent()
        parentToWrap.replaceChild(self, parentSite)
        if parent is None:
            # Insert new parent at top level with ic as its child
            self.window.replaceTop(self, parentToWrap)
        else:
            # Insert new parent between parent and ic old parent
            parent.replaceChild(parentToWrap, parent.siteOf(self))

    def removeEmptySeriesSite(self, siteId):
        if self.childAt(siteId):
            return
        self.sites.removeSeriesSiteById(self, siteId)
        self.markLayoutDirty()

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None,
            preserveNoneAtZero=False):
        """Insert a child icon or empty icon site (child=None) at the specified site.
        siteIdOrName may specify either the complete siteId for a site, or (if
        seriesIdx is specified), the name for a series of sites with the index specified
        in seriesIdx.  Normally the site of the child icon is inferred by finding a
        mating site of the appropriate type, but if 'child' has multiple mating sites,
        the site name can be specified in childSite.  The zeroth site is of a series is
        somewhat special, in that it always exists, and when empty does not imply an
        empty element unless a second site exists.  Normally the call will overwrite this
        empty site, but if the desired behavior is to insert before it and leave a
        trailing comma, set preserveNoneAtZero to True."""
        if seriesIdx is None:
            seriesName, seriesIdx = iconsites.splitSeriesSiteId(siteIdOrSeriesName)
        else:
            seriesName = siteIdOrSeriesName
        if seriesName is None:
            print("Failed to insert icon", child, "at", siteIdOrSeriesName)
            return
        series = self.sites.getSeries(seriesName)
        if series is None:
            print("Failed to insert icon,", child, "in series", seriesName)
            return
        if not preserveNoneAtZero and len(series) == 1 and series[0].att is None and \
                seriesIdx == 0:
            series[0].attach(self, child, childSite)
        else:
            self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, seriesIdx)
            self.sites.lookupSeries(seriesName)[seriesIdx].attach(self, child, childSite)
        self.markLayoutDirty()
        if child is not None:
            child.markLayoutDirty()

    def insertChildren(self, children, seriesOrSiteName, seriesIdx=None, childSite=None,
            preserveNoneAtZero=False):
        """Insert a group of child icons at the specified series-site.  seriesOrSiteName
        can be either be a site name within the series, or just the name of the series,
        in which case seriesIdx must specify the index.  Normally the site of each child
        icon is inferred by finding a mating site for siteOrSeriesName, but in the (very
        unlikely) event that the children have multiple mating sites, the site name can
        be specified in childSite.  The zeroth site is of a series is somewhat special,
        in that it always exists, and when empty does not imply an empty element unless a
        second site exists.  Normally the call will overwrite this empty site, but if the
        desired behavior is to insert before it and leave a trailing comma, set
        preserveNoneAtZero to True."""
        if seriesIdx is None:
            seriesName, seriesIdx = iconsites.splitSeriesSiteId(seriesOrSiteName)
        else:
            seriesName = seriesOrSiteName
        for i, child in enumerate(children):
            self.insertChild(child, seriesName, seriesIdx + i, childSite,
                preserveNoneAtZero=preserveNoneAtZero)

    def insertAttr(self, topAttrIcon):
        """Insert an attribute or chain of attributes between the icon and its current
        attributes"""
        endAttrIcon = findLastAttrIcon(topAttrIcon)
        origAttrIcon = self.childAt('attrIcon')
        self.replaceChild(topAttrIcon, 'attrIcon')
        endAttrIcon.replaceChild(origAttrIcon, 'attrIcon')

    def childAt(self, siteOrSeriesName, seriesIdx=None):
        if seriesIdx is None:
            site = siteOrSeriesName
        else:
            site = iconsites.makeSeriesSiteId(siteOrSeriesName, seriesIdx)
        icSite = self.sites.lookup(site)
        return icSite.att if icSite is not None else None

    def siteOf(self, ic, recursive=False):
        """Find the site name for an attached icon.  If recursive is True, ic is not
        required to be a direct descendant."""
        if ic is None:
            return None
        if recursive:
            while True:
                parent = ic.parent()
                if parent is None:
                    return None
                if parent is self:
                    break
                ic = parent
        icSite = self.sites.siteOfAttachedIcon(ic)
        return icSite.name if icSite is not None else None

    def hasSite(self, siteId):
        return self.sites.lookup(siteId) is not None

    def hasSiteType(self, siteType):
        return bool(self.sites.sitesOfType(siteType))

    def posOfSite(self, siteId=None):
        """Return the window position of a given site of the icon.  If siteId is not
        specified, return the top left corner of the icon's rectangle."""
        if siteId is None:
            return self.rect[:2]
        site = self.sites.lookup(siteId)
        if site is None:
            return None
        x, y = self.rect[:2]
        return x + site.xOffset, y + site.yOffset

    def typeOf(self, siteId):
        site = self.sites.lookup(siteId)
        if site is None:
            if iconsites.isSeriesSiteId(siteId):
                # It is legal to insert at a series site that does not exist yet, and we
                # may (occasionally) need to know the type
                seriesName, idx = iconsites.splitSeriesSiteId(siteId)
                series = getattr(self.sites, seriesName, None)
                if series is not None:
                    return series.type
            return None
        return site.type

    def isCursorOnlySite(self, siteId):
        site = self.sites.lookup(siteId)
        if site is None:
            return False
        if not hasattr(site, 'cursorOnly'):
            return False
        return site.cursorOnly

    def isCursorSkipSite(self, siteId):
        site = self.sites.lookup(siteId)
        if site is None:
            return False
        if not hasattr(site, 'cursorSkip'):
            return False
        return site.cursorSkip

    def becomeTopLevel(self, isTop):
        """Change top level status of icon (most icons add or remove sequence sites)."""
        self.drawList = None  # Force change at next redraw

    def hasCoincidentSite(self):
        """If the icon has an input site in the same spot as its output site (done so
        binary operations can be arranged like text), return that input site"""
        if hasattr(self, 'coincidentSite') and self.coincidentSite is not None:
            return self.coincidentSite

    def hasStmtComment(self):
        """If this is at statement-level (top) icon and has a statement comment
        associated with it, return the comment icon."""
        return self.stmtComment if hasattr(self, 'stmtComment') else None

    def textRepr(self):
        """Produce Python-equivalent text for clipboard text representation"""
        return repr(self)

    def dumpName(self):
        """Give the icon a name to be used in text dumps."""
        return self.__class__.__name__

    def doLayout(self, outSiteX, outSiteY, layout):
        pass

    def calcLayouts(self):
        pass

    def textEntryHandler(self, entryIc, text, onAttr):
        """Called when an icon or one of its children holds a text-entry box (entryIc),
        and a new character is typed in the box.  text provides the full text currently
        held in entryIc, onAttr will be true if the entry icon is attached to an
        attribute site.  The function can return None to do nothing and allow normal
        parsing to take place.  It can create and return an icon, along with whatever
        delimiter character was left in text.  Or, it can return one of a set of keywords
        accepted by the entry-processing code:

            reject:reason-text  Prevent the user from entering the character and beep
            accept              Allow the user to enter the character
            typeover            Initiate typeover of dimmed characters

        Additional keywords are supported as part of general parsing, but would probably
        not be used by text entry handlers:

            comma, colon, openBracket, endBracket, openBrace, endBrace, openParen,
            endParen
        """
        return None

    def setTypeover(self, idx, site=None):
        """For an icon that supports typeover (hasTypeover==True), change the typeover
        state.  Typeover allows icons to put text in front of the cursor that the user
        can optionally type, but that will become fixed once the user navigates away from
        it.  idx specifies the index in to the typeover string at which dimmed typeover
        characters are drawn in place of fully drawn text.  None or an invalid index
        value turn typeover off.  For a single character typeover, such as a paren or
        brace, 0 is the only value that will enable typeover.  site can be specified to
        disambiguate typeover regions for icons that have more than one  (currently only
        function definitions).  site should be either the site that *follows* the
        typeover region, or none to set it for all sites. Returns True if typeover is
        enabled after the call"""
        pass

    def typeoverSites(self, allRegions=False):
        """By default (allRegions==False), returns the site before, site after, text,
        and index of the first (leftmost) active typeover region of the icon.  Setting
        allRegions=True will return a list of the data for all still-active typeover
        regions (function definitions, DefIcon, is the only icon that currently has more
        than one region)."""
        pass

    def typeoverCursorPos(self):
        """Icons with multi-character typeovers support a cursor type of "typeover",
        where a blinking text cursor is displayed on the icon (icons with single-character
        typeover don't need this, as there are icon cursor positions on either side).
        To provide the position to the cursor-drawing code, the icon must implement this
        method, which should return two values: x and y offsets relative to the icon's
        rectangle that specify the origin (y center) for the text cursor."""
        pass

    def _drawFromDrawList(self, toDragImage, location, clip, style):
        if location is None:
            location = self.rect[:2]
        if toDragImage is None:
            outImg = self.window.image
            x, y = self.window.contentToImageCoord(*location)
            if clip is not None:
                clip = comn.offsetRect(clip, -self.window.scrollOrigin[0],
                 -self.window.scrollOrigin[1])
        else:
            outImg = toDragImage
            x, y = location
        if self.isSelected():
            style |= STYLE_SELECTED
        if isinstance(self.errHighlight, ErrorHighlight):
            style |= STYLE_SYNTAX_ERR
        elif isinstance(self.errHighlight, TypeAnnHighlight):
            style |= STYLE_TYPE_ANN
        if self.window.highlightedForReplace is not None and \
                self in self.window.highlightedForReplace:
            style |= STYLE_PENDING_REMOVE
        if self.window.immediateDragHighlight is not None and \
                self in self.window.immediateDragHighlight:
            style |= STYLE_IMMEDIATE_COPY
        for (imgOffsetX, imgOffsetY), img in self.drawList:
            pasteImageWithClip(outImg, tintSelectedImage(img, style),
                (x + imgOffsetX, y + imgOffsetY), clip)

    def _drawEmptySites(self, toDragImage, clip, skip=None, hilightEmptySeries=False,
            allowTrailingComma=False):
        """Draws highlighting for empty sites.  Since empty site width is standardized
        across icons, and Python syntax is fairly consistent in not allowing stray empty
        fields, most icons can just call this method to find and highlight the sites
        that need highlighting.  An icon that has sites that are allowed to be empty, or
        that needs to do something different with a particular site, can specify a list
        of sites (IconSite or IconSiteSeries objects) to skip in parameter "skip".
        Since we allow empty series sites to be selected, this will color the site in the
        selection color (rather than the empty site color) it is selected."""
        # Note that empty sites are drawn as transparent via alpha-blending, which
        # required a change to the basic drawing model.  Prior versions of the code
        # allowed redraw without clearing, which was used for operations that didn't
        # change the icon layout (selection and cursor drawing in particular).  If
        # empty site highlighting turns dark-red, look for old code making multiple icon
        # drawing calls without clearing.
        if skip is None:
            skip = ()
        sitesToDraw = []
        for siteOrSeries in self.sites.allSites(expandSeries=False):
            if isinstance(siteOrSeries, iconsites.IconSiteSeries):
                if len(siteOrSeries) > 1 or hilightEmptySeries:
                    for site in siteOrSeries:
                        if site.name in skip or allowTrailingComma and site is \
                                siteOrSeries[-1] and len(siteOrSeries) > 1:
                            continue
                        if site.att is None and site.type == 'input':
                            sitesToDraw.append((site, True))
            elif siteOrSeries.att is None and siteOrSeries.type == 'input' and \
                    siteOrSeries.name not in skip:
                sitesToDraw.append((siteOrSeries, False))
        if len(sitesToDraw) == 0:
            return
        iconX, iconY, _, _ = self.rect
        outImg = toDragImage if toDragImage is not None else self.window.image
        if clip is None:
            clip = 0, 0, outImg.width, outImg.height
        draw = alpha = None
        if toDragImage is None:
            iconX, iconY = self.window.contentToImageCoord(iconX, iconY)
            clipLeft, clipTop, clipRight, clipBottom = comn.offsetRect(clip,
                -self.window.scrollOrigin[0], -self.window.scrollOrigin[1])
            alpha = EMPTY_ARG_COLOR[3] / 255.0
        else:
            clipLeft, clipTop, clipRight, clipBottom = clip
            draw = ImageDraw.Draw(outImg)
        height = minTxtIconHgt - 2
        for site, isSeriesSite in sitesToDraw:
            color = EMPTY_ARG_COLOR
            # Per selection rules, we color non-series sites to match the *icon*, but for
            # series sites, the selection/highlight must be explicitly list the *site*.
            icOrSite = (self, site.name) if isSeriesSite else self
            if self.window.highlightedForReplace is not None and \
                    icOrSite in self.window.highlightedForReplace:
                color = PENDING_REMOVE_TINT
            elif self.window.immediateDragHighlight is not None and \
                    icOrSite in self.window.immediateDragHighlight:
                color = IMMEDIATE_COPY_TINT
            elif icOrSite in self.window.selectedSet:
                color = SELECT_TINT
            alpha = color[3] / 255.0
            width = (LIST_EMPTY_ARG_WIDTH if isSeriesSite else EMPTY_ARG_WIDTH) - 2
            x = iconX + site.xOffset + inSiteImage.width
            y = iconY + site.yOffset - height // 2
            l = max(x, clipLeft)
            r = min(x + width, clipRight)
            t = max(y, clipTop)
            b = min(y + height, clipBottom)
            if r - l > 0 and b - t > 0:
                if toDragImage:
                    draw.rectangle((l, t, r-1, b-1), fill=color)
                else:
                    tintImg = Image.new('RGB', (r-l, b-t), color)
                    contentImg = outImg.crop((l, t, r, b))
                    compositeImg = Image.blend(contentImg, tintImg, alpha)
                    outImg.paste(compositeImg, (l, t))

    def _serialize(self, offset, iconsToCopy, **args):
        currentSeries = None
        children = []
        for site in self.sites.childSites():
            att = self.childAt(site.name)
            if att is not None and att not in iconsToCopy:
                continue
            childRepr = None if att is None else att.clipboardRepr(offset, iconsToCopy)
            if iconsites.isSeriesSiteId(site.name):
                seriesName, idx = iconsites.splitSeriesSiteId(site.name)
                if currentSeries is None or seriesName != currentSeries[0]:
                    if currentSeries is not None:
                        children.append(currentSeries)
                    currentSeries = [seriesName]
                currentSeries.append(childRepr)
            else:
                if currentSeries is not None:
                    children.append(currentSeries)
                    currentSeries = None
                children.append((site.name, childRepr))
        if currentSeries is not None:
            children.append(currentSeries)
        return self.__class__.__name__, addPoints(self.rect[:2], offset), args, children

    def _duplicateChildren(self, toIcon, linkToOriginal=False):
        """Part of the normal mechanism for icon duplication.  The 'duplicate' methods in
        icon subclasses will typically recreate the icon itself and configure its state,
        but will call this to find, copy, and link all of the icons children.
        Additionally, if linkToOriginal is specified, it will tag toIcon with a back-
        pointer to the icon of which it is a copy."""
        if linkToOriginal:
            toIcon.copiedFrom = self
        for site in self.sites.childSites(expandSeries=True):
            if site.att is None:
                newChild = None
            else:
                newChild = site.att.duplicate(linkToOriginal=linkToOriginal)
            toIcon.replaceChild(newChild, site.name, leavePlace=True)

    def _restoreChildrenFromClipData(self, childrenClipData, window, offset):
        for childData in childrenClipData:
            siteName, *iconData = childData
            if self.sites.isSeries(siteName):
                self.insertChildren(clipboardDataToIcons(iconData, window, offset),
                 siteName, 0)
            else:
                getattr(self.sites, siteName).attach(self,
                 clipboardDataToIcons(iconData, window, offset)[0])

    def execute(self):
        """Directly execute icon and return a value.  This method of execution is
        deprecated in favor of creating and executing a Python AST.  Not all icons
        support this.  It is currently left in as it may be useful for experimentation
        (since the program retains control over each step of execution)."""
        return None

    def createAst(self):
        """Create a Python Abstract Syntax Tree (AST) for the icon and everything below
        it in the icon hierarchy.  The AST can be passed to the Python compiler to create
        code for execution."""
        return None

    def createSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        """Create text-format representation of the icon and hierarchy below it.  Returns
        an object of type filefmt.SegmentedText, which provides text annotated with
        potential wrap points classified by level in the icon hierarchy.  Icon code
        should increment parentBreakLevel (with some exceptions, like arithmetic
        associativity binary operations) in calls to createSaveText for child icons.
        Likewise, continuationNeeded should either be passed unchanged to child calls,
        or set to False if the icon provides enclosing parens/brackets/braces that
        remove the need for child text to get line continuation characters.  Icons that
        are legal as store and del targets have an additional parameter (ctx=None) that
        can provide that context, which they use both for checking validity to decide if
        the save text needs to be wrapped in a $Ctx$ macro, and in some cases, to
        propagate the context information to their own arguments."""
        return filefmt.SegmentedText("***No createSaveText method for icon %s" %
                                     self.dumpName())

    def createInvalidCtxSaveText(self, parentBreakLevel=0, contNeeded=True, export=False):
        """Same as createSaveText, but called when writer code detects that the icon
        appears outside of its allowed (statement-level) context.  This is implemented
        only by icons that can be invalidated by context above the statement-level, such
        as an 'else' outside of an if block.  Note that this is currently only used on
        pseudo-block icons (elif, else, except, finally) which need to write a macro for
        out-of-context use.  return, yield, continue, and break, are acceptable to the
        Python parser, without additional macro support.  This method exists both for
        efficiency (so icons don't have to individually scan their entire block to
        determine their context), and to simplify writing of code fragments (by not
        having to reconstruct sequences)."""
        raise Exception(f"Icon type, {self.__class__} createInvalidCtxSaveText method " \
            "called for icon that does not implement it.")

    def clipboardRepr(self, offset, iconsToCopy):
        """Serialized binary representation of an icon tree currently used for copy/paste
        within and between windows.  Given that the save file format will also be capable
        of being used for copy/paste, this mechanism will eventually be removed."""
        return self._serialize(offset, iconsToCopy)

    def temporaryDuplicate(self, inclStmtComment=False, linkToOriginal=False):
        """Make a copy of the hierarchy under this icon with undo turned off and no icon
        ids expended (currently, not wasting ids matters, because we don't have icon
        deletion, so there's no reuse mechanism).  Also leaves icon off of the window
        topIcon list and page-related infrastructure.  Temporary icons cannot be
        intermixed with permanent ones, and are only used in the process of producing
        save text for disjoint selections (see window._copyCb)."""
        with self.window.pauseUndoRecording():
            copyTopIcon = self.duplicate(linkToOriginal=linkToOriginal)
        if inclStmtComment and hasattr(self, 'stmtComment'):
            stmtComment = self.stmtComment.duplicate(linkToOriginal=linkToOriginal)
            stmtComment.attachStmtComment(copyTopIcon)
        return copyTopIcon

    def duplicate(self, linkToOriginal=False):
        """Return a copy of the icon and hierarchy beneath it.  Note that block-owning
        and comment-owning icons will neither duplicate their associated .endBlock
        and stmtComment icons, nor fill in the associated fields."""
        # This (icon superclass method) can be used for icons that do not have internal
        # state (other than connections to their child icons) to reproduce.  Those that
        # do will need to subclass this function.
        ic = self.__class__(window=self.window)
        self._duplicateChildren(ic, linkToOriginal=linkToOriginal)
        return ic

    def _isTemporaryIcon(self):
        return self.window.undoRecordingIsPaused()

    def backspace(self, siteId, evt):
        """Icon-specific action to perform when user presses backspace with the cursor
        positioned on one of the icon's sites.  This usually results in the deletion of
        the icon with its text being loaded in to an entry icon, and its arguments
        and attributes attached to the entry icon as pending args/attributes."""
        print('Backspace method not yet implemented for', self.dumpName())

    def becomeEntryIcon(self, clickPos=None, siteAfter=None):
        """Open the icon for editing by replacing it with a text entry icon.  If clickPos
        is specified, will verify that the given x,y position is within its editable
        area.  If siteAfter is specified, will verify that the given siteId is the site
        following the editable area of the icon.  Returns the new entry icon and, only if
        clickPos is specified, the window x,y location within the icon where the cursor
        would have been placed.  If verification of clickPos or siteAfter fails, returns
        None for the entry icon.  The reason the additional return value in the clickPos
        case, is so the caller can nudge the window cursor by the appropriate amount to
        account for layout and font changes between the clicked icon and the entry icon.
        Icons that do not support text-editing should not define this method."""
        if clickPos is not None:
            return None, None
        return None

    def placeArgs(self, placementList, startSiteId=None, overwriteStart=False):
        """Attach icons in placement list to icon sites.  Unlike replace/insertChild
        methods, allows for multiple attachments to a (contiguous) range of sites, and
        creation of sites that don't yet exist on the icon.  Used for placing icons from
        entry icon pending args list and (eventually) for multi-element pastes.  The
        format of the placementList is a list of elements which can be either:
        1. An icon to be placed.  Icons on the top level of the list originate from
           individual (not series) sites of the icon whose arguments were transferred.
           The exception to this rule, is that comprehension sites, which are managed as
           a series by icons, are managed as individuals in a place list.
        2. None, representing an empty site in the icon whose arguments were transferred
        3. A tuple or list of icons originating from a site series.  This may also
           contain Nones, representing empty series sites.  Note that this entry type
           refers specifically to a series of input sites that will be displayed comma-
           separated by the owning icon.  Comprehension site series are split up and
           added to the top level of the list (per #1).
        Starts placing at startAtSite.  If startAtSite is None, starts at the first
        child-type cursor site.  Placement will proceed until any of the following
        conditions are met:
        1. All icons in placementList are placed
        3. The next icon's parent attachment site is incompatible with the next site
        2. The next (non-list) site to be placed is already occupied.  Note, however:
            a. If overwriteStart is True, the starting site will be placed regardless of
               whether it is already occupied (replacing the existing icon).
            b. List sites are *inserted*, not replaced (except for the starting site,
               which will be replaced if overwriteStart is True).  Therefore, provided
               that the site types match, an icon can always be placed on a list site,
               even it is currently occupied.
        Returns two values: 1) the index in to placementList of the last icon placed
        or None if no icons could be placed, and 2) if that icon was from a series,
        the index in to that series of the icon (or None if it was not from a series).
        The Icon base class method handles only the simple cases of a single input or
        a single list (as detected from the icon site list).  While it can also handle
        multiple inputs or multiple inputs followed by a list, it will fill them in
        blindly disregarding site/list boundaries of the original icon, which is probably
        not what you want.  Icons with more complicated needs must redefine the method.
        (For the Python language, itself, the few icons that do have combinations of
        sites also have content-specific placement criteria, so there was no point in
        trying to define placement rules in the base class that no one would use).
        Note that the placement list format matches that of the call to add icons to an
        entry icon's pending argument list.  This is not a coincidence, because this is
        the mechanism by which argument attachments get reestablished when an icon with
        multiple argument sites (for, def, class, inline-if) gets converted back and
        forth to/from an entry icon.  While the placementList format does manage to
        encode all of the information needed to reproduce argument configurations for all
        of the Python-language icons, this mechanism may be insufficient for arbitrary
        icon designs, since some information from the original configuration is lost."""
        return self._placeArgs(placementList, startSiteId, overwriteStart, True)

    def canPlaceArgs(self, placementList, startSiteId=None, overwriteStart=False):
        """Determine which arguments from placementList would be placed if the placeArgs
        method were called.  Arguments and return values are the same as for placeArgs
        method (see placeArgs for descriptions)."""
        return self._placeArgs(placementList, startSiteId, overwriteStart, False)

    def _placeArgs(self, placementList, startSiteId, overwriteStart, doPlacement):
        """"Common method to perform both placeArgs and canPlaceArgs (the only difference
        between the two is the two lines of code that actually insert/replace the
        argument icons, which are called (or not) based on the value of doPlacement)."""
        placedIdx = None
        placedSeriesIdx = None
        siteId = self.sites.firstCursorSite() if startSiteId is None else startSiteId
        placeListIter = placementListIter(placementList)
        while siteId is not None:
            if iconsites.isSeriesSiteId(siteId):
                # If we're placing in a series, we can keep going until we exhaust
                # placementList or something is the wrong type, so we'll never return
                # to the outer while loop
                seriesName, seriesIdx = iconsites.splitSeriesSiteId(siteId)
                for i, (ic, placeListIdx, placeListSeriesIdx) in enumerate(placeListIter):
                    if not validateCompatibleChild(ic, self, seriesName):
                        return placedIdx, placedSeriesIdx
                    if doPlacement:
                        placeSiteId = iconsites.makeSeriesSiteId(seriesName, seriesIdx+i)
                        if overwriteStart and placeSiteId == startSiteId:
                            # This is the start site, and overwriteStart indicates that
                            # the caller wants it replaced rather than inserted.
                            self.replaceChild(ic, placeSiteId)
                        else:
                            self.insertChild(ic, placeSiteId)
                    placedIdx = placeListIdx
                    placedSeriesIdx = placeListSeriesIdx
                return placedIdx, placedSeriesIdx
            else:
                ic, placeListIdx, placeListSeriesIdx = next(placeListIter,
                    ("end", None, None))
                if ic == "end":
                    return placedIdx, placedSeriesIdx
                site = getattr(self.sites, siteId)
                if hasattr(site, 'cursorOnly') and site.cursorOnly:
                    return placedIdx, placedSeriesIdx
                if siteId == startSiteId and not overwriteStart:
                    if site.att is not None:
                        return placedIdx, placedSeriesIdx
                if not validateCompatibleChild(ic, self, siteId):
                    return placedIdx, placedSeriesIdx
                if doPlacement:
                    self.replaceChild(ic, siteId)
                placedIdx = placeListIdx
                placedSeriesIdx = placeListSeriesIdx
                siteId = self.sites.nextCursorSite(siteId)
        return placedIdx, placedSeriesIdx

    @staticmethod
    def fromClipboard(clipData, window, offset):
        iconClass, location, args, childData = clipData
        ic = iconClass(**args, window=window, location=addPoints(location, offset))
        ic._restoreChildrenFromClipData(childData, window, offset)
        return ic

    def debugLayoutFilter(self, layouts):
        if not hasattr(self, "debugLayoutFilterIdx"):
            return layouts
        selectedIdx = self.debugLayoutFilterIdx
        if selectedIdx >= len(layouts):
            selectedIdx = 0
            self.debugLayoutFilterIdx = 0
        print("Filtering layouts for %s %d/%d, badness %d, height %d" % (self.dumpName(),
                selectedIdx, len(layouts), layouts[selectedIdx].badness,
                layouts[selectedIdx].height))
        return [layouts[selectedIdx]]

    def compareData(self, data, compareContent=False):
        """Icons that are used to represent Python data (as opposed to operations) must
        supply a comparison function to match live data against the icon.  This is used
        to detect when  data is in an edited state.  Icons representing code must return
        False (leave this method unimplemented), as code can be pasted in to live mutable
        data, but must be executed to re-sync.  To preserve "is" identity in data for
        compound data objects, the compareData function should be based on object
        identity, rather than equality.  Simple immutable data objects (numbers in
        particular) are still compared by value, because any code that depends upon the
        identity of a numeric object is almost certainly doing so in error, and if we act
        upon such differences, lots of simple editing operations on values risk
        needlessly invalidating whatever compound data structures enclose them.

        For icons representing mutable data, the function must operate either from the
        point of view of the parent icon, asking if the data represented by the icon has
        changed (compareContent=False), or of the icon itself, asking if its own data has
        changed (compareContent=True).  From the point of view of the parent, mutable
        data retains its identity even when modified, so generally comparison stops at
        mutable icons and ignores changes to their content.  This is, of course, the
        opposite of what we need to figure out if the data *within* the object has
        changed, which is why mutable icons must supply the second (compareContent=True)
        mode of operation."""
        return False

    def getPythonDocRef(self):
        """Icons that need to dynamically choose which Python documentation references
        to provide, can override this method, which will be called when assembling the
        context-sensitive icon menu.  (Icons that always serve the same reference(s),
        can simply override the class variable, pythonDocRef.)  The method should return
        a list of html reference strings including the file name and relative path within
        the Doc subdirectory and (currently Windows-only) PythonNNN.chm file of the
        current Python interpreter.  To see the source files and find the required
        reference ids, you can decompile the .chm file using the '-decompile' command
        line option of the Windows 'hh' command.  You can also ask the document viewer
        to report both its link content and nearest href, by pointing at the link or at
        a location in the document and selecting 'Properties' from the right-mouse
        backkground menu, though I suggest viewing the source and choosing the named
        ids over 'index-20' type references which might get reassigned."""
        return self.pythonDocRef

class BlockEnd(Icon):
    def __init__(self, primary, window=None, location=None):
        Icon.__init__(self, window)
        self.primary = primary
        self.sites.add('seqIn', 'seqIn', 1 + comn.BLOCK_INDENT, 0)
        self.sites.add('seqOut', 'seqOut', 1, 2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + branchFootImage.width, y + branchFootImage.height)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            self.drawList = [((0, 0), branchFootImage)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def select(self, select=True, selectPrimary=False):
        if selectPrimary:
            self.primary.select(select)

    def primaryRect(self):
        return self.primary.rect

    def doLayout(self, outSiteX, outSiteY, layout):
        seqSiteX = outSiteX - self.sites.seqIn.xOffset
        seqSiteY = outSiteY - self.sites.seqIn.yOffset
        width, height = branchFootImage.size
        top = seqSiteY - 1
        left = seqSiteX - 1
        self.rect = (left, top, left + width, top + height)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = branchFootImage.size
        return [iconlayout.Layout(self, width, height, 1)]

    def inRectSelect(self, rect):
        return False

    def selectionRect(self):
        return None

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, primary=None)

    def siteRightOfPart(self, partId):
        return 'seqOut'

class ImageIcon(Icon):
    def __init__(self, image, window, location=None):
        Icon.__init__(self, window)
        self.image = image.convert('RGBA')
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + image.width, y + image.height)

    def draw(self, toDragImage=None, location=None, clip=None, style=0):
        if self.drawList is None:
            self.drawList = [((0, 0), self.image)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def snapLists(self, forCursor=False):
        return {}

    def layout(self, location=None):
        # Can't use Base class layout method because it depends on having an output site
        if location is not None:
            self.rect = moveRect(self.rect, location)

    def doLayout(self, x, bottom, _layout):
        self.rect = (x, bottom - self.image.height, x + self.image.width, bottom)
        self.layoutDirty = False

    def calcLayouts(self):
        return [iconlayout.Layout(self, self.image.width, self.image.height, 0)]

    def execute(self):
        return None

    def dumpName(self):
        return "image"

class ErrorHighlight:
    """Attached to errHighlight field of icons which need to receive error highlighting
    (pink tint), and contain information needed to construct explanation dialog."""
    # Note that while this currently contains only a reasonText field, it is defined
    # as a class because future versions will likely add more information, such as
    # different coloring or highlight style for other types of errors, and possibly a
    # way to refer to other icon(s) involved in the error.
    def __init__(self, reasonText):
        self.text = reasonText

class TypeAnnHighlight:
    """Attached to errHighlight field of icons that are being used for type annotation
    (grayed text)."""
    text = "Type annotation (not an error)"

def pasteImageWithClip(dstImage, srcImage, pos, clipRect):
    """clipping rectangle is in the coordinate system of the destination image"""
    if clipRect is None:
        dstImage.paste(srcImage, box=pos, mask=srcImage)
        return
    cl, ct, cr, cb = clipRect
    pl, pt = pos
    pr, pb = pl + srcImage.width, pt + srcImage.height
    # Pasted region is entirely outside of the clip rectangle
    if cl > pr or pl > cr or ct > pb or pt > cb:
        return
    # Pasted region is entirely inside of the clip rectangle
    if pl >= cl and pr <= cr and pt >= ct and pb <= cb:
        dstImage.paste(srcImage, box=pos, mask=srcImage)
        return
    # Find the area that will be drawn
    dl = max(pl, cl)
    dt = max(pt, ct)
    dr = min(pr, cr)
    db = min(pb, cb)
    # Crop the pasted image to the drawn area transformed to its coordinates
    croppedImage = srcImage.crop((dl - pl, dt - pt, dr - pl, db - pt))
    # Paste the cropped image in the drawn area
    dstImage.paste(croppedImage, box=(dl, dt), mask=croppedImage)

def tintSelectedImage(image, style):
    if style & STYLE_OUTLINE:
        alphaImg = image.getchannel('A')
        outlineMask = ImageMath.eval("convert(a*255, 'L')", a=alphaImg)
    else:
        outlineMask = None
    color = None
    # Note that the order of the if clauses below determines the relative priority of
    # each of the color highlights (rather than blending, we choose the most important)
    if style & STYLE_EXEC_ERR:
        color = EXEC_ERR_TINT
    elif style & STYLE_PENDING_REMOVE:
        color = PENDING_REMOVE_TINT
    elif style & STYLE_IMMEDIATE_COPY:
        color = IMMEDIATE_COPY_TINT
    elif style & STYLE_SELECTED:
        color = SELECT_TINT
    elif style & STYLE_SYNTAX_ERR:
        color = SYNTAX_ERR_TINT
    elif style & STYLE_TYPE_ANN:
        color = TYPE_ANN_TINT
    elif outlineMask is None:  # No outline and no additional coloring
        return image
    if color is not None:
        alphaImg = image.getchannel('A')
        colorImg = Image.new('RGBA', (image.width, image.height), color=color)
        colorImg.putalpha(alphaImg)
        image = Image.blend(image, colorImg, color[3] / 255.0)
    if outlineMask is not None:
        outlineImg = Image.new('RGBA', (image.width, image.height),
                color=SHOW_OUTLINE_TINT)
        outlineImg.putalpha(outlineMask)
        outlineImg.paste(image, mask=image)
        return outlineImg
    return image

def incorporateStmtCommentLayouts(layouts, commentLayouts, margin):
    """extend each layout in the list (layouts) to incorporate the best matching
    statement comment from commentLayouts.  Best-matching means fits within margin
    and adds the least badness."""
    widthRankedComments = sorted(commentLayouts, key=lambda l: l.width)
    heightRankedComments = sorted(commentLayouts, key=lambda l: l.height)
    for layout in layouts:
        for commentLayout in widthRankedComments:
            if commentLayout.height <= layout.height and \
                    layout.width + commentLayout.width + STMT_COMMENT_OFFSET <= margin:
                bestCommentLayout = commentLayout
                break
        else:
            for commentLayout in heightRankedComments:
                if layout.width + commentLayout.width + STMT_COMMENT_OFFSET <= margin:
                    bestCommentLayout = commentLayout
                    break
            else:
                bestCommentLayout = widthRankedComments[0]
        # Since the comment will only extend to the right of and (possibly) below, the
        # existing layout, it will not affect any of the offsets, so just extend size
        layout.width += bestCommentLayout.width + STMT_COMMENT_OFFSET
        layout.height = max(layout.height, bestCommentLayout.height)
        layout.stmtCommentLayout = bestCommentLayout
    return layouts

def drawSeqSites(ic, img, imgX, imgY, blockIndent=False, boxRightEdge=None):
    """Draw sequence (in and out) sites on a rectangular boxed icon.  If blockIndent is
    set to true, also add an extension to the icon body downward by BLOCK_SEQ_MARGIN, and
    rightward (if necessary) from boxRightEdge to the seqOut site.  Note that
    boxRightEdge is in the coordinates of img (as opposed to being relative to the icon
    rectangle), and therefore not offset by imgX."""
    # Draw seqIn site (will always be on icon body)
    siteX = ic.sites.seqIn.xOffset - imgX
    siteY = ic.sites.seqIn.yOffset - imgY
    img.putpixel((siteX - 1, siteY + 1),  comn.OUTLINE_COLOR)
    img.putpixel((siteX, siteY + 1 ), comn.OUTLINE_COLOR)
    img.putpixel((siteX + 1, siteY + 1), comn.OUTLINE_COLOR)
    img.putpixel((siteX, siteY + 2), comn.OUTLINE_COLOR)
    # Draw seqOut site.  Block-owners have either a bump or a connector holding the site.
    siteX = ic.sites.seqOut.xOffset - imgX
    siteY = ic.sites.seqOut.yOffset - imgY
    if blockIndent:
        extRight = siteX + 1
        if boxRightEdge is not None and boxRightEdge <= extRight:
            # Add connector rectangle extending to the seqOut site
            extLeft = boxRightEdge - 4
            extTop = siteY - BLOCK_SEQ_MARGIN
            draw = ImageDraw.Draw(img)
            draw.rectangle((extLeft, extTop, extRight, siteY),
                fill=comn.ICON_BG_COLOR,  outline=comn.OUTLINE_COLOR)
            img.putpixel((extLeft+1, extTop), comn.ICON_BG_COLOR)
            img.putpixel((extLeft+2, extTop), comn.ICON_BG_COLOR)
            img.putpixel((extLeft+3, extTop), comn.ICON_BG_COLOR)
            img.putpixel((extRight - 1, extTop + 1), comn.OUTLINE_COLOR)
            img.putpixel((extRight - 2, extTop + 1), comn.OUTLINE_COLOR)
        else:
            # Add just a bump
            img.paste(seqOutBumpImage, (siteX - 3, siteY - seqOutBumpImage.height + 1))
    else:
        # Just draw the seqOut site with no extra doodads
        img.putpixel((siteX - 1, siteY - 1), comn.OUTLINE_COLOR)
        img.putpixel((siteX,     siteY - 1), comn.OUTLINE_COLOR)
        img.putpixel((siteX + 1, siteY - 1), comn.OUTLINE_COLOR)
        img.putpixel((siteX,     siteY - 2), comn.OUTLINE_COLOR)

def drawSeqSiteConnection(fromIcon, image=None, clip=None):
    """Draw connection line between fromIcon's seqIn site and whatever it connects to.
    Draws to either the window (from toIcon) or to the specified image.  If clip is
    specified, clips drawing to the given rectangle."""
    # Find the top and bottom of the connector at toIcon's seqIn site
    toIcon = fromIcon.nextInSeq()
    if toIcon is None:
        return
    x, fromY = fromIcon.posOfSite('seqOut')
    _, toY = toIcon.posOfSite('seqIn')
    # If drawing to window, translate endpoints and clip rectangle to image coords
    if image is None:
        draw = toIcon.window.draw
        img = toIcon.window.image
        x, fromY = toIcon.window.contentToImageCoord(x, fromY)
        _, toY = toIcon.window.contentToImageCoord(x, toY)
        if clip is not None:
            l, t = toIcon.window.contentToImageCoord(clip[0], clip[1])
            r, b = toIcon.window.contentToImageCoord(clip[2], clip[3])
            clip = l, t, r, b
    else:
        draw = ImageDraw.Draw(image)
        img = image
    # Combine the specified clip rectangle with the image rectangle to determine the
    # final clip rectangle
    if clip is None:
        clip = 0, 0, img.width, img.height
    else:
        l, t, r, b = clip
        clip = max(0, l), max(0, t), min(img.width, r), min(img.height, b)
    # Determine which parts to draw, and where to draw them, based solely upon the
    # distance we're filling (ignoring clipping)
    if fromY == toY:
        return
    topDot = fromY + 1
    bottomDot = None if toY - fromY < 2 else toY - 1
    lineTop = fromY + 1
    lineBottom = toY - 1
    dotLeft = x - 1
    dotRight = x + 1
    # Apply additional clipping based upon the specified clip rectangle
    if clip is not None:
        l, t, r, b = clip
        if dotRight < l or dotLeft > r or lineBottom < t or lineTop > b:
            return
        if dotLeft < l:
            dotLeft = None
        if dotRight > r:
            dotRight = None
        if x < l or x > r:
            lineTop = None
        else:
            lineTop = max(t, lineTop)
            lineBottom = min(b, lineBottom)
        if topDot < t or topDot >= b:
            topDot = None
        if bottomDot is not None and (bottomDot < t or bottomDot >= b):
            bottomDot = None
    # Draw whatever was not clipped out
    if topDot is not None:
        if  dotLeft is not None:
            img.putpixel((dotLeft, topDot), SEQ_CONNECT_COLOR)
        if dotRight is not None:
            img.putpixel((dotRight, topDot), SEQ_CONNECT_COLOR)
    if bottomDot is not None:
        if  dotLeft is not None:
            img.putpixel((dotLeft, bottomDot), SEQ_CONNECT_COLOR)
        if dotRight is not None:
            img.putpixel((dotRight, bottomDot), SEQ_CONNECT_COLOR)
    if lineTop is not None:
        draw.line((x, lineTop, x, lineBottom), SEQ_CONNECT_COLOR)

def seqConnectorTouches(fromIcon, rect):
    """Return True if the icon is connected via its seqOut site and the sequence site
    connector line (to the icon below) intersects rectangle, rect."""
    toIcon = fromIcon.nextInSeq()
    if toIcon is None:
        return False
    fromX, fromY = fromIcon.posOfSite('seqOut')
    toX, toY = toIcon.posOfSite('seqIn')
    l, t, r, b = rect
    if fromX < l or fromX > r:
        return False
    if fromY < t and toY < t:
        return False
    if toY > b and fromY > b:
        return False
    return True

def seqRuleTouches(ic, rect):
    """Return True if the icon draws an indent rule line and it intersects rect"""
    if not hasattr(ic, 'blockEnd'):
        return False
    x, toY = ic.blockEnd.posOfSite('seqOut')
    fromY = ic.posOfSite('seqOut')[1]
    l, t, r, b = rect
    if x < l or x > r:
        return False
    if fromY < t and toY < t:
        return False
    if toY > b and fromY > b:
        return False
    return True

def drawSeqRule(ic, clip=None, image=None):
    """Draw connection line spanning indented code block below ic."""
    if not hasattr(ic, 'blockEnd'):
        return
    x, toY = ic.blockEnd.posOfSite('seqOut')
    toY -= BLOCK_SEQ_MARGIN
    fromY = ic.posOfSite('seqOut')[1] - 1
    if clip is not None:
        # Clip the line to within the clip rectangle (rules are always vertical and
        # drawn downward and rectangles are ordered left, top, right, bottom).
        l, t, r, b = clip
        if x < l or x > r:
            return
        if fromY < t:
            if toY < t:
                return
            fromY = t
        if toY > b:
            if fromY > b:
                return
            toY = b
    if image is None:
        draw = ic.window.draw
        _x, fromY = ic.window.contentToImageCoord(x, fromY)
        x, toY = ic.window.contentToImageCoord(x, toY)
    else:
        draw = ImageDraw.Draw(image)
    draw.line((x, fromY, x, toY), SEQ_RULE_COLOR)

def findSeqStart(ic, toStartOfBlock=False):
    """Find the first icon of a sequence, either the very start (where it attaches to the
    window (default) or to the top icon in its code block (toStartOfBlock=True).  Note
    that this will not return the window's module anchor icon (it will return the first
    icon below it)."""
    moduleAnchorIc = ic.window.modSeqIcon
    while True:
        if not hasattr(ic.sites, 'seqIn'):
            return ic
        prevIc = ic.sites.seqIn.att
        if prevIc is None or prevIc is moduleAnchorIc:
            return ic
        if toStartOfBlock and hasattr(prevIc, 'blockEnd'):
            return ic
        ic = prevIc
        if isinstance(ic, BlockEnd):
            # Shortcut around blocks significantly improves performance
            ic = ic.primary

def findBlockOwner(ic):
    """Search up the sequence from ic to find and return the icon that owns its code
    block.  Returns None if the block is in the outermost block of the sequence."""
    return findSeqStart(ic, toStartOfBlock=True).prevInSeq()

def findSeqEnd(ic, toEndOfBlock=False):
    while True:
        if hasattr(ic, 'blockEnd'):
            ic = ic.blockEnd
        if not hasattr(ic.sites, 'seqOut'):
            return ic
        nextIc = ic.sites.seqOut.att
        if nextIc is None:
            return ic
        if toEndOfBlock and isinstance(nextIc, BlockEnd):
            return ic
        ic = nextIc

def traverseSeq(ic, includeStartingIcon=True, reverse=False, hier=False,
        restrictToPage=None, skipInnerBlocks=False, inclStmtComments=False):
    """Traverse either top-level icons (hier=False) or all icons (hier-True) from
    ic to the start (reverse=True) or end (reverse=False) of the sequence in which they
    appear.  restrictToPage will stop the traversal when it leaves the boundary of the
    specified page.  Specifying skipInnerBlocks=True will skip over nested code blocks.
    inclStmtComments will yield statement comment icons along with the code icons that
    it normally produces (line comments and verticalBlank icons are always included).
    The window's module anchor icon is always excluded (both if passed as ic, and if
    encountered in upward (reverse=True) traversal."""
    moduleAnchor = ic.window.modSeqIcon
    if includeStartingIcon and ic is not moduleAnchor:
        if hier:
            yield from ic.traverse(inclStmtComment=inclStmtComments)
        else:
            yield ic
    if reverse:
        while True:
            if not hasattr(ic.sites, 'seqIn'):
                return
            if skipInnerBlocks and isinstance(ic, BlockEnd):
                ic = ic.primary.sites.seqIn.att
            else:
                ic = ic.sites.seqIn.att
            if ic is None or ic is moduleAnchor:
                return
            if restrictToPage is not None and ic.window.topIcons[ic] != restrictToPage:
                return
            if hier:
                yield from ic.traverse(inclStmtComment=inclStmtComments)
            else:
                yield ic
    else:
        while True:
            if not hasattr(ic.sites, 'seqOut'):
                return
            if skipInnerBlocks and hasattr(ic, 'blockEnd'):
                ic = ic.blockEnd.sites.seqOut.att
            else:
                ic = ic.sites.seqOut.att
            if ic is None:
                return
            if restrictToPage is not None and ic.window.topIcons[ic] != restrictToPage:
                return
            if hier:
                yield from ic.traverse(inclStmtComment=inclStmtComments)
            else:
                yield ic

def traverseOwnedBlock(blockOwnerIc, hier=False, skipInnerBlocks=False,
        inclStmtComments=False):
    ic = blockOwnerIc.nextInSeq()
    while ic is not None and ic is not blockOwnerIc.blockEnd:
        if hier:
            yield from ic.traverse(inclStmtComment=inclStmtComments)
        else:
            yield ic
        if not hasattr(ic.sites, 'seqOut'):
            return
        if skipInnerBlocks and hasattr(ic, 'blockEnd'):
            ic = ic.blockEnd.sites.seqOut.att
        else:
            ic = ic.sites.seqOut.att

def insertSeq(seqStartIc, atIc, before=False):
    seqEndIc = findSeqEnd(seqStartIc)
    if before:
        prevIcon = atIc.sites.seqIn.att
        if prevIcon is None:
            filefmt.moveIconToPos(seqStartIc, atIc.pos())
        else:
            prevIcon.replaceChild(seqStartIc, 'seqOut')
        atIc.replaceChild(seqEndIc, 'seqIn')
    else:
        nextIcon = atIc.sites.seqOut.att
        atIc.replaceChild(seqStartIc, 'seqOut')
        if nextIcon is not None:
            nextIcon.replaceChild(seqEndIc, 'seqIn')

def traverseAttrs(ic, includeStart=True):
    if includeStart:
        yield ic
    while ic.hasSite('attrIcon') and ic.sites.attrIcon.att is not None:
        ic = ic.sites.attrIcon.att
        yield ic

def findLastAttrIcon(ic):
    for i in traverseAttrs(ic):
        pass
    return i

def rightmostSite(ic, ignoreAutoParens=False):
    """Return the site that is rightmost on an icon and its children.  For most icons,
    that is an attribute site, but for unary or binary operations with the right operand
    missing, it can be an input site.  While binary op icons may have a fake invisible
    attribute site, it should be used carefully (if ever).  ignoreAutoParens prevents
    choosing auto-paren attribute site of BinOpIcon, even if it the rightmost."""
    if hasattr(ic, 'hasParens') and (not ic.hasParens or ignoreAutoParens):
        if ic.rightArg() is None:
            if ic.__class__.__name__ == "IfExpIcon":
                return ic, "falseExpr"
            return ic, 'rightArg'
        return rightmostSite(ic.rightArg(), ignoreAutoParens)
    lastCursorSite = ic.sites.lastCursorSite()
    if lastCursorSite is None:
        if ic.hasSite('seqOut'):
            # BlockEnd (I think) is the only case with no site on the right
            return ic, 'seqOut'
        print("rightmostSite passed icon with no acceptable cursor site", ic.dumpName())
        return ic, list(ic.sites.allSites())[-1].name
    if lastCursorSite[:10] == 'cprhIcons_':
        # There's some question whether lastCursorSite() should be returning non-cursor-
        # capable sites, but because traversal ordering is now used for other purposes,
        # it is possible to get a non-traversable site (for this one pargicular case).
        lastCursorSite = ic.sites.argIcons[-1].name
    child = ic.childAt(lastCursorSite)
    if child is None:
        return ic, lastCursorSite
    return rightmostSite(child, ignoreAutoParens)

def rightmostFromSite(ic, siteId):
    """Returns rightmost icon and siteId for an icon site.  Same as rightmostSite, but
    passed the parent icon and site to handle the empty-site case (which would otherwise
    accompany the call to rightmostIcon in the most common use-case)."""
    argIcon = ic.childAt(siteId)
    if argIcon is None:
        return ic, siteId
    return rightmostSite(argIcon)

def findAttrOutputSite(ic, inclEntryIc=True):
    if hasOutputSite(ic):
        return ic
    for i in ic.parentage():
        if not inclEntryIc and isEntryIcon(i):
            return None
        if hasOutputSite(i):
            return i
    return None

def hasOutputSite(ic):
    return ic.hasSite('output') and not (ic.__class__.__name__ == 'EntryIcon' and
        ic.attachedToAttribute())

def containingRect(icons):
    maxRect = comn.AccumRects()
    for ic in icons:
        maxRect.add(ic.rect)
    return maxRect.get()

def rectSize(rect):
    l, t, r, b = rect
    return r - l, b - t

def pointInRect(point, rect):
    l, t, r, b = rect
    x, y = point
    return l <= x < r and t <= y < b

def moveRect(rect, newLoc):
    l, t, r, b = rect
    x, y = newLoc
    return x, y, x + r - l, y + b - t

def addPoints(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return x1 + x2, y1 + y2

def subtractPoints(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return x1 - x2, y1 - y2

def rectWithinXBounds(rect, leftBound, rightBound):
    left, top, right, bottom = rect
    return left > leftBound and right < rightBound

def _allSubclasses(cls):
    """Like the class.__subclass__ method, but returns all of the subclasses below cls"""
    for subclass in cls.__subclasses__():
        yield from _allSubclasses(subclass)
        yield subclass

def _getIconClasses():
    """Returns a dictionary mapping Icon subclass names to classes.  This allows the
    clipboard paste command to find and instantiate any icon by name, without requiring
    the icon module to import every module that defines icons."""
    if _getIconClasses.cachedDict is None:
        _getIconClasses.cachedDict = {cls.__name__:cls for cls in _allSubclasses(Icon)}
    return _getIconClasses.cachedDict
_getIconClasses.cachedDict = None

def dumpPlaceList(placeList):
    if placeList is None:
        print('<None>')
        return
    for e in placeList:
        if isinstance(e, (list,tuple)):
            print('[', end='')
            for i, ic in enumerate(e):
                name = 'None' if ic is None else ic.dumpName()
                comma = ', ' if i < len(e) - 1 else ''
                print(name + comma, end='')
            print('] ', end='')
        else:
            print(e.dumpName() + ' ', end='')
    print()

def argSaveText(breakLevel, site, cont, export):
    """Create a filefmt.SegmentedText string representing an argument icon (tree) at
    a given site.  If the site is empty, place the $Empty$ macro, instead."""
    if site.att is None:
        return filefmt.SegmentedText(None if export else "$Empty$")
    return site.att.createSaveText(breakLevel, cont, export)

def addArgSaveText(saveText, breakLevel, site, cont, export):
    """Convenience function to append the result of argSaveText to saveText at the same
    break-level as is being passed to argSaveText."""
    saveText.concat(breakLevel, argSaveText(breakLevel, site, cont, export), cont)

def seriesSaveText(breakLevel, seriesSite, cont, export, allowTrailingComma=False,
        allowEmpty=True):
    """Create a filefmt.SegmentedText string representing a series of arguments.  If
    any but the first argument of a single-entry list has no icon, place the $Empty$
    macro at the site.  If allowTrailingComma is specified, the second position of a
    two-element series will not be marked with $Empty$ if it is empty (used when the
    series can represent a non-parenthesized tuple, such as =, for, return, and yield).
    if allowEmpty is set to False, a completely empty series will get a $Empty$ macro."""
    if len(seriesSite) == 0 or len(seriesSite) == 1 and seriesSite[0].att is None:
        return filefmt.SegmentedText(None if allowEmpty or export else '$Empty$')
    args = [argSaveText(breakLevel, site, cont, export) for site in seriesSite]
    combinedText = args[0]
    if allowTrailingComma and len(args) == 2 and seriesSite[1].att is None:
        combinedText.add(None, ', ', cont)
    else:
        for arg in args[1:]:
            combinedText.add(None, ', ', cont)
            combinedText.concat(breakLevel, arg, cont)
    return combinedText

def addSeriesSaveText(saveText, breakLevel, seriesSite, cont, export,
        allowTrailingComma=False, allowEmpty=True):
    """Convenience function to append the result of seriesSaveText to saveText at the
    same break-level as is being passed to seriesSaveText.  If allowTrailingComma is
    specified, the second position of a two-element series will not be marked with
    $Empty$ if it is empty (used when the series can represent a non-parenthesized tuple,
    such as =, for, return, and yield)."""
    saveText.concat(breakLevel, seriesSaveText(breakLevel, seriesSite, cont, export,
        allowTrailingComma=allowTrailingComma, allowEmpty=allowEmpty), cont)

def addAttrSaveText(saveText, ic, parentBreakLevel, cont, export):
    """If the given icon has an attribute attached, compose and append the text from the
     attribute icon to saveText."""
    if ic.sites.attrIcon.att is None:
        return saveText
    # Note, below that the parent break level is passed to the attribute icon, so
    # that a series of attributes (a.b.c.d) will all end up at the same level (as
    # opposed to inappropriately nested in deeper and deeper levels)
    attrText = ic.sites.attrIcon.att.createSaveText(parentBreakLevel, cont, export)
    if hasattr(ic.sites.attrIcon.att, 'sticksToAttr'): # No break before subscript or call
        saveText.concat(None, attrText)
    else:
        saveText.concat(parentBreakLevel + 1, attrText, cont)
    return saveText

def argTextRepr(site):
    if site.att is None:
        return "None"
    return site.att.textRepr()

def seriesTextRepr(seriesSite):
    argText = ""
    for site in seriesSite:
        if site.att is None:
            argText = argText + "None, "
        else:
            argText = argText + site.att.textRepr() + ", "
    if len(argText) > 0:
        argText = argText[:-2]
    return argText

def attrTextRepr(ic):
    if ic.sites.attrIcon.att is None:
        return ""
    return ic.sites.attrIcon.att.textRepr()

def dumpHier(ic, indent=0, site=None):
    siteStr = (" " + site) if site is not None else ""
    print("   " * indent + siteStr, ic.dumpName(), '#' + str(ic.id))
    if hasattr(ic, 'stmtComment'):
        dumpHier(ic.stmtComment, indent+1)
    for child in ic.children():
        dumpHier(child, indent+1, ic.siteOf(child))

def composeAttrAst(ic, icAst):
    if ic.sites.attrIcon.att:
        return ic.sites.attrIcon.att.createAst(icAst)
    return icAst

def createStmtAst(ic):
    """Create the ast corresponding to a top-level icon (ic).  For statements, this
    simply means calling the .createAst() method, but for expressions this additionally
    entails wrapping it in an ast.Expr() node."""
    stmtAst = ic.createAst()
    if stmtAst is None:
        return None
    if stmtAst.__class__ in stmtAstClasses:
        return stmtAst
    return ast.Expr(stmtAst, lineno=ic.id, col_offset=0)

def yStretchImage(img, stretchPts, desiredHeight):
    """Function used to stretch parens/brackets/braces over vertically wrapped list-type
    content."""
    if desiredHeight <= img.height:
        return img.copy()
    newImg = Image.new('RGBA', (img.width, desiredHeight))
    insertCount = (desiredHeight - img.height)
    # Divide in insertion across all stretch points, but round up
    insertCountPerStretch = (insertCount + len(stretchPts) - 1) // len(stretchPts)
    excessStretch = insertCountPerStretch * len(stretchPts) - insertCount
    oldY = newY = 0
    for stretchCnt, stretchPt in enumerate(stretchPts):
        copyImg = img.crop((0, oldY, img.width, stretchPt + 1))
        newImg.paste(copyImg, (0, newY, img.width, newY + copyImg.height))
        dupImg = img.crop((0, stretchPt, img.width, stretchPt+1))
        newY += copyImg.height
        excessAdjCnt = insertCountPerStretch - (1 if stretchCnt < excessStretch else 0)
        for i in range(excessAdjCnt):
            newImg.paste(dupImg, (0, newY + i, img.width, newY + i + 1))
        newY += excessAdjCnt
        oldY += copyImg.height
    copyImg = img.crop((0, oldY, img.width, img.height + 1))
    newImg.paste(copyImg, (0, newY, img.width, newImg.height+1))
    return newImg

def createAstDataRef(ic, value=None):
    """Icons representing data objects which need their execution to return a particular
    object (to satisfy an "is" comparison) can call this function to create an AST for
    a reference to the object, rather than creating an AST that will create a new one.
    The object is taken from ic.object, unless "value" is specified, in which case, that
    value is used.  The function enters the value in a special dictionary in the
    execution namespace (__windowExecContext__), indexed by icon id, and creates and
    returns an AST representing code to fetch the value from that dictionary."""
    if value is None:
        value = ic.object
    ic.window.globals['__windowExecContext__'][ic.id] = value
    nameAst = ast.Name(id='__windowExecContext__', ctx=ast.Load(), lineno=ic.id,
        col_offset=0)
    iconIdAst = ast.Index(value=ast.Constant(value=ic.id, lineno=ic.id,
        col_offset=0))
    return ast.Subscript(value=nameAst, slice=iconIdAst, ctx=ast.Load(), lineno=ic.id,
        col_offset=0)

def registerAstDecodeFallback(fn):
    """Register a function to create a placeholder icon when createFromAst fails"""
    global astDecodeFallback
    astDecodeFallback = fn

def registerIconCreateFn(astNodeClass, createFn):
    """Register a function for creating icons of a given AST node type"""
    astCreationFunctions[astNodeClass] = createFn

def createFromAst(astNode, window):
    """Given an AST Node, create icons from it."""
    # If the ast has property iconCreationFunction, a user-defined macro has attached
    # its own function for creating an icon.  Pass the node to that function instead of
    # the normal one for creating icons for the given AST type
    if hasattr(astNode, 'macroAnnotations'):
        macroName, macroArgs, iconCreateFn, argAsts = astNode.macroAnnotations
        if iconCreateFn is not None:
            return iconCreateFn(astNode, macroArgs, argAsts, window)
    # Look up the creation function for the given AST type, call it, and return the result
    creationFn = astCreationFunctions.get(astNode.__class__)
    if creationFn is None:
        return astDecodeFallback(astNode, window)
    return creationFn(astNode, window)

def createIconsFromBodyAsts(bodyAsts, window):
    return astCreationFunctions["bodyAsts"](bodyAsts, window)

def placementListIter(placeList, stopAfterIdx=None, stopAfterSeriesIdx=None,
        includeEmptySites=False, includeEmptySeriesSites=True):
    """Iterate through placement list of the form accepted by Icon.placeArgs, returning
    icon, index in the place list of the icon, and if the icon came from a series, the
    index in to the series from which it was taken."""
    for placeListIdx, placeItem in enumerate(placeList):
        if isinstance(placeItem, (list, tuple)):
            for seriesIdx, ic in enumerate(placeItem):
                if ic is not None or includeEmptySeriesSites:
                    yield ic, placeListIdx, seriesIdx
                if stopAfterIdx == placeListIdx and stopAfterSeriesIdx == seriesIdx:
                    return
        else:
            if placeItem is not None or includeEmptySites:
                yield placeItem, placeListIdx, None
        if stopAfterIdx == placeListIdx:
            return

def firstPlaceListIcon(placeList):
    for ic, placeListIdx, seriesIdx in placementListIter(placeList):
        if ic is not None:
            return ic, placeListIdx, seriesIdx
    return None, None, None

def placeListAtEnd(argList, thruIdx, thruSeriesIdx):
    """Return True if placement list indices, thruIdx and thruSeriesIdx, point to the
    last element of placement list, argList."""
    if thruIdx is None:
        return False
    if thruIdx == len(argList) - 1:
        if thruSeriesIdx is None:
            return True
        if isinstance(argList[-1], (list, tuple)):
            if thruSeriesIdx == len(argList[-1]) - 1:
                return True
    return False

def placeListEmpty(argList, thruIdx=None, thruSeriesIdx=None):
    """"Return True if placement, argList, through indices thruIdx and thruSeriesIdx,
    consists only of empty sites/series."""
    for _ in placementListIter(argList, stopAfterIdx=thruIdx, includeEmptySites=False,
            includeEmptySeriesSites=False, stopAfterSeriesIdx=thruSeriesIdx):
        return False
    return True  # Only empty sites used

def placeListIdxOf(placeList, ic):
    """Return the place list index and series index of an icon from a placement list."""
    #... this is currently unused and not well tested, but left in because it is
    #    potentially useful functionality.
    for placeListIdx, placeItem in enumerate(placeList):
        if isinstance(placeItem, (list, tuple)):
            for seriesIdx, seriesIc in enumerate(placeItem):
                if seriesIc is ic:
                    return placeListIdx, seriesIdx
        else:
            if placeItem is ic:
                return placeListIdx, None
    return None, None

def validateCompatibleChild(child, parent, siteOrSeriesName):
    if child is None:
        return True  # Anything can have an empty site
    if isEntryIcon(child):
        return True  # Anything can host an entry icon
    if parent.hasSite(siteOrSeriesName) and parent.isCursorOnlySite(siteOrSeriesName):
        return False  # Can't put anything but an entry icon on a cursor-only site
    if iconsites.isSeriesSiteId(siteOrSeriesName):
        # Caller can pass either the series name or a site name in the series
        siteOrSeriesName, _ = iconsites.splitSeriesSiteId(siteOrSeriesName)
    parentSiteOrSeries = getattr(parent.sites, siteOrSeriesName)
    for childParentSite in child.sites.parentSites():
        if iconsites.matingSiteType[parentSiteOrSeries.type] == childParentSite.type:
            break
    else:
        return False
    return True

def chooseOutSeqSites(ic, forDrag):
    """Takes an icon that has an output site as argument, and decides whether the icon
    should display its output site, its sequence sites, or both.  Returns two boolean
    values: 1) whether to display sequence sites and 2) whether to draw its output site.
    This will also command the icon to draw 'referred' sequence sites, even when its own
    sequence sites are technically disabled, so that they will show up for icons with
    input sites coincident with the left margin (such as assignments, naked tuples, and
    binary operators)."""
    parent = ic.parent()
    if parent is None:
        needSeqSites = True
    else:
        highestIc = iconsites.highestCoincidentIcon(ic)
        if highestIc.parent() is None:
            needSeqSites = ic.posOfSite('seqIn') == highestIc.posOfSite('seqIn') and \
                ic.posOfSite('seqOut') == highestIc.posOfSite('seqOut')
        else:
            needSeqSites = False
    needOutSite = ic.parent() is not None or ic.sites.seqIn.att is None and (
            ic.sites.seqOut.att is None or forDrag)
    return needSeqSites, needOutSite

def cursorInText(textOriginPos, clickPos, font, text, padLeft=0, padRight=0):
    """Determine if a given window x,y position, clickPos is within a displayed text
    string, starting at textOriginPos (by left edge and text center Y).  If so, return
    the (cursor) position within the text closest to clickPos, and the x,y window
    coordinate location for that cursor (y center).  If the clickpos is not within
    TEXT_MARGIN of the text, return (None, None)."""
    textOriginX, textCenterY = textOriginPos
    textXOffset = clickPos[0] - textOriginX
    textWidth, textHeight = font.getsize(text)
    textWidth += padLeft + padRight
    textBoxLeft = textOriginX - TEXT_MARGIN - padLeft
    textBoxTop = textCenterY - textHeight // 2 - TEXT_MARGIN
    textRight = textBoxLeft + textWidth + 2 * TEXT_MARGIN
    textBoxBottom = textBoxTop + textHeight + 2 * TEXT_MARGIN
    textBox = (textBoxLeft, textBoxTop, textRight, textBoxBottom)
    if not pointInRect(clickPos, textBox):
        return None, None
    cursorIdx = comn.findTextOffset(font, text, textXOffset)
    cursorX = textOriginX + font.getsize(text[:cursorIdx])[0]
    return cursorIdx, (cursorX, textCenterY)

def isEntryIcon(ic):
    """Hack for modularity issues preventing import of entryicon"""
    return ic.__class__.__name__ == 'EntryIcon'