# Copyright Mark Edel  All rights reserved
# Constants and low-level utility functions used across modules
from PIL import Image

# Number of pixels to indent a code block
BLOCK_INDENT = 24

# Outline color is currently set to white with a minimal non-zero alpha to allow
# a rendering trick to make outlines appear on demand.  This is sub-optimal because it
# does not allow any sort of variable coloring or shading in outlines.
OUTLINE_COLOR = (255, 255, 255, 1)

ICON_BG_COLOR = (255, 255, 255, 255)

def asciiToImage(asciiPixmap, tint=None):
    if asciiToImage.asciiMap is None:
        asciiToImage.asciiMap = {'.':(0, 0, 0, 0), 'o': OUTLINE_COLOR,
                ' ': ICON_BG_COLOR, '%':(0, 0, 0, 255), 'R':(255, 0, 0, 255),
                'r':(255, 128, 128, 255)}
        for i in range(1, 10):
            lum = int(int(i) * 255 * 0.1)
            asciiToImage.asciiMap[str(i)] = (lum, lum, lum, 255)
    if tint is not None:
        colorMap = dict(asciiToImage.asciiMap)
        colorMap['%'] = tint
        for i in range(1,10):
            lum = int(int(i) * 255 * 0.1)
            tr, tg, tb, ta = tint
            colorMap[str(i)] = (_tint(lum, tr), _tint(lum, tg), _tint(lum, tb), ta)
    else:
        colorMap = asciiToImage.asciiMap
    height = len(asciiPixmap)
    width = len(asciiPixmap[0])
    pixels = "".join(asciiPixmap)
    colors = [colorMap[pixel] for pixel in pixels]
    image = Image.new('RGBA', (width, height))
    image.putdata(colors)
    return image
asciiToImage.asciiMap = None

def _tint(color, tint):
    scale = (255 - tint) / 255
    return int(tint + color * scale)

def rectWidth(rect):
    return rect[2] - rect[0]

def rectHeight(rect):
    return rect[3] - rect[1]

def rectsTouch(rect1, rect2):
    """Returns true if rectangles rect1 and rect2 overlap"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    # One is to the right side of the other
    if l1 > r2 or l2 > r1:
        return False
    # One is above the other
    if t1 > b2 or t2 > b1:
        return False
    return True

def offsetRect(rect, xOff, yOff):
    l, t, r, b = rect
    return l+xOff, t+yOff, r+xOff, b+yOff

def combineRects(rect1, rect2):
    """Find the minimum rectangle enclosing rect1 and rect2"""
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    return min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)

class AccumRects:
    """Make one big rectangle out of all rectangles added."""
    def __init__(self, initRect=None):
        self.rect = initRect

    def add(self, rect):
        if rect is None:
            return
        if self.rect is None:
            self.rect = rect
        else:
            self.rect = combineRects(rect, self.rect)

    def get(self):
        """Return the enclosing rectangle.  Returns None if no rectangles were added"""
        return self.rect

    def clear(self):
        self.rect = None

def findTextOffset(font, text, pixelOffset):
    # We use proportionally-spaced fonts, but don't have full access to the font
    # rendering code, so the only tool we have to see how it got laid out is the
    # font.getsize method, which can only answer the question: "how many pixels long is
    # this entire string".  Rather than try to measure individual characters and adjust
    # for kerning and other oddness, this code makes a statistical starting guess and
    # brutally iterates until it finds the right place.
    nChars = len(text)
    if nChars == 0:
        return 0
    textLength = font.getsize(text)[0]
    guessedPos = (nChars * pixelOffset) // textLength
    lastGuess = None
    lastGuessDist = textLength
    while True:
        pixelOfGuess = font.getsize(text[:guessedPos])[0]
        guessDist = abs(pixelOfGuess - pixelOffset)
        if pixelOfGuess > pixelOffset:
            if lastGuess == '<':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '>'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos -= 1
            if guessedPos <= 0:
                return 0 if pixelOffset < guessDist else lastGuessedPos
        elif pixelOfGuess < pixelOffset:
            if lastGuess == '>':
                return guessedPos if guessDist < lastGuessDist else lastGuessedPos
            lastGuess = '<'
            lastGuessDist = guessDist
            lastGuessedPos = guessedPos
            guessedPos += 1
            if guessedPos >= nChars:
                return nChars if textLength - pixelOffset < guessDist else lastGuessedPos
        else:
            return guessedPos

def splitWords(text):
    """Split the string at the end of whitespace of word boundaries, and return a
    list of strings.  Newlines are considered a word by themselves."""
    foundSpace = False
    words = []
    startIdx = 0
    inEscape = False
    for i, c in enumerate(text):
        if c == '\n':
            words.append(text[startIdx:i])
            words.append('\n')
            startIdx = i + 1
            foundSpace = False
            inEscape = False
        elif c.isspace():
            foundSpace = True
        elif foundSpace:
            words.append(text[startIdx:i])
            startIdx = i
            foundSpace = False
            inEscape = c == '\\'
        elif c == '\\':
            inEscape = True
        elif inEscape and c in ('t', 'n', 'r', 'v', 'f'):
            words.append(text[startIdx:i+1])
            startIdx = i + 1
            foundSpace = False
            inEscape = False
        else:
            inEscape = False
    words.append(text[startIdx:])
    return words

def breakLongWords(words, maxWordLength, maxFirstWrapLength=None):
    if maxFirstWrapLength is None:
        maxFirstWrapLength = maxWordLength
    segments = []
    maxLength = maxFirstWrapLength
    for i, string in enumerate(words):
        if len(string) > maxLength:
            startIdx = 0
            while len(string) - startIdx > maxLength:
                segments.append(string[startIdx:startIdx + maxLength])
                startIdx += maxLength
                maxLength = maxWordLength
            segments.append(string[startIdx:])
        else:
            segments.append(string)
        maxLength = maxWordLength
    return segments

def wordWrap(words, maxLineLength, firstLineMax=None, lastLineMax=None):
    """Python's built-in textwrap module, unfortunately, does not treat space characters
    and their equivalents at the end of the line the way we need them treated for
    displaying strings and comments and wrapping comments in the save-file format.  In
    all three of these cases, we need to both preserve all characters, and if possible,
    place space characters before the wrap.  Returns a list of line strings and the
    length in characters of the actual longest line."""
    if firstLineMax is None:
        firstLineMax = maxLineLength
    if lastLineMax is None:
        lastLineMax = maxLineLength
    words = breakLongWords(words, maxLineLength, firstLineMax)
    lines = []
    lineLen = 0
    lineWords = []
    maxLength = firstLineMax
    lastWordIdx = len(words) - 1
    maxUsedLineLen = 0
    for i, word in enumerate(words):
        if i == lastWordIdx and len(lines) > 0:
            maxLength = lastLineMax
        if word == '\n':
            lineWords.append(word)
            lines.append(''.join(lineWords))
            lineLen = 0
            lineWords = []
            maxLength = maxLineLength
        elif len(word) + lineLen <= maxLength or (word[-1] == ' ' and
                len(word) + lineLen == maxLength + 1 and i < len(words)-1):
            lineWords.append(word)
            lineLen += len(word)
        else:
            lines.append(''.join(lineWords))
            lineLen = len(word)
            lineWords = [word]
            maxLength = maxLineLength
        if lineLen > maxUsedLineLen:
            maxUsedLineLen = lineLen
    lines.append(''.join(lineWords))
    return lines, maxUsedLineLen
