# Copyright Mark Edel  All rights reserved
import sys

from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
import python_g
import ast
import heapq
import operator
import re
import functools
import itertools

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

isSeriesRe = re.compile(".*_\\d*$")

binOpPrecedence = {'+':10, '-':10, '*':11, '/':11, '//':11, '%':11, '**':14,
 '<<':9, '>>':9, '|':6, '^':7, '&':8, '@':11, 'and':3, 'or':2, 'in':5, 'not in':5,
 'is':5, 'is not':5, '<':5, '<=':5, '>':5, '>=':5, '==':5, '!=':5, '=':-1, ':':-1}

unaryOpPrecedence = {'+':12, '-':12, '~':13, 'not':4, '*':-1, '**':-1, 'yield from':-1,
 'await':-1}

binOpFn = {'+':operator.add, '-':operator.sub, '*':operator.mul, '/':operator.truediv,
 '//':operator.floordiv, '%':operator.mod, '**':operator.pow, '<<':operator.lshift,
 '>>':operator.rshift, '|':operator.or_, '^':operator.xor, '&':operator.and_,
 '@':lambda x,y:x@y, 'and':lambda x,y:x and y, 'or':lambda x,y:x or y,
 'in':lambda x,y:x in y, 'not in':lambda x,y:x not in y, 'is':operator.is_,
 'is not':operator.is_not, '<':operator.lt, '<=':operator.le, '>':operator.gt,
 '>=':operator.ge, '==':operator.eq, '!=':operator.ne}

binOpAsts = {'+':ast.Add, '-':ast.Sub, '*':ast.Mult, '/':ast.Div, '//':ast.FloorDiv,
 '%':ast.Mod, '**':ast.Pow, '<<':ast.LShift, '>>':ast.RShift, '|':ast.Or, '^':ast.BitXor,
 '&':ast.BitAnd}

compareAsts = {'is':ast.Is, 'is not':ast.IsNot, '<':ast.Lt, '<=':ast.LtE, '>':ast.Gt,
 '>=':ast.GtE, '==':ast.Eq, '!=':ast.NotEq}

unaryOpFn = {'+':operator.pos, '-':operator.neg, '~':operator.inv, 'not':operator.not_,
 '*':lambda a:a, '**': lambda a:a, 'await': lambda a:a}

unaryOpAsts = {'+':ast.UAdd, '-':ast.USub, '~':ast.Invert, 'not':ast.Not}

namedConsts = {'True':True, 'False':False, 'None':None}

stmtAstClasses = {ast.Assign, ast.AugAssign, ast.While, ast.For, ast.AsyncFor, ast.If,
 ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Return, ast.With,
 ast.AsyncWith, ast.Delete, ast.Pass, ast.Continue, ast.Break, ast.Global, ast.Nonlocal}

parentSiteTypes = {'output', 'attrOut', 'cprhOut'}
childSiteTypes = {'input', 'attrIn', 'cprhIn'}
matingSiteType = {'output':'input', 'input':'output', 'attrOut':'attrIn',
 'attrIn':'attrOut', 'seqOut':'seqIn', 'seqIn':'seqOut', 'cprhIn':'cprhOut',
 'cprhOut':'cprhIn'}

ATTR_SITE_DEPTH = 1
OUTPUT_SITE_DEPTH = 2
SEQ_SITE_DEPTH = -1  # Icons extend 1 pixel to the left of the sequence site
siteDepths = {'input':OUTPUT_SITE_DEPTH, 'output':OUTPUT_SITE_DEPTH,
 'attrOut':ATTR_SITE_DEPTH, 'attrIn':ATTR_SITE_DEPTH, 'seqIn':SEQ_SITE_DEPTH,
 'seqInsert':4, 'cprhIn':0, 'cprhOut':0}

TEXT_MARGIN = 2
# Outline color is currently set to white with a minimal non-zero alpha to allow
# a rendering trick to make outlines appear on demand.  This is sub-optimal because it
# does not allow any sort of variable coloring or shading in outlines.
OUTLINE_COLOR = (255, 255, 255, 1)
# The rendered color for outlines when drawn
SHOW_OUTLINE_TINT = (220, 220, 220, 255)

KEYWORD_COLOR = (48, 0, 128, 255)
ICON_BG_COLOR = (255, 255, 255, 255)
SELECT_TINT = (0, 0, 255, 0)
ERR_TINT = (255, 0, 0, 0)
GRAY_75 = (192, 192, 192, 255)
GRAY_50 = (128, 128, 128, 255)
GRAY_25 = (64, 64, 64, 255)
BLACK = (0, 0, 0, 255)
SEQ_RULE_COLOR = (165, 180, 165, 255)
SEQ_CONNECT_COLOR = (70, 100, 70, 255)

DEPTH_EXPAND = 4

EMPTY_ARG_WIDTH = 11
LIST_EMPTY_ARG_WIDTH = 4
SLICE_EMPTY_ARG_WIDTH = 1

# Pixels below input/output site to place function/list/tuple icons insertion site
INSERT_SITE_X_OFFSET = 2
INSERT_SITE_Y_OFFSET = 5

# Number of pixels to indent a code block
BLOCK_INDENT = 24

# Number of pixels to the left of sequence site to start else and elif icons
ELSE_DEDENT = 21

# Pixels below input/output site to place attribute site
# This should be based on font metrics, but for the moment, we have a hard-coded cursor
ATTR_SITE_OFFSET = 4

outSitePixmap = (
 "..o",
 ".o ",
 "o  ",
 ".o ",
 "..o")

inSitePixmap = (
 "  o",
 " o.",
 "o..",
 " o.",
 "  o")

attrOutPixmap = (
 "%%",
 "%%",
)

dimAttrOutPixmap = (
 "oo",
 "oo",
)

attrInPixmap = (
 "o.",
 "o.",
)

leftInSitePixmap = (
 "...o ",
 "..o  ",
 ".o  o",
 "o  o.",
 "o o..",
 "o  o.",
 ".o  o",
 "..o  ",
 "...o ",
)
commaPixmap = (
 "ooooo",
 "o   o",
 "o  o.",
 "o o..",
 "o  o.",
 "o   o",
 "o   o",
 "o %7o",
 "o8%7o",
 "o%8 o",
 "o   o",
 "ooooo",
)
commaImageSiteYOffset = 3

colonPixmap = (
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
 "ooooo",
)
colonImageSiteYOffset = 5


argAssignPixmap = (
 "ooooooooo",
 "o       o",
 "o       o",
 "o       o",
 "o %%%%% o",
 "o      o.",
 "o     o..",
 "o %%%%%o.",
 "o       o",
 "o       o",
 "o       o",
 "o       o",
 "ooooooooo",
)

binOutPixmap = (
 "..ooo",
 ".o  o",
 "o   o",
 ".o  o",
 "..ooo",
)

floatInPixmap = (
 "ooo",
 "o o",
 "oo.",
 "o..",
 "...",
 "o..",
 "oo.",
 "o o",
 "ooo",
)

binLParenPixmap = (
 "..ooooooo",
 "..o     o",
 "..o     o",
 "..o     o",
 "..o  85 o",
 "..o 85  o",
 "..o 38  o",
 "..o8%   o",
 ".o 3%  o.",
 "o  5% o..",
 ".o 3%  o.",
 "..o8%   o",
 "..o 38  o",
 "..o 85  o",
 "..o  85 o",
 "..o     o",
 "..o     o",
 "..ooooooo",
)

binRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o 58   o",
 "o  58  o",
 "o  83  o",
 "o   %8 o",
 "o   %3 o",
 "o   %5 o",
 "o   %3 o",
 "o   %8 o",
 "o  83  o",
 "o  58 o.",
 "o 58  o.",
 "o      o",
 "o      o",
 "oooooooo",
)

listLBktPixmap = (
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o  %%% o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %7  o",
 "..o  %%% o",
 "..o      o",
 "..oooooooo",
)
listLBrktExtendDupRows = (9,)

listRBktPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o %%%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o  7%  o",
 "o %%%  o",
 "o      o",
 "oooooooo",
)
listRBrktExtendDupRows = (9,)

subscriptLBktPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o %% o",
 "o %% o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %% o",
 "o %% o",
 "o    o",
 "o    o",
 "oooooo",
)

subscriptLBktOpenPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o %% o",
 "o %% o",
 "o %  o",
 "o %  o",
 "o 7  o",
 "o    o",
 "o 7  o",
 "o %  o",
 "o %  o",
 "o %% o",
 "o %% o",
 "o    o",
 "o    o",
 "oooooo",
)

subscriptRBktPixmap = (
 "oooooo",
 "o    o",
 "o    o",
 "o    o",
 "o%%  o",
 "o%%  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o %  o",
 "o%%  o",
 "o%%  o",
 "o    o",
 "o    o",
 "oooooo",
)

tupleLParenPixmap = (
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o   5  o",
 "..o  76  o",
 "..o  47  o",
 "..o  %8  o",
 "..o 9%8  o",
 "..o 8%8  o",
 "..o 8%8  o",
 "..o 8%8  o",
 "..o 9%8  o",
 "..o  %8  o",
 "..o  47  o",
 "..o  76  o",
 "..o   5  o",
 "..o      o",
 "..oooooooo",
)
tupleLParenExtendDupRows = (9,)

tupleRParenPixmap = (
 "ooooooo",
 "o     o",
 "o     o",
 "o 5   o",
 "o 67  o",
 "o 74  o",
 "o 8%  o",
 "o 8%9 o",
 "o 8%8 o",
 "o 8%8 o",
 "o 8%8 o",
 "o 8%9 o",
 "o 8%  o",
 "o 74  o",
 "o 67  o",
 "o 5   o",
 "o     o",
 "ooooooo",
)
tupleRParenExtendDupRows = (9,)

lBracePixmap = (
 "..oooooooo",
 "..o      o",
 "..o      o",
 "..o      o",
 "..o  912 o",
 "..o  639 o",
 "..o  65  o",
 "..o  65  o",
 "..o 9%7  o",
 "..o %%   o",
 "..o 9%7  o",
 "..o  65  o",
 "..o  65  o",
 "..o  639 o",
 "..o  912 o",
 "..o      o",
 "..o      o",
 "..oooooooo",
)
lBraceExtendDupRows = 6, 12

rBracePixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o 219  o",
 "o 936  o",
 "o  56  o",
 "o  56  o",
 "o  7%9 o",
 "o   %% o",
 "o  7%9 o",
 "o  56  o",
 "o  56  o",
 "o 936  o",
 "o 219  o",
 "o      o",
 "o      o",
 "oooooooo",
)
rBraceExtendDupRows = 6, 12

fnLParenPixmap = (
 ".oooooooo",
 ".o      o",
 ".o      o",
 ".o      o",
 ".o   84 o",
 ".o  81  o",
 ".o  28  o",
 ".o 73   o",
 ".o 56   o",
 ".o 48   o",
 ".o 19   o",
 ".o 19   o",
 ".o 18   o",
 ".o 28   o",
 ".o 68   o",
 ".o      o",
 ".o      o",
 ".oooooooo",
)
fnLParenExtendDupRows = 11,

fnLParenOpenPixmap = (
 ".oooooooo",
 ".o      o",
 ".o      o",
 ".o      o",
 ".o   84 o",
 ".o  81  o",
 ".o  28  o",
 ".o 73   o",
 ".o 98   o",
 ".o      o",
 ".o 5    o",
 ".o 19   o",
 ".o 18   o",
 ".o 28   o",
 ".o 68   o",
 ".o      o",
 ".o      o",
 ".oooooooo",
)

defLParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o   84 o",
 "o  81  o",
 "o  28  o",
 "o 73   o",
 "o 56   o",
 "o 48   o",
 "o 19   o",
 "o 19   o",
 "o 18   o",
 "o 28   o",
 "o 68   o",
 "o      o",
 "o      o",
 "oooooooo",
)
defLParenExtendDupRows = 11,

fnRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o  82  o",
 "o   29 o",
 "o   38 o",
 "o   37 o",
 "o   37 o",
 "o   38 o",
 "o  829 o",
 "o  74  o",
 "o  38  o",
 "o 65   o",
 "o85    o",
 "o      o",
 "o      o",
 "oooooooo",
)
fnRParenExtendDupRows = 7,

defRParenPixmap = (
 "oooooooo",
 "o      o",
 "o      o",
 "o      o",
 "o  82  o",
 "o   29 o",
 "o   38 o",
 "o   37 o",
 "o   37 o",
 "o   38 o",
 "o  829 o",
 "o  74  o",
 "o  38  o",
 "o 65   o",
 "o85    o",
 "o      o",
 "o      o",
 "oooooooo",
)
defRParenExtendDupRows = 7,

binInSeqPixmap = (
 "ooo",
 "ooo",
 "ooo",
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
 "ooo",
 "ooo",
 "ooo",
)

lSimpleSpinePixmap = (
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
 "..ooo",
)
simpleSpineExtendDupRows = 9,

rSimpleSpinePixmap = (
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
 "ooo",
)

inpSeqPixmap = (
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
 "ooo",
)

inpOptionalSeqPixmap = (
 "ooo",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "o o",
 "ooo",
)

dragSeqPixmap = (
 "..ooo",
 ".o%%o",
 "o%%%%",
 ".o%%o",
 "..ooo",
)

assignDragPixmap = (
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
 "......",
)

branchFootPixmap = (
 "ooooooooooooooooooooooooooo",
 "ooo                     ooo",
 "ooooooooooooooooooooooooooo",
)

seqSitePixmap = (
 "ooo",
 "ooo",
 "ooo",
)

cphSitePixmap = (
 "oo",
 ".o",
 ".o",
 ".o",
 ".o",
 ".o",
 "oo",
)

renderCache = {}

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

def clipboardRepr(icons, offset):
    """Top level function for converting icons into their serialized string representation
    for copying to the clipboard.  icons should be a list of icons to be copied."""
    seriesLists = python_g.findSeries(icons)
    iconsToCopy = set(icons)
    seqLists = []
    for sequence in seriesLists['sequences']:
        seqLists.append([ic.clipboardRepr(offset, iconsToCopy) for ic in sequence])
    for series in seriesLists['lists']:
        children = ["argIcons"] + [ic.clipboardRepr(offset, iconsToCopy) for ic in series]
        seqLists.append([("TupleIcon", addPoints(series[0].rect[:2], (0, 5)),
         {'noParens':True}, [children])])
    for ic in seriesLists['individual']:
        seqLists.append([ic.clipboardRepr(offset, iconsToCopy)])
    return repr(seqLists)

def textRepr(icons):
    topIcons = python_g.findTopIcons(icons)
    branchDepth = 0
    clipText = []
    for ic in topIcons:
        if isinstance(ic, BlockEnd):
            branchDepth -= 1
        else:
            if ic.__class__ in (ElifIcon, ElseIcon):
                indent = "    " * max(0, branchDepth-1)
            else:
                indent = "    " * max(0, branchDepth)
            if hasattr(ic, 'blockEnd'):
                branchDepth += 1
            clipText.append(indent + ic.textRepr())
    return "\n".join(clipText)

def asciiToImage(asciiPixmap):
    if asciiToImage.asciiMap is None:
        asciiToImage.asciiMap = {'.': (0, 0, 0, 0), 'o': OUTLINE_COLOR,
         ' ': ICON_BG_COLOR, '%': BLACK}
        for i in range(1, 10):
            pixel = int(int(i) * 255 * 0.1)
            asciiToImage.asciiMap[str(i)] = (pixel, pixel, pixel, 255)
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [asciiToImage.asciiMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image
asciiToImage.asciiMap = None

def iconBoxedText(text, font=globalFont, color=BLACK):
    if (text, font, color) in renderCache:
        return renderCache[(text, font, color)]
    width, height = font.getsize(text)
    if height < minTxtHgt:
        height = minTxtHgt
    width += 2 * TEXT_MARGIN + 1
    height += 2 * TEXT_MARGIN + 1
    txtImg = Image.new('RGBA', (width, height), color=ICON_BG_COLOR)
    draw = ImageDraw.Draw(txtImg)
    draw.text((TEXT_MARGIN, TEXT_MARGIN), text, font=font, fill=color)
    draw.rectangle((0, 0, width-1, height-1), fill=None, outline=OUTLINE_COLOR)
    renderCache[(text, font, color)] = txtImg
    return txtImg

textSizeCache = {}
def getTextSize(text, font=globalFont):
    key = text, font
    size = textSizeCache.get(key)
    if size is None:
        size = textSizeCache[key] = font.getsize(text)
    return size

outSiteImage = asciiToImage(outSitePixmap)
inSiteImage = asciiToImage(inSitePixmap)
attrOutImage = asciiToImage(attrOutPixmap)
attrInImage = asciiToImage(attrInPixmap)
dimAttrOutImage = asciiToImage(dimAttrOutPixmap)
leftInSiteImage = asciiToImage(leftInSitePixmap)
commaImage = asciiToImage(commaPixmap)
colonImage = asciiToImage(colonPixmap)
argAssignImage = asciiToImage(argAssignPixmap)
binOutImage = asciiToImage(binOutPixmap)
floatInImage = asciiToImage(floatInPixmap)
lParenImage = asciiToImage(binLParenPixmap)
rParenImage = asciiToImage(binRParenPixmap)
tupleLParenImage = asciiToImage(tupleLParenPixmap)
tupleRParenImage = asciiToImage(tupleRParenPixmap)
lBraceImage = asciiToImage(lBracePixmap)
rBraceImage = asciiToImage(rBracePixmap)
fnLParenImage = asciiToImage(fnLParenPixmap)
fnLParenOpenImage = asciiToImage(fnLParenOpenPixmap)
fnRParenImage = asciiToImage(fnRParenPixmap)
defLParenImage = asciiToImage(defLParenPixmap)
defRParenImage = asciiToImage(defRParenPixmap)
listLBktImage = asciiToImage(listLBktPixmap)
listRBktImage = asciiToImage(listRBktPixmap)
subscriptLBktImage = asciiToImage(subscriptLBktPixmap)
subscriptRBktImage = asciiToImage(subscriptRBktPixmap)
subscriptLBktOpenImage = asciiToImage(subscriptLBktOpenPixmap)
lSimpleSpineImage = asciiToImage(lSimpleSpinePixmap)
rSimpleSpineImage = asciiToImage(rSimpleSpinePixmap)
inpSeqImage = asciiToImage(inpSeqPixmap)
inpOptionalSeqImage = asciiToImage(inpOptionalSeqPixmap)
binInSeqImage = asciiToImage(binInSeqPixmap)
assignDragImage = asciiToImage(assignDragPixmap)
dragSeqImage = asciiToImage(dragSeqPixmap)
branchFootImage = asciiToImage(branchFootPixmap)
seqSiteImage = asciiToImage(seqSitePixmap)
cphSiteImage = asciiToImage(cphSitePixmap)
emptyImage = Image.new('RGBA', (0, 0))

# Sadly, hand drawn components are drawn in pixels rather than being dynamically based
# on font size, so the font can not be arbitrarily enlarged or reduced without hurting
# appearance.  The eventual, non-prototype, version of this will need to have higher
# resolution pixmaps for these, and scale them to match the chosen font.
minTxtIconHgt = tupleLParenImage.height
minTxtHgt = minTxtIconHgt - 2 * TEXT_MARGIN - 1

class IconExecException(Exception):
    def __init__(self, ic, exceptionText):
        self.icon = ic
        self.message = exceptionText
        super().__init__(self.message)

class Icon:
    def __init__(self, window=None):
        self.window = window
        self.rect = None
        self.layoutDirty = False
        self.drawList = None
        self.sites = IconSiteList()
        self.id = None if window is None else self.window.makeId(self)
        window.undo.registerIconCreated(self)

    def draw(self, image=None, location=None, clip=None):
        """Draw the icon.  The image to which it is drawn and the location at which it is
         drawn can be optionally overridden by specifying image and/or location."""
        pass

    def pos(self, preferSeqIn=False):
        """The "official" position of an icon is defined by the location of its seqInsert
        site if it has one, or output site if it doesn't.  Icons that don't have either
        will not be centered vertically on that location: Icons with an attrOut site are
        positioned by that, and anything else on the top-left corner of its rectangle.
        For backward compatibility with earlier versions of the call, setting preferSeqIn
        to True will return the position of the seqIn site over the seqInsert site."""
        if preferSeqIn and hasattr(self.sites, 'seqIn'):
            return self.posOfSite('seqIn')
        if hasattr(self.sites, 'seqInsert'):
            return self.posOfSite('seqInsert')
        elif hasattr(self.sites, 'output'):
            return self.posOfSite('output')
        elif hasattr(self.sites, 'attrOut'):
            return self.posOfSite('attrOut')
        else:
            return self.rect[:2]

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

    def layout(self, location=None):
        """Compute layout and set locations for icon and its children (do not redraw).
        location (at least for the moment) is upper left corner of .rect, not .pos().
        This should only be called on top-level icons."""
        if location is None:
            x, y = self.rect[:2]
        else:
            x, y = location
        # The calcLayouts and doLayout calls use the icon's output, seqInsert, attrOut
        # or cphrOut site in that order (if it has none of those, use the rect position).
        forSeq = self.nextInSeq() or self.prevInSeq()
        if forSeq:
            layouts = self.calcLayouts()  # ... Hint sequential layout for optimization
            if layouts[0].width > self.window.margin:
                layouts = self.calcLayouts()
        else:
            layouts = self.calcLayouts()
        # Determine the best of the calculated layouts based on size and "badness" rating
        # recorded in each of the layouts.  Incorporate size and margin exceeded penalties
        # directly in to the layout badness score
        for layout in layouts:
            if layout.width > self.window.margin:
                layout.badness += 100 + 2 * layout.width - self.window.margin
        if forSeq:
            # Icon is part of a sequence.  Optimize for height
            minHeight = min((layout.height for layout in layouts))
            for layout in layouts:
                layout.badness += (layout.height - minHeight) // 2
        else:
            # Icon is not in a sequence.  Optimize for perimeter
            minBadness = min((layout.width + layout.height * 4 for layout in layouts))
            for layout in layouts:
                layout.badness += (layout.width + layout.height * 4 - minBadness) // 8
        bestScore = None
        for layout in layouts:
            if bestScore is None or layout.badness < bestScore:
                bestLayout = layout
                bestScore = layout.badness
        if hasattr(self.sites, 'output'):
            # ... The only reason the code below works, is that the only callers to this
            #     function reposition the icon no matter where this puts it (the old
            #     output site offset will be incorrect if doLayout changes it).
            self.doLayout(x+self.sites.output.xOffset, y+self.sites.output.yOffset,
                    bestLayout)
        elif hasattr(self.sites, 'seqInsert'):
            self.doLayout(x, y, bestLayout)
        elif hasattr(self.sites, 'attrOut'):
            self.doLayout(x+self.sites.attrOut.xOffset, y+self.sites.attrOut.yOffset,
                    bestLayout)
        elif hasattr(self.sites, 'cprhOut'):
            self.doLayout(x+self.sites.cprhOut.xOffset, y+self.sites.cprhOut.yOffset,
                    bestLayout)
        else:
            self.doLayout(x, y, bestLayout)
        return bestLayout

    def traverse(self, order="draw", includeSelf=True):
        """Iterator for traversing the tree below this icon.  Traversal can be in either
        drawing (order="draw") or picking (order="pick") order."""
        if includeSelf and order != "pick":
            yield self
        # For "pick" order to be the true opposite of "draw", this loop should run in
        # reverse, but child icons are not intended to overlap in a detectable way.
        for child in self.children():
            if child is None:
                print('icon has null child', self)
            yield from child.traverse(order)
        if includeSelf and order == "pick":
            yield self

    def traverseBlock(self, includeSelf=True, hier=False):
        """If the icon owns a code block return either all the icons in the code block
        (if hier is True), or just the top level icons in the block (if hier is False)."""
        if includeSelf:
            if hier:
                yield from self.traverse()
            else:
                yield self
        if not hasattr(self, 'blockEnd'):
            return
        for ic in traverseSeq(self, includeStartingIcon=False):
            if ic is self.blockEnd:
                break
            if hier:
                yield from ic.traverse()
            else:
                yield ic
        if includeSelf:
            yield self.blockEnd

    def touchesPosition(self, x, y):
        """Return True if any of the drawn part of the icon falls at x, y"""
        if not pointInRect((x, y), self.rect):
            return False
        for imgOffset, img in self.drawList:
            if img is commaImage:
                continue
            left, top = addPoints(self.rect[:2], imgOffset)
            imgX = x - left
            imgY = y - top
            if pointInRect((imgX, imgY), (0, 0, img.width, img.height)):
                pixel = img.getpixel((imgX, imgY))
                return pixel[3] > 128
        return False

    def inRectSelect(self, rect):
        """Return True if rect overlaps any visible part of the icon (commas excepted).
        Note that this is not as thorough as touchesPosition, which answers at the level
        of pixels.  This only answers at the level of rectangles in which the icon
        draws something."""
        if not python_g.rectsTouch(self.rect, rect):
            return False
        if self.drawList is None:
            print('Missing drawlist?')
        for imgOffset, img in self.drawList:
            if img is commaImage:
                continue
            left, top = addPoints(self.rect[:2], imgOffset)
            right = left + img.width
            bottom = top + img.height
            if python_g.rectsTouch((left, top, right, bottom), rect):
                return True
        return False

    def selectionRect(self):
        """Return the area of the icon that constitutes the selected portion of the icon.
        This is used for extending existing selections (Shift+select), and typically
        excludes tiny connectors and snap sites"""
        return self.rect

    def hierRect(self):
        """Return a rectangle covering this icon and its children"""
        return containingRect(self.traverse())

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

    def prevInSeq(self):
        if not hasattr(self.sites, 'seqIn'):
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
                seriesName, idx = splitSeriesSiteId(siteId)
                seriesLen = len(self.sites.getSeries(seriesName))
                if idx == seriesLen:
                    self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
                self.sites.lookup(siteId).attach(self, newChild, childSite)
        else:
            self.sites.lookup(siteId).attach(self, newChild, childSite)
        self.markLayoutDirty()

    def removeEmptySeriesSite(self, siteId):
        if self.childAt(siteId):
            return
        self.sites.removeSeriesSiteById(self, siteId)
        self.markLayoutDirty()

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None):
        """Insert a child icon or empty icon site (child=None) at the specified site.
        siteIdOrName may specify either the complete siteId for a site, or (if
        seriesIdx is specified), the name for a series of sites with the index specified
        in seriesIdx."""
        if seriesIdx is None:
            seriesName, seriesIdx = splitSeriesSiteId(siteIdOrSeriesName)
        else:
            seriesName = siteIdOrSeriesName
        if seriesName is None:
            print("Failed to insert icon", child, "at", siteIdOrSeriesName)
            return
        series = self.sites.getSeries(seriesName)
        if series is None:
            print("Failed to insert icon,", child, "in series", seriesName)
            return
        if len(series) == 1 and series[0].att is None and seriesIdx == 0:
            series[0].attach(self, child, childSite)
        else:
            self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, seriesIdx)
            self.sites.lookupSeries(seriesName)[seriesIdx].attach(self, child, childSite)
        self.markLayoutDirty()

    def insertChildren(self, children, seriesName, seriesIdx, childSite=None):
        """Insert a group of child icons at the specified site"""
        for i, child in enumerate(children):
            self.insertChild(child, seriesName, seriesIdx + i, childSite)

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
            site = makeSeriesSiteId(siteOrSeriesName, seriesIdx)
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

    def posOfSite(self, siteId):
        """Return the window position of a given site of the icon"""
        site = self.sites.lookup(siteId)
        if site is None:
            return None
        x, y = self.rect[:2]
        return x + site.xOffset, y + site.yOffset

    def typeOf(self, siteId):
        site = self.sites.lookup(siteId)
        if site is None:
            return None
        return site.type

    def indexOf(self, siteId):
        series, index = splitSeriesSiteId(siteId)
        if series is not None:
            return index
        return None

    def becomeTopLevel(self, isTop):
        """Change top level status of icon (most icons add or remove sequence sites)."""
        self.drawList = None  # Force change at next redraw

    def hasCoincidentSite(self):
        """If the icon has an input site in the same spot as its output site (done so
        binary operations can be arranged like text), return that input site"""
        if hasattr(self, 'coincidentSite') and self.coincidentSite is not None:
            return self.coincidentSite

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

    def _drawFromDrawList(self, toDragImage, location, clip, style):
        if location is None:
            location = self.rect[:2]
        if toDragImage is None:
            outImg = self.window.image
            x, y = self.window.contentToImageCoord(*location)
            if clip is not None:
                clip = python_g.offsetRect(clip, -self.window.scrollOrigin[0],
                 -self.window.scrollOrigin[1])
        else:
            outImg = toDragImage
            x, y = location
        for (imgOffsetX, imgOffsetY), img in self.drawList:
            pasteImageWithClip(outImg, tintSelectedImage(img, self.isSelected(), style),
             (x + imgOffsetX, y + imgOffsetY), clip)

    def _serialize(self, offset, iconsToCopy, **args):
        currentSeries = None
        children = []
        for site in self.sites.childSites():
            att = self.childAt(site.name)
            if att is not None and att not in iconsToCopy:
                continue
            childRepr = None if att is None else att.clipboardRepr(offset, iconsToCopy)
            if isSeriesSiteId(site.name):
                seriesName, idx = splitSeriesSiteId(site.name)
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
        code for execution.  In the future it may also be used to create a version-
        control-friendly Python-text-compatible save file format."""
        return None

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy)

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

class TextIcon(Icon):
    def __init__(self, text, window=None, location=None, hasAttrIn=True):
        Icon.__init__(self, window)
        self.text = text
        self.hasAttrIn = hasAttrIn
        bodyWidth, bodyHeight = getTextSize(self.text)
        bodyHeight = max(minTxtHgt, bodyHeight)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('output', 'output', 0, bodyHeight // 2)
        self.sites.add('attrIcon', 'attrIn', bodyWidth,
         bodyHeight // 2 + ATTR_SITE_OFFSET)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text)
            img.paste(txtImg, (outSiteImage.width - 1, 0))
            if needSeqSites:
                drawSeqSites(img, outSiteImage.width-1, 0, txtImg.height)
            if needOutSite:
                outX = self.sites.output.xOffset
                outY = self.sites.output.yOffset - outSiteImage.height // 2
                img.paste(outSiteImage, (outX, outY), mask=outSiteImage)
            if self.hasAttrIn:
                attrX = self.sites.attrIcon.xOffset
                attrY = self.sites.attrIcon.yOffset
                img.paste(attrInImage, (attrX, attrY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.drawList = None  # Draw or undraw sequence sites ... refine when sites added
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.attrIcon.att is None:
            attrLayouts = [None]
        else:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        width, height = self.bodySize
        layouts = []
        for attrLayout in attrLayouts:
            layout = Layout(self, width, height, height // 2)
            layout.addSubLayout(attrLayout, 'attrIcon', width-1, ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return self.text + _attrTextRepr(self)

    def dumpName(self):
        """Give the icon a name to be used in text dumps."""
        return self.text

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, text=self.text)

class IdentifierIcon(TextIcon):
    def __init__(self, name, window=None, location=None):
        TextIcon.__init__(self, name, window, location)
        self.name = name

    def execute(self):
        if self.name in namedConsts:
            value = namedConsts[self.name]
        elif self.name in globals():
            value = globals()[self.name]
        else:
            raise IconExecException(self, self.name + " is not defined")
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(value)
        return value

    def createAst(self):
        if self.name in namedConsts:
            return ast.NameConstant(namedConsts[self.name], lineno=self.id, col_offset=0)
        ctx = determineCtx(self)
        identAst = ast.Name(self.name, ctx=ctx, lineno=self.id, col_offset=0)
        return composeAttrAst(self, identAst)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

class NumericIcon(TextIcon):
    def __init__(self, value, window=None, location=None):
        if type(value) == type(""):
            try:
                value = int(value)
            except ValueError:
                value = float(value)
        TextIcon.__init__(self, repr(value), window, location, hasAttrIn=False)
        self.value = value

    def execute(self):
        return self.value

    def createAst(self):
        return ast.Num(self.value, lineno=self.id, col_offset=0)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, value=self.value)

class StringIcon(TextIcon):
    def __init__(self, string, window=None, location=None):
        TextIcon.__init__(self, repr(string), window, location)
        self.string = string

    def execute(self):
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(self.string)
        return self.string

    def createAst(self):
        return composeAttrAst(self, ast.Str(self.string, lineno=self.id, col_offset=0))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, string=self.string)

class PosOnlyMarkerIcon(TextIcon):
    def __init__(self, window=None, location=None):
        TextIcon.__init__(self, '/', window, location)

class AttrIcon(Icon):
    def __init__(self, name, window=None, location=None):
        Icon.__init__(self, window)
        self.name = name
        bodyWidth, bodyHeight = getTextSize(self.name)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight = max(bodyHeight, minTxtHgt) + 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        self.sites.add('attrOut', 'attrOut', 0, bodyHeight // 2 + ATTR_SITE_OFFSET)
        self.sites.add('attrIcon', 'attrIn', bodyWidth - ATTR_SITE_DEPTH,
         bodyHeight // 2 + ATTR_SITE_OFFSET)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + attrOutImage.width, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.name)
            img.paste(txtImg, (attrOutImage.width - 1, 0))
            attrOutX = self.sites.attrOut.xOffset
            attrOutY = self.sites.attrOut.yOffset
            img.paste(attrOutImage, (attrOutX, attrOutY), mask=attrOutImage)
            attrInX = self.sites.attrIcon.xOffset
            attrInY = self.sites.attrIcon.yOffset
            img.paste(attrInImage, (attrInX, attrInY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        width, height = self.bodySize
        width += attrOutImage.width - 1
        top = attrSiteY - (height // 2 + ATTR_SITE_OFFSET)
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        layouts = []
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        for attrLayout in attrLayouts:
            layout = Layout(self, width, height, height // 2 + ATTR_SITE_OFFSET)
            layout.addSubLayout(attrLayout, 'attrIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return '.' + self.name + _attrTextRepr(self)

    def dumpName(self):
        return "." + self.name

    def execute(self, attrOfValue):
        try:
            result = getattr(attrOfValue, self.name)
        except Exception as err:
            raise IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self, attrOfAst):
        return composeAttrAst(self, ast.Attribute(value=attrOfAst, attr=self.name,
         lineno=self.id, col_offset=0, ctx=determineCtx(self)))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, name=self.name)

class SubscriptIcon(Icon):
    def __init__(self, numSubscripts=1, window=None, closed=True, location=None):
        Icon.__init__(self, window)
        self.closed = False
        leftWidth, leftHeight = subscriptLBktImage.size
        attrY = leftHeight // 2 + ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrY)
        self.sites.add('indexIcon', 'input',
         leftWidth + ATTR_SITE_DEPTH - outSiteImage.width + 1, leftHeight//2)
        self.argWidths = [LIST_EMPTY_ARG_WIDTH, 0, 0]
        totalWidth, totalHeight = self._size()
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + totalWidth, y + totalHeight)
        self.changeNumSubscripts(numSubscripts)
        if closed:
            self.close()

    def _size(self):
        rBrktWidth = subscriptRBktImage.width - 1 if self.closed else 0
        return subscriptLBktImage.width + sum(self.argWidths) + \
         rBrktWidth + ATTR_SITE_DEPTH, subscriptLBktImage.height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            leftBoxX = dimAttrOutImage.width - 1
            leftBoxWidth, leftBoxHeight = subscriptLBktImage.size
            leftImg = Image.new('RGBA', (leftBoxX + leftBoxWidth, leftBoxHeight),
             color=(0, 0, 0, 0))
            # Left bracket
            lBrktImg = subscriptLBktImage if self.closed else subscriptLBktOpenImage
            leftImg.paste(lBrktImg, (leftBoxX, 0))
            # attrOut site
            leftImg.paste(dimAttrOutImage,  (self.sites.attrOut.xOffset,
             self.sites.attrOut.yOffset), mask=dimAttrOutImage)
            # Index input site
            inSiteX = leftBoxX + leftBoxWidth - inSiteImage.width
            inSiteY = leftBoxHeight // 2 - inSiteImage.height // 2
            leftImg.paste(inSiteImage, (inSiteX, inSiteY))
            self.drawList = [((0, 0), leftImg)]
            x = inSiteX + self.argWidths[0] + inSiteImage.width - 1
            # Colons:
            colonY = leftBoxHeight // 2 - colonImage.height // 2
            if hasattr(self.sites, 'upperIcon'):
                self.drawList.append(((x, colonY), colonImage))
                x += self.argWidths[1]
            if hasattr(self.sites, 'stepIcon'):
                self.drawList.append(((x, colonY), colonImage))
                x += self.argWidths[2]
            # Right bracket
            if self.closed:
                self.drawList.append(((x, 0), subscriptRBktImage))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self,  attrSiteX,  attrSiteY, layout):
        self.argWidths = layout.argWidths
        layout.updateSiteOffsets(self.sites.attrOut)
        top = attrSiteY - (subscriptLBktImage.height // 2 + ATTR_SITE_OFFSET)
        width, height = self._size()
        self.rect = (attrSiteX, top,  attrSiteX + width, top + height)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        indexLayouts = stepLayouts = upperLayouts = attrLayouts = [None]
        if self.sites.indexIcon.att is not None:
            indexLayouts = self.sites.indexIcon.att.calcLayouts()
        if hasattr(self.sites, 'upperIcon') and self.sites.upperIcon.att is not None:
            upperLayouts = self.sites.upperIcon.att.calcLayouts()
        if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
            stepLayouts = self.sites.stepIcon.att.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        layouts = []
        for indexLayout, upperLayout, stepLayout, attrLayout in allCombinations(
                (indexLayouts, upperLayouts, stepLayouts, attrLayouts)):
            if indexLayout is None:
                if hasattr(self.sites, 'upperIcon'):
                    indexWidth = SLICE_EMPTY_ARG_WIDTH
                else:
                    indexWidth = LIST_EMPTY_ARG_WIDTH  # Emphasize missing argument(s)
            else:
                indexWidth = indexLayout.width - 1
            if upperLayout is None:
                if hasattr(self.sites, 'upperIcon'):
                    upperWidth = colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
                else:
                    upperWidth = 0
            else:
                upperWidth = colonImage.width + upperLayout.width - 2
            if stepLayout is None:
                if hasattr(self.sites, 'stepIcon'):
                    stepWidth = colonImage.width + SLICE_EMPTY_ARG_WIDTH - 2
                else:
                    stepWidth = 0
            else:
                stepWidth = colonImage.width + stepLayout.width - 2
            rBrktWidth = subscriptRBktImage.width - 1 if self.closed else 0
            totalWidth = subscriptLBktImage.width + indexWidth + upperWidth + \
                         stepWidth + rBrktWidth - 1 + ATTR_SITE_DEPTH
            x, height = subscriptLBktImage.size
            x -= 1  # Icon overlap
            layout = Layout(self, totalWidth, height, height // 2 + ATTR_SITE_OFFSET)
            layout.addSubLayout(indexLayout, 'indexIcon', x, -ATTR_SITE_OFFSET)
            x += indexWidth
            if upperWidth > 0:
                layout.addSubLayout(upperLayout, 'upperIcon', x +
                                    colonImage.width - 1, -ATTR_SITE_OFFSET)
                x += upperWidth
            if stepWidth > 0:
                layout.addSubLayout(stepLayout, 'stepIcon', x +
                                    colonImage.width - 1, -ATTR_SITE_OFFSET)
            if self.closed:
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width - 1, 0)
            layout.argWidths = [indexWidth, upperWidth, stepWidth]
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def changeNumSubscripts(self, n):
        if hasattr(self.sites, 'stepIcon'):
            oldN = 3
        elif hasattr(self.sites, 'upperIcon'):
            oldN = 2
        else:
            oldN = 1
        if n < 3 and oldN == 3:
            self.sites.remove('stepIcon')
        if n < 2 and oldN >= 2:
            self.sites.remove('upperIcon')
        if n >= 2 and oldN < 2:
            self.sites.add('upperIcon', 'input')
        if n == 3 and oldN < 3:
            self.sites.add('stepIcon', 'input')
        self.window.undo.registerCallback(self.changeNumSubscripts, oldN)
        self.markLayoutDirty()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Add back the attribute site on the end paren.  Done here to allow the site to
        # be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', rectWidth(self.rect) -
         ATTR_SITE_DEPTH, rectHeight(self.rect) // 2 + ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def textRepr(self):
        indexIcon = self.sites.indexIcon.att
        indexText = "" if indexIcon is None else indexIcon.textRepr()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperText = ":"
            else:
                upperText = ":" + self.sites.upperIcon.att.textRepr()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepText = ":" + self.sites.stepIcon.att.textRepr()
            else:
                stepText = ""
        else:
            upperText = stepText = ""
        return '[' + indexText + upperText + stepText + ']' + _attrTextRepr(self)

    def dumpName(self):
        return "." + "[" + ("]" if self.closed else "")

    def clipboardRepr(self, offset, iconsToCopy):
        if not hasattr(self.sites, 'upperIcon'):
            numSubscripts = 1
        elif not hasattr(self.sites, 'stepIcon'):
            numSubscripts = 2
        else:
            numSubscripts = 3
        return self._serialize(offset, iconsToCopy, numSubscripts=numSubscripts,
         closed=self.closed)

    def execute(self, attrOfValue):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.sites.indexIcon.att is None:
            raise IconExecException(self, "Missing argument")
        indexValue = self.sites.indexIcon.att.execute()
        if hasattr(self.sites, 'upperIcon'):
            if self.sites.upperIcon.att is None:
                upperValue = None
            else:
                upperValue = self.sites.upperIcon.att.execute()
            if hasattr(self.sites, 'stepIcon') and self.sites.stepIcon.att is not None:
                stepValue = self.sites.stepIcon.att.execute()
            else:
                stepValue = None
            try:
                result = attrOfValue[indexValue:upperValue:stepValue]
            except Exception as err:
                raise IconExecException(self, err)
        else:
            try:
                result = attrOfValue[indexValue]
            except Exception as err:
                raise IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self, attrOfAst):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.sites.indexIcon.att is None:
            if not self.hasSite('upperIcon'):
                raise IconExecException(self, "Missing subscript")
            indexAst = None
        else:
            indexAst = self.sites.indexIcon.att.createAst()
        if self.hasSite('upperIcon'):
            if self.sites.upperIcon.att:
                upperAst = self.sites.upperIcon.att.createAst()
            else:
                upperAst = None
            if self.hasSite('stepIcon') and self.sites.stepIcon.att:
                stepAst = self.sites.stepIcon.att.createAst()
            else:
                stepAst = None
            slice = ast.Slice(indexAst, upperAst, stepAst)
        else:
            slice = ast.Index(value=indexAst)
        return composeAttrAst(self, ast.Subscript(value=attrOfAst, slice=slice,
         lineno=self.id, col_offset=0, ctx=determineCtx(self)))

class UnaryOpIcon(Icon):
    def __init__(self, op, window, location=None):
        Icon.__init__(self, window)
        self.operator = op
        self.precedence = unaryOpPrecedence[op]
        bodyWidth, bodyHeight = getTextSize(self.operator)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('argIcon', 'input', bodyWidth - 1, siteYOffset)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + bodyWidth + outSiteImage.width, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            width, height = getTextSize(self.operator)
            bodyLeft = outSiteImage.width - 1
            bodyWidth = width + 2 * TEXT_MARGIN
            bodyHeight = height + 2 * TEXT_MARGIN
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyLeft + bodyWidth, bodyHeight),
             fill=ICON_BG_COLOR, outline=OUTLINE_COLOR)
            if needOutSite:
                outImageY = self.sites.output.yOffset - outSiteImage.height // 2
                img.paste(outSiteImage, (0, outImageY), mask=outSiteImage)
            inImageY = self.sites.argIcon.yOffset - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.argIcon.xOffset, inImageY))
            if needSeqSites:
                drawSeqSites(img, bodyLeft, 0, bodyHeight+1)
            if self.operator in ('+', '-', '~'):
                # Raise unary operators up and move then to the left.  Not sure if this
                # is safe for all fonts, but the Ariel font we're using pads on top.
                textTop = -1 if self.operator == '+' else -2
                textLeft = bodyLeft + 2 * TEXT_MARGIN
            else:
                textTop = TEXT_MARGIN
                textLeft = bodyLeft + TEXT_MARGIN + 1
            draw.text((textLeft, textTop), self.operator, font=globalFont,
             fill=(0, 0, 0, 255))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def arg(self):
        return self.sites.argIcon.att

    def doLayout(self, outSiteX, outSiteY, layout):
        width, height = self.bodySize
        width += outSiteImage.width - 1
        top = outSiteY - height // 2
        self.rect = (outSiteX, top, outSiteX + width, top + height)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.layoutDirty = False

    def calcLayouts(self):
        if self.sites.argIcon.att is None:
            argLayouts = (None,)
        else:
            argLayouts = self.sites.argIcon.att.calcLayouts()
        width, height = self.bodySize
        layouts = []
        for argLayout in argLayouts:
            layout = Layout(self, width, height, height // 2)
            layout.addSubLayout(argLayout, 'argIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        addSpace = " " if self.operator[-1].isalpha() else ""
        return self.operator + addSpace + _singleArgTextRepr(self.sites.argIcon)

    def dumpName(self):
        return "unary " + self.operator

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, op=self.operator)

    def execute(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument")
        argValue = self.arg().execute()
        try:
            result = unaryOpFn[self.operator](argValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

    def createAst(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument")
        operandAst = self.arg().createAst()
        return ast.UnaryOp(unaryOpAsts[self.operator](), operandAst, lineno=self.id,
         col_offset=0)

class StarIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, '*', window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list,
        # list, tuple, or assignment
        snapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def matingIcon(ic, siteId):
            siteName, idx = splitSeriesSiteId(siteId)
            if ic.__class__ in (CallIcon, DefIcon, ListIcon, TupleIcon):
                return siteName == "argIcons"
            if ic.__class__ is AssignIcon:
                return siteName is not None and siteName[:7] in ("targets", "values")
            return False
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def createAst(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument to star")
        return ast.Starred(self.arg().createAst(), determineCtx(self), lineno=self.id,
         col_offset=0)

    def clipboardRepr(self, offset, iconsToCopy):
        # Parent UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

class StarStarIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, '**', window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list,
        # or dictionary
        snapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def matingIcon(ic, siteId):
            siteName, idx = splitSeriesSiteId(siteId)
            return ic.__class__ in (CallIcon, DefIcon, DictIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', matingIcon) for snapData in outSites]
        return snapLists

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

class YieldFromIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, 'yield from', window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def createAst(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument to yield from")
        return ast.YieldFrom(self.arg().createAst(), lineno=self.id, col_offset=0)

class AwaitIcon(UnaryOpIcon):
    def __init__(self, window=None, location=None):
        UnaryOpIcon.__init__(self, 'await', window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        # Superclass UnaryOp specifies op keyword, which this does not have
        return self._serialize(offset, iconsToCopy)

    def createAst(self):
        if self.arg() is None:
            raise IconExecException(self, "Missing argument to await")
        return ast.Await(self.arg().createAst(), lineno=self.id, col_offset=0)

class ListTypeIcon(Icon):
    def __init__(self, leftText, rightText, window, leftImgFn=None, rightImgFn=None,
     closed=True, location=None):
        """Note that the images generated by leftImgFn and rightImgFn get modified by
        the draw method, so must not return template images."""
        Icon.__init__(self, window)
        self.closed = False
        self.leftText = leftText
        self.rightText = rightText
        self.leftImgFn = leftImgFn
        self.rightImgFn = rightImgFn
        leftWidth, height = leftImgFn(0).size
        self.sites.add('output', 'output', 0, height // 2)
        self.argList = ListLayoutMgr(self, 'argIcons', leftWidth-1, height//2)
        self.sites.addSeries('cprhIcons', 'cprhIn', 1, [(leftWidth-1, height//2)])
        width = self.sites.cprhIcons[-1].xOffset + rightImgFn(0).width
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, height-2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if closed:
            self.close()

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            # Left paren/bracket/brace
            leftImg = self.leftImgFn(self.argList.spineHeight)
            leftImgX = min(outSiteImage.width - 1, leftImg.width - 3)
            if needSeqSites:
                drawSeqSites(leftImg, leftImgX, 0, leftImg.height)
            # Output site
            if needOutSite:
                outSiteX = self.sites.output.xOffset
                outSiteY = self.sites.output.yOffset - outSiteImage.height // 2
                leftImg.paste(outSiteImage, (outSiteX, outSiteY)) #, mask=outSiteImage)
            # Body input site(s)
            self.argList.drawBodySites(leftImg)
            # Unclosed icons need to be dimmed and crossed out
            inSiteX = leftImg.width - inSiteImage.width
            if not self.closed:
                cntrY = self.sites.output.yOffset
                draw = ImageDraw.Draw(leftImg)
                draw.line((leftImgX+1, cntrY, inSiteX, cntrY),
                        fill=ICON_BG_COLOR, width=3)
            self.drawList = [((0, 0), leftImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(inSiteX,
                    self.sites.output.yOffset)
            # End paren/brace/bracket
            if self.closed:
                rightImg = self.rightImgFn(self.argList.spineHeight)
                if self.acceptsComprehension():
                    cphYOff = self.sites.output.yOffset - cphSiteImage.height // 2
                    rightImg.paste(cphSiteImage, (0, cphYOff))
                attrInXOff = rightImg.width - attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rightImg.paste(attrInImage, (attrInXOff, attrInYOff))
                parenX = self.sites.cprhIcons[-1].xOffset
                self.drawList.append(((parenX, 0), rightImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def isComprehension(self):
        return len(self.sites.cprhIcons) > 1

    def acceptsComprehension(self):
        return len(self.sites.argIcons) <= 1

    def insertChild(self, child, siteIdOrSeriesName, seriesIdx=None, childSite=None):
        # Checks and special rules for comprehension series with no commas.
        if seriesIdx is None:
            seriesName, idx = splitSeriesSiteId(siteIdOrSeriesName)
        else:
            seriesName = siteIdOrSeriesName
            idx = seriesIdx
        if seriesName == "argIcons":
            if self.isComprehension():
                print('Attempt to add elements to comprehension')
                return
        if seriesName != 'cprhIcons':
            Icon.insertChild(self, child, siteIdOrSeriesName, seriesIdx, childSite)
            return
        if len(self.sites.argIcons) > 1:
            print("Can't add comprehension to multi-element list")
            return
        #  Without commas we need to never leave an empty site, except for the last one,
        #  which must always exist and remain empty
        if child is None:
            return
        self.sites.insertSeriesSiteByNameAndIndex(self, seriesName, idx)
        self.sites.lookupSeries(seriesName)[idx].attach(self, child, childSite)
        self.markLayoutDirty()

    def replaceChild(self, newChild, siteId, leavePlace=False, childSite=None):
        # Checks and special rules for comprehension series with no commas.
        siteName, seriesIdx = splitSeriesSiteId(siteId)
        if siteName == 'cprhIcons':
            # Generic version of insertChild is intended for series with commas.  Never
            # leave an empty site when there is no way to see or access it
            if seriesIdx == len(self.sites.cprhIcons) - 1:
                self.insertChild(newChild, siteName, seriesIdx)
            else:
                Icon.replaceChild(self, newChild, siteId, False, childSite)
        else:
            Icon.replaceChild(self, newChild, siteId, leavePlace, childSite)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        if self.isComprehension():
            if forCursor:
                return siteSnapLists
            x = self.rect[0] + INSERT_SITE_X_OFFSET
            y = self.rect[1] + self.sites.cprhIcons[0].yOffset + INSERT_SITE_Y_OFFSET
            siteSnapLists['insertCprh'] = [(self, (x + site.xOffset, y), site.name)
             for site in self.sites.cprhIcons[:-1]]
        else:
            siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
            if not self.acceptsComprehension():
                del siteSnapLists['cprhIn']
        return siteSnapLists

    def inRectSelect(self, rect):
        # Require selection rectangle to touch both parens to be considered selected
        if not Icon.inRectSelect(self, rect):
            return False
        selLeft, selTop, selRight, selBottom = rect
        icLeft, icTop, icRight, icBottom = self.rect
        if selLeft > icLeft + self.leftImgFn(0).width:
            return False
        if selRight < icRight - self.rightImgFn(0).width:
            return False
        return True

    def doLayout(self, outSiteX, outSiteY, layout):
        self.argList.doLayout(layout)
        self.sites.output.yOffset = self.argList.spineTop
        self.sites.seqOut.yOffset = self.argList.spineHeight - 2
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        if self.closed:
            width = self.sites.cprhIcons[-1].xOffset + self.rightImgFn(0).width
        else:
            width = self.sites.cprhIcons[-1].xOffset
        x = outSiteX
        #y = outSiteY - self.sites.output.yOffset
        y = outSiteY - self.argList.spineTop
        self.rect = (x, y, x + width, y + self.argList.spineHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        argListLayouts = self.argList.calcLayouts()
        cprhLayoutLists = [(None,) if site.att is None else site.att.calcLayouts()
                for site in self.sites.cprhIcons]
        if not self.closed or self.sites.attrIcon.att is None:
            attrLayouts = (None,)
        else:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        layouts = []
        for argListLayout, attrLayout, *cprhLayouts in allCombinations((argListLayouts,
                attrLayouts, *cprhLayoutLists)):
            leftWidth, minHeight = self.leftImgFn(0).size
            leftWidth -= OUTPUT_SITE_DEPTH
            layout = Layout(self, leftWidth, minHeight, minHeight // 2)
            argListLayout.mergeInto(layout, leftWidth - 1, 0)
            cprhWidth = 0
            leftCprhX = leftWidth - 1 + argListLayout.width - 1
            cprhY = 0  # In-line with output because comprehensions have only one arg
            for siteIdx, site in enumerate(self.sites.cprhIcons):
                cprhLayout = cprhLayouts[siteIdx]
                layout.addSubLayout(cprhLayout, site.name, leftCprhX + cprhWidth, cprhY)
                cprhWidth += 0 if cprhLayout is None else cprhLayout.width - 1
            if self.closed:
                layout.width = leftWidth - 1 + argListLayout.width - 1 + cprhWidth + \
                        self.rightImgFn(0).width
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1,
                        ATTR_SITE_OFFSET)
            else:
                layout.width = leftWidth - 1 + argListLayout.width - 1 + cprhWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Add back the attribute site on the end brace/bracket.  Done here to allow the
        # site to be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', rectWidth(self.rect) -
         ATTR_SITE_DEPTH, rectHeight(self.rect) // 2 + ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def textRepr(self):
        argText = _seriesTextRepr(self.sites.argIcons)
        cprhText = ""
        for site in self.sites.cprhIcons[:-1]:
            cprhText += " " + site.att.textRepr()
        return self.leftText + argText + cprhText+ self.rightText + _attrTextRepr(self)

    def argIcons(self):
        """Return list of list argument icons.  This is trivial, but exists to give list
        and dict icons an identical interface with that of the TupleIcon version which
        which has to deal with."""
        return [site.att for site in self.sites.argIcons]

    def dumpName(self):
        return self.leftText + ("" if self.closed else self.rightText)

class ListIcon(ListTypeIcon):
    def __init__(self, window, closed=True, location=None):
        ListTypeIcon.__init__(self, '[', ']', window, location=location,
                closed=closed, leftImgFn=self._stretchedLBracketImage,
                rightImgFn=self._stretchedRBracketImage)

    def execute(self):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return eval(self.textRepr())
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return []
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
        result = [site.att.execute() for site in self.sites.argIcons]
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return composeAttrAst(self, createComprehensionAst(self))
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            elts = []
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            elts = [site.att.createAst() for site in self.sites.argIcons]
        return composeAttrAst(self, ast.List(elts=elts, ctx=determineCtx(self),
         lineno=self.id, col_offset=0))

    @staticmethod
    def _stretchedLBracketImage(desiredHeight):
        return yStretchImage(listLBktImage, listLBrktExtendDupRows, desiredHeight)

    @staticmethod
    def _stretchedRBracketImage(desiredHeight):
        return yStretchImage(listRBktImage, listRBrktExtendDupRows, desiredHeight)

class TupleIcon(ListTypeIcon):
    def __init__(self, window, noParens=False, closed=True, location=None):
        self.noParens = noParens
        self.argList = None  # Temporary to help with initialization
        ListTypeIcon.__init__(self, '(', ')', window, closed=closed, location=location,
         leftImgFn=self._stretchedLTupleImage, rightImgFn=self._stretchedRTupleImage)
        if noParens:
            self.sites.remove('attrIn')

    def argIcons(self):
        """Return list of tuple argument icons, handling special case of a single element
        tuple represented as (x,).  It would be nice to convert these at type-in, but
        hard to distinguish from leaving a space for a second argument."""
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return []
        if len(self.sites.argIcons) == 2 and self.sites.argIcons[0].att is not None and \
         self.sites.argIcons[1] is None:
            # Special case of single item tuple allowed to have missing arg
            return [self.sites.argIcons.att[0]]
        return [site.att for site in self.sites.argIcons]

    def restoreParens(self):
        """Tuples with no parenthesis are allowed on the top level, to make typing
        multi-variable assignment statements more natural.  If one of these paren-less
        icons gets dragged or pasted in to an expression, it needs its parens back."""
        if not self.noParens:
            return
        self.noParens = False
        self.drawList = None
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.removeParens)

    def removeParens(self):
        if self.noParens:
            return
        self.noParens = True
        self.drawList = None
        self.markLayoutDirty()
        self.window.undo.registerCallback(self.restoreParens)

    def acceptsComprehension(self):
        # Redefine to add prohibition on no-paren tuple becoming generator comprehension
        return len(self.sites.argIcons) <= 1 and not self.noParens

    def calcLayouts(self):
        # If the icon is no longer at the top level and needs its parens restored, do so
        # before calculating the layout (would be better to do this elsewhere).
        if self.noParens and self.parent() is not None:
            self.restoreParens()
        return ListTypeIcon.calcLayouts(self)

    def execute(self):
        if self.isComprehension():
            return eval(self.textRepr())
        argIcons = self.argIcons()
        for argIcon in argIcons:
            if argIcon is None:
                raise IconExecException(self, "Missing argument(s)")
        result = tuple(argIcon.execute() for argIcon in argIcons)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return composeAttrAst(self, createComprehensionAst(self))
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            elts = []
        elif len(self.sites.argIcons) == 2 and self.sites.argIcons[0].att is not None \
         and self.sites.argIcons[1].att is None:
            elts = [self.sites.argIcons[0].att.createAst()]  # Traditional form: (1, )
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            elts = [site.att.createAst() for site in self.sites.argIcons]
        return composeAttrAst(self, ast.Tuple(elts=elts, ctx=determineCtx(self),
         lineno=self.id, col_offset=0))

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, noParens=self.noParens,
         closed=self.closed)

    def _stretchedLTupleImage(self, desiredHeight):
        if self.noParens:
            if self.argList is not None and self.argList.rowWidths is not None and \
                    len(self.argList.rowWidths) >= 2:
                img = lSimpleSpineImage
            else:
                img = inpOptionalSeqImage
        else:
            img = tupleLParenImage
        return yStretchImage(img, tupleLParenExtendDupRows, desiredHeight)

    def _stretchedRTupleImage(self, desiredHeight):
        if self.noParens:
            if self.argList is not None and self.argList.rowWidths is not None and \
                    len(self.argList.rowWidths) >= 2:
                img = rSimpleSpineImage
            else:
                return emptyImage
        else:
            img = tupleRParenImage
        return yStretchImage(img, tupleRParenExtendDupRows, desiredHeight)

class DictIcon(ListTypeIcon):
    def __init__(self, window, closed=True, location=None):
        ListTypeIcon.__init__(self, '{', '}', window,
                leftImgFn=self._stretchedLBraceImage,
                rightImgFn=self._stretchedRBraceImage, closed=closed, location=location)

    def execute(self):
        if self.isComprehension():
            return eval(self.textRepr())
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return {}
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
            if site.att.__class__ not in (StarStarIcon, DictElemIcon):
                raise IconExecException(self, "Bad format for dictionary element")
        result = {}
        for site in self.sites.argIcons:
            if isinstance(site.att, DictElemIcon):
                key, value = site.att.execute()
                result[key] = value
            elif isinstance(site.att, StarStarIcon):
                result = {**result, **site.att.execute()}
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if self.isComprehension():
            return composeAttrAst(self, createComprehensionAst(self))
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            # Empty Dict
            return composeAttrAst(self, ast.Dict([], [], lineno=self.id, col_offset=0))
        else:
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            for site in self.sites.argIcons:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            elts = [site.att for site in self.sites.argIcons]
            # Check for consistency: are we a set or a dictionary constant
            isDict = len(elts) == 0 or isinstance(elts[0], DictElemIcon) or \
             isinstance(elts[0], StarStarIcon)
            for elt in elts:
                if isDict and elt.__class__ not in (DictElemIcon, StarStarIcon):
                    raise IconExecException(self, "Inconsistent dict/set content")
            if isDict:
                keyAsts = []
                valueAsts = []
                for elt in elts:
                    if isinstance(elt, DictElemIcon):
                        keyAsts.append(elt.childAt('leftArg').createAst())
                        valueAsts.append(elt.childAt('rightArg').createAst())
                    else:  # StarStarIcon
                        keyAsts.append(None)
                        valueAsts.append(elt.childAt('argIcon').createAst())
                return composeAttrAst(self, ast.Dict(keyAsts, valueAsts, lineno=self.id,
                 col_offset=0))
            else:
                eltAsts = [elt.createAst() for elt in elts]
                return composeAttrAst(self, ast.Set(elts=eltAsts, lineno=self.id,
                 col_offset=0))

    def snapLists(self, forCursor=False):
        siteSnapLists = ListTypeIcon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        _restoreConditionalTargets(self, siteSnapLists, (DictElemIcon, StarStarIcon))
        return siteSnapLists

    @staticmethod
    def _stretchedLBraceImage(desiredHeight):
        return yStretchImage(lBraceImage, lBraceExtendDupRows, desiredHeight)

    @staticmethod
    def _stretchedRBraceImage(desiredHeight):
        return yStretchImage(rBraceImage, rBraceExtendDupRows, desiredHeight)

class CprhIfIcon(Icon):
    def __init__(self, window, location=None):
        Icon.__init__(self, window)
        bodyWidth = getTextSize(" if", boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('cprhOut', 'cprhOut', 0, siteYOffset)
        self.sites.add('testIcon', 'input', bodyWidth-1 - OUTPUT_SITE_DEPTH, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            img = Image.new('RGBA', (bodyWidth, bodyHeight), color=(0, 0, 0, 0))
            img.paste(iconBoxedText(" if", boldFont, KEYWORD_COLOR), (0, 0))
            cphYOff = bodyHeight // 2 - cphSiteImage.height // 2
            img.paste(cphSiteImage, (0, cphYOff))
            inImageY = self.sites.testIcon.yOffset - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.testIcon.xOffset, inImageY))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, cprhX, cprhY, layout):
        width, height = self.bodySize
        top = cprhY - height // 2
        self.rect = (cprhX, top, cprhX + width, top + height)
        layout.doSubLayouts(self.sites.cprhOut, cprhX, cprhY)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        if self.sites.testIcon.att is None:
            testIconLayouts = (None,)
        else:
            testIconLayouts = self.sites.testIcon.att.calcLayouts()
        layouts = []
        for testIconLayout in testIconLayouts:
            layout = Layout(self, width, height, height // 2)
            layout.addSubLayout(testIconLayout, 'testIcon', width-1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "if " + _singleArgTextRepr(self.sites.testIcon)

    def createAst(self):
        if self.sites.testIcon.att is None:
            raise IconExecException(self, 'Missing argument to "if" in comprehension')
        return self.sites.testIcon.att.createAst()

class CprhForIcon(Icon):
    def __init__(self, isAsync=False, window=None, location=None):
        Icon.__init__(self, window)
        self.isAsync = isAsync
        text = " async for" if isAsync else " for"
        bodyWidth = getTextSize(text)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        inWidth = getTextSize("in")[0] + 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, inWidth)
        siteYOffset = bodyHeight // 2
        targetXOffset = bodyWidth - OUTPUT_SITE_DEPTH
        self.tgtList = ListLayoutMgr(self, 'targets', targetXOffset, siteYOffset,
                simpleSpine=True)
        self.sites.add('cprhOut', 'cprhOut', 0, siteYOffset)
        iterX = bodyWidth-1 + self.tgtList.width-1 + inWidth-1
        self.sites.add('iterIcon', 'input', iterX, siteYOffset)
        totalWidth = iterX
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            bodyWidth, bodyHeight, inWidth = self.bodySize
            img = Image.new('RGBA', (bodyWidth, bodyHeight),
             color=(0, 0, 0, 0))
            txt = " async for" if self.isAsync else " for"
            txtImg = iconBoxedText(txt, color=KEYWORD_COLOR)
            img.paste(txtImg, (0, 0))
            img.paste(cphSiteImage, (0, bodyHeight // 2 - cphSiteImage.height // 2))
            inImgX = bodyWidth - 1 - inSiteImage.width
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (inImgX, inImageY))
            cntrSiteY = self.tgtList.spineTop
            bodyTopY = cntrSiteY - bodyHeight // 2
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            tgtListOffset = bodyWidth - 1 - OUTPUT_SITE_DEPTH
            self.drawList += self.tgtList.drawSimpleSpine(tgtListOffset, cntrSiteY)
            # Target list commas
            self.drawList += self.tgtList.drawListCommas(tgtListOffset, cntrSiteY)
            # "in"
            txtImg = iconBoxedText("in", color=KEYWORD_COLOR)
            img = Image.new('RGBA', (txtImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            inImgX = txtImg.width - inSiteImage.width
            inImageY = cntrSiteY - inSiteImage.height // 2
            img.paste(inSiteImage, (inImgX, inImageY))
            inOffset = bodyWidth - 1 + self.tgtList.width - 1
            self.drawList.append(((inOffset, bodyTopY), img))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.tgtList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, cprhX, cprhY, layout):
        self.tgtList.doLayout(layout)
        bodyWidth, bodyHeight, inWidth = self.bodySize
        width = bodyWidth-1 + self.tgtList.width-1 + inWidth
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        if self.tgtList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.tgtList.spineTop)
            heightBelow = max(heightBelow, self.tgtList.spineHeight -
                    self.tgtList.spineTop)
        self.sites.cprhOut.yOffset = heightAbove
        left = cprhX
        top = cprhY - heightAbove
        self.rect = (left, top, left + width, top + heightAbove + heightBelow)
        layout.updateSiteOffsets(self.sites.cprhOut)
        layout.doSubLayouts(self.sites.cprhOut, cprhX, cprhY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        tgtListLayouts =  self.tgtList.calcLayouts()
        if self.sites.iterIcon.att is None:
            iterLayouts = (None,)
        else:
            iterLayouts = self.sites.iterIcon.att.calcLayouts()
        bodyWidth, bodyHeight, inWidth = self.bodySize
        tgtXOff = bodyWidth - 1
        layouts = []
        for tgtListLayout, iterLayout in allCombinations((tgtListLayouts, iterLayouts)):
            layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            tgtListLayout.mergeInto(layout, tgtXOff, 0)
            iterXOff = bodyWidth - 1 + tgtListLayout.width - 1 + inWidth - 1
            layout.addSubLayout(iterLayout, 'iterIcon', iterXOff, 0)
            iterWidth = 0 if iterLayout is None else iterLayout.width
            layout.width = iterXOff + iterWidth
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        text = "async for" if self.isAsync else "for"
        tgtText = _seriesTextRepr(self.sites.targets)
        iterText = _singleArgTextRepr(self.sites.iterIcon)
        return text + " " + tgtText + " in " + iterText

    def dumpName(self):
        return "for (cprh)"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self, ifAsts):
        if self.sites.iterIcon.att is None:
            raise IconExecException(self, 'Missing iteration value in comprehension')
        iterAst = self.sites.iterIcon.att.createAst()
        for target in self.sites.targets:
            if target.att is None:
                raise IconExecException(self, 'Missing target in comprehension')
        tgtAsts = [tgt.att.createAst() for tgt in self.sites.targets]
        if len(tgtAsts) == 1:
            targetAst = tgtAsts[0]
        else:
            targetAst = ast.Tuple(tgtAsts, ctx=ast.Store(), lineno=self.id, col_offset=0)
        return ast.comprehension(targetAst, iterAst, ifAsts, self.isAsync)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft - 1
        bodyWidth, bodyHeight, inWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return python_g.rectsTouch(rect, bodyRect)

class BinOpIcon(Icon):
    def __init__(self, op, window, location=None):
        Icon.__init__(self, window)
        self.operator = op
        self.precedence = binOpPrecedence[op]
        self.hasParens = False  # Filled in by layout methods
        self.leftArgWidth = EMPTY_ARG_WIDTH
        self.rightArgWidth = EMPTY_ARG_WIDTH
        opWidth, opHeight = getTextSize(self.operator)
        opHeight = max(opHeight + 2*TEXT_MARGIN + 1, lParenImage.height)
        opWidth += 2*TEXT_MARGIN - 1
        self.opSize = (opWidth, opHeight)
        self.depthWidth = 0
        x, y = (0, 0) if location is None else location
        width, height = self._size()
        self.rect = (x, y, x + width, y + height)
        siteYOffset = opHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('leftArg', 'input', 0, siteYOffset)
        self.sites.add('rightArg', 'input', self.leftArgWidth + opWidth, siteYOffset)
        # Note that the attrIcon site is only usable when parens are displayed
        self.sites.add("attrIcon", "attrIn",
         self.leftArgWidth + opWidth - ATTR_SITE_DEPTH, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - SEQ_SITE_DEPTH, height-2)
        # Indicates that input site falls directly on top of output site
        self.coincidentSite = 'leftArg'

    def _size(self):
        opWidth, opHeight = self.opSize
        opWidth += self.depthWidth
        if self.hasParens:
            parenWidth = lParenImage.width - 1 + rParenImage.width - 1
        else:
            parenWidth = 0
        width = parenWidth + self.leftArgWidth + self.rightArgWidth + opWidth
        return width, opHeight

    def leftArg(self):
        return self.sites.leftArg.att if self.sites.leftArg is not None else None

    def rightArg(self):
        return self.sites.rightArg.att if self.sites.rightArg is not None else None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        atTop = self.parent() is None
        suppressSeqSites = toDragImage is not None and self.prevInSeq() is None
        temporaryOutputSite = suppressSeqSites and atTop and self.leftArg() is None
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
            leftArgX = outSiteX + outSiteImage.width - 1
            if self.hasParens:
                outSiteY = siteY - lParenImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), lParenImage))
                leftArgX = outSiteX + lParenImage.width - 1
            elif temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binOutImage))
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - binInSeqImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binInSeqImage))
            # Body
            txtImg = iconBoxedText(self.operator)
            opWidth, opHeight = self.opSize
            opWidth = txtImg.width + self.depthWidth
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            opX = leftArgX + self.leftArgWidth - 1
            opY = siteY - txtImg.height // 2
            if self.depthWidth > 0:
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 0, opWidth - 1, txtImg.height - 1),
                 outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
                txtSubImg = txtImg.crop((1, 0, txtImg.width - 1, txtImg.height))
                img.paste(txtSubImg, (self.depthWidth // 2 + 1, opY))
            else:
                img.paste(txtImg, (self.depthWidth // 2, opY))
            rInSiteX = opWidth - inSiteImage.width
            rInSiteY = siteY - inSiteImage.height // 2
            img.paste(inSiteImage, (rInSiteX, rInSiteY))
            self.drawList.append(((opX, 0), img))
            # End paren
            if self.hasParens:
                rParenX = opX + opWidth - 1 + self.rightArgWidth - 1
                rParenY = siteY - rParenImage.height // 2
                self.drawList.append(((rParenX, rParenY), rParenImage))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryOutputSite or suppressSeqSites:
            self.drawList = None  # Don't keep after drawing (see above)

    def depth(self, lDepth=None, rDepth=None):
        """Calculate factor which decides how much to pad the operator to help indicate
        its level in the icon hierarchy.  The function does not expand the operator icon
        when it and a child or parent form an associative group (so chains of operations,
        like: 1 + 2 + 3 + 4, don't get out of control).  While this looks much nicer, it
        has great potential confuse users who need to understand the hierarchy to edit
        effectively.  Parameters lDepth and rDepth allow a recursive call to calculate
        parent depth, which would otherwise recurse infinitely."""
        if lDepth is None:
            lChild = self.leftArg()
            if lChild is None or lChild.__class__ is not BinOpIcon:
                lDepth = 0
            else:
                lDepth = lChild.depth()
                if not (lChild.leftAssoc() and lChild.precedence == self.precedence):
                    lDepth += 1
        if rDepth is None:
            rChild = self.rightArg()
            if rChild is None or rChild.__class__ is not BinOpIcon:
                rDepth = 0
            else:
                rDepth = rChild.depth()
                if not (rChild.rightAssoc() and rChild.precedence == self.precedence):
                    rDepth += 1
        myDepth = max(lDepth, rDepth)
        # Also expand the operator to match the parent end of the associative group
        parent = self.parent()
        if parent.__class__ is BinOpIcon and parent.precedence == self.precedence:
            if parent.siteOf(self) == "leftArg" and parent.leftAssoc():
                myDepth = max(myDepth, parent.depth(lDepth=myDepth))
            elif parent.siteOf(self) == "rightArg" and parent.rightAssoc():
                myDepth = max(myDepth, parent.depth(rDepth=myDepth))
        return myDepth

    def doLayout(self, outSiteX, outSiteY, layout):
        self.hasParens = layout.hasParens
        self.coincidentSite = None if self.hasParens else "leftArg"
        self.leftArgWidth = layout.lArgWidth
        self.rightArgWidth = layout.rArgWidth
        self.depthWidth = layout.depthWidth
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        hasParens = needsParens(self)
        if hasParens:
            lParenWidth = lParenImage.width - OUTPUT_SITE_DEPTH - 1
            rParenWidth = rParenImage.width - 1
        else:
            lParenWidth = rParenWidth = 0
        opWidth, opHeight = self.opSize
        lArg = self.leftArg()
        lArgLayouts = [None] if lArg is None else lArg.calcLayouts()
        rArg = self.rightArg()
        rArgLayouts = [None] if rArg is None else rArg.calcLayouts()
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        layouts = []
        for lArgLayout, rArgLayout, attrLayout in allCombinations((lArgLayouts,
                rArgLayouts, attrLayouts)):
            layout = Layout(self, opWidth, opHeight, opHeight // 2)
            layout.hasParens = hasParens
            layout.addSubLayout(lArgLayout, "leftArg", lParenWidth, 0)
            lArgWidth = EMPTY_ARG_WIDTH if lArgLayout is None else lArgLayout.width
            layout.lArgWidth = lArgWidth
            depthWidth = self.depth() * DEPTH_EXPAND
            layout.depthWidth = depthWidth
            rArgSiteX = lParenWidth + lArgWidth + opWidth + depthWidth
            layout.addSubLayout(rArgLayout, "rightArg", rArgSiteX, 0)
            rArgWidth = EMPTY_ARG_WIDTH if rArgLayout is None else rArgLayout.width
            layout.rArgWidth = rArgWidth
            layout.width = rArgSiteX + rArgWidth + rParenWidth
            layout.addSubLayout(attrLayout, 'attrIcon', layout.width - ATTR_SITE_DEPTH,
                    ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def snapLists(self, forCursor=False):
        # Make attribute site unavailable unless the icon has parens to hold it
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        if not self.hasParens:
            del siteSnapLists['attrIn']
        return siteSnapLists

    def textRepr(self):
        leftArgText = _singleArgTextRepr(self.sites.leftArg)
        rightArgText = _singleArgTextRepr(self.sites.rightArg)
        text = leftArgText + " " + self.operator + " " + rightArgText
        if self.hasParens:
            return "(" + text + ")" + _attrTextRepr(self)
        return text

    def dumpName(self):
        return ("(%s)" if self.hasParens else "%s") % self.operator

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, op=self.operator)

    def locIsOnLeftParen(self, btnPressLoc):
        iconLeft = self.rect[0]
        return iconLeft < btnPressLoc[0] < iconLeft + lParenImage.width

    def leftAssoc(self):
        return self.operator != "**"

    def rightAssoc(self):
        return self.operator == "**"

    def execute(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing left operand")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing right operand")
        leftValue = self.leftArg().execute()
        rightValue = self.rightArg().execute()
        try:
            result = binOpFn[self.operator](leftValue, rightValue)
        except Exception as err:
            raise IconExecException(self, err)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self):
        if self.leftArg() is None:
            raise IconExecException(self, "Missing left operand")
        if self.rightArg() is None:
            raise IconExecException(self, "Missing right operand")
        if self.operator in compareAsts:
            return ast.Compare(left=self.leftArg().createAst(),
             ops=[compareAsts[self.operator]()],
             comparators=[self.rightArg().createAst()], lineno=self.id, col_offset=0)
        return ast.BinOp(lineno=self.id, col_offset=0, left=self.leftArg().createAst(),
         op=binOpAsts[self.operator](), right=self.rightArg().createAst())

    def selectionRect(self):
        # Limit selection rectangle for extending selection to op itself
        opWidth, opHeight = self.opSize
        opWidth += self.depthWidth
        rightOffset = self.sites.rightArg.xOffset + OUTPUT_SITE_DEPTH
        leftOffset = rightOffset - opWidth
        x, top = self.rect[:2]
        left = x + leftOffset
        return left, top, left + opWidth, top + opHeight

    def inRectSelect(self, rect):
        if not python_g.rectsTouch(rect, self.rect):
            return False
        return python_g.rectsTouch(rect, self.selectionRect())

class CallIcon(Icon):
    def __init__(self, window, closed=True, location=None):
        Icon.__init__(self, window)
        self.closed = False
        leftWidth, leftHeight = fnLParenImage.size
        attrSiteY = leftHeight // 2 + ATTR_SITE_OFFSET
        self.sites.add('attrOut', 'attrOut', 0, attrSiteY)
        self.argList = ListLayoutMgr(self, 'argIcons', leftWidth, leftHeight//2)
        width, height = self._size()
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + width, y + height)
        if closed:
            self.close()

    def _size(self):
        width = fnLParenImage.width
        height = self.argList.spineHeight
        if self.closed:
            width += self.argList.width + fnRParenImage.width - 1
        else:
            width += self.argList.width
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if self.drawList is None:
            # Left paren/bracket/brace
            lParenImg = fnLParenImage if self.closed else fnLParenOpenImage
            lParenImg = yStretchImage(lParenImg, fnLParenExtendDupRows,
                    self.argList.spineHeight)
            # Output site
            outSiteX = self.sites.attrOut.xOffset
            outSiteY = self.sites.attrOut.yOffset - attrOutImage.height // 2
            lParenImg.paste(dimAttrOutImage, (outSiteX, outSiteY), mask=attrOutImage)
            # Body input site(s)
            self.argList.drawBodySites(lParenImg)
            self.drawList = [((0, 0), lParenImg)]
            # Commas
            self.drawList += self.argList.drawListCommas(lParenImg.width -
                    OUTPUT_SITE_DEPTH - 1, self.sites.attrOut.yOffset - ATTR_SITE_OFFSET)
            # End paren/brace/bracket
            if self.closed:
                parenX = lParenImg.width + self.argList.width - ATTR_SITE_DEPTH - 1
                rParenImg = yStretchImage(fnRParenImage, fnRParenExtendDupRows,
                        self.argList.spineHeight)
                attrInXOff = rParenImg.width - attrInImage.width
                attrInYOff = self.sites.attrIcon.yOffset
                rParenImg.paste(attrInImage, (attrInXOff, attrInYOff))
                self.drawList.append(((parenX, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def argIcons(self):
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return siteSnapLists
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        _restoreConditionalTargets(self, siteSnapLists,
         (StarIcon, StarStarIcon, ArgAssignIcon))
        return siteSnapLists

    def doLayout(self, attrSiteX, attrSiteY, layout):
        self.argList.doLayout(layout)
        self.sites.attrOut.yOffset = self.argList.spineTop + ATTR_SITE_OFFSET
        layout.updateSiteOffsets(self.sites.attrOut)
        layout.doSubLayouts(self.sites.attrOut, attrSiteX, attrSiteY)
        width, height = self._size()
        x = attrSiteX
        y = attrSiteY - self.argList.spineTop - ATTR_SITE_OFFSET
        self.rect = (x, y, x + width, y + self.argList.spineHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = fnLParenImage.size
        bodyWidth -= ATTR_SITE_DEPTH
        argListLayouts = self.argList.calcLayouts()
        if self.closed and self.sites.attrIcon.att is not None:
            attrLayouts = self.sites.attrIcon.att.calcLayouts()
        else:
            attrLayouts = [None]
        layouts = []
        for argLayout, attrLayout in allCombinations((argListLayouts, attrLayouts)):
            layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2 + ATTR_SITE_OFFSET)
            argLayout.mergeInto(layout, bodyWidth - 1, -ATTR_SITE_OFFSET)
            argWidth = argLayout.width
            # layout now incorporates argument layout sizes, but not end paren
            if self.closed:
                layout.width = fnLParenImage.width-1 + argWidth-1 + fnRParenImage.width-1
                layout.addSubLayout(attrLayout, 'attrIcon', layout.width-1, 0,)
            else:
                layout.width = fnLParenImage.width-1 + argWidth-1
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.markLayoutDirty()
        # Add back the attribute site on the end paren.  Done here to allow the site to
        # be used for cursor or new attachments before layout knows where it goes
        self.sites.add('attrIcon', 'attrIn', rectWidth(self.rect) -
         ATTR_SITE_DEPTH, rectHeight(self.rect) // 2 + ATTR_SITE_OFFSET)
        self.window.undo.registerCallback(self.reopen)

    def reopen(self):
        if not self.closed:
            return
        self.closed = False
        self.markLayoutDirty()
        self.sites.remove('attrIcon')
        self.window.undo.registerCallback(self.close)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, closed=self.closed)

    def textRepr(self):
        return '(' + _seriesTextRepr(self.sites.argIcons) + ')' + _attrTextRepr(self)

    def dumpName(self):
        return "call("  + (")" if self.closed else "")

    def execute(self, attrOfValue):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        if len(self.sites.argIcons) == 1 and self.sites.argIcons[0].att is None:
            return None
        for site in self.sites.argIcons:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
        args = []
        kwArgs = {}
        for site in self.sites.argIcons:
            if isinstance(site.att, ArgAssignIcon):
                key, val = site.att.execute()
                kwArgs[key] = val
            elif isinstance(site.att, StarIcon):
                args += site.att.execute()
            elif isinstance(site.att, StarStarIcon):
                kwArgs = {**kwArgs, **site.att.execute()}
            else:
                args.append(site.att.execute())
        result = attrOfValue(*args, **kwArgs)
        if self.sites.attrIcon.att:
            return self.sites.attrIcon.att.execute(result)
        return result

    def createAst(self, attrOfAst):
        if not self.closed:
            raise IconExecException(self, "Unclosed temporary icon")
        argAsts = []
        kwdArgAsts = []
        for site in self.sites.argIcons:
            arg = site.att
            if arg is None:
                if site.name == 'argIcons_0':
                    continue  # 1st site can be empty, meaning "no arguments"
                raise IconExecException(self, "Missing argument(s)")
            if isinstance(arg, ArgAssignIcon):
                key = arg.sites.leftArg.att
                value = arg.sites.rightArg.att
                if key is None:
                    raise IconExecException(arg, "Missing keyword")
                if not isinstance(key, IdentifierIcon):
                    raise IconExecException(arg, "Keyword must be identifier")
                if value is None:
                    raise IconExecException(arg, "Missing keyword value")
                kwdArgAsts.append(ast.keyword(key.name, value.createAst()))
            elif isinstance(arg, StarStarIcon):
                if arg.sites.argIcon.att is None:
                    raise IconExecException(arg, "Missing value for **")
                kwdArgAsts.append(ast.keyword(None, arg.sites.argIcon.att.createAst()))
            else:
                argAsts.append(arg.createAst())
        return composeAttrAst(self, ast.Call(attrOfAst, argAsts, kwdArgAsts,
         lineno=self.id, col_offset=0))

    def inRectSelect(self, rect):
        # Require selection rectangle to touch both parens to be considered selected
        if not Icon.inRectSelect(self, rect):
            return False
        selLeft, selTop, selRight, selBottom = rect
        icLeft, icTop, icRight, icBottom = self.rect
        if selLeft > icLeft + fnLParenImage.width:
            return False
        if selRight < icRight - fnRParenImage.width:
            return False
        return True

class TwoArgIcon(Icon):
    def __init__(self, op, opImg=None, window=None, location=None):
        Icon.__init__(self, window)
        self.operator = op
        if opImg is None:
            opTxt = iconBoxedText(op)
            opImg = Image.new('RGBA', opTxt.size, color=(0, 0, 0, 0))
            opImg.paste(opTxt, (0, 0))
            rInSiteX = opTxt.width - inSiteImage.width
            rInSiteY = opTxt.height // 2 - inSiteImage.height // 2
            opImg.paste(inSiteImage, (rInSiteX, rInSiteY))
        self.opImg = opImg
        self.leftArgWidth = EMPTY_ARG_WIDTH
        x, y = (0, 0) if location is None else location
        width = self.leftArgWidth - 1 + opImg.width
        self.rect = (x, y, x + width, y + opImg.height)
        siteYOffset = opImg.height // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        self.sites.add('leftArg', 'input', 0, siteYOffset)
        self.sites.add('rightArg', 'input', self.leftArgWidth + opImg.width, siteYOffset)
        self.sites.add('seqIn', 'seqIn', - SEQ_SITE_DEPTH, 1)
        self.sites.add('seqOut', 'seqOut', - SEQ_SITE_DEPTH, opImg.height-2)
        # Indicates that input site falls directly on top of output site
        self.coincidentSite = 'leftArg'

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        atTop = self.parent() is None
        suppressSeqSites = toDragImage is not None and self.prevInSeq() is None
        temporaryOutputSite = suppressSeqSites and atTop and self.sites.leftArg.att is None
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
            leftArgX = outSiteX + outSiteImage.width - 1
            if temporaryOutputSite:
                outSiteY = siteY - binOutImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binOutImage))
            elif atTop and not suppressSeqSites:
                outSiteY = siteY - binInSeqImage.height // 2
                self.drawList.append(((outSiteX, outSiteY), binInSeqImage))
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
        for lArgLayout, rArgLayout in allCombinations((lArgLayouts, rArgLayouts)):
            layout = Layout(self, opWidth, opHeight, opHeight // 2)
            layout.addSubLayout(lArgLayout, "leftArg", 0, 0)
            lArgWidth = EMPTY_ARG_WIDTH if lArgLayout is None else lArgLayout.width
            layout.lArgWidth = lArgWidth
            layout.width = lArgWidth - 1 + opWidth
            layout.addSubLayout(rArgLayout, "rightArg", layout.width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        leftArgText = _singleArgTextRepr(self.sites.leftArg)
        rightArgText = _singleArgTextRepr(self.sites.rightArg)
        return leftArgText + " " + self.operator + " " + rightArgText

    def dumpName(self):
        return self.operator

    def selectionRect(self):
        # Limit selection rectangle for extending selection to op itself
        opWidth, opHeight = self.opImg.size
        rightOffset = self.sites.rightArg.xOffset + OUTPUT_SITE_DEPTH
        leftOffset = rightOffset - opWidth
        x, top = self.rect[:2]
        left = x + leftOffset
        return left, top, left + opWidth, top + opHeight

    def inRectSelect(self, rect):
        if not python_g.rectsTouch(rect, self.rect):
            return False
        return python_g.rectsTouch(rect, self.selectionRect())

    def leftArg(self):
        return self.sites.leftArg.att if self.sites.leftArg is not None else None

    def rightArg(self):
        return self.sites.rightArg.att if self.sites.rightArg is not None else None

class ArgAssignIcon(TwoArgIcon):
    """Special assignment statement for use only in function argument lists"""
    def __init__(self, window=None, location=None):
        TwoArgIcon.__init__(self, "=", argAssignImage, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on being part of an argument or parameter list
        snapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = splitSeriesSiteId(siteId)
            return ic.__class__ in (CallIcon, DefIcon, ClassDefIcon) and \
             siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def execute(self):
        if self.sites.leftArg.att is None:
            raise IconExecException(self, "Missing argument name")
        if self.sites.rightArg.att is None:
            raise IconExecException(self, "Missing argument value")
        if not isinstance(self.sites.leftArg.att, IdentifierIcon):
            raise IconExecException(self, "Argument name is not identifier")
        return self.sites.leftArg.att.name, self.sites.rightArg.att.execute()

class DictElemIcon(TwoArgIcon):
    """Individual entry in a dictionary constant"""
    def __init__(self, window=None, location=None):
        TwoArgIcon.__init__(self, ":", colonImage, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a dictionary constant
        snapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = splitSeriesSiteId(siteId)
            return isinstance(ic, DictIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

    def execute(self):
        if self.sites.leftArg.att is None:
            raise IconExecException(self, "Missing argument name")
        if self.sites.rightArg.att is None:
            raise IconExecException(self, "Missing argument value")
        key = self.sites.leftArg.att.execute()
        value = self.sites.rightArg.att.execute()
        return key, value

class WithAsIcon(TwoArgIcon):
    def __init__(self, window=None, location=None):
        TwoArgIcon.__init__(self, "as", None, window, location)

    def snapLists(self, forCursor=False):
        # Make snapping conditional on parent being a "with" statement
        snapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor:
            return snapLists
        def snapFn(ic, siteId):
            siteName, siteIdx = splitSeriesSiteId(siteId)
            return isinstance(ic, WithIcon) and siteName == "argIcons"
        outSites = snapLists['output']
        snapLists['output'] = []
        snapLists['conditional'] = [(*snapData, 'output', snapFn) for snapData in outSites]
        return snapLists

class AssignIcon(Icon):
    def __init__(self, numTargets=1, window=None, location=None):
        Icon.__init__(self, window)
        opWidth, opHeight = getTextSize('=')
        opWidth += 2*TEXT_MARGIN + 1
        opHeight += 2*TEXT_MARGIN + 1
        siteY = inpSeqImage.height // 2
        self.opSize = (opWidth, opHeight)
        tgtSitesX = assignDragImage.width - 3
        seqSiteX = tgtSitesX + 1
        self.sites.add('seqIn', 'seqIn', seqSiteX, siteY - inpSeqImage.height // 2 + 1)
        self.sites.add('seqOut', 'seqOut', seqSiteX, siteY + inpSeqImage.height//2 - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteY)
        self.tgtLists = [ListLayoutMgr(self, 'targets0', tgtSitesX, siteY,
                simpleSpine=True)]
        valueSitesX = tgtSitesX + EMPTY_ARG_WIDTH + opWidth
        self.valueList = ListLayoutMgr(self, 'values', valueSitesX, siteY,
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
                tgtSiteX -= OUTPUT_SITE_DEPTH
            if temporaryDragSite:
                y = siteY - assignDragImage.height // 2
                self.drawList.append(((0, y), assignDragImage))
            elif not leftTgtHasSpine:
                y = siteY - inpSeqImage.height // 2
                self.drawList.append(((tgtSiteX, y), inpSeqImage))
            # Commas, spines and an = for each target group
            txtImg = iconBoxedText('=')
            opWidth, opHeight = txtImg.size
            img = Image.new('RGBA', (opWidth, opHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            rInSiteX = opWidth - inSiteImage.width
            rInSiteY = opHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (rInSiteX, rInSiteY))
            for i, tgtList in enumerate(self.tgtLists):
                self.drawList += tgtList.drawListCommas(tgtSiteX, siteY)
                spines = tgtList.drawSimpleSpine(tgtSiteX, siteY, drawOutputSite=False)
                if i == 0 and leftTgtHasSpine:
                    # If the leftmost target list has a spine, drawing of inpSeqImage
                    # was skipped, above, and we draw the sequence sites on the spine
                    leftSpineImg = spines[0][1]
                    drawSeqSites(leftSpineImg, 0, 0, leftSpineImg.height)
                self.drawList += spines
                tgtSiteX += tgtList.width - 1
                self.drawList.append(((tgtSiteX + OUTPUT_SITE_DEPTH, siteY - opHeight // 2), img))
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
        self.tgtLists.insert(idx, ListLayoutMgr(self, 'targetsX', 0, 0, simpleSpine=True))
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
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
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
                    raise IconExecException(self, "Missing assignment target(s)")
                tgts.append(site.att)
            tgtLists.append(tgts)
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing assignment value")
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
                    raise IconExecException(self, "Missing assignment target(s)")
                tgts.append(site.att)
            tgtLists.append(tgts)
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing assignment value")
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
        if isinstance(tgtIcon, IdentifierIcon):
            try:
                globals()[tgtIcon.name] = value
            except Exception as err:
                raise IconExecException(self, err)
            return
        if tgtIcon.__class__ in (TupleIcon, ListIcon):
            assignTargets = tgtIcon.argIcons()
        elif isinstance(tgtIcon, list):
            assignTargets = tgtIcon
        else:
            raise IconExecException(tgtIcon, "Not a valid assignment target")
        if not hasattr(value, "__len__") or len(assignTargets) != len(value):
            raise IconExecException(self, "Could not unpack")
        for target in assignTargets:
            if target is None:
                raise IconExecException(self, "Missing argument(s)")
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
        self.sites.seqOut.yOffset = leftSpineTop + self.tgtLists[0].spineHeight -1
        self.sites.seqInsert.yOffset = heightAbove
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + heightAbove)
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
        for valueLayout, *tgtLayouts in allCombinations((valueLayouts, *tgtListsLayouts)):
            layout = Layout(self, opWidth, opHeight, opHeight // 2)
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
            text += _seriesTextRepr(getattr(self.sites, tgtList.siteSeriesName)) + " = "
        return text +  _seriesTextRepr(self.sites.values)

class AugmentedAssignIcon(Icon):
    def __init__(self, op, window, location=None):
        Icon.__init__(self, window)
        self.op = op
        bodyWidth = getTextSize(self.op + '=')[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        targetXOffset = dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.sites.add('targetIcon', 'input', targetXOffset, siteYOffset)
        seqX = dragSeqImage.width - 1
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        self.targetWidth = EMPTY_ARG_WIDTH
        argX = dragSeqImage.width + self.targetWidth + bodyWidth
        self.valuesList = ListLayoutMgr(self, 'values', argX, siteYOffset,
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
            targetOffset = dragSeqImage.width - 1
            bodyOffset = targetOffset + self.targetWidth - 1
            txtImg = iconBoxedText(self.op + '=')
            img.paste(txtImg, (0, 0))
            inImageX = bodyWidth - inSiteImage.width
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (inImageX, inImageY))
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList.append(((bodyOffset, bodyTopY), img))
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valuesList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valuesList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valuesList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, left, top, layout):
        self.valuesList.doLayout(layout)
        self.targetWidth = layout.targetWidth
        bodyWidth, bodyHeight = self.bodySize
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        width = dragSeqImage.width - 1 + bodyWidth - 1 + self.targetWidth - 1 + \
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
        layout.doSubLayouts(self.sites.seqInsert, 0, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        valueListLayouts = self.valuesList.calcLayouts()
        targetIcon = self.sites.targetIcon.att
        tgtLayouts = [None] if targetIcon is None else targetIcon.calcLayouts()
        layouts = []
        for valueListLayout, tgtLayout in allCombinations((valueListLayouts, tgtLayouts)):
            layout = Layout(self, bodyWidth, bodyHeight, 1)
            layout.addSubLayout(tgtLayout, 'targetIcon', 0, 0)
            tgtWidth = EMPTY_ARG_WIDTH if tgtLayout is None else tgtLayout.width
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
        argText = _seriesTextRepr(self.sites.values)
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
            raise IconExecException(self, "Missing assignment target")
        tgtAst = self.sites.targetIcon.att.createAst()
        values = []
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing assignment value")
            values.append(site.att)
        # If there are multiple values, make a tuple out of them
        if len(values) == 1:
            valueAst = values[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in values], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        opAst = binOpAsts[self.op]()
        return ast.AugAssign(tgtAst, opAst, valueAst, lineno=self.id, col_offset=0)

class DivideIcon(Icon):
    def __init__(self, floorDiv=False, window=None, location=None):
        Icon.__init__(self, window)
        self.precedence = 11
        self.floorDiv = floorDiv
        emptyArgHeight = 14
        self.emptyArgSize = (EMPTY_ARG_WIDTH, emptyArgHeight)
        self.topArgSize = self.emptyArgSize
        self.bottomArgSize = self.emptyArgSize
        width, height = self._size()
        outSiteY = self.topArgSize[1] + 2
        self.sites.add('output', 'output', 0, outSiteY)
        self.sites.add('topArg', 'input', 2, outSiteY - emptyArgHeight // 2 - 2)
        self.sites.add('bottomArg', 'input', 2, outSiteY + emptyArgHeight // 2 + 2)
        self.sites.add('attrIcon', 'attrIn', width - 1, outSiteY + ATTR_SITE_OFFSET)
        seqX = OUTPUT_SITE_DEPTH - SEQ_SITE_DEPTH
        self.sites.add('seqIn', 'seqIn', seqX, emptyArgHeight - 2)
        self.sites.add('seqOut', 'seqOut', seqX, emptyArgHeight + 5)
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + width, y + height)

    def _size(self):
        topWidth, topHeight = self.topArgSize
        bottomWidth, bottomHeight = self.bottomArgSize
        width = max(topWidth, bottomWidth) + 3 + outSiteImage.width
        height = topHeight + bottomHeight + 3
        return width, height

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            self.drawList = []
            # Input sites
            topArgX = self.sites.topArg.xOffset
            topArgY = self.sites.topArg.yOffset - floatInImage.height // 2
            self.drawList.append(((topArgX, topArgY), floatInImage))
            bottomArgX = self.sites.bottomArg.xOffset
            bottomArgY = self.sites.bottomArg.yOffset - floatInImage.height // 2
            self.drawList.append(((bottomArgX, bottomArgY), floatInImage))
            # Body
            width, height = self._size()
            bodyLeft = outSiteImage.width - 1
            bodyRight = width - 1
            cntrY = 5
            bodyHeight = 11
            img = Image.new('RGBA', (width, bodyHeight), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle((bodyLeft, 0, bodyRight, bodyHeight-1),
             outline=OUTLINE_COLOR, fill=ICON_BG_COLOR)
            if needSeqSites:
                drawSeqSites(img, bodyLeft, 0, bodyHeight)
            if self.floorDiv:
                cntrX = (bodyLeft + bodyRight) // 2
                draw.line((bodyLeft + 2, cntrY, cntrX - 1, cntrY), fill=BLACK)
                draw.line((cntrX + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            else:
                draw.line((bodyLeft + 2, cntrY, bodyRight - 2, cntrY), fill=BLACK)
            bodyTop = self.sites.output.yOffset - 5
            if needOutSite:
                img.paste(outSiteImage, (0, cntrY - outSiteImage.height//2))
            self.drawList.append(((0, bodyTop), img))
        self._drawFromDrawList(toDragImage, location, clip, style)

    def doLayout(self, outSiteX, outSiteY, layout):
        self.topArgSize = layout.topArgSize
        self.bottomArgSize = layout.bottomArgSize
        self.sites.output.yOffset = layout.parentSiteOffset
        layout.updateSiteOffsets(self.sites.output)
        self.sites.seqIn.yOffset = layout.parentSiteOffset - 4
        self.sites.seqOut.yOffset = layout.parentSiteOffset + 4
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        width, height = self._size()
        x = outSiteX - self.sites.output.xOffset
        y = outSiteY - self.sites.output.yOffset
        self.rect = (x, y, x + width, y + height)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        topArg = self.sites.topArg.att
        tArgLayouts = [None] if topArg is None else topArg.calcLayouts()
        bottomArg = self.sites.bottomArg.att
        bArgLayouts = [None] if bottomArg is None else bottomArg.calcLayouts()
        attrIcon = self.sites.attrIcon.att
        attrLayouts = [None] if attrIcon is None else attrIcon.calcLayouts()
        layouts = []
        for tArgLayout, bArgLayout, attrLayout in allCombinations((tArgLayouts,
                bArgLayouts, attrLayouts)):
            if tArgLayout is None:
                tArgWidth, tArgHeight = self.emptyArgSize
                tArgSiteOffset = tArgHeight // 2
            else:
                tArgWidth = tArgLayout.width
                tArgHeight = tArgLayout.height
                tArgSiteOffset = tArgLayout.parentSiteOffset
            if bArgLayout is None:
                bArgWidth, bArgHeight = self.emptyArgSize
                bArgSiteOffset = bArgHeight // 2
            else:
                bArgWidth = bArgLayout.width
                bArgHeight = bArgLayout.height
                bArgSiteOffset = bArgLayout.parentSiteOffset
            width = max(tArgWidth, bArgWidth) + 4
            height = tArgHeight + bArgHeight + 3
            siteYOff = tArgHeight + 1
            layout = Layout(self, width, height, siteYOff)
            layout.topArgSize = tArgWidth, tArgHeight
            layout.bottomArgSize = bArgWidth, bArgHeight
            layout.addSubLayout(tArgLayout, 'topArg', (width - tArgWidth) // 2,
             - tArgHeight + tArgSiteOffset - 1)
            layout.addSubLayout(bArgLayout, 'bottomArg', (width - bArgWidth) // 2,
             + bArgSiteOffset + 2)
            layout.addSubLayout(attrLayout, 'attrIcon', width, ATTR_SITE_OFFSET)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        topArgText = _singleArgTextRepr(self.sites.topArg)
        bottomArgText = _singleArgTextRepr(self.sites.bottomArg)
        op = '//' if self.floorDiv else '/'
        text = topArgText + " " + op + " " + bottomArgText
        if needsParens(self, forText=True):
            return "(" + text + ")" + _attrTextRepr(self)
        return text

    def dumpName(self):
        return '//' if self.floorDiv else '/'

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, floorDiv=self.floorDiv)

    def leftAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return True

    def rightAssoc(self):
        """Note that this is only used for text generation for copy/paste"""
        return False

    def execute(self):
        if self.sites.topArg.att is None:
            raise IconExecException(self, "Missing numerator")
        if self.sites.bottomArg.att is None:
            raise IconExecException(self, "Missing denominator")
        topValue = self.sites.topArg.att.execute()
        bottomValue = self.sites.bottomArg.att.execute()
        try:
            if self.floorDiv:
                result = operator.floordiv(topValue, bottomValue)
            else:
                result = operator.truediv(topValue, bottomValue)
        except Exception as err:
            raise IconExecException(self, err)
        return result

    def createAst(self):
        if self.sites.topArg.att is None:
            raise IconExecException(self, "Missing numerator")
        if self.sites.bottomArg.att is None:
            raise IconExecException(self, "Missing denominator")
        left = self.sites.topArg.att.createAst()
        right = self.sites.bottomArg.att.createAst()
        op = ast.FloorDiv() if self.floorDiv else ast.Div()
        return ast.BinOp(lineno=self.id, col_offset=0, left=left, op=op, right=right)

class BlockEnd(Icon):
    def __init__(self, primary, window=None, location=None):
        Icon.__init__(self, window)
        self.primary = primary
        self.sites.add('seqIn', 'seqIn', 1 + BLOCK_INDENT, 1)
        self.sites.add('seqOut', 'seqOut', 1, 1)
        x, y = (0, 0)  if location is None else location
        self.rect = (x, y, x + branchFootImage.width, y + branchFootImage.height)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
        return [Layout(self, width, height, 1)]

    def inRectSelect(self, rect):
        return False

    def selectionRect(self):
        return None

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, primary=None)

class WhileIcon(Icon):
    def __init__(self, createBlockEnd=True, window=None, location=None):
        Icon.__init__(self, window)
        bodyWidth, bodyHeight = getTextSize("while", boldFont)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        bodyHeight = max(bodyHeight, minTxtIconHgt)
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + dragSeqImage.width-1, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            txtImg = iconBoxedText("while", boldFont, KEYWORD_COLOR)
            bodyOffset = dragSeqImage.width - 1
            bodyWidth, bodyHeight = txtImg.size
            img = Image.new('RGBA', (bodyOffset + max(BLOCK_INDENT + 3, bodyWidth),
             bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (dragSeqImage.width - 1, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            drawSeqSites(img, bodyOffset, 0, bodyHeight, indent="right",
             extendWidth=bodyWidth)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, cntrSiteY - dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def select(self, select=True):
        Icon.select(self, select)
        Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = Layout(self, width, height, height // 2)
            condXOff = width - 1
            layout.addSubLayout(condLayout, 'condIcon', condXOff, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "while " + _singleArgTextRepr(self.sites.condIcon) + ":"

    def dumpName(self):
        return "while"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        if self.sites.condIcon.att is None:
            raise IconExecException(self, "Missing condition in while statement")
        testAst = self.sites.condIcon.att.createAst()
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElse=True)
        return ast.While(testAst, bodyAsts, orElseAsts, lineno=self.id, col_offset=0)

class ForIcon(Icon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        Icon.__init__(self, window)
        self.isAsync = isAsync
        text = "async for" if isAsync else "for"
        bodyWidth = getTextSize(text, boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        inWidth = getTextSize("in", boldFont)[0] + 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight, inWidth)
        siteYOffset = bodyHeight // 2
        targetXOffset = bodyWidth + dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.tgtList = ListLayoutMgr(self, 'targets', targetXOffset, siteYOffset,
                simpleSpine=True)
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        iterX = dragSeqImage.width + bodyWidth-1 + self.tgtList.width-1 + inWidth-1
        self.iterList = ListLayoutMgr(self, 'iterIcons', iterX, siteYOffset,
                simpleSpine=True)
        totalWidth = iterX + self.iterList.width - 1
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.elseIcon = None
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight, inWidth = self.bodySize
            bodyOffset = dragSeqImage.width - 1
            img = Image.new('RGBA', (max(BLOCK_INDENT + 3, bodyWidth) + bodyOffset,
             bodyHeight), color=(0, 0, 0, 0))
            txt = "async for" if self.isAsync else "for"
            txtImg = iconBoxedText(txt, boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            cntrSiteY = self.sites.seqInsert.yOffset
            inImgX = bodyOffset + bodyWidth - 1 - inSiteImage.width
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (inImgX, inImageY))
            drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, cntrSiteY - dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            # Target list commas and possible list simple-spines
            tgtListOffset = bodyWidth + bodyOffset - 1 - OUTPUT_SITE_DEPTH
            self.drawList += self.tgtList.drawListCommas(tgtListOffset, cntrSiteY)
            self.drawList += self.tgtList.drawSimpleSpine(tgtListOffset, cntrSiteY)
            # "in"
            txtImg = iconBoxedText("in", boldFont, KEYWORD_COLOR)
            img = Image.new('RGBA', (txtImg.width, bodyHeight), color=(0, 0, 0, 0))
            img.paste(txtImg, (0, 0))
            inImgX = txtImg.width - inSiteImage.width
            img.paste(inSiteImage, (inImgX, inImageY))
            inOffset = bodyOffset + bodyWidth - 1 + self.tgtList.width - 1
            self.drawList.append(((inOffset, self.sites.seqIn.yOffset - 1), img))
            # Commas and possible list simple-spines
            iterOffset = inOffset + inWidth - 1 - OUTPUT_SITE_DEPTH
            self.drawList += self.iterList.drawListCommas(iterOffset, cntrSiteY)
            self.drawList += self.iterList.drawSimpleSpine(iterOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def addElse(self, ic):
        self.elseIcon = ic
        ic.parentIf = self

    def removeElse(self, ic):
        self.elseIcon = None
        ic.parentIf = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.tgtList.makeInsertSnapList() + \
         self.iterList.makeInsertSnapList()
        return siteSnapLists

    def select(self, select=True):
        Icon.select(self, select)
        Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        self.tgtList.doLayout(layout)
        self.iterList.doLayout(layout)
        bodyWidth, bodyHeight, inWidth = self.bodySize
        width = dragSeqImage.width-1 + bodyWidth-1 + self.tgtList.width-1 + inWidth-1 + \
                self.iterList.width
        heightAbove = max(bodyHeight // 2, self.tgtList.spineTop, self.iterList.spineTop)
        heightBelow = max(bodyHeight - bodyHeight // 2, self.tgtList.spineHeight -
                self.tgtList.spineTop, self.iterList.spineHeight - self.iterList.spineTop)
        height = heightAbove + heightBelow
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = heightAbove + bodyHeight // 2 - 1
        self.sites.seqInsert.yOffset = heightAbove
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight, inWidth = self.bodySize
        tgtListLayouts = self.tgtList.calcLayouts()
        iterListLayouts = self.iterList.calcLayouts()
        layouts = []
        for tgtListLayout, iterListLayout in allCombinations((tgtListLayouts,
                iterListLayouts)):
            layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            tgtXOff = bodyWidth - 1
            tgtListLayout.mergeInto(layout, tgtXOff, 0)
            iterXOff = bodyWidth - 1 + tgtListLayout.width - 1 + inWidth - 1
            iterListLayout.mergeInto(layout, iterXOff, 0)
            layout.width = iterXOff + iterListLayout.width + defRParenImage.width - 2
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        text = "async for" if self.isAsync else "for"
        tgtText = _seriesTextRepr(self.sites.targets)
        iterText = _seriesTextRepr(self.sites.iterIcons)
        return text + " " + tgtText + " in " + iterText + ":"

    def dumpName(self):
        return "for"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync,
         createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        # Get the target and iteration icons
        tgts = []
        for site in self.sites.targets:
            if site.att is None:
                raise IconExecException(self, "Missing assignment target(s)")
            tgts.append(site.att)
        if len(tgts) == 1:
            tgtAst = tgts[0].createAst()
        else:
            perTgtAsts = [tgt.createAst() for tgt in tgts]
            tgtAst = ast.Tuple(perTgtAsts, ctx=ast.Store(), lineno=self.id,
             col_offset=0)
        iterValues = []
        for site in self.sites.iterIcons:
            if site.att is None:
                raise IconExecException(self, "Missing iteration value")
            iterValues.append(site.att)
        # Make asts for targets and values, adding tuples if packing/unpacking is
        # specified
        if len(iterValues) == 1:
            valueAst = iterValues[0].createAst()
        else:
            valueAst = ast.Tuple([v.createAst() for v in iterValues], ctx=ast.Load(),
             lineno=self.id, col_offset=0)
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElse=True)
        return ast.For(tgtAst, valueAst, bodyAsts, orElseAsts, lineno=self.id,
         col_offset=0)

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + dragSeqImage.width - 1
        bodyWidth, bodyHeight, inWidth = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return python_g.rectsTouch(rect, bodyRect)

class IfIcon(Icon):
    def __init__(self, createBlockEnd=True, window=None, location=None):
        Icon.__init__(self, window)
        bodyWidth, bodyHeight = getTextSize("if", boldFont)
        bodyHeight = max(minTxtHgt, bodyHeight)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        width = max(seqX + BLOCK_INDENT + 1, bodyWidth + dragSeqImage.width-1)
        self.rect = (x, y, x + width, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)
        self.elifIcons = []
        self.elseIcon = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            boxLeft = dragSeqImage.width - 1
            txtImg = iconBoxedText("if", boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            drawSeqSites(img, boxLeft, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, cntrSiteY - dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def select(self, select=True, includeElses=False):
        Icon.select(self, select)
        Icon.select(self.blockEnd, select)
        if includeElses:
            if self.elseIcon is not None:
                Icon.select(self.elseIcon, select)
            for elifIc in self.elifIcons:
                Icon.select(elifIc, select)

    def addElse(self, ic):
        if isinstance(ic, ElifIcon):
            self.elifIcons.append(self)
        else:
            self.elseIcon = ic
        ic.parentIf = self

    def removeElse(self, ic):
        if isinstance(ic, ElifIcon):
            self.elifIcons.remove(self)
        else:
            self.elseIcon = None
        ic.parentIf = None

    def doLayout(self, left, top, layout):
        layout.updateSiteOffsets(self.sites.seqInsert)
        width, height = self.bodySize
        width = max(BLOCK_INDENT + 3, width) + dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = Layout(self, width, height, height // 2)
            layout.addSubLayout(condLayout, 'condIcon', width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "if " + _singleArgTextRepr(self.sites.condIcon) + ":"

    def dumpName(self):
        return "if"

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def execute(self):
        return None  #... no idea what to do here, yet.

    def createAst(self):
        if self.sites.condIcon.att is None:
            raise IconExecException(self, "Missing condition in if statement")
        testAst = self.sites.condIcon.att.createAst()
        bodyAsts, orElseAsts = createBlockAsts(self, allowsElifElse=True)
        return ast.If(testAst, bodyAsts, orElseAsts, lineno=self.id, col_offset=0)

class ElifIcon(Icon):
    def __init__(self, window, location=None):
        Icon.__init__(self, window)
        bodyWidth, bodyHeight = getTextSize("elif ", boldFont)
        bodyHeight = max(minTxtHgt, bodyHeight)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        condXOffset = bodyWidth + dragSeqImage.width - 1 - OUTPUT_SITE_DEPTH
        self.sites.add('condIcon', 'input', condXOffset, siteYOffset)
        seqX = dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + dragSeqImage.width - 1, y + bodyHeight)
        self.parentIf = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
            rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText("elif ", boldFont, KEYWORD_COLOR)
            boxLeft = dragSeqImage.width - 1
            img.paste(txtImg, (boxLeft, 0))
            cntrSiteY = self.sites.condIcon.yOffset
            inImageY = cntrSiteY - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.condIcon.xOffset, inImageY))
            seqSiteX = self.sites.seqIn.xOffset-1
            img.paste(seqSiteImage, (seqSiteX, self.sites.seqIn.yOffset-1))
            img.paste(seqSiteImage, (seqSiteX, self.sites.seqOut.yOffset-1))
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, cntrSiteY - dragSeqImage.height // 2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + height // 2)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        condIcon = self.sites.condIcon.att
        condLayouts = [None] if condIcon is None else condIcon.calcLayouts()
        layouts = []
        for condLayout in condLayouts:
            layout = Layout(self, width, height, height // 2)
            layout.addSubLayout(condLayout, 'condIcon', width - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "elif " + _singleArgTextRepr(self.sites.condIcon) + ":"

    def dumpName(self):
        return "elif"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class ElseIcon(Icon):
    def __init__(self, window, location=None):
        Icon.__init__(self, window)
        bodyWidth, bodyHeight = getTextSize("else", boldFont)
        bodyHeight = max(minTxtHgt, bodyHeight)
        bodyWidth += 2 * TEXT_MARGIN + 1
        bodyHeight += 2 * TEXT_MARGIN + 1
        self.bodySize = (bodyWidth, bodyHeight)
        seqX = dragSeqImage.width + ELSE_DEDENT
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight - 2)
        self.sites.add('seqInsert', 'seqInsert', 0, bodyHeight // 2)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + bodyWidth + dragSeqImage.width - 1, y + bodyHeight)
        self.parentIf = None

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
            rectHeight(self.rect)), color=(0, 0, 0, 0))
            txtImg = iconBoxedText("else", boldFont, KEYWORD_COLOR)
            boxLeft = dragSeqImage.width - 1
            img.paste(txtImg, (boxLeft, 0))
            seqSiteX = self.sites.seqIn.xOffset-1
            img.paste(seqSiteImage, (seqSiteX, self.sites.seqIn.yOffset-1))
            img.paste(seqSiteImage, (seqSiteX, self.sites.seqOut.yOffset-1))
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, txtImg.height//2 - dragSeqImage.height//2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        width, height = self.bodySize
        width += dragSeqImage.width - 1
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        self.layoutDirty = False

    def calcLayouts(self):
        width, height = self.bodySize
        layout = Layout(self, width, height, height // 2)
        return [layout]

    def textRepr(self):
        return "else:"

    def dumpName(self):
        return "else"

    def execute(self):
        return None  # ... no idea what to do here, yet.

class DefOrClassIcon(Icon):
    def __init__(self, text, hasArgs, createBlockEnd=True, window=None, location=None):
        Icon.__init__(self, window)
        self.text = text
        bodyWidth = getTextSize(self.text, boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        nameXOffset = bodyWidth + dragSeqImage.width-1 - OUTPUT_SITE_DEPTH
        self.sites.add('nameIcon', 'input', nameXOffset, siteYOffset)
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX + BLOCK_INDENT, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        if hasArgs:
            lParenWidth = defLParenImage.width
            self.nameWidth = EMPTY_ARG_WIDTH
            argX = dragSeqImage.width + bodyWidth + self.nameWidth + lParenWidth
            self.argList = ListLayoutMgr(self, 'argIcons', argX, siteYOffset)
            rParenWidth = defRParenImage.width
            totalWidth = argX + self.argList.width + rParenWidth - 3
        else:
            totalWidth = max(bodyWidth, BLOCK_INDENT+2) + dragSeqImage.width
            self.argList = None
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = BlockEnd(self, window, (x, y + bodyHeight + 2))
            self.sites.seqOut.attach(self, self.blockEnd)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        if toDragImage is None:
            temporaryDragSite = False
        else:
            # When image is specified the icon is being dragged, and it must display
            # its sequence-insert snap site unless it is in a sequence and not the start.
            self.drawList = None
            temporaryDragSite = self.prevInSeq() is None
        if self.drawList is None:
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = dragSeqImage.width - 1
            img = Image.new('RGBA', (max(bodyWidth, BLOCK_INDENT+3) + bodyOffset,
             bodyHeight), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.text, boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (self.sites.nameIcon.xOffset, inImageY))
            drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
             extendWidth=txtImg.width)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, bodyHeight // 2 - dragSeqImage.height // 2))
            self.drawList = [((0, self.sites.seqIn.yOffset - 1), img)]
            if self.argList is not None:
                # Open Paren
                lParenOffset = bodyOffset + bodyWidth - 1 + self.nameWidth - 1
                lParenImg = yStretchImage(defLParenImage, defLParenExtendDupRows,
                    self.argList.spineHeight)
                # Open paren body sites
                self.argList.drawBodySites(lParenImg)
                self.drawList.append(((lParenOffset, 0), lParenImg))
                # Commas
                argsOffset = lParenOffset + defLParenImage.width - 1
                self.drawList += self.argList.drawListCommas(
                        argsOffset - OUTPUT_SITE_DEPTH, self.argList.spineTop)
                # End Paren
                rParenOffset = argsOffset + self.argList.width - 1
                rParenImg = yStretchImage(defRParenImage, defRParenExtendDupRows,
                        self.argList.spineHeight)
                self.drawList.append(((rParenOffset, 0), rParenImg))
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def argIcons(self):
        if self.argList is None:
            return []
        return [site.att for site in self.sites.argIcons]

    def snapLists(self, forCursor=False):
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        if forCursor or not self.argList is not None:
            return siteSnapLists
        # Add snap sites for insertion to those representing actual attachment sites
        siteSnapLists['insertInput'] = self.argList.makeInsertSnapList()
        # Add back versions of sites that were filtered out for having more local
        # snap targets (such as left arg of BinOpIcon).  The ones added back are highly
        # conditional on the icons that have to be connected directly to the call icon
        # argument list (*, **, =).
        _restoreConditionalTargets(self, siteSnapLists,
         (StarIcon, StarStarIcon, ArgAssignIcon))
        return siteSnapLists

    def select(self, select=True):
        Icon.select(self, select)
        Icon.select(self.blockEnd, select)

    def doLayout(self, left, top, layout):
        self.nameWidth = layout.nameWidth
        bodyWidth, bodyHeight = self.bodySize
        width = dragSeqImage.width - 1 + bodyWidth - 1 + self.nameWidth
        if self.argList is None:
            height = bodyHeight
            centerY = bodyHeight // 2 + 1
        else:
            self.argList.doLayout(layout)
            width += defLParenImage.width - 1 + self.argList.width - 1 + \
                    defRParenImage.width
            height = self.argList.spineHeight
            centerY = self.argList.spineTop
        self.sites.seqInsert.yOffset = centerY
        seqInY = centerY - bodyHeight // 2 + 1
        self.sites.seqIn.yOffset = seqInY
        self.sites.seqOut.yOffset = seqInY + bodyHeight - 2
        self.rect = (left, top, left + width, top + height)
        layout.updateSiteOffsets(self.sites.seqInsert)
        # ... The parent site offsets need to be adjusted one pixel left and up, here, for
        #     the child icons to draw in the right place, but I have no idea why.
        layout.doSubLayouts(self.sites.seqInsert, 0, top + centerY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        argListLayouts = [None] if self.argList is None else self.argList.calcLayouts()
        nameIcon = self.sites.nameIcon.att
        nameLayouts = [None] if nameIcon is None else nameIcon.calcLayouts()
        nameXOff = bodyWidth - 1
        cntrYOff = bodyHeight // 2
        layouts = []
        for nameLayout, argListLayout in allCombinations((nameLayouts, argListLayouts)):
            layout = Layout(self, bodyWidth, bodyHeight, cntrYOff)
            layout.addSubLayout(nameLayout, 'nameIcon', nameXOff, 0)
            nameWidth = EMPTY_ARG_WIDTH if nameLayout is None else nameLayout.width
            layout.nameWidth = nameWidth
            if argListLayout is not None:
                argXOff = bodyWidth - 1 + nameWidth - 1 + lParenImage.width
                argListLayout.mergeInto(layout, argXOff - OUTPUT_SITE_DEPTH, 0)
                layout.width = argXOff + argListLayout.width + defRParenImage.width - 2
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        nameIcon = self.sites.nameIcon.att
        text = self.text + " " + ("" if nameIcon is None else nameIcon.textRepr())
        if self.argList is None:
            return text
        return text + "(" + _seriesTextRepr(self.sites.argIcons) + "):"

    def dumpName(self):
        return self.text

    def inRectSelect(self, rect):
        # Require selection rectangle to touch icon body
        if not Icon.inRectSelect(self, rect):
            return False
        icLeft, icTop = self.rect[:2]
        bodyLeft = icLeft + dragSeqImage.width - 1
        bodyWidth, bodyHeight = self.bodySize
        bodyRect = (bodyLeft, icTop, bodyLeft + bodyWidth, icTop + bodyHeight)
        return python_g.rectsTouch(rect, bodyRect)

    def addArgs(self):
        if self.argList is not None:
            return
        argX = rectWidth(self.rect)
        argY = self.sites.nameIcon.yOffset
        self.argList = ListLayoutMgr(self, 'argIcons', argX, argY)
        self.window.undo.registerCallback(self.removeArgs)

    def removeArgs(self):
        if self.argList is None:
            return
        if len(self.argIcons()) > 0:
            print("trying to remove non-empty argument list")
            return
        self.argList = None
        self.window.undo.registerCallback(self.addArgs)

class ClassDefIcon(DefOrClassIcon):
    def __init__(self, hasArgs=False, createBlockEnd=True, window=None, location=None):
        DefOrClassIcon.__init__(self, "class", hasArgs, createBlockEnd, window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, hasArgs=self.argList is not None,
         createBlockEnd=False)

    def createAst(self):
        nameIcon = self.sites.nameIcon.att
        if nameIcon is None:
            raise IconExecException(self, "Definition missing function name")
        if not isinstance(nameIcon, IdentifierIcon):
            raise IconExecException(nameIcon, "Argument name must be identifier")
        bases = []
        kwds = []
        if self.argList is not None:
            for site in self.sites.argIcons:
                base = site.att
                if base is None:
                    if site.name == 'argIcons_0':
                        continue  # 1st site can be empty, meaning parens but no bases
                    raise IconExecException(self, "Missing argument(s)")
                if isinstance(base, ArgAssignIcon):
                    keyIcon = base.sites.leftArg.att
                    valueIcon = base.sites.rightArg.att
                    if keyIcon is None:
                        raise IconExecException(base, "Missing keyword name")
                    if not isinstance(keyIcon, IdentifierIcon):
                        raise IconExecException(keyIcon, "Keyword must be identifier")
                    kwds.append(ast.keyword(keyIcon.name, valueIcon.createAst(),
                     lineno=base.id, col_offset=0))
                else:
                    bases.append(base.createAst())
        bodyAsts = createBlockAsts(self)
        return ast.ClassDef(nameIcon.name, bases, keywords=kwds, body=bodyAsts,
         decorator_list=[], lineno=self.id, col_offset=0)

class DefIcon(DefOrClassIcon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        self.isAsync = isAsync
        text = "async def" if isAsync else "def"
        DefOrClassIcon.__init__(self, text, True, createBlockEnd, window, location)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, isAsync=self.isAsync,
         createBlockEnd=False)

    def createAst(self):
        nameIcon = self.sites.nameIcon.att
        if nameIcon is None:
            raise IconExecException(self, "Definition missing function name")
        if not isinstance(nameIcon, IdentifierIcon):
            raise IconExecException(nameIcon, "Argument name must be identifier")
        posOnlyArgAsts = []
        normalArgAsts = []
        kwdOnlyAsts = []
        normalArgDefaults = []
        kwOnlyDefaults = []
        accumArgAsts = normalArgAsts
        accumArgDefaults = normalArgDefaults
        starArgAst = None
        starStarArgAst = None
        for site in self.sites.argIcons:
            arg = site.att
            if arg is None:
                if site.name == 'argIcons_0':
                    continue  # 1st site can be empty, meaning "no arguments"
                raise IconExecException(self, "Missing argument(s)")
            if isinstance(arg, ArgAssignIcon):
                argIcon = arg.sites.leftArg.att
                defaultIcon = arg.sites.rightArg.att
                if argIcon is None:
                    raise IconExecException(arg, "Missing argument name")
                if not isinstance(argIcon, IdentifierIcon):
                    raise IconExecException(arg, "Argument name must be identifier")
                if defaultIcon is None:
                    raise IconExecException(arg, "Missing default value")
                accumArgAsts.append(ast.arg(argIcon.name, lineno=arg.id, col_offset=0))
                accumArgDefaults.append(defaultIcon.createAst())
            elif isinstance(arg, StarStarIcon):
                starStarArg = arg.sites.argIcon.att
                if starStarArg is None:
                    raise IconExecException(arg, "Missing value for **")
                if not isinstance(starStarArg, IdentifierIcon):
                    raise IconExecException(starStarArg, "Argument must be identifier")
                starStarArgAst = ast.arg(starStarArg.name, lineno=arg.id, col_offset=0)
            elif isinstance(arg, StarIcon):
                # A star icon with an argument is a vararg list.  Without, it is a
                # keyword-only marker.  Either way, subsequent arguments are keyword-only
                # and should go in the kwdOnly lists
                starArg = arg.sites.argIcon.att
                if starArg is not None:
                    if not isinstance(starArg, IdentifierIcon):
                        raise IconExecException(starArg, "Argument must be identifier")
                    starArgAst = ast.arg(starArg.name, lineno=arg.id, col_offset=0)
                accumArgAsts = kwdOnlyAsts
                accumArgDefaults = kwOnlyDefaults
            elif isinstance(arg, PosOnlyMarkerIcon):
                posOnlyArgAsts = normalArgAsts
                normalArgAsts = []
                accumArgAsts = normalArgAsts
            else:
                if not isinstance(arg, IdentifierIcon):
                    raise IconExecException(arg, "Argument name must be identifier")
                accumArgAsts.append(ast.arg(arg.name, lineno=arg.id, col_offset=0))
        argumentAsts = ast.arguments(posOnlyArgAsts, normalArgAsts, starArgAst,
         kwdOnlyAsts, kwOnlyDefaults, starStarArgAst, normalArgDefaults)
        bodyAsts = createBlockAsts(self)
        if self.isAsync:
            return ast.AsyncFunctionDef(nameIcon.name, argumentAsts, bodyAsts,
             decorator_list=[], returns=None, lineno=self.id, col_offset=0)
        return ast.FunctionDef(nameIcon.name, argumentAsts, bodyAsts,
         decorator_list=[], returns=None, lineno=self.id, col_offset=0)

class NoArgStmtIcon(Icon):
    def __init__(self, stmt, window, location):
        Icon.__init__(self, window)
        self.stmt = stmt
        bodyWidth = getTextSize(stmt, boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = minTxtIconHgt
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = dragSeqImage.width + bodyWidth
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
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = dragSeqImage.width - 1
            txtImg = iconBoxedText(self.stmt, boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            drawSeqSites(img, bodyOffset, 0, txtImg.height)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, bodyHeight//2 - dragSeqImage.height//2))
            self.drawList = [((0, 0), img)]
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def doLayout(self, left, top, layout):
        bodyWidth, bodyHeight = self.bodySize
        width = dragSeqImage.width - 1 + bodyWidth
        self.rect = (left, top, left + width, top + bodyHeight)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        return [Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)]

    def textRepr(self):
        return self.stmt

    def dumpName(self):
        return self.stmt

    def execute(self):
        return None  #... no idea what to do here, yet.

class PassIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "pass", window, location)

    def createAst(self):
        return ast.Pass(lineno=self.id, col_offset=0)

class ContinueIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "continue", window, location)

    def createAst(self):
        return ast.Continue(lineno=self.id, col_offset=0)

class BreakIcon(NoArgStmtIcon):
    def __init__(self, window, location=None):
        NoArgStmtIcon.__init__(self, "break", window, location)

    def createAst(self):
        return ast.Break(lineno=self.id, col_offset=0)

class SeriesStmtIcon(Icon):
    def __init__(self, stmt, window, seqIndent=False, location=None):
        Icon.__init__(self, window)
        self.stmt = stmt
        self.drawIndent = seqIndent
        bodyWidth = getTextSize(stmt, boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        seqX = dragSeqImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        seqOutIndent = BLOCK_INDENT if seqIndent else 0
        self.sites.add('seqOut', 'seqOut', seqX + seqOutIndent, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = dragSeqImage.width + bodyWidth
        self.valueList = ListLayoutMgr(self, 'values', bodyWidth+1, siteYOffset,
                simpleSpine=True)
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
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = dragSeqImage.width - 1
            img = Image.new('RGBA', (bodyOffset + max(bodyWidth, BLOCK_INDENT+2),
             bodyHeight), color=(0, 0, 0, 0))
            txtImg = iconBoxedText(self.stmt, boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImgX = bodyOffset + bodyWidth - inSiteImage.width
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (inImgX, inImageY))
            if self.drawIndent:
                drawSeqSites(img, bodyOffset, 0, txtImg.height, indent="right",
                 extendWidth=txtImg.width)
            else:
                drawSeqSites(img, bodyOffset, 0, txtImg.height)
            if temporaryDragSite:
                img.paste(dragSeqImage, (0, bodyHeight // 2 - dragSeqImage.height // 2))
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valueList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valueList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)
        if temporaryDragSite:
            self.drawList = None

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valueList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, left, top, layout):
        self.valueList.doLayout(layout)
        bodyWidth, bodyHeight = self.bodySize
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        width = dragSeqImage.width - 1 + bodyWidth + self.valueList.width + 2
        if self.valueList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.valueList.spineTop)
            heightBelow = max(heightBelow, self.valueList.spineHeight -
                    self.valueList.spineTop)
        self.sites.seqInsert.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        height = heightAbove + heightBelow
        self.rect = left, top, left + width, top + height
        layout.updateSiteOffsets(self.sites.seqInsert)
        layout.doSubLayouts(self.sites.seqInsert, 0, top + heightAbove)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        valueListLayouts = self.valueList.calcLayouts()
        layouts = []
        for valueListLayout in valueListLayouts:
            layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            valueListLayout.mergeInto(layout, bodyWidth - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return self.stmt + " " + _seriesTextRepr(self.sites.values)

    def dumpName(self):
        return self.stmt

    def execute(self):
        return None  #... no idea what to do here, yet.

class ReturnIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "return", window, location=location)

    def createAst(self):
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            valueAst = None
        else:
            for site in self.sites.values:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            valueAsts = [site.att.createAst() for site in self.sites.values]
            if len(valueAsts) == 1:
                valueAst = valueAsts[0]
            else:
                valueAst = ast.Tuple(valueAsts, ctx=ast.Load(), lineno=self.id,
                 col_offset=0)
        return ast.Return(value=valueAst, lineno=self.id, col_offset=0)

class DelIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "del", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
        targetAsts = [site.att.createAst() for site in self.sites.values]
        return ast.Delete(targetAsts, lineno=self.id, col_offset=0)

class WithIcon(SeriesStmtIcon):
    def __init__(self, isAsync=False, createBlockEnd=True, window=None, location=None):
        stmt = "async with" if isAsync else "with"
        SeriesStmtIcon.__init__(self, stmt, window, seqIndent=True, location=location)
        self.blockEnd = None
        if createBlockEnd:
            self.blockEnd = BlockEnd(self, window)
            self.sites.seqOut.attach(self, self.blockEnd)

    def select(self, select=True):
        Icon.select(self, select)
        Icon.select(self.blockEnd, select)

    def clipboardRepr(self, offset, iconsToCopy):
        return self._serialize(offset, iconsToCopy, createBlockEnd=False)

    def createAst(self):
        withItems = []
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
            if isinstance(site.att, WithAsIcon):
                leftArg = site.att.leftArg()
                rightArg = site.att.rightArg()
                if leftArg is None:
                    raise IconExecException(site.att, "Missing argument")
                if rightArg is None:
                    raise IconExecException(site.att, 'Missing name(s) for "as"')
                withItems.append(ast.withitem(leftArg.createAst(), rightArg.createAst()))
            else:
                withItems.append(ast.withitem(site.att.createAst(), None))
        bodyAsts = createBlockAsts(self)
        return ast.With(withItems, body=bodyAsts, lineno=self.id, col_offset=0)

class GlobalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "global", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise IconExecException(site.att, "Argument be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Global(names, lineno=self.id, col_offset=0)

class NonlocalIcon(SeriesStmtIcon):
    def __init__(self, window=None, location=None):
        SeriesStmtIcon.__init__(self, "nonlocal", window, location=location)

    def createAst(self):
        for site in self.sites.values:
            if site.att is None:
                raise IconExecException(self, "Missing argument(s)")
            if not isinstance(site.att, IdentifierIcon):
                raise IconExecException(site.att, "Argument be identifier")
        names = [site.att.name for site in self.sites.values]
        return ast.Nonlocal(names, lineno=self.id, col_offset=0)

class YieldIcon(Icon):
    def __init__(self, window=None, location=None):
        Icon.__init__(self, window)
        bodyWidth = getTextSize("yield", boldFont)[0] + 2 * TEXT_MARGIN + 1
        bodyHeight = defLParenImage.height
        self.bodySize = (bodyWidth, bodyHeight)
        siteYOffset = bodyHeight // 2
        self.sites.add('output', 'output', 0, siteYOffset)
        seqX = outSiteImage.width
        self.sites.add('seqIn', 'seqIn', seqX, 1)
        self.sites.add('seqOut', 'seqOut', seqX, bodyHeight-2)
        self.sites.add('seqInsert', 'seqInsert', 0, siteYOffset)
        totalWidth = outSiteImage.width - 1 + bodyWidth
        self.valueList = ListLayoutMgr(self, 'values', bodyWidth-1, siteYOffset,
                simpleSpine=True)
        x, y = (0, 0) if location is None else location
        self.rect = (x, y, x + totalWidth, y + bodyHeight)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
        needSeqSites = self.parent() is None and toDragImage is None
        needOutSite = self.parent() is not None or self.sites.seqIn.att is None and (
         self.sites.seqOut.att is None or toDragImage is not None)
        if self.drawList is None:
            img = Image.new('RGBA', (rectWidth(self.rect),
             rectHeight(self.rect)), color=(0, 0, 0, 0))
            bodyWidth, bodyHeight = self.bodySize
            bodyOffset = outSiteImage.width - 1
            txtImg = iconBoxedText("yield", boldFont, KEYWORD_COLOR)
            img.paste(txtImg, (bodyOffset, 0))
            inImgX = bodyOffset + bodyWidth - inSiteImage.width
            inImageY = bodyHeight // 2 - inSiteImage.height // 2
            img.paste(inSiteImage, (inImgX, inImageY))
            if needSeqSites:
                drawSeqSites(img, bodyOffset, 0, txtImg.height)
            if needOutSite:
                outImageY = bodyHeight // 2 - outSiteImage.height // 2
                img.paste(outSiteImage, (0, outImageY), mask=outSiteImage)
            bodyTopY = self.sites.seqIn.yOffset - 1
            self.drawList = [((0, bodyTopY), img)]
            # Minimal spines (if list has multi-row layout)
            argsOffset = bodyOffset + bodyWidth - 1 - OUTPUT_SITE_DEPTH
            cntrSiteY = bodyTopY + bodyHeight // 2
            self.drawList += self.valueList.drawSimpleSpine(argsOffset, cntrSiteY)
            # Commas
            self.drawList += self.valueList.drawListCommas(argsOffset, cntrSiteY)
        self._drawFromDrawList(toDragImage, location, clip, style)

    def snapLists(self, forCursor=False):
        # Add snap sites for insertion
        siteSnapLists = Icon.snapLists(self, forCursor=forCursor)
        siteSnapLists['insertInput'] = self.valueList.makeInsertSnapList()
        return siteSnapLists

    def doLayout(self, outSiteX, outSiteY, layout):
        self.valueList.doLayout(layout)
        bodyWidth, bodyHeight = self.bodySize
        width = outSiteImage.width - 1 + bodyWidth + self.valueList.width
        heightAbove = bodyHeight // 2
        heightBelow = bodyHeight - heightAbove
        if self.valueList.simpleSpineWillDraw():
            heightAbove = max(heightAbove, self.valueList.spineTop)
            heightBelow = max(heightBelow, self.valueList.spineHeight -
                    self.valueList.spineTop)
        self.sites.output.yOffset = heightAbove
        self.sites.seqInsert.yOffset = heightAbove
        self.sites.seqIn.yOffset = heightAbove - bodyHeight // 2 + 1
        self.sites.seqOut.yOffset = self.sites.seqIn.yOffset + bodyHeight - 2
        left = outSiteX - self.sites.output.xOffset
        top = outSiteY - self.sites.output.yOffset
        self.rect = (left, top, left + width, top + heightAbove + heightBelow)
        layout.updateSiteOffsets(self.sites.output)
        layout.doSubLayouts(self.sites.output, outSiteX, outSiteY)
        self.drawList = None
        self.layoutDirty = False

    def calcLayouts(self):
        bodyWidth, bodyHeight = self.bodySize
        layouts = []
        for valueListLayout in self.valueList.calcLayouts():
            layout = Layout(self, bodyWidth, bodyHeight, bodyHeight // 2)
            valueListLayout.mergeInto(layout, bodyWidth - 1, 0)
            layouts.append(layout)
        return self.debugLayoutFilter(layouts)

    def textRepr(self):
        return "yield " + _seriesTextRepr(self.sites.values)

    def dumpName(self):
        return "yield"

    def createAst(self):
        if len(self.sites.values) == 1 and self.sites.values[0].att is None:
            valueAst = None
        else:
            for site in self.sites.values:
                if site.att is None:
                    raise IconExecException(self, "Missing argument(s)")
            valueAsts = [site.att.createAst() for site in self.sites.values]
            if len(valueAsts) == 1:
                valueAst = valueAsts[0]
            else:
                valueAst = ast.Tuple(valueAsts, ctx=ast.Load(), lineno=self.id,
                 col_offset=0)
        return ast.Yield(value=valueAst, lineno=self.id, col_offset=0)

class ImageIcon(Icon):
    def __init__(self, image, window, location=None):
        Icon.__init__(self, window)
        self.image = image.convert('RGBA')
        if location is None:
            x, y = 0, 0
        else:
            x, y = location
        self.rect = (x, y, x + image.width, y + image.height)

    def draw(self, toDragImage=None, location=None, clip=None, style=None):
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
        return [Layout(self, self.image.width, self.image.height, 0)]

    def execute(self):
        return None

    def dumpName(self):
        return "image"

# Unfinished
class ToDoIcon(TextIcon):
    def __init__(self, window=None, location=None):
        name = self.__class__.__name__
        TextIcon.__init__(self, 'ToDo: ' + name + 'Not implemented', window, location)

class ExceptIcon(ToDoIcon):
    pass

class FinallyIcon(ToDoIcon):
    pass

class FromIcon(ToDoIcon):
    pass

class ImportIcon(ToDoIcon):
    pass

class RaiseIcon(ToDoIcon):
    pass

class TryIcon(ToDoIcon):
    pass

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

    def updateSiteOffsets(self, parentSite):
        """Icon site positions are relative to the icon rectangle.  Set them from the
        layout site positions, which are relative to the implied site of the layout
        (on the left edge of the layout rectangle, parentSiteOffset from the top, and
        idealized to zero site depth).  The parentSite argument should provide the site
        object (which has presumably already been positioned relative to the icon
        rectangle)."""
        parentSiteDepth = siteDepths[parentSite.type]
        for name, layout in self.subLayouts.items():
            site = self.icon.sites.lookup(name)
            siteDepth = siteDepths[site.type]
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

def tintSelectedImage(image, selected, style):
    if style == "outline":
        alphaImg = image.getchannel('A')
        outlineMask = ImageMath.eval("convert(a*255, 'L')", a=alphaImg)
        outlineImg = Image.new('RGBA', (image.width, image.height), color=SHOW_OUTLINE_TINT)
        outlineImg.putalpha(outlineMask)
        outlineImg.paste(image, mask=image)
        return outlineImg
    elif style == "error":
        color = ERR_TINT
    elif selected:
        color = SELECT_TINT
    else:  # No outline and no additional coloring
        return image
    alphaImg = image.getchannel('A')
    colorImg = Image.new('RGBA', (image.width, image.height), color=color)
    colorImg.putalpha(alphaImg)
    selImg = Image.blend(image, colorImg, .15)
    return selImg

def needsParens(ic, parent=None, forText=False, parentSite=None):
    """Returns True if the BinOpIcon, ic, should have parenthesis.  Specify "parent" to
    compute for a parent which is not the actual icon parent.  If forText is True, ic
    can also be a DivideIcon, and the calculation is appropriate to text rather than
    icons, where division is just another binary operator and not laid out numerator /
    denominator."""
    if ic.childAt('attrIcon'):
        return True  # BinOps can have attributes, and need parens to support the site
    if parent is None:
        parent = ic.parent()
    if parent is None:
        return False
    # Unclosed cursor-parens count as a left-paren, but not a right-paren
    if parent.__class__.__name__ == "CursorParenIcon" and not parent.closed:
        parenParent = parent.parent()
        if parenParent is None or parenParent.__class__ is not BinOpIcon or \
         parenParent.siteOf(parent) != "leftArg":
            return False
        parent = parenParent
    arithmeticOpClasses = (BinOpIcon, UnaryOpIcon)
    if forText:
        arithmeticOpClasses += (DivideIcon,)
    if parent.__class__ not in arithmeticOpClasses:
        return False
    if ic.precedence > parent.precedence:
        return False
    if ic.precedence < parent.precedence:
        return True
    # Precedence is equal to parent.  Look at associativity
    if parentSite is None:
        parentSite = parent.siteOf(ic, recursive=True)
    if parentSite == "leftArg" and ic.rightAssoc():
        return True
    if parentSite == "rightArg" and ic.leftAssoc():
        return True
    return False

def findLeftOuterIcon(clickedIcon, btnPressLoc, fromIcon=None):
    """Because we have icons with no pickable structure left of their arguments (binary
    operations), we have to make rules about what it means to click or drag the leftmost
    icon in an expression.  For the purpose of selection, that is simply the icon that was
    clicked.  For dragging and double clicking (execution), this function finds the
    outermost operation that claims the clicked icon as its leftmost operand."""
    # One idiotic case we have to distinguish, is when the clicked icon is a BinOpIcon
    # with automatic parens visible: only if the user clicked on the left paren can
    # the icon be the leftmost object in an expression.  Clicking on the body or the
    # right paren does not count.
    if fromIcon is None:
        fromIcon = clickedIcon.topLevelParent()
    if clickedIcon.__class__ is BinOpIcon and clickedIcon.hasParens:
        if not clickedIcon.locIsOnLeftParen(btnPressLoc):
            return clickedIcon
    if clickedIcon is fromIcon:
        return clickedIcon
    # Only binary operations are candidates, and only when the expression directly below
    # has claimed itself to be the leftmost operand of an expression
    if fromIcon.__class__ is AssignIcon:
        leftSiteIcon = fromIcon.sites.targets0[0].att
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is AugmentedAssignIcon:
        leftSiteIcon = fromIcon.sites.targetIcon.att
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is TupleIcon and fromIcon.noParens:
        leftSiteIcon = fromIcon.childAt('argIcons_0')
        if leftSiteIcon is not None:
            left = findLeftOuterIcon(clickedIcon, btnPressLoc, leftSiteIcon)
            if left is leftSiteIcon:
                return fromIcon  # Claim outermost status for this icon
    if fromIcon.__class__ is BinOpIcon and fromIcon.leftArg() is not None:
        left = findLeftOuterIcon(clickedIcon, btnPressLoc, fromIcon.leftArg())
        if left is fromIcon.leftArg():
            targetIsBinOpIcon = clickedIcon.__class__ is BinOpIcon
            if not targetIsBinOpIcon or targetIsBinOpIcon and clickedIcon.hasParens:
                # Again, we have to check before claiming outermost status for fromIcon,
                # if its left argument has parens, whether its status as outermost icon
                # was earned by promotion or by a direct click on its parens.
                if left.__class__ is not BinOpIcon or not left.hasParens or \
                 left.locIsOnLeftParen(btnPressLoc):
                    return fromIcon  # Claim outermost status for this icon
    # Pass on any results from below fromIcon in the hierarchy
    children = fromIcon.children()
    if children is not None:
        for child in fromIcon.children():
            result = findLeftOuterIcon(clickedIcon, btnPressLoc, child)
            if result is not None:
                return result
    return None

def drawSeqSites(img, boxLeft, boxTop, boxHeight, indent=None, extendWidth=None):
    """Draw sequence (in and out) sites on a rectangular boxed icon.  If extendWidth
    is specified and the icon specifies an indent, build up the icon outline to include
    the indented sequence site.  The value for extendWidth should be the width of the
    icon box (how far in x beyond boxLeft to start the extension."""
    topIndent = 0
    bottomIndent = 0
    if indent == "right":
        bottomIndent = BLOCK_INDENT
    elif indent == "left":
        topIndent = BLOCK_INDENT
    img.putpixel((topIndent + boxLeft + 1, boxTop+1),  OUTLINE_COLOR)
    img.putpixel((topIndent + boxLeft + 2, boxTop+1), OUTLINE_COLOR)
    img.putpixel((topIndent + boxLeft + 2, boxTop+2), OUTLINE_COLOR)
    img.putpixel((topIndent + boxLeft + 1, boxTop+2), OUTLINE_COLOR)
    bottomSiteY = boxTop + boxHeight - 2
    img.putpixel((bottomIndent + boxLeft + 1, bottomSiteY), OUTLINE_COLOR)
    img.putpixel((bottomIndent + boxLeft + 2, bottomSiteY), OUTLINE_COLOR)
    img.putpixel((bottomIndent + boxLeft + 2, bottomSiteY-1), OUTLINE_COLOR)
    img.putpixel((bottomIndent + boxLeft + 1, bottomSiteY-1), OUTLINE_COLOR)
    if indent == "right":
        extendRight = bottomIndent + boxLeft + 2
        if extendWidth is not None and extendWidth < extendRight:
            boxRight = boxLeft + extendWidth - 1
            boxBottom = boxTop + boxHeight
            draw = ImageDraw.Draw(img)
            draw.rectangle((boxRight, boxBottom-3, extendRight-2, boxBottom-1),
             fill=ICON_BG_COLOR,  outline=OUTLINE_COLOR)
            img.putpixel((boxRight, boxBottom-2), ICON_BG_COLOR)
        img.putpixel((bottomIndent + boxLeft, bottomSiteY), OUTLINE_COLOR)
        img.putpixel((bottomIndent + boxLeft, bottomSiteY - 1), OUTLINE_COLOR)

class IconSite:
    def __init__(self, siteName, siteType, xOffset=0, yOffset=0):
        self.name = siteName
        self.type = siteType
        self.xOffset = xOffset
        self.yOffset = yOffset
        self.att = None

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
    def __init__(self, name, siteType, initCount=0, initOffsets=None):
        self.type = siteType
        self.name = name
        self.sites = [None] * initCount
        for idx in range(initCount):
            if initOffsets is not None and idx < len(initOffsets):
                xOff, yOff = initOffsets[idx]
            else:
                xOff, yOff = 0, 0
            self.sites[idx] = IconSite(makeSeriesSiteId(name, idx), siteType, xOff, yOff)

    def __getitem__(self, idx):
        return self.sites[idx]

    def __len__(self):
        return len(self.sites)

    def insertSite(self, insertIdx):
        site = IconSite(makeSeriesSiteId(self.name, insertIdx), self.type)
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

    def allSites(self):
        """Traverse all sites in the list (generator)"""
        for siteNames in self._typeDict.values():
            for name in siteNames:
                site =getattr(self, name)
                if isinstance(site, IconSiteSeries):
                    for s in site.sites:
                        yield s
                elif isinstance(site, IconSite):
                    yield site

    def siteOfAttachedIcon(self, ic):
        for site in self.allSites():
            if site.att == ic:
                return site
        return None

    def childSites(self):
        childList = []
        for siteType, siteNames in self._typeDict.items():
            if siteType in childSiteTypes:
                for name in siteNames:
                    site = getattr(self, name)
                    if isinstance(site, IconSiteSeries):
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

    def add(self, name, siteType, xOffset=0, yOffset=0):
        """Add a new icon site to the site list given name and type.  Optionally add
        offset from the icon origin (sometimes these are not known until the icon has
        been through layout).  The ordering of calls to add determines the order in which
        sites will be traversed."""
        setattr(self, name, IconSite(name, siteType, xOffset, yOffset))
        if siteType not in self._typeDict:
            self._typeDict[siteType] = []
        self._typeDict[siteType].append(name)

    def addSeries(self, name, siteType, initCount=0, initOffsets=None):
        setattr(self, name, IconSiteSeries(name, siteType, initCount, initOffsets))
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
        if isinstance(series, IconSiteSeries):
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

    def makeSnapLists(self, ic, x, y, forCursor=False):
        snapSites = {}
        for site in self.allSites():
            # Omit any site whose attached icon has a site of the same type, at the
            # same location.  In such a case we want both dropped icons and typing to
            # go to the site of the innermost (most local) icon.
            if hasLowerCoincidentSite(ic, site.name):
                continue
            # Numeric icons have attribute sites for cursor, only (no snapping)
            if site.type == 'attrIn' and not forCursor and isinstance(ic, NumericIcon):
                continue
            # seqIn and seqOut sites are only valid for icons at the top level
            if site.type in ('seqIn', 'seqOut') and ic.parent() is not None:
                continue
            # The first icon in a sequence hosts the snap site for the sequence
            hasPrev = ic.prevInSeq() is not None
            if hasPrev and site.type in ('output', 'seqInsert'):
                continue
            # If the icon is in a sequence, convert the output site to a seqInsert
            hasNext = ic.nextInSeq()
            if site.type == 'output' and (hasPrev or hasNext):
                siteType = 'seqInsert'
            else:
                siteType = site.type
            # If the icon has an attrIn site with something connected, also give it an
            # insertAttr site
            if site.type == 'attrIn' and ic.sites.attrIcon.att is not None:
                snapSites['insertAttr'] = [(ic, (x + site.xOffset,
                 y + site.yOffset + INSERT_SITE_Y_OFFSET), site.name)]
            # Add the snap site to the list
            if siteType not in snapSites:
                snapSites[siteType] = []
            snapSites[siteType].append((ic, (x + site.xOffset, y + site.yOffset),
             site.name))
        return snapSites

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

def highestCoincidentIcon(ic):
    """Return highest icon with an output coincident with that of ic"""
    while True:
        parent = ic.parent()
        if parent is None or not isCoincidentSite(parent, parent.siteOf(ic)):
            return ic
        ic = parent

def lowestCoincidentSite(ic, site):
    """Return the icon and site occupying the lowest coincident input site at ic, site"""
    # ic itself does not need to have a coincident site (site is coincident with itself)
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

class ListLayoutMgr:
    """Manage layout for a one-dimensional list of icon arguments.  An icon can have
    multiple argument lists, and each list should have its own ListLayoutMgr.  By default,
    the icon is responsible for drawing parens/brackets/braces around the list.  However
    for icons that don't draw these, a "simple spine" (minimal visual grouping guide to
    help the user associate the list with the parent icon) can be requested that will
    appear when the list becomes multi-row.  Both the layout and the .width attribute
    incorporate the additional space where the spine will draw, but the caller must
    invoke drawSimpleSpine to actually draw it"""
    def __init__(self, ic, siteSeriesName, leftSiteX, leftSiteY, simpleSpine=False):
        self.icon = ic
        self.siteSeriesName = siteSeriesName
        self.simpleSpine = simpleSpine
        ic.sites.addSeries(siteSeriesName, 'input', 1, [(leftSiteX, leftSiteY)])
        self.width = 0
        self.height = minTxtIconHgt
        self.spineHeight = minTxtIconHgt
        self.spineTop = minTxtIconHgt // 2
        self.bodySitePositions = None
        self.commaSitePositions = None
        self.rowWidths = None

    def drawListCommas(self, leftSiteX, leftSiteY):
        xOff = leftSiteX + inSiteImage.width - commaImage.width
        yOff = leftSiteY - commaImageSiteYOffset
        return [((x+xOff, y+yOff), commaImage) for x, y in self.commaSitePositions]

    def drawBodySites(self, bodyImg):
        xOff = bodyImg.width - inSiteImage.width
        yOff = self.spineTop - inSiteImage.height // 2
        for x, y in self.bodySitePositions:
            bodyImg.paste(inSiteImage, (x+xOff, y+yOff))

    def drawSimpleSpine(self, leftSiteX, leftSiteY, drawOutputSite=True):
        """Returns left and right spine images suitable for an icon draw list for the
        minimal "simple spine" used by icons which do not draw parens/brackets/braces
        around argument lists.  If drawOutputSite is specified as False, the spine will
        not include an output site (but note that position is still specified as if it
        were on an output site, two pixels left of the spine)."""
        if not self.simpleSpineWillDraw():
            return []
        lImg = lSimpleSpineImage if drawOutputSite else rSimpleSpineImage
        lSpine = yStretchImage(lImg, simpleSpineExtendDupRows, self.spineHeight)
        outSiteY = self.spineTop - outSiteImage.height // 2
        if drawOutputSite:
            lSpine.paste(outSiteImage, (0, outSiteY), mask=outSiteImage)
        self.drawBodySites(lSpine)
        rSpine = yStretchImage(rSimpleSpineImage, simpleSpineExtendDupRows,
                self.spineHeight)
        rightX = leftSiteX + OUTPUT_SITE_DEPTH + self.width - rSimpleSpineImage.width
        if not drawOutputSite:
            leftSiteX += OUTPUT_SITE_DEPTH
        return [((leftSiteX, leftSiteY - self.spineTop), lSpine),
                ((rightX, leftSiteY - self.spineTop), rSpine)]

    def simpleSpineWillDraw(self):
        """Return True if ListLayoutMgr has simpleSpine enabled and the chosen layout
        (last doLayout call) was multi-row (requires drawSimpleSpine call and includes
        space for drawing the simple spine)."""
        return self.simpleSpine and self.rowWidths and len(self.rowWidths) >= 2

    def makeInsertSnapList(self):
        """Generate snap sites for item insertion"""
        insertSites = []
        inputSites = self.icon.sites.getSeries(self.siteSeriesName)
        if len(inputSites) > 1 or len(inputSites) == 1 and inputSites[0].att is not None:
            x, y = self.icon.rect[:2]
            x += INSERT_SITE_X_OFFSET
            y += INSERT_SITE_Y_OFFSET
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
                    siteName = makeSeriesSiteId(self.siteSeriesName + 'Dup',
                            bodySiteIdxs[i+1])
                else:
                    siteName = makeSeriesSiteId(self.siteSeriesName, numInputSites)
                insertSites.append((self.icon, (siteX, siteY), siteName))
        return insertSites

    def doLayout(self, layout):
        """Updates the icon spacing for the list as calculated in the calcLayouts method.
        This does not call doLayout for the icons in the list (but calcLayouts adds the
        information to the icon layout such that layout.doSubLayouts will do them along
        with the rest of the attached icons)."""
        # layout for managed list gets merged in to layout of entire icon. List-specific
        # data is added as an attribute based on site name
        leftSublayoutOffset = OUTPUT_SITE_DEPTH if self.simpleSpineWillDraw() else 0
        self.width, self.height, siteOffsets, self.rowWidths = getattr(layout,
                self.siteSeriesName + 'ListMgrData')
        self.commaSitePositions = []
        self.bodySitePositions = []
        for offset in siteOffsets.values():
            if offset[0] == leftSublayoutOffset:
                self.bodySitePositions.append(offset)
            else:
                self.commaSitePositions.append(offset)
        minBodySiteY = 0   # Include the anchor point (y == 0)
        maxBodySiteY = 0
        for bodySitePos in self.bodySitePositions:
            minBodySiteY = min(minBodySiteY, bodySitePos[1])
            maxBodySiteY = max(maxBodySiteY, bodySitePos[1])
        if minBodySiteY == sys.maxsize or maxBodySiteY == minBodySiteY:
            self.spineHeight = minTxtIconHgt
            self.spineTop = minTxtIconHgt // 2
        else:
            self.spineHeight = maxBodySiteY - minBodySiteY + inSiteImage.height + 10
            self.spineTop = -minBodySiteY + inSiteImage.height // 2 + 5

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
            layout.height = minTxtIconHgt
            layout.parentSiteOffset = minTxtIconHgt // 2
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
            leftSublayoutOffset = OUTPUT_SITE_DEPTH if self.simpleSpineWillDraw() else 0
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
                    centerY = height // 2
                    for siteNum, sublayout in enumerate(sublayouts):
                        if rowNum < len(rowData)-1 and siteNum == rowData[rowNum+1][0]:
                            rowNum += 1
                            x = leftSublayoutOffset
                        startIdx, rowYOffset, rowWidth = rowData[rowNum]
                        siteName = siteSeries[siteNum].name
                        lo.addSubLayout(sublayout, siteName, x, rowYOffset - centerY)
                        x += (LIST_EMPTY_ARG_WIDTH if sublayout is None else
                              sublayout.width) + commaImage.width - 2
                    lo.width = margin
                    if self.simpleSpine and len(rowData) >= 2:
                        lo.width += rSimpleSpineImage.width * 2 - 2
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
                    loWidth = LIST_EMPTY_ARG_WIDTH if lo is None else lo.width
                    heapq.heappush(rowBranches, (loWidth, (0, 0, 0, 0, ()), lo))
            # Loop, incrementally incorporating new layout choices until the margin is
            # reached
            while len(rowBranches) > 0 and rowBranches[0][0] <= margin:
                # pull the shortest non-margin-exceeding layout from rowBranches
                width, baseRowLayout, newItemLayout = heapq.heappop(rowBranches)
                # Make a new row layout by advancing baseRowLayout with newItemLayout
                _, heightAbove, heightBelow, badness, sublayouts = baseRowLayout
                if newItemLayout is None:
                    itemHeightAbove = minTxtIconHgt // 2
                    itemHeightBelow = minTxtIconHgt - itemHeightAbove
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
                            loWidth = LIST_EMPTY_ARG_WIDTH if lo is None else lo.width
                            rowWidth = width + loWidth + commaImage.width-2
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
            layout.height = minTxtIconHgt
            return [layout]
        commaWidth = commaImage.width - 1
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
                        childWidth = LIST_EMPTY_ARG_WIDTH
                        childHeightAbove = minTxtIconHgt // 2
                        childHeightBelow = minTxtIconHgt - childHeightAbove
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

def drawSeqSiteConnection(toIcon, image=None, clip=None):
    """Draw connection line between ic's seqIn site and whatever it connects."""
    # Note that this is not currently used.  Since sequenced icons are usually close
    # together, it seems to be enough that they share the same indent.  However there
    # may be reasons to bring this code back, so for now it remains.
    fromIcon = toIcon.prevInSeq()
    if fromIcon is None:
        return
    fromX, fromY = fromIcon.posOfSite('seqOut')
    toX, toY = toIcon.posOfSite('seqIn')
    if clip is not None:
        # Clip the line to within the clip rectangle.  This is simplified by the fact
        # that connections are always vertical and drawn downward from seqOut to seqIn,
        # and that rectangles are defined ordered left, top, right, bottom.
        l, t, r, b = clip
        if fromX < l or fromX > r:
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
        draw = fromIcon.window.draw
    else:
        draw = ImageDraw.Draw(image)
    draw.line((fromX, fromY, toX, toY), SEQ_CONNECT_COLOR)

def seqConnectorTouches(toIcon, rect):
    """Return True if the icon is connected via its seqIn site and the sequence site
    connector line intersects rectangle, rect."""
    fromIcon = toIcon.prevInSeq()
    if fromIcon is None:
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
    fromY = ic.posOfSite('seqOut')[1] + 2
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
    while True:
        if not hasattr(ic.sites, 'seqIn'):
            return ic
        prevIc = ic.sites.seqIn.att
        if prevIc is None:
            return ic
        if toStartOfBlock and hasattr(prevIc, 'blockEnd'):
            return ic
        ic = prevIc
        if isinstance(ic, BlockEnd):
            # Shortcut around blocks significantly improves performance
            ic = ic.primary

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
 restrictToPage=None, skipInnerBlocks=False):
    if includeStartingIcon:
        if hier:
            yield from ic.traverse()
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
            if ic is None:
                return
            if restrictToPage is not None and ic.window.topIcons[ic] != restrictToPage:
                return
            if hier:
                yield from ic.traverse()
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
                yield from ic.traverse()
            else:
                yield ic

def elseElifBlockIcons(ic):
    """Returns a list of all icons (hierarchy) in an else or elif clause, including
    the else or elif icon itself."""
    seqIcons = list(ic.traverse())
    for seqIcon in traverseSeq(ic, includeStartingIcon=False):
        if isinstance(seqIcon, BlockEnd):
            break
        if seqIcon.__class__ in (ElifIcon, ElseIcon):
            break
        seqIcons += list(seqIcon.traverse())
    return seqIcons

def insertSeq(seqStartIc, atIc, before=False):
    seqEndIc = findSeqEnd(seqStartIc)
    if before:
        prevIcon = atIc.sites.seqIn.att
        if prevIcon is not None:
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
    while ic.hasSite('attrIcon') and ic.sites.attrIcon.att != None:
        ic = ic.sites.attrIcon.att
        yield ic

def findLastAttrIcon(ic):
    for i in traverseAttrs(ic):
        pass
    return i

def findAttrOutputSite(ic):
    if ic.hasSite('output'):
        return ic
    for i in ic.parentage():
        if i.hasSite('output'):
            return i
    return None

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

def containingRect(icons):
    maxRect = python_g.AccumRects()
    for ic in icons:
        maxRect.add(ic.rect)
    return maxRect.get()

def rectWidth(rect):
    return rect[2] - rect[0]

def rectHeight(rect):
    return rect[3] - rect[1]

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
    return  _getIconClasses.cachedDict
_getIconClasses.cachedDict = None

def _singleArgTextRepr(site):
    if site.att is None:
        return "None"
    return site.att.textRepr()

def _seriesTextRepr(seriesSite):
    argText = ""
    for site in seriesSite:
        if site.att is None:
            argText = argText + "None, "
        else:
            argText = argText + site.att.textRepr() + ", "
    if len(argText) > 0:
        argText = argText[:-2]
    return argText

def _attrTextRepr(ic):
    if ic.sites.attrIcon.att is None:
        return ""
    return ic.sites.attrIcon.att.textRepr()

def _restoreConditionalTargets(ic, snapLists, directAttachmentClasses):
    """Add back versions of sites that were filtered out for having more local snap
    targets (such as left arg of BinOpIcon).  The ones added back are conditional on
    icon types that must be directly connected (directAttachmentClasses)."""
    snapFn = lambda ic, s: ic.__class__ in directAttachmentClasses
    if 'conditional' not in snapLists:
        snapLists['conditional'] = []
    for site in ic.sites.argIcons:
        for i, pos, name in snapLists.get("input", []):
            if name == site.name:
                break
        else:
            snapLists['conditional'].append((ic, ic.posOfSite(site.name),
            site.name, site.type, snapFn))

def dumpHier(ic, indent=0, site=""):
    print("   " * indent, site, ic.dumpName(), '#' + str(ic.id))
    for child in ic.children():
        dumpHier(child, indent+1, ic.siteOf(child))

def determineCtx(ic):
    """Figure out the load/store/delete context of a given icon.  Returns an object
    of class ast.Load, ast.Store, or ast.Del based on the result."""
    # Architecture note: it would have been more direct and efficient to to add a
    # parameter to createAst to pass the context from parent icons as asts are created.
    # I am calculating this per-icon, because I suspect the information will be important
    # for display and interaction purposes later on (for example, showing current errors).
    if ic.hasSite('attrIcon') and ic.childAt('attrIcon'):
        return ast.Load()  # Has attribute but is not at the end of the attribute chain
    parent = ic.parent()
    if parent is None:
        return ast.Load()  # At the top level
    if parent.siteOf(ic) == 'attrIcon':
        # ic is the end of an attribute chain.  Determine ctx from parent of its root.
        ic = findAttrOutputSite(ic)
        if ic is None:
            return ast.Load()
        parent = ic.parent()
        if parent is None:
            return ast.Load()
    parentClass = parent.__class__
    if parentClass in (ListIcon, TupleIcon):
        # A list or tuple can be an assignment target: look above for assignment
        return determineCtx(parent)
    # Return ast.Store() if parent site is an assignment target, ast.Del() if it is a
    # deletion target, or ast.Load() if neither.
    parentSite = parent.siteOf(ic, recursive=True)
    if parentClass in (AssignIcon, AugmentedAssignIcon, ForIcon, CprhForIcon):
        if parentSite[:6] == 'target':
            return ast.Store()
    elif parentClass in (DefIcon, ClassDefIcon):
        if parentSite == 'nameIcon':
            return ast.Store()
    elif parentClass is WithAsIcon:
        if parentSite == 'rightArg':
            return ast.Store()
    elif parentClass is DelIcon:
        return ast.Del()
    return ast.Load()

def createComprehensionAst(ic):
    eltIcon = ic.childAt('argIcons_0')
    if eltIcon is None:
        raise IconExecException(ic, "Missing expression")
    generators = []
    for site in ic.sites.cprhIcons:
        cprhIcon = site.att
        if cprhIcon is None:
            continue
        if isinstance(cprhIcon, CprhForIcon):
            generators.append([cprhIcon])
        elif isinstance(cprhIcon, CprhIfIcon):
            generators[-1].append(cprhIcon)
        else:
            raise IconExecException(cprhIcon, 'Unexpected item in comprehension')
    if len(generators) == 0:
        raise IconExecException(ic, 'Missing "for" in comprehension')
    generatorAsts = []
    for generator in generators:
        ifAsts = [ifClause.createAst() for ifClause in generator[1:]]
        generatorAsts.append(generator[0].createAst(ifAsts))
    if isinstance(ic, DictIcon):
        if isinstance(eltIcon, DictElemIcon):
            key = eltIcon.childAt('leftArg')
            value = eltIcon.childAt('rightArg')
            if not key or not value:
                raise IconExecException(eltIcon, "Missing argument to dictionary element")
            return ast.DictComp(key.createAst(), value.createAst(), generatorAsts,
             lineno=ic.id, col_offset=0)
        else:
            return ast.SetComp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
             col_offset=0)
    elif isinstance(ic, ListIcon):
        return ast.ListComp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
         col_offset=0)
    return ast.GeneratorExp(eltIcon.createAst(), generatorAsts, lineno=ic.id,
     col_offset=0)

def composeAttrAst(ic, icAst):
    if ic.sites.attrIcon.att:
        return ic.sites.attrIcon.att.createAst(icAst)
    return icAst

def createBlockAsts(ic, allowsElse=False, allowsElifElse=False):
    """Create ASTs for icons in the block belonging to ic, suitable for the "body"
    parameter to ASTs for statements that own an indented block.  If allowsElse is
    True, the block can contain an else clause.  If allowsElifElse is True, the block
    may also contain elif statements and the function returns two items: 1) a list of
    the statement ASTs, and 2) a list of the else-clause ASTs (there is no elif AST,
    elifs are converted to an else clause containing chained "if" ASTs).  Without
    either allowsElse or allowsElifElse, the function returns just the list of statement
    ASTs"""
    stmtAsts = []
    endBlock = ic.blockEnd
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            if not allowsElifElse:
                raise IconExecException(stmt, "Elif statement should not be here")
            return stmtAsts, [createElifAst(stmt, endBlock)]
        elif isinstance(stmt, ElseIcon):
            if not (allowsElse or allowsElifElse):
                raise IconExecException(stmt, "Else statement should not be here")
            return stmtAsts, createElseAsts(stmt, endBlock)
        else:
            stmtAsts.append(createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    if allowsElse or allowsElifElse:
        return stmtAsts, []
    return stmtAsts

def createElseAsts(ic, endBlock):
    """Return a list of statement ASTs from the else clause starting at"""
    stmtAsts = []
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            raise IconExecException(stmt, "Elif statement found after else")
        if isinstance(stmt, ElseIcon):
            raise IconExecException(stmt, "Multiple else statements")
        stmtAsts.append(createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    return stmtAsts

def createElifAst(ic, endBlock):
    """Returns a single "if" AST representing the remaining elif and else clauses starting
    at elif icon, ic."""
    if ic.sites.condIcon.att is None:
        raise IconExecException(ic, "Missing condition in elif")
    stmtAsts = []
    stmt = ic.nextInSeq()
    while stmt is not endBlock:
        if stmt is None:
            raise IconExecException(ic, "Error processing code block")
        if isinstance(stmt, ElifIcon):
            return ast.If(ic.sites.condIcon.att.createAst(), stmtAsts,
             [createElifAst(stmt, endBlock)], lineno=ic.id, col_offset=0)
        if isinstance(stmt, ElseIcon):
            return ast.If(ic.sites.condIcon.att.createAst(), stmtAsts,
             createElseAsts(stmt, endBlock), lineno=ic.id, col_offset=0)
        stmtAsts.append(createStmtAst(stmt))
        if hasattr(stmt, 'blockEnd'):
            stmt = stmt.blockEnd.nextInSeq()
        else:
            stmt = stmt.nextInSeq()
    return stmtAsts

def createStmtAst(ic):
    """Create the ast corresponding to a top-level icon (ic).  For statements, this
    simply means calling the .createAst() method, but for expressions this additionally
    entails wrapping it in an ast.Expr() node."""
    stmtAst = ic.createAst()
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
